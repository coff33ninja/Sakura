import asyncio
import logging
from typing import Optional, AsyncGenerator, Dict, Any, List
from google import genai
import secrets
from datetime import datetime, timedelta
from .persona import get_goodbye_responses
from .api_key_manager import APIKeyManager, KeyStatus

class GeminiVoiceClient:
    """Handles Gemini Live API interactions with automatic key rotation"""
    
    def __init__(self, model: str, voice_name: str = "Aoede"):
        self.model = model
        self.voice_name = voice_name
        self.client = None
        self.session = None
        self._session_context = None
        self.is_connected = False
        self.key_manager = APIKeyManager()
        self.current_key = None
        self.tools = []  # Tool declarations for function calling
        self._system_prompt = ""  # Store for reconnection
        self._last_activity = datetime.now()
        self._connection_check_interval = timedelta(seconds=30)
        self._reconnect_lock = asyncio.Lock()
        self._consecutive_errors = 0
        self._max_consecutive_errors = 10
        # Backoff, rotation and circuit breaker controls
        self._circuit_open_until = None
        self._rotation_last = datetime.min
        self._rotation_cooldown_seconds = 30
        self._base_backoff_seconds = 1
        self._max_backoff_seconds = 30
        
    async def initialize(self, system_prompt: str, resume_handle: Optional[str] = None, 
                         tools: Optional[List[Dict[str, Any]]] = None):
        """Initialize Gemini client and session with key rotation and tools"""
        try:
            # Store for reconnection
            self._system_prompt = system_prompt
            self.tools = tools or []
            
            # Load API keys
            await self.key_manager.load_keys()
            
            # Get current key
            self.current_key = await self.key_manager.get_current_key()
            if not self.current_key:
                logging.error("No available API keys")
                return False
            
            # Configure Gemini with current key (new SDK uses Client directly)
            self.client = genai.Client(api_key=self.current_key.key)
            
            logging.info(f"Using API key: {self.current_key.name}")
            
            # Configure for voice interaction - use simple dict format per official docs
            config = {
                "response_modalities": ["AUDIO"],
                "system_instruction": system_prompt,
                "speech_config": {
                    "voice_config": {
                        "prebuilt_voice_config": {
                            "voice_name": self.voice_name
                        }
                    }
                }
            }
            
            # Add tools for function calling if provided
            if self.tools:
                config["tools"] = [{"function_declarations": self.tools}]
                logging.info(f"Registered {len(self.tools)} tools with Gemini")
            
            # Only add session resumption if we have a handle
            if resume_handle:
                config["session_resumption"] = {"handle": resume_handle}
            
            # Connect to live session
            self.session = await self._connect_with_retry(config)
            if not self.session:
                return False
            
            self.is_connected = True
            await self.key_manager.mark_key_used(self.current_key, success=True)
            logging.info(f"Gemini client initialized with voice: {self.voice_name}")
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to initialize Gemini client: {e}")
            if self.current_key:
                await self.key_manager.mark_key_used(self.current_key, success=False)
            return False
    
    async def send_audio(self, audio_data: bytes):
        """Send audio data to Gemini with error handling and connection monitoring"""
        if not self.is_connected or not self.session:
            # Try to reconnect if disconnected
            if await self._auto_reconnect():
                logging.info("🔄 Auto-reconnected, resuming audio stream")
            else:
                return
            
        try:
            # Send as realtime input with proper format
            await self.session.send_realtime_input(
                audio={"data": audio_data, "mime_type": "audio/pcm"}
            )
            self._update_activity()
            self._consecutive_errors = 0
        except Exception as e:
            self._consecutive_errors += 1
            logging.error(f"Error sending audio (attempt {self._consecutive_errors}): {e}")
            
            if self._consecutive_errors >= self._max_consecutive_errors:
                logging.warning("🔄 Too many consecutive errors, attempting reconnect...")
                await self._auto_reconnect()
            else:
                await self._handle_api_error(e)
    
    async def send_text(self, text: str, end_of_turn: bool = True):
        """Send text input to Gemini to trigger a voice response"""
        if not self.is_connected or not self.session:
            if not await self._auto_reconnect():
                return
            
        try:
            await self.session.send(input=text, end_of_turn=end_of_turn)
            self._update_activity()
            self._consecutive_errors = 0
        except Exception as e:
            self._consecutive_errors += 1
            logging.error(f"Error sending text: {e}")
            await self._handle_api_error(e)
    
    async def receive_responses(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Receive responses from Gemini with error handling"""
        if not self.is_connected or not self.session:
            return
            
        try:
            while True:
                turn = self.session.receive()
                async for response in turn:
                    response_data = {}
                    
                    # Handle interruption
                    if response.server_content and response.server_content.interrupted:
                        response_data['interrupted'] = True
                        yield response_data
                        continue
                    
                    # Handle function calls from multiple possible locations
                    function_calls_found = []
                    
                    # Check response.tool_call (old SDK format)
                    if hasattr(response, 'tool_call') and response.tool_call:
                        if hasattr(response.tool_call, 'function_calls'):
                            function_calls_found.extend(response.tool_call.function_calls)
                            logging.info(f"🔧 Function calls in tool_call: {len(response.tool_call.function_calls)}")
                    
                    # Check server_content.model_turn.parts for function calls (Live API format)
                    if response.server_content and response.server_content.model_turn:
                        for part in response.server_content.model_turn.parts:
                            # Extract audio
                            if part.inline_data and isinstance(part.inline_data.data, bytes):
                                response_data['audio'] = part.inline_data.data
                            # Extract text
                            if hasattr(part, 'text') and part.text:
                                response_data['text'] = part.text
                            # Extract function calls
                            if hasattr(part, 'function_call') and part.function_call:
                                function_calls_found.append(part.function_call)
                                logging.info(f"🔧 Function call in model_turn.parts: {part.function_call.name if hasattr(part.function_call, 'name') else 'unknown'}")
                    
                    # Add to response if any found
                    if function_calls_found:
                        response_data['function_calls'] = function_calls_found
                        logging.info(f"✨ Total function calls found: {len(function_calls_found)}")
                    
                    # Handle user transcription if available (input_transcription)
                    if hasattr(response, 'server_content') and response.server_content:
                        if hasattr(response.server_content, 'input_transcription') and response.server_content.input_transcription:
                            response_data['user_transcription'] = response.server_content.input_transcription
                        # Also check for turn_complete which may have transcription
                        if hasattr(response.server_content, 'turn_complete') and response.server_content.turn_complete:
                            response_data['turn_complete'] = True
                    
                    # Handle session resumption updates
                    if (hasattr(response, 'session_resumption_update') and 
                        response.session_resumption_update and
                        hasattr(response.session_resumption_update, 'resumable') and
                        response.session_resumption_update.resumable):
                        response_data['session_handle'] = response.session_resumption_update.new_handle
                    
                    if response_data:
                        self._update_activity()
                        self._consecutive_errors = 0
                        await self.key_manager.mark_key_used(self.current_key, success=True)
                        yield response_data
                    
        except Exception as e:
            logging.error(f"Error receiving responses: {e}")
            await self._handle_api_error(e)
    async def send_function_response(self, function_call_id: str, function_name: str, result: str):
        """Send function/tool call response back to Gemini Live API"""
        if not self.is_connected or not self.session:
            return
            
        try:
            # Live API uses send_tool_response with FunctionResponse format
            from google.genai import types
            
            function_response = types.FunctionResponse(
                id=function_call_id,
                name=function_name,
                response={"result": result}
            )
            
            await self.session.send_tool_response(function_responses=[function_response])
            logging.info(f"✅ Sent tool response for {function_name}")
        except Exception as e:
            logging.error(f"Error sending function response: {e}")
    
    async def send_goodbye(self):
        """Send a goodbye message via text input"""
        if self.is_connected and self.session:
            goodbye_responses = get_goodbye_responses()
            goodbye_msg = goodbye_responses[secrets.randbelow(len(goodbye_responses))]
            try:
                # Use send() with text content for Gemini Live API
                await self.session.send(input=goodbye_msg, end_of_turn=True)
                # Give time for response
                await asyncio.sleep(2)
            except Exception as e:
                logging.error(f"Error sending goodbye: {e}")
    
    async def get_connection_status(self) -> Dict[str, Any]:
        """Get detailed connection and key status"""
        time_since_activity = datetime.now() - self._last_activity
        
        status = {
            'is_connected': self.is_connected,
            'current_key_name': self.current_key.name if self.current_key else None,
            'current_key_status': self.current_key.status.value if self.current_key else None,
            'session_active': self.session is not None,
            'client_initialized': self.client is not None,
            'voice_name': self.voice_name,
            'model': self.model,
            # Health monitoring info
            'last_activity_seconds_ago': time_since_activity.seconds,
            'consecutive_errors': self._consecutive_errors,
            'connection_healthy': await self.check_connection_health()
        }
        
        # Get key manager stats if available
        if self.key_manager:
            key_stats = await self.key_manager.get_key_stats()
            status.update({
                'total_keys': key_stats['total_keys'],
                'active_keys': key_stats['active_keys'],
                'rate_limited_keys': key_stats['rate_limited_keys'],
                'disabled_keys': key_stats['disabled_keys'],
                'invalid_keys': key_stats['invalid_keys']
            })
        
        return status
    
    async def check_key_health(self) -> bool:
        """Check if current key is healthy and rotate if needed"""
        if not self.current_key:
            return False
        
        # Check if current key status is problematic
        if self.current_key.status in [KeyStatus.RATE_LIMITED, KeyStatus.INVALID, KeyStatus.DISABLED]:
            logging.warning(f"Current key {self.current_key.name} has status: {self.current_key.status.value}")
            
            # Try to rotate to a better key
            next_key = await self.key_manager.rotate_key()
            if next_key and next_key != self.current_key and next_key.status == KeyStatus.ACTIVE:
                await self._reconnect_with_new_key(next_key)
                return True
            
            return False
        
        return self.current_key.status == KeyStatus.ACTIVE
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
    
    def _update_activity(self):
        """Update last activity timestamp"""
        self._last_activity = datetime.now()
    
    async def check_connection_health(self) -> bool:
        """Check if connection is healthy based on activity and errors"""
        if not self.is_connected or not self.session:
            return False
        
        # Check if connection is stale (no activity for too long)
        time_since_activity = datetime.now() - self._last_activity
        if time_since_activity > self._connection_check_interval * 2:
            logging.warning(f"⚠️ Connection may be stale (no activity for {time_since_activity.seconds}s)")
            return False
        
        # Check consecutive errors
        if self._consecutive_errors >= self._max_consecutive_errors // 2:
            logging.warning(f"⚠️ High error rate: {self._consecutive_errors} consecutive errors")
            return False
        
        return True
    
    async def _auto_reconnect(self) -> bool:
        """Attempt to automatically reconnect if disconnected"""
        async with self._reconnect_lock:
            # Double-check connection state inside lock
            if self.is_connected and self.session:
                return True
            
            logging.info("🔄 Attempting auto-reconnect...")
            
            try:
                # Cleanup old session if exists
                if self._session_context:
                    try:
                        await self._session_context.__aexit__(None, None, None)
                    except Exception as e:
                        logging.debug(f"Session cleanup error: {e}")
                    self._session_context = None
                    self.session = None
                
                # Rebuild config
                config = {
                    "response_modalities": ["AUDIO"],
                    "system_instruction": self._system_prompt,
                    "speech_config": {
                        "voice_config": {
                            "prebuilt_voice_config": {
                                "voice_name": self.voice_name
                            }
                        }
                    }
                }
                
                if self.tools:
                    config["tools"] = [{"function_declarations": self.tools}]
                
                # Reconnect
                self.session = await self._connect_with_retry(config)
                if self.session:
                    self.is_connected = True
                    self._consecutive_errors = 0
                    self._update_activity()
                    logging.info("✅ Auto-reconnect successful")
                    return True
                else:
                    self.is_connected = False
                    logging.error("❌ Auto-reconnect failed")
                    return False
                    
            except Exception as e:
                logging.error(f"❌ Auto-reconnect error: {e}")
                self.is_connected = False
                return False
    
    async def _connect_with_retry(self, config, max_retries: int = 3) -> Optional[Any]:
        """Connect to Gemini with automatic key rotation on failure"""
        # Prevent reconnect attempts while circuit is open
        now = datetime.now()
        if self._circuit_open_until and now < self._circuit_open_until:
            logging.error(f"Circuit open until {self._circuit_open_until}, skipping connect")
            return None

        for attempt in range(max_retries):
            try:
                # live.connect returns an async context manager, enter it
                session = self.client.aio.live.connect(
                    model=self.model, 
                    config=config
                )
                # Enter the context manager to get the actual session
                self._session_context = session
                actual_session = await session.__aenter__()
                return actual_session
                
            except Exception as e:
                error_msg = str(e).lower()
                logging.error(f"Connection error: {e}")
                
                # Detect rate limiting / quota exhaustion
                is_rate_limited = any(term in error_msg for term in [
                    "rate limit", "quota", "resource_exhausted", "exhausted",
                    "429", "too many requests", "exceeded"
                ])
                
                # Detect invalid/unauthorized keys
                is_invalid_key = any(term in error_msg for term in [
                    "unauthorized", "api_key", "permission denied", 
                    "403", "401", "invalid api key"
                ])
                
                # Detect temporary/retriable errors (not key issues)
                is_temporary = any(term in error_msg for term in [
                    "timeout", "connection", "network", "unavailable",
                    "503", "502", "500", "internal"
                ])
                
                if is_rate_limited:
                    logging.warning(f"🚫 Rate limit/quota hit on key {self.current_key.name}")
                    await self.key_manager.handle_rate_limit(self.current_key)
                elif is_invalid_key:
                    logging.error(f"❌ Invalid/unauthorized key {self.current_key.name}")
                    await self.key_manager.handle_invalid_key(self.current_key)
                elif is_temporary:
                    logging.warning(f"⚠️ Temporary error on key {self.current_key.name}, will retry")
                    await self.key_manager.mark_key_used(self.current_key, success=False)
                else:
                    # Unknown error - don't mark key as bad, might be config issue
                    logging.error(f"❓ Unknown error with key {self.current_key.name}: {e}")
                    await self.key_manager.mark_key_used(self.current_key, success=False)
                
                # Backoff before retrying to avoid hot-looping; add jitter
                backoff = min(self._base_backoff_seconds * (2 ** attempt), self._max_backoff_seconds)
                jitter = (secrets.randbelow(int(backoff * 50)) / 100.0)
                await asyncio.sleep(backoff + jitter)

                # Try next key if available (respect rotation cooldown)
                if attempt < max_retries - 1:
                    now = datetime.now()
                    if (now - self._rotation_last).total_seconds() < self._rotation_cooldown_seconds:
                        logging.info("Rotation cooldown active, will retry same key after backoff")
                    else:
                        next_key = await self.key_manager.rotate_key()
                        if next_key and next_key != self.current_key:
                            self.current_key = next_key
                            self.client = genai.Client(api_key=self.current_key.key)
                            self._rotation_last = datetime.now()
                            logging.info(f"Retrying with key: {self.current_key.name}")
                            continue
                
                # If this was the last attempt or no other keys available
                if attempt == max_retries - 1:
                    logging.error("All connection attempts failed")
                    return None
        
        return None
    
    async def _handle_api_error(self, error: Exception):
        """Handle API errors and rotate keys if necessary"""
        error_msg = str(error).lower()
        
        # Detect rate limiting / quota exhaustion
        is_rate_limited = any(term in error_msg for term in [
            "rate limit", "quota", "resource_exhausted", "exhausted",
            "429", "too many requests", "exceeded"
        ])
        
        # Detect invalid/unauthorized keys
        is_invalid_key = any(term in error_msg for term in [
            "unauthorized", "api_key", "permission denied", 
            "403", "401", "invalid api key"
        ])
        
        if is_rate_limited:
            logging.warning(f"🚫 Rate limit during operation on key {self.current_key.name}")
            await self.key_manager.handle_rate_limit(self.current_key)
            # Avoid rapid rotations: respect cooldown and apply backoff
            now = datetime.now()
            if (now - self._rotation_last).total_seconds() < self._rotation_cooldown_seconds:
                logging.warning("Rotation cooldown active; delaying rotation and backing off")
                await asyncio.sleep(self._rotation_cooldown_seconds)
            else:
                next_key = await self.key_manager.rotate_key()
                self._rotation_last = datetime.now()
                if next_key and next_key != self.current_key:
                    await self._reconnect_with_new_key(next_key)
                    return
            # If we didn't rotate, increase backoff and possibly open circuit
            self._consecutive_errors += 1
            if self._consecutive_errors >= self._max_consecutive_errors:
                self._circuit_open_until = datetime.now() + timedelta(seconds=max(self._rotation_cooldown_seconds, 60))
                logging.error(f"Circuit opened until {self._circuit_open_until} due to repeated errors")
        elif is_invalid_key:
            logging.error(f"❌ Invalid key during operation: {self.current_key.name}")
            await self.key_manager.handle_invalid_key(self.current_key)
            next_key = await self.key_manager.rotate_key()
            if next_key and next_key != self.current_key:
                await self._reconnect_with_new_key(next_key)
        else:
            await self.key_manager.mark_key_used(self.current_key, success=False)
    
    async def _reconnect_with_new_key(self, new_key):
        """Reconnect with a new API key"""
        try:
            self.current_key = new_key
            self.client = genai.Client(api_key=self.current_key.key)
            logging.info(f"Reconnected with new key: {self.current_key.name}")
        except Exception as e:
            logging.error(f"Failed to reconnect with new key: {e}")    

    async def cleanup(self):
        """Clean up Gemini client resources"""
        try:
            if self._session_context:
                await self._session_context.__aexit__(None, None, None)
            self.is_connected = False
            logging.info("Gemini client cleanup completed")
        except Exception as e:
            logging.error(f"Error during Gemini cleanup: {e}")
    
    async def force_key_rotation(self) -> bool:
        """Force rotation to next available key"""
        if not self.key_manager:
            return False
        
        current_name = self.current_key.name if self.current_key else "None"
        next_key = await self.key_manager.rotate_key()
        
        if next_key and next_key != self.current_key:
            success = await self._reconnect_with_new_key(next_key)
            if success:
                logging.info(f"Forced rotation from {current_name} to {next_key.name}")
                return True
        
        logging.warning("Force rotation failed - no better keys available")
        return False
    
    async def get_key_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for all keys"""
        if not self.key_manager:
            return {}
        
        stats = await self.key_manager.get_key_stats()
        
        # Add current session info
        stats['current_session'] = {
            'connected': self.is_connected,
            'active_key': self.current_key.name if self.current_key else None,
            'active_key_status': self.current_key.status.value if self.current_key else None,
            'voice_model': self.voice_name,
            'gemini_model': self.model
        }
        
        return stats