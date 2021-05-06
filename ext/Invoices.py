
from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import (QDialog, QMessageBox, QFrame,QVBoxLayout, QHBoxLayout, QAbstractItemView,
                             QGridLayout, QLabel, QPushButton, QLineEdit,QTextEdit, QDateEdit, QToolButton, QCheckBox)
from PyQt5.QtGui import QDoubleValidator, QIcon, QColor
from PyQt5.QtCore import Qt, QDate, pyqtSlot, QModelIndex
from PyQt5.QtSql import QSqlQueryModel, QSqlQuery
from ext.APM import (FocusCombo, FocusSpin, TableViewAndModel,DataError, NullDateEdit,
    PAYABLES_TYPE_BOARD, PAYABLES_TYPE_DOWNPAYMENT, PAYABLES_TYPE_ALL,PAYABLES_TYPE_SALE,
    PAYABLES_TYPE_OTHER, PAYABLES_TYPE_FULL_BREAK,PAYABLES_TYPE_HALF_BREAK,
    ACCOUNT_PAYMENT, ACCOUNT_INVOICE,
    OPEN_NEW, OPEN_EDIT, OPEN_DELETE)



class Payment(QDialog):
    def __init__(self, db, supplierId, mode, paymentId=None, con_string=None, parent=None, record=None, qry=None):
        super().__init__()
        self.db = db
        if not self.db.isOpen():
            self.db.open()
        if not self.db.contains("Temp"):
            self.db = self.db.cloneDatabase(self.db, "Temp")
            self.db.open()
        else:
            self.db = self.db.database("Temp")
        self.mode = mode
        self.record = record
        self.qry = qry
        self.paymentId = paymentId
        self.supplierId = supplierId
        self.parent = parent
        self.setTemporaryTables()
        self.selectedAmount = 0.00
        self.amountToPay = 0.00
        self.setUI()

    def setUI(self):
        self.setModal(True)
        self.setWindowTitle("Payment") if self.mode == OPEN_NEW else  self.setWindowTitle("Edit Payment")
        self.setMinimumSize(1000, 700)
        self.setMaximumSize(1000, 700)

        topFrame = QFrame()
        topFrame.setMaximumWidth(3000)
        topFrame.setMaximumHeight(300)
        topFrame.setFrameStyle(QFrame.Panel | QFrame.Plain)
        topFrame.setLineWidth(2)

        self.setWindowTitle("Payment to {}".format(self.parent.supplier))

        lblNumber = QLabel("Number: ")
        self.lineNumber = QLineEdit()
        self.lineNumber.setMaximumWidth(100)
        self.lineNumber.setAlignment(Qt.AlignRight)
        self.lineNumber.editingFinished.connect(self.enableSave)

        valExchange = QDoubleValidator(0.00, 1.00, 2)
        valAmount = QDoubleValidator(0.00, 999999.99,2)

        lblTransaction = QLabel("Transaction No.:")
        self.lineTransaction = QLineEdit()
        self.lineTransaction.setAlignment(Qt.AlignRight)
        self.lineTransaction.setMaximumWidth(150)
        self.lineTransaction.editingFinished.connect(self.enableSave)
        self.lineTransaction.setEnabled(False)

        lblAmountToPay = QLabel('Amount to pay')
        self.lineAmountToPay = QLineEdit()
        self.lineAmountToPay.setAlignment(Qt.AlignRight)
        self.lineAmountToPay.setMaximumWidth(150)
        self.lineAmountToPay.setValidator(valAmount)
        self.lineAmountToPay.textChanged.connect(self.enableSave)

        self.lblPayInPesos = QLabel("Amount in AR$:")
        self.lblPayInPesos.hide()
        self.linePayInPesos = QLineEdit()
        self.linePayInPesos.setMaximumWidth(150)
        self.linePayInPesos.setAlignment(Qt.AlignRight)
        self.linePayInPesos.setValidator(valAmount)
        self.linePayInPesos.setEnabled(False)
        self.linePayInPesos.hide()

        self.checkLocal = QCheckBox("Pay in local Currency", self)
        self.checkLocal.stateChanged.connect(self.enableRate)
        self.checkLocal.hide()

        self.lblExchange = QLabel("Exchange Rate")
        self.lblExchange.hide()
        self.lineExchange = QLineEdit()
        self.lineExchange.setMaximumWidth(100)
        self.lineExchange.setAlignment(Qt.AlignRight)
        self.lineExchange.setValidator(valAmount)
        self.lineExchange.setText("1.00")
        self.lineExchange.setEnabled(False)
        self.lineExchange.hide()
        self.lineExchange.editingFinished.connect(self.setLocalPayment)

        self.lblCurrency = QLabel("Local Currency")
        self.lblCurrency.setStyleSheet("QLabel {background-color: red; color: white;}")
        self.lblCurrency.hide()

        lblPaymentDate = QLabel('Payment Date: ')
        self.paymentDate = QDateEdit()
        self.paymentDate.setCalendarPopup(True)
        self.paymentDate.setDate(QDate.currentDate())
        self.paymentDate.setDisplayFormat('MM-dd-yyyy')
        self.paymentDate.setMinimumWidth(120)
        self.paymentDate.dateChanged.connect(self.setInvoices)
        self.paymentDate.dateChanged.connect(self.enableSave)

        lblCurrency = QLabel("Currency")
        self.comboCurrency = FocusCombo(itemList=['USA Dollar', 'Argentine Peso'])
        self.comboCurrency.setMinimumWidth(70)
        currency = self.getCurrency()
        self.comboCurrency.setCurrentIndex(currency) if currency in [0, 1] else self.comboCurrency.setCurrentIndex(0)
        #self.comboCurrency.setEnabled(False) if currency in [0, 1] else self.comboCurrency.setEnabled(True)
        self.comboCurrency.setModelColumn(1)
        self.getNumber()
        self.comboCurrency.activated.connect(self.getNumber)
        self.comboCurrency.activated.connect(self.setInvoices)
        self.comboCurrency.activated.connect(self.setCurrency)
        self.comboCurrency.currentIndexChanged.connect(self.setCurrency)

        self.setCurrency()

        lblPaymentType = QLabel("Payment Method")
        self.comboPaymentType = FocusCombo(itemList=['Cash', 'Check', 'Transfer'])
        self.comboPaymentType.setMinimumWidth(110)
        self.comboPaymentType.setCurrentIndex(-1)
        self.comboPaymentType.setModelColumn(1)
        self.comboPaymentType.activated.connect(self.enableBanks)
        self.comboPaymentType.activated.connect(self.enableSave)

        lblBank = QLabel("Bank")
        self.comboBank = FocusCombo(itemList=['Galicia', 'Nacion', 'Provincia', 'Santander',
                                              'Columbia', 'Macro', 'Frances'])
        self.comboBank.setMinimumWidth(110)
        self.comboBank.setCurrentIndex(-1)
        self.comboBank.setModelColumn(1)
        self.comboBank.activated.connect(self.enableSave)
        self.comboBank.activated.connect(self.setTransactionNumber)

        self.lblTotalDue = QLabel("Total Amount Due")

        self.lblAmountToPay = QLabel("Amount Selected to Pay")

        pushCancel = QPushButton("Exit")
        pushCancel.setMaximumWidth(70)
        pushCancel.clicked.connect(self.widgetClose)

        self.pushSave = QPushButton("Save")
        self.pushSave.setMaximumWidth(70)
        self.pushSave.setEnabled(False)
        self.pushSave.setObjectName("save")
        self.pushSave.clicked.connect(self.saveAndClose)

        self.pushReset = QPushButton()
        self.pushReset.setIcon(QIcon(":Icons8/Edit/reset.png"))
        self.pushReset.setMaximumWidth(50)
        self.pushReset.setEnabled(False)
        self.pushReset.clicked.connect(self.resetWidget)

        self.toolRight = QToolButton()
        self.toolRight.setIcon(QIcon(":Icons8/arrows/right-arrow.png"))
        self.toolRight.setMinimumSize(100, 30)
        self.toolRight.clicked.connect(self.includePayment)
        self.toolRight.setToolTip("Load selected Invoice")
        self.toolRight.setEnabled(False)

        self.toolAllRight = QToolButton()
        self.toolAllRight.setIcon(QIcon(":Icons8/arrows/double-right.png"))
        self.toolAllRight.setMinimumSize(100, 30)
        self.toolAllRight.clicked.connect(self.includeAllPayments)
        self.toolAllRight.setToolTip("Load All Invoices")
        self.toolAllRight.setEnabled(False)

        self.toolLeft = QToolButton()
        self.toolLeft.setIcon(QIcon(":Icons8/arrows/left-arrow.png"))
        self.toolLeft.setMinimumSize(100, 30)
        self.toolLeft.clicked.connect(self.excludePayment)
        self.toolLeft.setEnabled(False)

        self.toolAllLeft = QToolButton()
        self.toolAllLeft.setIcon(QIcon(":Icons8/arrows/double-left.png"))
        self.toolAllLeft.setMinimumSize(100, 30)
        self.toolAllLeft.clicked.connect(self.excludeAllPayments)
        self.toolAllLeft.setEnabled(False)

        self.toolApply = QToolButton()
        self.toolApply.setText("Apply")
        self.toolApply.setMinimumSize(50, 30)
        self.toolApply.clicked.connect(self.applyPayment)

        self.toolPay = QToolButton()
        self.toolPay.setText("Pay All")
        self.toolPay.setMinimumSize(50, 30)
        self.toolPay.clicked.connect(self.payAllSelected)

        #lblNotes = QLabel("Notes")
        self.textNotes = QTextEdit()
        self.textNotes.setMaximumWidth(412)
        self.textNotes.setMaximumHeight(150)

        lblUnpaid = QLabel("Invoices Due")
        lblSelected = QLabel("Invoices Selected for Payment")
        self.setInvoices()
        qryActive, qryPaid = self.getQueries()
        colorDict = {'column': (10),
                     0: (QColor('white'), QColor('blue')),
                     1: (QColor('red'), QColor('yellow'))}
        colDict = {0: ("InvoiceID", True, True, False, None),
                   1: ("Date", False, True, False, None),
                   2: ("Number", False, False, False, None),
                   3: ("Provider",True, False,False, None),
                   4: ("Currency", False, True, True, None),
                   5: ("Amount", False, True, 2, None),
                   6: ("Currencyid", True, False, False, None),
                   7: ("Checked", True, True, True, None),
                   8: ("Paymentid", True, True, False, None)}

        self.tableCheck = TableViewAndModel(colDict=colDict, colorDict=colorDict, size=(100, 200), qry=qryActive)
        self.tableCheck.setObjectName("tableCheck")
        self.tableCheck.setMouseTracking(True)
        self.tableCheck.setMinimumWidth(400)
        self.tableCheck.entered.connect(self.setArrows)
        self.tableCheck.viewportEntered.connect(self.setArrows)
        self.tableCheck.doubleClicked.connect(self.includePayment)
        self.tableCheck.doubleClicked.connect(self.enableSave)
        self.tableCheck.hideColumn(6)

        self.tableBilled = TableViewAndModel(colDict=colDict, colorDict=colorDict, size=(100, 200), qry=qryPaid)
        self.tableBilled.setObjectName("tableBilled")
        self.tableBilled.setMouseTracking(True)
        self.tableBilled.entered.connect(self.setArrows)
        self.tableBilled.viewportEntered.connect(self.setArrows)
        self.tableBilled.doubleClicked.connect(self.excludePayment)
        self.tableBilled.doubleClicked.connect(self.enableSave)
        self.tableBilled.setMinimumWidth(400)

        self.refreshTables()

        if self.mode == OPEN_EDIT:
            colorInvDict = {'column': (9),
                            0: (QColor('white'), QColor('black')),
                            1: (QColor('black'), QColor('white'))}
            colInvDict = {0: ("PaymentId", True, True, False, None),
                          1: ("Date", False, True, False, None),
                          2: ("Bank", False, False, False, None),
                          3: ("Type", False, True, False, None),
                          4: ("Number", False, True, False, None),
                          5: ("Currency", False, True, True, None),
                          6: ("PaidAmount", False, True, 2, None),
                          7: ("LocalAmount", True, True, 2, None),
                          8: ("paytype", True, True, False, None),
                          9: ("paycurrency", True, True, False, None),
                          10: ("paybank", True, False, False, None),
                          11: ("TransNb", True, False, False, None),
                          12: ("Notes", True, False, False, None)}
            qryPay = self.getPayments()
            self.tablePayments = TableViewAndModel(colInvDict, colorInvDict, (100, 100), qryPay)
            self.tablePayments.doubleClicked.connect(self.loadPayment)
            self.tablePayments.currentMove.connect(self.cursorMove)

            self.pushDelete = QPushButton("Delete")
            self.pushDelete.setMaximumWidth(70)
            self.pushDelete.setEnabled(False)
            self.pushDelete.clicked.connect(self.deletePayment)

            self.toolClear = QToolButton()
            self.toolClear.setText("Clear Paid")
            self.toolClear.setIcon(QIcon(":/Icons8/Edit/eraser.png"))
            self.toolClear.setMinimumSize(100, 30)
            self.toolClear.setEnabled(False)
            self.toolClear.clicked.connect(self.clearPayment)

        topLayout = QGridLayout()
        topLayout.addWidget(lblPaymentDate,0,0,Qt.AlignLeft)
        topLayout.addWidget(self.paymentDate,0,1,Qt.AlignLeft)
        topLayout.addWidget(lblPaymentType,0,2,Qt.AlignLeft)
        topLayout.addWidget(self.comboPaymentType,0,3,Qt.AlignLeft)

        topLayout.addWidget(lblNumber,0,4,Qt.AlignLeft)
        topLayout.addWidget(self.lineNumber,0,5,Qt.AlignRight)
        topLayout.addWidget(lblCurrency,1,0,Qt.AlignLeft)
        topLayout.addWidget(self.comboCurrency,1,1,Qt.AlignLeft)
        topLayout.addWidget(lblBank, 1, 2, Qt.AlignLeft)
        topLayout.addWidget(self.comboBank, 1, 3, Qt.AlignLeft)
        topLayout.addWidget(lblTransaction,1,4,Qt.AlignLeft)
        topLayout.addWidget(self.lineTransaction,1,5,Qt.AlignRight)
        topFrame.setLayout(topLayout)

        toolsFrame = QFrame()
        toolsFrame.setMaximumWidth(150)
        toolsFrame.setMaximumHeight(150)

        toolsLayout = QVBoxLayout()
        toolsLayout.addWidget(self.toolRight)
        toolsLayout.addWidget(self.toolAllRight)
        toolsLayout.addWidget(self.toolAllLeft)
        toolsLayout.addWidget(self.toolLeft)

        if self.mode == OPEN_EDIT:
            toolsLayout.addSpacing(20)
            toolsLayout.addWidget(self.toolClear)
        toolsFrame.setLayout(toolsLayout)

        centerLayout = QGridLayout()
        centerLayout.addWidget(lblUnpaid,0,0)
        centerLayout.addWidget(lblSelected,0,2)
        centerLayout.addWidget(toolsFrame,1,1)
        centerLayout.addWidget(self.tableCheck,1,0)
        centerLayout.addWidget(self.tableBilled,1,2)
        centerLayout.addWidget(self.lblTotalDue,2,0,Qt.AlignLeft)
        centerLayout.addWidget(self.lblAmountToPay,2,2,Qt.AlignLeft)
        #centerLayout.addWidget(self.lblCurrency, 3, 0,Qt.AlignLeft)
        #centerLayout.addWidget(payFrame,3,2,Qt.AlignLeft)

        payLayout = QGridLayout()
        payLayout.addWidget(lblAmountToPay, 0, 0, Qt.AlignLeft)
        payLayout.addWidget(self.lineAmountToPay, 0, 4, Qt.AlignRight)
        payLayout.addWidget(self.checkLocal,1,0)
        payLayout.addWidget(self.lblExchange,2,0, Qt.AlignLeft)
        payLayout.addWidget(self.lineExchange,2,1, Qt.AlignRight)
        payLayout.addWidget(self.lblPayInPesos,3,0,Qt.AlignLeft)
        payLayout.addWidget(self.linePayInPesos,3,4,Qt.AlignRight)

        payFrame = QFrame()
        payFrame.setLayout(payLayout)
        payFrame.setFrameStyle(QFrame.Panel | QFrame.Plain)
        payFrame.setMaximumWidth(self.tableBilled.width())

        paymentLayout = QHBoxLayout()
        if self.mode == OPEN_EDIT:
            paymentLayout.addWidget(self.tablePayments)
        else:
            paymentLayout.addWidget(self.textNotes)
        paymentLayout.addWidget(payFrame)

        buttonsLayout = QHBoxLayout()
        buttonsLayout.addWidget(self.pushReset)
        if self.mode == OPEN_EDIT:
            buttonsLayout.addWidget(self.pushDelete)
        buttonsLayout.addWidget(pushCancel)
        buttonsLayout.addWidget(self.pushSave)

        layout = QVBoxLayout()
        layout.addWidget(topFrame)
        layout.addLayout(centerLayout)
        layout.addLayout(paymentLayout)
        if self.mode == OPEN_EDIT:
            layout.addWidget(self.textNotes,0, Qt.AlignCenter)
        layout.addLayout(buttonsLayout)

        self.setLayout(layout)
        if self.mode == OPEN_EDIT:
            self.textNotes.setMinimumWidth(self.tablePayments.width())

    @pyqtSlot()
    def setCurrency(self):
        action = not self.comboCurrency.currentIndex()
        self.lblPayInPesos.setVisible(action)
        self.linePayInPesos.setVisible(action)
        self.checkLocal.setVisible(action)
        self.lblExchange.setVisible(action)
        self.lineExchange.setVisible(action)

    @pyqtSlot()
    def getNumber(self):
        qryNumber = QSqlQuery(self.db)
        qryNumber.exec("CALL payment_getnumber({})".format(self.comboCurrency.currentIndex()))
        if qryNumber.first():
            self.lineNumber.setText(qryNumber.value(0))

    def getCurrency(self):
        payDate = self.paymentDate.date().toString("yyyy-MM-dd")
        qry = QSqlQuery(self.db)
        qry.exec("CALL payment_getcurrency({}, '{}', {})".format(self.supplierId, payDate, self.mode))
        if qry.lastError().type() != 0:
            raise DataError("Invoice: getCurrency", qry.lastError().text())
        if qry.first():
            if qry.value(0) and qry.value(1):
                pop = QMessageBox()
                pop.setWindowTitle("Currency")
                pop.setWindowIcon(QIcon(":Icons8/Accounts/currency.png"))
                pop.setText('There are payables on both currencies!')
                pop.setIcon(QMessageBox.Question)
                pop.addButton("U$A", QMessageBox.YesRole)
                pop.addButton("AR$", QMessageBox.NoRole)
                pop.setModal(True)
                pop.show()
                res = pop.exec()
                self.comboCurrency.setEnabled(True)
                return res
            elif qry.value(0):
                self.parent.comboCurrency.setCurrentIndex(0)
                return 0
            elif qry.value(1):
                self.parent.comboCurrency.setCurrentIndex(1)
                return 1
        QMessageBox.information(self,"Payments", "There are not invoices due before {}".format(payDate), QMessageBox.Ok)
        raise DataError("Payment: getCurrency", "There are not invoices due before {}".format(payDate))

    @pyqtSlot()
    def clearPayment(self):
        try:
            row = self.tableBilled.currentIndex().row()
            qryLook = self.tableBilled.model().query()
            if not qryLook.seek(row):
                return
            qry = QSqlQuery(self.db)
            qry.exec("CALL payment_clearpayment({})".format(qryLook.value(0)))
            if qry.lastError().type() != 0:
                raise DataError("Payment:clearPayment", qry.lastError().text())
            if qry.first():
                raise DataError("Payment: ClearPayment", qry.value(0) + qry.value(1))
            self.refreshTables()
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print("Payment: clearPayment", err.args)

    def getPayments(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL payment_loadpayments({})".format(self.supplierId))
            if qry.lastError().type() != 0:
                raise DataError("Payment: getPayments", qry.lastError().text())
            return qry
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print("Payment: getPayments", type(err), err.args)

    @pyqtSlot()
    def setLocalPayment(self):
        if self.lineAmountToPay.text() and self.checkLocal.isChecked():
            self.linePayInPesos.setText("{:.2f}".format(float(self.lineAmountToPay.text()) * float(self.lineExchange.text())))

    def setTemporaryTables(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL payment_initializeinvoices()")
            if qry.lastError().type() != 0:
                raise DataError("Payment: setTemporaryTables", qry.lastError().text())
            if qry.first():
                raise DataError("Payment: setTemporaryTables", qry.value(0) +' ' + qry.value(1))
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def setArrows(self):
        if self.mode == OPEN_EDIT and self.tableBilled.model().query().size() < 1:
            return
        action = True if self.sender().objectName() == "tableCheck" else False
        if self.sender().model().query().size() > 0:
            self.toolRight.setEnabled(action)
            self.toolAllRight.setEnabled(action)
            self.toolLeft.setEnabled(not action)
            self.toolAllLeft.setEnabled(not action)
            if self.tableBilled.currentIndex().row() != -1 and self.mode == OPEN_EDIT:
                self.toolClear.setEnabled(not action)

    @pyqtSlot(int)
    def setLocalOption(self, option):
        pass
        #if option == 0:
        #    self.lineExchange.setEnabled(False)
        #    self.lblAmount.setText("Amount (u$a)")
        #    self.checkLocal.setEnabled(True)
        #else:
        #    self.lblAmount.setText("Amount ($)")

    def setInvoices(self):
        try:
            qryLoad = QSqlQuery(self.db)
            qryLoad.exec("CALL payment_loadinvoicestopay({}, {}, '{}')".format(
                self.supplierId, self.comboCurrency.currentIndex(),  self.paymentDate.date().toString("yyyy-MM-dd")))
            if qryLoad.lastError().type() != 0:
                raise DataError('Payment: setInvoices', qryLoad.lastError().text())
            if qryLoad.first():
                raise DataError("Payment: setInvoices", qryLoad.value(0), qryLoad.value(1))
            if self.isVisible():
                self.refreshTables()
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def applyPayment(self):
        try:
            if self.tableBilled.model().query().size() < 1: # or not self.lineAmount.text():
                return
            qry = QSqlQuery(self.db)
            qry.exec("CALL payment_applypayment('{}')".format(self.lineAmountToPay.text()))
            if qry.lastError().type() != 0:
                raise DataError("applyPayment", qry.lastError().text())
            if qry.first():
                if qry.value(0) > 0:
                    self.lineAmountToPay.setText("{:.2f}".format(float(self.lineAmountToPay.text()) - qry.value(0)))
            self.refreshTables()
            self.setLocalPayment()
            self.enableSave()
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print("Include Payment", type(err), err.args)

    @pyqtSlot()
    def payAllSelected(self):
        try:
            self.lineAmountToPay.setText(str(self.selectedAmount))
            qry = QSqlQuery(self.db)
            qry.exec("CALL payment_payallselected()")
            if qry.lastError().type() != 0:
                raise DataError("applyPayment", qry.lastError().text())
            if qry.first():
                if qry.value(0) > 0:
                    raise DataError("applyPayment", "Error {} {}".format(qry.value(0), qry.value(1)))
            self.refreshTables()
            self.setLocalPayment()
            self.enableSave()
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print("payAllSelected", type(err), err.args)

    def refreshTables(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL payment_updateamounts()")
            if qry.lastError().type() != 0:
                raise DataError("refreshTables", qry.lastError().text())
            if qry.first():
                symbol = 'U$A' if self.comboCurrency.getHiddenData(0) == 0 else 'AR$'
                self.lblTotalDue.setText("Total Amount Due: {} {:,.2f}".format(symbol, qry.value(0)))
                self.lblAmountToPay.setText("Selected for Payment: {} {:,.2f}".format(symbol, qry.value(1)))
                self.selectedAmount = qry.value(1)
                self.lineAmountToPay.setText(str(qry.value(1)))
                self.amountToPay = qry.value(1)
                if self.checkLocal.isChecked():
                    self.setLocalPayment()
            qryFrom, qryTo = self.getQueries()
            self.tableCheck.model().setQuery(qryFrom)
            self.tableBilled.model().setQuery(qryTo)
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print('refreshTables', type(err), err.args)

    def getQueries(self):
        try:
            qryFrom = QSqlQuery(self.db)
            qryFrom.exec("CALL payment_refreshinvoicefrom()")
            if qryFrom.lastError().type() != 0:
                raise DataError("Payment: getQueries -getinvoicefrom", qryFrom.lastError().text())
            qryTo = QSqlQuery(self.db)
            qryTo.exec("CALL payment_refreshinvoiceto()")
            if qryTo.lastError().type() != 0:
                raise DataError("Payment: getQueries -getinvoiceto", qryTo.lastError().text())
            return qryFrom, qryTo
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot(int)
    def enableBanks(self, option):
        if option == 0:
            self.comboBank.setCurrentIndex(-1)
            self.comboBank.setEnabled(False)
            self.lineTransaction.setEnabled(False)
        else:
            self.comboBank.setEnabled(True)
            self.lineTransaction.setEnabled(True)

    @pyqtSlot()
    def setTransactionNumber(self):
        if self.comboBank.currentIndex() >= 0:
            action = True
            self.lineTransaction.setFocus()
            self.lineTransaction.setText("{}-".format(self.comboBank.currentText()[:2].upper()))
        else:
            action = False
            self.lineTransaction.clear()
        self.lineTransaction.setEnabled(action)

    @pyqtSlot(int)
    def enableRate(self, state):
        action = True if state == 2 else False
        self.lineExchange.setEnabled(action)
        self.lineExchange.selectAll()
        self.lineExchange.setFocus()
        self.linePayInPesos.setEnabled(action)
        self.setLocalPayment()
        if not action:
            self.linePayInPesos.clear()
            self.lineExchange.setText('1.00')

    @pyqtSlot(QModelIndex)
    def loadPayment(self, idx):
        try:
            qry = self.tablePayments.model().query()
            row = idx.row()
            if qry.seek(row):
                self.paymentDate.setDate(qry.value(1))
                self.lineNumber.setText(qry.value(4))
                self.lineAmountToPay.setText(str(qry.value(6)))
                self.comboBank.setCurrentIndex(qry.value(10))
                self.comboPaymentType.setCurrentIndex(qry.value(8))
                self.comboCurrency.setCurrentIndex(qry.value(9))
                self.lineTransaction.setText(qry.value(11))
                self.textNotes.setText(qry.value(12))
                self.checkLocal.setChecked(True) if self.comboCurrency.currentIndex() == 0 and \
                    qry.value(7) > 0 else self.checkLocal.setChecked(False)
                self.lineExchange.setText('1.0') if self.comboCurrency.currentIndex() == 1 or \
                    qry.value(7) == 0 else  self.lineExchange.setText(str(qry.value(7)/qry.value(6)))
                self.record = qry.record()
                self.loadEditableInvoices(qry.value(0))
                self.pushReset.setEnabled(True)
                self.pushDelete.setEnabled(True)
        except DataError as err:
            print(err.source, err.message)
        except ZeroDivisionError:
            pass
        except Exception as err:
            print("Payment: loadPayment", err.args)

    @pyqtSlot()
    def loadEditableInvoices(self, paymentid):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL payment_loadeditableinvoices({})".format(paymentid))
            if qry.lastError().type() != 0:
                raise DataError("Payment: loadeditableinvoices)", qry.lastError().text())
            if qry.first():
                raise DataError("Payment loadEditableInvoices", qry.value(0))
            self.refreshTables()
        except DataError as err:
            print(err.source, err.message)
        except ZeroDivisionError:
            pass
        except Exception as err:
            print("loadPayment", err.args)

    @pyqtSlot()
    def resetWidget(self):
        try:
            self.lineNumber.clear()
            self.lineAmountToPay.clear()
            self.comboBank.setCurrentIndex(-1)
            self.comboPaymentType.setCurrentIndex(-1)
            #self.comboCurrency.setCurrentIndex(-1)
            self.textNotes.clear()
            self.checkLocal.setChecked(False)
            self.lineExchange.setText('1.0')
            if self.mode == OPEN_NEW:
                self.setInvoices()
                self.refreshTables()
            else:
                qry = self.tablePayments.model().query()
                self.loadPayment(self.tablePayments.currentIndex())
            #qry = QSqlQuery(self.db)
            #qry.exec("Call payment_clearpayments()")
            #if qry.lastError().type() != 0:
            #    raise DataError("Payment: resetWidget", qry.lastError().text())
            #if qry.first():
            #    raise DataError("Payment: resetWidget", qry.value(0) + ' ' + qry.value(1))
            self.pushReset.setEnabled(False)
            if self.mode ==OPEN_EDIT:
                self.pushDelete.setEnabled(False)
            #self.refreshTables()
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot(int)
    def cursorMove(self, row):
        self.loadPayment(row)

    @pyqtSlot()
    def enableSave(self):
        try:
            if self.mode == OPEN_EDIT:
                self.pushSave.setEnabled(True)
                self.pushReset.setEnabled(True)
                return
            if float(self.lineAmountToPay.text()) > 0 and \
                (self.comboPaymentType.currentIndex() == 0 or \
                (self.comboPaymentType.currentIndex() > 0 and \
                self.comboBank.currentIndex() != -1 and self.lineTransaction.text())):
                self.pushSave.setEnabled(True)
                self.pushReset.setEnabled(True)
                return
            self.pushSave.setEnabled(False)
            self.pushReset.setEnabled(True)
        except ValueError:
            return

    @pyqtSlot()
    def includePayment(self):
        #if self.mode == OPEN_EDIT and self.tableBilled.model().query().size() < 1:
        #    return
        try:
            row = self.tableCheck.currentIndex().row()
            qryLook = self.tableCheck.model().query()
            if not qryLook.seek(row):
                return
            qry = QSqlQuery(self.db)
            qry.exec("CALL payment_includepayment({})".format(qryLook.value(0)))
            if qry.lastError().type() != 0:
                raise DataError("Payment: includePayment", qry.lastError().text())
            if qry.first():
                raise DataError("includePayment", "Error {} {}".format(qry.value(0), qry.value(1)))
            self.refreshTables()
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print("Include Payment", type(err), err.args)

    @pyqtSlot()
    def includeAllPayments(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL payment_includeallpayments()")
            if qry.lastError().type() != 0:
                    raise DataError("Payment: includeAllPayments", qry.lastError().text())
            if qry.first():
                print(qry.value(0))
                raise DataError("Payment: includeAllPayments", "Error {} {}".format(qry.value(0), qry.value(1)))
            self.refreshTables()
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print("Payment: includeAllPayments", type(err), err.args)

    @pyqtSlot()
    def excludePayment(self):
        try:
            qryLook = self.tableBilled.model().query()
            row = self.tableBilled.currentIndex().row()
            if not qryLook.seek(row):
                return
            qry = QSqlQuery(self.db)
            qry.exec("CALL payment_excludepayment({})".format(qryLook.value(0)))
            if qry.lastError().type() != 0:
                raise DataError("excludePayment", qry.lastError().text())
            if qry.first():
                raise DataError("excludePayment", "Error {} {}".format(qry.value(0), qry.value(1)))
            self.refreshTables()
            self.enableSave()
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def excludeAllPayments(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL payment_excludeallpayments()")
            if qry.lastError().type() != 0:
                raise DataError("excludeAlldePayments", qry.lastError().text())
            if qry.first():
                raise DataError("excludeAlPayment", "Error {} {}".format(qry.value(0), qry.value(1)))
            self.refreshTables()
            self.enableSave()
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print("excludeAllPayments", type(err), err.args)

    @pyqtSlot()
    def deletePayment(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL payment_deletepayment({})".format(self.record.value(0)))
            if qry.lastError().type() != 0:
                raise DataError("Payment: deletePayment", qry.lastError().text())
            if qry.first():
                raise DataError("Payment: deletePayment", "Error {} {}".format(qry.value(0), qry.value(1)))
            self.refreshTables()
            self.parent.updateSupplierAccount(ACCOUNT_PAYMENT)
            self.widgetClose()
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print("deletePayment", type(err), err.args)

    @pyqtSlot()
    def widgetClose(self):
        if self.db.isOpen():
            self.db.close()
        self.done(QDialog.Rejected)

    def saveAndClose(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL payment_save({}, '{}', '{}', {}, {}, {}, {}, {}, {}, '{}', {}, '{}')".format(
                self.mode,
                self.lineNumber.text(),
                self.paymentDate.date().toString("yyyy-MM-dd"),
                self.comboPaymentType.getHiddenData(0),
                self.supplierId,
                float(self.lineAmountToPay.text()),
                self.comboCurrency.currentIndex(),
                "{:.2f}".format(float(self.linePayInPesos.text())) if self.checkLocal.isChecked() else 'NULL',
                self.comboBank.currentIndex() if self.comboBank.currentIndex() != -1 else 'NULL',
                self.lineTransaction.text() if self.comboPaymentType.getHiddenData(0) > 0 else 'NULL',
                'NULL' if self.mode == OPEN_NEW else self.record.value(0),
                self.textNotes.toPlainText()))
            if qry.lastError().type() != 0:
                raise DataError("saveAndClose", qry.lastError().text())
            if qry.first():
                raise DataError("saveAndClose", "Error {} {}".format(qry.value(0), qry.value(1)))
            self.refreshTables()
            self.parent.updateSupplierAccount(ACCOUNT_PAYMENT)
            self.widgetClose()
        except Exception as err:
            print("saveAndClose", type(err), err.args)

class Invoice(QDialog):
    def __init__(self, db, supplierId, payableType, mode=None, con_string=None,
                 invoiceid=None, parent=None, record=None):
        super().__init__(parent=parent)
        self.db = db
        if not self.db.isOpen():
            self.db.open()
        self.invoiceId = invoiceid
        self.con_string = con_string
        self.mode = mode
        self.parent = parent
        self.payableType = payableType
        self.supplierId = supplierId
        self.record = record
        self.localCurrencyAmount = 0.00
        self.setUI()
        self.setWindowIcon(QIcon(":Icons8/Accounts/invoice.png"))
        if self.record is not None:
            self.loadInvoice(record=self.record)

    def setUI(self):
        self.setModal(True)
        self.setWindowTitle("Invoice")
        self.setMinimumSize(1425,800)
        topFrame = QFrame()
        topFrame.setMaximumWidth(3000)
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
        self.lineNumber.setText(self.getInvoiceNumber())
        self.lineNumber.editingFinished.connect(self.enableSave)

        self.lblTotalPayable = QLabel("Total Payable")

        self.lblTotalSelected = QLabel("Total Selected")

        self.lblCurrencyTotal = QLabel("Currency ")
        self.lblCurrencyTotal.hide()
        self.lineCurrencyTotal = QLineEdit()
        self.lineCurrencyTotal.setAlignment(Qt.AlignRight)
        self.lineCurrencyTotal.setMaximumWidth(150)
        self.lineCurrencyTotal.setEnabled(False)
        self.lineCurrencyTotal.hide()
        self.lineCurrencyTotal.editingFinished.connect(self.enableSave)

        lblCurrency = QLabel("Currency")
        self.comboCurrency = FocusCombo(itemList=['U$A', 'AR$'])
        self.comboCurrency.setMinimumWidth(70)
        self.comboCurrency.setModelColumn(1)
        self.comboCurrency.activated.connect(self.updatePayables)
        self.comboCurrency.currentIndexChanged[int].connect(self.togglePaymentModality)

        billDate = self.getDates() if self.getDates() else QDate.currentDate()
        currency = self.getCurrency(billDate.toString("yyyy-MM-dd"))
        self.comboCurrency.setCurrentIndex(currency) if currency is not None else self.comboCurrency.setCurrentIndex(-1)

        lblDate = QLabel('Invoice Date: ')
        self.dateInvoice = QDateEdit()
        self.dateInvoice.setCalendarPopup(True)
        self.dateInvoice.setDate(billDate)
        self.dateInvoice.setDisplayFormat('MM-dd-yyyy')
        self.dateInvoice.setMinimumWidth(120)
        self.dateInvoice.dateChanged.connect(self.enableSave)
        self.dateInvoice.dateChanged.connect(self.updatePayables)


        lblType = QLabel("Invoice Type")
        lblType.setStyleSheet("QLabel {background-color: red; color: white;}")
        lblType.setAlignment(Qt.AlignCenter)

        self.comboType = FocusCombo(itemList=['C', 'A'])
        self.comboType.setMinimumWidth(30)
        self.comboType.setModelColumn(1)
        self.comboType.setCurrentIndex(0)
        self.comboType.currentIndexChanged.connect(self.addIVA)

        lblInvoice = QLabel("Charge type")
        self.comboChargeType = FocusCombo(itemList=['DownPayment', 'Board', 'Full Break', 'Half Break',
                                                     'Sale Sharing', 'Other Charges', 'All Charges'])
        self.comboChargeType.setMinimumWidth(70)
        self.comboChargeType.setCurrentIndex(self.payableType)
        self.comboChargeType.setModelColumn(1)
        self.comboChargeType.setEnabled(False)



        self.lblPaymentMode = QLabel("Payment Modality")
        # self.lblPaymentMode.hide()
        self.comboPaymentModality = FocusCombo(itemList=["US Dollar", "Local Currency"])
        # self.comboPaymentModality.setVisible(False)
        self.comboPaymentModality.setCurrentIndex(self.comboCurrency.getHiddenData(0)) if self.mode == OPEN_NEW \
            else self.comboPaymentModality.setCurrentIndex(-1)
        self.comboPaymentModality.setModelColumn(1)
        self.comboPaymentModality.setMaximumWidth(self.comboChargeType.width())
        self.comboPaymentModality.currentIndexChanged[int].connect(self.paymentModalityChanged)

        self.lblExchangeRate = QLabel("Exchange Rate")
        self.lblExchangeRate.setVisible(False)
        self.lineExchangeRate = QLineEdit()
        self.lineExchangeRate.setVisible(False)
        self.lineExchangeRate.setMaximumWidth(70)
        self.lineExchangeRate.setAlignment(Qt.AlignRight)
        self.lineExchangeRate.editingFinished.connect(self.refreshTotals)

        self.lblBillingAmount = QLabel("Billed Amount in AR$: ")
        self.lblBillingAmount.setVisible(False)
        self.lineBillingAmount = QLineEdit()
        self.lineBillingAmount.setVisible(False)
        self.lineBillingAmount.setMaximumWidth(100)
        self.lineBillingAmount.setEnabled(False)
        self.lineBillingAmount.setAlignment(Qt.AlignRight)

        self.lblTotal = QLabel('Total: ' + self.comboCurrency.currentText())
        self.lineTotal = QLineEdit()
        self.lineTotal.setAlignment(Qt.AlignRight)
        self.lineTotal.setMaximumWidth(150)
        self.lineTotal.setEnabled(False)
        self.lineTotal.editingFinished.connect(self.enableSave)

        self.lblIva = QLabel("IVA 21%")
        self.lblIva.hide()
        self.lineIva = QLineEdit()
        self.lineIva.setMaximumWidth(150)
        self.lineIva.setAlignment(Qt.AlignRight)
        self.lineIva.setEnabled(False)
        self.lineIva.hide()

        self.lblGrandTotal = QLabel("Total {}".format(self.comboCurrency.currentText()))
        self.lblGrandTotal.hide()
        self.lineGrandTotal = QLineEdit()
        self.lineGrandTotal.setAlignment(Qt.AlignRight)
        self.lineGrandTotal.setMaximumWidth(150)
        self.lineGrandTotal.setEnabled(False)
        self.lineGrandTotal.hide()

        lblNotes = QLabel("Notes")

        self.pushDelete = QPushButton("Delete")
        self.pushDelete.setMaximumWidth(70)
        self.pushDelete.setEnabled(False)
        self.pushDelete.clicked.connect(self.deleteInvoice)

        self.textNotes = QTextEdit()

        colorDict = {'column': (10),
                     0: (QColor('white'), QColor('blue')),
                     1: (QColor('red'), QColor('yellow'))}

        colDict = {0: ("Id", True, False, None),
                   1: ("ID", True, False, None),
                   2: ("Date", False, True, False, None),
                   3: ("Horse", False, True, False, None),
                   4: ("Concept", False, False, False, None),
                   5: ("Amount", False, True, 2, None),
                   6: ("Number", True, True, True, None),
                   7: ("typeid", True ,True, True, None),
                   8: ("ahid", True,True, False, None ),
                   9: ("Checked", True, True, False, None),
                   10: ("iid", True, True, False, None)}
        self.setTemporaryTables()
        qryActive, qryBilled = self.getPayables()

        self.tableCheck = TableViewAndModel(colDict=colDict, colorDict=colorDict, size=(100,200), qry=qryActive)
        self.tableCheck.doubleClicked.connect(self.includePayable)
        self.tableCheck.doubleClicked.connect(self.enableSave)

        self.tableBilled = TableViewAndModel(colDict=colDict,colorDict=colorDict, size=(100,200),qry=qryBilled)
        self.tableBilled.doubleClicked.connect(self.excludePayable)
        self.tableBilled.doubleClicked.connect(self.enableSave)

        if self.mode == OPEN_EDIT:
            colorInvDict = {'column': (10),
                         0: (QColor('white'), QColor('black')),
                         1: (QColor('black'), QColor('white'))}
            colInvDict = {0:("Id", True, True, False, None),
                          1:("Number", False,True, False, None),
                          2:("Date", False,True, False, None),
                          3:("Form", False, True, False, None),
                          4:("$", False, True, False, None),
                          5:("Concept", False, False, False, None),
                          6:("total", True, False, 2, None),
                          7:("iva", False, True, 2, None),
                          8:("Grand Total", True, False,2, None),
                          9:("Amount", False, True, 2, None),
                          10:("Currency", True, True, False, None),
                          11:("Billing Currency", True, True, False, None),
                          12:("Iva Rate", True, False, False, None),
                          13:("Exchange Rate", True, False, False, None),
                          14:("Invoicetypeid", True, False, False, None),
                          15:("Chargetypeid", True, False, False, None),
                          16:("Notes", True, True, False, None),
                          17:("Closed", True, True, False, None)}
            qryInvoices = self.getInvoices()
            self.tableInvoices = TableViewAndModel(colInvDict, colorInvDict, (100,100),qryInvoices)
            self.tableInvoices.doubleClicked.connect(self.loadInvoice)
            self.tableInvoices.currentMove.connect(self.cursorMove)
            self.tableInvoices.setMinimumWidth(600)

            lblInvoices = QLabel("Invoices")

            self.textNotes.setMaximumHeight(self.tableInvoices.height())

        self.lblSpinIva = QLabel("IVA(%)")
        self.lblSpinIva.setVisible(False)

        self.spinIva = FocusSpin()
        self.spinIva.setRange(0,100)
        self.spinIva.setMaximumWidth(50)
        self.spinIva.setValue(21)
        self.spinIva.setVisible(False)
        self.spinIva.valueChanged.connect(self.refreshTotals)
        self.spinIva.valueChanged.connect(self.upgradeIvaLbl)

        pushCancel = QPushButton("Exit")
        pushCancel.setMaximumWidth(70)
        pushCancel.clicked.connect(self.widgetClose)

        self.pushSave = QPushButton("Save")
        self.pushSave.setMaximumWidth(70)
        self.pushSave.setEnabled(False)
        self.pushSave.clicked.connect(self.saveAndClose)

        self.pushReset = QPushButton()
        self.pushReset.setIcon(QIcon(":Icons8/Edit/reset.png"))
        self.pushReset.setMaximumWidth(50)
        self.pushReset.setEnabled(False)
        self.pushReset.clicked.connect(self.resetWidget)

        invoiceVLayout = QVBoxLayout()
        invoiceLayout_1 = QHBoxLayout()
        invoiceLayout = QHBoxLayout()

        invoiceLayout_1.addWidget(lblSupplier)
        invoiceLayout_1.addWidget(self.lineSupplier)
        invoiceLayout_1.addWidget(lblCurrency)
        invoiceLayout_1.addWidget(self.comboCurrency)
        invoiceLayout_1.addWidget(lblInvoice)
        invoiceLayout_1.addWidget(self.comboChargeType)
        invoiceLayout_1.addWidget(lblType)
        invoiceLayout_1.addWidget(self.comboType)
        invoiceLayout_1.addWidget(lblNumber)
        invoiceLayout_1.addWidget(self.lineNumber)

        invoiceLayout.addWidget(lblDate, 0, Qt.AlignLeft)
        invoiceLayout.addWidget(self.dateInvoice,0,Qt.AlignLeft )


        invoiceVLayout.addLayout(invoiceLayout_1)
        invoiceVLayout.addLayout(invoiceLayout)

        topLayout = QGridLayout()
        topLayout.addWidget(lblSupplier,0,0,Qt.AlignLeft)
        topLayout.addWidget(self.lineSupplier,0,1,Qt.AlignLeft)
        topLayout.addWidget(lblInvoice,0,2,Qt.AlignLeft)
        topLayout.addWidget(self.comboChargeType,0,3, Qt.AlignLeft)
        topLayout.addWidget(lblCurrency,0,4, Qt.AlignLeft)
        topLayout.addWidget(self.comboCurrency, 0, 5, Qt.AlignLeft)
        topLayout.addWidget(lblNumber,0,6, Qt.AlignRight)
        topLayout.addWidget(self.lineNumber,0,7,Qt.AlignRight)

        topLayout.addWidget(lblDate, 1, 0, Qt.AlignLeft)
        topLayout.addWidget(self.dateInvoice, 1, 1, Qt.AlignLeft)
        topLayout.addWidget(self.lblPaymentMode,1,2)
        topLayout.addWidget(self.comboPaymentModality,1,3)
        topLayout.addWidget(self.lblExchangeRate,1,4)
        topLayout.addWidget(self.lineExchangeRate,1,5)
        topLayout.addWidget(lblType, 1, 6, Qt.AlignRight)
        topLayout.addWidget(self.comboType, 1, 7, Qt.AlignRight)

        topFrame.setLayout(topLayout)

        lblDue = QLabel("Payables Due")
        lblChoose = QLabel("Selected for billing")

        tablesLayout = QGridLayout()
        tablesLayout.addWidget(lblDue, 0, 0)
        tablesLayout.addWidget(lblChoose, 0, 1)
        tablesLayout.addWidget(self.tableCheck,1,0)
        tablesLayout.addWidget(self.tableBilled,1,1)
        tablesLayout.addWidget(self.lblTotalPayable,2,0, Qt.AlignRight)
        tablesLayout.addWidget(self.lblTotalSelected,2,1,Qt.AlignRight)

        totalLayout = QGridLayout()

        totalLayout.addWidget(self.lblSpinIva, 0, 0, Qt.AlignLeft)
        totalLayout.addWidget(self.spinIva, 0, 3, Qt.AlignLeft)
        totalLayout.addWidget(self.lblTotal,0,4, Qt.AlignLeft)
        totalLayout.addWidget(self.lineTotal,0,5,Qt.AlignRight)

        totalLayout.addWidget(self.lblIva,1,4, Qt.AlignLeft)
        totalLayout.addWidget(self.lineIva,1,5, Qt.AlignRight)
        totalLayout.addWidget(self.lblGrandTotal,2,4, Qt.AlignLeft)
        totalLayout.addWidget(self.lineGrandTotal,2,5, Qt.AlignRight)
        totalLayout.addWidget(self.lblBillingAmount,3,4, Qt.AlignLeft)
        totalLayout.addWidget(self.lineBillingAmount,3,5,Qt.AlignRight)

        totalFrame = QFrame()
        totalFrame.setLayout(totalLayout)
        totalFrame.setMinimumHeight(150)
        totalFrame.setFrameStyle(QFrame.Panel | QFrame.Plain)
        totalFrame.setLineWidth(2)

        middleLayout = QHBoxLayout()


        if self.mode == OPEN_EDIT:
            invoiceLayout = QVBoxLayout()
            invoiceLayout.addWidget(lblInvoices)
            invoiceLayout.addWidget(self.tableInvoices)

            notesLayout = QVBoxLayout()
            notesLayout.addWidget(lblNotes)
            notesLayout.addWidget(self.textNotes)

            middleLayout.addLayout(notesLayout)
            middleLayout.addLayout(invoiceLayout)
            middleLayout.addWidget(totalFrame)
            totalFrame.setMaximumHeight(150)
            totalFrame.setMaximumWidth(self.width() * 0.5)
        else:
            middleLayout.addWidget(self.textNotes)
            middleLayout.addWidget(totalFrame)
            self.textNotes.setMaximumHeight(150)
            self.textNotes.setMaximumWidth(self.width() * 0.5)
            totalFrame.setMaximumHeight(150)

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(pushCancel)
        if self.mode == OPEN_EDIT:
            buttonLayout.addWidget(self.pushDelete)
        buttonLayout.addWidget(self.pushReset)
        buttonLayout.addWidget(self.pushSave)

        layout = QVBoxLayout()
        layout.addWidget(topFrame)
        layout.addLayout(tablesLayout)
        layout.addLayout(middleLayout)
        layout.addLayout(buttonLayout)

        self.setLayout(layout)
        self.lineExchangeRate.editingFinished.connect(self.refreshTables)

    @pyqtSlot(int)
    def togglePaymentModality(self, idx):
        try:
            self.parent.comboCurrency.setCurrentIndex(idx)
            self.lblGrandTotal.setText("Total {}".format(self.comboCurrency.currentText()))
            self.lblTotal.setText("Total {}".format(self.comboCurrency.currentText()))
            self.lblPaymentMode.setVisible(not idx)
            self.comboPaymentModality.setVisible(not idx)
            if idx:
                self.lblExchangeRate.setVisible(not idx)
                self.lineExchangeRate.setVisible(not idx)
                self.lblBillingAmount.setVisible(not idx)
                self.lineBillingAmount.setVisible(not idx)


        except AttributeError:
            pass

    @pyqtSlot(int)
    def paymentModalityChanged(self, idx):
        if not self.comboCurrency.currentIndex():
            self.lblExchangeRate.setVisible(idx)
            self.lblBillingAmount.setVisible(idx)
            self.lineExchangeRate.setVisible(idx)
            self.lineBillingAmount.setVisible(idx)
            if idx:
                QMessageBox.information(self, "Exchange Rate", "Don´t forget to enter the exchange rate",
                                        QMessageBox.Ok)
                self.lineExchangeRate.setFocus()
                self.parent.comboCurrency.setCurrentIndex(idx)


    pyqtSlot()
    def setArrows(self):
        pass

    @pyqtSlot(int)
    def cursorMove(self,row):
        self.loadInvoice(row=row)

    @pyqtSlot(int)
    def upgradeIvaLbl(self,iva):
        self.lblIva.setText("IVA " + str(iva) + "%")

    @pyqtSlot(QModelIndex)
    def loadInvoice(self, idx=None, row=None, record=None):
        try:
            row = idx.row()
            qry = self.tableInvoices.model().query()
            if qry.seek(row):
                self.record = qry.record()
                self.lineNumber.setText(self.record.value(1))
                self.dateInvoice.setDate(self.record.value(2))
                self.comboCurrency.setCurrentIndex(self.record.value(10))
                self.spinIva.setValue(self.record.value(12) * 100)
                self.lineExchangeRate.setText(str(self.record.value(13)))
                self.comboType.setCurrentIndex(self.record.value(14))
                self.comboChargeType.setCurrentIndex(self.record.value(15))
                self.textNotes.setText(self.record.value(16))
                self.comboPaymentModality.setCurrentIndex(self.record.value(11))

            qryEdit = QSqlQuery(self.db)
            qryEdit.exec("CALL invoice_loadeditable({})".format(self.record.value(0)))
            if qryEdit.lastError().type() != 0:
                raise DataError("Invoice: loadInvoice", qryEdit.lastError().text())
            if qryEdit.first():
                if not isinstance(qryEdit.value(0), QDate):
                    raise DataError("Invoice: loadInvoice", qryEdit.value(0) )
            self.dateInvoice.setMinimumDate(qryEdit.value(0))
            self.refreshTables()
            if idx is not None or row is not None:
                self.pushReset.setEnabled(True)
                self.pushDelete.setEnabled(True)
                self.pushDelete.setVisible(True)
            else:
                self.pushSave.setEnabled(False)
                self.record = record
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print("Invoice: loadInvoice", err.args)

    def getInvoices(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL invoice_getinvoices({})".format(self.supplierId))
            if qry.lastError().type() != 0:
                raise DataError("Invoice: getInvoices", qry.lastError().text())
            return qry
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def getDates(self):
        try:
            if self.mode == OPEN_NEW:
                qry = QSqlQuery(self.db)
                qry.exec("CALL invoice_getdates({})".format(self.supplierId))
                if qry.lastError().type() != 0:
                    raise DataError("getDates - PastDue", qry.lastError().text())
                if qry.first():
                    return qry.value(0)
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print("getDates", err.args)

    def getCurrency(self, invDate=None):
        if self.mode == OPEN_EDIT:
            return
        qry = QSqlQuery(self.db)
        qry.exec("CALL invoice_getcurrency({}, '{}', {})".format(self.supplierId, invDate, self.mode))
        if qry.lastError().type() != 0:
            raise DataError("Invoice: getCurrency", qry.lastError().text())
        if qry.first():
            if qry.value(0) and qry.value(1):
                pop = QMessageBox()
                pop.setWindowTitle("Currency")
                pop.setWindowIcon(QIcon(":Icons8/Accounts/currency.png"))
                pop.setText('There are payables on both currencies!')
                pop.setIcon(QMessageBox.Question)
                pop.addButton("U$A",QMessageBox.YesRole)
                pop.addButton("AR$", QMessageBox.NoRole)
                pop.setModal(True)
                pop.show()
                res = pop.exec()
                self.comboCurrency.setEnabled(True)
                return res
            elif qry.value(0):
                self.parent.comboCurrency.setCurrentIndex(0)
                return 0
            elif qry.value(1):
                self.parent.comboCurrency.setCurrentIndex(1)
                return 1
        raise DataError("Invoice: getCurrency",  "There are not due  charges before {}".format(invDate) )

    @pyqtSlot()
    def enableSave(self):
        enable = False
        if self.lineNumber.text() and \
            self.lineTotal.text():
                enable = True
        if self.comboPaymentModality.currentIndex() and not self.comboCurrency.currentIndex() and \
                not self.lineExchangeRate.text():
                enable = False
        self.pushSave.setEnabled(enable)
        self.pushReset.setEnabled(enable)

    @pyqtSlot()
    def resetWidget(self):
        self.updatePayables()
        if self.mode == OPEN_EDIT:
            self.pushReset.setEnabled(False)
            self.pushDelete.setEnabled(False)

    @pyqtSlot()
    def widgetClose(self):
        self.done(QDialog.Rejected)

    def setTemporaryTables(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL invoice_gettemporarytables()")
            if qry.lastError().type() != 0:
                raise DataError("Invoice: setTemporaryTables", qry.lastError().text())
            if qry.first():
                raise DataError("Invoice: setTemporaryTables", qry.value(0))
        except DataError as err:
            print(err.source, err.message)

    def getPayables(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL invoice_loadpayables({}, '{}', {}, {})".format(self.supplierId,
                                                                        self.dateInvoice.date().toString("yyyy-MM-dd"),
                                                                        self.payableType,
                                                                        self.comboCurrency.currentIndex()))
            if qry.lastError().type() != 0:
                raise DataError("Invoice: getPayables", qry.lastError().text())
            if qry.first():
                raise DataError("Invoice: getPayables", qry.value(0))
            qryFrom, qryTo = self.refreshTables()
            return qryFrom, qryTo
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def updatePayables(self):
        try:
            self.comboPaymentModality.setCurrentIndex(self.comboCurrency.currentIndex())
            if self.mode == OPEN_NEW:
                self.getPayables()
            #self.tableCheck.model().setQuery(qryCheck)
            #self.tableBilled.model().setQuery(qryBilled)

        except Exception as err:
            pass

    def refreshTables(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL invoice_refreshpayablefrom()")
            if qry.lastError().type() != 0:
                raise DataError("Invoice: refreshTables -check", qry.lastError().text())
            qryTo = QSqlQuery(self.db)
            qryTo.exec("CALL invoice_refreshpayableto()")
            if qryTo.lastError().type() != 0:
                raise DataError("Invoice: refreshTables -billed", qryTo.lastError().text())
            if self.isVisible():
                self.tableCheck.model().setQuery(qry)
                self.tableBilled.model().setQuery(qryTo)
            totalAmount = 0.00
            if qryTo.first():
                qryTo.seek(-1)
                while qryTo.next():
                    totalAmount += qryTo.value(5)
            self.lineTotal.setText('{:.2f}'.format(round(totalAmount,2)))
            self.lineGrandTotal.setText(self.lineTotal.text())
            self.lblTotalSelected.setText("Total Amount Selected: {} {:.2f}".format(
                                          self.comboCurrency.currentText(),  totalAmount))
            totalAmountPayable = 0.00
            if qry.first():
                qry.seek(-1)
                while qry.next():
                    totalAmountPayable += qry.value(5)
            self.lblTotalPayable.setText("Total Amount Due: {} {:.2f}".format(self.comboCurrency.currentText(),
                                          totalAmountPayable))
            self.refreshTotals()
            if not self.isVisible():
                if self.mode == OPEN_EDIT:
                    self.pushDelete.setEnabled(False)
                return qry, qryTo
        except DataError as err:
            print(err.source, err.message)
        except (TypeError, ValueError):
            pass

    def getInvoiceNumber(self):
        qry = QSqlQuery(self.db)
        qry.exec("CALL invoice_getnumber({})".format(self.supplierId))
        if qry.first():
            return qry.value(0)

    def refreshTotals(self):
        try:
            if not self.isVisible():
                return
            exchangeRate = float(self.lineExchangeRate.text()) if self.lineExchangeRate.text() else None
            amount = float(self.lineTotal.text())
            if self.comboType.currentIndex() == 0:
                self.lineIva.clear()
                self.lineGrandTotal.setText("{:.2f}".format(amount))
            else:
                iva = 0.01 * self.spinIva.value()

                self.lblIva.setText("IVA " + str(self.spinIva.value()) + "%")
                self.lineIva.setText('{:.2f}'.format(amount * iva))
                self.lineGrandTotal.setText('{:.2f}'.format(amount * (1 + iva)))
            if  self.comboPaymentModality.currentIndex() == 0 or self.comboCurrency.currentIndex() == 1:
                self.lineBillingAmount.setText(self.lineGrandTotal.text())
            else:
                self.lineBillingAmount.setText("{:.2f}".format(float(self.lineGrandTotal.text()) * exchangeRate))
        except ValueError:
            return
        except Exception as err:
            print("refreshTotals: ", err.args)

    @pyqtSlot()
    def includePayable(self):
        try:
            qry = self.tableCheck.model().query()
            row = self.tableCheck.currentIndex().row()
            qry.seek(row)
            qryInsert = QSqlQuery(self.db)
            qryInsert.exec("""CALL invoice_includepayable({})""".format(
                qry.value(0)))
            if qryInsert.lastError().type() != 0:
                raise DataError("Invoice: includePAYABLE -Insert", qryInsert.lastError().text())
            if qryInsert.first():
                raise DataError("Invoice: includePAYABLE:", qryInsert.value(0))
            self.refreshTables()
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print("Invoice: includePayable", err.args)

    @pyqtSlot()
    def excludePayable(self):
        try:
            qryBilled = self.tableBilled.model().query()
            row = self.tableBilled.currentIndex().row()
            qryBilled.seek(row)
            qry = QSqlQuery(self.db)
            qry.exec("CALL invoice_excludepayable({}, {})".format(qryBilled.value(0), self.mode))
            if qry.lastError().type() != 0:
                raise DataError("Invoice: excludePayable", qry.lastError().text())
            if qry.first():
                raise DataError("Invoice: excludePayable", qry.value(0))
            self.refreshTables()
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot(int)
    def addIVA(self):
        try:
            if int(self.comboType.currentIndex()) == 1:
                self.lblTotal.setText("Subtotal")
                self.lblSpinIva.setVisible(True)
                self.spinIva.setVisible(True)
                self.lblIva.setVisible(True)
                self.lineIva.setVisible(True)
                self.lblGrandTotal.setVisible(True)
                self.lineGrandTotal.setVisible(True)
            else:
                self.lblIva.setVisible(False)
                self.lineIva.setVisible(False)
                self.lblGrandTotal.setVisible(True)
                self.lineGrandTotal.setVisible(True)
                self.lblSpinIva.setVisible(False)
                self.spinIva.setVisible(False)
                #self.lblTotal.setVisible(False)
                #self.lineTotal.setVisible(False)
            self.refreshTotals()
        except ValueError:
            return
        except Exception as err:
            print('addIVA', err.args)

    @pyqtSlot()
    def saveAndClose(self):
        if self.mode == OPEN_EDIT:
            self.editPayable()
            return
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL invoice_save({}, '{}','{}', '{}', {}, '{}', '{}',{}, {}, {}, {}, {}, {},'{}')".format(
                self.supplierId,
                self.lineNumber.text(),
                self.dateInvoice.date().toString("yyyy-MM-dd"),
                self.lineTotal.text(),
                "'{:.2f}'".format(float(self.lineIva.text())) if self.lineIva.isVisible() else 'NULL',
                self.lineGrandTotal.text(),
                self.lineBillingAmount.text(),
                self.comboCurrency.currentIndex(),
                self.comboPaymentModality.currentIndex(),
                "'" + str(self.spinIva.value() * 0.01) + "'" if self.comboType.currentIndex() == 1 else 'NULL',
                "'{}'".format(self.lineExchangeRate.text()) if self.lineExchangeRate.text() else 'NULL',
                self.comboType.currentIndex(),
                self.comboChargeType.currentIndex(),
                self.textNotes.toPlainText()))

            if qry.lastError().type() != 0:
                raise DataError("saveAndClose", qry.lastError().text())
            if qry.first():
                print(qry.value(0))
                raise DataError(" Invoice: saveAndClose", qry.value(0))
            self.refreshTables()
            #self.parent.refreshInvoicesTable()
            self.parent.updateSupplierAccount(ACCOUNT_INVOICE)
            self.widgetClose()
        except DataError as err:
            print(err.source, err.message)
            raise DataError(err.source, err.message)
        except Exception as err:
            print(' Invoice: saveAndClose', err.args)

    def editPayable(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("""CALL invoice_saveeditedinvoice({},'{}', {},
                    {}, {}, {},
                    {}, {}, {},
                    {}, '{}')""".format(
                self.record.value(0),
                self.dateInvoice.date().toString("yyyy-MM-dd"),
                self.lineTotal.text(),
                "'" + self.lineIva.text() + "'" if self.lineIva.text().isnumeric() else 'NULL',
                self.lineGrandTotal.text(),
                self.lineBillingAmount.text(),
                self.comboPaymentModality.currentIndex(),
                "'" + str(self.spinIva.value() * 0.01) + "'" if self.comboType.currentIndex() == 1 else 'NULL',
                self.lineExchangeRate.text(),
                self.comboType.currentIndex(),
                self.textNotes.toPlainText()))
            if qry.lastError().type() != 0:
                raise DataError("saveAndClose", qry.lastError().text())
            if qry.size() == 0:
                QMessageBox.question(self, "Empty Invoice", "Invoice {} is empty. Do you want to delete it?".format(
                    self.lineNumber.text()), QMessageBox.Yes|QMessageBox.No)
                if QMessageBox.Yes:
                    self.deleteInvoice()
            if qry.first():
                print(qry.value(0))
                raise DataError("Invoice editPayable", qry.value(0))
            self.refreshTables()
            self.widgetClose()
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print('saveAndClose', err.args)

    @pyqtSlot()
    def deleteInvoice(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL invoice_delete({})".format(self.record.value(0)))
            if qry.lastError().type() != 0:
                raise DataError("Invoice: deleteInvoice", qry.lastError().text())
            if qry.first():
                print(qry.value(0))
            self.refreshTables()
            self.tableInvoices.model().setQuery(self.getInvoices())
            self.widgetClose()
        except DataError as err:
            print(err.source, err.message)




class Payables(QDialog):

    def __init__(self, db, supplierId, mode=None, parent=None):
        super().__init__()
        self.db = db
        if not self.db.isOpen():
            self.db.open()
        self.record = None
        self.mode = mode
        self.parent = parent
        self.supplierId = supplierId
        self.basedates = self.getDates()
        self.createTemporaryTables()
        self.setUI()

    def setUI(self):
        self.setModal(True)
        self.setMinimumSize(1400, 600)
        self.setWindowTitle("Boarding charges for: {}".format(self.parent.supplier) )

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
        self.lineNumber.setText(self.getNumber())
        self.lineNumber.editingFinished.connect(self.enableSave)

        self.lblPayable = QLabel("Payable amount:")
        self.linePayable = QLineEdit()
        self.linePayable.setAlignment(Qt.AlignRight)
        self.linePayable.setMaximumWidth(100)
        self.linePayable.setEnabled(False)
        self.linePayable.editingFinished.connect(self.enableSave)

        self.lblTotal = QLabel('Selected Amount:')
        self.lblTotal.setAlignment(Qt.AlignRight)
        self.lineTotal = QLineEdit()
        self.lineTotal.setAlignment(Qt.AlignRight)
        self.lineTotal.setMaximumWidth(100)
        self.lineTotal.setEnabled(False)
        self.lineTotal.editingFinished.connect(self.enableSave)

        billQry = self.basedates

        if billQry.first():
            billdate = billQry.value(0)
            fromdate = billQry.value(1)
            todate = billQry.value(2)

        lblDate = QLabel('Date: ')
        self.dateInvoice = QDateEdit()
        self.dateInvoice.setDisplayFormat('yyyy-MM-dd')
        self.dateInvoice.setCalendarPopup(True)
        self.dateInvoice.setDate(billdate)
        self.dateInvoice.setMinimumWidth(120)
        self.dateInvoice.dateChanged.connect(self.enableSave)
        self.dateInvoice.dateChanged.connect(self.setPeriod)
        self.dateInvoice.dateChanged.connect(self.updateElegibleHorses)

        lblFrom = QLabel('From: ')
        self.dateFrom = QDateEdit()
        self.dateFrom.setCalendarPopup(True)
        self.dateFrom.setDisplayFormat('yyyy-MM-dd')
        self.dateFrom.setMinimumWidth(120)
        self.dateFrom.setDate(fromdate)

        lblTo = QLabel('To: ')
        self.dateTo = QDateEdit()
        self.dateTo.setCalendarPopup(True)
        self.dateTo.setDisplayFormat('yyyy-MM-dd')
        self.dateTo.setMinimumWidth(120)
        self.dateTo.setDate(todate)

        lblCurrency = QLabel("Currency")
        self.comboCurrency = FocusCombo(itemList = ['U$A', 'AR$'])
        self.comboCurrency.setCurrentIndex(self.getValidCurrencies())
        self.comboCurrency.setModelColumn(1)
        self.comboCurrency.activated.connect(self.resetHorses)

        self.toolRight = QToolButton()
        self.toolRight.setIcon(QIcon(":Icons8/arrows/right-arrow.png"))
        self.toolRight.setMinimumSize(100, 30)
        self.toolRight.clicked.connect(self.includeCharges)
        self.toolRight.clicked.connect(self.enableSave)
        self.toolRight.setToolTip("Load selected Invoice")
        self.toolRight.setEnabled(False)

        self.toolAllRight = QToolButton()
        self.toolAllRight.setIcon(QIcon(":Icons8/arrows/double-right.png"))
        self.toolAllRight.setMinimumSize(100, 30)
        self.toolAllRight.clicked.connect(self.includeAllCharges)
        self.toolAllRight.setToolTip("Load All Invoices")
        self.toolAllRight.clicked.connect(self.enableSave)
        self.toolAllRight.setEnabled(False)

        self.toolLeft = QToolButton()
        self.toolLeft.setIcon(QIcon(":Icons8/arrows/left-arrow.png"))
        self.toolLeft.setMinimumSize(100, 30)
        self.toolLeft.clicked.connect(self.excludeCharges)
        self.toolLeft.clicked.connect(self.enableSave)
        self.toolLeft.setEnabled(False)

        self.toolAllLeft = QToolButton()
        self.toolAllLeft.setIcon(QIcon(":Icons8/arrows/double-left.png"))
        self.toolAllLeft.setMinimumSize(100, 30)
        self.toolAllLeft.clicked.connect(self.excludeAllCharges)
        self.toolAllLeft.clicked.connect(self.enableSave)
        self.toolAllLeft.setEnabled(False)

        self.checkLocation = QCheckBox("Disable Location Check")


        lblNotes = QLabel("Notes")
        self.textNotes = QTextEdit()
        self.textNotes.setMaximumHeight(100)

        lblCharges = QLabel("Charges Billed")

        colorDict = {}
        colDict = {0: ("HorseID", True, True, False, None),
                   1: ("Horse", False, False, False, None),
                   2: ("DOS", False, True, True, None),
                   3: ("Installment", True, True, 2, None),
                   4: ("Index", False, True, 2, None),
                   5: ("Total", False, True, 2, None),
                   6: ("Currency", True, True, False, None)}
        self.getBillableCharges()
        qry, qryBilled = self.updateTables()
        self.tableCheck = TableViewAndModel(colDict=colDict, colorDict=colorDict, size=(100, 200), qry=qry)
        self.tableCheck.doubleClicked.connect(self.includeCharges)
        self.tableCheck.setMouseTracking(True)
        self.tableCheck.viewportEntered.connect(self.setArrows)
        self.tableCheck.entered.connect(self.setArrows)
        self.tableCheck.setObjectName('tablecheck')
        self.tableCheck.doubleClicked.connect(self.enableSave)

        colBilled = {0: ("HorseID", True, True, False, None),
                     1: ("Horse", False, True, False, None),
                     2: ("Concept", False, False, False, None),
                     3: ("Installment",False, True, 2, None),
                     4: ("Index", False, True, 2, None),
                     5: ("Amount", False, True, 2, None),
                     6: ("Currency", True, True, False, None)}

        self.tableBilled = TableViewAndModel(colDict=colBilled, colorDict=colorDict, size=(100, 200), qry=qryBilled)
        self.tableBilled.doubleClicked.connect(self.excludeCharges)
        self.tableBilled.doubleClicked.connect(self.enableSave)
        self.tableBilled.setObjectName('tableBilled')
        self.tableBilled.setMouseTracking(True)
        self.tableBilled.entered.connect(self.setArrows)
        self.tableBilled.viewportEntered.connect(self.setArrows)

        pushCancel = QPushButton("Exit")
        pushCancel.setMaximumWidth(70)
        pushCancel.clicked.connect(self.widgetClose)

        self.pushSave = QPushButton("Save")
        self.pushSave.setMaximumWidth(70)
        self.pushSave.setEnabled(False)
        self.pushSave.clicked.connect(self.saveAndClose)

        self.pushReset = QPushButton()
        self.pushReset.setIcon(QIcon(":Icons8/Edit/reset.png"))
        self.pushReset.setMaximumWidth(50)
        self.pushReset.setEnabled(False)
        self.pushReset.clicked.connect(self.resetHorses)


        invoiceVLayout = QVBoxLayout()
        invoiceLayout_1 = QHBoxLayout()
        invoiceLayout = QHBoxLayout()

        invoiceLayout_1.addWidget(lblSupplier)
        invoiceLayout_1.addWidget(self.lineSupplier)
        invoiceLayout_1.addWidget(lblCurrency)
        invoiceLayout_1.addWidget(self.comboCurrency)
        #invoiceLayout_1.addWidget(lblInvoice)
        #invoiceLayout_1.addWidget(self.comboInvoiceType)
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
        topFrame.setMaximumHeight(100)

        toolsFrame = QFrame()
        toolsFrame.setMaximumWidth(150)
        toolsFrame.setMaximumHeight(150)

        toolsLayout = QVBoxLayout()
        toolsLayout.addWidget(self.toolRight)
        toolsLayout.addWidget(self.toolAllRight)
        toolsLayout.addWidget(self.toolAllLeft)
        toolsLayout.addWidget(self.toolLeft)
        toolsFrame.setLayout(toolsLayout)


        tablesLayout = QGridLayout()
        tablesLayout.addWidget(self.tableCheck,0,0,)
        tablesLayout.addWidget(toolsFrame,0,3)
        tablesLayout.addWidget(self.tableBilled,0,4,)
        tablesLayout.addWidget(self.lblPayable,2,0,Qt.AlignRight)
        tablesLayout.addWidget(self.lblTotal,2,4,Qt.AlignRight)

        tablesLayout.addWidget(self.checkLocation,3,0)

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(pushCancel)
        buttonLayout.addWidget(self.pushReset)
        buttonLayout.addWidget(self.pushSave)

        layout = QVBoxLayout()
        layout.addWidget(topFrame,0,Qt.AlignHCenter)
        layout.addLayout(tablesLayout)
        layout.addLayout(buttonLayout)

        self.setLayout(layout)
        self.checkLocation.setVisible(True)
        self.checkLocation.stateChanged.connect(self.locationChange)

    @pyqtSlot()
    def setArrows(self):
        action = True if self.sender().objectName() == "tablecheck" else False
        if self.sender().model().query().size() > 0:
            self.toolRight.setEnabled(action)
            self.toolAllRight.setEnabled(action)
            self.toolLeft.setEnabled(not action)
            self.toolAllLeft.setEnabled(not action)

    def getValidCurrencies(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL payables_getcurrency({})".format(self.supplierId))
            if qry.lastError().type() != 0:
                raise DataError("getValidCurencies", qry.lastError().text())
            if qry.first():
                if qry.value(0) == 3:
                    QMessageBox.warning(self,"Currency", "There are active charges in both currencies", QMessageBox.Ok)
                value = qry.value(0) if qry.value(0) in [0,1] else 1
                return value

        except DataError as err:
            raise DataError(err.source, err.message)

    def getNumber(self):
        qry = QSqlQuery(self.db)
        qry.exec("CALL payables_getticketnumber({})".format(self.supplierId))
        if qry.lastError().type() != 0:
            raise DataError("getNumber", qry.lastError().text())
        if qry.first():
            return qry.value(0)

    @pyqtSlot()
    def getDates(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL payables_getdates({})".format( self.supplierId))
            if qry.lastError().type() != 0:
                raise DataError("Payables: getDates", qry.lastError().text())
            if not qry.first():
                raise DataError("Payables: getDates ", "There is no data! Check if there is an active agreement "
                                                     " with started horses.")
            return qry
        except DataError as err:
            raise DataError(err.source, err.message)

    @pyqtSlot()
    def updateElegibleHorses(self):
        self.getBillableCharges()
        self.updateTables(True)

    @pyqtSlot()
    def setPeriod(self):
        dateBase = self.dateInvoice.date().addMonths(-1)
        dateFrom = dateBase.addDays(- dateBase.day() + 1)
        dateTo = dateFrom.addDays(dateFrom.daysInMonth() -1)
        self.dateTo.setDate(dateTo)
        self.dateFrom.setDate(dateFrom)

    @pyqtSlot()
    def getBillableCharges(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL payables_getbillablecharges({}, '{}', '{}', '{}', {} )".format(
                self.supplierId, self.dateInvoice.date().toString('yyyy-MM-dd'),
                self.dateFrom.date().toString('yyyy-MM-dd'), self.dateTo.date().toString('yyyy-MM-dd'),
                not self.checkLocation.isChecked()))

            if qry.lastError().type() != 0:
                raise DataError("Payables: getBillableCharges", qry.lastError().text())
            if self.comboCurrency.currentIndex() == -1:
                self.getCurrency()
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def locationChange(self):
        self.getBillableCharges()
        self.updateTables()
        self.resetHorses()

    def updateTables(self, mode=False):
        try:
            qryBillable = QSqlQuery(self.db)
            qryBillable.exec("CALL payables_loadbillables({})".format(self.comboCurrency.currentIndex()))

            if qryBillable.lastError().type() != 0:
                raise DataError("Payables: updateTables Billable", qryBillable.lastError().text())
            qryBilled = QSqlQuery(self.db)
            qryBilled.exec("CALL payables_loadbilled()")
            if qryBilled.lastError().type() != 0:
                raise DataError("Payables: updateTables - Billed", qryBilled.lastError().text())
            amountPayable = 0
            qryBillable.seek(-1)
            while qryBillable.next():
                amountPayable += qryBillable.value(5)
            self.linePayable.setText("{:.2f}".format(amountPayable))
            self.lblPayable.setText("Amount Payable: {} {}".format(self.comboCurrency.currentText(), amountPayable))
            amountSelected = 0
            qryBilled.seek(-1)
            while qryBilled.next():
                amountSelected += qryBilled.value(5)
            self.lineTotal.setText("{:.2f}".format(amountSelected))
            self.lblTotal.setText("Amount Selected: {} {}".format(self.comboCurrency.currentText(), amountSelected))
            if not mode:
                return qryBillable, qryBilled
            self.tableCheck.model().setQuery(qryBillable)
            self.tableBilled.model().setQuery(qryBilled)
        except DataError as err:
            raise DataError(err.source, err.message)
        except TypeError:
            pass

    def createTemporaryTables(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL payables_createtemporarytables ()")
            if qry.lastError().type() != 0:
                raise DataError("Payables: createTemporaryTable", qry.lastError().text())
            if qry.first():
                raise DataError("Payables: createTemporaryTable", qry.value(0))
        except DataError as err:
            raise DataError(err.source, err.message)


    @pyqtSlot()
    def enableSave(self):
        if not self.lineNumber.text() or \
                not self.lineTotal.text():
            return
        self.pushSave.setEnabled(True)
        self.pushReset.setEnabled(True)

    @pyqtSlot()
    def includeCharges(self):
        try:
            qryInclude = QSqlQuery(self.db)
            qry = self.tableCheck.model().query()
            row = self.tableCheck.currentIndex().row()
            if row < 0:
                row = 0
            qry.seek(row)
            qryInclude.exec("CALL payables_includecharges({},'{}','{}','{}',{},{},{}, {})".format(
                    qry.value(0),
                    qry.value(1),
                    self.dateFrom.date().toString("yyyy-MM-dd"),
                    self.dateTo.date().toString("yyyy-MM-dd"),
                    qry.value(3),
                    'NULL' if qry.value(4) == '' else qry.value(4),
                    qry.value(5),
                    qry.value(6)))
            if qryInclude.lastError().type() != 0:
                raise DataError("Payables: includeCharges", qryInclude.lastError().text())
            if qryInclude.first():
                raise DataError('Payables: includeCharges', qryInclude.value(0))
            self. updateTables(True)
        except DataError as err:
            raise DataError(err.source, err.message)

    @pyqtSlot()
    def includeAllCharges(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL payables_includeallcharges('{}', '{}')".format(
                self.dateFrom.date().toString("yyyy-MM-dd"),
                self.dateTo.date().toString("yyyy-MM-dd")))
            if qry.lastError().type() != 0:
                raise DataError("Payables: includeAllCharges", qry.lastError().text())
            if qry.first():
                raise DataError('Payables: includeAllCharges', qry.value(0))
            self.updateTables(True)
        except DataError as err:
            raise DataError(err.source, err.message)

    @pyqtSlot()
    def excludeCharges(self):
        try:
            qry = self.tableBilled.model().query()
            row = self.tableBilled.currentIndex().row()
            if row < 0:
                row = 0
            qry.seek(row)
            qryExclude = QSqlQuery(self.db)
            qryExclude.exec("CALL payables_excludecharges({})".format(qry.value(0)))
            if qryExclude.lastError().type() != 0:
                raise DataError("Payables: excludeCharges", qryExclude.lastError().text())
            if qryExclude.first():
                raise DataError('Payables: excludeCharges', qryExclude.value(0))
            self.updateTables(True)
        except DataError as err:
            raise DataError(err.source, err.message)

    @pyqtSlot()
    def excludeAllCharges(self):
        try:
            qryExclude = QSqlQuery(self.db)
            qryExclude.exec("CALL payables_excludeAllcharges()")
            if qryExclude.lastError().type() != 0:
                raise DataError("Payables: excludeAllCharges", qryExclude.lastError().text())
            if qryExclude.first():
                raise DataError('Payables: excludeAllCharges', qryExclude.value(0))
            self.updateTables(True)
        except DataError as err:
            raise DataError(err.source, err.message)



    @pyqtSlot()
    def widgetClose(self):
      self.done(QDialog.Rejected)

    @pyqtSlot()
    def resetHorses(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL payables_resethorses")
            if qry.lastError().type() != 0:
                raise DataError("Payables: resetHorses", qry.lastError().text())
            if qry.first():
                raise DataError("Payables: resetHorses", qry.value(0))
            self.updateTables(True)
        except DataError as err:
            raise DataError(err.source, err.message)

    @pyqtSlot()
    def saveAndClose(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL payables_save_and_close({}, '{}', '{}')".format(
                PAYABLES_TYPE_BOARD,
                self.lineNumber.text(),
                self.dateInvoice.date().toString("yyyy-MM-dd")))
            if qry.lastError().type() != 0:
                raise DataError("Payables: saveAndClose", qry.lastError().text())
            if qry.first():
                raise DataError("Payables: saveAndClose", qry.value(0))

        except DataError as err:
            raise DataError(err.source, err.message)
        except Exception as err:
            raise DataError(" Payable Exception: saveAndClose", err.args)
        self.widgetClose()

class Downpayments(QDialog):
    def __init__(self, db, supplierId, mode=None, parent=None):
        super().__init__()
        self.db = db
        if not self.db.isOpen():
            self.db.open()
        self.record = None
        self.mode = mode
        self.parent = parent
        self.supplierId = supplierId
        self.createTemporaryTables()
        self.setUI()

    def setUI(self):
        self.setModal(True)
        self.setMinimumSize(1400, 600)
        self.setWindowTitle("Downpayment charges for: {}".format(self.parent.supplier) )

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
        self.lineNumber.setText(self.getNumber())
        self.lineNumber.editingFinished.connect(self.enableSave)

        self.lblPayable = QLabel("Payable amount:")
        self.linePayable = QLineEdit()
        self.linePayable.setAlignment(Qt.AlignRight)
        self.linePayable.setMaximumWidth(100)
        self.linePayable.setEnabled(False)
        self.linePayable.editingFinished.connect(self.enableSave)

        self.lblTotal = QLabel('Selected Amount:')
        self.lblTotal.setAlignment(Qt.AlignRight)
        self.lineTotal = QLineEdit()
        self.lineTotal.setAlignment(Qt.AlignRight)
        self.lineTotal.setMaximumWidth(100)
        self.lineTotal.setEnabled(False)
        self.lineTotal.editingFinished.connect(self.enableSave)

        qryDate = self.getDates()
        qryDate.first()

        lblDate = QLabel('Date: ')
        self.dateInvoice = QDateEdit()
        self.dateInvoice.setDisplayFormat('yyyy-MM-dd')
        self.dateInvoice.setCalendarPopup(True)
        self.dateInvoice.setDate(qryDate.value(0))
        self.dateInvoice.setMinimumWidth(120)
        self.dateInvoice.setMaximumWidth(180)
        self.dateInvoice.dateChanged.connect(self.changedDate)
        self.dateInvoice.dateChanged.connect(self.enableSave)

        lblCurrency = QLabel("Currency")
        self.comboCurrency = FocusCombo(itemList = ['U$A', 'AR$'])
        self.comboCurrency.setCurrentIndex(self.getValidCurrencies())
        self.comboCurrency.setModelColumn(1)
        self.comboCurrency.activated.connect(self.resetHorses)

        self.toolRight = QToolButton()
        self.toolRight.setIcon(QIcon(":Icons8/arrows/right-arrow.png"))
        self.toolRight.setMinimumSize(100, 30)
        self.toolRight.clicked.connect(self.includeCharges)
        self.toolRight.clicked.connect(self.enableSave)
        self.toolRight.setToolTip("Load selected Invoice")
        self.toolRight.setEnabled(False)

        self.toolAllRight = QToolButton()
        self.toolAllRight.setIcon(QIcon(":Icons8/arrows/double-right.png"))
        self.toolAllRight.setMinimumSize(100, 30)
        self.toolAllRight.clicked.connect(self.includeAllCharges)
        self.toolAllRight.setToolTip("Load All Invoices")
        self.toolAllRight.clicked.connect(self.enableSave)
        self.toolAllRight.setEnabled(False)

        self.toolLeft = QToolButton()
        self.toolLeft.setIcon(QIcon(":Icons8/arrows/left-arrow.png"))
        self.toolLeft.setMinimumSize(100, 30)
        self.toolLeft.clicked.connect(self.excludeCharges)
        self.toolLeft.clicked.connect(self.enableSave)
        self.toolLeft.setEnabled(False)

        self.toolAllLeft = QToolButton()
        self.toolAllLeft.setIcon(QIcon(":Icons8/arrows/double-left.png"))
        self.toolAllLeft.setMinimumSize(100, 30)
        self.toolAllLeft.clicked.connect(self.excludeAllCharges)
        self.toolAllLeft.clicked.connect(self.enableSave)
        self.toolAllLeft.setEnabled(False)

        lblNotes = QLabel("Notes")
        self.textNotes = QTextEdit()
        self.textNotes.setMaximumHeight(100)

        lblCharges = QLabel("Charges Billed")

        colorDict = {}
        colDict = {0: ("HorseID", True, True, False, None),
                   1: ("Horse", False, False, False, None),
                   2: ("DOS", False, True, True, None),
                   3: ("Installment", True, True, 2, None),
                   4: ("Index", False, True, 2, None),
                   5: ("Total", False, True, 2, None),
                   6: ("Currency", True, True, False, None)}
        self.getBillableCharges()
        qry, qryBilled = self.updateTables()
        self.tableCheck = TableViewAndModel(colDict=colDict, colorDict=colorDict, size=(100, 200), qry=qry)
        self.tableCheck.doubleClicked.connect(self.includeCharges)
        self.tableCheck.setMouseTracking(True)
        self.tableCheck.viewportEntered.connect(self.setArrows)
        self.tableCheck.entered.connect(self.setArrows)
        self.tableCheck.setObjectName('tablecheck')
        self.tableCheck.doubleClicked.connect(self.enableSave)

        colBilled = {0: ("HorseID", True, True, False, None),
                     1: ("Horse", False, True, False, None),
                     2: ("Concept", False, False, False, None),
                     3: ("Installment",False, True, 2, None),
                     4: ("Index", False, True, 2, None),
                     5: ("Amount", False, True, 2, None),
                     6: ("Currency", True, True, False, None)}

        self.tableBilled = TableViewAndModel(colDict=colBilled, colorDict=colorDict, size=(100, 200), qry=qryBilled)
        self.tableBilled.doubleClicked.connect(self.excludeCharges)
        self.tableBilled.doubleClicked.connect(self.enableSave)
        self.tableBilled.setObjectName('tableBilled')
        self.tableBilled.setMouseTracking(True)
        self.tableBilled.entered.connect(self.setArrows)
        self.tableBilled.viewportEntered.connect(self.setArrows)

        pushCancel = QPushButton("Exit")
        pushCancel.setMaximumWidth(70)
        pushCancel.clicked.connect(self.widgetClose)

        self.pushSave = QPushButton("Save")
        self.pushSave.setMaximumWidth(70)
        self.pushSave.setEnabled(False)
        self.pushSave.clicked.connect(self.saveAndClose)

        self.pushReset = QPushButton()
        self.pushReset.setIcon(QIcon(":Icons8/Edit/reset.png"))
        self.pushReset.setMaximumWidth(50)
        self.pushReset.setEnabled(False)
        self.pushReset.clicked.connect(self.resetHorses)

        invoiceVLayout = QVBoxLayout()
        invoiceLayout_1 = QHBoxLayout()
        invoiceLayout = QHBoxLayout()

        invoiceLayout_1.addWidget(lblSupplier)
        invoiceLayout_1.addWidget(self.lineSupplier)
        invoiceLayout_1.addWidget(lblCurrency)
        invoiceLayout_1.addWidget(self.comboCurrency)
        invoiceLayout_1.addWidget(lblNumber)
        invoiceLayout_1.addWidget(self.lineNumber)

        invoiceLayout.addWidget(lblDate)
        invoiceLayout.addWidget(self.dateInvoice)
        invoiceLayout.addStretch(100)

        invoiceVLayout.addLayout(invoiceLayout_1)
        invoiceVLayout.addLayout(invoiceLayout)

        topFrame.setLayout(invoiceVLayout)
        topFrame.setMaximumHeight(100)

        toolsFrame = QFrame()
        toolsFrame.setMaximumWidth(150)
        toolsFrame.setMaximumHeight(150)

        toolsLayout = QVBoxLayout()
        toolsLayout.addWidget(self.toolRight)
        toolsLayout.addWidget(self.toolAllRight)
        toolsLayout.addWidget(self.toolAllLeft)
        toolsLayout.addWidget(self.toolLeft)
        toolsFrame.setLayout(toolsLayout)

        tablesLayout = QGridLayout()
        tablesLayout.addWidget(self.tableCheck,0,0,)
        tablesLayout.addWidget(toolsFrame,0,3)
        tablesLayout.addWidget(self.tableBilled,0,4,)
        tablesLayout.addWidget(self.lblPayable,2,0,Qt.AlignRight)
        tablesLayout.addWidget(self.lblTotal,2,4,Qt.AlignRight)

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(pushCancel)
        buttonLayout.addWidget(self.pushReset)
        buttonLayout.addWidget(self.pushSave)

        layout = QVBoxLayout()
        layout.addWidget(topFrame,0,Qt.AlignHCenter)
        layout.addLayout(tablesLayout)
        layout.addLayout(buttonLayout)

        self.setLayout(layout)

    def getDates(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL downpayments_getdates({})".format(self.supplierId))
            if qry.lastError().type() != 0:
                raise DataError("Downpayments: getDates", qry.lastError().text())
            if not qry.first():
                raise DataError("Downpayments: getDates ", "There is no data! Check if there are agreements  "
                                                       " including downpayments unpaid.")
            return qry
        except DataError as err:
            raise DataError(err.source, err.message)

    def createTemporaryTables(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL payables_createtemporarytables ()")
            if qry.lastError().type() != 0:
                raise DataError("Downpayments: createTemporaryTable", qry.lastError().text())
            if qry.first():
                raise DataError("Downpayment: createTemporaryTable", qry.value(0))
        except DataError as err:
            raise DataError(err.source, err.message)

    def getNumber(self):
        qry = QSqlQuery(self.db)
        qry.exec("CALL payables_getticketnumber({})".format(self.supplierId))
        if qry.lastError().type() != 0:
            raise DataError("Downpayments: getNumber", qry.lastError().text())
        if qry.first():
            return qry.value(0)

    def getValidCurrencies(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL downpayments_getcurrency({})".format(self.supplierId))
            if qry.lastError().type() != 0:
                raise DataError("Downpayments: getValidCurencies", qry.lastError().text())
            if qry.first():
                if qry.value(0) == 3:
                    QMessageBox.warning(self,"Currency", "There are active charges in both currencies", QMessageBox.Ok)
                value = qry.value(0) if qry.value(0) in [0,1] else 1
                return value
        except DataError as err:
            raise DataError(err.source, err.message)

    @pyqtSlot()
    def changedDate(self):
        self.getBillableCharges()
        self.updateTables(mode=True)


    @pyqtSlot()
    def enableSave(self):
        if not self.lineNumber.text() or \
                not self.lineTotal.text():
            return
        self.pushSave.setEnabled(True)
        self.pushReset.setEnabled(True)

    @pyqtSlot()
    def includeCharges(self):
        try:
            qryInclude = QSqlQuery(self.db)
            qry = self.tableCheck.model().query()
            row = self.tableCheck.currentIndex().row()
            if row < 0:
                row = 0
            qry.seek(row)
            qryInclude.exec("CALL downpayments_includecharges({},'{}',{},{},{}, {})".format(
                qry.value(0),
                qry.value(1),
                qry.value(3),
                'NULL' if qry.value(4) == '' else qry.value(4),
                qry.value(5),
                qry.value(6)))
            if qryInclude.lastError().type() != 0:
                raise DataError("Downpayments: includeCharges", qryInclude.lastError().text())
            if qryInclude.first():
                raise DataError('Downpayments: includeCharges', qryInclude.value(0))
            self.updateTables(True)
        except DataError as err:
            raise DataError(err.source, err.message)

    @pyqtSlot()
    def includeAllCharges(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL downpayments_includeallcharges()")
            if qry.lastError().type() != 0:
                raise DataError("Downpayments: includeAllCharges", qry.lastError().text())
            if qry.first():
                raise DataError('Downpayments: includeAllCharges', qry.value(0))
            self.updateTables(True)
        except DataError as err:
            raise DataError(err.source, err.message)

    @pyqtSlot()
    def excludeCharges(self):
        try:
            qry = self.tableBilled.model().query()
            row = self.tableBilled.currentIndex().row()
            if row < 0:
                row = 0
            qry.seek(row)
            qryExclude = QSqlQuery(self.db)
            qryExclude.exec("CALL payables_excludecharges({})".format(qry.value(0)))
            if qryExclude.lastError().type() != 0:
                raise DataError("Downpayments: excludeCharges", qryExclude.lastError().text())
            if qryExclude.first():
                raise DataError('Downpayments: excludeCharges', qryExclude.value(0))
            self.updateTables(True)
        except DataError as err:
            raise DataError(err.source, err.message)

    @pyqtSlot()
    def excludeAllCharges(self):
        try:
            qryExclude = QSqlQuery(self.db)
            qryExclude.exec("CALL payables_excludeAllcharges()")
            if qryExclude.lastError().type() != 0:
                raise DataError("Downpayments: excludeAllCharges", qryExclude.lastError().text())
            if qryExclude.first():
                raise DataError('Downpayments: excludeAllCharges', qryExclude.value(0))
            self.updateTables(True)
        except DataError as err:
            raise DataError(err.source, err.message)

    @pyqtSlot()
    def resetHorses(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL payables_resethorses")
            if qry.lastError().type() != 0:
                raise DataError("Payables: resetHorses", qry.lastError().text())
            if qry.first():
                raise DataError("Payables: resetHorses", qry.value(0))
            self.updateTables(True)
        except DataError as err:
            raise DataError(err.source, err.message)

    @pyqtSlot()
    def getBillableCharges(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL downpayments_getbillablecharges({}, '{}')".format(
                self.supplierId, self.dateInvoice.date().toString('yyyy-MM-dd')))

            if qry.lastError().type() != 0:
                raise DataError("Downpayments: getBillableCharges", qry.lastError().text())
            if qry.first():
                raise DataError("Downpayments: getBillableCharges", qry.value(0))
            if self.comboCurrency.currentIndex() == -1:
                self.getCurrency()
        except DataError as err:
            print(err.source, err.message)

    def updateTables(self, mode=False):
        try:
            qryBillable = QSqlQuery(self.db)
            qryBillable.exec("CALL payables_loadbillables({})".format(self.comboCurrency.currentIndex()))

            if qryBillable.lastError().type() != 0:
                raise DataError("Downpayments: updateTables Billable", qryBillable.lastError().text())
            qryBilled = QSqlQuery(self.db)
            qryBilled.exec("CALL payables_loadbilled()")
            if qryBilled.lastError().type() != 0:
                raise DataError("Downpayments: updateTables - Billed", qryBilled.lastError().text())
            amountPayable = 0
            qryBillable.seek(-1)
            while qryBillable.next():
                amountPayable += qryBillable.value(5)
            self.linePayable.setText("{:.2f}".format(amountPayable))
            self.lblPayable.setText("Amount Payable: {} {}".format(self.comboCurrency.currentText(), amountPayable))
            amountSelected = 0
            qryBilled.seek(-1)
            while qryBilled.next():
                amountSelected += qryBilled.value(5)
            self.lineTotal.setText("{:.2f}".format(amountSelected))
            self.lblTotal.setText("Amount Selected: {} {}".format(self.comboCurrency.currentText(), amountSelected))
            if not mode:
                return qryBillable, qryBilled
            self.tableCheck.model().setQuery(qryBillable)
            self.tableBilled.model().setQuery(qryBilled)
        except DataError as err:
            raise DataError(err.source, err.message)
        except TypeError:
            pass

    @pyqtSlot()
    def setArrows(self):
        action = True if self.sender().objectName() == "tablecheck" else False
        if self.sender().model().query().size() > 0:
            self.toolRight.setEnabled(action)
            self.toolAllRight.setEnabled(action)
            self.toolLeft.setEnabled(not action)
            self.toolAllLeft.setEnabled(not action)

    @pyqtSlot()
    def saveAndClose(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL payables_save_and_close({}, '{}', '{}')".format(
                PAYABLES_TYPE_DOWNPAYMENT,
                self.lineNumber.text(),
                self.dateInvoice.date().toString("yyyy-MM-dd")))
            if qry.lastError().type() != 0:
                raise DataError("Payables: saveAndClose", qry.lastError().text())
            if qry.first():
                raise DataError("Payables: saveAndClose", qry.value(0))

        except DataError as err:
            raise DataError(err.source, err.message)
        except Exception as err:
            raise DataError(" Payable Exception: saveAndClose", err.args)
        self.widgetClose()

    @pyqtSlot()
    def widgetClose(self):
        self.done(QDialog.Rejected)



class OtherCharge(QDialog):

    def __init__(self, db, supplierId, mode=None,
                 parent=None):
        super().__init__()
        self.db = db
        if not self.db.isOpen():
            self.db.open()
        self.mode = mode
        self.parent = parent
        self.record = None
        self.supplierId = supplierId
        self.lastDate = None
        self.setUI()

    def setUI(self):
        self.setModal(True)
        self.setWindowTitle("Other Charges {}".format(self.parent.supplier))
        topFrame = QFrame()
        topFrame.setMaximumWidth(1000)
        topFrame.setFrameStyle(QFrame.Panel | QFrame.Plain)
        topFrame.setLineWidth(2)

        middleFrame = QFrame()
        middleFrame.setMaximumWidth(1000)
        middleFrame.setFrameStyle(QFrame.Panel | QFrame.Plain)
        middleFrame.setLineWidth(2)

        lblSupplier = QLabel('Supplier: ')
        self.lineSupplier = QLineEdit()
        self.lineSupplier.setEnabled(False)
        self.lineSupplier.setMinimumWidth(300)
        self.lineSupplier.setText(self.parent.supplier)

        lblNumber = QLabel("Ticket #: ")
        self.lineNumber = QLineEdit()
        self.lineNumber.setMaximumWidth(100)
        self.lineNumber.setAlignment(Qt.AlignRight)
        self.lineNumber.setText(self.getNumber())
        self.lineNumber.editingFinished.connect(self.enableSave)

        lblTotal = QLabel('Total Amount:')
        lblTotal.setAlignment(Qt.AlignRight)
        self.lineTotal = QLineEdit()
        self.lineTotal.setAlignment(Qt.AlignRight)
        self.lineTotal.setMaximumWidth(400)
        self.lineTotal.editingFinished.connect(self.enableSave)

        lblInvoice = QLabel("Payable for: ")
        self.comboInvoiceType = FocusCombo(itemList=['DownPayment', 'Board', 'Half Break', 'Final Break', 'Sale Share',
                                                     'OtherCharge'])
        self.comboInvoiceType.setMinimumWidth(70)
        self.comboInvoiceType.setCurrentIndex(5)
        self.comboInvoiceType.setModelColumn(1)
        self.comboInvoiceType.setEnabled(False)
        self.comboInvoiceType.activated.connect(self.enableSave)

        lblAgreement = QLabel("Agreements")
        self.comboAgreements = FocusCombo()
        self.comboAgreements.model().setQuery(self.getAgreements())
        self.comboAgreements.setModelColumn(1)
        self.comboAgreements.activated.connect(lambda: self.getHorses(True))

        lastDate = self.getLastChargeDate()

        lblDate = QLabel('Date: ')
        lblDate.setAlignment(Qt.AlignRight)
        self.dateInvoice = QDateEdit()
        self.dateInvoice.setCalendarPopup(True)
        self.dateInvoice.setDate(lastDate)
        self.dateInvoice.setDisplayFormat('MM-dd-yyyy')
        self.dateInvoice.setMinimumWidth(120)
        self.dateInvoice.dateChanged.connect(self.enableSave)

        lblAccount = QLabel("Account")
        lblAccount.setAlignment(Qt.AlignRight)
        self.comboAccount = FocusCombo(self, sorted(['Transportation',
                                              'Veterinary',
                                              'Blacksmith',
                                              'Tack',
                                              'Club Fee',
                                              'Tournament Fee',
                                              'Stalls & Pens',
                                              'Other',
                                              'Board',
                                               'Downpayment',
                                                'Sale',
                                                'Brake',
                                                'Half Break']))
        self.comboAccount.setMinimumWidth(150)
        self.comboAccount.setCurrentIndex(-1)
        self.comboAccount.setModelColumn(1)
        self.comboAccount.currentIndexChanged.connect(self.enableSave)
        self.comboAccount.activated.connect(self.testCombo)

        lblCurrency = QLabel("Currency")
        self.comboCurrency = FocusCombo(self, itemList=['U$A', 'AR$'])
        self.comboCurrency.setModelColumn(1)
        self.comboCurrency.setCurrentIndex(1)


        lblHorses = QLabel("Horse")
        lblHorses.setAlignment(Qt.AlignRight)
        self.comboHorses = FocusCombo()
        self.comboHorses.model().setQuery(self.getHorses())
        self.comboHorses.setCurrentIndex(-1)
        self.comboHorses.setModelColumn(1)
        self.comboHorses.setMaximumWidth(200)
        self.comboHorses.activated.connect(self.loadAgreement)
        self.comboHorses.activated.connect(self.enableSave)

        lblConcept = QLabel('Concept')
        lblConcept.setAlignment(Qt.AlignRight)
        self.lineConcept = QLineEdit()
        self.lineConcept.setMaximumWidth(400)
        self.lineConcept.editingFinished.connect(self.enableSave)

        pushReset = QPushButton()
        pushReset.setIcon(QIcon(":Icons8/Edit/reset.png"))
        pushReset.setMaximumWidth(50)
        pushReset.clicked.connect(self.resetWidget)

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
        invoiceLayout.addWidget(lblAgreement)
        invoiceLayout.addWidget(self.comboAgreements)
        invoiceLayout.addWidget(lblCurrency)
        invoiceLayout.addWidget(self.comboCurrency)
        invoiceLayout.addStretch(100)

        topFrame.setLayout(invoiceVLayout)

        tablesLayout = QHBoxLayout()

        totalLayout = QGridLayout()
        totalLayout.addWidget(lblHorses,0,0)
        totalLayout.addWidget(self.comboHorses,0,1)
        totalLayout.addWidget(lblAccount,0,2)
        totalLayout.addWidget(self.comboAccount,0,3)
        totalLayout.addWidget(lblConcept,1,0)
        totalLayout.addWidget(self.lineConcept,1,1)
        totalLayout.addWidget(lblTotal, 1, 2, Qt.AlignRight)
        totalLayout.addWidget(self.lineTotal, 1, 3, Qt.AlignRight)

        invoiceVLayout.addLayout(invoiceLayout_1)
        invoiceVLayout.addLayout(invoiceLayout)

        middleFrame.setLayout(totalLayout)

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(pushReset)
        buttonLayout.addWidget(pushCancel)
        buttonLayout.addWidget(self.pushSave)

        layout = QVBoxLayout()
        layout.addWidget(topFrame)
        layout.addWidget(middleFrame)
        layout.addLayout(buttonLayout)

        self.setLayout(layout)

    @pyqtSlot()
    def testCombo(self):
        a = self.comboAccount.currentText()
        print(a)

    def getCharges(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL othercharges_get({})".format(self.supplierId))
            if qry.lastError().type() != 0:
                raise DataError("getCharges", qry.lastError().text())
            return qry
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def loadAgreement(self):
        self.comboAgreements.seekData(self.comboHorses.getHiddenData(2))

    @pyqtSlot()
    def enableSave(self):
        if self.lineNumber.text() and \
                self.lineTotal.text() and \
                self.lineConcept.text() and \
                self.comboAccount.currentIndex() != -1:
            self.pushSave.setEnabled(True)

    @pyqtSlot()
    def widgetClose(self):
        self.done(QDialog.Rejected)

    @pyqtSlot()
    def saveAndClose(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL othercharges_saveAndClose('{}', '{}', {} , {}, '{}', {}, '{}')".format(
                self.lineNumber.text(),
                self.dateInvoice.date().toString("yyyy-MM-dd"),
                PAYABLES_TYPE_OTHER,
                self.comboHorses.getHiddenData(0),
                self.lineConcept.text(),
                self.lineTotal.text(),
                self.comboCurrency.getHiddenData(0),
                self.comboAccount.getHiddenData(0)))
            if qry.lastError().type() != 0:
                raise DataError("OtherCharge: saveAndClose", qry.lastError().text(),qry.lastError().number())
            if qry.first():
                raise DataError("OtherCharge: saveAndClose", qry.value(0))
            self.widgetClose()
        except DataError as err:
            print(err.source, err.message)


    def getLastChargeDate(self):
        try:
            qry = QSqlQuery(self.db)
            qry.prepare("""SELECT MAX(o.date) FROM 
            othercharges o
            WHERE 
            o.supplierid = ?""")
            qry.addBindValue(QVariant(self.supplierId))
            qry.exec()
            if qry.lastError().type() != 0:
                raise DataError("OtherCharge: getLastChargeDate", qry.lastError().text())
            qry.first()
            if not qry.value(0).isNull():
                startDate = qry.value(0)
            else:
                startDate = QDate.currentDate().addDays(-30)
            return startDate
        except DataError as err:
            print(err.source, err.message)

    def getHorses(self, mode=False):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("call othercharges_gethorses({}, {})".format(self.supplierId,
            'NULL' if self.comboAgreements.currentIndex() < 0 else self.comboAgreements.getHiddenData(0)))
            if qry.lastError().type() != 0:
                raise DataError("OtherChatge: getHorses", qry.lastError().text())
            if not mode:
                return qry
            self.comboHorses.model().setQuery(qry)
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def setAgreement(self):
        self.comboAgreements.seekData(self.comboHorses.getHiddenData(2), 0)

    @pyqtSlot()
    def resetWidget(self):
        self.lineNumber.setText(self.getNumber())
        self.lineConcept.clear()
        self.lineTotal.clear()
        self.dateInvoice.setDate(self.getLastChargeDate())
        self.comboAgreements.setCurrentIndex(-1)
        self.getHorses()
        self.comboAccount.setCurrentIndex(-1)
        self.comboHorses.setCurrentIndex(-1)

        self.pushSave.setEnabled(False)

    def getDates(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL downpayments_getdates({})".format(self.supplierId))
            if qry.lastError().type() != 0:
                raise DataError("OtherCharge: getDates", qry.lastError().text())
            if not qry.first():
                raise DataError("OtherCharge: getDates ", "There is no data! Check if there is an active agreement "
                                                       " with started horses.")
            return qry
        except DataError as err:
            raise DataError(err.source, err.message)

    def getAgreements(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL othercharges_getagreements({})".format(self.supplierId))
            if qry.lastError().type() != 0:
                raise DataError("OtherCharge: getAgreements", qry.lastError().text())
            if not qry.first():
                raise DataError("OtherCharge: getAgreements ", "There is no data! Check if there is an active agreement.")
            return qry
        except DataError as err:
            raise DataError(err.source, err.message)

    def getNumber(self):
        qry = QSqlQuery(self.db)
        qry.exec("CALL payables_getticketnumber({})".format(self.supplierId))
        if qry.lastError().type() != 0:
            raise DataError("getNumber", qry.lastError().text())
        if qry.first():
            return qry.value(0)

class EditPayables(QDialog):

    def __init__(self, db, supplierId, payableType=None, parent=None):
        super().__init__()
        self.db = db
        if not self.db.isOpen():
            self.db.open()
        self.payableType = payableType
        self.parent = parent
        self.record = None
        self.supplierId = supplierId
        self.lastDate = None
        self.setUI()

    def setUI(self):
        self.setModal(True)
        self.setWindowTitle("Edit payable Charges {}".format(self.parent.supplier))
        self.setMinimumWidth(1041)
        topFrame = QFrame()
        topFrame.setMaximumWidth(1000)
        topFrame.setFrameStyle(QFrame.Panel | QFrame.Plain)
        topFrame.setLineWidth(2)

        middleFrame = QFrame()
        middleFrame.setMaximumWidth(1000)
        middleFrame.setFrameStyle(QFrame.Panel | QFrame.Plain)
        middleFrame.setLineWidth(2)

        lblSupplier = QLabel('Supplier: ')
        self.lineSupplier = QLineEdit()
        self.lineSupplier.setEnabled(False)
        self.lineSupplier.setMinimumWidth(300)
        self.lineSupplier.setText(self.parent.supplier)

        lblNumber = QLabel("Ticket #: ")
        self.lineNumber = QLineEdit()
        self.lineNumber.setMaximumWidth(100)
        self.lineNumber.setAlignment(Qt.AlignRight)
        self.lineNumber.setEnabled(False)

        lblTotal = QLabel('Total Amount:')
        #lblTotal.setAlignment(Qt.AlignRight)
        self.lineTotal = QLineEdit()
        self.lineTotal.setAlignment(Qt.AlignRight)
        self.lineTotal.setMaximumWidth(400)
        self.lineTotal.setEnabled(False)

        lblInstallment = QLabel("Installment")
        self.lineInstallment = QLineEdit()
        self.lineInstallment.setAlignment(Qt.AlignRight)
        self.lineInstallment.setMaximumWidth(400)
        self.lineInstallment.editingFinished.connect(self.enableSave)
        self.lineInstallment.editingFinished.connect(self.updateAmount)

        lblIndex = QLabel("Cost Index")
        self.lineIndex = QLineEdit()
        self.lineIndex.setAlignment(Qt.AlignRight)
        self.lineIndex.setMaximumWidth(50)
        self.lineIndex.setEnabled(False)


        lblInvoice = QLabel("Payable for: ")
        self.comboInvoiceType = FocusCombo(itemList=['DownPayment', 'Board', 'Half Break', 'Final Break', 'Sale Share',
                                                     'OtherCharge'])
        self.comboInvoiceType.setMinimumWidth(70)
        self.comboInvoiceType.setCurrentIndex(-1)
        self.comboInvoiceType.setModelColumn(1)
        self.comboInvoiceType.setEnabled(False)

        lblAgreement = QLabel("Agreements")
        self.comboAgreements = FocusCombo()
        self.comboAgreements.model().setQuery(self.getAgreements())
        self.comboAgreements.setModelColumn(1)
        self.comboAgreements.setEnabled(False)

        lblDate = QLabel('Date: ')
        self.dateInvoice = NullDateEdit(self)
        self.dateInvoice.setDate(QDate(55555,76,89))
        self.dateInvoice.setMinimumWidth(120)
        self.dateInvoice.dateChanged.connect(self.enableSave)

        lblAccount = QLabel("Account")
        self.comboAccount = FocusCombo(self, sorted(['Transportation',
                                              'Veterinary',
                                              'Blacksmith',
                                              'Tack',
                                              'Club Fee',
                                              'Tournament Fee',
                                              'Stalls & Pens',
                                              'Other',
                                              'Board',
                                               'Downpayment',
                                                'Sale',
                                                'Brake',
                                                'Half Break']))
        self.comboAccount.setMinimumWidth(150)
        self.comboAccount.setCurrentIndex(-1)
        self.comboAccount.setModelColumn(1)
        self.comboAccount.setEnabled(False)

        lblCurrency = QLabel("Currency")
        self.comboCurrency = FocusCombo(self, itemList=['U$A', 'AR$'])
        self.comboCurrency.setModelColumn(1)
        self.comboCurrency.setCurrentIndex(-1)
        self.comboCurrency.setEnabled(False)

        lblHorses = QLabel("Horse")
        self.comboHorses = FocusCombo()
        self.comboHorses.model().setQuery(self.getHorses())
        self.comboHorses.setCurrentIndex(-1)
        self.comboHorses.setModelColumn(1)
        self.comboHorses.setMaximumWidth(200)
        self.comboHorses.setEnabled(False)

        lblConcept = QLabel('Concept')
        self.lineConcept = QLineEdit()
        self.lineConcept.setMaximumWidth(400)
        self.lineConcept.editingFinished.connect(self.enableSave)

        self.pushReset = QPushButton()
        self.pushReset.setIcon(QIcon(":Icons8/Edit/reset.png"))
        self.pushReset.setMaximumWidth(50)
        self.pushReset.clicked.connect(self.resetWidget)
        self.pushReset.setEnabled(False)

        qry = self.getCharges()
        colorDict = {'column': (13),
                     False: (QColor('red'), QColor('yellow')),
                     True: (QColor('white'), QColor('black'))}

        colDict = {0: ("ID", True, True, False, None),
                1: ("Number", False, True, False, None),
                2: ("Date", False, True, False, None),
                3: ("Horse", False, True, False, None),
                4: ("Concept", False, True, False, None),
                5: ("Installment", False, True, 2, None),
                6: ("Idx", False, True, False, None),
                7: ("Amount", False, True, 2, None),
                8: ("Type", False, True, False, None),
                9: ("$", False, True, False, None),
                10: ("Payabletype", True, True, False, None),
                11: ("Agreementhorseid", True, True, False, None),
                12: ("Currencyid", True, True, False, None),
                13: ("Accountid", True, True, False, None)}

        self.tableCharges = TableViewAndModel(colDict=colDict, colorDict=colorDict, size=(100, 200), qry=qry)
        self.tableCharges.doubleClicked.connect(self.loadCharge)
        self.tableCharges.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tableCharges.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tableCharges.doubleClicked.connect(self.enableSave)
        self.setWindowTitle("Edit {}".format(self.windowTitle()))

        self.pushDelete = QPushButton("Delete")
        self.pushDelete.setMaximumWidth(70)
        self.pushDelete.clicked.connect(self.deleteCharge)
        self.pushDelete.setEnabled(False)

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
        invoiceLayout.addWidget(lblAgreement)
        invoiceLayout.addWidget(self.comboAgreements)
        invoiceLayout.addWidget(lblCurrency)
        invoiceLayout.addWidget(self.comboCurrency)
        invoiceLayout.addStretch(100)

        topFrame.setLayout(invoiceVLayout)

        tablesLayout = QHBoxLayout()

        totalLayout = QGridLayout()
        totalLayout.addWidget(lblHorses, 0, 0)
        totalLayout.addWidget(self.comboHorses, 0, 1)
        totalLayout.addWidget(lblAccount, 0, 2)
        totalLayout.addWidget(self.comboAccount, 0, 3)
        totalLayout.addWidget(lblInstallment,1,2)
        totalLayout.addWidget(self.lineInstallment,1,3, Qt.AlignRight)
        totalLayout.addWidget(lblConcept, 1, 0)
        totalLayout.addWidget(self.lineConcept, 1, 1)
        totalLayout.addWidget(lblIndex, 2, 0)
        totalLayout.addWidget(self.lineIndex, 2, 1)
        totalLayout.addWidget(lblTotal, 2, 2, Qt.AlignRight)
        totalLayout.addWidget(self.lineTotal, 2, 3, Qt.AlignRight)

        invoiceVLayout.addLayout(invoiceLayout_1)
        invoiceVLayout.addLayout(invoiceLayout)

        middleFrame.setLayout(totalLayout)

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(self.pushReset)
        buttonLayout.addWidget(self.pushDelete)
        buttonLayout.addWidget(pushCancel)
        buttonLayout.addWidget(self.pushSave)

        layout = QVBoxLayout()
        layout.addWidget(topFrame)
        layout.addWidget(middleFrame)
        layout.addWidget(self.tableCharges)

        layout.addLayout(buttonLayout)

        self.setLayout(layout)

    def getCharges(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL editpayables_getpayables({}, {})".format(self.supplierId, self.payableType))
            if qry.lastError().type() != 0:
                raise DataError("EditPayables: getCharges", qry.lastError().text())
            return qry
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def deleteCharge(self):
        try:
            ans = QMessageBox.question(self, "Warning", "You're about to delete the current record for {} in "
                                                        "concept of {} Confirm (Y/N)".format(self.record.value(3),
                                                        self.record.value(4)),
                                       QMessageBox.Yes | QMessageBox.No)
            if ans == QMessageBox.No:
                return
            qry = QSqlQuery(self.db)
            qry.exec("CALL editpayables_deletecharge({})".format(self.record.value(0)))
            if qry.lastError().type() != 0:
                raise DataError("EditPayables: deleteCharge", qry.lastError().text())
            if qry.first():
                raise DataError("EditPayables: deleteCharge", qry.value(0))
            qryCharges = self.getCharges()
            self.tableCharges.model().setQuery(qryCharges)
        except DataError as err:
            raise DataError(err.source, err.message)


    @pyqtSlot()
    def updateAmount(self):
        try:
            if self.lineIndex.text():
                self.lineTotal.setText(str(round(float(self.lineInstallment.text()) * float(self.lineIndex.text()),2)))
            else:
                self.lineTotal.setText(self.lineInstallment.text())
        except Exception as err:
            print("EditPayables: updateAmount", err.args)

    @pyqtSlot()
    def enableSave(self):
        if self.lineNumber.text() and \
                self.lineTotal.text() and \
                self.lineConcept.text() and \
                self.comboAccount.currentIndex() != -1:
            self.pushSave.setEnabled(True)
            self.pushDelete.setEnabled(True)
            self.pushReset.setEnabled(True)

    def loadCharge(self):
        try:
            row = self.tableCharges.currentIndex().row()
            qry = self.tableCharges.model().query()
            qry.seek(row)
            record = self.tableCharges.model().query().record()
            self.comboInvoiceType.seekData(record.value(10))
            self.lineNumber.setText(record.value(1))
            self.dateInvoice.setDate(record.value(2))
            self.comboCurrency.seekData(record.value(12))
            self.comboHorses.seekData(record.value(11))
            self.comboAccount.seekData(record.value(13))
            self.comboAgreements.seekData(self.comboHorses.getHiddenData(2))
            self.lineIndex.setText(str(record.value(6))) if record.value(6) > 0 else self.lineIndex.setText(None)
            self.lineInstallment.setText(str(record.value(5)))
            self.lineConcept.setText(record.value(4))
            self.lineTotal.setText(str(record.value(7)))
            self.record = record
            self.enableSave()

        except Exception as err:
            print("EditPayables: loadCharge", err.args)

    @pyqtSlot()
    def widgetClose(self):
        self.done(QDialog.Rejected)

    @pyqtSlot()
    def saveAndClose(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL editpayables_saveandclose({}, '{}', '{}' , {}, {})".format(
                self.record.value(0),
                self.dateInvoice.date.toString("yyyy-MM-dd"),
                self.lineConcept.text(),
                self.lineInstallment.text(),
                self.lineTotal.text()))
            if qry.lastError().type() != 0:
                raise DataError("EditPayables: saveAndClose", qry.lastError().text())
            if qry.first():
                raise DataError("EditPayables: saveAndClose", qry.value(0))
            self.widgetClose()
        except DataError as err:
            print(err.source, err.message)

    def getHorses(self, mode=False):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("call othercharges_gethorses({}, {})".format(self.supplierId,
                                                                  'NULL' if self.comboAgreements.currentIndex() < 0 else self.comboAgreements.getHiddenData(
                                                                      0)))
            if qry.lastError().type() != 0:
                raise DataError("getHorses", qry.lastError().text())
            if not mode:
                return qry
            self.comboHorses.model().setQuery(qry)
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def setAgreement(self):
        self.comboAgreements.seekData(self.comboHorses.getHiddenData(2), 0)

    @pyqtSlot()
    def resetWidget(self):
        self.lineNumber.clear()
        self.lineConcept.clear()
        self.lineInstallment.clear()
        self.lineIndex.clear()
        self.lineTotal.clear()
        self.dateInvoice.setDate(QDate(99999,89, 78))
        self.comboAgreements.setCurrentIndex(-1)
        self.comboAccount.setCurrentIndex(-1)
        self.comboHorses.setCurrentIndex(-1)
        self.comboCurrency.setCurrentIndex(-1)
        self.comboInvoiceType.setCurrentIndex(-1)

        self.pushSave.setEnabled(False)
        self.pushDelete.setEnabled(False)
        self.pushReset.setEnabled(False)

    def getDates(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL downpayments_getdates({})".format(self.supplierId))
            if qry.lastError().type() != 0:
                raise DataError("Downpayments: getDates", qry.lastError().text())
            if not qry.first():
                raise DataError("Downpayments: getDates ", "There is no data! Check if there is an active agreement "
                                                           " with started horses.")
            return qry
        except DataError as err:
            raise DataError(err.source, err.message)

    def getAgreements(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL othercharges_getagreements({})".format(self.supplierId))
            if qry.lastError().type() != 0:
                raise DataError("OtherCharge: getAgreements", qry.lastError().text())
            if not qry.first():
                raise DataError("OtherCharge: getAgreements ",
                                "There is no data! Check if there is an active agreement.")
            return qry
        except DataError as err:
            raise DataError(err.source, err.message)

