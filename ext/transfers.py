import sys
import os
import json
from PyQt5.QtWidgets import (QDialog, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel, QLineEdit, QPlainTextEdit,
                             QPushButton, QToolButton, QMessageBox, QCheckBox, QListView, QTableView,
                              QAbstractItemView, QMainWindow, QFrame, QFormLayout, QGroupBox, QDateEdit)
from PyQt5.QtCore import Qt, QSettings, pyqtSlot, QVariant, QEvent, QPoint, QModelIndex, QDate
from PyQt5.QtGui import QStandardItemModel, QColor, QMouseEvent, QIcon
from PyQt5.QtSql import QSqlQuery, QSqlQueryModel, QSqlDriver, QSqlDatabase, QSqlError, QSql
import pymysql
from ext.APM import ( TableViewAndModel, FocusCombo, TEMP_RECORD_IN, TEMP_RECORD_OUT ,Cdatabase,
                    OPEN_NEW, OPEN_EDIT, DataError, SQL_Query, NullDateEdit)

from configparser import ConfigParser

class Transfer(QDialog):
    """It takes the inventory of a single participant - supplier -" that may include
    one or more agreements, and  produces transfers between the supplier's locations plus the horse owner location
    and  start the horse as first transfer is done from base location to supplier location"""
    def __init__(self, db, supplierId, mode = OPEN_NEW, con_string = None,
                 transferRecord = None, qryHorses = None, parent=None):
        super().__init__()
        try:
            self.setModal(True)
            self.db = db
            if not self.db.isOpen():
                self.db.open()
            self.con_string = con_string
            self.supplierId = supplierId
            self.mode = mode
            self.tempDb = None
            self.okTransfers = [False, False]
            if isinstance(parent, QMainWindow):
                self.parent = parent
            else:
                self.parent = parent.parent
            self.qryHorses = qryHorses
            self.transferRecord = transferRecord
            self.originalDate = None
            self.deleted = []
            self.inserted = []
            self.isDirty = False
            self.toHome = False
            self.oldDate = None
            self.setUI()
        except DataError as err:
            raise DataError(err.source, err.message)

    def setUI(self):
        """Include all the data transfer"""
        if self.mode == OPEN_NEW:
            self.setWindowTitle(self.parent.supplier + ": Horse Transference")
        else:
            self.setWindowTitle(self.parent.supplier + ": Edit Horse Transference")


        groupBase = QGroupBox("Horse Transference")
        groupBase.setAlignment(Qt.AlignHCenter)

        _date, self.minimumDate,  = self.getMinimumDate()

        lblDate = QLabel("Date")
        self.dateDate = QDateEdit()
        self.dateDate.setDate(QDate.currentDate())
        self.dateDate.setCalendarPopup(True)
        self.dateDate.setMinimumWidth(120)
        self.dateDate.setMinimumDate(_date)
        #self.dateDate.dateChanged.connect(self.setOldDate)
        self.dateDate.dateChanged.connect(self.enableSave)

        lblDriver = QLabel('Driver')
        modelDriver = QSqlQueryModel()
        modelDriver.setQuery(self.getDrivers())
        self.comboDriver = FocusCombo()
        self.comboDriver.setModel(modelDriver)
        self.comboDriver.setModelColumn(1)
        self.comboDriver.setCurrentIndex(-1)
        self.comboDriver.activated.connect(self.enableSave)
        self.comboDriver.activated.connect(self.setDirty)
        self.comboDriver.setCurrentIndex(-1)

        lblFrom = QLabel('From Location')
        self.comboFrom = FocusCombo()
        self.comboFrom.setObjectName('comboFrom')
        self.comboFrom.model().setQuery(self.locationsLook(2))
        self.comboFrom.setModelColumn(1)
        self.comboFrom.activated.connect(self.enableSave)
        self.comboFrom.activated.connect(self.enableTransfers)
        self.comboFrom.activated.connect(self.loadToLocations)
        self.comboFrom.activated.connect(self.changeFromLocation)
        # main = self.comboFrom.seekData(True, 2)
        if self.mode == OPEN_NEW:
            searchDict = {2:True,3: self.supplierId}
            mani = self.comboFrom.seekMultipleData(searchDict)
        else:
            self.comboFrom.setCurrentIndex(-1) # if self.mode == OPEN_NEW else self.comboFrom.setCurrentIndex(-1)

        lblTo = QLabel('To Location')
        self.comboTo = FocusCombo()
        self.comboTo.model().setQuery(self.locationsLook(3))
        self.comboTo.setModelColumn(1)
        self.comboTo.setCurrentIndex(-1)
        self.comboTo.setMinimumWidth(250)
        self.comboTo.activated.connect(self.enableSave)
        self.comboTo.activated.connect(self.enableTransfers)
        #self.comboTo.activated.connect(self.loadFromHorses)

        groupTools = QGroupBox()
        self.toolRight = QToolButton()
        self.toolRight.setObjectName('ToolRight')
        self.toolRight.setIcon(QIcon(":icons8/arrows/right-arrow.png"))
        self.toolRight.setMaximumSize(100, 30)
        self.toolRight.setMinimumWidth(100)
        self.toolRight.setEnabled(False)
        self.toolRight.clicked.connect(self.transferHorse)
        self.toolRight.clicked.connect(self.enableSave)

        self.toolLeft = QToolButton()
        self.toolLeft.setIcon(QIcon(":icons8/arrows/left-arrow.png"))
        self.toolLeft.setMaximumSize(100, 30)
        self.toolLeft.setMinimumWidth(80)
        self.toolLeft.setEnabled(False)
        self.toolLeft.clicked.connect(self.transferHorse)
        self.toolLeft.clicked.connect(self.enableSave)

        self.toolAllRight = QToolButton()
        self.toolAllRight.setIcon(QIcon(":Icons8/arrows/double-right.png"))
        self.toolAllRight.setStatusTip("Load All Horses")
        self.toolAllRight.setObjectName("AllRight")
        self.toolAllRight.setMinimumSize(100, 30)
        self.toolAllRight.clicked.connect(self.transferAllHorses)
        self.toolAllRight.setToolTip("Load All Horses")
        self.toolAllRight.setEnabled(False)

        self.toolAllLeft = QToolButton()
        self.toolAllLeft.setIcon(QIcon(":Icons8/arrows/double-left.png"))
        self.toolAllLeft.setStatusTip("Remove All Horses")
        self.toolAllLeft.setObjectName("AllLeft")
        self.toolAllLeft.setMinimumSize(100, 30)
        self.toolAllLeft.clicked.connect(self.transferAllHorses)
        self.toolAllLeft.setEnabled(False)

        frameTools = QFrame()
        frameLayout = QVBoxLayout()
        frameLayout.addWidget(self.toolRight)
        frameLayout.addWidget(self.toolAllRight)
        frameLayout.addWidget(self.toolAllLeft)
        frameLayout.addWidget(self.toolLeft)
        frameTools.setLayout(frameLayout)

        self.initialiteTableViews()

        pushCancel = QPushButton("Cancel")
        pushCancel.setMaximumWidth(60)
        pushCancel.clicked.connect(self.closeForm)

        self.pushSave = QPushButton("Save")
        self.pushSave.setMaximumWidth(60)
        self.pushSave.setEnabled(False)
        self.pushSave.clicked.connect(self.saveAndClose)

        pushLayout = QHBoxLayout()
        pushLayout.addWidget(pushCancel)
        pushLayout.addWidget(self.pushSave)

        if self.mode == OPEN_EDIT:
            self.comboFrom.setEnabled(False)
            self.comboTo.setEnabled(False)

            self.pushDelete = QPushButton("Delete")
            self.pushDelete.setStatusTip("Deletes the whole transfer")
            self.pushDelete.setMaximumWidth(80)
            self.pushDelete.clicked.connect(self.deleteTransfer)
            self.pushDelete.setEnabled(False)

            self.pushClose = QPushButton("Transfer Close")
            self.pushClose.setStatusTip("Close the transfer")
            self.pushClose.setMaximumWidth(120)
            self.pushClose.clicked.connect(self.closeTransfer)
            self.pushClose.setEnabled(False)

            lblFromDate = QLabel("From Date")
            lblToDate = QLabel("To Date")
            lblFromLocation = QLabel("From:")
            lblToLocation = QLabel("To:")

            self.fromDate = NullDateEdit(self)
            self.fromDate.setMinimumDate(self.minimumDate)

            self.toDate = NullDateEdit(self)
            self.toDate.setMinimumDate(self.minimumDate)

            self.comboLookFrom = FocusCombo()
            self.comboLookFrom.model().setQuery(self.locationsLook(0))
            self.comboLookFrom.setModelColumn(1)

            self.comboLookTo = FocusCombo()
            self.comboLookTo.model().setQuery(self.locationsLook(1))
            self.comboLookTo.setModelColumn(1)

            optLayout = QVBoxLayout()
            groupOptions = QGroupBox()
            groupOptions.setLayout(optLayout)
            self.checkAll = QCheckBox("All Transfers")
            self.checkAll.setChecked(True)
            self.checkAll.setObjectName("All")
            self.checkAll.stateChanged.connect(self.optionChanged)
            self.checkOpen = QCheckBox("Open Transfers")
            self.checkOpen.setObjectName("Open")
            self.checkOpen.stateChanged.connect(self.optionChanged)
            self.checkClosed = QCheckBox("Closed Transfers")
            self.checkClosed.setObjectName("Closed")
            self.checkClosed.stateChanged.connect(self.optionChanged)
            optLayout.addWidget(self.checkAll)
            optLayout.addWidget(self.checkOpen)
            optLayout.addWidget(self.checkClosed)

            qry = self.getTransfers()
            transferId = qry.value(0)
            colorDict = {'column': (5),
                         u'\u2714': (QColor('black'), QColor('white'))}
            colDict = {
                0: ("ID", True, True, False, None),
                1: ("Date", False, True, False, None),
                2: ("driverId", True, True, False, None),
                3: ("From:", False, True, False, None),
                4: ("To:", False, True, False, None),
                5: ("Closed", False, True, True, None),
                6: ("Active", True, True, True, None),
                7: ("FromId", True, True, False, None),
                8: ("ToId", True, True, False, None)}
            self.tableTransfers = TableViewAndModel(colDict, colorDict, (100, 200), qry)
            self.tableTransfers.selectionModel().selectionChanged.connect(self.transferChanged)
            self.tableTransfers.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.tableTransfers.doubleClicked.connect(self.editTransfer)
            self.tableTransfers.setMinimumWidth(435)

            #self.dateDate.setDate(self.transferRecord.value(1))
            self.originalDate = self.dateDate.date()
            self.dateDate.dateChanged.connect(self.setDirty)

            self.comboDriver.activated.connect(self.setDirty)

            toolApplyFilter = QToolButton()
            toolApplyFilter.setIcon(QIcon(":/Icons8/print/filter.png"))
            toolApplyFilter.setStatusTip("Apply Filters")
            toolApplyFilter.clicked.connect(self.getTransfers)

            toolClearFilters = QToolButton()
            toolClearFilters.setIcon(QIcon(":Icons8/Edit/reset.png"))
            toolClearFilters.setStatusTip("Clear Filters")
            toolClearFilters.clicked.connect(self.clearFilters)
            toolClearFilters.setMaximumSize(100, 25)

            filterLayout = QGridLayout()
            filterGroup = QGroupBox("Filters")
            filterGroup.setLayout(filterLayout)
            filterLayout.addWidget(toolApplyFilter, 0, 0)
            filterLayout.addWidget(toolClearFilters, 1, 0)
            filterLayout.addWidget(lblFromDate, 0, 1, Qt.AlignRight)
            filterLayout.addWidget(lblToDate, 1, 1, Qt.AlignRight)

            filterLayout.addWidget(self.fromDate, 0, 2)
            filterLayout.addWidget(self.toDate, 1, 2)
            filterLayout.addWidget(lblFromLocation, 0, 3, Qt.AlignRight)
            filterLayout.addWidget(lblToLocation, 1, 3, Qt.AlignRight)
            filterLayout.addWidget(self.comboLookFrom, 0, 4)
            filterLayout.addWidget(self.comboLookTo, 1, 4)
            filterLayout.addWidget(groupOptions, 0, 5, 2, 1)

            pushLayout.insertWidget(1, self.pushDelete)
            pushLayout.insertWidget(1, self.pushClose)

        gLayout = QGridLayout()
        gLayout.addWidget(lblDate,0,0)
        gLayout.addWidget(self.dateDate,0,1)
        gLayout.addWidget(lblDriver,0,2)
        gLayout.addWidget(self.comboDriver,0,3)
        gLayout.addWidget(lblFrom,0,4)
        gLayout.addWidget(self.comboFrom,0,5)
        gLayout.addWidget(lblTo,0,6)
        gLayout.addWidget(self.comboTo,0,7)

        groupBase.setLayout(gLayout)

        groupFrom = QGroupBox("From:")
        groupFrom.setAlignment(Qt.AlignHCenter)

        groupFromLayout = QHBoxLayout()
        groupFromLayout.addWidget(self.tableFrom)
        groupFrom.setLayout(groupFromLayout)

        groupTo = QGroupBox('To:')
        groupTo.setAlignment(Qt.AlignHCenter)
        groupToLayout = QHBoxLayout()
        groupToLayout.addWidget(self.tableTo)
        groupTo.setLayout(groupToLayout)

        groupLayout = QHBoxLayout()
        groupLayout.addWidget(groupFrom)
        groupLayout.addWidget(frameTools)
        groupLayout.addWidget(groupTo)

        vLayout = QVBoxLayout()
        vLayout.addWidget(groupBase)
        vLayout.addLayout(groupLayout)
        if self.mode == OPEN_EDIT:
            vLayout.addWidget(filterGroup)
            vLayout.addWidget(self.tableTransfers)
        vLayout.addLayout(pushLayout)

        self.setLayout(vLayout)

    @pyqtSlot()
    def transferChanged(self):
        try:
            self.pushClose.setEnabled(False)
            self.pushSave.setEnabled(False)
            self.pushDelete.setEnabled(False)
            qry = self.tableTransfers.model().query()
            row = self.tableTransfers.currentIndex().row()
            qry.seek(row)
            transferId = qry.value(0)
            self.getHorses(transferId)
            self.updateTransferTables()
            #self.tableTo.model().setQuery(qryHorses)
        except Exception as err:
            print(err.args)

    def getHorses(self, transferId):
        try:
            qry = SQL_Query(self.tempDb)
            qry.exec("CALL transfer_retrivetransferhorses({})".format(transferId))
            if qry.lastError().type() != 0:
                raise DataError('getHorses', qry.lastError().text())
            if qry.first():
                raise DataError('getHorses', qry.value(0))
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print(err.args)

    def updateTransferTables(self):
        try:

            qryFrom = QSqlQuery(self.tempDb)
            qryFrom.exec("CALL transfer_getcurrenthorses({})".format(TEMP_RECORD_OUT))
            if qryFrom.lastError().type() != 0:
                raise DataError('getHorses', qryFrom.lastError().text())
            self.tableFrom.model().setQuery(qryFrom)
            self.tableFrom.hideColumn(7)
            qryTo = QSqlQuery(self.tempDb)
            qryTo.exec("CALL transfer_getcurrenthorses({})".format(TEMP_RECORD_IN))
            if qryTo.lastError().type() != 0:
                raise DataError('getHorses', qryTo.lastError().text())
            self.tableTo.model().setQuery(qryTo)
            self.tableTo.hideColumn(7)
            self.enableSave()

        except DataError as err:
            raise DataError(err.source, err.message)

    @pyqtSlot()
    def editTransfer(self):
        try:
            qry = self.tableTransfers.model().query()
            row = self.tableTransfers.currentIndex().row()
            if qry.seek(row):
                if qry.value(5) == u'\u2714':
                    QMessageBox.warning(self, "Transfer Closed", "This transfer has been already closed",
                                        QMessageBox.Ok)
                    return
                res = QMessageBox.question(self, 'Close Transfer',
                                           "Do you want to edit the transfer dated on {} , "
                                           "From: {} To: {}".format(qry.value(1).toString("MM-dd-yyyy"),
                                                                    qry.value(3), qry.value(4)), QMessageBox.Yes |
                                           QMessageBox.No)
                if res == QMessageBox.Yes:
                    self.pushClose.setEnabled(True)
                    self.pushSave.setEnabled(True)
                    self.pushDelete.setEnabled(True)
                    record = qry.record()
                    self.dateDate.setDate(record.value(1))
                    self.oldDate = self.dateDate.date()
                    self.comboDriver.seekData(record.value(2), 0)
                    self.comboFrom.seekData(record.value(7), 0)
                    self.loadToLocations()
                    self.comboTo.seekData(record.value(8),0)
                    self.transferRecord = record
                    self.loadFromHorses()
                    self.updateTransferTables()
                    #self.tableFrom.model().setQuery(self.loadFromHorses())

        except Exception as err:
            print("editTransfer",err.args)

    @pyqtSlot()
    def clearFilters(self):
        self.fromDate.setDate(QDate())
        self.toDate.setDate(QDate())

        self.comboLookFrom.setCurrentIndex(-1)
        self.comboLookTo.setCurrentIndex(-1)
        self.checkAll.click()

    @pyqtSlot()
    def locationsLook(self, option):
        try:

            qry = QSqlQuery(self.db)
            qry.exec("CALL transfer_looklocations({}, {}, {})".format(self.supplierId, option,
                                                        'NULL' if option < 3 else self.comboFrom.getHiddenData(0)))
            if qry.lastError().type() != 0:
                raise DataError("locationsLook", qry.lastError().text())
            return qry
        except DataError:
            return
        except Exception as err:
            print("locationsLook", err.args)

    @pyqtSlot()
    def getTransfers(self):
        try:
            sender = self.sender()
            filter = {}
            filter['strwhere'] = " WHERE t.supplierid = {}". format(self.supplierId)
            if self.fromDate.text != 'None' and self.toDate.text != 'None':
                filter['strdate'] = " AND (t.date BETWEEN ''{}'' AND ''{}''".format(self.fromDate.toString("yyyy-MM-dd"),
                                                             self.toDate.toString("yyyy-MM-dd"))
            elif self.fromDate.text != 'None' and self.toDate.text == 'None':
                filter['strdate'] = " AND t.date >= ''{}''".format(self.fromDate.date.toString("yyyy-MM-dd" ))
            elif self.toDate.text != 'None':
                filter['strdate'] =  " AND t.date <= ''{}''".format(self.fromDate.date.toString("yyyy-MM-dd"))
            if self.comboLookFrom.currentIndex() != -1:
                filter['strfrom'] = " AND t.fromid  = {}". format(self.comboLookFrom.getHiddenData(0))
            if self.comboLookTo.currentIndex() != -1:
                filter['strto'] = " AND t.toid  = {}". format(self.comboLookFrom.getHiddenData(0))
            if self.checkClosed.isChecked():
                filter['stroption'] = " AND t.closed "
            elif self.checkOpen.isChecked():
                filter['stroption'] = " AND NOT t.closed "
            jFilter = json.dumps(filter)
            qry = QSqlQuery(self.db)
            qry.exec("CALL transfer_gettransfers('{}')".format(jFilter))
            if qry.lastError().type() != 0:
                raise DataError("getTransfers", qry.lastError().text())
            if not qry.first():
                raise DataError("getTransfers", "There is no data!")
            if isinstance(sender, QToolButton):
                self.tableTransfers.model().setQuery(qry)
                return
            return qry
        except DataError as err:
            QMessageBox.warning(self, "Notice", "There are not transfers for {}".format(self.parent.supplier))
            raise DataError(err.source, err.message)

    def getMinimumDate(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL transfer_minimumdate({})".format(self.supplierId))
            if qry.lastError().type() != 0:
                raise DataError('getMinimumDate', qry.lastError().text())
            if qry.first():
                return qry.value(0), qry.value(1)
        except DataError as err:
            print(err.source, err.message)

    def initialiteTableViews(self):
        self.createTemporaryTables()
        qry = self.loadFromHorses()

        colorDict = {'column': (3),
                         u'\u2640': (QColor('pink'), QColor('black')),
                         u'\u2642': (QColor('lightskyblue'), QColor('black')),
                         u'\u265E': (QColor('lightgrey'), QColor('black'))}
        colDict = {
                0: ("ID", True, True, False, None),
                1: ("RP", False, True, True, None),
                2: ("Name", False, False, False, None),
                3: ("Sex", False, True, True, None),
                4: ("Coat", False, True, False, None),
                5: ("DetailId", True, True, False, None),
                6: ("ahid", True, True, True, None),
                7:("selected", True, True, False, None)}

        self.tableFrom = TableViewAndModel(colDict, colorDict, (100, 300), qry)
        self.tableFrom.setObjectName('TableFrom')
        self.tableFrom.setMouseTracking(True)
        self.tableFrom.entered.connect(self.setArrows)
        self.tableFrom.viewportEntered.connect(self.setArrows)
        self.tableFrom.clicked.connect(self.enableTransfers)
        self.tableFrom.clicked.connect(self.tableClicked)
        self.tableFrom.doubleClicked.connect(self.transferHorse)
        self.tableFrom.doubleClicked.connect(self.enableSave)

        qryTo = self.loadBaseToHorses()

        self.tableTo = TableViewAndModel(colDict, colorDict, (100, 300), qryTo)
        self.tableTo.setObjectName('TableTo')
        self.tableTo.setMouseTracking(True)
        self.tableTo.entered.connect(self.setArrows)
        self.tableTo.viewportEntered.connect(self.setArrows)
        self.tableTo.clicked.connect(self.enableTransfers)
        self.tableTo.clicked.connect(self.tableClicked)
        self.tableTo.doubleClicked.connect(self.transferHorse)
        self.tableTo.doubleClicked.connect(self.enableSave)

    def createTemporaryTables(self):
        try:
            self.tempDb = self.db.cloneDatabase(self.db, "Temp")
            self.tempDb.open()
            qry = QSqlQuery(self.tempDb)
            qry.exec('CALL transfer_createtemporarytables()')
            if qry.lastError().type() != 0:
                raise DataError("createTemporaryTable", qry.lastError().text())
            if qry.first():
                raise DataError("createTemporaryTable", qry.value(0))
        except DataError as err:
            print(err.source, err.message)

    def getDrivers(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL transfer_getdrivers()")
            if qry.lastError().type() != 0:
                raise DataError('getDrivers', qry.lastError().text())
            return qry
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def changeFromLocation(self):
        self.loadFromHorses()

    @pyqtSlot()
    def optionChanged(self):
        try:
            sender = self.sender()
            if not sender.isChecked():
                return
            options = [self.checkAll, self.checkOpen, self.checkClosed]
            [x.setChecked(False) for x in options if x.objectName != sender.objectName]
        except Exception as err:
            print("optionchanged", err.args)

    @pyqtSlot()
    def setDirty(self):
        self.isDirty = True

    @pyqtSlot()
    def loadToLocations(self):
        try:
            self.comboTo.model().setQuery(self.locationsLook(3))
        except Exception as err:
            print("loadToLocations", err.args)

    @pyqtSlot()
    def enableSave(self):
        if self.mode == OPEN_NEW:
            if self.isVisible():
                if self.tableTo.model().query().size() > 0:
                    self.pushSave.setEnabled(True)
                else:
                    self.pushSave.setEnabled(False)
        else:
            if self.isDirty or len(self.inserted)> 0 or len(self.deleted) > 0:
                self.pushSave.setEnabled(True)

    @pyqtSlot()
    def enableTransfers(self):
        okToTransfer = False
        okToDelete = True
        if self.comboFrom.currentIndex() >= 0 and \
            self.comboTo.currentIndex() >= 0 :
            okToTransfer = True
        if self.tableTo.model().query().size()> 0 and okToTransfer:
            okToDelete = True
        self.okTransfers = [okToTransfer, okToDelete]

    @pyqtSlot()
    def loadFromHorses(self):
        try:
            transferRecord =  'NULL' if self.mode == OPEN_NEW  or self.transferRecord is None \
                else self.transferRecord.value(0)
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL transfer_loadfromhorses({}, {}, {})".format(self.supplierId,
                    'NULL' if self.comboFrom.currentIndex() == -1 else self.comboFrom.getHiddenData(0),transferRecord))
            if qry.lastError().type() != 0:
                raise DataError('loadFromHorses', qry.lastError().text())
            if self.isVisible():
                self.updateTransferTables()
                return
            qryFrom = QSqlQuery(self.tempDb)
            qryFrom.exec("CALL transfer_getcurrenthorses({})".format(TEMP_RECORD_OUT))
            if qryFrom.lastError().type() != 0:
                raise DataError('getHorses', qryFrom.lastError().text())
            return qryFrom
        except DataError as err:
            print(err.source, err.message)

    def loadBaseToHorses(self):
        try:
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL transfer_loadtobasequery()")
            if qry.lastError().type() != 0:
                raise DataError('loadBaseToHorses', qry.lastError().text())
            return qry
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def closeForm(self):
        if self.tempDb.isOpen():
            self.tempDb.close()
        self.close()

    @pyqtSlot()
    def transferHorse(self):
        sender = self.sender()
        try:
            if not self.okTransfers[0]:
                QMessageBox.warning(self,"Incomplete Data", "You must set the date and destination",
                                    QMessageBox.Ok)
                return
            if sender.objectName() == 'TableFrom' or \
                    sender.objectName() == 'ToolRight':
                row = self.tableFrom.currentIndex().row()
                qry = self.tableFrom.model().query()
                direction = TEMP_RECORD_IN
            else:
                row = self.tableTo.currentIndex().row()
                qry = self.tableTo.model().query()
                direction = TEMP_RECORD_OUT
            qry.seek(row)
            qryTransfer = QSqlQuery(self.tempDb)
            qryTransfer.exec("CALL transfer_transferhorse({}, {})".format(qry.value(0), direction))
            if qryTransfer.lastError().type() != 0:
                raise DataError('transferHorse', qryTransfer.lastError().text())
            if qryTransfer.first():
                raise DataError("transferHorse", qryTransfer.value(0))
            self.updateTransferTables()
        except DataError as err:
                    print(err.source, err.message)
        except Exception as err:
            if type(err) == IndexError:
                res = QMessageBox.warning(self, "Horse not Selected", "Select the horse to be "
                                                                      "tranfered",QMessageBox.Ok)
            else:
                print("transferHorse", type(err).__name__, err.args)

    @pyqtSlot()
    def transferAllHorses(self):
        try:
            if not self.okTransfers[0]:
                QMessageBox.warning(self,"Incomplete Data", "You must set the date and destination", QMessageBox.Ok)
                return
            sender = self.sender()
            direction = TEMP_RECORD_IN if sender.objectName() == "AllRight" else TEMP_RECORD_OUT
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL transfer_transferallhorses({})".format(direction))
            if qry.lastError().type() != 0:
                raise DataError('transferAllHorses', qry.lastError().text())
            if qry.first():
                raise DataError("transferAllHorses", qry.value(0))
            self.updateTransferTables()
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def setArrows(self):
        if self.mode == OPEN_EDIT and self.tableFrom.model().query().size() < 1:
            return
        action = True if self.sender().objectName() == "TableFrom" else False
        if self.sender().model().query().size() > 0:
            self.toolRight.setEnabled(action)
            self.toolAllRight.setEnabled(action)
            self.toolLeft.setEnabled(not action)
            self.toolAllLeft.setEnabled(not action)
            #if self.tableFrom.currentIndex().row() != -1:
            #    self.toolClear.setEnabled(not action)

    @pyqtSlot()
    def deleteTransfer(self):
        try:
            res = QMessageBox.question(self, "Transfer Delete", "Do you want to delete transfer record dated {} "
                                        "from: {} to: {}". format(self.transferRecord.value(1).toString("yyyy-MM-dd"),
                                                                                        self.transferRecord.value(3),
                                                                                        self.transferRecord.value(4)),
                                       QMessageBox.Yes|QMessageBox.No)
            if res != QMessageBox.Yes:
                return
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL transfer_deletetransfer ({})".format(self.transferRecord.value(0)))
            if qry.lastError().type() != 0:
                raise DataError("deleteTransfer", qry.lastError().text())
            if qry.first():
                raise DataError("deleteTransfer", qry.value(0))
            self.closeForm()
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def closeTransfer(self):
        try:
            if self.transferRecord.value(5) == u'\u2714':
                return
            res = QMessageBox.question(self, 'Close Transfer',
                                       "Do you want to close the transfer dated on {} , "
                                       "From: {} To: {}".format(self.transferRecord.value(1).toString("MM-dd-yyyy"),
                                                self.transferRecord.value(3), self.transferRecord.value(4)), QMessageBox.Yes |
                                       QMessageBox.No)
            if res == QMessageBox.No:
                return
            qry = QSqlQuery(self.db)
            qry.exec("CALL transfer_closetransfer({})".format(self.transferRecord.value(0)))
            if qry.lastError().type() != 0:
                raise DataError("closeTransfer", qry.lastError().text())
            if qry.first():
                raise DataError("closeTramsfer", qry.value(0))
            self.closeForm()
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def saveAndClose(self):
        try:
            msg = "Confirm saving the transference" if self.mode == OPEN_NEW else "Confirm editing the transference"
            ans = QMessageBox.question(self, "Transference", msg, QMessageBox.Yes|QMessageBox.No)
            if ans != QMessageBox.Yes:
                return
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL transfer_save({}, {}, '{}', {}, {}, {}, {}, {})".format(
                'NULL' if self.mode == OPEN_NEW else self.transferRecord.value(0),
                self.mode,
                self.dateDate.date().toString("yyyy-MM-dd"),
                self.comboFrom.getHiddenData(0),
                self.comboTo.getHiddenData(0),
                self.supplierId,
                self.comboDriver.getHiddenData(0),
                'NULL' if self.oldDate is None else "'" + self.oldDate.toString("yyyy-MM-dd") + "'"))
            if qry.lastError().type() != 0:
                raise DataError()

            if qry.first():
                raise DataError("saveAndClose", qry.value(0))
            self.closeForm()
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def tableClicked(self):
        if self.okTransfers[0]:
            activate = False
            if self.sender().objectName() == 'TableFrom':
                activate = True
            self.toolRight.setEnabled(activate)
            self.toolLeft.setEnabled(not activate)

