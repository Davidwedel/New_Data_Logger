import shutil
import requests
import glob
import os
import xml.etree.ElementTree as ET
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
from collections import Counter
from dataclasses import dataclass
from typing import Union
import database_helper
from helpers import get_bird_age
from config import get_corrupt_files_dir

@dataclass
class TemperatureAndLightData:
    """Data extracted from processing all XML files for a day"""
    outside_high: float
    outside_low: float
    inside_high: float
    inside_low: float
    light_on_time: str
    light_off_time: str

@dataclass
class DailyTotalsData:
    """Daily totals extracted from the last XML file of the day"""
    mortality: int
    feed_consumption: float
    water_consumption: int
    avg_weight: float

@dataclass
class CoolerTempData:
    """Cooler temperature at a specific time"""
    time: str
    temperature: Union[float, str]  # Can be float or '=NA()'

@dataclass
class CorruptionReport:
    """Track corrupt/invalid files encountered during processing"""
    files_skipped: list  # [(filename, reason), ...]
    files_moved: list    # [(filename, reason), ...]

    def add_skipped(self, filename: str, reason: str):
        """Record a file that was skipped but not moved"""
        self.files_skipped.append((filename, reason))

    def add_moved(self, filename: str, reason: str):
        """Record a file that was moved to failed_dir"""
        self.files_moved.append((filename, reason))

    def has_issues(self) -> bool:
        """Return True if any files had problems"""
        return len(self.files_skipped) > 0 or len(self.files_moved) > 0

    def print_report(self):
        """Print summary of all corruption issues"""
        if not self.has_issues():
            print("No corrupt or invalid files detected")
            return

        print("\n" + "="*60)
        print("CORRUPTION REPORT")
        print("="*60)

        if self.files_moved:
            print(f"\nMoved to corrupt_files/ ({len(self.files_moved)} files):")
            for filename, reason in self.files_moved:
                print(f"  - {os.path.basename(filename)}: {reason}")

        if self.files_skipped:
            print(f"\nSkipped ({len(self.files_skipped)} files):")
            for filename, reason in self.files_skipped:
                print(f"  - {os.path.basename(filename)}: {reason}")

        print("="*60 + "\n")

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

