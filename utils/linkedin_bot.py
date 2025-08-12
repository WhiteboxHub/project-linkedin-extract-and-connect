




# # import time
# # from datetime import datetime
# # from selenium.webdriver.common.by import By
# # from selenium.webdriver.support import expected_conditions as EC
# # from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
# # from utils.helpers import load_message
# # from utils.logger import log_csv
# # from utils.browser import setup_browser

# # class LinkedInBot:
# #     def __init__(self, username, password):
# #         self.username = username
# #         self.password = password
# #         self.message = load_message("messages/message.txt")
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
# #         time.sleep(10)
# #         self.main_window = self.driver.current_window_handle
# #         return

# #     def extract_recent_contacts(self):
# #         contacts = []
# #         try:
# #             # Fetch threads
# #             threads = self.wait.until(EC.presence_of_all_elements_located(
# #                 (By.XPATH, "//div[contains(@class, 'msg-conversations-container__convo-item-link')]")
# #             ))
# #             print(f"Found {len(threads)} total threads. Processing last 10...")
# #             threads = threads[:10]
# #             for i, thread in enumerate(threads, start=1):
# #                 try:
# #                     print(f"📨 Opening thread {i} of {len(threads)}...")
# #                     # Re-fetch threads to avoid stale elements
# #                     all_threads = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'msg-conversations-container__convo-item-link')]")
# #                     if i-1 < len(all_threads):
# #                         thread = all_threads[i-1]
# #                     self.driver.execute_script("arguments[0].scrollIntoView(true);", thread)
# #                     time.sleep(1)
# #                     thread.click()
# #                     time.sleep(3)
# #                     # Extract sender's profile
# #                     profile_block = self.wait.until(EC.presence_of_element_located(
# #                         (By.CSS_SELECTOR, "div.artdeco-entity-lockup__title.ember-view")
# #                     ))
# #                     name_link = profile_block.find_element(By.CSS_SELECTOR, "a")
# #                     profile_url = name_link.get_attribute("href")
# #                     # Open profile in new tab
# #                     self.driver.execute_script("window.open(arguments[0]);", profile_url)
# #                     time.sleep(5)
# #                     # Switch to profile tab
# #                     self.driver.switch_to.window(self.driver.window_handles[-1])
# #                     # Extract profile details
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
# #                         except Exception:
# #                             try:
# #                                 modal_section = self.driver.find_element(By.CSS_SELECTOR, "section.pv-contact-info__contact-type")
# #                                 contact_info = modal_section.text.strip()
# #                             except Exception:
# #                                 contact_info = ""
# #                         try:
# #                             close_btn = self.driver.find_element(By.CSS_SELECTOR, "button.artdeco-modal__dismiss")
# #                             self.driver.execute_script("arguments[0].click();", close_btn)
# #                             time.sleep(1)
# #                         except Exception:
# #                             try:
# #                                 from selenium.webdriver.common.keys import Keys
# #                                 body = self.driver.find_element(By.TAG_NAME, "body")
# #                                 body.send_keys(Keys.ESCAPE)
# #                             except Exception:
# #                                 pass
# #                     except Exception as ci_err:
# #                         print(f"⚠️ No contact info found for {full_name}: {ci_err}")
# #                     # Log extracted details
# #                     log_csv("logs/extracted_contacts.csv",
# #                             [datetime.now(), self.username, full_name, title, location, pronouns, connection, profile_url, contact_info])
# #                     print(f"✅ Extracted {full_name}")
# #                     contacts.append((full_name, title))
# #                     # Close profile tab and switch back to messages tab
# #                     self.driver.close()
# #                     self.driver.switch_to.window(self.main_window)
# #                     # Wait for messages list to reload
# #                     self.wait.until(EC.presence_of_element_located(
# #                         (By.CSS_SELECTOR, "div.msg-conversations-container__convo-item-link")
# #                     ))
# #                     time.sleep(2)
# #                 except Exception as e:
# #                     print(f"⚠️ Error reading thread {i}: {e}")
# #                     log_csv("logs/error_logs.csv", [datetime.now(), self.username, f"Thread {i}", str(e)])
# #                     try:
# #                         if len(self.driver.window_handles) > 1:
# #                             self.driver.close()
# #                         self.driver.switch_to.window(self.main_window)
# #                         self.wait.until(EC.presence_of_element_located(
# #                             (By.CSS_SELECTOR, "div.msg-conversations-container__convo-item-link")
# #                         ))
# #                     except Exception:
# #                         pass
# #                     continue
# #         except Exception as e:
# #             print(f"⚠️ Error in extract_recent_contacts: {e}")
# #             log_csv("logs/error_logs.csv", [datetime.now(), self.username, "extract_recent_contacts", str(e)])
# #         return contacts

