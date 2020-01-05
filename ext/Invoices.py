import sys
import os
from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import (QDialog, QMessageBox, QFrame, QApplication, QVBoxLayout, QHBoxLayout,
                             QGridLayout, QLabel, QPushButton, QLineEdit,QTextEdit, QDateEdit, QCheckBox)
from PyQt5.QtGui import QDoubleValidator
import pymysql



from PyQt5.QtCore import Qt, QDate, pyqtSlot
from PyQt5.QtSql import QSqlDatabase, QSqlQueryModel, QSqlQuery
from ext.APM import (FocusCombo, TableViewAndModel,PAYABLES_TYPE_OTHER, PAYABLES_TYPE_BOARD,
    PAYABLES_TYPE_SALE, PAYABLES_TYPE_FULL_BREAK, PAYABLES_TYPE_HALF_BREAK, PAYABLES_TYPE_DOWNPAYMENT,DataError)

class Invoice(QDialog):
    def __init__(self, db, supplierId, payableType, mode=None, con_string=None, invoiceid=None, parent=None):
        super().__init__(parent=parent)
        self.db = db
        if not self.db.isOpen():
            self.db.isOpen()
        self.invoiceId = invoiceid
        self.con_string = con_string
        self.mode = mode
        self.parent = parent
        self.payableType = payableType
        self.supplierid = supplierId
        self.tempDb = None
        self.createTemporaryTables()
        self.setUI()


    def setUI(self):
        self.setModal(True)
        self.setMinimumSize(1000,600)
        self.setWindowTitle("Invoice")
        topFrame = QFrame()
        topFrame.setMaximumWidth(1000)
        topFrame.setFrameStyle(QFrame.Panel | QFrame.Plain)
        topFrame.setLineWidth(2)

        lblSupplier = QLabel('Supplier: ')
        self.lineSupplier = QLineEdit()
        self.lineSupplier.setEnabled(False)
        self.lineSupplier.setMinimumWidth(300)
        self.lineSupplier.setText(self.parent.supplier)


        lblNumber = QLabel("Number: ")
        self.lineNumber = QLineEdit()
        self.lineNumber.setMaximumWidth(100)
        self.lineNumber.setAlignment(Qt.AlignRight)
        self.lineNumber.editingFinished.connect(self.enableSave)


        self.lblTotal = QLabel('Total U$A')
        self.lineTotal = QLineEdit()
        self.lineTotal.setAlignment(Qt.AlignRight)
        self.lineTotal.setMaximumWidth(150)
        self.lineTotal.setEnabled(False)
        self.lineTotal.editingFinished.connect(self.enableSave)

        self.lblGrandTotal = QLabel("Total U$A")
        self.lblGrandTotal.hide()
        self.lineGrandTotal = QLineEdit()
        self.lineGrandTotal.setAlignment(Qt.AlignRight)
        self.lineGrandTotal.setMaximumWidth(150)
        self.lineGrandTotal.setEnabled(False)
        self.lineGrandTotal.hide()

        self.lblCurrencyTotal = QLabel("Currency ")
        self.lblCurrencyTotal.hide()
        self.lineCurrencyTotal = QLineEdit()
        self.lineCurrencyTotal.setAlignment(Qt.AlignRight)
        self.lineCurrencyTotal.setMaximumWidth(150)
        self.lineCurrencyTotal.setEnabled(False)
        self.lineCurrencyTotal.hide()
        self.lineCurrencyTotal.editingFinished.connect(self.enableSave)

        if QDate.currentDate().day() < 15:
            billDate = QDate.currentDate().addDays(- QDate.currentDate().day()+1)
        else:
            billDate = QDate.currentDate().addMonths(1).addDays(- QDate.currentDate().day() + 1)

        lblDate = QLabel('Date: ')
        self.dateInvoice = QDateEdit()
        self.dateInvoice.setCalendarPopup(True)
        self.dateInvoice.setDate(billDate)
        self.dateInvoice.setDisplayFormat('yyyy-MM-dd')
        self.dateInvoice.setMinimumWidth(120)
        self.dateInvoice.dateChanged.connect(self.enableSave)
        self.dateInvoice.dateChanged.connect(self.setPeriod)
        self.dateInvoice.dateChanged.connect(self.updateElegibleHorses)

        lblFrom = QLabel('From: ')
        self.dateFrom = QDateEdit()
        self.dateFrom.setCalendarPopup(True)
        #self.dateFrom.setDate(QDate.currentDate())
        self.dateFrom.setDisplayFormat('yyyy-MM-dd')
        self.dateFrom.setMinimumWidth(120)

        lblTo = QLabel('To: ')
        self.dateTo = QDateEdit()
        self.dateTo.setCalendarPopup(True)
        #self.dateTo.setDate(QDate.currentDate())
        self.dateTo.setDisplayFormat('yyyy-MM-dd')
        self.dateTo.setMinimumWidth(120)

        self.setPeriod()

        lblType = QLabel("Type")
        lblType.setStyleSheet("QLabel {background-color: red; color: white;}")
        lblType.setAlignment(Qt.AlignCenter)

        self.comboType = FocusCombo(itemList=['C', 'A'])
        self.comboType.setMinimumWidth(30)
        self.comboType.setModelColumn(1)
        self.comboType.setCurrentIndex(0)
        self.comboType.activated.connect(self.addIVA)

        lblInvoice = QLabel("Invoice type")
        self.comboInvoiceType = FocusCombo(itemList=['DownPayment', 'Board', 'Half Break', 'Final Break', 'Sale Share'])
        self.comboInvoiceType.setMinimumWidth(70)
        self.comboInvoiceType.setCurrentIndex(self.payableType)
        self.comboInvoiceType.setModelColumn(1)
        self.comboInvoiceType.setEnabled(False)

        lblCurrency = QLabel("Currency")
        self.comboCurrency = FocusCombo(itemList=['USA Dollar', 'Argentine Peso'])
        self.comboCurrency.setMinimumWidth(70)
        self.comboCurrency.setCurrentIndex(0)
        self.comboCurrency.setModelColumn(1)
        self.comboCurrency.activated.connect(self.setCurrency)

        self.lblIva = QLabel("IVA 21%")
        self.lblIva.hide()
        self.lineIva = QLineEdit()
        self.lineIva.setMaximumWidth(150)
        self.lineIva.setAlignment(Qt.AlignRight)
        self.lineIva.setEnabled(False)
        self.lineIva.hide()

        valExchange = QDoubleValidator(0.00, 999999.99,2)

        lblExchange = QLabel("Exchange Rate")
        self.lineExchange = QLineEdit()
        self.lineExchange.setMaximumWidth(100)
        self.lineExchange.setAlignment(Qt.AlignRight)
        self.lineExchange.setValidator(valExchange)
        self.lineExchange.setText("1.00")
        self.lineExchange.setEnabled(False)
        self.lineExchange.editingFinished.connect(self.refreshTables)

        lblNotes = QLabel("Notes")
        self.textNotes = QTextEdit()
        self.textNotes.setMaximumHeight(100)

        colorDict = {}
        colDict = {0:("ID", True, True, False, None),
                   1:("Horse", False, False, False, None),
                   2:("#", False, True, True, None),
                   3:("Payed", True, True, False, None),
                   4: ("DOS", False, True, True, None),
                   5:("Months", False, True, True, None),
                   6:("Installment", False,True, 2, None ),
                   7:("Total", True, True, False, None),
                   8:("Concept", True, True, False, None)}
        qry, qryBilled = self.getHorses()
        self.tableCheck = TableViewAndModel(colDict=colDict, colorDict=colorDict, size=(100,200), qry=qry)
        self.tableCheck.doubleClicked.connect(self.includeHorses)
        self.tableCheck.doubleClicked.connect(self.enableSave)

        colBilled = {0:("agreementhorseid", True, True, False, None),
                     1:("Horse",False, True, False, None ),
                     2:("Concept", False, False, False, None),
                     3:("Amount", False, True, 2, None)}

        self.tableBilled = TableViewAndModel(colDict=colBilled,colorDict=colorDict, size=(100,200),qry=qryBilled)
        self.tableBilled.doubleClicked.connect(self.excludeHorses)
        self.tableBilled.doubleClicked.connect(self.enableSave)

        pushCancel = QPushButton("Cancel")
        pushCancel.setMaximumWidth(70)
        pushCancel.clicked.connect(self.widgetClose)

        self.pushSave = QPushButton("Save")
        self.pushSave.setMaximumWidth(70)
        self.pushSave.setEnabled(False)
        self.pushSave.clicked.connect(self.saveAndClose)

        invoiceVLayout = QVBoxLayout()
        invoiceLayout_1 = QHBoxLayout()
        invoiceLayout = QHBoxLayout()

        invoiceLayout_1.addWidget(lblSupplier)
        invoiceLayout_1.addWidget(self.lineSupplier)
        invoiceLayout_1.addWidget(lblInvoice)
        invoiceLayout_1.addWidget(self.comboInvoiceType)
        invoiceLayout_1.addWidget(lblType)
        invoiceLayout_1.addWidget(self.comboType)
        invoiceLayout_1.addWidget(lblNumber)
        invoiceLayout_1.addWidget(self.lineNumber)

        invoiceLayout.addWidget(lblDate)
        invoiceLayout.addWidget(self.dateInvoice)

        invoiceLayout.addWidget(lblFrom)
        invoiceLayout.addWidget(self.dateFrom)
        invoiceLayout.addWidget(lblTo)
        invoiceLayout.addWidget(self.dateTo)

        invoiceVLayout.addLayout(invoiceLayout_1)
        invoiceVLayout.addLayout(invoiceLayout)

        topFrame.setLayout(invoiceVLayout)

        tablesLayout = QHBoxLayout()
        tablesLayout.addWidget(self.tableCheck)
        tablesLayout.addWidget(self.tableBilled)

        self.totalLayout = QGridLayout()
        self.totalLayout.addWidget(lblCurrency,0,0, Qt.AlignRight)
        self.totalLayout.addWidget(self.comboCurrency,0,1, Qt.AlignRight)
        self.totalLayout.addWidget(lblExchange,0,2,Qt.AlignRight)
        self.totalLayout.addWidget(self.lineExchange,0,3,Qt.AlignRight)
        self.totalLayout.addWidget(self.lblTotal,0,4, Qt.AlignRight)
        self.totalLayout.addWidget(self.lineTotal,0,5,Qt.AlignRight)
        self.totalLayout.addWidget(self.lblIva,1,4, Qt.AlignRight)
        self.totalLayout.addWidget(self.lineIva,1,5, Qt.AlignRight)
        self.totalLayout.addWidget(self.lblGrandTotal,2,4,Qt.AlignRight)
        self.totalLayout.addWidget(self.lineGrandTotal,2,5,Qt.AlignRight)
        self.totalLayout.addWidget(self.lblCurrencyTotal, 3, 4, Qt.AlignRight)
        self.totalLayout.addWidget(self.lineCurrencyTotal, 3, 5, Qt.AlignRight)

        totalFrame = QFrame()
        totalFrame.setLayout(self.totalLayout)
        totalFrame.setMinimumSize(50, 50)

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(pushCancel)
        buttonLayout.addWidget(self.pushSave)

        layout = QVBoxLayout()
        layout.addWidget(topFrame)
        layout.addLayout(tablesLayout)
        layout.addWidget(totalFrame)
        layout.addLayout(buttonLayout)
        layout.addWidget(self.textNotes)

        self.setLayout(layout)

    @pyqtSlot()
    def setPeriod(self):
        self.dateTo.setDate(self.dateInvoice.date().addDays(-1))
        self.dateFrom.setDate(self.dateInvoice.date().addDays(-
                self.dateInvoice.date().addDays(-28).daysInMonth()))

    @pyqtSlot()
    def enableSave(self):
        if not self.lineNumber.text() or \
            not self.lineTotal.text():
            return
        if self.lineCurrencyTotal.isEnabled():
            if not self.lineCurrencyTotal.text():
                return
        self.pushSave.setEnabled(True)

    @pyqtSlot()
    def widgetClose(self):
        if self.tempDb.isOpen():
            self.tempDb.close()
        self.done(QDialog.Rejected)

    @pyqtSlot()
    def updateElegibleHorses(self):
        qry = self.getHorses()[0]
        self.tableCheck.model().setQuery(qry)

    @pyqtSlot()
    def getHorses(self):
        try:
            qryTruncate = QSqlQuery(self.tempDb)
            qryTruncate.exec("TRUNCATE billablehorses")
            if qryTruncate.lastError().type() != 0:
                raise DataError("getHorses -Truncate-billable", qryTruncate.lastError().text())
            qryTruncate.exec("TRUNCATE billed")
            if qryTruncate.lastError().type() != 0:
                raise DataError("getHorses -Truncate-billed", qryTruncate.lastError().text())
            qry = QSqlQuery(self.tempDb)

            if self.payableType == PAYABLES_TYPE_BOARD:
                qry.prepare("""INSERT INTO billablehorses 
                (id, horse, agrid, amountpayed, dos, months, installment, totalamount, concept)
                SELECT 
                ah.id, h.name, a.id,
                COALESCE((SELECT SUM(amount) FROM invoicelines WHERE agreementhorseid = ah.id), 0) payed,
                ah.dos,
                TIMESTAMPDIFF(MONTH, ah.dos, ?) Months,
                ROUND((a.totalamount - a.downpayment)/ a.installments, 2) inst,
                a.totalamount,
                Null concept
                FROM horses h
                INNER JOIN agreementhorses ah
                ON h.id = ah.horseid
                INNER JOIN locationS l 
                ON h.locationid = l.id
                INNER JOIN agreements a
                    ON ah.agreementid = a.id
                WHERE
                ah.dos IS NOT NULL
                AND a.supplierid = ? 
                AND ah.active 
                AND (a.paymentoption = 1 OR (a.paymentoption = 2 AND l.contactid != 0))
                AND NOT EXISTS (SELECT i.id FROM invoices i 
                    INNER JOIN invoicelines il
                    ON i.id = il.invoiceid
                    WHERE 
                        il.agreementhorseid = ah.id    
                        AND i.invoiceDate > ?)
                 AND (a.paymentoption = 1 OR 
                    (a.paymentoption = 2 AND 
                        ( h.locationid IN 
                            (SELECT lo.id 
                            FROM locations lo 
                            WHERE lo.contactid = ?
                        )
                    ) OR EXISTS 
                        (SELECT t.date FROM transfers t 
                        INNER JOIN transferdetail td 
                        ON t.id = td.transferid
                        INNER JOIN locations lc 
                        ON t.toid = lc.id
                        WHERE td.agreementhorseid = ah.id 
                        AND lc.contactid = 0
                        AND t.date < ?
                        )
                    )
                )
                HAVING
                payed BETWEEN 0 AND a.totalamount""")
                qry.bindValue(0, QVariant(self.dateInvoice.date().toString("yyyy-MM-dd")))
                qry.bindValue(1, QVariant(self.supplierid))
                qry.bindValue(2, QVariant(self.dateInvoice.date().addDays(-28).toString("yyyy-MM-dd")))
                qry.bindValue(3, QVariant(self.supplierid))
                qry.bindValue(4,QVariant(self.dateInvoice.date().addDays(-15).toString("yyyy-MM-dd")))
                qry.exec()
                if qry.lastError().type() != 0:
                    raise DataError("getHorses -Board",qry.lastError().text() )

            elif self.payableType == PAYABLES_TYPE_DOWNPAYMENT:
                qry.prepare("""INSERT INTO billablehorses 
                                (id, horse, agrid, amountpayed, dos, months, installment,
                                 totalamount, concept)
                                SELECT 
                                ah.id, h.name, a.id,
                                COALESCE((SELECT SUM(il.amount) FROM invoices i 
                                    INNER JOIN invoicelines il
                                    ON i.id = il.invoiceid
                                    WHERE il.agreementhorseid = ah.id
                                    AND i.type = 0), 0) payed,
                                ah.dos,
                                TIMESTAMPDIFF(MONTH, ah.dos, ?) Months,
                                a.downpayment - COALESCE((SELECT SUM(il.amount) FROM invoices i 
                                    INNER JOIN invoicelines il
                                    ON i.id = il.invoiceid
                                    WHERE il.agreementhorseid = ah.id
                                    AND i.type = 0), 0) inst,
                                a.totalamount,
                                null concept
                                FROM horses h 
                                INNER JOIN agreementhorses ah
                                ON h.id = ah.horseid
                                INNER JOIN agreements a
                                ON ah.agreementid = a.id
                                WHERE ah.active 
                                AND a.supplierid = ? 
                                AND a.downpayment > 0
                                HAVING 
                                payed BETWEEN 0 AND inst """)
                qry.addBindValue(QVariant(self.dateInvoice.date().toString("yyyy-MM-dd")))
                qry.addBindValue(QVariant(self.supplierid))
                qry.exec()
                if qry.lastError().type() != 0:
                    raise DataError("getHorses -Downpayment",qry.lastError().text() )
            elif self.payableType == PAYABLES_TYPE_SALE:
                qry.prepare("""INSERT INTO billablehorses 
                                                (id, horse, agrid, amountpayed, dos, months, installment, 
                                                totalamount, concept)
                                                SELECT 
                                                ah.id, h.name, a.id,
                                                0 payed,
                                                ah.dos,
                                                TIMESTAMPDIFF(MONTH, ah.dos, ?) Months,
                                                p.amount inst,
                                                a.totalamount,
                                                p.concept
                                                FROM horses h 
                                                INNER JOIN agreementhorses ah
                                                ON h.id = ah.horseid
                                                INNER JOIN agreements a
                                                ON ah.agreementid = a.id
                                                INNER JOIN sales s
                                                ON ah.id = s.agreementhorseid
                                                INNER JOIN payables p 
                                                ON s.id = p.saleid
                                                WHERE NOT p.billed 
                                                AND a.supplierid = ? 
                                                """)
                qry.addBindValue(QVariant(self.dateInvoice.date().toString("yyyy-MM-dd")))
                qry.addBindValue(QVariant(self.supplierid))
                qry.exec()
                if qry.lastError().type() != 0:
                    raise DataError("getHorses -Sales", qry.lastError().text())
            elif self.payableType == PAYABLES_TYPE_FULL_BREAK:
                qry.prepare("""INSERT INTO billablehorses 
                (id, horse, agrid, amountpayed, dos, months, installment, 
                            totalamount, concept)
                SELECT 
                ah.id, h.name,
                COALESCE((SELECT SUM(amount) FROM invoicelines WHERE agreementhorseid = ah.id), 0) payed,
                ah.dos,
                TIMESTAMPDIFF(MONTH, ah.dos, ?) Months,
                p.amount inst,
                a.totalamount,
                p.concept
                FROM horses h
                INNER JOIN agreementhorses ah
                ON h.id = ah.horseid
                INNER JOIN agreements a
                    ON ah.agreementid = a.i
                INNER JOIN payables p
                
                            
                            
                
                param""")

            qryDisplay = QSqlQuery(self.tempDb)
            qryDisplay.exec("""SELECT id, horse, agrid, amountpayed, dos,
             months, installment, totalamount, concept
                               FROM billablehorses 
                               WHERE NOT billed
                               ORDER BY agrid, horse""")
            qryBilled = QSqlQuery(self.tempDb)
            qryBilled.exec("""SELECT id, horse, description, amount FROM billed""")
            return qryDisplay, qryBilled

        except DataError as err:
            print(err.source, err.message)

    def createTemporaryTables(self):
        try:
            if self.tempDb is None:
                self.tempDb = self.db.cloneDatabase(self.db, "Temp")
            if not self.tempDb.isOpen():
                self.tempDb.open()
            qry = QSqlQuery(self.tempDb)
            qry.exec("""CREATE TEMPORARY TABLE IF NOT EXISTS billablehorses (
                id TINYINT(5) NOT NULL,
                horse VARCHAR(45) NOT NULL,
                agrid TINYINT(5) NOT NULL,
                amountpayed DECIMAL(6,2) NOT NULL,
                dos DATE ,
                months TINYINT(2) ,
                installment DECIMAL(6,2) NOT NULL,
                totalamount DECIMAL(7,2) NOT NULL,
                billed TINYINT(1) NOT NULL DEFAULT FALSE,
                concept VARCHAR(100) NULL DEFAULT NULL,
                PRIMARY KEY (id))""")
            if qry.lastError().type() != 0:
                raise DataError("createTemporaryTable -billablehorses", qry.lastError().text())
            qry.clear()
            qry.exec("""CREATE TEMPORARY TABLE IF NOT EXISTS billed 
                (id TINYINT(5) NOT NULL, 
                horse VARCHAR(45) NOT NULL,
                description VARCHAR(100) NOT NULL, 
                amount DECIMAL(6,2) NOT NULL,
                PRIMARY KEY (id))""")
            if qry.lastError().type() != 0:
                raise DataError("createTemporaryTable -billed", qry.lastError().text())
        except DataError as err:
            print(err.source, err.message)

    def refreshTables(self):
        try:
            qryBilled = QSqlQuery(self.tempDb)
            qryCheck = QSqlQuery(self.tempDb)
            qryBilled.exec(("""SELECT id, horse, description, amount FROM billed"""))
            if qryBilled.lastError().type() != 0:
                raise DataError("refreshTables -billed", qryBilled.lastError().text())
            self.tableBilled.model().setQuery(qryBilled)
            qryCheck.exec(("""SELECT id, horse, agrid, amountpayed, dos, months, 
            installment, totalamount, concept
                FROM billablehorses 
                WHERE NOT billed
                ORDER BY agrid, horse"""))
            if qryBilled.lastError().type() != 0:
                raise DataError("refreshTables -Check", qryBilled.lastError().text())
            self.tableCheck.model().setQuery(qryCheck)
            qryAmount = QSqlQuery(self.tempDb)
            qryAmount.exec("SELECT SUM(amount) FROM billed")
            qryAmount.first()
            self.lineTotal.setText('{:.2f}'.format(round(qryAmount.value(0),2)))
            if int(self.comboType.getHiddenData(0)) !=0 or int(self.comboCurrency.getHiddenData(0)) != 0:
                self.refreshTotals(qryAmount)

        except DataError as err:
            print(err.source, err.message)

    def refreshTotals(self, qryAmount):
        try:

            if int(self.comboType.getHiddenData(0)) == 1:
                self.lineIva.setText('{:.2f}'.format(qryAmount.value(0) * .21))
                self.lineGrandTotal.setText('{:.2f}'.format(qryAmount.value(0) * 1.21))
            if int(self.comboCurrency.getHiddenData(0)) == 0:
                return
            if int(self.comboType.getHiddenData(0)) != 0:
                self.lineCurrencyTotal.setText('{:.2f}'.format(float(self.lineGrandTotal.text()) *
                                               float(self.lineExchange.text())))
            else:
                if self.lineExchange.text():
                    self.lineCurrencyTotal.setText('{:.2f}'.format(float(self.lineTotal.text()) *
                                                               float(self.lineExchange.text())))
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def includeHorses(self):
        try:
            qryFrom = self.tableCheck.model().query()
            row = self.tableCheck.currentIndex().row()
            qryFrom.seek(row)
            qryInsert = QSqlQuery(self.tempDb)

            qryInsert.prepare("""INSERT INTO billed 
            (id, horse, description, amount) 
            VALUES (?, ?, ?, ?)
            """)
            qryInsert.addBindValue(QVariant(qryFrom.value(0)))
            qryInsert.addBindValue(QVariant(qryFrom.value(1)))
            if int(self.comboInvoiceType.getHiddenData(0)) == PAYABLES_TYPE_BOARD:
                qryInsert.addBindValue(QVariant("Board from {} to {}".format(self.dateFrom.date().toString("yyyy-MM-dd"),
                                                                         self.dateTo.date().toString("yyyy-MM-dd"))))
            elif int(self.comboInvoiceType.getHiddenData(0)) == PAYABLES_TYPE_DOWNPAYMENT:
                qryInsert.addBindValue(QVariant("Downpayment"))
            elif self.payableType == PAYABLES_TYPE_SALE:
                qryInsert.addBindValue(QVariant(qryFrom.value(8)))

            qryInsert.addBindValue(QVariant(qryFrom.value(6)))
            qryInsert.exec()
            if qryInsert.lastError().type() != 0:
                raise DataError("includeHorses -Insert", qryInsert.lastError().text())
            qryUpdate = QSqlQuery(self.tempDb)
            qryUpdate.prepare("""UPDATE billablehorses
            SET billed = ? 
            WHERE id = ? """)
            qryUpdate.addBindValue(QVariant(True))
            qryUpdate.addBindValue(QVariant(qryFrom.value(0)))
            qryUpdate.exec()
            if qryUpdate.lastError().type() != 0:
                raise DataError("includeHorses -Update", qryUpdate.lastError().text())
            self.refreshTables()
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def excludeHorses(self):
        try:
            qryBilled = self.tableBilled.model().query()
            row = self.tableBilled.currentIndex().row()
            qryBilled.seek(row)
            qryDelete = QSqlQuery(self.tempDb)
            qryDelete.prepare("""DELETE FROM billed 
                WHERE id = ?""")
            qryDelete.addBindValue(QVariant(qryBilled.value(0)))
            qryDelete.exec()
            if qryDelete.lastError().type() != 0:
                raise DataError("excludeHorses -Deletete", qryDelete.lastError().text())
            qryUpdate = QSqlQuery(self.tempDb)
            qryUpdate.prepare("""UPDATE billableHorses 
                SET billed = False 
                WHERE id = ?""")
            qryUpdate.addBindValue(QVariant(qryBilled.value(0)))
            qryUpdate.exec()
            if qryUpdate.lastError().type() != 0:
                raise DataError("excludeHorses -Update", qryUpdate.lastError().text())
            self.refreshTables()
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot(int)
    def addIVA(self, num):
        try:
            if int(self.comboType.getHiddenData(0)) == 1:
                self.lblIva.show()
                self.lineIva.show()
                self.lblGrandTotal.show()
                self.lineGrandTotal.show()
                self.lblTotal.setText("Subtotal U$A")
            else:
                self.lblIva.hide()
                self.lineIva.hide()
                self.lblGrandTotal.hide()
                self.lineGrandTotal.hide()
                self.lblTotal.setText("Total U$A")
            self.refreshTables()
        except Exception as err:
            print('addIVA', err.args)

    @pyqtSlot(int)
    def setCurrency(self,num):
        if int(self.comboCurrency.getHiddenData(0)) == 0:
            self.lblCurrencyTotal.hide()
            self.lineCurrencyTotal.hide()
            self.lineExchange.setEnabled(True)
            self.lineExchange.setText("1.00")
            self.refreshTables()
        else:
            self.lblCurrencyTotal.setText("Total {}".format(self.comboCurrency.currentText()))
            self.lblCurrencyTotal.show()
            self.lineCurrencyTotal.show()
            self.lineExchange.clear()
            self.lineExchange.setEnabled(True)


    @pyqtSlot()
    def saveAndClose(self):
        try:
            cnn = pymysql.connect(**self.con_string)
            cnn.begin()
            with cnn.cursor() as cur:

                #if int(self.comboInvoiceType.getHiddenData(0))== PAYABLES_TYPE_DOWNPAYMENT or \
                #    int(self.comboInvoiceType.getHiddenData(0))== PAYABLES_TYPE_BOARD:
                sql_invoice = """INSERT INTO invoices 
                    (supplierid, number, fromdate, todate, invoicedate, amountcurrency,
                    amountu$a, currency, type, notes, ivaamount)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                paramInvoice = (self.supplierId,
                            self.lineNumber.text(),
                            self.dateFrom.date().toString("yyyy-MM-dd"),
                            self.dateTo.date().toString("yyyy-MM-dd"),
                            self.dateInvoice.date().toString("yyyy-MM-dd"),
                            self.lineCurrencyTotal.text() if self.lineCurrencyTotal.text() else None,
                            self.lineTotal.text(),
                            self.comboCurrency.getHiddenData(0),
                            self.comboInvoiceType.getHiddenData(0),
                            self.textNotes.toPlainText(),
                            self.lineIva.text() if self.lineIva.text() else None)
                cur.execute(sql_invoice, paramInvoice)
                lastId = cur.lastrowid
                sql_InvoiceLine = """INSERT INTO invoicelines 
                    (invoiceid, agreementhorseid, description, amount)
                    VALUES (%s, %s, %s, %s)"""
                sql_sale = """UPDATE payables p
                                        INNER JOIN sales s
                                        ON p.saleid = s.id
                                        SET p.billed = True 
                                        WHERE s.agreementhorseid = %s
                                        AND p.typeid = %s"""
                qry = self.tableBilled.model().query()
                qry.seek(-1)
                while qry.next():
                    paramLine = (lastId, qry.value(0), qry.value(2), qry.value(3))
                    cur.execute(sql_InvoiceLine, paramLine)
                    if self.payableType == PAYABLES_TYPE_SALE or \
                        self.payableType == PAYABLES_TYPE_HALF_BREAK or \
                        self.payableType == PAYABLES_TYPE_FULL_BREAK:
                        param_sale = [qry.value(0), self.payableType]
                        cur.execute(sql_sale, param_sale)

            cnn.commit()
        except pymysql.Error as err:
            print('saveAndClose', err.args)
            cnn.rollback
        except Exception as err:
            print('saveAndClose', err.args)
            cnn.rollback()
        finally:
            cnn.close()
        self.widgetClose()

class Payables(QDialog):

    def __init__(self, db, supplierId, payableType, mode=None, con_string=None,
                 parent=None):
        super().__init__()
        self.db = db
        if not self.db.isOpen():
            self.db.open()
        self.con_string = con_string
        self.mode = mode
        self.parent = parent
        self.payableType = payableType
        self.supplierId = supplierId
        self.tempDb = None
        self.createTemporaryTables()
        self.setUI()

    def setUI(self):
        self.setModal(True)
        self.setMinimumSize(1000, 600)
        if self.payableType == PAYABLES_TYPE_BOARD:
            self.setWindowTitle("Boarding {}".format(self.parent.supplier) )
        elif self.payableType == PAYABLES_TYPE_DOWNPAYMENT:
            self.setWindowTitle("Downpayments {}".format(self.parent.supplier))
        else:
            self.setWindowTitle("Other Charges {}".format(self.parent.supplier))
        topFrame = QFrame()
        topFrame.setMaximumWidth(1000)
        topFrame.setFrameStyle(QFrame.Panel | QFrame.Plain)
        topFrame.setLineWidth(2)

        lblSupplier = QLabel('Supplier: ')
        self.lineSupplier = QLineEdit()
        self.lineSupplier.setEnabled(False)
        self.lineSupplier.setMinimumWidth(300)
        self.lineSupplier.setText(self.parent.supplier)

        lblNumber = QLabel("Ticket #: ")
        self.lineNumber = QLineEdit()
        self.lineNumber.setMaximumWidth(100)
        self.lineNumber.setAlignment(Qt.AlignRight)
        self.lineNumber.editingFinished.connect(self.enableSave)

        self.lblTotal = QLabel('Total Amount:')
        self.lblTotal.setAlignment(Qt.AlignRight)
        self.lineTotal = QLineEdit()
        self.lineTotal.setAlignment(Qt.AlignRight)
        self.lineTotal.setMaximumWidth(150)
        self.lineTotal.setEnabled(False)
        self.lineTotal.editingFinished.connect(self.enableSave)

        lblFrom = QLabel('From: ')
        self.dateFrom = QDateEdit()
        self.dateFrom.setCalendarPopup(True)
        self.dateFrom.setDisplayFormat('yyyy-MM-dd')
        self.dateFrom.setMinimumWidth(120)

        lblTo = QLabel('To: ')
        self.dateTo = QDateEdit()
        self.dateTo.setCalendarPopup(True)
        self.dateTo.setDisplayFormat('yyyy-MM-dd')
        self.dateTo.setMinimumWidth(120)

        lblInvoice = QLabel("Payable for: ")
        self.comboInvoiceType = FocusCombo(itemList=['DownPayment', 'Board', 'Half Break', 'Final Break', 'Sale Share'])
        self.comboInvoiceType.setMinimumWidth(70)
        self.comboInvoiceType.setCurrentIndex(self.payableType)
        self.comboInvoiceType.setModelColumn(1)
        self.comboInvoiceType.setEnabled(False)

        lastDate = QDate.currentDate()
        if self.comboInvoiceType.getHiddenData(0) == PAYABLES_TYPE_BOARD:
            lastDate = self.getLastBoardDate()
            billDate = lastDate.addMonths(1).addDays(- lastDate.day() + 1)
        elif self.comboInvoiceType.getHiddenData(0) == PAYABLES_TYPE_DOWNPAYMENT:
            billDate = self.getLastAgreementDate().addDays(1)



        lblDate = QLabel('Date: ')
        self.dateInvoice = QDateEdit()
        self.dateInvoice.setCalendarPopup(True)
        self.dateInvoice.setDate(billDate)
        self.dateInvoice.setDisplayFormat('yyyy-MM-dd')
        self.dateInvoice.setMinimumWidth(120)
        self.dateInvoice.dateChanged.connect(self.enableSave)
        self.dateInvoice.dateChanged.connect(self.setPeriod)
        self.dateInvoice.dateChanged.connect(self.updateElegibleHorses)

        self.setPeriod()

        self.checkLocation = QCheckBox("Disable Location Check")
        self.checkLocation.setVisible(True) if self.payableType == PAYABLES_TYPE_BOARD else \
            self.checkLocation.setVisible(False)
        self.checkLocation.stateChanged.connect(self.getHorses)

        lblNotes = QLabel("Notes")
        self.textNotes = QTextEdit()
        self.textNotes.setMaximumHeight(100)

        colorDict = {}
        colDict = {0: ("ID", True, True, False, None),
                   1: ("Horse", False, False, False, None),
                   2: ("#", False, True, True, None),
                   3: ("Payed", True, True, False, None),
                   4: ("DOS", False, True, True, None),
                   5: ("Days", False, True, True, None),
                   6: ("Installment", False, True, 2, None),
                   7: ("Total", True, True, False, None)}
        qry, qryBilled = self.getHorses()
        self.tableCheck = TableViewAndModel(colDict=colDict, colorDict=colorDict, size=(100, 200), qry=qry)
        self.tableCheck.doubleClicked.connect(self.includeHorses)
        self.tableCheck.doubleClicked.connect(self.enableSave)

        colBilled = {0: ("agreementhorseid", True, True, False, None),
                     1: ("Horse", False, True, False, None),
                     2: ("Concept", False, False, False, None),
                     3: ("Amount", False, True, 2, None)}

        self.tableBilled = TableViewAndModel(colDict=colBilled, colorDict=colorDict, size=(100, 200), qry=qryBilled)
        self.tableBilled.doubleClicked.connect(self.excludeHorses)
        self.tableBilled.doubleClicked.connect(self.enableSave)

        pushCancel = QPushButton("Cancel")
        pushCancel.setMaximumWidth(70)
        pushCancel.clicked.connect(self.widgetClose)

        self.pushSave = QPushButton("Save")
        self.pushSave.setMaximumWidth(70)
        self.pushSave.setEnabled(False)
        self.pushSave.clicked.connect(self.saveAndClose)

        invoiceVLayout = QVBoxLayout()
        invoiceLayout_1 = QHBoxLayout()
        invoiceLayout = QHBoxLayout()

        invoiceLayout_1.addWidget(lblSupplier)
        invoiceLayout_1.addWidget(self.lineSupplier)
        invoiceLayout_1.addWidget(lblInvoice)
        invoiceLayout_1.addWidget(self.comboInvoiceType)
        invoiceLayout_1.addWidget(lblNumber)
        invoiceLayout_1.addWidget(self.lineNumber)

        invoiceLayout.addWidget(lblDate)
        invoiceLayout.addWidget(self.dateInvoice)

        invoiceLayout.addWidget(lblFrom)
        invoiceLayout.addWidget(self.dateFrom)
        invoiceLayout.addWidget(lblTo)
        invoiceLayout.addWidget(self.dateTo)

        invoiceVLayout.addLayout(invoiceLayout_1)
        invoiceVLayout.addLayout(invoiceLayout)

        topFrame.setLayout(invoiceVLayout)

        tablesLayout = QHBoxLayout()
        tablesLayout.addWidget(self.tableCheck)
        tablesLayout.addWidget(self.tableBilled)

        self.totalLayout = QGridLayout()
        self.totalLayout.addWidget(self.checkLocation,0,0)
        self.totalLayout.addWidget(self.lblTotal, 0, 1, Qt.AlignRight)
        self.totalLayout.addWidget(self.lineTotal, 0, 2, Qt.AlignRight)

        totalFrame = QFrame()
        totalFrame.setLayout(self.totalLayout)
        totalFrame.setMinimumSize(50, 50)

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(pushCancel)
        buttonLayout.addWidget(self.pushSave)

        layout = QVBoxLayout()
        layout.addWidget(topFrame)
        layout.addLayout(tablesLayout)
        layout.addWidget(totalFrame)
        layout.addWidget(lblNotes)
        layout.addWidget(self.textNotes)
        layout.addLayout(buttonLayout)

        self.setLayout(layout)

    def getLastBoardDate(self):
        try:
            qry = QSqlQuery(self.db)
            qry.prepare("""SELECT MAX(b.boardingdate), MAX(ah.dos)  FROM 
            agreementhorses ah 
            INNER JOIN agreements a 
            ON ah.agreementid = a.id
            LEFT JOIN boarding  b 
            ON a.supplierid = b.supplierid 
            WHERE a.supplierid = ?""")
            qry.addBindValue(QVariant(self.supplierId))
            qry.exec()
            if qry.lastError().type() != 0:
                raise DataError("getLastBoardDate", qry.lastError().text())
            qry.first()
            if not qry.value(0).isNull():
                return qry.value(0)
            return qry.value(1)
        except DataError as err:
            print(err.source, err.message)

    def getLastAgreementDate(self):
        try:
            qry = QSqlQuery(self.db)
            qry.prepare("""SELECT MAX(a.date) FROM 
            agreements a
            INNER JOIN agreementhorses ah
            ON a.id = ah.agreementid
            WHERE 
            ah.active 
            AND a.supplierid = ?""")
            qry.addBindValue(QVariant(self.supplierId))
            qry.exec()
            if qry.lastError().type() != 0:
                raise DataError("getLastBoardDate", qry.lastError().text())
            qry.first()
            if not qry.value(0).isNull():
                return qry.value(0)
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def updateElegibleHorses(self):
        qry = self.getHorses()[0]
        self.tableCheck.model().setQuery(qry)

    @pyqtSlot()
    def setPeriod(self):
        self.dateTo.setDate(self.dateInvoice.date().addDays(-1))
        self.dateFrom.setDate(self.dateInvoice.date().addDays(-
                self.dateInvoice.date().addDays(-28).daysInMonth()))

    @pyqtSlot()
    def getHorses(self):
        try:
            qryTruncate = QSqlQuery(self.tempDb)
            qryTruncate.exec("TRUNCATE billablehorses")
            if qryTruncate.lastError().type() != 0:
                raise DataError("getHorses -Truncate-billable", qryTruncate.lastError().text())
            qryTruncate.exec("TRUNCATE billed")
            if qryTruncate.lastError().type() != 0:
                raise DataError("getHorses -Truncate-billed", qryTruncate.lastError().text())
            qry = QSqlQuery(self.tempDb)

            if self.payableType == PAYABLES_TYPE_BOARD:
                if not self.checkLocation.isChecked():
                    qry.prepare("""INSERT INTO billablehorses 
                    (id, horse, agrid, amountpayed, dos, months, installment, totalamount)
                    SELECT DISTINCT
                    ah.id, h.name, a.id,
                    COALESCE((SELECT SUM(p.amount) 
                        FROM payables p 
                        WHERE 
                        p.agreementhorseid = ah.id
                        AND p.typeid = 1), 0) payed,
                    ah.dos,
                    TIMESTAMPDIFF(DAY, ah.dos, ?) Days, 
                    ROUND((a.totalamount - a.downpayment)/ a.installments, 2) inst,
                    a.totalamount
                    FROM horses h
                    INNER JOIN agreementhorses ah
                    ON h.id = ah.horseid
                    INNER JOIN agreements a
                    ON ah.agreementid = a.id
                    LEFT JOIN locationS l 
                    ON h.locationid = l.id
                    WHERE
                    ah.active
                    AND ah.dos IS NOT NULL
                    AND a.supplierid = ? 
                    AND a.paymentoption = 1 
                        OR (a.paymentoption = 2 AND l.contactid != 0 )
                        OR (a.paymentoption = 2 AND l.contactid = 0 
                            AND EXISTS (SELECT t.id FROM transfers t 
                                INNER JOIN transferdetail td 
                                ON t.id = td.transferid
                                WHERE td.agreementhorseid = ah.id
                                AND t.toid IN (SELECT id FROM locations WHERE contactid = 0)
                                AND t.date >= ?))
                    HAVING
                    payed BETWEEN 0 AND a.totalamount""")
                    qry.bindValue(0, QVariant(self.dateInvoice.date().toString("yyyy-MM-dd")))
                    qry.bindValue(1, QVariant(self.supplierId))
                    qry.bindValue(2, QVariant(self.dateInvoice.date().addDays(-20).toString("yyyy-MM-dd")))
                else:
                    qry.prepare("""INSERT INTO billablehorses 
                                        (id, horse, agrid, amountpayed, dos, months, installment, totalamount, concept)
                                        SELECT 
                                        ah.id, h.name, a.id,
                                        COALESCE((SELECT SUM(p.amount) 
                                        FROM payables p 
                                        WHERE 
                                        p.agreementhorseid = ah.id
                                        AND p.typeid = 1), 0) payed,
                                        ah.dos,
                                        TIMESTAMPDIFF(DAY, ah.dos, ?) Days, 
                                        ROUND((a.totalamount - a.downpayment)/ a.installments, 2) inst,
                                        a.totalamount,
                                        Null concept
                                        FROM horses h
                                        INNER JOIN agreementhorses ah
                                        ON h.id = ah.horseid
                                        INNER JOIN agreements a
                                        ON ah.agreementid = a.id
                                        LEFT JOIN locationS l 
                                        ON h.locationid = l.id
                                        WHERE
                                        ah.active
                                        AND ah.dos IS NOT NULL
                                        AND a.supplierid = ? 
                                        AND (a.paymentoption = 1 OR a.paymentoption = 2)
                                        HAVING
                                        payed BETWEEN 0 AND a.totalamount;""")
                    qry.bindValue(0, QVariant(self.dateInvoice.date().toString("yyyy-MM-dd")))
                    qry.bindValue(1, QVariant(self.supplierId))
                qry.exec()
                if qry.lastError().type() != 0:
                    raise DataError("getHorses -Board", qry.lastError().text())
            elif self.payableType == PAYABLES_TYPE_DOWNPAYMENT:
                qry.prepare("""INSERT INTO billablehorses 
                                    (id, horse, agrid, amountpayed, dos, months, installment,
                                     totalamount)
                                    SELECT 
                                    ah.id, h.name, a.id,
                                    COALESCE((SELECT SUM(amount) FROM payables  
                                        WHERE agreementhorseid = ah.id
                                        AND typeid = 0), 0) payed,
                                    ah.dos,
                                    TIMESTAMPDIFF(DAY, a.date, ?) days,
                                    ROUND(a.downpayment,2)  Inst,
                                    a.totalamount
                                    FROM horses h 
                                    INNER JOIN agreementhorses ah
                                    ON h.id = ah.horseid
                                    INNER JOIN agreements a
                                    ON ah.agreementid = a.id
                                    WHERE ah.active 
                                    AND a.supplierid = ? 
                                    AND a.downpayment > 0
                                    HAVING  payed BETWEEN 0 AND Inst -1 """)
                qry.addBindValue(QVariant(self.dateInvoice.date().toString("yyyy-MM-dd")))
                qry.addBindValue(QVariant(self.supplierId))
                qry.exec()
                if qry.lastError().type() != 0:
                    raise DataError("getHorses -Downpayment", qry.lastError().text())
            elif self.payableType == PAYABLES_TYPE_OTHER:
                qry.prepare("""INSERT INTO billablehorses 
                    (id, horse, agrid, amountpayed, dos, months, installment, 
                                totalamount)
                    SELECT 
                    ah.id, h.name, a.id, 
                    COALESCE((SELECT SUM(amount) FROM invoicelines WHERE agreementhorseid = ah.id), 0) payed,
                    ah.dos,
                    TIMESTAMPDIFF(MONTH, ah.dos, ?) Months,
                    p.amount inst,
                    a.totalamount
                    FROM horses h
                    INNER JOIN agreementhorses ah
                    ON h.id = ah.horseid
                    INNER JOIN agreements a
                        ON ah.agreementid = a.i
                    INNER JOIN payables p
                    param""")

            qryDisplay = QSqlQuery(self.tempDb)
            qryDisplay.exec("""SELECT id, horse, agrid, amountpayed, dos,
                 months, installment, totalamount
                                   FROM billablehorses 
                                   WHERE NOT billed
                                   ORDER BY agrid, horse""")
            qryBilled = QSqlQuery(self.tempDb)
            qryBilled.exec("""SELECT id, horse, description, amount FROM billed""")
            return qryDisplay, qryBilled

        except DataError as err:
            print(err.source, err.message)

    def createTemporaryTables(self):
        try:
            if self.tempDb is None:
                self.tempDb = self.db.cloneDatabase(self.db, "Temp")
            if not self.tempDb.isOpen():
                self.tempDb.open()
            qry = QSqlQuery(self.tempDb)
            qry.exec("""CREATE TEMPORARY TABLE IF NOT EXISTS billablehorses (
                id TINYINT(5) NOT NULL,
                horse VARCHAR(45) NOT NULL,
                agrid TINYINT(5) NOT NULL,
                amountpayed DECIMAL(6,2) NOT NULL,
                dos DATE ,
                months SMALLINT(5) ,
                installment DECIMAL(6,2) NOT NULL,
                totalamount DECIMAL(7,2) NOT NULL,
                billed TINYINT(1) NOT NULL DEFAULT FALSE,
                PRIMARY KEY (id))""")
            if qry.lastError().type() != 0:
                raise DataError("createTemporaryTable -billablehorses", qry.lastError().text())
            qry.clear()
            qry.exec("""CREATE TEMPORARY TABLE IF NOT EXISTS billed 
                (id TINYINT(5) NOT NULL, 
                horse VARCHAR(45) NOT NULL,
                description VARCHAR(100) NOT NULL, 
                amount DECIMAL(7,2) NOT NULL,
                PRIMARY KEY (id))""")
            if qry.lastError().type() != 0:
                raise DataError("createTemporaryTable -billed", qry.lastError().text())
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def enableSave(self):
        if not self.lineNumber.text() or \
                not self.lineTotal.text():
            return
        if self.lineTotal.isEnabled():
            if not self.lineTotal.text():
                return
        self.pushSave.setEnabled(True)

    @pyqtSlot()
    def includeHorses(self):
        try:
            qryFrom = self.tableCheck.model().query()
            row = self.tableCheck.currentIndex().row()
            qryFrom.seek(row)
            qryInsert = QSqlQuery(self.tempDb)

            qryInsert.prepare("""INSERT INTO billed 
                (id, horse, description, amount) 
                VALUES (?, ?, ?, ?)
                """)
            qryInsert.addBindValue(QVariant(qryFrom.value(0)))
            qryInsert.addBindValue(QVariant(qryFrom.value(1)))
            if int(self.comboInvoiceType.getHiddenData(0)) == PAYABLES_TYPE_BOARD:
                qryInsert.addBindValue(
                    QVariant("Board from {} to {}".format(self.dateFrom.date().toString("yyyy-MM-dd"),
                                                          self.dateTo.date().toString("yyyy-MM-dd"))))
            elif int(self.comboInvoiceType.getHiddenData(0)) == PAYABLES_TYPE_DOWNPAYMENT:
                qryInsert.addBindValue(QVariant("Downpayment"))
            qryInsert.addBindValue(QVariant(qryFrom.value(6)))
            qryInsert.exec()
            if qryInsert.lastError().type() != 0:
                raise DataError("includeHorses -Insert", qryInsert.lastError().text())
            qryUpdate = QSqlQuery(self.tempDb)
            qryUpdate.prepare("""UPDATE billablehorses
                SET billed = ? 
                WHERE id = ? """)
            qryUpdate.addBindValue(QVariant(True))
            qryUpdate.addBindValue(QVariant(qryFrom.value(0)))
            qryUpdate.exec()
            if qryUpdate.lastError().type() != 0:
                raise DataError("includeHorses -Update", qryUpdate.lastError().text())
            self.refreshTables()
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def excludeHorses(self):
        try:
            qryBilled = self.tableBilled.model().query()
            row = self.tableBilled.currentIndex().row()
            qryBilled.seek(row)
            qryDelete = QSqlQuery(self.tempDb)
            qryDelete.prepare("""DELETE FROM billed 
                    WHERE id = ?""")
            qryDelete.addBindValue(QVariant(qryBilled.value(0)))
            qryDelete.exec()
            if qryDelete.lastError().type() != 0:
                raise DataError("excludeHorses -Deletete", qryDelete.lastError().text())
            qryUpdate = QSqlQuery(self.tempDb)
            qryUpdate.prepare("""UPDATE billableHorses 
                    SET billed = False 
                    WHERE id = ?""")
            qryUpdate.addBindValue(QVariant(qryBilled.value(0)))
            qryUpdate.exec()
            if qryUpdate.lastError().type() != 0:
                raise DataError("excludeHorses -Update", qryUpdate.lastError().text())
            self.refreshTables()
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def widgetClose(self):
        if self.tempDb.isOpen():
            self.tempDb.close()
        self.done(QDialog.Rejected)

    @pyqtSlot()
    def refreshTables(self):
        try:
            qryBilled = QSqlQuery(self.tempDb)
            qryCheck = QSqlQuery(self.tempDb)
            qryBilled.exec(("""SELECT id, horse, description, amount FROM billed"""))
            if qryBilled.lastError().type() != 0:
                raise DataError("refreshTables -billed", qryBilled.lastError().text())
            self.tableBilled.model().setQuery(qryBilled)
            qryCheck.exec(("""SELECT id, horse, agrid, amountpayed, dos, months, 
            installment, totalamount
                FROM billablehorses 
                WHERE NOT billed
                ORDER BY agrid, horse"""))
            if qryBilled.lastError().type() != 0:
                raise DataError("refreshTables -Check", qryBilled.lastError().text())
            self.tableCheck.model().setQuery(qryCheck)
            qryAmount = QSqlQuery(self.tempDb)
            qryAmount.exec("SELECT SUM(amount) FROM billed")
            qryAmount.first()
            self.lineTotal.setText('{:.2f}'.format(round(qryAmount.value(0),2)))

        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def saveAndClose(self):
        try:
            cnn = pymysql.connect(**self.con_string)
            cnn.begin()
            qrySave = self.tableBilled.model().query()
            qrySave.seek(-1)
            with cnn.cursor() as cur:
                if self.payableType == PAYABLES_TYPE_BOARD:
                    sql_board = """INSERT INTO boarding 
                        (boardingdate, fromdate, todate, totalamount, supplierid) 
                        VALUES (%s, %s, %s,%s, %s )"""
                    paramBoard = (self.dateInvoice.date().toString("yyyy-MM-dd"),
                                  self.dateFrom.date().toString("yyyy-MM-dd"),
                                  self.dateTo.date().toString("yyyy-MM-dd"),
                                  self.lineTotal.text(),
                                  self.supplierId)
                    cur.execute(sql_board, paramBoard)
                    lastBoard = cur.lastrowid
                    sql_payables = """ INSERT INTO payables 
                    (agreementhorseid, concept, amount, ticketid, typeid)
                    VALUES (%s, %s, %s, %s, %s)"""
                    while qrySave.next():
                        paramPayables = (qrySave.value(0),
                                         qrySave.value(2),
                                         qrySave.value(3),
                                         lastBoard,
                                         self.payableType)
                        cur.execute(sql_payables, paramPayables)
                elif self.payableType == PAYABLES_TYPE_DOWNPAYMENT:
                    sql_downpayment = """INSERT INTO downpayments 
                    (date, totalamount, supplierid) 
                    VALUES (%s, %s, %s)"""
                    paramDownpayment = (self.dateInvoice.date().toString("yyyy-MM-dd"),
                                        self.lineTotal.text(),
                                        self.supplierId)
                    cur.execute(sql_downpayment, paramDownpayment)
                    lastDownpayment = cur.lastrowid
                    sql_payables =""" INSERT INTO payables 
                    (agreementhorseid, concept, amount, ticketid, typeid)
                    VALUES (%s, %s, %s, %s, %s)"""
                    while qrySave.next():
                        paramPayables = (qrySave.value(0),
                                         qrySave.value(2),
                                         qrySave.value(3),
                                         lastDownpayment,
                                         self.payableType)
                        cur.execute(sql_payables, paramPayables)
            cnn.commit()
        except DataError as err:
            print(err.source, err.message)
            cnn.rollback()
        except pymysql.Error as err:
            print("saveAndClose", err.args)
            cnn.rollback()
        except Exception as err:
            print("saveAndClose", err.args)
            cnn.rollback()
        finally:
            cnn.close()
        self.widgetClose()

