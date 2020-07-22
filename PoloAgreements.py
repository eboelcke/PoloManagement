import sys
import os
import traceback
from struct import Struct

from PyQt5.QtCore import (QVariant, Qt, QDir, QModelIndex,QPoint, QSettings, pyqtSlot,
                            QCoreApplication, QDate)
from PyQt5.QtGui import QColor
from PyQt5.QtSql import (QSqlDatabase,QSqlQueryModel, QSqlQuery)

from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableView, QAction, QFileSystemModel,
            QDockWidget, QAbstractItemView, QTreeView,  QTextEdit, QDialog,
            QFontComboBox, QComboBox, QColorDialog, QMessageBox, QMenu, QFileDialog)
from PyQt5.QtGui import (QFont, QIcon, QTextListFormat, QTextCharFormat,
                         QTextCursor, QImage, QContextMenuEvent)
from PyQt5.QtPrintSupport import QPrintPreviewDialog, QPrintDialog
import pyodbc

from ext import Settings, pushdate, find, wordcount, table, newAgreement, APM
from ext.transfers import Transfer
from ext.APM import TableViewAndModel, DataError
from ext.Printing import InvoicePrint
from ext.Horses import Horses, StartHorse, Mortality, Reject, Sales
from ext.HorseReports import AvailableHorses
from ext.Invoices import Invoice, Payment, Payables, OtherCharge
from ext.Contacts import (Contacts, ShowContacts, ChooseActiveSupplier, Supplier, Location)
from ext.BrokeReceive import ReceiveBroken
from ext.Import import ImportHorses, ImportContacts, ImportLocations
import PoloResource


class QConnectionError(Exception):
    pass


