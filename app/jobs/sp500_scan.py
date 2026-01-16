# # app/jobs/sp500_scan.py
# from __future__ import annotations

# import os
# from typing import Any, Dict, List, Optional

# from app.universe.sp500 import get_sp500_tickers
# from app.ta.ta_engine import confluence_score, trade_plan, checklist_technical
# from app.services.news_provider import get_company_news
# from app.services.ai_news_summarizer import summarize_news_he
# from app.services.emailer import send_email, build_email


# SCORE_THRESHOLD = float(os.getenv("SCAN_SCORE_THRESHOLD", "70"))
# NEWS_DAYS = int(os.getenv("SCAN_NEWS_DAYS", "7"))
# NEWS_LIMIT = int(os.getenv("SCAN_NEWS_LIMIT", "5"))
# MAX_TICKERS = int(os.getenv("SCAN_MAX_TICKERS", "50"))  # 0 = בלי הגבלה

# # אם send_email אצלך לוקח "to_email" — תשאיר.
# # אם הוא לא לוקח, פשוט תמחוק את השורה של EMAIL_TO ואת הפרמטר בקריאה.
# EMAIL_TO = os.getenv("EMAIL_TO", "").strip() or None


# def _fmt(x: Any) -> str:
#     if x is None:
#         return "-"
#     return str(x)


# def _safe_float(x: Any) -> Optional[float]:
#     try:
#         if x is None:
#             return None
#         return float(x)
#     except Exception:
#         return None


# def _plan_to_dict(plan_obj: Any) -> Dict[str, Any]:
#     """
#     trade_plan() אצלך יכול להחזיר:
#     - dataclass (TradePlan)
#     - dict
#     - משהו אחר
#     פה אנחנו מנרמלים לדיקט כדי לבנות HTML בלי להישבר.
#     """
#     if plan_obj is None:
#         return {"ok": False, "reason": "No plan returned"}

#     if isinstance(plan_obj, dict):
#         return plan_obj

#     # dataclass / object with attributes
#     d: Dict[str, Any] = {}
#     for k in (
#         "ok",
#         "reason",
#         "entry",
#         "entry_zone",
#         "stop",
#         "tp1",
#         "tp2",
#         "rr1",
#         "rr2",
#         "risk_per_share",
#         "position_size_shares",
#         "position_notional",
#         "notes",
#     ):
#         if hasattr(plan_obj, k):
#             d[k] = getattr(plan_obj, k)
#     if "ok" not in d:
#         d["ok"] = False
#         d["reason"] = "Unknown plan object"
#     return d


# def _build_news_html(news_items: List[Dict[str, Any]]) -> str:
#     if not news_items:
#         return "<p>אין חדשות משמעותיות בימים האחרונים.</p>"

#     lis = []
#     for it in news_items[:NEWS_LIMIT]:
#         title = _fmt(it.get("title") or it.get("headline"))
#         url = _fmt(it.get("url") or it.get("link"))
#         source = _fmt(it.get("source", ""))
#         when = _fmt(it.get("published") or it.get("date") or it.get("time"))

#         if url and url != "-":
#             lis.append(
#                 f'<li><a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a>'
#                 f' <span style="color:#666;font-size:12px;">{source} {when}</span></li>'
#             )
#         else:
#             lis.append(f"<li>{title} <span style='color:#666;font-size:12px;'>{source} {when}</span></li>")

#     return "<ul>" + "\n".join(lis) + "</ul>"


# def _build_plan_html(plan: Dict[str, Any]) -> str:
#     ok = bool(plan.get("ok"))
#     if not ok:
#         reason = _fmt(plan.get("reason"))
#         notes = plan.get("notes") or []
#         notes_html = ""
#         if notes:
#             notes_html = "<ul>" + "".join([f"<li>{_fmt(n)}</li>" for n in notes]) + "</ul>"
#         return f"""
#         <h3>📌 Trade Plan</h3>
#         <p style="color:#b00;"><b>לא נבנתה תוכנית עסקה:</b> {reason}</p>
#         {notes_html}
#         """

