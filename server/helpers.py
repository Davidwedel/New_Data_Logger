import json
import os
from datetime import datetime, timedelta, date

def get_hatch_date(settings_path=None):
    """Read hatch_date from settings.json."""
    if settings_path is None:
        settings_path = os.path.join(os.path.dirname(__file__), "..", "settings.json")
    if not os.path.exists(settings_path):
        raise FileNotFoundError(f"Settings file not found: {settings_path}")
    with open(settings_path, "r") as f:
        settings = json.load(f)
    hatch_date = settings.get("hatch_date")
    if not hatch_date:
        raise ValueError("hatch_date not found in settings.json")
    return hatch_date

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
