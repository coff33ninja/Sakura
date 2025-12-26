# 🌸 Sakura - Ultimate Windows AI Assistant

> ## ⚠️ EXPERIMENTAL SOFTWARE WARNING
> 
> **Sakura is a research-grade AI agent, NOT a production-safe consumer product.**
> 
> - Can generate and execute arbitrary code on your system
> - Can self-modify its own source code
> - Can access network, files, and system resources
> - Safeguards are soft limits that can be bypassed
> - Should be run in isolated/sandboxed environments
> 
> **Required reading before use:**
> - [docs/SECURITY.md](docs/SECURITY.md) — Threat model, attack scenarios, incident response
> - [docs/HARDENING.md](docs/HARDENING.md) — How to run Sakura more safely
> - [docs/ETHICS_AND_ACCESSIBILITY.md](docs/ETHICS_AND_ACCESSIBILITY.md) — Risks, abuse scenarios, data retention

**Sakura** is a fully autonomous AI assistant with real-time voice interaction, complete Windows control, self-learning memory, and script generation capabilities. She can control your PC, remember everything, create and execute scripts, and learn about your system over time.

> *"Hey Sakura, find my project files and create a backup script"* - She'll search all drives, remember the locations, write the script, and execute it.

> ⚠️ **Documentation Notice**: The docs in `docs/tools/` and `docs/modules/` were AI-generated and may not be 100% accurate. The codebase is large and complex, so some details involve AI guessing based on partial context. Always refer to the actual source code for authoritative information.

## ✨ Key Features

### 💻 Developer Tools (47 Actions)
- Git operations (status, add, commit, push, pull, branch, checkout, log, diff, clone, init)
- Code execution (Python, JavaScript, PowerShell, Batch)
- Package management (pip, npm, winget)
- Connection profiles (SSH, SMB, FTP/SFTP, RDP) with database storage
- SSH (OpenSSH, PuTTY), SMB shares, FTP/SFTP, RDP

### 🧠 Meta Tools - Self-Awareness (15 Actions)
- **Introspection** - Understand all 206 available actions
- **Capability search** - Find tools matching user requests
- **Gap analysis** - Identify when extension scripts are needed
- **Script generation** - Create Python/PowerShell/Batch/JS extensions on-the-fly
- **Script execution** - Run and track extension scripts with success metrics
- **Self-improvement** - Learn from script usage patterns

### 📅 Productivity (27 Actions)
- Reminders with Windows notifications
- Countdown timers and stopwatch
- Quick notes with tags, search, and FTS5 full-text search
- To-do lists with priorities, due dates, and completion history
- Task history tracking ("what did I complete last month?")

### 🎙️ Real-Time Voice Conversation
- **Gemini Live API** - Natural, low-latency voice interaction
- **Interruption support** - Talk naturally, interrupt anytime
- **Multiple voices** - Female (Aoede, Kore), Male (Charon, Fenrir), Neutral (Puck)
- **Configurable personalities** - Female & Male personas with gender-matched voices
- **Voice/Persona validation** - Warns if voice gender doesn't match persona

### Complete Windows Control (46 Actions)
- **Run commands** - PowerShell, CMD, any command
- **App control** - Open, close, focus, minimize, maximize windows
- **Mouse control** - Move cursor, click, double-click, multi-monitor aware
- **Smart clicking** - Find and click buttons by name (OK, Cancel, Close, Accept)
- **Context awareness** - Know what's under the cursor (UI element, window, monitor)
- **Media control** - Play, pause, next, prev, volume up/down/mute
- **File operations** - Read, write, delete files and folders
- **Search** - Find files across ALL drives
- **Screenshots** - Capture screen anytime
- **Clipboard** - Get/set clipboard content
- **Process management** - List, kill processes
- **Screen reading** - UI Automation, OCR, element inspection

