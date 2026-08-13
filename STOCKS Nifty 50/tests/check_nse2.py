"""Test NSE archives with real historical dates to confirm availability."""
import warnings
warnings.filterwarnings("ignore")
import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
s = requests.Session()
s.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9",
                  "Referer": "https://www.nseindia.com/"})

# Try to get cookies
for _ in range(3):
    try:
        r0 = s.get("https://www.nseindia.com/all-reports", timeout=15)
        if r0.status_code == 200:
            print("home ok", r0.status_code)
            break
    except Exception as e:
        print("home retry err", type(e).__name__)

import time
time.sleep(2)

# Test a REAL past date that NSE definitely has: 2024-03-01 (Friday)
dates = ["01MAR2024", "05JUL2024", "06AUG2024"]
for d in dates:
    url = f"https://archives.nseindia.com/products/content/sec_bhavdata_full_{d}.csv"
    try:
        r = s.get(url, headers={"User-Agent": UA, "Referer": "https://www.nseindia.com/"}, timeout=20)
        print(f"{url}\n  status={r.status_code} len={len(r.content)}")
        if r.status_code == 200 and r.content[:3] == b'\xef\xbb\xbf':
            print("  UTF8 BOM, first:", r.content[:80].decode('utf-8-sig', errors='ignore').replace('\n',' '))
    except Exception as e:
        print(f"{url} error: {type(e).__name__} {e}")

# FII DII historical - test the only available endpoint again
print("\nFII/DII API:")
try:
    r = s.get("https://www.nseindia.com/api/fiidiiTradeReact", timeout=15)
    print("status:", r.status_code)
    print(r.text[:600])
except Exception as e:
    print("err", type(e).__name__, e)
