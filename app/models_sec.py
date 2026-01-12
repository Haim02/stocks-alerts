from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from .db import Base

class SecReportCache(Base):
    __tablename__ = "sec_reports"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    cik10 = Column(String, nullable=True)
    form = Column(String, nullable=True)           # 10-K / 10-Q
    filing_date = Column(String, nullable=True)    # YYYY-MM-DD
    accession = Column(String, nullable=True)      # accessionNumber
    primary_doc = Column(String, nullable=True)
    sec_url = Column(String, nullable=True)

    ai_summary = Column(Text, nullable=True)       # סיכום AI לדוח
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
