import sys
from PyQt5.QtWidgets import QApplication
import form
import messaging
from PyQt5 import QtCore

if __name__ == "__main__":
    hostname = open("host.txt", "r").read()

    app = QApplication(sys.argv)
    login_form = form.LoginForm(hostname)
    message_board = messaging.MessageBoard()
    login_form.message_board = message_board
    message_board.login_form = login_form

    # TODO: would be nice to have this within a member function of
    #       LoginForm but for some unknown reason it refuses to start.
    login_check_timer = QtCore.QTimer()
    login_check_timer.setInterval(100)
    login_check_timer.timeout.connect(login_form.login_check)
    login_check_timer.start()

    # Telling the application to run!
    login_form.show()
    sys.exit(app.exec_())
