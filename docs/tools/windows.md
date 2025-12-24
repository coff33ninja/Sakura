# Windows Automation Tool

**File:** `tools/windows/automation.py`  
**Actions:** 46

Complete Windows control through native APIs and PowerShell.

## Actions

### App & Window Control
| Action | Description |
|--------|-------------|
| `run_command` | Execute PowerShell/CMD commands |
| `open_app` | Launch applications |
| `close_app` | Close applications |
| `focus_window` | Bring window to front |
| `minimize_window` | Minimize window |
| `maximize_window` | Maximize window |
| `list_windows` | List all open windows |
| `snap_window` | Snap to left/right/corners (Win+Arrow) |

### Mouse Control
| Action | Description |
|--------|-------------|
| `move_mouse` | Move cursor to position |
| `click_mouse` | Left click at position |
| `double_click` | Double click |
| `right_click_menu` | Open context menu |
| `scroll_mouse` | Scroll up/down/left/right |
| `drag_mouse` | Drag from start to end position |
| `get_mouse_position` | Get current cursor position |

### Keyboard
| Action | Description |
|--------|-------------|
| `send_hotkey` | Send keyboard shortcuts (Ctrl+C, Alt+Tab, Win+D, etc.) |
| `type_text` | Type text string |

### Media & Volume
| Action | Description |
|--------|-------------|
| `volume_up` | Increase volume |
| `volume_down` | Decrease volume |
| `volume_mute` | Toggle mute |
| `media_play_pause` | Play/pause media |
| `media_next` | Next track |
| `media_prev` | Previous track |

### Files & Clipboard
| Action | Description |
|--------|-------------|
| `read_file` | Read file contents |
| `write_file` | Write to file |
| `delete_file` | Delete file |
| `search_files` | Search files across drives |
| `get_clipboard` | Get clipboard content |
| `set_clipboard` | Set clipboard content |

### Screen & UI
| Action | Description |
|--------|-------------|
| `screenshot` | Capture screen |
| `read_screen` | OCR screen content |
| `get_ui_element` | Get UI element info |
| `smart_click` | Click button by name |
| `get_context_at_cursor` | Get info under cursor |

### System
| Action | Description |
|--------|-------------|
| `list_processes` | List running processes |
| `kill_process` | Terminate process |
| `virtual_desktop` | Create/switch/close virtual desktops |
| `lock_screen` | Lock workstation (Win+L) |
| `power_action` | Sleep, hibernate, shutdown, restart, logoff |

### Scripts
| Action | Description |
|--------|-------------|
| `execute_script` | Run script from sandbox |
| `create_script` | Create script in sandbox folder |

## Script Sandbox

All scripts are saved to: `~/Documents/{ASSISTANT_NAME}/scripts/`

Organized by type:
- `/powershell/` - .ps1 files
- `/python/` - .py files
- `/batch/` - .bat files
- `/javascript/` - .js files

## Example Usage

```python
# Send Ctrl+C
await tool.execute("send_hotkey", keys=["ctrl", "c"])

# Snap window to left half
await tool.execute("snap_window", direction="left")

# Scroll down 3 clicks
await tool.execute("scroll_mouse", direction="down", amount=3)

# Shutdown computer
await tool.execute("power_action", action="shutdown")
```
