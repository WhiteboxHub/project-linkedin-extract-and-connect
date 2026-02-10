# selectors/helpers.py
"""
Helper functions for using selectors with automatic fallback.
"""

import logging
from typing import Optional, List
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .selectors import get_selector, get_all_selectors, get_description

logger = logging.getLogger(__name__)


def find_element_with_fallback(
    driver: WebDriver,
    category: str,
    name: str,
    parent: Optional[WebElement] = None,
    timeout: int = 0
) -> Optional[WebElement]:
    """
    Find element using primary selector, falling back to alternatives.
    
    Args:
        driver: Selenium WebDriver instance
        category: Selector category
        name: Selector name
        parent: Parent element to search within (optional)
        timeout: Seconds to wait (0 = no wait)
        
    Returns:
        WebElement if found, None otherwise
    """
    selectors = get_all_selectors(category, name)
    description = get_description(category, name)
    search_context = parent if parent else driver
    
    for i, selector in enumerate(selectors):
        selector_type = "primary" if i == 0 else f"fallback {i}"
        
        try:
            if timeout > 0:
                wait = WebDriverWait(driver, timeout)
                element = wait.until(EC.presence_of_element_located(selector))
            else:
                element = search_context.find_element(*selector)
            
            if i > 0:
                logger.info(f"✅ {category}.{name}: Found using {selector_type}")
            
            return element
            
        except (TimeoutException, NoSuchElementException):
            if i == len(selectors) - 1:
                # Last selector failed
                logger.warning(f"⚠️  {category}.{name}: Not found ({description})")
            continue
        except Exception as e:
            logger.error(f"❌ {category}.{name}: Error with {selector_type} - {e}")
            continue
    
    return None


def find_elements_with_fallback(
    driver: WebDriver,
    category: str,
    name: str,
    parent: Optional[WebElement] = None
) -> List[WebElement]:
    """
    Find multiple elements using primary selector, falling back to alternatives.
    
    Args:
        driver: Selenium WebDriver instance
        category: Selector category
        name: Selector name
        parent: Parent element to search within (optional)
        
    Returns:
        List of WebElements (empty if none found)
    """
    selectors = get_all_selectors(category, name)
    description = get_description(category, name)
    search_context = parent if parent else driver
    
    for i, selector in enumerate(selectors):
        selector_type = "primary" if i == 0 else f"fallback {i}"
        
        try:
            elements = search_context.find_elements(*selector)
            
            if elements:
                if i > 0:
                    logger.info(f"✅ {category}.{name}: Found {len(elements)} using {selector_type}")
                return elements
                
        except Exception as e:
            logger.error(f"❌ {category}.{name}: Error with {selector_type} - {e}")
            continue
    
    logger.warning(f"⚠️  {category}.{name}: No elements found ({description})")
    return []


def click_element_with_fallback(
    driver: WebDriver,
    category: str,
    name: str,
    timeout: int = 5
) -> bool:
    """
    Find and click element using selectors with fallback.
    
    Args:
        driver: Selenium WebDriver instance
        category: Selector category
        name: Selector name
        timeout: Seconds to wait for element
        
    Returns:
        True if clicked successfully, False otherwise
    """
    element = find_element_with_fallback(driver, category, name, timeout=timeout)
    
    if element:
        try:
            element.click()
            logger.debug(f"✅ {category}.{name}: Clicked successfully")
            return True
        except Exception as e:
            logger.error(f"❌ {category}.{name}: Click failed - {e}")
            return False
    
    return False


def get_text_with_fallback(
    driver: WebDriver,
    category: str,
    name: str,
    timeout: int = 0
) -> Optional[str]:
    """
    Find element and get its text using selectors with fallback.
    
    Args:
        driver: Selenium WebDriver instance
        category: Selector category
        name: Selector name
        timeout: Seconds to wait for element
        
    Returns:
        Element text if found, None otherwise
    """
    element = find_element_with_fallback(driver, category, name, timeout=timeout)
    
    if element:
        try:
            text = element.text.strip()
            return text if text else None
        except Exception as e:
            logger.error(f"❌ {category}.{name}: Failed to get text - {e}")
            return None
    
    return None


def get_attribute_with_fallback(
    driver: WebDriver,
    category: str,
    name: str,
    attribute: str,
    timeout: int = 0
) -> Optional[str]:
    """
    Find element and get its attribute using selectors with fallback.
    
    Args:
        driver: Selenium WebDriver instance
        category: Selector category
        name: Selector name
        attribute: Attribute name to get
        timeout: Seconds to wait for element
        
    Returns:
        Attribute value if found, None otherwise
    """
    element = find_element_with_fallback(driver, category, name, timeout=timeout)
    
    if element:
        try:
            return element.get_attribute(attribute)
        except Exception as e:
            logger.error(f"❌ {category}.{name}: Failed to get attribute '{attribute}' - {e}")
            return None
    
    return None
