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
                    "detail_level": {
                        "type": "string",
                        "enum": ["basic", "full"],
                        "description": "Detail level for get_hardware: basic (summary) or full (complete specs including RAM type, GPU VRAM, storage details)"
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
