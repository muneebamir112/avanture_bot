#!/usr/bin/env bash
# ========================================================
# Avanture Automation Runner for macOS
# ========================================================

cd "$(dirname "$0")"

# Check Python3 availability
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed or not in PATH. Please install Python 3.10+ from python.org or Homebrew."
    exit 1
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installing required packages..."
    pip install -r requirements.txt
    playwright install chromium
else
    source venv/bin/activate
fi

# Run the UI app
python3 app.py

