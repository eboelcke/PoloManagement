from PyQt5.QtWidgets import (QMessageBox, QDialog, QPushButton, QTableView, QVBoxLayout,QHBoxLayout,
                             QHeaderView,  QAction, QDateEdit, QLabel, QRadioButton)
from PyQt5.QtSql import QSqlQuery, QSqlQueryModel
from PyQt5.QtCore import Qt, QVariant, pyqtSlot, QDate
from PyQt5.QtGui import QColor, QTextLength, QIcon
from PyQt5.QtPrintSupport import QPrintPreviewDialog, QPrintDialog
from ext.APM import ACCOUNT_INVOICE, ACCOUNT_PAYMENT, ACCOUNT_ALL, ACCOUNT_HORSE_BALANCE, TableViewAndModel,\
                    DataError, FocusCombo
from ext.Printing import ReportPrint, InvoicePrint
import poloresurce



class AvailableDocuments(QDialog):

    def __init__(self, db, documentType, supplierId, parent=None):
        super().__init__()
        self.parent = parent
        self.documentType = documentType
        self.db = db
        self.setModal(True)
        self.document = None
        self.supplierId = supplierId
        self.setUI()

    def setUI(self):
        #self.currencyId = 1
        self.setMinimumWidth(500)
        startDate = QDate(QDate.currentDate().year(), 1, 1)
        lblDate = QLabel('Date From: ')
        self.startDate = QDateEdit()
        self.startDate.setDisplayFormat('yyyy-MM-dd')
        self.startDate.setCalendarPopup(True)
        self.startDate.setDate(startDate)
        self.startDate.setFixedWidth(120)
        self.startDate.dateChanged.connect(self.setDocumentTable)

        lblCurrency = QLabel("Currency")
        self.comboCurrency = FocusCombo(itemList=["U$A", "AR$"])
        self.comboCurrency.setModelColumn(1)
        self.comboCurrency.setCurrentIndex(self.parent.parent.comboCurrency.currentIndex())
        self.comboCurrency.setMaximumWidth(80)
        self.comboCurrency.activated.connect(self.setDocumentTable)

        if self.documentType == ACCOUNT_HORSE_BALANCE:
            self.radioMode = QRadioButton("Active")
            self.radioMode.toggled.connect(self.setDocumentTable)

        self.documentTable = self.setDocumentTable()
        self.documentTable.doubleClicked.connect(self.handlePrintInvoicePreview)
        self.documentTable.verticalHeader().setVisible(False)

        oKButton = QPushButton(QIcon(":/Icons8/exit/closeman.png"), "Exit", self)
        oKButton.clicked.connect(self.widgetClose)
        oKButton.setMaximumSize(100, 30)

        printButton = QPushButton(QIcon(":/Icons8/print/print.png"), "Print", self)
        printButton.setMaximumSize(100, 30)
        printButton.clicked.connect(self.handlePrint)

        previewButton = QPushButton(QIcon(":/Icons8/print/printpreview.png"), "Preview", self)
        previewButton.setMaximumSize(100, 30)
        previewButton.clicked.connect(self.handlePrintListPreview)

        pdfButton = QPushButton(QIcon(":/Icons8/print/savepdf.png"), "Save PDF", self)
        pdfButton.setMaximumSize(100, 30)
        pdfButton.clicked.connect(self.handleSavePdfList)

        optionsLayout = QHBoxLayout()
        if self.documentType == ACCOUNT_HORSE_BALANCE:
            optionsLayout.addWidget(self.radioMode)
        optionsLayout.addWidget(lblDate,alignment=Qt.AlignLeft)
        optionsLayout.addWidget(self.startDate, alignment=Qt.AlignLeft)
        optionsLayout.addWidget(lblCurrency, alignment=Qt.AlignLeft)
        optionsLayout.addWidget(self.comboCurrency,alignment=Qt.AlignLeft)

        buttonsLayout = QHBoxLayout()
        buttonsLayout.addWidget(pdfButton)
        buttonsLayout.addWidget(printButton)
        buttonsLayout.addWidget(previewButton)
        buttonsLayout.addWidget(oKButton)

        layout = QVBoxLayout()
        layout.addWidget(self.documentTable)
        layout.addLayout(optionsLayout)
        layout.addLayout(buttonsLayout)
        self.setLayout(layout)

    def setDocumentTable(self):
        if self.documentType == ACCOUNT_INVOICE:
            self.setWindowTitle("Invoices from {}".format(self.parent.parent._supplier))
            try:
                qry = QSqlQuery(self.db)
                qry.exec("call accountreports_getInvoices({}, {}, '{}')".format(self.supplierId,
                                                                          self.comboCurrency.currentIndex(),
                                                                          self.startDate.date().toString("yyyy-MM-dd")))
                if not isinstance(self.sender(), QAction):
                    self.documentTable.model().setQuery(qry)
                    return
                colorInvDict = {'column': (6),
                                0: (QColor('red'), QColor('yellow')),
                                1: (QColor('white'), QColor('black'))}

                colInvDict = {0: ("Id", True, True, False, None),
                              1: ("Date", False, True, False, None),
                              2: ("Type", False, True, True, None),
                              3: ("Number", False, True, False, None),
                              4: ("Curr", True, True, False, None),
                              5: ("Installment", True, True, 2, None),
                              6: ("Closed", True, True, False, None),
                              7: ("supplierid", True, True, False, None),
                              8: ("Subtotal", False, True, 2, None),
                              9: ("iva", False, True, 2, None),
                              10: ("Total", False, False, 2, None),
                              11: ("currency", True, True, False, None),
                              12: ("billingcurrency", True, True, False, None),
                              13: ("ivarate", True, True, False, None),
                              14: ("exchangerate", True, True, False, None),
                              15: ("invoicetypeid", True, True, False, None),
                              16: ("chargetypeid", True, True, False, None),
                              17: ("notes", True, True, False, None)}

            except DataError as err:
                print("AvailableDocuments: setDocumentTable", err.args)
        elif self.documentType == ACCOUNT_PAYMENT:
            self.setFixedWidth(750)
            self.setWindowTitle("Payments to {}".format(self.parent.parent._supplier))
            try:
                qry = QSqlQuery(self.db)
                qry.exec("call accountreports_getPayments({}, {},'{}')".format(self.supplierId,
                                                                          self.comboCurrency.currentIndex(),
                                                                          self.startDate.date().toString("yyyy-MM-dd")))
                if not isinstance(self.sender(), QAction):
                    self.documentTable.model().setQuery(qry)
                    return
                colorInvDict = {'column': (7),
                                0: (QColor('red'), QColor('yellow')),
                                1: (QColor('white'), QColor('black')),
                                2: (QColor("LightBlue"), QColor("black"))}

                colInvDict = {0: ("Id", True, True, False, None),
                              1: ("Date ", False, True, False, None),
                              2: ("Number", False, True, False, None),
                              3: ("Type", False, True, True, None),
                              4: ("Bank", False, False, False, None),
                              5: ("Transaction", False, True, False, None),
                              6: ("Amount", False, False, 2, None),
                              7: ("payType", True, True, False, None),
                              8: ("paybank", True, True, False, None),
                              9: ("paycurrency", True, True, False, None),
                              10: ("amountLocal", True, True, False, None),
                              11: ("notes", True, True, False, None)}

            except DataError as err:
                print("AvailableDocuments: setDocumentTable", err.args)
        elif self.documentType == ACCOUNT_ALL:
            self.setFixedWidth(750)
            self.setWindowTitle("Account {}".format(self.parent.parent._supplier))
            try:
                qry = QSqlQuery(self.db)
                qry.exec("call accountreports_getaccount({}, {}, '{}')".format(self.supplierId,
                                                                          self.comboCurrency.currentIndex(),
                                                                          self.startDate.date().toString("yyyy-MM-dd")))
                if not isinstance(self.sender(), QAction):
                    self.documentTable.model().setQuery(qry)
                    return
                colorInvDict = {'column': (7),
                                0: (QColor('lightBlue'), QColor('black')),
                                1: (QColor('white'), QColor('black')),
                                2: (QColor("yellow"), QColor("black"))}

                colInvDict = {0: ("Id", True, True, False, None),
                              1: ("tid", True, True, False, None),
                              2: ("Date", False, True, False, None),
                              3: ("Type", False, False, False, None),
                              4: ("Paytype", True, True, False, None),
                              5: ("Number", False, False, False, None),
                              6: ("Bank", False, False, False, None),
                              7: ("Debit", False, False, 2, None),
                              8: ("Credit", False, False, 2, None),
                              9: ("Balance", False, False, 2, None)}

            except DataError as err:
                print("AvailableDocuments: setDocumentTable", err.args)
        elif self.documentType == ACCOUNT_HORSE_BALANCE:
            self.setFixedWidth(800)
            self.setWindowTitle("{}'s horses balances".format(self.parent.parent._supplier))
            try:
                qry = QSqlQuery(self.db)
                qry.exec("CALL accountreports_gethorsesbalance({}, '{}', {})".format(self.supplierId,
                                                                self.startDate.date().toString("yyyy-MM-dd"),
                                                                 True if self.radioMode.isChecked() else False))
                if not isinstance(self.sender(), QAction):
                    self.documentTable.model().setQuery(qry)
                    return
                colorInvDict = {'column': (7),
                                0: (QColor('red'), QColor('white')),
                                1: (QColor('white'), QColor('black')),
                                'modifier': (2),
                                QDate(): (QColor('yellow'),QColor('Black'))}

                colInvDict = {0: ("Id", True, True, False, None),
                              1: ("Horse", False, False, False, None),
                              2: ("DOS ", False, True, False, None),
                              3: ("Months", False, True, True, None),
                              4: ("Inst", False, True, True, None),
                              5: ("Total Agr.", False, True, 2, None),
                              6: ("Inst. Paid", False, True, 2, None),
                              7: ("Balance", False, True, 2, None),
                              8: ("Amount Paid", True, True, 2, None),
                              9: ("Balance due", False, True, 2, None)}

            except DataError as err:
                print("AvailableDocuments: setDocumentTable", err.args)

            except DataError as err:
                print("AvailableDocuments: setDocumentTable", err.args)
        return TableViewAndModel(colInvDict, colorInvDict, (100, 100), qry)

    @pyqtSlot()
    def handlePrint(self):
        pass

    def handleSavePdfList(self):
        try:
            prt = ReportPrint(self.documentTable, self.windowTitle(), self.parent.parent)
            prt.handlePdf()
        except Exception as err:
            print("AvailableDocuments: handlePrintListPreview", err.args)

    @pyqtSlot()
    def handlePrintListPreview(self):
        try:
            total = self.getTotals()
            prt = ReportPrint(self.documentTable, self.windowTitle(), totalRecord=total)
            prt.handlePreview()
        except Exception as err:
            print("AvailableDocuments: handlePrintListPreview", err.args)

    def getTotals(self):
        try:
            if self.documentType == ACCOUNT_HORSE_BALANCE:
                qry = QSqlQuery(self.db)
                qry.exec("CALL accountreports_gethorsebalancetotals ({}, '{}', {})".format(self.supplierId,
                                                                    self.startDate.date().toString(
                                                                                           "yyyy-MM-dd"),
                                                                    True if self.radioMode.isChecked() else False))
                if qry.lastError().type() != 0:
                    raise DataError("AvailableDocuments: getTotal", qry.lastError().text())
                if qry.first():
                    return dict([(0, "Total"), (4 , qry.value(0)), (5 , qry.value(1)),
                                 (6 , qry.value(2)), (7 , qry.value(3))])
            elif self.documentType == ACCOUNT_INVOICE:
                qry = QSqlQuery(self.db)
                qry.exec("CALL accountreports_getInvoicestotals({}, {}, '{}')".format(self.supplierId,
                                                                                self.comboCurrency.currentIndex(),
                                                                                self.startDate.date().toString(
                                                                                    "yyyy-MM-dd")))
                if qry.lastError().type() != 0:
                    raise DataError("AvailableDocuments: getTotal", qry.lastError().text())
                if qry.first():
                    return dict([(0, "Total"), (3 , qry.value(1)), (4 , qry.value(2)),
                                 (5 , qry.value(3))])
            elif self.documentType == ACCOUNT_PAYMENT:
                qry = QSqlQuery(self.db)
                qry.exec("CALL accountreports_getpaymenttotals({}, {}, '{}')".format(self.supplierId,
                                                                                      self.comboCurrency.currentIndex(),
                                                                                      self.startDate.date().toString(
                                                                                          "yyyy-MM-dd")))
                if qry.lastError().type() != 0:
                    raise DataError("AvailableDocuments: getTotal", qry.lastError().text())
                if qry.first():
                    return dict([(0, "Total"), (5, qry.value(0))])

            else:
                return None
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print("AvailableDocuments: getTotals", err.args)

    @pyqtSlot()
    def handlePrintInvoicePreview(self):
        try:
            row = self.documentTable.currentIndex().row()
            self.documentTable.model().query().seek(row)
            record = self.documentTable.model().query().record()
            table = self.getDetailTable(record.value(0))
            msgBox = QMessageBox()
            # msgBox.setParent(self)
            msgBox.setWindowTitle("{} Save or Preview".format("Invoice" if self.documentType == ACCOUNT_INVOICE else
                                                              "Payment"))
            msgBox.setText("Make your choice: Save to PDF or Preview?")
            msgBox.addButton(QPushButton(QIcon(":/Icons8/print/savepdf.png"), 'Save PDF'), QMessageBox.YesRole)
            msgBox.addButton(QPushButton(QIcon(":/Icons8/print/printpreview.png"), "Preview"), QMessageBox.YesRole)
            msgBox.addButton(QPushButton(QIcon(":/Icons8/exit/closeman.png"), "Cancel"), QMessageBox.YesRole)
            msgBox.exec()
            if msgBox.clickedButton().text() == "Cancel":
                return
            prt = InvoicePrint(self.db, record, table,documentType=self.documentType, parent=self.parent.parent)
            if msgBox.clickedButton().text() == "Save PDF":
                prt.handlePdf()
            else:
                prt.handlePreview()

        except Exception as err:
            print("AvailableDocuments: handlePrintPreview", err.args)

    def getDetailTable(self, documentId):
        try:
            if self.documentType == ACCOUNT_INVOICE:
                qry = QSqlQuery(self.db)
                qry.exec("call availableDocuments_getinvoicelines({})".format(documentId))
                if qry.lastError().type() != 0:
                    raise DataError("AvailableDocuments: getDetailTable", qry.lastError().text())
                colorDict = {'column': (0),
                            0: (QColor('white'), QColor('black')),
                            1: (QColor('white'), QColor('black'))}

                colDict = {0: ("Concept", False, False, False, None),
                            1: ("Amount", False, True, 2, None)}
            elif self.documentType == ACCOUNT_PAYMENT:
                qry = QSqlQuery(self.db)
                qry.exec("call availableDocuments_getpaymentlines({})".format(documentId))
                if qry.lastError().type() != 0:
                    raise DataError("AvailableDocuments: getDetailTable", qry.lastError().text())
                colorDict = {'column': (0),
                             0: (QColor('white'), QColor('black')),
                             1: (QColor('white'), QColor('black'))}

                colDict = {0: ("Date", False, False, False, None),
                           1: ("Invoice", False, False, False, None),
                           2: ("Amount", False, True, 2, None)}

            return TableViewAndModel(colDict, colorDict, (100, 100), qry)


        except DataError as err:
            print(err.source, err.message)


    @pyqtSlot()
    def widgetClose(self):
        self.close()