"""
Developer Tools for Sakura
Git operations, code execution, package management, SSH/SMB/FTP/RDP connections

Rules followed:
- All imports MUST be used
- Async with asyncio.Lock() for thread safety
- aiofiles for file I/O
- Database for connection profiles (FTS search, history)
"""
import asyncio
import logging
import os
import subprocess
import shutil
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import json
import aiofiles
from ..base import BaseTool, ToolResult, ToolStatus

# Database import for connection profiles
try:
    from modules.database import DatabaseManager
    HAS_DATABASE = True
except ImportError:
    HAS_DATABASE = False
    logging.warning("Database module not available - profiles will use JSON only")

# Paramiko for SFTP support
try:
    import paramiko
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False
    logging.warning("paramiko not installed - SFTP features limited. Install with: pip install paramiko")


# Get assistant name for data folder
ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "Sakura")


@dataclass
class ConnectionProfile:
    """Universal connection profile for SSH, SMB, FTP, RDP, etc."""
    id: str
    profile_type: str  # ssh, smb, ftp, sftp, rdp
    name: str
    host: str
    port: int = 0  # 0 = use default for type
    username: str = ""
    auth_type: str = "password"  # password, key, ntlm, kerberos
    key_path: Optional[str] = None
    domain: Optional[str] = None  # For SMB/RDP
    share_path: Optional[str] = None  # For SMB
    remote_path: Optional[str] = None  # Default remote directory
    local_path: Optional[str] = None  # Default local directory
    use_ssl: bool = False  # For FTP -> FTPS
    passive_mode: bool = True  # For FTP
    extra_config: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    last_used: Optional[str] = None
    use_count: int = 0
    
    def __post_init__(self):
        """Validate connection profile after initialization"""
        # Required fields
        if not self.id or not self.id.strip():
            raise ValueError("Profile ID is required and cannot be empty")
        if not self.name or not self.name.strip():
            raise ValueError("Profile name is required and cannot be empty")
        if not self.host or not self.host.strip():
            raise ValueError("Host is required and cannot be empty")
        if not self.profile_type or self.profile_type not in ["ssh", "sftp", "smb", "ftp", "ftps", "rdp"]:
            raise ValueError(f"Invalid profile_type: {self.profile_type}. Must be one of: ssh, sftp, smb, ftp, ftps, rdp")
        
        # Port validation
        if self.port < 0 or self.port > 65535:
            raise ValueError(f"Invalid port: {self.port}. Port must be between 0 and 65535")
        
        # Auth type validation
        valid_auth_types = ["password", "key", "ntlm", "kerberos"]
        if self.auth_type not in valid_auth_types:
            raise ValueError(f"Invalid auth_type: {self.auth_type}. Must be one of: {', '.join(valid_auth_types)}")
        
        # Key auth requires key_path
        if self.auth_type == "key" and (not self.key_path or not self.key_path.strip()):
            raise ValueError("auth_type='key' requires key_path to be set")
        
        # Default port assignment happens in get_default_port, no validation needed here
    
    def get_default_port(self) -> int:
        """Get default port for profile type"""
        defaults = {
            "ssh": 22,
            "sftp": 22,
            "ftp": 21,
            "ftps": 990,
            "smb": 445,
            "rdp": 3389
        }
        return self.port if self.port > 0 else defaults.get(self.profile_type, 0)


# Legacy dataclass for backward compatibility
@dataclass
class SSHConnection:
    """SSH connection profile (legacy, for migration)"""
    id: str
    name: str
    host: str
    port: int = 22
    username: str = ""
    auth_type: str = "password"  # password, key
    key_path: Optional[str] = None
    created_at: str = ""


