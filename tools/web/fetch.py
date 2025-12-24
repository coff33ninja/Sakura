"""
Web Fetch Tool for Sakura
Fetch and extract content from URLs - fully async
"""
import asyncio
import logging
import re
from typing import Dict, Any, Optional
import httpx
from ..base import BaseTool, ToolResult, ToolStatus

class WebFetch(BaseTool):
    """Fetch and read web pages - async"""
    
    name = "web_fetch"
    description = "Fetch and read content from a URL"
    
    def __init__(self):
        self.client: Optional[httpx.AsyncClient] = None
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> bool:
        """Initialize async HTTP client"""
        async with self._lock:
            self.client = httpx.AsyncClient(
                timeout=15.0,
                follow_redirects=True,
                headers={"User-Agent": "Sakura-AI/1.0"}
            )
            logging.info("Web fetch initialized (async)")
        return True
    
    async def execute(self, url: str, extract_text: bool = True) -> ToolResult:
        """Fetch a web page and optionally extract text"""
        async with self._lock:
            if not self.client:
                await self.initialize()
        
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            
            content = response.text
            
            if extract_text:
                # Run text extraction in executor (CPU-bound)
                content = await self.run_in_executor(self._extract_text, content)
            
            # Truncate if too long
            max_length = 4000
            if len(content) > max_length:
                content = content[:max_length] + "... [truncated]"
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "url": str(response.url),
                    "content": content,
                    "status_code": response.status_code,
                    "content_type": response.headers.get("content-type", "")
                },
                message=f"Fetched {len(content)} characters from {url}"
            )
            
        except httpx.HTTPError as e:
            logging.error(f"Fetch HTTP error: {e}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
                message=f"Failed to fetch {url}"
            )
        except Exception as e:
            logging.error(f"Fetch error: {e}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
                message="Fetch failed"
            )
    
    def _extract_text(self, html: str) -> str:
        """Extract readable text from HTML (CPU-bound, run in executor)"""
        # Remove script and style elements
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html)
        
        # Decode HTML entities
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'&lt;', '<', text)
        text = re.sub(r'&gt;', '>', text)
        text = re.sub(r'&quot;', '"', text)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"},
                    "extract_text": {"type": "boolean", "description": "Extract text only", "default": True}
                },
                "required": ["url"]
            }
        }
    
    async def cleanup(self):
        """Close async HTTP client"""
        async with self._lock:
            if self.client:
                await self.client.aclose()
                self.client = None
