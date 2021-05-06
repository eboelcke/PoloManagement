import sys
import os

from PyQt5.QtWidgets import (QGroupBox, QDialog, QHBoxLayout, QVBoxLayout,QFormLayout, QLabel, QLineEdit, QComboBox,
                             QPushButton, QApplication, QFileDialog, QMessageBox, QFrame, QPlainTextEdit)
from PyQt5.QtCore import Qt, QSettings, QCoreApplication, pyqtSlot, QVariant,QRegExp
from PyQt5.QtSql import QSqlDatabase, QSqlQuery, QSqlQueryModel
from PyQt5.QtGui import QRegExpValidator, QRegularExpressionValidator
from configparser import ConfigParser
from ext.socketclient import RequestHandler
from ext.Contacts import Location
from ext.APM import DataError, LineEditHover,  FocusPlainTextEdit, CreateDatabase, FocusCombo, EMAILREGEXP
import resources
import poloresurce



class SettingsDialog(QDialog):
    def __init__(self, db=None, parent=None):
        super().__init__()
        self.parent = parent
        self.contactId = None
        self.locationId = None
        self.setUI()
        self.state = False
        self.con_string = {}
        self.access_con_string = None
        self.address = self.serverAddress
        self.serverOk = False
        self.databaseOk = False
        self.accessOk = False
        self.okToSave = [self.serverOk, self.databaseOk,self.accessOk]
        self.farmDirty = False
        self.ownerDirty = False
        self.db = db
        self.loadData()
        self.showComboLocation()
        self.isNameEditable = False
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

        lblAccess = QLabel("MS Access Database Connection")
        lblAccess.setAlignment(Qt.AlignCenter)
        lblDriver = QLabel("Driver")
        self.comboDriver = FocusCombo(self,["Microsoft Access Driver (*.mdb, *.accdb)",
                                       "Microsof Access Driver (*.mdb)"])
        self.comboDriver.setCurrentIndex(0)
        self.comboDriver.setModelColumn(1)
        lblAccessPath = QLabel("Access DB Path")
        self.linePath = QLineEdit()

        lblAccessName = QLabel("Database Name")
        self.lineAccessName = QLineEdit()

        btnAccessDir = QPushButton("...")
        btnAccessDir.setMaximumWidth(30)
        btnAccessDir.setMaximumHeight(28)
        btnAccessDir.setObjectName("AccessPath")
        btnAccessDir.clicked.connect(self.lookForPath)

        btnAccessFile = QPushButton("...")
        btnAccessFile.setMaximumWidth(30)
        btnAccessFile.setMaximumHeight(28)
        btnAccessFile.setObjectName("AccessFile")
        btnAccessFile.clicked.connect(self.lookForFile)

        btnIconsFile = QPushButton("...")
        btnIconsFile.setMaximumWidth(30)
        btnIconsFile.setMaximumHeight(28)
        btnIconsFile.setObjectName("IconsFile")
        btnIconsFile.clicked.connect(self.lookForFile)

        btnAccess = QPushButton("Test")
        btnAccess.setMaximumWidth(50)
        btnAccess.clicked.connect(self.accessTest)

        lblAccessConnect = QLabel("Connection Test")
        self.lblAccessTestResult = QLabel("Untested")
        self.lblAccessTestResult.setStyleSheet("QLabel {background-color: black; color: white}")
        self.lblAccessTestResult.setMaximumWidth(150)

        lblOwnerTitle = QLabel("Operation Owner")
        lblOwnerTitle.setAlignment(Qt.AlignHCenter)

        lblOwner = QLabel("Owner")
        self.lineOwner = QLineEdit()
        self.lineOwner.editingFinished.connect(self.dirtyOwner)
        self.lineOwner.editingFinished.connect(self.isEditable)

        lblAddress = QLabel("Address")
        self.textAddress = QPlainTextEdit()
        self.textAddress.document().modificationChanged.connect(self.dirtyOwner)

        self.lblFarm = QLabel("Main Location")
        self.lineFarm = QLineEdit()
        self.lineFarm.editingFinished.connect(self.dirtyFarm)

        self.lblNewLocation = QLabel("New Main Location")
        self.lblNewLocation.setVisible(False)
        self.comboLocation = FocusCombo()
        modelLocation = QSqlQueryModel()
        self.comboLocation.setEditable(True)
        self.comboLocation.setModel(modelLocation)
        self.comboLocation.activated.connect(self.dirtyFarm)
        self.comboLocation.currentIndexChanged.connect(self.upgradeLocationAddress)
        self.comboLocation.focusLost.connect(self.locationFocusLost)
        self.comboLocation.setVisible(False)

        lblFarmAddress = QLabel("Address")
        self.textFarmAddress = FocusPlainTextEdit()
        self.textFarmAddress.focusOut.connect(self.dirtyFarm)

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

        rx = EMAILREGEXP
        lblEMail = QLabel("EMail Settings")
        lblEMailAddress= QLabel("EMail Address")
        self.lineEMailAddress = LineEditHover()
        self.lineEMailAddress.setRegExpValidator(rx)

        lblEMailPassword = QLabel("EMail Password")
        self.lineEMailPassword = QLineEdit()
        self.lineEMailPassword.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        self.lineEMailPassword.setMaximumWidth(210)

        lblOauth2 = QLabel('Oauth2 token"')
        self.lineOauth2 = QLineEdit()
        self.lineOauth2.setMaximumWidth(210)
        self.lineOauth2.setObjectName("token")

        self.btnContinue = QPushButton("Continue")
        self.btnContinue.setEnabled(False)
        self.btnContinue.clicked.connect(self.accept)

        btnTestAll = QPushButton("Test All Servers")
        btnTestAll.clicked.connect(self.testAllServers)

        btnCancel = QPushButton("Cancel")
        btnCancel.clicked.connect(self.widgetClose)

        btnReset = QPushButton("Reset")
        btnReset.clicked.connect(self.resetData)

        btnTest = QPushButton("Test")
        btnTest.setMaximumWidth(50)
        btnTest.clicked.connect(self.connectionTest)

        btnServer = QPushButton("Test")
        btnServer.setMaximumWidth(50)
        btnServer.clicked.connect(self.serverTest)

        btnDir = QPushButton("...")
        btnDir.setMaximumWidth(30)
        btnDir.setMaximumHeight(28)
        btnDir.setObjectName("AgreementPath")
        btnDir.clicked.connect(self.lookForPath)

        btnOauth2 = QPushButton("...")
        btnOauth2 = QPushButton("...")
        btnOauth2.setMaximumWidth(30)
        btnOauth2.setMaximumHeight(28)
        btnOauth2.setObjectName("tokenFile")
        btnOauth2.clicked.connect(self.lookForFile)

        lfrmLayout = QFormLayout()
        rfrmLayout = QFormLayout()
        testHLayout = QHBoxLayout()
        dirHLayout = QHBoxLayout()
        accessHLayout = QHBoxLayout()

        btnHLayout = QHBoxLayout()
        btnHLayout.addWidget(self.btnContinue)
        btnHLayout.addWidget(btnTestAll)
        btnHLayout.addStretch(10)
        btnHLayout.addWidget(btnReset)
        btnHLayout.addWidget(btnCancel)
        btnHLayout.addWidget(self.btnOk)

        testHLayout.addWidget(btnTest)
        testHLayout.addWidget(self.lblTestResult)

        accessTestLayout = QHBoxLayout()
        accessTestLayout.addWidget(btnAccess)
        accessTestLayout.addWidget(self.lblAccessTestResult)

        accessNameLayout = QHBoxLayout()
        accessNameLayout.addWidget(self.lineAccessName)
        accessNameLayout.addWidget(btnAccessFile)

        emailOauth2Layout = QHBoxLayout()
        emailOauth2Layout.addWidget(self.lineOauth2)
        emailOauth2Layout.addWidget(btnOauth2)

        iconsFileLayout = QHBoxLayout()
        iconsFileLayout.addWidget(self.lineIconsDir)
        iconsFileLayout.addWidget(btnIconsFile)

        serverHLayout = QHBoxLayout()
        serverHLayout.addWidget(btnServer)
        serverHLayout.addWidget(self.lblServerTestResult)

        dirHLayout.addWidget(self.lineAgreementDir)
        dirHLayout.addWidget(btnDir)

        accessHLayout.addWidget(self.linePath)
        accessHLayout.addWidget(btnAccessDir)

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

        lfrmLayout.addRow(lblAccess)
        lfrmLayout.addRow(lblDriver, self.comboDriver)
        lfrmLayout.addRow(lblAccessPath,accessHLayout)
        lfrmLayout.addRow(lblAccessName, accessNameLayout)
        lfrmLayout.addRow(lblAccessConnect, accessTestLayout)

        lfrmLayout.addRow(lblEMail)
        lfrmLayout.addRow(lblEMailAddress, self.lineEMailAddress)
        lfrmLayout.addRow(lblEMailPassword, self.lineEMailPassword)
        lfrmLayout.addRow(lblOauth2, emailOauth2Layout)

        rfrmLayout.addRow(lblOwnerTitle)
        rfrmLayout.addRow(lblOwner, self.lineOwner)
        rfrmLayout.addRow(lblAddress, self.textAddress)
        rfrmLayout.addRow(self.lblFarm, self.lineFarm)
        rfrmLayout.addRow(self.lblNewLocation, self.comboLocation)
        rfrmLayout.addRow(lblFarmAddress, self.textFarmAddress)
        rfrmLayout.addRow(lblPath)
        rfrmLayout.addRow(lblAgreementDir, dirHLayout)
        rfrmLayout.addRow(lblIconsDir, iconsFileLayout)
        rfrmLayout.addRow(lblOrganization)
        rfrmLayout.addRow(lblOrganizationName, self.lineOrganizationName)
        rfrmLayout.addRow(lblSoftwareName, self.lineSoftwareName)


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

    @pyqtSlot()
    def testAllServers(self):
        try:
            self.connectionTest()
            self.serverTest()
            self.accessTest()
        except Exception as err:
            print("testAllServers", type(err), err.args)

    @pyqtSlot()
    def isEditable(self):
        try:
            msgBox = QMessageBox(self)
            msgBox.setText("Would you edit the owner's name or add a new one?")
            addButton = msgBox.addButton("Add", QMessageBox.ActionRole)
            editButton = msgBox.addButton('Edit',QMessageBox.ActionRole)
            cancelButton = msgBox.addButton(QMessageBox.Abort)
            ans = msgBox.exec()
            if msgBox.clickedButton() == editButton:
                self.isNameEditable = True
            elif msgBox.clickedButton() == addButton:
                self.isNameEditable = False
                self.textFarmAddress.clear()
                self.textAddress.clear()
                self.lineFarm.clear()
                self.locationId = None
                self.contactId, address = self.ownerLook()
                self.textAddress.setPlainText(address)
                self.showComboLocation()
        except Exception as err:
            print("isEditable", type(err), err.args)

    @pyqtSlot()
    def resetData(self):
        self.loadData()
        self.showComboLocation()

    @pyqtSlot()
    def upgradeLocationAddress(self):
        try:
            self.textFarmAddress.setPlainText(self.comboLocation.model().query().value(2))

        except Exception as err:
            print("upgradeLocationAdress", err.args)

    def showComboLocation(self):
        try:
            if not self.db.isOpen():
                self.db.open()
            self.loadLocationCombo()
            if self.comboLocation.model().query().size() < 1:
                return
            if self.locationId:
                row = self.comboLocation.seekData(self.locationId)
            else:
                row = self.comboLocation.seekData(1, 3)
            self.comboLocation.setCurrentIndex(row)
            self.lblNewLocation.setVisible(True)
            self.comboLocation.setVisible(True)
            self.comboLocation.setModelColumn(1)
        except AttributeError: pass
        except Exception as err:
            print("showComboLocation", err.args)

    @pyqtSlot()
    def loadLocationCombo(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL system_loadLocations({})".format(
                self.contactId if self.contactId is not None else 'NULL'))
            if qry.lastError().type() != 0:
                raise DataError('loadCLocationCombo', qry.lastError().text())
            self.comboLocation.model().setQuery(qry)
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot(FocusCombo)
    def locationFocusLost(self, combo):
        try:
            self.setFocusPolicy(Qt.NoFocus)
            name = combo.currentText()
            if combo.findText(name) > -1:
                return
            else:
                msgBox = QMessageBox(self)
                msgBox.setText("Include:'{}' as a new Location or edit the '{}'".format(
                                               self.comboLocation.currentText(), self.lineFarm.text()))
                insertButton = msgBox.addButton("Insert",QMessageBox.ActionRole)
                editButton = msgBox.addButton("Edit",QMessageBox.ActionRole)
                cancelButton = msgBox.addButton(QMessageBox.Abort)
                ans = msgBox.exec()
                if  msgBox.clickedButton() == insertButton:
                    self.loadNewLocation(name)
                    return
                elif msgBox.clickedButton() == editButton:
                    return
                combo.setFocus()
                combo.setFocusPolicy(Qt.NoFocus)
                combo.setCurrentIndex(0)
        except Exception as err:
            print(err)
        finally:
            self.setFocusPolicy(Qt.StrongFocus)

    def loadNewLocation(self, name):
        try:
            loc = Location(self.db,self.contactId, name=name)
            loc.show()
            self.showComboLocation()
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print("loadNewLocation", err.args)

    def loadData(self):
        try:
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
            if settings.value("owner/locationId"):
                self.locationId = int(settings.value("owner/locationId"))
            if settings.value("owner/contactId"):
                self.contactId = int(settings.value("owner/contactId"))

            self.comboDriver.setCurrentIndex(int(settings.value("access/driver")))
            self.linePath.setText(settings.value("access/path"))
            self.lineAccessName.setText(settings.value("access/fullpath"))

            self.lineEMailAddress.setText(settings.value("email/address"))
            self.lineEMailPassword.setText(settings.value("email/password"))
            self.lineOauth2.setText(settings.value("email/outh2_token"))
        except TypeError as err:
            print(type(err), err.args)

    @property
    def serverAddress(self):
        sett = QSettings(":ext/config.ini", QSettings.IniFormat)
        serverName = sett.value("Server/ServerName")
        serverPort = int(sett.value("Server/ServerPort"))
        address = (serverName, serverPort)
        return address

    @property
    def emailConnectionString(self):
        return (self.lineEMailAddress.text(), self.lineEMailPassword.text())

    @property
    def iconsRelativeDir(self):
        if self.state:
            return self.lineIconsDir.text()

    @property
    def agreementsDir(self):
        if self.state:
            return self.lineAgreementDir.text()

    @property
    def accessConnectionString(self):
        try:
            if self.access_con_string:
                return self.access_con_string
        except Exception as err:
            print("accessConnectionString", err.args)

    @property
    def accessDatabaseName(self):
        try:
            name = os.path.basename(self.lineAccessName.text())
            return name
        except Exception as err:
            print("accessDatabase", type(err), err.args)

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
    def lookForPath(self):
        try:
            obj = self.sender()
            if obj.objectName() == "AgreementPath":
                capt= "Agreements Directory"
                baseDir = self.lineAgreementDir.text()
            elif obj.objectName() == "AccessPath":
                capt = "Access Database Directory"
                baseDir = os.getcwd()
            rootDir = QFileDialog.getExistingDirectory(caption=capt,
                                                       directory=baseDir)
            if obj.objectName() == "AgreementsDir":
                self.lineAgreementDir.setText(rootDir)
            else:
                self.linePath.setText(rootDir)
        except Exception as err:
            print("settings: lookForFile", err.args)

    @pyqtSlot()
    def lookForFile(self):
        try:
            obj = self.sender()
            if obj.objectName() == "AccessFile":
                capt = "Access Database"
                baseDir = self.linePath.text()
                fileType = "Access Database (*.accdb *.mdb)"
            elif obj.objectName() == "IconsFile":
                capt = "Icons Resource File"
                fileType = "Icons Files (*.qrc, *.png)"
                baseDir = self.lineIconsDir.text()
            elif obj.objectName() == "tokenFile":
                capt = "Gmail Outh2 token File"
                fileType = "Gmail token Files (*.json)"
                baseDir = self.lineOauth2.text()
            res = QFileDialog.getOpenFileName(self, caption=capt,directory=baseDir, filter=fileType)
            fileName = res[0]
            if obj.objectName() == "AccessFile":
                self.lineAccessName.setText(fileName)
            elif obj.objectName() == "IconsFile":
                self.lineIconsDir.setText(fileName)
            elif obj.objectName() == "tokenFile":
                self.lineOauth2.setText(fileName)
        except Exception as err:
            print("settings: lookForFile", err.args)

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
                sett.setValue("owner/FarmName", self.comboLocation.currentText())
                sett.setValue("owner/FarmAddress", self.textFarmAddress.toPlainText())

                if self.farmDirty:
                    self.farmChanged()
                sett.setValue("owner/locationId", self.comboLocation.getHiddenData(0))

                sett.setValue("access/driver", self.comboDriver.getHiddenData(0))
                sett.setValue("access/path", self.linePath.text())
                sett.setValue("access/fullpath",self.lineAccessName.text())

                sett.setValue("email/address", self.lineEMailAddress.text())
                sett.setValue("email/password", self.lineEMailPassword.text())
                sett.setValue("email/outh2_token", self.lineOauth2.text())

                if self.ownerDirty:
                    contactId = self.ownerChanged()
                    sett.setValue("owner/contactid", str(contactId) )

            except Exception as err:
                print('saveAndClose',type(err).__name__, err.args)
            self.accept()

    def widgetClose(self):
        try:
            self.db.close()
        except AttributeError:
            pass
        finally:
            self.done(QDialog.Rejected)

    def read_db_config(self,section='mysql', configfile="config.ini"):
        """ Read database configuration file and return a dictionary object
        :param filename: name of the configuration file
        :param section: section of database configuration
        :return: a dictionary of database parameters
        """
        # create parser and read ini configuration file
        parser = ConfigParser()
        if os.getcwd()[-3:] != 'ext':
            configfile = "ext/" + configfile
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
                raise Exception('{0} not found in the {1} file'.format(section, configfile))
        except Exception as err:
            print("SettingsDialog: read_db_config", err.args)
            return conn_string

    @pyqtSlot()
    def connectionTest(self):
        self.lblTestResult.setText("Connecting")
        self.lblTestResult.setStyleSheet("QLabel{background-color: yellow; color: black}")
        self.repaint()
        testMessage = "Failed"
        self.con_string = self.read_db_config()
        #self.con_string = {'host': self.lineDatabaseHost.text(), 'user': self.lineDatabaseUser.text(),
        #                   'database': self.lineDatabaseName.text(), 'password': self.lineDatabasePwd.text()}
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
                if db.lastError().type() == 1:
                    if db.lastError().databaseText() == "Unknown database '{}'". format(self.con_string['database']):

                        res = QMessageBox.question(self, "Database Error",
                                               "Database {} doesn't exist. Do you want to create it?".format(
                                                   self.con_string['database'], QMessageBox.Yes|QMessageBox.No))
                        if res == QMessageBox.Yes:
                            #implements a module to create database open with host, user and password"
                            res = CreateDatabase(self.con_string, self)
                            ans = res.create()
                            if ans:
                                self.lblTestResult.setStyleSheet("QLabel{background-color: black; color: white}")
                                self.lblTestResult.setText('Database created')
                                self.connectionTest()
                            return
                    elif db.lastError().databaseText() == "Can't connect to MySQL server on '{}' (10060)".format(
                        self.con_string['host']):
                        res = QMessageBox.warning(self,"Connection Error", "The server '{}' is not available".format(
                        self.con_string['host']), QMessageBox.Ok)
                        raise DataError("connectionTest", db.lastError().text())

                self.lblTestResult.setStyleSheet("QLabel{background-color: red; color: white}")
                raise TypeError("MySql is closed")
            self.lblTestResult.setText(testMessage)
            self.db = db
            return True, db
        except DataError as err:
            self.lblTestResult.setStyleSheet("QLabel{background-color: red; color: white}")
            self.lblTestResult.setText('Could not create')
            pop = QMessageBox()
            pop.setText("Connection to MYSQL failed")
            pop.setDetailedText(err.source + ',' + err.message)
            pop.show()
            pop.exec_()
            return False, None

        except Exception as err:
            self.lblTestResult.setStyleSheet("QLabel{background-color: red; color: white}")
            self.lblTestResult.setText('Connection failed')
            pop = QMessageBox()
            pop.setText("Connection to MYSQL failed")
            pop.setDetailedText(db.lastError().text())
            pop.show()
            pop.exec_()
            return False, None

    @pyqtSlot()
    def accessTest(self):
        try:
            if not self.lineAccessName.text():
                self.loadData()
            hdb = QSqlDatabase("QODBC")
            con_string ="DRIVER={}; DBQ={};".format("{" + self.comboDriver.currentText() + "}",
                                                      self.lineAccessName.text())
            self.lblAccessTestResult.setStyleSheet("QLabel{background-color: yellow; color: black}")
            self.repaint()
            testMessage = "Failed"
            hdb.setDatabaseName(con_string)
            if hdb.open():
                textMessage = "Succeeded"
                self.state = True
                self.lblAccessTestResult.setStyleSheet("QLabel{background-color: green; color: white}")
                self.accessOk = True
                self.okToSave[2] = self.accessOk
                self.checkBtnEnabled()
                self.access_con_string = con_string
                hdb.close()
            else:
                self.lblAccessTestResult.setStyleSheet("QLabel{background-color: red; color: white}")
                self.lblAccessTestResult.setText(testMessage)
                raise DataError("Cannot open Database {}".format(self.lineDatabaseName),  hdb.lastError().text())
        except DataError as err:
            QMessageBox.critical(self, "Connection Error", "{}; {}".format(err.source, err.message),QMessageBox.Ok)

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
        if False in self.okToSave:
            return
        self.btnOk.setEnabled(True)
        self.btnContinue.setEnabled(True)

    @pyqtSlot()
    def dirtyFarm(self):
        self.farmDirty = True

    @pyqtSlot()
    def dirtyOwner(self):
        self.ownerDirty = True

    @pyqtSlot()
    def ownerLook(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL settings_lookforowner('{}')".format(self.lineOwner.text()))
            if qry.lastError().type() != 0:
                raise DataError("ownerLook", qry.lastError().text())
            if qry.first():
                return qry.value(0), qry.value(1)
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def ownerChanged(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL settings_setowner( {}, '{}', '{}')".format(
                'NULL' if self.contactId is None or not self.isNameEditable else self.contactId,
                self.lineOwner.text(),
                self.textAddress.toPlainText()))
            if qry.lastError().type() != 0:
                raise DataError("ownerChanged", qry.lastError().text())
            if qry.first():
                return qry.value(0)
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def farmChanged(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL settings_setlocation('{}',  '{}', {})".format(
                self.textFarmAddress.toPlainText(),
                self.lineFarm.text(),
                self.comboLocation.getHiddenData(0)))
            if qry.lastError().type() != 0:
                raise DataError("farmChanged", qry.lastError().text())
            if qry.first():
                return qry.value(0)
        except DataError as err:
            print(err.source, err.message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    setting = SettingsDialog()
    setting.show()
    app.exec()


