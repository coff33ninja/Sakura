# Changelog

All notable changes to Sakura AI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.1] - 2025-12-26

### 🔌 Integration Improvements

Fixes and enhancements for MCP and Smart Home integrations.

#### Added

**MCP Client Improvements**
- Proper MCP protocol initialization (initialize → initialized notification → tools/list)
- 60-second timeout (up from 5s) for slow servers
- Multi-line JSON response handling
- Environment variable support for server configs
- Better error messages for missing uvx/npx
- `get_schema()` method for Gemini function calling
- `cleanup()` method for proper process termination

**Smart Home Enhancements (21 Actions)**
- **Switches**: `switch_on`, `switch_off`
- **Fans**: `fan_on`, `fan_off`, `set_fan_speed`
- **Covers/Blinds**: `cover_open`, `cover_close`, `cover_stop`, `set_cover_position`
- **Scenes**: `activate_scene`, `list_scenes`
- **Automations**: `trigger_automation`, `list_automations`
- **Energy**: `get_energy_usage` (monitors power/consumption sensors)
- **State**: `get_device_state` (full device state with attributes)
- **Discovery**: `list_devices_by_type` (filter by light, switch, fan, etc.)
- **Media**: `pause_music`, `stop_music`, `set_volume`
- **Climate**: `set_hvac_mode` (heat, cool, auto, off)

#### Changed
- Smart Home actions increased from 6 to 21
- Total tool actions increased from 156 to 173
- Better authentication error messages for Home Assistant

---

## [1.1.0] - 2025-12-26

### 🧠 Intelligent Memory System

Major upgrade to Sakura's memory and learning capabilities.

#### Added

**SQLite Database Backend**
- New `modules/database.py` - Async SQLite wrapper with connection pooling
- 17 database tables for comprehensive data storage
- WAL mode for better concurrent access
- Foreign keys and proper indexing
- JSON export every 5 minutes for user transparency

**FTS5 Full-Text Search**
- `memory_fts` virtual table with porter tokenizer
- BM25 relevance ranking
- Auto-indexing on insert
- New `search_fts` memory action

**User Feedback Detection**
- `_detect_correction()` - Detects "No, I meant...", "Not that", etc.
- `_detect_positive_feedback()` - Detects "Perfect!", "Thanks!", etc.
- `_detect_negative_feedback()` - Detects "That's wrong", "Stop it", etc.
- All feedback logged to `user_feedback` table

**Self-Learning Corrections**
- `learned_corrections` table with trigger patterns
- `_apply_corrections()` in main.py modifies tool behavior
- Confidence scoring with decay over time
- Session-aware vs permanent corrections

**Tool Pattern Analytics**
- `tool_patterns` table tracks success rates and duration
- `get_tool_insights()` returns reliability warnings
- Warns before using tools with <50% success rate

**Error Pattern Tracking**
- `error_patterns` table with solutions
- `get_error_solutions()` queries known fixes
- Auto-applies solutions on repeat errors

**Memory Cleanup**
- `prune_old_data()` with configurable retention
- Keeps high-value data (with feedback)
- VACUUM for disk space reclamation
- `get_database_stats()` for monitoring

**New Memory Actions**
- `search_fts` - Fast full-text search
- `log_feedback` - Log user corrections/reactions
- `get_corrections` - Get relevant learned corrections
- `get_full_history` - Query infinite conversation history
- `get_error_solutions` - Get known solutions for errors
- `get_history_stats` - Statistics about stored history
- `log_exchange` - Log full conversation exchange

**MCP Client Improvements**
- Proper MCP protocol initialization (initialize → initialized notification → tools/list)
- 60-second timeout (up from 5s) for slow servers
- Multi-line JSON response handling
- Environment variable support for server configs
- Better error messages for missing uvx/npx
- `get_schema()` method for Gemini function calling
- `cleanup()` method for proper process termination

**Smart Home Enhancements (21 Actions)**
- Better authentication error messages
- **Switches**: `switch_on`, `switch_off`
- **Fans**: `fan_on`, `fan_off`, `set_fan_speed`
- **Covers/Blinds**: `cover_open`, `cover_close`, `cover_stop`, `set_cover_position`
- **Scenes**: `activate_scene`, `list_scenes`
- **Automations**: `trigger_automation`, `list_automations`
- **Energy**: `get_energy_usage` (monitors power/consumption sensors)
- **State**: `get_device_state` (full device state with attributes)
- **Discovery**: `list_devices_by_type` (filter by light, switch, fan, etc.)
- **Media**: `pause_music`, `stop_music`, `set_volume`
- **Climate**: `set_hvac_mode` (heat, cool, auto, off)

