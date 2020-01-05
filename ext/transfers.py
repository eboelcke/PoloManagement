import sys
import os
from PyQt5.QtWidgets import (QDialog, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel, QLineEdit, QPlainTextEdit,
                             QPushButton, QToolButton, QMessageBox, QCheckBox, QListView, QTableView,
                              QAbstractItemView, QHeaderView, QFrame, QFormLayout, QGroupBox, QDateEdit)
from PyQt5.QtCore import Qt, QSettings, pyqtSlot, QVariant, QEvent, QPoint, QModelIndex, QDate
from PyQt5.QtGui import QStandardItemModel, QColor, QMouseEvent, QIcon
from PyQt5.QtSql import QSqlQuery, QSqlQueryModel, QSqlDriver, QSqlDatabase, QSqlError, QSql
import pymysql
from ext.APM import ( TableViewAndModel, FocusCombo, FocusPlainTextEdit, Cdatabase,
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
            self.transferRecord = transferRecord
            self.tempDb = None
            self.okTransfers = []
            self.parent = parent
            self.qryHorses = qryHorses
            self.transferRecord = transferRecord
            self.originalDate = None
            self.deleted = []
            self.inserted = []
            self.isDirty = False
            self.toHome = False
            self.setUI()
        except DataError as err:
            res = QMessageBox.warning(self,err.source, err.message, QMessageBox.Ok)
            raise DataError(err.source, err.message)

    def setUI(self):
        """Include all the data transfer"""
        if self.mode == OPEN_NEW:
            self.setWindowTitle(self.parent.supplier + ": Horse Transference")
        else:
            self.setWindowTitle(self.parent.supplier + ": Edit Horse Transference")


        groupBase = QGroupBox("Horse Transference")
        groupBase.setAlignment(Qt.AlignHCenter)

        lblDate = QLabel("Date")
        self.dateDate = QDateEdit()
        self.dateDate.setDate(QDate.currentDate())
        self.dateDate.setCalendarPopup(True)
        self.dateDate.setMinimumWidth(120)
        self.dateDate.dateChanged.connect(self.enableSave)
        if self.mode == OPEN_EDIT:
            self.dateDate.setDate(self.transferRecord.value(1))
            self.originalDate = self.dateDate.date()
            self.dateDate.dateChanged.connect(self.setDirty)


        lblDriver = QLabel('Driver')
        modelDriver = QSqlQueryModel()
        modelDriver.setQuery(self.getDrivers())
        self.comboDriver = FocusCombo()
        self.comboDriver.setModel(modelDriver)
        self.comboDriver.setModelColumn(1)
        self.comboDriver.setCurrentIndex(-1)
        self.comboDriver.activated.connect(self.enableSave)
        if self.mode == OPEN_EDIT:
            self.comboDriver.seekData(self.transferRecord.value(2))
            self.comboDriver.activated.connect(self.setDirty)
        else:
            self.comboDriver.setCurrentIndex(-1)

        lblFrom = QLabel('From Location')
        self.comboFrom = FocusCombo()
        self.comboFrom.setObjectName('comboFrom')
        self.comboFrom.setModel(self.fromLocations())
        self.comboFrom.setModelColumn(1)
        self.comboFrom.activated.connect(self.enableSave)
        self.comboFrom.activated.connect(self.loadFromHorses)
        self.comboFrom.activated.connect(self.enableTransfers)
        if self.mode == OPEN_EDIT:
            self.comboFrom.seekData(self.transferRecord.value(7), 0)
        else:
            self.comboFrom.activated.connect(self.loadToLocations)
            self.comboFrom.setModelColumn(2)
            main = self.comboFrom.findData(QVariant(True), Qt.DisplayRole)
            self.comboFrom.setCurrentIndex(main)
            self.comboFrom.setModelColumn(1)


        lblTo = QLabel('To Location')
        self.comboTo = FocusCombo()
        self.comboTo.activated.connect(self.enableSave)
        self.comboTo.setModel(self.loadToLocations())
        self.comboTo.setModelColumn(1)
        self.comboTo.setCurrentIndex(-1)
        self.comboTo.activated.connect(self.enableTransfers)
        self.comboTo.activated.connect(self.loadFromHorses)
        if self.mode == OPEN_EDIT:
            self.comboTo.seekData(self.transferRecord.value(8))

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

        frameTools = QFrame()
        frameLayout = QVBoxLayout()
        frameLayout.addWidget(self.toolRight)
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

        self.pushLoad = QPushButton('Load')
        self.pushLoad.setObjectName('Load')
        self.pushLoad.setMaximumWidth(100)
        self.pushLoad.setEnabled(False)
        self.pushLoad.clicked.connect(self.transferHorse)
        self.pushLoad.clicked.connect(self.enableSave)

        self.pushUnload = QPushButton('Unload')
        self.pushUnload.setObjectName('Unload')
        self.pushUnload.setMaximumWidth(100)
        self.pushUnload.setEnabled(False)
        self.pushUnload.clicked.connect(self.transferHorse)
        self.pushUnload.clicked.connect(self.enableSave)


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

        pushLayout = QHBoxLayout()
        #pushLayout.addSpacing(400)
        pushLayout.addWidget(pushCancel)
        pushLayout.addWidget(self.pushSave)
        #pushLayout.addSpacing(400)

        if self.mode == OPEN_EDIT:
            self.comboFrom.setEnabled(False)
            self.comboTo.setEnabled(False)
            #self.loadToHorses()

            pushDelete = QPushButton("Delete")
            pushDelete.setStatusTip("Deletes the whole transfer")
            pushDelete.setMaximumWidth(100)
            pushDelete.clicked.connect(self.deleteTransfer)

            pushLayout.insertWidget(1, pushDelete)

        loadLayout = QHBoxLayout()
        loadLayout.addSpacing(100)
        loadLayout.addWidget(self.pushLoad)
        loadLayout.addSpacing(0)
        loadLayout.addWidget(self.pushUnload)
        loadLayout.addSpacing(100)

        vLayout = QVBoxLayout()
        vLayout.addWidget(groupBase)
        vLayout.addLayout(groupLayout)
        vLayout.addLayout(loadLayout)
        vLayout.addLayout(pushLayout)

        self.setLayout(vLayout)

    def initialiteTableViews(self):
        qry = self.getQueryFrom()
        self.createTemporaryTables()
        if not self.tempDb.isOpen():
            self.tempDb.open()
        qry.seek(-1)
        qryInsert = QSqlQuery(self.tempDb)
        qryInsert.prepare("""INSERT INTO table1 
                            (id, rp, name, sex, coat, transferdetailid, agreementhorseid) 
                            VALUES (?, ?, ?, ?, ?, Null, ?)
                            """)
        while qry.next():
            qryInsert.addBindValue(QVariant(qry.value(0)))
            qryInsert.addBindValue(QVariant(qry.value(1)))
            qryInsert.addBindValue(QVariant(qry.value(2)))
            qryInsert.addBindValue(QVariant(qry.value(3)))
            qryInsert.addBindValue(QVariant(qry.value(4)))
            qryInsert.addBindValue(QVariant(qry.value(5)))
            qryInsert.exec()
            if qryInsert.lastError().type() != 0:
                raise DataError('loadFromHorses', qryInsert.lastError().text())
        qryResult = QSqlQuery(self.tempDb)
        qryResult.exec("""SELECT id, rp, name, sex, coat, transferdetailid, agreementhorseid FROM table1 ORDER BY sex, name""")
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
            6: ("ahid", True, True, True, None)}


        self.tableFrom = TableViewAndModel(colDict, colorDict, (100, 300), qryResult)
        self.tableFrom.setObjectName('TableFrom')
        self.tableFrom.clicked.connect(self.enableTransfers)
        self.tableFrom.clicked.connect(self.tableClicked)
        self.tableFrom.doubleClicked.connect(self.transferHorse)
        self.tableFrom.doubleClicked.connect(self.enableSave)
        qryTo = None
        if self.mode ==OPEN_NEW:
            qryTo = QSqlQuery(self.tempDb)
            qryTo.exec("SELECT id, rp, name, sex,  coat, transferdetailid, agreementhorseid FROM table2")
        else:
            qryTo = self.loadToHorses()

        self.tableTo = TableViewAndModel(colDict, colorDict, (100, 300), qryTo)
        self.tableTo.setObjectName('TableTo')
        self.tableTo.clicked.connect(self.enableTransfers)
        self.tableTo.clicked.connect(self.tableClicked)
        self.tableTo.doubleClicked.connect(self.transferHorse)
        self.tableTo.doubleClicked.connect(self.enableSave)

    def createTemporaryTables(self):
        try:
            self.tempDb = self.db.cloneDatabase(self.db, "Temp")
            self.tempDb.open()
            qry = QSqlQuery(self.tempDb)
            qry.prepare("""CREATE TEMPORARY TABLE IF NOT EXISTS table1 AS 
            (SELECT 
            h.id,
            h.rp,
            h.name,
            CASE 
                WHEN h.sexid = 1 THEN _ucs2 X'2642'
                WHEN h.sexid = 2 THEN _ucs2 X'2640'
                WHEN h.sexid = 3 THEN _ucs2 X'265E'
            END Sex,
            c.coat
            FROM horses h
            INNER JOIN agreementhorses ah
            ON h.id = ah.horseid
            INNER JOIN sexes s
            ON h.sexid = s.id
            INNER JOIN coats c
            ON h.coatid = c.id 
            LIMIT 1)
            """)
            qry.exec()
            if qry.lastError().type() != 0:
                raise DataError("createTemporaryTable", qry.lastError().text())
            qryAlter = QSqlQuery(self.tempDb)
            qryAlter.exec("ALTER TABLE table1 ADD COLUMN transferdetailid TINYINT(5) NULL DEFAULT NULL AFTER coat")
            if qry.lastError().type() != 0:
                raise DataError("alterTemporaryTable-First", qry.lastError().text())
            qryAlter.exec("ALTER TABLE table1 ADD COLUMN agreementhorseid TINYINT(5) NOT NULL AFTER transferdetailid")
            if qry.lastError().type() != 0:
                raise DataError("alterTemporaryTable", qry.lastError().text())
            qryTo = QSqlQuery(self.tempDb)
            qryTo.exec("""CREATE TEMPORARY TABLE IF NOT EXISTS table2 AS 
            (SELECT id, name, rp, sex, coat, transferdetailid, agreementhorseid  FROM table1 LIMIT 1)""")
            if qryTo.lastError().type() != 0:
                raise DataError("createTemporaryTable", qryTo.lastError().text())
            qryTruncate = QSqlQuery(self.tempDb)
            qryTruncate.exec("TRUNCATE table1")
            qryTruncate.exec("TRUNCATE table2")
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print(type(err).__name__, err.args)

    def getDrivers(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("""SELECT id, fullname FROM contacts WHERE driver
                         ORDER BY fullname;""")
            if qry.lastError().type() != 0:
                raise DataError('getDrivers', qry.lastError().text())
            return qry

        except DataError as err:
            print(err.source, err.message)

    def fromLocations(self):
        try:
            qry = QSqlQuery(self.db)
            qry.prepare("""
                SELECT id, name, main , contactId
                FROM locations 
                WHERE contactid = 0 
                OR contactid = ?
                ORDER BY name""")
            qry.addBindValue(QVariant(self.supplierId))
            qry.exec()
            if qry.lastError().type() != 0:
                raise DataError('fromLocations', qry.lastError().text())
            modelFrom = QSqlQueryModel()
            modelFrom.setQuery(qry)
            return modelFrom
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def setDirty(self):
        self.isDirty = True

    @pyqtSlot()
    def deleteTransfer(self):
        """Must delete the transfer from transfers, all records from transferdetail, reset horses loacationid, and if
        original from location is main, look for set null for  start date (dos) in agreementhorses"""
        res = QMessageBox.question(self, "DELETE TRANSFER", "Confirm deleting transfer?",QMessageBox.Yes|QMessageBox.No)
        if res == QMessageBox.No :
            return
        try:
            cnn= pymysql.connect(**self.con_string)
            cnn.begin()
            with cnn.cursor() as cur:
                """Deletes the transfer"""
                sqlTransfer = """DELETE FROM transfers 
                    WHERE id = %s"""
                param = (self.transferRecord.value(0))
                cur.execute(sqlTransfer, param)

                sqlDetail = """DELETE FROM transferdetail 
                    WHERE transferid = %s"""

                sqlHorses = """UPDATE horses 
                    SET locationid = %s 
                    WHERE id = %s """

                sqlStart = """UPDATE agreementhorses ah
                        SET dos = Null
                       WHERE id = %s 
                       AND dos = %s"""
                self.qryHorses.seek(-1)
                while self.qryHorses.next():
                    paramDetail = (self.qryHorses.value(5))
                    paramHorses = (self.comboFrom.getHiddenData(0), self.qryHorses.value(0))
                    cur.execute(sqlDetail, paramDetail)
                    cur.execute(sqlHorses, paramHorses)
                    if self.comboFrom.getHiddenData(2) == 0:
                        paramStart = (self.qryHorses.value(6), self.originalDate.toString("yyyy-MM-dd"))
                        cur.execute(sqlStart, paramStart)
                        if cur.rowcount > 0:
                            sql_look_ahead = """SELECT t.date , ah.id
                                                FROM transfers t 
                                                INNER JOIN transferdetail td 
                                                ON t.id = td.transferid 
                                                INNER JOIN agreementhorses ah
                                                ON td.horseid = ah.horseid
                                                WHERE t.date > %s 
                                                AND td.horseid = %s
                                                AND ah.id = %s """
                            paramLook = (self.originalDate.toString("yyyy-MM-dd"), self.deleted[i][0],
                                         self.deleted[i][2])
                            cur.execute(sql_look_ahead, paramLook)
                            if cur.rowcount > 0:
                                row = cur.fetchone()
                                sql_next = """UPDATE agreementhorses 
                                                                        SET dos = %s 
                                                                        WHERE id = %s"""
                                paramNext = (row[0], self.deleted[i][2])
                                cur.execute(sql_next, paramNext)
                                if cur.rowcount > 0:
                                    print("Success")

                ans = QMessageBox.question(self, "Confirmation",
                                               "Deleted records can't be restored. Do you really want to delete "
                                                "transfer dated '{}' from '{}' to '{}'".format(
                                                   self.transferRecord.value(1).toString("MM-dd-yyyy"),
                                               self.transferRecord.value(3), self.transferRecord.value(4)),
                                               QMessageBox.Yes|QMessageBox.No)
                if ans == QMessageBox.No:
                    cnn.rollback()
                    return
            cnn.commit()
        except pymysql.Error as err:
            print('saveAndClose',err.args)
            cnn.rollback()
        except Exception as err:
            print("SaveAndClose", type(err).__name__, err.args)
            cnn.rollback()
        finally:
            cnn.close()
            self.closeForm()

    @pyqtSlot()
    def loadToHorses(self):
        try:
            if not self.tempDb.isOpen():
                self.tempDbdb.open()
            qryInsert = QSqlQuery(self.tempDb)
            qryInsert.prepare("""INSERT INTO table2
                                (id, rp, name, sex, coat, transferdetailid, agreementhorseid) 
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                                """)
            self.qryHorses.seek(-1)
            while self.qryHorses.next():
                qryInsert.addBindValue(QVariant(self.qryHorses.value(0)))
                qryInsert.addBindValue(QVariant(self.qryHorses.value(1)))
                qryInsert.addBindValue(QVariant(self.qryHorses.value(2)))
                qryInsert.addBindValue(QVariant(self.qryHorses.value(3)))
                qryInsert.addBindValue(QVariant(self.qryHorses.value(4)))
                qryInsert.addBindValue(QVariant(self.qryHorses.value(5)))
                qryInsert.addBindValue(QVariant(self.qryHorses.value(6)))
                qryInsert.exec()
                if qryInsert.lastError().type() != 0:
                    raise DataError('loadFromHorses', qryInsert.lastError().text())
            qryResult = QSqlQuery(self.tempDb)
            qryResult.exec("""SELECT id, rp, name, sex, coat,transferdetailid, agreementhorseid FROM  table2 ORDER BY sex, name""")
            if qryResult.lastError().type()!= 0:
                raise DataError('loadToHorses', qryResult.lastError().text())
            return qryResult
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def loadToLocations(self):
        try:
            qry = QSqlQuery(self.db)
            qry.prepare("""
                SELECT id, name
                FROM locations 
                WHERE (contactid = 0 
                OR contactid = ?)
                AND id  != ?
                ORDER BY name""")
            qry.addBindValue(QVariant(self.supplierId))
            qry.addBindValue(QVariant(self.comboFrom.getHiddenData(0)))
            qry.exec()
            if qry.lastError().type() != 0:
                raise DataError('loadToLocations', qry.lastError().text())
            if qry.size() == 0:
                raise DataError("LoadToLocations","{} must have at least one location".format(
                    self.parent.supplier))
            modelTo = QSqlQueryModel()
            modelTo.setQuery(qry)
            self.comboTo.setModel(modelTo)
            return modelTo
        except DataError as err:
            print(err.source, err.message)
            raise DataError(err.source, err.message)

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
            self.comboTo.currentIndex() >= 0 and \
            self.tableFrom.model().query().size() > 0 :
            okToTransfer = True
        self.pushLoad.setEnabled(okToTransfer)
        if self.tableTo.model().query().size()> 0 and okToTransfer:
            self.pushUnload.setEnabled(True)
            okToDelete = True
        self.okTransfers = [okToTransfer, okToDelete]

    @pyqtSlot()
    def loadFromHorses(self):
        try:
            qry = self.getQueryFrom()
            qry.seek(-1)
            qryTruncate = QSqlQuery(self.tempDb)
            qryTruncate.exec("Truncate table1")
            qryTruncate.exec("Truncate table2")
            qryInsert = QSqlQuery(self.tempDb)

            qryInsert.prepare("""INSERT INTO table1
                    (id, rp, name, sex, coat, transferdetailid, agreementhorseid) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """)
            while qry.next():
                qryInsert.addBindValue(QVariant(qry.value(0)))
                qryInsert.addBindValue(QVariant(qry.value(1)))
                qryInsert.addBindValue(QVariant(qry.value(2)))
                qryInsert.addBindValue(QVariant(qry.value(3)))
                qryInsert.addBindValue(QVariant(qry.value(4)))
                qryInsert.addBindValue(QVariant(None))
                qryInsert.addBindValue((QVariant(qry.value(5))))
                qryInsert.exec()
                if qryInsert.lastError().type() != 0 :
                    raise DataError('loadFromHorses', qryInsert.lastError().text())
            qryResult = QSqlQuery(self.tempDb)
            qryResult.exec("""SELECT id, rp, name, sex, coat,
             transferdetailid, agreementhorseid FROM  table1 ORDER BY sex, name""")
            self.tableFrom.model().setQuery(qryResult)
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print(type(err).__name__, err.args)

    def getQueryFrom(self):
        try:
            locationId = self.comboFrom.getHiddenData(0)
            contactId= self.comboFrom.getHiddenData(3)
            if self.isVisible():
                locationToId = self.comboTo.getHiddenData(0)
                self.toHome = self.lookForHome(locationToId)
            qry = QSqlQuery(self.db)
            sql_string = """SELECT 
                h.id,
                h.rp,
                h.name,
                CASE 
                    WHEN h.sexid = 1 THEN _ucs2 X'2642'
                    WHEN h.sexid = 2 THEN _ucs2 X'2640'
                    WHEN h.sexid = 3 THEN _ucs2 X'265E'
                END Sex,
                c.coat,
                ah.id
                FROM horses h
                INNER JOIN coats c
                ON h.coatid = c.id
                INNER JOIN agreementhorses ah
                ON h.id = ah.horseid
                INNER JOIN agreements a
                ON ah.agreementId = a.id
                WHERE h.locationid = ?
                AND a.supplierid = ?
                AND ah.billable 
                """
            if self.toHome:
                sql_string += " OR (NOT ah.BILLABLE AND ah.active)"
            qry.prepare(sql_string)
            qry.addBindValue(QVariant(locationId))
            qry.addBindValue(QVariant(self.supplierId))
            qry.exec()
            if qry.lastError().type() != 0:
                raise DataError('getQueryFrom', qry.lastError().text())
            return qry
        except DataError as err:
            print('getQueryFrom', qry.lastError().text())

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
            qryInsert = QSqlQuery(self.tempDb)
            qryDelete = QSqlQuery(self.tempDb)
            if sender.objectName() == 'TableFrom' or \
                    sender.objectName() == 'ToolRight' or \
                    sender.objectName() == 'Load':
                row = self.tableFrom.currentIndex().row()
                qry = self.tableFrom.model().query()
                qry.seek(row)
                if self.mode == OPEN_EDIT:
                    #The horse was in the original list
                    self.qryHorses.seek(-1)
                    isInFile = False
                    while self.qryHorses.next():
                        if self.qryHorses.value(0) == qry.value(0):
                            isInFile = True
                    if isInFile:
                        deleted = [self.deleted[x][0] for x in range(len(self.deleted))]
                        if qry.value(0) in deleted:
                            [self.deleted.remove(self.deleted[x]) for x in range(len(self.deleted)) if
                             self.deleted[x][0] == qry.value(0)]
                    else:
                        if not qry.value(0) in self.inserted:
                            self.inserted.append(qry.value(0))
                qryInsert.prepare(""" INSERT INTO table2 
                        (id, rp, name, sex, coat, transferdetailid, agreementhorseid) 
                        values (?, ?, ?, ?, ?, ?, ?)""")
                qryInsert.addBindValue(QVariant(qry.value(0)))
                qryInsert.addBindValue(QVariant(qry.value(1)))
                qryInsert.addBindValue(QVariant(qry.value(2)))
                qryInsert.addBindValue(QVariant(qry.value(3)))
                qryInsert.addBindValue(QVariant(qry.value(4)))
                if qry.value(5) == b'\x00' :
                    qryInsert.addBindValue(QVariant(None))
                else:
                    qryInsert.addBindValue(QVariant(qry.value(5)))
                qryInsert.addBindValue(QVariant(qry.value(6)))
                qryInsert.exec()
                if qryInsert.lastError().type() != 0:
                    raise DataError('Insert From', qryInsert.lastError().text())

                qryDelete.prepare("""DELETE FROM table1 
                        WHERE id = ? """)
                qryDelete.addBindValue(QVariant(qry.value(0)))
                qryDelete.exec()
                if qryDelete.lastError().type() != 0:
                    raise DataError('Delete From', qryDelete.lastError().text())
            else:
                qry = self.tableTo.model().query()
                row = self.tableTo.currentIndex().row()
                qry.seek(row)
                if self.mode == OPEN_EDIT:
                    self.qryHorses.seek(-1)
                    isInFile = False
                    while self.qryHorses.next():
                        if self.qryHorses.value(0) == qry.value(0):
                           isInFile = True
                           break
                    if isInFile:
                        #The horse was in the original list
                        if qry.value(0) not in self.deleted:
                            self.deleted.append((qry.value(0), qry.value(5), qry.value(6)))
                    else:
                        if qry.value(0) in self.inserted:
                            self.inserted.remove(qry.value(0))
                qryInsert.prepare(""" INSERT INTO table1 
                                (id, rp, name, sex, coat, transferdetailid, agreementhorseid) 
                                values (?, ?, ?, ?, ?,?, ?)""")
                qryInsert.addBindValue(QVariant(qry.value(0)))
                qryInsert.addBindValue(QVariant(qry.value(1)))
                qryInsert.addBindValue(QVariant(qry.value(2)))
                qryInsert.addBindValue(QVariant(qry.value(3)))
                qryInsert.addBindValue(QVariant(qry.value(4)))
                if qry.value(5) == b'\x00' :
                    qryInsert.addBindValue(QVariant(None))
                else:
                    qryInsert.addBindValue(QVariant(qry.value(5)))
                qryInsert.addBindValue(QVariant(qry.value(6)))
                qryInsert.exec()
                if qryInsert.lastError().type() != 0:
                    raise DataError('Insert To', qryInsert.lastError().text())

                qryDelete.prepare("""DELETE FROM table2 
                                WHERE id = ? """)
                qryDelete.addBindValue(QVariant(qry.value(0)))
                qryDelete.exec()
                if qryDelete.lastError().type() != 0:
                    raise DataError('Delete to', qryDelete.lastError().text())

            #update the tables
            qryFrom = QSqlQuery(self.tempDb)
            qryFrom.exec("""SELECT id, rp, name, sex, coat, transferdetailid, agreementhorseid FROM table1
             ORDER BY sex, name""")
            if qryFrom.lastError().type() != 0:
                raise DataError('Update From', qryFrom.lastError().text())
            self.tableFrom.model().setQuery(qryFrom)

            qryTo = QSqlQuery(self.tempDb)
            qryTo.exec("""SELECT id, rp, name, sex, coat, transferdetailid , agreementhorseid FROM table2
             ORDER BY sex, name""")
            if qryTo.lastError().type() != 0:
                raise DataError('Update to', qryTo.lastError().text())
            self.tableTo.model().setQuery(qryTo)

        except DataError as err:
                    print(err.source, err.message)
        except Exception as err:
            if type(err) == IndexError:
                res = QMessageBox.warning(self, "Horse not Selected", "Select the horse to be "
                                                                      "tranfered",QMessageBox.Ok)
            else:
                print("transferHorse", type(err).__name__, err.args)

    def lookForHome(self, locationToId):
        try:
            qryLook = QSqlQuery(self.db)
            qryLook.prepare("""SELECT true WHERE 
            EXISTS (SELECT id FROM locations WHERE id = ? AND contactid = 0) """)
            qryLook.addBindValue(QVariant(locationToId))
            qryLook.exec()
            if qryLook.lastError().type()!= 0:
                raise DataError('lookForHome', qryLook.lastError().text())
            qryLook.first()
            return qryLook.value(0)
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def saveAndClose(self):
        #if the base location is sending
        checkStart = False
        if int(self.comboFrom.getHiddenData(3)) == 0 :
            checkStart = True
        try:
            cnn = pymysql.connect(**self.con_string)
            cnn.begin()
            with cnn.cursor() as cur:
                if self.mode == OPEN_NEW:
                    qry = self.tableTo.model().query()
                    #Saves the main transaction
                    sql_transfer = """INSERT INTO transfers
                            (date, driverid, fromid, toid, supplierid)
                            VALUES (%s, %s, %s, %s, %s)"""
                    parameters = (self.dateDate.date().toString("yyyy-MM-dd"),
                                  self.comboDriver.getHiddenData(0) if self.comboDriver.getHiddenData(0) else None,
                                  self.comboFrom.getHiddenData(0),
                                  self.comboTo.getHiddenData(0),
                                  self.supplierId)
                    cur.execute(sql_transfer, parameters)
                    lastId = cur.lastrowid
                    #saves the transfered horses

                    sql_transfer_detail = """INSERT INTO transferdetail  
                        (agreementhorseid, transferid) 
                        VALUES (%s,%s)"""

                    sql_horse_update = """ UPDATE `horses` 
                                            SET `locationid` = %s
                                            WHERE `id` = %s """

                    sql_start_update = """ UPDATE `agreementhorses` 
                                                    SET  `dos`= %s 
                                                    WHERE `dos` IS NULL 
                                                    AND `id` = %s """
                    sql_toHome_update = """UPDATE agreementhorses
                                            SET active = False 
                                            WHERE id = %s 
                                            AND NOT billable"""
                    qry.seek(-1)
                    while qry.next():
                        paramdetail = (qry.value(6), lastId)
                        param_update = (self.comboTo.getHiddenData(0),qry.value(0))
                        cur.execute(sql_transfer_detail, paramdetail)
                        cur.execute(sql_horse_update, param_update)
                        if checkStart:
                            param_start = (self.dateDate.date().toString("yyyy-MM-dd"), qry.value(6))
                            cur.execute(sql_start_update, param_start)
                        if self.toHome:
                            param_toHome = (qry.value(6),)
                            cur.execute(sql_toHome_update, param_toHome)
                else:
                    #Edit mode
                    if self.isDirty:
                        """Updates the transfer record"""
                        sqlUpdate = """UPDATE transfers 
                            SET date = %s, driverid = %s 
                            WHERE id = %s """
                        param = (self.dateDate.date().toString("yyyy-MM-dd"),
                                     self.comboDriver.getHiddenData(0),
                                     self.transferRecord.value(0))
                        cur.execute(sqlUpdate, param)
                    if len(self.deleted) > 0:
                        """Must delete horses from transferdetail, update location in horses
                        and try to figure out the start Date situation (check the dates)"""
                        sqlDelete = """DELETE FROM transferdetail 
                            WHERE id = %s """

                        sqlStart = """UPDATE agreementHorses 
                        SET dos = NULL 
                        WHERE id = %s
                        AND dos = %s """

                        sqlHorses = """UPDATE horses 
                            SET locationid = %s 
                            WHERE id = %s"""

                        for i in range(len(self.deleted)):
                            """check Deletes withdrawn horses, looks for starting date and update to null
                            if date similar to """
                            paramHorses = (self.comboFrom.getHiddenData(0), self.deleted[i][0])
                            paramDelete = (self.deleted[i][1])
                            cur.execute(sqlHorses, paramHorses)
                            cur.execute(sqlDelete, paramDelete)
                            if checkStart:
                                paramStart = (self.deleted[i][2], self.originalDate.toString("yyyy-MM-dd"))
                                cur.execute(sqlStart, paramStart)
                                if cur.rowcount > 0:
                                    #method checking for existence of agreementhorse further up the date, and update
                                    #the dos date with the first occurrence (date > currentDate, From Location = 0 and
                                    # location belonging to this supplier.
                                    #reproduce also on delete transfer--
                                    sql_look_ahead = """SELECT t.date , ah.id
                                        FROM transfers t 
                                        INNER JOIN transferdetail td 
                                        ON t.id = td.transferid 
                                        INNER JOIN agreementhorses ah
                                        ON td.horseid = ah.horseid
                                        WHERE t.date > %s 
                                        AND td.horseid = %s
                                        AND ah.id = %s """
                                    paramLook = (self.originalDate.toString("yyyy-MM-dd"), self.deleted[i][0],
                                                 self.deleted[i][2])
                                    cur.execute(sql_look_ahead, paramLook)
                                    if cur.rowcount > 0:
                                        row = cur.fetchone()
                                        sql_next = """UPDATE agreementhorses 
                                            SET dos = %s 
                                            WHERE id = %s"""
                                        paramNext = (row[0], self.deleted[i][2])
                                        cur.execute(sql_next, paramNext)
                                        if cur.rowcount > 0:
                                            print("Success")
                    if len(self.inserted) > 0:
                        """must insert this records into the transferdetail table;
                        check if the horse is started and if not do it; and 
                        update the horse table with nhe new location"""

                        sqlInsert = """INSERT INTO transferdetail 
                            (horseid, transferid) 
                            VALUES (%s, %s) """

                        sqlStarted = """UPDATE agreementhorses ah
                            INNER JOIN agreements a
                            ON ah.agreementid = a.id
                            SET  ah.dos = %s 
                            WHERE ah.active = 1 
                            AND ah.horseid = %s 
                            AND a.supplierid = %s 
                            AND ah.dos IS NULL 
                            ;"""

                        sqlUpdate = """UPDATE horses 
                            SET locationid = %s  
                            WHERE id = %s"""

                        for i in range(len(self.inserted)):
                            paramInsert = (self.inserted[i], self.transferRecord.value(0))
                            paramUpdate = (self.comboTo.getHiddenData(0), self.inserted[i])
                            cur.execute(sqlInsert,paramInsert)
                            cur.execute(sqlUpdate, paramUpdate)
                            if checkStart:
                                paramStart = (self.dateDate.date().toString("yyyy-MM-dd"),
                                              self.inserted[i], self.supplierId)
                                cur.execute(sqlStarted, paramStart)
                if self.mode == OPEN_EDIT:
                    strUpdate = "Do you really want to update the  "\
                                           "transfer dated '{}' from '{}' to '{}'".format(
                                               self.transferRecord.value(1).toString("MM-dd-yyyy"),
                                self.comboFrom.currentText(), self.comboTo.currentText())
                    if len(self.inserted) > 0:
                        strUpdate += " adding {} horses to the transfer". format(len(self.inserted))
                    if len(self.deleted) > 0:
                        strUpdate += " removing {} horses from the transfer". format(len(self.deleted))
                strMessage = "Save the transference?" if self.mode == OPEN_NEW else strUpdate

                ans = QMessageBox.question(self, "Confirmation",
                                           strMessage,QMessageBox.Yes | QMessageBox.No)
                if ans == QMessageBox.No:
                    cnn.rollback()
                    return
                cnn.commit()
        except pymysql.Error as err:
            print('saveAndClose',err.args)
            cnn.rollback()
        except Exception as err:
            print("SaveAndClose", type(err).__name__, err.args)
            cnn.rollback()
        finally:
            cnn.close()
            self.closeForm()

    @pyqtSlot()
    def tableClicked(self):
        if self.okTransfers[0]:
            activate = False
            if self.sender().objectName() == 'TableFrom':
                activate = True
            self.toolRight.setEnabled(activate)
            self.toolLeft.setEnabled(not activate)

class EditTransfer(QDialog):
    """List all the transfer for a particular supplier on two tables, the transfer list and the
    horses associated on the scond tables witch is updated as the selection changes on the first table.
    When doubleclicking on the transference list the "Transfer form will open for editing or deletnng"""
    def __init__(self, db, supplierId, parent = None):
        super().__init__()
        try:
            self.db = db
            if not self.db.isOpen():
                self.db.open()
            self.supplierId = supplierId
            self.parent = parent
            self.setUI()
        except DataError as err:
            return

    def setUI(self):
        self.setModal(True)
        self.setWindowTitle("Horse Transfers " + self.parent.supplier)
        self.setMinimumWidth(680)
        self.setMinimumHeight(500)

        lblToDate = QLabel('To Date: ')
        self.dateTo = NullDateEdit(self)
        #self.dateTo.setDate(None)
        self.dateTo.dateEdit.setCalendarPopup(True)
        self.dateTo.setMinimumWidth(120)
        self.dateTo.clearDate()

        lblFromDate = QLabel('From Date: ')
        self.dateFrom = NullDateEdit(self)
        #self.dateFrom.setDate(None)
        self.dateFrom.dateEdit.setCalendarPopup(True)
        self.dateFrom.setMinimumWidth(120)
        self.dateFrom.setMinimumDate(QDate.currentDate().addYears(-3))
        self.dateFrom.dateChanged.connect(self.setToDate)
        self.dateFrom.clearDate()

        lblFromLocation = QLabel('From Location:')
        self.comboFrom = FocusCombo()
        self.comboFrom.setModel(QSqlQueryModel())
        self.comboFrom.model().setQuery(self.getFromLocations())
        self.comboFrom.setModelColumn(1)
        self.comboFrom.activated.connect(self.getToLocations)

        lblToLocation = QLabel('To Location:')
        self.comboTo = FocusCombo()
        self.comboTo.setModel(QSqlQueryModel())
        self.comboTo.model().setQuery(self.getToLocations())
        self.comboTo.setModelColumn(1)

        pushOk = QPushButton('Cancel')
        pushOk.clicked.connect(self.closeWidget)
        pushOk.setMaximumSize(100, 25)

        pushClose = QPushButton("Close transfer")
        pushClose.setStatusTip("Closes the transfer")
        pushClose.clicked.connect(self.closeTransfer)
        pushClose.setMaximumSize(125,25)

        pushEdit = QPushButton("Edit")
        pushEdit.setStatusTip("Edit/Delete the current transaction")
        pushEdit.clicked.connect(self.editTransfer)
        pushEdit.setMaximumSize(100, 25)

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(pushClose)
        buttonLayout.addWidget(pushEdit)
        buttonLayout.addWidget(pushOk)

        pushClearFilters = QToolButton()
        pushClearFilters.setIcon(QIcon(":Icons8/Edit/reset.png"))
        pushClearFilters.clicked.connect(self.clearFilters)
        pushClearFilters.setMaximumSize(100,25)

        pushSearch = QToolButton()
        pushSearch.setIcon(QIcon(":Icons8/Edit/search.png"))
        pushSearch.clicked.connect(self.searchFilters)
        pushSearch.setMaximumSize(100,25)
        pushSearch.clicked.connect(self.setFiltersOn)

        self.groupState = QGroupBox("State")
        self.groupState.setAlignment(Qt.AlignHCenter)
        self.groupState.setCheckable(True)
        self.groupState.clicked.connect(self.disableState)

        self.checkClose = QCheckBox('Closed',self.groupState )
        self.checkClose.clicked.connect(self.checkState)
        self.checkOpen = QCheckBox('Open',self.groupState )
        self.checkOpen.clicked.connect(self.checkState)
        self.checkAll = QCheckBox('All',self.groupState)
        self.checkAll.clicked.connect(self.checkState)

        stateLayout = QVBoxLayout()
        stateLayout.addWidget(self.checkAll)
        stateLayout.addWidget(self.checkOpen)
        stateLayout.addWidget(self.checkClose)

        self.groupState.setLayout(stateLayout)

        groupFilters = QGroupBox("Filters")
        groupFilters.setAlignment(Qt.AlignHCenter)

        filtersLayout = QGridLayout()
        filtersLayout.addWidget(self.groupState,0,0,2,1)
        filtersLayout.addWidget(lblFromDate, 0, 1)
        filtersLayout.addWidget(self.dateFrom,0,2)
        filtersLayout.addWidget(lblToDate, 0, 3)
        filtersLayout.addWidget(self.dateTo, 0,4)
        filtersLayout.addWidget(pushClearFilters,0,5)
        filtersLayout.addWidget(lblFromLocation,1,1)
        filtersLayout.addWidget(self.comboFrom,1,2)
        filtersLayout.addWidget(lblToLocation,1,3)
        filtersLayout.addWidget(self.comboTo,1,4)
        filtersLayout.addWidget(pushSearch,1,5)

        groupFilters.setLayout(filtersLayout)

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

        qryHorses = self.getHorses(transferId)
        colorDict = {}
        colDict = {
            0: ("ID", True, True, False, None),
            1: ("RP", False, True, True, None),
            2: ("Horse", False, False, False, None),
            3: ("Sex", False, True, True, None),
            4: ("Coat", False, True, False, None),
            5: ("Detailid", True, True, False, None),
            6: ("ahid", True, True, True, False, None)}
        self.tableHorses = TableViewAndModel(colDict, colorDict, (100, 200), qryHorses)
        self.tableHorses.setMinimumWidth(350)


        tableLayout = QHBoxLayout()
        tableLayout.addWidget(self.tableTransfers)
        tableLayout.addWidget(self.tableHorses)
        vLayout = QVBoxLayout()

        vLayout.addLayout(tableLayout)
        vLayout.addWidget(groupFilters)
        vLayout.addLayout(buttonLayout)
        self.setLayout(vLayout)

    def getFromLocations(self):
        try:
            qry = SQL_Query(self.db)
            qry.prepare("""SELECT DISTINCT l.id, l.name 
                FROM locations l
                WHERE EXISTS (SELECT t.fromid 
                    FROM transfers t 
                    WHERE t.fromid = l.id)
                AND (l.contactid = ? OR l.contactid = 0);""")
            qry.addBindValue(QVariant(self.supplierId))
            qry.exec()
            if qry.lastError().type() != 0:
                raise DataError('getFromLocations', qry.lastError().text())
            return qry
        except DataError as err:
            print(err.source, err.message)

    def getToLocations(self):
        try:
            qry = SQL_Query(self.db)
            sql_str = """SELECT DISTINCT l.id, l.name 
                 FROM locations l
                 WHERE EXISTS (SELECT t.toid 
                     FROM transfers t 
                     WHERE t.toid = l.id)
                 AND (l.contactid = ? OR l.contactid = 0)"""
            if self.comboFrom.currentIndex() != -1:
                sql_str += " AND l.id != ? "
            sql_str += " ORDER BY l.name"
            qry.prepare(sql_str)
            qry.addBindValue(QVariant(self.supplierId))
            if self.comboFrom.currentIndex() != -1:
                qry.addBindValue(QVariant(self.comboFrom.getHiddenData(0)))
            qry.exec()
            if qry.lastError().type() != 0:
                raise DataError('getFromLocations', qry.lastError().text())
            self.comboTo.model().setQuery(qry)
            return qry
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def setFiltersOn(self):
        str_between = ''
        str_date = ''
        str_from = ''
        str_to = ''
        str_state = ''
        filterDict = {'dateFrom': None, 'dateTo': None, 'From' : None, 'To' : None, 'Closed' : None}
        if self.dateFrom.date > self.dateFrom.minimumDate :
            if self.dateTo.date > self.dateTo.minimumDate:
                str_between = " AND (date BETWEEN ? AND ?) "
                filterDict['dateFrom'] = self.dateFrom.date.toString("yyyy-MM-dd")
                filterDict['dateTo'] = self.dateTo.date.toString("yyyy-MM-dd")
            else:
                if self.dateFrom.date > self.dateFrom.minimumDate:
                    str_date = "AND date >= ? "
                    filterDict['dateFrom'] = self.dateFrom.date.toString("yyyy-MM-dd")
        if self.comboFrom.currentIndex() != -1:
            str_from = "AND fromid = ? "
            filterDict['From'] = self.comboFrom.getHiddenData(0)
        if self.comboTo.currentIndex() != -1:
            str_to = "AND toid = ? "
            filterDict['To'] = self.comboTo.getHiddenData(0)
        if self.groupState.isChecked():
            if self.checkClose.isChecked():
                str_state = " AND closed = ? "
                filterDict['Closed'] = True
            if self.checkOpen.isChecked():
                str_state = " AND closed = ? "
                filterDict['Closed'] = False

        str_where = str_between + str_date + str_from + str_to + str_state
        qry = self.getTransfers((str_where, filterDict))
        self.tableTransfers.model().setQuery(qry)
        self.clearFilters()

    def getTransfers(self, filter=None):
        try:
            qry = SQL_Query(self.db)
            sql_string = """SELECT
                t.id,
                t.date,
                t.driverid,
                l.name,
                l1.name,
                if (t.closed = 1, _ucs2 x'2714', ''),
                if (t.active = 1, _ucs2 x'2714', ''),
                t.fromid,
                t.toid
                FROM transfers t
                INNER JOIN locations l
                ON t.fromid = l.id
                INNER JOIN locations l1
                ON t.toid = l1.id 
                WHERE t.supplierid = ? 
                """
            if filter:
                sql_string += filter[0]
            sql_string += "ORDER BY t.date DESC"
            qry.prepare(sql_string)
            qry.addBindValue(QVariant(self.supplierId))
            if filter:
                if filter[1]['dateFrom']:
                    qry.addBindValue(QVariant(filter[1]['dateFrom']))
                if filter[1]['dateTo']:
                    qry.addBindValue(QVariant(filter[1]['dateTo']))
                if filter[1]['From']:
                    qry.addBindValue(QVariant(filter[1]['From']))
                if filter[1]['To']:
                    qry.addBindValue(QVariant(filter[1]['To']))
                if filter[1]['Closed'] is not None:
                    qry.addBindValue(QVariant(filter[1]['Closed']))
            qry.exec()
            if qry.lastError().type() != 0:
                raise DataError('getTransfers', qry.lastError().text())
            qry.first()
            return qry
        except DataError as err:
            print(err.source, err.message)


    def getHorses(self, transferId):
        try:
            qry = SQL_Query(self.db)
            qry.prepare("""SELECT 
                h.id, h.rp, h.name,
                CASE 
                    WHEN h.sexid = 1 THEN _ucs2 X'2642'
                    WHEN h.sexid = 2 THEN _ucs2 X'2640'
                    WHEN h.sexid = 3 THEN _ucs2 X'265E'
                END Sex,
                c.coat,
                td.id,
                ah.id
                FROM horses h
                INNER JOIN agreementhorses ah
                ON h.id = ah.horseid
                INNER JOIN transferdetail td
                ON ah.id = td.agreementhorseid
                INNER JOIN coats c
                ON h.coatid = c.id
                WHERE td.transferid = ?
                ORDER BY h.name 
                """)
            qry.addBindValue(QVariant(transferId))
            qry.exec()
            if qry.lastError().type() != 0:
                raise DataError('getHorses', qry.lastError().text())
            return qry

        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print(err.args)

    @pyqtSlot()
    def transferChanged(self):
        try:
            qry = self.tableTransfers.model().query()
            row = self.tableTransfers.currentIndex().row()
            qry.seek(row)
            transferId = qry.value(0)
            qryHorses = self.getHorses(transferId)
            self.tableHorses.model().setQuery(qryHorses)

        except Exception as err:
            print(err.args)

    @pyqtSlot()
    def setToDate(self):
        self.dateTo.setMinimumDate(self.dateFrom.date)
        self.dateTo.setDate(QDate.currentDate())

    @pyqtSlot()
    def clearFilters(self):
        self.dateTo.clearDate()
        self.dateFrom.clearDate()
        self.comboFrom.setCurrentIndex(-1)
        self.comboTo.setCurrentIndex(-1)

    @pyqtSlot()
    def searchFilters(self):
        pass

    def closeWidget(self):
        self.close()

    @pyqtSlot()
    def closeTransfer(self):
        try:
            qry = self.tableTransfers.model().query()
            row = self.tableTransfers.currentIndex().row()
            if qry.seek(row):
                if qry.value(5) == u'\u2714':
                    QMessageBox.warning(self, "Transfer Closed", "This transfer have been closed already",
                                        QMessageBox.Ok)
                    return
                res = QMessageBox.question(self, 'Close Transfer',
                                           "Do you want to close the transfer dated on {} , "
                                           "From: {} To: {}".format(qry.value(1).toString("MM-dd-yyyy"),
                                                                    qry.value(3), qry.value(4)),QMessageBox.Yes|
                                           QMessageBox.No)
                if res == QMessageBox.Yes:
                    qryUpdate = QSqlQuery(db)
                    qryUpdate.prepare("""UPDATE transfers 
                        SET closed = True 
                        WHERE id = ? """)
                    qryUpdate.addBindValue(QVariant(qry.value(0)))
                    qryUpdate.exec()
                    if qryUpdate.lastError().type() != 0:
                        raise DataError('closeTransfer',qryUpdate.lastError().text())
                    qryNew = self.getTransfers()
                    self.tableTransfers.model().setQuery(qryNew)
        except DataError as err:
            print(err.source, err.message)


    @pyqtSlot()
    def editTransfer(self):
        try:
            qry = self.tableTransfers.model().query()
            row = self.tableTransfers.currentIndex().row()
            if qry.seek(row):
                if qry.value(5) == u'\u2714':
                    QMessageBox.warning(self,"Transfer Closed", "This transfer have been closed already",
                                        QMessageBox.Ok)
                    return
                res = QMessageBox.question(self, 'Close Transfer',
                                           "Do you want to edit the transfer dated on {} , "
                                           "From: {} To: {}".format(qry.value(1).toString("MM-dd-yyyy"),
                                                                    qry.value(3), qry.value(4)), QMessageBox.Yes |
                                           QMessageBox.No)
                if res == QMessageBox.Yes:
                    record = qry.record()
                    qryHorse = self.tableHorses.model().query()
                    res = Transfer(self.db, self.supplierId,OPEN_EDIT,
                                   self.parent.con_string,record,qryHorse, self.parent)
                    res.show()
                    res.exec()
                    self.resetWidgetData()

        except DataError as err:
            print(err.source, err.message)

    def resetWidgetData(self):
        qryTransfers = self.getTransfers()
        self.tableTransfers.model().setQuery(qryTransfers)
        self.tableTransfers.selectRow(0)
        self.tableTransfers.setFocus()
        self.transferChanged()

    @pyqtSlot()
    def checkState(self):
        sender = self.sender()
        if sender.isChecked():
            for checkBox in self.groupState.findChildren(QCheckBox):
                if checkBox != sender:
                    checkBox.setChecked(False)

    @pyqtSlot()
    def disableState(self):
        if self.groupState.isChecked():
            return
        for checkBox in self.groupState.findChildren(QCheckBox):
            checkBox.setChecked(False)


    @pyqtSlot()
    def enableSave(self):
        pass