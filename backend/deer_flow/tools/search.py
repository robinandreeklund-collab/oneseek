# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
import logging
import os
import threading
from typing import List, Optional

from langchain_community.tools import (
    BraveSearch,
    DuckDuckGoSearchResults,
    GoogleSerperRun,
    SearxSearchRun,
    WikipediaQueryRun,
)
from langchain_community.tools.arxiv import ArxivQueryRun
from langchain_community.utilities import (
    ArxivAPIWrapper,
    BraveSearchWrapper,
    GoogleSerperAPIWrapper,
    SearxSearchWrapper,
    WikipediaAPIWrapper,
)

from backend.deer_flow.config import SELECTED_SEARCH_ENGINE, SearchEngine, load_yaml_config
from backend.deer_flow.tools.decorators import create_logged_tool
from backend.deer_flow.tools.infoquest_search.infoquest_search_results import InfoQuestSearchResults
from backend.deer_flow.tools.tavily_search.tavily_search_results_with_images import (
    TavilySearchWithImages,
)

logger = logging.getLogger(__name__)

# Track per-run web_search usage to prevent infinite tool loops
_web_search_lock = threading.Lock()
_web_search_calls_by_run: dict[str, dict[str, int]] = {}
_web_search_total_by_run: dict[str, int] = {}
_DEFAULT_MAX_WEB_SEARCH_CALLS = int(os.getenv("WEB_SEARCH_MAX_CALLS", "6"))
_DEFAULT_MAX_WEB_SEARCH_DUPLICATES = int(os.getenv("WEB_SEARCH_MAX_DUPLICATE_CALLS", "2"))
_DEFAULT_MAX_WEB_SEARCH_QUERY_CHARS = int(os.getenv("WEB_SEARCH_MAX_QUERY_CHARS", "400"))


def _sanitize_web_search_query(query: str) -> str:
    if query is None:
        return ""
    text = " ".join(str(query).split())
    if _DEFAULT_MAX_WEB_SEARCH_QUERY_CHARS > 0 and len(text) > _DEFAULT_MAX_WEB_SEARCH_QUERY_CHARS:
        logger.warning(
            "Web search query truncated from %s to %s chars",
            len(text),
            _DEFAULT_MAX_WEB_SEARCH_QUERY_CHARS,
        )
        text = text[:_DEFAULT_MAX_WEB_SEARCH_QUERY_CHARS]
    return text


def _record_web_search_call(run_id: str, query: str) -> tuple[int, int]:
    normalized_query = (query or "").strip().lower()
    with _web_search_lock:
        total = _web_search_total_by_run.get(run_id, 0) + 1
        _web_search_total_by_run[run_id] = total
        per_query = _web_search_calls_by_run.setdefault(run_id, {})
        per_query[normalized_query] = per_query.get(normalized_query, 0) + 1
        return total, per_query[normalized_query]


def _limit_web_search_calls(tool):
    from backend.deer_flow.tools.code_tools import get_current_run_id

    original_run = getattr(tool, "_run")
    original_arun = getattr(tool, "_arun", None)

    def _make_limit_response(query: str, reason: str) -> str:
        payload = {
            "status": "limit_reached",
            "reason": reason,
            "query": query,
            "message": (
                "Web search limit reached. Use existing results and proceed to answer."
            ),
        }
        return json.dumps(payload, ensure_ascii=False)

    def limited_run(query: str, *args, **kwargs):
        run_id = get_current_run_id()
        sanitized_query = _sanitize_web_search_query(query)
        total, duplicates = _record_web_search_call(run_id, sanitized_query)
        if total > _DEFAULT_MAX_WEB_SEARCH_CALLS:
            logger.warning(
                "Web search limit exceeded (run_id=%s total=%s query=%s)",
                run_id,
                total,
                query,
            )
            return _make_limit_response(sanitized_query, "max_calls")
        if duplicates > _DEFAULT_MAX_WEB_SEARCH_DUPLICATES:
            logger.warning(
                "Web search duplicate limit exceeded (run_id=%s query=%s count=%s)",
                run_id,
                query,
                duplicates,
            )
            return _make_limit_response(sanitized_query, "duplicate_query")
        return original_run(sanitized_query, *args, **kwargs)

    async def limited_arun(query: str, *args, **kwargs):
        run_id = get_current_run_id()
        sanitized_query = _sanitize_web_search_query(query)
        total, duplicates = _record_web_search_call(run_id, sanitized_query)
        if total > _DEFAULT_MAX_WEB_SEARCH_CALLS:
            logger.warning(
                "Web search limit exceeded (run_id=%s total=%s query=%s)",
                run_id,
                total,
                query,
            )
            return _make_limit_response(sanitized_query, "max_calls")
        if duplicates > _DEFAULT_MAX_WEB_SEARCH_DUPLICATES:
            logger.warning(
                "Web search duplicate limit exceeded (run_id=%s query=%s count=%s)",
                run_id,
                query,
                duplicates,
            )
            return _make_limit_response(sanitized_query, "duplicate_query")
        if original_arun:
            return await original_arun(sanitized_query, *args, **kwargs)
        return original_run(sanitized_query, *args, **kwargs)

    object.__setattr__(tool, "_run", limited_run)
    if original_arun:
        object.__setattr__(tool, "_arun", limited_arun)
    return tool

