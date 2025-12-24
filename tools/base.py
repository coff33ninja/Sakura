"""
Base tool classes for Sakura's tool system
All tools use async/aio patterns
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional, List, Callable
from enum import Enum

class ToolStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"

@dataclass
class ToolResult:
    """Result from a tool execution"""
    status: ToolStatus
    data: Any = None
    message: str = ""
    error: Optional[str] = None

class BaseTool(ABC):
    """Base class for all Sakura tools - fully async"""
    
    name: str = "base_tool"
    description: str = "Base tool"
    enabled: bool = True
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters"""
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Return the tool's parameter schema for Gemini function calling"""
        pass
    
    async def initialize(self) -> bool:
        """Initialize the tool (override if needed)"""
        return True
    
    async def cleanup(self):
        """Cleanup resources (override if needed)"""
        pass
    
    async def run_in_executor(self, func: Callable, *args) -> Any:
        """Run blocking function in executor"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args)

class ToolRegistry:
    """Registry for managing available tools - fully async"""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._lock = asyncio.Lock()
    
    async def register(self, tool: BaseTool):
        """Register a tool"""
        async with self._lock:
            self._tools[tool.name] = tool
            logging.info(f"Registered tool: {tool.name}")
    
    async def unregister(self, name: str):
        """Unregister a tool"""
        async with self._lock:
            if name in self._tools:
                del self._tools[name]
                logging.info(f"Unregistered tool: {name}")
    
    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """List all registered tool names"""
        return list(self._tools.keys())
    
    def get_enabled_tools(self) -> List[BaseTool]:
        """Get all enabled tools"""
        return [t for t in self._tools.values() if t.enabled]
    
    def get_schemas(self) -> List[Dict[str, Any]]:
        """Get schemas for all enabled tools (for Gemini function calling)"""
        return [t.get_schema() for t in self.get_enabled_tools()]
    
    async def initialize_all(self) -> Dict[str, bool]:
        """Initialize all tools concurrently"""
        async def init_tool(name: str, tool: BaseTool) -> tuple:
            try:
                result = await tool.initialize()
                return (name, result)
            except Exception as e:
                logging.error(f"Failed to initialize {name}: {e}")
                return (name, False)
        
        tasks = [init_tool(name, tool) for name, tool in self._tools.items()]
        results = await asyncio.gather(*tasks)
        return dict(results)
    
    async def cleanup_all(self):
        """Cleanup all tools concurrently"""
        async def cleanup_tool(tool: BaseTool):
            try:
                await tool.cleanup()
            except Exception as e:
                logging.error(f"Error cleaning up {tool.name}: {e}")
        
        tasks = [cleanup_tool(tool) for tool in self._tools.values()]
        await asyncio.gather(*tasks)
    
    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool by name"""
        tool = self.get(tool_name)
        if not tool:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Tool not found: {tool_name}"
            )
        if not tool.enabled:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Tool disabled: {tool_name}"
            )
        return await tool.execute(**kwargs)
