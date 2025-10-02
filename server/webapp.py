import os
import json
from flask import Flask, request, jsonify, render_template
import sqlite3
from datetime import date, datetime
import database_helper as db

app = Flask(__name__)

@app.route("/")   # homepage route
def index():
    today_str = date.today().isoformat()
    user_log = db.get_daily_user_log(today_str)
    bot_log = db.get_daily_bot_log(today_str)
    user_logs = db.get_all_user_logs()
    bot_logs = db.get_all_bot_logs()
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

    db.insert_pallet_log(thedate, pallet_id, house_id, total_pallet_weight, case_weight, flock_age, yolk_color)

    return jsonify({"status": "ok", "message": "Pallet saved!"})

@app.route("/add_daily_userlog", methods=["POST"])
def add_daily_userlog():
    import json
    data = request.json
    date_entered = datetime.now().isoformat()
    belt_eggs = data.get("belt_eggs")
    floor_eggs = data.get("floor_eggs")
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
        date_entered=date_entered,
        belt_eggs=belt_eggs,
        floor_eggs=floor_eggs,
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
    settings = {
        "hatch_date": data.get("hatch_date"),
        "birds_arrived_date": data.get("birds_arrived_date")
    }
    settings_path = os.path.join(os.path.dirname(__file__), "..", "settings.json")
    try:
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)
        return jsonify({"status": "ok", "message": "Settings saved!"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to save settings: {e}"}), 500

# Endpoint to get farm settings
@app.route("/get_settings", methods=["GET"])
def get_settings():
    import json, os
    settings_path = os.path.join(os.path.dirname(__file__), "..", "settings.json")
    if not os.path.exists(settings_path):
        return jsonify({"hatch_date": "", "birds_arrived_date": ""})
    with open(settings_path, "r") as f:
        settings = json.load(f)
    return jsonify(settings)



# API endpoint to set a flag in .runstate.json
@app.route("/set_flag", methods=["POST"])
def set_flag():
    data = request.json
    flag = data.get("flag")
    if not flag:
        return jsonify({"status": "error", "message": "No flag specified"}), 400
    try:
        import runstate
        runstate.save_data(flag)
        return jsonify({"status": "ok", "message": f"Flag '{flag}' set for today"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Endpoint to update today's user log
@app.route("/update_user_log", methods=["POST"])
def update_user_log():
    data = request.json
    today_str = date.today().isoformat()
    # Get the current record to find the rowid or unique key
    user_log = db.get_daily_user_log(today_str)
    if not user_log:
        return jsonify({"status": "error", "message": "No user log for today."}), 404
    # Use date_entered as unique key for update
    date_entered = user_log.get("date_entered")
    if not date_entered:
        return jsonify({"status": "error", "message": "No date_entered in user log."}), 400
    try:
        db.update_daily_user_log(date_entered, data)
        return jsonify({"status": "ok", "message": "User log updated."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Endpoint to update today's bot log
@app.route("/update_bot_log", methods=["POST"])
def update_bot_log():
    data = request.json
    today_str = date.today().isoformat()
    bot_log = db.get_daily_bot_log(today_str)
    if not bot_log:
        return jsonify({"status": "error", "message": "No bot log for today."}), 404
    # Use date or unique key for update
    date_key = bot_log.get("date")
    if not date_key:
        return jsonify({"status": "error", "message": "No date in bot log."}), 400
    try:
        db.update_daily_bot_log(date_key, data)
        return jsonify({"status": "ok", "message": "Bot log updated."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/all_data")
def all_data():
    # Fetch all user and bot logs
    user_logs = db.get_all_user_logs()
    bot_logs = db.get_all_bot_logs()
    return render_template("all_data.html", user_logs=user_logs, bot_logs=bot_logs)

# API endpoint to fetch all user and bot logs as JSON for History tab
@app.route("/api/all_data")
def api_all_data():
    user_logs = db.get_all_user_logs()
    bot_logs = db.get_all_bot_logs()
    return jsonify({"user_logs": user_logs, "bot_logs": bot_logs})

# API endpoint to fetch today's data
@app.route("/api/today_data")
def api_today_data():
    today_str = date.today().isoformat()
    user_log = db.get_daily_user_log(today_str)
    bot_log = db.get_daily_bot_log(today_str)
    return jsonify({"user_log": user_log, "bot_log": bot_log})