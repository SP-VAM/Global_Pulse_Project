"""Detailed NSE archive / FII-DII check with correct session handling."""
import warnings
warnings.filterwarnings("ignore")
import requests
import datetime

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"

# Establish cookies via home page first (NSE requires cookie + retries)
s = requests.Session()
s.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})

# Try to get a cookie from home
try:
    r0 = s.get("https://www.nseindia.com/", timeout=15)
    print("home status:", r0.status_code)
except Exception as e:
    print("home error:", type(e).__name__, e)

# FII/DII API
try:
    r = s.get("https://www.nseindia.com/api/fiidiiTradeReact", timeout=15)
    print("\nFII_DII status:", r.status_code)
    print("FII_DII body:", r.text[:500])
except Exception as e:
    print("FII_DII error:", type(e).__name__, e)

# Try a recent known trading day for FO bhavcopy. Use 2026-08-06 (Thursday).
for fmt in ["fo", "udiff"]:
    url = f"https://archives.nseindia.com/archives/fo/{fmt}/fo06AUG2026.csv"
    try:
        r = s.get(url, headers={"User-Agent": UA}, timeout=20)
        print(f"\n{url}")
        print(f"  status={r.status_code} len={len(r.content)}")
        if r.status_code == 200:
            print("  head:", r.content[:200])
    except Exception as e:
        print(f"{url} error: {type(e).__name__} {e}")

# Also test equity bhavcopy to see if archives reachable at all
for d in ["06AUG2026", "05AUG2026", "04AUG2026"]:
    url = f"https://archives.nseindia.com/products/content/sec_bhavdata_full_{d}.csv"
    try:
        r = s.get(url, headers={"User-Agent": UA}, timeout=20)
        print(f"\n{url}")
        print(f"  status={r.status_code} len={len(r.content)}")
    except Exception as e:
        print(f"{url} error: {type(e).__name__} {e}")
