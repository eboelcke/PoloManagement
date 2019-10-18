import sys
import os

from PyQt5.QtWidgets import (QGroupBox, QDialog, QHBoxLayout, QVBoxLayout,QFormLayout, QLabel, QLineEdit, QComboBox,
                             QPushButton, QApplication, QFileDialog, QMessageBox, QFrame, QPlainTextEdit)
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
        self.setGeometry(50,50, 1000,500)
        lblDatabaseTitle = QLabel("MySQL Database Connection")
        lblDatabaseTitle.setAlignment(Qt.AlignCenter)
        lblDatabaseHost = QLabel("Host: ")
        lblDatabaseName = QLabel("Database")
        lblDatabaseUser = QLabel("User")
        lblDatabasePwd = QLabel("Password")
        lblTest = QLabel("Database Test")
        lblServerTest = QLabel("Connection Test")
        lblTCP = QLabel("TCP Server")
        lblTCP.setAlignment(Qt.AlignHCenter)

        lblOwnerTitle = QLabel("Horse Owner")
        lblOwnerTitle.setAlignment(Qt.AlignHCenter)

        lblOwner = QLabel("Owner")
        self.lineOwner = QLineEdit()

        lblAddress = QLabel("Address")
        self.textAddress = QPlainTextEdit()

        lblFarm = QLabel("Farm")
        self.lineFarm = QLineEdit()
        lblFarmAddress = QLabel("Farm Address")
        self.textFarmAddress = QPlainTextEdit()


        self.lblServerTestResult = QLabel('Untested')
        self.lblServerTestResult.setStyleSheet("QLabel {background-color: black; color:white}")
        self.lblServerTestResult.setMaximumWidth(150)
        self.lblTestResult = QLabel("Untested")
        self.lblTestResult.setStyleSheet("QLabel {background-color: black; color: white}")
        self.lblTestResult.setMaximumWidth(150)

        lblServerName = QLabel("Server Name", self)
        lblServerPort = QLabel("Port Number", self)

        lblOrganization = QLabel("Application Developer")
        lblOrganization.setAlignment(Qt.AlignCenter)
        lblOrganizationName = QLabel("Organization")
        lblSoftwareName = QLabel("Title")

        lblPath = QLabel("Directories and Paths")
        lblPath.setAlignment(Qt.AlignCenter)
        lblAgreementDir = QLabel("Agreements")
        lblIconsDir = QLabel("Icons")

        self.lineDatabaseHost = QLineEdit()
        self.lineDatabaseHost.setMaximumWidth(210)
        self.lineDatabaseName = QLineEdit()
        self.lineDatabaseName.setMaximumWidth(210)

        self.lineDatabaseUser = QLineEdit()
        self.lineDatabaseUser.setMaximumWidth(210)

        self.lineDatabasePwd = QLineEdit()
        self.lineDatabasePwd.setMaximumWidth(210)
        self.lineDatabasePwd.setEchoMode(QLineEdit.PasswordEchoOnEdit)

        self.lineOrganizationName = QLineEdit()
        self.lineSoftwareName = QLineEdit()
        self.lineAgreementDir = QLineEdit()
        self.lineIconsDir = QLineEdit()

        self.lineServerName = QLineEdit()
        self.lineServerName.setMaximumWidth(210)
        self.lineServerPort = QLineEdit()
        self.lineServerPort.setMaximumWidth(210)
        self.lineServerPort.editingFinished.connect(self.portAssert)

        self.btnOk = QPushButton("Save")
        self.btnOk.setEnabled(False)
        self.btnOk.clicked.connect(self.saveAndClose)

        self.btnContinue = QPushButton("Continue")
        self.btnContinue.setEnabled(False)
        self.btnContinue.clicked.connect(self.accept)

        btnCancel = QPushButton("Cancel")
        btnCancel.clicked.connect(self.close)

        btnTest = QPushButton("Test")
        btnTest.setMaximumWidth(50)
        btnTest.clicked.connect(self.connectionTest)

        btnServer = QPushButton("Test")
        btnServer.setMaximumWidth(50)
        btnServer.clicked.connect(self.serverTest)

        btnDir = QPushButton("...")
        btnDir.setMaximumWidth(30)
        btnDir.setMaximumHeight(28)
        btnDir.clicked.connect(self.lookForFile)

        lfrmLayout = QFormLayout()
        rfrmLayout = QFormLayout()
        testHLayout = QHBoxLayout()
        dirHLayout = QHBoxLayout()

        btnHLayout = QHBoxLayout()
        btnHLayout.addWidget(self.btnContinue)
        btnHLayout.addStretch(10)
        btnHLayout.addWidget(btnCancel)
        btnHLayout.addWidget(self.btnOk)

        testHLayout.addWidget(btnTest)
        testHLayout.addWidget(self.lblTestResult)

        serverHLayout = QHBoxLayout()
        serverHLayout.addWidget(btnServer)
        serverHLayout.addWidget(self.lblServerTestResult)

        dirHLayout.addWidget(self.lineAgreementDir)
        dirHLayout.addWidget(btnDir)

        lfrmLayout.addRow(lblDatabaseTitle)
        lfrmLayout.addRow(lblDatabaseHost, self.lineDatabaseHost)
        lfrmLayout.addRow(lblDatabaseName, self.lineDatabaseName)
        lfrmLayout.addRow(lblDatabaseUser, self.lineDatabaseUser)
        lfrmLayout.addRow(lblDatabasePwd, self.lineDatabasePwd)
        lfrmLayout.addRow(lblTest, testHLayout)
        lfrmLayout.addRow(lblTCP)
        lfrmLayout.addRow(lblServerName, self.lineServerName)
        lfrmLayout.addRow(lblServerPort, self.lineServerPort)
        lfrmLayout.addRow(lblServerTest, serverHLayout)
        lfrmLayout.addRow(lblOrganization)
        lfrmLayout.addRow(lblOrganizationName, self.lineOrganizationName)
        lfrmLayout.addRow(lblSoftwareName, self.lineSoftwareName)
        lfrmLayout.addRow(lblPath)
        lfrmLayout.addRow(lblAgreementDir, dirHLayout)
        lfrmLayout.addRow(lblIconsDir, self.lineIconsDir)


        rfrmLayout.addRow(lblOwnerTitle)
        rfrmLayout.addRow(lblOwner, self.lineOwner)
        rfrmLayout.addRow(lblAddress, self.textAddress)
        rfrmLayout.addRow(lblFarm, self.lineFarm)
        rfrmLayout.addRow(lblFarmAddress, self.textFarmAddress)


        frameLeft = QGroupBox("Servers")
        frameLeft.setLayout(lfrmLayout)
        frameRight = QGroupBox("Data and Directories")
        frameRight.setLayout(rfrmLayout)

        frameLayout = QHBoxLayout()
        frameLayout.addWidget(frameLeft)
        frameLayout.addWidget(frameRight)
        layout = QVBoxLayout()
        layout.addLayout(frameLayout)
        layout.addLayout(btnHLayout)
        self.setLayout(layout)

        settings = QSettings("ext/config.ini", QSettings.IniFormat)
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

        self.lineOwner.setText(settings.value("owner/ownerName"))
        self.textAddress.setPlainText(settings.value("owner/Address"))
        self.lineFarm.setText(settings.value("owner/FarmName"))
        self.textFarmAddress.setPlainText(settings.value("owner/FarmAddress"))

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
        self.lblServerTestResult.setText("Connecting")
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
                self.lblServerTestResult.setText("Failed")
                self.lblServerTestResult.setStyleSheet("QLabel {background-color:red; color: white}")
                return False, "Failed"

        except TypeError as err:
            self.lblServerTestResult.setText("Failed")
            self.lblServerTestResult.setStyleSheet("QLabel {background-color:red; color: white}")
            pop = QMessageBox()
            pop.setText("Connection to the python server Failed")
            pop.setDetailedText(err.args[0])
            pop.show()
            pop.exec_()
            return False, "Failed"

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

                sett.setValue("owner/ownerName", self.lineOwner.text())
                sett.setValue("owner/Address", self.textAddress.toPlainText())
                sett.setValue("owner/FarmName", self.lineFarm.text())
                sett.setValue("owner/FarmAddress", self.textFarmAddress.toPlainText())


            except Exception as err:
                print(tyoe(err).__name__, err.args)
            self.accept()

    def close(self):
        try:
            self.reject()
        except Exception as err:
            print(type(err).__name__, err.args)

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
        self.lblTestResult.setText("Connecting")
        self.lblTestResult.setStyleSheet("QLabel{background-color: yellow; color: black}")
        self.repaint()
        testMessage = "Failed"
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
                testMessage = "Succeeded"
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

    @property
    def owner(self):
        return self.lineOwner.text()

    @property
    def ownerAddress(self):
        return self.textAddress.toPlainText()

    @property
    def farm(self):
        return self.lineFarm.text()

    @property
    def farmAddress(self):
        return self.textFarmAddress.toPlainText()

    def checkBtnEnabled(self):
        if self.okToSave.count(True) == 2:
            self.btnOk.setEnabled(True)
            self.btnContinue.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    setting = SettingsDialog()
    setting.show()
    app.exec()


