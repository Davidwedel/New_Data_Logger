#!/usr/bin/env python3
"""
Data Logger Automation Service
Handles XML → Database and Database → Unitas automation
"""
import sys
import schedule
import logging
import time
import argparse
import os
import json
from datetime import datetime, timedelta
import pathlib

sys.path.append(os.path.join(os.path.dirname(__file__), "server"))
sys.path.append(os.path.join(os.path.dirname(__file__), "server/unitas_manager"))

# Local imports
from server.helpers import check_all_settings_there as check_settings
import server.jobs as jobs
import server.database_helper as db
from server.xml_processing import run_xml_stuff as log_from_xml
from server.xml_processing import deleteOldFiles, do_xml_setup
import server.unitas_manager.unitas_coolerlog as coolerlog
import server.unitas_manager.unitas_production as unitas
from server.unitas_manager.unitas_helper import set_timeout as helper_set_timeout


# ─── Logging ───
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


# ─── CLI args ───
parser = argparse.ArgumentParser(
    description="Data Logger Automation Service",
    epilog="If no args are provided, runs in Forever Mode."
)
parser.add_argument("--LogToDatabase", "-LD", action="store_true", help="Log XML → Database (one-shot)")
parser.add_argument("--LogToUnitas", "-LU", action="store_true", help="Log Database → Unitas (one-shot)")
parser.add_argument("--CoolerLogToUnitas", "-CTU", action="store_true", help="Log cooler temps → Unitas (one-shot)")
parser.add_argument("--NoDelete", "-ND", action="store_true", help="Don't delete old XML files")
args = parser.parse_args()

# ─── Config ───
DB_FILE = pathlib.Path(__file__).parent / "database.db"
CONFIG_FILE = pathlib.Path(__file__).parent / "secrets.json"
secrets = json.loads(CONFIG_FILE.read_text())

RETRIEVE_FROM_XML_TIME = secrets["retrieve_from_xml_time"]
LOG_COOLER_TO_UNITAS = secrets["Cooler_Log_To_Unitas"]
TIMEOUT = secrets["Timeout"]


# ─── Init ───
db.setup_db(DB_FILE)
check_settings(secrets)
unitas.do_unitas_setup(secrets)
do_xml_setup(secrets)
helper_set_timeout(TIMEOUT)
coolerlog.do_coolerlog_setup(secrets, DB_FILE)


# ─── Main Execution ───
if args.LogToDatabase:
    logger.info("Running one-shot: XML → Database")
    jobs.xml_to_sheet_job(args, DB_FILE, process_all=True)

elif args.CoolerLogToUnitas:
    logger.info("Running one-shot: Cooler Log → Unitas")
    coolerlog.run_coolerlog_to_unitas(DB_FILE)

elif args.LogToUnitas:
    logger.info("Running one-shot: Database → Unitas")
    unitas.run_unitas_stuff(secrets, DB_FILE)

else:
    logger.info("Running in Forever Mode (continuous automation)")

    # ─── Scheduling ───
    schedule.every().day.at(RETRIEVE_FROM_XML_TIME).do(jobs.xml_to_sheet_job, args, DB_FILE, True)  # XML → DB

    # Schedule coolerlog if enabled
    if LOG_COOLER_TO_UNITAS:
        run_time = jobs.schedule_offset(RETRIEVE_FROM_XML_TIME, 1)  # One minute after XML processing
        schedule.every().day.at(run_time).do(coolerlog.run_coolerlog_to_unitas, DB_FILE)
        logger.info(f"Cooler log job scheduled at {run_time}")

    try:
        # Forever loop
        while True:
            schedule.run_pending()
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Stopped by user")
