# app/universe/sp500.py
from __future__ import annotations
from typing import List
import pandas as pd

WIKI_SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

def get_sp500_tickers() -> List[str]:
    tables = pd.read_html(WIKI_SP500_URL)
    # הטבלה הראשונה בדף היא רשימת החברות
    df = tables[0]
    tickers = df["Symbol"].astype(str).str.strip().tolist()
    # בוויקיפדיה יש לפעמים נקודה (BRK.B) -> yfinance מעדיף BRK-B
    tickers = [t.replace(".", "-") for t in tickers]
    return sorted(list(set(tickers)))
