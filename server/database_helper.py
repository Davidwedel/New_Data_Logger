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
    curr.execute('''CREATE TABLE IF NOT EXISTS Data_Log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATE,
        bird_age INTEGER,
        eggs_to_minus INTEGER,
        mortality INTEGER,
        mortality_indoor INTEGER,
        mortality_outdoor INTEGER,
        euthanized_indoor INTEGER,
        euthanized_outdoor INTEGER,
        depop_number INTEGER,
        cull_reason TEXT,
        mortality_reason TEXT,
        mortality_comments TEXT,
        total_eggs INTEGER,
        belt_eggs INTEGER,
        floor_eggs INTEGER,
        nutritionist TEXT,
        ration_used TEXT,
        feed_consumption REAL,
        ration_delivered REAL,
        amount_delivered REAL,
        lights_on TIME,
        lights_off TIME,
        added_supplements TEXT,
        water_consumption REAL,
        body_weight REAL,
        case_weight REAL,
        yolk_color TEXT,
        door_open TIME,
        door_closed TIME,
        birds_restricted INTEGER,
        birds_restricted_reason TEXT,
        inside_low_temp REAL,
        inside_high_temp REAL,
        outside_low_temp REAL,
        outside_high_temp REAL,
        air_sensory TEXT,
        weather_conditions TEXT,
        outside_drinkers_clean INTEGER,
        birds_found_under_slats INTEGER,
        safe_environment_indoors INTEGER,
        safe_environment_outdoors INTEGER,
        equipment_functioning INTEGER,
        predator_activity INTEGER,
        comment TEXT,
        eggs_shipped INTEGER,
        eggs_comments TEXT,
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

def insert_data_log(
    date=None,
    bird_age=None,
    eggs_to_minus=None,
    mortality=None,
    mortality_indoor=None,
    mortality_outdoor=None,
    euthanized_indoor=None,
    euthanized_outdoor=None,
    depop_number=None,
    cull_reason=None,
    mortality_reason=None,
    mortality_comments=None,
    total_eggs=None,
    belt_eggs=None,
    floor_eggs=None,
    nutritionist=None,
    ration_used=None,
    feed_consumption=None,
    ration_delivered=None,
    amount_delivered=None,
    lights_on=None,
    lights_off=None,
    added_supplements=None,
    water_consumption=None,
    body_weight=None,
    case_weight=None,
    yolk_color=None,
    door_open=None,
    door_closed=None,
    birds_restricted=None,
    birds_restricted_reason=None,
    inside_low_temp=None,
    inside_high_temp=None,
    outside_low_temp=None,
    outside_high_temp=None,
    air_sensory=None,
    weather_conditions=None,
    outside_drinkers_clean=None,
    birds_found_under_slats=None,
    safe_environment_indoors=None,
    safe_environment_outdoors=None,
    equipment_functioning=None,
    predator_activity=None,
    comment=None,
    eggs_shipped=None,
    eggs_comments=None,
    cooler_time_am=None,
    cooler_temp_am=None,
    cooler_time_pm=None,
    cooler_temp_pm=None,
):
    payload = {k: v for k, v in locals().items() if v is not None}
    return _insert_into_table("Data_Log", payload)


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
