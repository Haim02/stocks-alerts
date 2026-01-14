from app.db.database import get_conn

DDL = """
CREATE TABLE IF NOT EXISTS scan_results (
  id SERIAL PRIMARY KEY,
  ticker TEXT NOT NULL UNIQUE,
  score DOUBLE PRECISION NOT NULL,
  sent_at TIMESTAMP DEFAULT NOW()
);
"""

def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)

if __name__ == "__main__":
    init_db()
    print("DB initialized ✅")
