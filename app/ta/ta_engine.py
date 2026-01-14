from __future__ import annotations
import numpy as np
import pandas as pd

def moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ma20"] = df["close"].rolling(20).mean()
    df["ma50"] = df["close"].rolling(50).mean()
    df["ma200"] = df["close"].rolling(200).mean()
    return df

def pivots(df: pd.DataFrame, left: int = 3, right: int = 3) -> tuple[pd.Series, pd.Series]:
    """
    Pivot High/Low בסיסי:
    pivot_low = low שהוא הנמוך ביותר בחלון (left+right+1)
    pivot_high = high שהוא הגבוה ביותר בחלון
    """
    low = df["low"].values
    high = df["high"].values

    piv_low = np.full(len(df), False, dtype=bool)
    piv_high = np.full(len(df), False, dtype=bool)

    for i in range(left, len(df) - right):
        window_low = low[i-left:i+right+1]
        window_high = high[i-left:i+right+1]
        piv_low[i] = low[i] == window_low.min()
        piv_high[i] = high[i] == window_high.max()

    return pd.Series(piv_low, index=df.index), pd.Series(piv_high, index=df.index)

def support_resistance_levels(df, window: int = 5):
    lows = []
    highs = []

    for i in range(window, len(df) - window):
        low = df["low"].iloc[i]
        high = df["high"].iloc[i]

        if low == df["low"].iloc[i - window:i + window + 1].min():
            lows.append(low)

        if high == df["high"].iloc[i - window:i + window + 1].max():
            highs.append(high)

    return {
        "support": sorted(lows)[-5:],       # 5 רמות אחרונות
        "resistance": sorted(highs)[:5],    # 5 רמות ראשונות
    }


def supply_demand_zones(df: pd.DataFrame) -> dict[str, list[tuple[float, float]]]:
    """
    MVP: אזורי Demand/Supply כטווחים סביב pivot lows/highs.
    נחזיר רשימה של (low_bound, high_bound) לכל אזור.
    """
    piv_low, piv_high = pivots(df, left=3, right=3)

    # גודל אזור לפי ATR-ish פשוט (טווח ממוצע)
    tr = (df["high"] - df["low"]).rolling(14).mean()
    zone_pad = (tr.iloc[-1] if not tr.isna().all() else (df["high"]-df["low"]).mean()) * 0.6

    demand = []
    for price in df.loc[piv_low, "low"].tail(12):
        demand.append((float(price - zone_pad), float(price + zone_pad)))

    supply = []
    for price in df.loc[piv_high, "high"].tail(12):
        supply.append((float(price - zone_pad), float(price + zone_pad)))

    return {"demand": demand, "supply": supply}

def confluence_score(df: pd.DataFrame) -> dict:
    """
    מחשב ציון קונפלואנס פשוט:
    +1 אם מחיר מעל MA50 ו-MA50 עולה
    +1 אם המחיר קרוב לתמיכה
    +1 אם המחיר בתוך Demand zone
    +1 אם המחיר מתחת להתנגדות קרובה (יש 'room to run')
    """
    df = moving_averages(df)
    last = df.iloc[-1]
    close = float(last["close"])


    levels = support_resistance_levels(df)
    zones = supply_demand_zones(df)

    score = 0
    reasons = []

    # Trend via MA50
    if not pd.isna(last["ma50"]):
        ma50 = float(last["ma50"])
        ma50_prev = float(df["ma50"].iloc[-6]) if len(df) > 6 and not pd.isna(df["ma50"].iloc[-6]) else ma50
        if close > ma50 and ma50 > ma50_prev:
            score += 1
            reasons.append("Price > MA50 and MA50 rising")

    # Near support (within 1.2%)
    supports = levels["support"]
    if supports:
        nearest_support = min(supports, key=lambda x: abs(close - x))
        if abs(close - nearest_support) / nearest_support <= 0.012 and close >= nearest_support:
            score += 1
            reasons.append(f"Near support ~ {nearest_support:.2f}")

    # In demand zone
    in_demand = False
    for lo, hi in zones["demand"]:
        if lo <= close <= hi:
            in_demand = True
            break
    if in_demand:
        score += 1
        reasons.append("Inside demand zone")

    # Room to next resistance (>= 3%)
    resistances = levels["resistance"]
    if resistances:
        above = [r for r in resistances if r > close]
        if above:
            next_res = min(above)
            if (next_res - close) / close >= 0.03:
                score += 1
                reasons.append(f"Room to next resistance ~ {next_res:.2f}")

    return {
        "score": score,
        "reasons": reasons,
        "close": close,
        "levels": levels,
        "zones": zones,
        "ma": {"ma20": float(last["ma20"]) if not pd.isna(last["ma20"]) else None,
               "ma50": float(last["ma50"]) if not pd.isna(last["ma50"]) else None,
               "ma200": float(last["ma200"]) if not pd.isna(last["ma200"]) else None},
    }

