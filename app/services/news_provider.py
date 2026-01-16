# app/news_provider.py
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
load_dotenv()

import requests


FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "").strip()
FINNHUB_BASE = "https://finnhub.io/api/v1"


def _utc_date_str(dt: datetime) -> str:
    # Finnhub expects YYYY-MM-DD
    return dt.strftime("%Y-%m-%d")


def get_company_news(
    ticker: str,
    days: int = 14,
    limit: int = 8,
    session: Optional[requests.Session] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch recent company news from Finnhub.
    Returns a clean list of items (headline, summary, source, url, datetime_utc).

    Notes:
    - Works best for US tickers.
    - Requires FINNHUB_API_KEY in .env
    """
    if not FINNHUB_API_KEY:
        raise RuntimeError("FINNHUB_API_KEY is missing in environment (.env)")

    t = ticker.upper().strip()
    if not t:
        return []

    now = datetime.now(timezone.utc)
    frm = now - timedelta(days=days)

    params = {
        "symbol": t,
        "from": _utc_date_str(frm),
        "to": _utc_date_str(now),
        "token": FINNHUB_API_KEY,
    }

    s = session or requests.Session()
    url = f"{FINNHUB_BASE}/company-news"
    resp = s.get(url, params=params, timeout=20)
    resp.raise_for_status()

    data = resp.json()
    if not isinstance(data, list):
        return []

    # Normalize and filter
    cleaned: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue

        headline = (item.get("headline") or "").strip()
        summary = (item.get("summary") or "").strip()
        source = (item.get("source") or "").strip()
        link = (item.get("url") or "").strip()
        ts = item.get("datetime")

        # basic quality filters
        if not headline:
            continue

        # Finnhub datetime is epoch seconds
        dt_utc = None
        try:
            if ts is not None:
                dt_utc = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        except Exception:
            dt_utc = None

        cleaned.append(
            {
                "headline": headline,
                "summary": summary,
                "source": source or "—",
                "url": link or "",
                "datetime_utc": dt_utc.isoformat(timespec="seconds") if dt_utc else "",
            }
        )

    # Sort newest first
    cleaned.sort(key=lambda x: x.get("datetime_utc", ""), reverse=True)

    # Dedup headlines (simple)
    seen = set()
    uniq: List[Dict[str, Any]] = []
    for it in cleaned:
        key = it["headline"].lower()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(it)

    return uniq[: max(1, int(limit))]
