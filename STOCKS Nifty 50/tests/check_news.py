"""Check NewsAPI availability and historical reach for news extension.

NewsAPI is a FALLBACK only; RSS feeds are the primary live-news source.
The API key is loaded from the environment via python-dotenv (.env).
No secret values are ever printed.
"""
import os
import warnings

warnings.filterwarnings("ignore")

from dotenv import load_dotenv

load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")

import requests
from datetime import datetime, timedelta


def test_range(days_back):
    if not NEWS_API_KEY:
        print(
            f"days_back={days_back:4d} skipped: NEWS_API_KEY not set "
            "(configure in .env or environment; RSS is the primary source)."
        )
        return
    from_d = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": "Indian stock market NSE",
        "from": from_d,
        "sortBy": "publishedAt",
        "pageSize": 5,
        "language": "en",
        "apiKey": NEWS_API_KEY,
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            data = r.json()
            total = data.get("totalResults", 0)
            articles = data.get("articles", [])
            # Reach diagnostics only; never echo the key.
            print(
                f"days_back={days_back:4d} from={from_d} status=200 "
                f"total={total} returned={len(articles)}"
            )
            if articles:
                print("   first article date:", articles[0].get("publishedAt"))
        else:
            print(f"days_back={days_back:4d} status={r.status_code}")
    except Exception as e:
        print(f"days_back={days_back:4d} error: {type(e).__name__} {e}")


if __name__ == "__main__":
    print("NewsAPI free-tier reach test (key from env/.env; RSS remains primary):")
    test_range(1)
    test_range(30)
    test_range(60)
    test_range(365 * 2)
    if not NEWS_API_KEY:
        print(
            "\nNOTE: NEWS_API_KEY is unset in the environment and .env. "
            "NewsAPI fallback is disabled. RSS feeds are the primary live-news source."
        )
