"""
Productivity Tools for Sakura
Reminders, alarms, timers, notes, and to-do lists
"""

from enum import Enum
from .manager import ProductivityManager


class ProductivityActions(Enum):
    """Available productivity tool actions"""
    # Reminders & Alarms
    SET_REMINDER = "set_reminder"
    LIST_REMINDERS = "list_reminders"
    CANCEL_REMINDER = "cancel_reminder"
    SNOOZE_REMINDER = "snooze_reminder"
    
    # Timers
    START_TIMER = "start_timer"
    STOP_TIMER = "stop_timer"
    LIST_TIMERS = "list_timers"
    GET_TIMER_STATUS = "get_timer_status"
    
    # Stopwatch
    START_STOPWATCH = "start_stopwatch"
    STOP_STOPWATCH = "stop_stopwatch"
    
    # Notes
    CREATE_NOTE = "create_note"
    GET_NOTE = "get_note"
    UPDATE_NOTE = "update_note"
    DELETE_NOTE = "delete_note"
    LIST_NOTES = "list_notes"
    SEARCH_NOTES = "search_notes"
    SEARCH_NOTES_FTS = "search_notes_fts"
    
    # To-Do Lists
    ADD_TODO = "add_todo"
    COMPLETE_TODO = "complete_todo"
    UPDATE_TODO = "update_todo"
    DELETE_TODO = "delete_todo"
    LIST_TODOS = "list_todos"
    SEARCH_TODOS = "search_todos"
    SEARCH_TODOS_FTS = "search_todos_fts"
    GET_COMPLETED_HISTORY = "get_completed_history"
    
    # Notifications
    OPEN_ALARMS_APP = "open_alarms_app"
    SHOW_NOTIFICATION = "show_notification"


__all__ = ['ProductivityManager', 'ProductivityActions']
