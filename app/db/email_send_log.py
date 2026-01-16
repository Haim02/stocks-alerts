# app/db/models/email_send_log.py
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base  # שנה אם אצלך זה Base במקום אחר


class EmailSendLog(Base):
    __tablename__ = "email_send_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    ticker: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    signal: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)

    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        index=True,
    )

