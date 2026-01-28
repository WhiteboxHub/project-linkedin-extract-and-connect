#!/usr/bin/env python3
# connections.py
# ============================================
# LINKEDIN CONNECTION REQUEST BOT
# - YOUR working CSV loader
# - MY aside-fix connection logic
# ============================================

import random
import time
import logging
import yaml
import csv
import re
import sys
import os

# ============================================
# WINDOWS ENCODING FIX
# ============================================

if sys.platform == "win32":
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass

# ============================================
# LOGGING SETUP
# ============================================

os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/connector.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ============================================
# IMPORTS
# ============================================

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    WebDriverException, 
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    StaleElementReferenceException
)

from utils.browser import setup_browser
from utils.db import log_connector_activity

# ============================================
# ANTI-DETECTION & UTILS
# ============================================

def human_sleep(min_sec=3, max_sec=7):
    """Human-like sleep with random variations."""
    base = random.uniform(min_sec, max_sec)
    chunks = random.randint(3, 6)
    for _ in range(chunks):
        time.sleep(base / chunks + random.uniform(-0.1, 0.1))
    if random.random() < 0.3:
        time.sleep(random.uniform(0.5, 1.5))

def random_scroll(driver):
    """Random scroll movement."""
    try:
        amount = random.randint(150, 300) * random.choice([-1, 1])
        driver.execute_script(f"window.scrollBy(0, {amount})")
    except:
        pass

def human_type(element, text, min_delay=0.03, max_delay=0.1):
    """Type text with human-like delays."""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(min_delay, max_delay))
        if random.random() < 0.05:
            time.sleep(random.uniform(0.1, 0.4))

# ============================================
# LOADERS - FROM YOUR WORKING CODE
# ============================================

def load_accounts(path):
    """Load accounts from YAML file."""
    logger.info(f"[LOAD_ACCOUNTS] Loading from: {path}")
    try:
        with open(path, "r", encoding='utf-8') as f:
            accounts = yaml.safe_load(f).get("accounts", [])
        logger.info(f"[LOAD_ACCOUNTS] Loaded {len(accounts)} accounts")
        return accounts
    except Exception as e:
        logger.error(f"[LOAD_ACCOUNTS] Error: {e}")
        return []

def load_wbl_config():
    """Load WBL config from config.py."""
    try:
        from config import WBL_CONFIG
        logger.info("[LOAD_CONFIG] Config loaded successfully")
        return WBL_CONFIG
    except ImportError:
        logger.warning("[LOAD_CONFIG] config.py not found")
        return None

