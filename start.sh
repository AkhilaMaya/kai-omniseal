#!/bin/bash

# Run both scripts and show logs
python3 kai_telegram.py > telegram.log 2>&1 &
python3 kai_omniseal.py > flask.log 2>&1 &

# Print both logs continuously to console
tail -f telegram.log flask.log
