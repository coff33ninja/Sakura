"""
User Preferences Manager for Sakura
Learns from user corrections and remembers preferences

Rules followed:
- All imports MUST be used
- Async with asyncio.Lock() for thread safety
- aiofiles for file I/O (fallback)
- Database integration for corrections and preferences
"""
import asyncio
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import aiofiles
from difflib import SequenceMatcher

# Import database module
try:
    from modules.database import get_database, HAS_AIOSQLITE
except ImportError:
    HAS_AIOSQLITE = False
    get_database = None


class PreferenceType(Enum):
    """Types of user preferences"""
    CORRECTION = "correction"      # "When I say X, I mean Y"
    PREFERENCE = "preference"      # "Always use X instead of Y"
    SHORTCUT = "shortcut"          # "My project = path"
    DEFAULT = "default"            # Default values for actions
    BEHAVIOR = "behavior"          # How to behave in certain situations


@dataclass
class Correction:
    """A learned correction from user feedback"""
    trigger_phrase: str
    intended_tool: str
    intended_action: str
    intended_args: Dict[str, Any]
    created_at: str
    use_count: int = 0
    last_used: Optional[str] = None
    confidence: float = 1.0
    db_id: Optional[int] = None  # Database ID for syncing


@dataclass
class Preference:
    """A user preference for tool behavior"""
    category: str
    key: str
    value: Any
    created_at: str
    updated_at: str
    source: str = "explicit"
    db_id: Optional[int] = None


@dataclass
class Shortcut:
    """A user-defined shortcut/alias"""
    phrase: str
    expansion: str
    context: Optional[str] = None
    created_at: str = ""
    use_count: int = 0
    tags: List[str] = field(default_factory=list)


