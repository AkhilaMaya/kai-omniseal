#!/bin/bash
python3 kai_omniseal.py &   # Start backend Flask server in the background
python3 kai_telegram.py     # Start Telegram bot (runs in foreground)
