from datetime import datetime, timedelta
from xml_processing import deleteOldFiles
from xml_processing import run_xml_stuff as log_from_xml
import runstate as runstate
import unitas_manager.unitas_production as unitas
def reset_flags():
    """Reset daily run flags at midnight."""
    global xml_to_sheet_ran, sheet_to_unitas_ran
    xml_to_sheet_ran = False
    sheet_to_unitas_ran = False
    print("[Reset] Flags reset at midnight")

def xml_to_sheet_job(args):
    """Run XML → Sheets logging once per day."""
    have_we_ran = runstate.load_data("XML_TO_DB")
    if not have_we_ran:
        if not args.LogToUnitas:
            valuesFromXML = log_from_xml()
            print(valuesFromXML)
            runstate.save_data("XML_TO_DB")
            if not args.NoDelete:
                deleteOldFiles()
            print("[XML] Logged XML → DB")

def check_and_run_unitas(secrets):
    """Poll spreadsheet and run Unitas if checkbox is TRUE."""
    global xml_to_sheet_ran, sheet_to_unitas_ran
    if xml_to_sheet_ran and not sheet_to_unitas_ran and not args.LogToSheet:
        do_unitas_stuff = read_from_sheet(checkbox_cell)
        bool_value = do_unitas_stuff[0][0].upper() == 'TRUE'
        if bool_value:
            unitas.run_unitas_stuff(secrets)
            print("[Unitas] Logged DB → Unitas")


def schedule_offset(base_time="00:15:00", offset_minutes=15):
    h, m = map(int, base_time.split(":"))
    target = (datetime.combine(datetime.today(), datetime.min.time())
              + timedelta(hours=h, minutes=m)
              + timedelta(minutes=offset_minutes))
    return target.strftime("%H:%M")

