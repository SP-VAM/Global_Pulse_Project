# Stock Market Prediction Dashboard

An end-to-end machine learning project for stock market prediction using XGBoost, technical indicators, and news sentiment analysis. Includes a comprehensive Streamlit dashboard for visualization and analysis.

## Features

- **Data Collection**: Downloads historical stock data for 50 Nifty companies using Yahoo Finance
- **Technical Indicators**: Computes 20+ technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands, ATR, OBV, Stochastic, ADX)
- **News Sentiment**: Aggregates news sentiment from headlines for each company
- **ML Model**: XGBoost classifier trained on technical indicators + sentiment features
- **Interactive Dashboard**: Streamlit-based dashboard with:
  - Price charts (candlestick, line)
  - Technical analysis (RSI, MACD, Bollinger Bands)
  - ML predictions with probability scores
  - Feature importance analysis
  - News sentiment visualization

## Project Structure

```
Stocks/
├── download_stock_data.py      # Download stock data from Yahoo Finance
├── technical_indicators.py     # Compute technical indicators
├── train_xgboost.py            # Train XGBoost model
├── predict.py                  # CLI prediction script
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── TODO.md                     # Project progress tracker
│
├── stock_data/                 # Raw stock CSV files (50 companies)
│   ├── RELIANCE.csv
│   ├── HDFCBANK.csv
│   └── ...
│
├── technical_indicators/       # CSV files with computed indicators
│
├── news_data/
│   └── final_news_sentiment_analysis.csv  # Raw news sentiment
│
├── merged_data/                # Merged datasets (stock + indicators + sentiment)
│
├── models/                     # Trained models
│   ├── xgboost_model.pkl
│   ├── label_encoder.pkl
│   └── model_features.pkl
│
├── utils/                      # Utility modules
│   ├── helper.py               # Constants, mappings, date utils
│   ├── preprocess_stock.py     # Stock data cleaning & indicators
│   ├── preprocess_news.py      # News sentiment aggregation
│   ├── merge_data.py           # Dataset merging
│   └── prediction.py           # Model loading & prediction
│
└── dashboard/                  # Streamlit dashboard
    ├── app.py                  # Main dashboard app
    ├── charts.py               # Plotly chart components
    └── utils.py                # Dashboard data loading
```

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Stocks
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Download Stock Data (Optional - Data already included)

```bash
python download_stock_data.py
```

This downloads data for 50 Nifty companies from 2022-01-01 to 2026-06-30.

### 4. Compute Technical Indicators

```bash
python technical_indicators.py
```

This computes 20+ technical indicators for all companies and saves them to `technical_indicators/`.

### 5. Preprocess News Sentiment

```bash
python utils/preprocess_news.py
```

This aggregates news sentiment by company and date.

### 6. Merge Datasets

```bash
python utils/merge_data.py
```

This merges stock data, technical indicators, and news sentiment into a single dataset.

### 7. Train the Model

```bash
python train_xgboost.py
```

This trains an XGBoost classifier and saves the model to `models/`.

### 8. Run the Dashboard

```bash
streamlit run dashboard/app.py
```

### 9. CLI Predictions

```bash
# Predict for a specific company
python predict.py RELIANCE

# Predict for all companies
python predict.py --all

# Show feature importance
python predict.py --feature-importance

# List available companies
python predict.py --list-companies
```

## Model Details

- **Algorithm**: XGBoost Classifier
- **Features**: 20+ technical indicators + news sentiment + time-based features
- **Target**: Binary classification (UP/DOWN) for next day's price movement
- **Training**: 80-20 train-test split with stratified sampling
- **Evaluation**: Accuracy, Precision, Recall, F1 Score, ROC AUC

### Technical Indicators Used

| Indicator | Description |
|-----------|-------------|
| SMA20/SMA50 | Simple Moving Averages |
| EMA20/EMA50 | Exponential Moving Averages |
| RSI | Relative Strength Index (14) |
| MACD | Moving Average Convergence Divergence |
| BB Upper/Middle/Lower | Bollinger Bands (20, 2) |
| ATR | Average True Range (14) |
| OBV | On-Balance Volume |
| STOCH K/D | Stochastic Oscillator (14, 3, 3) |
| ADX | Average Directional Index (14) |
| Daily Return | Daily percentage change |
| Volatility | 20-day rolling volatility |
| Price Change | Daily price change |

## Companies Covered

50 Nifty 50 companies including: Reliance, HDFC Bank, ICICI Bank, Infosys, TCS, ITC, SBI, Hindustan Unilever, Bajaj Finance, and more.

## License

This project is for educational purposes only. Not financial advice.
