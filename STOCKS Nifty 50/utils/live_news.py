"""
Live news filtering and sentiment analysis module.
Fetches news from NewsAPI, filters for market-relevant articles,
then runs sentiment analysis using FinBERT.
"""

import os
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
import warnings
warnings.filterwarnings("ignore")

# NewsAPI key — loaded from environment / .env file
# ⚠️ SECURITY: The previous hardcoded key has been moved to .env.
# If this key was ever committed to a public repo, rotate it immediately.
import os
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")
if not NEWS_API_KEY:
    print("WARNING: NEWS_API_KEY not found in environment/.env. Live news will be unavailable.")

# ==========================================================
# FILTERING KEYWORDS AND PATTERNS
# ==========================================================

# Keywords that indicate market-relevant news
INCLUDE_KEYWORDS = [
    # Financial Results
    "quarterly results", "annual results", "financial results", "Q1", "Q2", "Q3", "Q4",
    "revenue", "profit", "net income", "earnings", "EBITDA", "margin",
    # Corporate Actions
    "dividend", "stock split", "buyback", "bonus", "rights issue",
    "merger", "acquisition", "divestiture", "takeover", "joint venture",
    # Management
    "CEO", "CFO", "appointed", "resigned", "management change", "board",
    # Regulatory
    "SEBI", "RBI", "IRDAI", "regulatory", "approval", "penalty", "fine",
    # Economy & Policy
    "interest rate", "repo rate", "monetary policy", "inflation", "GDP",
    "fiscal deficit", "budget", "government", "policy",
    # Orders & Contracts
    "order win", "contract", "partnership", "expansion",
    # Ratings
    "credit rating", "upgrade", "downgrade", "outlook",
    # Market Events
    "IPO", "FPO", "listing", "market capitalization", "NSE", "BSE",
    "bullish", "bearish", "target price", "overweight", "underweight",
    # Sector-specific
    "sector", "industry", "manufacturing", "infrastructure",
    # Global
    "crude oil", "commodity", "trade", "tariff", "sanction",
    # Company-specific
    "announces", "launches", "investment", "expansion plan",
]

# Keywords/patterns for auto-exclusion
EXCLUDE_PATTERNS = [
    # Sports
    r"\b(IPL|T20|cricket|football|World Cup|Olympic|medal|sports)\b",
    # Entertainment
    r"\b(movie|film|actor|actress|singer|concert|album|entertainment|TV|series)\b",
    # Lifestyle
    r"\b(recipe|fashion|beauty|travel|fitness|yoga|wellness|lifestyle)\b",
    # Celebrity
    r"\b(celebrity|viral|trending|influencer)\b",
    # General tech (unrelated to listed companies)
    r"\b(gadget|smartphone|app|startup|tech launch)\b",
    # Promotional
    r"\b(offer|discount|coupon|sale|promotion|sponsored)\b",
    # Opinion
    r"\b(opinion|editorial|viewpoint|column)\b",
]

# Company ticker mapping for search queries
# Maps company names to their tickers for filtering
COMPANY_SEARCH_TERMS = {
    "RELIANCE": "Reliance Industries",
    "TCS": "Tata Consultancy Services",
    "HDFCBANK": "HDFC Bank",
    "INFY": "Infosys",
    "ICICIBANK": "ICICI Bank",
    "SBIN": "State Bank of India",
    "BHARTIARTL": "Bharti Airtel",
    "ITC": "ITC",
    "WIPRO": "Wipro",
    "HINDUNILVR": "Hindustan Unilever",
    "LT": "Larsen & Toubro",
    "BAJFINANCE": "Bajaj Finance",
    "MARUTI": "Maruti Suzuki",
    "TITAN": "Titan Company",
    "ASIANPAINT": "Asian Paints",
    "AXISBANK": "Axis Bank",
    "NTPC": "NTPC",
    "KOTAKBANK": "Kotak Mahindra Bank",
    "SUNPHARMA": "Sun Pharma",
    "ONGC": "Oil and Natural Gas Corporation",
    "HCLTECH": "HCL Technologies",
    "POWERGRID": "Power Grid",
    "JSWSTEEL": "JSW Steel",
    "ULTRACEMCO": "UltraTech Cement",
    "BAJAJFINSV": "Bajaj Finserv",
    "TATASTEEL": "Tata Steel",
    "TATACONSUM": "Tata Consumer",
    "M&M": "Mahindra & Mahindra",
    "SHRIRAMFIN": "Shriram Finance",
    "SBILIFE": "SBI Life Insurance",
    "NESTLEIND": "Nestle India",
    "BAJAJ-AUTO": "Bajaj Auto",
    "HEROMOTOCO": "Hero MotoCorp",
    "DRREDDY": "Dr Reddy's",
    "EICHERMOT": "Eicher Motors",
    "COALINDIA": "Coal India",
    "TECHM": "Tech Mahindra",
    "GRASIM": "Grasim Industries",
    "HINDALCO": "Hindalco",
    "INDUSINDBK": "IndusInd Bank",
    "CIPLA": "Cipla",
    "BEL": "Bharat Electronics",
    "TRENT": "Trent",
    "APOLLOHOSP": "Apollo Hospitals",
    "JIOFIN": "Jio Financial Services",
    "ADANIENT": "Adani Enterprises",
    "ADANIPORTS": "Adani Ports",
    "HDFCLIFE": "HDFC Life",
    "ETERNAL": "Eternal",
    "BPCL": "BPCL",
    "HAL": "HAL",
}


