

# import random
# import time
# import logging
# import yaml
# import csv
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import (
#     TimeoutException,
#     StaleElementReferenceException,
#     ElementClickInterceptedException,
#     InvalidSelectorException,
#     NoSuchElementException,
# )
# from webdriver_manager.chrome import ChromeDriverManager

# # Configure logging
# logging.basicConfig(
#     level=logging.DEBUG,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler('linkedin_bot_debug.log'),
#         logging.StreamHandler()
#     ]
# )

# def load_accounts(file_path):
#     """Load accounts from YAML file."""
#     try:
#         with open(file_path, "r") as f:
#             data = yaml.safe_load(f)
#         return data.get("accounts", [])
#     except Exception as e:
#         logging.error(f"Failed to load accounts: {str(e)}", exc_info=True)
#         return []

# def load_message(file_path):
#     """Load connection message from YAML config."""
#     try:
#         with open(file_path, "r") as f:
#             data = yaml.safe_load(f)
#         return data.get("message", "Hi, I'd like to connect with you!")
#     except Exception as e:
#         logging.error(f"Failed to load message: {str(e)}", exc_info=True)
#         return "Hi, I'd like to connect with you!"

# def load_profile_urls_from_csv(file_path):
#     """Read LinkedIn profile URLs from CSV file."""
#     urls = []
#     try:
#         with open(file_path, "r", encoding="utf-8") as csvfile:
#             reader = csv.reader(csvfile)
#             for row in reader:
#                 if len(row) >= 8:
#                     url = row[7].strip()
#                     if url.startswith("https://www.linkedin.com/in/"):
#                         urls.append(url)
#         logging.info(f"Loaded {len(urls)} profile URLs from CSV.")
#     except Exception as e:
#         logging.error(f"Failed to read profile URLs from CSV: {str(e)}", exc_info=True)
#     return urls

# class LinkedInBot:
#     def __init__(self, username, password):
#         self.username = username
#         self.password = password
#         self.driver = None
#         self.wait = None

#     def start_browser(self):
#         """Start Chrome browser with options."""
#         try:
#             options = Options()
#             options.add_argument("--start-maximized")
#             options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
#             options.add_argument("--disable-blink-features=AutomationControlled")
#             self.driver = webdriver.Chrome(
#                 service=Service(ChromeDriverManager().install()),
#                 options=options
#             )
#             self.wait = WebDriverWait(self.driver, 30)  # Increased wait time
#             logging.info("Browser started successfully.")
#         except Exception as e:
#             logging.error(f"Failed to start browser: {str(e)}", exc_info=True)
#             raise

#     def login(self):
#         """Log in to LinkedIn."""
#         try:
#             logging.info(f"Logging in as {self.username}...")
#             self.driver.get("https://www.linkedin.com/login")
#             self.wait.until(
#                 EC.presence_of_element_located((By.ID, "username"))
#             ).send_keys(self.username)
#             self.driver.find_element(By.ID, "password").send_keys(self.password)
#             self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
#             self.wait.until(EC.url_contains("feed"))
#             logging.info(f"Successfully logged in: {self.username}")
#             time.sleep(random.uniform(3, 7))
#         except Exception as e:
#             logging.error(f"Login failed: {str(e)}", exc_info=True)
#             self.driver.save_screenshot('debug_login.png')
#             raise

#     def click_more_actions(self):
#         try:
#             self.wait.until(
#                 EC.presence_of_element_located(
#                     (By.CSS_SELECTOR, "section.artdeco-card[data-member-id]")
#                 )
#             )
#             logging.info("Profile page fully loaded.")

#             locators = [
#                 (By.CSS_SELECTOR, "div.HZVlqmhRoGLChHcOHQXZHBCczivbLdHU button[aria-label='More actions']"),
#                 (By.XPATH, "//button[@aria-label='More actions']"),
#                 (By.XPATH, "//button[contains(@aria-label, 'More actions')]"),
#                 (By.CSS_SELECTOR, "button#ember110-profile-overflow-action"),
#                 (By.XPATH, "//button[@id='ember110-profile-overflow-action']"),
#                 (By.CSS_SELECTOR, "button.artdeco-dropdown__trigger[aria-label='More actions']"),
#                 (By.XPATH, "//div[contains(@class, 'pv-top-card')]//button[@aria-label='More actions']"),
#             ]

#             for locator in locators:
#                 try:
#                     more_button = self.wait.until(
#                         EC.presence_of_element_located(locator)
#                     )
#                     logging.info(f"Found 'More actions' button using locator: {locator}")
#                     self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", more_button)
#                     self.driver.execute_script("arguments[0].click();", more_button)
#                     logging.info("Clicked 'More actions' button.")
#                     time.sleep(random.uniform(2, 4))
#                     return
#                 except Exception as e:
#                     logging.warning(f"Locator {locator} failed: {str(e)}")
#                     continue

#             logging.error("No 'More actions' button found.")
#             self.driver.save_screenshot('debug_no_more_actions_button.png')
#             raise Exception("No 'More actions' button found.")
#         except Exception as e:
#             logging.error(f"Error clicking 'More actions' button: {str(e)}", exc_info=True)
#             self.driver.save_screenshot('debug_more_actions_error.png')
#             raise

#     def click_connect(self):
#         """Click the 'Connect' option from the dropdown."""
#         try:
#             logging.info("Waiting for 'Connect' option to be clickable...")
#             connect_option = self.wait.until(
#                 EC.element_to_be_clickable(
#                     (By.XPATH, "//div[contains(@aria-label, 'Invite') and contains(@aria-label, 'to connect')]")
#                 )
#             )
#             logging.info("Found 'Connect' option.")
#             self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", connect_option)
#             self.driver.execute_script("arguments[0].click();", connect_option)
#             logging.info("Clicked 'Connect' option.")
#             time.sleep(random.uniform(2, 4))
#         except Exception as e:
#             logging.error(f"Error clicking 'Connect' option: {str(e)}", exc_info=True)
#             self.driver.save_screenshot('debug_connect_error.png')
#             raise

#     def is_profile_restricted(self):
#         """Check if the profile is restricted."""
#         try:
#             restricted_check = self.driver.find_elements(
#                 By.XPATH,
#                 "//*[contains(text(), 'This profile is restricted')]"
#             )
#             if not restricted_check:
#                 restricted_check = self.driver.find_elements(
#                     By.XPATH,
#                     "//*[contains(text(), 'You can't connect with this person')]"
#                 )
#             return len(restricted_check) > 0
#         except InvalidSelectorException as e:
#             logging.error(f"Invalid XPath: {str(e)}", exc_info=True)
#             return False
#         except Exception as e:
#             logging.error(f"Error checking if profile is restricted: {str(e)}", exc_info=True)
#             return False

#     def send_connection_with_note(self, profile_url, note_text):
#         """Send a connection request with a note."""
#         try:
#             self.driver.get(profile_url)
#             logging.info(f"Navigated to profile: {profile_url}")
#             time.sleep(random.uniform(5, 10))

#             if self.is_profile_restricted():
#                 logging.error(f"Profile is restricted: {profile_url}")
#                 self.driver.save_screenshot('debug_restricted_profile.png')
#                 return

#             # Try direct connect button first
#             try:
#                 direct_connect_btn = self.wait.until(
#                     EC.presence_of_element_located((
#                         By.CSS_SELECTOR,
#                         "div.ph5.pb5 button.artdeco-button[aria-label^='Invite'][id^='ember']:has(> svg[data-test-icon='connect-small'])"
#                     ))
#                 )
#                 logging.info("Found direct 'Connect' button. Clicking it...")
#                 self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", direct_connect_btn)
#                 self.driver.execute_script("arguments[0].click();", direct_connect_btn)
#                 time.sleep(random.uniform(2, 4))
#             except TimeoutException:
#                 logging.info("Direct 'Connect' button not found. Using More actions flow...")
#                 self.click_more_actions()
#                 self.click_connect()

#             # Wait for connection modal
#             self.wait.until(EC.visibility_of_element_located(
#                 (By.XPATH, "//div[@role='dialog']")
#             ))

#             try:
#                 add_note_btn = self.wait.until(
#                     EC.element_to_be_clickable(
#                         (By.XPATH, "//button[contains(@aria-label, 'Add a free note')]")
#                     )
#                 )
#                 add_note_btn.click()
#                 logging.info("Clicked 'Add a free note'.")

#                 note_box = self.wait.until(
#                     EC.presence_of_element_located(
#                         (By.XPATH, "//textarea[@name='message']")
#                     )
#                 )
#                 note_box.clear()
#                 note_box.send_keys(note_text)
#                 logging.info("Entered note text.")
#             except (NoSuchElementException, TimeoutException):
#                 logging.warning("Couldn't find 'Add a free note'. Sending basic connection request.")

#             send_btn = self.wait.until(
#                 EC.element_to_be_clickable(
#                     (By.XPATH, "//button[contains(@aria-label, 'Send')]")
#                 )
#             )
#             send_btn.click()
#             logging.info(f"Connection request sent to {profile_url}.")
#             time.sleep(random.uniform(3, 6))

#         except Exception as e:
#             logging.error(f"Could not send request to {profile_url}: {str(e)}", exc_info=True)
#             self.driver.save_screenshot('debug_connection_error.png')
#             raise

#     def run(self, profile_url, note_text):
#         """Run the bot for a single profile."""
#         try:
#             self.start_browser()
#             self.login()
#             self.send_connection_with_note(profile_url, note_text)
#         except Exception as e:
#             logging.error(f"Bot run failed: {str(e)}", exc_info=True)
#         finally:
#             if self.driver:
#                 self.driver.quit()
#                 logging.info("Browser closed.")

# if __name__ == "__main__":
#     accounts = load_accounts("credentials/accounts.yaml")
#     message_text = load_message("config.yaml")
#     urls = load_profile_urls_from_csv("logs/extracted_contacts.csv")

#     if accounts and urls:
#         acc = accounts[0]  # Pick first account
#         bot = LinkedInBot(acc['username'], acc['password'])

#         try:
#             bot.start_browser()
#             bot.login()

#             for url in urls:
#                 try:
#                     bot.send_connection_with_note(url, message_text)
#                 except Exception as e:
#                     logging.error(f"Failed for {url}: {str(e)}", exc_info=True)
#                     continue  # Skip and go to the next profile

#         finally:
#             if bot.driver:
#                 bot.driver.quit()
#                 logging.info("Browser closed.")





import random
import time
import logging
import yaml
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
    InvalidSelectorException,
    NoSuchElementException,
)
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('linkedin_bot_debug.log'),
        logging.StreamHandler()
    ]
)

