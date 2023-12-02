import typing
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import QEvent, QObject
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QWidget
import connection
from threading import Thread 
from constants import *

class FriendLabel(QLabel):
   def __init__(self, friend, message_board):
      super().__init__(friend)
      self.friend = friend
      self.message_board = message_board

   def mousePressEvent(self, event):
      if event.button() == Qt.LeftButton:
         self.message_board.switch_to_chatting_with(self.friend)

      return super().mousePressEvent(event)

#class TestWidget(QWidget):
#   def __init__(self):
#      self.msgs_to_add = []
#      super().__init__()
#
#   def resizeEvent(self, event):
#      print("resize event called")
#      return super().resizeEvent(event)
#   
#   def showEvent(self, event):
#      print("show event called?")
#      return super().showEvent(event)
#   
#   def changeEvent(self, event):
#      print("change event called?")
#      return super().changeEvent(event)
#   
#   def paintEvent(self, event):
#      print("paint event?")
#      return super().paintEvent(event)
#   
#   def updateGeometry(self):
#      print("updating geometry?")
#      return super().updateGeometry()
#
#   def eventFilter(self, obj, event) -> bool:
#      if event == QEvent.LayoutRequest:
#         print("layout request?")
#      else:
#         print(f"event: {event}")
#      return super().eventFilter(obj, event)
#
   #def resizeEvent(self, event):
   #   super().resizeEvent(event)
   #   while len(self.msgs_to_add) > 0:
   #      msg = self.msgs_to_add.pop(0)
#
   #      msg_label = QLabel(f"{msg[0]}: {msg[1]}")
   #      msg_label.setFont(QFont(FONT_NAME, 10))
   #      msg_label.setWordWrap(True)
   #      #msg_label.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
   #      msg_label.setStyleSheet("background-color : red")
   #      #msg_label.showEvent()
   #      msg_label.adjustSize()
#
   #      self.layout().addWidget(msg_label, alignment=Qt.AlignBottom)
#
   #      # Calculating the height when taking into account margins, spacing, and heights of
   #      # the widgets.
   #      margins = self.layout().getContentsMargins()
   #      content_height = margins[1] + margins[3] + self.layout().spacing() * (self.layout().count() - 1)
   #      
   #      for i in range(self.layout().count()):
   #         self.layout().itemAt(i).widget().adjustSize()
   #         content_height += self.layout().itemAt(i).widget().height()
   #      
   #      #self.msg_scroll_area.updateGeometry()
   #      #
   #      #print(f"content height: {content_height}")
   #      self.setFixedHeight(content_height)

         


# Utility function to help remove all the children of a layout.
def clear_layout(layout):
   for i in reversed(range(layout.count())):
      layout.itemAt(i).widget().setParent(None)

