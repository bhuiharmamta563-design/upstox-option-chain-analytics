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
from datetime import date, timedelta
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
[data-testid=stHeader], [data-testid=stToolbar] {background:#ffffff !important;}
[data-testid=stToolbar] *, [data-testid=stHeader] * {color:#111111 !important;}
[data-testid=stToolbar] svg, [data-testid=stHeader] svg {fill:#111111 !important;stroke:#111111 !important;}
[data-testid=stButton] button, [data-testid=stBaseButton-secondary] {background:#ffffff !important;color:#111111 !important;border:1px solid #d1d5db !important;}
[data-testid=stButton] button:hover {border-color:#2563eb !important;color:#2563eb !important;}
[data-baseweb=popover] ul, [data-baseweb=menu], [data-baseweb=popover] li {background:#ffffff !important;color:#111111 !important;}
[data-testid=stTickBarMin], [data-testid=stTickBarMax], [data-testid=stTickBar] {color:#374151 !important;}
[data-testid=stRadio] label div p, [data-testid=stCheckbox] label p {color:#111111 !important;}
</style>"""
theme_pick = st.sidebar.radio("Theme", ["🌙 Dark", "☀️ Light"], horizontal=True, index=0)
st.session_state["theme_dark"] = theme_pick.startswith("🌙")
st.markdown(PAGE_DARK if st.session_state["theme_dark"] else PAGE_LIGHT, unsafe_allow_html=True)
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
zone_pts = st.sidebar.number_input("Zone ki chaudai (points, 0 = auto)", min_value=0.0, value=0.0, step=5.0,
                                   help="0 = auto: spot ka 0.16% (Nifty par lagbhag 40 points, BankNifty ~83, Sensex ~130). Apni marzi ke points bhi likh sakte hain. Sab zone isi chaudai ke hote hain.")
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


def analyze(df, spot, zone_pts=0.0):
    d = df.sort_values("Strike").reset_index(drop=True).copy()
    diffs = np.diff(d["Strike"].astype(float).values)
    diffs = diffs[diffs > 0]
    step = float(diffs.min()) if len(diffs) else 50.0          # strike gap (Nifty 50, BankNifty 100, stock 2.5...)

    # Zone ki chaudai (points): user ne di ho to wahi, warna auto = spot ka 0.16% (Nifty par ~40 points)
    w = float(zone_pts) if zone_pts and zone_pts > 0 else float(spot) * 0.0016
    w = round(w) if w >= 1 else round(w, 2)
    w = max(w, 0.01)
    half = w / 2
    colmax = {c: max(float(d[c].max()), 1.0) for c in ("Call OI", "Put OI", "Call Vol", "Put Vol")}

    def make_zone(basis, side, rank, row):
        c = "Call" if side == "supply" else "Put"
        base = "Vol" if basis == "vol" else "OI"
        k = float(row["Strike"])
        pct = float(row[f"{c} {base}"]) / colmax[f"{c} {base}"] * 100      # poori chain ke sabse zyada ka kitna %
        chg = float(row[f"{c} OI Chg"])
        z = {
            "basis": basis, "side": side, "rank": rank, "strike": fs(k), "pct": pct,
            "primary": {"strike": fs(k), "score": pct, "oi": float(row[f"{c} OI"]),
                        "vol": float(row[f"{c} Vol"]), "chg": chg, "fresh": chg > 0},
            "low": round(k - half, 2), "high": round(k + half, 2), "width": w,     # strike ke aas-paas w points ki patti
        }
        z["dist"] = (z["low"] - spot) if side == "supply" else (spot - z["high"])  # spot se kitne points door
        return z

    zone_sets = {"vol": {"supply": [], "demand": []}, "oi": {"supply": [], "demand": []}}
    for basis in ("vol", "oi"):
        for side in ("supply", "demand"):
            col = ("Call " if side == "supply" else "Put ") + ("Vol" if basis == "vol" else "OI")
            pool = d[d["Strike"] >= spot] if side == "supply" else d[d["Strike"] <= spot]
            pool = pool[pool[col] > 0]
            if pool.empty:
                continue
            i1 = pool[col].idxmax()                                  # Zone 1: us taraf ka sabse zyada
            out = [make_zone(basis, side, 1, d.loc[i1])]
            k1, lim = float(d.loc[i1, "Strike"]), 10 * step
            if side == "supply":                                     # Zone 2: bahar ki taraf (upar), 10 strikes tak
                cand = pool[(pool["Strike"] > k1) & (pool["Strike"] <= k1 + lim)]
            else:                                                    # Demand: bahar ki taraf (niche)
                cand = pool[(pool["Strike"] < k1) & (pool["Strike"] >= k1 - lim)]
            cand = cand[cand[col] >= 0.6 * colmax[col]]              # 60% ya usse upar
            if not cand.empty:
                out.append(make_zone(basis, side, 2, d.loc[cand[col].idxmax()]))
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
        "supply": supply, "demand": demand, "zones": zones_flat, "zone_sets": zone_sets, "zone_width": w,
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
            f'<div class="v">{text}</div><div class="pb hi">{pct:.0f}%</div></td>'
        )
    if pct >= 74.5:                                  # 75% se upar: saaf ek rang (bina bar ke)
        return (
            f'<td style="background-color:{MID_COLOR}">'
            f'<div class="v">{text}</div><div class="pb mid">{pct:.0f}%</div></td>'
        )
    if pct >= 59.5:                                  # 60% se upar (Zone 2 ke layak)
        return (
            f'<td style="background-color:{CYAN_COLOR}">'
            f'<div class="v">{text}</div><div class="pb cy">{pct:.0f}%</div></td>'
        )
    cls = "pb"
    grad = f"linear-gradient({direction}, {color} {pct:.0f}%, transparent {pct:.0f}%)"
    return (
        f'<td style="background-color:{bg};background-image:{grad}">'
        f'<div class="v">{text}</div><div class="{cls}">{pct:.0f}%</div></td>'
    )


def chg_cell(x, bg):
    color = "#16a34a" if x > 0 else "#dc2626" if x < 0 else "#6b7280"
    return f'<td style="background-color:{bg};color:{color};font-weight:600">{x / 1e5:.1f}</td>'


def plain_cell(text, bg, bold=False):
    w = "font-weight:700;" if bold else ""
    return f'<td style="background-color:{bg};{w}">{text}</td>'


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


def build_table_body(df, spot, n, ana=None, show_summary=True, inst_label="SPOT", shift=None):
    mx = {k: max(float(df[k].max()), 1.0) for k in ["Call OI", "Put OI", "Call Vol", "Put Vol"]}
    d = df.sort_values("Strike").reset_index(drop=True)
    atm_idx = int((d["Strike"] - spot).abs().idxmin())
    atm_strike = d.loc[atm_idx, "Strike"]
    view = d.iloc[max(atm_idx - n, 0): atm_idx + n + 1]

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
        f'<tr class="spotrow"><td colspan="{ncols}">▶▶ {inst_label} SPOT {spot:,.2f} (market yahan chal raha hai) ◀◀</td></tr>'
    )
    for _, r in view.iterrows():
        s = r["Strike"]
        if not spot_done and s > spot:
            rows.append(spot_row)
            spot_done = True
        cbg = ITM if s < spot else NORM
        pbg = ITM if s > spot else NORM
        is_atm = s == atm_strike
        strike_bg = "#e5e7eb"                              # saare strike ek hi color

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
            + plain_cell(f'{r["Call IV"]:.1f}', cbg)
            + plain_cell(f'{r["Call LTP"]:.2f}', cbg, True)
            + chg_cell(r["Call OI Chg"], cbg)
            + bar_cell(f'{r["Call OI"] / 1e5:.1f}', r["Call OI"] / mx["Call OI"] * 100, cbg, "rgba(248,113,113,.55)", "to left", "red")
            + bar_cell(fmt_vol(r["Call Vol"]), r["Call Vol"] / mx["Call Vol"] * 100, cbg, "rgba(251,146,60,.35)", "to left", "red")
            + f'<td style="background-color:{strike_bg};font-weight:800;font-size:14px">{fs(s)}</td>'
            # PUTS: Volume | OI | OI Chg | LTP | Zone | PCR | IV
            + bar_cell(fmt_vol(r["Put Vol"]), r["Put Vol"] / mx["Put Vol"] * 100, pbg, "rgba(96,165,250,.35)", "to right", "green")
            + bar_cell(f'{r["Put OI"] / 1e5:.1f}', r["Put OI"] / mx["Put OI"] * 100, pbg, "rgba(74,222,128,.6)", "to right", "green")
            + chg_cell(r["Put OI Chg"], pbg)
            + plain_cell(f'{r["Put LTP"]:.2f}', pbg, True)
            + zone_td
            + pcr_td
            + plain_cell(f'{r["Put IV"]:.1f}', pbg)
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
    return bool(st.session_state.get("theme_dark", True))


def _wc():
    return "dk" if _dark() else ""


DARK_CSS = """<style>
.dk{--fg:#e5e7eb;}
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
      .wrap{overflow-x:auto;}
      .bar{display:flex;justify-content:flex-end;padding:4px 2px 6px 2px;}
      #fsbtn{background:#2563eb;color:#fff;border:none;border-radius:8px;padding:7px 14px;font-size:13px;font-weight:700;cursor:pointer;}
      #fsbtn:active{background:#1d4ed8;}
      #oc{background:#fff;}
      #oc:fullscreen{overflow:hidden;padding:6px;}
      #oc:fullscreen .wrap{height:calc(100vh - 52px);overflow:auto;}
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
      .pb.mid{color:#5b21b6;border-color:#a78bfa;background:#ede9fe;font-weight:700;}
      .pb.cy{color:#155e75;border-color:#22d3ee;background:#ecfeff;font-weight:700;}
      .sh{white-space:normal;font-size:11px;font-weight:600;letter-spacing:0;text-align:left;padding:5px 8px 3px 8px;line-height:1.55;color:#111;position:sticky;left:4px;width:min(360px,calc(100vw - 24px));box-sizing:border-box;}
      th.shmid{white-space:normal;font-size:10px;color:#6b7280;font-weight:700;}
      tr.atm td{border-top:2px solid #3b82f6;border-bottom:2px solid #3b82f6;}
      tr.spotrow td{background:linear-gradient(90deg,#f97316,#ef4444,#f97316);color:#fff;font-weight:800;
                    padding:4px;font-size:12px;letter-spacing:1px;border:none;}
      .chip{display:inline-block;font-size:10px;font-weight:700;border-radius:10px;padding:1px 7px;margin:1px;}
      .chip.r{background:#ef4444;color:#fff;} .chip.s{background:#22c55e;color:#fff;} .chip.m{background:#8b5cf6;color:#fff;} .chip.l{background:#0891b2;color:#fff;} .chip.rv{background:#9f1239;color:#fff;} .chip.sv{background:#4d7c0f;color:#fff;}
    </style>"""

TABLE_UPDATE_JS = """
<script>
window.__cid = 'table';
var lastV = null, wrapEl = document.getElementById('wrap');
window.__update = function(p){
  if (p.v === lastV) return;
  var first = (lastV === null); lastV = p.v;
  wrapEl.innerHTML = p.html;
  if (first && window.__restoreScroll) window.__restoreScroll();
};
</script>"""


def table_shell_html():
    """Ye hissa kabhi badalta nahi, isliye refresh par iframe reload nahi hota (Full Screen bana rehta hai)."""
    return (
        DARK_CSS + TABLE_CSS
        + '<div id="oc" class="' + _wc() + '"><div class="bar"><button id="fsbtn" onclick="toggleFS()">⛶ Full Screen</button></div>'
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


def zone_items(ana, show_vol=True, show_oi=True, breached=None):
    items = []
    for g in zone_groups(ana, show_vol, show_oi):
        short, both, drop = group_tag(g)
        has_oi = any(m["basis"] == "oi" for m in g["members"])
        sup = g["side"] == "supply"
        color = ("#ef4444" if has_oi else "#9f1239") if sup else ("#16a34a" if has_oi else "#4d7c0f")
        alpha = 0.26 if both else 0.18 if any(m["rank"] == 1 for m in g["members"]) else 0.10
        broke = bool(breached) and any(abs(float(b["low"]) - float(g["low"])) < 1e-6 and b["side"] == g["side"] for b in breached)
        label = f"{'✖ ' if broke else ''}{'⭐ ' if both else ''}{'💧 ' if drop else ''}{short} {fs(g['low'])}-{fs(g['high'])} ({fs(g['width'])}p)"
        if broke:
            color, alpha = "#6b7280", 0.06                       # toota zone: dhundhla slate rang
        pa = (ana or {}).get("pressure_alert")
        if pa is not None and g["side"] == "demand" and abs(float(g["level"]) - float(pa)) < 1e-6:
            label = "⚠️ BEARISH PRESSURE · " + label
        items.append({"label": label, "short": short, "lo": float(g["low"]), "hi": float(g["high"]), "color": color,
                      "alpha": alpha, "level": fs(g["level"]), "key": g["side"], "single": True, "broke": broke})
    return items


def level_lines(ana, spot):
    out = [(f"SPOT {_pfmt(spot)}", float(spot), "#f97316")]
    if ana:
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

function drawPrice(){
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
  D.zones.forEach(function(z){
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
  var zy = zv.map(function(q){ var t = (q[2] - q[1]) >= 20 ? q[1] + 13 : q[1] - 4; return Math.min(Math.max(t, T + 12), T + ph - 4); });
  zy = spread(zy, 13);
  zv.forEach(function(q, k){
    cl.push('<text x="' + (L + 6) + '" y="' + f1(Math.min(zy[k], T + ph - 3)) + '" font-size="11" font-weight="700" fill="' + q[0].color + '" stroke="' + HALO + '" stroke-width="3" paint-order="stroke">' + q[0].label + '</text>');
  });
  D.lines.forEach(function(l){
    var y = Y(l.val);
    cl.push('<line x1="' + L + '" x2="' + (L + pw) + '" y1="' + f1(y) + '" y2="' + f1(y) + '" stroke="' + l.color + '" stroke-width="1.4" stroke-dasharray="' + l.dash + '"/>');
  });
  out.push('<g clip-path="url(#cp)">' + cl.join('') + '</g>', ticks.join(''));
  var tg = D.lines.map(function(l){
    var y = Y(l.val), arrow = '';
    if (y < T) { y = T + 9; arrow = '\u25B2 '; } else if (y > T + ph) { y = T + ph - 9; arrow = '\u25BC '; }
    return {l: l, y: y, t: arrow + l.lab};
  });
  D.zones.forEach(function(z){                       // screen se bahar ke zone ka tag (▲ / ▼)
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
  out.push('<text x="' + (L + pw / 2) + '" y="' + (H - 2) + '" font-size="10" fill="#9ca3af" text-anchor="middle">Strike  (laal = Call OI, hara = Put OI)</text>');
  svg.innerHTML = out.join('');
}

function draw(){ if (!D) return; if (CFG.kind === 'price') drawPrice(); else drawOI(); window.__view = view; }
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
document.getElementById('zrs').addEventListener('click', reset);
var zall = document.getElementById('zall');
if (zall) zall.addEventListener('click', function(){ if (D) { view.lo = D.flo; view.hi = D.fhi; changed(); } });
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
document.getElementById('zin').addEventListener('click', function(){ zoomX(0.7, (view.a + view.b) / 2); zoomY(0.7, (view.hi + view.lo) / 2); changed(); });
document.getElementById('zout').addEventListener('click', function(){ zoomX(1 / 0.7, (view.a + view.b) / 2); zoomY(1 / 0.7, (view.hi + view.lo) / 2); changed(); });

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
  setData(p.data);
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


def zoom_shell_html(kind):
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
        ".top{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:flex-start;gap:6px;padding:6px 8px 0 8px}"
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
        '<div class="btns"><button id="zin" class="g" title="Zoom in">＋</button><button id="zout" class="g" title="Zoom out">－</button>'
        '<button id="zrs" class="g" title="Reset">⟲</button>'
        + ('<button id="zall" class="g" title="Saare zone/levels dikhao">⤢ Sab</button>' if kind == "price" else "")
        + '<button id="zm" class="g">✋ Zoom</button><button id="fsbtn" onclick="toggleFS()">⛶ Full Screen</button></div></div>'
        f'<div id="info">{hint}</div><div id="wait">Chart load ho raha hai…</div>'
        '<div class="sc"><div class="inner" style="min-width:360px;max-width:620px;margin:auto"><div id="stage">'
        f'<svg id="svg" viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg" style="background:{svgbg};display:block"></svg>'
        f'<div id="zp" class="ov" style="left:{pc(L, W)};top:{pc(T, H)};width:{pc(pw, W)};height:{pc(ph, H)}"></div>'
        f'<div id="za" class="ov" style="left:{pc(ax0, W)};top:{pc(T, H)};width:{pc(ax1 - ax0, W)};height:{pc(ph, H)}"></div>'
        f'<div id="zt" class="ov" style="left:{pc(L, W)};top:{pc(T + ph, H)};width:{pc(pw, W)};height:{pc(H - T - ph, H)}"></div>'
        '</div></div></div></div>'
    )
    return DARK_CSS + html + ZOOM_JS.replace("__CFG__", json.dumps(cfg)) + FS_JS + SCROLL_JS


def price_chart_data(c, spot, ana, xfmt="%H:%M", sig="", fit_all=False, show_vol=True, show_oi=True, breached=None):
    items, lines = zone_items(ana, show_vol, show_oi, breached), level_lines(ana, spot)
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
    return {
        "sig": sig, "n": len(rows),
        "c": [[float(r.open), float(r.high), float(r.low), float(r.close)] for r in rows],
        "labels": [f"{r.time:{xfmt}}" for r in rows],
        "tips": [f"{r.time:%d %b %H:%M}  O {r.open:.2f}  H {r.high:.2f}  L {r.low:.2f}  C {r.close:.2f}" for r in rows],
        "zones": [{"label": i["label"], "short": i["short"], "lo": i["lo"], "hi": i["hi"], "color": i["color"], "alpha": i["alpha"]} for i in items],
        "lines": [{"lab": lab, "val": float(val), "color": col, "dash": "2 3" if lab.startswith("LIQ") else "5 4"} for lab, val, col in lines],
        "lo": lo, "hi": hi, "flo": flo, "fhi": fhi, "defA": max(0, len(rows) - 90), "defB": len(rows) + 1,
    }


def oi_chart_data(df, spot, n, ana, sig="", show_vol=True, show_oi=True):
    d = df.sort_values("Strike").reset_index(drop=True)
    ai = int((d["Strike"] - spot).abs().idxmin())
    v = d.iloc[max(ai - n, 0): ai + n + 1].reset_index(drop=True)
    strikes = v["Strike"].astype(float).tolist()
    sstep = min([b - a for a, b in zip(strikes, strikes[1:])] or [50])
    atm = float(d.loc[ai, "Strike"])
    ymax = max(float(v["Call OI"].max()), float(v["Put OI"].max()), 1.0) * 1.1
    zones = [
        {"key": it["key"], "short": it["short"], "a": it["level"], "b": it["level"], "color": it["color"], "alpha": it["alpha"]}
        for it in zone_items(ana, show_vol, show_oi)
    ]
    lines = [
        {"lab": lab, "val": float(val), "color": col, "dash": "2 3" if lab.startswith("LIQ") else "5 4"}
        for lab, val, col in level_lines(ana, spot)
    ]
    return {
        "sig": "oi|" + sig, "n": len(strikes),
        "s0": strikes[0], "sstep": sstep, "atm": strikes.index(atm) if atm in strikes else -1,
        "slabels": [str(fs(s)) for s in strikes],
        "call": [float(x) for x in v["Call OI"]], "put": [float(x) for x in v["Put OI"]],
        "tips": [f'{fs(r["Strike"])}  Call OI {r["Call OI"] / 1e5:.1f}L  Put OI {r["Put OI"] / 1e5:.1f}L' for _, r in v.iterrows()],
        "zones": zones, "lines": lines, "lo": 0.0, "hi": ymax, "defA": 0, "defB": len(strikes),
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
    """Pehle free Gemini, key na ho to Claude."""
    if get_secret("GEMINI_API_KEY"):
        return ask_gemini(summary_text)
    if get_secret("ANTHROPIC_API_KEY"):
        return ask_claude(summary_text)
    return None, ("Koi AI key nahi mila. Free ke liye GEMINI_API_KEY (aistudio.google.com) "
                  "Streamlit Secrets ya .env mein add karein.")


# ---------------- Shifting: option ki intraday history (button dabane par) ----------------
def fetch_option_hist(key):
    try:
        data = requests.get(f"https://api.upstox.com/v2/historical-candle/intraday/{enc(key)}/1minute",
                            headers=HEADERS, timeout=20).json()
        cs = (data.get("data") or {}).get("candles") or []
        if not cs:
            e = data.get("errors") or [{}]
            return key, None, str(e[0].get("message") or data.get("status") or "khali")[:80]
        c = pd.DataFrame(cs).iloc[:, :7]
        c.columns = ["time", "o", "h", "l", "c", "vol", "oi"]
        c["time"] = pd.to_datetime(c["time"], utc=True).dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
        return key, c[["time", "vol", "oi"]].sort_values("time").reset_index(drop=True), ""
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


def _win_metrics(view, hist):
    """Har option ke liye 9:17-12:17 ka Volume, aakhri OI, aur kya OI badh raha hai (aur volume dusre half mein zyada)."""
    rows = []
    for _, r in view.iterrows():
        for side, kc in (("Call", "Call Key"), ("Put", "Put Key")):
            h = hist.get(r.get(kc))
            if h is None or h.empty:
                continue
            tm = h["time"].dt.time
            w = h[(tm >= PRESS_START) & (tm <= PRESS_END)]
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


def build_pressure_full(df, spot, n, ana):
    d = df.sort_values("Strike").reset_index(drop=True)
    ai = int((d["Strike"] - spot).abs().idxmin())
    view = d.iloc[max(ai - n, 0): ai + n + 1]
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
    m = _win_metrics(view, hist)
    if m.empty:
        return {"error": f"{PRESS_START:%H:%M} se {PRESS_END:%H:%M} ka data abhi nahi hai. Market khulne ke baad dobara dabayein."}
    sup_k = float(ana["demand"]["primary"]["strike"]) if ana.get("demand") else None
    res_k = float(ana["supply"]["primary"]["strike"]) if ana.get("supply") else None
    s_state, s_at = _zone_state(m, "Put", sup_k, spot, "sup")
    r_state, r_at = _zone_state(m, "Call", res_k, spot, "res")
    return {
        "support": {"state": s_state, "zone": sup_k, "at": s_at},
        "resistance": {"state": r_state, "zone": res_k, "at": r_at},
        "column": PRESS_COL[(s_state, r_state)],
        "alert": s_state == "DOWN" and r_state == "DOWN",
        "support_strike": sup_k,
        "n_ok": len(hist), "n_all": len(keys),
    }


def pressure_html(pr):
    def row(name, d):
        if d["zone"] is None:
            return f"{name}: zone nahi mila"
        extra = f" (shift {fs(d['at'])} par)" if d["at"] else ""
        return f"{name} <b>{fs(d['zone'])}</b> → {PRESS_LABEL[d['state']]}{extra}"
    return (f"🧭 <b>Pressure matrix</b> ({PRESS_START:%H:%M}–{PRESS_END:%H:%M}) · Column <b>{pr['column']}</b><br>"
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


# ---------------- Candles (price chart ke liye) ----------------
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


def render_table(df, spot, n, ana, show_summary, label, height):
    components.html(table_shell_html(), height=height, scrolling=True)
    components.html(push_html("table", {"html": build_table_body(df, spot, n, ana, show_summary, label, current_shift())}), height=0)


def render_charts(df, spot, ana, n_strikes, height=440):
    view = st.radio("Chart chuno", ["📈 Price + Zones", "📊 OI + Zones"], horizontal=True)
    if view.startswith("📈"):
        tf = st.radio("Timeframe", [1, 5, 15], index=1, horizontal=True, format_func=lambda m: f"{m} min")
        candles, src, err = fetch_candles(inst_key)
        br = []
        if not candles.empty:
            # sirf aaj ke intraday candles par tod-ne ka check (30-min history par nahi)
            br_c = resample_candles(candles, tf) if src == "intraday" else None
            if br_c is not None:
                br = breach_check(br_c, ana)
        st.session_state["breaches"] = br
        if candles.empty:
            st.warning(
                "Candle data nahi mila, isliye sirf zones aur levels dikha raha hoon. "
                f"Upstox ka jawab: {err or 'khali'}"
            )
            fake = pd.DataFrame({"time": [pd.Timestamp("2000-01-01")], "open": [spot], "high": [spot],
                                 "low": [spot], "close": [spot], "volume": [0]})
            data = price_chart_data(fake, spot, ana, "%H:%M", f"{inst_name}|fake", True, show_vol_zones, show_oi_zones)
        else:
            if src == "intraday":
                candles, xfmt = resample_candles(candles, tf), "%H:%M"
            else:
                xfmt = "%d %b %H:%M"
            data = price_chart_data(candles.tail(200), spot, ana, xfmt, f"{inst_name}|{tf}|{src}|{len(br)}", False, show_vol_zones, show_oi_zones, br)
        components.html(zoom_shell_html("price"), height=height, scrolling=True)
        components.html(push_html("price", {"data": data}), height=0)
        if st.button("📊 Zone price test (aaj ke candles par)"):
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
    else:
        components.html(zoom_shell_html("oi"), height=height, scrolling=True)
        components.html(push_html("oi", {"data": oi_chart_data(df, spot, min(n_strikes, 15), ana, inst_name, show_vol_zones, show_oi_zones)}), height=0)
        st.caption("Laal bar = Call OI, Hara bar = Put OI. SUP1/SUP2 = Supply zones, DEM1/DEM2 = Demand zones, LIQ = Liquidity strike.")


# ---------------- Page ----------------
def render_page():
    df, spot = fetch_option_chain(inst_key, expiry_date)

    if df.empty:
        st.warning(f"⚠️ {inst_name} ka data load nahi hua! Upstox Access Token check karein. Stock ho to uske F&O options na hon ya symbol badal gaya ho to bhi data nahi aata.")
    else:
        ana = analyze(df, spot, zone_pts)
        supply, demand = ana["supply"], ana["demand"]

        if focus_mode:
            st.caption(f"{inst_name} Spot {spot:,.2f} | Expiry {expiry_date} | PCR {ana['pcr']:.2f}")
            render_table(df, spot, n_strikes, ana, show_summary, inst_name, min(160 + (2 * n_strikes + 2) * 50, 2200))
            return

        if chart_focus:
            st.caption(f"{inst_name} Spot {spot:,.2f} | Expiry {expiry_date} | Bias {ana['bias']}")
            render_charts(df, spot, ana, n_strikes, height=640)
            return

        # ---- Smart Analysis ----
        st.markdown("---")
        st.subheader("🧠 Smart Analysis – Supply / Demand Zone (OI + Volume based)")

        bias_col = "#dcfce7" if "BULL" in ana["bias"] else "#fee2e2" if "BEAR" in ana["bias"] else "#fef9c3"
        _br = st.session_state.get("breaches") or []
        if _br:
            st.markdown(breach_banner_html(_br), unsafe_allow_html=True)
        st.markdown(
            f'<div style="background:{bias_col};color:#111;padding:14px;border-radius:10px;font-size:18px;">'
            f'<b>Market Bias: {ana["bias"]}</b> &nbsp;|&nbsp; Score: {ana["points"]:+d} &nbsp;|&nbsp; PCR: {ana["pcr"]:.2f}'
            f' &nbsp;|&nbsp; Spot: {spot:,.2f}</div>',
            unsafe_allow_html=True,
        )
        st.write("")

        if st.button("🧭 Pressure matrix dekho (9:17 se 3 ghante)"):
            with st.spinner("Pressure nikal raha hoon (option ki history)..."):
                st.session_state["pressure"] = {"inst": inst_name, "exp": expiry_date,
                                                **build_pressure_full(df, spot, n_strikes, ana)}
        pr = st.session_state.get("pressure")
        same = bool(pr) and pr.get("inst") == inst_name and pr.get("exp") == expiry_date
        if same and pr.get("error"):
            st.warning(pr["error"])
        elif same:
            st.markdown(f'<div style="background:#f5f3ff;color:#111;padding:10px;border-radius:8px">{pressure_html(pr)}</div>',
                        unsafe_allow_html=True)
            if pr["alert"]:
                st.error("⚠️ Support ke paas BEARISH pressure: support aur resistance dono ⬇ hain. Chart par support zone par alert dikhega.")
        ana["pressure_alert"] = pr["support_strike"] if (same and not pr.get("error") and pr.get("alert")) else None
        # ---- Table ----
        st.markdown("---")
        st.subheader("📋 Complete Option Chain Matrix")
        sc1, sc2, sc3 = st.columns([2, 2, 1])
        cutoff_t = sc1.time_input("Shifting ka aadhar samay (isse pehle ka data 'purana')", value=dt_time(9, 20), step=60)
        if sc2.button(f"🔀 Shifting dekho ({cutoff_t:%H:%M} ke baad)"):
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
                    f'(strike {p["strike"]}, {z["pct"]:.0f}%)<br>'
                    f'📏 {zone_size_txt(z)} • Spot se {zone_dist_txt(z, side)}<br>'
                    f'OI {p["oi"] / 1e5:.1f}L • Chg {p["chg"] / 1e5:+.1f}L • Vol {fmt_vol(p["vol"])}<br>'
                    + ('⭐ OI aur Volume dono ka zone yahin<br>' if both else '')
                )
            return html + '</div>'

        zs_ = ana["zone_sets"]
        st.markdown("**📊 Volume ke hisaab se zone**")
        va, vb = st.columns(2)
        va.markdown(zone_card("🔴 SUPPLY (Call Volume)", zs_["vol"]["supply"], "supply", "#fff1f2", "#9f1239"), unsafe_allow_html=True)
        vb.markdown(zone_card("🟢 DEMAND (Put Volume)", zs_["vol"]["demand"], "demand", "#f7fee7", "#4d7c0f"), unsafe_allow_html=True)
        st.markdown("**📈 OI ke hisaab se zone**")
        oa, ob = st.columns(2)
        oa.markdown(zone_card("🔴 SUPPLY (Call OI)", zs_["oi"]["supply"], "supply", "#fef2f2", "#ef4444"), unsafe_allow_html=True)
        ob.markdown(zone_card("🟢 DEMAND (Put OI)", zs_["oi"]["demand"], "demand", "#f0fdf4", "#16a34a"), unsafe_allow_html=True)


# Auto refresh: sirf data wala hissa dobara bante hai (fragment), poora page nahi, isliye screen smooth rehti hai
if auto_refresh and hasattr(st, "fragment"):
    st.fragment(run_every=f"{refresh_secs}s")(render_page)()
else:
    render_page()
    if auto_refresh:                      # purane Streamlit version ke liye
        time.sleep(refresh_secs)
        st.rerun()
