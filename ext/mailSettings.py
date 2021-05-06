import sys
import os

from PyQt5.QtWidgets import (QDialog, QMessageBox, QLineEdit,QLabel, QPushButton,
                             QFormLayout,QFileDialog, QHBoxLayout, QVBoxLayout)
from PyQt5.QtCore import QSettings, QDate, pyqtSlot, Qt, QRegExp
from PyQt5.QtGui import QRegExpValidator
from ext.APM import LineEditHover, EMAILREGEXP
import poloresurce

class MailSettings(QDialog):
    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        self.setUI()

    def setUI(self):
        self.setWindowTitle("EMail Settings")
        self.setModal(True)

        rx = EMAILREGEXP
        lblAddress = QLabel("EMail Address")
        self.lineAddress = LineEditHover()
        self.lineAddress.setRegExpValidator(rx)

        lblPassword = QLabel("Password")
        self.linePwd = QLineEdit()
        self.linePwd.setEchoMode(QLineEdit.PasswordEchoOnEdit)

        lblOauth2 = QLabel("Oauth2 Token")
        self.lineOauth = QLineEdit()
        pushOauth = QPushButton("...")
        pushOauth.setObjectName("token")
        pushOauth.clicked.connect(self.lookForFile)
        pushOauth.setFixedWidth(30)

        lblDraft = QLabel("eMail Folder")
        self.lineDraft = QLineEdit()
        pushDraft = QPushButton("...")
        pushDraft.setObjectName("Draft")
        pushDraft.setFixedWidth(30)
        pushDraft.clicked.connect(self.lookForFile)

        pushCancel = QPushButton("Exit")
        pushCancel.setFixedWidth(80)
        pushCancel.clicked.connect(self.close)

        pushSave = QPushButton("Save")
        pushSave.setFixedWidth(80)
        pushSave.clicked.connect(self.saveAndClose)


        OauthLayout = QHBoxLayout()
        OauthLayout.addWidget(self.lineOauth)
        OauthLayout.addWidget(pushOauth)

        draftLayout = QHBoxLayout()
        draftLayout.addWidget(self.lineDraft)
        draftLayout.addWidget(pushDraft)

        formLayout = QFormLayout()
        formLayout.addRow(lblAddress, self.lineAddress)
        formLayout.addRow(lblPassword, self.linePwd)
        formLayout.addRow(lblOauth2, OauthLayout)
        formLayout.addRow(lblDraft, draftLayout)
        formLayout.addRow(pushCancel, pushSave)

        self.setLayout(formLayout)
        self.loadData()
        self.lineAddress.setFocus()
        self.lineAddress.selectAll()

    @pyqtSlot(int)
    def checkValidator(self, pos):
        v = self.mailValidator.validate(self.lineAddress.text(), pos)
        if v[0] == 0:
            self.lineAddress.setText(self.lineAddress.text()[:-1])

    @pyqtSlot(QRegExp)
    def checkRegExp(self, rx):
        if not rx.exactMatch(self.lineAddress.text()) and self.lineAddress.text():
            if QMessageBox.question(self, "Leave the Address field",
            "The string entered is not a valid email address! \n" 
             "Do you want to clear the field?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
                self.lineAddress.clear()
            else:
                self.lineAddress.setFocus()


    def loadData(self):
        try:
            settings = QSettings("ext/config.ini", QSettings.IniFormat)
            self.lineAddress.setText(settings.value("email/address"))
            self.linePwd.setText(settings.value("email/password"))
            self.lineOauth.setText(settings.value("email/outh2_token"))
            self.lineDraft.setText(settings.value("email/draftfolder"))
        except Exception as err:
            print("SendMail: loadData", err.args)

    def saveAndClose(self):
        try:
            if not self.lineAddress.text() or not self.linePwd.text():
                if not self.lineAddress.text():
                    msg = "You must enter the administrator email address"
                if not self.linePwd.text():
                    msg = "You must enter the mail account password"
                QMessageBox.warning(self, "Email address errors", msg, QMessageBox.Ok)
            sett = QSettings("ext/config.ini", QSettings.IniFormat)
            sett.setValue("email/address", self.lineAddress.text())
            sett.setValue("email/password", self.linePwd.text())
            sett.setValue("email/outh2_token", self.lineOauth.text())
            sett.setValue("email/draftfolder", self.lineDraft.text())
            self.close()
        except Exception as err:
            print("MailSettings: saveAndClose")

    @pyqtSlot()
    def lookForFile(self):
        try:
            if not self.sender().hasFocus():
                return
            baseDir = "C"
            obj = self.sender()
            if obj.objectName() == "Draft":
                capt = "Email Draft"
                baseDir = os.getcwd() + "\\draft"
                fileType = "Polo Management Email (*.pad)"
                dialog = QFileDialog(self, directory=os.getcwd())
                dialog.setFileMode(QFileDialog.Directory)
                res = dialog.getExistingDirectory()

            elif obj.objectName() == "token":
                capt = "Gmail Outh2 token File"
                fileType = "Gmail token Files (*.json)"
                baseDir = self.lineOauth.text()
                res = QFileDialog.getOpenFileName(self, caption=capt, directory=baseDir, filter=fileType)[0]
            fileName = res
            if obj.objectName() == "Draft":
                self.lineDraft.setText(fileName)
            elif obj.objectName() == "tokenFile":
                self.lineOauth.setText(fileName)
        except Exception as err:
            print("settings: lookForFile", err.args)



