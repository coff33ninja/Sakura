"""
Web Search Tool for Sakura
Uses DuckDuckGo for free web search - fully async
Implements rate limiting to prevent IP blocks
"""
import asyncio
import logging
import time
import urllib.parse
from typing import Dict, Any, Optional, List
import httpx
from ..base import BaseTool, ToolResult, ToolStatus

class WebSearch(BaseTool):
    """Web search capabilities using DuckDuckGo - async"""
    
    name = "web_search"
    description = "Search the web for information"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key  # Reserved for future paid APIs
        self.client: Optional[httpx.AsyncClient] = None
        self._lock = asyncio.Lock()
        self._last_request_time: float = 0.0
        self._min_interval: float = 1.0  # Minimum 1 second between requests to prevent IP blocks
    
    async def initialize(self) -> bool:
        """Initialize async HTTP client"""
        async with self._lock:
            self.client = httpx.AsyncClient(
                timeout=10.0,
                headers={"User-Agent": "Sakura-AI/1.0"}
            )
            logging.info("Web search initialized (async) with rate limiting (1s interval)")
        return True
    
    async def execute(self, query: str, num_results: int = 5) -> ToolResult:
        """Search the web using DuckDuckGo instant answers"""
        async with self._lock:
            if not self.client:
                await self.initialize()
            
            # Rate limiting: ensure minimum interval between requests
            elapsed = time.time() - self._last_request_time
            if elapsed < self._min_interval:
                wait_time = self._min_interval - elapsed
                logging.debug(f"Rate limit: waiting {wait_time:.2f}s before search")
                await asyncio.sleep(wait_time)
        
        try:
            # Update last request time
            async with self._lock:
                self._last_request_time = time.time()
            
            # DuckDuckGo Instant Answer API (free, no key needed)
            encoded_query = urllib.parse.quote(query)
            url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1"
            
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            
            results: List[Dict[str, str]] = []
            
            # Abstract (main answer)
            if data.get("Abstract"):
                results.append({
                    "title": data.get("Heading", "Answer"),
                    "snippet": data["Abstract"],
                    "url": data.get("AbstractURL", "")
                })
            
            # Related topics
            for topic in data.get("RelatedTopics", [])[:num_results]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append({
                        "title": topic.get("Text", "")[:50],
                        "snippet": topic.get("Text", ""),
                        "url": topic.get("FirstURL", "")
                    })
            
            if not results:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=[],
                    message=f"No results found for: {query}"
                )
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=results[:num_results],
                message=f"Found {len(results)} results for: {query}"
            )
            
        except httpx.HTTPError as e:
            logging.error(f"Search HTTP error: {e}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
                message="Search request failed"
            )
        except Exception as e:
            logging.error(f"Search error: {e}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
                message="Search failed"
            )
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "num_results": {"type": "integer", "description": "Number of results", "default": 5}
                },
                "required": ["query"]
            }
        }
    
    async def cleanup(self):
        """Close async HTTP client"""
        async with self._lock:
            if self.client:
                await self.client.aclose()
                self.client = None
