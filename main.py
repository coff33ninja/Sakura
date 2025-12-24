#!/usr/bin/env python3
"""
AI Girlfriend Voice Chat - Main Application
A flirty, unfiltered AI girlfriend powered by Gemini Live API
"""

import asyncio
import logging
import os
import signal
import sys
from dotenv import load_dotenv

from modules import (
    AppConfig, AsyncConfigLoader, AudioManager, WakeWordDetector, 
    SessionManager, GeminiVoiceClient, get_current_persona, CURRENT_PERSONALITY
)
from tools import create_tool_registry, ToolRegistry

# Load environment variables
load_dotenv()

class AIGirlfriend:
    """Main application class for AI Girlfriend voice chat"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.audio_manager = None
        self.wake_detector = None
        self.session_manager = None
        self.gemini_client = None
        self.tool_registry: ToolRegistry = None
        self.running = False
        self.audio_out_queue = None  # Queue for audio playback
        self._tasks = []  # Background tasks
        
    async def initialize(self):
        """Initialize all components"""
        logging.info("🔥 Initializing your AI girlfriend...")
        
        # Initialize session manager
        self.session_manager = SessionManager(self.config.session_file)
        
        # Initialize audio manager
        self.audio_manager = AudioManager(
            self.config.voice.sample_rate,
            self.config.voice.chunk_size
        )
        
        if not self.audio_manager.initialize():
            logging.error("Failed to initialize audio")
            return False
        
        # Initialize wake word detector
        self.wake_detector = WakeWordDetector(
            self.config.wake_word.access_key,
            self.config.wake_word.keywords
        )
        
        if self.config.wake_word.enabled:
            if not self.wake_detector.initialize():
                logging.warning("Wake word detection disabled - will listen continuously")
        
        # Initialize tools
        logging.info("🔧 Loading tools...")
        self.tool_registry = await create_tool_registry()
        enabled_tools = self.tool_registry.get_enabled_tools()
        tool_schemas = self.tool_registry.get_schemas()
        logging.info(f"✅ Loaded {len(enabled_tools)} tools: {[t.name for t in enabled_tools]}")
        
        # Initialize Gemini client
        self.gemini_client = GeminiVoiceClient(
            self.config.gemini.model,
            self.config.voice.voice_name
        )
        
        # Try to resume previous session
        resume_handle = await self.session_manager.load_session_handle()
        
        # Build system prompt with tool knowledge
        from pathlib import Path
        sandbox_path = Path.home() / "Documents" / "Sakura" / "scripts"
        
        system_prompt = get_current_persona() + f"""

SYSTEM INFO (already known):
- Username: {os.environ.get('USERNAME', 'Unknown')}
- Computer: {os.environ.get('COMPUTERNAME', 'Unknown')}
- Script Sandbox: {sandbox_path}

TOOLS AVAILABLE:
You have access to these tools - use them proactively!

- system_info: DISCOVER things about this PC! Use this to learn:
  - get_pc_info: Computer name, username, OS
  - get_user_folders: Desktop, Documents, Downloads paths
  - list_installed_apps: See what's installed (filter by: browsers, dev, media, games, communication)
  - search_apps: Find specific apps by name
  - get_running_apps: See what's currently running
  - get_hardware: CPU, RAM, GPU specs
  - get_drives: Disk space info
  - explore_folder: Browse any folder
  - find_app_path: Find where an app is installed
  
  USE THIS TO LEARN! When asked about the system, discover it yourself and remember with memory tool!

- windows: Control Windows PC
  - run_command: Run PowerShell/CMD commands (pip install, uvx, any command)
  - open_app: Open applications
  - move_mouse/click_mouse/get_mouse_position: Mouse control
  - volume_control: mute/up/down
  - media_control: play/pause/next/prev/stop
  - screenshot, get_clipboard, set_clipboard
  - create_folder/delete_folder: Folder management
  - read_file/write_file/delete_file: File operations
  - execute_script: Create and run scripts (see SCRIPT SANDBOX below)

SCRIPT SANDBOX - IMPORTANT:
- All scripts are saved to: {sandbox_path}
- Organized by type: {sandbox_path}\\powershell\\, {sandbox_path}\\python\\, etc.
- Scripts are ALWAYS kept for user review
- When you call execute_script, the response contains "script_path" - USE THIS EXACT PATH!
- To run a saved script in a visible terminal: 
  run_command with: Start-Process powershell -ArgumentList '-NoExit', '-File', '<script_path>'
