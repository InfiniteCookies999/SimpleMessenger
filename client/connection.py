import paramiko
import json

class Connection:
    client  : paramiko.SSHClient
    channel : paramiko.Channel
    # When reading json objects if there are
    # any leftover bytes from reading a previous
    # json object it is stored in json_lo.
    json_lo = ""

    def create_connection(self, hostname):
        """
        create_connection establishes a SSH connection with the given
                          hostname.
        """
        self.client = paramiko.SSHClient()

        self.client.load_system_host_keys()    
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        self.client.connect(hostname, port=22)

        # SSH has multiple layers so got to also open the channel for it to work.
        self.channel = self.client.get_transport().open_channel("session")
       
    def read_json_object(self):
        """
        read_json_object reads a single json object from the
                         network and returns it to the caller.
        """
        json_obj = self.json_lo
        while True:
            packet = self.channel.recv(512).decode("utf-8")
            if "\n" in packet:
                # end of json delim
                parts = packet.split("\n")
                rest         = parts[0]
                self.json_lo = packet[1]
                return json.loads(json_obj + rest)

    def send_json_object(self, obj):
        """
        send_json_object takes a json object (python dictionary) and
                         sends it to the server.
        """
        packet = bytes(json.dumps(obj) + "\n", encoding="utf-8")
        self.channel.sendall(packet)

    def close(self):
        self.channel.close()
        self.client.close()

connection = Connection()