# #     def _safe_get_text(self, selector):
# #         try:
# #             return self.driver.find_element(By.CSS_SELECTOR, selector).text.strip()
# #         except:
# #             return ""

# #     # def send_connection(self, name):
# #     #     self.driver.get(f"https://www.linkedin.com/search/results/people/?keywords={name}")
# #     #     time.sleep(5)
# #     #     try:
# #     #         connect_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Connect')]")))
# #     #         self.driver.execute_script("arguments[0].scrollIntoView();", connect_btn)
# #     #         connect_btn.click()
# #     #         time.sleep(2)
# #     #         try:
# #     #             add_note = self.driver.find_element(By.XPATH, "//button[contains(., 'Add a note')]")
# #     #             add_note.click()
# #     #             time.sleep(1)
# #     #             note_box = self.wait.until(EC.presence_of_element_located((By.NAME, 'message')))
# #     #             note_box.send_keys(self.message)
# #     #         except NoSuchElementException:
# #     #             print("No note option available")
# #     #         send_btn = self.driver.find_element(By.XPATH, "//button[contains(., 'Send')]")
# #     #         send_btn.click()
# #     #         log_csv("logs/connection_logs.csv", [datetime.now(), self.username, name, "Success", ""])
# #     #         print(f"✅ Connection sent to: {name}")
# #     #     except Exception as e:
# #     #         log_csv("logs/connection_logs.csv", [datetime.now(), self.username, name, "Failed", str(e)])
# #     #         print(f"❌ Failed to connect with: {name}")

# #     def run(self):
# #         try:
# #             self.login()
# #             self.go_to_messages()
# #             contacts = self.extract_recent_contacts()
# #             for name, _ in contacts:
# #                 self.send_connection(name)
# #                 time.sleep(10)
# #         except Exception as e:
# #             print(f"Error in {self.username}: {str(e)}")
# #         finally:
# #             self.driver.quit()









# import time
# from datetime import datetime
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
# from utils.helpers import load_message
# from utils.logger import log_csv
# from utils.browser import setup_browser

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

#     def extract_recent_contacts(self):
#         contacts = []
#         try:
#             threads = self.wait.until(EC.presence_of_all_elements_located(
#                 (By.XPATH, "//div[contains(@class, 'msg-conversations-container__convo-item-link')]")
#             ))
#             print(f"Found {len(threads)} total threads. Processing last 10...")
#             threads = threads[:10]
#             for i, thread in enumerate(threads, start=1):
#                 try:
#                     print(f"📨 Opening thread {i} of {len(threads)}...")
#                     all_threads = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'msg-conversations-container__convo-item-link')]")
#                     if i-1 < len(all_threads):
#                         thread = all_threads[i-1]
#                     self.driver.execute_script("arguments[0].scrollIntoView(true);", thread)
#                     time.sleep(1)
#                     thread.click()
#                     time.sleep(5)  # Wait for the chat to fully load

#                     # Scroll the profile card into view
#                     profile_card = self.wait.until(EC.presence_of_element_located(
#                         (By.CSS_SELECTOR, "div.msg-s-profile-card.msg-s-profile-card-one-to-one.ph3")
#                     ))
#                     self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", profile_card)
#                     time.sleep(3)  # Wait for the profile card to be visible

