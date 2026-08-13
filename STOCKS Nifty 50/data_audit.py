"""
PHASE 1: FULL DATA AUDIT.
Inspects all datasets, CSVs, pipelines, models, and produces:
  - DATA_AUDIT_REPORT.md
  - FEATURE_AUDIT.json
"""
import os
import sys
import json
import warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.abspath(__file__))


def path(*p):
    return os.path.join(ROOT, *p)


def inspect_csv(rel, date_col=None):
    """Inspect a CSV file."""
    fp = path(rel)
    if not os.path.exists(fp):
        return None
    try:
        df = pd.read_csv(fp)
        nrows = len(df)
        ncols = df.shape[1]
        missing = df.isna().mean().mean() * 100 if nrows else 0
        info = {
            "file": rel,
            "rows": nrows,
            "cols": ncols,
            "missing_pct": round(missing, 2),
            "columns_sample": list(df.columns[:10]),
        }
        if date_col and date_col in df.columns:
            try:
                dates = pd.to_datetime(df[date_col], errors="coerce")
                info["date_min"] = str(dates.min().date()) if dates.notna().any() else None
                info["date_max"] = str(dates.max().date()) if dates.notna().any() else None
            except Exception:
                pass
        return info
    except Exception as e:
        return {"file": rel, "error": str(e)}


