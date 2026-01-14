# # import os
# # import smtplib
# # from datetime import datetime, timedelta
# # from email.mime.multipart import MIMEMultipart
# # from email.mime.text import MIMEText

# # import yfinance as yf
# # from dotenv import load_dotenv
# # from fastapi import FastAPI, Depends
# # from pydantic import BaseModel
# # from sqlalchemy.orm import Session

# # from .db import Base, engine, get_db
# # from .crud import save_alert

# # from app.ta_engine import confluence_score, trade_plan, checklist_technical

# # from app.fundamentals_us import fetch_fundamentals_us
# # from app.ai_summarizer import summarize_fundamentals_he

# # from app.news_provider import get_company_news
# # from app.ai_news_summarizer import summarize_news_he

# # from app.models_ai_cache import AiCache


# # # ✅ Stage 8.4: News cache (DB)
# # from app.models_news import NewsCache
# # from app.crud_news import get_recent_news_for_ticker, upsert_news_items

# # # (optional / existing in your project)
# # from app.sec_edgar import (
# #     get_cik_by_ticker,
# #     get_recent_filings,
# #     find_latest_10k_10q,
# #     download_primary_doc_text,
# #     extract_sections,
# # )
# # from app.ai_reports import summarize_report_he
# # from app.models_sec import SecReportCache  # important so table is created

# # # from __future__ import annotations
# # from typing import Any, Dict, Optional

# # from fastapi import FastAPI, Request
# # from fastapi.responses import JSONResponse

# # import os
# # from fastapi import FastAPI, Request, HTTPException
# # from fastapi.responses import JSONResponse
# # from dotenv import load_dotenv

# # from app.trade_engine_tv import build_trade_plan_from_tv
# # from app.mailer import send_email  # הקובץ שיצרנו קודם

# # from app.trade_engine_tv import build_trade_plan_from_tv

# # # plan = build_trade_plan_from_tv(tv_payload, account_size=10000, risk_pct=0.01, rr_min=2.0)


# # # ======================================================
# # # App setup
# # # ======================================================
# # load_dotenv()

# # print("OPENAI_API_KEY loaded:", bool(os.getenv("OPENAI_API_KEY")))
# # print("OPENAI_MODEL:", os.getenv("OPENAI_MODEL"))

# # app = FastAPI()

# # @app.get("/health")
# # def health():
# #     return {"ok": True}


# # @app.post("/webhook/tradingview")
# # async def webhook_tradingview(req: Request):
# #     try:
# #         tv_payload = await req.json()
# #     except Exception:
# #         raise HTTPException(status_code=400, detail="Invalid JSON")

# #     ticker = str(tv_payload.get("ticker", "UNKNOWN")).upper()
# #     interval = str(tv_payload.get("interval", "1D")).upper()
# #     signal = str(tv_payload.get("signal", "—")).upper()

# #     # 1) Trade Plan
# #     plan_obj = build_trade_plan_from_tv(
# #         tv_payload,
# #         account_size=float(os.getenv("ACCOUNT_SIZE", "10000")),
# #         risk_pct=float(os.getenv("RISK_PCT", "0.01")),
# #         rr_min=float(os.getenv("RR_MIN", "2.0")),
# #     )

# #     # אם הפונקציה מחזירה dataclass (TradePlan), נמיר ל-dict קטן למייל
# #     if hasattr(plan_obj, "__dict__"):
# #         plan = dict(plan_obj.__dict__)
# #     else:
# #         plan = plan_obj  # אם כבר dict

# #     # 2) Email content (רק אליך)
# #     email_obj = build_email(
# #         ticker=ticker,
# #         interval=interval,
# #         payload=tv_payload,
# #         plan=plan,
# #         news_items=None,       # בשלב הבא נכניס חדשות
# #         why_now_text=None,     # בשלב הבא נכניס "למה עכשיו"
# #         company_blurb=None,    # אפשר להעביר טקסט קצר אם תרצה
# #     )

# #     # 3) שליחה בפועל (גם אם נפסל – אתה עדיין רוצה לקבל, כרגע)
# #     send_email(email_obj["subject"], email_obj["body"])

# #     return JSONResponse({
# #         "received": True,
# #         "sent": True,
# #         "ticker": ticker,
# #         "interval": interval,
# #         "signal": signal,
# #         "plan_ok": bool(plan.get("ok", False)),
# #     })

