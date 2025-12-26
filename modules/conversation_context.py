"""
Conversation Context Manager for Sakura
Maintains rolling buffer of conversation exchanges for better context awareness

Rules followed:
- All imports MUST be used
- Async with asyncio.Lock() for thread safety
- aiofiles for file I/O
- Database integration for infinite history
"""
import asyncio
import logging
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
import aiofiles

# Import database module for infinite history
try:
    from modules.database import get_database, HAS_AIOSQLITE
except ImportError:
    HAS_AIOSQLITE = False
    get_database = None


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
    """Manages conversation context with rolling buffer and database persistence"""
    
    def __init__(self, max_exchanges: int = 20, context_file: str = None, db_path: str = None):
        self.max_exchanges = max_exchanges
        # Allow environment variable overrides
        self.context_file = context_file or os.getenv("CONVERSATION_CONTEXT_FILE", "conversation_context.json")
        self.db_path = db_path or os.getenv("DB_PATH", "sakura.db")
        self._lock = asyncio.Lock()
        self._exchanges: List[ConversationExchange] = []
        self._session_start: str = datetime.now().isoformat()
        self._session_id: str = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._pending_tasks: List[str] = []
        self._failed_actions: List[Dict[str, Any]] = []
        self._current_topics: List[str] = []
        self._db = None
        self._use_db = HAS_AIOSQLITE
    
    async def initialize(self) -> bool:
        """Initialize context manager, optionally load previous session"""
        async with self._lock:
            try:
                # Initialize database connection for infinite history
                if self._use_db and get_database:
                    try:
                        self._db = await get_database(self.db_path)
                        logging.info("Conversation context connected to database for infinite history")
                    except Exception as e:
                        logging.warning(f"Database init failed for context: {e}")
                        self._use_db = False
                
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
        """Add a new exchange to the conversation buffer and database"""
        async with self._lock:
            # Extract mood indicators from user input
            mood_indicators = self._detect_mood(user_input)
            mood = mood_indicators[0] if mood_indicators else None
            
            # Extract topics from the exchange
            topics = self._extract_topics(user_input, ai_response)
            self._current_topics = list(set(self._current_topics + topics))[-10:]  # Keep last 10 topics
            
            # Detect user corrections and log them for learning
            correction_info = self._detect_correction(user_input)
            if correction_info and self._db:
                try:
                    # Get the last exchange to know what was wrong
                    last_action = None
                    if self._exchanges:
                        last_ex = self._exchanges[-1]
                        if last_ex.tools_used:
                            last_action = ", ".join(last_ex.tools_used)
                    
                    await self._db.log_user_feedback(
                        feedback_type="correction",
                        user_message=user_input,
                        original_action=last_action,
                        correct_action=correction_info.get("intended")
                    )
                    
                    # Create learned correction pattern
                    if correction_info.get("intended"):
                        await self._db.add_learned_correction(
                            trigger_pattern=correction_info.get("trigger", user_input[:100]),
                            correct_behavior=correction_info["intended"],
                            wrong_behavior=last_action
                        )
                    
                    logging.info(f"📝 Detected correction: {correction_info.get('type')}")
                except Exception as e:
                    logging.warning(f"Failed to log correction: {e}")
            
            # Detect positive feedback and log it
            positive_info = self._detect_positive_feedback(user_input)
            if positive_info and self._db:
                try:
                    # Get the last action that received positive feedback
                    last_action = None
                    if self._exchanges:
                        last_ex = self._exchanges[-1]
                        if last_ex.tools_used:
                            last_action = ", ".join(last_ex.tools_used)
                    
                    await self._db.log_user_feedback(
                        feedback_type="positive",
                        user_message=user_input,
                        original_action=last_action
                    )
                    
                    logging.info(f"👍 Detected positive feedback: {positive_info.get('type')}")
                except Exception as e:
                    logging.warning(f"Failed to log positive feedback: {e}")
            
            # Detect negative feedback and log it
            negative_info = self._detect_negative_feedback(user_input)
            if negative_info and self._db:
                try:
                    last_action = None
                    if self._exchanges:
                        last_ex = self._exchanges[-1]
                        if last_ex.tools_used:
                            last_action = ", ".join(last_ex.tools_used)
                    
                    await self._db.log_user_feedback(
                        feedback_type="negative",
                        user_message=user_input,
                        original_action=last_action
                    )
                    
                    logging.info(f"👎 Detected negative feedback: {negative_info.get('type')}")
                except Exception as e:
                    logging.warning(f"Failed to log negative feedback: {e}")
            
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
            
            # Log to database for infinite history
            if self._db:
                try:
                    await self._db.log_conversation_exchange(
                        session_id=self._session_id,
                        user_input=user_input,
                        ai_response=ai_response,
                        tools_used=tools_used,
                        tool_results=tool_results,
                        mood=mood,
                        topics=topics
                    )
                except Exception as e:
                    logging.warning(f"Failed to log exchange to database: {e}")
            
            # Trim in-memory buffer to max size
            if len(self._exchanges) > self.max_exchanges:
                self._exchanges = self._exchanges[-self.max_exchanges:]
            
            # Save to JSON periodically (every 5 exchanges)
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
            # Keep only last 10 failures in memory
            self._failed_actions = self._failed_actions[-10:]
            
            # Log error pattern to database for learning
            if self._db:
                try:
                    # Parse action string to get tool and action name
                    tool_name = "unknown"
                    action_name = "unknown"
                    if "." in action:
                        parts = action.split(".", 1)
                        tool_name = parts[0]
                        action_name = parts[1] if len(parts) > 1 else "unknown"
                    
                    # Determine error type
                    error_lower = error.lower()
                    error_type = "unknown"
                    if "not found" in error_lower or "no such" in error_lower:
                        error_type = "not_found"
                    elif "permission" in error_lower or "access denied" in error_lower:
                        error_type = "permission"
                    elif "timeout" in error_lower:
                        error_type = "timeout"
                    elif "connection" in error_lower or "network" in error_lower:
                        error_type = "network"
                    
                    await self._db.log_error_pattern(
                        tool_name=tool_name,
                        action_name=action_name,
                        error_type=error_type,
                        error_message=error,
                        context=context
                    )
                except Exception as e:
                    logging.warning(f"Failed to log error pattern: {e}")
    
    async def log_user_feedback(
        self,
        feedback_type: str,
        message: str,
        original_action: str = None,
        correct_action: str = None
    ):
        """Log user feedback/correction for learning"""
        if not self._db:
            logging.warning("Database not available for feedback logging")
            return
        
        try:
            await self._db.log_user_feedback(
                feedback_type=feedback_type,
                user_message=message,
                original_action=original_action,
                correct_action=correct_action
            )
            
            # If it's a correction, also create a learned correction
            if feedback_type == "correction" and correct_action:
                trigger = message.lower()[:100]
                await self._db.add_learned_correction(
                    trigger_pattern=trigger,
                    correct_behavior=correct_action,
                    wrong_behavior=original_action
                )
                logging.info(f"Learned correction: {trigger[:50]}...")
        except Exception as e:
            logging.error(f"Failed to log user feedback: {e}")
    
    async def get_relevant_corrections(self, user_input: str, tool_name: str = None) -> List[Dict[str, Any]]:
        """Get corrections relevant to current context"""
        if not self._db:
            return []
        
        try:
            return await self._db.get_relevant_corrections(user_input, tool_name)
        except Exception as e:
            logging.warning(f"Failed to get corrections: {e}")
            return []
    
    async def search_history(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search infinite conversation history"""
        if not self._db:
            # Fallback to in-memory search
            results = []
            query_lower = query.lower()
            for ex in reversed(self._exchanges):
                if query_lower in ex.user_input.lower() or query_lower in ex.ai_response.lower():
                    results.append(asdict(ex))
                    if len(results) >= limit:
                        break
            return results
        
        try:
            return await self._db.get_conversation_history(search_query=query, limit=limit)
        except Exception as e:
            logging.warning(f"Failed to search history: {e}")
            return []
    
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
    
    def _detect_correction(self, text: str) -> Optional[Dict[str, Any]]:
        """Detect if user is correcting Sakura's previous action"""
        text_lower = text.lower().strip()
        
        # Correction patterns with their types
        correction_patterns = [
            # Direct negation
            (r"^no[,.]?\s+", "negation"),
            (r"^nope[,.]?\s+", "negation"),
            (r"^wrong[,.]?\s+", "negation"),
            (r"^that'?s wrong", "negation"),
            (r"^that'?s not", "negation"),
            (r"^not that", "negation"),
            
            # Clarification
            (r"^i meant", "clarification"),
            (r"^i said", "clarification"),
            (r"^i asked for", "clarification"),
            (r"^i wanted", "clarification"),
            (r"^what i meant", "clarification"),
            (r"^actually[,.]?\s+i", "clarification"),
            
            # Instruction to stop/change
            (r"^don'?t do that", "stop"),
            (r"^stop doing", "stop"),
            (r"^never do", "stop"),
            (r"^don'?t ever", "stop"),
            (r"^please don'?t", "stop"),
            
            # Retry request
            (r"^try again", "retry"),
            (r"^do it again", "retry"),
            (r"^redo", "retry"),
            (r"^again[,.]?\s+but", "retry"),
            
            # Preference statement
            (r"^i prefer", "preference"),
            (r"^i'?d rather", "preference"),
            (r"^next time[,.]?\s+", "preference"),
            (r"^in the future[,.]?\s+", "preference"),
            (r"^always ", "preference"),
            (r"^remember to ", "preference"),
        ]
        
        import re
        for pattern, correction_type in correction_patterns:
            if re.search(pattern, text_lower):
                # Try to extract what user actually wanted
                intended = None
                
                # Extract the intended action from common patterns
                clarification_extractors = [
                    r"i meant (.+)",
                    r"i said (.+)",
                    r"i wanted (.+)",
                    r"i asked for (.+)",
                    r"not that[,.]?\s*(.+)",
                    r"i prefer (.+)",
                    r"i'?d rather (.+)",
                    r"next time[,.]?\s*(.+)",
                    r"always (.+)",
                    r"remember to (.+)",
                ]
                
                for extractor in clarification_extractors:
                    match = re.search(extractor, text_lower)
                    if match:
                        intended = match.group(1).strip()
                        break
                
                return {
                    "type": correction_type,
                    "trigger": text[:100],
                    "intended": intended,
                    "full_text": text
                }
        
        return None
    
    def _detect_positive_feedback(self, text: str) -> Optional[Dict[str, Any]]:
        """Detect if user is giving positive feedback about Sakura's action"""
        text_lower = text.lower().strip()
        
        import re
        
        # Positive feedback patterns
        positive_patterns = [
            # Direct praise
            (r"^perfect", "praise"),
            (r"^exactly", "praise"),
            (r"^great", "praise"),
            (r"^awesome", "praise"),
            (r"^nice", "praise"),
            (r"^good job", "praise"),
            (r"^well done", "praise"),
            (r"^that'?s (exactly )?what i (wanted|needed|meant)", "praise"),
            (r"^that'?s (right|correct|perfect|great)", "praise"),
            (r"^yes[,!.]?\s*(that'?s|exactly|perfect)", "praise"),
            
            # Gratitude
            (r"^thanks?( you)?[,!.]?$", "thanks"),
            (r"^thanks?( you)?[,!.]?\s+(that|this|it)", "thanks"),
            (r"^thank you so much", "thanks"),
            (r"^thanks?,?\s*(sakura|that worked|perfect)", "thanks"),
            
            # Confirmation of success
            (r"^(it|that) worked", "success"),
            (r"^(it|that)'?s working", "success"),
            (r"^got it", "success"),
            (r"^found it", "success"),
            (r"^there (it is|we go)", "success"),
            
            # Affirmation
            (r"^yes[,!.]?\s*$", "affirm"),
            (r"^yep", "affirm"),
            (r"^yeah", "affirm"),
            (r"^correct", "affirm"),
            (r"^right", "affirm"),
        ]
        
        for pattern, feedback_type in positive_patterns:
            if re.search(pattern, text_lower):
                return {
                    "type": feedback_type,
                    "text": text,
                    "positive": True
                }
        
        return None
    
    def _detect_negative_feedback(self, text: str) -> Optional[Dict[str, Any]]:
        """Detect if user is giving explicit negative feedback"""
        text_lower = text.lower().strip()
        
        import re
        
        # Negative feedback patterns (distinct from corrections)
        negative_patterns = [
            # Frustration
            (r"^(that'?s|this is) (bad|terrible|awful|horrible)", "frustration"),
            (r"^(i )?hate (that|this|when you)", "frustration"),
            (r"^(this|that) sucks", "frustration"),
            (r"^ugh", "frustration"),
            (r"^(so )?annoying", "frustration"),
            (r"^(this is )?frustrating", "frustration"),
            
            # Disappointment
            (r"^(that'?s )?not (good|great|helpful)", "disappointment"),
            (r"^(that|this) (didn'?t|doesn'?t) (help|work)", "disappointment"),
            (r"^useless", "disappointment"),
            (r"^(that'?s )?unhelpful", "disappointment"),
            (r"^(you'?re|that'?s) (not|no) help", "disappointment"),
            
            # Stop/cease
            (r"^stop it", "stop"),
            (r"^quit it", "stop"),
            (r"^enough", "stop"),
            (r"^(just )?stop$", "stop"),
            
            # Explicit negative
            (r"^bad (sakura|job|work)", "negative"),
            (r"^(that was|you did) (bad|wrong|poorly)", "negative"),
            (r"^fail(ed)?", "negative"),
            (r"^(you )?mess(ed)? (it )?up", "negative"),
            (r"^(you )?broke (it|something)", "negative"),
        ]
        
        for pattern, feedback_type in negative_patterns:
            if re.search(pattern, text_lower):
                return {
                    "type": feedback_type,
                    "text": text,
                    "negative": True
                }
        
        return None
    
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
