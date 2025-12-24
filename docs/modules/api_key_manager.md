# API Key Manager Module

**File:** `modules/api_key_manager.py`

Manages multiple API keys with automatic rotation and failover.

## Features

- Multiple key support (up to 20)
- Automatic rotation on rate limits
- Key health monitoring
- Usage statistics
- Persistent key state

## Key Status

```python
class KeyStatus(Enum):
    ACTIVE = "active"
    RATE_LIMITED = "rate_limited"
    EXPIRED = "expired"
    INVALID = "invalid"
    DISABLED = "disabled"
```

## API Key Data

```python
@dataclass
class APIKey:
    key: str
    name: str
    status: KeyStatus
    last_used: Optional[datetime]
    rate_limit_reset: Optional[datetime]
    usage_count: int
    error_count: int
    max_errors: int = 5
```

## Configuration

Set keys in `.env`:
```env
GEMINI_API_KEY=primary_key
GEMINI_API_KEY_2=backup_key
GEMINI_API_KEY_3=another_backup
# ... up to GEMINI_API_KEY_20
```

## Usage

```python
manager = APIKeyManager()
await manager.load_keys()

# Get current active key
key = await manager.get_current_key()

# Report rate limit
await manager.report_rate_limit(key)
# Automatically rotates to next available key

# Report error
await manager.report_error(key, "Connection failed")
# After max_errors, key is marked invalid

# Get statistics
stats = await manager.get_stats()
```

## Rotation Logic

1. Try current key
2. On rate limit → mark key, set reset time, rotate
3. On error → increment error count
4. After max errors → mark invalid
5. Rotate to next ACTIVE key
6. If no active keys → wait for rate limit reset

## Key Recovery

Rate-limited keys automatically recover:
- Checks `rate_limit_reset` timestamp
- Reactivates when reset time passes
- Resets error count on successful use

## Persistence

Key state saved to `api_keys.json`:
- Status per key
- Usage counts
- Error counts
- Rate limit reset times
