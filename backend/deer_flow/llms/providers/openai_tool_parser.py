import logging
from typing import Any, Dict, Optional, Union

import openai
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatResult
from langchain_openai import AzureChatOpenAI as BaseAzureChatOpenAI
from langchain_openai import ChatOpenAI as BaseChatOpenAI

from backend.deer_flow.utils.llm_output_parser import parse_llm_output

logger = logging.getLogger(__name__)


def _apply_output_parsing(chat_result: ChatResult) -> ChatResult:
    for generation in chat_result.generations:
        message = generation.message
        if not isinstance(message, AIMessage):
            continue
        content = message.content if isinstance(message.content, str) else str(message.content)
        parsed = parse_llm_output(content)

        if parsed.reasoning_content and not message.additional_kwargs.get("reasoning_content"):
            message.additional_kwargs["reasoning_content"] = parsed.reasoning_content

        if parsed.tool_calls and not message.tool_calls:
            message.tool_calls = parsed.tool_calls

        if parsed.content != content:
            message.content = parsed.content

    return chat_result


class ChatOpenAIWithToolCallParsing(BaseChatOpenAI):
    """ChatOpenAI with XML tool_call/think parsing fallback."""

    def _create_chat_result(
        self,
        response: Union[Dict[str, Any], openai.BaseModel],
        generation_info: Optional[Dict[str, Any]] = None,
    ) -> ChatResult:
        chat_result = super()._create_chat_result(response, generation_info)
        try:
            return _apply_output_parsing(chat_result)
        except Exception as exc:
            logger.warning("Failed to parse XML tool_calls from OpenAI response: %s", exc)
            return chat_result


class AzureChatOpenAIWithToolCallParsing(BaseAzureChatOpenAI):
    """AzureChatOpenAI with XML tool_call/think parsing fallback."""

    def _create_chat_result(
        self,
        response: Union[Dict[str, Any], openai.BaseModel],
        generation_info: Optional[Dict[str, Any]] = None,
    ) -> ChatResult:
        chat_result = super()._create_chat_result(response, generation_info)
        try:
            return _apply_output_parsing(chat_result)
        except Exception as exc:
            logger.warning("Failed to parse XML tool_calls from Azure response: %s", exc)
            return chat_result
