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


# Get assistant name for sandbox folder
ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "Sakura")

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
        self.sandbox_dir: Path = self.user_home / "Documents" / ASSISTANT_NAME / "scripts"
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
            "find_clickable_element": self._find_clickable_element,
            "click_element_by_name": self._click_element_by_name,
            # Screen reading actions
            "read_screen": self._read_screen,
            "read_window_text": self._read_window_text,
            "get_ui_elements": self._get_ui_elements,
            "find_ui_element": self._find_ui_element,
            "click_ui_element": self._click_ui_element,
            "get_focused_element": self._get_focused_element,
            "read_window_content": self._read_window_content,
            "read_text_at_position": self._read_text_at_position,
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
    
    async def _move_mouse(self, x: int, y: int, absolute: bool = True, monitor: int = None, **kwargs) -> ToolResult:
        """Move mouse cursor to position using ctypes
        
        Args:
            x: X coordinate
            y: Y coordinate  
            absolute: If True, use absolute screen coordinates. If False, move relative to current position.
            monitor: If specified, x/y are relative to that monitor (0=primary, 1=second, etc.)
        """
        try:
            target_x, target_y = x, y
            
            # If monitor specified, convert to absolute coordinates
            if monitor is not None and absolute:
                # Get monitor info
                monitor_info = await self._get_monitor_bounds(monitor)
                if monitor_info:
                    # Convert monitor-relative to absolute
                    target_x = monitor_info['x'] + x
                    target_y = monitor_info['y'] + y
                    
                    # Clamp to monitor bounds
                    target_x = max(monitor_info['x'], min(target_x, monitor_info['x'] + monitor_info['width'] - 1))
                    target_y = max(monitor_info['y'], min(target_y, monitor_info['y'] + monitor_info['height'] - 1))
            
            if absolute:
                # SetCursorPos for absolute positioning
                user32.SetCursorPos(target_x, target_y)
            else:
                # Relative movement using mouse_event
                user32.mouse_event(MOUSEEVENTF_MOVE, x, y, 0, 0)
            
            msg = f"Mouse moved to ({target_x}, {target_y})"
            if monitor is not None:
                msg += f" (monitor {monitor}: {x}, {y})"
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"x": target_x, "y": target_y, "absolute": absolute, "monitor": monitor},
                message=msg
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _get_monitor_bounds(self, monitor_index: int) -> dict:
        """Get bounds for a specific monitor"""
        try:
            cmd = f'''
            Add-Type -AssemblyName System.Windows.Forms
            $monitors = [System.Windows.Forms.Screen]::AllScreens
            if ({monitor_index} -lt $monitors.Count) {{
                $mon = $monitors[{monitor_index}]
                @{{
                    x = $mon.Bounds.X
                    y = $mon.Bounds.Y
                    width = $mon.Bounds.Width
                    height = $mon.Bounds.Height
                }} | ConvertTo-Json
            }}
            '''
            result = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout.strip())
        except Exception:
            pass
        return None
    
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
    
    async def _get_mouse_position(self, include_context: bool = False, **kwargs) -> ToolResult:
        """Get current mouse cursor position with optional context about what's under cursor
        
        Args:
            include_context: If True, also get info about UI element under cursor
        """
        try:
            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
            
            pt = POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            
            data = {"x": pt.x, "y": pt.y}
            
            if include_context:
                # Get element under cursor using UI Automation
                context = await self._get_element_at_point(pt.x, pt.y)
                if context:
                    data["element_under_cursor"] = context
                
                # Get which monitor
                monitor_info = await self._get_monitor_at_point(pt.x, pt.y)
                if monitor_info:
                    data["monitor"] = monitor_info
            
            msg = f"Mouse at ({pt.x}, {pt.y})"
            if include_context and "element_under_cursor" in data:
                elem = data["element_under_cursor"]
                if elem.get("name"):
                    msg += f" over '{elem.get('name')}' ({elem.get('control_type', 'unknown')})"
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=data,
                message=msg
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _get_element_at_point(self, x: int, y: int) -> Optional[Dict[str, Any]]:
        """Get UI element information at a specific point using UI Automation"""
        try:
            cmd = f'''
            Add-Type -AssemblyName UIAutomationClient
            Add-Type -AssemblyName UIAutomationTypes
            
            $point = New-Object System.Windows.Point({x}, {y})
            $element = [System.Windows.Automation.AutomationElement]::FromPoint($point)
            
            if ($element) {{
                $result = @{{
                    name = $element.Current.Name
                    control_type = $element.Current.ControlType.ProgrammaticName
                    class_name = $element.Current.ClassName
                    automation_id = $element.Current.AutomationId
                    is_enabled = $element.Current.IsEnabled
                    is_keyboard_focusable = $element.Current.IsKeyboardFocusable
                    bounding_rect = @{{
                        x = $element.Current.BoundingRectangle.X
                        y = $element.Current.BoundingRectangle.Y
                        width = $element.Current.BoundingRectangle.Width
                        height = $element.Current.BoundingRectangle.Height
                    }}
                    process_id = $element.Current.ProcessId
                }}
                
                # Try to get parent window info
                try {{
                    $walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker
                    $parent = $element
                    while ($parent -and $parent.Current.ControlType.ProgrammaticName -ne "ControlType.Window") {{
                        $parent = $walker.GetParent($parent)
                    }}
                    if ($parent) {{
                        $result.window_title = $parent.Current.Name
                    }}
                }} catch {{}}
                
                $result | ConvertTo-Json -Depth 3
            }}
            '''
            
            result = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout.strip())
        except Exception as e:
            logging.debug(f"Error getting element at point: {e}")
        return None
    
    async def _get_monitor_at_point(self, x: int, y: int) -> Optional[Dict[str, Any]]:
        """Get monitor information for a specific point"""
        try:
            cmd = f'''
            Add-Type -AssemblyName System.Windows.Forms
            $monitors = [System.Windows.Forms.Screen]::AllScreens
            $index = 0
            foreach ($mon in $monitors) {{
                if ({x} -ge $mon.Bounds.X -and {x} -lt ($mon.Bounds.X + $mon.Bounds.Width) -and
                    {y} -ge $mon.Bounds.Y -and {y} -lt ($mon.Bounds.Y + $mon.Bounds.Height)) {{
                    @{{
                        index = $index
                        is_primary = $mon.Primary
                        device_name = $mon.DeviceName
                        bounds = @{{
                            x = $mon.Bounds.X
                            y = $mon.Bounds.Y
                            width = $mon.Bounds.Width
                            height = $mon.Bounds.Height
                        }}
                        relative_position = @{{
                            x = {x} - $mon.Bounds.X
                            y = {y} - $mon.Bounds.Y
                        }}
                    }} | ConvertTo-Json -Depth 3
                    break
                }}
                $index++
            }}
            '''
            
            result = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout.strip())
        except Exception:
            pass
        return None
    
    async def _find_clickable_element(self, element_name: str, window_title: str = "", **kwargs) -> ToolResult:
        """Find a clickable element by name (button, link, menu item) and return its location
        
        Common searches: "OK", "Cancel", "Close", "Accept", "Yes", "No", "Save", "Open", etc.
        """
        try:
            # Escape quotes in search terms
            safe_name = element_name.replace("'", "''").replace('"', '`"')
            safe_title = window_title.replace("'", "''").replace('"', '`"') if window_title else ""
            
            cmd = f'''
            Add-Type -AssemblyName UIAutomationClient
            Add-Type -AssemblyName UIAutomationTypes
            
            $results = @()
            $root = [System.Windows.Automation.AutomationElement]::RootElement
            
            # Find target window or use root
            $searchRoot = $root
            if ("{safe_title}") {{
                $windowCondition = New-Object System.Windows.Automation.PropertyCondition(
                    [System.Windows.Automation.AutomationElement]::NameProperty, 
                    "*{safe_title}*"
                )
                $windows = $root.FindAll([System.Windows.Automation.TreeScope]::Children, 
                    [System.Windows.Automation.Condition]::TrueCondition)
                foreach ($win in $windows) {{
                    if ($win.Current.Name -like "*{safe_title}*") {{
                        $searchRoot = $win
                        break
                    }}
                }}
            }}
            
            # Search for clickable elements with matching name
            $nameCondition = New-Object System.Windows.Automation.PropertyCondition(
                [System.Windows.Automation.AutomationElement]::NameProperty, 
                "{safe_name}"
            )
            
            # Also search for partial matches
            $allElements = $searchRoot.FindAll([System.Windows.Automation.TreeScope]::Descendants, 
                [System.Windows.Automation.Condition]::TrueCondition)
            
            foreach ($elem in $allElements) {{
                $name = $elem.Current.Name
                $controlType = $elem.Current.ControlType.ProgrammaticName
                
                # Check if name matches (exact or contains)
                if ($name -and ($name -eq "{safe_name}" -or $name -like "*{safe_name}*")) {{
                    # Only include clickable types
                    $clickableTypes = @("ControlType.Button", "ControlType.MenuItem", "ControlType.Hyperlink", 
                                       "ControlType.ListItem", "ControlType.TabItem", "ControlType.TreeItem",
                                       "ControlType.CheckBox", "ControlType.RadioButton", "ControlType.SplitButton")
                    
                    if ($clickableTypes -contains $controlType -or $elem.Current.IsKeyboardFocusable) {{
                        $rect = $elem.Current.BoundingRectangle
                        if ($rect.Width -gt 0 -and $rect.Height -gt 0) {{
                            $results += @{{
                                name = $name
                                control_type = $controlType
                                automation_id = $elem.Current.AutomationId
                                is_enabled = $elem.Current.IsEnabled
                                center_x = [int]($rect.X + $rect.Width / 2)
                                center_y = [int]($rect.Y + $rect.Height / 2)
                                bounds = @{{
                                    x = [int]$rect.X
                                    y = [int]$rect.Y
                                    width = [int]$rect.Width
                                    height = [int]$rect.Height
                                }}
                            }}
                        }}
                    }}
                }}
                
                if ($results.Count -ge 10) {{ break }}
            }}
            
            $results | ConvertTo-Json -Depth 3
            '''
            
            result = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0 and result.stdout.strip():
                elements = json.loads(result.stdout.strip())
                if isinstance(elements, dict):
                    elements = [elements]
                
                if elements:
                    # Return first enabled element
                    for elem in elements:
                        if elem.get("is_enabled", True):
                            return ToolResult(
                                status=ToolStatus.SUCCESS,
                                data=elem,
                                message=f"Found '{elem['name']}' at ({elem['center_x']}, {elem['center_y']})"
                            )
                    
                    # If no enabled, return first anyway
                    elem = elements[0]
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data=elem,
                        message=f"Found '{elem['name']}' (disabled) at ({elem['center_x']}, {elem['center_y']})"
                    )
            
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Could not find element '{element_name}'",
                message=f"No clickable element named '{element_name}' found"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _click_element_by_name(self, element_name: str, window_title: str = "", 
                                      double: bool = False, **kwargs) -> ToolResult:
        """Find an element by name and click it
        
        Common uses: click "OK", click "Cancel", click "Close", click "Accept"
        """
        try:
            # First find the element
            find_result = await self._find_clickable_element(element_name, window_title)
            
            if find_result.status != ToolStatus.SUCCESS:
                return find_result
            
            elem = find_result.data
            x, y = elem["center_x"], elem["center_y"]
            
            # Move mouse and click
            user32.SetCursorPos(x, y)
            await asyncio.sleep(0.05)  # Small delay for UI to register
            
            clicks = 2 if double else 1
            for _ in range(clicks):
                user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                if double:
                    await asyncio.sleep(0.05)
            
            action = "Double-clicked" if double else "Clicked"
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"element": elem, "clicked_at": {"x": x, "y": y}},
                message=f"{action} '{elem['name']}' at ({x}, {y})"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    # ==================== SCREEN READING METHODS ====================
    
    async def _read_screen(self, method: str = "ocr", region: str = "", 
                           estimate_only: bool = False) -> ToolResult:
        """Read screen content using various methods.
        
        Methods:
        - ocr: Extract text using Windows OCR (LOW tokens ~500-2000)
        - ui_tree: Get UI Automation elements (LOWEST tokens ~100-500)
        - screenshot_path: Save screenshot, return path only (NO tokens for image)
        
        Use estimate_only=True to get token cost estimate without reading.
        """
        try:
            # Token cost estimates
            token_estimates = {
                "ocr": "~500-2000 tokens (text only, efficient)",
                "ui_tree": "~100-500 tokens (structured data, most efficient)",
                "screenshot_path": "~50 tokens (path only, you review manually)",
                "vision_api": "~2000-6000 tokens (EXPENSIVE - sends image to AI)"
            }
            
            if estimate_only:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={
                        "token_estimates": token_estimates,
                        "recommendation": "Use 'ui_tree' for navigation, 'ocr' for reading text, 'screenshot_path' for manual review",
                        "warning": "Avoid continuous screen reading - tokens add up fast!"
                    },
                    message="Token estimates for screen reading methods"
                )
            
            if method == "ocr":
                return await self._ocr_screen(region)
            elif method == "ui_tree":
                return await self._get_ui_elements()
            elif method == "screenshot_path":
                # Just take screenshot and return path
                result = await self._screenshot()
                if result.status == ToolStatus.SUCCESS:
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data={
                            "path": result.data.get("path"),
                            "token_cost": "~50 tokens (path only)",
                            "note": "Screenshot saved - review manually or use OCR on specific region"
                        },
                        message=f"Screenshot saved to {result.data.get('path')}"
                    )
                return result
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Unknown method: {method}. Use: ocr, ui_tree, screenshot_path"
                )
                
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _ocr_screen(self, region: str = "") -> ToolResult:
        """Extract text from screen using Windows OCR"""
        try:
            # Use PowerShell with Windows.Media.Ocr
            if region:
                # Parse region "x,y,width,height"
                parts = region.split(",")
                if len(parts) == 4:
                    reg_x, reg_y, reg_w, reg_h = map(int, parts)
                    capture_region = f"$x={reg_x}; $y={reg_y}; $w={reg_w}; $h={reg_h}"
                else:
                    capture_region = "$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; $x=0; $y=0; $w=$screen.Width; $h=$screen.Height"
            else:
                capture_region = "$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; $x=0; $y=0; $w=$screen.Width; $h=$screen.Height"
            
            # PowerShell script for OCR - use string concat to avoid f-string escaping issues
            ps_script = "Add-Type -AssemblyName System.Drawing\n" + capture_region + '''
$bitmap = New-Object System.Drawing.Bitmap($w, $h)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($x, $y, 0, 0, (New-Object System.Drawing.Size($w, $h)))

# Save to temp file for OCR
$tempFile = [System.IO.Path]::GetTempFileName() + ".png"
$bitmap.Save($tempFile)
$graphics.Dispose()
$bitmap.Dispose()

# Use Windows OCR via PowerShell
try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    $null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
    $null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime]
    $null = [Windows.Storage.StorageFile, Windows.Foundation, ContentType = WindowsRuntime]
    
    $ocrEngine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
    
    $file = [Windows.Storage.StorageFile]::GetFileFromPathAsync($tempFile).GetAwaiter().GetResult()
    $stream = $file.OpenAsync([Windows.Storage.FileAccessMode]::Read).GetAwaiter().GetResult()
    $decoder = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream).GetAwaiter().GetResult()
    $softwareBitmap = $decoder.GetSoftwareBitmapAsync().GetAwaiter().GetResult()
    
    $ocrResult = $ocrEngine.RecognizeAsync($softwareBitmap).GetAwaiter().GetResult()
    $ocrResult.Text
    
    $stream.Dispose()
    Remove-Item $tempFile -Force
} catch {
    # Fallback: just report we need tesseract
    "OCR_FALLBACK_NEEDED"
}
'''
            result = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            text = result.stdout.strip()
            
            if text == "OCR_FALLBACK_NEEDED" or not text:
                # Fallback to simpler method - get window titles and visible text
                return await self._read_window_text()
            
            # Estimate tokens (roughly 1 token per 4 chars)
            token_estimate = len(text) // 4
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "text": text[:5000],  # Limit to prevent huge responses
                    "char_count": len(text),
                    "token_estimate": token_estimate,
                    "method": "windows_ocr"
                },
                message=f"Extracted {len(text)} chars (~{token_estimate} tokens)"
            )
            
        except Exception:
            # Fallback to window text
            return await self._read_window_text()
    
    async def _read_window_text(self, window_title: str = "", estimate_only: bool = False, **kwargs) -> ToolResult:
        """Read text from windows using UI Automation (fallback, low tokens)"""
        try:
            if estimate_only:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"token_estimate": 50, "method": "window_titles"},
                    message="Estimated ~50 tokens for window titles (very low cost)"
                )
            if window_title:
                filter_cmd = f"| Where-Object {{ $_.MainWindowTitle -like '*{window_title}*' }}"
            else:
                filter_cmd = "| Where-Object { $_.MainWindowTitle -ne '' }"
            
            cmd = f'''
            Get-Process {filter_cmd} | 
            Select-Object -First 10 ProcessName, MainWindowTitle |
            ForEach-Object {{ "$($_.ProcessName): $($_.MainWindowTitle)" }}
            '''
            
            result = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            text = result.stdout.strip()
            lines = [line for line in text.split('\n') if line.strip()]
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "windows": lines,
                    "count": len(lines),
                    "token_estimate": len(text) // 4,
                    "method": "window_titles"
                },
                message=f"Found {len(lines)} windows (~{len(text)//4} tokens)"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _get_ui_elements(self, window_title: str = "", element_type: str = "", estimate_only: bool = False, **kwargs) -> ToolResult:
        """Get UI Automation elements (LOWEST token cost for screen reading)"""
        try:
            if estimate_only:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"token_estimate": 100, "method": "ui_automation"},
                    message="Estimated ~100 tokens for UI elements (LOWEST cost method)"
                )
            # Build filter conditions
            name_filter = f'$name -like "*{window_title}*"' if window_title else '$name.Length -gt 0'
            type_check = f'$win.Current.ControlType.ProgrammaticName -like "*{element_type}*"' if element_type else '$true'
            
            cmd = f'''
            Add-Type -AssemblyName UIAutomationClient
            Add-Type -AssemblyName UIAutomationTypes
            
            $root = [System.Windows.Automation.AutomationElement]::RootElement
            $condition = [System.Windows.Automation.Condition]::TrueCondition
            
            # Get top-level windows
            $windows = $root.FindAll([System.Windows.Automation.TreeScope]::Children, $condition)
            
            $results = @()
            foreach ($win in $windows) {{
                try {{
                    $name = $win.Current.Name
                    if ($name -and ({name_filter}) -and ({type_check})) {{
                        $results += @{{
                            Name = $name
                            Type = $win.Current.ControlType.ProgrammaticName
                            ClassName = $win.Current.ClassName
                            ProcessId = $win.Current.ProcessId
                        }}
                    }}
                }} catch {{}}
            }}
            
            $results | Select-Object -First 20 | ConvertTo-Json
            '''
            
            result = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0 and result.stdout.strip():
                elements = json.loads(result.stdout)
                if isinstance(elements, dict):
                    elements = [elements]
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={
                        "elements": elements,
                        "count": len(elements),
                        "token_estimate": len(result.stdout) // 4,
                        "method": "ui_automation"
                    },
                    message=f"Found {len(elements)} UI elements (~{len(result.stdout)//4} tokens) - MOST EFFICIENT"
                )
            
            # Fallback to window list
            return await self._read_window_text()
            
        except Exception:
            return await self._read_window_text()
    
    async def _find_ui_element(self, name: str = "", element_type: str = "Button", 
                                window_title: str = "", estimate_only: bool = False, **kwargs) -> ToolResult:
        """Find a specific UI element by name or type"""
        try:
            if estimate_only:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"token_estimate": 150, "method": "ui_automation_search"},
                    message="Estimated ~150 tokens for element search"
                )
            
            search_name = name if name else "*"
            
            cmd = f'''
            Add-Type -AssemblyName UIAutomationClient
            Add-Type -AssemblyName UIAutomationTypes
            
            $root = [System.Windows.Automation.AutomationElement]::RootElement
            
            # Find by name condition
            $nameCondition = New-Object System.Windows.Automation.PropertyCondition(
                [System.Windows.Automation.AutomationElement]::NameProperty, 
                "{search_name}",
                [System.Windows.Automation.PropertyConditionFlags]::IgnoreCase
            )
            
            $elements = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $nameCondition)
            
            $results = @()
            foreach ($el in $elements) {{
                try {{
                    $rect = $el.Current.BoundingRectangle
                    if (-not $rect.IsEmpty) {{
                        $results += @{{
                            Name = $el.Current.Name
                            Type = $el.Current.ControlType.ProgrammaticName
                            X = [int]$rect.X
                            Y = [int]$rect.Y
                            Width = [int]$rect.Width
                            Height = [int]$rect.Height
                            IsEnabled = $el.Current.IsEnabled
                        }}
                    }}
                }} catch {{}}
            }}
            
            $results | Select-Object -First 10 | ConvertTo-Json
            '''
            
            result = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=20
            )
            
            if result.returncode == 0 and result.stdout.strip():
                elements = json.loads(result.stdout)
                if isinstance(elements, dict):
                    elements = [elements]
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={
                        "elements": elements,
                        "count": len(elements),
                        "search": {"name": name, "type": element_type}
                    },
                    message=f"Found {len(elements)} elements matching '{name}'"
                )
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"elements": [], "count": 0},
                message=f"No elements found matching '{name}'"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _click_ui_element(self, name: str, element_type: str = "", **kwargs) -> ToolResult:
        """Find and click a UI element by name"""
        try:
            # First find the element
            find_result = await self._find_ui_element(name=name, element_type=element_type)
            
            if find_result.status != ToolStatus.SUCCESS:
                return find_result
            
            elements = find_result.data.get("elements", [])
            if not elements:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"No element found with name '{name}'"
                )
            
            # Get first matching element's center
            el = elements[0]
            center_x = el.get("X", 0) + el.get("Width", 0) // 2
            center_y = el.get("Y", 0) + el.get("Height", 0) // 2
            
            # Move and click
            await self._move_mouse(x=center_x, y=center_y)
            await asyncio.sleep(0.1)
            await self._click_mouse(button="left")
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "element": el.get("Name"),
                    "clicked_at": {"x": center_x, "y": center_y}
                },
                message=f"Clicked '{el.get('Name')}' at ({center_x}, {center_y})"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _get_focused_element(self, **kwargs) -> ToolResult:
        """Get information about the currently focused UI element"""
        try:
            cmd = '''
            Add-Type -AssemblyName UIAutomationClient
            Add-Type -AssemblyName UIAutomationTypes
            
            $focused = [System.Windows.Automation.AutomationElement]::FocusedElement
            
            if ($focused) {
                @{
                    Name = $focused.Current.Name
                    Type = $focused.Current.ControlType.ProgrammaticName
                    ClassName = $focused.Current.ClassName
                    AutomationId = $focused.Current.AutomationId
                    ProcessId = $focused.Current.ProcessId
                    IsEnabled = $focused.Current.IsEnabled
                    HasKeyboardFocus = $focused.Current.HasKeyboardFocus
                    BoundingRectangle = @{
                        X = $focused.Current.BoundingRectangle.X
                        Y = $focused.Current.BoundingRectangle.Y
                        Width = $focused.Current.BoundingRectangle.Width
                        Height = $focused.Current.BoundingRectangle.Height
                    }
                } | ConvertTo-Json
            } else {
                '{"error": "No focused element"}'
            }
            '''
            
            result = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                element = json.loads(result.stdout)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=element,
                    message=f"Focused: {element.get('Name', 'Unknown')} ({element.get('Type', 'Unknown')})"
                )
            
            return ToolResult(status=ToolStatus.ERROR, error="Could not get focused element")
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _read_window_content(self, window_title: str, max_depth: int = 3, **kwargs) -> ToolResult:
        """Read all text content from a specific window by title"""
        try:
            cmd = f'''
            Add-Type -AssemblyName UIAutomationClient
            Add-Type -AssemblyName UIAutomationTypes
            
            $root = [System.Windows.Automation.AutomationElement]::RootElement
            $condition = [System.Windows.Automation.Condition]::TrueCondition
            
            # Find window by title
            $windows = $root.FindAll([System.Windows.Automation.TreeScope]::Children, $condition)
            $targetWindow = $null
            
            foreach ($win in $windows) {{
                if ($win.Current.Name -like "*{window_title}*") {{
                    $targetWindow = $win
                    break
                }}
            }}
            
            if (-not $targetWindow) {{
                Write-Output '{{"error": "Window not found"}}'
                exit
            }}
            
            # Get all text elements
            $textCondition = New-Object System.Windows.Automation.PropertyCondition(
                [System.Windows.Automation.AutomationElement]::IsTextPatternAvailableProperty, $true
            )
            
            $results = @()
            $allElements = $targetWindow.FindAll([System.Windows.Automation.TreeScope]::Descendants, $condition)
            
            foreach ($el in $allElements) {{
                try {{
                    $name = $el.Current.Name
                    if ($name -and $name.Length -gt 0) {{
                        $results += @{{
                            Text = $name
                            Type = $el.Current.ControlType.ProgrammaticName
                        }}
                    }}
                }} catch {{}}
            }}
            
            @{{
                WindowTitle = $targetWindow.Current.Name
                ElementCount = $results.Count
                Content = $results | Select-Object -First 50
            }} | ConvertTo-Json -Depth 3
            '''
            
            result = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=20
            )
            
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                if "error" in data:
                    return ToolResult(status=ToolStatus.ERROR, error=data["error"])
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=data,
                    message=f"Read {data.get('ElementCount', 0)} elements from '{data.get('WindowTitle', window_title)}'"
                )
            
            return ToolResult(status=ToolStatus.ERROR, error="Could not read window content")
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _read_text_at_position(self, x: int, y: int, **kwargs) -> ToolResult:
        """Read UI element text at specific screen coordinates"""
        try:
            cmd = f'''
            Add-Type -AssemblyName UIAutomationClient
            Add-Type -AssemblyName UIAutomationTypes
            
            $point = New-Object System.Windows.Point({x}, {y})
            $element = [System.Windows.Automation.AutomationElement]::FromPoint($point)
            
            if ($element) {{
                @{{
                    Name = $element.Current.Name
                    Type = $element.Current.ControlType.ProgrammaticName
                    ClassName = $element.Current.ClassName
                    AutomationId = $element.Current.AutomationId
                    Value = ""
                    Position = @{{ X = {x}; Y = {y} }}
                    BoundingRectangle = @{{
                        X = $element.Current.BoundingRectangle.X
                        Y = $element.Current.BoundingRectangle.Y
                        Width = $element.Current.BoundingRectangle.Width
                        Height = $element.Current.BoundingRectangle.Height
                    }}
                }} | ConvertTo-Json
            }} else {{
                '{{"error": "No element at position"}}'
            }}
            '''
            
            result = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                if "error" in data:
                    return ToolResult(status=ToolStatus.ERROR, error=data["error"])
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=data,
                    message=f"At ({x}, {y}): {data.get('Name', 'Unknown')} ({data.get('Type', 'Unknown')})"
                )
            
            return ToolResult(status=ToolStatus.ERROR, error="Could not read element at position")
            
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
                            "get_mouse_position", "find_clickable_element", "click_element_by_name",
                            "read_screen", "read_window_text", "get_ui_elements",
                            "find_ui_element", "click_ui_element",
                            "get_focused_element", "read_window_content", "read_text_at_position"
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
                    "script_content": {"type": "string", "description": f"Script code to execute (saved to ~/Documents/{ASSISTANT_NAME}/scripts/)"},
                    "script_type": {
                        "type": "string",
                        "enum": ["powershell", "python", "batch", "cmd", "javascript", "vbscript"],
                        "description": "Type of script to execute",
                        "default": "powershell"
                    },
                    "script_name": {"type": "string", "description": "Name for the script file (optional, auto-generated if not provided)"},
                    "execute": {"type": "boolean", "description": "Execute the script after creating (default true)", "default": True},
                    "x": {"type": "integer", "description": "X coordinate for mouse movement or position query"},
                    "y": {"type": "integer", "description": "Y coordinate for mouse movement or position query"},
                    "absolute": {"type": "boolean", "description": "Use absolute coordinates (default true)", "default": True},
                    "monitor": {"type": "integer", "description": "Monitor index for mouse movement (0=primary, 1=second, etc). If set, x/y are relative to that monitor"},
                    "include_context": {"type": "boolean", "description": "For get_mouse_position: include info about element under cursor and monitor", "default": False},
                    "element_name": {"type": "string", "description": "Name of element to find/click (e.g., 'OK', 'Cancel', 'Close', 'Accept', 'Save')"},
                    "window_title": {"type": "string", "description": "Window title to search within (optional, searches all windows if not specified)"},
                    "button": {"type": "string", "enum": ["left", "right"], "description": "Mouse button to click", "default": "left"},
                    "double": {"type": "boolean", "description": "Double-click", "default": False},
                    "method": {
                        "type": "string",
                        "enum": ["ocr", "ui_tree", "screenshot_path"],
                        "description": "Screen reading method: ui_tree (lowest tokens), ocr (medium), screenshot_path (highest - returns path for vision)",
                        "default": "ui_tree"
                    },
                    "region": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "integer"},
                            "y": {"type": "integer"},
                            "width": {"type": "integer"},
                            "height": {"type": "integer"}
                        },
                        "description": "Screen region to read (optional, full screen if not specified)"
                    },
                    "estimate_only": {"type": "boolean", "description": "Only estimate token cost without reading", "default": False},
                    "element_type": {"type": "string", "description": "Filter UI elements by type (Button, Edit, Text, etc.)"},
                    "max_depth": {"type": "integer", "description": "Max depth for UI tree traversal", "default": 3}
                },
                "required": ["action"]
            }
        }
    
    async def cleanup(self):
        """Cleanup Windows automation"""
        pass
