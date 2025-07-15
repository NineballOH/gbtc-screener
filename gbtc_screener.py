import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# =============================
# CONFIGURATION
# =============================
TICKER = "GBTC"
DAYS_LOOKBACK = 90
ENTRY_LOOKBACK = 10
EXIT_LOOKBACK = 5
RVOL_LOOKBACK = 50

# =============================
# HELPER FUNCTIONS
# =============================
def get_data(ticker):
    end = datetime.today()
    start = end - timedelta(days=DAYS_LOOKBACK * 2)  # account for weekends/holidays
    df = yf.download(ticker, start=start, end=end)
    df = df.reset_index()
    df["RVOL50"] = df["Volume"] / df["Volume"].rolling(RVOL_LOOKBACK).mean()
    df["20SMA"] = df["Close"].rolling(20).mean()
    df["50SMA"] = df["Close"].rolling(50).mean()
    return df.dropna()

def rvol_score(rvol):
    if rvol > 5.0:
        return 5
    elif rvol > 3.0:
        return 3
    elif rvol > 2.0:
        return 2
    elif rvol > 1.5:
        return 1.5
    elif rvol > 1.0:
        return 1
    return 0

def evaluate_entry(day, prev_day):
    score = 0
    traits = []

    if float(day["Close"]) > float(day["Open"]):
        score += 1
        traits.append("Bullish candle")

    if float(day["Close"]) > float(day["20SMA"]):
        score += 1
        traits.append("Above 20SMA")

    if float(day["Close"]) > float(day["50SMA"]):
        score += 1
        traits.append("Above 50SMA")

    if float(day["High"]) > float(prev_day["High"]) and float(day["Low"]) > float(prev_day["Low"]):
        score += 1
        traits.append("Bullish continuation")

    return score, traits

def evaluate_exit(day, entry_day):
    reasons = []

    if float(day["Close"]) < float(day["20SMA"]):
        reasons.append("Below 20SMA")

    if float(day["Close"]) < float(entry_day["Close"]):
        reasons.append("Below entry close")

    return len(reasons), reasons

# =============================
# STREAMLIT APP
# =============================
st.set_page_config(layout="wide")
st.title("\U0001F4C8 GBTC Entry/Exit Screener")

with st.spinner("Loading GBTC data from Yahoo Finance..."):
    df = get_data(TICKER)

entry_results = []
exit_results = []

if df.empty:
    st.error("No data returned for GBTC. Please try again later.")
    st.stop()

for i in range(-ENTRY_LOOKBACK, 0):
    today = df.iloc[i]
    prev = df.iloc[i - 1]
    score, reasons = evaluate_entry(today, prev)
    entry_results.append({
        "Date": pd.to_datetime(today["Date"]).strftime("%Y-%m-%d"),
        "Close": round(float(today["Close"]), 2),
        "Score": score,
        "Traits": reasons
    })

for i in range(-EXIT_LOOKBACK, 0):
    today = df.iloc[i]
    entry_day = df.iloc[i - 1]
    score, reasons = evaluate_exit(today, entry_day)
    exit_results.append({
        "Date": pd.to_datetime(today["Date"]).strftime("%Y-%m-%d"),
        "Close": round(float(today["Close"]), 2),
        "Score": score,
        "Traits": reasons
    })

col1, col2 = st.columns(2)

with col1:
    st.subheader("\U0001F4E5 Entry Screener (Last 10 Days)")
    st.dataframe(pd.DataFrame(entry_results).sort_values("Date", ascending=False))

with col2:
    st.subheader("\U0001F6AA Exit Screener (Last 5 Days)")
    st.dataframe(pd.DataFrame(exit_results).sort_values("Date", ascending=False))
