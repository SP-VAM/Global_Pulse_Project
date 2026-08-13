import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, matthews_corrcoef, f1_score

from utils.helper import ENHANCED_TECHNICAL_FEATURES, FUNDAMENTAL_FEATURES


def main():
    df = pd.read_csv('merged_data/merged_dataset.csv', parse_dates=['Date'])
    df = df.dropna(subset=['Target_Multi']).copy()
    df = df.sort_values(['Company', 'Date']).reset_index(drop=True)

    feature_cols = []
    for col in ENHANCED_TECHNICAL_FEATURES:
        if col in df.columns:
            feature_cols.append(col)
    for col in [
        'Sentiment_Mean', 'Sentiment_Count', 'Sentiment_Positive',
        'Sentiment_Neutral', 'Sentiment_Negative'
    ]:
        if col in df.columns:
            feature_cols.append(col)
    for col in FUNDAMENTAL_FEATURES:
        if col in df.columns:
            feature_cols.append(col)

    feature_cols += [
        'NIFTY_Daily_Return', 'NIFTY_3D_Return', 'NIFTY_5D_Return', 'NIFTY_10D_Return', 'NIFTY_20D_Return',
        'NIFTY_EMA20', 'NIFTY_EMA50', 'NIFTY_EMA200', 'NIFTY_RSI', 'NIFTY_MACD', 'NIFTY_MACD_SIGNAL',
        'NIFTY_MACD_HIST', 'NIFTY_ADX', 'NIFTY_Trend_Direction', 'NIFTY_Rolling_Volatility',
        'NIFTY_Market_Strength', 'Stock_vs_Nifty_Return',
        'Valuation_Category_Overvalued', 'Valuation_Category_Undervalued', 'Valuation_Category_Correct'
    ]
    feature_cols = [c for c in dict.fromkeys(feature_cols) if c in df.columns]
    feature_cols = [c for c in feature_cols if c not in {'Company', 'Ticker', 'Year', 'Quarter', 'Month', 'Target', 'Target_Return', 'Company_Encoded'}]

    split_idx = int(len(df) * (1 - 0.15))
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()

    X_train = train_df[feature_cols].fillna(0).replace([np.inf, -np.inf], 0)
    X_test = test_df[feature_cols].fillna(0).replace([np.inf, -np.inf], 0)
    y_train = train_df['Target_Multi'].astype(int)
    y_test = test_df['Target_Multi'].astype(int)

    model = RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=-1, class_weight='balanced')
    model.fit(X_train, y_train)
    pred = model.predict(X_test)

    print('accuracy', accuracy_score(y_test, pred))
    print('mcc', matthews_corrcoef(y_test, pred))
    print('f1_weighted', f1_score(y_test, pred, average='weighted'))
    print(pd.crosstab(y_test, pred, rownames=['True'], colnames=['Pred']))


if __name__ == '__main__':
    main()
