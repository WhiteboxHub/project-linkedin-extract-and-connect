# logging_config/schema.py
"""
Logging schema definitions for structured logging.
"""

from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


class LogLevel(str, Enum):
    """Standard log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogStep(str, Enum):
    """Bot execution steps for context."""
    INIT = "INIT"
    BROWSER_START = "BROWSER_START"
    LOGIN = "LOGIN"
    NAVIGATION = "NAVIGATION"
    MESSAGING = "MESSAGING"
    EXTRACTION = "EXTRACTION"
    PROFILE_VIEW = "PROFILE_VIEW"
    CONTACT_INFO = "CONTACT_INFO"
    DATA_SAVE = "DATA_SAVE"
    API_CALL = "API_CALL"
    CLEANUP = "CLEANUP"
    ERROR_HANDLING = "ERROR_HANDLING"


class ExceptionType(str, Enum):
    """Common exception types."""
    TIMEOUT = "TimeoutException"
    NO_ELEMENT = "NoSuchElementException"
    STALE_ELEMENT = "StaleElementReferenceException"
    WEB_DRIVER = "WebDriverException"
    PERMISSION = "PermissionError"
    IO_ERROR = "IOError"
    VALUE_ERROR = "ValueError"
    KEY_ERROR = "KeyError"
    ATTRIBUTE_ERROR = "AttributeError"
    HTTP_ERROR = "HTTPError"
    CONNECTION_ERROR = "ConnectionError"
    UNKNOWN = "UnknownException"


@dataclass
class LogRecord:
    """Structured log record."""
    timestamp: str
    level: str
    message: str
    logger_name: str
    
    # Enrichment fields
    job_id: Optional[int] = None
    employee_id: Optional[int] = None
    candidate_id: Optional[int] = None
    step: Optional[str] = None
    username: Optional[str] = None
    
    # Exception fields
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None
    stack_trace: Optional[str] = None
    
    # Additional context
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}
    
    def to_json_string(self) -> str:
        """Convert to JSON string."""
        import json
        return json.dumps(self.to_dict(), default=str)


def classify_exception(exc: Exception) -> str:
    """
    Classify exception type.
    
    Args:
        exc: Exception instance
        
    Returns:
        ExceptionType string
    """
    exc_name = type(exc).__name__
    
    # Map common exceptions
    exception_map = {
        'TimeoutException': ExceptionType.TIMEOUT,
        'NoSuchElementException': ExceptionType.NO_ELEMENT,
        'StaleElementReferenceException': ExceptionType.STALE_ELEMENT,
        'WebDriverException': ExceptionType.WEB_DRIVER,
        'PermissionError': ExceptionType.PERMISSION,
        'IOError': ExceptionType.IO_ERROR,
        'OSError': ExceptionType.IO_ERROR,
        'ValueError': ExceptionType.VALUE_ERROR,
        'KeyError': ExceptionType.KEY_ERROR,
        'AttributeError': ExceptionType.ATTRIBUTE_ERROR,
        'HTTPError': ExceptionType.HTTP_ERROR,
        'ConnectionError': ExceptionType.CONNECTION_ERROR,
        'RequestException': ExceptionType.CONNECTION_ERROR,
    }
    
    return exception_map.get(exc_name, ExceptionType.UNKNOWN).value
