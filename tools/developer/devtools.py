"""
Developer Tools for Sakura
Git operations, code execution, package management, SSH connections

Rules followed:
- All imports MUST be used
- Async with asyncio.Lock() for thread safety
- aiofiles for file I/O
"""
import asyncio
import logging
import os
import subprocess
import shutil
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import json
import aiofiles
from ..base import BaseTool, ToolResult, ToolStatus


# Get assistant name for data folder
ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "Sakura")


@dataclass
class SSHConnection:
    """SSH connection profile"""
    id: str
    name: str
    host: str
    port: int = 22
    username: str = ""
    auth_type: str = "password"  # password, key
    key_path: Optional[str] = None
    created_at: str = ""


class DeveloperTools(BaseTool):
    """Developer tools - Git, code execution, package management, SSH"""
    
    name = "developer"
    description = "Developer tools: Git operations (status, add, commit, push, pull, branch, log, diff), run code snippets (Python, JS, PowerShell, Batch), package management (pip, npm, winget), SSH connections."
    
    def __init__(self):
        self._lock = asyncio.Lock()
        self.is_windows = os.name == 'nt'
        self.data_dir: Path = Path.home() / "Documents" / ASSISTANT_NAME / "developer"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # SSH profiles file
        self.ssh_profiles_file = self.data_dir / "ssh_profiles.json"
        self.ssh_profiles: Dict[str, SSHConnection] = {}
        
        # Detect available tools
        self.available_tools: Dict[str, bool] = {}
        self._counter = 0
    
    async def initialize(self) -> bool:
        """Initialize developer tools"""
        try:
            # Detect available tools
            await self._detect_tools()
            
            # Load SSH profiles
            await self._load_ssh_profiles()
            
            available = [k for k, v in self.available_tools.items() if v]
            logging.info(f"Developer tools initialized. Available: {available}")
            return True
        except Exception as e:
            logging.error(f"Failed to initialize developer tools: {e}")
            return False
    
    async def _detect_tools(self):
        """Detect which developer tools are available on the system"""
        tools_to_check = {
            "git": ["git", "--version"],
            "python": ["python", "--version"],
            "node": ["node", "--version"],
            "npm": ["npm", "--version"],
            "pip": ["pip", "--version"],
            "winget": ["winget", "--version"],
            "ssh": ["ssh", "-V"],
        }
        
        for tool, cmd in tools_to_check.items():
            try:
                result = await asyncio.to_thread(
                    subprocess.run, cmd,
                    capture_output=True, text=True, timeout=5
                )
                self.available_tools[tool] = result.returncode == 0
            except Exception:
                self.available_tools[tool] = False
    
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
            # SSH
            "ssh_connect": self._ssh_connect,
            "ssh_run_command": self._ssh_run_command,
            "ssh_add_profile": self._ssh_add_profile,
            "ssh_list_profiles": self._ssh_list_profiles,
            "ssh_delete_profile": self._ssh_delete_profile,
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
    
    async def _pip_install(self, package: str, upgrade: bool = False, **kwargs) -> ToolResult:
        """Install Python package with pip"""
        if not self.available_tools.get("pip"):
            return ToolResult(status=ToolStatus.ERROR, error="pip is not installed")
        
        try:
            cmd = ["pip", "install"]
            if upgrade:
                cmd.append("--upgrade")
            cmd.append(package)
            
            result = await asyncio.to_thread(
                subprocess.run, cmd,
                capture_output=True, text=True, timeout=120
            )
            
            if result.returncode != 0:
                return ToolResult(status=ToolStatus.ERROR, error=result.stderr.strip())
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"output": result.stdout.strip()},
                message=f"📦 Installed: {package}"
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

    
    # ==================== SSH ====================
    
    async def _ssh_add_profile(self, name: str, host: str, username: str, port: int = 22,
                               auth_type: str = "password", key_path: str = None, 
                               **kwargs) -> ToolResult:
        """Add an SSH connection profile"""
        async with self._lock:
            self._counter += 1
            profile_id = f"ssh_{self._counter}_{datetime.now().strftime('%H%M%S')}"
            
            profile = SSHConnection(
                id=profile_id,
                name=name,
                host=host,
                port=port,
                username=username,
                auth_type=auth_type,
                key_path=key_path,
                created_at=datetime.now().isoformat()
            )
            
            self.ssh_profiles[profile_id] = profile
            await self._save_ssh_profiles()
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"id": profile_id},
                message=f"🔐 Added SSH profile: {name} ({username}@{host}:{port})"
            )
    
    async def _ssh_list_profiles(self, **kwargs) -> ToolResult:
        """List saved SSH profiles"""
        async with self._lock:
            profiles = []
            for profile in self.ssh_profiles.values():
                profiles.append({
                    "id": profile.id,
                    "name": profile.name,
                    "host": profile.host,
                    "port": profile.port,
                    "username": profile.username,
                    "auth_type": profile.auth_type
                })
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=profiles,
                message=f"🔐 {len(profiles)} SSH profile(s)"
            )
    
    async def _ssh_delete_profile(self, profile_id: str, **kwargs) -> ToolResult:
        """Delete an SSH profile"""
        async with self._lock:
            if profile_id not in self.ssh_profiles:
                return ToolResult(status=ToolStatus.ERROR, error=f"Profile not found: {profile_id}")
            
            name = self.ssh_profiles[profile_id].name
            del self.ssh_profiles[profile_id]
            await self._save_ssh_profiles()
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"🗑️ Deleted SSH profile: {name}"
            )
    
    async def _ssh_connect(self, profile_id: str = "", host: str = "", username: str = "",
                           port: int = 22, **kwargs) -> ToolResult:
        """Open SSH connection in new terminal window"""
        if not self.available_tools.get("ssh"):
            return ToolResult(status=ToolStatus.ERROR, error="SSH is not installed")
        
        try:
            # Get connection details from profile or params
            if profile_id and profile_id in self.ssh_profiles:
                profile = self.ssh_profiles[profile_id]
                host = profile.host
                username = profile.username
                port = profile.port
            elif not host or not username:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="Provide profile_id or host+username"
                )
            
            # Build SSH command
            ssh_cmd = f"ssh {username}@{host}"
            if port != 22:
                ssh_cmd += f" -p {port}"
            
            # Open in new terminal window
            if self.is_windows:
                cmd = f'Start-Process powershell -ArgumentList "-NoExit", "-Command", "{ssh_cmd}"'
                await asyncio.to_thread(
                    subprocess.run,
                    ["powershell", "-NoProfile", "-Command", cmd],
                    capture_output=True, timeout=10
                )
            else:
                # Linux/Mac - try common terminals
                await asyncio.to_thread(
                    subprocess.run,
                    ["x-terminal-emulator", "-e", ssh_cmd],
                    capture_output=True, timeout=10
                )
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"🔐 Opening SSH connection to {username}@{host}:{port}"
            )
            
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _ssh_run_command(self, command: str, profile_id: str = "", host: str = "",
                               username: str = "", port: int = 22, password: str = "",
                               key_path: str = "", timeout: int = 30, **kwargs) -> ToolResult:
        """Run a command on remote server via SSH"""
        if not self.available_tools.get("ssh"):
            return ToolResult(status=ToolStatus.ERROR, error="SSH is not installed")
        
        try:
            # Get connection details from profile or params
            if profile_id and profile_id in self.ssh_profiles:
                profile = self.ssh_profiles[profile_id]
                host = profile.host
                username = profile.username
                port = profile.port
                key_path = profile.key_path or key_path
            elif not host or not username:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="Provide profile_id or host+username"
                )
            
            # Build SSH command
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
                result = await asyncio.to_thread(
                    subprocess.run,
                    cmd if isinstance(cmd, list) else ["cmd", "/c", cmd] if self.is_windows else ["sh", "-c", cmd],
                    capture_output=True, text=True, timeout=60, cwd=path,
                    shell=isinstance(cmd, str)
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
    
    async def _load_ssh_profiles(self):
        """Load SSH profiles from file"""
        try:
            if self.ssh_profiles_file.exists():
                async with aiofiles.open(self.ssh_profiles_file, 'r') as f:
                    data = json.loads(await f.read())
                    for item in data:
                        self.ssh_profiles[item['id']] = SSHConnection(**item)
        except Exception as e:
            logging.warning(f"Could not load SSH profiles: {e}")
    
    async def _save_ssh_profiles(self):
        """Save SSH profiles to file"""
        try:
            data = [asdict(p) for p in self.ssh_profiles.values()]
            async with aiofiles.open(self.ssh_profiles_file, 'w') as f:
                await f.write(json.dumps(data, indent=2))
        except Exception as e:
            logging.error(f"Could not save SSH profiles: {e}")

    
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
                            # SSH
                            "ssh_connect", "ssh_run_command", "ssh_add_profile", 
                            "ssh_list_profiles", "ssh_delete_profile",
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
                    "global_install": {"type": "boolean", "description": "Install globally (npm)"},
                    "dev": {"type": "boolean", "description": "Install as dev dependency (npm)"},
                    "outdated": {"type": "boolean", "description": "Show only outdated packages (pip)"},
                    "depth": {"type": "integer", "description": "Dependency tree depth (npm)", "default": 0},
                    "query": {"type": "string", "description": "Search query (winget)"},
                    # SSH params
                    "profile_id": {"type": "string", "description": "SSH profile ID"},
                    "name": {"type": "string", "description": "Profile name"},
                    "host": {"type": "string", "description": "SSH host/IP address"},
                    "username": {"type": "string", "description": "SSH username"},
                    "port": {"type": "integer", "description": "SSH port", "default": 22},
                    "auth_type": {"type": "string", "enum": ["password", "key"], "description": "Authentication type"},
                    "key_path": {"type": "string", "description": "Path to SSH private key"},
                    "password": {"type": "string", "description": "SSH password (not stored)"},
                    "command": {"type": "string", "description": "Command to run on remote server"},
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
        await self._save_ssh_profiles()
        logging.info("Developer tools cleanup completed")
