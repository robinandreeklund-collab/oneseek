"""
Search tools for OneSeek.ai agent
Implements Tavily, DuckDuckGo, and Vespa search as LangGraph tools
"""

import os
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

# Constants for chunk handling
PREVIEW_LENGTH = 800  # Characters to show in preview for large pages
TRUNCATION_MESSAGE = "... [content truncated, use check_chunk_relevance to filter, then get_chunk_content to retrieve full text]"

# Global cache for storing full chunk content
# Note: For production use, consider thread-safe implementation or external cache
_chunk_content_cache = {}
_cache_lock = None  # Can be initialized with threading.Lock() for thread safety


def _get_chunk_cache():
    """Get or initialize the chunk content cache"""
    global _chunk_content_cache
    if not isinstance(_chunk_content_cache, dict):
        _chunk_content_cache = {}
    return _chunk_content_cache


@tool
def tavily_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search the web using Tavily API - a paid, robust, and highly accurate search platform.
    Uses advanced search depth and includes AI-generated answer summary.
    Searches are geographically focused on Sweden for relevant local results.
    
    Args:
        query: The search query
        max_results: Maximum number of results to return (default: 5)
        
    Returns:
        List of search results including AI summary and web results with title, content, URL, and score
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
        response = client.search(
            query=query,
            max_results=max_results,
            include_answer="advanced",
            search_depth="advanced",
            country="sweden"
        )
        
        results = []
        
        # Include Tavily's advanced LLM-generated answer if available
        if response.get("answer"):
            results.append({
                "title": "Tavily AI Summary",
                "content": response.get("answer"),
                "url": "",
                "score": 1.0,
                "is_ai_summary": True
            })
        
        # Add search results
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
def browse_page(url: str, max_chunk_size: int = 6000, overlap_sentences: int = 2) -> List[Dict[str, Any]]:
    """
    Browse and extract content from a webpage URL with automatic intelligent chunking for large pages.
    
    IMPORTANT TOKEN-SAVING BEHAVIOR:
    - Small pages (<6000 chars): Returns full content immediately in a single chunk with 'content' field
    - Large pages (>6000 chars): Returns ONLY PREVIEWS (800 chars each) to avoid token limits
    
    When multiple chunks are returned (large pages), each chunk contains:
    - preview: First 800 characters (for relevance checking ONLY - NOT for answering)
    - full_length: Total character count of the full chunk
    - chunk_id: Position indicator (e.g., "2/5")
    - status: "preview_only" - indicating you MUST call get_chunk_content for full text
    
    ⚠️ CRITICAL: Previews are NOT sufficient to answer questions. Always follow the workflow.
    
    WORKFLOW for large pages:
    1. browse_page returns chunk previews with status="preview_only"
    2. Call check_chunk_relevance on all previews in parallel to filter
    3. Call get_chunk_content to fetch full text of ONLY relevant chunks
    4. Generate answer ONLY from full content retrieved in step 3
    
    This prevents token limit errors by filtering BEFORE retrieving full content.
    
    Args:
        url: The URL of the webpage to browse
        max_chunk_size: Maximum characters per chunk (default: 6000)
        overlap_sentences: Number of sentences to overlap between chunks (default: 2)
        
    Returns:
        List of chunks. Each chunk has:
        - For small pages (single chunk): 'content' with full text, status not set
        - For large pages (multiple chunks): 'preview' with 800 chars, 'status'='preview_only', 'full_length'
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        import re
        
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
        phrases = (phrase.strip() for line in lines for phrase in line.split("  "))
        text_content = ' '.join(phrase for phrase in phrases if phrase)
        
        # If content fits within max_chunk_size, return as single chunk with full content
        if len(text_content) <= max_chunk_size:
            return [{
                "title": title_text,
                "content": text_content,
                "url": url,
                "chunk_id": "1/1",
                "instructions": "This is the complete page content.",
                "error": False
            }]
        
        # Large page: split into semantic chunks with overlap
        # Split text into sentences for semantic chunking
        sentences = re.split(r'(?<=[.!?])\s+', text_content)
        
        chunks = []
        chunk_full_contents = []  # Store full content separately
        current_chunk = []
        current_length = 0
        min_chunk_size = max_chunk_size // 2  # Ensure chunks aren't too small
        
        for i, sentence in enumerate(sentences):
            sentence_length = len(sentence)
            
            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_length += sentence_length + 1  # +1 for space
            
            # Check if we should finalize this chunk
            should_finalize = (
                current_length >= min_chunk_size and 
                current_length + sentence_length > max_chunk_size
            ) or i == len(sentences) - 1
            
            if should_finalize and current_chunk:
                # Create chunk text
                chunk_text = ' '.join(current_chunk)
                chunk_number = len(chunks) + 1
                
                # Store full content for later retrieval
                chunk_full_contents.append(chunk_text)
                
                # Create preview using constant
                content_preview = chunk_text[:PREVIEW_LENGTH]
                if len(chunk_text) > PREVIEW_LENGTH:
                    content_preview += TRUNCATION_MESSAGE
                
                chunks.append({
                    "title": f"{title_text} (Part {chunk_number})",
                    "preview": content_preview,  # Preview for relevance checking only
                    "full_length": len(chunk_text),  # Show how much content is available
                    "url": url,
                    "chunk_id": f"{chunk_number}/TBD",  # Will update total later
                    "status": "preview_only",  # Explicitly mark as incomplete
                    "instructions": f"⚠️ PREVIEW ONLY - NOT COMPLETE CONTENT ⚠️\nThis is a preview of part {chunk_number} of a large document. To get the full content:\n1. Call check_chunk_relevance(chunk_id='{chunk_number}/TBD', chunk_content=preview, user_query='your query') to determine if relevant\n2. If relevant, call get_chunk_content(url='{url}', chunk_id='{chunk_number}/TBD') to get full text\n3. Use full text from get_chunk_content to answer the question",
                    "error": False
                })
                
                # Prepare next chunk with overlap
                # Keep last N sentences for context
                if i < len(sentences) - 1:  # Not the last sentence
                    current_chunk = current_chunk[-overlap_sentences:] if len(current_chunk) > overlap_sentences else current_chunk
                    current_length = sum(len(s) + 1 for s in current_chunk)
                else:
                    current_chunk = []
                    current_length = 0
        
        # Update chunk_id with actual total count
        total_chunks = len(chunks)
        for chunk in chunks:
            chunk_num = chunk["chunk_id"].split("/")[0]
            chunk["chunk_id"] = f"{chunk_num}/{total_chunks}"
        
        # Store full content in a cache for retrieval (using URL as key)
        cache = _get_chunk_cache()
        cache[url] = chunk_full_contents
        
        return chunks if chunks else [{
            "title": title_text,
            "content": "Content extraction resulted in empty text.",
            "url": url,
            "chunk_id": "1/1",
            "instructions": "Page appears to be empty or content could not be extracted.",
            "error": False
        }]
    
    except ImportError:
        return [{
            "title": "Missing Dependencies",
            "content": "Required packages (requests, beautifulsoup4) not installed. Run: pip install requests beautifulsoup4",
            "url": url,
            "chunk_id": "1/1",
            "instructions": "Error occurred",
            "error": True
        }]
    except requests.exceptions.Timeout:
        return [{
            "title": "Timeout Error",
            "content": f"Request to {url} timed out after 10 seconds",
            "url": url,
            "chunk_id": "1/1",
            "instructions": "Error occurred",
            "error": True
        }]
    except requests.exceptions.HTTPError as e:
        return [{
            "title": "HTTP Error",
            "content": f"HTTP error occurred: {str(e)}",
            "url": url,
            "chunk_id": "1/1",
            "instructions": "Error occurred",
            "error": True
        }]
    except Exception as e:
        return [{
            "title": "Browse Error",
            "content": f"Error browsing page: {str(e)}",
            "url": url,
            "chunk_id": "1/1",
            "instructions": "Error occurred",
            "error": True
        }]


@tool
def get_chunk_content(url: str, chunk_id: str) -> Dict[str, Any]:
    """
    Retrieve the full content of a specific chunk from a previously browsed page.
    Use this AFTER check_chunk_relevance has identified relevant chunks.
    
    This tool fetches the complete text of chunks that were initially returned 
    as previews by browse_page to avoid token limit issues.
    
    Args:
        url: The URL of the page (must match the URL from browse_page)
        chunk_id: The chunk identifier (e.g., "2/5") from browse_page result
        
    Returns:
        Dictionary with:
        - chunk_id: The chunk identifier
        - content: Full content of the chunk
        - url: Source URL
        - success: Boolean indicating if retrieval was successful
    """
    try:
        # Access the cache using helper function
        cache = _get_chunk_cache()
        
        # Check if we have cached content for this URL
        if url not in cache:
            return {
                "chunk_id": chunk_id,
                "content": "",
                "url": url,
                "success": False,
                "error": "No cached content found for this URL. Please call browse_page first."
            }
        
        # Extract chunk number
        try:
            chunk_num = int(chunk_id.split('/')[0])
        except (ValueError, IndexError):
            return {
                "chunk_id": chunk_id,
                "content": "",
                "url": url,
                "success": False,
                "error": f"Invalid chunk_id format: {chunk_id}. Expected format like '2/5'."
            }
        
        # Get the content from cache (chunks are 1-indexed)
        cached_chunks = cache[url]
        if chunk_num < 1 or chunk_num > len(cached_chunks):
            return {
                "chunk_id": chunk_id,
                "content": "",
                "url": url,
                "success": False,
                "error": f"Chunk {chunk_num} not found. Available chunks: 1-{len(cached_chunks)}"
            }
        
        # Return the full content
        full_content = cached_chunks[chunk_num - 1]  # Convert to 0-indexed
        
        return {
            "chunk_id": chunk_id,
            "content": full_content,
            "url": url,
            "success": True,
            "length": len(full_content)
        }
        
    except Exception as e:
        return {
            "chunk_id": chunk_id,
            "content": "",
            "url": url,
            "success": False,
            "error": f"Error retrieving chunk content: {str(e)}"
        }


@tool
def check_chunk_relevance(chunk_id: str, chunk_content: str, user_query: str) -> Dict[str, Any]:
    """
    Check if a specific chunk from browse_page is relevant to the user's query.
    This tool works with both preview content and full content.
    Designed for parallel execution - call it on multiple chunks simultaneously
    to leverage vLLM's multi-query batching for efficient throughput.
    
    Use this tool when browse_page returns multiple chunks (chunk_id like "2/5" indicates multiple chunks).
    By checking relevance in parallel with previews, you avoid sending all full chunks to the model.
    
    After identifying relevant chunks, use get_chunk_content() to retrieve their full text.
    
    Args:
        chunk_id: The chunk identifier (e.g., "1/5", "2/5") from browse_page result
        chunk_content: The content to evaluate (can be preview or full content)
        user_query: The user's original question or query
        
    Returns:
        Dictionary with:
        - chunk_id: The chunk identifier
        - is_relevant: Boolean indicating if chunk is relevant
        - relevance_score: Float 0.0-1.0 indicating confidence
        - relevant_excerpts: List of relevant text excerpts if found
        - reasoning: Brief explanation of relevance decision
    """
    # Configuration constants
    RELEVANCE_THRESHOLD = 0.2  # Minimum score to consider chunk relevant
    MAX_EXCERPTS = 3  # Maximum number of excerpts to return
    
    try:
        # Simple keyword-based relevance check
        # In production, this could use embeddings or LLM-based relevance
        import re
        
        # Normalize texts for comparison
        query_lower = user_query.lower()
        content_lower = chunk_content.lower()
        
        # Special handling for structured document queries (chapters, paragraphs, sections)
        # Look for patterns like "kapitel 1", "1 kap", "paragraf 2", "§ 2", etc.
        structure_patterns = [
            r'kapitel\s*(\d+)', r'kap\.?\s*(\d+)', r'(\d+)\s*kap',
            r'paragraf\s*(\d+)', r'§\s*(\d+)', r'punkt\s*(\d+)',
            r'avsnitt\s*(\d+)', r'stycke\s*(\d+)'
        ]
        
        # Check if query is asking for a specific section/paragraph
        is_citation_query = any(re.search(pattern, query_lower) for pattern in structure_patterns)
        citation_boost = 0  # Initialize citation boost
        relevant_excerpts = []  # Initialize excerpts list
        
        if is_citation_query:
            # For citation queries, check if the content has matching section markers
            for pattern in structure_patterns:
                query_matches = re.findall(pattern, query_lower)
                content_matches = re.findall(pattern, content_lower)
                # If query asks for specific section numbers that appear in content
                if query_matches and any(qm in content_matches for qm in query_matches):
                    citation_boost = 0.5  # Strong boost for matching section numbers
                    relevant_excerpts.append(f"Found section marker matching query in content")
                    break
        
        # Extract key terms from query (simple approach)
        # Remove common Swedish and English stop words
        stop_words = {
            # Swedish stop words
            'och', 'i', 'på', 'att', 'en', 'är', 'som', 'för', 'det', 'av', 
            'till', 'med', 'om', 'den', 'kan', 'vad', 'hur', 'när', 'vilka',
            'från', 'citera', 'quote',  # Add citation-related words
            # English stop words
            'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'is', 'of', 'and', 'or'
        }
        query_words = [w for w in re.findall(r'\w+', query_lower) if len(w) > 2 and w not in stop_words]
        
        if not query_words:
            # If no meaningful words, consider relevant (conservative approach)
            return {
                "chunk_id": chunk_id,
                "is_relevant": True,
                "relevance_score": 0.5,
                "relevant_excerpts": [],
                "reasoning": "No specific keywords to match, treating as potentially relevant"
            }
        
        # Count how many query terms appear in chunk
        matches = 0
        
        for word in query_words:
            if word in content_lower:
                matches += 1
                # Find context around the match (50 chars before and after)
                pattern = re.compile(f'.{{0,50}}{re.escape(word)}.{{0,50}}', re.IGNORECASE)
                match_contexts = pattern.findall(chunk_content)
                if match_contexts:
                    # Add first match as excerpt
                    relevant_excerpts.append(match_contexts[0].strip())
        
        # Calculate relevance score
        relevance_score = min(matches / len(query_words), 1.0) if query_words else 0.5
        
        # Add citation boost if applicable
        relevance_score = min(relevance_score + citation_boost, 1.0)
        
        is_relevant = relevance_score > RELEVANCE_THRESHOLD
        
        # Deduplicate and limit excerpts
        relevant_excerpts = list(dict.fromkeys(relevant_excerpts))[:MAX_EXCERPTS]
        
        reasoning = f"Found {matches}/{len(query_words)} query terms in chunk. "
        if is_relevant:
            reasoning += "Chunk appears relevant to the query."
        else:
            reasoning += "Chunk does not appear relevant to the query."
        
        return {
            "chunk_id": chunk_id,
            "is_relevant": is_relevant,
            "relevance_score": round(relevance_score, 2),
            "relevant_excerpts": relevant_excerpts,
            "reasoning": reasoning
        }
    
    except Exception as e:
        # On error, be conservative and mark as relevant
        return {
            "chunk_id": chunk_id,
            "is_relevant": True,
            "relevance_score": 0.5,
            "relevant_excerpts": [],
            "reasoning": f"Error checking relevance: {str(e)}. Treating as potentially relevant.",
            "error": True
        }


@tool
def smhi_weather_forecast(location: str) -> Dict[str, Any]:
    """
    Get real-time weather forecast from SMHI (Swedish Meteorological and Hydrological Institute) for any location in Sweden.
    SMHI is the official weather authority in Sweden and provides accurate, authoritative forecasts.
    
    Args:
        location: Swedish city or location name (e.g., "Stockholm", "Göteborg", "Tidaholm")
        
    Returns:
        Dictionary with forecast information including temperature, weather description, and source URL
    """
    try:
        import requests
        from datetime import datetime
        
        # Simplified coordinate lookup for major Swedish cities
        # In production, you'd use a geocoding service
        city_coords = {
            "stockholm": (59.3293, 18.0686),
            "göteborg": (57.7089, 11.9746),
            "gothenburg": (57.7089, 11.9746),
            "malmö": (55.6050, 13.0038),
            "malmo": (55.6050, 13.0038),
            "uppsala": (59.8586, 17.6389),
            "västerås": (59.6099, 16.5448),
            "vasteras": (59.6099, 16.5448),
            "örebro": (59.2753, 15.2134),
            "orebro": (59.2753, 15.2134),
            "linköping": (58.4108, 15.6214),
            "linkoping": (58.4108, 15.6214),
            "helsingborg": (56.0465, 12.6945),
            "jönköping": (57.7826, 14.1618),
            "jonkoping": (57.7826, 14.1618),
            "norrköping": (58.5877, 16.1924),
            "norrkoping": (58.5877, 16.1924),
            "lund": (55.7047, 13.1910),
            "umeå": (63.8258, 20.2630),
            "umea": (63.8258, 20.2630),
            "gävle": (60.6749, 17.1413),
            "gavle": (60.6749, 17.1413),
            "borås": (57.7210, 12.9401),
            "boras": (57.7210, 12.9401),
            "eskilstuna": (59.3667, 16.5077),
            "södertälje": (59.1955, 17.6256),
            "sodertalje": (59.1955, 17.6256),
            "karlstad": (59.3793, 13.5036),
            "täby": (59.4439, 18.0687),
            "taby": (59.4439, 18.0687),
            "växjö": (56.8777, 14.8091),
            "vaxjo": (56.8777, 14.8091),
            "halmstad": (56.6745, 12.8577),
            "sundsvall": (62.3908, 17.3069),
            "luleå": (65.5848, 22.1547),
            "lulea": (65.5848, 22.1547),
            "trollhättan": (58.2837, 12.2886),
            "trollhattan": (58.2837, 12.2886),
            "östersund": (63.1767, 14.6361),
            "ostersund": (63.1767, 14.6361),
            "borlänge": (60.4858, 15.4362),
            "borlange": (60.4858, 15.4362),
            "falun": (60.6066, 15.6263),
            "kalmar": (56.6634, 16.3567),
            "kristianstad": (56.0294, 14.1567),
            "karlskrona": (56.1612, 15.5869),
            "skellefteå": (64.7507, 20.9527),
            "skelleftea": (64.7507, 20.9527),
            "tidaholm": (58.1814, 13.9570),
        }
        
        # Normalize location name
        location_lower = location.lower().strip()
        
        # Try to find coordinates
        lat, lon = city_coords.get(location_lower, (59.3293, 18.0686))  # Default to Stockholm
        
        # SMHI API endpoint for point forecast
        url = f"https://opendata-download-metfcst.smhi.se/api/category/pmp3g/version/2/geotype/point/lon/{lon}/lat/{lat}/data.json"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract forecast data
        if "timeSeries" not in data or not data["timeSeries"]:
            return {
                "title": "SMHI Data Unavailable",
                "content": f"Weather forecast data not available for {location}",
                "url": "https://opendata.smhi.se",
                "error": True
            }
        
        # Get the next few hours of forecast
        forecasts = []
        for i, time_point in enumerate(data["timeSeries"][:8]):  # Next 8 hours
            valid_time = time_point.get("validTime", "")
            parameters = {p["name"]: p["values"][0] for p in time_point.get("parameters", [])}
            
            temp = parameters.get("t", "N/A")  # Temperature
            weather_symbol = parameters.get("Wsymb2", 1)  # Weather symbol code
            
            # Simplified weather description mapping
            weather_descriptions = {
                1: "Klart",
                2: "Halvklart",
                3: "Molnigt",
                4: "Mulet",
                5: "Lätt regn",
                6: "Regn",
                7: "Kraftigt regn",
                8: "Lätt snö",
                9: "Snö",
                10: "Kraftig snö",
                11: "Duggregn"
            }
            
            weather_desc = weather_descriptions.get(int(weather_symbol), "Varierande")
            
            # Format time
            try:
                dt = datetime.fromisoformat(valid_time.replace("Z", "+00:00"))
                time_str = dt.strftime("%H:%M")
            except:
                time_str = valid_time
            
            forecasts.append(f"{time_str}: {temp}°C, {weather_desc}")
        
        forecast_text = "\n".join(forecasts[:4])  # Show next 4 hours
        
        content = f"Väderprogn för {location.title()} från SMHI:\n\n{forecast_text}\n\nKälla: Sveriges Meteorologiska och Hydrologiska Institut (SMHI)"
        
        return {
            "title": f"SMHI Väderprognos - {location.title()}",
            "content": content,
            "url": "https://opendata.smhi.se",
            "error": False
        }
    
    except requests.exceptions.Timeout:
        return {
            "title": "SMHI Timeout",
            "content": f"Request to SMHI API timed out. Please try again.",
            "url": "https://opendata.smhi.se",
            "error": True
        }
    except requests.exceptions.HTTPError as e:
        return {
            "title": "SMHI API Error",
            "content": f"Could not retrieve weather data from SMHI: {str(e)}",
            "url": "https://opendata.smhi.se",
            "error": True
        }
    except Exception as e:
        return {
            "title": "Weather Forecast Error",
            "content": f"Error getting weather forecast: {str(e)}",
            "url": "https://opendata.smhi.se",
            "error": True
        }


# Export all tools for easy access
AVAILABLE_TOOLS = [tavily_search, duckduckgo_search, vespa_search, browse_page, check_chunk_relevance, get_chunk_content, smhi_weather_forecast]
