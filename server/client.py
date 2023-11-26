from connection import ClientConnection

class Client:
    def __init__(self, connection: ClientConnection, db_id, addr, username):
        self.connection = connection
        self.db_id = db_id
        self.addr = addr
        self.username = username
    
    def send_json_object(self, obj):
        self.connection.send_json_object(obj)