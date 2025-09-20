from re import L
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from unitas_helper import click_when_clickable

LOGIN_URL = None
USERNAME = None
PASSWORD = None 
TIMEOUT = None

def setup_unitas_login(secrets):
    global LOGIN_URL, USERNAME, PASSWORD, TIMEOUT
    LOGIN_URL = "https://vitalfarms.poultrycloud.com/login"  # confirm this
    print('LOGIN_URL in setup:', LOGIN_URL)
    USERNAME = secrets["Unitas_Username"]
    PASSWORD = secrets["Unitas_Password"]
    TIMEOUT = secrets["Timeout"]

    if not USERNAME or not PASSWORD:
        raise SystemExit("Set Unitas_Username and Unitas_Password in secrets.json!")


def login(driver, LOGIN_URL):
    wait = WebDriverWait(driver, 10)
    print('LOGIN_URL in login:', LOGIN_URL)
    driver.get(LOGIN_URL)
    username_box = wait.until(EC.visibility_of_element_located((By.ID, "username")))
    password_box = wait.until(EC.visibility_of_element_located((By.ID, "password")))
    username_box.send_keys(USERNAME)
    password_box.send_keys(PASSWORD)
    login_btn = click_when_clickable(driver, By.CSS_SELECTOR, "button[type='submit']")
    login_btn.click()
    WebDriverWait(driver, TIMEOUT).until_not(EC.url_contains("/login"))
    print("Logged in")

