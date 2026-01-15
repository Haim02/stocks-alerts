# from __future__ import annotations

# from typing import Any, Dict

# from fastapi import APIRouter, Request

# from app.services.emailer import send_email, build_email_html
# from app.services.news_ai import summarize_news_with_ai
# from app.ta.trade_engine_tv import build_trade_plan_from_tv
# from app.services.emailer import build_email, send_email


# router = APIRouter()


# @router.post("/webhook/tradingview")
# async def tradingview_webhook(req: Request):
#     print("webhook hit: ")
#     tv: Dict[str, Any] = await req.json()

#     plan = build_trade_plan_from_tv(tv, account_size=10_000, risk_pct=0.01, rr_min=2.0)

#     ticker = str(tv.get("ticker", "")).upper().strip() or "UNKNOWN"
#     ai = summarize_news_with_ai(ticker=ticker, tv_payload=tv)

#     html_body = f"""
#     <p><b>Ticker:</b> {ticker}</p>
#     <p><b>Signal:</b> {tv.get("signal")}</p>
#     <p><b>Interval:</b> {tv.get("interval")}</p>
#     <hr/>
#     <h3>Trade Plan</h3>
#     <pre style="background:#f6f6f6;padding:10px;border-radius:8px;">{plan}</pre>
#     <hr/>
#     <h3>News + AI</h3>
#     <pre style="background:#f6f6f6;padding:10px;border-radius:8px;">{ai.get("news_summary","")}</pre>
#     """

#     subject = f"[stocks-alerts] {ticker} {tv.get('signal','')}"
#     html = build_email_html(subject, html_body)


#     # שולחים מייל רק אם התכנית OK
#     if plan.ok:
#         send_email(subject=subject, html=html)

#     return {
#         "received": True,
#         "ticker": ticker,
#         "plan_ok": plan.ok,
#         "reason": plan.reason,
#     }


# # app/api/routes_webhook.py
# import os
# from __future__ import annotations

# from typing import Any, Dict

# from fastapi import APIRouter, Request

# from app.services.emailer import build_email_html, send_email
# from app.services.news_ai import summarize_news_with_ai
# from app.ta.trade_engine_tv import build_trade_plan_from_tv

# router = APIRouter()


# @router.post("/webhook/tradingview")
# async def tradingview_webhook(req: Request):
#     print('webhook/tradingview')
#     tv: Dict[str, Any] = {}
#     try:
#         tv = await req.json()
#     except Exception as e:
#         # אם הבקשה לא JSON תקין — לא מפילים 500
#         return {"received": False, "error": f"Invalid JSON: {e}"}

#     ticker = str(tv.get("ticker", "")).upper().strip() or "UNKNOWN"
#     signal = str(tv.get("signal", "")).upper().strip() or "UNKNOWN"
#     interval = str(tv.get("interval", "")).upper().strip() or "UNKNOWN"

#     print(f"[TV WEBHOOK] hit ticker={ticker} signal={signal} interval={interval}")
#     ai_summary = "Ai לא רץ עדיין"
#     ai_err = None
#     ai_ok = False

#     # 1) Trade plan (לא מפילים אם יש בעיה)
#     try:
#         plan = build_trade_plan_from_tv(tv, account_size=10_000, risk_pct=0.01, rr_min=2.0)
#     except Exception as e:
#         plan = None
#         print(f"[TV WEBHOOK] trade plan error: {e}")

#     # 2) News + AI (לא מפילים אם יש בעיה)
#     try:
#         ai = summarize_news_with_ai(ticker=ticker, tv_payload=tv)
#         # ai_summary = ai.get("summary", "")  # ✅ הפלט החדש
#         ai_summary = ai.get("summary") or ai.get("news_summary") or ai.get("output_text") or ""
#         ai_ok = bool(ai.get("ok", False))
#         ai_err = ai.get("error")
#     except Exception as e:
#         ai_ok = False
#         ai_err = str(e)
#         ai_summary = "⚠️ סיכום AI לא זמין כרגע."
#         print(f"[TV WEBHOOK] AI error: {e}")

