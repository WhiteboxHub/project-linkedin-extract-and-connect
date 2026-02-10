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
        Open contact information modal.
        
        Returns:
            True if modal opened successfully, False otherwise
            
        Raises:
            ExtractionException: If modal cannot be opened
        """
        try:
            logger.debug("Opening contact modal...")
            
            # Find and click contact info button
            button_selectors = [
                "//button[contains(@aria-label, 'view') and contains(@aria-label, 'profile')]",
                "//button[contains(@class, 'msg-thread__link-to-profile')]",
                "//a[contains(@class, 'msg-thread__link-to-profile')]",
            ]
            
            button = None
            for selector in button_selectors:
                try:
                    button = self.wait.until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    if button:
                        logger.debug(f"Found button with selector: {selector}")
                        break
                except TimeoutException:
                    continue
            
            if not button:
                logger.warning("Contact info button not found")
                return False
            
            # Click button
            self.human.human_click(self.driver, button)
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
        Verify that contact modal is open.
        
        Returns:
            True if modal is open, False otherwise
        """
        modal_selectors = [
            "//div[contains(@class, 'artdeco-modal')]",
            "//div[contains(@role, 'dialog')]",
            "//section[contains(@class, 'pv-contact-info')]",
        ]
        
        for selector in modal_selectors:
            try:
                modal = self.driver.find_element(By.XPATH, selector)
                if modal and modal.is_displayed():
                    return True
            except NoSuchElementException:
                continue
        
        return False
    
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
        """Extract contact name."""
        try:
            selectors = [
                "//h1[contains(@class, 'text-heading-xlarge')]",
                "//div[contains(@class, 'pv-text-details__left-panel')]//h1",
                "//h2[contains(@class, 'msg-thread__title')]",
            ]
            
            for selector in selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    name = element.text.strip()
                    if name:
                        logger.debug(f"Found name: {name}")
                        return name
                except NoSuchElementException:
                    continue
            
            logger.warning("Name not found")
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting name: {e}")
            return None
    
    def _extract_email(self) -> Optional[str]:
        """Extract email address."""
        try:
            selectors = [
                "//section[contains(@class, 'pv-contact-info__contact-type')]//a[contains(@href, 'mailto:')]",
                "//a[contains(@href, 'mailto:')]",
            ]
            
            for selector in selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    email = element.get_attribute('href').replace('mailto:', '').strip()
                    if email and '@' in email:
                        logger.debug(f"Found email: {email}")
                        return email
                except NoSuchElementException:
                    continue
            
            logger.debug("Email not found")
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting email: {e}")
            return None
    
    def _extract_phone(self) -> Optional[str]:
        """Extract phone number."""
        try:
            selectors = [
                "//section[contains(@class, 'pv-contact-info__contact-type')]//span[contains(@class, 'pv-contact-info__contact-link')]",
                "//li[contains(@class, 'pv-contact-info__contact-item')]//span",
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        text = element.text.strip()
                        # Simple phone number detection
                        if any(char.isdigit() for char in text) and len(text) >= 10:
                            logger.debug(f"Found phone: {text}")
                            return text
                except NoSuchElementException:
                    continue
            
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
        """Extract LinkedIn profile URL from modal."""
        try:
            selectors = [
                "//a[contains(@href, 'linkedin.com/in/')]",
                "//section[contains(@class, 'pv-contact-info')]//a[contains(@href, 'linkedin.com')]",
            ]
            
            for selector in selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    url = element.get_attribute('href')
                    if url and 'linkedin.com/in/' in url:
                        logger.debug(f"Found LinkedIn URL: {url}")
                        return url
                except NoSuchElementException:
                    continue
            
            logger.debug("LinkedIn URL not found")
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting LinkedIn URL: {e}")
            return None
    
    @retry_on_stale_element(max_retries=2)
    def close_modal(self) -> bool:
        """
        Close contact information modal.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.debug("Closing modal...")
            
            # Find close button
            close_selectors = [
                "//button[contains(@aria-label, 'Dismiss')]",
                "//button[contains(@class, 'artdeco-modal__dismiss')]",
                "//button[@data-test-modal-close-btn]",
            ]
            
            for selector in close_selectors:
                try:
                    button = self.driver.find_element(By.XPATH, selector)
                    if button:
                        self.human.human_click(self.driver, button)
                        self.human.random_pause(0.5, 1)
                        logger.debug("Modal closed")
                        return True
                except NoSuchElementException:
                    continue
            
            logger.warning("Close button not found")
            return False
            
        except Exception as e:
            logger.warning(f"Failed to close modal: {e}")
            return False
