"""
Task Chain Manager for Sakura
Enables multi-step task execution from single requests

Rules followed:
- All imports MUST be used
- Async with asyncio.Lock() for thread safety
- aiofiles for file I/O
"""
import asyncio
import logging
import re
from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import aiofiles


class TaskStatus(Enum):
    """Status of a task in the chain"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


@dataclass
class ChainTask:
    """Single task in a chain"""
    id: str
    tool_name: str
    action: str
    args: Dict[str, Any] = field(default_factory=dict)
    depends_on: Optional[str] = None  # ID of task this depends on
    result_mapping: Optional[Dict[str, str]] = None  # Map result fields to args
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class TaskChainResult:
    """Result of executing a task chain"""
    success: bool
    tasks_completed: int
    tasks_failed: int
    tasks_skipped: int
    results: List[Dict[str, Any]]
    error: Optional[str] = None
    total_time_ms: float = 0


class TaskChain:
    """Manages multi-step task execution"""
    
    # Patterns that indicate chained requests
    CHAIN_PATTERNS = [
        r'\band\s+then\b',
        r'\bafter\s+that\b',
        r'\bthen\b',
        r'\balso\b',
        r'\bfollowed\s+by\b',
        r'\bnext\b',
        r'\bfinally\b',
        r',\s*and\b',
        r';\s*',  # Semicolon as separator
    ]
    
    def __init__(self, tool_executor: Callable[[str, Dict[str, Any]], Awaitable[Any]]):
        """
        Initialize TaskChain
        
        Args:
            tool_executor: Async function to execute tools (tool_name, args) -> result
        """
        self.tool_executor = tool_executor
        self._lock = asyncio.Lock()
        self._tasks: List[ChainTask] = []
        self._execution_log: List[Dict[str, Any]] = []
        self._rollback_actions: List[Callable[[], Awaitable[None]]] = []
    
    def detect_chain(self, user_input: str) -> bool:
        """Detect if user input contains a chained request"""
        input_lower = user_input.lower()
        for pattern in self.CHAIN_PATTERNS:
            if re.search(pattern, input_lower):
                return True
        return False
    
    def parse_chain_request(self, user_input: str) -> List[str]:
        """
        Parse a chained request into individual steps
        
        Returns list of individual request strings
        """
        # Split by chain patterns
        parts = [user_input]
        
        for pattern in self.CHAIN_PATTERNS:
            new_parts = []
            for part in parts:
                split = re.split(pattern, part, flags=re.IGNORECASE)
                new_parts.extend([p.strip() for p in split if p.strip()])
            parts = new_parts
        
        return parts

    async def add_task(
        self,
        tool_name: str,
        action: str,
        args: Optional[Dict[str, Any]] = None,
        depends_on: Optional[str] = None,
        result_mapping: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Add a task to the chain
        
        Args:
            tool_name: Name of the tool to execute
            action: Action within the tool
            args: Arguments for the action
            depends_on: ID of task this depends on
            result_mapping: Map result fields from dependency to this task's args
                           e.g., {"file_path": "source"} maps dependency's file_path to this task's source arg
        
        Returns:
            Task ID
        """
        async with self._lock:
            task_id = f"task_{len(self._tasks)}_{datetime.now().strftime('%H%M%S%f')}"
            
            task = ChainTask(
                id=task_id,
                tool_name=tool_name,
                action=action,
                args=args or {},
                depends_on=depends_on,
                result_mapping=result_mapping
            )
            
            self._tasks.append(task)
            logging.info(f"Added task to chain: {task_id} - {tool_name}.{action}")
            
            return task_id
    
    async def execute_chain(self, stop_on_failure: bool = True) -> TaskChainResult:
        """
        Execute all tasks in the chain
        
        Args:
            stop_on_failure: If True, stop chain on first failure
        
        Returns:
            TaskChainResult with execution summary
        """
        async with self._lock:
            start_time = datetime.now()
            completed = 0
            failed = 0
            skipped = 0
            results = []
            
            for task in self._tasks:
                # Check if dependency failed
                if task.depends_on:
                    dep_task = self._get_task_by_id(task.depends_on)
                    if dep_task and dep_task.status == TaskStatus.FAILED:
                        task.status = TaskStatus.SKIPPED
                        skipped += 1
                        results.append({
                            "task_id": task.id,
                            "status": "skipped",
                            "reason": f"Dependency {task.depends_on} failed"
                        })
                        continue
                    
                    # Apply result mapping from dependency
                    if dep_task and dep_task.result and task.result_mapping:
                        task.args = self._apply_result_mapping(
                            task.args, 
                            dep_task.result, 
                            task.result_mapping
                        )
                
                # Execute task
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now().isoformat()
                
                try:
                    # Build full args with action
                    full_args = {"action": task.action, **task.args}
                    
                    # Execute via tool executor
                    result = await self.tool_executor(task.tool_name, full_args)
                    
                    task.completed_at = datetime.now().isoformat()
                    
                    # Check result status
                    if hasattr(result, 'status'):
                        if result.status.value == "success":
                            task.status = TaskStatus.COMPLETED
                            task.result = result.data if hasattr(result, 'data') else result
                            completed += 1
                            results.append({
                                "task_id": task.id,
                                "status": "completed",
                                "result": str(task.result)[:200]
                            })
                        else:
                            task.status = TaskStatus.FAILED
                            task.error = result.error if hasattr(result, 'error') else str(result)
                            failed += 1
                            results.append({
                                "task_id": task.id,
                                "status": "failed",
                                "error": task.error
                            })
                            
                            if stop_on_failure:
                                break
                    else:
                        # Assume success if no status
                        task.status = TaskStatus.COMPLETED
                        task.result = result
                        completed += 1
                        results.append({
                            "task_id": task.id,
                            "status": "completed",
                            "result": str(result)[:200]
                        })
                        
                except Exception as e:
                    task.completed_at = datetime.now().isoformat()
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    failed += 1
                    results.append({
                        "task_id": task.id,
                        "status": "failed",
                        "error": str(e)
                    })
                    logging.error(f"Task {task.id} failed: {e}")
                    
                    if stop_on_failure:
                        break
            
            # Mark remaining tasks as skipped
            for task in self._tasks:
                if task.status == TaskStatus.PENDING:
                    task.status = TaskStatus.SKIPPED
                    skipped += 1
                    results.append({
                        "task_id": task.id,
                        "status": "skipped",
                        "reason": "Chain stopped before this task"
                    })
            
            end_time = datetime.now()
            total_time = (end_time - start_time).total_seconds() * 1000
            
            # Log execution
            self._execution_log.append({
                "timestamp": start_time.isoformat(),
                "tasks": len(self._tasks),
                "completed": completed,
                "failed": failed,
                "skipped": skipped,
                "time_ms": total_time
            })
            
            return TaskChainResult(
                success=failed == 0,
                tasks_completed=completed,
                tasks_failed=failed,
                tasks_skipped=skipped,
                results=results,
                error=self._tasks[-1].error if failed > 0 and self._tasks else None,
                total_time_ms=total_time
            )
    
    def _get_task_by_id(self, task_id: str) -> Optional[ChainTask]:
        """Get task by ID"""
        for task in self._tasks:
            if task.id == task_id:
                return task
        return None
    
    def _apply_result_mapping(
        self, 
        args: Dict[str, Any], 
        result: Any, 
        mapping: Dict[str, str]
    ) -> Dict[str, Any]:
        """Apply result mapping from dependency to task args"""
        new_args = args.copy()
        
        for result_key, arg_key in mapping.items():
            if isinstance(result, dict) and result_key in result:
                new_args[arg_key] = result[result_key]
            elif hasattr(result, result_key):
                new_args[arg_key] = getattr(result, result_key)
            elif isinstance(result, (str, int, float, bool)):
                # If result is simple type, use it directly
                new_args[arg_key] = result
        
        return new_args
    
    async def clear(self):
        """Clear all tasks from the chain"""
        async with self._lock:
            self._tasks.clear()
            self._rollback_actions.clear()
    
    async def get_chain_status(self) -> Dict[str, Any]:
        """Get current chain status"""
        async with self._lock:
            return {
                "total_tasks": len(self._tasks),
                "pending": sum(1 for t in self._tasks if t.status == TaskStatus.PENDING),
                "running": sum(1 for t in self._tasks if t.status == TaskStatus.RUNNING),
                "completed": sum(1 for t in self._tasks if t.status == TaskStatus.COMPLETED),
                "failed": sum(1 for t in self._tasks if t.status == TaskStatus.FAILED),
                "skipped": sum(1 for t in self._tasks if t.status == TaskStatus.SKIPPED),
                "tasks": [
                    {
                        "id": t.id,
                        "tool": t.tool_name,
                        "action": t.action,
                        "status": t.status.value,
                        "depends_on": t.depends_on
                    }
                    for t in self._tasks
                ]
            }
    
    async def save_chain(self, filepath: str):
        """Save chain to file for later execution"""
        async with self._lock:
            data = {
                "created": datetime.now().isoformat(),
                "tasks": [
                    {
                        "id": t.id,
                        "tool_name": t.tool_name,
                        "action": t.action,
                        "args": t.args,
                        "depends_on": t.depends_on,
                        "result_mapping": t.result_mapping
                    }
                    for t in self._tasks
                ]
            }
            async with aiofiles.open(filepath, 'w') as f:
                await f.write(json.dumps(data, indent=2))
    
    async def load_chain(self, filepath: str):
        """Load chain from file"""
        async with self._lock:
            async with aiofiles.open(filepath, 'r') as f:
                content = await f.read()
                data = json.loads(content)
            
            self._tasks.clear()
            for task_data in data.get("tasks", []):
                task = ChainTask(
                    id=task_data["id"],
                    tool_name=task_data["tool_name"],
                    action=task_data["action"],
                    args=task_data.get("args", {}),
                    depends_on=task_data.get("depends_on"),
                    result_mapping=task_data.get("result_mapping")
                )
                self._tasks.append(task)


