import scrapy
from news_scraper.items import NewsScraperItem
import sys
import os
import hashlib
import redis
from datetime import datetime
import random
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import requests

class PanoramaSpider(scrapy.Spider):
    name = "panorama"
    allowed_domains = ["panorama.am"]
    start_urls = ["https://www.panorama.am/am"]

    def __init__(self, *args, **kwargs):
        super(PanoramaSpider, self).__init__(*args, **kwargs)
        
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
        self.cached_skips = 0
        self.blocked_attempts = 0
        self.duplicate_articles = 0
        
        # Setup Chrome WebDriver
        self.driver = None
        self.setup_driver()

    def setup_driver(self):
        """Setup Chrome WebDriver with anti-detection measures"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # User agent randomization
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
            chrome_options.add_argument(f'--user-agent={random.choice(user_agents)}')
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Additional anti-detection
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.logger.info("🌐 Chrome WebDriver սկսված է")
            
        except Exception as e:
            self.logger.error(f"❌ WebDriver սկսելու սխալ: {e}")
            self.driver = None

    def is_article_processed(self, url, title):
        """Check if article was already processed using Redis cache"""
        if not self.redis_client:
            return False
        # Create unique hash for article
        article_hash = hashlib.md5(f"{url}:{title}".encode()).hexdigest()
        cache_key = f"processed_panorama:{article_hash}"
        return self.redis_client.exists(cache_key)

    def mark_article_processed(self, url, title):
        """Mark article as processed in Redis cache"""
        if not self.redis_client:
            return
        # Create unique hash for article
        article_hash = hashlib.md5(f"{url}:{title}".encode()).hexdigest()
        cache_key = f"processed_panorama:{article_hash}"
        # Mark as processed (expire in 7 days)
        self.redis_client.setex(cache_key, 604800, "1")

    def article_contains_keyword(self, article_text):
        if not article_text:
            self.logger.debug("🔍 Հոդծի տեքստ դատարկ է")
            return False
        if not self.keywords:
            self.logger.debug("🔍 Բանալի բառեր չկան, բոլորն ընդունում")
            return True
        
        article_lower = article_text.lower()
        for keyword in self.keywords:
            if keyword in article_lower:
                self.logger.info(f"🔍 Գտնվեց բանալի բառ: '{keyword}'")
                return True
        
        self.logger.info(f"🔍 Բանալի բառ չգտավ: {self.keywords}")
        return False

    def save_item_to_database(self, item):
        """Save item directly to database as fallback"""
        try:
            from main.models import NewsArticle
            
            # Check if article already exists
            existing = NewsArticle.objects.filter(
                source_url=item['source_url']
            ).first()
            
            if not existing:
                article = NewsArticle(
                    title=item['title'],
                    link=item['link'],
                    source_url=item['source_url'],
                    content=item['content'],
                    scraped_time=item['scraped_time']
                )
                article.save()
                self.logger.info(f"💾 Հոդված պահպանվեց database-ում: {item['title'][:50]}...")
            else:
                self.logger.info(f"🔄 Հոդված արդեն գոյություն ունի: {item['title'][:50]}...")
                
        except Exception as e:
            self.logger.error(f"❌ Database պահպանման սխալ: {e}")

    def process_item_through_pipeline(self, item):
        """Process item through scrapy pipeline"""
        try:
            from news_scraper.pipelines import NewsScraperPipeline
            pipeline = NewsScraperPipeline()
            pipeline.process_item(item, self)
        except Exception as e:
            self.logger.warning(f"⚠️ Pipeline սխալ: {e}")
            # Fallback to direct database save
            self.save_item_to_database(item)

    def start_requests(self):
        """Override to skip normal HTTP requests and use Selenium only"""
        # Run Selenium parsing directly
        self.selenium_parse()
        return []

    def parse(self, response):
        """This method won't be called - Selenium parsing is done directly"""
        pass

    def selenium_parse(self):
        """Main parsing method using Selenium"""
        if not self.driver:
            self.logger.error("❌ WebDriver չկա")
            return
        
        try:
            # Navigate to panorama.am
            self.logger.info("🔍 PANORAMA.AM բեռնում...")
            self.driver.get("https://www.panorama.am/am")
            time.sleep(random.uniform(3, 5))
            
            # Check if page loaded successfully
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except TimeoutException:
                self.logger.error("❌ Էջը չբեռնվեց")
                return
            
            # Human-like scrolling
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
            time.sleep(2)
            
            # Find article links
            article_links = []
            try:
                # Try different selectors for panorama.am
                selectors = [
                    "div.news_block a",
                    "a[href*='/news/']",
                    "a[href*='/arm/']",
                    ".news-item a",
                    ".news-block a"
                ]
                
                for selector in selectors:
                    try:
                        links = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if links:
                            article_links = links[:10]  # Limit to 10 articles
                            self.logger.info(f"📰 {len(article_links)} հոդված գտնվեց ({selector})")
                            break
                    except:
                        continue
                
                if not article_links:
                    # Fallback - get all armenian article links
                    all_links = self.driver.find_elements(By.TAG_NAME, "a")
                    for link in all_links:
                        try:
                            href = link.get_attribute("href")
                            if href and ("panorama.am" in href and ("/arm/" in href or "/news/" in href)):
                                article_links.append(link)
                                if len(article_links) >= 10:
                                    break
                        except:
                            continue
                    
                    self.logger.info(f"📰 Fallback: {len(article_links)} հոդված գտնվեց")
                
            except Exception as e:
                self.logger.error(f"❌ Հոդվածների հղումները գտնելու սխալ: {e}")
                return
            
            # Extract URL and title data first to avoid stale element errors
            article_data = []
            for i, link in enumerate(article_links):
                try:
                    article_url = link.get_attribute("href")
                    if not article_url:
                        continue
                    
                    # Get article title from link text
                    article_title = ""
                    try:
                        title_text = link.text.strip()
                        title_attr = link.get_attribute("title") or ""
                        aria_label = link.get_attribute("aria-label") or ""
                        
                        # Use the longest meaningful text
                        candidates = [title_text, title_attr, aria_label]
                        for candidate in candidates:
                            if candidate and len(candidate) > len(article_title) and len(candidate) > 5:
                                article_title = candidate
                        
                        # Clean title
                        if article_title:
                            article_title = article_title.replace("Պանորամա", "").replace("Panorama", "").strip()
                            article_title = article_title.replace(" | ", " ").strip()
                        
                        # Fallback to URL-based title
                        if not article_title or len(article_title) <= 5:
                            article_title = f"Հոդված #{i+1} - {article_url.split('/')[-1]}"
                        
                    except Exception as e:
                        article_title = f"Հոդված #{i+1} - {article_url.split('/')[-1]}"
                    
                    article_data.append({
                        'url': article_url,
                        'title': article_title,
                        'index': i+1
                    })
                    
                except Exception as e:
                    self.logger.warning(f"⚠️ Հղման տվյալների քաշման սխալ: {e}")
                    continue
            
            # Process each article with stable data
            processed_urls = set()
            for article in article_data:
                try:
                    if article['url'] in processed_urls:
                        continue
                    
                    processed_urls.add(article['url'])
                    
                    # Check cache
                    if self.is_article_processed(article['url'], article['title']):
                        self.cached_skips += 1
                        continue
                    
                    # Process article
                    self.process_article_with_selenium(article['url'], article['title'])
                    
                    # Delay between articles
                    time.sleep(random.uniform(2, 4))
                    
                except Exception as e:
                    self.logger.warning(f"⚠️ Հղման մշակման սխալ: {e}")
                    continue

                except Exception as e:
                    self.logger.warning(f"⚠️ Հղման մշակման սխալ: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"❌ Parsing սխալ: {e}")
            self.blocked_attempts += 1

    def process_article_with_selenium(self, url, preview_title):
        """Process individual article using Selenium"""
        try:
            self.logger.info(f"🔍 Բեռնում: {url}")
            
            # Navigate to article
            self.driver.get(url)
            time.sleep(random.uniform(2, 4))
            
            # Wait for content to load
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except TimeoutException:
                self.logger.warning(f"⏰ Timeout: {url}")
                return
            
            self.processed_articles += 1

            # Extract title with better selectors for panorama.am
            title = None
            try:
                title_selectors = [
                    "h1.article-title",
                    "h1.post-title",
                    "h1.entry-title",
                    "h1.news-title",
                    "h1",
                    ".article-title",
                    ".post-title",
                    ".entry-title",
                    ".news-title",
                    "title",
                    "meta[property='og:title']"
                ]
                for selector in title_selectors:
                    try:
                        if selector == "title":
                            title_element = self.driver.find_element(By.TAG_NAME, "title")
                        elif selector == "meta[property='og:title']":
                            title_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                            title = title_element.get_attribute("content")
                            if title and title.strip():
                                break
                            continue
                        else:
                            title_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        
                        if title_element.text.strip():
                            title = title_element.text.strip()
                            # Clean title from site name
                            title = title.replace("Պանորամա", "").replace("Panorama", "").strip()
                            title = title.replace(" | ", " ").replace(" - ", " ").strip()
                            if title and len(title) > 5:  # Ensure meaningful title
                                break
                    except:
                        continue
            except:
                pass
            
            # Fallback to preview title only if no better title found
            if not title or len(title) <= 5:
                title = preview_title
                if title:
                    title = title.replace("Պանորամա", "").replace("Panorama", "").strip()
            
            # Final fallback
            if not title or len(title) <= 5:
                title = f"Panorama.am հոդված - {url.split('/')[-1]}"
            
            # Extract content with advanced filtering for panorama.am
            content_parts = []
            try:
                content_selectors = [
                    "div.post-content p",
                    "div.entry-content p",
                    "div.article-content p",
                    "div.content p",
                    "div.text p",
                    "article p",
                    "div.post-body p",
                    "div.news-content p",
                    "div.news-text p",
                    "main p",
                    ".post-content p",
                    ".entry-content p",
                    ".article-content p"
                ]
                
                for selector in content_selectors:
                    try:
                        paragraphs = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if paragraphs:
                            content_parts = [p.text.strip() for p in paragraphs if p.text.strip()]
                            break
                    except:
                        continue
                
                # Fallback to all paragraphs
                if not content_parts:
                    paragraphs = self.driver.find_elements(By.TAG_NAME, "p")
                    content_parts = [p.text.strip() for p in paragraphs if p.text.strip()]
                
            except Exception as e:
                self.logger.warning(f"⚠️ Content extraction սխալ: {e}")
                content_parts = []
            
            # Advanced content filtering
            unwanted_phrases = [
                "կարդալ ավելին", "կարդալ ավելի", "ավելին", "կարդալ",
                "տեսնել ավելին", "մանրամասն", "ավելի տեղեկություն",
                "more", "read more", "continue reading", "click here",
                "share", "like", "follow", "subscribe", "կիսվել", "հավանել",
                "բաժանորդագրվել", "facebook", "twitter", "instagram", "youtube",
                "կապ", "contact", "author", "հեղինակ", "email", "phone",
                "copyright", "© ", "all rights reserved", "բոլոր իրավունքները",
                "մեկնաբանություն", "comment", "reply", "respond", "discuss",
                "tag", "պիտակ", "category", "կատեգորիա", "նմանապես",
                "related", "հարակից", "կապված", "նույն բաժնից",
                "advertisement", "գովազդ", "sponsored", "promo", "ad",
                "panorama.am", "panorama", "պանորամա", "լուր", "լրատվություն",
                "menu", "մենյու", "navigation", "նավիգացիա", "home", "տուն",
                "search", "որոնում", "find", "filter", "ֆիլտր",
                "popular", "հայտնի", "trending", "թրենդ", "hot", "տաք",
                "recent", "վերջին", "latest", "նոր", "fresh", "թարմ",
                "more news", "ավելի լուրեր", "other articles", "այլ հոդվածներ"
            ]
            
            # Filter content
            filtered_content = []
            for part in content_parts:
                if part and len(part.strip()) > 15:
                    clean_part = part.strip()
                    
                    # Skip if contains unwanted phrases
                    is_unwanted = False
                    for phrase in unwanted_phrases:
                        if phrase.lower() in clean_part.lower():
                            is_unwanted = True
                            break
                    
                    # Skip very short content
                    if len(clean_part) < 20:
                        is_unwanted = True
                    
                    # Skip if mostly numbers/dates
                    if len([c for c in clean_part if c.isdigit()]) > len(clean_part) * 0.3:
                        is_unwanted = True
                    
                    # Skip if contains too many special characters
                    special_chars = len([c for c in clean_part if c in '©®™@#$%^&*()_+-=[]{}|;:,.<>?'])
                    if special_chars > len(clean_part) * 0.1:
                        is_unwanted = True
                    
                    if not is_unwanted:
                        filtered_content.append(clean_part)
            
            # Join and final cleaning
            content = "\n".join(filtered_content)
            content_lines = [line.strip() for line in content.split('\n') if line.strip() and len(line.strip()) > 10]
            content = "\n".join(content_lines)

            # Display title for logging
            display_title = title[:60] + "..." if title and len(title) > 60 else title or "Անանուն հոդված"
            
            # Only process if we have meaningful content
            if content and len(content.strip()) > 100:
                full_text = f"{title or ''} {content}".strip()
                
                # Debug logging
                self.logger.info(f"🔍 Հոդվածի տեքստ ստուգվում է: {display_title}")
                self.logger.info(f"🔍 Տեքստի երկարություն: {len(full_text)} նիշ")
                
                if self.article_contains_keyword(full_text):
                    self.logger.info(f"✅ Բանալի բառ գտնվեց: {display_title}")
                    self.mark_article_processed(url, title)
                    self.new_articles += 1
                    
                    # Create item and process through pipeline
                    item = NewsScraperItem()
                    item['title'] = title or f'Panorama.am հոդված'
                    item['link'] = url
                    item['source_url'] = url
                    item['content'] = content
                    item['scraped_time'] = datetime.now().isoformat()
                    
                    # Process through pipeline
                    self.process_item_through_pipeline(item)
                    
                else:
                    self.logger.info(f"❌ Բանալի բառ չգտնվեց: {display_title}")
                    self.mark_article_processed(url, title)
            else:
                self.logger.info(f"⚠️ Անբավարար պարունակություն: {display_title}")
                self.logger.info(f"⚠️ Պարունակության երկարություն: {len(content.strip()) if content else 0} նիշ")
                self.mark_article_processed(url, title)
                
        except Exception as e:
            self.logger.error(f"❌ Հոդվածի մշակման սխալ: {e}")

    def parse_article(self, response):
        """This method is no longer used - Selenium parsing is done directly"""
        pass

    def closed(self, reason):
        """Called when spider finishes"""
        # Close Selenium WebDriver
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("🔒 WebDriver փակվեց")
            except:
                pass
            
        self.logger.info(f"""
📊 ԱՄՓՈՓՈՒՄ PANORAMA.AM (Selenium միայն):
   • Ստուգված հոդվածներ: {self.processed_articles}
   • Նոր հոդվածներ: {self.new_articles}
   • Cache-ից բաց թողնված: {self.cached_skips}
   • Բլոկավորման փորձեր: {self.blocked_attempts}
   • Սկրիպտի աշխատանքը: ✅ Ավարտված
        """.strip())