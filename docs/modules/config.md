# Config Module

**File:** `modules/config.py`

Centralized configuration management.

## Configuration Sources

1. Environment variables (`.env`)
2. Default values

## Key Settings

```python
# API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.0-flash-exp"

# Assistant
ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "Sakura")
SAKURA_PERSONALITY = os.getenv("SAKURA_PERSONALITY", "friendly")

# Voice
VOICE_NAME = os.getenv("VOICE_NAME", "Aoede")

# Wake Word
PICOVOICE_ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY")
WAKE_WORD_KEYWORDS = os.getenv("WAKE_WORD_KEYWORDS", "jarvis")

# Integrations
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
HOME_ASSISTANT_URL = os.getenv("HOME_ASSISTANT_URL")
HOME_ASSISTANT_TOKEN = os.getenv("HOME_ASSISTANT_TOKEN")
```

## .env Example

```env
GEMINI_API_KEY=your_key
ASSISTANT_NAME=Sakura
SAKURA_PERSONALITY=friendly
VOICE_NAME=Aoede
WAKE_WORD_KEYWORDS=jarvis
PICOVOICE_ACCESS_KEY=your_key
```

## Async Config Loader

`modules/async_config_loader.py` provides async config loading with validation.