#### Changed
- Memory store now uses SQLite as primary storage
- JSON files are now exports for transparency (not primary storage)
- Conversation context logs exchanges to database automatically
- Tool execution tracks duration and updates patterns
- Error handling queries known solutions first
- Smart Home actions increased from 6 to 21
- Total tool actions increased from 156 to 173

#### Technical
- Added `aiosqlite>=0.22.1` to requirements
- Database auto-migrates from legacy JSON on first run
- Singleton pattern for database connection
- All database operations are async with proper locking

---

## [1.0.0] - 2025-12-24

### 🎉 First Stable Release

Sakura v1.0.0 - A fully autonomous AI assistant with real-time voice interaction, complete Windows control, and self-learning capabilities.

**150 Total Tool Actions** across 10 tool categories.

---

### Latest Updates (2025-12-25)

#### 🔍 Enhanced File Search (`find_file`)
Major improvements to file discovery across all drives:

**Path Handling**
- User shortcuts: `Documents`, `Downloads`, `Desktop`, `Pictures`, `Music`, `Videos`, `AppData`, `Home`
- Environment variables: `%USERPROFILE%`, `%APPDATA%`, `%LOCALAPPDATA%`, `%TEMP%`, etc.
- UNC/network paths: `\\server\share\folder`
- Proper escaping for paths with spaces and special characters

**Search Scope**
- Added `LocalAppData\Programs` (Discord, VS Code user installs)
- Added `PortableApps` and portable app locations
- New `include_removable` parameter for USB drives
- Configurable `max_depth` parameter (default 6)
- Enhanced priority paths: Steam, SteamLibrary, GOG, Epic, Origin, Ubisoft, Battle.net

**Smart Folder Hints**
- New `folder_hint` parameter: `folder_hint="Steam"` + `search_drive="D"` → searches `D:\Steam`
- Fuzzy folder matching (exact → contains → starts-with)
- Combines user intent with drive specification

**Symlinks & Junctions**
- New `follow_links` parameter (default true)
- Results include `IsSymlink` and `LinkTarget` fields
- Properly follows Steam library junctions

**PATH Search**
- New `search_path_env` parameter
- Auto-searches PATH for executable file types
- Environment variable expansion in paths

#### 🎙️ Wake Word Personality Responses
- Sakura now **speaks** a greeting when wake word is detected (not just silent listening)
- Greetings match current personality (flirty, friendly, romantic, tsundere, etc.)
- 70% probability by default for human-like variation (configurable)
- New `WAKE_GREETING_PROBABILITY` setting in .env (0.0-1.0)

#### 🔧 Bug Fixes
- Fixed `find_file` parameter naming (`search_drive` now works as alias for `search_path`)
- Fixed search not finding files in specific folders like `D:\Steam`
- Improved PowerShell path escaping for special characters

---

### Tool Categories

#### 🖥️ Windows Automation (46 Actions)
- App/window control (open, close, focus, minimize, maximize)
- Mouse control (move, click, scroll, drag, multi-monitor aware)
- Smart UI clicking (find buttons by name)
- Keyboard shortcuts (Ctrl+C, Alt+Tab, Win+D, etc.)
- Window snapping (Win+Arrow keys)
- Virtual desktop control
- Media control (play, pause, volume)
- File operations (read, write, delete, search)
- Process management (list, kill)
- Screenshots and clipboard
- Screen reading (OCR, UI Automation)
- Power management (sleep, shutdown, restart, lock)

#### 💻 Developer Tools (33 Actions)
**Git Operations (11)**
- git_status, git_add, git_commit, git_push, git_pull
- git_branch, git_checkout, git_log, git_diff
- git_clone, git_init

**Code Execution (4)**
- run_python, run_javascript, run_powershell, run_batch

**Package Management (11)**
- pip: install, uninstall, list
- npm: install, uninstall, list
- winget: search, install, uninstall, list

**SSH (5)**
- ssh_connect, ssh_run_command
- ssh_add_profile, ssh_list_profiles, ssh_delete_profile

**Utility (3)**
- check_tools, find_tool_path, run_multiple_commands

#### 📅 Productivity (23 Actions)
**Reminders (4)**
- set_reminder, list_reminders, cancel_reminder, snooze_reminder

**Timers (6)**
- start_timer, stop_timer, list_timers, get_timer_status
- start_stopwatch, stop_stopwatch