def load_accounts(file_path):
    """Load accounts from YAML file."""
    try:
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)
        return data.get("accounts", [])
    except Exception as e:
        logging.error(f"Failed to load accounts: {str(e)}", exc_info=True)
        return []

def load_message(file_path):
    """Load connection message from YAML config."""
    try:
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)
        return data.get("message", "Hi, I'd like to connect with you!")
    except Exception as e:
        logging.error(f"Failed to load message: {str(e)}", exc_info=True)
        return "Hi, I'd like to connect with you!"

def load_profile_urls_from_csv(file_path):
    """Read LinkedIn profile URLs from CSV file."""
    urls = []
    try:
        with open(file_path, "r", encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if len(row) >= 8:
                    url = row[7].strip()
                    if url.startswith("https://www.linkedin.com/in/"):
                        urls.append(url)
        logging.info(f"Loaded {len(urls)} profile URLs from CSV.")
    except Exception as e:
        logging.error(f"Failed to read profile URLs from CSV: {str(e)}", exc_info=True)
    return urls

class LinkedInBot:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.driver = None
        self.wait = None

    def start_browser(self):
        """Start Chrome browser with options."""
        try:
            options = Options()
            options.add_argument("--start-maximized")
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
            options.add_argument("--disable-blink-features=AutomationControlled")
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
            self.wait = WebDriverWait(self.driver, 30)  # Increased wait time
            logging.info("Browser started successfully.")
        except Exception as e:
            logging.error(f"Failed to start browser: {str(e)}", exc_info=True)
            raise

    def login(self):
        """Log in to LinkedIn."""
        try:
            logging.info(f"Logging in as {self.username}...")
            self.driver.get("https://www.linkedin.com/login")
            self.wait.until(
                EC.presence_of_element_located((By.ID, "username"))
            ).send_keys(self.username)
            self.driver.find_element(By.ID, "password").send_keys(self.password)
            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            self.wait.until(EC.url_contains("feed"))
            logging.info(f"Successfully logged in: {self.username}")
            time.sleep(random.uniform(3, 7))
        except Exception as e:
            logging.error(f"Login failed: {str(e)}", exc_info=True)
            self.driver.save_screenshot('debug_login.png')
            raise

    def click_more_actions(self):
        try:
            self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "section.artdeco-card[data-member-id]")
                )
            )
            logging.info("Profile page fully loaded.")

            locators = [
                (By.CSS_SELECTOR, "div.HZVlqmhRoGLChHcOHQXZHBCczivbLdHU button[aria-label='More actions']"),
                (By.XPATH, "//button[@aria-label='More actions']"),
                (By.XPATH, "//button[contains(@aria-label, 'More actions')]"),
                (By.CSS_SELECTOR, "button#ember110-profile-overflow-action"),
                (By.XPATH, "//button[@id='ember110-profile-overflow-action']"),
                (By.CSS_SELECTOR, "button.artdeco-dropdown__trigger[aria-label='More actions']"),
                (By.XPATH, "//div[contains(@class, 'pv-top-card')]//button[@aria-label='More actions']"),
            ]

            for locator in locators:
                try:
                    more_button = self.wait.until(
                        EC.presence_of_element_located(locator)
                    )
                    logging.info(f"Found 'More actions' button using locator: {locator}")
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", more_button)
                    self.driver.execute_script("arguments[0].click();", more_button)
                    logging.info("Clicked 'More actions' button.")
                    time.sleep(random.uniform(2, 4))
                    return
                except Exception as e:
                    logging.warning(f"Locator {locator} failed: {str(e)}")
                    continue

            logging.error("No 'More actions' button found.")
            self.driver.save_screenshot('debug_no_more_actions_button.png')
            raise Exception("No 'More actions' button found.")
        except Exception as e:
            logging.error(f"Error clicking 'More actions' button: {str(e)}", exc_info=True)
            self.driver.save_screenshot('debug_more_actions_error.png')
            raise

    def click_connect(self):
        """Click the 'Connect' option from the dropdown."""
        try:
            logging.info("Waiting for 'Connect' option to be clickable...")
            connect_option = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//div[contains(@aria-label, 'Invite') and contains(@aria-label, 'to connect')]")
                )
            )
            logging.info("Found 'Connect' option.")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", connect_option)
            self.driver.execute_script("arguments[0].click();", connect_option)
            logging.info("Clicked 'Connect' option.")
            time.sleep(random.uniform(2, 4))
        except Exception as e:
            logging.error(f"Error clicking 'Connect' option: {str(e)}", exc_info=True)
            self.driver.save_screenshot('debug_connect_error.png')
            raise

    def is_profile_restricted(self):
        """Check if the profile is restricted."""
        try:
            restricted_check = self.driver.find_elements(
                By.XPATH,
                "//*[contains(text(), 'This profile is restricted')]"
            )
            if not restricted_check:
                restricted_check = self.driver.find_elements(
                    By.XPATH,
                    "//*[contains(text(), 'You can't connect with this person')]"
                )
            return len(restricted_check) > 0
        except InvalidSelectorException as e:
            logging.error(f"Invalid XPath: {str(e)}", exc_info=True)
            return False
        except Exception as e:
            logging.error(f"Error checking if profile is restricted: {str(e)}", exc_info=True)
            return False

    def send_connection_with_note(self, profile_url, note_text):
        """Send a connection request with a note."""
        try:
            self.driver.get(profile_url)
            logging.info(f"Navigated to profile: {profile_url}")
            time.sleep(random.uniform(5, 10))

            if self.is_profile_restricted():
                logging.error(f"Profile is restricted: {profile_url}")
                self.driver.save_screenshot('debug_restricted_profile.png')
                return

            # Try direct connect button first
            try:
                direct_connect_btn = self.wait.until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR,
                        "div.ph5.pb5 button.artdeco-button[aria-label^='Invite'][id^='ember']:has(> svg[data-test-icon='connect-small'])"
                    ))
                )
                logging.info("Found direct 'Connect' button. Clicking it...")
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", direct_connect_btn)
                self.driver.execute_script("arguments[0].click();", direct_connect_btn)
                time.sleep(random.uniform(2, 4))
            except TimeoutException:
                logging.info("Direct 'Connect' button not found. Using More actions flow...")
                self.click_more_actions()
                self.click_connect()

            # Wait for connection modal
            self.wait.until(EC.visibility_of_element_located(
                (By.XPATH, "//div[@role='dialog']")
            ))

            try:
                # Click 'Add a free note' if available
                try:
                    add_note_btn = self.wait.until(
                        EC.element_to_be_clickable(
                            (By.XPATH, "//button[contains(@aria-label, 'Add a free note')]")
                        )
                    )
                    add_note_btn.click()
                    logging.info("Clicked 'Add a free note'.")
                except TimeoutException:
                    logging.info("'Add a free note' not found, trying to type directly in message box.")

                # Always try to enter note text from config.yaml
                note_box = self.wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//textarea[@name='message']")
                    )
                )
                note_box.clear()
                note_box.send_keys(note_text)
                logging.info(f"Entered note text from config.yaml: {note_text}")

            except (NoSuchElementException, TimeoutException):
                logging.warning("Couldn't find any message box. Sending basic connection request.")

            send_btn = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(@aria-label, 'Send')]")
                )
            )
            send_btn.click()
            logging.info(f"Connection request sent to {profile_url}.")
            time.sleep(random.uniform(3, 6))

        except Exception as e:
            logging.error(f"Could not send request to {profile_url}: {str(e)}", exc_info=True)
            self.driver.save_screenshot('debug_connection_error.png')
            raise

    def run(self, profile_url, note_text):
        """Run the bot for a single profile."""
        try:
            self.start_browser()
            self.login()
            self.send_connection_with_note(profile_url, note_text)
        except Exception as e:
            logging.error(f"Bot run failed: {str(e)}", exc_info=True)
        finally:
            if self.driver:
                self.driver.quit()
                logging.info("Browser closed.")

if __name__ == "__main__":
    accounts = load_accounts("credentials/accounts.yaml")
    message_text = load_message("config.yaml")
    urls = load_profile_urls_from_csv("logs/extracted_contacts.csv")

    if accounts and urls:
        acc = accounts[0]  # Pick first account
        bot = LinkedInBot(acc['username'], acc['password'])

        try:
            bot.start_browser()
            bot.login()

            for url in urls:
                try:
                    bot.send_connection_with_note(url, message_text)
                except Exception as e:
                    logging.error(f"Failed for {url}: {str(e)}", exc_info=True)
                    continue  # Skip and go to the next profile

        finally:
            if bot.driver:
                bot.driver.quit()
                logging.info("Browser closed.")

