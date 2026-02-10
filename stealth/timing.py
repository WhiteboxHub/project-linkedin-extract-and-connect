# stealth/timing.py
"""
Natural timing patterns for human-like behavior.
Provides realistic delays for various actions.
"""

import random
import time
import logging

logger = logging.getLogger(__name__)


def get_random_delay(min_ms: int, max_ms: int) -> float:
    """
    Get a random delay in seconds.
    
    Args:
        min_ms: Minimum delay in milliseconds
        max_ms: Maximum delay in milliseconds
        
    Returns:
        Random delay in seconds
    """
    delay_ms = random.uniform(min_ms, max_ms)
    return delay_ms / 1000.0


def get_typing_delay() -> float:
    """
    Get a realistic typing delay between characters.
    Simulates variable human typing speed.
    
    Returns:
        Delay in seconds (50-150ms)
    """
    return get_random_delay(50, 150)


def get_scroll_delay() -> float:
    """
    Get a natural scroll timing delay.
    
    Returns:
        Delay in seconds (200-800ms)
    """
    return get_random_delay(200, 800)


def get_click_delay() -> float:
    """
    Get a pre-click pause delay.
    Simulates human hesitation before clicking.
    
    Returns:
        Delay in seconds (100-500ms)
    """
    return get_random_delay(100, 500)


def get_page_load_delay() -> float:
    """
    Get a page load wait delay.
    
    Returns:
        Delay in seconds (1-3s)
    """
    return get_random_delay(1000, 3000)


def get_reading_time(word_count: int) -> float:
    """
    Calculate realistic reading time based on word count.
    Assumes 200-300 words per minute reading speed.
    
    Args:
        word_count: Number of words to read
        
    Returns:
        Reading time in seconds
    """
    # Random reading speed: 200-300 words per minute
    words_per_minute = random.uniform(200, 300)
    words_per_second = words_per_minute / 60.0
    
    reading_time = word_count / words_per_second
    
    # Add some variance
    variance = reading_time * random.uniform(-0.2, 0.2)
    return max(0.5, reading_time + variance)


def random_pause(min_seconds: float = 0.5, max_seconds: float = 3.0) -> None:
    """
    Pause for a random duration to simulate human thinking.
    
    Args:
        min_seconds: Minimum pause duration
        max_seconds: Maximum pause duration
    """
    pause_time = random.uniform(min_seconds, max_seconds)
    logger.debug(f"Random pause: {pause_time:.2f}s")
    time.sleep(pause_time)


def reading_pause(text: str) -> None:
    """
    Pause based on text length to simulate reading.
    
    Args:
        text: Text content to "read"
    """
    if not text:
        return
    
    word_count = len(text.split())
    reading_time = get_reading_time(word_count)
    
    logger.debug(f"Reading pause: {reading_time:.2f}s for {word_count} words")
    time.sleep(reading_time)
