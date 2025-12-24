#!/bin/bash
# Daily Chromebook Data Export for Looker Studio
cd /opt/chromebook-dashboard
/opt/chromebook-dashboard/venv/bin/python3 export_to_sheets.py >> /var/log/chromebook-export.log 2>&1
