import os
import re
import time
import requests
from bs4 import BeautifulSoup

SEC_UA = os.getenv("SEC_USER_AGENT", "")
HEADERS = {"User-Agent": SEC_UA, "Accept-Encoding": "gzip, deflate"}

BASE = "https://data.sec.gov"
SUBMISSIONS = "https://data.sec.gov/submissions"


def _sec_get(url: str, sleep_s: float = 0.2) -> requests.Response:
    if not SEC_UA:
        raise RuntimeError("SEC_USER_AGENT is missing in .env")
    time.sleep(sleep_s)  # להיות נחמדים ל-SEC
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r


def get_cik_by_ticker(ticker: str) -> str | None:
    # SEC publishes a json mapping tickers->cik
    # (עדיף קאש בהמשך; ב-MVP מספיק)
    r = _sec_get("https://www.sec.gov/files/company_tickers.json")
    data = r.json()
    t = ticker.upper()

    for _, row in data.items():
        if str(row.get("ticker", "")).upper() == t:
            cik = str(row.get("cik_str"))
            return cik.zfill(10)
    return None


def get_recent_filings(cik10: str) -> dict:
    url = f"{SUBMISSIONS}/CIK{cik10}.json"
    return _sec_get(url).json()


def find_latest_10k_10q(submissions_json: dict) -> dict | None:
    """
    מחזיר dict עם {form, accessionNumber, filingDate, primaryDocument}
    """
    recent = submissions_json.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accs = recent.get("accessionNumber", [])
    dates = recent.get("filingDate", [])
    prim = recent.get("primaryDocument", [])

    best = None
    for form, acc, dt, doc in zip(forms, accs, dates, prim):
        if form not in ("10-K", "10-Q"):
            continue
        best = {"form": form, "accessionNumber": acc, "filingDate": dt, "primaryDocument": doc}
        break

    return best


def download_primary_doc_text(cik10: str, accession: str, primary_doc: str) -> str:
    # accession in submissions has dashes; in URL we need no dashes
    acc_nodash = accession.replace("-", "")
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik10)}/{acc_nodash}/{primary_doc}"
    html = _sec_get(url).text

    soup = BeautifulSoup(html, "lxml")
    # remove scripts/styles
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n")

    # clean
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    return text


def extract_sections(text: str, max_chars: int = 18000) -> dict[str, str]:
    """
    MVP: מחלץ קטעים בקירוב לפי כותרות נפוצות.
    לא מושלם אבל עובד.
    """
    lower = text.lower()

    def grab(start_keywords, end_keywords):
        # find first start
        start = None
        for kw in start_keywords:
            i = lower.find(kw)
            if i != -1:
                start = i
                break
        if start is None:
            return ""
        end = None
        for kw in end_keywords:
            j = lower.find(kw, start + 50)
            if j != -1:
                end = j
                break
        chunk = text[start:end] if end else text[start:]
        return chunk[:max_chars].strip()

    risk = grab(
        ["risk factors", "item 1a", "item 1a."],
        ["management’s discussion", "management's discussion", "md&a", "item 7", "item 2"]
    )
    mda = grab(
        ["management’s discussion", "management's discussion", "md&a", "item 7", "item 2"],
        ["financial statements", "item 8", "item 3", "quantitative and qualitative"]
    )
    results = grab(
        ["results of operations", "item 2.", "item 7."],
        ["liquidity", "capital resources", "cash flows", "item 3", "item 8"]
    )

    return {
        "risk_factors": risk,
        "mda": mda,
        "results": results,
    }
