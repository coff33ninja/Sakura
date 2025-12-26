"""
Memory Tools
Long-term memory and knowledge storage for Sakura
"""

from enum import Enum
from .store import MemoryStore


class MemoryActions(Enum):
    """Available memory tool actions"""
    # Memory Management
    REMEMBER = "remember"
    RECALL = "recall"
    FORGET = "forget"
    SEARCH_MEMORIES = "search_memories"
    LIST_MEMORIES = "list_memories"
    
    # User Information
    STORE_USER_INFO = "store_user_info"
    GET_USER_INFO = "get_user_info"
    UPDATE_USER_INFO = "update_user_info"
    
    # Preferences
    STORE_PREFERENCE = "store_preference"
    GET_PREFERENCES = "get_preferences"
    UPDATE_PREFERENCE = "update_preference"
    
    # Dates & Events
    REMEMBER_DATE = "remember_date"
    GET_IMPORTANT_DATES = "get_important_dates"
    FORGET_DATE = "forget_date"
    
    # Topics
    TRACK_TOPIC = "track_topic"
    GET_TOPICS = "get_topics"
    GET_TOPIC_HISTORY = "get_topic_history"
    
    # Locations
    REMEMBER_LOCATION = "remember_location"
    GET_LOCATIONS = "get_locations"
    
    # Connections
    ADD_CONNECTION = "add_connection"
    GET_CONNECTIONS = "get_connections"
    UPDATE_CONNECTION = "update_connection"


__all__ = ['MemoryStore', 'MemoryActions']
