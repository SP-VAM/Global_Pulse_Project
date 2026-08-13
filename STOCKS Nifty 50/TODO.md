# Market-Wide Data Integration — Implementation Plan

## Goal
Extend the existing stock prediction pipeline with market-wide data (VIX, indices, sector indices, market breadth) and new feature engineering, then validate on the untouched chronological test set.

## Steps
- [x] 1. Create `utils/market_data.py`:
  - Indicator helpers (returns, EMA, RSI, MACD, ADX, volatility)
  - Download VIX `^INDIAVIX`, Nifty `^NSEI`, Sensex `^BSESN`, BankNifty `^NSEBANK`, sector indices (`^CNX*`)
  - Compute index indicators (returns, EMA20/50/200, RSI, MACD, ADX, trend direction, rolling volatility)
  - Compute market breadth from local NIFTY-50 stock CSVs (advance/decline, % above EMA20/50, 52wk highs/lows)
  - Compute Market Regime (5 levels) + Market Strength Score + Breadth Score + Market Alignment Score + Trend Consensus Score
- [x] 2. Add sector mapping for all 50 stocks
- [x] 3. Add market-relative features (stock vs Nifty/sector, RSI/momentum diff, relative volume, relative strength) in merge step
- [x] 4. Update `utils/helper.py` with new feature lists
- [x] 5. Create `download_market_data.py` to fetch and generate market features
- [ ] 6. Create `feature_selection.py` (permutation importance, keep only features improving validation)
- [ ] 7. Train current model, compare old vs new on untouched test set (Accuracy, MCC, ROC-AUC)
- [ ] 8. Accept new model only if it improves; otherwise revert
- [ ] 9. Document all files changed
