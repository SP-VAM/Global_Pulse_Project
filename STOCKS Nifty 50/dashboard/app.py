"""
Stock Market Prediction Dashboard
A Streamlit dashboard for stock analysis, technical indicators, and ML predictions.
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

st = None

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def init_streamlit():
    global st
    import streamlit as st_mod
    st = st_mod
    st.set_page_config(
        page_title="Stock Market Prediction Dashboard",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def is_streamlit_running():
    if os.environ.get("STREAMLIT_SERVER_RUN") is not None or os.environ.get("STREAMLIT_RUN") is not None:
        return True
    try:
        import streamlit as st_mod
        runtime = getattr(st_mod, "runtime", None)
        return runtime is not None and getattr(runtime, "exists", lambda: False)()
    except Exception:
        return False

from dashboard.utils import (
    load_merged_data, get_models, get_company_list,
    get_company_data, get_latest_data_for_prediction,
    get_ticker_symbol, load_live_data, load_live_dataframe,
    load_news_sentiment, load_live_news_sentiment,
    get_horizon_models
)
from dashboard.charts import (
    create_candlestick_chart, create_line_chart,
    create_rsi_chart, create_macd_chart, create_bollinger_bands_chart,
    create_feature_importance_chart, create_prediction_vs_actual,
    create_sentiment_chart
)
from utils.prediction import (
    make_prediction, get_feature_importance
)
from utils.helper import TICKER_TO_COMPANY

# ==========================================================
# SIDEBAR
# ==========================================================

def render_sidebar():
    """Render the sidebar with company selection and filters."""
    st.sidebar.title("📈 Stock Predictor")
    st.sidebar.markdown("---")
    
    # Company selection
    companies = get_company_list()
    selected_ticker = st.sidebar.selectbox(
        "Select Company",
        companies,
        index=companies.index("RELIANCE") if "RELIANCE" in companies else 0,
        format_func=lambda x: f"{x} - {TICKER_TO_COMPANY.get(x, x)}"
    )
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Settings")
    
    # Prediction Horizon dropdown
    horizon_map = {
        "Next Day (1D)": "1d",
        "5 Days (5D)": "5d",
        "10 Days (10D)": "10d",
    }
    horizon_label = st.sidebar.selectbox(
        "Prediction Horizon",
        list(horizon_map.keys()),
        index=0,
        help="5D means the expected direction over the next 5 trading days. 10D means the next 10 trading days."
    )
    horizon = horizon_map[horizon_label]
    
    # Date range filter (for chart display only)
    date_range = st.sidebar.selectbox(
        "Chart Date Range",
        ["1 Month", "3 Months", "6 Months", "1 Year", "2 Years", "All"],
        index=3
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
        **About**  
        This dashboard uses separate trained models for each prediction horizon  
        (1D, 5D, 10D) based on technical indicators, fundamentals, and news sentiment.
        """
    )
    
    return selected_ticker, date_range, horizon, horizon_label


def get_date_filter(date_range_str):
    """Convert date range string to start date."""
    today = datetime.now()
    ranges = {
        "1 Month": today - timedelta(days=30),
        "3 Months": today - timedelta(days=90),
        "6 Months": today - timedelta(days=180),
        "1 Year": today - timedelta(days=365),
        "2 Years": today - timedelta(days=730),
        "All": datetime(2022, 1, 1),
    }
    return ranges.get(date_range_str, today - timedelta(days=365))


def render_glossary():
    """Show a short, simple explanation for technical and sentiment terms."""
    st.markdown(
        """
        ### What this means for learners
        - **RSI:** Shows if the stock is moving up or down too quickly.
        - **MACD:** Helps spot when the trend is turning stronger or weaker.
        - **Bollinger Bands:** Shows whether price is high or low compared to its normal range.
        - **ATR:** Shows how much the price usually moves each day.
        - **ADX:** Shows how strong the trend is, even if it is up or down.
        - **News Sentiment:** Shows whether recent news is mostly positive or negative.
        """
    )


def get_prediction_label(pred_value, prob_up, prob_down):
    """
    Map the binary model output to an interpretable dashboard label using the
    actual class probability from the model. Only UP (BUY) and DOWN (SELL)
    are predicted; there is no neutral/FLAT class.
    """
    best_prob = max(prob_up, prob_down)
    if best_prob == prob_up:
        return "BUY", best_prob, "📈"
    else:
        return "SELL", best_prob, "📉"


