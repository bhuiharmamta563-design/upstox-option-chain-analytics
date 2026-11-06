"""
Vajra Analytics - Nifty Option Chain (single file: app.py)

Install : pip install streamlit pandas numpy requests python-dotenv
Run     : streamlit run app.py

Secrets / .env keys:
  UPSTOX_ACCESS_TOKEN = "..."   (required, roz naya token)
  GEMINI_API_KEY      = "..."   (optional, FREE AI - aistudio.google.com)
  ANTHROPIC_API_KEY   = "..."   (optional, paid AI)
  GEMINI_MODEL        = "..."   (optional, default gemini-flash-latest)
"""
import json
import os
import time
from datetime import date

import numpy as np
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

st.set_page_config(page_title="Vajra Analytics - Option Chain", layout="wide")
st.title("📊 Live Nifty Option Chain & Volume Analytics")

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


# ---------------- Expiry dates (auto) ----------------
@st.cache_data(ttl=3600)
def fetch_expiries():
    url = "https://api.upstox.com/v2/option/contract?instrument_key=NSE_INDEX%7CNifty%2050"
    try:
        data = requests.get(url, headers=HEADERS).json()
        if data.get("status") == "success":
            exp = sorted({i["expiry"] for i in data.get("data", []) if i.get("expiry")})
            return [e for e in exp if e >= str(date.today())]
    except Exception as e:
        st.error(f"Expiry fetch error: {e}")
    return []


expiry_options = fetch_expiries()
if not expiry_options:
    st.error("⚠️ Expiry dates load nahi hui! Access Token check karein.")
    st.stop()

st.sidebar.header("Settings")
expiry_date = st.sidebar.selectbox("Select Expiry Date", expiry_options)
n_strikes = st.sidebar.slider("ATM ke upar/niche strikes", 5, 30, 10)
show_summary = st.sidebar.checkbox("Strike ke baad PCR / Zone dikhao", value=True)
focus_mode = st.sidebar.checkbox("📺 Focus mode (sirf option chain)", value=False)
auto_refresh = st.sidebar.checkbox("Auto refresh (5 sec)", value=False)
if st.sidebar.button("🔄 Refresh now"):
    st.cache_data.clear()


# ---------------- Option chain data ----------------
@st.cache_data(ttl=5)
def fetch_option_chain(expiry):
    url = (
        "https://api.upstox.com/v2/option/chain"
        f"?instrument_key=NSE_INDEX%7CNifty%2050&expiry_date={expiry}"
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
def strength_label(score):
    return "Strong 💪" if score >= 70 else "Medium 👍" if score >= 45 else "Weak ⚠️"


def analyze(df, spot):
    d = df.sort_values("Strike").reset_index(drop=True).copy()

    # Score = 50% OI + 30% Volume + 20% fresh OI addition (0-100)
    for side in ("Call", "Put"):
        oi, vol = d[f"{side} OI"], d[f"{side} Vol"]
        chg = d[f"{side} OI Chg"].clip(lower=0)
        d[f"{side} Score"] = (
            0.5 * oi / max(oi.max(), 1) + 0.3 * vol / max(vol.max(), 1) + 0.2 * chg / max(chg.max(), 1)
        ) * 100

    def zone(side, mask):
        cand = d[mask].sort_values(f"{side} Score", ascending=False)
        if cand.empty:
            return None
        top = cand.iloc[0]
        cluster = cand[(cand["Strike"] - top["Strike"]).abs() <= 100].head(3)
        levels = []
        for _, r in cluster.iterrows():
            chg = float(r[f"{side} OI Chg"])
            levels.append({
                "strike": int(r["Strike"]),
                "score": float(r[f"{side} Score"]),
                "oi": float(r[f"{side} OI"]),
                "vol": float(r[f"{side} Vol"]),
                "chg": chg,
                "fresh": chg > 0,
            })
        return {
            "primary": levels[0],
            "low": min(l["strike"] for l in levels),
            "high": max(l["strike"] for l in levels),
            "levels": levels,
        }

    supply = zone("Call", d["Strike"] >= spot)   # Resistance (Call writers)
    demand = zone("Put", d["Strike"] <= spot)    # Support (Put writers)

    # Max pain
    k = d["Strike"].values
    c_oi, p_oi = d["Call OI"].values, d["Put OI"].values
    pain = [(np.maximum(s - k, 0) * c_oi).sum() + (np.maximum(k - s, 0) * p_oi).sum() for s in k]
    max_pain = int(k[int(np.argmin(pain))])

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
        "supply": supply, "demand": demand, "max_pain": max_pain, "pcr": pcr,
        "chg_c": chg_c, "chg_p": chg_p, "points": pts, "bias": bias, "reasons": reasons,
    }


