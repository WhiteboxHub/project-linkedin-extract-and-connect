









# # # import time
# # # from datetime import datetime
# # # from selenium.webdriver.common.by import By
# # # from selenium.webdriver.support import expected_conditions as EC
# # # from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
# # # from utils.helpers import load_message
# # # from utils.logger import log_csv
# # # from utils.browser import setup_browser
# # # from config import NUM_MESSAGES_TO_PROCESS

# # # class LinkedInBot:
# # #     def __init__(self, username, password):
# # #         self.username = username
# # #         self.password = password
# # #         self.message = load_message("messages/message.txt")
# # #         self.driver, self.wait = setup_browser()
# # #         self.main_window = None

# # #     def login(self):
# # #         self.driver.get("https://www.linkedin.com/login")
# # #         self.wait.until(EC.presence_of_element_located((By.ID, 'username'))).send_keys(self.username)
# # #         self.driver.find_element(By.ID, 'password').send_keys(self.password)
# # #         self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
# # #         self.wait.until(EC.url_contains("feed"))
# # #         print(f"✅ Logged in: {self.username}")
# # #         time.sleep(3)

# # #     def go_to_messages(self):
# # #         self.driver.get("https://www.linkedin.com/messaging/")
# # #         time.sleep(10)
# # #         self.main_window = self.driver.current_window_handle
# # #         return

# # #     def _scroll_to_top_of_chat(self):
# # #         """Scroll to the top of the current chat conversation"""
# # #         try:
# # #             # First wait for the message list to be present
# # #             message_list = self.wait.until(EC.presence_of_element_located(
# # #                 (By.CSS_SELECTOR, "div.msg-s-message-list.full-width.scrollable")
# # #             ))
            
# # #             # Scroll to top with smooth behavior
# # #             self.driver.execute_script("""
# # #                 arguments[0].scrollTo({
# # #                     top: 0,
# # #                     behavior: 'smooth'
# # #                 });
# # #             """, message_list)
            
# # #             # Wait for scroll to complete
# # #             time.sleep(2)
            
# # #             # Additional check to ensure we're at the top
# # #             scroll_position = self.driver.execute_script("return arguments[0].scrollTop", message_list)
# # #             if scroll_position > 100:  # If not at top, try again
# # #                 self.driver.execute_script("arguments[0].scrollTop = 0;", message_list)
# # #                 time.sleep(1)
            
# # #             return True
# # #         except Exception as e:
# # #             print(f"⚠️ Error scrolling chat: {e}")
# # #             return False

# # #     def extract_recent_contacts(self):
# # #         contacts = []
# # #         try:
# # #             # Get all conversation threads
# # #             threads = self.wait.until(EC.presence_of_all_elements_located(
# # #                 (By.XPATH, "//div[contains(@class, 'msg-conversations-container__convo-item-link')]")
# # #             ))

# # #             if NUM_MESSAGES_TO_PROCESS == "all":
# # #                 print(f"Found {len(threads)} total threads. Processing all...")
# # #                 threads_to_process = threads
# # #             else:
# # #                 print(f"Found {len(threads)} total threads. Processing last {NUM_MESSAGES_TO_PROCESS}...")
# # #                 threads_to_process = threads[:NUM_MESSAGES_TO_PROCESS]

# # #             for i, thread in enumerate(threads_to_process, start=1):
# # #                 try:
# # #                     print(f"📨 Opening thread {i} of {len(threads_to_process)}...")
                    
# # #                     # Re-find thread to avoid staleness
# # #                     current_threads = self.driver.find_elements(
# # #                         By.XPATH, "//div[contains(@class, 'msg-conversations-container__convo-item-link')]"
# # #                     )
# # #                     if i-1 < len(current_threads):
# # #                         thread = current_threads[i-1]
                    
# # #                     # Scroll to and click the thread
# # #                     self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", thread)
# # #                     thread.click()
# # #                     time.sleep(3)  # Wait for click to register
                    
# # #                     # Wait for chat container to load
# # #                     self.wait.until(EC.presence_of_element_located(
# # #                         (By.CSS_SELECTOR, "div.msg-s-message-list-container")
# # #                     ))
                    
# # #                     # Scroll to top of chat - this is the critical fix
# # #                     if not self._scroll_to_top_of_chat():
# # #                         print("⚠️ Retrying scroll...")
# # #                         time.sleep(2)
# # #                         self._scroll_to_top_of_chat()
                    
