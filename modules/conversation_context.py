"""
Conversation Context Manager for Sakura
Maintains rolling buffer of conversation exchanges for better context awareness

Rules followed:
- All imports MUST be used
- Async with asyncio.Lock() for thread safety
- aiofiles for file I/O
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
import aiofiles


@dataclass
class ConversationExchange:
    """Single exchange in conversation"""
    timestamp: str
    user_input: str
    ai_response: str
    tools_used: List[str] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    mood_indicators: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)


class ConversationContext:
    """Manages conversation context with rolling buffer"""
    
    def __init__(self, max_exchanges: int = 20, context_file: str = "conversation_context.json"):
        self.max_exchanges = max_exchanges
        self.context_file = context_file
        self._lock = asyncio.Lock()
        self._exchanges: List[ConversationExchange] = []
        self._session_start: str = datetime.now().isoformat()
        self._pending_tasks: List[str] = []
        self._failed_actions: List[Dict[str, Any]] = []
        self._current_topics: List[str] = []
    
    async def initialize(self) -> bool:
        """Initialize context manager, optionally load previous session"""
        async with self._lock:
            try:
                # Try to load recent context if exists and recent
                await self._load_context()
                logging.info(f"Conversation context initialized with {len(self._exchanges)} exchanges")
                return True
            except Exception as e:
                logging.warning(f"Could not load previous context: {e}")
                return True  # Still return True, just start fresh
    
    async def add_exchange(
        self,
        user_input: str,
        ai_response: str,
        tools_used: Optional[List[str]] = None,
        tool_results: Optional[List[Dict[str, Any]]] = None
    ):
        """Add a new exchange to the conversation buffer"""
        async with self._lock:
            # Extract mood indicators from user input
            mood_indicators = self._detect_mood(user_input)
            
            # Extract topics from the exchange
            topics = self._extract_topics(user_input, ai_response)
            self._current_topics = list(set(self._current_topics + topics))[-10:]  # Keep last 10 topics
            
            exchange = ConversationExchange(
                timestamp=datetime.now().isoformat(),
                user_input=user_input,
                ai_response=ai_response,
                tools_used=tools_used or [],
                tool_results=tool_results or [],
                mood_indicators=mood_indicators,
                topics=topics
            )
            
            self._exchanges.append(exchange)
            
            # Trim to max size
            if len(self._exchanges) > self.max_exchanges:
                self._exchanges = self._exchanges[-self.max_exchanges:]
            
            # Save periodically (every 5 exchanges)
            if len(self._exchanges) % 5 == 0:
                await self._save_context()
    
    async def add_pending_task(self, task: str):
        """Add a task that user requested but hasn't been completed"""
        async with self._lock:
            if task not in self._pending_tasks:
                self._pending_tasks.append(task)
                logging.info(f"Added pending task: {task}")
    
    async def complete_task(self, task: str):
        """Mark a task as completed"""
        async with self._lock:
            if task in self._pending_tasks:
                self._pending_tasks.remove(task)
                logging.info(f"Completed task: {task}")
    
    async def add_failed_action(self, action: str, error: str, context: Dict[str, Any] = None):
        """Record a failed action for potential retry or user notification"""
        async with self._lock:
            self._failed_actions.append({
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "error": error,
                "context": context or {}
            })
            # Keep only last 10 failures
            self._failed_actions = self._failed_actions[-10:]
    
    async def get_context_summary(self, max_chars: int = 2000) -> str:
        """Get a summary of recent context for injection into system prompt"""
        async with self._lock:
            if not self._exchanges:
                return ""
            
            summary_parts = []
            
            # Session info
            summary_parts.append(f"[Session started: {self._session_start}]")
            
            # Current topics
            if self._current_topics:
                summary_parts.append(f"[Topics discussed: {', '.join(self._current_topics[-5:])}]")
            
            # Pending tasks
            if self._pending_tasks:
                summary_parts.append(f"[Pending tasks: {', '.join(self._pending_tasks[-3:])}]")
            
            # Recent failures
            if self._failed_actions:
                recent_fail = self._failed_actions[-1]
                summary_parts.append(f"[Recent failure: {recent_fail['action']} - {recent_fail['error']}]")
            
            # Recent exchanges (most recent first, limited)
            summary_parts.append("\n[Recent conversation:]")
            recent = self._exchanges[-5:]  # Last 5 exchanges
            for ex in recent:
                # Truncate long messages
                user_short = ex.user_input[:100] + "..." if len(ex.user_input) > 100 else ex.user_input
                ai_short = ex.ai_response[:100] + "..." if len(ex.ai_response) > 100 else ex.ai_response
                
                entry = f"User: {user_short}\nSakura: {ai_short}"
                if ex.tools_used:
                    entry += f"\n(Used: {', '.join(ex.tools_used)})"
                summary_parts.append(entry)
            
            summary = "\n".join(summary_parts)
            
            # Truncate if too long
            if len(summary) > max_chars:
                summary = summary[:max_chars] + "\n[...truncated]"
            
            return summary
    
    async def get_recent_tools_used(self, n: int = 5) -> List[str]:
        """Get list of recently used tools"""
        async with self._lock:
            tools = []
            for ex in reversed(self._exchanges[-n:]):
                tools.extend(ex.tools_used)
            return list(set(tools))
    
    async def get_last_user_request(self) -> Optional[str]:
        """Get the last thing user asked for"""
        async with self._lock:
            if self._exchanges:
                return self._exchanges[-1].user_input
            return None
    
    async def get_failed_actions(self) -> List[Dict[str, Any]]:
        """Get list of recent failed actions"""
        async with self._lock:
            return self._failed_actions.copy()
    
    async def clear_context(self):
        """Clear all context (new session)"""
        async with self._lock:
            self._exchanges.clear()
            self._pending_tasks.clear()
            self._failed_actions.clear()
            self._current_topics.clear()
            self._session_start = datetime.now().isoformat()
            logging.info("Conversation context cleared")
    
    def _detect_mood(self, text: str) -> List[str]:
        """Detect mood indicators from user input"""
        moods = []
        text_lower = text.lower()
        
        # Positive indicators
        if any(w in text_lower for w in ["thanks", "thank you", "great", "awesome", "perfect", "love"]):
            moods.append("positive")
        
        # Negative indicators
        if any(w in text_lower for w in ["frustrated", "annoyed", "angry", "hate", "stupid", "broken"]):
            moods.append("frustrated")
        
        # Urgency indicators
        if any(w in text_lower for w in ["urgent", "asap", "quickly", "hurry", "now", "immediately"]):
            moods.append("urgent")
        
        # Confusion indicators
        if any(w in text_lower for w in ["confused", "don't understand", "what do you mean", "huh", "?"]):
            moods.append("confused")
        
        # Casual indicators
        if any(w in text_lower for w in ["hey", "hi", "hello", "sup", "yo"]):
            moods.append("casual")
        
        return moods
    
    def _extract_topics(self, user_input: str, ai_response: str) -> List[str]:
        """Extract topics from conversation exchange"""
        topics = []
        combined = (user_input + " " + ai_response).lower()
        
        # Topic keywords
        topic_keywords = {
            "files": ["file", "folder", "directory", "document", "save", "open"],
            "system": ["computer", "pc", "system", "hardware", "cpu", "ram", "gpu"],
            "apps": ["app", "application", "program", "software", "chrome", "browser"],
            "media": ["music", "video", "play", "pause", "volume", "spotify"],
            "coding": ["code", "script", "python", "programming", "git", "debug"],
            "web": ["website", "url", "search", "google", "internet"],
            "discord": ["discord", "server", "channel", "message"],
            "smart_home": ["light", "temperature", "thermostat", "home assistant"],
            "mouse": ["mouse", "click", "cursor", "screen"],
            "window": ["window", "minimize", "maximize", "focus"],
        }
        
        for topic, keywords in topic_keywords.items():
            if any(kw in combined for kw in keywords):
                topics.append(topic)
        
        return topics[:3]  # Max 3 topics per exchange
    
    async def _save_context(self):
        """Save context to file"""
        try:
            data = {
                "session_start": self._session_start,
                "exchanges": [asdict(ex) for ex in self._exchanges[-10:]],  # Save last 10
                "pending_tasks": self._pending_tasks,
                "failed_actions": self._failed_actions,
                "current_topics": self._current_topics
            }
            async with aiofiles.open(self.context_file, 'w') as f:
                await f.write(json.dumps(data, indent=2))
        except Exception as e:
            logging.error(f"Failed to save context: {e}")
    
    async def _load_context(self):
        """Load context from file if recent"""
        try:
            async with aiofiles.open(self.context_file, 'r') as f:
                content = await f.read()
                data = json.loads(content)
            
            # Check if session is recent (within 30 minutes)
            session_start = datetime.fromisoformat(data.get("session_start", "2000-01-01"))
            age_minutes = (datetime.now() - session_start).total_seconds() / 60
            
            if age_minutes < 30:
                # Load recent context
                self._session_start = data.get("session_start", self._session_start)
                self._pending_tasks = data.get("pending_tasks", [])
                self._failed_actions = data.get("failed_actions", [])
                self._current_topics = data.get("current_topics", [])
                
                # Reconstruct exchanges
                for ex_data in data.get("exchanges", []):
                    self._exchanges.append(ConversationExchange(**ex_data))
                
                logging.info(f"Loaded {len(self._exchanges)} exchanges from previous session ({age_minutes:.1f} min ago)")
            else:
                logging.info(f"Previous session too old ({age_minutes:.1f} min), starting fresh")
                
        except FileNotFoundError:
            pass  # No previous context, that's fine
        except Exception as e:
            logging.warning(f"Error loading context: {e}")
    
    async def cleanup(self):
        """Save context before shutdown"""
        async with self._lock:
            await self._save_context()
            logging.info("Conversation context saved")
