# utils/exceptions.py
"""
Custom Exception Classes for LinkedIn Bot

Provides a hierarchy of exceptions for different error scenarios:
- LinkedInBotException: Base exception
- BrowserException: Browser-related errors
- NavigationException: Navigation and page load errors
- ExtractionException: Data extraction errors
- AbortException: Controlled abort signal
"""

import logging

logger = logging.getLogger(__name__)


class LinkedInBotException(Exception):
    """
    Base exception for LinkedIn bot.
    
    All custom exceptions inherit from this class.
    """
    pass


class BrowserException(LinkedInBotException):
    """
    Browser-related errors.
    
    Examples:
    - Browser failed to start
    - Browser crashed
    - Browser health check failed
    """
    pass


class NavigationException(LinkedInBotException):
    """
    Navigation and page load errors.
    
    Examples:
    - Page failed to load
    - Element not found
    - Timeout waiting for element
    """
    pass


class ExtractionException(LinkedInBotException):
    """
    Data extraction errors.
    
    Examples:
    - Failed to extract contact info
    - Invalid data format
    - Missing required fields
    """
    pass


class AbortException(LinkedInBotException):
    """
    Controlled abort signal.
    
    Used to gracefully stop execution when a condition is met
    that requires stopping the bot (e.g., rate limit, security challenge).
    """
    
    def __init__(self, reason: str, cleanup_required: bool = True):
        """
        Initialize abort exception.
        
        Args:
            reason: Human-readable reason for abort
            cleanup_required: Whether cleanup is needed before exit
        """
        self.reason = reason
        self.cleanup_required = cleanup_required
        super().__init__(reason)
        logger.warning(f"AbortException raised: {reason} (cleanup={cleanup_required})")


class RetryExhaustedException(LinkedInBotException):
    """
    Raised when retry attempts are exhausted.
    
    Contains information about the original exception and number of attempts.
    """
    
    def __init__(self, original_exception: Exception, attempts: int):
        """
        Initialize retry exhausted exception.
        
        Args:
            original_exception: The exception that caused retries
            attempts: Number of retry attempts made
        """
        self.original_exception = original_exception
        self.attempts = attempts
        message = f"Retry exhausted after {attempts} attempts: {original_exception}"
        super().__init__(message)
        logger.error(f"RetryExhaustedException: {message}")
