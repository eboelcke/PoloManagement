# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ConnectionDialog.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(326, 459)
        Dialog.setModal(True)
        self.widget = QtWidgets.QWidget(Dialog)
        self.widget.setGeometry(QtCore.QRect(20, 11, 291, 435))
        self.widget.setObjectName("widget")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.widget)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.formLayout = QtWidgets.QFormLayout()
        self.formLayout.setObjectName("formLayout")
        self.label_7 = QtWidgets.QLabel(self.widget)
        self.label_7.setObjectName("label_7")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label_7)
        self.line_edit_host = QtWidgets.QLineEdit(self.widget)
        self.line_edit_host.setObjectName("line_edit_host")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.line_edit_host)
        self.label_2 = QtWidgets.QLabel(self.widget)
        self.label_2.setObjectName("label_2")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.label_2)
        self.line_edit_user = QtWidgets.QLineEdit(self.widget)
        self.line_edit_user.setObjectName("line_edit_user")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.line_edit_user)
        self.label_3 = QtWidgets.QLabel(self.widget)
        self.label_3.setObjectName("label_3")
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.label_3)
        self.line_edit_database = QtWidgets.QLineEdit(self.widget)
        self.line_edit_database.setObjectName("line_edit_database")
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.line_edit_database)
        self.label_5 = QtWidgets.QLabel(self.widget)
        self.label_5.setTextFormat(QtCore.Qt.PlainText)
        self.label_5.setObjectName("label_5")
        self.formLayout.setWidget(3, QtWidgets.QFormLayout.LabelRole, self.label_5)
        self.line_edit_password = QtWidgets.QLineEdit(self.widget)
        self.line_edit_password.setInputMethodHints(QtCore.Qt.ImhHiddenText|QtCore.Qt.ImhNoAutoUppercase|QtCore.Qt.ImhNoPredictiveText|QtCore.Qt.ImhSensitiveData)
        self.line_edit_password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.line_edit_password.setObjectName("line_edit_password")
        self.formLayout.setWidget(3, QtWidgets.QFormLayout.FieldRole, self.line_edit_password)
        self.label_4 = QtWidgets.QLabel(self.widget)
        self.label_4.setTextFormat(QtCore.Qt.PlainText)
        self.label_4.setObjectName("label_4")
        self.formLayout.setWidget(4, QtWidgets.QFormLayout.LabelRole, self.label_4)
        self.line_edit_check = QtWidgets.QLineEdit(self.widget)
        self.line_edit_check.setInputMethodHints(QtCore.Qt.ImhHiddenText|QtCore.Qt.ImhNoAutoUppercase|QtCore.Qt.ImhNoPredictiveText|QtCore.Qt.ImhSensitiveData)
        self.line_edit_check.setEchoMode(QtWidgets.QLineEdit.Password)
        self.line_edit_check.setObjectName("line_edit_check")
        self.formLayout.setWidget(4, QtWidgets.QFormLayout.FieldRole, self.line_edit_check)
        self.verticalLayout_2.addLayout(self.formLayout)
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        spacerItem = QtWidgets.QSpacerItem(246, 13, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.txt_edit_connection = QtWidgets.QTextEdit(self.widget)
        self.txt_edit_connection.setObjectName("txt_edit_connection")
        self.verticalLayout.addWidget(self.txt_edit_connection)
        self.verticalLayout_2.addLayout(self.verticalLayout)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.pbtnSave = QtWidgets.QPushButton(self.widget)
        self.pbtnSave.setObjectName("pbtnSave")
        self.horizontalLayout.addWidget(self.pbtnSave)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem1)
        self.pbtn_test = QtWidgets.QPushButton(self.widget)
        self.pbtn_test.setObjectName("pbtn_test")
        self.horizontalLayout.addWidget(self.pbtn_test)
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem2)
        self.pbtnQuit = QtWidgets.QPushButton(self.widget)
        self.pbtnQuit.setObjectName("pbtnQuit")
        self.horizontalLayout.addWidget(self.pbtnQuit)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        self.pbtn_test.raise_()
        self.txt_edit_connection.raise_()
        self.label_7.setBuddy(self.line_edit_host)
        self.label_2.setBuddy(self.line_edit_user)
        self.label_3.setBuddy(self.line_edit_database)
        self.label_5.setBuddy(self.line_edit_password)
        self.label_4.setBuddy(self.line_edit_check)

        self.retranslateUi(Dialog)
        self.pbtnQuit.clicked.connect(Dialog.close)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Connection Settings"))
        self.label_7.setText(_translate("Dialog", "&Server"))
        self.line_edit_host.setToolTip(_translate("Dialog", "Server Name or ip address"))
        self.label_2.setText(_translate("Dialog", "&User"))
        self.line_edit_user.setToolTip(_translate("Dialog", "User name"))
        self.label_3.setText(_translate("Dialog", "&Database"))
        self.line_edit_database.setToolTip(_translate("Dialog", "database name"))
        self.label_5.setText(_translate("Dialog", "&Password"))
        self.line_edit_password.setToolTip(_translate("Dialog", "password for user"))
        self.label_4.setText(_translate("Dialog", "&Type"))
        self.line_edit_check.setToolTip(_translate("Dialog", "password for user"))
        self.pbtnSave.setToolTip(_translate("Dialog", "Saves the current connection string to  file"))
        self.pbtnSave.setText(_translate("Dialog", "&Save"))
        self.pbtn_test.setText(_translate("Dialog", "Test"))
        self.pbtnQuit.setText(_translate("Dialog", "&Quit"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Dialog = QtWidgets.QDialog()
    ui = Ui_Dialog()
    ui.setupUi(Dialog)
    Dialog.show()
    sys.exit(app.exec_())

