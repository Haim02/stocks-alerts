# app/scanners/finviz.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# NOTE:
# Finviz הוא אתר עם הגבלות ושינויים תכופים.
# בשלב הבא אפשר:
# 1) להשתמש ב-API חוקי (אם יש לך), או
# 2) להחליף למקור נתונים אחר (Polygon, TwelveData, AlphaVantage וכו')
# כרגע משאירים שלד כדי שהארכיטקטורה תהיה מוכנה.

@dataclass
class FinvizSnapshot:
    ticker: str
    price: Optional[float] = None
    volume: Optional[int] = None
    rsi: Optional[float] = None


async def get_finviz_snapshot(ticker: str) -> FinvizSnapshot:
    # TODO: מימוש אמיתי (אם תרצה)
    return FinvizSnapshot(ticker=ticker)
