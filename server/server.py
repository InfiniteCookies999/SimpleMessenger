import paramiko
import socket
import sys, os
from threading import Thread
import connection
import database
import sqlite3

WORKING_DIR   = os.getcwd()
HOST_KEY_PATH = WORKING_DIR + os.sep + "ssh-server.key"

if os.path.isfile(HOST_KEY_PATH):
    print("[*] Found existing host ssh key.")
    HOST_KEY = paramiko.RSAKey(filename=HOST_KEY_PATH)
else:
    print("[*] Did not find existing host ssh key. Generating it.")
    # Host ssh key does not exist so let's create it.
    HOST_KEY = paramiko.RSAKey.generate(bits=2048)
    HOST_KEY.write_private_key_file(HOST_KEY_PATH)

database.setup_database()

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

    db_conn = sqlite3.connect(database.DATABSE_NAME)
    if database.has_user_by(db_conn, username, password):
        client_connection.send_json_object({ "status": "success" })
    else:
        client_connection.send_json_object({ "status": "wrong_creds" })
    db_conn.close()

    client_connection.close()


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

# TODO: There is an issue in which KeyboardInterrupt is not raised
#       and caught if accept() is allowed to continue running. Placing
#       a timeout on the socket will just lead to both exceptions occuring
#       once the timeout occures.
while True:
    try:
        sock.listen(100)
        conn, addr = sock.accept()
        connect_thread = Thread(target=handle_connection, args=(conn, addr))
        connect_thread.start()
    except TimeoutError:
        pass
    except KeyboardInterrupt:
        print("\n\nClosing server down!\n")
        sock.close()
        sys.exit(1)
    except Exception as e:
        print("[=] An exception occured while trying to accept clients: {:s}".format(str(e)))