class TaskChainBuilder:
    """Helper class to build task chains fluently"""
    
    def __init__(self, chain: TaskChain):
        self.chain = chain
        self._last_task_id: Optional[str] = None
    
    async def then(
        self,
        tool_name: str,
        action: str,
        args: Optional[Dict[str, Any]] = None,
        use_previous_result: Optional[Dict[str, str]] = None
    ) -> 'TaskChainBuilder':
        """
        Add a task that depends on the previous one
        
        Args:
            tool_name: Tool to execute
            action: Action within tool
            args: Arguments for action
            use_previous_result: Map previous result fields to this task's args
        """
        task_id = await self.chain.add_task(
            tool_name=tool_name,
            action=action,
            args=args,
            depends_on=self._last_task_id,
            result_mapping=use_previous_result
        )
        self._last_task_id = task_id
        return self
    
    async def parallel(
        self,
        tasks: List[Dict[str, Any]]
    ) -> 'TaskChainBuilder':
        """
        Add multiple tasks that can run in parallel (no dependencies)
        
        Args:
            tasks: List of task definitions with tool_name, action, args
        """
        for task_def in tasks:
            await self.chain.add_task(
                tool_name=task_def["tool_name"],
                action=task_def["action"],
                args=task_def.get("args", {})
            )
        return self
    
    async def execute(self, stop_on_failure: bool = True) -> TaskChainResult:
        """Execute the built chain"""
        return await self.chain.execute_chain(stop_on_failure)
