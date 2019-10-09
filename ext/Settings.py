import sys
import os

from PyQt5.QtWidgets import (QWidget, QDialog, QHBoxLayout, QVBoxLayout,QFormLayout, QLabel, QLineEdit, QComboBox,
                             QPushButton, QApplication, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt, QSettings, QCoreApplication, pyqtSlot
from PyQt5.QtSql import QSqlDatabase
from configparser import ConfigParser
from ext.socketclient import RequestHandler
import resources



class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        self.setUI()
        self.state = False
        self.con_string = {}
        self.address = self.serverAddress
        self.serverOk = False
        self.databaseOk = False
        self.okToSave = [self.serverOk, self.databaseOk]
        self.setModal(True)


    def setUI(self):
        self.setWindowTitle("Settings")
        self.setGeometry(50,50, 500,500)
        lblDatabaseTitle = QLabel("Database Connection")
        lblDatabaseTitle.setAlignment(Qt.AlignCenter)
        lblDatabaseName = QLabel("Database")
        lblDatabaseHost = QLabel("Host: ")
        lblDatabaseUser = QLabel("User")
        lblDatabasePwd = QLabel("Password")
        lblTest = QLabel("Database Test")
        lblServerTest = QLabel("Server Connection Test")
        self.lblServerTestResult = QLabel('Server connection untested')
        self.lblServerTestResult.setStyleSheet("QLabel {background-color: black; color:white}")
        self.lblTestResult = QLabel("Connection Untested")
        self.lblTestResult.setStyleSheet("QLabel {background-color: black; color: white}")

        lblServer = QLabel("Server Data", self)
        lblServer.setAlignment(Qt.AlignCenter)
        lblServerName = QLabel("Server Name", self)
        lblServerPort = QLabel("Port Number", self)

        lblOrganization = QLabel("Organization and Software")
        lblOrganization.setAlignment(Qt.AlignCenter)
        lblOrganizationName = QLabel("Organization")
        lblSoftwareName = QLabel("Title")

        lblPath = QLabel("Directories and Paths")
        lblPath.setAlignment(Qt.AlignCenter)
        lblAgreementDir = QLabel("Agreements")
        lblIconsDir = QLabel("Icons")

        self.lineDatabaseHost = QLineEdit()
        self.lineDatabaseName = QLineEdit()
        self.lineDatabaseUser = QLineEdit()
        self.lineDatabasePwd = QLineEdit()
        self.lineDatabasePwd.setEchoMode(QLineEdit.PasswordEchoOnEdit)

        self.lineOrganizationName = QLineEdit()
        self.lineSoftwareName = QLineEdit()
        self.lineAgreementDir = QLineEdit()
        self.lineIconsDir = QLineEdit()

        self.lineServerName = QLineEdit()
        self.lineServerPort = QLineEdit()
        self.lineServerPort.editingFinished.connect(self.portAssert)

        self.btnOk = QPushButton("OK")
        self.btnOk.setEnabled(False)
        self.btnOk.clicked.connect(self.saveAndClose)

        self.btnContinue = QPushButton("Continue")
        self.btnContinue.setEnabled(False)
        self.btnContinue.clicked.connect(self.accept)

        btnCancel = QPushButton("Cancel")
        btnCancel.clicked.connect(self.close)

        btnTest = QPushButton("Test")
        btnTest.setMaximumWidth(100)
        btnTest.clicked.connect(self.connectionTest)

        btnServer = QPushButton("Server")
        btnServer.setMaximumWidth(100)
        btnServer.clicked.connect(self.serverTest)

        btnDir = QPushButton("...")
        btnDir.setMaximumWidth(30)
        btnDir.setMaximumHeight(28)
        btnDir.clicked.connect(self.lookForFile)


        btnHLayout = QHBoxLayout()
        frmLayout = QFormLayout()
        testHLayout = QHBoxLayout()
        dirHLayout = QHBoxLayout()
        vLayout = QVBoxLayout()

        btnHLayout.addWidget(self.btnContinue)
        btnHLayout.addStretch(10)
        btnHLayout.addWidget(self.btnOk)
        btnHLayout.addWidget(btnCancel)

        testHLayout.addWidget(btnTest)
        testHLayout.addWidget(self.lblTestResult)

        serverHLayout = QHBoxLayout()
        serverHLayout.addWidget(btnServer)
        serverHLayout.addWidget(self.lblServerTestResult)

        dirHLayout.addWidget(self.lineAgreementDir)
        dirHLayout.addWidget(btnDir)

        frmLayout.addRow(lblDatabaseTitle)
        frmLayout.addRow(lblDatabaseHost, self.lineDatabaseHost)
        frmLayout.addRow(lblDatabaseName, self.lineDatabaseName)
        frmLayout.addRow(lblDatabaseUser, self.lineDatabaseUser)
        frmLayout.addRow(lblDatabasePwd, self.lineDatabasePwd)
        frmLayout.addRow(lblTest, testHLayout)
        frmLayout.addRow(lblOrganization)
        frmLayout.addRow(lblOrganizationName, self.lineOrganizationName)
        frmLayout.addRow(lblSoftwareName, self.lineSoftwareName)
        frmLayout.addRow(lblPath)
        frmLayout.addRow(lblAgreementDir, dirHLayout)
        frmLayout.addRow(lblIconsDir, self.lineIconsDir)
        frmLayout.addRow(lblServerName, self.lineServerName)
        frmLayout.addRow(lblServerPort, self.lineServerPort)
        frmLayout.addRow(lblServerTest, serverHLayout)

        vLayout.addLayout(frmLayout)
        vLayout.addStretch(10)
        vLayout.addLayout(btnHLayout)
        self.setLayout(vLayout)

        settings = QSettings(":ext/config.ini", QSettings.IniFormat)
        self.lineDatabaseHost.setText(settings.value("mysql/host"))
        self.lineDatabaseName.setText(settings.value("mysql/Database"))
        self.lineDatabaseUser.setText(settings.value("mysql/user"))
        self.lineDatabasePwd.setText(settings.value("mysql/password"))

        self.lineOrganizationName.setText(settings.value("organization/companyName"))
        self.lineSoftwareName.setText(settings.value("organization/softwareTitle"))

        self.lineAgreementDir.setText(settings.value("path/Agreements"))
        self.lineIconsDir.setText(settings.value("path/icons"))

        self.lineServerName.setText(settings.value("Server/serverName"))
        self.lineServerPort.setText(settings.value("Server/serverPort"))
        self.address = self.serverAddress

    @property
    def serverAddress(self):
        sett = QSettings(":ext/config.ini", QSettings.IniFormat)
        serverName = sett.value("Server/ServerName")
        serverPort = int(sett.value("Server/ServerPort"))
        address = (serverName, serverPort)
        return address

    @property
    def iconsRelativeDir(self):
        if self.state:
            return self.lineIconsDir.text()

    @property
    def agreementsDir(self):
        if self.state:
            return self.lineAgreementDir.text()


    @property
    def connectionString(self):
        if self.con_string:
            return self.con_string

    @pyqtSlot()
    def serverTest(self):
        self.lblServerTestResult.setText("Connecting to the Server.....")
        self.lblServerTestResult.setStyleSheet("QLabel {background-color:yellow; color: black}")
        self.repaint()
        try:
            ok, answer = RequestHandler.handle_request(RequestHandler, self.address, ["TEST"])
            if ok[0]:
                self.lblServerTestResult.setText(ok[1])
                self.lblServerTestResult.setStyleSheet("QLabel {background-color:green; color: white}")
                self.serverOk = True
                self.okToSave[1] = self.serverOk
                self.checkBtnEnabled()
                return True, ok[1]
            else:
                self.lblServerTestResult.setText("Connection Failed")
                self.lblServerTestResult.setStyleSheet("QLabel {background-color:red; color: white}")
                return False, "Connection Failed"

        except TypeError as err:
            self.lblServerTestResult.setText("Connection Failed")
            self.lblServerTestResult.setStyleSheet("QLabel {background-color:red; color: white}")
            pop = QMessageBox()
            pop.setText("Connection to the python server failed")
            pop.setDetailedText(err.args[0])
            pop.show()
            pop.exec_()
            return False, "Connection Failed"

    @pyqtSlot()
    def goForward(self):
        if __name__ == '__main__':
            os.system('python ./AgreementsServer.py')

    @pyqtSlot()
    def portAssert(self):
        if int(self.lineServerPort.text()) < 5001 or int(self.lineServerPort.text()) > 32767 :
            self.lineServerPort.setText("")
            popup = QMessageBox(QMessageBox.Warning,
                                "Parameter error",
                                "Port must be between 5001 and 32767",
                                QMessageBox.Ok, self)
            popup.show()

    @pyqtSlot()
    def lookForFile(self):
        try:
            if not os.path.exists(os.path.join(os.getcwd(), 'Agreements/')):
                os.makedirs(os.path.join(os.getcwd(),"Agreements/Breaking/"))
                os.makedirs(os.path.join(os.getcwd(), "Agreements/Play&Sale/"))
            rootDir = QFileDialog.getExistingDirectory(caption="Agreements Directory",
                                                       directory=os.getcwd())
            self.lineAgreementDir.setText(rootDir)
        except Exception as err:
            print(err)

    @pyqtSlot()
    def saveAndClose(self, state=False):
        if self.state:
            self.lblTestResult.setText("Connecting to MSQL database ........")
            try:
                assert (len(self.lineOrganizationName.text()) > 0 and len(
                self.lineSoftwareName.text()) > 0), "Missing Parameters"
                QSettings(self.lineOrganizationName.text(), self.lineSoftwareName.text())
                sett = QSettings("ext/config.ini", QSettings.IniFormat)
                sett.setValue("mysql/host", self.lineDatabaseHost.text())
                sett.setValue("mysql/user",self.lineDatabaseUser.text())
                sett.setValue("mysql/password", self.lineDatabasePwd.text())
                sett.setValue("mysql/database", self.lineDatabaseName.text())

                sett.setValue("organization/companyName", self.lineOrganizationName.text())
                sett.setValue("organization/SoftwareTitle", self.lineSoftwareName.text())

                sett.setValue("path/agreements", self.lineAgreementDir.text())
                sett.setValue("path/icons", self.lineIconsDir.text())

                sett.setValue("Server/serverName", self.lineServerName.text())
                sett.setValue("Server/serverPort", self.lineServerPort.text())


            except Exception as err:
                print(err)
            self.accept()

    def close(self):
        try:
            self.reject()
        except Exception as err:
            print(err)

    def read_db_config(self,section='mysql', configfile = 'config.ini'):
        """ Read database configuration file and return a dictionary object
        :param filename: name of the configuration file
        :param section: section of database configuration
        :return: a dictionary of database parameters
        """
        # create parser and read ini configuration file
        parser = ConfigParser()
        parser.read(configfile)
        conn_string = {}

        # get section, default to mysql
        try:
            if parser.has_section(section):
                items = parser.items(section)
                for item in items:
                    conn_string[item[0]] = item[1]
                return conn_string
            else:
                raise Exception('{0} not found in the {1} file'.format(section, self.filename))
        except Exception as err:
            print(err)
            return conn_string

    @pyqtSlot()
    def connectionTest(self):
        self.lblTestResult.setText("Connecting to MYSQL server........")
        self.lblTestResult.setStyleSheet("QLabel{background-color: yellow; color: black}")
        self.repaint()
        testMessage = "Connection Failed"
        self.con_string = {'host': self.lineDatabaseHost.text(), 'user': self.lineDatabaseUser.text(),
                           'database': self.lineDatabaseName.text(), 'password': self.lineDatabasePwd.text()}
        try:
            db = QSqlDatabase.addDatabase("QMYSQL3")
            db.setHostName(self.con_string['host'])
            db.setUserName(self.con_string['user'])
            db.setPassword(self.con_string['password'])
            db.setDatabaseName(self.con_string['database'])
            ok = db.open()
            if ok:
                testMessage = "Connection Succeeded"
                self.state = True
                self.lblTestResult.setStyleSheet("QLabel{background-color: green; color: white}")
                self.databaseOk = True
                self.okToSave[0]= self.databaseOk
                self.checkBtnEnabled()
            else:
                self.lblTestResult.setStyleSheet("QLabel{background-color: red; color: white}")
                raise TypeError("MySql is closed")
            self.lblTestResult.setText(testMessage)
        except Exception as err:
            self.lblTestResult.setText(err.args[0])
            pop = QMessageBox()
            pop.setText("Connection to MYSQL failed")
            pop.setDetailedText(db.lastError().text())
            pop.show()
            pop.exec_()
            return False, None
        return True, db

    def checkBtnEnabled(self):
        if self.okToSave.count(True) == 2:
            self.btnOk.setEnabled(True)
            self.btnContinue.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    setting = SettingsDialog()
    setting.show()
    app.exec()