# # # create tables (imports above ensure models are registered)
# # Base.metadata.create_all(bind=engine)

# # # ======================================================
# # # Settings (email + anti-spam)
# # # ======================================================
# # SMTP_HOST = os.getenv("SMTP_HOST", "")
# # SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
# # SMTP_USER = os.getenv("SMTP_USER", "")
# # SMTP_PASS = os.getenv("SMTP_PASS", "")
# # ALERT_TO_EMAIL = os.getenv("ALERT_TO_EMAIL", "")

# # DEDUP_MINUTES = int(os.getenv("DEDUP_MINUTES", "60"))
# # MAX_EMAILS_PER_HOUR = int(os.getenv("MAX_EMAILS_PER_HOUR", "20"))

# # _last_sent: dict[str, datetime] = {}
# # _sent_times: list[datetime] = []


# # # ======================================================
# # # Models
# # # ======================================================
# # class TVAlert(BaseModel):
# #     ticker: str
# #     interval: str = "1D"
# #     close: float | None = None
# #     signal: str  # BREAKOUT / REBOUND / SWING_LONG


# # # ======================================================
# # # Anti-spam helpers
# # # ======================================================
# # def cleanup(now: datetime):
# #     one_hour_ago = now - timedelta(hours=1)
# #     while _sent_times and _sent_times[0] < one_hour_ago:
# #         _sent_times.pop(0)


# # def can_send(key: str) -> bool:
# #     now = datetime.utcnow()
# #     cleanup(now)

# #     if len(_sent_times) >= MAX_EMAILS_PER_HOUR:
# #         return False

# #     last = _last_sent.get(key)
# #     if last and (now - last) < timedelta(minutes=DEDUP_MINUTES):
# #         return False

# #     return True


# # def mark_sent(key: str):
# #     now = datetime.utcnow()
# #     _last_sent[key] = now
# #     _sent_times.append(now)


# # # ======================================================
# # # Email builder (Stage 8.4: includes news cache)
# # # ======================================================

# # def _fmt_money(x: Optional[float]) -> str:
# #     if x is None:
# #         return "—"
# #     return f"${x:,.2f}"

# # def _fmt_num(x: Optional[float]) -> str:
# #     if x is None:
# #         return "—"
# #     return f"{x:,.2f}"

# # def _fmt_int(x: Optional[int]) -> str:
# #     if x is None:
# #         return "—"
# #     return f"{x:,}"

# # def _yn(b: Optional[bool]) -> str:
# #     if b is None:
# #         return "—"
# #     return "כן" if b else "לא"

# # def company_blurb(ticker: str) -> str:
# #     """
# #     הסבר קצר מאוד על החברה/מניה.
# #     אפשר לשדרג אחר כך לבלורב אוטומטי (SEC/ויקי/אתר חברה),
# #     כרגע זה טמפלט נקי שלא נתקע אותך.
# #     """
# #     t = ticker.upper()
# #     return (
# #         f"על המניה ({t}):\n"
# #         f"- מדובר במניית {t}. מומלץ להשלים בדיקה בסיסית: מה החברה עושה, סקטור, חדשות קרובות, דוחות, ותנודתיות.\n"
# #         f"- שים לב: הסיכום כאן הוא תבנית; לפני כניסה לטרייד תוודא שאין אירוע מהותי (דוחות/הודעה) שעלול לשנות את התמונה.\n"
# #     )

# # def build_email(
# #     *,
# #     ticker: str,
# #     plan: Any,
# #     tv_payload: Dict[str, Any],
# #     why_now_text: Optional[str] = None,
# #     news_bullets: Optional[list[str]] = None,
# # ) -> Dict[str, str]:
# #     """
# #     מחזיר dict עם: subject, body.
# #     plan: אובייקט TradePlan (כמו אצלך ב-test_trade_engine_tv.py).
# #     tv_payload: JSON שהגיע מ-TradingView / דמה.
# #     """

# #     t = ticker.upper()

# #     # שדות נפוצים שיש אצלך לפי הפלט ששלחת
# #     ok = getattr(plan, "ok", False)
# #     reason = getattr(plan, "reason", None)

# #     entry = getattr(plan, "entry", None)
# #     entry_zone = getattr(plan, "entry_zone", None)
# #     stop = getattr(plan, "stop", None)
# #     tp1 = getattr(plan, "tp1", None)
# #     rr1 = getattr(plan, "rr1", None)
# #     risk_per_share = getattr(plan, "risk_per_share", None)
# #     position_size = getattr(plan, "position_size", None)
# #     shares = getattr(plan, "shares", None)
# #     position_notional = getattr(plan, "position_notional", None)
# #     notes = getattr(plan, "notes", None) or []

