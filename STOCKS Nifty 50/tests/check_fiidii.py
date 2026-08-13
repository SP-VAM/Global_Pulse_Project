"""Check FII/DII historical data availability via NSE endpoints."""
import warnings
warnings.filterwarnings("ignore")
import requests, time

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
s = requests.Session()
s.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9",
                  "Referer": "https://www.nseindia.com/"})
for _ in range(3):
    try:
        r0 = s.get("https://www.nseindia.com/all-reports", timeout=15)
        if r0.status_code == 200:
            print("home ok", r0.status_code)
            break
    except Exception as e:
        print("home retry", type(e).__name__)
time.sleep(2)

# Try historical FII/DII endpoints
endpoints = {
    "fiidiiTradeReact": "https://www.nseindia.com/api/fiidiiTradeReact",
    "fiidiiTrade_recent": "https://www.nseindia.com/api/fiidiiTradeBody",
}
for name, url in endpoints.items():
    try:
        r = s.get(url, timeout=15)
        print(f"\n{name}: status={r.status_code}")
        print(r.text[:400])
    except Exception as e:
        print(f"\n{name}: error {type(e).__name__} {e}")

# Check if there is a historical CSV (sometimes under archives)
for url in [
    "https://archives.nseindia.com/content/nsccl/fao_participant_oi_03082026.csv",
    "https://archives.nseindia.com/content/csv/oi_03Aug2026.csv",
]:
    try:
        r = s.get(url, timeout=15)
        print(f"\n{url}: status={r.status_code} len={len(r.content)}")
    except Exception as e:
        print(f"\n{url}: error {type(e).__name__}")
