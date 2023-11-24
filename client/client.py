import sys
from PyQt5.QtWidgets import QApplication
import login_form
import messaging
import connection
from PyQt5 import QtCore

if __name__ == "__main__":
    hostname = open("host.txt", "r").read()
    
    conn = connection.Connection()

    app = QApplication(sys.argv)
    login_form = login_form.LoginForm(hostname, conn)
    message_board = messaging.MessageBoard(conn)
    login_form.message_board = message_board
    message_board.login_form = login_form

    for arg in sys.argv:
        if arg.startswith("-u:"):
            login_form.username_field.setText(arg.split(":")[1])
        elif arg.startswith("-p:"):
            login_form.password_field.setText(arg.split(":")[1])

    # Telling the application to run!
    login_form.show()
    exit_code = app.exec_()
    conn.close()
    sys.exit(exit_code)
