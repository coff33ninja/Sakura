"""
Windows Tools
Windows-specific automation and control tools for Sakura
"""

from enum import Enum
from .automation import WindowsAutomation


class WindowsActions(Enum):
    """Available Windows automation actions"""
    # Process & Command Control
    RUN_COMMAND = "run_command"
    OPEN_APP = "open_app"
    LIST_PROCESSES = "list_processes"
    KILL_PROCESS = "kill_process"
    
    # File & Folder Operations
    SEARCH_FILES = "search_files"
    LIST_FILES = "list_files"
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    DELETE_FILE = "delete_file"
    CREATE_FOLDER = "create_folder"
    DELETE_FOLDER = "delete_folder"
    
    # System Info
    GET_SYSTEM_INFO = "get_system_info"
    GET_MEMORY_STATUS = "get_memory_status"
    GET_DRIVES = "get_drives"
    
    # Web & URL
    OPEN_URL = "open_url"
    
    # Keyboard & Input
    TYPE_TEXT = "type_text"
    PRESS_KEY = "press_key"
    SEND_HOTKEY = "send_hotkey"
    
    # Screen & Window
    SCREENSHOT = "screenshot"
    LIST_WINDOWS = "list_windows"
    FOCUS_WINDOW = "focus_window"
    MINIMIZE_WINDOW = "minimize_window"
    MAXIMIZE_WINDOW = "maximize_window"
    SNAP_WINDOW = "snap_window"
    
    # Mouse Control
    MOVE_MOUSE = "move_mouse"
    CLICK_MOUSE = "click_mouse"
    RIGHT_CLICK_MENU = "right_click_menu"
    DRAG_MOUSE = "drag_mouse"
    SCROLL_MOUSE = "scroll_mouse"
    GET_MOUSE_POSITION = "get_mouse_position"
    
    # UI Element Control
    READ_SCREEN = "read_screen"
    READ_WINDOW_TEXT = "read_window_text"
    GET_UI_ELEMENTS = "get_ui_elements"
    FIND_UI_ELEMENT = "find_ui_element"
    CLICK_UI_ELEMENT = "click_ui_element"
    GET_FOCUSED_ELEMENT = "get_focused_element"
    READ_WINDOW_CONTENT = "read_window_content"
    READ_TEXT_AT_POSITION = "read_text_at_position"
    FIND_CLICKABLE_ELEMENT = "find_clickable_element"
    CLICK_ELEMENT_BY_NAME = "click_element_by_name"
    
    # Clipboard
    GET_CLIPBOARD = "get_clipboard"
    SET_CLIPBOARD = "set_clipboard"
    
    # Script Execution
    EXECUTE_SCRIPT = "execute_script"
    
    # Media Control
    VOLUME_CONTROL = "volume_control"
    MEDIA_CONTROL = "media_control"
    
    # System Control
    VIRTUAL_DESKTOP = "virtual_desktop"
    LOCK_SCREEN = "lock_screen"
    POWER_ACTION = "power_action"


__all__ = ['WindowsAutomation', 'WindowsActions']
