from sqlalchemy import Column, Integer, String, DateTime, Float
from datetime import datetime
from .db import Base

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    signal = Column(String, index=True, nullable=False)     # BREAKOUT / REBOUND
    interval = Column(String, index=True, nullable=False)   # 1D
    price = Column(Float, nullable=True)
    received_at = Column(DateTime, default=datetime.utcnow, index=True)
