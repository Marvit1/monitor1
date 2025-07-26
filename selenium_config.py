# Selenium Configuration for Render.com
# This file contains Selenium setup optimized for Render.com environment

import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def get_selenium_driver():
    """
    Create Selenium WebDriver optimized for Render.com
    """
    try:
        # Chrome options for Render.com (headless, no GUI)
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # No GUI
        chrome_options.add_argument("--no-sandbox")  # Required for Render.com
        chrome_options.add_argument("--disable-dev-shm-usage")  # Required for Render.com
        chrome_options.add_argument("--disable-gpu")  # Disable GPU
        chrome_options.add_argument("--window-size=800,600")  # Smaller window size
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # Aggressive memory optimization
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--disable-css")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-javascript")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-features=TranslateUI")
        chrome_options.add_argument("--disable-ipc-flooding-protection")
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--max_old_space_size=256")  # Reduced from 4096
        chrome_options.add_argument("--single-process")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        
        # Additional aggressive optimizations
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--disable-sync")
        chrome_options.add_argument("--disable-translate")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-prompt-on-repost")
        chrome_options.add_argument("--disable-save-password-bubble")
        chrome_options.add_argument("--disable-single-click-autofill")
        chrome_options.add_argument("--disable-spellcheck-autocorrect")
        chrome_options.add_argument("--disable-web-resources")
        chrome_options.add_argument("--disable-client-side-phishing-detection")
        chrome_options.add_argument("--disable-component-extensions-with-background-pages")
        chrome_options.add_argument("--disable-domain-reliability")
        chrome_options.add_argument("--disable-features=AudioServiceOutOfProcess")
        chrome_options.add_argument("--disable-hang-monitor")
        chrome_options.add_argument("--disable-prompt-on-repost")
        chrome_options.add_argument("--disable-sync-preferences")
        chrome_options.add_argument("--disable-threaded-animation")
        chrome_options.add_argument("--disable-threaded-scrolling")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--aggressive-cache-discard")
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--max_old_space_size=128")  # Very aggressive
        chrome_options.add_argument("--js-flags=--max-old-space-size=128")
        
        # Set up Chrome service
        service = Service(ChromeDriverManager().install())
        
        # Create driver
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Set page load timeout
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(10)
        
        return driver
        
    except Exception as e:
        print(f"❌ Selenium setup failed: {e}")
        return None

def close_selenium_driver(driver):
    """
    Safely close Selenium WebDriver
    """
    try:
        if driver:
            driver.quit()
            print("✅ Selenium driver closed successfully")
    except Exception as e:
        print(f"⚠️ Error closing Selenium driver: {e}")

# Render.com specific settings
RENDER_SELENIUM_CONFIG = {
    "headless": True,
    "no_sandbox": True,
    "disable_dev_shm_usage": True,
    "disable_gpu": True,
    "timeout": 30,
    "implicit_wait": 10
} 