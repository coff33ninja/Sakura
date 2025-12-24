# Web Tools

**Files:** `tools/web/search.py`, `tools/web/fetch.py`  
**Actions:** 2

Web search and URL content fetching.

## Actions

| Action | Description |
|--------|-------------|
| `search` | Search the web via DuckDuckGo |
| `fetch` | Fetch and extract content from URL |

## Web Search

Uses DuckDuckGo Instant Answer API (free, no API key needed).

```python
result = await tool.execute(query="Python asyncio tutorial", num_results=5)
```

Returns:
```python
{
    "results": [
        {
            "title": "Answer title",
            "snippet": "Answer content...",
            "url": "https://..."
        }
    ]
}
```

## Web Fetch

Fetches URL content and extracts text.

```python
result = await tool.execute(url="https://example.com")
```

Returns:
```python
{
    "title": "Page Title",
    "content": "Extracted text content...",
    "url": "https://example.com"
}
```

## Configuration

Both tools use `httpx.AsyncClient` with:
- 10 second timeout
- Custom User-Agent: `Sakura-AI/1.0`

## Example Usage

```python
# Search for information
search_tool = WebSearch()
await search_tool.initialize()
result = await search_tool.execute("latest Python version")

# Fetch page content
fetch_tool = WebFetch()
await fetch_tool.initialize()
result = await fetch_tool.execute(url="https://docs.python.org")
```