# ---------------- Colourful HTML table ----------------
def fmt_vol(v):
    v = v or 0
    if v >= 10000000:
        return f"{v / 10000000:.2f}Cr"
    if v >= 100000:
        return f"{v / 100000:.1f}L"
    if v >= 1000:
        return f"{v / 1000:.1f}K"
    return f"{int(v)}"


def bar_cell(text, pct, bg, color, direction, top_cls):
    grad = f"linear-gradient({direction}, {color} {pct:.0f}%, transparent {pct:.0f}%)"
    cls = "pb top-" + top_cls if pct >= 99.9 else "pb"
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


def build_table_html(df, spot, n, ana=None, show_summary=True):
    mx = {k: max(float(df[k].max()), 1.0) for k in ["Call OI", "Put OI", "Call Vol", "Put Vol"]}
    d = df.sort_values("Strike").reset_index(drop=True)
    atm_idx = int((d["Strike"] - spot).abs().idxmin())
    atm_strike = d.loc[atm_idx, "Strike"]
    view = d.iloc[max(atm_idx - n, 0): atm_idx + n + 1]

    # zone tags per strike
    tags, zone_bg = {}, {}
    if ana:
        for key, name, bg in (("supply", "SUPPLY", "#fecaca"), ("demand", "DEMAND", "#bbf7d0")):
            z = ana[key]
            if not z:
                continue
            for i, lv in enumerate(z["levels"]):
                label = ("R" if key == "supply" else "S") + str(i + 1)
                cls = "r" if key == "supply" else "s"
                tags.setdefault(lv["strike"], []).append(f'<span class="chip {cls}">{label} {name}</span>')
                zone_bg[lv["strike"]] = bg
        tags.setdefault(ana["max_pain"], []).append('<span class="chip m">🎯 MAX PAIN</span>')

    ITM, NORM = "#fff7cc", "#ffffff"
    ncols = 13 if show_summary else 11
    rows, spot_done = [], False
    spot_row = (
        f'<tr class="spotrow"><td colspan="{ncols}">▶▶ NIFTY SPOT {spot:,.2f} (market yahan chal raha hai) ◀◀</td></tr>'
    )
    for _, r in view.iterrows():
        s = r["Strike"]
        if not spot_done and s > spot:
            rows.append(spot_row)
            spot_done = True
        cbg = ITM if s < spot else NORM
        pbg = ITM if s > spot else NORM
        is_atm = s == atm_strike
        strike_bg = zone_bg.get(int(s), "#bfdbfe" if is_atm else "#f3f4f6")

        zone_td, pcr_td = "", ""
        if show_summary:
            pcr_s = r["Put OI"] / r["Call OI"] if r["Call OI"] else 0
            pcr_col = "#16a34a" if pcr_s > 1 else "#dc2626"
            sbg = "#faf5ff"
            zone_td = f'<td style="background-color:{sbg}">{"".join(tags.get(int(s), [])) or "-"}</td>'
            pcr_td = f'<td style="background-color:{sbg};color:{pcr_col};font-weight:700">{pcr_s:.2f}</td>'

        rows.append(
            f'<tr class="{"atm" if is_atm else ""}">'
            # CALLS: IV | LTP | OI Chg | OI | Volume  (Volume strike ke paas)
            + plain_cell(f'{r["Call IV"]:.1f}', cbg)
            + plain_cell(f'{r["Call LTP"]:.2f}', cbg, True)
            + chg_cell(r["Call OI Chg"], cbg)
            + bar_cell(f'{r["Call OI"] / 1e5:.1f}', r["Call OI"] / mx["Call OI"] * 100, cbg, "rgba(248,113,113,.55)", "to left", "red")
            + bar_cell(fmt_vol(r["Call Vol"]), r["Call Vol"] / mx["Call Vol"] * 100, cbg, "rgba(251,146,60,.35)", "to left", "red")
            + f'<td style="background-color:{strike_bg};font-weight:800;font-size:14px">{int(s)}</td>'
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

    css = """
    <style>
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
      tr.atm td{border-top:2px solid #3b82f6;border-bottom:2px solid #3b82f6;}
      tr.spotrow td{background:linear-gradient(90deg,#f97316,#ef4444,#f97316);color:#fff;font-weight:800;
                    padding:4px;font-size:12px;letter-spacing:1px;border:none;}
      .chip{display:inline-block;font-size:10px;font-weight:700;border-radius:10px;padding:1px 7px;margin:1px;}
      .chip.r{background:#ef4444;color:#fff;} .chip.s{background:#22c55e;color:#fff;} .chip.m{background:#8b5cf6;color:#fff;}
    </style>"""
    put_cols = 7 if show_summary else 5
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
    js = """
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
    table = f'<table style="min-width:{minw}px">{head1}{head2}{"".join(rows)}</table>'
    return (
        f'{css}<div id="oc"><div class="bar"><button id="fsbtn" onclick="toggleFS()">⛶ Full Screen</button></div>'
        f'<div class="wrap">{table}</div></div>{js}'
    )


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
        "Tum ek experienced Nifty options analyst ho. Neeche option chain ka analysis data hai. "
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
        return st.secrets[name]
    except Exception:
        return os.getenv(name)


def ask_gemini(summary_text):
    """FREE option: Google Gemini (Google AI Studio key)."""
    key = get_secret("GEMINI_API_KEY")
    if not key:
        return None, "GEMINI_API_KEY nahi mila."
    model = get_secret("GEMINI_MODEL") or "gemini-flash-latest"
    prompt = (
        "Tum ek experienced Nifty options analyst ho. Neeche option chain ka analysis data hai. "
        "Hinglish mein short, clear analysis do: market bias, supply zone (resistance), demand zone (support), "
        "breakout/breakdown ke levels, aur risk. Last mein 1 line disclaimer do (financial advice nahi hai).\n\n"
        + summary_text
    )
    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": key, "Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=60,
        )
        data = r.json()
        if "candidates" not in data:
            return None, f"Gemini error: {data.get('error', {}).get('message', data)}"
        parts = data["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts), None
    except Exception as e:
        return None, str(e)


def ask_ai(summary_text):
    """Pehle free Gemini, key na ho to Claude."""
    if get_secret("GEMINI_API_KEY"):
        return ask_gemini(summary_text)
    if get_secret("ANTHROPIC_API_KEY"):
        return ask_claude(summary_text)
    return None, ("Koi AI key nahi mila. Free ke liye GEMINI_API_KEY (aistudio.google.com) "
                  "Streamlit Secrets ya .env mein add karein.")


# ---------------- Page ----------------
df, spot = fetch_option_chain(expiry_date)

if df.empty:
    st.warning("⚠️ Data load nahi hua! Kripya check karein ki Upstox Access Token active hai aur sahi dala hai.")
else:
    ana = analyze(df, spot)
    supply, demand = ana["supply"], ana["demand"]

    if focus_mode:
        st.caption(f"Nifty Spot {spot:,.2f} | Expiry {expiry_date} | PCR {ana['pcr']:.2f}")
        components.html(
            build_table_html(df, spot, n_strikes, ana, show_summary),
            height=min(160 + (2 * n_strikes + 2) * 50, 2200),
            scrolling=True,
        )
        if auto_refresh:
            time.sleep(5)
            st.rerun()
        st.stop()

    max_call_oi_row = df.loc[df["Call OI"].idxmax()]
    max_put_oi_row = df.loc[df["Put OI"].idxmax()]
    max_call_vol_row = df.loc[df["Call Vol"].idxmax()]
    max_put_vol_row = df.loc[df["Put Vol"].idxmax()]

    c0, c1, c2, c3, c4, c5 = st.columns(6)
    c0.metric("📍 Nifty Spot", f"{spot:,.2f}", f"PCR: {ana['pcr']:.2f}")
    c1.metric("🔴 Major Resistance (Max Call OI)", f"{int(max_call_oi_row['Strike'])}", f"OI: {int(max_call_oi_row['Call OI']):,}")
    c2.metric("🟢 Major Support (Max Put OI)", f"{int(max_put_oi_row['Strike'])}", f"OI: {int(max_put_oi_row['Put OI']):,}")
    c3.metric("⚡ Max Call Volume Strike", f"{int(max_call_vol_row['Strike'])}", f"Vol: {int(max_call_vol_row['Call Vol']):,}")
    c4.metric("⚡ Max Put Volume Strike", f"{int(max_put_vol_row['Strike'])}", f"Vol: {int(max_put_vol_row['Put Vol']):,}")
    c5.metric("🎯 Max Pain", f"{ana['max_pain']}", f"Expiry: {expiry_date}", delta_color="off")

    # ---- Smart Analysis ----
    st.markdown("---")
    st.subheader("🧠 Smart Analysis – Supply / Demand Zone (OI + Volume based)")

    bias_col = "#dcfce7" if "BULL" in ana["bias"] else "#fee2e2" if "BEAR" in ana["bias"] else "#fef9c3"
    st.markdown(
        f'<div style="background:{bias_col};color:#111;padding:14px;border-radius:10px;font-size:18px;">'
        f'<b>Market Bias: {ana["bias"]}</b> &nbsp;|&nbsp; Score: {ana["points"]:+d} &nbsp;|&nbsp; PCR: {ana["pcr"]:.2f}'
        f' &nbsp;|&nbsp; Spot: {spot:,.2f}</div>',
        unsafe_allow_html=True,
    )
    st.write("")

    z1, z2 = st.columns(2)
    if supply:
        p = supply["primary"]
        z1.markdown(
            f'<div style="background:#fef2f2;color:#111;border-left:6px solid #ef4444;padding:12px;border-radius:8px">'
            f'<b>🔴 SUPPLY ZONE (Resistance)</b><br>'
            f'<span style="font-size:24px;font-weight:800">{supply["low"]} – {supply["high"]}</span><br>'
            f'Main level R1: <b>{p["strike"]}</b> • {strength_label(p["score"])}<br>'
            f'Call OI: {p["oi"] / 1e5:.1f}L • Chg: {p["chg"] / 1e5:+.1f}L • Vol: {fmt_vol(p["vol"])}<br>'
            f'{"Naya Call writing ➜ resistance mazboot" if p["fresh"] else "Call unwinding ➜ resistance kamzor"}</div>',
            unsafe_allow_html=True,
        )
    else:
        z1.info("Spot ke upar supply zone nahi mila.")
    if demand:
        p = demand["primary"]
        z2.markdown(
            f'<div style="background:#f0fdf4;color:#111;border-left:6px solid #22c55e;padding:12px;border-radius:8px">'
            f'<b>🟢 DEMAND ZONE (Support)</b><br>'
            f'<span style="font-size:24px;font-weight:800">{demand["low"]} – {demand["high"]}</span><br>'
            f'Main level S1: <b>{p["strike"]}</b> • {strength_label(p["score"])}<br>'
            f'Put OI: {p["oi"] / 1e5:.1f}L • Chg: {p["chg"] / 1e5:+.1f}L • Vol: {fmt_vol(p["vol"])}<br>'
            f'{"Naya Put writing ➜ support mazboot" if p["fresh"] else "Put unwinding ➜ support kamzor"}</div>',
            unsafe_allow_html=True,
        )
    else:
        z2.info("Spot ke niche demand zone nahi mila.")

    with st.expander("📌 Bias ke karan (reasons)", expanded=True):
        for rs in ana["reasons"]:
            st.write("• " + rs)
        if supply and demand:
            st.write(
                f"• **Trade view:** {demand['primary']['strike']} ke upar tak support, "
                f"{supply['primary']['strike']} ke niche tak resistance. "
                f"{supply['primary']['strike']} ke upar mazboot close = breakout, "
                f"{demand['primary']['strike']} ke niche close = breakdown."
            )

    lv_rows = []
    for name, z in (("Supply (R)", supply), ("Demand (S)", demand)):
        if z:
            for i, lv in enumerate(z["levels"]):
                lv_rows.append({
                    "Level": f"{name[-2]}{i + 1}", "Type": name, "Strike": lv["strike"],
                    "Score": round(lv["score"], 1), "OI (L)": round(lv["oi"] / 1e5, 1),
                    "OI Chg (L)": round(lv["chg"] / 1e5, 1), "Volume": int(lv["vol"]),
                    "Status": "Fresh writing" if lv["fresh"] else "Unwinding",
                })
    if lv_rows:
        st.dataframe(pd.DataFrame(lv_rows), use_container_width=True, hide_index=True)

    if st.button("🤖 AI se detailed analysis (Gemini free / Claude)"):
        summary = {
            "spot": spot, "expiry": expiry_date, "bias": ana["bias"], "pcr": round(ana["pcr"], 2),
            "max_pain": ana["max_pain"], "supply_zone": supply, "demand_zone": demand,
            "net_call_oi_change": ana["chg_c"], "net_put_oi_change": ana["chg_p"],
        }
        with st.spinner("AI analysis ho rahi hai..."):
            text, err = ask_ai(json.dumps(summary, default=float))
        if err:
            st.warning(err)
        else:
            st.markdown(text)

    # ---- Table ----
    st.markdown("---")
    st.subheader("📋 Complete Option Chain Matrix")
    st.caption(
        "Peela = ITM | Neela strike = ATM | Laal strike = Supply zone | Hara strike = Demand zone | "
        "Orange line = Nifty spot (market yahan chal raha hai)"
    )
    html = build_table_html(df, spot, n_strikes, ana, show_summary)
    components.html(html, height=min(140 + (2 * n_strikes + 2) * 50, 1100), scrolling=True)

    # ---- OI chart ----
    st.subheader("📊 Strike-wise OI (Call vs Put)")
    cd = df.sort_values("Strike").reset_index(drop=True)
    ai = int((cd["Strike"] - spot).abs().idxmin())
    cd = cd.iloc[max(ai - n_strikes, 0): ai + n_strikes + 1]
    chart_df = cd.set_index(cd["Strike"].astype(int).astype(str))[["Call OI", "Put OI"]]
    st.bar_chart(chart_df, color=["#ef4444", "#22c55e"])

if auto_refresh:
    time.sleep(5)
    st.rerun()
