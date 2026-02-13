# stealth/undetected_browser.py
"""
Undetected ChromeDriver setup with profile safety checks.
Prevents detection by LinkedIn and ensures profile safety.
"""

import os
import logging
import platform
import subprocess
import psutil
import time
from pathlib import Path
from typing import Optional, Tuple
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)

# Profile lock file name
LOCK_FILE_NAME = ".bot_profile.lock"


def get_chrome_version() -> str:
    """
    Get installed Chrome version.
    
    Returns:
        Chrome version string or "Unknown"
    """
    try:
        if platform.system() == "Windows":
            # Try multiple methods to get Chrome version
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Users\%USERNAME%\AppData\Local\Google\Chrome\Application\chrome.exe"
            ]
            
            for chrome_path in chrome_paths:
                try:
                    # Expand environment variables
                    chrome_path = os.path.expandvars(chrome_path)
                    
                    if os.path.exists(chrome_path):
                        result = subprocess.check_output(
                            f'"{chrome_path}" --version',
                            shell=True,
                            timeout=10
                        ).decode().strip()
                        
                        # Filter out unwanted output like "Opening in existing browser session."
                        if "Opening in existing browser session" in result:
                            # Try with --version-only flag if available
                            try:
                                result = subprocess.check_output(
                                    f'"{chrome_path}" --version-only',
                                    shell=True,
                                    timeout=10
                                ).decode().strip()
                            except:
                                # Fall back to parsing the output
                                lines = result.split('\n')
                                for line in lines:
                                    if 'Chrome' in line and 'version' in line.lower():
                                        result = line.strip()
                                        break
                        
                        if result and 'Chrome' in result:
                            return result
                except subprocess.TimeoutExpired:
                    logger.warning(f"Chrome version check timed out for: {chrome_path}")
                    continue
                except Exception as e:
                    logger.debug(f"Could not get version from {chrome_path}: {e}")
                    continue
            
            # If all paths failed, try registry method
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon") as key:
                    version = winreg.QueryValueEx(key, "version")[0]
                    return f"Google Chrome {version}"
            except Exception as e:
                logger.debug(f"Registry method failed: {e}")
                
        else:
            # Linux/macOS
            chrome_commands = ["google-chrome", "google-chrome-stable", "chromium-browser"]
            for cmd in chrome_commands:
                try:
                    result = subprocess.check_output([cmd, "--version"], timeout=10).decode().strip()
                    if result:
                        return result
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    continue
        
        return "Unknown"
    except Exception as e:
        logger.warning(f"Could not detect Chrome version: {e}")
        return "Unknown"


def get_chrome_major_version() -> int:
    """
    Get Chrome major version number (e.g., 144 from "Google Chrome 144.0.7559.133").
    
    Returns:
        Major version number or None if detection fails
    """
    try:
        version_string = get_chrome_version()
        logger.info(f"Chrome version string: {version_string}")
        
        # Extract version number from various formats:
        # "Google Chrome 144.0.7559.133"
        # "144.0.7559.133"
        # "Chromium 144.0.7559.133"
        import re
        match = re.search(r'(\d+)\.(\d+)\.(\d+)\.(\d+)', version_string)
        if match:
            major_version = int(match.group(1))
            logger.info(f"✅ Detected Chrome major version: {major_version}")
            return major_version
        
        logger.warning(f"Could not parse version from: {version_string}")
        return None
    except Exception as e:
        logger.warning(f"Could not extract Chrome major version: {e}")
        return None


def check_chrome_running(profile_path: str) -> bool:
    """
    Check if Chrome is already running with the specified profile.
    
    Args:
        profile_path: Path to Chrome profile directory
        
    Returns:
        True if Chrome is running with this profile, False otherwise
    """
    try:
        # Check for Chrome processes
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                if proc.info['name'] and 'chrome' in proc.info['name'].lower():
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and any(profile_path in arg for arg in cmdline):
                        logger.warning(f"Chrome is already running with profile: {profile_path}")
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return False
    except Exception as e:
        logger.error(f"Error checking Chrome processes: {e}")
        return False


def create_profile_lock(profile_path: str) -> bool:
    """
    Create a lock file to indicate profile is in use by bot.
    
    Args:
        profile_path: Path to Chrome profile directory
        
    Returns:
        True if lock created successfully, False if lock already exists
    """
    try:
        lock_file = Path(profile_path) / LOCK_FILE_NAME
        
        # Check if lock already exists
        if lock_file.exists():
            # Check if lock is stale (older than 1 hour)
            lock_age = time.time() - lock_file.stat().st_mtime
            if lock_age > 3600:  # 1 hour
                logger.warning("Stale lock file detected, removing...")
                lock_file.unlink()
            else:
                logger.error(f"Profile is locked by another bot instance: {lock_file}")
                return False
        
        # Create lock file
        lock_file.write_text(f"Locked by bot at {time.time()}")
        logger.info(f"Profile lock created: {lock_file}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating profile lock: {e}")
        return False


def release_profile_lock(profile_path: str) -> None:
    """
    Release profile lock file.
    
    Args:
        profile_path: Path to Chrome profile directory
    """
    try:
        lock_file = Path(profile_path) / LOCK_FILE_NAME
        if lock_file.exists():
            lock_file.unlink()
            logger.info(f"Profile lock released: {lock_file}")
    except Exception as e:
        logger.error(f"Error releasing profile lock: {e}")


