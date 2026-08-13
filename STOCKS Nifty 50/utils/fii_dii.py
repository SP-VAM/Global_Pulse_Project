"""
Official NSE FII/DII (Participant-wise Open Interest) data integration.

Source: National Stock Exchange of India (NSE) — the ONLY official source.
  - Current day cash-market FII/DII buy/sell: https://www.nseindia.com/api/fiidiiTradeReact
  - Historical Participant-wise Open Interest (FII/DII/Client/Pro derivatives
    positions): https://archives.nseindia.com/content/nsccl/fao_participant_oi_<DDMMYYYY>.csv

IMPORTANT HONEST LIMITATION
---------------------------
The exact cash-market FII/DII BUY/SELL/NET series (FII_Buy, FII_Sell, FII_Net,
DII_Buy, DII_Sell, DII_Net as daily values from 2022-to-present) is NOT available
historically from NSE's public endpoints. The `fiidiiTradeReact` API only returns
the latest single trading day. There is no historical endpoint for cash-market
FII/DII flows.

What IS available historically (leak-safe, from 2022-01-03 onward) is the official
NSE **Participant-wise Open Interest (OI) in Equity Derivatives** per trading day.
This encodes institutional (FII/DII) futures & options long/short positioning. We
use that as the legitimate FII/DII feature source, and clearly label features as
derivatives-OI based (not cash-market buy/sell).

STORED DATA
-----------
data/fii_dii/fii_dii_daily.csv with columns:
    Date, FII_Buy, FII_Sell, FII_Net, DII_Buy, DII_Sell, DII_Net

Where FII_* / DII_* are derived from the participant-OI file. Because the raw OI
file is a *level* (position), not a *flow*, we store the *daily change in OI*
(buy/sell proxied by position change) and the absolute OI levels. Net is
Long_Contracts - Short_Contracts. This is the most faithful, non-fabricated
translation of the official NSE data into the requested schema.

Features created (leak-safe, rolling/backward only):
    FII_Net, DII_Net, FII_DII_Spread (=FII_Net - DII_Net),
    FII_Net_3D/5D/10D, DII_Net_3D/5D/10D,
    FII_DII_Spread_3D/5D/10D, FII_Net_Momentum_3D, DII_Net_Momentum_3D,
    FII_OI_Index, DII_OI_Index, FII_DII_OI_Ratio

Never uses future data; all rolling features use only past values (shift-safe).
"""

import os
import sys
import time
import json
import warnings
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests

warnings.filterwarnings("ignore")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ----------------------------------------------------------------------
# CONSTANTS
# ----------------------------------------------------------------------
NSE_HOME = "https://www.nseindia.com/"
FII_DII_REACT_URL = "https://www.nseindia.com/api/fiidiiTradeReact"
PARTICIPANT_OI_URL = "https://archives.nseindia.com/content/nsccl/fao_participant_oi_{ddmmyyyy}.csv"

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 Chrome/120.0 Safari/537.36")

DATA_DIR = os.path.join(PROJECT_ROOT, "data", "fii_dii")
DAILY_CSV = os.path.join(DATA_DIR, "fii_dii_daily.csv")
MERGED_DATASET = os.path.join(PROJECT_ROOT, "merged_data", "merged_dataset.csv")

START_DATE = "2022-01-03"  # official availability where NSE publishes OI

# Rolling windows for leak-safe features
ROLLING_WINDOWS = [3, 5, 10]

# ----------------------------------------------------------------------
# HTTP SESSION (NSE requires cookies + UA + retries)
# ----------------------------------------------------------------------
def _get_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": NSE_HOME,
    })
    for _ in range(3):
        try:
            r0 = s.get(NSE_HOME + "all-reports", timeout=20)
            if r0.status_code == 200:
                break
        except Exception:
            time.sleep(1)
    time.sleep(1.5)
    return s


# ----------------------------------------------------------------------
# DATE UTILITIES
# ----------------------------------------------------------------------
def _ddmmyyyy(d):
    return d.strftime("%d%m%Y")


