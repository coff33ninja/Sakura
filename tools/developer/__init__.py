"""
Developer Tools for Sakura
Git operations, code execution, package management, SSH
"""

from enum import Enum
from .devtools import DeveloperTools


class DeveloperActions(Enum):
    """Available developer tool actions"""
    # Git Operations
    GIT_STATUS = "git_status"
    GIT_ADD = "git_add"
    GIT_COMMIT = "git_commit"
    GIT_PUSH = "git_push"
    GIT_PULL = "git_pull"
    GIT_BRANCH = "git_branch"
    GIT_CHECKOUT = "git_checkout"
    GIT_LOG = "git_log"
    GIT_DIFF = "git_diff"
    GIT_CLONE = "git_clone"
    GIT_INIT = "git_init"
    
    # Code Execution
    RUN_PYTHON = "run_python"
    RUN_JAVASCRIPT = "run_javascript"
    RUN_POWERSHELL = "run_powershell"
    RUN_BATCH = "run_batch"
    
    # Package Management
    PIP_INSTALL = "pip_install"
    PIP_UNINSTALL = "pip_uninstall"
    PIP_LIST = "pip_list"
    NPM_INSTALL = "npm_install"
    NPM_UNINSTALL = "npm_uninstall"
    NPM_LIST = "npm_list"
    WINGET_SEARCH = "winget_search"
    WINGET_INSTALL = "winget_install"
    WINGET_UNINSTALL = "winget_uninstall"
    WINGET_LIST = "winget_list"
    
    # Connection Profiles
    ADD_PROFILE = "add_profile"
    LIST_PROFILES = "list_profiles"
    GET_PROFILE = "get_profile"
    DELETE_PROFILE = "delete_profile"
    UPDATE_PROFILE = "update_profile"
    
    # SSH Operations
    SSH_CONNECT = "ssh_connect"
    SSH_RUN_COMMAND = "ssh_run_command"
    SSH_ADD_PROFILE = "ssh_add_profile"
    SSH_LIST_PROFILES = "ssh_list_profiles"
    SSH_DELETE_PROFILE = "ssh_delete_profile"
    
    # SMB Operations
    SMB_CONNECT = "smb_connect"
    SMB_MAP_DRIVE = "smb_map_drive"
    SMB_UNMAP_DRIVE = "smb_unmap_drive"
    SMB_LIST_SHARES = "smb_list_shares"
    
    # FTP Operations
    FTP_CONNECT = "ftp_connect"
    FTP_LIST = "ftp_list"
    FTP_UPLOAD = "ftp_upload"
    FTP_DOWNLOAD = "ftp_download"
    
    # RDP Operations
    RDP_CONNECT = "rdp_connect"
    
    # Utility
    CHECK_TOOLS = "check_tools"
    FIND_TOOL_PATH = "find_tool_path"
    RUN_MULTIPLE_COMMANDS = "run_multiple_commands"


__all__ = ['DeveloperTools', 'DeveloperActions']
