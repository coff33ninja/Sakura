import os
import json
import logging
import asyncio
import aiofiles
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

class KeyStatus(Enum):
    ACTIVE = "active"
    RATE_LIMITED = "rate_limited"
    EXPIRED = "expired"
    INVALID = "invalid"
    DISABLED = "disabled"

@dataclass
class APIKey:
    """Represents an API key with its metadata"""
    key: str
    name: str
    status: KeyStatus = KeyStatus.ACTIVE
    last_used: Optional[datetime] = None
    rate_limit_reset: Optional[datetime] = None
    usage_count: int = 0
    error_count: int = 0
    max_errors: int = 5
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['status'] = self.status.value
        data['last_used'] = self.last_used.isoformat() if self.last_used else None
        data['rate_limit_reset'] = self.rate_limit_reset.isoformat() if self.rate_limit_reset else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'APIKey':
        """Create from dictionary"""
        data['status'] = KeyStatus(data['status'])
        if data['last_used']:
            data['last_used'] = datetime.fromisoformat(data['last_used'])
        if data['rate_limit_reset']:
            data['rate_limit_reset'] = datetime.fromisoformat(data['rate_limit_reset'])
        return cls(**data)

class APIKeyManager:
    """Manages multiple API keys with automatic rotation and failover"""
    
    def __init__(self, keys_file: str = "api_keys.json"):
        self.keys_file = keys_file
        self.keys: List[APIKey] = []
        self.current_key_index = 0
        self.rotation_enabled = True
        self._lock = asyncio.Lock()
        
    async def load_keys(self) -> bool:
        """Load API keys from environment and file.
        
        Returns:
            bool: True if at least one key was loaded, False otherwise
        """
        async with self._lock:
            self.keys = []
            
            # Load from environment variables
            await self._load_from_environment()
            
            # Load from file if exists
            if os.path.exists(self.keys_file):
                await self._load_from_file()
            
            if not self.keys:
                logging.error("❌ No API keys loaded - GEMINI_API_KEY environment variable not set")
                logging.error("Get your key at: https://ai.google.dev/")
                return False
            
            logging.info(f"✅ Loaded {len(self.keys)} API key(s)")
            return True
    
    async def _load_from_environment(self):
        """Load keys from environment variables"""
        # Support multiple key formats:
        # GEMINI_API_KEY (primary)
        # GEMINI_API_KEY_1, GEMINI_API_KEY_2, ... (numbered)
        
        # Load primary key first
        primary_key = os.getenv("GEMINI_API_KEY")
        if primary_key:
            name = os.getenv("GEMINI_API_KEY_NAME", "primary")
            self.keys.append(APIKey(
                key=primary_key,
                name=name,
                status=KeyStatus.ACTIVE
            ))
        
        # Load numbered keys (GEMINI_API_KEY_2, GEMINI_API_KEY_3, etc.)
        for i in range(2, 20):  # Support up to 20 keys
            key_var = f"GEMINI_API_KEY_{i}"
            key = os.getenv(key_var)
            if not key:
                continue
                
            name_var = f"GEMINI_API_KEY_{i}_NAME"
            name = os.getenv(name_var, f"env_key_{i}")
            
            # Skip duplicates
            if any(k.key == key for k in self.keys):
                continue
                
            self.keys.append(APIKey(
                key=key,
                name=name,
                status=KeyStatus.ACTIVE
            ))
    
    async def _load_from_file(self):
        """Load keys from JSON file"""
        try:
            async with aiofiles.open(self.keys_file, 'r') as f:
                content = await f.read()
                data = json.loads(content)
                
            for key_data in data.get('keys', []):
                api_key = APIKey.from_dict(key_data)
                # Don't load keys that are already from environment
                if not any(k.key == api_key.key for k in self.keys):
                    self.keys.append(api_key)
                    
        except Exception as e:
            logging.error(f"Failed to load keys from file: {e}")
    
    async def save_keys(self):
        """Save key metadata to file (not the actual keys)"""
        try:
            async with self._lock:
                # Only save keys that aren't from environment
                env_keys = {os.getenv(f"GEMINI_API_KEY_{i}" if i > 1 else "GEMINI_API_KEY") 
                           for i in range(1, 10) if os.getenv(f"GEMINI_API_KEY_{i}" if i > 1 else "GEMINI_API_KEY")}
                
                file_keys = [k for k in self.keys if k.key not in env_keys]
                
                data = {
                    'keys': [key.to_dict() for key in file_keys],
                    'current_index': self.current_key_index,
                    'rotation_enabled': self.rotation_enabled,
                    'last_updated': datetime.now().isoformat()
                }
                
                async with aiofiles.open(self.keys_file, 'w') as f:
                    await f.write(json.dumps(data, indent=2))
                    
        except Exception as e:
            logging.error(f"Failed to save keys: {e}")
    
    async def add_key(self, key: str, name: str) -> bool:
        """Add a new API key"""
        async with self._lock:
            if any(k.key == key for k in self.keys):
                logging.warning(f"Key {name} already exists")
                return False
                
            self.keys.append(APIKey(
                key=key,
                name=name,
                status=KeyStatus.ACTIVE
            ))
            
            await self.save_keys()
            logging.info(f"Added new API key: {name}")
            return True
    
    async def get_current_key(self) -> Optional[APIKey]:
        """Get the current active API key"""
        async with self._lock:
            if not self.keys:
                return None
                
            # Find next available key
            for _ in range(len(self.keys)):
                key = self.keys[self.current_key_index]
                
                if await self._is_key_available(key):
                    return key
                
                # Move to next key
                if self.rotation_enabled:
                    self.current_key_index = (self.current_key_index + 1) % len(self.keys)
                else:
                    break
            
            # No available keys
            logging.error("No available API keys")
            return None
    
    async def _is_key_available(self, key: APIKey) -> bool:
        """Check if a key is available for use"""
        now = datetime.now()
        
        # Check if key is disabled or invalid
        if key.status in [KeyStatus.DISABLED, KeyStatus.INVALID, KeyStatus.EXPIRED]:
            return False
        
        # Check if rate limit has reset
        if key.status == KeyStatus.RATE_LIMITED:
            if key.rate_limit_reset and now >= key.rate_limit_reset:
                key.status = KeyStatus.ACTIVE
                logging.info(f"Key {key.name} rate limit reset")
            else:
                return False
        
        # Check error count
        if key.error_count >= key.max_errors:
            key.status = KeyStatus.DISABLED
            logging.warning(f"Key {key.name} disabled due to too many errors")
            return False
        
        return True
    
    async def mark_key_used(self, key: APIKey, success: bool = True):
        """Mark a key as used and update its status"""
        async with self._lock:
            key.last_used = datetime.now()
            key.usage_count += 1
            
            if not success:
                key.error_count += 1
                logging.warning(f"Key {key.name} error count: {key.error_count}")
            else:
                # Reset error count on successful use
                key.error_count = max(0, key.error_count - 1)
            
            # Save asynchronously without blocking
            asyncio.create_task(self.save_keys())
    
    async def handle_rate_limit(self, key: APIKey, reset_time: Optional[datetime] = None):
        """Handle rate limit for a key"""
        async with self._lock:
            key.status = KeyStatus.RATE_LIMITED
            key.rate_limit_reset = reset_time or (datetime.now() + timedelta(minutes=60))
            
            logging.warning(f"Key {key.name} rate limited until {key.rate_limit_reset}")
            
            # Rotate to next key
            if self.rotation_enabled and len(self.keys) > 1:
                self.current_key_index = (self.current_key_index + 1) % len(self.keys)
                logging.info(f"Rotated to key index {self.current_key_index}")
            
            # Save asynchronously
            asyncio.create_task(self.save_keys())
    
    async def handle_invalid_key(self, key: APIKey):
        """Handle invalid key"""
        async with self._lock:
            key.status = KeyStatus.INVALID
            logging.error(f"Key {key.name} marked as invalid")
            
            # Rotate to next key
            if self.rotation_enabled and len(self.keys) > 1:
                self.current_key_index = (self.current_key_index + 1) % len(self.keys)
            
            # Save asynchronously
            asyncio.create_task(self.save_keys())
    
    async def get_key_stats(self) -> Dict[str, Any]:
        """Get statistics about all keys"""
        async with self._lock:
            stats = {
                'total_keys': len(self.keys),
                'active_keys': len([k for k in self.keys if k.status == KeyStatus.ACTIVE]),
                'rate_limited_keys': len([k for k in self.keys if k.status == KeyStatus.RATE_LIMITED]),
                'disabled_keys': len([k for k in self.keys if k.status == KeyStatus.DISABLED]),
                'invalid_keys': len([k for k in self.keys if k.status == KeyStatus.INVALID]),
                'current_key': self.keys[self.current_key_index].name if self.keys else None,
                'rotation_enabled': self.rotation_enabled,
                'keys': []
            }
            
            for key in self.keys:
                key_stats = {
                    'name': key.name,
                    'status': key.status.value,
                    'usage_count': key.usage_count,
                    'error_count': key.error_count,
                    'last_used': key.last_used.isoformat() if key.last_used else None,
                    'rate_limit_reset': key.rate_limit_reset.isoformat() if key.rate_limit_reset else None
                }
                stats['keys'].append(key_stats)
            
            return stats
    
    async def reset_key_errors(self, key_name: str) -> bool:
        """Reset error count for a specific key"""
        async with self._lock:
            for key in self.keys:
                if key.name == key_name:
                    key.error_count = 0
                    if key.status == KeyStatus.DISABLED:
                        key.status = KeyStatus.ACTIVE
                    await self.save_keys()
                    logging.info(f"Reset errors for key {key_name}")
                    return True
            return False
    
    async def disable_key(self, key_name: str) -> bool:
        """Manually disable a key"""
        async with self._lock:
            for key in self.keys:
                if key.name == key_name:
                    key.status = KeyStatus.DISABLED
                    await self.save_keys()
                    logging.info(f"Disabled key {key_name}")
                    return True
            return False
    
    async def enable_key(self, key_name: str) -> bool:
        """Manually enable a key"""
        async with self._lock:
            for key in self.keys:
                if key.name == key_name:
                    if key.status != KeyStatus.INVALID:
                        key.status = KeyStatus.ACTIVE
                        key.error_count = 0
                        await self.save_keys()
                        logging.info(f"Enabled key {key_name}")
                        return True
            return False
    
    async def rotate_key(self) -> Optional[APIKey]:
        """Manually rotate to the next available key"""
        async with self._lock:
            if len(self.keys) <= 1:
                return await self.get_current_key()
            
            original_index = self.current_key_index
            
            # Try to find next available key
            for _ in range(len(self.keys) - 1):
                self.current_key_index = (self.current_key_index + 1) % len(self.keys)
                key = self.keys[self.current_key_index]
                
                if await self._is_key_available(key):
                    logging.info(f"Rotated from key {original_index} to {self.current_key_index}")
                    await self.save_keys()
                    return key
            
            # No other available keys, stay with current
            self.current_key_index = original_index
            return await self.get_current_key()
    
    async def health_check(self):
        """Perform health check on all keys and update their status"""
        async with self._lock:
            now = datetime.now()
            updated = False
            
            for key in self.keys:
                # Reset rate limited keys if time has passed
                if (key.status == KeyStatus.RATE_LIMITED and 
                    key.rate_limit_reset and 
                    now >= key.rate_limit_reset):
                    key.status = KeyStatus.ACTIVE
                    key.rate_limit_reset = None
                    logging.info(f"Key {key.name} rate limit expired, reactivated")
                    updated = True
                
                # Reduce error count over time for disabled keys
                if (key.status == KeyStatus.DISABLED and 
                    key.last_used and 
                    now - key.last_used > timedelta(hours=1)):
                    key.error_count = max(0, key.error_count - 1)
                    if key.error_count < key.max_errors:
                        key.status = KeyStatus.ACTIVE
                        logging.info(f"Key {key.name} error count reduced, reactivated")
                        updated = True
            
            if updated:
                await self.save_keys()