"""
Memory Store for Sakura
Persistent memory using SQLite database with JSON export for transparency

Rules followed:
- All imports MUST be used
- Async with asyncio.Lock() for thread safety
- aiofiles for file I/O
- Database as primary storage, JSON for user transparency
"""
import asyncio
import logging
import json
import aiofiles
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from pathlib import Path
from ..base import BaseTool, ToolResult, ToolStatus

# Import database module
try:
    from modules.database import DatabaseManager, get_database, HAS_AIOSQLITE
except ImportError:
    HAS_AIOSQLITE = False
    DatabaseManager = None
    get_database = None


class MemoryStore(BaseTool):
    """Long-term memory storage - SQLite database with JSON export"""
    
    name = "memory"
    description = "Remember and recall information about the user"
    
    def __init__(self, storage_file: Optional[Union[str, Path]] = None, db_path: Optional[Union[str, Path]] = None):
        self.storage_file = Path(storage_file) if storage_file else Path("sakura_memory.json")
        self.db_path = Path(db_path) if db_path else Path("sakura.db")
        self._lock = asyncio.Lock()
        self._db: Optional[DatabaseManager] = None
        self._use_db = HAS_AIOSQLITE
        self._last_export = datetime.now()
        self._export_interval = 300  # Export to JSON every 5 minutes
        
        # Legacy in-memory cache (used when DB unavailable or for quick access)
        self.memories: Dict[str, Any] = {
            "user_info": {},
            "facts": [],
            "preferences": {},
            "important_dates": {},
            "conversation_notes": [],
            "action_log": [],
            "conversation_history": [],
            "scripts_created": [],
            "topics_discussed": {},
            "session_stats": {
                "total_sessions": 0,
                "total_actions": 0,
                "first_session": None,
                "last_session": None
            },
            "discovered_locations": []
        }
    
    async def initialize(self) -> bool:
        """Initialize database and load memories"""
        async with self._lock:
            # Try to initialize database
            if self._use_db and get_database:
                try:
                    self._db = await get_database(self.db_path)
                    
                    # Check if we need to migrate from JSON
                    action_count = await self._db.count("actions")
                    if action_count == 0 and self.storage_file.exists():
                        logging.info("Migrating legacy JSON data to database...")
                        await self._db.import_from_legacy_json(str(self.storage_file))
                    
                    logging.info(f"Memory store initialized with database: {self.db_path}")
                    
                    # Load into memory cache for quick access
                    await self._load_to_cache()
                    return True
                except Exception as e:
                    logging.warning(f"Database init failed, falling back to JSON: {e}")
                    self._use_db = False
                    self._db = None
            
            # Fallback to JSON-only mode
            try:
                async with aiofiles.open(str(self.storage_file), 'r') as f:
                    content = await f.read()
                    self.memories = json.loads(content)
                logging.info(f"Loaded {len(self.memories.get('facts', []))} memories from JSON")
                return True
            except FileNotFoundError:
                logging.info("No existing memories, starting fresh")
                return True
            except Exception as e:
                logging.error(f"Error loading memories: {e}")
                return True
    
    async def _load_to_cache(self):
        """Load database data into memory cache for quick access"""
        if not self._db:
            return
        
        try:
            # Load user_info
            user_info_rows = await self._db.select("user_info")
            self.memories["user_info"] = {row["key"]: row["value"] for row in user_info_rows}
            
            # Load facts
            facts_rows = await self._db.select("facts", order_by="created_at DESC", limit=100)
            self.memories["facts"] = [{"content": r["content"], "category": r["category"], "timestamp": r["created_at"]} for r in facts_rows]
            
            # Load important_dates
            dates_rows = await self._db.select("important_dates")
            self.memories["important_dates"] = {row["name"]: row["date_value"] for row in dates_rows}
            
            # Load recent actions
            actions_rows = await self._db.select("actions", order_by="created_at DESC", limit=100)
            self.memories["action_log"] = [
                {"key": f"action_{r['id']}", "value": f"[{r['created_at']}] {r['tool_name']}.{r['action_name']} -> {r['status']}", "timestamp": r["created_at"]}
                for r in actions_rows
            ]
            
            # Load conversations
            convos_rows = await self._db.select("conversations", order_by="created_at DESC", limit=50)
            self.memories["conversation_history"] = [
                {"summary": r["summary"], "topics": r["topics"], "mood": r["mood"], "timestamp": r["created_at"]}
                for r in convos_rows
            ]
            
            # Load scripts
            scripts_rows = await self._db.select("scripts", order_by="created_at DESC")
            self.memories["scripts_created"] = [
                {"name": r["name"], "path": r["path"], "type": r["script_type"], "description": r["description"], "timestamp": r["created_at"]}
                for r in scripts_rows
            ]
            
            # Load topics
            topics_rows = await self._db.select("topics")
            self.memories["topics_discussed"] = {
                r["name"]: {"topic": r["name"], "count": r["mention_count"], "first_discussed": r["first_mentioned"], "last_discussed": r["last_mentioned"]}
                for r in topics_rows
            }
            
            # Load discovered_locations
            locations_rows = await self._db.select("discovered_locations", order_by="created_at DESC", limit=100)
            self.memories["discovered_locations"] = [
                {"key": f"{r['location_type']}_{r['name']}", "value": f"{r['location_type']} for {r['name']}: {r['path']}", "timestamp": r["created_at"]}
                for r in locations_rows
            ]
            
        except Exception as e:
            logging.error(f"Error loading cache from database: {e}")
    
    async def execute(self, action: str, **kwargs) -> ToolResult:
        """Execute memory action"""
        actions = {
            # Core memory actions
            "remember": self._remember,
            "recall": self._recall,
            "forget": self._forget,
            "set_user_info": self._set_user_info,
            "get_user_info": self._get_user_info,
            "set_date": self._set_date,
            "get_dates": self._get_dates,
            "store": self._store,
            "get_action_log": self._get_action_log,
            "log_conversation": self._log_conversation,
            "get_conversations": self._get_conversations,
            "log_script": self._log_script,
            "get_scripts": self._get_scripts,
            "log_topic": self._log_topic,
            "get_stats": self._get_stats,
            "search_all": self._search_all,
            # Database-powered search actions
            "search_by_subject": self._search_by_subject,
            "get_timeline": self._get_timeline,
            "get_related": self._get_related,
            # Fast full-text search
            "search_fts": self._search_fts,
            # User feedback & learning actions (infinite history)
            "log_feedback": self._log_feedback,
            "get_corrections": self._get_corrections,
            "get_full_history": self._get_full_history,
            "get_error_solutions": self._get_error_solutions,
            "get_history_stats": self._get_history_stats,
            # Conversation exchange logging (for infinite history)
            "log_exchange": self._log_exchange,
            # Database maintenance
            "prune_old_data": self._prune_old_data,
            "get_db_stats": self._get_db_stats,
        }
        
        if action not in actions:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Unknown action: {action}. Available: {list(actions.keys())}"
            )
        
        result = await actions[action](**kwargs)
        
        # Periodic JSON export for transparency
        await self._maybe_export_json()
        
        return result
    
    async def _maybe_export_json(self):
        """Export to JSON periodically for user transparency"""
        now = datetime.now()
        if (now - self._last_export).total_seconds() > self._export_interval:
            await self._export_to_json()
            self._last_export = now
    
    async def _export_to_json(self):
        """Export current state to JSON file"""
        try:
            async with aiofiles.open(str(self.storage_file), 'w') as f:
                await f.write(json.dumps(self.memories, indent=2, default=str))
        except Exception as e:
            logging.error(f"Error exporting to JSON: {e}")
    
    # ==================== Core Memory Actions ====================
    
    async def _remember(self, fact: str, category: str = "facts") -> ToolResult:
        """Remember a new fact"""
        async with self._lock:
            timestamp = datetime.now().isoformat()
            
            if self._db:
                # Store in database
                await self._db.insert("facts", {
                    "content": fact,
                    "category": category,
                    "source": "user_stated",
                    "created_at": timestamp
                })
            
            # Update cache
            memory = {"content": fact, "timestamp": timestamp, "category": category}
            if category == "facts":
                self.memories["facts"].append(memory)
            elif category == "preference":
                self.memories["preferences"][fact] = memory
            elif category == "note":
                self.memories["conversation_notes"].append(memory)
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            message=f"I'll remember that: {fact}"
        )
    
    async def _recall(self, query: str = "", category: str = "all") -> ToolResult:
        """Recall memories"""
        results: List[str] = []
        
        if self._db and query:
            # Use database search for better performance
            search_results = await self._db.search_text(
                ["facts", "user_info", "important_dates"],
                query,
                {
                    "facts": ["content"],
                    "user_info": ["key", "value"],
                    "important_dates": ["name", "date_value"]
                }
            )
            
            for table, rows in search_results.items():
                for row in rows:
                    if table == "facts":
                        results.append(row["content"])
                    elif table == "user_info":
                        results.append(f"{row['key']}: {row['value']}")
                    elif table == "important_dates":
                        results.append(f"{row['name']}: {row['date_value']}")
        else:
            # Use cache
            async with self._lock:
                if category in ["all", "facts"]:
                    for fact in self.memories.get("facts", []):
                        if not query or query.lower() in fact["content"].lower():
                            results.append(fact["content"])
                
                if category in ["all", "user_info"]:
                    for key, value in self.memories.get("user_info", {}).items():
                        if not query or query.lower() in key.lower():
                            results.append(f"{key}: {value}")
                
                if category in ["all", "important_dates"]:
                    for key, value in self.memories.get("important_dates", {}).items():
                        if not query or query.lower() in key.lower():
                            results.append(f"{key}: {value}")
                
                if category in ["all", "preferences"]:
                    for key, value in self.memories.get("preferences", {}).items():
                        if not query or query.lower() in key.lower():
                            results.append(f"Preference: {key}")
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=results,
            message=f"Found {len(results)} memories"
        )
    
    async def _forget(self, fact: str) -> ToolResult:
        """Forget a specific fact"""
        removed = 0
        
        if self._db:
            # Delete from database
            await self._db.delete("facts", "content LIKE ?", (f"%{fact}%",))
        
        async with self._lock:
            original_count = len(self.memories["facts"])
            self.memories["facts"] = [
                f for f in self.memories["facts"] 
                if fact.lower() not in f["content"].lower()
            ]
            removed = original_count - len(self.memories["facts"])
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            message=f"Forgotten {removed} memories"
        )
    
    async def _set_user_info(self, key: str, value: str) -> ToolResult:
        """Set user information"""
        async with self._lock:
            if self._db:
                # Upsert in database
                existing = await self._db.select_one("user_info", "*", "key = ?", (key,))
                if existing:
                    await self._db.update("user_info", {"value": value, "updated_at": datetime.now().isoformat()}, "key = ?", (key,))
                else:
                    await self._db.insert("user_info", {"key": key, "value": value})
            
            self.memories["user_info"][key] = value
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            message=f"Got it, your {key} is {value}"
        )
    
    async def _get_user_info(self, key: str = "") -> ToolResult:
        """Get user information"""
        if key:
            if self._db:
                row = await self._db.select_one("user_info", "*", "key = ?", (key,))
                value = row["value"] if row else None
            else:
                value = self.memories["user_info"].get(key)
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=value,
                message=f"Your {key} is {value}" if value else f"I don't know your {key}"
            )
        
        if self._db:
            rows = await self._db.select("user_info")
            data = {row["key"]: row["value"] for row in rows}
        else:
            data = self.memories["user_info"].copy()
        
        return ToolResult(status=ToolStatus.SUCCESS, data=data)
    
    async def _set_date(self, name: str, date: str) -> ToolResult:
        """Set an important date"""
        async with self._lock:
            if self._db:
                existing = await self._db.select_one("important_dates", "*", "name = ?", (name,))
                if existing:
                    await self._db.update("important_dates", {"date_value": date}, "name = ?", (name,))
                else:
                    await self._db.insert("important_dates", {"name": name, "date_value": date})
            
            self.memories["important_dates"][name] = date
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            message=f"I'll remember {name}: {date}"
        )
    
    async def _get_dates(self) -> ToolResult:
        """Get all important dates"""
        if self._db:
            rows = await self._db.select("important_dates")
            dates = {row["name"]: row["date_value"] for row in rows}
        else:
            dates = self.memories.get("important_dates", {}).copy()
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=dates,
            message=f"Found {len(dates)} important dates"
        )
    
    async def _store(self, category: str, key: str, value: str) -> ToolResult:
        """Store any data by category and key"""
        timestamp = datetime.now().isoformat()
        
        if self._db:
            if category == "action_log":
                # Parse action string and store properly
                tool_name = "unknown"
                action_name = "unknown"
                status = "unknown"
                
                if "] " in value and " -> " in value:
                    parts = value.split("] ", 1)
                    if len(parts) == 2:
                        action_part = parts[1]
                        if " -> " in action_part:
                            tool_action, status = action_part.rsplit(" -> ", 1)
                            if "." in tool_action:
                                tool_name, action_name = tool_action.split(".", 1)
                                if " (" in action_name:
                                    action_name = action_name.split(" (")[0]
                
                await self._db.insert("actions", {
                    "tool_name": tool_name.strip(),
                    "action_name": action_name.strip(),
                    "status": status.strip(),
                    "created_at": timestamp
                })
            elif category == "discovered_locations":
                # Parse location and store
                loc_type = "app_path" if "app_path" in key.lower() else "file_path"
                name = key.replace("app_path_", "").replace("app_", "")
                path = value.split(": ")[-1] if ": " in value else value
                await self._db.upsert_location(loc_type, name, path)
        
        # Update cache
        async with self._lock:
            if category not in self.memories:
                self.memories[category] = []
            
            entry = {"key": key, "value": value, "timestamp": timestamp}
            
            if category == "action_log":
                self.memories[category].append(entry)
                if len(self.memories[category]) > 100:
                    self.memories[category] = self.memories[category][-100:]
            else:
                if isinstance(self.memories[category], list):
                    self.memories[category].append(entry)
                else:
                    self.memories[category][key] = entry
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            message=f"Stored {key} in {category}"
        )
    
    async def _get_action_log(self, count: int = 20, query: str = "") -> ToolResult:
        """Get recent action history"""
        if self._db:
            if query:
                rows = await self._db.execute_raw(
                    "SELECT * FROM actions WHERE tool_name LIKE ? OR action_name LIKE ? ORDER BY created_at DESC LIMIT ?",
                    (f"%{query}%", f"%{query}%", count)
                )
            else:
                rows = await self._db.get_recent_actions(count)
            
            formatted = [f"[{r['created_at']}] {r['tool_name']}.{r['action_name']} -> {r['status']}" for r in rows]
        else:
            async with self._lock:
                logs = self.memories.get("action_log", [])
                if query:
                    logs = [log for log in logs if query.lower() in log.get("value", "").lower()]
                recent = logs[-count:] if len(logs) > count else logs
                recent.reverse()
                formatted = [entry.get("value", str(entry)) for entry in recent]
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=formatted,
            message=f"Found {len(formatted)} actions in history"
        )

    async def _log_conversation(self, summary: str, topics: str = "", mood: str = "") -> ToolResult:
        """Log a conversation summary"""
        timestamp = datetime.now().isoformat()
        
        if self._db:
            await self._db.insert("conversations", {
                "summary": summary,
                "topics": topics,
                "mood": mood,
                "created_at": timestamp
            })
        
        async with self._lock:
            if "conversation_history" not in self.memories:
                self.memories["conversation_history"] = []
            
            entry = {"summary": summary, "topics": topics, "mood": mood, "timestamp": timestamp}
            self.memories["conversation_history"].append(entry)
            
            if len(self.memories["conversation_history"]) > 50:
                self.memories["conversation_history"] = self.memories["conversation_history"][-50:]
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            message=f"Logged conversation: {summary[:50]}..."
        )
    
    async def _get_conversations(self, count: int = 10, query: str = "") -> ToolResult:
        """Get recent conversation history"""
        if self._db:
            if query:
                rows = await self._db.execute_raw(
                    "SELECT * FROM conversations WHERE summary LIKE ? OR topics LIKE ? ORDER BY created_at DESC LIMIT ?",
                    (f"%{query}%", f"%{query}%", count)
                )
            else:
                rows = await self._db.select("conversations", order_by="created_at DESC", limit=count)
            
            recent = [{"summary": r["summary"], "topics": r["topics"], "mood": r["mood"], "timestamp": r["created_at"]} for r in rows]
        else:
            async with self._lock:
                convos = self.memories.get("conversation_history", [])
                if query:
                    convos = [c for c in convos if query.lower() in c.get("summary", "").lower() or query.lower() in c.get("topics", "").lower()]
                recent = convos[-count:] if len(convos) > count else convos
                recent = list(reversed(recent))
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=recent,
            message=f"Found {len(recent)} conversations"
        )
    
    async def _log_script(self, script_name: str, script_path: str, script_type: str, description: str = "") -> ToolResult:
        """Log a script that was created"""
        timestamp = datetime.now().isoformat()
        
        if self._db:
            await self._db.insert("scripts", {
                "name": script_name,
                "path": script_path,
                "script_type": script_type,
                "description": description,
                "created_at": timestamp
            })
        
        async with self._lock:
            if "scripts_created" not in self.memories:
                self.memories["scripts_created"] = []
            
            entry = {"name": script_name, "path": script_path, "type": script_type, "description": description, "timestamp": timestamp}
            self.memories["scripts_created"].append(entry)
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            message=f"Logged script: {script_name}"
        )
    
    async def _get_scripts(self, script_type: str = "", query: str = "") -> ToolResult:
        """Get scripts that were created"""
        if self._db:
            if script_type and query:
                rows = await self._db.execute_raw(
                    "SELECT * FROM scripts WHERE script_type = ? AND (name LIKE ? OR description LIKE ?) ORDER BY created_at DESC",
                    (script_type, f"%{query}%", f"%{query}%")
                )
            elif script_type:
                rows = await self._db.select("scripts", where="script_type = ?", where_params=(script_type,), order_by="created_at DESC")
            elif query:
                rows = await self._db.execute_raw(
                    "SELECT * FROM scripts WHERE name LIKE ? OR description LIKE ? ORDER BY created_at DESC",
                    (f"%{query}%", f"%{query}%")
                )
            else:
                rows = await self._db.select("scripts", order_by="created_at DESC")
            
            scripts = [{"name": r["name"], "path": r["path"], "type": r["script_type"], "description": r["description"]} for r in rows]
        else:
            async with self._lock:
                scripts = self.memories.get("scripts_created", [])
                if script_type:
                    scripts = [s for s in scripts if s.get("type", "").lower() == script_type.lower()]
                if query:
                    scripts = [s for s in scripts if query.lower() in s.get("name", "").lower() or query.lower() in s.get("description", "").lower()]
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=scripts,
            message=f"Found {len(scripts)} scripts"
        )
    
    async def _log_topic(self, topic: str) -> ToolResult:
        """Log a topic that was discussed"""
        if self._db:
            await self._db.upsert_topic(topic)
        
        async with self._lock:
            if "topics_discussed" not in self.memories:
                self.memories["topics_discussed"] = {}
            
            topic_lower = topic.lower()
            if topic_lower in self.memories["topics_discussed"]:
                self.memories["topics_discussed"][topic_lower]["count"] += 1
                self.memories["topics_discussed"][topic_lower]["last_discussed"] = datetime.now().isoformat()
            else:
                self.memories["topics_discussed"][topic_lower] = {
                    "topic": topic,
                    "count": 1,
                    "first_discussed": datetime.now().isoformat(),
                    "last_discussed": datetime.now().isoformat()
                }
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            message=f"Logged topic: {topic}"
        )
    
    async def _get_stats(self) -> ToolResult:
        """Get memory and session statistics"""
        if self._db:
            stats = {
                "total_facts": await self._db.count("facts"),
                "total_user_info": await self._db.count("user_info"),
                "total_dates": await self._db.count("important_dates"),
                "total_conversations": await self._db.count("conversations"),
                "total_actions_logged": await self._db.count("actions"),
                "total_scripts": await self._db.count("scripts"),
                "total_topics": await self._db.count("topics"),
                "total_locations": await self._db.count("discovered_locations"),
                "database_enabled": True
            }
        else:
            async with self._lock:
                stats = {
                    "session_stats": self.memories.get("session_stats", {}),
                    "total_facts": len(self.memories.get("facts", [])),
                    "total_user_info": len(self.memories.get("user_info", {})),
                    "total_preferences": len(self.memories.get("preferences", {})),
                    "total_dates": len(self.memories.get("important_dates", {})),
                    "total_conversations": len(self.memories.get("conversation_history", [])),
                    "total_actions_logged": len(self.memories.get("action_log", [])),
                    "total_scripts": len(self.memories.get("scripts_created", [])),
                    "total_topics": len(self.memories.get("topics_discussed", {})),
                    "database_enabled": False
                }
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=stats,
            message=f"Memory stats: {stats.get('total_facts', 0)} facts, {stats.get('total_conversations', 0)} conversations"
        )
    
    async def _search_all(self, query: str) -> ToolResult:
        """Search across all memory categories"""
        results = {
            "facts": [],
            "user_info": [],
            "conversations": [],
            "scripts": [],
            "actions": [],
            "topics": [],
            "locations": []
        }
        
        if self._db:
            # Use database full-text search
            db_results = await self._db.search_text(
                ["facts", "user_info", "conversations", "scripts", "actions", "topics", "discovered_locations"],
                query,
                {
                    "facts": ["content"],
                    "user_info": ["key", "value"],
                    "conversations": ["summary", "topics"],
                    "scripts": ["name", "description"],
                    "actions": ["tool_name", "action_name"],
                    "topics": ["name"],
                    "discovered_locations": ["name", "path"]
                }
            )
            
            for table, rows in db_results.items():
                if table == "facts":
                    results["facts"] = [r["content"] for r in rows]
                elif table == "user_info":
                    results["user_info"] = [f"{r['key']}: {r['value']}" for r in rows]
                elif table == "conversations":
                    results["conversations"] = [r["summary"] for r in rows]
                elif table == "scripts":
                    results["scripts"] = [f"{r['name']} ({r['script_type']})" for r in rows]
                elif table == "actions":
                    results["actions"] = [f"{r['tool_name']}.{r['action_name']}" for r in rows]
                elif table == "topics":
                    results["topics"] = [r["name"] for r in rows]
                elif table == "discovered_locations":
                    results["locations"] = [f"{r['name']}: {r['path']}" for r in rows]
        else:
            # Use cache search
            query_lower = query.lower()
            async with self._lock:
                for fact in self.memories.get("facts", []):
                    if query_lower in fact.get("content", "").lower():
                        results["facts"].append(fact["content"])
                
                for key, value in self.memories.get("user_info", {}).items():
                    if query_lower in key.lower() or query_lower in str(value).lower():
                        results["user_info"].append(f"{key}: {value}")
                
                for conv in self.memories.get("conversation_history", []):
                    if query_lower in conv.get("summary", "").lower():
                        results["conversations"].append(conv["summary"])
                
                for script in self.memories.get("scripts_created", []):
                    if query_lower in script.get("name", "").lower() or query_lower in script.get("description", "").lower():
                        results["scripts"].append(f"{script['name']} ({script.get('type', 'unknown')})")
                
                for action in self.memories.get("action_log", [])[-50:]:
                    if query_lower in action.get("value", "").lower():
                        results["actions"].append(action["value"])
                
                for topic_key, topic_data in self.memories.get("topics_discussed", {}).items():
                    if query_lower in topic_key:
                        results["topics"].append(f"{topic_data['topic']} (discussed {topic_data['count']} times)")
                
                for loc in self.memories.get("discovered_locations", []):
                    if query_lower in loc.get("value", "").lower():
                        results["locations"].append(loc["value"])
        
        total = sum(len(v) for v in results.values())
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=results,
            message=f"Found {total} matches for '{query}'"
        )

    # ==================== New Database-Powered Actions ====================
    
    async def _search_by_subject(self, subject: str, limit: int = 20) -> ToolResult:
        """Search all memories related to a subject/topic"""
        if not self._db:
            # Fallback to search_all
            return await self._search_all(subject)
        
        results = {
            "events": [],
            "tasks": [],
            "actions": [],
            "facts": [],
            "locations": []
        }
        
        # Find or create subject
        subject_row = await self._db.select_one("subjects", "*", "name LIKE ?", (f"%{subject}%",))
        
        if subject_row:
            # Get events for this subject
            events = await self._db.get_subject_timeline(subject_row["id"], limit)
            results["events"] = [{"title": e["title"], "type": e["event_type"], "timestamp": e["created_at"]} for e in events]
            
            # Get tasks related to events
            for event in events[:5]:
                tasks = await self._db.select("tasks", where="event_id = ?", where_params=(event["id"],))
                results["tasks"].extend([{"title": t["title"], "status": t["status"]} for t in tasks])
        
        # Also search by text
        text_results = await self._db.search_text(
            ["facts", "discovered_locations", "actions"],
            subject,
            {
                "facts": ["content"],
                "discovered_locations": ["name", "path"],
                "actions": ["tool_name", "action_name"]
            }
        )
        
        results["facts"] = [r["content"] for r in text_results.get("facts", [])]
        results["locations"] = [f"{r['name']}: {r['path']}" for r in text_results.get("discovered_locations", [])]
        results["actions"] = [f"{r['tool_name']}.{r['action_name']}" for r in text_results.get("actions", [])[:10]]
        
        total = sum(len(v) for v in results.values())
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=results,
            message=f"Found {total} items related to '{subject}'"
        )
    
    async def _search_fts(self, query: str, source: str = "", limit: int = 50) -> ToolResult:
        """Fast full-text search using FTS5 index"""
        if not self._db:
            # Fallback to search_all
            return await self._search_all(query)
        
        try:
            results = await self._db.search_fts(
                query=query,
                limit=limit,
                source_filter=source if source else None
            )
            
            # Group by source
            grouped = {}
            for r in results:
                src = r.get("source", "unknown")
                if src not in grouped:
                    grouped[src] = []
                grouped[src].append({
                    "content": r.get("content", "")[:200],
                    "id": r.get("source_id"),
                    "rank": r.get("rank", 0)
                })
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=grouped,
                message=f"FTS found {len(results)} matches for '{query}'"
            )
        except Exception as e:
            # Fallback to regular search
            logging.warning(f"FTS search failed, falling back: {e}")
            return await self._search_all(query)
    
    async def _get_timeline(self, days: int = 7, event_type: str = "") -> ToolResult:
        """Get chronological timeline of activities"""
        if not self._db:
            # Fallback to action log
            return await self._get_action_log(count=50)
        
        from_date = (datetime.now() - __import__('datetime').timedelta(days=days)).isoformat()
        
        timeline = []
        
        # Get actions
        if not event_type or event_type == "actions":
            actions = await self._db.execute_raw(
                "SELECT * FROM actions WHERE created_at >= ? ORDER BY created_at DESC LIMIT 50",
                (from_date,)
            )
            for a in actions:
                timeline.append({
                    "type": "action",
                    "title": f"{a['tool_name']}.{a['action_name']}",
                    "status": a["status"],
                    "timestamp": a["created_at"]
                })
        
        # Get conversations
        if not event_type or event_type == "conversations":
            convos = await self._db.execute_raw(
                "SELECT * FROM conversations WHERE created_at >= ? ORDER BY created_at DESC LIMIT 20",
                (from_date,)
            )
            for c in convos:
                timeline.append({
                    "type": "conversation",
                    "title": c["summary"][:100] if c["summary"] else "Conversation",
                    "topics": c["topics"],
                    "timestamp": c["created_at"]
                })
        
        # Get scripts created
        if not event_type or event_type == "scripts":
            scripts = await self._db.execute_raw(
                "SELECT * FROM scripts WHERE created_at >= ? ORDER BY created_at DESC",
                (from_date,)
            )
            for s in scripts:
                timeline.append({
                    "type": "script",
                    "title": f"Created {s['name']}",
                    "path": s["path"],
                    "timestamp": s["created_at"]
                })
        
        # Sort by timestamp
        timeline.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=timeline[:50],
            message=f"Timeline: {len(timeline)} events in last {days} days"
        )
    
    async def _get_related(self, item_type: str, item_id: int) -> ToolResult:
        """Get related items (e.g., task with subtasks and actions)"""
        if not self._db:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Database required for related items query"
            )
        
        results = {}
        
        if item_type == "task":
            # Get task tree with subtasks and actions
            task_tree = await self._db.get_task_tree(item_id)
            results = task_tree
        elif item_type == "event":
            # Get event with all tasks
            event = await self._db.select_one("events", "*", "id = ?", (item_id,))
            if event:
                results["event"] = dict(event)
                results["tasks"] = await self._db.select("tasks", where="event_id = ?", where_params=(item_id,))
        elif item_type == "subject":
            # Get subject with timeline
            subject = await self._db.select_one("subjects", "*", "id = ?", (item_id,))
            if subject:
                results["subject"] = dict(subject)
                results["events"] = await self._db.get_subject_timeline(item_id, 20)
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=results,
            message=f"Found related items for {item_type} #{item_id}"
        )
    
    # ==================== User Feedback & Learning Actions ====================
    
    async def _log_feedback(
        self, 
        feedback_type: str, 
        message: str, 
        original: str = "", 
        correct: str = "",
        action_id: int = None
    ) -> ToolResult:
        """Log user feedback about Sakura's actions"""
        if not self._db:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Database required for feedback logging"
            )
        
        feedback_id = await self._db.log_user_feedback(
            feedback_type=feedback_type,
            user_message=message,
            original_action=original,
            correct_action=correct,
            action_id=action_id
        )
        
        # If it's a correction, also create a learned correction
        if feedback_type == "correction" and correct:
            # Extract keywords from the message for trigger pattern
            trigger = message.lower()[:100]  # First 100 chars as trigger
            await self._db.add_learned_correction(
                trigger_pattern=trigger,
                correct_behavior=correct,
                wrong_behavior=original
            )
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"feedback_id": feedback_id},
            message=f"Logged {feedback_type} feedback - I'll remember this!"
        )
    
    async def _get_corrections(self, context: str = "", tool: str = "") -> ToolResult:
        """Get relevant corrections for current context"""
        if not self._db:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Database required for corrections"
            )
        
        corrections = await self._db.get_relevant_corrections(context, tool)
        
        formatted = []
        for c in corrections:
            formatted.append({
                "trigger": c["trigger_pattern"],
                "wrong": c["wrong_behavior"],
                "correct": c["correct_behavior"],
                "confidence": c["confidence"],
                "tool": c["tool_name"]
            })
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=formatted,
            message=f"Found {len(formatted)} relevant corrections"
        )
    
    async def _get_full_history(self, limit: int = 100, search: str = "") -> ToolResult:
        """Get full conversation history (infinite)"""
        if not self._db:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Database required for full history"
            )
        
        history = await self._db.get_conversation_history(
            limit=limit,
            search_query=search if search else None
        )
        
        formatted = []
        for h in history:
            formatted.append({
                "user": h["user_input"][:200] if h["user_input"] else "",
                "ai": h["ai_response"][:200] if h["ai_response"] else "",
                "tools": json.loads(h["tools_used"]) if h["tools_used"] else [],
                "mood": h["mood"],
                "timestamp": h["created_at"]
            })
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=formatted,
            message=f"Retrieved {len(formatted)} exchanges from history"
        )
    
    async def _get_error_solutions(self, tool: str, action: str, error_type: str = "") -> ToolResult:
        """Get known solutions for errors"""
        if not self._db:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Database required for error solutions"
            )
        
        solutions = await self._db.get_error_solutions(tool, action, error_type if error_type else None)
        
        formatted = []
        for s in solutions:
            formatted.append({
                "error_type": s["error_type"],
                "error_message": s["error_message"],
                "solution": s["solution"],
                "occurrences": s["occurrence_count"]
            })
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=formatted,
            message=f"Found {len(formatted)} known solutions"
        )
    
    async def _get_history_stats(self) -> ToolResult:
        """Get statistics about stored history"""
        if not self._db:
            return await self._get_stats()
        
        stats = await self._db.get_history_stats()
        
        # Add memory stats
        memory_stats = await self._get_stats()
        if memory_stats.data:
            stats.update(memory_stats.data)
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=stats,
            message=f"History: {stats.get('total_exchanges', 0)} exchanges, {stats.get('total_corrections', 0)} corrections learned"
        )
    
    async def _log_exchange(
        self,
        session_id: str,
        user_input: str,
        ai_response: str,
        tools_used: str = "",
        tool_results: str = "",
        mood: str = "",
        topics: str = ""
    ) -> ToolResult:
        """Log a conversation exchange for infinite history"""
        if not self._db:
            # Fallback to log_conversation
            return await self._log_conversation(
                summary=f"User: {user_input[:100]}... AI: {ai_response[:100]}...",
                topics=topics,
                mood=mood
            )
        
        # Parse tools_used and tool_results if they're strings
        tools_list = []
        results_list = []
        
        if tools_used:
            try:
                tools_list = json.loads(tools_used) if tools_used.startswith("[") else [t.strip() for t in tools_used.split(",")]
            except json.JSONDecodeError:
                tools_list = [tools_used]
        
        if tool_results:
            try:
                results_list = json.loads(tool_results) if tool_results.startswith("[") else [{"result": tool_results}]
            except json.JSONDecodeError:
                results_list = [{"result": tool_results}]
        
        topics_list = [t.strip() for t in topics.split(",")] if topics else []
        
        exchange_id = await self._db.log_conversation_exchange(
            session_id=session_id,
            user_input=user_input,
            ai_response=ai_response,
            tools_used=tools_list if tools_list else None,
            tool_results=results_list if results_list else None,
            mood=mood if mood else None,
            topics=topics_list if topics_list else None
        )
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"exchange_id": exchange_id},
            message=f"Logged exchange #{exchange_id}"
        )
    
    async def _prune_old_data(
        self,
        exchange_days: int = 90,
        action_days: int = 30,
        error_days: int = 60
    ) -> ToolResult:
        """Prune old data to keep database size manageable"""
        if not self._db:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Database required for pruning"
            )
        
        try:
            result = await self._db.prune_old_data(
                exchange_days=exchange_days,
                action_days=action_days,
                error_days=error_days,
                keep_high_value=True
            )
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=result,
                message=f"Pruned old data (keeping {exchange_days}d exchanges, {action_days}d actions, {error_days}d errors)"
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Prune failed: {e}"
            )
    
    async def _get_db_stats(self) -> ToolResult:
        """Get database size and table statistics"""
        if not self._db:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Database required for stats"
            )
        
        try:
            stats = await self._db.get_database_stats()
            
            # Format nicely
            total_rows = sum(v for k, v in stats.items() if k != "file_size_mb")
            size_mb = stats.get("file_size_mb", 0)
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=stats,
                message=f"Database: {total_rows} total rows, {size_mb:.2f} MB"
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Stats failed: {e}"
            )
    
    # ==================== Schema & Cleanup ====================
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Full memory system with database: facts, conversations, actions, scripts, topics, search, timeline, feedback, corrections, infinite history, and maintenance",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            # Core memory actions
                            "remember", "recall", "forget", 
                            "set_user_info", "get_user_info", 
                            "set_date", "get_dates",
                            "store", "get_action_log",
                            "log_conversation", "get_conversations",
                            "log_script", "get_scripts",
                            "log_topic", "get_stats", "search_all",
                            # Database-powered search
                            "search_by_subject", "get_timeline", "get_related",
                            # Fast full-text search
                            "search_fts",
                            # User feedback & learning (infinite history)
                            "log_feedback", "get_corrections", "get_full_history",
                            "get_error_solutions", "get_history_stats", "log_exchange",
                            # Database maintenance
                            "prune_old_data", "get_db_stats"
                        ],
                        "description": "Memory action to perform"
                    },
                    # Core memory params
                    "fact": {"type": "string", "description": "Fact to remember/forget"},
                    "query": {"type": "string", "description": "Search query (also used for search_fts)"},
                    "category": {"type": "string", "description": "Memory category"},
                    "key": {"type": "string", "description": "Key for storing data"},
                    "value": {"type": "string", "description": "Value to store"},
                    "name": {"type": "string", "description": "Name (date or script)"},
                    "date": {"type": "string", "description": "Date value"},
                    "source": {"type": "string", "description": "Filter FTS by source type (fact, user_info, conversation, script, location, exchange)"},
                    "count": {"type": "integer", "description": "Number of entries to retrieve", "default": 20},
                    "summary": {"type": "string", "description": "Conversation summary"},
                    "topics": {"type": "string", "description": "Topics discussed (comma-separated)"},
                    "mood": {"type": "string", "description": "Conversation mood"},
                    "script_name": {"type": "string", "description": "Name of script"},
                    "script_path": {"type": "string", "description": "Path to script"},
                    "script_type": {"type": "string", "description": "Type of script (python, powershell, etc.)"},
                    "description": {"type": "string", "description": "Description of script"},
                    "topic": {"type": "string", "description": "Topic to log"},
                    # Database search params
                    "subject": {"type": "string", "description": "Subject to search for (search_by_subject)"},
                    "days": {"type": "integer", "description": "Number of days for timeline", "default": 7},
                    "event_type": {"type": "string", "description": "Filter timeline by event type (actions, conversations, scripts)"},
                    "item_type": {"type": "string", "enum": ["task", "event", "subject"], "description": "Type of item for get_related"},
                    "item_id": {"type": "integer", "description": "ID of item for get_related"},
                    "limit": {"type": "integer", "description": "Maximum results to return", "default": 20},
                    # User feedback & learning params
                    "feedback_type": {"type": "string", "enum": ["correction", "positive", "negative", "preference"], "description": "Type of feedback (log_feedback)"},
                    "message": {"type": "string", "description": "User's feedback message (log_feedback)"},
                    "original": {"type": "string", "description": "What Sakura did wrong (log_feedback)"},
                    "correct": {"type": "string", "description": "What user wanted instead (log_feedback)"},
                    "action_id": {"type": "integer", "description": "ID of action being corrected (log_feedback)"},
                    "context": {"type": "string", "description": "Context for getting corrections (get_corrections)"},
                    "tool": {"type": "string", "description": "Tool name for filtering (get_corrections, get_error_solutions)"},
                    "search": {"type": "string", "description": "Search query for history (get_full_history)"},
                    "error_type": {"type": "string", "description": "Type of error (get_error_solutions)"},
                    # Conversation exchange params (infinite history)
                    "session_id": {"type": "string", "description": "Session ID for exchange logging (log_exchange)"},
                    "user_input": {"type": "string", "description": "User's input text (log_exchange)"},
                    "ai_response": {"type": "string", "description": "AI's response text (log_exchange)"},
                    "tools_used": {"type": "string", "description": "Tools used (comma-separated or JSON array) (log_exchange)"},
                    "tool_results": {"type": "string", "description": "Tool results (JSON array) (log_exchange)"},
                    # Database maintenance params
                    "exchange_days": {"type": "integer", "description": "Days to keep exchanges (prune_old_data)", "default": 90},
                    "action_days": {"type": "integer", "description": "Days to keep actions (prune_old_data)", "default": 30},
                    "error_days": {"type": "integer", "description": "Days to keep errors (prune_old_data)", "default": 60}
                },
                "required": ["action"]
            }
        }
    
    async def cleanup(self):
        """Save and cleanup"""
        # Final JSON export
        await self._export_to_json()
        
        # Database cleanup handled by database module
        if self._db:
            logging.info("Memory store cleanup complete (database mode)")
        else:
            logging.info("Memory store cleanup complete (JSON mode)")
