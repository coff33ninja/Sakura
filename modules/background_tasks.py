"""
Background Task Manager for Sakura
Executes tasks in background while keeping voice connection alive

Rules followed:
- All imports MUST be used
- Async with asyncio.Lock() for thread safety
- aiofiles for file I/O
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import aiofiles


class TaskState(Enum):
    """State of a background task"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BackgroundTask:
    """A task running in the background"""
    id: str
    name: str
    description: str
    state: TaskState = TaskState.PENDING
    progress: float = 0.0  # 0.0 to 1.0
    progress_message: str = ""
    result: Any = None
    error: Optional[str] = None
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    subtasks: List[str] = field(default_factory=list)
    current_subtask: int = 0


class BackgroundTaskManager:
    """Manages background task execution without blocking voice"""
    
    def __init__(self):
        self._lock = asyncio.Lock()
        self._tasks: Dict[str, BackgroundTask] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._task_coroutines: Dict[str, Callable[[BackgroundTask], Awaitable[Any]]] = {}  # Store coroutines for queued tasks
        self._task_counter = 0
        self._max_concurrent = 3  # Max concurrent background tasks
        self._task_timeout = timedelta(minutes=10)  # Default timeout (increased for long searches)
        self._completion_callbacks: List[Callable[[BackgroundTask], Awaitable[None]]] = []
        self._newly_completed: List[str] = []  # Task IDs that completed since last check
    
    def on_task_complete(self, callback: Callable[[BackgroundTask], Awaitable[None]]):
        """Register a callback to be called when any task completes"""
        self._completion_callbacks.append(callback)
    
    async def get_newly_completed_tasks(self) -> List[Dict[str, Any]]:
        """Get tasks that completed since last check and clear the list"""
        async with self._lock:
            completed = []
            for task_id in self._newly_completed:
                if task_id in self._tasks:
                    task = self._tasks[task_id]
                    completed.append({
                        "id": task.id,
                        "name": task.name,
                        "description": task.description,
                        "state": task.state.value,
                        "result": task.result,
                        "error": task.error,
                        "duration": self._calculate_duration(task)
                    })
            self._newly_completed.clear()
            return completed
    
    def _calculate_duration(self, task: BackgroundTask) -> str:
        """Calculate human-readable duration"""
        if not task.started_at or not task.completed_at:
            return "unknown"
        try:
            start = datetime.fromisoformat(task.started_at)
            end = datetime.fromisoformat(task.completed_at)
            duration = end - start
            if duration.total_seconds() < 60:
                return f"{duration.total_seconds():.1f} seconds"
            elif duration.total_seconds() < 3600:
                return f"{duration.total_seconds() / 60:.1f} minutes"
            else:
                return f"{duration.total_seconds() / 3600:.1f} hours"
        except Exception:
            return "unknown"
    
    async def has_pending_notifications(self) -> bool:
        """Check if there are completed tasks waiting to be announced"""
        async with self._lock:
            return len(self._newly_completed) > 0
    
    async def submit_task(
        self,
        name: str,
        description: str,
        coroutine: Callable[['BackgroundTask'], Awaitable[Any]],
        subtasks: Optional[List[str]] = None,
        timeout_minutes: int = 10
    ) -> str:
        """
        Submit a task to run in background
        
        Args:
            name: Short name for the task
            description: What the task does
            coroutine: Async function that takes BackgroundTask and returns result
            subtasks: Optional list of subtask descriptions for progress tracking
            timeout_minutes: Task timeout in minutes (default 10)
        
        Returns:
            Task ID
        """
        async with self._lock:
            self._task_counter += 1
            task_id = f"bg_{self._task_counter}_{datetime.now().strftime('%H%M%S')}"
            
            task = BackgroundTask(
                id=task_id,
                name=name,
                description=description,
                created_at=datetime.now().isoformat(),
                subtasks=subtasks or []
            )
            
            self._tasks[task_id] = task
            self._task_coroutines[task_id] = coroutine  # Store coroutine for later if queued
            
            # Check if we can start immediately
            running_count = sum(1 for t in self._tasks.values() if t.state == TaskState.RUNNING)
            
            if running_count < self._max_concurrent:
                # Start the task
                task_timeout = timedelta(minutes=timeout_minutes)
                asyncio_task = asyncio.create_task(
                    self._run_task(task_id, coroutine, task_timeout)
                )
                self._running_tasks[task_id] = asyncio_task
                task.state = TaskState.RUNNING
                task.started_at = datetime.now().isoformat()
                logging.info(f"🚀 Started background task: {name} ({task_id})")
            else:
                logging.info(f"📋 Queued background task: {name} ({task_id}) - {running_count} tasks already running")
            
            return task_id
    
    async def _run_task(
        self,
        task_id: str,
        coroutine: Callable[[BackgroundTask], Awaitable[Any]],
        timeout: timedelta = None
    ):
        """Run a task and handle completion"""
        task = self._tasks.get(task_id)
        if not task:
            return
        
        if timeout is None:
            timeout = self._task_timeout
        
        try:
            # Run with timeout
            result = await asyncio.wait_for(
                coroutine(task),
                timeout=timeout.total_seconds()
            )
            
            async with self._lock:
                task.state = TaskState.COMPLETED
                task.result = result
                task.progress = 1.0
                task.completed_at = datetime.now().isoformat()
                self._newly_completed.append(task_id)  # Mark for notification
                logging.info(f"✅ Background task completed: {task.name} ({task_id})")
            
            # Call completion callbacks
            for callback in self._completion_callbacks:
                try:
                    await callback(task)
                except Exception as e:
                    logging.error(f"Error in task completion callback: {e}")
                
        except asyncio.TimeoutError:
            async with self._lock:
                task.state = TaskState.FAILED
                task.error = f"Task timed out after {timeout.total_seconds()}s"
                task.completed_at = datetime.now().isoformat()
                self._newly_completed.append(task_id)  # Still notify on failure
                logging.error(f"⏰ Background task timed out: {task.name} ({task_id})")
                
        except asyncio.CancelledError:
            async with self._lock:
                task.state = TaskState.CANCELLED
                task.completed_at = datetime.now().isoformat()
                logging.info(f"🚫 Background task cancelled: {task.name} ({task_id})")
                
        except Exception as e:
            async with self._lock:
                task.state = TaskState.FAILED
                task.error = str(e)
                task.completed_at = datetime.now().isoformat()
                self._newly_completed.append(task_id)  # Still notify on failure
                logging.error(f"❌ Background task failed: {task.name} ({task_id}): {e}")
        
        finally:
            # Remove from running tasks and coroutines
            if task_id in self._running_tasks:
                del self._running_tasks[task_id]
            if task_id in self._task_coroutines:
                del self._task_coroutines[task_id]
            
            # Start next queued task
            await self._start_next_queued()
    
    async def _start_next_queued(self):
        """Start the next queued task if capacity available"""
        async with self._lock:
            running_count = sum(1 for t in self._tasks.values() if t.state == TaskState.RUNNING)
            
            if running_count >= self._max_concurrent:
                return
            
            # Find oldest pending task
            for task_id, task in self._tasks.items():
                if task.state == TaskState.PENDING:
                    # Get the stored coroutine
                    if task_id in self._task_coroutines:
                        coroutine = self._task_coroutines[task_id]
                        
                        # Start the task
                        asyncio_task = asyncio.create_task(
                            self._run_task(task_id, coroutine)
                        )
                        self._running_tasks[task_id] = asyncio_task
                        task.state = TaskState.RUNNING
                        task.started_at = datetime.now().isoformat()
                        logging.info(f"🚀 Started queued task: {task.name} ({task_id})")
                        break

    async def update_progress(
        self,
        task_id: str,
        progress: float,
        message: str = ""
    ):
        """Update task progress"""
        async with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.progress = min(1.0, max(0.0, progress))
                task.progress_message = message
                
                # Update subtask index based on progress
                if task.subtasks:
                    task.current_subtask = int(progress * len(task.subtasks))
    
    async def advance_subtask(self, task_id: str, message: str = ""):
        """Advance to next subtask"""
        async with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                if task.subtasks:
                    task.current_subtask = min(task.current_subtask + 1, len(task.subtasks))
                    task.progress = task.current_subtask / len(task.subtasks)
                    task.progress_message = message or task.subtasks[min(task.current_subtask, len(task.subtasks) - 1)]
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task"""
        async with self._lock:
            if task_id not in self._tasks:
                return None
            
            task = self._tasks[task_id]
            return {
                "id": task.id,
                "name": task.name,
                "description": task.description,
                "state": task.state.value,
                "progress": f"{task.progress * 100:.0f}%",
                "progress_message": task.progress_message,
                "current_subtask": task.subtasks[task.current_subtask] if task.subtasks and task.current_subtask < len(task.subtasks) else None,
                "subtasks_completed": f"{task.current_subtask}/{len(task.subtasks)}" if task.subtasks else "N/A",
                "result": str(task.result)[:200] if task.result else None,
                "error": task.error,
                "created_at": task.created_at,
                "started_at": task.started_at,
                "completed_at": task.completed_at
            }
    
    async def get_all_tasks_status(self) -> Dict[str, Any]:
        """Get status of all tasks"""
        async with self._lock:
            running = []
            pending = []
            completed = []
            failed = []
            
            for task in self._tasks.values():
                status = {
                    "id": task.id,
                    "name": task.name,
                    "progress": f"{task.progress * 100:.0f}%",
                    "message": task.progress_message
                }
                
                if task.state == TaskState.RUNNING:
                    running.append(status)
                elif task.state == TaskState.PENDING:
                    pending.append(status)
                elif task.state == TaskState.COMPLETED:
                    completed.append(status)
                elif task.state in [TaskState.FAILED, TaskState.CANCELLED]:
                    status["error"] = task.error
                    failed.append(status)
            
            return {
                "running": running,
                "pending": pending,
                "recently_completed": completed[-5:],  # Last 5
                "recently_failed": failed[-5:],
                "total_running": len(running),
                "total_pending": len(pending)
            }
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running or pending task"""
        async with self._lock:
            if task_id not in self._tasks:
                return False
            
            task = self._tasks[task_id]
            
            if task.state == TaskState.PENDING:
                task.state = TaskState.CANCELLED
                task.completed_at = datetime.now().isoformat()
                return True
            
            if task.state == TaskState.RUNNING and task_id in self._running_tasks:
                self._running_tasks[task_id].cancel()
                return True
            
            return False
    
    async def get_running_summary(self) -> str:
        """Get a human-readable summary of running tasks"""
        async with self._lock:
            running = [t for t in self._tasks.values() if t.state == TaskState.RUNNING]
            pending = [t for t in self._tasks.values() if t.state == TaskState.PENDING]
            
            if not running and not pending:
                return "No tasks running or pending."
            
            lines = []
            
            if running:
                lines.append(f"🔄 Running ({len(running)}):")
                for task in running:
                    progress = f"{task.progress * 100:.0f}%"
                    lines.append(f"  • {task.name}: {progress} - {task.progress_message or 'working...'}")
            
            if pending:
                lines.append(f"📋 Pending ({len(pending)}):")
                for task in pending[:3]:  # Show first 3
                    lines.append(f"  • {task.name}")
                if len(pending) > 3:
                    lines.append(f"  ... and {len(pending) - 3} more")
            
            return "\n".join(lines)
    
    async def format_completion_message(self, task: BackgroundTask) -> str:
        """Format a completion message for Sakura to speak"""
        duration = self._calculate_duration(task)
        
        if task.state == TaskState.COMPLETED:
            # Format result summary
            result_summary = ""
            if task.result:
                if isinstance(task.result, dict):
                    if 'message' in task.result:
                        result_summary = task.result['message']
                    elif 'data' in task.result:
                        data = task.result['data']
                        if isinstance(data, list):
                            result_summary = f"Found {len(data)} results"
                        else:
                            result_summary = str(data)[:100]
                elif isinstance(task.result, str):
                    result_summary = task.result[:100]
                else:
                    result_summary = str(task.result)[:100]
            
            if result_summary:
                return f"Hey! Your task '{task.name}' is done. It took {duration}. {result_summary}"
            else:
                return f"Hey! Your task '{task.name}' is complete. It took {duration}."
        
        elif task.state == TaskState.FAILED:
            return f"Sorry, the task '{task.name}' failed after {duration}. Error: {task.error or 'Unknown error'}"
        
        elif task.state == TaskState.CANCELLED:
            return f"The task '{task.name}' was cancelled."
        
        else:
            return f"Task '{task.name}' status: {task.state.value}"
    
    async def get_completion_announcements(self) -> List[str]:
        """Get formatted announcements for all newly completed tasks"""
        completed = await self.get_newly_completed_tasks()
        announcements = []
        
        for task_info in completed:
            task_id = task_info['id']
            if task_id in self._tasks:
                task = self._tasks[task_id]
                announcement = await self.format_completion_message(task)
                announcements.append(announcement)
        
        return announcements
    
    async def cleanup_old_tasks(self, max_age: timedelta = None):
        """Remove old completed/failed tasks"""
        if max_age is None:
            max_age = timedelta(hours=1)
        
        async with self._lock:
            now = datetime.now()
            to_remove = []
            
            for task_id, task in self._tasks.items():
                if task.state in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED]:
                    if task.completed_at:
                        completed = datetime.fromisoformat(task.completed_at)
                        if now - completed > max_age:
                            to_remove.append(task_id)
            
            for task_id in to_remove:
                del self._tasks[task_id]
            
            if to_remove:
                logging.info(f"Cleaned up {len(to_remove)} old background tasks")
    
    async def save_task_history(self, filepath: str = "background_tasks_history.json"):
        """Save completed task history to file"""
        async with self._lock:
            completed_tasks = [
                {
                    "id": task.id,
                    "name": task.name,
                    "description": task.description,
                    "state": task.state.value,
                    "result": str(task.result)[:500] if task.result else None,
                    "error": task.error,
                    "created_at": task.created_at,
                    "completed_at": task.completed_at
                }
                for task in self._tasks.values()
                if task.state in [TaskState.COMPLETED, TaskState.FAILED]
            ]
            
            data = {
                "saved_at": datetime.now().isoformat(),
                "tasks": completed_tasks[-50:]  # Keep last 50
            }
            
            async with aiofiles.open(filepath, 'w') as f:
                await f.write(json.dumps(data, indent=2))
            
            logging.info(f"Saved {len(completed_tasks)} task history entries")
    
    async def load_task_history(self, filepath: str = "background_tasks_history.json") -> List[Dict[str, Any]]:
        """Load task history from file"""
        try:
            async with aiofiles.open(filepath, 'r') as f:
                content = await f.read()
                data = json.loads(content)
                return data.get("tasks", [])
        except FileNotFoundError:
            return []
        except Exception as e:
            logging.warning(f"Could not load task history: {e}")
            return []
    
    async def cleanup(self):
        """Cancel all running tasks, save history, and cleanup"""
        async with self._lock:
            # Cancel all running tasks
            for task_id, asyncio_task in list(self._running_tasks.items()):
                asyncio_task.cancel()
            
            # Wait for cancellations
            if self._running_tasks:
                await asyncio.gather(*self._running_tasks.values(), return_exceptions=True)
            
            self._running_tasks.clear()
        
        # Save history outside lock to avoid deadlock
        await self.save_task_history()
        logging.info("Background task manager cleanup completed")
