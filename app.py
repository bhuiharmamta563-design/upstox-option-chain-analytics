"""
Veer Zone Pro: Indices + Stocks (single file: app.py)

Install : pip install streamlit pandas numpy requests python-dotenv
Run     : streamlit run app.py

Secrets / .env keys:
  UPSTOX_ACCESS_TOKEN = "..."   (required, roz naya token)
  GEMINI_API_KEY      = "..."   (optional, FREE AI - aistudio.google.com)
  ANTHROPIC_API_KEY   = "..."   (optional, paid AI)
  GEMINI_MODEL        = "..."   (optional, default gemini-flash-latest)
"""
import hashlib
import json
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from datetime import time as dt_time
from urllib.parse import quote

import numpy as np
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

st.set_page_config(page_title="Veer Zone Pro", layout="wide")

load_dotenv()
try:
    ACCESS_TOKEN = st.secrets["UPSTOX_ACCESS_TOKEN"]
except Exception:
    ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

if not ACCESS_TOKEN:
    st.error("⚠️ Access Token nahi mila! Kripya Streamlit Secrets ya .env file check karein.")
    st.stop()

HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Bearer {ACCESS_TOKEN}",
}

# ---------------- Instrument selection (Index / Stock) ----------------
INDEXES = {
    "Nifty 50": "NSE_INDEX|Nifty 50",
    "Bank Nifty": "NSE_INDEX|Nifty Bank",
    "Fin Nifty": "NSE_INDEX|Nifty Fin Service",
    "Midcap Nifty": "NSE_INDEX|NIFTY MID SELECT",
    "Nifty Next 50": "NSE_INDEX|Nifty Next 50",
    "Sensex": "BSE_INDEX|SENSEX",
    "Bankex": "BSE_INDEX|BANKEX",
}
STOCKS = [
    "RELIANCE", "TATAPOWER", "TATASTEEL", "TMPV", "HDFCBANK", "ICICIBANK", "SBIN", "INFY", "TCS",
    "AXISBANK", "KOTAKBANK", "ITC", "LT", "BHARTIARTL", "MARUTI", "BAJFINANCE", "ADANIENT", "ADANIPORTS",
    "WIPRO", "HINDUNILVR", "SUNPHARMA", "M&M", "ONGC", "COALINDIA", "VEDL", "JSWSTEEL", "HINDALCO",
    "NTPC", "POWERGRID", "BANKBARODA", "PNB", "TITAN", "DLF", "HCLTECH", "TECHM", "INDUSINDBK",
]
OTHER_STOCK = "✍️ Doosra stock (khud likhein)"


def enc(key):
    return quote(key, safe="")


def resolve_stock(symbol):
    """Stock symbol -> Upstox instrument_key (Instrument Search API), session mein yaad rakhta hai."""
    cache = st.session_state.setdefault("stock_keys", {})
    if symbol in cache:
        return cache[symbol]
    try:
        r = requests.get(
            "https://api.upstox.com/v2/instruments/search",
            headers=HEADERS,
            params={"query": symbol, "exchanges": "NSE", "segments": "EQ", "records": 10},
            timeout=20,
        ).json()
        items = [i for i in r.get("data", []) if i.get("instrument_type") == "EQ"]
        exact = [i for i in items if str(i.get("trading_symbol", "")).upper() == symbol.upper()]
        hit = (exact or items or [None])[0]
        if hit:
            cache[symbol] = hit["instrument_key"]
            return cache[symbol]
    except Exception:
        pass
    return None


PAGE_DARK = "<style>.stApp{background:#0e1117;color:#e5e7eb}[data-testid=stSidebar]{background:#161b22}</style>"
PAGE_LIGHT = """<style>
.stApp, [data-testid=stHeader], [data-testid=stAppViewContainer] {background:#ffffff !important;}
.stApp, .stApp p, .stApp span, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp li, .stApp div {color:#111111;}
[data-testid=stSidebar] {background:#f3f4f6 !important;}
[data-testid=stSidebar] *, [data-testid=stSidebar] label, [data-testid=stSidebar] p {color:#111111 !important;}
[data-baseweb=select] > div, [data-baseweb=input], [data-baseweb=input] input, [data-testid=stNumberInput] input {background:#ffffff !important;color:#111111 !important;border-color:#d1d5db !important;}
[data-testid=stSelectbox] div, [data-testid=stSelectbox] span, [data-testid=stSelectbox] input, [data-testid=stSelectbox] [data-baseweb=select] div {background-color:#ffffff !important;color:#111111 !important;}
[data-testid=stTimeInput] input, [data-testid=stTimeInput] [data-baseweb=input], [data-testid=stTimeInput] [data-baseweb=input] div {background:#ffffff !important;color:#111111 !important;}
[data-testid=stTimeInput] *, [data-testid=stTimeInput] input {background-color:#ffffff !important;color:#111111 !important;border-color:#d1d5db !important;}
[data-testid=stSelectbox] svg, [data-testid=stTimeInput] svg {fill:#111111 !important;}
[data-testid=stNumberInput] button, [data-testid=stNumberInput] button div {background:#ffffff !important;color:#111111 !important;border-color:#d1d5db !important;}
[data-testid=stNumberInput] button svg {fill:#111111 !important;color:#111111 !important;}
[data-testid=stTextInput] input, [data-testid=stTextInput] [data-baseweb=base-input], [data-testid=stTextInput] [data-baseweb=base-input] div {background:#ffffff !important;color:#111111 !important;border-color:#d1d5db !important;}
[data-testid=stTextInput] input::placeholder {color:#6b7280 !important;}
[data-testid=stAlert], [data-testid=stAlertContainer] {background:#fffbeb !important;}
[data-testid=stAlert] *, [data-testid=stAlertContainer] * {color:#111111 !important;}
[data-testid=stHeader], [data-testid=stToolbar] {background:#ffffff !important;}
[data-testid=stToolbar] *, [data-testid=stHeader] * {color:#111111 !important;}
[data-testid=stToolbar] svg, [data-testid=stHeader] svg {fill:#111111 !important;stroke:#111111 !important;}
[data-testid=stButton] button, [data-testid=stBaseButton-secondary] {background:#ffffff !important;color:#111111 !important;border:1px solid #d1d5db !important;}
[data-testid=stButton] button:hover {border-color:#2563eb !important;color:#2563eb !important;}
[data-baseweb=popover] ul, [data-baseweb=menu], [data-baseweb=popover] li {background:#ffffff !important;color:#111111 !important;}
[data-testid=stTickBarMin], [data-testid=stTickBarMax], [data-testid=stTickBar] {color:#374151 !important;}
[data-testid=stRadio] label div p, [data-testid=stCheckbox] label p {color:#111111 !important;}
</style>"""
theme_pick = st.sidebar.radio("Theme", ["🌙 Dark", "☀️ Light"], horizontal=True, index=1)
st.session_state["theme_dark"] = theme_pick.startswith("🌙")
SIDEBAR_FIX = """<style>
[data-testid="stSidebarCollapseButton"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"],
[data-testid="stSidebarHeader"] button, [data-testid="stSidebarHeader"] {
  display: flex !important; visibility: visible !important; opacity: 1 !important; z-index: 999999 !important;
}
[data-testid="stHeader"] {display: flex !important; visibility: visible !important;}
</style>"""
INPUT_CSS_LIGHT = """<style>
html, body, textarea, input {color-scheme: light;}
[data-testid="stTextArea"] textarea, [data-testid="stTextArea"] div[data-baseweb="textarea"],
[data-testid="stTextArea"] div[data-baseweb="base-input"], textarea {background:#ffffff !important;color:#111827 !important;-webkit-text-fill-color:#111827 !important;}
div[data-baseweb="popover"] ul, div[data-baseweb="popover"] div[role="listbox"], ul[role="listbox"],
div[data-baseweb="popover"] li, li[role="option"], div[role="option"] {background:#ffffff !important;color:#111827 !important;}
li[role="option"]:hover, li[role="option"][aria-selected="true"] {background:#f1f5f9 !important;}
</style>"""
INPUT_CSS_DARK = """<style>
html, body, textarea, input {color-scheme: dark;}
[data-testid="stTextArea"] textarea, [data-testid="stTextArea"] div[data-baseweb="textarea"],
[data-testid="stTextArea"] div[data-baseweb="base-input"], textarea {background:#0f172a !important;color:#e5e7eb !important;-webkit-text-fill-color:#e5e7eb !important;}
div[data-baseweb="popover"] ul, div[data-baseweb="popover"] div[role="listbox"], ul[role="listbox"],
div[data-baseweb="popover"] li, li[role="option"], div[role="option"] {background:#0f172a !important;color:#e5e7eb !important;}
li[role="option"]:hover, li[role="option"][aria-selected="true"] {background:#1e293b !important;}
</style>"""
st.markdown((PAGE_DARK if st.session_state["theme_dark"] else PAGE_LIGHT) + SIDEBAR_FIX
            + (INPUT_CSS_DARK if st.session_state["theme_dark"] else INPUT_CSS_LIGHT), unsafe_allow_html=True)
st.sidebar.header("Instrument")
kind = st.sidebar.radio("Type", ["Index", "Stock"], horizontal=True)
if kind == "Index":
    inst_name = st.sidebar.selectbox("Index", list(INDEXES))
    inst_key = INDEXES[inst_name]
else:
    pick = st.sidebar.selectbox("Popular stock", STOCKS + [OTHER_STOCK])
    sym = st.sidebar.text_input("Stock symbol (jaise ITC, DLF)").strip().upper() if pick == OTHER_STOCK else pick
    if not sym:
        st.info("Sidebar mein stock ka symbol likhein (jaise ITC, DLF).")
        st.stop()
    inst_key = resolve_stock(sym)
    if not inst_key:
        st.error(f"'{sym}' ka instrument key nahi mila. Symbol sahi likhein ya Access Token check karein.")
        st.stop()
    inst_name = sym

st.title(f"📊 Veer Zone Pro · {inst_name}")
st.caption("Live Option Chain & Zone Analytics")


# ---------------- Expiry dates (auto) ----------------
@st.cache_data(ttl=3600)
def fetch_expiries(inst_key):
    url = f"https://api.upstox.com/v2/option/contract?instrument_key={enc(inst_key)}"
    try:
        data = requests.get(url, headers=HEADERS).json()
        if data.get("status") == "success":
            exp = sorted({i["expiry"] for i in data.get("data", []) if i.get("expiry")})
            return [e for e in exp if e >= str(date.today())]
    except Exception as e:
        st.error(f"Expiry fetch error: {e}")
    return []


expiry_options = fetch_expiries(inst_key)
if not expiry_options:
    st.error(f"⚠️ {inst_name} ki expiry dates load nahi hui! Access Token check karein, ya is instrument ke F&O options na hon (ya symbol badal gaya ho, jaise Tata Motors ab TMPV/TMCV).")
    st.stop()

st.sidebar.header("Settings")
expiry_date = st.sidebar.selectbox("Select Expiry Date", expiry_options)
n_strikes = st.sidebar.slider("ATM ke upar/niche strikes", 5, 30, 10)
show_summary = st.sidebar.checkbox("Strike ke baad PCR / Zone dikhao", value=True)
VOLUME_GUIDE_MD = """**VajraAnalytics - Volume ka Mahatva:**

1. **Asli Support aur Resistance:** Highest OI + Highest Volume = Strong Support / Resistance.
2. **Reversal aur Breakout:** Volume badhne par reversal ya breakout ka confirmation milta hai.
3. **Trap se Bachav:** Bina volume ke price movement fake/trap ho sakti hai.
4. **Liquidity:** Zyada volume se orders jaldi execute hote hain aur slippage kam hoti hai.

**Summary:** OI batata hai bade players kahan hain, Volume batata hai activity kitni tezi se ho rahi hai.

*Ye sirf shiksha ke liye hai, trading ki salah nahi.*"""
with st.sidebar.expander("📘 Volume Guide"):
    st.markdown(VOLUME_GUIDE_MD)
def last_trading_days(n=5):
    """Aaj se shuru karke pichhle n weekdays (holidays ka check nahi)."""
    out, d = [], date.today()
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d -= timedelta(days=1)
    return out


chart_day = date.today()   # historical ab nahi; hamesha aaj ka data
st.session_state.setdefault("past_t", dt_time(11, 0))   # pichhli date ka replay samay (page ke buttons se badalta hai)
zone_pts_s = st.sidebar.number_input("Supply zone ki chaudai (points, 0 = auto)", min_value=0.0, value=0.0, step=5.0,
                                     help="0 = auto: spot ka 0.16% (Nifty par lagbhag 40 points). Apni marzi ke points bhi likh sakte hain.")
zone_pts_d = st.sidebar.number_input("Demand zone ki chaudai (points, 0 = auto)", min_value=0.0, value=0.0, step=5.0,
                                     help="0 = auto: spot ka 0.16% (Nifty par lagbhag 40 points). Apni marzi ke points bhi likh sakte hain.")
zone_pts = {"supply": zone_pts_s, "demand": zone_pts_d}
show_vol_zones = st.sidebar.checkbox("📊 Volume zones chart par dikhao", value=True)
show_oi_zones = st.sidebar.checkbox("📈 OI zones chart par dikhao", value=True)
focus_mode = st.sidebar.checkbox("📺 Focus mode (sirf option chain)", value=False)
chart_focus = st.sidebar.checkbox("📈 Charts Focus mode (sirf charts)", value=False)
auto_refresh = st.sidebar.checkbox("🔄 Auto refresh (smooth, screen wahin rahegi)", value=False)
refresh_secs = 5
if auto_refresh:
    refresh_secs = st.sidebar.selectbox("Refresh kitne second mein", [1, 2, 3, 4, 5, 10, 15, 30, 60], index=4)
    if refresh_secs < 5:
        st.sidebar.caption("⚠️ 1-4 sec par Upstox ki limit ya slow net se dikkat ho to 5+ rakhein.")
if st.sidebar.button("🔄 Refresh now"):
    st.cache_data.clear()


# ---------------- Option chain data ----------------
@st.cache_data(ttl=1)
def fetch_option_chain(inst_key, expiry):
    url = (
        "https://api.upstox.com/v2/option/chain"
        f"?instrument_key={enc(inst_key)}&expiry_date={expiry}"
    )
    try:
        data = requests.get(url, headers=HEADERS).json()
        if data.get("status") != "success":
            st.error(f"API Error: {data}")
            return pd.DataFrame(), 0
        rows, spot = [], 0
        for item in data.get("data", []):
            spot = item.get("underlying_spot_price") or spot
            c = item.get("call_options", {}) or {}
            p = item.get("put_options", {}) or {}
            cm, pm = c.get("market_data", {}) or {}, p.get("market_data", {}) or {}
            cg, pg = c.get("option_greeks", {}) or {}, p.get("option_greeks", {}) or {}
            rows.append({
                "Call Vol": cm.get("volume", 0),
                "Call OI Chg": cm.get("oi", 0) - cm.get("prev_oi", 0),
                "Call OI": cm.get("oi", 0),
                "Call IV": cg.get("iv", 0),
                "Call LTP": cm.get("ltp", 0),
                "Strike": item.get("strike_price"),
                "Call Key": c.get("instrument_key"),
                "Put Key": p.get("instrument_key"),
                "Put LTP": pm.get("ltp", 0),
                "Put IV": pg.get("iv", 0),
                "Put OI": pm.get("oi", 0),
                "Put OI Chg": pm.get("oi", 0) - pm.get("prev_oi", 0),
                "Put Vol": pm.get("volume", 0),
            })
        return pd.DataFrame(rows), spot
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame(), 0


# ---------------- Smart analysis engine (Supply / Demand zones) ----------------
def fs(x):
    """Strike ko saaf dikhao: 25000.0 -> 25000, 392.5 -> 392.5"""
    x = float(x)
    return int(x) if x == int(x) else round(x, 2)


def zone_size_txt(z):
    return f"{fs(z['width'])} points"


def zone_dist_txt(z, side):
    d = z["dist"]
    if d < 0:
        return "spot zone ke andar / paar"
    return f"{fs(round(d, 1))} points " + ("upar" if side == "supply" else "niche")


def strength_label(score):
    return "Strong 💪" if score >= 70 else "Medium 👍" if score >= 45 else "Weak ⚠️"


NEAR_K = 10  # Zone 1 (Support/Resistance) spot ke sabse paas ke itne strikes mein se hi chuna jayega


def analyze(df, spot, zone_pts=0.0, prev=None):
    d = df.sort_values("Strike").reset_index(drop=True).copy()
    diffs = np.diff(d["Strike"].astype(float).values)
    diffs = diffs[diffs > 0]
    step = float(diffs.min()) if len(diffs) else 50.0          # strike gap (Nifty 50, BankNifty 100, stock 2.5...)

    # Zone ki chaudai (points): user ne di ho to wahi, warna auto = spot ka 0.16% (Nifty par ~40 points)
    def _w_of(v):
        w_ = float(v) if v and v > 0 else float(spot) * 0.0016
        w_ = round(w_) if w_ >= 1 else round(w_, 2)
        return max(w_, 0.01)
    if isinstance(zone_pts, dict):
        w_side = {"supply": _w_of(zone_pts.get("supply")), "demand": _w_of(zone_pts.get("demand"))}
    else:
        w_side = {"supply": _w_of(zone_pts), "demand": _w_of(zone_pts)}
    w = w_side["supply"]
    half = w / 2
    colmax = {c: max(float(d[c].max()), 1.0) for c in ("Call OI", "Put OI", "Call Vol", "Put Vol")}

    def make_zone(basis, side, rank, row):
        c = "Call" if side == "supply" else "Put"
        base = "Vol" if basis == "vol" else "OI"
        k = float(row["Strike"])
        pct = float(row[f"{c} {base}"]) / colmax[f"{c} {base}"] * 100      # poori chain ke sabse zyada ka kitna %
        chg = float(row[f"{c} OI Chg"])
        wz = w_side[side] if pct >= 60 else w_side[side] * 0.5    # side ki chaudai; 60% se neeche: aadha
        hz = wz / 2
        z = {
            "basis": basis, "side": side, "rank": rank, "strike": fs(k), "pct": pct,
            "primary": {"strike": fs(k), "score": pct, "oi": float(row[f"{c} OI"]),
                        "vol": float(row[f"{c} Vol"]), "chg": chg, "fresh": chg > 0},
            "low": round(k - hz, 2), "high": round(k + hz, 2), "width": wz,     # strike ke aas-paas wz points ki patti
        }
        z["dist"] = (z["low"] - spot) if side == "supply" else (spot - z["high"])  # spot se kitne points door
        return z

    zone_sets = {"vol": {"supply": [], "demand": []}, "oi": {"supply": [], "demand": []}}
    second_store = {}
    for basis in ("vol", "oi"):
        for side in ("supply", "demand"):
            col = ("Call " if side == "supply" else "Put ") + ("Vol" if basis == "vol" else "OI")
            pool = d[d["Strike"] >= spot - step] if side == "supply" else d[d["Strike"] <= spot + step]   # ek step ka buffer: spot ke chhote hilne par zone gayab nahi hota
            pool = pool[pool[col] > 0]
            if pool.empty:
                continue
            atm_k = float(d.loc[(d["Strike"] - spot).abs().idxmin(), "Strike"])   # ATM strike (spot ke sabse paas)
            if side == "supply":                                     # resistance: ATM se upar 10 strike tak
                near = pool[(pool["Strike"] >= atm_k) & (pool["Strike"] <= atm_k + NEAR_K * step)]
            else:                                                    # support: ATM se neeche 10 strike tak
                near = pool[(pool["Strike"] <= atm_k) & (pool["Strike"] >= atm_k - NEAR_K * step)]
            if near.empty:
                near = pool
            i1 = near[col].idxmax()                                  # Zone 1: market price ke paas ka sabse zyada
            _srt = near.sort_values(col, ascending=False)
            _sec = None
            if len(_srt) > 1:
                _r2 = _srt.iloc[1]
                _p2 = float(_r2[col]) / colmax[col] * 100
                if _p2 >= 75:
                    _sec = {"strike": fs(float(_r2["Strike"])), "pct": _p2}
            second_store[(basis, side)] = _sec
            kp = (prev or {}).get(f"{basis}_{side}")                 # HOLD: pichla zone tab tak rahe jab tak naya 15%+ zyada mazboot na ho
            if kp is not None:
                rp = near[near["Strike"] == kp]
                if not rp.empty and float(rp[col].iloc[0]) >= 0.85 * float(near[col].max()):
                    i1 = rp.index[0]
            out = [make_zone(basis, side, 1, d.loc[i1])]
            k1, lim = float(d.loc[i1, "Strike"]), 10 * step
            if side == "supply":                                     # Zone 2: bahar ki taraf (upar), 10 strikes tak
                cand = pool[(pool["Strike"] > k1) & (pool["Strike"] <= k1 + lim)]
            else:                                                    # Demand: bahar ki taraf (niche)
                cand = pool[(pool["Strike"] < k1) & (pool["Strike"] >= k1 - lim)]
            cand = cand[cand[col] >= 0.6 * colmax[col]]              # 60% ya usse upar: sab zone bante hain
            for rk, ix in enumerate(cand.sort_values(col, ascending=False).index, start=2):
                out.append(make_zone(basis, side, rk, d.loc[ix]))
            zone_sets[basis][side] = out
    zones_flat = [z for b_ in ("oi", "vol") for sd in ("supply", "demand") for z in zone_sets[b_][sd]]
    supply = (zone_sets["oi"]["supply"] or zone_sets["vol"]["supply"] or [None])[0]    # bias ke liye (OI zone 1)
    demand = (zone_sets["oi"]["demand"] or zone_sets["vol"]["demand"] or [None])[0]

    # Liquidity strikes: jahan Call+Put dono ka OI aur Volume sabse zyada
    tot_oi, tot_vol = d["Call OI"] + d["Put OI"], d["Call Vol"] + d["Put Vol"]
    liq_score = (0.5 * tot_oi / max(tot_oi.max(), 1) + 0.5 * tot_vol / max(tot_vol.max(), 1)) * 100
    liq = [
        {"strike": fs(d.loc[i, "Strike"]), "score": float(liq_score[i]),
         "oi": float(tot_oi[i]), "vol": float(tot_vol[i])}
        for i in liq_score.sort_values(ascending=False).index[:3]
    ]

    # Max pain
    k = d["Strike"].values
    c_oi, p_oi = d["Call OI"].values, d["Put OI"].values
    pain = [(np.maximum(s - k, 0) * c_oi).sum() + (np.maximum(k - s, 0) * p_oi).sum() for s in k]
    max_pain = fs(k[int(np.argmin(pain))])

    tot_c, tot_p = float(d["Call OI"].sum()), float(d["Put OI"].sum())
    pcr = tot_p / max(tot_c, 1)
    chg_c, chg_p = float(d["Call OI Chg"].sum()), float(d["Put OI Chg"].sum())

    # Bias scoring
    pts, reasons = 0, []
    if pcr >= 1.2:
        pts += 2; reasons.append(f"PCR {pcr:.2f} (>1.2) – Put writing zyada, bullish 🟢")
    elif pcr >= 1.0:
        pts += 1; reasons.append(f"PCR {pcr:.2f} – halka bullish")
    elif pcr <= 0.7:
        pts -= 2; reasons.append(f"PCR {pcr:.2f} (<0.7) – Call writing zyada, bearish 🔴")
    else:
        pts -= 1; reasons.append(f"PCR {pcr:.2f} – halka bearish")

    if chg_p > chg_c:
        pts += 1; reasons.append("Put OI mein addition, Call se zyada – support ban raha hai 🟢")
    else:
        pts -= 1; reasons.append("Call OI mein addition, Put se zyada – resistance ban raha hai 🔴")

    if spot < max_pain:
        pts += 1; reasons.append(f"Spot Max Pain ({max_pain}) se niche – upar kheench sakta hai 🟢")
    elif spot > max_pain:
        pts -= 1; reasons.append(f"Spot Max Pain ({max_pain}) se upar – niche kheench sakta hai 🔴")

    if supply and supply["primary"]["fresh"]:
        pts -= 1; reasons.append(f"Resistance {supply['primary']['strike']} par naya Call writing – mazboot 🔴")
    elif supply:
        pts += 1; reasons.append(f"Resistance {supply['primary']['strike']} par Call unwinding – kamzor 🟢")

    if demand and demand["primary"]["fresh"]:
        pts += 1; reasons.append(f"Support {demand['primary']['strike']} par naya Put writing – mazboot 🟢")
    elif demand:
        pts -= 1; reasons.append(f"Support {demand['primary']['strike']} par Put unwinding – kamzor 🔴")

    if supply and demand:
        d_sup = spot - demand["primary"]["strike"]
        d_res = supply["primary"]["strike"] - spot
        if d_sup < d_res:
            pts += 1; reasons.append("Spot support ke zyada paas hai 🟢")
        elif d_res < d_sup:
            pts -= 1; reasons.append("Spot resistance ke zyada paas hai 🔴")

    if pts >= 3:
        bias = "BULLISH 🟢"
    elif pts <= -3:
        bias = "BEARISH 🔴"
    else:
        bias = "SIDEWAYS / RANGE-BOUND 🟡"

    return {
        "supply": supply, "demand": demand, "zones": zones_flat, "zone_sets": zone_sets, "zone_width": w, "second": second_store,
        "liq": liq, "step": step,
        "max_pain": max_pain, "pcr": pcr,
        "chg_c": chg_c, "chg_p": chg_p, "points": pts, "bias": bias, "reasons": reasons,
    }


