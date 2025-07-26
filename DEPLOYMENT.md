# 🚀 News Monitor Group 1 - Deployment Guide

## 📋 Essential Files

### Core Files:
- ✅ `monitor_news_group1.py` - Main monitoring script
- ✅ `requirements.txt` - Python dependencies (without lxml)
- ✅ `build_render.sh` - Build script for Render.com
- ✅ `start.sh` - Start script for Render.com
- ✅ `render.yaml` - Render.com configuration

### Documentation:
- ✅ `api_endpoints.md` - API endpoints documentation
- ✅ `README.md` - Project overview

## 🎯 Render.com Configuration

### Build Command:
```bash
chmod +x build_render.sh && ./build_render.sh
```

### Start Command:
```bash
chmod +x start.sh && ./start.sh
```

### Environment Variables:
```
PYTHON_VERSION=3.11.0
API_BASE_URL=https://beackkayq.onrender.com
SCRAPY_SETTINGS_MODULE=news_scraper.settings
PYTHONPATH=/opt/render/project/src/news_scraper_group1
LOG_LEVEL=INFO
MONITOR_INTERVAL_MINUTES=2
DAYS_TO_KEEP_ARTICLES=7
```

## ✅ Dependencies (requirements.txt)

```txt
# HTTP requests for API communication
requests==2.31.0
urllib3==2.0.7

# Scrapy Framework
Scrapy==2.5.1
scrapy-user-agents==0.1.1

# Selenium (for dynamic content)
selenium==4.15.2
webdriver-manager==4.0.1

# Redis (for caching)
redis==5.0.1

# Utilities
python-dateutil==2.8.2
pytz==2023.3

# Logging and monitoring
colorlog==6.8.0

# Telegram Bot - Keep v13.15 to avoid compatibility issues
python-telegram-bot==13.15
```

## 🚀 Deployment Steps

1. **Push to GitHub:**
```bash
git add .
git commit -m "Clean deployment files - remove lxml dependency"
git push origin main
```

2. **Render.com Setup:**
   - Connect GitHub repository
   - Use build command: `chmod +x build_render.sh && ./build_render.sh`
   - Use start command: `chmod +x start.sh && ./start.sh`
   - Add environment variables
   - Deploy

3. **Monitor Logs:**
   - Check build success
   - Verify spiders start
   - Test Telegram notifications

## ✅ Features

- ✅ **Web scraping** - All spiders (TERT, PANORAMA, NEWS.AM, etc.)
- ✅ **Selenium support** - Dynamic content scraping
- ✅ **Telegram notifications** - Real-time alerts
- ✅ **Redis caching** - Performance optimization
- ✅ **API integration** - Database communication
- ✅ **Error handling** - Graceful failures

Հիմա deployment-ը պարզ և մաքուր է! 🎉 