### 📝 Script Generation & Execution
- **Sandbox folder** - All scripts saved to `~/Documents/Sakura/scripts/`
- **Multiple languages** - PowerShell, Python, Batch, JavaScript, VBScript
- **Auto-headers** - Timestamp and metadata in every script
- **Safe execution** - Scripts always saved for user review
- **Visible terminals** - Can launch scripts in new terminal windows

### 🧠 Self-Learning Memory System (16+ Actions)
- **SQLite Database** - Fast, reliable storage with full-text search
- **JSON Transparency** - Exports to JSON every 5 minutes for user visibility
- **Auto-logging** - Every action recorded with timestamp
- **Location memory** - Remembers file paths, app locations discovered
- **Script tracking** - Logs all scripts created with paths
- **Infinite conversation history** - Full history in database, AI queries only what's needed
- **Topic tracking** - What you've discussed and how often
- **Cross-search** - Search across ALL memory categories
- **FTS5 Full-Text Search** - Lightning-fast search with relevance ranking
- **User Feedback Learning** - Learns from corrections, positive/negative feedback
- **Error Pattern Tracking** - Remembers solutions to avoid repeating mistakes
- **Tool Usage Analytics** - Tracks success rates and performance per tool

### 🔍 System Discovery (16 Actions)
- **PC info** - Computer name, username, OS
- **Hardware** - Full specs: CPU, RAM (type, speed, slots), GPU (VRAM via nvidia-smi), storage
- **Multi-monitor** - Detect all displays, primary/secondary, resolution, mouse position per monitor
- **Installed apps** - Search by category (browsers, dev, media, games, office, utilities)
- **Running processes** - See what's active
- **Network info** - Adapters, IPs, DNS
- **Folder exploration** - Browse any directory
- **App paths** - Find where apps are installed (searches ALL drives and registry)
- **Advanced file search** - Find any file type with smart path handling:
  - User shortcuts: `Documents`, `Downloads`, `Desktop`, `Pictures`, etc.
  - Environment variables: `%APPDATA%`, `%LOCALAPPDATA%`, `%USERPROFILE%`
  - Network paths: `\\server\share\folder`
  - Folder hints: "Find steam.exe in Steam folder on D drive"
  - Symlink/junction following for Steam libraries
  - PATH environment search for executables
  - Configurable depth and removable drive support

### 🔄 Background Task Execution
- **Non-blocking operations** - Long tasks run in background while you keep chatting
- **Task queue** - Up to 3 concurrent tasks, others queued automatically
- **Completion notifications** - Sakura tells you when tasks finish
- **Progress tracking** - Monitor running and pending tasks
- **Automatic for**: File searches across drives, app discovery, git clone, package installs

### 🎙️ Wake Word Personality Responses
- **Spoken greetings** - Sakura speaks when you say her name (not just silent listening)
- **Personality-matched** - Greetings match current persona (flirty, friendly, tsundere, etc.)
- **Human-like variation** - 70% chance to speak (configurable), adds natural randomness
- **Configurable** - Set `WAKE_GREETING_PROBABILITY` in .env (0.0-1.0)

### 🌐 Web & Integrations
- **Web search** - DuckDuckGo instant answers
- **URL fetching** - Extract content from websites
- **Discord** - Send messages, join voice channels
- **Smart Home** - Home Assistant integration
- **MCP Client** - Connect to Model Context Protocol servers

## 🚀 Quick Start

### Prerequisites
- Windows 10/11
- Microphone and speakers
- Gemini API key(s)

### Easy Install (Recommended)

