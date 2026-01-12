import os
from app.ai_summarizer import summarize_fundamentals_he

print("KEY?", bool(os.getenv("OPENAI_API_KEY")))
txt = "טיקר: AAPL\nP/E: 18\nRevenue CAGR: 8%\nNet Income CAGR: 7%\nMargins: במגמת עלייה\nAssets: 100 | Liabilities: 60\nFCF CAGR: 9%\n"
print(summarize_fundamentals_he(txt))
