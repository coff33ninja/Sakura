import pyaudio
import pygame
import numpy as np
from typing import Optional
from collections import deque
import logging

class AudioManager:
    """Handles audio input/output operations"""
    
    # Gemini Live API requirements
    SEND_SAMPLE_RATE = 16000    # Input audio must be 16kHz
    RECEIVE_SAMPLE_RATE = 24000  # Output audio is 24kHz
    
    # Echo cancellation parameters
    ECHO_BUFFER_SIZE = 8  # Number of chunks to keep for echo cancellation
    ECHO_THRESHOLD = 0.15  # Threshold for detecting speaker output in microphone
    
    def __init__(self, sample_rate: int = 24000, chunk_size: int = 1024):
        self.chunk_size = chunk_size
        self.p = None
        self.stream_in = None
        self.stream_out = None
        self.echo_buffer = deque(maxlen=self.ECHO_BUFFER_SIZE)  # Track recent output audio
        self.last_output_chunk = None
        
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
        """Read audio chunk from microphone with echo cancellation"""
        try:
            if self.stream_in:
                audio_chunk = self.stream_in.read(self.chunk_size, exception_on_overflow=False)
                
                # Apply echo cancellation to reduce feedback
                if audio_chunk:
                    audio_chunk = self._apply_echo_cancellation(audio_chunk)
                
                return audio_chunk
        except Exception as e:
            logging.error(f"Error reading audio: {e}")
        return None
    
    def _apply_echo_cancellation(self, mic_chunk: bytes) -> bytes:
        """
        Remove speaker output from microphone input to prevent feedback loop.
        Uses correlation-based echo detection and subtraction.
        
        Args:
            mic_chunk: Audio bytes from microphone
            
        Returns:
            Cleaned audio bytes with echo reduced
        """
        try:
            # Convert to numpy array for processing
            mic_audio = np.frombuffer(mic_chunk, dtype=np.int16).astype(np.float32)
            
            # Check each buffered output chunk for correlation (echo detection)
            for speaker_chunk in self.echo_buffer:
                if speaker_chunk is None or len(speaker_chunk) == 0:
                    continue
                
                # Resample speaker audio to match mic sample rate if needed
                speaker_audio = np.frombuffer(speaker_chunk, dtype=np.int16).astype(np.float32)
                
                # Normalize for correlation
                mic_norm = np.linalg.norm(mic_audio)
                speaker_norm = np.linalg.norm(speaker_audio)
                
                if mic_norm < 1e-5 or speaker_norm < 1e-5:
                    continue
                
                # Compute correlation to detect echo
                # Match the shorter length for correlation
                min_len = min(len(mic_audio), len(speaker_audio))
                correlation = np.correlate(
                    mic_audio[:min_len], 
                    speaker_audio[:min_len], 
                    mode='valid'
                )
                
                if len(correlation) > 0:
                    # Normalize correlation
                    max_corr = np.max(np.abs(correlation)) / (mic_norm * speaker_norm / min_len)
                    
                    # If high correlation detected, this is likely echo - reduce it
                    if max_corr > self.ECHO_THRESHOLD:
                        # Subtract a scaled version of speaker audio from mic audio
                        scale_factor = min(0.8, max_corr)  # Cap the scaling
                        
                        if len(speaker_audio) >= len(mic_audio):
                            mic_audio = mic_audio - (speaker_audio[:len(mic_audio)] * scale_factor * 0.5)
                        else:
                            # Pad speaker audio if it's shorter
                            padded = np.pad(speaker_audio, (0, len(mic_audio) - len(speaker_audio)))
                            mic_audio = mic_audio - (padded * scale_factor * 0.5)
                        
                        logging.debug(f"Echo detected and reduced (correlation: {max_corr:.2f})")
            
            # Normalize to prevent clipping
            max_val = np.max(np.abs(mic_audio))
            if max_val > 32767:
                mic_audio = mic_audio * (32767 / max_val)
            
            # Clip to valid int16 range
            mic_audio = np.clip(mic_audio, -32768, 32767).astype(np.int16)
            
            return mic_audio.tobytes()
            
        except Exception as e:
            logging.warning(f"Echo cancellation error (returning original audio): {e}")
            return mic_chunk
    
    def play_audio(self, audio_data: bytes):
        """Play audio through speakers with buffering and echo tracking"""
        try:
            if self.stream_out and audio_data and len(audio_data) > 0:
                # Track this output for echo cancellation
                self.echo_buffer.append(audio_data)
                self.last_output_chunk = audio_data
                
                # Play the audio
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