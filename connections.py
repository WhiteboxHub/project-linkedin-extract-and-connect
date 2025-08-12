





# import random
# import time
# import logging
# import yaml
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from webdriver_manager.chrome import ChromeDriverManager

# # Configure logging for both file and console
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
#             # options.add_argument("--headless")  # Uncomment for headless mode
#             self.driver = webdriver.Chrome(
#                 service=Service(ChromeDriverManager().install()),
#                 options=options
#             )
#             self.wait = WebDriverWait(self.driver, 20)
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

#     def send_connection_with_note(self, profile_url, note_text):
#         """Send a connection request with a note."""
#         try:
#             self.driver.get(profile_url)
#             logging.debug(f"Navigated to: {profile_url}")
#             time.sleep(random.uniform(3, 6))

#             # Refined check for restricted profile
#             restricted_check = self.driver.find_elements(
#                 By.XPATH,
#                 "//*[contains(text(), 'This profile is restricted') or contains(text(), 'You can’t connect with this person')]"
#             )
#             if restricted_check:
#                 logging.error(f"Profile is restricted: {profile_url}")
#                 self.driver.save_screenshot('debug_restricted.png')
#                 return

#             # Click "More actions" button
#             more_actions_btn = self.wait.until(
#                 EC.element_to_be_clickable(
#                     (By.XPATH, "//button[contains(@aria-label, 'More actions')]")
#                 )
#             )
#             more_actions_btn.click()
#             logging.info("Clicked 'More actions' button.")
#             time.sleep(random.uniform(2, 4))

#             # Click "Connect"
#             connect_option = self.wait.until(
#                 EC.element_to_be_clickable(
#                     (By.XPATH, "//div[contains(@class, 'artdeco-dropdown__item')]//span[contains(text(), 'Connect')]")
#                 )
#             )
#             connect_option.click()
#             logging.info("Clicked 'Connect'.")
#             time.sleep(random.uniform(2, 4))

#             # Click "Add a note"
#             add_note_btn = self.wait.until(
#                 EC.element_to_be_clickable(
#                     (By.XPATH, "//button//span[contains(text(), 'Add a note')]")
#                 )
#             )
#             add_note_btn.click()
#             logging.info("Clicked 'Add a note'.")
#             time.sleep(random.uniform(2, 4))

#             # Enter the note
#             note_box = self.wait.until(
#                 EC.presence_of_element_located(
#                     (By.XPATH, "//textarea[contains(@name, 'message')]")
#                 )
#             )
#             note_box.clear()
#             note_box.send_keys(note_text)
#             logging.info("Entered note text.")
#             time.sleep(random.uniform(2, 4))

#             # Click Send
#             send_btn = self.wait.until(
#                 EC.element_to_be_clickable(
#                     (By.XPATH, "//button[contains(@class, 'mr1')]//span[contains(text(), 'Send')]")
#                 )
#             )
#             send_btn.click()
#             logging.info(f"Connection request with note sent to {profile_url}.")
#             time.sleep(random.uniform(3, 6))
#         except Exception as e:
#             logging.error(f"Could not send request to {profile_url}: {str(e)}", exc_info=True)
#             self.driver.save_screenshot('debug_connection.png')

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
#     for acc in accounts:
#         logging.info(f"\nProcessing Account: {acc['username']}")
#         bot = LinkedInBot(acc['username'], acc['password'])
#         bot.run(
#             "https://www.linkedin.com/in/guruteja8/",
#             "Hi, I'd like to connect with you!"
#         )
#         time.sleep(random.uniform(15, 25))











import random
import time
import logging
import yaml
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging for both file and console
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

def load_profile_urls(csv_path):
    """Load LinkedIn profile URLs from CSV."""
    try:
        df = pd.read_csv(csv_path)
        urls = []
        for col in df.columns:
            # Extract any cell starting with "https://www.linkedin.com/in/"
            urls.extend(df[col].dropna().astype(str).str.extract(r'(https://www\.linkedin\.com/in/[^"\s]+)')[0].dropna().tolist())
        return list(set(urls))  # Remove duplicates
    except Exception as e:
        logging.error(f"Failed to load profile URLs: {str(e)}", exc_info=True)
        return []

def load_message(message_file):
    """Load message from a text file."""
    try:
        with open(message_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        logging.error(f"Failed to load message: {str(e)}", exc_info=True)
        return ""

class LinkedInBot:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.driver = None
        self.wait = None

    def start_browser(self):
        """Start Chrome browser with options."""
        options = Options()
        options.add_argument("--start-maximized")
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        self.wait = WebDriverWait(self.driver, 20)
        logging.info("Browser started successfully.")

    def login(self):
        """Log in to LinkedIn."""
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

    def send_connection_with_note(self, profile_url, note_text):
        """Send a connection request with a note."""
        try:
            self.driver.get(profile_url)
            logging.debug(f"Navigated to: {profile_url}")
            time.sleep(random.uniform(3, 6))

            # Refined check for restricted profile
            restricted_check = self.driver.find_elements(
                By.XPATH,
                "//*[contains(text(), 'This profile is restricted') or contains(text(), 'You can’t connect with this person')]"
            )
            if restricted_check:
                logging.error(f"Profile is restricted: {profile_url}")
                return

            # Click "More actions" button
            more_actions_btn = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(@aria-label, 'More actions')]")
                )
            )
            more_actions_btn.click()
            time.sleep(random.uniform(2, 4))

            # Click "Connect"
            connect_option = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//div[contains(@class, 'artdeco-dropdown__item')]//span[contains(text(), 'Connect')]")
                )
            )
            connect_option.click()
            time.sleep(random.uniform(2, 4))

            # Click "Add a note"
            add_note_btn = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button//span[contains(text(), 'Add a note')]")
                )
            )
            add_note_btn.click()
            time.sleep(random.uniform(2, 4))

            # Enter the note
            note_box = self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//textarea[contains(@name, 'message')]")
                )
            )
            note_box.clear()
            note_box.send_keys(note_text)
            time.sleep(random.uniform(2, 4))

            # Click Send
            send_btn = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(@class, 'mr1')]//span[contains(text(), 'Send')]")
                )
            )
            send_btn.click()
            logging.info(f"✅ Connection request with note sent to {profile_url}")
            time.sleep(random.uniform(3, 6))
        except Exception as e:
            logging.error(f"❌ Could not send request to {profile_url}: {str(e)}", exc_info=True)

    def run(self, profile_urls, note_text):
        """Run the bot for multiple profiles."""
        self.start_browser()
        self.login()
        for profile_url in profile_urls:
            self.send_connection_with_note(profile_url, note_text)
        self.driver.quit()

if __name__ == "__main__":
    accounts = load_accounts("credentials/accounts.yaml")
    profile_urls = load_profile_urls("/logs/extracted_contacts.csv")
    message_text = load_message("/messages/message.txt")

    if not profile_urls:
        logging.error("No valid LinkedIn profile URLs found in CSV.")
    elif not message_text:
        logging.error("Message file is empty or not found.")
    else:
        for acc in accounts:
            logging.info(f"Processing Account: {acc['username']}")
            bot = LinkedInBot(acc['username'], acc['password'])
            bot.run(profile_urls, message_text)
            time.sleep(random.uniform(15, 25))
