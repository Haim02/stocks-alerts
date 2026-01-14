def why_now_sentence(tech: dict, plan: dict, news_ai: dict) -> str:
    parts = []

    if tech.get("score", 0) >= 3:
        parts.append("המניה נמצאת באזור טכני משמעותי")

    if plan.get("ok"):
        parts.append("עם יחס סיכוי-סיכון חיובי")

    if news_ai.get("sentiment") == "Bullish":
        parts.append("ובתמיכת חדשות חיוביות מהשבוע האחרון")

    if not parts:
        return "קיימת התכנסות ראשונית של גורמים, אך נדרש אישור נוסף."

    return " ".join(parts) + "."
