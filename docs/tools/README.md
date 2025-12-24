# Sakura Tools Documentation

Tools are the action capabilities of Sakura - they allow her to interact with the system, web, and external services.

## Tool Categories

| Tool | Actions | Description |
|------|---------|-------------|
| [windows](windows.md) | 46 | Windows automation, mouse, keyboard, apps, files |
| [developer](developer.md) | 33 | Git, code execution, packages, SSH |
| [productivity](productivity.md) | 23 | Reminders, timers, notes, to-do |
| [system_info](system_info.md) | 15 | Hardware, apps, network discovery |
| [memory](memory.md) | 16 | Persistent memory storage |
| [web](web.md) | 2 | Web search and URL fetching |
| [discord](discord.md) | 5 | Discord text and voice |
| [smart_home](smart_home.md) | 6 | Home Assistant integration |
| [mcp](mcp.md) | 3 | MCP server connections |

**Total: 149 tool actions**

## Architecture

All tools inherit from `BaseTool` in `tools/base.py`:

```python
class BaseTool:
    name: str           # Tool identifier
    description: str    # What the tool does
    
    async def initialize(self) -> bool
    async def execute(self, action: str, **kwargs) -> ToolResult
    async def cleanup(self)
```

## Rules

1. **Async Everything** - All tools use `asyncio.Lock()` for thread safety
2. **aiofiles** - All file I/O uses aiofiles
3. **All Imports Used** - No unused imports allowed
4. **Graceful Degradation** - Tools fail gracefully when optional features unavailable
