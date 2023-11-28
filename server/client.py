from connection import ClientConnection

class Client:
    def __init__(self, connection: ClientConnection, db_id, addr, username):
        self.connection = connection
        self.db_id = db_id
        self.addr = addr
        self.username = username
        # When a user request chat logs the chat logs are dispersed between multiple
        # json objects so this id counter assigns an id to a set of logs/objects.
        self.chat_logs_instance_id_counter = 1
    
    def send_json_object(self, obj):
        self.connection.send_json_object(obj)