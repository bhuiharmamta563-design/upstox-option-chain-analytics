import streamlit as st
import pandas as pd
import upstox_client
import os
from dotenv import load_dotenv

# Page Configuration
st.set_page_config(page_title="Vajra Analytics - Option Chain", layout="wide")
st.title("📊 Live Nifty Option Chain & Volume Analytics")

# Environment variables load karein (.env file ya Streamlit secrets se)
load_dotenv()
ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

if not ACCESS_TOKEN:
    st.error("⚠️ Access Token nahi mila! Kripya .env file ya Streamlit secrets check karein.")
    st.stop()

# Upstox API Setup
configuration = upstox_client.Configuration()
configuration.access_token = ACCESS_TOKEN
api_instance = upstox_client.OptionsApi(upstox_client.ApiClient(configuration))

# Sidebar Controls
st.sidebar.header("Settings")
expiry_date = st.sidebar.text_input("Expiry Date (YYYY-MM-DD)", "2026-11-12")

@st.cache_data(ttl=5)
def fetch_option_chain(expiry):
    try:
        response = api_instance.get_option_chain("NSE_INDEX|Nifty 50", expiry)
        chain_data = []
        
        for item in response.data:
            strike = item.strike_price
            c_oi = item.call_options.market_data.oi if item.call_options else 0
            p_oi = item.put_options.market_data.oi if item.put_options else 0
            c_vol = item.call_options.market_data.volume if item.call_options else 0
            p_vol = item.put_options.market_data.volume if item.put_options else 0
            c_ltp = item.call_options.market_data.ltp if item.call_options else 0
            p_ltp = item.put_options.market_data.ltp if item.put_options else 0

            chain_data.append({
                "Call Vol": c_vol,
                "Call OI": c_oi,
                "Call LTP": c_ltp,
                "Strike": strike,
                "Put LTP": p_ltp,
                "Put OI": p_oi,
                "Put Vol": p_vol
            })
        return pd.DataFrame(chain_data)
    except Exception as e:
        st.error(f"Data fetch karne mein error: {e}")
        return pd.DataFrame()

# Data Fetching
df = fetch_option_chain(expiry_date)

if not df.empty:
    # Key Levels Metrics (Highest OI & Volume)
    max_call_oi_row = df.loc[df['Call OI'].idxmax()]
    max_put_oi_row = df.loc[df['Put OI'].idxmax()]
    max_call_vol_row = df.loc[df['Call Vol'].idxmax()]
    max_put_vol_row = df.loc[df['Put Vol'].idxmax()]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🔴 Major Resistance (Max Call OI)", f"{max_call_oi_row['Strike']}", f"OI: {max_call_oi_row['Call OI']:,}")
    col2.metric("🟢 Major Support (Max Put OI)", f"{max_put_oi_row['Strike']}", f"OI: {max_put_oi_row['Put OI']:,}")
    col3.metric("⚡ Max Call Volume Strike", f"{max_call_vol_row['Strike']}", f"Vol: {max_call_vol_row['Call Vol']:,}")
    col4.metric("⚡ Max Put Volume Strike", f"{max_put_vol_row['Strike']}", f"Vol: {max_put_vol_row['Put Vol']:,}")

    st.markdown("---")
    st.subheader("📋 Complete Option Chain Matrix")
    
    # Styled Table
    st.dataframe(df, use_container_width=True, height=500)
