import paramiko
import json
import threading

MAX_JSON_OBJECT_SIZE = 4096

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

class ClientConnection:
    ssh_session : paramiko.Transport
    channel     : paramiko.Channel
    # When reading json objects if there are
    # any leftover bytes from reading a previous
    # json object it is stored in json_lo.
    json_lo = ""
    # While reading json objects from the network a packet
    # might have extra json objects shoved between pairs of
    # new line characters. This queue is used to store those
    # objects when the user request a single json object.
    queued_json_objs = []

    def create_connection(self, tcp_conn, host_key):
        """Takes an already open TCP connection and turns it into a SSH session
           to securely send messages back and forth. 
        """
        self.ssh_session = paramiko.Transport(tcp_conn)
        self.ssh_session.add_server_key(host_key)
        self.ssh_session.start_server(server=SSHInterface())
        self.channel = self.ssh_session.accept(20)
        
    def read_json_object(self):
        """Reads a single json object from the network and
           returns it to the caller.

           :raises ValueError:
              if the client sent a json object larger than
              ``MAX_JSON_OBJECT_SIZE``.
        """

        if len(self.queued_json_objs) > 0:
            return self.queued_json_objs.pop(0)

        json_obj = self.json_lo
        while self.is_open():
            packet = self.channel.recv(512).decode("utf-8")
            
            if "\n" in packet:
                # end of json delim
                parts = packet.split("\n")
                json_obj += parts[0]
                if len(json_obj) > MAX_JSON_OBJECT_SIZE:
                    raise ValueError("Client sent a json object that was too large")
                
                # There might be extra json objects shoved between pairs
                # of \n characters so we place them into a backup queue
                # and return from the queue if it is not empty on subsequent
                # calls.
                for i in range(1, len(parts) - 1):
                    self.queued_json_objs.append(json.loads(parts[i]))

                self.json_lo = parts[-1]
                return json.loads(json_obj)
            else:
                json_obj += packet
        # Return None since the connection was closed.
        return None

    def send_json_object(self, obj):
        """Takes a json object (python dictionary) and sends it to the client.
        """
        packet = bytes(json.dumps(obj) + "\n", encoding="utf-8")
        self.channel.sendall(packet)

    def is_open(self):
        return self.channel != None and self.ssh_session.is_active()

    def close(self):
        self.ssh_session.close()
        self.channel.close()
