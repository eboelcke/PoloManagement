import sys
from PyQt5.QtWidgets import (QDialog, QLabel, QLineEdit,QAbstractItemView,QWidget,
QPushButton, QFormLayout, QGridLayout, QApplication, QDateEdit, QTextEdit, QCheckBox,
                             QVBoxLayout, QHBoxLayout, QFormLayout, QMessageBox, QTableView, QComboBox,
                             )
from PyQt5.QtGui import QColor
from PyQt5.QtSql import QSqlDatabase, QSqlQuery
from PyQt5.QtCore import pyqtSlot, QVariant, QDate
from PyQt5.QtSql import QSqlQuery, QSqlQueryModel
from ext.CQSqlDatabase import Cdatabase
from ext.APM import NullDateEdit, TableViewAndModel, DataError
from ext import APM

class CheckHorse(QDialog):
    def __init__(self, record=None, qdb=None, mode=APM.OPEN_EDIT_ONE, parent=None):
        super().__init__()
        self.horseDb = Cdatabase(qdb, 'dqdb')
        self.record = record
        self.mode = mode
        try:
            self.setUI()
            self.parent = parent
            if mode == APM.OPEN_EDIT_ONE:
                self.loadUI()
            else:
                self.loadComboBoxes()
            self.setModal(True)
            self.dirty = False
        except DataError as err:
            raise DataError(err.source, err.message)

    def setUI(self):
        try:
            lblName = QLabel("Name")
            self.lineName = QLineEdit()
            self.lineName.setToolTip("Horse Name")
            self.lineName.setEnabled(False)

            lblSex = QLabel("Sex")
            self.lineSex = QLineEdit(self)
            self.lineSex.setToolTip("Horse Sex")
            self.lineSex.setMinimumWidth(200)
            self.lineSex.setEnabled(False)

            lblCoat = QLabel("Coat")
            self.lineCoat = QLineEdit()
            self.lineCoat.setToolTip("Horse Coat")
            self.lineCoat.setMinimumWidth(200)
            self.lineCoat.setEnabled(False)

            lblRp = QLabel("RP")
            self.lineRp = QLineEdit()
            self.lineRp.setToolTip("Horse RP  ")
            self.lineRp.setMaximumWidth(70)
            self.lineRp.setEnabled(False)

            lblDob = QLabel("Birth Date")
            self.dateDob = NullDateEdit(self)
            self.dateDob.setToolTip("Birth Date")
            self.dateDob.setMinimumDate(QDate.currentDate().addYears(-25))
            self.dateDob.setEnabled(False)

            lblDos = QLabel("Starting Date")
            self.dateDos = NullDateEdit(self)
            self.dateDos.setToolTip("Starting Date")
            self.dateDos.setMinimumDate(QDate.currentDate().addYears(-5))
            self.dateDos.doubleClicked.connect(self.clearDos)

            lblNotes = QLabel("Notes")
            self.notes = QTextEdit()
            self.notes.setToolTip("Notes on this horse")
            self.notes.textChanged.connect(self.enableSave)

            self.checkBroke = QCheckBox("Broke")
            self.checkBroke.setToolTip("Is the horse broke")
            self.checkBroke.setEnabled(False)

            self.checkEligible = QCheckBox('Eligible')
            self.checkEligible.setToolTip("Eligibility")
            self.checkEligible.setEnabled(False)

            self.checkActive = QCheckBox("Active")
            self.checkActive.setToolTip("Weather the Horse is active")
            self.checkActive.setEnabled(False)

            self.checkBillable = QCheckBox("Billable")
            self.checkBillable.setToolTip("Horse is billable")
            self.checkBillable.setEnabled(False)

            lblHorseBaseId = QLabel("Horsebase ID")
            self.lineHorseBaseId = QLineEdit()
            self.lineHorseBaseId.setMaximumWidth(50)
            self.lineHorseBaseId.setEnabled(False)

            self.pushSave = QPushButton("Save")
            self.pushSave.setMaximumWidth(60)
            self.pushSave.setEnabled(False)
            self.pushSave.clicked.connect(self.saveAndClose)

            pushCancel = QPushButton("Cancel")
            pushCancel.setMaximumWidth(60)
            pushCancel.clicked.connect(self.close)
            pushCancel.setFocus()

            hLayoutButtons = QHBoxLayout()
            hLayoutButtons.addSpacing(500)
            hLayoutButtons.addWidget(pushCancel)
            hLayoutButtons.addWidget(self.pushSave)

            hLayoutRp = QHBoxLayout()
            hLayoutRp.addWidget(lblRp)
            hLayoutRp.addWidget(self.lineRp)

            hLayoutAccessID = QHBoxLayout()
            hLayoutAccessID.addWidget(lblHorseBaseId)
            hLayoutAccessID.addWidget(self.lineHorseBaseId)
            hLayoutAccessID.addSpacing(100)

            hLayoutCheck = QHBoxLayout()
            hLayoutCheck.addWidget(self.checkBroke)
            hLayoutCheck.addWidget(self.checkEligible)
            hLayoutCheck.addWidget(self.checkBillable)
            hLayoutCheck.addWidget(self.checkActive)

            hLayoutName = QHBoxLayout()
            hLayoutName.addWidget(lblName)
            hLayoutName.addWidget(self.lineName)

            hLayoutRp = QHBoxLayout()
            hLayoutRp.addWidget(lblRp)
            hLayoutRp.addWidget(self.lineRp)

            hLayoutSex = QHBoxLayout()
            hLayoutSex.addWidget(lblSex)
            hLayoutSex.addWidget(self.lineSex)

            hLayoutCoat = QHBoxLayout()
            hLayoutCoat.addWidget(lblCoat)
            hLayoutCoat.addWidget(self.lineCoat)

            hLayoutDob = QHBoxLayout()
            hLayoutDob.addWidget(lblDob)
            hLayoutDob.addWidget(self.dateDob)

            hLayoutDos = QHBoxLayout()
            hLayoutDos.addWidget(lblDos)
            hLayoutDos.addWidget(self.dateDos)


            gLayout = QGridLayout()
            gLayout.addLayout(hLayoutName, 0, 0)
            gLayout.addLayout(hLayoutRp, 0,1)
            gLayout.addLayout(hLayoutAccessID, 0,2)
            gLayout.addLayout(hLayoutSex, 1, 0)
            gLayout.addLayout(hLayoutCoat, 1, 1)
            gLayout.addLayout(hLayoutDob, 1, 2)
            gLayout.addLayout(hLayoutCheck, 2, 0)
            gLayout.addLayout(hLayoutDos,2,2)

            vLayout = QVBoxLayout()
            vLayout.addLayout(gLayout)
            vLayout.addWidget(lblNotes)
            vLayout.addWidget(self.notes)
            """When the mode is APM.OPEN_EDIT there the widget will include
            two comboBoxes - One for Client and other for agreement, the will
            show in a tableView the agreement horses that were not started so far"""
            if self.mode == APM.OPEN_EDIT:
                self.dateDob.setMinimumDate(QDate(2000, 1, 1))

                lblProvider = QLabel("Provider:")
                modelProvider = QSqlQueryModel()
                self.comboProvider = QComboBox()
                self.comboProvider.setMinimumWidth(200)
                self.comboProvider.setModel(modelProvider)
                self.comboProvider.activated[int].connect(self.setProvider)

                lblAgreement = QLabel("Agreement ID")
                modelAgreementId = QSqlQueryModel()
                self.comboAgreementID = QComboBox()
                self.comboAgreementID.setMinimumWidth(100)
                self.comboAgreementID.setModel(modelAgreementId)
                self.comboAgreementID.activated[int].connect(self.setAgreement)

                lblUnstarted = QLabel("Horses to Start")
                self.tableUnStarted = self.getTableViewAndModel()
                self.tableUnStarted.selectionModel().selectionChanged.connect(self.tableUnstartedSelectionchanged)

                comboLayout = QHBoxLayout()
                comboLayout.addWidget(lblProvider)
                comboLayout.addWidget(self.comboProvider)
                #comboLayout.addSpacing(300)
                comboLayout.addWidget(lblAgreement)
                comboLayout.addWidget(self.comboAgreementID)
                comboLayout.addSpacing(300)
                vLayout.addLayout(comboLayout)
                vLayout.addWidget(lblUnstarted)
                vLayout.addWidget(self.tableUnStarted)
            vLayout.addLayout(hLayoutButtons)
            self.setLayout(vLayout)
            self.setMinimumWidth(950)
            self.setMaximumWidth(self.minimumWidth())
        except DataError as err:
            raise DataError(err.source, err.message)

    def clearUI(self):
        self.setWindowTitle("Unstarted Horses")
        #self.dateDos.setMinimumDate(self.record.value('doa').addDays(-1))
        self.lineName.setText('')
        self.lineRp.setText('')
        self.lineSex.setText('')
        self.lineCoat.setText('')
        self.lineHorseBaseId.setText('')
        self.dateDob.setDate(QDate())
        self.dateDos.setDate(QDate())
        self.checkBroke.setChecked(False)
        self.checkBillable.setChecked(False)
        self.checkEligible.setChecked(False)
        self.checkActive.setChecked(False)
        self.notes.setText('')

    def loadUI(self):
        self.setWindowTitle(self.record.value('name'))
        self.dateDos.setMinimumDate(self.record.value('doa').addDays(-1))
        self.lineName.setText(self.record.value('name'))
        self.lineRp.setText(self.record.value('rp'))
        self.lineSex.setText(self.record.value('sex_name'))
        self.lineCoat.setText(self.record.value('coat'))
        self.lineHorseBaseId.setText(str(self.record.value('accessid')))
        self.dateDob.setDate(self.record.value('dob'))
        self.dateDos.setDate(self.record.value('dos'))
        self.checkBroke.setChecked(True) if self.record.value('broke') else self.checkBroke.setChecked(False)
        self.checkBillable.setChecked(True) if self.record.value('billable') else self.checkBillable.setChecked(False)
        self.checkEligible.setChecked(True) if self.record.value('eligible') else self.checkEligible.setChecked(False)
        self.checkActive.setChecked(True) if self.record.value('active') else self.checkActive.setChecked(False)
        self.notes.setText(self.record.value('Notes'))

    def getTableViewAndModel(self):
        try:
            centerColumns = []
            colDict = {0: ("ID", True, False, False,0),
                       1: ("Provider", False, True,False, 120),
                       2: ("AID", False, True, True, 45),
                       3: ("DOA", False, True, False, 80),
                       4: ("RP", False, True, True, 45),
                       5:("Horse", False, False, False,120),
                       6:("Sex", False, True, True, 45),
                       7:("Coat", False, True, False, 60),
                       8:("DOS", False, True, True, 80),
                       9:("Notes", True, False, False, 0),
                       10:("SexName", True, False, False, 0),
                       11:("Billable", True, False, False, 0),
                       12:("Broke", True, False, False, 0),
                       13: ("DOB", True, False, False, 0),
                       14: ("DOA", True, False, False, 0),
                       15: ("AccessID", True, False, False,0),
                       16: ("Active", True, False, False, 0),
                       17: ("CID", True, False, False, 0)}

            colorDict = colorDict = {'column':(6),
                        u'\u2640':(QColor('pink'), QColor('black')),
                        u'\u2642':(QColor('lightskyblue'), QColor('black')),
                        u'\u265E': (QColor('lightgrey'), QColor('black'))}
            qryHorses =self.queryUnstartedHorses()
            if qryHorses.size() == 0 :
                raise DataError("getTableViewAndModel", "There are not unstarted horses!")

            table = APM.TableViewAndModel(colDict, colorDict, (500, 300), qryHorses)
            table.setSelectionMode(QAbstractItemView.SingleSelection)
            table.selectionModel().selectionChanged.connect(self.getHorseData)
            table.horizontalHeader().setStyleSheet("QHeaderView {font-size: 8pt; text-align: center;}")
            table.verticalHeader().setVisible(False)
            table.doubleClicked.connect(self.loadUnstartedHorse)
            return table
        except DataError as err:
            raise DataError(err.source, err.message)

    def queryUnstartedHorses(self, providerId=None, agreementId=None):
        with Cdatabase(self.horseDb) as cdb:
            qry = QSqlQuery(cdb)
            sqlString = """
            SELECT 
            ah.id,
            co.fullname,
            a.id, 
            a.date, 
            h.rp,
            h.name,
            CASE WHEN h.sexid = 1 THEN _ucs2 X'2642'
                 WHEN h.sexid = 2 THEN _ucs2 X'2640'
                 WHEN h.sexid = 3 THEN _ucs2 X'265E'
            END Sex,
            c.coat,
            ah.dos,
            ah.notes,
            s.sex as Sex_name,
            ah.billable,
            h.isbroke as broke,
            h.dob as DOB,
            a.date as DOA,
            h.horseBaseId as AccessID,
            ah.active as Active,
            co.id as CID
            FROM agreementhorses as ah
            INNER JOIN horses as h ON ah.horseid = h.id 
            INNER JOIN coats as c ON h.coatid = c.id 
            INNER JOIN sexes as s ON h.sexid = s.id
            INNER JOIN agreements as a on ah.agreementid = a.id
            INNER JOIN contacts as co ON a.supplierID = co.id
            WHERE ISNULL(ah.dos)"""
            if providerId is not None:
                sqlString += """ AND  co.id = ? """
                if agreementId is not None:
                    sqlString += " AND a.id = ? "
            sqlString += """ ORDER BY co.fullname, s.sex """
            qry.prepare(sqlString)
            self.setWindowTitle("Unstarted Horses")
            if providerId:
                qry.addBindValue(QVariant(providerId))
                self.setWindowTitle("{} with {}".format(self.windowTitle(), self.comboProvider.currentText()))
                if agreementId:
                    qry.addBindValue(QVariant(agreementId))
                    self.setWindowTitle(" {} Agreement # {}".format(self.windowTitle(),
                                                                    self.comboAgreementID.currentText()))
            qry.exec_()
        return qry

    def loadComboBoxes(self):
        modelProvider = QSqlQueryModel()
        qryProvider = QSqlQuery(self.horseDb)
        qryProvider.prepare(
            """SELECT DISTINCT co.fullname, co.id 
            FROM contacts as co
            INNER JOIN agreements as a
            ON co.id = a.supplierid
            INNER JOIN  agreementhorses as ah
            ON ah.agreementid = a.id
            WHERE ISNULL(ah.dos) 
            """)
        qryProvider.exec_()
        modelProvider.setQuery(qryProvider)
        self.comboProvider.model().setQuery(qryProvider)

    @pyqtSlot()
    def loadUnstartedHorse(self):
        row = self.tableUnStarted.currentIndex().row()
        model = self.tableUnStarted.model()
        model.query().isSelect()
        model.query().isActive()
        model.query().seek(row)
        record = model.query().record()
        res = QMessageBox.warning(self, "{}".format(record.value(5)),
                             'Would you check or edit the data as neccesary',QMessageBox.Yes | QMessageBox.No)
        if res != QMessageBox.Yes:
            return
        self.setWindowTitle(record.value(5))
        self.record = record
        self.loadUI()

    @pyqtSlot(int)
    def setAgreement(self, row):
        idx = self.comboAgreementID.model().index(row, 0)
        agreeId = self.comboAgreementID.model().data(idx)

        row = self.comboProvider.currentIndex()
        idx = self.comboProvider.model().index(row, 1)
        provId = self.comboProvider.model().data(idx)
        qry = self.queryUnstartedHorses(providerId=provId,agreementId=agreeId)
        self.tableUnStarted.model().setQuery(qry)

    @pyqtSlot(int)
    def setProvider(self, row):
        idx = self.comboProvider.model().index(row, 1)
        provId = self.comboProvider.model().data(idx)
        qry = self.queryUnstartedHorses(providerId=provId)
        self.tableUnStarted.model().setQuery(qry)
        self.enableComboAgreement(provId)

    def enableComboAgreement(self,Id):
        qry = QSqlQuery(self.horseDb)
        qry.prepare("""
        SELECT id FROM agreements 
        WHERE supplierID = ?""")
        qry.addBindValue(QVariant(Id))
        qry.exec_()
        self.comboAgreementID.model().setQuery(qry)

    @pyqtSlot()
    def getHorseData(self):
        pass

    @pyqtSlot()
    def clearDos(self):
        self.dateDos.setDate(QDate())
        self.dateDos.clearDate()

    def enableSave(self):
        self.dirty = True
        self.checkDirty()

    @pyqtSlot()
    def checkDirty(self):
        if self.isVisible() and self.record:
            self.pushSave.setEnabled(True)

    @pyqtSlot()
    def saveAndClose(self):
        dos = None if self.dateDos.text == 'None' else self.dateDos.date.toString('yyyy-MM-dd')
        with self.horseDb as dbh:
            qry = QSqlQuery(dbh)
            qry.prepare("""
            UPDATE agreementhorses SET dos = ?,notes = ? WHERE id = ?;""")
            qry.addBindValue(QVariant(dos))
            qry.addBindValue(QVariant(self.notes.toHtml()))
            qry.addBindValue(QVariant(self.record.value('id')))
            qry.exec_()
            if qry.numRowsAffected() == 1:
                self.dirty = False
                self.parent.setDockHorses
        if self.mode == APM.OPEN_EDIT_ONE:
            self.close()
        qry = self.queryUnstartedHorses(self.record.value('cid'), self.record.value('aid'))
        if qry.size() == 0:
            qry = self.queryUnstartedHorses()
            self.loadComboBoxes()
        self.clearUI()
        self.dirty = False
        self.tableUnStarted.model().setQuery(qry)
        return

    def closeWindow(self):
        res = self.close()

    @pyqtSlot()
    def tableUnstartedSelectionchanged(self):
        row = self.tableUnStarted.currentIndex().row()
        model = self.tableUnStarted.model()
        model.query().isSelect()
        model.query().isActive()
        model.query().seek(row)
        record = model.query().record()
        res = QMessageBox.warning(self, "{}".format(record.value(5)),
                             'Would you check or edit the data as neccesary',QMessageBox.Yes | QMessageBox.No)
        if res != QMessageBox.Yes:
            return
        self.setWindowTitle(record.value(5))
        self.record = record
        self.loadUI()
        print('Selection changed')



if __name__ == '__main__':
    app = QApplication(sys.argv)
    tst = CheckHorse(None)
    tst.show()
    app.exec()





