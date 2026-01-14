# app/scanners/sp500.py
from __future__ import annotations

from typing import List

import httpx
from bs4 import BeautifulSoup


WIKI_SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


async def fetch_sp500_tickers() -> List[str]:
    """
    מביא רשימת S&P 500 מויקיפדיה (פשוט ואמין).
    """
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(WIKI_SP500_URL)
        r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table", {"id": "constituents"})
    if not table:
        raise RuntimeError("S&P 500 table not found")

    tickers: List[str] = []
    rows = table.find_all("tr")
    for row in rows[1:]:
        cols = row.find_all("td")
        if not cols:
            continue
        ticker = cols[0].get_text(strip=True)
        # ב-Yahoo/פעמים יש פורמט BRK.B במקום BRK-B
        ticker = ticker.replace(".", "-")
        tickers.append(ticker)

    return tickers
