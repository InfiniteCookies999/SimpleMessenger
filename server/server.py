import paramiko
import socket
import sys, os
from threading import Thread
import threading

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

print(f"host key fingerprint: {HOST_KEY.get_fingerprint()}")

class SSHInterface(paramiko.ServerInterface):
    def __init__(self):
        self.event = threading.Event()
    
    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def get_allowed_auths(self, username):
        return "publickey"

    def check_auth_publickey(self, username, key):
        return paramiko.AUTH_SUCCESSFUL

def handle_connection(conn, addr):
    
    print("[*] Recieved client connection with address: {:s}".format(addr[0]))
    
    ssh_session = paramiko.Transport(conn)
    ssh_session.add_server_key(HOST_KEY)
    
    try:
        ssh_session.start_server(server=SSHInterface())
        channel = ssh_session.accept(20)
        if channel == None:
            print("[=] ssh session channel was None.")
            ssh_session.close()
            return
    except Exception:
        print("[=] client failed to authenticate via SSH.")
        ssh_session.close()
        return
    
    print("[*] Client successfully authenticated with SSH.")

    # let us send a message!
    channel.send("Sending potentially encrypted data to client")

    ssh_session.close()


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
