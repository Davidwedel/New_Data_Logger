import json
import os
from datetime import datetime, timedelta, date
from server.config import load_config

def check_all_settings_there(config):
    LOGIN_URL = "https://vitalfarms.poultrycloud.com/login"  # confirm this
    print('LOGIN_URL in setup:', LOGIN_URL)
    USERNAME = config["Unitas_Username"]
    PASSWORD = config["Unitas_Password"]
    TIMEOUT = config["Timeout"]

    if not USERNAME or not PASSWORD:
        raise SystemExit("Set Unitas_Username and Unitas_Password in config!")


def get_hatch_date():
    """Read hatch_date from config."""
    try:
        config = load_config()
        hatch_date = config["farm"].get("hatch_date")
        if not hatch_date:
            raise ValueError("hatch_date not found in config")
        return hatch_date
    except Exception as e:
        raise ValueError(f"Failed to load hatch_date from config: {e}")

def get_bird_age():

    target_date = (date.today() - timedelta(days=1)).isoformat()
    hatch_date_str = get_hatch_date()
    hatch_date = datetime.strptime(hatch_date_str, "%Y-%m-%d").date()
    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
    days_diff = (target_date - hatch_date).days
    week = days_diff // 7
    day = days_diff % 7
    return f"{week}.{day}"
