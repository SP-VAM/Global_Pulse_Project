"""
Plotly chart components for the Streamlit dashboard.
Provides reusable chart functions for stock analysis visualization.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


def create_candlestick_chart(df, company_name="", height=500):
    """
    Create a candlestick chart with volume bars.

    Parameters
    ----------
    df : pd.DataFrame
        Stock data with Date, Open, High, Low, Close, Volume columns
    company_name : str
        Company name for the title
    height : int
        Chart height in pixels

    Returns
    -------
    plotly.graph_objects.Figure
        Candlestick chart figure
    """
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        subplot_titles=(f"{company_name} - Price", "Volume")
    )
    
    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df["Date"],
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Price",
            increasing_line_color="#00cc96",
            decreasing_line_color="#ef553b",
        ),
        row=1, col=1
    )
    
    # Volume bars
    colors = ["#00cc96" if df["Close"].iloc[i] >= df["Open"].iloc[i] else "#ef553b"
              for i in range(len(df))]
    
    fig.add_trace(
        go.Bar(
            x=df["Date"],
            y=df["Volume"],
            name="Volume",
            marker_color=colors,
            opacity=0.7,
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        height=height,
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        hovermode="x unified",
        showlegend=False,
    )
    
    fig.update_yaxes(title_text="Price (₹)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    
    return fig


def create_line_chart(df, company_name="", height=400):
    """
    Create a line chart for stock closing price.

    Parameters
    ----------
    df : pd.DataFrame
        Stock data with Date and Close columns
    company_name : str
        Company name for the title
    height : int
        Chart height in pixels

    Returns
    -------
    plotly.graph_objects.Figure
        Line chart figure
    """
    fig = go.Figure()
    
    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["Close"],
            mode="lines",
            name="Close Price",
            line=dict(color="#00cc96", width=2),
            fill="tozeroy",
            fillcolor="rgba(0, 204, 150, 0.1)",
        )
    )
    
    # Add moving averages if available
    if "SMA20" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["Date"],
                y=df["SMA20"],
                mode="lines",
                name="SMA20",
                line=dict(color="#ffa15a", width=1, dash="dash"),
            )
        )
    
    if "SMA50" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["Date"],
                y=df["SMA50"],
                mode="lines",
                name="SMA50",
                line=dict(color="#636efa", width=1, dash="dash"),
            )
        )
    
    fig.update_layout(
        title=f"{company_name} - Price with Moving Averages",
        height=height,
        template="plotly_dark",
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Price (₹)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
    )
    
    return fig


def create_rsi_chart(df, height=200):
    """
    Create an RSI (Relative Strength Index) chart.

    Parameters
    ----------
    df : pd.DataFrame
        Stock data with Date and RSI columns
    height : int
        Chart height in pixels

    Returns
    -------
    plotly.graph_objects.Figure
        RSI chart figure
    """
    if "RSI" not in df.columns:
        return None
    
    fig = go.Figure()
    
    # RSI line
    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["RSI"],
            mode="lines",
            name="RSI",
            line=dict(color="#ffa15a", width=2),
        )
    )
    
    # Overbought / Oversold lines
    fig.add_hline(y=70, line_dash="dash", line_color="#ef553b", opacity=0.5)
    fig.add_hline(y=30, line_dash="dash", line_color="#00cc96", opacity=0.5)
    fig.add_hline(y=50, line_dash="dot", line_color="#636efa", opacity=0.3)
    
    # Add fill between 30-70
    fig.add_hrect(y0=30, y1=70, line_width=0, fillcolor="gray", opacity=0.05)
    
    fig.update_layout(
        title="RSI (14)",
        height=height,
        template="plotly_dark",
        hovermode="x unified",
        yaxis_title="RSI",
        showlegend=False,
    )
    
    fig.update_yaxes(range=[0, 100])
    
    return fig


def create_macd_chart(df, height=250):
    """
    Create a MACD (Moving Average Convergence Divergence) chart.

    Parameters
    ----------
    df : pd.DataFrame
        Stock data with Date, MACD, MACD_SIGNAL, MACD_HIST columns
    height : int
        Chart height in pixels

    Returns
    -------
    plotly.graph_objects.Figure
        MACD chart figure
    """
    if not all(col in df.columns for col in ["MACD", "MACD_SIGNAL", "MACD_HIST"]):
        return None
    
    fig = go.Figure()
    
    # MACD line
    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["MACD"],
            mode="lines",
            name="MACD",
            line=dict(color="#636efa", width=2),
        )
    )
    
    # Signal line
    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["MACD_SIGNAL"],
            mode="lines",
            name="Signal",
            line=dict(color="#ffa15a", width=2),
        )
    )
    
    # Histogram
    colors = ["#00cc96" if v >= 0 else "#ef553b" for v in df["MACD_HIST"]]
    
    fig.add_trace(
        go.Bar(
            x=df["Date"],
            y=df["MACD_HIST"],
            name="Histogram",
            marker_color=colors,
            opacity=0.5,
        )
    )
    
    fig.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.5)
    
    fig.update_layout(
        title="MACD",
        height=height,
        template="plotly_dark",
        hovermode="x unified",
        yaxis_title="MACD",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
    )
    
    return fig


def create_bollinger_bands_chart(df, height=350):
    """
    Create a Bollinger Bands chart.

    Parameters
    ----------
    df : pd.DataFrame
        Stock data with Date, Close, BB_UPPER, BB_MIDDLE, BB_LOWER columns
    height : int
        Chart height in pixels

    Returns
    -------
    plotly.graph_objects.Figure
        Bollinger Bands chart figure
    """
    if not all(col in df.columns for col in ["BB_UPPER", "BB_MIDDLE", "BB_LOWER"]):
        return None
    
    fig = go.Figure()
    
    # Close price
    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["Close"],
            mode="lines",
            name="Close",
            line=dict(color="#00cc96", width=2),
        )
    )
    
    # Upper band
    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["BB_UPPER"],
            mode="lines",
            name="Upper Band",
            line=dict(color="#ef553b", width=1, dash="dash"),
        )
    )
    
    # Middle band (SMA20)
    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["BB_MIDDLE"],
            mode="lines",
            name="Middle (SMA20)",
            line=dict(color="#ffa15a", width=1.5),
        )
    )
    
    # Lower band
    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["BB_LOWER"],
            mode="lines",
            name="Lower Band",
            line=dict(color="#00cc96", width=1, dash="dash"),
            fill="tonexty",
            fillcolor="rgba(0, 204, 150, 0.05)",
        )
    )
    
    fig.update_layout(
        title="Bollinger Bands (20, 2)",
        height=height,
        template="plotly_dark",
        hovermode="x unified",
        yaxis_title="Price (₹)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
    )
    
    return fig


def create_feature_importance_chart(importance_df, height=400):
    """
    Create a horizontal bar chart for feature importance.

    Parameters
    ----------
    importance_df : pd.DataFrame
        DataFrame with Feature and Importance columns
    height : int
        Chart height in pixels

    Returns
    -------
    plotly.graph_objects.Figure
        Feature importance bar chart
    """
    if importance_df.empty:
        return None
    
    # Top 15 features
    df = importance_df.head(15).copy()
    
    fig = go.Figure()
    
    fig.add_trace(
        go.Bar(
            x=df["Importance"],
            y=df["Feature"],
            orientation="h",
            marker=dict(
                color=df["Importance"],
                colorscale="Viridis",
                showscale=True,
                colorbar=dict(title="Importance"),
            ),
        )
    )
    
    fig.update_layout(
        title="Feature Importance",
        height=height,
        template="plotly_dark",
        xaxis_title="Importance",
        yaxis_title="Feature",
        yaxis=dict(autorange="reversed"),
    )
    
    return fig


def create_prediction_vs_actual(df, height=400):
    """
    Create a chart showing predicted vs actual price movements.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with Date, Close, Prediction (0/1) columns
    height : int
        Chart height in pixels

    Returns
    -------
    plotly.graph_objects.Figure
        Prediction vs actual chart
    """
    if "Prediction" not in df.columns:
        return None
    
    fig = go.Figure()
    
    # Close price line
    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["Close"],
            mode="lines",
            name="Close Price",
            line=dict(color="gray", width=1),
            opacity=0.5,
        )
    )
    
    # Up predictions (green markers)
    up_data = df[df["Prediction"] == 1]
    fig.add_trace(
        go.Scatter(
            x=up_data["Date"],
            y=up_data["Close"],
            mode="markers",
            name="Predict UP",
            marker=dict(
                symbol="triangle-up",
                size=10,
                color="#00cc96",
            ),
        )
    )
    
    # Down predictions (red markers)
    down_data = df[df["Prediction"] == 0]
    fig.add_trace(
        go.Scatter(
            x=down_data["Date"],
            y=down_data["Close"],
            mode="markers",
            name="Predict DOWN",
            marker=dict(
                symbol="triangle-down",
                size=10,
                color="#ef553b",
            ),
        )
    )
    
    fig.update_layout(
        title="Price with Predictions",
        height=height,
        template="plotly_dark",
        hovermode="x unified",
        yaxis_title="Price (₹)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
    )
    
    return fig


def create_sentiment_chart(df, height=300):
    """
    Create a chart showing news sentiment over time.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with Date and Sentiment_Mean columns
    height : int
        Chart height in pixels

    Returns
    -------
    plotly.graph_objects.Figure
        Sentiment chart
    """
    if "Sentiment_Mean" not in df.columns:
        return None
    
    fig = go.Figure()
    
    # Sentiment line
    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["Sentiment_Mean"],
            mode="lines+markers",
            name="Sentiment",
            line=dict(color="#636efa", width=2),
            marker=dict(
                size=6,
                color=df["Sentiment_Mean"],
                colorscale=["#ef553b", "gray", "#00cc96"],
                cmin=-1,
                cmax=1,
                showscale=True,
                colorbar=dict(title="Sentiment"),
            ),
        )
    )
    
    fig.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.5)
    
    fig.update_layout(
        title="News Sentiment",
        height=height,
        template="plotly_dark",
        hovermode="x unified",
        yaxis_title="Sentiment Score",
        showlegend=False,
    )
    
    fig.update_yaxes(range=[-1.5, 1.5])
    
    return fig

