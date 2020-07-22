


import sys, os
from PyQt5.QtPrintSupport import QPrintPreviewDialog, QPrintDialog
from PyQt5.QtGui import (QTextDocument, QTextCursor, QTextTableFormat, QTextLength, QIcon,
                        QTextTableCellFormat, QTextCharFormat, QFont, QTextFrameFormat)
from PyQt5.QtWidgets import (QToolButton,QHBoxLayout, QVBoxLayout, QDialog, QTextEdit)
from PyQt5.QtCore import (Qt, QVariant, pyqtSlot, QDate)
from PyQt5.QtSql import QSqlQueryModel, QSqlDatabase, QSqlQuery








class ReportPrint():
    def __init__(self, table, title, centerColumns, colWidths):
        self.tableView = table
        self.title = title
        self.centerColumns = centerColumns
        self.colWidths = colWidths

    def handlePrint(self):
        dialog = QPrintDialog()
        if dialog.exec_():
            self.handlePaintRequest(dialog.printer())

    def handlePreview(self):
        dialog = QPrintPreviewDialog()
        dialog.paintRequested.connect(self.handlePaintRequest)
        dialog.exec_()


    def handlePaintRequest(self, printer):
        visibleColumns = [x for x in range(self.tableView.model().columnCount()) if not self.tableView.isColumnHidden(x)]
        document = QTextDocument()
        cursor = QTextCursor(document)
        cursor.select(QTextCursor.LineUnderCursor)
        docCharFormat = QTextCharFormat()
        docCharFormat.setFont(QFont('Helvetica', 30))
        docCharFormat.setFontUnderline(True)
        cursor.setBlockCharFormat(docCharFormat)
        docBlockFormat = cursor.blockFormat()
        docBlockFormat.setAlignment(Qt.AlignHCenter | Qt.AlignBottom)
        cursor.setBlockCharFormat(docCharFormat)
        cursor.setBlockFormat(docBlockFormat)
        cursor.insertText(self.title + "\r\n")
        blankCharFormat = QTextCharFormat()
        blankCharFormat.setFontUnderline(False)
        cursor.insertText("     ", blankCharFormat)

        model = self.tableView.model()

        table = cursor.insertTable(model.rowCount(), len(visibleColumns))
        charFormat = QTextCharFormat()
        charFormat.setFont(QFont('Helvetica', 8))
        fmt = QTextTableFormat()
        idWidth = QTextLength(QTextLength.FixedLength,45)
        nameWidth = QTextLength()
        dobWidth = QTextLength(QTextLength.FixedLength,100)
        ageWidth = QTextLength(QTextLength.FixedLength,45)
        sexWidth = QTextLength(QTextLength.FixedLength,45)
        coatWidth = QTextLength(QTextLength.FixedLength,120)
        brokeWidth = QTextLength(QTextLength.FixedLength, 60)
        activeWidth = QTextLength(QTextLength.FixedLength, 60)

        colWidths = [idWidth, nameWidth, dobWidth, ageWidth, sexWidth, coatWidth, brokeWidth, activeWidth]
        fmt.setColumnWidthConstraints(colWidths)
        fmt.setCellPadding(0)
        fmt.setCellSpacing(0)
        fmt.setAlignment(Qt.AlignCenter)
        table.setFormat(fmt)
        cellFormat = QTextTableCellFormat()
        #table.setFrameFormat(fmt)
        tableCol = 0
        for x in range(model.columnCount()):
            print(x, tableCol)
            if x in visibleColumns:
                tableCursor = table.cellAt(0, tableCol).firstCursorPosition()
                blockFormat = tableCursor.blockFormat()
                vAlign = blockFormat.alignment() & Qt.AlignVertical_Mask
                align = Qt.AlignHCenter | vAlign
                blockFormat.setAlignment(align)
                tableCursor.setBlockFormat(blockFormat)
                tableCursor.insertText(model.headerData(x, Qt.Horizontal), charFormat)
                tableCursor.movePosition(QTextCursor.NextCell)
                tableCol += 1
        qry = model.query()
        qry.first()
        row = 1
        while qry.next():
            col = 0
            rec = qry.record()
            for x in range(rec.count()):
                if x not in visibleColumns:
                    continue
                tableCursor = table.cellAt(row, col).firstCursorPosition()
                blockFormat = tableCursor.blockFormat()
                vAlign = blockFormat.alignment() & Qt.AlignVertical_Mask

                if x in self.centerColumns:
                    align = Qt.AlignHCenter
                else:
                    align = Qt.AlignLeft
                blockFormat.setAlignment(align)
                tableCursor.setBlockFormat(blockFormat)
                tableCursor.insertBlock(blockFormat)
                if type(rec.value(x)) is int:
                    tableCursor.insertText(str(rec.value(x)), charFormat)
                elif type(rec.value(x)) is QDate:
                    tableCursor.insertText(rec.value(x).toString('MM-dd-yyyy'), charFormat)
                else:
                    tableCursor.insertText(rec.value(x),charFormat)
                tableCursor.movePosition(QTextCursor.NextCell)
                col +=1
            row += 1
        document.print(printer)

