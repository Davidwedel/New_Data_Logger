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


def schedule_offset(base_time="00:15:00", offset_minutes=15):
    h, m = map(int, base_time.split(":"))
    target = (datetime.combine(datetime.today(), datetime.min.time())
              + timedelta(hours=h, minutes=m)
              + timedelta(minutes=offset_minutes))
    return target.strftime("%H:%M")

