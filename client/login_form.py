from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from threading import Thread
from enum import Enum
import connection

MAX_USERNAME_LENGTH = 16
USERNAME_REG_EXP    = QRegExp("[a-zA-Z][a-zA-Z_0-9]*")

MAX_PASSWORD_LENGTH = 30

class LoginResponse(Enum):
    NONE         = 0
    SUCCESS      = 1
    WRONG_CREDS  = 2
    CONNECT_FAIL = 3

class LoginForm(QWidget):

    message_board : QWidget

    def __init__(self, hostname, conn: connection.Connection):
        super().__init__()
        self.conn = conn
        self.hostname = hostname
        self.login_response = LoginResponse.NONE

        self.setWindowTitle("Simple Messenger - Login")
        self.setFixedSize(270, 300)

        self.center_on_monitor()

        layout = QFormLayout()
        self.setLayout(layout)

        font_name = "Helvetica"

        self.username_label = QLabel("Username")
        self.username_label.setFont(QFont(font_name, 14))
        self.username_field = QLineEdit(self, maxLength=MAX_USERNAME_LENGTH)
        self.username_field.setFont(QFont(font_name, 12))
        self.username_field.setValidator(QRegExpValidator(USERNAME_REG_EXP))
        self.username_field.setFixedSize(250, 30)
        self.username_field.textChanged.connect(lambda: self.error_label.clear())

        self.password_label = QLabel("Password")
        self.password_label.setFont(QFont(font_name, 14))
        self.password_field = QLineEdit(self, maxLength=MAX_PASSWORD_LENGTH, echoMode=QLineEdit.EchoMode.Password)
        self.password_field.setFont(QFont(font_name, 12))
        self.password_field.setFixedSize(250, 30)
        self.password_field.textChanged.connect(lambda: self.error_label.clear())

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color : #f20000")

        self.submit_button = QPushButton("Login")
        self.submit_button.setFixedSize(250, 30)
        self.submit_button.clicked.connect(self.attempt_login)

        layout.addRow(self.username_label)
        layout.addRow(self.username_field)
        layout.addRow(self.password_label)
        layout.addRow(self.password_field)
        layout.addRow(self.error_label)
        layout.addRow(self.submit_button)

        self.login_check_timer = QTimer()
        self.login_check_timer.setInterval(100)
        self.login_check_timer.timeout.connect(self.login_check)
        self.login_check_timer.start()

    def login_check(self):
        if self.login_response == LoginResponse.SUCCESS:
            self.conn.send_json_object({ "act": "friends_list" })
            self.login_response = LoginResponse.NONE
            self.on_successful_login()
        elif self.login_response == LoginResponse.WRONG_CREDS:
            self.login_response = LoginResponse.NONE
            self.error_label.setText("Invalid credentials")
            self.set_form_enabled(True)
        elif self.login_response == LoginResponse.CONNECT_FAIL:
            self.login_response = LoginResponse.NONE
            self.error_label.setText("Failed to connect to server")
            self.set_form_enabled(True)

    def on_successful_login(self):
        self.message_board.run_packet_recv_thread()
        self.close()
        self.message_board.show()

    def set_form_enabled(self, tof):
        self.username_field.setDisabled(not tof)
        self.password_field.setDisabled(not tof)
        self.submit_button.setDisabled(not tof)

    def attempt_login(self):
        if self.username_field.text() == "":
            self.error_label.setText("No username provided")
            return
        if self.password_field.text() == "":
            self.error_label.setText("No password provided")
            return

        self.set_form_enabled(False)
        username = self.username_field.text()
        password = self.password_field.text()

        self.message_board.username = username
        # Starting the connection on a seperate thread to prevent
        # the application from freezing.
        connect_thread = Thread(target=self.try_connect, args=(username, password))
        connect_thread.start()

    def try_connect(self, username, password):

        try:
            self.conn.create_connection(self.hostname)
        except Exception:
            self.error_label.setText("Failed to connect to server")
            self.set_form_enabled(True)
            return


        self.conn.send_json_object({ "username": username, "password": password })
        response = self.conn.read_json_object()

        if response == None:
            # Server must have shutdown early.
            self.login_response = LoginResponse.CONNECT_FAIL
            self.conn.close()
            return
        
        status = response["status"]
        if status == "success":
            self.login_response = LoginResponse.SUCCESS
        elif status == "wrong_creds":
            self.login_response = LoginResponse.WRONG_CREDS
            self.conn.close()
        else:
            self.login_response = LoginResponse.CONNECT_FAIL
            self.conn.close()

    def center_on_monitor(self):
        fg = self.frameGeometry()
        fg.moveCenter(QDesktopWidget().availableGeometry().center())
        self.move(fg.topLeft())