# ---------------- Colourful HTML table ----------------
SCROLL_JS = """
<script>
(function(){
  var box = document.querySelector('.wrap') || document.querySelector('.sc');
  function restore(){
    var s = {}; try { s = JSON.parse(window.name || '{}') || {}; } catch(e) { s = {}; }
    if (box) { box.scrollLeft = s.l || 0; box.scrollTop = s.bt || 0; }
    window.scrollTo(0, s.t || 0);
  }
  window.__restoreScroll = restore;
  restore();
  function save(){ try { var o = {}; try { o = JSON.parse(window.name || '{}') || {}; } catch(e) { o = {}; } o.l = box ? box.scrollLeft : 0; o.bt = box ? box.scrollTop : 0; o.t = window.pageYOffset || 0; window.name = JSON.stringify(o); } catch(e){} }
  if (box) box.addEventListener('scroll', save);
  window.addEventListener('scroll', save);
})();
</script>"""


def pct_s(x):
    """100 -> '100%', 75.1 -> '75.1%', 94.0 -> '94%' (poora number bina decimal ke)."""
    v = round(float(x), 1)
    return (str(int(v)) + "%") if v == int(v) else ("%.1f" % v + "%")


def iv_max_info(df, spot, n):
    """Option chain ke view (ATM +- n) mein sabse zyada IV wala strike (Call ya Put IV)."""
    d = df.sort_values("Strike").reset_index(drop=True)
    if "Call IV" not in d.columns or "Put IV" not in d.columns:
        return None
    ai = int((d["Strike"] - spot).abs().idxmin())
    view = d.iloc[max(ai - n, 0): ai + n + 1].copy()
    view["iv"] = view[["Call IV", "Put IV"]].astype(float).max(axis=1)
    if view["iv"].isna().all():
        return None
    r = view.loc[view["iv"].idxmax()]
    return {"strike": float(r["Strike"]), "iv": float(r["iv"])}


def build_rv(df, spot, n):
    """Realized volatility per strike (Call aur Put): pichle window (9:17 se ab tak) mein (high-low) / avg close ka %."""
    d = df.sort_values("Strike").reset_index(drop=True)
    ai = int((d["Strike"] - spot).abs().idxmin())
    view = d.iloc[max(ai - n, 0): ai + n + 1]
    keys = [k for k in list(view["Call Key"]) + list(view["Put Key"]) if isinstance(k, str) and k]
    if not keys:
        return {"error": "Option ke instrument key nahi mile."}
    hist, errs = {}, []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for key, h, e in ex.map(fetch_option_hist, keys):
            if h is not None:
                hist[key] = h
            else:
                errs.append(e)
    if not hist:
        return {"error": "Option ki history nahi aayi. Upstox ka jawab: " + (errs[0] if errs else "khali")}
    end_t = max(h["time"].max() for h in hist.values()).time()
    if end_t > dt_time(15, 30):
        end_t = dt_time(15, 30)
    rows = []
    for _, r in view.iterrows():
        for side, col in (("Call", "Call Key"), ("Put", "Put Key")):
            h = hist.get(r.get(col))
            if h is None or h.empty:
                continue
            tm = h["time"].dt.time
            w = h[(tm >= PRESS_START) & (tm <= end_t)]
            if w.empty or float(w["c"].mean()) <= 0:
                continue
            rv = (float(w["h"].max()) - float(w["l"].min())) / float(w["c"].mean()) * 100
            rows.append({"Strike": float(r["Strike"]), "Side": side, "RV %": round(rv, 2)})
    if not rows:
        return {"error": "Volatility nikalne ke liye data kam hai. Market khulne ke baad dobara dabayein."}
    res = pd.DataFrame(rows).sort_values("RV %", ascending=False).reset_index(drop=True)
    return {"table": res, "end_label": end_t.strftime("%H:%M")}


def volatility_zone_alert(rv_res, iv_info, breaches, step):
    """Combined alert: sabse zyada RV (ya IV) wala strike kisi TOOTE zone ke andar / paas ho to alert."""
    if not breaches:
        return None
    cands = []
    if rv_res and rv_res.get("table") is not None and len(rv_res["table"]):
        top = rv_res["table"].iloc[0]
        cands.append(("RV", float(top["Strike"]), float(top["RV %"])))
    if iv_info:
        cands.append(("IV", float(iv_info["strike"]), float(iv_info["iv"])))
    lines = []
    for b in breaches:
        for kind, k, v in cands:
            if float(b["low"]) - step <= k <= float(b["high"]) + step:
                lines.append(f"{kind} {fs(k)} ({v:.1f}%) · {b['short']} toota ({b['dir']})")
    if not lines:
        return None
    return "⚠️ Volatility + zone break: " + " | ".join(lines) + ". Ye sirf jaankari hai, trade ki salah nahi."


def fmt_vol(v):
    v = v or 0
    if v >= 10000000:
        return f"{v / 10000000:.2f}Cr"
    if v >= 100000:
        return f"{v / 100000:.1f}L"
    if v >= 1000:
        return f"{v / 1000:.1f}K"
    return f"{int(v)}"


HI_COLOR, MID_COLOR, CYAN_COLOR = "#7c3aed", "#c4b5fd", "#a5f3fc"      # 100% / 75% se upar / 60% se upar


def bar_cell(text, pct, bg, color, direction, top_cls):
    if pct >= 99.5:                                  # sabse zyada OI / Volume (badge '100%' ke barabar)
        return (
            f'<td style="background-color:{HI_COLOR};color:#fff">'
            f'<div class="v">{text}</div><div class="pb hi">{pct_s(pct)}</div></td>'
        )
    if pct >= 74.5:                                  # 75% se upar: 60% wala hi rang, sirf % chhota bold
        return (
            f'<td style="background-color:{CYAN_COLOR}">'
            f'<div class="v">{text}</div><div class="pb mid">{pct_s(pct)}</div></td>'
        )
    if pct >= 59.5:                                  # 60% se upar (Zone 2 ke layak)
        return (
            f'<td style="background-color:{CYAN_COLOR}">'
            f'<div class="v">{text}</div><div class="pb cy">{pct_s(pct)}</div></td>'
        )
    cls = "pb"
    grad = f"linear-gradient({direction}, {color} {pct_s(pct)}, transparent {pct_s(pct)})"
    return (
        f'<td style="background-color:{bg};background-image:{grad}">'
        f'<div class="v">{text}</div><div class="{cls}">{pct_s(pct)}</div></td>'
    )


def chg_cell(x, bg):
    color = "#16a34a" if x > 0 else "#dc2626" if x < 0 else "#6b7280"
    return f'<td style="background-color:{bg};color:{color};font-weight:600">{x / 1e5:.1f}</td>'


def plain_cell(text, bg, bold=False):
    w = "font-weight:700;" if bold else ""
    return f'<td style="background-color:{bg};{w}">{text}</td>'


def ltp_cell(ltp, bg, is_call, strike, spot):
    """LTP ke neeche do label: 1) INT = Intrinsic, 2) TV = Time value (LTP - INT).
    Call: INT = max(Spot - Strike, 0); Put: INT = max(Strike - Spot, 0). TV negative ho to '—'."""
    intrinsic = max(float(spot) - float(strike), 0.0) if is_call else max(float(strike) - float(spot), 0.0)
    tv = float(ltp) - intrinsic
    tv_txt = f"TV {tv:.1f}" if tv >= 0 else "TV —"
    return (f'<td style="background-color:{bg};font-weight:700;">{float(ltp):.2f}'
            f'<div style="font-size:9px;font-weight:600;color:#64748b">INT {intrinsic:.1f}</div>'
            f'<div style="font-size:9px;font-weight:600;color:#64748b">{tv_txt}</div></td>')


def shift_analysis(view, hist, cutoff):
    """cutoff se pehle (jaise 9:20 tak) aur uske baad ka fark: volume kahan shift hua, OI kahan jama hua.
    view: chain ki rows (Strike, Call Key, Put Key); hist: {instrument_key: DataFrame[time, vol, oi]}"""
    rows = []
    for _, r in view.iterrows():
        for side, kc in (("Call", "Call Key"), ("Put", "Put Key")):
            h = hist.get(r.get(kc))
            if h is None or h.empty:
                continue
            tm = h["time"].dt.time
            before, after = h[tm < cutoff], h[tm >= cutoff]
            oi_now = float(h["oi"].iloc[-1])
            if len(before):
                oi_b = float(before["oi"].iloc[-1])
            elif len(after):
                oi_b = float(after["oi"].iloc[0])
            else:
                continue
            rows.append({"side": side, "strike": fs(r["Strike"]), "vol_before": float(before["vol"].sum()),
                         "vol_after": float(after["vol"].sum()), "oi_before": oi_b, "oi_now": oi_now, "oi_chg": oi_now - oi_b})
    t = pd.DataFrame(rows)
    out = {}
    for side in ("Call", "Put"):
        x = t[t["side"] == side] if not t.empty else t
        if x is None or x.empty:
            out[side] = None
            continue
        vb = x.sort_values("vol_before", ascending=False).iloc[0]
        va = x.sort_values("vol_after", ascending=False).head(2)
        oa = x[x["oi_chg"] > 0].sort_values("oi_chg", ascending=False).head(2)
        oc = x.sort_values("oi_chg").iloc[0]
        va_l = [(fs(r["strike"]), float(r["vol_after"])) for _, r in va.iterrows() if r["vol_after"] > 0]
        oa_l = [(fs(r["strike"]), float(r["oi_chg"])) for _, r in oa.iterrows()]
        if len(va_l) > 1 and va_l[1][1] < 0.25 * va_l[0][1]:       # bahut chhota doosra naam mat dikhao
            va_l = va_l[:1]
        if len(oa_l) > 1 and oa_l[1][1] < 0.25 * oa_l[0][1]:
            oa_l = oa_l[:1]
        out[side] = {
            "vol_before_top": (fs(vb["strike"]), float(vb["vol_before"])) if vb["vol_before"] > 0 else None,
            "vol_after_top": va_l,
            "oi_add_top": oa_l,
            "oi_cut_top": (fs(oc["strike"]), float(oc["oi_chg"])) if oc["oi_chg"] < 0 else None,
        }
    return out


def shift_header_html(sh, side):
    d = (sh or {}).get(side)
    if not d:
        return '<div class="sh">Is side ka data nahi mila</div>'
    cut, lines = sh["cut"], []
    va = d["vol_after_top"]
    if va:
        new = ", ".join(f"<b>{s_}</b> (+{fmt_vol(v)})" for s_, v in va)
        vb = d["vol_before_top"]
        if vb and va[0][0] != vb[0]:
            lines.append(f"🔀 Volume shift: {cut} tak <b>{vb[0]}</b> par tha → ab <b>{va[0][0]}</b> par. Naya volume: {new}")
        else:
            lines.append(f"🔀 Volume wahi hai: {new}")
    else:
        lines.append("🔀 Volume: koi naya volume nahi")
    label = "🛑 Resistance ban raha hai" if side == "Call" else "🟢 Support ban raha hai"
    oa = d["oi_add_top"]
    lines.append(f"{label}: " + (", ".join(f"<b>{s_}</b> (OI +{v / 1e5:.1f}L)" for s_, v in oa) if oa else "koi nahi (OI nahi badha)"))
    if d["oi_cut_top"]:
        s_, v = d["oi_cut_top"]
        lines.append(f"↘️ OI sabse zyada ghata: <b>{s_}</b> ({v / 1e5:.1f}L)")
    return '<div class="sh">' + "<br>".join(lines) + "</div>"


def build_table_body(df, spot, n, ana=None, show_summary=True, inst_label="SPOT", shift=None, marks=None, vm_txt=None):
    marks = marks or {}
    mx = {k: max(float(df[k].max()), 1.0) for k in ["Call OI", "Put OI", "Call Vol", "Put Vol"]}
    d = df.sort_values("Strike").reset_index(drop=True)
    atm_idx = int((d["Strike"] - spot).abs().idxmin())
    atm_strike = d.loc[atm_idx, "Strike"]
    view = d.iloc[max(atm_idx - n, 0): atm_idx + n + 1]
    _mk_rows = d[d["Strike"].apply(lambda x: fs(x) in marks)]          # support/resistance strike hamesha dikhe
    view = pd.concat([view, _mk_rows]).drop_duplicates(subset=["Strike"]).sort_values("Strike").reset_index(drop=True)

    # zone tags per strike
    tags = {}
    if ana:
        for g in zone_groups(ana):
            short, both, drop = group_tag(g)
            has_oi = any(m["basis"] == "oi" for m in g["members"])
            cls = ("r" if has_oi else "rv") if g["side"] == "supply" else ("s" if has_oi else "sv")
            tags.setdefault(fs(g["level"]), []).append(
                f'<span class="chip {cls}">{"⭐ " if both else ""}{"💧 " if drop else ""}{short}</span>')
        for lq in ana.get("liq") or []:
            tags.setdefault(lq["strike"], []).append('<span class="chip l">💧 LIQUIDITY</span>')
        tags.setdefault(ana["max_pain"], []).append('<span class="chip m">🎯 MAX PAIN</span>')

    ITM, NORM = "#fff7cc", "#ffffff"
    ncols = 13 if show_summary else 11
    rows, spot_done = [], False
    spot_row = (
        f'<tr class="spotrow"><td colspan="{ncols}">▶▶ {inst_label} SPOT {spot:,.2f}' + (f' · {vm_txt}' if vm_txt else '') + ' (market yahan chal raha hai) ◀◀</td></tr>'
    )
    for _, r in view.iterrows():
        s = r["Strike"]
        if not spot_done and s > spot:
            rows.append(spot_row)
            spot_done = True
        cbg = ITM if s < spot else NORM
        pbg = ITM if s > spot else NORM
        is_atm = s == atm_strike
        mk = marks.get(fs(s))
        strike_bg = mk["bg"] if (mk and mk.get("bg")) else "#e5e7eb"          # support/resistance strike ka rang, baaki ek hi color
        if mk and mk.get("dual"):
            bg_css = "background-image:linear-gradient(to bottom,#b91c1c 50%,#15803d 50%)"
        else:
            bg_css = f"background-color:{strike_bg}"

        zone_td, pcr_td = "", ""
        if show_summary:
            pcr_s = r["Put OI"] / r["Call OI"] if r["Call OI"] else 0
            pcr_col = "#16a34a" if pcr_s > 1 else "#dc2626"
            sbg = "#faf5ff"
            zone_td = f'<td style="background-color:{sbg}">{"".join(tags.get(fs(s), [])) or "-"}</td>'
            pcr_td = f'<td style="background-color:{sbg};color:{pcr_col};font-weight:700">{pcr_s:.2f}</td>'

        rows.append(
            f'<tr class="{"atm" if is_atm else ""}">'
            # CALLS: IV | LTP | OI Chg | OI | Volume  (Volume strike ke paas)
            + plain_cell(_iv_txt(r["Call IV"]), cbg)
            + ltp_cell(r["Call LTP"], cbg, True, s, spot)
            + chg_cell(r["Call OI Chg"], cbg)
            + bar_cell(f'{r["Call OI"] / 1e5:.1f}', r["Call OI"] / mx["Call OI"] * 100, cbg, "rgba(248,113,113,.55)", "to left", "red")
            + bar_cell(fmt_vol(r["Call Vol"]), r["Call Vol"] / mx["Call Vol"] * 100, cbg, "rgba(251,146,60,.35)", "to left", "red")
            + (f'<td style="background:linear-gradient(to bottom,#b91c1c 0 48%,#15803d 52% 100%);font-weight:800;font-size:14px;color:#ffffff">'
               f'<div style="font-size:9px;font-weight:700;color:#fecaca">{mk["top"]}</div>{fs(s)}'
               f'<div style="font-size:9px;font-weight:700;color:#bbf7d0">{mk["bot"]}</div></td>' if (mk and mk.get("both")) else
               (f'<td style="{bg_css};font-weight:800;font-size:14px;color:#ffffff">' + f'<div style="font-size:9px;font-weight:700;color:#ffffff">{mk["dual"][0][0]}</div>{fs(s)}<div style="font-size:9px;font-weight:700;color:#ffffff">{mk["dual"][1][0]}</div></td>' if (mk and mk.get("dual")) else f'<td style="{bg_css};font-weight:800;font-size:14px{(";color:" + mk["numfg"]) if mk else ""}">{fs(s)}' + (f'<div style="font-size:9px;font-weight:700;color:{mk["fg"]}">{mk["txt"]}</div>' if mk else '') + '</td>'))
            # PUTS: Volume | OI | OI Chg | LTP | Zone | PCR | IV
            + bar_cell(fmt_vol(r["Put Vol"]), r["Put Vol"] / mx["Put Vol"] * 100, pbg, "rgba(96,165,250,.35)", "to right", "green")
            + bar_cell(f'{r["Put OI"] / 1e5:.1f}', r["Put OI"] / mx["Put OI"] * 100, pbg, "rgba(74,222,128,.6)", "to right", "green")
            + chg_cell(r["Put OI Chg"], pbg)
            + ltp_cell(r["Put LTP"], pbg, False, s, spot)
            + zone_td
            + pcr_td
            + plain_cell(_iv_txt(r["Put IV"]), pbg)
            + "</tr>"
        )
    if not spot_done:
        rows.append(spot_row)


    put_cols = 7 if show_summary else 5
    if shift:
        mid = f'<th class="shmid">🔀 {shift["cut"]} → {shift["asof"]}</th>'
        head1 = (
            f'<tr><th colspan="5" class="calls">CALLS{shift_header_html(shift, "Call")}</th>{mid}'
            f'<th colspan="{put_cols}" class="puts">PUTS{shift_header_html(shift, "Put")}</th></tr>'
        )
    else:
        head1 = (
            '<tr><th colspan="5" class="calls">CALLS</th><th></th>'
            f'<th colspan="{put_cols}" class="puts">PUTS</th></tr>'
        )
    head2 = "<tr><th>IV</th><th>LTP</th><th>OI Chg (L)</th><th>OI (L)</th><th>Volume</th><th>Strike</th>"
    head2 += "<th>Volume</th><th>OI (L)</th><th>OI Chg (L)</th><th>LTP</th>"
    if show_summary:
        head2 += "<th>Zone</th><th>PCR</th>"
    head2 += "<th>IV</th></tr>"
    minw = 1150 if show_summary else 950

    return f'<table style="min-width:{minw}px">{head1}{head2}{"".join(rows)}</table>'


# ---------------- Charts with Supply / Demand zones (pure SVG, no extra library) ----------------
def _dark():
    return bool(st.session_state.get("theme_dark", False))


def _wc():
    return "dk" if _dark() else ""


DARK_CSS = """<style>
.dk{--fg:#e5e7eb;}
.dk .top, .dk .bar{background:#0e1117;}
body:has(.dk){background:#0e1117;}
#oc.dk{background:#0e1117;}
.dk td[style*="background-color:#c4b5fd"]{background-color:#4c1d95 !important;color:#ede9fe !important;}
.dk td[style*="background-color:#c4b5fd"] .v{color:#ede9fe;}
.dk td{color:#e5e7eb;border-color:#30363d;}
.dk td[style*="background-color:#ffffff"]{background-color:#161b22 !important;}
.dk td[style*="background-color:#fff7cc"]{background-color:#3d3a1c !important;}
.dk td[style*="background-color:#e5e7eb"]{background-color:#2d333b !important;}
.dk td[style*="background-color:#faf5ff"]{background-color:#1f1a2e !important;}
.dk td[style*="background-color:#a5f3fc"]{background-color:#164e63 !important;}
.dk th{background:#161b22;color:#c9d1d9;border-color:#30363d;}
.dk th.calls{background:#3b1d1d;color:#fca5a5;}
.dk th.puts{background:#14291f;color:#86efac;}
.dk th.sum{background:#2a1f3d;color:#d8b4fe;}
.dk .pb{background:#0d1117;color:#86efac;border-color:#2ea043;}
.dk .pb.cy{background:#0e2a33;color:#67e8f9;border-color:#0891b2;}
.dk .pb.mid{background:#2e1065;color:#ddd6fe;border-color:#7c3aed;}
.dk .pb.hi{background:#0d1117;color:#c4b5fd;border-color:#7c3aed;}
.dk .sh{color:#e5e7eb;}
.dk #info{color:#c9d1d9;}
.dk #wait{color:#8b949e;}
.dk .btns button.g{background:#334155;}
</style>"""

