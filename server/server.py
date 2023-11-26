import paramiko
import socket
import sys, os
from threading import Thread
import connection
from database import DatabaseConnection 
import socket
import packet_processing
from client import Client 

WORKING_DIR   = os.getcwd()
HOST_KEY_PATH = WORKING_DIR + os.sep + "ssh-server.key"

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
db_conn = DatabaseConnection()
db_conn.setup()
del db_conn

def handle_connection(tcp_conn, addr):
    """Handles incoming TCP connections and tries to establish
       an SSH  channel for communication with the client.
       
       If established the function then reads a username/password
       from the network and tries to login that user.
    """
    
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


    db_conn = DatabaseConnection()
    try:
        if db_conn.has_user_by(username, password):
            client_connection.send_json_object({ "status": "success" })
        else:
            client_connection.send_json_object({ "status": "wrong_creds" })
            client_connection.close()
    except (socket.timeout, socket.error):
        client_connection.close()
        return

    # TODO: here we may update the last login information of the database

    client = Client(client_connection, db_conn.get_user_id(username), addr, username)
    packet_processing.connected_clients[client_connection] = client
    packet_processing.usernames_to_connections[username] = client_connection
    packet_processing.handle_client_packets(client_connection)


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
    for client_connection in packet_processing.connected_clients:
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

