# Error Recovery Module

**File:** `modules/error_recovery.py`

Intelligent error handling with retry strategies and user feedback.

## Features

- Error categorization
- Automatic retry with exponential backoff
- User-friendly suggestions
- Cooldown for repeated failures
- Error history for learning

## Error Categories

```python
class ErrorCategory(Enum):
    TRANSIENT = "transient"      # Retry automatically
    PERMISSION = "permission"    # Ask user for permission
    NOT_FOUND = "not_found"      # Search alternatives
    RATE_LIMIT = "rate_limit"    # Wait and retry
    INVALID_INPUT = "invalid"    # Clarify with user
    PERMANENT = "permanent"      # Give up gracefully
    UNKNOWN = "unknown"          # Uncategorized
```

## Retry Strategies

### Transient Errors
- Network timeouts, connection errors
- Retry 3x with exponential backoff
- Base delay: 1 second, max: 30 seconds

### Rate Limit Errors
- API quota exceeded
- Retry 5x with longer delays
- Rotate to backup resources if available

### Permission Errors
- Access denied, elevation required
- Ask user for permission
- Suggest running as admin

### Not Found Errors
- File/app not found
- Search for alternatives
- Suggest similar items

## Retry Configuration

```python
@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay_ms: int = 1000
    max_delay_ms: int = 30000
    exponential_base: float = 2.0
    jitter: bool = True
```

## Usage

```python
recovery = ErrorRecovery()
await recovery.initialize()

# Attempt with recovery
result = await recovery.attempt_with_recovery(
    tool_name="windows",
    action="open_app",
    args={"app": "chrome"},
    executor=execute_tool
)

if not result.success:
    print(f"Failed: {result.error}")
    print(f"Suggestion: {result.suggestion}")
    print(f"Alternatives: {result.alternatives}")
```

## Cooldown System

Prevents repeated failures from overwhelming the system:
- Tracks error frequency per tool/action
- Applies cooldown after threshold
- Gradually reduces cooldown on success
