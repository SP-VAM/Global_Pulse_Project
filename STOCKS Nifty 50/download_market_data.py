"""
Download and compute market-wide features.

This script downloads broad indices (NIFTY, SENSEX, BANKNIFTY, INDIAVIX),
sector indices (IT, AUTO, PHARMA, FMCG, METAL, ENERGY, REALTY, PSU BANK),
and macro series (USD/INR, Brent, WTI, Gold, US 10Y yield) via yfinance.
It also computes market breadth from locally stored NIFTY-50 stock CSVs
and market regime/strength/alignment scores.

Each dataset is saved separately under `market_data/` with source metadata,
then combined into `market_features.csv`.

Data coverage: 2022-01-03 (project start) through the latest available date.

Usage:
    python download_market_data.py
"""

import os
import sys
import json
import warnings
import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime

OUTPUT_DIR = "market_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Project data start / end
START = "2022-01-01"
END = datetime.now().strftime("%Y-%m-%d")  # Dynamic end date (today)

# Macro series (name -> yfinance ticker)
MACRO_TICKERS = {
    "USDINR": "INR=X",
    "BRENT": "BZ=F",
    "WTI": "CL=F",
    "GOLD": "GC=F",
    "US10Y": "^TNX",
}

# Sector indices beyond those in utils.market_data
SECTOR_INDEX_TICKERS_EXTRA = {
    "PSUBANK": "^CNXPSUBANK",
}

# Metadata manifest
manifest = {}


