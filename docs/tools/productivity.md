# Productivity Tool

**File:** `tools/productivity/manager.py`  
**Actions:** 23

Reminders, timers, notes, and to-do lists with Windows notifications.

## Actions

### Reminders (4)
| Action | Description |
|--------|-------------|
| `set_reminder` | Create reminder with notification |
| `list_reminders` | List all reminders |
| `cancel_reminder` | Cancel a reminder |
| `snooze_reminder` | Snooze triggered reminder |

### Timers (6)
| Action | Description |
|--------|-------------|
| `start_timer` | Start countdown timer |
| `stop_timer` | Stop/cancel timer |
| `list_timers` | List active timers |
| `get_timer_status` | Get specific timer status |
| `start_stopwatch` | Start stopwatch |
| `stop_stopwatch` | Stop stopwatch, get elapsed time |

### Notes (6)
| Action | Description |
|--------|-------------|
| `create_note` | Create new note |
| `get_note` | Get note by ID |
| `update_note` | Update note content |
| `delete_note` | Delete note |
| `list_notes` | List all notes |
| `search_notes` | Search notes by content/tags |

### To-Do (5)
| Action | Description |
|--------|-------------|
| `add_todo` | Add to-do item |
| `complete_todo` | Mark item complete |
| `update_todo` | Update item details |
| `delete_todo` | Delete item |
| `list_todos` | List all items |

### Windows Integration (2)
| Action | Description |
|--------|-------------|
| `open_alarms_app` | Open Windows Alarms & Clock |
| `show_notification` | Show Windows toast notification |

## Data Storage

All data stored in: `~/Documents/{ASSISTANT_NAME}/productivity/`

- `reminders.json` - Reminder data
- `timers.json` - Timer data
- `notes.json` - Notes data
- `todos.json` - To-do data

## Data Models

### Reminder
```python
@dataclass
class Reminder:
    id: str
    title: str
    message: str
    trigger_time: str  # ISO format
    status: str        # pending, triggered, dismissed, snoozed
    repeat: str        # daily, weekly, monthly, none
```

### TodoItem
```python
@dataclass
class TodoItem:
    id: str
    title: str
    description: str
    priority: str      # low, medium, high, urgent
    due_date: str
    completed: bool
    tags: List[str]
```

## Example Usage

```python
# Set reminder for 5 minutes
await tool.execute("set_reminder", 
    title="Break time",
    message="Take a 5 minute break",
    minutes=5
)

# Start 25 minute pomodoro timer
await tool.execute("start_timer", name="Pomodoro", minutes=25)

# Create note
await tool.execute("create_note",
    title="Meeting Notes",
    content="Discussed project timeline...",
    tags=["work", "meeting"]
)

# Add high priority task
await tool.execute("add_todo",
    title="Review PR",
    priority="high",
    due_date="2025-12-25"
)
```
