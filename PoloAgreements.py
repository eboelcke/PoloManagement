import sys
import os
import traceback
from struct import Struct

from PyQt5.QtCore import (QVariant, Qt, pyqtSlot, QItemSelectionModel, QDir,QSize,
                          QItemSelection, QModelIndex, QAbstractItemModel, QCoreApplication,
                          QPoint, QSettings, pyqtSlot, QAbstractTableModel)
from PyQt5.QtGui import QColor
from PyQt5.QtSql import (QSqlDatabase,QSqlQueryModel, QSqlQuery)
#from PyQt5.QtSql import QSqlQueryModel,QSqlQuery , QSqlTableModel, QSqlError

from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableView, QAction, QFileSystemModel,
            QDockWidget, QAbstractItemView, QTreeView,  QTextEdit, QDialog,
            QFontComboBox, QComboBox, QColorDialog, QMessageBox, QMenu, QFileDialog)
from PyQt5.QtGui import (QFont, QIcon, QTextListFormat, QTextCharFormat,
                         QTextCursor, QImage, QContextMenuEvent)
from PyQt5.QtPrintSupport import QPrintPreviewDialog, QPrintDialog

from ext import Settings, pushdate, find, wordcount, table, newAgreement, APM
from ext.APM import TableViewAndModel, DataError
from ext.Horses import Horses, StartHorse, Mortality, Reject, Sales
from ext.HorseReports import AvailableHorses
from ext.CQSqlDatabase import Cdatabase
from ext.Contacts import Contacts, ShowContacts
from ext.BrokeReceive import ReceiveBroken
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
        if not self.check_connection():
            sys.exit()
        self.initUI()
        self.qdb.open()


    def check_connection(self):
        res = QDialog.Rejected
        settings = Settings.SettingsDialog()
        while self.qdb == None:
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
                else:
                    res = self.applicationSettings()
                    if res == QDialog.Rejected:
                        self.messageBox("Server not open", "Check the server status and the connection's parameters")
                        sys.exit()
            else:
                res = self.applicationSettings()
                if res == QDialog.Rejected:
                    self.messageBox("Database not open", "Check the database  and the connection's parameters")
                    sys.exit()
        return True

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
        self.setCentralWidget(self.text)
        self.initToolBar()
        self.initFormatBar()
        self.initAccountBar()
        self.initHorseBar()
        self.initPeopleBar()
        self.initMenuBar()
        self.statusBar = self.statusBar()

        self.dockInvoices = QDockWidget("Invoices",self)
        self.dockInvoices.setObjectName("dockInvoices")
        self.dockInvoices.setAllowedAreas(Qt.BottomDockWidgetArea)
        self.dockInvoices.visibilityChanged.connect(lambda : self.checkDock(self.invoiceDockAction,
                                                                            self.dockInvoices))
        self.queryInvoice = self.queryInvoices(self.qdb)
        self.modelInvoice = QSqlQueryModel()
        self.modelInvoice.setQuery(self.queryInvoice)
        self.modelInvoice.setHeaderData(0,Qt.Horizontal, "ID")
        self.modelInvoice.setHeaderData(1, Qt.Horizontal, "Name")
        self.tableInvoices = QTableView()
        self.tableInvoices.resizeRowsToContents()
        self.tableInvoices.fontMetrics()
        self.tableInvoices.setModel(self.modelInvoice)
        self.tableInvoices.verticalHeader().setVisible(False)
        self.tableInvoices.verticalHeader().setDefaultSectionSize(25)


        self.InvoiceSelectionModel = self.tableInvoices.selectionModel()
        self.InvoiceSelectionModel.currentChanged.connect(self.on_current_change)

        self.dockInvoices.setWidget(self.tableInvoices)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dockInvoices)

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

        self.dockAgreementHorses = QDockWidget("Horses", self)
        self.dockAgreementHorses.setObjectName("dockAgreementHorses")
        self.dockAgreementHorses.setAllowedAreas(Qt.RightDockWidgetArea)
        self.dockAgreementHorses.setStyleSheet("DockWidget.title {font-size: 10pt}")
        self.dockAgreementHorses.visibilityChanged.connect(lambda: self.checkDock(
            self.agreementHorseDockAction, self.dockAgreementHorses))

        self.addDockWidget(Qt.RightDockWidgetArea, self.dockAgreementHorses)
        self.dockAgreementHorses.setStyleSheet("QDockWidget.windowTitle { font-size: 8pt; text-align: left;}")


        self.dockAccount = QDockWidget("Account", self)
        self.dockAccount.setObjectName("dockAccount")
        self.dockAccount.setAcceptDrops(Qt.BottomDockWidgetArea)
        self.dockAccount.visibilityChanged.connect(lambda: self.checkDock(
            self.accountDockAction, self.dockAccount))

        self.queryAccount = self.queryAccounts()
        self.modelAccount = QSqlQueryModel()
        self.modelAccount.setQuery(self.queryAccount)

        self.tableAccount = QTableView()
        self.tableAccount.verticalHeader().setVisible(False)
        self.tableAccount.verticalHeader().setDefaultSectionSize(25)
        self.tableAccount.setModel(self.modelAccount)
        self.tableAccount.setMinimumHeight(100)

        self.dockAccount.setWidget(self.tableAccount)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dockAccount)

        self.dockPayment = QDockWidget("Payments", self)
        self.dockPayment.setObjectName("dockPayment")
        self.dockPayment.setAcceptDrops(Qt.BottomDockWidgetArea)
        self.dockPayment.visibilityChanged.connect(lambda: self.checkDock(
            self.paymentDockAction, self.dockPayment))

        self.queryPayment = self.queryPayments()
        self.modelPayment = QSqlQueryModel()
        self.modelPayment.setQuery(self.queryPayment)

        self.tablePayment = QTableView()
        self.tablePayment.verticalHeader().setVisible(False)
        self.tablePayment.verticalHeader().setDefaultSectionSize(25)
        self.tablePayment.setModel(self.modelPayment)
        self.tablePayment.setMinimumHeight(100)

        self.dockPayment.setWidget(self.tablePayment)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dockPayment)

        self.dockSales = QDockWidget("Sales", self)
        self.dockSales.setObjectName("dockSales")
        self.dockSales.setAcceptDrops(Qt.RightDockWidgetArea)
        self.dockSales.visibilityChanged.connect(lambda: self.checkDock(
            self.salesDockAction, self.dockSales))

        self.tableSales = QTableView()
        self.tableSales.verticalHeader().setVisible(False)
        self.tableSales.verticalHeader().setDefaultSectionSize(25)
        self.tableSales.setMinimumHeight(100)

        #self.dockSales.setWidget(self.tableSales)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dockSales)

        self.dockMortality = QDockWidget("Mortality", self)
        self.dockMortality.setObjectName("dockMortality")
        self.dockMortality.setAcceptDrops(Qt.RightDockWidgetArea)
        self.dockMortality.visibilityChanged.connect(lambda: self.checkDock(
            self.mortalityDockAction, self.dockMortality))
        self.dockMortality.setMinimumWidth(400)

        self.addDockWidget(Qt.RightDockWidgetArea, self.dockMortality)

        self.dockRejection = QDockWidget("Rejection", self)
        self.dockRejection.setObjectName("dockRejection")
        self.dockRejection.setAcceptDrops(Qt.RightDockWidgetArea)
        self.dockRejection.visibilityChanged.connect(lambda: self.checkDock(
            self.rejectDockAction, self.dockRejection))

        self.addDockWidget(Qt.RightDockWidgetArea, self.dockRejection)

        self.settings = QSettings("config.ini", QSettings.IniFormat)
        if not self.settings.value("geometry") == None:
            self.restoreGeometry(self.settings.value("geometry"))
        if not self.settings.value("windowState") == None:
            self.restoreState(self.settings.value("windowState"))
        self.setFont(fd)

        self.tabifyDockWidget(self.dockRejection, self.dockSales)
        self.tabifyDockWidget(self.dockRejection, self.dockMortality)
        self.tabifyDockWidget(self.dockRejection, self.dockAgreementHorses)
        self.setMinimumHeight(700)
        self.text.setContextMenuPolicy(Qt.CustomContextMenu)
        self.text.customContextMenuRequested.connect(self.context)
        if self.qdb.isOpen():
            self.qdb.close()


    def initToolBar(self):
        self.toolBar = self.addToolBar("Options")
        self.toolBar.setObjectName('Options')
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


        self.printAction = QAction(QIcon("icons/print.png"), 'Print', self)
        self.printAction.setStatusTip("Print document.")
        self.printAction.setShortcut("Ctrl+P")
        self.printAction.triggered.connect(self.print)

        self.previewAction = QAction(QIcon("icons/preview.png"), "Preview", self)
        self.previewAction.setStatusTip("Preview document")
        self.previewAction.setShortcut("Ctrl+Shift+P")
        self.previewAction.triggered.connect(self.preview)

        self.cutAction = QAction(QIcon("icons/cut.png"), 'Cut', self)
        self.cutAction.setStatusTip("Delete and copy text to clipboard")
        self.cutAction.setShortcut("Ctrl+X")
        self.cutAction.triggered.connect(self.text.cut)

        self.copyAction = QAction(QIcon("icons/copy.png"), "Copy", self)
        self.copyAction.setStatusTip("Copy text to clipboard")
        self.copyAction.setShortcut("Ctrl+C")
        self.copyAction.triggered.connect(self.text.copy)

        self.pasteAction = QAction(QIcon("icons/paste.png"), "Paste", self)
        self.pasteAction.setStatusTip("Paste into the text cursor")
        self.pasteAction.setShortcut("Ctrl+V")
        self.pasteAction.triggered.connect(self.text.paste)

        self.undoAction = QAction(QIcon("icons/undo.png"), "Undo", self)
        self.undoAction.setStatusTip("Undo last Action")
        self.undoAction.setShortcut("Ctrl+Z")
        self.undoAction.triggered.connect(self.text.undo)

        self.redoAction = QAction(QIcon("icons/redo.png"), "Redo, self")
        self.redoAction.setStatusTip("Redo las undo action")
        self.redoAction.setShortcut("Ctrl+Y")
        self.redoAction.triggered.connect(self.text.redo)

        self.bulletAction = QAction(QIcon("Icons/bullet.png"), "Bullet list", self)
        self.bulletAction.setStatusTip("Insert bullet list")
        self.bulletAction.setShortcut("Ctrl*B")
        self.bulletAction.triggered.connect(self.bulletList)

        self.numberedAction = QAction(QIcon("icons/number.png"),"Numbered list", self)
        self.numberedAction.setStatusTip("Insert a numbered list")
        self.numberedAction.setShortcut("Ctrl+L")
        self.numberedAction.triggered.connect(self.numberedList)

        self.quitAction = QAction(QIcon("icons/btn_close.png"), "Quit", self)
        self.quitAction.shortcut = "Ctrl+Q"
        self.quitAction.statusTip = "Exits the application"
        self.quitAction.triggered.connect(self.close)

        self.settingsAction  = QAction(QIcon("icons/settings.png"), "Settings", self)
        self.settingsAction.setStatusTip("Settings")
        self.settingsAction.setShortcut("Application Settings")
        self.settingsAction.triggered.connect(self.applicationSettings)

        self.deleteAction = QAction(QIcon("icons/delete.png"), "Delete", self)
        self.deleteAction.setStatusTip("Delete selected area")
        self.deleteAction.setShortcut("Ctrl+D")
        self.deleteAction.triggered.connect(self.removeText)

        self.findAction = QAction(QIcon("icons/find.png"),"Find and Replaced", self)
        self.findAction.setStatusTip("Find and Replace")
        self.findAction.setShortcut("Ctrl+F")
        self.findAction.triggered.connect(find.Find(self).show)

        imageAction = QAction(QIcon("icons/image.png"), "Insert image", self)
        imageAction.setStatusTip("Insert and image")
        imageAction.setShortcut("Ctrl+Shift+I")
        imageAction.triggered.connect(self.insertImage)

        wordCountAction = QAction(QIcon("icons/count.png"), "Words/Characters count", self)
        wordCountAction.setStatusTip("Word/Characteer count")
        wordCountAction.setShortcut("Ctrl+W")
        wordCountAction.triggered.connect(self.wordCount)

        tableAction = QAction(QIcon("icons/table.png"), "Insert Table", self)
        tableAction.setStatusTip("Insert Table")
        tableAction.setShortcut("Ctrl+I")
        tableAction.triggered.connect(table.Table(self).show)

        listAction = QAction("Insert List",self)
        listAction.setStatusTip("Insert a horse list")
        listAction.setShortcut("Ctrl + L")
        listAction.triggered.connect(self.insertList)

        dateTimeAction = QAction(QIcon("icons/calender.png"),"Date and Time", self)
        dateTimeAction.setStatusTip("Insert Date and Time")
        dateTimeAction.setShortcut("Ctrl+D")
        dateTimeAction.triggered.connect(pushdate.DateTime(self).show)

        self.toolBar.addAction(self.newAction)
        self.toolBar.addAction(self.openAction)
        self.toolBar.addAction(self.saveAction)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.printAction)
        self.toolBar.addAction(self.previewAction)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.undoAction)
        self.toolBar.addAction(self.redoAction)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.pasteAction)
        self.toolBar.addAction(self.cutAction)
        self.toolBar.addAction(self.copyAction)
        self.toolBar.addAction(self.deleteAction)
        self.toolBar.addAction(self.bulletAction)
        self.toolBar.addAction(self.numberedAction)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.findAction)
        self.toolBar.addAction(self.settingsAction)
        self.toolBar.addAction(imageAction)
        self.toolBar.addAction(wordCountAction)
        self.toolBar.addAction(tableAction)
        self.toolBar.addAction(listAction)
        self.toolBar.addAction(dateTimeAction)
        self.addToolBarBreak()


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
        self.addToolBarBreak()

    def initAccountBar(self):
        self.accountBar = self.addToolBar('Account')
        self.accountBar.setObjectName("Account")

        self.invoiceAction = QAction(QIcon(":/Icons8/Accounts/invoice.png"), "Invoice", self)
        self.invoiceAction.setStatusTip("Receive Invoice")
        self.invoiceAction.triggered.connect(self.invoice)

        self.paymentAction = QAction(QIcon(":/Icons8/Accounts/cash.png"), 'Payment', self)
        self.paymentAction.setStatusTip("Receive Payment")
        self.paymentAction.triggered.connect(self.payment)

        self.accountAction = QAction(QIcon(":/Icons8/Accounts/ledger.png"),'Account', self)
        self.accountAction.setStatusTip("Show Agreement Account")
        self.accountAction.triggered.connect(self.account)

        self.accountBar.addAction(self.invoiceAction)
        self.accountBar.addAction(self.paymentAction)
        self.accountBar.addAction(self.accountAction)

    def initHorseBar(self):
        self.horseBar = self.addToolBar('Horse Management')
        self.horseBar.setObjectName("Management")

        self.startAction = QAction(QIcon(":Icons8/transport.png"), "Movements Horse", self)
        self.startAction.setStatusTip("Horse Starting Date")
        self.startAction.triggered.connect(self.startHorse)

        self.saleAction = QAction(QIcon(":/Icons8/Sales/sales.png"), "Horse Sale", self)
        self.saleAction.setStatusTip("Agreement Horse Sale")
        self.saleAction.triggered.connect(self.saleHorse)

        self.rejectAction = QAction(QIcon(":/Icons8/Horses/reject.png"), "Reject Horse", self)
        self.rejectAction.setStatusTip("Agreement Horse Rejection")
        self.rejectAction.triggered.connect(self.rejectHorse)

        self.deathAction = QAction(QIcon(":/Icons8/Horses/dead.png"), "Death", self)
        self.deathAction.setStatusTip("Agreement Horse Death")
        self.deathAction.triggered.connect(self.deadHorse)

        self.breakingAction = QAction(QIcon(":/Icons8/Horses/breaking.png"), "Receive Broke Horse", self)
        self.breakingAction.setStatusTip("Receive Broke Horse")
        self.breakingAction.triggered.connect(self.receiveBrokeHorse)

        self.addHorseAction = QAction(QIcon(":/Icons8/Horses/newhorse.png"), "Increase Horse Inventory", self)
        self.addHorseAction.setStatusTip("Update available Inventory")
        self.addHorseAction.triggered.connect(lambda: self.updateHorseInventory(APM.OPEN_NEW))

        self.brokeHorseReceivingAction = QAction(QIcon(":/Icons8/Horses/BrokeHorse.png"),
                                                  "Broke Horse Receiving", self)
        self.brokeHorseReceivingAction.setStatusTip("Receive broken horses")
        self.brokeHorseReceivingAction.triggered.connect(self.brokenHorseReceiving)

        self.horseBar.addAction(self.startAction)
        self.horseBar.addAction(self.saleAction)
        self.horseBar.addAction(self.addHorseAction)
        self.horseBar.addAction(self.breakingAction)
        self.horseBar.addAction(self.brokeHorseReceivingAction)
        self.horseBar.addAction(self.rejectAction)
        self.horseBar.addAction(self.deathAction)

    def initPeopleBar(self):
        self.newContactAction = QAction(QIcon(":/Icons8/People/addcontact.png"),"New Contact",self)
        self.newContactAction.triggered.connect(lambda: self.contact(APM.OPEN_NEW))

        self.editContactAction = QAction(QIcon(":/Icons8/People/editcontact.png"),"Edit Contact", self)
        self.editContactAction.triggered.connect(lambda: self.contact(APM.OPEN_EDIT))

        self.managerAction = QAction(QIcon(":/Icons8/People/manager.png"),"List of Managers", self)
        self.managerAction.triggered.connect(lambda: self.showContacts(APM.CONTACT_RESPONSIBLE))

        self.playerAction = QAction(QIcon(":/Icons8/People/PlayerSeller.png"),"Polo Players", self)
        self.playerAction.triggered.connect(lambda: self.showContacts(APM.CONTACT_PLAYER))

        self.breakerAction = QAction(QIcon(":/Icons8/People/HorseBreaker.png"), "Horse Breakers", self)
        self.breakerAction.triggered.connect(lambda: self.showContacts(APM.CONTACT_BREAKER))

        #self.sellerAction = QAction(QIcon(":/Icons8/People/Seller.png"), "Horse Sellers", self)
        #self.sellerAction.triggered.connect(lambda: self.showContacts(APM.CONTACT_SELLER))

        self.dealerAction = QAction(QIcon(":/Icons8/People/Dealer.png"), "Horse Dealers", self)
        self.dealerAction.triggered.connect(lambda: self.showContacts(APM.CONTACT_DEALER))

        self.buyerAction = QAction(QIcon(":/Icons8/People/farmer.png"), "Horse Buyers", self)
        self.buyerAction.triggered.connect(lambda: self.showContacts(APM.CONTACT_BUYER))


        self.peopleToolBar = self.addToolBar("Contacts")
        self.peopleToolBar.setObjectName("contacts")
        self.peopleToolBar.addAction(self.newContactAction)
        self.peopleToolBar.addAction(self.editContactAction)
        self.peopleToolBar.addAction(self.playerAction)
        self.peopleToolBar.addAction(self.breakerAction)
        self.peopleToolBar.addAction(self.managerAction)
        self.peopleToolBar.addAction(self.buyerAction)
        self.peopleToolBar.addAction(self.dealerAction)



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
        self.agreementHorseDockAction.triggered.connect(lambda :self.toggleDock(self.dockAgreementHorses))

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

        self.closeResultsDockAction = QAction("Close Results ")
        self.closeResultsDockAction.triggered.connect(lambda : self.closeAll([
            self.dockSales,
            self.dockMortality,
            self.dockRejection],
            self.salesDockAction,
             [self.mortalityDockAction,
             self.rejectDockAction]))
        
        self.closeAccountDockAction = QAction("Close Account")
        self.closeAccountDockAction.triggered.connect(lambda : self.closeAll(
            [self.dockAccount,
             self.dockPayment,
             self.dockInvoices],
        [self.accountDockAction,
         self.invoiceDockAction,
         self.paymentDockAction]))


        editHorseAction = QAction('Edit Horse', self)
        editHorseAction.triggered.connect(lambda: self.updateHorseInventory(APM.OPEN_EDIT))
        importHorseAction = QAction('Import Horse', self)
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
        file.addSeparator()
        file.addAction(self.settingsAction)
        file.addAction(self.quitAction)

        document = menuBar.addMenu("Document")
        document.addAction(selectAllAction)
        document.addAction(self.copyAction)
        document.addAction(self.cutAction)
        document.addAction(self.pasteAction)
        document.addAction(self.deleteAction)
        document.addAction(self.undoAction)
        document.addAction(self.redoAction)
        document.addAction(self.findAction)
        document.addSeparator()
        document.addAction(self.previewAction)
        document.addAction(self.printAction)

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
        view.addAction(self.agreementHorseDockAction)
        view.addSeparator()
        view.addAction(self.invoiceDockAction)
        view.addAction(self.paymentDockAction)
        view.addAction(self.accountDockAction)
        view.addAction(self.closeAccountDockAction)
        view.addSeparator()
        view.addActions([self.salesDockAction, self.mortalityDockAction,
                         self.rejectDockAction,self.closeResultsDockAction])
        inventory = menuBar.addMenu('Horse Inventory')
        inventory.addAction(allAvailableHorsesAction)
        inventory.addAction(allBreakingHorsesAction)
        inventory.addAction(allPlayingHorsesAction)

        horses = menuBar.addMenu("Horses")
        horses.addAction(self.addHorseAction)
        horses.addAction(editHorseAction)
        horses.addAction(self.startAction)
        horses.addAction(self.brokeHorseReceivingAction)
        horses.addAction(self.saleAction)
        horses.addAction(self.rejectAction)
        horses.addAction(self.deathAction)

        contacts = menuBar.addMenu("People")
        contacts.addAction(self.newContactAction)
        contacts.addAction(self.editContactAction)
        contacts.addSeparator()
        contacts.addAction(self.playerAction)
        contacts.addAction(self.breakerAction)
        contacts.addAction(self.managerAction)
        contacts.addSeparator()
        contacts.addAction(self.buyerAction)
        #contacts.addAction(self.sellerAction)
        contacts.addAction(self.dealerAction)

        help = menuBar.addMenu("Help")

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
        rpt = AvailableHorses(self.qdb, mode, self)
        rpt.show()
        rpt.exec()


    @pyqtSlot()
    def brokenHorseReceiving(self):
        try:
            h = ReceiveBroken(self.qdb, self.con_string,self.agreementId)
            h.show()
            h.exec()
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
            horseid = record.value(0)
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
    def invoice(self):
        pass

    @pyqtSlot()
    def payment(self):
        pass

    @pyqtSlot()
    def showAccount(self):
        pass

    @pyqtSlot()
    def saleHorse(self):
        try:
            sh = Sales(self.qdb, self.agreementId, con_string=self.con_string, parent=self)
            sh.show()
            sh.exec()
        except APM.DataError as err:
            if err.type == 1:
                self.showError(err)
            return


    @pyqtSlot()
    def rejectHorse(self):
        try:
            detail = Reject(self.qdb, self.agreementId, con_string=self.con_string, parent=self)
            detail.show()
            detail.exec()
        except APM.DataError as err:
            if err.type == 1:
                self.showError(err)
            return

    @pyqtSlot()
    def deadHorse(self):
        try:
            detail = Mortality(self.qdb, self.agreementId, con_string = self.con_string,  parent= self)
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
        state = dock.isVisible()
        dock.setVisible(not state)

    @pyqtSlot()
    def closeAll(self, lst, actlst):
        [dock.setVisible(False) for dock in lst]
        [act.setChecked(False) for act in actlst]

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
            settWindow = Settings.SettingsDialog()
            settWindow.show()
            res = settWindow.exec_()

        except Exception as err:
            print(err        )
        return res

    @pyqtSlot()
    def invoice(self):
        pass

    @pyqtSlot()
    def payment(self):
        pass

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
            new = newAgreement.Agreement(self.qdb, self.address, parent=None)
            new.show()
            result = new.exec_()
            if result:
                self.setWindowTitle(new.lineAgreement.text())
                self.agreementId = new.getID
                self.filename = os.path.join(self.agreementsPath, os.path.basename(new.getFilename))
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
            self.setDockWindows()
        except Exception as err:
            print('open_file', type(err).__name__)

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
                print('open method: {}'.format(err))
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

    def queryInvoices(self,qdb):
        query = QSqlQuery()
        query.prepare("""
        SELECT id, nombre, rp, sba FROM CABALLOS 
        WHERE propietarioID = ? 
         AND existencia = True
         ORDER BY Nombre""")
        query.addBindValue('4')
        query.exec_()
        return query

    def queryAgreementHorses(self):
        with Cdatabase(self.qdb) as cdb:
            qry = QSqlQuery(cdb)
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
            ah.active as Active
            FROM agreementhorses as ah
            INNER JOIN horses as h ON ah.horseid = h.id
            INNER JOIN coats as c ON h.coatid = c.id
            INNER JOIN sexes as s ON h.sexid = s.id
            INNER JOIN agreements as a on ah.agreementid = a.id
            WHERE ah.agreementid = ?""")
            qry.addBindValue(QVariant(self.agreementId))
            qry.exec_()
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
        with Cdatabase(self.qdb, 'sales') as db:
            query= QSqlQuery(db)
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
                sa.typeid,
                sa.comissionpercent,
                sa.comission,
                sa.expenses,
                sa.documentid,
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
        return query

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
        self.treeViewAgr.model().setRootPath(QDir.path(QDir(self.agreementsPath)))

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

            insertRowAction = QAction("Inser Row", self)
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

    def setDockWindows(self):
        try:
            self.setDockHorses()
            self.setDockMortality()
            self.setDockRejection()
            self.setDockSales()
            self.dockAgreementHorses.raise_()
        except Exception as err:
            print('setDockWindows', type(err).__name__)

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
                       15: ("Active", True, False, False, 0),}

            colorDict = colorDict = {'column':(3),
                        u'\u2640':(QColor('pink'), QColor('black')),
                        u'\u2642':(QColor('lightskyblue'), QColor('black')),
                        u'\u265E': (QColor('lightgrey'), QColor('black'))}
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

    def queryMortality(self):
        with Cdatabase(self.qdb, 'mortality') as db:
            query = QSqlQuery(db)
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
        with Cdatabase(self.qdb, 'rejection') as db:
            query = QSqlQuery(db)
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
            res = self.messageBoxYesNo("Would check {}'s rejection record?".format(record.value(1)),
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


def main():
    app = QApplication(sys.argv)
    QCoreApplication.setOrganizationName("ErickSoft")
    QCoreApplication.setApplicationName("PoloManagement")
    window = MainWindow()
    window.show()
    app.exec_()

if __name__ == '__main__':
    main()
