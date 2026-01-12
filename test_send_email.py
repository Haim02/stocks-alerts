from dotenv import load_dotenv
load_dotenv()

from app.main import build_email, send_email

subject, html = build_email("AAPL", "1D", "REBOUND_TEST", 190.12)
send_email(subject, html)

print("Sent OK")