#     # 3) Build HTML
#     plan_block = ""
#     plan_ok = False
#     plan_reason = ""
#     if plan is None:
#         plan_block = "Trade plan generation failed."
#         plan_ok = False
#         plan_reason = "trade_plan_exception"
#     else:
#         plan_ok = bool(getattr(plan, "ok", False))
#         plan_reason = getattr(plan, "reason", "") or ""
#         # מייצגים את ה-dataclass יפה (fallback ל-str)
#         try:
#             plan_block = str(plan)
#         except Exception:
#             plan_block = repr(plan)

#     html_body = f"""
#     <p><b>Ticker:</b> {ticker}</p>
#     <p><b>Signal:</b> {signal}</p>
#     <p><b>Interval:</b> {interval}</p>
#     <hr/>
#     <h3>Trade Plan</h3>
#     <p><b>OK:</b> {plan_ok}</p>
#     <p><b>Reason:</b> {plan_reason}</p>
#     <pre style="background:#f6f6f6;padding:10px;border-radius:8px;white-space:pre-wrap;">{plan_block}</pre>
#     <hr/>
#     <h3>News + AI</h3>
#     <p><b>AI OK:</b> {ai_ok}</p>
#     <p><b>AI Error:</b> {ai_err}</p>
#     <pre style="background:#f6f6f6;padding:10px;border-radius:8px;white-space:pre-wrap;">{ai_summary}</pre>
#     """

#     subject_prefix = "OK" if plan_ok else "NOT OK"
#     subject = f"[stocks-alerts] {subject_prefix} {ticker} {signal}"
#     html = build_email_html(subject, html_body)

#     send_all = os.getenv("SEND_EMAIL_ALWAYS", "1").strip() == "1"
#     print("[TV WEBHOOK] will_send=", (send_all or plan_ok))
#     print("[TV WEBHOOK] subject=", subject)


#     # 4) Send email
#     # כדי שתוכל לבדוק E2E, שולחים תמיד (ואפשר לשלוט עם ENV)
#     # send_all = (str((__import__("os").getenv("SEND_EMAIL_ALWAYS", "1"))).strip() == "1")


#     try:
#         if send_all or plan_ok:
#             send_email(subject=subject, html=html)
#             print(f"[TV WEBHOOK] email sent subject={subject}")
#         else:
#             print("[TV WEBHOOK] email skipped (plan not ok and SEND_EMAIL_ALWAYS=0)")
#     except Exception as e:
#         # לא מפילים 500 בגלל SMTP
#         print(f"[TV WEBHOOK] email error: {e}")

#     return {
#         "received": True,
#         "ticker": ticker,
#         "signal": signal,
#         "interval": interval,
#         "plan_ok": plan_ok,
#         "reason": plan_reason,
#         "ai_ok": ai_ok,
#         "ai_error": ai_err,
#     }


# from __future__ import annotations
# import os
# from typing import Any, Dict
# from fastapi import APIRouter, Request

# from app.services.emailer import build_email_html, send_email
# from app.services.news_ai import summarize_news_with_ai
# from app.ta.trade_engine_tv import build_trade_plan_from_tv

# router = APIRouter()

# @router.post("/webhook/tradingview")
# async def tradingview_webhook(req: Request):
#     print('[TV WEBHOOK] Request received')

#     # --- 0) אתחול משתנים למניעת שגיאות UnboundLocalError ---
#     tv: Dict[str, Any] = {}
#     ticker, signal, interval = "UNKNOWN", "UNKNOWN", "UNKNOWN"
#     ai_summary = "המתנה לסיכום AI..."
#     ai_err = None
#     ai_ok = False
#     plan_block = "לא נוצר תוכנית מסחר"
#     plan_ok = False
#     plan_reason = ""
#     plan = None

#     # --- 1) קבלת ה-JSON ---
#     try:
#         tv = await req.json()
#     except Exception as e:
#         print(f"[TV WEBHOOK] JSON parse error: {e}")
#         return {"received": False, "error": f"Invalid JSON: {e}"}

