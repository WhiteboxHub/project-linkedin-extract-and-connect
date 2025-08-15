

# import time
# from datetime import datetime
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
# from utils.helpers import load_message
# from utils.logger import log_csv
# from utils.browser import setup_browser
# from config import NUM_MESSAGES_TO_PROCESS

# class LinkedInBot:
#     def __init__(self, username, password):
#         self.username = username
#         self.password = password
#         self.message = load_message("messages/message.txt")
#         self.driver, self.wait = setup_browser()
#         self.main_window = None

#     def login(self):
#         self.driver.get("https://www.linkedin.com/login")
#         self.wait.until(EC.presence_of_element_located((By.ID, 'username'))).send_keys(self.username)
#         self.driver.find_element(By.ID, 'password').send_keys(self.password)
#         self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
#         self.wait.until(EC.url_contains("feed"))
#         print(f"✅ Logged in: {self.username}")
#         time.sleep(3)

#     def go_to_messages(self):
#         self.driver.get("https://www.linkedin.com/messaging/")
#         time.sleep(10)
#         self.main_window = self.driver.current_window_handle
#         return

#     def _scroll_to_top_of_chat(self):
#         """Scroll to the top of the current chat conversation"""
#         try:
#             # First wait for the message list to be present
#             message_list = self.wait.until(EC.presence_of_element_located(
#                 (By.CSS_SELECTOR, "div.msg-s-message-list.full-width.scrollable")
#             ))
            
#             # Scroll to top with smooth behavior
#             self.driver.execute_script("""
#                 arguments[0].scrollTo({
#                     top: 0,
#                     behavior: 'smooth'
#                 });
#             """, message_list)
            
#             # Wait for scroll to complete
#             time.sleep(2)
            
#             # Additional check to ensure we're at the top
#             scroll_position = self.driver.execute_script("return arguments[0].scrollTop", message_list)
#             if scroll_position > 100:  # If not at top, try again
#                 self.driver.execute_script("arguments[0].scrollTop = 0;", message_list)
#                 time.sleep(1)
            
#             return True
#         except Exception as e:
#             print(f"⚠️ Error scrolling chat: {e}")
#             return False

#     def extract_recent_contacts(self):
#         contacts = []
#         try:
#             # Get all conversation threads
#             threads = self.wait.until(EC.presence_of_all_elements_located(
#                 (By.XPATH, "//div[contains(@class, 'msg-conversations-container__convo-item-link')]")
#             ))

#             if NUM_MESSAGES_TO_PROCESS == "all":
#                 print(f"Found {len(threads)} total threads. Processing all...")
#                 threads_to_process = threads
#             else:
#                 print(f"Found {len(threads)} total threads. Processing last {NUM_MESSAGES_TO_PROCESS}...")
#                 threads_to_process = threads[:NUM_MESSAGES_TO_PROCESS]

#             for i, thread in enumerate(threads_to_process, start=1):
#                 try:
#                     print(f"📨 Opening thread {i} of {len(threads_to_process)}...")
                    
#                     # Re-find thread to avoid staleness
#                     current_threads = self.driver.find_elements(
#                         By.XPATH, "//div[contains(@class, 'msg-conversations-container__convo-item-link')]"
#                     )
#                     if i-1 < len(current_threads):
#                         thread = current_threads[i-1]
                    
#                     # Scroll to and click the thread
#                     self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", thread)
#                     thread.click()
#                     time.sleep(3)  # Wait for click to register
                    
#                     # Wait for chat container to load
#                     self.wait.until(EC.presence_of_element_located(
#                         (By.CSS_SELECTOR, "div.msg-s-message-list-container")
#                     ))
                    
#                     # Scroll to top of chat - this is the critical fix
#                     if not self._scroll_to_top_of_chat():
#                         print("⚠️ Retrying scroll...")
#                         time.sleep(2)
#                         self._scroll_to_top_of_chat()
                    