def extract_daily_temperature_and_light_data(file_list, corruption_report=None):
    """
    Extract temperature ranges and light on/off times from a day's XML files.

    Args:
        file_list: List of XML file paths to process
        corruption_report: Optional CorruptionReport to track moved files

    Returns:
        TemperatureAndLightData: Dataclass containing:
            - outside_high/low: Max/min outside temperatures (Celsius)
            - inside_high/low: Max/min inside temperatures (Celsius)
            - light_on_time: Time lights turned on (HH:MM)
            - light_off_time: Time lights turned off (HH:MM)

    Raises:
        ValueError: If no valid temperature data found

    Note: Files are sorted by internal <General><Time> field, not filename.
          Files with invalid Time (-9999) are skipped.
          Corrupt files are moved to failed_dir.
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
            # Move corrupt file out of the way
            shutil.move(filename, dst)
            if corruption_report:
                corruption_report.add_moved(filename, f"XML parse error: {e}")

    ## verify that our light data is good 
    if lightStatus is True:
        print("LightStatus Failure. Light was on in last file")

    elif lightFlag != 100000:
        print("lightFlag failed")
        print("LightFlag: ", lightFlag)

    ## end of verify light data

    if outsideTemps:
        outsideHigh = max(outsideTemps)
        outsideLow = min(outsideTemps)
    else:
        print(f"ERROR: No valid outside temperature data found")
        raise ValueError("No valid outside temperature data in XML files")

    if insideTemps:
        insideHigh = max(insideTemps)
        insideLow = min(insideTemps)
    else:
        print(f"ERROR: No valid inside temperature data found")
        raise ValueError("No valid inside temperature data in XML files")

    return TemperatureAndLightData(
        outside_high=outsideHigh,
        outside_low=outsideLow,
        inside_high=insideHigh,
        inside_low=insideLow,
        light_on_time=lightOnTime,
        light_off_time=lightOffTime
    )
   
def extract_daily_totals_from_last_file(last_file_path, corruption_report=None):
        """
        Extract daily totals from the last XML file of the day.

        Args:
            last_file_path: Path to the last XML file of the day
            corruption_report: Optional CorruptionReport to track moved files

        Returns:
            DailyTotalsData: Dataclass containing:
                - mortality: Total daily female mortality count
                - feed_consumption: Daily feed consumption (kg)
                - water_consumption: Daily water consumption
                - avg_weight: Average bird weight (kg)

        Raises:
            ValueError: If required XML elements are missing
            Exception: If file cannot be parsed

        Note: Corrupt files are moved to failed_dir.
        """
        try:
            tree = ET.parse(last_file_path)
            root = tree.getroot()

            # Extract mortality
            mortality_element = root.find(".//TotalDailyFemaleMortality")
            if mortality_element is None:
                raise ValueError("TotalDailyFemaleMortality not found")
            mortality = int(mortality_element.text)

            # Extract feed consumption
            feed_element = root.find(".//DailyFeed")
            if feed_element is None:
                raise ValueError("DailyFeed not found")
            feed = int(feed_element.text)

            # Extract water consumption
            water_element = root.find(".//DailyWater")
            if water_element is None:
                raise ValueError("DailyWater not found")
            water = int(water_element.text)

            # Extract avg weight
            weight_element = root.find(".//AverageWeight")
            if weight_element is None:
                raise ValueError("AverageWeight not found")
            weight = float(weight_element.text)

            return DailyTotalsData(
                mortality=mortality,
                feed_consumption=feed,
                water_consumption=water,
                avg_weight=weight
            )

        except Exception as e:
            print(f"Failed to process {last_file_path}: {e}")
            dst = os.path.join(failed_dir, os.path.basename(last_file_path))
            # Ensure destination directory exists
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            # Move corrupt file out of the way
            shutil.move(last_file_path, dst)
            if corruption_report:
                corruption_report.add_moved(last_file_path, f"Failed to extract daily totals: {e}")
            raise  # Re-raise so caller can try fallback

def extract_daily_totals_with_fallback(sorted_files_with_time, corruption_report=None, max_attempts=3):
    """
    Try to extract daily totals from last files, with fallback.

    Args:
        sorted_files_with_time: List of (filename, time_str) tuples, sorted by time
        corruption_report: Optional CorruptionReport to track issues
        max_attempts: Maximum number of files to try (default: 3)

    Returns:
        DailyTotalsData or None if all attempts fail

    Note: Tries last file, then second-to-last, etc.
    """
    if not sorted_files_with_time:
        return None

    # Try from last to first (reverse order)
    for attempt_num in range(min(max_attempts, len(sorted_files_with_time))):
        file_index = -(attempt_num + 1)  # -1, -2, -3, ...
        file_path, file_time = sorted_files_with_time[file_index]

        attempt_label = "last" if attempt_num == 0 else f"{attempt_num+1} from last"
        print(f"Attempting to extract daily totals from {attempt_label} file (time: {file_time})")

        try:
            return extract_daily_totals_from_last_file(file_path, corruption_report)
        except Exception as e:
            if attempt_num < max_attempts - 1 and attempt_num < len(sorted_files_with_time) - 1:
                print(f"  Failed, trying next earlier file...")
            else:
                print(f"  Failed, no more files to try")
                raise  # Re-raise on final attempt

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
        return CoolerTempData(time='=NA()', temperature='=NA()')

    # Return closest file among candidates
    closest_file = min(candidates, key=lambda x: diff_minutes(x[1]))[0]

    try:
        tree = ET.parse(closest_file)
        root = tree.getroot()

        # Extract egg room temp and time
        temp_element = root.find(".//EggRoom")
        time_element = root.find(".//Time")
        if (temp_element is not None) and (time_element is not None):
            room_temp = float(temp_element.text)
            time_temp = time_element.text
            return CoolerTempData(time=time_temp, temperature=room_temp)
        else:
            return CoolerTempData(time='=NA()', temperature='=NA()')

    except Exception as e:
        print(f"Failed to process {closest_file}: {e}")
        return CoolerTempData(time='=NA()', temperature='=NA()')
            
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
    # Create corruption report to track issues
    corruption_report = CorruptionReport(files_skipped=[], files_moved=[])

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

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # GrowthDay Matching Logic
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #
    # Problem: We cannot rely solely on file timestamps (filename dates).
    #
    # Why: The farm equipment generates one XML file per hour, but:
    #   - File timestamps reflect when the file was created (UTC time)
    #   - The <GrowthDay> inside the XML reflects the farm's calendar day
    #   - Due to timezone differences, files near midnight may have:
    #     * Filename date = Day N
    #     * Internal GrowthDay = Day N+1 (or N-1)
    #
    # Example:
    #   File: 20241115230000_...xml (Nov 15, 23:00 UTC)
    #   Internal GrowthDay: 256 (which corresponds to Nov 16 local time)
    #
    # Solution:
    #   1. Use filename date to get candidate files (fast, gets most of them)
    #   2. Parse GrowthDay from each candidate to find the most common value
    #   3. Search ALL XMLs (even from other dates) for that GrowthDay
    #   4. Process only files matching the target GrowthDay
    #
    # This ensures we get a complete 24-hour day of data (all 24 files)
    # even when files span multiple filename dates.
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # Step 1: Get initial file list using filename pattern (most will be correct day)
    yesterdayFiles = os.path.join(xmlFolder, (yesterday+"*.xml"))
    candidate_files = glob.glob(yesterdayFiles)

    if not candidate_files:
        print("No files found for yesterday. Exiting...")
        return None

    # Step 2: Parse GrowthDay from candidate files to determine which GrowthDay to process
    print(f"Found {len(candidate_files)} candidate files, determining target GrowthDay...")
    growthdays = []
    skipped_count = 0
    for filename in candidate_files:
        _, growthday = extract_time_and_growthday(filename)
        if growthday is not None:
            growthdays.append(growthday)
        else:
            skipped_count += 1
            corruption_report.add_skipped(filename, "Invalid/missing GrowthDay or Time field")

    if skipped_count > 0:
        print(f"  Skipped {skipped_count} candidate files with invalid GrowthDay/Time")

    if not growthdays:
        print("ERROR: No valid GrowthDay values found in candidate files.")
        corruption_report.print_report()
        return None

    # Step 3: Find most common GrowthDay (should be 23-24 out of 24 files)
    growthday_counts = Counter(growthdays)
    target_growthday = growthday_counts.most_common(1)[0][0]
    print(f"Target GrowthDay: {target_growthday} (appears in {growthday_counts[target_growthday]}/{len(candidate_files)} candidate files)")

    # Step 4: Get ALL files from directory that match target GrowthDay
    # This catches any files with different filename dates but same GrowthDay
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

    #for the db
    now = datetime.now()
    formatted_now = now.strftime("%m-%d-%Y %H:%M:%S")

    yesterdayDate = date.today() - timedelta(days=1)
    formatted_yesterday = yesterdayDate.strftime("%m-%d-%Y")


    # Parse all files from yesterday and extract temperature and light data
    try:
        temp_light_data = extract_daily_temperature_and_light_data(xmlNameOnly, corruption_report)
        if not temp_light_data:
            raise ValueError("Failed to extract temperature and light data")

        outsideHigh = c_to_f(temp_light_data.outside_high)
        outsideLow = c_to_f(temp_light_data.outside_low)
        insideHigh = c_to_f(temp_light_data.inside_high)
        insideLow = c_to_f(temp_light_data.inside_low)
        lightOnTime = round_hhmm_to_15(temp_light_data.light_on_time)
        lightOffTime = round_hhmm_to_15(temp_light_data.light_off_time)
    except Exception as e:
        print(f"ERROR: Failed processing temperature/light data: {e}")
        raise

    # Extract daily totals from last file (with fallback to earlier files if needed)
    try:
        daily_totals = extract_daily_totals_with_fallback(files_with_time, corruption_report)
        if not daily_totals:
            raise ValueError("Failed to extract daily totals from any file")

        mortality = daily_totals.mortality
        feedConsumption = kg_to_lb(daily_totals.feed_consumption)
        waterConsumption = daily_totals.water_consumption
        avgWeight = kg_to_lb(daily_totals.avg_weight)
    except Exception as e:
        print(f"ERROR: Failed extracting daily totals: {e}")
        corruption_report.print_report()  # Show what went wrong
        raise

    # Extract cooler temperatures
    cooler_am = getCoolerTemp(getCoolerTempAM, coolerTempTimeTolerance, xmlNameOnly)
    coolerTempTimeAM = round_hhmm_to_15(cooler_am.time)
    coolerTempAM = c_to_f(cooler_am.temperature)

    cooler_pm = getCoolerTemp(getCoolerTempPM, coolerTempTimeTolerance, xmlNameOnly)
    coolerTempTimePM = round_hhmm_to_15(cooler_pm.time)
    coolerTempPM = c_to_f(cooler_pm.temperature)

    # Validation before DB insert
    file_count = len(xmlNameOnly)
    print(f"\nProcessing Summary:")
    print(f"  Files processed: {file_count}")

    if coolerTempAM == '=NA()' or coolerTempPM == '=NA()':
        print(f"  WARNING: Cooler temperatures not available (AM: {coolerTempAM}, PM: {coolerTempPM})")

    # Insert into database
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

    # Print corruption report if any issues were found
    corruption_report.print_report()

    return f"Successfully logged data for {yesterday_readable}"

