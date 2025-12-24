# System Discovery Tool

**File:** `tools/system_info/discovery.py`  
**Actions:** 15

Discover system information, hardware specs, installed apps, and network details.

## Actions

| Action | Description |
|--------|-------------|
| `get_pc_info` | Computer name, username, OS, processor |
| `get_user_folders` | User folder paths (Documents, Downloads, etc.) |
| `list_installed_apps` | List all installed applications |
| `search_apps` | Search apps by category (browsers, dev, media, games) |
| `get_running_apps` | List currently running processes |
| `get_hardware` | Full hardware specs (CPU, RAM, GPU) |
| `get_network` | Network adapters, IPs, DNS |
| `get_drives` | Drive information and space |
| `get_environment` | Environment variables |
| `explore_folder` | Browse directory contents |
| `find_app_path` | Find where an app is installed |
| `get_startup_apps` | List startup programs |
| `get_recent_files` | Get recently accessed files |
| `get_display_info` | Monitor info (resolution, primary, position) |
| `get_audio_devices` | List audio input/output devices |

## Hardware Detection

### CPU
- Model, cores, threads, architecture
- Current usage percentage

### RAM
- Total, available, used
- Type (DDR4, DDR5)
- Speed (MHz)
- Slots used

### GPU
- Model, VRAM (via nvidia-smi for NVIDIA)
- Driver version

### Storage
- All drives with total/free space
- Drive type (SSD, HDD)

## Multi-Monitor Support

`get_display_info` returns:
- All connected monitors
- Resolution per monitor
- Primary monitor flag
- Position coordinates
- Current mouse position per monitor

## Example Usage

```python
# Get basic PC info
result = await tool.execute("get_pc_info")
# Returns: computer_name, username, os, processor_arch

# Get detailed hardware
result = await tool.execute("get_hardware")
# Returns: cpu, ram (type, speed, slots), gpu (vram), storage

# Find Chrome installation
result = await tool.execute("find_app_path", app="chrome")
# Returns: path to chrome.exe

# Search for dev tools
result = await tool.execute("search_apps", category="dev")
# Returns: VS Code, Git, Python, Node.js, etc.

# Get network info
result = await tool.execute("get_network")
# Returns: adapters, IPs, DNS servers, gateway
```

## Caching

Results are cached to avoid repeated expensive queries. Cache is cleared on tool reinitialization.
