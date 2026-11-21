import requests
from django.core.cache import cache

MANDI_API_KEY = "579b464db66ec23bdd000001f3329f33a5d74be37762ab2de4408c18"
MANDI_API_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"


def fetch_mandi_prices(commodity=None, state=None, district=None, limit=20, offset=0):
    cache_key = f"mandi_{commodity or 'all'}_{state or 'all'}_{district or 'all'}_{limit}_{offset}".lower().replace(" ", "_")
    cached = cache.get(cache_key)
    if cached:
        return cached

    params = {
        "api-key": MANDI_API_KEY,
        "format": "json",
        "limit": limit,
        "offset": offset,
    }

    if commodity:
        params["filters[commodity]"] = commodity
    if state:
        params["filters[state]"] = state
    if district:
        params["filters[district]"] = district

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(MANDI_API_URL, params=params, headers=headers, timeout=45)
        response.raise_for_status()
        data = response.json()
        result = {
            "records": data.get("records", []),
            "total": data.get("total", 0),
            "count": data.get("count", 0),
            "error": None,
        }
        if result["records"]:
            cache.set(cache_key, result, timeout=300)
        return result
    except requests.exceptions.ConnectionError:
        return {"records": [], "total": 0, "count": 0, "error": "Could not connect to the price discovery service. Please check your internet connection."}
    except requests.exceptions.Timeout:
        return {"records": [], "total": 0, "count": 0, "error": "The market prices service is taking longer than usual to respond. Please retry your search."}
    except requests.exceptions.HTTPError as e:
        return {"records": [], "total": 0, "count": 0, "error": f"Market price query returned error: {e}"}
    except Exception as e:
        return {"records": [], "total": 0, "count": 0, "error": f"Unexpected error: {e}"}
