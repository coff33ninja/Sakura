"""
AI Girlfriend Voice Chat - Modules Package
"""

# Core modules
from .config import AppConfig, VoiceConfig, WakeWordConfig, GeminiConfig
from .persona import (
    get_current_persona, get_wake_responses, get_goodbye_responses,
    PersonalityMode, PERSONAS, CURRENT_PERSONALITY,
    # Backwards compatibility
    FLIRTY_GIRLFRIEND_PERSONA, WAKE_UP_RESPONSES_LIST, GOODBYE_RESPONSES_LIST
)
from .audio_manager import AudioManager
from .wake_word_detector import WakeWordDetector
from .session_manager import SessionManager
from .gemini_client import GeminiVoiceClient
from .api_key_manager import APIKeyManager, APIKey, KeyStatus
from .async_config_loader import AsyncConfigLoader
from .async_utils import AsyncFileManager, AsyncLogger, AsyncBackupManager

__all__ = [
    # Configuration
    'AppConfig', 'VoiceConfig', 'WakeWordConfig', 'GeminiConfig',
    
    # Persona
    'get_current_persona', 'get_wake_responses', 'get_goodbye_responses',
    'PersonalityMode', 'PERSONAS', 'CURRENT_PERSONALITY',
    'FLIRTY_GIRLFRIEND_PERSONA', 'WAKE_UP_RESPONSES_LIST', 'GOODBYE_RESPONSES_LIST',
    
    # Core components
    'AudioManager', 'WakeWordDetector', 'SessionManager', 'GeminiVoiceClient',
    
    # API management
    'APIKeyManager', 'APIKey', 'KeyStatus',
    
    # Async utilities
    'AsyncConfigLoader', 'AsyncFileManager', 'AsyncLogger', 'AsyncBackupManager'
]