# #     interval = tv_payload.get("interval")
# #     close = tv_payload.get("close")
# #     volume = tv_payload.get("volume")
# #     signal = tv_payload.get("signal")
# #     rsi = tv_payload.get("rsi")
# #     ma20 = tv_payload.get("ma20")
# #     ma50 = tv_payload.get("ma50")
# #     ma200 = tv_payload.get("ma200")
# #     trend = tv_payload.get("trend")
# #     support = tv_payload.get("support")
# #     resistance = tv_payload.get("resistance")
# #     bull_div = tv_payload.get("bullDiv")
# #     bear_div = tv_payload.get("bearDiv")

# #     status_line = "✅ עומד בתנאים (מועמד לטרייד)" if ok else "⛔ נפסל כרגע (לא נכנס לטרייד)"
# #     subject = f"[Swing Alert] {t} | {signal} | {interval} | {status_line}"

# #     # חלק חדשות (אופציונלי)
# #     news_txt = ""
# #     if news_bullets:
# #         lines = "\n".join([f"- {x}" for x in news_bullets[:6]])
# #         news_txt = f"\nחדשות/הקשר (בקצרה):\n{lines}\n"

# #     # למה עכשיו (אופציונלי)
# #     why_txt = ""
# #     if why_now_text:
# #         why_txt = f"\nלמה עכשיו:\n{why_now_text.strip()}\n"

# #     # תוכן מרכזי
# #     body = f"""\
# # היי,
# # התקבל סיגנל מ-TradingView עבור {t} ({signal}) בטיים-פריים {interval}.

# # {company_blurb(t)}

# # סיכום טכני מהגרף:
# # - מחיר סגירה: {_fmt_money(close)}
# # - נפח: {_fmt_int(int(volume)) if volume is not None else "—"}
# # - RSI: {_fmt_num(rsi)}
# # - MA20/50/200: {_fmt_num(ma20)} / {_fmt_num(ma50)} / {_fmt_num(ma200)}
# # - מגמה (Trend): {trend or "—"}
# # - תמיכה/התנגדות (S/R): {_fmt_num(support)} / {_fmt_num(resistance)}
# # - RSI Divergence: BullDiv={_yn(bull_div)}, BearDiv={_yn(bear_div)}

# # סטטוס המודל:
# # {status_line}
# # סיבה: {reason or "—"}

# # תכנית טרייד (אם עומד בתנאים):
# # - Entry: {_fmt_money(entry)}
# # - Entry Zone: {entry_zone or "—"}
# # - Stop: {_fmt_money(stop)}
# # - Target (TP1): {_fmt_money(tp1)}
# # - RR1: {rr1 if rr1 is not None else "—"}
# # - Risk per share: {_fmt_money(risk_per_share)}
# # - Position size ($): {_fmt_money(position_size)}
# # - Shares: {_fmt_int(int(shares)) if shares is not None else "—"}
# # - Notional: {_fmt_money(position_notional)}

# # הערות/בדיקות:
# # {chr(10).join([f"- {n}" for n in notes]) if notes else "- —"}
# # {news_txt}{why_txt}
# # דיסקליימר קצר: זה לא ייעוץ השקעות. לפני ביצוע, לבצע בדיקה עצמאית וניהול סיכונים.
# # """

# #     return {"subject": subject, "body": body}




# # # ======================================================
# # # Email sender (HTML)
# # # ======================================================
# # def send_email(subject: str, html_body: str):
# #     msg = MIMEMultipart("alternative")
# #     msg["Subject"] = subject
# #     msg["From"] = SMTP_USER
# #     msg["To"] = ALERT_TO_EMAIL

# #     msg.attach(MIMEText(html_body, "html", "utf-8"))

# #     with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
# #         smtp.login(SMTP_USER, SMTP_PASS)
# #         smtp.send_message(msg)


# # # ======================================================
# # # Routes
# # # ======================================================
# # @app.get("/health")
# # def health():
# #     return {"ok": True}


# # @app.post("/webhook/tradingview")
# # def webhook(alert: TVAlert, db: Session = Depends(get_db)):
# #     ticker = alert.ticker.upper()
# #     signal = alert.signal.upper()
# #     interval = alert.interval.upper()

