import sys
import os
from PyQt5.QtWidgets import ( QDialog, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel, QLineEdit, QWidget,
                             QPushButton, QTableView, QMessageBox, QCheckBox, QComboBox,
                              QHeaderView, QAbstractItemView, QDateEdit, QTextEdit)
from PyQt5.QtCore import Qt, QSettings, pyqtSlot, QVariant, QDate
from PyQt5.QtGui import QStandardItemModel, QColor, QFont, QDoubleValidator, QIcon
from PyQt5.QtSql import QSqlQuery, QSqlQueryModel,QSqlDatabase
from ext.Settings import SettingsDialog
from ext import APM, Settings
from ext.APM import (FocusCombo, QSqlAlignColorQueryModel, PercentOrAmountLineEdit, Cdatabase,
REJECTION_TYPE_FINAL, REJECTION_TYPE_VETERINARY, REJECTION_TYPE_TRANSITORY, CLEARENCE_REASON_REJECT)
#from ext.CQSqlDatabase import Cdatabase
import pymysql
from configparser import ConfigParser

class QSqlAlignQueryModel(QSqlQueryModel):
    def __init__(self, centerColumns, mode=APM.CONTACT_ALL):
        super().__init__()
        self.type = mode
        self.centerColumns = centerColumns

    def data(self,idx, role=Qt.DisplayRole):
        try:
            if not idx.isValid() or \
                not(0<=idx.row() < self.query().size()):
                return QVariant()
            if self.query().seek(idx.row()):
                qry = self.query().record()
                if self.type == APM.CONTACT_ALL:
                    if role == Qt.DisplayRole:
                        return QVariant(qry.value(idx.column()))
                    elif role == Qt.TextAlignmentRole:
                        if idx.column() in self.centerColumns:
                            return QVariant(Qt.AlignCenter)
                        else:
                            return QVariant(Qt.AlignLeft)
                    elif role == Qt.TextColorRole:
                        if qry.value(9) == 1:
                            return QVariant(QColor(Qt.darkBlue))
                        elif qry.value(9) == 2:
                            return QVariant(QColor(Qt.red))
                        elif qry.value(9) == 3:
                            return QVariant(QColor(Qt.darkCyan))
                    elif role == Qt.BackgroundColorRole:
                        if qry.value(6) == u'\u2714':
                            return QVariant(QColor(Qt.white))
                        else:
                            return QVariant(QColor(Qt.yellow))
                elif self.type in [APM.CONTACT_PLAYER, APM.CONTACT_RESPONSIBLE, APM.CONTACT_BREAKER, APM.CONTACT_DEALER,
                              APM.CONTACT_BUYER]:
                    if role == Qt.DisplayRole:
                        return QVariant(qry.value(idx.column()))
                    elif role == Qt.TextAlignmentRole:
                        if idx.column() == 1:
                            return QVariant(Qt.AlignLeft)
                        else:
                            return QVariant(Qt.AlignCenter)
                    elif role == Qt.TextColorRole:
                        if qry.value(7):
                            return QVariant(QColor(Qt.darkBlue))
                        else:
                            return QVariant(QColor(Qt.white))
                    elif role == Qt.BackgroundColorRole:
                        if qry.value(7):
                            return QVariant(QColor(Qt.white))
                        else:
                            return QVariant(QColor(Qt.black))
                elif self.type in [APM.HORSE_INVENTORY, APM.HORSE_BREAKING, APM.HORSE_PLAYING]:
                    if role == Qt.DisplayRole:
                        return QVariant(qry.value(idx.column()))
                    elif role == Qt.TextAlignmentRole:
                        if idx.column() in self.centerColumns:
                            return QVariant(Qt.AlignCenter)
                    elif role == Qt.TextColorRole:
                        if not qry.value(9):
                            return QVariant(QColor(Qt.white))
                    elif role == Qt.BackgroundColorRole:
                        if not qry.value(9):
                            return QVariant(QColor(Qt.black))
                elif self.type in [APM.REPORT_TYPE_ALL_BREAKING_HORSES, APM.REPORT_TYPE_ALL_PLAYING_HORSES]:
                    if role == Qt.DisplayRole:
                        return QVariant(qry.value(idx.column()))
                    if role == Qt.TextAlignmentRole:
                        if idx.column() in self.centerColumns:
                            return QVariant(Qt.AlignHCenter)
                        return QVariant(Qt.AlignLeft)
                elif self.type == APM.REPORT_TYPE_ALL_HORSES:
                    if role == Qt.DisplayRole:
                        return QVariant(qry.value(idx.column()))
                    if role == Qt.TextAlignmentRole:
                        if idx.column() in self.centerColumns:
                            return QVariant(Qt.AlignHCenter)
                        return QVariant(Qt.AlignLeft)
        except Exception as err:
            print(type(err).__name__, err.args)

