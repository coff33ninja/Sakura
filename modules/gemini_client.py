import asyncio
import logging
from typing import Optional, AsyncGenerator, Dict, Any, List
from google import genai
import random
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
        
    async def initialize(self, system_prompt: str, resume_handle: Optional[str] = None, 
                         tools: Optional[List[Dict[str, Any]]] = None):
        """Initialize Gemini client and session with key rotation and tools"""
        try:
            # Store tools for function calling
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
        """Send audio data to Gemini with error handling"""
        if not self.is_connected or not self.session:
            return
            
        try:
            # Send as realtime input with proper format
            await self.session.send_realtime_input(
                audio={"data": audio_data, "mime_type": "audio/pcm"}
            )
        except Exception as e:
            logging.error(f"Error sending audio: {e}")
            await self._handle_api_error(e)
    
    async def send_text(self, text: str, end_of_turn: bool = True):
        """Send text input to Gemini to trigger a voice response"""
        if not self.is_connected or not self.session:
            return
            
        try:
            await self.session.send(input=text, end_of_turn=end_of_turn)
        except Exception as e:
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
                    
                    # Handle server content with model turn
                    if response.server_content and response.server_content.model_turn:
                        for part in response.server_content.model_turn.parts:
                            if part.inline_data and isinstance(part.inline_data.data, bytes):
                                response_data['audio'] = part.inline_data.data
                            if hasattr(part, 'text') and part.text:
                                response_data['text'] = part.text
                    
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
                    
                    # Handle function calls if implemented
                    if hasattr(response, 'tool_call') and response.tool_call:
                        response_data['function_calls'] = response.tool_call.function_calls
                    
                    if response_data:
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
            goodbye_msg = random.choice(get_goodbye_responses())
            try:
                # Use send() with text content for Gemini Live API
                await self.session.send(input=goodbye_msg, end_of_turn=True)
                # Give time for response
                await asyncio.sleep(2)
            except Exception as e:
                logging.error(f"Error sending goodbye: {e}")
    
    async def get_connection_status(self) -> Dict[str, Any]:
        """Get detailed connection and key status"""
        status = {
            'is_connected': self.is_connected,
            'current_key_name': self.current_key.name if self.current_key else None,
            'current_key_status': self.current_key.status.value if self.current_key else None,
            'session_active': self.session is not None,
            'client_initialized': self.client is not None,
            'voice_name': self.voice_name,
            'model': self.model
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
    
    async def _connect_with_retry(self, config, max_retries: int = 3) -> Optional[Any]:
        """Connect to Gemini with automatic key rotation on failure"""
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
                
                # Try next key if available
                if attempt < max_retries - 1:
                    next_key = await self.key_manager.rotate_key()
                    if next_key and next_key != self.current_key:
                        self.current_key = next_key
                        self.client = genai.Client(api_key=self.current_key.key)
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
            next_key = await self.key_manager.rotate_key()
            if next_key and next_key != self.current_key:
                await self._reconnect_with_new_key(next_key)
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