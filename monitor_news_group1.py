print("🔍 Debug: Starting imports...")
import time
print("🔍 Debug: time imported")
import os
print("🔍 Debug: os imported")
import sys
print("🔍 Debug: sys imported")
import subprocess
print("🔍 Debug: subprocess imported")
import requests
print("🔍 Debug: requests imported")
import json
print("🔍 Debug: json imported")
from datetime import datetime, timedelta
print("🔍 Debug: datetime imported")
print("🔍 Debug: All imports completed")

# Memory optimization imports
import gc
import psutil

def cleanup_memory():
    """Memory cleanup function"""
    try:
        # Force garbage collection
        gc.collect()
        
        # Get memory info
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        print(f"🧹 Memory cleanup: {memory_mb:.1f} MB")
        return memory_mb
    except Exception as e:
        print(f"⚠️ Memory cleanup error: {e}")
        return 0

class NewsMonitorAPI:
    def __init__(self, api_base_url):
        self.api_base_url = api_base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'NewsMonitor/1.0'
        })
        
    def test_connection(self):
        """API-ի կապի ստուգում"""
        try:
            print(f"🔗 Ստուգում ենք API կապը՝ {self.api_base_url}")
            
            # Փորձում ենք հիմնական endpoint-ները
            test_endpoints = [
                f"{self.api_base_url}/",
                f"{self.api_base_url}/api/",
                f"{self.api_base_url}/health/",
                f"{self.api_base_url}/status/"
            ]
            
            for endpoint in test_endpoints:
                try:
                    response = self.session.get(endpoint, timeout=5)
                    if response.status_code in [200, 404]:  # 404-ը նույնպես OK է, նշանակում է endpoint գոյություն ունի
                        print(f"✅ API կապ հաջող՝ {endpoint}")
                        return True
                except:
                    continue
            
            print(f"⚠️ API կապի խնդիր՝ {self.api_base_url}")
            return False
            
        except Exception as e:
            print(f"❌ API կապի սխալ՝ {e}")
            return False
    
    def cleanup_old_articles(self, days_to_keep):
        """Հին հոդվածների մաքրում API-ի միջոցով"""
        try:
            cleanup_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
            print(f"🧹 Փորձում ենք մաքրել հոդվածները {cleanup_date} ամսաթվից առաջ...")
            
            # Փորձում ենք տարբեր endpoint-ներ
            endpoints_to_try = [
                f"{self.api_base_url}/api/articles/cleanup/",
                f"{self.api_base_url}/api/cleanup/",
                f"{self.api_base_url}/api/articles/",
                f"{self.api_base_url}/cleanup/"
            ]
            
            for endpoint in endpoints_to_try:
                try:
                    print(f"🔗 Փորձում ենք endpoint՝ {endpoint}")
                    response = self.session.delete(
                        endpoint,
                        params={'before_date': cleanup_date},
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        deleted_count = data.get('deleted_count', 0)
                        print(f"✅ Հաջողությամբ մաքրվեց {deleted_count} հոդված")
                        return deleted_count
                    elif response.status_code == 404:
                        print(f"⚠️ Endpoint չի գտնվել՝ {endpoint}")
                        continue
                    else:
                        print(f"❌ API cleanup error: {response.status_code} - {response.text}")
                        continue
                        
                except requests.exceptions.RequestException as e:
                    print(f"⚠️ Network error {endpoint}: {e}")
                    continue
            
            print("❌ Ոչ մի endpoint չաշխատեց")
            return 0
            
        except Exception as e:
            print(f"❌ API cleanup exception: {e}")
            return 0
    
    def get_keywords(self):
        """Բանալի բառերի ստացում API-ից"""
        try:
            print(f"🔍 Փորձում ենք ստանալ բանալի բառեր...")
            
            # Փորձում ենք տարբեր endpoint-ներ
            endpoints_to_try = [
                f"{self.api_base_url}/api/keywords/",
                f"{self.api_base_url}/api/keywords",
                f"{self.api_base_url}/keywords/",
                f"{self.api_base_url}/keywords"
            ]
            
            for endpoint in endpoints_to_try:
                try:
                    print(f"🔗 Փորձում ենք endpoint՝ {endpoint}")
                    response = self.session.get(endpoint, timeout=10)
                    
                    if response.status_code == 200:
                        keywords = response.json()
                        print(f"✅ Ստացվեց {len(keywords)} բանալի բառ")
                        return keywords
                    elif response.status_code == 404:
                        print(f"⚠️ Endpoint չի գտնվել՝ {endpoint}")
                        continue
                    else:
                        print(f"❌ API keywords error: {response.status_code} - {response.text}")
                        continue
                        
                except requests.exceptions.RequestException as e:
                    print(f"⚠️ Network error {endpoint}: {e}")
                    continue
            
            print("❌ Ոչ մի keywords endpoint չաշխատեց")
            return []
            
        except Exception as e:
            print(f"❌ API keywords exception: {e}")
            return []

def run_scrapy_with_reactor_fix(spider_name, scrapy_project_path):
    """Run scrapy with reactor signal handling fix"""
    try:
        # Set environment variables to fix reactor issues
        env = dict(os.environ)
        env.update({
            'SCRAPY_SETTINGS_MODULE': 'news_scraper.settings',
            'PYTHONPATH': scrapy_project_path,
            # Disable signal handling that causes issues in containerized environments
            'TWISTED_DISABLE_SIGNAL_HANDLERS': '1',
            'TWISTED_NO_SIGNAL_HANDLERS': '1',
            # Suppress all warnings
            'PYTHONWARNINGS': 'ignore'
        })
        
        # Use simple scrapy crawl command with environment variables
        result = subprocess.run([
            sys.executable, '-m', 'scrapy', 'crawl', spider_name
        ], 
            cwd=scrapy_project_path,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minutes per spider
            env=env
        )
        
        # Print full error details for debugging
        if result.returncode != 0:
            print(f"❌ Spider {spider_name} failed with return code: {result.returncode}")
            print(f"📄 STDOUT: {result.stdout}")
            print(f"❌ STDERR: {result.stderr}")
        
        # Memory cleanup after spider finishes
        memory_usage = cleanup_memory()
        print(f"🧹 Spider {spider_name} finished, memory usage: {memory_usage:.1f} MB")
        
        return result
        
    except Exception as reactor_error:
        print(f"❌ Scrapy crawl failed: {reactor_error}")
        # Return a mock result to prevent crashes
        from types import SimpleNamespace
        mock_result = SimpleNamespace()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = f"Scrapy crawl failed: {reactor_error}"
        return mock_result

def get_spiders_list(scrapy_project_path):
    """Get list of available spiders by scanning spider files directly"""
    spiders = []
    
    # Method 1: Direct file scanning (most reliable)
    spiders_dir = os.path.join(scrapy_project_path, 'news_scraper', 'spiders')
    print(f"🔍 Ստուգում ենք spiders պանակը՝ {spiders_dir}")
    
    if os.path.exists(spiders_dir):
        try:
            for filename in os.listdir(spiders_dir):
                if filename.endswith('.py') and filename != '__init__.py':
                    spider_file = os.path.join(spiders_dir, filename)
                    print(f"📄 Գտնված spider ֆայլ՝ {filename}")
                    
                    # Try to extract spider name from file
                    try:
                        with open(spider_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Look for name = 'spider_name' pattern
                            import re
                            name_matches = re.findall(r"name\s*=\s*['\"]([^'\"]+)['\"]", content)
                            if name_matches:
                                spider_name = name_matches[0]
                                spiders.append(spider_name)
                                print(f"✅ Գտնված spider՝ {spider_name}")
                            else:
                                # Fallback: use filename without .py
                                spider_name = filename[:-3]
                                if spider_name not in ['__init__', 'base']:
                                    spiders.append(spider_name)
                                    print(f"✅ Fallback spider՝ {spider_name}")
                    except Exception as e:
                        print(f"⚠️ Չհաջողվեց կարդալ {filename}: {e}")
                        
        except Exception as e:
            print(f"❌ Spiders պանակի սկանավորման սխալ: {e}")
    else:
        print(f"❌ Spiders պանակը գոյություն չունի՝ {spiders_dir}")
    
    # Method 2: Try Scrapy's spider loader as fallback (only if Method 1 failed)
    if not spiders:
        print("🔄 Փորձում ենք Scrapy-ի spider loader...")
        try:
            env = dict(os.environ)
            env.update({
                'SCRAPY_SETTINGS_MODULE': 'news_scraper.settings',
                'PYTHONPATH': scrapy_project_path,
                # Use Python 3.11 for better compatibility
                'PYTHON_VERSION': '3.11',
                # Use stable Twisted version
                'TWISTED_VERSION': '22.10.0',
                # Force asyncio reactor before any imports
                'TWISTED_REACTOR': 'twisted.internet.asyncioreactor.AsyncioSelectorReactor',
                'TWISTED_DISABLE_SIGNAL_HANDLERS': '1',
                'TWISTED_NO_SIGNAL_HANDLERS': '1',
                'PYTHONWARNINGS': 'ignore'
            })
            
            # Simpler approach without using deprecated modules
            result = subprocess.run([
                sys.executable, '-W', 'ignore', '-c', f'''
import warnings
warnings.filterwarnings("ignore")

import sys
import os
sys.path.insert(0, "{scrapy_project_path}")

try:
    import importlib.util
    import glob
    
    spider_files = glob.glob("{spiders_dir}/*.py")
    for spider_file in spider_files:
        if not spider_file.endswith("__init__.py"):
            with open(spider_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'class' in content and 'Spider' in content:
                    import re
                    names = re.findall(r"name\\s*=\\s*['\\""]([^'\\"\"]+)['\\""]", content)
                    if names:
                        print(names[0])
                    else:
                        basename = os.path.basename(spider_file)[:-3]
                        if basename not in ['__init__', 'base']:
                            print(basename)
except Exception as subprocess_error:
    print(f"Error: {{subprocess_error}}", file=sys.stderr)
    sys.exit(1)
'''],
                cwd=scrapy_project_path,
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )
            
            if result.returncode == 0 and result.stdout.strip():
                fallback_spiders = [spider.strip() for spider in result.stdout.strip().split('\n') if spider.strip()]
                spiders.extend(fallback_spiders)
                print(f"✅ Scrapy loader արդյունք՝ {fallback_spiders}")
            else:
                print(f"❌ Scrapy loader ձախողում: {result.stderr}")
                
        except Exception as e:
            print(f"❌ Scrapy loader սխալ: {e}")
    
    # Method 3: Hardcoded fallback for common spider names
    if not spiders:
        print("🔄 Փորձում ենք ստանդարտ spider անուններ...")
        common_spiders = ['asbarez', 'aravot', 'news_am', 'panorama', 'hetq']
        for spider_name in common_spiders:
            spider_file = os.path.join(spiders_dir, f'{spider_name}.py')
            if os.path.exists(spider_file):
                spiders.append(spider_name)
                print(f"✅ Ստանդարտ spider գտնված՝ {spider_name}")
    
    return list(set(spiders))  # Remove duplicates

def check_project_structure(scrapy_project_path):
    """Check and debug project structure"""
    print(f"🔍 Ստուգում ենք նախագծի կառուցվածքը...")
    print(f"📁 Project path: {scrapy_project_path}")
    print(f"📁 Exists: {os.path.exists(scrapy_project_path)}")
    
    if os.path.exists(scrapy_project_path):
        print("📂 Project directory contents:")
        try:
            for item in os.listdir(scrapy_project_path):
                item_path = os.path.join(scrapy_project_path, item)
                if os.path.isdir(item_path):
                    print(f"  📁 {item}/")
                else:
                    print(f"  📄 {item}")
        except Exception as e:
            print(f"❌ Could not list project directory: {e}")
    
    # Check news_scraper directory
    news_scraper_path = os.path.join(scrapy_project_path, 'news_scraper')
    print(f"📁 news_scraper path: {news_scraper_path}")
    print(f"📁 Exists: {os.path.exists(news_scraper_path)}")
    
    if os.path.exists(news_scraper_path):
        print("📂 news_scraper directory contents:")
        try:
            for item in os.listdir(news_scraper_path):
                item_path = os.path.join(news_scraper_path, item)
                if os.path.isdir(item_path):
                    print(f"  📁 {item}/")
                else:
                    print(f"  📄 {item}")
        except Exception as e:
            print(f"❌ Could not list news_scraper directory: {e}")
    
    # Check spiders directory
    spiders_path = os.path.join(scrapy_project_path, 'news_scraper', 'spiders')
    print(f"📁 spiders path: {spiders_path}")
    print(f"📁 Exists: {os.path.exists(spiders_path)}")
    
    if os.path.exists(spiders_path):
        print("📂 spiders directory contents:")
        try:
            for item in os.listdir(spiders_path):
                item_path = os.path.join(spiders_path, item)
                if os.path.isdir(item_path):
                    print(f"  📁 {item}/")
                else:
                    print(f"  📄 {item}")
        except Exception as e:
            print(f"❌ Could not list spiders directory: {e}")

def main():
    print("🏢 ԽՈՒՄԲ 1 - Մեծ նյուզ սայտերի մոնիտորինգ (news_scraper_group1)")
    print("🔍 Debug: main() function started")
    
    # Get settings from environment variables or use defaults
    interval_minutes = int(os.environ.get('MONITOR_INTERVAL_MINUTES', 7))
    days_to_keep = int(os.environ.get('DAYS_TO_KEEP_ARTICLES', 7))
    api_base_url = os.environ.get('API_BASE_URL', 'https://beackkayq.onrender.com')
    
    print(f"🌐 API Base URL: {api_base_url}")
    print(f"🔍 Debug: interval_minutes = {interval_minutes}")
    print(f"🔍 Debug: days_to_keep = {days_to_keep}")
    
    print("🚀 ԽՈՒՄԲ 1 - Մեծ նյուզ սայտերի մոնիտորինգ սկսվել է")
    print(f"📅 Հոդվածների պահպանման ժամկետը՝ {days_to_keep} օր")
    print(f"⏰ Ստուգման միջակայքը՝ {interval_minutes} րոպե")

    # Initialize API client
    api_client = NewsMonitorAPI(api_base_url)
    
    # Test API connection
    api_connected = api_client.test_connection()
    if api_connected:
        try:
            keywords = api_client.get_keywords()
            print(f"✅ API կապ հաստատված, բանալի բառեր՝ {len(keywords)}")
            print(f"🔍 Keywords: {[kw.get('word', '') for kw in keywords]}")
        except Exception as e:
            print(f"⚠️ API keywords սխալ՝ {e}")
            keywords = []
    else:
        print("⚠️ API կապի խնդիր, շարունակում ենք Scrapy-ով...")
        keywords = []
    
    # Fallback keywords if API is not available
    if not keywords:
        print("📝 Օգտագործում ենք fallback բանալի բառեր...")
        keywords = [
            {"word": "Հայաստան", "is_active": True},
            {"word": "Երևան", "is_active": True},
            {"word": "Նիկոլ Փաշինյան", "is_active": True},
            {"word": "Կառավարություն", "is_active": True},
            {"word": "Պատգամավոր", "is_active": True},
            {"word": "Բանակ", "is_active": True},
            {"word": "Սահման", "is_active": True},
            {"word": "Տնտեսություն", "is_active": True},
            {"word": "Կրթություն", "is_active": True},
            {"word": "Առողջապահություն", "is_active": True}
        ]
        print(f"✅ Fallback բանալի բառեր՝ {len(keywords)}")

    # Set up Scrapy environment for GROUP 1
    scrapy_project_path = os.path.join(os.path.dirname(__file__), 'news_scraper_group1')
    
    # Debug project structure
    check_project_structure(scrapy_project_path)
    
    # Get available spiders with improved method
    spiders = get_spiders_list(scrapy_project_path)
    
    if not spiders:
        print("❌ ԽՈՒՄԲ 1 - Սարդեր չեն գտնվել։")
        
        # Try alternative paths
        alternative_paths = [
            os.path.dirname(__file__),  # Current directory
            os.path.join(os.path.dirname(__file__), '..', 'news_scraper_group1'),  # Parent directory
            '/opt/render/project/src/news_scraper_group1',  # Render.com typical path
            '/app/news_scraper_group1',  # Heroku typical path
        ]
        
        print("🔍 Փորձում ենք այլընտրանքային ուղիներ...")
        for alt_path in alternative_paths:
            print(f"📁 Ստուգում ենք՝ {alt_path}")
            if os.path.exists(alt_path):
                print(f"✅ Գտնված՝ {alt_path}")
                check_project_structure(alt_path)
                spiders = get_spiders_list(alt_path)
                if spiders:
                    scrapy_project_path = alt_path
                    break
        
        if not spiders:
            print("❌ ԽՈՒՄԲ 1 - Բոլոր ուղիներում սարդեր չեն գտնվել։ Ելք։")
            return
    
    print(f"✅ ԽՈՒՄԲ 1 - Գտնված սարդեր՝ {', '.join(spiders)}")

    cycle_count = 0
    
    try:
        while True:
            cycle_count += 1
            print(f"\n🔄 ԽՈՒՄԲ 1 - Ցիկլ #{cycle_count} - {datetime.now().strftime('%H:%M:%S')}")
            
            # Cleanup old articles via API (only if API is connected)
            if api_connected:
                deleted_count = api_client.cleanup_old_articles(days_to_keep)
                if deleted_count > 0:
                    print(f"🗑️ ԽՈՒՄԲ 1 - API-ի միջոցով մաքրվել է {deleted_count} հին հոդված")
                else:
                    print("⚠️ API cleanup բաց թողնված (կապ չկա)")

            # Run each spider with reactor fix
            for spider_name in spiders:
                print(f"🕷️ ԽՈՒՄԲ 1 - Սկսվում է սարդը՝ {spider_name}")
                print(f"🔍 Debug: Spider {spider_name} start time: {datetime.now().strftime('%H:%M:%S')}")
                
                try:
                    result = run_scrapy_with_reactor_fix(spider_name, scrapy_project_path)
                    
                    if result.returncode == 0:
                        # Extract key info from output
                        lines = result.stdout.split('\n')
                        found_output = False
                        for line in lines:
                            if any(keyword in line for keyword in ['📊 ԱՄՓՈՓՈՒՄ', '✅ Բանալի բառ գտնվեց', '💾 Նոր հոդված', '🔄 Կրկնություն', '📄 Հոդված', '🔍 Գտնված', '📰 Գտնվել է', '✅ Բանալի բառ գտնվեց', '❌ Բանալի բառ չգտնվեց']):
                                print(f"    ԽՈՒՄԲ 1 - {line.strip()}")
                                found_output = True
                        
                        if not found_output:
                            print(f"    ԽՈՒՄԲ 1 - {spider_name}: Ոչ մի հոդված չի գտնվել")
                            # Show first few lines of stdout for debugging
                            if result.stdout:
                                print(f"    ԽՈՒՄԲ 1 - {spider_name} stdout preview: {result.stdout[:300]}...")
                        
                        # Show stderr if there are any errors
                        if result.stderr:
                            print(f"    ԽՈՒՄԲ 1 - {spider_name} stderr: {result.stderr[:200]}...")
                        
                        print(f"✅ ԽՈՒՄԲ 1 - {spider_name} ավարտված")
                    else:
                        # Print full error details
                        print(f"❌ ԽՈՒՄԲ 1 - {spider_name} սխալ (return code: {result.returncode})")
                        if result.stdout:
                            print(f"📄 STDOUT: {result.stdout}")
                        if result.stderr:
                            print(f"❌ STDERR: {result.stderr}")
                        
                        # If it's a critical error, skip this spider for this cycle
                        error_msg = result.stderr if result.stderr else "Unknown error"
                        if "Could not find spider class" in error_msg or "ImportError" in error_msg:
                            print(f"⚠️ ԽՈՒՄԲ 1 - {spider_name} բաց թողնված այս ցիկլում")
                        
                except subprocess.TimeoutExpired:
                    print(f"⏰ ԽՈՒՄԲ 1 - {spider_name} timeout (2 րոպե)")
                    print(f"🔍 Debug: Spider {spider_name} took too long, skipping...")
                except Exception as e:
                    print(f"❌ ԽՈՒՄԲ 1 - {spider_name} սխալ: {e}")
                    # Continue with next spider instead of crashing
                    continue

            print(f"✅ ԽՈՒՄԲ 1 - Ցիկլ #{cycle_count} ավարտված")
            print(f"😴 ԽՈՒՄԲ 1 - Հաջորդ ստուգումը՝ {interval_minutes} րոպեից...")
            
            # Sleep for the specified interval
            time.sleep(interval_minutes * 60)
            
    except KeyboardInterrupt:
        print("\n🛑 ԽՈՒՄԲ 1 - Մոնիտորինգը դադարեցվել է օգտագործողի կողմից")
    except Exception as e:
        print(f"❌ ԽՈՒՄԲ 1 - Ընդհանուր սխալ: {e}")

if __name__ == "__main__":
    main()