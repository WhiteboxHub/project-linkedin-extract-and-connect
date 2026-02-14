# modules/workflow.py
"""
Workflow Module

Orchestrates contact extraction workflow on LinkedIn.
Handles thread clicks, modal interactions, and data extraction.
"""

import logging
from typing import Optional, Dict, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait

from stealth import HumanBehavior
from utils.retry import retry_on_stale_element, retry_on_timeout
from utils.exceptions import ExtractionException

# Import centralized selector system
from linkedin_selectors.helpers import (
    find_element_with_fallback,
    get_text_with_fallback,
    click_element_with_fallback
)

logger = logging.getLogger(__name__)


class WorkflowModule:
    """
    Orchestrates contact extraction workflow.
    
    Responsibilities:
    - Click on threads
    - Open contact modals
    - Extract contact information
    - Handle modal interactions
    """
    
    def __init__(self, driver: uc.Chrome, wait: WebDriverWait, human: HumanBehavior):
        """
        Initialize workflow module.
        
        Args:
            driver: Chrome driver instance
            wait: WebDriverWait instance
            human: HumanBehavior instance for natural interactions
        """
        self.driver = driver
        self.wait = wait
        self.human = human
        
        logger.info("WorkflowModule initialized")
    
    @retry_on_stale_element(max_retries=3)
    def click_thread(self, thread_element: WebElement) -> bool:
        """
        Click on a message thread.
        
        Args:
            thread_element: Thread element to click
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.debug("Clicking thread...")
            self.human.human_click(self.driver, thread_element)
            self.human.random_pause(1, 2)
            return True
            
        except Exception as e:
            logger.warning(f"Failed to click thread: {e}")
            return False
    
    @retry_on_timeout(max_retries=2)
    def open_contact_modal(self) -> bool:
        """
        Open contact information modal using centralized selectors.
        
        Returns:
            True if modal opened successfully, False otherwise
            
        Raises:
            ExtractionException: If modal cannot be opened
        """
        try:
            logger.debug("Opening contact modal...")
            
            # Use centralized selector to click view profile button
            clicked = click_element_with_fallback(
                self.driver,
                category="messaging",
                name="view_profile_button",
                timeout=5
            )
            
            if not clicked:
                logger.warning("Contact info button not found")
                return False
            
            self.human.random_pause(2, 3)
            
            # Verify modal opened
            modal_opened = self._verify_modal_opened()
            if modal_opened:
                logger.info("Contact modal opened successfully")
            else:
                logger.warning("Modal did not open")
            
            return modal_opened
            
        except Exception as e:
            logger.error(f"Failed to open contact modal: {e}")
            raise ExtractionException(f"Modal open failed: {e}")
    
    def _verify_modal_opened(self) -> bool:
        """
        Verify that contact modal is open using centralized selectors.
        
        Returns:
            True if modal is open, False otherwise
        """
        modal = find_element_with_fallback(
            self.driver,
            category="contact_modal",
            name="dialog",
            timeout=2
        )
        
        return modal is not None and modal.is_displayed()
    
    def extract_contact_info(self) -> Dict[str, Any]:
        """
        Extract contact information from modal.
        
        Returns:
            Dictionary with contact information
            
        Raises:
            ExtractionException: If extraction fails
        """
        try:
            logger.debug("Extracting contact information...")
            
            contact_info = {
                'name': self._extract_name(),
                'email': self._extract_email(),
                'phone': self._extract_phone(),
                'profile_url': self._extract_profile_url(),
                'linkedin_url': self._extract_linkedin_url(),
            }
            
            logger.info(f"Extracted contact: {contact_info.get('name', 'Unknown')}")
            return contact_info
            
        except Exception as e:
            logger.error(f"Failed to extract contact info: {e}")
            raise ExtractionException(f"Contact extraction failed: {e}")
    
    def _extract_name(self) -> Optional[str]:
        """Extract contact name using centralized selectors."""
        try:
            name = get_text_with_fallback(
                self.driver,
                category="profile",
                name="name",
                timeout=0
            )
            
            if name:
                logger.debug(f"Found name: {name}")
                return name
            
            logger.warning("Name not found")
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting name: {e}")
            return None
    
    def _extract_email(self) -> Optional[str]:
        """Extract email address using centralized selectors."""
        try:
            element = find_element_with_fallback(
                self.driver,
                category="contact_modal",
                name="email",
                timeout=0
            )
            
            if element:
                email = element.get_attribute('href').replace('mailto:', '').strip()
                if email and '@' in email:
                    logger.debug(f"Found email: {email}")
                    return email
            
            logger.debug("Email not found")
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting email: {e}")
            return None
    
    def _extract_phone(self) -> Optional[str]:
        """Extract phone number using centralized selectors."""
        try:
            element = find_element_with_fallback(
                self.driver,
                category="contact_modal",
                name="phone",
                timeout=0
            )
            
            if element:
                text = element.text.strip()
                # Simple phone number detection
                if any(char.isdigit() for char in text) and len(text) >= 10:
                    logger.debug(f"Found phone: {text}")
                    return text
            
            logger.debug("Phone not found")
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting phone: {e}")
            return None
    
    def _extract_profile_url(self) -> Optional[str]:
        """Extract profile URL."""
        try:
            current_url = self.driver.current_url
            if 'linkedin.com/in/' in current_url:
                logger.debug(f"Found profile URL: {current_url}")
                return current_url
            
            logger.debug("Profile URL not found")
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting profile URL: {e}")
            return None
    
    def _extract_linkedin_url(self) -> Optional[str]:
        """Extract LinkedIn profile URL from modal using centralized selectors."""
        try:
            element = find_element_with_fallback(
                self.driver,
                category="contact_modal",
                name="linkedin_profile",
                timeout=0
            )
            
            if element:
                url = element.get_attribute('href')
                if url and 'linkedin.com/in/' in url:
                    logger.debug(f"Found LinkedIn URL: {url}")
                    return url
            
            logger.debug("LinkedIn URL not found")
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting LinkedIn URL: {e}")
            return None
    
    @retry_on_stale_element(max_retries=2)
    def close_modal(self) -> bool:
        """
        Close contact information modal using centralized selectors.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.debug("Closing modal...")
            
            # Use centralized selector to close modal
            clicked = click_element_with_fallback(
                self.driver,
                category="contact_modal",
                name="dismiss_button",
                timeout=2
            )
            
            if clicked:
                self.human.random_pause(0.5, 1)
                logger.debug("Modal closed")
                return True
            
            logger.warning("Close button not found")
            return False
            
        except Exception as e:
            logger.warning(f"Failed to close modal: {e}")
            return False
