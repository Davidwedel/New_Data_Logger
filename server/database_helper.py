import sqlite3
import shutil
import pathlib
from datetime import datetime

# ------------------- DATABASE SETUP -------------------
def setup_db(db_file):
    conn = sqlite3.connect(db_file)
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
        date DATE,
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

    # Run migrations to add any missing columns
    migrate_schema(conn)

    conn.close()

def migrate_schema(conn):
    """Add missing columns to existing tables"""
    cur = conn.cursor()

    # Get current columns in Daily_User_Log
    cur.execute("PRAGMA table_info(Daily_User_Log)")
    existing_user_columns = {row[1] for row in cur.fetchall()}

    # Define expected columns for Daily_User_Log
    expected_user_columns = {
        'send_to_bot': 'INTEGER DEFAULT 0',
        'nutritionist': 'TEXT',
        'ration_used': 'TEXT',
        'sent_to_unitas_at': 'TIMESTAMP',
    }

    # Add missing columns to Daily_User_Log
    for col_name, col_def in expected_user_columns.items():
        if col_name not in existing_user_columns:
            try:
                cur.execute(f"ALTER TABLE Daily_User_Log ADD COLUMN {col_name} {col_def}")
                print(f"Added column '{col_name}' to Daily_User_Log")
            except Exception as e:
                print(f"Error adding column '{col_name}': {e}")

    # Get current columns in Daily_Bot_Log
    cur.execute("PRAGMA table_info(Daily_Bot_Log)")
    existing_bot_columns = {row[1] for row in cur.fetchall()}

    # Define expected columns for Daily_Bot_Log
    expected_bot_columns = {
        'cooler_logged_at': 'TIMESTAMP',
    }

    # Add missing columns to Daily_Bot_Log
    for col_name, col_def in expected_bot_columns.items():
        if col_name not in existing_bot_columns:
            try:
                cur.execute(f"ALTER TABLE Daily_Bot_Log ADD COLUMN {col_name} {col_def}")
                print(f"Added column '{col_name}' to Daily_Bot_Log")
            except Exception as e:
                print(f"Error adding column '{col_name}': {e}")

    conn.commit()


# ------------------- GENERIC INSERT HELPER -------------------
def _insert_into_table(db_file, table, data_dict):
    if not data_dict:
        raise ValueError("No data provided to insert.")
    cols = ", ".join(data_dict.keys())
    placeholders = ", ".join("?" for _ in data_dict)
    sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute(sql, tuple(data_dict.values()))
    conn.commit()
    lastrowid = cur.lastrowid
    conn.close()
    return lastrowid


# ------------------- INSERT FUNCTIONS -------------------