# # #                     # Wait for profile card to load
# # #                     profile_card = self.wait.until(EC.visibility_of_element_located(
# # #                         (By.CSS_SELECTOR, "div.msg-s-profile-card.msg-s-profile-card-one-to-one.ph3")
# # #                     ))
                    
# # #                     # Scroll profile card into view
# # #                     self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", profile_card)
# # #                     time.sleep(2)

# # #                     # Rest of your profile extraction logic remains exactly the same...
# # #                     profile_block = self.wait.until(EC.visibility_of_element_located(
# # #                         (By.CSS_SELECTOR, "div.artdeco-entity-lockup__title.ember-view")
# # #                     ))
# # #                     name_link = profile_block.find_element(By.CSS_SELECTOR, "a")
# # #                     profile_url = name_link.get_attribute("href")

# # #                     # Open profile in new tab
# # #                     self.driver.execute_script("window.open(arguments[0]);", profile_url)
# # #                     time.sleep(3)
# # #                     self.driver.switch_to.window(self.driver.window_handles[-1])

# # #                     # Extract profile details
# # #                     full_name = self._safe_get_text("h1.text-heading-xlarge")
# # #                     title = self._safe_get_text("div.text-body-medium.break-words")
# # #                     location = self._safe_get_text("span.text-body-small.inline.t-black--light.break-words")
# # #                     pronouns = self._safe_get_text("span.text-body-small")
# # #                     connection = self._safe_get_text("span.dist-value")

# # #                     contact_info = ""
# # #                     try:
# # #                         contact_button = self.driver.find_element(By.CSS_SELECTOR, "a[href*='overlay/contact-info']")
# # #                         self.driver.execute_script("arguments[0].click();", contact_button)
# # #                         time.sleep(2)
# # #                         try:
# # #                             modal_section = self.wait.until(EC.presence_of_element_located(
# # #                                 (By.CSS_SELECTOR, "section.pv-contact-info")
# # #                             ))
# # #                             contact_info = modal_section.text.strip()
# # #                         except Exception:
# # #                             try:
# # #                                 modal_section = self.driver.find_element(By.CSS_SELECTOR, "section.pv-contact-info__contact-type")
# # #                                 contact_info = modal_section.text.strip()
# # #                             except Exception:
# # #                                 contact_info = ""
# # #                         try:
# # #                             close_btn = self.driver.find_element(By.CSS_SELECTOR, "button.artdeco-modal__dismiss")
# # #                             self.driver.execute_script("arguments[0].click();", close_btn)
# # #                             time.sleep(1)
# # #                         except Exception:
# # #                             pass
# # #                     except Exception as ci_err:
# # #                         print(f"⚠️ No contact info found for {full_name}: {ci_err}")

# # #                     # Log details
# # #                     log_csv("logs/extracted_contacts.csv",
# # #                             [datetime.now(), self.username, full_name, title, location, pronouns, connection, profile_url, contact_info])
# # #                     print(f"✅ Extracted {full_name}")
# # #                     contacts.append((full_name, title))

# # #                     # Close profile tab and return to messages
# # #                     self.driver.close()
# # #                     self.driver.switch_to.window(self.main_window)
# # #                     self.wait.until(EC.presence_of_element_located(
# # #                         (By.CSS_SELECTOR, "div.msg-conversations-container__convo-item-link")
# # #                     ))
# # #                     time.sleep(2)

# # #                 except Exception as e:
# # #                     print(f"⚠️ Error reading thread {i}: {e}")
# # #                     log_csv("logs/error_logs.csv", [datetime.now(), self.username, f"Thread {i}", str(e)])
# # #                     try:
# # #                         if len(self.driver.window_handles) > 1:
# # #                             self.driver.close()
# # #                         self.driver.switch_to.window(self.main_window)
# # #                         self.wait.until(EC.presence_of_element_located(
# # #                             (By.CSS_SELECTOR, "div.msg-conversations-container__convo-item-link")
# # #                         ))
# # #                     except Exception:
# # #                         pass
# # #                     continue
# # #         except Exception as e:
# # #             print(f"⚠️ Error in extract_recent_contacts: {e}")
# # #             log_csv("logs/error_logs.csv", [datetime.now(), self.username, "extract_recent_contacts", str(e)])
# # #         return contacts

