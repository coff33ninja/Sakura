# Copilot Instructions for Sakura AI Assistant

## Project Overview
Sakura is a fully autonomous Windows AI assistant featuring Gemini Live API voice interaction, complete Windows automation (211 tool actions), self-learning memory (SQLite + FTS5), multi-step task execution, and error recovery with user feedback learning.

## Critical Development Rules

### Rule #1: ALL IMPORTS MUST BE USED
⚠️ **CRITICAL** - Every import loaded MUST be used. Unused imports indicate forgotten functionality. If you find unused imports:
1. Check if the import is truly unused
2. Either remove it OR implement the missing functionality
3. Never ignore unused imports - they signal incomplete features

### Rule #2: Async Everything (Strict Pattern)
- **ALL tools**: Use `asyncio.Lock()` for thread safety
- **File I/O**: ALWAYS use `aiofiles`, never blocking I/O
- **Blocking operations**: Use `asyncio.to_thread()` to avoid blocking event loop
- **Database**: Use `aiosqlite` (already imported where needed)
- Never mix sync/async - be consistent in each module

### Rule #3: Python 3.12 Required
- Only tested version for this project
- Maintain 3.8+ compatibility only if cross-version work required
- Use 3.12 features where beneficial (e.g. `typing` improvements)
- Test with Python 3.12 interpreter in the venv

### Rule #4: Type Hints Everywhere
- All functions/methods must have complete type hints
- Use `from typing import ...` for complex types
- Maintain type hinting consistency across modules
- Use `mypy` for type checking during development

### Rule #5: Comprehensive Docstrings
- Every class, method, and function must have a docstring
- Follow Google-style or NumPy-style docstrings consistently
- Include parameter and return type descriptions
- Update docstrings when functionality changes

### Rule #6: Follow the version control workflow
- Follow CHANGELOG.md for versioning
## Architecture Overview

### Core Component Lifecycle
```
main.py (AIGirlfriend class)
├─ AudioManager: Audio I/O with PyAudio (sample_rate: 24000, chunk_size: 1024)
├─ WakeWordDetector: Porcupine (keyword-based, custom training via Picovoice)
├─ GeminiVoiceClient: Gemini Live API (voice_name: Aoede/Charon/Fenrir/Kore/Puck)
├─ ToolRegistry: Unified tool execution system
├─ ConversationContext: Sliding window of ~20 exchanges with SQLite persistence
├─ TaskChain: Multi-step request parsing and execution
├─ ErrorRecovery: Intelligent error categorization with database knowledge store
├─ UserPreferences: Learned corrections, shortcuts, user info (database-backed)
├─ SuggestionEngine: Proactive suggestions based on context
├─ IntentParser: Fuzzy intent matching with synonyms
└─ BackgroundTaskManager: Async background task orchestration
```

### Tool System Design
- **Base class**: `tools/base.py` → `BaseTool` (async/aio only)
- **Execution**: `tool_registry.execute(tool_name, action, kwargs)` returns `ToolResult`
- **Categories**: Windows, Developer, Productivity, Memory, System, Smart Home, Web, Discord, MCP, Meta
- **Tool addition**: Subclass `BaseTool`, implement `execute()` and `get_schema()`, register in `tools/__init__.py`

## Key Data Flows

### Voice Interaction Flow
1. Audio → AudioManager.listen() → bytes
2. Wake word detection (Porcupine) or continuous listening
3. Audio sent to GeminiVoiceClient.send_audio_chunk()
4. Gemini parses intent, calls tools via function_calling
5. ToolRegistry.execute() runs the tool
6. Response audio from GeminiVoiceClient.get_response_audio()
7. AudioManager.play() outputs audio

### Multi-Step Task Execution
1. TaskChain.detect_chain() checks for patterns: "and then", "after that", ",", ";"
2. TaskChain.parse_chain_request() splits into subtasks
3. TaskChain.execute() runs with dependency management and result mapping
4. ErrorRecovery catches failures, checks database for known solutions
5. ConversationContext stores completed chain for reference

