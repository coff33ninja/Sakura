"""
Discord Integration Tools
Allow Sakura to interact with Discord
"""

from enum import Enum
from .bot import DiscordBot


class DiscordActions(Enum):
    """Available Discord tool actions"""
    # Messages
    SEND_MESSAGE = "send_message"
    READ_MESSAGES = "read_messages"
    
    # Channel Information
    GET_CHANNELS = "get_channels"
    GET_GUILDS = "get_guilds"
    GET_VOICE_CHANNELS = "get_voice_channels"
    
    # Voice Control
    JOIN_VOICE = "join_voice"
    LEAVE_VOICE = "leave_voice"
    SPEAK_IN_VOICE = "speak_in_voice"


__all__ = ['DiscordBot', 'DiscordActions']
