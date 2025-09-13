import sys
import logging
import time
import argparse
import os
import json
from datetime import datetime, timedelta
import pathlib

sys.path.append("pyfiles")  # path to subdirectory with py files

#local imports
from database_helper import setup_db
from xml_processing import run_xml_stuff as log_from_xml_to_db
from webapp import app as webapp


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
parser.add_argument("--LogToSheet", "-LS", action="store_true", help="Log XML → Google Sheets (one-shot)")
parser.add_argument("--LogToUnitas", "-LU", action="store_true", help="Log Google Sheets → Unitas (one-shot)")
parser.add_argument("--CoolerLogToUnitas", "-CTU", action="store_true", help="Log cooler temps → Unitas (one-shot)")
parser.add_argument("--NoDelete", "-ND", action="store_true", help="Don’t delete old XML files")
args = parser.parse_args()

#──Config───
DB_FILE = pathlib.Path(__file__).parent / "database.db"
CONFIG_FILE = pathlib.Path(__file__).parent / "secrets.json"
secrets = json.loads(CONFIG_FILE.read_text())

XML_TO_SHEET_RANGE_NAME = secrets["xml_to_sheet_range_name"]
SHEET_TO_UNITAS_RANGE_NAME = secrets["sheet_to_unitas_range_name"]
RETRIEVE_FROM_XML_TIME = secrets["retrieve_from_xml_time"]
LOG_COOLER_TO_UNITAS = secrets["Cooler_Log_To_Unitas"]
TIMEOUT = secrets["Timeout"]

checkbox_cell = "Send_To_Bot!AU3:AU3"
COOLER_LOG_TO_UNITAS_CELL_RANGE = "Send_To_Bot!AV3:BC3"

# ─── Init ───
setup_db(DB_FILE)
runstate.make_sure_exists()
sheets_setup(secrets)
setup_unitas_login(secrets)
do_unitas_setup(secrets)
do_xml_setup(secrets)
set_timeout(TIMEOUT)
coolerlog.do_coolerlog_setup(secrets, COOLER_LOG_TO_UNITAS_CELL_RANGE)
webapp.run(debug=True)


    #log_from_xml_to_db()

## Go through args to see if we are doing single run or the continuous one
if args.LogToSheet:
    valuesFromXML = run_xml_stuff()
    write_to_sheet(valuesFromXML, XML_TO_SHEET_RANGE_NAME)
    runstate.save_data("XML_TO_SHEET")

    #delete all old files, so directory doesn't fill up.
    if not args.NoDelete:
        deleteOldFiles()

elif args.CoolerLogToUnitas:
    coolerlog.run_coolerlog_to_unitas()

elif args.LogToUnitas:
    valuesToSend = read_from_sheet(SHEET_TO_UNITAS_RANGE_NAME)
    run_unitas_stuff(valuesToSend)


else:
    print(f"Running in Forever Run mode.")

    do_unitas_stuff = False
    xml_to_sheet_ran = runstate.load_data("XML_TO_SHEET")
    sheet_to_unitas_ran = runstate.load_data("SHEET_TO_PRODUCTION")

    def coolerlog_unitas():
        if(LOG_COOLER_TO_UNITAS):
            coolerlog.run_coolerlog_to_unitas()


    def reset_flags():
        """Reset daily run flags at midnight."""
        global xml_to_sheet_ran, sheet_to_unitas_ran
        xml_to_sheet_ran = False
        sheet_to_unitas_ran = False
        print("[Reset] Flags reset at midnight")

    def xml_to_sheet_job():
        """Run XML → Sheets logging once per day."""
        global xml_to_sheet_ran
        if not xml_to_sheet_ran:
            if not args.LogToUnitas:
                valuesFromXML = run_xml_stuff()
                write_to_sheet(valuesFromXML,  XML_TO_SHEET_RANGE_NAME)
                runstate.save_data("XML_TO_SHEET")
                if not args.NoDelete:
                    deleteOldFiles()
                xml_to_sheet_ran = True
                print("[XML] Logged XML → Sheets")

    def check_and_run_unitas():
        """Poll spreadsheet and run Unitas if checkbox is TRUE."""
        global xml_to_sheet_ran, sheet_to_unitas_ran
        if xml_to_sheet_ran and not sheet_to_unitas_ran and not args.LogToSheet:
            do_unitas_stuff = read_from_sheet(checkbox_cell)
            bool_value = do_unitas_stuff[0][0].upper() == 'TRUE'
            if bool_value:
                valuesToSend = read_from_sheet(SHEET_TO_UNITAS_RANGE_NAME)
                run_unitas_stuff(valuesToSend)
                sheet_to_unitas_ran = True
                print("[Unitas] Logged Sheet → Unitas")

    # ─── Scheduling ───
    schedule.every().day.at("00:00:00").do(reset_flags)      # reset daily
    schedule.every().day.at(RETRIEVE_FROM_XML_TIME).do(xml_to_sheet_job) # XML → Sheets
    schedule.every(10).seconds.do(check_and_run_unitas)      # poll spreadsheet

    # define a helper to calculate the coolerlog->unitas run time
    def schedule_offset(base_time="00:15:00", offset_minutes=15):
        h, m = map(int, base_time.split(":"))
        target = (datetime.combine(datetime.today(), datetime.min.time())
                  + timedelta(hours=h, minutes=m)
                  + timedelta(minutes=offset_minutes))
        return target.strftime("%H:%M")

    run_time = schedule_offset(RETRIEVE_FROM_XML_TIME, 1)  #one minute after
    schedule.every().day.at(run_time).do(coolerlog_unitas)

    print(f"Job scheduled at {run_time}")

    try:

        ##this is the forever loop
        while True:
            schedule.run_pending()
            time.sleep(1)

    except KeyboardInterrupt:
        print("Stopped by user")
    


