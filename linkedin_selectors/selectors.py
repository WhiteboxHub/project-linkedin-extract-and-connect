# selectors/linkedin_selectors.py
"""
Centralized LinkedIn Selector Registry
All selectors for LinkedIn automation in one place with fallbacks.
"""

from selenium.webdriver.common.by import By
from typing import Tuple, List, Dict, Any

# ============================================
# SELECTOR REGISTRY
# ============================================

SELECTORS = {
    # ========== LOGIN ==========
    "login": {
        "global_nav": {
            "primary": (By.ID, "global-nav"),
            "fallback": [(By.CSS_SELECTOR, "nav.global-nav")],
            "description": "Main navigation bar (indicates logged in)",
            "critical": True,
        },
        "username_field": {
            "primary": (By.ID, "username"),
            "fallback": [(By.NAME, "session_key"), (By.CSS_SELECTOR, "input[name='session_key']")],
            "description": "Username/email input field",
            "critical": True,
        },
        "password_field": {
            "primary": (By.ID, "password"),
            "fallback": [(By.NAME, "session_password"), (By.CSS_SELECTOR, "input[name='session_password']")],
            "description": "Password input field",
            "critical": True,
        },
        "submit_button": {
            "primary": (By.XPATH, "//button[@type='submit']"),
            "fallback": [(By.CSS_SELECTOR, "button[type='submit']"), (By.XPATH, "//button[contains(text(), 'Sign in')]")],
            "description": "Login submit button",
            "critical": True,
        },
    },
    
    # ========== MESSAGING ==========
    "messaging": {
        "container": {
            "primary": (By.CSS_SELECTOR, ".msg-overlay-list-bubble"),
            "fallback": [
                (By.CSS_SELECTOR, ".msg-overlay-bubble-header"),
                (By.CSS_SELECTOR, "[data-control-name='overlay.messaging_container']"),
            ],
            "description": "Messaging container/overlay",
            "critical": True,
        },
        "thread_container": {
            "primary": (By.CSS_SELECTOR, ".msg-conversations-container__conversations-list"),
            "fallback": [
                (By.CSS_SELECTOR, "ul.msg-conversations-container__conversations-list"),
                (By.CSS_SELECTOR, "[class*='msg-conversations-container']"),
            ],
            "description": "Thread list container",
            "critical": True,
        },
        "thread_list": {
            "primary": (By.XPATH, "//div[contains(@class, 'msg-conversations-container__convo-item-link')]"),
            "fallback": [
                (By.XPATH, "//li[contains(@class, 'msg-conversation-listitem')]"),
                (By.XPATH, "//div[contains(@class, 'msg-conversation-card')]"),
                (By.XPATH, "//div[contains(@class, 'msg-conversation-listitem__link')]"),
                (By.XPATH, "//div[contains(@class, 'msg-selectable-entity')]"),
                (By.CSS_SELECTOR, ".msg-conversations-container__convo-item-link"),
                (By.CSS_SELECTOR, "[data-control-name='view_conversation']"),
            ],
            "description": "Message thread items",
            "critical": True,
        },
        "load_more_button": {
            "primary": (By.XPATH, "//button[contains(@class, 'artdeco-button') and contains(., 'Load more')]"),
            "fallback": [
                (By.XPATH, "//button[contains(text(), 'Load more')]"),
                (By.CSS_SELECTOR, "button.artdeco-button[aria-label*='Load']"),
            ],
            "description": "Load more messages button",
            "critical": False,
        },
        "view_profile_button": {
            "primary": (By.XPATH, "//button[contains(@aria-label, 'view') and contains(@aria-label, 'profile')]"),
            "fallback": [
                (By.XPATH, "//button[contains(text(), 'View profile')]"),
                (By.XPATH, "//button[contains(@class, 'msg-thread__link-to-profile')]"),
                (By.XPATH, "//a[contains(@class, 'msg-thread__link-to-profile')]"),
                (By.XPATH, "//button[contains(@aria-label, 'View')]"),
                (By.CSS_SELECTOR, "button[aria-label*='View']"),
            ],
            "description": "View profile button in message thread",
            "critical": False,
        },
    },
    
    # ========== CONTACT INFO MODAL ==========
    "contact_modal": {
        "dialog": {
            "primary": (By.XPATH, "//div[@role='dialog']"),
            "fallback": [
                (By.CSS_SELECTOR, "div[role='dialog']"),
                (By.CSS_SELECTOR, ".artdeco-modal"),
            ],
            "description": "Contact info modal dialog",
            "critical": True,
        },
        "email": {
            "primary": (By.XPATH, "//a[contains(@href, 'mailto:')]"),
            "fallback": [
                (By.CSS_SELECTOR, "a[href^='mailto:']"),
                (By.XPATH, "//section//a[contains(@href, 'mailto:')]"),  # Within section
                (By.XPATH, "//section[.//h3[contains(text(), 'Email')]]//a"),  # OLD structure
            ],
            "description": "Email link in contact info",
            "critical": False,
        },
        "phone": {
            "primary": (By.XPATH, "//section[.//h3[text()='Phone']]//span[@class='t-14 t-black t-normal']"),  # OLD structure
            "fallback": [
                (By.XPATH, "//section[.//p[contains(text(), 'Phone')]]//p[contains(@class, 'e327422b')]"),  # NEW structure
                (By.XPATH, "//p[contains(@class, '_1b2d0c42') and contains(text(), '+')]"),  # NEW obfuscated with phone pattern
                (By.XPATH, "//section//span[contains(text(), '+') and contains(text(), '-')]"),  # Phone number pattern
                (By.XPATH, "//section[contains(@class, 'pv-contact-info__contact-type')]//span[contains(@class, 't-14')]"),  # OLD fallback
                (By.CSS_SELECTOR, ".pv-contact-info__contact-type.ci-phone span"),  # OLD fallback
            ],
            "description": "Phone number in contact info",
            "critical": False,
        },
        "linkedin_profile": {
            "primary": (By.XPATH, "//a[contains(@href, 'linkedin.com/in/')]"),
            "fallback": [
                (By.CSS_SELECTOR, "a[href*='linkedin.com/in/']"),
                (By.XPATH, "//section[.//h3[contains(text(), 'Profile')]]//a"),
            ],
            "description": "LinkedIn profile URL",
            "critical": True,
        },
        "dismiss_button": {
            "primary": (By.XPATH, "//button[@aria-label='Dismiss']"),
            "fallback": [
                (By.CSS_SELECTOR, "button[aria-label='Dismiss']"),
                (By.XPATH, "//button[contains(@class, 'artdeco-modal__dismiss')]"),
            ],
            "description": "Dismiss/close button for modal",
            "critical": False,
        },
    },
    
    # ========== PROFILE PAGE ==========
    "profile": {
        "name": {
            "primary": (By.XPATH, "//h2[contains(@class, '_1b2d0c42')]"),  # NEW structure (h2 with obfuscated)
            "fallback": [
                (By.XPATH, "//h2[contains(@class, 'c9b4ed2d')]"),  # NEW structure variant
                (By.TAG_NAME, "h2"),  # Any h2 fallback
                (By.XPATH, "//h1[contains(@class, 'break-words') and contains(@class, 'inline')]"),  # OLD structure
                (By.XPATH, "//h1[contains(@class, 'text-heading-xlarge')]"),  # OLD structure
                (By.CSS_SELECTOR, "h1.text-heading-xlarge"),  # OLD structure
                (By.XPATH, "//h1[contains(@class, 'v-align-middle')]"),  # OLD structure
                (By.XPATH, "//div[contains(@class, 'pv-text-details__left-panel')]//h1"),  # OLD structure
                (By.TAG_NAME, "h1"),  # Any h1 fallback
            ],
            "description": "Profile name (h1 or h2 depending on LinkedIn A/B test)",
            "critical": True,
        },
        "location": {
            "primary": (By.XPATH, "//div[contains(@class, 'pv-text-details')]//p[contains(text(), ',')]"),  # Structure-based (most stable)
            "fallback": [
                (By.XPATH, "//h2/../following-sibling::div//p[contains(text(), ',')]"),  # Structure: p with comma after h2
                (By.CSS_SELECTOR, ".text-body-small.inline.t-black--light.break-words"),  # OLD semantic class
                (By.CSS_SELECTOR, ".pv-top-card__location"),  # OLD semantic class
                (By.XPATH, "//span[contains(@class, 'text-body-small') and contains(@class, 't-black--light')]"),  # OLD fallback
                (By.XPATH, "//p[contains(@class, '_1b2d0c42') and contains(@class, 'e327422b')]"),  # NEW obfuscated
                (By.XPATH, "//p[contains(@class, '_2d40a4a7')]"),  # NEW obfuscated variant
                (By.XPATH, "//p[contains(text(), ',') and string-length(text()) < 100 and string-length(text()) > 5]"),  # Text pattern
            ],
            "description": "Profile location",
            "critical": False,
        },
        "company_text": {
            "primary": (By.XPATH, "//p[contains(@class, '_1b2d0c42') and contains(@class, 'e327422b')]"),  # NEW obfuscated (like "HCLTech")
            "fallback": [
                (By.XPATH, "//button[contains(@aria-label, 'Current company:')]//div[contains(@class, 'inline-show-more-text')]"),  # OLD structure
                (By.XPATH, "//div[contains(@class, 'pv-text-details__left-panel')]//div[contains(@class, 'inline-show-more-text')]"),  # Structure-based
                (By.XPATH, "//div[contains(@class, '_1b2d0c42') and contains(@class, 'f3e5fdd5')]"),  # NEW obfuscated variant
                (By.XPATH, "//p[contains(@class, '_1b2d0c42')]"),  # Simple obfuscated fallback
            ],
            "description": "Company name text",
            "critical": False,
        },
        "company_button": {
            "primary": (By.XPATH, "//button[contains(@aria-label, 'Current company:')]"),
            "fallback": [
                (By.CSS_SELECTOR, "button[aria-label*='Current company']"),
                (By.XPATH, "//div[contains(@class, 'pv-text-details__left-panel')]//button"),
            ],
            "description": "Current company button",
            "critical": False,
        },
        "contact_info_link": {
            "primary": (By.XPATH, "//a[contains(@class, '_190ec6e8') and contains(text(), 'Contact info')]"),  # NEW obfuscated
            "fallback": [
                (By.CSS_SELECTOR, "a#top-card-text-details-contact-info"),  # OLD ID-based
                (By.XPATH, "//a[@id='top-card-text-details-contact-info']"),  # OLD ID-based
                (By.XPATH, "//a[contains(@href, 'overlay/contact-info')]"),  # Structure-based
                (By.XPATH, "//a[contains(text(), 'Contact info')]"),  # Text-based fallback
            ],
            "description": "Contact info link on profile",
            "critical": False,
        },
    },
}


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_selector(category: str, name: str) -> Tuple[str, str]:
    """
    Get primary selector for a given category and name.
    
    Args:
        category: Selector category (e.g., 'login', 'messaging')
        name: Selector name (e.g., 'username_field', 'thread_list')
        
    Returns:
        Tuple of (By type, selector string)
        
    Raises:
        KeyError: If selector not found
    """
    try:
        return SELECTORS[category][name]["primary"]
    except KeyError:
        raise KeyError(f"Selector not found: {category}.{name}")


