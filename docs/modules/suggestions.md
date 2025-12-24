# Suggestions Module

**File:** `modules/suggestions.py`

Proactive suggestions based on context, time, history, and patterns.

## Features

- Time-based suggestions (morning, night, lunch)
- Context-based suggestions (after certain actions)
- Error-based suggestions (after failures)
- Follow-up suggestions
- Acceptance tracking

## Suggestion Types

```python
class SuggestionType(Enum):
    TIME_BASED = "time_based"
    CONTEXT_BASED = "context_based"
    HISTORY_BASED = "history_based"
    ERROR_BASED = "error_based"
    PROACTIVE = "proactive"
    FOLLOW_UP = "follow_up"
```

## Time-Based Rules

| Time | Suggestion |
|------|------------|
| 6-10 AM | "Good morning! Check calendar or news?" |
| 11 PM-2 AM | "It's late. Save work and rest?" |
| 12-1 PM | "Lunch break. Step away?" |
| 5-6 PM | "End of day. Review tasks?" |

## Context-Based Rules

| Context | Suggestion |
|---------|------------|
| Python file open | "Run tests?" |
| Git repo | "Check git status?" |
| Large file | "Create backup?" |
| Browser research | "Save notes?" |

## Error-Based Suggestions

| Error Type | Suggestion |
|------------|------------|
| Permission denied | "Try running as admin" |
| File not found | "Search for similar files?" |
| Network error | "Check internet connection" |
| Timeout | "Try again or use alternative" |

## Suggestion Data

```python
@dataclass
class Suggestion:
    id: str
    type: SuggestionType
    priority: SuggestionPriority
    message: str
    action_tool: Optional[str]
    action_name: Optional[str]
    action_args: Dict
    cooldown_minutes: int = 30
    times_shown: int
    times_accepted: int
    times_rejected: int
```

## Usage

```python
engine = SuggestionEngine()
await engine.initialize()

# Get suggestions for current context
suggestions = await engine.get_suggestions(
    context={"current_file": "main.py", "recent_action": "git_commit"}
)

# Record feedback
await engine.record_feedback(
    suggestion_id="morning_greeting",
    accepted=True
)

# Check if suggestion should be shown (cooldown)
if await engine.should_show(suggestion_id):
    # Show suggestion
```

## Cooldown System

- Default cooldown: 30 minutes
- Prevents suggestion spam
- Tracks last shown time per suggestion
- Respects user rejection patterns