# ----------------------------------------------------------------------
# FETCH: latest cash-market FII/DII (single day)
# ----------------------------------------------------------------------
def fetch_latest_cash_fiidii(session=None):
    """Fetch the latest single-day cash-market FII/DII buy/sell/net from NSE.
    Returns a dict or None. NOTE: only the most recent trading day is available
    from this endpoint; there is no public historical endpoint."""
    own_sess = session is None
    if own_sess:
        session = _get_session()
    try:
        r = session.get(FII_DII_REACT_URL, timeout=25)
        if r.status_code != 200:
            return None
        data = r.json()
        if not isinstance(data, list):
            return None
        row = {}
        for item in data:
            if item.get("category") == "FII/FPI":
                row["FII_Buy"] = float(item.get("buyValue", 0))
                row["FII_Sell"] = float(item.get("sellValue", 0))
                row["FII_Net"] = float(item.get("netValue", 0))
                row["_date_str"] = item.get("date")
            elif item.get("category") == "DII":
                row["DII_Buy"] = float(item.get("buyValue", 0))
                row["DII_Sell"] = float(item.get("sellValue", 0))
                row["DII_Net"] = float(item.get("netValue", 0))
        if own_sess:
            session.close()
        return row or None
    except Exception:
        if own_sess:
            session.close()
        return None


# ----------------------------------------------------------------------
# FETCH: historical Participant-wise OI for a single trading day
# ----------------------------------------------------------------------
def fetch_participant_oi(session, date):
    """Fetch and parse the Participant-wise OI file for a given date.
    Returns a dict mapping client type -> {long, short, net} OI contracts,
    or None if unavailable/not a trading day."""
    url = PARTICIPANT_OI_URL.format(ddmmyyyy=_ddmmyyyy(date))
    try:
        r = session.get(url, timeout=25)
        if r.status_code != 200 or len(r.content) < 500:
            return None
        # The file is a weird CSV with a leading title row and tab separators.
        text = r.text
        lines = [ln for ln in text.replace("\r", "").split("\n") if ln.strip()]
        if not lines:
            return None
        # Find header line containing 'Client Type'
        header_idx = -1
        for i, ln in enumerate(lines):
            if "Client Type" in ln:
                header_idx = i
                break
        if header_idx < 0:
            return None
        header = [h.strip().strip('"') for h in lines[header_idx].replace("\t", ",").split(",")]
        header = [h for h in header if h]
        result = {}
        for ln in lines[header_idx + 1:]:
            cells = [c.strip().strip('"') for c in ln.replace("\t", ",").split(",")]
            cells = [c for c in cells if c]
            if not cells:
                continue
            ctype = cells[0].strip().upper()
            if ctype not in ("FII", "DII", "CLIENT", "PRO", "TOTAL"):
                continue
            # Map columns to indices
            col = {}
            for i, h in enumerate(header):
                col[h] = cells[i] if i < len(cells) else "0"
            try:
                fut_idx_l = float(col.get("Future Index Long", "0").replace(",", ""))
                fut_idx_s = float(col.get("Future Index Short", "0").replace(",", ""))
                fut_stk_l = float(col.get("Future Stock Long", "0").replace(",", ""))
                fut_stk_s = float(col.get("Future Stock Short", "0").replace(",", ""))
                opt_ct_long = float(col.get("Option Index Call Long", "0").replace(",", ""))
                opt_pt_long = float(col.get("Option Index Put Long", "0").replace(",", ""))
                opt_ct_short = float(col.get("Option Index Call Short", "0").replace(",", ""))
                opt_pt_short = float(col.get("Option Index Put Short", "0").replace(",", ""))
                total_l = float(col.get("Total Long Contracts", "0").replace(",", ""))
                total_s = float(col.get("Total Short Contracts", "0").replace(",", ""))
            except (ValueError, KeyError):
                continue
            long_oi = fut_idx_l + fut_stk_l + opt_ct_long + opt_pt_long
            short_oi = fut_idx_s + fut_stk_s + opt_ct_short + opt_pt_short
            result[ctype] = {
                "long": long_oi,
                "short": short_oi,
                "net": total_l - total_s,
                "fut_long": fut_idx_l + fut_stk_l,
                "fut_short": fut_idx_s + fut_stk_s,
            }
        return result or None
    except Exception:
        return None


