"""
Merge sector-index features into the merged_dataset.csv (point-in-time, leak-safe).

Sector features from market_features/market_features.csv are joined by exact Date
using merge_asof backward (no future leakage). This makes the features available
to the dashboard and predictions for the 10D binary sector-enhanced model.
"""
import os
import sys
import warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.abspath(__file__))
MERGED_PATH = os.path.join(ROOT, "merged_data", "merged_dataset.csv")
MARKET_FEATURES_PATH = os.path.join(ROOT, "market_data", "market_features.csv")


def main():
    print("=" * 60)
    print("MERGE SECTOR FEATURES INTO MERGED DATASET")
    print("=" * 60)

    # Load merged dataset
    df = pd.read_csv(MERGED_PATH, parse_dates=["Date"])
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).copy()
    print(f"Merged dataset: {df.shape}")

    # Load market features
    mf = pd.read_csv(MARKET_FEATURES_PATH, parse_dates=["Date"])
    mf = mf.drop_duplicates(subset=["Date"]).set_index("Date").sort_index()
    mf_flat = mf.reset_index()
    mf_flat["Date"] = pd.to_datetime(mf_flat["Date"])

    # Only sector columns not already present
    sector_cols = [c for c in mf_flat.columns if c.startswith("SECTOR_")]
    base_cols = set(df.columns)
    sector_cols = [c for c in sector_cols if c not in base_cols]
    print(f"Sector features to add: {len(sector_cols)}")

    if not sector_cols:
        print("No new sector columns to add. Already present.")
        return

    # Point-in-time merge (backward)
    mf_for_merge = mf_flat[["Date"] + sector_cols].copy()
    df = df.sort_values("Date").reset_index(drop=True)
    merged = pd.merge_asof(df, mf_for_merge, on="Date", direction="backward")

    # Save
    merged.to_csv(MERGED_PATH, index=False)
    print(f"Saved merged dataset with sector features: {merged.shape}")
    print(f"New columns: {sector_cols[:5]}... (+{len(sector_cols)} total)")


if __name__ == "__main__":
    main()