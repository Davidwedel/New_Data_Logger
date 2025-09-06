
from flask import Flask, jsonify, render_template
import sqlite3

app = Flask(__name__)
DB_FILE = "database.db"

def get_dailylog():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        SELECT TimeStamp, Date_Of_Data, Feed_Consumption, Body_Weight
        FROM botdailylog
        ORDER BY TimeStamp DESC
        LIMIT 50
    """)
    rows = cur.fetchall()
    conn.close()
    return [
        {"timestamp": r[0], "date": r[1], "feed": r[2], "weight": r[3]}
        for r in rows
    ]

@app.route("/")
def index():
    return render_template("index.html")  # make sure templates/index.html exists

@app.route("/api/dailylog")
def dailylog_api():
    return jsonify(get_dailylog())

if __name__ == "__main__":
    app.run(debug=True)
