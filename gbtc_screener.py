import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# CONFIG
TICKER = "GBTC"
DAYS_LOOKBACK = 90
ENTRY_LOOKBACK = 10
EXIT_LOOKBACK = 10
RVOL_LOOKBACK = 50

# DATA FETCHING
@st.cache_data
def get_data(ticker):
    end = datetime.today()
    start = end - timedelta(days=DAYS_LOOKBACK * 2)
    df = yf.download(ticker, start=start, end=end)
    df = df.reset_index()
    df["RVOL50"] = df["Volume"] / df["Volume"].rolling(RVOL_LOOKBACK).mean()
    df["20SMA"] = df["Close"].rolling(20).mean()
    df["50SMA"] = df["Close"].rolling(50).mean()
    return df.dropna()

# SCORING FUNCTIONS
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

    if day["Close"] > day["Open"]:
        score += 1
        traits.append("Bullish candle")

    if day["Close"] > day["20SMA"]:
        score += 1
        traits.append("Above 20SMA")

    if day["Close"] > day["50SMA"]:
        score += 1
        traits.append("Above 50SMA")

    if day["High"] > prev_day["High"] and day["Low"] > prev_day["Low"]:
        score += 1
        traits.append("Bullish continuation")

    rvol_pts = rvol_score(day["RVOL50"])
    score += rvol_pts
    if rvol_pts > 0:
        traits.append(f"RVOL: {day['RVOL50']:.2f}")

    return score, traits

def evaluate_exit(day, entry_price):
    reasons = []
    score = 0

    if day["Close"] < day["20SMA"]:
        score += 1
        reasons.append("Below 20SMA")

    if day["Close"] < entry_price:
        score += 1
        reasons.append("Below entry price")

    return score, reasons

# APP LAYOUT
st.set_page_config(layout="wide")
st.title("📈 GBTC Entry & Exit Screener")

with st.spinner("Loading latest GBTC data..."):
    df = get_data(TICKER)

if df.empty:
    st.error("No data available.")
    st.stop()

entry_results = []
exit_results = []

# ENTRY ANALYSIS
for i in range(-ENTRY_LOOKBACK, 0):
    day = df.iloc[i]
    prev = df.iloc[i - 1]
    score, traits = evaluate_entry(day, prev)
    entry_results.append({
        "Date": day["Date"].strftime("%Y-%m-%d"),
        "Close": round(day["Close"], 2),
        "Score": score,
        "Traits": ", ".join(traits)
    })

# EXIT ANALYSIS
entry_price_reference = df.iloc[-EXIT_LOOKBACK - 1]["Close"]
for i in range(-EXIT_LOOKBACK, 0):
    day = df.iloc[i]
    score, reasons = evaluate_exit(day, entry_price_reference)
    exit_results.append({
        "Date": day["Date"].strftime("%Y-%m-%d"),
        "Close": round(day["Close"], 2),
        "Score": score,
        "Reasons": ", ".join(reasons)
    })

tab1, tab2 = st.tabs(["📥 Entry Screener", "📤 Exit Screener"])

with tab1:
    st.subheader("Entry Signals (Last 10 Days)")
    st.dataframe(pd.DataFrame(entry_results).sort_values("Date", ascending=False))

with tab2:
    st.subheader("Exit Signals (Last 10 Days)")
    st.dataframe(pd.DataFrame(exit_results).sort_values("Date", ascending=False))
