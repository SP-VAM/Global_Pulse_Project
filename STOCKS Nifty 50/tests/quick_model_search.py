import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, matthews_corrcoef, f1_score
from sklearn.preprocessing import LabelEncoder

from utils.helper import ENHANCED_TECHNICAL_FEATURES, FUNDAMENTAL_FEATURES


def evaluate_models():
    df = pd.read_csv('merged_data/merged_dataset.csv', parse_dates=['Date'])
    df = df.dropna(subset=['Target_Multi']).copy()
    df = df.sort_values(['Company', 'Date']).reset_index(drop=True)

    feature_cols = []
    for col in ENHANCED_TECHNICAL_FEATURES:
        if col in df.columns:
            feature_cols.append(col)
    for col in ['Sentiment_Mean', 'Sentiment_Count', 'Sentiment_Positive', 'Sentiment_Neutral', 'Sentiment_Negative']:
        if col in df.columns:
            feature_cols.append(col)
    for col in FUNDAMENTAL_FEATURES:
        if col in df.columns:
            feature_cols.append(col)
    feature_cols += [
        'NIFTY_Daily_Return', 'NIFTY_3D_Return', 'NIFTY_5D_Return', 'NIFTY_10D_Return', 'NIFTY_20D_Return',
        'NIFTY_EMA20', 'NIFTY_EMA50', 'NIFTY_EMA200', 'NIFTY_RSI', 'NIFTY_MACD', 'NIFTY_MACD_SIGNAL',
        'NIFTY_MACD_HIST', 'NIFTY_ADX', 'NIFTY_Trend_Direction', 'NIFTY_Rolling_Volatility',
        'NIFTY_Market_Strength', 'Stock_vs_Nifty_Return', 'Valuation_Category_Overvalued',
        'Valuation_Category_Undervalued', 'Valuation_Category_Correct'
    ]
    feature_cols = [c for c in dict.fromkeys(feature_cols) if c in df.columns]
    feature_cols = [c for c in feature_cols if c not in {'Company', 'Ticker', 'Year', 'Quarter', 'Month', 'Target', 'Target_Return'}]

    split_idx = int(len(df) * (1 - 0.15))
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()

    le = LabelEncoder()
    train_df['Company_Encoded'] = le.fit_transform(train_df['Company'].astype(str))
    test_df['Company_Encoded'] = test_df['Company'].astype(str).map(lambda x: le.transform([x])[0] if x in le.classes_ else -1)
    feature_cols.append('Company_Encoded')

    X_train = train_df[feature_cols].fillna(0).replace([np.inf, -np.inf], 0)
    X_test = test_df[feature_cols].fillna(0).replace([np.inf, -np.inf], 0)
    y_train = train_df['Target_Multi'].astype(int)
    y_test = test_df['Target_Multi'].astype(int)

    candidates = [
        ('rf', RandomForestClassifier(n_estimators=400, random_state=42, n_jobs=-1, class_weight='balanced')),
        ('et', ExtraTreesClassifier(n_estimators=400, random_state=42, n_jobs=-1, class_weight='balanced')),
        ('hgb', HistGradientBoostingClassifier(random_state=42, max_depth=4, learning_rate=0.05, max_iter=200)),
    ]

    results = []
    for name, model in candidates:
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        results.append((name, accuracy_score(y_test, pred), matthews_corrcoef(y_test, pred), f1_score(y_test, pred, average='weighted')))

    return results


if __name__ == '__main__':
    for item in evaluate_models():
        print(item)
