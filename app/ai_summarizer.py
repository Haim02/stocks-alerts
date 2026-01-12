import os
from openai import OpenAI

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.2")


def summarize_fundamentals_he(ai_input: str) -> str:
    """
    מחזיר 4–6 שורות בעברית:
    - 2 נקודות חיוביות
    - 1–2 סיכונים
    - מה יכול להזיז מחיר
    אם אין OPENAI_API_KEY → מחזיר מחרוזת ריקה (לא מפיל שרת!)
    """

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return ""

    try:
        client = OpenAI(api_key=api_key)

        prompt = (
            "אתה אנליסט סווינג.\n"
            "סכם בקצרה ובבהירות את מצב החברה לפי הנתונים.\n"
            "תן:\n"
            "1) שתי נקודות חיוביות\n"
            "2) 1–2 סיכונים\n"
            "3) שורה אחת: מה עשוי להזיז מחיר בקרוב\n\n"
            "ענה בעברית, 4–6 שורות, בלי חפירות.\n\n"
            f"נתונים:\n{ai_input}"
        )

        resp = client.responses.create(
            model=OPENAI_MODEL,
            input=prompt,
        )

        return (resp.output_text or "").strip()

    except Exception as e:
        # ⚠️ לא מפילים מערכת בגלל AI
        print("AI summary error:", e)
        return ""
