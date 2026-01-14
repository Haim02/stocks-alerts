from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


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