#     # חילוץ נתונים בסיסיים
#     ticker = str(tv.get("ticker", "")).upper().strip() or "UNKNOWN"
#     signal = str(tv.get("signal", "")).upper().strip() or "UNKNOWN"
#     interval = str(tv.get("interval", "")).upper().strip() or "UNKNOWN"

#     print(f"[TV WEBHOOK] hit ticker={ticker} signal={signal} interval={interval}")

#     # --- 2) Trade plan ---
#     try:
#         plan = build_trade_plan_from_tv(tv, account_size=10_000, risk_pct=0.01, rr_min=2.0)
#         if plan:
#             plan_ok = bool(getattr(plan, "ok", False))
#             plan_reason = getattr(plan, "reason", "") or ""
#             try:
#                 plan_block = str(plan)
#             except Exception:
#                 plan_block = repr(plan)
#     except Exception as e:
#         print(f"[TV WEBHOOK] trade plan error: {e}")
#         plan_reason = f"Exception: {str(e)}"

#     # --- 3) News + AI ---
#     try:
#         ai = summarize_news_with_ai(ticker=ticker, tv_payload=tv)
#         if ai:
#             ai_summary = ai.get("summary") or ai.get("news_summary") or ai.get("output_text") or "No content found"
#             ai_ok = bool(ai.get("ok", False))
#             ai_err = ai.get("error")
#     except Exception as e:
#         ai_ok = False
#         ai_err = str(e)
#         ai_summary = "⚠️ סיכום AI נכשל עקב שגיאה פנימית."
#         print(f"[TV WEBHOOK] AI error: {e}")

#     # --- 4) בניית HTML למייל ---
#     html_body = f"""
#     <div style="direction: ltr; font-family: sans-serif;">
#         <p><b>Ticker:</b> {ticker}</p>
#         <p><b>Signal:</b> {signal}</p>
#         <p><b>Interval:</b> {interval}</p>
#         <hr/>
#         <h3>Trade Plan</h3>
#         <p><b>OK:</b> {plan_ok}</p>
#         <p><b>Reason:</b> {plan_reason}</p>
#         <pre style="background:#f6f6f6;padding:10px;border-radius:8px;white-space:pre-wrap;">{plan_block}</pre>
#         <hr/>
#         <h3>News + AI</h3>
#         <p><b>AI OK:</b> {ai_ok}</p>
#         <p><b>AI Error:</b> {ai_err}</p>
#         <pre style="background:#f6f6f6;padding:10px;border-radius:8px;white-space:pre-wrap;">{ai_summary}</pre>
#     </div>
#     """

#     subject_prefix = "OK" if plan_ok else "NOT OK"
#     subject = f"[stocks-alerts] {subject_prefix} {ticker} {signal}"
#     html = build_email_html(subject, html_body)

#     # הגדרות שליחה
#     send_all = os.getenv("SEND_EMAIL_ALWAYS", "1").strip() == "1"

#     print(f"[TV WEBHOOK] will_send={(send_all or plan_ok)}")
#     print(f"[TV WEBHOOK] subject={subject}")

#     # --- 5) שליחת המייל ---
#     try:
#         if send_all or plan_ok:
#             send_email(subject=subject, html=html)
#             print(f"[TV WEBHOOK] email sent")
#         else:
#             print("[TV WEBHOOK] email skipped (plan not ok and SEND_EMAIL_ALWAYS=0)")
#     except Exception as e:
#         print(f"[TV WEBHOOK] SMTP error: {e}")

#     # --- 6) החזרת תשובה ל-TradingView ---
#     return {
#         "received": True,
#         "ticker": ticker,
#         "signal": signal,
#         "interval": interval,
#         "plan_ok": plan_ok,
#         "ai_ok": ai_ok
#     }


from __future__ import annotations
import os
from typing import Any, Dict

# הוספנו את BackgroundTasks
from fastapi import APIRouter, Request, BackgroundTasks

# Imports - ודא שהקבצים האלו קיימים בנתיבים האלו
from app.services.emailer import build_email_html, send_email
from app.services.news_ai import summarize_news_with_ai
from app.ta.trade_engine_tv import build_trade_plan_from_tv

router = APIRouter()