TABLE_CSS = """
    <meta charset="utf-8"><style>
      body{margin:0;font-family:Arial,Helvetica,sans-serif;}
      .wrap{overflow-x:auto;touch-action:pan-x pan-y;}
      .zb{background:#2563eb;color:#fff;border:none;border-radius:8px;padding:7px 11px;font-size:13px;font-weight:700;cursor:pointer;margin-right:6px;}
      .bar{display:flex;justify-content:flex-end;padding:4px 2px 6px 2px;position:sticky;top:0;z-index:20;background:#fff;}
      #fsbtn{background:#2563eb;color:#fff;border:none;border-radius:8px;padding:7px 14px;font-size:13px;font-weight:700;cursor:pointer;}
      #fsbtn:active{background:#1d4ed8;}
      #oc{background:#fff;}
      #oc:fullscreen{overflow:hidden;padding:6px;}
      #oc:fullscreen .wrap{height:calc(100vh - 60px);overflow:auto;}
      #oc:fullscreen table{width:100%;}
      #oc:-webkit-full-screen{overflow:hidden;padding:6px;}
      #oc:-webkit-full-screen .wrap{height:calc(100vh - 52px);overflow:auto;}
      table{width:100%;border-collapse:collapse;font-size:13px;text-align:center;}
      th{position:sticky;top:0;z-index:2;padding:8px 4px;color:#374151;background:#f9fafb;border-bottom:2px solid #e5e7eb;white-space:nowrap;}
      th.calls{background:#fee2e2;color:#b91c1c;letter-spacing:1px;}
      th.puts{background:#dcfce7;color:#15803d;letter-spacing:1px;}
      th.sum{background:#f3e8ff;color:#7e22ce;letter-spacing:1px;}
      td{padding:5px 6px;border-bottom:1px solid #eef0f3;white-space:nowrap;color:#111;}
      .v{font-size:13px;font-weight:600;}
      .pb{display:inline-block;font-size:9px;color:#15803d;border:1px solid #86efac;border-radius:4px;padding:0 3px;margin-top:2px;background:#f0fdf4;}
      .pb.top-red{color:#b91c1c;border-color:#f87171;background:#fef2f2;font-weight:700;}
      .pb.top-green{color:#166534;border-color:#22c55e;background:#dcfce7;font-weight:700;}
      .pb.hi{color:#6d28d9;border-color:#c4b5fd;background:#fff;font-weight:800;}
      .pb.mid{color:#0f172a;border-color:#0e7490;background:#ffffff;font-weight:900;}
      .pb.cy{color:#155e75;border-color:#22d3ee;background:#ecfeff;font-weight:700;}
      .sh{white-space:normal;font-size:11px;font-weight:600;letter-spacing:0;text-align:left;padding:5px 8px 3px 8px;line-height:1.55;color:#111;position:sticky;left:4px;width:min(360px,calc(100vw - 24px));box-sizing:border-box;}
      th.shmid{white-space:normal;font-size:10px;color:#6b7280;font-weight:700;}

      tr.spotrow td{background:linear-gradient(90deg,#f97316,#ef4444,#f97316);color:#fff;font-weight:800;
                    padding:4px;font-size:12px;letter-spacing:1px;border:none;}
      .chip{display:inline-block;font-size:10px;font-weight:700;border-radius:10px;padding:1px 7px;margin:1px;}
      .chip.r{background:#ef4444;color:#fff;} .chip.s{background:#22c55e;color:#fff;} .chip.m{background:#8b5cf6;color:#fff;} .chip.l{background:#0891b2;color:#fff;} .chip.rv{background:#9f1239;color:#fff;} .chip.sv{background:#4d7c0f;color:#fff;}
    </style>"""

TABLE_UPDATE_JS = """
<script>
window.__cid = 'table';
var lastV = null, wrapEl = document.getElementById('wrap');
var zs = 1, fitMode = false, pinch = null, pts = {};
function natW(t){ t.style.zoom = 1; return t.scrollWidth; }
function applyZoom(){
  var t = wrapEl.querySelector('table'); if (!t) return;
  if (fitMode) { var nw = natW(t), av = wrapEl.clientWidth - 4; zs = nw > av && nw > 0 ? Math.max(0.35, av / nw) : 1; }
  zs = Math.min(3, Math.max(0.35, zs));
  t.style.zoom = zs;
  var fsNow = document.fullscreenElement || document.webkitFullscreenElement;
  t.style.height = fsNow ? Math.floor(wrapEl.clientHeight / zs) + 'px' : '';
  var lab = document.getElementById('tfit'); if (lab) lab.textContent = fitMode ? '⤢ Fit ✓' : '⤢ Fit';
}
document.getElementById('tzo').addEventListener('click', function(){ fitMode = false; zs = Math.max(0.35, zs - 0.15); applyZoom(); });
document.getElementById('tzi').addEventListener('click', function(){ fitMode = false; zs = Math.min(3, zs + 0.15); applyZoom(); });
document.getElementById('tfit').addEventListener('click', function(){ fitMode = !fitMode; applyZoom(); });
wrapEl.addEventListener('pointerdown', function(e){ pts[e.pointerId] = [e.clientX, e.clientY]; if (Object.keys(pts).length === 2) { var k = Object.keys(pts).map(Number); pinch = {d: dist(k), z: zs}; } });
wrapEl.addEventListener('pointermove', function(e){
  if (!pts[e.pointerId]) return; pts[e.pointerId] = [e.clientX, e.clientY];
  if (pinch && Object.keys(pts).length >= 2) { var k = Object.keys(pts).map(Number), d = dist(k); if (pinch.d > 0) { fitMode = false; zs = Math.min(3, Math.max(0.35, pinch.z * d / pinch.d)); applyZoom(); } }
});
function endPtr(e){ delete pts[e.pointerId]; if (Object.keys(pts).length < 2) pinch = null; }
wrapEl.addEventListener('pointerup', endPtr); wrapEl.addEventListener('pointercancel', endPtr);
function dist(k){ var a = pts[k[0]], b = pts[k[1]]; return Math.hypot(a[0] - b[0], a[1] - b[1]); }
window.addEventListener('resize', function(){ if (fitMode) applyZoom(); });
function onTableFS(){ fitMode = !!(document.fullscreenElement || document.webkitFullscreenElement); setTimeout(applyZoom, 120); }
document.addEventListener('fullscreenchange', onTableFS);
document.addEventListener('webkitfullscreenchange', onTableFS);
window.__update = function(p){
  if (p.v === lastV) return;
  var first = (lastV === null); lastV = p.v;
  wrapEl.innerHTML = p.html;
  applyZoom();
  if (first && window.__restoreScroll) window.__restoreScroll();
};
</script>"""


def table_shell_html():
    """Ye hissa kabhi badalta nahi, isliye refresh par iframe reload nahi hota (Full Screen bana rehta hai)."""
    return (
        DARK_CSS + TABLE_CSS
        + '<div id="oc" class="' + _wc() + '"><div class="bar"><button class="zb" id="tzo">－</button><button class="zb" id="tzi">＋</button><button class="zb" id="tfit">⤢ Fit</button><button id="fsbtn" onclick="toggleFS()">⛶ Full Screen</button></div>'
        + '<div class="wrap" id="wrap"><div style="padding:14px;color:#6b7280;font-size:13px;font-family:Arial">Option chain load ho raha hai…</div></div></div>'
        + FS_JS + SCROLL_JS + TABLE_UPDATE_JS
    )


PUSH_TEMPLATE = """
<script>
(function(){
  var CID = "__CID__", PAYLOAD = __PAYLOAD__;
  function findShell(){
    try {
      var fr = window.parent.document.querySelectorAll('iframe');
      for (var i = 0; i < fr.length; i++) {
        try { var w = fr[i].contentWindow; if (w && w.__cid === CID && w.__update) return w; } catch(e) {}
      }
    } catch(e) {}
    return null;
  }
  function tick(){ var w = findShell(); if (w) { try { w.__update(PAYLOAD); } catch(e) {} } }
  tick(); setInterval(tick, 600);
})();
</script>"""


def push_html(cid, payload):
    """Naya data chhupe hue (height=0) iframe se dikhne wale chart/table mein JS se daal diya jata hai."""
    payload = dict(payload)
    raw = json.dumps(payload, sort_keys=True, default=float)
    payload["v"] = hashlib.md5(raw.encode()).hexdigest()
    body = json.dumps(payload, default=float).replace("</", "<\\/")
    return PUSH_TEMPLATE.replace("__CID__", cid).replace("__PAYLOAD__", body)



def _strength_txt(score):
    return "Strong" if score >= 70 else "Medium" if score >= 45 else "Weak"


def _pfmt(v):
    return f"{v:,.0f}" if abs(v) >= 1000 else f"{v:,.2f}"


def zone_groups(ana, show_vol=True, show_oi=True):
    """Volume zone aur OI zone agar ek hi jagah (overlap) hon to ek group mein (⭐ dono mile)."""
    groups = []
    for z in (ana or {}).get("zones", []):
        if (z["basis"] == "vol" and not show_vol) or (z["basis"] == "oi" and not show_oi):
            continue
        for g in groups:
            if g["side"] == z["side"] and abs(g["level"] - float(z["strike"])) < z["width"]:
                g["members"].append(z)
                break
        else:
            groups.append({"side": z["side"], "level": float(z["strike"]), "low": z["low"], "high": z["high"],
                           "width": z["width"], "members": [z]})
    return groups


def zone_name(g, tag=True):
    """Chart label: SUPPLY 1 / SUPPLY 2 / DEMAND 1 / DEMAND 2, aur (tag=True ho to) basis (Vol / OI)."""
    side = "SUPPLY" if g["side"] == "supply" else "DEMAND"
    num = str(min(m["rank"] for m in g["members"]))
    if not tag:
        return f"{side} {num}"
    bases = {m["basis"] for m in g["members"]}
    tg = " (Vol+OI)" if len(bases) > 1 else (" (Vol)" if "vol" in bases else " (OI)")
    return f"{side} {num}{tg}"


def group_tag(g):
    parts = [("V" if m["basis"] == "vol" else "O") + str(m["rank"])
             for m in sorted(g["members"], key=lambda m: (m["basis"] != "vol", m["rank"]))]
    short = ("SUP " if g["side"] == "supply" else "DEM ") + "+".join(parts)
    both = len({m["basis"] for m in g["members"]}) > 1
    drop = any(m["rank"] == 2 for m in g["members"])
    return short, both, drop


BREACH_CANDLES = 2   # itni lagatar candles zone ke bahar band hon tabhi "toota"


def breach_check(c, ana, need=BREACH_CANDLES):
    """Har zone ke liye: kya spot zone ke bahar lagataar `need` candle close ho chuka hai?
    Supply tuta = close zone se UPAR. Demand tuta = close zone se NEECHE.
    Chart ke candles (time, close) pe chalta hai. Return: list of dicts (sirf toote zone)."""
    if c is None or len(c) < need or not ana:
        return []
    closes = [float(x) for x in c["close"].tolist()]
    last = closes[-need:]
    out = []
    for z in zone_groups(ana):
        lo, hi = float(z["low"]), float(z["high"])
        if z["side"] == "supply" and all(x > hi for x in last):
            out.append({"side": "supply", "low": lo, "high": hi, "close": last[-1], "n": need,
                        "short": group_tag(z)[0], "dir": "upar"})
        elif z["side"] == "demand" and all(x < lo for x in last):
            out.append({"side": "demand", "low": lo, "high": hi, "close": last[-1], "n": need,
                        "short": group_tag(z)[0], "dir": "neeche"})
    return out


def breach_banner_html(br):
    """Market Bias patti ke neeche lal/hara alert."""
    if not br:
        return ""
    lines = []
    for b in br:
        col = "#fee2e2" if b["side"] == "supply" else "#dcfce7"
        bd = "#dc2626" if b["side"] == "supply" else "#16a34a"
        lines.append(
            f'<div style="background:{col};border-left:6px solid {bd};padding:8px 10px;border-radius:6px;margin:4px 0;color:#111">'
            f'⚠️ <b>{b["short"]} TOOTA</b>: {b["n"]} candle lagatar {b["low"]:,.0f}-{b["high"]:,.0f} zone ke '
            f'{b["dir"]} band hui (last close {b["close"]:,.2f}). '
            f'{"Resistance" if b["side"] == "supply" else "Support"} kamzor, dam dikh raha hai.</div>')
    return "".join(lines)


def option_weak_hint(sh_or_none, side, zone_low, zone_high):
    """Ye sirf sanket hai: zone ki strike ka OI ghat raha ho (unwinding) to 'kamzor' hint."""
    return None


def zone_items(ana, show_vol=True, show_oi=True, breached=None, legacy=False):
    items = []
    for g in zone_groups(ana, show_vol, show_oi):
        short, both, drop = group_tag(g)
        has_oi = any(m["basis"] == "oi" for m in g["members"])
        sup = g["side"] == "supply"
        color = ("#ef4444" if has_oi else "#9f1239") if sup else ("#16a34a" if has_oi else "#4d7c0f")
        alpha = 0.26 if both else 0.18 if any(m["rank"] == 1 for m in g["members"]) else 0.10
        broke = bool(breached) and any(abs(float(b["low"]) - float(g["low"])) < 1e-6 and b["side"] == g["side"] for b in breached)
        pct_parts = []
        for m in sorted(g["members"], key=lambda m: (m["basis"] != "vol", m["rank"])):
            tg = "Vol" if m["basis"] == "vol" else "OI"
            pct_parts.append(f"{tg} {pct_s(m['pct'])}")
            sec = (ana or {}).get("second", {}).get((m["basis"], g["side"]))
            if sec and sec["strike"] != fs(float(m["strike"])):
                pct_parts.append(f"2nd {tg} {sec['strike']:g} {pct_s(sec['pct'])}")
        pct_txt = " · ".join(pct_parts)
        nm = zone_name(g, tag=False)
        prim = next((m for m in g["members"] if m["basis"] == "vol"), None) or min(g["members"], key=lambda m: m["rank"])
        sec = (ana or {}).get("second", {}).get((prim["basis"], g["side"]))
        prim_pct = f"{pct_s(prim['pct'])}"
        sec_part = ""
        if sec and sec["strike"] != fs(float(prim["strike"])):
            sec_part = f" · 2nd {sec['strike']:g} {pct_s(sec['pct'])}"
        pct_txt = prim_pct + sec_part
        flags = f"{'✖ ' if broke else ''}{'⭐ ' if both else ''}{'💧 ' if drop else ''}"
        label = flags + f"{nm} · {pct_txt}"
        main_label = flags + f"{nm} · {prim_pct}"
        sec_col = "#15803d" if g["side"] == "demand" else "#b91c1c"   # Support (demand) hara, Resistance (supply) laal
        if broke:
            color, alpha = "#6b7280", 0.06                       # toota zone: dhundhla slate rang
        pa = (ana or {}).get("pressure_alert")
        if pa is not None and g["side"] == "demand" and abs(float(g["level"]) - float(pa)) < 1e-6:
            label = "⚠️ BEARISH PRESSURE · " + label
            main_label = "⚠️ BEARISH PRESSURE · " + main_label
        sec_k = float(sec["strike"]) if sec_part else None
        sec_t = (f"2nd {sec['strike']:g} {pct_s(sec['pct'])}") if sec_part else ""
        items.append({"label": label, "main": main_label, "sec": "", "seccol": sec_col, "short": short,
                      "secK": sec_k, "secT": sec_t,
                      "shortp": f"{short} · {prim_pct}{sec_part}",
                      "lo": float(g["low"]), "hi": float(g["high"]), "color": color,
                      "alpha": alpha, "level": fs(g["level"]), "key": g["side"], "single": True, "broke": broke})
    return items


def level_lines(ana, spot):
    out = [(f"SPOT {_pfmt(spot)}", float(spot), "#f97316")]
    if ana and not ana.get("hist"):
        out.append((f"MP {ana['max_pain']}", float(ana["max_pain"]), "#8b5cf6"))
        taken = {round(v) for _, v, _ in out}
        n_liq = 0
        for lq in ana.get("liq") or []:
            if lq["strike"] not in taken and n_liq < 2:
                out.append((f"LIQ {lq['strike']}", float(lq["strike"]), "#0891b2"))
                n_liq += 1
    return out


def _nice_step(rng, target=6):
    raw = max(rng, 1e-9) / target
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


def _spread(ys, gap=15):
    order = sorted(range(len(ys)), key=lambda i: ys[i])
    res, prev = list(ys), -1e9
    for i in order:
        res[i] = max(res[i], prev + gap)
        prev = res[i]
    return res


def _legend():
    chips = (
        ("SUPPLY ZONE (Resistance)", "#ef4444"), ("DEMAND ZONE (Support)", "#16a34a"),
        ("SPOT", "#f97316"), ("MP = MAX PAIN", "#8b5cf6"), ("LIQ = LIQUIDITY", "#0891b2"),
    )
    return "".join(
        f'<span style="display:inline-block;margin:0 10px 4px 0;font-size:12px;font-weight:700;color:var(--fg,#111)">'
        f'<span style="display:inline-block;width:11px;height:11px;border-radius:3px;background:{c};margin-right:5px;vertical-align:-1px"></span>{t}</span>'
        for t, c in chips
    )


FS_JS = """
<script>
  var oc = document.getElementById('oc'), btn = document.getElementById('fsbtn');
  function isFS(){ return document.fullscreenElement || document.webkitFullscreenElement; }
  function toggleFS(){
    try {
      if (!isFS()) {
        var f = oc.requestFullscreen || oc.webkitRequestFullscreen;
        var p = f.call(oc);
        if (p && p.catch) p.catch(function(){ alert('Is browser mein Full Screen support nahi. Sidebar ka Focus mode use karein.'); });
      } else {
        (document.exitFullscreen || document.webkitExitFullscreen).call(document);
      }
    } catch(e) { alert('Is browser mein Full Screen support nahi. Sidebar ka Focus mode use karein.'); }
  }
  function upd(){ btn.textContent = isFS() ? '✖ Exit Full Screen' : '⛶ Full Screen'; }
  document.addEventListener('fullscreenchange', upd);
  document.addEventListener('webkitfullscreenchange', upd);
</script>"""


