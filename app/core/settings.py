from __future__ import annotations

import os


def env(name: str, default: str | None = None) -> str | None:
    val = os.getenv(name)
    return val if val is not None and val != "" else default


# Email
EMAIL_HOST = env("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(env("EMAIL_PORT", "587") or "587")
EMAIL_USER = env("EMAIL_USER")
EMAIL_PASS = env("EMAIL_PASS")
EMAIL_TO = env("EMAIL_TO")  # לאן לשלוח

# OpenAI
OPENAI_API_KEY = env("OPENAI_API_KEY")

# Optional news key (אם יש לך ספק חדשות)
NEWSAPI_KEY = env("NEWSAPI_KEY")
