# Define your item pipelines here
# Safe version that works even if API endpoints don't exist

import logging
import requests
import json
import os
import hashlib
import redis
from datetime import datetime
from itemadapter import ItemAdapter

class NewsScraperPipeline:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_base_url = os.environ.get('API_BASE_URL', 'https://beackkayq.onrender.com')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'NewsMonitor/1.0'
        })
        self.api_working = True  # Track if API is working
        
        # Fallback keywords if API is not available - match API format
        self.fallback_keywords = [
            {"id": 1, "word": "Հայաստան"},
            {"id": 2, "word": "Երևան"},
            {"id": 3, "word": "Նիկոլ Փաշինյան"},
            {"id": 4, "word": "Կառավարություն"},
            {"id": 5, "word": "Պատգամավոր"},
            {"id": 6, "word": "Բանակ"},
            {"id": 7, "word": "Սահման"},
            {"id": 8, "word": "Տնտեսություն"},
            {"id": 9, "word": "Կրթություն"},
            {"id": 10, "word": "Առողջապահություն"}
        ]

    def process_item(self, item, spider):
        try:
            # Skip API calls if API is not working
            if not self.api_working:
                self.logger.info(f"🚫 API չի աշխատում, հոդվածը չի պահպանվում: {item['title'][:60]}...")
                return item

            # Check if article already exists via API (skip if API not working)
            # Note: Check endpoints don't work, so we'll rely on save endpoint's duplicate detection
            
            # Get keywords via API with fallback
            keywords = []
            try:
                # Try multiple endpoints for keywords
                keyword_endpoints = [
                    f"{self.api_base_url}/api/keywords/",
                    f"{self.api_base_url}/api/keywords",
                    f"{self.api_base_url}/keywords/",
                    f"{self.api_base_url}/keywords"
                ]
                
                all_keywords = []
                for endpoint in keyword_endpoints:
                    try:
                        response = self.session.get(endpoint, timeout=10)
                        if response.status_code == 200:
                            all_keywords = response.json()
                            self.logger.info(f"✅ Keywords ստացվեցին {endpoint}-ից")
                            break
                        elif response.status_code == 404:
                            self.logger.warning(f"⚠️ Endpoint չի գտնվել՝ {endpoint}")
                            continue
                    except Exception as e:
                        self.logger.warning(f"⚠️ Network error {endpoint}: {e}")
                        continue
                
                # Use fallback keywords if API failed
                if not all_keywords:
                    self.logger.warning("⚠️ API keywords չաշխատեց, օգտագործում ենք fallback")
                    all_keywords = self.fallback_keywords
                    self.api_working = False
                
                # Handle API response format - extract results if it's a dictionary
                if isinstance(all_keywords, dict) and 'results' in all_keywords:
                    all_keywords = all_keywords['results']
                    self.logger.info(f"✅ Extracted {len(all_keywords)} keywords from API response")
                
                # Match keywords in article
                article_text = f"{item.get('title', '')} {item.get('content', '')}".lower()
                self.logger.info(f"🔍 Ստուգվում են {len(all_keywords)} բանալի բառ հոդվածի մեջ...")
                
                # Debug: print first few keywords
                if all_keywords and len(all_keywords) > 0:
                    self.logger.info(f"🔍 Debug: First keyword: {all_keywords[0]}")
                
                # Check if all_keywords is a list of objects or just a list
                if all_keywords and isinstance(all_keywords, list):
                    if len(all_keywords) > 0 and isinstance(all_keywords[0], dict):
                        # It's a list of objects with 'word' key
                        for keyword_obj in all_keywords:
                            keyword_lower = keyword_obj.get('word', '').lower().strip()
                            if keyword_lower and keyword_lower in article_text:
                                # Avoid duplicates
                                if keyword_obj.get('word') not in keywords:
                                    keywords.append(keyword_obj.get('word'))
                                    self.logger.info(f"✅ Բանալի բառ գտնվեց: '{keyword_obj.get('word')}'")
                    else:
                        # It's a list of strings
                        for keyword_str in all_keywords:
                            keyword_lower = keyword_str.lower().strip()
                            if keyword_lower and keyword_lower in article_text:
                                # Avoid duplicates
                                if keyword_str not in keywords:
                                    keywords.append(keyword_str)
                                    self.logger.info(f"✅ Բանալի բառ գտնվեց: '{keyword_str}'")
                
                if keywords:
                    self.logger.info(f"🔑 Ընդամենը գտնվեց {len(keywords)} բանալի բառ: {', '.join(keywords)}")
                else:
                    self.logger.info("❌ Բանալի բառեր չգտնվեցին")
                        
            except Exception as e:
                self.logger.warning(f"Keywords matching error: {e}")
                self.api_working = False
                return item

            # Save article via API ONLY if keywords were found and API is working
            if keywords and len(keywords) > 0 and self.api_working:
                try:
                    article_data = {
                        'title': item['title'],
                        'link': item['link'],
                        'source_url': item.get('source_url', item['link']),
                        'content': item.get('content', ''),
                        'scraped_time': item.get('scraped_time', ''),
                        'keywords': keywords
                    }
                    
                    # Debug: print article data being sent
                    self.logger.info(f"🔍 Debug: Sending article data: {article_data}")
                    
                    # Try multiple endpoints for saving articles
                    save_endpoints = [
                        f"{self.api_base_url}/api/articles/",
                        f"{self.api_base_url}/api/articles",
                        f"{self.api_base_url}/articles/",
                        f"{self.api_base_url}/articles"
                    ]
                    
                    article_saved = False
                    for endpoint in save_endpoints:
                        try:
                            response = self.session.post(
                                endpoint,
                                json=article_data,
                                timeout=10
                            )
                            
                            if response.status_code == 201:
                                spider.new_articles += 1
                                self.logger.info(f"💾 Նոր հոդված պահպանվեց {len(keywords)} բանալի բառով: {item['title'][:60]}...")
                                article_saved = True
                                
                                # Send Telegram notification directly via bot token
                                try:
                                    bot_token = "8151695933:AAGeY8Rgqz4_ERUATORGvdnimEvFQwHqdwc"
                                    chat_id = "-1002802141303"  # Monitor group ID
                                    
                                    # Create message
                                    message = f"📰 **Նոր հոդված գտնվեց!**\n\n"
                                    message += f"**Վերնագիր:** {item['title']}\n"
                                    message += f"**Հղում:** {item['link']}\n"
                                    message += f"**Բանալի բառեր:** {', '.join(keywords)}"
                                    
                                    telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                                    telegram_data = {
                                        'chat_id': chat_id,
                                        'text': message,
                                        'parse_mode': 'Markdown',
                                        'disable_web_page_preview': False
                                    }
                                    
                                    response = self.session.post(telegram_url, json=telegram_data, timeout=10)
                                    if response.status_code == 200:
                                        self.logger.info(f"📤 Telegram ծանուցում ուղարկվեց {len(keywords)} բանալի բառով")
                                    else:
                                        self.logger.warning(f"⚠️ Telegram error: {response.status_code}")
                                        
                                except Exception as e:
                                    self.logger.warning(f"⚠️ Telegram ծանուցման սխալ: {e}")
                                break
                            elif response.status_code == 400:
                                # Check if it's a duplicate article error
                                try:
                                    error_data = response.json()
                                    if "already exists" in str(error_data) or "link already exists" in str(error_data):
                                        spider.duplicate_articles += 1
                                        self.logger.info(f"🔄 Հոդված արդեն գոյություն ունի: {item['title'][:60]}...")
                                        article_saved = True  # Mark as "handled"
                                        break
                                    else:
                                        self.logger.warning(f"API save error 400: {error_data}")
                                        continue
                                except:
                                    self.logger.warning(f"API save error 400: {response.text[:200]}")
                                    continue
                            elif response.status_code == 404:
                                continue
                            else:
                                self.logger.warning(f"API save error: {response.status_code}")
                                continue
                                
                        except Exception as e:
                            continue
                    
                    if not article_saved:
                        self.logger.warning("⚠️ Ոչ մի save endpoint չաշխատեց")
                        self.api_working = False
                        
                except Exception as e:
                    self.logger.error(f"Error saving article via API: {e}")
                    self.api_working = False
            elif not keywords:
                self.logger.info(f"🚫 Հոդվածը չի պահպանվում - բանալի բառեր չգտնվեցին: {item['title'][:60]}...")
            elif not self.api_working:
                self.logger.info(f"🚫 Հոդվածը չի պահպանվում - API չի աշխատում: {item['title'][:60]}...")
            
        except Exception as e:
            spider.logger.error(f"Error processing article: {e}")
            
        return item

    def close_spider(self, spider):
        """Called when spider closes"""
        if not self.api_working:
            self.logger.warning("⚠️ Spider ավարտվեց - API չի աշխատում")
        else:
            self.logger.info("🕷️ Spider finished - cleanup handled by main monitor") 