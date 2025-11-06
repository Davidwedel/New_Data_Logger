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
import telebot

# Set config directory for production deployment
# XML watcher service uses production config at /var/lib/datalogger/
os.environ['DATALOGGER_CONFIG_DIR'] = '/var/lib/datalogger'

# Add server directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "server"))
from server.config import load_config

# Load configuration
try:
    config = load_config()
    XML_DIR = config["xml"]["path"]
    TELEGRAM_BOT_TOKEN = config["telegram"].get("bot_token", "")
    TELEGRAM_CHAT_ID = config["telegram"].get("chat_id", "")

    # Initialize Telegram bot if configured
    telegram_bot = None
    if telebot and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        telegram_bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
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

def send_telegram_notification(message):
    """Send a notification via Telegram bot."""
    if not telegram_bot:
        return False

    try:
        telegram_bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=f"🚨 XML Watcher Alert\n\n{message}"
        )
        return True
    except Exception as e:
        print(f"Error sending Telegram notification: {e}")
        return False

def send_notification(message):
    """Send a notification (console + Telegram)."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"[{timestamp}] ⚠️  ALERT: {message}")
    print(f"{'='*60}\n")

    # Try to send via Telegram
    if telegram_bot:
        if send_telegram_notification(message):
            print("✓ Telegram notification sent")
        else:
            print("✗ Failed to send Telegram notification")

def main():
    print(f"Starting XML directory watcher...")
    print(f"Monitoring: {XML_DIR}")
    print(f"Check interval: {CHECK_INTERVAL} seconds ({CHECK_INTERVAL/60:.1f} minutes)\n")

    if not os.path.exists(XML_DIR):
        print(f"ERROR: Directory does not exist: {XML_DIR}")
        exit(1)

    # Send startup notification
    if telegram_bot:
        try:
            startup_msg = f"✅ XML Watcher Started\n\nMonitoring: {XML_DIR}\nCheck interval: {CHECK_INTERVAL/60:.0f} minutes"
            telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=startup_msg)
            print("✓ Startup notification sent to Telegram")
        except Exception as e:
            print(f"✗ Failed to send startup notification: {e}")

    last_file_time = get_latest_file_time(XML_DIR)
    already_warned = False  # Track if we've already sent a warning

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
                if not already_warned:
                    send_notification("No XML files found in directory!")
                    already_warned = True
            elif current_file_time == last_file_time:
                # No new files since last check
                last_datetime = datetime.fromtimestamp(last_file_time)
                if not already_warned:
                    send_notification(
                        f"No new XML files in the last {CHECK_INTERVAL/60:.0f} minutes! "
                        f"Last file at {last_datetime.strftime('%H:%M:%S')}"
                    )
                    already_warned = True
                print(f"[{timestamp}] ⚠️  No new files since {last_datetime.strftime('%H:%M:%S')}")
            else:
                # New file detected
                new_datetime = datetime.fromtimestamp(current_file_time)

                # If we had previously warned, send a "resumed" notification
                if already_warned:
                    send_notification(
                        f"✅ XML files resumed! New file detected at {new_datetime.strftime('%H:%M:%S')}"
                    )
                    already_warned = False  # Reset warning flag for next gap

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