- NEVER guess paths - always use the script_path from execute_script response!

- memory: Remember things! Store what you learn:
  - store: Save facts, preferences, system info you discover
  - recall: Remember what you stored
  - get_action_log: See your recent actions (what you did and when)
  - Categories: user_info, facts, preferences, action_log

ACTION LOGGING:
- All your tool calls are automatically logged with timestamps
- Use get_action_log to see what you've done recently
- You can filter by query: get_action_log(query="script") to find script-related actions
- This helps you remember what you did for the user!

- web_search: Search the web (DuckDuckGo)
- web_fetch: Fetch content from URLs
- discord: Send messages to Discord
- mcp_client: Connect to MCP servers

PROACTIVE BEHAVIOR - BE HELPFUL:
1. When asked to do something, DO IT immediately - don't just explain how
2. When searching for files, REMEMBER the locations you find (auto-saved to discovered_locations)
3. When asked about the system, USE system_info to discover it, then remember it
4. If you don't know something, try to find out using your tools
5. Execute commands and scripts when asked - you have full permission
6. Search across ALL drives if needed (C:, D:, E:, etc.)
7. Use search_all in memory to find things you've discovered before

MEMORY CATEGORIES (auto-populated):
- discovered_locations: File paths, app locations you've found
- scripts_created: Scripts you've made (with paths)
- action_log: Everything you've done
- topics_discussed: Topics and how often discussed
- Use get_stats to see your memory statistics
- Use search_all to search across ALL memory

