import shutil
import requests
import glob
import os
import xml.etree.ElementTree as ET
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
from database_helper import insert_daily_bot_log as log_to_db
from helpers import get_bird_age

# Shared variables for all functions
xmlFolder = None
failed_dir = "../corrupt_files"
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

def c_to_f(celsius):
    if celsius == "=NA()":
        return "=NA()"
    return (celsius * 9/5) + 32

def kg_to_lb(kg):
    return kg * 2.20462

def doProcessingOnAllFiles(yesterdayFiles):
    lightStatus = False
    lightOnTime = "=NA()"
    lightOffTime = "=NA()"
    lightFlag = 0
    outsideTemps = []
    insideTemps = []

    def extract_timestamp(filename):
        # Assumes filenames like: 20250722225053_...
        base = os.path.basename(filename)
        return base.split('_')[0]  # '20250722225053'

    for filename in sorted(glob.glob(yesterdayFiles), key=extract_timestamp):
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

    def diff_minutes(hm):
        h, m = hm
        total = h * 60 + m
        return abs(total - target_total_minutes)


    target_total_minutes = grab_hr_min_frm_var(theTime)
    theTolerance = grab_hr_min_frm_var(theTolerance)

    # Filter files within tolerance
    candidates = [f for f in theName if diff_minutes(extract_hour_min_from_filename(f)) <= theTolerance]

    if not candidates:
        return '=NA()', '=NA()'

    # Return closest file among candidates
    closest_file = min(candidates, key=lambda f: diff_minutes(extract_hour_min_from_filename(f)))

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
    global coolerTempTimeTolerance, time_zone

    xmlFolder = secrets["path_to_xmls"]
    howLongToSaveOldFiles = secrets["how_long_to_save_old_files"]
    getCoolerTempAM = secrets["get_cooler_temp_AM"]
    getCoolerTempPM = secrets["get_cooler_temp_PM"]
    coolerTempTimeTolerance = secrets["cooler_temp_time_tolerance"]
    time_zone = secrets["time_zone"]
def run_xml_stuff():
    databack = []
    #start figuring various things we need to know

    #get yesterday's date, as formatted in the xml filename I.E. YYYYMMDD(20250722)
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y%m%d")

    #file pattern to yesterday's files
    yesterdayFiles = os.path.join(xmlFolder, (yesterday+"*.xml"))

    xmlNameOnly = glob.glob(yesterdayFiles)

    if xmlNameOnly:
        last_yesterdayFile = max(xmlNameOnly, key=lambda f: datetime.strptime(os.path.basename(f)[:14], "%Y%m%d%H%M%S"))
    else:
        print("No files found for yesterday. Exiting...")
        return None

    #end figuring various things we need to know

    #for the spreadsheet
    now = datetime.now()
    formatted_now = now.strftime("%m-%d-%Y %H:%M:%S")

    yesterdayDate = date.today() - timedelta(days=1)
    formatted_yesterday = yesterdayDate.strftime("%m-%d-%Y")


    #parse all files from yesterday and average the outside temp
    #return outsideHigh, outsideLow, insideHigh, insideLow !!What gets returned!!
    databack = doProcessingOnAllFiles(yesterdayFiles)

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

    log_to_db(
        date=(date.today() - timedelta(days=1)).isoformat(),
        bird_age=get_bird_age(),  # set if available
        feed_consumption=feedConsumption,
        lights_on=lightOnTime,
        lights_off=lightOffTime,
        water_consumption=waterConsumption,
        body_weight=avgWeight,
        case_weight=None,  # set if available
        yolk_color=None,  # set if available
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