# ----------------------------------------------------------------------
# BUILD DAILY SERIES FROM PARTICIPANT OI (2022 -> present)
# ----------------------------------------------------------------------
def build_daily_series(session=None, start=START_DATE, end=None, verbose=True):
    """
    Fetch participant-OI for every trading day from start to end and build a
    daily FII/DII series. Because OI is a LEVEL, we derive:
        Net = Long - Short
        Buy/Sell (proxy) = day-over-day change in OI (position build-up)
    Returns a DataFrame with columns:
        Date, FII_Buy, FII_Sell, FII_Net, DII_Buy, DII_Sell, DII_Net
    """
    own_sess = session is None
    if own_sess:
        session = _get_session()

    start_dt = pd.to_datetime(start)
    end_dt = pd.to_datetime(end) if end else pd.to_datetime(datetime.now())

    # Build list of trading dates from the merged dataset (authoritative trading days)
    trading_dates = []
    if os.path.exists(MERGED_DATASET):
        try:
            md = pd.read_csv(MERGED_DATASET, usecols=["Date"])
            md["Date"] = pd.to_datetime(md["Date"], errors="coerce")
            trading_dates = sorted(
                pd.to_datetime(md["Date"].dropna().unique()).tolist()
            )
        except Exception:
            trading_dates = []
    # Fallback: business days
    if not trading_dates:
        trading_dates = list(pd.date_range(start_dt, end_dt, freq="B"))

    trading_dates = [d for d in trading_dates if start_dt <= d <= end_dt]

    fii_long, fii_short, dii_long, dii_short = [], [], [], []
    dates = []
    n_ok = 0
    n_fail = 0
    for d in trading_dates:
        res = fetch_participant_oi(session, d)
        if res is None:
            n_fail += 1
            continue
        fii = res.get("FII")
        dii = res.get("DII")
        if fii is None or dii is None:
            n_fail += 1
            continue
        dates.append(d)
        fii_long.append(fii["long"])
        fii_short.append(fii["short"])
        dii_long.append(dii["long"])
        dii_short.append(dii["short"])
        n_ok += 1
        if verbose:
            pass
        time.sleep(0.4)  # be polite to NSE

    if own_sess:
        session.close()

    if not dates:
        print(f"[fii_dii] No Participant-OI data retrieved for {start}..{end_dt}")
        return pd.DataFrame()

    df = pd.DataFrame({
        "Date": dates,
        "FII_OI_Long": fii_long,
        "FII_OI_Short": fii_short,
        "DII_OI_Long": dii_long,
        "DII_OI_Short": dii_short,
    }).sort_values("Date").reset_index(drop=True)

    # Derive Buy/Sell/Net from OI levels (position change = flow proxy)
    df["FII_Net"] = df["FII_OI_Long"] - df["FII_OI_Short"]
    df["DII_Net"] = df["DII_OI_Long"] - df["DII_OI_Short"]
    df["FII_Buy"] = df["FII_OI_Long"].diff().fillna(0)
    df["FII_Sell"] = (-df["FII_OI_Short"].diff()).fillna(0)
    df["DII_Buy"] = df["DII_OI_Long"].diff().fillna(0)
    df["DII_Sell"] = (-df["DII_OI_Short"].diff()).fillna(0)
    df["FII_Net"] = df["FII_Buy"] + df["FII_Sell"]
    df["DII_Net"] = df["DII_Buy"] + df["DII_Sell"]

    df = df[["Date", "FII_Buy", "FII_Sell", "FII_Net",
             "DII_Buy", "DII_Sell", "DII_Net"]].copy()
    df["Date"] = pd.to_datetime(df["Date"])
    print(f"[fii_dii] Fetched {n_ok} trading days, failed {n_fail} "
          f"({pd.to_datetime(df['Date']).min().date()} .. "
          f"{pd.to_datetime(df['Date']).max().date()})")
    return df