def _atr(df: pd.DataFrame, n: int = 14) -> float:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)

    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)

    atr = tr.rolling(n).mean().iloc[-1]
    if pd.isna(atr):
        atr = tr.mean()
    return float(atr)

def trade_plan(df: pd.DataFrame, tech: dict, rr_min: float = 2.0) -> dict:
    """
    יוצר תוכנית עסקה (Swing Long) על בסיס:
    - demand zone / support (Stop מבני)
    - ATR buffer
    - TP לפי resistances + RR מינימלי
    """
    df = df.copy()
    close = float(tech["close"])
    atr = _atr(df)

    levels = tech["levels"]
    zones = tech["zones"]
    supports = levels.get("support", [])
    resistances = levels.get("resistance", [])

    # ---- Entry zone: סביב המחיר הנוכחי (MVP)
    entry_lo = close * 0.995
    entry_hi = close * 1.005

    # ---- Stop: מתחת ל-demand zone או לתמיכה הקרובה, עם ATR buffer
    stop_candidates = []

    # demand zone שמתחת/סביב המחיר
    demand_below = []
    for lo, hi in zones.get("demand", []):
        if lo <= close:  # zone below or containing price
            demand_below.append((lo, hi))
    if demand_below:
        # בוחרים את האזור שהגבול העליון שלו הכי קרוב למחיר (האזור "הרלוונטי")
        demand_below.sort(key=lambda z: abs(close - z[1]))
        dz_lo, dz_hi = demand_below[0]
        stop_candidates.append(dz_lo)

    # תמיכה קרובה מתחת למחיר
    below_supports = [s for s in supports if s <= close]
    if below_supports:
        nearest_support = max(below_supports)  # הכי קרובה מתחת
        stop_candidates.append(nearest_support)

    if not stop_candidates:
        # fallback: stop = close - 2*ATR
        raw_stop = close - 2.0 * atr
        stop_reason = "Fallback: close - 2*ATR"
    else:
        raw_stop = min(stop_candidates)  # הכי נמוך (שמרני)
        stop_reason = "Below demand/support + ATR buffer"

    stop = float(raw_stop - 0.8 * atr)  # buffer

    risk_per_share = close - stop
    if risk_per_share <= 0:
        return {"ok": False, "reason": "Invalid stop (risk_per_share <= 0)"}

    # ---- TP: התנגדויות מעל המחיר + RR מינימלי
    above_res = sorted([r for r in resistances if r > close])
    tp1 = None
    tp2 = None
    tp_reason = []

    # יעד לפי RR מינימלי
    rr_target_price = close + rr_min * risk_per_share

    # TP1: ההתנגדות הראשונה שמעל rr_target_price, אם קיימת
    if above_res:
        candidates = [r for r in above_res if r >= rr_target_price]
        if candidates:
            tp1 = float(candidates[0])
            tp_reason.append("TP1 = next resistance above RR-min")
        else:
            # אם אין התנגדות שמספיקה, TP1 לפי RR מינימלי
            tp1 = float(rr_target_price)
            tp_reason.append("TP1 = RR-min target (no resistance far enough)")
        # TP2: התנגדות הבאה אחרי TP1 אם קיימת, אחרת TP2 = TP1 + risk*1.5
        higher = [r for r in above_res if r > tp1]
        if higher:
            tp2 = float(higher[0])
            tp_reason.append("TP2 = next higher resistance")
        else:
            tp2 = float(tp1 + 1.5 * risk_per_share)
            tp_reason.append("TP2 = extension (no higher resistance)")
    else:
        tp1 = float(rr_target_price)
        tp2 = float(tp1 + 1.5 * risk_per_share)
        tp_reason.append("No resistances found; TP by RR targets")

    rr1 = (tp1 - close) / risk_per_share if tp1 else None
    rr2 = (tp2 - close) / risk_per_share if tp2 else None

    # סינון עסקאות חלשות
    if rr1 is not None and rr1 < rr_min:
        return {"ok": False, "reason": f"RR too low ({rr1:.2f} < {rr_min})"}

    return {
        "ok": True,
        "entry_zone": {"low": round(entry_lo, 4), "high": round(entry_hi, 4)},
        "stop_loss": round(stop, 4),
        "risk_per_share": round(risk_per_share, 4),
        "tp1": round(tp1, 4) if tp1 else None,
        "tp2": round(tp2, 4) if tp2 else None,
        "rr1": round(rr1, 2) if rr1 is not None else None,
        "rr2": round(rr2, 2) if rr2 is not None else None,
        "atr": round(atr, 4),
        "reasons": {
            "stop": stop_reason,
            "tp": tp_reason,
        },
        "risk_model": {"account_risk_pct": 1.0},  # נעול לפי מה שקבעת
    }


