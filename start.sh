#!/bin/bash

# Log file locations
echo "Launching Kai Telegram and Kai Omniseal..."

# Clean logs from last run (optional)
rm -f telegram.log flask.log

# Run both scripts and log everything
python3 kai_telegram.py > telegram.log 2>&1 &
python3 kai_omniseal.py > flask.log 2>&1 &

# Keep the container alive and stream logs
tail -n 50 -f telegram.log flask.log
