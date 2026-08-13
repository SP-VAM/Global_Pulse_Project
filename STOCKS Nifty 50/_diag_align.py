import pandas as pd, numpy as np
agg = pd.read_csv('merged_data/news_sentiment_aggregated.csv', parse_dates=['Date'])
mer = pd.read_csv('merged_data/merged_dataset.csv', parse_dates=['Date'])

# normalize tickers the same way merge_data does
def norm(s):
    return s.astype(str).str.upper().str.replace('.NS','',regex=False).str.strip()
agg['Ticker'] = norm(agg['Ticker'])
mer['Ticker'] = norm(mer['Ticker'])

agg = agg.dropna(subset=['Date'])
mer = mer.dropna(subset=['Date'])
# strip time
agg['D'] = agg['Date'].dt.normalize()
mer['D'] = mer['Date'].dt.normalize()

# restrict agg to merged date range
ar = agg[(agg['D']>=mer['D'].min()) & (agg['D']<=mer['D'].max())]
print('agg rows in merged date range:', len(ar))
mk = mer[['Ticker','D']].drop_duplicates()
ak = ar[['Ticker','D']].drop_duplicates()
overlap_keys = len(pd.merge(ak, mk, on=['Ticker','D'], how='inner'))
print('agg (Ticker,Date) keys overlapping merged:', overlap_keys, 'of', len(ak))
print('ticker overlap:', len(set(ak.Ticker)&set(mk.Ticker)), 'agg tickers:', ak.Ticker.nunique(), 'merged tickers:', mk.Ticker.nunique())
# date overlap
print('distinct agg dates in range:', ar['D'].nunique(), 'merged dates:', mer['D'].nunique(), 'date overlap:', len(set(ar['D'])&set(mer['D'])))

# why miss: news on non-trading days?
trading = set(mer['D'].dt.date)
news_on_trading = ar['D'].dt.date.isin(trading)
print('news articles whose publish date IS a trading day:', news_on_trading.sum(), '/', len(ar))
# ticker in agg but not merged
print('agg tickers not in merged:', sorted(set(ak.Ticker)-set(mk.Ticker))[:20])

# Sentiment_Mean nonzero after proper alignment
merged_check = pd.merge(ar, mer[['Ticker','D','Sentiment_Mean']], on=['Ticker','D'], how='inner', suffixes=('_agg','_mer'))
print('matched rows:', len(merged_check))
print('agg nonzero Sentiment_Mean in matched:', (merged_check['Sentiment_Mean_agg'].fillna(0)!=0).mean())
print('mer nonzero Sentiment_Mean in matched:', (merged_check['Sentiment_Mean_mer'].fillna(0)!=0).mean())
print('rows where agg has nonzero but mer is 0 (alignment bug):', ((merged_check['Sentiment_Mean_agg'].fillna(0)!=0) & (merged_check['Sentiment_Mean_mer'].fillna(0)==0)).sum())
