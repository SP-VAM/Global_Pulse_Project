import yfinance as yf
import pandas as pd
import os
from datetime import datetime

# Folder to store individual company files
OUTPUT_DIR = "stock_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Company Name : Yahoo Finance Ticker
companies = {
    "Adani Enterprises Ltd": "ADANIENT.NS",
    "Adani Ports & Special Economic Zone Ltd": "ADANIPORTS.NS",
    "Apollo Hospitals Enterprise Ltd": "APOLLOHOSP.NS",
    "Asian Paints Ltd": "ASIANPAINT.NS",
    "Axis Bank Ltd": "AXISBANK.NS",
    "Bajaj Auto Ltd": "BAJAJ-AUTO.NS",
    "Bajaj Finance Ltd": "BAJFINANCE.NS",
    "Bajaj Finserv Ltd": "BAJAJFINSV.NS",
    "Bharti Airtel Ltd": "BHARTIARTL.NS",
    "Bharat Electronics Ltd": "BEL.NS",
    "Cipla Ltd": "CIPLA.NS",
    "Coal India Ltd": "COALINDIA.NS",
    "Dr. Reddy's Laboratories Ltd": "DRREDDY.NS",
    "Eicher Motors Ltd": "EICHERMOT.NS",
    "Grasim Industries Ltd": "GRASIM.NS",
    "HCL Technologies Ltd": "HCLTECH.NS",
    "HDFC Bank Ltd": "HDFCBANK.NS",
    "HDFC Life Insurance Ltd": "HDFCLIFE.NS",
    "Hero MotoCorp Ltd": "HEROMOTOCO.NS",
    "Hindustan Unilever Ltd": "HINDUNILVR.NS",
    "Hindalco Industries Ltd": "HINDALCO.NS",
    "ICICI Bank Ltd": "ICICIBANK.NS",
    "IndusInd Bank Ltd": "INDUSINDBK.NS",
    "Infosys Ltd": "INFY.NS",
    "ITC Ltd": "ITC.NS",
    "JSW Steel Ltd": "JSWSTEEL.NS",
    "Kotak Mahindra Bank Ltd": "KOTAKBANK.NS",
    "Larsen & Toubro Ltd": "LT.NS",
    "Mahindra & Mahindra Ltd": "M&M.NS",
    "Maruti Suzuki India Ltd": "MARUTI.NS",
    "NTPC Ltd": "NTPC.NS",
    "Oil & Natural Gas Corporation Ltd": "ONGC.NS",
    "Power Grid Corporation of India Ltd": "POWERGRID.NS",
    "Reliance Industries Ltd": "RELIANCE.NS",
    "State Bank of India": "SBIN.NS",
    "Shriram Finance Ltd": "SHRIRAMFIN.NS",
    "Sun Pharmaceutical Industries Ltd": "SUNPHARMA.NS",
    "Tata Consultancy Services Ltd": "TCS.NS",
    "Tata Consumer Products Ltd": "TATACONSUM.NS",
    "Tata Motors Passenger Vehicles Ltd": "TATAMOTORS.NS",
    "Tata Steel Ltd": "TATASTEEL.NS",
    "Tech Mahindra Ltd": "TECHM.NS",
    "Titan Company Ltd": "TITAN.NS",
    "Trent Ltd": "TRENT.NS",
    "UltraTech Cement Ltd": "ULTRACEMCO.NS",
    "Wipro Ltd": "WIPRO.NS",
    "Nestle India Ltd": "NESTLEIND.NS",
    "SBI Life Insurance Ltd": "SBILIFE.NS",
    "Eternal Ltd": "ETERNAL.NS",
    "Jio Financial Services Ltd": "JIOFIN.NS"
}

all_data = []

for company, ticker in companies.items():

    print(f"Downloading {company} ({ticker})...")

    try:
        df = yf.download(
            ticker,
            start="2022-01-01",
            end=datetime.now().strftime("%Y-%m-%d"),  # Dynamic end date
            interval="1d",         # Daily data
            auto_adjust=False,
            progress=False
        )

        if df.empty:
            print(f"No data found for {ticker}")
            continue

        # Convert index to column
        df.reset_index(inplace=True)

        # Add useful columns
        df["Company"] = company
        df["Ticker"] = ticker
        df["Year"] = df["Date"].dt.year
        df["Quarter"] = "Q" + df["Date"].dt.quarter.astype(str)
        df["Month"] = df["Date"].dt.month

        # Save individual company CSV
        filename = ticker.replace(".NS", "") + ".csv"
        df.to_csv(os.path.join(OUTPUT_DIR, filename), index=False)

        all_data.append(df)

    except Exception as e:
        print(f"Error downloading {ticker}: {e}")

# Save one combined CSV
if all_data:
    combined = pd.concat(all_data, ignore_index=True)
    combined.to_csv("all_companies_stock_data.csv", index=False)

# ==========================================================
# Download Nifty 50 Index data for market-relative features
# ==========================================================
print("\nDownloading Nifty 50 Index data...")
try:
    nifty = yf.download(
        "^NSEI",
        start="2022-01-01",
        end=datetime.now().strftime("%Y-%m-%d"),  # Dynamic end date
        interval="1d",
        auto_adjust=False,
        progress=False
    )
    
    if not nifty.empty:
        nifty.reset_index(inplace=True)
        nifty["Ticker"] = "NIFTY_50"
        nifty["Company"] = "Nifty 50 Index"
        nifty["Year"] = nifty["Date"].dt.year
        nifty["Quarter"] = "Q" + nifty["Date"].dt.quarter.astype(str)
        nifty["Month"] = nifty["Date"].dt.month
        
        nifty.to_csv(os.path.join(OUTPUT_DIR, "nifty_data.csv"), index=False)
        print(f"✅ Nifty 50 data saved ({len(nifty)} rows)")
    else:
        print("⚠️ No Nifty data found")
except Exception as e:
    print(f"⚠️ Error downloading Nifty data: {e}")

print("\n✅ All stock data downloaded successfully!")
