import hashlib
from sqlalchemy.orm import Session
from app.db.models_ai_cache import AiCache

def _hash_content(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_ai_cached_summary(db: Session, ticker: str, kind: str, content: str):
    h = _hash_content(content)
    row = (
        db.query(AiCache)
        .filter(
            AiCache.ticker == ticker,
            AiCache.kind == kind,
            AiCache.content_hash == h,
        )
        .first()
    )
    return row.summary_he if row else None


def save_ai_summary(db: Session, ticker: str, kind: str, content: str, summary_he: str):
    h = _hash_content(content)
    row = AiCache(
        ticker=ticker,
        kind=kind,
        content_hash=h,
        summary_he=summary_he,
    )
    db.add(row)
    try:
        db.commit()
    except Exception:
        db.rollback()
