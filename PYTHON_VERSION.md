# Python Version Configuration

## Current Setup
- **Python Version**: 3.11.0
- **Virtual Environment**: `venv/` (created with `py -3.11 -m venv venv`)
- **Key Dependencies**:
  - Scrapy: 2.11.0
  - Twisted: 22.10.0
  - Python: 3.11.0

## Why Python 3.11?
- Better compatibility with Twisted 22.10.0
- Resolves `_handleSignals` attribute errors
- More stable signal handling in containerized environments
- Avoids Python 3.13 compatibility issues

## Setup Instructions
```bash
# Create virtual environment with Python 3.11
py -3.11 -m venv venv

# Activate virtual environment
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run monitor
python monitor_news_group1.py
```

## Changes Made
- Updated `requirements.txt` with stable versions
- Simplified subprocess calls in `monitor_news_group1.py`
- Removed complex Twisted reactor patching
- Using simple `scrapy crawl` commands

## Date
Updated: $(date) 