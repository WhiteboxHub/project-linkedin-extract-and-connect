# utils/retry.py
"""
Retry Framework with Exponential Backoff

Provides robust retry mechanisms for handling transient failures:
- Exponential backoff strategy
- Configurable retry limits
- Selective exception handling
- Comprehensive logging
"""

import time
import logging
from functools import wraps
from typing import Callable, Tuple, Type, Optional

from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)

from utils.exceptions import RetryExhaustedException

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None,
):
    """
    Decorator for retry with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 1.0)
        backoff_factor: Multiplier for delay after each retry (default: 2.0)
        exceptions: Tuple of exception types to catch (default: all exceptions)
        on_retry: Optional callback function called before each retry
        
    Returns:
        Decorated function with retry logic
        
    Example:
        @retry_with_backoff(max_retries=3, exceptions=(TimeoutException,))
        def click_element(element):
            element.click()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries - 1:
                        # Last attempt failed, raise RetryExhaustedException
                        logger.error(
                            f"{func.__name__} failed after {max_retries} attempts: {e}"
                        )
                        raise RetryExhaustedException(e, max_retries)
                    
                    # Log retry attempt
                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1}/{max_retries} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    
                    # Call on_retry callback if provided
                    if on_retry:
                        try:
                            on_retry(attempt, e)
                        except Exception as callback_error:
                            logger.warning(f"on_retry callback failed: {callback_error}")
                    
                    # Wait before retry
                    time.sleep(delay)
                    delay *= backoff_factor
            
            # Should never reach here, but just in case
            if last_exception:
                raise RetryExhaustedException(last_exception, max_retries)
                
        return wrapper
    return decorator


def retry_on_stale_element(max_retries: int = 3):
    """
    Decorator specifically for handling stale element exceptions.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        
    Returns:
        Decorated function with stale element retry logic
        
    Example:
        @retry_on_stale_element(max_retries=3)
        def click_button(self, button_locator):
            button = self.driver.find_element(*button_locator)
            button.click()
    """
    return retry_with_backoff(
        max_retries=max_retries,
        initial_delay=0.5,
        backoff_factor=1.5,
        exceptions=(StaleElementReferenceException,),
    )


def retry_on_timeout(max_retries: int = 2):
    """
    Decorator specifically for handling timeout exceptions.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 2)
        
    Returns:
        Decorated function with timeout retry logic
        
    Example:
        @retry_on_timeout(max_retries=2)
        def wait_for_element(self, locator):
            return self.wait.until(EC.presence_of_element_located(locator))
    """
    return retry_with_backoff(
        max_retries=max_retries,
        initial_delay=2.0,
        backoff_factor=2.0,
        exceptions=(TimeoutException,),
    )


def retry_on_webdriver_exception(max_retries: int = 3):
    """
    Decorator for handling general WebDriver exceptions.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        
    Returns:
        Decorated function with WebDriver exception retry logic
        
    Example:
        @retry_on_webdriver_exception(max_retries=3)
        def navigate_to_page(self, url):
            self.driver.get(url)
    """
    return retry_with_backoff(
        max_retries=max_retries,
        initial_delay=1.0,
        backoff_factor=2.0,
        exceptions=(WebDriverException, TimeoutException, NoSuchElementException),
    )


class RetryContext:
    """
    Context manager for retry logic.
    
    Allows using retry logic without decorators.
    
    Example:
        with RetryContext(max_retries=3, exceptions=(TimeoutException,)):
            element.click()
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
    ):
        """
        Initialize retry context.
        
        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            backoff_factor: Multiplier for delay after each retry
            exceptions: Tuple of exception types to catch
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.exceptions = exceptions
        self.attempt = 0
        self.delay = initial_delay
    
    def __enter__(self):
        """Enter context."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit context with retry logic.
        
        Returns:
            True if exception was handled and should retry, False otherwise
        """
        if exc_type is None:
            # No exception, success
            return False
        
        if not issubclass(exc_type, self.exceptions):
            # Exception not in retry list, don't handle
            return False
        
        self.attempt += 1
        
        if self.attempt >= self.max_retries:
            # Max retries reached, don't suppress exception
            logger.error(f"Retry exhausted after {self.max_retries} attempts: {exc_val}")
            return False
        
        # Log and retry
        logger.warning(
            f"Attempt {self.attempt}/{self.max_retries} failed: {exc_val}. "
            f"Retrying in {self.delay:.1f}s..."
        )
        
        time.sleep(self.delay)
        self.delay *= self.backoff_factor
        
        # Suppress exception to retry
        return True
