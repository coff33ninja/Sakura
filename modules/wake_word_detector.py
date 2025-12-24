import pvporcupine
import numpy as np
from typing import List, Optional
import logging
import random
from .persona import WAKE_UP_RESPONSES

class WakeWordDetector:
    """Handles wake word detection using Picovoice Porcupine"""
    
    def __init__(self, access_key: str, keywords: List[str]):
        self.access_key = access_key
        self.keywords = keywords
        self.porcupine = None
        self.is_listening = False
        
    def initialize(self) -> bool:
        """Initialize the wake word detector"""
        try:
            if not self.access_key:
                logging.warning("No Picovoice access key provided - wake word detection disabled")
                return False
                
            self.porcupine = pvporcupine.create(
                access_key=self.access_key,
                keywords=self.keywords
            )
            logging.info(f"Wake word detector initialized with keywords: {self.keywords}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to initialize wake word detector: {e}")
            return False
    
    def process_audio(self, audio_chunk: bytes) -> Optional[str]:
        """
        Process audio chunk for wake word detection
        Returns wake up response if wake word detected, None otherwise
        """
        if not self.porcupine:
            # If no wake word detector, always listen
            self.is_listening = True
            return None
            
        try:
            # Porcupine expects 512 frame chunks
            pcm = np.frombuffer(audio_chunk, dtype=np.int16)
            
            # Resize to 512 frames if needed
            if len(pcm) != 512:
                if len(pcm) > 512:
                    pcm = pcm[:512]
                else:
                    # Pad with zeros
                    pcm = np.pad(pcm, (0, 512 - len(pcm)), 'constant')
            
            keyword_index = self.porcupine.process(pcm)
            
            if keyword_index >= 0:
                detected_keyword = self.keywords[keyword_index]
                self.is_listening = True
                wake_response = random.choice(WAKE_UP_RESPONSES)
                logging.info(f"Wake word '{detected_keyword}' detected")
                return wake_response
                
        except Exception as e:
            logging.error(f"Error processing wake word: {e}")
            
        return None
    
    def stop_listening(self):
        """Stop listening after conversation ends"""
        self.is_listening = False
        logging.info("Stopped listening - waiting for wake word")
    
    def cleanup(self):
        """Clean up wake word detector resources"""
        try:
            if self.porcupine:
                self.porcupine.delete()
                logging.info("Wake word detector cleanup completed")
        except Exception as e:
            logging.error(f"Error during wake word cleanup: {e}")
    
    def __enter__(self):
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()