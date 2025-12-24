import os
import json
import logging
import asyncio
import aiofiles
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

class SessionManager:
    """Manages session persistence and resumption with async file I/O"""
    
    def __init__(self, session_file: str = "gf_session.txt"):
        self.session_file = session_file
        self.current_handle = None
        self.session_data = {}
        self._lock = asyncio.Lock()
        
    async def save_session_handle(self, handle: str, metadata: Optional[Dict[str, Any]] = None):
        """Save session handle for resumption"""
        async with self._lock:
            try:
                session_data = {
                    "handle": handle,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": metadata or {}
                }
                
                async with aiofiles.open(self.session_file, 'w') as f:
                    await f.write(json.dumps(session_data, indent=2))
                    
                self.current_handle = handle
                self.session_data = session_data
                logging.info(f"Session handle saved: {handle[:20]}...")
                
            except Exception as e:
                logging.error(f"Failed to save session handle: {e}")
    
    async def load_session_handle(self) -> Optional[str]:
        """Load previous session handle if still valid"""
        async with self._lock:
            try:
                if not os.path.exists(self.session_file):
                    return None
                    
                async with aiofiles.open(self.session_file, 'r') as f:
                    content = await f.read()
                    session_data = json.loads(content)
                
                # Check if session is still valid (within 2 hours)
                timestamp = datetime.fromisoformat(session_data["timestamp"])
                if datetime.now() - timestamp > timedelta(hours=2):
                    logging.info("Previous session expired")
                    await self.clear_session()
                    return None
                
                handle = session_data.get("handle")
                if handle:
                    self.current_handle = handle
                    self.session_data = session_data
                    logging.info(f"Loaded previous session: {handle[:20]}...")
                    return handle
                    
            except Exception as e:
                logging.error(f"Failed to load session handle: {e}")
                
            return None
    
    async def clear_session(self):
        """Clear current session data"""
        async with self._lock:
            try:
                if os.path.exists(self.session_file):
                    # Use asyncio to run os.remove in thread pool
                    await asyncio.get_event_loop().run_in_executor(None, os.remove, self.session_file)
                self.current_handle = None
                self.session_data = {}
                logging.info("Session data cleared")
            except Exception as e:
                logging.error(f"Failed to clear session: {e}")
    
    def get_session_metadata(self) -> Dict[str, Any]:
        """Get metadata from current session"""
        return self.session_data.get("metadata", {})
    
    async def update_session_metadata(self, metadata: Dict[str, Any]):
        """Update session metadata"""
        async with self._lock:
            if self.session_data:
                self.session_data["metadata"].update(metadata)
                try:
                    async with aiofiles.open(self.session_file, 'w') as f:
                        await f.write(json.dumps(self.session_data, indent=2))
                except Exception as e:
                    logging.error(f"Failed to update session metadata: {e}")
    
    def is_session_active(self) -> bool:
        """Check if there's an active session"""
        return self.current_handle is not None
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        async with self._lock:
            stats = {
                'has_active_session': self.is_session_active(),
                'current_handle': self.current_handle[:20] + "..." if self.current_handle else None,
                'session_age': None,
                'metadata': self.get_session_metadata()
            }
            
            if self.session_data and 'timestamp' in self.session_data:
                timestamp = datetime.fromisoformat(self.session_data['timestamp'])
                age = datetime.now() - timestamp
                stats['session_age'] = str(age)
            
            return stats