def is_market_relevant_news(article):
    """
    Check if a news article is relevant for stock market prediction.
    
    Parameters
    ----------
    article : dict
        News article with title, description, content fields
    
    Returns
    -------
    bool
        True if the article is market-relevant
    """
    title = (article.get("title") or "") + " " + (article.get("description") or "")
    title_lower = title.lower()
    
    # Check exclusion patterns first
    for pattern in EXCLUDE_PATTERNS:
        if re.search(pattern, title_lower):
            return False
    
    # Check for include keywords
    for keyword in INCLUDE_KEYWORDS:
        if keyword.lower() in title_lower:
            return True
    
    # Check if it mentions any of our tracked companies
    for ticker, company_name in COMPANY_SEARCH_TERMS.items():
        if company_name.lower() in title_lower or ticker.lower() in title_lower:
            return True
    
    # Default: don't include if no market relevance detected
    return False


# ==========================================================
# TRUE-LIVE INDIAN NEWS FEEDS
# ==========================================================
# NewsAPI's free Developer plan indexes articles with a ~24h delay, which is
# why the dashboard only showed ~2-day-old headlines. These RSS feeds are
# fetched on every call and carry the publishers' real publication timestamps
# — no API key and no delay. Google News RSS (India locale) aggregates the
# major Indian business publishers (Moneycontrol, ET, CNBC-TV18, Business
# Standard, NSE, BSE, etc.) into a single clean feed and is far more reliable
# than the individual publishers, several of which now block or redirect
# automated requests (Moneycontrol 503, ET 404, CNBC HTML page, NSE 404).
INDIAN_MARKET_RSS_FEEDS = [
    "https://news.google.com/rss/search?q=Indian%20stock%20market&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Sensex%20Nifty%20BSE%20NSE&hl=en-IN&gl=IN&ceid=IN:en",
]

RSS_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def _el_text(item, tag):
    """Return the stripped text of the first <tag> child, or ''."""
    el = item.find(tag)
    return (el.text or "").strip() if el is not None else ""