#     entry = plan.get("entry")
#     stop = plan.get("stop")
#     tp1 = plan.get("tp1")
#     tp2 = plan.get("tp2")
#     rr1 = plan.get("rr1")
#     rr2 = plan.get("rr2")
#     shares = plan.get("position_size_shares")
#     notional = plan.get("position_notional")
#     entry_zone = plan.get("entry_zone") or {}
#     notes = plan.get("notes") or []

#     notes_html = ""
#     if notes:
#         notes_html = "<ul>" + "".join([f"<li>{_fmt(n)}</li>" for n in notes]) + "</ul>"

#     return f"""
#     <h3>📌 Trade Plan</h3>
#     <table border="0" cellpadding="6" cellspacing="0" style="border:1px solid #ddd; border-radius:8px;">
#       <tr><td><b>Entry</b></td><td>{_fmt(entry)}</td></tr>
#       <tr><td><b>Entry Zone</b></td><td>{_fmt(entry_zone.get("low"))} – {_fmt(entry_zone.get("high"))}</td></tr>
#       <tr><td><b>Stop</b></td><td>{_fmt(stop)}</td></tr>
#       <tr><td><b>TP1</b></td><td>{_fmt(tp1)} (RR1: {_fmt(rr1)})</td></tr>
#       <tr><td><b>TP2</b></td><td>{_fmt(tp2)} (RR2: {_fmt(rr2)})</td></tr>
#       <tr><td><b>Shares</b></td><td>{_fmt(shares)}</td></tr>
#       <tr><td><b>Notional</b></td><td>{_fmt(notional)}</td></tr>
#     </table>
#     {notes_html}
#     """


# def _build_email_body_for_ticker(
#     ticker: str,
#     score: float,
#     tech: Any,
#     plan: Dict[str, Any],
#     news_items: List[Dict[str, Any]],
#     news_ai_he: str,
# ) -> str:
#     tech_html = f"<pre style='background:#f6f6f6;padding:10px;border-radius:8px;white-space:pre-wrap;'>{_fmt(tech)}</pre>"

#     news_html = _build_news_html(news_items)
#     plan_html = _build_plan_html(plan)

#     return f"""
#     <div style="margin-bottom:18px;">
#       <h2>📈 {ticker}</h2>
#       <p><b>Confluence Score:</b> <span style="font-size:18px;">{score:.2f}</span></p>

#       <h3>🧪 Technical Checklist</h3>
#       {tech_html}

#       {plan_html}

#       <h3>📰 News (last {NEWS_DAYS} days)</h3>
#       {news_html}

#       <h3>🤖 AI Summary (HE)</h3>
#       <div style="background:#f0f7ff;padding:10px;border-radius:8px;">
#         {_fmt(news_ai_he)}
#       </div>

#       <hr/>
#     </div>
#     """


# def run_sp500_scan() -> Dict[str, Any]:
#     tickers = get_sp500_tickers()
#     if MAX_TICKERS > 0:
#         tickers = tickers[:MAX_TICKERS]

#     sent = 0
#     passed: List[str] = []
#     errors: List[str] = []

#     for ticker in tickers:
#         try:
#             score = confluence_score(ticker)
#             score_f = _safe_float(score) or 0.0

#             if score_f < SCORE_THRESHOLD:
#                 continue

#             tech = checklist_technical(ticker)

#             plan_obj = trade_plan(ticker)
#             plan = _plan_to_dict(plan_obj)

#             news_items = get_company_news(ticker, days=NEWS_DAYS, limit=NEWS_LIMIT) or []
#             news_ai_he = summarize_news_he(ticker, news_items) if news_items else "אין מספיק חדשות לסיכום."

#             html_body = _build_email_body_for_ticker(
#                 ticker=ticker,
#                 score=score_f,
#                 tech=tech,
#                 plan=plan,
#                 news_items=news_items,
#                 news_ai_he=news_ai_he,
#             )

#             subject = f"S&P500 Alert – {ticker} (Score {score_f:.0f})"
#             email_html = build_email(title=subject, html_body=html_body)

#             # אם send_email אצלך לא מקבל to_email — פשוט תמחוק את הפרמטר הזה.
#             if EMAIL_TO:
#                 send_email(subject=subject, html=email_html, to_email=EMAIL_TO)
#             else:
#                 send_email(subject=subject, html=email_html)

