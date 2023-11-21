from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from connection import connection
from threading import Thread
from enum import Enum

MAX_USERNAME_LENGTH = 16
USERNAME_REG_EXP    = QRegExp("[a-zA-Z][a-zA-Z_0-9]*")

MAX_PASSWORD_LENGTH = 30

class LoginResponse(Enum):
    NONE        = 0
    SUCCESS     = 1
    WRONG_CREDS = 2

class LoginForm(QWidget):

    message_board : QWidget

    def __init__(self, hostname):
        super().__init__()
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

    def login_check(self):
        if self.login_response == LoginResponse.SUCCESS:
            self.login_response = LoginResponse.NONE
            self.on_successful_login()
        elif self.login_response == LoginResponse.WRONG_CREDS:
            self.login_response = LoginResponse.NONE
            self.error_label.setText("Invalid credentials")
            self.set_form_enabled(True)

    def on_successful_login(self):
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
        # Starting the connection on a seperate thread to prevent
        # the application from freezing.
        connect_thread = Thread(target=self.try_connect, args=(username, password))
        connect_thread.start()

    def try_connect(self, username, password):

        try:
            connection.create_connection(self.hostname)
        except Exception:
            self.error_label.setText("Failed to connect to server")
            self.set_form_enabled(True)
            return


        connection.send_json_object({ "username": username, "password": password })
        response = connection.read_json_object()
        
        status = response["status"]
        if status == "success":
            self.login_response = LoginResponse.SUCCESS
        elif status == "wrong_creds":
            self.login_response = LoginResponse.WRONG_CREDS
            connection.close()
        else:
            connection.close()

    def center_on_monitor(self):
        fg = self.frameGeometry()
        fg.moveCenter(QDesktopWidget().availableGeometry().center())
        self.move(fg.topLeft())
