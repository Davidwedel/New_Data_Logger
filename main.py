import sys
sys.path.append("pyfiles")  # path to subdirectory with py files
import pathlib
from database_helper import setup_db

DB_FILE = pathlib.Path(__file__).parent / "database.db"

setup_db(DB_FILE)


