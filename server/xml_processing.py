import shutil
import requests
import glob
import os
import xml.etree.ElementTree as ET
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
from collections import Counter
import database_helper
from helpers import get_bird_age
from config import get_corrupt_files_dir

# Shared variables for all functions
xmlFolder = None
failed_dir = None
howLongToSaveOldFiles = None
getCoolerTempAM = None
getCoolerTempPM = None
coolerTempTimeTolerance = None
time_zone = None

def round_hhmm_to_15(s: str) -> str:
    # deal with Not available strings
    if s == "=NA()":
        return "=NA()"
    h, m = map(int, s.split(":"))
    total = h * 60 + m
    rounded = round(total / 15) * 15
    rounded %= 24 * 60                     # wrap past midnight
    return f"{rounded // 60:02d}:{rounded % 60:02d}"



def grab_hr_min_frm_var(timevar):
    var = timevar.strip().split(":")
    target_hr = int(var[0])
    target_min = int(var[1])
    target_total_min = target_hr * 60 + target_min
    return target_total_min

def extract_hour_min_from_filename(filename):
    timestamp_str = filename.split('_')[0]
    time_part = timestamp_str[-6:]
    hour = int(time_part[0:2])
    minute = int(time_part[2:4])
    return hour, minute

def extract_time_and_growthday(filename):
    """
    Extract Time and GrowthDay from XML file.
    Returns: (time_str, growthday_int) or (None, None) if invalid/missing

    time_str format: "HH:MM" (e.g., "23:45")
    growthday_int: integer day number (e.g., 256)

    Returns (None, None) if Time or GrowthDay is -9999 or cannot be parsed
    """
    try:
        tree = ET.parse(filename)
        root = tree.getroot()

        # Extract Time from <General><Time>
        time_element = root.find(".//General/Time")
        if time_element is None or time_element.text == "-9999":
            return None, None
        time_str = time_element.text.strip()

        # Extract GrowthDay from <General><GrowthDay>
        growthday_element = root.find(".//General/GrowthDay")
        if growthday_element is None or growthday_element.text == "-9999":
            return None, None
        growthday_int = int(growthday_element.text)

        return time_str, growthday_int

    except Exception as e:
        print(f"Failed to extract time/growthday from {filename}: {e}")
        return None, None

def c_to_f(celsius):
    if celsius == "=NA()":
        return "=NA()"
    return (celsius * 9/5) + 32

def kg_to_lb(kg):
    return kg * 2.20462

