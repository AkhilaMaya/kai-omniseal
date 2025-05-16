#!/bin/bash
# Run both scripts in background
python3 kai_telegram.py &
python3 kai_omniseal.py &

# Keep the container alive
tail -f /dev/null
