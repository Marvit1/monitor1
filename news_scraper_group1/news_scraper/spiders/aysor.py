import scrapy
from news_scraper.items import NewsScraperItem
import sys
import os
import hashlib
import redis
from datetime import datetime
from urllib.parse import unquote
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import time
import requests


class AysorSpider(scrapy.Spider):
    name = "aysor"
    allowed_domains = ["aysor.am"]
    start_urls = [
        "https://www.aysor.am/am",
    ]
    
    # Add custom headers to bypass potential blocking
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    }

    def __init__(self, *args, **kwargs):
        super(AysorSpider, self).__init__(*args, **kwargs)
        
        # Initialize Selenium WebDriver
        self.driver = None
        self.setup_selenium()
        
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
        self.duplicate_articles = 0  # Add missing counter used in pipeline
        self.cached_skips = 0
        
    def setup_selenium(self):
        """Setup Selenium WebDriver with optimal settings"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # Run in background
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Try to initialize Chrome driver
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.logger.info("🚗 Selenium Chrome driver կապակցված է")
            
        except Exception as e:
            self.logger.error(f"❌ Selenium setup failed: {e}")
            self.driver = None
    
    def get_page_with_selenium(self, url):
        """Get page content using Selenium"""
        if not self.driver:
            self.logger.error("❌ Selenium driver չկա")
            return None
            
        try:
            self.logger.info(f"🌐 Selenium-ով բեռնվում է: {url}")
            self.driver.get(url)
            
            # Wait for content to load
            time.sleep(3)
            
            # Wait for specific elements that indicate content is loaded
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
            except TimeoutException:
                self.logger.warning("⏰ Page load timeout")
            
            return self.driver.page_source
            
        except WebDriverException as e:
            self.logger.error(f"❌ Selenium error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"❌ Unexpected error: {e}")
            return None

    def is_article_processed(self, url, title):
        """Check if article was already processed using Redis cache"""
        if not self.redis_client:
            return False
        # Create unique hash for article
        article_hash = hashlib.md5(f"{url}:{title}".encode()).hexdigest()
        cache_key = f"processed_aysor:{article_hash}"
        return self.redis_client.exists(cache_key)

    def mark_article_processed(self, url, title):
        """Mark article as processed in Redis cache"""
        if not self.redis_client:
            return
        # Create unique hash for article
        article_hash = hashlib.md5(f"{url}:{title}".encode()).hexdigest()
        cache_key = f"processed_aysor:{article_hash}"
        # Mark as processed (expire in 7 days)
        self.redis_client.setex(cache_key, 604800, "1")

    def article_contains_keyword(self, article_text):
        if not article_text:
            return False
        if not self.keywords:  # If no keywords, scrape all articles
            return True
        
        article_lower = article_text.lower()
        for keyword in self.keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in article_lower:
                self.logger.debug(f"🔍 Keyword '{keyword}' found in text")
                return True
        return False

    def start_requests(self):
        """Override start_requests to use Selenium"""
        for url in self.start_urls:
            # Use a dummy request since we'll use Selenium
            yield scrapy.Request(url, callback=self.parse_with_selenium, dont_filter=True)
    
    def parse_with_selenium(self, response):
        """Parse page using Selenium to get JavaScript-rendered content"""
        if not self.driver:
            self.logger.error("❌ Selenium driver չկա, սովորական parsing")
            yield from self.parse(response)
            return
        
        # Get page content with Selenium
        html_content = self.get_page_with_selenium(response.url)
        if not html_content:
            self.logger.error(f"❌ Selenium չկարողացավ բեռնել: {response.url}")
            return
        
        # Create a new response object with Selenium content
        from scrapy.http import HtmlResponse
        selenium_response = HtmlResponse(
            url=response.url,
            body=html_content,
            encoding='utf-8'
        )
        
        yield from self.parse(selenium_response)

    def parse(self, response):
        # Check if this is an article page or a listing page
        if '/news/' in response.url and len(response.url.split('/')) > 6:
            # This looks like an article page, parse it directly
            yield from self.parse_article(response)
            return
        
        # Extract articles from news feed using aysor.am structure with Selenium-loaded content
        
        # Try various selectors for dynamically loaded content
        selectors_to_try = [
            "div.news_feed div.news_block",
            "div.news_block", 
            "article",
            ".article",
            ".news-item",
            ".news_item",
            "a[href*='/news/']",
            "a[href*='/article/']",
            "div[class*='news'] a",
            "div[class*='article'] a",
            ".main-content a[href*='/news/']",
            ".content a[href*='/news/']",
            ".container a[href*='/news/']",
            "ul li a[href*='/news/']",
            ".news-list a",
            ".article-list a"
        ]
        
        articles = []
        for selector in selectors_to_try:
            try:
                found = response.css(selector)
                if found:
                    articles = found
                    self.logger.info(f"✅ Հոդվածներ գտնվեցին selector-ով: {selector}")
                    break
            except Exception as e:
                continue
        
        # If still no articles, try broader search
        if not articles:
            # Look for any links that might be articles based on URL patterns
            all_links = response.css("a[href]")
            potential_articles = []
            for link in all_links:
                href = link.css("::attr(href)").get()
                if href and any(pattern in href for pattern in ['/news/', '/article/', '/post/', '/2024/', '/2025/']):
                    potential_articles.append(link)
            articles = potential_articles
            self.logger.info(f"🔍 Գտնվել է {len(articles)} հավանական հոդվածներ URL pattern-ներով")
        
        # Limit to latest 10 articles only for optimization (running every 10 minutes)
        articles = articles[:10]
        
        self.logger.info(f"📰 Գտնվել է {len(articles)} հոդված (սահմանափակված 10-ով)")

        for article in articles:
            # Extract link from news title - try multiple selectors
            link = (article.css("a.news_title::attr(href)").get() or
                   article.css("a::attr(href)").get() or
                   article.attrib.get('href'))  # If article is already an 'a' element
            
            title_preview = (article.css("a.news_title::text").get() or
                           article.css("a::text").get() or
                           article.css("::text").get())  # If article is already an 'a' element
            
            if link and title_preview:
                # Make URL absolute
                full_url = response.urljoin(link)
                
                # Check Redis cache first
                if self.is_article_processed(full_url, title_preview):
                    self.cached_skips += 1
                    continue
                    
                # Use Selenium for individual articles too
                yield scrapy.Request(full_url, callback=self.parse_article_with_selenium)

        # Pagination removed - only processing latest 10 articles for optimization


    def parse_article_with_selenium(self, response):
        """Parse article page using Selenium to get JavaScript-rendered content"""
        if not self.driver:
            self.logger.error("❌ Selenium driver չկա, սովորական parsing")
            yield from self.parse_article(response)
            return
        
        # Get page content with Selenium
        html_content = self.get_page_with_selenium(response.url)
        if not html_content:
            self.logger.error(f"❌ Selenium չկարողացավ բեռնել: {response.url}")
            return
        
        # Create a new response object with Selenium content
        from scrapy.http import HtmlResponse
        selenium_response = HtmlResponse(
            url=response.url,
            body=html_content,
            encoding='utf-8'
        )
        
        yield from self.parse_article(selenium_response)

    def parse_article(self, response):
        self.processed_articles += 1

        # Check if this is a redirect to main page (common issue with aysor.am)
        if response.url == "https://www.aysor.am/am" or "aysor.am/am" == response.url.rstrip('/'):
            self.logger.warning(f"🔄 Article redirected to main page: {response.url}")
            return
        
        # Try multiple title selectors for aysor.am (with Selenium-loaded content)
        title_selectors = [
            "h1::text",
            ".article_title::text",
            ".news_title::text", 
            "h2::text",
            "meta[property='og:title']::attr(content)",
            ".title::text",
            ".article-title::text",
            ".post-title::text",
            "h1.entry-title::text",
            ".entry-header h1::text",
            ".main-title::text"
        ]
        
        title = None
        for selector in title_selectors:
            try:
                title = response.css(selector).get()
                if title and title.strip():
                    break
            except:
                continue
        
        # If no proper title found, try URL decoding
        if not title or title.strip() == "Այսօր` թարմ լուրեր Հայաստանից":
                                # Extract title from the URL if needed
            url_title = unquote(response.url.split('/')[-2]) if len(response.url.split('/')) > 2 else None
            if url_title and len(url_title) > 3:
                title = url_title
                self.logger.info(f"📝 Title extracted from URL: {title}")
        
        # If still generic title, skip
        if not title or title.strip() == "Այսօր` թարմ լուրեր Հայաստանից":
            self.logger.warning(f"⚠️ Generic title detected, skipping: {response.url}")
            return
        
        # Clean title
        if title:
            title = title.strip()
        
        # Try multiple content selectors for aysor.am (enhanced for JavaScript content)
        content_selectors = [
            "div.article_content ::text",
            ".news_content ::text",
            ".content ::text",
            ".article_text ::text",
            "div.news_text ::text",
            ".main_content ::text",
            ".article-content ::text",
            ".post-content ::text",
            ".entry-content ::text",
            ".main-text ::text",
            ".content-text ::text",
            "p::text"
        ]
        
        content_parts = []
        for selector in content_selectors:
            try:
                parts = response.css(selector).getall()
                if parts:
                    content_parts = parts
                    break
            except:
                continue
        
        content = "\n".join([p.strip() for p in content_parts if p.strip()])

        # Extract scraped time - aysor.am has specific date format
        time_selectors = [
            '.news_date::text',
            '.date::text',
            'time::attr(datetime)',
            'time::text',
            '.publish-date::text',
            '.article-date::text',
            '.post-date::text',
            'meta[property="article:published_time"]::attr(content)'
        ]
        
        scraped_time = None
        for selector in time_selectors:
            try:
                scraped_time = response.css(selector).get()
                if scraped_time:
                    break
            except:
                continue
        
        if not scraped_time:
            scraped_time = datetime.now().isoformat()

        # Clean title for display
        display_title = title[:60] + "..." if title and len(title) > 60 else title or "Անանուն հոդված"
        
        # Check for keywords in title or content
        title_has_keyword = self.article_contains_keyword(title) if title else False
        content_has_keyword = self.article_contains_keyword(content) if content else False
        
        if title_has_keyword or content_has_keyword:
            keyword_source = "title" if title_has_keyword else "content"
            self.logger.info(f"✅ Բանալի բառ գտնվեց ({keyword_source}): {display_title}")
            
            # Mark as processed only after successful keyword match
            self.mark_article_processed(response.url, title)
            self.new_articles += 1
            
            item = NewsScraperItem()
            item['title'] = title or f'Article from {response.url.split("/")[-1] or response.url.split("/")[-2]}'
            item['link'] = response.url
            item['source_url'] = response.url
            item['content'] = content or f"Հոդված: {title}"  # Use title as content if no content
            item['scraped_time'] = scraped_time
            yield item
        else:
            self.logger.info(f"❌ Բանալի բառ չգտնվեց: {display_title}")
            # Mark as processed even if no keyword match to avoid re-checking
            self.mark_article_processed(response.url, title)

    def closed(self, reason):
        """Called when spider finishes"""
        # Clean up Selenium driver
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("🚗 Selenium driver փակված է")
            except Exception as e:
                self.logger.warning(f"⚠️ Selenium driver cleanup error: {e}")
        
        self.logger.info(f"""
📊 ԱՄՓՈՓՈՒՄ AYSOR.AM (Selenium-ով, 10 հոդված):
   • Ստուգված հոդվածներ: {self.processed_articles}
   • Նոր հոդվածներ: {self.new_articles}
   • Կրկնություն հոդվածներ: {self.duplicate_articles}
   • Cache-ից բաց թողնված: {self.cached_skips}
   • Selenium driver: {'✅ Օգտագործվել է' if self.driver else '❌ Չի աշխատել'}
   • Սկրիպտի աշխատանքը: ✅ Ավարտված
        """.strip()) 