"""
Memory Store for Sakura
Persistent memory for user preferences, facts, and conversation history - fully async
"""
import asyncio
import logging
import json
import aiofiles
from typing import Dict, Any, Optional, List
from datetime import datetime
from ..base import BaseTool, ToolResult, ToolStatus

class MemoryStore(BaseTool):
    """Long-term memory storage - async with file locking"""
    
    name = "memory"
    description = "Remember and recall information about the user"
    
    def __init__(self, storage_file: Optional[str] = None):
        self.storage_file = storage_file or "sakura_memory.json"
        self._lock = asyncio.Lock()
        self.memories: Dict[str, Any] = {
            "user_info": {},          # Name, preferences, etc.
            "facts": [],              # Things user has told Sakura
            "preferences": {},        # User likes/dislikes
            "important_dates": {},    # Birthdays, anniversaries
            "conversation_notes": [], # Notable conversation moments
            "action_log": [],         # History of actions performed
            "conversation_history": [],# Conversation summaries
            "scripts_created": [],    # Scripts Sakura has created
            "topics_discussed": {},   # Topics and frequency
            "session_stats": {        # Session statistics
                "total_sessions": 0,
                "total_actions": 0,
                "first_session": None,
                "last_session": None
            }
        }
    
    async def initialize(self) -> bool:
        """Load memories from storage - async"""
        async with self._lock:
            try:
                async with aiofiles.open(self.storage_file, 'r') as f:
                    content = await f.read()
                    self.memories = json.loads(content)
                logging.info(f"Loaded {len(self.memories.get('facts', []))} memories (async)")
                return True
            except FileNotFoundError:
                logging.info("No existing memories, starting fresh")
                return True
            except Exception as e:
                logging.error(f"Error loading memories: {e}")
                return True  # Continue anyway
    
    async def execute(self, action: str, **kwargs) -> ToolResult:
        """Execute memory action - async"""
        actions = {
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
        }
        
        if action not in actions:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Unknown action: {action}"
            )
        
        return await actions[action](**kwargs)
    
    async def _remember(self, fact: str, category: str = "facts") -> ToolResult:
        """Remember a new fact - async"""
        async with self._lock:
            memory = {
                "content": fact,
                "timestamp": datetime.now().isoformat(),
                "category": category
            }
            
            if category == "facts":
                self.memories["facts"].append(memory)
            elif category == "preference":
                self.memories["preferences"][fact] = memory
            elif category == "note":
                self.memories["conversation_notes"].append(memory)
            
            await self._save_unlocked()
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            message=f"I'll remember that: {fact}"
        )
    
    async def _recall(self, query: str = "", category: str = "all") -> ToolResult:
        """Recall memories - async"""
        async with self._lock:
            results: List[str] = []
            
            if category in ["all", "facts"]:
                for fact in self.memories.get("facts", []):
                    if not query or query.lower() in fact["content"].lower():
                        results.append(fact["content"])
            
            if category in ["all", "user_info"]:
                for key, value in self.memories.get("user_info", {}).items():
                    if not query or query.lower() in key.lower():
                        results.append(f"{key}: {value}")
            
            if category in ["all", "important_dates"]:
                dates: Dict[str, Any] = self.memories.get("important_dates", {})
                for key, value in dates.items():
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
        """Forget a specific fact - async"""
        async with self._lock:
            original_count = len(self.memories["facts"])
            self.memories["facts"] = [
                f for f in self.memories["facts"] 
                if fact.lower() not in f["content"].lower()
            ]
            removed = original_count - len(self.memories["facts"])
            await self._save_unlocked()
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            message=f"Forgotten {removed} memories"
        )
    
    async def _set_user_info(self, key: str, value: str) -> ToolResult:
        """Set user information - async"""
        async with self._lock:
            self.memories["user_info"][key] = value
            await self._save_unlocked()
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            message=f"Got it, your {key} is {value}"
        )
    
    async def _get_user_info(self, key: str = "") -> ToolResult:
        """Get user information - async"""
        async with self._lock:
            if key:
                value = self.memories["user_info"].get(key)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=value,
                    message=f"Your {key} is {value}" if value else f"I don't know your {key}"
                )
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=self.memories["user_info"].copy()
            )
    
    async def _set_date(self, name: str, date: str) -> ToolResult:
        """Set an important date - async"""
        async with self._lock:
            self.memories["important_dates"][name] = date
            await self._save_unlocked()
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            message=f"I'll remember {name}: {date}"
        )
    
    async def _get_dates(self) -> ToolResult:
        """Get all important dates - async"""
        async with self._lock:
            dates = self.memories.get("important_dates", {}).copy()
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=dates,
            message=f"Found {len(dates)} important dates"
        )
    
    async def _store(self, category: str, key: str, value: str) -> ToolResult:
        """Store any data by category and key - async"""
        async with self._lock:
            if category not in self.memories:
                self.memories[category] = []
            
            entry = {
                "key": key,
                "value": value,
                "timestamp": datetime.now().isoformat()
            }
            
            # For action_log, keep as list (append)
            if category == "action_log":
                self.memories[category].append(entry)
                # Keep only last 100 actions
                if len(self.memories[category]) > 100:
                    self.memories[category] = self.memories[category][-100:]
            else:
                # For other categories, store as dict
                if isinstance(self.memories[category], list):
                    self.memories[category].append(entry)
                else:
                    self.memories[category][key] = entry
            
            await self._save_unlocked()
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            message=f"Stored {key} in {category}"
        )
    
    async def _get_action_log(self, count: int = 20, query: str = "") -> ToolResult:
        """Get recent action history - async"""
        async with self._lock:
            logs = self.memories.get("action_log", [])
            
            # Filter by query if provided
            if query:
                logs = [log for log in logs if query.lower() in log.get("value", "").lower()]
            
            # Get most recent
            recent = logs[-count:] if len(logs) > count else logs
            recent.reverse()  # Most recent first
            
            # Format for display
            formatted = [entry.get("value", str(entry)) for entry in recent]
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=formatted,
            message=f"Found {len(formatted)} actions in history"
        )
    
    async def _log_conversation(self, summary: str, topics: str = "", mood: str = "") -> ToolResult:
        """Log a conversation summary"""
        async with self._lock:
            if "conversation_history" not in self.memories:
                self.memories["conversation_history"] = []
            
            entry = {
                "summary": summary,
                "topics": topics,
                "mood": mood,
                "timestamp": datetime.now().isoformat()
            }
            self.memories["conversation_history"].append(entry)
            
            # Keep last 50 conversations
            if len(self.memories["conversation_history"]) > 50:
                self.memories["conversation_history"] = self.memories["conversation_history"][-50:]
            
            await self._save_unlocked()
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            message=f"Logged conversation: {summary[:50]}..."
        )
    
    async def _get_conversations(self, count: int = 10, query: str = "") -> ToolResult:
        """Get recent conversation history"""
        async with self._lock:
            convos = self.memories.get("conversation_history", [])
            
            if query:
                convos = [c for c in convos if query.lower() in c.get("summary", "").lower() 
                          or query.lower() in c.get("topics", "").lower()]
            
            recent = convos[-count:] if len(convos) > count else convos
            recent.reverse()
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=recent,
            message=f"Found {len(recent)} conversations"
        )
    
    async def _log_script(self, script_name: str, script_path: str, script_type: str, description: str = "") -> ToolResult:
        """Log a script that was created"""
        async with self._lock:
            if "scripts_created" not in self.memories:
                self.memories["scripts_created"] = []
            
            entry = {
                "name": script_name,
                "path": script_path,
                "type": script_type,
                "description": description,
                "timestamp": datetime.now().isoformat()
            }
            self.memories["scripts_created"].append(entry)
            await self._save_unlocked()
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            message=f"Logged script: {script_name}"
        )
    
    async def _get_scripts(self, script_type: str = "", query: str = "") -> ToolResult:
        """Get scripts that were created"""
        async with self._lock:
            scripts = self.memories.get("scripts_created", [])
            
            if script_type:
                scripts = [s for s in scripts if s.get("type", "").lower() == script_type.lower()]
            if query:
                scripts = [s for s in scripts if query.lower() in s.get("name", "").lower() 
                          or query.lower() in s.get("description", "").lower()]
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=scripts,
            message=f"Found {len(scripts)} scripts"
        )
    
    async def _log_topic(self, topic: str) -> ToolResult:
        """Log a topic that was discussed"""
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
            
            await self._save_unlocked()
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            message=f"Logged topic: {topic}"
        )
    
    async def _get_stats(self) -> ToolResult:
        """Get memory and session statistics"""
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
            }
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=stats,
            message=f"Memory stats: {stats['total_facts']} facts, {stats['total_conversations']} conversations"
        )
    
    async def _search_all(self, query: str) -> ToolResult:
        """Search across all memory categories"""
        async with self._lock:
            results = {
                "facts": [],
                "user_info": [],
                "conversations": [],
                "scripts": [],
                "actions": [],
                "topics": []
            }
            query_lower = query.lower()
            
            # Search facts
            for fact in self.memories.get("facts", []):
                if query_lower in fact.get("content", "").lower():
                    results["facts"].append(fact["content"])
            
            # Search user info
            for key, value in self.memories.get("user_info", {}).items():
                if query_lower in key.lower() or query_lower in str(value).lower():
                    results["user_info"].append(f"{key}: {value}")
            
            # Search conversations
            for conv in self.memories.get("conversation_history", []):
                if query_lower in conv.get("summary", "").lower():
                    results["conversations"].append(conv["summary"])
            
            # Search scripts
            for script in self.memories.get("scripts_created", []):
                if query_lower in script.get("name", "").lower() or query_lower in script.get("description", "").lower():
                    results["scripts"].append(f"{script['name']} ({script['type']})")
            
            # Search actions
            for action in self.memories.get("action_log", [])[-50:]:
                if query_lower in action.get("value", "").lower():
                    results["actions"].append(action["value"])
            
            # Search topics
            for topic_key, topic_data in self.memories.get("topics_discussed", {}).items():
                if query_lower in topic_key:
                    results["topics"].append(f"{topic_data['topic']} (discussed {topic_data['count']} times)")
            
            total = sum(len(v) for v in results.values())
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=results,
            message=f"Found {total} matches for '{query}'"
        )
    
    async def _save_unlocked(self):
        """Save memories to file - must be called with lock held"""
        try:
            async with aiofiles.open(self.storage_file, 'w') as f:
                await f.write(json.dumps(self.memories, indent=2))
        except Exception as e:
            logging.error(f"Error saving memories: {e}")
    
    async def _save(self):
        """Save memories to file - async with lock"""
        async with self._lock:
            await self._save_unlocked()
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Full memory system: facts, conversations, actions, scripts, topics, stats, and search",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "remember", "recall", "forget", 
                            "set_user_info", "get_user_info", 
                            "set_date", "get_dates",
                            "store", "get_action_log",
                            "log_conversation", "get_conversations",
                            "log_script", "get_scripts",
                            "log_topic", "get_stats", "search_all"
                        ],
                        "description": "Memory action"
                    },
                    "fact": {"type": "string", "description": "Fact to remember/forget"},
                    "query": {"type": "string", "description": "Search query"},
                    "category": {"type": "string", "description": "Memory category"},
                    "key": {"type": "string", "description": "Key for storing data"},
                    "value": {"type": "string", "description": "Value to store"},
                    "name": {"type": "string", "description": "Name (date or script)"},
                    "date": {"type": "string", "description": "Date value"},
                    "count": {"type": "integer", "description": "Number of entries to retrieve", "default": 20},
                    "summary": {"type": "string", "description": "Conversation summary"},
                    "topics": {"type": "string", "description": "Topics discussed (comma-separated)"},
                    "mood": {"type": "string", "description": "Conversation mood"},
                    "script_name": {"type": "string", "description": "Name of script"},
                    "script_path": {"type": "string", "description": "Path to script"},
                    "script_type": {"type": "string", "description": "Type of script (python, powershell, etc.)"},
                    "description": {"type": "string", "description": "Description of script"},
                    "topic": {"type": "string", "description": "Topic to log"}
                },
                "required": ["action"]
            }
        }
    
    async def cleanup(self):
        """Save before cleanup - async"""
        await self._save()
