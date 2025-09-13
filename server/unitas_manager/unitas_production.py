import os
import time
import unitas_helper as helper

from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from unitas_login import login
import runstate as runstate

HEADLESS = None
FARM_ID = None
HOUSE_ID = None
TIMEOUT = None
RANGE_NAME = None
SPREADSHEET_ID = None
PRODUCTION_URL_TMPL = None

def do_unitas_setup(secrets):
# ---------- config ----------

    global HEADLESS, FARM_ID, HOUSE_ID, TIMEOUT, RANGE_NAME, SPREADSHEET_ID, PRODUCTION_URL_TMPL
    PRODUCTION_URL_TMPL = "https://vitalfarms.poultrycloud.com/farm/production?farmId={farm_id}&houseId={house_id}"

    HEADLESS = False  # set True for headless mode
# ----------------------------

    FARM_ID = secrets["Farm_ID"]
    HOUSE_ID = secrets["House_ID"]
    TIMEOUT = secrets["Timeout"]
    RANGE_NAME = secrets["sheet_to_unitas_range_name"]
    SPREADSHEET_ID = secrets["spreadsheet_id"]

    helper.set_timeout(TIMEOUT)


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

def fill_production_form(driver, data: dict):
    
    #mortality_indoor = data[0]
    if data[0][0] == "" : data[0][0] = "0"
    helper.fill_input_by_id(driver, "V33-H1", data[0][0])

    #mortality_outdoor = data[1]
    if data[0][1] == "": data[0][1] = "0"
    helper.fill_input_by_id(driver, "V35-H1", data[0][1])

    #euthanized_indoor = data[2]
    if data[0][2] == "": data[0][2] = "0"
    helper.fill_input_by_id(driver, "V34-H1", data[0][2])
    
    #euthanized_outdoor = data[3]
    if data[0][3] == "": data[0][3] = "0"
    helper.fill_input_by_id(driver, "V36-H1", data[0][3])

    #depop_number = data[4]
    helper.fill_input_by_id(driver, "V101-H1", data[0][4])

    #cull_reason = data[5]
    helper.fill_multiselect_box(driver, "V60-H1", data[0][5])
    
    #mortality_reason = data[6]
    helper.fill_multiselect_box(driver, "V50-H1", data[0][6])

    #mortality_comments = data[7]
    helper.fill_input_by_id(driver, "V81-H1", data[0][7])

    #total_eggs = data[8]
    helper.fill_input_by_id(driver, "V4-H1", data[0][8])

    #floor_eggs = data[9]
    helper.fill_input_by_id(driver, "V1-H1", data[0][9])

    #nutritionist = data[10]
    helper.fill_input_by_id(driver, "V32-H1", data[0][10])

    #ration_used = data[11]
    helper.fill_input_by_id(driver, "V31-H1", data[0][11])

    #feed_consumption = data[12]
    helper.fill_input_by_id(driver, "V39-H1", data[0][12])
    
    #ration_delivered = data[13]
    helper.fill_input_by_id(driver, "V70-H1", data[0][13])
    
    #amount_delivered = data[14]
    helper.fill_input_by_id(driver, "V23-H1", data[0][14])

    #lights_on_hh = data[15]
    if data[0][15].strip() != "":
        formatted_hour = f"{int(data[0][15]):02d}"
        helper.fill_input_by_datacy_and_id(driver, "input-hour", "V99-H1", formatted_hour)

    #lights_on_mm = data[16]
    if data[0][16].strip() != "":
        formatted_minute = f"{int(data[0][16]):02d}"  # "05"
        helper.fill_input_by_datacy_and_id(driver, "input-minute", "V99-H1", formatted_minute)

    #lights_off_hh = data[17]
    if data[0][17].strip() != "":
        formatted_hour = f"{int(data[0][17]):02d}"
        helper.fill_input_by_datacy_and_id(driver, "input-hour", "V100-H1", formatted_hour)

    #lights_off_mm = data[18]
    if data[0][18].strip() != "":
        formatted_minute = f"{int(data[0][18]):02d}"  # "05"
        helper.fill_input_by_datacy_and_id(driver, "input-minute", "V100-H1", formatted_minute)

    #added_supplements = data[19]
    helper.fill_input_by_id(driver, "V25-H1", data[0][19])

    #water_consumption = data[20]
    helper.fill_input_by_id(driver, "V27-H1", data[0][20])
        
    #body_weight = data[21]
    helper.fill_input_by_id(driver, "V37-H1", data[0][21])
        
    #case_weight = data[22]
    helper.fill_input_by_id(driver, "V11-H1", data[0][22])
        
    #yolk_color = data[23]
    helper.fill_input_by_id(driver, "V98-H1", data[0][23])
        
    #door_open_hh = data[24]
    if data[0][24].strip() != "":
        formatted_hour = f"{int(data[0][24]):02d}"
        helper.fill_input_by_datacy_and_id(driver, "input-hour", "V78-H1", formatted_hour)

    #door_open_mm = data[25]
    if data[0][25].strip() != "":
        formatted_minute = f"{int(data[0][25]):02d}"  # "05"
        helper.fill_input_by_datacy_and_id(driver, "input-minute", "V78-H1", formatted_minute)

    #door_close_hh = data[26]
    if data[0][26].strip() != "":
        formatted_hour = f"{int(data[0][26]):02d}"
        helper.fill_input_by_datacy_and_id(driver, "input-hour", "V79-H1", formatted_hour)

    #door_close_mm = data[27]
    if data[0][27].strip() != "":
        formatted_minute = f"{int(data[0][27]):02d}"  # "05"
        helper.fill_input_by_datacy_and_id(driver, "input-minute", "V79-H1", formatted_minute)

    #birds_restricted = data[28]
    helper.fill_input_by_id(driver, "V92-H1", data[0][28])
        
    #birds_restricted_reason = data[29]
    helper.fill_input_by_id(driver, "V97-H1", data[0][29])
        
    #inside_high = data[30]
    helper.fill_input_by_id(driver, "V28-H1", data[0][30])
        
    #inside_low = data[31]
    helper.fill_input_by_id(driver, "V29-H1", data[0][31])
        
    #outside_high = data[32]
    helper.fill_input_by_id(driver, "V72-H1", data[0][32])
        
    #outside_low = data[33]
    helper.fill_input_by_id(driver, "V71-H1", data[0][33])
        
    #air_sensory = data[34]
    helper.fill_input_by_id(driver, "V89-H1", data[0][34])
        
    #weather_conditions = data[35]
    helper.fill_input_by_id(driver, "V90-H1", data[0][35])
        
    #outside_drinkers_clean = data[36]
    helper.fill_input_by_id(driver, "V95-H1", data[0][36])
        
    #birds_found_under_slats = data[37]
    helper.fill_input_by_id(driver, "V77-H1", data[0][37])
        
    #safe_environment_indoors = data[38]
    helper.fill_input_by_id(driver, "V93-H1", data[0][38])
        
    #safe_environment_outdoors = data[39]
    helper.fill_input_by_id(driver, "V94-H1", data[0][39])
        
    #equipment_functioning = data[40]
    helper.fill_input_by_id(driver, "V91-H1", data[0][40])
        
    #predator_activity = data[41]
    helper.fill_input_by_id(driver, "V88-H1", data[0][41])
        
    #comment = data[42]
    helper.fill_input_by_id(driver, "Comment-H1", data[0][42])

def run_unitas_stuff(values):

    driver = make_driver(HEADLESS)
    try:
        login(driver)
        open_production_page(driver, FARM_ID, HOUSE_ID)
        get_yesterdays_form(driver, TIMEOUT)
        fill_production_form(driver, values)

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

