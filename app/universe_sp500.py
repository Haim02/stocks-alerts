import pandas as pd

WIKI_SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


def get_sp500_tickers() -> list[str]:
    tables = pd.read_html(WIKI_SP500_URL)
    df = tables[0]
    tickers = df["Symbol"].astype(str).str.strip().tolist()
    # Yahoo format: BRK.B -> BRK-B
    return [t.replace(".", "-") for t in tickers if t and t != "nan"]
