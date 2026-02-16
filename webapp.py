#!/usr/bin/env python3
"""
Farm Data Web Application
Provides web interface for viewing and editing farm data
"""
import os
import sys
import json
import pathlib
import requests
import subprocess
import threading
from flask import Flask, request, jsonify, render_template
import sqlite3
from datetime import date, datetime

# Add server directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "server"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "server/unitas_manager"))
import database_helper as db
from server.config import load_config, save_config, get_flat_config, get_database_path, get_deployment_mode, get_localhost_port, is_config_unconfigured, CONFIG_DIR
from server.helpers import get_bird_age
import server.unitas_manager.unitas_production as unitas

app = Flask(__name__)

# Global variables to store startup state
STARTUP_ERROR = None
CONFIG_NEEDS_SETUP = False
DB_FILE = None

# Initialize database on startup - path depends on deployment mode
try:
    DB_FILE = pathlib.Path(get_database_path())
    # Ensure directory exists
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    db.setup_db(DB_FILE)

    # Initialize Unitas module with config
    config = get_flat_config()
    unitas.do_unitas_setup(config)

    # Check if config needs to be configured
    CONFIG_NEEDS_SETUP = is_config_unconfigured()
    if CONFIG_NEEDS_SETUP:
        print("WARNING: Configuration is using default values. Please update settings via the web UI.")
except Exception as e:
    # Store the error to display in UI
    STARTUP_ERROR = str(e)
    print(f"STARTUP ERROR: {e}")
    # Continue to allow Flask to start, but routes will show error page

def fetch_nws_weather(station_id):
    """Fetch current weather from National Weather Service station"""
    try:
        # Get latest observation from station
        obs_url = f"https://api.weather.gov/stations/{station_id}/observations/latest"
        headers = {'User-Agent': 'FarmDataLogger/1.0'}

        print(f"DEBUG: Fetching weather from: {obs_url}")
        obs_response = requests.get(obs_url, headers=headers, timeout=10)
        print(f"DEBUG: Response status: {obs_response.status_code}")

        if obs_response.status_code != 200:
            print(f"DEBUG: Bad response code: {obs_response.status_code}")
            return None

        obs_data = obs_response.json()
        text_description = obs_data['properties'].get('textDescription')
        print(f"DEBUG: NWS text description: {text_description}")

        if not text_description:
            print("DEBUG: No text description in response")
            return None

        # Map NWS observation to our weather options
        text_lower = text_description.lower()

        weather_mapping = {
            'sunny': 'Sunny',
            'clear': 'Sunny',
            'fair': 'Sunny',
            'partly cloudy': 'Partly Cloudy',
            'partly sunny': 'Partly Sunny',
            'mostly cloudy': 'Mostly Cloudy',
            'cloudy': 'Cloudy',
            'overcast': 'Cloudy',
            'rain': 'Rain',
            'showers': 'Rain',
            'drizzle': 'Rain',
            'thunderstorm': 'Severe Storm',
            'storm': 'Severe Storm',
            'snow': 'Snow',
            'sleet': 'Sleet',
            'freezing': 'Freezing Rain',
            'wind': 'Cloudy/Windy',
        }

        # Find best match
        for key, value in weather_mapping.items():
            if key in text_lower:
                print(f"DEBUG: Matched '{key}' -> '{value}'")
                return value

        print(f"DEBUG: No match found for '{text_description}'")
        return None  # Return None if no match

    except Exception as e:
        print(f"DEBUG: Error fetching weather: {e}")
        import traceback
        traceback.print_exc()
        return None


# ─── Startup Error Handling ───

from functools import wraps

def check_startup_error(f):
    """Decorator to check for startup errors before executing routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if STARTUP_ERROR:
            return render_startup_error(), 503
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_config_status():
    """Inject configuration status into all templates"""
    return dict(config_needs_setup=CONFIG_NEEDS_SETUP)

def render_startup_error():
    """Render a helpful error page when config/database initialization fails"""
    error_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Configuration Error - Data Logger</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 900px;
            margin: 50px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .error-container {{
            background: white;
            border-left: 5px solid #dc3545;
            padding: 30px;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #dc3545;
            margin-top: 0;
        }}
        .error-message {{
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            padding: 15px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            white-space: pre-wrap;
            word-wrap: break-word;
            overflow-x: auto;
        }}
        .info {{
            margin-top: 20px;
            padding: 15px;
            background: #e7f3ff;
            border-left: 4px solid #0066cc;
            border-radius: 4px;
        }}
        code {{
            background: #f1f1f1;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <h1>⚠️ Configuration Error</h1>
        <p>The data logger web application could not start due to a configuration error.</p>

        <h3>Error Details:</h3>
        <div class="error-message">{STARTUP_ERROR}</div>

        <div class="info">
            <strong>ℹ️ Note:</strong> After fixing the configuration, restart the web server:<br>
            <code>sudo systemctl restart httpd</code> (for Apache)<br>
            or simply restart the Flask development server (for localhost mode)
        </div>
    </div>
</body>
</html>
"""
    return error_html


@app.route("/")   # homepage route
@check_startup_error
def index():
    today_str = date.today().isoformat()
    user_log = db.get_daily_user_log(DB_FILE, today_str)
    bot_log = db.get_daily_bot_log(DB_FILE, today_str)
    user_logs = db.get_all_user_logs(DB_FILE)
    bot_logs = db.get_all_bot_logs(DB_FILE)

    # Check last 7 days for missing Unitas uploads
    missing_uploads = db.check_last_n_days_unitas_status(DB_FILE, days=7)

    return render_template("index.html", user_log=user_log, bot_log=bot_log, user_logs=user_logs, bot_logs=bot_logs, missing_uploads=missing_uploads)

