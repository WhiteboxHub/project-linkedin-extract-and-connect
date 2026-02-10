# stealth/fingerprint.py
"""
Fingerprint randomization and selenium-stealth integration.
Hides automation indicators and randomizes browser fingerprint.
"""

import random
import logging
from typing import Optional, Tuple
from selenium_stealth import stealth
import undetected_chromedriver as uc

logger = logging.getLogger(__name__)

# Common user agents (realistic, recent versions)
USER_AGENTS = [
    # Windows Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    # Windows Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
]

# Common viewport sizes (realistic desktop resolutions)
VIEWPORTS = [
    (1920, 1080),  # Full HD
    (1366, 768),   # Common laptop
    (1536, 864),   # Common laptop
    (1440, 900),   # MacBook
    (2560, 1440),  # 2K
]

# Common timezones
TIMEZONES = [
    "America/New_York",
    "America/Chicago",
    "America/Los_Angeles",
    "America/Denver",
    "America/Phoenix",
]


def randomize_user_agent() -> str:
    """
    Get a random realistic user agent.
    
    Returns:
        Random user agent string
    """
    user_agent = random.choice(USER_AGENTS)
    logger.debug(f"Randomized user agent: {user_agent[:50]}...")
    return user_agent


def randomize_viewport() -> Tuple[int, int]:
    """
    Get a random realistic viewport size.
    
    Returns:
        Tuple of (width, height)
    """
    viewport = random.choice(VIEWPORTS)
    logger.debug(f"Randomized viewport: {viewport}")
    return viewport


def randomize_timezone() -> str:
    """
    Get a random timezone.
    
    Returns:
        Timezone string
    """
    timezone = random.choice(TIMEZONES)
    logger.debug(f"Randomized timezone: {timezone}")
    return timezone


def apply_stealth(driver: uc.Chrome) -> None:
    """
    Apply selenium-stealth to hide automation indicators.
    
    Args:
        driver: Chrome driver instance
    """
    try:
        logger.info("Applying selenium-stealth...")
        
        stealth(
            driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        
        logger.info("✅ Selenium-stealth applied successfully")
        
    except Exception as e:
        logger.error(f"Failed to apply stealth: {e}")
        raise


def apply_fingerprint_randomization(driver: uc.Chrome) -> None:
    """
    Apply comprehensive fingerprint randomization.
    
    Args:
        driver: Chrome driver instance
    """
    try:
        logger.info("Applying fingerprint randomization...")
        
        # Apply selenium-stealth first
        apply_stealth(driver)
        
        # Additional fingerprint randomization via JavaScript
        user_agent = randomize_user_agent()
        
        # Override navigator properties
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": user_agent
        })
        
        # Randomize viewport
        width, height = randomize_viewport()
        driver.set_window_size(width, height)
        
        # Override timezone
        timezone = randomize_timezone()
        driver.execute_cdp_cmd('Emulation.setTimezoneOverride', {
            'timezoneId': timezone
        })
        
        # Additional anti-detection scripts
        driver.execute_script("""
            // Hide webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        logger.info("✅ Fingerprint randomization applied successfully")
        logger.info(f"   User Agent: {user_agent[:60]}...")
        logger.info(f"   Viewport: {width}x{height}")
        logger.info(f"   Timezone: {timezone}")
        
    except Exception as e:
        logger.error(f"Failed to apply fingerprint randomization: {e}")
        raise


def get_fingerprint_info(driver: uc.Chrome) -> dict:
    """
    Get current browser fingerprint information.
    
    Args:
        driver: Chrome driver instance
        
    Returns:
        Dictionary with fingerprint details
    """
    try:
        info = driver.execute_script("""
            return {
                userAgent: navigator.userAgent,
                platform: navigator.platform,
                language: navigator.language,
                languages: navigator.languages,
                webdriver: navigator.webdriver,
                plugins: navigator.plugins.length,
                hardwareConcurrency: navigator.hardwareConcurrency,
                deviceMemory: navigator.deviceMemory,
                viewport: {
                    width: window.innerWidth,
                    height: window.innerHeight
                }
            };
        """)
        
        return info
        
    except Exception as e:
        logger.error(f"Failed to get fingerprint info: {e}")
        return {}
