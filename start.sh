#!/bin/bash
python3 kai_telegram.py &   # Launch Telegram bot in background
python3 kai_omniseal.py     # Run main validation app in foreground
