# logging_config/formatters.py
"""
Custom log formatters for console and file output.
"""

import logging
import json
from typing import Optional
from datetime import datetime
from .schema import LogRecord, classify_exception


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging to files."""
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON string
        """
        # Create structured log record
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add enrichment fields if present
        enrichment_fields = [
            'job_id', 'employee_id', 'candidate_id',
            'step', 'username', 'exception_type'
        ]
        for field in enrichment_fields:
            if hasattr(record, field) and getattr(record, field) is not None:
                log_data[field] = getattr(record, field)
        
        # Add exception info if present
        if record.exc_info:
            exc_type, exc_value, exc_tb = record.exc_info
            if exc_type:
                log_data['exception_type'] = classify_exception(exc_value)
                log_data['exception_message'] = str(exc_value)
                if exc_tb:
                    import traceback
                    log_data['stack_trace'] = ''.join(traceback.format_exception(*record.exc_info))
        
        # Add extra fields
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                               'levelname', 'levelno', 'lineno', 'module', 'msecs',
                               'message', 'pathname', 'process', 'processName',
                               'relativeCreated', 'thread', 'threadName', 'exc_info',
                               'exc_text', 'stack_info'] + enrichment_fields:
                    log_data[key] = value
        
        return json.dumps(log_data, default=str)


class ColoredConsoleFormatter(logging.Formatter):
    """Colored formatter for console output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    def __init__(self, use_colors: bool = True, show_context: bool = True):
        """
        Initialize formatter.
        
        Args:
            use_colors: Whether to use ANSI colors
            show_context: Whether to show enrichment context
        """
        super().__init__()
        self.use_colors = use_colors
        self.show_context = show_context
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with colors and context.
        
        Args:
            record: Log record to format
            
        Returns:
            Formatted string
        """
        # Get color
        color = self.COLORS.get(record.levelname, '') if self.use_colors else ''
        reset = self.RESET if self.use_colors else ''
        bold = self.BOLD if self.use_colors else ''
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Format level
        level = f"{color}{record.levelname:8s}{reset}"
        
        # Format message
        message = record.getMessage()
        
        # Build context string
        context_parts = []
        if self.show_context:
            if hasattr(record, 'step') and record.step:
                context_parts.append(f"step={record.step}")
            if hasattr(record, 'username') and record.username:
                context_parts.append(f"user={record.username}")
            if hasattr(record, 'job_id') and record.job_id:
                context_parts.append(f"job={record.job_id}")
        
        context_str = f" [{', '.join(context_parts)}]" if context_parts else ""
        
        # Format exception if present
        exc_str = ""
        if record.exc_info:
            exc_type, exc_value, exc_tb = record.exc_info
            if exc_type:
                exc_name = classify_exception(exc_value)
                exc_str = f"\n  {color}↳ {exc_name}: {exc_value}{reset}"
        
        # Combine
        return f"{timestamp} - {level} - {message}{context_str}{exc_str}"


class CompactFormatter(logging.Formatter):
    """Compact formatter for less verbose output."""
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record compactly.
        
        Args:
            record: Log record to format
            
        Returns:
            Formatted string
        """
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        level_short = record.levelname[0]  # D, I, W, E, C
        message = record.getMessage()
        
        # Add step if present
        step = ""
        if hasattr(record, 'step') and record.step:
            step = f"[{record.step}] "
        
        return f"{timestamp} {level_short} {step}{message}"
