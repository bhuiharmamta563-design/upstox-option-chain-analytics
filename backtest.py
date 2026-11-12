"""
Veer Zone Pro - Pressure matrix backtest (column 1 se 9)

Data folder: data/
  spot_YYYY-MM-DD.csv : time,open,high,low,close   (1-min Nifty candles, us din ke)
  opt_YYYY-MM-DD.csv  : time,strike,side,vol,oi    (1-min, side = Call ya Put)

Rule (aapke bataye hue):
  - Window: 09:17 se 12:17.
  - Support = spot ke neeche sabse zyada Put OI wala strike; Resistance = spot ke upar sabse zyada Call OI wala strike
    (window ki shuruaat par).
  - Har zone ki state: STRONG / UP (bullish) / DOWN (bearish), _zone_state ke niyam se.
  - Column = (support state, resistance state) -> 1 se 9.
  - Outcome: 12:17 se 15:15 tak spot kitna badla.
  - Expected direction (ASSUMPTION, badal sakte hain): sirf ek taraf ka signal ho to wahi disha;
    dono taraf ek hi disha ho to wahi; dono alag disha ho ya dono STRONG ho to 'flat'.

Run:
  python backtest.py            -> data/ se backtest
  python backtest.py --sample   -> nakli data banakar test
"""
import os
import sys
import glob
import pandas as pd

WIN_START, WIN_END, EXIT_TIME = "09:17", "12:17", "15:15"
MOVE_PCT = 0.3          # is se zyada upar/neeche move = up/down, warna flat
PRESS_COL = {("STRONG", "STRONG"): 1, ("STRONG", "DOWN"): 2, ("STRONG", "UP"): 3,
             ("DOWN", "STRONG"): 4, ("UP", "STRONG"): 5, ("DOWN", "DOWN"): 6,
             ("UP", "UP"): 7, ("DOWN", "UP"): 8, ("UP", "DOWN"): 9}


def _t(x):
    return pd.to_datetime(x).dt.time


def _at_or_before(spot, hhmm):
    t = pd.to_datetime(hhmm).time()
    s = spot[spot["tm"] <= t]
    return float(s["close"].iloc[-1]) if len(s) else None