def _strip_html(text):
    """Remove HTML tags and collapse whitespace from a feed description."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_pubdate(rfc822):
    """Normalise an RSS/Atom pubDate to ISO-8601; fall back to now()."""
    if not rfc822:
        return datetime.now().isoformat()
    try:
        return parsedate_to_datetime(rfc822).isoformat()
    except (ValueError, TypeError):
        return rfc822


def _clean_gn_title(title, source_name):
    """
    Google News formats RSS titles as "Headline - Publisher". Drop the
    trailing " - <source>" suffix only when it matches the item's <source>
    element so headlines stay clean without misfiring on real headlines.
    """
    if not title or not source_name:
        return title
    suffix = f" - {source_name}"
    if title.endswith(suffix):
        return title[: -len(suffix)].strip()
    return title


def fetch_rss_feed(url, max_items=60, timeout=12):
    """
    Fetch and parse one RSS/Atom feed into article dicts shaped like NewsAPI
    articles: title, description, content, url, source{name}, publishedAt.
    Returns [] on any error so callers can fall back gracefully.
    """
    headers = {
        "User-Agent": RSS_USER_AGENT,
        "Accept": "application/rss+xml, application/xml;q=0.9",
    }
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
    except Exception:
        return []

    try:
        root = ET.fromstring(response.content)
    except ET.ParseError:
        return []

    channel_title = ""
    channel = root.find("channel")
    if channel is not None:
        channel_title = _el_text(channel, "title")

    articles = []
    for item in root.findall(".//item")[:max_items]:
        title = _strip_html(_el_text(item, "title"))
        source_name = channel_title or "Indian News"
        source_el = item.find("source")
        if source_el is not None and (source_el.text or "").strip():
            source_name = source_el.text.strip()
        title = _clean_gn_title(title, source_name)

        description = _strip_html(_el_text(item, "description"))
        articles.append({
            "title": title,
            "description": description,
            "content": description,
            "url": _el_text(item, "link"),
            "source": {"name": source_name},
            "publishedAt": _parse_pubdate(_el_text(item, "pubDate")),
        })
    return articles


def _company_rss_urls(company_ticker):
    """
    Real-time, company-specific Google News RSS (India locale).
    Returns the most recent articles mentioning the company.
    """
    if not company_ticker:
        return []
    company_name = COMPANY_SEARCH_TERMS.get(company_ticker.upper(), company_ticker)
    queries = [f"{company_name} stock", f"{company_name} India"]
    return [
        f"https://news.google.com/rss/search?q={requests.utils.quote(q, safe='')}"
        f"&hl=en-IN&gl=IN&ceid=IN:en"
        for q in queries
    ]


def _fetch_newsapi_articles(company_ticker=None, from_days=7, page_size=50):
    """
    Original NewsAPI path — used as a fallback when RSS is unreachable.
    N.B. the free Developer plan indexes with a ~24h delay.
    """
    from_date = (datetime.now() - timedelta(days=from_days)).strftime("%Y-%m-%d")

    if company_ticker:
        company_name = COMPANY_SEARCH_TERMS.get(
            company_ticker.upper(), company_ticker
        )
        query = f"{company_name} India stock"
    else:
        query = "Indian stock market NSE"

    params = {
        "q": query,
        "from": from_date,
        "sortBy": "publishedAt",
        "pageSize": page_size,
        "language": "en",
        "apiKey": NEWS_API_KEY,
    }

    try:
        response = requests.get("https://newsapi.org/v2/everything", params=params, timeout=10)
        if response.status_code == 200:
            return response.json().get("articles", [])
        return []
    except Exception:
        return []


def fetch_live_news(company_ticker=None, from_days=7, page_size=50):
    """
    Fetch LIVE Indian market + company news on every call (no caching).

    Primary source: real-time Google News RSS (India locale) — no API key,
    no 24h delay. Falls back to the NewsAPI free tier when every RSS feed is
    unreachable so the dashboard always has something to display.

    Parameters
    ----------
    company_ticker : str, optional
        Specific company ticker to fetch news for
    from_days : int
        Look-back window used only for the NewsAPI fallback
    page_size : int
        Maximum number of articles to return

    Returns
    -------
    list
        Article dicts: title, description, content, url, source{name},
        publishedAt (ISO-8601).
    """
    urls = list(INDIAN_MARKET_RSS_FEEDS)
    urls.extend(_company_rss_urls(company_ticker))

    articles = []
    for url in urls:
        articles.extend(fetch_rss_feed(url, max_items=page_size, timeout=12))

    # Dedupe by URL and keep the newest first.
    seen = set()
    unique = []
    for art in articles:
        u = art.get("url")
        if u and u in seen:
            continue
        if u:
            seen.add(u)
        unique.append(art)

    unique.sort(key=lambda a: a.get("publishedAt") or "", reverse=True)
    unique = unique[:page_size]

    if unique:
        return unique

    # Fallback: NewsAPI (24h-delayed on the free tier, but better than nothing).
    return _fetch_newsapi_articles(company_ticker, from_days, page_size)


def filter_market_news(articles):
    """
    Filter articles to keep only market-relevant ones.
    
    Parameters
    ----------
    articles : list
        List of news article dicts
    
    Returns
    -------
    list
        Filtered list of market-relevant articles
    """
    filtered = []
    for article in articles:
        if is_market_relevant_news(article):
            filtered.append(article)
    return filtered


def analyze_sentiment_finbert(text):
    """
    Analyze sentiment of text using FinBERT via HuggingFace.
    
    Parameters
    ----------
    text : str
        Text to analyze
    
    Returns
    -------
    dict
        Sentiment analysis result with label and score
    """
    try:
        from transformers import pipeline
        
        # Use FinBERT model
        sentiment_pipeline = pipeline(
            "sentiment-analysis",
            model="ProsusAI/finbert",
            tokenizer="ProsusAI/finbert",
        )
        
        result = sentiment_pipeline(text[:512])[0]
        
        label = result["label"]
        score = result["score"]
        
        sentiment_map = {"positive": 1, "negative": -1, "neutral": 0}
        sentiment_value = sentiment_map.get(label.lower(), 0)
        
        return {
            "sentiment": label,
            "sentiment_value": sentiment_value,
            "confidence": score,
        }
    except Exception:
        # Simple fallback: keyword-based sentiment if FinBERT fails
        return _simple_sentiment_analysis(text)


def _simple_sentiment_analysis(text):
    """Simple keyword-based sentiment analysis fallback."""
    text_lower = text.lower()
    
    positive_words = [
        "profit", "growth", "surge", "gain", "rise", "bullish", "positive",
        "upgrade", "outperform", "dividend", "bonus", "buyback", "approval",
        "expansion", "investment", "contract", "order", "partnership",
        "record", "highest", "strong", "improvement", "recovery",
    ]
    
    negative_words = [
        "loss", "decline", "fall", "drop", "crash", "bearish", "negative",
        "downgrade", "penalty", "fine", "investigation", "scam", "fraud",
        "layoff", "resignation", "default", "bankruptcy", "debt",
        "slowdown", "recession", "inflation", "crisis", "warning",
    ]
    
    pos_count = sum(1 for w in positive_words if w in text_lower)
    neg_count = sum(1 for w in negative_words if w in text_lower)
    
    if pos_count > neg_count:
        return {"sentiment": "positive", "sentiment_value": 1, "confidence": 0.6}
    elif neg_count > pos_count:
        return {"sentiment": "negative", "sentiment_value": -1, "confidence": 0.6}
    else:
        return {"sentiment": "neutral", "sentiment_value": 0, "confidence": 0.5}


def get_filtered_sentiment_news(company_ticker=None, max_articles=30):
    """
    End-to-end pipeline: fetch news → filter → analyze sentiment.
    
    Parameters
    ----------
    company_ticker : str, optional
        Company ticker to focus on
    max_articles : int
        Maximum number of articles to process
    
    Returns
    -------
    pd.DataFrame
        DataFrame with filtered and analyzed news
    """
    # Fetch news
    articles = fetch_live_news(company_ticker, page_size=max_articles * 2)
    
    if not articles:
        return pd.DataFrame()
    
    # Filter for market relevance
    filtered = filter_market_news(articles)
    
    if not filtered:
        return pd.DataFrame()
    
    # Take only top articles
    filtered = filtered[:max_articles]
    
    # Analyze sentiment for each article
    results = []
    for article in filtered:
        text = f"{article.get('title', '')} {article.get('description', '')}"
        
        sentiment_result = analyze_sentiment_finbert(text)
        
        results.append({
            "title": article.get("title", ""),
            "description": article.get("description", ""),
            "url": article.get("url", ""),
            "source": article.get("source", {}).get("name", ""),
            "published_at": article.get("publishedAt", ""),
            "sentiment": sentiment_result.get("sentiment", "neutral"),
            "sentiment_value": sentiment_result.get("sentiment_value", 0),
            "sentiment_confidence": sentiment_result.get("confidence", 0),
        })
    
    df = pd.DataFrame(results)
    
    # Aggregate by date
    if not df.empty and "published_at" in df.columns:
        df["date"] = pd.to_datetime(df["published_at"]).dt.date
        df["date"] = pd.to_datetime(df["date"])
    
    return df


if __name__ == "__main__":
    # Test the pipeline
    df = get_filtered_sentiment_news()
    print(f"Fetched {len(df)} market-relevant articles")
    if not df.empty:
        print(df[["title", "sentiment", "sentiment_value"]].head(10).to_string())