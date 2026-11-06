import streamlit as st
import pandas as pd
import requests
import os
from datetime import date
from dotenv import load_dotenv

st.set_page_config(page_title="Vajra Analytics - Option Chain", layout="wide")
st.title("📊 Live Nifty Option Chain & Volume Analytics")

load_dotenv()
try:
    ACCESS_TOKEN = st.secrets["UPSTOX_ACCESS_TOKEN"]
except:
    ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

if not ACCESS_TOKEN:
    st.error("⚠️ Access Token nahi mila! Kripya Streamlit Secrets ya .env file check karein.")
    st.stop()

# Expiry Dates automatically Upstox se fetch honge
@st.cache_data(ttl=3600)
def fetch_expiries():
    url = "https://api.upstox.com/v2/option/contract?instrument_key=NSE_INDEX%7CNifty%2050"
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {ACCESS_TOKEN}'
    }
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        if data.get('status') == 'success':
            expiries = sorted({item['expiry'] for item in data.get('data', []) if item.get('expiry')})
            return [e for e in expiries if e >= str(date.today())]
    except Exception as e:
        st.error(f"Expiry fetch error: {e}")
    return []

expiry_options = fetch_expiries()

if not expiry_options:
    st.error("⚠️ Expiry dates load nahi hui! Access Token check karein.")
    st.stop()

st.sidebar.header("Settings")
expiry_date = st.sidebar.selectbox("Select Expiry Date", expiry_options)

@st.cache_data(ttl=5)
def fetch_option_chain(expiry):
    url = f"https://api.upstox.com/v2/option/chain?instrument_key=NSE_INDEX%7CNifty%2050&expiry_date={expiry}"
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {ACCESS_TOKEN}'
    }
    try:
        response = requests.get(url, headers=headers)
        data = response.json()

        if data.get('status') == 'success':
            chain_data = []
            for item in data.get('data', []):
                strike = item.get('strike_price')
                call_opt = item.get('call_options', {})
                put_opt = item.get('put_options', {})

                c_oi = call_opt.get('market_data', {}).get('oi', 0)
                p_oi = put_opt.get('market_data', {}).get('oi', 0)
                c_vol = call_opt.get('market_data', {}).get('volume', 0)
                p_vol = put_opt.get('market_data', {}).get('volume', 0)
                c_ltp = call_opt.get('market_data', {}).get('ltp', 0)
                p_ltp = put_opt.get('market_data', {}).get('ltp', 0)

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
        else:
            st.error(f"API Error: {data}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

df = fetch_option_chain(expiry_date)

if df.empty:
    st.warning("⚠️ Data load nahi hua! Kripya check karein ki Upstox Access Token active hai aur sahi dala hai.")
else:
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
    st.dataframe(df, use_container_width=True, height=500)
