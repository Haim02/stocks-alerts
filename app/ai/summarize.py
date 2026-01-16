# app/ai/summarize.py
from __future__ import annotations

import os
from typing import Any, Dict, List

from openai import OpenAI


def _client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY")
    return OpenAI(api_key=api_key)


def build_ai_prompt(candidate: Dict[str, Any]) -> str:
    """
    candidate לדוגמה:
    {
      "ticker": "AAPL",
      "signal": "BREAKOUT",
      "interval": "1D",
      "notes": "...",
    }
    """
    ticker = candidate.get("ticker")
    signal = candidate.get("signal")
    interval = candidate.get("interval")
    notes = candidate.get("notes", "")

    return f"""
You are a swing trading assistant. Provide a concise, practical analysis (no execution instructions).
Ticker: {ticker}
Signal: {signal}
Interval: {interval}
Notes/context: {notes}

Return in Hebrew with this structure:
1) למה עכשיו? (2-4 נקודות)
2) תרחישים אפשריים + סיכונים (3-6 נקודות)
3) רעיון אסטרטגיה (לא ביצוע) — כללי בלבד (2-4 נקודות)
4) מה הייתי מחפש באישור נוסף (2-4 נקודות)

Keep it short and actionable.
""".strip()


def summarize_one(candidate: Dict[str, Any]) -> str:
    """
    מחזיר Markdown קצר למניה אחת
    """
    c = _client()
    prompt = build_ai_prompt(candidate)

    resp = c.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": "You are a careful financial assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
    )
    return resp.choices[0].message.content or ""


def render_email_html(results: List[Dict[str, Any]]) -> str:
    """
    results:
    [
      {"ticker":"AAPL","signal":"BREAKOUT","ai_md":"..."},
      ...
    ]
    """
    rows = []
    for r in results:
        rows.append(
            f"""
            <div style="margin-bottom:18px; padding:12px; border:1px solid #ddd; border-radius:8px;">
              <div style="font-size:16px; font-weight:bold;">
                {r.get("ticker")} — {r.get("signal")}
              </div>
              <pre style="white-space:pre-wrap; font-family:Arial, sans-serif; margin-top:8px;">
{r.get("ai_md","").strip()}
              </pre>
            </div>
            """.strip()
        )

    return "<br/>".join(rows)
