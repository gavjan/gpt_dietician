from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from datetime import datetime, timedelta, date
from gpt_api import pick_meal
from tg_api import tg_notify

import time
import os
import json

HOME_URL = "https://app.ntfy.pl/"
CLIENT_FULL_NAME = "Gevorg Chobanyan"
DAYS_FROM_TODAY = 4
JS_TIMEOUT = 15
PAGE_TIMEOUT = 15
ESC_KEY_DELAY = 0.3
HEADLESS = True
DEBUG_PORT = 9222
JSON_DIR = "/home/cgev/public_html/logs/diet"
def load_json_today(folder):
    today = date.today().isoformat()
    filepath = f"{folder}/{today}.json"
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

DAILY_GOALS = {
    "protein": 180,
    "creatine": 5,
    "omega3": 2
}

def parse_report(report):
    if not report:
        return None
    text = f'''
Supplements:
    💪 Protein: {report["protein"]}g
    🥩 Creatine: {report["creatine"]}g
    🐟 Omega3: {report["omega3"]}g

Comments: \n{report["meal_comments"]}
    '''
    return text

user_data_dir = os.path.abspath("user_data")

options = Options()
options.add_argument("--start-maximized")
options.add_argument(f"--user-data-dir={user_data_dir}")
if HEADLESS:
    print(f'''Warning, running in headless mode. Either set HEADLESS=False or follow these instructions:
          1. Connect port to the server ssh -L {DEBUG_PORT}:localhost:{DEBUG_PORT} cgev@gavjan.com 
          2. Go to chrome://inspect/#devices then click Configure, and add localhost:{DEBUG_PORT}
          3. Remote Target list should refresh and show your instance. Click insect and interact with it
    ''')
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--remote-debugging-port={DEBUG_PORT}")

def init_driver():
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def save_json(json_data, folder, days_from_today=0):
    if not os.path.exists(folder):
        os.makedirs(folder)
    target_date = (date.today() + timedelta(days=days_from_today)).isoformat()
    filepath = f"{folder}/{target_date}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=4, ensure_ascii=False)



def date_in_polish(days_from_today=0):
    polish_months = {
        1: "stycznia", 2: "lutego", 3: "marca", 4: "kwietnia",
        5: "maja", 6: "czerwca", 7: "lipca", 8: "sierpnia",
        9: "września", 10: "października", 11: "listopada", 12: "grudnia"
    }

    target_date = datetime.now() + timedelta(days=days_from_today)
    return f"{target_date.day} {polish_months[target_date.month]} {target_date.year}"


def forward_days(driver,days_from_today):
    abbr_elements = driver.find_elements(By.TAG_NAME, "abbr")

    for abbr in abbr_elements:
        aria_date = abbr.get_attribute("aria-label")
        date_pl = date_in_polish(days_from_today=days_from_today)
        if aria_date == date_pl:
            abbr.click()
            wait_on_home_page_load(driver)
            return
    assert "aria text changed, fixme pls"

def wait_on_home_page_load(driver):
    WebDriverWait(driver, PAGE_TIMEOUT).until(EC.presence_of_element_located((By.XPATH, f"//p[contains(text(), '{CLIENT_FULL_NAME}')]")))

def parse_meal_option(driver, meal_option_title):
    tabs = {
        "ingredients": {"button": "simple-tab-1", "panel": "simple-tabpanel-1"},
        "allergens": {"button": "simple-tab-2", "panel": "simple-tabpanel-2"},
        "nutritional_value": {"button": "simple-tab-3", "panel": "simple-tabpanel-3"},
    }
    meal_info = {"title": meal_option_title}
    for tab_name, ids in tabs.items():
        # Click the tab button
        button = WebDriverWait(driver, JS_TIMEOUT).until(
            EC.element_to_be_clickable((By.ID, ids["button"]))
        )
        button.click()

        # Wait for the corresponding panel to appear
        panel = WebDriverWait(driver, JS_TIMEOUT).until(
            EC.presence_of_element_located((By.ID, ids["panel"]))
        )
        text = "<field missing>"
        if tab_name == "ingredients":
            text = panel.find_element(By.TAG_NAME, "p").text
            meal_info["ingredients"] = text.strip()
        elif tab_name == "allergens":
            text = panel.find_element(By.TAG_NAME, "p").text
        elif tab_name == "nutritional_value":
            text = ""
            p_tags = panel.find_elements(By.TAG_NAME, "p")
            for p_tag in p_tags:
                text += p_tag.text + ". "

        text = text.replace("Podane wartości odżywcze są orientacyjne.", "")
        text = text.replace('"', "")
        meal_info[tab_name] = text.strip()
    
    # Click X button
    time.sleep(ESC_KEY_DELAY)
    ActionChains(driver).send_keys(Keys.ESCAPE).perform()

    return meal_info

