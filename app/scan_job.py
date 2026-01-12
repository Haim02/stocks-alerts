import os
from datetime import datetime
import yfinance as yf

from app.universe_sp500 import get_sp500_tickers
from app.ta_engine import confluence_score, trade_plan
from app.emailer import send_email

# נשתמש באותו build_email של השרת כדי לקבל אותו מייל עשיר ומסודר
from app.main import build_email


# ===== Config =====
SCAN_TOP_N = int(os.getenv("SCAN_TOP_N", "20"))  # כמה מיילים מקסימום בכל ריצה
MIN_SCORE = int(os.getenv("SCAN_MIN_SCORE", "3"))  # 3/4 ומעלה

SCAN_MIN_PRICE = float(os.getenv("SCAN_MIN_PRICE", "5"))
SCAN_MIN_AVG_DOLLAR_VOL = float(os.getenv("SCAN_MIN_AVG_DOLLAR_VOL", "20000000"))  # $20M/day


def _download_1y_daily(ticker: str):
    df = yf.download(ticker, period="1y", interval="1d", auto_adjust=False, progress=False)

    # normalize columns (multi-index safe)
    if hasattr(df.columns, "levels"):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    df = df[["open", "high", "low", "close", "volume"]].dropna()
    return df


def _avg_dollar_volume(df) -> float:
    tail = df.tail(20)
    return float((tail["close"] * tail["volume"]).mean())


def main():
    started = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    tickers = get_sp500_tickers()

    candidates: list[dict] = []

    # 1) סריקה ראשונית: פילטרים + ציון טכני + תוכנית עסקה
    for t in tickers:
        try:
            df = _download_1y_daily(t)
            if df.empty:
                continue

            close = float(df["close"].iloc[-1])
            if close < SCAN_MIN_PRICE:
                continue

            adv = _avg_dollar_volume(df)
            if adv < SCAN_MIN_AVG_DOLLAR_VOL:
                continue

            tech = confluence_score(df)
            score = int(tech.get("score", 0))
            if score < MIN_SCORE:
                continue

            plan = trade_plan(df, tech, rr_min=2.0)
            if not plan.get("ok"):
                continue

            candidates.append(
                {
                    "ticker": t,
                    "score": score,
                    "close": round(close, 2),
                }
            )

        except Exception:
            continue

    # 2) מיון לפי score, ואז לוקחים TOP N כדי לא להציף
    candidates.sort(key=lambda x: x["score"], reverse=True)
    top = candidates[:SCAN_TOP_N]

    if not top:
        subject = f"🔎 סריקה אוטומטית (S&P 500) — אין מועמדות — {started}"
        html = (
            "<div style='direction:rtl;font-family:Arial'>"
            "לא נמצאו מועמדות שעברו פילטרים בסריקה הנוכחית."
            "</div>"
        )
        send_email(subject, html)
        return

    # 3) מייל לכל מניה (מייל מלא עם News+AI + Fundamentals וכו' דרך build_email)
    for item in top:
        t = item["ticker"]
        close = item["close"]

        try:
            subject, html = build_email(
                ticker=t,
                interval="1D",
                signal="SCAN_TOP",
                close=close,
            )
            send_email(subject, html)
        except Exception:
            # אם מניה אחת נופלת—לא מפילים את כל הריצה
            continue

    # אופציונלי: מייל סיום קצר (אם תרצה)
    # subject = f"✅ סריקה הסתיימה — נשלחו {len(top)} מיילים — {started}"
    # html = f"<div style='direction:rtl;font-family:Arial'>נשלחו {len(top)} מיילים.</div>"
    # send_email(subject, html)


if __name__ == "__main__":
    main()
