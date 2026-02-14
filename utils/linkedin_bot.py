# utils/linkedin_bot.py
# ============================================
# LINKEDIN CONTACT EXTRACTION BOT
# WITH FULL DEBUG LOGGING
# ============================================

import time
import random
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from utils.logger import log_csv
from utils.browser import setup_browser
from utils.db import insert_contact, bulk_insert_contacts, log_extraction_activity
import yaml
import os
import logging

# Import stealth modules for human-like behavior
from stealth import HumanBehavior, random_pause

# Import Phase 3 modules
from modules import BrowserManager, DiscoveryModule, WorkflowModule, PersistenceModule
from utils.exceptions import BrowserException, NavigationException, ExtractionException
from config.secrets import get_execution_config

# Import Phase 5 metrics
from utils.metrics import ExtractionMetrics

# Import Phase 6 DuckDB
from utils.duckdb_manager import DuckDBManager

# Import centralized selector system
from linkedin_selectors.helpers import (
    find_element_with_fallback,
    get_text_with_fallback,
    click_element_with_fallback
)

logger = logging.getLogger(__name__)

# Load config.yaml
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")

try:
    with open(os.path.abspath(CONFIG_PATH), "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f) or {}
    logger.info(f"Loaded config.yaml: {config_data}")
except FileNotFoundError:
    logger.warning("config.yaml not found, using defaults")
    config_data = {}

NUM_MESSAGES_TO_PROCESS = config_data.get("NUM_MESSAGES_TO_PROCESS", "all")


class LinkedInBot:
    """LinkedIn Contact Extraction Bot with Full Debug Logging."""
    
    def __init__(self, username, password, chrome_profile, employee_id, candidate_id, proxy=None):
        # Credentials
        self.username = username
        self.password = password
        self.chrome_profile = chrome_profile
        self.employee_id = employee_id
        self.candidate_id = candidate_id
        self.proxy = proxy
        
        # Module initialization (driver/wait set in start_browser)
        self.browser_manager = None
        self.driver = None
        self.wait = None
        self.human = HumanBehavior()
        self.discovery = None
        self.workflow = None
        self.persistence = None
        
        # State
        self.main_window = None
        self.num_messages = NUM_MESSAGES_TO_PROCESS
        self.extracted_count = 0
        
        # Execution config (Phase 4)
        self.max_contacts = self._get_max_contacts()
        self.thread_delay_range = self._get_thread_delay_range()
        
        # Metrics tracking (Phase 5)
        self.metrics = ExtractionMetrics()
        
        # DuckDB tracking (Phase 6) - use separate file to avoid IDE locks
        self.duckdb = DuckDBManager(db_path="data/bot_contacts.duckdb")
        self.current_run_id = None
        
        logger.info("=" * 60)
        logger.info("LinkedInBot initialized (Modular Architecture - Phase 6)")
        logger.info(f"   Username: {username}")
        logger.info(f"   Chrome Profile: {chrome_profile}")
        logger.info(f"   Employee ID: {employee_id}")
        logger.info(f"   Candidate ID: {candidate_id}")
        if self.proxy:
            logger.info(f"   Proxy: {self.proxy}")
        logger.info(f"   Messages to process: {self.num_messages}")
        logger.info(f"   Max contacts per run: {self.max_contacts}")
        logger.info(f"   Thread delay range: {self.thread_delay_range[0]}-{self.thread_delay_range[1]}ms")
        logger.info("=" * 60)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup."""
        self.cleanup()

    def cleanup(self):
        """Close browser and release resources."""
        if self.browser_manager:
            try:
                self.browser_manager.close_browser()
                logger.info("[CLEANUP] Browser closed")
            except Exception as e:
                logger.warning(f"[CLEANUP] Error closing browser: {e}")

    def start_browser(self):
        """Start browser using BrowserManager (Phase 4)."""
        try:
            logger.info("[START_BROWSER] Starting with BrowserManager...")
            
            # Initialize BrowserManager
            self.browser_manager = BrowserManager(
                chrome_profile=self.chrome_profile,
                headless=False,
                proxy=self.proxy
            )
            
            # Start browser
            self.driver, self.wait = self.browser_manager.start_browser()
            
            # Initialize other modules now that we have driver/wait
            self.discovery = DiscoveryModule(self.driver, self.wait, self.human)
            self.workflow = WorkflowModule(self.driver, self.wait, self.human)
            self.persistence = PersistenceModule(self.employee_id, self.candidate_id)
            
            logger.info("[START_BROWSER] ✅ All modules initialized successfully")
            logger.info(f"[START_BROWSER]    - BrowserManager")
            logger.info(f"[START_BROWSER]    - DiscoveryModule")
            logger.info(f"[START_BROWSER]    - WorkflowModule")
            logger.info(f"[START_BROWSER]    - PersistenceModule")
            
        except BrowserException as e:
            logger.error(f"[START_BROWSER] Failed: {e}")
            raise
    
    def _get_max_contacts(self) -> int:
        """Get max contacts limit from config (Phase 4)."""
        try:
            config = get_execution_config()
            return config.get('MAX_CONTACTS_PER_RUN', 50)
        except Exception as e:
            logger.warning(f"Failed to load execution config: {e}, using default")
            return 50  # Default
    
    def _get_thread_delay_range(self) -> tuple:
        """Get thread delay range from config (Phase 4)."""
        try:
            config = get_execution_config()
            return (
                config.get('MIN_THREAD_DELAY_MS', 2000),
                config.get('MAX_THREAD_DELAY_MS', 5000)
            )
        except Exception as e:
            logger.warning(f"Failed to load execution config: {e}, using defaults")
            return (2000, 5000)  # Defaults
    
    def _apply_thread_delay(self):
        """Apply rate limiting between threads (Phase 4)."""
        min_delay, max_delay = self.thread_delay_range
        delay_ms = random.randint(min_delay, max_delay)
        delay_s = delay_ms / 1000.0
        
        logger.debug(f"[RATE_LIMIT] Waiting {delay_s:.2f}s before next thread")
        time.sleep(delay_s)
    
    def _recover_from_error(self):
        """Recover from extraction error (Phase 4)."""
        try:
            # Close any extra windows
            for w in self.driver.window_handles:
                if w != self.main_window:
                    self.driver.switch_to.window(w)
                    self.driver.close()
            
            # Return to main window
            self.driver.switch_to.window(self.main_window)
            logger.debug("[RECOVERY] Returned to main window")
            
        except Exception as e:
            logger.warning(f"[RECOVERY] Failed: {e}")

    def login(self):
        """Login to LinkedIn or verify session."""
        try:
            logger.info(f"[LOGIN] Checking login for {self.username}...")
            
            self.driver.get("https://www.linkedin.com/feed/")
            time.sleep(5)
            
            # Check if logged in (more robust)
            is_logged_in = False
            try:
                current_url = self.driver.current_url
                logger.info(f"[LOGIN] Current URL: {current_url}")
                
                
                # Check for multiple indicators of being logged in (from actual LinkedIn HTML)
                login_indicators = [
                    (By.ID, "global-nav"),  # Main header
                    (By.CLASS_NAME, "global-nav__content"),  # Header content wrapper
                    (By.ID, "global-nav-search"),  # Search container
                    (By.ID, "global-nav-typeahead"),  # Search input
                    (By.CLASS_NAME, "global-nav__me"),  # Me dropdown
                    (By.CLASS_NAME, "global-nav__me-photo"),  # Profile picture
                    (By.CLASS_NAME, "global-nav__primary-items"),  # Nav items (Home, Jobs, etc)
                ]
                
                for by, selector in login_indicators:
                    try:
                        if self.driver.find_elements(by, selector):
                            is_logged_in = True
                            logger.info(f"[LOGIN] Found login indicator: {selector}")
                            break
                    except:
                        continue
                
                if not is_logged_in and "feed" in current_url:
                    # Double check if on feed URL but elements not found yet
                    logger.info("[LOGIN] On feed URL but indicators missing - waiting longer...")
                    time.sleep(8)  # Wait longer for page to fully load
                    
                    # Try one more time with explicit wait
                    for by, selector in login_indicators:
                        try:
                            if self.driver.find_elements(by, selector):
                                is_logged_in = True
                                logger.info(f"[LOGIN] Found login indicator after extended wait: {selector}")
                                break
                        except:
                            continue
                            
            except Exception as e:
                logger.debug(f"[LOGIN] Check failed: {e}")

            if is_logged_in:
                logger.info("[LOGIN] Already logged in (persistent session)")
                return
            
            # Login required
            logger.info("[LOGIN] Not logged in, performing login...")
            
            # Check current URL - if still on feed, we might actually be logged in
            current_url = self.driver.current_url
            if "feed" in current_url and "login" not in current_url:
                logger.warning("[LOGIN] Still on feed page but no indicators found - assuming logged in")
                self.driver.save_screenshot('debug_feed_no_indicators.png')
                logger.info("[LOGIN] Screenshot saved to debug_feed_no_indicators.png")
                return
            
            # Check for "Welcome Back" screens (multiple scenarios)
            is_welcome_back_password = False
            is_account_selection = False
            
            try:
                # Check for account selection screen (multiple member__profile divs)
                account_profiles = self.driver.find_elements(By.CLASS_NAME, "member__profile")
                if len(account_profiles) > 1:
                    is_account_selection = True
                    logger.info(f"[LOGIN] Account selection screen detected ({len(account_profiles)} accounts)")
                elif len(account_profiles) == 1:
                    # Single account shown - check if password field exists
                    try:
                        self.driver.find_element(By.ID, "password")
                        is_welcome_back_password = True
                        logger.info("[LOGIN] Welcome Back screen (password-only) detected")
                    except:
                        # Profile shown but no password field yet - might need to click
                        is_account_selection = True
                        logger.info("[LOGIN] Single account profile found - will click to proceed")
            except:
                pass
            
            # Handle account selection screen
            if is_account_selection:
                try:
                    logger.info("[LOGIN] Account selection screen detected - matching by email...")
                    
                    # Get all account profiles
                    account_profiles = self.driver.find_elements(By.CLASS_NAME, "member__profile")
                    logger.info(f"[LOGIN] Found {len(account_profiles)} account profiles")
                    
                    # Extract username from config (email address)
                    target_email = self.username.lower()
                    logger.info(f"[LOGIN] Looking for account matching: {target_email}")
                    
                    matched_profile = None
                    
                    # Loop through profiles to find matching email
                    for profile in account_profiles:
                        try:
                            # Look for email in profile__handle
                            email_element = profile.find_element(By.CLASS_NAME, "profile__handle")
                            email_text = email_element.text.lower()
                            
                            # Check if configured email matches (handles partial masking like "g*****@gmail.com")
                            if target_email in email_text or any(part in email_text for part in target_email.split('@')):
                                matched_profile = profile
                                logger.info(f"[LOGIN] ✅ Matched account: {email_text}")
                                break
                        except:
                            continue
                    
                    if matched_profile:
                        logger.info("[LOGIN] Clicking on matched account profile...")
                        self.human.human_click(self.driver, matched_profile)
                        self.human.random_pause(2, 3)
                        
                        # After clicking, check if password field appears
                        try:
                            self.driver.find_element(By.ID, "password")
                            is_welcome_back_password = True
                            logger.info("[LOGIN] Password field appeared after account selection")
                        except:
                            # Might have logged in directly
                            current_url = self.driver.current_url
                            if "feed" in current_url:
                                logger.info("[LOGIN] Logged in directly after account selection!")
                                return
                    else:
                        logger.warning(f"[LOGIN] ⚠️ Could not find account matching {target_email}")
                        logger.warning("[LOGIN] Clicking first account as fallback...")
                        first_profile = self.driver.find_element(By.CLASS_NAME, "member__profile")
                        self.human.human_click(self.driver, first_profile)
                        self.human.random_pause(2, 3)
                        
                except Exception as e:
                    logger.warning(f"[LOGIN] Failed to click account profile: {e}")
            
            # Handle Welcome Back password-only screen
            if is_welcome_back_password:
                logger.info("[LOGIN] Filling password on Welcome Back screen...")
                try:
                    password_field = self.wait.until(EC.presence_of_element_located((By.ID, 'password')))
                    self.human.human_type(password_field, self.password)
                    
                    # Click Sign in button
                    logger.info("[LOGIN] Clicking Sign in...")
                    submit_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
                    self.human.human_click(self.driver, submit_button)
                    
                    # Wait for login
                    for i in range(30):
                        current_url = self.driver.current_url
                        if "feed" in current_url and "login" not in current_url:
                            logger.info("[LOGIN] Login successful via Welcome Back")
                            return
                        if "challenge" in current_url or "checkpoint" in current_url:
                            logger.warning("[LOGIN] VERIFICATION REQUIRED - complete manually")
                            while "feed" not in self.driver.current_url:
                                self.human.random_pause(3, 5)
                            return
                        self.human.random_pause(1, 2)
                    
                    logger.info("[LOGIN] Welcome Back login completed")
                    return
                except Exception as e:
                    logger.error(f"[LOGIN] Failed on Welcome Back screen: {e}")
                    self.driver.save_screenshot('debug_welcome_back_error.png')
                    raise
            
            
            # Standard login flow (username + password)
            if not is_welcome_back_password and not is_account_selection:
                try:
                    self.driver.find_element(By.ID, "username")
                    logger.info("[LOGIN] Username field found on current page")
                except:
                    logger.info("[LOGIN] Navigating to login page...")
                    self.driver.get("https://www.linkedin.com/login")
                    self.human.random_pause(2, 3)  # Wait longer after navigation
                    
                    # Check if we got redirected (might already be logged in)
                    new_url = self.driver.current_url
                    logger.info(f"[LOGIN] After navigation, URL is: {new_url}")
                    
                    if "feed" in new_url:
                        logger.info("[LOGIN] Redirected to feed - already logged in!")
                        return

                # Fill username if not welcome back
                logger.info("[LOGIN] Filling username...")
                try:
                    username_field = self.wait.until(EC.presence_of_element_located((By.ID, 'username')))
                    self.human.human_type(username_field, self.username)
                except Exception as e:
                    logger.error(f"[LOGIN] Failed to find/fill username field: {e}")
                    self.driver.save_screenshot('debug_login_username_error.png')
                    raise
            
            # Fill password (common for both)
            logger.info("[LOGIN] Filling password...")
            password_field = self.wait.until(EC.presence_of_element_located((By.ID, 'password')))
            self.human.human_type(password_field, self.password)
            
            logger.info("[LOGIN] Clicking submit...")
            submit_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            self.human.human_click(self.driver, submit_button)
            
            # Wait for login
            for i in range(30):
                current_url = self.driver.current_url
                logger.debug(f"[LOGIN] Waiting... URL: {current_url}")
                
                if "feed" in current_url and "login" not in current_url:
                    logger.info("[LOGIN] Login successful")
                    break
                    
                if "challenge" in current_url or "checkpoint" in current_url:
                    logger.warning("[LOGIN] VERIFICATION REQUIRED - complete manually")
                    while "feed" not in self.driver.current_url:
                        self.human.random_pause(3, 5)
                    break
                    
                self.human.random_pause(1, 2)  # Natural waiting

            self.human.random_pause(2, 4)  # Post-login pause
                
        except Exception as e:
            logger.error(f"[LOGIN] Failed: {e}", exc_info=True)
            self.driver.save_screenshot('debug_login.png')
            raise

    def go_to_messages(self):
        """Navigate to messages using DiscoveryModule (Phase 4)."""  
        try:
            logger.info("[GO_TO_MESSAGES] Using DiscoveryModule...")
            
            # Navigate to messages
            self.discovery.navigate_to_messages()
            
            # Store main window handle
            self.main_window = self.driver.current_window_handle
            logger.info(f"[GO_TO_MESSAGES] Main window: {self.main_window}")
            
            # Load threads with limit
            max_threads = None if self.num_messages == "all" else int(self.num_messages)
            # Apply max_contacts limit as well
            if max_threads is None:
                max_threads = self.max_contacts
            else:
                max_threads = min(max_threads, self.max_contacts)
            
            self.discovery.load_all_threads(
                max_scrolls=20,
                max_threads=max_threads
            )
            
            thread_count = self.discovery.get_thread_count()
            logger.info(f"[GO_TO_MESSAGES] ✅ Loaded {thread_count} threads")
            
        except NavigationException as e:
            logger.error(f"[GO_TO_MESSAGES] Failed: {e}")
            raise
        except Exception as e:
            logger.error(f"[GO_TO_MESSAGES] Unexpected error: {e}", exc_info=True)
            raise NavigationException(f"Failed to navigate to messages: {e}")

    def _scroll_to_load_threads(self):
        """DEPRECATED: Now handled by DiscoveryModule.load_all_threads() (Phase 4)"""
        logger.warning("[SCROLL] This method is deprecated. Use DiscoveryModule instead.")
        pass

    def _extract_contact_modal(self):
        """Extract email, phone from contact modal using centralized selector system."""
        info = {"email": None, "phone": None, "public_linkedin": None}
        
        logger.debug("[MODAL] Attempting to open contact info modal...")
        
        try:
            # Click contact info button using centralized selector
            clicked = click_element_with_fallback(
                self.driver,
                category="profile",
                name="contact_info_link",
                timeout=5
            )
            
            if not clicked:
                logger.debug("[MODAL] Contact info button not found")
                return info
            
            self.human.random_pause(2, 3)  # Wait for modal to open
            
            # Wait for modal using centralized selector
            modal = find_element_with_fallback(
                self.driver,
                category="contact_modal",
                name="dialog",
                timeout=5
            )
            
            if not modal:
                logger.debug("[MODAL] Modal not found after wait")
                return info
            
            logger.debug("[MODAL] Modal found")
            
            # Extract email using centralized selector
            email_element = find_element_with_fallback(
                self.driver,
                category="contact_modal",
                name="email",
                parent=modal,
                timeout=0
            )
            
            if email_element:
                try:
                    email_text = email_element.text.strip() or email_element.get_attribute('href').replace('mailto:', '')
                    if email_text and '@' in email_text:
                        info['email'] = email_text
                        logger.debug(f"[MODAL] Found email: {info['email']}")
                except:
                    pass
            
            if not info['email']:
                logger.debug("[MODAL] No email found")
            
            # Extract phone using centralized selector
            phone_element = find_element_with_fallback(
                self.driver,
                category="contact_modal",
                name="phone",
                parent=modal,
                timeout=0
            )
            
            if phone_element:
                try:
                    phone_text = phone_element.text.strip()
                    if phone_text and ('+' in phone_text or len(phone_text) >= 10):
                        info['phone'] = phone_text
                        logger.debug(f"[MODAL] Found phone: {info['phone']}")
                except:
                    pass
            
            if not info['phone']:
                logger.debug("[MODAL] No phone found")
            
            # Extract profile URL using centralized selector
            profile_element = find_element_with_fallback(
                self.driver,
                category="contact_modal",
                name="linkedin_profile",
                parent=modal,
                timeout=0
            )
            
            if profile_element:
                try:
                    info['public_linkedin'] = profile_element.get_attribute("href")
                    logger.debug(f"[MODAL] Found profile URL: {info['public_linkedin']}")
                except:
                    pass
            
            # Close modal using centralized selector
            close_clicked = click_element_with_fallback(
                self.driver,
                category="contact_modal",
                name="dismiss_button",
                timeout=2
            )
            
            if close_clicked:
                logger.debug("[MODAL] Modal closed")
                self.human.random_pause(0.5, 1)
            else:
                logger.debug("[MODAL] Could not close modal")

        except Exception as e:
            logger.debug(f"[MODAL] Error: {e}")
        
        return info

    def _extract_company(self):
        """Extract company name using centralized selector system."""
        logger.debug("[COMPANY] Attempting to extract company...")
        
        # Try centralized selector system first
        company = get_text_with_fallback(
            self.driver,
            category="profile",
            name="company_text",
            timeout=0
        )
        
        if company and company != "LinkedIn Member":
            logger.debug(f"[COMPANY] Found: {company}")
            return company
        
        # Try extracting from aria-label as fallback
        try:
            btn = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Current company:')]")
            label = btn.get_attribute('aria-label')
            company = label.replace('Current company:', '').split('.')[0].strip()
            if company:
                logger.debug(f"[COMPANY] Found from aria-label: {company}")
                return company
        except:
            pass
        
        logger.debug("[COMPANY] Not found")
        return None

    def _safe_get_text(self, selectors):
        """Try selectors to get text (supports CSS and XPath)."""
        for sel in selectors:
            try:
                by_type = By.XPATH if sel.startswith("//") else By.CSS_SELECTOR
                el = self.driver.find_element(by_type, sel)
                text = el.text.strip()
                if text:
                    logger.debug(f"[GET_TEXT] Found with '{sel}': {text[:50]}")
                    return text
            except:
                continue
        return None
    
    def _get_profile_url_from_thread(self):
        """Get profile URL from current thread (Phase 4.2)."""
        profile_selectors = [
            "a.msg-thread__link-to-profile",
            ".msg-thread__link-to-profile",
            "a[href*='/in/']"
        ]
        
        for sel in profile_selectors:
            try:
                el = self.driver.find_element(By.CSS_SELECTOR, sel)
                href = el.get_attribute("href")
                if href and '/in/' in href:
                    return href
            except:
                continue
        return None
    
    def _open_profile_tab(self, profile_url):
        """Open profile in new tab (Phase 4.2)."""
        try:
            original_windows = self.driver.window_handles
            self.driver.execute_script("window.open(arguments[0]);", profile_url)
            self.human.random_pause(2, 3)
            
            new_windows = [w for w in self.driver.window_handles if w not in original_windows]
            
            if not new_windows:
                return False
            
            self.driver.switch_to.window(new_windows[0])
            self.human.random_pause(1, 2)
            return True
        except Exception as e:
            logger.error(f"[PROFILE_TAB] Failed to open: {e}")
            return False
    
    def _close_profile_tab(self):
        """Close profile tab and return to main window (Phase 4.2)."""
        try:
            self.driver.close()
            self.driver.switch_to.window(self.main_window)
            self.human.random_pause(0.5, 1)
        except Exception as e:
            logger.warning(f"[PROFILE_TAB] Failed to close: {e}")
    
    def _extract_from_profile_page(self, thread_num, profile_url):
        """Extract contact data from profile page (Phase 4.2)."""
        try:
            # Wait for profile page to load (critical for internal ID URLs)
            logger.info(f"[THREAD {thread_num}] Waiting for profile page to load...")
            
            # Verify we're on a profile page
            current_url = self.driver.current_url
            if "/in/" not in current_url:
                logger.warning(f"[THREAD {thread_num}] Not on profile page: {current_url}")
                return None
            
            # Wait for page to render (internal IDs take longer)
            time.sleep(4)  # Give page time to fully render
            
            # Wait for name element to be present (h1 OR h2 - LinkedIn A/B tests different structures)
            try:
                # Try h1 first (old structure)
                try:
                    self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
                    logger.debug(f"[THREAD {thread_num}] Profile page loaded (h1 found)")
                except:
                    # Try h2 (new structure)
                    self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "h2")))
                    logger.debug(f"[THREAD {thread_num}] Profile page loaded (h2 found)")
            except:
                logger.warning(f"[THREAD {thread_num}] Timeout waiting for profile page")
                # Take screenshot for debugging
                self.driver.save_screenshot(f'debug_profile_load_thread_{thread_num}.png')
                logger.info(f"[THREAD {thread_num}] Screenshot saved for debugging")
            
            
            # Extract name using centralized selector system
            full_name = get_text_with_fallback(
                self.driver,
                category="profile",
                name="name",
                timeout=0
            )
            
            if not full_name or full_name == "LinkedIn Member":
                logger.warning(f"[THREAD {thread_num}] Invalid name '{full_name}'")
                return None
            
            logger.info(f"[THREAD {thread_num}] Name: {full_name}")
            
            # Extract company
            company = self._extract_company()
            logger.info(f"[THREAD {thread_num}] Company: {company or 'N/A'}")
            
            # Extract location using centralized selector system
            location = get_text_with_fallback(
                self.driver,
                category="profile",
                name="location",
                timeout=0
            )
            logger.info(f"[THREAD {thread_num}] Location: {location or 'N/A'}")
            
            # Extract contact info
            contact_info = self._extract_contact_modal()
            logger.info(f"[THREAD {thread_num}] Email: {contact_info.get('email') or 'N/A'}")
            logger.info(f"[THREAD {thread_num}] Phone: {contact_info.get('phone') or 'N/A'}")
            
            # Generate IDs
            linkedin_internal_id = profile_url.rstrip("/").split("/")[-1].split('?')[0]
            linkedin_id = linkedin_internal_id
            
            current_url = self.driver.current_url
            if "/in/" in current_url:
                slug = current_url.split("/in/")[-1].split('?')[0].rstrip('/')
                if slug and len(slug) > 5:
                    linkedin_id = slug
            
            logger.info(f"[THREAD {thread_num}] LinkedIn ID: {linkedin_id}")
            
            # Return contact data
            return {
                "full_name": full_name,
                "source_email": self.username,
                "email": contact_info.get('email'),
                "phone": contact_info.get('phone'),
                "linkedin_id": linkedin_id,
                "linkedin_internal_id": linkedin_internal_id,
                "company_name": company,
                "location": location,
                "job_source": "Bot Linkedin Message Extraction",
                "profile_url": profile_url,
                "extraction_date": datetime.now().strftime("%Y-%m-%d")
            }
            
        except Exception as e:
            logger.error(f"[THREAD {thread_num}] Extraction error: {e}", exc_info=True)
            return None
    
    def _log_contact_to_csv(self, contact_data):
        """Log contact to CSV file (Phase 4.2)."""
        try:
            csv_row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                contact_data.get('source_email', ''),
                contact_data.get('full_name', ''),
                contact_data.get('company_name', ''),
                contact_data.get('location', ''),
                contact_data.get('email', ''),
                contact_data.get('phone', ''),
                contact_data.get('profile_url', ''),
                ""
            ]
            
            csv_success = log_csv("logs/extracted_contacts.csv", csv_row)
            if csv_success:
                logger.debug("[CSV] Logged successfully")
            else:
                logger.warning("[CSV] Failed to log")
        except Exception as e:
            logger.error(f"[CSV] Exception: {e}", exc_info=True)

    def extract_recent_contacts(self):
        """Extract contacts using modular architecture with metrics (Phase 5.1)."""
        logger.info("=" * 70)
        logger.info("[EXTRACTION] STARTING (Modular Architecture - Phase 5)")
        logger.info("=" * 70)
        
        # Start metrics tracking
        self.metrics.start_extraction()
        
        # Stats
        successful = 0
        skipped_no_profile = 0
        skipped_invalid_name = 0
        errors = 0
        consecutive_errors = 0
        contacts_to_insert = []
        contacts_summary = []
        
        try:
            # Get threads from DiscoveryModule
            threads = self.discovery.get_thread_elements()
            self.metrics.increment_threads_discovered(len(threads))
            logger.info(f"[EXTRACTION] Found {len(threads)} threads")
            
            if not threads:
                logger.error("[EXTRACTION] No threads found!")
                self.driver.save_screenshot('debug_no_threads.png')
                return []
            
            # Determine how many to process
            total = len(threads)
            if self.num_messages != "all":
                total = min(total, int(self.num_messages))
            
            # Apply max_contacts limit (Phase 4 execution control)
            total = min(total, self.max_contacts)
            logger.info(f"[EXTRACTION] Will process {total} threads (limit: {self.max_contacts})")
            
            # Process each thread
            for i in range(total):
                logger.info("-" * 60)
                logger.info(f"[THREAD {i+1}/{total}] Processing...")
                logger.info("-" * 60)
                
                try:
                    # Re-fetch threads (stale element protection)
                    threads = self.discovery.get_thread_elements()
                    if i >= len(threads):
                        logger.warning(f"[THREAD {i+1}] Not found after re-fetch")
                        continue
                    
                    thread = threads[i]
                    
                    # Click thread using WorkflowModule
                    logger.info(f"[THREAD {i+1}] Clicking thread...")
                    if not self.workflow.click_thread(thread):
                        logger.warning(f"[THREAD {i+1}] Failed to click thread")
                        errors += 1
                        consecutive_errors += 1
                        continue
                    
                    # Reset consecutive errors on success
                    consecutive_errors = 0
                    self.metrics.reset_consecutive_errors()
                    
                    # Find profile link
                    logger.info(f"[THREAD {i+1}] Looking for profile link...")
                    profile_url = self._get_profile_url_from_thread()
                    
                    if not profile_url:
                        logger.warning(f"[THREAD {i+1}] No profile link found - SKIPPING")
                        skipped_no_profile += 1
                        self.metrics.increment_skipped_no_profile()
                        continue
                    
                    logger.info(f"[THREAD {i+1}] Found profile URL: {profile_url}")
                    
                    # Open profile in new tab
                    if not self._open_profile_tab(profile_url):
                        logger.warning(f"[THREAD {i+1}] Failed to open profile tab")
                        errors += 1
                        consecutive_errors += 1
                        continue
                    
                    # Extract contact data from profile
                    contact_data = self._extract_from_profile_page(i+1, profile_url)
                    
                    if not contact_data:
                        logger.warning(f"[THREAD {i+1}] Failed to extract contact data")
                        skipped_invalid_name += 1
                        self.metrics.increment_skipped_invalid_name()
                        self._close_profile_tab()
                        continue
                    
                    # Log to CSV
                    self._log_contact_to_csv(contact_data)
                    
                    # Store to DuckDB (Phase 6)
                    if self.current_run_id:
                        try:
                            contact_id = self.duckdb.insert_contact(self.current_run_id, contact_data)
                            logger.debug(f"[DUCKDB] Stored contact {contact_id}")
                        except Exception as e:
                            logger.warning(f"[DUCKDB] Failed to store contact: {e}")
                    
                    # Collect for bulk insert
                    contacts_to_insert.append(contact_data)
                    contacts_summary.append((contact_data['full_name'], contact_data.get('company_name')))

                    successful += 1

                    self.metrics.increment_contacts_extracted()
                    self.metrics.increment_threads_processed()
                    
                    logger.info(f"[THREAD {i+1}] ✅ SUCCESS: {contact_data['full_name']}")
                    
                    # Close profile tab
                    self._close_profile_tab()
                    
                    # Rate limiting (Phase 4 execution control)
                    self._apply_thread_delay()
                    self.metrics.increment_rate_limit_delays()
                    
                except ExtractionException as e:
                    logger.warning(f"[THREAD {i+1}] Extraction failed: {e}")
                    errors += 1
                    consecutive_errors += 1
                    self.metrics.increment_errors()
                    self.metrics.increment_consecutive_errors()
                    self._recover_from_error()
                    self.metrics.increment_error_recoveries()
                    
                    # Check consecutive error limit
                    if consecutive_errors >= 5:
                        logger.error(f"[EXTRACTION] Too many consecutive errors ({consecutive_errors}), stopping")
                        break
                    continue
                
                except Exception as e:
                    logger.error(f"[THREAD {i+1}] Unexpected error: {e}", exc_info=True)
                    errors += 1
                    consecutive_errors += 1
                    self.metrics.increment_errors()
                    self.metrics.increment_consecutive_errors()
                    self._recover_from_error()
                    self.metrics.increment_error_recoveries()
                    
                    # Check consecutive error limit
                    if consecutive_errors >= 5:
                        logger.error(f"[EXTRACTION] Too many consecutive errors ({consecutive_errors}), stopping")
                        break
                    continue
        
        except Exception as e:
            logger.error(f"[EXTRACTION] FATAL ERROR: {e}", exc_info=True)
        
        # Bulk insert using PersistenceModule (Phase 4)
        inserted_count = 0  # Track actual inserted count
        if contacts_to_insert:
            logger.info("=" * 60)
            logger.info(f"[BULK_INSERT] Inserting {len(contacts_to_insert)} contacts via PersistenceModule...")
            logger.info("=" * 60)
            
            try:
                inserted_count = self.persistence.bulk_insert_contacts(contacts_to_insert)
                self.metrics.increment_contacts_inserted(inserted_count)
                logger.info(f"[BULK_INSERT] ✅ Successfully inserted {inserted_count} contacts")
            except Exception as e:
                logger.error(f"[BULK_INSERT] Failed: {e}", exc_info=True)
        else:
            logger.info("[BULK_INSERT] No contacts to insert")
        
        # Log activity using PersistenceModule (Phase 4)
        # Only log if contacts were actually inserted (not just extracted)
        if inserted_count > 0:
            logger.info("=" * 60)
            logger.info("[EXTRACTION] Logging activity via PersistenceModule...")
            
            try:
                self.persistence.log_activity(
                    action="contact_extraction",
                    details=f"Inserted {inserted_count} contacts from {successful} extracted ({total} threads)",
                    activity_count=inserted_count  # Use actual inserted count
                )
                logger.info("[EXTRACTION] ✅ Activity logged successfully")
            except Exception as e:
                logger.error(f"[EXTRACTION] Activity logging failed: {e}", exc_info=True)
        
        # End metrics tracking and log summary
        self.metrics.end_extraction()
        self.metrics.log_summary()
        
        # Summary
        self.extracted_count = successful
        
        logger.info("=" * 70)
        logger.info("[EXTRACTION] LEGACY SUMMARY (for compatibility)")
        logger.info("=" * 70)
        logger.info(f"   Total threads processed: {total}")
        logger.info(f"   Successful extractions:  {successful}")
        logger.info(f"   Skipped (no profile):    {skipped_no_profile}")
        logger.info(f"   Skipped (invalid name):  {skipped_invalid_name}")
        logger.info(f"   Errors:                  {errors}")
        logger.info("=" * 70)
        
        return contacts_summary

    def run(self):
        """Main execution with DuckDB tracking (Phase 6)."""
        logger.info("=" * 70)
        logger.info("[RUN] STARTING BOT (Modular Architecture - Phase 6)")
        logger.info("=" * 70)
        
        try:
            # Connect to DuckDB and start run tracking
            self.duckdb.connect()
            self.current_run_id = self.duckdb.start_run(
                self.employee_id,
                self.candidate_id,
                self.username
            )
            logger.info(f"[DUCKDB] Started run {self.current_run_id}")
            
            self.start_browser()
            self.login()
            self.go_to_messages()
            self.extract_recent_contacts()
            
            # End run with success status
            self.duckdb.end_run(self.current_run_id, self.metrics.get_summary(), 'completed')
            logger.info(f"[DUCKDB] Ended run {self.current_run_id} successfully")
            
        except Exception as e:
            logger.error(f"[RUN] BOT ERROR: {e}", exc_info=True)
            # End run with failed status
            if self.current_run_id:
                try:
                    self.duckdb.end_run(self.current_run_id, self.metrics.get_summary(), 'failed')
                except:
                    pass
            raise  # Re-raise to let MultiAccountManager know it failed
            
        finally:
            # CRITICAL: Always close browser
            self.cleanup()
            
            # Close DuckDB connection
            try:
                self.duckdb.close()
                logger.info("[DUCKDB] Connection closed")
            except:
                pass
        
        logger.info("=" * 70)
        logger.info("[RUN] BOT FINISHED")
        logger.info("=" * 70)