class DeveloperTools(BaseTool):
    """Developer tools - Git, code execution, package management, connections (SSH/SMB/FTP/RDP)"""
    
    name = "developer"
    description = "Developer tools: Git operations (status, add, commit, push, pull, branch, log, diff), run code snippets (Python, JS, PowerShell, Batch), package management (pip, npm, winget), connections (SSH, SMB shares, FTP/SFTP, RDP)."
    
    def __init__(self):
        self._lock = asyncio.Lock()
        self.is_windows = os.name == 'nt'
        self.data_dir: Path = Path.home() / "Documents" / ASSISTANT_NAME / "developer"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Legacy SSH profiles file (for migration)
        self.ssh_profiles_file = self.data_dir / "ssh_profiles.json"
        self.ssh_profiles: Dict[str, SSHConnection] = {}  # Legacy, kept for migration
        
        # New unified connection profiles
        self.profiles_file = self.data_dir / "connection_profiles.json"  # JSON backup
        self.profiles: Dict[str, ConnectionProfile] = {}
        
        # Database for profiles
        self._db: Optional[DatabaseManager] = None
        self._db_available = False
        
        # Detect available tools
        self.available_tools: Dict[str, bool] = {}
        self._counter = 0
    
    async def initialize(self) -> bool:
        """Initialize developer tools"""
        try:
            # Initialize database for connection profiles
            if HAS_DATABASE:
                try:
                    self._db = DatabaseManager()
                    self._db_available = await self._db.initialize()
                    if self._db_available:
                        logging.info("Developer tools using database for connection profiles")
                        # Migrate legacy SSH profiles to database
                        await self._migrate_ssh_profiles_to_db()
                except Exception as e:
                    logging.warning(f"Database init failed, using JSON for profiles: {e}")
                    self._db_available = False
            
            # Detect available tools
            await self._detect_tools()
            
            # Load profiles (from DB or JSON)
            await self._load_profiles()
            
            available = [k for k, v in self.available_tools.items() if v]
            logging.info(f"Developer tools initialized. Available: {available}")
            return True
        except Exception as e:
            logging.error(f"Failed to initialize developer tools: {e}")
            return False
    
    async def _detect_tools(self):
        """Detect which developer tools are available on the system"""
        tools_to_check = {
            # Core dev tools
            "git": ["git", "--version"],
            "python": ["python", "--version"],
            "node": ["node", "--version"],
            "npm": ["npm", "--version"],
            "pip": ["pip", "--version"],
            "winget": ["winget", "--version"],
            # SSH tools
            "ssh": ["ssh", "-V"],
            "putty": ["putty", "-help"],  # PuTTY GUI
            "plink": ["plink", "-V"],  # PuTTY command-line
            "pscp": ["pscp", "-V"],  # PuTTY SCP
            # FTP tools
            "winscp": ["winscp", "/help"],  # WinSCP
            "ftp": ["ftp", "-?"] if self.is_windows else ["ftp", "--help"],
            # RDP
            "mstsc": ["mstsc", "/?"],  # Windows RDP client
            # SMB/Network
            "net": ["net", "help"],  # Windows net command
        }
        
        for tool, cmd in tools_to_check.items():
            try:
                proc_result = await asyncio.to_thread(
                    subprocess.run, cmd,
                    capture_output=True, text=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW if self.is_windows else 0
                )
                # Some tools return non-zero for help/version but still exist
                # Store version info if available
                self.available_tools[tool] = True
                version_output = proc_result.stdout.strip() or proc_result.stderr.strip()
                if version_output and len(version_output) < 100:
                    logging.debug(f"Tool {tool} version: {version_output[:50]}")
            except FileNotFoundError:
                self.available_tools[tool] = False
            except Exception:
                # Tool might exist but command failed - check with shutil.which
                self.available_tools[tool] = shutil.which(tool) is not None
    
    async def execute(self, action: str, **kwargs) -> ToolResult:
        """Execute developer tool action"""
        actions = {
            # Git operations
            "git_status": self._git_status,
            "git_add": self._git_add,
            "git_commit": self._git_commit,
            "git_push": self._git_push,
            "git_pull": self._git_pull,
            "git_branch": self._git_branch,
            "git_checkout": self._git_checkout,
            "git_log": self._git_log,
            "git_diff": self._git_diff,
            "git_clone": self._git_clone,
            "git_init": self._git_init,
            # Code execution
            "run_python": self._run_python,
            "run_javascript": self._run_javascript,
            "run_powershell": self._run_powershell,
            "run_batch": self._run_batch,
            # Package management
            "pip_install": self._pip_install,
            "pip_uninstall": self._pip_uninstall,
            "pip_list": self._pip_list,
            "npm_install": self._npm_install,
            "npm_uninstall": self._npm_uninstall,
            "npm_list": self._npm_list,
            "winget_search": self._winget_search,
            "winget_install": self._winget_install,
            "winget_uninstall": self._winget_uninstall,
            "winget_list": self._winget_list,
            # Connection Profiles (unified)
            "add_profile": self._add_profile,
            "list_profiles": self._list_profiles,
            "get_profile": self._get_profile,
            "delete_profile": self._delete_profile,
            "update_profile": self._update_profile,
            # SSH (legacy actions kept for compatibility)
            "ssh_connect": self._ssh_connect,
            "ssh_run_command": self._ssh_run_command,
            "ssh_add_profile": self._ssh_add_profile,  # Redirects to add_profile
            "ssh_list_profiles": self._ssh_list_profiles,  # Redirects to list_profiles
            "ssh_delete_profile": self._ssh_delete_profile,  # Redirects to delete_profile
            # SMB/Network shares
            "smb_connect": self._smb_connect,
            "smb_map_drive": self._smb_map_drive,
            "smb_unmap_drive": self._smb_unmap_drive,
            "smb_list_shares": self._smb_list_shares,
            # FTP/SFTP
            "ftp_connect": self._ftp_connect,
            "ftp_list": self._ftp_list,
            "ftp_upload": self._ftp_upload,
            "ftp_download": self._ftp_download,
            # RDP
            "rdp_connect": self._rdp_connect,
            # Utility
            "check_tools": self._check_tools,
            "find_tool_path": self._find_tool_path,
            "run_multiple_commands": self._run_multiple_commands,
        }
        
        if action not in actions:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Unknown action: {action}. Available: {list(actions.keys())}"
            )
        
        return await actions[action](**kwargs)

    
    # ==================== GIT OPERATIONS ====================
    
    async def _git_status(self, path: str = ".", **kwargs) -> ToolResult:
        """Get git status of a repository"""
        if not self.available_tools.get("git"):
            return ToolResult(status=ToolStatus.ERROR, error="Git is not installed")
        
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["git", "status", "--porcelain", "-b"],
                capture_output=True, text=True, timeout=30, cwd=path
            )
            
            if result.returncode != 0:
                return ToolResult(status=ToolStatus.ERROR, error=result.stderr.strip())
            
            lines = result.stdout.strip().split('\n')
            branch = lines[0].replace("## ", "") if lines else "unknown"
            
            # Parse status
            staged = []
            modified = []
            untracked = []
            
            for line in lines[1:]:
                if not line.strip():
                    continue
                status = line[:2]
                file = line[3:]
                
                if status[0] in ['A', 'M', 'D', 'R']:
                    staged.append({"status": status[0], "file": file})
                if status[1] == 'M':
                    modified.append(file)
                elif status == '??':
                    untracked.append(file)
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "branch": branch,
                    "staged": staged,
                    "modified": modified,
                    "untracked": untracked,
                    "clean": len(staged) == 0 and len(modified) == 0 and len(untracked) == 0
                },
                message=f"📂 Branch: {branch} | Staged: {len(staged)} | Modified: {len(modified)} | Untracked: {len(untracked)}"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _git_add(self, files: str = ".", path: str = ".", **kwargs) -> ToolResult:
        """Stage files for commit"""
        if not self.available_tools.get("git"):
            return ToolResult(status=ToolStatus.ERROR, error="Git is not installed")
        
        try:
            # Handle multiple files
            file_list = files.split() if ' ' in files else [files]
            
            result = await asyncio.to_thread(
                subprocess.run,
                ["git", "add"] + file_list,
                capture_output=True, text=True, timeout=30, cwd=path
            )
            
            if result.returncode != 0:
                return ToolResult(status=ToolStatus.ERROR, error=result.stderr.strip())
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"✅ Staged: {files}"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _git_commit(self, message: str, path: str = ".", **kwargs) -> ToolResult:
        """Commit staged changes"""
        if not self.available_tools.get("git"):
            return ToolResult(status=ToolStatus.ERROR, error="Git is not installed")
        
        if not message:
            return ToolResult(status=ToolStatus.ERROR, error="Commit message is required")
        
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["git", "commit", "-m", message],
                capture_output=True, text=True, timeout=30, cwd=path
            )
            
            if result.returncode != 0:
                error = result.stderr.strip() or result.stdout.strip()
                return ToolResult(status=ToolStatus.ERROR, error=error)
            
            # Extract commit hash from output
            output = result.stdout.strip()
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"output": output},
                message=f"✅ Committed: {message[:50]}..."
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _git_push(self, remote: str = "origin", branch: str = "", path: str = ".", **kwargs) -> ToolResult:
        """Push commits to remote"""
        if not self.available_tools.get("git"):
            return ToolResult(status=ToolStatus.ERROR, error="Git is not installed")
        
        try:
            cmd = ["git", "push", remote]
            if branch:
                cmd.append(branch)
            
            result = await asyncio.to_thread(
                subprocess.run, cmd,
                capture_output=True, text=True, timeout=60, cwd=path
            )
            
            if result.returncode != 0:
                error = result.stderr.strip()
                return ToolResult(status=ToolStatus.ERROR, error=error)
            
            output = result.stderr.strip() or result.stdout.strip()  # Git push outputs to stderr
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"output": output},
                message=f"✅ Pushed to {remote}"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _git_pull(self, remote: str = "origin", branch: str = "", path: str = ".", **kwargs) -> ToolResult:
        """Pull changes from remote"""
        if not self.available_tools.get("git"):
            return ToolResult(status=ToolStatus.ERROR, error="Git is not installed")
        
        try:
            cmd = ["git", "pull", remote]
            if branch:
                cmd.append(branch)
            
            result = await asyncio.to_thread(
                subprocess.run, cmd,
                capture_output=True, text=True, timeout=60, cwd=path
            )
            
            if result.returncode != 0:
                return ToolResult(status=ToolStatus.ERROR, error=result.stderr.strip())
            
            output = result.stdout.strip()
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"output": output},
                message=f"✅ Pulled from {remote}"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _git_branch(self, name: str = "", delete: bool = False, path: str = ".", **kwargs) -> ToolResult:
        """List, create, or delete branches"""
        if not self.available_tools.get("git"):
            return ToolResult(status=ToolStatus.ERROR, error="Git is not installed")
        
        try:
            if delete and name:
                cmd = ["git", "branch", "-d", name]
            elif name:
                cmd = ["git", "branch", name]
            else:
                cmd = ["git", "branch", "-a"]
            
            result = await asyncio.to_thread(
                subprocess.run, cmd,
                capture_output=True, text=True, timeout=30, cwd=path
            )
            
            if result.returncode != 0:
                return ToolResult(status=ToolStatus.ERROR, error=result.stderr.strip())
            
            if not name:
                # Parse branch list
                branches = []
                current = None
                for line in result.stdout.strip().split('\n'):
                    line = line.strip()
                    if line.startswith('* '):
                        current = line[2:]
                        branches.append({"name": current, "current": True})
                    elif line:
                        branches.append({"name": line, "current": False})
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"branches": branches, "current": current},
                    message=f"🌿 {len(branches)} branches, current: {current}"
                )
            elif delete:
                return ToolResult(status=ToolStatus.SUCCESS, message=f"🗑️ Deleted branch: {name}")
            else:
                return ToolResult(status=ToolStatus.SUCCESS, message=f"🌿 Created branch: {name}")
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _git_checkout(self, branch: str, create: bool = False, path: str = ".", **kwargs) -> ToolResult:
        """Switch branches or create and switch"""
        if not self.available_tools.get("git"):
            return ToolResult(status=ToolStatus.ERROR, error="Git is not installed")
        
        try:
            if create:
                cmd = ["git", "checkout", "-b", branch]
            else:
                cmd = ["git", "checkout", branch]
            
            result = await asyncio.to_thread(
                subprocess.run, cmd,
                capture_output=True, text=True, timeout=30, cwd=path
            )
            
            if result.returncode != 0:
                return ToolResult(status=ToolStatus.ERROR, error=result.stderr.strip())
            
            action = "Created and switched to" if create else "Switched to"
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"🔀 {action} branch: {branch}"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _git_log(self, count: int = 10, oneline: bool = True, path: str = ".", **kwargs) -> ToolResult:
        """Show commit history"""
        if not self.available_tools.get("git"):
            return ToolResult(status=ToolStatus.ERROR, error="Git is not installed")
        
        try:
            if oneline:
                cmd = ["git", "log", f"-{count}", "--oneline"]
            else:
                cmd = ["git", "log", f"-{count}", "--pretty=format:%h|%an|%ar|%s"]
            
            result = await asyncio.to_thread(
                subprocess.run, cmd,
                capture_output=True, text=True, timeout=30, cwd=path
            )
            
            if result.returncode != 0:
                return ToolResult(status=ToolStatus.ERROR, error=result.stderr.strip())
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if oneline:
                    parts = line.split(' ', 1)
                    if len(parts) == 2:
                        commits.append({"hash": parts[0], "message": parts[1]})
                else:
                    parts = line.split('|')
                    if len(parts) == 4:
                        commits.append({
                            "hash": parts[0],
                            "author": parts[1],
                            "date": parts[2],
                            "message": parts[3]
                        })
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=commits,
                message=f"📜 Last {len(commits)} commits"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _git_diff(self, file: str = "", staged: bool = False, path: str = ".", **kwargs) -> ToolResult:
        """Show changes/diff"""
        if not self.available_tools.get("git"):
            return ToolResult(status=ToolStatus.ERROR, error="Git is not installed")
        
        try:
            cmd = ["git", "diff"]
            if staged:
                cmd.append("--staged")
            if file:
                cmd.append(file)
            
            result = await asyncio.to_thread(
                subprocess.run, cmd,
                capture_output=True, text=True, timeout=30, cwd=path
            )
            
            if result.returncode != 0:
                return ToolResult(status=ToolStatus.ERROR, error=result.stderr.strip())
            
            diff = result.stdout.strip()
            
            if not diff:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"diff": ""},
                    message="No changes"
                )
            
            # Truncate if too long
            if len(diff) > 5000:
                diff = diff[:5000] + "\n... (truncated)"
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"diff": diff},
                message=f"📝 Diff: {len(diff)} chars"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _git_clone(self, url: str, directory: str = "", path: str = ".", **kwargs) -> ToolResult:
        """Clone a repository"""
        if not self.available_tools.get("git"):
            return ToolResult(status=ToolStatus.ERROR, error="Git is not installed")
        
        try:
            cmd = ["git", "clone", url]
            if directory:
                cmd.append(directory)
            
            result = await asyncio.to_thread(
                subprocess.run, cmd,
                capture_output=True, text=True, timeout=120, cwd=path
            )
            
            if result.returncode != 0:
                return ToolResult(status=ToolStatus.ERROR, error=result.stderr.strip())
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"✅ Cloned: {url}"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _git_init(self, path: str = ".", **kwargs) -> ToolResult:
        """Initialize a new git repository"""
        if not self.available_tools.get("git"):
            return ToolResult(status=ToolStatus.ERROR, error="Git is not installed")
        
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["git", "init"],
                capture_output=True, text=True, timeout=30, cwd=path
            )
            
            if result.returncode != 0:
                return ToolResult(status=ToolStatus.ERROR, error=result.stderr.strip())
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"✅ Initialized git repository in {path}"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    
    # ==================== CODE EXECUTION ====================
    
    async def _run_python(self, code: str, timeout: int = 30, **kwargs) -> ToolResult:
        """Run Python code snippet"""
        if not self.available_tools.get("python"):
            return ToolResult(status=ToolStatus.ERROR, error="Python is not installed")
        
        try:
            # Use -c flag to run code directly
            result = await asyncio.to_thread(
                subprocess.run,
                ["python", "-c", code],
                capture_output=True, text=True, timeout=timeout
            )
            
            output = result.stdout.strip()
            error = result.stderr.strip()
            
            if result.returncode != 0:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    data={"output": output, "error": error},
                    error=error or "Python execution failed"
                )
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"output": output, "return_code": result.returncode},
                message=output[:500] if output else "Code executed (no output)"
            )
            
        except subprocess.TimeoutExpired:
            return ToolResult(status=ToolStatus.ERROR, error=f"Execution timed out after {timeout}s")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _run_javascript(self, code: str, timeout: int = 30, **kwargs) -> ToolResult:
        """Run JavaScript code snippet (requires Node.js)"""
        if not self.available_tools.get("node"):
            return ToolResult(status=ToolStatus.ERROR, error="Node.js is not installed")
        
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["node", "-e", code],
                capture_output=True, text=True, timeout=timeout
            )
            
            output = result.stdout.strip()
            error = result.stderr.strip()
            
            if result.returncode != 0:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    data={"output": output, "error": error},
                    error=error or "JavaScript execution failed"
                )
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"output": output, "return_code": result.returncode},
                message=output[:500] if output else "Code executed (no output)"
            )
            
        except subprocess.TimeoutExpired:
            return ToolResult(status=ToolStatus.ERROR, error=f"Execution timed out after {timeout}s")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _run_powershell(self, code: str, timeout: int = 30, **kwargs) -> ToolResult:
        """Run PowerShell code snippet"""
        if not self.is_windows:
            return ToolResult(status=ToolStatus.ERROR, error="PowerShell is only available on Windows")
        
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command", code],
                capture_output=True, text=True, timeout=timeout
            )
            
            output = result.stdout.strip()
            error = result.stderr.strip()
            
            if result.returncode != 0:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    data={"output": output, "error": error},
                    error=error or "PowerShell execution failed"
                )
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"output": output, "return_code": result.returncode},
                message=output[:500] if output else "Code executed (no output)"
            )
            
        except subprocess.TimeoutExpired:
            return ToolResult(status=ToolStatus.ERROR, error=f"Execution timed out after {timeout}s")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _run_batch(self, code: str, timeout: int = 30, **kwargs) -> ToolResult:
        """Run Batch/CMD code snippet"""
        if not self.is_windows:
            return ToolResult(status=ToolStatus.ERROR, error="Batch is only available on Windows")
        
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["cmd", "/c", code],
                capture_output=True, text=True, timeout=timeout
            )
            
            output = result.stdout.strip()
            error = result.stderr.strip()
            
            if result.returncode != 0:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    data={"output": output, "error": error},
                    error=error or "Batch execution failed"
                )
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"output": output, "return_code": result.returncode},
                message=output[:500] if output else "Code executed (no output)"
            )
            
        except subprocess.TimeoutExpired:
            return ToolResult(status=ToolStatus.ERROR, error=f"Execution timed out after {timeout}s")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    # ==================== PACKAGE MANAGEMENT ====================
    
    async def _pip_install(self, package: str, upgrade: bool = False, 
                           use_venv: bool = True, **kwargs) -> ToolResult:
        """Install Python package with pip
        
        Args:
            package: Package name to install
            upgrade: Upgrade if already installed
            use_venv: Install to project venv (default True). Set False for user/system install.
        """
        if not self.available_tools.get("pip"):
            return ToolResult(status=ToolStatus.ERROR, error="pip is not installed")
        
        try:
            # Determine which pip to use
            if use_venv:
                # Try project venv first
                project_venv_pip = Path(__file__).parent.parent.parent / ".venv" / "Scripts" / "pip.exe"
                if project_venv_pip.exists():
                    pip_cmd = str(project_venv_pip)
                else:
                    # Fall back to current directory venv
                    cwd_venv_pip = Path(".venv/Scripts/pip.exe")
                    if cwd_venv_pip.exists():
                        pip_cmd = str(cwd_venv_pip.absolute())
                    else:
                        pip_cmd = "pip"
            else:
                pip_cmd = "pip"
            
            cmd = [pip_cmd, "install"]
            if upgrade:
                cmd.append("--upgrade")
            cmd.append(package)
            
            result = await asyncio.to_thread(
                subprocess.run, cmd,
                capture_output=True, text=True, timeout=120
            )
            
            if result.returncode != 0:
                return ToolResult(status=ToolStatus.ERROR, error=result.stderr.strip())
            
            venv_note = " (to project venv)" if use_venv and "venv" in pip_cmd else " (to user packages)"
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"output": result.stdout.strip(), "pip_used": pip_cmd},
                message=f"📦 Installed: {package}{venv_note}"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _pip_uninstall(self, package: str, **kwargs) -> ToolResult:
        """Uninstall Python package"""
        if not self.available_tools.get("pip"):
            return ToolResult(status=ToolStatus.ERROR, error="pip is not installed")
        
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["pip", "uninstall", "-y", package],
                capture_output=True, text=True, timeout=60
            )
            
            if result.returncode != 0:
                return ToolResult(status=ToolStatus.ERROR, error=result.stderr.strip())
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"🗑️ Uninstalled: {package}"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _pip_list(self, outdated: bool = False, **kwargs) -> ToolResult:
        """List installed Python packages"""
        if not self.available_tools.get("pip"):
            return ToolResult(status=ToolStatus.ERROR, error="pip is not installed")
        
        try:
            cmd = ["pip", "list", "--format=json"]
            if outdated:
                cmd.append("--outdated")
            
            result = await asyncio.to_thread(
                subprocess.run, cmd,
                capture_output=True, text=True, timeout=60
            )
            
            if result.returncode != 0:
                return ToolResult(status=ToolStatus.ERROR, error=result.stderr.strip())
            
            packages = json.loads(result.stdout)
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=packages,
                message=f"📦 {len(packages)} packages" + (" (outdated)" if outdated else "")
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _npm_install(self, package: str = "", global_install: bool = False, 
                           dev: bool = False, path: str = ".", **kwargs) -> ToolResult:
        """Install npm package"""
        if not self.available_tools.get("npm"):
            return ToolResult(status=ToolStatus.ERROR, error="npm is not installed")
        
        try:
            cmd = ["npm", "install"]
            if global_install:
                cmd.append("-g")
            if dev:
                cmd.append("--save-dev")
            if package:
                cmd.append(package)
            
            result = await asyncio.to_thread(
                subprocess.run, cmd,
                capture_output=True, text=True, timeout=120, cwd=path
            )
            
            if result.returncode != 0:
                return ToolResult(status=ToolStatus.ERROR, error=result.stderr.strip())
            
            msg = f"📦 Installed: {package}" if package else "📦 Installed dependencies"
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"output": result.stdout.strip()},
                message=msg
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _npm_uninstall(self, package: str, global_install: bool = False, 
                             path: str = ".", **kwargs) -> ToolResult:
        """Uninstall npm package"""
        if not self.available_tools.get("npm"):
            return ToolResult(status=ToolStatus.ERROR, error="npm is not installed")
        
        try:
            cmd = ["npm", "uninstall"]
            if global_install:
                cmd.append("-g")
            cmd.append(package)
            
            result = await asyncio.to_thread(
                subprocess.run, cmd,
                capture_output=True, text=True, timeout=60, cwd=path
            )
            
            if result.returncode != 0:
                return ToolResult(status=ToolStatus.ERROR, error=result.stderr.strip())
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"🗑️ Uninstalled: {package}"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _npm_list(self, global_install: bool = False, depth: int = 0, 
                        path: str = ".", **kwargs) -> ToolResult:
        """List npm packages"""
        if not self.available_tools.get("npm"):
            return ToolResult(status=ToolStatus.ERROR, error="npm is not installed")
        
        try:
            cmd = ["npm", "list", "--json", f"--depth={depth}"]
            if global_install:
                cmd.append("-g")
            
            result = await asyncio.to_thread(
                subprocess.run, cmd,
                capture_output=True, text=True, timeout=60, cwd=path
            )
            
            # npm list returns non-zero if there are peer dep issues, but still outputs
            try:
                data = json.loads(result.stdout)
                deps = data.get("dependencies", {})
                packages = [{"name": k, "version": v.get("version", "?")} for k, v in deps.items()]
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=packages,
                    message=f"📦 {len(packages)} packages"
                )
            except json.JSONDecodeError:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"output": result.stdout.strip()},
                    message="Package list retrieved"
                )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _winget_search(self, query: str, **kwargs) -> ToolResult:
        """Search for packages with winget"""
        if not self.available_tools.get("winget"):
            return ToolResult(status=ToolStatus.ERROR, error="winget is not installed")
        
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["winget", "search", query],
                capture_output=True, text=True, timeout=60
            )
            
            if result.returncode != 0:
                return ToolResult(status=ToolStatus.ERROR, error=result.stderr.strip())
            
            # Parse output (table format)
            lines = result.stdout.strip().split('\n')
            packages = []
            
            # Skip header lines
            for line in lines[2:]:
                if line.strip():
                    packages.append(line.strip())
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"results": packages[:20]},  # Limit results
                message=f"🔍 Found {len(packages)} packages"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _winget_install(self, package: str, **kwargs) -> ToolResult:
        """Install package with winget"""
        if not self.available_tools.get("winget"):
            return ToolResult(status=ToolStatus.ERROR, error="winget is not installed")
        
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["winget", "install", "--accept-package-agreements", "--accept-source-agreements", package],
                capture_output=True, text=True, timeout=300
            )
            
            if result.returncode != 0:
                return ToolResult(status=ToolStatus.ERROR, error=result.stderr.strip() or result.stdout.strip())
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"output": result.stdout.strip()},
                message=f"📦 Installed: {package}"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _winget_uninstall(self, package: str, **kwargs) -> ToolResult:
        """Uninstall package with winget"""
        if not self.available_tools.get("winget"):
            return ToolResult(status=ToolStatus.ERROR, error="winget is not installed")
        
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["winget", "uninstall", package],
                capture_output=True, text=True, timeout=120
            )
            
            if result.returncode != 0:
                return ToolResult(status=ToolStatus.ERROR, error=result.stderr.strip() or result.stdout.strip())
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"🗑️ Uninstalled: {package}"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _winget_list(self, **kwargs) -> ToolResult:
        """List installed packages with winget"""
        if not self.available_tools.get("winget"):
            return ToolResult(status=ToolStatus.ERROR, error="winget is not installed")
        
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["winget", "list"],
                capture_output=True, text=True, timeout=60
            )
            
            if result.returncode != 0:
                return ToolResult(status=ToolStatus.ERROR, error=result.stderr.strip())
            
            lines = result.stdout.strip().split('\n')
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"output": result.stdout.strip()[:3000]},
                message=f"📦 {len(lines) - 2} packages installed"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    
    # ==================== CONNECTION PROFILES (Unified) ====================
    
    async def _add_profile(self, profile_type: str, name: str, host: str, 
                           username: str = "", port: int = 0,
                           auth_type: str = "password", key_path: str = None,
                           domain: str = None, share_path: str = None,
                           remote_path: str = None, local_path: str = None,
                           use_ssl: bool = False, passive_mode: bool = True,
                           extra_config: Dict = None, **kwargs) -> ToolResult:
        """Add a connection profile (SSH, SMB, FTP, SFTP, RDP)
        
        Args:
            profile_type: Type of connection - ssh, smb, ftp, sftp, rdp
            name: User-friendly name for the profile
            host: Hostname or IP address
            username: Username for authentication
            port: Port number (0 = use default for type)
            auth_type: Authentication type - password, key, ntlm, kerberos
            key_path: Path to SSH key or certificate
            domain: Windows domain (for SMB/RDP)
            share_path: SMB share path (e.g., 'SharedFolder')
            remote_path: Default remote directory
            local_path: Default local directory for transfers
            use_ssl: Use SSL/TLS (for FTP -> FTPS)
            passive_mode: Use passive mode (for FTP)
            extra_config: Additional type-specific options as JSON
        """
        valid_types = ["ssh", "smb", "ftp", "sftp", "rdp"]
        if profile_type not in valid_types:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Invalid profile_type: {profile_type}. Valid: {valid_types}"
            )
        
        async with self._lock:
            self._counter += 1
            profile_id = f"{profile_type}_{self._counter}_{datetime.now().strftime('%H%M%S')}"
            now = datetime.now().isoformat()
            
            profile = ConnectionProfile(
                id=profile_id,
                profile_type=profile_type,
                name=name,
                host=host,
                port=port,
                username=username,
                auth_type=auth_type,
                key_path=key_path,
                domain=domain,
                share_path=share_path,
                remote_path=remote_path,
                local_path=local_path,
                use_ssl=use_ssl,
                passive_mode=passive_mode,
                extra_config=extra_config or {},
                created_at=now
            )
            
            # Store in database if available
            if self._db_available:
                try:
                    await self._db.insert("connection_profiles", {
                        "profile_id": profile_id,
                        "profile_type": profile_type,
                        "name": name,
                        "host": host,
                        "port": port if port > 0 else None,
                        "username": username,
                        "auth_type": auth_type,
                        "key_path": key_path,
                        "domain": domain,
                        "share_path": share_path,
                        "remote_path": remote_path,
                        "local_path": local_path,
                        "use_ssl": 1 if use_ssl else 0,
                        "passive_mode": 1 if passive_mode else 0,
                        "extra_config": json.dumps(extra_config or {}),
                        "created_at": now
                    })
                except Exception as e:
                    logging.warning(f"Database insert failed for profile: {e}")
            
            # Keep in memory and save JSON backup
            self.profiles[profile_id] = profile
            await self._save_profiles()
            
            port_str = f":{profile.get_default_port()}" if profile.get_default_port() else ""
            user_str = f"{username}@" if username else ""
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"id": profile_id, "type": profile_type},
                message=f"🔐 Added {profile_type.upper()} profile: {name} ({user_str}{host}{port_str})"
            )
    
    async def _list_profiles(self, profile_type: str = None, **kwargs) -> ToolResult:
        """List saved connection profiles
        
        Args:
            profile_type: Filter by type (ssh, smb, ftp, sftp, rdp) or None for all
        """
        async with self._lock:
            profiles = []
            
            # Try database first
            if self._db_available:
                try:
                    where = "profile_type = ?" if profile_type else None
                    params = (profile_type,) if profile_type else ()
                    
                    db_profiles = await self._db.select(
                        "connection_profiles", "*", where, params,
                        order_by="last_used DESC NULLS LAST, created_at DESC"
                    )
                    
                    for row in db_profiles:
                        profiles.append({
                            "id": row["profile_id"],
                            "type": row["profile_type"],
                            "name": row["name"],
                            "host": row["host"],
                            "port": row["port"],
                            "username": row["username"],
                            "auth_type": row["auth_type"],
                            "use_count": row["use_count"] or 0,
                            "last_used": row["last_used"]
                        })
                    
                    type_str = f" {profile_type.upper()}" if profile_type else ""
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data=profiles,
                        message=f"🔐 {len(profiles)}{type_str} profile(s)"
                    )
                except Exception as e:
                    logging.warning(f"Database query failed: {e}")
            
            # Fallback to memory
            for profile in self.profiles.values():
                if profile_type and profile.profile_type != profile_type:
                    continue
                profiles.append({
                    "id": profile.id,
                    "type": profile.profile_type,
                    "name": profile.name,
                    "host": profile.host,
                    "port": profile.get_default_port(),
                    "username": profile.username,
                    "auth_type": profile.auth_type,
                    "use_count": profile.use_count,
                    "last_used": profile.last_used
                })
            
            type_str = f" {profile_type.upper()}" if profile_type else ""
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=profiles,
                message=f"🔐 {len(profiles)}{type_str} profile(s)"
            )
    
    async def _get_profile(self, profile_id: str, **kwargs) -> ToolResult:
        """Get full details of a connection profile"""
        async with self._lock:
            # Try database first
            if self._db_available:
                try:
                    row = await self._db.select_one(
                        "connection_profiles", "*", "profile_id = ?", (profile_id,)
                    )
                    if row:
                        return ToolResult(
                            status=ToolStatus.SUCCESS,
                            data={
                                "id": row["profile_id"],
                                "type": row["profile_type"],
                                "name": row["name"],
                                "host": row["host"],
                                "port": row["port"],
                                "username": row["username"],
                                "auth_type": row["auth_type"],
                                "key_path": row["key_path"],
                                "domain": row["domain"],
                                "share_path": row["share_path"],
                                "remote_path": row["remote_path"],
                                "local_path": row["local_path"],
                                "use_ssl": bool(row["use_ssl"]),
                                "passive_mode": bool(row["passive_mode"]),
                                "extra_config": json.loads(row["extra_config"]) if row["extra_config"] else {},
                                "created_at": row["created_at"],
                                "last_used": row["last_used"],
                                "use_count": row["use_count"] or 0
                            },
                            message=f"🔐 Profile: {row['name']}"
                        )
                except Exception as e:
                    logging.warning(f"Database query failed: {e}")
            
            # Fallback to memory
            if profile_id not in self.profiles:
                return ToolResult(status=ToolStatus.ERROR, error=f"Profile not found: {profile_id}")
            
            profile = self.profiles[profile_id]
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=asdict(profile),
                message=f"🔐 Profile: {profile.name}"
            )
    
    async def _delete_profile(self, profile_id: str, **kwargs) -> ToolResult:
        """Delete a connection profile"""
        async with self._lock:
            name = None
            
            # Get name and remove from memory
            if profile_id in self.profiles:
                name = self.profiles[profile_id].name
                del self.profiles[profile_id]
            
            # Delete from database
            if self._db_available:
                try:
                    if not name:
                        row = await self._db.select_one(
                            "connection_profiles", "name", "profile_id = ?", (profile_id,)
                        )
                        if row:
                            name = row["name"]
                    await self._db.delete("connection_profiles", "profile_id = ?", (profile_id,))
                except Exception as e:
                    logging.warning(f"Database delete failed: {e}")
            
            if not name:
                return ToolResult(status=ToolStatus.ERROR, error=f"Profile not found: {profile_id}")
            
            await self._save_profiles()
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"🗑️ Deleted profile: {name}"
            )
    
    async def _update_profile(self, profile_id: str, **kwargs) -> ToolResult:
        """Update a connection profile"""
        async with self._lock:
            # Build update data from kwargs
            update_fields = ["name", "host", "port", "username", "auth_type", "key_path",
                           "domain", "share_path", "remote_path", "local_path", 
                           "use_ssl", "passive_mode", "extra_config"]
            
            update_data = {}
            for field_name in update_fields:
                if field_name in kwargs and kwargs[field_name] is not None:
                    if field_name == "extra_config":
                        update_data[field_name] = json.dumps(kwargs[field_name])
                    elif field_name in ["use_ssl", "passive_mode"]:
                        update_data[field_name] = 1 if kwargs[field_name] else 0
                    else:
                        update_data[field_name] = kwargs[field_name]
            
            if not update_data:
                return ToolResult(status=ToolStatus.ERROR, error="No fields to update")
            
            # Update in database
            if self._db_available:
                try:
                    await self._db.update(
                        "connection_profiles", update_data, "profile_id = ?", (profile_id,)
                    )
                except Exception as e:
                    logging.warning(f"Database update failed: {e}")
            
            # Update in memory
            if profile_id in self.profiles:
                profile = self.profiles[profile_id]
                for field, value in kwargs.items():
                    if field in update_fields and value is not None:
                        setattr(profile, field, value)
            
            await self._save_profiles()
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"📝 Updated profile: {profile_id}"
            )
    
    async def _mark_profile_used(self, profile_id: str):
        """Mark a profile as used (update last_used and use_count)"""
        now = datetime.now().isoformat()
        
        if self._db_available:
            try:
                await self._db.execute_raw(
                    """UPDATE connection_profiles 
                       SET last_used = ?, use_count = COALESCE(use_count, 0) + 1 
                       WHERE profile_id = ?""",
                    (now, profile_id)
                )
            except Exception as e:
                logging.debug(f"Failed to update profile last_used: {e}")
        
        if profile_id in self.profiles:
            self.profiles[profile_id].last_used = now
            self.profiles[profile_id].use_count += 1
    
    # Legacy SSH profile methods (redirect to unified system)
    async def _ssh_add_profile(self, name: str, host: str, username: str, port: int = 22,
                               auth_type: str = "password", key_path: str = None, 
                               **kwargs) -> ToolResult:
        """Add an SSH connection profile (legacy - redirects to add_profile)"""
        return await self._add_profile(
            profile_type="ssh", name=name, host=host, username=username,
            port=port, auth_type=auth_type, key_path=key_path, **kwargs
        )
    
    async def _ssh_list_profiles(self, **kwargs) -> ToolResult:
        """List saved SSH profiles (legacy - redirects to list_profiles)"""
        return await self._list_profiles(profile_type="ssh", **kwargs)
    
    async def _ssh_delete_profile(self, profile_id: str, **kwargs) -> ToolResult:
        """Delete an SSH profile (legacy - redirects to delete_profile)"""
        return await self._delete_profile(profile_id=profile_id, **kwargs)
    
    # ==================== SSH OPERATIONS ====================
    
    async def _get_profile_details(self, profile_id: str) -> Optional[ConnectionProfile]:
        """Helper to get profile details from DB or memory"""
        if self._db_available:
            try:
                row = await self._db.select_one(
                    "connection_profiles", "*", "profile_id = ?", (profile_id,)
                )
                if row:
                    return ConnectionProfile(
                        id=row["profile_id"],
                        profile_type=row["profile_type"],
                        name=row["name"],
                        host=row["host"],
                        port=row["port"] or 0,
                        username=row["username"] or "",
                        auth_type=row["auth_type"] or "password",
                        key_path=row["key_path"],
                        domain=row["domain"],
                        share_path=row["share_path"],
                        remote_path=row["remote_path"],
                        local_path=row["local_path"],
                        use_ssl=bool(row["use_ssl"]),
                        passive_mode=bool(row["passive_mode"]),
                        extra_config=json.loads(row["extra_config"]) if row["extra_config"] else {},
                        created_at=row["created_at"] or "",
                        last_used=row["last_used"],
                        use_count=row["use_count"] or 0
                    )
            except Exception:
                pass
        
        return self.profiles.get(profile_id)
    
    async def _ssh_connect(self, profile_id: str = "", host: str = "", username: str = "",
                           port: int = 22, use_putty: bool = False, **kwargs) -> ToolResult:
        """Open SSH connection in new terminal window
        
        Args:
            profile_id: Use saved profile
            host: Hostname or IP
            username: SSH username
            port: SSH port (default 22)
            use_putty: Use PuTTY instead of OpenSSH (Windows)
        """
        # Check for SSH tools
        has_ssh = self.available_tools.get("ssh")
        has_putty = self.available_tools.get("putty")
        
        if not has_ssh and not has_putty:
            return ToolResult(status=ToolStatus.ERROR, error="No SSH client installed (ssh or putty)")
        
        try:
            # Get connection details from profile or params
            if profile_id:
                profile = await self._get_profile_details(profile_id)
                if profile:
                    host = profile.host
                    username = profile.username
                    port = profile.get_default_port()
                    await self._mark_profile_used(profile_id)
            
            if not host or not username:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="Provide profile_id or host+username"
                )
            
            # Decide which client to use
            if use_putty and has_putty:
                # Use PuTTY
                cmd = ["putty", "-ssh", f"{username}@{host}", "-P", str(port)]
                await asyncio.to_thread(
                    subprocess.Popen, cmd,
                    creationflags=subprocess.CREATE_NO_WINDOW if self.is_windows else 0
                )
            elif has_ssh:
                # Use OpenSSH
                ssh_cmd = f"ssh {username}@{host}"
                if port != 22:
                    ssh_cmd += f" -p {port}"
                
                if self.is_windows:
                    cmd = f'Start-Process powershell -ArgumentList "-NoExit", "-Command", "{ssh_cmd}"'
                    await asyncio.to_thread(
                        subprocess.run,
                        ["powershell", "-NoProfile", "-Command", cmd],
                        capture_output=True, timeout=10
                    )
                else:
                    await asyncio.to_thread(
                        subprocess.run,
                        ["x-terminal-emulator", "-e", ssh_cmd],
                        capture_output=True, timeout=10
                    )
            elif has_putty:
                # Fallback to PuTTY
                cmd = ["putty", "-ssh", f"{username}@{host}", "-P", str(port)]
                await asyncio.to_thread(subprocess.Popen, cmd)
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"🔐 Opening SSH connection to {username}@{host}:{port}"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _ssh_run_command(self, command: str, profile_id: str = "", host: str = "",
                               username: str = "", port: int = 22, password: str = "",
                               key_path: str = "", timeout: int = 30, 
                               use_plink: bool = False, **kwargs) -> ToolResult:
        """Run a command on remote server via SSH
        
        Args:
            command: Command to execute
            profile_id: Use saved profile
            host: Hostname or IP
            username: SSH username
            port: SSH port
            key_path: Path to SSH private key
            timeout: Command timeout in seconds
            use_plink: Use PuTTY plink instead of OpenSSH
        """
        has_ssh = self.available_tools.get("ssh")
        has_plink = self.available_tools.get("plink")
        
        if not has_ssh and not has_plink:
            return ToolResult(status=ToolStatus.ERROR, error="No SSH client installed (ssh or plink)")
        
        try:
            # Get connection details from profile or params
            if profile_id:
                profile = await self._get_profile_details(profile_id)
                if profile:
                    host = profile.host
                    username = profile.username
                    port = profile.get_default_port()
                    key_path = profile.key_path or key_path
                    await self._mark_profile_used(profile_id)
            
            if not host or not username:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="Provide profile_id or host+username"
                )
            
            # Build command
            if use_plink and has_plink:
                # Use PuTTY plink
                cmd = ["plink", "-ssh", "-batch"]
                if key_path:
                    cmd.extend(["-i", key_path])
                cmd.extend(["-P", str(port), f"{username}@{host}", command])
            else:
                # Use OpenSSH
                cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes"]
                if key_path:
                    cmd.extend(["-i", key_path])
                if port != 22:
                    cmd.extend(["-p", str(port)])
                cmd.append(f"{username}@{host}")
                cmd.append(command)
            
            result = await asyncio.to_thread(
                subprocess.run, cmd,
                capture_output=True, text=True, timeout=timeout
            )
            
            output = result.stdout.strip()
            error = result.stderr.strip()
            
            if result.returncode != 0:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    data={"output": output, "error": error},
                    error=error or f"SSH command failed (code {result.returncode})"
                )
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"output": output, "host": host},
                message=f"🔐 [{host}] {output[:200]}" if output else f"🔐 [{host}] Command executed"
            )
            
        except subprocess.TimeoutExpired:
            return ToolResult(status=ToolStatus.ERROR, error=f"SSH command timed out after {timeout}s")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    # ==================== SMB/NETWORK SHARES ====================
    
    async def _smb_connect(self, profile_id: str = "", host: str = "", share: str = "",
                           username: str = "", password: str = "", domain: str = "",
                           **kwargs) -> ToolResult:
        """Connect to SMB/CIFS network share (opens in Explorer)
        
        Args:
            profile_id: Use saved SMB profile
            host: Server hostname or IP
            share: Share name
            username: Username (optional)
            domain: Windows domain (optional)
        """
        if not self.is_windows:
            return ToolResult(status=ToolStatus.ERROR, error="SMB connect only supported on Windows")
        
        try:
            # Get from profile
            if profile_id:
                profile = await self._get_profile_details(profile_id)
                if profile and profile.profile_type == "smb":
                    host = profile.host
                    share = profile.share_path or share
                    username = profile.username or username
                    domain = profile.domain or domain
                    await self._mark_profile_used(profile_id)
            
            if not host:
                return ToolResult(status=ToolStatus.ERROR, error="Host is required")
            
            # Build UNC path
            unc_path = f"\\\\{host}"
            if share:
                unc_path += f"\\{share}"
            
            # Open in Explorer
            await asyncio.to_thread(
                subprocess.run,
                ["explorer", unc_path],
                capture_output=True, timeout=10
            )
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"📁 Opening {unc_path}"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _smb_map_drive(self, drive_letter: str, host: str, share: str,
                             username: str = "", password: str = "", domain: str = "",
                             persistent: bool = False, profile_id: str = "", **kwargs) -> ToolResult:
        """Map a network drive to SMB share
        
        Args:
            drive_letter: Drive letter (e.g., 'Z')
            host: Server hostname or IP
            share: Share name
            username: Username (optional)
            password: Password (optional, will prompt if needed)
            domain: Windows domain (optional)
            persistent: Reconnect at logon
            profile_id: Use saved SMB profile
        """
        if not self.is_windows:
            return ToolResult(status=ToolStatus.ERROR, error="Drive mapping only supported on Windows")
        
        try:
            # Get from profile
            if profile_id:
                profile = await self._get_profile_details(profile_id)
                if profile and profile.profile_type == "smb":
                    host = profile.host
                    share = profile.share_path or share
                    username = profile.username or username
                    domain = profile.domain or domain
                    await self._mark_profile_used(profile_id)
            
            if not host or not share:
                return ToolResult(status=ToolStatus.ERROR, error="Host and share are required")
            
            # Normalize drive letter
            drive = drive_letter.upper().rstrip(':') + ':'
            unc_path = f"\\\\{host}\\{share}"
            
            # Build net use command
            cmd = ["net", "use", drive, unc_path]
            
            if username:
                user_str = f"{domain}\\{username}" if domain else username
                cmd.extend([f"/user:{user_str}"])
            
            if password:
                cmd.append(password)
            
            if persistent:
                cmd.append("/persistent:yes")
            else:
                cmd.append("/persistent:no")
            
            result = await asyncio.to_thread(
                subprocess.run, cmd,
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode != 0:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=result.stderr.strip() or result.stdout.strip()
                )
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"drive": drive, "path": unc_path},
                message=f"📁 Mapped {drive} to {unc_path}"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _smb_unmap_drive(self, drive_letter: str, force: bool = False, **kwargs) -> ToolResult:
        """Disconnect a mapped network drive
        
        Args:
            drive_letter: Drive letter to disconnect (e.g., 'Z')
            force: Force disconnect even if in use
        """
        if not self.is_windows:
            return ToolResult(status=ToolStatus.ERROR, error="Drive unmapping only supported on Windows")
        
        try:
            drive = drive_letter.upper().rstrip(':') + ':'
            
            cmd = ["net", "use", drive, "/delete"]
            if force:
                cmd.append("/yes")
            
            result = await asyncio.to_thread(
                subprocess.run, cmd,
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode != 0:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=result.stderr.strip() or result.stdout.strip()
                )
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"📁 Disconnected {drive}"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _smb_list_shares(self, host: str, username: str = "", password: str = "",
                               domain: str = "", profile_id: str = "", **kwargs) -> ToolResult:
        """List available shares on a server
        
        Args:
            host: Server hostname or IP
            username: Username (optional)
            domain: Windows domain (optional)
            profile_id: Use saved SMB profile
        """
        if not self.is_windows:
            return ToolResult(status=ToolStatus.ERROR, error="SMB only supported on Windows")
        
        try:
            # Get from profile
            if profile_id:
                profile = await self._get_profile_details(profile_id)
                if profile and profile.profile_type == "smb":
                    host = profile.host
                    username = profile.username or username
                    domain = profile.domain or domain
                    await self._mark_profile_used(profile_id)
            
            if not host:
                return ToolResult(status=ToolStatus.ERROR, error="Host is required")
            
            # Use net view to list shares
            cmd = ["net", "view", f"\\\\{host}"]
            
            result = await asyncio.to_thread(
                subprocess.run, cmd,
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode != 0:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=result.stderr.strip() or "Failed to list shares"
                )
            
            # Parse output
            shares = []
            lines = result.stdout.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('-') and not line.startswith('Share') and not line.startswith('The command'):
                    parts = line.split()
                    if parts:
                        shares.append({"name": parts[0], "type": parts[1] if len(parts) > 1 else "Unknown"})
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=shares,
                message=f"📁 {len(shares)} share(s) on {host}"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    # ==================== FTP/SFTP ====================
    
    async def _ftp_connect(self, profile_id: str = "", host: str = "", username: str = "",
                           port: int = 21, use_sftp: bool = False, **kwargs) -> ToolResult:
        """Open FTP/SFTP connection (opens WinSCP or terminal)
        
        Args:
            profile_id: Use saved FTP/SFTP profile
            host: FTP server hostname
            username: FTP username
            port: FTP port (21 for FTP, 22 for SFTP)
            use_sftp: Use SFTP instead of FTP
        """
        try:
            # Get from profile
            if profile_id:
                profile = await self._get_profile_details(profile_id)
                if profile and profile.profile_type in ["ftp", "sftp"]:
                    host = profile.host
                    username = profile.username or username
                    port = profile.get_default_port()
                    use_sftp = profile.profile_type == "sftp"
                    await self._mark_profile_used(profile_id)
            
            if not host:
                return ToolResult(status=ToolStatus.ERROR, error="Host is required")
            
            # Try WinSCP first
            if self.available_tools.get("winscp"):
                protocol = "sftp" if use_sftp else "ftp"
                user_str = f"{username}@" if username else ""
                url = f"{protocol}://{user_str}{host}:{port}"
                
                await asyncio.to_thread(
                    subprocess.Popen,
                    ["winscp", url],
                    creationflags=subprocess.CREATE_NO_WINDOW if self.is_windows else 0
                )
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    message=f"📂 Opening WinSCP to {protocol}://{host}:{port}"
                )
            
            # Fallback to command line
            if use_sftp and self.available_tools.get("ssh"):
                sftp_cmd = f"sftp {username}@{host}" if username else f"sftp {host}"
                if port != 22:
                    sftp_cmd = f"sftp -P {port} {username}@{host}" if username else f"sftp -P {port} {host}"
                
                if self.is_windows:
                    cmd = f'Start-Process powershell -ArgumentList "-NoExit", "-Command", "{sftp_cmd}"'
                    await asyncio.to_thread(
                        subprocess.run,
                        ["powershell", "-NoProfile", "-Command", cmd],
                        capture_output=True, timeout=10
                    )
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    message=f"📂 Opening SFTP to {host}:{port}"
                )
            
            return ToolResult(
                status=ToolStatus.ERROR,
                error="No FTP client available (install WinSCP or use SSH for SFTP)"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _ftp_list(self, profile_id: str = "", host: str = "", username: str = "",
                        password: str = "", port: int = 22, remote_path: str = "/",
                        use_sftp: bool = True, key_path: str = "", **kwargs) -> ToolResult:
        """List files on SFTP server using paramiko
        
        Args:
            profile_id: Use saved profile
            host: SFTP server hostname
            username: Username
            password: Password (or use key_path)
            port: Port (default 22 for SFTP)
            remote_path: Directory to list (default /)
            key_path: Path to SSH private key
        """
        if not HAS_PARAMIKO:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="paramiko not installed. Install with: pip install paramiko"
            )
        
        try:
            # Get from profile
            if profile_id:
                profile = await self._get_profile_details(profile_id)
                if profile:
                    host = profile.host
                    username = profile.username or username
                    port = profile.get_default_port()
                    key_path = profile.key_path or key_path
                    remote_path = profile.remote_path or remote_path
                    await self._mark_profile_used(profile_id)
            
            if not host or not username:
                return ToolResult(status=ToolStatus.ERROR, error="Host and username required")
            
            # Run SFTP operation in thread to not block
            def sftp_list():
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                try:
                    # Connect with key or password
                    if key_path and Path(key_path).exists():
                        ssh.connect(host, port=port, username=username, key_filename=key_path, timeout=30)
                    elif password:
                        ssh.connect(host, port=port, username=username, password=password, timeout=30)
                    else:
                        # Try without password (agent or default key)
                        ssh.connect(host, port=port, username=username, timeout=30)
                    
                    sftp = ssh.open_sftp()
                    files = []
                    
                    for entry in sftp.listdir_attr(remote_path):
                        file_type = "d" if entry.st_mode and (entry.st_mode & 0o40000) else "f"
                        files.append({
                            "name": entry.filename,
                            "type": file_type,
                            "size": entry.st_size,
                            "modified": datetime.fromtimestamp(entry.st_mtime).isoformat() if entry.st_mtime else None
                        })
                    
                    sftp.close()
                    ssh.close()
                    return files
                except Exception as e:
                    ssh.close()
                    raise e
            
            files = await asyncio.to_thread(sftp_list)
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=files,
                message=f"📂 {len(files)} items in {remote_path} on {host}"
            )
            
        except paramiko.AuthenticationException:
            return ToolResult(status=ToolStatus.ERROR, error="Authentication failed - check username/password/key")
        except paramiko.SSHException as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"SSH error: {e}")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _ftp_upload(self, local_file: str, remote_path: str, profile_id: str = "",
                          host: str = "", username: str = "", password: str = "",
                          port: int = 22, key_path: str = "", use_paramiko: bool = True,
                          **kwargs) -> ToolResult:
        """Upload file via SFTP using paramiko or scp/pscp
        
        Args:
            local_file: Local file path to upload
            remote_path: Remote destination path
            profile_id: Use saved profile
            host: SFTP server hostname
            username: Username
            password: Password (or use key_path)
            port: Port (default 22)
            key_path: Path to SSH private key
            use_paramiko: Use paramiko (True) or fall back to scp/pscp (False)
        """
        try:
            # Get from profile
            if profile_id:
                profile = await self._get_profile_details(profile_id)
                if profile:
                    host = profile.host
                    username = profile.username or username
                    port = profile.get_default_port()
                    key_path = profile.key_path or key_path
                    await self._mark_profile_used(profile_id)
            
            if not host or not username:
                return ToolResult(status=ToolStatus.ERROR, error="Host and username required")
            
            if not Path(local_file).exists():
                return ToolResult(status=ToolStatus.ERROR, error=f"Local file not found: {local_file}")
            
            # Try paramiko first
            if use_paramiko and HAS_PARAMIKO:
                def sftp_upload():
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    
                    try:
                        if key_path and Path(key_path).exists():
                            ssh.connect(host, port=port, username=username, key_filename=key_path, timeout=30)
                        elif password:
                            ssh.connect(host, port=port, username=username, password=password, timeout=30)
                        else:
                            ssh.connect(host, port=port, username=username, timeout=30)
                        
                        sftp = ssh.open_sftp()
                        sftp.put(local_file, remote_path)
                        sftp.close()
                        ssh.close()
                        return True
                    except Exception as e:
                        ssh.close()
                        raise e
                
                await asyncio.to_thread(sftp_upload)
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    message=f"📤 Uploaded {Path(local_file).name} to {host}:{remote_path}"
                )
            
            # Fall back to scp/pscp
            has_pscp = self.available_tools.get("pscp")
            has_ssh = self.available_tools.get("ssh")
            
            if not has_pscp and not has_ssh:
                return ToolResult(status=ToolStatus.ERROR, error="No SCP client available (pscp, scp, or paramiko)")
            
            if has_pscp:
                cmd = ["pscp", "-P", str(port), local_file, f"{username}@{host}:{remote_path}"]
            else:
                cmd = ["scp", "-P", str(port), local_file, f"{username}@{host}:{remote_path}"]
            
            result = await asyncio.to_thread(
                subprocess.run, cmd,
                capture_output=True, text=True, timeout=300
            )
            
            if result.returncode != 0:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=result.stderr.strip() or "Upload failed"
                )
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"📤 Uploaded {Path(local_file).name} to {host}:{remote_path}"
            )
            
        except paramiko.AuthenticationException:
            return ToolResult(status=ToolStatus.ERROR, error="Authentication failed")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _ftp_download(self, remote_file: str, local_path: str, profile_id: str = "",
                            host: str = "", username: str = "", password: str = "",
                            port: int = 22, key_path: str = "", use_paramiko: bool = True,
                            **kwargs) -> ToolResult:
        """Download file via SFTP using paramiko or scp/pscp
        
        Args:
            remote_file: Remote file path to download
            local_path: Local destination path
            profile_id: Use saved profile
            host: SFTP server hostname
            username: Username
            password: Password (or use key_path)
            port: Port (default 22)
            key_path: Path to SSH private key
            use_paramiko: Use paramiko (True) or fall back to scp/pscp (False)
        """
        try:
            # Get from profile
            if profile_id:
                profile = await self._get_profile_details(profile_id)
                if profile:
                    host = profile.host
                    username = profile.username or username
                    port = profile.get_default_port()
                    key_path = profile.key_path or key_path
                    await self._mark_profile_used(profile_id)
            
            if not host or not username:
                return ToolResult(status=ToolStatus.ERROR, error="Host and username required")
            
            # Ensure local directory exists
            local_dir = Path(local_path).parent
            if not local_dir.exists():
                local_dir.mkdir(parents=True, exist_ok=True)
            
            # Try paramiko first
            if use_paramiko and HAS_PARAMIKO:
                def sftp_download():
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    
                    try:
                        if key_path and Path(key_path).exists():
                            ssh.connect(host, port=port, username=username, key_filename=key_path, timeout=30)
                        elif password:
                            ssh.connect(host, port=port, username=username, password=password, timeout=30)
                        else:
                            ssh.connect(host, port=port, username=username, timeout=30)
                        
                        sftp = ssh.open_sftp()
                        sftp.get(remote_file, local_path)
                        sftp.close()
                        ssh.close()
                        return True
                    except Exception as e:
                        ssh.close()
                        raise e
                
                await asyncio.to_thread(sftp_download)
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    message=f"📥 Downloaded {remote_file} to {local_path}"
                )
            
            # Fall back to scp/pscp
            has_pscp = self.available_tools.get("pscp")
            has_ssh = self.available_tools.get("ssh")
            
            if not has_pscp and not has_ssh:
                return ToolResult(status=ToolStatus.ERROR, error="No SCP client available (pscp, scp, or paramiko)")
            
            if has_pscp:
                cmd = ["pscp", "-P", str(port), f"{username}@{host}:{remote_file}", local_path]
            else:
                cmd = ["scp", "-P", str(port), f"{username}@{host}:{remote_file}", local_path]
            
            result = await asyncio.to_thread(
                subprocess.run, cmd,
                capture_output=True, text=True, timeout=300
            )
            
            if result.returncode != 0:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=result.stderr.strip() or "Download failed"
                )
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"📥 Downloaded {remote_file} to {local_path}"
            )
            
        except paramiko.AuthenticationException:
            return ToolResult(status=ToolStatus.ERROR, error="Authentication failed")
        except FileNotFoundError:
            return ToolResult(status=ToolStatus.ERROR, error=f"Remote file not found: {remote_file}")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    # ==================== RDP ====================
    
    async def _rdp_connect(self, profile_id: str = "", host: str = "", username: str = "",
                           domain: str = "", port: int = 3389, fullscreen: bool = True,
                           width: int = 0, height: int = 0, **kwargs) -> ToolResult:
        """Open Remote Desktop connection
        
        Args:
            profile_id: Use saved RDP profile
            host: Remote computer hostname or IP
            username: Username (optional)
            domain: Windows domain (optional)
            port: RDP port (default 3389)
            fullscreen: Open in fullscreen mode
            width: Window width (if not fullscreen)
            height: Window height (if not fullscreen)
        """
        if not self.is_windows:
            return ToolResult(status=ToolStatus.ERROR, error="RDP only supported on Windows")
        
        if not self.available_tools.get("mstsc"):
            return ToolResult(status=ToolStatus.ERROR, error="mstsc (Remote Desktop) not available")
        
        try:
            # Get from profile
            if profile_id:
                profile = await self._get_profile_details(profile_id)
                if profile and profile.profile_type == "rdp":
                    host = profile.host
                    username = profile.username or username
                    domain = profile.domain or domain
                    port = profile.get_default_port()
                    await self._mark_profile_used(profile_id)
            
            if not host:
                return ToolResult(status=ToolStatus.ERROR, error="Host is required")
            
            # Build mstsc command
            cmd = ["mstsc"]
            
            # Add host (with port if non-standard)
            if port != 3389:
                cmd.append(f"/v:{host}:{port}")
            else:
                cmd.append(f"/v:{host}")
            
            if fullscreen:
                cmd.append("/f")
            elif width and height:
                cmd.append(f"/w:{width}")
                cmd.append(f"/h:{height}")
            
            # Launch RDP
            await asyncio.to_thread(
                subprocess.Popen, cmd,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"🖥️ Opening Remote Desktop to {host}:{port}"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    # ==================== UTILITY ====================
    
    async def _check_tools(self, **kwargs) -> ToolResult:
        """Check which developer tools are available"""
        await self._detect_tools()
        
        available = {k: v for k, v in self.available_tools.items() if v}
        unavailable = {k: v for k, v in self.available_tools.items() if not v}
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "available": list(available.keys()),
                "unavailable": list(unavailable.keys())
            },
            message=f"✅ Available: {', '.join(available.keys())} | ❌ Missing: {', '.join(unavailable.keys())}"
        )
    
    async def _find_tool_path(self, tool: str, **kwargs) -> ToolResult:
        """Find the full path of a tool/executable using shutil.which"""
        try:
            path = shutil.which(tool)
            
            if path:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"tool": tool, "path": path},
                    message=f"🔍 {tool}: {path}"
                )
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Tool not found: {tool}"
                )
                
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _run_multiple_commands(self, commands: List[str], stop_on_error: bool = True,
                                      path: str = ".", **kwargs) -> ToolResult:
        """Run multiple shell commands in sequence
        
        Args:
            commands: List of commands to run
            stop_on_error: Stop execution if a command fails
            path: Working directory
        """
        try:
            results: List[Dict[str, Any]] = []
            
            for i, cmd in enumerate(commands):
                # Convert string commands to list format for security
                if isinstance(cmd, str):
                    if self.is_windows:
                        cmd_list = ["cmd", "/c", cmd]
                    else:
                        cmd_list = ["/bin/sh", "-c", cmd]
                else:
                    cmd_list = cmd
                
                result = await asyncio.to_thread(
                    subprocess.run,
                    cmd_list,
                    capture_output=True, text=True, timeout=60, cwd=path,
                    shell=False
                )
                
                cmd_result = {
                    "command": cmd,
                    "output": result.stdout.strip(),
                    "error": result.stderr.strip(),
                    "return_code": result.returncode,
                    "success": result.returncode == 0
                }
                results.append(cmd_result)
                
                if result.returncode != 0 and stop_on_error:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        data={"results": results, "failed_at": i},
                        error=f"Command {i+1} failed: {cmd}"
                    )
            
            successful = sum(1 for r in results if r["success"])
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"results": results},
                message=f"✅ Ran {len(commands)} commands ({successful} successful)"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    # ==================== DATA PERSISTENCE ====================
    
    async def _migrate_ssh_profiles_to_db(self):
        """Migrate legacy SSH profiles from JSON to database"""
        if not self._db_available:
            return
        
        try:
            # Check if database already has profiles
            count = await self._db.count("connection_profiles")
            if count > 0:
                logging.info(f"Database already has {count} profiles, skipping migration")
                return
            
            # Load legacy SSH profiles
            if not self.ssh_profiles_file.exists():
                return
            
            async with aiofiles.open(self.ssh_profiles_file, 'r') as f:
                data = json.loads(await f.read())
            
            if not data:
                return
            
            migrated = 0
            for item in data:
                try:
                    await self._db.insert("connection_profiles", {
                        "profile_id": item["id"],
                        "profile_type": "ssh",
                        "name": item["name"],
                        "host": item["host"],
                        "port": item.get("port", 22),
                        "username": item.get("username", ""),
                        "auth_type": item.get("auth_type", "password"),
                        "key_path": item.get("key_path"),
                        "created_at": item.get("created_at", datetime.now().isoformat())
                    })
                    migrated += 1
                except Exception as e:
                    logging.warning(f"Failed to migrate SSH profile {item.get('id')}: {e}")
            
            logging.info(f"Migrated {migrated} SSH profiles from JSON to database")
            
        except Exception as e:
            logging.warning(f"SSH profile migration failed: {e}")
    
    async def _load_profiles(self):
        """Load connection profiles from database or JSON"""
        try:
            # Try loading from database first
            if self._db_available:
                try:
                    db_profiles = await self._db.select(
                        "connection_profiles", "*",
                        order_by="last_used DESC NULLS LAST"
                    )
                    for row in db_profiles:
                        profile = ConnectionProfile(
                            id=row["profile_id"],
                            profile_type=row["profile_type"],
                            name=row["name"],
                            host=row["host"],
                            port=row["port"] or 0,
                            username=row["username"] or "",
                            auth_type=row["auth_type"] or "password",
                            key_path=row["key_path"],
                            domain=row["domain"],
                            share_path=row["share_path"],
                            remote_path=row["remote_path"],
                            local_path=row["local_path"],
                            use_ssl=bool(row["use_ssl"]),
                            passive_mode=bool(row["passive_mode"]),
                            extra_config=json.loads(row["extra_config"]) if row["extra_config"] else {},
                            created_at=row["created_at"] or "",
                            last_used=row["last_used"],
                            use_count=row["use_count"] or 0
                        )
                        self.profiles[profile.id] = profile
                    
                    if db_profiles:
                        logging.info(f"Loaded {len(db_profiles)} connection profiles from database")
                        return
                except Exception as e:
                    logging.warning(f"Database load failed, trying JSON: {e}")
            
            # Fallback to JSON file
            if self.profiles_file.exists():
                async with aiofiles.open(self.profiles_file, 'r') as f:
                    data = json.loads(await f.read())
                    for item in data:
                        # Handle extra_config which might be a dict already
                        if isinstance(item.get('extra_config'), str):
                            item['extra_config'] = json.loads(item['extra_config'])
                        self.profiles[item['id']] = ConnectionProfile(**item)
            
            # Also load legacy SSH profiles for backward compatibility
            await self._load_ssh_profiles()
            
        except Exception as e:
            logging.warning(f"Could not load profiles: {e}")
    
    async def _load_ssh_profiles(self):
        """Load legacy SSH profiles from file (for backward compatibility)"""
        try:
            if self.ssh_profiles_file.exists():
                async with aiofiles.open(self.ssh_profiles_file, 'r') as f:
                    data = json.loads(await f.read())
                    for item in data:
                        # Convert to new format if not already in profiles
                        if item['id'] not in self.profiles:
                            self.profiles[item['id']] = ConnectionProfile(
                                id=item['id'],
                                profile_type="ssh",
                                name=item['name'],
                                host=item['host'],
                                port=item.get('port', 22),
                                username=item.get('username', ''),
                                auth_type=item.get('auth_type', 'password'),
                                key_path=item.get('key_path'),
                                created_at=item.get('created_at', '')
                            )
        except Exception as e:
            logging.warning(f"Could not load legacy SSH profiles: {e}")
    
    async def _save_profiles(self):
        """Save connection profiles to JSON backup"""
        try:
            data = []
            for p in self.profiles.values():
                item = asdict(p)
                # Ensure extra_config is serializable
                if isinstance(item.get('extra_config'), dict):
                    item['extra_config'] = item['extra_config']
                data.append(item)
            
            async with aiofiles.open(self.profiles_file, 'w') as f:
                await f.write(json.dumps(data, indent=2))
        except Exception as e:
            logging.error(f"Could not save profiles: {e}")
    
    async def _save_ssh_profiles(self):
        """Save SSH profiles to legacy file (for backward compatibility)"""
        # Just redirect to save_profiles now
        await self._save_profiles()

    
    def get_schema(self) -> Dict[str, Any]:
        """Return schema for developer tools"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            # Git
                            "git_status", "git_add", "git_commit", "git_push", "git_pull",
                            "git_branch", "git_checkout", "git_log", "git_diff", "git_clone", "git_init",
                            # Code execution
                            "run_python", "run_javascript", "run_powershell", "run_batch",
                            # Package management
                            "pip_install", "pip_uninstall", "pip_list",
                            "npm_install", "npm_uninstall", "npm_list",
                            "winget_search", "winget_install", "winget_uninstall", "winget_list",
                            # Connection Profiles
                            "add_profile", "list_profiles", "get_profile", "delete_profile", "update_profile",
                            # SSH (legacy + new)
                            "ssh_connect", "ssh_run_command", "ssh_add_profile", 
                            "ssh_list_profiles", "ssh_delete_profile",
                            # SMB/Network
                            "smb_connect", "smb_map_drive", "smb_unmap_drive", "smb_list_shares",
                            # FTP/SFTP
                            "ftp_connect", "ftp_list", "ftp_upload", "ftp_download",
                            # RDP
                            "rdp_connect",
                            # Utility
                            "check_tools", "find_tool_path", "run_multiple_commands"
                        ],
                        "description": "Developer action to perform"
                    },
                    # Git params
                    "path": {"type": "string", "description": "Repository path (default: current directory)"},
                    "files": {"type": "string", "description": "Files to stage (space-separated, or '.' for all)"},
                    "message": {"type": "string", "description": "Commit message"},
                    "remote": {"type": "string", "description": "Git remote name", "default": "origin"},
                    "branch": {"type": "string", "description": "Branch name"},
                    "create": {"type": "boolean", "description": "Create new branch when checking out"},
                    "delete": {"type": "boolean", "description": "Delete branch"},
                    "count": {"type": "integer", "description": "Number of commits to show in log", "default": 10},
                    "oneline": {"type": "boolean", "description": "Show log in oneline format", "default": True},
                    "file": {"type": "string", "description": "File to diff"},
                    "staged": {"type": "boolean", "description": "Show staged changes in diff"},
                    "url": {"type": "string", "description": "Repository URL to clone"},
                    "directory": {"type": "string", "description": "Directory name for clone"},
                    # Code execution params
                    "code": {"type": "string", "description": "Code snippet to execute"},
                    "timeout": {"type": "integer", "description": "Execution timeout in seconds", "default": 30},
                    # Package management params
                    "package": {"type": "string", "description": "Package name to install/uninstall"},
                    "upgrade": {"type": "boolean", "description": "Upgrade package (pip)"},
                    "use_venv": {"type": "boolean", "description": "For pip: install to project venv (default True). Set False for user/system install.", "default": True},
                    "global_install": {"type": "boolean", "description": "Install globally (npm)"},
                    "dev": {"type": "boolean", "description": "Install as dev dependency (npm)"},
                    "outdated": {"type": "boolean", "description": "Show only outdated packages (pip)"},
                    "depth": {"type": "integer", "description": "Dependency tree depth (npm)", "default": 0},
                    "query": {"type": "string", "description": "Search query (winget)"},
                    # Connection Profile params
                    "profile_id": {"type": "string", "description": "Connection profile ID"},
                    "profile_type": {
                        "type": "string",
                        "enum": ["ssh", "smb", "ftp", "sftp", "rdp"],
                        "description": "Type of connection profile"
                    },
                    "name": {"type": "string", "description": "Profile name"},
                    "host": {"type": "string", "description": "Host/IP address"},
                    "username": {"type": "string", "description": "Username"},
                    "port": {"type": "integer", "description": "Port number (0 = default for type)"},
                    "auth_type": {
                        "type": "string",
                        "enum": ["password", "key", "ntlm", "kerberos"],
                        "description": "Authentication type"
                    },
                    "key_path": {"type": "string", "description": "Path to SSH key or certificate"},
                    "domain": {"type": "string", "description": "Windows domain (SMB/RDP)"},
                    "share": {"type": "string", "description": "SMB share name"},
                    "share_path": {"type": "string", "description": "SMB share path"},
                    "remote_path": {"type": "string", "description": "Remote directory path"},
                    "local_path": {"type": "string", "description": "Local directory path"},
                    "use_ssl": {"type": "boolean", "description": "Use SSL/TLS (FTP)"},
                    "passive_mode": {"type": "boolean", "description": "Use passive mode (FTP)", "default": True},
                    "use_sftp": {"type": "boolean", "description": "Use SFTP instead of FTP"},
                    "use_putty": {"type": "boolean", "description": "Use PuTTY instead of OpenSSH"},
                    "use_plink": {"type": "boolean", "description": "Use plink instead of ssh"},
                    # SSH/Remote params
                    "password": {"type": "string", "description": "Password (not stored in profiles)"},
                    "command": {"type": "string", "description": "Command to run on remote server"},
                    # SMB params
                    "drive_letter": {"type": "string", "description": "Drive letter for mapping (e.g., 'Z')"},
                    "persistent": {"type": "boolean", "description": "Reconnect at logon"},
                    "force": {"type": "boolean", "description": "Force operation"},
                    # FTP params
                    "local_file": {"type": "string", "description": "Local file path for upload"},
                    "remote_file": {"type": "string", "description": "Remote file path for download"},
                    # RDP params
                    "fullscreen": {"type": "boolean", "description": "Open RDP in fullscreen", "default": True},
                    "width": {"type": "integer", "description": "RDP window width"},
                    "height": {"type": "integer", "description": "RDP window height"},
                    # Utility params
                    "tool": {"type": "string", "description": "Tool name to find path for"},
                    "commands": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of commands to run in sequence"
                    },
                    "stop_on_error": {"type": "boolean", "description": "Stop if a command fails", "default": True}
                },
                "required": ["action"]
            }
        }
    
    async def cleanup(self):
        """Cleanup developer tools"""
        await self._save_profiles()
        
        # Close database connection
        if self._db_available and self._db:
            try:
                await self._db.cleanup()
            except Exception as e:
                logging.warning(f"Database cleanup error: {e}")
        
        logging.info("Developer tools cleanup completed")
