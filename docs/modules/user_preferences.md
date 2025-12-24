# User Preferences Module

**File:** `modules/user_preferences.py`

Learns from user corrections and remembers preferences.

## Features

- Correction learning ("No, I meant...")
- Preference detection ("Always use X")
- Shortcut system ("My project = path")
- Preference inference from actions

## Data Types

### Correction
```python
@dataclass
class Correction:
    trigger_phrase: str      # What was misunderstood
    intended_tool: str       # Correct tool
    intended_action: str     # Correct action
    intended_args: Dict      # Correct arguments
    use_count: int
    confidence: float        # Decreases if overridden
```

### Preference
```python
@dataclass
class Preference:
    category: str    # shell, browser, editor
    key: str         # default_shell
    value: Any       # powershell
    source: str      # explicit, inferred, correction
```

### Shortcut
```python
@dataclass
class Shortcut:
    phrase: str       # "my project"
    expansion: str    # "E:\\Projects\\Main"
    context: str      # path, app, url
    use_count: int
```

## Detection Patterns

### Corrections
- "No, I meant..."
- "Actually, use..."
- "Not that, the other..."
- "Wrong one"
- "That's not right"

### Preferences
- "Always use X"
- "I prefer X over Y"
- "Default to X"
- "Never use X"

### Shortcuts
- "Remember that X is Y"
- "X means Y"
- "When I say X, I mean Y"

## Storage

Data stored in: `user_preferences.json`

```json
{
  "corrections": [...],
  "preferences": {
    "shell": "powershell",
    "browser": "firefox"
  },
  "shortcuts": {
    "my project": "E:\\Projects\\Main"
  }
}
```

## Usage

```python
prefs = UserPreferences()
await prefs.initialize()

# Check for correction
correction = await prefs.find_correction("open browser")
if correction:
    # Use corrected action instead

# Get preference
shell = await prefs.get_preference("shell")

# Expand shortcut
path = await prefs.expand_shortcut("my project")
# Returns: "E:\\Projects\\Main"

# Learn from correction
await prefs.learn_correction(
    trigger="open browser",
    tool="windows",
    action="open_app",
    args={"app": "firefox"}
)
```