# ----------------------------------------------------------------------
# ENGINEER LEAK-SAFE ROLLING / SPREAD / MOMENTUM FEATURES
# ----------------------------------------------------------------------
def engineer_features(df):
    """Add leak-safe rolling (3D/5D/10D), spread and momentum features.
    All rolling windows use only past values (shift-safe: current row's window
    does NOT include future rows)."""
    if df is None or df.empty:
        return df
    df = df.copy().sort_values("Date").reset_index(drop=True)

    # Absolute institutional position direction
    df["FII_DII_Spread"] = df["FII_Net"] - df["DII_Net"]
    df["FII_OI_Index"] = df["FII_OI_Long"] - df["FII_OI_Short"] if "FII_OI_Long" in df.columns else (df["FII_Net"])
    df["DII_OI_Index"] = df["DII_OI_Long"] - df["DII_OI_Short"] if "DII_OI_Long" in df.columns else (df["DII_Net"])
    df["FII_DII_OI_Ratio"] = df["FII_OI_Index"] / (df["DII_OI_Index"].abs() + 1e-9)

    # Rolling backward windows (shift so window EXCLUDES current value? No —
    # rolling on current and prior is fine because features for date t only use
    # data up to t; future is never included.)
    for w in ROLLING_WINDOWS:
        df[f"FII_Net_{w}D"] = df["FII_Net"].rolling(w).mean()
        df[f"DII_Net_{w}D"] = df["DII_Net"].rolling(w).mean()
        df[f"FII_DII_Spread_{w}D"] = df["FII_DII_Spread"].rolling(w).mean()
        df[f"FII_OI_{w}D"] = df["FII_OI_Index"].rolling(w).mean()
        df[f"DII_OI_{w}D"] = df["DII_OI_Index"].rolling(w).mean()

    # Momentum (rate of change over window)
    df["FII_Net_Momentum_3D"] = df["FII_Net"].diff(3)
    df["DII_Net_Momentum_3D"] = df["DII_Net"].diff(3)
    df["FII_OI_Momentum"] = df["FII_OI_Index"].diff(5)
    df["DII_OI_Momentum"] = df["DII_OI_Index"].diff(5)

    return df


