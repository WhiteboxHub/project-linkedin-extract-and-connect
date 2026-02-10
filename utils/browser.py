# utils/browser.py
"""
Browser setup with undetected ChromeDriver and stealth features.
Replaces standard Selenium with undetected-chromedriver for anti-detection.
"""

import os
import logging
from pathlib import Path
from typing import Tuple
from selenium.webdriver.support.ui import WebDriverWait
import undetected_chromedriver as uc

# Import stealth modules
from stealth import (
    setup_undetected_chrome,
    apply_fingerprint_randomization,
    check_chrome_running,
    release_profile_lock,
)

logger = logging.getLogger(__name__)


def setup_browser(chrome_profile_name: str) -> Tuple[uc.Chrome, WebDriverWait]:
    """
    Setup browser using undetected ChromeDriver with full stealth features.
    
    This function replaces the old Selenium-based setup with:
    - Undetected ChromeDriver (bypasses automation detection)
    - Fingerprint randomization (unique browser identity)
    - Profile safety checks (prevents conflicts)
    
    Args:
        chrome_profile_name: Name of Chrome profile to use
        
    Returns:
        Tuple of (driver, wait) objects
        
    Raises:
        RuntimeError: If Chrome is already running with profile
        FileNotFoundError: If Chrome profile doesn't exist
    """
    driver = None
    profile_path = None
    
    try:
        logger.info("=" * 60)
        logger.info("Setting up browser with STEALTH features")
        logger.info(f"Profile: {chrome_profile_name}")
        logger.info("=" * 60)
        
        # Setup undetected Chrome with profile safety checks
        driver, wait = setup_undetected_chrome(
            chrome_profile_name=chrome_profile_name,
            headless=False,  # Headless mode is more detectable
        )
        
        # Apply fingerprint randomization
        logger.info("Applying fingerprint randomization...")
        apply_fingerprint_randomization(driver)
        
        logger.info("✅ Browser setup complete with stealth features")
        logger.info("=" * 60)
        
        return driver, wait
        
    except Exception as e:
        logger.error(f"Browser setup failed: {e}", exc_info=True)
        
        # Cleanup on failure
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        
        # Release profile lock if it was created
        if profile_path:
            try:
                release_profile_lock(profile_path)
            except Exception:
                pass
        
        raise


def close_browser(driver: uc.Chrome, profile_path: str = None) -> None:
    """
    Safely close browser and release profile lock.
    
    Args:
        driver: Chrome driver instance
        profile_path: Optional profile path for lock release
    """
    if driver:
        try:
            driver.quit()
            logger.info("Browser closed")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
    
    # Release profile lock if path provided
    if profile_path:
        try:
            release_profile_lock(profile_path)
        except Exception as e:
            logger.debug(f"Error releasing profile lock: {e}")
