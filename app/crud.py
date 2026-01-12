from sqlalchemy.orm import Session
from .models import Alert

def save_alert(db: Session, ticker: str, signal: str, interval: str, price: float | None):
    row = Alert(ticker=ticker, signal=signal, interval=interval, price=price)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
