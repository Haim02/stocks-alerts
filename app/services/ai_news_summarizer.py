import os
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()


def summarize_news_he(ticker: str, news: list[dict], signal: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY missing in environment")

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    items = []
    for n in (news or [])[:6]:
        items.append(
            f"- {n.get('headline','')}\n"
            f"  מקור: {n.get('source','')}\n"
            f"  תקציר: {n.get('summary','')}\n"
            f"  זמן: {n.get('datetime_utc','')}\n"
        )

    prompt = f"""
אתה עוזר מחקר למסחר סווינג. כתוב בעברית סיכום חדשות קצר ומעשי לטיקר {ticker}.
הסיגנל: {signal}
זמן: {datetime.utcnow().isoformat(timespec="seconds")} UTC

הנחיות:
- 4–7 נקודות בולטים
- מה עשוי להזיז מחיר בטווח ימים/שבועות
- האם החדשות תומכות או סותרות את הסיגנל
- בסוף: "סיכון מרכזי אחד" + "מה לבדוק בהמשך"

חדשות:
{chr(10).join(items) if items else "אין חדשות משמעותיות שנמשכו."}
""".strip()

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "ענה בעברית, תמציתי, פרקטי. בלי ייעוץ השקעות."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    return (resp.choices[0].message.content or "").strip()
