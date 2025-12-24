"""
Windows Automation Tool for Sakura
Provides Windows-specific automation: file search, command execution, app control
Uses native Windows APIs and optional MCP servers for extended functionality
"""
import asyncio
import os
import subprocess
import logging
import ctypes
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from ..base import BaseTool, ToolResult, ToolStatus


# Windows API constants for ctypes
if os.name == 'nt':
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    
    # Window show commands
    SW_MINIMIZE = 6
    SW_MAXIMIZE = 3
    SW_RESTORE = 9
    SW_HIDE = 0
    SW_SHOW = 5
    
    # Virtual key codes
    VK_VOLUME_MUTE = 0xAD
    VK_VOLUME_DOWN = 0xAE
    VK_VOLUME_UP = 0xAF
    VK_MEDIA_NEXT = 0xB0
    VK_MEDIA_PREV = 0xB1
    VK_MEDIA_STOP = 0xB2
    VK_MEDIA_PLAY_PAUSE = 0xB3
    
    # Mouse input constants
    MOUSEEVENTF_MOVE = 0x0001
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_RIGHTDOWN = 0x0008
    MOUSEEVENTF_RIGHTUP = 0x0010
    MOUSEEVENTF_ABSOLUTE = 0x8000


class WindowsAutomation(BaseTool):
    """Windows automation - native commands + MCP server integration"""
    
    name = "windows"
    description = "Control Windows: run commands (pip install, uvx, powershell), search files, open apps, manage windows, mouse control, volume/media. Scripts are saved to sandbox folder for review."
    
    def __init__(self):
        self._lock = asyncio.Lock()
        self.is_windows = os.name == 'nt'
        self.everything_available = False
        self.temp_dir: Path = Path(os.environ.get('TEMP', '.'))
        self.user_home: Path = Path.home()
        # Sandbox folder for scripts - user can review before running
        self.sandbox_dir: Path = self.user_home / "Documents" / "Sakura" / "scripts"
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        self.common_paths: List[Path] = self._get_common_paths()
        self._check_everything()
    
    def _get_common_paths(self) -> List[Path]:
        """Get common user paths for file operations"""
        if not self.is_windows:
            return []
        
        home = Path.home()
        return [
            home / "Documents",
            home / "Downloads",
            home / "Desktop",
            home / "Pictures",
            home / "Music",
            home / "Videos",
        ]
    
    def _check_everything(self):
        """Check if Everything search is available"""
        if not self.is_windows:
            return
        try:
            # Check if Everything is running
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq Everything.exe'],
                capture_output=True, text=True, timeout=5
            )
            self.everything_available = 'Everything.exe' in result.stdout
            if self.everything_available:
                logging.info("Everything search detected")
        except Exception:
            pass
    
    async def initialize(self) -> bool:
        """Initialize Windows automation"""
        if not self.is_windows:
            logging.warning("Windows automation disabled - not running on Windows")
            self.enabled = False
            return False
        
        logging.info(f"Windows automation initialized (temp: {self.temp_dir})")
        return True

    async def execute(self, action: str, **kwargs) -> ToolResult:
        """Execute Windows automation action"""
        if not self.is_windows:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Not running on Windows"
            )
        
        actions = {
            "run_command": self._run_command,
            "open_app": self._open_app,
            "search_files": self._search_files,
            "list_processes": self._list_processes,
            "kill_process": self._kill_process,
            "get_system_info": self._get_system_info,
            "get_memory_status": self._get_memory_status,
            "open_url": self._open_url,
            "type_text": self._type_text,
            "press_key": self._press_key,
            "screenshot": self._screenshot,
            "list_windows": self._list_windows,
            "focus_window": self._focus_window,
            "minimize_window": self._minimize_window,
            "maximize_window": self._maximize_window,
            "volume_control": self._volume_control,
            "media_control": self._media_control,
            "list_files": self._list_files,
            "read_file": self._read_file,
            "write_file": self._write_file,
            "delete_file": self._delete_file,
            "create_folder": self._create_folder,
            "delete_folder": self._delete_folder,
            "execute_script": self._execute_script,
            "get_clipboard": self._get_clipboard,
            "set_clipboard": self._set_clipboard,
            "move_mouse": self._move_mouse,
            "click_mouse": self._click_mouse,
            "get_mouse_position": self._get_mouse_position,
        }
        
        if action not in actions:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Unknown action: {action}. Available: {list(actions.keys())}"
            )
        
        return await actions[action](**kwargs)
    
    async def _run_command(self, command: str, shell: str = "powershell", timeout: int = 30) -> ToolResult:
        """Run a shell command (PowerShell or CMD)"""
        async with self._lock:
            try:
                if shell.lower() == "powershell":
                    cmd = ["powershell", "-NoProfile", "-Command", command]
                else:
                    cmd = ["cmd", "/c", command]
                
                # Run in executor to not block
                result = await asyncio.to_thread(
                    subprocess.run,
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                
                output = result.stdout.strip()
                error = result.stderr.strip()
                
                if result.returncode == 0:
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data={"output": output, "return_code": result.returncode},
                        message=output[:500] if output else "Command executed successfully"
                    )
                else:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        data={"output": output, "error": error, "return_code": result.returncode},
                        error=error or f"Command failed with code {result.returncode}"
                    )
                    
            except subprocess.TimeoutExpired:
                return ToolResult(status=ToolStatus.ERROR, error=f"Command timed out after {timeout}s")
            except Exception as e:
                return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _open_app(self, app: str, args: str = "") -> ToolResult:
        """Open an application"""
        try:
            # Common app shortcuts
            app_paths = {
                "chrome": "chrome",
                "firefox": "firefox",
                "edge": "msedge",
                "notepad": "notepad",
                "explorer": "explorer",
                "calculator": "calc",
                "terminal": "wt",
                "cmd": "cmd",
                "powershell": "powershell",
                "vscode": "code",
                "spotify": "spotify",
            }
            
            app_cmd = app_paths.get(app.lower(), app)
            
            if args:
                cmd = f'Start-Process "{app_cmd}" -ArgumentList "{args}"'
            else:
                cmd = f'Start-Process "{app_cmd}"'
            
            result = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    message=f"Opened {app}"
                )
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=result.stderr or f"Failed to open {app}"
                )
                
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _open_url(self, url: str) -> ToolResult:
        """Open a URL in default browser"""
        try:
            cmd = f'Start-Process "{url}"'
            await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                timeout=10
            )
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"Opened {url}"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def _search_files(self, query: str, path: str = "", max_results: int = 20) -> ToolResult:
        """Search for files using Everything or fallback to PowerShell"""
        try:
            if self.everything_available:
                # Use Everything CLI (es.exe) if available
                cmd = f'es.exe -n {max_results} "{query}"'
                result = await asyncio.to_thread(
                    subprocess.run,
                    ["cmd", "/c", cmd],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data=files[:max_results],
                        message=f"Found {len(files)} files matching '{query}'"
                    )
            
            # Fallback to PowerShell search
            search_path = path or "C:\\Users"
            cmd = f'Get-ChildItem -Path "{search_path}" -Recurse -Filter "*{query}*" -ErrorAction SilentlyContinue | Select-Object -First {max_results} | ForEach-Object {{ $_.FullName }}'
            
            result = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=files,
                message=f"Found {len(files)} files matching '{query}'"
            )
            
        except subprocess.TimeoutExpired:
            return ToolResult(status=ToolStatus.ERROR, error="Search timed out")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _list_processes(self, filter_name: str = "") -> ToolResult:
        """List running processes"""
        try:
            if filter_name:
                cmd = f'Get-Process | Where-Object {{ $_.ProcessName -like "*{filter_name}*" }} | Select-Object -Property ProcessName, Id, CPU, WorkingSet | ConvertTo-Json'
            else:
                cmd = 'Get-Process | Select-Object -First 30 -Property ProcessName, Id, CPU, WorkingSet | ConvertTo-Json'
            
            result = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                import json
                try:
                    processes = json.loads(result.stdout)
                    if isinstance(processes, dict):
                        processes = [processes]
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data=processes,
                        message=f"Found {len(processes)} processes"
                    )
                except json.JSONDecodeError:
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data=result.stdout,
                        message="Process list retrieved"
                    )
            
            return ToolResult(status=ToolStatus.ERROR, error=result.stderr)
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _kill_process(self, name: str = "", pid: int = 0) -> ToolResult:
        """Kill a process by name or PID"""
        try:
            if pid:
                cmd = f'Stop-Process -Id {pid} -Force'
            elif name:
                cmd = f'Stop-Process -Name "{name}" -Force'
            else:
                return ToolResult(status=ToolStatus.ERROR, error="Provide process name or PID")
            
            result = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    message=f"Killed process {name or pid}"
                )
            else:
                return ToolResult(status=ToolStatus.ERROR, error=result.stderr)
                
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _get_system_info(self) -> ToolResult:
        """Get system information"""
        try:
            cmd = '''
            $info = @{
                ComputerName = $env:COMPUTERNAME
                Username = $env:USERNAME
                OS = (Get-CimInstance Win32_OperatingSystem).Caption
                Memory = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 2)
                CPU = (Get-CimInstance Win32_Processor).Name
                Uptime = (Get-Date) - (Get-CimInstance Win32_OperatingSystem).LastBootUpTime
            }
            $info | ConvertTo-Json
            '''
            
            result = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                import json
                try:
                    info = json.loads(result.stdout)
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data=info,
                        message=f"System: {info.get('OS', 'Unknown')}"
                    )
                except json.JSONDecodeError:
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data=result.stdout,
                        message="System info retrieved"
                    )
            
            return ToolResult(status=ToolStatus.ERROR, error=result.stderr)
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _get_memory_status(self) -> ToolResult:
        """Get memory status using kernel32 GlobalMemoryStatusEx"""
        try:
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            
            mem_status = MEMORYSTATUSEX()
            mem_status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            kernel32.GlobalMemoryStatusEx(ctypes.byref(mem_status))
            
            total_gb = mem_status.ullTotalPhys / (1024**3)
            avail_gb = mem_status.ullAvailPhys / (1024**3)
            used_gb = total_gb - avail_gb
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "memory_load_percent": mem_status.dwMemoryLoad,
                    "total_physical_gb": round(total_gb, 2),
                    "available_physical_gb": round(avail_gb, 2),
                    "used_physical_gb": round(used_gb, 2),
                    "total_page_file_gb": round(mem_status.ullTotalPageFile / (1024**3), 2),
                    "available_page_file_gb": round(mem_status.ullAvailPageFile / (1024**3), 2),
                },
                message=f"Memory: {mem_status.dwMemoryLoad}% used ({round(used_gb, 1)}/{round(total_gb, 1)} GB)"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def _type_text(self, text: str, delay: float = 0.05) -> ToolResult:
        """Type text using SendKeys (requires pyautogui or similar)"""
        try:
            # Use PowerShell SendKeys
            # Escape special characters
            escaped = text.replace('"', '`"').replace("'", "`'")
            cmd = f'''
            Add-Type -AssemblyName System.Windows.Forms
            [System.Windows.Forms.SendKeys]::SendWait("{escaped}")
            '''
            
            result = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    message=f"Typed: {text[:50]}..."
                )
            else:
                return ToolResult(status=ToolStatus.ERROR, error=result.stderr)
                
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _press_key(self, key: str) -> ToolResult:
        """Press a special key (Enter, Tab, Escape, etc.)"""
        try:
            # Map common key names to SendKeys codes
            key_map = {
                "enter": "{ENTER}",
                "tab": "{TAB}",
                "escape": "{ESC}",
                "esc": "{ESC}",
                "backspace": "{BACKSPACE}",
                "delete": "{DELETE}",
                "up": "{UP}",
                "down": "{DOWN}",
                "left": "{LEFT}",
                "right": "{RIGHT}",
                "home": "{HOME}",
                "end": "{END}",
                "pageup": "{PGUP}",
                "pagedown": "{PGDN}",
                "f1": "{F1}", "f2": "{F2}", "f3": "{F3}", "f4": "{F4}",
                "f5": "{F5}", "f6": "{F6}", "f7": "{F7}", "f8": "{F8}",
                "f9": "{F9}", "f10": "{F10}", "f11": "{F11}", "f12": "{F12}",
            }
            
            send_key = key_map.get(key.lower(), key)
            
            cmd = f'''
            Add-Type -AssemblyName System.Windows.Forms
            [System.Windows.Forms.SendKeys]::SendWait("{send_key}")
            '''
            
            result = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    message=f"Pressed key: {key}"
                )
            else:
                return ToolResult(status=ToolStatus.ERROR, error=result.stderr)
                
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _screenshot(self, path: str = "") -> ToolResult:
        """Take a screenshot"""
        try:
            if not path:
                path = os.path.join(os.environ.get('TEMP', '.'), 'screenshot.png')
            
            cmd = f'''
            Add-Type -AssemblyName System.Windows.Forms
            $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
            $bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
            $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
            $graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
            $bitmap.Save("{path}")
            $graphics.Dispose()
            $bitmap.Dispose()
            "{path}"
            '''
            
            result = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and os.path.exists(path):
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"path": path},
                    message=f"Screenshot saved to {path}"
                )
            else:
                return ToolResult(status=ToolStatus.ERROR, error=result.stderr or "Screenshot failed")
                
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _list_windows(self) -> ToolResult:
        """List open windows"""
        try:
            cmd = '''
            Get-Process | Where-Object { $_.MainWindowTitle -ne "" } | 
            Select-Object -Property ProcessName, Id, MainWindowTitle | 
            ConvertTo-Json
            '''
            
            result = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                try:
                    windows = json.loads(result.stdout)
                    if isinstance(windows, dict):
                        windows = [windows]
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data=windows,
                        message=f"Found {len(windows)} open windows"
                    )
                except json.JSONDecodeError:
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data=result.stdout,
                        message="Window list retrieved"
                    )
            
            return ToolResult(status=ToolStatus.ERROR, error=result.stderr)
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _focus_window(self, title: Optional[str] = None, pid: Optional[int] = None) -> ToolResult:
        """Focus a window by title or PID using ctypes"""
        try:
            if pid:
                # Find window by PID
                cmd = f'(Get-Process -Id {pid}).MainWindowHandle'
            elif title:
                cmd = f'(Get-Process | Where-Object {{ $_.MainWindowTitle -like "*{title}*" }} | Select-Object -First 1).MainWindowHandle'
            else:
                return ToolResult(status=ToolStatus.ERROR, error="Provide window title or PID")
            
            result = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                hwnd = int(result.stdout.strip())
                if hwnd:
                    # Use ctypes to focus window
                    user32.SetForegroundWindow(hwnd)
                    user32.ShowWindow(hwnd, SW_RESTORE)
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        message=f"Focused window (handle: {hwnd})"
                    )
            
            return ToolResult(status=ToolStatus.ERROR, error="Window not found")
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _minimize_window(self, title: Optional[str] = None, pid: Optional[int] = None) -> ToolResult:
        """Minimize a window using ctypes"""
        try:
            hwnd = await self._get_window_handle(title, pid)
            if hwnd:
                user32.ShowWindow(hwnd, SW_MINIMIZE)
                return ToolResult(status=ToolStatus.SUCCESS, message="Window minimized")
            return ToolResult(status=ToolStatus.ERROR, error="Window not found")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _maximize_window(self, title: Optional[str] = None, pid: Optional[int] = None) -> ToolResult:
        """Maximize a window using ctypes"""
        try:
            hwnd = await self._get_window_handle(title, pid)
            if hwnd:
                user32.ShowWindow(hwnd, SW_MAXIMIZE)
                return ToolResult(status=ToolStatus.SUCCESS, message="Window maximized")
            return ToolResult(status=ToolStatus.ERROR, error="Window not found")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _get_window_handle(self, title: Optional[str] = None, pid: Optional[int] = None) -> Optional[int]:
        """Helper to get window handle"""
        if pid:
            cmd = f'(Get-Process -Id {pid}).MainWindowHandle'
        elif title:
            cmd = f'(Get-Process | Where-Object {{ $_.MainWindowTitle -like "*{title}*" }} | Select-Object -First 1).MainWindowHandle'
        else:
            return None
        
        result = await asyncio.to_thread(
            subprocess.run,
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            try:
                return int(result.stdout.strip())
            except ValueError:
                return None
        return None
    
    async def _volume_control(self, action: str, level: Optional[int] = None) -> ToolResult:
        """Control system volume using ctypes"""
        try:
            if action == "mute":
                user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
                user32.keybd_event(VK_VOLUME_MUTE, 0, 2, 0)  # Key up
                return ToolResult(status=ToolStatus.SUCCESS, message="Volume muted/unmuted")
            elif action == "up":
                for _ in range(level or 5):
                    user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)
                    user32.keybd_event(VK_VOLUME_UP, 0, 2, 0)
                return ToolResult(status=ToolStatus.SUCCESS, message=f"Volume increased by {level or 5}")
            elif action == "down":
                for _ in range(level or 5):
                    user32.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)
                    user32.keybd_event(VK_VOLUME_DOWN, 0, 2, 0)
                return ToolResult(status=ToolStatus.SUCCESS, message=f"Volume decreased by {level or 5}")
            else:
                return ToolResult(status=ToolStatus.ERROR, error="Action must be: mute, up, or down")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _media_control(self, action: str) -> ToolResult:
        """Control media playback using ctypes"""
        try:
            key_map = {
                "play": VK_MEDIA_PLAY_PAUSE,
                "pause": VK_MEDIA_PLAY_PAUSE,
                "next": VK_MEDIA_NEXT,
                "prev": VK_MEDIA_PREV,
                "previous": VK_MEDIA_PREV,
                "stop": VK_MEDIA_STOP,
            }
            
            vk = key_map.get(action.lower())
            if not vk:
                return ToolResult(status=ToolStatus.ERROR, error="Action must be: play, pause, next, prev, stop")
            
            user32.keybd_event(vk, 0, 0, 0)
            user32.keybd_event(vk, 0, 2, 0)  # Key up
            return ToolResult(status=ToolStatus.SUCCESS, message=f"Media {action}")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _list_files(self, directory: str = "", pattern: str = "*") -> ToolResult:
        """List files in a directory using Path"""
        try:
            if directory:
                dir_path = Path(directory)
            else:
                dir_path = self.user_home / "Documents"
            
            if not dir_path.exists():
                return ToolResult(status=ToolStatus.ERROR, error=f"Directory not found: {dir_path}")
            
            files: List[Dict[str, Any]] = []
            for item in dir_path.glob(pattern):
                files.append({
                    "name": item.name,
                    "path": str(item),
                    "is_dir": item.is_dir(),
                    "size": item.stat().st_size if item.is_file() else 0,
                })
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=files[:50],  # Limit to 50 items
                message=f"Found {len(files)} items in {dir_path}"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _read_file(self, file_path: str, max_size: int = 10000) -> ToolResult:
        """Read a file using Path"""
        try:
            path = Path(file_path)
            if not path.exists():
                return ToolResult(status=ToolStatus.ERROR, error=f"File not found: {path}")
            
            if path.stat().st_size > max_size:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"File too large ({path.stat().st_size} bytes). Max: {max_size}"
                )
            
            content = path.read_text(encoding='utf-8', errors='replace')
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"content": content, "path": str(path)},
                message=f"Read {len(content)} characters from {path.name}"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _write_file(self, file_path: str, content: str, append: bool = False) -> ToolResult:
        """Write to a file using Path"""
        try:
            path = Path(file_path)
            
            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            
            if append:
                with path.open('a', encoding='utf-8') as f:
                    f.write(content)
            else:
                path.write_text(content, encoding='utf-8')
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"{'Appended to' if append else 'Wrote'} {path.name}"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _delete_file(self, file_path: str) -> ToolResult:
        """Delete a file"""
        try:
            path = Path(file_path)
            if not path.exists():
                return ToolResult(status=ToolStatus.ERROR, error=f"File not found: {path}")
            if path.is_dir():
                return ToolResult(status=ToolStatus.ERROR, error="Use delete_folder for directories")
            
            path.unlink()
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"Deleted {path.name}"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _create_folder(self, folder_path: str) -> ToolResult:
        """Create a folder (and parent folders if needed)"""
        try:
            path = Path(folder_path)
            path.mkdir(parents=True, exist_ok=True)
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"path": str(path)},
                message=f"Created folder: {path}"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _delete_folder(self, folder_path: str, recursive: bool = False) -> ToolResult:
        """Delete a folder"""
        try:
            path = Path(folder_path)
            if not path.exists():
                return ToolResult(status=ToolStatus.ERROR, error=f"Folder not found: {path}")
            if not path.is_dir():
                return ToolResult(status=ToolStatus.ERROR, error="Use delete_file for files")
            
            if recursive:
                import shutil
                shutil.rmtree(path)
            else:
                path.rmdir()  # Only works if empty
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"Deleted folder: {path.name}"
            )
        except OSError as e:
            if "not empty" in str(e).lower() or "directory not empty" in str(e).lower():
                return ToolResult(status=ToolStatus.ERROR, error="Folder not empty. Use recursive=true to delete contents.")
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _execute_script(self, script_content: str, script_type: str = "powershell", 
                              script_name: str = "", execute: bool = True) -> ToolResult:
        """Create and execute a script in the sandbox folder for user review.
        
        All scripts are saved to: ~/Documents/Sakura/scripts/
        Scripts are ALWAYS kept for user review.
        """
        try:
            from datetime import datetime
            
            # Determine file extension and executor
            script_config = {
                "powershell": {"ext": ".ps1", "cmd": ["powershell", "-ExecutionPolicy", "Bypass", "-File"]},
                "python": {"ext": ".py", "cmd": [str(Path(".venv/Scripts/python").absolute()) if Path(".venv").exists() else "python"]},
                "batch": {"ext": ".bat", "cmd": ["cmd", "/c"]},
                "cmd": {"ext": ".bat", "cmd": ["cmd", "/c"]},
                "javascript": {"ext": ".js", "cmd": ["node"]},
                "vbscript": {"ext": ".vbs", "cmd": ["cscript", "//nologo"]},
            }
            
            if script_type.lower() not in script_config:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Unknown script type: {script_type}. Supported: {list(script_config.keys())}"
                )
            
            config = script_config[script_type.lower()]
            
            # Generate script filename with timestamp for uniqueness
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if script_name:
                # Sanitize script name
                safe_name = "".join(c for c in script_name if c.isalnum() or c in "._-")
                filename = f"{safe_name}{config['ext']}"
            else:
                filename = f"script_{timestamp}{config['ext']}"
            
            # ALWAYS save to sandbox folder
            script_path = self.sandbox_dir / script_type.lower() / filename
            script_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write script with header comment
            header = f"# Generated by Sakura on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            header += f"# Script type: {script_type}\n"
            header += f"# Location: {script_path}\n\n"
            
            full_content = header + script_content
            script_path.write_text(full_content, encoding='utf-8')
            
            result_data = {
                "script_path": str(script_path),
                "sandbox_folder": str(self.sandbox_dir),
                "script_type": script_type,
                "executed": False,
                "output": None
            }
            
            # Execute if requested
            if execute:
                cmd = config['cmd'] + [str(script_path)]
                result = await asyncio.to_thread(
                    subprocess.run,
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=str(script_path.parent)
                )
                
                output = result.stdout.strip()
                error = result.stderr.strip()
                result_data["executed"] = True
                result_data["output"] = output
                result_data["return_code"] = result.returncode
                
                if result.returncode != 0:
                    result_data["error"] = error
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        data=result_data,
                        error=f"Script failed: {error}. Script saved at: {script_path}"
                    )
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=result_data,
                    message=f"Script executed successfully. Output: {output[:200] if output else 'No output'}. Script saved at: {script_path}"
                )
            else:
                # Just create, don't execute
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=result_data,
                    message=f"Script created (not executed). Review at: {script_path}"
                )
                
        except subprocess.TimeoutExpired:
            return ToolResult(
                status=ToolStatus.ERROR, 
                data={"script_path": str(script_path)},
                error=f"Script timed out after 60s. Script saved at: {script_path}"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _get_clipboard(self) -> ToolResult:
        """Get clipboard content using ctypes"""
        try:
            cmd = 'Get-Clipboard'
            result = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"content": result.stdout.strip()},
                    message="Clipboard content retrieved"
                )
            return ToolResult(status=ToolStatus.ERROR, error=result.stderr)
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _set_clipboard(self, content: str) -> ToolResult:
        """Set clipboard content"""
        try:
            # Escape for PowerShell
            escaped = content.replace('"', '`"')
            cmd = f'Set-Clipboard -Value "{escaped}"'
            
            result = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    message="Clipboard set"
                )
            return ToolResult(status=ToolStatus.ERROR, error=result.stderr)
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _move_mouse(self, x: int, y: int, absolute: bool = True) -> ToolResult:
        """Move mouse cursor to position using ctypes"""
        try:
            if absolute:
                # SetCursorPos for absolute positioning
                user32.SetCursorPos(x, y)
            else:
                # Relative movement using mouse_event
                user32.mouse_event(MOUSEEVENTF_MOVE, x, y, 0, 0)
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"x": x, "y": y, "absolute": absolute},
                message=f"Mouse moved to ({x}, {y})"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _click_mouse(self, button: str = "left", double: bool = False) -> ToolResult:
        """Click mouse button using ctypes"""
        try:
            if button.lower() == "left":
                down_flag = MOUSEEVENTF_LEFTDOWN
                up_flag = MOUSEEVENTF_LEFTUP
            elif button.lower() == "right":
                down_flag = MOUSEEVENTF_RIGHTDOWN
                up_flag = MOUSEEVENTF_RIGHTUP
            else:
                return ToolResult(status=ToolStatus.ERROR, error="Button must be 'left' or 'right'")
            
            clicks = 2 if double else 1
            for _ in range(clicks):
                user32.mouse_event(down_flag, 0, 0, 0, 0)
                user32.mouse_event(up_flag, 0, 0, 0, 0)
            
            click_type = "Double-clicked" if double else "Clicked"
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"{click_type} {button} mouse button"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _get_mouse_position(self) -> ToolResult:
        """Get current mouse cursor position"""
        try:
            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
            
            pt = POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"x": pt.x, "y": pt.y},
                message=f"Mouse at ({pt.x}, {pt.y})"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    def get_schema(self) -> Dict[str, Any]:
        """Return schema for Windows automation tools"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "run_command", "open_app", "search_files", "list_processes",
                            "kill_process", "get_system_info", "get_memory_status", "open_url",
                            "type_text", "press_key", "screenshot", "list_windows", "focus_window",
                            "minimize_window", "maximize_window", "volume_control",
                            "media_control", "list_files", "read_file", "write_file",
                            "delete_file", "create_folder", "delete_folder", "execute_script",
                            "get_clipboard", "set_clipboard", "move_mouse", "click_mouse",
                            "get_mouse_position"
                        ],
                        "description": "Windows action to perform"
                    },
                    "command": {"type": "string", "description": "Command to run (for run_command)"},
                    "shell": {"type": "string", "enum": ["powershell", "cmd"], "description": "Shell to use", "default": "powershell"},
                    "app": {"type": "string", "description": "Application to open"},
                    "args": {"type": "string", "description": "Arguments for the app"},
                    "query": {"type": "string", "description": "Search query for files"},
                    "path": {"type": "string", "description": "Path for file operations"},
                    "url": {"type": "string", "description": "URL to open"},
                    "text": {"type": "string", "description": "Text to type"},
                    "key": {"type": "string", "description": "Key to press"},
                    "name": {"type": "string", "description": "Process name"},
                    "pid": {"type": "integer", "description": "Process ID"},
                    "filter_name": {"type": "string", "description": "Filter for process list"},
                    "max_results": {"type": "integer", "description": "Max results for search", "default": 20},
                    "timeout": {"type": "integer", "description": "Command timeout in seconds", "default": 30},
                    "title": {"type": "string", "description": "Window title for focus/minimize/maximize"},
                    "volume_action": {"type": "string", "enum": ["mute", "up", "down"], "description": "Volume control action"},
                    "level": {"type": "integer", "description": "Volume level steps (1-10)"},
                    "media_action": {"type": "string", "enum": ["play", "pause", "next", "prev", "stop"], "description": "Media control action"},
                    "directory": {"type": "string", "description": "Directory path for list_files"},
                    "pattern": {"type": "string", "description": "File pattern for list_files (e.g., *.txt)", "default": "*"},
                    "file_path": {"type": "string", "description": "File path for read_file/write_file/delete_file"},
                    "folder_path": {"type": "string", "description": "Folder path for create_folder/delete_folder"},
                    "recursive": {"type": "boolean", "description": "Delete folder contents recursively", "default": False},
                    "content": {"type": "string", "description": "Content for write_file or set_clipboard"},
                    "append": {"type": "boolean", "description": "Append to file instead of overwrite", "default": False},
                    "max_size": {"type": "integer", "description": "Max file size to read in bytes", "default": 10000},
                    "script_content": {"type": "string", "description": "Script code to execute (saved to ~/Documents/Sakura/scripts/)"},
                    "script_type": {
                        "type": "string",
                        "enum": ["powershell", "python", "batch", "cmd", "javascript", "vbscript"],
                        "description": "Type of script to execute",
                        "default": "powershell"
                    },
                    "script_name": {"type": "string", "description": "Name for the script file (optional, auto-generated if not provided)"},
                    "execute": {"type": "boolean", "description": "Execute the script after creating (default true)", "default": True},
                    "x": {"type": "integer", "description": "X coordinate for mouse movement"},
                    "y": {"type": "integer", "description": "Y coordinate for mouse movement"},
                    "absolute": {"type": "boolean", "description": "Use absolute coordinates (default true)", "default": True},
                    "button": {"type": "string", "enum": ["left", "right"], "description": "Mouse button to click", "default": "left"},
                    "double": {"type": "boolean", "description": "Double-click", "default": False}
                },
                "required": ["action"]
            }
        }
    
    async def cleanup(self):
        """Cleanup Windows automation"""
        pass