def doProcessingOnAllFiles(file_list):
    """
    Process all files in the provided list (not a glob pattern).
    Files are sorted by internal <General><Time> field.
    Files with invalid Time (-9999) are skipped.
    """
    lightStatus = False
    lightOnTime = "=NA()"
    lightOffTime = "=NA()"
    lightFlag = 0
    outsideTemps = []
    insideTemps = []

    # Sort files by internal Time field
    files_with_time = []
    for filename in file_list:
        time_str, _ = extract_time_and_growthday(filename)
        if time_str is not None:  # Skip files with Time == -9999
            files_with_time.append((filename, time_str))

    # Sort by time string (HH:MM format sorts correctly)
    files_with_time.sort(key=lambda x: x[1])

    for filename, _ in files_with_time:
        try: 
            tree = ET.parse(filename)
            root = tree.getroot()

            ##outside temp stuff
            temp_element = root.find(".//OutsideTemperature")
            if temp_element is not None:
                temp = float(temp_element.text)
                ## -9999 is bogus data
                if temp != -9999:
                    outsideTemps.append(temp)
                
            ##inside temp stuff
            temp_element = root.find(".//AverageTemperature")
            if temp_element is not None:
                temp = float(temp_element.text)
                ## -9999 is bogus data
                if temp != -9999:
                    insideTemps.append(temp)

            ## Light on and off calcs
            ## 99999 means a failure, 100000 means total success, so no reason 
            ## to continue calculations
            if lightFlag < 99999:

                ##light processing stuff
                light = root.find(".//Light")

                def grabTime():
                    tm = root.find(".//Headers/TimeStamp").text
                    tm = datetime.strptime(tm, "%Y/%m/%d %H:%M:%S").replace(tzinfo=ZoneInfo("UTC"))

                    # Convert to local time (e.g., America/Chicago)
                    tm_local = tm.astimezone(ZoneInfo(time_zone))
                    tm_local = tm_local.strftime("%H:%M")

                    return tm_local

                if light is not None:
                    active_text = light.findtext("Active")
                    if active_text is not None:
                        #print("found active")
                        active = int(active_text)
                    else:
                        print("fail")
                        print(active)

                    ## first file of the day shows light was already on, so we 
                    ## don't kow when it was turned on. 
                    if lightFlag == 0 and active != 0:
                        lightFlag = 99999
                        print("First file showed light on. Error")
                    
                    ##light turned on in this file
                    elif active > 0  and lightStatus is False:
                        lightStatus = True
                        lightOnTime = grabTime()

                    ## light went off this file
                    elif active == 0 and lightStatus is True:
                        lightStatus = False
                        lightOffTime = grabTime()
                        lightFlag = 100000

                    #just advance the counter
                    else:
                        lightFlag = lightFlag + 1

                    

                else:
                    print("Light element not found in XML file ", filename)

            ## end of light on and off calcs

        except Exception as e:
            print(f"Failed to process {filename}: {e}")
            dst = os.path.join(failed_dir, os.path.basename(filename))
            # Ensure destination directory exists
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            ## get it out so it doens't cause any more trouble
            shutil.move(filename, dst)

    ## verify that our light data is good 
    if lightStatus is True:
        print("LightStatus Failure. Light was on in last file")

    elif lightFlag != 100000:
        print("lightFlag failed")
        print("LightFlag: ", lightFlag)

    ## end of verify light data

    if outsideTemps:
        outsideHigh = max(outsideTemps)
        outsideLow = min (outsideTemps)

    else:
        print(f"Something failed in Outside Temps!")

    if insideTemps:
        insideHigh = max(insideTemps)
        insideLow = min (insideTemps)

    else:
        print(f"Something failed in Inside! Temps")

    return outsideHigh, outsideLow, insideHigh, insideLow, lightOnTime, lightOffTime
   
def everythingfromlastfile(last_yesterdayFile):
        datawesendback = []
        try: 
            tree = ET.parse(last_yesterdayFile)
            root = tree.getroot()

            ##mortality stuff
            temp_element = root.find(".//TotalDailyFemaleMortality")
            if temp_element is not None:
                temp = int(temp_element.text)
                datawesendback.append(temp)
                
            ##feed consumption stuff
            temp_element = root.find(".//DailyFeed")
            if temp_element is not None:
                temp = int(temp_element.text)
                datawesendback.append(temp)

            ##water consumption stuff
            temp_element = root.find(".//DailyWater")
            if temp_element is not None:
                temp = int(temp_element.text)
                datawesendback.append(temp)
                
            ##avg weight stuff
            temp_element = root.find(".//AverageWeight")
            if temp_element is not None:
                temp = float(temp_element.text)
                datawesendback.append(temp)

            return datawesendback
                
        except Exception as e:
            print(f"Failed to process {last_yesterdayFile}: {e}")
            dst = os.path.join(failed_dir, last_yesterdayFile)
            ## get it out so it doens't cause any more trouble
            shutil.move(last_yesterdayFile, dst)

def deleteOldFiles():
    #print(f"howlong {howLongToSaveOldFiles}")
    if howLongToSaveOldFiles == 0:
        print("File Deletion shut off!")
    else:
       howManyDeleted = 0
       day2Delete = (date.today() - timedelta(days=howLongToSaveOldFiles)).strftime("%Y%m%d")
       print(f"Deleting files from day {day2Delete}!")
       for filename in os.listdir(xmlFolder):
           if filename.endswith(".xml") and filename[:8] <= day2Delete:
               howManyDeleted = howManyDeleted + 1
               filepath = os.path.join(xmlFolder, filename)
               #print(f"Deleting: {filepath}")
               os.remove(filepath)

       print(f"Deleted {howManyDeleted} XML files!")

