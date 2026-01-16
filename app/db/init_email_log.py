from dotenv import load_dotenv
load_dotenv()

from app.db.db import Base, engine

# from app.db.email_send_log import EmailSendLog  # חשוב

def init_email_log():
    Base.metadata.create_all(bind=engine)
    print("email_send_log initialized ✅")

if __name__ == "__main__":
    init_email_log()