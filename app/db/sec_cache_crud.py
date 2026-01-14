from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .models_sec import SecReportCache

def get_cached_report(db: Session, ticker: str) -> SecReportCache | None:
    return db.query(SecReportCache).filter(SecReportCache.ticker == ticker).first()

def upsert_cached_report(
    db: Session,
    ticker: str,
    cik10: str | None,
    form: str | None,
    filing_date: str | None,
    accession: str | None,
    primary_doc: str | None,
    sec_url: str | None,
    ai_summary: str | None,
):
    row = get_cached_report(db, ticker)
    if not row:
        row = SecReportCache(ticker=ticker)
        db.add(row)

    row.cik10 = cik10
    row.form = form
    row.filing_date = filing_date
    row.accession = accession
    row.primary_doc = primary_doc
    row.sec_url = sec_url
    row.ai_summary = ai_summary
    row.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(row)
    return row

def cache_is_fresh(row: SecReportCache | None, max_age_hours: int = 24) -> bool:
    if not row or not row.updated_at:
        return False
    return (datetime.utcnow() - row.updated_at) < timedelta(hours=max_age_hours)
