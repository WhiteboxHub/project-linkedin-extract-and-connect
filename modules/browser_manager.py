# modules/browser_manager.py
"""
Browser Manager Module

Centralized browser lifecycle management with health monitoring and restart capability.
Handles all browser-related operations including initialization, health checks, and cleanup.
"""

import logging
import time
from typing import Tuple, Optional
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException

from stealth import (
    setup_undetected_chrome,
    apply_fingerprint_randomization,
    check_chrome_running,
    release_profile_lock,
)

logger = logging.getLogger(__name__)


class BrowserManager:
    """
    Manages browser lifecycle, health monitoring, and restart capability.
    
    Responsibilities:
    - Browser initialization with stealth features
    - Session state management
    - Browser health checks
    - Restart capability
    - Cleanup on shutdown
    """
    

    def __init__(self, chrome_profile: str, headless: bool = False, proxy: Optional[str] = None):
        """
        Initialize browser manager.
        
        Args:
            chrome_profile: Chrome profile name to use
            headless: Whether to run in headless mode
            proxy: Optional proxy string "ip:port"
        """
        self.chrome_profile = chrome_profile
        self.headless = headless
        self.proxy = proxy
        self.driver: Optional[uc.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self._is_initialized = False
        self._restart_count = 0
        self._max_restarts = 3
        
        logger.info(f"BrowserManager initialized for profile: {chrome_profile}")
        if self.proxy:
            logger.info(f"Proxy configured: {self.proxy}")
    
    def start_browser(self) -> Tuple[uc.Chrome, WebDriverWait]:
        """
        Start browser with stealth features.
        
        Returns:
            Tuple of (driver, wait) objects
            
        Raises:
            BrowserException: If browser fails to start
        """
        try:
            logger.info("Starting browser with stealth features...")
            
            # Check if Chrome is already running with this profile
            if check_chrome_running(self.chrome_profile):
                logger.warning(f"Chrome already running with profile: {self.chrome_profile}")
                logger.info("Attempting to release profile lock...")
                release_profile_lock(self.chrome_profile)
                time.sleep(2)
            
            # Setup undetected Chrome
            self.driver, self.wait = setup_undetected_chrome(
                chrome_profile_name=self.chrome_profile,
                headless=self.headless,
                proxy=self.proxy
            )
            
            # Apply fingerprint randomization
            apply_fingerprint_randomization(self.driver)
            
            self._is_initialized = True
            logger.info("Browser started successfully")
            
            return self.driver, self.wait
            
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            raise BrowserException(f"Browser startup failed: {e}")

    
    def restart_browser(self) -> Tuple[uc.Chrome, WebDriverWait]:
        """
        Restart browser (close and start fresh).
        
        Returns:
            Tuple of (driver, wait) objects
            
        Raises:
            BrowserException: If restart limit exceeded or restart fails
        """
        if self._restart_count >= self._max_restarts:
            raise BrowserException(
                f"Maximum restart limit ({self._max_restarts}) exceeded"
            )
        
        logger.info(f"Restarting browser (attempt {self._restart_count + 1}/{self._max_restarts})...")
        
        # Close existing browser
        self.close_browser()
        
        # Wait before restarting
        time.sleep(3)
        
        # Start fresh browser
        self._restart_count += 1
        return self.start_browser()
    
    def is_browser_healthy(self) -> bool:
        """
        Check if browser is healthy and responsive.
        
        Returns:
            True if browser is healthy, False otherwise
        """
        if not self._is_initialized or self.driver is None:
            logger.debug("Browser not initialized")
            return False
        
        try:
            # Try to get current URL (simple health check)
            _ = self.driver.current_url
            
            # Try to execute simple JavaScript
            self.driver.execute_script("return document.readyState;")
            
            logger.debug("Browser health check passed")
            return True
            
        except WebDriverException as e:
            logger.warning(f"Browser health check failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during health check: {e}")
            return False
    
    def get_driver(self) -> uc.Chrome:
        """
        Get the driver instance.
        
        Returns:
            Chrome driver instance
            
        Raises:
            BrowserException: If browser not initialized
        """
        if not self._is_initialized or self.driver is None:
            raise BrowserException("Browser not initialized. Call start_browser() first.")
        
        return self.driver
    
    def get_wait(self) -> WebDriverWait:
        """
        Get the WebDriverWait instance.
        
        Returns:
            WebDriverWait instance
            
        Raises:
            BrowserException: If browser not initialized
        """
        if not self._is_initialized or self.wait is None:
            raise BrowserException("Browser not initialized. Call start_browser() first.")
        
        return self.wait
    
    def close_browser(self) -> None:
        """
        Close browser and cleanup resources.
        """
        if self.driver is not None:
            try:
                logger.info("Closing browser...")
                self.driver.quit()
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
            finally:
                self.driver = None
                self.wait = None
                self._is_initialized = False
    
    def __enter__(self):
        """Context manager entry."""
        self.start_browser()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_browser()
        return False


class BrowserException(Exception):
    """Browser-related errors."""
    pass
