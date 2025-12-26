import pvporcupine
import numpy as np
import os
from typing import List, Optional
import logging
import secrets
from .persona import get_wake_responses

# Built-in Picovoice keywords (no .ppn file needed)
BUILTIN_KEYWORDS = [
    "alexa", "americano", "blueberry", "bumblebee", "computer",
    "grapefruit", "grasshopper", "hey barista", "hey google",
    "hey siri", "jarvis", "ok google", "pico clock", "picovoice",
    "porcupine", "terminator"
]

class WakeWordDetector:
    """Handles wake word detection using Picovoice Porcupine
    
    Supports both built-in keywords and custom trained .ppn files.
    For custom keywords, set WAKE_WORD_PATH in .env to the .ppn file path.
    """
    
    def __init__(self, access_key: str, keywords: List[str], keyword_paths: Optional[List[str]] = None, device: str = "best"):
        self.access_key = access_key
        self.keywords = keywords
        self.keyword_paths = keyword_paths or []
        self.device = device  # "best", "gpu:0", "cpu", etc.
        self.porcupine = None
        self.is_listening = False
        self._audio_buffer = np.array([], dtype=np.int16)  # Buffer for accumulating audio
        self._frame_length = 512  # Porcupine's required frame length
        self._last_detection_time = 0  # Debounce: prevent re-triggering within 1 second
        self._detection_cooldown = 1.0  # Seconds between detections
        
    def initialize(self) -> bool:
        """Initialize the wake word detector"""
        try:
            if not self.access_key:
                logging.warning("No Picovoice access key provided - wake word detection disabled")
                return False
            
            # Separate built-in keywords from custom ones
            builtin_kw = []
            custom_paths = []
            
            # First, add explicit keyword_paths (convert to absolute)
            for path in self.keyword_paths:
                abs_path = os.path.abspath(path)
                if os.path.exists(abs_path):
                    custom_paths.append(abs_path)
                    logging.info(f"Using custom wake word file: {abs_path}")
                else:
                    logging.warning(f"Custom wake word file not found: {path}")
            
            # Then process keywords list
            for kw in self.keywords:
                kw_lower = kw.lower()
                if kw_lower in BUILTIN_KEYWORDS:
                    builtin_kw.append(kw_lower)
                elif kw_lower.endswith('.ppn'):
                    # It's a path to a .ppn file
                    abs_path = os.path.abspath(kw)
                    if os.path.exists(abs_path):
                        custom_paths.append(abs_path)
                else:
                    # Non-builtin keyword - check if WAKE_WORD_PATH is set
                    ppn_path = os.getenv('WAKE_WORD_PATH', '')
                    if ppn_path:
                        abs_ppn = os.path.abspath(ppn_path)
                        if os.path.exists(abs_ppn) and abs_ppn not in custom_paths:
                            custom_paths.append(abs_ppn)
                            logging.info(f"Using custom wake word '{kw}' from: {abs_ppn}")
                        elif not os.path.exists(abs_ppn):
                            logging.warning(f"WAKE_WORD_PATH file not found: {ppn_path}")
                    else:
                        logging.warning(f"'{kw}' is not a built-in keyword. Train it at https://console.picovoice.ai/ and set WAKE_WORD_PATH")
            
            # Log available devices
            available = pvporcupine.available_devices()
            logging.info(f"Porcupine available devices: {available}")
            
            # Create porcupine with appropriate parameters
            if custom_paths and builtin_kw:
                # Both custom and built-in - NOTE: can't mix keywords and keyword_paths in same call
                # Use only custom paths if we have them
                logging.info(f"Using custom keyword paths: {custom_paths} on device: {self.device}")
                self.porcupine = pvporcupine.create(
                    access_key=self.access_key,
                    keyword_paths=custom_paths,
                    device=self.device
                )
                self.keywords = [os.path.basename(p).replace('.ppn', '').split('_')[0] for p in custom_paths]
            elif custom_paths:
                # Only custom keywords
                logging.info(f"Using custom keyword paths: {custom_paths} on device: {self.device}")
                self.porcupine = pvporcupine.create(
                    access_key=self.access_key,
                    keyword_paths=custom_paths,
                    device=self.device
                )
                self.keywords = [os.path.basename(p).replace('.ppn', '').split('_')[0] for p in custom_paths]
            elif builtin_kw:
                # Only built-in keywords
                self.porcupine = pvporcupine.create(
                    access_key=self.access_key,
                    keywords=builtin_kw,
                    device=self.device
                )
                self.keywords = builtin_kw
            else:
                logging.error("No valid wake words configured")
                return False
            
            # Get actual frame length from Porcupine
            self._frame_length = self.porcupine.frame_length
            logging.info(f"Wake word detector initialized with keywords: {self.keywords} (frame_length={self._frame_length})")
            return True
            
        except Exception as e:
            logging.error(f"Failed to initialize wake word detector: {e}")
            return False
    
    def process_audio(self, audio_chunk: bytes) -> Optional[str]:
        """
        Process audio chunk for wake word detection.
        Buffers audio and processes in 512-sample frames as required by Porcupine.
        Returns wake up response if wake word detected, None otherwise.
        Includes debouncing to prevent continuous re-triggering.
        """
        if not self.porcupine:
            # If no wake word detector, always listen
            self.is_listening = True
            return None
        
        import time
        current_time = time.time()
            
        try:
            # Convert bytes to numpy array and add to buffer
            pcm = np.frombuffer(audio_chunk, dtype=np.int16)
            self._audio_buffer = np.concatenate([self._audio_buffer, pcm])
            
            # Process all complete 512-sample frames in buffer
            while len(self._audio_buffer) >= self._frame_length:
                # Extract one frame - must be contiguous C array for Porcupine
                frame = np.ascontiguousarray(self._audio_buffer[:self._frame_length], dtype=np.int16)
                self._audio_buffer = self._audio_buffer[self._frame_length:]
                
                # Process frame through Porcupine
                keyword_index = self.porcupine.process(frame)
                
                if keyword_index >= 0:
                    # Debounce: only trigger if enough time has passed since last detection
                    if current_time - self._last_detection_time < self._detection_cooldown:
                        return None
                    
                    # If we are already listening, do not send another wake response for this current listening session
                    if self.is_listening:
                        return None
                    
                    detected_keyword = self.keywords[keyword_index]
                    self.is_listening = True
                    self._last_detection_time = current_time  # Update last detection time
                    wake_responses = get_wake_responses()
                    wake_response = wake_responses[secrets.randbelow(len(wake_responses))]
                    logging.info(f"Wake word '{detected_keyword}' detected")
                    # Clear buffer after detection to avoid re-triggering
                    self._audio_buffer = np.array([], dtype=np.int16)
                    return wake_response
                
        except Exception as e:
            logging.error(f"Error processing wake word: {type(e).__name__}: {e}")
            
        return None
    
    def stop_listening(self):
        """Stop listening after conversation ends"""
        self.is_listening = False
        # Clear audio buffer when stopping
        self._audio_buffer = np.array([], dtype=np.int16)
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