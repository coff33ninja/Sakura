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
            "find_file": self._find_file,
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
        """List installed applications from all registry locations"""
        try:
            cmd = '''
            $results = @()
            $regPaths = @(
                "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*",
                "HKLM:\\SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*",
                "HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*"
            )
            
            foreach ($regPath in $regPaths) {
                Get-ItemProperty $regPath -ErrorAction SilentlyContinue | Where-Object {
                    $_.DisplayName -ne $null
                } | ForEach-Object {
                    $results += @{
                        DisplayName = $_.DisplayName
                        Publisher = $_.Publisher
                        InstallLocation = $_.InstallLocation
                        DisplayVersion = $_.DisplayVersion
                    }
                }
            }
            
            $results | Sort-Object DisplayName -Unique | ConvertTo-Json -Depth 2
            '''
            
            result = await self._run_ps(cmd, timeout=60)
            if result:
                apps = json.loads(result)
                if isinstance(apps, dict):
                    apps = [apps]
                
                # Filter out empty entries
                apps = [a for a in apps if a.get('DisplayName')]
                
                # Filter by category if specified
                if category != "all":
                    category_filters = {
                        "browsers": ["Chrome", "Firefox", "Edge", "Opera", "Brave", "Vivaldi", "Safari", "Chromium"],
                        "dev": ["Visual Studio", "Code", "Python", "Node", "Git", "Docker", "JetBrains", "IntelliJ", "PyCharm", "WebStorm", "Android Studio", "Xcode", "Eclipse", "NetBeans", "Sublime", "Atom", "Notepad++"],
                        "media": ["VLC", "Spotify", "iTunes", "Media Player", "OBS", "Audacity", "Foobar", "Winamp", "AIMP", "MusicBee", "Plex", "Kodi", "MPV", "PotPlayer", "KMPlayer", "DaVinci", "Premiere", "After Effects", "Photoshop", "GIMP", "Paint"],
                        "games": ["Steam", "Epic", "GOG", "Battle.net", "Origin", "Ubisoft", "EA App", "Riot", "Xbox", "PlayStation", "Rockstar", "Bethesda"],
                        "communication": ["Discord", "Slack", "Teams", "Zoom", "Telegram", "WhatsApp", "Skype", "Signal", "Viber", "WeChat"],
                        "office": ["Microsoft Office", "Word", "Excel", "PowerPoint", "Outlook", "OneNote", "LibreOffice", "OpenOffice", "WPS", "Google Docs"],
                        "utilities": ["7-Zip", "WinRAR", "CCleaner", "Malwarebytes", "Avast", "AVG", "Norton", "Kaspersky", "TeamViewer", "AnyDesk", "PuTTY", "FileZilla", "WinSCP"],
                    }
                    
                    if category in category_filters:
                        filters = category_filters[category]
                        apps = [a for a in apps if any(f.lower() in a.get('DisplayName', '').lower() for f in filters)]
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=apps[:100],  # Limit to 100
                    message=f"Found {len(apps)} installed apps" + (f" in category '{category}'" if category != "all" else "")
                )
            
            return ToolResult(status=ToolStatus.ERROR, error="Could not retrieve apps")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _search_apps(self, query: str) -> ToolResult:
        """Search for installed apps by name across all registry locations"""
        try:
            cmd = f'''
            $results = @()
            $regPaths = @(
                "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*",
                "HKLM:\\SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*",
                "HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*"
            )
            
            foreach ($regPath in $regPaths) {{
                Get-ItemProperty $regPath -ErrorAction SilentlyContinue | Where-Object {{
                    $_.DisplayName -like "*{query}*"
                }} | ForEach-Object {{
                    $results += @{{
                        DisplayName = $_.DisplayName
                        Publisher = $_.Publisher
                        InstallLocation = $_.InstallLocation
                        DisplayVersion = $_.DisplayVersion
                        UninstallString = $_.UninstallString
                        DisplayIcon = $_.DisplayIcon
                    }}
                }}
            }}
            
            # Also check App Paths registry
            $appPaths = "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths"
            Get-ChildItem $appPaths -ErrorAction SilentlyContinue | Where-Object {{
                $_.PSChildName -like "*{query}*"
            }} | ForEach-Object {{
                $default = (Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).'(default)'
                if ($default) {{
                    $results += @{{
                        DisplayName = $_.PSChildName
                        InstallLocation = $default
                        Source = "App Paths"
                    }}
                }}
            }}
            
            $results | Sort-Object DisplayName -Unique | ConvertTo-Json -Depth 2
            '''
            
            result = await self._run_ps(cmd, timeout=30)
            if result:
                apps = json.loads(result)
                if isinstance(apps, dict):
                    apps = [apps]
                
                # Filter out empty entries
                apps = [a for a in apps if a.get('DisplayName')]
                
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
    
    async def _get_hardware(self, detail_level: str = "basic") -> ToolResult:
        """Get hardware information
        
        Args:
            detail_level: "basic" for summary, "full" for detailed specs
        """
        try:
            if detail_level == "full":
                # Detailed hardware info
                cmd = '''
                $hw = @{}
                
                # CPU Details
                $cpu = Get-CimInstance Win32_Processor
                $hw.CPU = @{
                    Name = $cpu.Name
                    Manufacturer = $cpu.Manufacturer
                    Cores = $cpu.NumberOfCores
                    Threads = $cpu.NumberOfLogicalProcessors
                    MaxClockSpeedMHz = $cpu.MaxClockSpeed
                    CurrentClockSpeedMHz = $cpu.CurrentClockSpeed
                    L2CacheKB = $cpu.L2CacheSize
                    L3CacheKB = $cpu.L3CacheSize
                    Architecture = $cpu.Architecture
                    Socket = $cpu.SocketDesignation
                }
                
                # RAM Details
                $ram = Get-CimInstance Win32_PhysicalMemory
                $hw.RAM = @{
                    TotalGB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 2)
                    Slots = @()
                }
                foreach ($stick in $ram) {
                    $hw.RAM.Slots += @{
                        CapacityGB = [math]::Round($stick.Capacity / 1GB, 2)
                        SpeedMHz = $stick.Speed
                        Manufacturer = $stick.Manufacturer
                        PartNumber = $stick.PartNumber.Trim()
                        FormFactor = switch ($stick.FormFactor) {
                            8 { "DIMM" }
                            12 { "SODIMM" }
                            default { $stick.FormFactor }
                        }
                        MemoryType = switch ($stick.SMBIOSMemoryType) {
                            20 { "DDR" }
                            21 { "DDR2" }
                            22 { "DDR2 FB-DIMM" }
                            24 { "DDR3" }
                            26 { "DDR4" }
                            34 { "DDR5" }
                            default { "Type $($stick.SMBIOSMemoryType)" }
                        }
                        BankLabel = $stick.BankLabel
                        DeviceLocator = $stick.DeviceLocator
                    }
                }
                
                # GPU Details - use nvidia-smi for accurate VRAM on NVIDIA cards
                $gpus = Get-CimInstance Win32_VideoController
                $hw.GPU = @()
                
                # Try nvidia-smi for NVIDIA GPUs (more accurate VRAM)
                $nvidiaSmi = $null
                try {
                    $nvidiaSmi = nvidia-smi --query-gpu=name,memory.total,driver_version,temperature.gpu,utilization.gpu,power.draw --format=csv,noheader,nounits 2>$null
                } catch {}
                
                $nvidiaInfo = @{}
                if ($nvidiaSmi) {
                    $lines = $nvidiaSmi -split "`n"
                    foreach ($line in $lines) {
                        if ($line.Trim()) {
                            $parts = $line -split ","
                            if ($parts.Count -ge 2) {
                                $gpuName = $parts[0].Trim()
                                $nvidiaInfo[$gpuName] = @{
                                    VRAM_MB = [int]$parts[1].Trim()
                                    DriverVersion = if ($parts.Count -ge 3) { $parts[2].Trim() } else { $null }
                                    Temperature = if ($parts.Count -ge 4) { $parts[3].Trim() } else { $null }
                                    Utilization = if ($parts.Count -ge 5) { $parts[4].Trim() } else { $null }
                                    PowerDraw = if ($parts.Count -ge 6) { $parts[5].Trim() } else { $null }
                                }
                            }
                        }
                    }
                }
                
                foreach ($gpu in $gpus) {
                    $gpuData = @{
                        Name = $gpu.Name
                        Manufacturer = $gpu.AdapterCompatibility
                        DriverVersion = $gpu.DriverVersion
                        DriverDate = $gpu.DriverDate
                        CurrentResolution = "$($gpu.CurrentHorizontalResolution)x$($gpu.CurrentVerticalResolution)"
                        RefreshRate = $gpu.CurrentRefreshRate
                        VideoProcessor = $gpu.VideoProcessor
                        Status = $gpu.Status
                    }
                    
                    # Use nvidia-smi data if available for this GPU
                    if ($nvidiaInfo.ContainsKey($gpu.Name)) {
                        $nv = $nvidiaInfo[$gpu.Name]
                        $gpuData.VRAM_GB = [math]::Round($nv.VRAM_MB / 1024, 2)
                        $gpuData.VRAM_MB = $nv.VRAM_MB
                        if ($nv.Temperature) { $gpuData.Temperature_C = [int]$nv.Temperature }
                        if ($nv.Utilization) { $gpuData.Utilization_Percent = [int]$nv.Utilization }
                        if ($nv.PowerDraw) { $gpuData.PowerDraw_W = [math]::Round([double]$nv.PowerDraw, 1) }
                    } else {
                        # Fallback to WMI (may be inaccurate for >4GB)
                        $gpuData.VRAM_GB = [math]::Round($gpu.AdapterRAM / 1GB, 2)
                        $gpuData.VRAM_Note = "WMI value - may be inaccurate for GPUs >4GB"
                    }
                    
                    $hw.GPU += $gpuData
                }
                
                # Motherboard
                $mb = Get-CimInstance Win32_BaseBoard
                $hw.Motherboard = @{
                    Manufacturer = $mb.Manufacturer
                    Product = $mb.Product
                    SerialNumber = $mb.SerialNumber
                    Version = $mb.Version
                }
                
                # BIOS
                $bios = Get-CimInstance Win32_BIOS
                $hw.BIOS = @{
                    Manufacturer = $bios.Manufacturer
                    Version = $bios.SMBIOSBIOSVersion
                    ReleaseDate = $bios.ReleaseDate
                    SerialNumber = $bios.SerialNumber
                }
                
                # Storage
                $disks = Get-CimInstance Win32_DiskDrive
                $hw.Storage = @()
                foreach ($disk in $disks) {
                    $hw.Storage += @{
                        Model = $disk.Model
                        SizeGB = [math]::Round($disk.Size / 1GB, 2)
                        InterfaceType = $disk.InterfaceType
                        MediaType = $disk.MediaType
                        SerialNumber = $disk.SerialNumber
                        Partitions = $disk.Partitions
                    }
                }
                
                # Battery (for laptops)
                $battery = Get-CimInstance Win32_Battery
                if ($battery) {
                    $hw.Battery = @{
                        Name = $battery.Name
                        Status = $battery.Status
                        EstimatedChargeRemaining = $battery.EstimatedChargeRemaining
                        BatteryStatus = switch ($battery.BatteryStatus) {
                            1 { "Discharging" }
                            2 { "AC Power" }
                            3 { "Fully Charged" }
                            4 { "Low" }
                            5 { "Critical" }
                            default { $battery.BatteryStatus }
                        }
                    }
                }
                
                $hw | ConvertTo-Json -Depth 4
                '''
            else:
                # Basic hardware info
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
            
            result = await self._run_ps(cmd, timeout=60)
            if result:
                hw = json.loads(result)
                
                if detail_level == "full":
                    # Build summary message
                    cpu_name = hw.get('CPU', {}).get('Name', 'Unknown')
                    ram_total = hw.get('RAM', {}).get('TotalGB', '?')
                    gpu_list = hw.get('GPU', [])
                    gpu_name = gpu_list[0].get('Name', 'Unknown') if gpu_list else 'Unknown'
                    msg = f"CPU: {cpu_name}, RAM: {ram_total}GB, GPU: {gpu_name}"
                else:
                    msg = f"CPU: {hw.get('CPU', 'Unknown')}, RAM: {hw.get('RAM_GB', '?')}GB"
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=hw,
                    message=msg
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
    
    async def _find_app_path(self, app_name: str, search_drive: str = None) -> ToolResult:
        """Find the executable path for an application
        
        Args:
            app_name: Name of the application to find
            search_drive: Optional drive letter to search (e.g., "D", "E:")
        """
        try:
            found = []
            app_lower = app_name.lower()
            
            # Normalize drive letter
            if search_drive:
                search_drive = search_drive.rstrip(':').upper() + ":"
            
            # 1. Search in PATH first (fastest)
            cmd = f'Get-Command "{app_name}*" -ErrorAction SilentlyContinue | Select-Object Source | ConvertTo-Json'
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
            
            # 2. Check App Paths registry (Windows app registration)
            app_paths_cmd = f'''
            $paths = @()
            $appPaths = "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths"
            Get-ChildItem $appPaths -ErrorAction SilentlyContinue | ForEach-Object {{
                $name = $_.PSChildName
                if ($name -like "*{app_name}*") {{
                    $default = (Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).'(default)'
                    if ($default) {{ $paths += @{{ Name = $name; Path = $default }} }}
                }}
            }}
            $paths | ConvertTo-Json
            '''
            result = await self._run_ps(app_paths_cmd)
            if result:
                try:
                    data = json.loads(result)
                    if isinstance(data, dict) and data.get('Path'):
                        found.append({"path": data['Path'], "source": "App Paths Registry"})
                    elif isinstance(data, list):
                        for d in data:
                            if d.get('Path'):
                                found.append({"path": d['Path'], "source": "App Paths Registry"})
                except json.JSONDecodeError:
                    pass
            
            # 3. Search Registry Uninstall keys for InstallLocation
            reg_cmd = f'''
            $results = @()
            $regPaths = @(
                "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*",
                "HKLM:\\SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*",
                "HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*"
            )
            foreach ($regPath in $regPaths) {{
                Get-ItemProperty $regPath -ErrorAction SilentlyContinue | Where-Object {{
                    $_.DisplayName -like "*{app_name}*" -and $_.InstallLocation
                }} | ForEach-Object {{
                    $results += @{{
                        Name = $_.DisplayName
                        InstallLocation = $_.InstallLocation
                        DisplayIcon = $_.DisplayIcon
                    }}
                }}
            }}
            $results | ConvertTo-Json
            '''
            result = await self._run_ps(reg_cmd)
            if result:
                try:
                    data = json.loads(result)
                    if isinstance(data, dict):
                        data = [data]
                    for d in data:
                        if d.get('InstallLocation'):
                            install_path = Path(d['InstallLocation'])
                            found.append({
                                "path": str(install_path),
                                "name": d.get('Name', ''),
                                "source": "Registry InstallLocation"
                            })
                            # Try to find exe in install location
                            if install_path.exists():
                                for exe in install_path.glob("*.exe"):
                                    if app_lower in exe.stem.lower():
                                        found.append({
                                            "path": str(exe),
                                            "source": "Registry InstallLocation (exe)"
                                        })
                        # Also check DisplayIcon which often points to exe
                        if d.get('DisplayIcon'):
                            icon_path = d['DisplayIcon'].split(',')[0].strip('"')
                            if icon_path.lower().endswith('.exe') and Path(icon_path).exists():
                                found.append({
                                    "path": icon_path,
                                    "source": "Registry DisplayIcon"
                                })
                except json.JSONDecodeError:
                    pass
            
            # 4. Search in Start Menu shortcuts
            start_menu_paths = [
                Path(os.environ.get('APPDATA', '')) / "Microsoft/Windows/Start Menu/Programs",
                Path("C:/ProgramData/Microsoft/Windows/Start Menu/Programs"),
            ]
            
            for sm_path in start_menu_paths:
                if sm_path.exists():
                    for lnk in sm_path.rglob("*.lnk"):
                        if app_lower in lnk.stem.lower():
                            # Try to resolve shortcut target
                            resolve_cmd = f'''
                            $shell = New-Object -ComObject WScript.Shell
                            $shortcut = $shell.CreateShortcut("{str(lnk)}")
                            $shortcut.TargetPath
                            '''
                            target = await self._run_ps(resolve_cmd)
                            if target and Path(target).exists():
                                found.append({"path": target, "source": "Start Menu (resolved)"})
                            else:
                                found.append({"path": str(lnk), "source": "Start Menu"})
            
            # 5. Search common installation directories on all available drives
            # Get all drives
            if search_drive:
                drives_to_search = [search_drive]
            else:
                # Get all fixed drives
                drives_result = await self._run_ps(
                    "Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Free -ne $null } | Select-Object -ExpandProperty Root"
                )
                if drives_result:
                    drives_to_search = [d.strip().rstrip('\\') for d in drives_result.split('\n') if d.strip()]
                else:
                    drives_to_search = ["C:"]
            
            # Common installation directories (will be checked on each drive)
            common_subdirs = [
                "Program Files",
                "Program Files (x86)",
                "Programs",
                "Apps",
                "Applications",
                "Software",
                "Tools",
                "Utilities",
                "Games",
                "SteamLibrary\\steamapps\\common",
                "GOG Games",
                "Epic Games",
            ]
            
            for drive in drives_to_search:
                for subdir in common_subdirs:
                    base = Path(f"{drive}\\{subdir}")
                    if base.exists():
                        try:
                            for folder in base.iterdir():
                                if folder.is_dir() and app_lower in folder.name.lower():
                                    found.append({
                                        "path": str(folder),
                                        "source": f"{drive}\\{subdir}"
                                    })
                                    # Look for exe inside
                                    try:
                                        for exe in folder.glob("*.exe"):
                                            if app_lower in exe.stem.lower():
                                                found.append({
                                                    "path": str(exe),
                                                    "source": f"{drive}\\{subdir} (exe)"
                                                })
                                                break
                                    except PermissionError:
                                        pass
                        except PermissionError:
                            pass
            
            # Add user-specific paths
            user_paths = [
                os.path.expandvars("%LOCALAPPDATA%\\Programs"),
                os.path.expandvars("%LOCALAPPDATA%"),
                os.path.expandvars("%APPDATA%"),
                os.path.expandvars("%USERPROFILE%"),
            ]
            
            for base_path in user_paths:
                base = Path(base_path)
                if base.exists():
                    try:
                        for folder in base.iterdir():
                            if folder.is_dir() and app_lower in folder.name.lower():
                                found.append({
                                    "path": str(folder),
                                    "source": f"User ({base.name})"
                                })
                                # Look for exe inside
                                try:
                                    for exe in folder.glob("*.exe"):
                                        if app_lower in exe.stem.lower():
                                            found.append({
                                                "path": str(exe),
                                                "source": f"User ({base.name}) exe"
                                            })
                                            break
                                except PermissionError:
                                    pass
                    except PermissionError:
                        pass
            
            # 6. If user specified a drive, do a broader search on that drive
            if search_drive:
                drive_search_cmd = f'''
                $results = @()
                $searchPath = "{search_drive}\\"
                
                # Search top-level folders and one level deep
                Get-ChildItem $searchPath -Directory -ErrorAction SilentlyContinue | ForEach-Object {{
                    if ($_.Name -like "*{app_name}*") {{
                        $results += $_.FullName
                        # Look for exe
                        Get-ChildItem $_.FullName -Filter "*.exe" -ErrorAction SilentlyContinue | 
                            Where-Object {{ $_.Name -like "*{app_name}*" }} |
                            ForEach-Object {{ $results += $_.FullName }}
                    }}
                    # Check one level deeper
                    Get-ChildItem $_.FullName -Directory -ErrorAction SilentlyContinue | ForEach-Object {{
                        if ($_.Name -like "*{app_name}*") {{
                            $results += $_.FullName
                            Get-ChildItem $_.FullName -Filter "*.exe" -ErrorAction SilentlyContinue |
                                Where-Object {{ $_.Name -like "*{app_name}*" }} |
                                ForEach-Object {{ $results += $_.FullName }}
                        }}
                    }}
                }}
                $results | ConvertTo-Json
                '''
                result = await self._run_ps(drive_search_cmd, timeout=30)
                if result:
                    try:
                        data = json.loads(result)
                        if isinstance(data, str):
                            data = [data]
                        for path in data:
                            if path:
                                found.append({"path": path, "source": f"Drive Search ({search_drive})"})
                    except json.JSONDecodeError:
                        pass
            
            # Deduplicate by path
            seen = set()
            unique_found = []
            for item in found:
                path_lower = item['path'].lower()
                if path_lower not in seen:
                    seen.add(path_lower)
                    unique_found.append(item)
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=unique_found[:20],
                message=f"Found {len(unique_found)} matches for '{app_name}'" + (f" on {search_drive}" if search_drive else "")
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _find_file(self, name: str, file_type: str = "any", search_path: str = None, max_results: int = 20) -> ToolResult:
        """Find any file by name - executables, documents, images, videos, music, or any file type
        
        Args:
            name: Name or partial name to search for
            file_type: Type of file to find: "any", "exe", "document", "image", "video", "audio", "archive", "code"
            search_path: Specific path to search (drive letter like "D:" or full path). Searches all drives if not specified.
            max_results: Maximum number of results to return (default 20)
        """
        try:
            name_lower = name.lower()
            found = []
            
            # Define file extensions by type
            type_extensions = {
                "exe": [".exe", ".msi", ".bat", ".cmd", ".ps1", ".com", ".scr"],
                "document": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".rtf", ".odt", ".ods", ".odp", ".csv", ".md", ".epub"],
                "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico", ".tiff", ".tif", ".raw", ".psd", ".ai"],
                "video": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpeg", ".mpg", ".3gp"],
                "audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a", ".opus", ".aiff"],
                "archive": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso"],
                "code": [".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".cs", ".go", ".rs", ".rb", ".php", ".html", ".css", ".json", ".xml", ".yaml", ".yml", ".sql"],
            }
            
            # Build extension filter
            if file_type == "any":
                ext_filter = "*"
            elif file_type in type_extensions:
                ext_filter = type_extensions[file_type]
            else:
                ext_filter = "*"
            
            # Determine search paths
            if search_path:
                # Normalize path
                if len(search_path) <= 2:
                    search_path = search_path.rstrip(':').upper() + ":\\"
                search_paths = [search_path]
            else:
                # Get all fixed drives
                drives_result = await self._run_ps(
                    "Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Free -ne $null } | Select-Object -ExpandProperty Root"
                )
                if drives_result:
                    search_paths = [d.strip() for d in drives_result.split('\n') if d.strip()]
                else:
                    search_paths = ["C:\\"]
            
            # Build PowerShell search command
            if isinstance(ext_filter, list):
                ext_pattern = ",".join([f"'*{ext}'" for ext in ext_filter])
                include_clause = f"-Include {ext_pattern}"
            else:
                include_clause = ""
            
            for search_root in search_paths:
                if len(found) >= max_results:
                    break
                    
                # Use PowerShell for efficient recursive search with depth limit
                ps_cmd = f'''
                $results = @()
                $searchRoot = "{search_root}"
                $searchName = "*{name}*"
                $maxDepth = 4
                
                function Search-Files {{
                    param($path, $depth)
                    if ($depth -gt $maxDepth) {{ return }}
                    
                    try {{
                        # Search files in current directory
                        Get-ChildItem -Path $path -File -Filter $searchName -ErrorAction SilentlyContinue {include_clause} | 
                            Select-Object -First {max_results - len(found)} |
                            ForEach-Object {{
                                $results += @{{
                                    Name = $_.Name
                                    Path = $_.FullName
                                    Size = $_.Length
                                    Extension = $_.Extension
                                    Modified = $_.LastWriteTime.ToString("yyyy-MM-dd HH:mm")
                                    Type = "file"
                                }}
                            }}
                        
                        # Also find folders matching the name
                        Get-ChildItem -Path $path -Directory -Filter $searchName -ErrorAction SilentlyContinue |
                            Select-Object -First 5 |
                            ForEach-Object {{
                                $results += @{{
                                    Name = $_.Name
                                    Path = $_.FullName
                                    Type = "folder"
                                }}
                            }}
                        
                        # Recurse into subdirectories
                        if ($results.Count -lt {max_results}) {{
                            Get-ChildItem -Path $path -Directory -ErrorAction SilentlyContinue | ForEach-Object {{
                                if ($results.Count -lt {max_results}) {{
                                    Search-Files -path $_.FullName -depth ($depth + 1)
                                }}
                            }}
                        }}
                    }} catch {{}}
                }}
                
                # Start search from common locations first for speed
                $priorityPaths = @(
                    "$searchRoot",
                    "$searchRoot\\Users",
                    "$searchRoot\\Program Files",
                    "$searchRoot\\Program Files (x86)",
                    "$searchRoot\\Games"
                )
                
                foreach ($p in $priorityPaths) {{
                    if ((Test-Path $p) -and ($results.Count -lt {max_results})) {{
                        Search-Files -path $p -depth 0
                    }}
                }}
                
                $results | Select-Object -First {max_results} | ConvertTo-Json -Depth 2
                '''
                
                result = await self._run_ps(ps_cmd, timeout=60)
                if result:
                    try:
                        data = json.loads(result)
                        if isinstance(data, dict):
                            data = [data]
                        for item in data:
                            if item and item.get('Path'):
                                # Format size nicely
                                if item.get('Size'):
                                    size_bytes = item['Size']
                                    if size_bytes > 1073741824:
                                        item['SizeFormatted'] = f"{size_bytes / 1073741824:.1f} GB"
                                    elif size_bytes > 1048576:
                                        item['SizeFormatted'] = f"{size_bytes / 1048576:.1f} MB"
                                    elif size_bytes > 1024:
                                        item['SizeFormatted'] = f"{size_bytes / 1024:.1f} KB"
                                    else:
                                        item['SizeFormatted'] = f"{size_bytes} bytes"
                                found.append(item)
                    except json.JSONDecodeError:
                        pass
            
            # Also check Windows Search Index for faster results (if available)
            if len(found) < max_results:
                index_cmd = f'''
                try {{
                    $searcher = New-Object -ComObject Microsoft.Search.Interop.CSearchManager
                    $catalog = $searcher.GetCatalog("SystemIndex")
                    $conn = New-Object System.Data.OleDb.OleDbConnection
                    $conn.ConnectionString = "Provider=Search.CollatorDSO;Extended Properties='Application=Windows'"
                    $conn.Open()
                    
                    $query = "SELECT TOP {max_results - len(found)} System.ItemName, System.ItemPathDisplay, System.Size, System.DateModified FROM SystemIndex WHERE System.ItemName LIKE '%{name}%'"
                    $cmd = New-Object System.Data.OleDb.OleDbCommand($query, $conn)
                    $reader = $cmd.ExecuteReader()
                    
                    $results = @()
                    while ($reader.Read()) {{
                        $results += @{{
                            Name = $reader["System.ItemName"]
                            Path = $reader["System.ItemPathDisplay"]
                            Size = $reader["System.Size"]
                            Modified = $reader["System.DateModified"]
                            Source = "WindowsIndex"
                        }}
                    }}
                    $conn.Close()
                    $results | ConvertTo-Json
                }} catch {{}}
                '''
                index_result = await self._run_ps(index_cmd, timeout=10)
                if index_result:
                    try:
                        data = json.loads(index_result)
                        if isinstance(data, dict):
                            data = [data]
                        for item in data:
                            if item and item.get('Path'):
                                # Case-insensitive name check using name_lower
                                item_name = item.get('Name', '').lower()
                                if name_lower not in item_name:
                                    continue
                                # Filter by extension if file_type specified
                                if file_type != "any" and file_type in type_extensions:
                                    item_ext = Path(item.get('Path', '')).suffix.lower()
                                    if item_ext not in type_extensions[file_type]:
                                        continue
                                # Avoid duplicates
                                if not any(f.get('Path', '').lower() == item['Path'].lower() for f in found):
                                    found.append(item)
                    except json.JSONDecodeError:
                        pass
            
            # Final Python-side filter to ensure case-insensitive matching
            filtered_found = []
            for item in found:
                item_name = item.get('Name', '').lower()
                item_path = item.get('Path', '').lower()
                # Check if name matches (case-insensitive)
                if name_lower in item_name or name_lower in item_path:
                    # Filter by extension if file_type specified
                    if file_type != "any" and file_type in type_extensions and item.get('Type') != 'folder':
                        item_ext = Path(item.get('Path', '')).suffix.lower()
                        if item_ext not in type_extensions[file_type]:
                            continue
                    filtered_found.append(item)
            
            # Deduplicate by path
            seen = set()
            unique_found = []
            for item in filtered_found:
                path_lower = item.get('Path', '').lower()
                if path_lower and path_lower not in seen:
                    seen.add(path_lower)
                    unique_found.append(item)
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=unique_found[:max_results],
                message=f"Found {len(unique_found)} {file_type} files matching '{name}'" + (f" in {search_path}" if search_path else " across all drives")
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
        """Get detailed display/monitor information including multi-monitor setup and mouse position"""
        try:
            if self.is_windows:
                # Get mouse position using ctypes
                class POINT(ctypes.Structure):
                    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
                
                user32 = ctypes.windll.user32
                
                # Primary screen size (virtual screen for multi-monitor)
                primary_width = user32.GetSystemMetrics(0)  # SM_CXSCREEN
                primary_height = user32.GetSystemMetrics(1)  # SM_CYSCREEN
                
                # Virtual screen (all monitors combined)
                virtual_left = user32.GetSystemMetrics(76)   # SM_XVIRTUALSCREEN
                virtual_top = user32.GetSystemMetrics(77)    # SM_YVIRTUALSCREEN
                virtual_width = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
                virtual_height = user32.GetSystemMetrics(79) # SM_CYVIRTUALSCREEN
                
                # Number of monitors
                monitor_count = user32.GetSystemMetrics(80)  # SM_CMONITORS
                
                # Get current mouse position
                pt = POINT()
                user32.GetCursorPos(ctypes.byref(pt))
                mouse_x, mouse_y = pt.x, pt.y
                
                # Get detailed monitor info via PowerShell
                cmd = '''
                Add-Type -AssemblyName System.Windows.Forms
                $monitors = [System.Windows.Forms.Screen]::AllScreens
                $result = @{
                    Monitors = @()
                    MousePosition = @{
                        X = [System.Windows.Forms.Cursor]::Position.X
                        Y = [System.Windows.Forms.Cursor]::Position.Y
                    }
                }
                
                $index = 0
                foreach ($mon in $monitors) {
                    $monInfo = @{
                        Index = $index
                        DeviceName = $mon.DeviceName
                        IsPrimary = $mon.Primary
                        Bounds = @{
                            X = $mon.Bounds.X
                            Y = $mon.Bounds.Y
                            Width = $mon.Bounds.Width
                            Height = $mon.Bounds.Height
                            Right = $mon.Bounds.X + $mon.Bounds.Width
                            Bottom = $mon.Bounds.Y + $mon.Bounds.Height
                        }
                        WorkingArea = @{
                            X = $mon.WorkingArea.X
                            Y = $mon.WorkingArea.Y
                            Width = $mon.WorkingArea.Width
                            Height = $mon.WorkingArea.Height
                        }
                        BitsPerPixel = $mon.BitsPerPixel
                    }
                    $result.Monitors += $monInfo
                    $index++
                }
                
                # Determine which monitor the mouse is on
                $mouseX = $result.MousePosition.X
                $mouseY = $result.MousePosition.Y
                $result.MouseOnMonitor = -1
                
                foreach ($mon in $result.Monitors) {
                    $b = $mon.Bounds
                    if ($mouseX -ge $b.X -and $mouseX -lt $b.Right -and $mouseY -ge $b.Y -and $mouseY -lt $b.Bottom) {
                        $result.MouseOnMonitor = $mon.Index
                        $result.MouseRelativePosition = @{
                            X = $mouseX - $b.X
                            Y = $mouseY - $b.Y
                        }
                        break
                    }
                }
                
                $result | ConvertTo-Json -Depth 4
                '''
                
                result = await self._run_ps(cmd)
                display_data = {
                    "monitor_count": monitor_count,
                    "primary_resolution": f"{primary_width}x{primary_height}",
                    "virtual_screen": {
                        "left": virtual_left,
                        "top": virtual_top,
                        "width": virtual_width,
                        "height": virtual_height,
                        "right": virtual_left + virtual_width,
                        "bottom": virtual_top + virtual_height
                    },
                    "mouse_position": {"x": mouse_x, "y": mouse_y}
                }
                
                if result:
                    try:
                        ps_data = json.loads(result)
                        display_data["monitors"] = ps_data.get("Monitors", [])
                        display_data["mouse_on_monitor"] = ps_data.get("MouseOnMonitor", 0)
                        display_data["mouse_relative_position"] = ps_data.get("MouseRelativePosition", {"X": mouse_x, "Y": mouse_y})
                    except json.JSONDecodeError:
                        pass
                
                # Build helpful message
                mouse_mon = display_data.get("mouse_on_monitor", 0)
                msg = f"{monitor_count} monitor(s), mouse at ({mouse_x}, {mouse_y}) on monitor {mouse_mon}"
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=display_data,
                    message=msg
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
                            "explore_folder", "find_app_path", "find_file", "get_startup_apps",
                            "get_recent_files", "get_display_info", "get_audio_devices"
                        ],
                        "description": "Discovery action to perform"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["all", "browsers", "dev", "media", "games", "communication", "office", "utilities"],
                        "description": "App category filter for list_installed_apps"
                    },
                    "detail_level": {
                        "type": "string",
                        "enum": ["basic", "full"],
                        "description": "Detail level for get_hardware: basic (summary) or full (complete specs including RAM type, GPU VRAM, storage details)"
                    },
                    "query": {"type": "string", "description": "Search query for search_apps"},
                    "path": {"type": "string", "description": "Folder path for explore_folder"},
                    "search_path": {"type": "string", "description": "Path or drive to search for find_file (e.g., 'D:', 'C:\\Users'). Searches all drives if not specified"},
                    "depth": {"type": "integer", "description": "Exploration depth", "default": 1},
                    "app_name": {"type": "string", "description": "App name for find_app_path"},
                    "search_drive": {"type": "string", "description": "Drive letter to search (e.g., 'D', 'E:') for find_app_path - searches all drives if not specified"},
                    "name": {"type": "string", "description": "File or folder name to search for (find_file)"},
                    "file_type": {
                        "type": "string",
                        "enum": ["any", "exe", "document", "image", "video", "audio", "archive", "code"],
                        "description": "Type of file to find: any, exe (executables), document (pdf/doc/txt), image, video, audio, archive (zip/rar), code (source files)"
                    },
                    "max_results": {"type": "integer", "description": "Maximum results to return for find_file", "default": 20},
                    "filter_key": {"type": "string", "description": "Filter for environment variables"},
                    "count": {"type": "integer", "description": "Number of recent files", "default": 20}
                },
                "required": ["action"]
            }
        }
    
    async def cleanup(self):
        """Cleanup"""
        self._cache.clear()
