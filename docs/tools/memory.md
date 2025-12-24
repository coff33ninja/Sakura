# Memory Store Tool

**File:** `tools/memory/store.py`  
**Actions:** 16

Persistent memory for user info, facts, preferences, and action history.

## Actions

| Action | Description |
|--------|-------------|
| `remember` | Store a fact about the user |
| `recall` | Recall stored facts |
| `forget` | Remove a stored fact |
| `set_user_info` | Set user info (name, preferences) |
| `get_user_info` | Get user info |
| `set_date` | Store important date (birthday, etc.) |
| `get_dates` | Get stored dates |
| `store` | Generic key-value storage |
| `get_action_log` | Get history of actions performed |
| `log_conversation` | Log conversation summary |
| `get_conversations` | Get conversation history |
| `log_script` | Log created script |
| `get_scripts` | Get list of created scripts |
| `log_topic` | Track discussed topic |
| `get_stats` | Get session statistics |
| `search_all` | Search across all memory categories |

## Memory Categories

```python
memories = {
    "user_info": {},          # Name, preferences
    "facts": [],              # Things user has told Sakura
    "preferences": {},        # User likes/dislikes
    "important_dates": {},    # Birthdays, anniversaries
    "conversation_notes": [], # Notable moments
    "action_log": [],         # History of actions
    "conversation_history": [],# Conversation summaries
    "scripts_created": [],    # Scripts made with paths
    "topics_discussed": {},   # Topics and frequency
    "session_stats": {}       # Usage statistics
}
```

## Storage

Data stored in: `sakura_memory.json` (workspace root)

## Example Usage

```python
# Remember user's name
await tool.execute("set_user_info", key="name", value="John")

# Store a fact
await tool.execute("remember", fact="User prefers dark mode")

# Recall facts about a topic
result = await tool.execute("recall", query="preferences")

# Store important date
await tool.execute("set_date", 
    name="birthday",
    date="1990-05-15",
    description="User's birthday"
)

# Search everything
result = await tool.execute("search_all", query="python")
# Searches: facts, notes, scripts, topics, action_log

# Get session stats
result = await tool.execute("get_stats")
# Returns: total_sessions, total_actions, first_session, last_session
```

## Auto-Logging

The memory tool automatically logs:
- Every tool action with timestamp
- Scripts created with full paths
- Topics discussed with frequency
- Session statistics