def getCoolerTemp(theTime, theTolerance, theName):
    """
    Find file closest to target time using internal <General><Time> field.
    theName: list of file paths
    """
    def time_to_minutes(time_str):
        """Convert HH:MM string to total minutes"""
        h, m = map(int, time_str.split(':'))
        return h * 60 + m

    def diff_minutes(time_str):
        """Calculate difference in minutes from target time"""
        if time_str is None:
            return float('inf')
        total = time_to_minutes(time_str)
        return abs(total - target_total_minutes)

    target_total_minutes = grab_hr_min_frm_var(theTime)
    theTolerance = grab_hr_min_frm_var(theTolerance)

    # Extract time from each file and filter within tolerance
    candidates = []
    for f in theName:
        time_str, _ = extract_time_and_growthday(f)
        if time_str is not None and diff_minutes(time_str) <= theTolerance:
            candidates.append((f, time_str))

    if not candidates:
        return '=NA()', '=NA()'

    # Return closest file among candidates
    closest_file = min(candidates, key=lambda x: diff_minutes(x[1]))[0]

    try: 
        tree = ET.parse(closest_file)
        root = tree.getroot()

        ##egg room temp stuff
        temp_element = root.find(".//EggRoom")
        temp_element1 = root.find(".//Time")
        if (temp_element is not None) and (temp_element1 is not None):
            room_temp = float(temp_element.text)
            time_temp = temp_element1.text
            return time_temp, room_temp
            
        else:
            return '=NA()', '=NA()'


    except Exception as e:
        print(f"Failed to process {closest_file}: {e}")
            
def do_xml_setup(secrets):

    global xmlFolder, howLongToSaveOldFiles, getCoolerTempAM, getCoolerTempPM
    global coolerTempTimeTolerance, time_zone, failed_dir

    xmlFolder = secrets["path_to_xmls"]
    howLongToSaveOldFiles = secrets["how_long_to_save_old_files"]
    getCoolerTempAM = secrets["get_cooler_temp_AM"]
    getCoolerTempPM = secrets["get_cooler_temp_PM"]
    coolerTempTimeTolerance = secrets["cooler_temp_time_tolerance"]
    time_zone = secrets["time_zone"]
    failed_dir = get_corrupt_files_dir()
