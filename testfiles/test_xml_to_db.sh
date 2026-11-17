#!/bin/bash
# Test XML → Database processing
# Tests datalogger_service.py --LogToDatabase using test XMLs

cd "$(dirname "$0")/.."

# Force dev environment
export DATALOGGER_CONFIG_DIR="$HOME/.datalogger"

echo "================================================================"
echo "Testing XML → Database Processing"
echo "================================================================"
echo ""

DB_FILE="$HOME/.datalogger/dev_database.db"
XML_DIR="$HOME/.datalogger/xmls"

# Configure test date here
TEST_DATE="2026-11-16"  # Change this to the date you want to test with

echo "Using test date: $TEST_DATE"
echo "XML directory: $XML_DIR"
echo ""

# Check if date exists in DB before deletion
echo "Before test - checking for $TEST_DATE:"
EXISTS=$(sqlite3 "$DB_FILE" "SELECT date, bird_age FROM Daily_Bot_Log WHERE date='$TEST_DATE';" 2>/dev/null)
if [ -n "$EXISTS" ]; then
    echo "   Found: $EXISTS"
    echo "   Deleting to prepare for test..."
    sqlite3 "$DB_FILE" "DELETE FROM Daily_Bot_Log WHERE date='$TEST_DATE';" 2>/dev/null
else
    echo "   Not found (will be inserted)"
fi
echo ""

# Run XML → DB processing (with --NoDelete to preserve test XMLs)
echo "Running: datalogger_service.py --LogToDatabase --NoDelete"
echo ""
.venv/bin/python3 datalogger_service.py --LogToDatabase --NoDelete

echo ""
echo "================================================================"
echo "After test - checking for $TEST_DATE:"
RESULT=$(sqlite3 "$DB_FILE" "SELECT date, bird_age FROM Daily_Bot_Log WHERE date='$TEST_DATE';" 2>/dev/null)
if [ -n "$RESULT" ]; then
    echo "   Success! Found: $RESULT"
else
    echo "   Failed - row not created"
fi
echo ""

echo "Test complete"
echo "================================================================"
