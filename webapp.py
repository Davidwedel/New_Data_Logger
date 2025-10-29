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
from server.config import load_config, save_config, get_flat_config
import server.unitas_manager.unitas_production as unitas

app = Flask(__name__)

# Initialize database on startup
DB_FILE = pathlib.Path.home() / ".datalogger" / "database.db"
# Ensure directory exists
DB_FILE.parent.mkdir(parents=True, exist_ok=True)
db.setup_db(DB_FILE)

# Initialize Unitas module with config
try:
    config = get_flat_config()
    unitas.do_unitas_setup(config)
except Exception as e:
    print(f"Warning: Failed to initialize Unitas module: {e}")

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

@app.route("/")   # homepage route
def index():
    today_str = date.today().isoformat()
    user_log = db.get_daily_user_log(DB_FILE, today_str)
    bot_log = db.get_daily_bot_log(DB_FILE, today_str)
    user_logs = db.get_all_user_logs(DB_FILE)
    bot_logs = db.get_all_bot_logs(DB_FILE)
    return render_template("index.html", user_log=user_log, bot_log=bot_log, user_logs=user_logs, bot_logs=bot_logs)

@app.route("/add_pallet", methods=["POST"])
def add_pallet():
    data = request.json
    thedate = date.today().isoformat() 
    pallet_id = data.get("pallet_id")
    house_id = 1
    total_pallet_weight = float(data.get("weight", 0))
    case_weight = (total_pallet_weight - 192) / 30
    flock_age = 22.5
    yolk_color = data.get("yolk_color")

    db.insert_pallet_log(DB_FILE, thedate, pallet_id, house_id, total_pallet_weight, case_weight, flock_age, yolk_color)

    return jsonify({"status": "ok", "message": "Pallet saved!"})

@app.route("/add_daily_userlog", methods=["POST"])
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


    return jsonify({"status": "ok", "message": "Daily userlog saved!"})

@app.route("/save_settings", methods=["POST"])
def save_settings():
    data = request.json
    try:
        config = load_config()
        config["farm"]["hatch_date"] = data.get("hatch_date")
        config["farm"]["birds_arrived_date"] = data.get("birds_arrived_date")
        config["farm"]["nws_station_id"] = data.get("nws_station_id")
        config["farm"]["floor_eggs_through_belt"] = data.get("floor_eggs_through_belt", False)
        save_config(config)
        return jsonify({"status": "ok", "message": "Settings saved!"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to save settings: {e}"}), 500

# Endpoint to get farm settings
@app.route("/get_settings", methods=["GET"])
def get_settings():
    try:
        config = load_config()
        return jsonify({
            "hatch_date": config["farm"]["hatch_date"],
            "birds_arrived_date": config["farm"]["birds_arrived_date"],
            "nws_station_id": config["farm"]["nws_station_id"],
            "floor_eggs_through_belt": config["farm"]["floor_eggs_through_belt"]
        })
    except Exception:
        return jsonify({"hatch_date": "", "birds_arrived_date": "", "nws_station_id": ""})

# Endpoint to get full configuration
@app.route("/get_secrets", methods=["GET"])
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
        return jsonify({"status": "ok", "message": "Configuration saved successfully!"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to save configuration: {e}"}), 500

# Endpoint to fetch current weather from NWS
@app.route("/get_weather", methods=["GET"])
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
def save_defaults():
    data = request.json
    try:
        config = load_config()
        config["form_defaults"] = data
        save_config(config)
        return jsonify({"status": "ok", "message": "Defaults saved!"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to save defaults: {e}"}), 500

# Endpoint to get default values
@app.route("/get_defaults", methods=["GET"])
def get_defaults():
    try:
        config = load_config()
        return jsonify(config.get("form_defaults", {}))
    except Exception:
        return jsonify({})




# Endpoint to update user log for a specific date
def trigger_unitas_upload_background(date_str):
    """Run Unitas upload in background thread for specific date"""
    try:
        print(f"[Background] Starting Unitas upload for {date_str}")
        config = get_flat_config()
        unitas.run_unitas_stuff(config, DB_FILE, target_date=date_str)
        print(f"[Background] Completed Unitas upload for {date_str}")
    except Exception as e:
        print(f"[Background] Error uploading {date_str} to Unitas: {e}")

@app.route("/update_user_log", methods=["POST"])
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

        # Trigger Unitas upload in background if checkbox was just checked
        if send_to_bot_changed:
            # Check that bot_log exists before uploading
            bot_log = db.get_daily_bot_log(DB_FILE, date_str)
            if bot_log:
                thread = threading.Thread(target=trigger_unitas_upload_background, args=(date_str,))
                thread.daemon = True
                thread.start()
                message += " Upload to Unitas started."
            else:
                message += " Warning: No bot log data found for this date - skipping upload."

        return jsonify({"status": "ok", "message": message})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Endpoint to update today's bot log
@app.route("/update_bot_log", methods=["POST"])
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
        return jsonify({"status": "ok", "message": "Bot log updated."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# API endpoint to check send_to_bot status for a date range
@app.route("/api/check_send_to_bot")
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
def all_data():
    # Fetch all user and bot logs
    user_logs = db.get_all_user_logs(DB_FILE)
    bot_logs = db.get_all_bot_logs(DB_FILE)
    return render_template("all_data.html", user_logs=user_logs, bot_logs=bot_logs)

# API endpoint to fetch all user and bot logs as JSON for History tab
@app.route("/api/all_data")
def api_all_data():
    user_logs = db.get_all_user_logs(DB_FILE)
    bot_logs = db.get_all_bot_logs(DB_FILE)
    return jsonify({"user_logs": user_logs, "bot_logs": bot_logs})

# API endpoint to fetch data for a specific date
@app.route("/api/date_data")
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
                        # Update the weather field
                        db.update_daily_user_log(DB_FILE, date_str, {'weather': weather})
                        user_log['weather'] = weather
                    else:
                        print("DEBUG: Weather fetch returned None")
            except Exception as e:
                print(f"DEBUG: Failed to load config for weather: {e}")

    bot_log = db.get_daily_bot_log(DB_FILE, date_str)
    return jsonify({"user_log": user_log, "bot_log": bot_log})

# API endpoint to fetch today's data (kept for backward compatibility)
@app.route("/api/today_data")
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

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Farm Data Web Application")
    parser.add_argument("--port", type=int, default=5000, help="Port to run the web server on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind the web server to")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    args = parser.parse_args()

    print(f"Starting web server on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)