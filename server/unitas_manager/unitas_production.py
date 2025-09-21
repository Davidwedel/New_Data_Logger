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
import runstate as runstate

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

def trigger_fill_production_form(driver, target_date=None):
    """
    Fetches data from Daily_User_Log and Daily_Bot_Log for the given date (default: yesterday),
    merges them, and calls fill_production_form with named arguments.
    """
    if target_date is None:
        target_date = (date.today() - timedelta(days=1)).isoformat()
    user_data = get_daily_user_log(target_date) or {}
    bot_data = get_daily_bot_log(target_date) or {}

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
        total_eggs=merged.get('belt_eggs', ''),
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
        birds_restricted=merged.get('birds_restricted', ''),
        birds_restricted_reason=merged.get('birds_restricted_reason', ''),
        inside_high=bot_data.get('inside_high_temp', ''),
        inside_low=bot_data.get('inside_low_temp', ''),
        outside_high=bot_data.get('outside_high_temp', ''),
        outside_low=bot_data.get('outside_low_temp', ''),
        air_sensory=merged.get('air_sensory', ''),
        weather_conditions=merged.get('weather', ''),
        outside_drinkers_clean='',
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

def get_yesterdays_form(driver, timeout):
    wait = WebDriverWait(driver, timeout)

    target = wait.until(EC.element_to_be_clickable((
        By.XPATH,
        "(//li[@data-cy='list-item' and @aria-label='daily'])[2]"
    )))
    target.click()
    print("Opening Yesterday's form.")

    # Wait for the next page/section to be ready
    WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((By.XPATH, "//h3[normalize-space()='House']"))
    )
    print("Yesterday's form opened.")
    # Just sit and wait for 3 seconds
    time.sleep(.5)

def fill_production_form(
    driver,
    mortality_indoor="0",
    mortality_outdoor="0",
    euthanized_indoor="0",
    euthanized_outdoor="0",
    depop_number="",
    cull_reason=None,
    mortality_reason=None,
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

def run_unitas_stuff(secrets):

    driver = make_driver(HEADLESS)
    try:
        login(driver, secrets)
        open_production_page(driver, FARM_ID, HOUSE_ID)
        get_yesterdays_form(driver, TIMEOUT)
        helper.trigger_fill_production_form(driver, values)

        #scroll back to top
        element = driver.find_element(By.ID, "V33-H1")
        driver.execute_script("arguments[0].scrollIntoView({ behavior: 'smooth', block: 'center' });", element)

        print("Worked!")
        runstate.save_data("SHEET_TO_PRODUCTION")
        time.sleep(1)

    finally:
        print("Quitting. Look over the data and Save.")
        print("Don't forget to close the browser window when you are done.")
        print("Goodbye!")