#             sent += 1
#             passed.append(ticker)

#         except Exception as e:
#             errors.append(f"{ticker}: {e}")

#     return {"sent": sent, "passed": passed, "errors": errors}


# if __name__ == "__main__":
#     result = run_sp500_scan()
#     print(result)



# # app/jobs/sp500_scan.py
# from __future__ import annotations

# import os
# from datetime import datetime
# from typing import Any, Dict, List

# import yfinance as yf

# from app.ta.ta_engine import confluence_score, trade_plan, checklist_technical
# from app.services.emailer import build_email, send_email
# from app.universe.sp500 import get_sp500_tickers


# def _normalize_yf_df(df):
#     """
#     Normalize yfinance columns to lower-case names expected by your TA engine:
#     open, high, low, close, volume
#     """
#     if df is None or df.empty:
#         return df

#     # If MultiIndex columns exist, flatten
#     if hasattr(df.columns, "levels"):
#         df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

#     df = df.rename(
#         columns={
#             "Open": "open",
#             "High": "high",
#             "Low": "low",
#             "Close": "close",
#             "Adj Close": "adj_close",
#             "Volume": "volume",
#         }
#     )

#     # Keep only what we need
#     cols = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
#     df = df[cols].dropna()

#     return df


# def analyze_ticker(ticker: str, interval: str = "1d", period: str = "1y") -> Dict[str, Any]:
#     """
#     Fetch data -> TA -> trade plan.
#     Returns dict with analysis results.
#     """
#     df = yf.download(
#         ticker,
#         period=period,
#         interval=interval,
#         auto_adjust=False,
#         progress=False,
#     )

#     df = _normalize_yf_df(df)
#     if df is None or df.empty:
#         return {
#             "ticker": ticker,
#             "ok": False,
#             "reason": "empty_yfinance_df",
#         }

#     tech = confluence_score(df)
#     plan = trade_plan(df, tech, rr_min=2.0)
#     chk = checklist_technical(df, tech)

#     close = float(df["close"].iloc[-1])

#     return {
#         "ticker": ticker,
#         "ok": bool(plan.get("ok")),
#         "reason": plan.get("reason", ""),
#         "tech": tech,
#         "plan": plan,
#         "checklist": chk,
#         "close": close,
#         "interval": interval,
#         "period": period,
#     }


# def run_scan() -> Dict[str, Any]:
#     """
#     Main scan runner.
#     - scans S&P500 tickers
#     - sends email only when plan ok (or SEND_EMAIL_ALWAYS=1)
#     """
#     # controls
#     limit = int(os.getenv("SP500_SCAN_LIMIT", "0"))  # 0 = no limit
#     send_all = str(os.getenv("SEND_EMAIL_ALWAYS", "0")).strip() == "1"

#     # If you want "every 12 hours one email summary", set this to 1 and build a summary message.
#     # For now: send per-ticker only if plan ok (or send_all).
#     tickers = get_sp500_tickers()

#     if limit and limit > 0:
#         tickers = tickers[:limit]

#     passed: List[str] = []
#     errors: List[str] = []
#     sent = 0

#     print(f"[SP500_SCAN] start tickers={len(tickers)} limit={limit or 'none'} utc={datetime.utcnow().isoformat(timespec='seconds')}")

#     for ticker in tickers:
#         try:
#             res = analyze_ticker(ticker)

#             # "plan ok" means interesting candidate
#             plan_ok = bool(res.get("ok"))
#             if plan_ok:
#                 passed.append(ticker)

#             will_send = send_all or plan_ok
#             if not will_send:
#                 continue

#             # build full email with your existing builder
#             subject, html = build_email(
#                 ticker=ticker,
#                 interval=res.get("interval", "1d"),
#                 signal=("PLAN_OK" if plan_ok else "SCAN"),
#                 close=float(res.get("close", 0.0)),
#                 tv_payload={
#                     "source": "sp500_scan",
#                     "plan_ok": plan_ok,
#                     "reason": res.get("reason", ""),
#                     "score": (res.get("tech") or {}).get("score"),
#                 },
#             )