ZOOM_JS = r"""
<script>
(function(){
var CFG = __CFG__;
var svg = document.getElementById('svg'), stage = document.getElementById('stage'), info = document.getElementById('info');
var W = CFG.W, H = CFG.H, L = CFG.L, T = CFG.T, B = CFG.B, pw = CFG.pw, ph = CFG.ph;
var GRID = CFG.dark ? '#263241' : '#eef0f3', HALO = CFG.dark ? '#0e1117' : '#fff';
var D = null, n = 0, sel = -1, touched = false, lastV = null, HINT = info.textContent;
var DEF = {a: 0, b: 1, lo: 0, hi: 1}, view = {a: 0, b: 1, lo: 0, hi: 1};
function copyDef(){ return {a: DEF.a, b: DEF.b, lo: DEF.lo, hi: DEF.hi}; }
function setData(nd){
  var oldN = n, same = (D !== null) && D.sig === nd.sig;
  D = nd; n = D.n;
  DEF = {a: D.defA, b: D.defB, lo: D.lo, hi: D.hi};
  if (!same) {
    view = copyDef(); touched = false; sel = -1;
    try {
      var o0 = JSON.parse(window.name || '{}') || {}, z0 = o0.z;
      if (z0 && z0.sig === D.sig) { view.a = n - z0.ra; view.b = n - z0.rb; view.lo = z0.lo; view.hi = z0.hi; touched = true; }
    } catch(e) {}
    if (!(view.b - view.a > 0.5)) { view = copyDef(); touched = false; }
  } else if (touched) {
    var sh = n - oldN; view.a += sh; view.b += sh;
  } else { view = copyDef(); }
  clampView(); draw();
}

function persist(clear){
  touched = !clear;
  try {
    var o = {}; try { o = JSON.parse(window.name || '{}') || {}; } catch(e) { o = {}; }
    if (clear) { delete o.z; } else { o.z = {sig: D.sig, ra: n - view.a, rb: n - view.b, lo: view.lo, hi: view.hi}; }
    window.name = JSON.stringify(o);
  } catch(e) {}
}
function clampView(){
  var minSpan = Math.min(5, n), maxSpan = Math.max(n * 3, 10), span = view.b - view.a, c;
  if (span < minSpan) { c = (view.a + view.b) / 2; view.a = c - minSpan / 2; view.b = c + minSpan / 2; }
  if (span > maxSpan) { c = (view.a + view.b) / 2; view.a = c - maxSpan / 2; view.b = c + maxSpan / 2; }
  c = (view.a + view.b) / 2;
  if (c < 0) { view.a -= c; view.b -= c; } else if (c > n) { view.a -= c - n; view.b -= c - n; }
  var minY = (DEF.hi - DEF.lo) * 0.02;
  if (view.hi - view.lo < minY) { var m = (view.hi + view.lo) / 2; view.lo = m - minY / 2; view.hi = m + minY / 2; }
  if (CFG.anchorBottom) view.lo = 0;
}
function zoomX(f, cx){ view.a = cx - (cx - view.a) * f; view.b = cx + (view.b - cx) * f; }
function zoomY(f, cy){ if (CFG.anchorBottom) cy = 0; view.lo = cy - (cy - view.lo) * f; view.hi = cy + (view.hi - cy) * f; }
function rect(){ return stage.getBoundingClientRect(); }
function idxAt(vx){ return view.a + (vx - L) / pw * (view.b - view.a); }
function valAt(vy){ return view.hi - (vy - T) / ph * (view.hi - view.lo); }
function niceStep(rng, target){
  var raw = Math.max(rng, 1e-9) / target, mag = Math.pow(10, Math.floor(Math.log10(raw))), ms = [1, 2, 2.5, 5, 10];
  for (var i = 0; i < ms.length; i++) { if (raw <= ms[i] * mag) return ms[i] * mag; }
  return 10 * mag;
}
function pfmt(v){ return Math.abs(v) >= 1000 ? Math.round(v).toLocaleString('en-US') : v.toFixed(2); }
function spread(ys, gap){
  var idx = ys.map(function(_, i){ return i; }).sort(function(p, q){ return ys[p] - ys[q]; }), res = ys.slice(), prev = -1e9;
  idx.forEach(function(i){ res[i] = Math.max(res[i], prev + gap); prev = res[i]; });
  return res;
}
function f1(x){ return x.toFixed(1); }

var obOnly = false;
var MODE = 'price', TF = 5, DS = {price: {}, vol: {}, oi: null};
var smcOn = false;
var labOn = false;
function getDS(m){ var k = modeKey(m); if (k === 'oi') return DS.oi; var bucket = (k === 'vol') ? DS.vol : DS.price; return (bucket && bucket[TF]) || null; }
function markTFBtns(){ [1,5,15,60,1440].forEach(function(t){ var e = document.getElementById('t' + t); if (e) e.style.outline = (t === TF) ? '2px solid #facc15' : 'none'; }); }
function modeKey(m){ return (m === 'vol') ? 'vol' : (m === 'oi') ? 'oi' : 'price'; }
function setOverlaysVisible(v){ ['zp','za','zt'].forEach(function(id){ var e = document.getElementById(id); if (e) e.style.display = v ? '' : 'none'; }); }
function markModeBtns(){
  var act = {price:'mP', oi:'mO', vol:'mV', ob:'mB'}[MODE];
  ['mP','mO','mV','mB'].forEach(function(id){ var e = document.getElementById(id); if (e) e.style.outline = (id === act) ? '2px solid #facc15' : 'none'; });
}
function switchMode(m){
  var nd = getDS(m);
  if (!nd) return;
  MODE = m; obOnly = (m === 'ob');
  D = nd; n = D.n;
  DEF = {a: D.defA, b: D.defB, lo: D.lo, hi: D.hi};
  view = copyDef(); touched = false; sel = -1;
  setOverlaysVisible(m !== 'oi');
  markModeBtns();
  draw();
}
function switchTF(t){
  TF = t;
  var nd = getDS(MODE);
  if (!nd) return;
  D = nd; n = D.n;
  DEF = {a: D.defA, b: D.defB, lo: D.lo, hi: D.hi};
  view = copyDef(); touched = false; sel = -1;
  markTFBtns();
  draw();
}
function obFit(){
  var zz = obOnly ? D.zones.filter(function(z){ return z.short === 'OB'; }) : D.zones;
  var lo = Infinity, hi = -Infinity;
  D.c.forEach(function(c){ if (c[2] < lo) lo = c[2]; if (c[1] > hi) hi = c[1]; });
  zz.forEach(function(z){ if (z.lo < lo) lo = z.lo; if (z.hi > hi) hi = z.hi; });
  if (!isFinite(lo) || !isFinite(hi)) return null;
  var pad = (hi - lo) * 0.04 || 5;
  return [lo - pad, hi + pad];
}
function drawPrice(){
  var ZS0 = obOnly ? D.zones.filter(function(z){ return z.short === 'OB'; }) : D.zones;
  var ZS = smcOn ? ZS0 : ZS0.filter(function(z){ return ['FVG','PREM','DISC'].indexOf(z.short) < 0; });
  var LN = smcOn ? D.lines : D.lines.filter(function(l){ return l.dash !== '4 3'; });
  var a = view.a, b = view.b, lo = view.lo, hi = view.hi, span = b - a, slot = pw / span, rng = hi - lo;
  function Y(v){ return T + (hi - v) / rng * ph; }
  function X(i){ return L + (i - a + 0.5) * slot; }
  var out = ['<defs><clipPath id="cp"><rect x="' + L + '" y="' + T + '" width="' + pw + '" height="' + ph + '"/></clipPath></defs>'];
  var cl = [], ticks = [], step = niceStep(rng, 6), v = Math.ceil(lo / step) * step, g = 0;
  while (v <= hi && g++ < 80) {
    var y = Y(v);
    cl.push('<line x1="' + L + '" x2="' + (L + pw) + '" y1="' + f1(y) + '" y2="' + f1(y) + '" stroke="' + GRID + '"/>');
    ticks.push('<text x="' + (L + pw + 4) + '" y="' + f1(y + 3) + '" font-size="10" fill="#9ca3af">' + pfmt(v) + '</text>');
    v += step;
  }
  var zl = [];
  ZS.forEach(function(z){
    var y1 = Y(z.hi), y2 = Y(z.lo);
    cl.push('<rect x="' + L + '" y="' + f1(y1) + '" width="' + pw + '" height="' + f1(Math.max(y2 - y1, 2)) + '" fill="' + z.color + '" opacity="' + z.alpha + '"/>');
    [y1, y2].forEach(function(yy){ cl.push('<line x1="' + L + '" x2="' + (L + pw) + '" y1="' + f1(yy) + '" y2="' + f1(yy) + '" stroke="' + z.color + '" stroke-width="1" opacity="0.55"/>'); });
    zl.push([z, y1, y2]);
  });
  var i0 = Math.max(0, Math.floor(a) - 1), i1 = Math.min(n - 1, Math.ceil(b) + 1), cw = Math.min(Math.max(1.2, slot * 0.7), 40);
  for (var i = i0; i <= i1; i++) {
    var c = D.c[i], col = c[3] >= c[0] ? '#16a34a' : '#dc2626', x = X(i), yo = Y(c[0]), yc = Y(c[3]);
    cl.push('<g><title>' + D.tips[i] + '</title><line x1="' + f1(x) + '" x2="' + f1(x) + '" y1="' + f1(Y(c[1])) + '" y2="' + f1(Y(c[2])) + '" stroke="' + col + '"/>' +
            '<rect x="' + f1(x - cw / 2) + '" y="' + f1(Math.min(yo, yc)) + '" width="' + f1(cw) + '" height="' + f1(Math.max(Math.abs(yo - yc), 1)) + '" fill="' + col + '"/></g>');
  }
  if (sel >= 0 && sel < n) { var xs = X(sel); cl.push('<line x1="' + f1(xs) + '" x2="' + f1(xs) + '" y1="' + T + '" y2="' + (T + ph) + '" stroke="#2563eb" stroke-width="1" stroke-dasharray="3 3"/>'); }
  var zv = zl.filter(function(q){ return !(q[2] < T || q[1] > T + ph); });
  var zy = zv.map(function(q){ var t = (q[2] - q[1]) >= 20 ? (q[0].side === 'demand' ? q[2] - 6 : q[1] + 13) : q[1] - 4; return Math.min(Math.max(t, T + 12), T + ph - 4); });
  zy = spread(zy, 13);
  zv.forEach(function(q, k){
    cl.push('<text x="' + (L + 6) + '" y="' + f1(Math.min(zy[k], T + ph - 3)) + '" font-size="11" font-weight="700" fill="' + (q[0].side === 'supply' ? '#b91c1c' : '#15803d') + '" stroke="' + HALO + '" stroke-width="3" paint-order="stroke">' + q[0].main + (q[0].sec ? '<tspan fill="' + q[0].seccol + '">' + q[0].sec + '</tspan>' : '') + '</text>');
  });
  var secSeen = {};
  ZS.forEach(function(z){
    if (z.secK === null || z.secK === undefined || !z.secT) return;
    var key = z.secK + '|' + z.seccol; if (secSeen[key]) return; secSeen[key] = 1;
    var ys = Y(z.secK);
    if (ys < T || ys > T + ph) return;
    cl.push('<text x="' + (L + 6) + '" y="' + f1(ys + 12) + '" font-size="10" font-weight="700" fill="' + z.seccol + '" stroke="' + HALO + '" stroke-width="3" paint-order="stroke">' + z.secT + '</text>');
  });
  LN.forEach(function(l){
    var y = Y(l.val);
    cl.push('<line x1="' + L + '" x2="' + (L + pw) + '" y1="' + f1(y) + '" y2="' + f1(y) + '" stroke="' + l.color + '" stroke-width="1.4" stroke-dasharray="' + l.dash + '"/>');
  });
  out.push('<g clip-path="url(#cp)">' + cl.join('') + '</g>', ticks.join(''));
  var tg = LN.map(function(l){
    var y = Y(l.val), arrow = '';
    if (y < T) { y = T + 9; arrow = '\u25B2 '; } else if (y > T + ph) { y = T + ph - 9; arrow = '\u25BC '; }
    return {l: l, y: y, t: arrow + l.lab};
  });
  ZS.forEach(function(z){                       // screen se bahar ke zone ka tag (▲ / ▼)
    var yc = Y((z.lo + z.hi) / 2);
    if (yc < T || yc > T + ph) tg.push({l: {color: z.color}, y: yc < T ? T + 9 : T + ph - 9, t: (yc < T ? '\u25B2 ' : '\u25BC ') + z.short});
  });
  var ys = spread(tg.map(function(o){ return o.y; }), 15);
  tg.forEach(function(o, k){
    out.push('<rect x="' + (L + pw + 2) + '" y="' + f1(ys[k] - 8) + '" width="' + (CFG.R - 4) + '" height="15" rx="4" fill="' + o.l.color + '"/>' +
             '<text x="' + (L + pw + 2 + (CFG.R - 4) / 2) + '" y="' + f1(ys[k] + 3) + '" font-size="' + (o.t.length > 11 ? 8.3 : 9.5) + '" font-weight="700" fill="#fff" text-anchor="middle">' + o.t + '</text>');
  });
  for (var k = 0; k < 5; k++) {
    var idx = Math.round(a + span * k / 4 - 0.5);
    if (idx < 0 || idx > n - 1) continue;
    var xx = Math.min(Math.max(X(idx), L + 22), L + pw - 22);
    out.push('<text x="' + f1(xx) + '" y="' + (H - 8) + '" font-size="10" fill="#6b7280" text-anchor="middle">' + D.labels[idx] + '</text>');
  }
  svg.innerHTML = out.join('');
}

function drawOI(){
  var a = view.a, b = view.b, hi = view.hi, span = b - a, slot = pw / span;
  function Y(v){ return T + (1 - v / hi) * ph; }
  function X(i){ return L + (i - a + 0.5) * slot; }
  function XS(s){ return X((s - D.s0) / D.sstep); }
  var out = ['<defs><clipPath id="cp"><rect x="' + L + '" y="' + T + '" width="' + pw + '" height="' + ph + '"/></clipPath></defs>'];
  var cl = [], step = niceStep(hi / 1e5, 5) * 1e5, t = 0, g = 0;
  while (t <= hi && g++ < 80) {
    var y = Y(t);
    cl.push('<line x1="' + L + '" x2="' + (L + pw) + '" y1="' + f1(y) + '" y2="' + f1(y) + '" stroke="' + GRID + '"/>');
    out.push('<text x="' + (L - 4) + '" y="' + f1(y + 3) + '" font-size="10" fill="#9ca3af" text-anchor="end">' + Math.round(t / 1e5) + 'L</text>');
    t += step;
  }
  var zt = [];
  D.zones.forEach(function(z, zi){
    var x1 = Math.max(L, XS(z.a) - slot / 2), x2 = Math.min(L + pw, XS(z.b) + slot / 2);
    if (x2 <= x1) return;
    cl.push('<rect x="' + f1(x1) + '" y="' + T + '" width="' + f1(x2 - x1) + '" height="' + ph + '" fill="' + z.color + '" opacity="' + z.alpha + '"/>' +
            '<rect x="' + f1(x1) + '" y="' + T + '" width="' + f1(x2 - x1) + '" height="' + ph + '" fill="none" stroke="' + z.color + '" stroke-width="1" stroke-dasharray="4 3" opacity="0.6"/>');
    var dem = z.key.indexOf('demand') === 0;
    zt.push('<text x="' + f1(dem ? x2 : x1) + '" y="' + (T - 8 - (zi % 2) * 12) + '" font-size="10" font-weight="700" fill="' + z.color + '" text-anchor="' + (dem ? 'end' : 'start') + '">' + z.short + '</text>');
  });
  var i0 = Math.max(0, Math.floor(a) - 1), i1 = Math.min(n - 1, Math.ceil(b) + 1), bw = Math.min(Math.max(2, slot * 0.38), 30);
  if (labOn) {
    for (var li = i0; li <= i1; li++) {
      var lx = X(li), cy = Y(D.call[li]), py = Y(D.put[li]);
      if (D.clab) {
        cl.push('<text x="' + f1(lx - bw / 2) + '" y="' + f1(Math.max(T + 9, cy - 16)) + '" font-size="8" font-weight="700" fill="#b91c1c" text-anchor="middle">' + D.clab[li][0] + '</text>' +
                '<text x="' + f1(lx - bw / 2) + '" y="' + f1(Math.max(T + 18, cy - 6)) + '" font-size="8" font-weight="700" fill="#b91c1c" text-anchor="middle">' + D.clab[li][1] + '</text>');
        cl.push('<text x="' + f1(lx + bw / 2) + '" y="' + f1(Math.max(T + 9, py - 16)) + '" font-size="8" font-weight="700" fill="#15803d" text-anchor="middle">' + D.plab[li][0] + '</text>' +
                '<text x="' + f1(lx + bw / 2) + '" y="' + f1(Math.max(T + 18, py - 6)) + '" font-size="8" font-weight="700" fill="#15803d" text-anchor="middle">' + D.plab[li][1] + '</text>');
      }
    }
  }
  for (var i = i0; i <= i1; i++) {
    var x = X(i);
    cl.push('<g><title>' + D.tips[i] + '</title>' +
            '<rect x="' + f1(x - bw - 0.5) + '" y="' + f1(Y(D.call[i])) + '" width="' + f1(bw) + '" height="' + f1(Math.max(Y(0) - Y(D.call[i]), 0)) + '" fill="#ef4444"/>' +
            '<rect x="' + f1(x + 0.5) + '" y="' + f1(Y(D.put[i])) + '" width="' + f1(bw) + '" height="' + f1(Math.max(Y(0) - Y(D.put[i]), 0)) + '" fill="#22c55e"/></g>');
  }
  if (sel >= 0 && sel < n) { var xs = X(sel); cl.push('<line x1="' + f1(xs) + '" x2="' + f1(xs) + '" y1="' + T + '" y2="' + (T + ph) + '" stroke="#2563eb" stroke-width="1" stroke-dasharray="3 3"/>'); }
  var tags = [];
  D.lines.forEach(function(l){
    var x = XS(l.val);
    if (x < L || x > L + pw) return;
    cl.push('<line x1="' + f1(x) + '" x2="' + f1(x) + '" y1="' + (T - 52) + '" y2="' + (T + ph) + '" stroke="' + l.color + '" stroke-width="1.6" stroke-dasharray="' + l.dash + '"/>');
    tags.push([x, l]);
  });
  out.push('<g clip-path="url(#cp)">' + cl.join('') + '</g>', zt.join(''));
  var vis = Math.max(1, i1 - i0 + 1), skip = Math.max(1, Math.ceil(vis / 11));
  for (var j = Math.max(0, Math.floor(a)); j <= Math.min(n - 1, Math.ceil(b)); j++) {
    var isAtm = j === D.atm;
    if (isAtm || (j % skip === 0 && Math.abs(j - D.atm) > Math.max(1, Math.floor(skip / 2)))) {
      var lx = X(j);
      if (lx < L + 6 || lx > L + pw - 6) continue;
      out.push('<text x="' + f1(lx) + '" y="' + (H - 16) + '" font-size="9.5" text-anchor="middle"' + (isAtm ? ' font-weight="800" fill="#2563eb"' : ' fill="#6b7280"') + '>' + D.slabels[j] + '</text>');
    }
  }
  tags.sort(function(p, q){ return p[0] - q[0]; });
  tags.forEach(function(q, k){
    var x = q[0], l = q[1], ty = T - 56 + (k % 2) * 16, w = 6.2 * l.lab.length + 8, bx = Math.min(Math.max(x - w / 2, L), L + pw - w);
    out.push('<rect x="' + f1(bx) + '" y="' + f1(ty - 11) + '" width="' + f1(w) + '" height="15" rx="4" fill="' + l.color + '"/>' +
             '<text x="' + f1(bx + w / 2) + '" y="' + f1(ty) + '" font-size="9.5" font-weight="700" fill="#fff" text-anchor="middle">' + l.lab + '</text>');
  });
  out.push('<text x="' + (L + pw / 2) + '" y="' + (H - 2) + '" font-size="10" fill="#9ca3af" text-anchor="middle">Strike  (laal = Call ' + D.mlab + ', hara = Put ' + D.mlab + ')</text>');
  svg.innerHTML = out.join('');
}

function draw(){ if (!D) return; if (MODE === 'oi') drawOI(); else drawPrice(); window.__view = view; window.__mode = MODE; window.__tf = TF; }
function changed(){ clampView(); persist(false); draw(); }

var P = {};
function handle(e, p, zone){
  var r = rect(), k = W / r.width;
  var ids = Object.keys(P).filter(function(id){ return P[id].z === 'plot'; });
  if (zone === 'plot' && ids.length >= 2) {
    var q1 = P[ids[0]], q2 = P[ids[1]], ox1 = q1.x, oy1 = q1.y, ox2 = q2.x, oy2 = q2.y;
    p.x = e.clientX; p.y = e.clientY; p.moved = true;
    var odx = Math.abs(ox1 - ox2), ody = Math.abs(oy1 - oy2), ndx = Math.abs(q1.x - q2.x), ndy = Math.abs(q1.y - q2.y);
    var mx = ((q1.x + q2.x) / 2 - r.left) * k, my = ((q1.y + q2.y) / 2 - r.top) * k;
    if (odx >= ody) { if (ndx > 4 && odx > 4) zoomX(odx / ndx, idxAt(mx)); }
    else if (ndy > 4 && ody > 4) { zoomY(ody / ndy, valAt(my)); }
    changed(); return;
  }
  var dxv = (e.clientX - p.x) * k, dyv = (e.clientY - p.y) * k;
  p.x = e.clientX; p.y = e.clientY;
  if (Math.abs(e.clientX - p.sx) + Math.abs(e.clientY - p.sy) > 5) p.moved = true;
  if (zone === 'plot') {
    var span = view.b - view.a; view.a -= dxv / pw * span; view.b -= dxv / pw * span;
    if (CFG.panY) { var yr = view.hi - view.lo; view.lo += dyv / ph * yr; view.hi += dyv / ph * yr; }
  } else if (zone === 'yaxis') { zoomY(Math.exp(dyv * 0.008), (view.hi + view.lo) / 2); }
  else if (zone === 'xaxis') { zoomX(Math.exp(-dxv * 0.008), (view.a + view.b) / 2); }
  changed();
}
function showSel(e){
  var r = rect(), k = W / r.width, i = Math.floor(idxAt((e.clientX - r.left) * k));
  if (i < 0 || i >= n) { sel = -1; info.textContent = HINT; draw(); return; }
  sel = i; info.textContent = D.tips[i]; draw();
}
function bind(id, zone){
  var el = document.getElementById(id);
  el.addEventListener('pointerdown', function(e){
    try { el.setPointerCapture(e.pointerId); } catch(_) {}
    P[e.pointerId] = {x: e.clientX, y: e.clientY, sx: e.clientX, sy: e.clientY, z: zone, moved: false};
  });
  el.addEventListener('pointermove', function(e){ var p = P[e.pointerId]; if (p) handle(e, p, zone); });
  el.addEventListener('pointerup', function(e){ var p = P[e.pointerId]; delete P[e.pointerId]; if (p && zone === 'plot' && !p.moved) showSel(e); });
  el.addEventListener('pointercancel', function(e){ delete P[e.pointerId]; });
}
bind('zp', 'plot'); bind('za', 'yaxis'); bind('zt', 'xaxis');

function wheelF(e){ return e.deltaY > 0 ? 1.12 : 1 / 1.12; }
document.getElementById('za').addEventListener('wheel', function(e){ e.preventDefault(); zoomY(wheelF(e), (view.hi + view.lo) / 2); changed(); }, {passive: false});
document.getElementById('zt').addEventListener('wheel', function(e){ e.preventDefault(); zoomX(wheelF(e), (view.a + view.b) / 2); changed(); }, {passive: false});
document.getElementById('zp').addEventListener('wheel', function(e){
  var r = rect(), k = W / r.width;
  if (e.ctrlKey || e.metaKey) { e.preventDefault(); zoomX(wheelF(e), idxAt((e.clientX - r.left) * k)); changed(); }
  else if (e.shiftKey) { e.preventDefault(); zoomY(wheelF(e), valAt((e.clientY - r.top) * k)); changed(); }
}, {passive: false});

function reset(){ view.a = DEF.a; view.b = DEF.b; view.lo = DEF.lo; view.hi = DEF.hi; sel = -1; info.textContent = HINT; persist(true); draw(); }
if (document.getElementById('zrs')) document.getElementById('zrs').addEventListener('click', reset);
var zall = document.getElementById('zall');
if (zall) zall.addEventListener('click', function(){ if (D) { var r = obOnly ? obFit() : null; view.lo = r ? r[0] : D.flo; view.hi = r ? r[1] : D.fhi; changed(); } });
var MB = {mP:'price', mO:'oi', mV:'vol', mB:'ob'};
Object.keys(MB).forEach(function(id){ var e = document.getElementById(id); if (e) e.addEventListener('click', function(){ switchMode(MB[id]); }); });
[1,5,15,60,1440].forEach(function(t){ var e = document.getElementById('t' + t); if (e) e.addEventListener('click', function(){ switchTF(t); }); });
var zsmc = document.getElementById('zsmc');
if (zsmc) zsmc.addEventListener('click', function(){ smcOn = !smcOn; zsmc.textContent = smcOn ? '🧩 SMC ✓' : '🧩 SMC'; draw(); });
var zlab = document.getElementById('zlab');
if (zlab) zlab.addEventListener('click', function(){ labOn = !labOn; zlab.textContent = labOn ? '🏷 INT/TV ✓' : '🏷 INT/TV'; draw(); });
markTFBtns();
var zm = document.getElementById('zm'), zp = document.getElementById('zp'), zoomOn = true;
try { var o1 = JSON.parse(window.name || '{}') || {}; if (o1.zm === 0) zoomOn = false; } catch(e) {}
function applyMode(){
  zp.style.touchAction = zoomOn ? 'none' : 'pan-y';
  zm.textContent = zoomOn ? '\u270B Zoom' : '\uD83D\uDCDC Scroll';
  zm.style.background = zoomOn ? '#16a34a' : '#475569';
}
zm.addEventListener('click', function(){
  zoomOn = !zoomOn; applyMode();
  try { var o = JSON.parse(window.name || '{}') || {}; o.zm = zoomOn ? 1 : 0; window.name = JSON.stringify(o); } catch(e) {}
});
applyMode();
stage.addEventListener('dblclick', reset);
if (document.getElementById('zin')) document.getElementById('zin').addEventListener('click', function(){ zoomX(0.7, (view.a + view.b) / 2); zoomY(0.7, (view.hi + view.lo) / 2); changed(); });
if (document.getElementById('zout')) document.getElementById('zout').addEventListener('click', function(){ zoomX(1 / 0.7, (view.a + view.b) / 2); zoomY(1 / 0.7, (view.hi + view.lo) / 2); changed(); });

function layoutOverlays(){
  var pc = function(x, tot){ return (x / tot * 100).toFixed(3) + '%'; };
  var zp = document.getElementById('zp'), za = document.getElementById('za'), zt = document.getElementById('zt');
  zp.style.left = pc(L, W); zp.style.top = pc(T, H); zp.style.width = pc(pw, W); zp.style.height = pc(ph, H);
  za.style.left = pc(CFG.yax[0], W); za.style.top = pc(T, H); za.style.width = pc(CFG.yax[1] - CFG.yax[0], W); za.style.height = pc(ph, H);
  zt.style.left = pc(L, W); zt.style.top = pc(T + ph, H); zt.style.width = pc(pw, W); zt.style.height = pc(H - T - ph, H);
}
function setH(nh){
  H = nh; ph = H - T - B;
  svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
  layoutOverlays(); draw();
}
function onFS(){
  var fsEl = document.fullscreenElement || document.webkitFullscreenElement;
  setTimeout(function(){
    if (fsEl) {
      var st = document.getElementById('stage'), top = document.querySelector('.top'), inf = document.getElementById('info');
      var chrome = (top ? top.offsetHeight : 0) + (inf && inf.style.display !== 'none' ? inf.offsetHeight : 0) + 24;
      var availH = window.innerHeight - chrome, availW = st.offsetWidth || window.innerWidth;
      setH(Math.max(CFG.H, Math.min(1400, Math.round(W * availH / availW))));
    } else {
      setH(CFG.H);
    }
  }, 80);
}
document.addEventListener('fullscreenchange', onFS);
document.addEventListener('webkitfullscreenchange', onFS);
layoutOverlays();
window.__cid = CFG.kind;
window.__update = function(p){
  if (p.v === lastV) return;
  var first = (lastV === null); lastV = p.v;
  if (p.price) DS.price = p.price;
  if (p.vol) DS.vol = p.vol;
  if (p.oi) DS.oi = p.oi;
  if (p.mode && p.mode !== MODE) {
    switchMode(p.mode);
  } else if (MODE === 'vol' || MODE === 'oi') {
    var nd = getDS(MODE); if (nd) { D = nd; n = D.n; changed(); }
  } else {
    var nd2 = getDS(MODE); if (nd2) setData(nd2);
  }
  var w = document.getElementById('wait'); if (w) w.style.display = 'none';
  if (first && window.__restoreScroll) window.__restoreScroll();
};
})();
</script>"""