# ==========================================================
# MAIN DASHBOARD
# ==========================================================

def main():
    if st is None:
        init_streamlit()

    st.title("📊 Stock Market Prediction Dashboard")
    
    # Sidebar
    selected_ticker, date_range, horizon, horizon_label = render_sidebar()
    start_date = get_date_filter(date_range)
    
    # Load trained model and historical data
    with st.spinner(f"Loading {horizon_label} model and historical data..."):
        merged_data = load_merged_data()
        # Try horizon-specific model first; fall back to default model
        model, label_encoder, feature_cols, horizon_metrics = get_horizon_models(horizon, "binary")
        if model is None:
            model, label_encoder, feature_cols = get_models()
            horizon_metrics = None
    
    if merged_data.empty:
        st.error("No historical data loaded. Please run the data preprocessing pipeline first.")
        st.info("Run `python utils/preprocess_stock.py` and `python utils/merge_data.py`")
        return
    
    # ==========================================================
    # LIVE MARKET DATA (Fresh on every refresh)
    # ==========================================================
    ticker_symbol = get_ticker_symbol(selected_ticker)
    live_data = load_live_data(ticker_symbol)
    
    # ==========================================================
    # Get historical company data for charts
    # ==========================================================
    company_df = get_company_data(merged_data, selected_ticker)
    
    if company_df.empty:
        st.warning(f"No historical data found for {selected_ticker}")
        return
    
    # Filter by date for chart display
    company_df = company_df[company_df["Date"] >= pd.Timestamp(start_date)]
    
    # ==========================================================
    # LIVE NEWS SENTIMENT (fetched once, reused by prediction + news tab)
    # ==========================================================
    with st.spinner("Fetching live Indian news & sentiment..."):
        live_news_df = load_live_news_sentiment(selected_ticker)
    
    # ==========================================================
    # LIVE PRICE METRICS SECTION - ALWAYS DISPLAY TOP
    # ==========================================================
    
    st.header(f"{selected_ticker} - {TICKER_TO_COMPANY.get(selected_ticker, '')}")
    
    # Live price metrics from fresh API data
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    if "error" not in live_data and live_data.get("current_price") is not None:
        with col1:
            st.metric(
                "Current Price",
                f"₹{live_data['current_price']:.2f}",
                delta=f"{live_data.get('change_pct', 0):+.2f}%" if live_data.get('change_pct') else None
            )
        
        with col2:
            st.metric("Open", f"₹{live_data['open']:.2f}" if live_data.get('open') else "N/A")
        
        with col3:
            st.metric("High", f"₹{live_data['high']:.2f}" if live_data.get('high') else "N/A")
        
        with col4:
            st.metric("Low", f"₹{live_data['low']:.2f}" if live_data.get('low') else "N/A")
        
        with col5:
            prev_close = live_data.get('previous_close')
            st.metric("Prev Close", f"₹{prev_close:.2f}" if prev_close else "N/A")
        
        with col6:
            vol = live_data.get('volume')
            st.metric("Volume", f"{vol:,}" if vol else "N/A")
        
        st.caption(f"🕐 Last Updated: {live_data.get('last_updated', 'N/A')} | Source: {live_data.get('source', 'Yahoo Finance')}")
    else:
        # Fallback to historical data if live unavailable
        latest = company_df.iloc[-1] if not company_df.empty else None
        if latest is not None:
            with col1:
                st.metric("Last Close (Hist)", f"₹{latest.get('Close', 0):.2f}")
            with col2:
                st.metric("RSI (14)", f"{latest.get('RSI', 0):.1f}")
            st.info("Live data unavailable - showing last historical close")
        else:
            st.warning("No live or historical price data available")
    
    st.markdown("---")
    
    # ==========================================================
    # TABS
    # ==========================================================
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Overview & Charts",
        "📉 Technical Analysis",
        "🤖 Predictions",
        "📰 News Sentiment"
    ])
    
    # ==========================================================
    # TAB 1: OVERVIEW & CHARTS
    # ==========================================================
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            if "Close" in company_df.columns:
                fig = create_line_chart(company_df, selected_ticker, height=400)
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            if all(col in company_df.columns for col in ["Open", "High", "Low", "Close"]):
                fig = create_candlestick_chart(company_df, selected_ticker, height=400)
                st.plotly_chart(fig, use_container_width=True)
        
        # Company info
        with st.expander("Company Information & Historical Data"):
            company_name = TICKER_TO_COMPANY.get(selected_ticker, "Unknown")
            st.write(f"**Company:** {company_name}")
            st.write(f"**Ticker:** {selected_ticker}.NS")
            st.write(f"**Historical Data Range:** {company_df['Date'].min().date()} to {company_df['Date'].max().date()}")
            st.write(f"**Total Days:** {len(company_df)}")
            
            cols_to_show = ["Date", "Open", "High", "Low", "Close", "Volume"]
            cols_to_show = [c for c in cols_to_show if c in company_df.columns]
            st.dataframe(company_df.tail(10)[cols_to_show], use_container_width=True)
    
    # ==========================================================
    # TAB 2: TECHNICAL ANALYSIS
    # ==========================================================
    
    with tab2:
        st.header("Technical Analysis")
        render_glossary()
        
        fig_rsi = create_rsi_chart(company_df)
        if fig_rsi:
            st.plotly_chart(fig_rsi, use_container_width=True)
        
        fig_macd = create_macd_chart(company_df)
        if fig_macd:
            st.plotly_chart(fig_macd, use_container_width=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_bb = create_bollinger_bands_chart(company_df)
            if fig_bb:
                st.plotly_chart(fig_bb, use_container_width=True)
        
        with col2:
            st.subheader("Technical Indicators Summary")
            tech_cols = [
                "Date", "SMA20", "SMA50", "RSI", "MACD", "MACD_SIGNAL",
                "BB_UPPER", "BB_MIDDLE", "BB_LOWER", "ATR", "ADX"
            ]
            tech_cols = [c for c in tech_cols if c in company_df.columns]
            if tech_cols:
                st.dataframe(company_df.tail(10)[tech_cols], use_container_width=True)
    
    # ==========================================================
    # TAB 3: PREDICTIONS
    # ==========================================================
    
    with tab3:
        st.header(f"ML Prediction — {horizon_label}")
        
        # Show horizon explanation
        horizon_explanation = {
            "Next Day (1D)": "This predicts the expected direction of the stock over the **next 1 trading day**.",
            "5 Days (5D)": "This predicts the expected direction of the stock over the **next 5 trading days**.",
            "10 Days (10D)": "This predicts the expected direction of the stock over the **next 10 trading days**.",
        }
        st.caption(horizon_explanation.get(horizon_label, ""))
        
        if model is None or feature_cols is None:
            st.warning(f"No trained model found for {horizon_label}. Please run `python build_horizon_models.py` first.")
        else:
            with st.spinner(f"Generating {horizon_label} prediction..."):
                pred_df = company_df.copy()
                
                # Inject today's live news sentiment into the latest feature row.
                # The trained model expects the aggregated Sentiment_* columns, but
                # the historical snapshot is stale/zero for recent dates. Overlaying
                # real-time sentiment is leak-safe for inference (current information
                # at prediction time) and lets live news actually influence the call.
                if not pred_df.empty and not live_news_df.empty:
                    _latest_idx = pred_df.index[-1]
                    _sent = live_news_df["sentiment_value"]
                    _live_sentiment = {
                        "Sentiment_Mean": float(_sent.mean()),
                        "Sentiment_Count": int(len(live_news_df)),
                        "Sentiment_Positive": int((_sent > 0).sum()),
                        "Sentiment_Neutral": int((_sent == 0).sum()),
                        "Sentiment_Negative": int((_sent < 0).sum()),
                    }
                    for _col, _val in _live_sentiment.items():
                        if _col in pred_df.columns:
                            pred_df.loc[_latest_idx, _col] = _val
                
                # Encode company name
                company_name = TICKER_TO_COMPANY.get(selected_ticker, selected_ticker)
                try:
                    company_encoded = label_encoder.transform([company_name])[0]
                except:
                    company_encoded = 0
                
                # Build prediction features
                X_pred = pd.DataFrame()
                for col in feature_cols:
                    if col == "Company_Encoded":
                        X_pred[col] = [company_encoded] * len(pred_df)
                    elif col in pred_df.columns:
                        X_pred[col] = pred_df[col].values
                    else:
                        X_pred[col] = [0] * len(pred_df)
                
                X_pred = X_pred.fillna(0).replace([np.inf, -np.inf], 0)
                
                predictions = make_prediction(model, X_pred, feature_cols, return_proba=True)
                
                if predictions is not None:
                    pred_df["Prediction"] = predictions["Prediction"].values
                    pred_df["Direction"] = predictions["Direction"].values
                    if "Prob_UP" in predictions.columns:
                        pred_df["Prob_UP"] = predictions["Prob_UP"].values
                    if "Prob_DOWN" in predictions.columns:
                        pred_df["Prob_DOWN"] = predictions["Prob_DOWN"].values
                
                # ==========================================================
                # PREDICTION RESULT - ALWAYS SHOW (REQUIREMENT #1)
                # ==========================================================
                latest_pred = pred_df.iloc[-1] if not pred_df.empty else None
                latest_prob_row = None
                if predictions is not None:
                    latest_prob_row = predictions.iloc[-1].copy() if hasattr(predictions, 'iloc') else None

                st.subheader(f"📊 Market Prediction ({horizon_label})")

                if latest_pred is not None and "Prediction" in pred_df.columns:
                    pred = int(latest_pred.get("Prediction", -1))
                    prob_up = 0.0
                    prob_down = 0.0

                    if latest_prob_row is not None:
                        prob_up = float(latest_prob_row.get("Prob_UP", 0.0) or 0.0)
                        prob_down = float(latest_prob_row.get("Prob_DOWN", 0.0) or 0.0)

                    if not any([prob_up, prob_down]):
                        prob_up = float(latest_pred.get("Prob_UP", 0.0) or 0.0)
                        prob_down = float(latest_pred.get("Prob_DOWN", 0.0) or 0.0)

                    if not any([prob_up, prob_down]):
                        prob_up = 0.0
                        prob_down = 0.0

                    prob_values = {
                        "up": prob_up,
                        "down": prob_down,
                    }
                    label, confidence, emoji = get_prediction_label(pred, prob_up, prob_down)
                    
                    # Display prediction prominently
                    pred_col1, pred_col2 = st.columns([1, 1])
                    
                    with pred_col1:
                        if label == "BUY":
                            st.success(f"{emoji} **PREDICTION: {label}**")
                        elif label == "SELL":
                            st.error(f"{emoji} **PREDICTION: {label}**")

                        st.metric("Confidence", f"{confidence:.1%}")
                        st.write(f"Model probability: UP {prob_values['up']:.1%} | DOWN {prob_values['down']:.1%}")
                    
                    with pred_col2:
                        live_price = live_data.get("current_price", latest_pred.get("Close", 0))
                        st.metric("Current Price", f"₹{live_price:.2f}")
                        st.metric("Probability UP", f"{prob_values['up']:.1%}")
                        st.metric("Probability DOWN", f"{prob_values['down']:.1%}")
                        st.caption(f"Raw values: UP={prob_values['up']:.3f}, DOWN={prob_values['down']:.3f}")
                    
                    # Disclaimer - always shown (requirement #1)
                    st.warning(
                        "⚠️ **Disclaimer:** This prediction is AI-generated based on historical "
                        "market patterns, technical indicators, company fundamentals, and live news "
                        "sentiment. Stock markets are inherently uncertain, and this prediction should "
                        "not be treated as financial advice."
                    )
                else:
                    # If prediction fails, show a neutral fallback
                    st.info("📊 **PREDICTION: —**")
                    st.metric("Confidence", "—")
                    st.warning(
                        "⚠️ **Disclaimer:** This prediction is AI-generated based on historical "
                        "market patterns, technical indicators, company fundamentals, and live news "
                        "sentiment. Stock markets are inherently uncertain, and this prediction should "
                        "not be treated as financial advice."
                    )
                
                # Chart: Prediction vs Actual
                st.subheader("Prediction vs Actual (Historical)")
                fig_pred = create_prediction_vs_actual(pred_df)
                if fig_pred:
                    st.plotly_chart(fig_pred, use_container_width=True)
                
                # Prediction details table
                with st.expander("Recent Prediction Details"):
                    detail_cols = ["Date", "Close", "Direction", "Prob_UP", "Prob_DOWN"]
                    detail_cols = [c for c in detail_cols if c in pred_df.columns]
                    st.dataframe(pred_df.tail(15)[detail_cols], use_container_width=True)
                
                # Feature Importance
                st.subheader("Feature Importance")
                importance = get_feature_importance(model, feature_cols, top_n=20)
                if not importance.empty:
                    fig_imp = create_feature_importance_chart(importance)
                    if fig_imp:
                        st.plotly_chart(fig_imp, use_container_width=True)
    
    # ==========================================================
    # TAB 4: NEWS SENTIMENT (Historical + Live)
    # ==========================================================
    
    with tab4:
        st.header("News Sentiment Analysis")
        st.markdown(
            """
            **News sentiment** tells you whether news about the company is mostly good or mostly bad.
            - Positive news usually helps stock price.
            - Negative news can make the stock move down.
            """
        )
        
        # ==========================================================
        # LIVE NEWS SECTION
        # ==========================================================
        st.subheader("💬 Live News Sentiment")
        st.caption("Real-time Indian RSS feeds (Google News + Moneycontrol/ET/CNBC) - filtered for market-relevant news only")
        
        # live_news_df was fetched once in main() and is reused here (sentiment
        # is computed once, not twice).
        if not live_news_df.empty:
            # Display live sentiment metrics
            avg_sent = live_news_df["sentiment_value"].mean()
            total_live = len(live_news_df)
            pos_count = (live_news_df["sentiment_value"] > 0).sum()
            neg_count = (live_news_df["sentiment_value"] < 0).sum()
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Live Avg Sentiment", f"{avg_sent:.3f}")
            with col2:
                st.metric("Articles Found", total_live)
            with col3:
                st.metric("Positive Articles", pos_count)
            with col4:
                st.metric("Negative Articles", neg_count)
            
            # Show live news headlines
            st.subheader("Latest Market-Relevant News")
            for _, row in live_news_df.iterrows():
                sentiment_icon = "🟢" if row["sentiment_value"] > 0 else ("🔴" if row["sentiment_value"] < 0 else "⚪")
                st.markdown(
                    f"{sentiment_icon} **{row.get('title', 'N/A')}**  \n"
                    f"*{row.get('source', '')} | {row.get('published_at', '')}*  \n"
                    f"Sentiment: {row.get('sentiment', 'neutral').upper()} (Confidence: {row.get('sentiment_confidence', 0):.0%})"
                )
                st.markdown("---")
        else:
            st.info("No live news articles fetched for this company. The RSS feeds may be temporarily unavailable, or the company may not be in recent news.")
        
        st.markdown("---")
        
        # ==========================================================
        # HISTORICAL NEWS SENTIMENT SECTION
        # ==========================================================
        st.subheader("📊 Historical News Sentiment")
        
        news_data = load_news_sentiment()
        
        if not news_data.empty:
            company_name = TICKER_TO_COMPANY.get(selected_ticker, "")
            company_news = news_data[
                news_data["Company"].str.contains(company_name, case=False, na=False) |
                news_data["Ticker"].str.contains(selected_ticker, case=False, na=False)
            ]
            
            if not company_news.empty:
                company_news = company_news.sort_values("Date", ascending=False)
                
                fig_sent = create_sentiment_chart(company_news)
                if fig_sent:
                    st.plotly_chart(fig_sent, use_container_width=True)
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    avg_sentiment = company_news["Sentiment_Mean"].mean()
                    st.metric("Avg Sentiment", f"{avg_sentiment:.3f}")
                
                with col2:
                    total_articles = company_news["Sentiment_Count"].sum()
                    st.metric("Total Articles", int(total_articles))
                
                with col3:
                    positive = company_news["Sentiment_Positive"].sum()
                    st.metric("Positive Articles", int(positive))
                
                with col4:
                    negative = company_news["Sentiment_Negative"].sum()
                    st.metric("Negative Articles", int(negative))
                
                with st.expander("Historical Sentiment Data"):
                    news_cols = ["Date", "Sentiment_Mean", "Sentiment_Count",
                               "Sentiment_Positive", "Sentiment_Neutral", "Sentiment_Negative"]
                    news_cols = [c for c in news_cols if c in company_news.columns]
                    st.dataframe(company_news[news_cols].head(20), use_container_width=True)
            else:
                st.info(f"No historical news sentiment data available for {selected_ticker}")
        else:
            st.info("No historical news sentiment data loaded.")


if __name__ == "__main__":
    if not is_streamlit_running():
        from subprocess import Popen
        import sys

        cmd = [sys.executable, "-m", "streamlit", "run", os.path.abspath(__file__)]
        Popen(cmd)
    else:
        main()
