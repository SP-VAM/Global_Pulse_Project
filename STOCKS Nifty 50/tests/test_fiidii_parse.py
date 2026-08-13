"""Quick verification of NSE FII/DII parsing and fetch."""
import sys, warnings
sys.path.insert(0, ".")
warnings.filterwarnings("ignore")
import pandas as pd
from utils.fii_dii import (
    _get_session, fetch_latest_cash_fiidii, fetch_participant_oi,
    build_daily_series, engineer_features
)

s = _get_session()

# 1. Latest cash FII/DII
cash = fetch_latest_cash_fiidii(s)
print("Latest cash FII/DII:", cash)
print("---")

# 2. Participant OI parsing on one date
res = fetch_participant_oi(s, pd.to_datetime("2024-07-05"))
print("Participant OI 2024-07-05:")
if res:
    for k, v in res.items():
        print(f"  {k}: long={v['long']:.0f} short={v['short']:.0f} net={v['net']:.0f}")
else:
    print("  None")
print("---")

# 3. Build a small daily series over a few dates to test pipeline
s2 = _get_session()
small = build_daily_series(s2, start="2024-07-01", end="2024-07-10", verbose=False)
print("Small build_daily_series rows:", len(small))
if not small.empty:
    print(small.to_string())
    print("---")
    feat = engineer_features(small)
    print("Engineered features:")
    print(feat.columns.tolist())
    print(feat.to_string())