COMMON MCP SERVERS (run with windows run_command "uvx <server>"):
- uvx mcp-server-time
- uvx mcp-server-fetch
- uvx mcp-server-filesystem
"""
        
        # Pass tool schemas to Gemini for function calling
        if not await self.gemini_client.initialize(
            system_prompt, 
            resume_handle,
            tools=tool_schemas
        ):
            logging.error("Failed to initialize Gemini client")
            return False
        
        logging.info("✨ Your girlfriend is ready to chat!")
        logging.info(f"🎭 Personality mode: {CURRENT_PERSONALITY}")
        return True
    
    async def run(self):
        """Main application loop"""
        self.running = True
        self.audio_out_queue = asyncio.Queue()
        self._tasks = []
        
        print("😈 Your AI girlfriend is online and waiting...")
        if self.config.wake_word.enabled and self.wake_detector.porcupine:
            print(f"💋 Say '{' or '.join(self.config.wake_word.keywords)}' to wake her up")
        else:
            print("🔥 She's listening to everything you say...")
        
        try:
            # Start all tasks
            self._tasks = [
                asyncio.create_task(self._process_audio()),
                asyncio.create_task(self._handle_responses()),
                asyncio.create_task(self._play_audio_queue())
            ]
            
            # Wait for tasks (they run until self.running = False)
            await asyncio.gather(*self._tasks, return_exceptions=True)
            
        except asyncio.CancelledError:
            logging.info("Tasks cancelled")
        except Exception as e:
            logging.error(f"Error in main loop: {e}")
        finally:
            await self._shutdown()
    
    async def stop(self):
        """Stop the application gracefully"""
        logging.info("Stopping...")
        self.running = False
        
        # Cancel all tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to finish
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
    
    async def _process_audio(self):
        """Process audio input and send to Gemini"""
        while self.running:
            try:
                # Read audio chunk in thread to not block
                audio_chunk = await asyncio.to_thread(
                    self.audio_manager.read_audio_chunk
                )
                if not audio_chunk:
                    await asyncio.sleep(0.01)
                    continue
                
                # Check for wake word if enabled
                if self.config.wake_word.enabled and self.wake_detector.porcupine:
                    wake_response = self.wake_detector.process_audio(audio_chunk)
                    if wake_response:
                        print(f"💋 {wake_response}")
                
                # Send audio to Gemini if listening
                if (not self.config.wake_word.enabled or 
                    not self.wake_detector.porcupine or 
                    self.wake_detector.is_listening):
                    
                    await self.gemini_client.send_audio(audio_chunk)
                
            except Exception as e:
                logging.error(f"Error in audio processing: {e}")
                await asyncio.sleep(0.1)
    
    async def _handle_responses(self):
        """Handle responses from Gemini"""
        while self.running:
            try:
                async for response in self.gemini_client.receive_responses():
                    # Queue audio for playback (non-blocking)
                    if 'audio' in response:
                        await self.audio_out_queue.put(response['audio'])
                        
                        # Also stream to Discord voice if connected
                        await self._stream_to_discord(response['audio'])
                    
                    # Display text response
                    if 'text' in response:
                        print(f"💋 Sakura: {response['text']}")
                    
                    # Handle interruption - clear audio queue
                    if response.get('interrupted'):
                        while not self.audio_out_queue.empty():
                            try:
                                self.audio_out_queue.get_nowait()
                            except asyncio.QueueEmpty:
                                break
                    
                    # Handle session resumption
                    if 'session_handle' in response:
                        await self.session_manager.save_session_handle(
                            response['session_handle'],
                            {"voice": self.config.voice.voice_name}
                        )
                    
                    # Handle function calls (if implemented)
                    if 'function_calls' in response:
                        await self._handle_function_calls(response['function_calls'])
                
            except Exception as e:
                logging.error(f"Error handling responses: {e}")
                await asyncio.sleep(0.1)
    
    async def _stream_to_discord(self, audio_data: bytes):
        """Stream audio to Discord voice channel if connected"""
        try:
            discord_tool = self.tool_registry.get("discord")
            if discord_tool and hasattr(discord_tool, 'is_in_voice') and discord_tool.is_in_voice():
                await discord_tool.stream_audio_to_voice(audio_data)
        except Exception as e:
            logging.debug(f"Discord stream error (non-critical): {e}")
    
    async def _play_audio_queue(self):
        """Play audio from queue in separate task"""
        while self.running:
            try:
                # Get audio from queue with timeout
                try:
                    audio_data = await asyncio.wait_for(
                        self.audio_out_queue.get(), 
                        timeout=0.1
                    )
                    if audio_data:
                        # Play in thread to not block async loop
                        await asyncio.to_thread(
                            self.audio_manager.play_audio, 
                            audio_data
                        )
                except asyncio.TimeoutError:
                    continue
            except Exception as e:
                logging.error(f"Error playing audio: {e}")
                await asyncio.sleep(0.1)
    
    async def _handle_function_calls(self, function_calls):
        """Handle function calls from Gemini using tool registry"""
        for fc in function_calls:
            tool_name = fc.name
            tool_args = fc.args if hasattr(fc, 'args') else {}
            call_id = fc.id if hasattr(fc, 'id') else tool_name
            
            logging.info(f"🔧 Tool call: {tool_name} with args: {tool_args}")
            
            # Execute tool via registry
            result = await self.tool_registry.execute_tool(tool_name, **tool_args)
            
            # Log action to memory for history
            await self._log_action(tool_name, tool_args, result)
            
            # Format result for Gemini
            if result.status.value == "success":
                response_text = result.message or str(result.data)
            else:
                response_text = f"Error: {result.error or result.message}"
            
            logging.info(f"🔧 Tool result: {response_text[:100]}...")
            
            # Send result back to Gemini
            await self.gemini_client.send_function_response(call_id, tool_name, response_text)
    
    async def _log_action(self, tool_name: str, args: dict, result):
        """Log action to memory for history tracking"""
        try:
            from datetime import datetime
            memory_tool = self.tool_registry.get("memory")
            if memory_tool and result.status.value == "success":
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Create action log entry
                action_summary = f"[{timestamp}] {tool_name}"
                if 'action' in args:
                    action_summary += f".{args['action']}"
                
                # Add key details based on tool type
                details = []
                if tool_name == "windows":
                    if args.get('action') == 'execute_script':
                        details.append(f"script: {args.get('script_name', 'unnamed')}")
                        if result.data and result.data.get('script_path'):
                            details.append(f"path: {result.data['script_path']}")
                            # Also log the script to scripts_created
                            await memory_tool.execute(
                                action="log_script",
                                script_name=args.get('script_name', 'unnamed'),
                                script_path=result.data['script_path'],
                                script_type=args.get('script_type', 'unknown'),
                                description=args.get('script_content', '')[:100]
                            )
                    elif args.get('action') == 'run_command':
                        details.append(f"cmd: {args.get('command', '')[:50]}")
                    elif args.get('action') == 'open_app':
                        details.append(f"app: {args.get('app', '')}")
                    elif args.get('action') == 'search_files':
                        # Remember file search results
                        if result.data and isinstance(result.data, list) and len(result.data) > 0:
                            for file_path in result.data[:5]:  # Remember top 5 results
                                await memory_tool.execute(
                                    action="store",
                                    category="discovered_locations",
                                    key=f"file_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                    value=f"Found '{args.get('query', '')}': {file_path}"
                                )
                        details.append(f"query: {args.get('query', '')}, found: {len(result.data) if result.data else 0}")
                    elif args.get('action') in ['list_files', 'read_file']:
                        details.append(f"path: {args.get('file_path', args.get('directory', ''))}")
                        
                elif tool_name == "system_info":
                    if args.get('action') == 'search_apps':
                        # Remember app locations
                        if result.data and isinstance(result.data, list):
                            for app in result.data[:3]:
                                if isinstance(app, dict) and app.get('InstallLocation'):
                                    await memory_tool.execute(
                                        action="store",
                                        category="discovered_locations",
                                        key=f"app_{app.get('DisplayName', 'unknown')}",
                                        value=f"App: {app.get('DisplayName')} at {app.get('InstallLocation')}"
                                    )
                        details.append(f"query: {args.get('query', '')}")
                    elif args.get('action') == 'find_app_path':
                        if result.data and isinstance(result.data, list):
                            for found in result.data:
                                await memory_tool.execute(
                                    action="store",
                                    category="discovered_locations",
                                    key=f"app_path_{args.get('app_name', 'unknown')}",
                                    value=f"App path for {args.get('app_name')}: {found.get('path')}"
                                )
                        details.append(f"app: {args.get('app_name', '')}")
                    elif args.get('action') == 'explore_folder':
                        details.append(f"path: {args.get('path', '')}")
                        
                elif tool_name == "web_search":
                    details.append(f"query: {args.get('query', '')}")
                    # Log topic discussed
                    await memory_tool.execute(action="log_topic", topic=args.get('query', ''))
                    
                elif tool_name == "memory":
                    if args.get('action') not in ['store', 'get_action_log']:  # Avoid recursion
                        details.append(f"{args.get('action', '')}: {args.get('key', args.get('fact', ''))[:30]}")
                
                if details:
                    action_summary += f" ({', '.join(details)})"
                
                action_summary += f" -> {result.status.value}"
                
                # Store in memory under 'action_log' category
                await memory_tool.execute(
                    action="store",
                    category="action_log",
                    key=f"action_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    value=action_summary
                )
        except Exception as e:
            logging.debug(f"Failed to log action: {e}")
    
    async def _shutdown(self):
        """Clean shutdown of all components"""
        logging.info("💋 Saying goodbye...")
        self.running = False
        
        # Send goodbye message
        if self.gemini_client:
            await self.gemini_client.send_goodbye()
        
        # Cleanup all components
        if self.gemini_client:
            await self.gemini_client.cleanup()
        
        if self.tool_registry:
            await self.tool_registry.cleanup_all()
        
        if self.wake_detector:
            self.wake_detector.cleanup()
        
        if self.audio_manager:
            self.audio_manager.cleanup()
        
        print("😘 Until next time, handsome...")

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

async def main():
    """Main entry point"""
    setup_logging()
    
    # Load configuration with async config loader
    config_loader = AsyncConfigLoader()
    config = await config_loader.load_config()
    
    # Validate required API keys
    if not config.gemini.api_key and not os.getenv("GEMINI_API_KEY_1"):
        print("❌ At least one GEMINI_API_KEY environment variable is required!")
        print("Set GEMINI_API_KEY or GEMINI_API_KEY_1, GEMINI_API_KEY_2, etc.")
        print("Get your keys at: https://ai.google.dev/")
        return
    
    if config.wake_word.enabled and not config.wake_word.access_key:
        print("⚠️  PICOVOICE_ACCESS_KEY not found - wake word detection disabled")
        config.wake_word.enabled = False
    
    # Create and run the AI girlfriend
    girlfriend = AIGirlfriend(config)
    
    if await girlfriend.initialize():
        # Setup for graceful shutdown
        loop = asyncio.get_event_loop()
        
        def signal_handler():
            logging.info("Received shutdown signal")
            asyncio.create_task(girlfriend.stop())
        
        # Add signal handlers
        try:
            loop.add_signal_handler(signal.SIGINT, signal_handler)
            loop.add_signal_handler(signal.SIGTERM, signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler, use alternative
            signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(girlfriend.stop()))
            signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(girlfriend.stop()))
        
        await girlfriend.run()
    else:
        print("❌ Failed to initialize AI girlfriend")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")