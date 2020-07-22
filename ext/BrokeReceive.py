from ext.MySQLConnector import MySQLConnector
from PyQt5.QtWidgets import (QDialog, QLabel, QLineEdit, QDateEdit, QGridLayout, QHBoxLayout,
                             QTableView, QVBoxLayout, QPushButton, QTextEdit, QHeaderView,
                             QMessageBox)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon
from PyQt5.QtCore import QSettings, QVariant, QDate, Qt, pyqtSlot
#from ext.CQSqlDatabase import Cdatabase,
from ext.APM import (FocusCombo, NullDateEdit, DataError, OPEN_NEW, OPEN_EDIT,
                     PAYABLES_TYPE_FULL_BREAK, PAYABLES_TYPE_HALF_BREAK, TableViewAndModel,
                     BRAKE_TYPE_FINAL, BRAKE_TYPE_HALFBREAKE, BRAKE_TYPE_INCOMPLETE,
                     CLEARENCE_REASON_BREAK)
from PyQt5.QtSql import QSqlQuery
import pymysql

class ReceiveBroken(QDialog):

    def __init__( self, mode, db, con_string, agreementId=None, qryLoad = None, parent=None):
        super().__init__()
        self.horseId = None
        self.halfBreak = None
        self.agreementHorseId = None
        self.agreementId = agreementId
        self.con_string = con_string
        self.db = db
        self.qryLoad = qryLoad
        if not self.db.isOpen():
            self.db.open()
        self.parent = parent
        self.supplierId = parent.supplierId
        self.breakingId = None
        self.mode = mode
        if not self.db.isOpen():
            self.db.open()
        self.setModal(True)
        self.setUI()

    def setUI(self):
        self.setWindowTitle("Receive Broken Horses ")
        if self.agreementId:
            self.setWindowTitle(self.windowTitle() +" Agreement ID: " + str(self.agreementId))

        lblHorse = QLabel('Horse')
        self.lineHorse = QLineEdit()
        self.lineHorse.setToolTip("Horse´s name")
        self.lineHorse.setEnabled(False)

        lblAgreeId = QLabel("Agreement ID")
        self.lineAgreement = QLineEdit()
        self.lineAgreement.setToolTip("Agreement ID Number")
        self.lineAgreement.setEnabled(False)

        lblProvider = QLabel("Breaking Services Provider")
        self.lineProvider = QLineEdit()
        self.lineProvider.setToolTip("Provider of breaking services")
        self.lineProvider.setEnabled(False)

        lblBreaker = QLabel("Horse Breaker")
        self.lineBreaker = QLineEdit()
        self.lineBreaker.setToolTip("Actual horse breaker")
        self.lineBreaker.setEnabled(False)

        lblDos = QLabel("Starting Date")
        self.dateDos = NullDateEdit(self)
        self.dateDos.setToolTip("Starting brake date")
        self.dateDos.setEnabled(False)

        lblDays = QLabel("Days")
        self.lineDays = QLineEdit()
        self.lineDays.setToolTip("Breaking days")
        self.lineDays.setEnabled(False)

        lblDor = QLabel("Receiving Date")
        self.dateDor = NullDateEdit(self)
        self.dateDor.setToolTip("Receiving Date")
        self.dateDor.setMinimumDate(self.getLastBoardDate())
        self.dateDor.setDate(QDate.currentDate())
        self.dateDor.dateChanged.connect(self.enableSave)

        keys = ('0', '1', '2')
        types = ('Full Break', 'Half Break', 'Incomplete')
        payable = ('2', '3', '5')
        typeModel = QStandardItemModel(3, 3)
        for row, type in enumerate(types):
            item = QStandardItem(keys[row])
            typeModel.setItem(row, 0, item)
            item = QStandardItem(types[row])
            typeModel.setItem(row,1,item)
            item = QStandardItem(payable[row])
            typeModel.setItem(row, 2, item)


        lblBreakType = QLabel("Break Type")
        self.comboType = FocusCombo()
        self.comboType.addItem('23')
        self.comboType.setMaximumWidth(200)
        self.comboType.setModel(typeModel)
        self.comboType.setCurrentIndex(-1)
        self.comboType.setModelColumn(1)
        self.comboType.activated.connect(self.enableSave)

        keys = ('0', '1', '2', '3', '4')
        rates = ('Excellent', 'Very Good', 'Good','Fair', 'Poor')
        rateModel = QStandardItemModel(5, 2)

        for row, rate in enumerate(rates):
            item = QStandardItem(keys[row])
            rateModel.setItem(row, 0, item)
            item = QStandardItem(rates[row])
            rateModel.setItem(row, 1, item)

        lblBreakRate = QLabel("Break Rate")
        self.comboRate = FocusCombo()
        self.comboRate.setToolTip("Job Rate")
        self.comboRate.setModel(rateModel)
        self.comboRate.setCurrentIndex(-1)
        self.comboRate.setModelColumn(1)
        self.comboRate.activated.connect(self.enableSave)

        self.notes = QTextEdit()
        self.notes.setToolTip("Breaking Notes")
        self.notes. setMaximumHeight(50)
        self.notes.textChanged.connect(self.enableSave)

        self.pushSave = QPushButton('Save')
        self.pushSave.clicked.connect(self.saveAndClose)
        self.pushSave.setMaximumWidth(80)
        self.pushSave.setEnabled(False)

        self.pushCancel = QPushButton('Close')
        self.pushCancel.setMaximumWidth(80)
        self.pushCancel.clicked.connect(self.closeWidget)
        colorDict = {}
        if self.mode == OPEN_NEW:

            colDict = {0 :("Provider", True, True, False, None ),
                       1 :("AgrID", False, True, True, None),
                       2 : ("Horse", False, False, False, None),
                       3 : ("Buster", True, True, False, None),
                       4 : ("DOS", False, True, True, None),
                       5 : ("Days", False, True, True, None),
                       6 : ("AHID", True, True, False, None),
                       7 :("HID", True, True, True, None),
                       8 : ("Half Break", True, True, False, None)}
        else:
            self.pushReset = QPushButton()
            self.pushReset.setIcon(QIcon(":Icons8/Edit/reset.png"))
            self.pushReset.setMaximumWidth(50)
            self.pushReset.setEnabled(False)
            self.pushReset.clicked.connect(self.resetWidget)

            colDict = {0 :("Provider", True, True, False, None ),
                       1 :("AgrID", False, True, True, None),
                       2 : ("Horse", False, False, False, None),
                       3 : ("Buster", True, True, False, None),
                       4 : ("DOS", False, True, True, None),
                       5 : ("Days", False, True, True, None),
                       6 : ("AHID", True, True, False, None),
                       7 : ("HID", True, True, True, None),
                       8 : ("Half Break", True, True, False, None),
                        9: ("BKID", True, True, False, None),
                       10: ("DOR", False, True, False, None),
                       11: ("TYPE", False, True, True, None),
                       12: ("RATE", False, True, True, None),
                       13: ("NOTES", True, True, False, None)}

        self.table = TableViewAndModel(colDict, colorDict, (100,100), self.qryLoad)
        self.table.doubleClicked.connect(self.getHorseData)

        self.pushDelete = QPushButton("Delete")
        self.pushDelete.setMaximumWidth(70)
        self.pushDelete.setEnabled(False)
        self.pushDelete.clicked.connect(self.deleteReception)

        lblDetail = QLabel("Horses List")
        layout = QGridLayout()
        layout.addWidget(lblProvider, 0, 0)
        layout.addWidget(self.lineProvider,0 ,1)
        layout.addWidget(lblAgreeId, 0,2)
        layout.addWidget(self.lineAgreement,0,3)
        layout.addWidget(lblHorse,1,0)
        layout.addWidget(self.lineHorse,1,1)
        layout.addWidget(lblBreaker, 1,2)
        layout.addWidget(self.lineBreaker, 1, 3)
        layout.addWidget(lblDos, 2, 0)
        layout.addWidget(self.dateDos,2,1)
        layout.addWidget(lblDays,2,2)
        layout.addWidget(self.lineDays)
        layout.addWidget(lblDor,3,0)
        layout.addWidget(self.dateDor,3,1)
        layout.addWidget(self.notes,3,2, 1,2)
        layout.addWidget(lblBreakType, 4, 0)
        layout.addWidget(self.comboType,4,1)
        layout.addWidget(lblBreakRate,4,2)
        layout.addWidget(self.comboRate)

        hLayout = QHBoxLayout()
        hLayout.addSpacing(100)
        if self.mode != OPEN_NEW:
            hLayout.addWidget(self.pushReset)
            hLayout.addWidget(self.pushDelete)
            self.setWindowTitle("Editing " + self.windowTitle())
        hLayout.addWidget(self.pushCancel)
        hLayout.addSpacing(100)
        hLayout.addWidget(self.pushSave)

        vLayout = QVBoxLayout()
        vLayout.addLayout(layout)
        vLayout.addWidget(lblDetail)
        vLayout.addWidget(self.table)
        vLayout.addLayout(hLayout)
        self.setLayout(vLayout)

    def getLastBoardDate(self):
        """Set the minimum date as the last boarding date if available,
        otherwise as the agreement signing date."""
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL system_minimumdate({})".format(self.agreementId))
            if qry.lastError().type() != 0:
                raise DataError("getLastBoardDate", qry.lastError().text())
            if qry.first():
                return qry.value(0)

        except DataError as err:
            print(err.source, err.message)

    def getHorseData(self):
        row = self.table.currentIndex().row()
        self.table.model().query().seek(row)
        record = self.table.model().query().record()
        msg = "Receive {} from breaking with {} ?".format(
                                       record.value(2), record.value(0)) if self.mode == OPEN_NEW else \
            "Edit/Delete {} from breaking with {} ?".format(
                    record.value(2), record.value(0))
        try:
            res = QMessageBox.question(self,"Receiving Horse",msg, QMessageBox.Yes|QMessageBox.No)
            if res != QMessageBox.Yes:
                self.clearForm()
            else:
                self.lineProvider.setText(record.value(0))
                self.lineAgreement.setText(str(record.value(1)))
                self.lineHorse.setText(record.value(2))
                self.lineBreaker.setText(record.value(3))
                self.dateDos.setDate(record.value(4))
                self.lineDays.setText(str(record.value(5)))
                self.agreementHorseId = record.value(6)
                self.horseId = record.value(7)
                self.halfBreak = record.value(8)
                if self.mode == OPEN_EDIT:
                    self.dateDor.setDate(record.value(10))
                    self.breakingId = record.value(9)
                    self.comboType.setCurrentIndex(record.value(11))
                    self.comboRate.setCurrentIndex(record.value(12))
                    self.notes.setText(record.value(13))
                    self.pushReset.setEnabled(True)
                self.pushSave.setEnabled(False)
                self.pushDelete.setEnabled(True)

        except ValueError:
            return
        except Exception as err:
            print('getHorseData', type(err).__name__, err.args)

    def clearForm(self):
        self.lineHorse.clear()
        self.lineDays.clear()
        self.lineBreaker.clear()
        self.lineAgreement.clear()
        self.lineProvider.clear()
        self.comboRate.setCurrentIndex(-1)
        self.comboType.setCurrentIndex(-1)
        self.dateDos.setDate(QDate(99, 99, 99))
        self.dateDor.setDate(QDate(99, 99, 99))
        self.notes.clear()
        self.agreementHorseId = None
        self.horseId = None
        return


    def enableSave(self):
        if self.window().isVisible():
            if self.mode == OPEN_EDIT:
                self.pushSave.setEnabled(True)
                return
            if self.dateDor.text != 'None' \
                    and len(self.comboType.currentText()) > 0 \
                    and len(self.comboRate.currentText()) > 0 \
                    and len(self.lineHorse.text()) > 0 :
                self.pushSave.setEnabled(True)
            else:
                self.pushSave.setEnabled(False)

    def saveAndClose(self):
        """"Requieres to save on breaking table  and payables table .and to update broke in horses and active in agreementhorses?
        Remember to transfer the horses to the ownere´s main location or establish a new contract with the horses
         currently located"""
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL receivebroken_save({}, '{}',{},{}, '{}', {}, {}, {}, {})".format(
                self.agreementHorseId,
                self.dateDor.date.toString("yyyy-MM-dd"),
                self.comboType.getHiddenData(0),
                self.comboRate.getHiddenData(0),
                self.notes.toPlainText(),
                self.horseId,
                self.halfBreak,
                self.mode,
                self.breakingId if self.breakingId else 'NULL'))
            if qry.lastError().type() != 0:
                raise DataError("saveAndClose", qry.lastError().text())
            if qry.first():
                print(qry.value(0), qry.value(1))
            self.resetWidget()

        except DataError as err:
            print(err.source, err.message)
            # raise DataError(err.source, err.message)
            self.parent.messageBox(err.source, err.message)
            raise DataError(err)
        except Exception as err:
            print('saveAndClose',type(err).__name__, err.args)


    def conTest(self):
        if self.cnx.open:
            print("y")

    @pyqtSlot()
    def resetWidget(self):
        self.lineHorse.clear()
        self.lineDays.clear()
        self.lineBreaker.clear()
        self.lineAgreement.clear()
        self.lineProvider.clear()
        self.comboRate.setCurrentIndex(-1)
        self.comboType.setCurrentIndex(-1)
        self.dateDos.setDate(QDate(99, 99, 99))
        self.dateDor.setDate(QDate(99, 99, 99))
        self.notes.clear()
        self.agreementHorseId = None
        self.horseId = None
        self.resetTables()

    @pyqtSlot()
    def deleteReception(self):
        ans = QMessageBox.question(self, 'Delete Reception', "This record once deleted can't be recoverd."
                                                             " Would you continue?",QMessageBox.Yes | QMessageBox.No)
        if ans != QMessageBox.Yes:
            return
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL receivebroken_delete({}, {}, {}, {})".format(self.agreementHorseId,
                                                           self.comboType.getHiddenData(0),
                                                          self.horseId,
                                                          self.breakingId))
            if qry.lastError().type() != 0:
                raise DataError('deleteReception', qry.lastError().text())
            if qry.first():
                print(qry.value(0), qry.value(1))
            self.resetWidget()
            self.parent.setTableBreaking()
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print('deleteReception', err.args)


    def resetTables(self):
        try:
            qryLoad = QSqlQuery(self.db)
            qryLoad.exec("CALL receivebroken_loadhorses({}, '{}', {})".format(self.agreementId,
                                                                              self.dateDor.date.toString("yyyy-MM-dd"),
                                                                              self.mode))
            if qryLoad.lastError().type() != 0:
                raise DataError("setUI - load horse", qryLoad.lastError().text())
            if qryLoad.size() < 1 :
                QMessageBox.warning(self, "No data", "There are not more horses to be considered!",QMessageBox.Ok)
                self.closeWidget()
            self.table.model().setQuery(qryLoad)
            qry = self.parent.queryBreaking()
            self.parent.dockBreaking.widget().model().setQuery(qry)

        except DataError as err:
            print(err.source, err.message)

        except AttributeError as err:
            print("retetTables", err.args)

    @pyqtSlot()
    def closeWidget(self):
        super().close()
        #self.done(QDialog.Rejected)
