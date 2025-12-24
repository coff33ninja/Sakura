# Changelog

All notable changes to Sakura AI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-24

### 🎉 First Stable Release

This is the first stable release of Sakura, a fully autonomous AI assistant with real-time voice interaction, complete Windows control, and self-learning capabilities.

### Added

#### AI Enhancement Suite (6 Modules)
- **Conversation Context** (`conversation_context.py`)
  - Rolling buffer of 20 exchanges
  - Mood detection (positive, frustrated, urgent, confused, casual)
  - Topic tracking (files, system, apps, media, coding, etc.)
  - Context injection into system prompt
  - Session persistence with 30-min resume

- **Task Chaining** (`task_chain.py`)
  - Multi-step request execution
  - Dependency tracking between tasks
  - Result passing between steps
  - Chain detection ("and then", "after that", "also")
  - Save/load chains to JSON

- **Error Recovery** (`error_recovery.py`)
  - Error categorization (transient, permission, not_found, rate_limit, invalid, permanent)
  - Automatic retry with exponential backoff
  - Cooldown system for repeated failures
  - User-friendly suggestions
  - Error history tracking

- **User Preferences** (`user_preferences.py`)
  - Correction learning ("No, I meant...")
  - Preference detection ("Always use PowerShell")
  - Shortcut system ("My project = E:\Projects\Main")
  - Preference inference from actions
  - Auto-apply to tool arguments

- **Proactive Suggestions** (`suggestions.py`)
  - Time-based (morning, late night, lunch, end of day)
  - Context-based (Python testing, git status, file backup)
  - Error-based (permission fixes, search alternatives)
  - Follow-up suggestions after actions
  - Acceptance tracking and learning

- **Natural Language Understanding** (`intent_parser.py`)
  - Comprehensive synonym database
  - Vague command handling ("do that", "the usual", "fix it")
  - Fuzzy matching with typo tolerance
  - Intent type detection
  - Recent word context tracking

#### Core Features
- **Real-time Voice** via Gemini Live API
  - Natural, low-latency conversation
  - Interruption support
  - Multiple voices (Aoede, Kore, Charon, Fenrir, Puck)
  - 8 personality modes (4 female, 4 male)

- **Wake Word Detection** via Picovoice
  - GPU acceleration support
  - Custom .ppn file support
  - Built-in keywords (jarvis, alexa, etc.)

- **Multi-Key API Rotation**
  - Automatic failover on rate limits
  - Key health monitoring
  - Usage statistics

- **Session Management**
  - 2-hour session persistence
  - Automatic resume on restart

#### Windows Integration (41 Actions)
- App/window control (open, close, focus, minimize, maximize)
- Mouse control (move, click, multi-monitor aware)
- Smart UI clicking (find buttons by name)
- Media control (play, pause, volume)
- File operations (read, write, delete, search)
- Process management (list, kill)
- Screenshots and clipboard
- Screen reading (OCR, UI Automation)

#### System Discovery (15 Actions)
- Hardware specs (CPU, RAM type/speed, GPU VRAM via nvidia-smi)
- Multi-monitor detection with primary flag
- Installed/running applications
- Network adapters and IPs
- Drive information

#### Memory System (16 Actions)
- Auto-logging of all actions
- Location memory (file paths, app locations)
- Script tracking with paths
- Topic tracking with frequency
- Cross-category search

#### Integrations
- **Web Search** - DuckDuckGo instant answers
- **Web Fetch** - URL content extraction
- **Discord** - Text and voice channel support
- **Smart Home** - Home Assistant integration
- **MCP Client** - Model Context Protocol servers

### Technical Details
- **Python 3.12** required
- **Full async architecture** with asyncio
- **Thread-safe** operations with asyncio.Lock()
- **aiofiles** for all file I/O
- **Proper cleanup** on shutdown

### Files Added
```
modules/
├── conversation_context.py
├── task_chain.py
├── error_recovery.py
├── user_preferences.py
├── suggestions.py
└── intent_parser.py
```

### Data Files Created at Runtime
```
conversation_context.json    # Conversation history
user_preferences.json        # Learned preferences
suggestion_history.json      # Suggestion tracking
error_recovery_log.json      # Error history
intent_learning.json         # Learned intent mappings
```

---

## Pre-1.0 Development History

<details>
<summary>Click to expand development history</summary>

### [0.9.x] - AI Enhancement Phases
- v0.9.6: Natural Language Understanding
- v0.9.5: Proactive Suggestions
- v0.9.4: Learning from Corrections
- v0.9.3: Error Recovery
- v0.9.2: Task Chaining
- v0.9.1: Conversation Context

### [0.8.x] - Smart UI & Hardware
- Smart element clicking
- Multi-monitor support
- Detailed hardware specs
- GPU stats via nvidia-smi

### [0.7.x] - Wake Word & Voice
- Wake word fixes
- GPU acceleration
- Custom .ppn support
- Voice customization

### [0.6.x] - Personas & Screen Reading
- Male personas
- Voice-gender validation
- Screen reading actions
- OCR support

### [0.5.x] - Windows Automation
- 41 Windows actions
- Script sandbox
- File operations
- Process management

### [0.4.x] - Memory & Discovery
- Memory system (16 actions)
- System discovery (15 actions)
- Auto-logging
- Location tracking

### [0.3.x] - Tools & Integrations
- Tool registry system
- Discord integration
- Web search/fetch
- Smart home support

### [0.2.x] - Audio & SDK
- Gemini SDK 1.x compatibility
- Correct sample rates
- Async audio queue

### [0.1.x] - Foundation
- Async architecture
- API key rotation
- Session persistence
- Basic voice chat

</details>
