# app/models_news.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint
from .db import Base

class NewsCache(Base):
    __tablename__ = "news_cache"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    url = Column(String, nullable=False)
    headline = Column(String, nullable=False)
    source = Column(String, nullable=True)
    datetime_utc = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("ticker", "url", name="uq_news_ticker_url"),
    )
