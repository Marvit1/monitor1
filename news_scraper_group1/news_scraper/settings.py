# Scrapy settings for news_scraper_group1 project (MAJOR NEWS SITES)
# Simplified version without Django for Render.com deployment

BOT_NAME = "news_scraper_group1"

SPIDER_MODULES = ["news_scraper.spiders"]
NEWSPIDER_MODULE = "news_scraper.spiders"

# Use asyncio reactor for better signal handling
TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'

# Disable Twisted signal handling for containerized environments
TWISTED_DISABLE_SIGNAL_HANDLERS = True

# Use stable Twisted version for better compatibility
TWISTED_VERSION = '22.10.0'

# Additional Twisted settings for stability
TWISTED_NO_SIGNAL_HANDLERS = True

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Aggressive memory optimization - Group 1 (Major sites)
CONCURRENT_REQUESTS = 1  # Single request at a time to save memory
CONCURRENT_REQUESTS_PER_DOMAIN = 1  # Single per domain
CONCURRENT_REQUESTS_PER_IP = 1  # Single per IP

# Add respectful delays for major sites
DOWNLOAD_DELAY = 1.5  # Longer delay for major sites
RANDOMIZE_DOWNLOAD_DELAY = 0.5  # Random delay 1-2 seconds

# Enable AutoThrottle for better performance
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 15
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.5
AUTOTHROTTLE_DEBUG = False

# Better timeout settings
DOWNLOAD_TIMEOUT = 45  # Longer timeout for major sites

# Retry settings
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Disable image loading to save memory
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.media.MediaPipeline': None,
}

# Disable media pipeline
MEDIA_ALLOW_REDIRECTS = False

# Configure item pipelines
ITEM_PIPELINES = {
   "news_scraper.pipelines.NewsScraperPipeline": 300,
}

# Enable HTTP caching for development
HTTPCACHE_ENABLED = False  # Disable for production

# Set settings whose default value is deprecated to a future-proof value
FEED_EXPORT_ENCODING = "utf-8"

# User agent rotation
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Log level
LOG_LEVEL = 'INFO' 