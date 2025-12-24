# Developer Tools

**File:** `tools/developer/devtools.py`  
**Actions:** 33

Git operations, code execution, package management, and SSH connections.

## Actions

### Git Operations (11)
| Action | Description |
|--------|-------------|
| `git_status` | Show working tree status |
| `git_add` | Stage files for commit |
| `git_commit` | Commit staged changes |
| `git_push` | Push to remote |
| `git_pull` | Pull from remote |
| `git_branch` | List/create branches |
| `git_checkout` | Switch branches |
| `git_log` | Show commit history |
| `git_diff` | Show changes |
| `git_clone` | Clone repository |
| `git_init` | Initialize new repo |

### Code Execution (4)
| Action | Description |
|--------|-------------|
| `run_python` | Execute Python code |
| `run_javascript` | Execute JavaScript (Node.js) |
| `run_powershell` | Execute PowerShell script |
| `run_batch` | Execute batch/CMD script |

### Package Management (11)
| Action | Description |
|--------|-------------|
| `pip_install` | Install Python package |
| `pip_uninstall` | Uninstall Python package |
| `pip_list` | List installed packages |
| `npm_install` | Install npm package |
| `npm_uninstall` | Uninstall npm package |
| `npm_list` | List npm packages |
| `winget_search` | Search Windows packages |
| `winget_install` | Install Windows package |
| `winget_uninstall` | Uninstall Windows package |
| `winget_list` | List installed packages |

### SSH (5)
| Action | Description |
|--------|-------------|
| `ssh_connect` | Open SSH connection in terminal |
| `ssh_run_command` | Execute command on remote host |
| `ssh_add_profile` | Save SSH connection profile |
| `ssh_list_profiles` | List saved profiles |
| `ssh_delete_profile` | Delete saved profile |

### Utility (3)
| Action | Description |
|--------|-------------|
| `check_tools` | Detect available dev tools |
| `find_tool_path` | Find executable path |
| `run_multiple_commands` | Run command sequence |

## Data Storage

SSH profiles stored in: `~/Documents/{ASSISTANT_NAME}/developer/ssh_profiles.json`

## Example Usage

```python
# Git commit
await tool.execute("git_add", files=["."])
await tool.execute("git_commit", message="feat: add new feature")
await tool.execute("git_push")

# Run Python code
await tool.execute("run_python", code="print('Hello!')")

# Install package
await tool.execute("pip_install", package="requests")

# SSH to server
await tool.execute("ssh_connect", host="192.168.1.100", username="admin")
```

## Tool Detection

On initialization, the tool detects which dev tools are available:
- git, python, node, npm, pip, winget, ssh

Use `check_tools` action to see what's available on the system.