# #     saved = save_alert(
# #         db,
# #         ticker=ticker,
# #         signal=signal,
# #         interval=interval,
# #         price=alert.close,
# #     )

# #     key = f"{ticker}|{signal}|{interval}"
# #     if not can_send(key):
# #         return {
# #             "received": True,
# #             "sent": False,
# #             "reason": "dedup_or_rate_limit",
# #             "key": key,
# #             "db_id": saved.id,
# #         }

# #     subject, body = build_email(
# #         db=db,
# #         ticker=ticker,
# #         interval=interval,
# #         signal=signal,
# #         close=alert.close,
# #     )

# #     send_email(subject, body)
# #     mark_sent(key)

# #     return {
# #         "received": True,
# #         "sent": True,
# #         "key": key,
# #         "db_id": saved.id,
# #     }


# import os
# from datetime import datetime, timedelta

# from fastapi import FastAPI, Depends
# from pydantic import BaseModel
# from dotenv import load_dotenv
# from sqlalchemy.orm import Session

# import yfinance as yf

# from app.emailer import send_email
# from app.fundamentals_us import fetch_fundamentals_us
# from app.ai_summarizer import summarize_fundamentals_he
# from app.news_provider import get_company_news
# from app.ai_news_summarizer import summarize_news_he
# from app.ta_engine import confluence_score, trade_plan, checklist_technical

# from .db import Base, engine, get_db
# from .crud import save_alert


# # ======================================================
# # App setup
# # ======================================================
# load_dotenv()
# app = FastAPI()
# Base.metadata.create_all(bind=engine)

# @app.get("/healthz")
# def health():
#     return {"status": "ok"}


# # ======================================================
# # Anti-spam settings
# # ======================================================
# DEDUP_MINUTES = int(os.getenv("DEDUP_MINUTES", "60"))
# MAX_EMAILS_PER_HOUR = int(os.getenv("MAX_EMAILS_PER_HOUR", "20"))

# _last_sent: dict[str, datetime] = {}
# _sent_times: list[datetime] = []


# # ======================================================
# # Models
# # ======================================================
# class TVAlert(BaseModel):
#     ticker: str
#     interval: str = "1D"
#     close: float | None = None
#     signal: str  # BREAKOUT / REBOUND / SWING_LONG / ...


# # ======================================================
# # Anti-spam helpers
# # ======================================================
# def cleanup(now: datetime):
#     one_hour_ago = now - timedelta(hours=1)
#     while _sent_times and _sent_times[0] < one_hour_ago:
#         _sent_times.pop(0)


# def can_send(key: str) -> bool:
#     now = datetime.utcnow()
#     cleanup(now)

#     if len(_sent_times) >= MAX_EMAILS_PER_HOUR:
#         return False

#     last = _last_sent.get(key)
#     if last and (now - last) < timedelta(minutes=DEDUP_MINUTES):
#         return False

#     return True


# def mark_sent(key: str):
#     now = datetime.utcnow()
#     _last_sent[key] = now
#     _sent_times.append(now)


# # ======================================================
# # Email builder (Tech + Fundamentals + News+AI)
# # ======================================================
# def build_email(ticker: str, interval: str, signal: str, close: float | None) -> tuple[str, str]:
#     # 1) Price data (daily MVP)
#     df = yf.download(ticker, period="1y", interval="1d", auto_adjust=False, progress=False)

#     if hasattr(df.columns, "levels"):
#         df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

#     df = df.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close","Volume":"volume"})
#     df = df[["open", "high", "low", "close", "volume"]].dropna()

#     last_close = float(df["close"].iloc[-1]) if close is None else float(close)

#     # 2) Technical
#     tech = confluence_score(df)
#     plan = trade_plan(df, tech, rr_min=2.0)
#     chk = checklist_technical(df, tech)

#     # 3) Fundamentals + AI
#     fundamentals = {"checks": {}, "metrics": {}, "ai_input": ""}
#     try:
#         fundamentals = fetch_fundamentals_us(ticker)
#     except Exception:
#         fundamentals = {"checks": {}, "metrics": {}, "ai_input": ""}

#     checks = fundamentals.get("checks", {}) or {}
#     metrics = fundamentals.get("metrics", {}) or {}

#     ai_fund = ""
#     try:
#         ai_fund = summarize_fundamentals_he(fundamentals.get("ai_input", "") or "")
#     except Exception:
#         ai_fund = ""

