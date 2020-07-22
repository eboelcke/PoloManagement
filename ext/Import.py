import sys
import os

from PyQt5.QtWidgets import (QGroupBox, QDialog, QHBoxLayout, QVBoxLayout,QFormLayout, QLabel, QProgressDialog,
                             QSpinBox, QApplication,
                             QPushButton, QCheckBox, QDateEdit, QMessageBox, QFrame, QToolButton, QGridLayout)
from PyQt5.QtCore import Qt, QSettings, pyqtSlot, QVariant, QDate, QModelIndex, QThreadPool
from PyQt5.QtSql import QSqlDatabase, QSqlQuery
from PyQt5.QtGui import QIcon
from ext.APM import (DataError,ProgressWidget, Worker, TableViewAndModel,
                     WHERE_CLAUSE_ALL,WHERE_CLAUSE_ONE, Runnable, WorkerThread)
from ext.Settings import SettingsDialog
import time
class ImportHorses(QDialog):
    """Connects to the HorseBase MS Access database and imports all available horses to
    update the horses table"""
    def __init__(self, db, con_string=None, parent=None ):
        super().__init__()
        self.db = db
        if not self.db.isOpen():
            self.db.open()
        self.parent = parent
        try:
            if not self.tempDb.isOpen():
                self.tempDb.open()
        except AttributeError:
            if QSqlDatabase.contains("tempDb"):
                QSqlDatabase.removeDatabase("tempDb")
            self.tempDb = QSqlDatabase.addDatabase("QMYSQL3", "tempDb")
            self.tempDb = QSqlDatabase.addDatabase("QMYSQL3")
            self.tempDb.setHostName(con_string['host'])
            self.tempDb.setUserName(con_string['user'])
            self.tempDb.setPassword(con_string['password'])
            self.tempDb.setDatabaseName(con_string['database'])
            self.tempDb.open()
        self.accessName = None
        self.adb = self.openAccessDb()
        self.setModal(True)
        self.setUi()
        self.setWindowTitle("Import Horse Data from {}".format(self.accessName[:self.accessName.index('.')]))

    def setUi(self):
        self.setMinimumSize(1450, 700)
        groupSex = QGroupBox()
        groupSex.setTitle("Horse Sex")

        self.checkAll = QCheckBox("All Available")
        self.checkAll.stateChanged.connect(self.toggleSexes)
        self.checkFemale = QCheckBox("Female")
        self.checkMale = QCheckBox("Male")
        self.checkGelding = QCheckBox("Gelding")
        sexLayout = QFormLayout()
        sexLayout.addRow(self.checkAll, self.checkGelding)
        sexLayout.addRow(self.checkFemale, self.checkMale)
        groupSex.setLayout(sexLayout)

        groupCategories = QGroupBox()
        groupCategories.setTitle("Categories")
        self.checkCatAll = QCheckBox("All Available")
        self.checkCatAll.stateChanged.connect(self.toggleCategories)
        self.checkUnbroken = QCheckBox("Unbroken")
        self.checkGreenBroke = QCheckBox("Green Broke")
        self.checkPlayer = QCheckBox("Polo Pony")

        groupCategoriesLayout = QFormLayout()
        groupCategories.setLayout(groupCategoriesLayout)
        groupCategoriesLayout.addRow(self.checkCatAll, self.checkUnbroken)
        groupCategoriesLayout.addRow(self.checkGreenBroke, self.checkPlayer)

        groupAge = QGroupBox()
        groupAge.setTitle("Age Limits")

        lblFrom = QLabel("Minimum Age (Months)")
        self.spinFrom = QSpinBox()
        self.spinFrom.setRange(24, 120)
        self.spinFrom.setMaximumWidth(50)
        self.spinFrom.setValue(24)
        lblTo = QLabel("Maximum Age (Months)")
        self.spinTo = QSpinBox()
        self.spinTo.setRange(24,120)
        self.spinTo.setMaximumWidth(50)
        self.spinTo.setValue(60)

        lblDate = QLabel("Import Date")
        self.importDate = QDateEdit()
        self.importDate.setCalendarPopup(True)
        self.importDate.setDate(QDate.currentDate())
        self.importDate.setMaximumWidth(120)
        self.createTemporaryTables()
        self.importHorses()
        qry, qrySelected= self.loadAvailableHorses()
        colorDict = {}
        colDict = {
            0:("id", True, True, False, None),
            1:("HBid", True, True, False, None),
            2:("Horse", False, False, False, None),
            3:("RP",False, True, False, None),
            4:("DOB", False, True, False, None),
            5:("Sex", False, True, True, None),
            6:("Coat", False, True, False, None),
            7:("Bre", False, True, True, None),
            8:("Bro", False, True, True, None),
            9:("Ply", False, True, True, None),
            10:("IsBrk", True, True, False, None),
            11:("IsBok", True, True, False, None),
            12:("IsPly", True, True, False, None),
            13:("sxid", True, True, False, None),
            14:("Cotid", True, True, False, None),
            15:("Father", True, True, False, None),
            16:("Mother", True, True, False, None),
            17:("HBlocID", True, True, False, None),
            18: ("locid", True, True, False, None),
            19:("InDate", True, True, False, None),
            20:("Selected", True, True, False, None)}

        self.tableImported = TableViewAndModel(colDict=colDict, colorDict=colorDict,size=(100.100), qry=qry)
        self.tableImported.setObjectName("tableImported")
        self.tableImported.setMouseTracking(True)
        self.tableImported.entered.connect(self.setArrows)
        self.tableImported.viewportEntered.connect(self.setArrows)
        self.tableImported.doubleClicked.connect(self.includeHorse)

        self.tableSelected = TableViewAndModel(colDict, {}, (100, 100), qrySelected)
        self.tableSelected.setMouseTracking(True)
        self.tableSelected.entered.connect(self.setArrows)
        self.tableSelected.viewportEntered.connect(self.setArrows)
        self.tableSelected.doubleClicked.connect(self.excludeHorse)

        self.toolRight = QToolButton()
        self.toolRight.setIcon(QIcon(":Icons8/arrows/right-arrow.png"))
        self.toolRight.setMinimumSize(100, 30)
        self.toolRight.clicked.connect(lambda: self.includeHorse(WHERE_CLAUSE_ONE))
        self.toolRight.setToolTip("Load selected Horse")
        self.toolRight.setEnabled(False)

        self.toolAllRight = QToolButton()
        self.toolAllRight.setIcon(QIcon(":Icons8/arrows/double-right.png"))
        self.toolAllRight.setMinimumSize(100, 30)
        self.toolAllRight.clicked.connect(lambda: self.includeHorse(WHERE_CLAUSE_ALL))
        self.toolAllRight.setToolTip("Load All Horses")
        self.toolAllRight.setEnabled(False)

        self.toolLeft = QToolButton()
        self.toolLeft.setIcon(QIcon(":Icons8/arrows/left-arrow.png"))
        self.toolLeft.setMinimumSize(100, 30)
        self.toolLeft.clicked.connect(lambda: self.excludeHorse(WHERE_CLAUSE_ONE))
        self.toolLeft.setEnabled(False)

        self.toolAllLeft = QToolButton()
        self.toolAllLeft.setIcon(QIcon(":Icons8/arrows/double-left.png"))
        self.toolAllLeft.setMinimumSize(100, 30)
        self.toolAllLeft.clicked.connect(lambda: self.excludeHorse(WHERE_CLAUSE_ALL))
        self.toolAllLeft.setEnabled(False)

        lblAvailable = QLabel("Available Horses for Import")
        lblSelected = QLabel("Selected Horses for Import")


        toolsFrame = QFrame()
        toolsFrame.setMaximumWidth(150)
        toolsFrame.setMaximumHeight(150)

        toolsLayout = QVBoxLayout()
        toolsLayout.addWidget(self.toolRight)
        toolsLayout.addWidget(self.toolAllRight)
        toolsLayout.addWidget(self.toolLeft)
        toolsLayout.addWidget(self.toolAllLeft)
        toolsFrame.setLayout(toolsLayout)

        centerLayout = QGridLayout()
        centerLayout.addWidget(lblAvailable, 0, 0)
        centerLayout.addWidget(lblSelected, 0, 2)
        centerLayout.addWidget(toolsFrame, 1, 1)
        centerLayout.addWidget(self.tableImported, 1, 0)
        centerLayout.addWidget(self.tableSelected, 1, 2)

        groupAgeLayout = QFormLayout()
        #groupAgeLayout.addRow(lblDate, self.importDate)
        groupAgeLayout.addRow(lblFrom, self.spinFrom)
        groupAgeLayout.addRow(lblTo, self.spinTo)
        groupAge.setLayout(groupAgeLayout)

        optionLayout = QHBoxLayout()
        optionLayout.addWidget(groupSex)
        optionLayout.addWidget(groupCategories)
        optionLayout.addWidget(groupAge)

        toolImport = QPushButton(QIcon(":/Icons8/arrows/import.png"), "Import")
        toolImport.clicked.connect(self.importHorseList)
        toolImport.setMaximumWidth(100)

        self.btnSave = QPushButton("Save")
        self.btnSave.setMaximumWidth(80)
        self.btnSave.setEnabled(False)
        self.btnSave.clicked.connect(self.saveAndClose)

        btnClose = QPushButton("Cancel")
        btnClose.setMaximumWidth(80)
        btnClose.clicked.connect(self.widgetClose)

        importLayout = QHBoxLayout()
        importLayout.addWidget(lblDate, Qt.AlignRight)
        importLayout.addWidget(self.importDate,Qt.AlignRight)
        importLayout.addWidget(toolImport,Qt.AlignRight)
        importLayout.addSpacing(1000)
        #importLayout.addWidget(btnRefresh)
        importLayout.addWidget(btnClose)
        importLayout.addWidget(self.btnSave)

        vLayout = QVBoxLayout()
        vLayout.addLayout(optionLayout)
        vLayout.addLayout(centerLayout)
        vLayout.addLayout(importLayout)

        self.setLayout(vLayout)

    @pyqtSlot()
    def setArrows(self):
        action = True if self.sender().objectName() == "tableImported" else False
        if self.sender().model().query().size() > 0:
            self.toolRight.setEnabled(action)
            self.toolAllRight.setEnabled(action)
            self.toolLeft.setEnabled(not action)
            self.toolAllLeft.setEnabled(not action)

    def openAccessDb(self):
        try:
            sett = SettingsDialog()
            self.accessName = sett.accessDatabaseName
            if QSqlDatabase.contains("MSAccess"):
                adb = QSqlDatabase.database("MSAccess", True)
                return adb

            sett.loadData()
            adb = QSqlDatabase.addDatabase("QODBC","MSAccess")
            sett.accessTest()
            con_string = sett.accessConnectionString

            adb.setDatabaseName(con_string)
            if adb.open():
                self.adb = adb
                return adb
            raise DataError("openAccessDb", adb.lastError().text())
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def importHorses(self):
        try:
            qryImport = QSqlQuery(self.adb)
            import_str = """SELECT id, nombre, rp, nacio, sexoid, colorid,
             esdomable, esdomado, esjugador, padre, madre, ubicaciónid
             FROM qryExportReady 
             WHERE edad BETWEEN ? and ?"""
            where_str = ''
            optSex = [self.checkAll.isChecked(), self.checkFemale.isChecked(),
                  self.checkMale.isChecked(), self.checkGelding.isChecked()]
            if not optSex[0] and True in optSex:
                if optSex[1]:
                    where_str += " AND (sexoid = 2"
                if optSex[2]:
                    where_str += " AND (sexoid = 1" if len(where_str) == 0 else " OR sexoid = 1"
                if optSex[3]:
                    where_str += " AND (sexoid = 3" if len(where_str) == 0 else " OR sexoid = 3"
                where_str += ")"
            where_cat = ''
            optCat = [self.checkCatAll.isChecked(), self.checkUnbroken.isChecked(),
                      self.checkGreenBroke.isChecked(), self.checkPlayer.isChecked()]
            if not optCat[0] and True in optCat:
                if optCat[1]:
                    where_cat += " AND esdomable "
                if optCat[2]:
                    where_cat += " AND (esdomado AND NOT esjugador)" if len(where_cat) == 0 else \
                        " OR (esdomado AND NOT esjugador)"
                if optCat[3]:
                    where_cat += " AND esjugador" if len(where_cat) == 0 else " OR esjugador"
            qryImport.prepare(import_str + where_str + where_cat)
            qryImport.addBindValue(QVariant(self.spinFrom.value()))
            qryImport.addBindValue(QVariant(self.spinTo.value()))
            qryImport.exec()
            if qryImport.lastError().type() !=0:
                raise DataError("importHorses", qryImport.lastError().text())
            if not qryImport.first():
                raise DataError("ImportHorses", "There are not horses to be imported")
            qryImport.seek(-1)
            rows = 0
            while qryImport.next():
                rows += 1
            proDiag = QProgressDialog("Loading Horses", "Abort", 0, rows, self)
            proDiag.setWindowModality(Qt.WindowModal)
            #proDiag.setWindowTitle("Import Contacts")
            proDiag.setLabelText("Import Horses")
            proDiag.setMinimumWidth(500)
            qryImport.seek(-1)
            qry = QSqlQuery(self.db)
            i = 0
            while qryImport.next():
                qry.prepare("CALL importhorses_loaddata(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")
                qry.addBindValue(QVariant(qryImport.value(0)))  # accessid
                qry.addBindValue(QVariant(qryImport.value(1))) # name
                qry.addBindValue(QVariant(qryImport.value(2))) #rp
                qry.addBindValue(QVariant(qryImport.value(3).toString("yyyy-MM-dd"))) #BirthDate
                qry.addBindValue(QVariant(qryImport.value(4))) #sexid
                qry.addBindValue(QVariant(qryImport.value(5))) #coatid
                qry.addBindValue(QVariant(qryImport.value(6))) #isbreakable
                qry.addBindValue(QVariant(qryImport.value(7))) #isBroke
                qry.addBindValue(QVariant(qryImport.value(8))) #isPlayer
                qry.addBindValue(QVariant(qryImport.value(9))) #Father
                qry.addBindValue(QVariant(qryImport.value(10))) #Mother
                qry.addBindValue(QVariant(qryImport.value(11))) #UbicacionID
                qry.addBindValue(QVariant(self.importDate.date().toString("yyyy-MM-dd"))) #ImportDate
                qry.exec()
                if qry.lastError().type() != 0:
                    raise DataError("importHorses", qry.lastError().text())
                if qry.first():
                    print(qry.value(0))
                    raise DataError("importHorses", qry.value(0))
                qry.clear()
                i += 1
                proDiag.setValue(i)
                if proDiag.wasCanceled():
                    break
        except DataError as err:
            print(err.source, err.message)
            QMessageBox.warning(self, err.source, err.message, QMessageBox.Ok)
        finally:
            if not self.tempDb.isOpen():
                self.tempDb.open()

    @pyqtSlot()
    def importHorseList(self):
        try:
            self.createTemporaryTables()
            self.importHorses()
            qry, qrySelected = self.loadAvailableHorses()
            self.tableImported.model().setQuery(qry)
            self.tableSelected.model().setQuery(qrySelected)
        except Exception as err:
            print("importHorseList", type(err), err.args)

    def refreshTables(self):
        try:
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL importhorses_getimportedhorses ()")
            if qry.lastError().type() !=0:
                raise DataError("refreshTables - import", qry.lastError().text())
            self.tableImported.model().setQuery(qry)
            qryExport = QSqlQuery(self.tempDb)
            qryExport.exec("CALL importhorses_getselectedhorses ()")
            if qryExport.lastError().type() !=0:
                raise DataError("refreshTables - import", qryExport.lastError().text())
            self.tableSelected.model().setQuery(qryExport)
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print("refreshTables", err.args)

    @pyqtSlot()
    def loadAvailableHorses(self):
        try:
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL importHorses_loadAvailableHorses()")
            if qry.lastError().type() !=0:
                raise DataError("loadAvailableHorses", qry.lastError().text())
            if not qry.first() and self.isVisible():
                raise DataError("Avalable Horses","There are not available horses ")
            qrySelected = QSqlQuery(self.tempDb)
            qrySelected.exec("CALL importhorses_getselectedhorses()")
            if qrySelected.lastError().type() !=0:
                raise DataError("loadavailableHorses-selected", qrySelected.lastError().text())
            return qry, qrySelected
        except DataError as err:
            QMessageBox.warning(self, err.source, err.message, QMessageBox.Ok)

    @pyqtSlot()
    def toggleSexes(self):
        opt = self.checkAll.isChecked()
        self.checkFemale.setChecked(opt)
        self.checkMale.setChecked(opt)
        self.checkGelding.setChecked(opt)

    @pyqtSlot()
    def toggleCategories(self):
        if self.checkCatAll.isChecked():
            self.checkUnbroken.setChecked(True)
            self.checkGreenBroke.setChecked(True)
            self.checkPlayer.setChecked(True)

    @pyqtSlot()
    def enableSave(self):
        if self.tableSelected.model().rowCount() > 0:
            self.btnSave.setEnabled(True)
        else:
            self.btnSave.setEnabled(False)

    def createTemporaryTables(self):
        try:
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL importhorses_createtemporary()")
            if qry.lastError().        type() != 0:
                raise DataError("createTemporaryTables", qry.lastError().text())
            if qry.first():
                raise DataError("createTemporaryTables", qry.value(0) + ' ' + qry.value(1))
        except DataError as err:
            print(err.source, err.message)


    @pyqtSlot()
    def includeHorse(self, clause=WHERE_CLAUSE_ONE):
        try:
            row = self.tableImported.currentIndex().row()
            self.tableImported.model().query().seek(row)
            self.record =  self.tableImported.model().query().record()
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL importhorses_includeHorse({})".format(
                self.record.value(0) if clause == WHERE_CLAUSE_ONE else 'NULL'))
            if qry.lastError().type() != 0:
                raise DataError("includehorse", qry.lastError().text())
            if qry.first():
                raise DataError("includeHorse", "Error {}".format(qry.value(0)))
            self.refreshTables()
            self.enableSave()
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def excludeHorse(self, clause=WHERE_CLAUSE_ONE):
        try:
            row = self.tableSelected.currentIndex().row()
            self.tableSelected.model().query().seek(row)
            self.record =  self.tableSelected.model().query().record()
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL importhorses_excludeHorse({})".format(
                self.record.value(0) if clause == WHERE_CLAUSE_ONE else 'NULL'))
            if qry.lastError().type() != 0:
                raise DataError("excludehorse", qry.lastError().text())
            if qry.first():
                raise DataError("includeHorse", "Error {}".format(qry.value(0)))
            self.refreshTables()
            self.enableSave()
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def saveAndClose(self):
        try:
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL importHorses_save()")
            if qry.lastError().type() !=0:
                raise DataError("loadAvailableHorses", qry.lastError().text())
            if qry.first():
                raise DataError("saveAndClose", qry.value(0))
            self.widgetClose()
        except DataError as err:
            QMessageBox.warning(self, err.source, err.message, QMessageBox.Ok)
        except Exception as err:
            print("saveAndClose", type(err), err.args)

    @pyqtSlot()
    def widgetClose(self):
        if self.tempDb.isOpen():
            self.tempDb.close()
        if self.adb.isOpen():
            self.adb.close()
        self.done(QDialog.Rejected)