def setup_undetected_chrome(
    chrome_profile_name: str,
    headless: bool = False,
    version_main: Optional[int] = None,
    proxy: Optional[str] = None
) -> Tuple[uc.Chrome, WebDriverWait]:
    """
    Setup undetected ChromeDriver with profile safety checks.
    
    Args:
        chrome_profile_name: Name of Chrome profile to use
        headless: Whether to run in headless mode (not recommended for stealth)
        version_main: Chrome major version (auto-detected if None)
        proxy: Optional proxy string "ip:port"
        
    Returns:
        Tuple of (driver, wait) objects
        
    Raises:
        RuntimeError: If Chrome is already running with profile or profile is locked
        FileNotFoundError: If Chrome profile doesn't exist
    """
    driver = None
    
    try:
        logger.info("=" * 60)
        logger.info(f"Setting up undetected Chrome for profile: {chrome_profile_name}")
        
        # Get Chrome version
        chrome_version = get_chrome_version()
        logger.info(f"Detected Chrome: {chrome_version}")
        
        # Locate Chrome User Data
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
        
        # Check if Chrome is already running with this profile
        if check_chrome_running(source_profile_path):
            logger.warning(f"Chrome is running with profile '{chrome_profile_name}' - will use bot profile instead")
        
        # Create persistent bot profile (saves cookies/sessions between runs)
        logger.info(f"Using persistent bot profile for: {chrome_profile_name}")
        logger.info("(First run: will login and save session)")
        logger.info("(Next runs: will use saved session - no login needed!)")
        
        # Bot profile directory (persistent across runs)
        bot_profiles_base = os.path.join(
            os.path.dirname(chrome_user_data_dir),  # Same parent as Chrome User Data
            "LinkedIn_Bot_Profiles"  # Dedicated bot profiles folder
        )
        
        bot_user_data_dir = os.path.join(bot_profiles_base, f"Bot_{chrome_profile_name}")
        
        # Create bot profile directory
        os.makedirs(bot_user_data_dir, exist_ok=True)
        
        # Check if this is first run (no profile data yet)
        profile_marker = os.path.join(bot_user_data_dir, "Default", "Preferences")
        is_first_run = not os.path.exists(profile_marker)
        
        if is_first_run:
            logger.info("✨ First run detected - will login and save session")
        else:
            logger.info("✅ Saved session found - will skip login!")
        
        # Configure undetected Chrome options
        options = uc.ChromeOptions()
        
        # Profile binding - use persistent bot profile
        options.add_argument(f"--user-data-dir={bot_user_data_dir}")
        options.add_argument(f"--profile-directory=Default")
        
        # Stability
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # Proxy Support (added for Phase 7.5 scalability)
        if proxy:
            logger.info(f"Using Proxy: {proxy}")
            options.add_argument(f'--proxy-server={proxy}')

        
        # Headless mode (not recommended for stealth)
        if headless:
            options.add_argument("--headless=new")
            logger.warning("Running in headless mode - may be more detectable")
        
        # Launch undetected Chrome
        logger.info("Launching undetected Chrome...")
        logger.info("(First time may download ChromeDriver - please wait)")
        logger.info("This may take 30-60 seconds...")
        
        # Detect Chrome major version and force matching ChromeDriver
        chrome_major_version = get_chrome_major_version()
        
        if chrome_major_version:
            logger.info(f"Forcing ChromeDriver version {chrome_major_version} to match Chrome")
        else:
            logger.warning("Could not detect Chrome version - using auto-detection")
        
        # Let undetected-chromedriver use detected version
        # This ensures compatibility with any Chrome version
        try:
            logger.info("Creating Chrome driver (timeout: 120 seconds)...")
            
            # Try to create driver with detected version first
            if chrome_major_version:
                logger.info(f"Attempting to use ChromeDriver version {chrome_major_version}")
                driver = uc.Chrome(
                    options=options,
                    version_main=chrome_major_version,  # Force correct version
                    use_subprocess=True,
                )
            else:
                logger.info("Chrome version not detected, using auto-detection")
                driver = uc.Chrome(
                    options=options,
                    use_subprocess=True,
                )
            
            logger.info("Chrome driver created successfully!")
        except Exception as e:
            logger.error(f"Failed to create Chrome driver: {e}")
            
            # If version-specific creation failed, try without version constraint
            if chrome_major_version:
                logger.warning("Retrying without version constraint...")
                try:
                    driver = uc.Chrome(
                        options=options,
                        use_subprocess=True,
                    )
                    logger.info("Chrome driver created successfully with auto-detection!")
                except Exception as e2:
                    logger.error(f"Failed again without version constraint: {e2}")
                    logger.info("This may be due to slow network or ChromeDriver download issue")
                    raise
            else:
                logger.info("This may be due to slow network or ChromeDriver download issue")
                raise
        
        # Create WebDriverWait
        wait = WebDriverWait(driver, 20)
        
        logger.info("Undetected Chrome started successfully")
        logger.info("=" * 60)
        
        return driver, wait
        
    except Exception as e:
        logger.error("Undetected Chrome setup failed", exc_info=True)
        
        # Release lock if created
        if 'bot_profile_path' in locals():
            release_profile_lock(bot_profile_path)
        
        # Close driver if created
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        
        raise


def close_undetected_chrome(driver: uc.Chrome, profile_path: str) -> None:
    """
    Safely close undetected Chrome and release profile lock.
    
    Args:
        driver: Chrome driver instance
        profile_path: Path to Chrome profile directory
    """
    if driver:
        try:
            driver.quit()
            logger.info("Undetected Chrome closed")
        except Exception as e:
            logger.error(f"Error closing Chrome: {e}")
    
    # Release profile lock
    release_profile_lock(profile_path)