class Horses(QDialog):

    def __init__(self, db, mode=None, record=None, horseid = None, parent=None):
        super().__init__()
        self.parent = parent
        self.cdb = db
        self.record = record
        self.setModal(True)
        self.horseid = horseid
        self.mode = mode
        self.setUI()

    def setUI(self):
        self.setMinimumWidth(600)
        self.setMaximumWidth(700)
        lblName = QLabel("Name")
        self.lineName = QLineEdit()
        self.lineName.setToolTip("Horse Name")
        self.lineName.editingFinished.connect(self.enableSave)

        lblSex = QLabel("Sex")
        self.comboSex = FocusCombo()
        self.comboSex.setToolTip("Horse Sex")
        self.comboSex.setMaximumWidth(200)
        self.comboSex.activated.connect(self.enableSave)

        lblcoat = QLabel("Coat")
        self.comboCoat = FocusCombo()
        self.comboCoat.setToolTip("Horse Coat")
        self.comboCoat.setMaximumWidth(200)
        self.comboCoat.activated.connect(self.enableSave)

        self.loadCombos()

        lblBreaker = QLabel("Breaker")
        self.comboBreaker = FocusCombo()
        self.comboBreaker.setToolTip("Horse breaker")
        self.comboBreaker.setMaximumWidth(200)
        self.comboBreaker.setEnabled(False)
        self.comboBreaker.activated.connect(self.enableSave)
        self.comboBreaker.setObjectName('Breaker')
        self.comboBreaker.doubleClicked.connect(self.addBreaker)

        lblPlayer = QLabel("Player")
        self.comboPlayer = FocusCombo()
        self.comboPlayer.setToolTip("Horse player")
        self.comboPlayer.setMaximumWidth(200)
        self.comboPlayer.setEnabled(False)
        self.comboPlayer.activated.connect(self.enableSave)
        self.comboPlayer.setObjectName('Player')
        self.comboPlayer.doubleClicked.connect(self.addPlayer)

        lblLocation = QLabel('Location')
        self.comboLocation = FocusCombo(self)
        self.comboLocation.setMaximumWidth(200)
        self.comboLocation.setModel(QSqlQueryModel())
        self.comboLocation.model().setQuery(self.getLocations())
        self.comboLocation.setModelColumn(1)
        self.comboLocation.seekData(0,2)

        lblRp = QLabel("RP")
        self.lineRp = QLineEdit()
        self.lineRp.setToolTip("Horse RP  ")
        self.lineRp.setMaximumWidth(70)
        self.lineRp.editingFinished.connect(self.enableSave)

        self.pushSave = QPushButton("Save")
        self.pushSave.setMaximumWidth(60)
        self.pushSave.setEnabled(False)
        self.pushSave.clicked.connect(self.saveAndClose)

        self.pushDelete = QPushButton("Delete")
        self.pushDelete.setMaximumWidth(60)
        self.pushDelete.setVisible(False)
        self.pushDelete.clicked.connect(self.deleteHorse)

        pushCancel = QPushButton("Cancel")
        pushCancel.setMaximumWidth(60)
        pushCancel.clicked.connect(self.close)
        pushCancel.setFocus()

        lblDob = QLabel("Birth Date")
        self.date = APM.NullDateEdit(self)
        self.date.setToolTip("Date of Birth")
        self.date.setMinimumDate(QDate.currentDate().addYears(-10))
        self.date.setDate(QDate.currentDate().addYears(-5))

        lblDos = QLabel("Start Date")
        self.dateDos = APM.NullDateEdit(self)
        self.dateDos.setToolTip("Date of Start")
        self.dateDos.setMinimumDate(QDate.currentDate().addMonths(-6))
        self.dateDos.setDate(QDate.currentDate())

        self.checkBroke = QCheckBox("Broke")
        self.checkBroke.setToolTip("Is the horse broke")
        self.checkBroke.setEnabled(False)
        self.checkBroke.stateChanged.connect(self.enableSave)

        self.checkActive = QCheckBox("Active")
        self.checkActive.setToolTip("Weather the Horse is active")
        self.checkActive.setChecked(True)
        self.checkActive.setEnabled(False)
        self.checkActive.stateChanged.connect(self.enableSave)

        lblHorseBaseId = QLabel("Horsebase ID")
        self.lineHorseBaseId = QLineEdit()
        self.lineHorseBaseId.setMaximumWidth(50)
        self.lineHorseBaseId.editingFinished.connect(self.enableSave)

        self.lblState = QLabel("Closed")
        self.lblState.setMinimumWidth(80)
        self.lblState.setFont(QFont("Times", 9, QFont.Bold))
        self.lblState.setAlignment(Qt.AlignHCenter)
        self.lblState.setStyleSheet("QLabel {color : white;"
                                    " background-color: red;"
                                    "padding: 1px;"
                                    "border-radius: 15px;}")
        self.lblState.setVisible(False)

        hLayoutButtons = QHBoxLayout()
        hLayoutButtons.addWidget(self.pushDelete)
        hLayoutButtons.addWidget(self.lblState)
        hLayoutButtons.addSpacing(500)
        hLayoutButtons.addWidget(pushCancel)

        hLayoutAccessId = QHBoxLayout()
        hLayoutAccessId.addWidget(lblHorseBaseId)
        hLayoutAccessId.addWidget(self.lineHorseBaseId)

        hLayoutCheck = QHBoxLayout()
        hLayoutCheck.addWidget(self.checkBroke)
        hLayoutCheck.addWidget(self.checkActive)

        hLayoutButtons.addWidget(self.pushSave)

        hRpLayout = QHBoxLayout()
        hRpLayout.addWidget(lblRp)
        hRpLayout.addWidget(self.lineRp)
        hRpLayout.addWidget(lblHorseBaseId)
        hRpLayout.addWidget((self.lineHorseBaseId))

        vLayout = QVBoxLayout()
        gLayout = QGridLayout()
        gLayout.addWidget(lblName, 0, 0, )
        gLayout.addWidget(self.lineName, 0, 1)
        gLayout.addLayout(hRpLayout,0,3)
        gLayout.addWidget(lblDob, 1,0 )
        gLayout.addWidget(self.date, 1, 1)
        gLayout.addWidget(lblSex, 2, 0)
        gLayout.addWidget(self.comboSex, 2, 1)
        gLayout.addWidget(lblcoat, 2, 2)
        gLayout.addWidget(self.comboCoat, 2, 3)
        if self.mode != APM.OPEN_NEW:
            gLayout.addWidget(lblDos,1,2)
            gLayout.addWidget(self.dateDos,1,3)
            gLayout.addWidget(lblBreaker,3,0)
            gLayout.addWidget(self.comboBreaker, 3, 1)
            gLayout.addWidget(lblPlayer, 3,2)
            gLayout.addWidget(self.comboPlayer, 3,3)
            gLayout.addLayout(hLayoutCheck, 4, 1)
            gLayout.addWidget(lblLocation,4,2)
            gLayout.addWidget(self.comboLocation,4,3)
            self.loadEditCombos()
        else:
            gLayout.addLayout(hLayoutCheck, 3, 1)
            gLayout.addWidget(lblLocation,3,2)
            gLayout.addWidget(self.comboLocation,3,3)
        vLayout.addLayout(gLayout)

        if self.mode == APM.OPEN_EDIT:
            try:
                centerColumns = [2, 4, 6, 7]
                colorDict = {}
                self.tableHorses = QTableView()
                self.tableHorses.verticalHeader().setVisible(False)
                self.modelHorses = APM.QSqlAlignColorQueryModel(centerColumns, [], colorDict)
                qry = self.getHorsesQuery()
                self.modelHorses.setQuery(qry)
                self.modelHorses.setHeaderData(0,Qt.Horizontal,"ID")
                self.modelHorses.setHeaderData(1, Qt.Horizontal, "Name")
                self.modelHorses.setHeaderData(2, Qt.Horizontal, "RP")
                self.modelHorses.setHeaderData(3, Qt.Horizontal, 'DOB')
                self.modelHorses.setHeaderData(4, Qt.Horizontal, "Sex")
                self.modelHorses.setHeaderData(5, Qt.Horizontal, 'Coat')
                self.modelHorses.setHeaderData(6, Qt.Horizontal, 'Broke')
                self.modelHorses.setHeaderData(7, Qt.Horizontal, 'Active')
                self.tableHorses.setModel(self.modelHorses)
                self.tableHorses.setSelectionMode(QAbstractItemView.SingleSelection)
                self.tableHorses.setStyleSheet("QTableView {font-size: 8pt;}")
                header = self.tableHorses.horizontalHeader()
                header.setStyleSheet("QHeaderView {font-size: 8pt;}")
                header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
                header.setSectionResizeMode(1, QHeaderView.Stretch)
                header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
                header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
                header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
                header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
                header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
                header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
                self.tableHorses.setRowHeight(0, 10)
                self.tableHorses.verticalHeader().setDefaultSectionSize(self.tableHorses.rowHeight(0))
                self.tableHorses.setColumnWidth(0,50)
                self.tableHorses.setColumnWidth(1, 100)
                self.tableHorses.hideColumn(0)
                self.tableHorses.hideColumn(8)
                self.tableHorses.hideColumn(9)
                self.tableHorses.hideColumn(10)
                self.tableHorses.hideColumn(11)
                self.tableHorses.hideColumn(12)
                self.tableHorses.hideColumn(13)
                self.tableHorses.hideColumn(14)
                self.tableHorses.hideColumn(15)
                self.tableHorses.hideColumn(16)
                self.tableHorses.doubleClicked.connect(self.getHorseData)
                vLayout.addWidget(self.tableHorses)
                self.setWindowTitle("Edit Horse")
            except Exception as err:
                print(type(err).__name__, err.args)
        elif self.mode == APM.OPEN_EDIT_ONE:
            self.loadHorse()
        else:
            self.setWindowTitle("Add Horse")
        vLayout.addLayout(hLayoutButtons)
        self.setLayout(vLayout)
        if self.mode == APM.OPEN_EDIT:
            self.tableHorses.setFocus()
        else:
            self.lineName.setFocus()

    def getLocations(self):
        try:
            with Cdatabase(self.cdb, 'getLocations') as db:
                qry = QSqlQuery(db)
                qry.exec("SELECT id, name ,contactid FROM locations WHERE active")
                if qry.lastError().type()!= 0:
                    raise APM.DataError('getLocations', qry.lastError().text())
                return qry
        except APM.DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print('getLocations', err.args)

    @pyqtSlot()
    def deleteHorse(self):
        pass

    def loadEditCombos(self):
        with Cdatabase(self.cdb, 'combos') as db:
            qryBreakers = QSqlQuery(db)
            qryBreakers.exec("SELECT id, fullname FROM contacts WHERE breaker = True")
            modelBreaker = QSqlQueryModel()
            modelBreaker.setQuery(qryBreakers)
            self.comboBreaker.setModel(modelBreaker)
            self.comboBreaker.setModelColumn(1)
            self.comboBreaker.setCurrentIndex(-1)

            qryPlayers = QSqlQuery(db)
            qryPlayers.exec("SELECT id, fullname FROM contacts WHERE player = True")
            modelPlayer = QSqlQueryModel()
            modelPlayer.setQuery(qryPlayers)
            self.comboPlayer.setModel(modelPlayer)
            self.comboPlayer.setModelColumn(1)
            self.comboPlayer.setCurrentIndex(-1)

    def loadCombos(self):
        with Cdatabase(self.cdb, 'combos_2') as db:
            qrySex = QSqlQuery(self.cdb)
            qrySex.exec_("SELECT id, sex FROM sexes ORDER BY sex")
            modelSex = QSqlQueryModel()
            modelSex.setQuery(qrySex)
            self.comboSex.setModel(modelSex)
            self.comboSex.setModelColumn(1)
            self.comboSex.setCurrentIndex(-1)

            qryCoat = QSqlQuery(db)
            qryCoat.exec_("SELECT id, coat FROM coats ORDER BY coat")
            modelCoat = QSqlQueryModel()
            modelCoat.setQuery(qryCoat)
            self.comboCoat.setModel(modelCoat)
            self.comboCoat.setCurrentIndex(-1)
            self.comboCoat.setModelColumn(1)

    @pyqtSlot()
    def addBreaker(self):
        pass

    @pyqtSlot()
    def addPlayer(self):
        pass

    @pyqtSlot()
    def getHorseData(self):
        self.comboBreaker.setEnabled(False)
        self.comboPlayer.setEnabled(False)
        row = self.tableHorses.currentIndex().row()
        self.modelHorses.query().seek(row)
        record = self.modelHorses.query().record()
        if self.mode == APM.OPEN_EDIT_ONE:
            qry = self.getOneRecord()
        self.record = record
        try:
            res = QMessageBox.question(self,"Edit Horse", "Do you want to edit {}´data.\n Check data and edit it "
                                            " as necessary".format(record.value(1)))
            if res != QMessageBox.Yes:
                self.horseid = None
                self.lineName.clear()
                self.lineRp.clear()
                self.lineHorseBaseId.clear()
                self.comboSex.setCurrentIndex(-1)
                self.comboLocation.seekData(0,2)
                self.comboCoat.setCurrentIndex(-1)
                self.checkBroke.setChecked(False)
                self.checkActive.setChecked(True)
                self.setWindowTitle("Edit Horse:")
                self.pushSave.setEnabled(False)
                return
            self.setWindowTitle("Edit Horse: {}".format(record.value(1)))
            self.horseid = record.value(0)
            self.lineName.setText(record.value(1))
            self.lineRp.setText(record.value(2))
            self.date.setDate(record.value(3))
            self.dateDos.setDate(record.value(14))
            self.comboSex.seekData(record.value(9),0)
            self.comboSex.setModelColumn(0)
            sdx = self.comboSex.findData(QVariant(record.value(9)), Qt.DisplayRole)
            self.comboSex.setModelColumn(1)
            self.comboSex.setCurrentIndex(sdx)
            self.comboCoat.setModelColumn(0)
            cdx = self.comboCoat.findData(QVariant(record.value(10)), Qt.DisplayRole)
            self.comboCoat.setModelColumn(1)
            self.comboCoat.setCurrentIndex(cdx)
            self.comboLocation.seekData(record.value(16), Qt.DisplayRole)
            self.checkBroke.setChecked(True if record.value(6) == u'\u2714' else False)
            self.checkActive.setChecked(True if record.value(7) == u'\u2714' else False)
            self.lineHorseBaseId.setText(str(record.value(8)) if record.value(8) > 0 else None)
            self.comboBreaker.setModelColumn(0)
            cdx = self.comboBreaker.findData(QVariant(record.value(12)), Qt.DisplayRole)
            self.comboBreaker.setModelColumn(1)
            self.comboBreaker.setCurrentIndex(cdx)
            self.comboPlayer.setModelColumn(0)
            cdx = self.comboPlayer.findData(QVariant(record.value(11)), Qt.DisplayRole)
            self.comboPlayer.setModelColumn(1)
            self.comboPlayer.setCurrentIndex(cdx)
            if not record.value(6) :
                self.comboBreaker.setEnabled(True)
            else:
                self.comboPlayer.setEnabled(True)
            self.horseOkSave = False
            self.agreeOkSave= False
            self.pushSave.setEnabled(False)
            if record.value(7) != u'\u2714':
                self.lblState.setVisible(True)
                self.pushDelete.setVisible(False)
            else:
                self.lblState.setVisible(False)
                self.pushDelete.setVisible(True)
                self.pushSave.setVisible(True)
        except Exception as err:
            print(type(err).__name__, err.args)

    def getOneRecord(self):
        try:
            with Cdatabase(self.cdb, 'getOneRecord') as db:
                qry = QSqlQuery(db)
                qry.prepare("""SELECT
                     h.id, h.name, h.rp, h.dob,
                     CASE
                        WHEN h.sexid = 1 THEN _ucs2 X'2642'
                        WHEN h.sexid = 2 THEN _ucs2 X'2640'
                        WHEN h.sexid = 3 THEN _ucs2 X'265E'
                     END Sex,
                     c.coat,
                     IF (h.isbroke = 1, _ucs2 X'2714', '') AS Broke, 
                     IF (a.active = 1, _ucs2 X'2714','') AS Active,
                     h.horsebaseid,
                     h.sexid,
                     h.coatid,
                     a.playerid,
                     a.breakerid,
                     a.agreementid,
                     a.dos,
                     a.id AS agrid,
                     h.locationid
                    FROM horses as h 
                     INNER JOIN agreementhorses as a
                     ON h.id = a.horseid
                     INNER JOIN coats as c
                     ON h.coatid = c.id
                    WHERE h.active = 1
                    AND h.id = ?
                """)
                qry.addBindValue(QVariant(self.horseid))
                qry.exec()
                if qry.lastError().type() != 0:
                    raise APM.DataError('getOneRecord', qry.lastError().text())
                qry.first()
                return qry.record()


        except APM.DataError as err:
            print(err.source, err.message)

    def getHorsesQuery(self):
        with Cdatabase(self.cdb, 'query') as db:
            qry = QSqlQuery(db)
            qry.exec("""SELECT
                     h.id, h.name, h.rp, h.dob,
                     CASE
                        WHEN h.sexid = 1 THEN _ucs2 X'2642'
                        WHEN h.sexid = 2 THEN _ucs2 X'2640'
                        WHEN h.sexid = 3 THEN _ucs2 X'265E'
                     END Sex,
                     c.coat,
                     IF (h.isbroke = 1, _ucs2 X'2714', '') AS Broke, 
                     IF (a.active = 1, _ucs2 X'2714','') AS Active,
                     h.horsebaseid,
                     h.sexid,
                     h.coatid,
                     a.playerid,
                     a.breakerid,
                     a.agreementid,
                     a.dos,
                     a.id AS agrid,
                     h.locationid
                    FROM horses as h 
                     INNER JOIN agreementhorses as a
                     ON h.id = a.horseid
                     INNER JOIN coats as c
                     ON h.coatid = c.id
                    WHERE h.active = 1
                    ORDER BY h.isbroke, h.sexid, h.name""")
        return qry

    @pyqtSlot()
    def enableSave(self):
        if self.isVisible():
            send_object = self.sender()
            if self.mode == APM.OPEN_EDIT and self.horseid is None:
                return
            if (isinstance(send_object, FocusCombo)\
                    or isinstance(send_object, QComboBox)\
                    or isinstance(send_object, FocusCombo)\
                    or isinstance(send_object, QDateEdit)\
                    or isinstance(send_object, QCheckBox))\
                    and self.checkActive.isChecked() \
                    and len(self.lineName.text()) > 0 :
                self.pushSave.setEnabled(True)
                if isinstance(send_object, FocusCombo):
                    self.agreeOkSave = True
                else:
                    self.horseOkSave = True

    @pyqtSlot()
    def checkName(self):
        try:
            if len(self.lineName.text()) > 0:
                self.lineName.text().index(",")
            self.lineName.setText(self.lineName.text().title())
        except ValueError as err:
            self.lineName.setFocus()
            return
        if self.mode == APM.OPEN_NEW:
            qry = QSqlQuery(self.cdb)
            qry.prepare("""SELECT id FROM horses 
            WHERE name = ?;""")
            qry.addBindValue(QVariant(self.lineName.text()))
            qry.exec_()
            if qry.size() > 0:
                QMessageBox.warning(self, "Duplicate Name",
                                    "The horse: '{}' already exists!"
                                    " Use the existing or enter a different name".format(self.lineName.text()))
                self.lineName.clear()
                return
        if self.isVisible():
            self.enableSave()

    def loadHorse(self):
        try:
            if self.mode == APM.OPEN_EDIT_ONE:
                record = self.getOneRecord()
            else:
                record = self.modelHorses.findIdItem(self.horseid, 15)
            self.setWindowTitle("Edit '{}'".format(record.value(1)))
            self.lineName.setText(record.value(1))
            self.lineRp.setText(record.value(2))
            self.date.setDate(record.value(3))
            self.dateDos.setDate(record.value(14))
            self.comboSex.setModelColumn(0)
            sdx = self.comboSex.findData(QVariant(record.value(9)), Qt.DisplayRole)
            self.comboSex.setCurrentIndex(sdx)
            self.comboSex.setModelColumn(1)
            self.comboCoat.setModelColumn(0)
            cdx = self.comboCoat.findData(record.value(10), Qt.DisplayRole)
            self.comboCoat.setModelColumn(1)
            self.comboCoat.setCurrentIndex(cdx)
            self.comboBreaker.setModelColumn(0)
            bdx = self.comboBreaker.findData(record.value('breakerid'), Qt.DisplayRole)
            self.comboBreaker.setModelColumn(1)
            self.comboBreaker.setCurrentIndex(bdx)
            self.comboPlayer.setModelColumn(0)
            pdx = self.comboPlayer.findData(record.value('playerid'), Qt.DisplayRole)
            self.comboPlayer.setCurrentIndex(pdx)
            self.comboPlayer.setModelColumn(1)
            self.checkBroke.setChecked(True if record.value(6) == u'\u2714' else False)
            if not self.checkBroke.isChecked():
                self.comboBreaker.setModelColumn(0)
                bdx = self.comboBreaker.findData(record.value(12), Qt.DisplayRole)
                self.comboBreaker.setCurrentIndex(bdx)
                self.comboBreaker.setModelColumn(1)
                self.comboBreaker.setEnabled(True)
            else:
                self.comboPlayer.setModelColumn(0)
                pdx = self.comboPlayer.findData(record.value(11), Qt.DisplayRole)
                self.comboPlayer.setCurrentIndex(pdx)
                self.comboPlayer.setModelColumn(1)
                self.comboPlayer.setEnabled(True)
            self.checkActive.setChecked(True if record.value(7) == u'\u2714' else False)
            self.lineHorseBaseId.setText(str(record.value(8)))
            if record.value('active') != u'\u2714':
                self.lblState.setVisible(True)
            else:
                self.lblState.setVisible(False)
        except ValueError as err:
            print(type(err).__name__, err.args)
            return
        except TypeError as err:
            print(type(err).__name__, err.args)
        except APM.DataError as err:
            if err.type == 10:
                QMessageBox.critical(self,
                                     "Horse Not Active", err.message + " This horse is not active any longer"
                                                                       "Check sorting causes")
            raise APM.DataError(err.source, err.message, err.type)
        except Exception as err:
            print(type(err).__name__, err.args)
            return
        return

    @pyqtSlot()
    def saveAndClose(self):
        if self.mode == APM.OPEN_EDIT or self.mode == APM.OPEN_EDIT_ONE:
            try:
                qry = QSqlQuery(self.cdb)
                if self.mode == APM.OPEN_NEW:
                    qry.prepare("""
                        INSERT INTO horses (
                        horsebaseid,
                        name,
                        sexid,
                        coatid,
                        isbroke,
                        dob,
                        rp,
                        locationid)
                        VALUES (?, ?, ?, ?, ?, ?, ?,? )""")
                else:
                    qry.prepare("""
                        UPDATE horses as h INNER JOIN agreementhorses as a
                        ON h.id = a.horseid
                        SET h.horsebaseid = ?,
                        h.name = ?, 
                        h.sexid = ?, 
                        h.coatid = ?, 
                        h.isbroke = ?, 
                        h.dob = ?, 
                        h.rp = ?,
                        h.locationid = ?
                        a.dos = ?,
                        a.breakerid = ?,
                        a.playerid = ?,
                        a.active = ?
                        WHERE h.id = ?
                        AND
                        a.agreementid = ?
                        ;""")
                dob = None if self.date.text == 'None' else self.date.date.toString("yyyy-MM-dd")
                qry.addBindValue(QVariant(None if self.lineHorseBaseId.text() == '' or
                                  self.lineHorseBaseId is None else int(self.lineHorseBaseId.text())))
                qry.addBindValue(QVariant(self.lineName.text()))
                row = self.comboSex.currentIndex()
                idx = self.comboSex.model().index(row, 0)
                qry.addBindValue(QVariant(self.comboSex.model().data(idx)))
                row = self.comboCoat.currentIndex()
                idx = self.comboCoat.model().index(row, 0)
                qry.addBindValue(QVariant(self.comboCoat.model().data(idx)))
                qry.addBindValue(QVariant(self.checkBroke.isChecked()))
                qry.addBindValue(QVariant(dob))
                qry.addBindValue(QVariant(self.lineRp.text()))
                qry.addBindValue(QVariant(self.comboLocation.getHiddenData(0)))
                if self.mode == APM.OPEN_EDIT or self.mode == APM.OPEN_EDIT_ONE:
                    dos = None if self.dateDos.text == 'None' else self.dateDos.date.toString("yyyy-MM-dd")
                    qry.addBindValue(QVariant(dos))
                    row = self.comboBreaker.currentIndex()
                    idx = self.comboBreaker.model().index(row, 0)
                    qry.addBindValue(QVariant(self.comboBreaker.model().data(idx)))
                    row = self.comboPlayer.currentIndex()
                    idx = self.comboPlayer.model().index(row, 0)
                    qry.addBindValue(QVariant(self.comboPlayer.model().data(idx)))
                    qry.addBindValue(QVariant(self.checkActive.isChecked()))
                    qry.addBindValue(QVariant(self.horseid))
                    qry.addBindValue(QVariant(self.record.value(13)))
                qry.exec()
                if qry.lastError().ErrorType() > 0:
                    raise APM.DataError('SaveAndClose',qry.lastError().text())
            except APM.DataError as err:
                print(err.source, err.message)
                QMessageBox.warning(self, type(err).__name__, err.message)
                return
            except Exception as err:
                print(type(err).__name__ , err.args)
                return
            self.modelHorses.setQuery(self.getHorsesQuery())
            self.close()

