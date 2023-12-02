import sqlite3
from datetime import date
import bcrypt

MAX_USERNAME_LENGTH = 16
MAX_PASSWORD_LENGTH = 30

MAX_LOG_REQUEST = 30

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

        # Maps a pair of users to a chat_log.id. This id can be used to find
        # all the logs between the two users.
        db_cur.execute("""CREATE TABLE IF NOT EXISTS chat_log(
            id INTEGER PRIMARY KEY,
            user1_id INTEGER NOT NULL,
            user2_id INTEGER NOT NULL,
            FOREIGN KEY(user1_id) REFERENCES user(id),
            FOREIGN KEY(user2_id) REFERENCES user(id)
        )""")

        db_cur.execute("""CREATE TABLE IF NOT EXISTS chat_log_msg(
            id INTEGER PRIMARY KEY,
            chat_log_id INTEGER NOT NULL,
            from_user_id INTEGER NOT NULL,
            chat_message TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY(from_user_id) REFERENCES user(id),
            FOREIGN KEY(chat_log_id) REFERENCES chat_log(id)
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
    
    def get_user_username(self, user_id):
        db_cur = self.db_conn.cursor()
        res = db_cur.execute("SELECT username FROM user WHERE id = ?", (user_id, )).fetchone()
        return res[0]

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
                                WHERE friends.user_id = :id) t

                                WHERE EXISTS(SELECT 1 FROM friends WHERE friends.user_id = t.id AND
                                             friends.friend_id = :id)
        """, { "id": user_id })
        return res.fetchall()
    
    def get_sent_friend_requests(self, user_id):
         # Way to convert the list directly to a non-tupled list from the queried result.
        self.db_conn.row_factory = lambda c, row: row[0]
        db_cur = self.db_conn.cursor()
        res = db_cur.execute("""SELECT t.username FROM (SELECT user.* FROM friends
                                LEFT JOIN user ON user.id = friends.friend_id
                                WHERE friends.user_id = :id) t

                                WHERE NOT EXISTS(SELECT 1 FROM friends WHERE friends.user_id = t.id AND
                                             friends.friend_id = :id)
                       """, { "id": user_id })
        return res.fetchall()
    
    def get_friend_requests(self, user_id):
        # Way to convert the list directly to a non-tupled list from the queried result.
        self.db_conn.row_factory = lambda c, row: row[0]
        db_cur = self.db_conn.cursor()
        res = db_cur.execute("""SELECT t.username FROM (SELECT user.* FROM friends
                                LEFT JOIN user ON user.id = friends.user_id         
                                WHERE friends.friend_id = :id) t
                             
                                WHERE NOT EXISTS(SELECT 1 FROM friends WHERE friends.user_id = :id AND
                                                 friends.friend_id = t.id)
                                """, { "id": user_id })
        return res.fetchall()
    
    def are_users_friends(self, user_id, friend_id):
        """Returns true if both the user of user_id and the friend by friend_id
           both have each other added as friends.
        """
        db_cur = self.db_conn.cursor()
        res = db_cur.execute("""SELECT (
                                EXISTS(
                                    SELECT 1 FROM friends WHERE friends.user_id = :id1 AND friends.friend_id = :id2
                                ) AND
                                EXISTS(
                                    SELECT 1 FROM friends WHERE friends.user_id = :id2 AND friends.friend_id = :id1
                                ))
                       """, { "id1": user_id, "id2": friend_id})
        return res.fetchone()[0] == 1
    
    def has_user_as_friend(self, user_id, friend_id):
        """Returns true if the user by user_id has the user by friend_id added as a friend.

           Unlike the function ``are_users_friends`` only the user by user_id has to have
           the friend by friend_id to be added as a friend and not vice versa.
        """
        db_cur = self.db_conn.cursor()
        res = db_cur.execute("SELECT EXISTS(SELECT 1 FROM friends WHERE friends.user_id = ? AND friends.friend_id = ?)",
                       (user_id, friend_id))
        return res.fetchone()[0] == 1

    def _get_chat_log_id(self, user1_id, user2_id):
        db_cur = self.db_conn.cursor()
        res = db_cur.execute("""SELECT id FROM chat_log
                                WHERE (user1_id = :id1 AND user2_id = :id2) OR
                                      (user1_id = :id2 AND user2_id = :id1)
                       """, { "id1": user1_id, "id2": user2_id }).fetchone()
        return res[0] if res != None else None 

    def add_chat_log_msg(self, from_user_id, to_user_id, chat_msg, timestamp):
        db_cur = self.db_conn.cursor()

        chat_log_id = self._get_chat_log_id(from_user_id, to_user_id)
        if chat_log_id == None:
            # There exist no chat logs between the two users so need to create
            # a chat log id for their logs.
            db_cur.execute("INSERT INTO chat_log VALUES(?, ?, ?)",
                        (None, from_user_id, to_user_id))
            self.db_conn.commit()
            chat_log_id = self._get_chat_log_id(from_user_id, to_user_id)
        
        db_cur.execute("INSERT INTO chat_log_msg VALUES(?, ?, ?, ?, ?)",
                       (None, chat_log_id, from_user_id, chat_msg, timestamp))
        self.db_conn.commit()

    def get_chat_logs(self, user1_id, user2_id, offset):
        """Returns a list of tuples that describe chat messages between
           users for user1_id and user2_id.

           Tuples in form: (from_user_id, chat_message, timestamp)
        """
        db_cur = self.db_conn.cursor()
        chat_log_id = self._get_chat_log_id(user1_id, user2_id)
        if chat_log_id == None:
            # There exists no chat logs between those users.
            return []
        res = db_cur.execute(f"""SELECT from_user_id, chat_message, timestamp FROM chat_log_msg
                                WHERE chat_log_id = ?
                                ORDER BY id DESC
                                LIMIT {MAX_LOG_REQUEST} OFFSET {offset}
                    """, (chat_log_id, ))
        logs = res.fetchall()
        logs.reverse()
        return logs