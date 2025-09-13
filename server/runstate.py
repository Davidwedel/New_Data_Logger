import json
import pathlib
from datetime import date

# key values from .runstate.json

#DB_TO_PRODUCTION
#DB_TO_COOLER
#XML_TO_DB

RUNSTATE_FILE = pathlib.Path(__file__).parent / ".runstate.json"

def make_sure_exists():
    if not RUNSTATE_FILE.exists():
        RUNSTATE_FILE.write_text("{}")  # create empty JSON object

def load_data(key):
    with open(RUNSTATE_FILE, "r") as f:
        data = json.load(f)

    today_str = date.today().isoformat()

    if data.get(key) == today_str:
        return True
    else:
        return False

def save_data(key):
    today_str = date.today().isoformat()
    with open(RUNSTATE_FILE, "r") as f:
        data = json.load(f)

    data[key] = today_str

    with open(RUNSTATE_FILE, "w") as f:
        json.dump(data, f, indent=4)

    print("Saved:", data)
