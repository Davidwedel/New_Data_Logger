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

    


