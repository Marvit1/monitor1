import scrapy
from news_scraper.items import NewsScraperItem
import sys
import os
import hashlib
import redis
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import time
import random
import requests

class CivilNetSpider(scrapy.Spider):
    name = "civilnet"
    allowed_domains = ["civilnet.am"]
    start_urls = ["https://www.civilnet.am/"]
    
    # Enhanced anti-blocking headers and settings
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15'
    ]
    
    custom_settings = {
        'DOWNLOAD_DELAY': 5,
        'RANDOMIZE_DOWNLOAD_DELAY': 2,
        'RETRY_TIMES': 8,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429, 403, 401, 404],
        'HTTPERROR_ALLOWED_CODES': [403, 404, 401],
        'COOKIES_ENABLED': True,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 5,
        'AUTOTHROTTLE_MAX_DELAY': 20,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 0.5,
        'CONCURRENT_REQUESTS': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': 90,
            'scrapy_user_agents.middlewares.RandomUserAgentMiddleware': 400,
        },
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'hy,en-US;q=0.9,en;q=0.8,ru;q=0.7,fr;q=0.6',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'DNT': '1',
            'Sec-GPC': '1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
        },
    }

    def __init__(self, *args, **kwargs):
        super(CivilNetSpider, self).__init__(*args, **kwargs)
        
        # Setup Selenium WebDriver
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--allow-running-insecure-content')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.logger.info("🌐 Selenium Chrome driver ստեղծված է")
        except Exception as e:
            self.logger.warning(f"🌐 Selenium չկա: {e}")
            self.driver = None
        
        # Redis connection
        try:
            self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            self.redis_client.ping()
            self.logger.info("🔴 Redis կապակցված է")
        except Exception as e:
            self.logger.warning(f"🔴 Redis չկա, կաշխատի առանց cache: {e}")
            self.redis_client = None

        # API client
        self.api_base_url = os.environ.get('API_BASE_URL', 'https://beackkayq.onrender.com')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'NewsMonitor/1.0'
        })
        
        # Load keywords via API
        try:
            response = self.session.get(f"{self.api_base_url}/api/keywords/", timeout=10)
            if response.status_code == 200:
                keywords_data = response.json()
                self.keywords = [kw.get('word', '').lower() for kw in keywords_data]
                self.logger.info(f"🔑 Բանալի բառեր: {', '.join(self.keywords) if self.keywords else 'Չկա (բոլոր հոդվածները)'}")
            else:
                self.logger.warning(f"API keywords error: {response.status_code}")
                self.keywords = []
        except Exception as e:
            self.logger.warning(f"Բանալի բառերը չհաջողվեց բեռնել: {e}")
            self.keywords = []

        # Statistics
        self.processed_articles = 0
        self.new_articles = 0
        self.duplicate_articles = 0  # Add missing counter used by pipeline
        self.cached_skips = 0
        self.blocked_attempts = 0

    def get_random_headers(self):
        """Generate random headers to avoid blocking"""
        import random
        user_agent = random.choice(self.user_agents)
        referers = [
            'https://www.google.com/',
            'https://www.facebook.com/',
            'https://www.bing.com/',
            'https://duckduckgo.com/',
            'https://yandex.com/',
            'https://t.me/',
            'https://www.youtube.com/'
        ]
        return {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,hy;q=0.8,ru;q=0.7,fr;q=0.6',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-User': '?1',
            'DNT': '1',
            'Sec-GPC': '1',
            'Cache-Control': 'max-age=0',
            'Referer': random.choice(referers)
        }

    def start_requests(self):
        """Override start_requests to use only Selenium"""
        # Use only Selenium without scrapy requests
        if not self.driver:
            self.logger.error("❌ Selenium driver չկա")
            return
            
        for url in self.start_urls:
            try:
                self.parse_with_selenium_only(url)
            except Exception as e:
                self.logger.error(f"❌ Selenium parsing error: {e}")
        
        # Return empty generator to satisfy scrapy
        return
        yield

    def is_article_processed(self, url, title):
        """Check if article was already processed using Redis cache"""
        if not self.redis_client:
            return False
        # Create unique hash for article
        article_hash = hashlib.md5(f"{url}:{title}".encode()).hexdigest()
        cache_key = f"processed_civilnet:{article_hash}"
        return self.redis_client.exists(cache_key)

    def mark_article_processed(self, url, title):
        """Mark article as processed in Redis cache"""
        if not self.redis_client:
            return
        # Create unique hash for article
        article_hash = hashlib.md5(f"{url}:{title}".encode()).hexdigest()
        cache_key = f"processed_civilnet:{article_hash}"
        # Mark as processed (expire in 7 days)
        self.redis_client.setex(cache_key, 604800, "1")

    def article_contains_keyword(self, article_text):
        if not article_text:
            return False
        if not self.keywords:  # If no keywords, scrape all articles
            return True
        for keyword in self.keywords:
            if keyword in article_text.lower():
                return True
        return False

    def parse_with_selenium_only(self, url):
        """Parse page using only Selenium without scrapy requests"""
        try:
            # Try to load page with Selenium
            self.logger.info(f"🌐 Selenium-ով բեռնում է: {url}")
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Random scroll to simulate human behavior
            scroll_height = self.driver.execute_script("return document.body.scrollHeight")
            for _ in range(3):
                scroll_to = random.randint(0, scroll_height)
                self.driver.execute_script(f"window.scrollTo(0, {scroll_to})")
                time.sleep(random.uniform(0.5, 1.5))
            
            # Get page source
            page_source = self.driver.page_source
            
            # Create new response with Selenium content
            from scrapy.http import HtmlResponse
            selenium_response = HtmlResponse(
                url=url,
                body=page_source,
                encoding='utf-8'
            )
            
            # Parse articles directly
            self.parse_articles_direct(selenium_response)
            
        except Exception as e:
            self.logger.error(f"❌ Selenium error: {e}")
            
    def parse_articles_direct(self, response):
        """Parse articles directly using Selenium content"""
        # Extract articles using the civilnet.am structure
        # Try multiple selectors for different page layouts
        articles = (response.css("div.sidebar-newsfeed ul.flex-module li") or
                   response.css("article") or
                   response.css(".post") or
                   response.css(".news-item") or
                   response.css("div.news-block") or
                   response.css("div.article-item") or
                   response.css("a[href*='/news/']"))
        
        self.logger.info(f"📰 Գտնվել է {len(articles)} հոդված (օպտիմիզացված - սահմանափակված 10-ով)")
        
        # Limit to latest 10 articles only for optimization (running every 10 minutes)
        articles = articles[:10]

        for article in articles:
            # Extract link and title using civilnet.am structure
            link = (article.css("div.item-content h4.ellipsis a::attr(href)").get() or
                   article.css("h4 a::attr(href)").get() or
                   article.css("h3 a::attr(href)").get() or
                   article.css("h2 a::attr(href)").get() or
                   article.css("a::attr(href)").get())
                   
            title_preview = (article.css("div.item-content h4.ellipsis a::text").get() or
                           article.css("h4 a::text").get() or
                           article.css("h3 a::text").get() or
                           article.css("h2 a::text").get() or
                           article.css("a::text").get())
            
            if link and title_preview:
                # Clean the title by removing extra whitespace
                title_preview = title_preview.strip()
                if len(title_preview) < 10:  # Skip too short titles
                    continue
                    
                full_url = response.urljoin(link)
                
                # Check Redis cache first
                if self.is_article_processed(full_url, title_preview):
                    self.cached_skips += 1
                    continue
                
                # Parse article directly with Selenium
                self.parse_article_direct(full_url)
                
    def parse_article_direct(self, url):
        """Parse individual article using Selenium directly"""
        try:
            time.sleep(random.uniform(2, 4))  # Random delay between articles
            
            self.logger.info(f"🌐 Selenium-ով հոդված բեռնում է: {url}")
            self.driver.get(url)
            
            # Wait for article to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Get page source
            page_source = self.driver.page_source
            
            # Create response
            from scrapy.http import HtmlResponse
            article_response = HtmlResponse(
                url=url,
                body=page_source,
                encoding='utf-8'
            )
            
            # Parse article content
            self.processed_articles += 1

            # Try multiple title selectors for civilnet.am
            title = (article_response.css("h1::text").get() or
                    article_response.css(".article-title::text").get() or
                    article_response.css(".post-title::text").get() or
                    article_response.css(".entry-title::text").get() or
                    article_response.css(".page-title::text").get() or
                    article_response.css(".news-title::text").get() or
                    article_response.css(".title::text").get() or
                    article_response.css("meta[property='og:title']::attr(content)").get() or
                    article_response.css("title::text").get())
            
            # Try multiple content selectors for civilnet.am
            content_parts = (article_response.css("div.post-content ::text").getall() or
                            article_response.css("div.entry-content ::text").getall() or
                            article_response.css("div.article-content ::text").getall() or
                            article_response.css("div.content ::text").getall() or
                            article_response.css("div.article-body ::text").getall() or
                            article_response.css("div.article-text ::text").getall() or
                            article_response.css("div.text-content ::text").getall() or
                            article_response.css("div.main-content ::text").getall() or
                            article_response.css("article ::text").getall() or
                            article_response.css(".content ::text").getall() or
                            article_response.css(".article ::text").getall() or
                            article_response.css(".text ::text").getall() or
                            article_response.css("p::text").getall())
            
            content = "\n".join([p.strip() for p in content_parts if p.strip()])

            # Extract scraped time
            scraped_time = (article_response.css('time::attr(datetime)').get() or
                           article_response.css('time::text').get() or 
                           article_response.css('.date::text').get() or
                           article_response.css('.article-date::text').get() or
                           article_response.css('.post-date::text').get() or
                           article_response.css('.publish-date::text').get() or
                           article_response.css('.timestamp::text').get() or
                           article_response.css('.meta-date::text').get() or
                           article_response.css('.post-meta-date::text').get() or
                           datetime.now().isoformat())

            # Clean title for display
            display_title = title[:60] + "..." if title and len(title) > 60 else title or "Անանուն հոդված"
            
            if self.article_contains_keyword(title) or self.article_contains_keyword(content):
                self.logger.info(f"✅ Բանալի բառ գտնվեց: {display_title}")
                # Mark as processed only after successful keyword match
                self.mark_article_processed(url, title)
                self.new_articles += 1
                
                # Create and yield item directly
                item = NewsScraperItem()
                item['title'] = title or f'Article from {url.split("/")[-1]}'
                item['link'] = url
                item['source_url'] = url
                item['content'] = content
                item['scraped_time'] = scraped_time
                
                # Process item through pipeline
                from news_scraper.pipelines import NewsScraperPipeline
                pipeline = NewsScraperPipeline()
                pipeline.process_item(item, self)
                
            else:
                self.logger.info(f"❌ Բանալի բառ չգտնվեց: {display_title}")
                # Mark as processed even if no keyword match to avoid re-checking
                self.mark_article_processed(url, title)
                
        except Exception as e:
            self.logger.error(f"❌ Article parsing error: {e}")
            
    def parse(self, response):
        # Extract articles using the civilnet.am structure
        # Try multiple selectors for different page layouts
        articles = (response.css("div.sidebar-newsfeed ul.flex-module li") or
                   response.css("article") or
                   response.css(".post") or
                   response.css(".news-item") or
                   response.css("div.news-block") or
                   response.css("div.article-item") or
                   response.css("a[href*='/news/']"))
        
        self.logger.info(f"📰 Գտնվել է {len(articles)} հոդված (օպտիմիզացված - սահմանափակված 10-ով)")
        
        # Limit to latest 10 articles only for optimization (running every 10 minutes)
        articles = articles[:10]

        for article in articles:
            # Extract link and title using civilnet.am structure
            link = (article.css("div.item-content h4.ellipsis a::attr(href)").get() or
                   article.css("h4 a::attr(href)").get() or
                   article.css("h3 a::attr(href)").get() or
                   article.css("h2 a::attr(href)").get() or
                   article.css("a::attr(href)").get())
                   
            title_preview = (article.css("div.item-content h4.ellipsis a::text").get() or
                           article.css("h4 a::text").get() or
                           article.css("h3 a::text").get() or
                           article.css("h2 a::text").get() or
                           article.css("a::text").get())
            
            if link and title_preview:
                # Clean the title by removing extra whitespace
                title_preview = title_preview.strip()
                if len(title_preview) < 10:  # Skip too short titles
                    continue
                    
                full_url = response.urljoin(link)
                
                # Check Redis cache first
                if self.is_article_processed(full_url, title_preview):
                    self.cached_skips += 1
                    continue
                
                # Add delay and random headers for individual articles
                time.sleep(random.uniform(1, 3))
                    
                yield scrapy.Request(
                    url=full_url,
                    headers=self.get_random_headers(),
                    callback=self.parse_article,
                    dont_filter=True
                )
    
    def parse_news_section(self, response):
        """Alternative parsing method for news section"""
        # Look for news articles in the news section
        article_links = response.css("a[href*='/news/']")
        
        self.logger.info(f"📰 Գտնվել է {len(article_links)} լրություն հղում (օպտիմիզացված - սահմանափակված 10-ով)")
        
        # Limit to latest 10 articles
        article_links = article_links[:10]
        
        for link_element in article_links:
            link = link_element.css("::attr(href)").get()
            title_preview = link_element.css("::text").get()
            
            if link and title_preview:
                title_preview = title_preview.strip()
                if len(title_preview) < 10:
                    continue
                    
                full_url = response.urljoin(link)
                
                if self.is_article_processed(full_url, title_preview):
                    self.cached_skips += 1
                    continue
                
                # Add delay and random headers for individual articles
                time.sleep(random.uniform(1, 3))
                    
                yield scrapy.Request(
                    url=full_url,
                    headers=self.get_random_headers(),
                    callback=self.parse_article,
                    dont_filter=True
                )

    def parse_article(self, response):
        self.processed_articles += 1

        # Try multiple title selectors for civilnet.am
        title = (response.css("h1::text").get() or
                response.css(".article-title::text").get() or
                response.css(".post-title::text").get() or
                response.css(".entry-title::text").get() or
                response.css(".page-title::text").get() or
                response.css(".news-title::text").get() or
                response.css(".title::text").get() or
                response.css("meta[property='og:title']::attr(content)").get() or
                response.css("title::text").get())
        
        # Try multiple content selectors for civilnet.am
        content_parts = (response.css("div.post-content ::text").getall() or
                        response.css("div.entry-content ::text").getall() or
                        response.css("div.article-content ::text").getall() or
                        response.css("div.content ::text").getall() or
                        response.css("div.article-body ::text").getall() or
                        response.css("div.article-text ::text").getall() or
                        response.css("div.text-content ::text").getall() or
                        response.css("div.main-content ::text").getall() or
                        response.css("article ::text").getall() or
                        response.css(".content ::text").getall() or
                        response.css(".article ::text").getall() or
                        response.css(".text ::text").getall() or
                        response.css("p::text").getall())
        
        content = "\n".join([p.strip() for p in content_parts if p.strip()])

        # Extract scraped time - try multiple selectors
        scraped_time = (response.css('time::attr(datetime)').get() or
                       response.css('time::text').get() or 
                       response.css('.date::text').get() or
                       response.css('.article-date::text').get() or
                       response.css('.post-date::text').get() or
                       response.css('.publish-date::text').get() or
                       response.css('.timestamp::text').get() or
                       response.css('.meta-date::text').get() or
                       response.css('.post-meta-date::text').get() or
                       datetime.now().isoformat())

        # Clean title for display
        display_title = title[:60] + "..." if title and len(title) > 60 else title or "Անանուն հոդված"
        
        if self.article_contains_keyword(title) or self.article_contains_keyword(content):
            self.logger.info(f"✅ Բանալի բառ գտնվեց: {display_title}")
            # Mark as processed only after successful keyword match
            self.mark_article_processed(response.url, title)
            self.new_articles += 1
            
            item = NewsScraperItem()
            item['title'] = title or f'Article from {response.url.split("/")[-1]}'
            item['link'] = response.url
            item['source_url'] = response.url
            item['content'] = content
            item['scraped_time'] = scraped_time
            yield item
        else:
            self.logger.info(f"❌ Բանալի բառ չգտնվեց: {display_title}")
            # Mark as processed even if no keyword match to avoid re-checking
            self.mark_article_processed(response.url, title)

    def closed(self, reason):
        """Called when spider finishes"""
        # Close Selenium driver
        if hasattr(self, 'driver') and self.driver:
            try:
                self.driver.quit()
                self.logger.info("🌐 Selenium driver-ը փակված է")
            except Exception as e:
                self.logger.warning(f"🌐 Selenium driver-ը չափակվեց: {e}")
                
        self.logger.info(f"""
📊 ԱՄՓՈՓՈՒՄ CIVILNET.AM (օպտիմիզացված - միայն 10 հոդված):
   • Ստուգված հոդվածներ: {self.processed_articles}
   • Նոր հոդվածներ: {self.new_articles}
   • Կրկնություն հոդվածներ: {self.duplicate_articles}
   • Cache-ից բաց թողնված: {self.cached_skips}
   • Արգելափակման փորձեր: {self.blocked_attempts}
   • Սկրիպտի աշխատանքը: ✅ Ավարտված
        """.strip()) 