class ShowHorses(QDialog):
    def __init__(self, db, mode):
        super().__init__()
        self.sdb = Cdatabase(db, "show")
        self.type = mode
        self.initUI()
        self.setMinimumSize(600,200)

    def initUI(self):
        pushOK = QPushButton("Close")
        pushOK.setMaximumSize(50, 30)
        pushOK.clicked.connect(self.close)
        self.tableHorses = QTableView()
        self.tableHorses.verticalHeader().setVisible(False)
        self.modelHorses = QSqlAlignQueryModel(self.type)
        qry = self.getHorsesQuery()
        self.modelHorses.setQuery(qry)
        self.modelHorses.setHeaderData(0, Qt.Horizontal, "ID")
        self.modelHorses.setHeaderData(1, Qt.Horizontal, "Name")
        self.modelHorses.setHeaderData(2, Qt.Horizontal, "Player")
        self.modelHorses.setHeaderData(3, Qt.Horizontal, 'Breaker')
        self.modelHorses.setHeaderData(4, Qt.Horizontal, "Manager")
        self.modelHorses.setHeaderData(5, Qt.Horizontal, 'Buyer')
        self.modelHorses.setHeaderData(6, Qt.Horizontal, 'Dealer')
        self.modelHorses.setHeaderData(7, Qt.Horizontal, 'Active')
        self.tableHorses.setModel(self.modelHorses)
        self.tableHorses.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tableHorses.setStyleSheet("QTableView {font-size: 8pt;}")
        header = self.tableHorses.horizontalHeader()
        header.setStyleSheet("QHeaderView {font-size: 8pt;}")
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.tableHorses.setRowHeight(0, 10)
        self.tableHorses.verticalHeader().setDefaultSectionSize(self.tableHorses.rowHeight(0))
        self.tableHorses.setColumnWidth(0, 50)
        self.tableHorses.setColumnWidth(1, 100)
        self.tableHorses.hideColumn(0)
        layout = QVBoxLayout()
        hLayout = QHBoxLayout()
        hLayout.addSpacing(500)
        hLayout.addWidget(pushOK)
        layout.addWidget(self.tableHorses)
        layout.addLayout(hLayout)
        self.setLayout(layout)

    def getHorsesQuery(self):
        qry = QSqlQuery(self.cdb)
        select = """SELECT
                 h.id, 
                 h.name,
                 s.sex,
                 c.coat,
                 h.dob,
                 IF (h.isbroke = 1, _ucs2 X'2714', ''), 
                 if(h.isbreakable = 1, _ucs2 X'2714',''),
                 h.dob,
                 h.active,
                 h.sexid,
                 h.coatid,
                 a.dos
                 FROM horses as h 
                 INNER JOIN sexes as s
                 ON h.sexid = s.id 
                 INNER JOIN coats as c
                 ON h.coatid = c.id"""
        if self.type == APM.CONTACT_BUYER:
            where = "WHERE buyer "
            self.setWindowTitle("Horse Buyers")
        elif self.type == APM.CONTACT_DEALER:
            where = "WHERE dealer "
            self.setWindowTitle("Horse Dealers")
        elif self.type == APM.CONTACT_BREAKER:
            where = "WHERE horsebreaker "
            self.setWindowTitle("Horse Breakers")
        elif self.type == APM.CONTACT_RESPONSIBLE:
            where = "WHERE responsible "
            self.setWindowTitle("Authorized Representative")
        elif self.type == APM.CONTACT_PLAYER:
            where = "WHERE playerseller "
            self.setWindowTitle("Polo Player Sellers")
        qry.prepare(select + where + "ORDER BY name")
        qry.exec()
        return qry

