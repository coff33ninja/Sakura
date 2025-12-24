# MCP Client Tool

**File:** `tools/mcp/client.py`  
**Actions:** 3

Connect to Model Context Protocol servers for extended capabilities.

## Actions

| Action | Description |
|--------|-------------|
| `list_servers` | List connected MCP servers |
| `list_tools` | List tools from a server |
| `call_tool` | Call a tool on an MCP server |

## Configuration

Create `mcp_config.json`:
```json
{
  "servers": {
    "example-server": {
      "type": "stdio",
      "command": ["uvx", "example-mcp-server"]
    },
    "http-server": {
      "type": "sse",
      "url": "http://localhost:8080/sse"
    }
  }
}
```

Set path in `.env`:
```env
MCP_CONFIG_PATH=mcp_config.json
```

## Server Types

### stdio
Runs MCP server as subprocess, communicates via stdin/stdout.

```json
{
  "type": "stdio",
  "command": ["uvx", "server-name"]
}
```

### sse
Connects to HTTP-based MCP server via Server-Sent Events.

```json
{
  "type": "sse",
  "url": "http://localhost:8080/sse"
}
```

## Example Usage

```python
# List connected servers
result = await tool.execute("list_servers")

# List tools from a server
result = await tool.execute("list_tools", server="example-server")

# Call a tool
result = await tool.execute("call_tool",
    server="example-server",
    tool="search",
    args={"query": "test"}
)
```

## Tool Discovery

On connection, the client queries each server for available tools and caches them in `server_tools` dict.

## Known Issues

- Some uvx servers may timeout on first connection
- JSON parse errors can occur with malformed server responses
- Node.js required for npx-based servers