def _flatten_columns(df):
    """Flatten yfinance multi-index columns to simple names."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    else:
        df.columns = [str(c).split(",")[0].strip() for c in df.columns]
    return df


def download_series(ticker, name, start=START, end=END):
    """Download a daily OHLCV series, return clean DataFrame with Date."""
    try:
        data = yf.download(ticker, start=start, end=end, interval="1d",
                           auto_adjust=False, progress=False)
    except Exception as e:
        print(f"  [ERROR] {name} ({ticker}): {e}")
        return pd.DataFrame()
    if data is None or data.empty:
        print(f"  [WARN] {name} ({ticker}): no data")
        return pd.DataFrame()
    data = _flatten_columns(data.reset_index())
    if "Date" not in data.columns:
        data = data.rename(columns={"index": "Date"})
    data = data[["Date", "Open", "High", "Low", "Close", "Volume"]].copy()
    data["Date"] = pd.to_datetime(data["Date"])
    data = data.drop_duplicates(subset=["Date"]).sort_values("Date")
    return data


def save_dataset(df, name, source):
    """Save a dataset to market_data/ with a metadata manifest entry."""
    if df is None or df.empty:
        print(f"  [SKIP] {name}: empty, not saved")
        return df
    path = os.path.join(OUTPUT_DIR, f"{name}.csv")
    df.to_csv(path, index=False)
    manifest[name] = {
        "source": source,
        "file": path,
        "rows": int(len(df)),
        "start": str(df["Date"].min().date()),
        "end": str(df["Date"].max().date()),
        "columns": df.columns.tolist(),
    }
    print(f"  [OK] {name}: {len(df)} rows, {df['Date'].min().date()} -> {df['Date'].max().date()}")
    return df


def main():
    print("=" * 60)
    print("MARKET-WIDE DATA DOWNLOAD")
    print(f"Period: {START} to {END}")
    print("=" * 60)

    from utils import market_data as md

    # ---------- 1. Broad indices ----------
    print("\n[1/5] Broad indices (NIFTY, SENSEX, BANKNIFTY, INDIAVIX)...")
    broad = {}
    for name, ticker in md.BROAD_INDEX_TICKERS.items():
        df = download_series(ticker, name)
        if df.empty:
            continue
        broad[name] = df
        save_dataset(df, f"index_{name}", "yfinance")

    # ---------- 2. Sector indices ----------
    print("\n[2/5] Sector indices...")
    sector = {}
    sector_tickers = dict(md.SECTOR_INDEX_TICKERS)
    sector_tickers.update(SECTOR_INDEX_TICKERS_EXTRA)
    for sec, ticker in sector_tickers.items():
        if sec == "BANK":
            # BankNifty already downloaded
            if "BANKNIFTY" in broad:
                sector[sec] = broad["BANKNIFTY"].copy()
                save_dataset(sector[sec], f"sector_{sec}", "yfinance (BankNifty)")
                continue
        df = download_series(ticker, f"sector_{sec}")
        if df.empty:
            continue
        sector[sec] = df
        save_dataset(df, f"sector_{sec}", "yfinance")

    # ---------- 3. Macro series ----------
    print("\n[3/5] Macro series (USD/INR, Brent, WTI, Gold, US10Y)...")
    macro = {}
    for name, ticker in MACRO_TICKERS.items():
        df = download_series(ticker, name)
        if df.empty:
            continue
        macro[name] = df
        save_dataset(df, f"macro_{name}", "yfinance")

    # ---------- 4. Aggregate all into a single market_features table ----------
    print("\n[4/5] Building market_features.csv...")
    # Start with broad features
    if "NIFTY" not in broad:
        print("  [ERROR] NIFTY data missing; cannot build market features.")
        return None

    nifty = md.compute_index_features(broad["NIFTY"].copy(), prefix="NIFTY")
    # Add NIFTY_Close (needed by regime/strength functions)
    nifty["NIFTY_Close"] = nifty["Close"]
    merged = nifty[["Date"] + [c for c in nifty.columns if c.startswith("NIFTY_")]].copy()

    for name, df in broad.items():
        if name == "NIFTY":
            continue
        if name == "INDIAVIX":
            feat = md.compute_vix_features(df.copy(), prefix="INDIAVIX")
        else:
            feat = md.compute_index_features(df.copy(), prefix=name)
        cols = ["Date"] + [c for c in feat.columns if c.startswith(name + "_")]
        merged = merged.merge(feat[cols], on="Date", how="left")

    for sec, df in sector.items():
        if sec == "BANK":
            continue  # already covered as BANKNIFTY broad
        feat = md.compute_index_features(df.copy(), prefix=f"SECTOR_{sec}")
        cols = ["Date"] + [c for c in feat.columns if c.startswith(f"SECTOR_{sec}_")]
        merged = merged.merge(feat[cols], on="Date", how="left")

    # Macro features (raw OHLCV + returns)
    for name, df in macro.items():
        f = df.copy()
        f[f"{name}_Daily_Return"] = f["Close"].pct_change() * 100
        f[f"{name}_5D_Return"] = f["Close"].pct_change(5) * 100
        f[f"{name}_20D_Return"] = f["Close"].pct_change(20) * 100
        rename = {c: f"MACRO_{name}_{c}" if c not in ("Date",) else c
                  for c in f.columns if c not in ("Open", "High", "Low", "Volume")}
        f = f.rename(columns=rename)
        keep = ["Date"] + [c for c in f.columns if c.startswith("MACRO_")]
        merged = merged.merge(f[keep], on="Date", how="left")

    # ---------- Market breadth from local stock CSVs ----------
    print("\n[5/5] Computing market breadth from local stock CSVs...")
    breadth = md.compute_market_breadth("stock_data")
    if not breadth.empty:
        # compute_market_breadth returns a Date-indexed df (Date dropped as column)
        breadth = breadth.reset_index().rename(columns={"index": "Date"})
        breadth["Date"] = pd.to_datetime(breadth["Date"])
        save_dataset(breadth, "market_breadth", "computed-from-stock_data/")
        merged = merged.merge(breadth, on="Date", how="left")

    # Market regime + strength
    merged = md.compute_market_regime(merged, None)
    merged["Market_Strength_Score"] = md.compute_market_strength(merged, None)

    # Save combined
    merged_path = os.path.join(OUTPUT_DIR, "market_features.csv")
    merged.to_csv(merged_path, index=False)
    manifest["market_features"] = {
        "source": "combined (yfinance + computed breadth)",
        "file": merged_path,
        "rows": int(len(merged)),
        "start": str(merged["Date"].min().date()),
        "end": str(merged["Date"].max().date()),
        "columns": merged.columns.tolist(),
    }

    # Save manifest
    manifest_path = os.path.join(OUTPUT_DIR, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest saved to {manifest_path}")

    print("\n" + "=" * 60)
    print(f"market_features.csv: {merged.shape}")
    print(f"Date range: {merged['Date'].min().date()} to {merged['Date'].max().date()}")
    print(f"Columns ({len(merged.columns)}):")
    for c in merged.columns:
        print(f"  - {c}")
    print("=" * 60)
    return merged


if __name__ == "__main__":
    df = main()
    if df is not None:
        print("\nMarket data generation complete.")
    else:
        print("\nMarket data generation failed.")
