
from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import (QDialog, QMessageBox, QFrame, QCheckBox, QVBoxLayout, QHBoxLayout, QAbstractItemView,
                             QGridLayout, QLabel, QPushButton, QLineEdit,QTextEdit, QDateEdit, QToolButton, QCheckBox)
from PyQt5.QtGui import QDoubleValidator, QIcon, QColor
from PyQt5.QtCore import Qt, QDate, pyqtSlot, QModelIndex
from PyQt5.QtSql import QSqlDatabase, QSqlQueryModel, QSqlQuery, QSql
from ext.APM import (FocusCombo, FocusSpin, TableViewAndModel,PAYABLES_TYPE_OTHER, PAYABLES_TYPE_BOARD,
    PAYABLES_TYPE_SALE, PAYABLES_TYPE_FULL_BREAK, PAYABLES_TYPE_HALF_BREAK, PAYABLES_TYPE_DOWNPAYMENT,
    OPEN_NEW, OPEN_EDIT,DataError, OPEN_DELETE)
from ext import Settings


class Payment(QDialog):
    def __init__(self, db, supplierId, mode, paymentId=None, con_string=None, parent=None, record=None, qry=None):
        super().__init__()
        self.db = db
        if not self.db.isOpen():
            self.db.open()
        if not self.db.contains("Temp"):
            self.tempDb = self.db.cloneDatabase(self.db, "Temp")
            self.tempDb.open()
        else:
            self.tempDb = self.db.database("Temp")
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
        self.lineTransaction.setEnabled(False)

        #self.lblAmount = QLabel('Pay Amount')
        #self.lineAmount = QLineEdit()
        #self.lineAmount.setAlignment(Qt.AlignRight)
        #self.lineAmount.setMaximumWidth(150)
        #self.lineAmount.setValidator(valAmount)
        #self.lineAmount.textChanged.connect(self.enableSave)

        lblAmountToPay = QLabel('Amount to pay')
        self.lineAmountToPay = QLineEdit()
        self.lineAmountToPay.setAlignment(Qt.AlignRight)
        self.lineAmountToPay.setMaximumWidth(150)
        self.lineAmountToPay.setValidator(valAmount)

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
        self.paymentDate.dateChanged.connect(self.enableSave)
        #self.paymentDate.dateChanged.connect(self.updateInvoices)

        lblCurrency = QLabel("Currency")
        self.comboCurrency = FocusCombo(itemList=['USA Dollar', 'Argentine Peso'])
        self.comboCurrency.setMinimumWidth(70)
        currency = self.getCurrency()
        self.comboCurrency.setCurrentIndex(currency) if currency in [0, 1] else self.comboCurrency.setCurrentIndex(0)
        self.comboCurrency.setEnabled(False) if currency in [0, 1] else self.comboCurrency.setEnabled(True)
        self.comboCurrency.setModelColumn(1)
        self.getNumber()
        self.comboCurrency.activated.connect(self.getNumber)
        self.comboCurrency.activated.connect(self.setInvoices)
        self.comboCurrency.activated.connect(self.setCurrency)

        self.setCurrency()

        lblPaymentType = QLabel("Payment Method")
        self.comboPaymentType = FocusCombo(itemList=['Check', 'Transfer', 'Cash'])
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

        self.lblTotalDue = QLabel("Total Amount Due")

        self.lblAmountToPay = QLabel("Amount Selected to Pay")

        pushCancel = QPushButton("Exit")
        pushCancel.setMaximumWidth(70)
        pushCancel.clicked.connect(self.widgetClose)

        self.pushSave = QPushButton("Save")
        self.pushSave.setMaximumWidth(70)
        self.pushSave.setEnabled(False)
        self.pushSave.clicked.connect(self.saveAndClose)

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

        lblNotes = QLabel("Notes")
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
        colDict = {0: ("ID", True, True, False, None),
                   1: ("Date", False, True, False, None),
                   2: ("Number", False, True, False, None),
                   3: ("Provider",True, False,False, None),
                   4: ("Currency", False, True, True, None),
                   5: ("Amount", False, True, 2, None),
                   6: ("Paid", True, True, 2, None),
                   7: ("Closed", True, True, True, None),
                   8: ("Currencyid", True, False, False, None),
                   9: ("Checked", True, True, True, None),
                   10: ("Removed", True, True, False, None)}

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
            colInvDict = {0: ("Id", True, True, False, None),
                          1: ("Date", False, True, False, None),
                          2: ("Bank", False, False, False, None),
                          3: ("Type", False, True, False, None),
                          4: ("Number", False, True, False, None),
                          5: ("Currency", False, True, True, None),
                          6: ("Total", False, True, 2, None),
                          7: ("Local", True, True, 2, None),
                          8: ("paytype", True, True, False, None),
                          9: ("paycurrency", True, True, False, None),
                          10: ("paybank", True, False, False, None),
                          11: ("Notes", True, False, False, None)}
            qryPay = self.getPayments()
            self.tablePayments = TableViewAndModel(colInvDict, colorInvDict, (100, 100), qryPay)
            self.tablePayments.doubleClicked.connect(self.loadPayment)
            self.tablePayments.currentMove.connect(self.cursorMove)

            lblPayments = QLabel("Payments")

            self.pushReset = QPushButton()
            self.pushReset.setIcon(QIcon(":Icons8/Edit/reset.png"))
            self.pushReset.setMaximumWidth(50)
            self.pushReset.setEnabled(False)
            self.pushReset.clicked.connect(self.resetWidget)

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
        toolsLayout.addWidget(self.toolLeft)
        toolsLayout.addWidget(self.toolAllLeft)
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
        paymentLayout.addWidget(self.textNotes)
        paymentLayout.addWidget(payFrame)

        buttonsLayout = QHBoxLayout()
        if self.mode == OPEN_EDIT:
            buttonsLayout.addWidget(self.pushReset)
            buttonsLayout.addWidget(self.pushDelete)
        buttonsLayout.addWidget(pushCancel)
        buttonsLayout.addWidget(self.pushSave)

        #notesLayout = QGridLayout()
        #if self.mode == OPEN_EDIT:
        #    notesLayout.addWidget(lblPayments,0,0,Qt.AlignBottom)
        #    notesLayout.addWidget(self.tablePayments,1,0,Qt.AlignTop)
        #notesLayout.addWidget(lblNotes,0,1,Qt.AlignBottom)
        #"notesLayout.addWidget(self.textNotes,1,1,Qt.AlignTop)

        layout = QVBoxLayout()
        layout.addWidget(topFrame)
        layout.addLayout(centerLayout)
        layout.addLayout(paymentLayout)
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
        qry = QSqlQuery(self.db)
        qry.exec("CALL payment_getcurrency({})".format(self.supplierId))
        if qry.lastError().type() != 0:
            raise DataError("Payment getCurrency", qry.lastError().text())
        if qry.first():
            return qry.value(0)

    @pyqtSlot()
    def clearPayment(self):
        try:
            row = self.tableBilled.currentIndex().row()
            qryLook = self.tableBilled.model().query()
            if not qryLook.seek(row):
                return
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL payment_clearpayment({})".format(qryLook.value(0)))
            if qry.lastError().type() != 0:
                raise DataError("clearPayment", qry.lastError().text())
            if qry.first():
                raise DataError("ClearPayment", qry.value(0) + qry.value(1))
            self.refreshTables()
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print("clearPayment", err.args)

    def getPayments(self):
        try:
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL payment_loadpayments({})".format(self.supplierId))
            if qry.lastError().type() != 0:
                raise DataError("getPayments", qry.lastError().text())
            return qry
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print("getPayments", type(err), err.args)

    @pyqtSlot()
    def setLocalPayment(self):
        if self.lineAmountToPay.text() and self.checkLocal.isChecked():
            self.linePayInPesos.setText("{:.2f}".format(float(self.lineAmountToPay.text()) * float(self.lineExchange.text())))

    def setTemporaryTables(self):
        try:
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL payment_initializeinvoices()")
            if qry.lastError().type() != 0:
                raise DataError("setTemporaryTables(Payment)", qry.lastError().text())
            if qry.first():
                raise DataError("Payment setTemporaryTables", qry.value(0) +' ' + qry.value(1))
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
            qryLoad = QSqlQuery(self.tempDb)
            qryLoad.exec("CALL payment_loadinvoicestopay({}, {})".format(
                self.supplierId, self.comboCurrency.currentIndex()))
            if qryLoad.lastError().type() != 0:
                raise DataError('setInvoices', qryLoad.lastError().text())
            if qryLoad.first():
                raise DataError("setInvoices", qryLoad.value(0), qryLoad.value(1))
            if self.isVisible():
                self.refreshTables()
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def applyPayment(self):
        try:
            if self.tableBilled.model().query().size() < 1: # or not self.lineAmount.text():
                return
            qry = QSqlQuery(self.tempDb)
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
            qry = QSqlQuery(self.tempDb)
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
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL payment_updateamounts()")
            if qry.lastError().type() != 0:
                raise DataError("refreshTables", qry.lastError().text())
            if qry.first():
                symbol = 'U$A' if self.comboCurrency.getHiddenData(0) == 0 else 'AR$'
                self.lblTotalDue.setText("Total Amount Due: {} {:,.2f}".format(symbol, qry.value(0)))
                self.lblAmountToPay.setText("Selected for Payment: {} {:,.2f}".format(symbol, qry.value(1)))
                self.selectedAmount = qry.value(1)
                self.lineAmountToPay.setText(str(qry.value(1)))
                #self.amountToPay = qry.value(2)
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
            qryFrom = QSqlQuery(self.tempDb)
            qryFrom.exec("CALL payment_refreshinvoicefrom()")
            if qryFrom.lastError().type() != 0:
                raise DataError("getQueries -getinvoicefrom", qryFrom.lastError().text())
            qryTo = QSqlQuery(self.tempDb)
            qryTo.exec("CALL payment_refreshinvoiceto()")
            if qryTo.lastError().type() != 0:
                raise DataError("getQueries -getinvoiceto", qryTo.lastError().text())
            return qryFrom, qryTo
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot(int)
    def enableBanks(self, option):
        if option == 2:
            self.comboBank.setCurrentIndex(-1)
            self.comboBank.setEnabled(False)
        else:
            self.comboBank.setEnabled(True)

    @pyqtSlot(int)
    def enableRate(self, state):
        action = True if state == 2 else False
        self.lineExchange.setEnabled(action)
        self.lineExchange.selectAll()
        self.lineExchange.setFocus()
        self.linePayInPesos.setEnabled(action)
        self.setLocalPayment()

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
                self.textNotes.setText(qry.value(11))
                self.checkLocal.setChecked(True) if self.comboCurrency.currentIndex() == 1 \
                    else self.checkLocal.setChecked(False)
                self.lineExchange.setText('1.0') if self.comboCurrency.getHiddenData(0) == 0 else \
                    self.lineExchange.setText(str(qry.value(7)/qry.value(6)))
                self.record = qry.record()
                self.loadEditableInvoices()
                self.pushReset.setEnabled(True)
                self.pushDelete.setEnabled(True)
        except DataError as err:
            print(err.source, err.message)
        except ZeroDivisionError:
            pass
        except Exception as err:
            print("loadPayment", err.args)

    @pyqtSlot()
    def loadEditableInvoices(self):
        try:
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL payment_loadeditableinvoices({})".format(self.record.value(0)))
            if qry.lastError().type() != 0:
                raise DataError("loadeditableinvoices)", qry.lastError().text())
            if qry.first():
                print(qry.value(0))
                #if not qry.value(1) is None:
                #    raise DataError("loadEditableInvoices", qry.value(0) + qry.value(1))
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
            self.comboCurrency.setCurrentIndex(-1)
            self.textNotes.clear()
            self.checkLocal.setChecked(False)
            self.lineExchange.setText('1.0')
            qry = QSqlQuery(self.tempDb)
            qry.exec("Call payment_clearpayments()")
            if qry.lastError().type() != 0:
                raise DataError("resetWidget", qry.lastError().text())
            if qry.first():
                raise DataError("resetWidget", qry.value(0) + ' ' + qry.value(1))
            self.pushReset.setEnabled(False)
            self.pushDelete.setEnabled(False)
            self.refreshTables()
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot(int)
    def cursorMove(self, row):
        self.loadPayment(row)

    @pyqtSlot()
    def enableSave(self):
        try:
            if float(self.lineAmountToPay.text()) == self.amountToPay and \
                self.comboPaymentType.currentIndex() != -1 and \
                (self.comboPaymentType.currentIndex() == 2 or (self.comboPaymentType.currentIndex() != 2 and
                self.comboBank.currentIndex() != -1)) and self.lineNumber.text():
                self.pushSave.setEnabled(True)
                return
            self.pushSave.setEnabled(False)
        except ValueError:
            return

    @pyqtSlot()
    def includePayment(self):
        if self.mode == OPEN_EDIT and self.tableBilled.model().query().size() < 1:
            return
        try:
            row = self.tableCheck.currentIndex().row()
            qryLook = self.tableCheck.model().query()
            if not qryLook.seek(row):
                return
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL payment_includepayment({})".format(qryLook.value(0)))
            if qry.lastError().type() != 0:
                raise DataError("includePayment", qry.lastError().text())
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
            while True:
                qry = QSqlQuery(self.tempDb)
                qry.exec("CALL payment_includeallpayments()")
                if qry.lastError().type() != 0:
                    if qry.lastError().nativeErrorCode() == 2006:
                        continue
                break
                    #raise DataError("includeAllPayments", qry.lastError().text())
            if qry.first():
                print(qry.value(1), qry.value(2))
                    #raise DataError("includeAllPayments", "Error {} {}".format(qry.value(0), qry.value(1)))
            self.refreshTables()
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print("includeAllPayments", type(err), err.args)

    @pyqtSlot()
    def excludePayment(self):
        try:
            qryLook = self.tableBilled.model().query()
            row = self.tableBilled.currentIndex().row()
            if not qryLook.seek(row):
                return
            qry = QSqlQuery(self.tempDb)
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
            qry = QSqlQuery(self.tempDb)
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
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL payment_deletepayment({})".format(self.record.value(0)))
            if qry.lastError().type() != 0:
                raise DataError("deletePayment", qry.lastError().text())
            if qry.first():
                raise DataError("deletePayment", "Error {} {}".format(qry.value(0), qry.value(1)))
            self.refreshTables()
            self.parent.updateAccounts(1)
            self.widgetClose()
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print("deletePayment", type(err), err.args)

    @pyqtSlot()
    def widgetClose(self):
        if self.tempDb.isOpen():
            self.tempDb.close()
        self.done(QDialog.Rejected)

    def saveAndClose(self):
        try:
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL payment_save({}, '{}', '{}', {}, {}, {}, {}, {}, {}, {})".format(
                self.mode,
                self.lineNumber.text(),
                self.paymentDate.date().toString("yyyy-MM-dd"),
                self.comboPaymentType.getHiddenData(0),
                self.supplierId,
                float(self.lineAmountToPay.text()),
                self.comboCurrency.getHiddenData(0),
                " {:.2f}".format(float(self.lineAmountToPay.text()) * float(self.lineExchange.text()) ) \
                    if self.checkLocal.isChecked() else 'NULL',
                self.comboBank.getHiddenData(0) if self.comboBank.currentIndex() != -1 else 'NULL',
                'NULL' if self.mode == OPEN_NEW else 1))
            if qry.lastError().type() != 0:
                raise DataError("saveAndClose", qry.lastError().text())
            if qry.first():
                raise DataError("saveAndClose", "Error {} {}".format(qry.value(0), qry.value(1)))
            self.refreshTables()
            self.parent.updateAccounts(1)
            self.widgetClose()
        except DataError as err:
            print(err.source, err.message)
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
        if not self.db.contains("Temp"):
            self.tempDb = self.db.cloneDatabase(self.db, "Temp")
            self.tempDb.open()
        else:
            self.tempDb = self.db.database("Temp")
        self.record = record
        self.setUI()
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

        billDate, fromDate, toDate = self.getDates() #self.getDates()
        currency = self.getCurrency(billDate.toString("yyyy-MM-dd"))

        lblDate = QLabel('Invoice Date: ')
        self.dateInvoice = QDateEdit()
        self.dateInvoice.setCalendarPopup(True)
        self.dateInvoice.setDate(billDate)
        self.dateInvoice.setDisplayFormat('MM-dd-yyyy')
        self.dateInvoice.setMinimumWidth(120)
        self.dateInvoice.dateChanged.connect(self.enableSave)
        self.dateInvoice.dateChanged.connect(self.setPeriod)
        self.dateInvoice.dateChanged.connect(self.updatePayables)

        lblFrom = QLabel('From: ')
        self.dateFrom = QDateEdit()
        self.dateFrom.setCalendarPopup(True)
        self.dateFrom.setDate(fromDate)
        self.dateFrom.setDisplayFormat('MM-dd-yyyy')
        self.dateFrom.setMinimumWidth(120)

        lblTo = QLabel('To: ')
        self.dateTo = QDateEdit()
        self.dateTo.setCalendarPopup(True)
        self.dateTo.setDate(toDate)
        self.dateTo.setDisplayFormat('MM-dd-yyyy')
        self.dateTo.setMinimumWidth(120)


        lblType = QLabel("Type")
        lblType.setStyleSheet("QLabel {background-color: red; color: white;}")
        lblType.setAlignment(Qt.AlignCenter)

        self.comboType = FocusCombo(itemList=['C', 'A'])
        self.comboType.setMinimumWidth(30)
        self.comboType.setModelColumn(1)
        self.comboType.setCurrentIndex(0)
        self.comboType.activated.connect(self.addIVA)

        lblInvoice = QLabel("Invoice type")
        self.comboInvoiceType = FocusCombo(itemList=['DownPayment', 'Board', 'Full Break', 'Half Break',
                                                     'Sale Sharing', 'Other Charges', 'All Payables'])
        self.comboInvoiceType.setMinimumWidth(70)
        self.comboInvoiceType.setCurrentIndex(self.payableType)
        self.comboInvoiceType.setModelColumn(1)
        self.comboInvoiceType.setEnabled(False)

        lblCurrency = QLabel("Currency")
        self.comboCurrency = FocusCombo(itemList=['USA Dollar', 'Argentine Peso'])
        self.comboCurrency.setMinimumWidth(70)
        self.comboCurrency.setEnabled(False) if currency in [0,1] else self.comboCurrency.setEnable(True)
        self.comboCurrency.setCurrentIndex(currency) if currency in [0,1] else self.comboCurrency.setCurrentIndex(0)
        self.comboCurrency.setModelColumn(1)
        self.comboCurrency.activated.connect(self.updatePayables)

        self.lblIva = QLabel("IVA 21%")
        self.lblIva.hide()
        self.lineIva = QLineEdit()
        self.lineIva.setMaximumWidth(150)
        self.lineIva.setAlignment(Qt.AlignRight)
        self.lineIva.setEnabled(False)
        self.lineIva.hide()
        """
        valExchange = QDoubleValidator(0.00, 999999.99,2)

        lblExchange = QLabel("Exchange Rate")
        self.lineExchange = QLineEdit()
        self.lineExchange.setMaximumWidth(100)
        self.lineExchange.setAlignment(Qt.AlignRight)
        self.lineExchange.setValidator(valExchange)
        self.lineExchange.setText("1.00")
        self.lineExchange.setEnabled(False)
        self.lineExchange.editingFinished.connect(self.refreshTables)
        """
        self.textNotes = QTextEdit()

        colorDict = {'column': (9),
                     0: (QColor('white'), QColor('blue')),
                     1: (QColor('red'), QColor('yellow'))}
        colDict = {0: ("ID", False, True, False, None),
                   1: ("Date", False, True, False, None),
                   2: ("Horse", False, True, False, None),
                   3: ("Concept", False, False, False, None),
                   4: ("Amount", False, True, 2, None),
                   5: ("ticketid", True, True, True, None),
                   6: ("typeid", True ,True, True, None),
                   7: ("ahid", True,True, False, None ),
                   8: ("Checked", True, True, False, None),
                   9: ("Billed", True, True, False, None),
                   10: ("Removed", True, True, False, None)}
        self.setTemporaryTables()
        qryActive, qryBilled = self.getPayables()

        self.tableCheck = TableViewAndModel(colDict=colDict, colorDict=colorDict, size=(100,200), qry=qryActive)
        self.tableCheck.doubleClicked.connect(self.includePayable)
        self.tableCheck.doubleClicked.connect(self.enableSave)

        self.tableBilled = TableViewAndModel(colDict=colDict,colorDict=colorDict, size=(100,200),qry=qryBilled)
        self.tableBilled.doubleClicked.connect(self.excludePayable)
        self.tableBilled.doubleClicked.connect(self.enableSave)

        if self.mode == OPEN_EDIT:
            colorInvDict = {'column': (11),
                         0: (QColor('white'), QColor('black')),
                         1: (QColor('black'), QColor('white'))}
            colInvDict = {0:("Id", True, True, False, None),
                          1:("Number", False,True, False, None),
                          2:("Invoice Date", False,True, False, None),
                          3:("Provider", False, False, False, None),
                          4:("Total", False, True, 2, None),
                          5:("From Date", True, True, False, None),
                          6:("To Date", True, True, False, None),
                          7:("Ex Rate", True, True, False, None),
                          8:("Currency", True, True, False, None),
                          9:("Inv Type", True, False, False, None),
                          10:("Notes", True, False, False, None),
                          11:("Closed", True, False, False, None),
                          12:("Amount", True, True, False, None),
                          13:("IVA $", True, True, False, None),
                          14:("IVA%", True, True, False, None)}
            qryInvoices = self.getInvoices()
            self.tableInvoices = TableViewAndModel(colInvDict, colorInvDict, (100,100),qryInvoices)
            self.tableInvoices.doubleClicked.connect(self.loadInvoice)
            self.tableInvoices.currentMove.connect(self.cursorMove)

            lblInvoices = QLabel("Invoices")

            self.pushReset = QPushButton()
            self.pushReset.setIcon(QIcon(":Icons8/Edit/reset.png"))
            self.pushReset.setMaximumWidth(50)
            self.pushReset.setEnabled(False)
            self.pushReset.clicked.connect(self.resetWidget)

            self.pushDelete = QPushButton("Delete")
            self.pushDelete.setMaximumWidth(70)
            self.pushDelete.setEnabled(False)
            self.pushDelete.clicked.connect(self.deleteInvoice)

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

        invoiceVLayout = QVBoxLayout()
        invoiceLayout_1 = QHBoxLayout()
        invoiceLayout = QHBoxLayout()

        invoiceLayout_1.addWidget(lblSupplier)
        invoiceLayout_1.addWidget(self.lineSupplier)
        invoiceLayout_1.addWidget(lblCurrency)
        invoiceLayout_1.addWidget(self.comboCurrency)
        invoiceLayout_1.addWidget(lblInvoice)
        invoiceLayout_1.addWidget(self.comboInvoiceType)
        invoiceLayout_1.addWidget(lblType)
        invoiceLayout_1.addWidget(self.comboType)
        invoiceLayout_1.addWidget(lblNumber)
        invoiceLayout_1.addWidget(self.lineNumber)

        invoiceLayout.addWidget(lblDate, 0, Qt.AlignLeft)
        invoiceLayout.addWidget(self.dateInvoice,0,Qt.AlignLeft )

        invoiceLayout.addWidget(lblFrom, 0, Qt.AlignRight)
        invoiceLayout.addWidget(self.dateFrom,0 ,Qt.AlignLeft)
        invoiceLayout.addWidget(lblTo,0, Qt.AlignRight)
        invoiceLayout.addWidget(self.dateTo, 0, Qt.AlignLeft)

        invoiceVLayout.addLayout(invoiceLayout_1)
        invoiceVLayout.addLayout(invoiceLayout)

        topLayout = QGridLayout()
        topLayout.addWidget(lblSupplier,0,0,Qt.AlignLeft)
        topLayout.addWidget(self.lineSupplier,0,1,Qt.AlignLeft)
        topLayout.addWidget(lblInvoice,0,2,Qt.AlignLeft)
        topLayout.addWidget(self.comboInvoiceType,0,3, Qt.AlignLeft)
        topLayout.addWidget(lblCurrency,0,4, Qt.AlignLeft)
        topLayout.addWidget(self.comboCurrency, 0, 5, Qt.AlignLeft)
        topLayout.addWidget(lblNumber,0,6, Qt.AlignRight)
        topLayout.addWidget(self.lineNumber,0,7,Qt.AlignRight)

        topLayout.addWidget(lblDate, 1, 0, Qt.AlignLeft)
        topLayout.addWidget(self.dateInvoice, 1, 1, Qt.AlignLeft)
        topLayout.addWidget(lblFrom, 1, 2, Qt.AlignLeft)
        topLayout.addWidget(self.dateFrom, 1, 3, Qt.AlignLeft)
        topLayout.addWidget(lblTo, 1, 4, Qt.AlignLeft)
        topLayout.addWidget(self.dateTo, 1, 5, Qt.AlignLeft)
        topLayout.addWidget(lblType, 1, 6, Qt.AlignRight)
        topLayout.addWidget(self.comboType, 1, 7, Qt.AlignRight)



        topFrame.setLayout(topLayout)

        lblDue = QLabel("Payables Due")
        lblChoose = QLabel("Selected Charges")
        tablesLayout = QGridLayout()
        tablesLayout.addWidget(lblDue, 0, 0)
        tablesLayout.addWidget(lblChoose, 0, 1)
        tablesLayout.addWidget(self.tableCheck,1,0)
        tablesLayout.addWidget(self.tableBilled,1,1)

        totalLayout = QGridLayout()

        totalLayout.addWidget(self.lblSpinIva, 0, 0, Qt.AlignLeft)
        totalLayout.addWidget(self.spinIva, 0, 3, Qt.AlignLeft)
        totalLayout.addWidget(self.lblTotal,0,4, Qt.AlignLeft)
        totalLayout.addWidget(self.lineTotal,0,5,Qt.AlignRight)

        totalLayout.addWidget(self.lblIva,1,4, Qt.AlignLeft)
        totalLayout.addWidget(self.lineIva,1,5, Qt.AlignRight)
        totalLayout.addWidget(self.lblGrandTotal,2,4, Qt.AlignLeft)
        totalLayout.addWidget(self.lineGrandTotal,2,5, Qt.AlignRight)
        #totalLayout.addWidget(self.lblCurrencyTotal, 3, 4, Qt.AlignLeft)
        #totalLayout.addWidget(self.lineCurrencyTotal, 3, 5, Qt.AlignRight)

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

        self.textNotes.setText("Notes: ")
        buttonLayout = QHBoxLayout()
        if self.mode == OPEN_EDIT:
            buttonLayout.addWidget(self.pushReset)
            buttonLayout.addWidget(self.pushDelete)
        buttonLayout.addWidget(pushCancel)
        buttonLayout.addWidget(self.pushSave)

        layout = QVBoxLayout()
        layout.addWidget(topFrame)
        layout.addLayout(tablesLayout)
        layout.addLayout(middleLayout)
        if self.mode == OPEN_EDIT:
            layout.addWidget(self.textNotes)
        layout.addLayout(buttonLayout)

        self.setLayout(layout)

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
            if record is None and (idx is not None or row is not None):
                if idx is not None:
                    row = idx.row()
                qry = self.tableInvoices.model().query()
                if qry.seek(row):
                    if qry.value(11):
                        QMessageBox.information(self,"Invoice Closed", "The invoice {} dated {} is paid.".format(
                            qry.value(1), qry.value(2).toString("MM-dd-yyyy")),QMessageBox.OK)
                        return
                    record = qry.record()

            self.lineNumber.setText(record.value(1))
            self.dateInvoice.setDate(record.value(2))
            self.lineGrandTotal.setText(str(record.value(4)))
            self.dateFrom.setDate(record.value(5))
            self.dateTo.setDate(record.value(6))
            #self.lineExchange.setText(str(record.value(7)))
            self.comboCurrency.setCurrentIndex(record.value(8))
            self.comboType.setCurrentIndex(record.value(9))
            self.textNotes.setText(record.value(10))
            self.lineTotal.setText(str(record.value(12)))
            self.lineIva.setText(str(record.value(13)))
            self.spinIva.setValue(record.value(14) * 100)
            self.addIVA(record.value(9))

            qryEdit = QSqlQuery(self.tempDb)
            qryEdit.exec("CALL invoice_loadeditable({}, {})".format(self.supplierId, record.value(0)))
            if qryEdit.lastError().type() != 0:
                raise DataError("loadInvoice", qryEdit.lastError().text())
            self.refreshTables()
            if idx is not None or row is not None:
                self.pushReset.setEnabled(True)
                self.pushDelete.setEnabled(True)
            else:
                self.pushSave.setEnabled(False)
            self.record = record
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print("loadInvoice", err.args)

    def getInvoices(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL invoice_getinvoices({})".format(self.supplierId))
            if qry.lastError().type() != 0:
                raise DataError("getInvoices", qry.lastError().text())
            return qry
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def getDates(self, invDate=None):
        try:
            invDate = 'NULL' if invDate is None else "'" + invDate.toString("yyyy-MM-dd") + "'"
            if self.mode == OPEN_NEW:
                qryOld = QSqlQuery(self.db)
                qryOld.exec("CALL invoice_getduepayables({}, {})".format(self.supplierId, invDate))
                if qryOld.lastError().type() != 0:
                    raise DataError("getDates - PastDue", qryOld.lastError().text())
                if qryOld.first():
                    if not qryOld.value(0).isNull():
                        if QMessageBox.question(self, 'Past Due Invoices', "There are pending charges from {}. Do you "
                                                                    "want to bill them?".format(qryOld.value(1)),
                                         QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
                            invDate = "'" + qryOld.value(0).toString("yyyy-MM-dd") + "'"
            qry = QSqlQuery(self.db)
            qry.exec("CALL invoice_getdates({},{})".format(self.supplierId, invDate))
            if qry.lastError().type() != 0:
                raise DataError("getDates", qry.lastError().text())
            if qry.first():
                return qry.value(0), qry.value(1), qry.value(2)
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print("getDates", err.args)

    def getCurrency(self, invDate):
        qry = QSqlQuery(self.db)
        qry.exec("CALL invoice_currency({}, '{}')".format(self.supplierId, invDate))
        if qry.first():
            return qry.value(0)
        raise Exception("getCurrency " + qry.lastError().text())


    @pyqtSlot()
    def setPeriod(self):
        if self.isVisible() :
            invDate, fromDate, toDate = self.getDates(self.dateInvoice.date())
            self.dateTo.setDate(toDate)
            self.dateFrom.setDate(fromDate)

    @pyqtSlot()
    def enableSave(self):
        if not self.lineNumber.text() or \
            not self.lineTotal.text():
            return
        #if self.lineCurrencyTotal.isEnabled():
        #    if not self.lineCurrencyTotal.text():
        #        return
        self.pushSave.setEnabled(True)

    @pyqtSlot()
    def resetWidget(self):
        self.lineExchange.clear()
        self.lineTotal.clear()
        self.lineNumber.clear()
        self.lineTotal.clear()
        self.lineCurrencyTotal.clear()
        self.lineGrandTotal.clear()
        self.comboCurrency.setCurrentIndex(-1)
        self.comboType.setCurrentIndex(-1)
        self.textNotes.setText("Notes: ")
        if self.mode == OPEN_EDIT:
            self.pushReset.setEnabled(False)
            self.pushDelete.setEnabled(False)

    @pyqtSlot()
    def widgetClose(self):
        if self.tempDb.isOpen():
            self.tempDb.close()
        #self.tempDb.removeDatabase("Temp")
        self.done(QDialog.Rejected)

    def setTemporaryTables(self):
        try:
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL invoice_initializepayables()")
            if qry.lastError().type() != 0:
                raise DataError("setTemporaryTebles", qry.lastError().text())
        except DataError as err:
            print(err.source, err.message)

    def getPayables(self):
        try:
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL invoice_loadpayables({}, '{}', '{}', {}, {})".format(self.supplierId,
                                                                        self.dateFrom.date().toString("yyyy-MM-dd"),
                                                                        self.dateTo.date().toString("yyyy-MM-dd"),
                                                                        self.payableType,
                                                                        self.comboCurrency.currentIndex()))
            if qry.lastError().type() != 0:
                raise DataError("getPayables", qry.lastError().text())
            qryBill = QSqlQuery(self.tempDb)
            qryBill.exec("CALL invoice_loadbasetobill()")
            if qryBill.lastError().type() != 0:
                raise DataError("getPayables", qryBill.lastError().text())
            return qry, qryBill
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def updatePayables(self):
        try:
            qryCheck, qryBilled = self.getPayables()
            self.tableCheck.model().setQuery(qryCheck)
            self.tableBilled.model().setQuery(qryBilled)
        except Exception as err:
            print('updatePayables', err.args)

    def refreshTables(self):
        try:
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL invoice_refreshpayablefrom()")
            if qry.lastError().type() != 0:
                raise DataError("refreshTables -check", qry.lastError().text())
            self.tableCheck.model().setQuery(qry)
            qryTo = QSqlQuery(self.tempDb)
            qryTo.exec("CALL invoice_refreshpayableto()")
            if qryTo.lastError().type() != 0:
                raise DataError("refreshTables -billed", qryTo.lastError().text())
            self.tableBilled.model().setQuery(qryTo)
            if not qryTo.first():
                totalAmount = 0
                totalAmountSelected = 0
            else:
                totalAmount = qryTo.value(4)
                totalAmountSelected = qryTo.value(5)
                while qryTo.next():
                    totalAmount += qryTo.value(4)
                    totalAmountSelected += qryTo.value(5)
            self.lineTotal.setText('{:.2f}'.format(round(totalAmount,2)))
            self.lineGrandTotal.setText(self.lineTotal.text())
            if int(self.comboType.getHiddenData(0)) !=0 or int(self.comboCurrency.getHiddenData(0)) != 0:
                self.refreshTotals()
            self.refreshTotals()
            self.tableBilled.hideColumn(10)
            if self.mode == OPEN_EDIT:
                self.pushReset.setEnabled(False)
                self.pushDelete.setEnabled(False)
        except DataError as err:
            print(err.source, err.message)

    def getInvoiceNumber(self):
        qry = QSqlQuery(self.db)
        qry.exec("CALL invoice_getnumber({})".format(self.supplierId))
        if qry.first():
            return qry.value(0)

    def refreshTotals(self):
        try:
            if not self.isVisible():
                return
            amount = float(self.lineTotal.text())
            iva = 0.01 * self.spinIva.value()

            if int(self.comboType.getHiddenData(0)) == 0:
                self.lineIva.clear()
                self.lineGrandTotal.setText(self.lineTotal.text())
            if int(self.comboType.getHiddenData(0)) == 1:
                self.lblIva.setText("IVA " + str(self.spinIva.value()) + "%")
                self.lineIva.setText('{:.2f}'.format(amount * iva))
                self.lineGrandTotal.setText('{:.2f}'.format(amount * 1.21))
                # self.lineCurrencyTotal.setText('{:.2f}'.format(float(self.lineGrandTotal.text()
        except ValueError:
            return
        except Exception as err:
            print("refreshTotals", err.args)

    @pyqtSlot()
    def includePayable(self):
        try:
            qry = self.tableCheck.model().query()
            row = self.tableCheck.currentIndex().row()
            qry.seek(row)
            qryInsert = QSqlQuery(self.tempDb)
            qryInsert.exec("""CALL invoice_includepayable({},{})""".format(
                qry.value(0),
                self.mode))
            if qryInsert.lastError().type() != 0:
                raise DataError("includePAYABLE -Insert", qryInsert.lastError().text())
            self.refreshTables()
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print("includePayable", err.args)

    @pyqtSlot()
    def excludePayable(self):
        try:
            qryBilled = self.tableBilled.model().query()
            row = self.tableBilled.currentIndex().row()
            qryBilled.seek(row)
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL invoice_excludepayable({}, {})".format(qryBilled.value(0), self.mode))
            if qry.lastError().type() != 0:
                raise DataError("excludePayable -Deletete", qry.lastError().text())
            self.refreshTables()
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot(int)
    def addIVA(self):
        try:
            if int(self.comboType.getHiddenData(0)) == 1:
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
                self.lblTotal.setText("Subtotal")
            self.refreshTotals()
        except ValueError:
            return
        except Exception as err:
            print('addIVA', err.args)


        """
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
        """
    @pyqtSlot()
    def saveAndClose(self):
        if self.mode == OPEN_EDIT:
            self.editPayable()
            return
        try:
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL invoice_save({}, '{}','{}', '{}', '{}', '{}',{}, {}, '{}','{}',{}, {})".format(
                self.supplierId,
                self.lineNumber.text(),
                self.dateFrom.date().toString("yyyy-MM-dd"),
                self.dateTo.date().toString("yyyy-MM-dd"),
                self.dateInvoice.date().toString("yyyy-MM-dd"),
                self.lineGrandTotal.text(),
                self.comboCurrency.getHiddenData(0),
                self.comboType.getHiddenData(0),
                self.textNotes.toPlainText(),
                self.lineTotal.text(),
                "'" + self.lineIva.text() + "'" if self.lineIva.isVisible() else 'NULL',
                "'" + str(self.spinIva.value() * 0.01) + "'" if self.comboType.currentIndex() == 1 else 'NULL'))
            if qry.lastError().type() != 0:
                raise DataError("saveAndClose", qry.lastError().text())
            if qry.first():
                print(qry.value(0), ' ' ,qry.value(1))
                raise DataError(" Invoice Save and Close", qry.value(0) + ' ' + qry.value(1))
            self.refreshTables()
            self.parent.refreshInvoicesTable()
            self.widgetClose()
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print('saveAndClose', err.args)

    def editPayable(self):
        try:
            qry = QSqlQuery(self.tempDb)
            qry.exec("""CALL invoice_saveeditinvoice({},'{}','{}', '{}', '{}', 
                     '{}', '{}',{}, {}, '{}','{}',{}, '{}', {})""".format(
                self.supplierId,
                self.lineNumber.text(),
                self.dateFrom.date().toString("yyyy-MM-dd"),
                self.dateTo.date().toString("yyyy-MM-dd"),
                self.dateInvoice.date().toString("yyyy-MM-dd"),
                self.lineGrandTotal.text(),
                self.lineExchange.text(),
                self.comboCurrency.getHiddenData(0),
                self.comboType.getHiddenData(0),
                self.textNotes.toPlainText(),
                self.lineTotal.text(),
                "'" + self.lineIva.text() + "'" if self.lineIva.text().isnumeric() else 'NULL',
                self.spinIva.value() * 0.01,
                self.record.value(0)))
            if qry.lastError().type() != 0:
                raise DataError("saveAndClose", qry.lastError().text())
            if qry.size() == 0:
                QMessageBox.question(self, "Empty Invoice", "Invoice {} is empty. Do you want to delete ir?".format(
                    self.lineNumber.text()), QMessageBox.Yes|QMessageBox.No)
                if QMessageBox.Yes:
                    self.deleteInvoice()
            if qry.first():
                print(qry.value(0))
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
                raise DataError("DeleteInvoice", qry.lastError().text())
            if qry.first():
                print(qry.value(0))
            self.refreshTables()
            self.tableInvoices.model().setQuery(self.getInvoices())
            self.widgetClose()
        except DataError as err:
            print(err.source, err.message)




