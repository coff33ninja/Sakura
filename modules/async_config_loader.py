import os
import json
import logging
import asyncio
import aiofiles
from typing import Dict, Any, Optional
from dataclasses import asdict
from .config import AppConfig

class AsyncConfigLoader:
    """Handles loading and saving configuration with async file I/O"""
    
    def __init__(self, config_file: str = "app_config.json"):
        self.config_file = config_file
        self._lock = asyncio.Lock()
        self._cached_config: Optional[AppConfig] = None
    
    async def load_config(self) -> AppConfig:
        """Load configuration from file and environment"""
        async with self._lock:
            config = AppConfig()
            
            # Try to load from file first
            if os.path.exists(self.config_file):
                try:
                    async with aiofiles.open(self.config_file, 'r') as f:
                        content = await f.read()
                        file_config = json.loads(content)
                    
                    # Update config with file values
                    await self._update_config_from_dict(config, file_config)
                    logging.info(f"Configuration loaded from {self.config_file}")
                    
                except Exception as e:
                    logging.warning(f"Failed to load config file: {e}")
            
            # Environment variables always override file config
            self._update_config_from_env(config)
            
            # Cache the loaded config
            self._cached_config = config
            
            return config
    
    async def save_config(self, config: AppConfig):
        """Save configuration to file (excluding sensitive data)"""
        async with self._lock:
            try:
                # Convert to dict but exclude sensitive data
                config_dict = self._config_to_safe_dict(config)
                
                async with aiofiles.open(self.config_file, 'w') as f:
                    await f.write(json.dumps(config_dict, indent=2))
                
                # Update cache
                self._cached_config = config
                logging.info(f"Configuration saved to {self.config_file}")
                
            except Exception as e:
                logging.error(f"Failed to save config: {e}")
    
    def get_cached_config(self) -> Optional[AppConfig]:
        """Get the cached config without reloading from file"""
        return self._cached_config
    
    def config_to_full_dict(self, config: AppConfig) -> Dict[str, Any]:
        """Convert entire config to dict using asdict (includes all fields)"""
        full_dict = asdict(config)
        # Remove sensitive keys
        if 'wake_word' in full_dict and 'access_key' in full_dict['wake_word']:
            full_dict['wake_word']['access_key'] = '***' if full_dict['wake_word']['access_key'] else None
        if 'gemini' in full_dict and 'api_key' in full_dict['gemini']:
            full_dict['gemini']['api_key'] = '***' if full_dict['gemini']['api_key'] else None
        return full_dict
    
    def _config_to_safe_dict(self, config: AppConfig) -> Dict[str, Any]:
        """Convert config to dict excluding sensitive data"""
        config_dict = {
            'voice': {
                'voice_name': config.voice.voice_name,
                'sample_rate': config.voice.sample_rate,
                'chunk_size': config.voice.chunk_size
            },
            'wake_word': {
                'enabled': config.wake_word.enabled,
                'keywords': config.wake_word.keywords,
                # Don't save access_key - always from env
            },
            'gemini': {
                'model': config.gemini.model,
                # Don't save api_key - always from env
            },
            'session_file': config.session_file
        }
        return config_dict
    
    async def _update_config_from_dict(self, config: AppConfig, config_dict: Dict[str, Any]):
        """Update config object from dictionary"""
        if 'voice' in config_dict:
            voice_config = config_dict['voice']
            config.voice.voice_name = voice_config.get('voice_name', config.voice.voice_name)
            config.voice.sample_rate = voice_config.get('sample_rate', config.voice.sample_rate)
            config.voice.chunk_size = voice_config.get('chunk_size', config.voice.chunk_size)
        
        if 'wake_word' in config_dict:
            wake_config = config_dict['wake_word']
            config.wake_word.enabled = wake_config.get('enabled', config.wake_word.enabled)
            config.wake_word.keywords = wake_config.get('keywords', config.wake_word.keywords)
        
        if 'gemini' in config_dict:
            gemini_config = config_dict['gemini']
            config.gemini.model = gemini_config.get('model', config.gemini.model)
        
        if 'session_file' in config_dict:
            config.session_file = config_dict['session_file']
    
    def _update_config_from_env(self, config: AppConfig):
        """Update config from environment variables"""
        # Voice settings
        if os.getenv('VOICE_NAME'):
            config.voice.voice_name = os.getenv('VOICE_NAME')
        if os.getenv('VOICE_SAMPLE_RATE'):
            try:
                config.voice.sample_rate = int(os.getenv('VOICE_SAMPLE_RATE'))
            except ValueError:
                pass
        
        # Wake word settings
        if os.getenv('WAKE_WORD_ENABLED'):
            config.wake_word.enabled = os.getenv('WAKE_WORD_ENABLED').lower() == 'true'
        if os.getenv('WAKE_WORD_KEYWORDS'):
            # Explicit keywords override everything
            config.wake_word.keywords = [k.strip() for k in os.getenv('WAKE_WORD_KEYWORDS').split(',')]
        elif os.getenv('ASSISTANT_NAME'):
            # Use assistant name as wake word if it's a built-in
            name = os.getenv('ASSISTANT_NAME').lower()
            builtin = ["alexa", "americano", "blueberry", "bumblebee", "computer", 
                      "grapefruit", "grasshopper", "hey barista", "hey google", 
                      "hey siri", "jarvis", "ok google", "pico clock", "picovoice", 
                      "porcupine", "terminator"]
            if name in builtin:
                config.wake_word.keywords = [name]
        
        # Gemini settings
        if os.getenv('GEMINI_MODEL'):
            config.gemini.model = os.getenv('GEMINI_MODEL')
        
        # Session file
        if os.getenv('SESSION_FILE'):
            config.session_file = os.getenv('SESSION_FILE')
    
    async def create_default_config(self) -> AppConfig:
        """Create and save a default configuration file"""
        config = AppConfig()
        await self.save_config(config)
        return config
    
    async def get_config_status(self) -> Dict[str, Any]:
        """Get configuration file status"""
        async with self._lock:
            status = {
                'config_file_exists': os.path.exists(self.config_file),
                'config_file_path': os.path.abspath(self.config_file),
                'environment_variables': {
                    'GEMINI_API_KEY': bool(os.getenv('GEMINI_API_KEY')),
                    'PICOVOICE_ACCESS_KEY': bool(os.getenv('PICOVOICE_ACCESS_KEY')),
                    'VOICE_NAME': os.getenv('VOICE_NAME'),
                    'GEMINI_MODEL': os.getenv('GEMINI_MODEL'),
                }
            }
            
            if status['config_file_exists']:
                try:
                    stat = await asyncio.get_event_loop().run_in_executor(
                        None, os.stat, self.config_file
                    )
                    status['config_file_size'] = stat.st_size
                    status['config_file_modified'] = stat.st_mtime
                except Exception as e:
                    status['config_file_error'] = str(e)
            
            return status