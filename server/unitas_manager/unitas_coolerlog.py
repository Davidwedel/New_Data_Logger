from unitas_login import login
from sheets_processing import read_from_sheet
from webdriver_manager.firefox import GeckoDriverManager
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from datetime import date, timedelta
import unitas_helper as helper
import time
import runstate as runstate

FARM_ID = None
HOUSE_ID = None
COOLERLOG_URL = None
TIMEOUT = None
RANGE_NAME = None
INITIALS = None

def do_coolerlog_setup(secrets, range_name):
    global FARM_ID, HOUSE_ID, COOLERLOG_URL, TIMEOUT, RANGE_NAME, INITIALS
    
    RANGE_NAME = range_name
    FARM_ID = secrets["Farm_ID"]
    HOUSE_ID = secrets["House_ID"]
    TIMEOUT = secrets["Timeout"]
    INITIALS = secrets["Cooler_Log_Initials"]
    COOLERLOG_URL = f"https://vitalfarms.poultrycloud.com/farm/cooler-log/coolerlog/new?farmId={FARM_ID}&houseId={HOUSE_ID}"

def make_driver(headless: bool = False):
    options = webdriver.FirefoxOptions()
    if headless:
        options.add_argument("--headless")
    return webdriver.Firefox(
        service=Service(GeckoDriverManager().install()),
        options=options
    )
def open_coolerlog_page(driver):
    driver.get(COOLERLOG_URL)

def fill_coolerlog_values(driver, data):

    def pick_date(driver, date_input, target_date: date):
        # 1. Open the date picker
        date_input.click()
        time.sleep(0.5)  # let popup render

        # 2. Navigate to correct month/year
        while True:
            header = driver.find_element(By.CSS_SELECTOR, ".flex.justify-between.items-center.mb-2 div span")
            month_year = header.text.strip()  # e.g. "August"
            year_text = driver.find_element(By.CSS_SELECTOR, ".flex.justify-between.items-center.mb-2 div span.ml-1").text.strip()

            # convert to int month/year
            import calendar
            current_month = list(calendar.month_name).index(month_year)
            current_year = int(year_text)

            if current_month == target_date.month and current_year == target_date.year:
                break  # desired month is shown

            if (current_year, current_month) > (target_date.year, target_date.month):
                # too far ahead → click previous
                prev_btn = driver.find_element(By.CSS_SELECTOR, "button[aria-label='previous month']")
                prev_btn.click()
            else:
                # behind → click next
                next_btn = driver.find_element(By.CSS_SELECTOR, "button[aria-label='next month']")
                next_btn.click()
            time.sleep(0.3)

        # 3. Click the day cell
        selector = f"[data-cy='date-{target_date.day}']"
        day_elem = driver.find_element(By.CSS_SELECTOR, selector)
        day_elem.click()



    

    # wait until the input is present and clickable
    date_input = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "select-date-input"))
    )

    yesterday = date.today() - timedelta(days=1)
    pick_date(driver, date_input, yesterday)

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


def run_coolerlog_to_unitas():
    driver = make_driver(False)
    try:
        login(driver)
        open_coolerlog_page(driver)
        valuesToSend = read_from_sheet(RANGE_NAME)
        print(valuesToSend)
        fill_coolerlog_values(driver, valuesToSend)
        runstate.save_data("SHEET_TO_COOLER")
        
    finally:
        print("Quitting.")
        print("Goodbye!")
        driver.quit()
    
