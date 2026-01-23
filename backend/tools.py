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


@tool
def browse_page(url: str) -> Dict[str, Any]:
    """
    Browse and extract content from a webpage URL.
    Useful for reading articles, documentation, or any web content.
    
    Args:
        url: The URL of the webpage to browse
        
    Returns:
        Dictionary with title, content (text), and url
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        # Add headers to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title
        title = soup.find('title')
        title_text = title.get_text().strip() if title else "No title"
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text content
        text = soup.get_text()
        
        # Clean up text - remove extra whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text_content = ' '.join(chunk for chunk in chunks if chunk)
        
        # Limit content length to avoid token overflow
        max_length = 3000
        if len(text_content) > max_length:
            text_content = text_content[:max_length] + "..."
        
        return {
            "title": title_text,
            "content": text_content,
            "url": url,
            "error": False
        }
    
    except ImportError:
        return {
            "title": "Missing Dependencies",
            "content": "Required packages (requests, beautifulsoup4) not installed. Run: pip install requests beautifulsoup4",
            "url": url,
            "error": True
        }
    except requests.exceptions.Timeout:
        return {
            "title": "Timeout Error",
            "content": f"Request to {url} timed out after 10 seconds",
            "url": url,
            "error": True
        }
    except requests.exceptions.HTTPError as e:
        return {
            "title": "HTTP Error",
            "content": f"HTTP error occurred: {str(e)}",
            "url": url,
            "error": True
        }
    except Exception as e:
        return {
            "title": "Browse Error",
            "content": f"Error browsing page: {str(e)}",
            "url": url,
            "error": True
        }


# Export all tools for easy access
AVAILABLE_TOOLS = [tavily_search, duckduckgo_search, vespa_search, browse_page]
