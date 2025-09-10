
from flask import Flask, request, jsonify, render_template
import sqlite3

app = Flask(__name__)

# Ensure DB + table exist
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS pallets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pallet_id TEXT,
                    weight REAL,
                    yolk_color TEXT
                )''')
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

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
