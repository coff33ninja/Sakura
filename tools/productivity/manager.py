"""
Productivity Manager for Sakura
Handles reminders, alarms, timers, notes, and to-do lists
Uses Windows notifications and integrates with Windows Alarms app

Rules followed:
- All imports MUST be used
- Async with asyncio.Lock() for thread safety
- aiofiles for file I/O
"""
import asyncio
import logging
import os
import subprocess
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import json
import aiofiles
from ..base import BaseTool, ToolResult, ToolStatus


# Get assistant name for data folder
ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "Sakura")


class ReminderStatus(Enum):
    """Status of a reminder"""
    PENDING = "pending"
    TRIGGERED = "triggered"
    DISMISSED = "dismissed"
    SNOOZED = "snoozed"


class TaskPriority(Enum):
    """Priority levels for tasks"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Reminder:
    """A reminder/alarm"""
    id: str
    title: str
    message: str
    trigger_time: str  # ISO format
    status: str = "pending"
    repeat: Optional[str] = None  # daily, weekly, monthly, none
    created_at: str = ""
    snoozed_until: Optional[str] = None


@dataclass
class Timer:
    """A countdown timer"""
    id: str
    name: str
    duration_seconds: int
    started_at: str
    ends_at: str
    is_running: bool = True
    is_completed: bool = False


@dataclass
class Note:
    """A quick note"""
    id: str
    title: str
    content: str
    created_at: str
    updated_at: str
    tags: List[str] = field(default_factory=list)
    pinned: bool = False


@dataclass
class TodoItem:
    """A to-do item"""
    id: str
    title: str
    description: str = ""
    priority: str = "medium"
    due_date: Optional[str] = None
    completed: bool = False
    created_at: str = ""
    completed_at: Optional[str] = None
    tags: List[str] = field(default_factory=list)


class ProductivityManager(BaseTool):
    """Productivity tool - reminders, alarms, timers, notes, to-do lists"""
    
    name = "productivity"
    description = "Manage reminders, alarms, timers, notes, and to-do lists. Set timers, create reminders with Windows notifications, take quick notes, manage tasks."
    
    def __init__(self):
        self._lock = asyncio.Lock()
        self.is_windows = os.name == 'nt'
        self.data_dir: Path = Path.home() / "Documents" / ASSISTANT_NAME / "productivity"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Data files
        self.reminders_file = self.data_dir / "reminders.json"
        self.timers_file = self.data_dir / "timers.json"
        self.notes_file = self.data_dir / "notes.json"
        self.todos_file = self.data_dir / "todos.json"
        
        # In-memory data
        self.reminders: Dict[str, Reminder] = {}
        self.timers: Dict[str, Timer] = {}
        self.notes: Dict[str, Note] = {}
        self.todos: Dict[str, TodoItem] = {}
        
        # Active timer tasks
        self._timer_tasks: Dict[str, asyncio.Task] = {}
        self._reminder_task: Optional[asyncio.Task] = None
        self._counter = 0
    
    async def initialize(self) -> bool:
        """Initialize productivity manager and load data"""
        try:
            await self._load_all_data()
            
            # Start reminder checker background task
            self._reminder_task = asyncio.create_task(self._reminder_checker())
            
            # Resume any active timers
            await self._resume_timers()
            
            logging.info(f"Productivity manager initialized (data: {self.data_dir})")
            return True
        except Exception as e:
            logging.error(f"Failed to initialize productivity manager: {e}")
            return False
    
    async def execute(self, action: str, **kwargs) -> ToolResult:
        """Execute productivity action"""
        actions = {
            # Reminders/Alarms
            "set_reminder": self._set_reminder,
            "list_reminders": self._list_reminders,
            "cancel_reminder": self._cancel_reminder,
            "snooze_reminder": self._snooze_reminder,
            # Timers
            "start_timer": self._start_timer,
            "stop_timer": self._stop_timer,
            "list_timers": self._list_timers,
            "get_timer_status": self._get_timer_status,
            # Stopwatch
            "start_stopwatch": self._start_stopwatch,
            "stop_stopwatch": self._stop_stopwatch,
            # Notes
            "create_note": self._create_note,
            "get_note": self._get_note,
            "update_note": self._update_note,
            "delete_note": self._delete_note,
            "list_notes": self._list_notes,
            "search_notes": self._search_notes,
            # To-Do
            "add_todo": self._add_todo,
            "complete_todo": self._complete_todo,
            "update_todo": self._update_todo,
            "delete_todo": self._delete_todo,
            "list_todos": self._list_todos,
            # Windows integration
            "open_alarms_app": self._open_alarms_app,
            "show_notification": self._show_notification,
        }
        
        if action not in actions:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Unknown action: {action}. Available: {list(actions.keys())}"
            )
        
        return await actions[action](**kwargs)
    
    # ==================== REMINDERS ====================
    
    async def _set_reminder(self, title: str, time: str, message: str = "", 
                            repeat: str = "none", **kwargs) -> ToolResult:
        """Set a reminder/alarm
        
        Args:
            title: Reminder title
            time: When to trigger - supports:
                  - Relative: "5 minutes", "1 hour", "30 seconds"
                  - Absolute: "14:30", "2:30 PM", "tomorrow 9am"
                  - ISO: "2025-12-25T10:00:00"
            message: Optional message to show
            repeat: "none", "daily", "weekly", "monthly"
        """
        async with self._lock:
            try:
                trigger_time = self._parse_time(time)
                if not trigger_time:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error=f"Could not parse time: {time}"
                    )
                
                # Check if time is in the past
                if trigger_time <= datetime.now():
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error="Reminder time must be in the future"
                    )
                
                self._counter += 1
                reminder_id = f"rem_{self._counter}_{datetime.now().strftime('%H%M%S')}"
                
                reminder = Reminder(
                    id=reminder_id,
                    title=title,
                    message=message or title,
                    trigger_time=trigger_time.isoformat(),
                    repeat=repeat if repeat != "none" else None,
                    created_at=datetime.now().isoformat()
                )
                
                self.reminders[reminder_id] = reminder
                await self._save_reminders()
                
                # Format time for display
                time_diff = trigger_time - datetime.now()
                if time_diff.total_seconds() < 3600:
                    time_str = f"{int(time_diff.total_seconds() / 60)} minutes"
                elif time_diff.total_seconds() < 86400:
                    time_str = f"{time_diff.total_seconds() / 3600:.1f} hours"
                else:
                    time_str = trigger_time.strftime("%Y-%m-%d %H:%M")
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"id": reminder_id, "trigger_time": trigger_time.isoformat()},
                    message=f"⏰ Reminder set: '{title}' in {time_str}"
                )
                
            except Exception as e:
                return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _list_reminders(self, include_triggered: bool = False, **kwargs) -> ToolResult:
        """List all reminders"""
        async with self._lock:
            reminders = []
            now = datetime.now()
            
            for rem in self.reminders.values():
                if not include_triggered and rem.status != "pending":
                    continue
                
                trigger_time = datetime.fromisoformat(rem.trigger_time)
                time_until = trigger_time - now
                
                if time_until.total_seconds() > 0:
                    if time_until.total_seconds() < 3600:
                        time_str = f"in {int(time_until.total_seconds() / 60)} min"
                    elif time_until.total_seconds() < 86400:
                        time_str = f"in {time_until.total_seconds() / 3600:.1f} hrs"
                    else:
                        time_str = trigger_time.strftime("%m/%d %H:%M")
                else:
                    time_str = "overdue"
                
                reminders.append({
                    "id": rem.id,
                    "title": rem.title,
                    "time": time_str,
                    "trigger_time": rem.trigger_time,
                    "status": rem.status,
                    "repeat": rem.repeat
                })
            
            # Sort by trigger time
            reminders.sort(key=lambda x: x["trigger_time"])
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=reminders,
                message=f"📋 {len(reminders)} reminder(s)"
            )
    
    async def _cancel_reminder(self, reminder_id: str, **kwargs) -> ToolResult:
        """Cancel a reminder"""
        async with self._lock:
            if reminder_id not in self.reminders:
                return ToolResult(status=ToolStatus.ERROR, error=f"Reminder not found: {reminder_id}")
            
            title = self.reminders[reminder_id].title
            del self.reminders[reminder_id]
            await self._save_reminders()
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"🚫 Cancelled reminder: '{title}'"
            )
    
    async def _snooze_reminder(self, reminder_id: str, minutes: int = 5, **kwargs) -> ToolResult:
        """Snooze a reminder"""
        async with self._lock:
            if reminder_id not in self.reminders:
                return ToolResult(status=ToolStatus.ERROR, error=f"Reminder not found: {reminder_id}")
            
            reminder = self.reminders[reminder_id]
            new_time = datetime.now() + timedelta(minutes=minutes)
            reminder.trigger_time = new_time.isoformat()
            reminder.status = "pending"
            reminder.snoozed_until = new_time.isoformat()
            await self._save_reminders()
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"😴 Snoozed '{reminder.title}' for {minutes} minutes"
            )

    
    # ==================== TIMERS ====================
    
    async def _start_timer(self, duration: str, name: str = "Timer", **kwargs) -> ToolResult:
        """Start a countdown timer
        
        Args:
            duration: Duration string like "5 minutes", "1 hour 30 minutes", "90 seconds"
            name: Optional name for the timer
        """
        async with self._lock:
            try:
                seconds = self._parse_duration(duration)
                if seconds <= 0:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error=f"Invalid duration: {duration}"
                    )
                
                self._counter += 1
                timer_id = f"timer_{self._counter}_{datetime.now().strftime('%H%M%S')}"
                
                now = datetime.now()
                ends_at = now + timedelta(seconds=seconds)
                
                timer = Timer(
                    id=timer_id,
                    name=name,
                    duration_seconds=seconds,
                    started_at=now.isoformat(),
                    ends_at=ends_at.isoformat()
                )
                
                self.timers[timer_id] = timer
                await self._save_timers()
                
                # Start background task for this timer
                task = asyncio.create_task(self._timer_countdown(timer_id, seconds))
                self._timer_tasks[timer_id] = task
                
                # Format duration for display
                if seconds < 60:
                    dur_str = f"{seconds} seconds"
                elif seconds < 3600:
                    dur_str = f"{seconds // 60} minutes"
                else:
                    hours = seconds // 3600
                    mins = (seconds % 3600) // 60
                    dur_str = f"{hours}h {mins}m" if mins else f"{hours} hours"
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"id": timer_id, "duration_seconds": seconds, "ends_at": ends_at.isoformat()},
                    message=f"⏱️ Timer started: {name} ({dur_str})"
                )
                
            except Exception as e:
                return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _timer_countdown(self, timer_id: str, seconds: int):
        """Background task for timer countdown"""
        try:
            await asyncio.sleep(seconds)
            
            async with self._lock:
                if timer_id in self.timers:
                    timer = self.timers[timer_id]
                    timer.is_running = False
                    timer.is_completed = True
                    await self._save_timers()
                    
                    # Show notification
                    await self._show_notification(
                        title="⏱️ Timer Complete!",
                        message=f"{timer.name} has finished!"
                    )
                    
                    logging.info(f"Timer completed: {timer.name}")
                    
        except asyncio.CancelledError:
            logging.info(f"Timer cancelled: {timer_id}")
        except Exception as e:
            logging.error(f"Timer error: {e}")
    
    async def _stop_timer(self, timer_id: str, **kwargs) -> ToolResult:
        """Stop/cancel a timer"""
        async with self._lock:
            if timer_id not in self.timers:
                return ToolResult(status=ToolStatus.ERROR, error=f"Timer not found: {timer_id}")
            
            timer = self.timers[timer_id]
            
            # Cancel the background task
            if timer_id in self._timer_tasks:
                self._timer_tasks[timer_id].cancel()
                del self._timer_tasks[timer_id]
            
            # Calculate elapsed time
            started = datetime.fromisoformat(timer.started_at)
            elapsed = datetime.now() - started
            elapsed_str = str(timedelta(seconds=int(elapsed.total_seconds())))
            
            timer.is_running = False
            await self._save_timers()
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"elapsed": elapsed_str},
                message=f"⏹️ Stopped timer: {timer.name} (elapsed: {elapsed_str})"
            )
    
    async def _list_timers(self, **kwargs) -> ToolResult:
        """List all timers"""
        async with self._lock:
            timers = []
            now = datetime.now()
            
            for timer in self.timers.values():
                ends_at = datetime.fromisoformat(timer.ends_at)
                remaining = ends_at - now
                
                if timer.is_running and remaining.total_seconds() > 0:
                    remaining_str = str(timedelta(seconds=int(remaining.total_seconds())))
                    status = "running"
                elif timer.is_completed:
                    remaining_str = "0:00:00"
                    status = "completed"
                else:
                    remaining_str = "stopped"
                    status = "stopped"
                
                timers.append({
                    "id": timer.id,
                    "name": timer.name,
                    "remaining": remaining_str,
                    "status": status,
                    "duration_seconds": timer.duration_seconds
                })
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=timers,
                message=f"⏱️ {len(timers)} timer(s)"
            )
    
    async def _get_timer_status(self, timer_id: str, **kwargs) -> ToolResult:
        """Get status of a specific timer"""
        async with self._lock:
            if timer_id not in self.timers:
                return ToolResult(status=ToolStatus.ERROR, error=f"Timer not found: {timer_id}")
            
            timer = self.timers[timer_id]
            now = datetime.now()
            ends_at = datetime.fromisoformat(timer.ends_at)
            started_at = datetime.fromisoformat(timer.started_at)
            
            remaining = max(0, (ends_at - now).total_seconds())
            elapsed = (now - started_at).total_seconds()
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "id": timer.id,
                    "name": timer.name,
                    "remaining_seconds": int(remaining),
                    "remaining": str(timedelta(seconds=int(remaining))),
                    "elapsed_seconds": int(elapsed),
                    "elapsed": str(timedelta(seconds=int(elapsed))),
                    "is_running": timer.is_running,
                    "is_completed": timer.is_completed
                },
                message=f"⏱️ {timer.name}: {str(timedelta(seconds=int(remaining)))} remaining"
            )
    
    # ==================== STOPWATCH ====================
    
    async def _start_stopwatch(self, name: str = "Stopwatch", **kwargs) -> ToolResult:
        """Start a stopwatch (timer counting up)"""
        async with self._lock:
            self._counter += 1
            stopwatch_id = f"sw_{self._counter}_{datetime.now().strftime('%H%M%S')}"
            
            now = datetime.now()
            
            # Use Timer with very long duration (24 hours) as stopwatch
            timer = Timer(
                id=stopwatch_id,
                name=name,
                duration_seconds=86400,  # 24 hours max
                started_at=now.isoformat(),
                ends_at=(now + timedelta(hours=24)).isoformat()
            )
            
            self.timers[stopwatch_id] = timer
            await self._save_timers()
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"id": stopwatch_id, "started_at": now.isoformat()},
                message=f"⏱️ Stopwatch started: {name}"
            )
    
    async def _stop_stopwatch(self, stopwatch_id: str, **kwargs) -> ToolResult:
        """Stop a stopwatch and get elapsed time"""
        return await self._stop_timer(stopwatch_id)

    
    # ==================== NOTES ====================
    
    async def _create_note(self, title: str, content: str = "", tags: List[str] = None, 
                           pinned: bool = False, **kwargs) -> ToolResult:
        """Create a quick note"""
        async with self._lock:
            self._counter += 1
            note_id = f"note_{self._counter}_{datetime.now().strftime('%H%M%S')}"
            
            now = datetime.now().isoformat()
            
            note = Note(
                id=note_id,
                title=title,
                content=content,
                created_at=now,
                updated_at=now,
                tags=tags or [],
                pinned=pinned
            )
            
            self.notes[note_id] = note
            await self._save_notes()
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"id": note_id},
                message=f"📝 Note created: '{title}'"
            )
    
    async def _get_note(self, note_id: str, **kwargs) -> ToolResult:
        """Get a note by ID"""
        async with self._lock:
            if note_id not in self.notes:
                return ToolResult(status=ToolStatus.ERROR, error=f"Note not found: {note_id}")
            
            note = self.notes[note_id]
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=asdict(note),
                message=f"📝 {note.title}"
            )
    
    async def _update_note(self, note_id: str, title: str = None, content: str = None,
                           tags: List[str] = None, pinned: bool = None, **kwargs) -> ToolResult:
        """Update a note"""
        async with self._lock:
            if note_id not in self.notes:
                return ToolResult(status=ToolStatus.ERROR, error=f"Note not found: {note_id}")
            
            note = self.notes[note_id]
            
            if title is not None:
                note.title = title
            if content is not None:
                note.content = content
            if tags is not None:
                note.tags = tags
            if pinned is not None:
                note.pinned = pinned
            
            note.updated_at = datetime.now().isoformat()
            await self._save_notes()
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"📝 Updated note: '{note.title}'"
            )
    
    async def _delete_note(self, note_id: str, **kwargs) -> ToolResult:
        """Delete a note"""
        async with self._lock:
            if note_id not in self.notes:
                return ToolResult(status=ToolStatus.ERROR, error=f"Note not found: {note_id}")
            
            title = self.notes[note_id].title
            del self.notes[note_id]
            await self._save_notes()
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"🗑️ Deleted note: '{title}'"
            )
    
    async def _list_notes(self, tag: str = None, pinned_only: bool = False, **kwargs) -> ToolResult:
        """List all notes"""
        async with self._lock:
            notes = []
            
            for note in self.notes.values():
                if pinned_only and not note.pinned:
                    continue
                if tag and tag not in note.tags:
                    continue
                
                notes.append({
                    "id": note.id,
                    "title": note.title,
                    "preview": note.content[:100] + "..." if len(note.content) > 100 else note.content,
                    "tags": note.tags,
                    "pinned": note.pinned,
                    "updated_at": note.updated_at
                })
            
            # Sort: pinned first, then by updated_at
            notes.sort(key=lambda x: (not x["pinned"], x["updated_at"]), reverse=True)
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=notes,
                message=f"📝 {len(notes)} note(s)"
            )
    
    async def _search_notes(self, query: str, **kwargs) -> ToolResult:
        """Search notes by title or content"""
        async with self._lock:
            query_lower = query.lower()
            results = []
            
            for note in self.notes.values():
                if query_lower in note.title.lower() or query_lower in note.content.lower():
                    results.append({
                        "id": note.id,
                        "title": note.title,
                        "preview": note.content[:100] + "..." if len(note.content) > 100 else note.content,
                        "tags": note.tags
                    })
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=results,
                message=f"🔍 Found {len(results)} note(s) matching '{query}'"
            )
    
    # ==================== TO-DO ====================
    
    async def _add_todo(self, title: str, description: str = "", priority: str = "medium",
                        due_date: str = None, tags: List[str] = None, **kwargs) -> ToolResult:
        """Add a to-do item"""
        async with self._lock:
            self._counter += 1
            todo_id = f"todo_{self._counter}_{datetime.now().strftime('%H%M%S')}"
            
            # Parse due date if provided
            parsed_due = None
            if due_date:
                parsed_due = self._parse_time(due_date)
                if parsed_due:
                    parsed_due = parsed_due.isoformat()
            
            todo = TodoItem(
                id=todo_id,
                title=title,
                description=description,
                priority=priority,
                due_date=parsed_due,
                created_at=datetime.now().isoformat(),
                tags=tags or []
            )
            
            self.todos[todo_id] = todo
            await self._save_todos()
            
            priority_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "urgent": "🔴"}.get(priority, "⚪")
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"id": todo_id},
                message=f"{priority_emoji} Added task: '{title}'"
            )
    
    async def _complete_todo(self, todo_id: str, **kwargs) -> ToolResult:
        """Mark a to-do item as complete"""
        async with self._lock:
            if todo_id not in self.todos:
                return ToolResult(status=ToolStatus.ERROR, error=f"Task not found: {todo_id}")
            
            todo = self.todos[todo_id]
            todo.completed = True
            todo.completed_at = datetime.now().isoformat()
            await self._save_todos()
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"✅ Completed: '{todo.title}'"
            )
    
    async def _update_todo(self, todo_id: str, title: str = None, description: str = None,
                           priority: str = None, due_date: str = None, tags: List[str] = None,
                           completed: bool = None, **kwargs) -> ToolResult:
        """Update a to-do item"""
        async with self._lock:
            if todo_id not in self.todos:
                return ToolResult(status=ToolStatus.ERROR, error=f"Task not found: {todo_id}")
            
            todo = self.todos[todo_id]
            
            if title is not None:
                todo.title = title
            if description is not None:
                todo.description = description
            if priority is not None:
                todo.priority = priority
            if due_date is not None:
                parsed = self._parse_time(due_date)
                todo.due_date = parsed.isoformat() if parsed else None
            if tags is not None:
                todo.tags = tags
            if completed is not None:
                todo.completed = completed
                if completed:
                    todo.completed_at = datetime.now().isoformat()
                else:
                    todo.completed_at = None
            
            await self._save_todos()
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"📝 Updated task: '{todo.title}'"
            )
    
    async def _delete_todo(self, todo_id: str, **kwargs) -> ToolResult:
        """Delete a to-do item"""
        async with self._lock:
            if todo_id not in self.todos:
                return ToolResult(status=ToolStatus.ERROR, error=f"Task not found: {todo_id}")
            
            title = self.todos[todo_id].title
            del self.todos[todo_id]
            await self._save_todos()
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"🗑️ Deleted task: '{title}'"
            )
    
    async def _list_todos(self, show_completed: bool = False, priority: str = None,
                          tag: str = None, **kwargs) -> ToolResult:
        """List to-do items"""
        async with self._lock:
            todos = []
            priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
            
            for todo in self.todos.values():
                if not show_completed and todo.completed:
                    continue
                if priority and todo.priority != priority:
                    continue
                if tag and tag not in todo.tags:
                    continue
                
                priority_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "urgent": "🔴"}.get(todo.priority, "⚪")
                
                item = {
                    "id": todo.id,
                    "title": todo.title,
                    "priority": todo.priority,
                    "priority_emoji": priority_emoji,
                    "completed": todo.completed,
                    "due_date": todo.due_date,
                    "tags": todo.tags
                }
                
                # Check if overdue
                if todo.due_date and not todo.completed:
                    due = datetime.fromisoformat(todo.due_date)
                    if due < datetime.now():
                        item["overdue"] = True
                
                todos.append(item)
            
            # Sort by priority, then due date
            todos.sort(key=lambda x: (
                x["completed"],
                priority_order.get(x["priority"], 2),
                x["due_date"] or "9999"
            ))
            
            pending = sum(1 for t in todos if not t["completed"])
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=todos,
                message=f"📋 {pending} pending task(s)"
            )

    
    # ==================== WINDOWS INTEGRATION ====================
    
    async def _open_alarms_app(self, **kwargs) -> ToolResult:
        """Open Windows Alarms & Clock app"""
        try:
            await asyncio.to_thread(
                subprocess.run,
                ["cmd", "/c", "start", "ms-clock:"],
                capture_output=True,
                timeout=10
            )
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message="⏰ Opened Windows Alarms & Clock"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _show_notification(self, title: str, message: str = "", **kwargs) -> ToolResult:
        """Show a Windows toast notification"""
        try:
            # Use PowerShell to show toast notification
            ps_script = f'''
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
            [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

            $template = @"
            <toast>
                <visual>
                    <binding template="ToastText02">
                        <text id="1">{title}</text>
                        <text id="2">{message}</text>
                    </binding>
                </visual>
                <audio src="ms-winsoundevent:Notification.Default"/>
            </toast>
"@

            $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
            $xml.LoadXml($template)
            $toast = New-Object Windows.UI.Notifications.ToastNotification $xml
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("{ASSISTANT_NAME}").Show($toast)
            '''
            
            result = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    message=f"🔔 Notification shown: {title}"
                )
            else:
                # Fallback to simpler notification
                return await self._show_notification_fallback(title, message)
                
        except Exception:
            return await self._show_notification_fallback(title, message)
    
    async def _show_notification_fallback(self, title: str, message: str) -> ToolResult:
        """Fallback notification using msg command or balloon tip"""
        try:
            # Try balloon tip via PowerShell
            ps_script = f'''
            Add-Type -AssemblyName System.Windows.Forms
            $balloon = New-Object System.Windows.Forms.NotifyIcon
            $balloon.Icon = [System.Drawing.SystemIcons]::Information
            $balloon.BalloonTipTitle = "{title}"
            $balloon.BalloonTipText = "{message}"
            $balloon.Visible = $true
            $balloon.ShowBalloonTip(5000)
            Start-Sleep -Seconds 5
            $balloon.Dispose()
            '''
            
            await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                timeout=10
            )
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"🔔 Notification shown: {title}"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    # ==================== HELPER METHODS ====================
    
    def _parse_time(self, time_str: str) -> Optional[datetime]:
        """Parse various time formats into datetime"""
        now = datetime.now()
        time_str = time_str.lower().strip()
        
        # Try ISO format first
        try:
            return datetime.fromisoformat(time_str)
        except ValueError:
            pass
        
        # Relative time: "5 minutes", "1 hour", "30 seconds"
        import re
        relative_match = re.match(r'(\d+)\s*(second|sec|minute|min|hour|hr|day)s?', time_str)
        if relative_match:
            amount = int(relative_match.group(1))
            unit = relative_match.group(2)
            
            if unit in ['second', 'sec']:
                return now + timedelta(seconds=amount)
            elif unit in ['minute', 'min']:
                return now + timedelta(minutes=amount)
            elif unit in ['hour', 'hr']:
                return now + timedelta(hours=amount)
            elif unit == 'day':
                return now + timedelta(days=amount)
        
        # Time only: "14:30", "2:30 PM"
        time_match = re.match(r'(\d{1,2}):(\d{2})\s*(am|pm)?', time_str)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            ampm = time_match.group(3)
            
            if ampm == 'pm' and hour < 12:
                hour += 12
            elif ampm == 'am' and hour == 12:
                hour = 0
            
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            return target
        
        # "tomorrow 9am", "tomorrow 14:00"
        if 'tomorrow' in time_str:
            tomorrow = now + timedelta(days=1)
            time_part = time_str.replace('tomorrow', '').strip()
            if time_part:
                parsed = self._parse_time(time_part)
                if parsed:
                    return tomorrow.replace(hour=parsed.hour, minute=parsed.minute, second=0)
            return tomorrow.replace(hour=9, minute=0, second=0)
        
        return None
    
    def _parse_duration(self, duration_str: str) -> int:
        """Parse duration string into seconds"""
        import re
        duration_str = duration_str.lower().strip()
        total_seconds = 0
        
        # Match patterns like "1 hour 30 minutes", "5 min", "90 seconds"
        patterns = [
            (r'(\d+)\s*(?:hour|hr|h)', 3600),
            (r'(\d+)\s*(?:minute|min|m)(?!s)', 60),
            (r'(\d+)\s*(?:second|sec|s)', 1),
        ]
        
        for pattern, multiplier in patterns:
            match = re.search(pattern, duration_str)
            if match:
                total_seconds += int(match.group(1)) * multiplier
        
        # If no pattern matched, try to parse as just a number (assume minutes)
        if total_seconds == 0:
            try:
                total_seconds = int(duration_str) * 60
            except ValueError:
                pass
        
        return total_seconds
    
    async def _reminder_checker(self):
        """Background task to check and trigger reminders"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                async with self._lock:
                    now = datetime.now()
                    
                    for reminder in list(self.reminders.values()):
                        if reminder.status != "pending":
                            continue
                        
                        trigger_time = datetime.fromisoformat(reminder.trigger_time)
                        
                        if trigger_time <= now:
                            # Trigger the reminder
                            reminder.status = "triggered"
                            
                            await self._show_notification(
                                title=f"⏰ {reminder.title}",
                                message=reminder.message
                            )
                            
                            logging.info(f"Reminder triggered: {reminder.title}")
                            
                            # Handle repeat
                            if reminder.repeat:
                                if reminder.repeat == "daily":
                                    new_time = trigger_time + timedelta(days=1)
                                elif reminder.repeat == "weekly":
                                    new_time = trigger_time + timedelta(weeks=1)
                                elif reminder.repeat == "monthly":
                                    new_time = trigger_time + timedelta(days=30)
                                else:
                                    new_time = None
                                
                                if new_time:
                                    reminder.trigger_time = new_time.isoformat()
                                    reminder.status = "pending"
                    
                    await self._save_reminders()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Reminder checker error: {e}")
    
    async def _resume_timers(self):
        """Resume any active timers from saved state"""
        now = datetime.now()
        
        for timer in list(self.timers.values()):
            if timer.is_running and not timer.is_completed:
                ends_at = datetime.fromisoformat(timer.ends_at)
                remaining = (ends_at - now).total_seconds()
                
                if remaining > 0:
                    # Resume the timer
                    task = asyncio.create_task(self._timer_countdown(timer.id, int(remaining)))
                    self._timer_tasks[timer.id] = task
                    logging.info(f"Resumed timer: {timer.name} ({int(remaining)}s remaining)")
                else:
                    # Timer already expired
                    timer.is_running = False
                    timer.is_completed = True
        
        await self._save_timers()
    
    # ==================== DATA PERSISTENCE ====================
    
    async def _load_all_data(self):
        """Load all data from files"""
        await self._load_reminders()
        await self._load_timers()
        await self._load_notes()
        await self._load_todos()
    
    async def _load_reminders(self):
        """Load reminders from file"""
        try:
            if self.reminders_file.exists():
                async with aiofiles.open(self.reminders_file, 'r') as f:
                    data = json.loads(await f.read())
                    for item in data:
                        self.reminders[item['id']] = Reminder(**item)
        except Exception as e:
            logging.warning(f"Could not load reminders: {e}")
    
    async def _save_reminders(self):
        """Save reminders to file"""
        try:
            data = [asdict(r) for r in self.reminders.values()]
            async with aiofiles.open(self.reminders_file, 'w') as f:
                await f.write(json.dumps(data, indent=2))
        except Exception as e:
            logging.error(f"Could not save reminders: {e}")
    
    async def _load_timers(self):
        """Load timers from file"""
        try:
            if self.timers_file.exists():
                async with aiofiles.open(self.timers_file, 'r') as f:
                    data = json.loads(await f.read())
                    for item in data:
                        self.timers[item['id']] = Timer(**item)
        except Exception as e:
            logging.warning(f"Could not load timers: {e}")
    
    async def _save_timers(self):
        """Save timers to file"""
        try:
            data = [asdict(t) for t in self.timers.values()]
            async with aiofiles.open(self.timers_file, 'w') as f:
                await f.write(json.dumps(data, indent=2))
        except Exception as e:
            logging.error(f"Could not save timers: {e}")
    
    async def _load_notes(self):
        """Load notes from file"""
        try:
            if self.notes_file.exists():
                async with aiofiles.open(self.notes_file, 'r') as f:
                    data = json.loads(await f.read())
                    for item in data:
                        self.notes[item['id']] = Note(**item)
        except Exception as e:
            logging.warning(f"Could not load notes: {e}")
    
    async def _save_notes(self):
        """Save notes to file"""
        try:
            data = [asdict(n) for n in self.notes.values()]
            async with aiofiles.open(self.notes_file, 'w') as f:
                await f.write(json.dumps(data, indent=2))
        except Exception as e:
            logging.error(f"Could not save notes: {e}")
    
    async def _load_todos(self):
        """Load todos from file"""
        try:
            if self.todos_file.exists():
                async with aiofiles.open(self.todos_file, 'r') as f:
                    data = json.loads(await f.read())
                    for item in data:
                        self.todos[item['id']] = TodoItem(**item)
        except Exception as e:
            logging.warning(f"Could not load todos: {e}")
    
    async def _save_todos(self):
        """Save todos to file"""
        try:
            data = [asdict(t) for t in self.todos.values()]
            async with aiofiles.open(self.todos_file, 'w') as f:
                await f.write(json.dumps(data, indent=2))
        except Exception as e:
            logging.error(f"Could not save todos: {e}")

    
    def get_schema(self) -> Dict[str, Any]:
        """Return schema for productivity tools"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            # Reminders
                            "set_reminder", "list_reminders", "cancel_reminder", "snooze_reminder",
                            # Timers
                            "start_timer", "stop_timer", "list_timers", "get_timer_status",
                            # Stopwatch
                            "start_stopwatch", "stop_stopwatch",
                            # Notes
                            "create_note", "get_note", "update_note", "delete_note", 
                            "list_notes", "search_notes",
                            # To-Do
                            "add_todo", "complete_todo", "update_todo", "delete_todo", "list_todos",
                            # Windows
                            "open_alarms_app", "show_notification"
                        ],
                        "description": "Productivity action to perform"
                    },
                    # Reminder params
                    "title": {"type": "string", "description": "Title for reminder/note/todo"},
                    "time": {"type": "string", "description": "Time for reminder: '5 minutes', '14:30', 'tomorrow 9am'"},
                    "message": {"type": "string", "description": "Message content"},
                    "repeat": {
                        "type": "string",
                        "enum": ["none", "daily", "weekly", "monthly"],
                        "description": "Repeat frequency for reminders"
                    },
                    "reminder_id": {"type": "string", "description": "Reminder ID"},
                    "minutes": {"type": "integer", "description": "Minutes to snooze", "default": 5},
                    # Timer params
                    "duration": {"type": "string", "description": "Timer duration: '5 minutes', '1 hour 30 min'"},
                    "name": {"type": "string", "description": "Name for timer/stopwatch"},
                    "timer_id": {"type": "string", "description": "Timer/stopwatch ID"},
                    "stopwatch_id": {"type": "string", "description": "Stopwatch ID"},
                    # Note params
                    "note_id": {"type": "string", "description": "Note ID"},
                    "content": {"type": "string", "description": "Note content"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for notes/todos"
                    },
                    "pinned": {"type": "boolean", "description": "Pin the note"},
                    "query": {"type": "string", "description": "Search query for notes"},
                    "tag": {"type": "string", "description": "Filter by tag"},
                    "pinned_only": {"type": "boolean", "description": "Show only pinned notes"},
                    # Todo params
                    "todo_id": {"type": "string", "description": "Todo item ID"},
                    "description": {"type": "string", "description": "Todo description"},
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "urgent"],
                        "description": "Task priority"
                    },
                    "due_date": {"type": "string", "description": "Due date: 'tomorrow', '2025-12-25'"},
                    "completed": {"type": "boolean", "description": "Mark todo as completed/uncompleted"},
                    "show_completed": {"type": "boolean", "description": "Include completed todos"},
                    "include_triggered": {"type": "boolean", "description": "Include triggered reminders"}
                },
                "required": ["action"]
            }
        }
    
    async def cleanup(self):
        """Cleanup productivity manager"""
        # Cancel reminder checker
        if self._reminder_task:
            self._reminder_task.cancel()
            try:
                await self._reminder_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all timer tasks
        for task in self._timer_tasks.values():
            task.cancel()
        
        if self._timer_tasks:
            await asyncio.gather(*self._timer_tasks.values(), return_exceptions=True)
        
        # Save all data
        await self._save_reminders()
        await self._save_timers()
        await self._save_notes()
        await self._save_todos()
        
        logging.info("Productivity manager cleanup completed")
