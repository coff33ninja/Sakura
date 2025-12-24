# Session Manager Module

**File:** `modules/session_manager.py`

Manages session persistence and resumption.

## Features

- Session handle saving
- 2-hour session resumption
- Metadata storage
- Automatic expiration cleanup

## Session Data

```python
session_data = {
    "handle": "session_handle_string",
    "timestamp": "2025-12-24T10:00:00",
    "metadata": {
        "user": "John",
        "personality": "friendly"
    }
}
```

## Usage

```python
manager = SessionManager(session_file="gf_session.txt")

# Save session
await manager.save_session_handle(
    handle="abc123...",
    metadata={"personality": "friendly"}
)

# Load previous session
handle = await manager.load_session_handle()
if handle:
    # Resume session
    await client.initialize(resume_handle=handle)

# Clear session
await manager.clear_session()

# Get session info
info = await manager.get_session_info()
```

## Session Expiration

- Sessions valid for 2 hours (Gemini API limit)
- Automatic cleanup of expired sessions
- Timestamp validation on load

## Storage

Session saved to: `gf_session.txt`

```json
{
  "handle": "session_handle...",
  "timestamp": "2025-12-24T10:00:00",
  "metadata": {}
}
```

## Thread Safety

All operations use `asyncio.Lock()` for thread-safe access.