#             send_email(subject=subject, html=html)
#             sent += 1
#             print(f"[SP500_SCAN] email sent ticker={ticker} plan_ok={plan_ok}")

#         except Exception as e:
#             msg = f"{ticker}: {e}"
#             errors.append(msg)
#             print(f"[SP500_SCAN] error {msg}")

#     out = {"sent": sent, "passed": passed, "errors": errors}
#     print(f"[SP500_SCAN] done {out}")
#     return out


# def main():
#     run_scan()


# if __name__ == "__main__":
#     main()




# app/jobs/sp500_scan.py
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List

import yfinance as yf

from app.ta.ta_engine import confluence_score, trade_plan, checklist_technical
from app.services.emailer import build_email, send_email
from app.universe.sp500 import get_sp500_tickers
from dotenv import load_dotenv
load_dotenv()


def _normalize_yf_df(df):
    """
    Normalize yfinance columns to lower-case names expected by your TA engine:
    open, high, low, close, volume
    """
    if df is None or df.empty:
        return df

    # If MultiIndex columns exist, flatten
    if hasattr(df.columns, "levels"):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

    df = df.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
        }
    )

    # Keep only what we need
    cols = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
    df = df[cols].dropna()

    return df


def analyze_ticker(ticker: str, interval: str = "1d", period: str = "1y") -> Dict[str, Any]:
    """
    Fetch data -> TA -> trade plan.
    Returns dict with analysis results.
    """
    df = yf.download(
        ticker,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
    )

    df = _normalize_yf_df(df)
    if df is None or df.empty:
        return {
            "ticker": ticker,
            "ok": False,
            "reason": "empty_yfinance_df",
        }

    tech = confluence_score(df)
    plan = trade_plan(df, tech, rr_min=2.0)
    chk = checklist_technical(df, tech)

    close = float(df["close"].iloc[-1])

    return {
        "ticker": ticker,
        "ok": bool(plan.get("ok")),
        "reason": plan.get("reason", ""),
        "tech": tech,
        "plan": plan,
        "checklist": chk,
        "close": close,
        "interval": interval,
        "period": period,
    }


def run_scan() -> Dict[str, Any]:
    """
    Main scan runner.
    - scans S&P500 tickers
    - sends email only when plan ok (or SEND_EMAIL_ALWAYS=1)
    """
    # controls
    limit = int(os.getenv("SP500_SCAN_LIMIT", "0"))  # 0 = no limit
    send_all = str(os.getenv("SEND_EMAIL_ALWAYS", "0")).strip() == "1"

    # If you want "every 12 hours one email summary", set this to 1 and build a summary message.
    # For now: send per-ticker only if plan ok (or send_all).
    tickers = get_sp500_tickers()

    if limit and limit > 0:
        tickers = tickers[:limit]

    passed: List[str] = []
    errors: List[str] = []
    sent = 0

    print(f"[SP500_SCAN] start tickers={len(tickers)} limit={limit or 'none'} utc={datetime.utcnow().isoformat(timespec='seconds')}")

    for ticker in tickers:
        try:
            res = analyze_ticker(ticker)

            # "plan ok" means interesting candidate
            plan_ok = bool(res.get("ok"))
            if plan_ok:
                passed.append(ticker)

            will_send = send_all or plan_ok
            if not will_send:
                continue

            # build full email with your existing builder
            subject, html = build_email(
                ticker=ticker,
                interval=res.get("interval", "1d"),
                signal=("PLAN_OK" if plan_ok else "SCAN"),
                close=float(res.get("close", 0.0)),
                tv_payload={
                    "source": "sp500_scan",
                    "plan_ok": plan_ok,
                    "reason": res.get("reason", ""),
                    "score": (res.get("tech") or {}).get("score"),
                },
            )

            send_email(subject=subject, html=html)
            sent += 1
            print(f"[SP500_SCAN] email sent ticker={ticker} plan_ok={plan_ok}")

        except Exception as e:
            msg = f"{ticker}: {e}"
            errors.append(msg)
            print(f"[SP500_SCAN] error {msg}")

    out = {"sent": sent, "passed": passed, "errors": errors}
    print(f"[SP500_SCAN] done {out}")
    return out


def main():
    run_scan()


if __name__ == "__main__":
    main()


