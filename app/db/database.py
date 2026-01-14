from dotenv import load_dotenv
import os
import psycopg2

load_dotenv()

print(f"DEBUG: DB= {os.environ.get('DATABASE_URL')}")

DATABASE_URL = os.environ["DATABASE_URL"]

def get_conn():
    return psycopg2.connect(DATABASE_URL)
