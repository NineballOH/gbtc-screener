import streamlit as st
import pandas as pd
import numpy as np

# === Parameters ===
ENTRY_LOOKBACK = 5
EXIT_LOOKBACK = 5

# === Load Data ===
def load_data():
    df = pd.read_csv("/mnt/data/gbtc_data.csv", parse_dates=["Date"])
    df = df.sort_values("Date").reset_index(drop=True)
    return df

# === Entry Signal Logic ===
def evaluate_entry(today_row, prev_row):
    try:
        if today_row["Close"] > today_row["Open"] and today_row["Volume"] > prev_row["Volume"]:
            return 1, "Bullish candle + rising volume"
        else:
            return 0, "No entry signal"
    except:
        return 0, "Error in entry logic"

# === Exit Signal Logic ===
def evaluate_exit(today_row, prev_row):
    try:
        if today_row["Close"] < today_row["Open"] and today_row["Volume"] > prev_row["Volume"]:
            return 1, "Bearish candle + rising volume"
        else:
            return 0, "No exit signal"
    except:
        return 0, "Error in exit logic"

# === Streamlit App ===
st.set_page_config(page_title="GBTC Entry/Exit Screener")
st.title("📈 GBTC Entry/Exit Screener")

# Load data
df = load_data()
if df.empty:
    st.error("No data returned for GBTC. Please check your file.")
    st.stop()

# Evaluate Entry Signals
entry_results = []
for i in range(ENTRY_LOOKBACK, len(df)):
    today = df.iloc[i]
    prev = df.iloc[i - 1]
    score, traits = evaluate_entry(today, prev)
    entry_results.append({
        "Date": today["Date"].strftime("%Y-%m-%d"),
        "Close": round(float(today["Close"]), 2),
        "Score": score,
        "Traits": traits
    })

# Evaluate Exit Signals
exit_results = []
for i in range(EXIT_LOOKBACK, len(df)):
    today = df.iloc[i]
    prev = df.iloc[i - 1]
    score, traits = evaluate_exit(today, prev)
    exit_results.append({
        "Date": today["Date"].strftime("%Y-%m-%d"),
        "Close": round(float(today["Close"]), 2),
        "Score": score,
        "Traits": traits
    })

# Display
st.subheader("Recent Entry Signals")
st.dataframe(pd.DataFrame(entry_results[-10:]))

st.subheader("Recent Exit Signals")
st.dataframe(pd.DataFrame(exit_results[-10:]))
