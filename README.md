# 🌸 Sakura - Ultimate Windows AI Assistant

**Sakura** is a fully autonomous AI assistant with real-time voice interaction, complete Windows control, self-learning memory, and script generation capabilities. She can control your PC, remember everything, create and execute scripts, and learn about your system over time.

> *"Hey Sakura, find my project files and create a backup script"* - She'll search all drives, remember the locations, write the script, and execute it.

## ✨ Key Features

### 🎙️ Real-Time Voice Conversation
- **Gemini Live API** - Natural, low-latency voice interaction
- **Interruption support** - Talk naturally, interrupt anytime
- **Multiple voices** - Aoede, Kore, Leda, Fenrir
- **Configurable personalities** - Flirty, Friendly, Romantic, Tsundere

### 🖥️ Complete Windows Control (29 Actions)
- **Run commands** - PowerShell, CMD, any command
- **App control** - Open, close, focus, minimize, maximize windows
- **Mouse control** - Move cursor, click, double-click
- **Media control** - Play, pause, next, prev, volume up/down/mute
- **File operations** - Read, write, delete files and folders
- **Search** - Find files across ALL drives
- **Screenshots** - Capture screen anytime
- **Clipboard** - Get/set clipboard content
- **Process management** - List, kill processes
- **System info** - Memory, CPU, hardware stats

### 📝 Script Generation & Execution
- **Sandbox folder** - All scripts saved to `~/Documents/Sakura/scripts/`
- **Multiple languages** - PowerShell, Python, Batch, JavaScript, VBScript
- **Auto-headers** - Timestamp and metadata in every script
- **Safe execution** - Scripts always saved for user review
- **Visible terminals** - Can launch scripts in new terminal windows

### 🧠 Self-Learning Memory System (16 Actions)
- **Auto-logging** - Every action recorded with timestamp
- **Location memory** - Remembers file paths, app locations discovered
- **Script tracking** - Logs all scripts created with paths
- **Conversation history** - Summaries of past conversations
- **Topic tracking** - What you've discussed and how often
- **Cross-search** - Search across ALL memory categories
- **Session stats** - Track usage over time

### 🔍 System Discovery (15 Actions)
- **PC info** - Computer name, username, OS
- **Hardware** - CPU, RAM, GPU, drives
- **Installed apps** - Search by category (browsers, dev, media, games)
- **Running processes** - See what's active
- **Network info** - Adapters, IPs, DNS
- **Folder exploration** - Browse any directory
- **App paths** - Find where apps are installed

### 🌐 Web & Integrations
- **Web search** - DuckDuckGo instant answers
- **URL fetching** - Extract content from websites
- **Discord** - Send messages, join voice channels
- **Smart Home** - Home Assistant integration
- **MCP Client** - Connect to Model Context Protocol servers

## 🚀 Quick Start

### Prerequisites
- **Python 3.12** (only tested version)
- Windows 10/11
- Microphone and speakers
- Gemini API key(s)

### Installation

```bash
# Clone the repository
git clone https://github.com/coff33ninja/sakura-ai.git
cd sakura-ai

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file:

```env
# Required - Gemini API keys (supports multiple for rotation)
GEMINI_API_KEY=your_primary_key
GEMINI_API_KEY_2=your_backup_key
GEMINI_API_KEY_3=another_backup_key

# Personality: flirty, friendly, romantic, tsundere
SAKURA_PERSONALITY=friendly

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
.\.venv\Scripts\python main.py
```

## 🎯 What Can Sakura Do?

### Voice Commands Examples

| You Say | Sakura Does |
|---------|-------------|
| "What's my PC name?" | Discovers and remembers system info |
| "Find all Python files" | Searches all drives, remembers locations |
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
| `windows` | 29 | Full Windows control |
| `system_info` | 15 | System discovery |
| `memory` | 16 | Persistent memory |
| `web_search` | 1 | DuckDuckGo search |
| `web_fetch` | 1 | URL content extraction |
| `discord` | 5 | Discord integration |
| `smart_home` | 6 | Home Assistant |
| `mcp_client` | 3 | MCP server connection |

**Total: 76 tool actions**

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
│   └── session_manager.py  # Session persistence
├── tools/
│   ├── base.py             # Base tool classes
│   ├── windows/            # Windows automation (29 actions)
│   ├── system_info/        # System discovery (15 actions)
│   ├── memory/             # Memory system (16 actions)
│   ├── web/                # Web search & fetch
│   ├── discord/            # Discord integration
│   ├── smart_home/         # Home Assistant
│   └── mcp/                # MCP client
├── sakura_memory.json      # Persistent memory storage
├── requirements.txt        # Python dependencies
└── .env                    # Configuration (create this)
```

## 🔧 Configuration Options

### Personality Modes

| Mode | Description |
|------|-------------|
| `friendly` | Warm, helpful assistant (default) |
| `flirty` | Playful, affectionate girlfriend |
| `romantic` | Sweet, caring partner (PG-13) |
| `tsundere` | Classic anime tsundere |

### Voice Options

Available voices: `Aoede`, `Kore`, `Leda`, `Fenrir`

### Script Sandbox

All scripts are saved to: `C:\Users\<YourName>\Documents\Sakura\scripts\`

Organized by type:
- `/powershell/` - PowerShell scripts (.ps1)
- `/python/` - Python scripts (.py)
- `/batch/` - Batch files (.bat)
- `/javascript/` - Node.js scripts (.js)
- `/vbscript/` - VBScript files (.vbs)

## 🧠 Memory System

Sakura automatically remembers:

| Category | What's Stored |
|----------|---------------|
| `action_log` | Every tool action with timestamp |
| `discovered_locations` | File paths, app locations found |
| `scripts_created` | Scripts made with full paths |
| `conversation_history` | Conversation summaries |
| `topics_discussed` | Topics and frequency |
| `user_info` | Your name, preferences |
| `facts` | Things you've told her |
| `important_dates` | Birthdays, anniversaries |
| `session_stats` | Usage statistics |

## 🔒 Security Notes

- Scripts are always saved before execution for review
- Sensitive environment variables are hidden in memory
- API keys stored only in `.env` file
- No conversation audio is stored locally

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

### v1.4 - Ultimate Windows AI
- 29 Windows automation actions
- 15 System discovery actions
- 16 Memory actions with auto-logging
- Script sandbox with multi-language support
- Location memory for file/app discovery
- Cross-category memory search
- Proactive execution behavior

### v1.3 - Tools & Discord Voice
- Full tool system with function calling
- Discord text and voice integration
- Web search and URL fetching
- Smart home integration
- MCP client support

### v1.2 - Audio & SDK Fix
- Google GenAI SDK 1.x compatibility
- Correct audio sample rates (16kHz in, 24kHz out)
- Async audio queue for smooth playback

### v1.1 - Async Architecture
- Full async/aio implementation
- Multi-key API rotation
- Session persistence

## 📄 License

MIT License - See LICENSE file

## 🤝 Contributing

Contributions welcome! Please read CONTRIBUTING.md first.

---

**Sakura** 🌸 - Your Ultimate Windows AI Assistant

*Built with ❤️ using Google Gemini Live API*
