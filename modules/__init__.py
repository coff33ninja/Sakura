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
from .conversation_context import ConversationContext
from .task_chain import TaskChain, TaskChainBuilder, TaskChainResult, ChainTask, TaskStatus
from .error_recovery import (
    ErrorRecovery, ErrorCategory, RetryConfig, RecoveryResult, 
    ErrorRecord, categorize_tool_error
)
from .user_preferences import (
    UserPreferences, PreferenceType, Correction, Preference, Shortcut
)
from .suggestions import (
    SuggestionEngine, SuggestionType, SuggestionPriority, Suggestion, SuggestionFeedback
)
from .intent_parser import IntentParser, IntentType, ParsedIntent
from .background_tasks import BackgroundTaskManager, BackgroundTask, TaskState

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
    'AsyncConfigLoader', 'AsyncFileManager', 'AsyncLogger', 'AsyncBackupManager',
    
    # Context & Chaining
    'ConversationContext', 'TaskChain', 'TaskChainBuilder', 'TaskChainResult', 
    'ChainTask', 'TaskStatus',
    
    # Error Recovery
    'ErrorRecovery', 'ErrorCategory', 'RetryConfig', 'RecoveryResult',
    'ErrorRecord', 'categorize_tool_error',
    
    # User Preferences
    'UserPreferences', 'PreferenceType', 'Correction', 'Preference', 'Shortcut',
    
    # Suggestions
    'SuggestionEngine', 'SuggestionType', 'SuggestionPriority', 'Suggestion', 'SuggestionFeedback',
    
    # Intent Parsing
    'IntentParser', 'IntentType', 'ParsedIntent',
    
    # Background Tasks
    'BackgroundTaskManager', 'BackgroundTask', 'TaskState'
]