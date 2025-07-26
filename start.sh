#!/usr/bin/env bash

# Debug information
echo "🔍 Debug: Current directory: $(pwd)"
echo "🔍 Debug: Python version: $(python3.11 --version)"
echo "🔍 Debug: Testing Python import:"
python3.11 -c "import sys; print('Python works:', sys.version)"
echo "🔍 Debug: Testing required imports:"
python3.11 -c "import requests; print('requests OK')"
python3.11 -c "import scrapy; print('scrapy OK')"
echo "🔍 Debug: Testing monitor imports one by one:"
python3.11 -c "import time; print('time OK')"
python3.11 -c "import os; print('os OK')"
python3.11 -c "import sys; print('sys OK')"
python3.11 -c "import subprocess; print('subprocess OK')"
python3.11 -c "import json; print('json OK')"
python3.11 -c "from datetime import datetime, timedelta; print('datetime OK')"
echo "🔍 Debug: Testing monitor first few lines:"
python3.11 -c "
import sys
sys.path.append('.')
content = open('monitor_news_group1.py').read()
print('File read OK, length:', len(content))
print('First 500 chars:')
print(repr(content[:500]))
exec(content[:500])
print('First 500 chars OK')
"
echo "🔍 Debug: Files in directory: $(ls -la)"

# Create logs directory if it doesn't exist
mkdir -p logs
 
# Start the news monitor
echo "🚀 Starting News Monitor Group 1..."
echo "🔍 Debug: About to run monitor_news_group1.py"
echo "🔍 Debug: Checking if file exists..."
ls -la monitor_news_group1.py
echo "🔍 Debug: File permissions:"
stat monitor_news_group1.py
echo "🔍 Debug: Trying to run with python3.11..."
echo "🔍 Debug: Checking syntax first:"
python3.11 -m py_compile monitor_news_group1.py
echo "🔍 Debug: Syntax check completed"
echo "🔍 Debug: Now running the monitor:"
echo "🔍 Debug: Running with timeout (30 minutes):"
echo "🔍 Debug: This should show import debug logs if monitor starts:"
echo "🔍 Debug: Setting PYTHONUNBUFFERED=1 to force output:"
PYTHONUNBUFFERED=1 timeout 1800 python3.11 monitor_news_group1.py 2>&1
echo "🔍 Debug: No import logs above means monitor hangs before imports"
echo "🔍 Debug: Monitor exit code: $?"
echo "🔍 Debug: If exit code is 124, monitor timed out"
echo "🔍 Debug: If exit code is 0, monitor completed successfully"
echo "🔍 Debug: If exit code is other, monitor failed with error"
echo "🔍 Debug: Monitor finished (if you see this, monitor completed)" 