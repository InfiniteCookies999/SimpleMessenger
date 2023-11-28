import typing
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QWidget
import connection
from threading import Thread 

MAX_MESSAGE_LENGTH = 1500

class FriendLabel(QLabel):
   def __init__(self, friend, message_board):
      super().__init__(friend)
      self.friend = friend
      self.message_board = message_board

   def mousePressEvent(self, event):
      if event.button() == Qt.LeftButton:
         self.message_board.switch_to_chatting_with(self.friend)

      return super().mousePressEvent(event)

class MessageBoard(QWidget):

   login_form : QWidget

   def __init__(self, conn: connection.Connection):
      super().__init__()
      self.conn = conn
      self.decoded_json_objects = []
      self.friends = []
      self.cur_friend_msging = None
      self.username = ""
      self.chat_log_instance_id = 0
      
      self.setWindowTitle("Simple Messenger")
      self.resize(600, 540)
      
      self.main_layout = QHBoxLayout()
      self.setLayout(self.main_layout)

      self.init_friend_group()
      self.init_message_group()

      self.handle_packets_timer = QTimer()
      self.handle_packets_timer.timeout.connect(self.handle_packets)
      self.handle_packets_timer.setInterval(100)
      self.handle_packets_timer.start()

   def init_friend_group(self):
      friend_group = QWidget()
      friend_group.setFixedWidth(140)
      friend_layout = QVBoxLayout()
      friend_group.setLayout(friend_layout)
      self.main_layout.addWidget(friend_group)

      friend_info_bar = QWidget()
      friend_info_bar.setFixedHeight(40)
      friend_info_bar_layout = QFormLayout()
      friend_info_bar.setLayout(friend_info_bar_layout)
      friend_layout.addWidget(friend_info_bar)
      friend_info_label = QLabel("Friends List")
      friend_info_label.setFont(QFont("Helvetica", 16))
      friend_info_bar_layout.addRow(friend_info_label)

      friends_scroll_area = QScrollArea()
      friends_scroll_area.setWidgetResizable(True)
      friends_scroll_content = QWidget()
      friends_scroll_area.setWidget(friends_scroll_content)
      self.friends_scroll_layout = QFormLayout()
      self.friends_scroll_layout.setContentsMargins(0, 0, 0, 0)
      self.friends_scroll_layout.setSpacing(0)
      friends_scroll_content.setLayout(self.friends_scroll_layout)
      friend_layout.addWidget(friends_scroll_area)

   def init_message_group(self):
      message_group = QWidget()
      message_layout = QVBoxLayout()
      message_group.setLayout(message_layout)
      self.main_layout.addWidget(message_group)

      self.msgs_layout = QVBoxLayout()
      
      self.msgs_content = QWidget()
      self.msgs_content.setFixedHeight(0)
      self.msgs_content.setLayout(self.msgs_layout)

      self.msg_scroll_area = QScrollArea()
      self.msg_scroll_area.verticalScrollBar().rangeChanged.connect(self.msg_scrollbar_update)
      self.msg_scroll_area.setWidget(self.msgs_content)
      self.msg_scroll_area.setAlignment(Qt.AlignBottom)
      self.msg_scroll_area.setWidgetResizable(True)

      self.msg_field = QLineEdit()
      self.msg_field.setPlaceholderText("Send message here!")
      self.msg_field.setMaxLength(MAX_MESSAGE_LENGTH)
      self.msg_field.setFixedHeight(30)
      self.msg_field.returnPressed.connect(self.on_submit_msg)
      self.msg_field.setDisabled(True) # Disabled until we have the friend's list.

      message_layout.addWidget(self.msg_scroll_area)
      message_layout.addWidget(self.msg_field)

   def handle_packets(self):
      
      while len(self.decoded_json_objects) > 0:
         # pop(0) so that it pops from the front of the list allowing the
         # list to behave as a queue.
         server_obj = self.decoded_json_objects.pop(0)

         act = server_obj["act"]
         match act:
               case "message":
                  from_user = server_obj["from_user"]
                  to_user   = server_obj["to_user"]
                  msg       = server_obj["body"]

                  if from_user == self.username and to_user == self.cur_friend_msging:
                     # The message was from us to the user we are currently chatting with.
                     self.add_message_to_chat(from_user, msg)
                  elif from_user == self.cur_friend_msging:
                     self.add_message_to_chat(from_user, msg)
                  # TODO: Otherwise the user needs to be pinged in some way to tell them
                  #       they have unread messages! 

               case "friends_list":
                  self.friends = server_obj["body"]
               
                  for friend in self.friends:
                     friend_label = FriendLabel(friend, self)
                     friend_label.setFont(QFont("Helvetica", 12))
                     if friend == self.cur_friend_msging:
                        friend_label.setStyleSheet("background-color : gray")
                     friend_label.setFixedHeight(30)
                     self.friends_scroll_layout.addRow(friend_label)
                  
                  if len(self.friends) > 0:
                     self.switch_to_chatting_with(self.friends[0])
                     self.msg_field.setDisabled(False)
               case "chat_log_start":
                  # Since the chat logs are dispersed between multiple packets
                  # a instance id is used to make sure the incoming chat logs
                  # are part of the last requested set of logs.
                  self.chat_log_instance_id = server_obj["instance_id"]
               case "chat_log":
                  from_user   = server_obj["from_user"]
                  msg         = server_obj["msg"]
                  instance_id = server_obj["instance_id"]

                  if instance_id == self.chat_log_instance_id:
                     self.add_message_to_chat(from_user, msg)

               case _:
                  print(f"Unknown act from server: {act}")

   def add_message_to_chat(self, from_user, msg):
      msg_label = QLabel(f"{from_user}: {msg}")
      msg_label.setWordWrap(True)
      # Calling adjustSize so that we can actually determine the size of the label given
      # how many lines the text takes up from word wrapping.
      msg_label.adjustSize()
      
      self.msgs_content.setFixedHeight(self.msgs_content.height() + msg_label.height())
      # For some strange reason not setting alignment causes the widgets to just sorta align themselves
      # randomly causing a rather obnoxious and disorderly looking assortment of text.
      self.msgs_layout.addWidget(msg_label, alignment=Qt.AlignBottom)
      
   def msg_scrollbar_update(self):
      # TODO: when requesting logs that are not the first set of logs this will need
      # to not be set.
      vbar = self.msg_scroll_area.verticalScrollBar()
      vbar.setValue(vbar.maximum())
      

   def switch_to_chatting_with(self, friend):
      if self.cur_friend_msging == friend:
         return
      self.cur_friend_msging = friend
      self.msgs_content.setFixedHeight(0)
      self.set_friend_scroll_area_cur_friend(friend)

      self.conn.send_json_object({
         "act": "chat_logs",
         "user": friend,
         "block": 0 # TODO: Will want to select more than the first 50 logs!
      })

      for i in reversed(range(self.msgs_layout.count())):
         self.msgs_layout.itemAt(i).widget().setParent(None)      

   def set_friend_scroll_area_cur_friend(self, friend):
      for i in range(self.friends_scroll_layout.count()):
         friend_label = self.friends_scroll_layout.itemAt(i).widget()
         
         if friend == friend_label.friend:
            friend_label.setStyleSheet("background-color : gray")
         else:
            friend_label.setStyleSheet("")

   def run_packet_recv_thread(self):
      Thread(target=self.recv_packets).start()

   def recv_packets(self):
      """Continues to read json objects from the server as
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
      
      if self.cur_friend_msging == None:
         return

      if len(message_to_send) > MAX_MESSAGE_LENGTH:
         # The field should not even allow this but adding the check
         # just in case.
         return

      self.msg_field.clear()
      obj_to_send = {
         "act": "message",
         "user": self.cur_friend_msging,
         "body": message_to_send
      }
      self.conn.send_json_object(obj_to_send)