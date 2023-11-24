from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import connection
from threading import Thread 

MAX_MESSAGE_LENGTH = 1500

class MessageBoard(QWidget):

   login_form : QWidget

   def __init__(self, conn: connection.Connection):
      super().__init__()
      self.conn = conn
      self.decoded_json_objects = []

      self.setWindowTitle("Simple Messenger")
      self.setFixedSize(400, 300)

      layout = QVBoxLayout()
      self.setLayout(layout)


      self.msgs_layout = QFormLayout()
      self.msgs_content = QWidget()
      self.msgs_content.setLayout(self.msgs_layout)

      self.msg_scroll_area = QScrollArea()
      self.msg_scroll_area.setWidget(self.msgs_content)
      self.msg_scroll_area.setWidgetResizable(True)

      self.msg_field = QLineEdit()
      self.msg_field.setPlaceholderText("Send message here!")
      self.msg_field.setMaxLength(MAX_MESSAGE_LENGTH)
      self.msg_field.setFixedHeight(30)
      self.msg_field.returnPressed.connect(self.on_submit_msg)

      layout.addWidget(self.msg_scroll_area)
      layout.addWidget(self.msg_field)

      self.handle_packets_timer = QTimer()
      self.handle_packets_timer.timeout.connect(self.handle_packets)
      self.handle_packets_timer.setInterval(100)
      self.handle_packets_timer.start()


   def handle_packets(self):
      
      while len(self.decoded_json_objects) > 0:
         server_msg = self.decoded_json_objects.pop()

         act = server_msg["act"]
         match act:
               case "message":
                  username = server_msg["user"]
                  msg      = server_msg["body"]
                  msg_label = QLabel(f"{username}: {msg}")
                  msg_label.setWordWrap(True)
                  self.msgs_layout.addRow(msg_label)
               case _:
                  print(f"Unknown act from server: {act}")
         

   def run_packet_recv_thread(self):
      Thread(target=self.recv_packets).start()

   def recv_packets(self):
      """
      recv_packets continues to read json objects from the server as
                  long as the connection is open.
      """
      while self.conn.is_open():
         server_msg = self.conn.read_json_object()
         
         if server_msg == None:
               # Means connection was closed.
               break

         self.decoded_json_objects.append(server_msg)

      print("Connection to server was closed.")

   def on_submit_msg(self):
      message_to_send = self.msg_field.text()
      if message_to_send == "":
         return
      
      if len(message_to_send) > MAX_MESSAGE_LENGTH:
         # The field should not even allow this but adding the check
         # just in case.
         return

      self.msg_field.clear()
      self.conn.send_json_object({ "act": "message", "body": message_to_send })