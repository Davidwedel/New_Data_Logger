"""
Configuration management for datalogger
Loads config from ~/.datalogger/config.json
"""
import json
import pathlib
from typing import Any, Dict

CONFIG_DIR = pathlib.Path.home() / ".datalogger"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "farm": {
        "hatch_date": "2025-03-05",
        "birds_arrived_date": "2025-06-01",
        "nws_station_id": "KMPR"
    },
    "unitas": {
        "username": "",
        "password": "",
        "farm_id": "",
        "house_id": "",
        "cooler_log_enabled": True,
        "cooler_log_initials": ""
    },
    "xml": {
        "path": "/srv/ftp/upload/",
        "retention_days": 2,
        "retrieve_time": "00:15"
    },
    "cooler": {
        "am_time": "06:00:00",
        "pm_time": "18:00:00",
        "time_tolerance": "00:30"
    },
    "system": {
        "time_zone": "America/Chicago",
        "timeout": 30
    },
    "telegram": {
        "bot_token": "",
        "chat_id": ""
    },
    "legacy": {
        "spreadsheet_id": "",
        "xml_to_sheet_range_name": "Nightly_Bot_Responses!A3",
        "sheet_to_unitas_range_name": "Send_To_Bot!D3:AU3"
    },
    "form_defaults": {
        "air_sensory": 1,
        "added_supplements": "",
        "door_open": "08:45",
        "door_closed": "20:50",
        "birds_restricted_reason": "",
        "drinkers_clean": "Yes",
        "safe_indoors": "Yes",
        "safe_outdoors": "Yes",
        "equipment_functioning": "Yes"
    }
}


def ensure_config_exists():
    """Create config file with defaults if it doesn't exist"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_FILE.exists():
        print(f"Creating default config at {CONFIG_FILE}")
        print("Please edit this file with your settings.")
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2))
        return False
    return True


def load_config() -> Dict[str, Any]:
    """Load configuration from file"""
    if not ensure_config_exists():
        raise RuntimeError(
            f"Config file created at {CONFIG_FILE}. "
            "Please edit it with your settings and run again."
        )

    try:
        config = json.loads(CONFIG_FILE.read_text())

        # Auto-migrate: add missing sections from DEFAULT_CONFIG
        needs_save = False
        for section, defaults in DEFAULT_CONFIG.items():
            if section not in config:
                config[section] = defaults
                needs_save = True
                print(f"Added missing config section: {section}")
            elif isinstance(defaults, dict):
                # Add missing keys within existing sections
                for key, default_value in defaults.items():
                    if key not in config[section]:
                        config[section][key] = default_value
                        needs_save = True
                        print(f"Added missing config key: {section}.{key}")

        # Save if we added anything
        if needs_save:
            save_config(config)
            print(f"Config auto-migrated and saved to {CONFIG_FILE}")

        return config
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in config file {CONFIG_FILE}: {e}")


def save_config(config: Dict[str, Any]):
    """Save configuration to file"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_flat_config() -> Dict[str, Any]:
    """
    Get config in legacy flat format for backwards compatibility.
    Maps new sectioned config to old flat keys.
    """
    config = load_config()

    flat = {}

    # Farm settings
    flat["hatch_date"] = config["farm"]["hatch_date"]
    flat["birds_arrived_date"] = config["farm"]["birds_arrived_date"]
    flat["nws_station_id"] = config["farm"]["nws_station_id"]

    # Unitas settings
    flat["Unitas_Username"] = config["unitas"]["username"]
    flat["Unitas_Password"] = config["unitas"]["password"]
    flat["Farm_ID"] = config["unitas"]["farm_id"]
    flat["House_ID"] = config["unitas"]["house_id"]
    flat["Cooler_Log_To_Unitas"] = config["unitas"]["cooler_log_enabled"]
    flat["Cooler_Log_Initials"] = config["unitas"]["cooler_log_initials"]

    # XML settings
    flat["path_to_xmls"] = config["xml"]["path"]
    flat["how_long_to_save_old_files"] = config["xml"]["retention_days"]
    flat["retrieve_from_xml_time"] = config["xml"]["retrieve_time"]

    # Cooler settings
    flat["get_cooler_temp_AM"] = config["cooler"]["am_time"]
    flat["get_cooler_temp_PM"] = config["cooler"]["pm_time"]
    flat["cooler_temp_time_tolerance"] = config["cooler"]["time_tolerance"]

    # System settings
    flat["time_zone"] = config["system"]["time_zone"]
    flat["Timeout"] = str(config["system"]["timeout"])

    # Legacy settings
    flat["spreadsheet_id"] = config["legacy"]["spreadsheet_id"]
    flat["xml_to_sheet_range_name"] = config["legacy"]["xml_to_sheet_range_name"]
    flat["sheet_to_unitas_range_name"] = config["legacy"]["sheet_to_unitas_range_name"]

    return flat