_CHART_CFG = {
    "price": {"kind": "price", "W": 440, "H": 330, "L": 6, "R": 74, "T": 10, "B": 26, "panY": True, "anchorBottom": False},
    "oi": {"kind": "oi", "W": 440, "H": 354, "L": 32, "R": 6, "T": 70, "B": 34, "panY": False, "anchorBottom": True},
}


def _cfg(kind):
    c = dict(_CHART_CFG[kind])
    c["pw"], c["ph"] = c["W"] - c["L"] - c["R"], c["H"] - c["T"] - c["B"]
    c["yax"] = [c["L"] + c["pw"], c["W"]] if kind == "price" else [0, c["L"]]
    return c


def zoom_shell_html(kind, inst=""):
    """Har chart instance ka alag cid: inst = '-main' ya '-daily' (warna dono charts ek-dusre ko overwrite karte hain)."""
    h_ = _zoom_shell_html_base(kind)
    if inst:
        h_ = h_.replace("window.__cid = CFG.kind;", f"window.__cid = CFG.kind + {json.dumps(inst)};")
    return h_


def _zoom_shell_html_base(kind):
    """Chart ka dhancha: kabhi badalta nahi, isliye refresh par chart reload/chhota nahi hota."""
    cfg = _cfg(kind)
    cfg["dark"] = _dark()
    svgbg = "#0e1117" if cfg["dark"] else "#fff"
    W, H, L, T, pw, ph = cfg["W"], cfg["H"], cfg["L"], cfg["T"], cfg["pw"], cfg["ph"]
    ratio = W / H

    def pc(x, tot):
        return f"{x / tot * 100:.3f}%"

    ax0, ax1 = cfg["yax"]
    css = (
        "<meta charset=\"utf-8\"><style>body{margin:0;font-family:Arial,Helvetica,sans-serif;background:#fff}"
        ".sc{overflow-x:auto;padding:0 2px}"
        ".top{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:flex-start;gap:6px;padding:6px 8px 0 8px;position:sticky;top:0;z-index:20;background:#fff}"
        ".btns{display:flex;flex-wrap:wrap;gap:5px}"
        ".btns button{background:#2563eb;color:#fff;border:none;border-radius:8px;padding:6px 10px;font-size:13px;font-weight:700;cursor:pointer}"
        ".btns button.g{background:#475569;padding:6px 10px}"
        ".btns button:active{opacity:.8}"
        "#info{font-size:11px;color:#334155;min-height:16px;padding:4px 10px 4px 10px;line-height:1.35}"
        "#wait{font-size:13px;color:#6b7280;padding:14px 10px}"
        "#stage{position:relative;line-height:0;user-select:none;-webkit-user-select:none}"
        ".ov{position:absolute}"
        "#zp{touch-action:pan-y;cursor:crosshair}#za,#zt{touch-action:none}#za{cursor:ns-resize}#zt{cursor:ew-resize}"
        "#oc{background:#fff}"
        "#oc:fullscreen{overflow:auto;padding:6px}#oc:-webkit-full-screen{overflow:auto;padding:6px}"
        "#oc:fullscreen .inner,#oc:-webkit-full-screen .inner{max-width:none!important;width:100%!important;min-width:0!important}"
        "#oc:fullscreen #info,#oc:-webkit-full-screen #info,#oc:fullscreen .top>div:first-child,#oc:-webkit-full-screen .top>div:first-child{display:none!important}"
        "</style>"
    )
    hint = "2 ungli pinch = zoom | khinchein = chart khiskao | Axis par khinchein = price/time zoom | tap = data | double tap = reset"
    html = (
        f'{css}<div id="oc" class="{_wc()}"><div class="top"><div></div>'
        '<div class="btns">'
        + ('<button id="zall" class="g" title="Saare zone/levels dikhao">⤢ Sab</button>' if kind == "price" else "")
        + '<button id="zm" class="g">✋ Zoom</button>' + ('<button id="t1" class="g" title="1 minute">1m</button><button id="t5" class="g" title="5 minute">5m</button><button id="t15" class="g" title="15 minute">15m</button><button id="t60" class="g" title="1 ghanta (structure)">1H</button><button id="t1440" class="g" title="1 din (structure)">1D</button>' if kind == "price" else "") + ('<button id="zlab" class="g" title="OI chart par INT / TV labels">🏷 INT/TV</button><button id="zsmc" class="g" title="FVG, BOS/CHoCH, Premium/Discount dikhao ya chhupao">🧩 SMC</button><button id="mP" class="g" title="Price + Zones">📈 Price</button><button id="mO" class="g" title="OI bars">📊 OI</button><button id="mV" class="g" title="Volume zones">📊 Vol</button><button id="mB" class="g" title="Sirf OB BULL / OB BEAR">🟦 OB</button>' if kind == "price" else "") + '<button id="fsbtn" onclick="toggleFS()">⛶ Full Screen</button></div></div>'
        f'<div id="info">{hint}</div><div id="wait">Chart load ho raha hai…</div>'
        '<div class="sc"><div class="inner" style="min-width:360px;max-width:620px;margin:auto"><div id="stage">'
        f'<svg id="svg" viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg" style="background:{svgbg};display:block"></svg>'
        f'<div id="zp" class="ov" style="left:{pc(L, W)};top:{pc(T, H)};width:{pc(pw, W)};height:{pc(ph, H)}"></div>'
        f'<div id="za" class="ov" style="left:{pc(ax0, W)};top:{pc(T, H)};width:{pc(ax1 - ax0, W)};height:{pc(ph, H)}"></div>'
        f'<div id="zt" class="ov" style="left:{pc(L, W)};top:{pc(T + ph, H)};width:{pc(pw, W)};height:{pc(H - T - ph, H)}"></div>'
        '</div></div></div></div>'
    )
    return DARK_CSS + html + ZOOM_JS.replace("__CFG__", json.dumps(cfg)) + FS_JS + SCROLL_JS


def detect_ob(c, mult=1.5, keep=3):
    """Order block (anumaan, pakka nahi): strong candle (body > mult x average body) ke PEHLE ki aakhri ulti candle.
    Strong upar ki candle -> bullish OB = pehli laal candle; strong neeche ki candle -> bearish OB = pehli hari candle.
    Sirf aakhri 'keep' OB."""
    c = c.reset_index(drop=True)
    o = c["open"].astype(float)
    h = c["high"].astype(float)
    l = c["low"].astype(float)
    cl = c["close"].astype(float)
    body = (cl - o).abs()
    avg = body.rolling(20, min_periods=5).mean().shift(1)
    out = []
    for i in range(len(c)):
        a = avg.iloc[i]
        if not (a == a) or a <= 0 or body.iloc[i] <= mult * a:
            continue
        want_bull = cl.iloc[i] > o.iloc[i]
        for j in range(i - 1, max(-1, i - 11), -1):
            if want_bull and cl.iloc[j] < o.iloc[j]:
                out.append(("bull", float(l.iloc[j]), float(h.iloc[j])))
                break
            if (not want_bull) and cl.iloc[j] > o.iloc[j]:
                out.append(("bear", float(l.iloc[j]), float(h.iloc[j])))
                break
    seen, uniq = set(), []
    for x in out:
        k = (x[0], round(x[1], 2), round(x[2], 2))
        if k not in seen:
            seen.add(k)
            uniq.append(x)
    return uniq[-keep:]


def smc_items(c):
    """SMC (Price mode): FVG zones, BOS/CHoCH lines, Premium/Discount zones. Simple rules, anumaan."""
    c = c.reset_index(drop=True)
    h = c["high"].astype(float).values
    l = c["low"].astype(float).values
    cl = c["close"].astype(float).values
    n = len(c)
    zones, lines = [], []
    if n < 6:
        return zones, lines
    # FVG: teen candle ka gap; aakhri 4
    fvgs = []
    for i in range(2, n):
        if l[i] > h[i - 2]:
            fvgs.append({"lo": float(h[i - 2]), "hi": float(l[i]), "side": "demand", "lab": "FVG UP", "col": "#16a34a", "i": i})
        elif h[i] < l[i - 2]:
            fvgs.append({"lo": float(h[i]), "hi": float(l[i - 2]), "side": "supply", "lab": "FVG DOWN", "col": "#dc2626", "i": i})
    for f in fvgs[-2:]:
        zones.append({"label": "", "main": f["lab"], "sec": "", "seccol": "", "secK": None, "secT": "", "short": "FVG",
                      "side": f["side"], "lo": f["lo"], "hi": f["hi"], "color": f["col"], "alpha": 0.10})
    # BOS / CHoCH: confirmed swing (2 candle dono taraf) ke toot-ne par
    trend, last_hi, last_lo, events = None, None, None, []
    for j in range(n):
        k = j - 2
        if 2 <= k < n - 2:
            if h[k] == max(h[k - 2:k + 3]):
                last_hi = float(h[k])
            if l[k] == min(l[k - 2:k + 3]):
                last_lo = float(l[k])
        if last_hi is not None and cl[j] > last_hi:
            events.append(("CHoCH" if trend == "down" else "BOS", "UP", last_hi))
            trend, last_hi = "up", None
        if last_lo is not None and cl[j] < last_lo:
            events.append(("CHoCH" if trend == "up" else "BOS", "DOWN", last_lo))
            trend, last_lo = "down", None
    for kind, d, v in events[-1:]:
        col = "#16a34a" if d == "UP" else "#dc2626"
        lines.append((f"{kind} {'↑' if d == 'UP' else '↓'}", float(v), col))
    # Premium / Discount: pichhle 50 candles ki range
    W = min(50, n)
    H, L = float(max(h[-W:])), float(min(l[-W:]))
    eq = (H + L) / 2
    zones.append({"label": "", "main": "Premium", "sec": "", "seccol": "", "secK": None, "secT": "", "short": "PREM",
                  "side": "supply", "lo": eq, "hi": H, "color": "#f87171", "alpha": 0.06})
    zones.append({"label": "", "main": "Discount", "sec": "", "seccol": "", "secK": None, "secT": "", "short": "DISC",
                  "side": "demand", "lo": L, "hi": eq, "color": "#4ade80", "alpha": 0.06})
    lines.append(("EQ", eq, "#94a3b8"))
    return zones, lines


def price_chart_data(c, spot, ana, xfmt="%H:%M", sig="", fit_all=False, show_vol=True, show_oi=True, breached=None, legacy=False, extra=None):
    items, lines = zone_items(ana, show_vol, show_oi, breached, legacy), level_lines(ana, spot)
    vals = [c["low"].min(), c["high"].max()] + [v for _, v, _ in lines] + [i["lo"] for i in items] + [i["hi"] for i in items]
    flo, fhi = float(min(vals)), float(max(vals))
    fpad = (fhi - flo) * 0.04 or 5
    flo, fhi = flo - fpad, fhi + fpad                      # saare zone + levels
    vis = c.tail(90)                                       # default: aakhri 90 candles hi dikhao
    cl, ch = float(vis["low"].min()), float(vis["high"].max())
    crng = max(ch - cl, abs(float(spot)) * 0.002)
    lo, hi = cl - crng * 0.35, ch + crng * 0.35            # candles saaf dikhein
    if fit_all:
        lo, hi = flo, fhi
    rows = list(c.reset_index(drop=True).itertuples())
    ob_zones = []
    if legacy:                                             # sirf Price + Zones mein OB (anumaan)
        for kind, lo_, hi_ in detect_ob(c):
            bull = kind == "bull"
            ob_zones.append({"label": "", "main": "OB " + ("BULL" if bull else "BEAR"), "sec": "", "seccol": "",
                             "secK": None, "secT": "", "short": "OB", "side": "demand" if bull else "supply",
                             "lo": lo_, "hi": hi_, "color": "#3b82f6" if bull else "#a855f7", "alpha": 0.12})
    smc_zones, smc_lines = ([], [])
    if legacy:
        smc_zones, smc_lines = smc_items(c)
    if extra:
        smc_zones = list(smc_zones) + list(extra.get("zones", []))
        smc_lines = list(smc_lines) + [(x["lab"], x["val"], x["color"]) for x in extra.get("lines", [])]
    return {
        "sig": sig, "n": len(rows),
        "c": [[float(r.open), float(r.high), float(r.low), float(r.close)] for r in rows],
        "labels": [f"{r.time:{xfmt}}" for r in rows],
        "tips": [f"{r.time:%d %b %H:%M}  O {r.open:.2f}  H {r.high:.2f}  L {r.low:.2f}  C {r.close:.2f}" for r in rows],
        "zones": [{"label": i["label"], "main": i.get("main", i["label"]), "sec": i.get("sec", ""), "seccol": i.get("seccol", ""),
                   "secK": i.get("secK"), "secT": i.get("secT", ""),
                   "short": i["short"], "side": i["key"], "lo": i["lo"], "hi": i["hi"], "color": i["color"], "alpha": i["alpha"]} for i in items] + ob_zones + smc_zones,
        "lines": [{"lab": lab, "val": float(val), "color": col, "dash": "2 3" if lab.startswith("LIQ") else "5 4"} for lab, val, col in lines] + [{"lab": lab, "val": float(val), "color": col, "dash": "4 3"} for lab, val, col in smc_lines],
        "lo": lo, "hi": hi, "flo": flo, "fhi": fhi, "defA": max(0, len(rows) - 90), "defB": len(rows) + 1,
    }


def _int_tv(ltp, strike, spot, is_call):
    """(INT, TV) label pair: INT = intrinsic, TV = LTP - INT (negative ho to '—')."""
    intr = max(float(spot) - float(strike), 0.0) if is_call else max(float(strike) - float(spot), 0.0)
    tv = float(ltp) - intr
    return [f"INT {intr:.0f}", f"TV {tv:.0f}" if tv >= 0 else "TV —"]


def oi_chart_data(df, spot, n, ana, sig="", show_vol=True, show_oi=True, metric="oi"):
    d = df.sort_values("Strike").reset_index(drop=True)
    ai = int((d["Strike"] - spot).abs().idxmin())
    v = d.iloc[max(ai - n, 0): ai + n + 1].reset_index(drop=True)
    strikes = v["Strike"].astype(float).tolist()
    sstep = min([b - a for a, b in zip(strikes, strikes[1:])] or [50])
    atm = float(d.loc[ai, "Strike"])
    cc, pc_ = ("Call Vol", "Put Vol") if metric == "vol" else ("Call OI", "Put OI")
    ymax = max(float(v[cc].max()), float(v[pc_].max()), 1.0) * 1.1
    zones = [
        {"key": it["key"], "short": it.get("shortp", it["short"]), "a": it["level"], "b": it["level"], "color": it["color"], "alpha": it["alpha"]}
        for it in zone_items(ana, show_vol, show_oi)
    ]
    lines = [
        {"lab": lab, "val": float(val), "color": col, "dash": "2 3" if lab.startswith("LIQ") else "5 4"}
        for lab, val, col in level_lines(ana, spot)
    ]
    return {
        "sig": "oi|" + sig + "|" + metric, "n": len(strikes), "mlab": "Vol" if metric == "vol" else "OI",
        "s0": strikes[0], "sstep": sstep, "atm": strikes.index(atm) if atm in strikes else -1,
        "slabels": [str(fs(s)) for s in strikes],
        "call": [float(x) for x in v[cc]], "put": [float(x) for x in v[pc_]],
        "tips": ([f'{fs(r["Strike"])}  Call Vol {fmt_vol(r["Call Vol"])}  Put Vol {fmt_vol(r["Put Vol"])}' for _, r in v.iterrows()]
                 if metric == "vol" else
                 [f'{fs(r["Strike"])}  Call OI {r["Call OI"] / 1e5:.1f}L  Put OI {r["Put OI"] / 1e5:.1f}L' for _, r in v.iterrows()]),
        "zones": zones, "lines": lines, "lo": 0.0, "hi": ymax, "defA": 0, "defB": len(strikes),
        "clab": [_int_tv(ltp, s_, spot, True) for ltp, s_ in zip(v["Call LTP"].tolist(), strikes)],
        "plab": [_int_tv(ltp, s_, spot, False) for ltp, s_ in zip(v["Put LTP"].tolist(), strikes)],
    }


def resample_candles(c, minutes):
    if minutes <= 1 or c.empty:
        return c
    o = (c.set_index("time")
          .resample(f"{minutes}min")
          .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
          .dropna().reset_index())
    return o


# ---------------- Optional: Claude AI commentary ----------------
def get_anthropic_key():
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        return os.getenv("ANTHROPIC_API_KEY")


def ask_claude(summary_text):
    key = get_anthropic_key()
    if not key:
        return None, "ANTHROPIC_API_KEY nahi mila. Streamlit Secrets ya .env mein add karein."
    prompt = (
        "Tum ek experienced Indian options market analyst ho. Neeche option chain ka analysis data hai. "
        "Hinglish mein short, clear analysis do: market bias, supply zone (resistance), demand zone (support), "
        "breakout/breakdown ke levels, aur risk. Last mein 1 line disclaimer do (financial advice nahi hai).\n\n"
        + summary_text
    )
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-5-5", "max_tokens": 1000, "messages": [{"role": "user", "content": prompt}]},
            timeout=60,
        )
        data = r.json()
        return "".join(b.get("text", "") for b in data.get("content", [])), None
    except Exception as e:
        return None, str(e)



def get_secret(name):
    try:
        v = st.secrets[name]
    except Exception:
        v = os.getenv(name)
    if isinstance(v, str):                       # galti se aaye space / quotes hata do
        v = v.strip().strip('"').strip("'").strip()
    return v


def ask_gemini(summary_text):
    """FREE option: Google Gemini. Do tarah ki key chalti hai:
       - 'AIza...'  : Google AI Studio key (generativelanguage endpoint)
       - 'AQ.Ab8...': Vertex AI express-mode key (aiplatform endpoint)"""
    key = get_secret("GEMINI_API_KEY")
    if not key:
        return None, "GEMINI_API_KEY nahi mila."
    vertex = key.startswith("AQ.")
    prompt = (
        "Tum ek experienced Indian options market analyst ho. Neeche option chain ka analysis data hai. "
        "Hinglish mein short, clear analysis do: market bias, supply zone (resistance), demand zone (support), "
        "breakout/breakdown ke levels, aur risk. Last mein 1 line disclaimer do (financial advice nahi hai).\n\n"
        + summary_text
    )
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    models = [get_secret("GEMINI_MODEL"), "gemini-flash-latest", "gemini-2.5-flash", "gemini-2.0-flash"]
    last = ""
    for model in dict.fromkeys(m for m in models if m):
        try:
            if vertex:
                r = requests.post(
                    f"https://aiplatform.googleapis.com/v1/publishers/google/models/{model}:generateContent",
                    params={"key": key}, headers={"Content-Type": "application/json"}, json=body, timeout=60,
                )
            else:
                r = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    headers={"x-goog-api-key": key, "Content-Type": "application/json"}, json=body, timeout=60,
                )
            data = r.json()
        except Exception as e:
            return None, str(e)
        if "candidates" in data:
            try:
                parts = data["candidates"][0]["content"]["parts"]
                return "".join(p.get("text", "") for p in parts), None
            except Exception:
                last = f"{model}: khali jawab"
                continue
        err = data.get("error", {}) if isinstance(data, dict) else {}
        msg = str(err.get("message", data))[:220]
        last = f"{model}: {msg}"
        if err.get("code") in (400, 401, 403) and ("API key" in msg or "credentials" in msg or "authentication" in msg.lower()):
            break                                # key ka masla hai, doosra model try karna bekaar
    hint = ""
    if "API key" in last or "credentials" in last:
        hint = (" | Key sahi copy karein: AI Studio key 'AIza' se, Vertex express key 'AQ.' se shuru hoti hai. "
                "Secrets mein double quotes ke andar daalein aur app Reboot karein.")
    return None, f"Gemini error: {last}{hint}"


def ask_ai(summary_text):
    """Pehle free Gemini, phir Claude (jo key mili ho)."""
    if get_secret("GEMINI_API_KEY"):
        return ask_gemini(summary_text)
    if get_secret("ANTHROPIC_API_KEY"):
        return ask_claude(summary_text)
    return None, ("Koi AI key nahi mila. Secrets mein GEMINI_API_KEY ya ANTHROPIC_API_KEY daalein.")


# ---------------- Shifting: option ki intraday history (button dabane par) ----------------
def fetch_option_hist(key):
    try:
        data = requests.get(f"https://api.upstox.com/v2/historical-candle/intraday/{enc(key)}/1minute",
                            headers=HEADERS, timeout=20).json()
        cs = (data.get("data") or {}).get("candles") or []
        if not cs:
            e = data.get("errors") or [{}]
            return key, None, str(e[0].get("message") or ("aaj ka candle data khali aaya" if data.get("status") == "success" else (data.get("status") or "khali")))[:80]
        c = pd.DataFrame(cs).iloc[:, :7]
        c.columns = ["time", "o", "h", "l", "c", "vol", "oi"]
        c["time"] = pd.to_datetime(c["time"], utc=True).dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
        return key, c[["time", "vol", "oi", "h", "l", "c"]].sort_values("time").reset_index(drop=True), ""
    except Exception as e:
        return key, None, str(e)[:80]


def build_shift(df, spot, n, cutoff):
    d = df.sort_values("Strike").reset_index(drop=True)
    ai = int((d["Strike"] - spot).abs().idxmin())
    view = d.iloc[max(ai - n, 0): ai + n + 1]
    if "Call Key" not in view.columns:
        return {"error": "Option ke instrument key nahi mile."}
    keys = [k for k in list(view["Call Key"]) + list(view["Put Key"]) if isinstance(k, str) and k]
    if not keys:
        return {"error": "Upstox chain mein option ke instrument key nahi aaye, isliye shifting nahi nikal sakta."}
    hist, errs = {}, []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for key, h, e in ex.map(fetch_option_hist, keys):
            if h is not None:
                hist[key] = h
            else:
                errs.append(e)
    if not hist:
        return {"error": "Option ki history nahi aayi. Upstox ka jawab: " + (errs[0] if errs else "khali")}
    res = shift_analysis(view, hist, cutoff)
    res.update({"cut": cutoff.strftime("%H:%M"), "asof": max(h["time"].max() for h in hist.values()).strftime("%H:%M"),
                "n_ok": len(hist), "n_all": len(keys)})
    return res


# ---------------- Pressure matrix (9:17 se 3 ghante, support/resistance ke tees) ----------------
PRESS_START, PRESS_END = dt_time(9, 17), dt_time(12, 17)
PRESS_LABEL = {"STRONG": "मज़बूत (दायरा)", "UP": "⬆ बुलिश", "DOWN": "⬇ बेयरिश"}
PRESS_COL = {("STRONG", "STRONG"): 1, ("STRONG", "DOWN"): 2, ("STRONG", "UP"): 3,
             ("DOWN", "STRONG"): 4, ("UP", "STRONG"): 5, ("DOWN", "DOWN"): 6,
             ("UP", "UP"): 7, ("DOWN", "UP"): 8, ("UP", "DOWN"): 9}


