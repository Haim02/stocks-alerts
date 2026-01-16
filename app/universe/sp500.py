# app/universe/sp500.py
# from __future__ import annotations
# from typing import List
# import pandas as pd

# WIKI_SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

# def get_sp500_tickers() -> List[str]:
#     tables = pd.read_html(WIKI_SP500_URL)
#     # הטבלה הראשונה בדף היא רשימת החברות
#     df = tables[0]
#     tickers = df["Symbol"].astype(str).str.strip().tolist()
#     # בוויקיפדיה יש לפעמים נקודה (BRK.B) -> yfinance מעדיף BRK-B
#     tickers = [t.replace(".", "-") for t in tickers]
#     return sorted(list(set(tickers)))


# app/universe/sp500.py
from __future__ import annotations

import os
import pandas as pd
import requests
from io import StringIO

WIKI_SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0 Safari/537.36"
)

def get_sp500_tickers() -> list[str]:
    """
    מחזיר רשימת טיקרים של S&P 500 בצורה יציבה.
    פותר 403 של Wikipedia ע"י בקשת HTTP עם User-Agent.
    """
    ua = os.getenv("HTTP_USER_AGENT", DEFAULT_UA)

    resp = requests.get(
        WIKI_SP500_URL,
        headers={"User-Agent": ua, "Accept-Language": "en-US,en;q=0.9"},
        timeout=30,
    )
    resp.raise_for_status()

    # קוראים את הטבלאות מתוך ה-HTML שהבאנו בעצמנו
    tables = pd.read_html(StringIO(resp.text))
    if not tables:
        raise RuntimeError("No tables found on Wikipedia page")

    df = tables[0]  # הטבלה הראשונה היא ה-S&P 500
    # לפעמים העמוד משנה שמות עמודות - ננסה להיות גמישים:
    symbol_col = None
    for c in df.columns:
        if str(c).lower() in ("symbol", "ticker", "ticker symbol"):
            symbol_col = c
            break
    if symbol_col is None:
        symbol_col = df.columns[0]

    tickers = df[symbol_col].astype(str).tolist()

    # ויקיפדיה משתמשת בנקודה במקום מקף (BRK.B) אבל ב-yfinance צריך BRK-B
    tickers = [t.replace(".", "-").strip().upper() for t in tickers if t and t != "nan"]

    return tickers