def get_meal_options_divs(driver):
    classes = ["MuiPaper-root", "MuiDialog-paper", "MuiDialog-paperScrollPaper", "MuiDialog-paperWidthSm", "MuiPaper-elevation24", "MuiPaper-rounded"]
    xpath = ".//div[" + " and ".join([f"contains(@class, '{cls}')" for cls in classes]) + "]"
    meal_options_div = WebDriverWait(driver, JS_TIMEOUT).until(
        EC.presence_of_element_located((By.XPATH, xpath))
    )
    meal_options_div = meal_options_div.find_element(By.XPATH, './/div/div/div/div')

    return meal_options_div.find_elements(By.XPATH, './div')


def get_meal_options(driver, meal_i):
    # Reassign meals_div again since it changes after opening/closing windows
    meals_div = WebDriverWait(driver, JS_TIMEOUT).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="root"]/div/main/div/div[3]/div[2]'))
    )
    meal_div = meals_div.find_elements(By.XPATH, './div')[meal_i]
    meal_type = meal_div.find_element(By.XPATH, './div[2]/div[1]/p').text

    # Click change meal button
    detail_btn = WebDriverWait(meal_div, JS_TIMEOUT).until(
        EC.element_to_be_clickable((By.XPATH, './/button[contains(@class, "MuiButton-outlined") and normalize-space()="Zmień"]'))
    )
    driver.execute_script("arguments[0].click();", detail_btn)

    # Get Change Meal Window Div
    meal_option_divs = get_meal_options_divs(driver)
    meal_options = []
    for i in range(len(meal_option_divs)):
        # Rerender meal_options_divs
        meal_option_div = get_meal_options_divs(driver)[i]
        meal_option_title = meal_option_div.find_element(By.CSS_SELECTOR, "p.MuiTypography-body2").text
        
        # Hover over div to make buttons appear
        actions = ActionChains(driver)
        actions.move_to_element(meal_option_div).perform()
        time.sleep(ESC_KEY_DELAY)
        meal_info_button = meal_option_div.find_element(By.XPATH, './/button[@type="button"]')
        meal_info_button.click()
        meal_option = parse_meal_option(driver, meal_option_title)
        meal_options.append(meal_option)
    
    return meal_options, meal_type


def select_picked_meal(driver, picked):
    meal_option_div = get_meal_options_divs(driver)[picked]
    meal_option_title = meal_option_div.find_element(By.CSS_SELECTOR, "p.MuiTypography-body2").text
    
    # Hover over div to make buttons appear
    actions = ActionChains(driver)
    actions.move_to_element(meal_option_div).perform() 
    meal_info_button = meal_option_div.find_element(By.XPATH, './/button[@type="button" and @tabindex="0"]')
    meal_info_button.click()

    # Wait for pick to process
    WebDriverWait(driver, JS_TIMEOUT).until(
        EC.presence_of_element_located((By.ID, "notistack-snackbar"))
    )


def get_meals_div(driver):
    return driver.find_element(By.XPATH, '//*[@id="root"]/div/main/div/div[3]/div[2]')

def main():
    protein = 0
    creatine = 0
    omega3 = 0
    meal_comments = ""
    meal_options_list = []

    # Load Todays Menu
    driver = init_driver()
    driver.get(HOME_URL)
    wait_on_home_page_load(driver)
    forward_days(driver, days_from_today=DAYS_FROM_TODAY)
    
    # Parse todays meal count
    meals_div = get_meals_div(driver)
    child_divs = meals_div.find_elements(By.XPATH, './div')
    meal_count = len(child_divs)
    
    # Skip the first one (title), iterate over meals only
    for i in range(1, meal_count):
        # Get parsed meal options
        meal_options, meal_type = get_meal_options(driver, i)

        # Get picked meal from api
        resp = pick_meal(meal_options)
        protein += resp["protein"]
        creatine += resp["creatine"]
        omega3 += resp["omega3"]
        picked = resp["picked_option"]
        meal_comments += f"{meal_type}: {resp['comments']}\n"
        meal_options_list.append({"type": meal_type, "options": meal_options})


        if picked != 0:
            # Something other than default (0) is seleced
            select_picked_meal(driver, picked)
        else:
            # Wait and click X
            time.sleep(ESC_KEY_DELAY)
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
    
    # Stop Chromium
    driver.quit()
    
    # Save choices and meal reports for upcoming day
    daily_report = {
        "protein": DAILY_GOALS["protein"] - protein,
        "creatine": DAILY_GOALS["creatine"] - creatine,
        "omega3": DAILY_GOALS["omega3"] - omega3,
        "meal_comments": meal_comments
    } 
    save_json(meal_options_list, f"{JSON_DIR}/meal_options", days_from_today=DAYS_FROM_TODAY)
    save_json(daily_report, f"{JSON_DIR}/daily_report", days_from_today=DAYS_FROM_TODAY)

    # Send report for today
    report = load_json_today(f"{JSON_DIR}/daily_report")
    text = parse_report(report)
    if text:
        tg_notify(text)
    else:
        print("No meal report for today to send.")


if __name__ == "__main__":
    exit(main())
