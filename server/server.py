import paramiko
import socket
import sys, os
from threading import Thread
import connection
import database
import sqlite3
import socket

WORKING_DIR   = os.getcwd()
HOST_KEY_PATH = WORKING_DIR + os.sep + "ssh-server.key"

MAX_MESSAGE_LENGTH = 1500

class Client:
    def __init__(self, addr, username):
        self.addr = addr
        self.username = username

# Map of client connections to Client objects.
connected_clients = {}

# Creating the ssh host key if it does not exist.
if os.path.isfile(HOST_KEY_PATH):
    print("[*] Found existing host ssh key.")
    HOST_KEY = paramiko.RSAKey(filename=HOST_KEY_PATH)
else:
    print("[*] Did not find existing host ssh key. Generating it.")
    # Host ssh key does not exist so let's create it.
    HOST_KEY = paramiko.RSAKey.generate(bits=2048)
    HOST_KEY.write_private_key_file(HOST_KEY_PATH)

# Creates the database and tables if they do not exist.
database.setup_database()

def handle_client_packets(client_connection: connection.ClientConnection):
    client = connected_clients[client_connection]
    
    while client_connection.is_open():
        try:
            client_msg = client_connection.read_json_object()
            
            if client_msg == None:
                # Means the connection was closed.
                break

            if not "act" in client_msg:
                print("[=] Client sent invalid json not containing an act.")
                break
            match client_msg["act"]:
                case "message":
                    if not "body" in client_msg:
                        break
                    
                    msg = client_msg["body"]
                    if len(msg) > MAX_MESSAGE_LENGTH:
                        # Client sending messages that are too large!
                        break

                    msg_to_send = {
                        "act": "message",
                        "user": client.username,
                        "body": msg
                    }
                    # Sending the message to all the clients.
                    for other_conn in connected_clients:
                        other_conn.send_json_object(msg_to_send)
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
    client_connection.close()

def handle_connection(tcp_conn, addr):
    
    print("[*] Recieved client connection with address: {:s}.".format(addr[0]))
    
    try:
        client_connection = connection.ClientConnection()
        client_connection.create_connection(tcp_conn, HOST_KEY)
        if not client_connection.is_open():
            print("[=] Failed to open the SSH channel for client.")
    except Exception:
        print("[=] Client failed to authenticate via SSH.")
        client_connection.close()
        return

    print("[*] Client successfully authenticated with SSH.")

    login_info = client_connection.read_json_object()
    if not "username" in login_info or not "password" in login_info:
        # User supplied bad login information.
        return
    
    username = login_info["username"]
    password = login_info["password"]


    try:
        db_conn = sqlite3.connect(database.DATABSE_NAME)
        if database.has_user_by(db_conn, username, password):
            client_connection.send_json_object({ "status": "success" })
        else:
            client_connection.send_json_object({ "status": "wrong_creds" })
            client_connection.close()
    except (socket.timeout, socket.error):
        client_connection.close()
    finally:
        db_conn.close()

    # TODO: here we may update the last login information of the database

    connected_clients[client_connection] = Client(addr, username)

    handle_client_packets(client_connection)
    


print("[*] Opening the server socket for connections...")
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", 22))
    sock.settimeout(10.0)
except Exception as e:
    print("[!] Could not open server socket: {:s}".format(str(e)))
    sys.exit(1)
print("[*] Successfully opened the server socket.")



def handle_shutdown():
    print("\n\nClosing server down!\n")
    sock.close()
    # Close all open connections so the user threads shutdown properly.
    for client_connection in connected_clients:
        client_connection.close()
    sys.exit(1)

# Code for recieving connections to the server from clients.
try:
    while True:
        try:
            sock.listen(100)
            conn, addr = sock.accept()
            connect_thread = Thread(target=handle_connection, args=(conn, addr))
            connect_thread.start()
        except TimeoutError:
            pass
        except KeyboardInterrupt:
            handle_shutdown()
        except Exception as e:
            print("[=] An exception occured while trying to accept clients: {:s}".format(str(e)))
except KeyboardInterrupt:
   handle_shutdown()