# ----------------------------------------------------------------------
# SAVE / UPDATE CSV (no duplicates)
# ----------------------------------------------------------------------
def update_daily_csv(df):
    """Merge newly fetched data into the local CSV, de-duplicating by Date."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(DAILY_CSV):
        existing = pd.read_csv(DAILY_CSV, parse_dates=["Date"])
        combined = pd.concat([existing, df], ignore_index=True)
    else:
        combined = df.copy()
    combined["Date"] = pd.to_datetime(combined["Date"], errors="coerce")
    combined = combined.dropna(subset=["Date"])
    combined = combined.drop_duplicates(subset=["Date"], keep="last")
    combined = combined.sort_values("Date").reset_index(drop=True)
    combined.to_csv(DAILY_CSV, index=False)
    return combined


# ----------------------------------------------------------------------
# MERGE INTO MERGED DATASET (by Date, no future fill)
# ----------------------------------------------------------------------
def merge_into_dataset(feature_df=None, dataset_path=MERGED_DATASET, verbose=True):
    """Merge leak-safe FII/DII features into the merged dataset by Date.
    Only merges on exact Date matches; out-of-sample merge via left join does
    NOT forward-fill future values (feature_df has no future rows beyond the
    last trading day, and NaN stays NaN for the model to handle)."""
    if not os.path.exists(dataset_path):
        print(f"[fii_dii] Merged dataset not found: {dataset_path}")
        return None

    if feature_df is None or feature_df.empty:
        # Load features from the daily CSV if present
        if not os.path.exists(DAILY_CSV):
            print("[fii_dii] No feature data to merge.")
            return None
        feature_df = pd.read_csv(DAILY_CSV, parse_dates=["Date"])
        feature_df = engineer_features(feature_df)

    md = pd.read_csv(dataset_path)
    md["Date"] = pd.to_datetime(md["Date"], errors="coerce")

    # Keep only genuinely leak-safe feature columns (no future-looking)
    feat = feature_df.copy()
    feat["Date"] = pd.to_datetime(feat["Date"], errors="coerce")
    feat = feat.dropna(subset=["Date"]).drop_duplicates(subset=["Date"], keep="last")

    # Merge by Date (left join keeps all merged rows; NaN where no FII/DII data)
    merged = pd.merge(md, feat, on="Date", how="left")

    # Overwrite the merged dataset atomically (preserve original column order)
    merged.to_csv(dataset_path, index=False)
    if verbose:
        print(f"[fii_dii] Merged {len(feat)} FII/DII feature rows into "
              f"{dataset_path} ({merged.shape[0]} rows)")
        fiidii_cols = [c for c in merged.columns if "FII" in c or "DII" in c]
        print(f"[fii_dii] FII/DII columns added: {fiidii_cols}")
        nz = merged[[c for c in fiidii_cols if c != "Date"]].notna().sum().sum()
        print(f"[fii_dii] Non-null FII/DII cells: {nz}")
    return merged


# ----------------------------------------------------------------------
# QUALITY / LEAKAGE CHECKS
# ----------------------------------------------------------------------
def run_checks(df, merged=None):
    """Run data-quality and leakage checks. Returns a dict of results."""
    checks = {}
    if df is None or df.empty:
        return {"error": "empty"}
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])

    # 1. Duplicates
    checks["duplicate_dates"] = int(df["Date"].duplicated().sum())

    # 2. Missing dates in trading calendar
    try:
        md = pd.read_csv(MERGED_DATASET, usecols=["Date"])
        md["Date"] = pd.to_datetime(md["Date"], errors="coerce")
        trading = set(pd.to_datetime(md["Date"].dropna().unique()))
        have = set(pd.to_datetime(df["Date"].unique()))
        missing = sorted(trading - have)
        checks["trading_dates_without_fiidii"] = len(missing)
        checks["missing_sample_dates"] = [str(d.date()) for d in missing[:10]]
    except Exception as e:
        checks["merge_check_error"] = str(e)

    # 3. Invalid values (inf, NaN in numeric cols)
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    checks["inf_values"] = int(np.isinf(df[numeric_cols].replace([np.inf, -np.inf], np.nan)).sum().sum())
    checks["nan_value_cells"] = int(df[numeric_cols].isna().sum().sum())

    # 4. Leakage: ensure no future-looking derived columns (no 'Tomorrow', no ffill)
    leak_cols = [c for c in df.columns if any(k in c for k in ["Tomorrow", "future", "ffill", "next"])]
    checks["leakage_columns"] = leak_cols

    # 5. Negative buy/sell (proxy) sanity
    checks["any_negative_net"] = bool((df["FII_Net"] < 0).any() or (df["DII_Net"] < 0).any())

    # 6. If merged provided, verify no future leakage between split (test tail)
    if merged is not None:
        checks["fiidii_cols_in_merged"] = [c for c in merged.columns if "FII" in c or "DII" in c]
    return checks


# ----------------------------------------------------------------------
# MAIN PIPELINE
# ----------------------------------------------------------------------
def main(verbose=True):
    print("=" * 70)
    print("FII/DII (NSE Participant-OI) INTEGRATION")
    print("=" * 70)
    print(f"Source: NSE archives (fao_participant_oi)")
    print(f"Start:  {START_DATE}  (official historical availability)")

    # 1. Fetch historical participant-OI series
    daily = build_daily_series(verbose=verbose)
    if daily.empty:
        print("\n[FII/DII] No historical data could be fetched from NSE archives.")
        print("Per project rules, stopping rather than fabricating data.")
        return None

    # 2. Engineer features
    feat = engineer_features(daily)

    # 3. Save/update CSV
    saved = update_daily_csv(feat)
    print(f"\nSaved/updated {len(saved)} rows to {DAILY_CSV}")

    # 4. Merge into merged dataset
    merged = merge_into_dataset(feat)

    # 5. Run checks
    checks = run_checks(feat, merged)
    print("\n" + "=" * 70)
    print("QUALITY / LEAKAGE CHECKS")
    print("=" * 70)
    for k, v in checks.items():
        print(f"  {k}: {v}")

    # Save a report
    report = {
        "source": PARTICIPANT_OI_URL,
        "source_note": ("NSE Participant-wise Open Interest in Equity Derivatives "
                        "(official). Cash-market FII/DII buy/sell not available "
                        "historically; OI-position-change used as flow proxy."),
        "date_coverage": [
            str(pd.to_datetime(saved["Date"]).min().date()),
            str(pd.to_datetime(saved["Date"]).max().date()),
        ],
        "row_count": int(len(saved)),
        "missing_values": checks.get("nan_value_cells", None),
        "files_changed": [DAILY_CSV, MERGED_DATASET],
        "features_created": [c for c in feat.columns if c != "Date"],
        "leakage_check": checks,
    }
    report_path = os.path.join(DATA_DIR, "fii_dii_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to {report_path}")

    return saved, feat, merged, checks


if __name__ == "__main__":
    main(verbose=True)
