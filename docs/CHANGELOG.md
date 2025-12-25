# Changelog

All notable changes to Sakura AI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-24

### 🎉 First Stable Release

Sakura v1.0.0 - A fully autonomous AI assistant with real-time voice interaction, complete Windows control, and self-learning capabilities.

**150 Total Tool Actions** across 10 tool categories.

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
- **find_file** - Search for ANY file type across all drives (exe, documents, images, videos, audio, archives, code)
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