class UserPreferences:
    """Manages user preferences, corrections, and shortcuts"""
    
    CORRECTION_PATTERNS = [
        (r"no,?\s*i\s*meant", "correction"),
        (r"actually,?\s*(?:i\s*wanted|use|open|run)", "correction"),
        (r"not\s+that,?\s*(?:i\s*meant|the\s*other)", "correction"),
        (r"wrong\s+(?:one|app|file|folder)", "correction"),
        (r"i\s*said\s+(\w+),?\s*not\s+(\w+)", "correction"),
        (r"that'?s?\s*not\s*(?:what\s*i|right)", "correction"),
    ]
    
    PREFERENCE_PATTERNS = [
        (r"always\s+use\s+(\w+)", "preference"),
        (r"(?:from\s*now\s*on|in\s*the\s*future),?\s*use\s+(\w+)", "preference"),
        (r"i\s*prefer\s+(\w+)", "preference"),
        (r"default\s+(?:to|should\s*be)\s+(\w+)", "preference"),
        (r"never\s+use\s+(\w+)", "negative_preference"),
    ]
    
    SHORTCUT_PATTERNS = [
        (r"(?:remember\s*that\s*)?['\"]?(.+?)['\"]?\s*(?:is|means|=|refers\s*to)\s*['\"]?(.+?)['\"]?$", "shortcut"),
        (r"when\s*i\s*say\s*['\"]?(.+?)['\"]?,?\s*(?:i\s*mean|it\s*means)\s*['\"]?(.+?)['\"]?", "shortcut"),
        (r"call\s+['\"]?(.+?)['\"]?\s+['\"]?(.+?)['\"]?", "shortcut"),
    ]
    
    def __init__(self, preferences_file: str = "user_preferences.json", db_path: str = "sakura.db"):
        self.preferences_file = preferences_file
        self.db_path = db_path
        self._lock = asyncio.Lock()
        self._corrections: List[Correction] = []
        self._preferences: Dict[str, Preference] = {}
        self._shortcuts: Dict[str, Shortcut] = {}
        self._preference_expiry = timedelta(days=30)
        self._last_action: Optional[Dict[str, Any]] = None
        self._db = None
        self._use_db = HAS_AIOSQLITE and get_database is not None
    
    async def initialize(self) -> bool:
        """Initialize preferences, connect to database"""
        async with self._lock:
            try:
                # Try to connect to database
                if self._use_db and get_database:
                    try:
                        self._db = await get_database(self.db_path)
                        logging.info("User preferences connected to database")
                        
                        # Load from database first
                        await self._load_from_database()
                        
                        # Migrate JSON data if exists
                        await self._migrate_json_to_db()
                    except Exception as e:
                        logging.warning(f"Database connection failed, using JSON fallback: {e}")
                        self._db = None
                        self._use_db = False
                
                # Load from JSON as fallback
                if not self._db:
                    await self._load_preferences()
                
                logging.info(f"User preferences loaded: {len(self._corrections)} corrections, "
                           f"{len(self._preferences)} preferences, {len(self._shortcuts)} shortcuts")
                return True
            except Exception as e:
                logging.warning(f"Could not load preferences: {e}")
                return True
    
    async def _load_from_database(self):
        """Load corrections and preferences from database"""
        if not self._db:
            return
        
        try:
            # Load learned corrections
            db_corrections = await self._db.select(
                "learned_corrections",
                "*",
                order_by="created_at DESC",
                limit=100
            )
            
            for corr in db_corrections:
                # Parse correct_behavior as JSON if it contains tool info
                correct_behavior = corr.get("correct_behavior", "")
                intended_args = {}
                
                try:
                    if correct_behavior.startswith("{"):
                        behavior_data = json.loads(correct_behavior)
                        intended_args = behavior_data.get("args", {})
                except (json.JSONDecodeError, AttributeError):
                    pass
                
                self._corrections.append(Correction(
                    trigger_phrase=corr.get("trigger_pattern", ""),
                    intended_tool=corr.get("tool_name", ""),
                    intended_action=corr.get("action_name", ""),
                    intended_args=intended_args,
                    created_at=corr.get("created_at", ""),
                    use_count=corr.get("use_count", 0),
                    last_used=corr.get("last_used"),
                    confidence=corr.get("confidence", 1.0),
                    db_id=corr.get("id")
                ))
            
            # Load user_info as preferences
            db_prefs = await self._db.select("user_info", "*")
            for pref in db_prefs:
                key = pref.get("key", "")
                category = pref.get("category", "general")
                pref_key = f"{category}.{key}" if category else key
                
                self._preferences[pref_key] = Preference(
                    category=category,
                    key=key,
                    value=pref.get("value"),
                    created_at=pref.get("created_at", ""),
                    updated_at=pref.get("updated_at", ""),
                    source="database",
                    db_id=pref.get("id")
                )
            
            logging.info(f"Loaded {len(self._corrections)} corrections and {len(self._preferences)} preferences from database")
            
        except Exception as e:
            logging.warning(f"Error loading from database: {e}")
    
    async def _migrate_json_to_db(self):
        """Migrate existing JSON preferences to database"""
        if not self._db:
            return
        
        try:
            async with aiofiles.open(self.preferences_file, 'r') as f:
                content = await f.read()
                data = json.loads(content)
            
            migrated_corrections = 0
            migrated_prefs = 0
            
            # Migrate corrections
            for c_data in data.get("corrections", []):
                trigger = c_data.get("trigger_phrase", "")
                
                # Check if already in database
                existing = await self._db.select_one(
                    "learned_corrections",
                    "*",
                    "trigger_pattern = ?",
                    (trigger,)
                )
                
                if not existing:
                    correct_behavior = json.dumps({
                        "tool": c_data.get("intended_tool", ""),
                        "action": c_data.get("intended_action", ""),
                        "args": c_data.get("intended_args", {})
                    })
                    
                    await self._db.insert("learned_corrections", {
                        "trigger_pattern": trigger,
                        "correct_behavior": correct_behavior,
                        "tool_name": c_data.get("intended_tool", ""),
                        "action_name": c_data.get("intended_action", ""),
                        "confidence": c_data.get("confidence", 1.0),
                        "use_count": c_data.get("use_count", 0),
                        "is_permanent": 1,
                        "created_at": c_data.get("created_at", datetime.now().isoformat())
                    })
                    migrated_corrections += 1
            
            # Migrate preferences to user_info
            for key, p_data in data.get("preferences", {}).items():
                existing = await self._db.select_one(
                    "user_info",
                    "*",
                    "key = ?",
                    (p_data.get("key", key),)
                )
                
                if not existing:
                    await self._db.insert("user_info", {
                        "key": p_data.get("key", key),
                        "value": str(p_data.get("value", "")),
                        "category": p_data.get("category", "general"),
                        "created_at": p_data.get("created_at", datetime.now().isoformat()),
                        "updated_at": p_data.get("updated_at", datetime.now().isoformat())
                    })
                    migrated_prefs += 1
            
            if migrated_corrections > 0 or migrated_prefs > 0:
                logging.info(f"Migrated {migrated_corrections} corrections and {migrated_prefs} preferences to database")
                
        except FileNotFoundError:
            pass
        except Exception as e:
            logging.debug(f"JSON migration skipped: {e}")

    async def detect_correction(self, user_input: str) -> Tuple[bool, Optional[str]]:
        """Detect if user input is a correction"""
        input_lower = user_input.lower()
        
        for pattern, ptype in self.CORRECTION_PATTERNS:
            if re.search(pattern, input_lower):
                return True, ptype
        
        return False, None
    
    async def detect_preference_setting(self, user_input: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Detect if user is setting a preference"""
        input_lower = user_input.lower()
        
        for pattern, ptype in self.PREFERENCE_PATTERNS:
            match = re.search(pattern, input_lower)
            if match:
                value = match.group(1) if match.groups() else None
                return True, ptype, value
        
        return False, None, None
    
    async def detect_shortcut_definition(self, user_input: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Detect if user is defining a shortcut"""
        for pattern, _ in self.SHORTCUT_PATTERNS:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match and len(match.groups()) >= 2:
                phrase = match.group(1).strip()
                expansion = match.group(2).strip()
                if phrase and expansion and len(phrase) < len(expansion):
                    return True, phrase, expansion
        
        return False, None, None
    
    async def record_last_action(self, tool_name: str, action: str, args: Dict[str, Any]):
        """Record the last action for correction context"""
        async with self._lock:
            self._last_action = {
                "tool_name": tool_name,
                "action": action,
                "args": args,
                "timestamp": datetime.now().isoformat()
            }
    
    async def learn_correction(
        self,
        trigger_phrase: str,
        intended_tool: str,
        intended_action: str,
        intended_args: Dict[str, Any]
    ) -> bool:
        """Learn a correction from user feedback"""
        async with self._lock:
            # Check for existing similar correction
            for corr in self._corrections:
                similarity = SequenceMatcher(None, corr.trigger_phrase.lower(), 
                                            trigger_phrase.lower()).ratio()
                if similarity > 0.8:
                    # Update existing correction
                    corr.intended_tool = intended_tool
                    corr.intended_action = intended_action
                    corr.intended_args = intended_args
                    corr.confidence = min(1.0, corr.confidence + 0.1)
                    
                    # Update in database
                    if self._db and corr.db_id:
                        await self._update_correction_in_db(corr)
                    
                    logging.info(f"Updated correction: '{trigger_phrase}' -> {intended_tool}.{intended_action}")
                    await self._save_preferences()
                    return True
            
            # Add new correction
            correction = Correction(
                trigger_phrase=trigger_phrase,
                intended_tool=intended_tool,
                intended_action=intended_action,
                intended_args=intended_args,
                created_at=datetime.now().isoformat()
            )
            
            # Save to database
            if self._db:
                db_id = await self._save_correction_to_db(correction)
                correction.db_id = db_id
            
            self._corrections.append(correction)
            logging.info(f"Learned correction: '{trigger_phrase}' -> {intended_tool}.{intended_action}")
            await self._save_preferences()
            return True
    
    async def _save_correction_to_db(self, correction: Correction) -> Optional[int]:
        """Save a correction to the database"""
        if not self._db:
            return None
        
        try:
            correct_behavior = json.dumps({
                "tool": correction.intended_tool,
                "action": correction.intended_action,
                "args": correction.intended_args
            })
            
            return await self._db.insert("learned_corrections", {
                "trigger_pattern": correction.trigger_phrase,
                "correct_behavior": correct_behavior,
                "tool_name": correction.intended_tool,
                "action_name": correction.intended_action,
                "confidence": correction.confidence,
                "use_count": correction.use_count,
                "is_permanent": 1,
                "created_at": correction.created_at
            })
        except Exception as e:
            logging.debug(f"Failed to save correction to database: {e}")
            return None
    
    async def _update_correction_in_db(self, correction: Correction):
        """Update a correction in the database"""
        if not self._db or not correction.db_id:
            return
        
        try:
            correct_behavior = json.dumps({
                "tool": correction.intended_tool,
                "action": correction.intended_action,
                "args": correction.intended_args
            })
            
            await self._db.update(
                "learned_corrections",
                {
                    "correct_behavior": correct_behavior,
                    "tool_name": correction.intended_tool,
                    "action_name": correction.intended_action,
                    "confidence": correction.confidence,
                    "use_count": correction.use_count,
                    "last_used": correction.last_used
                },
                "id = ?",
                (correction.db_id,)
            )
        except Exception as e:
            logging.debug(f"Failed to update correction in database: {e}")

    async def set_preference(
        self,
        category: str,
        key: str,
        value: Any,
        source: str = "explicit"
    ) -> bool:
        """Set a user preference"""
        async with self._lock:
            pref_key = f"{category}.{key}"
            now = datetime.now().isoformat()
            
            if pref_key in self._preferences:
                self._preferences[pref_key].value = value
                self._preferences[pref_key].updated_at = now
                self._preferences[pref_key].source = source
                
                # Update in database
                if self._db and self._preferences[pref_key].db_id:
                    await self._db.update(
                        "user_info",
                        {"value": str(value), "updated_at": now},
                        "id = ?",
                        (self._preferences[pref_key].db_id,)
                    )
            else:
                pref = Preference(
                    category=category,
                    key=key,
                    value=value,
                    created_at=now,
                    updated_at=now,
                    source=source
                )
                
                # Save to database
                if self._db:
                    db_id = await self._db.insert("user_info", {
                        "key": key,
                        "value": str(value),
                        "category": category,
                        "created_at": now,
                        "updated_at": now
                    })
                    pref.db_id = db_id
                
                self._preferences[pref_key] = pref
            
            logging.info(f"Set preference: {pref_key} = {value}")
            await self._save_preferences()
            return True
    
    async def get_preference(self, category: str, key: str, default: Any = None) -> Any:
        """Get a user preference"""
        async with self._lock:
            pref_key = f"{category}.{key}"
            if pref_key in self._preferences:
                return self._preferences[pref_key].value
            return default
    
    async def add_shortcut(
        self,
        phrase: str,
        expansion: str,
        context: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """Add a user shortcut"""
        async with self._lock:
            phrase_lower = phrase.lower()
            
            self._shortcuts[phrase_lower] = Shortcut(
                phrase=phrase,
                expansion=expansion,
                context=context,
                created_at=datetime.now().isoformat(),
                tags=tags or []
            )
            
            logging.info(f"Added shortcut: '{phrase}' -> '{expansion}'")
            await self._save_preferences()
            return True
    
    async def expand_shortcuts(self, text: str) -> str:
        """Expand any shortcuts in the text"""
        async with self._lock:
            result = text
            
            for phrase_lower, shortcut in self._shortcuts.items():
                pattern = re.compile(re.escape(shortcut.phrase), re.IGNORECASE)
                if pattern.search(result):
                    result = pattern.sub(lambda m: shortcut.expansion, result)
                    shortcut.use_count += 1
                    logging.debug(f"Expanded shortcut: '{shortcut.phrase}' -> '{shortcut.expansion}'")
            
            return result
    
    async def find_matching_correction(self, user_input: str) -> Optional[Correction]:
        """Find a correction that matches the user input"""
        async with self._lock:
            input_lower = user_input.lower()
            best_match = None
            best_score = 0.6
            
            for correction in self._corrections:
                if correction.trigger_phrase.lower() in input_lower:
                    score = 0.9
                else:
                    score = SequenceMatcher(None, correction.trigger_phrase.lower(), 
                                           input_lower).ratio()
                
                if score > best_score:
                    best_score = score
                    best_match = correction
            
            if best_match:
                best_match.use_count += 1
                best_match.last_used = datetime.now().isoformat()
                
                # Update in database
                if self._db and best_match.db_id:
                    await self._update_correction_in_db(best_match)
                
                logging.info(f"Found matching correction: '{best_match.trigger_phrase}' (score: {best_score:.2f})")
            
            return best_match
    
    async def get_corrections_for_tool(self, tool_name: str, action_name: str = None) -> List[Correction]:
        """Get all corrections for a specific tool/action"""
        # Try database first for more comprehensive results
        if self._db:
            try:
                if action_name:
                    db_corrs = await self._db.select(
                        "learned_corrections",
                        "*",
                        "tool_name = ? AND action_name = ? AND confidence > 0.3",
                        (tool_name, action_name),
                        order_by="confidence DESC",
                        limit=10
                    )
                else:
                    db_corrs = await self._db.select(
                        "learned_corrections",
                        "*",
                        "tool_name = ? AND confidence > 0.3",
                        (tool_name,),
                        order_by="confidence DESC",
                        limit=10
                    )
                
                corrections = []
                for corr in db_corrs:
                    intended_args = {}
                    try:
                        behavior = corr.get("correct_behavior", "{}")
                        if behavior.startswith("{"):
                            data = json.loads(behavior)
                            intended_args = data.get("args", {})
                    except (json.JSONDecodeError, AttributeError):
                        pass
                    
                    corrections.append(Correction(
                        trigger_phrase=corr.get("trigger_pattern", ""),
                        intended_tool=corr.get("tool_name", ""),
                        intended_action=corr.get("action_name", ""),
                        intended_args=intended_args,
                        created_at=corr.get("created_at", ""),
                        use_count=corr.get("use_count", 0),
                        confidence=corr.get("confidence", 1.0),
                        db_id=corr.get("id")
                    ))
                
                return corrections
            except Exception as e:
                logging.debug(f"Database query failed: {e}")
        
        # Fallback to in-memory
        async with self._lock:
            return [c for c in self._corrections 
                    if c.intended_tool == tool_name and 
                    (action_name is None or c.intended_action == action_name)]

    async def apply_preferences_to_args(
        self,
        tool_name: str,
        action: str,
        args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply user preferences to tool arguments"""
        async with self._lock:
            modified_args = args.copy()
            
            # Apply tool-specific preferences
            tool_prefs = {k: v for k, v in self._preferences.items() 
                        if k.startswith(f"{tool_name}.")}
            
            for pref_key, pref in tool_prefs.items():
                arg_name = pref_key.split(".")[-1]
                if arg_name not in modified_args:
                    modified_args[arg_name] = pref.value
                    logging.debug(f"Applied preference: {arg_name} = {pref.value}")
            
            # Apply general preferences
            if tool_name == "windows" and action == "run_command":
                shell_pref = self._get_preference_unlocked("shell", "default")
                if shell_pref and "shell" not in modified_args:
                    modified_args["shell"] = shell_pref
            
            if action == "open_app":
                app = args.get("app", "").lower()
                if app in ["browser", "web browser"]:
                    browser_pref = self._get_preference_unlocked("apps", "browser")
                    if browser_pref:
                        modified_args["app"] = browser_pref
                elif app in ["editor", "text editor", "code editor"]:
                    editor_pref = self._get_preference_unlocked("apps", "editor")
                    if editor_pref:
                        modified_args["app"] = editor_pref
            
            # Expand shortcuts in string arguments
            for key, value in modified_args.items():
                if isinstance(value, str):
                    expanded = self._expand_shortcuts_unlocked(value)
                    if expanded != value:
                        modified_args[key] = expanded
            
            return modified_args
    
    def _get_preference_unlocked(self, category: str, key: str, default: Any = None) -> Any:
        """Get a user preference without acquiring lock"""
        pref_key = f"{category}.{key}"
        if pref_key in self._preferences:
            return self._preferences[pref_key].value
        return default
    
    def _expand_shortcuts_unlocked(self, text: str) -> str:
        """Expand shortcuts without acquiring lock"""
        result = text
        for phrase_lower, shortcut in self._shortcuts.items():
            pattern = re.compile(re.escape(shortcut.phrase), re.IGNORECASE)
            if pattern.search(result):
                result = pattern.sub(lambda m: shortcut.expansion, result)
                shortcut.use_count += 1
        return result
    
    async def get_all_preferences(self) -> Dict[str, Any]:
        """Get all preferences as a dictionary"""
        async with self._lock:
            return {
                "corrections": [
                    {
                        "trigger": c.trigger_phrase,
                        "tool": c.intended_tool,
                        "action": c.intended_action,
                        "use_count": c.use_count,
                        "confidence": c.confidence,
                        "db_synced": c.db_id is not None
                    }
                    for c in self._corrections
                ],
                "preferences": {
                    k: {"value": v.value, "source": v.source, "db_synced": v.db_id is not None}
                    for k, v in self._preferences.items()
                },
                "shortcuts": {
                    k: {"expansion": v.expansion, "use_count": v.use_count}
                    for k, v in self._shortcuts.items()
                },
                "source": "database" if self._db else "json"
            }
    
    async def get_preference_stats(self) -> Dict[str, Any]:
        """Get statistics about preferences"""
        if self._db:
            try:
                total_corrections = await self._db.count("learned_corrections")
                total_prefs = await self._db.count("user_info")
                high_confidence = await self._db.count("learned_corrections", "confidence >= 0.8")
                
                return {
                    "total_corrections": total_corrections,
                    "total_preferences": total_prefs,
                    "high_confidence_corrections": high_confidence,
                    "shortcuts": len(self._shortcuts),
                    "source": "database"
                }
            except Exception as e:
                logging.debug(f"Database stats failed: {e}")
        
        return {
            "total_corrections": len(self._corrections),
            "total_preferences": len(self._preferences),
            "shortcuts": len(self._shortcuts),
            "source": "memory"
        }
    
    async def cleanup_expired(self):
        """Remove expired/unused preferences"""
        async with self._lock:
            now = datetime.now()
            
            # Remove corrections with low confidence that haven't been used
            original_count = len(self._corrections)
            self._corrections = [
                c for c in self._corrections
                if c.confidence > 0.3 or c.use_count > 0
            ]
            removed_corrections = original_count - len(self._corrections)
            
            # Also clean up in database
            if self._db and removed_corrections > 0:
                try:
                    await self._db.execute_raw(
                        "DELETE FROM learned_corrections WHERE confidence <= 0.3 AND use_count = 0"
                    )
                except Exception as e:
                    logging.debug(f"Database cleanup failed: {e}")
            
            # Remove old unused preferences
            expired_keys = []
            for key, pref in self._preferences.items():
                try:
                    updated = datetime.fromisoformat(pref.updated_at)
                    if now - updated > self._preference_expiry and pref.source == "inferred":
                        expired_keys.append(key)
                except (ValueError, TypeError):
                    continue
            
            for key in expired_keys:
                pref = self._preferences[key]
                if self._db and pref.db_id:
                    try:
                        await self._db.delete("user_info", "id = ?", (pref.db_id,))
                    except Exception:
                        pass
                del self._preferences[key]
                logging.info(f"Expired preference: {key}")
            
            if expired_keys or removed_corrections > 0:
                await self._save_preferences()

    async def infer_preference_from_action(
        self,
        tool_name: str,
        action: str,
        args: Dict[str, Any],
        success: bool
    ):
        """Infer preferences from successful actions"""
        if not success:
            return
        
        # Infer shell preference
        if tool_name == "windows" and action == "run_command":
            shell = args.get("shell")
            if shell:
                existing = await self.get_preference("shell", "default")
                if existing is None:
                    await self.set_preference("shell", "default", shell, "inferred")
        
        # Infer browser preference
        if action == "open_app":
            app = args.get("app", "").lower()
            if app in ["chrome", "firefox", "edge", "brave", "opera", "vivaldi"]:
                existing = await self.get_preference("apps", "browser")
                if existing is None:
                    await self.set_preference("apps", "browser", app, "inferred")
            
            if app in ["code", "vscode", "notepad++", "sublime", "atom", "vim", "nvim"]:
                existing = await self.get_preference("apps", "editor")
                if existing is None:
                    await self.set_preference("apps", "editor", app, "inferred")
    
    async def _save_preferences(self):
        """Save preferences to JSON file (backup/transparency)"""
        try:
            data = {
                "last_updated": datetime.now().isoformat(),
                "note": "This is a backup file. Primary storage is in sakura.db" if self._db else "Primary storage",
                "corrections": [
                    {
                        "trigger_phrase": c.trigger_phrase,
                        "intended_tool": c.intended_tool,
                        "intended_action": c.intended_action,
                        "intended_args": c.intended_args,
                        "created_at": c.created_at,
                        "use_count": c.use_count,
                        "last_used": c.last_used,
                        "confidence": c.confidence
                    }
                    for c in self._corrections
                ],
                "preferences": {
                    k: {
                        "category": v.category,
                        "key": v.key,
                        "value": v.value,
                        "created_at": v.created_at,
                        "updated_at": v.updated_at,
                        "source": v.source
                    }
                    for k, v in self._preferences.items()
                },
                "shortcuts": {
                    k: {
                        "phrase": v.phrase,
                        "expansion": v.expansion,
                        "context": v.context,
                        "created_at": v.created_at,
                        "use_count": v.use_count,
                        "tags": v.tags
                    }
                    for k, v in self._shortcuts.items()
                }
            }
            async with aiofiles.open(self.preferences_file, 'w') as f:
                await f.write(json.dumps(data, indent=2))
        except Exception as e:
            logging.error(f"Failed to save preferences: {e}")
    
    async def _load_preferences(self):
        """Load preferences from JSON file"""
        try:
            async with aiofiles.open(self.preferences_file, 'r') as f:
                content = await f.read()
                data = json.loads(content)
            
            for c_data in data.get("corrections", []):
                self._corrections.append(Correction(
                    trigger_phrase=c_data["trigger_phrase"],
                    intended_tool=c_data["intended_tool"],
                    intended_action=c_data["intended_action"],
                    intended_args=c_data.get("intended_args", {}),
                    created_at=c_data.get("created_at", ""),
                    use_count=c_data.get("use_count", 0),
                    last_used=c_data.get("last_used"),
                    confidence=c_data.get("confidence", 1.0)
                ))
            
            for key, p_data in data.get("preferences", {}).items():
                self._preferences[key] = Preference(
                    category=p_data["category"],
                    key=p_data["key"],
                    value=p_data["value"],
                    created_at=p_data.get("created_at", ""),
                    updated_at=p_data.get("updated_at", ""),
                    source=p_data.get("source", "explicit")
                )
            
            for key, s_data in data.get("shortcuts", {}).items():
                self._shortcuts[key] = Shortcut(
                    phrase=s_data["phrase"],
                    expansion=s_data["expansion"],
                    context=s_data.get("context"),
                    created_at=s_data.get("created_at", ""),
                    use_count=s_data.get("use_count", 0),
                    tags=s_data.get("tags", [])
                )
                
        except FileNotFoundError:
            pass
        except Exception as e:
            logging.warning(f"Error loading preferences: {e}")
    
    async def cleanup(self):
        """Save preferences before shutdown"""
        await self.cleanup_expired()
        async with self._lock:
            await self._save_preferences()
            logging.info("User preferences saved")