# Create logged versions of the search tools
LoggedTavilySearch = create_logged_tool(TavilySearchWithImages)
LoggedInfoQuestSearch = create_logged_tool(InfoQuestSearchResults)
LoggedDuckDuckGoSearch = create_logged_tool(DuckDuckGoSearchResults)
LoggedBraveSearch = create_logged_tool(BraveSearch)
LoggedSerperSearch = create_logged_tool(GoogleSerperRun)
LoggedArxivSearch = create_logged_tool(ArxivQueryRun)
LoggedSearxSearch = create_logged_tool(SearxSearchRun)
LoggedWikipediaSearch = create_logged_tool(WikipediaQueryRun)


def get_search_config():
    config = load_yaml_config("conf.yaml")
    search_config = config.get("SEARCH_ENGINE", {})
    # Handle both string (simple) and dict (advanced) configuration formats
    if isinstance(search_config, str):
        # Simple format: just the engine name, return empty dict for tool options
        return {}
    return search_config


# Get the selected search tool
def get_web_search_tool(max_search_results: int):
    search_config = get_search_config()

    if SELECTED_SEARCH_ENGINE == SearchEngine.TAVILY.value:
        # Get all Tavily search parameters from configuration with defaults
        include_domains: Optional[List[str]] = search_config.get("include_domains", [])
        exclude_domains: Optional[List[str]] = search_config.get("exclude_domains", [])
        include_answer: bool = search_config.get("include_answer", False)
        search_depth: str = search_config.get("search_depth", "advanced")
        include_raw_content: bool = search_config.get("include_raw_content", False)
        include_images: bool = search_config.get("include_images", True)
        include_image_descriptions: bool = include_images and search_config.get(
            "include_image_descriptions", True
        )

        logger.info(
            f"Tavily search configuration loaded: include_domains={include_domains}, "
            f"exclude_domains={exclude_domains}, include_answer={include_answer}, "
            f"search_depth={search_depth}, include_raw_content={include_raw_content}, "
            f"include_images={include_images}, include_image_descriptions={include_image_descriptions}"
        )

        return _limit_web_search_calls(LoggedTavilySearch(
            name="web_search",
            max_results=max_search_results,
            include_answer=include_answer,
            search_depth=search_depth,
            include_raw_content=include_raw_content,
            include_images=include_images,
            include_image_descriptions=include_image_descriptions,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
        ))
    elif SELECTED_SEARCH_ENGINE == SearchEngine.INFOQUEST.value:
        time_range = search_config.get("time_range", -1)
        site = search_config.get("site", "")
        logger.info(
            f"InfoQuest search configuration loaded: time_range={time_range}, site={site}"
        )
        return _limit_web_search_calls(LoggedInfoQuestSearch(
            name="web_search",
            time_range=time_range,
            site=site,
        ))
    elif SELECTED_SEARCH_ENGINE == SearchEngine.DUCKDUCKGO.value:
        return _limit_web_search_calls(LoggedDuckDuckGoSearch(
            name="web_search",
            num_results=max_search_results,
        ))
    elif SELECTED_SEARCH_ENGINE == SearchEngine.BRAVE_SEARCH.value:
        return _limit_web_search_calls(LoggedBraveSearch(
            name="web_search",
            search_wrapper=BraveSearchWrapper(
                api_key=os.getenv("BRAVE_SEARCH_API_KEY", ""),
                search_kwargs={"count": max_search_results},
            ),
        ))
    elif SELECTED_SEARCH_ENGINE == SearchEngine.SERPER.value:
        return _limit_web_search_calls(LoggedSerperSearch(
            name="web_search",
            api_wrapper=GoogleSerperAPIWrapper(
                k=max_search_results,
                serper_api_key=os.getenv("SERPER_API_KEY", ""),
            ),
        ))
    elif SELECTED_SEARCH_ENGINE == SearchEngine.ARXIV.value:
        return _limit_web_search_calls(LoggedArxivSearch(
            name="web_search",
            api_wrapper=ArxivAPIWrapper(
                top_k_results=max_search_results,
                load_max_docs=max_search_results,
                load_all_available_meta=True,
            ),
        ))
    elif SELECTED_SEARCH_ENGINE == SearchEngine.SEARX.value:
        return _limit_web_search_calls(LoggedSearxSearch(
            name="web_search",
            wrapper=SearxSearchWrapper(
                k=max_search_results,
            ),
        ))
    elif SELECTED_SEARCH_ENGINE == SearchEngine.WIKIPEDIA.value:
        wiki_lang = search_config.get("wikipedia_lang", "en")
        wiki_doc_content_chars_max = search_config.get(
            "wikipedia_doc_content_chars_max", 4000
        )
        return _limit_web_search_calls(LoggedWikipediaSearch(
            name="web_search",
            api_wrapper=WikipediaAPIWrapper(
                lang=wiki_lang,
                top_k_results=max_search_results,
                load_all_available_meta=True,
                doc_content_chars_max=wiki_doc_content_chars_max,
            ),
        ))
    else:
        raise ValueError(f"Unsupported search engine: {SELECTED_SEARCH_ENGINE}")
