import os
import time
import unitas_helper as helper
from unitas_login import login

from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import date, timedelta
import database_helper as db

HEADLESS = None
FARM_ID = None
HOUSE_ID = None
TIMEOUT = None
PRODUCTION_URL_TMPL = None

def do_unitas_setup(secrets):
# ---------- config ----------

    global HEADLESS, FARM_ID, HOUSE_ID, TIMEOUT, PRODUCTION_URL_TMPL
    PRODUCTION_URL_TMPL = "https://vitalfarms.poultrycloud.com/farm/production?farmId={farm_id}&houseId={house_id}"

    HEADLESS = False  # set True for headless mode
# ----------------------------

    FARM_ID = secrets["Farm_ID"]
    HOUSE_ID = secrets["House_ID"]
    TIMEOUT = secrets["Timeout"]

    helper.set_timeout(TIMEOUT)

def trigger_fill_production_form(driver, db_file, target_date=None):
    """
    Fetches data from Daily_User_Log and Daily_Bot_Log for the given date (default: yesterday),
    merges them, and calls fill_production_form with named arguments.
    """
    if target_date is None:
        target_date = (date.today() - timedelta(days=1)).isoformat()
    user_data = db.get_daily_user_log(db_file, target_date) or {}
    bot_data = db.get_daily_bot_log(db_file, target_date) or {}

    # Merge, user_data takes precedence if overlap
    merged = {**bot_data, **user_data}

    def split_hh_mm(timestr):
        if not timestr or not isinstance(timestr, str) or ':' not in timestr:
            return '', ''
        parts = timestr.split(':')
        return parts[0].zfill(2), parts[1].zfill(2)

    lights_on_hh, lights_on_mm = split_hh_mm(bot_data.get('lights_on', ''))
    lights_off_hh, lights_off_mm = split_hh_mm(bot_data.get('lights_off', ''))
    door_open_hh, door_open_mm = split_hh_mm(merged.get('door_open', ''))
    door_close_hh, door_close_mm = split_hh_mm(merged.get('door_closed', ''))

    # Birds are restricted if door open/close times are empty or null
    door_open_val = merged.get('door_open', '')
    door_close_val = merged.get('door_closed', '')
    birds_restricted = 'Yes' if (not door_open_val or not door_close_val) else 'No'

    fill_production_form(
        driver,
        mortality_indoor=merged.get('mortality_indoor', '0'),
        mortality_outdoor=merged.get('mortality_outdoor', '0'),
        euthanized_indoor=merged.get('euthanized_indoor', '0'),
        euthanized_outdoor=merged.get('euthanized_outdoor', '0'),
        depop_number=merged.get('depop', ''),
        cull_reason=merged.get('cull_reasons', None),
        mortality_reason=merged.get('mortality_reasons', None),
        mortality_comments=merged.get('mortality_comments', ''),
        total_eggs=merged.get('total_eggs', ''),
        floor_eggs=merged.get('floor_eggs', ''),
        nutritionist='',
        ration_used=merged.get('ration', ''),
        feed_consumption=bot_data.get('feed_consumption', ''),
        ration_delivered=bot_data.get('ration_delivered', ''),
        amount_delivered=merged.get('amount_delivered', ''),
        lights_on_hh=lights_on_hh,
        lights_on_mm=lights_on_mm,
        lights_off_hh=lights_off_hh,
        lights_off_mm=lights_off_mm,
        added_supplements=merged.get('added_supplements', ''),
        water_consumption=bot_data.get('water_consumption', ''),
        body_weight=bot_data.get('body_weight', ''),
        case_weight='',
        yolk_color='',
        door_open_hh=door_open_hh,
        door_open_mm=door_open_mm,
        door_close_hh=door_close_hh,
        door_close_mm=door_close_mm,
        birds_restricted=birds_restricted,
        birds_restricted_reason=merged.get('birds_restricted_reason', ''),
        inside_high=bot_data.get('inside_high_temp', ''),
        inside_low=bot_data.get('inside_low_temp', ''),
        outside_high=bot_data.get('outside_high_temp', ''),
        outside_low=bot_data.get('outside_low_temp', ''),
        air_sensory=merged.get('air_sensory', ''),
        weather_conditions=merged.get('weather', ''),
        outside_drinkers_clean=merged.get('drinkers_clean', ''),
        birds_found_under_slats=merged.get('birds_under_slats', ''),
        safe_environment_indoors=merged.get('safe_indoors', ''),
        safe_environment_outdoors=merged.get('safe_outdoors', ''),
        equipment_functioning=merged.get('equipment_functioning', ''),
        predator_activity=merged.get('predator_activity', ''),
        comment=merged.get('comments', '')
    )

