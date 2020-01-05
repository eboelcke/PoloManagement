from ext.MySQLConnector import MySQLConnector
from PyQt5.QtWidgets import (QDialog, QLabel, QLineEdit, QDateEdit, QGridLayout, QHBoxLayout,
                             QTableView, QVBoxLayout, QPushButton, QTextEdit, QHeaderView,
                             QMessageBox)
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import QSettings, QVariant, QDate, Qt
#from ext.CQSqlDatabase import Cdatabase
from ext.APM import (FocusCombo, QSqlAlignColorQueryModel,NullDateEdit, DataError,
                     PAYABLES_TYPE_FULL_BREAK, PAYABLES_TYPE_HALF_BREAK,
                     BRAKE_TYPE_FINAL, BRAKE_TYPE_HALFBREAKE, BRAKE_TYPE_INCOMPLETE)
from PyQt5.QtSql import QSqlQuery
import pymysql

class ReceiveBroken(QDialog):

    def __init__(self, db, con_string, agreementId=None, parent=None):
        super().__init__()
        self.horseId = None
        self.halfBreak = None
        self.agreementHorseId = None
        self.agreementId = agreementId
        self.con_string = con_string
        self.db = db
        if not self.db.isOpen():
            self.db.open()
        self.parent = parent
        self.supplierId = parent.supplierId
        if not self.db.isOpen():
            self.db.open()
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
        self.dateDor.setDate(self.dateDor.date)
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

        self.pushSave = QPushButton('Save')
        self.pushSave.clicked.connect(self.saveAndClose)
        self.pushSave.setEnabled(False)

        self.pushCancel = QPushButton('Cancel')
        self.pushCancel.clicked.connect(self.close)

        self.table = QTableView()
        self.table.doubleClicked.connect(self.getHorseData)

        centerColumns = [1, 5]
        colorDict = {}
        rightColumns = []
        model = QSqlAlignColorQueryModel(centerColumns, rightColumns, colorDict)
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
            self.table.hideColumn(8)

            header = self.table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

            self.table.verticalHeader().setDefaultSectionSize(25)
            self.table.horizontalHeader().setStyleSheet("QHeaderView { font-size: 8pt;}")
            self.table.setStyleSheet("QTableView {font-size: 8pt;}")

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

    def getLastBoardDate(self):
        try:
            qry = QSqlQuery(self.db)
            qry.prepare("""SELECT MAX(b.boardingdate) FROM 
            agreements a
            INNER JOIN agreementhorses ah 
            ON a.id = ah.agreementid
            INNER JOIN boarding  b 
            ON a.supplierid = b.supplierid 
            WHERE a.id= ?""")
            qry.addBindValue(QVariant(self.agreementId))
            qry.exec()
            if qry.lastError().type() != 0:
                raise DataError("getLastBoardDate", qry.lastError().text())
            qry.first()
            if not qry.value(0).isNull():
                return qry.value(0)
            return qry.value(1)
        except DataError as err:
            print(err.source, err.message)

    def loadHorses(self):

        try:
            qry = QSqlQuery(self.db)
            sql_qry = """
                         SELECT 
                         c.fullname AS Provider, 
                          a.id AS 'Agreement ID',
                          h.name as Horse, 
                          cb.fullname AS breaker,
                          ah.dos AS 'Starting Date',
                          TIMESTAMPDIFF(DAY, ah.dos, CURRENT_DATE()) AS Days,
                          ah.id AS 'agreementhorseid',
                          h.id as horseid,
                          a.halfbreakpercent as half
                          FROM agreements as a
                          INNER JOIN agreementhorses as ah
                          ON a.id = ah.agreementid
                          INNER JOIN  horses as h
                          ON ah.horseid = h.id
                          INNER JOIN contacts as c
                          ON a.supplierid = c.id
                          LEFT JOIN contacts as cb
                          ON ah.breakerid = cb.id
                          WHERE h.isbroke = False
                          AND ah.dos IS NOT null
                          AND ah.billable = TRUE  
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
            return qry
        except DataError as err:
            print(err.source, err.message)
            raise DataError(err.source, err.message)
            #self.parent.messageBox(self,err.source, err.message)
        except Exception as err:
            print('loadHorses', type(err).__name__, err.args)

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
                self.halfBreak = record.value(8)

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
        """"Requieres to save on breaking table  and payables table .and to update broke in horses and active in agreementhorses?
        Remember to transfer the hores to the ownere´s main location or establish a new contract with the horses
         currently located"""
        try:
            qryAmount = QSqlQuery(self.db)
            cnn = pymysql.connect(**self.con_string)
            cnn.begin()
            with cnn.cursor() as cur:
                sql_breaking = """ INSERT INTO breaking
                (agreementhorseid, dor, type, rate, notes)
                VALUES (%s, %s, %s, %s, %s)"""
                parameters = (self.agreementHorseId,
                              self.dateDor.date.toString('yyyy-MM-dd'),
                              self.comboType.getHiddenData(0),
                              self.comboRate.getHiddenData(0),
                              self.notes.toPlainText())
                cur.execute(sql_breaking, parameters)
                breakingid = cur.lastrowid
                if parameters[2] == BRAKE_TYPE_FINAL:
                    sql_horses = """ UPDATE horses 
                    SET isbroke = 1, 
                    isbreakable = 0
                    WHERE id = %s"""
                    cur.execute(sql_horses, (self.horseId,))
                    qryAmount.prepare("""
                                SELECT 
                                a.totalamount - COALESCE(SUM(p.amount),0)
                                FROM agreements a 
                                INNER JOIN  agreementhorses ah
                                ON a.id = ah.agreementid
                                LEFT JOIN payables p
                                ON ah.id = p.agreementhorseid
                                WHERE (p.typeid = 0 OR p.typeid = 1 OR p.typeid IS NULL) 
                                AND ah.id = ? """)
                    qryAmount.addBindValue(self.agreementHorseId)
                    qryAmount.exec()
                    if qryAmount.lastError().type() != 0:
                        raise DataError("saveAndClose", qryAmount.lastError().text())
                    if qryAmount.first():
                        if qryAmount.value(0) > 0:
                            sql_payable = """INSERT INTO payables 
                                (agreementhorseid, ticketid, concept, amount, typeid) 
                                VALUES (%s, %s, %s, %s, %s)"""
                            parampay = (self.agreementHorseId, breakingid, "Final payment for the break of {}".format(self.lineHorse.text()),
                            qryAmount.value(0),PAYABLES_TYPE_FULL_BREAK)
                            cur.execute(sql_payable, parampay)
                if parameters[2] == BRAKE_TYPE_HALFBREAKE and self.halfBreak:
                    qryAmount.prepare("""
                                SELECT 
                                COALESCE(a.halfbreakpercent * a.totalamount * 0.01 - SUM(p.amount), 0 ) 
                                FROM agreements a
                                INNER JOIN agreementhorses ah
                                ON a.id = ah.agreementid
                                LEFT JOIN  payables P
                                ON  ah.id = p.agreementhorseid  
                                WHERE (p.typeid = 0 OR p.typeid = 1 OR p.typeid = 2 OR p.typeid = 3)
                                AND ah.id = ? 
                                GROUP BY ah.id""")
                    qryAmount.addBindValue(self.agreementHorseId)
                    qryAmount.exec()
                    if qryAmount.lastError().type() != 0:
                        raise DataError("saveAndClose", qryAmount.lastError().text())
                    if qryAmount.first():
                        if qryAmount.value(0) > 0:
                            sql_payable = """INSERT INTO payables 
                                (agreementhorseid, ticketid, concept, amount, typeid) 
                                VALUES (%s, %s, %s, %s, %s)"""
                            parampay = (self.agreementHorseId, breakingid,
                                        "Final payment for the half-break of {}".format(self.lineHorse.text()),
                            qryAmount.value(0),PAYABLES_TYPE_HALF_BREAK)
                            cur.execute(sql_payable, parampay)
                sql_agreementhorses = """ UPDATE agreementhorses
                    SET billable = False 
                    WHERE id = %s"""
                cur.execute(sql_agreementhorses, self.agreementHorseId)
            cnn.commit()
            self.table.model().setQuery(self.loadHorses())
            self.clearForm()
        except DataError as err:
            print(err.source, err.message)
            #raise DataError(err.source, err.message)
            self.parent.messageBox(err.source, err.message)
            cnn.rollback()
        except pymysql.Error as err:
            print("saveAndClose",err.args)
            cnn.rollback()
        except Exception as err:
            print('saveAndClose',type(err).__name__, err.args)
        finally:
            cnn.close()


    def conTest(self):
        if self.cnx.open:
            print("y")

