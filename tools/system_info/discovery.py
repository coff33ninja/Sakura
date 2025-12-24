"""
System Discovery Tool for Sakura
Allows Sakura to discover system info, installed apps, and learn about the environment
"""
import asyncio
import os
import subprocess
import logging
import ctypes
import json
from typing import Dict, Any, Optional
from pathlib import Path
from ..base import BaseTool, ToolResult, ToolStatus


class SystemDiscovery(BaseTool):
    """Self-discovery tool - Sakura can learn about the system"""
    
    name = "system_info"
    description = "Discover system info: PC name, user, folders, installed apps, running processes, hardware. Use this to learn about the system!"
    
    def __init__(self):
        self._lock = asyncio.Lock()
        self.is_windows = os.name == 'nt'
        self._cache: Dict[str, Any] = {}
    
    async def initialize(self) -> bool:
        """Initialize system discovery"""
        logging.info("System discovery tool initialized")
        return True

    async def execute(self, action: str, **kwargs) -> ToolResult:
        """Execute system discovery action"""
        actions = {
            "get_pc_info": self._get_pc_info,
            "get_user_folders": self._get_user_folders,
            "list_installed_apps": self._list_installed_apps,
            "search_apps": self._search_apps,
            "get_running_apps": self._get_running_apps,
            "get_hardware": self._get_hardware,
            "get_network": self._get_network,
            "get_drives": self._get_drives,
            "get_environment": self._get_environment,
            "explore_folder": self._explore_folder,
            "find_app_path": self._find_app_path,
            "get_startup_apps": self._get_startup_apps,
            "get_recent_files": self._get_recent_files,
            "get_display_info": self._get_display_info,
            "get_audio_devices": self._get_audio_devices,
        }
        
        if action not in actions:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Unknown action: {action}. Available: {list(actions.keys())}"
            )
        
        return await actions[action](**kwargs)
    
    async def _run_ps(self, cmd: str, timeout: int = 30) -> Optional[str]:
        """Run PowerShell command and return output"""
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True, text=True, timeout=timeout
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None

    async def _get_pc_info(self) -> ToolResult:
        """Get basic PC information"""
        try:
            info = {
                "computer_name": os.environ.get('COMPUTERNAME', 'Unknown'),
                "username": os.environ.get('USERNAME', 'Unknown'),
                "os": os.environ.get('OS', 'Unknown'),
                "processor_arch": os.environ.get('PROCESSOR_ARCHITECTURE', 'Unknown'),
                "processor_id": os.environ.get('PROCESSOR_IDENTIFIER', 'Unknown'),
                "number_of_processors": os.environ.get('NUMBER_OF_PROCESSORS', 'Unknown'),
            }
            
            # Get OS version
            os_info = await self._run_ps("(Get-CimInstance Win32_OperatingSystem).Caption")
            if os_info:
                info["os_version"] = os_info
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=info,
                message=f"PC: {info['computer_name']}, User: {info['username']}"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _get_user_folders(self) -> ToolResult:
        """Get user's common folders"""
        try:
            home = Path.home()
            folders = {
                "home": str(home),
                "desktop": str(home / "Desktop"),
                "documents": str(home / "Documents"),
                "downloads": str(home / "Downloads"),
                "pictures": str(home / "Pictures"),
                "music": str(home / "Music"),
                "videos": str(home / "Videos"),
                "appdata": os.environ.get('APPDATA', ''),
                "localappdata": os.environ.get('LOCALAPPDATA', ''),
                "temp": os.environ.get('TEMP', ''),
            }
            
            # Check which exist
            existing = {k: v for k, v in folders.items() if Path(v).exists()}
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=existing,
                message=f"Found {len(existing)} user folders"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _list_installed_apps(self, category: str = "all") -> ToolResult:
        """List installed applications"""
        try:
            cmd = '''
            Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*,
            HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* 2>$null |
            Where-Object { $_.DisplayName -ne $null } |
            Select-Object DisplayName, Publisher, InstallLocation |
            Sort-Object DisplayName -Unique |
            ConvertTo-Json
            '''
            
            result = await self._run_ps(cmd)
            if result:
                apps = json.loads(result)
                if isinstance(apps, dict):
                    apps = [apps]
                
                # Filter by category if specified
                if category != "all":
                    category_filters = {
                        "browsers": ["Chrome", "Firefox", "Edge", "Opera", "Brave", "Vivaldi"],
                        "dev": ["Visual Studio", "Code", "Python", "Node", "Git", "Docker"],
                        "media": ["VLC", "Spotify", "iTunes", "Media Player", "OBS", "Audacity"],
                        "games": ["Steam", "Epic", "GOG", "Battle.net", "Origin", "Ubisoft"],
                        "communication": ["Discord", "Slack", "Teams", "Zoom", "Telegram"],
                    }
                    
                    if category in category_filters:
                        filters = category_filters[category]
                        apps = [a for a in apps if any(f.lower() in a.get('DisplayName', '').lower() for f in filters)]
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=apps[:50],  # Limit to 50
                    message=f"Found {len(apps)} installed apps"
                )
            
            return ToolResult(status=ToolStatus.ERROR, error="Could not retrieve apps")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _search_apps(self, query: str) -> ToolResult:
        """Search for installed apps by name"""
        try:
            cmd = f'''
            Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*,
            HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* 2>$null |
            Where-Object {{ $_.DisplayName -like "*{query}*" }} |
            Select-Object DisplayName, Publisher, InstallLocation, DisplayVersion |
            ConvertTo-Json
            '''
            
            result = await self._run_ps(cmd)
            if result:
                apps = json.loads(result)
                if isinstance(apps, dict):
                    apps = [apps]
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=apps,
                    message=f"Found {len(apps)} apps matching '{query}'"
                )
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=[],
                message=f"No apps found matching '{query}'"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def _get_running_apps(self) -> ToolResult:
        """Get currently running applications with windows"""
        try:
            cmd = '''
            Get-Process | Where-Object { $_.MainWindowTitle -ne "" } |
            Select-Object ProcessName, Id, MainWindowTitle, @{N='MemoryMB';E={[math]::Round($_.WorkingSet64/1MB,1)}} |
            ConvertTo-Json
            '''
            
            result = await self._run_ps(cmd)
            if result:
                apps = json.loads(result)
                if isinstance(apps, dict):
                    apps = [apps]
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=apps,
                    message=f"Found {len(apps)} running apps with windows"
                )
            
            return ToolResult(status=ToolStatus.SUCCESS, data=[], message="No windowed apps running")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _get_hardware(self) -> ToolResult:
        """Get hardware information"""
        try:
            cmd = '''
            $hw = @{
                CPU = (Get-CimInstance Win32_Processor).Name
                Cores = (Get-CimInstance Win32_Processor).NumberOfCores
                Threads = (Get-CimInstance Win32_Processor).NumberOfLogicalProcessors
                RAM_GB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)
                GPU = (Get-CimInstance Win32_VideoController).Name
                Motherboard = (Get-CimInstance Win32_BaseBoard).Product
                BIOS = (Get-CimInstance Win32_BIOS).SMBIOSBIOSVersion
            }
            $hw | ConvertTo-Json
            '''
            
            result = await self._run_ps(cmd)
            if result:
                hw = json.loads(result)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=hw,
                    message=f"CPU: {hw.get('CPU', 'Unknown')}, RAM: {hw.get('RAM_GB', '?')}GB"
                )
            
            return ToolResult(status=ToolStatus.ERROR, error="Could not get hardware info")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _get_network(self) -> ToolResult:
        """Get network information"""
        try:
            cmd = '''
            $net = @{
                Adapters = Get-NetAdapter | Where-Object Status -eq 'Up' | Select-Object Name, InterfaceDescription, MacAddress, LinkSpeed
                IPs = Get-NetIPAddress | Where-Object { $_.AddressFamily -eq 'IPv4' -and $_.IPAddress -notlike '127.*' } | Select-Object IPAddress, InterfaceAlias
                DNS = Get-DnsClientServerAddress | Where-Object { $_.ServerAddresses } | Select-Object InterfaceAlias, ServerAddresses
            }
            $net | ConvertTo-Json -Depth 3
            '''
            
            result = await self._run_ps(cmd)
            if result:
                net = json.loads(result)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=net,
                    message="Network info retrieved"
                )
            
            return ToolResult(status=ToolStatus.ERROR, error="Could not get network info")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _get_drives(self) -> ToolResult:
        """Get drive information"""
        try:
            cmd = '''
            Get-PSDrive -PSProvider FileSystem |
            Select-Object Name, @{N='UsedGB';E={[math]::Round($_.Used/1GB,1)}}, 
            @{N='FreeGB';E={[math]::Round($_.Free/1GB,1)}},
            @{N='TotalGB';E={[math]::Round(($_.Used+$_.Free)/1GB,1)}},
            Root |
            ConvertTo-Json
            '''
            
            result = await self._run_ps(cmd)
            if result:
                drives = json.loads(result)
                if isinstance(drives, dict):
                    drives = [drives]
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=drives,
                    message=f"Found {len(drives)} drives"
                )
            
            return ToolResult(status=ToolStatus.ERROR, error="Could not get drive info")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _get_environment(self, filter_key: str = "") -> ToolResult:
        """Get environment variables"""
        try:
            env_vars = dict(os.environ)
            
            if filter_key:
                env_vars = {k: v for k, v in env_vars.items() if filter_key.lower() in k.lower()}
            
            # Limit sensitive info
            safe_vars = {}
            sensitive = ['key', 'token', 'secret', 'password', 'credential']
            for k, v in env_vars.items():
                if any(s in k.lower() for s in sensitive):
                    safe_vars[k] = "[HIDDEN]"
                else:
                    safe_vars[k] = v[:200] if len(v) > 200 else v
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=safe_vars,
                message=f"Found {len(safe_vars)} environment variables"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def _explore_folder(self, path: str, depth: int = 1) -> ToolResult:
        """Explore a folder's contents"""
        try:
            folder = Path(path)
            if not folder.exists():
                return ToolResult(status=ToolStatus.ERROR, error=f"Path not found: {path}")
            
            if not folder.is_dir():
                return ToolResult(status=ToolStatus.ERROR, error=f"Not a directory: {path}")
            
            items = []
            for item in folder.iterdir():
                try:
                    info = {
                        "name": item.name,
                        "type": "folder" if item.is_dir() else "file",
                        "path": str(item),
                    }
                    if item.is_file():
                        info["size_kb"] = round(item.stat().st_size / 1024, 1)
                        info["extension"] = item.suffix
                    items.append(info)
                except PermissionError:
                    continue
            
            # Sort: folders first, then files
            items.sort(key=lambda x: (x['type'] != 'folder', x['name'].lower()))
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=items[:100],  # Limit to 100 items
                message=f"Found {len(items)} items in {folder.name}"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _find_app_path(self, app_name: str) -> ToolResult:
        """Find the executable path for an application"""
        try:
            found = []
            
            # Search in PATH first
            cmd = f'Get-Command "{app_name}" -ErrorAction SilentlyContinue | Select-Object Source | ConvertTo-Json'
            result = await self._run_ps(cmd)
            if result:
                try:
                    data = json.loads(result)
                    if isinstance(data, dict) and data.get('Source'):
                        found.append({"path": data['Source'], "source": "PATH"})
                    elif isinstance(data, list):
                        for d in data:
                            if d.get('Source'):
                                found.append({"path": d['Source'], "source": "PATH"})
                except json.JSONDecodeError:
                    pass
            
            # Search in Start Menu
            start_menu_paths = [
                Path(os.environ.get('APPDATA', '')) / "Microsoft/Windows/Start Menu/Programs",
                Path("C:/ProgramData/Microsoft/Windows/Start Menu/Programs"),
            ]
            
            for sm_path in start_menu_paths:
                if sm_path.exists():
                    for lnk in sm_path.rglob("*.lnk"):
                        if app_name.lower() in lnk.stem.lower():
                            found.append({"path": str(lnk), "source": "Start Menu"})
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=found[:10],
                message=f"Found {len(found)} matches for '{app_name}'"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _get_startup_apps(self) -> ToolResult:
        """Get apps that run at startup"""
        try:
            cmd = '''
            $startup = @()
            $startup += Get-ItemProperty "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" 2>$null | 
                Select-Object * -ExcludeProperty PS* | ForEach-Object { $_.PSObject.Properties | Where-Object { $_.Name -notlike 'PS*' } }
            $startup += Get-ItemProperty "HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" 2>$null |
                Select-Object * -ExcludeProperty PS* | ForEach-Object { $_.PSObject.Properties | Where-Object { $_.Name -notlike 'PS*' } }
            $startup | Select-Object Name, Value | ConvertTo-Json
            '''
            
            result = await self._run_ps(cmd)
            if result:
                apps = json.loads(result)
                if isinstance(apps, dict):
                    apps = [apps]
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=apps,
                    message=f"Found {len(apps)} startup apps"
                )
            
            return ToolResult(status=ToolStatus.SUCCESS, data=[], message="No startup apps found")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _get_recent_files(self, count: int = 20) -> ToolResult:
        """Get recently accessed files"""
        try:
            recent_path = Path(os.environ.get('APPDATA', '')) / "Microsoft/Windows/Recent"
            
            if not recent_path.exists():
                return ToolResult(status=ToolStatus.ERROR, error="Recent folder not found")
            
            files = []
            for item in sorted(recent_path.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:count]:
                if item.suffix == '.lnk':
                    files.append({
                        "name": item.stem,
                        "accessed": item.stat().st_mtime,
                    })
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=files,
                message=f"Found {len(files)} recent files"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _get_display_info(self) -> ToolResult:
        """Get display/monitor information"""
        try:
            if self.is_windows:
                user32 = ctypes.windll.user32
                width = user32.GetSystemMetrics(0)
                height = user32.GetSystemMetrics(1)
                
                cmd = '''
                Get-CimInstance Win32_VideoController | 
                Select-Object Name, CurrentHorizontalResolution, CurrentVerticalResolution, CurrentRefreshRate, AdapterRAM |
                ConvertTo-Json
                '''
                
                result = await self._run_ps(cmd)
                displays = []
                if result:
                    displays = json.loads(result)
                    if isinstance(displays, dict):
                        displays = [displays]
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={
                        "primary_resolution": f"{width}x{height}",
                        "displays": displays
                    },
                    message=f"Primary display: {width}x{height}"
                )
            
            return ToolResult(status=ToolStatus.ERROR, error="Not on Windows")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _get_audio_devices(self) -> ToolResult:
        """Get audio devices"""
        try:
            cmd = '''
            Get-CimInstance Win32_SoundDevice | 
            Select-Object Name, Status, Manufacturer |
            ConvertTo-Json
            '''
            
            result = await self._run_ps(cmd)
            if result:
                devices = json.loads(result)
                if isinstance(devices, dict):
                    devices = [devices]
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=devices,
                    message=f"Found {len(devices)} audio devices"
                )
            
            return ToolResult(status=ToolStatus.ERROR, error="Could not get audio devices")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    def get_schema(self) -> Dict[str, Any]:
        """Return schema for system discovery tools"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "get_pc_info", "get_user_folders", "list_installed_apps",
                            "search_apps", "get_running_apps", "get_hardware",
                            "get_network", "get_drives", "get_environment",
                            "explore_folder", "find_app_path", "get_startup_apps",
                            "get_recent_files", "get_display_info", "get_audio_devices"
                        ],
                        "description": "Discovery action to perform"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["all", "browsers", "dev", "media", "games", "communication"],
                        "description": "App category filter for list_installed_apps"
                    },
                    "query": {"type": "string", "description": "Search query for search_apps"},
                    "path": {"type": "string", "description": "Folder path for explore_folder"},
                    "depth": {"type": "integer", "description": "Exploration depth", "default": 1},
                    "app_name": {"type": "string", "description": "App name for find_app_path"},
                    "filter_key": {"type": "string", "description": "Filter for environment variables"},
                    "count": {"type": "integer", "description": "Number of recent files", "default": 20}
                },
                "required": ["action"]
            }
        }
    
    async def cleanup(self):
        """Cleanup"""
        self._cache.clear()