class Payables(QDialog):

    def __init__(self, db, supplierId, payableType, mode=None, con_string=None,
                 parent=None):
        super().__init__()
        self.db = db
        if not self.db.isOpen():
            self.db.open()
        self.record = None
        self.con_string = con_string
        self.mode = mode
        self.parent = parent
        self.payableType = payableType
        self.supplierId = supplierId
        if not self.db.contains("Temp"):
            self.tempDb = self.db.cloneDatabase(self.db, "Temp")
            self.tempDb.open()
        else:
            self.tempDb = self.db.database("Temp")
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
        self.lineNumber.setText(self.getNumber())
        self.lineNumber.editingFinished.connect(self.enableSave)

        self.lblTotal = QLabel('Total Amount:')
        self.lblTotal.setAlignment(Qt.AlignRight)
        self.lineTotal = QLineEdit()
        self.lineTotal.setAlignment(Qt.AlignRight)
        self.lineTotal.setMaximumWidth(150)
        self.lineTotal.setEnabled(False)
        self.lineTotal.editingFinished.connect(self.enableSave)

        billdate = self.getDates()
        if billdate is not None:
            billdate = billdate.addMonths(1)
            fromdate = billdate.addMonths(-1)
            todate = fromdate.addDays(fromdate.daysInMonth()-1)

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
        self.comboCurrency.setCurrentIndex(-1)#(self.getCurrency())
        self.comboCurrency.setModelColumn(1)
        self.comboCurrency.activated.connect(self.getHorses)

        lblInvoice = QLabel("Payable for: ")
        self.comboInvoiceType = FocusCombo(itemList=['DownPayment', 'Board', 'Half Break', 'Final Break', 'Sale Share'])
        self.comboInvoiceType.setMinimumWidth(70)
        self.comboInvoiceType.setCurrentIndex(self.payableType)
        self.comboInvoiceType.setModelColumn(1)
        self.comboInvoiceType.setEnabled(False)

        self.checkLocation = QCheckBox("Disable Location Check")

        lblNotes = QLabel("Notes")
        self.textNotes = QTextEdit()
        self.textNotes.setMaximumHeight(100)

        lblCharges = QLabel("Charges Billed")

        colorDict = {}
        colDict = {0: ("ID", True, True, False, None),
                   1: ("Horse", False, False, False, None),
                   2: ("#", False, True, True, None),
                   3: ("DOS", False, True, True, None),
                   4: ("Days", False, True, True, None),
                   5: ("Installment", False, True, 2, None),
                   6: ("Total", True, True, False, None),
                   7:("Payableid", True, True, False, None),
                   8:("Currency", True, True, False, None)}
        qry, qryBilled = self.getHorses()
        self.tableCheck = TableViewAndModel(colDict=colDict, colorDict=colorDict, size=(100, 200), qry=qry)
        self.tableCheck.doubleClicked.connect(self.includeExcludeHorses)
        self.tableCheck.setObjectName('tablecheck')
        self.tableCheck.doubleClicked.connect(self.enableSave)

        colBilled = {0: ("agreementhorseid", True, True, False, None),
                     1: ("Horse", False, True, False, None),
                     2: ("Concept", False, False, False, None),
                     3: ("Amount", False, True, 2, None),
                     4:("Payableid", True, True, False, 0),
                     5:("Currency", True, True, False, None)}

        self.tableBilled = TableViewAndModel(colDict=colBilled, colorDict=colorDict, size=(100, 200), qry=qryBilled)
        self.tableBilled.doubleClicked.connect(self.includeExcludeHorses)
        self.tableBilled.doubleClicked.connect(self.enableSave)
        self.tableBilled.setObjectName('tableBilled')

        pushCancel = QPushButton("Exit")
        pushCancel.setMaximumWidth(70)
        pushCancel.clicked.connect(self.widgetClose)

        self.pushSave = QPushButton("Save")
        self.pushSave.setMaximumWidth(70)
        self.pushSave.setEnabled(False)
        self.pushSave.clicked.connect(self.saveAndClose)

        if self.mode != OPEN_NEW:

            self.pushReset = QPushButton()
            self.pushReset.setIcon(QIcon(":Icons8/Edit/reset.png"))
            self.pushReset.setMaximumWidth(50)
            self.pushReset.setEnabled(False)
            self.pushReset.clicked.connect(self.resetWidget)

            self.pushDelete = QPushButton("Delete")
            self.pushDelete.setMaximumWidth(70)
            self.pushDelete.setEnabled(False)
            self.pushDelete.clicked.connect(self.deleteCharge)

            qryBoards = self.getBoardsOrDownpayment()

            colorBoards = {'column': (6),
                         True: (QColor('red'), QColor('yellow')),
                         False: (QColor('white'), QColor('black'))}

            colBoards = {0:("ID", True, True, False, None),
                         1: ("Date", False, True, False, None),
                         2:("#", False, False, False, None),
                         3:("From", False, True, False, None),
                         4:("To", False, True, False, None),
                         5:("Amount", False, True,2, None),
                         6:("Billed", True, True, False, None)}

            self.tableBoards = TableViewAndModel(colBoards, colorBoards,(100,100), qryBoards)


            self.tableBoards.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.tableBoards.setSelectionMode(QAbstractItemView.SingleSelection)
            self.tableBoards.doubleClicked.connect(lambda: self.loadBoard(self.payableType))

        invoiceVLayout = QVBoxLayout()
        invoiceLayout_1 = QHBoxLayout()
        invoiceLayout = QHBoxLayout()

        invoiceLayout_1.addWidget(lblSupplier)
        invoiceLayout_1.addWidget(self.lineSupplier)
        invoiceLayout_1.addWidget(lblCurrency)
        invoiceLayout_1.addWidget(self.comboCurrency)
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
        if self.mode != OPEN_NEW:
            buttonLayout.addWidget(self.pushReset)
            buttonLayout.addWidget(self.pushDelete)
        buttonLayout.addWidget(pushCancel)
        buttonLayout.addWidget(self.pushSave)

        editLayout = QGridLayout()
        if self.mode != OPEN_EDIT:
            editLayout.addWidget(lblNotes,0,0,Qt.AlignLeft)
            editLayout.addWidget(self.textNotes,1,0,4, Qt.AlignLeft)
        else:
            editLayout.addWidget(lblCharges, 0,0,Qt.AlignLeft)
            editLayout.addWidget(lblNotes,0,1,Qt.AlignLeft)
            editLayout.addWidget(self.tableBoards,1,0,2, Qt.AlignLeft)
            editLayout.addWidget(self.textNotes,1,1,2,Qt.AlignLeft)
            self.textNotes.setMaximumHeight(self.tableBoards.height())

        layout = QVBoxLayout()
        layout.addWidget(topFrame)
        layout.addLayout(tablesLayout)
        layout.addWidget(totalFrame)
        #layout.addWidget(lblNotes)
        layout.addLayout(editLayout)
        layout.addLayout(buttonLayout)

        self.setLayout(layout)
        self.checkLocation.setVisible(True) if self.payableType == PAYABLES_TYPE_BOARD else \
            self.checkLocation.setVisible(False)

    def getNumber(self):
        qry = QSqlQuery(self.db)
        qry.exec("CALL payables_getticketnumber({})".format(self.supplierId))
        if qry.lastError().type() != 0:
            raise DataError("getNumber", qry.lastError().text())
        if qry.first():
            return qry.value(0)

    def getCurrency(self):
        us = ar = None
        qryus = QSqlQuery(self.tempDb)
        qryar = QSqlQuery(self.tempDb)
        qryus.exec("SELECT currency FROM billablehorses WHERE currency = 0")
        if qryus.first():
            us = qryus.value(0)
        qryar.exec("SELECT currency FROM billablehorses WHERE currency = 1")
        if qryar.first():
            ar = qryar.value(0)
        if us is not None and ar is not None:
            ans = QMessageBox.question(self, "Currency", "There are charges in us dollars and in argentine pesos. "
                                                   "Process us dollar charges?", QMessageBox.Ok|QMessageBox.No)
            if ans == QMessageBox.Yes:
                self.comboCurrency.setCurrentIndex(0)
                return
            else:
                self.comboCurrency.setCurrentIndex(1)
                return
        elif us is not None:
            self.comboCurrency.setCurrentIndex(0)
        elif ar is not None:
            self.comboCurrency.setCurrentIndex(1)
        else:
            QMessageBox.warning(self, "Charges", "Currently there are not charges to enter!", QMessageBox.Ok)
        self.comboCurrency.setEnabled(False)


    @pyqtSlot()
    def getDates(self, invDate=None):
        try:
            invDate = 'NULL' if invDate is None else invDate
            qry = QSqlQuery(self.db)
            qry.exec("CALL system_minimumsupplierdate({})".format(self.supplierId))
            if qry.lastError().type() != 0:
                raise DataError("getDates", qry.lastError().text())
            if qry.first():
                return qry.value(0)
        except DataError as err:
            print(err.source, err.message)

    def getBoardsOrDownpayment(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL payables_getboardsordownpayment({},{})".format(self.supplierId,
                                                                           self.payableType))
            if qry.lastError().type() != 0:
                raise DataError("getBoardsOrDownpayment", qry.lastError().text())
            return qry
        except DataError as err:
            print(err.source, err.message)

    def getLastBoardDate(self):
        try:
            qry = QSqlQuery( self.db)
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

    @pyqtSlot()
    def loadBoard(self, type):
        try:
            qryBoards = self.tableBoards.model().query()
            row = self.tableBoards.currentIndex().row()
            qryBoards.seek(row)
            self.record = qryBoards.record()
            if self.record.value(6):
                ans = QMessageBox.warning(self, "Billed Charge",
                                          "This charge is already billed",
                                          QMessageBox.Ok)
                return
            self.lineNumber.setText(self.record.value(2))
            self.dateInvoice.setDate(self.record.value(1))
            self.dateFrom.setDate(self.record.value(3)) if self.payableType == 1 else self.dateFrom.hide()
            self.dateTo.setDate(self.record.value(4)) if self.payableType == 1 else self.dateTo.hide()
            self.lineTotal.setText(str(self.record.value(5)))
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL payables_getedithorses({},{}, {}, @res)".format(self.record.value(0),
                                                                      self.payableType,
                                                                       self.mode))
            if qry.lastError().type() != 0:
                raise DataError("getBoard", qry.lastError().text())
            if qry.size() > 0 :
                qry.first()
                print(qry.value(0), qry.value(1), qry.value(2))
            self.pushDelete.setEnabled(True)
            self.pushReset.setEnabled(True)
            self.refreshTables()

        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print("getBoard", err.args)

    @pyqtSlot()
    def deleteCharge(self):
        try:
            ans = QMessageBox.question(self,"Warning", "You're about to delete the current record. Confirm (Y/N)",
                                       QMessageBox.Yes|QMessageBox.No)
            if ans == QMessageBox.No:
                return
            qry = QSqlQuery(self.tempDb)
            qry.exec('CALL payables_delete({}, {})'.format(self.record.value(0),self.payableType))
            if qry.lastError().type() != 0:
                raise DataError("deleteCharge", qry.lastError().text())
            if qry.first():
                print(qry.value(0))
            self.refreshTables()
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print('deleteCharge', err.args)

    @pyqtSlot()
    def updateElegibleHorses(self):
        qry, qryBilled = self.getHorses()
        self.tableCheck.model().setQuery(qry)
        self.tableBilled.model().setQuery(qryBilled)

    @pyqtSlot()
    def setPeriod(self):
        #self.dateInvoice.setDate(self.dateInvoice.date().addDays(-self.dateInvoice.date().day()+1))
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
                self.lastDate = self.dateFrom.date()
                if not self.checkLocation.isChecked():
                    qry.prepare("""INSERT INTO billablehorses 
                    (id, horse, agrid, dos, months, installment, totalamount, payableid, currency)
                    SELECT DISTINCT
                    ah.id, h.name, a.id,
                    ah.dos,
                    TIMESTAMPDIFF(MONTH, ah.dos, ?) Months, 
                    IF (a.installments = 0 ,ROUND(a.totalamount - a.downpayment) ,
                        ROUND((a.totalamount - a.downpayment)/ a.installments, 2)),
                    a.totalamount,
                    NULL,
                    a.currency
                    FROM horses h
                    INNER JOIN agreementhorses ah
                    ON h.id = ah.horseid
                    INNER JOIN agreements a
                    ON ah.agreementid = a.id
                    INNER JOIN locations l
                    ON h.locationid = l.id
                    WHERE
                    ah.billable
                    AND ah.dos IS NOT NULL
                    AND (a.paymentoption = 1
                        OR (a.paymentoption = 2 AND (h.locationid IN (SELECT id FROM locations WHERE contactid = ?)
                                                OR (h.locationid IN (SELECT id FROM LOCATIONS WHERE contactid = 0)
                                                    AND EXISTS (SELECT t.id FROM transfers t 
                                                                INNER JOIN transferdetail td 
                                                                ON t.id = td.transferid
                                                                WHERE td.agreementhorseid = ah.id
                                                                AND toid = h.locationid 
                                                                AND t.date BETWEEN ? AND ?))))) 
                    AND a.totalamount > (SELECT COALESCE(SUM(amount),0) FROM payables 
                                            WHERE agreementhorseid = ah.id)
                    AND a.supplierid = ? """)
                    qry.addBindValue(QVariant(self.dateInvoice.date().toString("yyyy-MM-dd")))
                    qry.addBindValue(QVariant(self.supplierId))
                    qry.addBindValue(QVariant(self.dateFrom.date().toString("yyyy-MM-dd")))
                    qry.addBindValue(QVariant(self.dateTo.date().toString("yyyy-MM-dd")))
                    qry.addBindValue(QVariant(self.supplierId))
                else: #Option to disable location checking checked
                    qry.prepare("""INSERT INTO billablehorses 
                                        (id, horse, agrid, dos, months, installment, totalamount, payableid, currency)
                    SELECT DISTINCT
                    ah.id, h.name, a.id,
                    ah.dos,
                    TIMESTAMPDIFF(MONTH, ah.dos, ?) Months, 
                    ROUND((a.totalamount - a.downpayment)/ a.installments, 2) inst,
                    a.totalamount,
                    NULL,
                    a.currency
                    FROM horses h
                    INNER JOIN agreementhorses ah
                    ON h.id = ah.horseid
                    INNER JOIN agreements a
                    ON ah.agreementid = a.id
                    WHERE
                    ah.billable
                    AND ah.dos IS NOT NULL
                    AND (a.paymentoption = 1 OR a.paymentoption = 2)
                    AND a.totalamount > (SELECT COALESCE(SUM(amount), 0) FROM payables WHERE agreementhorseid = ah.id)
                    AND a.supplierid = ? """)
                    qry.bindValue(0, QVariant(self.dateInvoice.date().toString("yyyy-MM-dd")))
                    qry.bindValue(1, QVariant(self.supplierId))
                qry.exec()
                if qry.lastError().type() != 0:
                    raise DataError("getHorses -Board", qry.lastError().text())
            elif self.payableType == PAYABLES_TYPE_DOWNPAYMENT:
                qry.prepare("""INSERT INTO billablehorses 
                                    (id, horse, agrid, dos, months, installment,
                                     totalamount, payableid, currency)
                                    SELECT 
                                    ah.id, h.name, a.id,
                                    ah.dos,
                                    TIMESTAMPDIFF(DAY, a.date, ?) ,
                                    a.downpayment ,
                                    a.totalamount,
                                    NULL,
                                    a.currency
                                    FROM horses h 
                                    INNER JOIN agreementhorses ah
                                    ON h.id = ah.horseid
                                    INNER JOIN agreements a
                                    ON ah.agreementid = a.id
                                    WHERE ah.billable
                                    AND a.downpayment > (SELECT COALESCE(SUM(amount),0) FROM payables WHERE agreementhorseid = ah.id
                                                         AND typeid = 0)
                                    AND a.supplierid = ? """)
                qry.addBindValue(QVariant(self.dateInvoice.date().toString("yyyy-MM-dd")))
                qry.addBindValue(QVariant(self.supplierId))
                qry.exec()
                if qry.lastError().type() != 0:
                    raise DataError("getHorses -Downpayment", qry.lastError().text())
            if self.comboCurrency.currentIndex() == -1:
                self.getCurrency()
            qryDisplay = QSqlQuery(self.tempDb)
            qryDisplay.prepare("""SELECT id, horse, agrid, dos,
                 months, installment, totalamount, payableid, currency
                                   FROM billablehorses 
                                   WHERE NOT billed
                                   AND currency = ?
                                   ORDER BY agrid, horse""")
            qryDisplay.addBindValue(QVariant(self.comboCurrency.currentIndex()))
            qryDisplay.exec()
            qryBilled = QSqlQuery(self.tempDb)
            qryBilled.exec("""SELECT id, horse, description, amount, payableid, currency FROM billed""")
            return qryDisplay, qryBilled
        except DataError as err:
            print(err.source, err.message)

    def createTemporaryTables(self):
        try:
            qry = QSqlQuery(self.tempDb)
            qry.exec("CALL payables_createtemporarytables ({})".format(self.mode))
            if qry.lastError().type() != 0:
                raise DataError("createTemporaryTable -edittable", qry.lastError().text())
            if qry.first():
                raise DataError("createTemporaryTable -edittable", qry.value(0))
        except DataError as err:
            print(err.source, err.message)

            # qry.exec("""CREATE TEMPORARY TABLE IF NOT EXISTS billablehorses (
            #     id TINYINT(5) UNSIGNED NOT NULL,
            #     horse VARCHAR(45) NOT NULL,
            #     agrid TINYINT(5) NOT NULL,
            #     dos DATE NULL,
            #     months SMALLINT(5) NOT NULL,
            #     installment DECIMAL(10,2) NOT NULL DEFAULT 0,
            #     totalamount DECIMAL(10,2) NOT NULL DEFAULT 0,
            #     billed TINYINT(1) NOT NULL DEFAULT 0,
            #     payableid SMALLINT(5) DEFAULT NULL,
            #     currency SMALLINT(1) NOT NULL,
            #     PRIMARY KEY (id))""")
            # if qry.lastError().type() != 0:
            #     raise DataError("createTemporaryTable -billablehorses", qry.lastError().text())
            # qry.clear()
            # qry.exec("""CREATE TEMPORARY TABLE IF NOT EXISTS billed
            #     (id TINYINT(5) NOT NULL,
            #     horse VARCHAR(45) NOT NULL,
            #     description VARCHAR(100) NOT NULL,
            #     amount DECIMAL(7,2) NOT NULL,
            #     payableid SMALLINT(5) DEFAULT NULL,
            #     currency SMALLINT(1) NOT NULL,
            #     PRIMARY KEY (id))""")
            # if qry.lastError().type() != 0:
            #     raise DataError("createTemporaryTable -billed", qry.lastError().text())
            # qry.clear()
            # if self.mode == OPEN_EDIT:
            #     qry.exec("""CREATE TEMPORARY TABLE IF NOT EXISTS edittable
            #     (id TINYINT(5) NOT NULL,
            #     horse VARCHAR(45) NOT NULL,
            #     description VARCHAR(100) NOT NULL,
            #     amount DECIMAL(7,2) NOT NULL,
            #     payableid SMALLINT(5) DEFAULT NULL,
            #     actioninout TINYINT(1) DEFAULT NULL,
            #     PRIMARY KEY (id))""")
        #          if qry.lastError().type() != 0:
        #           raise DataError("createTemporaryTable -edittable", qry.lastError().text())
        # except DataError as err:
        #     print(err.source, err.message)

    @pyqtSlot()
    def resetWidget(self):
        self.lineNumber.clear()
        self.lineTotal.clear()
        self.dateInvoice.setDate(self.getLastBoardDate())
        self.pushSave.setEnabled(False)
        try:
            if self.mode != OPEN_NEW:
                self.pushReset.setEnabled(False)
                self.pushDelete.setEnabled(False)

            qry = QSqlQuery(self.tempDb)
            qry.exec("TRUNCATE table billed")
            if qry.lastError().type() != 0:
                raise DataError("resetWidget", qry.lastError().text())
            self.tableBilled.model().setQuery(qry)
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
    def includeExcludeHorses(self):
        try:
            qryInsert = QSqlQuery(self.tempDb)
            if self.sender().objectName() == "tablecheck":
                qry = self.tableCheck.model().query()
                row = self.tableCheck.currentIndex().row()
                qry.seek(row)
                qryInsert.exec("CALL payables_include_exclude_charges({},'{}','{}',{},{},{},{},{})".format(
                    qry.value(0),
                    (qry.value(1)),
                    "Board from {} to {}".format(self.dateFrom.date().toString("yyyy-MM-dd"),
                                                 self.dateTo.date().toString("yyyy-MM-dd"))\
                    if self.comboInvoiceType.getHiddenData(0) == PAYABLES_TYPE_BOARD else "Downpayment",
                qry.value(5),
                'NULL' if qry.value(7) == 0  or qry.value(7) == b'\x00' else qry.value(7),
                self.mode,
                True,
                qry.value(8)))

            else :
                qry = self.tableBilled.model().query()
                row = self.tableBilled.currentIndex().row()
                qry.seek(row)
                qryInsert.exec("CALL payables_include_exclude_charges({}, {}, {}, {}, {}, {}, {}, {})".format(
                    qry.value(0),
                    'NULL',
                    'NULL',
                    'NULL',
                    'NULL',
                    self.mode,
                    False,
                    'NULL'))
            if qryInsert.lastError().type() != 0:
                raise DataError("includeHorses -Insert", qryInsert.lastError().text())
            if qryInsert.first():
                qryInsert.first()
                print(qryInsert.value(0), qryInsert.value(1), qryInsert.value(2), qryInsert.value(3),
                  qryInsert.value(4), qryInsert.size())
            while qryInsert.nextResult():
                print("===============")
                while qryInsert.next():
                    print(qryInsert.value(0), qryInsert.value(1), qryInsert.value(2), qryInsert.value(3),
                          qryInsert.value(4),qryInsert.size())

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
            qryBilled.exec(("""SELECT id, horse, description, amount , payableid FROM billed"""))
            if qryBilled.lastError().type() != 0:
                raise DataError("refreshTables -billed", qryBilled.lastError().text())
            self.tableBilled.model().setQuery(qryBilled)
            qryCheck.exec(("""SELECT id, horse, agrid, dos, months, 
            installment, totalamount, payableid, currency
                FROM billablehorses 
                WHERE NOT billed
                ORDER BY agrid, horse"""))
            if qryBilled.lastError().type() != 0:
                raise DataError("refreshTables -Check", qryBilled.lastError().text())
            self.tableBilled.model().setQuery(qryBilled)
            self.tableCheck.model().setQuery(qryCheck)
            qryAmount = QSqlQuery(self.tempDb)
            qryAmount.exec("SELECT SUM(amount) FROM billed")
            qryAmount.first()
            self.lineTotal.setText('{:.2f}'.format(round(qryAmount.value(0),2)))
            self.tableBilled.hideColumn(4)
            self.tableBilled.hideColumn(0)
            self.tableCheck.hideColumn(7)
            #Actualize the invoices table in mainWindow

        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def saveAndClose(self):
        try:
            qrySave = QSqlQuery(self.tempDb)
            qrySave.exec("CALL payables_save_and_close({}, '{}', '{}', '{}', '{}', {}, {}, {}, {})".format(
                'NULL' if self.record is None else self.record.value(0),
                self.lineNumber.text(),
                self.dateInvoice.date().toString("yyyy-MM-dd"),
                self.dateFrom.date().toString("yyyy-MM-dd"),
                self.dateTo.date().toString("yyyy-MM-dd"),
                self.lineTotal.text(),
                self.supplierId,
                self.payableType,
                self.mode))
            if qrySave.lastError().type() != 0:
                raise DataError("refreshTables -Check", qrySave.lastError().text())
            if qrySave.first():
                print(qrySave.value(0))

        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print("saveAndClose", err.args)
        self.widgetClose()

