from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint
from app.db import Base

class AiCache(Base):
    __tablename__ = "ai_cache"

    id = Column(Integer, primary_key=True)
    ticker = Column(String, nullable=False)
    kind = Column(String, nullable=False)
    # "news" | "fundamentals"

    content_hash = Column(String, nullable=False)
    summary_he = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("ticker", "kind", "content_hash", name="uq_ai_cache"),
    )
