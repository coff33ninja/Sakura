"""
Proactive Suggestion Engine for Sakura
Suggests actions based on context, time, history, and patterns

Rules followed:
- All imports MUST be used
- Async with asyncio.Lock() for thread safety
- aiofiles for file I/O
"""
import asyncio
import logging
import re
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, time
from enum import Enum
import json
import aiofiles
import random


class SuggestionType(Enum):
    """Types of suggestions"""
    TIME_BASED = "time_based"          # Based on time of day
    CONTEXT_BASED = "context_based"    # Based on current activity
    HISTORY_BASED = "history_based"    # Based on past patterns
    ERROR_BASED = "error_based"        # After an error occurred
    PROACTIVE = "proactive"            # General helpful suggestions
    FOLLOW_UP = "follow_up"            # Follow-up to recent action


class SuggestionPriority(Enum):
    """Priority levels for suggestions"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


@dataclass
class Suggestion:
    """A proactive suggestion"""
    id: str
    type: SuggestionType
    priority: SuggestionPriority
    message: str
    action_tool: Optional[str] = None
    action_name: Optional[str] = None
    action_args: Dict[str, Any] = field(default_factory=dict)
    context_required: Optional[str] = None  # Context that must be present
    cooldown_minutes: int = 30              # Don't repeat for this long
    last_shown: Optional[str] = None
    times_shown: int = 0
    times_accepted: int = 0
    times_rejected: int = 0


@dataclass
class SuggestionFeedback:
    """Feedback on a suggestion"""
    suggestion_id: str
    accepted: bool
    timestamp: str
    context: Optional[str] = None


class SuggestionEngine:
    """Engine for generating proactive suggestions"""
    
    # Time-based suggestion rules
    TIME_RULES = [
        {
            "id": "morning_greeting",
            "start": time(6, 0),
            "end": time(10, 0),
            "message": "Good morning! Want me to check your calendar or read any news?",
            "priority": SuggestionPriority.LOW
        },
        {
            "id": "late_night_reminder",
            "start": time(23, 0),
            "end": time(3, 0),
            "message": "It's getting late. Want me to set a reminder for tomorrow before you go?",
            "priority": SuggestionPriority.MEDIUM
        },
        {
            "id": "lunch_break",
            "start": time(12, 0),
            "end": time(13, 0),
            "message": "It's lunch time! Want me to pause any running tasks or play some music?",
            "priority": SuggestionPriority.LOW
        },
        {
            "id": "end_of_day",
            "start": time(17, 0),
            "end": time(18, 0),
            "message": "End of work day approaching. Want me to summarize what we did today?",
            "priority": SuggestionPriority.LOW
        }
    ]
    
    # Context-based suggestion patterns
    CONTEXT_PATTERNS = [
        {
            "id": "python_testing",
            "pattern": r"\.py$|python|pytest|unittest",
            "context_type": "topic",
            "message": "I see you're working with Python. Want me to run tests or check for errors?",
            "action_tool": "windows",
            "action_name": "run_command",
            "action_args": {"command": "pytest", "shell": "powershell"},
            "priority": SuggestionPriority.MEDIUM
        },
        {
            "id": "git_status",
            "pattern": r"git|commit|push|pull|branch",
            "context_type": "topic",
            "message": "Working with git? Want me to check the repository status?",
            "action_tool": "windows",
            "action_name": "run_command",
            "action_args": {"command": "git status", "shell": "powershell"},
            "priority": SuggestionPriority.LOW
        },
        {
            "id": "file_backup",
            "pattern": r"important|document|project|work",
            "context_type": "topic",
            "message": "This seems important. Want me to create a backup?",
            "priority": SuggestionPriority.MEDIUM
        },
        {
            "id": "browser_research",
            "pattern": r"search|find|look\s*up|research|how\s*to",
            "context_type": "topic",
            "message": "Need more information? I can search the web for you.",
            "action_tool": "web_search",
            "action_name": "search",
            "priority": SuggestionPriority.LOW
        }
    ]
    
    # Error-based suggestions
    ERROR_SUGGESTIONS = {
        "permission": {
            "message": "That needed admin rights. Want me to try running as administrator?",
            "priority": SuggestionPriority.HIGH
        },
        "not_found": {
            "message": "Couldn't find that. Want me to search for similar files or apps?",
            "priority": SuggestionPriority.MEDIUM
        },
        "network": {
            "message": "Network issue detected. Want me to check your connection?",
            "action_tool": "windows",
            "action_name": "run_command",
            "action_args": {"command": "ping google.com", "shell": "powershell"},
            "priority": SuggestionPriority.MEDIUM
        },
        "timeout": {
            "message": "That took too long. Want me to try again or try a different approach?",
            "priority": SuggestionPriority.MEDIUM
        }
    }
    
    def __init__(self, suggestions_file: str = "suggestion_history.json"):
        self.suggestions_file = suggestions_file
        self._lock = asyncio.Lock()
        self._suggestions: Dict[str, Suggestion] = {}
        self._feedback_history: List[SuggestionFeedback] = []
        self._suggestion_cooldowns: Dict[str, datetime] = {}
        self._min_interval = timedelta(minutes=5)  # Min time between any suggestions
        self._last_suggestion_time: Optional[datetime] = None
        self._context_callback: Optional[Callable] = None
        self._enabled = True
    
    async def initialize(self) -> bool:
        """Initialize suggestion engine"""
        async with self._lock:
            try:
                # Build suggestions first, then load history to restore stats
                self._build_suggestions()
                await self._load_history()
                logging.info(f"Suggestion engine initialized with {len(self._suggestions)} suggestions")
                return True
            except Exception as e:
                logging.warning(f"Could not load suggestion history: {e}")
                self._build_suggestions()
                return True
    
    def _build_suggestions(self):
        """Build suggestion catalog from rules"""
        # Time-based suggestions
        for rule in self.TIME_RULES:
            self._suggestions[rule["id"]] = Suggestion(
                id=rule["id"],
                type=SuggestionType.TIME_BASED,
                priority=rule["priority"],
                message=rule["message"],
                cooldown_minutes=60  # Time-based suggestions once per hour
            )
        
        # Context-based suggestions
        for pattern in self.CONTEXT_PATTERNS:
            self._suggestions[pattern["id"]] = Suggestion(
                id=pattern["id"],
                type=SuggestionType.CONTEXT_BASED,
                priority=pattern["priority"],
                message=pattern["message"],
                action_tool=pattern.get("action_tool"),
                action_name=pattern.get("action_name"),
                action_args=pattern.get("action_args", {}),
                context_required=pattern["pattern"],
                cooldown_minutes=30
            )
        
        # Error-based suggestions
        for error_type, config in self.ERROR_SUGGESTIONS.items():
            self._suggestions[f"error_{error_type}"] = Suggestion(
                id=f"error_{error_type}",
                type=SuggestionType.ERROR_BASED,
                priority=config["priority"],
                message=config["message"],
                action_tool=config.get("action_tool"),
                action_name=config.get("action_name"),
                action_args=config.get("action_args", {}),
                cooldown_minutes=15
            )

    async def get_suggestion(
        self,
        context: Optional[Dict[str, Any]] = None,
        recent_error: Optional[str] = None,
        force: bool = False
    ) -> Optional[Suggestion]:
        """
        Get a relevant suggestion based on current context
        
        Args:
            context: Current context (topics, mood, recent actions)
            recent_error: Recent error message if any
            force: Bypass cooldowns
        
        Returns:
            A suggestion or None
        """
        if not self._enabled and not force:
            return None
        
        async with self._lock:
            # Check global cooldown
            if not force and self._last_suggestion_time:
                if datetime.now() - self._last_suggestion_time < self._min_interval:
                    return None
            
            candidates: List[Tuple[Suggestion, float]] = []
            
            # Check error-based suggestions first (highest priority)
            if recent_error:
                error_suggestion = self._get_error_suggestion(recent_error)
                if error_suggestion and self._can_show(error_suggestion):
                    candidates.append((error_suggestion, 10.0))
            
            # Check time-based suggestions
            time_suggestion = self._get_time_suggestion()
            if time_suggestion and self._can_show(time_suggestion):
                candidates.append((time_suggestion, 5.0))
            
            # Check context-based suggestions
            if context:
                context_suggestions = self._get_context_suggestions(context)
                for sugg in context_suggestions:
                    if self._can_show(sugg):
                        # Score based on acceptance rate
                        score = self._calculate_score(sugg)
                        candidates.append((sugg, score))
            
            if not candidates:
                return None
            
            # Sort by score and priority
            candidates.sort(key=lambda x: (x[0].priority.value, x[1]), reverse=True)
            
            # Pick the best one (with some randomness for variety)
            if len(candidates) > 1 and random.random() < 0.3:
                selected = random.choice(candidates[:3])[0]
            else:
                selected = candidates[0][0]
            
            # Update tracking
            selected.times_shown += 1
            selected.last_shown = datetime.now().isoformat()
            self._suggestion_cooldowns[selected.id] = datetime.now()
            self._last_suggestion_time = datetime.now()
            
            return selected
    
    def _get_error_suggestion(self, error_message: str) -> Optional[Suggestion]:
        """Get suggestion based on error type"""
        error_lower = error_message.lower()
        
        if any(w in error_lower for w in ["permission", "access denied", "admin"]):
            return self._suggestions.get("error_permission")
        elif any(w in error_lower for w in ["not found", "missing", "no such"]):
            return self._suggestions.get("error_not_found")
        elif any(w in error_lower for w in ["network", "connection", "unreachable"]):
            return self._suggestions.get("error_network")
        elif any(w in error_lower for w in ["timeout", "timed out"]):
            return self._suggestions.get("error_timeout")
        
        return None
    
    def _get_time_suggestion(self) -> Optional[Suggestion]:
        """Get suggestion based on current time"""
        now = datetime.now().time()
        
        for rule in self.TIME_RULES:
            start = rule["start"]
            end = rule["end"]
            
            # Handle overnight ranges (e.g., 23:00 to 03:00)
            if start > end:
                if now >= start or now <= end:
                    return self._suggestions.get(rule["id"])
            else:
                if start <= now <= end:
                    return self._suggestions.get(rule["id"])
        
        return None
    
    def _get_context_suggestions(self, context: Dict[str, Any]) -> List[Suggestion]:
        """Get suggestions based on context"""
        suggestions = []
        
        # Get topics from context
        topics = context.get("topics", [])
        recent_text = context.get("recent_text", "")
        combined = " ".join(topics) + " " + recent_text
        
        for pattern_config in self.CONTEXT_PATTERNS:
            pattern = pattern_config["pattern"]
            if re.search(pattern, combined, re.IGNORECASE):
                sugg = self._suggestions.get(pattern_config["id"])
                if sugg:
                    suggestions.append(sugg)
        
        return suggestions
    
    def _can_show(self, suggestion: Suggestion) -> bool:
        """Check if suggestion can be shown (not on cooldown)"""
        if suggestion.id in self._suggestion_cooldowns:
            last_shown = self._suggestion_cooldowns[suggestion.id]
            cooldown = timedelta(minutes=suggestion.cooldown_minutes)
            if datetime.now() - last_shown < cooldown:
                return False
        
        # Don't show suggestions that are consistently rejected
        if suggestion.times_shown > 5:
            acceptance_rate = suggestion.times_accepted / suggestion.times_shown
            if acceptance_rate < 0.1:  # Less than 10% acceptance
                return False
        
        return True
    
    def _calculate_score(self, suggestion: Suggestion) -> float:
        """Calculate relevance score for a suggestion"""
        base_score = suggestion.priority.value
        
        # Boost based on acceptance rate
        if suggestion.times_shown > 0:
            acceptance_rate = suggestion.times_accepted / suggestion.times_shown
            base_score += acceptance_rate * 2
        
        # Slight penalty for frequently shown suggestions
        if suggestion.times_shown > 10:
            base_score -= 0.5
        
        return base_score
    
    async def record_feedback(self, suggestion_id: str, accepted: bool, context: Optional[str] = None):
        """Record user feedback on a suggestion"""
        async with self._lock:
            if suggestion_id in self._suggestions:
                sugg = self._suggestions[suggestion_id]
                if accepted:
                    sugg.times_accepted += 1
                else:
                    sugg.times_rejected += 1
                
                self._feedback_history.append(SuggestionFeedback(
                    suggestion_id=suggestion_id,
                    accepted=accepted,
                    timestamp=datetime.now().isoformat(),
                    context=context
                ))
                
                # Keep only last 100 feedback entries
                if len(self._feedback_history) > 100:
                    self._feedback_history = self._feedback_history[-100:]
                
                await self._save_history()
                logging.info(f"Recorded feedback for {suggestion_id}: {'accepted' if accepted else 'rejected'}")

    async def add_custom_suggestion(
        self,
        suggestion_id: str,
        message: str,
        suggestion_type: SuggestionType = SuggestionType.PROACTIVE,
        priority: SuggestionPriority = SuggestionPriority.MEDIUM,
        action_tool: Optional[str] = None,
        action_name: Optional[str] = None,
        action_args: Optional[Dict[str, Any]] = None,
        context_pattern: Optional[str] = None,
        cooldown_minutes: int = 30
    ):
        """Add a custom suggestion"""
        async with self._lock:
            self._suggestions[suggestion_id] = Suggestion(
                id=suggestion_id,
                type=suggestion_type,
                priority=priority,
                message=message,
                action_tool=action_tool,
                action_name=action_name,
                action_args=action_args or {},
                context_required=context_pattern,
                cooldown_minutes=cooldown_minutes
            )
            logging.info(f"Added custom suggestion: {suggestion_id}")
    
    async def get_follow_up_suggestion(
        self,
        last_tool: str,
        last_action: str,
        last_result: Any
    ) -> Optional[Suggestion]:
        """Get a follow-up suggestion based on last action"""
        async with self._lock:
            # Follow-up suggestions based on common patterns
            follow_ups = {
                ("windows", "search_files"): {
                    "message": "Found some files. Want me to open one or create a backup?",
                    "priority": SuggestionPriority.LOW
                },
                ("windows", "execute_script"): {
                    "message": "Script executed. Want me to save it for later or run it again?",
                    "priority": SuggestionPriority.LOW
                },
                ("system_info", "get_hardware"): {
                    "message": "Got your hardware info. Want me to check for driver updates or monitor temps?",
                    "priority": SuggestionPriority.LOW
                },
                ("web_search", "search"): {
                    "message": "Found some results. Want me to fetch more details from any of these?",
                    "priority": SuggestionPriority.LOW
                },
                ("memory", "store"): {
                    "message": "Saved that. Want me to recall related memories?",
                    "priority": SuggestionPriority.LOW
                }
            }
            
            key = (last_tool, last_action)
            if key in follow_ups:
                config = follow_ups[key]
                sugg_id = f"followup_{last_tool}_{last_action}"
                
                if sugg_id not in self._suggestions:
                    self._suggestions[sugg_id] = Suggestion(
                        id=sugg_id,
                        type=SuggestionType.FOLLOW_UP,
                        priority=config["priority"],
                        message=config["message"],
                        cooldown_minutes=10
                    )
                
                sugg = self._suggestions[sugg_id]
                if self._can_show(sugg):
                    sugg.times_shown += 1
                    sugg.last_shown = datetime.now().isoformat()
                    self._suggestion_cooldowns[sugg_id] = datetime.now()
                    return sugg
            
            return None
    
    async def set_enabled(self, enabled: bool):
        """Enable or disable suggestions"""
        async with self._lock:
            self._enabled = enabled
            logging.info(f"Suggestions {'enabled' if enabled else 'disabled'}")
    
    async def set_min_interval(self, minutes: int):
        """Set minimum interval between suggestions"""
        async with self._lock:
            self._min_interval = timedelta(minutes=minutes)
            logging.info(f"Suggestion interval set to {minutes} minutes")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get suggestion statistics"""
        async with self._lock:
            total_shown = sum(s.times_shown for s in self._suggestions.values())
            total_accepted = sum(s.times_accepted for s in self._suggestions.values())
            
            return {
                "total_suggestions": len(self._suggestions),
                "total_shown": total_shown,
                "total_accepted": total_accepted,
                "acceptance_rate": f"{(total_accepted/total_shown*100):.1f}%" if total_shown > 0 else "N/A",
                "enabled": self._enabled,
                "min_interval_minutes": self._min_interval.total_seconds() / 60,
                "top_accepted": sorted(
                    [(s.id, s.times_accepted) for s in self._suggestions.values()],
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
            }
    
    async def _save_history(self):
        """Save suggestion history to file"""
        try:
            data = {
                "last_updated": datetime.now().isoformat(),
                "suggestions": {
                    sid: {
                        "times_shown": s.times_shown,
                        "times_accepted": s.times_accepted,
                        "times_rejected": s.times_rejected,
                        "last_shown": s.last_shown
                    }
                    for sid, s in self._suggestions.items()
                },
                "feedback": [
                    {
                        "suggestion_id": f.suggestion_id,
                        "accepted": f.accepted,
                        "timestamp": f.timestamp,
                        "context": f.context
                    }
                    for f in self._feedback_history[-50:]
                ]
            }
            async with aiofiles.open(self.suggestions_file, 'w') as f:
                await f.write(json.dumps(data, indent=2))
        except Exception as e:
            logging.error(f"Failed to save suggestion history: {e}")
    
    async def _load_history(self):
        """Load suggestion history from file"""
        try:
            async with aiofiles.open(self.suggestions_file, 'r') as f:
                content = await f.read()
                data = json.loads(content)
            
            # Restore suggestion stats
            for sid, stats in data.get("suggestions", {}).items():
                if sid in self._suggestions:
                    self._suggestions[sid].times_shown = stats.get("times_shown", 0)
                    self._suggestions[sid].times_accepted = stats.get("times_accepted", 0)
                    self._suggestions[sid].times_rejected = stats.get("times_rejected", 0)
                    self._suggestions[sid].last_shown = stats.get("last_shown")
            
            # Restore feedback history
            for f_data in data.get("feedback", []):
                self._feedback_history.append(SuggestionFeedback(
                    suggestion_id=f_data["suggestion_id"],
                    accepted=f_data["accepted"],
                    timestamp=f_data["timestamp"],
                    context=f_data.get("context")
                ))
                
        except FileNotFoundError:
            pass
        except Exception as e:
            logging.warning(f"Error loading suggestion history: {e}")
    
    async def cleanup(self):
        """Save history before shutdown"""
        async with self._lock:
            await self._save_history()
            logging.info("Suggestion history saved")