def get_fallback_selectors(category: str, name: str) -> List[Tuple[str, str]]:
    """
    Get fallback selectors for a given category and name.
    
    Args:
        category: Selector category
        name: Selector name
        
    Returns:
        List of (By type, selector string) tuples
    """
    try:
        return SELECTORS[category][name].get("fallback", [])
    except KeyError:
        return []


def get_all_selectors(category: str, name: str) -> List[Tuple[str, str]]:
    """
    Get primary + all fallback selectors.
    
    Args:
        category: Selector category
        name: Selector name
        
    Returns:
        List of (By type, selector string) tuples, primary first
    """
    primary = get_selector(category, name)
    fallbacks = get_fallback_selectors(category, name)
    return [primary] + fallbacks


def is_critical(category: str, name: str) -> bool:
    """
    Check if a selector is marked as critical.
    
    Args:
        category: Selector category
        name: Selector name
        
    Returns:
        True if critical, False otherwise
    """
    try:
        return SELECTORS[category][name].get("critical", False)
    except KeyError:
        return False


def get_description(category: str, name: str) -> str:
    """
    Get description for a selector.
    
    Args:
        category: Selector category
        name: Selector name
        
    Returns:
        Description string
    """
    try:
        return SELECTORS[category][name].get("description", "No description")
    except KeyError:
        return "Selector not found"


def get_selector_info(category: str, name: str) -> Dict[str, Any]:
    """
    Get complete selector information.
    
    Args:
        category: Selector category
        name: Selector name
        
    Returns:
        Dictionary with all selector info
    """
    try:
        return SELECTORS[category][name]
    except KeyError:
        return {}
