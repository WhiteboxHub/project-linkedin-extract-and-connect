



from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
import os, sys, shutil, tempfile, platform, psutil

def kill_chrome_processes():
    """Kill all Chrome/Chromium processes to avoid profile conflicts."""
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if "chrome" in proc.info['name'].lower() or "chromedriver" in proc.info['name'].lower():
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

def setup_browser():
    # Kill all Chrome processes first
    kill_chrome_processes()

    chrome_options = webdriver.ChromeOptions()

    # Detect OS and set Chrome binary and profile paths
    if platform.system() == "Darwin":  # macOS
        chrome_options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        profile_path = os.path.expanduser("~/Library/Application Support/Google/Chrome/Profile 29")  # Update profile name
    elif platform.system() == "Windows":  # Windows
        chrome_options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        profile_path = os.path.join(os.environ["LOCALAPPDATA"], r"Google\Chrome\User Data\Profile 1")  # Update profile name
    else:
        raise OSError("Unsupported operating system")

    # Create a temporary copy of the profile
    temp_profile_dir = tempfile.mkdtemp()
    profile_name = os.path.basename(profile_path)
    shutil.copytree(profile_path, os.path.join(temp_profile_dir, profile_name))

    # Use the temporary profile
    chrome_options.add_argument(f"--user-data-dir={temp_profile_dir}")
    chrome_options.add_argument(f"--profile-directory={profile_name}")

    # Optional: Add these for stability
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-extensions")

    driver_path = ChromeDriverManager().install()
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 20)
    return driver, wait

