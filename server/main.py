import sys
import schedule
import logging
import time
import argparse
import os
import json
from datetime import datetime, timedelta
import pathlib
from helpers import check_all_settings_there as check_settings

sys.path.append(os.path.join(os.path.dirname(__file__), "unitas_manager"))

#local imports
import jobs as jobs
import runstate as runstate
import database_helper as db
from xml_processing import run_xml_stuff as log_from_xml
from xml_processing import deleteOldFiles, do_xml_setup
from webapp import app as webapp
import unitas_manager.unitas_coolerlog as coolerlog
import unitas_manager.unitas_production as unitas
from unitas_manager.unitas_helper import set_timeout as helper_set_timeout


# ─── Logging ───
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


# ─── CLI args ───
parser = argparse.ArgumentParser(
    epilog="If no args are provided, runs in Forever Mode."
)
parser.add_argument("--LogToDatabase", "-LD", action="store_true", help="Log XML → Database (one-shot)")
parser.add_argument("--LogToUnitas", "-LU", action="store_true", help="Log Database → Unitas (one-shot)")
parser.add_argument("--CoolerLogToUnitas", "-CTU", action="store_true", help="Log cooler temps → Unitas (one-shot)")
parser.add_argument("--NoDelete", "-ND", action="store_true", help="Don’t delete old XML files")
parser.add_argument("--WebApp", "-WA", action="store_true", help="Run the web application")
args = parser.parse_args()

#──Config───
DB_FILE = pathlib.Path(__file__).parent / "../database.db"
CONFIG_FILE = pathlib.Path(__file__).parent / "../secrets.json"
secrets = json.loads(CONFIG_FILE.read_text())

RETRIEVE_FROM_XML_TIME = secrets["retrieve_from_xml_time"]
LOG_COOLER_TO_UNITAS = secrets["Cooler_Log_To_Unitas"]
TIMEOUT = secrets["Timeout"]


# ─── Init ───
db.setup_db(DB_FILE)
check_settings(secrets)
runstate.make_sure_exists()
unitas.do_unitas_setup(secrets)
do_xml_setup(secrets)
helper_set_timeout(TIMEOUT)
coolerlog.do_coolerlog_setup(secrets)

## Go through args to see if we are doing single run or the continuous one
if args.WebApp:
    webapp.run(debug=True)

elif args.LogToDatabase:
    valuesFromXML = log_from_xml()
    print(valuesFromXML)

    runstate.save_data("XML_TO_DB")

    #delete all old files, so directory doesn't fill up.
    if not args.NoDelete:
        deleteOldFiles()

elif args.CoolerLogToUnitas:
    coolerlog.run_coolerlog_to_unitas()

elif args.LogToUnitas:
    unitas.run_unitas_stuff(secrets)


else :
    print(f"Running in Forever Run mode.")

    do_unitas_stuff = False
    xml_to_sheet_ran = runstate.load_data("XML_TO_DB")
    sheet_to_unitas_ran = runstate.load_data("DB_TO_PRODUCTION")
    webapp.run(debug=False)


    # ─── Scheduling ───
    schedule.every().day.at("00:00:00").do(jobs.reset_flags)      # reset daily
    schedule.every().day.at(RETRIEVE_FROM_XML_TIME).do(jobs.xml_to_sheet_job(args)) # XML → Sheets
    schedule.every(10).seconds.do(jobs.check_and_run_unitas)      # poll spreadsheet

    # define a helper to calculate the coolerlog->unitas run time
    if(LOG_COOLER_TO_UNITAS):
        run_time = jobs.schedule_offset(RETRIEVE_FROM_XML_TIME, 1)  #one minute after
        schedule.every().day.at(run_time).do(coolerlog.run_coolerlog_to_unitas)

        print(f"Job scheduled at {run_time}")

    try:

        ##this is the forever loop
        while True:
            schedule.run_pending()
            time.sleep(1)

    except KeyboardInterrupt:
        print("Stopped by user")
    


