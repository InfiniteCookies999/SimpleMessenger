import sqlite3
from datetime import date
import bcrypt

MAX_USERNAME_LENGTH = 16
MAX_PASSWORD_LENGTH = 30

DATABSE_NAME = "server.db"

class DatabaseConnection:

    def __init__(self):
        self.db_conn = sqlite3.connect(DATABSE_NAME)

    def __del__(self):
        self.db_conn.close()

    def setup(self):
        """Sets up the database by creating the sqlite database
           .db file if it does not exists and creates the appropriate
           tables for the database.
        """

        db_cur = self.db_conn.cursor()

        db_cur.execute(f"""CREATE TABLE IF NOT EXISTS user(
            id INTEGER PRIMARY KEY,
            username CHAR({MAX_USERNAME_LENGTH}) UNIQUE NOT NULL,
            password CHAR({MAX_PASSWORD_LENGTH}) NOT NULL,
            first_joined TEXT NOT NULL,
            last_login TEXT NOT NULL
        )""")

        db_cur.execute("""CREATE TABLE IF NOT EXISTS friends(
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            friend_id INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES user(id),
            FOREIGN KEY(friend_id) REFERENCES user(id)
        )""")

    def add_new_user(self, username, password):
        """Creates a new user for the given username and password
            and inserts it into the database.
        """
        db_cur = self.db_conn.cursor()
        today = date.today()
        the_date = today.strftime("%d-%m-%Y")
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        db_cur.execute("INSERT INTO user VALUES(?, ?, ?, ?, ?)",
                       (None, username, hashed_password, the_date, the_date))
        self.db_conn.commit()

    def has_user_by(self, username, password):
        """Returns true if there exists a user by the given username/password
           within the database.
        """
        db_cur = self.db_conn.cursor()
        res = db_cur.execute("SELECT password FROM user WHERE username=?", (username, ))
        hashed_password = res.fetchone()
        if hashed_password == None:
            return False
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password[0])
    
    def get_user_id(self, username):
        """Retrieves the primary database key of the user table
           for the given username if it exists, otherwise returns
           None.
        """
        db_cur = self.db_conn.cursor()
        res = db_cur.execute("SELECT id FROM user WHERE username=?", (username, )).fetchone()
        return res[0] if res != None else None

    def delete_user(self, username):
        """Removes the user by the given username from the database.
        """
        db_cur = self.db_conn.cursor()
        db_cur.execute("DELETE FROM user WHERE username=?", (username, ))
        self.db_conn.commit()

    def add_friend(self, user_id, friend_id):
        """Adds a friend by friend_id to the user by user_id to the
           database.
        """
        db_cur = self.db_conn.cursor()
        db_cur.execute("INSERT INTO friends VALUES(?, ?, ?)", (None, user_id, friend_id))
        self.db_conn.commit()

    def get_friends(self, user_id):
        """Retrieves all friends of a given user_id. However, another user is only
           considered a friend if both users have each other added as friends, so
           this function returns a list of only those who have each other as friends
           for a given user.
        """
        # Way to convert the list directly to a non-tupled list from the queried result.
        self.db_conn.row_factory = lambda c, row: row[0]
        db_cur = self.db_conn.cursor()
        res = db_cur.execute("""SELECT t.username FROM (SELECT user.* FROM friends
                                LEFT JOIN user ON user.id = friends.friend_id
                                WHERE friends.user_id = ?) t

                                WHERE EXISTS(SELECT 1 FROM friends WHERE friends.user_id = t.id)
        """, (user_id, ))
        return res.fetchall()
    
    def are_users_friends(self, user_id, friend_id):
        """Returns true if both the user of user_id and the friend of friend_id
           both have each other added as friends.
        """
        db_cur = self.db_conn.cursor()
        res = db_cur.execute("""SELECT (
                                EXISTS(
                                    SELECT 1 FROM friends WHERE friends.user_id = ? AND friends.friend_id = ?
                                ) AND
                                EXISTS(
                                    SELECT 1 FROM friends WHERE friends.user_id = ? AND friends.friend_id = ?
                                ))
                       """, (user_id, friend_id, friend_id, user_id))
        return res.fetchone()[0] == 1
        