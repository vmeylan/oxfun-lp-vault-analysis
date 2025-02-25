import logging
import shutil
import sys
import os
import subprocess
import re
from typing import Tuple

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import csv
import time
from datetime import datetime


def get_chrome_version() -> Tuple[str, str]:
    """
    Detects the installed Chrome or Chromium version.
    Returns a tuple containing the full version and the binary path.
    """
    logger = logging.getLogger(__name__)

    version = ""
    chrome_binary_path = ""
    # List of possible executable names
    executable_names = ["google-chrome", "google-chrome-stable", "chrome", "chromium-browser", "chromium"]
    # List of known installation paths, including snap
    known_paths = [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
        "/snap/bin/chromium",  # Added Chromium from snap
        "/opt/google/chrome/google-chrome",
        "/usr/local/bin/google-chrome",
        "/usr/local/bin/google-chrome-stable",
    ]

    # First, search in PATH
    for exe in executable_names:
        chrome_binary_path = shutil.which(exe)
        if chrome_binary_path:
            try:
                logger.info(f"Found Chrome executable: {chrome_binary_path}")
                process = subprocess.run([chrome_binary_path, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if process.returncode == 0:
                    version = process.stdout.strip()
                    logger.info(f"Detected Chrome version from {exe}: {version}")
                    break
            except Exception as e:
                logger.warning(f"Error while running {chrome_binary_path}: {e}")
                continue

    # If not found in PATH, check known installation paths
    if not version:
        for path in known_paths:
            if os.path.exists(path):
                try:
                    logger.info(f"Found Chrome executable at known path: {path}")
                    process = subprocess.run([path, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    if process.returncode == 0:
                        version = process.stdout.strip()
                        chrome_binary_path = path
                        logger.info(f"Detected Chrome version from known path {path}: {version}")
                        break
                except Exception as e:
                    logger.warning(f"Error while running {path}: {e}")
                    continue

    if not version:
        raise Exception("Google Chrome or Chromium is not installed or not found in PATH.")

    # Extract version number using regex
    match = re.search(r'(\d+)\.(\d+)\.(\d+)\.(\d+)', version)
    if not match:
        # If the version format is different, try to extract major version
        match = re.search(r'(\d+)\.', version)
        if not match:
            raise Exception("Unable to parse Chrome version.")
        major_version = match.group(1)
    else:
        major_version = match.group(1)

    full_version = match.group(0) if match else version
    return full_version, chrome_binary_path


def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,  # Set to INFO to eliminate debug logs
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stdout  # Ensure logs are sent to stdout (PyCharm console)
    )
    logger = logging.getLogger(__name__)

    driver = None  # Initialize driver variable
    max_pages = 100  # Set a maximum number of pages to prevent infinite loops
    current_page = 1
    previous_last_date = None  # To store the last date from the previous page

    try:
        # Step 1: Detect Chrome Version and Binary Path
        full_chrome_version, chrome_binary_path = get_chrome_version()
        logger.info(f"Detected Chrome version: {full_chrome_version}")
        chrome_major_version = full_chrome_version.split('.')[0]
        logger.info(f"Detected Chrome major version: {chrome_major_version}")

        # Step 2: Use the detected Chrome binary path
        logger.info(f"Using Chrome binary at: {chrome_binary_path}")

        # Step 3: Set up Chrome options
        chrome_options = Options()
        # Add the remote debugging port to fix "DevToolsActivePort file doesn't exist" error
        chrome_options.add_argument("--remote-debugging-port=9222")  # Added remote debugging port

        # Uncomment the next line if you want to run in headless mode
        # chrome_options.add_argument('--headless=new')  # Use '--headless=new' for newer Chromium versions

        # Add necessary Chrome options
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-infobars')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument("--user-data-dir=/tmp/chrome-profile")  # Unique profile dir
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_experimental_option('prefs', {'profile.managed_default_content_settings.images': 2})

        # Update user-agent to match the detected Chrome version
        chrome_options.add_argument(f'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) ' +
                                    f'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{full_chrome_version} Safari/537.36')

        # Specify the Chrome binary path
        chrome_options.binary_location = chrome_binary_path

        # Step 4: Initialize the Chrome driver using SeleniumManager
        logger.info("Initializing Chrome driver using SeleniumManager")
        driver = webdriver.Chrome(
            options=chrome_options
        )
        logger.info("Chrome driver initialized successfully")

        # Step 5: Bypass detection of automation
        logger.info("Bypassing detection of automation")
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.navigator.chrome = {
                    runtime: {},
                };
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
            '''
        })

        # Step 6: Navigate to the target page
        url = "https://ox.fun/en/vaults/profile/110428"
        logger.info(f"Navigating to {url}")
        driver.get(url)

        # Step 6a: Click the accept cookies button
        try:
            logger.info("Waiting for the accept cookies button to be clickable")
            accept_cookies_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'body > div:nth-child(11) > div > div > div > section > div > div > button.oxfun-btn.oxfun-btn-primary.css-1etm9c6'))
            )
            accept_cookies_button.click()
            logger.info("Clicked accept cookies button")
        except Exception as e:
            logger.warning(f"Accept cookies button not found or not clickable: {e}")

        # Step 7: Set up an explicit wait
        logger.info("Setting up explicit wait")
        wait = WebDriverWait(driver, 30)
        time.sleep(10)

        # Step 8: Wait for the table header to be present and extract headers
        logger.info("Waiting for the table header to be present")
        header_row = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#__next table thead tr')))
        headers = [th.text for th in header_row.find_elements(By.TAG_NAME, 'th')]
        logger.info(f"Extracted headers: {headers}")

        # Step 8a: Determine the index of the date column
        date_column_index = None
        for idx, header in enumerate(headers):
            if 'date' in header.lower():
                date_column_index = idx
                logger.info(f"Found date column: '{header}' at index {idx}")
                break

        if date_column_index is None:
            # If no date column found, assume the first column
            date_column_index = 0
            logger.warning("Date column not found in headers. Assuming the first column as date.")

        # Step 9: Initialize data list
        data = []

        # Get today's date in yyyy-mm-dd format
        today_str = datetime.today().strftime('%Y-%m-%d')
        logger.info(f"Today's date: {today_str}")

        # Define the root directory (repo root)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.abspath(os.path.join(script_dir, os.pardir))
        data_dir = os.path.join(repo_root, 'data', today_str)

        # Create the data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)
        logger.info(f"Data will be saved to: {data_dir}")

        while current_page <= max_pages:
            logger.info(f"Processing page {current_page}")

            # Step 10: Wait for the table body to be present
            logger.info("Waiting for the table body to be present")
            table_body = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#__next table tbody')))

            # Step 11: Get all rows
            rows = table_body.find_elements(By.TAG_NAME, 'tr')
            logger.info(f"Found {len(rows)} rows on page {current_page}")

            # Step 12: Extract data from each row
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, 'td')
                row_data = [cell.text for cell in cells]
                data.append(row_data)
                logger.info(f"Extracted row data: {row_data}")  # Log each row added

            # Step 13: Handle pagination
            try:
                logger.info("Checking for next page")
                next_button = driver.find_element(By.CSS_SELECTOR, '#__next ul div.oxfun-pagination-next')
                if 'oxfun-pagination-disabled' in next_button.get_attribute('class'):
                    logger.info("No more pages. Exiting loop.")
                    break
                else:
                    # Retrieve the date of the last row on the current page
                    if len(rows) > 0:
                        last_row = rows[-1]
                        cells = last_row.find_elements(By.TAG_NAME, 'td')
                        last_date = cells[date_column_index].text.strip()
                        if previous_last_date and last_date == previous_last_date:
                            logger.info("Last date is the same as the previous page. Exiting loop.")
                            break
                        previous_last_date = last_date
                        logger.info(f"Last date on current page: {last_date}")

                    logger.info("Clicking next page button")
                    next_button.click()
                    current_page += 1
                    time.sleep(2)  # Wait for the next page to load
            except Exception as e:
                logger.info(f"No more pages or error occurred: {e}")
                break

        # Step 14: Write data to CSV in the data_dir
        csv_file = os.path.join(data_dir, 'oxfun_data.csv')
        logger.info(f"Writing data to {csv_file}")
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(data)
        logger.info(f"Data successfully written to {csv_file}")

    except Exception as e:
        logger.exception("An error occurred")
    finally:
        # Step 15: Close the driver if it was initialized
        if driver:
            try:
                logger.info("Closing the driver")
                driver.quit()
            except Exception as e:
                logger.info("Driver was already closed or not initialized properly.")


if __name__ == "__main__":
    main()
