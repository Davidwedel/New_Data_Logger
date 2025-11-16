#!/usr/bin/env python3
"""
Upload Queue Manager
Handles queue file for triggering Unitas uploads from webapp
"""
import os
import fcntl
import pathlib
from datetime import datetime

QUEUE_FILE = "/var/lib/datalogger/upload_queue.txt"

def add_to_queue(date_str):
    """
    Add a date to the upload queue.

    Args:
        date_str: ISO format date string (YYYY-MM-DD)
    """
    queue_path = pathlib.Path(QUEUE_FILE)

    # Ensure parent directory exists
    queue_path.parent.mkdir(parents=True, exist_ok=True)

    # Read existing queue to avoid duplicates
    existing_dates = set()
    if queue_path.exists():
        try:
            with open(queue_path, 'r') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                existing_dates = {line.strip() for line in f if line.strip()}
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            print(f"Warning: Could not read queue file: {e}")

    # Add date if not already queued
    if date_str not in existing_dates:
        try:
            with open(queue_path, 'a') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                f.write(f"{date_str}\n")
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            print(f"Added {date_str} to upload queue")
            return True
        except Exception as e:
            print(f"Error adding to queue: {e}")
            return False
    else:
        print(f"{date_str} already in queue")
        return True


def get_queued_dates():
    """
    Get all dates from the upload queue.

    Returns:
        list: List of date strings in queue
    """
    queue_path = pathlib.Path(QUEUE_FILE)

    if not queue_path.exists():
        return []

    try:
        with open(queue_path, 'r') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            dates = [line.strip() for line in f if line.strip()]
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        return dates
    except Exception as e:
        print(f"Error reading queue: {e}")
        return []


def remove_from_queue(date_str):
    """
    Remove a date from the upload queue.

    Args:
        date_str: ISO format date string (YYYY-MM-DD)
    """
    queue_path = pathlib.Path(QUEUE_FILE)

    if not queue_path.exists():
        return

    try:
        # Read all dates except the one to remove
        with open(queue_path, 'r') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            remaining_dates = [line.strip() for line in f if line.strip() and line.strip() != date_str]
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        # Write back remaining dates
        with open(queue_path, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            for date in remaining_dates:
                f.write(f"{date}\n")
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        print(f"Removed {date_str} from upload queue")
    except Exception as e:
        print(f"Error removing from queue: {e}")


def clear_queue():
    """Clear all dates from the upload queue."""
    queue_path = pathlib.Path(QUEUE_FILE)

    try:
        if queue_path.exists():
            queue_path.unlink()
        print("Upload queue cleared")
    except Exception as e:
        print(f"Error clearing queue: {e}")