# # #     def _safe_get_text(self, selector):
# # #         try:
# # #             return self.driver.find_element(By.CSS_SELECTOR, selector).text.strip()
# # #         except:
# # #             return ""

# # #     def run(self):
# # #         try:
# # #             self.login()
# # #             self.go_to_messages()
# # #             self.extract_recent_contacts()
# # #         except Exception as e:
# # #             print(f"Error in {self.username}: {str(e)}")
# # #         finally:
# # #             self.driver.quit()



# # import time
# # from datetime import datetime
# # from selenium.webdriver.common.by import By
# # from selenium.webdriver.support import expected_conditions as EC
# # from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
# # from utils.helpers import load_message
# # from utils.logger import log_csv
# # from utils.browser import setup_browser
# # import yaml
# # import os

# # # Load values from config.yaml
# # CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
# # with open(CONFIG_PATH, "r") as f:
# #     config_data = yaml.safe_load(f)

# # NUM_MESSAGES_TO_PROCESS = config_data.get("NUM_MESSAGES_TO_PROCESS", "all")

# # class LinkedInBot:
# #     def __init__(self, username, password):
# #         self.username = username
# #         self.password = password
# #         self.driver, self.wait = setup_browser()
# #         self.main_window = None

# #     def login(self):
# #         self.driver.get("https://www.linkedin.com/login")
# #         self.wait.until(EC.presence_of_element_located((By.ID, 'username'))).send_keys(self.username)
# #         self.driver.find_element(By.ID, 'password').send_keys(self.password)
# #         self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
# #         self.wait.until(EC.url_contains("feed"))
# #         print(f"✅ Logged in: {self.username}")
# #         time.sleep(3)

# #     def go_to_messages(self):
# #         self.driver.get("https://www.linkedin.com/messaging/")
# #         time.sleep(5)
# #         self.main_window = self.driver.current_window_handle
# #         self._scroll_to_load_all_threads()
# #         return

# #     def _scroll_to_load_all_threads(self):
# #         threads_locator = "//div[contains(@class, 'msg-conversations-container__convo-item-link')]"
# #         last_count = 0
# #         while True:
# #             threads = self.wait.until(
# #                 EC.presence_of_all_elements_located((By.XPATH, threads_locator))
# #             )
# #             if len(threads) > last_count:
# #                 last_count = len(threads)
# #                 self.driver.execute_script("arguments[0].scrollIntoView({block: 'end'});", threads[-1])
# #                 time.sleep(1.5)
# #             else:
# #                 break
# #         print(f"Found {last_count} total threads. Processing...")

# #     def extract_recent_contacts(self):
# #         contacts = []
# #         threads_locator = "//div[contains(@class, 'msg-conversations-container__convo-item-link')]"

# #         all_threads = self.wait.until(
# #             EC.presence_of_all_elements_located((By.XPATH, threads_locator))
# #         )

# #         total_threads = len(all_threads)
# #         if NUM_MESSAGES_TO_PROCESS != "all":
# #             total_threads = min(total_threads, int(NUM_MESSAGES_TO_PROCESS))

# #         for i in range(total_threads):
# #             try:
# #                 print(f"📨 Opening thread {i+1} of {total_threads}...")

# #                 current_threads = self.wait.until(
# #                     EC.presence_of_all_elements_located((By.XPATH, threads_locator))
# #                 )

# #                 if i >= len(current_threads):
# #                     print(f"⚠️ Thread index {i} not found, skipping...")
# #                     continue

# #                 thread = current_threads[i]
# #                 self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", thread)
# #                 thread.click()
# #                 time.sleep(2)

# #                 self.wait.until(EC.presence_of_element_located(
# #                     (By.CSS_SELECTOR, "div.msg-s-message-list-container")
# #                 ))

# #                 try:
# #                     sender_element = self.wait.until(EC.element_to_be_clickable(
# #                         (By.CSS_SELECTOR, "dt.msg-entity-lockup__entity-title-wrapper h2.msg-entity-lockup__entity-title a")
# #                     ))

# #                     # Open sender in a new tab
# #                     profile_url = sender_element.get_attribute("href")
# #                     self.driver.execute_script("window.open(arguments[0]);", profile_url)

# #                     # Switch to new tab
# #                     self.driver.switch_to.window(self.driver.window_handles[-1])

# #                     time.sleep(3)

