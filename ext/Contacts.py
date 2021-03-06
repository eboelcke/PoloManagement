import sys
import os
from PyQt5.QtWidgets import (QDialog, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel, QLineEdit, QPlainTextEdit,
                             QPushButton, QTableView, QMessageBox, QCheckBox, QListView,
                              QMenuBar, QMenu, QAction, QFormLayout, QAbstractItemView)
from PyQt5.QtCore import Qt, pyqtSlot, QVariant, QPoint, QModelIndex, QDate, QRegExp
from PyQt5.QtGui import QStandardItemModel, QColor, QMouseEvent, QIcon, QRegExpValidator
from PyQt5.QtSql import QSqlQuery, QSqlQueryModel, QSqlDriver
from ext.socketclient import RequestHandler
from ext.Invoices import Invoice, Payables, Downpayments, OtherCharge, Payment, EditPayables
from ext.APM import (DataError, INDEX_UPGRADE, INDEX_EDIT, INDEX_NEW,
    CONTACT_POLO_PLAYER, CONTACT_BUSTER, CONTACT_BUYER, CONTACT_DEALER, CONTACT_BREAKER, CONTACT_RESPONSIBLE,
    CONTACT_PLAYER, CONTACT_VETERINARY, ACCOUNT_ALL, ACCOUNT_PAYMENT, ACCOUNT_INVOICE, ACCOUNT_HORSE_BALANCE,
    OPEN_EDIT_ONE, OPEN_EDIT,OPEN_NEW,
    PAYABLES_TYPE_BOARD, PAYABLES_TYPE_DOWNPAYMENT, PAYABLES_TYPE_ALL,PAYABLES_TYPE_SALE, PAYABLES_TYPE_OTHER,
    PAYABLES_TYPE_FULL_BREAK, PAYABLES_TYPE_HALF_BREAK,
    TableViewAndModel, FocusCombo, FocusPlainTextEdit, Cdatabase, EMAILREGEXP, LineEditHover)
from ext.transfers import Transfer
from ext.PriceIndex import CostIndex
from ext.accountReports import AvailableDocuments


