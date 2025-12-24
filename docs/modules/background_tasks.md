# Background Tasks Module

**File:** `modules/background_tasks.py`

Execute tasks in background while keeping voice connection alive.

## Features

- Non-blocking task execution
- Task queue with progress tracking
- Subtask support
- Automatic timeout and cleanup
- Task history persistence

## Task States

```python
class TaskState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

## Background Task

```python
@dataclass
class BackgroundTask:
    id: str
    name: str
    description: str
    state: TaskState
    progress: float          # 0.0 to 1.0
    progress_message: str
    result: Any
    error: Optional[str]
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    subtasks: List[str]
    current_subtask: int
```

## Configuration

- Max concurrent tasks: 3
- Default timeout: 5 minutes

## Usage

```python
manager = BackgroundTaskManager()

# Submit task
task_id = await manager.submit_task(
    name="File Search",
    description="Searching all drives for Python files",
    coroutine=search_files("*.py")
)

# Check progress
task = await manager.get_task(task_id)
print(f"Progress: {task.progress * 100}%")
print(f"Status: {task.state}")

# Update progress from within task
await manager.update_progress(
    task_id,
    progress=0.5,
    message="Searched 50% of drives"
)

# Cancel task
await manager.cancel_task(task_id)

# List all tasks
tasks = await manager.list_tasks()
```

## Voice Integration

Background tasks allow long operations without blocking voice:

1. User: "Search all drives for Python files"
2. Sakura: "I'll search in the background. You can keep talking."
3. Task runs asynchronously
4. Sakura: "Found 150 Python files. Want me to list them?"

## Task History

Completed tasks are persisted for reference:
- Task name and description
- Start/end times
- Result or error
- Duration
