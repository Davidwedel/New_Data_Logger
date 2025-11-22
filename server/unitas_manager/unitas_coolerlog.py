from unitas_login import login
from webdriver_manager.firefox import GeckoDriverManager
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from datetime import date, timedelta, datetime
import unitas_helper as helper
import time
import database_helper as db

FARM_ID = None
HOUSE_ID = None
COOLERLOG_URL = None
TIMEOUT = None
INITIALS = None
DB_FILE = None
SECRETS = None

def do_coolerlog_setup(secrets, db_file=None):
    global FARM_ID, HOUSE_ID, COOLERLOG_URL, TIMEOUT, INITIALS, DB_FILE, SECRETS

    FARM_ID = secrets["Farm_ID"]
    HOUSE_ID = secrets["House_ID"]
    TIMEOUT = secrets["Timeout"]
    INITIALS = secrets["Cooler_Log_Initials"]
    COOLERLOG_URL = f"https://vitalfarms.poultrycloud.com/farm/coolerlog/coolerlog/new?farmId={FARM_ID}&houseId={HOUSE_ID}"
    SECRETS = secrets
    if db_file:
        DB_FILE = db_file

def make_driver(headless: bool = False):
    options = webdriver.FirefoxOptions()
    if headless:
        options.add_argument("--headless")
    # GeckoDriverManager caches driver automatically
    return webdriver.Firefox(
        service=Service(GeckoDriverManager().install()),
        options=options
    )
def open_coolerlog_page(driver):
    driver.get(COOLERLOG_URL)

def fill_coolerlog_values(driver, data):

    def pick_date(driver, date_picker_button, target_date: date):
        # 1. Open the date picker by clicking the button
        date_picker_button.click()
        time.sleep(0.5)  # let popup render

        # 2. Select month using dropdown
        month_dropdown = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "select.rdp-months_dropdown"))
        )
        from selenium.webdriver.support.ui import Select
        select_month = Select(month_dropdown)
        select_month.select_by_value(str(target_date.month - 1))  # Month is 0-indexed in dropdown
        time.sleep(0.3)

        # 3. Select year using dropdown
        year_dropdown = driver.find_element(By.CSS_SELECTOR, "select.rdp-years_dropdown")
        select_year = Select(year_dropdown)
        select_year.select_by_value(str(target_date.year))
        time.sleep(0.3)

        # 4. Click the day button - data-day format is "M/D/YYYY"
        day_selector = f"button[data-day='{target_date.month}/{target_date.day}/{target_date.year}']"
        day_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, day_selector))
        )
        day_button.click()
        time.sleep(0.3)



    

    # wait until the date picker button is present and clickable
    date_picker_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-haspopup, 'dialog') and .//span[contains(text(), 'Pick a date')]]"))
    )

    pick_date(driver, date_picker_button, data[1])

    #start filling in the rest

    #AM_Check_hh
    if data[0][0].strip() != "":
        formatted_hour = f"{int(data[0][0]):02d}"
        helper.fill_input_by_datacy_and_id(driver, "input-hour", "AMCheck-H1", formatted_hour)

    #AM_Check_mm
    if data[0][1].strip() != "":
        formatted_minute = f"{int(data[0][1]):02d}"  # "05"
        helper.fill_input_by_datacy_and_id(driver, "input-minute", "AMCheck-H1", formatted_minute)

    ## am temp
    helper.fill_input_by_id(driver, "AMTemp-H1", data[0][2])

    ## am temp initials
    helper.fill_input_by_id(driver, "AMInitial-H1", INITIALS)

    #PM_Check_hh = data[17]
    if data[0][3].strip() != "":
        formatted_hour = f"{int(data[0][3]):02d}"
        helper.fill_input_by_datacy_and_id(driver, "input-hour", "PMCheck-H1", formatted_hour)

    #PM_Check_mm = data[18]
    if data[0][4].strip() != "":
        formatted_minute = f"{int(data[0][4]):02d}"  # "05"
        helper.fill_input_by_datacy_and_id(driver, "input-minute", "PMCheck-H1", formatted_minute)
        
    ## pm temp
    helper.fill_input_by_id(driver, "PMTemp-H1", data[0][5])

    ## pm temp initials
    helper.fill_input_by_id(driver, "PMInitial-H1", INITIALS)

    ## eggs picked up
    helper.fill_input_by_id(driver, "EggsPick-H1", data[0][6])

    ## comments
    helper.fill_input_by_id(driver, "Comments-H1", data[0][7])



    # wait for the Save button to be clickable
    save_btn = driver.find_element(By.XPATH, ".//button[normalize-space()='Save']")

    time.sleep(4)
    save_btn.click()


