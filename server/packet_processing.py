from connection import ClientConnection
from database import DatabaseConnection, MAX_LOG_REQUEST
import socket
from datetime import date

# Map of client connections to Client objects.
connected_clients = {}
usernames_to_connections = {}

MAX_MESSAGE_LENGTH = 1500

def net_obj_has(net_obj, name, ty):
    return name in net_obj and isinstance(net_obj[name], ty)

def on_message_packet(client, net_obj):
    print("on_message_packet")
    if not net_obj_has(net_obj, "body", str):
        return
    if not net_obj_has(net_obj, "user", str):
        return
    
    msg = net_obj["body"]
    if len(msg) > MAX_MESSAGE_LENGTH:
        # Client sending messages that are too large!
        return
    if msg == "":
        # Clients cannot send blank messages.
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
    
    today = date.today()
    timestamp = today.strftime("%d-%m-%Y %M:%S")
    db_conn.add_chat_log_msg(client.db_id, user_to_sendto_id, msg, timestamp)

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
    obj_to_send = {
        "act": "friends_list",
        "body": db_conn.get_friends(client.db_id)
    }
    client.send_json_object(obj_to_send)


def on_req_sent_friend_requests_packet(client):
    db_conn = DatabaseConnection()
    obj_to_send = {
        "act": "sent_friends_requests",
        "body": db_conn.get_sent_friend_requests(client.db_id)
    }
    client.send_json_object(obj_to_send)
    
def on_req_friend_requests_packet(client):
    db_conn = DatabaseConnection()
    obj_to_send = {
        "act": "friend_requests",
        "body": db_conn.get_friend_requests(client.db_id)
    }
    client.send_json_object(obj_to_send)

def on_req_chat_logs_packet(client, net_obj):
    if not net_obj_has(net_obj, "user", str):
        return
    if not net_obj_has(net_obj, "block", int):
        return

    req_user = net_obj["user"]
    block    = net_obj["block"]
    
    db_conn = DatabaseConnection()
    user_id = db_conn.get_user_id(req_user)
    if user_id == None:
        # User requested chat logs from a user that does not exist.
        return

    chat_logs = db_conn.get_chat_logs(client.db_id, user_id, block * MAX_LOG_REQUEST)
    
    client.send_json_object({
        "act": "chat_log_start",
        "instance_id": client.chat_logs_instance_id_counter
        })

    for chat_log in chat_logs:
        # TODO: Will also want to send the timestamp.
        from_username = db_conn.get_user_username(chat_log[0])
        client.send_json_object({
            "act": "chat_log",
            "from_user": from_username,
            "msg": chat_log[1],
            "instance_id": client.chat_logs_instance_id_counter
        })

    client.chat_logs_instance_id_counter += 1

def on_add_friend_packet(client, net_obj):
    if not net_obj_has(net_obj, "user", str):
        return
    
    friend = net_obj["user"]
    db_conn = DatabaseConnection()
    friend_id = db_conn.get_user_id(friend)

    obj_to_send = {
        "act": "add_friend",
        "user": friend
    }

    if friend_id == None:
        obj_to_send["status"] = "no_such_user"
        client.send_json_object(obj_to_send)
        return
    
    if db_conn.are_users_friends(client.db_id, friend_id):
        obj_to_send["status"] = "already_friends"
        client.send_json_object(obj_to_send)
        return

    if db_conn.has_user_as_friend(client.db_id, friend_id):
        obj_to_send["status"] = "already_sent"
        client.send_json_object(obj_to_send)
        return

    db_conn.add_friend(client.db_id, friend_id)

    if friend in usernames_to_connections:
        friend_connection = connected_clients[usernames_to_connections[friend]]
        friend_connection.send_json_object({
            "act": "friend_req",
            "user": client.username
        })
        # TODO: Need some way to send tell the other user they have been sent a friend
        # request.
    
    if db_conn.are_users_friends(client.db_id, friend_id):
        obj_to_send["status"] = "now_friends"
    else:
        obj_to_send["status"] = "request_sent"
        
    client.send_json_object(obj_to_send)

def handle_client_packets(client_connection: ClientConnection):
    client = connected_clients[client_connection]
    
    while client_connection.is_open():
        try:
            net_obj = client_connection.read_json_object()
        except socket.timeout:
            continue
        except IOError as e:
            print("[=] IOError: {:s}.".format(str(e)))
            break
        except ValueError as e:
            print("[=] Client sent invalid json: {:s}.".format(str(e)))
            break
    
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
            case "sent_friends_requests":
                on_req_sent_friend_requests_packet(client)
            case "friend_requests":
                on_req_friend_requests_packet(client)
            case "chat_logs":
                on_req_chat_logs_packet(client, net_obj)
            case "add_friend":
                on_add_friend_packet(client, net_obj)    
            case _:
                print("[=] Client sent an unknown act.")
                break


    print("[*] Client with address {:s} has disconnected.".format(client.addr[0]))
    del connected_clients[client_connection]
    del usernames_to_connections[client.username]
    client_connection.close()