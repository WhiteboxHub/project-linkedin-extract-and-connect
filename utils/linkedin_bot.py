
            
            
            
            
            
            
            
            
import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from utils.logger import log_csv
from utils.browser import setup_browser
from utils.db import insert_contact
import yaml
import os

# Load config
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
abs_config_path = os.path.abspath(CONFIG_PATH)

print("Looking for config at:", abs_config_path)

# Load config or use defaults if not found
try:
    with open(abs_config_path, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f) or {}
except FileNotFoundError:
    print(f"Warning: config.yaml not found at {abs_config_path}. Using defaults.")
    config_data = {}

NUM_MESSAGES_TO_PROCESS = config_data.get("NUM_MESSAGES_TO_PROCESS", "all")

class LinkedInBot:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.driver, self.wait = setup_browser()
        self.main_window = None

    def login(self):
        self.driver.get("https://www.linkedin.com/login")
        self.wait.until(EC.presence_of_element_located((By.ID, 'username'))).send_keys(self.username)
        self.driver.find_element(By.ID, 'password').send_keys(self.password)
        self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
        self.wait.until(EC.url_contains("feed"))
        print(f"✅ Logged in: {self.username}")
        time.sleep(3)

    def go_to_messages(self):
        self.driver.get("https://www.linkedin.com/messaging/")
        time.sleep(5)
        self.main_window = self.driver.current_window_handle
        self._scroll_to_load_threads()

    def _scroll_to_load_threads(self):
        """Scroll until all or required number of threads are loaded."""
        last_height = self.driver.execute_script(
            "return document.querySelector('.msg-conversations-container__conversations-list').scrollHeight"
        )
        loaded_threads = 0
        while True:
            threads = self.driver.find_elements(
                By.XPATH, "//div[contains(@class, 'msg-conversations-container__convo-item-link')]"
            )
            loaded_threads = len(threads)

            if NUM_MESSAGES_TO_PROCESS != "all" and loaded_threads >= int(NUM_MESSAGES_TO_PROCESS):
                break

            self.driver.execute_script(
                "document.querySelector('.msg-conversations-container__conversations-list').scrollTo(0, arguments[0]);",
                last_height
            )
            time.sleep(2)
            new_height = self.driver.execute_script(
                "return document.querySelector('.msg-conversations-container__conversations-list').scrollHeight"
            )
            if new_height == last_height:  # no more threads to load
                break
            last_height = new_height

        print(f"📜 Found {loaded_threads} total threads. Processing...")

    def extract_contact_info_from_modal(self):
        contact_info = {}
        try:
            # Wait for Contact Info button
            contact_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "top-card-text-details-contact-info"))
            )
            self.driver.execute_script("arguments[0].click();", contact_button)
            time.sleep(2)

            # Wait for modal to appear
            modal = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.artdeco-modal__content"))
            )

            # Extract public LinkedIn URL
            try:
                profile_url_el = modal.find_element(
                    By.CSS_SELECTOR, "section.pv-contact-info__contact-type a[href*='linkedin.com/in/']"
                )
                contact_info['public_linkedin'] = profile_url_el.get_attribute("href")
            except:
                contact_info['public_linkedin'] = ""

            # Extract email if available
            try:
                email_section = modal.find_element(
                    By.XPATH, "//section[contains(@class,'pv-contact-info__contact-type')][.//h3[contains(text(),'Email')]]"
                )
                email = email_section.find_element(By.CSS_SELECTOR, "a").text.strip()
                contact_info['email'] = email
            except:
                contact_info['email'] = ""

            # Create clean contact text with just profile and email
            contact_info['full_text'] = f"Profile: {contact_info['public_linkedin']}\nEmail: {contact_info['email']}"

            # Close the modal
            try:
                close_btn = modal.find_element(By.CSS_SELECTOR, "button.artdeco-modal__dismiss")
                self.driver.execute_script("arguments[0].click();", close_btn)
            except:
                pass

        except Exception as e:
            print("⚠️ Could not fetch contact info from modal:", e)

        return contact_info

    def extract_recent_contacts(self):
        contacts = []
        try:
            threads_locator = "//div[contains(@class, 'msg-conversations-container__convo-item-link')]"
            all_threads = self.driver.find_elements(By.XPATH, threads_locator)

            total_threads = len(all_threads)
            if NUM_MESSAGES_TO_PROCESS != "all":
                total_threads = min(total_threads, int(NUM_MESSAGES_TO_PROCESS))

            for i in range(total_threads):
                try:
                    print(f"📨 Opening thread {i+1} of {total_threads}...")
                    current_threads = self.driver.find_elements(By.XPATH, threads_locator)
                    thread = current_threads[i]
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", thread)
                    thread.click()
                    time.sleep(2)

                    # Get profile link if available
                    try:
                        profile_link_el = self.driver.find_element(By.CSS_SELECTOR, "a[href*='/in/']")
                        profile_url = profile_link_el.get_attribute("href")
                    except:
                        print("⚠️ No profile link found (group/system/archived). Skipping...")
                        continue

                    # Open profile in a new tab
                    self.driver.execute_script("window.open(arguments[0]);", profile_url)
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    time.sleep(3)

                    # Extract profile details
                    full_name = self._safe_get_text("h1.text-heading-xlarge")
                    title = self._safe_get_text("div.text-body-medium.break-words")
                    location = self._safe_get_text("span.text-body-small.inline.t-black--light.break-words")
                    pronouns = self._safe_get_text("span.text-body-small")
                    connection = self._safe_get_text("span.dist-value")

                    contact_info = self.extract_contact_info_from_modal()

                    # Public LinkedIn ID (slug if available, else fallback)
                    linkedin_id = profile_url.rstrip("/").split("/")[-1]
                    if contact_info['public_linkedin']:
                        public_url = contact_info['public_linkedin'].rstrip("/")
                        if '/in/' in public_url:
                            linkedin_id = public_url.split('/in/')[-1]

                    # Internal LinkedIn ID (always raw ID from profile_url)
                    linkedin_internal_id = profile_url.rstrip("/").split("/")[-1]

                    # Log extracted data (CSV)
                    log_csv(
                        "logs/extracted_contacts.csv",
                        [
                            datetime.now(),
                            self.username,
                            full_name,
                            title,
                            location,
                            pronouns,
                            connection,
                            profile_url,
                            contact_info.get('full_text', '')
                        ]
                    )

                    # Also save to DB
                    insert_contact(
                        full_name if full_name else None,
                        self.username,
                        None,
                        None,
                        linkedin_id,              # public slug (if available)
                        linkedin_internal_id,     # internal ID only (e.g. ACoAAEyOmOUBfuCgd7pm6LjPD1m9D4SozLwvjs4)
                        title if title else None,
                        location if location else None
                    )

                    print(f"✅ Extracted + Saved {full_name} to DB")
                    contacts.append((full_name, title))

                    # Close profile tab and return to main tab
                    self.driver.close()
                    self.driver.switch_to.window(self.main_window)
                    time.sleep(1)

                except Exception as e:
                    print(f"⚠️ Error reading thread {i+1}: {e}")
                    log_csv("logs/error_logs.csv", [datetime.now(), self.username, f"Thread {i+1}", str(e)])
                    continue

        except Exception as e:
            print(f"⚠️ Error in extract_recent_contacts: {e}")
            log_csv("logs/error_logs.csv", [datetime.now(), self.username, "extract_recent_contacts", str(e)])
        return contacts

    def _safe_get_text(self, selector):
        try:
            return self.driver.find_element(By.CSS_SELECTOR, selector).text.strip()
        except:
            return ""

    def run(self):
        try:
            self.login()
            self.go_to_messages()
            self.extract_recent_contacts()
        except Exception as e:
            print(f"Error in {self.username}: {str(e)}")
        finally:
            self.driver.quit()
