import os
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class VoiceConfig:
    """Configuration for voice settings
    
    Available Gemini voices:
    - Aoede: Warm, friendly female voice (default)
    - Charon: Deep, calm male voice
    - Fenrir: Energetic male voice
    - Kore: Soft, gentle female voice
    - Puck: Playful, expressive voice
    """
    voice_name: str = "Aoede"
    sample_rate: int = 24000
    chunk_size: int = 1024
    
    def __post_init__(self):
        """Validate voice configuration"""
        # Validate sample rate
        if self.sample_rate <= 0:
            raise ValueError(f"sample_rate must be positive, got {self.sample_rate}")
        if self.sample_rate < 8000 or self.sample_rate > 48000:
            raise ValueError(
                f"sample_rate must be between 8000-48000 Hz, got {self.sample_rate}. "
                "Common values: 16000 (8kHz), 24000 (24kHz), 44100 (44.1kHz), 48000 (48kHz)"
            )
        
        # Validate chunk size (should be power of 2 for audio processing)
        chunk = self.chunk_size
        if chunk <= 0:
            raise ValueError(f"chunk_size must be positive, got {chunk}")
        if chunk < 256 or chunk > 65536:
            raise ValueError(
                f"chunk_size should be 256-65536 bytes, got {chunk}. "
                "Common values: 512, 1024, 2048, 4096"
            )
        
        # Warn if chunk_size is not power of 2
        if chunk & (chunk - 1) != 0:  # Check if power of 2
            import logging
            logging.warning(
                f"chunk_size {chunk} is not a power of 2. "
                "This may reduce audio quality. Consider using 512, 1024, 2048, or 4096."
            )

@dataclass
class WakeWordConfig:
    """Configuration for wake word detection
    
    Note: Custom wake words require training on Picovoice Console:
    https://console.picovoice.ai/
    
    Built-in keywords available without training:
    alexa, americano, blueberry, bumblebee, computer, grapefruit,
    grasshopper, hey barista, hey google, hey siri, jarvis, ok google,
    pico clock, picovoice, porcupine, terminator
    """
    enabled: bool = True
    keywords: List[str] = None
    access_key: Optional[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            # Use ASSISTANT_NAME as wake word, or default to built-in "jarvis"
            name = os.getenv("ASSISTANT_NAME", "Sakura").lower()
            # Check if it's a built-in Picovoice keyword
            builtin = ["alexa", "americano", "blueberry", "bumblebee", "computer", 
                      "grapefruit", "grasshopper", "hey barista", "hey google", 
                      "hey siri", "jarvis", "ok google", "pico clock", "picovoice", 
                      "porcupine", "terminator"]
            if name in builtin:
                self.keywords = [name]
            else:
                # Custom name needs Picovoice training, fallback to jarvis
                self.keywords = ["jarvis"]
        if self.access_key is None:
            self.access_key = os.getenv("PICOVOICE_ACCESS_KEY")

@dataclass
class GeminiConfig:
    """Configuration for Gemini API"""
    api_key: Optional[str] = None
    model: str = "gemini-2.5-flash-native-audio-preview-12-2025"
    personality: str = "friendly, helpful, and informative"  # Default personality
    assistant_name: str = "Sakura"  # Default assistant name
    
    def __post_init__(self):
        if self.api_key is None:
            self.api_key = os.getenv("GEMINI_API_KEY")

@dataclass
class AppConfig:
    """Main application configuration"""
    voice: VoiceConfig = None
    wake_word: WakeWordConfig = None
    gemini: GeminiConfig = None
    session_file: str = None  # Will be set from env or use default
    db_path: str = None  # Will be set from env or use default
    conversation_context_file: str = None  # Will be set from env or use default
    
    def __post_init__(self):
        if self.voice is None:
            self.voice = VoiceConfig()
        if self.wake_word is None:
            self.wake_word = WakeWordConfig()
        if self.gemini is None:
            self.gemini = GeminiConfig()
        
        # Session file with environment override
        if self.session_file is None:
            self.session_file = os.getenv("SESSION_FILE", "gf_session.txt")
        
        # Database path with environment override
        if self.db_path is None:
            self.db_path = os.getenv("DB_PATH", "sakura.db")
        
        # Conversation context file with environment override
        if self.conversation_context_file is None:
            self.conversation_context_file = os.getenv("CONVERSATION_CONTEXT_FILE", "conversation_context.json")