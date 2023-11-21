import sqlite3
from datetime import date
import bcrypt

MAX_USERNAME_LENGTH = 16
MAX_PASSWORD_LENGTH = 30

DATABSE_NAME = "server.db"

def setup_database():
    db_conn = sqlite3.connect(DATABSE_NAME)
    db_cur = db_conn.cursor()
    db_cur.execute(f"""CREATE TABLE IF NOT EXISTS user(
        id INTEGER PRIMARY KEY,
        username CHAR({MAX_USERNAME_LENGTH}) UNIQUE NOT NULL,
        password CHAR({MAX_PASSWORD_LENGTH}) NOT NULL,
        first_joined TEXT NOT NULL,
        last_login TEXT NOT NULL
    )""")

def add_new_user(db_conn, username, password):
    db_cur = db_conn.cursor()
    today = date.today()
    the_date = today.strftime("%d-%m-%Y")
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    db_cur.execute("INSERT INTO user VALUES(?, ?, ?, ?, ?)", (None, username, hashed_password, the_date, the_date))
    db_conn.commit()

def has_user_by(db_conn, username, password):
    db_cur = db_conn.cursor()
    res = db_cur.execute("SELECT password FROM user WHERE username=?", (username, ))
    hashed_password = res.fetchone()
    if hashed_password == None:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password[0])

def delete_user(db_conn, username):
    db_cur = db_conn.cursor()
    db_cur.execute("DELETE FROM user WHERE username=?", (username, ))
    db_conn.commit()

def print_user(db_conn, username):
    db_cur = db_conn.cursor()
    res = db_cur.execute("SELECT * FROM user WHERE username=?", (username, ))
    print(res.fetchone())