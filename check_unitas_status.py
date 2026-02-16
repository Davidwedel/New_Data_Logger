#!/usr/bin/env python3
"""
Check Unitas Production Form Status
Checks if a specific date's production form is Complete or Overdue
"""
import sys
import os
import argparse
from datetime import datetime

# Add server directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "server"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "server/unitas_manager"))

from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from server.config import load_config, get_flat_config
from unitas_login import login
import unitas_helper

def make_driver(headless: bool = False):
    """Create Firefox webdriver"""
    options = webdriver.FirefoxOptions()
    if headless:
        options.add_argument("--headless")
    return webdriver.Firefox(
        service=Service(GeckoDriverManager().install()),
        options=options
    )

def open_production_page(driver, farm_id: int, house_id: int, timeout: int):
    """Navigate to Unitas production page"""
    url = f"https://vitalfarms.poultrycloud.com/farm/production?farmId={farm_id}&houseId={house_id}"
    driver.get(url)
    # Wait until page loaded
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".px-4.py-5"))
    )
    print(f"Production page opened")

def check_date_status(driver, target_date_str: str, timeout: int = 10):
    """
    Check if a date's production form is Complete or Overdue

    Returns:
        str: "Complete", "Overdue", or "Unknown"
    """
    # Parse date and try different formats
    target_date = datetime.fromisoformat(target_date_str)

    # Unitas uses format like "Thu, 02 Oct 2025"
    date_formats = [
        target_date.strftime("%a, %d %b %Y"),    # "Thu, 02 Oct 2025"
        target_date.strftime("%a, %-d %b %Y"),   # "Thu, 2 Oct 2025" (no leading zero)
    ]

    print(f"Checking status for date: {target_date_str}")

    for date_fmt in date_formats:
        try:
            # Find the title div containing the date
            title_xpath = f"//div[@data-cy='title' and contains(., '{date_fmt}')]"
            title_elem = driver.find_element(By.XPATH, title_xpath)
            print(f"Found date with format: {date_fmt}")

            # The status is in the same list item, look for the Daily entry following the date
            # Navigate to the li containing the daily entry
            daily_li_xpath = f"//div[@data-cy='title' and contains(., '{date_fmt}')]/following-sibling::ul//li[@data-cy='list-item' and @aria-label='daily']"

            try:
                daily_elem = driver.find_element(By.XPATH, daily_li_xpath)
                print(f"Found Daily entry")

                # Now look for status within this daily element
                # Try to find Complete status
                try:
                    complete_elem = daily_elem.find_element(By.XPATH, ".//span[contains(@class, 'text-success-500')]")
                    status_text = complete_elem.text.strip()
                    print(f"Status found: {status_text}")
                    return "Complete"
                except NoSuchElementException:
                    pass

                # Try to find Overdue status
                try:
                    overdue_elem = daily_elem.find_element(By.XPATH, ".//span[contains(@class, 'text-danger-500')]")
                    status_text = overdue_elem.text.strip()
                    print(f"Status found: {status_text}")
                    return "Overdue"
                except NoSuchElementException:
                    pass

                # If we found the daily entry but no status, return Unknown
                print("Daily entry found but no status indicator detected")
                return "Unknown"

            except NoSuchElementException:
                print("Could not find Daily entry for this date")
                return "Unknown"

        except NoSuchElementException:
            # Try next format
            continue
        except Exception as e:
            print(f"Error checking format {date_fmt}: {e}")
            continue

    print(f"Could not find date {target_date_str} on the page")
    return "Not Found"

def main():
    parser = argparse.ArgumentParser(
        description="Check Unitas production form status for a specific date"
    )
    parser.add_argument(
        "--date", "-d",
        required=True,
        help="Date to check in YYYY-MM-DD format (e.g., 2026-01-15)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode"
    )
    args = parser.parse_args()

    # Validate date format
    try:
        datetime.fromisoformat(args.date)
    except ValueError:
        print(f"ERROR: Invalid date format. Use YYYY-MM-DD (e.g., 2026-01-15)")
        sys.exit(2)

    # Load config
    config = get_flat_config()
    FARM_ID = config["Farm_ID"]
    HOUSE_ID = config["House_ID"]
    TIMEOUT = int(config["Timeout"])

    # Set timeout for unitas_helper module
    unitas_helper.set_timeout(TIMEOUT)

    # Create driver and login
    print(f"Starting browser...")
    driver = make_driver(headless=args.headless)

    try:
        print("Logging into Unitas...")
        login(driver, config)

        print("Opening production page...")
        open_production_page(driver, FARM_ID, HOUSE_ID, TIMEOUT)

        # Check status
        status = check_date_status(driver, args.date, TIMEOUT)

        print("\n" + "="*50)
        print(f"Date: {args.date}")
        print(f"Status: {status}")
        print("="*50)

        # Exit with appropriate code
        if status == "Complete":
            sys.exit(0)
        elif status == "Overdue":
            sys.exit(1)
        else:
            sys.exit(2)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)
    finally:
        print("\nClosing browser...")
        driver.quit()

if __name__ == "__main__":
    main()
