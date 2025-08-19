# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.support.ui import WebDriverWait
# from webdriver_manager.chrome import ChromeDriverManager

# def setup_browser():
#     chrome_options = webdriver.ChromeOptions()
#     chrome_options.add_argument("--start-maximized")
#     chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
#     chrome_options.add_experimental_option('useAutomationExtension', False)
#     chrome_options.add_argument("--disable-blink-features=AutomationControlled")

#     driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
#     wait = WebDriverWait(driver, 15)
#     driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

#     return driver, wait


from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
import os, sys

def setup_browser():
    chrome_options = webdriver.ChromeOptions()
    driver_path = ChromeDriverManager().install()

    # Cross-platform fix
    if sys.platform.startswith("win"):
        if not driver_path.endswith(".exe"):
            driver_path = os.path.join(os.path.dirname(driver_path), "chromedriver.exe")
    else:
        if not driver_path.endswith("chromedriver"):
            driver_path = os.path.join(os.path.dirname(driver_path), "chromedriver")

    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # ✅ Return driver and proper WebDriverWait
    wait = WebDriverWait(driver, 20)
    return driver, wait