# --- פונקציית עזר למשימות רקע (הלוגיקה הכבדה) ---
def process_alert_and_send_email(ticker: str, signal: str, interval: str, tv_payload: Dict[str, Any]):
    print(f"[BG TASK] Starting processing for {ticker}...")

    # 1. אתחול משתנים (כדי למנוע קריסות)
    ai_summary = "AI summary not available."
    ai_err = None
    ai_ok = False

    plan_block = "No trade plan generated."
    plan_ok = False
    plan_reason = ""
    plan = None

    try:
        plan = build_trade_plan_from_tv(tv_payload, account_size=10_000, risk_pct=0.01, rr_min=2.0)
        if plan:
            plan_ok = bool(getattr(plan, "ok", False))
            plan_reason = getattr(plan, "reason", "") or ""
            try:
                plan_block = str(plan)
            except:
                plan_block = repr(plan)
    except Exception as e:
        print(f"[BG TASK] Trade plan error: {e}")
        plan_reason = f"Error: {e}"

    # 3. קריאה ל-AI + חדשות
    try:
        ai = summarize_news_with_ai(ticker=ticker, tv_payload=tv_payload)
        if ai:
            ai_summary = ai.get("summary") or ai.get("news_summary") or ai.get("output_text") or "No text."
            ai_ok = bool(ai.get("ok", False))
            ai_err = ai.get("error")
    except Exception as e:
        print(f"[BG TASK] AI error: {e}")
        ai_summary = f"Error fetching AI summary: {e}"

    # 4. בניית HTML
    html_body = f"""
    <div style="direction: ltr; font-family: sans-serif;">
        <p><b>Ticker:</b> {ticker}</p>
        <p><b>Signal:</b> {signal}</p>
        <p><b>Interval:</b> {interval}</p>
        <hr/>
        <h3>Trade Plan</h3>
        <p><b>OK:</b> {plan_ok}</p>
        <p><b>Reason:</b> {plan_reason}</p>
        <pre style="background:#f6f6f6;padding:10px;border-radius:8px;white-space:pre-wrap;">{plan_block}</pre>
        <hr/>
        <h3>News + AI</h3>
        <p><b>AI OK:</b> {ai_ok}</p>
        <p><b>AI Error:</b> {ai_err}</p>
        <pre style="background:#f6f6f6;padding:10px;border-radius:8px;white-space:pre-wrap;">{ai_summary}</pre>
    </div>
    """

    subject_prefix = "OK" if plan_ok else "NOT OK"
    subject = f"[stocks-alerts] {subject_prefix} {ticker} {signal}"
    html = build_email_html(subject, html_body)

    # 5. שליחת המייל
    send_all = os.getenv("SEND_EMAIL_ALWAYS", "1").strip() == "1"

    try:
        if send_all or plan_ok:
            send_email(subject=subject, html=html)
            print(f"[BG TASK] Email sent successfully for {ticker}")
        else:
            print(f"[BG TASK] Email skipped for {ticker} (Plan NOT OK)")
    except Exception as e:
        print(f"[BG TASK] Email sending failed: {e}")


# --- ה-Route הראשי (מהיר מאוד) ---
@router.post("/webhook/tradingview")
async def tradingview_webhook(req: Request, background_tasks: BackgroundTasks):
    # קודם כל מקבלים את המידע
    try:
        tv = await req.json()
    except Exception as e:
        return {"received": False, "error": str(e)}

    # מחלצים פרטים בסיסיים
    ticker = str(tv.get("ticker", "UNKNOWN")).upper().strip()
    signal = str(tv.get("signal", "UNKNOWN")).upper().strip()
    interval = str(tv.get("interval", "UNKNOWN")).upper().strip()

    print(f"[WEBHOOK] Received: {ticker} | {signal}. Sending to background...")

    # מוסיפים את המשימה לרקע (הפונקציה למעלה)
    background_tasks.add_task(process_alert_and_send_email, ticker, signal, interval, tv)

    # מחזירים תשובה מיידית ל-TradingView!
    return {"status": "processing", "ticker": ticker, "msg": "Handled in background"}