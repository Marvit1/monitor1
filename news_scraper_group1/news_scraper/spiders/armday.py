import scrapy
from news_scraper.items import NewsScraperItem
import os
import hashlib
import redis
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException
import time
import requests
import gc
import psutil

class ArmDaySpider(scrapy.Spider):
    name = "armday"
    allowed_domains = ["armday.am"]
    start_urls = ["https://armday.am/lrahos"]
    
    # Add custom headers to bypass potential blocking
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        },
        # Memory optimization settings
        'CONCURRENT_REQUESTS': 1,  # Process one request at a time
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'DOWNLOAD_DELAY': 1,  # 1 second delay between requests
        'RANDOMIZE_DOWNLOAD_DELAY': 0.5,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 1,
        'AUTOTHROTTLE_MAX_DELAY': 3,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.0,
        'AUTOTHROTTLE_DEBUG': False,
        # Disable features that consume memory
        'DOWNLOAD_TIMEOUT': 30,
        'RETRY_TIMES': 1,  # Reduce retries
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408],
        'COOKIES_ENABLED': False,  # Disable cookies to save memory
        'TELNETCONSOLE_ENABLED': False,  # Disable telnet console
        'LOG_LEVEL': 'INFO',  # Reduce logging
    }

    def __init__(self, *args, **kwargs):
        super(ArmDaySpider, self).__init__(*args, **kwargs)
        
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
        self.duplicate_articles = 0  # Add missing counter used by pipeline
        self.cached_skips = 0
        
        # Memory management
        self.articles_since_restart = 0
        self.max_articles_before_restart = 20  # Restart driver every 20 articles
        
    def setup_selenium(self):
        """Setup Selenium WebDriver with optimal settings for memory usage"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # Run in background
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1280,720')  # Smaller window
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Memory optimization options
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-images')  # Don't load images
            chrome_options.add_argument('--disable-javascript')  # Disable JS if not needed
            chrome_options.add_argument('--disable-css')  # Disable CSS if not needed
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            chrome_options.add_argument('--memory-pressure-off')
            chrome_options.add_argument('--max_old_space_size=512')  # Limit memory usage
            
            # Try to initialize Chrome driver
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.logger.info("🚗 Selenium Chrome driver կապակցված է (memory optimized)")
            
        except Exception as e:
            self.logger.error(f"❌ Selenium setup failed: {e}")
            self.driver = None
    
    def restart_driver(self):
        """Restart Selenium driver to free memory"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("🔄 Restarting Selenium driver for memory cleanup")
            except Exception as e:
                self.logger.warning(f"⚠️ Driver quit error: {e}")
        
        # Reset counter
        self.articles_since_restart = 0
        
        # Setup new driver
        self.setup_selenium()
    
    def log_memory_usage(self):
        """Log current memory usage"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            self.logger.info(f"💾 Memory usage: {memory_mb:.1f} MB")
            return memory_mb
        except Exception as e:
            self.logger.warning(f"⚠️ Memory monitoring error: {e}")
            return 0

    def get_page_with_selenium(self, url):
        """Get page content using Selenium with memory optimization"""
        if not self.driver:
            self.logger.error("❌ Selenium driver չկա")
            return None
            
        try:
            self.logger.info(f"🌐 Selenium-ով բեռնվում է: {url}")
            
            # Clear browser cache and memory before loading new page
            self.driver.delete_all_cookies()
            self.driver.execute_script("window.localStorage.clear();")
            self.driver.execute_script("window.sessionStorage.clear();")
            
            self.driver.get(url)
            
            # Wait for content to load (reduced wait time)
            time.sleep(2)
            
            # Wait for specific elements that indicate content is loaded
            try:
                WebDriverWait(self.driver, 8).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
            except TimeoutException:
                self.logger.warning("⏰ Page load timeout")
            
            # Get page source and immediately clear memory
            page_source = self.driver.page_source
            
            # Clear memory after getting content
            self.driver.execute_script("""
                // Clear DOM elements to free memory
                var elements = document.querySelectorAll('*');
                for(var i = 0; i < elements.length; i++) {
                    if(elements[i].tagName !== 'HTML' && elements[i].tagName !== 'HEAD' && elements[i].tagName !== 'BODY') {
                        elements[i].innerHTML = '';
                    }
                }
            """)
            
            return page_source
            
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
        cache_key = f"processed_armday:{article_hash}"
        return self.redis_client.exists(cache_key)

    def mark_article_processed(self, url, title):
        """Mark article as processed in Redis cache"""
        if not self.redis_client:
            return
        # Create unique hash for article
        article_hash = hashlib.md5(f"{url}:{title}".encode()).hexdigest()
        cache_key = f"processed_armday:{article_hash}"
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
        # Extract articles using enhanced selectors for JavaScript-loaded content
        selectors_to_try = [
            "div.medium-article-list div.item",
            "div.item",
            "article",
            ".article",
            ".news-item",
            ".news_item",
            "a[href*='/news/']",
            "a[href*='/article/']",
            "div[class*='news'] a",
            "div[class*='article'] a",
            ".main-content a",
            ".content a",
            ".container a",
            "ul li a",
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
        
        self.logger.info(f"📰 Գտնվել է {len(articles)} հոդված (օպտիմիզացված - սահմանափակված 10-ով)")
        
        # Limit to latest 10 articles only for optimization (running every 10 minutes)
        articles = articles[:10]

        for article in articles:
            # Extract link and title using multiple selectors
            link = (article.css("div.item-header a::attr(href)").get() or
                   article.css("div.item-content h4 a::attr(href)").get() or
                   article.css("a::attr(href)").get() or
                   article.attrib.get('href'))
            
            title_preview = (article.css("div.item-content h4 a::text").get() or
                           article.css("div.item-header a::text").get() or
                           article.css("a::text").get() or
                           article.css("::text").get())
            
            if link and title_preview:
                full_url = response.urljoin(link)
                
                # Check Redis cache first
                if self.is_article_processed(full_url, title_preview):
                    self.cached_skips += 1
                    continue
                    
                # Use Selenium for individual articles too
                yield scrapy.Request(full_url, callback=self.parse_article_with_selenium)
    
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
        self.articles_since_restart += 1
        
        # Check if we need to restart driver for memory cleanup
        if self.articles_since_restart >= self.max_articles_before_restart:
            self.logger.info(f"🔄 Memory cleanup: processed {self.articles_since_restart} articles, restarting driver")
            self.restart_driver()

        # Try multiple title selectors (enhanced for JavaScript content)
        title_selectors = [
            "h1::text",
            ".entry-title::text",
            ".post-title::text",
            "meta[property='og:title']::attr(content)",
            "title::text",
            ".title::text",
            ".article-title::text",
            ".news-title::text",
            "h2::text",
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
        
        # Optimized content selectors - only get main article content
        content_selectors = [
            "div.entry-content p::text",
            ".post-content p::text",
            ".article-content p::text",
            ".article-body p::text",
            ".article-text p::text",
            ".main-content p::text",
            ".news-content p::text",
            ".text-content p::text",
            "article p::text"
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
        
        # Clean content - remove navigation, ads, and other unwanted elements
        if not content_parts:
            # Fallback to all p tags if specific selectors fail
            content_parts = response.css("p::text").getall()
        
        # Filter out unwanted content
        filtered_content = []
        unwanted_phrases = [
            "կարդալ ավելին",
            "կարդալ ավելի",
            "ավելին",
            "կարդալ",
            "share",
            "like",
            "follow",
            "subscribe",
            "կիսվել",
            "հավանել",
            "տեսնել ավելին",
            "բաժանորդագրվել",
            "facebook",
            "twitter",
            "instagram",
            "կապ",
            "contact",
            "մեկնաբանություն",
            "comment",
            "tag",
            "պիտակ",
            "category",
            "կատեգորիա",
            "author",
            "հեղինակ",
            "date",
            "ամսաթիվ",
            "մարտ",
            "ապրիլ",
            "մայիս",
            "հունիս",
            "հուլիս",
            "օգոստոս",
            "սեպտեմբեր",
            "հոկտեմբեր",
            "նոյեմբեր",
            "դեկտեմբեր",
            "փետրվար",
            "հունվար",
            "copyright",
            "© ",
            "all rights reserved",
            "բոլոր իրավունքները",
            "advertisement",
            "գովազդ",
            "դասակարգիչ",
            "որպես",
            "Click here",
            "Մանրամասն",
            "Ավելի տեղեկություն",
            "Տեղեկություն",
            "Կարծիք",
            "Գրել",
            "Այլ"
        ]
        
        for part in content_parts:
            if part and len(part.strip()) > 10:  # Only keep meaningful content
                clean_part = part.strip()
                
                # Check if content contains unwanted phrases
                is_unwanted = False
                for phrase in unwanted_phrases:
                    if phrase.lower() in clean_part.lower():
                        is_unwanted = True
                        break
                
                # Skip short or unwanted content
                if not is_unwanted and len(clean_part) > 20:
                    filtered_content.append(clean_part)
        
        # Join filtered content
        content = "\n".join(filtered_content)
        
        # Additional content cleaning - remove empty lines and extra spaces
        content_lines = [line.strip() for line in content.split('\n') if line.strip()]
        content = "\n".join(content_lines)

        # Extract scraped time - try multiple selectors
        time_selectors = [
            'time::attr(datetime)',
            'time::text',
            '.date::text',
            '.publish-date::text',
            '.article-date::text',
            '.post-date::text',
            '.timestamp::text',
            '.meta-date::text',
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
        
        # Only process if we have meaningful content
        if content and len(content.strip()) > 50:  # Ensure minimum content length
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
        else:
            self.logger.info(f"⚠️ Անբավարար պարունակություն: {display_title}")
            # Mark as processed to avoid re-checking
            self.mark_article_processed(response.url, title)
        
        # Memory cleanup after each article
        gc.collect()  # Force garbage collection
        
        # Log memory usage every 5 articles
        if self.processed_articles % 5 == 0:
            self.log_memory_usage()

    def closed(self, reason):
        """Called when spider finishes"""
        # Clean up Selenium driver
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("🚗 Selenium driver փակված է")
            except Exception as e:
                self.logger.warning(f"⚠️ Selenium driver cleanup error: {e}")
        
        # Final memory cleanup
        gc.collect()
        final_memory = self.log_memory_usage()
        
        self.logger.info(f"""
📊 ԱՄՓՈՓՈՒՄ ARMDAY.AM (Selenium-ով, 10 հոդված):
   • Ստուգված հոդվածներ: {self.processed_articles}
   • Նոր հոդվածներ: {self.new_articles}
   • Կրկնություն հոդվածներ: {self.duplicate_articles}
   • Cache-ից բաց թողնված: {self.cached_skips}
   • Selenium driver: {'✅ Օգտագործվել է' if self.driver else '❌ Չի աշխատել'}
   • Հիշողության օգտագործում: {final_memory:.1f} MB
   • Սկրիպտի աշխատանքը: ✅ Ավարտված
        """.strip()) 