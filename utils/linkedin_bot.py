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
from utils.db import insert_contact, log_extraction_activity
import yaml
import os
import logging

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
    
    def __init__(self, username, password, chrome_profile, employee_id, candidate_id):
        self.username = username
        self.password = password
        self.chrome_profile = chrome_profile
        self.employee_id = employee_id
        self.candidate_id = candidate_id
        self.driver = None
        self.wait = None
        self.main_window = None
        self.num_messages = NUM_MESSAGES_TO_PROCESS
        self.extracted_count = 0
        
        logger.info("=" * 60)
        logger.info("LinkedInBot initialized")
        logger.info(f"   Username: {username}")
        logger.info(f"   Chrome Profile: {chrome_profile}")
        logger.info(f"   Employee ID: {employee_id}")
        logger.info(f"   Candidate ID: {candidate_id}")
        logger.info(f"   Messages to process: {self.num_messages}")
        logger.info("=" * 60)

    def start_browser(self):
        """Start browser with profile."""
        logger.info("[START_BROWSER] Starting...")
        self.driver, self.wait = setup_browser(self.chrome_profile)
        logger.info(f"[START_BROWSER] Browser started: {self.chrome_profile}")

    def login(self):
        """Login to LinkedIn or verify session."""
        try:
            logger.info(f"[LOGIN] Checking login for {self.username}...")
            
            self.driver.get("https://www.linkedin.com/feed/")
            time.sleep(5)
            
            # Check if logged in
            is_logged_in = False
            try:
                current_url = self.driver.current_url
                logger.info(f"[LOGIN] Current URL: {current_url}")
                
                if "feed" in current_url and "login" not in current_url:
                    self.driver.find_element(By.ID, "global-nav")
                    is_logged_in = True
                    logger.info("[LOGIN] Found global-nav - user is logged in")
            except Exception as e:
                logger.debug(f"[LOGIN] Check failed: {e}")

            if is_logged_in:
                logger.info("[LOGIN] Already logged in (persistent session)")
                return
            
            # Login required
            logger.info("[LOGIN] Not logged in, performing login...")
            
            try:
                self.driver.find_element(By.ID, "username")
                logger.info("[LOGIN] Found username field on current page")
            except:
                logger.info("[LOGIN] Navigating to login page...")
                self.driver.get("https://www.linkedin.com/login")
                time.sleep(2)
            
            # Fill credentials
            logger.info("[LOGIN] Filling credentials...")
            username_field = self.wait.until(EC.presence_of_element_located((By.ID, 'username')))
            username_field.clear()
            username_field.send_keys(self.username)
            
            password_field = self.driver.find_element(By.ID, 'password')
            password_field.clear()
            password_field.send_keys(self.password)
            
            logger.info("[LOGIN] Clicking submit...")
            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            
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
                        time.sleep(5)
                    break
                    
                time.sleep(2)

            time.sleep(random.uniform(3, 5))
                
        except Exception as e:
            logger.error(f"[LOGIN] Failed: {e}", exc_info=True)
            self.driver.save_screenshot('debug_login.png')
            raise

    def go_to_messages(self):
        """Navigate to messages."""
        logger.info("[GO_TO_MESSAGES] Navigating...")
        self.driver.get("https://www.linkedin.com/messaging/")
        time.sleep(5)
        
        current_url = self.driver.current_url
        logger.info(f"[GO_TO_MESSAGES] Current URL: {current_url}")
        
        if "login" in current_url:
            raise Exception("Session expired - restart bot")

        self.main_window = self.driver.current_window_handle
        logger.info(f"[GO_TO_MESSAGES] Main window handle: {self.main_window}")
        
        self._scroll_to_load_threads()

    def _scroll_to_load_threads(self):
        """Scroll to load threads."""
        logger.info("[SCROLL] Loading threads...")
        
        try:
            selectors = [
                ".msg-conversations-container__conversations-list",
                "ul.msg-conversations-container__conversations-list",
            ]
            
            container = None
            for sel in selectors:
                try:
                    container = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if container:
                        logger.info(f"[SCROLL] Found container: {sel}")
                        break
                except:
                    continue
            
            if not container:
                logger.warning("[SCROLL] Message container not found")
                return

            last_height = self.driver.execute_script("return arguments[0].scrollHeight", container)
            
            for scroll_count in range(20):
                threads = self.driver.find_elements(
                    By.XPATH, "//div[contains(@class, 'msg-conversations-container__convo-item-link')]"
                )
                
                logger.debug(f"[SCROLL] Scroll {scroll_count+1}: Found {len(threads)} threads")
                
                if self.num_messages != "all" and len(threads) >= int(self.num_messages):
                    break

                self.driver.execute_script("arguments[0].scrollTo(0, arguments[0].scrollHeight);", container)
                time.sleep(2)
                
                new_height = self.driver.execute_script("return arguments[0].scrollHeight", container)
                if new_height == last_height:
                    logger.info("[SCROLL] Reached end of list")
                    break
                last_height = new_height

            final_threads = self.driver.find_elements(
                By.XPATH, "//div[contains(@class, 'msg-conversations-container__convo-item-link')]"
            )
            logger.info(f"[SCROLL] Loaded {len(final_threads)} threads")
            
        except Exception as e:
            logger.error(f"[SCROLL] Error: {e}", exc_info=True)

    def _extract_contact_modal(self):
        """Extract email, phone from contact modal."""
        info = {"email": None, "phone": None, "public_linkedin": None}
        
        logger.debug("[MODAL] Attempting to open contact info modal...")
        
        try:
            # Click contact info
            clicked = False
            selectors = [
                "//a[@id='top-card-text-details-contact-info']", 
                "//a[contains(@href, '/overlay/contact-info/')]"
            ]
            
            for sel in selectors:
                try:
                    btn = self.driver.find_element(By.XPATH, sel)
                    if btn.is_displayed():
                        self.driver.execute_script("arguments[0].click();", btn)
                        clicked = True
                        logger.debug(f"[MODAL] Clicked contact info button: {sel}")
                        break
                except:
                    continue
            
            if not clicked:
                logger.debug("[MODAL] Contact info button not found")
                return info
            
            time.sleep(3)
            
            # Wait for modal
            try:
                modal = self.wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']")))
                logger.debug("[MODAL] Modal found")
            except:
                logger.debug("[MODAL] Modal not found after wait")
                return info

            # Email
            try:
                el = modal.find_element(By.XPATH, "//a[contains(@href, 'mailto:')]")
                info['email'] = el.text.strip()
                logger.debug(f"[MODAL] Found email: {info['email']}")
            except:
                logger.debug("[MODAL] No email found")

            # Phone
            try:
                el = modal.find_element(By.XPATH, "//section[.//h3[text()='Phone']]//span[@class='t-14 t-black t-normal']")
                info['phone'] = el.text.strip()
                logger.debug(f"[MODAL] Found phone: {info['phone']}")
            except:
                logger.debug("[MODAL] No phone found")

            # Profile URL
            try:
                el = modal.find_element(By.XPATH, "//a[contains(@href, 'linkedin.com/in/')]")
                info['public_linkedin'] = el.get_attribute("href")
                logger.debug(f"[MODAL] Found profile URL: {info['public_linkedin']}")
            except:
                logger.debug("[MODAL] No profile URL found")

            # Close modal
            try:
                btn = self.driver.find_element(By.XPATH, "//button[@aria-label='Dismiss']")
                self.driver.execute_script("arguments[0].click();", btn)
                logger.debug("[MODAL] Modal closed")
                time.sleep(1)
            except:
                logger.debug("[MODAL] Could not close modal")

        except Exception as e:
            logger.debug(f"[MODAL] Error: {e}")
        
        return info

    def _extract_company(self):
        """Extract company name."""
        logger.debug("[COMPANY] Attempting to extract company...")
        
        try:
            el = self.driver.find_element(
                By.XPATH,
                "//button[contains(@aria-label, 'Current company:')]//div[contains(@class, 'inline-show-more-text')]"
            )
            company = el.text.strip()
            logger.debug(f"[COMPANY] Found: {company}")
            return company
        except:
            pass
        
        try:
            btn = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Current company:')]")
            label = btn.get_attribute('aria-label')
            company = label.replace('Current company:', '').split('.')[0].strip()
            logger.debug(f"[COMPANY] Found from aria-label: {company}")
            return company
        except:
            pass
        
        logger.debug("[COMPANY] Not found")
        return None

    def _safe_get_text(self, selectors):
        """Try selectors to get text."""
        for sel in selectors:
            try:
                el = self.driver.find_element(By.CSS_SELECTOR, sel)
                text = el.text.strip()
                if text:
                    logger.debug(f"[GET_TEXT] Found with '{sel}': {text[:50]}")
                    return text
            except:
                continue
        return None

    def extract_recent_contacts(self):
        """Extract contacts from threads with full debug logging."""
        
        logger.info("=" * 70)
        logger.info("[EXTRACTION] STARTING CONTACT EXTRACTION")
        logger.info("=" * 70)
        
        contacts = []
        successful = 0
        skipped_no_profile = 0
        skipped_invalid_name = 0
        errors = 0
        
        try:
            # Find threads
            logger.info("[EXTRACTION] Finding message threads...")
            
            threads = self.driver.find_elements(
                By.XPATH, "//div[contains(@class, 'msg-conversations-container__convo-item-link')]"
            )
            
            logger.info(f"[EXTRACTION] Found {len(threads)} threads")
            
            if not threads:
                logger.error("[EXTRACTION] No threads found!")
                self.driver.save_screenshot('debug_no_threads.png')
                return contacts

            total = len(threads)
            if self.num_messages != "all":
                total = min(total, int(self.num_messages))

            logger.info(f"[EXTRACTION] Will process {total} threads")

            for i in range(total):
                logger.info("-" * 60)
                logger.info(f"[THREAD {i+1}/{total}] Processing...")
                logger.info("-" * 60)
                
                try:
                    # Re-fetch threads
                    threads = self.driver.find_elements(
                        By.XPATH, "//div[contains(@class, 'msg-conversations-container__convo-item-link')]"
                    )
                    
                    if i >= len(threads):
                        logger.warning(f"[THREAD {i+1}] Not found after re-fetch")
                        continue
                    
                    thread = threads[i]
                    
                    # Click thread
                    logger.info(f"[THREAD {i+1}] Clicking thread...")
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", thread)
                    time.sleep(1)
                    
                    try:
                        thread.click()
                    except:
                        self.driver.execute_script("arguments[0].click();", thread)
                    
                    time.sleep(2)

                    # ========== FIND PROFILE LINK ==========
                    logger.info(f"[THREAD {i+1}] Looking for profile link...")
                    
                    profile_url = None
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
                                profile_url = href
                                logger.info(f"[THREAD {i+1}] Found profile URL: {profile_url}")
                                break
                        except:
                            continue
                    
                    if not profile_url:
                        logger.warning(f"[THREAD {i+1}] No profile link found - SKIPPING")
                        skipped_no_profile += 1
                        continue

                    # ========== OPEN PROFILE IN NEW TAB ==========
                    logger.info(f"[THREAD {i+1}] Opening profile in new tab...")
                    
                    original_windows = self.driver.window_handles
                    self.driver.execute_script("window.open(arguments[0]);", profile_url)
                    time.sleep(3)
                    
                    new_windows = [w for w in self.driver.window_handles if w not in original_windows]
                    
                    if not new_windows:
                        logger.warning(f"[THREAD {i+1}] Failed to open new tab - SKIPPING")
                        errors += 1
                        continue
                    
                    self.driver.switch_to.window(new_windows[0])
                    logger.info(f"[THREAD {i+1}] Switched to profile tab")
                    time.sleep(2)

                    # ========== EXTRACT NAME ==========
                    logger.info(f"[THREAD {i+1}] Extracting name...")
                    
                    full_name = self._safe_get_text([
                        "h1.text-heading-xlarge",
                        ".pv-top-card h1",
                        "h1.inline"
                    ])
                    
                    if not full_name or full_name == "LinkedIn Member":
                        logger.warning(f"[THREAD {i+1}] Invalid name '{full_name}' - SKIPPING")
                        skipped_invalid_name += 1
                        self.driver.close()
                        self.driver.switch_to.window(self.main_window)
                        continue

                    logger.info(f"[THREAD {i+1}] Name: {full_name}")

                    # ========== EXTRACT OTHER DATA ==========
                    company = self._extract_company()
                    logger.info(f"[THREAD {i+1}] Company: {company or 'N/A'}")
                    
                    location = self._safe_get_text([
                        "span.text-body-small.inline.t-black--light.break-words",
                        ".pv-top-card__location"
                    ])
                    logger.info(f"[THREAD {i+1}] Location: {location or 'N/A'}")

                    contact_info = self._extract_contact_modal()
                    logger.info(f"[THREAD {i+1}] Email: {contact_info.get('email') or 'N/A'}")
                    logger.info(f"[THREAD {i+1}] Phone: {contact_info.get('phone') or 'N/A'}")

                    # ========== GENERATE IDs ==========
                    linkedin_internal_id = profile_url.rstrip("/").split("/")[-1].split('?')[0]
                    linkedin_id = linkedin_internal_id
                    
                    current_url = self.driver.current_url
                    if "/in/" in current_url:
                        slug = current_url.split("/in/")[-1].split('?')[0].rstrip('/')
                        if slug and len(slug) > 5:
                            linkedin_id = slug

                    logger.info(f"[THREAD {i+1}] LinkedIn ID: {linkedin_id}")

                    # ========== SAVE TO CSV ==========
                    logger.info(f"[THREAD {i+1}] === SAVING TO CSV ===")
                    
                    csv_row = [
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        self.username,
                        full_name,
                        company or "",
                        location or "",
                        contact_info.get('email', ""),
                        contact_info.get('phone', ""),
                        profile_url,
                        ""
                    ]
                    
                    logger.info(f"[THREAD {i+1}] CSV Row: {csv_row}")
                    
                    try:
                        csv_success = log_csv("logs/extracted_contacts.csv", csv_row)
                        if csv_success:
                            logger.info(f"[THREAD {i+1}] CSV: SUCCESS")
                        else:
                            logger.error(f"[THREAD {i+1}] CSV: FAILED (returned False)")
                    except Exception as e:
                        logger.error(f"[THREAD {i+1}] CSV: EXCEPTION - {e}", exc_info=True)

                    # ========== SAVE TO API ==========
                    logger.info(f"[THREAD {i+1}] === SAVING TO API ===")
                    
                    try:
                        api_success = insert_contact(
                            full_name=full_name,
                            source_email=self.username,
                            email=contact_info.get('email'),
                            phone=contact_info.get('phone'),
                            linkedin_id=linkedin_id,
                            linkedin_internal_id=linkedin_internal_id,
                            company_name=company,
                            location=location
                        )
                        
                        if api_success:
                            successful += 1
                            logger.info(f"[THREAD {i+1}] API: SUCCESS")
                            contacts.append((full_name, company))
                        else:
                            logger.error(f"[THREAD {i+1}] API: FAILED (returned False)")
                            
                    except Exception as e:
                        logger.error(f"[THREAD {i+1}] API: EXCEPTION - {e}", exc_info=True)

                    # ========== CLOSE TAB ==========
                    logger.info(f"[THREAD {i+1}] Closing profile tab...")
                    self.driver.close()
                    self.driver.switch_to.window(self.main_window)
                    time.sleep(1)
                    
                    logger.info(f"[THREAD {i+1}] COMPLETED")

                except Exception as e:
                    logger.error(f"[THREAD {i+1}] ERROR: {e}", exc_info=True)
                    errors += 1
                    
                    # Recovery
                    try:
                        for w in self.driver.window_handles:
                            if w != self.main_window:
                                self.driver.switch_to.window(w)
                                self.driver.close()
                        self.driver.switch_to.window(self.main_window)
                    except:
                        pass

        except Exception as e:
            logger.error(f"[EXTRACTION] FATAL ERROR: {e}", exc_info=True)
        
        # ========== LOG ACTIVITY ==========
        logger.info("=" * 60)
        logger.info("[EXTRACTION] Logging activity to API...")
        
        if successful > 0:
            try:
                activity_success = log_extraction_activity(
                    candidate_id=self.candidate_id,
                    employee_id=self.employee_id,
                    activity_count=successful,
                    notes=f"Extracted {successful} contacts"
                )
                if activity_success:
                    logger.info("[EXTRACTION] Activity logged successfully")
                else:
                    logger.error("[EXTRACTION] Activity logging failed")
            except Exception as e:
                logger.error(f"[EXTRACTION] Activity logging exception: {e}", exc_info=True)
        else:
            logger.info("[EXTRACTION] No successful extractions, skipping activity log")

        # ========== SUMMARY ==========
        self.extracted_count = successful
        
        logger.info("=" * 70)
        logger.info("[EXTRACTION] SUMMARY")
        logger.info("=" * 70)
        logger.info(f"   Total threads processed: {total}")
        logger.info(f"   Successful extractions:  {successful}")
        logger.info(f"   Skipped (no profile):    {skipped_no_profile}")
        logger.info(f"   Skipped (invalid name):  {skipped_invalid_name}")
        logger.info(f"   Errors:                  {errors}")
        logger.info("=" * 70)
        
        return contacts

    def run(self):
        """Main execution."""
        logger.info("=" * 70)
        logger.info("[RUN] STARTING BOT")
        logger.info("=" * 70)
        
        try:
            self.start_browser()
            self.login()
            self.go_to_messages()
            self.extract_recent_contacts()
            
        except Exception as e:
            logger.error(f"[RUN] BOT ERROR: {e}", exc_info=True)
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("[RUN] Browser closed")
        
        logger.info("=" * 70)
        logger.info("[RUN] BOT FINISHED")
        logger.info("=" * 70)