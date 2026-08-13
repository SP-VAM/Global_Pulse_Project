"""Examine NSE FO participant OI response and historical availability."""
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
            break
    except Exception:
        pass
time.sleep(2)

# Current content
url = "https://archives.nseindia.com/content/nsccl/fao_participant_oi_03082026.csv"
try:
    r = s.get(url, timeout=15)
    print(f"status={r.status_code} len={len(r.content)}")
    print("content:", r.content.decode('utf-8', errors='ignore')[:500])
except Exception as e:
    print("err", type(e).__name__, e)

# Test a historical month file - the pattern is fao_participant_oi_<ddmonyyyy>.csv
# Try a real past date
for d in ["31MAR2024", "01MAR2024", "28FEB2025"]:
    u = f"https://archives.nseindia.com/content/nsccl/fao_participant_oi_{d}.csv"
    try:
        rr = s.get(u, timeout=15)
        print(f"\n{u}\n  status={rr.status_code} len={len(rr.content)}")
        if rr.status_code == 200:
            print("  head:", rr.content.decode('utf-8', errors='ignore')[:150])
    except Exception as e:
        print(f"\n{u} error {type(e).__name__}")