#     # 4) News + AI
#     news_ai = ""
#     try:
#         finnhub_ticker = ticker.replace("-", ".")
#         news = get_company_news(finnhub_ticker, days=7, limit=6)
#         news_ai = summarize_news_he(ticker, news, signal=signal)
#     except Exception:
#         news_ai = ""

#     # helpers
#     def esc(x) -> str:
#         s = "" if x is None else str(x)
#         return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

#     def fmt_pct(x):
#         return "—" if x is None else f"{x:.2f}%"

#     tech_reasons_html = "".join(f"<li>{esc(r)}</li>" for r in (tech.get("reasons") or [])) or "<li>—</li>"

#     if plan.get("ok"):
#         plan_html = f"""
#           <table class="table">
#             <tr><td class="k">אזור כניסה</td><td class="v">{esc(plan["entry_zone"]["low"])} – {esc(plan["entry_zone"]["high"])}</td></tr>
#             <tr><td class="k">סטופ לוס</td><td class="v"><b>{esc(plan["stop_loss"])}</b></td></tr>
#             <tr><td class="k">סיכון למניה</td><td class="v">{esc(plan["risk_per_share"])}</td></tr>
#             <tr><td class="k">יעד 1</td><td class="v">{esc(plan["tp1"])} <span class="muted">(RR {esc(plan["rr1"])})</span></td></tr>
#             <tr><td class="k">יעד 2</td><td class="v">{esc(plan["tp2"])} <span class="muted">(RR {esc(plan["rr2"])})</span></td></tr>
#             <tr><td class="k">ATR</td><td class="v">{esc(plan["atr"])}</td></tr>
#           </table>
#           <div class="note">
#             <div><b>היגיון סטופ:</b> {esc(plan["reasons"]["stop"])}</div>
#             <div><b>היגיון יעדים:</b> {esc(", ".join(plan["reasons"]["tp"]))}</div>
#           </div>
#         """
#     else:
#         plan_html = f"""
#           <div class="note warn">
#             לא נוצרה תוכנית עסקה: {esc(plan.get("reason", "—"))}
#           </div>
#         """

#     if checks:
#         checks_rows = "".join(
#             f"<tr><td class='k'>{esc(k)}</td><td class='v'>{esc(v)}</td></tr>"
#             for k, v in checks.items()
#         )
#         fundamentals_html = f"""
#           <table class="table">
#             {checks_rows}
#           </table>
#           <div class="note">
#             <b>מדדים:</b><br/>
#             P/E: {esc(metrics.get("pe"))} ·
#             צמיחת הכנסות (CAGR): {fmt_pct(None if metrics.get("rev_cagr") is None else metrics.get("rev_cagr")*100)} ·
#             צמיחת רווח נקי (CAGR): {fmt_pct(None if metrics.get("ni_cagr") is None else metrics.get("ni_cagr")*100)} ·
#             FCF (CAGR): {fmt_pct(None if metrics.get("fcf_cagr") is None else metrics.get("fcf_cagr")*100)}
#           </div>
#         """
#     else:
#         fundamentals_html = """
#           <div class="note warn">
#             לא הצלחתי למשוך נתונים פונדמנטליים כרגע.
#           </div>
#         """

#     ai_fund_html = ""
#     if ai_fund.strip():
#         ai_fund_html = f"""
#           <div class="card">
#             <div class="h3">🤖 סיכום פונדמנטלי (AI)</div>
#             <div class="ai">{esc(ai_fund)}</div>
#           </div>
#         """

#     news_ai_html = ""
#     if news_ai.strip():
#         news_ai_html = f"""
#           <div class="card">
#             <div class="h3">🗞️ News + AI</div>
#             <div class="ai">{esc(news_ai)}</div>
#           </div>
#         """

#     subject = f"📈 התראת סווינג | {ticker} | {signal} | ציון {tech.get('score')}/4"