Just double-click `setup.bat` - it handles everything:
1. Installs [uv](https://docs.astral.sh/uv/) (fast Python package manager)
2. Installs Python 3.12 via uv
3. Creates virtual environment
4. Installs all dependencies
5. Creates .env configuration file

Then use `start.bat` to launch Sakura anytime.

### Manual Installation

```bash
# Clone the repository
git clone https://github.com/coff33ninja/sakura-ai.git
cd sakura-ai

# Install uv (required for MCP servers)
winget install astral-sh.uv
# Or: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Install Python 3.12 and create venv
uv python install 3.12
uv venv --python 3.12 .venv

# Install dependencies
uv pip install -r requirements.txt --python .venv\Scripts\python.exe
```

### Configuration

Create a `.env` file:

```env
# Required - Gemini API keys (supports multiple for rotation)
GEMINI_API_KEY=your_primary_key
GEMINI_API_KEY_2=your_backup_key
GEMINI_API_KEY_3=another_backup_key

# Assistant Name (used in prompts and as wake word if built-in)
ASSISTANT_NAME=Sakura

# Personality Mode
# Female: flirty, friendly, romantic, tsundere
# Male: flirty_m, friendly_m, romantic_m, kuudere
SAKURA_PERSONALITY=friendly

# Voice (should match persona gender!)
# Female: Aoede (warm), Kore (soft)
# Male: Charon (deep), Fenrir (energetic)
# Neutral: Puck (works with any persona)
VOICE_NAME=Aoede

# Wake Word (optional - overrides ASSISTANT_NAME)
# Built-in: alexa, jarvis, computer, hey google, hey siri, etc.
WAKE_WORD_KEYWORDS=jarvis

# Optional - Wake word detection
PICOVOICE_ACCESS_KEY=your_picovoice_key

# Optional - Discord integration
DISCORD_BOT_TOKEN=your_discord_token

# Optional - Smart home
HOME_ASSISTANT_URL=http://192.168.1.100:8123
HOME_ASSISTANT_TOKEN=your_ha_token
```

### Run Sakura

```bash
# Easy way - just double-click
start.bat

# Or manually
.\.venv\Scripts\python main.py
```

## 🎯 What Can Sakura Do?

### Voice Commands Examples

| You Say | Sakura Does |
|---------|-------------|
| "Set a reminder for 5 minutes" | Creates reminder with notification |
| "Start a 10 minute timer" | Starts countdown timer |
| "Add a note about the meeting" | Creates quick note |
| "Add task: buy groceries" | Adds to-do item |
| "What's my PC name?" | Discovers and remembers system info |
| "Find all Python files" | Starts background search, notifies when done |
| "Find Steam on D drive" | Searches specific drive for application |
| "Find steam.exe in Steam folder" | Uses folder hint for targeted search |
| "Find my vacation photos" | Searches all drives for image files |
| "Find project files in Documents" | Uses user folder shortcut |
| "Open Chrome" | Launches Chrome |
| "Turn up the volume" | Increases system volume |
| "Create a script to ping Google" | Writes PowerShell script to sandbox |
| "What scripts have you made?" | Lists all created scripts with paths |
| "Move mouse to top left" | Moves cursor to (0, 0) |
| "Take a screenshot" | Captures screen to temp folder |
| "What did you do today?" | Shows action history |
| "Remember my name is John" | Stores in persistent memory |
| "Search for anything about backup" | Searches all memory categories |

### Tool Summary

| Tool | Actions | Description |
|------|---------|-------------|
| `windows` | 46 | Full Windows control, smart clicking, screen reading, hotkeys, power |
| `system_info` | 16 | System discovery, hardware specs, multi-monitor, file search |
| `memory` | 24 | Persistent memory with SQLite + JSON, FTS5, feedback learning |
| `web_search` | 1 | DuckDuckGo search |
| `web_fetch` | 1 | URL content extraction |
| `discord` | 5 | Discord integration |
| `smart_home` | 21 | Home Assistant (lights, switches, fans, covers, scenes, automations, energy) |
| `mcp_client` | 3 | MCP server connection (fixed protocol, 60s timeout) |
| `productivity` | 27 | Reminders, timers, notes, to-do lists with FTS search |
| `developer` | 47 | Git, code execution, packages, SSH/SMB/FTP/RDP connections |
| `meta` | 15 | Self-introspection, capability search, extension script generation |

**Total: 206 tool actions**

## 📁 Project Structure

```
sakura-ai/
├── main.py                 # Main application
├── modules/
│   ├── gemini_client.py    # Gemini Live API client
│   ├── audio_manager.py    # Audio I/O handling
│   ├── persona.py          # Personality definitions
│   ├── config.py           # Configuration management
│   ├── api_key_manager.py  # Multi-key rotation
│   ├── session_manager.py  # Session persistence
│   ├── database.py         # SQLite database with FTS5
│   └── conversation_context.py # Context + feedback detection
├── tools/
│   ├── base.py             # Base tool classes
│   ├── windows/            # Windows automation (46 actions)
│   ├── system_info/        # System discovery (16 actions)
│   ├── memory/             # Memory system (22 actions)
│   ├── web/                # Web search & fetch
│   ├── discord/            # Discord integration
│   ├── smart_home/         # Home Assistant
│   └── mcp/                # MCP client
├── sakura.db               # SQLite database (primary storage)
├── sakura_memory.json      # JSON export (user transparency)
├── requirements.txt        # Python dependencies
└── .env                    # Configuration (create this)
```

## 🔧 Configuration Options

### Personality Modes

| Mode | Gender | Description |
|------|--------|-------------|
| `friendly` | Neutral | Warm, helpful assistant (default) |
| `flirty` | Female | Playful, affectionate girlfriend |
| `romantic` | Female | Sweet, caring partner (PG-13) |
| `tsundere` | Female | Classic anime tsundere |
| `friendly_m` | Neutral | Warm, helpful male assistant |
| `flirty_m` | Male | Charming, affectionate boyfriend |
| `romantic_m` | Male | Sweet, caring boyfriend (PG-13) |
| `kuudere` | Male | Cool, calm but secretly caring |

### Voice Options

| Voice | Gender | Description |
|-------|--------|-------------|
| `Aoede` | Female | Warm, friendly (default) |
| `Kore` | Female | Soft, gentle |
| `Charon` | Male | Deep, calm |
| `Fenrir` | Male | Energetic |
| `Puck` | Neutral | Playful (works with any persona) |

> ⚠️ **Voice/Persona Matching**: On startup, Sakura warns if voice gender doesn't match persona gender. For example, using `Charon` (male voice) with `flirty` (female persona) will show a warning.

### Wake Word Options

Built-in wake words (no training needed):
`alexa`, `americano`, `blueberry`, `bumblebee`, `computer`, `grapefruit`, `grasshopper`, `hey barista`, `hey google`, `hey siri`, `jarvis`, `ok google`, `pico clock`, `picovoice`, `porcupine`, `terminator`

**Custom Wake Words:**
1. Train your keyword at [Picovoice Console](https://console.picovoice.ai/)
2. Download the `.ppn` file for Windows
3. Set in `.env`:
```env
WAKE_WORD_KEYWORDS=sakura
WAKE_WORD_PATH=path/to/Sakura_en_windows_v4_0_0.ppn
```

**GPU Acceleration:**
Porcupine v4 supports GPU acceleration. Set device in `.env`:
```env
# Auto-select best device (default)
PORCUPINE_DEVICE=best

# Force GPU
PORCUPINE_DEVICE=gpu:0

# Force CPU with thread count
PORCUPINE_DEVICE=cpu:8
```

### Script Sandbox

All scripts are saved to: `C:\Users\<YourName>\Documents\<AssistantName>\scripts\`

Organized by type:
- `/powershell/` - PowerShell scripts (.ps1)
- `/python/` - Python scripts (.py)
- `/batch/` - Batch files (.bat)
- `/javascript/` - Node.js scripts (.js)
- `/vbscript/` - VBScript files (.vbs)

## 🧠 Memory System

Sakura uses a **SQLite database** for fast, reliable storage with **JSON exports** for transparency.

### Why SQLite + JSON?
- **SQLite**: Fast queries, full-text search (FTS5), ACID compliant, handles concurrent access
- **JSON Export**: User can see/edit memories, backup-friendly, transparent operation
- **Best of both**: Database performance + human-readable transparency

### What Sakura Remembers

| Category | What's Stored |
|----------|---------------|
| `action_log` | Every tool action with timestamp and duration |
| `discovered_locations` | File paths, app locations found |
| `scripts_created` | Scripts made with full paths |
| `conversation_history` | Full conversation exchanges (infinite) |
| `topics_discussed` | Topics and frequency |
| `user_info` | Your name, preferences |
| `facts` | Things you've told her |
| `important_dates` | Birthdays, anniversaries |
| `user_feedback` | Corrections, positive/negative reactions |
| `learned_corrections` | Patterns to avoid repeating mistakes |
| `tool_patterns` | Success rates, performance per tool |
| `error_patterns` | Known errors and their solutions |

### Self-Learning Features

- **Correction Detection**: "No, I meant..." → Sakura learns what you actually wanted
- **Positive Feedback**: "Perfect!", "Thanks!" → Reinforces good behavior
- **Negative Feedback**: "That's wrong", "Stop it" → Learns what to avoid
- **Error Solutions**: Remembers what fixed errors, applies automatically
- **Confidence Decay**: Old unused corrections fade over time
- **Tool Insights**: Warns before using unreliable tools (<50% success rate)

## ⚠️ Important: What Sakura Actually Is

**Sakura is not a "safe" consumer product.** It is an experimental, open-source AI agent with system-level capabilities.

This means:
- **Prompt manipulation is possible** — this is a property of the system, not a bug
- **Safeguards are speed bumps, not walls** — they create friction, not prevention
- **Users own their installation** — and the responsibility that comes with it
- **Sakura is closer to PowerShell than to Siri** — it's a powerful tool, not a locked-down assistant

Ichoose **transparency over false promises** and **responsibility over hype**.

📖 **[Security Policy](docs/SECURITY.md)** — Threat model, reporting, and honest limitations

## 🔒 Security Notes — Honest Assessment

**What Sakura CAN do (with the right prompt):**
- Generate and execute arbitrary scripts
- Self-modify its own Python source code
- Access any network endpoint
- Request privilege elevation (UAC prompt)
- Schedule persistent tasks
- Rewrite its own guardrails

**What currently exists:**
- Scripts saved before execution (user can review)
- Actions logged to visible file
- Runs as user-level process by default
- No automatic execution without user presence

**What does NOT exist yet:**
- Hard script sandboxing
- Self-modification detection
- Network egress monitoring
- Destructive action friction

📖 **[Security Policy](docs/SECURITY.md)** — Full threat model, attack scenarios, incident response, planned countermeasures

📖 **[Hardening Guide](docs/HARDENING.md)** — How to run Sakura more safely (VMs, firewalls, monitoring)

📖 **[Contributing Guidelines](docs/CONTRIBUTING.md)** — Security-focused contribution requirements

## ♿ Accessibility & Ethics

Sakura can be a powerful tool for **accessibility** — enabling users with physical disabilities, visual impairments, or cognitive challenges to control their computers through voice alone.

However, powerful tools require responsible use and honest documentation.

📖 **[Ethics, Accessibility & Responsible Use](docs/ETHICS_AND_ACCESSIBILITY.md)**

This document covers:
- ✅ How Sakura helps users with disabilities
- ✅ Positive use cases (productivity, learning, creative work)
- ⚠️ Potential risks and the manipulation reality
- 🛡️ Built-in safeguards (and their limitations)
- 📋 Responsible use guidelines
- 🎭 Personality modes and responsible interaction

📖 **[Security Policy](docs/SECURITY.md)**

This document covers:
- 🔐 Threat model (what Iprotect against, what Ican't)
- 🚨 Vulnerability reporting procedures
- ⚠️ The honest reality of open-source AI agents
- 👤 User security responsibilities

## 📋 Requirements

```
google-genai>=1.0.0
pyaudio>=0.2.14
pvporcupine>=3.0.0
aiofiles>=23.0.0
httpx>=0.27.0
discord.py[voice]>=2.3.0
python-dotenv>=1.0.0
pygame>=2.5.0
```

## 🎉 Version History

### v1.2.0 - Database Integration (2025-12-26)

Unified database storage for AI modules - error recovery and user preferences now use SQLite.

#### 🗄️ Error Recovery Database Integration
- Error patterns stored in `error_patterns` table
- Queries known solutions before recovery attempts
- Cross-references with tool patterns
- Auto-migrates JSON data, keeps JSON as backup

#### 📝 User Preferences Database Integration
- Corrections stored in `learned_corrections` table
- Preferences stored in `user_info` table
- New `get_corrections_for_tool()` for tool-specific queries
- Auto-migrates JSON data, keeps JSON as backup

---

### v1.1.1 - Integration Improvements (2025-12-26)

Fixes and enhancements for MCP and Smart Home integrations.

#### 🔌 MCP Client Fixes
- Proper MCP protocol initialization (initialize → initialized notification → tools/list)
- 60-second timeout (up from 5s) for slow servers
- Multi-line JSON response handling
- Environment variable support for server configs
- Better error messages for missing uvx/npx
- Added `get_schema()` and `cleanup()` methods

#### 🏠 Smart Home Enhancements (21 Actions)
Expanded from 6 to 21 actions with full Home Assistant support:

| Category | Actions |
|----------|---------|
| Lights | `lights_on`, `lights_off`, `set_brightness`, `set_color` |
| Media | `play_music`, `pause_music`, `stop_music`, `set_volume` |
| Climate | `set_temperature`, `set_hvac_mode` |
| Switches | `switch_on`, `switch_off` |
| Fans | `fan_on`, `fan_off`, `set_fan_speed` |
| Covers | `cover_open`, `cover_close`, `cover_stop`, `set_cover_position` |
| Scenes | `activate_scene`, `list_scenes` |
| Automations | `trigger_automation`, `list_automations` |
| Energy | `get_energy_usage` |
| State | `get_device_state`, `list_devices_by_type` |

---

### v1.1.0 - Intelligent Memory System (2025-12-26)

Major upgrade to Sakura's memory and learning capabilities with SQLite database backend.

#### 🧠 SQLite Database + JSON Transparency
- **Why**: JSON files get slow with large data, no efficient querying, file locking issues
- **Solution**: SQLite for speed + JSON exports every 5 minutes for user visibility
- **Result**: Fast queries, full-text search, infinite history, AND you can still see/edit the JSON

#### 🔍 FTS5 Full-Text Search
- Lightning-fast search across all memories using SQLite FTS5
- BM25 relevance ranking (most relevant results first)
- New `search_fts` action for instant results
- Auto-indexes new content on insert

#### 📝 User Feedback Learning
Sakura now detects and learns from your reactions:

| Feedback Type | Detection | What Sakura Learns |
|---------------|-----------|-------------------|
| **Corrections** | "No, I meant...", "Not that", "I said..." | What you actually wanted |
| **Positive** | "Perfect!", "Thanks!", "Exactly!" | Reinforces good behavior |
| **Negative** | "That's wrong", "Stop it", "Ugh" | What to avoid |
| **Preferences** | "I prefer...", "Always...", "Next time..." | Permanent preferences |

#### 🔧 Self-Healing Error Recovery
- Queries known error solutions before standard recovery
- Shows "Known fix: ..." when encountering familiar errors
- Logs successful recoveries as solutions for future use
- Error patterns tracked with occurrence counts

#### 📊 Tool Pattern Analytics
- Tracks success/failure rate per tool action
- Tracks average execution duration
- Warns before using unreliable tools (<50% success rate)
- Helps identify problematic tool configurations

#### 🎯 Correction Application
- Actually USES learned corrections (not just logs them)
- Modifies tool parameters based on past corrections
- Extracts paths, drives, depth from correction text
- Marks corrections as used (increases confidence)

#### ⏰ Confidence Decay
- Old corrections lose confidence over time (10% per week if unused)
- Prevents stale corrections from affecting behavior
- Reinforced corrections maintain high confidence
- Minimum floor prevents complete deletion

#### 🗂️ Session-Aware Corrections
- Some corrections are session-specific ("don't do that today")
- Others are permanent ("always use D: drive for games")
- Session corrections auto-cleanup when session ends

#### 🧹 Memory Cleanup/Pruning
- Configurable retention periods (exchanges: 90d, actions: 30d, errors: 60d)
- Keeps high-value data (with feedback attached)
- Removes low-confidence unused corrections
- VACUUM to reclaim disk space

#### 📈 New Memory Actions
| Action | Description |
|--------|-------------|
| `search_fts` | Fast full-text search with relevance ranking |
| `log_feedback` | Log user corrections/reactions |
| `get_corrections` | Get relevant learned corrections |
| `get_full_history` | Query infinite conversation history |
| `get_error_solutions` | Get known solutions for errors |
| `get_history_stats` | Statistics about stored history |
| `log_exchange` | Log full conversation exchange |

---

### v1.0.0 - First Stable Release (2025-12-24)

This is the first stable release of Sakura, consolidating all development work into a production-ready AI assistant with **149 tool actions** across 10 categories.

#### 🧠 AI Enhancement Suite
| Module | Description |
|--------|-------------|
| `conversation_context.py` | Rolling conversation buffer, mood detection, topic tracking |
| `task_chain.py` | Multi-step task execution with dependency tracking |
| `error_recovery.py` | Intelligent error handling with retry strategies |
| `user_preferences.py` | Learning from corrections, shortcuts, preferences |
| `suggestions.py` | Proactive suggestions based on context/time/errors |
| `intent_parser.py` | Natural language understanding with synonyms |
| `background_tasks.py` | Execute long tasks without blocking voice |

#### 🔧 Core Features
- **149 Tool Actions** across 10 tool categories
- **Real-time voice** via Gemini Live API
- **Wake word detection** with Picovoice (GPU accelerated)
- **Multi-key API rotation** with automatic failover
- **Session persistence** and resumption
- **Full async architecture** with proper cleanup
- **Connection health monitoring** with auto-reconnect

#### 🖥️ Windows Integration (46 Actions)
- App/window control, mouse/keyboard, media controls
- File operations, process management, screenshots
- Smart UI clicking, multi-monitor support
- Screen reading (OCR, UI Automation)
- Keyboard hotkeys (Ctrl+C, Alt+Tab, Win+D, etc.)
- Mouse scroll, drag and drop
- Window snapping (Win+Arrow)
- Virtual desktop control
- Power management (sleep, shutdown, restart)

#### 💻 Developer Tools (47 Actions)
- Git operations (status, add, commit, push, pull, branch, checkout, log, diff, clone, init)
- Code execution (Python, JavaScript, PowerShell, Batch)
- Package management (pip, npm, winget)
- Connection profiles (SSH, SMB, FTP/SFTP, RDP)
- SSH (OpenSSH, PuTTY), SMB shares, FTP/SFTP, RDP

#### 📅 Productivity (27 Actions)
- Reminders with Windows notifications
- Countdown timers and stopwatch
- Quick notes with tags, search, and FTS5 full-text search
- To-do lists with priorities, due dates, and completion history
- Task history tracking ("what did I complete last month?")

#### 📊 System Discovery (15 Actions)
- Hardware specs (CPU, RAM, GPU with nvidia-smi)
- Multi-monitor detection with primary flag
- Installed/running apps, network info

#### 🧠 Memory System (16 Actions)
- Auto-logging of all actions
- Location/script tracking
- Cross-category search

#### 🌐 Integrations
- Web search (DuckDuckGo) & URL fetching
- Discord (text + voice)
- Smart Home (Home Assistant)
- MCP Client for extended tools

## 📄 License

MIT License - See LICENSE file

## 🤝 Contributing

Contributions welcome! Please read CONTRIBUTING.md first.

---

**Sakura** 🌸 - Your Ultimate Windows AI Assistant

*Built with ❤️ using Google Gemini Live API*