def run_xml_stuff(db_file=None, target_date=None):
    """
    Process XML files and insert into database.
    If target_date is provided (YYYY-MM-DD format), process that date.
    Otherwise, process yesterday's date.
    """
    databack = []

    # Determine which date to process
    if target_date:
        # Convert YYYY-MM-DD to YYYYMMDD
        process_date = datetime.strptime(target_date, "%Y-%m-%d")
        yesterday = process_date.strftime("%Y%m%d")
        yesterday_readable = target_date
    else:
        # Default to yesterday
        yesterday = (date.today() - timedelta(days=1)).strftime("%Y%m%d")
        yesterday_readable = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"Processing XML files for date: {yesterday_readable}")

    # Step 1: Get initial file list using filename pattern (most will be correct day)
    yesterdayFiles = os.path.join(xmlFolder, (yesterday+"*.xml"))
    candidate_files = glob.glob(yesterdayFiles)

    if not candidate_files:
        print("No files found for yesterday. Exiting...")
        return None

    # Step 2: Parse GrowthDay from candidate files to determine which GrowthDay to process
    print(f"Found {len(candidate_files)} candidate files, determining target GrowthDay...")
    growthdays = []
    for filename in candidate_files:
        _, growthday = extract_time_and_growthday(filename)
        if growthday is not None:
            growthdays.append(growthday)

    if not growthdays:
        print("No valid GrowthDay values found in candidate files. Exiting...")
        return None

    # Step 3: Find most common GrowthDay (should be 23-24 out of 24 files)
    growthday_counts = Counter(growthdays)
    target_growthday = growthday_counts.most_common(1)[0][0]
    print(f"Target GrowthDay: {target_growthday} (appears in {growthday_counts[target_growthday]}/{len(candidate_files)} candidate files)")

    # Step 4: Get ALL files from directory that match target GrowthDay
    all_xml_files = glob.glob(os.path.join(xmlFolder, "*.xml"))
    xmlNameOnly = []
    for filename in all_xml_files:
        _, growthday = extract_time_and_growthday(filename)
        if growthday == target_growthday:
            xmlNameOnly.append(filename)

    print(f"Processing {len(xmlNameOnly)} files with GrowthDay {target_growthday}")

    if not xmlNameOnly:
        print("No files found with target GrowthDay. Exiting...")
        return None

    # Step 5: Find last file by internal Time value (not filename)
    files_with_time = []
    for filename in xmlNameOnly:
        time_str, _ = extract_time_and_growthday(filename)
        if time_str is not None:
            files_with_time.append((filename, time_str))

    if not files_with_time:
        print("No files with valid Time found. Exiting...")
        return None

    # Sort by time string (HH:MM format sorts correctly as strings)
    files_with_time.sort(key=lambda x: x[1])
    last_yesterdayFile = files_with_time[-1][0]
    print(f"Last file time: {files_with_time[-1][1]}")

    #end figuring various things we need to know

    #for the spreadsheet
    now = datetime.now()
    formatted_now = now.strftime("%m-%d-%Y %H:%M:%S")

    yesterdayDate = date.today() - timedelta(days=1)
    formatted_yesterday = yesterdayDate.strftime("%m-%d-%Y")


    #parse all files from yesterday and average the outside temp
    #return outsideHigh, outsideLow, insideHigh, insideLow !!What gets returned!!
    databack = doProcessingOnAllFiles(xmlNameOnly)

    outsideHigh = c_to_f(databack[0])
    outsideLow = c_to_f(databack[1])
    insideHigh = c_to_f(databack[2])
    insideLow = c_to_f(databack[3])
    lightOnTime = round_hhmm_to_15(databack[4])
    lightOffTime = round_hhmm_to_15(databack[5])

    #returns mortality, feed consumption, water consumption, average weight
    databack = everythingfromlastfile(last_yesterdayFile)

    mortality = databack[0]
    feedConsumption = kg_to_lb(databack[1])
    waterConsumption = databack[2]
    avgWeight = kg_to_lb(databack[3])

    t = getCoolerTemp(getCoolerTempAM, coolerTempTimeTolerance, xmlNameOnly)
    coolerTempTimeAM = round_hhmm_to_15(t[0])
    coolerTempAM = c_to_f(t[1])

    t = getCoolerTemp(getCoolerTempPM, coolerTempTimeTolerance, xmlNameOnly)
    coolerTempTimePM = round_hhmm_to_15(t[0])
    coolerTempPM = c_to_f(t[1])

    # null values may be added at a later date.

    database_helper.insert_daily_bot_log(
        db_file,
        date=yesterday_readable,
        bird_age=get_bird_age(yesterday_readable),  # Calculate age for yesterday's data
        feed_consumption=feedConsumption,
        lights_on=lightOnTime,
        lights_off=lightOffTime,
        water_consumption=waterConsumption,
        body_weight=avgWeight,
        door_open=None,
        door_closed=None,
        birds_restricted=None,
        inside_low_temp=insideLow,
        inside_high_temp=insideHigh,
        outside_low_temp=outsideLow,
        outside_high_temp=outsideHigh,
        cooler_time_am=coolerTempTimeAM,
        cooler_temp_am=coolerTempAM,
        cooler_time_pm=coolerTempTimePM,
        cooler_temp_pm=coolerTempPM
    )

    return f"Successfully logged data for {yesterday_readable}"