def make_driver(headless: bool = False):
    options = webdriver.FirefoxOptions()
    if headless:
        options.add_argument("--headless")
    return webdriver.Firefox(
        service=Service(GeckoDriverManager().install()),
        options=options
    )


def open_production_page(driver, farm_id: int, house_id: int):
    url = PRODUCTION_URL_TMPL.format(farm_id=farm_id, house_id=house_id)
    driver.get(url)
    ## wait until page loaded
    WebDriverWait(driver, TIMEOUT).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".px-4.py-5"))
    )

    print("Production page opened")

def get_form_by_date(driver, timeout, target_date_str):
    """
    Select a specific production form by date.
    target_date_str: ISO format date string (YYYY-MM-DD)

    This tries multiple strategies to find the correct form:
    1. Look for date in aria-label
    2. Look for date in visible text
    3. Fall back to position-based selection if date matching fails
    """
    from selenium.common.exceptions import TimeoutException

    # Parse target date for formatting
    from datetime import datetime
    target_date = datetime.fromisoformat(target_date_str)

    # Try different date formats that Unitas might use
    # Try both with and without leading zeros, and various separators
    date_formats = []

    # Unitas format: "Thu, 02 Oct 2025"
    date_formats.append(target_date.strftime("%a, %d %b %Y"))    # "Thu, 02 Oct 2025"

    # Try other common formats
    date_formats.append(target_date.strftime("%b %d, %Y"))    # "Oct 04, 2025"
    date_formats.append(target_date.strftime("%m/%d/%Y"))     # "10/04/2025"
    date_formats.append(target_date.strftime("%Y-%m-%d"))     # "2025-10-04"
    date_formats.append(target_date.strftime("%B %d, %Y"))    # "October 04, 2025"

    # Try formats without leading zeros (GNU systems)
    try:
        date_formats.append(target_date.strftime("%a, %-d %b %Y"))   # "Thu, 2 Oct 2025"
        date_formats.append(target_date.strftime("%b %-d, %Y"))   # "Oct 4, 2025"
        date_formats.append(target_date.strftime("%m/%-d/%Y"))     # "10/4/2025"
        date_formats.append(target_date.strftime("%B %-d, %Y"))    # "October 4, 2025"
    except:
        pass  # %-d not supported on this platform

    # Try other common variants
    date_formats.append(target_date.strftime("%d/%m/%Y"))     # "04/10/2025" (European)
    date_formats.append(target_date.strftime("%d %b %Y"))     # "04 Oct 2025"

    print(f"Looking for form with date: {target_date_str}")

    # Strategy 1: Try to find by date in the title div, then click the daily li
    for date_fmt in date_formats:
        try:
            # Look for the date in the title div, then find the daily list item after it
            xpath = f"//div[@data-cy='title' and contains(., '{date_fmt}')]/following-sibling::ul//li[@data-cy='list-item' and @aria-label='daily']"
            wait = WebDriverWait(driver, 3)  # Short timeout for each attempt
            target = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            target.click()
            print(f"Found and clicked form for date: {date_fmt}")

            # Wait for the form to open
            WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located((By.XPATH, "//h3[normalize-space()='House']"))
            )
            print(f"Form for {target_date_str} opened successfully.")
            time.sleep(.5)
            return
        except TimeoutException:
            continue
        except Exception as e:
            print(f"Error trying format {date_fmt}: {e}")
            continue

    # If we couldn't find it by any date format, raise an error
    print(f"ERROR: Could not find form for date {target_date_str}")
    raise Exception(f"Unable to locate form for date: {target_date_str}")

def get_yesterdays_form(driver, timeout):
    """Backwards compatibility wrapper - selects yesterday's form by position"""
    target_date = (date.today() - timedelta(days=1)).isoformat()
    get_form_by_date(driver, timeout, target_date)

