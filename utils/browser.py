from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
import os
import logging
import shutil
import subprocess
import platform

logger = logging.getLogger(__name__)

# -------------------------------------------------
# Utility: Get Chrome Version (for logging only)
# -------------------------------------------------
def get_chrome_version():
    try:
        if platform.system() == "Windows":
            chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            result = subprocess.check_output(
                f'"{chrome_path}" --version',
                shell=True
            ).decode()
            return result.strip()
        else:
            result = subprocess.check_output(["google-chrome", "--version"]).decode()
            return result.strip()
    except Exception:
        return "Unknown"


# -------------------------------------------------
# Main Browser Setup
# -------------------------------------------------
def setup_browser(chrome_profile_name):
    """
    Setup Chrome browser using Selenium Manager
    - Auto-matches ChromeDriver to installed Chrome
    - Isolates each profile
    """
    driver = None

    try:
        logger.info("=" * 60)
        logger.info(f"Setting up browser for profile: {chrome_profile_name}")

        chrome_version = get_chrome_version()
        logger.info(f"Detected Chrome: {chrome_version}")

        # -------------------------------------------------
        # Locate Chrome User Data
        # -------------------------------------------------
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            raise EnvironmentError("LOCALAPPDATA not found")

        chrome_user_data_dir = os.path.join(
            local_app_data, "Google", "Chrome", "User Data"
        )

        source_profile_path = os.path.join(chrome_user_data_dir, chrome_profile_name)

        if not os.path.exists(source_profile_path):
            raise FileNotFoundError(
                f"Chrome profile not found: {source_profile_path}\n"
                f"Check chrome://version → Profile Path"
            )

        # -------------------------------------------------
        # Bot profile isolation directory
        # -------------------------------------------------
        temp_base = os.path.join(
            os.environ.get("TEMP", "/tmp"),
            "linkedin_bot_profiles"
        )

        bot_user_data_dir = os.path.join(temp_base, chrome_profile_name)
        bot_profile_path = os.path.join(bot_user_data_dir, chrome_profile_name)

        os.makedirs(bot_user_data_dir, exist_ok=True)

        # -------------------------------------------------
        # Copy profile on first run
        # -------------------------------------------------
        if not os.path.exists(bot_profile_path):
            logger.info("First run → copying Chrome profile")

            shutil.copytree(
                source_profile_path,
                bot_profile_path,
                ignore=shutil.ignore_patterns(
                    "LockFile",
                    "SingletonLock",
                    "*.tmp",
                    "Cache*",
                    "Code Cache",
                    "blob_storage",
                    "GPUCache",
                    "ShaderCache",
                    "Service Worker",
                ),
            )

            logger.info("Profile copied successfully")
        else:
            logger.info("Using existing bot profile (persistent session)")

        # -------------------------------------------------
        # Chrome Options
        # -------------------------------------------------
        options = webdriver.ChromeOptions()

        # Profile binding
        options.add_argument(f"--user-data-dir={bot_user_data_dir}")
        options.add_argument(f"--profile-directory={chrome_profile_name}")

        # Anti-detection
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option(
            "excludeSwitches", ["enable-automation", "enable-logging"]
        )
        options.add_experimental_option("useAutomationExtension", False)

        # Stability
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        # -------------------------------------------------
        # Launch Browser (AUTO MATCHED DRIVER)
        # -------------------------------------------------
        logger.info("Launching Chrome via Selenium Manager (auto driver match)")
        driver = webdriver.Chrome(options=options)

        # -------------------------------------------------
        # Final tweaks
        # -------------------------------------------------
        wait = WebDriverWait(driver, 20)

        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        logger.info("Browser started successfully")
        logger.info("=" * 60)

        return driver, wait

    except Exception as e:
        logger.error("Browser setup failed", exc_info=True)
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        raise


# -------------------------------------------------
# Safe Browser Close
# -------------------------------------------------
def close_browser(driver):
    if driver:
        try:
            driver.quit()
            logger.info("Browser closed")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
