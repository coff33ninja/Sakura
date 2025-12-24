"""
Error Recovery Manager for Sakura
Intelligent error handling with retry strategies and user feedback

Rules followed:
- All imports MUST be used
- Async with asyncio.Lock() for thread safety
- aiofiles for file I/O
"""
import asyncio
import logging
import random
import re
from typing import Dict, Any, List, Optional, Callable, Awaitable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import aiofiles


class ErrorCategory(Enum):
    """Categories of errors with different recovery strategies"""
    TRANSIENT = "transient"      # Retry automatically (network, timeout)
    PERMISSION = "permission"    # Ask user for permission/elevation
    NOT_FOUND = "not_found"      # Resource not found, search alternatives
    RATE_LIMIT = "rate_limit"    # Wait and retry, rotate resources
    INVALID_INPUT = "invalid"    # Clarify with user
    PERMANENT = "permanent"      # Give up gracefully
    UNKNOWN = "unknown"          # Uncategorized error


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_retries: int = 3
    base_delay_ms: int = 1000
    max_delay_ms: int = 30000
    exponential_base: float = 2.0
    jitter: bool = True


@dataclass
class RecoveryResult:
    """Result of a recovery attempt"""
    success: bool
    action_taken: str
    result: Any = None
    error: Optional[str] = None
    retries_used: int = 0
    total_time_ms: float = 0
    suggestion: Optional[str] = None
    alternatives: List[str] = field(default_factory=list)


@dataclass
class ErrorRecord:
    """Record of an error for learning"""
    timestamp: str
    tool_name: str
    action: str
    error_message: str
    category: ErrorCategory
    recovery_attempted: bool
    recovery_success: bool
    user_resolution: Optional[str] = None
    tags: List[str] = field(default_factory=list)


