import paramiko
import json

class Connection:
    client  : paramiko.SSHClient = None
    channel : paramiko.Channel   = None
    # When reading json objects if there are
    # any leftover bytes from reading a previous
    # json object it is stored in json_lo.
    json_lo = ""

    def create_connection(self, hostname):
        """Establishes a SSH connection with the given hostname.
        """
        
        self.json_lo = ""
        self.client = paramiko.SSHClient()

        self.client.load_system_host_keys()    
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        self.client.connect(hostname, port=22, banner_timeout=200)

        # SSH has multiple layers so got to also open the channel for it to work.
        self.channel = self.client.get_transport().open_channel("session")
       
    def read_json_object(self):
        """Reads a single json object from the network and returns
           it to the caller.
        """
        json_obj = self.json_lo
        while self.is_open():
            packet = self.channel.recv(512).decode("utf-8")
            if "\n" in packet:
                # end of json delim
                parts = packet.split("\n")
                rest         = parts[0]
                self.json_lo = parts[1]
                return json.loads(json_obj + rest)
        # Return None since the connection was closed.
        return None

    def send_json_object(self, obj):
        """Takes a json object (python dictionary) and sends it to the server.
        """
        packet = bytes(json.dumps(obj) + "\n", encoding="utf-8")
        self.channel.sendall(packet)

    def is_open(self):
        return self.client.get_transport() != None and self.client.get_transport().is_active()

    def close(self):
        if self.channel == None:
            return

        self.channel.close()
        self.client.close()
