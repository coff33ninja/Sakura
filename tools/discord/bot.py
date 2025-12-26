"""
Discord Bot for Sakura
Allows Sakura to send messages and join voice channels - fully async
Supports both REST API and discord.py for voice
"""
import asyncio
import os
import io
import logging
from typing import Dict, Any, Optional, List, Callable
import httpx
from ..base import BaseTool, ToolResult, ToolStatus

# Try to import discord.py for voice support
try:
    import discord
    from discord.ext import commands
    DISCORD_PY_AVAILABLE = True
except ImportError:
    DISCORD_PY_AVAILABLE = False
    logging.warning("discord.py not installed - voice features disabled. Install with: pip install discord.py[voice]")


class DiscordBot(BaseTool):
    """Discord bot integration for Sakura - async with voice support"""

    name = "discord"
    description = "Send messages, read channels, and join voice chat on Discord"

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("DISCORD_BOT_TOKEN")
        self.client: Optional[httpx.AsyncClient] = None
        self._lock = asyncio.Lock()
        self.connected = False
        self.base_url = "https://discord.com/api/v10"

        # Voice support via discord.py
        self.bot: Optional[commands.Bot] = None
        self.voice_client: Optional[Any] = None
        self.voice_enabled = DISCORD_PY_AVAILABLE
        self._bot_task: Optional[asyncio.Task] = None
        self._playback_task: Optional[asyncio.Task] = None
        self._audio_callback: Optional[Callable] = None
        self._voice_queue: asyncio.Queue = asyncio.Queue()

    async def initialize(self) -> bool:
        """Initialize Discord REST client and optionally voice bot"""
        if not self.token:
            logging.warning("Discord token not provided - discord disabled")
            self.enabled = False
            return False

        # Initialize REST client
        async with self._lock:
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bot {self.token}",
                    "Content-Type": "application/json"
                },
                timeout=10.0
            )

        # Test REST connection
        try:
            response = await self.client.get("/users/@me")
            if response.status_code == 200:
                user = response.json()
                logging.info(f"Discord REST connected as {user.get('username')}")
                self.connected = True
            else:
                self.enabled = False
                return False
        except Exception as e:
            logging.error(f"Discord REST connection failed: {e}")
            self.enabled = False
            return False

        # Initialize discord.py bot for voice (runs in background)
        if self.voice_enabled:
            await self._init_voice_bot()

        return True

    async def _init_voice_bot(self):
        """Initialize discord.py bot for voice support"""
        try:
            intents = discord.Intents.default()
            intents.message_content = True
            intents.voice_states = True

            self.bot = commands.Bot(command_prefix="!", intents=intents)

            @self.bot.event
            async def on_ready():
                logging.info(f"Discord voice bot ready as {self.bot.user}")

            # Start bot in background task
            self._bot_task = asyncio.create_task(self._run_bot())
            logging.info("Discord voice bot starting...")

        except Exception as e:
            logging.error(f"Failed to init voice bot: {e}")
            self.voice_enabled = False

    async def _run_bot(self):
        """Run discord.py bot"""
        try:
            await self.bot.start(self.token)
        except Exception as e:
            logging.error(f"Discord bot error: {e}")

    async def execute(self, action: str, **kwargs) -> ToolResult:
        """Execute Discord action - async"""
        if not self.connected:
            return ToolResult(
                status=ToolStatus.ERROR,
                message="Discord not connected"
            )

        actions = {
            "send_message": self._send_message,
            "read_messages": self._read_messages,
            "get_channels": self._get_channels,
            "get_guilds": self._get_guilds,
            "join_voice": self._join_voice,
            "leave_voice": self._leave_voice,
            "speak": self._speak_in_voice,
            "get_voice_channels": self._get_voice_channels,
        }

        if action not in actions:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Unknown action: {action}"
            )

        return await actions[action](**kwargs)

    async def _send_message(self, channel_id: str, content: str) -> ToolResult:
        """Send a message to a Discord channel"""
        try:
            async with self._lock:
                response = await self.client.post(
                    f"/channels/{channel_id}/messages",
                    json={"content": content}
                )

            if response.status_code in [200, 201]:
                msg = response.json()
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"message_id": msg.get("id")},
                    message=f"Message sent to channel {channel_id}"
                )
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=response.text,
                    message=f"Failed to send: {response.status_code}"
                )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def _read_messages(self, channel_id: str, limit: int = 10) -> ToolResult:
        """Read recent messages from a channel"""
        try:
            async with self._lock:
                response = await self.client.get(
                    f"/channels/{channel_id}/messages",
                    params={"limit": min(limit, 100)}
                )

            if response.status_code == 200:
                messages = response.json()
                result: List[Dict[str, str]] = []
                for msg in messages:
                    result.append({
                        "author": msg.get("author", {}).get("username", "Unknown"),
                        "content": msg.get("content", ""),
                        "timestamp": msg.get("timestamp", "")
                    })
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=result,
                    message=f"Read {len(result)} messages"
                )
            else:
                return ToolResult(status=ToolStatus.ERROR, error=response.text)
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def _get_channels(self, guild_id: str) -> ToolResult:
        """Get all channels in a guild"""
        try:
            async with self._lock:
                response = await self.client.get(f"/guilds/{guild_id}/channels")

            if response.status_code == 200:
                channels = response.json()
                result: List[Dict[str, Any]] = []
                for ch in channels:
                    ch_type = ch.get("type")
                    type_name = {0: "text", 2: "voice", 4: "category", 5: "announcement"}.get(ch_type, str(ch_type))
                    result.append({
                        "id": ch.get("id"),
                        "name": ch.get("name"),
                        "type": type_name
                    })
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=result,
                    message=f"Found {len(result)} channels"
                )
            else:
                return ToolResult(status=ToolStatus.ERROR, error=response.text)
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def _get_guilds(self) -> ToolResult:
        """Get bot's guilds/servers"""
        try:
            async with self._lock:
                response = await self.client.get("/users/@me/guilds")

            if response.status_code == 200:
                guilds = response.json()
                result = [{"id": g.get("id"), "name": g.get("name")} for g in guilds]
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=result,
                    message=f"Found {len(result)} servers"
                )
            else:
                return ToolResult(status=ToolStatus.ERROR, error=response.text)
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def _get_voice_channels(self, guild_id: str) -> ToolResult:
        """Get voice channels in a guild"""
        try:
            async with self._lock:
                response = await self.client.get(f"/guilds/{guild_id}/channels")

            if response.status_code == 200:
                channels = response.json()
                voice_channels = [
                    {"id": ch.get("id"), "name": ch.get("name")}
                    for ch in channels if ch.get("type") == 2  # Voice channel type
                ]
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=voice_channels,
                    message=f"Found {len(voice_channels)} voice channels"
                )
            else:
                return ToolResult(status=ToolStatus.ERROR, error=response.text)
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def _join_voice(self, guild_id: str, channel_id: str) -> ToolResult:
        """Join a voice channel"""
        if not self.voice_enabled or not self.bot:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Voice not available. Install discord.py[voice]: pip install discord.py[voice]"
            )

        try:
            # Wait for bot to be ready
            await self.bot.wait_until_ready()

            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                return ToolResult(status=ToolStatus.ERROR, error=f"Guild {guild_id} not found")

            channel = guild.get_channel(int(channel_id))
            if not channel or not isinstance(channel, discord.VoiceChannel):
                return ToolResult(status=ToolStatus.ERROR, error=f"Voice channel {channel_id} not found")

            # Disconnect from current voice if connected
            if self.voice_client and self.voice_client.is_connected():
                await self.voice_client.disconnect()

            # Connect to voice channel
            self.voice_client = await channel.connect()

            logging.info(f"🎤 Joined voice channel: {channel.name}")
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"channel": channel.name, "guild": guild.name},
                message=f"Joined voice channel {channel.name}"
            )

        except Exception as e:
            logging.error(f"Failed to join voice: {e}")
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def _leave_voice(self) -> ToolResult:
        """Leave current voice channel"""
        if not self.voice_client:
            return ToolResult(status=ToolStatus.SUCCESS, message="Not in a voice channel")

        try:
            channel_name = self.voice_client.channel.name if self.voice_client.channel else "unknown"
            await self.voice_client.disconnect()
            self.voice_client = None

            logging.info(f"🎤 Left voice channel: {channel_name}")
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"Left voice channel {channel_name}"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def _speak_in_voice(self, audio_data: bytes = None, text: str = None) -> ToolResult:
        """Play audio in voice channel (receives PCM audio from Sakura)"""
        if not self.voice_client or not self.voice_client.is_connected():
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Not connected to a voice channel. Use join_voice first."
            )

        if not audio_data:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="No audio data provided"
            )

        try:
            # Queue audio for playback
            await self._voice_queue.put(audio_data)

            # Start playback task if not running
            if not hasattr(self, '_playback_task') or self._playback_task.done():
                self._playback_task = asyncio.create_task(self._voice_playback_loop())

            return ToolResult(
                status=ToolStatus.SUCCESS,
                message="Audio queued for voice playback"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def _voice_playback_loop(self):
        """Background task to play audio in voice channel"""
        while self.voice_client and self.voice_client.is_connected():
            try:
                # Get audio from queue
                audio_data = await asyncio.wait_for(self._voice_queue.get(), timeout=1.0)

                if audio_data and self.voice_client:
                    # Convert PCM to discord audio source
                    audio_source = discord.PCMAudio(io.BytesIO(audio_data))

                    # Play audio
                    if not self.voice_client.is_playing():
                        self.voice_client.play(audio_source)

                        # Wait for playback to finish
                        while self.voice_client.is_playing():
                            await asyncio.sleep(0.1)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logging.error(f"Voice playback error: {e}")
                break

    def set_audio_callback(self, callback: Callable):
        """Set callback to receive audio from Sakura's Gemini responses"""
        self._audio_callback = callback

    async def stream_audio_to_voice(self, audio_data: bytes):
        """Stream audio directly to voice channel (called from main loop)"""
        if self.voice_client and self.voice_client.is_connected():
            await self._voice_queue.put(audio_data)

    def is_in_voice(self) -> bool:
        """Check if bot is in a voice channel"""
        return self.voice_client is not None and self.voice_client.is_connected()

    def get_schema(self) -> Dict[str, Any]:
        """Return schema for Discord tools"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "send_message", "read_messages", "get_channels", 
                            "get_guilds", "get_voice_channels", "join_voice", "leave_voice"
                        ],
                        "description": "Discord action: send_message, read_messages, get_channels, get_guilds, get_voice_channels, join_voice, leave_voice"
                    },
                    "channel_id": {"type": "string", "description": "Discord channel ID"},
                    "content": {"type": "string", "description": "Message content to send"},
                    "guild_id": {"type": "string", "description": "Discord server/guild ID"},
                    "limit": {"type": "integer", "description": "Number of messages to read", "default": 10}
                },
                "required": ["action"]
            }
        }

    async def cleanup(self):
        """Disconnect from Discord"""
        async with self._lock:
            # Leave voice
            if self.voice_client:
                try:
                    await self.voice_client.disconnect()
                except Exception as e:
                    logging.debug(f"Voice disconnect error: {e}")
                self.voice_client = None

            # Stop bot
            if self.bot:
                try:
                    await self.bot.close()
                except Exception:
                    pass
                self.bot = None

            # Cancel bot task
            if self._bot_task:
                self._bot_task.cancel()
                self._bot_task = None

            # Close REST client
            if self.client:
                await self.client.aclose()
                self.client = None

            self.connected = False
            logging.info("Discord cleanup completed")
