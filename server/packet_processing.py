from connection import ClientConnection
from database import DatabaseConnection
import socket

# Map of client connections to Client objects.
connected_clients = {}
usernames_to_connections = {}

MAX_MESSAGE_LENGTH = 1500

def on_message_packet(client, net_obj):
    if not "body" in net_obj:
        return
    if not "user" in net_obj:
        return
    
    msg = net_obj["body"]
    if len(msg) > MAX_MESSAGE_LENGTH:
        # Client sending messages that are too large!
        return

    db_conn = DatabaseConnection()

    user_to_sendto_username = net_obj["user"]
    user_to_sendto_id = db_conn.get_user_id(user_to_sendto_username)
    if user_to_sendto_id == None:
        # Tried to send to a user that does not even exist.
        return
    
    if not db_conn.are_users_friends(client.db_id, user_to_sendto_id):
        # Cannot send to that user. They are not friends with each other!
        return

    obj_to_send = {
        "act": "message",
        "from_user": client.username,
        "to_user": user_to_sendto_username,
        "body": msg
    }

    if user_to_sendto_username in usernames_to_connections:
        # The user they are sending a message to is online so sending
        # the message to that user!
        send_to_client = connected_clients[usernames_to_connections[user_to_sendto_username]]
        send_to_client.send_json_object(obj_to_send)

    client.send_json_object(obj_to_send)
    

def on_friends_list_packet(client):
    db_conn = DatabaseConnection()
    obj_to_sent = {
        "act": "friends_list",
        "body": db_conn.get_friends(client.db_id)
    }
    client.send_json_object(obj_to_sent)


def handle_client_packets(client_connection: ClientConnection):
    client = connected_clients[client_connection]
    
    while client_connection.is_open():
        try:
            net_obj = client_connection.read_json_object()
            
            if net_obj == None:
                # Means the connection was closed.
                break

            if not "act" in net_obj:
                print("[=] Client sent invalid json not containing an act.")
                break
            match net_obj["act"]:
                case "message":
                    on_message_packet(client, net_obj)
                case "friends_list":
                    on_friends_list_packet(client)
                case _:
                    print("[=] Client sent an unknown act.")
                    break

        except socket.timeout:
            pass
        except IOError as e:
            print("[=] IOError: {:s}.".format(str(e)))
            break
        except ValueError as e:
            print("[=] Client sent invalid json: {:s}.".format(str(e)))
            break
    
    print("[*] Client with address {:s} has disconnected.".format(client.addr[0]))
    del connected_clients[client_connection]
    del usernames_to_connections[client.username]
    client_connection.close()