def candle_type(df: pd.DataFrame) -> str:
    last = df.iloc[-1]
    o, h, l, c = float(last["open"]), float(last["high"]), float(last["low"]), float(last["close"])

    body = abs(c - o)
    rng = max(h - l, 1e-9)
    upper = h - max(o, c)
    lower = min(o, c) - l

    # Doji
    if body / rng <= 0.12:
        return "DOJI"

    # Hammer / Pin bar
    if lower / rng >= 0.55 and body / rng <= 0.35 and upper / rng <= 0.15:
        return "HAMMER"
    if upper / rng >= 0.55 and body / rng <= 0.35 and lower / rng <= 0.15:
        return "SHOOTING_STAR"

    return "BULLISH" if c > o else "BEARISH"

def trend_return(df: pd.DataFrame, days: int) -> float:
    if len(df) < days + 1:
        return 0.0
    start = float(df["close"].iloc[-(days+1)])
    end = float(df["close"].iloc[-1])
    return (end - start) / start * 100.0

def volume_trend(df: pd.DataFrame, window: int = 20) -> str:
    if len(df) < window * 2:
        return "UNKNOWN"
    v1 = float(df["volume"].iloc[-window:].mean())
    v0 = float(df["volume"].iloc[-window*2:-window].mean())
    if v1 > v0 * 1.10:
        return "RISING"
    if v1 < v0 * 0.90:
        return "FALLING"
    return "FLAT"

def checklist_technical(df: pd.DataFrame, tech: dict) -> dict:
    """
    ממלא את הטופס הטכני (כמו בתמונה) בצורה אוטומטית ל-Swing.
    """
    df = moving_averages(df)
    close = float(df["close"].iloc[-1])
    ma20 = df["ma20"].iloc[-1]
    ma20_state = "UNKNOWN"
    if not pd.isna(ma20):
        ma20_state = "ABOVE" if close > float(ma20) else "BELOW"

    week_ret = trend_return(df, 5)
    month_ret = trend_return(df, 21)

    bull_bear = "BULLISH" if (tech["score"] >= 2 and (tech["ma"]["ma50"] is None or close > tech["ma"]["ma50"])) else "BEARISH"

    return {
        "candle": candle_type(df),
        "trend_week_pct": round(week_ret, 2),
        "trend_month_pct": round(month_ret, 2),
        "volume": volume_trend(df),
        "ma20": ma20_state,
        "support_levels": [round(x, 2) for x in tech["levels"]["support"]],
        "resistance_levels": [round(x, 2) for x in tech["levels"]["resistance"]],
        "demand_zones": [(round(lo, 2), round(hi, 2)) for lo, hi in tech["zones"]["demand"]],
        "supply_zones": [(round(lo, 2), round(hi, 2)) for lo, hi in tech["zones"]["supply"]],
        "bull_bear": bull_bear,
    }


