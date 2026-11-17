#!/bin/bash
# Test script to trigger startup error template in webapp
# Usage: ./testfiles/test_startup_error.sh [flask args...]

cd "$(dirname "$0")/.."
TEST_STARTUP_ERROR="This is a test configuration error for testing the error template" .venv/bin/python3 webapp.py "$@"