### Memory System
- **Storage**: SQLite database (`sakura.db`) with FTS5 full-text search
- **Auto-export**: JSON backup every 5 minutes to `sakura_memory.json`
- **Tables**: error_patterns, user_info, learned_corrections, tool_usage, task_history, memory_items, reminders, todos, notes, connections
- **Access pattern**: All queries are async via `aiosqlite`

## Common Patterns & Examples

### Adding a New Tool
```python
# tools/example/example.py
from tools.base import BaseTool, ToolResult, ToolStatus

class ExampleTool(BaseTool):
    name = "example"
    description = "Description of what this tool does"
    
    async def execute(self, action: str, **kwargs) -> ToolResult:
        try:
            # Tool implementation here
            return ToolResult(ToolStatus.SUCCESS, data=result, message="Success")
        except Exception as e:
            return ToolResult(ToolStatus.ERROR, error=str(e))
    
    def get_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {...}}
```

### Working with Configuration
```python
# AppConfig uses dataclass defaults from environment variables
config = AppConfig()  # Loads from env: GEMINI_API_KEY, PICOVOICE_ACCESS_KEY, etc.
```

### Error Handling with Recovery
```python
# Errors categorized by ErrorRecovery
recovery_result = await error_recovery.handle_error(
    tool_name="windows",
    error_message="Access denied",
    context={"action": "write_file"}
)
# Returns RecoveryResult with known_solution from database if available
```

### Async File Operations
```python
# ALWAYS use aiofiles, never blocking I/O
async with aiofiles.open(filepath, 'r') as f:
    content = await f.read()
```

## Testing Patterns
- **Framework**: pytest with `pytest-asyncio` and `hypothesis` (property-based)
- **Run**: `pytest tests/` (auto-detects async)
- **Coverage**: Tests organized in `tests/modules/`, `tests/tools/`, `tests/properties/`
- **Markers**: `@pytest.mark.slow` for slow tests, `@pytest.mark.integration` for integration tests

## Integration Points

### External APIs
- **Gemini Live**: `google-genai` SDK (voice audio streaming)
- **Picovoice Porcupine**: Wake word detection (custom models via console.picovoice.ai)
- **PyAudio**: System audio I/O
- **Discord.py**: Bot integration with voice support
- **paramiko**: SSH connections with database caching

### MCP Integration
- **MCPClient tool**: Discovers and calls MCP servers (60s timeout, automatic cleanup)
- **Use case**: Extend Sakura with external tool servers

## Common Gotchas
- **Config defaults**: Check environment variables - `GEMINI_API_KEY`, `PICOVOICE_ACCESS_KEY`, `ASSISTANT_NAME`
- **Audio thread safety**: AudioManager handles PyAudio in thread-safe manner
- **Tool timeout**: No global timeout - tools may hang; implement timeouts per tool
- **Database locks**: Use `asyncio.Lock()` for concurrent access to `sakura.db`
- **Script sandbox**: All user-generated scripts saved to `~/Documents/{ASSISTANT_NAME}/scripts/`

## Workflows

### Local Testing
```bash
python -m pytest tests/ -v                    # Run all tests
python -m pytest tests/modules/ -m "not slow" # Skip slow tests
python main.py                                # Start Sakura
```

### Adding a New Module
1. Create `modules/new_module.py` with async design
2. Add to `modules/__init__.py` exports
3. Add tests in `tests/modules/test_new_module.py` using `pytest-asyncio`
4. Integrate into `main.py` (AIGirlfriend class) if core functionality

## Project-Specific Conventions
- **Logging**: `logging.info()` for flow, `.warning()` for issues, `.error()` for failures
- **Emoji conventions**: Used in logs (🔥 init, 🧠 memory, 🔧 tools, etc.)
- **Timestamps**: ISO format in database, logs use Python logging defaults
- **Result patterns**: Always return `ToolResult` from tool execute(), `RecoveryResult` from recovery
- **JSON exports**: 5-minute interval backups, keys snake_case
