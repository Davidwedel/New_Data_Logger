from flask import Flask, request, jsonify, render_template
import sqlite3
from datetime import date
import database_helper as db

app = Flask(__name__)

@app.route("/")   # homepage route
def index():
    return render_template("index.html")

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
    data = request.json

    # Extract checkbox arrays
    mortality_reasons = ",".join(data.get("mortality_reasons", []))
    cull_reasons = ",".join(data.get("cull_reasons", []))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute('''
        INSERT INTO daily_userdata (
            belt_eggs, floor_eggs,
            mortality_indoor, mortality_outdoor,
            euthanized_indoor, euthanized_outdoor,
            depop, amount_delivered,
            mortality_reasons, cull_reasons,
            mortality_comments, coolerlog_comments, added_supplements, birds_restricted_reason, comments,
            weather, air_sensory, ration,
            drinkers_clean, birds_under_slats, safe_indoors, safe_outdoors, equipment_functioning, predator_activity,
            eggs_picked_up, door_open, door_closed
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        data.get("belt_eggs", 0),
        data.get("floor_eggs", 0),
        data.get("mortality_indoor", 0),
        data.get("mortality_outdoor", 0),
        data.get("euthanized_indoor", 0),
        data.get("euthanized_outdoor", 0),
        data.get("depop", 0),
        data.get("amount_delivered", 0),
        mortality_reasons,
        cull_reasons,
        data.get("mortality_comments", ""),
        data.get("coolerlog_comments", ""),
        data.get("added_supplements", ""),
        data.get("birds_restricted_reason", ""),
        data.get("comments", ""),
        data.get("weather", ""),
        data.get("air_sensory", 0),
        data.get("ration", ""),
        data.get("drinkers_clean", 0),
        data.get("birds_under_slats", 0),
        data.get("safe_indoors", 0),
        data.get("safe_outdoors", 0),
        data.get("equipment_functioning", 0),
        data.get("predator_activity", 0),
        1 if data.get("eggs_picked_up") else 0,
        data.get("door_open", ""),
        data.get("door_closed", "")
    ))
    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "message": "Daily userlog saved!"})
