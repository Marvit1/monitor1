# API Endpoints for News Monitor

Այս ֆայլը նկարագրում է API endpoint-ները, որոնք պետք է լինեն հիմնական API-ում նյուզ մոնիտորի համար:

## 🔧 Required Endpoints

### 1. GET /api/keywords/
Բանալի բառերի ցուցակի ստացում:

**Response:**
```json
[
  {
    "id": 1,
    "word": "Հայաստան",
    "is_active": true
  },
  {
    "id": 2,
    "word": "Երևան",
    "is_active": true
  }
]
```

### 2. DELETE /api/articles/cleanup/
Հին հոդվածների մաքրում:

**Parameters:**
- `before_date` (ISO format): Ամսաթիվ, որից առաջ հոդվածները պետք է ջնջվեն

**Example:**
```
DELETE /api/articles/cleanup/?before_date=2024-01-01T00:00:00
```

**Response:**
```json
{
  "deleted_count": 150,
  "message": "Successfully deleted 150 old articles"
}
```

## 🚀 Implementation Notes

### Django View Example

```python
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from datetime import datetime
from main.models import NewsArticle, Keyword

@require_http_methods(["GET"])
def get_keywords(request):
    keywords = Keyword.objects.filter(is_active=True)
    data = [
        {
            "id": kw.id,
            "word": kw.word,
            "is_active": kw.is_active
        }
        for kw in keywords
    ]
    return JsonResponse(data, safe=False)

@require_http_methods(["DELETE"])
def cleanup_articles(request):
    before_date_str = request.GET.get('before_date')
    if not before_date_str:
        return JsonResponse({"error": "before_date parameter required"}, status=400)
    
    try:
        before_date = datetime.fromisoformat(before_date_str.replace('Z', '+00:00'))
        deleted_count, _ = NewsArticle.objects.filter(created_at__lt=before_date).delete()
        
        return JsonResponse({
            "deleted_count": deleted_count,
            "message": f"Successfully deleted {deleted_count} old articles"
        })
    except ValueError:
        return JsonResponse({"error": "Invalid date format"}, status=400)
```

### URL Configuration

```python
# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('api/keywords/', views.get_keywords, name='get_keywords'),
    path('api/articles/cleanup/', views.cleanup_articles, name='cleanup_articles'),
]
```

## 🔒 Security Considerations

1. **Authentication** - Ավելացրեք authentication եթե անհրաժեշտ է
2. **Rate Limiting** - Սահմանափակեք cleanup endpoint-ի հաճախությունը
3. **Logging** - Գրանցեք cleanup գործողությունները

## 📝 Testing

```bash
# Test keywords endpoint
curl -X GET https://beackkayq.onrender.com/api/keywords/

# Test cleanup endpoint
curl -X DELETE "https://beackkayq.onrender.com/api/articles/cleanup/?before_date=2024-01-01T00:00:00"
``` 