def insert_daily_bot_log(
    db_file,
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
    payload = {k: v for k, v in locals().items() if v is not None and k != 'db_file'}
    return _insert_into_table(db_file, "Daily_Bot_Log", payload)


def insert_pallet_log(
    db_file,
    thedate=None,
    pallet_id=None,
    house_id=None,
    total_pallet_weight=None,
    case_weight=None,
    flock_age=None,
    yolk_color=None,
):
    payload = {k: v for k, v in locals().items() if v is not None and k != 'db_file'}
    return _insert_into_table(db_file, "Pallet_Log", payload)


def insert_daily_user_log(
    db_file,
    date=None,
    belt_eggs=None,
    floor_eggs=None,
    mortality_indoor=None,
    mortality_outdoor=None,
    euthanized_indoor=None,
    euthanized_outdoor=None,
    depop=None,
    amount_delivered=None,
    mortality_reasons="",
    cull_reasons="",
    mortality_comments="",
    coolerlog_comments="",
    added_supplements="",
    birds_restricted_reason="",
    comments="",
    weather="",
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
    payload = {k: v for k, v in locals().items() if v is not None and k != 'db_file'}
    return _insert_into_table(db_file, "Daily_User_Log", payload)


# ------------------- FETCH FUNCTIONS -------------------

def get_daily_user_log(db_file, date_str=None):
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    if date_str:
        cur.execute("SELECT * FROM Daily_User_Log WHERE date = ? LIMIT 1", (date_str,))
    else:
        cur.execute("SELECT * FROM Daily_User_Log ORDER BY date DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_daily_bot_log(db_file, date_str=None):
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    if date_str:
        cur.execute("SELECT * FROM Daily_Bot_Log WHERE date = ? ORDER BY date DESC LIMIT 1", (date_str,))
    else:
        cur.execute("SELECT * FROM Daily_Bot_Log ORDER BY date DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_user_logs(db_file):
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM Daily_User_Log ORDER BY date DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_bot_logs(db_file):
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM Daily_Bot_Log ORDER BY date DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# ------------------- UPDATE FUNCTIONS -------------------
def update_daily_user_log(db_file, date_str, data):
    if not data:
        raise ValueError("No data provided to update.")
    set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
    sql = f"UPDATE Daily_User_Log SET {set_clause} WHERE date = ?"
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute(sql, tuple(data.values()) + (date_str,))
    conn.commit()
    conn.close()

def update_daily_bot_log(db_file, date, data):
    if not data:
        raise ValueError("No data provided to update.")
    set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
    sql = f"UPDATE Daily_Bot_Log SET {set_clause} WHERE date = ?"
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute(sql, tuple(data.values()) + (date,))
    conn.commit()
    conn.close()

# ------------------- QUERY FUNCTIONS -------------------
def get_dates_pending_unitas_upload(db_file):
    """
    Get all dates that have:
    1. send_to_bot flag set to 1
    2. NOT yet sent to Unitas (sent_to_unitas_at IS NULL)
    3. Have corresponding bot_log data
    Returns list of date strings in ISO format
    """
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()

    # Join user_log with bot_log to ensure both exist
    sql = """
        SELECT DISTINCT u.date as date_only
        FROM Daily_User_Log u
        INNER JOIN Daily_Bot_Log b ON u.date = b.date
        WHERE u.send_to_bot = 1
        AND u.sent_to_unitas_at IS NULL
        ORDER BY u.date ASC
    """

    cur.execute(sql)
    results = cur.fetchall()
    conn.close()

    return [row[0] for row in results]

# ------------------- JOB STATUS FUNCTIONS -------------------
def has_xml_been_processed_today(db_file, date_str):
    """
    Check if XML has been processed for a given date.
    Returns True if bot_log entry exists for the date.
    """
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM Daily_Bot_Log WHERE date = ? LIMIT 1", (date_str,))
    result = cur.fetchone()
    conn.close()
    return result is not None

def has_production_been_sent_today(db_file, date_str):
    """
    Check if production data has been sent to Unitas for a given date.
    Returns True if sent_to_unitas_at is not NULL for the date.
    """
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM Daily_User_Log WHERE date = ? AND sent_to_unitas_at IS NOT NULL LIMIT 1", (date_str,))
    result = cur.fetchone()
    conn.close()
    return result is not None

def has_cooler_been_logged_today(db_file, date_str):
    """
    Check if cooler log has been sent to Unitas for a given date.
    Returns True if cooler_logged_at is not NULL for the date.
    """
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM Daily_Bot_Log WHERE date = ? AND cooler_logged_at IS NOT NULL LIMIT 1", (date_str,))
    result = cur.fetchone()
    conn.close()
    return result is not None

# ------------------- DATABASE BACKUP -------------------
def backup_database(db_file, backup_dir=None):
    """
    Create a database backup if it's been more than 24 hours since last backup.

    Args:
        db_file: Path to the database file to backup
        backup_dir: Directory to store backups (default: ~/.datalogger/backups)

    Returns:
        Path to backup file if created, None if skipped
    """
    if backup_dir is None:
        backup_dir = pathlib.Path.home() / ".datalogger" / "backups"
    else:
        backup_dir = pathlib.Path(backup_dir)

    backup_dir.mkdir(parents=True, exist_ok=True)

    # Find most recent backup
    existing_backups = sorted(backup_dir.glob("database_*.db"))

    if existing_backups:
        # Get the modification time of the most recent backup
        last_backup = existing_backups[-1]
        last_backup_time = datetime.fromtimestamp(last_backup.stat().st_mtime)
        hours_since_backup = (datetime.now() - last_backup_time).total_seconds() / 3600

        if hours_since_backup < 24:
            print(f"Skipping backup - last backup was {hours_since_backup:.1f} hours ago")
            return None

    # Create new backup
    backup_file = backup_dir / f"database_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    print(f"Creating database backup at {backup_file}")
    shutil.copy2(db_file, backup_file)
    print("Database backup completed")

    return backup_file