#                     # Wait for profile card to load
#                     profile_card = self.wait.until(EC.visibility_of_element_located(
#                         (By.CSS_SELECTOR, "div.msg-s-profile-card.msg-s-profile-card-one-to-one.ph3")
#                     ))
                    
#                     # Scroll profile card into view
#                     self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", profile_card)
#                     time.sleep(2)

#                     # Rest of your profile extraction logic remains exactly the same...
#                     profile_block = self.wait.until(EC.visibility_of_element_located(
#                         (By.CSS_SELECTOR, "div.artdeco-entity-lockup__title.ember-view")
#                     ))
#                     name_link = profile_block.find_element(By.CSS_SELECTOR, "a")
#                     profile_url = name_link.get_attribute("href")

#                     # Open profile in new tab
#                     self.driver.execute_script("window.open(arguments[0]);", profile_url)
#                     time.sleep(3)
#                     self.driver.switch_to.window(self.driver.window_handles[-1])

#                     # Extract profile details
#                     full_name = self._safe_get_text("h1.text-heading-xlarge")
#                     title = self._safe_get_text("div.text-body-medium.break-words")
#                     location = self._safe_get_text("span.text-body-small.inline.t-black--light.break-words")
#                     pronouns = self._safe_get_text("span.text-body-small")
#                     connection = self._safe_get_text("span.dist-value")

#                     contact_info = ""
#                     try:
#                         contact_button = self.driver.find_element(By.CSS_SELECTOR, "a[href*='overlay/contact-info']")
#                         self.driver.execute_script("arguments[0].click();", contact_button)
#                         time.sleep(2)
#                         try:
#                             modal_section = self.wait.until(EC.presence_of_element_located(
#                                 (By.CSS_SELECTOR, "section.pv-contact-info")
#                             ))
#                             contact_info = modal_section.text.strip()
#                         except Exception:
#                             try:
#                                 modal_section = self.driver.find_element(By.CSS_SELECTOR, "section.pv-contact-info__contact-type")
#                                 contact_info = modal_section.text.strip()
#                             except Exception:
#                                 contact_info = ""
#                         try:
#                             close_btn = self.driver.find_element(By.CSS_SELECTOR, "button.artdeco-modal__dismiss")
#                             self.driver.execute_script("arguments[0].click();", close_btn)
#                             time.sleep(1)
#                         except Exception:
#                             pass
#                     except Exception as ci_err:
#                         print(f"⚠️ No contact info found for {full_name}: {ci_err}")

#                     # Log details
#                     log_csv("logs/extracted_contacts.csv",
#                             [datetime.now(), self.username, full_name, title, location, pronouns, connection, profile_url, contact_info])
#                     print(f"✅ Extracted {full_name}")
#                     contacts.append((full_name, title))

#                     # Close profile tab and return to messages
#                     self.driver.close()
#                     self.driver.switch_to.window(self.main_window)
#                     self.wait.until(EC.presence_of_element_located(
#                         (By.CSS_SELECTOR, "div.msg-conversations-container__convo-item-link")
#                     ))
#                     time.sleep(2)

#                 except Exception as e:
#                     print(f"⚠️ Error reading thread {i}: {e}")
#                     log_csv("logs/error_logs.csv", [datetime.now(), self.username, f"Thread {i}", str(e)])
#                     try:
#                         if len(self.driver.window_handles) > 1:
#                             self.driver.close()
#                         self.driver.switch_to.window(self.main_window)
#                         self.wait.until(EC.presence_of_element_located(
#                             (By.CSS_SELECTOR, "div.msg-conversations-container__convo-item-link")
#                         ))
#                     except Exception:
#                         pass
#                     continue
#         except Exception as e:
#             print(f"⚠️ Error in extract_recent_contacts: {e}")
#             log_csv("logs/error_logs.csv", [datetime.now(), self.username, "extract_recent_contacts", str(e)])
#         return contacts

#     def _safe_get_text(self, selector):
#         try:
#             return self.driver.find_element(By.CSS_SELECTOR, selector).text.strip()
#         except:
#             return ""

