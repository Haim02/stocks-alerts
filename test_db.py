import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

print("DATABASE_URL:", os.getenv("DATABASE_URL"))

conn = psycopg2.connect(
    host="127.0.0.1",
    port=int(os.getenv("DB_PORT", "5432")),  # נשתמש בזה אם תעביר פורט
    user="postgres",
    password="postgres",
    dbname="stocks_alerts",
)

cur = conn.cursor()
cur.execute("select 1;")
print("select 1 =>", cur.fetchone())

cur.close()
conn.close()
print("OK")