def fill_production_form(
    driver,
    mortality_indoor="0",
    mortality_outdoor="0",
    euthanized_indoor="0",
    euthanized_outdoor="0",
    depop_number="",
    cull_reason="",
    mortality_reason="",
    mortality_comments="",
    total_eggs="",
    floor_eggs="",
    nutritionist="",
    ration_used="",
    feed_consumption="",
    ration_delivered="",
    amount_delivered="",
    lights_on_hh="",
    lights_on_mm="",
    lights_off_hh="",
    lights_off_mm="",
    added_supplements="",
    water_consumption="",
    body_weight="",
    case_weight="",
    yolk_color="",
    door_open_hh="",
    door_open_mm="",
    door_close_hh="",
    door_close_mm="",
    birds_restricted="",
    birds_restricted_reason="",
    inside_high="",
    inside_low="",
    outside_high="",
    outside_low="",
    air_sensory="",
    weather_conditions="",
    outside_drinkers_clean="",
    birds_found_under_slats="",
    safe_environment_indoors="",
    safe_environment_outdoors="",
    equipment_functioning="",
    predator_activity="",
    comment=""
):

    helper.fill_input_by_id(driver, "V33-H1", mortality_indoor or "0")
    helper.fill_input_by_id(driver, "V35-H1", mortality_outdoor or "0")
    helper.fill_input_by_id(driver, "V34-H1", euthanized_indoor or "0")
    helper.fill_input_by_id(driver, "V36-H1", euthanized_outdoor or "0")
    helper.fill_input_by_id(driver, "V101-H1", depop_number)
    helper.fill_multiselect_box(driver, "V60-H1", cull_reason)
    helper.fill_multiselect_box(driver, "V50-H1", mortality_reason)
    helper.fill_input_by_id(driver, "V81-H1", mortality_comments)
    helper.fill_input_by_id(driver, "V4-H1", total_eggs)
    helper.fill_input_by_id(driver, "V1-H1", floor_eggs)
    helper.fill_input_by_id(driver, "V32-H1", nutritionist)
    helper.fill_input_by_id(driver, "V31-H1", ration_used)
    helper.fill_input_by_id(driver, "V39-H1", feed_consumption)
    helper.fill_input_by_id(driver, "V70-H1", ration_delivered)
    helper.fill_input_by_id(driver, "V23-H1", amount_delivered)
    if lights_on_hh.strip() != "":
        formatted_hour = f"{int(lights_on_hh):02d}"
        helper.fill_input_by_datacy_and_id(driver, "input-hour", "V99-H1", formatted_hour)
    if lights_on_mm.strip() != "":
        formatted_minute = f"{int(lights_on_mm):02d}"
        helper.fill_input_by_datacy_and_id(driver, "input-minute", "V99-H1", formatted_minute)
    if lights_off_hh.strip() != "":
        formatted_hour = f"{int(lights_off_hh):02d}"
        helper.fill_input_by_datacy_and_id(driver, "input-hour", "V100-H1", formatted_hour)
    if lights_off_mm.strip() != "":
        formatted_minute = f"{int(lights_off_mm):02d}"
        helper.fill_input_by_datacy_and_id(driver, "input-minute", "V100-H1", formatted_minute)
    helper.fill_input_by_id(driver, "V25-H1", added_supplements)
    helper.fill_input_by_id(driver, "V27-H1", water_consumption)
    helper.fill_input_by_id(driver, "V37-H1", body_weight)
    helper.fill_input_by_id(driver, "V11-H1", case_weight)
    helper.fill_input_by_id(driver, "V98-H1", yolk_color)
    if door_open_hh.strip() != "":
        formatted_hour = f"{int(door_open_hh):02d}"
        helper.fill_input_by_datacy_and_id(driver, "input-hour", "V78-H1", formatted_hour)
    if door_open_mm.strip() != "":
        formatted_minute = f"{int(door_open_mm):02d}"
        helper.fill_input_by_datacy_and_id(driver, "input-minute", "V78-H1", formatted_minute)
    if door_close_hh.strip() != "":
        formatted_hour = f"{int(door_close_hh):02d}"
        helper.fill_input_by_datacy_and_id(driver, "input-hour", "V79-H1", formatted_hour)
    if door_close_mm.strip() != "":
        formatted_minute = f"{int(door_close_mm):02d}"
        helper.fill_input_by_datacy_and_id(driver, "input-minute", "V79-H1", formatted_minute)
    helper.fill_input_by_id(driver, "V92-H1", birds_restricted)
    helper.fill_input_by_id(driver, "V97-H1", birds_restricted_reason)
    helper.fill_input_by_id(driver, "V28-H1", inside_high)
    helper.fill_input_by_id(driver, "V29-H1", inside_low)
    helper.fill_input_by_id(driver, "V72-H1", outside_high)
    helper.fill_input_by_id(driver, "V71-H1", outside_low)
    helper.fill_input_by_id(driver, "V89-H1", air_sensory)
    helper.fill_input_by_id(driver, "V90-H1", weather_conditions)
    helper.fill_input_by_id(driver, "V95-H1", outside_drinkers_clean)
    helper.fill_input_by_id(driver, "V77-H1", birds_found_under_slats)
    helper.fill_input_by_id(driver, "V93-H1", safe_environment_indoors)
    helper.fill_input_by_id(driver, "V94-H1", safe_environment_outdoors)
    helper.fill_input_by_id(driver, "V91-H1", equipment_functioning)
    helper.fill_input_by_id(driver, "V88-H1", predator_activity)
    helper.fill_input_by_id(driver, "Comment-H1", comment)