# #                     full_name = self._safe_get_text("h1.text-heading-xlarge")
# #                     title = self._safe_get_text("div.text-body-medium.break-words")
# #                     location = self._safe_get_text("span.text-body-small.inline.t-black--light.break-words")
# #                     pronouns = self._safe_get_text("span.text-body-small")
# #                     connection = self._safe_get_text("span.dist-value")

# #                     contact_info = ""
# #                     try:
# #                         contact_button = self.driver.find_element(By.CSS_SELECTOR, "a[href*='overlay/contact-info']")
# #                         self.driver.execute_script("arguments[0].click();", contact_button)
# #                         time.sleep(2)
# #                         try:
# #                             modal_section = self.wait.until(EC.presence_of_element_located(
# #                                 (By.CSS_SELECTOR, "section.pv-contact-info")
# #                             ))
# #                             contact_info = modal_section.text.strip()
# #                         except:
# #                             try:
# #                                 modal_section = self.driver.find_element(By.CSS_SELECTOR, "section.pv-contact-info__contact-type")
# #                                 contact_info = modal_section.text.strip()
# #                             except:
# #                                 contact_info = ""
# #                         try:
# #                             close_btn = self.driver.find_element(By.CSS_SELECTOR, "button.artdeco-modal__dismiss")
# #                             self.driver.execute_script("arguments[0].click();", close_btn)
# #                             time.sleep(1)
# #                         except:
# #                             pass
# #                     except:
# #                         print(f"⚠️ No contact info found for {full_name}")

# #                     log_csv("logs/extracted_contacts.csv",
# #                             [datetime.now(), self.username, full_name, title, location, pronouns, connection, self.driver.current_url, contact_info])
# #                     print(f"✅ Extracted {full_name}")
# #                     contacts.append((full_name, title))

# #                     # Close the new tab and return to messaging list
# #                     self.driver.close()
# #                     self.driver.switch_to.window(self.main_window)

# #                 except Exception as e:
# #                     print(f"⚠️ Could not open sender's profile: {e}")
# #                     continue

# #             except Exception as e:
# #                 print(f"⚠️ Error reading thread {i+1}: {e}")
# #                 log_csv("logs/error_logs.csv", [datetime.now(), self.username, f"Thread {i+1}", str(e)])
# #                 continue

# #         return contacts

# #     def _safe_get_text(self, selector):
# #         try:
# #             return self.driver.find_element(By.CSS_SELECTOR, selector).text.strip()
# #         except:
# #             return ""

# #     def run(self):
# #         try:
# #             self.login()
# #             self.go_to_messages()
# #             self.extract_recent_contacts()
# #         except Exception as e:
# #             print(f"Error in {self.username}: {str(e)}")
# #         finally:
# #             self.driver.quit()






# import time
# from datetime import datetime
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import TimeoutException
# from utils.logger import log_csv
# from utils.browser import setup_browser
# import yaml
# import os

# # Load config
# CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
# abs_config_path = os.path.abspath(CONFIG_PATH)

# print("Looking for config at:", abs_config_path)

# # Load config or use defaults if not found
# try:
#     with open(abs_config_path, "r", encoding="utf-8") as f:
#         config_data = yaml.safe_load(f) or {}
# except FileNotFoundError:
#     print(f"Warning: config.yaml not found at {abs_config_path}. Using defaults.")
#     config_data = {}


# NUM_MESSAGES_TO_PROCESS = config_data.get("NUM_MESSAGES_TO_PROCESS", "all")

# class LinkedInBot:
#     def __init__(self, username, password):
#         self.username = username
#         self.password = password
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
#         time.sleep(5)
#         self.main_window = self.driver.current_window_handle
#         self._scroll_to_load_threads()

#     def _scroll_to_load_threads(self):
#         """Scroll until all or required number of threads are loaded."""
#         last_height = self.driver.execute_script(
#             "return document.querySelector('.msg-conversations-container__conversations-list').scrollHeight"
#         )
#         loaded_threads = 0
#         while True:
#             threads = self.driver.find_elements(
#                 By.XPATH, "//div[contains(@class, 'msg-conversations-container__convo-item-link')]"
#             )
#             loaded_threads = len(threads)

#             if NUM_MESSAGES_TO_PROCESS != "all" and loaded_threads >= int(NUM_MESSAGES_TO_PROCESS):
#                 break

