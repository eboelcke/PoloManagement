from ext.MySQLConnector import MySQLConnector
from PyQt5.QtWidgets import (QDialog, QLabel, QLineEdit, QDateEdit, QGridLayout, QHBoxLayout,
                             QTableView, QVBoxLayout, QPushButton, QTextEdit, QHeaderView,
                             QMessageBox)
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import QSettings, QVariant, QDate, Qt
from ext.CQSqlDatabase import Cdatabase
from ext.APM import FocusCombo, QSqlAlignColorQueryModel,NullDateEdit, DataError
from PyQt5.QtSql import QSqlQuery
import pymysql

class ReceiveBroken(QDialog):

    def __init__(self, db, con_string, agreementId=None):
        super().__init__()
        self.horseId = None
        self.agreementHorseId = None
        self.agreementId = agreementId
        self.con_string = con_string
        self.db = db
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
        self.dateDor.setMinimumDate(QDate.currentDate().addDays(-180))
        self.dateDor.setMinimumDate(QDate.currentDate())
        self.dateDor.setDate(QDate.currentDate())
        self.dateDor.dateChanged.connect(self.enableSave)


        keys = ('0', '1', '2', '3')
        types = ('Polo', 'Criolla', 'Half Break', 'Incomplete')
        typeModel = QStandardItemModel(4, 2)
        for row, type in enumerate(types):
            item = QStandardItem(keys[row])
            typeModel.setItem(row, 0, item)
            item = QStandardItem(types[row])
            typeModel.setItem(row, 1, item)


        lblBreakType = QLabel("Break Type")
        self.comboType = FocusCombo()
        self.comboType.addItems({'1':'Polo','2': 'Criolla', '3': '1/2 Break', '4': 'Incomplete'})
        self.comboType.addItem('23')
        self.comboType.setMaximumWidth(200)
        self.comboType.setModel(typeModel)
        self.comboType.setCurrentIndex(-1)
        self.comboType.setModelColumn(1)
        self.comboType.activated.connect(self.enableSave)

        rates = ('Excellent', 'Very Good', 'Fair', 'Poor')
        rateModel = QStandardItemModel(4, 2)

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

        self.pushSave = QPushButton('Save')
        self.pushSave.clicked.connect(self.saveAndClose)
        self.pushSave.setEnabled(False)

        self.pushCancel = QPushButton('Cancel')
        self.pushCancel.clicked.connect(self.close)

        self.table = QTableView()
        self.table.doubleClicked.connect(self.getHorseData)

        centerColumns = [1, 5]
        colorDict = {}
        model = QSqlAlignColorQueryModel(centerColumns, colorDict)
        try:
            model.setQuery(self.loadHorses())
            model.setHeaderData(0,Qt.Horizontal, 'Provider')
            model.setHeaderData(1, Qt.Horizontal,'ID')
            model.setHeaderData(2, Qt.Horizontal, 'Horse')
            model.setHeaderData(4, Qt.Horizontal, 'Start')
            model.setHeaderData(5, Qt.Horizontal, 'Days')

            self.table.setModel(model)
            self.table.verticalHeader().setVisible(False)
            self.table.hideColumn(3)
            self.table.hideColumn(6)
            self.table.hideColumn(7)

            header = self.table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

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
            hLayout.addWidget(self.pushCancel)
            hLayout.addSpacing(100)
            hLayout.addWidget(self.pushSave)

            vLayout = QVBoxLayout()
            vLayout.addLayout(layout)
            vLayout.addWidget(lblDetail)
            vLayout.addWidget(self.table)
            vLayout.addLayout(hLayout)
            self.setLayout(vLayout)
        except DataError as err:
            QMessageBox.warning(self, "There is no available data", err.message)
            raise DataError(err.source, err.message)
            return

    def loadHorses(self):
        with Cdatabase(self.db, 'Breaking') as cdb:
            qry = QSqlQuery(cdb)
            sql_qry = """
                         SELECT 
                         c.fullname AS Provider, 
                          a.id AS 'Agreement ID',
                          h.name as Horse, 
                          cb.fullname AS breaker,
                          ah.dos AS 'Starting Date',
                          TIMESTAMPDIFF(DAY, ah.dos, CURRENT_DATE()) AS Days,
                          ah.id AS 'agreementhorseid',
                          h.id as horseid
                          FROM agreements as a
                          INNER JOIN agreementhorses as ah
                          ON a.id = ah.agreementid
                          INNER JOIN  horses as h
                          ON ah.horseid = h.id
                          INNER JOIN contacts as c
                          ON a.supplierid = c.id
                          INNER JOIN contacts as cb
                          ON ah.breakerid = cb.id
                          WHERE h.isbroke = False
                          AND ah.dos IS NOT null
                          AND ah.active = TRUE  
                          """
            if self.agreementId:
                sql_qry += "AND a.id = ?"
            qry.prepare(sql_qry)
            if self.agreementId:
                qry.addBindValue(QVariant(self.agreementId))
            qry.exec()
            if qry.size() == 0:
                raise DataError("loadHorses","No Data Available")
            elif qry.size() == -1:
                raise DataError("loadHorses", qry.lastError().text())
            print(qry.size())
            return qry

    def getHorseData(self):
        row = self.table.currentIndex().row()
        self.table.model().query().seek(row)
        record = self.table.model().query().record()
        try:
            res = QMessageBox.question(self,
                                       "Receiving Horse",
                                       "Receive {} from breaking with {}".format(
                                       record.value(2), record.value(0)))
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

        except Exception as err:
            print(type(err).__name__, err.args)

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
            if self.dateDor.text != 'None' \
                    and len(self.comboType.currentText()) > 0 \
                    and len(self.comboRate.currentText()) > 0 \
                    and len(self.lineHorse.text()) > 0 :
                self.pushSave.setEnabled(True)
            else:
                self.pushSave.setEnabled(False)

    def saveAndClose(self):
        "Requieres to save on breaking table and to update broke in horses and active in agreementhorses? "
        try:
            cnn = pymysql.connect(**self.con_string)
            cnn.begin()
            with cnn.cursor() as cur:
                sql_breaking = """ INSERT INTO breaking
                (agreementhorseid, dor, type, rate, notes)
                VALUES (%s, %s, %s, %s, %s)"""
                self.comboType.setModelColumn(0)
                self.comboRate.setModelColumn(0)
                parameters = (self.agreementHorseId,
                              self.dateDor.date.toString('yyyy-MM-dd'),
                              self.comboType.currentText(),
                              self.comboRate.currentText(),
                              self.notes.toPlainText())
                cur.execute(sql_breaking, parameters)
                if int(parameters[2]) <= 2:
                    sql_horses = """ UPDATE horses 
                    SET isbroke = True 
                    WHERE id = %s"""
                    sql_agreementhorses = """ UPDATE agreementhorses
                    SET active = False 
                    WHERE id = %s"""
                    cur.execute(sql_horses, self.horseId )
                    cur.execute(sql_agreementhorses, self.agreementHorseId)
                cnn.commit()


        except pymysql.Error as err:
            QMessageBox.Warning("saveAndClose", (type(err).__name__ , err.args))
            cnn.rollback()
        finally:

            self.comboType.setModelColumn(1)
            self.comboRate.setModelColumn(1)
            self.table.model().setQuery(self.loadHorses())
            self.clearForm()

    def conTest(self):
        if self.cnx.open:
            print("y")

