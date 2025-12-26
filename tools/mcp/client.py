"""
MCP Client for Sakura
Connects to MCP servers to extend Sakura's capabilities - fully async

Supports:
- uvx (Python) servers - requires uv installed
- npx (Node.js) servers - requires Node.js installed
- SSE (HTTP) servers
"""
import asyncio
import logging
import json
import os
import shutil
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
        self.server_tools: Dict[str, List[Dict[str, Any]]] = {}
        self._lock = asyncio.Lock()
        self.http_client: Optional[httpx.AsyncClient] = None
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        self._has_uvx = False
        self._has_npx = False
    
    async def initialize(self) -> bool:
        """Initialize MCP connections from config"""
        async with self._lock:
            # Check for uvx and npx availability
            self._has_uvx = shutil.which("uvx") is not None
            self._has_npx = shutil.which("npx") is not None
            
            if not self._has_uvx:
                logging.warning("uvx not found - Python MCP servers disabled. Install uv: https://docs.astral.sh/uv/")
            if not self._has_npx:
                logging.warning("npx not found - Node.js MCP servers disabled. Install Node.js: https://nodejs.org/")
            
            # Load config from environment or file
            config_path = os.getenv("MCP_CONFIG_PATH", "mcp_config.json")
            
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        content = f.read()
                        self.server_config = json.loads(content)
                    
                    # Validate config structure
                    if not isinstance(self.server_config, dict):
                        raise ValueError("MCP config must be a JSON object")
                    
                    logging.info(f"✅ Loaded MCP config from {config_path}")
                except json.JSONDecodeError as e:
                    logging.error(f"❌ Invalid JSON in MCP config: {e}")
                    self.server_config = {}
                except Exception as e:
                    logging.error(f"❌ Failed to load MCP config: {e}")
                    self.server_config = {}
            else:
                logging.debug(f"No MCP config found at {config_path} - using defaults")
            
            # Initialize HTTP client for SSE servers
            self.http_client = httpx.AsyncClient(timeout=60.0)
            
            # Connect to configured servers
            servers = self.server_config.get("servers", {})
            if not isinstance(servers, dict):
                logging.error(f"❌ MCP 'servers' field must be an object, got {type(servers).__name__}")
                servers = {}
            
            for server_name, config in servers.items():
                if server_name.startswith("_"):
                    continue
                await self._connect_server(server_name, config)
            
            logging.info(f"✅ MCP client initialized: {len(self.connected_servers)} server(s)")
        return True
    
    async def _connect_server(self, name: str, config: Dict[str, Any]) -> bool:
        """Connect to a single MCP server with validation"""
        # Validate config structure
        if not isinstance(config, dict):
            logging.error(f"❌ MCP server '{name}' config must be an object, got {type(config).__name__}")
            return False
        
        server_type = config.get("type", "stdio")
        command = config.get("command", [])
        
        # Validate required fields
        if server_type == "stdio" and not command:
            logging.error(f"❌ MCP server '{name}' type='stdio' requires 'command' field")
            return False
        
        if server_type == "sse" and not config.get("url"):
            logging.error(f"❌ MCP server '{name}' type='sse' requires 'url' field")
            return False
        
        if command:
            cmd = command[0] if isinstance(command, list) else command
            if cmd == "uvx" and not self._has_uvx:
                logging.warning(f"⚠️  Skipping {name}: uvx not available (install uv)")
                return False
            if cmd == "npx" and not self._has_npx:
                logging.warning(f"⚠️  Skipping {name}: npx not available (install Node.js)")
                return False
        
        try:
            if server_type == "stdio":
                return await self._connect_stdio(name, config)
            elif server_type == "sse":
                return await self._connect_sse(name, config)
            else:
                logging.error(f"❌ Unknown MCP server type '{server_type}' for {name}")
                return False
        except Exception as e:
            logging.error(f"❌ Failed to connect to MCP server {name}: {e}")
            return False
    
    async def _connect_stdio(self, name: str, config: Dict[str, Any]) -> bool:
        """Connect to stdio-based MCP server"""
        command = config.get("command", [])
        if not command or not isinstance(command, list):
            logging.error(f"Invalid command format for {name}: must be a list")
            return False
        
        # Validate that all command elements are strings
        if not all(isinstance(arg, str) for arg in command):
            logging.error(f"Invalid command arguments for {name}: all must be strings")
            return False
        
        env = os.environ.copy()
        if "env" in config:
            env.update(config["env"])
        
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            self._processes[name] = process
            self.connected_servers[name] = {
                "type": "stdio",
                "process": process,
                "config": config
            }
            
            await asyncio.sleep(0.5)
            
            if process.returncode is not None:
                stderr = await process.stderr.read()
                logging.error(f"MCP server {name} exited: {stderr.decode()[:200]}")
                return False
            
            tools = await self._get_server_tools_stdio(name)
            self.server_tools[name] = tools
            
            logging.info(f"Connected to MCP server {name}: {len(tools)} tools")
            return True
            
        except FileNotFoundError:
            logging.error(f"MCP server {name} command not found: {command[0]}")
            return False
        except Exception as e:
            logging.error(f"Failed to start MCP server {name}: {e}")
            return False

    async def _connect_sse(self, name: str, config: Dict[str, Any]) -> bool:
        """Connect to SSE-based MCP server"""
        url = config.get("url", "")
        if not url:
            return False
        
        try:
            response = await self.http_client.get(f"{url}/health")
            if response.status_code == 200:
                self.connected_servers[name] = {
                    "type": "sse",
                    "url": url,
                    "config": config
                }
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
            # Initialize MCP protocol
            init_request = json.dumps({
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "sakura", "version": "1.1.0"}
                },
                "id": 0
            }) + "\n"
            process.stdin.write(init_request.encode())
            await process.stdin.drain()
            
            await self._read_response(process, timeout=10.0)
            
            # Send initialized notification
            initialized = json.dumps({
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }) + "\n"
            process.stdin.write(initialized.encode())
            await process.stdin.drain()
            
            # Request tools list
            request = json.dumps({"jsonrpc": "2.0", "method": "tools/list", "id": 1}) + "\n"
            process.stdin.write(request.encode())
            await process.stdin.drain()
            
            response = await self._read_response(process, timeout=10.0)
            if response:
                return response.get("result", {}).get("tools", [])
            
        except asyncio.TimeoutError:
            logging.warning(f"Timeout getting tools from {name}")
        except Exception as e:
            logging.error(f"Error getting tools from {name}: {e}")
        
        return []
    
    async def _read_response(self, process: asyncio.subprocess.Process, timeout: float = 30.0) -> Optional[Dict]:
        """Read JSON-RPC response, handling multi-line and initialization messages"""
        try:
            end_time = asyncio.get_event_loop().time() + timeout
            
            while asyncio.get_event_loop().time() < end_time:
                remaining = end_time - asyncio.get_event_loop().time()
                if remaining <= 0:
                    break
                
                try:
                    response_line = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=min(remaining, 5.0)
                    )
                except asyncio.TimeoutError:
                    continue
                
                if not response_line:
                    continue
                
                line = response_line.decode().strip()
                if not line:
                    continue
                
                try:
                    response = json.loads(line)
                    if "id" in response or "result" in response:
                        return response
                except json.JSONDecodeError:
                    continue
            
        except Exception as e:
            logging.debug(f"Read response error: {e}")
        
        return None
    
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

    async def execute(self, action: str = "call", server: str = "", tool: str = "", **kwargs) -> ToolResult:
        """Execute MCP action"""
        actions = {
            "call": self._call_tool,
            "list_servers": self._list_servers,
            "list_tools": self._list_tools,
        }
        
        if action not in actions:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Unknown action: {action}. Available: {list(actions.keys())}"
            )
        
        return await actions[action](server=server, tool=tool, **kwargs)
    
    async def _call_tool(self, server: str, tool: str, **kwargs) -> ToolResult:
        """Call a tool on an MCP server"""
        async with self._lock:
            if server not in self.connected_servers:
                available = list(self.connected_servers.keys())
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Server not connected: {server}. Available: {available}"
                )
            
            server_info = self.connected_servers[server]
            args = {k: v for k, v in kwargs.items() if k not in ["action", "server", "tool"]}
            
            try:
                if server_info["type"] == "stdio":
                    return await self._execute_stdio(server, tool, args)
                elif server_info["type"] == "sse":
                    return await self._execute_sse(server, tool, args)
                else:
                    return ToolResult(status=ToolStatus.ERROR, error="Unknown server type")
            except Exception as e:
                logging.error(f"MCP tool execution error: {e}")
                return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _list_servers(self, **kwargs) -> ToolResult:
        """List connected MCP servers"""
        servers = []
        for name, info in self.connected_servers.items():
            tool_count = len(self.server_tools.get(name, []))
            servers.append({"name": name, "type": info["type"], "tools": tool_count})
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=servers,
            message=f"Connected to {len(servers)} MCP servers"
        )
    
    async def _list_tools(self, server: str = "", **kwargs) -> ToolResult:
        """List tools available on a server or all servers"""
        if server:
            tools = self.server_tools.get(server, [])
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=tools,
                message=f"{len(tools)} tools on {server}"
            )
        else:
            all_tools = {}
            for srv, tools in self.server_tools.items():
                all_tools[srv] = [t.get("name", "unknown") for t in tools]
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=all_tools,
                message=f"Tools from {len(all_tools)} servers"
            )
    
    async def _execute_stdio(self, server: str, tool: str, args: Dict[str, Any]) -> ToolResult:
        """Execute tool on stdio MCP server"""
        process = self._processes.get(server)
        if not process:
            return ToolResult(status=ToolStatus.ERROR, error="Process not found")
        
        if process.returncode is not None:
            return ToolResult(status=ToolStatus.ERROR, error="Server process has exited")
        
        try:
            request = json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": tool, "arguments": args},
                "id": 2
            }) + "\n"
            
            process.stdin.write(request.encode())
            await process.stdin.drain()
            
            response = await self._read_response(process, timeout=60.0)
            
            if not response:
                return ToolResult(status=ToolStatus.ERROR, error="No response from server")
            
            if "error" in response:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=response["error"].get("message", "Unknown error")
                )
            
            result = response.get("result", {})
            content = result.get("content", result)
            
            if isinstance(content, list):
                texts = [c.get("text", str(c)) for c in content if isinstance(c, dict)]
                content = "\n".join(texts) if texts else str(content)
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=content,
                message=f"Executed {tool} on {server}"
            )
            
        except asyncio.TimeoutError:
            return ToolResult(status=ToolStatus.ERROR, error="Execution timeout (60s)")
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
                return ToolResult(status=ToolStatus.ERROR, error=f"HTTP {response.status_code}")
                
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    def get_schema(self) -> Dict[str, Any]:
        """Return tool schema for Gemini function calling"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["call", "list_servers", "list_tools"],
                        "description": "MCP action to perform"
                    },
                    "server": {
                        "type": "string",
                        "description": "MCP server name (for call/list_tools)"
                    },
                    "tool": {
                        "type": "string",
                        "description": "Tool name to call on the server"
                    }
                },
                "required": ["action"]
            }
        }
    
    async def cleanup(self) -> None:
        """Cleanup all MCP connections and processes"""
        async with self._lock:
            # Terminate all stdio processes
            for name, process in self._processes.items():
                try:
                    if process.returncode is None:
                        process.terminate()
                        try:
                            await asyncio.wait_for(process.wait(), timeout=5.0)
                        except asyncio.TimeoutError:
                            process.kill()
                        logging.info(f"Terminated MCP server: {name}")
                except Exception as e:
                    logging.warning(f"Error terminating {name}: {e}")
            
            self._processes.clear()
            self.connected_servers.clear()
            self.server_tools.clear()
            
            # Close HTTP client
            if self.http_client:
                await self.http_client.aclose()
                self.http_client = None
            
            logging.info("MCP client cleanup complete")
