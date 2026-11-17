#!/bin/bash

# Test script for Unitas dry-run mode
# Opens browser, logs in, navigates to form, shows data but doesn't submit

# Configuration
TEST_DATE="2026-11-16"  # Change this to test different dates

# Change to project root
cd "$(dirname "$0")/.." || exit 1

# Set config directory to dev environment
export DATALOGGER_CONFIG_DIR="$HOME/.datalogger"

# Get database path
DB_FILE="$HOME/.datalogger/dev_database.db"

echo "Running Unitas dry-run test..."
echo "Config dir: $DATALOGGER_CONFIG_DIR"
echo "Database: $DB_FILE"
echo "Test date: $TEST_DATE"
echo ""

# Run dry-run
.venv/bin/python3 datalogger_service.py --LogToUnitas --date "$TEST_DATE" --dry-run "$@"
