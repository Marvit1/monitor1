# News Monitor Group 1 - Render.com Deployment

Այս նախագիծը նյուզ քերթող է, որը աշխատում է որպես առանձին worker ծառայություն Render.com-ում:

## 🚀 Render.com Deployment

### Նախապայմաններ
- Render.com հաշիվ
- API ծառայություն (https://beackkayq.onrender.com)

### Դեպլոյի քայլեր

1. **Fork կամ Clone** այս repository-ն
2. **Render.com Dashboard**-ում ստեղծեք նոր **Worker Service**
3. **Connect** ձեր GitHub repository-ն
4. **Configure** հետևյալ կարգավորումները:

#### Environment Variables
```
PYTHON_VERSION=3.11.0
API_BASE_URL=https://beackkayq.onrender.com
SCRAPY_SETTINGS_MODULE=news_scraper.settings
LOG_LEVEL=INFO
MONITOR_INTERVAL_MINUTES=2
DAYS_TO_KEEP_ARTICLES=7
```

#### Build Command
```bash
chmod +x build.sh && ./build.sh
```

#### Start Command
```bash
chmod +x start.sh && ./start.sh
```

### 📁 Ֆայլերի կառուցվածք
```
├── monitor_news_group1.py      # Գլխավոր մոնիտորինգ սկրիպտ
├── news_scraper_group1/        # Scrapy նախագիծ
├── requirements.txt            # Python dependencies
├── render.yaml                 # Render.com կոնֆիգուրացիա
├── Procfile                    # Process configuration
├── runtime.txt                 # Python տարբերակ
├── build.sh                    # Build script
└── start.sh                    # Start script
```

### 🔧 Կարգավորումներ

#### Մոնիտորինգի միջակայք
- `MONITOR_INTERVAL_MINUTES=2` - Ստուգման միջակայքը րոպեներով

#### Հոդվածների պահպանում
- `DAYS_TO_KEEP_ARTICLES=7` - Հոդվածների պահպանման ժամկետը օրերով

#### API կապ
- `API_BASE_URL` - Ձեր API-ի հասցեն

### 📊 Մոնիտորինգ

Worker ծառայությունը կաշխատի 24/7 և կկատարի հետևյալ գործողությունները:

1. **Նյուզ քերթում** - Բոլոր կոնֆիգուրացված սարդերից
2. **API-ի միջոցով մաքրում** - Հին հոդվածների հեռացում API-ի միջոցով
3. **API-ի հետ կապ** - Բանալի բառերի ստացում և հոդվածների մաքրում

### 🐛 Troubleshooting

#### API Connection Error
Եթե API-ի հետ կապը ձախողվում է, սկրիպտը կշարունակի աշխատել Scrapy-ով:

#### API Base URL Error
Ստուգեք `API_BASE_URL` environment variable-ը:

#### Scrapy Timeout
Սարդերը ունեն 10 րոպե timeout, եթե ավելի շատ ժամանակ է պետք, ավելացրեք timeout-ը:

### 📝 Logs

Logs-երը կարող եք տեսնել Render.com Dashboard-ում: 