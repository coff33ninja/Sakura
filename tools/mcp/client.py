"""
MCP Client for Sakura
Connects to MCP servers to extend Sakura's capabilities - fully async
"""
import asyncio
import logging
import json
import os
from typing import Dict, Any, List, Optional
import httpx
from ..base import BaseTool, ToolResult, ToolStatus

class MCPClient(BaseTool):
    """MCP client for connecting to MCP servers - async with stdio/SSE support"""
    
    name = "mcp_client"
    description = "Connect to MCP servers for extended tools"
    
    def __init__(self, server_config: Optional[Dict[str, Any]] = None):
        self.server_config = server_config or {}
        self.connected_servers: Dict[str, Any] = {}
        self.server_tools: Dict[str, List[Dict[str, Any]]] = {}  # Tools per server
        self._lock = asyncio.Lock()
        self.http_client: Optional[httpx.AsyncClient] = None
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
    
    async def initialize(self) -> bool:
        """Initialize MCP connections from config"""
        async with self._lock:
            # Load config from environment or file
            config_path = os.getenv("MCP_CONFIG_PATH", "mcp_config.json")
            
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        self.server_config = json.load(f)
                    logging.info(f"Loaded MCP config from {config_path}")
                except Exception as e:
                    logging.error(f"Failed to load MCP config: {e}")
            
            # Initialize HTTP client for SSE servers
            self.http_client = httpx.AsyncClient(timeout=30.0)
            
            # Connect to configured servers
            for server_name, config in self.server_config.get("servers", {}).items():
                await self._connect_server(server_name, config)
            
            logging.info(f"MCP client initialized (async): {len(self.connected_servers)} servers")
        return True
    
    async def _connect_server(self, name: str, config: Dict[str, Any]) -> bool:
        """Connect to a single MCP server"""
        server_type = config.get("type", "stdio")
        
        try:
            if server_type == "stdio":
                return await self._connect_stdio(name, config)
            elif server_type == "sse":
                return await self._connect_sse(name, config)
            else:
                logging.warning(f"Unknown MCP server type: {server_type}")
                return False
        except Exception as e:
            logging.error(f"Failed to connect to MCP server {name}: {e}")
            return False
    
    async def _connect_stdio(self, name: str, config: Dict[str, Any]) -> bool:
        """Connect to stdio-based MCP server"""
        command = config.get("command", [])
        if not command:
            return False
        
        try:
            # Start the MCP server process
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            self._processes[name] = process
            self.connected_servers[name] = {
                "type": "stdio",
                "process": process,
                "config": config
            }
            
            # Get available tools from server
            tools = await self._get_server_tools_stdio(name)
            self.server_tools[name] = tools
            
            logging.info(f"Connected to MCP server {name} (stdio): {len(tools)} tools")
            return True
            
        except Exception as e:
            logging.error(f"Failed to start MCP server {name}: {e}")
            return False
    
    async def _connect_sse(self, name: str, config: Dict[str, Any]) -> bool:
        """Connect to SSE-based MCP server"""
        url = config.get("url", "")
        if not url:
            return False
        
        try:
            # Test connection
            response = await self.http_client.get(f"{url}/health")
            if response.status_code == 200:
                self.connected_servers[name] = {
                    "type": "sse",
                    "url": url,
                    "config": config
                }
                
                # Get available tools
                tools = await self._get_server_tools_sse(name, url)
                self.server_tools[name] = tools
                
                logging.info(f"Connected to MCP server {name} (SSE): {len(tools)} tools")
                return True
        except Exception as e:
            logging.error(f"Failed to connect to SSE server {name}: {e}")
        
        return False
    
    async def _get_server_tools_stdio(self, name: str) -> List[Dict[str, Any]]:
        """Get tools from stdio MCP server"""
        server = self.connected_servers.get(name)
        if not server or server["type"] != "stdio":
            return []
        
        process = server["process"]
        
        try:
            # Send tools/list request
            request = json.dumps({"jsonrpc": "2.0", "method": "tools/list", "id": 1}) + "\n"
            process.stdin.write(request.encode())
            await process.stdin.drain()
            
            # Read response with timeout
            response_line = await asyncio.wait_for(
                process.stdout.readline(),
                timeout=5.0
            )
            
            response = json.loads(response_line.decode())
            return response.get("result", {}).get("tools", [])
            
        except asyncio.TimeoutError:
            logging.warning(f"Timeout getting tools from {name}")
        except Exception as e:
            logging.error(f"Error getting tools from {name}: {e}")
        
        return []
    
    async def _get_server_tools_sse(self, name: str, url: str) -> List[Dict[str, Any]]:
        """Get tools from SSE MCP server"""
        try:
            response = await self.http_client.post(
                f"{url}/tools/list",
                json={"jsonrpc": "2.0", "method": "tools/list", "id": 1}
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("result", {}).get("tools", [])
        except Exception as e:
            logging.error(f"Error getting tools from SSE server {name}: {e}")
        
        return []
    
    async def execute(self, server: str, tool: str, **kwargs) -> ToolResult:
        """Execute a tool on an MCP server - async"""
        async with self._lock:
            if server not in self.connected_servers:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Server not connected: {server}",
                    message="MCP server not found"
                )
            
            server_info = self.connected_servers[server]
            
            try:
                if server_info["type"] == "stdio":
                    return await self._execute_stdio(server, tool, kwargs)
                elif server_info["type"] == "sse":
                    return await self._execute_sse(server, tool, kwargs)
                else:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error="Unknown server type"
                    )
            except Exception as e:
                logging.error(f"MCP tool execution error: {e}")
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=str(e),
                    message="Tool execution failed"
                )
    
    async def _execute_stdio(self, server: str, tool: str, args: Dict[str, Any]) -> ToolResult:
        """Execute tool on stdio MCP server"""
        process = self._processes.get(server)
        if not process:
            return ToolResult(status=ToolStatus.ERROR, error="Process not found")
        
        try:
            request = json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": tool, "arguments": args},
                "id": 2
            }) + "\n"
            
            process.stdin.write(request.encode())
            await process.stdin.drain()
            
            response_line = await asyncio.wait_for(
                process.stdout.readline(),
                timeout=30.0
            )
            
            response = json.loads(response_line.decode())
            
            if "error" in response:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=response["error"].get("message", "Unknown error")
                )
            
            result = response.get("result", {})
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=result.get("content", result),
                message=f"Executed {tool} on {server}"
            )
            
        except asyncio.TimeoutError:
            return ToolResult(status=ToolStatus.ERROR, error="Execution timeout")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _execute_sse(self, server: str, tool: str, args: Dict[str, Any]) -> ToolResult:
        """Execute tool on SSE MCP server"""
        server_info = self.connected_servers.get(server)
        if not server_info:
            return ToolResult(status=ToolStatus.ERROR, error="Server not found")
        
        url = server_info["url"]
        
        try:
            response = await self.http_client.post(
                f"{url}/tools/call",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {"name": tool, "arguments": args},
                    "id": 2
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if "error" in data:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error=data["error"].get("message", "Unknown error")
                    )
                
                result = data.get("result", {})
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=result.get("content", result),
                    message=f"Executed {tool} on {server}"
                )
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"HTTP {response.status_code}"
                )
                
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    def get_schema(self) -> Dict[str, Any]:
        """Return schema for MCP tool calls"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "server": {"type": "string", "description": "MCP server name"},
                    "tool": {"type": "string", "description": "Tool to execute"},
                    "args": {"type": "object", "description": "Tool arguments"}
                },
                "required": ["server", "tool"]
            }
        }
    
    async def list_servers(self) -> List[str]:
        """List connected MCP servers - async"""
        async with self._lock:
            return list(self.connected_servers.keys())
    
    async def list_server_tools(self, server: str) -> List[Dict[str, Any]]:
        """List tools available on a server - async"""
        async with self._lock:
            return self.server_tools.get(server, [])
    
    async def get_all_tools(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all tools from all servers - async"""
        async with self._lock:
            return self.server_tools.copy()
    
    async def cleanup(self):
        """Disconnect from all MCP servers - async"""
        async with self._lock:
            # Terminate stdio processes
            for name, process in self._processes.items():
                try:
                    process.terminate()
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except Exception as e:
                    logging.error(f"Error terminating MCP server {name}: {e}")
                    process.kill()
            
            self._processes.clear()
            self.connected_servers.clear()
            self.server_tools.clear()
            
            # Close HTTP client
            if self.http_client:
                await self.http_client.aclose()
                self.http_client = None
            
            logging.info("MCP client cleanup completed")
