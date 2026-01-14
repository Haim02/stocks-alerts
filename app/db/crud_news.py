# app/crud_news.py
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.models_news import NewsCache


def get_recent_news_for_ticker(db: Session, ticker: str, minutes: int = 60):
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    return (
        db.query(NewsCache)
        .filter(NewsCache.ticker == ticker, NewsCache.created_at >= cutoff)
        .order_by(desc(NewsCache.created_at))
        .all()
    )


def upsert_news_items(db: Session, ticker: str, items: list[dict]):
    """
    Insert news items; ignores duplicates by (ticker,url) unique constraint.
    """
    inserted = 0
    for it in items:
        url = (it.get("url") or "").strip()
        headline = (it.get("headline") or "").strip()
        if not url or not headline:
            continue

        row = NewsCache(
            ticker=ticker,
            url=url,
            headline=headline,
            source=(it.get("source") or ""),
            datetime_utc=(it.get("datetime_utc") or ""),
        )
        db.add(row)
        try:
            db.commit()
            inserted += 1
        except Exception:
            db.rollback()  # duplicate or other constraint issue -> ignore
            continue

    return inserted
