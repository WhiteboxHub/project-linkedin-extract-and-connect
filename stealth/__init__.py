# stealth/__init__.py
"""
Stealth package for LinkedIn bot anti-detection.
Provides undetected ChromeDriver, fingerprint randomization, and human behavior simulation.
"""

from .undetected_browser import (
    setup_undetected_chrome,
    check_chrome_running,
    create_profile_lock,
    release_profile_lock,
)
from .fingerprint import (
    apply_stealth,
    apply_fingerprint_randomization,
    get_fingerprint_info,
)
from .human_behavior import HumanBehavior
from .timing import (
    get_random_delay,
    get_typing_delay,
    get_scroll_delay,
    get_click_delay,
    random_pause,
    reading_pause,
)

__all__ = [
    'setup_undetected_chrome',
    'check_chrome_running',
    'create_profile_lock',
    'release_profile_lock',
    'apply_stealth',
    'apply_fingerprint_randomization',
    'get_fingerprint_info',
    'HumanBehavior',
    'get_random_delay',
    'get_typing_delay',
    'get_scroll_delay',
    'get_click_delay',
    'random_pause',
    'reading_pause',
]
