import sqlite3

def setup_db(DB_FILE):
    # Connect to database (creates file if it doesn't exist)
    conn = sqlite3.connect(DB_FILE)

    # Create a cursor object to execute SQL commands
    curr = conn.cursor()

    # Create a table
    #!!!!This needs help!!!!

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

    #pallet log table
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

    # daily userlog table
    curr.execute('''
        CREATE TABLE IF NOT EXISTS Daily_User_Log (
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

def insert_log(conn, table, **kwargs):
    """
    Insert a row into the given table.
    Pass values as keyword arguments matching the column names.
    Missing columns will be NULL.
    """
    curr = conn.cursor()

    # Extract column names and values
    columns = ", ".join(kwargs.keys())
    placeholders = ", ".join(["?"] * len(kwargs))
    values = tuple(kwargs.values())

    sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
    curr.execute(sql, values)

    conn.commit()
    return curr.lastrowid  # return the new row ID

def insert_botdailylog(timestamp, date, eggs, feed, lightson, lightsoff, water, weight, dooropen, doorclosed, insidelow, insidehigh, outsidelow, outsidehigh, coolertimeam, coolertempam, coolertimepm, coolertemppm):
# Insert some data
    conn = sqlite3.connect("database.db")

    new_log = insert_log(
        conn,
        "botdailylog",
        TimeStamp=timestamp,
        Date_Of_Data=date,
        Belt_Eggs=eggs,
        Feed_Consumption=feed,
        Lights_On=lightson,
        Lights_Off=lightsoff,
        Water_Consumption=water,
        Body_Weight=weight,
        Door_Open=doorsopen,
        Door_Closed=doorsclosed,
        Inside_Low_Temp=insidelow,
        Inside_High_Temp=insidehigh,
        Outside_Low_Temp=outsidelow,
        Outside_High_Temp=outsidehigh,
        Cooler_Time_AM=coolertimeam, 
        Cooler_Temp_AM=coolertempam,
        Cooler_Time_PM=coolertimepm,
        Cooler_Temp_PM=coolertemppm
    )

    # Close the connection
    conn.close()

