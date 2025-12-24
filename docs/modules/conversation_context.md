# Conversation Context Module

**File:** `modules/conversation_context.py`

Maintains rolling buffer of conversation exchanges for better context awareness.

## Features

- Rolling buffer of last N exchanges (default: 20)
- Mood detection from user input
- Topic extraction and tracking
- Session persistence
- Context injection into system prompt

## Classes

### ConversationExchange
```python
@dataclass
class ConversationExchange:
    timestamp: str
    user_input: str
    ai_response: str
    tools_used: List[str]
    tool_results: List[Dict]
    mood_indicators: List[str]
    topics: List[str]
```

### ConversationContext
Main class managing the conversation buffer.

## Mood Detection

Detects mood indicators from user input:
- **Positive**: thanks, great, awesome, love, perfect
- **Frustrated**: ugh, damn, frustrated, annoying, why won't
- **Urgent**: asap, urgent, quickly, hurry, emergency
- **Confused**: confused, don't understand, what do you mean
- **Casual**: hey, hi, hello, sup, yo

## Topic Extraction

Extracts topics from exchanges using keyword matching:
- Files, folders, apps, scripts
- Music, video, browser
- Settings, system, network
- And more...

## Usage

```python
context = ConversationContext(max_exchanges=20)
await context.initialize()

# Add exchange
await context.add_exchange(
    user_input="Open Chrome",
    ai_response="Opening Chrome now",
    tools_used=["windows"],
    tool_results=[{"status": "success"}]
)

# Get context summary for system prompt
summary = await context.get_context_summary()

# Get recent topics
topics = context.get_current_topics()
```

## Context Summary

Returns formatted string for injection into system prompt:
- Recent topics discussed
- User mood indicators
- Pending tasks
- Recent failures
