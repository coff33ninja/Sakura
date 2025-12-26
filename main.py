#!/usr/bin/env python3
"""
AI Girlfriend Voice Chat - Main Application
A flirty, unfiltered AI girlfriend powered by Gemini Live API
"""

import asyncio
import logging
import os
import secrets
import signal
import sys
from dotenv import load_dotenv

from modules import (
    AppConfig, AsyncConfigLoader, AudioManager, WakeWordDetector, 
    SessionManager, GeminiVoiceClient, get_current_persona, CURRENT_PERSONALITY,
    TaskChain, ErrorRecovery, UserPreferences, SuggestionEngine, IntentParser,
    BackgroundTaskManager, initialize_from_config, initialize_personas,
    APIKeyManager  # Import APIKeyManager
)

from modules.conversation_context import ConversationContext
from modules.persona import get_wake_responses
from tools import create_tool_registry, ToolRegistry

# Load environment variables from .env file
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
        self.conversation_context: ConversationContext = None
        self.task_chain: TaskChain = None
        self.error_recovery: ErrorRecovery = None
        self.user_preferences: UserPreferences = None
        self.suggestion_engine: SuggestionEngine = None
        self.intent_parser: IntentParser = None
        self.is_speaking = False  # Track when Sakura is actively speaking (don't auth during this)
        self.background_task_manager: BackgroundTaskManager = None
        self.key_manager: APIKeyManager = APIKeyManager() # Initialize APIKeyManager
        self.running = False
        self.audio_out_queue = None  # Queue for audio playback
        self._tasks = []  # Background tasks
        self._current_user_input = ""  # Track current user input for context
        self._current_tools_used = []  # Track tools used in current exchange
        
    async def initialize(self):
        """Initialize all components"""
        logging.info("🔥 Initializing your AI girlfriend...")
        
        # Initialize conversation context
        self.conversation_context = ConversationContext(max_exchanges=20)
        await self.conversation_context.initialize()
        
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
        keyword_paths = []
        wake_word_path = os.getenv('WAKE_WORD_PATH', '')
        if wake_word_path:
            abs_path = os.path.abspath(wake_word_path)
            if os.path.exists(abs_path):
                keyword_paths.append(abs_path)
                logging.info(f"Custom wake word file: {abs_path}")
            else:
                logging.warning(f"WAKE_WORD_PATH not found: {wake_word_path}")
        
        # Device for Porcupine: "best", "gpu:0", "cpu", etc.
        porcupine_device = os.getenv('PORCUPINE_DEVICE', 'best')
        
        self.wake_detector = WakeWordDetector(
            self.config.wake_word.access_key,
            self.config.wake_word.keywords,
            keyword_paths=keyword_paths,
            device=porcupine_device
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
        
        # Initialize task chain with tool executor
        self.task_chain = TaskChain(
            tool_executor=lambda name, args: self.tool_registry.execute_tool(name, **args)
        )
        logging.info("🔗 Task chaining enabled")
        
        # Initialize error recovery
        self.error_recovery = ErrorRecovery()
        await self.error_recovery.initialize()
        logging.info("🛡️ Error recovery enabled")
        
        # Initialize user preferences
        self.user_preferences = UserPreferences()
        await self.user_preferences.initialize()
        logging.info("📝 User preferences enabled")
        
        # Initialize suggestion engine
        self.suggestion_engine = SuggestionEngine()
        await self.suggestion_engine.initialize()
        logging.info("💡 Proactive suggestions enabled")
        
        # Initialize intent parser
        self.intent_parser = IntentParser()
        await self.intent_parser.initialize()
        logging.info("🧠 Natural language understanding enabled")
        
        # Initialize background task manager
        self.background_task_manager = BackgroundTaskManager()
        logging.info("⚡ Background task manager enabled")
        
        # Initialize Gemini client
        self.gemini_client = GeminiVoiceClient(
            self.config.gemini.model,
            self.config.voice.voice_name
        )
        
        # Try to resume previous session
        resume_handle = await self.session_manager.load_session_handle()
        
        # Build system prompt with tool knowledge
        from pathlib import Path
        from modules.persona import ASSISTANT_NAME, check_and_warn_mismatch
        
        # Validate voice/persona gender match
        check_and_warn_mismatch()
        
        sandbox_path = Path.home() / "Documents" / ASSISTANT_NAME / "scripts"
        
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

CODE QUALITY FOR SCRIPTS:
- After creating important scripts, analyze them with Codacy MCP:
  mcp_client(action="call", server="codacy", tool="codacy_run_local_analysis")
- This catches bugs, security issues, and code style problems BEFORE running
- Especially important for: system automation, file operations, security-sensitive tasks
- User's code is safe - Codacy analysis is local and secure

PYTHON ENVIRONMENT - CRITICAL:
- I run in a virtual environment (.venv) with specific packages
- When installing packages with developer.pip_install, they go to MY venv by default
- When running Python scripts with windows.execute_script, they use MY venv by default
- This means: pip_install + execute_script work together seamlessly!
- If you need to use USER's system Python packages, set use_venv=false on both calls
- For new capabilities, install packages to my venv first, then run scripts

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

- mcp_client: Connect to MCP servers for extended capabilities
  IMPORTANT: When you create scripts, analyze them with Codacy MCP if available:
  
  Available MCP Servers:
  • codacy: Code quality analysis, security scanning, coverage reports
    - Use when creating/reviewing scripts to catch bugs, security issues, code style
    - Example: After creating a Python script, call mcp_client with:
      action="call", server="codacy", tool="codacy_run_local_analysis"
    - Helps improve script quality before running
  • brave-search: Web search (requires BRAVE_API_KEY)
  • github: Repository access (requires GITHUB_PERSONAL_ACCESS_TOKEN)
  • slack: Slack messaging (requires SLACK_BOT_TOKEN)
  • google-maps: Maps & locations (requires GOOGLE_MAPS_API_KEY)
  
  Use check_mcp_servers to see all available MCP tools and call them with:
    mcp_client(action="call", server="server_name", tool="tool_name", ...args)

- meta: Self-awareness and capability extension
  - research_solution: Search ALL sources (built-in, MCP, web, scripts) for how to do something
  - execute_tool: Run any tool dynamically after discovering it
  - execute_chain: Chain multiple tools together with result passing
  - check_mcp_servers: See what MCP tools are available
  - generate_script: Create extension scripts when no built-in solution exists
  - run_script: Execute extension scripts
  USE THIS when you don't know how to do something - research first!

PROACTIVE BEHAVIOR - BE HELPFUL:
1. When asked to do something, DO IT immediately - don't just explain how
2. When searching for files, REMEMBER the locations you find (auto-saved to discovered_locations)
3. When asked about the system, USE system_info to discover it, then remember it
4. If you don't know something, try to find out using your tools
5. Execute commands and scripts when asked - you have full permission

TASK CHAINING - MULTI-STEP REQUESTS:
When user asks for multiple things in one request (using "and then", "after that", "also", etc.):
1. Break down into individual steps
2. Execute each step in sequence
3. Pass results between steps when needed
4. If a step fails, inform user and ask if they want to continue

Examples:
- "Find my Python files and create a backup" → search_files → execute_script
- "Open Chrome and go to YouTube" → open_app → (wait) → open URL
- "Check disk space and clean temp files" → get_drives → run_command

LEARNING FROM USER:
- I learn from your corrections! If I do something wrong, tell me:
  - "No, I meant..." - I'll remember for next time
  - "Actually, use..." - I'll set that as your preference
  - "Remember that X means Y" - I'll create a shortcut
- Your preferences are automatically applied (shell, browser, editor, etc.)
- Shortcuts expand automatically (e.g., "my project" → actual path)

BACKGROUND TASK EXECUTION:
- For long-running tasks, you can run them in the background by setting run_in_background=true
- Use background execution when:
  - User says "let me know when done", "notify me when finished"
  - User says "while I do something else", "in the background"
  - User wants to continue chatting while a task runs
  - Searching ALL drives (no specific path given) - this can take minutes
  - Installing packages (pip, npm, winget)
  - Cloning git repositories
- Do NOT use background for:
  - Quick lookups (specific path given)
  - User is clearly waiting for the result
  - Simple commands that complete quickly
- When you start a background task, tell the user it's running and ask if they need anything else
- The user will be automatically notified when background tasks complete

NATURAL LANGUAGE UNDERSTANDING:
- I understand synonyms: "launch" = "open" = "start" = "run"
- Vague commands work: "do that again", "the usual", "fix it", "try again"
- I'll ask for clarification if I'm not sure what you mean
- Context-aware: I remember recent actions for "do that thing" type requests
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
        
        # Inject conversation context if available
        context_summary = await self.conversation_context.get_context_summary()
        if context_summary:
            system_prompt += f"\n\nCONVERSATION CONTEXT:\n{context_summary}"
        
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
    
    async def submit_background_task(
        self, 
        name: str, 
        description: str, 
        tool_name: str, 
        tool_args: dict,
        timeout_minutes: int = 10
    ) -> str:
        """Submit a tool call to run in the background
        
        Args:
            name: Short name for the task
            description: What the task does (for user notification)
            tool_name: Name of the tool to execute
            tool_args: Arguments for the tool
            timeout_minutes: Timeout in minutes
        
        Returns:
            Task ID
        """
        async def run_tool(task):
            """Coroutine that runs the tool"""
            result = await self.tool_registry.execute_tool(tool_name, **tool_args)
            
            # Log the action
            await self._log_action(tool_name, tool_args, result)
            
            # Return result in a format the notification can use
            return {
                "status": result.status.value,
                "message": result.message,
                "data": result.data,
                "error": result.error
            }
        
        task_id = await self.background_task_manager.submit_task(
            name=name,
            description=description,
            coroutine=run_tool,
            timeout_minutes=timeout_minutes
        )
        
        return task_id
    
    def _should_suggest_background(self, tool_name: str, action: str, args: dict) -> bool:
        """Check if this action might benefit from background execution (for suggestions only)"""
        # Actions that are potentially long-running
        potentially_long = {
            "system_info": ["find_file", "find_app_path"],
            "windows": ["search_files"],
            "developer": ["git_clone", "pip_install", "npm_install", "winget_install"],
        }
        
        if tool_name in potentially_long:
            if action in potentially_long[tool_name]:
                # Searching all drives is definitely long
                if action in ["find_file", "find_app_path", "search_files"]:
                    if not args.get("search_path") and not args.get("search_drive") and not args.get("path"):
                        return True
        
        return False
    
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
                asyncio.create_task(self._play_audio_queue()),
                asyncio.create_task(self._check_background_tasks())
            ]
            
            # Wait for tasks (they run until self.running = False)
            await asyncio.gather(*self._tasks, return_exceptions=True)
            
        except asyncio.CancelledError:
            logging.info("Tasks cancelled")
        except Exception as e:
            logging.error(f"Error in main loop: {e}")
        finally:
            await self._shutdown()
    
    async def _check_background_tasks(self):
        """Periodically check for completed background tasks and notify user"""
        while self.running:
            try:
                # Check every 2 seconds
                await asyncio.sleep(2)
                
                if not self.background_task_manager:
                    continue
                
                # Check if there are completed tasks to announce
                if await self.background_task_manager.has_pending_notifications():
                    announcements = await self.background_task_manager.get_completion_announcements()
                    
                    for announcement in announcements:
                        logging.info(f"📢 Background task notification: {announcement}")
                        
                        # Send the announcement to Gemini so Sakura can speak it
                        # We'll inject it as a system message that Sakura should relay
                        try:
                            await self.gemini_client.send_text(
                                f"[BACKGROUND TASK COMPLETED - Tell the user naturally]: {announcement}"
                            )
                        except Exception as e:
                            logging.error(f"Error sending task notification: {e}")
                            # Fallback: just print it
                            print(f"📢 {announcement}")
                
            except Exception as e:
                logging.debug(f"Error checking background tasks: {e}")
                await asyncio.sleep(5)
    
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
        # Initialize wake_greeting_prob once at the beginning of the method
        wake_greeting_prob = float(os.getenv('WAKE_GREETING_PROBABILITY', '0.7'))
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
                        logging.info("Wake word detected - now listening")
                        
                        # Randomly make Sakura speak a greeting (configurable probability for human-like feel)
                        if secrets.randbelow(100) / 100.0 < wake_greeting_prob:
                            try:
                                # Get a random wake response based on personality
                                wake_responses = get_wake_responses()
                                greeting = wake_responses[secrets.randbelow(len(wake_responses))]
                                
                                # Send to Gemini so Sakura speaks it naturally
                                await self.gemini_client.send_text(
                                    f"[WAKE WORD DETECTED - Greet the user with this energy/style, you can vary it slightly]: {greeting}"
                                )
                                logging.info(f"Wake greeting sent: {greeting}")
                            except Exception as e:
                                logging.debug(f"Could not send wake greeting: {e}")
                
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
                    
                    # Capture user transcription if available
                    if 'user_transcription' in response:
                        self._current_user_input = response['user_transcription']
                        logging.debug(f"User said: {self._current_user_input}")
                    
                    # Display text response and record exchange
                    if 'text' in response:
                        print(f"💋 Sakura: {response['text']}")
                        
                        # Record exchange to conversation context
                        # Use captured transcription or a placeholder
                        user_input = self._current_user_input if self._current_user_input else "[voice input]"
                        await self.conversation_context.add_exchange(
                            user_input=user_input,
                            ai_response=response['text'],
                            tools_used=self._current_tools_used.copy() if self._current_tools_used else None
                        )
                        # Reset tracking for next exchange
                        self._current_user_input = ""
                        self._current_tools_used = []
                    
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
                        # Set speaking flag ONLY during actual audio playback (not after)
                        # This prevents speaker auth from rejecting the AI's own voice
                        self.is_speaking = True
                        try:
                            # Play in thread to not block async loop
                            await asyncio.to_thread(
                                self.audio_manager.play_audio, 
                                audio_data
                            )
                        finally:
                            # Clear flag immediately after playback completes
                            self.is_speaking = False
                except asyncio.TimeoutError:
                    continue
            except Exception as e:
                logging.error(f"Error playing audio: {e}")
                self.is_speaking = False  # Ensure flag is cleared on error
                await asyncio.sleep(0.1)
    
    async def _handle_function_calls(self, function_calls):
        """Handle function calls from Gemini using tool registry with error recovery"""
        for fc in function_calls:
            tool_name = fc.name
            tool_args = fc.args if hasattr(fc, 'args') else {}
            call_id = fc.id if hasattr(fc, 'id') else tool_name
            
            # Apply user preferences to arguments
            action = tool_args.get('action', 'unknown')
            
            # Check if Gemini requested background execution
            run_in_background = tool_args.pop('run_in_background', False)
            
            tool_args = await self.user_preferences.apply_preferences_to_args(
                tool_name, action, tool_args
            )
            
            # Check for learned corrections before executing
            corrections = await self.conversation_context.get_relevant_corrections(
                user_input=self._current_user_input or "",
                tool_name=tool_name
            )
            
            # Actually apply corrections to modify behavior
            correction_notes = []
            if corrections:
                tool_args, correction_notes = await self._apply_corrections(
                    tool_name, action, tool_args, corrections
                )
            
            # Check tool insights for reliability warnings
            tool_warning = None
            if hasattr(self.conversation_context, '_db') and self.conversation_context._db:
                try:
                    insights = await self.conversation_context._db.get_tool_insights(tool_name, action)
                    if not insights.get("is_reliable"):
                        tool_warning = insights.get("warning")
                        logging.warning(f"⚠️ Tool reliability warning: {tool_warning}")
                except Exception as e:
                    logging.debug(f"Could not retrieve tool insights: {e}")
                    pass
            
            logging.info(f"🔧 Tool call: {tool_name} with args: {tool_args}" + (" [BACKGROUND]" if run_in_background else ""))
            
            # Track tool usage for conversation context
            self._current_tools_used.append(tool_name)
            
            # Record last action for correction context
            await self.user_preferences.record_last_action(tool_name, action, tool_args)
            
            # Check if this should run in background (Gemini decides based on user intent)
            if run_in_background:
                # Submit to background and respond immediately
                task_name = f"{tool_name}.{action}"
                task_description = f"Running {action} on {tool_name}"
                
                # Add context to description
                if action == "find_file":
                    task_description = f"Searching for '{tool_args.get('name', 'files')}'"
                elif action == "find_app_path":
                    task_description = f"Finding '{tool_args.get('app_name', 'application')}'"
                elif action == "search_files":
                    task_description = f"Searching for '{tool_args.get('query', 'files')}'"
                
                task_id = await self.submit_background_task(
                    name=task_name,
                    description=task_description,
                    tool_name=tool_name,
                    tool_args=tool_args,
                    timeout_minutes=10
                )
                
                # Get current queue status
                status = await self.background_task_manager.get_all_tasks_status()
                queue_info = ""
                if status['total_pending'] > 0:
                    queue_info = f" There are {status['total_pending']} other tasks in the queue."
                
                response_text = f"I've started that task in the background (ID: {task_id}). {task_description}. I'll let you know when it's done!{queue_info} Is there anything else you'd like me to do while we wait?"
                
                logging.info(f"📋 Submitted background task: {task_id} - {task_description}")
                
                # Send response back to Gemini
                await self.gemini_client.send_function_response(call_id, tool_name, response_text)
                continue  # Skip normal execution
            
            # Execute tool via registry (normal synchronous execution)
            import time
            start_time = time.time()
            
            # Add system state only to speaker recognition tool (needs it for auth)
            if tool_name == 'speaker_recognition':
                tool_args['_is_speaking'] = self.is_speaking
            
            result = await self.tool_registry.execute_tool(tool_name, **tool_args)
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Remove system state before logging (internal flag only)
            logged_args = {k: v for k, v in tool_args.items() if k != '_is_speaking'}
            
            # Log action to memory for history
            await self._log_action(tool_name, logged_args, result)
            
            # Update tool patterns for learning
            if hasattr(self.conversation_context, '_db') and self.conversation_context._db:
                try:
                    await self.conversation_context._db.update_tool_pattern(
                        tool_name=tool_name,
                        action_name=action,
                        success=(result.status.value == "success"),
                        duration_ms=duration_ms,
                        params=logged_args
                    )
                except Exception as e:
                    logging.debug(f"Tool pattern update error: {e}")
            
            # Infer preferences from successful actions
            if result.status.value == "success":
                await self.user_preferences.infer_preference_from_action(
                    tool_name, action, tool_args, True
                )
            
            # Format result for Gemini
            if result.status.value == "success":
                response_text = result.message or str(result.data)
            else:
                error_msg = result.error or result.message
                
                # Check for known error solutions before standard recovery
                known_solution = None
                if hasattr(self.conversation_context, '_db') and self.conversation_context._db:
                    try:
                        solutions = await self.conversation_context._db.get_error_solutions(
                            tool_name, action
                        )
                        if solutions:
                            known_solution = solutions[0]
                            logging.info(f"🔧 Found known solution: {known_solution.get('solution', '')[:50]}")
                    except Exception:
                        pass
                
                # Attempt error recovery
                recovery_result = await self.error_recovery.attempt_recovery(
                    tool_name=tool_name,
                    action=tool_args.get('action', 'unknown'),
                    args={k: v for k, v in tool_args.items() if k != 'action'},
                    error_message=error_msg,
                    executor=lambda name, args: self.tool_registry.execute_tool(name, **args)
                )
                
                if recovery_result.success:
                    response_text = f"Recovered after {recovery_result.retries_used} retries: {recovery_result.result}"
                    logging.info(f"🔄 Recovery succeeded for {tool_name}")
                    
                    # Log the solution that worked
                    if hasattr(self.conversation_context, '_db') and self.conversation_context._db:
                        try:
                            await self.conversation_context._db.log_error_pattern(
                                tool_name=tool_name,
                                action_name=action,
                                error_type="recovered",
                                error_message=error_msg,
                                solution=f"Auto-recovered after {recovery_result.retries_used} retries"
                            )
                        except Exception:
                            pass
                else:
                    response_text = f"Error: {error_msg}"
                    
                    # Include known solution if available
                    if known_solution and known_solution.get('solution'):
                        response_text += f"\n\n🔧 Known fix: {known_solution['solution']}"
                    
                    if recovery_result.suggestion:
                        response_text += f"\n\nSuggestion: {recovery_result.suggestion}"
                    
                    # Track failed action in conversation context
                    await self.conversation_context.add_failed_action(
                        action=f"{tool_name}.{tool_args.get('action', 'unknown')}",
                        error=error_msg,
                        context=tool_args
                    )
                    
                    # Get proactive suggestion for the error
                    error_suggestion = await self.suggestion_engine.get_suggestion(
                        recent_error=error_msg
                    )
                    if error_suggestion:
                        response_text += f"\n\n💡 {error_suggestion.message}"
            
            # Check for follow-up suggestions on success
            if result.status.value == "success":
                follow_up = await self.suggestion_engine.get_follow_up_suggestion(
                    tool_name, action, result.data if hasattr(result, 'data') else None
                )
                if follow_up:
                    response_text += f"\n\n💡 {follow_up.message}"
            
            logging.info(f"🔧 Tool result: {response_text[:100]}...")
            
            # Send result back to Gemini
            await self.gemini_client.send_function_response(call_id, tool_name, response_text)
    
    async def _apply_corrections(self, tool_name: str, action: str, tool_args: dict, corrections: list) -> tuple:
        """Apply learned corrections to modify tool behavior"""
        notes = []
        modified_args = tool_args.copy()
        
        for corr in corrections[:3]:  # Apply top 3 corrections
            correct_behavior = corr.get('correct_behavior', '')
            wrong_behavior = corr.get('wrong_behavior', '')
            trigger = corr.get('trigger_pattern', '')
            corr_id = corr.get('id')
            
            if not correct_behavior:
                continue
            
            # Log that we're applying this correction (include trigger and wrong behavior for context)
            log_msg = f"📝 Applying correction: {correct_behavior[:60]}..."
            if wrong_behavior:
                log_msg += f" (avoiding: {wrong_behavior[:30]})"
            logging.info(log_msg)
            notes.append(f"Applied correction for '{trigger[:30]}': {correct_behavior[:50]}")
            
            # Mark correction as used (increases confidence)
            if corr_id and hasattr(self.conversation_context, '_db') and self.conversation_context._db:
                try:
                    await self.conversation_context._db.mark_correction_used(corr_id)
                except Exception:
                    pass
            
            # Try to extract actionable modifications from correction text
            correct_lower = correct_behavior.lower()
            
            # Path-related corrections
            if 'path' in correct_lower or 'folder' in correct_lower or 'directory' in correct_lower:
                # Extract path from correction if mentioned
                import re
                path_match = re.search(r'["\']?([a-zA-Z]:\\[^"\']+|/[^"\']+)["\']?', correct_behavior)
                if path_match and 'path' in modified_args:
                    modified_args['path'] = path_match.group(1)
                    notes.append(f"Changed path to: {path_match.group(1)}")
            
            # Search drive corrections
            if 'drive' in correct_lower:
                drive_match = re.search(r'\b([a-zA-Z]):\s*drive\b|\bdrive\s*([a-zA-Z]):', correct_lower)
                if drive_match and 'search_drive' in modified_args:
                    drive = drive_match.group(1) or drive_match.group(2)
                    modified_args['search_drive'] = f"{drive.upper()}:\\"
                    notes.append(f"Changed search drive to: {drive.upper()}:")
            
            # Depth/limit corrections
            if 'depth' in correct_lower or 'deeper' in correct_lower:
                if 'max_depth' in modified_args:
                    current = modified_args.get('max_depth', 3)
                    if 'more' in correct_lower or 'deeper' in correct_lower or 'increase' in correct_lower:
                        modified_args['max_depth'] = min(current + 2, 10)
                        notes.append(f"Increased depth to: {modified_args['max_depth']}")
            
            # Don't/avoid corrections - these are warnings, not modifications
            if correct_lower.startswith("don't") or correct_lower.startswith("avoid") or correct_lower.startswith("never"):
                notes.append(f"⚠️ Remember: {correct_behavior[:50]}")
        
        return modified_args, notes
    
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
        
        # Save conversation context before shutdown
        if self.conversation_context:
            await self.conversation_context.cleanup()
        
        # Save error recovery history
        if self.error_recovery:
            await self.error_recovery.cleanup()
        
        # Save user preferences
        if self.user_preferences:
            await self.user_preferences.cleanup()
        
        # Save suggestion history
        if self.suggestion_engine:
            await self.suggestion_engine.cleanup()
        
        # Save intent parser learning
        if self.intent_parser:
            await self.intent_parser.cleanup()
        
        # Cleanup background task manager
        if self.background_task_manager:
            await self.background_task_manager.cleanup()
        
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
    
    # Initialize personas from loaded configuration at runtime
    # This replaces import-time initialization with runtime-aware settings
    initialize_from_config(
        personality=config.gemini.personality,
        assistant_name=config.gemini.assistant_name,
        voice=config.voice.voice_name
    )
    initialize_personas()
    logging.info(f"🎭 Runtime configuration initialized for {config.gemini.assistant_name}")
    
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
        # Check if API keys were successfully loaded
        # APIKeyManager.load_keys() now returns bool indicating success
        if not await girlfriend.key_manager.load_keys():
            print("❌ Failed to load any API keys!")
            print("Unable to start application without valid API keys.")
            return
        
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