def _win_metrics(view, hist, end=None):
    """Har option ke liye 9:17 se 'end' tak ka Volume, aakhri OI, aur kya OI badh raha hai (aur volume dusre half mein zyada)."""
    end = end or PRESS_END
    rows = []
    for _, r in view.iterrows():
        for side, kc in (("Call", "Call Key"), ("Put", "Put Key")):
            h = hist.get(r.get(kc))
            if h is None or h.empty:
                continue
            tm = h["time"].dt.time
            w = h[(tm >= PRESS_START) & (tm <= end)]
            if w.empty:
                continue
            half = max(len(w) // 2, 1)
            v1 = float(w["vol"].iloc[:half].sum())
            v2 = float(w["vol"].iloc[half:].sum())
            rows.append({"side": side, "strike": float(r["Strike"]), "vol": float(w["vol"].sum()),
                         "oi_last": float(w["oi"].iloc[-1]),
                         "rising": bool(float(w["oi"].iloc[-1]) > float(w["oi"].iloc[0]) and v2 >= v1)})
    return pd.DataFrame(rows)


def _zone_state(m, side, zone_k, spot, kind):
    """Shart (aapke niyam ke hisaab se):
    - Bahar wali taraf (res: zone se upar; sup: zone se neeche): Volume AUR OI dono 75%+ aur badhte hon.
    - Andar wali taraf (spot ki taraf): dono mein se ek bhi 75%+ aur badhta ho.
    res: bahar = UP (bullish), andar = DOWN (bearish). sup: bahar = DOWN (bearish), andar = UP (bullish)."""
    if m.empty or zone_k is None:
        return "STRONG", None
    x = m[m["side"] == side].copy()
    if x.empty:
        return "STRONG", None
    x["sv"] = x["vol"] / max(float(x["vol"].max()), 1.0) * 100
    x["so"] = x["oi_last"] / max(float(x["oi_last"].max()), 1.0) * 100
    if kind == "res":
        out_m = x["strike"] > zone_k
        in_m = (x["strike"] > spot) & (x["strike"] < zone_k)
        out_state, in_state = "UP", "DOWN"
    else:
        out_m = x["strike"] < zone_k
        in_m = (x["strike"] < spot) & (x["strike"] > zone_k)
        out_state, in_state = "DOWN", "UP"
    cand = x[out_m & (x["sv"] >= 75) & (x["so"] >= 75) & x["rising"]]
    if not cand.empty:
        return out_state, float(cand.sort_values("vol", ascending=False).iloc[0]["strike"])
    cand = x[in_m & ((x["sv"] >= 75) | (x["so"] >= 75)) & x["rising"]]
    if not cand.empty:
        return in_state, float(cand.sort_values("vol", ascending=False).iloc[0]["strike"])
    return "STRONG", None


def _timeline(view, hist, end_t, side, cand_k, zone_k, kind, state, spot):
    """Har minute par dekhta hai ki candidate strike ki shart poori hai ya nahi, aur us se intervals banata hai."""
    if cand_k is None or state == "STRONG":
        return None
    key_col = "Call Key" if side == "Call" else "Put Key"
    rows = []
    for _, r in view.iterrows():
        h = hist.get(r.get(key_col))
        if h is None or h.empty:
            continue
        tm = h["time"].dt.time
        w = h[(tm >= PRESS_START) & (tm <= end_t)]
        if w.empty:
            continue
        w = w.assign(strike=float(r["Strike"]))
        rows.append(w[["time", "strike", "vol", "oi"]])
    if not rows:
        return None
    allw = pd.concat(rows)
    pv = allw.pivot_table(index="time", columns="strike", values="vol", aggfunc="sum").fillna(0).sort_index().rolling(15, min_periods=1).sum()  # pichle 15 min ka volume (current pace)
    po = allw.pivot_table(index="time", columns="strike", values="oi", aggfunc="last").sort_index().ffill().bfill()
    if cand_k not in pv.columns or cand_k not in po.columns:
        return None
    sv = pv.div(pv.max(axis=1).replace(0, 1), axis=0) * 100
    so = po.div(po.max(axis=1).replace(0, 1), axis=0) * 100
    rising = po[cand_k] > po[cand_k].iloc[0]
    if kind == "res":
        outside = state == "UP"
    else:
        outside = state == "DOWN"
    if outside:
        cond = (sv[cand_k] >= 75) & (so[cand_k] >= 75) & rising
    else:
        cond = ((sv[cand_k] >= 75) | (so[cand_k] >= 75)) & rising
    cond = cond.astype(bool)
    intervals, start, prev = [], None, None
    for t, ok in cond.items():
        if ok and start is None:
            start = t
        if not ok and start is not None:
            intervals.append((start, prev))
            start = None
        prev = t
    if start is not None:
        intervals.append((start, prev))
    if not intervals:
        return {"strike": cand_k, "text": f"{cand_k:g} par shart kabhi poori nahi hui"}
    parts = [f"{a:%H:%M} se {b:%H:%M} tak poori"for a, b in intervals]
    txt = f"{cand_k:g} par: " + ", ".join(parts)
    if start is None and intervals and intervals[-1][1] != cond.index[-1]:
        txt += f"; {intervals[-1][1]:%H:%M} ke baad 75% se neeche gaya"
    elif start is not None:
        txt += "; abhi tak chal rahi hai"
    return {"strike": cand_k, "text": txt}


# Notes ke hisaab se: Resistance aur Support ka trend (volume %, pichle 30 min se) -> 9 column
PRESS_MATRIX = {
    ("UP", "FLAT"): (1, "Bullish"), ("DOWN", "FLAT"): (2, "Bearish"), ("FLAT", "FLAT"): (3, "Consolidated"),
    ("UP", "UP"): (4, "Sideways (saaf nahi)"), ("DOWN", "UP"): (5, "Bearish"), ("FLAT", "UP"): (6, "Bearish"),
    ("FLAT", "DOWN"): (7, "Bullish"), ("UP", "DOWN"): (8, "Bullish"), ("DOWN", "DOWN"): (9, "Consolidated"),
}
TREND_TXT = {"UP": "⬆ badh raha", "DOWN": "⬇ ghat raha", "FLAT": "↔ stable"}


def _vol_trend(view, hist, end_t, side, k):
    """Us side ke sab strike ka 15-min rolling volume; k ka share (max ke % mein) ab vs 30 min pehle."""
    key_col = "Call Key" if side == "Call" else "Put Key"
    rows = []
    for _, r in view.iterrows():
        h = hist.get(r.get(key_col))
        if h is None or h.empty:
            continue
        tm = h["time"].dt.time
        w = h[(tm >= PRESS_START) & (tm <= end_t)]
        if w.empty:
            continue
        rows.append(w.assign(strike=float(r["Strike"]))[["time", "strike", "vol"]])
    if not rows:
        return None
    allw = pd.concat(rows)
    pv = allw.pivot_table(index="time", columns="strike", values="vol", aggfunc="sum").fillna(0).sort_index()
    if float(k) not in pv.columns:
        return None
    roll = pv.rolling(15, min_periods=1).sum()
    share = roll.div(roll.max(axis=1).replace(0, 1), axis=0) * 100
    series = share[float(k)]
    now = float(series.iloc[-1])
    past = series[series.index <= series.index[-1] - pd.Timedelta(minutes=30)]
    before = float(past.iloc[-1]) if len(past) else float(series.iloc[0])
    diff = now - before
    trend = "UP" if diff > 5 else "DOWN" if diff < -5 else "FLAT"
    return {"strike": float(k), "share": now, "trend": trend, "diff": diff}


def build_pressure_full(df, spot, n, ana):
    vs = ana.get("zone_sets", {}).get("vol", {})
    if not vs.get("supply") or not vs.get("demand"):
        return {"error": "Volume zone nahi mila, pressure nahi nikal sakta."}
    res_k = float(vs["supply"][0]["primary"]["strike"])
    sup_k = float(vs["demand"][0]["primary"]["strike"])
    d = df.sort_values("Strike").reset_index(drop=True)
    ai = int((d["Strike"] - spot).abs().idxmin())
    view = d.iloc[max(ai - n, 0): ai + n + 1]
    view = pd.concat([view, d[d["Strike"].isin([sup_k, res_k])]]).drop_duplicates(subset=["Strike"])
    keys = [k for k in list(view["Call Key"]) + list(view["Put Key"]) if isinstance(k, str) and k]
    if not keys:
        return {"error": "Option ke instrument key nahi mile, pressure nahi nikal sakta."}
    hist, errs = {}, []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for key, h, e in ex.map(fetch_option_hist, keys):
            if h is not None:
                hist[key] = h
            else:
                errs.append(e)
    if not hist:
        return {"error": "Option ki history nahi aayi. Upstox ka jawab: " + (errs[0] if errs else "khali")}
    end_t = max(h["time"].max() for h in hist.values()).time()
    if end_t > dt_time(15, 30):
        end_t = dt_time(15, 30)
    rt = _vol_trend(view, hist, end_t, "Call", res_k)
    st_ = _vol_trend(view, hist, end_t, "Put", sup_k)
    if rt is None or st_ is None:
        return {"error": f"{PRESS_START:%H:%M} se ab tak ka volume data abhi nahi hai. Market khulne ke baad dobara dabayein."}
    col, result = PRESS_MATRIX[(rt["trend"], st_["trend"])]
    return {
        "support": {"state": st_["trend"], "zone": sup_k, "at": None, "tl": None, "share": st_["share"]},
        "resistance": {"state": rt["trend"], "zone": res_k, "at": None, "tl": None, "share": rt["share"]},
        "column": col, "result": result,
        "alert": result == "Bearish",
        "support_strike": sup_k,
        "end_label": end_t.strftime("%H:%M"),
        "n_ok": len(hist), "n_all": len(keys),
    }


def pressure_html(pr):
    def row(name, d):
        if d["zone"] is None:
            return f"{name}: zone nahi mila"
        strong = "मज़बूत" if d.get("share", 0) >= 60 else "कमज़ोर"
        return (f"{name} <b>{fs(d['zone'])}</b> → {TREND_TXT[d['state']]} · {strong} "
                f"({pct_s(d.get('share', 0))})")
    return (f"🧭 <b>Pressure matrix</b> (Volume) · {PRESS_START:%H:%M}–{pr.get('end_label', '')} · "
            f"Column <b>{pr['column']}</b> · <b>{pr['result']}</b><br>"
            f"{row('Support', pr['support'])}<br>{row('Resistance', pr['resistance'])}<br>"
            f"<span style='font-size:11px;color:#374151'>{pr['n_ok']}/{pr['n_all']} options ka data mila</span>")


# ---------------- Price backtest: zone par price kitni baar ruka (sirf candles, koi alert nahi) ----------------
def zone_backtest(c, ana, look=12):
    """Har zone ke liye: price kitni baar zone mein aaya, aur aage 'look' candles mein wo ruka (rukaa) ya toota (2 candle lagatar bahar close).
    Supply: upar se aakar zone ke andar aaye. Demand: neeche se. Ye sirf ek jhalak hai, pakka saboot nahi."""
    rows = []
    if c is None or len(c) < 3 or not ana:
        return rows
    c = c.reset_index(drop=True)
    hi_s, lo_s, cl_s = c["high"].astype(float).values, c["low"].astype(float).values, c["close"].astype(float).values
    n = len(c)
    for it in zone_items(ana):
        side, lo, hi = it["key"], float(it["lo"]), float(it["hi"])
        touches = rukaa = toota = dekha = 0
        for i in range(1, n):
            if side == "supply":
                entered = hi_s[i] >= lo and hi_s[i - 1] < lo
            else:
                entered = lo_s[i] <= hi and lo_s[i - 1] > hi
            if not entered:
                continue
            touches += 1
            out = "dekha"
            for j in range(i + 1, min(n, i + 1 + look)):
                if side == "supply":
                    if cl_s[j] < lo:
                        out = "rukaa"; break
                    if cl_s[j] > hi and j + 1 < n and cl_s[j + 1] > hi:
                        out = "toota"; break
                else:
                    if cl_s[j] > hi:
                        out = "rukaa"; break
                    if cl_s[j] < lo and j + 1 < n and cl_s[j + 1] < lo:
                        out = "toota"; break
            if out == "rukaa":
                rukaa += 1
            elif out == "toota":
                toota += 1
            else:
                dekha += 1
        pct = round(rukaa / (rukaa + toota) * 100, 1) if (rukaa + toota) else None
        rows.append({"Zone": it["label"], "Touch": touches, "Ruka": rukaa, "Toota": toota,
                     "Dekha nahi": dekha, "Ruka %": pct})
    return rows


def zone_test_table_html(rows):
    """Backtest table: light/dark dono mein padhne layak (st.dataframe light mode mein gehra dikhta tha)."""
    cols = ["Zone", "Touch", "Ruka", "Toota", "Dekha nahi", "Ruka %"]
    th = "".join(f'<th style="text-align:left;padding:6px 8px;background:#f3f4f6;color:#111;border-bottom:2px solid #d1d5db">{c}</th>' for c in cols)
    body = ""
    for r in rows:
        pct = "—" if r["Ruka %"] is None else f'{r["Ruka %"]}%'
        cells = [r["Zone"], r["Touch"], r["Ruka"], r["Toota"], r["Dekha nahi"], pct]
        body += "<tr>" + "".join(
            f'<td style="padding:6px 8px;color:#111;background:#ffffff;border-bottom:1px solid #e5e7eb">{c}</td>' for c in cells) + "</tr>"
    return ('<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:13px">'
            f'<thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>')


# ---------------- Volume matrix (Volume + Zone wale notes ke hisaab se, sirf Volume, koi OI nahi) ----------------
WTT, WTB = "Weak towards top (WTT)", "Weak towards bottom (WTB)"
VM_MAP = {("↑", "↔"): (WTT, 1), ("↓", "↔"): (WTB, 2), ("↔", "↔"): ("Consolidated", 3),
          ("↑", "↑"): ("Sideways (—)", 4), ("↓", "↑"): (WTB, 5), ("↔", "↑"): (WTB, 6),
          ("↔", "↓"): (WTT, 7), ("↑", "↓"): (WTT, 8), ("↓", "↓"): ("Consolidated", 9)}


def _vol_trend(view, hist, side, k, end_t):
    """Volume share (max ke mukable %) pehle half aur doosre half mein; badh raha to ↑, ghat raha to ↓, warna ↔."""
    key_col = "Call Key" if side == "Call" else "Put Key"
    rows = []
    for _, r in view.iterrows():
        h = hist.get(r.get(key_col))
        if h is None or h.empty:
            continue
        tm = h["time"].dt.time
        w = h[(tm >= PRESS_START) & (tm <= end_t)]
        if w.empty:
            continue
        mid = w["time"].iloc[len(w) // 2]
        a = float(w[w["time"] < mid]["vol"].sum())
        b = float(w[w["time"] >= mid]["vol"].sum())
        rows.append((float(r["Strike"]), a, b))
    t = pd.DataFrame(rows, columns=["k", "a", "b"])
    if t.empty or not (t["k"] == k).any():
        return None, "data nahi"
    ma, mb = max(float(t["a"].max()), 1.0), max(float(t["b"].max()), 1.0)
    row = t[t["k"] == k].iloc[0]
    sa, sb = row["a"] / ma * 100, row["b"] / mb * 100
    if sb >= 60 and sb > sa + 5:
        arrow = "↑"
    elif sa >= 60 and sb < sa - 5:
        arrow = "↓"
    else:
        arrow = "↔"
    return arrow, f"{fs(k)} par volume share {pct_s(sa)} → {pct_s(sb)}"


def build_volume_matrix(df, spot, n, ana):
    vs = (ana or {}).get("zone_sets", {}).get("vol", {})
    if not vs.get("supply") or not vs.get("demand"):
        return {"error": "Volume zone 1 nahi bana, matrix nahi nikal sakta."}
    d = df.sort_values("Strike").reset_index(drop=True)
    ai = int((d["Strike"] - spot).abs().idxmin())
    view = d.iloc[max(ai - n, 0): ai + n + 1]
    keys = [k for k in list(view["Call Key"]) + list(view["Put Key"]) if isinstance(k, str) and k]
    if not keys:
        return {"error": "Option ke instrument key nahi mile."}
    hist, errs = {}, []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for key, h, e in ex.map(fetch_option_hist, keys):
            if h is not None:
                hist[key] = h
            else:
                errs.append(e)
    if not hist:
        return {"error": "Option ki history nahi aayi. Upstox ka jawab: " + (errs[0] if errs else "khali")}
    end_t = max(h["time"].max() for h in hist.values()).time()
    if end_t > dt_time(15, 30):
        end_t = dt_time(15, 30)
    r_k, s_k = float(vs["supply"][0]["strike"]), float(vs["demand"][0]["strike"])
    ra, rtxt = _vol_trend(view, hist, "Call", r_k, end_t)
    sa, stxt = _vol_trend(view, hist, "Put", s_k, end_t)
    if ra is None or sa is None:
        return {"error": "Volume ka trend nahi nikal paya (data kam hai). Market khulne ke baad dobara dabayein."}
    label, col = VM_MAP[(ra, sa)]
    return {"res_k": r_k, "sup_k": s_k, "res_arrow": ra, "sup_arrow": sa, "res_txt": rtxt, "sup_txt": stxt,
            "label": label, "column": col, "end_label": end_t.strftime("%H:%M")}


def volume_matrix_html(vm):
    arrow_word = {"↑": "badh raha", "↓": "ghat raha", "↔": "stable"}
    return (f"📋 <b>Volume matrix</b> (9:17–{vm['end_label']}) · Column <b>{vm['column']}</b> → <b>{vm['label']}</b><br>"
            f"Resistance <b>{fs(vm['res_k'])}</b> → {vm['res_arrow']} {arrow_word[vm['res_arrow']]}"
            f"<br><span style='font-size:12px;color:#374151'>↳ {vm['res_txt']}</span><br>"
            f"Support <b>{fs(vm['sup_k'])}</b> → {vm['sup_arrow']} {arrow_word[vm['sup_arrow']]}"
            f"<br><span style='font-size:12px;color:#374151'>↳ {vm['sup_txt']}</span>")


# ---------------- Candles (price chart ke liye) ----------------
EMPTY_ANA = {"hist": True, "zone_sets": {"vol": {"supply": [], "demand": []}, "oi": {"supply": [], "demand": []}},
             "liq": [], "max_pain": None, "zone_width": 40, "step": 50}


@st.cache_data(ttl=86400)
def fetch_candles_for_day(inst_key, day):
    """Ek trading din ke 1-minute candles (Upstox historical-candle)."""
    key = enc(inst_key)
    d = day.strftime("%Y-%m-%d")
    try:
        r = requests.get(f"https://api.upstox.com/v2/historical-candle/{key}/1minute/{d}/{d}", headers=HEADERS, timeout=20).json()
        cs = (r.get("data") or {}).get("candles") or []
        if not cs:
            return pd.DataFrame(), "none", f"{d} ka candle data khali aaya"
        c = pd.DataFrame(cs).iloc[:, :6]
        c.columns = ["time", "open", "high", "low", "close", "volume"]
        c["time"] = pd.to_datetime(c["time"], utc=True).dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
        return c.sort_values("time").reset_index(drop=True), "intraday", ""
    except Exception as e:
        return pd.DataFrame(), "error", str(e)[:150]


@st.cache_data(ttl=3)
def fetch_candles(inst_key):
    key = enc(inst_key)

    def parse(data):
        cs = (data.get("data") or {}).get("candles") or []
        if not cs:
            return pd.DataFrame()
        c = pd.DataFrame(cs).iloc[:, :6]
        c.columns = ["time", "open", "high", "low", "close", "volume"]
        c["time"] = pd.to_datetime(c["time"], utc=True).dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
        return c.sort_values("time").reset_index(drop=True)

    def why(r):
        try:
            e = r.get("errors") or []
            if e:
                return str(e[0].get("message") or e[0])[:200]
            return str(r.get("message") or r.get("status") or "khali jawab")[:200]
        except Exception:
            return str(r)[:200]

    err = ""
    try:
        r = requests.get(f"https://api.upstox.com/v2/historical-candle/intraday/{key}/1minute", headers=HEADERS, timeout=20).json()
        c = parse(r)
        if not c.empty:
            return c, "intraday", ""
        err = "Intraday: " + why(r)
        to, frm = date.today(), date.today() - timedelta(days=7)
        r = requests.get(f"https://api.upstox.com/v2/historical-candle/{key}/30minute/{to}/{frm}", headers=HEADERS, timeout=20).json()
        c = parse(r)
        if not c.empty:
            return c, "history", ""
        return pd.DataFrame(), "none", err + " | History: " + why(r)
    except Exception as e:
        return pd.DataFrame(), "error", f"{err} {e}".strip()


def current_shift():
    sh = st.session_state.get("shift")
    if sh and sh.get("inst") == inst_name and sh.get("exp") == expiry_date and not sh.get("error"):
        return sh
    return None


def zone_marks(ana, df, spot):
    """Option chain ke labels (dono side ek hi strike par ho to cell mein 3 hisse):
    - Zone 1: SUPPORT - WTT (support) / RESISTANCE - WTB (resistance).
    - Baaki (75% rule): S / R, numbering 1,2.. (ek ho to bina number).
    - Ek hi strike par support aur resistance dono ho:  upar resistance (laal), beech strike, neeche support (hara).
    Pressure matrix chalaya ho to zone 1 ke label mein uska state bhi."""
    st_txt = {"STRONG": "मज़बूत", "UP": "बुलिश", "DOWN": "बेयरिश"}
    pr = st.session_state.get("pressure") or {}
    same = bool(pr) and pr.get("inst") == inst_name and pr.get("exp") == expiry_date and not pr.get("error")
    vs = (ana or {}).get("zone_sets", {}).get("vol", {}) if ana else {}
    if df is None or df.empty or not vs:
        return {}
    d = df.sort_values("Strike").reset_index(drop=True)
    atm = float(d.loc[(d["Strike"] - spot).abs().idxmin(), "Strike"])
    mx = {c: max(float(d[c].max()), 1.0) for c in ("Call Vol", "Call OI", "Put Vol", "Put OI")}

    def pcts(row, side):
        return (float(row[f"{side} Vol"]) / mx[f"{side} Vol"] * 100, float(row[f"{side} OI"]) / mx[f"{side} OI"] * 100)

    def ok_2(row, side, inner):
        pv, po = pcts(row, side)
        return (max(pv, po) >= 75) if inner else (pv >= 75 and po >= 75)

    sup_map, res_map = {}, {}                                    # strike -> (label, bg)

    def numbered(entries, letter, word, bg, extra_zone1, target):
        z1 = [e for e in entries if e[3]]
        others = sorted([e for e in entries if not e[3]], key=lambda e: e[0])
        for _, k, tag, _ in z1:
            target[fs(k)] = (word + extra_zone1, bg)                 # zone 1: SUPPORT / RESISTANCE
        # 75% wale extra strikes option chain mein nahi dikhte: sirf zone 1 (SUPPORT / RESISTANCE)

    def pick_z1(side):
        """Zone 1 = Volume wala ya OI wala zone, jo bhi samne (strike par) zyada % ka ho."""
        cols = "Put" if side == "demand" else "Call"
        opts = []
        for basis in ("vol", "oi"):
            zl = (ana or {}).get("zone_sets", {}).get(basis, {}).get(side) or []
            if zl:
                k = float(zl[0]["primary"]["strike"])
                rows_k = d[d["Strike"] == k]
                if not rows_k.empty:
                    pv, po = pcts(rows_k.iloc[0], cols)
                    opts.append((round(max(pv, po), 6), -abs(k - spot), k))   # tie par market ke sabse paas wala
        if not opts:
            return None
        # Pehle market ke bilkul paas (3 strike ke andar) ka dekho: wahan 75%+ ho to wahi lo, door ka OI nahi
        _stp = float(pd.Series(sorted(d["Strike"].astype(float).unique())).diff().dropna().min() or 50.0)
        near_o = [o for o in opts if abs(o[2] - atm) <= 3 * _stp]
        if near_o and max(o[0] for o in near_o) >= 75:
            return max(near_o)[2]
        return max(opts)[2]

    s1 = pick_z1("demand")
    if s1 is not None:
        entries = [(abs(s1 - atm), s1, "WTT", True)]
        for _, r in d.iterrows():
            k = float(r["Strike"])
            if k == s1 or k > atm:
                continue
            if k > s1:
                if ok_2(r, "Put", True):
                    entries.append((abs(k - atm), k, "WTT", False))
            else:
                if ok_2(r, "Put", False):
                    entries.append((abs(k - atm), k, "WTB", False))
        extra = f" · {st_txt.get(pr['support']['state'], '')}" if same else ""
        numbered(entries, "S", "SUPPORT", "#15803d", extra, sup_map)

    r1 = pick_z1("supply")
    if r1 is not None:
        entries = [(abs(r1 - atm), r1, "WTB", True)]
        for _, r in d.iterrows():
            k = float(r["Strike"])
            if k == r1 or k < atm:
                continue
            if k < r1:
                if ok_2(r, "Call", True):
                    entries.append((abs(k - atm), k, "WTB", False))
            else:
                if ok_2(r, "Call", False):
                    entries.append((abs(k - atm), k, "WTT", False))
        extra = f" · {st_txt.get(pr['resistance']['state'], '')}" if same else ""
        numbered(entries, "R", "RESISTANCE", "#b91c1c", extra, res_map)

    m = {}
    for key in set(sup_map) | set(res_map):
        sup = sup_map.get(key)
        res = res_map.get(key)
        if sup and res:
            m[key] = {"dual": [(f"🔴 {res[0]}", "#b91c1c"), (f"🟢 {sup[0]}", "#15803d")], "fg": "#ffffff", "numfg": "#ffffff", "txt": ""}
        else:
            lab, bg = sup or res
            icon = "🟢" if bg == "#15803d" else "🔴"
            m[key] = {"bg": bg, "fg": "#ffffff", "numfg": "#ffffff", "txt": f"{icon} {lab}"}
    return m


def _iv_txt(v):
    try:
        f_ = float(v)
        return "—" if f_ != f_ else f"{f_:.1f}"
    except Exception:
        return "—"


@st.cache_data(ttl=86400)
def fetch_option_day(key, day_str):
    """Ek option ke ek trading din ke 1-minute candles (time, open, high, low, close, volume, oi)."""
    try:
        r = requests.get(f"https://api.upstox.com/v2/historical-candle/{enc(key)}/1minute/{day_str}/{day_str}", headers=HEADERS, timeout=20).json()
        cs = (r.get("data") or {}).get("candles") or []
        if not cs:
            return None
        names = ["time", "open", "high", "low", "close", "volume", "oi"]
        c = pd.DataFrame(cs).iloc[:, :len(names)]
        c.columns = names[:c.shape[1]]
        c["time"] = pd.to_datetime(c["time"], utc=True).dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
        if "oi" not in c.columns:
            c["oi"] = 0.0
        return c.sort_values("time").reset_index(drop=True)
    except Exception:
        return None


def build_past_chain(df, day, t_clock, n):
    """Us din ka option chain t_clock tak: LTP (last close), cumulative Volume, OI, OI Chg (din ki shuruaat se)."""
    d = df.sort_values("Strike").reset_index(drop=True)
    idx_c, _, idx_err = fetch_candles_for_day(inst_key, day)
    if idx_c.empty:
        return None, None, f"Index ka candle data nahi mila: {idx_err}"
    t = pd.Timestamp(datetime.combine(day, t_clock))
    sp = idx_c[idx_c["time"] <= t]
    spot_t = float(sp["close"].iloc[-1]) if not sp.empty else float(idx_c["open"].iloc[0])
    ai = int((d["Strike"] - spot_t).abs().idxmin())
    view = d.iloc[max(ai - n, 0): ai + n + 1].copy()
    day_str = day.strftime("%Y-%m-%d")
    keys = [k for k in list(view["Call Key"]) + list(view["Put Key"]) if isinstance(k, str) and k]
    hist = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        for k, h in zip(keys, ex.map(lambda k_: fetch_option_day(k_, day_str), keys)):
            hist[k] = h
    rows = []
    for _, r in view.iterrows():
        row = {"Strike": float(r["Strike"]), "Call IV": np.nan, "Put IV": np.nan}
        for side in ("Call", "Put"):
            h = hist.get(r.get(f"{side} Key"))
            ltp = oi = vol = oi_chg = 0.0
            if h is not None and not h.empty:
                upto = h[h["time"] <= t]
                if not upto.empty:
                    last = upto.iloc[-1]
                    ltp = float(last["close"])
                    oi = float(last["oi"])
                    vol = float(upto["volume"].sum())
                    oi_chg = oi - float(h["oi"].iloc[0])
            row[f"{side} LTP"] = ltp
            row[f"{side} OI"] = oi
            row[f"{side} Vol"] = vol
            row[f"{side} OI Chg"] = oi_chg
        rows.append(row)
    out = pd.DataFrame(rows)
    if out[["Call LTP", "Put LTP"]].abs().sum().sum() == 0:
        return None, spot_t, "Is samay tak option ka data nahi mila (expiry ya date check karein)."
    return out, spot_t, ""


def render_past_chain(df, n, day, t_clock):
    with st.spinner("Pichhle din ka option chain nikal raha hoon..."):
        pdf, spot_t, err = build_past_chain(df, day, t_clock, n)
    if pdf is None:
        st.warning(err or "Data nahi mila.")
        return
    st.caption(f"📅 {day:%d-%m-%Y} {t_clock:%H:%M} tak ka option chain (spot {spot_t:,.2f}). "
               "OI aur Volume us samay tak ke hain, OI Chg din ki shuruaat se. IV is view mein nahi hai (—).")
    body = build_table_body(pdf, spot_t, n, EMPTY_ANA, False, inst_name, None, {}, None)
    components.html(table_shell_html(), height=min(140 + (2 * n + 2) * 50, 1100), scrolling=True)
    components.html(push_html("table", {"html": body}), height=0)


def render_table(df, spot, n, ana, show_summary, label, height):
    components.html(table_shell_html(), height=height, scrolling=True)
    vm = st.session_state.get("vmatrix") or {}
    vm_txt = vm.get("label") if (vm and vm.get("inst") == inst_name and vm.get("exp") == expiry_date and not vm.get("error")) else None
    _iv = iv_max_info(df, spot, n)
    if _iv:
        vm_txt = " · ".join(x for x in [vm_txt, f"IV max {fs(_iv['strike'])} ({_iv['iv']:.1f}%)"] if x)
    components.html(push_html("table", {"html": build_table_body(df, spot, n, ana, show_summary, label, current_shift(), zone_marks(ana, df, spot), vm_txt)}), height=0)


def render_charts(df, spot, ana, n_strikes, height=440):
    mode = "price"          # mode aur timeframe ab chart ke toolbar (Price / OI / Vol / OB, 1m / 5m / 15m) se badalte hain
    tf = 5                  # zone test ke liye default timeframe
    is_hist = chart_day != date.today()
    if is_hist:
        candles, src, err = fetch_candles_for_day(inst_key, chart_day)
        if not candles.empty:
            candles = candles[candles["time"] <= pd.Timestamp(datetime.combine(chart_day, cur_past_t()))].reset_index(drop=True)
        st.caption(f"📅 {chart_day.strftime('%d-%m-%Y')} {cur_past_t():%H:%M} tak ka chart (candles, zones, OI us samay tak ke).")
    else:
        candles, src, err = fetch_candles(inst_key)
    if candles.empty:
        st.warning(
            "Candle data nahi mila, isliye sirf zones aur levels dikha raha hoon. "
            f"Upstox ka jawab: {err or 'khali'}"
        )
    price_sets, vol_sets = {}, {}
    for t_ in (1, 5, 15):
        if candles.empty:
            cdl = pd.DataFrame({"time": [pd.Timestamp("2000-01-01")], "open": [spot], "high": [spot],
                                "low": [spot], "close": [spot], "volume": [0]})
            xfmt, sig_ = "%H:%M", f"{inst_name}|fake|{t_}"
            br = []
        else:
            if src == "intraday":
                cdl, xfmt = resample_candles(candles, t_), "%H:%M"
                br_c = cdl
                br = breach_check(br_c, ana)
            else:
                cdl, xfmt = candles, "%d %b %H:%M"
                br = []
            sig_ = f"{inst_name}|{t_}|{src}|{len(br)}"
        if t_ == tf:
            st.session_state["breaches"] = br
        price_sets[str(t_)] = price_chart_data(cdl.tail(200), spot, ana, xfmt, sig_ + "|p", False, show_vol_zones, show_oi_zones, br, True)
        vol_sets[str(t_)] = price_chart_data(cdl.tail(200), spot, ana, xfmt, sig_ + "|v", False, True, False, br, False)
    oi_data = oi_chart_data(df, spot, min(n_strikes, 15), ana, inst_name, show_vol_zones, show_oi_zones)
    months_s, sw_on, bos_on = render_structure_controls()
    sp_, sv_ = structure_chart_sets_cached(inst_key, months_s, sw_on, bos_on)
    price_sets.update(sp_)
    vol_sets.update(sv_)
    with st.expander("📅 Structure events (SH/SL, BOS, CHoCH)", expanded=False):
        ev_df = structure_events_df(inst_key, months_s)
        if ev_df.empty:
            st.caption("Is range mein structure events nahi mile.")
        else:
            st.markdown(html_table(ev_df.head(40), _dark()), unsafe_allow_html=True)
            st.download_button("⬇️ Structure events CSV", ev_df.to_csv(index=False).encode("utf-8"),
                               file_name="structure_events.csv", mime="text/csv", key="dl_struct_ev")
    prev_mode = st.session_state.get("_cmode")
    send_mode = mode if prev_mode != mode else None
    st.session_state["_cmode"] = mode
    components.html(zoom_shell_html("price", "-main"), height=height, scrolling=True)
    components.html(push_html("price-main", {"price": price_sets, "vol": vol_sets, "oi": oi_data, "mode": send_mode}), height=0)
    zb_c1, zb_c2 = st.columns(2)
    if zb_c2.button("📊 Zone cards dekho / chhupao"):
        st.session_state["zc_show"] = not st.session_state.get("zc_show", False)
    if zb_c1.button("📊 Zone price test (aaj ke candles par)"):
        st.session_state["zbt"] = {"inst": inst_name, "rows": zone_backtest(candles, ana, 12), "tf": tf}
    zb = st.session_state.get("zbt")
    if zb and zb["inst"] == inst_name:
        if zb["rows"]:
            st.markdown(zone_test_table_html(zb["rows"]), unsafe_allow_html=True)
            st.caption(f"{zb['tf']} min candles par, zone mein aane ke baad aage 12 candles dekhe gaye. "
                       "Ruka = zone se wapas palta. Toota = 2 candle lagatar zone ke bahar. "
                       "Sample chhota hai, isliye ye sirf ek jhalak hai, pakka saboot nahi.")
        else:
            st.info("Test ke liye candles ya zone kam hain.")


# ---------------- Page ----------------
def cur_past_t():
    return st.session_state.get("past_t", dt_time(11, 0))


def _shift_past(delta):
    base = datetime.combine(date.today(), cur_past_t()) + timedelta(minutes=delta)
    lo_ = datetime.combine(date.today(), dt_time(9, 15))
    hi_ = datetime.combine(date.today(), dt_time(15, 30))
    st.session_state["past_t"] = min(max(base, lo_), hi_).time()


def _toggle_play():
    st.session_state["play_on"] = not st.session_state.get("play_on", False)


def _advance_play():
    """Play on ho to ek minute aage; 15:30 par ruk jaye."""
    if cur_past_t() >= dt_time(15, 30):
        st.session_state["play_on"] = False
        return
    _shift_past(1)


INDEX_SCAN_ALIASES = {
    "NIFTY": "Nifty 50", "NIFTY 50": "Nifty 50", "NIFTY50": "Nifty 50",
    "BANKNIFTY": "Bank Nifty", "BANK NIFTY": "Bank Nifty", "NIFTY BANK": "Bank Nifty",
    "FINNIFTY": "Fin Nifty", "FIN NIFTY": "Fin Nifty",
    "MIDCPNIFTY": "Midcap Nifty", "MIDCAP NIFTY": "Midcap Nifty",
    "NIFTY NEXT 50": "Nifty Next 50", "SENSEX": "Sensex", "BANKEX": "Bankex",
}


def scan_key_for(sym):
    """Index naam ho to uski direct key; warna stock (NSE EQ) ki key."""
    name = INDEX_SCAN_ALIASES.get(sym.upper())
    if name and name in INDEXES:
        return INDEXES[name]
    return resolve_stock(sym)


def _alert_list():
    return st.session_state.setdefault("alerts", [])


def check_alert(a, spot):
    """(hit, near): hit = level paar hua; near = level ke tol% ke andar, abhi paar nahi."""
    lvl = a["level"]
    tol = lvl * a["tol"] / 100.0
    if a["dir"] == "up":
        hit = spot >= lvl
        near = (not hit) and spot >= lvl - tol
    else:
        hit = spot <= lvl
        near = (not hit) and spot <= lvl + tol
    return hit, near


def render_alert_banner(spot, inst):
    """Page par active alerts ka banner (live spot se)."""
    for a in _alert_list():
        if a["inst"] != inst:
            continue
        hit, near = check_alert(a, spot)
        dir_txt = "upar" if a["dir"] == "up" else "neeche"
        if hit:
            st.warning(f"🔔 {a['name']} ({a['level']:,.2f}) {dir_txt} hit ho gaya. LTP {spot:,.2f}")
        elif near:
            st.info(f"⚠️ {a['name']} ({a['level']:,.2f}) ke paas hai. LTP {spot:,.2f}, {a['tol']}% ke andar")


def _del_alert(aid):
    st.session_state["alerts"] = [a for a in _alert_list() if a["id"] != aid]


def _add_alert(name, level, direction, tol, inst):
    _alert_list().append({"id": int(time.time() * 1000), "inst": inst, "name": name,
                          "level": float(level), "dir": direction, "tol": float(tol)})


def render_alert_panel():
    st.markdown("---")
    st.subheader("🔔 Price alerts")
    st.caption("Alert sirf tab dikhega jab ye app khula ho aur page refresh ho. Phone notification nahi bhejta. "
               "Reboot ya browser band hone par alerts khatam ho jate hain.")
    lv = scan_levels(inst_key) or {}
    opts = list(lv.keys()) + ["Manual"]
    c1, c2, c3 = st.columns([1.4, 1, 1])
    pick = c1.selectbox("Level", opts, key="al_pick")
    if pick == "Manual":
        price = c2.number_input("Price", min_value=0.0, value=0.0, step=1.0, key="al_price")
    else:
        price = float(lv[pick])
        c2.metric("Level", f"{price:,.2f}")
    dir_pick = c3.selectbox("Jab", ["upar jaaye", "neeche jaaye"], key="al_dir")
    tol = st.slider("Paas ka matlab (%)", 0.1, 1.0, 0.3, 0.1, key="al_tol")
    if st.button("➕ Alert add karein"):
        if price and price > 0:
            _add_alert(pick, price, "up" if dir_pick == "upar jaaye" else "down", tol, inst_name)
            st.success(f"Alert add ho gaya: {pick} {price:,.2f} {dir_pick}")
        else:
            st.warning("Price 0 se zyada daalein.")
    mine = [a for a in _alert_list() if a["inst"] == inst_name]
    if mine:
        st.markdown(f"**Active alerts ({inst_name})**")
        for a in mine:
            cc1, cc2 = st.columns([5, 1])
            cc1.write(f"{a['name']}: {a['level']:,.2f} {'upar' if a['dir'] == 'up' else 'neeche'} (paas {a['tol']}%)")
            cc2.button("❌", key=f"al_del_{a['id']}", on_click=_del_alert, args=(a["id"],))
    else:
        st.caption("Is instrument ke liye koi alert nahi.")


def render_page():
    df, spot = fetch_option_chain(inst_key, expiry_date)
    if not df.empty and spot:
        render_alert_banner(spot, inst_name)
    is_past = chart_day != date.today()
    if is_past and st.session_state.get("play_on"):
        _advance_play()
    if is_past and not df.empty:
        pdf, pspot, perr = build_past_chain(df, chart_day, cur_past_t(), n_strikes)
        if pdf is None:
            st.warning(perr or "Is samay ka data nahi mila.")
            return
        df, spot = pdf, pspot

    if df.empty:
        st.warning(f"⚠️ {inst_name} ka data load nahi hua! Upstox Access Token check karein. Stock ho to uske F&O options na hon ya symbol badal gaya ho to bhi data nahi aata.")
    else:
        zp_state = st.session_state.get("zone_prev") or {}
        prev_z = zp_state.get("z") if (zp_state.get("inst") == inst_name and zp_state.get("exp") == expiry_date) else None
        ana = analyze(df, spot, zone_pts, prev_z)
        st.session_state["zone_prev"] = {
            "inst": inst_name, "exp": expiry_date,
            "z": {f"{b_}_{sd}": ana["zone_sets"][b_][sd][0]["strike"]
                  for b_ in ("vol", "oi") for sd in ("supply", "demand") if ana["zone_sets"][b_][sd]},
        }
        supply, demand = ana["supply"], ana["demand"]

        if focus_mode:
            st.markdown("<style>.block-container{padding-top:0.3rem !important;padding-bottom:0 !important;}.stApp h1,.stApp [data-testid=stCaptionContainer]{display:none !important;}</style>", unsafe_allow_html=True)
            st.caption(f"{inst_name} Spot {spot:,.2f} | Expiry {expiry_date} | PCR {ana['pcr']:.2f}")
            render_table(df, spot, n_strikes, ana, show_summary, inst_name, 780)
            return

        if chart_focus:
            st.markdown("<style>.block-container{padding-top:0.3rem !important;padding-bottom:0 !important;}.stApp h1,.stApp [data-testid=stCaptionContainer]{display:none !important;}</style>", unsafe_allow_html=True)
            st.caption(f"{inst_name} Spot {spot:,.2f} | Expiry {expiry_date} | Bias {ana['bias']}")
            render_charts(df, spot, ana, n_strikes, height=780)
            return

        # ---- Smart Analysis ----
        st.markdown("---")
        st.subheader("🧠 Smart Analysis – Supply / Demand Zone (OI + Volume based)")

        bias_col = "#dcfce7" if "BULL" in ana["bias"] else "#fee2e2" if "BEAR" in ana["bias"] else "#fef9c3"
        _br = st.session_state.get("breaches") or []
        if _br:
            st.markdown(breach_banner_html(_br), unsafe_allow_html=True)
            _rv = st.session_state.get("rv") or {}
            _rv = _rv if (_rv.get("inst") == inst_name and _rv.get("exp") == expiry_date and not _rv.get("error")) else None
            _step = float(pd.Series(sorted(df["Strike"].astype(float).unique())).diff().dropna().min() or 50.0)
            _alert = volatility_zone_alert(_rv, iv_max_info(df, spot, n_strikes), _br, _step)
            if _alert:
                st.warning(_alert)
        st.markdown(
            f'<div style="background:{bias_col};color:#111;padding:14px;border-radius:10px;font-size:18px;">'
            f'<b>Market Bias: {ana["bias"]}</b> &nbsp;|&nbsp; Score: {ana["points"]:+d} &nbsp;|&nbsp; PCR: {ana["pcr"]:.2f}'
            f' &nbsp;|&nbsp; Spot: {spot:,.2f}</div>',
            unsafe_allow_html=True,
        )
        st.write("")

        bc1, bc2, bc3, bc4 = st.columns(4)
        pr_click = bc1.button("🧭 Pressure matrix (9:17 se ab tak)")
        vm_click = bc2.button("📋 Volume matrix (9:17 se ab tak)")
        rv_click = bc3.button("📈 Volatility (9:17 se ab tak)")
        ai_click = bc4.button("🤖 AI summary (Gemini / Claude)")
        if rv_click and not is_past:
            with st.spinner("Volatility nikal raha hoon..."):
                st.session_state["rv"] = {"inst": inst_name, "exp": expiry_date, **build_rv(df, spot, n_strikes)}
        rv = st.session_state.get("rv")
        if rv and rv.get("inst") == inst_name and rv.get("exp") == expiry_date:
            if rv.get("error"):
                st.warning(rv["error"])
            else:
                top3 = rv["table"].head(3)
                st.markdown("📈 **Realized volatility** (9:17–" + rv["end_label"] + ") · sabse zyada: " +
                            " | ".join(f"{fs(r['Strike'])} {r['Side']} {r['RV %']:.2f}%" for _, r in top3.iterrows()))
                with st.expander("📈 Volatility table (top 10)", expanded=True):
                    st.markdown(html_table(rv["table"].head(10), _dark()), unsafe_allow_html=True)
                    st.download_button("⬇️ Volatility CSV", rv["table"].to_csv(index=False).encode("utf-8"),
                                       file_name="volatility.csv", mime="text/csv", key="dl_rv")
        if pr_click and not is_past:
            with st.spinner("Pressure nikal raha hoon (option ki history)..."):
                st.session_state["pressure"] = {"inst": inst_name, "exp": expiry_date,
                                                **build_pressure_full(df, spot, n_strikes, ana)}
        pr = st.session_state.get("pressure")
        same = bool(pr) and pr.get("inst") == inst_name and pr.get("exp") == expiry_date
        if same and pr.get("error"):
            st.warning(pr["error"])
        elif same:
            with st.expander("🧭 Pressure matrix", expanded=True):
                st.markdown(f'<div style="background:#f5f3ff;color:#111;padding:10px;border-radius:8px">{pressure_html(pr)}</div>',
                            unsafe_allow_html=True)
                if pr["alert"]:
                    st.error("⚠️ Pressure result BEARISH hai. Chart par support zone par alert dikhega.")
        if vm_click and not is_past:
            with st.spinner("Volume trend nikal raha hoon..."):
                st.session_state["vmatrix"] = {"inst": inst_name, "exp": expiry_date,
                                               **build_volume_matrix(df, spot, n_strikes, ana)}
        vm = st.session_state.get("vmatrix")
        if vm and vm.get("inst") == inst_name and vm.get("exp") == expiry_date:
            if vm.get("error"):
                st.warning(vm["error"])
            else:
                with st.expander("📋 Volume matrix", expanded=True):
                    st.markdown(f'<div style="background:#ecfdf5;color:#111;padding:10px;border-radius:8px">{volume_matrix_html(vm)}</div>',
                                unsafe_allow_html=True)
        if ai_click:
            summary = {"instrument": inst_name, "spot": spot, "expiry": expiry_date, "bias": ana["bias"],
                       "pcr": round(ana["pcr"], 2), "max_pain": ana["max_pain"], "zone_width_points": ana["zone_width"],
                       "volume_zones": ana["zone_sets"]["vol"], "oi_zones": ana["zone_sets"]["oi"],
                       "liquidity_strikes": ana["liq"]}
            with st.spinner("AI analysis ho rahi hai..."):
                text, err = ask_ai(json.dumps(summary, default=float))
            st.session_state["ai_out"] = (inst_name, "warn" if err else "ok", err or text)
        ai_out = st.session_state.get("ai_out")
        if ai_out and ai_out[0] == inst_name:
            (st.warning if ai_out[1] == "warn" else st.markdown)(ai_out[2])
        ana["pressure_alert"] = pr["support_strike"] if (same and not pr.get("error") and pr.get("alert")) else None
        # ---- Table ----
        st.markdown("---")
        st.subheader("📋 Complete Option Chain Matrix")
        _box = st.container(border=True)
        with _box:
            sc1, sc2, sc3 = st.columns([1, 1.4, 0.7])
            cutoff_t = sc1.time_input("Samay", value=dt_time(9, 20), step=60, label_visibility="collapsed", help="Isse pehle ka data 'purana' mana jayega")
            if sc2.button("🔀 Shifting dekho", disabled=is_past):
                with st.spinner("Option ki history aa rahi hai (kuch second lagte hain)..."):
                    res = build_shift(df, spot, n_strikes, cutoff_t)
                st.session_state["shift"] = {"inst": inst_name, "exp": expiry_date, **res}
            if current_shift() and sc3.button("❌ Hatao"):
                st.session_state["shift"] = None
        sh_state = st.session_state.get("shift")
        if sh_state and sh_state.get("inst") == inst_name and sh_state.get("exp") == expiry_date:
            if sh_state.get("error"):
                st.warning(sh_state["error"])
            else:
                st.caption(f"🔀 Shifting {sh_state['cut']} se {sh_state['asof']} tak ki (option chain ke upar CALLS/PUTS mein dikh rahi hai). "
                           f"{sh_state['n_ok']}/{sh_state['n_all']} options ki history mili. Naya dekhne ke liye button dobara dabayein.")
        if is_past:
            pb1, pb2, pb3, pb4 = st.columns([1, 1, 1.4, 1.6])
            pb1.button("⏮ 1 min", on_click=_shift_past, args=(-1,))
            pb2.button("⏭ 1 min", on_click=_shift_past, args=(1,))
            pb3.button("⏸ Stop" if st.session_state.get("play_on") else "▶ Play", on_click=_toggle_play)
            pb4.selectbox("Speed (sec/min)", [1, 2, 3, 5], index=2, key="play_secs")
            st.caption(f"📅 {chart_day:%d-%m-%Y} · {cur_past_t():%H:%M} tak (pichhla data)")
        render_table(df, spot, n_strikes, ana, show_summary, inst_name, min(140 + (2 * n_strikes + 2) * 50, 1100))

        # ---- Charts with Supply / Demand zones ----
        st.markdown("---")
        st.subheader("📈 Charts – Supply / Demand Zones")
        render_charts(df, spot, ana, n_strikes)

        def zone_card(title, zs, side, bg, border):
            html = (f'<div style="background:{bg};color:#111;border-left:6px solid {border};padding:10px;'
                    f'border-radius:8px;margin-bottom:6px"><b>{title}</b><br>')
            if not zs:
                return html + 'Zone nahi mila</div>'
            for z in zs:
                p = z["primary"]
                other = ana["zone_sets"]["oi" if z["basis"] == "vol" else "vol"][side]
                both = any(abs(float(o["strike"]) - float(z["strike"])) < z["width"] for o in other)
                html += (
                    f'{"💧 " if z["rank"] == 2 else ""}<b>Zone {z["rank"]}:</b> '
                    f'<span style="font-size:18px;font-weight:800">{fs(z["low"])} – {fs(z["high"])}</span> '
                    f'(strike {p["strike"]}, {pct_s(z["pct"])})<br>'
                    f'📏 {zone_size_txt(z)} • Spot se {zone_dist_txt(z, side)}<br>'
                    f'OI {p["oi"] / 1e5:.1f}L • Chg {p["chg"] / 1e5:+.1f}L • Vol {fmt_vol(p["vol"])}<br>'
                    + ('⭐ OI aur Volume dono ka zone yahin<br>' if both else '')
                )
            return html + '</div>'

        if st.session_state.get("zc_show"):
            zs_ = ana["zone_sets"]
            st.markdown("**📊 Volume ke hisaab se zone**")
            va, vb = st.columns(2)
            va.markdown(zone_card("🔴 SUPPLY (Call Volume)", zs_["vol"]["supply"], "supply", "#fff1f2", "#9f1239"), unsafe_allow_html=True)
            vb.markdown(zone_card("🟢 DEMAND (Put Volume)", zs_["vol"]["demand"], "demand", "#f7fee7", "#4d7c0f"), unsafe_allow_html=True)
            st.markdown("**📈 OI ke hisaab se zone**")
            oa, ob = st.columns(2)
            oa.markdown(zone_card("🔴 SUPPLY (Call OI)", zs_["oi"]["supply"], "supply", "#fef2f2", "#ef4444"), unsafe_allow_html=True)
            ob.markdown(zone_card("🟢 DEMAND (Put OI)", zs_["oi"]["demand"], "demand", "#f0fdf4", "#16a34a"), unsafe_allow_html=True)


SCAN_NEAR_PCT = 0.3


@st.cache_data(ttl=120)
def scan_candles(inst_key):
    c, src, err = fetch_candles(inst_key)
    if c is None or c.empty:
        return None
    if src == "intraday":
        c = resample_candles(c, 5)
    return c


@st.cache_data(ttl=600)
def fetch_hist_range(inst_key, interval, start_d, end_d):
    """Upstox historical-candle (day / 30minute) ek range ke liye."""
    key = enc(inst_key)
    try:
        r = requests.get(f"https://api.upstox.com/v2/historical-candle/{key}/{interval}/{end_d:%Y-%m-%d}/{start_d:%Y-%m-%d}",
                         headers=HEADERS, timeout=20).json()
        cs = (r.get("data") or {}).get("candles") or []
        if not cs:
            return pd.DataFrame()
        c = pd.DataFrame(cs).iloc[:, :6]
        c.columns = ["time", "open", "high", "low", "close", "volume"]
        c["time"] = pd.to_datetime(c["time"], utc=True).dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
        return c.sort_values("time").reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def scan_levels(inst_key):
    """5-din high/low, pichhle din high/low, aur 4-ghante (30-min se) ka latest high/low."""
    today = date.today()
    out = {}
    d = fetch_hist_range(inst_key, "day", today - timedelta(days=12), today)
    if not d.empty:
        d = d[d["time"].dt.date < today]
        if len(d):
            last5 = d.tail(5)
            out["5D High"] = float(last5["high"].max())
            out["5D Low"] = float(last5["low"].min())
            out["Prev High"] = float(d["high"].iloc[-1])
            out["Prev Low"] = float(d["low"].iloc[-1])
    m = fetch_hist_range(inst_key, "30minute", today - timedelta(days=4), today)
    if not m.empty:
        m4 = m.set_index("time").resample("4h", origin="start_day", offset="9h15min").agg({"high": "max", "low": "min"}).dropna()
        if len(m4):
            out["4H High"] = float(m4["high"].iloc[-1])
            out["4H Low"] = float(m4["low"].iloc[-1])
    return out


def level_note(ltp, levels):
    """Har level ke mukable price: upar toota / neeche toota / paas (0.3% ke andar)."""
    notes = []
    for name, val in levels.items():
        if val is None or val != val:
            continue
        pct = (ltp - val) / val * 100
        if abs(pct) <= SCAN_NEAR_PCT:
            notes.append(f"{name} paas")
        elif pct > 0 and ("High" in name or "H" in name.split()[-1]):
            notes.append(f"{name} ke upar")
        elif pct < 0 and ("Low" in name or "L" in name.split()[-1]):
            notes.append(f"{name} ke neeche")
    return "; ".join(notes) if notes else "—"


def scan_stock(sym, key=None):
    """Ek stock: pichhle 20 candles ka high/low; status BREAKOUT / BREAKDOWN / paas / Range."""
    if key is None:
        key = resolve_stock(sym)
    if not key:
        return None
    c = scan_candles(key)
    if c is None or len(c) < 22:
        return None
    h = c["high"].astype(float).values
    l = c["low"].astype(float).values
    cl = c["close"].astype(float).values
    v = c["volume"].astype(float).values if "volume" in c.columns else np.ones(len(c))
    ltp = float(cl[-1])
    hi = float(h[-21:-1].max())
    lo = float(l[-21:-1].min())
    up_pct = (hi - ltp) / ltp * 100
    dn_pct = (ltp - lo) / ltp * 100
    if ltp > hi:
        status = "BREAKOUT"
    elif ltp < lo:
        status = "BREAKDOWN"
    elif up_pct <= SCAN_NEAR_PCT:
        status = "Breakout ke paas"
    elif dn_pct <= SCAN_NEAR_PCT:
        status = "Breakdown ke paas"
    else:
        status = "Range"
    base = float(v[-25:-5].mean()) if len(v) >= 25 else 0.0
    vol_x = float(v[-5:].mean()) / base if base > 0 else float("nan")
    chg = (ltp - float(cl[-2])) / float(cl[-2]) * 100
    # aakhri breakout/breakdown candle: uska time aur price = entry
    ev_type, ev_time, ev_px = None, None, None
    has_t = "time" in c.columns
    for i in range(21, len(cl)):
        hi_i = float(h[i - 20:i].max())
        lo_i = float(l[i - 20:i].min())
        if cl[i] > hi_i:
            ev_type, ev_px = "BREAKOUT", float(cl[i])
            ev_time = pd.Timestamp(c["time"].iloc[i]).strftime("%H:%M") if has_t else "—"
        elif cl[i] < lo_i:
            ev_type, ev_px = "BREAKDOWN", float(cl[i])
            ev_time = pd.Timestamp(c["time"].iloc[i]).strftime("%H:%M") if has_t else "—"
    if ev_type:
        since = (ltp - ev_px) / ev_px * 100 * (1 if ev_type == "BREAKOUT" else -1)
        entry_txt = {"Signal": ev_type, "Signal time": ev_time, "Entry price": round(ev_px, 2), "Entry se %": round(since, 2)}
    else:
        entry_txt = {"Signal": "—", "Signal time": "—", "Entry price": None, "Entry se %": None}
    levels = dict(scan_levels(key) or {})
    levels["Day High"] = float(h.max())
    levels["Day Low"] = float(l.min())
    lv_cols = {k: (round(levels[k], 2) if k in levels else None) for k in
               ["5D High", "5D Low", "Prev High", "Prev Low", "4H High", "4H Low", "Day High", "Day Low"]}
    return {"Stock": sym, "LTP": round(ltp, 2), "Chg %": round(chg, 2),
            "Resistance (20)": round(hi, 2), "Support (20)": round(lo, 2),
            "Status": status, "Vol x": (round(vol_x, 2) if vol_x == vol_x else None), **entry_txt,
            **lv_cols, "Level note": level_note(ltp, levels)}


def daily_structure(d, pivot=2, keep=4):
    """Daily price structure: swing high/low (support/resistance), BOS (breakout / breakdown), CHoCH (reversal)."""
    d = d.reset_index(drop=True)
    h = d["high"].astype(float).values
    l = d["low"].astype(float).values
    cl = d["close"].astype(float).values
    tm = d["time"]
    n = len(d)
    sh, sl = {}, {}
    for k in range(pivot, n - pivot):
        if h[k] == max(h[k - pivot:k + pivot + 1]):
            sh[k] = float(h[k])
        if l[k] == min(l[k - pivot:k + pivot + 1]):
            sl[k] = float(l[k])
    events, bos_lines = [], []
    trend, last_sh, last_sl = None, None, None
    for j in range(n):
        k = j - pivot
        if k in sh:
            last_sh = sh[k]
        if k in sl:
            last_sl = sl[k]
        if last_sh is not None and cl[j] > last_sh:
            kind = "CHoCH UP (reversal)" if trend == "down" else "BOS UP (breakout)"
            trend = "up"
            events.append((tm.iloc[j], kind, float(cl[j])))
            bos_lines.append((kind, last_sh))
            last_sh = None
        if last_sl is not None and cl[j] < last_sl:
            kind = "CHoCH DOWN (reversal)" if trend == "up" else "BOS DOWN (breakdown)"
            trend = "down"
            events.append((tm.iloc[j], kind, float(cl[j])))
            bos_lines.append((kind, last_sl))
            last_sl = None
    lines = []
    for k in sorted(sh)[-keep:]:
        lines.append({"lab": f"SH {sh[k]:,.1f}", "val": sh[k], "color": "#94a3b8", "dash": "2 3"})
        events.append((tm.iloc[k], "Swing High", sh[k]))
    for k in sorted(sl)[-keep:]:
        lines.append({"lab": f"SL {sl[k]:,.1f}", "val": sl[k], "color": "#94a3b8", "dash": "2 3"})
        events.append((tm.iloc[k], "Swing Low", sl[k]))
    for kind, lv in bos_lines[-3:]:
        if "CHoCH UP" in kind:
            lab, col = f"Reversal UP {lv:,.1f}", "#16a34a"
        elif "CHoCH DOWN" in kind:
            lab, col = f"Reversal DOWN {lv:,.1f}", "#dc2626"
        elif "BOS UP" in kind:
            lab, col = f"Breakout {lv:,.1f}", "#16a34a"
        else:
            lab, col = f"Breakdown {lv:,.1f}", "#dc2626"
        lines.append({"lab": lab, "val": lv, "color": col, "dash": "5 4"})
    return [], lines, events


def _set_struct(key, val):
    st.session_state[key] = val


def _flip_struct(key):
    st.session_state[key] = not st.session_state.get(key, True)


@st.cache_data(ttl=600)
def structure_events_df(inst_key, months):
    """1 दिन aur 1 घंटा ke SH/SL, BOS, CHoCH events ek table mein (latest pehle)."""
    today = date.today()
    start = today - timedelta(days=31 * months + 5)
    out = []
    d = fetch_hist_range(inst_key, "day", start, today)
    if not d.empty:
        _z, _l, ev = daily_structure(d, pivot=2, keep=4)
        out += [(t_, "1 दिन", k_, p_) for t_, k_, p_ in ev]
    m = fetch_hist_range(inst_key, "30minute", start, today)
    if not m.empty:
        h1 = m.set_index("time").resample("60min", origin="start_day", offset="9h15min").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna().reset_index()
        if not h1.empty:
            _z, _l, ev = daily_structure(h1, pivot=3, keep=4)
            out += [(t_, "1 घंटा", k_, p_) for t_, k_, p_ in ev]
    if not out:
        return pd.DataFrame()
    df = pd.DataFrame(out, columns=["Time", "TF", "Event", "Price"])
    df["Time"] = pd.to_datetime(df["Time"])
    df = df.sort_values("Time", ascending=False).reset_index(drop=True)
    df["Time"] = df["Time"].dt.strftime("%d-%m-%Y %H:%M")
    df["Price"] = df["Price"].round(2)
    return df


def render_structure_controls():
    """Chart ke upar: range (1M/2M/4M) aur structure lines ke toggles. 1H / 1D buttons chart ke toolbar mein hain."""
    st.session_state.setdefault("struct_months", 2)
    st.session_state.setdefault("struct_sw", True)
    st.session_state.setdefault("struct_bos", True)
    months = st.session_state["struct_months"]
    sw_on, bos_on = st.session_state["struct_sw"], st.session_state["struct_bos"]
    b3, b4, b5, t1, t2 = st.columns(5)
    b3.button(("✅ " if months == 1 else "") + "1M", on_click=_set_struct, args=("struct_months", 1), key="st_m1")
    b4.button(("✅ " if months == 2 else "") + "2M", on_click=_set_struct, args=("struct_months", 2), key="st_m2")
    b5.button(("✅ " if months == 4 else "") + "4M", on_click=_set_struct, args=("struct_months", 4), key="st_m4")
    t1.button(("✅ " if sw_on else "⬜ ") + "SH/SL", on_click=_flip_struct, args=("struct_sw",), key="st_sw")
    t2.button(("✅ " if bos_on else "⬜ ") + "BO/Rev", on_click=_flip_struct, args=("struct_bos",), key="st_bos")
    return months, sw_on, bos_on


def _struct_filter(lines, sw_on, bos_on):
    out = []
    for l_ in lines:
        is_sw = l_["lab"].startswith(("SH", "SL"))
        if (is_sw and sw_on) or ((not is_sw) and bos_on):
            out.append(l_)
    return out


@st.cache_data(ttl=300)
def structure_chart_sets_cached(inst_key_, months, sw_on, bos_on):
    """Structure chart ke price/volume sets: 5 minute cache (har rerun par dobara na banein)."""
    return structure_chart_sets(months, sw_on, bos_on)


def structure_chart_sets(months, sw_on, bos_on):
    """1D (key 1440) aur 1H (key 60) ka structure data, same chart ke liye."""
    today = date.today()
    start = today - timedelta(days=31 * months + 5)
    out_p, out_v = {}, {}
    d = fetch_hist_range(inst_key, "day", start, today)
    if not d.empty:
        zones, lines, _ev = daily_structure(d, pivot=2, keep=4)
        data = price_chart_data(d, float(d["close"].iloc[-1]), EMPTY_ANA, "%d %b", f"sD{months}{sw_on}{bos_on}", True, False, False, [], False,
                                extra={"zones": zones, "lines": _struct_filter(lines, sw_on, bos_on)})
        out_p["1440"] = data
        out_v["1440"] = data
    m = fetch_hist_range(inst_key, "30minute", start, today)
    if not m.empty:
        h1 = m.set_index("time").resample("60min", origin="start_day", offset="9h15min").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna().reset_index()
        if not h1.empty:
            zones, lines, _ev = daily_structure(h1, pivot=3, keep=4)
            data = price_chart_data(h1, float(h1["close"].iloc[-1]), EMPTY_ANA, "%d %b %H:%M", f"sH{months}{sw_on}{bos_on}", True, False, False, [], False,
                                    extra={"zones": zones, "lines": _struct_filter(lines, sw_on, bos_on)})
            out_p["60"] = data
            out_v["60"] = data
    return out_p, out_v


def html_table(df, dark):
    """Theme-aware HTML table (st.dataframe Streamlit ke system theme se chalta hai, isliye ye use karte hain)."""
    import html as _h
    fg = "#e5e7eb" if dark else "#111827"
    head_bg = "#1e293b" if dark else "#eef2f7"
    line = "#334155" if dark else "#e5e7eb"
    def cell(v):
        if v is None or (isinstance(v, float) and v != v):
            return "—"
        if isinstance(v, float):
            return f"{v:,.2f}"
        return _h.escape(str(v))
    head = "".join(f"<th style='padding:5px 6px;text-align:right;background:{head_bg};font-size:11px;"
                   f"border-bottom:1px solid {line}'>{_h.escape(str(c))}</th>" for c in df.columns)
    rows = []
    for _, r in df.iterrows():
        tds = "".join(f"<td style='padding:5px 6px;text-align:right;border-bottom:1px solid {line}'>{cell(v)}</td>" for v in r.values)
        rows.append(f"<tr>{tds}</tr>")
    return (f"<div style='overflow-x:auto;color:{fg}'><table style='width:100%;border-collapse:collapse;font-size:12px;color:{fg}'>"
            f"<thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>")


@st.cache_data(ttl=120)
def run_scan(pairs):
    """Poora scan ek hi baar (120 second cache). pairs = ((symbol, instrument_key), ...); keys bahar se aati hain."""
    rows = []
    for sym, key in pairs:
        try:
            r = scan_stock(sym, key)
        except Exception:
            r = None
        if r:
            rows.append(r)
    return rows


def render_scanner():
    st.markdown("---")
    st.subheader("🔎 Stock Scanner: breakout / breakdown")
    st.caption("Har stock ke aaj ke 5-minute candles par: pichhle 20 candles ka high (resistance) aur low (support). "
               "BREAKOUT = price high ke upar band, BREAKDOWN = low ke neeche band. 'Paas' = 0.3% ke andar. "
               "Signal time = aakhri breakout/breakdown candle ka time, Entry price = us candle ka close. "
               "Entry se % = entry se ab tak ka move (breakdown par ulta). 5D = pichhle 5 din, Prev = pichhla din, 4H = 4-ghante bar. "
               "Level note = price kis level ke paas / upar / neeche hai. Ye data hai, trade ki salah nahi.")
    txt = st.text_area("Stocks (comma se, jaise RELIANCE, TCS, INFY). 50 ya poori F&O list bhi paste kar sakte hain.",
                       value=", ".join(["NIFTY 50"] + STOCKS), height=110, key="scan_syms")
    syms = []
    for x in txt.replace("\n", ",").split(","):
        x = x.strip().upper()
        if x and x not in syms:
            syms.append(x)
    st.caption(f"{len(syms)} stock chune gaye. Har stock par 3-4 API calls lagti hain, isliye bade list mein time lag sakta hai.")
    if st.button("🔍 Scan chalao"):
        st.session_state["scan_on"] = True
    if not st.session_state.get("scan_on"):
        return
    with st.spinner("Scan ho raha hai (pehli baar kuch second lagenge, phir cache se fast)..."):
        pairs = tuple((sym, scan_key_for(sym)) for sym in syms)
        rows = run_scan(pairs)
    if not rows:
        st.warning("Koi stock ka data nahi mila. Token ya market hours check karein.")
        return
    sdf = pd.DataFrame(rows)
    groups = [("🚀 BREAKOUT (abhi toota)", "BREAKOUT"),
              ("⚠️ Breakout ke paas", "Breakout ke paas"),
              ("🔻 BREAKDOWN (abhi toota)", "BREAKDOWN"),
              ("🟠 Breakdown ke paas", "Breakdown ke paas")]
    for title, status in groups:
        part = sdf[sdf["Status"] == status].sort_values("Vol x", ascending=False)
        with st.expander(f"{title} · {len(part)} stock", expanded=(len(part) > 0 and status in ("BREAKOUT", "BREAKDOWN"))):
            if len(part):
                st.markdown(html_table(part, _dark()), unsafe_allow_html=True)
            else:
                st.caption("Koi nahi.")
    st.download_button("⬇️ Scanner CSV (sab stock)", sdf.to_csv(index=False).encode("utf-8"),
                       file_name="scanner.csv", mime="text/csv", key="dl_scan")


# Auto refresh: sirf data wala hissa dobara bante hai (fragment), poora page nahi, isliye screen smooth rehti hai
if auto_refresh and hasattr(st, "fragment"):
    st.fragment(run_every=f"{refresh_secs}s")(render_page)()
elif st.session_state.get("play_on") and hasattr(st, "fragment"):
    st.fragment(run_every=f"{int(st.session_state.get('play_secs', 3))}s")(render_page)()
else:
    render_page()
    if auto_refresh:                      # purane Streamlit version ke liye
        time.sleep(refresh_secs)
        st.rerun()


render_scanner()


render_alert_panel()
