
from flask import Flask, request, jsonify, render_template
import sqlite3

app = Flask(__name__)

# Ensure DB + table exist
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    #pallet log table
    c.execute('''CREATE TABLE IF NOT EXISTS pallets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    pallet_id TEXT,
                    house_id REAL,
                    total_pallet_weight REAL,
                    case_weight REAL,
                    flock_age REAL,
                    yolk_color TEXT
                )''')

    # daily userlog table

# Daily farm data table
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_userdata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_entered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            belt_eggs INTEGER DEFAULT 0,
            floor_eggs INTEGER DEFAULT 0,
            
            mortality_indoor INTEGER DEFAULT 0,
            mortality_outdoor INTEGER DEFAULT 0,
            euthanized_indoor INTEGER DEFAULT 0,
            euthanized_outdoor INTEGER DEFAULT 0,
            
            depop INTEGER DEFAULT 0,
            amount_delivered INTEGER DEFAULT 0,
            
            mortality_reasons TEXT,
            cull_reasons TEXT,
            mortality_comments TEXT,
            coolerlog_comments TEXT,
            added_supplements TEXT,
            birds_restricted_reason TEXT,
            comments TEXT,
            
            weather TEXT,
            air_sensory INTEGER DEFAULT 0,
            ration TEXT,
            drinkers_clean INTEGER DEFAULT 0,
            birds_under_slats INTEGER DEFAULT 0,
            safe_indoors INTEGER DEFAULT 0,
            safe_outdoors INTEGER DEFAULT 0,
            equipment_functioning INTEGER DEFAULT 0,
            predator_activity INTEGER DEFAULT 0,
            
            eggs_picked_up INTEGER DEFAULT 0,
            door_open TEXT,
            door_closed TEXT
        )
    ''')

    conn.commit()
    conn.close()

@app.route("/")   # 👈 homepage route
def index():
    return render_template("index.html")

@app.route("/add_pallet", methods=["POST"])
def add_pallet():
    data = request.json
    pallet_id = data.get("pallet_id")
    weight = data.get("weight")
    yolk_color = data.get("yolk_color")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT INTO pallets (pallet_id, weight, yolk_color) VALUES (?, ?, ?)",
              (pallet_id, weight, yolk_color))
    conn.commit()
    conn.close()

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
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