def run_coolerlog_to_unitas(db_file=None, target_date=None):
    """
    Send cooler log data to Unitas from database

    Args:
        db_file: Path to database file (uses global DB_FILE if None)
        target_date: Specific date to upload (YYYY-MM-DD format), or None to upload all pending dates
    """
    if db_file is None:
        db_file = DB_FILE

    # Determine which dates to upload BEFORE logging in
    if target_date is not None:
        # Single date mode
        dates_to_upload = [target_date]
        print(f"Single date mode: uploading coolerlog for {target_date}")
    else:
        # Multi-date mode: find all pending dates
        dates_to_upload = db.get_dates_pending_coolerlog_upload(db_file)
        if not dates_to_upload:
            print("="*60)
            print("No dates pending coolerlog upload. All caught up!")
            print("="*60)
            return
        print(f"Found {len(dates_to_upload)} date(s) pending coolerlog upload: {dates_to_upload}")

    # Now that we know we have work to do, start the browser and login
    driver = make_driver(False)

    try:
        login(driver, SECRETS)

        # Upload each date
        successful_uploads = []
        failed_uploads = []

        for upload_date in dates_to_upload:
            print(f"\n{'='*60}")
            print(f"Processing coolerlog for date: {upload_date}")
            print(f"{'='*60}")

            try:
                # Get bot log data for this date
                bot_log = db.get_daily_bot_log(db_file, upload_date)
                if not bot_log:
                    print(f"No bot log data found for {upload_date}, skipping")
                    failed_uploads.append(upload_date)
                    continue

                # Get user log for eggs_picked_up and comments
                user_log = db.get_daily_user_log(db_file, upload_date)

                # Format data for coolerlog form
                cooler_time_am = bot_log.get('cooler_time_am', '')
                cooler_temp_am = bot_log.get('cooler_temp_am', '')
                cooler_time_pm = bot_log.get('cooler_time_pm', '')
                cooler_temp_pm = bot_log.get('cooler_temp_pm', '')

                # Parse time strings (format: "HH:MM:SS" or "HH:MM")
                am_hour, am_minute = '', ''
                if cooler_time_am:
                    parts = str(cooler_time_am).split(':')
                    am_hour = parts[0] if len(parts) > 0 else ''
                    am_minute = parts[1] if len(parts) > 1 else ''

                pm_hour, pm_minute = '', ''
                if cooler_time_pm:
                    parts = str(cooler_time_pm).split(':')
                    pm_hour = parts[0] if len(parts) > 0 else ''
                    pm_minute = parts[1] if len(parts) > 1 else ''

                eggs_picked_up = user_log.get('eggs_picked_up', '') if user_log else ''
                comments = user_log.get('coolerlog_comments', '') if user_log else ''

                # Round temperatures to integers for Unitas form
                temp_am_str = str(round(cooler_temp_am)) if cooler_temp_am else ''
                temp_pm_str = str(round(cooler_temp_pm)) if cooler_temp_pm else ''

                # Convert upload_date string to date object for date picker
                from datetime import datetime as dt
                date_obj = dt.strptime(upload_date, '%Y-%m-%d').date()

                # valuesToSend: [data_row, date_object]
                valuesToSend = [[am_hour, am_minute, temp_am_str, pm_hour, pm_minute, temp_pm_str, str(eggs_picked_up), comments], date_obj]

                # Open coolerlog page and fill form
                open_coolerlog_page(driver)
                print(f"Sending coolerlog data for {upload_date}:")
                print(valuesToSend[0])  # Print just the data row
                fill_coolerlog_values(driver, valuesToSend)

                # Update database with timestamp
                db.update_daily_bot_log(db_file, upload_date, {'cooler_logged_at': datetime.now().isoformat()})
                print(f"✓ Coolerlog successfully sent for {upload_date}")
                successful_uploads.append(upload_date)

            except Exception as e:
                print(f"✗ Error uploading coolerlog for {upload_date}: {e}")
                failed_uploads.append(upload_date)
                # Continue with next date even if one fails

        # Summary
        print("\n" + "="*60)
        print("COOLERLOG UPLOAD SUMMARY")
        print("="*60)
        print(f"Successful: {len(successful_uploads)}")
        if successful_uploads:
            print(f"  {', '.join(successful_uploads)}")
        print(f"Failed: {len(failed_uploads)}")
        if failed_uploads:
            print(f"  {', '.join(failed_uploads)}")
        print("="*60)

    finally:
        print("Quitting browser.")
        driver.quit()
    
