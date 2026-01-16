# from __future__ import annotations

# from typing import Any, Dict, List

# import requests
# from openai import OpenAI

# from app.core.settings import NEWSAPI_KEY, OPENAI_API_KEY


# def _fetch_news_basic(ticker: str, limit: int = 6) -> List[Dict[str, Any]]:
#     """
#     גרסה בסיסית:
#     - אם יש NEWSAPI_KEY → נביא כתבות מ-NewsAPI
#     - אם אין → נחזיר רשימה ריקה (ועדיין ה-AI יעבוד על מה שיש מה-TV)
#     """
#     if not NEWSAPI_KEY:
#         return []

#     url = "https://newsapi.org/v2/everything"
#     params = {
#         "q": ticker,
#         "pageSize": str(limit),
#         "sortBy": "publishedAt",
#         "apiKey": NEWSAPI_KEY,
#         "language": "en",
#     }
#     r = requests.get(url, params=params, timeout=15)
#     r.raise_for_status()
#     data = r.json()
#     articles = data.get("articles", []) or []

#     out = []
#     for a in articles[:limit]:
#         out.append(
#             {
#                 "title": a.get("title"),
#                 "source": (a.get("source") or {}).get("name"),
#                 "publishedAt": a.get("publishedAt"),
#                 "url": a.get("url"),
#                 "description": a.get("description"),
#             }
#         )
#     return out


# def summarize_news_with_ai(*, ticker: str, tv_payload: Dict[str, Any]) -> Dict[str, str]:
#     """
#     מחזיר:
#       - news_summary: סיכום חדשות קצר
#       - why_now: למה זה מעניין עכשיו (מחבר בין TV+חדשות)
#       - risks: סיכונים מרכזיים
#     """
#     if not OPENAI_API_KEY:
#         return {
#             "news_summary": "OPENAI_API_KEY missing → skipping AI summary.",
#             "why_now": "",
#             "risks": "",
#         }

#     news = _fetch_news_basic(ticker)
#     client = OpenAI(api_key=OPENAI_API_KEY)

#     prompt = {
#         "ticker": ticker,
#         "tv": tv_payload,
#         "news": news,
#         "task": (
#             "Write in Hebrew. Give: (1) short news summary (2) why now "
#             "(connect TV signal + news) (3) key risks. Be concise."
#         ),
#     }

#     # דוגמת Responses API בפייתון :contentReference[oaicite:1]{index=1}
#     resp = client.chat.completions.create(
#         model="gpt-3.5-turbo",
#         messages=str(prompt)
#     )

#     text = getattr(resp, "output_text", None) or ""
#     # פיצול פשוט: אם תרצה, נבנה JSON אמיתי בהמשך.
#     return {
#         "news_summary": text.strip(),
#         "why_now": "",
#         "risks": "",
#     }


# app/services/news_ai.py
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_APIKEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY env var")
    return OpenAI(api_key=api_key)


def summarize_news_with_ai(
    *,
    ticker: str,
    tv_payload: Optional[Dict[str, Any]] = None,
    max_chars: int = 1200,
) -> Dict[str, Any]:
    """
    מחזיר dict:
    {
      "ok": bool,
      "summary": str,
      "model": str,
      "error": str|None
    }
    """
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    tv_payload = tv_payload or {}
    ctx = {
        "ticker": ticker,
        "signal": tv_payload.get("signal"),
        "interval": tv_payload.get("interval"),
        "close": tv_payload.get("close"),
        "volume": tv_payload.get("volume"),
        "rsi": tv_payload.get("rsi"),
        "ma20": tv_payload.get("ma20"),
        "ma50": tv_payload.get("ma50"),
        "ma200": tv_payload.get("ma200"),
        "trend": tv_payload.get("trend"),
        "support": tv_payload.get("support"),
        "resistance": tv_payload.get("resistance"),
        "bullDiv": tv_payload.get("bullDiv"),
        "bearDiv": tv_payload.get("bearDiv"),
    }

    system = (
        "אתה מסכם חדשות שוק. תחזיר בעברית, קצר וברור, עם נקודות.\n"
        "מבנה חובה:\n"
        "1) מה קרה לאחרונה (כותרות/אירועים מרכזיים)\n"
        "2) סיכונים\n"
        "3) תרחישים אפשריים\n"
        "בלי חפירות, עד 8 נקודות סה\"כ."
    )

    user = (
        f"סכם חדשות רלוונטיות ל-{ticker} והקשר לטכני/סיגנל.\n"
        f"Context (from TradingView payload): {ctx}\n"
        "אם אין מספיק מידע חדשותי ודאי—תכתוב 'אין מספיק חדשות חד-משמעיות' ותמשיך לסיכונים/תרחישים."
    )

    try:
        client = _get_client()

        # ✅ רק Chat Completions
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.4,
        )

        text = (resp.choices[0].message.content or "").strip()
        if not text:
            return {
                "ok": False,
                "summary": "לא הצלחתי להפיק סיכום AI כרגע.",
                "model": model,
                "error": "empty_response",
            }

        if len(text) > max_chars:
            text = text[: max_chars - 3] + "..."

        return {"ok": True, "summary": text, "model": model, "error": None}

    except Exception as e:
        # ⭐ לא מפילים webhook אם OpenAI נופל
        return {
            "ok": False,
            "summary": "⚠️ סיכום AI לא זמין כרגע (נשלח מייל בלי AI).",
            "model": model,
            "error": str(e),
        }
