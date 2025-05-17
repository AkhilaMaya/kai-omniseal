#!/bin/bash
# Run both scripts and log their outputs
python3 kai_telegram.py > telegram.log 2>&1 &
python3 kai_omniseal.py > flask.log 2>&1
