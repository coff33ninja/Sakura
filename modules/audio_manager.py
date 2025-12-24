import pyaudio
import pygame
import numpy as np
from typing import Optional
import logging

class AudioManager:
    """Handles audio input/output operations"""
    
    # Gemini Live API requirements
    SEND_SAMPLE_RATE = 16000    # Input audio must be 16kHz
    RECEIVE_SAMPLE_RATE = 24000  # Output audio is 24kHz
    
    def __init__(self, sample_rate: int = 24000, chunk_size: int = 1024):
        self.chunk_size = chunk_size
        self.p = None
        self.stream_in = None
        self.stream_out = None
        
    def initialize(self):
        """Initialize audio streams"""
        try:
            self.p = pyaudio.PyAudio()
            
            # Input stream (microphone) - 16kHz for Gemini
            self.stream_in = self.p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.SEND_SAMPLE_RATE,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            # Output stream (speakers) - 24kHz from Gemini
            self.stream_out = self.p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.RECEIVE_SAMPLE_RATE,
                output=True,
                frames_per_buffer=self.chunk_size * 2  # Larger buffer for smoother playback
            )
            
            # Initialize pygame mixer for additional audio features
            pygame.mixer.init(frequency=self.RECEIVE_SAMPLE_RATE)
            
            logging.info("Audio streams initialized successfully")
            return True
            
        except Exception as e:
            logging.error(f"Failed to initialize audio: {e}")
            return False
    
    def read_audio_chunk(self) -> Optional[bytes]:
        """Read audio chunk from microphone"""
        try:
            if self.stream_in:
                return self.stream_in.read(self.chunk_size, exception_on_overflow=False)
        except Exception as e:
            logging.error(f"Error reading audio: {e}")
        return None
    
    def play_audio(self, audio_data: bytes):
        """Play audio through speakers with buffering"""
        try:
            if self.stream_out and audio_data and len(audio_data) > 0:
                self.stream_out.write(audio_data)
        except Exception as e:
            logging.error(f"Error playing audio: {e}")
    
    def audio_to_numpy(self, audio_chunk: bytes) -> np.ndarray:
        """Convert audio bytes to numpy array"""
        return np.frombuffer(audio_chunk, dtype=np.int16)
    
    def cleanup(self):
        """Clean up audio resources"""
        try:
            if self.stream_in:
                self.stream_in.stop_stream()
                self.stream_in.close()
            
            if self.stream_out:
                self.stream_out.stop_stream()
                self.stream_out.close()
                
            if self.p:
                self.p.terminate()
                
            pygame.mixer.quit()
            logging.info("Audio cleanup completed")
            
        except Exception as e:
            logging.error(f"Error during audio cleanup: {e}")
    
    def __enter__(self):
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()