class ImportContacts(QDialog):
    """Connects to the HorseBase MS Access database and imports all available contacts to
       update the contacts table"""

    def __init__(self, db, con_string=None, parent=None):
        super().__init__()
        self.db = db
        if not self.db.isOpen():
            self.db.open()
        self.parent = parent
        try:
            if not self.tempDb.isOpen():
                self.tempDb.open()
        except AttributeError:
            if QSqlDatabase.contains("tempDb"):
                QSqlDatabase.removeDatabase("tempDb")
            self.tempDb = QSqlDatabase.addDatabase("QMYSQL3", "tempDb")
            #self.tempDb = QSqlDatabase.addDatabase("QMYSQL3")
            self.tempDb.setHostName(con_string['host'])
            self.tempDb.setUserName(con_string['user'])
            self.tempDb.setPassword(con_string['password'])
            self.tempDb.setDatabaseName(con_string['database'])
            self.tempDb.open()
        self.accessName = None
        self.adb = self.openAccessDb()
        self.setModal(True)
        self.setUi()
        self.setWindowTitle("Import Contact Data from {}".format(self.accessName[:self.accessName.index('.')]))

    def setUi(self):
        self.setMinimumSize(1450, 700)
        groupPlayer = QGroupBox()
        groupPlayer.setTitle("Polo")

        self.checkAllPlayer = QCheckBox("All Available")
        self.checkAllPlayer.stateChanged.connect(self.togglePlayer)
        self.checkPlayer = QCheckBox("Player")
        self.checkPlayAndSale = QCheckBox("Train And Sale Operation")
        #self.checkGelding = QCheckBox("Gelding")
        playLayout = QFormLayout()
        playLayout.addRow(self.checkAllPlayer)
        playLayout.addRow(self.checkPlayer, self.checkPlayAndSale)
        groupPlayer.setLayout(playLayout)

        groupBreaking = QGroupBox()
        groupBreaking.setTitle("Breaking")
        self.checkAllBreaking = QCheckBox("All Available")
        self.checkAllBreaking.stateChanged.connect(self.toggleBreaking)
        self.checkBuster = QCheckBox("Buster")
        self.checkBreaking = QCheckBox("Breaking Operation")
        self.checkBreaking.setStatusTip("Horse breaking business")
        #self.checkPlayer = QCheckBox("Polo Pony")

        groupBreakingLayout = QFormLayout()
        groupBreaking.setLayout(groupBreakingLayout)
        groupBreakingLayout.addRow(self.checkAllBreaking)
        groupBreakingLayout.addRow(self.checkBuster, self.checkBreaking)

        groupServices = QGroupBox()
        groupServices.setTitle("Services")

        self.checkAllService = QCheckBox("All Services")
        self.checkEmployee = QCheckBox("Employee")
        self.checkVet = QCheckBox("Veterinay")
        self.checkDriver = QCheckBox("Driver")

        serviceLayout = QFormLayout()
        serviceLayout.addRow(self.checkAllService, self.checkEmployee)
        serviceLayout.addRow(self.checkVet, self.checkDriver)

        groupServices.setLayout(serviceLayout)

        groupMarketing = QGroupBox()
        groupMarketing.setTitle("Marketing")

        self.checkAllMarket = QCheckBox("All Marketing")
        self.checkAllMarket.clicked.connect(self.toggleMarket)
        self.checkBuyer = QCheckBox("Horse Buyer")
        self.checkSeller = QCheckBox("Horse Seller")

        marketLayout = QFormLayout()
        marketLayout.addRow(self.checkAllMarket)
        marketLayout.addRow(self.checkBuyer, self.checkSeller)

        groupMarketing.setLayout(marketLayout)

        lblDate = QLabel("Import Date")
        self.importDate = QDateEdit()
        self.importDate.setCalendarPopup(True)
        self.importDate.setDate(QDate.currentDate())
        self.importDate.setMaximumWidth(120)
        self.createTemporaryTables()
        self.importContacts()
        qry, qrySelected = self.loadAvailableContacts()
        colorDict = {}
        colDict = {
            0: ("id", True, True, False, None),
            1: ("HBid", True, True, False, None),
            2: ("Name", False, False, False, None),
            3: ("email", True, True, False, None),
            4: ("Tel", True, True, False, None),
            5: ("Address", True, True, True, None),
            6: ("Vet", False, True, True, None),
            7: ("Bu", False, True, True, None),
            8: ("Ply", False, True, True, None),
            9: ("E", False, True, True, None),
            10: ("D", False, True, True, None),
            11: ("By", False, True, True, None),
            12: ("S", False, True, True, None),
            13: ("T", False, True, True, None),
            14: ("BB", False, True, True, None),
            15: ("Selected", True, True, False, None)}

        self.tableImported = TableViewAndModel(colDict=colDict, colorDict=colorDict, size=(100.100), qry=qry)
        self.tableImported.setObjectName("tableImported")
        self.tableImported.setMouseTracking(True)
        self.tableImported.entered.connect(self.setArrows)
        self.tableImported.viewportEntered.connect(self.setArrows)
        self.tableImported.doubleClicked.connect(self.includeContact)

        self.tableSelected = TableViewAndModel(colDict, {}, (100, 100), qrySelected)
        self.tableSelected.setMouseTracking(True)
        self.tableSelected.entered.connect(self.setArrows)
        self.tableSelected.viewportEntered.connect(self.setArrows)
        self.tableSelected.doubleClicked.connect(self.excludeContact)

        self.toolRight = QToolButton()
        self.toolRight.setIcon(QIcon(":Icons8/arrows/right-arrow.png"))
        self.toolRight.setMinimumSize(100, 30)
        self.toolRight.clicked.connect(lambda: self.includeContact(WHERE_CLAUSE_ONE))
        self.toolRight.setToolTip("Load selected Horse")
        self.toolRight.setEnabled(False)

        self.toolAllRight = QToolButton()
        self.toolAllRight.setIcon(QIcon(":Icons8/arrows/double-right.png"))
        self.toolAllRight.setMinimumSize(100, 30)
        self.toolAllRight.clicked.connect(lambda: self.includeContact(WHERE_CLAUSE_ALL))
        self.toolAllRight.setToolTip("Load All Horses")
        self.toolAllRight.setEnabled(False)

        self.toolLeft = QToolButton()
        self.toolLeft.setIcon(QIcon(":Icons8/arrows/left-arrow.png"))
        self.toolLeft.setMinimumSize(100, 30)
        self.toolLeft.clicked.connect(lambda: self.excludeContact(WHERE_CLAUSE_ONE))
        self.toolLeft.setEnabled(False)

        self.toolAllLeft = QToolButton()
        self.toolAllLeft.setIcon(QIcon(":Icons8/arrows/double-left.png"))
        self.toolAllLeft.setMinimumSize(100, 30)
        self.toolAllLeft.clicked.connect(lambda: self.excludeContact(WHERE_CLAUSE_ALL))
        self.toolAllLeft.setEnabled(False)

        lblAvailable = QLabel("Available Horses for Import")
        lblSelected = QLabel("Selected Horses for Import")
        lblCodes = QLabel("Vet:Veterinary, Bu:Buster, Ply:Player, E:Employee, D:Driver,"
                          " By:Buyer, S:Seller, BB:Breaking Business, T:Training Selling")

        toolsFrame = QFrame()
        toolsFrame.setMaximumWidth(150)
        toolsFrame.setMaximumHeight(150)

        toolsLayout = QVBoxLayout()
        toolsLayout.addWidget(self.toolRight)
        toolsLayout.addWidget(self.toolAllRight)
        toolsLayout.addWidget(self.toolLeft)
        toolsLayout.addWidget(self.toolAllLeft)
        toolsFrame.setLayout(toolsLayout)

        centerLayout = QGridLayout()
        centerLayout.addWidget(lblAvailable, 0, 0)
        centerLayout.addWidget(lblSelected, 0, 2)
        centerLayout.addWidget(toolsFrame, 1, 1)
        centerLayout.addWidget(self.tableImported, 1, 0)
        centerLayout.addWidget(self.tableSelected, 1, 2)

        optionLayout = QHBoxLayout()
        optionLayout.addWidget(groupPlayer)
        optionLayout.addWidget(groupBreaking)
        optionLayout.addWidget(groupMarketing)
        optionLayout.addWidget(groupServices)

        toolImport = QPushButton(QIcon(":/Icons8/arrows/import.png"), "Import")
        toolImport.clicked.connect(self.importContactList)
        toolImport.setMaximumWidth(100)

        self.btnSave = QPushButton("Save")
        self.btnSave.setMaximumWidth(80)
        self.btnSave.setEnabled(False)
        self.btnSave.clicked.connect(self.saveAndClose)

        btnClose = QPushButton("Cancel")
        btnClose.setMaximumWidth(80)
        btnClose.clicked.connect(self.widgetClose)

        importLayout = QHBoxLayout()
        importLayout.addWidget(lblDate, Qt.AlignRight)
        importLayout.addWidget(self.importDate, Qt.AlignRight)
        importLayout.addWidget(toolImport, Qt.AlignRight)
        importLayout.addSpacing(1000)
        # importLayout.addWidget(btnRefresh)
        importLayout.addWidget(btnClose)
        importLayout.addWidget(self.btnSave)

        vLayout = QVBoxLayout()
        vLayout.addLayout(optionLayout)
        vLayout.addLayout(centerLayout)
        vLayout.addWidget(lblCodes)
        vLayout.addLayout(importLayout)

        self.setLayout(vLayout)

    def startThread(self, data, pd):
        self.runnable = Runnable(data, pd)
        QThreadPool.globalInstance().start(self.runnable)

    @pyqtSlot(int)
    def progressThread(self, count):
        self.progress.setValue(count)

    def showProgress(self):
        self.progress = QProgressDialog("Work in progress...", None, 0, 100, self)
        self.progress.setWindowTitle("Opening MSAccess Database ")
        self.progress.setWindowModality(Qt.WindowModal)
        self.progress.setMinimumWidth(500)
        self.progress.setValue(0)
        self.progress.setValue(50)
        self.progress.setValue(1)
        self.progress.show()

    @pyqtSlot()
    def setArrows(self):
        action = True if self.sender().objectName() == "tableImported" else False
        if self.sender().model().query().size() > 0:
            self.toolRight.setEnabled(action)
            self.toolAllRight.setEnabled(action)
            self.toolLeft.setEnabled(not action)
            self.toolAllLeft.setEnabled(not action)

    def openAccessDb(self):
        try:
            #elf.showProgress()
            #thr = WorkerThread(self.progress)
            #thr.started.connect(self.showProgress)

            sett = SettingsDialog()
            self.accessName = sett.accessDatabaseName
            if QSqlDatabase.contains("MSAccess"):
                adb = QSqlDatabase.database("MSAccess", True)
                return adb

            sett.loadData()
            adb = QSqlDatabase.addDatabase("QODBC", "MSAccess")
            sett.accessTest()
            con_string = sett.accessConnectionString
            adb.setDatabaseName(con_string)
            if adb.open():
                self.adb = adb
                return adb
            raise DataError("openAccessDb", adb.lastError().text())
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def importContacts(self):
        try:
            qryImport = QSqlQuery(self.adb)
            import_str = """SELECT id, name, email, Tel, Address, esveterinario,
                esdomador, espolista, esempleado, esdriver, escomprador, esvendedor,
                esjugadorvendedor, esdomaservice
                FROM qryExportContacts 
                """
            where_str = ''
            opt_str = [self.checkPlayer.isChecked(), self.checkPlayAndSale.isChecked(), self.checkBuster.isChecked(),
                      self.checkBreaking.isChecked(), self.checkBuyer.isChecked(), self.checkSeller.isChecked(),
                      self.checkVet.isChecked(), self.checkDriver.isChecked(), self.checkEmployee.isChecked()]
            if True in opt_str:
                if opt_str[0]:
                    where_str += "WHERE espolista " if len(where_str) == 0 else " OR espolista "
                if opt_str[1]:
                    where_str += "WHERE esjugadorvendedor " if len(where_str) == 0 else " OR esjugadorvendedor "
                if opt_str[2]:
                    where_str += "WHERE esdomador " if len(where_str) == 0 else " OR esdomador "
                if opt_str[3]:
                    where_str += "WHERE esdomaservice " if len(where_str) == 0 else " OR esdomaservice "
                if opt_str[4]:
                    where_str += "WHERE escomprador " if len(where_str) == 0 else " OR escomprador "
                if opt_str[5]:
                    where_str += "WHERE esvendedor " if len(where_str) == 0 else " OR esvendedor "
                if opt_str[6]:
                    where_str += "WHERE esveterinario " if len(where_str) == 0 else " OR esveterinario "
                if opt_str[7]:
                    where_str += "WHERE esdriver " if len(where_str) == 0 else " OR esdriver "
                if opt_str[8]:
                    where_str += "WHERE esempleado " if len(where_str) == 0 else " OR esempleado "
                where_str += ";"

            qryImport.prepare(import_str + where_str )
            qryImport.exec()
            if qryImport.lastError().type() != 0:
                raise DataError("importContacts - access", qryImport.lastError().text())
            if not qryImport.first():
                raise DataError("importContacts - access", "There are no contacts to import")
            qryImport.seek(-1)
            rows = 0
            while qryImport.next():
                rows += 1
            qryImport.seek(-1)
            proDiag = QProgressDialog("Loading Contacts",None, 0, rows,self)
            proDiag.setWindowModality(Qt.WindowModal)
            proDiag.setWindowTitle("Importing Contacts")
            proDiag.setMinimumWidth(500)
            qryImport.seek(-1)
            qry = QSqlQuery(self.db)
            i = 0
            while qryImport.next():
                qry.prepare("CALL importcontacts_loaddata(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")
                qry.addBindValue(QVariant(qryImport.value(0)))  # accessid
                qry.addBindValue(QVariant(qryImport.value(1)))  # name
                qry.addBindValue(QVariant(qryImport.value(2)))  # email
                qry.addBindValue(QVariant(qryImport.value(3)))  # tel
                qry.addBindValue(QVariant(qryImport.value(4)))  # address
                qry.addBindValue(QVariant(qryImport.value(5)))  # vet
                qry.addBindValue(QVariant(qryImport.value(6)))  # buster
                qry.addBindValue(QVariant(qryImport.value(7)))  # player
                qry.addBindValue(QVariant(qryImport.value(8)))  # employee
                qry.addBindValue(QVariant(qryImport.value(9)))  # driver
                qry.addBindValue(QVariant(qryImport.value(10)))  # buyer
                qry.addBindValue(QVariant(qryImport.value(11)))  # seller
                qry.addBindValue(QVariant(qryImport.value(12)))  # playerseller
                qry.addBindValue(QVariant(qryImport.value(13))) # domaservice
                qry.exec()
                qry.clear()
                i += 1
                proDiag.setValue(i)
                if proDiag.wasCanceled():
                    break
        except DataError as err:
            print(err.source, err.message)
            QMessageBox.warning(self, err.source, err.message, QMessageBox.Ok)
        finally:
            if not self.tempDb.isOpen():
                self.tempDb.open()

    @pyqtSlot()
    def importContactList(self):
        try:
            self.createTemporaryTables()
            self.importContacts()
            qry, qrySelected = self.loadAvailableContacts()
            self.tableImported.model().setQuery(qry)
            self.tableSelected.model().setQuery(qrySelected)
        except Exception as err:
            print("importContactList", type(err), err.args)

    def refreshTables(self):
        try:
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL importcontacts_getimportedcontacts ()")
            if qry.lastError().type() != 0:
                raise DataError("refreshTables - include", qry.lastError().text())
            self.tableImported.model().setQuery(qry)
            qryExport = QSqlQuery(self.tempDb)
            qryExport.exec("CALL importcontacts_getselectedcontacts ()")
            if qryExport.lastError().type() != 0:
                raise DataError("refreshTables - exclude", qryExport.lastError().text())
            self.tableSelected.model().setQuery(qryExport)
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print("refreshTables", err.args)

    @pyqtSlot()
    def loadAvailableContacts(self):
        try:
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL importcontacts_loadAvailablecontacts()")
            if qry.lastError().type() != 0:
                raise DataError("loadAvailablecontacts", qry.lastError().text())
            if not qry.first() and self.isVisible():
                raise DataError("Available Horses", "There are not available contacts ")
            qrySelected = QSqlQuery(self.tempDb)
            qrySelected.exec("CALL importcontacts_getselectedcontacts()")
            if qrySelected.lastError().type() != 0:
                raise DataError("loadavailableContacts-selected", qrySelected.lastError().text())
            return qry, qrySelected
        except DataError as err:
            QMessageBox.warning(self, err.source, err.message, QMessageBox.Ok)

    @pyqtSlot()
    def togglePlayer(self):
        opt = self.checkAllPlayer.isChecked()
        self.checkPlayer.setChecked(opt)
        self.checkPlayAndSale.setChecked(opt)
        #self.checkGelding.setChecked(opt)

    @pyqtSlot()
    def toggleBreaking(self):
        if self.checkAllBreaking.isChecked():
            self.checkBuster.setChecked(True)
            self.checkBreaking.setChecked(True)
            #self.checkPlayer.setChecked(True)

    @pyqtSlot()
    def toggleServices(self):
        if self.checkAllService.isChecked():
            self.checkEmployee.setChecked(True)
            self.checkVet.setChecked(True)
            self.checkDriver.setChecked(True)

    @pyqtSlot()
    def toggleMarket(self):
        if self.checkAllMarket.isChecked():
            self.checkBuyer.setChecked(True)
            self.checkSeller.setChecked(True)

    @pyqtSlot()
    def enableSave(self):
        if self.tableSelected.model().rowCount() > 0:
            self.btnSave.setEnabled(True)
        else:
            self.btnSave.setEnabled(False)

    def createTemporaryTables(self):
        try:
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL importcontacts_createtemporary()")
            if qry.lastError().type() != 0:
                raise DataError("createTemporaryTables", qry.lastError().text())
            if qry.first():
                raise DataError("createTemporaryTables", qry.value(0) + ' ' + qry.value(1))
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def includeContact(self, clause=WHERE_CLAUSE_ONE):
        try:
            row = self.tableImported.currentIndex().row()
            self.tableImported.model().query().seek(row)
            self.record = self.tableImported.model().query().record()
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL importcontacts_includeContact({})".format(
                self.record.value(0) if clause == WHERE_CLAUSE_ONE else 'NULL'))
            if qry.lastError().type() != 0:
                raise DataError("includehorse", qry.lastError().text())
            if qry.first():
                raise DataError("importContact", "Error {}".format(qry.value(0)))
            self.refreshTables()
            self.enableSave()
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def excludeContact(self, clause=WHERE_CLAUSE_ONE):
        try:
            row = self.tableSelected.currentIndex().row()
            self.tableSelected.model().query().seek(row)
            self.record = self.tableSelected.model().query().record()
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL importcontacts_excludeContact({})".format(
                self.record.value(0) if clause == WHERE_CLAUSE_ONE else 'NULL'))
            if qry.lastError().type() != 0:
                raise DataError("excludehorse", qry.lastError().text())
            if qry.first():
                raise DataError("importContact", "Error {}".format(qry.value(0)))
            self.refreshTables()
            self.enableSave()
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def saveAndClose(self):
        try:
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL importcontacts_save('{}')".format(self.importDate.date().toString("yyyy-MM-dd")))
            if qry.lastError().type() != 0:
                raise DataError("saveAndClose", qry.lastError().text())
            if qry.first():
                raise DataError("saveAndClose", qry.value(0))
            self.widgetClose()
        except DataError as err:
            QMessageBox.warning(self, err.source, err.message, QMessageBox.Ok)
        except Exception as err:
            print("saveAndClose", type(err), err.args)

    @pyqtSlot()
    def widgetClose(self):
        if self.tempDb.isOpen():
            self.tempDb.close()
        if self.adb.isOpen():
            self.adb.close()
        self.done(QDialog.Rejected)