class ErrorRecovery:
    """Manages error recovery with intelligent retry and user feedback"""
    
    # Patterns to categorize errors
    ERROR_PATTERNS = {
        ErrorCategory.TRANSIENT: [
            r'timeout', r'timed?\s*out', r'connection\s*(refused|reset|error)',
            r'network', r'unreachable', r'temporarily\s*unavailable',
            r'503', r'502', r'504', r'ETIMEDOUT', r'ECONNRESET'
        ],
        ErrorCategory.PERMISSION: [
            r'permission\s*denied', r'access\s*denied', r'unauthorized',
            r'forbidden', r'403', r'401', r'elevation\s*required',
            r'admin', r'privilege', r'not\s*allowed'
        ],
        ErrorCategory.NOT_FOUND: [
            r'not\s*found', r'no\s*such\s*file', r'does\s*not\s*exist',
            r'404', r'missing', r'cannot\s*find', r'path.*invalid',
            r'FileNotFoundError', r'ENOENT'
        ],
        ErrorCategory.RATE_LIMIT: [
            r'rate\s*limit', r'quota', r'too\s*many\s*requests',
            r'429', r'throttl', r'exceeded', r'resource_exhausted'
        ],
        ErrorCategory.INVALID_INPUT: [
            r'invalid\s*(argument|parameter|input|value)',
            r'bad\s*request', r'400', r'malformed', r'syntax\s*error',
            r'type\s*error', r'value\s*error', r'missing\s*required'
        ],
        ErrorCategory.PERMANENT: [
            r'not\s*supported', r'deprecated', r'removed',
            r'incompatible', r'fatal', r'unrecoverable'
        ]
    }
    
    # Default retry configs per category
    DEFAULT_RETRY_CONFIGS = {
        ErrorCategory.TRANSIENT: RetryConfig(max_retries=3, base_delay_ms=1000),
        ErrorCategory.RATE_LIMIT: RetryConfig(max_retries=5, base_delay_ms=5000, max_delay_ms=60000),
        ErrorCategory.NOT_FOUND: RetryConfig(max_retries=1, base_delay_ms=500),
        ErrorCategory.PERMISSION: RetryConfig(max_retries=0),  # Don't auto-retry
        ErrorCategory.INVALID_INPUT: RetryConfig(max_retries=0),  # Don't auto-retry
        ErrorCategory.PERMANENT: RetryConfig(max_retries=0),  # Never retry
        ErrorCategory.UNKNOWN: RetryConfig(max_retries=1, base_delay_ms=2000)
    }

    def __init__(self, error_log_file: str = "error_recovery_log.json"):
        self.error_log_file = error_log_file
        self._lock = asyncio.Lock()
        self._error_history: List[ErrorRecord] = []
        self._retry_configs: Dict[ErrorCategory, RetryConfig] = self.DEFAULT_RETRY_CONFIGS.copy()
        self._alternative_handlers: Dict[str, Callable] = {}
        self._cooldown_until: Dict[str, datetime] = {}  # Tool cooldowns after repeated failures
        self._error_cooldown = timedelta(minutes=5)  # Cooldown period for repeated errors
    
    async def initialize(self) -> bool:
        """Initialize error recovery, load history"""
        async with self._lock:
            try:
                await self._load_error_history()
                logging.info(f"Error recovery initialized with {len(self._error_history)} historical errors")
                return True
            except Exception as e:
                logging.warning(f"Could not load error history: {e}")
                return True  # Still return True, start fresh
    
    def categorize_error(self, error_message: str) -> ErrorCategory:
        """Categorize an error based on its message"""
        error_lower = error_message.lower()
        
        for category, patterns in self.ERROR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, error_lower):
                    return category
        
        return ErrorCategory.UNKNOWN
    
    async def is_on_cooldown(self, tool_name: str, action: str) -> bool:
        """Check if a tool/action is on cooldown due to repeated failures"""
        async with self._lock:
            key = f"{tool_name}.{action}"
            if key in self._cooldown_until:
                if datetime.now() < self._cooldown_until[key]:
                    remaining = self._cooldown_until[key] - datetime.now()
                    logging.info(f"{key} is on cooldown for {remaining.seconds}s more")
                    return True
                else:
                    # Cooldown expired, remove it
                    del self._cooldown_until[key]
            return False
    
    async def set_cooldown(self, tool_name: str, action: str, duration: Optional[timedelta] = None):
        """Set a cooldown for a tool/action after repeated failures"""
        async with self._lock:
            key = f"{tool_name}.{action}"
            cooldown = duration or self._error_cooldown
            self._cooldown_until[key] = datetime.now() + cooldown
            logging.info(f"Set cooldown for {key}: {cooldown.seconds}s")
    
    async def get_recent_errors(self, tool_name: str, within: timedelta = None) -> List[ErrorRecord]:
        """Get recent errors for a tool within a time window"""
        async with self._lock:
            window = within or timedelta(hours=1)
            cutoff = datetime.now() - window
            
            recent = []
            for record in self._error_history:
                try:
                    error_time = datetime.fromisoformat(record.timestamp)
                    if error_time > cutoff and record.tool_name == tool_name:
                        recent.append(record)
                except (ValueError, TypeError):
                    continue
            
            return recent
    
    async def should_skip_retry(self, tool_name: str, action: str) -> Tuple[bool, Optional[str]]:
        """Check if we should skip retrying based on recent failure patterns"""
        # Check cooldown first
        if await self.is_on_cooldown(tool_name, action):
            return True, "Tool is on cooldown due to repeated failures"
        
        # Check for repeated recent failures (3+ in last 10 minutes)
        recent = await self.get_recent_errors(tool_name, timedelta(minutes=10))
        action_failures = [r for r in recent if r.action == action and not r.recovery_success]
        
        if len(action_failures) >= 3:
            await self.set_cooldown(tool_name, action)
            return True, f"Too many recent failures ({len(action_failures)} in 10 min), cooling down"
        
        return False, None
    
    async def attempt_recovery(
        self,
        tool_name: str,
        action: str,
        args: Dict[str, Any],
        error_message: str,
        executor: Callable[[str, Dict[str, Any]], Awaitable[Any]],
        category: Optional[ErrorCategory] = None
    ) -> RecoveryResult:
        """
        Attempt to recover from an error
        
        Args:
            tool_name: Name of the tool that failed
            action: Action that failed
            args: Original arguments
            error_message: The error message
            executor: Function to retry the action
            category: Optional pre-categorized error
        
        Returns:
            RecoveryResult with outcome
        """
        start_time = datetime.now()
        
        # Check if we should skip due to cooldown or repeated failures
        should_skip, skip_reason = await self.should_skip_retry(tool_name, action)
        if should_skip:
            return RecoveryResult(
                success=False,
                action_taken="skipped_cooldown",
                error=error_message,
                suggestion=skip_reason
            )
        
        # Categorize if not provided
        if category is None:
            category = self.categorize_error(error_message)
        
        logging.info(f"Error categorized as {category.value}: {error_message[:100]}")
        
        # Get retry config for this category
        config = self._retry_configs.get(category, RetryConfig(max_retries=0))
        
        # Record the error with tags based on category
        error_tags = [category.value, tool_name]
        if 'path' in args or 'file' in args:
            error_tags.append("filesystem")
        if 'url' in args:
            error_tags.append("network")
        
        error_record = ErrorRecord(
            timestamp=datetime.now().isoformat(),
            tool_name=tool_name,
            action=action,
            error_message=error_message,
            category=category,
            recovery_attempted=config.max_retries > 0,
            recovery_success=False,
            tags=error_tags
        )
        
        # Handle based on category
        if category == ErrorCategory.PERMANENT:
            return RecoveryResult(
                success=False,
                action_taken="gave_up",
                error=error_message,
                suggestion=self._get_permanent_error_suggestion(tool_name, action, error_message)
            )
        
        if category == ErrorCategory.PERMISSION:
            return RecoveryResult(
                success=False,
                action_taken="needs_permission",
                error=error_message,
                suggestion=self._get_permission_suggestion(tool_name, action)
            )
        
        if category == ErrorCategory.INVALID_INPUT:
            return RecoveryResult(
                success=False,
                action_taken="needs_clarification",
                error=error_message,
                suggestion=self._get_input_suggestion(tool_name, action, args, error_message)
            )
        
        if category == ErrorCategory.NOT_FOUND:
            # Try to find alternatives
            alternative = await self._find_alternative(tool_name, action, args, error_message)
            if alternative:
                return RecoveryResult(
                    success=False,
                    action_taken="found_alternative",
                    suggestion=alternative
                )
        
        # Attempt retries for transient/rate-limit errors
        if config.max_retries > 0:
            result = await self._retry_with_backoff(
                tool_name, action, args, executor, config
            )
            
            error_record.recovery_success = result.success
            await self._record_error(error_record)
            
            end_time = datetime.now()
            result.total_time_ms = (end_time - start_time).total_seconds() * 1000
            
            return result
        
        # No recovery possible
        await self._record_error(error_record)
        
        return RecoveryResult(
            success=False,
            action_taken="no_recovery",
            error=error_message,
            suggestion=self._get_generic_suggestion(category)
        )
    
    async def _retry_with_backoff(
        self,
        tool_name: str,
        action: str,
        args: Dict[str, Any],
        executor: Callable[[str, Dict[str, Any]], Awaitable[Any]],
        config: RetryConfig
    ) -> RecoveryResult:
        """Retry an action with exponential backoff"""
        last_error = None
        
        for attempt in range(config.max_retries):
            # Calculate delay with exponential backoff
            delay_ms = min(
                config.base_delay_ms * (config.exponential_base ** attempt),
                config.max_delay_ms
            )
            
            # Add jitter if enabled
            if config.jitter:
                delay_ms = delay_ms * (0.5 + random.random())
            
            logging.info(f"Retry {attempt + 1}/{config.max_retries} for {tool_name}.{action} after {delay_ms:.0f}ms")
            
            await asyncio.sleep(delay_ms / 1000)
            
            try:
                # Rebuild args with action
                full_args = {"action": action, **args}
                result = await executor(tool_name, full_args)
                
                # Check if successful
                if hasattr(result, 'status'):
                    if result.status.value == "success":
                        return RecoveryResult(
                            success=True,
                            action_taken="retry_succeeded",
                            result=result.data if hasattr(result, 'data') else result,
                            retries_used=attempt + 1
                        )
                    else:
                        last_error = result.error if hasattr(result, 'error') else str(result)
                else:
                    # Assume success if no status
                    return RecoveryResult(
                        success=True,
                        action_taken="retry_succeeded",
                        result=result,
                        retries_used=attempt + 1
                    )
                    
            except Exception as e:
                last_error = str(e)
                logging.warning(f"Retry {attempt + 1} failed: {e}")
        
        return RecoveryResult(
            success=False,
            action_taken="retries_exhausted",
            error=last_error,
            retries_used=config.max_retries,
            suggestion=f"Failed after {config.max_retries} retries. The service may be down."
        )
    
    async def _find_alternative(
        self,
        tool_name: str,
        action: str,
        args: Dict[str, Any],
        error_message: str
    ) -> Optional[str]:
        """Try to find an alternative when resource not found"""
        suggestions = []
        
        # File/path not found suggestions
        if 'path' in args or 'file' in args or 'directory' in args:
            path = args.get('path') or args.get('file_path') or args.get('directory', '')
            suggestions.append(f"The path '{path}' was not found.")
            suggestions.append("Would you like me to:")
            suggestions.append("1. Search for similar files?")
            suggestions.append("2. Check if the path has a typo?")
            suggestions.append("3. Look in common locations?")
        
        # App not found suggestions
        if action in ['open_app', 'find_app_path'] and 'app' in args:
            app = args.get('app', '')
            suggestions.append(f"Could not find '{app}'.")
            suggestions.append("Would you like me to:")
            suggestions.append("1. Search installed applications?")
            suggestions.append("2. Try a different app name?")
        
        if suggestions:
            return "\n".join(suggestions)
        
        return None
    
    def _get_permission_suggestion(self, tool_name: str, action: str) -> str:
        """Get suggestion for permission errors"""
        suggestions = [
            f"Permission denied for {tool_name}.{action}.",
            "This might require:",
            "1. Running as Administrator",
            "2. Checking file/folder permissions",
            "3. Closing programs that might be using the resource"
        ]
        return "\n".join(suggestions)
    
    def _get_input_suggestion(
        self, 
        tool_name: str, 
        action: str, 
        args: Dict[str, Any],
        error_message: str
    ) -> str:
        """Get suggestion for invalid input errors"""
        suggestions = [f"Invalid input for {tool_name}.{action}."]
        
        # Try to identify which argument is problematic
        if 'argument' in error_message.lower() or 'parameter' in error_message.lower():
            suggestions.append("Please check the arguments provided.")
        
        suggestions.append(f"Current arguments: {json.dumps(args, default=str)[:200]}")
        suggestions.append("Could you clarify what you'd like me to do?")
        
        return "\n".join(suggestions)
    
    def _get_permanent_error_suggestion(
        self,
        tool_name: str,
        action: str,
        error_message: str
    ) -> str:
        """Get suggestion for permanent errors"""
        return f"This action ({tool_name}.{action}) cannot be completed: {error_message[:100]}"
    
    def _get_generic_suggestion(self, category: ErrorCategory) -> str:
        """Get generic suggestion based on category"""
        suggestions = {
            ErrorCategory.TRANSIENT: "The service seems temporarily unavailable. Try again in a moment.",
            ErrorCategory.RATE_LIMIT: "We've hit a rate limit. Please wait a moment before trying again.",
            ErrorCategory.UNKNOWN: "An unexpected error occurred. Please try again or rephrase your request."
        }
        return suggestions.get(category, "Something went wrong. Please try again.")

    async def record_user_resolution(self, error_message: str, resolution: str):
        """Record how user resolved an error for learning"""
        async with self._lock:
            # Find matching recent error
            for record in reversed(self._error_history[-20:]):
                if error_message in record.error_message:
                    record.user_resolution = resolution
                    await self._save_error_history()
                    logging.info(f"Recorded user resolution: {resolution[:50]}")
                    break
    
    async def get_similar_error_resolutions(self, error_message: str) -> List[str]:
        """Get resolutions from similar past errors"""
        async with self._lock:
            resolutions = []
            error_lower = error_message.lower()
            
            for record in self._error_history:
                if record.user_resolution:
                    # Check for similar error patterns
                    if any(word in record.error_message.lower() 
                           for word in error_lower.split()[:5]):
                        resolutions.append(record.user_resolution)
            
            return list(set(resolutions))[-3:]  # Return up to 3 unique resolutions
    
    async def get_error_stats(self) -> Dict[str, Any]:
        """Get statistics about errors"""
        async with self._lock:
            if not self._error_history:
                return {"total_errors": 0}
            
            category_counts = {}
            recovery_success = 0
            recovery_attempted = 0
            
            for record in self._error_history:
                cat = record.category.value
                category_counts[cat] = category_counts.get(cat, 0) + 1
                
                if record.recovery_attempted:
                    recovery_attempted += 1
                    if record.recovery_success:
                        recovery_success += 1
            
            return {
                "total_errors": len(self._error_history),
                "by_category": category_counts,
                "recovery_attempted": recovery_attempted,
                "recovery_success": recovery_success,
                "recovery_rate": f"{(recovery_success/recovery_attempted*100):.1f}%" if recovery_attempted > 0 else "N/A"
            }
    
    async def set_retry_config(self, category: ErrorCategory, config: RetryConfig):
        """Set custom retry config for a category"""
        async with self._lock:
            self._retry_configs[category] = config
    
    async def _record_error(self, record: ErrorRecord):
        """Record an error to history"""
        async with self._lock:
            self._error_history.append(record)
            
            # Keep only last 100 errors
            if len(self._error_history) > 100:
                self._error_history = self._error_history[-100:]
            
            # Save periodically
            if len(self._error_history) % 10 == 0:
                await self._save_error_history()
    
    async def _save_error_history(self):
        """Save error history to file"""
        try:
            data = {
                "last_updated": datetime.now().isoformat(),
                "errors": [
                    {
                        "timestamp": r.timestamp,
                        "tool_name": r.tool_name,
                        "action": r.action,
                        "error_message": r.error_message[:500],  # Truncate long messages
                        "category": r.category.value,
                        "recovery_attempted": r.recovery_attempted,
                        "recovery_success": r.recovery_success,
                        "user_resolution": r.user_resolution
                    }
                    for r in self._error_history[-50:]  # Save last 50
                ]
            }
            async with aiofiles.open(self.error_log_file, 'w') as f:
                await f.write(json.dumps(data, indent=2))
        except Exception as e:
            logging.error(f"Failed to save error history: {e}")
    
    async def _load_error_history(self):
        """Load error history from file"""
        try:
            async with aiofiles.open(self.error_log_file, 'r') as f:
                content = await f.read()
                data = json.loads(content)
            
            for error_data in data.get("errors", []):
                record = ErrorRecord(
                    timestamp=error_data["timestamp"],
                    tool_name=error_data["tool_name"],
                    action=error_data["action"],
                    error_message=error_data["error_message"],
                    category=ErrorCategory(error_data["category"]),
                    recovery_attempted=error_data["recovery_attempted"],
                    recovery_success=error_data["recovery_success"],
                    user_resolution=error_data.get("user_resolution")
                )
                self._error_history.append(record)
                
        except FileNotFoundError:
            pass  # No history yet
        except Exception as e:
            logging.warning(f"Error loading error history: {e}")
    
    async def cleanup(self):
        """Save history before shutdown"""
        async with self._lock:
            await self._save_error_history()
            logging.info("Error recovery history saved")


def categorize_tool_error(error_message: str) -> Tuple[ErrorCategory, str]:
    """
    Utility function to categorize an error and get a user-friendly message
    
    Returns:
        Tuple of (ErrorCategory, user_friendly_message)
    """
    recovery = ErrorRecovery()
    category = recovery.categorize_error(error_message)
    
    friendly_messages = {
        ErrorCategory.TRANSIENT: "Temporary issue - will retry automatically",
        ErrorCategory.PERMISSION: "Permission denied - may need admin rights",
        ErrorCategory.NOT_FOUND: "Resource not found - checking alternatives",
        ErrorCategory.RATE_LIMIT: "Rate limited - waiting before retry",
        ErrorCategory.INVALID_INPUT: "Invalid input - please clarify",
        ErrorCategory.PERMANENT: "Cannot complete this action",
        ErrorCategory.UNKNOWN: "Unexpected error occurred"
    }
    
    return category, friendly_messages.get(category, "Error occurred")