class MainWindow(QMainWindow):
    MAGIC = 'pam\x00'.encode('UTF-8')

    def __init__(self):
        super().__init__()
        self._agreementData = []
        self.changesSaved = True
        self.filename = ""
        self.address = tuple()
        self.qdb = None
        self.con_string = {}
        self.agreementsPath = None
        self.agreementId = None
        self.supplierId = None
        self.isBreaking = None
        self.player = None
        self.buster = None
        self._supplier = None
        self.agreementObjects = None
        self.supplierObjects = None
        if not self.check_connection():
            sys.exit()
        if not self.qdb.isOpen():
            self.qdb.open()
        self.initUI()
        self.dockPayment = self.dockSales = self.dockRejection = self.dockClearance = self.dockBreaking =\
        self.dockMortality = self.dockAgreementHorses = self.dockAccount = self.dockInvoices = None


    def check_connection(self):
        res = QDialog.Rejected
        settings = Settings.SettingsDialog()
        while self.qdb is None:
            okDb, db = settings.connectionTest()
            try:
                self.qdb = QSqlDatabase.cloneDatabase(db, 'qdb')
            except TypeError as err:
                QMessageBox.critical(self, "Server Close", "The Server isn't running!")
            if okDb:
                okServer, message = settings.serverTest()
                if okServer:
                    self.address = settings.serverAddress
                    self.con_string = settings.connectionString
                    self.agreementsPath = settings.agreementsDir
                    return True
                else:
                    res = self.applicationSettings()
                    if res == QDialog.Rejected:
                        self.messageBox("Server not open", "Check the server status and the connection's parameters")
                        sys.exit()
            else:
                res = self.applicationSettings()
                if res == QDialog.Rejected:
                    self.messageBox("Database not open", "Check the database  and the connection's parameters")
            return False

    def initUI(self):
        self.setGeometry(100,100, 1030, 800)
        self.setWindowTitle("Polo Horse Agreements Management")
        self.setWindowIcon(QIcon(":Icons8/Stable.png"))
        f = QFont("Tahoma", 7, QFont.Light)
        fd = QFont("Tahoma", 8, QFont.Light)
        self.text = QTextEdit()
        self.text.setTabStopWidth(33)
        self.text.cursorPositionChanged.connect(self.cursorPosition)
        self.text.textChanged.connect(self.changed)
        self.text.setStyleSheet("QTextEdit.focus {background-color: black;"
                               "color: white}")
        self.text.setEnabled(False)
        self.setCentralWidget(self.text)

        self.initToolBar()
        self.initAccountBar()
        self.initHorseBar()
        self.initPeopleBar()
        self.addToolBarBreak()
        self.initDocumentBar()
        self.addToolBarBreak()
        self.initFormatBar()
        self.initMenuBar()
        self.statusBar = self.statusBar()

        self.treeViewAgr = QTreeView()
        treeModel = self.file_model()
        path = treeModel.rootPath()

        self.dockAgreement = QDockWidget("Agreements", self)
        self.dockAgreement.setObjectName("dockAgreements")
        self.dockAgreement.setAllowedAreas(Qt.LeftDockWidgetArea)
        self.dockAgreement.visibilityChanged.connect(lambda : self.checkDock(
            self.agreementDockAction, self.dockAgreement))

        self.treeViewAgr.setModel(treeModel)
        self.treeViewAgr.setRootIndex(treeModel.index(path))
        self.treeViewAgr.setStyleSheet("QTreeView {font-size: 8pt; font: Times;}")
        self.treeViewAgr.setMinimumWidth(300)
        self.treeViewAgr.setFont(f)
        self.treeViewAgr.setColumnHidden(1, True)
        self.treeViewAgr.setColumnHidden(2, True)
        self.treeViewAgr.setColumnHidden(3, True)
        self.treeViewAgr.setColumnHidden(4, True)
        self.treeViewAgr.doubleClicked.connect(lambda: self.getTreeData(APM.OPEN_FILE))
        self.treeViewAgr.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeViewAgr.customContextMenuRequested.connect(self.openPopDir)

        self.dockAgreement.setWidget(self.treeViewAgr)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dockAgreement)

        self.setMinimumHeight(700)
        self.text.setContextMenuPolicy(Qt.CustomContextMenu)
        self.text.customContextMenuRequested.connect(self.context)

        self.settings = QSettings("config.ini", QSettings.IniFormat)
        if not self.settings.value("geometry") == None:
            self.restoreGeometry(self.settings.value("geometry"))
        if not self.settings.value("windowState") == None:
            self.restoreState(self.settings.value("windowState"))
        self.setFont(fd)

    def initToolBar(self):

        self.newAction = QAction(QIcon(":Icons8/File/addfile.png"), "New", self)
        self.newAction.setStatusTip("Create a new document from scratch.")
        self.newAction.setShortcut("Ctrl+N")
        self.newAction.triggered.connect(self.new)

        self.openAction = QAction(QIcon(":/Icons8/File/openfile.png"), "Open", self)
        self.openAction.setStatusTip("Open existing document.")
        self.openAction.setShortcut("Ctrl+O")
        self.openAction.triggered.connect(self.open)

        self.saveAction = QAction(QIcon(":Icons8/File/save.png"), "Save", self)
        self.saveAction.setStatusTip("Save document")
        self.saveAction.setShortcut("Ctrl+S")
        self.saveAction.triggered.connect(self.save)

        self.saveAsAction = QAction(QIcon(":Icons8/File/saveas.png"), "Save As", self)
        self.saveAsAction.setShortcut("Ctrl + Shift + S")
        self.saveAsAction.triggered.connect(self.saveAs)

        self.deleteFileAction = QAction(QIcon(":/Icons8/File/deletefile.png"), "Delete File", self)
        self.deleteFileAction.setShortcut("Ctrl + Shift + D")
        self.deleteFileAction.triggered.connect(self.deleteFile)

        self.closeAction = QAction(QIcon(":/Icons8/File/closefile.png"),"Close", self)
        self.closeAction.setShortcut("Ctrl + C")
        self.closeAction.triggered.connect(self.closeFile)

        self.openSupplierAction = QAction(QIcon(":/Icons8/Suppliers/Contact.png"), "Open Supplier", self)
        self.openSupplierAction.setStatusTip("Open Service Provider")
        self.openSupplierAction.triggered.connect(self.chooseSupplier)

        self.openAgreementAction = QAction(QIcon(":/Icons8/Agreement/Agreement.png"), "Agreements", self)
        self.openAgreementAction.setStatusTip("Agreement Informaton")
        self.openAgreementAction.triggered.connect(self.prepareAgreementDocks)

        self.addHorseAction = QAction(QIcon(":/Icons8/Horses/newhorse.png"), "Add Horse", self)
        self.addHorseAction.setStatusTip("Increase Horse Inventoru")
        self.addHorseAction.triggered.connect(lambda: self.updateHorseInventory(APM.OPEN_NEW))

        self.editHorseAction = QAction('Edit Horse', self)
        self.editHorseAction.triggered.connect(lambda: self.updateHorseInventory(APM.OPEN_EDIT))

        peopleBarAction = QAction(QIcon(":/Icons8/People/person.png"), "Toggle People Bar", self)
        peopleBarAction.setCheckable(True)
        peopleBarAction.setChecked(True)
        peopleBarAction.triggered.connect(lambda: self.toggleDock(self.peopleToolBar))

        self.toolBar = self.addToolBar("Options")
        self.toolBar.setObjectName('Options')
        self.toolBar.addAction(self.newAction)
        self.toolBar.addAction(self.openAction)
        self.toolBar.addAction(self.saveAction)
        self.toolBar.addAction(self.saveAsAction)
        self.toolBar.addAction(self.deleteFileAction)
        self.toolBar.addAction(self.closeAction)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.openSupplierAction)
        self.toolBar.addAction(self.openAgreementAction)
        self.toolBar.addAction(self.addHorseAction)
        self.toolBar.addAction(peopleBarAction )
        self.toolBar.addSeparator()

    def initDocumentBar(self):
        self.openDocumentAction = QAction(QIcon(":/Icons8/Agreement/document.png"), "Document",self)
        self.openDocumentAction.setToolTip("Toggle Agreement document for editing")
        self.openDocumentAction.setEnabled(False)
        self.openDocumentAction.triggered.connect(self.setDocumentBars)

        self.editAgreementAction = QAction(QIcon(":/Icons8/Edit/EditAgreement.png"), "Edit Agreement", self)
        self.editAgreementAction.setToolTip("Open Agreement for editing")
        self.editAgreementAction.setEnabled(False)
        self.editAgreementAction.triggered.connect(self.editAgreement)

        self.printAction = QAction(QIcon("icons/print.png"), 'Print', self)
        self.printAction.setStatusTip("Print document.")
        self.printAction.setShortcut("Ctrl+P")
        self.printAction.setEnabled(False)
        self.printAction.triggered.connect(self.print)

        self.previewAction = QAction(QIcon("icons/preview.png"), "Preview", self)
        self.previewAction.setStatusTip("Preview document")
        self.previewAction.setShortcut("Ctrl+Shift+P")
        self.previewAction.setEnabled(False)
        self.previewAction.triggered.connect(self.preview)

        self.cutAction = QAction(QIcon("icons/cut.png"), 'Cut', self)
        self.cutAction.setStatusTip("Delete and copy text to clipboard")
        self.cutAction.setShortcut("Ctrl+X")
        self.cutAction.setEnabled(False)
        self.cutAction.triggered.connect(self.text.cut)

        self.copyAction = QAction(QIcon("icons/copy.png"), "Copy", self)
        self.copyAction.setStatusTip("Copy text to clipboard")
        self.copyAction.setShortcut("Ctrl+C")
        self.copyAction.setEnabled(False)
        self.copyAction.triggered.connect(self.text.copy)

        self.pasteAction = QAction(QIcon("icons/paste.png"), "Paste", self)
        self.pasteAction.setStatusTip("Paste into the text cursor")
        self.pasteAction.setShortcut("Ctrl+V")
        self.pasteAction.setEnabled(False)
        self.pasteAction.triggered.connect(self.text.paste)

        self.undoAction = QAction(QIcon("icons/undo.png"), "Undo", self)
        self.undoAction.setStatusTip("Undo last Action")
        self.undoAction.setShortcut("Ctrl+Z")
        self.undoAction.setEnabled(False)
        self.undoAction.triggered.connect(self.text.undo)

        self.redoAction = QAction(QIcon("icons/redo.png"), "Redo, self")
        self.redoAction.setStatusTip("Redo las undo action")
        self.redoAction.setShortcut("Ctrl+Y")
        self.redoAction.setEnabled(False)
        self.redoAction.triggered.connect(self.text.redo)

        self.bulletAction = QAction(QIcon("Icons/bullet.png"), "Bullet list", self)
        self.bulletAction.setStatusTip("Insert bullet list")
        self.bulletAction.setShortcut("Ctrl*B")
        self.bulletAction.setEnabled(False)
        self.bulletAction.triggered.connect(self.bulletList)

        self.numberedAction = QAction(QIcon("icons/number.png"), "Numbered list", self)
        self.numberedAction.setStatusTip("Insert a numbered list")
        self.numberedAction.setShortcut("Ctrl+L")
        self.numberedAction.setEnabled(False)
        self.numberedAction.triggered.connect(self.numberedList)

        self.quitAction = QAction(QIcon("icons/btn_close.png"), "Quit", self)
        self.quitAction.shortcut = "Ctrl+Q"
        self.quitAction.statusTip = "Exits the application"
        self.quitAction.triggered.connect(self.close)

        self.settingsAction = QAction(QIcon("icons/settings.png"), "Settings", self)
        self.settingsAction.setStatusTip("Settings")
        self.settingsAction.setShortcut("Application Settings")
        self.settingsAction.triggered.connect(self.applicationSettings)

        self.deleteAction = QAction(QIcon("icons/delete.png"), "Delete", self)
        self.deleteAction.setStatusTip("Delete selected area")
        self.deleteAction.setShortcut("Ctrl+D")
        self.deleteAction.setEnabled(False)
        self.deleteAction.triggered.connect(self.removeText)

        self.refreshAction = QAction('Refresh', self)
        self.refreshAction.setStatusTip('Refresh the server directory')
        self.refreshAction.triggered.connect(self.refresh)

        self.findAction = QAction(QIcon("icons/find.png"), "Find and Replaced", self)
        self.findAction.setStatusTip("Find and Replace")
        self.findAction.setShortcut("Ctrl+F")
        self.findAction.setEnabled(False)
        self.findAction.triggered.connect(find.Find(self).show)

        self.imageAction = QAction(QIcon("icons/image.png"), "Insert image", self)
        self.imageAction.setStatusTip("Insert and image")
        self.imageAction.setShortcut("Ctrl+Shift+I")
        self.imageAction.triggered.connect(self.insertImage)

        wordCountAction = QAction(QIcon("icons/count.png"), "Words/Characters count", self)
        wordCountAction.setStatusTip("Word/Characteer count")
        wordCountAction.setShortcut("Ctrl+W")
        wordCountAction.triggered.connect(self.wordCount)

        tableAction = QAction(QIcon("icons/table.png"), "Insert Table", self)
        tableAction.setStatusTip("Insert Table")
        tableAction.setShortcut("Ctrl+I")
        tableAction.triggered.connect(table.Table(self).show)

        listAction = QAction("Insert List", self)
        listAction.setStatusTip("Insert a horse list")
        listAction.setShortcut("Ctrl + L")
        listAction.triggered.connect(self.insertList)

        dateTimeAction = QAction(QIcon("icons/calender.png"), "Date and Time", self)
        dateTimeAction.setStatusTip("Insert Date and Time")
        dateTimeAction.setShortcut("Ctrl+D")
        dateTimeAction.triggered.connect(pushdate.DateTime(self).show)

        self.documentBar = self.addToolBar('Documents')
        self.documentBar.setObjectName("Documents")
        self.documentBar.setVisible(False)
        self.documentBar.addAction(self.printAction)
        self.documentBar.addAction(self.previewAction)
        self.documentBar.addSeparator()
        self.documentBar.addAction(self.undoAction)
        self.documentBar.addAction(self.redoAction)
        self.documentBar.addSeparator()
        self.documentBar.addAction(self.pasteAction)
        self.documentBar.addAction(self.cutAction)
        self.documentBar.addAction(self.copyAction)
        self.documentBar.addAction(self.deleteAction)
        self.documentBar.addAction(self.bulletAction)
        self.documentBar.addAction(self.numberedAction)
        self.documentBar.addSeparator()
        self.documentBar.addAction(self.findAction)
        self.documentBar.addAction(self.imageAction)
        self.documentBar.addAction(wordCountAction)
        self.documentBar.addAction(tableAction)
        self.documentBar.addAction(dateTimeAction)

    def initFormatBar(self):

        fontBox = QFontComboBox()
        fontBox.currentFontChanged.connect(self.fontFamily)

        fontSize = QComboBox(self)
        fontSize.setEditable(True)
        fontSize.setMinimumContentsLength(3)

        fontSizes = ['5','6', '7', '8', '9', '10', '11', '12','13', '14',
                     '15', '16', '18', '20', '22', '24','26', '28',
                     '32','36', '40', '44', '48', '54', '60', '66',
                     '72', '80', '88', '96']
        for i in fontSizes:
            fontSize.addItem(i)
        fontSize.activated.connect(self.fontSize)
        fontColor = QAction(QIcon("icons/font-color.png"), "Change Font Color", self)
        fontColor.triggered.connect(self.fontColor)

        backColor = QAction(QIcon("icons/highlight.png"), "Change Background Color", self)
        backColor.triggered.connect(self.highlight)

        boldAction = QAction(QIcon("icons/bold.png"), "Bold", self)
        boldAction.triggered.connect(self.bold)

        italicAction = QAction(QIcon("icons/italic.png"),"Italic", self)
        italicAction.triggered.connect(self.italic)

        underlineAction = QAction(QIcon("Icons/underline.png"), "Underline", self)
        underlineAction.triggered.connect(self.underline)

        strikeAction = QAction(QIcon("icons/strike.png"),"Strike", self)
        strikeAction.triggered.connect(self.strike)

        superAction = QAction(QIcon("icons/superscript.png"), "superscript", self)
        superAction.triggered.connect(self.superScript)

        subAction = QAction(QIcon("icons/subscript.png"), "Subscript", self)
        subAction.triggered.connect(self.subScript)

        alignLeft = QAction(QIcon("icons/align-left.png"), "Align Left", self)
        alignLeft.triggered.connect(self.alignLeft)

        alignCenter= QAction(QIcon("icons/align-center.png"), "Align Center", self)
        alignCenter.triggered.connect(self.alignCenter)

        alignRight = QAction(QIcon("icons/align-right.png"), "Align Right", self)
        alignRight.triggered.connect(self.alignRight)

        alignJustify = QAction(QIcon("icons/align-justify.png"), "Align Justify", self)
        alignJustify.triggered.connect(self.alignJustify)

        indentAction = QAction(QIcon("icons/indent.png"), "Indent Area", self)
        indentAction.setShortcut("Ctrl+Tab")
        indentAction.triggered.connect(self.indent)

        dedentAction = QAction(QIcon("icons/dedent.png"), "Dedent Area", self)
        dedentAction.setShortcut("Shift+Tab")
        dedentAction.triggered.connect(self.dedentArea)

        self.formatBar = self.addToolBar("Format")
        self.formatBar.setObjectName("Format")
        #self.formatBar.setEnabled(False)
        self.formatBar.setVisible(False)

        self.formatBar.addWidget(fontBox)
        self.formatBar.addWidget(fontSize)

        self.formatBar.addSeparator()

        self.formatBar.addAction(fontColor)
        self.formatBar.addAction(backColor)

        self.formatBar.addSeparator()

        self.formatBar.addAction(boldAction)
        self.formatBar.addAction(underlineAction)
        self.formatBar.addAction(italicAction)
        self.formatBar.addAction(strikeAction)
        self.formatBar.addAction(superAction)
        self.formatBar.addAction(subAction)

        self.formatBar.addSeparator()

        self.formatBar.addAction(alignLeft)
        self.formatBar.addAction(alignCenter)
        self.formatBar.addAction(alignRight)
        self.formatBar.addAction(alignJustify)

        self.formatBar.addSeparator()

        self.formatBar.addAction(indentAction)
        self.formatBar.addAction(dedentAction)

    def initAccountBar(self):

        self.accountBar = self.addToolBar('Account')
        self.accountBar.setObjectName("Account")
        self.accountBar.hide()

        billBarAction = QAction(QIcon(":/Icons8/Bills/bills.png"), "Biils", self)
        billBarAction.setStatusTip("Toggles de Charges Bar")
        billBarAction.triggered.connect(self.enableBillBar)

        self.invoiceAction = QAction(QIcon(":/Icons8/Accounts/invoice.png"), "Invoice", self)
        self.invoiceAction.setStatusTip("Receive Invoice")
        self.invoiceAction.triggered.connect(lambda: self.addInvoice(APM.OPEN_NEW))
        self.invoiceAction.setEnabled(True)

        self.paymentAction = QAction(QIcon(":/Icons8/Accounts/cash.png"), 'Payment', self)
        self.paymentAction.setStatusTip("Issue Payment")
        self.paymentAction.triggered.connect(lambda: self.payment(APM.OPEN_NEW))
        self.paymentAction.setEnabled(True)

        self.accountAction = QAction(QIcon(":/Icons8/Accounts/ledger.png"),'Account', self)
        self.accountAction.setStatusTip("Show Agreement Account")
        self.accountAction.triggered.connect(self.account)
        self.accountAction.setEnabled(True)

        self.addTransferAction = QAction(QIcon(":/Icons8/transport.png"),"Transfers", self)
        self.addTransferAction.setStatusTip("Horse Transfers between Locations")
        self.addTransferAction.setObjectName("AddTransfer")
        self.addTransferAction.triggered.connect(lambda: self.transferHorse(APM.OPEN_NEW))

        self.editTransferAction = QAction("Transfers", self)
        self.editTransferAction.setStatusTip("Horse Transfers")
        self.editTransferAction.setObjectName("EditTransfer")
        self.editTransferAction.triggered.connect(lambda: self.transferHorse(APM.OPEN_EDIT))

        self.addInvoiceAction = QAction(QIcon(":/Icons8/Accounts/invoice.png"),"Invoice", self)
        self.addInvoiceAction.setStatusTip("Ads a new Invoice")
        self.addInvoiceAction.triggered.connect(lambda: self.addInvoice(APM.OPEN_NEW))

        self.editInvoiceAction = QAction("Invoices", self)
        self.editInvoiceAction.setStatusTip("Edit/Delete Invoices")
        self.editInvoiceAction.triggered.connect(lambda: self.addInvoice(APM.OPEN_EDIT))

        self.addPaymentAction = QAction(QIcon(":/Icons8/Accounts/cash.png"),"Payment", self)
        self.addPaymentAction.setStatusTip("Add a new payment")
        self.addPaymentAction.triggered.connect(lambda: self.payment(APM.OPEN_NEW))

        self.editPaymentAction = QAction("Payment", self)
        self.editPaymentAction.setStatusTip("Edit/Delete a payment")
        self.editPaymentAction.triggered.connect(lambda: self.payment(APM.OPEN_EDIT))

        self.addLocationAction = QAction(QIcon(":/Icons8/Stable.png"), "Location", self)
        self.addLocationAction.setStatusTip("Adds an operation's location")
        self.addLocationAction.triggered.connect(lambda: self.handleLocations(APM.OPEN_NEW))

        self.supplierDataAction = QAction(QIcon(":/Icons8/Suppliers/SupplierData.png"), "Supplier Data", self)
        self.supplierDataAction.setStatusTip("Accounts and Supplier related data")
        self.supplierDataAction.setEnabled(True)
        self.supplierDataAction.triggered.connect(self.supplierData)

        self.accountBar.addAction(self.invoiceAction)
        self.accountBar.addAction(self.paymentAction)
        #self.accountBar.addAction(self.accountAction)
        self.accountBar.addAction(billBarAction)
        self.accountBar.addSeparator()
        self.accountBar.addAction(self.supplierDataAction)
        self.accountBar.addAction(self.addLocationAction)
        self.accountBar.addAction(self.addTransferAction)

    def initHorseBar(self):
        self.horseBar = self.addToolBar('Horse Management')
        self.horseBar.setObjectName("Management")
        self.horseBar.setVisible(False)

        self.saleAction = QAction(QIcon(":/Icons8/Sales/sales.png"), "Horse Sale", self)
        self.saleAction.setStatusTip("Agreement Horse Sale")
        self.saleAction.triggered.connect(lambda: self.saleHorse(APM.OPEN_NEW))

        self.rejectAction = QAction(QIcon(":/Icons8/Horses/reject.png"), "Reject Horse", self)
        self.rejectAction.setStatusTip("Agreement Horse Rejection")
        self.rejectAction.triggered.connect(lambda: self.rejectHorse(None))

        self.deathAction = QAction(QIcon(":/Icons8/Horses/dead.png"), "Death", self)
        self.deathAction.setStatusTip("Agreement Horse Death")
        self.deathAction.triggered.connect(self.deadHorse)

        self.brokeHorseReceivingAction = QAction(QIcon(":/Icons8/Horses/BrokeHorse.png"),
                                                  "Broke Horse Receiving", self)
        self.brokeHorseReceivingAction.setStatusTip("Receive Broken Horses")
        self.brokeHorseReceivingAction.triggered.connect(lambda:self.brokenHorseReceiving(APM.OPEN_NEW))

        self.horseBar.addAction(self.saleAction)
        self.horseBar.addAction(self.brokeHorseReceivingAction)
        self.horseBar.addAction(self.rejectAction)
        self.horseBar.addAction(self.deathAction)

    def initPeopleBar(self):
        self.newContactAction = QAction(QIcon(":/Icons8/People/addcontact.png"), "New Contact", self)
        self.newContactAction.triggered.connect(lambda: self.contact(APM.OPEN_NEW))

        self.editContactAction = QAction(QIcon(":/Icons8/Edit/EditContact.png"), "Edit Contact", self)
        self.editContactAction.triggered.connect(lambda: self.contact(APM.OPEN_EDIT))

        self.managerAction = QAction(QIcon(":/Icons8/People/manager.png"), "List of Managers", self)
        self.managerAction.triggered.connect(lambda: self.showContacts(APM.CONTACT_RESPONSIBLE))

        self.playerAction = QAction(QIcon(":/Icons8/People/PlayerSeller.png"), "Play And Sale", self)
        self.playerAction.triggered.connect(lambda: self.showContacts(APM.CONTACT_PLAYER))

        self.breakerAction = QAction(QIcon(":/Icons8/Suppliers/coach.png"), "Horse Breaking", self)
        self.breakerAction.triggered.connect(lambda: self.showContacts(APM.CONTACT_BREAKER))

        self.showPoloPlayerAction = QAction(QIcon(":/Icons8/Suppliers/polo.png"), "Polo Players", self)
        self.showPoloPlayerAction.triggered.connect(lambda: self.showContacts(APM.CONTACT_POLO_PLAYER))

        self.addPoloPlayerAction = QAction(QIcon(":Icons8/Suppliers/polo.png"), "Add Polo Player", self)
        self.addPoloPlayerAction.triggered.connect(lambda: self.supplierData(APM.CONTACT_POLO_PLAYER))
        self.addPoloPlayerAction.setEnabled(True)

        self.showBusterAction = QAction(QIcon(":Icons8/People/HorseBreaker.png"), "Horse Busters", self)
        self.showBusterAction.triggered.connect(lambda: self.showContacts(type=APM.CONTACT_BUSTER))

        self.addBusterAction = QAction(QIcon(":Icons8/People/HorseBreaker.png"), "Add Horse Buster", self)
        self.addBusterAction.triggered.connect(lambda: self.supplierData(APM.CONTACT_BUSTER))
        self.addBusterAction.setEnabled(True)

        self.dealerAction = QAction(QIcon(":/Icons8/People/Dealer.png"), "Horse Dealers", self)
        self.dealerAction.triggered.connect(lambda: self.showContacts(APM.CONTACT_DEALER))

        self.buyerAction = QAction(QIcon(":/Icons8/People/farmer.png"), "Horse Buyers", self)
        self.buyerAction.triggered.connect(lambda: self.showContacts(APM.CONTACT_BUYER))

        self.vetAction = QAction(QIcon(":/Icons8/Suppliers/veterinarian.png"), 'Horse Vets', self)
        self.vetAction.triggered.connect(lambda: self.showContacts(APM.CONTACT_VETERINARY))

        self.editLocationAction = QAction("Locations", self)
        self.editLocationAction.triggered.connect(lambda: self.handleLocations(APM.OPEN_EDIT) )

        self.peopleToolBar = self.addToolBar("Contacts")
        self.peopleToolBar.setObjectName("contacts")
        self.peopleToolBar.addAction(self.newContactAction)
        self.peopleToolBar.addAction(self.editContactAction)
        self.peopleToolBar.addAction(self.playerAction)
        self.peopleToolBar.addAction(self.breakerAction)
        self.peopleToolBar.addAction(self.managerAction)
        self.peopleToolBar.addAction(self.buyerAction)
        self.peopleToolBar.addAction(self.dealerAction)
        self.peopleToolBar.addAction(self.showBusterAction)
        self.peopleToolBar.addAction(self.showPoloPlayerAction)
        self.peopleToolBar.setVisible(False)

    def initMenuBar(self):
        menuBar = self.menuBar()

        toolBarAction = QAction("Toggle Toolbar", self)
        toolBarAction.setCheckable(True)
        toolBarAction.setChecked(True)
        toolBarAction.triggered.connect(self.toggleToolBar)

        formatBarAction = QAction("Toggle Format Bar", self)
        formatBarAction.setCheckable(True)
        formatBarAction.setChecked(True)
        formatBarAction.triggered.connect(self.toggleFormatBar)

        accountBarAction = QAction('Toggle Account Bar', self)
        accountBarAction.setCheckable(True)
        accountBarAction.setChecked(True)
        accountBarAction.triggered.connect(lambda: self.toggleDock(self.accountBar))

        statusBarAction = QAction("Toggle Status bar", self)
        statusBarAction.triggered.connect(self.toggleStatusBar)
        statusBarAction.setCheckable(True)
        statusBarAction.setChecked(True)

        horseBarAction = QAction("Toggle Horse Bar", self)
        horseBarAction.setCheckable(True)
        horseBarAction.setChecked(True)
        horseBarAction.triggered.connect(lambda: self.toggleDock(self.horseBar))

        peopleBarAction = QAction("Toggle People Bar", self)
        peopleBarAction.setCheckable(True)
        peopleBarAction.setChecked(True)
        peopleBarAction.triggered.connect(lambda: self.toggleDock(self.peopleToolBar))

        closeAllBarAction = QAction("Close all Bars", self)
        try:
            closeAllBarAction.triggered.connect(lambda: self.closeAllBars([
            self.peopleToolBar, self.statusBar, self.formatBar, self.accountBar, self.horseBar,
            self.toolBar],
            [toolBarAction, formatBarAction, accountBarAction, statusBarAction, horseBarAction, peopleBarAction]))
        except Exception as err:
            print(type(err.__name__, err.args))

        selectAllAction = QAction("Select All")
        selectAllAction.triggered.connect(self.text.selectAll)
        self.agreementDockAction = QAction("Toggle Agreements",self)
        self.agreementDockAction.setCheckable(True)
        self.agreementDockAction.setChecked(True)
        self.agreementDockAction.triggered.connect(lambda :self.toggleDock(
            self.dockAgreement))

        self.agreementHorseDockAction = QAction("Toggle Agreement Horses")
        self.agreementHorseDockAction.setCheckable(True)
        self.agreementHorseDockAction.setChecked(True)
        self.agreementHorseDockAction.triggered.connect(lambda : self.toggleDock(self.dockAgreementHorses))

        self.paymentDockAction = QAction("Toggle payments")
        self.paymentDockAction.setCheckable(True)
        self.paymentDockAction.setChecked(True)
        self.paymentDockAction.triggered.connect(lambda : self.toggleDock(
                self.dockPayment))

        self.invoiceDockAction = QAction("Toggle Invoices")
        self.invoiceDockAction.setCheckable(True)
        self.invoiceDockAction.setChecked(True)
        self.invoiceDockAction.triggered.connect(lambda : self.toggleDock(
            self.dockInvoices))

        self.accountDockAction = QAction("Toggle Account")
        self.accountDockAction.setCheckable(True)
        self.accountDockAction.setChecked(True)
        self.accountDockAction.triggered.connect(lambda : self.toggleDock(
            self.dockAccount))

        self.salesDockAction = QAction("Toggle Sales")
        self.salesDockAction.setCheckable(True)
        self.salesDockAction.setChecked(True)
        self.salesDockAction.triggered.connect(lambda : self.toggleDock(self.dockSales))

        self.rejectDockAction = QAction("Toggle Reject")
        self.rejectDockAction.setCheckable(True)
        self.rejectDockAction.setChecked(True)
        self.rejectDockAction.triggered.connect(lambda : self.toggleDock(self.dockRejection))

        self.mortalityDockAction = QAction("Toggle Mortality")
        self.mortalityDockAction.setCheckable(True)
        self.mortalityDockAction.setChecked(True)
        self.mortalityDockAction.triggered.connect(lambda : self.toggleDock(self.dockMortality))

        self.breakingDockAction = QAction("Toggle Breaking")
        self.breakingDockAction.setCheckable(True)
        self.breakingDockAction.setChecked(True)
        self.breakingDockAction.triggered.connect(lambda: self.toggleDock(self.dockBreaking))

        self.clearanceDockAction = QAction("Toggle Clearence")
        self.clearanceDockAction.setCheckable(True)
        self.clearanceDockAction.setChecked(True)
        self.clearanceDockAction.triggered.connect(lambda: self.toggleDock(self.dockClearance))

        self.closeResultsDockAction = QAction("Close Results ")
        self.closeResultsDockAction.triggered.connect(lambda : self.closeAll([
            self.dockAgreementHorses,
            self.dockSales,
            self.dockMortality,
            self.dockRejection,
            self.dockBreaking,
            self.dockClearance],
            [self.agreementHorseDockAction,
             self.salesDockAction,
             self.mortalityDockAction,
            self.rejectDockAction,
            self.breakingDockAction,
             self.clearanceDockAction]))
        
        self.closeAccountDockAction = QAction("Close Account")
        self.closeAccountDockAction.triggered.connect(lambda : self.closeAll(
                [self.dockAccount,
                 self.dockPayment,
                 self.dockInvoices],
            [self.accountDockAction,
             self.invoiceDockAction,
             self.paymentDockAction]))

        """Editing Actions """
        editBrokeHorseAction = QAction("Broke Horse", self)
        editBrokeHorseAction.triggered.connect(lambda: self.brokenHorseReceiving(APM.OPEN_EDIT))

        editSaleHorseAction = QAction("Horse Sale", self)
        editSaleHorseAction.triggered.connect(lambda: self.saleHorse(APM.OPEN_EDIT))

        editMortalityAction = QAction("Edit Mortality", self)
        editMortalityAction.triggered.connect(lambda: self.deadHorse(APM.OPEN_EDIT))

        editRejectionAction = QAction("Edit Mortality", self)
        editRejectionAction.triggered.connect(lambda:self.rejectHorse(APM.OPEN_EDIT))

        addBoardAction = QAction(QIcon(":/Icons8/Bills/boarding.png"),"Boarding", self)
        addBoardAction.setStatusTip("Horse Monthly Board")
        addBoardAction.triggered.connect(lambda: self.addPayables(APM.PAYABLES_TYPE_BOARD, APM.OPEN_NEW))

        editBoardAction = QAction("Boarding Charges", self)
        editBoardAction.setStatusTip("Edit Board Chargest")
        editBoardAction.triggered.connect(lambda : self.addPayables(APM.PAYABLES_TYPE_BOARD, APM.OPEN_EDIT))

        addDownpaymentAction = QAction(QIcon(":Icons8/Bills/downpayment"), "Downpayment", self)
        addDownpaymentAction.setStatusTip("Downpayments Charges")
        addDownpaymentAction.triggered.connect(lambda: self.addPayables(APM.PAYABLES_TYPE_DOWNPAYMENT,APM.OPEN_NEW))

        editDownpaymentAction = QAction("Downpayment", self)
        editDownpaymentAction.setStatusTip("Edit Downpayment Action")
        editDownpaymentAction.triggered.connect(lambda: self.addPayables(APM.PAYABLES_TYPE_DOWNPAYMENT, APM.OPEN_EDIT))

        addOtherChargeAction = QAction(QIcon(":/Icons8/Bills/charges.png"), "Other Charge", self)
        addOtherChargeAction.setStatusTip("Other Charges")
        addOtherChargeAction.triggered.connect(lambda:self.billOtherCharge(APM.OPEN_NEW))

        editOtherChargeAction = QAction("Other Charges", self)
        editOtherChargeAction.setStatusTip("Edit Other Charges")
        editOtherChargeAction.triggered.connect(lambda: self.billOtherCharge(APM.OPEN_EDIT))

        self.importHorseAction = QAction(QIcon(":/Icons8/Databases/msaccess.png"),"Import Horses", self)
        self.importHorseAction.setStatusTip("Imports Horse Data from HorseBase MSAccess")
        self.importHorseAction.triggered.connect(self.importHorses)

        self.importContactAction = QAction(QIcon(":/Icons8/Databases/cloud.png"), "Import Contacts", self)
        self.importContactAction.setStatusTip("Import Contacts from MSAccess Horsebase")
        self.importContactAction.triggered.connect(self.importContacts)

        self.importLocationAction = QAction(QIcon(":/Icons8/Databases/database.png"), "Import Locations", self)
        self.importLocationAction.setStatusTip("Import Locations from MSAccess Horsebase")
        self.importLocationAction.triggered.connect(self.importLocations)

        testAction = QAction("Test", self)
        testAction.triggered.connect(self.test)

        self.addToolBarBreak()
        self.chargesBar = self.addToolBar("Billable Charges")
        self.chargesBar.addAction(addDownpaymentAction)
        self.chargesBar.addAction(addBoardAction)
        self.chargesBar.addAction(addOtherChargeAction)
        self.chargesBar.setVisible(False)


        allAvailableHorsesAction = QAction("Available Horses", self)
        allAvailableHorsesAction.triggered.connect(self.allAvailableHorsesInventory)
        allPlayingHorsesAction = QAction("Schooling Horses",self)
        allPlayingHorsesAction.triggered.connect(lambda: self.allOnAgreementHorses(APM.REPORT_TYPE_ALL_PLAYING_HORSES))
        allBreakingHorsesAction = QAction("Breaking Horses", self)
        allBreakingHorsesAction.triggered.connect(lambda: self.allOnAgreementHorses(APM.REPORT_TYPE_ALL_BREAKING_HORSES))

        file = menuBar.addMenu("File")
        file.addAction(self.newAction)
        file.addAction(self.openAction)
        file.addAction(self.saveAction)
        file.addAction(self.saveAsAction)
        file.addAction(self.closeAction)
        file.addAction(self.deleteAction)
        file.addAction(self.refreshAction)
        file.addSeparator()
        file.addAction(self.settingsAction)
        file.addAction(self.quitAction)

        self.document = menuBar.addMenu("Document")
        self.document.addAction(self.openDocumentAction)
        self.document.addAction(self.editAgreementAction)
        self.document.addAction(selectAllAction)
        self.document.addAction(self.copyAction)
        self.document.addAction(self.cutAction)
        self.document.addAction(self.pasteAction)
        self.document.addAction(self.deleteAction)
        self.document.addAction(self.undoAction)
        self.document.addAction(self.redoAction)
        self.document.addAction(self.findAction)
        self.document.addSeparator()
        self.document.addAction(self.previewAction)
        self.document.addAction(self.printAction)
        self.document.menuAction().setVisible(False)

        view = menuBar.addMenu("View")
        view.addAction(toolBarAction)
        view.addAction(formatBarAction)
        view.addAction(accountBarAction)
        view.addAction(statusBarAction)
        view.addAction(horseBarAction)
        view.addAction(peopleBarAction)
        view.addAction(closeAllBarAction)

        view.addSeparator()
        view.addAction(self.agreementDockAction)
        view.addSeparator()
        view.addAction(self.invoiceDockAction)
        view.addAction(self.paymentDockAction)
        view.addAction(self.accountDockAction)
        view.addAction(self.closeAccountDockAction)
        view.addSeparator()
        view.addAction(self.agreementHorseDockAction)
        view.addAction(self.mortalityDockAction)
        view.addAction(self.rejectDockAction)
        view.addAction(self.clearanceDockAction)
        view.addAction(self.breakingDockAction)
        view.addAction(self.salesDockAction)
        view.addAction(self.closeResultsDockAction)

        reports = menuBar.addMenu("Reports")
        reports.addAction(allAvailableHorsesAction)
        reports.addAction(allBreakingHorsesAction)
        reports.addAction(allPlayingHorsesAction)

        inventory = menuBar.addMenu('Horse Inventory')
        inventory.addAction(self.addHorseAction)
        inventory.addAction(self.editHorseAction)
        inventory.addAction(self.importHorseAction)

        self.horses = menuBar.addMenu("Horses")
        self.horses.addAction(self.brokeHorseReceivingAction)
        self.horses.addAction(self.saleAction)
        self.horses.addAction(self.rejectAction)
        self.horses.addAction(self.deathAction)
        self.horses.addSeparator()
        self.horses.menuAction().setVisible(False)

        editHorses = self.horses.addMenu(QIcon(":/Icons8/Edit/EditHorse.png"), "Edit")
        editHorses.addAction(editBrokeHorseAction)
        editHorses.addAction(editSaleHorseAction)
        editHorses.addAction(editMortalityAction)
        editHorses.addAction(editRejectionAction)

        contacts = menuBar.addMenu("People")
        contacts.addAction(self.newContactAction)
        contacts.addAction(self.editContactAction)
        contacts.addSeparator()
        contacts.addAction(self.managerAction)
        contacts.addSeparator()
        contacts.addAction(self.buyerAction)
        contacts.addAction(self.dealerAction)
        contacts.addSeparator()
        contacts.addAction(self.playerAction)
        contacts.addAction(self.breakerAction)
        contacts.addAction(self.showPoloPlayerAction)
        contacts.addAction(self.showBusterAction)
        contacts.addAction(self.vetAction)

        access = menuBar.addMenu("Access")
        access.addAction(self.importHorseAction)
        access.addAction(self.importContactAction)
        access.addAction(self.importLocationAction)

        self.accounts = menuBar.addMenu("Accounts")
        self.accounts.addAction(self.supplierDataAction)
        self.accounts.addSeparator()
        billings = self.accounts.addMenu(QIcon(":/Icons8/Accounts/bill.png"), "Billing")
        billings.addAction(addDownpaymentAction)
        billings.addAction(addBoardAction)
        billings.addAction(addOtherChargeAction)
        self.accounts.addSeparator()
        self.accounts.addAction(self.addInvoiceAction)
        self.accounts.addAction(self.addPaymentAction)
        self.accounts.addSeparator()
        self.accounts.addAction(self.addLocationAction)
        self.accounts.addAction(self.addTransferAction)
        self.accounts.addSeparator()
        self.accounts.menuAction().setVisible(False)

        editAccounts = self.accounts.addMenu(QIcon(":Icons8/Edit/Edit.png"), "Edit")
        editAccounts.addAction(self.editInvoiceAction)
        editAccounts.addAction(self.editPaymentAction)
        editAccounts.addSeparator()
        editAccounts.addAction(self.editLocationAction)
        editAccounts.addAction(self.editTransferAction)

        editBills = editAccounts.addMenu("Edit Bills")
        editBills.addAction(editDownpaymentAction)
        editBills.addAction(editBoardAction)
        editBills.addAction(editOtherChargeAction)

        #edit = menuBar.addMenu('Edit')
        help = menuBar.addMenu("Help")
        help.addAction(testAction)

    @pyqtSlot()
    def test(self):
        model = self.tableAgreementHorses.model()
        provider = "John Doe"
        customer = "Peter Doe"
        res = InvoicePrint(model, provider, customer)
        res.show()
        res.exec()


    @pyqtSlot()
    def importHorses(self):
        try:
            wid = ImportHorses(self.qdb, self.con_string, self)
            wid.show()
            wid.exec()
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print(type(err), err.args)

    @pyqtSlot()
    def importContacts(self):
        try:
            wid = ImportContacts(self.qdb, self.con_string, self)
            wid.show()
            #wid.exec()
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print(type(err), err.args)

    @pyqtSlot()
    def importLocations(self):
        try:
            wid = ImportLocations(self.qdb, self.con_string, self)
            wid.show()
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print(type(err), err.args)


    @pyqtSlot()
    def enableBillBar(self):
        self.chargesBar.setVisible(not self.chargesBar.isVisible())

    @pyqtSlot()
    def setDocumentBars(self):
        opt = not self.text.isEnabled()
        documentObjects = [
            self.text,
            self.printAction,
            self.previewAction,
            self.cutAction,
            self.copyAction,
            self.pasteAction,
            self.undoAction,
            self.redoAction,
            self.bulletAction,
            self.numberedAction]
        [obj.setEnabled(opt) for obj in documentObjects]
        self.brokeHorseReceivingAction.setEnabled(opt) if self.isBreaking else \
            self.brokeHorseReceivingAction.setEnabled(False)
        self.formatBar.setVisible(opt)
        self.documentBar.setVisible(opt)


    @pyqtSlot()
    def allAvailableHorsesInventory(self):
        rpt = AvailableHorses(self.qdb, APM.REPORT_TYPE_ALL_HORSES, self)
        rpt.show()
        rpt.exec()

    @pyqtSlot()
    def allAvailable(self, mode):
        rpt = AvailableHorses(self.qdb, mode, self)
        rpt.show()
        rpt.exec()


    @pyqtSlot()
    def allOnAgreementHorses(self, mode):
        try:
            rpt = AvailableHorses(self.qdb, mode, self)
            rpt.show()
            rpt.exec()
        except DataError as err:
            return


    @pyqtSlot()
    def brokenHorseReceiving(self, mode):
        try:
            qryLoad = QSqlQuery(self.qdb)
            qryLoad.exec("CALL receivebroken_loadhorses({}, '{}', {})".format(self.agreementId,
                                                                              QDate.currentDate().toString("yyyy-MM-dd"),
                                                                              mode))
            if qryLoad.lastError().type() != 0:
                raise DataError("setUI - load horse", qryLoad.lastError().text())
            if qryLoad.size() < 1:
                raise DataError("brokenHorseReceiving", "No Data")

            h = ReceiveBroken(mode,  self.qdb, self.con_string,self.agreementId, qryLoad, self)
            h.show()
            #h.exec()
        except DataError as err:
            self.messageBox(err.source, err.message)
        except Exception as err:
            print(type(err).__name__, err.args)

    @pyqtSlot()
    def showContacts(self, type):
        s = ShowContacts(self.qdb, type)
        s.show()
        s.exec()

    @pyqtSlot()
    def getTreeData(self, action):
        index = self.treeViewAgr.currentIndex()
        filename = self.treeViewAgr.model().filePath(index)
        messageText = "File: {}".format(os.path.basename(filename))
        messageQuestion = "Do you want to open it?"
        if os.path.isfile(filename):
            if self.filename:
                if action == APM.OPEN_FILE:
                    messageText = "File: {} is open".format(os.path.basename(self.filename))
                    messageQuestion = "Do you want to close it?"
            if action == APM.DELETE_FILE:
                messageText = "File: {} would be deleted".format(os.path.basename(filename))
                messageQuestion =  "Are you sure??"
            if action == APM.RENAME_FILE:
                messageText = "File: {} would be renamed".format(os.path.basename(filename))
                messageQuestion = "Are you sure?"
            if action == APM.COPY_FILE:
                messageText = "File: {} would be copied".format(os.path.basename(filename))
                messageQuestion = "Are you sure??"
            res = self.messageBoxYesNo(messageText, messageQuestion)
            if res != QMessageBox.Yes:
                return
            if action == APM.OPEN_FILE:
                if self.filename:
                    self.closeFile()
                self.filename = filename
                self.open_file()
            elif action == APM.DELETE_FILE:
                self.delete_file(filename)
            elif action == APM.COPY_FILE:
                self.copy_file(filename)
            elif action == APM.RENAME_FILE:
                self.rename_file(filename)

    @pyqtSlot()
    def getHorseData(self, mode=APM.OPEN_EDIT_ONE):
        record = None
        if mode == APM.OPEN_EDIT_ONE:
            row = self.tableAgreementHorses.currentIndex().row()
            model = self.tableAgreementHorses.model()
            model.query().isSelect()
            model.query().isActive()
            model.query().seek(row)
            record = model.query().record()
            res = self.messageBoxYesNo("Would check {}'s record?".format(record.value(2)),
                                 'Check the data and/or enter/edit as neccesary')
            if res != QMessageBox.Yes:
                return
        try:
            horseid = record.value(16)
            detail = Horses(self.qdb, APM.OPEN_EDIT_ONE,record, horseid,self)
            detail.show()
        except DataError as err:
            QMessageBox.warning(self, "DataError", "{}".format(err.message),QMessageBox.Ok)
        except Exception as err:
            print(err.args)

    @pyqtSlot()
    def contact(self, action):
        if action == APM.OPEN_NEW:
            cont = Contacts(self.qdb, parent=self)
        else:
            cont = Contacts(self.qdb, mode=APM.OPEN_EDIT,parent=self)
        cont.show()
        res = cont.exec_()

    @pyqtSlot()
    def addInvoice(self, mode, record=None):
        try:
            if mode == APM.OPEN_EDIT:
                qry = QSqlQuery(self.qdb)
                qry.exec("CALL invoice_getinvoices({})".format(self.supplierId))
                if qry.lastError().type()!= 0 :
                    raise DataError('addInvoice', qry.lastError().text())
                if not qry.first():
                    QMessageBox.information(self,"Edit Invoices", "There are not {} pending charges in the system".format(
                        self._supplier), QMessageBox.Ok)
                    return
            inv = Invoice(self.qdb, self.supplierId, APM.PAYABLES_TYPE_ALL,mode,parent=self, record=record)
            inv.show()
            inv.exec()

        except APM.DataError as err:
            self.messageBox(err.source, err.message)
            print(err.source, err.message)
        except Exception as err:
            print(err.args)

    @pyqtSlot()
    def showAccount(self):
        pass

    @pyqtSlot()
    def saleHorse(self, mode):
        try:
            qry = QSqlQuery(self.qdb)
            qry.exec("CALL sales_gethorses({}, {})".format(self.agreementId, mode))
            if qry.lastError().type() != 0:
                raise APM.DataError("getHorsesQuery", qry.lastError().text())
            if not qry.first():
                raise APM.DataError("getHorsesQuery", "There is not available data")

            sh = Sales(self.qdb, self.agreementId, mode=mode,con_string=self.con_string, qryLoad=qry,parent=self)
            sh.show()
            sh.exec()
        except APM.DataError as err:
            self.messageBox(err.source, err.message)
            print(err.source, err.message)
        except Exception as err:
            print(err.args)


    def rejectHorse(self, mode):
        try:
            detail = Reject(self.qdb, self.agreementId, mode=mode, con_string=self.con_string, parent=self)
            detail.show()
            detail.exec()
        except APM.DataError as err:
            if err.type == 1:
                self.showError(err)
            return

    @pyqtSlot()
    def deadHorse(self, mode):
        try:
            detail = Mortality(self.qdb, self.agreementId, mode=mode, con_string = self.con_string,  parent= self)
            detail.show()
            detail.exec()
        except APM.DataError:
            return

    @pyqtSlot()
    def receiveBrokeHorse(self):
        pass

    @pyqtSlot()
    def updateHorseInventory(self, mode):
        try:
            if mode == APM.OPEN_EDIT_ONE:
                row = self.tableAgreementHorses.currentIndex().row()
                model = self.tableAgreementHorses.model()
                model.query().isSelect()
                model.query().isActive()
                model.query().seek(row)
                record = model.query().record()
                res = self.messageBoxYesNo("Do you want to Edit {} record?".format(record.value(2)),
                                           'Check the data and/or enter/edit as neccesary')
                if res != QMessageBox.Yes:
                    return
                h = Horses(self.qdb, mode, record)
            else:
                h = Horses(self.qdb, mode)
            h.show()
            h.exec()
        except DataError as err:
            if err.type == 1:
                self.showError(err)

    def showError(self, err):
        QMessageBox.critical(self, err.source, err.message)
        sys.exit()



    @pyqtSlot()
    def startHorse(self):
        str = StartHorse(self.qdb, self)
        str.show()
        str.exec()

    @pyqtSlot()
    def wordCount(self):
        try:
            wc = wordcount.WordCount(self)
            wc.getText()
            wc.show()
        except Exception as err:
            print(err)

    @pyqtSlot()
    def insertImage(self):
        try:
            filename = QFileDialog.getOpenFileName(self, 'Insert Image', '.', "Images("
                                                                          "*.png "
                                                                          "*.xpm "
                                                                          "*.jpg "
                                                                          ".bmp "
                                                                          "*.gif)")
            image = QImage(filename[0])
            if image.isNull():
                popup = QMessageBox(QMessageBox.critical,
                                "Image load error",
                                "Could not load image file!",
                                QMessageBox.Ok)
                popup.show()
            else:
                cursor = self.text.textCursor()
                cursor.insertImage(image, filename[0])
        except Exception as err:
            print(err)

    @pyqtSlot()
    def removeText(self):
        cursor = self.text.textCursor()
        if cursor.hasSelection():
            try:
                cursor.removeSelectedText()
            except Exception as err:
                print(err)

    @pyqtSlot()
    def toggleToolBar(self):
        state = self.toolBar.isVisible()
        self.toolBar.setVisible(not state)

    @pyqtSlot()
    def toggleFormatBar(self):
        state = self.formatBar.isVisible()
        self.formatBar.setVisible(not state)

    @pyqtSlot()
    def toggleAccountBar(self):
        state = self.accountBar.isVisible()
        self.accountBar.setVisible(not state)

    @pyqtSlot()
    def toggleStatusBar(self):
        state = self.statusBar.isVisible()
        self.statusBar.setVisible(not state)

    @pyqtSlot()
    def toggleDock(self, dock):
        try:
            state = dock.isVisible()
            dock.setVisible(not state)
            dock.setChecked(not state)
        except AttributeError:
            self.sender().setChecked(True)
            return


    @pyqtSlot()
    def closeAll(self, lst, actlst):
        try:
            [dock.setVisible(False) for dock in lst]
            [act.setChecked(False) for act in actlst]
        except AttributeError:
            return

    @pyqtSlot()
    def closeAllBars(self, bars, actions):
        [bar.setVisible(False) for bar in bars]
        [action.setChecked(False) for action in actions]


    @pyqtSlot()
    def checkDock(self, dockAction,dock):
        if not dock.isVisible():
            dockAction.setChecked(False)

    @pyqtSlot()
    def indent(self):
        cursor = self.text.textCursor()
        if cursor.hasSelection():
            temp = cursor.blockNumber()
            cursor.setPosition(cursor.selectionEnd())
            diff = cursor.blockNumber() - temp
            for n in range(diff + 1):
                cursor.movePosition(QTextCursor.StartOfLine)
                cursor.insertText("\t")
                cursor.movePosition(QTextCursor.Up)
        else:
            cursor.insertText("\t")

    @pyqtSlot()
    def dedentArea(self):
        cursor = self.text.textCursor()
        if cursor.hasSelection():
            temp = cursor.blockNumber()
            cursor.setPosition(cursor.selectionEnd())
            diff = cursor.blockNumber() - temp
            for n in range(diff + 1):
                try:
                    self.handleDedent(cursor)
                    cursor.movePosition(QTextCursor.Up)
                except Exception as err:
                    print(err)
        else:
            self.handleDedent(cursor)

    def handleDedent(self, cursor):
        cursor.movePosition(QTextCursor.StartOfLine)
        line = cursor.block().text()
        if line.startswith("\t"):
            cursor.deleteChar()
        else:
            for char in line[:8]:
                if char != " ":
                    break
                cursor.deleteChar()


    def treeView_doubleClicked(self,index):
        ed = self.treeViewAgr.EditTrigger() #QAbstractItemView.Doubleclicked
        print(ed)
        pass

    @pyqtSlot()
    def alignLeft(self):
        self.text.setAlignment(Qt.AlignLeft)

    @pyqtSlot()
    def alignCenter(self):
        self.text.setAlignment(Qt.AlignCenter)

    @pyqtSlot()
    def alignRight(self):
        self.text.setAlignment(Qt.AlignRight)

    @pyqtSlot()
    def alignJustify(self):
        self.text.setAlignment(Qt.AlignJustify)

    @pyqtSlot()
    def bold(self):
        if self.text.fontWeight() == QFont.Bold:
            self.text.setFontWeight(QFont.Light)
        else:
            self.text.setFontWeight(QFont.Bold)

    @pyqtSlot()
    def italic(self):
        self.text.setFontItalic(not self.text.fontItalic())

    @pyqtSlot()
    def underline(self):
        self.text.setFontUnderline(not self.text.fontUnderline())

    @pyqtSlot()
    def strike(self):
        fmt = self.text.currentCharFormat()
        fmt.setFontStrikeOut(not fmt.fontStrikeOut())
        self.text.setCurrentCharFormat(fmt)

    @pyqtSlot()
    def superScript(self):

        fmt = self.text.currentCharFormat()

        align = fmt.verticalAlignment()

        try:
            if align == QTextCharFormat.AlignNormal:
                fmt.setVerticalAlignment(QTextCharFormat.AlignSuperScript)
            else:
                fmt.setVerticalAlignment(QTextCharFormat.AlignNormal)
        except Exception as err:
            print(err)
        self.text.setCurrentCharFormat(fmt)

    @pyqtSlot()
    def subScript(self):
        fmt = self.text.currentCharFormat()

        align = fmt.verticalAlignment()

        if align == QTextCharFormat.AlignNormal:
            fmt.setVerticalAlignment(QTextCharFormat.AlignSubScript)
        else:
            fmt.setVerticalAlignment(QTextCharFormat.AlignNormal)
        self.text.setCurrentCharFormat(fmt)

    @pyqtSlot(QFont)
    def fontFamily(self, font):
        self.text.setCurrentFont(font)

    @pyqtSlot(int)
    def fontSize(self, fontSize):
        try:
            self.text.setFontPointSize(fontSize)
        except Exception as err:
            print(err)

    @pyqtSlot()
    def fontColor(self):
        color = QColorDialog.getColor()
        self.text.setTextColor(color)

    @pyqtSlot()
    def highlight(self):
        color = QColorDialog.getColor()
        self.text.setTextBackgroundColor(color)

    def applicationSettings(self):
        try:
            settWindow = Settings.SettingsDialog(self.qdb)
            settWindow.show()
            res = settWindow.exec_()

        except Exception as err:
            print(err)

    @pyqtSlot()
    def account(self):
        pass


    @pyqtSlot()
    def cursorPosition(self):
        cursor = self.text.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber()

        self.statusBar.showMessage("Line: {} | Column: {}".format(line, col))

    @pyqtSlot()
    def bulletList(self):
        cursor = self.text.textCursor()
        cursor.insertList(QTextListFormat.ListDisc)

    @pyqtSlot()
    def numberedList(self):
        cursor = self.text.textCursor()
        cursor.insertList(QTextListFormat.ListDecimal)

    @pyqtSlot()
    def new(self):

        """provides a delegate to open the new account stating
        the  name of the supplier, date, type of contract, total amount
        and installments if payment is not at final. List of horses incuded
        in the agreement and name of the contract. This to be done by
        a dialog window wset with a socketclient requesthandler class"
        it would create an Agreement entry, make a supplier directory if
        necessary and produce: filename and new agreement file; """

        try:
            new = newAgreement.Agreement(self.qdb, self.address, parent=self)
            new.show()
            result = new.exec_()
            if result:
                self.setWindowTitle(new.lineAgreement.text())
                self.agreementId = new.getID
                self.filename = os.path.join(self.agreementsPath,
                                             self.filename[self.filename.find("Agreements") +10 :])
                self.open_file()
                self.text.clear()
                self.treeViewAgr.model().setRootPath(QDir.path(QDir(self.agreementsPath)))
        except TypeError as err:
            print(type(err).__name__, err.args)
        except APM.DataError as err:
            self.messageBox("Can´t open a new agreement! No {}".format(err.source), "{}".format(err.args))
        except Exception as err:
            print(type(err).__name__, err.args)

    @pyqtSlot()
    def save(self):
        try:
            if not self.agreementId:
                raise ValueError("Missing Agreement ID")
            if not self.filename:
                self.filename = QFileDialog.getSaveFileName(self,'SaveFile',self.agreementsPath, '*.pam')[0]

            if not self.filename.endswith(".pam"):
                self.filename += ".pam"

            binText = self.text.toHtml().encode('UTF-8')
            magicStruct = Struct("<4s")
            idStruct = Struct("<h")
            xmlStruct = Struct("<{}s".format(len(binText)))
            with open(self.filename, "bw") as fb:
                fb.write(magicStruct.pack(self.MAGIC))
                fb.write(idStruct.pack(self.agreementId))
                fb.write(xmlStruct.pack(binText))
            self.changesSaved = True
        except ValueError as err:
            self.messageBox(err, "Choose de 'New' option to enter a new agreement")
            return

    pyqtSlot()
    def saveAs(self):
        filename = None,
        if self.filename:
            filename = QFileDialog.getSaveFileName(self, 'Save As', self.agreementsPath, '*.pam', )
        if filename[0] != self.filename:
            self.messageBox("New Agreement", "Choose de 'New' option to enter a new agreement")

        self.save()


    @pyqtSlot()
    def preview(self):

        preview = QPrintPreviewDialog()
        preview.paintRequested.connect(lambda p: self.text.print_(p))
        preview.exec_()

    @pyqtSlot()
    def print(self):
        dialog = QPrintDialog()

        if dialog.exec_() == QDialog.Accepted:
            self.text.document().print_(dialog.printer())

    @pyqtSlot()
    def open_file(self):
        """Needs to set up the methods to set the auxiliary windows for this agreement"""
        try:
            magicStruct = Struct("<4s")
            idStruct = Struct("<h")
            with open(self.filename, "br") as fh:
                magic = fh.read(magicStruct.size)
                if magic != self.MAGIC:
                    pop = QMessageBox(self)
                    pop.setIcon(QMessageBox.Critical)
                    pop.setText("Wrong File Type")
                    pop.setInformativeText("The selected file is not a'Polo Agreement Management' file (*.pam)")
                    pop.setStandardButtons(QMessageBox.Ok)
                    pop.show()
                    return
                idData = fh.read(idStruct.size)
                self.agreementId = idStruct.unpack(idData)[0]
            with open(self.filename, "rt") as ft:
                ft.seek(magicStruct.size + idStruct.size)
                self.text.setText(ft.read())
            fileDescription = os.path.basename(self.filename)
            self.setWindowTitle(fileDescription[:fileDescription.index('.')])
            self.changesSaved = True
            qry = QSqlQuery(self.qdb)
            qry.prepare("SELECT agreementtype FROM agreements WHERE id = ?")
            qry.addBindValue(QVariant(self.agreementId))
            qry.exec()
            qry.first()
            self.isBreaking = True if qry.value(0) == 0 else False
            self.accountBar.setVisible(False)
            self.horses.menuAction().setVisible(True)
            self.prepareAgreementDocks()
            self.showAgreementDocks()
            self.setDockWindows()

        except Exception as err:
            print('open_file', type(err).__name__, err.args)

    @pyqtSlot()
    def open(self):
        if self.filename:
            try:
                res = self.messageBoxYesNo("file {} is open".format(os.path.basename(self.filename)),
                                           "Do you want to close it?")
                if res != QMessageBox.Yes:
                    return
                self.closeFile()
            except Exception as err:
                print('open: {}'.format(err.args))
        filename = QFileDialog.getOpenFileName(self,'Open File', self.agreementsPath, "Polo Agreement (*.pam)")
        if filename != ('',''):
            self.filename = filename[0]
            self.open_file()

    @pyqtSlot(QModelIndex)
    def on_current_change(self, ModelIndex):
        try:
            name_index = self.tableInvoices.model().index(ModelIndex.row(), 1)
            id_index = self.tableInvoices.model().index(ModelIndex.row(), 0)
            id = id_index.data()
            name = name_index.data()
            print('{} corresponds to {}'.format(id, name))
        except Exception as err:
            print(err)

    def getInvoices(self):
        try:
            qry = QSqlQuery(self.qdb)
            qry.exec("CALL invoice_getinvoices({})".format(self.supplierId))
            if qry.lastError().type() != 0:
                raise DataError("getInvoices", qry.lastError().text())
            return qry
        except DataError as err:
            print(err.source, err.message)

    def getPayments(self):
        try:
            qry = QSqlQuery(self.qdb)
            qry.exec("CALL payment_loadpayments({})".format(self.supplierId))
            if qry.lastError().type() != 0:
                raise DataError("getPaymentss", qry.lastError().text())
            return qry
        except DataError as err:
            print(err.source, err.message)

    def getAccount(self):
        try:
            qry = QSqlQuery(self.qdb)
            qry.exec("CALL account_setaccount({}, {})".format(self.supplierId,
                                                              'NULL'))
            if qry.lastError().type() != 0:
                raise DataError("getAccount", qry.lastError().text())
            if qry.first():
                print(qry.value(0), qry.value(1))
            return qry
        except DataError as err:
            print(err.source, err.message)


    def queryAgreementHorses(self):
        qry = QSqlQuery(self.qdb)
        qry.prepare("""
            SELECT
            ah.id,
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
            ah.breakerid,
            ah.playerid,
            ah.active as Active,
            h.id,
            h.notes
            FROM agreementhorses as ah
            INNER JOIN horses as h ON ah.horseid = h.id
            INNER JOIN coats as c ON h.coatid = c.id
            INNER JOIN sexes as s ON h.sexid = s.id
            INNER JOIN agreements as a on ah.agreementid = a.id
            WHERE ah.agreementid = ?""")
        qry.addBindValue(QVariant(self.agreementId))
        qry.exec_()
        if qry.lastError().type() != 0:
            raise APM.DataError('queryAgreementHorses', qry.lastError().text())
        return qry

    def queryAccounts(self):
        query = QSqlQuery()
        query.prepare("""
                SELECT id, nombre, Owner FROM Ubicaciones
                WHERE ID = ?
                """)
        query.addBindValue(11)
        query.exec_()
        return query

    def queryPayments(self):
        query = QSqlQuery()
        query.prepare("""
                SELECT id, Concat(nombre , " ", Apellidos) As Nombre, esPolista FROM Contactos
                """)
        query.addBindValue(11)
        query.exec_()
        return query

    def setDockSales(self):
        self.dockSales.setWidget(self.setTableSales())

    def setTableSales(self):
        qry = self.querySales()
        colorDict = {'column': (27),
                     0 :(QColor('yellow'), QColor('black')),
                     1 :(QColor('red'), QColor('white')),
                     2 :(QColor('gray'),QColor('yellow')),
                     3 :(QColor('black'),QColor('white')),
                     4 :(QColor('lightgray'), QColor('black'))}
        colDict = {
            0: ("Date", False, True, True, None),
            1: ("RP", True, True, True, None),
            2: ("Horse", False, False, False, None),
            3: ("Sex", False, True, True, None),
            4: ("Age", False, True, False, None),
            5: ("Price",False, True, False, None ),
            6: ("SexStr", True, True, False, None),
            7: ("CoatStr", True, True, False, None),
            8: ("AgreHorseID", True, True, False, None),
            9: ("horseid", True, True, False, None),
            10: ("SaleBase", True, True, False, None),
            11: ("SaleFirstFrom", True, True, True, None),
            12: ("SaleFirstTo", True, True, False, None),
            13: ("SaleSecondFrom", True, True, False, None),
            14: ("SaleSecondTo", True, True, False, None),
            15: ("SaleThirdFrom", True, True, False, None),
            16: ("SaleThirdTo", True, True, False, None),
            17: ("SaleFinal", True, True, False, None),
            18: ("BasePercent", True, True, False, None),
            19: ("FirstPercent", True, True, False, None),
            20: ("SecondPercent", True, True, False, None),
            21: ("ThirdPercent", True, True, False, None),
            22: ("FinalPercent", True, True, False, None),
            23: ("BuyerId", True, True, False, None),
            24: ("DealerId", True, True, False, None),
            25: ("ResponsibleId", True, True, False, None),
            26: ("DestinationId", True, True, False, None),
            27: ("TypeId", True, True, False, None),
            28: ("ComissionPercent", True, True, False, None),
            29: ("Comission", True, True, False, None),
            30: ("Expenses", True, True, False, None),
            31: ("DocumentId", True, True, False, None),
            32: ("DocumentNumber", True, True, False, None),
            33: ("Notes", True, True, False, None),
            34: ("SaleID", True, True, False, None),
            35: ("Purpose", False, True, False, None)}
        table = TableViewAndModel(colDict, colorDict, (300, 300), qry)
        table.doubleClicked.connect(lambda : self.getSaleData(table))
        return table

    def getSaleData(self, table):
        record = None
        try:
            row = table.currentIndex().row()
            model = table.model()
            model.query().isSelect()
            model.query().isActive()
            model.query().seek(row)
            record = model.query().record()
            res = self.messageBoxYesNo("Would check {}'s Sale record?".format(record.value(2)),
                                       'Check the data and/or enter/edit as necessary')
            if res != QMessageBox.Yes:
                return
            #horseid = record.value(0)
            detail = Sales(self.qdb,self.agreementId, APM.OPEN_EDIT,
                               record, self.con_string, self)
            detail.show()
        except DataError as err:
            QMessageBox.warning(self, "DataError", "{}".format(err.message), QMessageBox.Ok)
        except Exception as err:
            print(type(err).__name__, err.args)

    def querySales(self):
        try:
            query= QSqlQuery(self.qdb)
            query.prepare("""SELECT sa.dos, h.rp, h.name,
                CASE
                    WHEN h.sexid = 1 THEN _ucs2 x'2642'
                    WHEN h.sexid = 2 THEN _ucs2 x'2640'
                    WHEN h.sexid = 3 THEN _ucs2 x'265E'
                END Sex,
                CONCAT(TIMESTAMPDIFF(YEAR, h.dob, sa.dos), ' years') Age,
                sa.price,
                s.sex, c.coat,
                 ah.id agreemenhorseid, h.id horseid,
                sac.salebaseAmount,
                sac.salefirstfrom,
                sac.salefirstto,
                sac.salesecondfrom,
                sac.salesecondto,
                sac.salethirdfrom,
                sac.salethirdto,
                sac.saleFinal,
                sac.salebasepercent,
                sac.salefirstpercent,
                sac.salesecondpercent,
                sac.salethirdpercent,
                sac.salefinalpercent,
                sa.buyerid,
                sa.dealerid,
                sa.responsibleid,
                sa.destinationid,
                sa.saletype,
                sa.comissionpercent,
                sa.comission,
                sa.expenses,
                sa.documenttype,
                sa.documentnumber,
                sa.notes,
                sa.id,
                CASE
                    WHEN destinationid = 0 THEN 'Polo Export'
                    WHEN destinationid = 1 THEN 'Polo Local'
                    WHEN destinationid = 2 THEN 'Breeding'
                    WHEN destinationid = 3 THEN 'Ridding'
                    WHEN destinationid = 4 THEN 'Rejection'
                    WHEN destinationid = 5 THEN 'Unknown'
                END 
                FROM horses  h
                INNER JOIN coats  c
                ON h.coatid = c.id
                INNER JOIN sexes  s
                ON h.sexid = s.id
                INNER JOIN agreementhorses AS ah
                ON h.id = ah.horseid
                INNER JOIN agreements a
                ON ah.agreementid = a.id
                LEFT JOIN agreementsaleconditions sac
                ON a.id = sac.agreementid
                INNER JOIN  sales  sa
                ON ah.id = sa.agreementhorseid
                WHERE a.id = ?""")
            query.addBindValue(QVariant(self.agreementId))
            query.exec_()
            if query.lastError().type()!= 0:
                raise DataError("querySales", query.lastError().text())
            return query
        except DataError as err:
            print(err.source, err.message)

    def file_model(self):
        dir_model = QFileSystemModel()
        dir_model.setRootPath(QDir.path(QDir(self.agreementsPath)))
        return dir_model

    @pyqtSlot(QPoint)
    def openPopDir(self, pos):
        try:
            openFileAction = QAction("Open file")
            openFileAction.triggered.connect(lambda : self.getTreeData(APM.OPEN_FILE))
            deleteFileAction = QAction("Delete File")
            deleteFileAction.triggered.connect(lambda : self.getTreeData(APM.DELETE_FILE))
            renameFileAction = QAction("Rename File")
            renameFileAction.triggered.connect(lambda : self.getTreeData(APM.RENAME_FILE))
            copyFileAction = QAction('Copy File')
            copyFileAction.triggered.connect(lambda : self.getTreeData(APM.COPY_FILE))
            refreshDirectoryAction = QAction("Refresh Directory")
            refreshDirectoryAction.triggered.connect(self.refreshDirectory)

            menu= QMenu(self)
            menu.addAction(openFileAction)
            menu.addAction(deleteFileAction)
            menu.addAction(renameFileAction)
            menu.addSeparator()
            menu.addAction(copyFileAction)
            menu.addAction(refreshDirectoryAction)

            menu.show()
            action = menu.exec_(self.treeViewAgr.mapToGlobal(pos))

            event = QContextMenuEvent(QContextMenuEvent.Mouse, QPoint())
            self.treeViewAgr.contextMenuEvent(event)
        except Exception as err:
            traceback.print_tb(sys.exc_info()[2])
            print('openPopDir', type(err).__name__, err.args)

    @pyqtSlot()
    def refreshDirectory(self):
        treeModel = self.file_model()
        path = treeModel.rootPath()
        self.treeViewAgr.setModel(treeModel)
        self.treeViewAgr.setRootIndex(treeModel.index(path))


    def delete_file(self, filename):
        pass

    def copy_file(self,filename):
        pass

    def rename_file(self,filename):
        pass

    def context(self, pos):
        cursor = self.text.textCursor()
        table = cursor.currentTable()
        if table:
            menu = QMenu(self)

            appendRowAction = QAction("Append Row", self)
            appendRowAction.triggered.connect(lambda: table.appendRows(1))

            appendColAction = QAction("Append Column", self)
            appendColAction.triggered.connect(lambda: table.appendColumns(1))

            removeRowAction = QAction("Remove Row", self)
            removeRowAction.triggered.connect(self.removeRow)

            removeColAction = QAction("Remove Column", self)
            removeColAction.triggered.connect(self.removeCol)

            insertRowAction = QAction("Insert Row", self)
            insertRowAction.triggered.connect(self.insertRow)

            insertColAction = QAction("Insert Column", self)
            insertColAction.triggered.connect(self.insertCol)

            mergeAction = QAction("Merge Cells", self)
            mergeAction.triggered.connect(lambda: table.merge(cursor))
            if not cursor.hasSelection():
                mergeAction.setEnabled(False)
            splitAction = QAction("Split Cell", self)
            try:
                cell = table.cellAt(cursor)
                if cell.rowSpan() > 1 or cell.columnSpan() > 1 :
                    splitAction.triggered.connect(lambda: table.splitCell(cell.row(),cell.col(),1,1))
                else:
                    splitAction.setEnabled(False)
            except Exception as err:
                print(type(err).__name__, err.args)
            menu.addAction(appendRowAction)
            menu.addAction(appendColAction)
            menu.addSeparator()
            menu.addAction(removeRowAction)
            menu.addAction(removeColAction)
            menu.addSeparator()
            menu.addAction(insertRowAction)
            menu.addAction(insertColAction)
            menu.addSeparator()
            menu.addAction(mergeAction)
            menu.addAction(splitAction)

            pos = self.mapToGlobal(pos)

            if self.toolBar.isVisible():
                pos.setY(pos.y() + 45)
            if self.formatBar.isVisible():
                pos.setY(pos.y() + 45)
            menu.move(pos)
            menu.show()
        else:
            event = QContextMenuEvent(QContextMenuEvent.Mouse, QPoint())
            self.text.contextMenuEvent(event)

    def removeRow(self):
        cursor = self.text.textCursor()
        table = cursor.currentTable()
        cell = table.cellAt(cursor)
        table.removeRows(cell.row(),1)

    def removeCol(self):
        cursor = self.text.textCursor()
        table = cursor.currentTable()
        cell = table.cellAt(cursor)
        table.removeColumns(cell.column(), 1)

    def insertRow(self):
        cursor = self.text.textCursor()
        table = cursor.currentTable()
        cell = table.cellAt(cursor)
        table.insertRows(cell.row(),1)

    def insertCol(self):
        cursor = self.text.textCursor()
        table = cursor.currentTable()
        cell = table.cellAt(cursor)
        table.insertColumns(cell.column(),1)

    def changed(self):
        self.changesSaved = False

    def closeEvent(self, event):
        QSettings("ErickSoft", "PoloManagement")
        try:
            sett = QSettings("config.ini", QSettings.IniFormat)
            sett.setValue("geometry", self.saveGeometry())
            sett.setValue("windowsSate", self.saveState())
            if self.filename:
                sett.setValue("path/lastfile",self.filename[0])

            if self.changesSaved:
                event.accept()
            else:
                popup = QMessageBox(self)
                popup.setIcon(QMessageBox.Warning)
                popup.setText("The document has been modified")
                popup.setInformativeText("Do you want to save your chages")
                popup.setStandardButtons(QMessageBox.Save  |
                                         QMessageBox.Cancel|
                                         QMessageBox.Discard)
                popup.setDefaultButton(QMessageBox.Save)

                answer = popup.exec_()
                if answer == QMessageBox.Save:
                    self.save()
                elif answer == QMessageBox.Discard:
                    event.accept()
                else:
                    event.ignore()
        except Exception as err:
            print('closeEvent', type(err).__name__, err.args)

    @pyqtSlot()
    def deleteFile(self):
        pass

    @pyqtSlot()
    def refresh(self):
        self.refreshDirectory()

    @pyqtSlot()
    def renameFile(self):
        pass

    @pyqtSlot()
    def closeFile(self):
        try:
            if not self.changesSaved:
                res = self.messageBoxYesNo('The file has been modified.' "Save it before closing?")
                if res == QMessageBox.Yes:
                    self.save()
            self.text.clear()
            self.agreementId = None
            self.filename = None
        except Exception as err:
            print('closeFile, type(err).__name__, err.args')
        #Include the clear of all the dock windows

    @property
    def agreementData(self):
        return self._agreementData

    @agreementData.setter
    def agreementData(self, data):
        self._agreementData = data

    def messageBox(self, text, detailText ):
        pop = QMessageBox()
        pop.setText(str(text))
        pop.setDetailedText(detailText)
        pop.show()
        pop.exec_()

    def messageBoxYesNo(self, text, informationText):
        pop = QMessageBox()
        pop.setText(str(text))
        pop.setInformativeText(informationText)
        pop.setStandardButtons(QMessageBox.Yes|QMessageBox.No)
        pop.show()
        res = pop.exec()
        return res


    def setDockInvoices(self):
        colorInvDict = {'column': (11),
                        0: (QColor('white'), QColor('black')),
                        1: (QColor('black'), QColor('white'))}
        colInvDict = {0: ("Id", True, True, False, None),
                      1: ("Number", False, True, False, None),
                      2: ("Invoice Date", False, True, False, None),
                      3: ("Provider", False, False, False, None),
                      4: ("Total", False, True, 2, None),
                      5: ("From Date", True, True, False, None),
                      6: ("To Date", True, True, False, None),
                      7: ("Ex Rate", True, True, False, None),
                      8: ("Currency", True, True, False, None),
                      9: ("Inv Type", True, False, False, None),
                      10: ("Notes", True, False, False, None),
                      11: ("Closed", True, False, False, None),
                      12: ("Amount", True, True, False, None),
                      13: ("IVA $", True, True, False, None),
                      14: ("IVA%", True, True, False, None)}

        qryInvoice = self.getInvoices()
        self.tableInvoices = TableViewAndModel(colInvDict, colorInvDict, (100, 100), qryInvoice)
        self.tableInvoices.doubleClicked.connect(self.showInvoiceLines)
        self.dockInvoices.setWidget(self.tableInvoices)

    def refreshInvoicesTable(self):
        self.tableInvoices.model().setQuery(self.getInvoices())

    def setDockPayments(self):
        colorInvDict = {'column': (9),
                        0: (QColor('white'), QColor('black')),
                        1: (QColor('black'), QColor('white'))}
        colInvDict = {0: ("Id", True, True, False, None),
                      1: ("Date", False, True, False, None),
                      2: ("Bank", False, False, False, None),
                      3: ("Type", False, True, False, None),
                      4: ("Number", False, True, False, None),
                      5: ("$", False, True, True, None),
                      6: ("Total", False, True, 2, None),
                      7: ("Local", True, True, 2, None),
                      8: ("paytype", True, True, False, None),
                      9: ("paycurrency", True, True, False, None),
                      10: ("paybank", True, False, False, None),
                      11: ("Notes", True, False, False, None)}
        qryPay = self.getPayments()
        self.tablePayments = TableViewAndModel(colInvDict, colorInvDict, (100, 100), qryPay)
        self.tablePayments.doubleClicked.connect(self.showPaymentLines)
        self.dockPayment.setWidget(self.tablePayments)

    def setDockAccounts(self):
        try:
            colorDict = {'column': (3),
                        'In': (QColor('white'), QColor('black')),
                        'Ck': (QColor('black'), QColor('white')),
                        'Ch': (QColor('black'), QColor('white')),
                        'Tr': (QColor('black'), QColor('white'))}
            colDict = {0: ("Id", True, True, False, None),
                      1: ("tid", True, True, False, None),
                      2: ("Date", False, True, False, None),
                      3: ("Type", False, True, True, None),
                      4: ("Number", False, True, False, None),
                      5: ("Bank", False, False, False, None),
                      6: ("Debit", False, True, 2, None),
                      7: ("Credit", False, True, 2, None),
                      8: ("Balance", False, True, 2, None)}
            qry = self.getAccount()
            self.tableAccount = TableViewAndModel(colDict, colorDict, (100, 100), qry)
            self.tableAccount.doubleClicked.connect(self.showTransaction)
            self.dockAccount.setWidget(self.tableAccount)
        except Exception as err:
            print("setDockAccount", err.args)

    def updateAccounts(self, type):
        try:
            self.setDockHorses()
            self.setDockMortality()
            self.setDockRejection()
            if not self.isBreaking:
                self.setDockSales()
            self.dockAgreementHorses.raise_()
        except Exception as err:
            print('setDockWindows', type(err).__name__, err.args)

    def setDockHorses(self):
        try:
            centerColumns = []
            colDict = {0: ("ID", True, False, False,0),
                       1: ("RP", False, False, True, 45),
                       2:("Name", False, True, False,120),
                       3:("Sex", False, False, True, 45),
                       4:("Coat", False, False, False, 60),
                       5:("DOS", False, False, False, 80),
                       6:("Notes", True, False, False, 0),
                       7:("SexName", True, False, False, 0),
                       8:("Billable", True, False, False, 0),
                       9:("Broke", True, False, False, 0),
                       10: ("DOB", True, False, False, 0),
                       11: ("DOA", True, False, False, 0),
                       12: ("AccessID", True, False, False,0),
                       13: ("BreakerID", True, False, False, 0),
                       14: ("PlayerID", True, False, False, 0),
                       15: ("Active", True, False, False, 0),
                       16: ("horseid", True, False, False, 0),
                       17: ("Notes", True, True, False, None)}

            colorDict = colorDict = {'column':(15),
                        True :(QColor('white'), QColor('black')),
                        False:(QColor('black'), QColor('white'))}

            qryHorses =self.queryAgreementHorses()
            self.tableAgreementHorses = APM.TableViewAndModel(colDict, colorDict, (500, 300), qryHorses)
            self.tableAgreementHorses.setSelectionMode(QAbstractItemView.SingleSelection)
            self.tableAgreementHorses.doubleClicked.connect(self.getHorseData)
            self.tableAgreementHorses.horizontalHeader().setStyleSheet("QHeaderView {font-size: 8pt; text-align: center;}")
            self.tableAgreementHorses.verticalHeader().setVisible(False)
            self.dockAgreementHorses.setWidget(self.tableAgreementHorses)
        except Exception as err:
            print('setDockHorses',type(err).__name__, err.args)

    def setDockMortality(self):
        self.dockMortality.setWidget(self.setTableMortality())

    def setDockBreaking(self):
        self.dockBreaking.setWidget(self.setTableBreaking())

    def setDockClearance(self):
        self.dockClearance.setWidget(self.setTableClearance())

    def queryClearance(self):
        try:
            qry = QSqlQuery(self.qdb)
            qry.prepare("""SELECT
            h.rp, h.name,
            CASE 
                    WHEN h.sexid = 1 THEN _ucs2 x'2642'
                    WHEN h.sexid = 2 THEN _ucs2 x'2640'
                    WHEN h.sexid = 3 THEN _ucs2 x'265E'
            END Sex,
            CASE
                    WHEN c.reasonid = 0 THEN 'Breaking'
                    WHEN c.reasonid = 1 THEN 'Rejection'
            END Reason,
            CASE
                    WHEN c.reasonid = 0 THEN CASE
                                                WHEN c.typeid = 0 THEN 'Full Break'
                                                WHEN c.typeid = 1 THEN 'Half Break'
                                                WHEN c.typeid = 2 THEN 'Incomplete'
                                              END
            ELSE
                                              CASE 
                                                WHEN c.typeid = 0 THEN 'Final'
                                                WHEN c.typeid = 1 THEN 'Veterinary'
                                                WHEN C.TYPEID = 2 THEN 'Provisory'
                                               END                          
            END type,
            c.reasonid
            FROM horses h 
            INNER JOIN agreementhorses ah 
            ON h.id = ah.horseid
            INNER JOIN clearance c
            ON ah.id = c.agreementhorseid
            WHERE c.active
            AND ah.agreementid = ?
            ORDER BY c.typeid""")
            qry.addBindValue(QVariant(self.agreementId))
            qry.exec()
            if qry.lastError().type() != 0:
                raise DataError('queryClearance', qry.lastError().text())
            return qry
        except DataError as err:
            print(err.source, err.message)

    def setTableClearance(self):
        qry = self.queryClearance()
        colorDict = {'column': (5),
                     0: (QColor('blue'), QColor('white')),
                     1: (QColor('red'), QColor('yellow'))}

        colDict = {0:("RP", False, True, True, None),
                     1:("Horse", False, False, False, True),
                     2:("Sex", False, True, True, None),
                     3:("Reason", False, True, False, None),
                     4:("Status",False, True, False, None ),
                     5:("ReasonId", True, True, False, None)}
        table = TableViewAndModel(colDict,colorDict, (100, 100), qry)
        table.doubleClicked.connect(lambda : self.getClearanceDate(table))
        return table

    def queryBreaking(self):
        try:
            qry = QSqlQuery(self.qdb)
            qry.prepare(""" SELECT
            b.dor, h.name,
            TIMESTAMPDIFF(MONTH, ah.dos, b.dor) Months,
            CASE 
                    WHEN h.sexid = 1 THEN _ucs2 x'2642'
                    WHEN h.sexid = 2 THEN _ucs2 x'2640'
                    WHEN h.sexid = 3 THEN _ucs2 x'265E'
            END Sex,
            CASE
                WHEN b.type = 0 THEN 'Full'
                WHEN b.type = 1 THEN 'Half'
                WHEN b.type = 2 THEN 'Failed'
            END Type,
            CASE 
                WHEN b.rate = 0 THEN 'Excellent'
                WHEN b.rate = 1 THEN 'Very Good'
                WHEN b.rate = 2 THEN 'Good'
                WHEN b.rate = 3 THEN 'Fair'
                WHEN b.rate = 4 THEN 'Poor' 
            END rate,
            c.fullname Buster,
            b.type
            FROM horses h
            INNER JOIN agreementhorses ah
            ON h.id = ah.horseid
            LEFT     JOIN contacts c
            ON ah.breakerid = c.id
            INNER JOIN breaking b
            ON ah.id = b.agreementhorseid
            WHERE ah.agreementid = ? 
            ORDER BY b.dor, b.type""")
            qry.addBindValue(QVariant(self.agreementId))
            qry.exec()
            if qry.lastError().type() != 0:
                raise DataError('queryBreaking', qry.lastError().text())
            return qry
        except DataError as err:
            print(err.source, err.message)

    def setTableBreaking(self):
        try:
            qry = self.queryBreaking()
            colorDict = {'column': (7),
                         0: (QColor('blue'), QColor('white')),
                         1: (QColor('black'), QColor('white')),
                         2: (QColor('red'), QColor('yellow'))}
            colDict = {0:("Date", False, True, False, None),
                       1:("Horse", False, False, False, None),
                       2:("Months", False, True, True, None),
                       3:("Sex", False, True, True, None),
                       4:("Type", False, True, False, None),
                       5:("Rate", True, True, False, None),
                       6:("Buster", True, True, False, None),
                       7:("Code",True, True, False, None )}
            table = TableViewAndModel(colDict, colorDict,(100, 100), qry)
            table.doubleClicked.connect(lambda: self.getBreakingData(table))
            return table
        except DataError as err:
            print(err.source, err.message)
        except exception as err:
            print("setTableBreaking", err.args)

    def getBreakingData(self, table):
        pass

    def getClearanceData(self,table):
        pass

    def queryMortality(self):
        query = QSqlQuery(self.qdb)
        query.prepare("""
                SELECT m.dod, h.name,
                 CASE 
                    WHEN h.sexid = 1 THEN _ucs2 x'2642'
                    WHEN h.sexid = 2 THEN _ucs2 x'2640'
                    WHEN h.sexid = 3 THEN _ucs2 x'265E'
                END Sex, 
                CONCAT(TIMESTAMPDIFF(YEAR,h.dob, m.dod) , ' years') Age,
                CASE
                    WHEN m.causeid = 0 THEN 'Disease'
                    WHEN m.causeid = 1 THEN "Accident"
                    WHEN m.causeid = 2 THEN "Slaughter"
                    WHEN m.causeid = 3 THEN "Old Age"
                    WHEN m.causeid = 4 THEN "unknown"
                END Cause, 
                m.diagnose, 
                m.veterinaryid,
                m.notes, m.causeid, h.rp, c.coat, s.sex,
                m.id, h.id, ah.id
                FROM horses as h
                INNER JOIN sexes AS s
                ON h.sexid = s.id
                INNER JOIN coats AS c
                ON h.coatid = c.id
                INNER JOIN agreementhorses AS ah
                ON h.id = ah.horseid
                INNER JOIN mortality AS m
                ON ah.id =  m.agreementhorseid
                WHERE ah.agreementid = ?
                """)
        query.addBindValue(QVariant(self.agreementId))
        query.exec_()
        return query

    def setTableMortality(self):
        qry = self.queryMortality()
        colorDict = {'column': (8),
                     0 :(QColor('yellow'), QColor('black')),
                     1 :(QColor('red'), QColor('white')),
                     2 :(QColor('gray'),QColor('yellow')),
                     3 :(QColor('black'),QColor('white')),
                     4 :(QColor('lightgray'), QColor('black'))}
        colDict = {
            0: ("Date", False, True, True, None),
            1: ("Horse", False, False, False, None),
            2: ("Sex", False, True, True, None),
            3: ("Age", False, True, False, None),
            4: ("Cause", False, True, False, None),
            5: ("Diagnose", True, True, False, None),
            6: ("Vetid", True, True, False, None),
            7: ("Notes", True, True, False, None),
            8: ("Causeid", True, True, True, None),
            9: ("RP", True, True, False, None),
            10: ("Coat", True, True, False, None),
            11: ("Sex", True, True, False, None),
            12: ("MID", True, True, False, None),
            13: ("HID", True, True, False, None),
            14: ("AHD", True, True, False, None)}
        table = TableViewAndModel(colDict, colorDict, (300, 300), qry)
        table.doubleClicked.connect(lambda : self.getMortalityData(table))
        return table

    def getMortalityData(self, table):
        record = None
        try:
            row = table.currentIndex().row()
            model = table.model()
            model.query().isSelect()
            model.query().isActive()
            model.query().seek(row)
            record = model.query().record()
            res = self.messageBoxYesNo("Would check {}'s death record?".format(record.value(1)),
                                       'Check the data and/or enter/edit as necessary')
            if res != QMessageBox.Yes:
                return
            #horseid = record.value(0)
            detail = Mortality(self.qdb,self.agreementId, APM.OPEN_EDIT,
                               record, self.con_string, self)
            detail.show()
        except DataError as err:
            QMessageBox.warning(self, "DataError", "{}".format(err.message), QMessageBox.Ok)
        except Exception as err:
            print(err.args)

    def setDockRejection(self):
        self.dockRejection.setWidget(self.setTableRejection())

    def queryRejected(self):
        query = QSqlQuery(self.qdb)
        query.prepare("""
                 SELECT r.dor, h.name,
                  CASE 
                     WHEN h.sexid = 1 THEN _ucs2 x'2642'
                     WHEN h.sexid = 2 THEN _ucs2 x'2640'
                     WHEN h.sexid = 3 THEN _ucs2 x'265E'
                 END Sex, 
                 CONCAT(TIMESTAMPDIFF(YEAR,h.dob, r.dor) , ' years') Age,
                 CASE
                     WHEN r.typeid = 0 THEN _ucs2 x'2714'
                     WHEN r.typeid = 1 THEN _ucs2 x'271A'
                     WHEN r.typeid = 2 THEN  _ucs2 x'003F'
                 END Type,
                 CASE
                     WHEN r.causeid = 0 THEN 'Performance'
                     WHEN r.causeid = 1 THEN "Conformation"
                     WHEN r.causeid = 2 THEN "Disease"
                     WHEN r.causeid = 3 THEN "Injury"
                     WHEN r.causeid = 4 THEN "Unknown"
                 END Cause,      
                 r.rejectorid,
                 r.notes, r.causeid, r.typeid, h.rp, c.coat, s.sex,
                 r.id, h.id, ah.id
                 FROM horses as h
                 INNER JOIN sexes AS s
                 ON h.sexid = s.id
                 INNER JOIN coats AS c
                 ON h.coatid = c.id
                 INNER JOIN agreementhorses AS ah
                 ON h.id = ah.horseid
                 INNER JOIN rejection AS r
                 ON ah.id =  r.agreementhorseid
                 WHERE ah.agreementid = ?
                 """)
        query.addBindValue(QVariant(self.agreementId))
        query.exec_()
        return query

    def setTableRejection(self):
        qry = self.queryRejected()
        colorDict = {'column': (9),
                     0: (QColor('red'), QColor('white')),
                     1: (QColor('yellow'), QColor('black')),
                     2: (QColor('lightgreen'), QColor('black'))}
        colDict = {
            0: ("Date", False, True, True, None),
            1: ("Horse", False, False, False, None),
            2: ("Sex", False, True, True, None),
            3: ("Age", False, True, False, None),
            4: ("Type", False, True, True, None),
            5: ("Cause", False, True, False, None),
            6: ("Rejectorid", True, True, False, None),
            7: ("Notes", True, True, False, None),
            8: ("Causeid", True, True, True, None),
            9: ("typeid", True, True, True, None),
            10: ("RP", True, True, False, None),
            11: ("Coat", True, True, False, None),
            12: ("Sex", True, True, False, None),
            13: ("RID", True, True, False, None),
            14: ("HID", True, True, False, None),
            15: ("AHD", True, True, False, None)}
        table = TableViewAndModel(colDict, colorDict, (300, 300), qry)
        table.doubleClicked.connect(lambda: self.getRejectedData(table))

        return table

    def getRejectedData(self, table):
        record = None
        try:
            row = table.currentIndex().row()
            model = table.model()
            model.query().isSelect()
            model.query().isActive()
            model.query().seek(row)
            record = model.query().record()
            res = self.messageBoxYesNo("Would you check {}'s rejection record?".format(record.value(1)),
                                       'Check the data and/or enter/edit as necessary')
            if res != QMessageBox.Yes:
                return
            # horseid = record.value(0)
            detail = Reject(self.qdb, self.agreementId, APM.OPEN_EDIT,
                               record, self.con_string, self)
            detail.show()
        except DataError as err:
            QMessageBox.warning(self, "DataError", "{}".format(err.message), QMessageBox.Ok)
        except Exception as err:
            print(type(err).__name__, err.args)

    @pyqtSlot()
    def insertList(self):
        pass

    @pyqtSlot()
    def handleLocations(self, mode):
        res = Location(self.qdb, self.supplierId, mode=mode)
        res.show()
        #res.exec()

    @pyqtSlot()
    def chooseSupplier(self):
        try:
            qry = QSqlQuery(self.qdb)
            qry.exec("CALL chooseactivesupplier_getsuppliers()")
            if qry.lastError().type() != 0:
                raise DataError('choosesupplier', qry.lastError().text())
            if qry.first():
                print(qry.size())
            if qry.size() < 1:
                raise DataError('chooseSupplier', 'No Data')
            res = ChooseActiveSupplier(self.qdb,self, qry)
            res.show()
            res.exec()
            if self.supplierId:
                self.horseBar.setVisible(False)
                self.showAccountsDocks()
            else:
                self.setWindowTitle("Polo Horse Agreements Management")
        except DataError as err:
            print('chooseSupplier',err.source, err.message)
        except Exception as err:
            print('chooseSupplier', err.args)

    @pyqtSlot()
    def supplierData(self,type=None):
        try:
            res = Supplier(self.qdb, self.supplierId, type,parent=self)
            res.show()
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def transferHorse(self, mode):
        try:
            res = Transfer(self.qdb,self.supplierId,mode=mode,parent=self)
            res.show()
            res.exec()
        except DataError as err:
            QMessageBox.warning(self, "Error Message", "{} {}".format(err.source, err.message), QMessageBox.Ok)
        except Exception as err:
            print(type(err), err.args)

    @pyqtSlot(QModelIndex)
    def showInvoiceLines(self, idx):
        try:
            qry = self.tableInvoices.model().query()
            row = idx.row()
            if qry.seek(row):
                record = qry.record()
                self.addInvoice(APM.OPEN_EDIT, record)
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot(QModelIndex)
    def showTransaction(self, idx):
        try:
            qry = self.tableInvoices.model().query()
            row = idx.row()
            if qry.seek(row):
                record = qry.record()
                self.addInvoice(APM.OPEN_EDIT, record)
        except DataError as err:
            print(err.source, err.message)

    @property
    def supplier(self):
        return self._supplier

    @supplier.setter
    def supplier(self, data):
        self._supplier = data

    @pyqtSlot()
    def invoice(self, mode):
        #place the add/edit module connection
        pass

    @pyqtSlot()
    def payment(self, mode):
        try:
            res = Payment(self.qdb, self.supplierId, mode= APM.OPEN_NEW, parent=self)
            res.show()
            res.exec()
        except AttributeError as err:
            print(err.args)
        except Exception as err:
            print(type(err), err.args)

    def showPaymentLines(self):
        pass

    def showAccountsDocks(self):
        try:
            if self.supplierObjects:
                [obj.close() for obj in self.supplierObjects]
            if self.agreementObjects:
                [obj.close() for obj in self.agreementObjects]
            self.accountBar.setVisible(True)
            self.horses.menuAction().setVisible(False)
            self.accounts.menuAction().setVisible(True)

            self.dockAccount = QDockWidget("Account", self)
            self.dockAccount.setObjectName("dockAccount")
            self.dockAccount.setAcceptDrops(Qt.LeftDockWidgetArea)
            self.dockAccount.visibilityChanged.connect(lambda: self.checkDock(
                self.accountDockAction, self.dockAccount))
            self.addDockWidget(Qt.LeftDockWidgetArea, self.dockAccount)
            self.setDockAccounts()

            self.dockInvoices = QDockWidget("Invoices", self)
            self.dockInvoices.setObjectName("dockInvoices")
            self.dockInvoices.setAllowedAreas(Qt.LeftDockWidgetArea)
            self.dockInvoices.visibilityChanged.connect(lambda: self.checkDock(self.invoiceDockAction,
                                                                           self.dockInvoices))
            self.addDockWidget(Qt.LeftDockWidgetArea, self.dockInvoices)
            self.setDockInvoices()

            self.dockPayment = QDockWidget("Payments", self)
            self.dockPayment.setObjectName("dockPayment")
            #self.dockPayment.setAcceptDrops(Qt.LeftDockWidgetArea)
            self.dockPayment.visibilityChanged.connect(lambda: self.checkDock(
                self.paymentDockAction, self.dockPayment))
            self.addDockWidget(Qt.LeftDockWidgetArea, self.dockPayment)
            self.setDockPayments()

            self.tabifyDockWidget(self.dockAccount, self.dockInvoices)
            self.tabifyDockWidget(self.dockAccount, self.dockPayment)
            self.tabifyDockWidget(self.dockAccount, self.dockAgreement)

            self.supplierObjects = [self.dockAccount,
                                        self.dockPayment,
                                        self.dockInvoices]
            [obj.setMinimumWidth(500) for obj in self.supplierObjects ]

        except Exception as err:
            print(type(err), err.args)

    def prepareAgreementDocks(self):
        try:
            if self.agreementObjects:
                [obj.close() for obj in self.agreementObjects]
            if self.supplierObjects:
                [obj.close() for obj in self.supplierObjects]
            self.document.menuAction().setVisible(True)
            self.dockAgreement.setVisible(True)
            self.openDocumentAction.setEnabled(True)
            self.accountBar.setVisible(False)
            self.horseBar.setVisible(True)
            self.horses.menuAction().setVisible(True)
            self.accounts.menuAction().setVisible(False)
            self.chargesBar.setVisible(False)
        except Exception as err:
            print(type(err), err.args)

    def showAgreementDocks(self):
        try:
            if self.agreementObjects:
                [obj.close() for obj in self.agreementObjects]
            if self.supplierObjects:
                [obj.close() for obj in self.supplierObjects]
            self.horses.menuAction().setVisible(True)

            self.dockAgreementHorses = QDockWidget("Horses", self)
            self.dockAgreementHorses.setObjectName("dockAgreementHorses")
            self.dockAgreementHorses.setAllowedAreas(Qt.RightDockWidgetArea)
            self.dockAgreementHorses.setStyleSheet("DockWidget.title {font-size: 10pt}")
            self.dockAgreementHorses.visibilityChanged.connect(lambda: self.checkDock(
                self.agreementHorseDockAction, self.dockAgreementHorses))
            self.addDockWidget(Qt.RightDockWidgetArea, self.dockAgreementHorses)
            self.dockAgreementHorses.setStyleSheet("QDockWidget.windowTitle { font-size: 8pt; text-align: left;}")
            self.setDockHorses()

            self.dockMortality = QDockWidget("Mortality", self)
            self.dockMortality.setObjectName("dockMortality")
            self.dockMortality.setAcceptDrops(Qt.RightDockWidgetArea)
            self.dockMortality.visibilityChanged.connect(lambda: self.checkDock(
                self.mortalityDockAction, self.dockMortality))
            self.dockMortality.setMinimumWidth(400)
            self.addDockWidget(Qt.RightDockWidgetArea, self.dockMortality)
            self.setDockMortality()

            self.dockRejection = QDockWidget("Rejection", self)
            self.dockRejection.setObjectName("dockRejection")
            self.dockRejection.setAcceptDrops(Qt.RightDockWidgetArea)
            self.dockRejection.visibilityChanged.connect(lambda: self.checkDock(
                self.rejectDockAction, self.dockRejection))
            self.addDockWidget(Qt.RightDockWidgetArea, self.dockRejection)
            self.setDockRejection()

            if self.isBreaking:
                self.dockBreaking = QDockWidget("Breaking", self)
                self.dockBreaking.setObjectName("dockBreaking")
                self.dockBreaking.setAcceptDrops(Qt.RightDockWidgetArea)
                self.dockBreaking.visibilityChanged.connect(lambda: self.checkDock(
                    self.breakingDockAction, self.dockBreaking))
                self.dockBreaking.setMinimumWidth(400)
                self.addDockWidget(Qt.RightDockWidgetArea, self.dockBreaking)
                self.setDockBreaking()

                self.dockClearance = QDockWidget("Clearance", self)
                self.dockClearance.setObjectName("dockClearance")
                self.dockClearance.setAcceptDrops(Qt.RightDockWidgetArea)
                self.dockClearance.visibilityChanged.connect(lambda: self.checkDock(
                    self.clearanceDockAction, self.dockClearance))
                self.dockClearance.setMinimumWidth(400)
                self.addDockWidget(Qt.RightDockWidgetArea, self.dockClearance)
                self.setDockClearance()
            else:
                self.dockSales = QDockWidget("Sales", self)
                self.dockSales.setObjectName("dockSales")
                self.dockSales.setAcceptDrops(Qt.RightDockWidgetArea)
                self.dockSales.visibilityChanged.connect(lambda: self.checkDock(
                    self.salesDockAction, self.dockSales))
                self.setDockSales()

            self.agreementObjects = [self.dockAgreementHorses,
                                     self.dockMortality,
                                     self.dockRejection]
            if self.isBreaking:
                self.agreementObjects.append(self.dockBreaking)
                self.agreementObjects.append(self.dockClearance)
                self.tabifyDockWidget(self.dockRejection, self.dockBreaking)
                self.tabifyDockWidget(self.dockRejection, self.dockClearance)
            else:
                self.agreementObjects.append(self.dockSales)
                self.tabifyDockWidget(self.dockRejection, self.dockSales)
            self.tabifyDockWidget(self.dockRejection, self.dockMortality)
            self.tabifyDockWidget(self.dockRejection, self.dockAgreementHorses)
            #self.setDockViewMenu(False)
        except Exception as err:
            print(type(err), err.args)

    def editAgreement(self):
        pass

    @pyqtSlot()
    def addPayables(self, payableType, openMode):
        try:
            res = Payables(self.qdb, self.supplierId, payableType, mode=openMode,
                           con_string=self.con_string, parent=self)
            res.show()
            res.exec()
        except APM.DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print('addPayables', type(err).__name__, err.args)

    @pyqtSlot()
    def billOtherCharge(self, mode):
        try:
            res = OtherCharge(self.qdb,self.supplierId, mode, parent=self)
            res.show()
            res.exec()
        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print(type(err), err.args)

def main():
    app = QApplication(sys.argv)
    QCoreApplication.setOrganizationName("ErickSoft")
    QCoreApplication.setApplicationName("PoloManagement")
    window = MainWindow()
    window.show()
    app.exec_()

if __name__ == '__main__':
    main()
