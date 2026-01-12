# test_trade_engine_tv.py
from app.trade_engine_tv import build_trade_plan_from_tv

payload = {
    "ticker": "MSFT",
    "interval": "1D",
    "close": 420.15,
    "volume": 123456789,
    "signal": "BREAKOUT",
    "rsi": 56.2,
    "ma20": 410.0,
    "ma50": 395.0,
    "ma200": 360.0,
    "trend": "UP",
    "support": 405.0,
    "resistance": 435.0,
    "bullDiv": False,
    "bearDiv": False,
}

plan = build_trade_plan_from_tv(payload, account_size=10000, risk_pct=0.01, rr_min=2.0)
print(plan)
