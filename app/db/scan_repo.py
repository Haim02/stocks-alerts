from app.db.database import get_conn

def was_sent(ticker: str) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM scan_results WHERE ticker=%s", (ticker,))
            return cur.fetchone() is not None

def mark_sent(ticker: str, score: float):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO scan_results (ticker, score)
                VALUES (%s, %s)
                ON CONFLICT (ticker) DO NOTHING
                """,
                (ticker, score),
            )
