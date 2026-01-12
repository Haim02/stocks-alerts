# app/trade_engine_tv.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class TradePlan:
    ok: bool
    reason: str = ""
    entry: Optional[float] = None
    entry_zone: Optional[dict] = None
    stop: Optional[float] = None
    tp1: Optional[float] = None
    tp2: Optional[float] = None
    rr1: Optional[float] = None
    rr2: Optional[float] = None
    risk_per_share: Optional[float] = None
    position_size_shares: Optional[int] = None
    position_notional: Optional[float] = None
    notes: Optional[list[str]] = None


def _to_float(x) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _clamp_price(x: Optional[float]) -> Optional[float]:
    if x is None:
        return None
    if x <= 0:
        return None
    return x


def _rr(entry: float, stop: float, tp: float) -> float:
    risk = entry - stop
    if risk <= 0:
        return 0.0
    return round((tp - entry) / risk, 2)


def build_trade_plan_from_tv(
    tv: Dict[str, Any],
    *,
    account_size: float = 10_000.0,
    risk_pct: float = 0.01,
    rr_min: float = 2.0,
) -> TradePlan:
    """
    קולט payload של TradingView (JSON) ומחזיר תוכנית עסקה לפי סוג סיגנל.
    עובד טוב במיוחד עם סווינג (1D/4H) ומודל סיכון 1% לעסקה.
    """

    ticker = str(tv.get("ticker", "")).upper().strip()
    signal = str(tv.get("signal", "")).upper().strip()
    interval = str(tv.get("interval", "")).upper().strip()

    close = _clamp_price(_to_float(tv.get("close")))
    rsi = _to_float(tv.get("rsi"))
    volume = _to_float(tv.get("volume"))
    ma20 = _to_float(tv.get("ma20"))
    ma50 = _to_float(tv.get("ma50"))
    ma200 = _to_float(tv.get("ma200"))
    trend = str(tv.get("trend", "")).upper().strip()

    support = _clamp_price(_to_float(tv.get("support")))
    resistance = _clamp_price(_to_float(tv.get("resistance")))

    bull_div = bool(tv.get("bullDiv", False))
    bear_div = bool(tv.get("bearDiv", False))

    notes: list[str] = []

    if not ticker or not signal or close is None:
        return TradePlan(ok=False, reason="Missing required fields (ticker/signal/close).")

    # --- Context checks (soft) ---
    if trend:
        notes.append(f"Trend: {trend}")
    if rsi is not None:
        notes.append(f"RSI: {round(rsi, 2)}")
    if ma200 is not None and close is not None:
        notes.append("Above MA200" if close > ma200 else "Below MA200")

    # --- Base risk model ---
    risk_amount = account_size * risk_pct  # 1% of account

    # --- Signal-specific logic ---
    entry = close
    entry_zone = {"low": round(close * 0.995, 4), "high": round(close * 1.005, 4)}  # ±0.5%

    # Default stop logic:
    # - Prefer support for long setups
    # - Otherwise use MA20, then MA50
    stop_candidates: list[float] = []
    if support:
        stop_candidates.append(support * 0.995)  # tiny buffer
    if ma20:
        stop_candidates.append(ma20 * 0.995)
    if ma50:
        stop_candidates.append(ma50 * 0.995)

    stop = None
    if stop_candidates:
        # choose the closest stop below entry (highest value below entry)
        below = [s for s in stop_candidates if s < entry]
        stop = max(below) if below else min(stop_candidates)

    # If we still don't have stop, fail gracefully
    if stop is None or stop >= entry:
        return TradePlan(ok=False, reason="Could not determine a valid stop below entry.", notes=notes)

    # Targets:
    # Prefer resistance as tp1 if above entry, otherwise use RR-based
    tp1 = None
    if resistance and resistance > entry:
        tp1 = resistance
        notes.append("TP1 uses resistance")
    else:
        tp1 = entry + (entry - stop) * rr_min
        notes.append("TP1 uses RR-min")

    tp2 = entry + (entry - stop) * max(rr_min + 1.0, 3.0)  # second target a bit further

    rr1 = _rr(entry, stop, tp1)
    rr2 = _rr(entry, stop, tp2)

    # Hard rule: if RR too low → not ok
    if rr1 < rr_min:
        notes.append(f"RR1 {rr1} < {rr_min}")
        return TradePlan(ok=False, reason="RR below minimum threshold.", notes=notes)

    risk_per_share = entry - stop
    if risk_per_share <= 0:
        return TradePlan(ok=False, reason="Invalid risk per share.", notes=notes)

    shares = int(risk_amount // risk_per_share)
    if shares <= 0:
        return TradePlan(ok=False, reason="Position size is 0 (risk/share too large).", notes=notes)

    notional = shares * entry

    # Extra notes per signal type
    if signal in ("BEAR_DIV", "BEARISH_DIVERGENCE"):
        notes.append("⚠️ Bearish divergence: consider reducing long exposure / tighter stop.")
    if bull_div:
        notes.append("BullDiv=true (supports long bias)")
    if bear_div:
        notes.append("BearDiv=true (risk warning)")

    # Basic quality flags
    if rsi is not None and signal in ("BREAKOUT", "REBOUND", "BULL_DIV"):
        if rsi < 40:
            notes.append("RSI low (early) – setup may be riskier")
        elif rsi > 70:
            notes.append("RSI high – beware exhaustion")

    return TradePlan(
        ok=True,
        entry=round(entry, 4),
        entry_zone={"low": round(entry_zone["low"], 4), "high": round(entry_zone["high"], 4)},
        stop=round(stop, 4),
        tp1=round(tp1, 4),
        tp2=round(tp2, 4),
        rr1=rr1,
        rr2=rr2,
        risk_per_share=round(risk_per_share, 4),
        position_size_shares=shares,
        position_notional=round(notional, 2),
        notes=notes,
    )