#             self.driver.execute_script(
#                 "document.querySelector('.msg-conversations-container__conversations-list').scrollTo(0, arguments[0]);",
#                 last_height
#             )
#             time.sleep(2)
#             new_height = self.driver.execute_script(
#                 "return document.querySelector('.msg-conversations-container__conversations-list').scrollHeight"
#             )
#             if new_height == last_height:  # no more threads to load
#                 break
#             last_height = new_height

#         print(f"📜 Found {loaded_threads} total threads. Processing...")

#     def extract_recent_contacts(self):
#         contacts = []
#         try:
#             threads_locator = "//div[contains(@class, 'msg-conversations-container__convo-item-link')]"
#             all_threads = self.driver.find_elements(By.XPATH, threads_locator)

#             total_threads = len(all_threads)
#             if NUM_MESSAGES_TO_PROCESS != "all":
#                 total_threads = min(total_threads, int(NUM_MESSAGES_TO_PROCESS))

#             for i in range(total_threads):
#                 try:
#                     print(f"📨 Opening thread {i+1} of {total_threads}...")
#                     current_threads = self.driver.find_elements(By.XPATH, threads_locator)
#                     thread = current_threads[i]
#                     self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", thread)
#                     thread.click()
#                     time.sleep(2)

#                     # Get profile link if available
#                     try:
#                         profile_link_el = self.driver.find_element(By.CSS_SELECTOR, "a[href*='/in/']")
#                         profile_url = profile_link_el.get_attribute("href")
#                     except:
#                         print("⚠️ No profile link found (group/system/archived). Skipping...")
#                         continue

#                     # Open profile in a new tab
#                     self.driver.execute_script("window.open(arguments[0]);", profile_url)
#                     self.driver.switch_to.window(self.driver.window_handles[-1])
#                     time.sleep(3)

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
#                             modal_section = self.wait.until(
#                                 EC.presence_of_element_located((By.CSS_SELECTOR, "section.pv-contact-info"))
#                             )
#                             contact_info = modal_section.text.strip()
#                         except:
#                             pass
#                         try:
#                             close_btn = self.driver.find_element(By.CSS_SELECTOR, "button.artdeco-modal__dismiss")
#                             self.driver.execute_script("arguments[0].click();", close_btn)
#                         except:
#                             pass
#                     except:
#                         pass

#                     # Log extracted data
#                     log_csv(
#                         "logs/extracted_contacts.csv",
#                         [datetime.now(), self.username, full_name, title, location, pronouns, connection, profile_url, contact_info]
#                     )
#                     print(f"✅ Extracted {full_name}")
#                     contacts.append((full_name, title))

#                     # Close profile tab and return to main tab
#                     self.driver.close()
#                     self.driver.switch_to.window(self.main_window)
#                     time.sleep(1)

#                 except Exception as e:
#                     print(f"⚠️ Error reading thread {i+1}: {e}")
#                     log_csv("logs/error_logs.csv", [datetime.now(), self.username, f"Thread {i+1}", str(e)])
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






# import time
# from datetime import datetime
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import TimeoutException
# from utils.logger import log_csv
# from utils.browser import setup_browser
# from utils.db import insert_contact   # ⬅️ Added this line
# import yaml
# import os

# # Load config
# CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
# abs_config_path = os.path.abspath(CONFIG_PATH)

# print("Looking for config at:", abs_config_path)

# # Load config or use defaults if not found
# try:
#     with open(abs_config_path, "r", encoding="utf-8") as f:
#         config_data = yaml.safe_load(f) or {}
# except FileNotFoundError:
#     print(f"Warning: config.yaml not found at {abs_config_path}. Using defaults.")
#     config_data = {}


# NUM_MESSAGES_TO_PROCESS = config_data.get("NUM_MESSAGES_TO_PROCESS", "all")

# class LinkedInBot:
#     def __init__(self, username, password):
#         self.username = username
#         self.password = password
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
#         time.sleep(5)
#         self.main_window = self.driver.current_window_handle
#         self._scroll_to_load_threads()

#     def _scroll_to_load_threads(self):
#         """Scroll until all or required number of threads are loaded."""
#         last_height = self.driver.execute_script(
#             "return document.querySelector('.msg-conversations-container__conversations-list').scrollHeight"
#         )
#         loaded_threads = 0
#         while True:
#             threads = self.driver.find_elements(
#                 By.XPATH, "//div[contains(@class, 'msg-conversations-container__convo-item-link')]"
#             )
#             loaded_threads = len(threads)