class InvoicePrint(QDialog):
    def __init__(self, model=None, provider=None, customer=None):
        super().__init__()
        self.model = model
        self.provider = provider
        self.customer = customer
        self.setMinimumSize(1000, 800)
        self.setUi()
        self.setInvoice()

    def setUi(self):
        txt = QTextEdit()
        self.doc = txt.document()

        toolPrint = QToolButton()
        toolPrint.setIcon(QIcon(":/Icons8/print/sendtoprinter.png"))
        toolPrint.clicked.connect(self.handlePrint)

        toolPreview = QToolButton()
        toolPreview.setIcon(QIcon(":/Icons8/print/printtopdf.png"))
        toolPreview.clicked.connect(self.handlePreview)

        toolClose = QToolButton()
        toolClose.setIcon(QIcon(":/Icons8/exit/closesign.png"))
        toolClose.clicked.connect(self.close)

        toolLayout = QHBoxLayout()
        toolLayout.addWidget(toolPrint)
        toolLayout.addWidget(toolPreview)
        toolLayout.addWidget(toolClose)

        layout = QVBoxLayout()
        layout.addWidget(txt)
        layout.addLayout(toolLayout)

        self.setLayout(layout)

    def handlePaintRequest(self, printer):
        try:
            self.doc.print(printer)

        except Exception as err:
            print(type(err), err.args)

    def setInvoice(self):
        try:
            cursor = QTextCursor(self.doc)
            cursor.select(QTextCursor.LineUnderCursor)
            docCharFormat = QTextCharFormat()
            docCharFormat.setFont(QFont('Sans Serif', 30))
            docCharFormat.setFontUnderline(True)
            cursor.setBlockCharFormat(docCharFormat)
            docBlockFormat = cursor.blockFormat()
            docBlockFormat.setAlignment(Qt.AlignRight | Qt.AlignTop)
            cursor.setBlockCharFormat(docCharFormat)
            cursor.setBlockFormat(docBlockFormat)
            cursor.insertText("INVOICE")
            cursor.setPosition(self.doc.rootFrame().lastPosition())
            frmFormat = QTextFrameFormat()
            frmFormat.setWidth(500)
            frmFormat.setHeight(300)
            frmFormat.setBackground(Qt.darkGray)
            frmFormat.setForeground(Qt.yellow)
            frmFormat.setPosition(QTextFrameFormat.FloatLeft)

            frmCharFormat = QTextCharFormat()
            frmCharFormat.setFont(QFont("Helvetica", 15))
            frmCharFormat.setForeground(Qt.yellow)
            frmBlockFormat = cursor.blockFormat()
            frmBlockFormat.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            frame = cursor.insertFrame(frmFormat)
            cursor.setPosition(frame.lastPosition())
            cursor.setBlockCharFormat(frmCharFormat)
            cursor.setBlockFormat(frmBlockFormat)


            cursor.insertText("Bill To:\r\nEnrique Carlos Boelcke\r\nAlvarez de Toledo 3958\r\nSaladillo 7260\r\nBuenos Aires")


           #blankCharFormat = QTextCharFormat()
            #blankCharFormat.setFontUnderline(False)
            #cursor.insertText("     ", blankCharFormat)

        except Exception as err:
            print(type(err), err.args)


    def handlePrint(self):
        dialog = QPrintDialog()
        if dialog.exec_():
            self.handlePaintRequest(dialog.printer())

    def handlePreview(self):
        dialog = QPrintPreviewDialog()
        dialog.paintRequested.connect(self.handlePaintRequest)
        dialog.exec_()

