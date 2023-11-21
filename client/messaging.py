from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class MessageBoard(QWidget):
     
     login_form : QWidget
     
     def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Messenger")
        self.setFixedSize(400, 300)