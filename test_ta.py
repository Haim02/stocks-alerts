import yfinance as yf
from app.ta_engine import confluence_score, trade_plan, checklist_technical

ticker = "AAPL"
df = yf.download(ticker, period="1y", interval="1d", auto_adjust=False, progress=False)

# אם יש MultiIndex בעמודות (common ב-yfinance)
if hasattr(df.columns, "levels"):
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

df = df.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close","Volume":"volume"})
df = df[["open","high","low","close","volume"]].dropna()

tech = confluence_score(df)
plan = trade_plan(df, tech, rr_min=2.0)
chk = checklist_technical(df, tech)

print("Score:", tech["score"])
print("Reasons:", tech["reasons"])
print("Plan OK:", plan.get("ok"), plan.get("reason"))
print("Checklist:", chk)
