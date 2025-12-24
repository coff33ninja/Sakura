"""
Intent Parser for Sakura
Better understanding of vague commands through synonyms, fuzzy matching, and context

Rules followed:
- All imports MUST be used
- Async with asyncio.Lock() for thread safety
- aiofiles for file I/O
"""
import asyncio
import logging
import re
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import aiofiles
from difflib import SequenceMatcher, get_close_matches


class IntentType(Enum):
    """Types of user intents"""
    ACTION = "action"              # User wants to do something
    QUERY = "query"                # User wants information
    NAVIGATION = "navigation"      # User wants to go somewhere
    CONTROL = "control"            # User wants to control something
    MEMORY = "memory"              # User wants to remember/recall
    VAGUE = "vague"                # Intent unclear
    CONFIRMATION = "confirmation"  # Yes/no response
    CORRECTION = "correction"      # User is correcting


@dataclass
class ParsedIntent:
    """Result of parsing user input"""
    raw_input: str
    normalized_input: str
    intent_type: IntentType
    confidence: float
    tool_hint: Optional[str] = None
    action_hint: Optional[str] = None
    extracted_args: Dict[str, Any] = field(default_factory=dict)
    alternatives: List[str] = field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    context_used: List[str] = field(default_factory=list)


class IntentParser:
    """Parses user input to understand intent with fuzzy matching and synonyms"""
    
    # Comprehensive synonym database
    SYNONYMS = {
        # Action verbs
        "open": ["launch", "start", "run", "execute", "fire up", "boot", "load"],
        "close": ["quit", "exit", "kill", "terminate", "end", "stop", "shut down", "shutdown"],
        "find": ["search", "look for", "locate", "where is", "where's", "hunt for", "seek"],
        "show": ["display", "list", "get", "tell me", "what is", "what's", "give me"],
        "create": ["make", "new", "generate", "build", "write", "add"],
        "delete": ["remove", "erase", "trash", "get rid of", "destroy"],
        "move": ["transfer", "relocate", "put", "drag"],
        "copy": ["duplicate", "clone", "replicate"],
        "save": ["store", "keep", "remember", "backup", "back up"],
        
        # System controls
        "volume": ["sound", "audio", "loudness", "speaker"],
        "mute": ["silence", "quiet", "hush", "shut up"],
        "brightness": ["screen brightness", "display brightness", "dim", "bright"],
        
        # Media controls
        "play": ["resume", "unpause", "continue"],
        "pause": ["stop", "hold", "freeze"],
        "next": ["skip", "forward", "next track", "next song"],
        "previous": ["back", "last", "prev", "previous track"],
        
        # Navigation
        "go to": ["navigate to", "open", "visit", "head to", "take me to"],
        "back": ["return", "go back", "previous"],
        
        # Common objects
        "browser": ["chrome", "firefox", "edge", "web browser", "internet"],
        "editor": ["code", "vscode", "notepad", "text editor", "ide"],
        "terminal": ["command prompt", "cmd", "powershell", "console", "shell"],
        "folder": ["directory", "dir", "path"],
        "file": ["document", "doc"],
        "app": ["application", "program", "software"],
        "window": ["screen", "display"],
        "desktop": ["home screen", "main screen"],
        
        # Time references
        "now": ["immediately", "right now", "asap", "at once"],
        "later": ["in a bit", "soon", "after", "afterwards"],
        "today": ["this day", "current day"],
        "tomorrow": ["next day", "the next day"],
    }

    # Vague command patterns and their meanings
    VAGUE_PATTERNS = {
        r"do\s+(?:that|it|the\s+thing)": "repeat_last",
        r"(?:the\s+)?usual": "user_preference",
        r"fix\s+(?:it|that|this)": "fix_error",
        r"try\s+again": "retry_last",
        r"undo\s+(?:that|it)?": "undo_last",
        r"never\s*mind|cancel|forget\s*it": "cancel",
        r"what\s+(?:did\s+you|was\s+that)": "explain_last",
        r"do\s+(?:the\s+)?same": "repeat_last",
        r"like\s+(?:before|last\s+time)": "repeat_pattern",
        r"you\s+know\s+(?:what|the\s+one)": "context_reference",
    }
    
    # Intent detection patterns
    INTENT_PATTERNS = {
        IntentType.ACTION: [
            r"^(?:please\s+)?(?:can\s+you\s+)?(?:open|close|run|start|stop|create|delete|move|copy)",
            r"^(?:please\s+)?(?:turn|set|change|adjust|increase|decrease)",
            r"^(?:please\s+)?(?:play|pause|skip|mute|unmute)",
        ],
        IntentType.QUERY: [
            r"^(?:what|where|when|who|how|why|which)",
            r"^(?:is|are|do|does|can|could|will|would)\s+",
            r"^(?:tell\s+me|show\s+me|list|get)",
        ],
        IntentType.NAVIGATION: [
            r"^(?:go\s+to|navigate|open|visit|take\s+me)",
        ],
        IntentType.CONTROL: [
            r"^(?:turn|set|change|adjust|increase|decrease|enable|disable)",
            r"volume|brightness|mute|unmute",
        ],
        IntentType.MEMORY: [
            r"^(?:remember|recall|forget|save|store)",
            r"^(?:what\s+did\s+(?:i|we)|do\s+you\s+remember)",
        ],
        IntentType.CONFIRMATION: [
            r"^(?:yes|yeah|yep|sure|ok|okay|no|nope|nah|cancel)",
        ],
        IntentType.CORRECTION: [
            r"^(?:no,?\s*)?(?:i\s+meant|actually|not\s+that)",
            r"^(?:wrong|incorrect|that's\s+not)",
        ],
    }
    
    # Tool mapping based on keywords
    TOOL_KEYWORDS = {
        "windows": ["app", "window", "file", "folder", "command", "script", "mouse", "click", 
                   "volume", "media", "screenshot", "clipboard", "process"],
        "system_info": ["hardware", "cpu", "ram", "gpu", "disk", "drive", "installed", 
                       "running", "pc", "computer", "system", "monitor", "display"],
        "memory": ["remember", "recall", "forget", "store", "memory", "save fact"],
        "web_search": ["search", "google", "look up", "find online", "web"],
        "web_fetch": ["fetch", "get page", "website content", "url"],
        "discord": ["discord", "server", "channel", "message"],
        "smart_home": ["light", "temperature", "thermostat", "home assistant", "smart"],
    }
    
    def __init__(self, learning_file: str = "intent_learning.json"):
        self.learning_file = learning_file
        self._lock = asyncio.Lock()
        self._reverse_synonyms: Dict[str, str] = {}  # word -> canonical form
        self._learned_mappings: Dict[str, Dict[str, Any]] = {}  # phrase -> intent mapping
        self._context_history: List[Dict[str, Any]] = []
        self._last_intent: Optional[ParsedIntent] = None
        self._ambiguity_threshold = 0.6
        self._recent_words: Set[str] = set()  # Track recently used words for context
        self._word_expiry = timedelta(minutes=10)  # How long words stay in recent set
        self._word_timestamps: Dict[str, datetime] = {}  # When each word was last used
        self._build_reverse_synonyms()
    
    def _build_reverse_synonyms(self):
        """Build reverse lookup for synonyms"""
        for canonical, synonyms in self.SYNONYMS.items():
            self._reverse_synonyms[canonical] = canonical
            for syn in synonyms:
                self._reverse_synonyms[syn.lower()] = canonical
    
    def _track_recent_words(self, text: str):
        """Track recently used words for context awareness"""
        now = datetime.now()
        words = set(text.lower().split())
        
        # Add new words
        for word in words:
            self._recent_words.add(word)
            self._word_timestamps[word] = now
        
        # Clean up expired words
        expired_words: Set[str] = set()
        for word, timestamp in self._word_timestamps.items():
            if now - timestamp > self._word_expiry:
                expired_words.add(word)
        
        for word in expired_words:
            self._recent_words.discard(word)
            del self._word_timestamps[word]
    
    def get_recent_words(self) -> Set[str]:
        """Get set of recently used words (within expiry window)"""
        now = datetime.now()
        # Filter to only non-expired words
        active_words: Set[str] = set()
        for word in self._recent_words:
            if word in self._word_timestamps:
                if now - self._word_timestamps[word] <= self._word_expiry:
                    active_words.add(word)
        return active_words
    
    def has_recent_context_for(self, keywords: List[str]) -> bool:
        """Check if any keywords appear in recent word context"""
        recent = self.get_recent_words()
        keyword_set: Set[str] = set(k.lower() for k in keywords)
        return bool(recent & keyword_set)  # Set intersection
    
    async def initialize(self) -> bool:
        """Initialize intent parser"""
        async with self._lock:
            try:
                await self._load_learning()
                logging.info(f"Intent parser initialized with {len(self._learned_mappings)} learned mappings")
                return True
            except Exception as e:
                logging.warning(f"Could not load intent learning: {e}")
                return True
    
    async def parse(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ParsedIntent:
        """
        Parse user input to understand intent
        
        Args:
            user_input: Raw user input
            context: Current context (topics, recent actions, etc.)
        
        Returns:
            ParsedIntent with analysis
        """
        async with self._lock:
            # Normalize input
            normalized = self._normalize_input(user_input)
            
            # Track words for context
            self._track_recent_words(normalized)
            
            # Check for vague commands first
            vague_type = self._detect_vague_command(normalized)
            if vague_type:
                return await self._handle_vague_command(user_input, normalized, vague_type, context)
            
            # Check learned mappings
            learned = self._check_learned_mapping(normalized)
            if learned:
                return learned
            
            # Detect intent type
            intent_type, confidence = self._detect_intent_type(normalized)
            
            # Extract tool and action hints
            tool_hint = self._detect_tool(normalized)
            action_hint = self._detect_action(normalized)
            
            # Extract arguments
            extracted_args = self._extract_arguments(normalized, tool_hint)
            
            # Check if clarification needed
            needs_clarification = confidence < self._ambiguity_threshold
            clarification_question = None
            alternatives = []
            
            if needs_clarification:
                alternatives = self._get_alternatives(normalized)
                if alternatives:
                    clarification_question = self._generate_clarification(normalized, alternatives)
            
            intent = ParsedIntent(
                raw_input=user_input,
                normalized_input=normalized,
                intent_type=intent_type,
                confidence=confidence,
                tool_hint=tool_hint,
                action_hint=action_hint,
                extracted_args=extracted_args,
                alternatives=alternatives,
                needs_clarification=needs_clarification,
                clarification_question=clarification_question,
                context_used=[]
            )
            
            # Store for context
            self._last_intent = intent
            self._context_history.append({
                "input": user_input,
                "intent": intent_type.value,
                "timestamp": datetime.now().isoformat()
            })
            if len(self._context_history) > 20:
                self._context_history = self._context_history[-20:]
            
            return intent

    def _normalize_input(self, text: str) -> str:
        """Normalize input text"""
        # Lowercase
        normalized = text.lower().strip()
        
        # Replace synonyms with canonical forms
        words = normalized.split()
        normalized_words = []
        
        i = 0
        while i < len(words):
            # Try multi-word synonyms first (up to 3 words)
            matched = False
            for length in range(3, 0, -1):
                if i + length <= len(words):
                    phrase = " ".join(words[i:i+length])
                    if phrase in self._reverse_synonyms:
                        normalized_words.append(self._reverse_synonyms[phrase])
                        i += length
                        matched = True
                        break
            
            if not matched:
                word = words[i]
                if word in self._reverse_synonyms:
                    normalized_words.append(self._reverse_synonyms[word])
                else:
                    normalized_words.append(word)
                i += 1
        
        return " ".join(normalized_words)
    
    def _detect_vague_command(self, text: str) -> Optional[str]:
        """Detect if input is a vague command"""
        for pattern, vague_type in self.VAGUE_PATTERNS.items():
            if re.search(pattern, text, re.IGNORECASE):
                return vague_type
        return None
    
    async def _handle_vague_command(
        self,
        raw_input: str,
        normalized: str,
        vague_type: str,
        context: Optional[Dict[str, Any]]
    ) -> ParsedIntent:
        """Handle vague commands using context"""
        context_used = []
        clarification = None
        tool_hint = None
        action_hint = None
        extracted_args = {}
        
        if vague_type == "repeat_last":
            # Use last action from context
            if self._last_intent:
                tool_hint = self._last_intent.tool_hint
                action_hint = self._last_intent.action_hint
                extracted_args = self._last_intent.extracted_args.copy()
                context_used.append("last_action")
            else:
                clarification = "What would you like me to do? I don't have a recent action to repeat."
        
        elif vague_type == "fix_error":
            # Look for recent errors in context
            if context and context.get("recent_errors"):
                context_used.append("recent_errors")
                clarification = "I see there was a recent error. Would you like me to try again or try a different approach?"
            else:
                clarification = "What would you like me to fix?"
        
        elif vague_type == "retry_last":
            if self._last_intent:
                tool_hint = self._last_intent.tool_hint
                action_hint = self._last_intent.action_hint
                extracted_args = self._last_intent.extracted_args.copy()
                context_used.append("last_action")
        
        elif vague_type == "user_preference":
            # Would need to check user preferences
            context_used.append("user_preferences")
            clarification = "What's your usual? I can check your preferences if you tell me what for."
        
        elif vague_type == "cancel":
            return ParsedIntent(
                raw_input=raw_input,
                normalized_input=normalized,
                intent_type=IntentType.CONFIRMATION,
                confidence=1.0,
                extracted_args={"cancel": True},
                context_used=["explicit_cancel"]
            )
        
        elif vague_type == "explain_last":
            context_used.append("last_action")
            if self._last_intent:
                clarification = f"I last tried to {self._last_intent.action_hint or 'do something'} using {self._last_intent.tool_hint or 'a tool'}."
        
        return ParsedIntent(
            raw_input=raw_input,
            normalized_input=normalized,
            intent_type=IntentType.VAGUE,
            confidence=0.5,
            tool_hint=tool_hint,
            action_hint=action_hint,
            extracted_args=extracted_args,
            needs_clarification=clarification is not None,
            clarification_question=clarification,
            context_used=context_used
        )
    
    def _detect_intent_type(self, text: str) -> Tuple[IntentType, float]:
        """Detect the type of intent"""
        best_type = IntentType.VAGUE
        best_confidence = 0.3
        
        for intent_type, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    confidence = 0.8
                    if confidence > best_confidence:
                        best_type = intent_type
                        best_confidence = confidence
        
        return best_type, best_confidence
    
    def _detect_tool(self, text: str) -> Optional[str]:
        """Detect which tool the user likely wants"""
        scores: Dict[str, int] = {}
        
        for tool, keywords in self.TOOL_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword in text:
                    score += 1
                    # Bonus for exact word match
                    if re.search(rf'\b{re.escape(keyword)}\b', text):
                        score += 1
            if score > 0:
                scores[tool] = score
        
        if scores:
            return max(scores, key=scores.get)
        return None
    
    def _detect_action(self, text: str) -> Optional[str]:
        """Detect the action verb"""
        action_verbs = ["open", "close", "find", "show", "create", "delete", "move", 
                       "copy", "save", "play", "pause", "mute", "run", "stop", "search"]
        
        for verb in action_verbs:
            if re.search(rf'\b{verb}\b', text):
                return verb
        
        return None
    
    def _extract_arguments(self, text: str, tool_hint: Optional[str]) -> Dict[str, Any]:
        """Extract arguments from text"""
        args = {}
        
        # Extract quoted strings
        quotes = re.findall(r'["\']([^"\']+)["\']', text)
        if quotes:
            args["quoted_values"] = quotes
        
        # Extract paths (Windows style)
        paths = re.findall(r'[A-Za-z]:\\[^\s"\']+', text)
        if paths:
            args["paths"] = paths
        
        # Extract URLs
        urls = re.findall(r'https?://[^\s]+', text)
        if urls:
            args["urls"] = urls
        
        # Extract numbers
        numbers = re.findall(r'\b\d+\b', text)
        if numbers:
            args["numbers"] = [int(n) for n in numbers]
        
        # Extract app names (common ones)
        apps = ["chrome", "firefox", "edge", "notepad", "code", "vscode", "spotify", 
                "discord", "steam", "explorer", "terminal", "powershell", "cmd"]
        for app in apps:
            if app in text:
                args["app"] = app
                break
        
        return args

    def _get_alternatives(self, text: str) -> List[str]:
        """Get alternative interpretations"""
        alternatives = []
        words = text.split()
        
        for word in words:
            # Find close matches in our vocabulary
            all_words = list(self._reverse_synonyms.keys())
            matches = get_close_matches(word, all_words, n=3, cutoff=0.6)
            for match in matches:
                if match != word:
                    alt = text.replace(word, match)
                    if alt not in alternatives:
                        alternatives.append(alt)
        
        return alternatives[:3]  # Max 3 alternatives
    
    def _generate_clarification(self, text: str, alternatives: List[str]) -> str:
        """Generate a clarification question"""
        if alternatives:
            alt_list = "\n".join(f"  {i+1}. {alt}" for i, alt in enumerate(alternatives))
            return f"I'm not sure I understood '{text[:30]}...'. Did you mean:\n{alt_list}\n  Or something else?"
        return "Could you please clarify what you'd like me to do?"
    
    def _check_learned_mapping(self, text: str) -> Optional[ParsedIntent]:
        """Check if we have a learned mapping for this input"""
        # Exact match
        if text in self._learned_mappings:
            mapping = self._learned_mappings[text]
            return ParsedIntent(
                raw_input=text,
                normalized_input=text,
                intent_type=IntentType(mapping.get("intent_type", "action")),
                confidence=0.95,
                tool_hint=mapping.get("tool"),
                action_hint=mapping.get("action"),
                extracted_args=mapping.get("args", {}),
                context_used=["learned_mapping"]
            )
        
        # Fuzzy match
        for learned_text, mapping in self._learned_mappings.items():
            similarity = SequenceMatcher(None, text, learned_text).ratio()
            if similarity > 0.85:
                return ParsedIntent(
                    raw_input=text,
                    normalized_input=text,
                    intent_type=IntentType(mapping.get("intent_type", "action")),
                    confidence=similarity,
                    tool_hint=mapping.get("tool"),
                    action_hint=mapping.get("action"),
                    extracted_args=mapping.get("args", {}),
                    context_used=["learned_mapping_fuzzy"]
                )
        
        return None
    
    async def learn_mapping(
        self,
        user_input: str,
        tool: str,
        action: str,
        args: Optional[Dict[str, Any]] = None,
        intent_type: IntentType = IntentType.ACTION
    ):
        """Learn a new mapping from user input to intent"""
        async with self._lock:
            normalized = self._normalize_input(user_input)
            self._learned_mappings[normalized] = {
                "tool": tool,
                "action": action,
                "args": args or {},
                "intent_type": intent_type.value,
                "learned_at": datetime.now().isoformat()
            }
            logging.info(f"Learned mapping: '{normalized}' -> {tool}.{action}")
            await self._save_learning()
    
    async def add_synonym(self, canonical: str, synonym: str):
        """Add a new synonym"""
        async with self._lock:
            if canonical in self.SYNONYMS:
                if synonym not in self.SYNONYMS[canonical]:
                    self.SYNONYMS[canonical].append(synonym)
            else:
                self.SYNONYMS[canonical] = [synonym]
            
            self._reverse_synonyms[synonym.lower()] = canonical
            logging.info(f"Added synonym: '{synonym}' -> '{canonical}'")
            await self._save_learning()
    
    async def get_canonical_form(self, word: str) -> str:
        """Get the canonical form of a word"""
        return self._reverse_synonyms.get(word.lower(), word)
    
    async def expand_synonyms(self, word: str) -> List[str]:
        """Get all synonyms for a word"""
        canonical = self._reverse_synonyms.get(word.lower(), word)
        if canonical in self.SYNONYMS:
            return [canonical] + self.SYNONYMS[canonical]
        return [word]
    
    async def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of recent context"""
        async with self._lock:
            return {
                "history_length": len(self._context_history),
                "recent_intents": [h["intent"] for h in self._context_history[-5:]],
                "last_intent": self._last_intent.intent_type.value if self._last_intent else None,
                "learned_mappings": len(self._learned_mappings)
            }
    
    async def _save_learning(self):
        """Save learned mappings to file"""
        try:
            # Build custom synonyms (only ones we added)
            custom_synonyms = {}
            for canonical, syns in self.SYNONYMS.items():
                # Check if any synonyms were added beyond defaults
                if canonical not in IntentParser.SYNONYMS or \
                   set(syns) != set(IntentParser.SYNONYMS.get(canonical, [])):
                    custom_synonyms[canonical] = syns
            
            data = {
                "last_updated": datetime.now().isoformat(),
                "learned_mappings": self._learned_mappings,
                "custom_synonyms": custom_synonyms
            }
            async with aiofiles.open(self.learning_file, 'w') as f:
                await f.write(json.dumps(data, indent=2))
        except Exception as e:
            logging.error(f"Failed to save intent learning: {e}")
    
    async def _load_learning(self):
        """Load learned mappings from file"""
        try:
            async with aiofiles.open(self.learning_file, 'r') as f:
                content = await f.read()
                data = json.loads(content)
            
            self._learned_mappings = data.get("learned_mappings", {})
            
            # Load custom synonyms
            for canonical, syns in data.get("custom_synonyms", {}).items():
                if canonical in self.SYNONYMS:
                    self.SYNONYMS[canonical].extend(s for s in syns if s not in self.SYNONYMS[canonical])
                else:
                    self.SYNONYMS[canonical] = syns
                
                # Update reverse lookup
                for syn in syns:
                    self._reverse_synonyms[syn.lower()] = canonical
                    
        except FileNotFoundError:
            pass
        except Exception as e:
            logging.warning(f"Error loading intent learning: {e}")
    
    async def cleanup(self):
        """Save learning before shutdown"""
        async with self._lock:
            await self._save_learning()
            logging.info("Intent parser learning saved")