def window_metrics(opt):
    """Har (side, strike) ke liye window ka volume, aakhri OI, aur OI badh raha hai ya nahi."""
    rows = []
    for (side, k), g in opt.groupby(["side", "strike"]):
        g = g.sort_values("time")
        if g.empty:
            continue
        half = max(len(g) // 2, 1)
        v1, v2 = g["vol"].iloc[:half].sum(), g["vol"].iloc[half:].sum()
        rows.append({"side": side, "strike": float(k), "vol": float(g["vol"].sum()),
                     "oi_last": float(g["oi"].iloc[-1]),
                     "rising": bool(float(g["oi"].iloc[-1]) > float(g["oi"].iloc[0]) and v2 >= v1)})
    return pd.DataFrame(rows)


def zone_state(m, side, zone_k, spot, kind):
    """Veer Zone Pro ke _zone_state jaisa niyam (veer app.py se)."""
    if m.empty or zone_k is None:
        return "STRONG"
    x = m[m["side"] == side].copy()
    if x.empty:
        return "STRONG"
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
    if not x[out_m & (x["sv"] >= 75) & (x["so"] >= 75) & x["rising"]].empty:
        return out_state
    if not x[in_m & ((x["sv"] >= 75) | (x["so"] >= 75)) & x["rising"]].empty:
        return in_state
    return "STRONG"


def expected(s, r):
    dirs = {"UP": "up", "DOWN": "down"}
    sd, rd = dirs.get(s), dirs.get(r)
    if sd and rd:
        return sd if sd == rd else "flat"
    return sd or rd or "flat"


def run_day(day, spot, opt):
    spot = spot.copy()
    spot["tm"] = _t(spot["time"])
    opt = opt.copy()
    opt["time"] = pd.to_datetime(opt["time"])
    opt["tm"] = opt["time"].dt.time
    w = opt[(opt["tm"] >= pd.to_datetime(WIN_START).time()) & (opt["tm"] <= pd.to_datetime(WIN_END).time())]
    if w.empty:
        return None
    spot_start = _at_or_before(spot, WIN_START)
    spot_end = _at_or_before(spot, WIN_END)
    spot_exit = _at_or_before(spot, EXIT_TIME)
    if None in (spot_start, spot_end, spot_exit):
        return None
    # window ki shuruaat par OI snapshot se support/resistance
    snap = opt[opt["tm"] >= pd.to_datetime(WIN_START).time()].sort_values("time").groupby(["side", "strike"]).first().reset_index()
    puts = snap[(snap["side"] == "Put") & (snap["strike"] < spot_start)]
    calls = snap[(snap["side"] == "Call") & (snap["strike"] > spot_start)]
    if puts.empty or calls.empty:
        return None
    sup_k = float(puts.loc[puts["oi"].idxmax(), "strike"])
    res_k = float(calls.loc[calls["oi"].idxmax(), "strike"])
    m = window_metrics(w)
    s_state = zone_state(m, "Put", sup_k, spot_start, "sup")
    r_state = zone_state(m, "Call", res_k, spot_start, "res")
    col = PRESS_COL[(s_state, r_state)]
    move = (spot_exit - spot_end) / spot_end * 100
    actual = "up" if move > MOVE_PCT else "down" if move < -MOVE_PCT else "flat"
    exp = expected(s_state, r_state)
    return {"date": day, "support": sup_k, "resistance": res_k, "sup_state": s_state, "res_state": r_state,
            "column": col, "move_pct": round(move, 2), "actual": actual, "expected": exp, "hit": exp == actual}


def backtest(data_dir="data"):
    rows = []
    for sp in sorted(glob.glob(os.path.join(data_dir, "spot_*.csv"))):
        day = os.path.basename(sp)[5:15]
        op = os.path.join(data_dir, f"opt_{day}.csv")
        if not os.path.exists(op):
            continue
        r = run_day(day, pd.read_csv(sp), pd.read_csv(op))
        if r:
            rows.append(r)
    return pd.DataFrame(rows)


def report(df):
    if df.empty:
        print("Koi din nahi mila. data/ folder mein spot_ aur opt_ files check karein.")
        return
    g = df.groupby("column").agg(days=("hit", "size"), hits=("hit", "sum"))
    g["hit_%"] = (g["hits"] / g["days"] * 100).round(1)
    print(g.to_string())
    print(f"\nKul din: {len(df)}, sahi: {int(df['hit'].sum())}, hit rate: {df['hit'].mean() * 100:.1f}%")
    print("Sample chhota ho to ye pakka saboot nahi. Kam se kam 2-3 mahine ke din chahiye.")
    df.to_csv("backtest_results.csv", index=False)
    print("Din-wise result: backtest_results.csv")


def make_sample(data_dir="data", days=12, seed=1):
    import numpy as np
    rng = np.random.default_rng(seed)
    os.makedirs(data_dir, exist_ok=True)
    for d in range(days):
        day = (pd.Timestamp("2026-10-01") + pd.Timedelta(days=d)).strftime("%Y-%m-%d")
        t = pd.date_range(f"{day} 09:15", f"{day} 15:30", freq="1min")
        px = 25000 + np.cumsum(rng.normal(0, 4, len(t)))
        pd.DataFrame({"time": t, "open": px, "high": px + 2, "low": px - 2, "close": px}).to_csv(
            os.path.join(data_dir, f"spot_{day}.csv"), index=False)
        rows = []
        for k in range(24500, 25550, 50):
            for side in ("Call", "Put"):
                vol = rng.integers(100, 1000, len(t)).astype(float)
                oi = 100000 + np.cumsum(rng.integers(-200, 300, len(t)))
                rows.append(pd.DataFrame({"time": t, "strike": k, "side": side, "vol": vol, "oi": oi}))
        pd.concat(rows).to_csv(os.path.join(data_dir, f"opt_{day}.csv"), index=False)
    print(f"Nakli data {days} din ka bana: {data_dir}/")


if __name__ == "__main__":
    if "--sample" in sys.argv:
        make_sample()
    report(backtest("data"))
