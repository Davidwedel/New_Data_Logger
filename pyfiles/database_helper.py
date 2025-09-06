import sqlite3

def setup_db(DB_FILE):
    # Connect to database (creates file if it doesn't exist)
    conn = sqlite3.connect(DB_FILE)

    # Create a cursor object to execute SQL commands
    cur = conn.cursor()

    # Create a table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS botdailylog (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        TimeStamp TEXT,
        Date_Of_Data TEXT,
        Belt_Eggs INTEGER,
        Feed_Consumption REAL,
        Lights_On TEXT,
        Lights_Off TEXT,
        Water_Consumption REAL,
        Body_Weight REAL,
        Door_Open TEXT,
        Door_Closed TEXT,
        Inside_Low_Temp REAL,
        Inside_High_Temp REAL,
        Outside_Low_Temp REAL,
        Outside_High_Temp REAL,
        Cooler_Time_AM TEXT, 
        Cooler_Temp_AM REAL,
        Cooler_Time_PM TEXT,
        Cooler_Temp_PM REAL
    )
                """)
    conn.commit()

def insert_log(conn, table, **kwargs):
    """
    Insert a row into the given table.
    Pass values as keyword arguments matching the column names.
    Missing columns will be NULL.
    """
    cur = conn.cursor()

    # Extract column names and values
    columns = ", ".join(kwargs.keys())
    placeholders = ", ".join(["?"] * len(kwargs))
    values = tuple(kwargs.values())

    sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
    cur.execute(sql, values)

    conn.commit()
    return cur.lastrowid  # return the new row ID

def insert_botdailylog():
# Insert some data
    conn = sqlite3.connect("database.db")

    new_log = insert_log(
        conn,
        "botdailylog",
        TimeStamp=timestamp,
        Date_Of_Data=date,
        Belt_Eggs=INTEGER,
        Feed_Consumption=feed,
        Lights_On=TEXT,
        Lights_Off=TEXT,
        Water_Consumption=REAL,
        Body_Weight=REAL,
        Door_Open=TEXT,
        Door_Closed=TEXT,
        Inside_Low_Temp=REAL,
        Inside_High_Temp=REAL,
        Outside_Low_Temp=REAL,
        Outside_High_Temp=REAL,
        Cooler_Time_AM=TEXT, 
        Cooler_Temp_AM=REAL,
        Cooler_Time_PM=TEXT,
        Cooler_Temp_PM=REAL
    )

    # Close the connection
    conn.close()

