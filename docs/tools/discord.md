# Discord Tool

**File:** `tools/discord/bot.py`  
**Actions:** 5

Discord integration for text and voice channels.

## Actions

| Action | Description |
|--------|-------------|
| `send_message` | Send message to channel |
| `read_messages` | Read recent messages |
| `list_channels` | List server channels |
| `list_guilds` | List joined servers |
| `join_voice` | Join voice channel |

## Configuration

Set in `.env`:
```env
DISCORD_BOT_TOKEN=your_bot_token
```

## Architecture

- **REST API** - Used for text operations (httpx)
- **discord.py** - Used for voice channel support

## Voice Support

Requires additional packages:
```bash
pip install discord.py[voice] PyNaCl
```

When voice is enabled, Sakura can:
- Join voice channels
- Stream audio to Discord
- Pipe voice responses to channel

## Example Usage

```python
# Send message
await tool.execute("send_message",
    channel_id="123456789",
    content="Hello from Sakura!"
)

# Read last 10 messages
result = await tool.execute("read_messages",
    channel_id="123456789",
    limit=10
)

# Join voice channel
await tool.execute("join_voice",
    guild_id="123456789",
    channel_id="987654321"
)
```

## Bot Permissions

Required Discord bot permissions:
- Send Messages
- Read Message History
- Connect (for voice)
- Speak (for voice)
