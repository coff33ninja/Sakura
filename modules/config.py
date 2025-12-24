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
    
    def __post_init__(self):
        if self.api_key is None:
            self.api_key = os.getenv("GEMINI_API_KEY")

@dataclass
class AppConfig:
    """Main application configuration"""
    voice: VoiceConfig = None
    wake_word: WakeWordConfig = None
    gemini: GeminiConfig = None
    session_file: str = "gf_session.txt"
    
    def __post_init__(self):
        if self.voice is None:
            self.voice = VoiceConfig()
        if self.wake_word is None:
            self.wake_word = WakeWordConfig()
        if self.gemini is None:
            self.gemini = GeminiConfig()