#             if NUM_MESSAGES_TO_PROCESS != "all" and loaded_threads >= int(NUM_MESSAGES_TO_PROCESS):
#                 break

#             self.driver.execute_script(
#                 "document.querySelector('.msg-conversations-container__conversations-list').scrollTo(0, arguments[0]);",
#                 last_height
#             )
#             time.sleep(2)
#             new_height = self.driver.execute_script(
#                 "return document.querySelector('.msg-conversations-container__conversations-list').scrollHeight"
#             )
#             if new_height == last_height:  # no more threads to load
#                 break
#             last_height = new_height

#         print(f"📜 Found {loaded_threads} total threads. Processing...")

#     def extract_recent_contacts(self):
#         contacts = []
#         try:
#             threads_locator = "//div[contains(@class, 'msg-conversations-container__convo-item-link')]"
#             all_threads = self.driver.find_elements(By.XPATH, threads_locator)

#             total_threads = len(all_threads)
#             if NUM_MESSAGES_TO_PROCESS != "all":
#                 total_threads = min(total_threads, int(NUM_MESSAGES_TO_PROCESS))

#             for i in range(total_threads):
#                 try:
#                     print(f"📨 Opening thread {i+1} of {total_threads}...")
#                     current_threads = self.driver.find_elements(By.XPATH, threads_locator)
#                     thread = current_threads[i]
#                     self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", thread)
#                     thread.click()
#                     time.sleep(2)

#                     # Get profile link if available
#                     try:
#                         profile_link_el = self.driver.find_element(By.CSS_SELECTOR, "a[href*='/in/']")
#                         profile_url = profile_link_el.get_attribute("href")
#                     except:
#                         print("⚠️ No profile link found (group/system/archived). Skipping...")
#                         continue

#                     # Open profile in a new tab
#                     self.driver.execute_script("window.open(arguments[0]);", profile_url)
#                     self.driver.switch_to.window(self.driver.window_handles[-1])
#                     time.sleep(3)

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
#                             modal_section = self.wait.until(
#                                 EC.presence_of_element_located((By.CSS_SELECTOR, "section.pv-contact-info"))
#                             )
#                             contact_info = modal_section.text.strip()
#                         except:
#                             pass
#                         try:
#                             close_btn = self.driver.find_element(By.CSS_SELECTOR, "button.artdeco-modal__dismiss")
#                             self.driver.execute_script("arguments[0].click();", close_btn)
#                         except:
#                             pass
#                     except:
#                         pass

#                     # Log extracted data (CSV)
#                     log_csv(
#                         "logs/extracted_contacts.csv",
#                         [
#                             datetime.now(),
#                             self.username,
#                             full_name,
#                             title,
#                             location,
#                             pronouns,
#                             connection,
#                             profile_url,
#                             contact_info
#                         ]
#                     )

#                     # Also save to DB
#                     linkedin_id = profile_url.rstrip("/").split("/")[-1]

#                     insert_contact(
#                         full_name if full_name else None,
#                         self.username,          # treating logged-in user as "source_email"
#                         None,                   # extracted email (if available, replace None)
#                         None,                   # extracted phone (if available, replace None)
#                         linkedin_id,
#                         title if title else None,
#                         location if location else None
#                     )

#                     print(f"✅ Extracted + Saved {full_name} to DB")
#                     contacts.append((full_name, title))

#                     # Close profile tab and return to main tab
#                     self.driver.close()
#                     self.driver.switch_to.window(self.main_window)
#                     time.sleep(1)

#                 except Exception as e:
#                     print(f"⚠️ Error reading thread {i+1}: {e}")
#                     log_csv("logs/error_logs.csv", [datetime.now(), self.username, f"Thread {i+1}", str(e)])
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

                    # Determine which LinkedIn ID to use (prefer public URL slug)
                    linkedin_id = profile_url.rstrip("/").split("/")[-1]  # Default to original ID
                    if contact_info['public_linkedin']:
                        # Try to get the public URL slug
                        public_url = contact_info['public_linkedin'].rstrip("/")
                        if '/in/' in public_url:
                            linkedin_id = public_url.split('/in/')[-1]

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
                        linkedin_id,
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
            