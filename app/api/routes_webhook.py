from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Request

from app.services.emailer import send_email, build_email_html
from app.services.news_ai import summarize_news_with_ai
from app.ta.trade_engine_tv import build_trade_plan_from_tv
from app.services.emailer import build_email, send_email


router = APIRouter()


@router.post("/webhook/tradingview")
async def tradingview_webhook(req: Request):
    tv: Dict[str, Any] = await req.json()

    plan = build_trade_plan_from_tv(tv, account_size=10_000, risk_pct=0.01, rr_min=2.0)

    ticker = str(tv.get("ticker", "")).upper().strip() or "UNKNOWN"
    ai = summarize_news_with_ai(ticker=ticker, tv_payload=tv)

    html_body = f"""
    <p><b>Ticker:</b> {ticker}</p>
    <p><b>Signal:</b> {tv.get("signal")}</p>
    <p><b>Interval:</b> {tv.get("interval")}</p>
    <hr/>
    <h3>Trade Plan</h3>
    <pre style="background:#f6f6f6;padding:10px;border-radius:8px;">{plan}</pre>
    <hr/>
    <h3>News + AI</h3>
    <pre style="background:#f6f6f6;padding:10px;border-radius:8px;">{ai.get("news_summary","")}</pre>
    """

    subject = f"[stocks-alerts] {ticker} {tv.get('signal','')}"
    html = build_email_html(subject, html_body)
    

    # שולחים מייל רק אם התכנית OK
    if plan.ok:
        send_email(subject=subject, html=html)

    return {
        "received": True,
        "ticker": ticker,
        "plan_ok": plan.ok,
        "reason": plan.reason,
    }
