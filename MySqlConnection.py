import MySQL_Connector
from ConnectionDialog import Ui_Dialog
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import pyqtSlot

import sys


class EmittingStream(QtCore.QObject):
    textWritten = QtCore.pyqtSignal(str)

    def write(self, text):
        try:
            self.textWritten.emit(str(text).strip())
        except Exception as err:
            print(err)

    def flush(self):
        pass


class MyConnectionDialog(QDialog, Ui_Dialog):
    def __init__(self):
        super(MyConnectionDialog, self).__init__()
        self.setupUi(self)

        self.connector = MySQL_Connector.MysqlConnection('ext/config.ini')
        self.db = self.connector.read_db_config()[1]
        try:
            self.line_edit_host.setText(self.db['host'])
            self.line_edit_user.setText(self.db['user'])
            self.line_edit_database.setText(self.db['database'])
            self.line_edit_password.setText(self.db['password'])
        except KeyError as err:
            message = "; '{}'".format(err)
            print(message)
        self.txt_edit_connection.setReadOnly(True)
        self.pbtnSave.setEnabled(False)
        if self.line_edit_host.text() == ''\
                or self.line_edit_user.text() == ''\
                or self.line_edit_database.text() == ''\
                or self.line_edit_password.text() == '':
            self.pbtn_test.setEnabled(False)
        else:
            self.pbtn_test.setEnabled(True)
        self.line_edit_check.setHidden(True)
        self.label_4.setText("Type again")
        self.label_4.setHidden(True)

        self.line_edit_host.editingFinished.connect(self.enable_pbtn_save)
        self.line_edit_user.editingFinished.connect(self.enable_pbtn_save)
        self.line_edit_database.editingFinished.connect(self.enable_pbtn_save)
        self.line_edit_password.editingFinished.connect(self.enable_pbtn_save)
        self.line_edit_password.editingFinished.connect(self.show_line_edit_check)
        self.line_edit_check.editingFinished.connect(self.validate_password)
        self.pbtn_test.clicked.connect(self.test_connection)
        self.pbtnSave.clicked.connect(self.save_config)
        self.show()
        return

    @pyqtSlot()
    def enable_pbtn_save(self):
        if self.line_edit_host.text() != '' \
                and self.line_edit_user.text() != '' \
                and self.line_edit_database.text() != ''\
                and self.line_edit_password.text() != '':
            self.pbtn_test.setEnabled(True)
            self.pbtnSave.setEnabled(True)
        else:
            self.pbtn_test.setEnabled(False)
            self.pbtnSave.setEnabled(False)


    @pyqtSlot()
    def show_line_edit_check(self):
        self.line_edit_check.setHidden(False)
        self.label_4.setHidden(False)
        self.line_edit_check.setFocus()

    @pyqtSlot()
    def validate_password(self):
        self.txt_edit_connection.clear()
        sys.stdout = EmittingStream(textWritten=self.Qtext_write)
        if self.line_edit_password.text() == self.line_edit_check.text():
            self.line_edit_check.clear()
            self.line_edit_check.setVisible(False)
            self.label_4.setVisible(False)
            print("You may use your new password if it's accepted by the host")
        else:
            self.line_edit_check.selectAll()
            self.line_edit_check.setFocus()
            print("The check password does'nt match.Try again!")
        sys.stdout = sys.__stdout__


    @pyqtSlot()
    def save_config(self):
        self.txt_edit_connection.clear()
        self.db = dict(host=self.line_edit_host.text(),
                       user=self.line_edit_user.text(),
                       database=self.line_edit_database.text(),
                       password=self.line_edit_password.text())
        try:
            sys.stdout = EmittingStream(textWritten=self.Qtext_write)
            res = self.connector.save_db_config(self.db)
            if res:
                print("Config file saved ")
            return res
        except Exception as err:
            print("Config file could not be save because {}".format(err))
        finally:
            sys.stdout = sys.__stdout__

    @pyqtSlot()
    def test_connection(self):
        try:
           sys.stdout = EmittingStream(textWritten=self.Qtext_write)
        except Exception as err:
            print(err)
        try:
            res = self.connector.test_connection()
            print(res[1])
            return res
        except Exception as err:
            print(err)
        finally:
            sys.stdout = sys.__stdout__

    def Qtext_write(self,text):
        cursor = self.txt_edit_connection.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        self.txt_edit_connection.append(text)
        self.txt_edit_connection.setTextCursor(cursor)
        self.txt_edit_connection.ensureCursorVisible()

def main():
    app = QtWidgets.QApplication(sys.argv)
    dialog = MyConnectionDialog()
    app.exec()

if __name__ == '__main__':
    main()