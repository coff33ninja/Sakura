# Task Chain Module

**File:** `modules/task_chain.py`

Enables multi-step task execution from single requests.

## Features

- Parse multi-step requests ("do X and then Y")
- Queue of actions with dependency tracking
- Pass results between steps
- Skip dependent tasks on failure
- Rollback support

## Chain Patterns

Detects these patterns in user input:
- "and then"
- "after that"
- "then"
- "also"
- "followed by"
- "next"
- "finally"
- Semicolons (;)

## Classes

### TaskStatus
```python
class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"
```

### ChainTask
```python
@dataclass
class ChainTask:
    id: str
    tool_name: str
    action: str
    args: Dict[str, Any]
    depends_on: Optional[str]  # Task ID this depends on
    result_mapping: Dict[str, str]  # Map result fields to args
    status: TaskStatus
    result: Any
    error: Optional[str]
```

### TaskChainResult
```python
@dataclass
class TaskChainResult:
    success: bool
    tasks_completed: int
    tasks_failed: int
    tasks_skipped: int
    results: List[Dict]
    total_time_ms: float
```

## Usage

```python
chain = TaskChain(tool_executor=execute_tool)
await chain.initialize()

# Add tasks
chain.add_task("windows", "search_files", {"pattern": "*.py"})
chain.add_task("windows", "create_script", 
    {"content": "backup script"},
    depends_on="task_0",
    result_mapping={"files": "file_list"}
)

# Execute chain
result = await chain.execute()
```

## Example Chains

- "Find my Python files and create a backup script"
  → search_files → create_script
  
- "Open Chrome and go to YouTube"
  → open_app → (navigate)
  
- "Turn off the lights and play relaxing music"
  → smart_home(lights_off) → smart_home(play_music)
