"""Connectivity and availability check for all data sources."""
import warnings
warnings.filterwarnings("ignore")
import yfinance as yf
import requests

print("=" * 60)
print("YFINANCE TICKER CHECK")
print("=" * 60)
tickers = {
    "INDIAVIX": "^INDIAVIX",
    "SENSEX": "^BSESN",
    "BANKNIFTY": "^NSEBANK",
    "NIFTY_IT": "^CNXIT",
    "NIFTY_AUTO": "^CNXAUTO",
    "NIFTY_PHARMA": "^CNXPHARMA",
    "NIFTY_FMCG": "^CNXFMCG",
    "NIFTY_METAL": "^CNXMETAL",
    "NIFTY_ENERGY": "^CNXENERGY",
    "NIFTY_REALTY": "^CNXREALTY",
    "NIFTY_PSUBANK": "^CNXPSUBANK",
    "NIFTY_FINSERV": "^CNXFIN",
    "USDINR": "INR=X",
    "BRENT": "BZ=F",
    "WTI": "CL=F",
    "GOLD": "GC=F",
    "US10Y": "^TNX",
}
for name, tk in tickers.items():
    try:
        df = yf.download(tk, start="2022-01-01", end="2022-01-15",
                         interval="1d", auto_adjust=False, progress=False)
        if df is not None and not df.empty:
            print(f"OK   {name:14s} {tk:12s} rows={len(df)}")
        else:
            print(f"FAIL {name:14s} {tk:12s} EMPTY")
    except Exception as e:
        print(f"FAIL {name:14s} {tk:12s} {type(e).__name__}: {e}")

print()
print("=" * 60)
print("NSE / WEB SOURCE CHECK")
print("=" * 60)
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0"}
tests = [
    ("FO_old_format", "https://archives.nseindia.com/archives/fo/bhav/fo05AUG2026.csv"),
    ("FO_udiff", "https://archives.nseindia.com/archives/fo/udiff/fo05AUG2026.csv"),
    ("NSE_home", "https://www.nseindia.com/"),
    ("FII_DII", "https://www.nseindia.com/api/fiidiiTradeReact"),
]
for name, url in tests:
    try:
        r = requests.get(url, headers=headers, timeout=15)
        print(f"{name:14s} status={r.status_code} len={len(r.content)}")
        if r.status_code == 200 and "FO" in name:
            print("   first 150:", r.content[:150])
    except Exception as e:
        print(f"{name:14s} ERROR {type(e).__name__}: {e}")
