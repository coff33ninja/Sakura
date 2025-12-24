# Gemini Client Module

**File:** `modules/gemini_client.py`

Handles Gemini Live API interactions with automatic key rotation and connection health.

## Features

- Real-time voice streaming
- Automatic key rotation on rate limits
- Connection health monitoring
- Auto-reconnect on drops
- Tool/function calling support

## Configuration

```python
client = GeminiVoiceClient(
    model="gemini-2.0-flash-exp",
    voice_name="Aoede"
)
```

## Voice Options

| Voice | Gender | Description |
|-------|--------|-------------|
| Aoede | Female | Warm, friendly (default) |
| Kore | Female | Soft, gentle |
| Charon | Male | Deep, calm |
| Fenrir | Male | Energetic |
| Puck | Neutral | Playful |

## Connection Health

Monitors connection status:
- Last activity timestamp
- Consecutive error count
- Auto-reconnect on timeout (30 seconds)
- Max consecutive errors: 10

## Key Rotation

Integrates with `APIKeyManager`:
- Automatic failover on rate limits
- Key health tracking
- Usage statistics

## Usage

```python
client = GeminiVoiceClient(model="gemini-2.0-flash-exp")

# Initialize with system prompt and tools
await client.initialize(
    system_prompt="You are Sakura...",
    tools=[tool_declarations]
)

# Send audio
await client.send_audio(audio_chunk)

# Receive responses
async for response in client.receive():
    if response.audio:
        play_audio(response.audio)
    if response.text:
        print(response.text)
    if response.tool_call:
        result = await execute_tool(response.tool_call)
        await client.send_tool_response(result)

# Cleanup
await client.cleanup()
```

## Auto-Reconnect

```python
# Connection check runs automatically
# If no activity for 30 seconds, reconnects

# Manual reconnect
await client.reconnect()
```

## Tool Calling

Pass tool declarations to enable function calling:

```python
tools = [
    {
        "name": "windows",
        "description": "Windows automation",
        "parameters": {...}
    }
]

await client.initialize(system_prompt, tools=tools)
```