class MessageBoard(QWidget):

   login_form : QWidget

   def __init__(self, conn: connection.Connection):
      super().__init__()
      self.conn = conn
      self.decoded_json_objects = []
      self.cur_friend_msging = None
      self.username = ""
      self.chat_log_instance_id = 0
      
      self.setWindowTitle("Simple Messenger")
      self.resize(600, 540)

      self.main_layout = QHBoxLayout()
      self.setLayout(self.main_layout)

      self.stack = QStackedWidget()
      
      self.init_friend_group()
      self.main_layout.addWidget(self.stack)
      
      self.init_message_group()
      self.init_friend_management_group()

      self.stack.setCurrentIndex(0)

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
      friend_info_bar.setFixedHeight(80)
      friend_info_bar_layout = QFormLayout()
      friend_info_bar.setLayout(friend_info_bar_layout)
      friend_layout.addWidget(friend_info_bar)
      friend_info_label = QLabel("Friends List")
      friend_info_label.setFont(QFont(FONT_NAME, 16))
      friend_info_bar_layout.addRow(friend_info_label)
      friend_mng_button = QPushButton("Manage Friends")
      friend_mng_button.clicked.connect(self.switch_to_friend_management_group)
      friend_info_bar_layout.addRow(friend_mng_button)

      friends_scroll_area = QScrollArea()
      friends_scroll_area.setWidgetResizable(True)
      friends_scroll_content = QWidget()
      friends_scroll_area.setWidget(friends_scroll_content)
      self.friends_scroll_layout = QFormLayout()
      self.friends_scroll_layout.setContentsMargins(0, 0, 0, 0)
      self.friends_scroll_layout.setSpacing(0)
      friends_scroll_content.setLayout(self.friends_scroll_layout)
      friend_layout.addWidget(friends_scroll_area)

   def switch_to_friend_management_group(self):
      self.stack.setCurrentIndex(1)
      self.cur_friend_msging = None
      self.set_friend_scroll_area_cur_friend(None)

   def init_message_group(self):
      message_group = QWidget()
      message_layout = QVBoxLayout()
      message_group.setLayout(message_layout)
      self.stack.addWidget(message_group)

      self.msgs_layout = QVBoxLayout()
      self.msgs_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
      self.msgs_layout.setSpacing(0)
      
      self.msgs_content = QWidget()
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

   def init_friend_management_group(self):
      friend_mng_group = QWidget()
      friend_mng_layout = QFormLayout()
      friend_mng_group.setLayout(friend_mng_layout)
      self.stack.addWidget(friend_mng_group)

      find_friend_section = QWidget()
      find_friend_layout = QHBoxLayout()
      find_friend_section.setLayout(find_friend_layout)
      friend_mng_layout.addRow(find_friend_section)

      self.find_friend_response_label = QLabel("")
      self.find_friend_response_label.setStyleSheet("color : #f20000")

      self.find_friend_field = QLineEdit()
      self.find_friend_field.setPlaceholderText("Search for friend")
      self.find_friend_field.setMaxLength(MAX_USERNAME_LENGTH)
      self.find_friend_field.setValidator(QRegExpValidator(QRegExp(USERNAME_REG_EXP)))
      self.find_friend_field.textChanged.connect(lambda: self.find_friend_response_label.clear())
      find_friend_layout.addWidget(self.find_friend_field)
      self.find_friend_submit_button = QPushButton("Send Friend Request")
      self.find_friend_submit_button.clicked.connect(self.on_submit_add_friend)
      find_friend_layout.addWidget(self.find_friend_submit_button)

      friend_mng_layout.addRow(self.find_friend_response_label)

      friend_sent_req_group = QWidget()
      friend_sent_req_layout = QHBoxLayout()
      friend_sent_req_group.setLayout(friend_sent_req_layout)
      
      sent_group = QWidget()
      sent_layout = QVBoxLayout()
      sent_group.setLayout(sent_layout)
      sent_label = QLabel("Sent Friend Requests")
      sent_label.setFont(QFont(FONT_NAME, 14))
      sent_label.setFixedHeight(30)
      sent_layout.addWidget(sent_label)
      # Scroll area
      sent_scroll_area = QScrollArea()
      sent_scroll_area.setWidgetResizable(True)
      sent_layout.addWidget(sent_scroll_area)
      sent_scroll_content = QWidget()
      self.sent_friend_req_scroll_layout = QFormLayout()
      sent_scroll_content.setLayout(self.sent_friend_req_scroll_layout)
      sent_scroll_area.setWidget(sent_scroll_content)
      friend_sent_req_layout.addWidget(sent_group)

      req_group = QWidget()
      req_layout = QVBoxLayout()
      req_group.setLayout(req_layout)
      req_label = QLabel("Friend Requests")
      req_label.setFont(QFont(FONT_NAME, 14))
      req_label.setFixedHeight(30)
      req_layout.addWidget(req_label)
      # Scroll area
      req_scroll_area = QScrollArea()
      req_scroll_area.setWidgetResizable(True)
      req_layout.addWidget(req_scroll_area)
      req_scroll_content = QWidget()
      self.req_friend_scroll_layout = QFormLayout()
      req_scroll_content.setLayout(self.req_friend_scroll_layout)
      req_scroll_area.setWidget(req_scroll_content)
      friend_sent_req_layout.addWidget(req_group)

      friend_mng_layout.addRow(friend_sent_req_group)


   def on_submit_add_friend(self):
      friend = self.find_friend_field.text()
      if friend == self.username:
         self.set_add_friend_error_text("Cannot add yourself as a friend!")
         return
      
      self.find_friend_field.setText("")
      
      self.conn.send_json_object({
         "act": "add_friend",
         "user": friend
      })
      self.find_friend_submit_button.setDisabled(True)

   def handle_packets(self):
      
      if not self.isVisible():
         # Do not update anything until visible because otherwise values calculated
         # will be inaccurate!
         return

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
                  friends = server_obj["body"]
               
                  for friend in friends:
                     self.add_friend_widget(friend)
                  
                  if len(friends) > 0:
                     self.switch_to_chatting_with(friends[0])

               case "sent_friends_requests":
                  sent_friends = server_obj["body"]
                  for sent_friend in sent_friends:
                     self.add_sent_friend_request_widget(sent_friend)

               case "friend_requests":
                  friend_reqs = server_obj["body"]
                  for friend_req in friend_reqs:
                     self.add_friend_request_widget(friend_req)

               case "friend_req":
                  user_who_sent_req = server_obj["user"]
                  
                  if self.remove_sent_friend_req(user_who_sent_req):
                     self.add_friend_widget(user_who_sent_req)
                  else:
                     self.add_friend_request_widget(user_who_sent_req)

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
               case "add_friend":
                  status      = server_obj["status"]
                  sent_friend = server_obj["user"]
                  self.find_friend_submit_button.setDisabled(False)

                  if status == "no_such_user":
                     self.set_add_friend_error_text("There is no user by that username.")
                  elif status == "already_friends":
                     self.set_add_friend_error_text("You are already friends with that user.")
                  elif status == "already_sent":
                     self.set_add_friend_error_text("You already sent a friend request to that user.")
                  elif status == "request_sent":
                     self.find_friend_response_label.setText("Successfully sent friend request!")
                     self.find_friend_response_label.setStyleSheet("")
                     self.add_sent_friend_request_widget(sent_friend)
                  elif status == "now_friends":
                     self.find_friend_response_label.setText("You are now friends with the user!")
                     self.find_friend_response_label.setStyleSheet("")

                     # Iterate through the friend requests and remove the request by the user.
                     for i in range(self.req_friend_scroll_layout.count()):
                        friend_req_widget = self.req_friend_scroll_layout.itemAt(i).widget()
                        if friend_req_widget.text() == sent_friend:
                           friend_req_widget.setParent(None)

                     self.add_friend_widget(sent_friend)

               case "disconnect":
                  self.on_disconnection()

               case _:
                  print(f"Unknown act from server: {act}")

   def on_disconnection(self):
      # Need to cleanup all the dynamic widgets.
      clear_layout(self.msgs_layout)
      clear_layout(self.friends_scroll_layout)
      clear_layout(self.sent_friend_req_scroll_layout)
      clear_layout(self.req_friend_scroll_layout)

      self.cur_friend_msging = None
      self.decoded_json_objects = []
      
      self.close()
      self.login_form.set_form_enabled(True)
      self.login_form.show()

   def add_friend_request_widget(self, friend_req):
      req_group = QLabel(friend_req)
      req_group.setFont(QFont(FONT_NAME, 12))
      req_group.setFixedHeight(30)
      self.req_friend_scroll_layout.addWidget(req_group)

   def add_sent_friend_request_widget(self, sent_friend):
      sent_group = QLabel(sent_friend)
      sent_group.setFont(QFont(FONT_NAME, 12))
      sent_group.setFixedHeight(30)
      self.sent_friend_req_scroll_layout.addWidget(sent_group)

   def remove_sent_friend_req(self, friend):
      """Iterates over the sent friend request widgets looking for the widget
         containing the friend by name ``friend``. Returns true if such a
         the widget was found and removed.

         :param friend: The friend name to search for and remove in the sent friend requests. 
      """
      for i in range(self.sent_friend_req_scroll_layout.count()):
         sent_friend_req_widget = self.sent_friend_req_scroll_layout.itemAt(i).widget()
         if sent_friend_req_widget.text() == friend:
            sent_friend_req_widget.setParent(None)
            return True
      return False

   def add_friend_widget(self, friend):
      friend_label = FriendLabel(friend, self)
      friend_label.setFont(QFont(FONT_NAME, 12))
      friend_label.setFixedHeight(30)
      self.friends_scroll_layout.addRow(friend_label)

   def set_add_friend_error_text(self, text):
      self.find_friend_response_label.setText(text)
      self.find_friend_response_label.setStyleSheet("color : #f20000")

   def add_message_to_chat(self, from_user, msg):
      
      msg_label = QLabel(f"{from_user}: {msg}")
      msg_label.setFont(QFont(FONT_NAME, 10))
      msg_label.setWordWrap(True)
      msg_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Minimum)
      # Setting the style sheet temporarily so things align correctly.
      # Without this the text ends up with very weird spacing.
      msg_label.setStyleSheet("background-color : red")
      msg_label.setStyleSheet("")

      self.msgs_layout.addWidget(msg_label)

   def msg_scrollbar_update(self):
      # TODO: when requesting logs that are not the first set of logs this will need
      # to not be set.
      vbar = self.msg_scroll_area.verticalScrollBar()
      vbar.setValue(vbar.maximum())
      

   def switch_to_chatting_with(self, friend):
      self.msg_field.setDisabled(False)

      if self.cur_friend_msging == friend:
         return
      
      self.stack.setCurrentIndex(0)
      self.cur_friend_msging = friend
      self.msgs_content.setFixedHeight(0)
      self.set_friend_scroll_area_cur_friend(friend)

      self.conn.send_json_object({
         "act": "chat_logs",
         "user": friend,
         "block": 0 # TODO: Will want to select more than the first 50 logs!
      })

      clear_layout(self.msgs_layout)

   def set_friend_scroll_area_cur_friend(self, friend):
      for i in range(self.friends_scroll_layout.count()):
         friend_label = self.friends_scroll_layout.itemAt(i).widget()
         
         if friend == friend_label.friend:
            friend_label.setStyleSheet("background-color : gray")
         else:
            friend_label.setStyleSheet("""
               QLabel:hover { background-color : #9c9c9c; }
            """)

   def run_packet_recv_thread(self):
      Thread(target=self.recv_packets).start()

   def recv_packets(self):
      """Continues to read json objects from the server as
         long as the connection is open.
      """
      while self.conn.is_open():
         server_obj = self.conn.read_json_object()
         
         if server_obj == None:
               # Means connection was closed.
               break

         self.decoded_json_objects.append(server_obj)

      self.decoded_json_objects.append({ "act": "disconnect" })

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