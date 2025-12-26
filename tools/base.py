"""
Base tool classes for Sakura's tool system
All tools use async/aio patterns
"""
import asyncio
import logging
import time
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


@dataclass
class ToolDependency:
    """Represents a tool's optional external dependency"""
    name: str  # Human-readable name (e.g., "discord.py")
    pip_package: str  # Package to install (e.g., "discord.py[voice]")
    import_name: str  # Module to import (e.g., "discord")
    optional: bool = True  # If False, tool cannot function without it


@dataclass
class ToolMetrics:
    """Metrics for a tool's execution performance"""
    execution_count: int = 0  # Total times tool was executed
    success_count: int = 0  # Successful executions
    error_count: int = 0  # Failed executions
    total_duration: float = 0.0  # Total execution time in seconds
    
    @property
    def average_duration(self) -> float:
        """Average execution time"""
        if self.execution_count == 0:
            return 0.0
        return self.total_duration / self.execution_count
    
    @property
    def success_rate(self) -> float:
        """Success rate as a percentage (0-100)"""
        if self.execution_count == 0:
            return 0.0
        return (self.success_count / self.execution_count) * 100


class BaseTool(ABC):
    """Base class for all Sakura tools - fully async"""
    
    name: str = "base_tool"
    description: str = "Base tool"
    enabled: bool = True
    dependencies: List[ToolDependency] = []  # Override in subclasses
    
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
    
    async def check_dependencies(self) -> Dict[str, bool]:
        """
        Check if all dependencies are available.
        
        Returns:
            Dict mapping dependency names to availability status
        """
        results = {}
        for dep in self.dependencies:
            try:
                __import__(dep.import_name)
                results[dep.name] = True
            except ImportError:
                results[dep.name] = False
                if not dep.optional:
                    logging.error(
                        f"{self.name} requires {dep.name}. "
                        f"Install with: pip install {dep.pip_package}"
                    )
                else:
                    logging.warning(
                        f"{self.name} optional feature {dep.name} unavailable. "
                        f"Install with: pip install {dep.pip_package}"
                    )
        return results


class ToolRegistry:
    """Registry for managing available tools - fully async"""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._lock = asyncio.Lock()
        self._metrics: Dict[str, ToolMetrics] = {}  # Track metrics per tool
    
    async def register(self, tool: BaseTool):
        """Register a tool"""
        async with self._lock:
            self._tools[tool.name] = tool
            self._metrics[tool.name] = ToolMetrics()  # Initialize metrics
            logging.info(f"Registered tool: {tool.name}")
    
    async def unregister(self, name: str):
        """Unregister a tool"""
        async with self._lock:
            if name in self._tools:
                del self._tools[name]
                if name in self._metrics:
                    del self._metrics[name]
                logging.info(f"Unregistered tool: {name}")
    
    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        return self._tools.get(name)
    
    def get_metrics(self, tool_name: Optional[str] = None) -> Dict[str, ToolMetrics]:
        """
        Get metrics for a specific tool or all tools.
        
        Args:
            tool_name: If provided, return metrics for just this tool. Otherwise return all.
        
        Returns:
            Dict mapping tool names to their ToolMetrics
        """
        if tool_name:
            return {tool_name: self._metrics.get(tool_name, ToolMetrics())}
        return dict(self._metrics)
    
    def list_tools(self) -> List[str]:
        """List all registered tool names"""
        return list(self._tools.keys())
    
    def get_enabled_tools(self) -> List[BaseTool]:
        """Get all enabled tools"""
        return [t for t in self._tools.values() if t.enabled]
    
    def get_schemas(self) -> List[Dict[str, Any]]:
        """Get schemas for all enabled tools (for Gemini function calling)"""
        schemas = []
        for tool in self.get_enabled_tools():
            schema = tool.get_schema()
            
            # Add run_in_background parameter to all tools
            # This lets Gemini decide based on user intent whether to run in background
            if 'parameters' in schema and 'properties' in schema['parameters']:
                schema['parameters']['properties']['run_in_background'] = {
                    "type": "boolean",
                    "description": "Set to true to run this task in the background. Use when: user says 'let me know when done', 'while I do something else', 'in the background', or for long operations like searching all drives. The user can continue chatting while the task runs, and will be notified when complete.",
                    "default": False
                }
            
            schemas.append(schema)
        return schemas
    
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
        """Execute a tool by name with metrics tracking"""
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
        
        # Track metrics
        metrics = self._metrics.get(tool_name, ToolMetrics())
        start_time = time.time()
        
        try:
            result = await tool.execute(**kwargs)
            
            # Update metrics
            metrics.execution_count += 1
            if result.status == ToolStatus.SUCCESS:
                metrics.success_count += 1
            else:
                metrics.error_count += 1
            
            duration = time.time() - start_time
            metrics.total_duration += duration
            
            # Log performance for slow operations (>2 seconds)
            if duration > 2.0:
                logging.warning(
                    f"Tool {tool_name} took {duration:.2f}s to execute. "
                    f"Metrics: {metrics.execution_count} calls, "
                    f"{metrics.success_rate:.1f}% success rate, "
                    f"{metrics.average_duration:.2f}s avg duration"
                )
            
            return result
        except Exception as e:
            metrics.execution_count += 1
            metrics.error_count += 1
            duration = time.time() - start_time
            metrics.total_duration += duration
            
            logging.error(f"Tool {tool_name} crashed: {e}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Tool execution failed: {str(e)}"
            )