def load_messages(path="config.yaml"):
    """Load connection messages from config."""
    logger.info(f"[LOAD_MESSAGES] Loading from: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        
        messages = {"default": data.get("MESSAGE", "Hi, I'd like to connect!")}
        
        for key, value in data.items():
            if "@" in key and isinstance(value, str):
                messages[key.lower()] = value
        
        logger.info(f"[LOAD_MESSAGES] Loaded {len(messages)} message templates")
        return messages
    except Exception as e:
        logger.error(f"[LOAD_MESSAGES] Error: {e}")
        return {"default": "Hi, I'd like to connect with you!"}

def get_message_for_account(messages, email):
    """Get the appropriate message for the account."""
    message = messages.get(email.lower(), messages.get("default"))
    return message

# ============================================
# YOUR WORKING CSV LOADER (EXACTLY AS YOU HAD IT)
# ============================================

def load_all_profiles_from_csv(file_path="logs/extracted_contacts.csv"):
    """Load ALL profiles from CSV with their source_email."""
    logger.info(f"[LOAD_PROFILES] Loading from: {file_path}")
    
    profiles = []
    
    paths = [
        file_path,
        f"logs/{file_path}",
        "logs/extracted_contacts.csv",
        "extracted_contacts.csv"
    ]
    
    actual_path = None
    for p in paths:
        if os.path.exists(p):
            actual_path = p
            logger.info(f"[LOAD_PROFILES] Found file: {p}")
            break
    
    if not actual_path:
        logger.error("[LOAD_PROFILES] CSV file not found!")
        return []
    
    try:
        with open(actual_path, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            
            if header:
                logger.info(f"[LOAD_PROFILES] CSV Header: {header}")
            
            row_count = 0
            for row in reader:
                row_count += 1
                
                # YOUR ORIGINAL CHECK - but let's make it more flexible
                # if len(row) < 8:
                #     continue
                
                # More flexible: just need at least 2 columns
                if len(row) < 2:
                    continue
                
                source_email = row[1].strip() if len(row) > 1 else ''
                name = row[2].strip() if len(row) > 2 else ''
                
                profile_url = None
                for cell in row:
                    # Your original regex - works fine
                    match = re.search(r'https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9\-_]+', cell)
                    if match:
                        profile_url = match.group(0).split('?')[0].rstrip('/')
                        break
                    
                    # Fallback: also check for any linkedin.com/in/ URL
                    if 'linkedin.com/in/' in cell and not profile_url:
                        profile_url = cell.strip().split('?')[0].rstrip('/')
                
                if profile_url and source_email:
                    profiles.append({
                        'url': profile_url,
                        'source_email': source_email.lower(),
                        'name': name
                    })
                    logger.info(f"[LOAD_PROFILES] Added: {name} | {source_email} | {profile_url[:50]}...")
        
        logger.info(f"[LOAD_PROFILES] Loaded {len(profiles)} total profiles from {row_count} rows")
        
        source_counts = {}
        for p in profiles:
            src = p['source_email']
            source_counts[src] = source_counts.get(src, 0) + 1
        
        logger.info("[LOAD_PROFILES] Breakdown by Source Email:")
        for src, count in source_counts.items():
            logger.info(f"   - {src}: {count} profiles")
        
        return profiles
        
    except Exception as e:
        logger.error(f"[LOAD_PROFILES] Error reading CSV: {e}", exc_info=True)
        return []

def filter_profiles_for_account(all_profiles, account_email):
    """Filter profiles to only those extracted by this account."""
    account_email_lower = account_email.lower().strip()
    
    filtered = [
        p for p in all_profiles 
        if p.get('source_email', '').lower().strip() == account_email_lower
    ]
    
    logger.info(f"[FILTER] Account: {account_email}")
    logger.info(f"[FILTER] Total profiles: {len(all_profiles)}")
    logger.info(f"[FILTER] Matched profiles: {len(filtered)}")
    
    return filtered

# ============================================
# CONNECTOR CLASS - MY ASIDE-FIX CODE
# ============================================

class LinkedInConnector:
    """LinkedIn Connection Bot - Only clicks MAIN profile Connect button."""
    
    def __init__(self, username, password, chrome_profile, employee_id, candidate_id):
        self.username = username
        self.password = password
        self.chrome_profile = chrome_profile
        self.employee_id = employee_id
        self.candidate_id = candidate_id
        self.driver = None
        self.wait = None
        self.sent_count = 0
        self.skipped_count = 0
        self.failed_count = 0
        self.failures = 0

        logger.info(f"[CONNECTOR] Initialized for: {username}")

    def start_browser(self):
        logger.info("[BROWSER] Starting...")
        self.driver, self.wait = setup_browser(self.chrome_profile)
        logger.info("[BROWSER] Started successfully")

    def ensure_logged_in(self):
        """Check if logged in, if not, perform login."""
        try:
            self.driver.get("https://www.linkedin.com/feed/")
            human_sleep(3, 5)
            
            current_url = self.driver.current_url
            if "feed" in current_url and "login" not in current_url:
                logger.info("[LOGIN] Already logged in")
                return True
            
            logger.info("[LOGIN] Not logged in, performing login...")
            self.driver.get("https://www.linkedin.com/login")
            human_sleep(2, 4)
            
            # Enter username
            username_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            human_type(username_field, self.username)
            human_sleep(0.5, 1)
            
            # Enter password
            password_field = self.driver.find_element(By.ID, "password")
            human_type(password_field, self.password)
            human_sleep(0.5, 1)
            
            # Click submit
            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            
            human_sleep(5, 8)
            
            # Check for verification
            current_url = self.driver.current_url
            if "checkpoint" in current_url or "challenge" in current_url:
                logger.warning("[LOGIN] Verification required! Complete manually...")
                input("Press Enter after completing verification...")
            
            self.driver.get("https://www.linkedin.com/feed/")
            human_sleep(2, 3)
            
            if "feed" in self.driver.current_url:
                logger.info("[LOGIN] Login successful")
                return True
            else:
                logger.error("[LOGIN] Login failed")
                return False
                
        except Exception as e:
            logger.error(f"[LOGIN] Error: {e}")
            return False

    def safe_click(self, element):
        """Safely click an element."""
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", 
                element
            )
            human_sleep(0.5, 1)
            element.click()
            return True
        except:
            try:
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except:
                return False

    def close_dropdown(self):
        """Close any open dropdown."""
        try:
            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        except:
            pass
        try:
            self.driver.find_element(By.TAG_NAME, "body").click()
        except:
            pass
        human_sleep(0.3, 0.5)

    def close_modal(self):
        """Close any open modal dialog."""
        try:
            close_btns = self.driver.find_elements(
                By.XPATH, 
                "//button[@aria-label='Dismiss' or @aria-label='Close']"
            )
            for btn in close_btns:
                if btn.is_displayed():
                    btn.click()
                    human_sleep(0.5, 1)
                    return True
        except:
            pass
        return False

    def check_connection_status(self):
        """
        Check connection status from MAIN profile section only.
        Uses data-member-id to identify the main profile card.
        NEVER checks sidebar.
        """
        try:
            # CHECK 1: Degree Badge (1st = Connected)
            try:
                degree_el = self.driver.find_element(
                    By.XPATH, 
                    "//section[@data-member-id]//span[contains(@class, 'dist-value')]"
                )
                degree = degree_el.text.strip()
                logger.info(f"[STATUS] Connection degree: {degree}")
                
                if "1st" in degree:
                    return 'connected'
            except:
                pass

            # CHECK 2: Pending Button in MAIN section
            try:
                pending_selectors = [
                    "//section[@data-member-id]//button[.//span[text()='Pending']]",
                    "//section[@data-member-id]//button[contains(@aria-label, 'Pending')]"
                ]
                for sel in pending_selectors:
                    try:
                        pending = self.driver.find_element(By.XPATH, sel)
                        if pending.is_displayed():
                            logger.info("[STATUS] Invitation is Pending")
                            return 'pending'
                    except:
                        continue
            except:
                pass

            # CHECK 3: "Remove Connection" in page source
            try:
                page_source = self.driver.page_source
                if "Remove your connection" in page_source or "Remove Connection" in page_source:
                    if "1st" in page_source:
                        logger.info("[STATUS] Found 'Remove Connection' - Already connected")
                        return 'connected'
            except:
                pass

            # CHECK 4: Message without Connect in MAIN section
            try:
                message_btn = self.driver.find_element(
                    By.XPATH, 
                    "//section[@data-member-id]//button[contains(@aria-label, 'Message')]"
                )
                
                connect_exists = False
                try:
                    connect_btn = self.driver.find_element(
                        By.XPATH, 
                        "//section[@data-member-id]//button[contains(@class, 'artdeco-button--primary') and .//span[text()='Connect']]"
                    )
                    if connect_btn.is_displayed():
                        connect_exists = True
                except:
                    pass

                if message_btn.is_displayed() and not connect_exists:
                    logger.info("[STATUS] Message exists without Connect = Connected")
                    return 'connected'
            except:
                pass

            return 'can_connect'

        except Exception as e:
            logger.debug(f"[STATUS] Error: {e}")
            return 'unknown'

    def find_connect_button(self):
        """
        Find Connect button with STRICT checks:
        1. ONLY inside //section[@data-member-id] (Main Profile)
        2. ONLY artdeco-button--primary (Blue button)
        3. NEVER inside <aside> (Sidebar)
        4. Fallback: Check "More" dropdown
        """
        logger.info("[CONNECT_BTN] Searching in main profile section...")

        # STEP 1: Try Direct Connect Button in MAIN section
        direct_selectors = [
            "//section[@data-member-id]//button[contains(@class, 'artdeco-button--primary') and .//span[text()='Connect']]",
            "//section[@data-member-id]//button[contains(@class, 'artdeco-button--primary') and contains(@aria-label, 'Invite') and contains(@aria-label, 'to connect')]",
            "//section[@data-member-id]//button[contains(@class, 'artdeco-button--primary') and .//svg[@data-test-icon='connect-small']]",
            "//section[@data-member-id]//button[.//span[text()='Connect'] and not(contains(@class, 'artdeco-button--muted'))]"
        ]

        for sel in direct_selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, sel)
                for btn in elements:
                    try:
                        if not btn.is_displayed() or not btn.is_enabled():
                            continue
                        
                        # SAFETY: Verify NOT in sidebar
                        is_in_aside = self.driver.execute_script(
                            "return arguments[0].closest('aside') !== null;", btn
                        )
                        if is_in_aside:
                            logger.debug("[CONNECT_BTN] Skipped - button in sidebar")
                            continue
                        
                        aria = btn.get_attribute("aria-label") or ""
                        logger.info(f"[CONNECT_BTN] ✓ Found DIRECT button: '{aria[:50]}'")
                        return btn
                        
                    except StaleElementReferenceException:
                        continue
            except:
                continue

        # STEP 2: Check "More" Dropdown in MAIN section
        logger.info("[CONNECT_BTN] Direct button not found, checking 'More' dropdown...")
        
        try:
            more_selectors = [
                "//section[@data-member-id]//button[contains(@aria-label, 'More actions')]",
                "//section[@data-member-id]//button[.//span[text()='More']]"
            ]
            
            more_btn = None
            for sel in more_selectors:
                try:
                    more_btn = self.driver.find_element(By.XPATH, sel)
                    if more_btn.is_displayed():
                        break
                    more_btn = None
                except:
                    continue
            
            if not more_btn:
                logger.debug("[CONNECT_BTN] 'More' button not found")
                return None
            
            logger.info("[CONNECT_BTN] Opening 'More' dropdown...")
            self.safe_click(more_btn)
            human_sleep(1.5, 2.5)
            
            # Look for Connect in dropdown
            dropdown_selectors = [
                "//div[contains(@class, 'artdeco-dropdown__content')]//div[contains(@aria-label, 'Invite') and contains(@aria-label, 'to connect')]",
                "//div[contains(@class, 'artdeco-dropdown__content')]//div[@role='button' and contains(., 'Connect')]",
                "//div[contains(@class, 'artdeco-dropdown__content')]//span[text()='Connect']/ancestor::div[@role='button']",
                "//div[contains(@class, 'artdeco-dropdown__content')]//li[contains(., 'Connect')]//div[@role='button']"
            ]
            
            for sel in dropdown_selectors:
                try:
                    connect_opt = self.driver.find_element(By.XPATH, sel)
                    if connect_opt.is_displayed():
                        logger.info("[CONNECT_BTN] ✓ Found Connect in 'More' dropdown")
                        return connect_opt
                except:
                    continue
            
            logger.info("[CONNECT_BTN] Connect not in dropdown, closing...")
            self.close_dropdown()
            
        except NoSuchElementException:
            logger.debug("[CONNECT_BTN] 'More' button not found")
        except Exception as e:
            logger.debug(f"[CONNECT_BTN] Dropdown error: {e}")
            self.close_dropdown()

        logger.warning("[CONNECT_BTN] No Connect button found anywhere in main profile")
        return None

    def find_add_note_button(self):
        """Find 'Add a note' button in connection modal."""
        selectors = [
            "//button[@aria-label='Add a note']",
            "//button[contains(@aria-label, 'Add a note')]",
            "//button[.//span[text()='Add a note']]"
        ]
        
        for sel in selectors:
            try:
                btn = self.driver.find_element(By.XPATH, sel)
                if btn.is_displayed():
                    return btn
            except:
                continue
        return None

    def find_note_textarea(self):
        """Find note textarea in modal."""
        selectors = [
            "//textarea[@name='message']",
            "//textarea[@id='custom-message']",
            "//div[@role='dialog']//textarea"
        ]
        
        for sel in selectors:
            try:
                textarea = self.driver.find_element(By.XPATH, sel)
                if textarea.is_displayed():
                    return textarea
            except:
                continue
        return None

    def find_send_button(self):
        """Find Send button in connection modal."""
        selectors = [
            "//button[@aria-label='Send now']",
            "//button[@aria-label='Send invitation']",
            "//button[@aria-label='Send']",
            "//button[.//span[text()='Send']]",
            "//button[.//span[text()='Send now']]",
            "//button[.//span[text()='Send invitation']]",
            "//div[@role='dialog']//button[contains(@class, 'artdeco-button--primary')]"
        ]
        
        for sel in selectors:
            try:
                btn = self.driver.find_element(By.XPATH, sel)
                if btn.is_displayed() and btn.is_enabled():
                    text = btn.text.strip().lower()
                    if 'send' in text and 'message' not in text:
                        return btn
            except:
                continue
        return None

    def send_connection(self, profile_url, profile_name, note):
        """Send connection request to a single profile."""
        logger.info("-" * 50)
        logger.info(f"[CONNECT] Processing: {profile_name}")
        logger.info(f"[CONNECT] URL: {profile_url}")
        
        try:
            # STEP 1: Navigate to Profile
            self.driver.get(profile_url)
            human_sleep(5, 8)
            random_scroll(self.driver)
            human_sleep(1, 2)
            
            # STEP 2: Check Connection Status
            status = self.check_connection_status()
            logger.info(f"[CONNECT] Status: {status}")
            
            if status == 'connected':
                logger.info(f"[CONNECT] SKIPPED: Already connected - {profile_name}")
                self.skipped_count += 1
                return 'skipped'
            
            if status == 'pending':
                logger.info(f"[CONNECT] SKIPPED: Invitation pending - {profile_name}")
                self.skipped_count += 1
                return 'skipped'
            
            # STEP 3: Find Connect Button (MAIN section only)
            connect_btn = self.find_connect_button()
            
            if not connect_btn:
                logger.warning(f"[CONNECT] FAILED: Connect button not found - {profile_name}")
                self.failed_count += 1
                return 'failed'
            
            # STEP 4: Click Connect Button
            logger.info("[CONNECT] Clicking Connect button...")
            if not self.safe_click(connect_btn):
                logger.warning("[CONNECT] Failed to click Connect button")
                self.failed_count += 1
                return 'failed'
            
            human_sleep(2, 4)
            
            # STEP 5: Add Note (Optional)
            note_added = False
            
            add_note_btn = self.find_add_note_button()
            if add_note_btn:
                logger.info("[CONNECT] Clicking 'Add a note'...")
                self.safe_click(add_note_btn)
                human_sleep(1, 2)
                
                textarea = self.find_note_textarea()
                if textarea:
                    logger.info("[CONNECT] Typing note...")
                    textarea.clear()
                    human_type(textarea, note)
                    note_added = True
                    logger.info("[CONNECT] Note added successfully")
                    human_sleep(1, 2)
            
            if not note_added:
                logger.info("[CONNECT] Proceeding without note")
            
            # STEP 6: Click Send Button
            logger.info("[CONNECT] Looking for Send button...")
            human_sleep(1, 2)
            
            send_btn = self.find_send_button()
            
            if not send_btn:
                logger.warning(f"[CONNECT] FAILED: Send button not found - {profile_name}")
                self.close_modal()
                self.failed_count += 1
                return 'failed'
            
            logger.info("[CONNECT] Clicking Send button...")
            if not self.safe_click(send_btn):
                logger.warning("[CONNECT] Failed to click Send button")
                self.close_modal()
                self.failed_count += 1
                return 'failed'
            
            # STEP 7: Success
            human_sleep(2, 3)
            
            self.sent_count += 1
            self.failures = 0
            
            logger.info(f"[CONNECT] ✓ SUCCESS: Connection sent to {profile_name} (#{self.sent_count})")
            
            # Cooldown
            cooldown = random.uniform(12, 20)
            logger.info(f"[CONNECT] Cooldown: {cooldown:.1f}s")
            time.sleep(cooldown)
            
            return 'sent'
            
        except WebDriverException as e:
            error_str = str(e).lower()
            if "10054" in error_str or "reset" in error_str:
                self.failures += 1
                logger.error("[CONNECT] Connection reset - possible detection!")
                wait_time = min(300, 60 * (2 ** self.failures))
                logger.warning(f"[CONNECT] Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"[CONNECT] WebDriver error: {e}")
            
            self.failed_count += 1
            return 'failed'
            
        except Exception as e:
            logger.error(f"[CONNECT] Error: {e}", exc_info=True)
            self.failures += 1
            self.failed_count += 1
            return 'failed'

    def run(self, profiles, note, max_connections=5):
        """Run connector for given profiles."""
        logger.info("=" * 60)
        logger.info(f"[RUN] Starting - {len(profiles)} profiles, max {max_connections}")
        logger.info("=" * 60)
        
        if not profiles:
            logger.warning("[RUN] No profiles to process")
            return
        
        try:
            self.start_browser()
            
            if not self.ensure_logged_in():
                logger.error("[RUN] Login failed, aborting")
                return
            
            for i, profile in enumerate(profiles):
                if self.sent_count >= max_connections:
                    logger.info(f"[RUN] Reached max connections: {max_connections}")
                    break
                
                if self.failures >= 3:
                    logger.error("[RUN] Too many consecutive failures, stopping")
                    break
                
                if self.sent_count > 0 and self.sent_count % 3 == 0:
                    wait_time = random.uniform(60, 120)
                    logger.info(f"[RUN] Extended break: {wait_time:.1f}s")
                    time.sleep(wait_time)
                
                logger.info(f"\n[RUN] Profile {i+1}/{len(profiles)}")
                
                self.send_connection(
                    profile['url'],
                    profile['name'],
                    note
                )
                
                if i < len(profiles) - 1 and self.sent_count < max_connections:
                    delay = random.uniform(8, 15)
                    logger.info(f"[RUN] Next profile in: {delay:.1f}s")
                    time.sleep(delay)
            
            logger.info("=" * 60)
            logger.info("[RUN] COMPLETED")
            logger.info(f"   Sent: {self.sent_count}")
            logger.info(f"   Skipped: {self.skipped_count}")
            logger.info(f"   Failed: {self.failed_count}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"[RUN] Fatal error: {e}", exc_info=True)
            
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("[RUN] Browser closed")

# ============================================
# MAIN
# ============================================

def main():
    print("=" * 60)
    print(" LINKEDIN CONNECTION BOT")
    print(" (Your CSV Loader + My Aside Fix)")
    print("=" * 60)

    wbl_config = load_wbl_config() or {}
    employee_id = wbl_config.get('EMPLOYEE_ID', 0)
    default_candidate_id = wbl_config.get('CANDIDATE_ID', 0)
    
    accounts = load_accounts("credentials/accounts.yaml")
    if not accounts:
        print("\nERROR: No accounts found in credentials/accounts.yaml")
        return
    
    all_profiles = load_all_profiles_from_csv()
    if not all_profiles:
        print("\nERROR: No profiles found in CSV.")
        return
    
    messages = load_messages()
    
    DAILY_LIMIT = 5
    
    print(f"\nAccounts: {len(accounts)}")
    print(f"Total Profiles: {len(all_profiles)}")
    print(f"Daily Limit: {DAILY_LIMIT}")
    print("=" * 60)

    total_sent = 0
    total_skipped = 0
    total_failed = 0

    for idx, acc in enumerate(accounts, 1):
        username = acc.get('username', '')
        password = acc.get('password', '')
        chrome_profile = acc.get('chrome_profile', 'Default')
        candidate_id = acc.get('candidate_id', default_candidate_id)
        
        if not username or not password:
            print(f"\n[{idx}] SKIP: Missing credentials")
            continue
        
        print(f"\n{'='*60}")
        print(f"[{idx}/{len(accounts)}] Account: {username}")
        print(f"{'='*60}")
        
        account_profiles = filter_profiles_for_account(all_profiles, username)
        
        if not account_profiles:
            print(f"   No profiles found for this account in CSV")
            continue
        
        print(f"   Profiles: {len(account_profiles)}")
        
        note = get_message_for_account(messages, username)
        print(f"   Message: {note[:50]}...")
        
        connector = LinkedInConnector(
            username=username,
            password=password,
            chrome_profile=chrome_profile,
            employee_id=employee_id,
            candidate_id=candidate_id
        )
        
        connector.run(
            profiles=account_profiles,
            note=note,
            max_connections=DAILY_LIMIT
        )
        
        if connector.sent_count > 0:
            log_connector_activity(
                candidate_id=candidate_id,
                employee_id=employee_id,
                activity_count=connector.sent_count,
                notes=f"Sent {connector.sent_count} connections from {username}"
            )
        
        total_sent += connector.sent_count
        total_skipped += connector.skipped_count
        total_failed += connector.failed_count
        
        print(f"\n   Results: Sent={connector.sent_count}, Skipped={connector.skipped_count}, Failed={connector.failed_count}")
        
        if idx < len(accounts):
            delay = random.uniform(30, 60)
            print(f"\n   Waiting {delay:.1f}s...")
            time.sleep(delay)

    print("\n" + "=" * 60)
    print(" COMPLETE")
    print(f" Sent: {total_sent}, Skipped: {total_skipped}, Failed: {total_failed}")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal: {e}", exc_info=True)
        sys.exit(1)