#                     # Extract sender's profile
#                     profile_block = self.wait.until(EC.presence_of_element_located(
#                         (By.CSS_SELECTOR, "div.artdeco-entity-lockup__title.ember-view")
#                     ))
#                     name_link = profile_block.find_element(By.CSS_SELECTOR, "a")
#                     profile_url = name_link.get_attribute("href")

#                     # Open profile in new tab
#                     self.driver.execute_script("window.open(arguments[0]);", profile_url)
#                     time.sleep(5)

#                     # Switch to profile tab
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
#                             try:
#                                 from selenium.webdriver.common.keys import Keys
#                                 body = self.driver.find_element(By.TAG_NAME, "body")
#                                 body.send_keys(Keys.ESCAPE)
#                             except Exception:
#                                 pass
#                     except Exception as ci_err:
#                         print(f"⚠️ No contact info found for {full_name}: {ci_err}")

#                     # Log extracted details
#                     log_csv("logs/extracted_contacts.csv",
#                             [datetime.now(), self.username, full_name, title, location, pronouns, connection, profile_url, contact_info])
#                     print(f"✅ Extracted {full_name}")
#                     contacts.append((full_name, title))

#                     # Close profile tab and switch back to messages tab
#                     self.driver.close()
#                     self.driver.switch_to.window(self.main_window)

#                     # Wait for messages list to reload
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

class LinkedInBot:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.message = load_message("messages/message.txt")
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
            threads = self.wait.until(EC.presence_of_all_elements_located(
                (By.XPATH, "//div[contains(@class, 'msg-conversations-container__convo-item-link')]")
            ))
            print(f"Found {len(threads)} total threads. Processing last 10...")
            threads = threads[:10]
            for i, thread in enumerate(threads, start=1):
                try:
                    print(f"📨 Opening thread {i} of {len(threads)}...")
                    all_threads = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'msg-conversations-container__convo-item-link')]")
                    if i-1 < len(all_threads):
                        thread = all_threads[i-1]
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", thread)
                    time.sleep(1)
                    thread.click()
                    time.sleep(5)  # Wait for chat to load

                    # Scroll the profile card into view
                    profile_card = self.wait.until(EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.msg-s-profile-card.msg-s-profile-card-one-to-one.ph3")
                    ))
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", profile_card)
                    time.sleep(3)  # Wait for profile card to be visible

                    # Extract sender's profile
                    profile_block = self.wait.until(EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.artdeco-entity-lockup__title.ember-view")
                    ))
                    name_link = profile_block.find_element(By.CSS_SELECTOR, "a")
                    profile_url = name_link.get_attribute("href")

                    # Open profile in new tab
                    self.driver.execute_script("window.open(arguments[0]);", profile_url)
                    time.sleep(5)

                    # Switch to profile tab
                    self.driver.switch_to.window(self.driver.window_handles[-1])

                    # Extract profile details
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
                            try:
                                from selenium.webdriver.common.keys import Keys
                                body = self.driver.find_element(By.TAG_NAME, "body")
                                body.send_keys(Keys.ESCAPE)
                            except Exception:
                                pass
                    except Exception as ci_err:
                        print(f"⚠️ No contact info found for {full_name}: {ci_err}")

                    # Log extracted details
                    log_csv("logs/extracted_contacts.csv",
                            [datetime.now(), self.username, full_name, title, location, pronouns, connection, profile_url, contact_info])
                    print(f"✅ Extracted {full_name}")
                    contacts.append((full_name, title))

                    # Close profile tab and switch back to messages tab
                    self.driver.close()
                    self.driver.switch_to.window(self.main_window)

                    # Wait for messages list to reload
                    self.wait.until(EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.msg-conversations-container__convo-item-link")
                    ))
                    time.sleep(2)

                except Exception as e:
                    print(f"⚠️ Error reading thread {i}: {e}")
                    log_csv("logs/error_logs.csv", [datetime.now(), self.username, f"Thread {i}", str(e)])
                    try:
                        if len(self.driver.window_handles) > 1:
                            self.driver.close()
                        self.driver.switch_to.window(self.main_window)
                        self.wait.until(EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "div.msg-conversations-container__convo-item-link")
                        ))
                    except Exception:
                        pass
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
