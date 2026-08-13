"""
Live stock data fetcher for NSE stocks.
Fetches fresh data on every call using yfinance with fallback to direct NSE API.
"""

import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import time


def fetch_live_price(ticker_symbol):
    """
    Fetch live stock price data from Yahoo Finance.
    
    Parameters
    ----------
    ticker_symbol : str
        Yahoo Finance ticker (e.g., "RELIANCE.NS")
    
    Returns
    -------
    dict
        Live price data with keys: current_price, open, high, low, 
        previous_close, volume, last_updated, change, change_pct
    """
    try:
        stock = yf.Ticker(ticker_symbol)
        
        # Get real-time data
        info = stock.info if hasattr(stock, 'info') else {}
        
        # Get today's intraday data
        hist = stock.history(period="1d", interval="1m")
        
        current_price = None
        open_price = None
        high_price = None
        low_price = None
        volume = None
        previous_close = None
        
        if not hist.empty:
            current_price = float(hist['Close'].iloc[-1])
            open_price = float(hist['Open'].iloc[0])
            high_price = float(hist['High'].max())
            low_price = float(hist['Low'].min())
            volume = int(hist['Volume'].sum())
        
        # Fallback to info if intraday data is empty
        if current_price is None:
            current_price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
        
        if open_price is None:
            open_price = info.get('regularMarketOpen')
        
        if high_price is None:
            high_price = info.get('regularMarketDayHigh')
        
        if low_price is None:
            low_price = info.get('regularMarketDayLow')
        
        if volume is None:
            volume = info.get('regularMarketVolume')
        
        previous_close = info.get('regularMarketPreviousClose') or info.get('previousClose')
        
        # Calculate change
        change = None
        change_pct = None
        if current_price is not None and previous_close is not None and previous_close != 0:
            change = current_price - previous_close
            change_pct = (change / previous_close) * 100
        
        return {
            "current_price": round(current_price, 2) if current_price else None,
            "open": round(open_price, 2) if open_price else None,
            "high": round(high_price, 2) if high_price else None,
            "low": round(low_price, 2) if low_price else None,
            "previous_close": round(previous_close, 2) if previous_close else None,
            "volume": volume,
            "change": round(change, 2) if change else None,
            "change_pct": round(change_pct, 2) if change_pct else None,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "Yahoo Finance",
        }
    except Exception as e:
        return {"error": str(e), "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


def fetch_nse_live_data(ticker_symbol):
    """
    Fetch live NSE data using NSE India API directly.
    More accurate for Indian stocks.
    
    Parameters
    ----------
    ticker_symbol : str
        NSE ticker (e.g., "RELIANCE")
    
    Returns
    -------
    dict
        Live price data
    """
    try:
        # Clean ticker
        ticker = ticker_symbol.upper().replace(".NS", "")
        
        # NSE India API endpoint
        url = f"https://www.nseindia.com/api/quote-equity?symbol={ticker}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
        
        session = requests.Session()
        session.headers.update(headers)
        
        # First visit NSE homepage to get cookies
        session.get("https://www.nseindia.com", timeout=10)
        time.sleep(1)
        
        response = session.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            price_info = data.get("priceInfo", {})
            
            return {
                "current_price": price_info.get("lastPrice"),
                "open": price_info.get("open"),
                "high": price_info.get("intraDayHighLow", {}).get("max"),
                "low": price_info.get("intraDayHighLow", {}).get("min"),
                "previous_close": price_info.get("previousClose"),
                "volume": price_info.get("totalTradedVolume"),
                "change": price_info.get("change"),
                "change_pct": price_info.get("pChange"),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": "NSE India",
            }
        else:
            # Fallback to Yahoo Finance
            return fetch_live_price(ticker_symbol)
            
    except Exception:
        # Fallback to Yahoo Finance
        return fetch_live_price(ticker_symbol)


def get_live_market_data(ticker_symbol):
    """
    Get live market data with best available source.
    Tries NSE API first, falls back to Yahoo Finance.
    
    Parameters
    ----------
    ticker_symbol : str
        Stock ticker symbol
    
    Returns
    -------
    dict
        Live market data
    """
    # Try NSE API first
    nse_data = fetch_nse_live_data(ticker_symbol)
    
    if "error" not in nse_data and nse_data.get("current_price") is not None:
        return nse_data
    
    # Fallback to Yahoo Finance
    return fetch_live_price(ticker_symbol)

