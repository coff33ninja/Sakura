"""
System Info Tool for Sakura
Self-discovery tool - lets Sakura learn about the system dynamically
"""

from enum import Enum
from .discovery import SystemDiscovery


class SystemActions(Enum):
    """Available system discovery actions"""
    GET_PC_INFO = "get_pc_info"
    GET_USER_FOLDERS = "get_user_folders"
    LIST_INSTALLED_APPS = "list_installed_apps"
    SEARCH_APPS = "search_apps"
    GET_RUNNING_APPS = "get_running_apps"
    GET_HARDWARE = "get_hardware"
    GET_NETWORK = "get_network"
    GET_DRIVES = "get_drives"
    GET_ENVIRONMENT = "get_environment"
    EXPLORE_FOLDER = "explore_folder"
    FIND_APP_PATH = "find_app_path"
    FIND_FILE = "find_file"
    GET_STARTUP_APPS = "get_startup_apps"
    GET_RECENT_FILES = "get_recent_files"
    GET_DISPLAY_INFO = "get_display_info"
    GET_AUDIO_DEVICES = "get_audio_devices"


__all__ = ['SystemDiscovery', 'SystemActions']
