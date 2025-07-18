import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# CONFIG
TICKER = "GBTC"
DAYS_LOOKBACK = 2567
ENTRY_LOOKBACK = 60
EXIT_LOOKBACK = 60
RVOL_LOOKBACK = 50

# DATA FETCHING
@st.cache_data
def get_data(ticker):
    try:
        # Try multiple approaches to get maximum data
        end = datetime.today()
        
        # Option 1: Try with period="max" first
        try:
            st.write("Attempting to fetch maximum available data...")
            df = yf.download(ticker, period="max")
            st.write(f"Period='max' returned {len(df)} rows")
        except:
            st.write("Period='max' failed, trying date range...")
            # Option 2: Try with a very early start date
            start = datetime(2013, 1, 1)  # GBTC inception was around 2013
            df = yf.download(ticker, start=start, end=end)
            st.write(f"Date range approach returned {len(df)} rows")
        
        # Handle MultiIndex columns if they exist
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        
        df = df.reset_index()
        
        # Show available date range
        if len(df) > 0:
            st.write(f"Available data range: {df['Date'].min()} to {df['Date'].max()}")
            st.write(f"Total trading days available: {len(df)}")
        
        # Ensure we have the required columns
        required_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"Missing columns: {missing_cols}")
            return pd.DataFrame()
        
        # Calculate indicators
        df["RVOL50"] = df["Volume"] / df["Volume"].rolling(RVOL_LOOKBACK).mean()
        df["20SMA"] = df["Close"].rolling(20).mean()
        df["50SMA"] = df["Close"].rolling(50).mean()
        
        return df.dropna()
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return pd.DataFrame()

# SCORING FUNCTIONS
def rvol_score(rvol):
    if pd.isna(rvol):
        return 0
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
    
    # Check for NaN values
    if pd.isna(day["Close"]) or pd.isna(day["Open"]):
        return score, traits
    
    if day["Close"] > day["Open"]:
        score += 1
        traits.append("Bullish candle")
    
    if not pd.isna(day["20SMA"]) and day["Close"] > day["20SMA"]:
        score += 1
        traits.append("Above 20SMA")
    
    if not pd.isna(day["50SMA"]) and day["Close"] > day["50SMA"]:
        score += 1
        traits.append("Above 50SMA")
    
    if (not pd.isna(day["High"]) and not pd.isna(prev_day["High"]) and 
        not pd.isna(day["Low"]) and not pd.isna(prev_day["Low"]) and
        day["High"] > prev_day["High"] and day["Low"] > prev_day["Low"]):
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
    
    # Check for NaN values
    if pd.isna(day["Close"]) or pd.isna(entry_price):
        return score, reasons
    
    if not pd.isna(day["20SMA"]) and day["Close"] < day["20SMA"]:
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
    st.error("No data available. Please check your internet connection and try again.")
    st.stop()

# Check if we have enough data
available_days = len(df)
requested_days = max(ENTRY_LOOKBACK, EXIT_LOOKBACK) + 1

if available_days < requested_days:
    st.warning(f"Requested {requested_days} days but only {available_days} days available.")
    st.write(f"Using all available data: {available_days} days")
    # Adjust lookback to available data
    max_lookback = available_days - 1
    actual_entry_lookback = min(ENTRY_LOOKBACK, max_lookback)
    actual_exit_lookback = min(EXIT_LOOKBACK, max_lookback)
    st.write(f"Adjusted entry lookback: {actual_entry_lookback} days")
    st.write(f"Adjusted exit lookback: {actual_exit_lookback} days")
else:
    actual_entry_lookback = ENTRY_LOOKBACK
    actual_exit_lookback = EXIT_LOOKBACK

entry_results = []
exit_results = []

# ENTRY ANALYSIS
st.write(f"Analyzing last {actual_entry_lookback} days for entry signals...")
for i in range(max(-len(df), -actual_entry_lookback), 0):
    if i - 1 >= -len(df):  # Make sure we have a previous day
        day = df.iloc[i]
        prev = df.iloc[i - 1]
        score, traits = evaluate_entry(day, prev)
        entry_results.append({
            "Date": day["Date"].strftime("%Y-%m-%d"),
            "Close": round(day["Close"], 2),
            "Score": score,
            "Traits": ", ".join(traits) if traits else "No signals"
        })

# EXIT ANALYSIS
st.write(f"Analyzing last {actual_exit_lookback} days for exit signals...")
if len(df) > actual_exit_lookback:
    entry_price_reference = df.iloc[-actual_exit_lookback - 1]["Close"]
    for i in range(max(-len(df), -actual_exit_lookback), 0):
        day = df.iloc[i]
        score, reasons = evaluate_exit(day, entry_price_reference)
        exit_results.append({
            "Date": day["Date"].strftime("%Y-%m-%d"),
            "Close": round(day["Close"], 2),
            "Score": score,
            "Reasons": ", ".join(reasons) if reasons else "No exit signals"
        })

# Display results
tab1, tab2 = st.tabs(["📥 Entry Screener", "📤 Exit Screener"])

with tab1:
    st.subheader(f"Entry Signals (Last {actual_entry_lookback} Days)")
    if entry_results:
        entry_df = pd.DataFrame(entry_results).sort_values("Date", ascending=False)
        st.dataframe(entry_df, use_container_width=True)
        
        # Show summary
        avg_score = entry_df["Score"].mean()
        st.metric("Average Entry Score", f"{avg_score:.2f}")
    else:
        st.warning("No entry data available")

with tab2:
    st.subheader(f"Exit Signals (Last {actual_exit_lookback} Days)")
    if exit_results:
        exit_df = pd.DataFrame(exit_results).sort_values("Date", ascending=False)
        st.dataframe(exit_df, use_container_width=True)
        
        # Show summary
        avg_score = exit_df["Score"].mean()
        st.metric("Average Exit Score", f"{avg_score:.2f}")
    else:
        st.warning("No exit data available")

# Display latest data info
st.sidebar.subheader("Data Info")
st.sidebar.write(f"Total days of data: {len(df)}")
st.sidebar.write(f"Date range: {df['Date'].min().strftime('%Y-%m-%d')} to {df['Date'].max().strftime('%Y-%m-%d')}")
st.sidebar.write(f"Latest close: ${df['Close'].iloc[-1]:.2f}")