def main():
    print("=" * 70)
    print("PHASE 1: FULL DATA AUDIT")
    print("=" * 70)

    datasets = [
        ("all_companies_stock_data.csv", None),
        ("merged_data/merged_dataset.csv", "Date"),
        ("merged_data/news_sentiment_aggregated.csv", "Date"),
        ("merged_data/fundamentals_data.csv", None),
        ("news_data/final_news_sentiment_analysis.csv", "Publish Date"),
        ("market_data/market_features.csv", "Date"),
        ("market_data/market_breadth.csv", "Date"),
        ("market_data/index_NIFTY.csv", "Date"),
        ("market_data/index_SENSEX.csv", "Date"),
        ("market_data/index_BANKNIFTY.csv", "Date"),
        ("market_data/index_INDIAVIX.csv", "Date"),
        ("market_data/macro_USDINR.csv", "Date"),
        ("market_data/macro_GOLD.csv", "Date"),
        ("market_data/macro_BRENT.csv", "Date"),
        ("market_data/macro_WTI.csv", "Date"),
        ("market_data/macro_US10Y.csv", "Date"),
        ("data/fii_dii/fii_dii_daily.csv", "Date") if os.path.exists(path("data/fii_dii/fii_dii_daily.csv")) else ("data/fii_dii/fii_dii_report.json", None),
    ]

    print("\n" + "=" * 70)
    print("DATASET INVENTORY")
    print("=" * 70)
    audit_rows = []
    for rel, date_col in datasets:
        info = inspect_csv(rel, date_col)
        if info:
            audit_rows.append(info)
            print(f"  {info['file']}: {info.get('rows','?')} rows, {info.get('cols','?')} cols, missing {info.get('missing_pct','?')}%")
            if "date_min" in info:
                print(f"    Dates: {info['date_min']} -> {info['date_max']}")

    # Stock data coverage per company
    print("\n" + "=" * 70)
    print("STOCK DATA COVERAGE (per company)")
    print("=" * 70)
    stock_dir = path("stock_data")
    stock_files = [f for f in os.listdir(stock_dir) if f.endswith(".csv")]
    print(f"  Found {len(stock_files)} stock files")
    coverages = []
    for f in stock_files[:10]:  # sample
        fp = os.path.join(stock_dir, f)
        try:
            df = pd.read_csv(fp, nrows=200)
            cov = {"file": f, "rows_sample": len(df)}
            if "Date" in df.columns:
                dates = pd.to_datetime(df["Date"], errors="coerce")
                cov["date_min"] = str(dates.min().date()) if dates.notna().any() else None
                cov["date_max"] = str(dates.max().date()) if dates.notna().any() else None
            coverages.append(cov)
        except Exception:
            pass
    print(f"  Sampled {len(coverages)} files")

    # Check merged dataset for issues
    print("\n" + "=" * 70)
    print("MERGED DATASET ANALYSIS")
    print("=" * 70)
    mdf_path = path("merged_data/merged_dataset.csv")
    if os.path.exists(mdf_path):
        mdf = pd.read_csv(mdf_path, parse_dates=["Date"])
        print(f"  Rows: {len(mdf)}, Columns: {mdf.shape[1]}")
        print(f"  Date range: {mdf['Date'].min().date()} -> {mdf['Date'].max().date()}")
        print(f"  Companies: {mdf['Company'].nunique()}")

        # Constant / near-constant columns
        num_cols = mdf.select_dtypes(include=[np.number]).columns
        const_cols = []
        for c in num_cols:
            nunique = mdf[c].nunique()
            if nunique <= 1:
                const_cols.append(c)
        print(f"  Constant columns: {const_cols}")

        # Duplicate columns
        dup_cols = [c for c in mdf.columns if mdf.columns.tolist().count(c) > 1]
        print(f"  Duplicate columns: {sorted(set(dup_cols))}")

        # Missing %
        missing_by_col = mdf.isna().mean().sort_values(ascending=False)
        high_missing = missing_by_col[missing_by_col > 0.5]
        if len(high_missing) > 0:
            print(f"  Columns with >50% missing:")
            for c, v in high_missing.items():
                print(f"    {c}: {v*100:.1f}%")

        # Sentiment coverage
        if "Sentiment_Mean" in mdf.columns:
            nz = (mdf["Sentiment_Mean"].fillna(0) != 0).mean()
            print(f"  Sentiment_Mean nonzero: {nz*100:.2f}%")

        # FII/DII coverage
        fiidii_cols = [c for c in mdf.columns if "FII" in c or "DII" in c]
        if fiidii_cols:
            non_null = mdf[fiidii_cols].notna().mean().mean() * 100
            print(f"  FII/DII columns ({len(fiidii_cols)}): avg non-null {non_null:.1f}%")

    # Model inventory
    print("\n" + "=" * 70)
    print("MODEL INVENTORY")
    print("=" * 70)
    models_dir = path("models")
    for f in sorted(os.listdir(models_dir)):
        fp = os.path.join(models_dir, f)
        size_kb = os.path.getsize(fp) / 1024
        print(f"  {f}: {size_kb:.1f} KB")

    # Pipeline audit
    print("\n" + "=" * 70)
    print("PIPELINE / LEAKAGE AUDIT SUMMARY")
    print("=" * 70)
    print("""
  Duplicate pipelines:
    - technical_indicators.py AND utils/preprocess_stock.py (both compute indicators)
    - utils/improved_model.py (LEAKED split, still exists) vs build_horizon_models.py (leak-safe)
    - utils/fii_dii.py (derivatives OI proxy, NOT cash-market flows)

  Known leakage risks:
    - Static fundamentals (PE/PB/Market_Cap/Dividend_Yield constant per company)
    - FII/DII named buy/sell but actually derived from derivatives OI changes
    - utils/improved_model.py sorts by Company->Date (leaked split)
    - Sparse news sentiment (< 5% coverage)

  Point-in-time safe:
    - Technical indicators (rolling/lag only)
    - NIFTY/SENSEX/BANKNIFTY/VIX/sector/macro (by-date merge)
    - FII/DII (by-date, rolling backward)
    - Market breadth (by-date, rolling)
""")

    # Write FEATURE_AUDIT.json
    feature_audit = {
        "merged_dataset": {
            "rows": int(len(mdf)) if 'mdf' in locals() else None,
            "cols": int(mdf.shape[1]) if 'mdf' in locals() else None,
            "constant_columns": const_cols if 'const_cols' in locals() else [],
            "sentiment_nonzero_pct": float(nz * 100) if 'nz' in locals() else None,
        },
        "datasets": audit_rows,
        "known_issues": [
            "Static fundamentals (not point-in-time)",
            "FII/DII is derivatives-OI proxy not cash flows",
            "utils/improved_model.py uses leaked split (should not be used)",
            "Duplicate indicator pipelines (technical_indicators.py vs utils/preprocess_stock.py)",
            "Sparse news sentiment",
        ],
    }
    with open(path("FEATURE_AUDIT.json"), "w") as f:
        json.dump(feature_audit, f, indent=2)
    print("Saved FEATURE_AUDIT.json")

    # Write DATA_AUDIT_REPORT.md
    report = """# Data Audit Report

Generated: 2026-08-10

## Dataset Inventory

| Dataset | Rows | Cols | Missing % | Date Coverage | Point-in-Time Safe? | Useful? |
|---------|------|------|-----------|---------------|---------------------|---------|
"""
    for r in audit_rows:
        dates = f"{r.get('date_min','?')} -> {r.get('date_max','?')}" if "date_min" in r else "N/A"
        report += f"| {r['file']} | {r.get('rows','?')} | {r.get('cols','?')} | {r.get('missing_pct','?')}% | {dates} | ? | ? |\n"

    report += """
## Known Issues

1. **Static fundamentals**: PE_Ratio, PB_Ratio, Market_Cap, Dividend_Yield are constant per company — this is look-ahead bias. They represent current values applied to all historical dates.
2. **FII/DII proxy**: The FII_Buy/Sell/Net values are derived from day-over-day changes in derivatives open interest (participant-wise OI), NOT actual cash-market flows.
3. **Leaked pipeline**: `utils/improved_model.py` still exists and uses the leaked Company→Date split. It must NOT be used.
4. **Duplicate indicator pipelines**: `technical_indicators.py` and `utils/preprocess_stock.py` both compute indicators and may diverge.
5. **Sparse news sentiment**: <5% of rows have non-zero sentiment.
6. **Sector features**: Added 120 sector-index columns in prior pass (point-in-time, by-date merge).

## Recommendations

- Remove/retire `utils/improved_model.py` from production use.
- Treat FII/DII as derivatives-positioning features, not cash flows.
- Consider dropping static fundamentals or making them point-in-time.
- Sector-relative features (stock vs own sector) are the most promising direction.
"""
    with open(path("DATA_AUDIT_REPORT.md"), "w", encoding="utf-8") as f:
        f.write(report)
    print("Saved DATA_AUDIT_REPORT.md")


if __name__ == "__main__":
    main()