#     html = f"""
#     <div style="font-family: Arial, Helvetica, sans-serif; direction: rtl; line-height: 1.6; background:#f5f7fb; padding:16px">
#       <style>
#         .wrap {{max-width: 760px; margin: 0 auto;}}
#         .header {{background:#ffffff; border-radius:12px; padding:16px; border:1px solid #e6e8ef;}}
#         .title {{font-size:20px; font-weight:700; margin:0 0 6px 0;}}
#         .sub {{color:#555; font-size:13px; margin:0;}}
#         .card {{background:#ffffff; border-radius:12px; padding:14px; border:1px solid #e6e8ef; margin-top:12px;}}
#         .h3 {{font-size:16px; font-weight:700; margin:0 0 10px 0;}}
#         .muted {{color:#666; font-size:12px;}}
#         .table {{width:100%; border-collapse: collapse;}}
#         .table td {{border:1px solid #e6e8ef; padding:8px; vertical-align:top;}}
#         .k {{width:45%; color:#333; background:#fafbff; font-weight:600;}}
#         .v {{width:55%;}}
#         .note {{margin-top:10px; padding:10px; border-radius:10px; background:#f7f7f7; border:1px solid #ececec;}}
#         .warn {{background:#fff6f6; border-color:#ffd2d2;}}
#         .ai {{background:#f6f6f6; padding:10px; border-radius:10px; border:1px solid #ececec; white-space:pre-wrap;}}
#         .footer {{margin-top:14px; color:#777; font-size:12px;}}
#       </style>

#       <div class="wrap">
#         <div class="header">
#           <div class="title">📊 התראת מסחר סווינג – {esc(ticker)}</div>
#           <p class="sub">
#             <b>טיימפריים:</b> {esc(interval)} ·
#             <b>סיגנל:</b> {esc(signal)} ·
#             <b>מחיר אחרון:</b> {esc(last_close)} ·
#             <b>UTC:</b> {esc(datetime.utcnow().isoformat(timespec="seconds"))}
#           </p>
#         </div>

#         <div class="card">
#           <div class="h3">🧠 ניתוח טכני (Confluence)</div>
#           <div><b>ציון:</b> {esc(tech.get("score"))} / 4</div>
#           <ul>{tech_reasons_html}</ul>
#         </div>

#         <div class="card">
#           <div class="h3">🎯 תוכנית מסחר (סיכון 1% לעסקה)</div>
#           {plan_html}
#         </div>

#         <div class="card">
#           <div class="h3">✅ צ’ק־ליסט טכני</div>
#           <table class="table">
#             <tr><td class="k">נר אחרון</td><td class="v">{esc(chk.get("candle"))}</td></tr>
#             <tr><td class="k">מגמה שבועית</td><td class="v">{esc(chk.get("trend_week_pct"))}%</td></tr>
#             <tr><td class="k">מגמה חודשית</td><td class="v">{esc(chk.get("trend_month_pct"))}%</td></tr>
#             <tr><td class="k">ווליום</td><td class="v">{esc(chk.get("volume"))}</td></tr>
#             <tr><td class="k">MA20</td><td class="v">{esc(chk.get("ma20"))}</td></tr>
#             <tr><td class="k">מצב כללי</td><td class="v">{esc(chk.get("bull_bear"))}</td></tr>
#           </table>
#         </div>

#         <div class="card">
#           <div class="h3">📘 פונדמנטלי (ארה״ב) — בדיקה מהירה</div>
#           {fundamentals_html}
#         </div>

#         {ai_fund_html}
#         {news_ai_html}

#         <div class="footer">
#           ⚠️ המידע נועד ללמידה ולמחקר בלבד ואינו מהווה ייעוץ השקעות.
#         </div>
#       </div>
#     </div>
#     """
#     return subject, html


# # ======================================================
# # Routes
# # ======================================================
# @app.get("/health")
# def health():
#     return {"ok": True}


# @app.post("/webhook/tradingview")
# def webhook(alert: TVAlert, db: Session = Depends(get_db)):
#     ticker = alert.ticker.upper()
#     signal = alert.signal.upper()
#     interval = alert.interval.upper()

#     saved = save_alert(db, ticker=ticker, signal=signal, interval=interval, price=alert.close)

#     key = f"{ticker}|{signal}|{interval}"
#     if not can_send(key):
#         return {"received": True, "sent": False, "reason": "dedup_or_rate_limit", "key": key, "db_id": saved.id}

#     subject, html = build_email(ticker=ticker, interval=interval, signal=signal, close=alert.close)
#     send_email(subject, html)
#     mark_sent(key)

#     return {"received": True, "sent": True, "key": key, "db_id": saved.id}

from __future__ import annotations

from fastapi import FastAPI

from app.api.routes_health import router as health_router
from app.api.routes_webhook import router as webhook_router

app = FastAPI(title="stocks-alerts")

app.include_router(health_router)
app.include_router(webhook_router)