@app.route("/add_pallet", methods=["POST"])
@check_startup_error
def add_pallet():
    data = request.json
    thedate = date.today().isoformat()
    pallet_id = data.get("pallet_id")
    house_id = 1

    # Get pallet settings from config
    config = load_config()
    pallet_tare = config["farm"].get("pallet_tare", 192)
    cases_per_pallet = config["farm"].get("cases_per_pallet", 30)

    # Accept either total weight or case weight, calculate the other
    total_pallet_weight = data.get("weight")
    case_weight_input = data.get("case_weight")

    if total_pallet_weight is not None and total_pallet_weight != "":
        # Total weight provided, calculate case weight
        total_pallet_weight = float(total_pallet_weight)
        case_weight = (total_pallet_weight - pallet_tare) / cases_per_pallet
    elif case_weight_input is not None and case_weight_input != "":
        # Case weight provided, calculate total weight
        case_weight = float(case_weight_input)
        total_pallet_weight = (case_weight * cases_per_pallet) + pallet_tare
    else:
        # Default to 0 if neither provided
        total_pallet_weight = 0
        case_weight = 0

    # Calculate flock age from hatch date
    try:
        flock_age = float(get_bird_age())
    except Exception as e:
        print(f"Error calculating bird age: {e}")
        flock_age = 0.0

    yolk_color = data.get("yolk_color")

    db.insert_pallet_log(DB_FILE, thedate, pallet_id, house_id, total_pallet_weight, case_weight, flock_age, yolk_color)

    # Get DB timestamp for polling
    db_timestamp = DB_FILE.stat().st_mtime if DB_FILE and DB_FILE.exists() else 0

    return jsonify({"status": "ok", "message": "Pallet saved!", "db_timestamp": db_timestamp})

@app.route("/get_pallet_logs", methods=["GET"])
@check_startup_error
def get_pallet_logs():
    logs = db.get_recent_pallet_logs(DB_FILE, limit=10)
    return jsonify(logs)

