import os
from openai import OpenAI

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.2")

def summarize_report_he(ticker: str, form: str, filing_date: str, sections: dict[str, str]) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return ""

    client = OpenAI(api_key=api_key)

    prompt = (
        f"אתה אנליסט סווינג. יש לך קטעים מתוך דוח {form} של {ticker} שדווח בתאריך {filing_date}.\n"
        "סכם בעברית, קצר וברור:\n"
        "1) מה 2–3 הנקודות החשובות בדוח (בולטים)\n"
        "2) 2 סיכונים מרכזיים (Risk Factors)\n"
        "3) 'מה יכול להזיז מחיר' בשבועות הקרובים\n"
        "4) שורה אחת: מה הייתי מחפש בחדשות/אירועים סביב החברה\n"
        "אל תצטט משפטים ארוכים. כתוב 6–10 שורות.\n\n"
        f"--- Risk Factors ---\n{sections.get('risk_factors','')}\n\n"
        f"--- MD&A ---\n{sections.get('mda','')}\n\n"
        f"--- Results ---\n{sections.get('results','')}\n"
    )

    resp = client.responses.create(model=OPENAI_MODEL, input=prompt)
    return (resp.output_text or "").strip()
