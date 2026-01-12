def confidence_score(tech: dict, news_ai: dict, fundamentals: dict) -> dict:
    score = 0
    reasons = []

    # 🧠 Technical (0–40)
    tech_score = tech.get("score", 0) / 4 * 40
    score += tech_score
    reasons.append(f"טכני: {round(tech_score)}%")

    # 📰 News (0–30)
    sentiment = news_ai.get("sentiment", "Neutral")
    news_map = {"Bullish": 30, "Neutral": 15, "Risky": 0}
    news_score = news_map.get(sentiment, 15)
    score += news_score
    reasons.append(f"חדשות: {news_score}% ({sentiment})")

    # 📘 Fundamentals (0–30)
    checks = fundamentals.get("checks", {})
    passed = sum(1 for v in checks.values() if v in ("✔", "Yes", True))
    total = len(checks) or 1
    fund_score = passed / total * 30
    score += fund_score
    reasons.append(f"פונדמנטלי: {round(fund_score)}%")

    return {
        "score": round(score),
        "reasons": reasons,
        "level": (
            "גבוה מאוד" if score >= 75 else
            "בינוני-גבוה" if score >= 60 else
            "בינוני" if score >= 45 else
            "נמוך"
        )
    }
