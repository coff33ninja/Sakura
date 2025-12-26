"""
Sakura Tools Package
Extensible tools and integrations for Sakura AI
"""

from .base import BaseTool, ToolResult, ToolStatus, ToolRegistry

# Import all tools
from .web import WebSearch, WebFetch
from .smart_home import SmartHomeController
from .memory import MemoryStore
from .discord import DiscordBot
from .mcp import MCPClient
from .windows import WindowsAutomation
from .system_info import SystemDiscovery
from .productivity import ProductivityManager
from .developer import DeveloperTools
from .meta import MetaTools

__all__ = [
    # Base classes
    'BaseTool',
    'ToolResult',
    'ToolStatus',
    'ToolRegistry',
    # Web tools
    'WebSearch',
    'WebFetch',
    # Smart home
    'SmartHomeController',
    # Memory
    'MemoryStore',
    # Discord
    'DiscordBot',
    # MCP
    'MCPClient',
    # Windows
    'WindowsAutomation',
    # System Discovery
    'SystemDiscovery',
    # Productivity
    'ProductivityManager',
    # Developer
    'DeveloperTools',
    # Meta (self-introspection)
    'MetaTools',
]


async def create_tool_registry() -> ToolRegistry:
    """Create and initialize a registry with all available tools"""
    registry = ToolRegistry()
    
    # Register all tools
    await registry.register(WebSearch())
    await registry.register(WebFetch())
    await registry.register(SmartHomeController())
    await registry.register(MemoryStore())
    await registry.register(DiscordBot())
    await registry.register(MCPClient())
    await registry.register(WindowsAutomation())
    await registry.register(SystemDiscovery())
    await registry.register(ProductivityManager())
    await registry.register(DeveloperTools())
    
    # Meta tools need registry reference for introspection
    meta_tools = MetaTools(tool_registry=registry)
    await registry.register(meta_tools)
    
    # Initialize all tools
    await registry.initialize_all()
    
    return registry
