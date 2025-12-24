# Sakura Modules Documentation

Modules are the core components that power Sakura's AI capabilities, voice interaction, and system management.

## Module Categories

### AI Enhancement Suite
| Module | Description |
|--------|-------------|
| [conversation_context](conversation_context.md) | Rolling conversation buffer, mood/topic tracking |
| [task_chain](task_chain.md) | Multi-step task execution |
| [error_recovery](error_recovery.md) | Intelligent retry strategies |
| [user_preferences](user_preferences.md) | Learning from corrections |
| [suggestions](suggestions.md) | Proactive suggestions |
| [intent_parser](intent_parser.md) | Natural language understanding |
| [background_tasks](background_tasks.md) | Non-blocking task execution |

### Core Infrastructure
| Module | Description |
|--------|-------------|
| [gemini_client](gemini_client.md) | Gemini Live API client |
| [api_key_manager](api_key_manager.md) | Multi-key rotation |
| [audio_manager](audio_manager.md) | Audio I/O handling |
| [session_manager](session_manager.md) | Session persistence |
| [wake_word_detector](wake_word_detector.md) | Wake word detection |
| [persona](persona.md) | Personality definitions |
| [config](config.md) | Configuration management |

## Architecture Rules

1. **Async Everything** - All modules use `asyncio.Lock()` for thread safety
2. **aiofiles** - All file I/O uses aiofiles
3. **All Imports Used** - No unused imports (Rule #1)
4. **Graceful Degradation** - Modules fail gracefully when optional features unavailable
5. **Python 3.12** - Only tested version

## Module Lifecycle

```python
# Initialize
await module.initialize()

# Use
result = await module.some_method()

# Cleanup
await module.cleanup()
```
