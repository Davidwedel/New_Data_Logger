#!/usr/bin/env python3
"""
XML Directory Watcher - Monitors XML directory for inactivity

This script watches the XML directory specified in config and sends
a notification if no new files are added within the check interval.
"""

import json
import os
import sys
import time
import pathlib
from datetime import datetime

# Add server directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "server"))
from server.config import get_flat_config

# Load configuration
try:
    config = get_flat_config()
    XML_DIR = config["path_to_xmls"]
except Exception as e:
    print(f"Error loading configuration: {e}")
    print("Make sure ~/.datalogger/config.json exists and is properly configured")
    exit(1)

# Configuration
CHECK_INTERVAL = 5 * 60  # Check every 5 minutes

def get_latest_file_time(directory):
    """Get the modification time of the most recently added XML file."""
    try:
        xml_files = [f for f in os.listdir(directory) if f.endswith('.xml')]
        if not xml_files:
            return None

        latest_file = max(
            [os.path.join(directory, f) for f in xml_files],
            key=os.path.getmtime
        )
        return os.path.getmtime(latest_file)
    except Exception as e:
        print(f"Error checking directory: {e}")
        return None

def send_notification(message):
    """Send a notification (currently prints to console)."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"[{timestamp}] ⚠️  ALERT: {message}")
    print(f"{'='*60}\n")

def main():
    print(f"Starting XML directory watcher...")
    print(f"Monitoring: {XML_DIR}")
    print(f"Check interval: {CHECK_INTERVAL} seconds ({CHECK_INTERVAL/60:.1f} minutes)\n")

    if not os.path.exists(XML_DIR):
        print(f"ERROR: Directory does not exist: {XML_DIR}")
        exit(1)

    last_file_time = get_latest_file_time(XML_DIR)

    if last_file_time:
        print(f"Initial check: Last file at {datetime.fromtimestamp(last_file_time).strftime('%Y-%m-%d %H:%M:%S')}\n")
    else:
        print(f"Initial check: No XML files found\n")

    while True:
        try:
            time.sleep(CHECK_INTERVAL)

            current_file_time = get_latest_file_time(XML_DIR)
            timestamp = datetime.now().strftime('%H:%M:%S')

            if current_file_time is None:
                print(f"[{timestamp}] No XML files found in directory")
                send_notification("No XML files found in directory!")
            elif current_file_time == last_file_time:
                # No new files since last check
                last_datetime = datetime.fromtimestamp(last_file_time)
                send_notification(
                    f"No new XML files in the last {CHECK_INTERVAL/60:.0f} minutes! "
                    f"Last file at {last_datetime.strftime('%H:%M:%S')}"
                )
                print(f"[{timestamp}] ⚠️  No new files since {last_datetime.strftime('%H:%M:%S')}")
            else:
                # New file detected
                new_datetime = datetime.fromtimestamp(current_file_time)
                print(f"[{timestamp}] ✓ New file detected at {new_datetime.strftime('%H:%M:%S')}")
                last_file_time = current_file_time

        except KeyboardInterrupt:
            print("\n\nWatcher stopped by user")
            break
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