@app.route("/delete_pallet/<int:pallet_id>", methods=["DELETE"])
@check_startup_error
def delete_pallet(pallet_id):
    """Delete a pallet log entry by its ID"""
    try:
        rows_deleted = db.delete_pallet_log(DB_FILE, pallet_id)
        if rows_deleted > 0:
            return jsonify({"status": "ok", "message": "Pallet deleted successfully"})
        else:
            return jsonify({"status": "error", "message": "Pallet not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/get_current_pallet", methods=["GET"])
@check_startup_error
def get_current_pallet():
    """Get the most recent pallet entry"""
    pallet = db.get_most_recent_pallet(DB_FILE)
    if pallet:
        return jsonify(pallet)
    else:
        # No pallets exist yet, return empty structure with current bird age
        try:
            flock_age = float(get_bird_age())
        except Exception as e:
            print(f"Error calculating bird age: {e}")
            flock_age = 0.0

        return jsonify({
            "id": None,
            "pallet_id": "",
            "total_pallet_weight": 0,
            "case_weight": 0,
            "yolk_color": "",
            "flock_age": flock_age,
            "completed": 0
        })

@app.route("/update_pallet/<int:pallet_id>", methods=["POST"])
@check_startup_error
def update_pallet(pallet_id):
    """Update a specific pallet entry (auto-save)"""
    data = request.json

    # Get pallet settings from config
    config = load_config()
    pallet_tare = config["farm"].get("pallet_tare", 192)
    cases_per_pallet = config["farm"].get("cases_per_pallet", 30)

    # Build update data dict
    update_data = {}

    # Handle pallet_id
    if "pallet_id" in data:
        update_data["pallet_id"] = data["pallet_id"]

    # Handle yolk_color
    if "yolk_color" in data:
        update_data["yolk_color"] = data["yolk_color"]

    # Accept either total weight or case weight, calculate the other
    total_pallet_weight = data.get("weight")
    case_weight_input = data.get("case_weight")

    if total_pallet_weight is not None and total_pallet_weight != "":
        # Total weight provided, calculate case weight
        total_pallet_weight = float(total_pallet_weight)
        case_weight = (total_pallet_weight - pallet_tare) / cases_per_pallet
        update_data["total_pallet_weight"] = total_pallet_weight
        update_data["case_weight"] = case_weight
    elif case_weight_input is not None and case_weight_input != "":
        # Case weight provided, calculate total weight
        case_weight = float(case_weight_input)
        total_pallet_weight = (case_weight * cases_per_pallet) + pallet_tare
        update_data["case_weight"] = case_weight
        update_data["total_pallet_weight"] = total_pallet_weight

    try:
        db.update_pallet_log(DB_FILE, pallet_id, update_data)

        # Get DB timestamp for polling
        db_timestamp = DB_FILE.stat().st_mtime if DB_FILE and DB_FILE.exists() else 0

        return jsonify({"status": "ok", "message": "Pallet updated", "db_timestamp": db_timestamp})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/create_new_pallet", methods=["POST"])
@check_startup_error
def create_new_pallet():
    """Create a new pallet entry with next ID and specified yolk color"""
    data = request.json

    # Get the most recent pallet to determine next ID
    recent = db.get_most_recent_pallet(DB_FILE)

    if recent and recent.get("pallet_id"):
        # Try to parse and increment the pallet ID
        try:
            current_id = int(recent["pallet_id"])
            next_id = str(current_id + 1)
        except (ValueError, TypeError):
            # If it's not a number, just use empty string
            next_id = ""
    else:
        # No previous pallet or no ID, start fresh
        next_id = ""

    # Get yolk color from request (defaults to previous or empty)
    yolk_color = data.get("yolk_color", "")
    if not yolk_color and recent:
        yolk_color = recent.get("yolk_color", "")

    # Create the new pallet entry
    new_pallet_id = db.create_new_pallet_entry(DB_FILE, pallet_id=next_id, yolk_color=yolk_color)

    # Fetch and return the newly created pallet
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM Pallet_Log WHERE id = ?", (new_pallet_id,))
    new_pallet = dict(cur.fetchone())
    conn.close()

    # Get DB timestamp for polling
    db_timestamp = DB_FILE.stat().st_mtime if DB_FILE and DB_FILE.exists() else 0
    new_pallet["db_timestamp"] = db_timestamp

    return jsonify(new_pallet)

@app.route("/mark_pallet_completed/<int:pallet_id>", methods=["POST"])
@check_startup_error
def mark_pallet_completed(pallet_id):
    """Mark a pallet as completed"""
    try:
        rows_updated = db.mark_pallet_completed(DB_FILE, pallet_id)
        if rows_updated > 0:
            # Get DB timestamp for polling
            db_timestamp = DB_FILE.stat().st_mtime if DB_FILE and DB_FILE.exists() else 0
            return jsonify({"status": "ok", "message": "Pallet marked as completed", "db_timestamp": db_timestamp})
        else:
            return jsonify({"status": "error", "message": "Pallet not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/config", methods=["GET"])
@check_startup_error
def get_config():
    config = load_config()
    return jsonify(config)

@app.route("/add_daily_userlog", methods=["POST"])
@check_startup_error
def add_daily_userlog():
    import json
    data = request.json
    date_val = date.today().isoformat()
    belt_eggs = data.get("belt_eggs")
    floor_eggs = data.get("floor_eggs")

    # Calculate total_eggs based on floor_eggs_through_belt setting
    config = load_config()
    floor_eggs_through_belt = config["farm"]["floor_eggs_through_belt"]

    belt_eggs_int = int(belt_eggs or 0)
    floor_eggs_int = int(floor_eggs or 0)

    if floor_eggs_through_belt:
        # Floor eggs go through belt, so total = belt only
        total_eggs = belt_eggs_int
    else:
        # Floor eggs counted separately, so total = belt + floor
        total_eggs = belt_eggs_int + floor_eggs_int
    mortality_indoor = data.get("mortality_indoor")
    mortality_outdoor = data.get("mortality_outdoor")
    euthanized_indoor = data.get("euthanized_indoor")
    euthanized_outdoor = data.get("euthanized_outdoor")
    depop = data.get("depop")
    amount_delivered = data.get("amount_delivered")
    mortality_reasons = data.get("mortality_reasons")
    cull_reasons = data.get("cull_reasons")
    if isinstance(mortality_reasons, list):
        mortality_reasons = json.dumps(mortality_reasons)
    if isinstance(cull_reasons, list):
        cull_reasons = json.dumps(cull_reasons)
    mortality_comments = data.get("mortality_comments")
    coolerlog_comments = data.get("coolerlog_comments")
    added_supplements = data.get("added_supplements")
    birds_restricted_reason = data.get("birds_restricted_reason")
    comments = data.get("comments")
    weather = data.get("weather")
    air_sensory = data.get("air_sensory")
    ration = data.get("ration")
    drinkers_clean = data.get("drinkers_clean")
    birds_under_slats = data.get("birds_under_slats")
    safe_indoors = data.get("safe_indoors")
    safe_outdoors = data.get("safe_outdoors")
    equipment_functioning = data.get("equipment_functioning")
    predator_activity = data.get("predator_activity")
    eggs_picked_up = data.get("eggs_picked_up")
    door_open = data.get("door_open")
    door_closed = data.get("door_closed")

    db.insert_daily_user_log(
        DB_FILE,
        date=date_val,
        belt_eggs=belt_eggs,
        floor_eggs=floor_eggs,
        total_eggs=total_eggs,
        mortality_indoor=mortality_indoor,
        mortality_outdoor=mortality_outdoor,
        euthanized_indoor=euthanized_indoor,
        euthanized_outdoor=euthanized_outdoor,
        depop=depop,
        amount_delivered=amount_delivered,
        mortality_reasons=mortality_reasons,
        cull_reasons=cull_reasons,
        mortality_comments=mortality_comments,
        coolerlog_comments=coolerlog_comments,
        added_supplements=added_supplements,
        birds_restricted_reason=birds_restricted_reason,
        comments=comments,
        weather=weather,
        air_sensory=air_sensory,
        ration=ration,
        drinkers_clean=drinkers_clean,
        birds_under_slats=birds_under_slats,
        safe_indoors=safe_indoors,
        safe_outdoors=safe_outdoors,
        equipment_functioning=equipment_functioning,
        predator_activity=predator_activity,
        eggs_picked_up=eggs_picked_up,
        door_open=door_open,
        door_closed=door_closed
    )

    # Get DB timestamp for polling
    db_timestamp = DB_FILE.stat().st_mtime if DB_FILE and DB_FILE.exists() else 0

    return jsonify({"status": "ok", "message": "Daily userlog saved!", "db_timestamp": db_timestamp})

@app.route("/save_settings", methods=["POST"])
@check_startup_error
def save_settings():
    data = request.json
    try:
        config = load_config()
        config["farm"]["hatch_date"] = data.get("hatch_date")
        config["farm"]["birds_arrived_date"] = data.get("birds_arrived_date")
        config["farm"]["nws_station_id"] = data.get("nws_station_id")
        config["farm"]["floor_eggs_through_belt"] = data.get("floor_eggs_through_belt", False)
        config["farm"]["pallet_tare"] = data.get("pallet_tare", 192)
        config["farm"]["cases_per_pallet"] = data.get("cases_per_pallet", 30)
        save_config(config)

        # Get DB timestamp for polling
        db_timestamp = DB_FILE.stat().st_mtime if DB_FILE and DB_FILE.exists() else 0

        return jsonify({"status": "ok", "message": "Settings saved!", "db_timestamp": db_timestamp})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to save settings: {e}"}), 500

# Endpoint to get farm settings
@app.route("/get_settings", methods=["GET"])
@check_startup_error
def get_settings():
    try:
        config = load_config()
        return jsonify({
            "hatch_date": config["farm"]["hatch_date"],
            "birds_arrived_date": config["farm"]["birds_arrived_date"],
            "nws_station_id": config["farm"]["nws_station_id"],
            "floor_eggs_through_belt": config["farm"]["floor_eggs_through_belt"],
            "pallet_tare": config["farm"]["pallet_tare"],
            "cases_per_pallet": config["farm"]["cases_per_pallet"]
        })
    except Exception:
        return jsonify({"hatch_date": "", "birds_arrived_date": "", "nws_station_id": "", "pallet_tare": 192, "cases_per_pallet": 30})

# Endpoint to get full configuration
@app.route("/get_secrets", methods=["GET"])
@check_startup_error
def get_secrets():
    try:
        config = load_config()
        # Return flattened config for backwards compatibility with UI
        return jsonify({
            "Unitas_Username": config["unitas"]["username"],
            "Unitas_Password": config["unitas"]["password"],
            "Farm_ID": config["unitas"]["farm_id"],
            "House_ID": config["unitas"]["house_id"],
            "Cooler_Log_To_Unitas": config["unitas"]["cooler_log_enabled"],
            "Cooler_Log_Initials": config["unitas"]["cooler_log_initials"],
            "path_to_xmls": config["xml"]["path"],
            "how_long_to_save_old_files": config["xml"]["retention_days"],
            "retrieve_from_xml_time": config["xml"]["retrieve_time"],
            "get_cooler_temp_AM": config["cooler"]["am_time"],
            "get_cooler_temp_PM": config["cooler"]["pm_time"],
            "cooler_temp_time_tolerance": config["cooler"]["time_tolerance"],
            "telegram_bot_token": config.get("telegram", {}).get("bot_token", ""),
            "telegram_chat_id": config.get("telegram", {}).get("chat_id", ""),
            "time_zone": config["system"]["time_zone"],
            "Timeout": config["system"]["timeout"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint to save configuration
@app.route("/save_secrets", methods=["POST"])
@check_startup_error
def save_secrets():
    data = request.json
    try:
        config = load_config()

        # Update config sections from flat data
        if "Unitas_Username" in data:
            config["unitas"]["username"] = data["Unitas_Username"]
        if "Unitas_Password" in data:
            config["unitas"]["password"] = data["Unitas_Password"]
        if "Farm_ID" in data:
            config["unitas"]["farm_id"] = data["Farm_ID"]
        if "House_ID" in data:
            config["unitas"]["house_id"] = data["House_ID"]
        if "Cooler_Log_To_Unitas" in data:
            config["unitas"]["cooler_log_enabled"] = data["Cooler_Log_To_Unitas"]
        if "Cooler_Log_Initials" in data:
            config["unitas"]["cooler_log_initials"] = data["Cooler_Log_Initials"]
        if "path_to_xmls" in data:
            config["xml"]["path"] = data["path_to_xmls"]
        if "how_long_to_save_old_files" in data:
            config["xml"]["retention_days"] = data["how_long_to_save_old_files"]
        if "retrieve_from_xml_time" in data:
            config["xml"]["retrieve_time"] = data["retrieve_from_xml_time"]
        if "get_cooler_temp_AM" in data:
            config["cooler"]["am_time"] = data["get_cooler_temp_AM"]
        if "get_cooler_temp_PM" in data:
            config["cooler"]["pm_time"] = data["get_cooler_temp_PM"]
        if "cooler_temp_time_tolerance" in data:
            config["cooler"]["time_tolerance"] = data["cooler_temp_time_tolerance"]
        if "time_zone" in data:
            config["system"]["time_zone"] = data["time_zone"]
        if "Timeout" in data:
            config["system"]["timeout"] = data["Timeout"]
        if "telegram_bot_token" in data:
            config["telegram"]["bot_token"] = data["telegram_bot_token"]
        if "telegram_chat_id" in data:
            config["telegram"]["chat_id"] = data["telegram_chat_id"]

        save_config(config)

        # Get DB timestamp for polling
        db_timestamp = DB_FILE.stat().st_mtime if DB_FILE and DB_FILE.exists() else 0

        return jsonify({"status": "ok", "message": "Configuration saved successfully!", "db_timestamp": db_timestamp})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to save configuration: {e}"}), 500

# Endpoint to fetch current weather from NWS
@app.route("/get_weather", methods=["GET"])
@check_startup_error
def get_weather():
    try:
        config = load_config()
        station_id = config["farm"].get("nws_station_id")

        if not station_id:
            return jsonify({"weather": None, "error": "No weather station configured"})

        weather = fetch_nws_weather(station_id)
        return jsonify({"weather": weather})
    except Exception:
        return jsonify({"weather": None, "error": "No weather station configured"})

# Endpoint to save default values
@app.route("/save_defaults", methods=["POST"])
@check_startup_error
def save_defaults():
    data = request.json
    try:
        config = load_config()
        config["form_defaults"] = data
        save_config(config)

        # Get DB timestamp for polling
        db_timestamp = DB_FILE.stat().st_mtime if DB_FILE and DB_FILE.exists() else 0

        return jsonify({"status": "ok", "message": "Defaults saved!", "db_timestamp": db_timestamp})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to save defaults: {e}"}), 500

# Endpoint to get default values
@app.route("/get_defaults", methods=["GET"])
@check_startup_error
def get_defaults():
    try:
        config = load_config()
        return jsonify(config.get("form_defaults", {}))
    except Exception:
        return jsonify({})

@app.route("/get_last_update_time", methods=["GET"])
@check_startup_error
def get_last_update_time():
    """Return the last modification time of the database file for polling"""
    try:
        if DB_FILE and DB_FILE.exists():
            mtime = DB_FILE.stat().st_mtime
            return jsonify({"last_update": mtime})
        else:
            return jsonify({"last_update": 0})
    except Exception as e:
        return jsonify({"last_update": 0, "error": str(e)})


# Endpoint to update user log for a specific date
TRIGGER_FILE_PATH = CONFIG_DIR / "pending_upload"

def trigger_unitas_upload(date_str):
    """
    Trigger Unitas upload for a specific date.
    - If date is today: Do nothing (waits for 3 AM check)
    - If date is not today: Create pending_upload trigger file
    """
    today_str = date.today().isoformat()

    if date_str == today_str:
        print(f"[Upload] Date {date_str} is today - will upload at 3 AM")
        return

    try:
        # Create trigger file for non-today dates
        TRIGGER_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        TRIGGER_FILE_PATH.touch()
        print(f"[Upload] Created trigger file for {date_str}")
    except Exception as e:
        print(f"[Upload] Error creating trigger file: {e}")

@app.route("/update_user_log", methods=["POST"])
@check_startup_error
def update_user_log():
    data = request.json
    # Get date from query parameter, default to today
    date_str = request.args.get('date', date.today().isoformat())
    # Get the current record to find the rowid or unique key
    user_log = db.get_daily_user_log(DB_FILE, date_str)

    # Calculate total_eggs based on floor_eggs_through_belt setting
    if 'belt_eggs' in data or 'floor_eggs' in data:
        config = load_config()
        floor_eggs_through_belt = config["farm"]["floor_eggs_through_belt"]

        belt_eggs = int(data.get('belt_eggs', 0) or 0)
        floor_eggs = int(data.get('floor_eggs', 0) or 0)

        if floor_eggs_through_belt:
            # Floor eggs go through belt, so total = belt only
            data['total_eggs'] = belt_eggs
        else:
            # Floor eggs counted separately, so total = belt + floor
            data['total_eggs'] = belt_eggs + floor_eggs

    # Check if send_to_bot is being changed from 0 to 1
    send_to_bot_changed = False
    if 'send_to_bot' in data:
        old_send_to_bot = user_log.get('send_to_bot') if user_log else 0
        new_send_to_bot = data['send_to_bot']
        # Trigger upload if changing from unchecked to checked
        if not old_send_to_bot and new_send_to_bot:
            send_to_bot_changed = True

    try:
        if not user_log:
            # No log exists, create a new one
            data['date'] = date_str
            db.insert_daily_user_log(DB_FILE, **data)
            message = f"User log created for {date_str}."
        else:
            # Update existing log
            db.update_daily_user_log(DB_FILE, date_str, data)
            message = f"User log updated for {date_str}."

        # Trigger upload if checkbox was just checked
        if send_to_bot_changed:
            # Check that bot_log exists before triggering upload
            bot_log = db.get_daily_bot_log(DB_FILE, date_str)
            if bot_log:
                trigger_unitas_upload(date_str)
                if date_str == date.today().isoformat():
                    message += " Will upload at 3 AM."
                else:
                    message += " Upload triggered."
            else:
                message += " Warning: No bot log data found for this date - skipping upload."

        # Get DB timestamp for polling
        db_timestamp = DB_FILE.stat().st_mtime if DB_FILE and DB_FILE.exists() else 0

        return jsonify({"status": "ok", "message": message, "db_timestamp": db_timestamp})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Endpoint to update today's bot log
@app.route("/update_bot_log", methods=["POST"])
@check_startup_error
def update_bot_log():
    data = request.json
    today_str = date.today().isoformat()
    bot_log = db.get_daily_bot_log(DB_FILE, today_str)
    if not bot_log:
        return jsonify({"status": "error", "message": "No bot log for today."}), 404
    # Use date or unique key for update
    date_key = bot_log.get("date")
    if not date_key:
        return jsonify({"status": "error", "message": "No date in bot log."}), 400
    try:
        db.update_daily_bot_log(DB_FILE, date_key, data)

        # Get DB timestamp for polling
        db_timestamp = DB_FILE.stat().st_mtime if DB_FILE and DB_FILE.exists() else 0

        return jsonify({"status": "ok", "message": "Bot log updated.", "db_timestamp": db_timestamp})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# API endpoint to check send_to_bot status for a date range
@app.route("/api/check_send_to_bot")
@check_startup_error
def check_send_to_bot():
    """Check if dates have send_to_bot flag set"""
    date_str = request.args.get('date')
    direction = request.args.get('direction', 'current')  # 'current', 'prev', 'next'

    if not date_str:
        return jsonify({"error": "No date provided"}), 400

    user_log = db.get_daily_user_log(DB_FILE, date_str)
    send_to_bot = user_log and (user_log.get('send_to_bot') == 1 or user_log.get('send_to_bot') == '1' or user_log.get('send_to_bot') == True)

    return jsonify({
        "date": date_str,
        "send_to_bot": send_to_bot
    })

# API endpoint to find next available editable date
@app.route("/api/find_editable_date")
@check_startup_error
def find_editable_date():
    """Find the next date in the given direction that doesn't have send_to_bot checked"""
    start_date_str = request.args.get('start_date')
    direction = request.args.get('direction', 'prev')  # 'prev' or 'next'
    max_days = int(request.args.get('max_days', 365))  # Maximum days to search

    if not start_date_str:
        return jsonify({"error": "No start_date provided"}), 400

    from datetime import datetime, timedelta
    start_date = datetime.fromisoformat(start_date_str).date()
    today = date.today()
    offset = -1 if direction == 'prev' else 1

    # Search for an editable date
    for i in range(1, max_days + 1):
        check_date = start_date + timedelta(days=offset * i)

        # Don't go beyond today
        if check_date > today:
            break

        # Don't go too far back
        if check_date.year < 2020:
            break

        check_date_str = check_date.isoformat()
        user_log = db.get_daily_user_log(DB_FILE, check_date_str)

        # If no log exists or send_to_bot is not checked, this date is editable
        if not user_log or not (user_log.get('send_to_bot') == 1 or user_log.get('send_to_bot') == '1' or user_log.get('send_to_bot') == True):
            return jsonify({
                "found": True,
                "date": check_date_str
            })

    # No editable date found
    return jsonify({
        "found": False,
        "date": None
    })

@app.route("/all_data")
@check_startup_error
def all_data():
    # Fetch all user and bot logs
    user_logs = db.get_all_user_logs(DB_FILE)
    bot_logs = db.get_all_bot_logs(DB_FILE)
    return render_template("all_data.html", user_logs=user_logs, bot_logs=bot_logs)

# API endpoint to fetch all user and bot logs as JSON for History tab
@app.route("/api/all_data")
@check_startup_error
def api_all_data():
    user_logs = db.get_all_user_logs(DB_FILE)
    bot_logs = db.get_all_bot_logs(DB_FILE)
    return jsonify({"user_logs": user_logs, "bot_logs": bot_logs})

# API endpoint to fetch data for a specific date
@app.route("/api/date_data")
@check_startup_error
def api_date_data():
    # Get date from query parameter, default to today
    date_str = request.args.get('date', date.today().isoformat())
    user_log = db.get_daily_user_log(DB_FILE, date_str)

    # If no user log exists for this date, create one with defaults
    if not user_log:
        print(f"DEBUG: No user log found for {date_str}, creating new one")
        defaults = {}

        # Load defaults from config
        try:
            config = load_config()
            defaults = config.get("form_defaults", {}).copy()
            print(f"DEBUG: Loaded defaults: {defaults}")
        except Exception as e:
            print(f"DEBUG: Failed to load defaults from config: {e}")

        # Auto-fetch weather if station is configured (only for today)
        if date_str == date.today().isoformat():
            try:
                config = load_config()
                station_id = config["farm"].get("nws_station_id")
                if station_id:
                    print(f"DEBUG: Attempting to fetch weather for station: {station_id}")
                    weather = fetch_nws_weather(station_id)
                    if weather:
                        print(f"DEBUG: Got weather: {weather}")
                        defaults['weather'] = weather
                    else:
                        print("DEBUG: Weather fetch returned None")
            except Exception as e:
                print(f"DEBUG: Failed to load config for weather: {e}")

            # Auto-fill nutritionist and ration_used from yesterday
            from datetime import timedelta
            yesterday = (date.today() - timedelta(days=1)).isoformat()
            yesterday_log = db.get_daily_user_log(DB_FILE, yesterday)
            if yesterday_log:
                if yesterday_log.get('nutritionist'):
                    defaults['nutritionist'] = yesterday_log.get('nutritionist')
                    print(f"DEBUG: Auto-filled nutritionist from yesterday: {defaults['nutritionist']}")
                if yesterday_log.get('ration_used'):
                    defaults['ration_used'] = yesterday_log.get('ration_used')
                    print(f"DEBUG: Auto-filled ration_used from yesterday: {defaults['ration_used']}")

        # Create new entry with defaults
        defaults['date'] = date_str
        print(f"DEBUG: Creating user log with data: {defaults}")
        try:
            # Check again right before inserting to avoid race condition
            user_log = db.get_daily_user_log(DB_FILE, date_str)
            if not user_log:
                db.insert_daily_user_log(DB_FILE, **defaults)
                user_log = db.get_daily_user_log(DB_FILE, date_str)
                print(f"DEBUG: Created user log: {user_log}")
            else:
                print(f"DEBUG: User log was created by another request, using existing one")
        except Exception as e:
            print(f"DEBUG: Error creating daily user log: {e}")
            import traceback
            traceback.print_exc()
            # Try to get it anyway in case another request created it
            user_log = db.get_daily_user_log(DB_FILE, date_str)
    else:
        print(f"DEBUG: Found existing user log for {date_str}: {user_log}")
        updates = {}

        # Auto-fill nutritionist and ration_used from previous day if empty
        if not user_log.get('nutritionist') or user_log.get('nutritionist', '').strip() == '':
            from datetime import datetime, timedelta
            current_date = datetime.fromisoformat(date_str).date()
            previous_day = (current_date - timedelta(days=1)).isoformat()
            previous_log = db.get_daily_user_log(DB_FILE, previous_day)
            if previous_log and previous_log.get('nutritionist'):
                updates['nutritionist'] = previous_log.get('nutritionist')
                print(f"DEBUG: Auto-filling nutritionist from {previous_day}: {updates['nutritionist']}")

        if not user_log.get('ration_used') or user_log.get('ration_used', '').strip() == '':
            from datetime import datetime, timedelta
            current_date = datetime.fromisoformat(date_str).date()
            previous_day = (current_date - timedelta(days=1)).isoformat()
            previous_log = db.get_daily_user_log(DB_FILE, previous_day)
            if previous_log and previous_log.get('ration_used'):
                updates['ration_used'] = previous_log.get('ration_used')
                print(f"DEBUG: Auto-filling ration_used from {previous_day}: {updates['ration_used']}")

        # If weather is blank and this is today, try to auto-fetch it
        if date_str == date.today().isoformat() and (not user_log.get('weather') or user_log.get('weather').strip() == ''):
            print("DEBUG: Weather is blank, attempting to fetch")
            try:
                config = load_config()
                station_id = config["farm"].get("nws_station_id")
                if station_id:
                    print(f"DEBUG: Attempting to fetch weather for station: {station_id}")
                    weather = fetch_nws_weather(station_id)
                    if weather:
                        print(f"DEBUG: Got weather: {weather}, updating user log")
                        updates['weather'] = weather
                    else:
                        print("DEBUG: Weather fetch returned None")
            except Exception as e:
                print(f"DEBUG: Failed to load config for weather: {e}")

        # Apply all updates at once
        if updates:
            db.update_daily_user_log(DB_FILE, date_str, updates)
            user_log.update(updates)
            print(f"DEBUG: Applied updates to user log: {updates}")

    bot_log = db.get_daily_bot_log(DB_FILE, date_str)
    pallet_log = db.get_pallets_by_date(DB_FILE, date_str)
    return jsonify({"user_log": user_log, "bot_log": bot_log, "pallet_log": pallet_log})

# API endpoint to fetch today's data (kept for backward compatibility)
@app.route("/api/today_data")
@check_startup_error
def api_today_data():
    today_str = date.today().isoformat()
    user_log = db.get_daily_user_log(DB_FILE, today_str)

    # If no user log exists for today, create one with defaults
    if not user_log:
        print("DEBUG: No user log found for today, creating new one")
        defaults = {}

        # Load defaults from config
        try:
            config = load_config()
            defaults = config.get("form_defaults", {}).copy()
            print(f"DEBUG: Loaded defaults: {defaults}")
        except Exception as e:
            print(f"DEBUG: Failed to load defaults from config: {e}")

        # Auto-fetch weather if station is configured
        try:
            config = load_config()
            station_id = config["farm"].get("nws_station_id")
            if station_id:
                print(f"DEBUG: Attempting to fetch weather for station: {station_id}")
                weather = fetch_nws_weather(station_id)
                if weather:
                    print(f"DEBUG: Got weather: {weather}")
                    defaults['weather'] = weather
                else:
                    print("DEBUG: Weather fetch returned None")
        except Exception as e:
            print(f"DEBUG: Failed to load config for weather: {e}")

        # Auto-fill nutritionist and ration_used from yesterday
        from datetime import timedelta
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        yesterday_log = db.get_daily_user_log(DB_FILE, yesterday)
        if yesterday_log:
            if yesterday_log.get('nutritionist'):
                defaults['nutritionist'] = yesterday_log.get('nutritionist')
                print(f"DEBUG: Auto-filled nutritionist from yesterday: {defaults['nutritionist']}")
            if yesterday_log.get('ration_used'):
                defaults['ration_used'] = yesterday_log.get('ration_used')
                print(f"DEBUG: Auto-filled ration_used from yesterday: {defaults['ration_used']}")

        # Create new entry with defaults
        defaults['date'] = today_str
        print(f"DEBUG: Creating user log with data: {defaults}")
        try:
            # Check again right before inserting to avoid race condition
            user_log = db.get_daily_user_log(DB_FILE, today_str)
            if not user_log:
                db.insert_daily_user_log(DB_FILE, **defaults)
                user_log = db.get_daily_user_log(DB_FILE, today_str)
                print(f"DEBUG: Created user log: {user_log}")
            else:
                print(f"DEBUG: User log was created by another request, using existing one")
        except Exception as e:
            print(f"DEBUG: Error creating daily user log: {e}")
            import traceback
            traceback.print_exc()
            # Try to get it anyway in case another request created it
            user_log = db.get_daily_user_log(DB_FILE, today_str)
    else:
        print(f"DEBUG: Found existing user log: {user_log}")
        # If weather is blank, try to auto-fetch it
        if not user_log.get('weather') or user_log.get('weather').strip() == '':
            print("DEBUG: Weather is blank, attempting to fetch")
            if os.path.exists(settings_path):
                with open(settings_path, "r") as f:
                    settings = json.load(f)
                station_id = settings.get("nws_station_id")
                if station_id:
                    print(f"DEBUG: Attempting to fetch weather for station: {station_id}")
                    weather = fetch_nws_weather(station_id)
                    if weather:
                        print(f"DEBUG: Got weather: {weather}, updating user log")
                        # Update the weather field
                        db.update_daily_user_log(DB_FILE, today_str, {'weather': weather})
                        user_log['weather'] = weather
                    else:
                        print("DEBUG: Weather fetch returned None")

    bot_log = db.get_daily_bot_log(DB_FILE, today_str)
    return jsonify({"user_log": user_log, "bot_log": bot_log})

# Service management endpoints
@app.route("/api/service_status", methods=["GET"])
@check_startup_error
def service_status():
    """Get status of datalogger and xml-watcher services"""
    try:
        services = {}
        for service_name in ['datalogger', 'xml-watcher']:
            result = subprocess.run(
                ['systemctl', 'show', f'{service_name}.service', '--property=ActiveState,SubState'],
                capture_output=True,
                text=True,
                timeout=5
            )

            # Parse output: ActiveState=active\nSubState=running
            status = {}
            for line in result.stdout.strip().split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    if key == 'ActiveState':
                        status['active'] = value
                    elif key == 'SubState':
                        status['sub_state'] = value

            services[service_name] = status

        return jsonify({"status": "ok", "services": services})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/service_control", methods=["POST"])
@check_startup_error
def service_control():
    """Start, stop, or restart a service"""
    data = request.json
    service = data.get('service')
    action = data.get('action')

    # Validate inputs
    allowed_services = ['datalogger', 'xml-watcher']
    allowed_actions = ['start', 'stop', 'restart']

    if service not in allowed_services:
        return jsonify({"status": "error", "message": f"Invalid service: {service}"}), 400

    if action not in allowed_actions:
        return jsonify({"status": "error", "message": f"Invalid action: {action}"}), 400

    try:
        # Execute systemctl command
        result = subprocess.run(
            ['sudo', 'systemctl', action, f'{service}.service'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return jsonify({
                "status": "ok",
                "message": f"Successfully {action}ed {service} service"
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Failed to {action} {service}: {result.stderr}"
            }), 500
    except subprocess.TimeoutExpired:
        return jsonify({"status": "error", "message": "Command timed out"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/manual_send_to_unitas", methods=["POST"])
@check_startup_error
def manual_send_to_unitas():
    """Manually trigger Unitas upload for a specific date"""
    data = request.json
    date_str = data.get('date')

    if not date_str:
        return jsonify({"status": "error", "message": "No date provided"}), 400

    # Validate that bot log exists
    bot_log = db.get_daily_bot_log(DB_FILE, date_str)
    if not bot_log:
        return jsonify({"status": "error", "message": "No bot log data found for this date"}), 400

    # Validate that send_to_bot is checked
    user_log = db.get_daily_user_log(DB_FILE, date_str)
    if not user_log or not user_log.get('send_to_bot'):
        return jsonify({"status": "error", "message": "Schedule Send to Unitas must be checked"}), 400

    # Clear the sent_to_unitas_at timestamp to force a resend
    try:
        db.update_daily_user_log(DB_FILE, date_str, {
            'sent_to_unitas_at': None
        })
        print(f"Cleared sent_to_unitas_at timestamp for {date_str} to force manual send")
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to reset upload status: {e}"}), 500

    # Trigger the datalogger service to process the upload
    # Create a trigger file that the datalogger service watches for
    trigger_file = CONFIG_DIR / "pending_upload"
    try:
        trigger_file.touch()
        print(f"Created trigger file for manual upload of {date_str}")
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to trigger upload: {e}"}), 500

    return jsonify({
        "status": "ok",
        "message": f"Unitas upload triggered for {date_str}. The datalogger service will process it shortly."
    })

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Farm Data Web Application")
    parser.add_argument("--port", type=int, default=None, help="Port to run the web server on (overrides config)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind the web server to")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    args = parser.parse_args()

    # Check deployment mode
    deployment_mode = get_deployment_mode()

    if deployment_mode == "production":
        print("ERROR: Deployment mode is set to 'production' in config.")
        print("The Flask development server should not be used in production mode.")
        print("Please either:")
        print("  1. Change deployment.mode to 'localhost' in ~/.datalogger/config.json")
        print("  2. Run the application through Apache/WSGI instead")
        sys.exit(1)

    # Use config port if not overridden by command line
    port = args.port if args.port is not None else get_localhost_port()

    print(f"Starting web server in LOCALHOST mode on {args.host}:{port}")
    print(f"Using database: {DB_FILE}")
    app.run(host=args.host, port=port, debug=args.debug)