class ImportLocations(QDialog):
    """Connects to the HorseBase MS Access database and imports all available contacts to
          update the locations table"""

    def __init__(self, db, con_string=None, parent=None):
        super().__init__()
        self.db = db
        if not self.db.isOpen():
            self.db.open()
        self.parent = parent
        try:
            if not self.tempDb.isOpen():
                self.tempDb.open()
        except AttributeError:
            if QSqlDatabase.contains("tempDb"):
                QSqlDatabase.removeDatabase("tempDb")
            self.tempDb = QSqlDatabase.addDatabase("QMYSQL3", "tempDb")
            # self.tempDb = QSqlDatabase.addDatabase("QMYSQL3")
            self.tempDb.setHostName(con_string['host'])
            self.tempDb.setUserName(con_string['user'])
            self.tempDb.setPassword(con_string['password'])
            self.tempDb.setDatabaseName(con_string['database'])
            self.tempDb.open()
        self.accessName = None
        self.adb = self.openAccessDb()
        self.setModal(True)
        self.setUi()
        self.setWindowTitle("Import Location Data from {}".format(self.accessName[:self.accessName.index('.')]))

    def setUi(self):
        self.setMinimumSize(1450, 700)
        groupCategories = QGroupBox()
        groupCategories.setTitle("Operation Category")

        self.checkAll = QCheckBox("All Available")
        self.checkAll.stateChanged.connect(self.toggleOptions)
        self.checkBreakingCenter = QCheckBox("Breaking Center")
        self.checkBreedingFarm = QCheckBox("Polo Breeding Farm")

        self.checkPoloCenter = QCheckBox('Polo Training Center')
        self.checkPoloClub = QCheckBox('Polo Club')

        self.checkRanch = QCheckBox("Ranch")


        # self.checkGelding = QCheckBox("Gelding")
        categoriesLayout = QGridLayout()
        categoriesLayout.addWidget(self.checkAll,0,0)
        categoriesLayout.addWidget(self.checkBreakingCenter,1,0)
        categoriesLayout.addWidget(self.checkBreedingFarm, 2,0)

        categoriesLayout.addWidget(self.checkPoloCenter, 1,1)
        categoriesLayout.addWidget(self.checkPoloClub,2,1)

        categoriesLayout.addWidget(self.checkRanch,1,2)

        groupCategories.setLayout(categoriesLayout)

        lblDate = QLabel("Import Date")
        self.importDate = QDateEdit()
        self.importDate.setCalendarPopup(True)
        self.importDate.setDate(QDate.currentDate())
        self.importDate.setMaximumWidth(120)
        self.createTemporaryTables()
        self.importLocations()
        qry, qrySelected = self.loadAvailableLocations()
        colorDict = {}
        colDict = {
            0: ("id", True, True, False, None),
            1: ("HBid", True, True, False, None),
            2: ("Name", False, False, False, None),
            3: ("Address", True, True, False, None),
            4: ("Ownerid", True, True, False, None),
            5: ("Managerid", True, True, False, None),
            6: ("Tel", True, True, False, None),
            7: ("BC", False, True, True, None),
            8: ("BF", False, True, True, None),
            9: ("R", False, True, True, None),
            10: ("PC", False, True, True, None),
            11: ("C", False, True, True, None),
            12: ("Selected", True, True, False, None)}

        self.tableImported = TableViewAndModel(colDict=colDict, colorDict=colorDict, size=(100,100), qry=qry)
        self.tableImported.setObjectName("tableImported")
        self.tableImported.setMouseTracking(True)
        self.tableImported.entered.connect(self.setArrows)
        self.tableImported.viewportEntered.connect(self.setArrows)
        self.tableImported.doubleClicked.connect(self.includeLocation)

        self.tableSelected = TableViewAndModel(colDict, {}, (100, 100), qrySelected)
        self.tableSelected.setMouseTracking(True)
        self.tableSelected.entered.connect(self.setArrows)
        self.tableSelected.viewportEntered.connect(self.setArrows)
        self.tableSelected.doubleClicked.connect(self.excludeLocation)

        self.toolRight = QToolButton()
        self.toolRight.setIcon(QIcon(":Icons8/arrows/right-arrow.png"))
        self.toolRight.setMinimumSize(100, 30)
        self.toolRight.clicked.connect(lambda: self.includeLocation(WHERE_CLAUSE_ONE))
        self.toolRight.setToolTip("Load selected Horse")
        self.toolRight.setEnabled(False)

        self.toolAllRight = QToolButton()
        self.toolAllRight.setIcon(QIcon(":Icons8/arrows/double-right.png"))
        self.toolAllRight.setMinimumSize(100, 30)
        self.toolAllRight.clicked.connect(lambda: self.includeLocation(WHERE_CLAUSE_ALL))
        self.toolAllRight.setToolTip("Load All Horses")
        self.toolAllRight.setEnabled(False)

        self.toolLeft = QToolButton()
        self.toolLeft.setIcon(QIcon(":Icons8/arrows/left-arrow.png"))
        self.toolLeft.setMinimumSize(100, 30)
        self.toolLeft.clicked.connect(lambda: self.excludeLocation(WHERE_CLAUSE_ONE))
        self.toolLeft.setEnabled(False)

        self.toolAllLeft = QToolButton()
        self.toolAllLeft.setIcon(QIcon(":Icons8/arrows/double-left.png"))
        self.toolAllLeft.setMinimumSize(100, 30)
        self.toolAllLeft.clicked.connect(lambda: self.excludeLocation(WHERE_CLAUSE_ALL))
        self.toolAllLeft.setEnabled(False)

        lblAvailable = QLabel("Locations Available")
        lblSelected = QLabel("Selected Locations")
        lblCodes = QLabel("BC:Breaking Center, BF:Breeding Farm, R:Ranch, PC:Polo Trainning Center,C:Polo Club")

        toolsFrame = QFrame()
        toolsFrame.setMaximumWidth(150)
        toolsFrame.setMaximumHeight(150)

        toolsLayout = QVBoxLayout()
        toolsLayout.addWidget(self.toolRight)
        toolsLayout.addWidget(self.toolAllRight)
        toolsLayout.addWidget(self.toolLeft)
        toolsLayout.addWidget(self.toolAllLeft)
        toolsFrame.setLayout(toolsLayout)

        centerLayout = QGridLayout()
        centerLayout.addWidget(lblAvailable, 0, 0)
        centerLayout.addWidget(lblSelected, 0, 2)
        centerLayout.addWidget(toolsFrame, 1, 1)
        centerLayout.addWidget(self.tableImported, 1, 0)
        centerLayout.addWidget(self.tableSelected, 1, 2)

        toolImport = QPushButton(QIcon(":/Icons8/arrows/import.png"), "Import")
        toolImport.clicked.connect(self.importLocationList)
        toolImport.setMaximumWidth(100)

        self.btnSave = QPushButton("Save")
        self.btnSave.setMaximumWidth(80)
        self.btnSave.setEnabled(False)
        self.btnSave.clicked.connect(self.saveAndClose)

        btnClose = QPushButton("Cancel")
        btnClose.setMaximumWidth(80)
        btnClose.clicked.connect(self.widgetClose)

        importLayout = QHBoxLayout()
        importLayout.addWidget(lblDate, Qt.AlignRight)
        importLayout.addWidget(self.importDate, Qt.AlignRight)
        importLayout.addWidget(toolImport, Qt.AlignRight)
        importLayout.addSpacing(1000)
        # importLayout.addWidget(btnRefresh)
        importLayout.addWidget(btnClose)
        importLayout.addWidget(self.btnSave)

        vLayout = QVBoxLayout()
        vLayout.addWidget(groupCategories)
        vLayout.addLayout(centerLayout)
        vLayout.addWidget(lblCodes)
        vLayout.addLayout(importLayout)

        self.setLayout(vLayout)

    @pyqtSlot()
    def setArrows(self):
        action = True if self.sender().objectName() == "tableImported" else False
        if self.sender().model().query().size() > 0:
            self.toolRight.setEnabled(action)
            self.toolAllRight.setEnabled(action)
            self.toolLeft.setEnabled(not action)
            self.toolAllLeft.setEnabled(not action)

    def openAccessDb(self):
        try:
            sett = SettingsDialog()
            self.accessName = sett.accessDatabaseName
            if QSqlDatabase.contains("MSAccess"):
                adb = QSqlDatabase.database("MSAccess", True)
                return adb

            sett.loadData()
            adb = QSqlDatabase.addDatabase("QODBC", "MSAccess")
            sett.accessTest()
            con_string = sett.accessConnectionString
            adb.setDatabaseName(con_string)
            if adb.open():
                self.adb = adb
                return adb
            raise DataError("openAccessDb", adb.lastError().text())
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def importLocations(self):
        try:
            qryImport = QSqlQuery(self.adb)
            import_str = """SELECT id, nombre, owner, Address, responsableid, telephone,
                   escentrodoma, esharas, esestancia, escentropolo, esclubpolo
                   FROM qryExportLocations 
                   """
            where_str = ''
            opt_str = [self.checkBreedingFarm.isChecked(), self.checkBreakingCenter.isChecked(),
                       self.checkRanch.isChecked(), self.checkPoloClub.isChecked(), self.checkPoloCenter.isChecked()]
            if True in opt_str:
                if opt_str[0]:
                    where_str += "WHERE esharas " if len(where_str) == 0 else " OR esharas "
                if opt_str[1]:
                    where_str += "WHERE escentrodoma " if len(where_str) == 0 else " OR escentrodoma "
                if opt_str[2]:
                    where_str += "WHERE esestancia " if len(where_str) == 0 else " OR esestancia "
                if opt_str[3]:
                    where_str += "WHERE espoloclub " if len(where_str) == 0 else " OR espoloclub "
                if opt_str[4]:
                    where_str += "WHERE escentropolo " if len(where_str) == 0 else " OR escentropolo "
                where_str += ";"

            qryImport.prepare(import_str + where_str)
            qryImport.exec()
            if qryImport.lastError().type() != 0:
                raise DataError("importLocations - access", qryImport.lastError().text())
            if not qryImport.first():
                raise DataError("importLocations - access", "There are no locations to import")
            qryImport.seek(-1)
            rows = 0
            while qryImport.next():
                rows += 1
            qryImport.seek(-1)
            proDiag = QProgressDialog("Loading Locations", None, 0, rows, self)
            proDiag.setWindowModality(Qt.WindowModal)
            proDiag.setWindowTitle("Importing Locations")
            proDiag.setMinimumWidth(500)
            qryImport.seek(-1)
            qry = QSqlQuery(self.db)
            i = 0
            while qryImport.next():
                qry.prepare("CALL importlocations_loaddata(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")
                qry.addBindValue(QVariant(qryImport.value(0)))  # accessid
                qry.addBindValue(QVariant(qryImport.value(1)))  # name
                qry.addBindValue(QVariant(qryImport.value(2)))  # owner
                qry.addBindValue(QVariant(qryImport.value(3)))  # address
                qry.addBindValue(QVariant(qryImport.value(4)))  # managerid
                qry.addBindValue(QVariant(qryImport.value(5)))  # telephone
                qry.addBindValue(QVariant(qryImport.value(6)))  # breakingC
                qry.addBindValue(QVariant(qryImport.value(7)))  # breeding
                qry.addBindValue(QVariant(qryImport.value(8)))  # Ranch
                qry.addBindValue(QVariant(qryImport.value(9)))  # polocenter
                qry.addBindValue(QVariant(qryImport.value(10))) # poloClub
                qry.exec()
                if qry.lastError().type() != 0:
                    raise DataError("importLocations - access", qry.lastError().text())
                qry.clear()
                i += 1
                proDiag.setValue(i)
                if proDiag.wasCanceled():
                    break
        except DataError as err:
            print(err.source, err.message)
            QMessageBox.warning(self, err.source, err.message, QMessageBox.Ok)
        finally:
            if not self.tempDb.isOpen():
                self.tempDb.open()

    @pyqtSlot()
    def importLocationList(self):
        try:
            self.createTemporaryTables()
            self.importLocations()
            qry, qrySelected = self.loadAvailableLocations()
            self.tableImported.model().setQuery(qry)
            self.tableSelected.model().setQuery(qrySelected)
        except Exception as err:
            print("importLocationList", type(err), err.args)

    def refreshTables(self):
        try:
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL importlocations_getimportedlocations ()")
            if qry.lastError().type() != 0:
                raise DataError("refreshTables - include", qry.lastError().text())
            self.tableImported.model().setQuery(qry)
            qryExport = QSqlQuery(self.tempDb)
            qryExport.exec("CALL importlocations_getselectedlocations ()")
            if qryExport.lastError().type() != 0:
                raise DataError("refreshTables - exclude", qryExport.lastError().text())
            self.tableSelected.model().setQuery(qryExport)
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print("refreshTables", err.args)

    @pyqtSlot()
    def loadAvailableLocations(self):
        try:
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL importlocations_loadAvailablelocations()")
            if qry.lastError().type() != 0:
                raise DataError("loadAvailablelocations", qry.lastError().text())
            if not qry.first() and self.isVisible():
                raise DataError("Available Horses", "There are not available locations ")
            qrySelected = QSqlQuery(self.tempDb)
            qrySelected.exec("CALL importlocations_getselectedlocations()")
            if qrySelected.lastError().type() != 0:
                raise DataError("loadavailableLocations-selected", qrySelected.lastError().text())
            return qry, qrySelected
        except DataError as err:
            QMessageBox.warning(self, err.source, err.message, QMessageBox.Ok)


    @pyqtSlot()
    def toggleOptions(self):
        opt = self.checkAll.isChecked()
        self.checkBreakingCenter.setChecked(opt)
        self.checkBreedingFarm.setChecked(opt)
        self.checkPoloCenter.setChecked(opt)
        self.checkPoloClub.setChecked(opt)
        self.checkRanch.setChecked(opt)


    @pyqtSlot()
    def enableSave(self):
        if self.tableSelected.model().rowCount() > 0:
            self.btnSave.setEnabled(True)
        else:
            self.btnSave.setEnabled(False)

    def createTemporaryTables(self):
        try:
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL importlocations_createtemporary()")
            if qry.lastError().type() != 0:
                raise DataError("createTemporaryTables", qry.lastError().text())
            if qry.first():
                raise DataError("createTemporaryTables", qry.value(0) + ' ' + qry.value(1))
        except DataError as err:
            if '02001'in err.message:
                QMessageBox.critical(self, "No Data", err.message, QMessageBox.Ok)
                raise DataError(err.source, err.message)

            print(err.source, err.message)

    @pyqtSlot()
    def includeLocation(self, clause=WHERE_CLAUSE_ONE):
        try:
            row = self.tableImported.currentIndex().row()
            self.tableImported.model().query().seek(row)
            self.record = self.tableImported.model().query().record()
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL importlocations_includeLocation({})".format(
                self.record.value(0) if clause == WHERE_CLAUSE_ONE else 'NULL'))
            if qry.lastError().type() != 0:
                raise DataError("includehorse", qry.lastError().text())
            if qry.first():
                raise DataError("importLocation", "Error {}".format(qry.value(0)))
            self.refreshTables()
            self.enableSave()
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def excludeLocation(self, clause=WHERE_CLAUSE_ONE):
        try:
            row = self.tableSelected.currentIndex().row()
            self.tableSelected.model().query().seek(row)
            self.record = self.tableSelected.model().query().record()
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL importlocations_excludeLocation({})".format(
                self.record.value(0) if clause == WHERE_CLAUSE_ONE else 'NULL'))
            if qry.lastError().type() != 0:
                raise DataError("excludehorse", qry.lastError().text())
            if qry.first():
                raise DataError("importLocation", "Error {}".format(qry.value(0)))
            self.refreshTables()
            self.enableSave()
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def saveAndClose(self):
        try:
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL importlocations_save('{}')".format(self.importDate.date().toString("yyyy-MM-dd")))
            if qry.lastError().type() != 0:
                raise DataError("saveAndClose", qry.lastError().text())
            if qry.first():
                raise DataError("saveAndClose", qry.value(0))
            self.widgetClose()
        except DataError as err:
            QMessageBox.warning(self, err.source, err.message, QMessageBox.Ok)
        except Exception as err:
            print("saveAndClose", type(err), err.args)

    @pyqtSlot()
    def widgetClose(self):
        if self.tempDb.isOpen():
            self.tempDb.close()
        if self.adb.isOpen():
            self.adb.close()
        self.done(QDialog.Rejected)