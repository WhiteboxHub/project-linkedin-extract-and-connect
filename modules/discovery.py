# modules/discovery.py
"""
Discovery Module

Handles message thread discovery and filtering on LinkedIn.
Responsible for navigating to messages, loading threads, and filtering.
"""

import logging
from typing import List, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait

from stealth import HumanBehavior
from utils.retry import retry_on_timeout, retry_on_stale_element
from utils.exceptions import NavigationException

# Import centralized selector system
from linkedin_selectors.helpers import (
    find_element_with_fallback,
    find_elements_with_fallback
)

logger = logging.getLogger(__name__)


class DiscoveryModule:
    """
    Handles message thread discovery and filtering.
    
    Responsibilities:
    - Navigate to messages page
    - Scroll to load threads
    - Filter threads based on criteria
    - Extract thread metadata
    """
    
    def __init__(self, driver: uc.Chrome, wait: WebDriverWait, human: HumanBehavior):
        """
        Initialize discovery module.
        
        Args:
            driver: Chrome driver instance
            wait: WebDriverWait instance
            human: HumanBehavior instance for natural interactions
        """
        self.driver = driver
        self.wait = wait
        self.human = human
        self.main_window = None
        
        logger.info("DiscoveryModule initialized")
    
    @retry_on_timeout(max_retries=2)
    def navigate_to_messages(self) -> None:
        """
        Navigate to LinkedIn messages page.
        
        Raises:
            NavigationException: If navigation fails
        """
        try:
            logger.info("Navigating to messages page...")
            self.driver.get("https://www.linkedin.com/messaging/")
            self.human.random_pause(3, 5)
            
            current_url = self.driver.current_url
            logger.info(f"Current URL: {current_url}")
            
            if "login" in current_url:
                raise NavigationException("Session expired - login required")
            
            # Store main window handle
            self.main_window = self.driver.current_window_handle
            logger.info(f"Main window handle: {self.main_window}")
            
        except Exception as e:
            logger.error(f"Failed to navigate to messages: {e}")
            raise NavigationException(f"Navigation failed: {e}")
    
    def load_all_threads(self, max_scrolls: int = 20, max_threads: Optional[int] = None) -> None:
        """
        Scroll to load all message threads.
        
        Args:
            max_scrolls: Maximum number of scroll attempts
            max_threads: Maximum number of threads to load (None = all)
            
        Raises:
            NavigationException: If container not found
        """
        try:
            logger.info(f"Loading threads (max_scrolls={max_scrolls}, max_threads={max_threads})...")
            
            # Find message container
            container = self._find_message_container()
            if not container:
                raise NavigationException("Message container not found")
            
            last_height = self.driver.execute_script(
                "return arguments[0].scrollHeight", container
            )
            
            for scroll_count in range(max_scrolls):
                # Count current threads
                threads = self.get_thread_elements()
                logger.debug(f"Scroll {scroll_count + 1}: Found {len(threads)} threads")
                
                # Check if we have enough threads
                if max_threads and len(threads) >= max_threads:
                    logger.info(f"Loaded {len(threads)} threads (target: {max_threads})")
                    break
                
                # Try to click "Load more" button first
                clicked_load_more = self._click_load_more()
                
                if not clicked_load_more:
                    # Scroll down with human-like behavior (scroll container!)
                    self.human.random_scroll(self.driver, direction="down", amount=None, element=container)
                
                self.human.random_pause(1, 2)
                
                # Check if we reached the bottom
                new_height = self.driver.execute_script(
                    "return arguments[0].scrollHeight", container
                )
                
                if new_height == last_height and not clicked_load_more:
                    logger.info(f"Reached bottom after {scroll_count + 1} scrolls")
                    break
                
                last_height = new_height
            
            final_count = len(self.get_thread_elements())
            logger.info(f"Finished loading: {final_count} threads total")
            
        except Exception as e:
            logger.error(f"Failed to load threads: {e}")
            raise NavigationException(f"Thread loading failed: {e}")

    def _click_load_more(self) -> bool:
        """
        Check for and click 'Load more conversations' button.
        Returns: True if clicked, False otherwise.
        Click 'Load more' button if present.
        
        Returns:
            True if button was clicked, False otherwise
        """
        try:
            # Use centralized selector
            button = find_element_with_fallback(
                self.driver,
                category="messaging",
                name="load_more_button",
                timeout=2
            )
            
            if button:
                self.human.human_click(self.driver, button)
                self.human.random_pause(2, 3)
                logger.debug("Clicked 'Load more' button")
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"No 'Load more' button found: {e}")
            return False
    
    def _find_message_container(self) -> Optional[WebElement]:
        """
        Find message container element using centralized selectors.
        
        Returns:
            Container WebElement or None
        """
        try:
            container = find_element_with_fallback(
                self.driver,
                category="messaging",
                name="thread_container",
                timeout=5
            )
            
            if container:
                logger.debug("Found message container")
                return container
            
            logger.warning("Message container not found")
            return None
            
        except Exception as e:
            logger.error(f"Error finding message container: {e}")
            return None
    
    @retry_on_stale_element(max_retries=3)
    def get_thread_elements(self) -> List[WebElement]:
        """
        Get all thread elements using centralized selectors.
        
        Returns:
            List of thread WebElements
        """
        try:
            # Use centralized selector system
            threads = find_elements_with_fallback(
                self.driver,
                category="messaging",
                name="thread_list"
            )
            
            if threads:
                logger.debug(f"Found {len(threads)} threads")
                return threads
            
            logger.warning("No threads found")
            return []
            
        except Exception as e:
            logger.error(f"Failed to get thread elements: {e}")
            return []
    
    def filter_threads(self, threads: List[WebElement], criteria: dict) -> List[WebElement]:
        """
        Filter threads based on criteria.
        
        Args:
            threads: List of thread elements
            criteria: Filter criteria (e.g., {'unread': True, 'max_count': 10})
            
        Returns:
            Filtered list of threads
        """
        filtered = threads
        
        # Apply max count filter
        if 'max_count' in criteria:
            max_count = criteria['max_count']
            filtered = filtered[:max_count]
            logger.info(f"Limited to {max_count} threads")
        
        # Could add more filters here:
        # - Unread only
        # - Date range
        # - Sender name pattern
        # etc.
        
        logger.info(f"Filtered: {len(filtered)} threads (from {len(threads)})")
        return filtered
    
    def get_thread_count(self) -> int:
        """
        Get current number of loaded threads.
        
        Returns:
            Number of threads
        """
        return len(self.get_thread_elements())