def run_unitas_stuff(secrets, db_file, target_date=None, headless=None):
    """
    Upload data to Unitas for dates that are flagged.

    If target_date is provided, uploads only that date.
    If target_date is None, finds and uploads ALL dates that:
      - Have send_to_bot flag set
      - Have not been sent yet (sent_to_unitas_at is NULL)
      - Have bot_log data available

    Args:
        secrets: Configuration dict
        db_file: Path to database
        target_date: Specific date to upload (None = upload all pending)
        headless: Force headless mode (None = use global HEADLESS setting)
    """
    from datetime import datetime

    # Determine which dates to upload BEFORE logging in
    if target_date is not None:
        # Single date mode (backwards compatibility)
        dates_to_upload = [target_date]
        print(f"Single date mode: uploading {target_date}")
    else:
        # Multi-date mode: find all pending dates
        dates_to_upload = db.get_dates_pending_unitas_upload(db_file)
        if not dates_to_upload:
            print("="*60)
            print("No dates pending upload. All caught up!")
            print("All data has been sent to Unitas.")
            print("="*60)
            return
        print(f"Found {len(dates_to_upload)} date(s) pending upload: {dates_to_upload}")

    # Now that we know we have work to do, start the browser and login
    # Use provided headless parameter or fall back to global HEADLESS setting
    use_headless = headless if headless is not None else HEADLESS
    driver = make_driver(use_headless)

    try:
        login(driver, secrets)
        open_production_page(driver, FARM_ID, HOUSE_ID)

        # Upload each date
        successful_uploads = []
        failed_uploads = []

        for upload_date in dates_to_upload:
            print(f"\n{'='*60}")
            print(f"Processing date: {upload_date}")
            print(f"{'='*60}")

            try:
                # Select the form for this date
                get_form_by_date(driver, TIMEOUT, upload_date)

                # Fill the form
                trigger_fill_production_form(driver, db_file, upload_date)

                # Scroll back to top
                element = driver.find_element(By.ID, "V33-H1")
                driver.execute_script("arguments[0].scrollIntoView({ behavior: 'smooth', block: 'center' });", element)

                print(f"Form filled for {upload_date}!")

                # Mark as sent to Unitas with timestamp
                user_log = db.get_daily_user_log(db_file, upload_date)
                if user_log:
                    db.update_daily_user_log(db_file, upload_date, {
                        'sent_to_unitas_at': datetime.now().isoformat()
                    })
                    print(f"✓ Marked {upload_date} as sent to Unitas")

                successful_uploads.append(upload_date)

                # Small delay between forms
                if len(dates_to_upload) > 1:
                    print("Waiting 2 seconds before next form...")
                    time.sleep(2)

            except Exception as e:
                print(f"✗ ERROR processing {upload_date}: {e}")
                print(f"Skipping {upload_date} and continuing with next date...")
                failed_uploads.append(upload_date)
                # Go back to production page to reset for next date
                try:
                    open_production_page(driver, FARM_ID, HOUSE_ID)
                except:
                    print("Warning: Could not return to production page")

        print(f"\n{'='*60}")
        print(f"UPLOAD SUMMARY")
        print(f"{'='*60}")
        print(f"Total dates attempted: {len(dates_to_upload)}")
        print(f"Successful: {len(successful_uploads)}")
        if successful_uploads:
            print(f"  ✓ {', '.join(successful_uploads)}")
        print(f"Failed: {len(failed_uploads)}")
        if failed_uploads:
            print(f"  ✗ {', '.join(failed_uploads)}")
        print(f"{'='*60}")
        time.sleep(1)

    finally:
        print("\nQuitting. Look over the data and Save.")
        print("Don't forget to close the browser window when you are done.")
        print("Goodbye!")