class ChooseActiveSupplier(QDialog):
    def __init__(self, db, parent=None, qry=None):
        super().__init__(parent=parent)
        self.parent = parent
        self.db = db
        if not self.db.isOpen():
            self.db.open()
        self.qrySupplier = qry
        self.setModal(True)
        self.setUI()


    def setUI(self):
        self.setModal(True)
        colDict = {
            0: ("ID", True, True, True, None),
            1: ("Name", False, False, False, None),
            2: ("Play", False, True, True, None),
            3: ("Break", False, True, True, None)}
        colorDict = {}
        self.table = TableViewAndModel(colDict, colorDict, (300, 200), self.qrySupplier)
        self.table.doubleClicked.connect(self.getSupplier)

        pushCancel = QPushButton('Cancel')
        pushCancel.setMaximumWidth(60)
        pushCancel.clicked.connect(self.closeChoose)

        pushOpen = QPushButton("Open")
        pushOpen.setMaximumWidth(60)
        pushOpen.clicked.connect(self.getSupplier)

        pushShow = QPushButton("Show")
        pushShow.setMaximumWidth(60)
        pushShow.clicked.connect(self.showSupplier)

        hLayout = QHBoxLayout()
        hLayout.addWidget(pushCancel)
        hLayout.addWidget(pushShow)
        hLayout.addWidget(pushOpen)

        vLayout = QVBoxLayout()
        vLayout.addWidget(self.table)
        vLayout.addLayout(hLayout)

        self.setWindowTitle("Choose Service Provider")
        self.setMinimumWidth(500)

        self.setLayout(vLayout)


    def getSuppliers(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("""SELECT c.id,
                    c.fullname,
                     if (c.playerseller = 1,  _ucs2 x'2714', ''),
                     if (c.horsebreaker = 1 , _ucs2 x'2714', '')
                     FROM contacts c 
                     WHERE (c.playerseller 
                     OR c.horsebreaker)
                     AND c.active
                     AND EXISTS (
                     SELECT a.supplierid
                     FROM agreements a
                     WHERE a.supplierid = c.id 
                     AND a.active);""")
            return qry
        except Exception as err:
            print("GetSuppliers", type(err).__name__, err.args)

    @pyqtSlot()
    def showSupplier(self):
        try:
            model = self.table.model()
            row = self.table.currentIndex().row()
            model.query().seek(row)
            record = model.query().record()
            self.parent.supplierId = record.value(0)
            self.parent.supplier = record.value(1)
            self.parent.player = True if record.value(2) == u'\u2714' else False
            self.parent.buster = True if record.value(3) == u'\u2714' else False
            self.parent.setWindowTitle("Polo Managemet Contact Data for :{}".format(record.value(1)))
            self.parent.supplierData()
            self.getCurrency(record.value(0))
            self.close()
        except Exception as err:
            print("ChooseActiveSupplier: getSupplier", type(err).__name__, err.args)

    @pyqtSlot()
    def getSupplier(self):
        try:
            idx = None
            model = self.table.model()
            row = self.table.currentIndex().row()
            model.query().seek(row)
            record = model.query().record()
            self.parent.supplierId = record.value(0)
            self.parent.supplier = record.value(1)
            self.parent.player = True if record.value(2) == u'\u2714' else False
            self.parent.buster = True if record.value(3) == u'\u2714' else False
            self.parent.setWindowTitle("Polo Managemet Contact Data for : " + record.value(1))
            self.getCurrency(record.value(0))
            self.close()
        except  Exception as err:
            print("ChooseActiveSupplier: getSupplier", err.args)

    def getCurrency(self, supplierId):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL chooseactivesupplier_getcurrency({})".format(supplierId))
            if qry.first():
                if qry.value(0) and qry.value(1):
                    pop = QMessageBox()
                    pop.setWindowTitle("Currency")
                    pop.setWindowIcon(QIcon(":Icons8/Accounts/currency.png"))
                    pop.setText('There are payables on both currencies!')
                    pop.setIcon(QMessageBox.Question)
                    pop.addButton("U$A", QMessageBox.YesRole)
                    pop.addButton("AR$", QMessageBox.YesRole)
                    pop.buttonClicked.connect(self.chooseCurrency)
                    pop.setModal(True)
                    pop.show()
                    idx = pop.exec()
                elif qry.value(0):
                    idx = 0
                elif qry.value(1):
                    idx = 1
                else:
                    idx = 0
            self.parent.comboCurrency.setCurrentIndex(idx)
        except Exception as err:
            print("ChooseActiveSupplier: getCurrency", type(err).__name__, err.args)

    def chooseCurrency(self, btn):
        if btn.text() == 'AR$':
            idx = 1
            return idx
        idx = 0

    @pyqtSlot()
    def closeChoose(self):
        self.parent.supplierId = None
        self.close()

class Supplier(QDialog):

    def __init__(self, db, supplierId, type=None, parent=None):
        super().__init__()
        self.db = db
        if not self.db.isOpen():
            self.db.open()
        self.supplierId = supplierId
        self.type = type
        self.players = False
        self.busters = False
        self.setModal(True)
        self.parent = parent
        self.player, self.buster = self.getPlayerBuster()
        self.setUI()

    def setUI(self):

        supplierMenu = self.getMenu()
        supplierMenu.show()

        supplier = self.getSupplier()
        self.setWindowTitle(supplier)
        lblSupplier = QLabel(supplier)
        lblSupplier.setMaximumWidth(300)

        checkPlay = QCheckBox("Play & Sale")
        checkPlay.setChecked(self.players)
        checkPlay.setEnabled(False)

        checkBuster = QCheckBox("Breaking Services")
        checkBuster.setChecked(self.busters)
        checkBuster.setEnabled(False)

        pushCancel = QPushButton()
        pushCancel.setMaximumWidth(80)
        pushCancel.clicked.connect(self.close)

        self.pushSave = QPushButton('Save')
        self.pushSave.setMaximumWidth(80)
        self.pushSave.clicked.connect(self.saveAndClose)
        self.pushSave.setEnabled(False)

        lblAvailable = QLabel()
        if self.type is  None:
            self.setMinimumWidth(1000)
            pushCancel.setText('Close')
            self.pushSave.setVisible(False)

            qryPlayers, qryBusters, qryLocations = self.getSupplierData()

            modelPlayers = QSqlQueryModel()
            modelPlayers.setQuery(qryPlayers)

            lblPlayers = QLabel('Polo Players')
            self.listPlayers = QListView()
            self.listPlayers.setModel(modelPlayers)
            self.listPlayers.setModelColumn(1)
            self.listPlayers.setObjectName('contactplayers')
            self.listPlayers.doubleClicked.connect(lambda : self.checkPerson(CONTACT_POLO_PLAYER))
            self.listPlayers.setContextMenuPolicy(Qt.CustomContextMenu)
            self.listPlayers.customContextMenuRequested.connect(self.contextMenu)
            self.listPlayers.setMouseTracking(True)
            self.listPlayers.entered.connect(self.tryEntered)
            self.listPlayers.setEnabled(True) if self.player else self.listPlayers.setEnabled(False)

            modelBusters = QSqlQueryModel()
            modelBusters.setQuery(qryBusters)

            lblBusters = QLabel("Horse Busters")
            self.listBusters = QListView()
            self.listBusters.setModel(modelBusters)
            self.listBusters.setObjectName('contactbusters')
            self.listBusters.setModelColumn(1)
            self.listBusters.setObjectName('contactbusters')
            self.listBusters.setContextMenuPolicy(Qt.CustomContextMenu)
            self.listBusters.doubleClicked.connect(lambda : self.checkPerson(CONTACT_BUSTER))
            self.listBusters.setContextMenuPolicy(Qt.CustomContextMenu)
            self.listBusters.customContextMenuRequested.connect(self.contextMenu)
            self.listBusters.setEnabled(True) if self.buster else self.listBusters.setEnabled(False)

            modelLocations = QSqlQueryModel()
            modelLocations.setQuery(qryLocations)

            lblLocations = QLabel('Locations')
            self.listLocations = QListView()
            self.listLocations.setModel(modelLocations)
            self.listLocations.setModelColumn(1)
            self.listLocations.setObjectName('locations')
            self.listLocations.doubleClicked.connect(self.checkPerson)
            self.listLocations.setContextMenuPolicy(Qt.CustomContextMenu)
            self.listLocations.customContextMenuRequested.connect(self.contextMenu)

            colorDict = colorDict = {'column':(3),
                        u'\u2640':(QColor('pink'), QColor('black')),
                        u'\u2642':(QColor('lightskyblue'), QColor('black')),
                        u'\u265E': (QColor('lightgrey'), QColor('black'))}
            colDict = {0:("id", True, True, True, None),
                       1:("RP", False, True, True, None),
                       2:("Horse", False, False, False, None),
                       3:("Sex", False, True, True, None),
                       4:("Coat", True, True, True, None),
                       5:("Agr No",False, True, True, None),
                       6:("Date", True, True, True, None),
                       7:("Break", False, True, True, None),
                       8:("B&P",False, True, True, None),
                       9: ("Play", False, True, True, None),
                       10: ("Over", False, True, True, None),
                       11:("DOS", False, True, False, None),
                       12:("Months", False, True, True, None),
                       13:("Location", False, True, False, None),
                       14: ("Broke", False, True, True, None)}
            qry = self.getHorses()
            self.tableHorses = TableViewAndModel(colDict, colorDict, (300, 100), qry)

        else:
            pushCancel.setText('Cancel')
            if self.type == CONTACT_POLO_PLAYER:
                qry = self.getPoloPlayers()
                lblAvailable.setText("Available Polo Players")
            elif self.type == CONTACT_BUSTER:
                qry = self.getBusters()
                lblAvailable.setText("Available Horse Busters")
            model = QSqlQueryModel()
            model.setQuery(qry)
            self.combo = FocusCombo()
            self.combo.setMaximumWidth(300)
            self.combo.setModel(model)
            self.combo.setModelColumn(1)
            self.combo.setCurrentIndex(-1)
            self.combo.activated.connect(self.enableSave)

        buttonsLayout = QHBoxLayout()
        buttonsLayout.addWidget(pushCancel)
        buttonsLayout.addWidget(self.pushSave)

        gLayout = QGridLayout()
        gLayout.addWidget(lblSupplier, 0,0)
        gLayout.addWidget(checkPlay, 0,1)
        gLayout.addWidget(checkBuster, 0,2)

        if self.type is not None:
            gLayout.addWidget(lblAvailable, 1,0)
            gLayout.addWidget(self.combo,1,2)
        else:
            gLayout.addWidget(lblPlayers,1,0)
            gLayout.addWidget(lblBusters,1,1)
            gLayout.addWidget(lblLocations,1,2)
            gLayout.addWidget(self.listPlayers,2,0)
            gLayout.addWidget(self.listBusters,2,1)
            gLayout.addWidget(self.listLocations,2,2)

        vLayout = QVBoxLayout()
        vLayout.addWidget(supplierMenu)
        vLayout.addLayout(gLayout)
        if self.type is None:
            vLayout.addWidget(self.tableHorses)
        vLayout.addLayout(buttonsLayout)

        self.setLayout(vLayout)

    def refreshHorses(self):
        self.tableHorses.model().setQuery(self.getHorses())


    def getHorses(self):
        try:
            qry = QSqlQuery(self.db)
            qry.prepare("""SELECT h.id, h.rp, h.name, 
            CASE    WHEN h.sexid = 1 THEN _ucs2 x'2642'
                    WHEN h.sexid = 2 THEN _ucs2 x'2640'
                    WHEN h.sexid = 3 THEN _UCS2 x'265E'
            END sex,
            c.coat,
            a.id agr,
            a.date,
            IF (a.agreementtype = 1, _ucs2 x'2714', '') ,
            IF (a.agreementtype = 1, _ucs2 x'2714', '') ,
            IF (a.agreementtype = 1, _ucs2 x'2714', '') ,
            IF (a.agreementtype = 1, _ucs2 x'2714', '') ,
            ah.dos, 
            TIMESTAMPDIFF(MONTH, CURDATE(), ah.dos) time,
            l.name location,
            IF (h.isbroke = 1, _ucs2 x'2714', '') broke
            FROM horses h
            INNER JOIN coats c 
            ON h.coatid = c.id
            INNER JOIN agreementhorses ah
            ON h.id = ah.horseid
            INNER JOIN agreements a
            ON ah.agreementid = a.id
            INNER JOIN locations l
            ON h.locationid = l.id
            WHERE ah.active 
            AND a.supplierid = ?
            ORDER BY agr, sex """)
            qry.addBindValue(QVariant(self.supplierId))
            qry.exec()
            if qry.lastError().type() != 0:
                raise DataError("getHorses", qry.lastError().text())
            return qry
        except DataError as err:
            print(err.source, err.message)

    pyqtSlot()
    def enableSave(self):
        if self.combo.currentIndex() != -1:
            self.pushSave.setEnabled(True)

    pyqtSlot(QModelIndex)
    def tryEntered(self, index):

        print(index.row())

    def getPoloPlayers(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("""SELECT C.id, C.fullname 
                            FROM contacts c
                            WHERE c.player AND c.active AND 
                            NOT EXISTS (SELECT cp.personid 
                                FROM contactplayers cp
                                WHERE cp.personid = c.id and cp.active)
                                ORDER BY c.fullname""")
            if qry.lastError().type() != 0:
                raise DataError("getPlayers", qry.lastError().text())
            return qry
        except DataError as err:
            print("getPoloPlayers", err.args)

    def getSupplierData(self):
        try:
            qryPlayer = QSqlQuery(self.db)
            qryPlayer.prepare("""SELECT C.id, c.fullname 
                FROM contacts c
                INNER JOIN contactplayers cp
                ON cp.personid = c.id
                WHERE c.active 
                AND cp.active 
                AND cp.contactid = ?
                """)
            qryPlayer.addBindValue(QVariant(self.supplierId))
            qryPlayer.exec()

            qryBuster = QSqlQuery(self.db)
            qryBuster.prepare("""
                SELECT c.id, c.fullname 
                FROM contacts c 
                INNER JOIN contactbusters cb
                ON c.id = cb.personid 
                WHERE cb.active 
                AND c.active
                AND cb.contactid = ?
                """)
            qryBuster.addBindValue(QVariant(self.supplierId))
            qryBuster.exec()

            qryLocations = QSqlQuery(self.db)
            qryLocations.prepare("""SELECT l.id, l.name , l.managerid, l.address, l.telephone, l.main, 
                l.systemlocation, l.active
                FROM locations l
                INNER JOIN contacts c
                ON l.contactid = c.id
                WHERE l.active AND l.contactid = ?""")
            qryLocations.addBindValue(QVariant(self.supplierId))
            qryLocations.exec()
            return qryPlayer, qryBuster, qryLocations
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print('Supplier: getSuppliersData', type(err).__name__, err.args)

    def getMenu(self):

        addTransferAction = QAction("Add Transfer", self)
        addTransferAction.triggered.connect(self.addTransfer)
        editTransferAction = QAction("Edit Transfers", self)
        editTransferAction.triggered.connect(self.editTransfer)

        addInvoiceDownPaymentAction = QAction("Downpayment", self)
        addInvoiceDownPaymentAction.triggered.connect(lambda: self.addInvoice(PAYABLES_TYPE_DOWNPAYMENT,
                                                                              OPEN_NEW))

        addInvoiceBoardPaymentAction = QAction("Board", self)
        addInvoiceBoardPaymentAction.triggered.connect(lambda: self.addInvoice(PAYABLES_TYPE_BOARD,OPEN_NEW))

        addInvoiceHalfBreakPaymentAction = QAction("Half Break", self)
        addInvoiceHalfBreakPaymentAction.triggered.connect(lambda: self.addInvoice(PAYABLES_TYPE_HALF_BREAK,
                                                                                   OPEN_NEW))

        addInvoiceBreakFinalPaymentAction = QAction("Final Break", self)
        addInvoiceBreakFinalPaymentAction.triggered.connect(lambda: self.addInvoice(PAYABLES_TYPE_FULL_BREAK,
                                                                                    OPEN_NEW))

        addInvoiceSalePaymentAction = QAction("Sale Share", self)
        addInvoiceSalePaymentAction.triggered.connect(lambda: self.addInvoice(PAYABLES_TYPE_SALE,OPEN_NEW))

        addInvoiceOtherPaymentAction = QAction("Other Charges", self)
        addInvoiceOtherPaymentAction.triggered.connect(lambda: self.addInvoice(PAYABLES_TYPE_OTHER,OPEN_NEW))

        addInvoiceAllPaymentAction = QAction("All Charges", self)
        addInvoiceAllPaymentAction.triggered.connect(lambda: self.addInvoice(PAYABLES_TYPE_ALL,OPEN_NEW))

        addBoardAction = QAction("Board", self)
        addBoardAction.triggered.connect(lambda: self.addPayables(OPEN_NEW))

        addDownpaymentAction = QAction("Downpayment", self)
        addDownpaymentAction.triggered.connect(lambda: self.addDownpayments(OPEN_NEW))

        addOtherChargeAction = QAction("Other Charges", self)
        addOtherChargeAction.triggered.connect(lambda : self.addOtherCharges(OPEN_NEW))

        editInvoiceAction = QAction("Edit Invoices", self)
        editInvoiceAction.triggered.connect(lambda: self.addInvoice(PAYABLES_TYPE_ALL, OPEN_EDIT))

        addPaymentAction = QAction("New Payment", self)
        addPaymentAction.triggered.connect(lambda: self.addPayment(OPEN_NEW))

        editPaymentAction = QAction("Edit Payment", self)
        editPaymentAction.triggered.connect(lambda: self.addPayment(OPEN_EDIT))

        addLocationAction = QAction("New Location", self)
        addLocationAction.setObjectName("locations")
        addLocationAction.triggered.connect(lambda : self.addItem(addLocationAction))

        editLocationAction = QAction("Edit Locations", self)
        editLocationAction.setObjectName("Edit_locations")
        editLocationAction.triggered.connect(lambda: self.addItem(editLocationAction))

        addPlayerAction = QAction("AddPlayer", self)
        addPlayerAction.setObjectName("contactplayer")
        addPlayerAction.triggered.connect(lambda : self.addItem(addPlayerAction))

        addBusterAction = QAction("Add Buster", self)
        addBusterAction.triggered.connect(lambda : self.addItem(addBusterAction))

        baseIndexAction = QAction(QIcon(":Icons8/Accounts/Index.png"), "Set Base Index", self)
        baseIndexAction.setToolTip("Update Cost Index value")
        baseIndexAction.setEnabled(True)
        baseIndexAction.triggered.connect(lambda: self.setIndex(INDEX_NEW))

        updateIndexAction = QAction(QIcon(":Icons8/Accounts/Index.png"), "Update Index", self)
        updateIndexAction.setToolTip("Update Cost Index value")
        updateIndexAction.setEnabled(True)
        updateIndexAction.triggered.connect(lambda: self.setIndex(INDEX_UPGRADE))

        editIndexAction = QAction("Edit Index", self)

        editOtherChargeAction = QAction("Other Charges", self)
        editOtherChargeAction.triggered.connect(lambda: self.editPayables(PAYABLES_TYPE_OTHER))

        editDownpaymentAction = QAction("Downpayments", self)
        editDownpaymentAction.triggered.connect(lambda: self.editPayables(PAYABLES_TYPE_DOWNPAYMENT))

        editBoardAction = QAction("Board Charges", self)
        editBoardAction.triggered.connect(lambda: self.editPayables(PAYABLES_TYPE_BOARD))

        editAllChargesAction = QAction("All Charges", self)
        editAllChargesAction.triggered.connect(lambda: self.editPayables(PAYABLES_TYPE_ALL))

        editSaleAction = QAction("Sale Charges", self)
        editSaleAction.triggered.connect(lambda: self.editPayables(PAYABLES_TYPE_SALE))

        editHalfBreakAction = QAction("Half Break Charges", self)
        editHalfBreakAction.triggered.connect(lambda: self.editPayables(PAYABLES_TYPE_HALF_BREAK))

        editFullBreakAction = QAction("Board Charges", self)
        editFullBreakAction.triggered.connect(lambda: self.editPayables(PAYABLES_TYPE_FULL_BREAK))

        printInvoiceAction = QAction("Print Invoices", self)
        printInvoiceAction.triggered.connect(lambda:self.printAccountDocument(ACCOUNT_INVOICE))

        printPaymentAction = QAction("Print Payment", self)
        printPaymentAction.triggered.connect(lambda:self.printAccountDocument(ACCOUNT_PAYMENT))

        printAccountAction = QAction("Print Account", self)
        printAccountAction.triggered.connect(lambda:self.printAccountDocument(ACCOUNT_ALL))

        printHorseBalanceAction = QAction("Horse Account", self)
        printHorseBalanceAction.triggered.connect(lambda : self.printAccountDocument(ACCOUNT_HORSE_BALANCE))

        supplierMenu = QMenuBar(self)

        locationsMenu = supplierMenu.addMenu("Locations")
        locationsMenu.addAction(addLocationAction)
        locationsMenu.addAction(editLocationAction)

        transferMenu = supplierMenu.addMenu("Transfers")
        transferMenu.addAction(addTransferAction)
        transferMenu.addAction(editTransferAction)

        billingMenu = supplierMenu.addMenu('Charges')
        billingMenu.addAction(addBoardAction)
        billingMenu.addAction(addDownpaymentAction)
        billingMenu.addAction(addOtherChargeAction)
        billingMenu.addSeparator()
        editBillingMenu = billingMenu.addMenu('Edit')
        editBillingMenu.addAction(editAllChargesAction)
        editBillingMenu.addAction(editBoardAction)
        editBillingMenu.addAction(editDownpaymentAction)
        editBillingMenu.addAction(editOtherChargeAction)
        editBillingMenu.addAction(editSaleAction)
        editBillingMenu.addAction(editHalfBreakAction)
        editBillingMenu.addAction(editFullBreakAction)

        invoicesMenu = supplierMenu.addMenu("Billing")
        invoicesMenu.addAction(addInvoiceAllPaymentAction)
        invoicesMenu.addAction(addInvoiceDownPaymentAction)
        invoicesMenu.addAction(addInvoiceBoardPaymentAction)
        invoicesMenu.addAction(addInvoiceHalfBreakPaymentAction)
        invoicesMenu.addAction(addInvoiceBreakFinalPaymentAction)
        invoicesMenu.addAction(addInvoiceSalePaymentAction)
        invoicesMenu.addAction(addInvoiceOtherPaymentAction)
        invoicesMenu.addAction(editInvoiceAction)

        paymentsMenu = supplierMenu.addMenu('Payments')
        paymentsMenu.addAction(addPaymentAction)
        paymentsMenu.addAction(editPaymentAction)

        accountMenu = supplierMenu.addMenu("Account")

        contactsMenu = supplierMenu.addMenu("Contacts")
        contactsMenu.addAction(addPlayerAction)
        contactsMenu.addAction(addBusterAction)

        costIndexMenu = supplierMenu.addMenu("Cost Index")
        costIndexMenu.addAction(baseIndexAction)
        costIndexMenu.addAction(updateIndexAction)
        costIndexMenu.addAction(editIndexAction)

        printingMenu = supplierMenu.addMenu("Print")
        printingMenu.addAction(printInvoiceAction)
        printingMenu.addAction(printPaymentAction)
        printingMenu.addAction(printAccountAction)
        printingMenu.addAction(printHorseBalanceAction)
        return supplierMenu

    @pyqtSlot()
    def printAccountDocument(self, documentType):
        try:
            doc = AvailableDocuments(self.db, documentType, self.supplierId, self)
            doc.show()
            doc.exec()
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print("Supplier: printAccountDocument", err.args)

    @pyqtSlot()
    def setIndex(self, mode):
        try:
            cix = CostIndex(self.db, QDate.currentDate(), self.supplierId,
                            supplierName=self.windowTitle(), mode=mode)
            cix.show()
            cix.exec()
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print(type(err), err.args)

    def getBusters(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("""SELECT c.id, c.fullname 
                            FROM contacts c
                            WHERE c.breaker AND c.active AND 
                            NOT EXISTS (SELECT cb.personid 
                                FROM contactbusters cb
                                WHERE cb.personid = c.id 
                                AND cb.active )
                            ORDER BY c.fullname""")
            if qry.lastError().type() != 0:
                raise DataError("getPlayers", qry.lastError().text())
            return qry
        except DataError as err:
            print("getPoloPlayers", err.args)

    def getSupplier(self):
        try:
            qry = QSqlQuery(self.db)
            qry.prepare("""SELECT id,
                    fullname,
                     playerseller,
                     horsebreaker
                     FROM contacts
                     WHERE id = ?""")
            qry.addBindValue(QVariant(self.supplierId))
            qry.exec()
            if qry.size() == -1:
                raise DataError("Supplier: getSupplier", qry.lastError().text())
            qry.first()
            supplier = qry.value(1)
            if qry.value(2) == True:
                self.players = True
            if qry.value(3):
                self.busters = True
            return supplier
        except DataError as err:
            print("getSupplier", err.args)

    @pyqtSlot()
    def saveAndClose(self):
        try:
            #"Determine if the player/buster exists as inactive"
            qry = QSqlQuery(self.db)
            sql_look = """SELECT id FROM contactplayers""" if self.type == CONTACT_POLO_PLAYER \
                else """SELECT id FROM contactbusters"""
            sql_look += """ WHERE NOT active 
                    AND contactid = ? 
                    AND personid = ?"""
            qry.prepare(sql_look)
            qry.addBindValue(QVariant(self.supplierId))
            self.combo.setModelColumn(0)
            qry.addBindValue(QVariant(self.combo.currentText()))
            qry.exec()
            if qry.size() > 0:
                sql_qry = """UPDATE contactPlayers """ if self.type  == CONTACT_POLO_PLAYER else \
                        """UPDATE contactbusters """
                sql_qry += """SET active = 1
                        WHERE contactid = ? 
                        AND personid = ? """
                qry.prepare(sql_qry)
            else:
                sql_qry = "INSERT INTO contactplayers " \
                if self.type == CONTACT_POLO_PLAYER else "INSERT INTO contactbusters "
            qry.prepare(sql_qry + "(contactid, personid) VALUES (?, ?)")
            qry.addBindValue(QVariant(self.supplierId))
            qry.addBindValue(QVariant(self.combo.currentText()))
            qry.exec()
            if qry.lastError().type() != 0:
                raise DataError('SaveAndClose', qry.lastError().text())
            self.combo.setModelColumn(1)
            self.close()
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def checkPerson(self, type=None):
        self.sender().model().query().seek(-1)
        if type == CONTACT_POLO_PLAYER:
            row = self.listPlayers.currentIndex().row()
            self.listPlayers.model().query().seek(row)
            record = self.listPlayers.model().query().record()
        elif type == CONTACT_BUSTER:
            row = self.listBusters.currentIndex().row()
            self.listBusters.model().query().seek(row)
            record = self.listBusters.model().query().record()
        else:
            row = self.listLocations.currentIndex().row()
            self.listLocations.model().query().seek(row)
            record = self.listLocations.model().query().record()
        msg = QMessageBox()
        msg.setText("Delete or Edit {}?".format(record.value(1)))
        msg.setWindowTitle("Choose an option")
        editButton = msg.addButton("Edit", QMessageBox.ActionRole)
        deleteButton = msg.addButton("Delete",QMessageBox.ActionRole)
        msg.addButton(QMessageBox.Cancel)
        res = msg.exec()
        if self.sender().objectName() != 'locations':
            if msg.clickedButton() == editButton:
                res = Contacts(self.db, fullname=record.value(1),mode=OPEN_EDIT_ONE,contactid=record.value(0))
                res.show()
                res.exec()
            elif msg.clickedButton() == deleteButton:
                self.deleteItem()
            else:
                msg.close()
        else:
            if msg.clickedButton() == editButton:
                res = Location(self.db,self.supplierId, record=record,parent=self, mode=OPEN_EDIT_ONE)
                res.show()
                res.exec()
            elif msg.clickedButton() == deleteButton:
                self.deleteItem()
            else:
                msg.close()

    @pyqtSlot(QPoint)
    def contextMenu(self, pos):
        try:
            object = self.sender()
            object.model().query().seek(-1)
            row = object.currentIndex().row()
            object.model().query().seek(row)
            record = object.model().query().record()
            data = (record, object)
            table = object.objectName()
            px = object.pos()

            inactivateAction = QAction("Desactivate {} from {}".format(record.value(1),
                                                                       self.windowTitle()), self)
            inactivateAction.triggered.connect(lambda: self.inactivateItem(data))

            deleteAction = QAction("Delete {} from {}".format(record.value(1),
                                                              self.windowTitle()), self)
            deleteAction.triggered.connect(lambda: self.deleteItem(data))

            addAction = QAction("Add to {}".format(self.windowTitle()), self)
            addAction.triggered.connect(lambda: self.addItem(object))

            closeAction = QAction("Close Menu", self)
            closeAction.triggered.connect(self.closeMenu)

            menu = QMenu(self)
            menu.addAction(addAction)
            menu.addAction(inactivateAction)
            menu.addAction(deleteAction)
            menu.addAction(closeAction)
            menu.show()
            pos = self.mapToGlobal(px)
            menu.move(pos)
            if row == -1:
                deleteAction.setEnabled(False)
                inactivateAction.setEnabled(False)
        except Exception as err:
            print('ContextMenu', type(err).__name__, err.args)

    @pyqtSlot()
    def addItem(self, object):
        try:
            if object.objectName().find('locations') < 0:
                type = CONTACT_POLO_PLAYER if object.objectName() == 'contactplayers' else CONTACT_BUSTER
                res = Supplier(self.db,self.supplierId,type)
                res.show()
                res.exec()
            elif object.objectName() == 'locations':
                res = Location(self.db, self.supplierId, parent=self)
                res.show()
                res.exec()
            elif object.objectName() == 'Edit_locations':
                res = Location(self.db, self.supplierId, parent=self, mode=OPEN_EDIT)
                res.show()
                res.exec()

            self.updateListView(object)
        except Exception as err:
            print("addItem", err)

    def updateListView(self, object):
        try:
            qryPlayer, qryBuster, qryLocations = self.getSupplierData()
            if object.objectName() == 'contactplayers':
                self.listPlayers.model().setQuery(qryPlayer)
            elif object.objectName() == 'contactbusters':
                self.listBusters.model().setQuery(qryBuster)
            elif object.objectName().find('locations') > 0:
                self.listLocations.model().setQuery(qryLocations)
        except AttributeError as err:
            print("UpdateListView",err.args)

    @pyqtSlot()
    def deleteItem(self, data= None):
        try:
            if data is None:
                object = self.sender()
                object.model().query().seek(-1)
                row = object.currentIndex().row()
                object.model().query().seek(row)
                record = object.model().query().record()
                data = (record, object)

            res = QMessageBox.warning(self, "Delete", "Do you want to delete {}".format(
                data[0].value(1)), QMessageBox.Yes | QMessageBox.No)
            if res == QMessageBox.No:
                return
            table = data[1].objectName()
            qry = QSqlQuery(self.db)
            if table != 'locations':
                qry.prepare("""
                        DELETE FROM """ + table + """ 
                        WHERE personid = ? 
                        AND contactid = ? ;""")
                qry.addBindValue(QVariant(data[0].value(0)))
                qry.addBindValue(QVariant(self.supplierId))
                qry.exec()
            else:
                qry.prepare(""" DELETE FROM """ + table + """
                    WHERE id = ?""")
                qry.addBindValue(QVariant(data[0].value(0)))
                qry.exec()
            if qry.lastError().type() != 0:
                raise DataError('Supplier: deleteItem', qry.lastError().text())
            self.updateListView(data[1])

        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def inactivateItem(self, data):
        try:
            res = QMessageBox.question(self, "Inactivate", "Do you want to inactivate {}".format(
                data[0].value(1)),QMessageBox.Yes|QMessageBox.No)
            if res == QMessageBox.No:
                return
            table = data[1].objectName()
            qry = QSqlQuery(self.db)
            if table != 'locations':
                qry.prepare("""
                        UPDATE """ + table + """
                        SET active = False
                        WHERE personid = ? 
                        AND contactid = ? ;""")
                qry.addBindValue(QVariant(data[0].value(0)))
                qry.addBindValue(QVariant(self.supplierId))
            else:
                qry.prepare("""
                        UPDATE """ + table + """
                        SET active = False 
                        WHERE id = ?""")
                qry.addBindValue(QVariant(data[0].value(0)))
            qry.exec()
            if qry.lastError().type() != 0 :
                raise DataError('inactivateItem', qry.lastError.text())
            self.updateListView(data[1])

        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def closeMenu(self):
        pass

    def getPlayerBuster(self):
        try:
            qry = QSqlQuery(self.db)
            qry.prepare("""
                SELECT playerseller, horsebreaker 
                FROM contacts 
                WHERE id = ?""")
            qry.addBindValue(QVariant(self.supplierId))
            qry.exec()
            qry.first()
            return qry.value(0), qry.value(1)
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def addTransfer(self):
        res = Transfer(self.db, self.supplierId, con_string= self.parent.con_string, parent=self)
        res.show()
        res.exec()

    @pyqtSlot()
    def editTransfer(self):
        res = Transfer(self.db, self.supplierId, mode=OPEN_EDIT, parent=self.parent)
        res.show()
        res.exec()

    @pyqtSlot()
    def addInvoice(self, payableType,mode):
        try:
            res = Invoice(self.db, self.supplierId, payableType,mode=mode,
                      con_string = self.parent.con_string, parent=self.parent )
            res.show()
            res.exec()
        except DataError as err:
            QMessageBox.warning(self, err.source, err.message, QMessageBox.Ok)
            print(err.source, err.message)

    @pyqtSlot()
    def addPayment(self, mode):
        try:
            res = Payment(self.db, self.supplierId, mode,parent=self.parent)
            res.show()
            res.exec()
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print(type(err), err.args)

    @pyqtSlot()
    def addPayables(self,openMode):
        try:
            res = Payables(self.db, self.supplierId, mode=openMode, parent=self.parent)
            res.show()
            res.exec()
        except DataError as err:
            QMessageBox.warning(self, err.source, err.message)
            print(err.source, err.message)
        except Exception as err:
            print('addPayables',type(err).__name__, err.args)

    @pyqtSlot()
    def editPayables(self, payableType):
        try:
            res = EditPayables(self.db, self.supplierId, payableType=payableType, parent=self.parent)
            res.show()
            res.exec()
        except DataError as err:
            QMessageBox.warning(self, err.source, err.message)
            print(err.source, err.message)
        except Exception as err:
            print('Supplier; editPayables', type(err).__name__, err.args)

    def addDownpayments(self, openMode):
        try:
            res = Downpayments(self.db, self.supplierId, parent=self.parent)
            res.show()
            res.exec()
        except DataError as err:
            QMessageBox.warning(self, err.source, err.message)
            print(err.source, err.message)
        except Exception as err:
            print('addDownpayments',type(err).__name__, err.args)

    def addOtherCharges(self, mode):
        try:
            res = OtherCharge(self.db,self.supplierId, mode,parent=self.parent)
            res.show()
            res.exec()

        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print('addOtherCharges',type(err).__name__, err.args)

class Contacts(QDialog):

    def __init__(self, db, fullname=None, mode=OPEN_NEW, contactid = None, parent=None):
        super().__init__()
        self.parent = parent
        self.db = db
        if not self.db.isOpen():
            self.db.open()
        self.fullname = fullname
        self.contactid = contactid
        self.setModal(True)
        self.mode = mode
        self.setUI()

    def setUI(self):
        self.setMinimumWidth(600)
        lblName = QLabel("Fullname")
        self.lineName = QLineEdit()
        self.lineName.setToolTip("Lastname, Firstname")
        self.lineName.editingFinished.connect(self.checkFullname)

        lblAddress = QLabel('Address:')
        self.textAddress = QPlainTextEdit()
        self.textAddress.setToolTip("Contact Address")
        self.textAddress.setTabStopWidth(33)

        lblPhone = QLabel('Telephone')
        self.linePhone = QLineEdit()
        self.linePhone.setToolTip("Contact telephone")
        self.linePhone.setMaximumWidth(250)
        self.linePhone.editingFinished.connect(self.enableSave)

        rx = EMAILREGEXP
        lblEmail = QLabel('Email')
        self.lineEmail = LineEditHover()
        self.lineEmail.setToolTip("Contact Email address")
        self.lineEmail.setMaximumWidth(250)
        self.lineEmail.setRegExpValidator(rx)
        self.lineEmail.editingFinished.connect(self.enableSave)

        self.checkPlayer = QCheckBox("Polo Seller")
        self.checkPlayer.setToolTip("Horse maker and seller")
        self.checkPlayer.stateChanged.connect(self.enableSave)

        self.checkBreaker = QCheckBox("Horse Breaker")
        self.checkBreaker.setToolTip("Horse Breaker")
        self.checkBreaker.stateChanged.connect(self.enableSave)

        self.checkBuyer = QCheckBox("Horse Buyer")
        self.checkBuyer.setToolTip("Horse Buyer")
        self.checkBuyer.stateChanged.connect(self.enableSave)

        self.checkDealer = QCheckBox("Horse Dealer")
        self.checkDealer.setToolTip("Horses' Sale Dealer")
        self.checkDealer.stateChanged.connect(self.enableSave)

        self.checkResponsible = QCheckBox("Manager")
        self.checkResponsible.setToolTip("Farm Responsible")
        self.checkResponsible.stateChanged.connect(self.enableSave)

        self.checkActualBreaker = QCheckBox("Buster")
        self.checkActualBreaker.setToolTip("Actual Horse Buster")
        self.checkActualBreaker.stateChanged.connect(self.enableSave)

        self.checkActualPlayer = QCheckBox("Player")
        self.checkActualPlayer.setToolTip("Actual Polo Player")
        self.checkActualPlayer.stateChanged.connect(self.enableSave)

        self.checkVeterinary = QCheckBox('Veterinary')
        self.checkVeterinary.setToolTip('Acting Veterinary')
        self.checkVeterinary.stateChanged.connect(self.enableSave)

        self.checkDriver = QCheckBox("Driver")
        self.checkDriver.setToolTip("Horse transfer driver")
        self.checkDriver.stateChanged.connect(self.enableSave)

        self.checkActive = QCheckBox("Active")
        self.checkActive.setToolTip("Weather the contact is active")
        self.checkActive.setChecked(True)
        self.checkActive.stateChanged.connect(self.enableSave)

        self.pushSave = QPushButton("Save")
        self.pushSave.setMaximumWidth(60)
        self.pushSave.setEnabled(False)
        self.pushSave.clicked.connect(self.saveAndClose)

        pushCancel = QPushButton("Cancel")
        pushCancel.setMaximumWidth(60)
        pushCancel.clicked.connect(self.close)
        pushCancel.setFocus()

        hLayoutTop = QHBoxLayout()
        hLayoutTop.addWidget(lblName)
        hLayoutTop.addWidget(self.lineName)

        gLayoutAddress = QGridLayout()
        gLayoutAddress.addWidget(lblAddress, 0, 0)
        gLayoutAddress.addWidget(self.textAddress, 0, 1, 2, 2)
        gLayoutAddress.addWidget(lblPhone, 0,3)
        gLayoutAddress.addWidget(self.linePhone, 0, 4)
        gLayoutAddress.addWidget(lblEmail,1,3)
        gLayoutAddress.addWidget(self.lineEmail, 1,4)
        #gLayoutAddress.addWidget(self.checkActive,2,2)

        hLayoutType = QHBoxLayout()
        hLayoutType.addSpacing(100)
        hLayoutType.addWidget(self.checkPlayer)
        hLayoutType.addWidget(self.checkBreaker)

        hLayoutActual = QHBoxLayout()
        hLayoutActual.addSpacing(100)
        hLayoutActual.addWidget(self.checkActualPlayer)
        hLayoutActual.addWidget(self.checkActualBreaker)

        hLayoutSale = QHBoxLayout()
        hLayoutSale.addSpacing(100)
        hLayoutSale.addWidget(self.checkBuyer)
        hLayoutSale.addWidget(self.checkDealer)

        hLayoutBottom = QHBoxLayout()
        hLayoutBottom.addSpacing(100)
        hLayoutBottom.addWidget(self.checkResponsible)
        hLayoutBottom.addWidget(self.checkVeterinary)

        hLayoutActive = QHBoxLayout()
        hLayoutActive.addSpacing(100)
        hLayoutActive.addWidget(self.checkDriver)
        hLayoutActive.addWidget(self.checkActive)

        hLayoutButtons = QHBoxLayout()
        hLayoutButtons.addSpacing(400)
        hLayoutButtons.addWidget(pushCancel)
        hLayoutButtons.addWidget(self.pushSave)
        if self.mode != OPEN_NEW:
            self.pushDelete = QPushButton("Delete")
            self.pushDelete.setMaximumWidth(60)
            self.pushDelete.clicked.connect(self.deleteContact)
            hLayoutButtons.insertWidget(2, self.pushDelete)

        vLayout = QVBoxLayout()
        vLayout.addLayout(hLayoutTop)
        vLayout.addLayout(gLayoutAddress)
        vLayout.addLayout(hLayoutType)
        vLayout.addLayout(hLayoutActual)
        vLayout.addLayout(hLayoutSale)
        vLayout.addLayout(hLayoutBottom)
        vLayout.addLayout(hLayoutActive)
        vLayout.addSpacing(20)
        if self.mode == OPEN_EDIT:
            try:
                self.setMinimumWidth(850)
                colDict = {
                    0: ("ID", True, True, True, None),
                    1: ("Contact", False, False, False, None),
                    2: ("Play", False, True, True, None),
                    3: ("Break", False, True, True, None),
                    4: ("Player", False, True, True, None),
                    5: ("Buster", False, True, True, None),
                    6: ("Checker", False, True, True, None),
                    7: ("Buyer", False, True, True, None),
                    8: ("Dealer", False, True, True, None),
                    9: ("Veterinay", False, True, True, None),
                    10: ("Active", True, True, True, None),
                    11: ("Address", True, True, False, None),
                    12: ("Telephone", True, True, False, None),
                    13: ("EMail", True, True, False, None),
                    14: ("Driver", False, True, True, None)}
                colorDict = {
                }
                qry = self.getContactsQuery()
                self.tableContacts = TableViewAndModel(colDict, colorDict,(500, 100),qry)
                self.tableContacts.verticalHeader().setVisible(False)
                self.tableContacts.doubleClicked.connect(self.getContactData)
                hLayoutButtons.insertStretch(0,5)
                vLayout.addWidget(self.tableContacts)
            except DataError as err:
                print(type(err).__name__, err.args)
                res = QMessageBox.warning(self, err.args[0],err.args[1])
                sys.exit()
            except Exception as err:
                print(type(err).__name__, err.args)
        elif self.mode == OPEN_EDIT_ONE:
            self.loadContact()
        vLayout.addLayout(hLayoutButtons)

        self.setLayout(vLayout)
        self.setWindowTitle("New Contact" if self.mode == OPEN_NEW else "Edit Contact:")
        self.tableContacts.setFocus() if self.mode == OPEN_EDIT else self.lineName.setFocus()

    @pyqtSlot()
    def getContactData(self):
        row = self.tableContacts.currentIndex().row()
        self.tableContacts.model().query().seek(row)
        record = self.tableContacts.model().query().record()
        try:
            res = QMessageBox.question(self,"Edit Contact", "Do you want to edit {}´data.\n Check data and edit it "
                                            " as necessary".format(record.value(1)))
            if res != QMessageBox.Yes:
                self.contactid = None
                self.lineName.clear()
                self.checkPlayer.setChecked(False)
                self.checkBreaker.setChecked(False)
                self.checkResponsible.setChecked(False)
                self.checkBuyer.setChecked(False)
                self.checkDealer.setChecked(False)
                self.checkVeterinary.setCheck(False)
                self.checkActive.setChecked(True)
                self.checkDriver.setChecked(False)
                self.pushSave.setEnabled(False)
                self.setWindowTitle("Edit Contact:")

                return
            self.setWindowTitle("Edit Contact: {}".format(record.value(1)))
            self.contactid = record.value(0)
            self.lineName.setText(record.value(1))
            self.checkPlayer.setChecked(True if record.value(2) == u'\u2714' else False)
            self.checkBreaker.setChecked(True if record.value(3) == u'\u2714' else False)
            self.checkActualBreaker.setChecked(True if record.value(4) == u'\u2714' else False)
            self.checkActualPlayer.setChecked(True if record.value(5)== u'\u2714' else False)
            self.checkResponsible.setChecked(True if record.value(6) == u'\u2714' else False)
            self.checkBuyer.setChecked(True if record.value(7) == u'\u2714' else False)
            self.checkDealer.setChecked(True if record.value(8) == u'\u2714' else False)
            self.checkVeterinary.setChecked(True if record.value(9) == u'\u2714' else False)
            self.checkActive.setChecked(True if record.value(10) == u'\u2714' else False)
            self.setWindowTitle("Edit Contact: '" + record.value(1) + "'")
            self.textAddress.setPlainText(record.value(11))
            self.linePhone.setText(record.value(12))
            self.lineEmail.setText(record.value(13))
            self.checkDriver.setChecked(True if record.value(14) == u'\u2714' else False)
        except Exception as err:
            print(type(err).__name__, err.args)

    def getContactsQuery(self):
        with Cdatabase(self.db, 'xdb') as xdb:
            qry = QSqlQuery(xdb)
            qry.exec("""SELECT
            id, 
            fullname, 
            If (playerseller = 1, _ucs2 X'2714', ''), 
            if(horsebreaker = 1, _ucs2 X'2714', ''), 
            if (breaker = 1, _ucs2 x'2714', ''),
            if (player = 1, _ucs2 x'2714', ''),
            if(responsible = 1, _ucs2 X'2714', ''),
            if(buyer = 1,_ucs2 X'2714', ''), 
            if(dealer = 1,_ucs2 X'2714', ''),
            if (veterinary = 1, _ucs2 x'2714', ''), 
            if(active = 1, _ucs2 X'2714', ''),
            address,
            telephone,
            email,
            if(driver = 1, _ucs2 x'2714', '')
            FROM contacts
            ORDER BY fullname""")
        return qry

    @pyqtSlot()
    def enableSave(self):
        send_object = self.sender()
        if isinstance(send_object, QPushButton):
            return
        if self.mode == OPEN_EDIT and self.contactid is None:
            QMessageBox.warning(self, "Wrong Mode", "Cannot save a new contact in the edit form!", )
            self.pushSave.setEnabled(False)
            if isinstance(send_object, QLineEdit):
                send_object.clear()
                self.textAddress.clear()
            elif isinstance(send_object, QCheckBox):
                if send_object == self.checkActive:
                    self.checkActive.setChecked(True)
                else:
                    send_object.setChecked(False)
            return

        if len(self.lineName.text()) > 0 :
            self.pushSave.setEnabled(True)

    @pyqtSlot()
    def checkFullname(self):
        try:
            if len(self.lineName.text()) > 0:
                self.lineName.text().index(",")
            self.lineName.setText(self.lineName.text().title())
        except ValueError as err:
            msgBox = QMessageBox()
            msgBox.setText("The customer name '{}' isn't formatted properly".format(self.lineName.text()))
            msgBox.exec()
            #self.lineName.clear()
            self.lineName.setFocus()
            return
        if self.mode == OPEN_NEW:
            qry = QSqlQuery(self.db)
            #qry = QSqlQuery(self.cdb)
            qry.prepare("""SELECT id FROM contacts 
            WHERE fullname = ?;""")
            qry.addBindValue(QVariant(self.lineName.text()))
            qry.exec_()
            if qry.size() > 0:
                QMessageBox.warning(self, "Duplicate Name",
                                    "The contact '{}' already exists! Use the existing or enter a different name".format(self.lineName.text()))
                self.lineName.clear()
                return
        if self.isVisible():
            self.enableSave()

    def loadContact(self):
        qry = QSqlQuery(self.db)
        qry.prepare("""
        SELECT fullname, playerseller, horsebreaker, buyer,
         dealer, responsible, breaker, player, veterinary, active FROM contacts 
         WHERE id = ?""")
        qry.addBindValue(QVariant(self.contactid))
        try:
            qry.exec_()
            if qry.size() == -1:
                raise ValueError(qry.lastError().text())
            qry.first()
            self.lineName.setText(qry.value(0))
            self.checkPlayer.setChecked(qry.value(1))
            self.checkBreaker.setChecked(qry.value(2))
            self.checkBuyer.setChecked(qry.value(3))
            self.checkDealer.setChecked(qry.value(4))
            self.checkResponsible.setChecked(qry.value(5))
            self.checkActualBreaker.setChecked(qry.value(6))
            self.checkActualPlayer.setChecked(qry.value(7))
            self.checkVeterinary.setChecked(qry.value(8))
            self.checkActive.setChecked(qry.value(9))
        except ValueError as err:
            print(type(err).__name__, err.args)
            return
        except Exception as err:
            print(type(err).__name__, err.args)
            return
        return

    @pyqtSlot()
    def saveAndClose(self):
        qry = QSqlQuery(self.db)
        if self.mode == OPEN_NEW:
            qry.prepare("""
            INSERT INTO contacts
            (fullname,
            address,
            telephone,
            email,
            playerseller,
            horsebreaker,
            buyer,
            dealer,
            responsible,
            breaker,
            player,
            veterinary,
            driver,
            active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""")
        else:
            qry.prepare("""
            UPDATE contacts 
            SET fullname = ?,
            address = ?,
            telephone = ?,
            email = ?,
            playerseller = ?, 
            horsebreaker = ?, 
            buyer = ?, 
            dealer = ?, 
            responsible = ?,
            breaker = ?,
            player = ?,
            veterinary = ?, 
            driver = ?,
            active = ?
            WHERE id = ?""")
        qry.addBindValue(QVariant(self.lineName.text()))
        qry.addBindValue(QVariant(self.textAddress.toPlainText()))
        qry.addBindValue(QVariant(self.linePhone.text()))
        qry.addBindValue(QVariant(self.lineEmail.text()))
        qry.addBindValue(QVariant(self.checkPlayer.isChecked()))
        qry.addBindValue(QVariant(self.checkBreaker.isChecked()))
        qry.addBindValue(QVariant(self.checkBuyer.isChecked()))
        qry.addBindValue(QVariant(self.checkDealer.isChecked()))
        qry.addBindValue(QVariant(self.checkResponsible.isChecked()))
        qry.addBindValue(QVariant(self.checkActualBreaker.isChecked()))
        qry.addBindValue(QVariant(self.checkActualPlayer.isChecked()))
        qry.addBindValue(QVariant(self.checkVeterinary.isChecked()))
        qry.addBindValue(QVariant(self.checkDriver.isChecked()))
        qry.addBindValue(QVariant(self.checkActive.isChecked()))
        if self.mode == OPEN_EDIT:
            qry.addBindValue(QVariant(self.contactid))
        try:
            qry.exec()
            if qry.numRowsAffected() != 1:
                print(qry.lastError().text())
                raise DataError('SaveAndClose',qry.lastError().text())
        except DataError as err:
            print(err.source, err.message)
            return
        except Exception as err:
            print('Save&close', type(err).__name__ , err.args)
            return
        self.close()

    @pyqtSlot()
    def deleteContact(self):
        pass

class ShowContacts(QDialog):
    def __init__(self, db, mode):
        super().__init__()
        self.db = db
        self.type = mode
        self.initUI()
        self.setMinimumSize(600,200)

    def initUI(self):
        pushOK = QPushButton("Close")
        pushOK.setMaximumSize(50, 30)
        pushOK.clicked.connect(self.close)
        colorDict = {'column': (10),
                     '':(QColor('black'), QColor('white'))}
        colDict = {
            0: ('ID', True, True, True, None),
            1: ('Name', False, False, False, None),
            2: ('Play', False, True, True, None),
            3: ('Break', False, True, True, None),
            4: ('Checker', False, True, True, None),
            5: ('Buyer', False, True, True, None ),
            6: ('Dealer', False, True, True, None),
            7: ('Player', False, True, True, None),
            8: ('Buster', False, True, True, None),
            9: ('Vet', False, True, True, None),
            10: ('Active', True, True, True, None)}
        qry = self.getContactsQuery()
        table = TableViewAndModel(colDict, colorDict, (700,200), qry)
        layout = QVBoxLayout()
        hLayout = QHBoxLayout()
        hLayout.addSpacing(500)
        hLayout.addWidget(pushOK)
        layout.addWidget(table)
        layout.addLayout(hLayout)

        self.setLayout(layout)


    def getContactsQuery(self):
        with Cdatabase(self.db, 'show') as showDb:
            qry = QSqlQuery(showDb)
            select = """SELECT
                 id, 
                 fullname, 
                 IF (playerseller = 1, _ucs2 X'2714', ''), 
                 if(horsebreaker = 1, _ucs2 X'2714', ''), 
                 if(responsible = 1, _ucs2 X'2714', ''),
                 if(buyer = 1,_ucs2 X'2714', ''), 
                 if(dealer = 1,_ucs2 X'2714', ''),
                 if (player = 1, _ucs2 x'2714', ''),
                 if (breaker = 1, _ucs2 x'2714', ''),
                 if (veterinary = 1, _ucs2 x'2714', ''), 
                 if(active = 1, _ucs2 X'2714', '')
                 FROM contacts """
            try:
                if self.type == CONTACT_BUYER:
                    where = "WHERE buyer "
                    self.setWindowTitle("Horse Buyers")
                elif self.type == CONTACT_DEALER:
                    where = "WHERE dealer "
                    self.setWindowTitle("Horse Dealers")
                elif self.type == CONTACT_BREAKER:
                    where = "WHERE horsebreaker "
                    self.setWindowTitle("Horse Breakers")
                elif self.type == CONTACT_RESPONSIBLE:
                    where = "WHERE responsible "
                    self.setWindowTitle("Authorized Representative")
                elif self.type == CONTACT_PLAYER:
                    where = "WHERE playerseller "
                    self.setWindowTitle("Polo Player Sellers")
                elif self.type == CONTACT_POLO_PLAYER:
                    where = "WHERE player "
                    self.setWindowTitle("Polo Players")
                elif self.type ==CONTACT_BUSTER:
                    where = "WHERE breaker "
                    self.setWindowTitle('Horse Busters')
                elif self.type == CONTACT_VETERINARY:
                    where = "WHERE veterinary "
                    self.setWindowTitle('Horse Veterinarians')
                qry.prepare(select + where + "ORDER BY fullname")
                qry.exec()
                return qry
            except Exception as err:
                print(type(err).__name__, err.args)


class Location(QDialog):

    def __init__(self, db, supplierId, record=None, parent=None, mode=OPEN_NEW):
        super().__init__()
        self.db = db
        self.supplierId = supplierId
        self.supplier = self.getSupplier()
        self.setModal(True)
        self.locationid = None
        self.name = None
        self.mode = mode
        self.record = record
        self.parent = parent
        self.setObjectName('Locations')
        self.setUI()



    def setUI(self):
        self.setWindowTitle(self.supplier)

        lblLocation = QLabel("Location")
        self.lineLocation = QLineEdit()
        self.lineLocation.editingFinished.connect(lambda : self.checkExistence(self.lineLocation.text()))
        self.lineLocation.editingFinished.connect(self.enableSave)

        lblManager = QLabel("Manager")

        model = QSqlQueryModel()
        model.setQuery(self.getStaff())
        self.comboManager = FocusCombo()
        self.comboManager.setModel(model)
        self.comboManager.setModelColumn(1)
        self.comboManager.setCurrentIndex(-1)
        self.comboManager.activated.connect(self.enableSave)

        lblTelephone = QLabel("Telephone")
        self.lineTelephone = QLineEdit()
        self.lineTelephone.editingFinished.connect(self.enableSave)

        lblAddress = QLabel("Address")
        self.textAddress = FocusPlainTextEdit(self)
        self.textAddress.focusOut.connect(self.enableSave)

        self.checkActive = QCheckBox('Active')
        self.checkActive.setChecked(True)
        self.checkActive.stateChanged.connect(self.enableSave)

        self.checkMain = QCheckBox('Main Location')
        self.checkMain.setChecked(False)
        self.checkMain.stateChanged.connect(lambda : self.checkMainData(self.checkMain.isChecked()))
        self.checkMain.stateChanged.connect(self.enableSave)

        self.checkSystem = QCheckBox('System Location')
        self.checkSystem.setChecked(False)
        self.checkSystem.stateChanged.connect(self.enableSave)


        pushCancel = QPushButton("Cancel")
        pushCancel.setMaximumWidth(70)
        pushCancel.clicked.connect(self.close)

        self.pushSave = QPushButton("Save")
        self.pushSave.setMaximumWidth(70)
        self.pushSave.clicked.connect(self.saveAndClose)
        self.pushSave.setEnabled(False)

        pushLayout = QHBoxLayout()
        if self.mode != OPEN_NEW:
            self.pushDelete = QPushButton("Delete")
            self.pushDelete.setMaximumWidth(70)
            self.pushDelete.clicked.connect(self.deleteLocation)
            self.pushDelete.setEnabled(False)

            #self.loadRecord(self.getData())
            self.pushEdit = QPushButton("Edit")
            self.pushEdit.setMaximumWidth(70)
            self.pushEdit.clicked.connect(lambda: self.enableEdit(True))
            self.enableEdit(False)

            pushLayout.addWidget(self.pushDelete)
            pushLayout.addWidget(self.pushEdit)

        frmLayout = QFormLayout()
        frmLayout.addRow(lblLocation, self.lineLocation)
        frmLayout.addRow(lblManager, self.comboManager)
        frmLayout.addRow(lblTelephone, self.lineTelephone)
        frmLayout.addRow(lblAddress, self.textAddress)

        ckLayout = QHBoxLayout()
        ckLayout.addSpacing(100)
        ckLayout.addWidget(self.checkSystem,Qt.AlignRight)
        ckLayout.addWidget(self.checkMain, Qt.AlignLeft)
        ckLayout.addWidget(self.checkActive,Qt.AlignRight)


        pushLayout.addWidget(pushCancel,Qt.AlignLeft)
        pushLayout.addWidget(self.pushSave,Qt.AlignRight)

        if self.mode == OPEN_EDIT:
            qry = self.getLocations()
            colorDict = {'column':(5),
                u'\u2714':(QColor('yellow'), QColor('red'))}
            colDict = {0:("ID", True, True, True, None),
                       1:("Location", False, False, False, None),
                       2:("Managerid", True, True, True, None),
                       3:("Address", True, True, False, None),
                       4:("Phone", False, True, False, None),
                       5:("MainCode", True, True, False, None),
                       6:("SystemCode", True, True, False, None),
                       7:("ActiveCode", True, True, False, None),
                       8:("Manager", False, True, False, None),
                       9:("main", False, True, True, None),
                       10:("System", False, True, True, None),
                       11:("Active", False, True, True, None)}
            self.tableLocations = TableViewAndModel(colDict, colorDict,(50, 50), qry)
            self.tableLocations.setMinimumWidth(500)
            self.tableLocations.doubleClicked.connect(lambda: self.loadRecord(self.getData()))
            self.tableLocations.setSelectionMode(QAbstractItemView.SingleSelection)


        vLayout = QVBoxLayout()
        vLayout.addLayout(frmLayout)
        vLayout.addLayout(ckLayout)
        if self.mode == OPEN_EDIT:
            vLayout.addWidget(self.tableLocations)
        vLayout.addLayout(pushLayout)
        self.setLayout(vLayout)

        if self.record:
            self.loadRecord(self.record)

    @pyqtSlot()
    def deleteLocation(self):
        try:
            res = QMessageBox.question(self, "Delete Location",
                                       "Do you want to delete location {}?".format(self.record.value(1)),
                                       QMessageBox.Yes|QMessageBox.No)
            if res != QMessageBox.Yes:
                return
            qry = QSqlQuery(self.db)
            qry.prepare("""DELETE FROM locations WHERE id = ?""")
            qry.addBindValue(QVariant(self.record.value(0)))
            qry.exec()
            if qry.lastError().type() != 0:
                raise DataError("Location: deleteLocation", qry.lastQuery().text())
        except DataError as err:
            print(err.source, err.message)

    def getLocations(self):
        try:
            with Cdatabase(self.db, 'getLocations') as db:
                qry = QSqlQuery(db)
                qry.prepare("""SELECT l.id, l.name, l.managerid, l.address,l.telephone, l.main,
                        l.systemlocation, l.active, c.fullname, 
                        if (l.main = 1, _ucs2 x'2714' , ''),
                        if (l.systemlocation = 1, _ucs2 x'2714',''), 
                        if (l.active = 1, _ucs2 x'2714', '')
                        FROM locations l
                        LEFT JOIN contacts c
                        ON l.managerid = c.id
                        WHERE contactid = ?""")
                qry.addBindValue(QVariant(self.supplierId))
                qry.exec()
                if qry.lastError().type() != 0:
                    raise DataError('getLocations', qry.lastError().text())
                return qry
        except DataError as err:
            print(err.source, err.message)

    def getLocationData(self):
        #Delete after checking operation
        try:
            with Cdatabase(self.db, 'getLocationData') as db:
                qry = QSqlQuery(db)
                qry.prepare("""SELECT name, address, managerid, telephone,
                main, active 
                FROM locations
                WHERE id = ?""")
                qry.exec()
                if qry.lastError().type() != 0:
                    raise DataError('getLocationData', qry.lastError().text())

        except DataError as err:
            print(err.source, err.message)

    def getSupplier(self):
        try:
            with Cdatabase(self.db, "getSupplier") as db:
                qry = QSqlQuery(db)
                qry.prepare("""SELECT fullname 
                FROM contacts 
                WHERE id = ? """)
                qry.addBindValue(QVariant(self.supplierId))
                qry.exec()
                if qry.lastError().type() != 0:
                    raise DataError("getSupplier", qry.lastError().text())
                qry.first()
                return qry.value(0)
        except DataError as err:
            print('getSupplier', err.source, err.message)

    def getData(self):
        try:
            row = self.tableLocations.currentIndex().row()
            self.tableLocations.model().query().seek(row)
            return self.tableLocations.model().query().record()

        except Exception as err:
            print('getData', err.args)

    def getStaff(self):
        try:
            with Cdatabase(self.db, "getStaff") as db:
                qry = QSqlQuery(db)
                qry.prepare("""SELECT c.id, c.fullname
                FROM contacts c
                INNER JOIN contactplayers cp
                ON c.id = cp.personid
                WHERE cp.active AND cp.contactid = ?
                UNION DISTINCT
                SELECT c.id, c.fullname 
                FROM contacts c
                INNER JOIN contactbusters cb
                ON c.id = cb.personid
                WHERE cb.active AND cb.contactid = ?
                UNION DISTINCT
                SELECT id, fullname 
                FROM contacts 
                WHERE active AND id = ? 
                ORDER BY fullname""")
                qry.addBindValue(QVariant(self.supplierId))
                qry.addBindValue(QVariant(self.supplierId))
                qry.addBindValue(QVariant(self.supplierId))
                qry.exec()
                if qry.lastError().type() != 0:
                    raise DataError("getStaff", qry.lastError().text())
                return qry
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def enableSave(self):
        sender = self.sender()
        if type(sender) == FocusPlainTextEdit or\
            type(sender) == QLineEdit or\
            type(sender) == FocusCombo or\
            type(sender) == QCheckBox:
            if len(self.lineLocation.text()) and \
                self.comboManager.currentIndex() != -1:
                self.pushSave.setEnabled(True)

    @pyqtSlot()
    def enableEdit(self, option):
        try:
            #if option:
            #    self.tableLocations.selectedIndexes()[0]
            #    self.loadRecord(self.getData())
            self.lineLocation.setEnabled(option)
            self.lineTelephone.setEnabled(option)
            self.textAddress.setEnabled(option)
            self.comboManager.setEnabled(option)
            self.checkActive.setEnabled(option)
            self.checkMain.setEnabled(option)
            self.checkSystem.setEnabled(option)
            self.pushDelete.setEnabled(option)
        except Exception as err:
            pass

    def saveAndClose(self):
        try:
            with Cdatabase(self.db, 'SaveAndClose') as db:
                qry = QSqlQuery(db)
                if self.mode == OPEN_NEW:
                    qry.prepare(""" INSERT INTO locations 
                    (name, contactid, address, managerid, telephone, main, active, systemlocation)
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?)""")
                    qry.addBindValue(QVariant(self.lineLocation.text()))
                    qry.addBindValue((QVariant(self.supplierId)))
                    qry.addBindValue(QVariant(self.textAddress.toPlainText()))
                    self.comboManager.setModelColumn(0)
                    qry.addBindValue(QVariant(self.comboManager.currentText()))
                    self.comboManager.setModelColumn(1)
                    qry.addBindValue(QVariant(self.lineTelephone.text()))
                    qry.addBindValue(QVariant(self.checkMain.isChecked()))
                    qry.addBindValue(QVariant(self.checkActive.isChecked()))
                    qry.addBindValue(QVariant(self.checkSystem.isChecked()))
                    qry.exec()
                    if qry.lastError().type() != 0:
                        raise DataError("SaveAndClose", qry.lastError().text())
                else:
                    self.comboManager.setModelColumn(0)
                    qry.prepare("""UPDATE locations 
                        SET name = ?, address = ?, 
                        managerid = ?, telephone = ?, 
                        main = ?, active = ? , systemlocation = ?
                        WHERE id = ?""")
                    qry.addBindValue(QVariant(self.lineLocation.text()))
                    qry.addBindValue(QVariant(self.textAddress.toPlainText()))
                    qry.addBindValue(QVariant(self.comboManager.currentText()))
                    qry.addBindValue(QVariant(self.lineTelephone.text()))
                    qry.addBindValue(QVariant(self.checkMain.isChecked()))
                    qry.addBindValue(QVariant(self.checkActive.isChecked()))
                    qry.addBindValue(QVariant(self.checkSystem.isChecked()))
                    qry.addBindValue(QVariant(self.record.value(0)))
                    qry.exec()
                    if qry.lastError().type() != 0:
                        raise DataError("SaveAndClose", qry.lastError().text())
                self.parent.updateListView(self)
                self.close()
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def checkMainData(self, state):
        try:
            if not state:
                return
            with Cdatabase(self.db, 'checkMainData') as db:
                qry = QSqlQuery(db)
                qry.prepare("""SELECT id , name FROM locations 
                        WHERE active 
                        AND main 
                        AND contactid = ?
                        """)
                qry.addBindValue(QVariant(self.supplierId))
                qry.exec()
                if qry.lastError().type() != 0 :
                    raise DataError('checkMainData', qry.lastError().text())
                if qry.size() > 0:
                    qry.first()
                    res = QMessageBox.warning(self,
                        "Existing Main Location", "'{}' already is a the main location for {}".format(qry.value(1),
                        self.supplier),QMessageBox.Ok)
                    self.checkMain.setChecked(False)
                    self.checkMain.setEnabled(False)

        except Exception as err:
            print("checkMainData", err.args)

    @pyqtSlot()
    def checkExistence(self, name):
        try:
            if self.mode != OPEN_NEW:
                return
            with Cdatabase(self.db, "checkExistence") as db:
                qry = QSqlQuery(db)
                qry.prepare("""SELECT id, name, contactid, 
                    address, managerid, telephone, main, active
                    FROM locations 
                    WHERE name = ? 
                    AND contactid = ?""")
                qry.addBindValue(QVariant(name))
                qry.addBindValue(QVariant(self.supplierId))
                qry.exec()
                if qry.lastError().type() != 0 :
                    raise DataError('checkExistence', qry.lastError().text())
                if qry.size() > 0:
                    qry.first()
                    res = QMessageBox.question(self, "Location","An inactive location '{}' is "
                                                                "already on file. Do you want to activate it?".format(
                        qry.value(1)), QMessageBox.Yes | QMessageBox.No)
                    if res == QMessageBox.Yes:
                        self.loadRecord(qry.record())
                self.enableSave()
                return True
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print("CheckExistence", err.args)

    def loadRecord(self, record):
        try:
            if not record:
                self.getData()
                self.lineLocation.setText(record.value(1))
                self.textAddress.setPlainText(record.value(2))
                self.lineTelephone.setText(record.value(4))
                if record.value(5) == u'\u2714':
                    self.checkMain.setChecked(True)
                else:
                    self.checkMain.setChecked(False)
                if record.value(6) == u'\u2714':
                    self.checkActive.setChecked(True)
                else :
                    self.checkActive.setChecked(False)
                self.comboManager.seek(record.value(7), 0)
                self.locationid = record.value(0)
            else:
                self.lineLocation.setText(record.value(1))
                self.textAddress.setPlainText(record.value(3))
                if self.mode == OPEN_EDIT:
                    self.comboManager.setCurrentText(record.value(8))
                else:
                    self.comboManager.setModelColumn(0)
                    self.comboManager.setCurrentText(str(record.value(2)))
                    self.comboManager.setModelColumn(1)
                self.lineTelephone.setText(record.value(4))
                self.checkMain.setChecked(record.value(5))
                self.checkSystem.setChecked(record.value(6))
                self.checkActive.setChecked(record.value(7))
        except Exception as err:
            print('Location: loadRecord', err.args)




