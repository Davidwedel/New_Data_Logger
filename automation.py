#!/usr/bin/env python3
"""
Data Logger Automation Service
Handles XML → Database automation and daily Unitas upload cleanup

Note: Primary Unitas uploads are triggered immediately via webapp when
send_to_bot checkbox is checked. This script runs a daily cleanup job
at 3 AM to catch any missed uploads.
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

# Set config directory for production deployment
# Automation service uses production config at /var/lib/datalogger/
os.environ['DATALOGGER_CONFIG_DIR'] = '/var/lib/datalogger'

sys.path.append(os.path.join(os.path.dirname(__file__), "server"))
sys.path.append(os.path.join(os.path.dirname(__file__), "server/unitas_manager"))

# Local imports
from server.config import load_config, get_flat_config, get_database_path
from server.helpers import check_all_settings_there as check_settings
import server.jobs as jobs
import server.database_helper as db
from server.xml_processing import run_xml_stuff as log_from_xml
from server.xml_processing import deleteOldFiles, do_xml_setup
import server.unitas_manager.unitas_coolerlog as coolerlog
import server.unitas_manager.unitas_production as unitas
from server.unitas_manager.unitas_helper import set_timeout as helper_set_timeout
import server.upload_queue as upload_queue


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
parser.add_argument("--CoolerLogToDB", "-CTD", action="store_true", help="Backup cooler logs → Cooler DB (one-shot)")
parser.add_argument("--NoDelete", "-ND", action="store_true", help="Don't delete old XML files")
parser.add_argument("--date", "-d", type=str, help="Specific date for Unitas upload (YYYY-MM-DD format)")
args = parser.parse_args()

# ─── Config ───
# Database path respects deployment.mode setting in config
full_config = load_config()
DB_FILE = pathlib.Path(get_database_path())
# Ensure directory exists
DB_FILE.parent.mkdir(parents=True, exist_ok=True)

config = get_flat_config()

RETRIEVE_FROM_XML_TIME = config["retrieve_from_xml_time"]
LOG_COOLER_TO_UNITAS = config["Cooler_Log_To_Unitas"]
TIMEOUT = config["Timeout"]


# ─── Init ───
db.setup_db(DB_FILE)
check_settings(config)
unitas.do_unitas_setup(config)
do_xml_setup(config)
helper_set_timeout(TIMEOUT)
coolerlog.do_coolerlog_setup(config, DB_FILE)

# Backup database on startup
db.backup_database(DB_FILE)


# ─── Upload Queue Processing ───
def process_upload_queue():
    """Process all dates in the upload queue"""
    queued_dates = upload_queue.get_queued_dates()

    if not queued_dates:
        return  # Nothing to process

    logger.info(f"Processing upload queue: {len(queued_dates)} date(s) queued")

    for date_str in queued_dates:
        try:
            logger.info(f"Processing queued upload for {date_str}")
            unitas.run_unitas_stuff(config, DB_FILE, target_date=date_str)
            # Remove from queue after successful upload
            upload_queue.remove_from_queue(date_str)
            logger.info(f"Successfully processed and removed {date_str} from queue")
        except Exception as e:
            logger.error(f"Error processing {date_str} from queue: {e}")
            # Leave it in queue to retry later
            logger.info(f"Keeping {date_str} in queue for retry")


# ─── Main Execution ───
if args.LogToDatabase:
    logger.info("Running one-shot: XML → Database")
    jobs.xml_to_sheet_job(args, DB_FILE)

elif args.CoolerLogToUnitas:
    logger.info("Running one-shot: Cooler Log → Unitas")
    coolerlog.run_coolerlog_to_unitas(DB_FILE)

elif args.CoolerLogToDB:
    logger.info("Running one-shot: Cooler Log → Backup Database")
    db.backup_cooler_logs(DB_FILE)

elif args.LogToUnitas:
    if args.date:
        logger.info(f"Running one-shot: Database → Unitas for date {args.date}")
        unitas.run_unitas_stuff(config, DB_FILE, target_date=args.date)
    else:
        logger.info("Running one-shot: Database → Unitas (all pending)")
        unitas.run_unitas_stuff(config, DB_FILE)

else:
    logger.info("Running in Forever Mode (continuous automation)")

    # ─── Scheduling ───
    schedule.every().day.at(RETRIEVE_FROM_XML_TIME).do(jobs.xml_to_sheet_job, args, DB_FILE)  # XML → DB
    schedule.every().day.at("00:05").do(db.backup_database, DB_FILE)  # Daily backup at 12:05 AM

    # Schedule cooler log backup 1 minute after XML processing
    cooler_backup_time = jobs.schedule_offset(RETRIEVE_FROM_XML_TIME, 1)
    schedule.every().day.at(cooler_backup_time).do(db.backup_cooler_logs, DB_FILE)
    logger.info(f"Cooler log backup scheduled at {cooler_backup_time}")

    # Schedule coolerlog to Unitas if enabled
    if LOG_COOLER_TO_UNITAS:
        unitas_time = jobs.schedule_offset(RETRIEVE_FROM_XML_TIME, 2)  # Two minutes after XML processing
        schedule.every().day.at(unitas_time).do(coolerlog.run_coolerlog_to_unitas, DB_FILE)
        logger.info(f"Cooler log to Unitas scheduled at {unitas_time}")

    # Schedule daily cleanup job for missed Unitas uploads (catches any failed webhook uploads)
    schedule.every().day.at("03:00").do(unitas.run_unitas_stuff, config, DB_FILE, None)
    logger.info("Daily Unitas upload cleanup scheduled at 03:00")

    # Schedule upload queue processing every minute
    schedule.every(1).minutes.do(process_upload_queue)
    logger.info("Upload queue processing scheduled every 1 minute")

    logger.info("Daily database backup scheduled at 00:05")

    try:
        # Forever loop
        while True:
            schedule.run_pending()
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Stopped by user")
