import sqlite3

# ------------------- GLOBAL DB FILE -------------------
DB_FILE = None

# ------------------- DATABASE SETUP -------------------
def setup_db(db_file):
    global DB_FILE
    DB_FILE = db_file
    conn = sqlite3.connect(DB_FILE)
    curr = conn.cursor()

    # Data_Log table
    curr.execute('''CREATE TABLE IF NOT EXISTS Daily_Bot_Log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATE,
        bird_age INTEGER,
        feed_consumption REAL,
        lights_on TIME,
        lights_off TIME,
        water_consumption REAL,
        body_weight REAL,
        door_open TIME,
        door_closed TIME,
        birds_restricted INTEGER,
        inside_low_temp REAL,
        inside_high_temp REAL,
        outside_low_temp REAL,
        outside_high_temp REAL,
        cooler_time_am TIME,
        cooler_temp_am REAL,
        cooler_time_pm TIME,
        cooler_temp_pm REAL
    )''')

    # Pallet_Log table
    curr.execute('''CREATE TABLE IF NOT EXISTS Pallet_Log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        thedate TEXT,
        pallet_id TEXT,
        house_id REAL,
        total_pallet_weight REAL,
        case_weight REAL,
        flock_age REAL,
        yolk_color TEXT
    )''')

    # Daily_User_Log table
    curr.execute('''CREATE TABLE IF NOT EXISTS Daily_User_Log (
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
    )''')

    conn.commit()
    conn.close()


# ------------------- GENERIC INSERT HELPER -------------------
def _insert_into_table(table, data_dict):
    if not data_dict:
        raise ValueError("No data provided to insert.")
    cols = ", ".join(data_dict.keys())
    placeholders = ", ".join("?" for _ in data_dict)
    sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(sql, tuple(data_dict.values()))
    conn.commit()
    lastrowid = cur.lastrowid
    conn.close()
    return lastrowid


# ------------------- INSERT FUNCTIONS -------------------

def insert_daily_bot_log(
    date=None,
    bird_age=None,
    feed_consumption=None,
    lights_on=None,
    lights_off=None,
    water_consumption=None,
    body_weight=None,
    door_open=None,
    door_closed=None,
    birds_restricted=None,
    inside_low_temp=None,
    inside_high_temp=None,
    outside_low_temp=None,
    outside_high_temp=None,
    cooler_time_am=None,
    cooler_temp_am=None,
    cooler_time_pm=None,
    cooler_temp_pm=None,
):
    payload = {k: v for k, v in locals().items() if v is not None}
    return _insert_into_table("Daily_Bot_Log", payload)


def insert_pallet_log(
    thedate=None,
    pallet_id=None,
    house_id=None,
    total_pallet_weight=None,
    case_weight=None,
    flock_age=None,
    yolk_color=None,
):
    payload = {k: v for k, v in locals().items() if v is not None}
    return _insert_into_table("Pallet_Log", payload)


def insert_daily_user_log(
    date_entered=None,
    belt_eggs=None,
    floor_eggs=None,
    mortality_indoor=None,
    mortality_outdoor=None,
    euthanized_indoor=None,
    euthanized_outdoor=None,
    depop=None,
    amount_delivered=None,
    mortality_reasons=None,
    cull_reasons=None,
    mortality_comments=None,
    coolerlog_comments=None,
    added_supplements=None,
    birds_restricted_reason=None,
    comments=None,
    weather=None,
    air_sensory=None,
    ration=None,
    drinkers_clean=None,
    birds_under_slats=None,
    safe_indoors=None,
    safe_outdoors=None,
    equipment_functioning=None,
    predator_activity=None,
    eggs_picked_up=None,
    door_open=None,
    door_closed=None,
):
    payload = {k: v for k, v in locals().items() if v is not None}
    return _insert_into_table("Daily_User_Log", payload)


# Fetch latest record from Daily_User_Log

def get_daily_user_log(date_str=None):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    if date_str:
        cur.execute("SELECT * FROM Daily_User_Log WHERE date(date_entered) = ? ORDER BY date_entered DESC LIMIT 1", (date_str,))
    else:
        cur.execute("SELECT * FROM Daily_User_Log ORDER BY date_entered DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

# Fetch latest record from Daily_Bot_Log

def get_daily_bot_log(date_str=None):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    if date_str:
        cur.execute("SELECT * FROM Daily_Bot_Log WHERE date = ? ORDER BY date DESC LIMIT 1", (date_str,))
    else:
        cur.execute("SELECT * FROM Daily_Bot_Log ORDER BY date DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None