class StartHorse(QDialog):
    """The purpose od this class is to start horses alreadiy asigned
    to a particular agreement. The table shows unstarted horses.
     Once the horse is started it'sn not showing in the table any longer.
     Most of the fields in the for are informative. the only field to set
     are: Starting date: and breaker or player as requiered."""

    def __init__(self, db, parent=None):
        super().__init__()
        self.parent = parent
        self.db = db
        self.setModal(True)
        self.record = None
        self.setUI()

    def setUI(self):

        self.setWindowTitle("Start Horse On Agreement")

        lblProvider = QLabel('Provider')
        self.lineProvider = QLineEdit()
        self.lineProvider.setEnabled(False)

        lblAgreementId = QLabel('Agreement No:')
        self.lineAgreementId = QLineEdit()
        self.lineAgreementId.setMaximumWidth(50)
        self.lineAgreementId.setEnabled(False)

        lblHorse = QLabel('Horse')
        self.lineHorse = QLineEdit()
        self.lineHorse.setEnabled(False)

        lblRp = QLabel("RP")
        self.lineRp = QLineEdit()
        self.lineRp.setEnabled(False)
        self.lineRp.setMaximumWidth(50)

        lblSex = QLabel('Sex')
        self.lineSex = QLineEdit()
        self.lineSex.setEnabled(False)
        self.lineSex.setMaximumWidth(50)
        self.lineSex.setStyleSheet("QLineEdit {font: bold 20px;}")

        lblType = QLabel('Agreement Type')
        self.lineType = QLineEdit()
        self.lineType.setEnabled(False)

        lblOption = QLabel('Payment Option')
        self.lineOption = QLineEdit()
        self.lineOption.setEnabled(False)

        lblDos = QLabel("Start Date")
        self.dateDos = APM.NullDateEdit(self)
        self.dateDos.setToolTip("Date of Start")
        self.dateDos.setMinimumDate(QDate.currentDate().addMonths(-6))
        self.dateDos.setDate(QDate(19999, 23,33))

        lblBreaker = QLabel("Breaker")
        self.comboBreaker = FocusCombo()
        self.comboBreaker.setToolTip("Horse breaker")
        self.comboBreaker.setMinimumWidth(200)
        self.comboBreaker.setEnabled(False)
        self.comboBreaker.activated.connect(self.enableSave)
        self.comboBreaker.setObjectName('Breaker')
        self.comboBreaker.doubleClicked.connect(self.addBreaker)

        lblPlayer = QLabel("Player")
        self.comboPlayer = FocusCombo()
        self.comboPlayer.setToolTip("Horse player")
        self.comboPlayer.setMinimumWidth(200)
        self.comboPlayer.setEnabled(False)
        self.comboPlayer.activated.connect(self.enableSave)
        self.comboPlayer.setObjectName('Player')
        self.comboPlayer.doubleClicked.connect(self.addPlayer)

        self.loadCombos()

        lblTable = QLabel("List of Horses to Start")
        self.tableHorses = QTableView()
        self.tableHorses.verticalHeader().setVisible(False)
        self.tableHorses.doubleClicked.connect(self.getHorseData)

        self.setUpTable()

        self.pushSave = QPushButton("Save")
        self.pushSave.setMaximumWidth(60)
        self.pushSave.setEnabled(False)
        self.pushSave.clicked.connect(self.saveAndClose)

        pushCancel = QPushButton("Cancel")
        pushCancel.setMaximumWidth(60)
        pushCancel.clicked.connect(self.close)
        pushCancel.setFocus()

        layout = QVBoxLayout()
        gLayout = QGridLayout()

        bLayout = QHBoxLayout()
        bLayout.addSpacing(600)
        bLayout.addWidget(pushCancel)
        bLayout.addWidget(self.pushSave)

        hLayoutHorse = QHBoxLayout()
        hLayoutHorse.addWidget(lblRp)
        hLayoutHorse.addWidget(self.lineRp)
        hLayoutHorse.addWidget(lblSex)
        hLayoutHorse.addWidget(self.lineSex)

        gLayout.addWidget(lblProvider,0,0)
        gLayout.addWidget(self.lineProvider,0,1)
        gLayout.addWidget(lblAgreementId,0,2)
        gLayout.addWidget(self.lineAgreementId,0,3)
        gLayout.addWidget(lblType,1,0)
        gLayout.addWidget(self.lineType,1,1)
        gLayout.addWidget(lblOption,1,2)
        gLayout.addWidget(self.lineOption, 1,3)
        gLayout.addWidget(lblHorse,2,0)
        gLayout.addWidget(self.lineHorse,2,1)
        gLayout.addLayout(hLayoutHorse,2,3)
        gLayout.addWidget(lblBreaker,3, 0)
        gLayout.addWidget(self.comboBreaker,3,1)
        gLayout.addWidget(lblPlayer, 3,2)
        gLayout.addWidget(self.comboPlayer, 3,3)
        gLayout.addWidget(lblDos,4,0)
        gLayout.addWidget(self.dateDos,4,1)

        layout.addLayout(gLayout)
        layout.addWidget(lblTable)
        layout.addWidget(self.tableHorses)
        layout.addLayout(bLayout)
        self.setLayout(layout)

    def addBreaker(self):
        pass

    def addPlayer(self):
        add

    def loadCombos(self):
        try:
            qryBreakers = QSqlQuery(self.db)
            qryBreakers.exec("SELECT id, fullname FROM contacts WHERE breaker = True")
            modelBreaker = QSqlQueryModel()
            modelBreaker.setQuery(qryBreakers)
            self.comboBreaker.setModel(modelBreaker)
            self.comboBreaker.setModelColumn(1)
            self.comboBreaker.setCurrentIndex(-1)

            qryPlayers = QSqlQuery(self.db)
            qryPlayers.exec("SELECT id, fullname FROM contacts WHERE player = True")
            modelPlayer = QSqlQueryModel()
            modelPlayer.setQuery(qryPlayers)
            self.comboPlayer.setModel(modelPlayer)
            self.comboPlayer.setModelColumn(1)
            self.comboPlayer.setCurrentIndex(-1)
        except Exception as err:
            raise APM.DataError("loadCombos", err.args)

    def enableSave(self):

        if self.isVisible():
            send_object = self.sender()
            if (isinstance(send_object, FocusCombo) \
                    or isinstance(send_object, QDateEdit))\
                    and len(self.lineProvider.text()) > 0 \
                    and self.dateDos.text != 'None' \
                    and (self.comboPlayer.currentIndex() != -1 \
                    or self.comboBreaker.currentIndex() != -1):
                self.pushSave.setEnabled(True)

    def getHorseData(self):
        self.comboBreaker.setEnabled(False)
        self.comboPlayer.setEnabled(False)
        modelHorses = self.tableHorses.model()
        row = self.tableHorses.currentIndex().row()
        modelHorses.query().seek(row)
        record = modelHorses.query().record()
        self.record = record
        try:
            res = QMessageBox.question(self,"Starting Horse", "Starting {} with {}?"
                                            .format(record.value(2),record.value(1)))
            if res != QMessageBox.Yes:
                self.lineAgreementId.clear()
                self.lineProvider.clear()
                self.lineHorse.clear()
                self.lineRp.clear()
                self.lineSex.clear()
                self.lineType.clear()
                self.lineOption.clear()
                self.dateDos.setDate(QDate(9999,99,99))
                self.comboBreaker.setCurrentIndex(-1)
                self.comboPlayer.setCurrentIndex(-1)
                self.pushSave.setEnabled(False)
                return
            self.lineAgreementId.setText(str(record.value(0)))
            self.lineProvider.setText(record.value(1))
            self.lineHorse.setText(record.value(2))
            self.lineRp.setText(record.value(9))
            self.lineSex.setText(record.value(3))
            self.lineType.setText('Play & Sale') if record.value(6) != 1 else \
                self.lineType.setText('Breaking')
            self.lineOption.setText('On Completion') if record.value(7) == 1 else\
                self.lineOption.setText('Monthly Installments')
            self.comboBreaker.setCurrentIndex(-1)
            self.comboPlayer.setCurrentIndex(-1)
            if record.value(6) == 1:
                self.comboBreaker.setEnabled(True)
            else:
                self.comboPlayer.setEnabled(True)

        except Exception as err:
            print(type(err).__name__, err.args)


    def setUpTable(self):
        qry = self.getHorsesQuery()
        centerColumns = [0, 3, 4, 5]
        colorDict = colorDict = {'column': (4),
                                 u'\u2714': (QColor('yellow'), QColor('black')),
                                 '': (QColor('lightgray'), QColor('black'))}
        modelHorses = QSqlAlignColorQueryModel(centerColumns,colorDict)
        modelHorses.setQuery(qry)
        self.tableHorses.setModel(modelHorses)

        header = self.tableHorses.horizontalHeader()
        header.setStyleSheet("QHeaderView {font-size: 8pt;}")
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        vHeader = self.tableHorses.verticalHeader()
        vHeader.setDefaultSectionSize(30)
        self.tableHorses.hideColumn(6)
        self.tableHorses.hideColumn(7)
        self.tableHorses.hideColumn(8)
        self.tableHorses.hideColumn(9)
        self.tableHorses.setFont(QFont('Tahoma',8))

    def getHorsesQuery(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec(""" SELECT
                a.id No,
                c.fullname Provider,
                h.name Horse,
                CASE
                    WHEN h.sexid = 1 THEN _ucs2 x'2642'
                    WHEN h.sexid = 2 THEN _ucs2 x'2640'
                    WHEN h.sexid = 3 THEN _ucs2 x'265E'
                END Sex,
                IF (a.breaking = 1, _ucs2 x'2714', '') Breaking,
                IF (a.paymentoption <> 1, _ucs2 x'2714', '') Monthly,
                a.breaking,
                a.paymentoption,
                ah.id agreementhorseid,
                h.rp
                FROM agreements AS a
                INNER JOIN contacts AS c
                ON a.supplierid = c.id
                INNER JOIN agreementhorses AS ah
                ON a.id = ah.agreementid
                INNER JOIN horses AS h
                ON ah.horseid = h.id
                WHERE ah.active AND IsNull(ah.dos)
                ORDER BY a.breaking, c.fullname
                """)
            if qry.lastError().type() != 0:
                raise APM.DataError("getHorseQuery", qry.lastError().text())
            if qry.size() == 0 :
                raise APM.DataError("getHorseQuery()","There are no horses to start")
            return qry
        except APM.DataError as err:
            QMessageBox.warning(self, err.source, err.message)
            raise APM.DataError(err.source, err,message)

    @pyqtSlot()
    def saveAndClose(self):
        try:
            qry = QSqlQuery(self.db)
            strSql = """UPDATE agreementhorses
                    SET dos = ?, 
                    breakerid = ?, 
                    playerid = ?
                    """
            if self.record.value(7) == 0:
                strSql +=", billable = True "
            whereSql = "WHERE id = ? "
            strSql += whereSql
            qry.prepare(strSql)
            qry.addBindValue(QVariant(self.dateDos.date.toString("yyyy-MM-dd")))
            row = self.comboBreaker.currentIndex()
            idx = self.comboBreaker.model().index(row, 0)
            qry.addBindValue(QVariant(self.comboBreaker.model().data(idx)))
            row = self.comboPlayer.currentIndex()
            idx = self.comboPlayer.model().index(row, 0)
            qry.addBindValue(QVariant(self.comboPlayer.model().data(idx)))
            qry.addBindValue(QVariant(self.record.value(8)))
            qry.exec()
            if qry.lastError().ErrorType() > 0:
                raise APM.DataError('SaveAndClose', qry.lastError().text())
            qry = self.tableHorses.model().setQuery(self.getHorsesQuery())
        except APM.DataError as err:
            print(err.source, err.message)
            QMessageBox.warning(self, type(err).__name__, err.message)
            return
        except Exception as err:
            print(type(err).__name__, err.args)
            return
        self.close()

class ShowHorse(QDialog):
    """The purpose of this class is to show the detailed information of a selected horse
    either for a play & sale or a breaking agreement. The input is a QSqlDatabase and the
    horse id to be display"""

    def __init__(self, db, horseid):
        super().__init__()
        self.db = db
        self.horseid = horseid
        self.qry = self.getHorseData()
        self.setModal(True)
        self.setUI()

    def setUI(self):
        self.qry.first()
        self.setWindowTitle(self.qry.value(0) + " Details")
        lblHorse = QLabel("Horse: " + self.qry.value(0))
        lblRp = QLabel("RP: " + self.qry.value(1))
        lblDob = QLabel("Birth Date: " + self.qry.value(2).toString("MM-dd-yyyy"))
        lblSex = QLabel('Sex: ' + self.qry.value(3))
        lblCoat = QLabel('Coat: ' + self.qry.value(4))
        lblAge = QLabel('Age: ' + self.qry.value(5))

        tableHorse = self.setTableModel()

        pushCancel = QPushButton('Ok')
        pushCancel.setMaximumWidth(100)
        pushCancel.clicked.connect(self.close)

        vLayout = QVBoxLayout()

        bLayout = QHBoxLayout()
        bLayout.addSpacing(800)
        bLayout.addWidget(pushCancel)

        layout = QGridLayout()
        layout.addWidget(lblHorse, 0, 0)
        layout.addWidget(lblRp, 0,1)
        layout.addWidget(lblSex,0,2)
        layout.addWidget(lblCoat,0,3)
        layout.addWidget(lblDob,1,0)
        layout.addWidget(lblAge,1,3)
        vLayout.addLayout(layout)
        vLayout.addWidget(tableHorse)
        vLayout.addLayout(bLayout)
        self.setLayout(vLayout)

    def getHorseData(self):
        with Cdatabase(self.db,'ShowHorse') as sdb:
            try:
                qry = QSqlQuery(sdb)
                qry.prepare("""
                SELECT DISTINCT 
                h.name, h.rp, h.dob, s.sex, c.coat,
                CONCAT(timestampdiff(YEAR, h.dob, CURDATE()), ' years') Age,
                ah.agreementid , ah.id horsesAgreementId,
                ah.dos, b.dor, 
                CASE
                    WHEN b.type = 0 THEN 'Polo'
                    WHEN b.type = 1 THEN 'Traditional'
                    WHEN b.type = 2 THEN 'Half Break'
                    WHEN b.type = 3 then 'Incomplete'
                END 'Break Type',
                CASE
                    WHEN b.rate = 0 THEN 'Excellent'
                    WHEN b.rate = 1 THEN 'Good'
                    WHEN b.rate = 2 THEN 'Fair'
                    WHEN b.rate = 3 THEN 'Poor'
                END 'Break Rate',
                CONCAT(timestampdiff(DAY, ah.dos, b.dor), ' days') 'BreakTime',
                ct.fullname  AS Buster,
                cp.fullname AS Player,
                b.notes
                FROM horses AS h
                LEFT JOIN agreementhorses AS ah
                ON h.id = ah.horseid
                INNER JOIN sexes AS s
                ON h.sexid = s.id
                INNER JOIN coats AS c
                ON h.coatid = c.id
                LEFT JOIN breaking AS b
                ON ah.id = b.agreementhorseid
                LEFT JOIN contacts AS ct
                ON ah.breakerid = ct.id
                LEFT JOIN contacts AS cp
                ON ah.playerid = cp.id
                WHERE h.id = ?
                """)
                qry.addBindValue(QVariant(self.horseid))
                qry.exec()
                if qry.lastError().type() != 0:
                    raise APM.DataError("getHorseData", qry.lastError().text())
                return qry
            except APM.DataError as err:
                print(err.source, err.message)

    def setTableModel(self):
        try:
            colorDict = {'column':(10),
                        '':(QColor('lightskyblue'), QColor('lightblue')),
                        'Polo': (QColor('lightgrey'), QColor('black')),
                        'Traditional': (QColor('yellow'), QColor('black')),
                        'Half Break': (QColor('green'), QColor('white')),
                        'Incomplete': (QColor('red'), QColor('white'))}


            # colDict = {colNb int:(colName str, colHidden bool, colResizeToContents bool, colCenterd bool,\
            # colWith int )}
            colDict = {
                0: ("HID", True, False, False, None),
                1: ("RP", True, False, False, None),
                2: ("DOB", True, False, False, None),
                3: ("Sex", True, False, False, None),
                4: ("Coat", True, False, False, None),
                5: ("Age",True, False , False ,None),
                6: ("AID",False,True ,True ,None),
                7: ("AHID",False,True , True,None),
                8: ("DOS",False,True ,False ,None),
                9: ("DOR",False,True ,False ,None),
                10: ("Break Type",False,True ,False ,None),
                11: ("Rate",False,True ,False ,None),
                12: ("Break Days",False,True ,False ,None),
                13: ("Buster",False,True ,False ,None),
                14: ("Player",False,True , False,None),
                15: ("Notes",False,False ,False ,None)}

            table = APM.TableViewAndModel(colDict, colorDict, (1000, 100), self.qry)
            return table
        except Exception as err:
            print (type(err).__name__, err.args)

class Mortality(QDialog):


    """This class intends to register the mortality occurences
    that may have happend on a particular agreement horse.
    Input :
           QSQLDatabase: Connection to a MySQL database.
           agreementId : Agreement id
           conn_string : MySQL connection String
           Mode = APM.EDIT_ONE
           record : record from DockMortality on mainidget
           parent: main widget"""


    def __init__(self, db, agreementid, mode = None,
                 record = None, con_string = None ,parent = None):
        super().__init__()
        self.db = db
        self.parent = parent
        self.agreementId = agreementid
        self.record = record
        self.con_string = con_string
        self.mode = mode
        self.setUI()
        if self.mode is not None:
            self.getHorseData()

    def setUI(self):
        self.setModal(True)

        lblDateOfDeath = QLabel("Date of Death")
        self.dateOfDeath = APM.NullDateEdit(self)
        self.dateOfDeath.setToolTip("Date of Start")
        self.dateOfDeath.setMinimumDate(QDate.currentDate().addMonths(-3))
        self.dateOfDeath.setDate(QDate.currentDate())

        self.lblHorse = QLabel("Horse: ")
        self.lblRp = QLabel("RP: ")
        self.lblCoat = QLabel("Coat: ")
        self.lblSex = QLabel("Sex: ")
        self.lblAge = QLabel("Age: ")

        lblVeterinary = QLabel("Veterinary")
        self.comboVet = FocusCombo(self)
        self.loadCombos()
        self.comboVet.setToolTip("Acting Veterinary")
        self.comboVet.activated.connect(self.enableSave)

        mortalityCauses = ['Disease', 'Accident', 'Slaughter', 'Old Age', 'Unknown']

        lblCause = QLabel("Cause")
        self.comboCause = FocusCombo(self,mortalityCauses)
        self.comboCause.setToolTip("Cause of Death")
        self.comboCause.setCurrentIndex(-1)
        self.comboCause.setModelColumn(1)
        self.comboCause.activated.connect(self.enableSave)

        lblDiagnosis = QLabel("Diagnosis")
        self.lineDiagnosis = QLineEdit()
        self.lineDiagnosis.setToolTip("Injury or disease")
        self.lineDiagnosis.editingFinished.connect(self.enableSave)

        if self.mode is None :
            self.tableHorses = self.setTableViewAndModel()
            self.tableHorses.doubleClicked.connect(self.getHorseData)

        self.pushSave = QPushButton("Save")
        self.pushSave.setMaximumWidth(60)
        self.pushSave.setEnabled(False)
        self.pushSave.clicked.connect(self.saveAndClose)

        lblNotes = QLabel("Observations")
        self.textNotes = QTextEdit()
        self.textNotes.setMaximumHeight(50)
        self.textNotes.textChanged.connect(self.enableSave)

        if self.mode is not None:

            self.comboCause.setEnabled(False)
            self.comboVet.setEnabled(False)
            self.lineDiagnosis.setEnabled(False)
            self.dateOfDeath.setEnabled(False)
            self.textNotes.setEnabled(False)
            self.pushDelete = QPushButton("Delete")
            self.pushDelete.setMaximumWidth(60)
            self.pushDelete.setEnabled(True)
            self.pushDelete.clicked.connect(self.deleteRecord)

            self.pushEdit = QPushButton("Edit")
            self.pushEdit.setMaximumWidth(60)
            self.pushEdit.setEnabled(True)
            self.pushEdit.clicked.connect(self.enableEdit)

        self.lblStock = QLabel("Horses Inventory")


        pushCancel = QPushButton("Cancel")
        pushCancel.setMaximumWidth(60)
        pushCancel.clicked.connect(self.close)
        pushCancel.setFocus()

        pushLayout = QHBoxLayout()
        layout = QVBoxLayout()
        gLayout = QGridLayout()

        gLayout.addWidget(self.lblHorse,0,0)
        gLayout.addWidget(self.lblRp,0,3)
        gLayout.addWidget(self.lblCoat,1,0)
        gLayout.addWidget(self.lblSex, 1,1)
        gLayout.addWidget(self.lblAge,1, 3)
        gLayout.addWidget(lblVeterinary,2,0)
        gLayout.addWidget(self.comboVet,2,1)
        gLayout.addWidget(lblCause,2,2)
        gLayout.addWidget(self.comboCause,2,3)
        gLayout.addWidget(lblDateOfDeath,3,0)
        gLayout.addWidget(self.dateOfDeath,3,1 )
        gLayout.addWidget(lblDiagnosis,3,2)
        gLayout.addWidget(self.lineDiagnosis,3,3)
        gLayout.addWidget(lblNotes,4,0)
        gLayout.addWidget(self.textNotes,4,1,1,3)
        gLayout.addWidget(lblStock,7,0)

        if self.mode is not None:
            pushLayout.addWidget(self.pushEdit)
            pushLayout.addWidget(self.pushDelete)

        pushLayout.addSpacing(400)
        pushLayout.addWidget(pushCancel)
        pushLayout.addWidget(self.pushSave)


        layout.addLayout(gLayout)
        if self.mode is None:
            layout.addWidget(self.tableHorses)
        layout.addLayout(pushLayout)

        self.setLayout(layout)
        self.setWindowTitle("Mortality Registry")


    def clearData(self):
        self.dateOfDeath.setDate(QDate.currentDate())
        self.lblHorse.setText("Horse: ")
        self.lblRp.setText("RP: ")
        self.lblCoat.setText("Coat: ")
        self.lblSex.setText("Sex: ")
        self.lblAge.setText("Age: ")
        self.lineDiagnosis.clear()
        self.textNotes.clear()
        self.pushSave.setEnabled(False)
        self.setWindowTitle("Mortality Registry")
        self.comboCause.setCurrentIndex(-1)
        self.comboVet.setCurrentIndex(-1)

    def enableSave(self):

        if self.isVisible():
            send_object = self.sender()
            if (isinstance(send_object, FocusCombo) \
                or isinstance(send_object, QDateEdit) \
                or isinstance(send_object, QTextEdit) \
                or isinstance(send_object, QLineEdit)) \
                    and self.dateOfDeath.text != 'None' \
                    and (self.comboVet.currentIndex() != -1 \
                         or self.comboCause.currentIndex() != -1):
                self.pushSave.setEnabled(True)

    def setTableViewAndModel(self):
        try:
            colorDict = {'column': (3),
                         u'\u2640': (QColor('pink'), QColor('black')),
                         u'\u2642': (QColor('lightskyblue'), QColor('black')),
                         u'\u265E': (QColor('lightgrey'), QColor('black'))}

            # colDict = {colNb int:(colName str, colHidden bool, colResizeToContents bool, colCenterd bool,\
            # colWith int )}
            colDict = {
                0: ("RP", False, True, True, None),
                1: ("Horse", False, False, False, None),
                2: ("Coat", False, True, False, None),
                3: ("Sex", False, True, True, None),
                4: ("Age", False, True, False, None),
                5: ("AgrID", True, True, True, None),
                6: ("Active", True, True, True, None),
                7: ("SexStr", True, True, False, None),
                8: ("ahid", True, True, True, None),
                9: ("horseid", True, True, True, None)}
            qry = self.getHorsesQuery()
            table = APM.TableViewAndModel(colDict, colorDict, (500, 100), qry)
            return table
        except Exception as err:
            print(type(err).__name__, err.args)
            raise APM.DataError(err.args[0], err.args[1])

    def getHorsesQuery(self):
        try:
            with Cdatabase(self.db, "AgreementHorses") as cdb:
                qry = QSqlQuery(cdb)
                qry.prepare(""" SELECT h.rp, 
                h.name Horse, c.coat, 
                CASE
                    WHEN h.sexid = 1 THEN _ucs2 x'2642'
                    WHEN h.sexid = 2 THEN _ucs2 x'2640'
                    WHEN h.sexid = 3 THEN _ucs2 x'265E'
                END Sex,
                CONCAT(TIMESTAMPDIFF(YEAR, h.dob, CURDATE()), ' years') Age,
                ah.agreementid, ah.active, s.sex,
                ah.id agreemenhorseid, h.id horseid
                FROM horses AS h
                INNER JOIN coats AS c
                ON h.coatid = c.id
                INNER JOIN sexes as s
                ON h.sexid = s.id
                INNER JOIN agreementhorses as ah
                ON h.id = ah.horseid
                WHERE ah.active AND ah.agreementid = ?
                ORDER BY h.name
                """)
                qry.addBindValue(QVariant(self.agreementId))
                qry.exec()
                if qry.lastError().type() != 0:
                    raise APM.DataError("getHorseQuery", qry.lastError().text())
                if qry.size() == 0 :
                    raise APM.DataError("getHorseQuery()","There are not active horses")
                return qry
        except APM.DataError as err:
            QMessageBox.warning(self, err.source, err.message)
            raise APM.DataError(err.source, err.message)
            return

    def loadCombos(self):
        with Cdatabase(self.db, 'combos_2') as db:
            qryVet= QSqlQuery(db)
            qryVet.exec_("SELECT id, fullname FROM contacts WHERE veterinary ORDER BY fullname")
            modelVet = QSqlQueryModel()
            modelVet.setQuery(qryVet)
            self.comboVet.setModel(modelVet)
            self.comboVet.setModelColumn(1)
            self.comboVet.setCurrentIndex(-1)

    def getHorseData(self):
        try:
            self.clearData()
            if self.mode is None:
                modelHorses = self.tableHorses.model()
                row = self.tableHorses.currentIndex().row()
                modelHorses.query().seek(row)
                record = modelHorses.query().record()
                self.record = record
                self.setWindowTitle("Death Registry of: {}". format(record.value(1)))
                res = QMessageBox.question(self,"Mortality", "Register {} death ?".format(record.value(1)))
                if res == QMessageBox.Yes:
                    self.lblRp.setText(self.lblRp.text() + record.value(0))
                    self.lblHorse.setText(self.lblHorse.text() + record.value(1))
                    self.lblCoat.setText(self.lblCoat.text() + record.value(2))
                    self.lblSex.setText(self.lblSex.text() + record.value(7))
                    self.lblAge.setText(self.lblAge.text() + record.value(4))
            else:
                self.lblRp.setText(self.lblRp.text() + self.record.value(9))
                self.lblHorse.setText(self.lblHorse.text() + self.record.value(1))
                self.lblCoat.setText(self.lblCoat.text() + self.record.value(10))
                self.lblSex.setText(self.lblSex.text() + self.record.value(11))
                self.lblAge.setText(self.lblAge.text() + self.record.value(3))
                self.dateOfDeath.setDate(self.record.value(0))

                self.comboVet.setModelColumn(0)
                vdx = self.comboVet.findData(self.record.value(6), Qt.DisplayRole)
                self.comboVet.setCurrentIndex(vdx)
                self.comboVet.setModelColumn(1)

                self.comboCause.setModelColumn(0)
                cdx = self.comboCause.findData(self.record.value(8), Qt.DisplayRole)
                self.comboCause.setCurrentIndex(cdx)
                self.comboCause.setModelColumn(1)

                self.lineDiagnosis.setText(self.record.value(5))
                self.textNotes.setText(self.record.value(7))

        except Exception as err:
            print(type(err).__name__, err.args)

    def saveAndClose(self):
        """Requieres to:
        - Save (Insert) new record in mortality table.
        - Update agreementhorses table - (active = False)
        - Update horses table - (active = False).
        - Refresh the dockMortality query in the main form.
        - Refresh this form horse query.
        """
        try:
            cnn = pymysql.connect(**self.con_string)
            cnn.begin()
            with cnn.cursor() as cur:
                self.comboVet.setModelColumn(0)
                self.comboCause.setModelColumn(0)
                if self.mode is None:
                    agreementHorseId = self.record.value(8)
                    horseId = self.record.value(9)

                    sql_mortality = """ INSERT INTO mortality
                        (dod, agreementhorseid, causeid, diagnose, veterinaryid, notes)
                        VALUES (%s, %s, %s, %s, %s, %s)"""
                else:
                    agreementHorseId = self.record.value(14)
                    horseId = self.record.value(13)
                    sql_mortality = """ UPDATE mortality 
                        SET dod = %s, agreementhorseid = %s, causeid = %s, 
                        diagnose = %s, veterinaryid = %s, notes = %s
                        WHERE id = %s """
                parameters = [self.dateOfDeath.date.toString('yyyy-MM-dd'),
                              agreementHorseId,
                              self.comboCause.currentText(),
                              self.lineDiagnosis.text(),
                              self.comboVet.currentText(),
                              self.textNotes.toPlainText()]
                if self.mode is not None:
                    parameters.append(self.record.value(12))
                cur.execute(sql_mortality, parameters)
                if self.mode is None:
                    sql_horses = """ UPDATE horses 
                        SET active = False
                        WHERE id = %s"""
                    cur.execute(sql_horses, (horseId,))
                    horseUpdate = cur.rowcount
                    sql_agreementhorses = """ UPDATE agreementhorses
                        SET active = False 
                        WHERE id = %s"""
                    cur.execute(sql_agreementhorses, (agreementHorseId,))
                    """Checks if there still are active horses on the agreement and if not
                                        updates de 'active' agreement status field"""
                    sql_check_Agreement = """
                                        UPDATE agreements AS a
                                        SET active = False,
                                        deactivationdate = %s 
                                        WHERE NOT EXISTS (SELECT ah.id FROM agreementhorses AS ah 
                                                            WHERE ah.active AND ah.agreementid = a.id)
                                        AND a.id = %s"""
                    parameters = [self.dateOfDeath.date.toString("yyyy-MM-dd"), self.agreementId]
                    cur.execute(sql_check_Agreement, parameters)

            cnn.commit()
        except pymysql.Error as e:
            QMessageBox.warning(self, "saveAndClose", "Error {}: {}".format(e.args[0], e.args[1]))
            cnn.rollback()
        except AttributeError as err:
            print(err.args)
            cnn.rollback()
        except Exception as err:
            print(type(err).__name__, err.args)
            cnn.rollback()
        finally:
            cnn.close()
            self.comboVet.setModelColumn(1)
            self.comboCause.setModelColumn(1)

            """Resets the mortality list for this particular agreement on
            the main form subform"""
        mainQuery = self.parent.queryMortality()
        if mainQuery.size() >= 0:
            self.parent.dockMortality.widget().model().setQuery(mainQuery)
            """Clear the form for the next record to be entered"""
            self.clearData()
            """Resets the  active horses list for this particular agreement"""
            try:
                if self.mode is None:
                    self.tableHorses.model().setQuery(self.getHorsesQuery())
                    return
                self.close()
            except APM.DataError:
                self.close()

    @pyqtSlot()
    def deleteRecord(self):
        """Requieres to:
            - Delete (delete) current record in mortality table.
            - Update (Reverse) agreementhorses table - (active = True)
            - Update (Reverse) horses table - (active = True).
            - Refresh the dockMortality query in the main form.
            - Refresh this form horse query.
            """
        try:
            cnn = pymysql.connect(**self.con_string)
            res = QMessageBox.question(self, "Cancel Rejection",
                                       "Confirm  {}  Death reoord Cancelation?".format(
                                           self.record.value(1)),
                                       QMessageBox.Yes | QMessageBox.No)
            if res == QMessageBox.No:
                return
            cnn.begin()
            with cnn.cursor() as cur:
                sql_delete = """ DELETE FROM mortality
                WHERE id = %s"""
                cur.execute(sql_delete, self.record.value(12))
                sql_horses = """ UPDATE horses 
                    SET active = True
                    WHERE id = %s"""
                cur.execute(sql_horses, (self.record.value(13),))
                sql_agreementhorses = """ UPDATE agreementhorses
                    SET active = True 
                    WHERE id = %s"""
                cur.execute(sql_agreementhorses, (self.record.value(14),))
                """It checks for active horses in agreementhorses for this particular
                                    agreement and if it does'nt find any desactivate - active = False - the agreement"""
                sql_check_Agreement = """
                                        UPDATE agreements AS a
                                        SET active = True,
                                            deactivationdate = NULL
                                            WHERE EXISTS (SELECT ah.id FROM agreementHorses AS ah 
                                            WHERE ah.active AND ah.agreementid = a.id)
                                            AND a.id = %s"""
                cur.execute(sql_check_Agreement, (self.agreementId,))

            res = QMessageBox.question(self, "Confirmation",
                                       "Are you sure?", QMessageBox.Yes | QMessageBox.Cancel)
            if res == QMessageBox.Yes:
                cnn.commit()
        except pymysql.Error as e:
            QMessageBox.warning(self, "deleteRecord", "Error {}: {}".format(e.args[0], e.args[1]))
            cnn.rollback()
        except AttributeError as err:
            print(err.args)
            cnn.rollback()
        except Exception as err:
            print(type(err).__name__, err.args)
            cnn.rollback()
        finally:
            cnn.close()
        """Resets the mortality list for this particular agreement on
                the main form subform"""
        mainQuery = self.parent.queryMortality()
        if mainQuery.size() >= 0 :
            self.parent.dockMortality.widget().model().setQuery(mainQuery)
        """Clear the form for the next record to be entered"""
        self.close()

    @pyqtSlot()
    def enableEdit(self):
        res = QMessageBox.question(self, "Edit", "Edit {} death data?".format(self.record.value(1)))
        if res == QMessageBox.Yes:
            self.comboCause.setEnabled(True)
            self.comboVet.setEnabled(True)
            self.lineDiagnosis.setEnabled(True)
            self.dateOfDeath.setEnabled(True)
            self.textNotes.setEnabled(True)


class Sales(QDialog):
    """This class intends to register the sales occurences
       that may have happened for a particular agreement horse.
       Input :
              QSQLDatabase: Connection to a MySQL database.
              agreementId : Agreement id
              conn_string : MySQL connection String
              Mode = APM.EDIT_ONE
              parent : calling widget
              record :Sales record from dockSales"""

    def __init__(self, db, agreementid, mode=None,
                 record=None, con_string=None, qryLoad=None, parent=None):
        super().__init__()
        self.db = db
        self.parent = parent
        self.agreementId = agreementid
        self.record = record
        self.con_string = con_string
        self.mode = mode
        self.qryLoad = qryLoad
        self.setUI()
        self.sharePercent = 0.00
        self.saleExpenses = 0.00
        self.saleDict = {}

    def setUI(self):
        self.setModal(True)

        lblDateOfSale = QLabel("Sale Date")
        self.dateOfSale = APM.NullDateEdit(self)
        self.dateOfSale.setToolTip("Date of Sale")
        self.dateOfSale.setMinimumDate(QDate.currentDate().addMonths(-3))
        self.dateOfSale.setDate(QDate.currentDate())

        self.lblHorse = QLabel("Horse: ")
        self.lblRp = QLabel("RP: ")
        self.lblCoat = QLabel("Coat: ")
        self.lblSex = QLabel("Sex: ")
        self.lblAge = QLabel("Age: ")

        lblSharePrice = QLabel("Player Share: ")
        self.lineSharePrice = QLineEdit('0.00')
        self.lineSharePrice.setToolTip("Player's income share")
        self.lineSharePrice.setAlignment(Qt.AlignRight)
        self.lineSharePrice.setEnabled(False)
        self.lineSharePrice.setStyleSheet("QLineEdit {color: yellow;"
                                          " background-color: red;"
                                          "padding: 1px;"
                                          "border-radius: 15px;}")
        lblNetPrice = QLabel("Net Income: ")
        self.lineNetPrice = QLineEdit('0.00')
        self.lineNetPrice.setToolTip("Sale Price")
        self.lineNetPrice.setAlignment(Qt.AlignRight)
        self.lineNetPrice.setEnabled(False)
        self.lineNetPrice.setStyleSheet("QLineEdit {color: white;"
                                          " background-color: blue;"
                                          "padding: 1px;"
                                          "border-radius: 15px;}")
        lblBuyer = QLabel("Buyer")
        self.comboBuyer = FocusCombo(self)
        self.comboBuyer.setToolTip("Horse's Buyer")
        self.comboBuyer.activated.connect(self.enableSave)

        lblDealer = QLabel("Dealer")
        self.comboDealer = FocusCombo(self)
        self.comboDealer.setToolTip("Transaction's  Dealer")
        self.comboDealer.activated.connect(self.enableSave)

        lblRepresentative = QLabel("Checker")
        self.comboRepresentative = FocusCombo(self)
        self.comboRepresentative.setToolTip("Transaction Checker")
        self.comboRepresentative.activated.connect(self.enableSave)

        self.loadCombos()

        salePurposes = ['Polo Export', 'Polo Local', 'Breeding', 'Ridding', 'Rejection', 'Unknown']

        lblPurpose = QLabel("Destination")
        self.comboPurpose = FocusCombo(self, salePurposes)
        self.comboPurpose.setToolTip("Buyer´s purpose")
        self.comboPurpose.setCurrentIndex(-1)
        self.comboPurpose.setModelColumn(1)
        self.comboPurpose.activated.connect(self.enableSave)

        saleTypes = ['Auction', 'Dealer', 'Direct','Unknown']

        lblType = QLabel("Sale Type")
        self.comboType = FocusCombo(self, saleTypes)
        self.comboType.setToolTip("Transaction's Type")
        self.comboType.setCurrentIndex(-1)
        self.comboType.setModelColumn(1)
        self.comboType.activated.connect(self.enableSave)

        saleDocuments = ['Invoice', 'Receipt', 'None']

        lblDocument = QLabel("Document")
        self.comboDocument = FocusCombo(self, saleDocuments)
        self.comboDocument.setToolTip("Transaction´s Document")
        self.comboDocument.setCurrentIndex(0)
        self.comboDocument.setModelColumn(1)
        self.comboDocument.activated.connect(lambda: self.setNumber(self.comboDocument.getHiddenData(0)))
        self.comboDocument.activated.connect(self.enableSave)

        priceValidator = QDoubleValidator(0.00, 100000.00, 2)
        priceValidator.setNotation(QDoubleValidator.StandardNotation)

        lblPrice = QLabel("Price")
        self.linePrice = QLineEdit('0.00')
        self.linePrice.setToolTip("Sale Price")
        self.linePrice.setAlignment(Qt.AlignRight)
        self.linePrice.enterEvent = lambda _: self.linePrice.selectAll()
        self.linePrice.editingFinished.connect(self.enableSave)
        self.linePrice.editingFinished.connect(self.saleResults)
        self.linePrice.setValidator(priceValidator)

        self.lineComission = PercentOrAmountLineEdit('Expenses',(0.00, 1000000.00,2), 2, self)
        self.lineComission.lineValue.editingFinished.connect(self.saleResults)

        lblNumber = QLabel("Number")
        self.lineNumber = QLineEdit()
        self.lineNumber.setToolTip("Sale Document Number")
        self.lineNumber.editingFinished.connect(self.enableSave)
        self.tableHorses = self.setTableViewAndModel()
        self.tableHorses.doubleClicked.connect(self.getHorseData)

        self.pushSave = QPushButton("Save")
        self.pushSave.setMaximumWidth(60)
        self.pushSave.setEnabled(False)
        self.pushSave.clicked.connect(self.saveAndClose)

        lblNotes = QLabel("Observations")
        self.textNotes = QTextEdit()
        self.textNotes.setMaximumHeight(50)
        self.textNotes.textChanged.connect(self.enableSave)



        self.comboBuyer.setEnabled(False)
        self.comboDealer.setEnabled(False)
        self.comboRepresentative.setEnabled(False)
        self.comboPurpose.setEnabled(False)
        self.comboType.setEnabled(False)
        self.comboDocument.setEnabled(False)

        self.linePrice.setEnabled(False)
        self.lineComission.setEnabled(False)
        self.lineNumber.setEnabled(False)
        self.dateOfSale.setEnabled(False)
        self.textNotes.setEnabled(False)
        if self.mode == APM.OPEN_EDIT:

            self.pushReset = QPushButton()
            self.pushReset.setIcon(QIcon(":Icons8/Edit/reset.png"))
            self.pushReset.setMaximumWidth(50)
            self.pushReset.setEnabled(False)
            self.pushReset.clicked.connect(self.clearData)

            self.pushDelete = QPushButton("Delete")
            self.pushDelete.setMaximumWidth(70)
            self.pushDelete.setEnabled(False)
            self.pushDelete.clicked.connect(self.deleteRecord)

        self.lblStock = QLabel("Horses Inventory")

        pushCancel = QPushButton("Exit")
        pushCancel.setMaximumWidth(60)
        pushCancel.clicked.connect(self.close)
        pushCancel.setFocus()

        pushLayout = QHBoxLayout()
        layout = QVBoxLayout()
        gLayout = QGridLayout()

        gLayout.addWidget(self.lblHorse,0,0)
        gLayout.addWidget(self.lblRp,0,2)
        gLayout.addWidget(self.lblAge,0,3)
        gLayout.addWidget(self.lblSex, 1, 0)
        gLayout.addWidget(self.lblCoat, 1, 2)
        gLayout.addWidget(lblDateOfSale, 2, 0)
        gLayout.addWidget(self.dateOfSale, 2, 1)
        gLayout.addWidget(lblRepresentative, 2, 2)
        gLayout.addWidget(self.comboRepresentative, 2, 3)
        gLayout.addWidget(lblDocument, 3, 0)
        gLayout.addWidget(self.comboDocument, 3, 1)
        gLayout.addWidget(lblNumber, 3, 2)
        gLayout.addWidget(self.lineNumber, 3, 3)

        gLayout.addWidget(lblBuyer, 4, 0)
        gLayout.addWidget(self.comboBuyer,4,1)
        gLayout.addWidget(lblDealer,4,2)
        gLayout.addWidget(self.comboDealer,4,3)
        gLayout.addWidget(lblType,5,0)
        gLayout.addWidget(self.comboType,5,1)
        gLayout.addWidget(lblPurpose,5,2)
        gLayout.addWidget(self.comboPurpose,5,3)

        gLayout.addWidget(self.lineComission, 6, 0, 1, 2)
        gLayout.addWidget(lblPrice,6,2)
        gLayout.addWidget(self.linePrice,6,3)
        gLayout.addWidget(lblSharePrice, 7, 0)
        gLayout.addWidget(self.lineSharePrice,7,1)
        gLayout.addWidget(lblNetPrice, 7, 2)
        gLayout.addWidget(self.lineNetPrice, 7, 3)
        gLayout.addWidget(lblNotes,8,0)
        gLayout.addWidget(self.textNotes,8,1,1,3)
        #gLayout.addWidget(self.lblStock,9,0)

        if self.mode == APM.OPEN_EDIT:
            pushLayout.addWidget(self.pushReset)
            pushLayout.addWidget(self.pushDelete)
            self.setWindowTitle("Edit Sale Record")
        else:
            self.setWindowTitle("Sales")

        pushLayout.addSpacing(400)
        pushLayout.addWidget(pushCancel)
        pushLayout.addWidget(self.pushSave)

        layout.addLayout(gLayout)
        layout.addWidget(self.lblStock)
        layout.addWidget(self.tableHorses)
        layout.addLayout(pushLayout)

        self.setLayout(layout)

    @pyqtSlot(int)
    def setNumber(self, type):
        if type == 0:
            self.lineNumber.setText("I-")
        elif type == 1:
            self.lineNumber.setText("R-")
        else:
            self.lineNumber.setText("--")

    def clearData(self):
        try:
            self.dateOfSale.setDate(QDate.currentDate())
            self.dateOfSale.setEnabled(True)
            self.lblHorse.setText("Horse: ")
            self.lblRp.setText("RP: ")
            self.lblCoat.setText("Coat: ")
            self.lblSex.setText("Sex: ")
            self.lblAge.setText('Age: ')
            self.lblStock.clear()
            self.linePrice.setText('0.00')
            self.linePrice.setEnabled(True)
            self.lineComission.lineValue.setText('0.00')
            self.lineComission.setEnabled(True)
            self.lineSharePrice.setText('0.00')
            self.lineNetPrice.setText('0.00')
            self.lineSharePrice.setText('0.00')
            self.lineNumber.clear()
            self.lineNumber.setEnabled(True)
            self.comboRepresentative.setCurrentIndex(-1)
            self.comboRepresentative.setEnabled(True)
            self.comboDealer.setCurrentIndex(-1)
            self.comboDealer.setEnabled(True)
            self.comboBuyer.setCurrentIndex(-1)
            self.comboBuyer.setEnabled(True)
            self.comboDocument.setCurrentIndex(-1)
            self.comboDocument.setEnabled(True)
            self.comboType.setCurrentIndex(-1)
            self.comboType.setEnabled(True)
            self.comboPurpose.setCurrentIndex(-1)
            self.comboPurpose.setEnabled(True)
            self.textNotes.clear()
            self.textNotes.setEnabled(True)
            self.pushSave.setEnabled(False)
            if self.mode == APM.OPEN_NEW:
                self.setWindowTitle("Sales")
            else:
                self.setWindowTitle("Edit Sales")
                self.pushReset.setEnabled(False)
                self.pushDelete.setEnabled(False)
        except AttributeError as err:
            print('ClearData', err.args)

    def enableSave(self):
        if self.isVisible():
            send_object = self.sender()
            if (isinstance(send_object, FocusCombo) \
                or isinstance(send_object, QDateEdit) \
                or isinstance(send_object, QTextEdit) \
                or isinstance(send_object, QLineEdit)
                or isinstance(send_object, APM.TableViewAndModel)) \
                    and self.dateOfSale.text != 'None' \
                    and len(self.lblHorse.text()) > 2  \
                    and (self.comboBuyer.currentIndex() != -1 \
                    and self.comboRepresentative.currentIndex() != -1\
                    and self.comboPurpose.currentIndex() != -1\
                    and self.comboDealer.currentIndex() != -1\
                    and self.comboType.currentIndex() != -1
                    and self.comboDocument.currentIndex() != -1\
                    and len(self.lineNumber.text()) > 2\
                    and float(self.lineNetPrice.text()) >=  0 ):
                self.pushSave.setEnabled(True)

    def setTableViewAndModel(self):
        try:
            colorDict = {'column': (3),
                         u'\u2640': (QColor('pink'), QColor('black')),
                         u'\u2642': (QColor('lightskyblue'), QColor('black')),
                         u'\u265E': (QColor('lightgrey'), QColor('black'))}

            # colDict = {colNb int:(colName str, colHidden bool, colResizeToContents bool, colCenterd bool,\
            # colWith int )}
            colDict = {
                0: ("RP", False, True, True, None),
                1: ("Horse", False, False, False, None),
                2: ("Coat", False, True, False, None),
                3: ("Sex", False, True, True, None),
                4: ("Age", False, True, False, None),
                5: ("AgrID", True, True, True, None),
                6: ("SexStr", True, True, False, None),
                7: ("ahid", True, True, None),
                8: ("horseid", True, True, True, None),
                9: ("baseamount", True, True, False, None),
                10:("firstfrom", True, True, False, None),
                11:("firtto", True, False, False, False, None),
                12:("secondfrom", True, False, False, False, None),
                13:("secondto", True, False, False, False, None),
                14:("thirdfrom", True, False, False, False, None),
                15:("thirdto", True, False, False, False, None),
                16:("finalamount", True, False, False, False, None),
                17:("basepercent", True, False, False, False, None),
                18:("firstpercent", True, False, False, False, None),
                19:("secondpercent", True, False, False, False, None),
                20:("thirdpercent", True, False, False, False, None),
                21:("finalpercent", True, False, False, False, None),
                22:("Agreementtype", True, True, False,False, None),
                23:("saleid", True, False, False, None),
                24:("DOS", True, True, False, None),
                25:("Buyerid", True, True, False, None),
                26:("Dealerid", True, True, False, None),
                27:("responsibleid", True, True, False, None),
                28:("destinationid", True, True, False, None),
                29:("type", True, True, False, None),
                30:("Price", True, True, False, None),
                31:("comissionpercent", True, True, False, None),
                32:("comission", True, True, False, None),
                33:("expenses", True, True, False, None),
                34:("documenttype", True, True, False, None),
                35:("documentnumber", True, True, False, None),
                36:("Notes", True, True, False, None)}
            #qry = self.getHorsesQuery()
            table = APM.TableViewAndModel(colDict, colorDict, (500, 100), self.qryLoad)
            return table
        except Exception as err:
            print(type(err).__name__, err.args)
            raise APM.DataError(type(err).__name__, err.args)


    def loadCombos(self):
        try:
            qryBuyer= QSqlQuery(self.db)
            qryBuyer.exec_("SELECT id, fullname FROM contacts WHERE buyer ORDER BY fullname")
            modelBuyer = QSqlQueryModel()
            modelBuyer.setQuery(qryBuyer)
            self.comboBuyer.setModel(modelBuyer)
            self.comboBuyer.setModelColumn(1)
            self.comboBuyer.setCurrentIndex(-1)
            if qryBuyer.lastError().type() != 0:
                raise APM.DataError("Load Combos", qryBuyer.lastError().text())

            qryDealer = QSqlQuery(self.db)
            qryDealer.exec("SELECT id, fullname FROM contacts WHERE dealer ORDER BY fullname")
            modelDealer = QSqlQueryModel()
            modelDealer.setQuery(qryDealer)
            self.comboDealer.setModel(modelDealer)
            self.comboDealer.setModelColumn(1)
            self.comboDealer.setCurrentIndex(-1)
            if qryDealer.lastError().type() != 0:
                raise APM.DataError("Load Combos", qryDealer.lastError().text())

            qryRepresentative = QSqlQuery(self.db)
            qryRepresentative.exec_("SELECT id, fullname FROM contacts WHERE responsible ORDER BY fullname")
            modelRepresentative= QSqlQueryModel()
            modelRepresentative.setQuery(qryRepresentative)
            self.comboRepresentative.setModel(modelRepresentative)
            self.comboRepresentative.setModelColumn(1)
            self.comboRepresentative.setCurrentIndex(-1)
            if qryRepresentative.lastError().type() != 0:
                raise APM.DataError("Load Combos", qryRepresentative.lastError().text())
        except APM.DataError as err:
            print(err.source, err.message)

    def getHorseData(self):
        try:
            self.clearData()
            modelHorses = self.tableHorses.model()
            row = self.tableHorses.currentIndex().row()
            modelHorses.query().seek(row)
            record = modelHorses.query().record()
            self.record = record
            self.lblRp.setText(self.lblRp.text() + record.value(0))
            self.lblHorse.setText(self.lblHorse.text() + record.value(1))
            self.lblCoat.setText(self.lblCoat.text() + record.value(2))
            self.lblSex.setText(self.lblSex.text() + record.value(6))
            self.lblAge.setText(self.lblAge.text() + str(record.value(4)))
            if not record.value(17) is None:
                self.saleDict['Base'] = (record.value(17), 0, record.value(9))
            if record.value(18) > 0 :
                self.saleDict['First'] = (record.value(18),record.value(10), record.value(11))
            if record.value(19) > 0 :
                self.saleDict['Second'] = (record.value(19),record.value(12), record.value(13))
            if record.value(20) > 0 :
                self.saleDict['Third'] = (record.value(20),record.value(14), record.value(15))
            if record.value(21) > 0:
                self.saleDict['Open']= (record.value(21),record.value(16), 1000000.00)
            if self.mode == APM.OPEN_NEW:
                self.setWindowTitle("{}'s Sale Registry".format(record.value(1)))
                res = QMessageBox.question(self, "Sales", "Register {}'s sale?".format(record.value(1)))
                if res != QMessageBox.Yes:
                    self.clearData()
                    return
            else:
                self.setWindowTitle("Edit/Delete {}'s Sale record". format(self.record.value(1)))
                res = QMessageBox.question(self, "Sales", "Edit {}'s sale record?".format(record.value(1)))
                if res != QMessageBox.Yes:
                    self.clearData()
                    return
                self.pushReset.setEnabled(True)
                self.pushDelete.setEnabled(True)
                self.dateOfSale.setDate(self.record.value(24))
                self.comboBuyer.setCurrentIndex(self.comboBuyer.seekData(self.record.value(25),0))
                self.comboDealer.setCurrentIndex(self.comboDealer.seekData(self.record.value(26),0))
                self.comboRepresentative.setCurrentIndex(self.comboRepresentative.seekData(self.record.value(27),0))
                self.comboPurpose.setCurrentIndex(self.comboPurpose.seekData(self.record.value(28),0))
                self.comboType.setCurrentIndex(self.comboType.seekData(self.record.value(29),0))
                self.comboDocument.setCurrentIndex(self.comboDocument.seekData(self.record.value(34),0))

                self.lineComission.lineValue.setText(str(self.record.value(33)))
                self.linePrice.setText(str(self.record.value(30)))
                self.lineSharePrice.setText(str(self.record.value(32)))
                self.lineNumber.setText(str(self.record.value(35)))

                if self.record.value(30) > 0:
                    netIncome = self.record.value(30) - self.record.value(33) - self.record.value(32)
                    self.lineNetPrice.setText(str(netIncome))
                    shareResult = "Player's {}% share on ${} Net Sale Income".format(str(self.record.value(31) * 100),
                                                                                     str(self.record.value(30) -
                                                                                         self.record.value(33)))
                    self.lblStock.setText(shareResult)
                    self.lblStock.setStyleSheet("QLabel {color: red; background-color: yellow;}")
                else:
                    self.lblStock.setText('')

                self.textNotes.setText(self.record.value(36))

        except Exception as err:
            print(type(err).__name__, err.args)

    def saveAndClose(self):
        """Requieres to:
        New Sale:
            - Save (Insert) new record in sales table.
            - Save (Insert) accountspayable table.
            - Update agreementhorses table - (active = False)
            - Update horses table - (active = False).
            - Update payable table -
        Updated Sale:
            - Update Sales table.
            _ Update payable table
        - Refresh the dockSales query in the main form.
        - Refresh this form horse query.
        - Checks agreement for active horses and if not found any, desactivate the
        agreement.
        """

        try:
            if self.mode == APM.OPEN_NEW:
                saleid = 'NULL'
            else:
                saleid = self.record.value(23)
            qry = QSqlQuery(self.db)
            qry.exec("""CALL sales_sale({}, {}, '{}', {}, {}, {}, {}, {}, {}, {},
                         {}, {}, {}, {}, '{}', '{}', {},  "{}", {})""".format(
                    self.mode,
                    self.agreementId,
                    self.dateOfSale.date.toString("yyyy-MM-dd"),
                    self.record.value(7),
                    self.comboBuyer.getHiddenData(0),
                    self.comboDealer.getHiddenData(0),
                    self.comboRepresentative.getHiddenData(0),
                    self.comboPurpose.getHiddenData(0),
                    self.comboType.getHiddenData(0),
                    float(self.linePrice.text()),
                    float(self.sharePercent),
                    float(self.lineSharePrice.text()),
                    float(self.saleExpenses),
                    self.comboDocument.getHiddenData(0),
                    self.lineNumber.text(),
                    self.textNotes.toPlainText(),
                    self.record.value(8),
                    self.lblStock.text(),
                    saleid))
            if qry.lastError().type() != 0:
                if qry.lastError().number() == 2013:
                    raise APM.DataError(qry.lastError().number())
                raise APM.DataError("saveAndClose", qry.lastError().text())
            if qry.first():
                print(qry.value(0), qry.value(1))
            self.clearData()
            self.resetTables()
        except APM.DataError as err:
            if not err.source == 2013:
                print(err.source, err.message)
                return
            count = 0
            while not self.db.isOpen():
                self.reconnect()
                count += 1
                if count >= 10: break

    def reconnect(self):
        ok, self.db = Settings.connectionTest()

    def resetTables(self):
        try:
            qrySales = self.parent.querySales()
            self.parent.dockSales.widget().model().setQuery(qrySales)
            qry = QSqlQuery(self.db)
            qry.exec("CALL sales_gethorses({}, {})".format(self.agreementId, self.mode))
            if qry.lastError().type() != 0:
                raise APM.DataError("getHorsesQuery", qry.lastError().text())
            if not qry.first():
                raise APM.DataError("getHorsesQuery", "There is not available data")
            self.tableHorses.model().setQuery(qry)
        except APM.DataError as err:
            print(err.source, err.message)
            self.close()

    @pyqtSlot()
    def saleResults(self):

        netPrice = 0.00
        if float(self.linePrice.text()) > 0:
            if self.lineComission.percent:
                self.saleExpenses = float(self.linePrice.text()) * float(self.lineComission.value)/100
            else:
                self.saleExpenses = float(self.lineComission.value)
            sharePercent = 0.0
            if self.record.value(22) == APM.AGREEMENT_TYPE_BREAKING:
                QMessageBox.information(self, "Sales", "Currently sales are not schedule for plain 'Breaking agreements'",
                                        QMessageBox.Ok)
                return
            elif self.record.value(22) in [APM.AGREEMENT_TYPE_FULL, APM.AGREEMENT_TYPE_PLAY]:
                netPrice = float(self.linePrice.text()) - self.saleExpenses
                for key, value in self.saleDict.items():
                    if value[1] <= netPrice <= value[2]:
                        sharePercent = value[0]
                        break
                shareResult = "Player's {}% share on ${} Net Sale Income".format(str(sharePercent * 100),
                                                                                 str(netPrice))
            elif self.record.value(22) == APM.AGREEMENT_TYPE_OVER_BASE:
                if float(self.linePrice.text()) >= (self.saleExpenses + self.record.value(9)):
                    netPrice = float(self.linePrice.text()) - self.saleExpenses - self.record.value(9)
                else:
                    netPrice = 0
                for key, value in self.saleDict.items():
                    if value[1] - self.record.value(9) <= netPrice <= value[2] - self.record.value(9):
                        sharePercent = value[0]
                        break
                shareResult = "Player's {}% share on ${} Net Sale Income over ${} base amount".format(
                    str(sharePercent * 100), str(netPrice), self.record.value(9))
            elif self.record.value(22) == APM.AGREEMENT_TYPE_OVER_EXPENSES:
                shareExpense = self.record.value(11) - self.record.value(9)
                if float(self.linePrice.text()) >= (self.saleExpenses + self.record.value(11)):
                    netPrice = float(self.linePrice.text()) - self.saleExpenses - self.record.value(11)
                else:
                    if float(self.linePrice.text()) >= self.saleExpenses + self.record.value(9):
                        shareExpense = float(self.linePrice.text()) - self.saleExpenses - self.record.value(9)
                    else:
                        shareExpense = 0
                    netPrice = 0
                for key, value in self.saleDict.items():
                    if value[1] - self.record.value(11) <= netPrice <= value[2] - self.record.value(11):
                        sharePercent = value[0]
                        break
                shareResult = "Player's ${} expenses plus {}% share on ${} Net Sale Income over ${} expenses".format(
                    shareExpense, str(sharePercent * 100), str(netPrice),
                    self.record.value(11))

            self.lineSharePrice.setText(str(netPrice * sharePercent))


            if self.record.value(22) in [APM.AGREEMENT_TYPE_PLAY, APM.AGREEMENT_TYPE_FULL]:
                self.lineNetPrice.setText(str(netPrice - float(self.lineSharePrice.text())))
                self.lineSharePrice.setText(str(netPrice * sharePercent))
            elif self.record.value(22) == APM.AGREEMENT_TYPE_OVER_BASE:

                self.lineNetPrice.setText(str(netPrice-float(self.lineSharePrice.text()) + self.record.value(9)))
            elif self.record.value(22)== APM.AGREEMENT_TYPE_OVER_EXPENSES:
                self.lineSharePrice.setText(str(shareExpense + netPrice * sharePercent))
                self.lineNetPrice.setText(str(float(self.linePrice.text())- float(self.lineSharePrice.text()) -
                                              self.saleExpenses))
            self.lblStock.setText(shareResult)

            self.sharePercent = sharePercent

    @pyqtSlot()
    def getComission(self):
        if float(self.linePrice.text()) > 0:
            self.saleResults()

    @pyqtSlot()
    def deleteRecord(self):
        """Requieres to:
            - Delete (delete) current record in sales table.
            - Update (Reverse) agreementhorses table - (active = True)
            - Update (Reverse) horses table - (active = True).deactivationdate = Null, Active 0 True
            - Deletes the entry in payable table
            - Refresh the dockSales query in the main form.
            - Refresh this form horse query.
            - Update - Reverse -Agreement table when all agreement horses are deactivates
            """
        try:
            res = QMessageBox.question(self,"Delete Confirm", """Delete records can't be recovered. 
            Delete {}' sale from file?""" .format(self.record.value(1)),
                                       QMessageBox.Yes | QMessageBox.No)
            if res != QMessageBox.Yes:
                return
            qry = QSqlQuery(self.db)
            qry.exec("CALL sales_delete({},{},{},{})".format(self.record.value(23),
                                                          self.record.value(7),
                                                          self.record.value(8),
                                                          self.record.value(5)))
            if qry.lastError().type() !=0:
                raise APM.DataError('deleteRecord', qry.lastError().text())
            if qry.first():
                print(qry.value(0), qry.value(1))
            self.clearData()
            self.resetTables()
        except APM.DataError as e:
            QMessageBox.warning(self, "saveAndClose", "Error {}: {}".format(e.args[0], e.args[1]))
        except AttributeError as err:
            print(err.args)
        except Exception as err:
            print(type(err).__name__, err.args)

    @pyqtSlot()
    def enableEdit(self):
        res = QMessageBox.question(self, "Edit", "Edit {}'s  sale information?".format(self.record.value(2)))
        if res == QMessageBox.Yes:
            self.comboBuyer.setEnabled(True)
            self.comboDealer.setEnabled(True)
            self.comboRepresentative.setEnabled(True)
            self.comboPurpose.setEnabled(True)
            self.comboType.setEnabled(True)
            self.comboDocument.setEnabled(True)

            self.linePrice.setEnabled(True)
            self.lineComission.setEnabled(True)
            self.lineNumber.setEnabled(True)
            self.dateOfSale.setEnabled(True)
            self.textNotes.setEnabled(True)

            if not self.record.value(18) is None:
                self.saleDict['Base'] = (self.record.value(18), 0, self.record.value(10))
                if self.record.value(19) > 0 :
                    self.saleDict['First'] = (self.record.value(19),self.record.value(11), self.record.value(12))
                if self.record.value(20) > 0 :
                    self.saleDict['Second'] = (self.record.value(20),self.record.value(13), self.record.value(14))
                if self.record.value(21) > 0 :
                    self.saleDict['Third'] = (self.record.value(21),self.record.value(12), self.record.value(16))
                if self.record.value(22) > 0:
                    self.saleDict['Open']= (self.record.value(22),self.record.value(17), 1000000.00)

class Reject(QDialog):

    """This class intends to register the rejection occurences
       that may have happen on a particular agreement horse.
       Input :
              QSQLDatabase: Connection to a MySQL database.
              agreementId : Agreement id
              conn_string : MySQL connection String
              Mode = APM.EDIT_ONE or None
              parent :calling widget - mainWidget
              record : Current record from QDockRejection"""


    def __init__(self, db, agreementid, mode=None,
                 record=None, con_string=None ,parent=None):
        super().__init__()
        self.db = db
        self.parent = parent
        self.agreementId = agreementid
        self.record = record
        self.con_string = con_string
        self.mode = mode
        self.setUI()
        if self.mode is not None:
            self.getHorseData()

    def setUI(self):
        self.setModal(True)
        lblDor = QLabel("Rejection Date")
        self.dor = APM.NullDateEdit(self)
        self.dor.setToolTip("Date of  Rejection")
        self.dor.setMinimumDate(QDate.currentDate().addMonths(-3))
        self.dor.setDate(QDate.currentDate())

        self.lblHorse = QLabel("Horse: ")
        self.lblRp = QLabel("RP: ")
        self.lblCoat = QLabel("Coat: ")
        self.lblSex = QLabel("Sex: ")
        self.lblAge = QLabel("Age: ")

        lblRejector = QLabel("Rejector")
        self.comboRejector = FocusCombo(self)
        self.loadCombos()
        self.comboRejector.setToolTip("Rejection Responsible")
        self.comboRejector.activated.connect(self.enableSave)

        rejectionCauses = ['Performance', 'Conformation', 'Disease','Injury', 'Unknown']

        lblCause = QLabel("Cause")
        self.comboCause = FocusCombo(self,rejectionCauses)
        self.comboCause.setToolTip("Rejection Cause")
        self.comboCause.setCurrentIndex(-1)
        self.comboCause.setModelColumn(1)
        self.comboCause.activated.connect(self.enableSave)

        rejectionTypes = ['Permanent','Veterinary','Transitory']
        if not self.agreementId:
            rejectionTypes.pop()

        lblType = QLabel("Type")
        self.comboType = FocusCombo(self, rejectionTypes)
        self.comboType.setToolTip("Rejection Type")
        self.comboType.setCurrentIndex(-1)
        self.comboType.setModelColumn(1)
        self.comboType.activated.connect(self.enableSave)

        if self.mode is None :
            self.setWindowTitle("Rejection Registry")

            self.tableHorses = self.setTableViewAndModel()
            self.tableHorses.doubleClicked.connect(self.getHorseData)

        self.pushSave = QPushButton("Save")
        self.pushSave.setMaximumWidth(60)
        self.pushSave.setEnabled(False)
        self.pushSave.clicked.connect(self.saveAndClose)

        lblNotes = QLabel("Observations")
        self.textNotes = QTextEdit()
        self.textNotes.setMaximumHeight(50)
        self.textNotes.textChanged.connect(self.enableSave)

        if self.mode is not None:
            self.setWindowTitle("{} Rejection Registry".format(self.record.value(1)))
            self.comboCause.setEnabled(False)
            self.comboType.setEnabled(False)
            self.comboRejector.setEnabled(False)
            self.dor.setEnabled(False)
            self.textNotes.setEnabled(False)

            self.pushDelete = QPushButton("Delete")
            self.pushDelete.setMaximumWidth(60)
            self.pushDelete.setEnabled(True)
            self.pushDelete.clicked.connect(self.deleteRecord)

            self.pushEdit = QPushButton("Edit")
            self.pushEdit.setMaximumWidth(60)
            self.pushEdit.setEnabled(True)
            self.pushEdit.clicked.connect(self.enableEdit)

        lblStock = QLabel("Horses Inventory")

        pushCancel = QPushButton("Cancel")
        pushCancel.setMaximumWidth(60)
        pushCancel.clicked.connect(self.close)
        pushCancel.setFocus()

        pushLayout = QHBoxLayout()
        layout = QVBoxLayout()
        gLayout = QGridLayout()

        gLayout.addWidget(self.lblHorse,0,0)
        gLayout.addWidget(self.lblRp,0,3)
        gLayout.addWidget(self.lblCoat,1,0)
        gLayout.addWidget(self.lblSex, 1,1)
        gLayout.addWidget(self.lblAge,1, 3)
        gLayout.addWidget(lblRejector,2,0)
        gLayout.addWidget(self.comboRejector,2,1)
        gLayout.addWidget(lblCause,2,2)
        gLayout.addWidget(self.comboCause,2,3)
        gLayout.addWidget(lblDor,3,0)
        gLayout.addWidget(self.dor,3,1 )
        gLayout.addWidget(lblType,3,2)
        gLayout.addWidget(self.comboType,3,3)
        gLayout.addWidget(lblNotes,4,0)
        gLayout.addWidget(self.textNotes,4,1,1,3)
        gLayout.addWidget(lblStock,7,0)

        if self.mode is not None:
            pushLayout.addWidget(self.pushEdit)
            pushLayout.addWidget(self.pushDelete)

        pushLayout.addSpacing(400)
        pushLayout.addWidget(pushCancel)
        pushLayout.addWidget(self.pushSave)


        layout.addLayout(gLayout)
        if self.mode is None:
            layout.addWidget(self.tableHorses)
        layout.addLayout(pushLayout)

        self.setLayout(layout)



    def clearData(self):
        self.dor.setDate(QDate.currentDate())
        self.lblHorse.setText("Horse: ")
        self.lblRp.setText("RP: ")
        self.lblCoat.setText("Coat: ")
        self.lblSex.setText("Sex: ")
        self.lblAge.setText("Age: ")
        self.textNotes.clear()
        self.comboRejector.setCurrentIndex(-1)
        self.comboType.setCurrentIndex(-1)
        self.comboCause.setCurrentIndex(-1)
        self.dor.setDate(QDate.currentDate())
        self.pushSave.setEnabled(False)
        self.setWindowTitle("Rejection Registry") if self.agreementId else self.setWindowTitle(
            "Unassigned Horses Rejection Registry")
    def enableSave(self):

        if self.isVisible():
            send_object = self.sender()
            if (isinstance(send_object, FocusCombo) \
                or isinstance(send_object, QDateEdit) \
                or isinstance(send_object, QTextEdit) \
                or isinstance(send_object, QLineEdit)
                or isinstance(send_object, APM.TableViewAndModelTable)) \
                    and self.dor.text != 'None' \
                    and (self.comboRejector.currentIndex() != -1 \
                         or self.comboCause.currentIndex() != -1):
                self.pushSave.setEnabled(True)

    def setTableViewAndModel(self):
        try:
            colorDict = {'column': (3),
                         u'\u2640': (QColor('pink'), QColor('black')),
                         u'\u2642': (QColor('lightskyblue'), QColor('black')),
                         u'\u265E': (QColor('lightgrey'), QColor('black'))}

            # colDict = {colNb int:(colName str, colHidden bool, colResizeToContents bool, colCenterd bool,\
            # colWith int )}
            colDict = {
                0: ("RP", False, True, True, None),
                1: ("Horse", False, False, False, None),
                2: ("Coat", False, True, False, None),
                3: ("Sex", False, True, True, None),
                4: ("Age", False, True, False, None),
                5: ("AgrID", True, True, True, None),
                6: ("Active", True, True, True, None),
                7: ("SexStr", True, True, False, None),
                8: ("ahid", True, True, True, None),
                9: ("horseid", True, True, True, None)}
            if not self.agreementId:
                colDict[5] = ('Broke', False, True, True, None )
            qry = self.getHorsesQuery()
            table = APM.TableViewAndModel(colDict, colorDict, (500, 100), qry)
            return table
        except Exception as err:
            print(type(err).__name__, err.args)
            raise APM.DataError(err.args[0], err.args[1])

    def getHorsesQuery(self):
        try:
            with Cdatabase(self.db, "AgreementHorses") as cdb:
                qry = QSqlQuery(cdb)
                qry.prepare(""" SELECT h.rp, 
                h.name Horse, c.coat, 
                CASE
                    WHEN h.sexid = 1 THEN _ucs2 x'2642'
                    WHEN h.sexid = 2 THEN _ucs2 x'2640'
                    WHEN h.sexid = 3 THEN _ucs2 x'265E'
                END Sex,
                CONCAT(TIMESTAMPDIFF(YEAR, h.dob, CURDATE()), ' years') Age,
                ah.agreementid, ah.active, s.sex,
                ah.id agreemenhorseid, h.id horseid
                FROM horses AS h
                INNER JOIN coats AS c
                ON h.coatid = c.id
                INNER JOIN sexes as s
                ON h.sexid = s.id
                INNER JOIN agreementhorses as ah
                ON h.id = ah.horseid
                WHERE ah.billable AND ah.agreementid = ?
                ORDER BY h.name
                """)
                qry.addBindValue(QVariant(self.agreementId))
                qry.exec()
                if qry.lastError().type() != 0:
                    raise APM.DataError("getHorseQuery", qry.lastError().text())
                if qry.size() == 0 :
                    raise APM.DataError("getHorseQuery()","There are not active horses")
                return qry
        except APM.DataError as err:
            QMessageBox.warning(self, err.source, err.message)
            raise APM.DataError(err.source, err.message)
            return

    def loadCombos(self):
        with Cdatabase(self.db, 'combos_2') as db:
            qryReject= QSqlQuery(db)
            qryReject.prepare("""
                SELECT id, fullname FROM contacts 
                WHERE  responsible OR veterinary or 
                 id IN (SELECT supplierid FROM agreements WHERE id  = ?) 
                 ORDER BY fullname""")
            qryReject.addBindValue(QVariant(self.agreementId))
            qryReject.exec()
            modelReject = QSqlQueryModel()
            modelReject.setQuery(qryReject)
            self.comboRejector.setModel(modelReject)
            self.comboRejector.setModelColumn(1)
            self.comboRejector.setCurrentIndex(-1)

    def getHorseData(self):
        try:
            self.clearData()
            if self.mode is None:
                modelHorses = self.tableHorses.model()
                row = self.tableHorses.currentIndex().row()
                modelHorses.query().seek(row)
                record = modelHorses.query().record()
                self.record = record
                self.setWindowTitle("{} Rejection Registry". format(record.value(1)))
                res = QMessageBox.question(self,"Rejection", "Register {} reject?".format(record.value(1)))
                if res == QMessageBox.Yes:
                    self.lblRp.setText(self.lblRp.text() + record.value(0))
                    self.lblHorse.setText(self.lblHorse.text() + record.value(1))
                    self.lblCoat.setText(self.lblCoat.text() + record.value(2))
                    self.lblSex.setText(self.lblSex.text() + record.value(7))
                    self.lblAge.setText(self.lblAge.text() + record.value(4))
                    self.textNotes.clear()
            else:

                self.lblRp.setText(self.lblRp.text() + self.record.value(10))
                self.lblHorse.setText(self.lblHorse.text() + self.record.value(1))
                self.lblCoat.setText(self.lblCoat.text() + self.record.value(11))
                self.lblSex.setText(self.lblSex.text() + self.record.value(12))
                self.lblAge.setText(self.lblAge.text() + self.record.value(3))
                self.dor.setDate(self.record.value(0))
                self.textNotes.setText(self.record.value(7))

                self.comboRejector.setModelColumn(0)
                vdx = self.comboRejector.findData(self.record.value(6), Qt.DisplayRole)
                self.comboRejector.setCurrentIndex(vdx)
                self.comboRejector.setModelColumn(1)

                self.comboCause.setModelColumn(0)
                cdx = self.comboCause.findData(self.record.value(8), Qt.DisplayRole)
                self.comboCause.setCurrentIndex(cdx)
                self.comboCause.setModelColumn(1)

                self.comboType.setModelColumn(0)
                tdx = self.comboType.findData(self.record.value(9), Qt.DisplayRole)
                self.comboType.setCurrentIndex(tdx)
                self.comboType.setModelColumn(1)

        except Exception as err:
            print(type(err).__name__, err.args)

    def saveAndClose(self):
        """Requieres to:
        - Save (Insert) new record in rejection table.
        - Insert ne record in clearance table
        - Update agreementhorses table - (active = False)
        - Update horses table - (active = False).
        - Refresh the dockRejection query in the main form.
        - Refresh this form horse query.
        """
        try:
            cnn = pymysql.connect(**self.con_string)
            cnn.begin()
            with cnn.cursor() as cur:
                self.comboRejector.setModelColumn(0)
                self.comboCause.setModelColumn(0)
                self.comboType.setModelColumn(0)
                if self.mode is None:
                    agreementHorseId = self.record.value(8) if self.agreementId else None
                    horseId = self.record.value(9)

                    sql_reject = """ INSERT INTO rejection
                              (dor, agreementhorseid, typeid, causeid, rejectorid, notes)
                              VALUES (%s, %s, %s, %s, %s, %s)"""

                    sql_Clearence = """INSERT INTO clearance 
                    (agreementhorseid, reasonid, typeid)
                    VALUES(%s, %s, %s)"""
                else:
                    agreementHorseId = self.record.value(15)
                    horseId = self.record.value(14)
                    sql_reject = """ UPDATE rejection 
                              SET dor = %s, agreementhorseid = %s, typeid = %s, causeid = %s, 
                              rejectorid = %s, notes = %s
                              WHERE id = %s """
                parameters = [self.dor.date.toString('yyyy-MM-dd'),
                              agreementHorseId,
                              self.comboType.currentText(),
                              self.comboCause.currentText(),
                              self.comboRejector.currentText(),
                              self.textNotes.toPlainText()]
                paramClearance = (self.record.value(8), CLEARENCE_REASON_REJECT, self.comboType.currentText())
                if self.mode is not None:
                    parameters.append(self.record.value(13))
                cur.execute(sql_reject, parameters)
                cur.execute(sql_Clearence, paramClearance)
                if self.mode is None:
                    """Updates the agreementhorses table"""
                    sql_agreementhorses = """ UPDATE agreementhorses
                                            SET billable = False 
                                            WHERE id = %s"""
                    cur.execute(sql_agreementhorses, (agreementHorseId,))
                    if self.comboType.currentText() != REJECTION_TYPE_TRANSITORY:
                        """If the rejection is permanentt removes - set active = false -
                        both the agreementhorses table and the horses table, otherwise it
                        only set active = false to the agreementhorse table removing the
                        horse from the agreement but it'll be elegible to alocate to other
                        agreement"""
                        sql_horses = """ UPDATE horses 
                                  SET active = False
                                  WHERE id = %s"""
                        cur.execute(sql_horses, (horseId,))
                        horseUpdate = cur.rowcount
                    """Checks if there still are active horses on the agreement and if not
                    updates de 'active' agreement status field"""
                    sql_check_Agreement = """
                    UPDATE agreements AS a
                    SET active = False,
                    deactivationdate = %s 
                    WHERE NOT EXISTS (SELECT ah.id FROM agreementhorses AS ah 
                                        WHERE ah.active AND ah.agreementid = a.id)
                    AND a.id = %s"""
                    parameters = [self.dor .date.toString("yyyy-MM-dd"), self.agreementId]
                    cur.execute(sql_check_Agreement, parameters)
                cnn.commit()
                self.comboRejector.setModelColumn(1)
                self.comboCause.setModelColumn(1)
                self.comboType.setModelColumn(1)
        except pymysql.Error as e:
            QMessageBox.warning(self, "saveAndClose", "Error {}: {}".format(e.args[0], e.args[1]))
            cnn.rollback()
        except AttributeError as err:
            print(err.args)
            cnn.rollback()
        except Exception as err:
            print(type(err).__name__, err.args)
            cnn.rollback()
        finally:
            cnn.close()


        """Resets the rejected list for this particular agreement on
            the main form subform"""
        mainQuery = self.parent.queryRejected()
        if mainQuery.size() >= 0 and self.agreementId:
            self.parent.dockRejection.widget().model().setQuery(mainQuery)
        """Clear the form for the next record to be entered"""
        self.clearData()
        """Resets the  active horses list for this particular agreement"""
        try:
            if self.mode is None:
                self.tableHorses.model().setQuery(self.getHorsesQuery())
                return
            else:
                self.close()
        except APM.DataError:
                self.close()

    @pyqtSlot()
    def deleteRecord(self):
        """Requieres to:
            - Delete (delete) current record in rejection table.
            - Update (Reverse) agreementhorses table - (active = True)
            - Update (Reverse) horses table - (active = True).
            - Refresh the dockRefuse query in the main form.
            - Refresh this form horse query.
            """
        try:
            res = QMessageBox.question(self, "Cancel Rejection",
                            "Confirm  {} rejection Cancelation from the records?".format(self.record.value(1)),
                            QMessageBox.Yes | QMessageBox.No)
            if res != QMessageBox.Yes:
                return
            cnn = pymysql.connect(**self.con_string)
            cnn.begin()
            with cnn.cursor() as cur:
                sql_delete = """ DELETE FROM rejection
                WHERE id = %s"""
                cur.execute(sql_delete, self.record.value(13))
                if self.record.value(9) != 2:
                    sql_horses = """ UPDATE horses 
                        SET active = True
                        WHERE id = %s"""
                    cur.execute(sql_horses, (self.record.value(14),))
                sql_agreementhorses = """ UPDATE agreementhorses
                    SET active = True 
                    WHERE id = %s"""
                cur.execute(sql_agreementhorses, (self.record.value(15),))
                """It checks for active horses in agreementhorses for this particular
                                    agreement and if it does'nt find any desactivate - active = False - the agreement"""
                sql_check_Agreement = """
                                        UPDATE agreements AS a
                                        SET active = True,
                                            deactivationdate = NULL
                                            WHERE EXISTS (SELECT ah.id FROM agreementHorses AS ah 
                                            WHERE ah.active AND ah.agreementid = a.id)
                                            AND a.id = %s"""
                parameters = [self.agreementId, ]
                cur.execute(sql_check_Agreement, parameters)
                res = QMessageBox.question(self, "Confirmation",
                                           "Are you sure?", QMessageBox.Yes | QMessageBox.Cancel)
                if res == QMessageBox.Yes:
                    cnn.commit()
        except pymysql.Error as e:
            QMessageBox.warning(self, "deleteRecord", type(e).__name__ + ' ' + e.args)
            cnn.rollback()
        except AttributeError as err:
            print(type(err), err.args)
            cnn.rollback()
        except Exception as err:
            print(type(err).__name__, err.args)
            cnn.rollback()
        finally:
            """Resets the rejection list for this particular agreement on
            the main form dockWidget"""
            mainQuery = self.parent.queryRejected()
            if mainQuery.size() >= 0 :
                self.parent.dockRejection.widget().model().setQuery(mainQuery)
            """Clear the form for the next record to be entered"""
            self.close()

    @pyqtSlot()
    def enableEdit(self):
        res = QMessageBox.question(self, "Edit", "Edit {} Reject data?".format(self.record.value(1)))
        if res == QMessageBox.Yes:
            self.comboCause.setEnabled(True)
            self.comboRejector.setEnabled(True)
            self.comboType.setEnabled(True)
            self.dor.setEnabled(True)
            self.textNotes.setEnabled(True)