#     def run(self):
#         try:
#             self.login()
#             self.go_to_messages()
#             self.extract_recent_contacts()
#         except Exception as e:
#             print(f"Error in {self.username}: {str(e)}")
#         finally:
#             self.driver.quit()

























import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
from utils.helpers import load_message
from utils.logger import log_csv
from utils.browser import setup_browser
import yaml
import os

# Load values from config.yaml
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
with open(CONFIG_PATH, "r") as f:
    config_data = yaml.safe_load(f)

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
        time.sleep(10)
        self.main_window = self.driver.current_window_handle
        return

    def extract_recent_contacts(self):
        contacts = []
        try:
            threads_locator = "//div[contains(@class, 'msg-conversations-container__convo-item-link')]"

            all_threads = self.wait.until(EC.presence_of_all_elements_located((By.XPATH, threads_locator)))
            total_threads = len(all_threads)

            if NUM_MESSAGES_TO_PROCESS != "all":
                total_threads = min(total_threads, NUM_MESSAGES_TO_PROCESS)

            print(f"Found {total_threads} total threads. Processing all...")

            for i in range(total_threads):
                try:
                    print(f"📨 Opening thread {i+1} of {total_threads}...")

                    # Re-fetch threads to avoid stale element issue
                    current_threads = self.wait.until(
                        EC.presence_of_all_elements_located((By.XPATH, threads_locator))
                    )

                    if i >= len(current_threads):
                        print(f"⚠️ Thread index {i} not found, skipping...")
                        continue

                    thread = current_threads[i]
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", thread)
                    thread.click()
                    time.sleep(3)

                    self.wait.until(EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.msg-s-message-list-container")
                    ))

                    try:
                        sender_element = self.wait.until(EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, "dt.msg-entity-lockup__entity-title-wrapper h2.msg-entity-lockup__entity-title")
                        ))
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", sender_element)
                        time.sleep(1)
                        sender_element.click()
                        time.sleep(3)
                    except Exception as e:
                        print(f"⚠️ Could not click sender's name: {e}")
                        continue

                    full_name = self._safe_get_text("h1.text-heading-xlarge")
                    title = self._safe_get_text("div.text-body-medium.break-words")
                    location = self._safe_get_text("span.text-body-small.inline.t-black--light.break-words")
                    pronouns = self._safe_get_text("span.text-body-small")
                    connection = self._safe_get_text("span.dist-value")

                    contact_info = ""
                    try:
                        contact_button = self.driver.find_element(By.CSS_SELECTOR, "a[href*='overlay/contact-info']")
                        self.driver.execute_script("arguments[0].click();", contact_button)
                        time.sleep(2)
                        try:
                            modal_section = self.wait.until(EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "section.pv-contact-info")
                            ))
                            contact_info = modal_section.text.strip()
                        except Exception:
                            try:
                                modal_section = self.driver.find_element(By.CSS_SELECTOR, "section.pv-contact-info__contact-type")
                                contact_info = modal_section.text.strip()
                            except Exception:
                                contact_info = ""
                        try:
                            close_btn = self.driver.find_element(By.CSS_SELECTOR, "button.artdeco-modal__dismiss")
                            self.driver.execute_script("arguments[0].click();", close_btn)
                            time.sleep(1)
                        except Exception:
                            pass
                    except Exception as ci_err:
                        print(f"⚠️ No contact info found for {full_name}: {ci_err}")

                    log_csv("logs/extracted_contacts.csv",
                            [datetime.now(), self.username, full_name, title, location, pronouns, connection, self.driver.current_url, contact_info])
                    print(f"✅ Extracted {full_name}")
                    contacts.append((full_name, title))

                    # Go back to messaging to refresh list
                    self.driver.get("https://www.linkedin.com/messaging/")
                    time.sleep(3)

                except Exception as e:
                    print(f"⚠️ Error reading thread {i+1}: {e}")
                    log_csv("logs/error_logs.csv", [datetime.now(), self.username, f"Thread {i+1}", str(e)])
                    self.driver.get("https://www.linkedin.com/messaging/")
                    time.sleep(3)
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
