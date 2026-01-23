"""
Search tools for OneSeek.ai agent
Implements Tavily, DuckDuckGo, and Vespa search as LangGraph tools
"""

import os
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()


@tool
def tavily_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search the web using Tavily API - a paid, robust, and highly accurate search platform.
    
    Args:
        query: The search query
        max_results: Maximum number of results to return (default: 5)
        
    Returns:
        List of search results with title, content, and URL
    """
    try:
        from tavily import TavilyClient
        
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return [{
                "title": "Tavily API Key Missing",
                "content": "TAVILY_API_KEY not configured in environment variables",
                "url": "",
                "error": True
            }]
        
        client = TavilyClient(api_key=api_key)
        response = client.search(query=query, max_results=max_results)
        
        results = []
        for item in response.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "content": item.get("content", ""),
                "url": item.get("url", ""),
                "score": item.get("score", 0.0)
            })
        
        return results if results else [{
            "title": "No Results",
            "content": "No results found for the query",
            "url": ""
        }]
    
    except ImportError:
        return [{
            "title": "Tavily Not Installed",
            "content": "tavily-python package is not installed. Install with: pip install tavily-python",
            "url": "",
            "error": True
        }]
    except Exception as e:
        return [{
            "title": "Tavily Search Error",
            "content": f"Error searching with Tavily: {str(e)}",
            "url": "",
            "error": True
        }]


@tool
def duckduckgo_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search the web using DuckDuckGo - a free, simple, and anonymous search engine.
    
    Args:
        query: The search query
        max_results: Maximum number of results to return (default: 5)
        
    Returns:
        List of search results with title, content, and URL
    """
    try:
        from duckduckgo_search import DDGS
        
        ddgs = DDGS()
        search_results = ddgs.text(query, max_results=max_results)
        
        results = []
        for item in search_results:
            results.append({
                "title": item.get("title", ""),
                "content": item.get("body", ""),
                "url": item.get("href", ""),
                "score": 1.0  # DuckDuckGo doesn't provide scores
            })
        
        return results if results else [{
            "title": "No Results",
            "content": "No results found for the query",
            "url": ""
        }]
    
    except ImportError:
        return [{
            "title": "DuckDuckGo Not Installed",
            "content": "duckduckgo-search package is not installed. Install with: pip install duckduckgo-search",
            "url": "",
            "error": True
        }]
    except Exception as e:
        return [{
            "title": "DuckDuckGo Search Error",
            "content": f"Error searching with DuckDuckGo: {str(e)}",
            "url": "",
            "error": True
        }]


@tool
def vespa_search(query: str, max_results: int = 6) -> List[Dict[str, Any]]:
    """
    Search local/cloud Vespa RAG with embeddings and hybrid searching.
    
    Args:
        query: The search query
        max_results: Maximum number of results to return (default: 6)
        
    Returns:
        List of search results with title, content, and relevance score
    """
    try:
        from pyvespa import Vespa
        from langchain_community.embeddings import HuggingFaceEmbeddings
        
        vespa_url = os.getenv("VESPA_URL")
        vespa_cert = os.getenv("VESPA_CERT_PATH")
        vespa_key = os.getenv("VESPA_KEY_PATH")
        
        if not vespa_url or not vespa_cert or not vespa_key:
            return [{
                "title": "Vespa Not Configured",
                "content": "Vespa configuration missing. Set VESPA_URL, VESPA_CERT_PATH, and VESPA_KEY_PATH",
                "relevance": 0.0,
                "error": True
            }]
        
        # Connect to Vespa
        vespa_app = Vespa(
            url=vespa_url,
            cert=vespa_cert,
            key=vespa_key
        )
        
        # Query Vespa with hybrid search
        yql = f"""
            select title, content from rag 
            where userQuery() 
            limit {max_results}
        """
        
        response = vespa_app.query(
            yql=yql,
            query=query
        )
        
        results = []
        if hasattr(response, 'hits'):
            for hit in response.hits:
                results.append({
                    "title": hit.get("fields", {}).get("title", ""),
                    "content": hit.get("fields", {}).get("content", ""),
                    "relevance": hit.get("relevance", 0.0),
                    "url": ""  # Vespa results typically don't have URLs
                })
        
        return results if results else [{
            "title": "No Results",
            "content": "No results found in Vespa",
            "relevance": 0.0
        }]
    
    except ImportError as e:
        return [{
            "title": "Vespa Import Error",
            "content": f"Required packages not installed: {str(e)}",
            "relevance": 0.0,
            "error": True
        }]
    except Exception as e:
        return [{
            "title": "Vespa Search Error",
            "content": f"Error searching Vespa: {str(e)}",
            "relevance": 0.0,
            "error": True
        }]


# Export all tools for easy access
AVAILABLE_TOOLS = [tavily_search, duckduckgo_search, vespa_search]
