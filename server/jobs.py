from datetime import datetime, timedelta
from xml_processing import deleteOldFiles
from xml_processing import run_xml_stuff as log_from_xml
from xml_processing import xmlFolder
import database_helper as db
import unitas_manager.unitas_production as unitas
import glob
import os

def find_oldest_complete_day_missing_from_db(db_file):
    """
    Find the oldest day that has XML files recorded before 1:00 and after 23:00
    but doesn't have a bot_log entry in the database.
    Returns date string in YYYY-MM-DD format or None if all days are logged.
    """
    if not xmlFolder:
        return None

    # Get all XML files
    all_xmls = glob.glob(os.path.join(xmlFolder, "*.xml"))
    if not all_xmls:
        return None

    # Group files by date (YYYYMMDD from filename)
    days_with_files = {}
    for filepath in all_xmls:
        filename = os.path.basename(filepath)
        if len(filename) >= 14:
            date_str = filename[:8]  # YYYYMMDD
            time_str = filename[8:14]  # HHMMSS
            hour = int(time_str[:2])

            if date_str not in days_with_files:
                days_with_files[date_str] = {'early': False, 'late': False}

            # Check if file is before 1:00 or after 23:00
            if hour < 1:
                days_with_files[date_str]['early'] = True
            if hour >= 23:
                days_with_files[date_str]['late'] = True

    # Find complete days (has both early and late files) sorted oldest first
    complete_days = sorted([
        day for day, times in days_with_files.items()
        if times['early'] and times['late']
    ])

    # Check each complete day to see if it's in the database
    for day_yyyymmdd in complete_days:
        # Convert YYYYMMDD to YYYY-MM-DD
        date_str = f"{day_yyyymmdd[:4]}-{day_yyyymmdd[4:6]}-{day_yyyymmdd[6:8]}"

        # Check if this day is already in the database
        if not db.has_xml_been_processed_today(db_file, date_str):
            return date_str

    return None

def xml_to_sheet_job(args, db_file, process_all=False):
    """
    Run XML → DB logging for oldest unprocessed complete day.
    If process_all is True, processes all missing days until caught up.
    """
    if process_all:
        # Process all missing days
        processed_count = 0
        while True:
            oldest_missing = find_oldest_complete_day_missing_from_db(db_file)
            if not oldest_missing:
                if processed_count == 0:
                    print("[XML] All complete days already processed")
                else:
                    print(f"[XML] Finished processing {processed_count} day(s)")
                break

            print(f"[XML] Processing data for {oldest_missing}")
            if not args.LogToUnitas:
                valuesFromXML = log_from_xml(db_file, target_date=oldest_missing)
                print(valuesFromXML)
                processed_count += 1

        # Delete old files after processing all days
        if processed_count > 0 and not args.NoDelete:
            deleteOldFiles()
    else:
        # Process only the oldest missing day
        oldest_missing = find_oldest_complete_day_missing_from_db(db_file)

        if oldest_missing:
            print(f"[XML] Processing data for {oldest_missing}")
            if not args.LogToUnitas:
                valuesFromXML = log_from_xml(db_file, target_date=oldest_missing)
                print(valuesFromXML)
                if not args.NoDelete:
                    deleteOldFiles()
                print(f"[XML] Logged XML → DB for {oldest_missing}")
        else:
            print("[XML] All complete days already processed")


def schedule_offset(base_time="00:15:00", offset_minutes=15):
    h, m = map(int, base_time.split(":"))
    target = (datetime.combine(datetime.today(), datetime.min.time())
              + timedelta(hours=h, minutes=m)
              + timedelta(minutes=offset_minutes))
    return target.strftime("%H:%M")

