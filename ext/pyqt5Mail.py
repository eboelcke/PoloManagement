import sys
import os
import re
import struct
from struct import Struct
from PyQt5.QtWidgets import (QDialog, QMessageBox, QLineEdit, QTextEdit, QComboBox,
                             QLabel, QMainWindow, QColorDialog,
                             QFontComboBox, QMenu, QFileDialog, QAction)
from PyQt5.QtCore import QSettings, QDate, pyqtSlot, Qt, QPoint, QDateTime
from PyQt5.QtGui import QFont, QIcon, QImage, QTextCursor, QTextListFormat,\
    QTextCharFormat, QContextMenuEvent
from PyQt5.QtPrintSupport import QPrintPreviewDialog, QPrintDialog
from PyQt5.QtSql import QSqlQuery
import yagmail
from smtplib import SMTPAuthenticationError
from ext.Settings import SettingsDialog
from ext.find import Find
from ext.table import Table
from ext.pushdate import DateTime
from ext.wordcount import WordCount
from ext.APM import FocusCombo, DataError, LineEditHover
from ext.mailSettings import MailSettings
import poloresurce


class SendMail(QMainWindow):
    MAGIC = 'pad\x00'.encode('UTF-8')

    def __init__(self, db, address=None, pwd=None, msg=None, token=None , id=None, parent=None):
        super().__init__()
        self.msg=msg
        self.db = db
        self.address = address
        self.pwd = pwd
        self.token = token
        self.parent = parent
        self.filename = None
        self.eMailFolder = None
        self.attachedFiles = {}
        self.toId = id
        self.address = []
        self.loadData()
        self.sentDateAndTime = None
        self.changesSaved = True
        self.setUI()

    def setUI(self):
        self.setGeometry(100, 100, 1030, 800)
        self.setMinimumHeight(700)
        self.setWindowTitle("Email")
        self.setWindowIcon(QIcon(":Icons8/Stable.png"))
        f = QFont("Tahoma", 7, QFont.Light)
        fd = QFont("Tahoma", 8, QFont.Light)
        self.text = QTextEdit()
        self.text.setTabStopWidth(33)
        self.text.cursorPositionChanged.connect(self.cursorPosition)
        self.text.textChanged.connect(self.changed)
        self.text.setStyleSheet("QTextEdit {selection-background-color: blue; selection-color:yellow;}")
        self.text.setContextMenuPolicy(Qt.CustomContextMenu)
        self.text.customContextMenuRequested.connect(self.context)
        self.text.setEnabled(True)

        self.lineFrom = QLineEdit()
        self.lineFrom.setText(self.address[0])
        self.lineFrom.setMaximumWidth(500)
        self.lineFrom.setEnabled(False)

        self.lineTo = LineEditHover()
        self.lineTo.setObjectName("To")
        self.lineTo.cursorPositionChanged.connect(self.searchDelete)

        self.lineCc = LineEditHover()
        self.lineCc.setObjectName("Cc")
        self.lineCc.cursorPositionChanged.connect(self.searchDelete)

        self.lineSubject = QLineEdit()

        self.lineAttached = LineEditHover()
        self.lineAttached.setObjectName("Attached")
        self.lineAttached.keyDeleteDown.connect(self.deleteEntry)
        self.lineAttached.cursorPositionChanged.connect(self.searchDelete)

        self.comboFrom = FocusCombo(itemList=[self.address[0]])
        self.comboFrom.setModelColumn(1)
        self.comboFrom.setCurrentIndex(0)
        self.comboFrom.setFixedWidth(250)

        self.comboTo = FocusCombo()
        self.comboTo.model().setQuery(self.getContacts())
        self.comboTo.setModelColumn(1)
        self.comboTo.activated.connect(self.getToAddress)
        self.comboTo.setFixedWidth(250)
        if self.toId:
            self.comboTo.setCurrentIndex(self.comboTo.seekData(self.toId,0))
            self.lineTo.setText(self.comboTo.currentText() + ' (' + self.comboTo.getHiddenData(2) + ')')

        self.comboCc = FocusCombo()
        self.comboCc.model().setQuery(self.getContacts())
        self.comboCc.setModelColumn(1)
        self.comboCc.activated.connect(self.getCcAddress)
        self.comboCc.setFixedWidth(250)

        self.initDocumentBar()
        self.initFormatBar()
        self.initMenu()
        self.statusBar = self.statusBar()
        self.setCentralWidget(self.text)
        if self.msg:
            self.text.setText(self.msg)
            self.changesSaved = True

    def loadData(self):
        try:
            settings = QSettings("ext/config.ini", QSettings.IniFormat)
            self.address.append(settings.value("email/address"))
            self.address.append(settings.value("email/password"))
            self.address.append(settings.value("email/outh2_token"))
            self.eMailFolder = settings.value("email/draftfolder")
        except Exception as err:
            print("SendMail: loadData", err.args)


    def changed(self):
        self.changesSaved = False

    def initMenu(self):

        self.newAction = QAction(QIcon(":/Icons8/Agreement/document.png"), "New Mail", self)
        self.newAction.setStatusTip("Open New Mail")
        self.newAction.setShortcut("Ctrl+N")
        self.newAction.triggered.connect(self.newMail)

        self.openAction = QAction(QIcon(":/Icons8/email/openMail.png"),"Open eMail", self)
        self.openAction.setStatusTip("Open Saved Mail")
        self.openAction.setShortcut("Ctrl+O")
        self.openAction.triggered.connect(self.openMail)

        self.resetAction = QAction(QIcon(":Icons8/Edit/eraser.png"), "Clear Email", self)
        self.resetAction.setStatusTip("Clear mail contents")
        self.resetAction.setShortcut("Ctrl+E")
        self.resetAction.triggered.connect(self.resetMail)

        self.saveAction = QAction(QIcon(":/Icons8/email/draftMail.png"), "Save Mail", self)
        self.saveAction.setObjectName("saveMail")
        self.saveAction.setStatusTip("Save Mail")
        self.saveAction.setShortcut("Ctrl+S")
        self.saveAction.triggered.connect(self.saveMail)

        self.deleteAction = QAction(QIcon(":/Icons8/email/deleteMail.png"), "Delete saved Mail", self)
        self.deleteAction.setStatusTip("Delete Saved Mail")
        self.deleteAction.setShortcut("Ctrl+D")
        self.deleteAction.triggered.connect(self.deleteMail)


        self.closeAction = QAction(QIcon(":/Icons8/File/closefile.png"), "Close Mail", self)
        self.closeAction.setObjectName("closeMail")
        self.closeAction.setStatusTip("Close Mail")
        self.closeAction.setShortcut("Ctrl+C")
        self.closeAction.triggered.connect(self.closeMail)

        self.settingsAction = QAction(QIcon(":/Icons8/Settings/settings.png"), "EMail Settings", self)
        self.settingsAction.setStatusTip("Settings")
        self.settingsAction.setShortcut("Ctrl+S")
        self.settingsAction.triggered.connect(self.setSettings)

        self.formatBarAction = QAction("Toggle Format Bar", self)
        self.formatBarAction.setCheckable(True)
        self.formatBarAction.setChecked(False)
        self.formatBarAction.triggered.connect(self.toggleFormatBar)

        toggleDocumentBarAction = QAction("Document Toolbar", self)
        toggleDocumentBarAction.setCheckable(True)
        toggleDocumentBarAction.setChecked(True)
        toggleDocumentBarAction.setStatusTip("Toggle Document Bar")
        toggleDocumentBarAction.setShortcut("Ctrl+D")
        toggleDocumentBarAction.triggered.connect(self.toggleDocumentBar)

        file = self.menuBar().addMenu("File")
        file.addAction(self.newAction)
        file.addAction(self.openAction)
        file.addAction(self.saveAction)
        file.addAction(self.resetAction)
        file.addAction(self.deleteAction)
        file.addAction(self.closeAction)

        file.addSeparator()
        file.addAction(self.settingsAction)
        file.addAction(self.quitAction)

        view = self.menuBar().addMenu("View")
        view.addAction(self.openDocumentAction)
        view.addAction(toggleDocumentBarAction)
        view.addAction(self.formatBarAction)

        edit = self.menuBar().addMenu("Edit")
        edit.addAction(self.undoAction)
        edit.addAction(self.redoAction)
        edit.addSeparator()
        edit.addAction(self.copyAction)
        edit.addAction(self.pasteAction)
        edit.addAction(self.cutAction)
        edit.addAction(self.deleteAction)
        edit.addSeparator()

        tools = self.menuBar().addMenu("Tools")
        tools.addAction(self.findAction)
        tools.addAction(self.wordCountAction)
        tools.addAction(self.dateTimeAction)
        tools.addSeparator()
        tools.addAction(self.bulletAction)
        tools.addAction(self.numberedAction)
        tools.addAction(self.imageAction)
        tools.addAction(self.tableAction)

        format= self.menuBar().addMenu("Format")
        format.addAction(self.formatBarAction)

        insert = self.menuBar().addMenu("Insert")
        insert.addAction(self.attachmentAction)

    @pyqtSlot()
    def toggleFormatBar(self):
        state = self.formatBar.isVisible()
        self.formatBar.setVisible(not state)

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
                if cell.rowSpan() > 1 or cell.columnSpan() > 1:
                    splitAction.triggered.connect(lambda: table.splitCell(cell.row(), cell.col(), 1, 1))
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

    def initDocumentBar(self):
        self.openDocumentAction = QAction(QIcon(":/Icons8/Agreement/document.png"), "Document",self)
        self.openDocumentAction.setToolTip("Toggle Agreement document for editing")
        self.openDocumentAction.setEnabled(True)
        self.openDocumentAction.triggered.connect(self.setDocumentBars)

        self.attachmentAction = QAction(QIcon(":/Icons8/email/send_clip.png"), "Attach File",self)
        self.attachmentAction.setStatusTip("Attach a file to the mail")
        self.attachmentAction.setShortcut("Ctrl+A")
        self.attachmentAction.triggered.connect(self.attachFile)

        self.printAction = QAction(QIcon("icons/print.png"), 'Print', self)
        self.printAction.setStatusTip("Print document.")
        self.printAction.setShortcut("Ctrl+P")
        self.printAction.setEnabled(True)
        self.printAction.triggered.connect(self.printMail)

        self.previewAction = QAction(QIcon("icons/preview.png"), "Preview", self)
        self.previewAction.setStatusTip("Preview document")
        self.previewAction.setShortcut("Ctrl+Shift+P")
        self.previewAction.setEnabled(True)
        self.previewAction.triggered.connect(self.preview)

        self.cutAction = QAction(QIcon("icons/cut.png"), 'Cut', self)
        self.cutAction.setStatusTip("Delete and copy text to clipboard")
        self.cutAction.setShortcut("Ctrl+X")
        self.cutAction.setEnabled(True)
        self.cutAction.triggered.connect(self.text.cut)

        self.copyAction = QAction(QIcon("icons/copy.png"), "Copy", self)
        self.copyAction.setStatusTip("Copy text to clipboard")
        self.copyAction.setShortcut("Ctrl+C")
        self.copyAction.setEnabled(True)
        self.copyAction.triggered.connect(self.text.copy)

        self.pasteAction = QAction(QIcon("icons/paste.png"), "Paste", self)
        self.pasteAction.setStatusTip("Paste into the text cursor")
        self.pasteAction.setShortcut("Ctrl+V")
        self.pasteAction.setEnabled(True)
        self.pasteAction.triggered.connect(self.text.paste)

        self.undoAction = QAction(QIcon("icons/undo.png"), "Undo", self)
        self.undoAction.setStatusTip("Undo last Action")
        self.undoAction.setShortcut("Ctrl+Z")
        self.undoAction.setEnabled(True)
        self.undoAction.triggered.connect(self.text.undo)

        self.redoAction = QAction(QIcon("icons/redo.png"), "Redo, self")
        self.redoAction.setStatusTip("Redo las undo action")
        self.redoAction.setShortcut("Ctrl+Y")
        self.redoAction.setEnabled(True)
        self.redoAction.triggered.connect(self.text.redo)

        self.bulletAction = QAction(QIcon("Icons/bullet.png"), "Bullet list", self)
        self.bulletAction.setStatusTip("Insert bullet list")
        self.bulletAction.setShortcut("Ctrl*B")
        self.bulletAction.setEnabled(True)
        self.bulletAction.triggered.connect(self.bulletList)

        self.numberedAction = QAction(QIcon("icons/number.png"), "Numbered list", self)
        self.numberedAction.setStatusTip("Insert a numbered list")
        self.numberedAction.setShortcut("Ctrl+L")
        self.numberedAction.setEnabled(True)
        self.numberedAction.triggered.connect(self.numberedList)

        self.quitAction = QAction(QIcon("icons/btn_close.png"), "Quit", self)
        self.quitAction.setObjectName("Quit")
        self.quitAction.shortcut = "Ctrl+Q"
        self.quitAction.statusTip = "Exits the application"
        self.quitAction.triggered.connect(self.closeMail)

        self.deleteAction = QAction(QIcon("icons/delete.png"), "Erase", self)
        self.deleteAction.setStatusTip("Delete selected area")
        self.deleteAction.setShortcut("Ctrl+D")
        self.deleteAction.setEnabled(True)
        self.deleteAction.triggered.connect(self.removeText)

        self.findAction = QAction(QIcon("icons/find.png"), "Find and Replaced", self)
        self.findAction.setStatusTip("Find and Replace")
        self.findAction.setShortcut("Ctrl+F")
        self.findAction.setEnabled(True)
        self.findAction.triggered.connect(Find(self).show)

        self.imageAction = QAction(QIcon("icons/image.png"), "Insert image", self)
        self.imageAction.setStatusTip("Insert and image")
        self.imageAction.setShortcut("Ctrl+Shift+I")
        self.imageAction.triggered.connect(self.insertImage)

        self.wordCountAction = QAction(QIcon("icons/count.png"), "Words/Characters count", self)
        self.wordCountAction.setStatusTip("Word/Characteer count")
        self.wordCountAction.setShortcut("Ctrl+W")
        self.wordCountAction.triggered.connect(self.wordCount)

        self.tableAction = QAction(QIcon("icons/table.png"), "Insert Table", self)
        self.tableAction.setStatusTip("Insert Table")
        self.tableAction.setShortcut("Ctrl+I")
        self.tableAction.triggered.connect(Table(self).show)

        listAction = QAction("Insert List", self)
        listAction.setStatusTip("Insert a horse list")
        listAction.setShortcut("Ctrl + L")
        listAction.triggered.connect(self.insertList)

        self.dateTimeAction = QAction(QIcon("icons/calender.png"), "Date and Time", self)
        self.dateTimeAction.setStatusTip("Insert Date and Time")
        self.dateTimeAction.setShortcut("Ctrl+D")
        self.dateTimeAction.triggered.connect(DateTime(self).show)

        self.documentBar = self.addToolBar('Documents')
        self.documentBar.setObjectName("Documents")
        self.documentBar.setVisible(True)
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
        self.documentBar.addAction(self.wordCountAction)
        self.documentBar.addAction(self.tableAction)
        self.documentBar.addAction(self.dateTimeAction)
        self.documentBar.addSeparator()
        self.documentBar.addAction(self.attachmentAction)
        self.documentBar.setFixedHeight(30)
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
        self.formatBar.setFixedHeight(30)
        self.addToolBarBreak()

        """FromToolBar"""
        sendMailAction = QAction(QIcon(":/Icons8/email/sendcolormail.png"), "Sen Mail", self)
        sendMailAction.setObjectName("sendMAil")
        sendMailAction.setShortcut("Ctrl+S")
        sendMailAction.setStatusTip("Send eMail")
        sendMailAction.triggered.connect(self.sendMail)

        lblFrom = QLabel("From:...")
        lblFrom.setFixedWidth(80)

        self.fromBar = self.addToolBar("From")
        self.fromBar.addAction(sendMailAction)
        self.fromBar.addWidget(lblFrom)
        self.fromBar.addWidget(self.comboFrom)
        self.fromBar.addWidget(self.lineFrom)
        self.fromBar.setFixedHeight(30)
        self.addToolBarBreak()

        """ ToBar"""
        nullFromAction = QAction(QIcon(":Icons8/test.png"), "From", self)
        nullCcAction = QAction(QIcon(":Icons8/test.png"), "Cc", self)

        lblCc = QLabel("Cc:...")
        lblCc.setFixedWidth(80)
        lblSubject = QLabel("Subject:")
        lblSubject.setFixedWidth(80)
        lblAttachment = QLabel("Attached")
        lblAttachment.setFixedWidth(80)

        lblTo = QLabel("To:...")
        lblTo.setFixedWidth(80)


        self.toToolBar = self.addToolBar("ToBar")

        self.toToolBar.addAction(nullFromAction)
        self.toToolBar.addWidget(lblTo)
        self.toToolBar.addWidget(self.comboTo)
        self.toToolBar.addWidget(self.lineTo)
        self.toToolBar.setFixedHeight(30)
        self.addToolBarBreak()

        self.ccToolBar = self.addToolBar("Cc:")
        self.ccToolBar.addAction(nullCcAction)
        self.ccToolBar.addWidget(lblCc)
        self.ccToolBar.addWidget(self.comboCc)
        self.ccToolBar.addWidget(self.lineCc)
        self.ccToolBar.setFixedHeight(30)
        self.addToolBarBreak()

        self.subjectToolBar = self.addToolBar("Subject")
        self.subjectToolBar.addAction(nullCcAction)
        self.subjectToolBar.addWidget(lblSubject)
        self.subjectToolBar.addWidget(self.lineSubject)
        self.subjectToolBar.setFixedHeight(30)
        self.addToolBarBreak()

        self.attachedToolBar = self.addToolBar("Attached")
        self.attachedToolBar.setVisible(False)
        self.attachedToolBar.addAction(nullCcAction)
        self.attachedToolBar.addWidget(lblAttachment)
        self.attachedToolBar.addWidget(self.lineAttached)
        self.attachedToolBar.setFixedHeight(30)
        self.addToolBarBreak()

    @pyqtSlot()
    def newMail(self):
        try:
            self.parent.sendEMail()


        except Exception as err:
            pass

    def resetMail(self):
        try:

            self.lineTo.clear()
            self.lineCc.clear()
            self.lineSubject.clear()
            self.lineAttached.clear()
            self.text.clear()
            self.filename = None
            self.sentDateAndTime = None
            self.comboTo.setCurrentIndex(-1)
            self.comboCc.setCurrentIndex(-1)
            self.changesSaved = True
        except Exception as err:
            print("SendMail: newMail")

    def deleteMail(self):
        try:
            res = QFileDialog.getOpenFileName(self, caption="Open EMail Draft",
                                              directory=self.eMailFolder, filter="*.pad")[0]
            if QMessageBox.warning(self, "Delete File", "Confirm deleting file '{}'".format(os.path.basename(res)),
                                QMessageBox.Ok | QMessageBox.No) == QMessageBox.Ok :
                os.remove(res)
        except Exception as err:
            print("SendMail: deleteMail", err.args)

    def closeMail(self):
        if not self.changesSaved:
            ans = QMessageBox.question(self, "Save Changes", "The mail message has been modified. "
                                                             "Do you want to save your changes?",
                                       QMessageBox.Yes|QMessageBox.No)
            if ans == QMessageBox.Yes:
                self.saveMail()
        self.close()

    def setSettings(self):
        try:
            ans = MailSettings()
            ans.show()
            ans.exec()

        except Exception as err:
            print("SendMail: setSettings", err.args )

    """ Methods related to fromBar"""

    @pyqtSlot()
    def sendMail(self):
        try:
            if not self.lineTo.text() or not self.lineSubject.text():
                if not self.lineTo.text():
                    msg = "You need know where to send this email. Enter at least one name "
                    self.comboTo.setFocus()
                if not self.lineSubject.text():
                    msg = "You must enter the mail's subject"
                    self.lineSubject.setFocus()
                res = QMessageBox.critical(self, "Email Format Error", msg, QMessageBox.Ok)
                return
            addressReg = r"\((.*?)\)"
            toAddress = re.findall(addressReg, self.lineTo.text())
            ccAddress = re.findall(addressReg, self.lineCc.text())
            attachments = [ v for v in self.attachedFiles.values()]
            with yagmail.SMTP(user= self.address[0], password=self.address[1]) as yag:
                yag.send(to=toAddress, cc=ccAddress, subject=self.lineSubject.text(),
                          contents=self.text.toPlainText(), attachments=attachments)
            self.sentDateAndTime = QDateTime.currentDateTime().toString("dddd MMMM dd yyyy hh:mm:ss.zzz A")
            if QMessageBox.question(self, "Saving", "Do you want to save this mail?",
                                    QMessageBox.Yes| QMessageBox.No) == QMessageBox.Yes:
                self.filename = self.eMailFolder + "/send/" + self.lineTo.text()[: self.lineTo.text().find("(") - 1] + \
                                " - " + self.lineSubject.text() + " - " + str(
                    QDateTime.currentSecsSinceEpoch()) + ".pad"
                self.saveMail()
            self.close()

        except SMTPAuthenticationError as err:

            msg = """{} \n You have the following options: \n
            - Change the gmail account with proper validation.\n
            - Turn the less secures app option on your GMail account. \n
            - Or Use the Aauth2 GMail security framework with you application """.format(
                err.smtp_error[6:41].decode('utf-8'))
            QMessageBox.critical(self, "Connection Error", msg,QMessageBox.Ok)
            if QMessageBox.question(self, "Saving", "Dou you want to save this mail?",
                                    QMessageBox.Yes| QMessageBox.No) == QMessageBox.Yes:
                self.saveMail()
            self.close()
        except Exception as err:
            print("SendMail: sendMail")

    """Method related to toBar"""

    def getContacts(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL sendmail_getcontacts()")
            if qry.lastError().type() != 0:
                raise DataError("SendMail: getContacts", qry.lastError().text())
            return qry
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def getToAddress(self):
        if not self.checkInUseAddress(self.comboTo.getHiddenData(2), self.sender()):
            return
        self.lineTo.blockSignals(True)
        if not self.lineTo.text():
            self.lineTo.setText(self.comboTo.currentText() + ' (' + self.comboTo.getHiddenData(2) + ')')
            self.lineTo.blockSignals(False)
            return
        self.lineTo.setText(self.lineTo.text() + '; ' +
                            self.comboTo.currentText() + ' (' + self.comboTo.getHiddenData(2) + ')' )
        self.lineTo.blockSignals(False)

    """Methods related to the Document Bar"""

    @pyqtSlot()
    def getCcAddress(self):
        if not self.checkInUseAddress(self.comboCc.getHiddenData(2), self.sender()):
            return
        self.lineCc.blockSignals(True)
        if not self.lineCc.text():
            self.lineCc.setText(self.comboCc.currentText() + ' ('+ self.comboCc.getHiddenData(2) + ')')
            self.lineCc.blockSignals(False)
            return
        self.lineCc.setText(self.lineCc.text() + '; ' + self.comboCc.currentText() +
                            ' ('+ self.comboCc.getHiddenData(2) + ')')
        self.lineCc.blockSignals(False)

    def checkInUseAddress(self, address, sender):
        if address in self.lineTo.text() + ', ' + self.lineCc.text():
            sender.setCurrentIndex(-1)
            return False
        return True

    @pyqtSlot()
    def attachFile(self):
        try:
            self.lineAttached.blockSignals(True)
            capt = "EMail, load files to attach"

            res = QFileDialog.getOpenFileName(self, caption=capt, directory="C:/users/erick/documents")
            if not res[0] or os.path.basename(res[0]) in self.attachedFiles:
                self.lineAttached.blockSignals(False)
                return
            self.attachedToolBar.setVisible(True)
            self.attachedFiles[os.path.basename(res[0])] = res[0]
            if self.lineAttached.text():
                self.lineAttached.setText(self.lineAttached.text() + '; ' + os.path.basename(res[0]))
                self.lineAttached.blockSignals(False)
                return
            self.lineAttached.setText(os.path.basename(res[0]))
            self.lineAttached.blockSignals(False)
        except Exception as err:
            print("SendNail; attachFile", err.args)
            
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
            self.numberedAction,
            self.attachmentAction]
        [obj.setEnabled(opt) for obj in documentObjects]
        self.formatBar.setVisible(opt)
        self.documentBar.setVisible(opt)

    @pyqtSlot()
    def cursorPosition(self):
        cursor = self.text.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber()
        self.statusBar.showMessage("Line: {} | Column: {}".format(line, col))

    @pyqtSlot()
    def preview(self):

        preview = QPrintPreviewDialog()
        preview.paintRequested.connect(lambda p: self.text.print_(p))
        preview.exec_()

    @pyqtSlot()
    def printMail(self):
        dialog = QPrintDialog()

        if dialog.exec_() == QDialog.Accepted:
            self.text.document().print_(dialog.printer())

    @pyqtSlot()
    def bulletList(self):
        cursor = self.text.textCursor()
        cursor.insertList(QTextListFormat.ListDisc)

    @pyqtSlot()
    def numberedList(self):
        cursor = self.text.textCursor()
        cursor.insertList(QTextListFormat.ListDecimal)

    @pyqtSlot()
    def removeText(self):
        cursor = self.text.textCursor()
        if cursor.hasSelection():
            try:
                cursor.removeSelectedText()
            except Exception as err:
                print(err)

    @pyqtSlot()
    def insertList(self):
        pass

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
    def wordCount(self):
        try:
            wc = WordCount(self)
            wc.getText()
            wc.show()
        except Exception as err:
            print(err)

    """Methods related to the formatBar"""

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

    @pyqtSlot()
    def searchDelete(self):
        obj = self.sender()
        pos = obj.cursorPosition()
        start = end = 0
        checkPos = 0
        while checkPos >= 0 and checkPos <= pos:
            checkPos = obj.text().find(";", checkPos)
            checkPos = checkPos + 1 if checkPos > -1 else checkPos
            start = checkPos if checkPos < pos and checkPos > 0 else start
            end = checkPos if checkPos >= pos else end

        obj.blockSignals(True)
        if start == 0 and end == 0:
            obj.end(False)
            obj.home(True)
        elif start == 0 and end > 0:
            obj.setCursorPosition(end)
            obj.home(True)
        elif start > 0  and end > 0:
            obj.setSelection(start, end - start)
        elif start > 0 and end == 0:
            obj.setCursorPosition(start)
            obj.end(True)
        obj.blockSignals(False)

    @pyqtSlot()
    def deleteEntry(self):
        entry = self.lineAttached.selectedText().lstrip()
        if entry.endswith(";"):
            entry = entry[:-1]
        self.attachedFiles.pop(entry)

    @pyqtSlot()
    def toggleDocumentBar(self):
        self.documentBar.setVisible(not self.documentBar.isVisible())

    @pyqtSlot()
    def openMail(self):
        """Needs to set up the methods to set the auxiliary windows for this agreement"""
        try:
            self.newMail()
            res = QFileDialog.getOpenFileName(self, caption="Open EMail Draft",
                                              directory=self.eMailFolder, filter="*.pad")
            filename = res[0]
            magicStruct = Struct("<4s")
            lenStruct = Struct("<H")
            with open(filename, "br") as fh:
                magic = fh.read(magicStruct.size)
                if magic != self.MAGIC:
                    pop = QMessageBox(self)
                    pop.setIcon(QMessageBox.Critical)
                    pop.setText("Wrong File Type")
                    pop.setInformativeText("The selected file is not a'Polo Agreement Management' file (*.pam)")
                    pop.setStandardButtons(QMessageBox.Ok)
                    pop.show()
                    return
                self.filename = filename
                mailData = {}
                while True:
                    lenData = fh.read(lenStruct.size)
                    if not lenData:
                            break
                    lenghtData = lenStruct.unpack(lenData)[0]
                    data = fh.read(lenghtData)
                    dataStruct = "<{}s".format(lenghtData)
                    readData = struct.unpack(dataStruct, data)[0].decode("UTF-8")
                    mailData[readData[: readData.find(":")-1]] = readData[readData.find(":")+1:]
                self.lineFrom.setText(mailData["From"])
                self.lineTo.setText(mailData["To"])
                self.lineCc.setText(mailData["Cc"])
                self.lineSubject.setText(mailData["Subject"])
                self.lineAttached.setText(mailData["Attachments"])
                self.text.setHtml(mailData["Text"])
                self.sentDateAndTime = mailData["Sent"]
                print(mailData)
        except Exception as err:
            print("SendMail: openMail", err.args)

    @pyqtSlot()
    def saveMail(self):
        try:
            sentTime = self.sentDateAndTime if self.sentDateAndTime else ''
            senderName = self.sender().objectName()
            if not self.filename:
                baseFile = self.eMailFolder + "/" + "send/" if senderName == "sendMail" else \
                    self.eMailFolder + "/" + "draft/"
                self.filename = baseFile +  self.lineTo.text()[: self.lineTo.text().find("(")-1] +\
                    " - " + self.lineSubject.text() + " - " + str(QDateTime.currentSecsSinceEpoch())+ ".pad"
            if not self.filename.endswith(".pad"):
                self.filename += ".pad"
            magicStruct = Struct("<4s")

            binFrom = ("From : " + self.lineFrom.text()).encode("UTF-8")
            fromStruct = Struct("<H{}s".format(len(binFrom)))
            toBin = ("To : " + self.lineTo.text()).encode("UTF-8")
            toStruct = Struct("<H{}s".format(len(toBin)))
            ccBin = ("Cc : " + self.lineCc.text()).encode("UTF-8")
            ccStruct = Struct("<H{}s".format(len(ccBin)))
            subjectBin = ("Subject : " + self.lineSubject.text()).encode("UTF-8")
            subjectStruct = Struct("<H{}s".format(len(subjectBin)))
            attachmentBin = ("Attachments : " + self.lineAttached.text()).encode("UTF-8")
            attachmentStruct = Struct("<H{}s".format(len(attachmentBin)))
            binText = ("Text : " + self.text.toHtml()).encode('UTF-8')
            xmlStruct = Struct("<H{}s".format(len(binText)))
            binSentTime = ("Sent : " + sentTime).encode("UTF-8")
            sentTimeStruct = Struct("<H{}s".format(len(binSentTime)))
            with open(self.filename, "bw") as fb:
                fb.write(magicStruct.pack(self.MAGIC))
                fb.write(fromStruct.pack(len(binFrom),binFrom))
                fb.write(toStruct.pack(len(toBin), toBin))
                fb.write(ccStruct.pack(len(ccBin), ccBin))
                fb.write(subjectStruct.pack(len(subjectBin),subjectBin))
                fb.write(attachmentStruct.pack(len(attachmentBin), attachmentBin))
                fb.write(xmlStruct.pack(len(binText),binText))
                fb.write(sentTimeStruct.pack(len(binSentTime), binSentTime))

        except FileNotFoundError as err:
            QMessageBox.warning(self, "File not found", "Check the email folder in the mail settings. It's probably wrong",
                                QMessageBox.Ok)
            self.close()
        except ValueError as err:
            print("SendMail: saveMail", err.args)

