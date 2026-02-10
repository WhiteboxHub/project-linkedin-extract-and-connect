# selectors/validator.py
"""
Selector validation module.
Validates selectors at startup to ensure they work with current LinkedIn UI.
"""

import logging
from typing import Dict, List, Tuple, Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .selectors import SELECTORS, get_selector, get_all_selectors, is_critical

logger = logging.getLogger(__name__)


class SelectorValidator:
    """Validates LinkedIn selectors against live pages."""
    
    def __init__(self, driver: WebDriver, wait_time: int = 5):
        """
        Initialize validator.
        
        Args:
            driver: Selenium WebDriver instance
            wait_time: Seconds to wait for elements
        """
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_time)
        self.results = {}
    
    def validate_selector(self, category: str, name: str, try_fallbacks: bool = True) -> Dict:
        """
        Validate a single selector.
        
        Args:
            category: Selector category
            name: Selector name
            try_fallbacks: Whether to try fallback selectors
            
        Returns:
            Validation result dictionary
        """
        result = {
            "category": category,
            "name": name,
            "primary_found": False,
            "fallback_used": None,
            "fallback_index": None,
            "critical": is_critical(category, name),
            "error": None,
        }
        
        try:
            # Try primary selector
            primary = get_selector(category, name)
            try:
                element = self.driver.find_element(*primary)
                result["primary_found"] = True
                logger.debug(f"✅ {category}.{name}: Primary selector found")
                return result
            except NoSuchElementException:
                logger.debug(f"⚠️  {category}.{name}: Primary selector not found")
            
            # Try fallbacks if enabled
            if try_fallbacks:
                fallbacks = get_all_selectors(category, name)[1:]  # Skip primary
                for i, fallback in enumerate(fallbacks):
                    try:
                        element = self.driver.find_element(*fallback)
                        result["fallback_used"] = fallback
                        result["fallback_index"] = i
                        logger.debug(f"✅ {category}.{name}: Fallback {i+1} found")
                        return result
                    except NoSuchElementException:
                        continue
            
            # None found
            result["error"] = "No selector found (primary or fallbacks)"
            if result["critical"]:
                logger.error(f"❌ {category}.{name}: CRITICAL selector not found!")
            else:
                logger.warning(f"⚠️  {category}.{name}: Optional selector not found")
                
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"❌ {category}.{name}: Validation error - {e}")
        
        return result
    
    def validate_category(self, category: str) -> Dict[str, Dict]:
        """
        Validate all selectors in a category.
        
        Args:
            category: Selector category to validate
            
        Returns:
            Dictionary of validation results
        """
        results = {}
        
        if category not in SELECTORS:
            logger.error(f"❌ Category not found: {category}")
            return results
        
        logger.info(f"Validating category: {category}")
        
        for name in SELECTORS[category].keys():
            results[name] = self.validate_selector(category, name)
        
        return results
    
    def validate_all(self, categories: Optional[List[str]] = None) -> Dict[str, Dict[str, Dict]]:
        """
        Validate all selectors or specific categories.
        
        Args:
            categories: List of categories to validate, or None for all
            
        Returns:
            Nested dictionary of validation results
        """
        if categories is None:
            categories = list(SELECTORS.keys())
        
        results = {}
        
        for category in categories:
            results[category] = self.validate_category(category)
        
        self.results = results
        return results
    
    def print_report(self):
        """Print validation report."""
        if not self.results:
            logger.warning("No validation results to report")
            return
        
        logger.info("=" * 60)
        logger.info("SELECTOR VALIDATION REPORT")
        logger.info("=" * 60)
        
        total = 0
        primary_found = 0
        fallback_used = 0
        not_found = 0
        critical_missing = 0
        
        for category, selectors in self.results.items():
            logger.info(f"\n[{category.upper()}]")
            
            for name, result in selectors.items():
                total += 1
                
                if result["primary_found"]:
                    primary_found += 1
                    status = "✅ PRIMARY"
                elif result["fallback_used"]:
                    fallback_used += 1
                    status = f"⚠️  FALLBACK {result['fallback_index'] + 1}"
                else:
                    not_found += 1
                    status = "❌ NOT FOUND"
                    if result["critical"]:
                        critical_missing += 1
                        status += " (CRITICAL!)"
                
                logger.info(f"  {name}: {status}")
        
        logger.info("\n" + "=" * 60)
        logger.info("SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total selectors: {total}")
        logger.info(f"Primary found: {primary_found}")
        logger.info(f"Fallback used: {fallback_used}")
        logger.info(f"Not found: {not_found}")
        
        if critical_missing > 0:
            logger.error(f"❌ CRITICAL SELECTORS MISSING: {critical_missing}")
            logger.error("Bot may not function correctly!")
        else:
            logger.info("✅ All critical selectors found")
        
        logger.info("=" * 60)
        
        return {
            "total": total,
            "primary_found": primary_found,
            "fallback_used": fallback_used,
            "not_found": not_found,
            "critical_missing": critical_missing,
        }


def validate_selectors(driver: WebDriver, categories: Optional[List[str]] = None) -> bool:
    """
    Convenience function to validate selectors.
    
    Args:
        driver: Selenium WebDriver instance
        categories: List of categories to validate, or None for all
        
    Returns:
        True if all critical selectors found, False otherwise
    """
    validator = SelectorValidator(driver)
    validator.validate_all(categories)
    summary = validator.print_report()
    
    return summary["critical_missing"] == 0
