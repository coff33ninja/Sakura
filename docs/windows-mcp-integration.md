# Windows MCP Integration for Sakura

This document outlines the Windows-specific MCP servers to integrate with Sakura, enabling her to control your PC, run commands, search files, and more.

## MCP Servers to Implement

### 1. Smooth Operator
**Purpose:** Windows automation via AI Vision, Mouse, Keyboard, Automation Trees, Webbrowser
**Use Case:** Let Sakura control Windows apps - open programs, click buttons, type text, navigate UIs

**Installation:**
```bash
npx -y @anthropic/smooth-operator
```

**Config:**
```json
{
  "smooth_operator": {
    "type": "stdio",
    "command": ["npx", "-y", "@anthropic/smooth-operator"]
  }
}
```

---

### 2. Windows CLI
**Purpose:** Secure command-line interactions on Windows (PowerShell, CMD, Git Bash)
**Use Case:** Run system commands safely - check system info, manage processes, run scripts

**Installation:**
```bash
npx -y @anthropic/windows-cli
```

**Config:**
```json
{
  "windows_cli": {
    "type": "stdio",
    "command": ["npx", "-y", "@anthropic/windows-cli"]
  }
}
```

---

### 3. Everything Search
**Purpose:** Fast file searching using Everything SDK on Windows
**Use Case:** Find files instantly across all drives

**Requirements:** 
- Everything search tool installed: https://www.voidtools.com/
- Everything SDK enabled

**Installation:**
```bash
npx -y mcp-server-everything
```

**Config:**
```json
{
  "everything_search": {
    "type": "stdio",
    "command": ["npx", "-y", "mcp-server-everything"]
  }
}
```

---

### 4. Desktop Commander
**Purpose:** Edit files, run terminal commands, SSH connections
**Use Case:** General purpose automation - file editing, command execution, remote server access

**Installation:**
```bash
npx -y @anthropic/desktop-commander
```

**Config:**
```json
{
  "desktop_commander": {
    "type": "stdio",
    "command": ["npx", "-y", "@anthropic/desktop-commander"]
  }
}
```

---

### 5. Filesystem (Official)
**Purpose:** File operations with configurable access
**Use Case:** Basic file management - read, write, list, search files in allowed directories

**Installation:**
```bash
npx -y @modelcontextprotocol/server-filesystem
```

**Config:**
```json
{
  "filesystem": {
    "type": "stdio",
    "command": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "C:/Users/YourName/Documents"]
  }
}
```

---

## Implementation Status

| Server | Status | Priority |
|--------|--------|----------|
| Windows Automation (Native) | ✅ Implemented | High |
| Smooth Operator | 🟡 Via MCP | Medium |
| Windows CLI | ✅ Implemented (native) | High |
| Everything Search | ✅ Implemented (fallback) | Medium |
| Desktop Commander | 🟡 Via MCP | Medium |
| Filesystem | 🟡 Via MCP | Low |

## Native Windows Tool

The `WindowsAutomation` tool (`tools/windows/automation.py`) provides native Windows control without external MCP servers:

### Available Actions:
- `run_command` - Execute PowerShell or CMD commands
- `open_app` - Open applications (chrome, notepad, vscode, etc.)
- `open_url` - Open URLs in default browser
- `search_files` - Search files (uses Everything if available, fallback to PowerShell)
- `list_processes` - List running processes
- `kill_process` - Kill process by name or PID
- `get_system_info` - Get system information
- `type_text` - Type text using SendKeys
- `press_key` - Press special keys (Enter, Tab, F1-F12, etc.)
- `screenshot` - Take a screenshot
- `list_windows` - List open windows

## Integration Approach

These MCP servers will be connected through Sakura's existing MCP client (`tools/mcp/client.py`). The servers run as external processes and communicate via stdio.

### Example Usage with Sakura:
- "Sakura, open Chrome and go to YouTube" → `open_app` + `open_url`
- "Sakura, find all my PDF files" → `search_files`
- "Sakura, run the backup script" → `run_command`
- "Sakura, what's in my Downloads folder?" → `run_command` with `dir`
- "Sakura, what apps are running?" → `list_processes`
- "Sakura, close Notepad" → `kill_process`
- "Sakura, take a screenshot" → `screenshot`
- "Sakura, what's my system info?" → `get_system_info`
