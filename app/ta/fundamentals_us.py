from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import math

import pandas as pd
import yfinance as yf


def _safe_float(x) -> float | None:
    try:
        if x is None:
            return None
        if isinstance(x, (int, float)):
            return float(x)
        if hasattr(x, "item"):
            return float(x.item())
        return float(x)
    except Exception:
        return None


def _cagr(start: float | None, end: float | None, years: float) -> float | None:
    if start is None or end is None or years <= 0:
        return None
    if start <= 0 or end <= 0:
        return None
    return (end / start) ** (1 / years) - 1


def _last_n_annual(series: pd.Series, n: int = 5) -> list[tuple[pd.Timestamp, float]]:
    """
    yfinance financials בדרך כלל: עמודות = תאריכים, אינדקס = סעיפים
    אנחנו רוצים סדר מהישן לחדש.
    """
    items = []
    for col in series.index:
        val = _safe_float(series[col])
        if val is not None:
            items.append((pd.to_datetime(col), val))
    items.sort(key=lambda x: x[0])  # old -> new
    return items[-n:]


def _status(pass_cond: bool | None) -> str:
    if pass_cond is None:
        return "⚠️ אין נתון"
    return "✅ עובר" if pass_cond else "❌ לא עובר"


def fetch_fundamentals_us(ticker: str) -> dict[str, Any]:
    """
    MVP Fundamentals (US) דרך yfinance.
    מחזיר:
    - metrics
    - checks (pass/fail לפי הקריטריונים שלך)
    - short_data_for_ai (טקסט קצר להזנה ל-LLM)
    """
    t = yf.Ticker(ticker)
    info = {}
    try:
        info = t.info or {}
    except Exception:
        info = {}

    # --- P/E + Shares
    pe = _safe_float(info.get("trailingPE") or info.get("forwardPE"))
    shares = _safe_float(info.get("sharesOutstanding"))

    # --- Annual statements
    financials = getattr(t, "financials", None)
    cashflow = getattr(t, "cashflow", None)
    balance = getattr(t, "balance_sheet", None)

    # Revenue & Net Income growth (3–5y)
    rev_cagr = None
    ni_cagr = None
    margin_trend = None  # up / down / flat / unknown
    fcf_cagr = None
    shares_trend_pct = None  # placeholder (yfinance לא תמיד נותן היסטוריה נקייה)

    # revenue
    try:
        if isinstance(financials, pd.DataFrame) and not financials.empty:
            # revenue row names vary
            rev_row = None
            for name in ["Total Revenue", "TotalRevenue"]:
                if name in financials.index:
                    rev_row = name
                    break
            ni_row = None
            for name in ["Net Income", "NetIncome"]:
                if name in financials.index:
                    ni_row = name
                    break

            if rev_row:
                items = _last_n_annual(financials.loc[rev_row], n=5)
                if len(items) >= 4:
                    # 3 שנים בין 4 נקודות
                    years = (items[-1][0] - items[-4][0]).days / 365.25
                    rev_cagr = _cagr(items[-4][1], items[-1][1], years)

            if ni_row:
                items = _last_n_annual(financials.loc[ni_row], n=5)
                if len(items) >= 4:
                    years = (items[-1][0] - items[-4][0]).days / 365.25
                    ni_cagr = _cagr(items[-4][1], items[-1][1], years)

            # Profit margin trend (NetIncome/Revenue) over last 3 annual points if possible
            if rev_row and ni_row:
                rev_items = _last_n_annual(financials.loc[rev_row], n=5)
                ni_items = _last_n_annual(financials.loc[ni_row], n=5)
                # align by nearest dates
                pairs = []
                for d, r in rev_items[-3:]:
                    ni_match = min(ni_items, key=lambda x: abs((x[0] - d).days))
                    if r and ni_match[1] is not None:
                        pairs.append((d, ni_match[1] / r))
                if len(pairs) >= 2:
                    if pairs[-1][1] > pairs[0][1] * 1.05:
                        margin_trend = "📈 במגמת עלייה"
                    elif pairs[-1][1] < pairs[0][1] * 0.95:
                        margin_trend = "📉 במגמת ירידה"
                    else:
                        margin_trend = "➖ יציב"
    except Exception:
        pass

    # Assets vs Liabilities
    assets_gt_liab = None
    total_assets = None
    total_liab = None
    try:
        if isinstance(balance, pd.DataFrame) and not balance.empty:
            a_row = None
            l_row = None
            for name in ["Total Assets", "TotalAssets"]:
                if name in balance.index:
                    a_row = name
                    break
            for name in ["Total Liab", "TotalLiab", "Total Liabilities Net Minority Interest"]:
                if name in balance.index:
                    l_row = name
                    break
            if a_row and l_row:
                # take most recent column
                col = balance.columns[0]
                total_assets = _safe_float(balance.loc[a_row, col])
                total_liab = _safe_float(balance.loc[l_row, col])
                if total_assets is not None and total_liab is not None:
                    assets_gt_liab = total_assets > total_liab
    except Exception:
        pass

    # FCF growth (Operating CF - CapEx)
    try:
        if isinstance(cashflow, pd.DataFrame) and not cashflow.empty:
            ocf_row = None
            capex_row = None
            for name in ["Total Cash From Operating Activities", "Operating Cash Flow", "OperatingCashFlow"]:
                if name in cashflow.index:
                    ocf_row = name
                    break
            for name in ["Capital Expenditures", "CapitalExpenditures"]:
                if name in cashflow.index:
                    capex_row = name
                    break

            if ocf_row and capex_row:
                # compute fcf series
                ocf = cashflow.loc[ocf_row]
                capex = cashflow.loc[capex_row]
                fcf = ocf.add(capex, fill_value=0)  # capex usually negative; add works
                items = _last_n_annual(fcf, n=5)
                if len(items) >= 4:
                    years = (items[-1][0] - items[-4][0]).days / 365.25
                    fcf_cagr = _cagr(items[-4][1], items[-1][1], years)
    except Exception:
        pass

    # --- Checks לפי הקריטריונים שלך
    pe_ok = (pe is not None and pe < 20)
    rev_ok = (rev_cagr is not None and rev_cagr > 0.06)
    ni_ok = (ni_cagr is not None and ni_cagr > 0.06)
    margin_ok = None
    if margin_trend is not None:
        margin_ok = ("עלייה" in margin_trend) or ("יציב" in margin_trend)

    assets_ok = assets_gt_liab if assets_gt_liab is not None else None
    fcf_ok = (fcf_cagr is not None and fcf_cagr > 0.06)

    # shares trend – כרגע “אין נתון” ב-MVP (נוסיף מאוחר יותר ממקור אחר)
    shares_ok = None

    checks = {
        "P/E < 20": _status(pe_ok if pe is not None else None),
        "צמיחת הכנסות 3–5 שנים > 6%": _status(rev_ok if rev_cagr is not None else None),
        "צמיחת רווח נקי 3–5 שנים > 6%": _status(ni_ok if ni_cagr is not None else None),
        "שולי רווח במגמת עלייה/יציב": _status(margin_ok),
        "נכסים > התחייבויות": _status(assets_ok),
        "צמיחת FCF 3–5 שנים > 6%": _status(fcf_ok if fcf_cagr is not None else None),
        "מניות מונפקות לא עלו משמעותית (3–5y)": _status(shares_ok),
    }

    metrics = {
        "pe": pe,
        "rev_cagr": rev_cagr,
        "ni_cagr": ni_cagr,
        "margin_trend": margin_trend,
        "total_assets": total_assets,
        "total_liab": total_liab,
        "fcf_cagr": fcf_cagr,
        "shares_outstanding": shares,
    }

    short_ai = (
        f"טיקר: {ticker}\n"
        f"P/E: {pe}\n"
        f"Revenue CAGR (3y approx): {None if rev_cagr is None else round(rev_cagr*100,2)}%\n"
        f"Net Income CAGR (3y approx): {None if ni_cagr is None else round(ni_cagr*100,2)}%\n"
        f"Margins: {margin_trend}\n"
        f"Assets: {total_assets} | Liabilities: {total_liab}\n"
        f"FCF CAGR (3y approx): {None if fcf_cagr is None else round(fcf_cagr*100,2)}%\n"
        f"Shares outstanding: {shares}\n"
    )

    return {"metrics": metrics, "checks": checks, "ai_input": short_ai}