**Notes (6)**
- create_note, get_note, update_note, delete_note
- list_notes, search_notes

**To-Do (5)**
- add_todo, complete_todo, update_todo, delete_todo, list_todos

**Windows Integration (2)**
- open_alarms_app, show_notification

#### 🔍 System Discovery (16 Actions)
- Hardware specs (CPU, RAM type/speed, GPU VRAM)
- Multi-monitor detection
- Installed/running applications (searches all registry locations)
- Network adapters and IPs
- Drive information
- Folder exploration
- **find_file** - Advanced file search with:
  - User shortcuts (Documents, Downloads, Desktop, etc.)
  - Environment variable expansion (%APPDATA%, %LOCALAPPDATA%)
  - UNC/network path support
  - Folder hints for targeted search
  - Symlink/junction following
  - PATH environment search
  - Configurable depth and removable drive support
- **find_app_path** - Enhanced app discovery (registry, App Paths, Start Menu, all drives)

#### 🧠 Memory System (16 Actions)
- Auto-logging of all actions
- Location memory (file paths, app locations)
- Script tracking with paths
- Topic tracking with frequency
- Cross-category search

#### 🌐 Web Tools (2 Actions)
- web_search (DuckDuckGo)
- web_fetch (URL content extraction)

#### 💬 Discord (5 Actions)
- Text and voice channel support
- Message sending/reading

#### 🏠 Smart Home (6 Actions)
- Home Assistant integration
- Device control

#### 🔌 MCP Client (3 Actions)
- Model Context Protocol server connections

---

### AI Enhancement Suite (6 Modules)

#### Conversation Context (`conversation_context.py`)
- Rolling buffer of 20 exchanges
- Mood detection (positive, frustrated, urgent, confused, casual)
- Topic tracking
- Context injection into system prompt

#### Task Chaining (`task_chain.py`)
- Multi-step request execution
- Dependency tracking between tasks
- Result passing between steps

#### Error Recovery (`error_recovery.py`)
- Error categorization (transient, permission, not_found, rate_limit)
- Automatic retry with exponential backoff
- User-friendly suggestions

#### User Preferences (`user_preferences.py`)
- Correction learning ("No, I meant...")
- Preference detection
- Shortcut system

#### Proactive Suggestions (`suggestions.py`)
- Time/context/error-based suggestions
- Acceptance tracking

#### Natural Language Understanding (`intent_parser.py`)
- Synonym database
- Vague command handling
- Fuzzy matching

---

### Core Features

#### Background Task Manager (`background_tasks.py`)
- Execute long tasks without blocking voice conversation
- Task queue with max 3 concurrent tasks
- Progress tracking and completion notifications
- Sakura announces when background tasks complete
- Automatic for: file searches, app discovery, git clone, package installs
- Task history persistence

#### Wake Word Responses
- Personality-matched spoken greetings on wake word detection
- Configurable probability (default 70%) for human-like variation
- Greetings sent to Gemini for natural voice output

#### Connection Health Monitoring (`gemini_client.py`)
- Auto-reconnect on connection drop
- Activity tracking
- Consecutive error handling

#### Real-time Voice (Gemini Live API)
- Natural, low-latency conversation
- Interruption support
- Multiple voices (Aoede, Kore, Charon, Fenrir, Puck)
- 8 personality modes

#### Wake Word Detection (Picovoice)
- GPU acceleration support
- Custom .ppn file support
- Built-in keywords

#### Multi-Key API Rotation
- Automatic failover on rate limits
- Key health monitoring

---

### Technical Details
- **Python 3.12** required
- **Full async architecture** with asyncio
- **Thread-safe** operations with asyncio.Lock()
- **aiofiles** for all file I/O
- **All imports used** per Rule #1

### Data Storage
```
~/Documents/{ASSISTANT_NAME}/
├── scripts/          # Generated scripts
├── productivity/     # Reminders, timers, notes, todos
└── developer/        # SSH profiles
```

---

## Pre-1.0 Development History

<details>
<summary>Click to expand</summary>

- v0.9.x: AI Enhancement Phases (context, chaining, recovery, preferences, suggestions, NLU)
- v0.8.x: Smart UI & Hardware detection
- v0.7.x: Wake Word & Voice customization
- v0.6.x: Personas & Screen Reading
- v0.5.x: Windows Automation (41 actions)
- v0.4.x: Memory & System Discovery
- v0.3.x: Tool registry, Discord, Web, Smart Home
- v0.2.x: Gemini SDK 1.x, Audio fixes
- v0.1.x: Foundation, async architecture

</details>
