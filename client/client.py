from PyQt5 import QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sys

MAX_USERNAME_LENGTH = 12
USERNAME_REG_EXP    = QRegExp("[a-zA-Z][a-zA-Z_0-9]*")

MAX_PASSWORD_LENGTH = 30

class LoginForm(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Messenger")
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

        submit_button = QPushButton("Login")
        submit_button.setFixedSize(250, 30)
        submit_button.clicked.connect(self.attempt_login)

        layout.addRow(self.username_label)
        layout.addRow(self.username_field)
        layout.addRow(self.password_label)
        layout.addRow(self.password_field)
        layout.addRow(self.error_label)
        layout.addRow(submit_button)

    def attempt_login(self):
        if self.username_field.text() == "":
            self.error_label.setText("No username provided")
            return
        if self.password_field.text() == "":
            self.error_label.setText("No password provided")
            return

        print("Attempting to login to server!")

    def center_on_monitor(self):
        fg = self.frameGeometry()
        fg.moveCenter(QDesktopWidget().availableGeometry().center())
        self.move(fg.topLeft())

app = QApplication(sys.argv)
login_form = LoginForm()

# Telling the application to run!
login_form.show()
sys.exit(app.exec_())
