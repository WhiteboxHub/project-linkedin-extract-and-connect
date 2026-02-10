# logging_config/enrichment.py
"""
Log enrichment utilities for adding context to logs.
"""

import logging
import threading
from typing import Optional, Dict, Any
from contextvars import ContextVar

# Thread-safe context storage
_log_context: ContextVar[Dict[str, Any]] = ContextVar('log_context', default={})


class LogContext:
    """Context manager for enriching logs with additional data."""
    
    def __init__(self, **kwargs):
        """
        Initialize log context.
        
        Args:
            **kwargs: Context fields (job_id, employee_id, step, etc.)
        """
        self.context = kwargs
        self.token = None
    
    def __enter__(self):
        """Enter context - save current context and set new one."""
        current = _log_context.get()
        # Merge with existing context
        new_context = {**current, **self.context}
        self.token = _log_context.set(new_context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - restore previous context."""
        if self.token:
            _log_context.reset(self.token)
    
    @staticmethod
    def get() -> Dict[str, Any]:
        """Get current log context."""
        return _log_context.get().copy()
    
    @staticmethod
    def set(**kwargs):
        """Set log context fields."""
        current = _log_context.get()
        new_context = {**current, **kwargs}
        _log_context.set(new_context)
    
    @staticmethod
    def clear():
        """Clear all context."""
        _log_context.set({})


class ContextEnrichmentFilter(logging.Filter):
    """Logging filter that adds context to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add context fields to log record.
        
        Args:
            record: Log record to enrich
            
        Returns:
            True (always pass through)
        """
        context = LogContext.get()
        
        # Add context fields to record
        for key, value in context.items():
            setattr(record, key, value)
        
        # Ensure all expected fields exist (even if None)
        expected_fields = [
            'job_id', 'employee_id', 'candidate_id', 
            'step', 'username', 'exception_type'
        ]
        for field in expected_fields:
            if not hasattr(record, field):
                setattr(record, field, None)
        
        return True


def enrich_log(logger: logging.Logger, **context):
    """
    Decorator to enrich logs with context.
    
    Usage:
        @enrich_log(logger, step="LOGIN", username="user@example.com")
        def login():
            logger.info("Logging in...")
    
    Args:
        logger: Logger instance
        **context: Context fields to add
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            with LogContext(**context):
                return func(*args, **kwargs)
        return wrapper
    return decorator