class OtherCharge(QDialog):

    def __init__(self, db, supplierId, mode=None, con_string=None,
                 parent=None):
        super().__init__()
        self.db = db
        if not self.db.isOpen():
            self.db.open()
        self.con_string = con_string
        self.mode = mode
        self.parent = parent
        self.record = None
        self.supplierId = supplierId
        if not self.db.contains("Temp"):
            self.tempDb = self.db.cloneDatabase(self.db, "Temp")
            self.tempDb.open()
        else:
            self.tempDb = self.db.database("Temp")
        self.lastDate = None
        self.setUI()

    def setUI(self):
        self.setModal(True)
        #self.setMinimumSize(1000, 600)
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
        self.lineNumber.editingFinished.connect(self.enableSave)

        lblTotal = QLabel('Total Amount:')
        lblTotal.setAlignment(Qt.AlignRight)
        self.lineTotal = QLineEdit()
        self.lineTotal.setAlignment(Qt.AlignRight)
        self.lineTotal.setMaximumWidth(400)
        self.lineTotal.editingFinished.connect(self.enableSave)

        lblFrom = QLabel('From: ')
        lblFrom.setAlignment(Qt.AlignRight)
        self.dateFrom = QDateEdit()
        self.dateFrom.setCalendarPopup(True)
        self.dateFrom.setDisplayFormat('MM-dd-yyyy')
        self.dateFrom.setMinimumWidth(120)

        lblTo = QLabel('To: ')
        lblTo.setAlignment(Qt.AlignRight)
        self.dateTo = QDateEdit()
        self.dateTo.setCalendarPopup(True)
        self.dateTo.setDisplayFormat('MM-dd-yyyy')
        self.dateTo.setMinimumWidth(120)

        lblInvoice = QLabel("Payable for: ")
        self.comboInvoiceType = FocusCombo(itemList=['DownPayment', 'Board', 'Half Break', 'Final Break', 'Sale Share',
                                                     'OtherCharge'])
        self.comboInvoiceType.setMinimumWidth(70)
        self.comboInvoiceType.setCurrentIndex(5)
        self.comboInvoiceType.setModelColumn(1)
        self.comboInvoiceType.setEnabled(False)
        self.comboInvoiceType.activated.connect(self.enableSave)

        lastDate = self.getLastChargeDate()

        lblDate = QLabel('Date: ')
        lblDate.setAlignment(Qt.AlignRight)
        self.dateInvoice = QDateEdit()
        self.dateInvoice.setCalendarPopup(True)
        self.dateInvoice.setDate(lastDate)
        self.dateInvoice.setDisplayFormat('MM-dd-yyyy')
        self.dateInvoice.setMinimumWidth(120)
        self.dateInvoice.dateChanged.connect(self.enableSave)
        self.dateInvoice.dateChanged.connect(self.checkPeriod)

        lblAccount = QLabel("Account")
        lblAccount.setAlignment(Qt.AlignRight)
        self.comboAccount = FocusCombo(self, ['Transportation',
                                              'Veterinary',
                                              'Blacksmith',
                                              'Tack',
                                              'Club Fee',
                                              'Tournament Fee',
                                              'Stalls & Pens',
                                              'Other'])
        self.comboAccount.setMinimumWidth(150)
        self.comboAccount.setCurrentIndex(-1)
        self.comboAccount.setModelColumn(1)
        self.comboAccount.activated.connect(self.enableSave)

        lblHorses = QLabel("Horse")
        lblHorses.setAlignment(Qt.AlignRight)
        self.comboHorses = FocusCombo()
        self.comboHorses.setModel(self.getHorses())
        self.comboHorses.setCurrentIndex(-1)
        self.comboHorses.setModelColumn(1)
        self.comboHorses.setMaximumWidth(200)
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

        if self.mode != OPEN_NEW:
            qry = self.getCharges()
            colorDict = {'column': (10),
                         True: (QColor('red'), QColor('yellow')),
                         False: (QColor('white'), QColor('black'))}

            colDict = {0: ("ID", True, True, False, None),
                   1: ("AgreementHorseid", True, True, False, None),
                   2: ("Date", False, True, False, None),
                   3: ("#", False, True, False, None),
                   4: ("Account", False, True, False, None),
                   5: ("Horse", False, True, False, None),
                   6: ("Concept", False, False, False, None),
                   7: ("Amount", False, True, 2, None),
                   8: ("Payableid", True, True, False, None),
                   9: ("Acountidid", True, True, False, None ),
                   10: ("Billed", True, True, False, None)}

            self.tableCharges = TableViewAndModel(colDict=colDict, colorDict=colorDict, size=(100, 200), qry=qry)
            self.tableCharges.doubleClicked.connect(self.loadCharge)
            self.tableCharges.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.tableCharges.setSelectionMode(QAbstractItemView.SingleSelection)
            self.tableCharges.doubleClicked.connect(self.enableSave)
            self.setWindowTitle("Edit {}".format(self.windowTitle()))

            pushDelete = QPushButton("Delete")
            pushDelete.setMaximumWidth(70)
            pushDelete.clicked.connect(self.deleteCharge)


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
        #invoiceVLayout.addLayout(self.totalLayout)

        middleFrame.setLayout(totalLayout)

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(pushReset)
        if self.mode != OPEN_NEW:
            buttonLayout.addWidget(pushDelete)
        buttonLayout.addWidget(pushCancel)
        buttonLayout.addWidget(self.pushSave)

        layout = QVBoxLayout()
        layout.addWidget(topFrame)
        layout.addWidget(middleFrame)
        if self.mode != OPEN_NEW:
            layout.addWidget(self.tableCharges)

        layout.addLayout(buttonLayout)

        self.setLayout(layout)

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
    def deleteCharge(self):
        try:
            ans = QMessageBox.question(self,"Warning", "You're about to delete the current record. Confirm (Y/N)",
                                       QMessageBox.Yes|QMessageBox.No)
            if ans == QMessageBox.No:
                return
            self.mode = OPEN_DELETE
            self.saveAndClose()
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def enableSave(self):
        if self.lineNumber.text() and \
                self.lineTotal.text() and \
                self.lineConcept.text() and \
                self.comboAccount.currentIndex() != -1:
            self.pushSave.setEnabled(True)

    def getPayables(self):
        pass

    def loadCharge(self):
        try:
            row = self.tableCharges.currentIndex().row()
            qry = self.tableCharges.model().query()
            qry.seek(row)
            self.record = self.tableCharges.model().query().record()
            if self.record.value(10):
                ans = QMessageBox.warning(self, "Billed Charge", "This charge has been invoiced already",
                                          QMessageBox.Ok)
                return
            self.resetWidget()
            self.lineNumber.setText(self.record.value(3))
            self.dateInvoice.setDate(self.record.value(2))
            self.comboHorses.setCurrentIndex(self.comboHorses.seekData(self.record.value(1), 0))
            self.comboAccount.setCurrentIndex(self.comboAccount.seekData(self.record.value(9),0))
            self.lineConcept.setText(self.record.value(6))
            self.lineTotal.setText(str(self.record.value(7)))


        except Exception as err:
            print("loadCharge", err.args)

    @pyqtSlot()
    def widgetClose(self):
        self.done(QDialog.Rejected)

    @pyqtSlot()
    def saveAndClose(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL othercharges_saveAndUpdate({}, '{}', {} , {}, '{}', {}, '{}', {}, {}, {}, @res)".format(
                self.comboHorses.getHiddenData(0) if self.comboHorses.getHiddenData(0) else 'NULL',
                self.dateInvoice.date().toString("yyyy-MM-dd"),
                int(self.comboAccount.getHiddenData(0)),
                int(self.supplierId),
                self.lineConcept.text(),
                self.lineTotal.text(),
                self.lineNumber.text(),
                self.mode,
                'NULL' if self.record is None else self.record.value(0),
                'NULL' if self.record is None else self.record.value(8)))
            if qry.lastError().type() != 0:
                raise DataError("saveAndClose", qry.lastError().text(),qry.lastError().number())
            qry.first()
            if qry.value(1) != '00000':
                raise DataError("saveAndClose", qry.value(2))
            if self.mode != OPEN_NEW:
                qryCharges = self.getCharges()
                self.tableCharges.model().setQuery(qryCharges)
            self.resetWidget()
            self.widgetClose()
        except DataError as err:
            print(err.source, err.message, err.type)
            if err.type == 2006:
                self.parent.check_connection()


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
                raise DataError("getLastChargeDate", qry.lastError().text())
            qry.first()
            if not qry.value(0).isNull():
                startDate = qry.value(0)
            else:
                startDate = QDate.currentDate().addDays(-30)
            self.setPeriod(startDate)
            return startDate
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def setPeriod(self, start):
        self.dateFrom.setDate(start.addDays(-start.day() + 1))
        self.dateTo.setDate(self.dateFrom.date().addDays(self.dateFrom.date().daysInMonth() - 1))

    def getHorses(self):
        try:
            qry = QSqlQuery(self.db)
            qry.prepare("""SELECT ah.id, h.name 
                        FROM horses h 
                        INNER JOIN agreementhorses ah 
                        on h.id = ah.horseid 
                        INNER JOIN agreements a
                        ON ah.agreementid = a.id
                        WHERE ah.billable 
                        AND a.supplierid = ? 
                        order by h.name""")
            qry.addBindValue(QVariant(self.supplierId))
            qry.exec()
            if qry.lastError().type() != 0:
                raise DataError("getHorses", qry.lastError().text())
            model = QSqlQueryModel()
            model.setQuery(qry)
            return model
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def resetWidget(self):
        self.lineNumber.clear()
        self.lineConcept.clear()
        self.lineTotal.clear()
        self.comboAccount.setCurrentIndex(-1)
        self.comboHorses.setCurrentIndex(-1)
        self.dateInvoice.setDate(self.getLastChargeDate())
        self.pushSave.setEnabled(False)

    @pyqtSlot()
    def checkPeriod(self):
        try:
            if self.dateInvoice.date() < self.dateFrom.date() or self.dateInvoice.date() > self.dateTo.date():
                ans = QMessageBox.warning(self, "Date Issue", "The date entered {} is outside the range provided."
                                                              "Do you want to continue".format(
                    self.dateInvoice.date().toString("MM-dd-yyyy")),QMessageBox.Yes|QMessageBox.No)
                if ans == QMessageBox.No :
                    self.dateInvoice.setDate(self.getLastChargeDate())
                    return

        except Exception as err:
            print("CheckPeriod", err.args)