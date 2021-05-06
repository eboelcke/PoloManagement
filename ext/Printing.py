


import sys, os
from PyQt5.QtPrintSupport import QPrintPreviewDialog, QPrintDialog, QPrinter, QPrintPreviewWidget
from PyQt5.QtGui import (QTextDocument, QTextCursor, QTextTableFormat, QTextLength, QIcon, QPixmap, QImage,
                        QTextTableCellFormat, QTextCharFormat, QTextBlockFormat, QTextImageFormat, QFont,
                        QTextFormat, QTextFrameFormat, QBrush)
from PyQt5.QtWidgets import (QToolButton,QHBoxLayout, QVBoxLayout, QDialog, QTextEdit, QComboBox)
from PyQt5.QtCore import (Qt, QVariant, pyqtSlot, QDate, QSettings)
from PyQt5.QtSql import QSqlQueryModel, QSqlDatabase, QSqlQuery
from ext.APM import DataError, ACCOUNT_ALL, ACCOUNT_PAYMENT, ACCOUNT_INVOICE, PAYMENT_TYPE_CASH
import poloresurce

class ReportPrint():
    def __init__(self, table, title, totalRecord=None, parent=None):
        self.tableView = table
        self.title = title
        self.name = None
        self.address = None
        self.printer = None
        self.parent = parent
        self.totalRecord = totalRecord
        self.getSender()

    def getSender(self):
        sett = QSettings("ext/config.ini", QSettings.IniFormat)
        self.name = sett.value("owner/FarmName")
        self.address = sett.value("owner/FarmAddress")

    def handlePrint(self):
        dialog = QPrintDialog()
        if dialog.exec_():
            self.handlePaintRequest(dialog.printer())

    def handlePdf(self):
        title = self.title + '-' + QDate.currentDate().toString("yyyy-MM-dd")
        document = self.handlePaintRequest()
        self.parent.savePdf(document, "Reports",title )

    def handlePreview(self):
        dialog = QPrintPreviewDialog()
        dialog.setMinimumSize(550, 950)
        dialog.printer().setPageMargins(10.0, 8.0, 15.0, 10.0, QPrinter.Millimeter)
        ppWidget = dialog.findChild(QPrintPreviewWidget)
        ppWidget.setZoomFactor(0.7)
        dialog.paintRequested.connect(lambda: self.handlePaintRequest(dialog.printer()))
        dialog.exec_()


    def handlePaintRequest(self, printer=None):
        logo = QImage(":/Icons8/logos/polo-right.png")
        smallLogo = logo.scaledToHeight(100)
        visibleColumns = [x for x in range(self.tableView.model().columnCount()) if not self.tableView.isColumnHidden(x)]
        document = QTextDocument()
        page = 1
        cursor = QTextCursor(document)
        mainFrame = cursor.currentFrame()
        mainFramefmt = QTextFrameFormat()
        headFormat = QTextBlockFormat()
        headFormat.setAlignment(Qt.AlignLeft)
        headCharfmt = QTextCharFormat()
        headCharfmt.setFont(QFont("Helvetica", 8))
        cursor.insertBlock(headFormat, headCharfmt)
        cursor.insertImage(smallLogo)
        cursor.insertBlock(headFormat, headCharfmt)
        cursor.insertText(self.name)
        for line in self.address.split("\n"):
            cursor.insertBlock(headFormat, headCharfmt)
            cursor.insertText(line)

        titleFormat = QTextBlockFormat()
        titleFormat.setAlignment(Qt.AlignHCenter)
        titleCharfmt = QTextCharFormat()
        titleCharfmt.setFont(QFont("Helvetica", 15))
        cursor.insertBlock(titleFormat, titleCharfmt)
        cursor.insertText(self.title)

        cursor.insertBlock(titleFormat, headCharfmt)
        cursor.insertText(QDate.currentDate().toString("MM-dd-yyyy") + "\r\n")

        blankCharFormat = QTextCharFormat()
        blankCharFormat.setFontUnderline(False)
        cursor.insertText("     ", blankCharFormat)

        model = self.tableView.model()

        cellBodyFormat = QTextBlockFormat()

        cellFormatLeft = QTextBlockFormat()
        cellFormatLeft.setAlignment(Qt.AlignLeft)

        cellHeaderCharFormat = QTextCharFormat()
        cellHeaderCharFormat.setFont(QFont("Times", 8))

        cellBlockCharFormat = QTextCharFormat()
        cellBlockCharFormat.setFont(QFont("Times", 9))

        totalCellCharFormat = QTextCharFormat()
        totalCellCharFormat.setFont(QFont("Times", 9))
        totalCellCharFormat.setBackground(Qt.cyan)

        redCellCharFormat = QTextCharFormat()
        redCellCharFormat.setFont(QFont("Times, 5"))
        redCellCharFormat.setForeground(Qt.red)

        table = cursor.insertTable(model.rowCount() + 2, len(visibleColumns))
        charFormat = QTextCharFormat()
        charFormat.setFont(QFont('Helvetica', 8))

        colWidths = [QTextLength(QTextLength.FixedLength, self.tableView.columnWidth(x)) for x in visibleColumns]
        alignDict = {x: model.data(model.index(1, x), Qt.TextAlignmentRole).value()
                     for x in range(model.columnCount()) if x in visibleColumns}
        fmt = QTextTableFormat()
        fmt.setColumnWidthConstraints(colWidths)
        fmt.setCellPadding(0)
        fmt.setCellSpacing(0)
        fmt.setAlignment(Qt.AlignCenter)
        fmt.setBorderStyle(fmt.BorderStyle_None)
        table.setFormat(fmt)
        tableCol = 0
        for x in range(model.columnCount()):
            if x in visibleColumns:
                tableCursor = table.cellAt(0, tableCol).firstCursorPosition()
                if alignDict[x] == 1:
                    cellFormatLeft.setAlignment(Qt.AlignLeft)
                elif alignDict[x] == 2:
                    cellFormatLeft.setAlignment(Qt.AlignRight)
                elif alignDict[x] == 4:
                    cellFormatLeft.setAlignment(Qt.AlignCenter)
                tableCursor.insertBlock(cellFormatLeft, cellHeaderCharFormat)
                tableCursor.insertText(model.headerData(x, Qt.Horizontal),)
                tableCursor.movePosition(QTextCursor.NextCell)
                tableCol += 1
        qry = self.tableView.model().query()
        row = 1
        qry.seek(-1)
        while qry.next():
            col = 0
            rec = qry.record()
            for x in range(rec.count()):
                if x not in visibleColumns:
                    continue
                tableCursor = table.cellAt(row, col).firstCursorPosition()
                if alignDict[x] == 1:
                    cellBodyFormat.setAlignment(Qt.AlignLeft)
                elif alignDict[x] == 4:
                    cellBodyFormat.setAlignment(Qt.AlignCenter)
                elif alignDict[x] == 2:
                    cellBodyFormat.setAlignment(Qt.AlignRight)
                tableCursor.insertBlock(cellBodyFormat, cellBlockCharFormat)
                if type(rec.value(x)) is int:
                    tableCursor.insertText(str(rec.value(x)))
                elif type(rec.value(x)) is QDate:
                    tableCursor.insertText(rec.value(x).toString('MM-dd-yyyy'))
                elif type(rec.value(x)) is float:
                    tableCursor.insertText("{:.2f}".format(rec.value(x)))

                else:
                    tableCursor.insertText(rec.value(x))
                tableCursor.movePosition(QTextCursor.NextCell)
                col +=1
            row += 1

        if self.totalRecord :
            for col in range(table.columns()):
                tableCursor = tableCursor = table.cellAt(row, col).firstCursorPosition()

                if col in self.totalRecord.keys():
                    if alignDict[visibleColumns[col]] == 1:
                        cellBodyFormat.setAlignment(Qt.AlignLeft)
                    elif alignDict[visibleColumns[col]] == 2:
                        cellBodyFormat.setAlignment(Qt.AlignRight)
                    elif alignDict[visibleColumns[col]] == 4:
                        cellBodyFormat.setAlignment(Qt.AlignCenter)

                    tableCursor.insertBlock(cellBodyFormat, totalCellCharFormat)
                    if isinstance(self.totalRecord[col], str):
                        tableCursor.insertText("{}".format(self.totalRecord[col]))
                    elif isinstance(self.totalRecord[col], float):
                        tableCursor.insertText("{:,.2f}".format(self.totalRecord[col]))

                tableCursor.movePosition(QTextCursor.NextCell)


        cursor.setPosition(mainFrame.lastPosition())
        cursor.insertBlock(titleFormat, titleCharfmt)
        cursor.insertText("-" * 77)

        lastParaBodyFormat = QTextBlockFormat()
        lastParaBodyFormat.setPageBreakPolicy(QTextFormat.PageBreak_AlwaysAfter)
        if not printer:
            return document
        document.print(printer)

class InvoicePrint(QDialog):
    def __init__(self, db, record, table, documentType=ACCOUNT_INVOICE, parent=None):
        super().__init__()
        self.record = record
        self.tableView = table
        self.parent = parent
        self.db = db
        self.documentType = documentType
        self.getNamesAndAddresses(self.parent.supplierId)

    def getNamesAndAddresses(self, supplierId):
        try:
            sett = QSettings("ext/config.ini", QSettings.IniFormat)
            self.billTo = sett.value("owner/ownerName")
            self.billToAddress = sett.value("owner/Address")
            qry = QSqlQuery(self.db)
            qry.exec("call invoiceprint_getnamesandaddresses({})".format(supplierId))
            if qry.lastError().type() != 0:
                raise DataError("InvoicePrint: getNamesAndAddresses", qry.lastError().text())
            if qry.first():
                name = qry.value(0)
                self.name = name[name.index(",") +1 :] + " " + name[: name.index(",")]
                self.address = qry.value(1)
        except Exception as err:
            print("InvoicePrint: getNameAndAddresses", err.args)

    def handlePreview(self):
        dialog = QPrintPreviewDialog()
        dialog.setMinimumSize(550, 950)
        dialog.printer().setPageMargins(0.0, 0.0, 0.0, 0.0, QPrinter.Millimeter)
        ppWidget = dialog.findChild(QPrintPreviewWidget)
        ppWidget.setZoomFactor(0.7)
        dialog.paintRequested.connect(lambda: self.handlePaintRequest(dialog.printer()))
        dialog.exec_()

    def handlePdf(self):
        #title = self.title + '-' + QDate.currentDate().toString("yyyy-MM-dd")
        document = self.handlePaintRequest()
        if self.documentType == ACCOUNT_INVOICE:
            folder = "Invoices"
            title = "{} Invoice {} {}".format(self.parent.supplier, self.record.value(3),
                                              self.record.value(1).toString("yyyy-MM-dd"))
        else:
            folder = "Payments"
            title = "{} Payment {} {}".format(self.parent.supplier, self.record.value(2),
                                              self.record.value(1).toString("yyyy-MM-dd"))
        self.parent.savePdf(document, folder, title)

    def handlePaintRequest(self, printer=None):
        try:
            logo = QImage(":/Icons8/logos/polo-right.png")
            smallLogo = logo.scaledToHeight(100)
            visibleColumns = [x for x in range(self.tableView.model().columnCount()) if
                              not self.tableView.isColumnHidden(x)]
            document = QTextDocument()
            page = 1
            cursor = QTextCursor(document)
            mainFrame = cursor.currentFrame()
            mainFramefmt = QTextFrameFormat()

            headFormat = QTextBlockFormat()
            headFormat.setAlignment(Qt.AlignCenter)
            headFormat.setIndent(19)
            headLineFormat = QTextBlockFormat()
            headLineFormat.setIndent(5)
            headLineFormat.setAlignment(Qt.AlignRight)
            billToFormat = QTextBlockFormat()
            billToFormat.setAlignment(Qt.AlignLeft)
            cellFormat = QTextBlockFormat()

            headCharfmt = QTextCharFormat()
            headCharfmt.setFont(QFont("Helvetica", 12))
            headerCharfmt = QTextCharFormat()
            headerCharfmt.setFont(QFont("Times", 10))

            billToCharfmt = QTextCharFormat()
            billToCharfmt.setFont(QFont("Times", 10))
            cellCharfmt = QTextCharFormat()
            cellCharfmt.setFont(QFont("Times", 10))
            if self.documentType == ACCOUNT_INVOICE:
                cursor.insertBlock(headFormat, headCharfmt)
                cursor.insertImage(smallLogo)
                cursor.insertBlock(headFormat, headCharfmt)
                cursor.insertText(self.name)
                for line in self.address.split("\n"):
                    cursor.insertBlock(headFormat, headCharfmt)
                    cursor.insertText("{:<}".format(line))

                cursor.insertBlock(headFormat, headerCharfmt)
                cursor.insertText("     ")
                cursor.insertBlock(headLineFormat, headCharfmt)
                cursor.insertText("Date: {} Form Type: {} Number: {}".format(
                    self.record.value(1).toString("yyyy-MM-dd"),
                    self.record.value(2),
                    self.record.value(3)))
                cursor.insertBlock(billToFormat, billToCharfmt)
                cursor.insertText("Bill to: {}".format(self.billTo))
                for line in self.billToAddress.split("\n"):
                    cursor.insertBlock(billToFormat, billToCharfmt)
                    cursor.insertText(line)
                cursor.insertBlock(headLineFormat, headerCharfmt)
                cursor.insertText(" ")
                model = self.tableView.model()
                bottomData = [("{:<20}".format("Subtotal {}:".format(self.record.value(4))),
                           "{:,.2f}".format(self.record.value(8))),
                          ("{:<20}".format("IVA {:.2f}%:".format(self.record.value(13))),
                           "{:,.2f}".format(self.record.value(9))),
                          (("{:<20}".format("Grand Total {}:".format(self.record.value(4))),
                           "{:,.2f}".format(self.record.value(10))),)] if self.record.value(15) != 0 else \
                [("{:<20}".format("Total {}:".format(self.record.value(4))),
                  "{:,.2f}".format(self.record.value(8)))]

                table = cursor.insertTable(13, len(visibleColumns))
                colWidths = [QTextLength(QTextLength.FixedLength, self.tableView.columnWidth(x)) for x in visibleColumns]
                alignDict = {x: model.data(model.index(1, x), Qt.TextAlignmentRole).value()
                         for x in range(model.columnCount()) if x in visibleColumns}
                fmt = QTextTableFormat()
                #fmt.setColumnWidthConstraints(colWidths)
                fmt.setCellPadding(0)
                fmt.setCellSpacing(0)
                fmt.setAlignment(Qt.AlignCenter)
                fmt.setBorderStyle(fmt.BorderStyle_None)
                fmt.setWidth(QTextLength(QTextLength.PercentageLength,90))
                table.setFormat(fmt)
                tableCol = 0
                for x in range(model.columnCount()):
                    if x in visibleColumns:
                        tableCursor = table.cellAt(0, tableCol).firstCursorPosition()
                        if alignDict[x] ==1:
                            cellFormat.setAlignment(Qt.AlignLeft)
                        elif alignDict[x] == 2:
                            cellFormat.setAlignment(Qt.AlignRight)
                        elif alignDict[x] == 4:
                            cellFormat.setAlignment(Qt.AlignCenter)
                        cellCharfmt.setFontWeight(QFont.Bold)
                        tableCursor.insertBlock(cellFormat, cellCharfmt)
                        tableCursor.insertText(model.headerData(x, Qt.Horizontal) )
                        tableCursor.movePosition(QTextCursor.NextCell)
                        tableCol += 1
                qry = model.query()
                row = 1
                qry.seek(-1)
                cellCharfmt.setFontWeight(QFont.Normal)
                while qry.next():
                    col = 0
                    rec = qry.record()
                    for x in range(rec.count()):
                        if x not in visibleColumns:
                            continue
                        tableCursor = table.cellAt(row, col).firstCursorPosition()
                        if alignDict[x] == 1:
                            cellFormat.setAlignment(Qt.AlignLeft)
                        elif alignDict[x] == 4:
                            cellFormat.setAlignment(Qt.AlignCenter)
                        elif alignDict[x] == 2:
                            cellFormat.setAlignment(Qt.AlignRight)
                        tableCursor.insertBlock(cellFormat, cellCharfmt)
                        if type(rec.value(x)) is int:
                            tableCursor.insertText(str(rec.value(x)))
                        elif type(rec.value(x)) is QDate:
                            tableCursor.insertText(rec.value(x).toString('MM-dd-yyyy'))
                        elif type(rec.value(x)) is float:
                            tableCursor.insertText("{:,.2f}".format(rec.value(x)))
                        else:
                            tableCursor.insertText(rec.value(x))
                        tableCursor.movePosition(QTextCursor.NextCell)
                        col += 1
                    row += 1
                cellFormat.setAlignment(Qt.AlignRight)
                cellCharfmt.setFontWeight(QFont.Bold)
                row = 11
                while row <= 10 + len(bottomData):
                    for col in range(table.columns()):
                        tableCursor = table.cellAt(row,col).firstCursorPosition()
                        tableCursor.insertBlock(cellFormat, cellCharfmt)
                        tableCursor.insertText(bottomData[row - 11][col])
                        tableCursor.movePosition(QTextCursor.NextCell)
                    row += 1
            if self.documentType == ACCOUNT_PAYMENT:
                cursor.insertBlock(headFormat, headCharfmt)
                cursor.insertImage(smallLogo)
                cursor.insertBlock(headFormat, headCharfmt)
                cursor.insertText(self.billTo)
                for line in self.billToAddress.split("\n"):
                    cursor.insertBlock(headFormat, headCharfmt)
                    cursor.insertText("{:<}".format(line))

                cursor.insertBlock(headFormat, headerCharfmt)
                cursor.insertText("     ")
                cursor.insertBlock(headLineFormat, headCharfmt)
                cursor.insertText("Date: {} Payment Type: {} Number: {}".format(
                    self.record.value(1).toString("yyyy-MM-dd"),
                    self.record.value(3),
                    self.record.value(2)))
                if self.record.value(7) != PAYMENT_TYPE_CASH:
                    cursor.insertBlock(headLineFormat, headCharfmt)
                    cursor.insertText("Bank: {} Transaction Number: {}".format(self.record.value(4), self.record.value(5)))
                cursor.insertBlock(billToFormat, billToCharfmt)
                cursor.insertText("Payment to: {}".format(self.name))
                for line in self.address.split("\n"):
                    cursor.insertBlock(billToFormat, billToCharfmt)
                    cursor.insertText(line)
                cursor.insertBlock(headLineFormat, headerCharfmt)
                cursor.insertText(" ")
                model = self.tableView.model()
                currency = "U$A" if self.record.value(9) == 0 else "AR$"
                bottomData = [("{:<20}".format("Total Amount {}".format(currency)),
                               "{:,.2f}".format(self.record.value(6)))]
                if self.record.value(10):
                    bottomData.append(("{:<20}".format("Paid in local currency (AR$)"),
                                       "{:,.2f}".format(self.record.value(10))))
                table = cursor.insertTable(8, len(visibleColumns))
                colWidths = [QTextLength(QTextLength.FixedLength, self.tableView.columnWidth(x)) for x in
                             visibleColumns]
                alignDict = {x: model.data(model.index(0, x), Qt.TextAlignmentRole).value()
                             for x in range(model.columnCount()) if x in visibleColumns}
                fmt = QTextTableFormat()
                #fmt.setColumnWidthConstraints(colWidths)
                fmt.setCellPadding(0)
                fmt.setCellSpacing(0)
                fmt.setAlignment(Qt.AlignCenter)
                fmt.setBorderStyle(fmt.BorderStyle_None)
                fmt.setWidth(QTextLength(QTextLength.PercentageLength, 90))
                table.setFormat(fmt)
                tableCol = 0
                for x in range(model.columnCount()):
                    if x in visibleColumns:
                        tableCursor = table.cellAt(0, tableCol).firstCursorPosition()
                        if alignDict[x] == 1:
                            cellFormat.setAlignment(Qt.AlignLeft)
                        elif alignDict[x] == 2:
                            cellFormat.setAlignment(Qt.AlignRight)
                        elif alignDict[x] == 4:
                            cellFormat.setAlignment(Qt.AlignCenter)
                        cellCharfmt.setFontWeight(QFont.Bold)
                        tableCursor.insertBlock(cellFormat, cellCharfmt)
                        tableCursor.insertText(model.headerData(x, Qt.Horizontal))
                        tableCursor.movePosition(QTextCursor.NextCell)
                        tableCol += 1
                qry = model.query()
                row = 1
                qry.seek(-1)
                cellCharfmt.setFontWeight(QFont.Normal)
                while qry.next():
                    col = 0
                    rec = qry.record()
                    for x in range(rec.count()):
                        if x not in visibleColumns:
                            continue
                        tableCursor = table.cellAt(row, col).firstCursorPosition()
                        if alignDict[x] == 1:
                            cellFormat.setAlignment(Qt.AlignLeft)
                        elif alignDict[x] == 4:
                            cellFormat.setAlignment(Qt.AlignCenter)
                        elif alignDict[x] == 2:
                            cellFormat.setAlignment(Qt.AlignRight)
                        tableCursor.insertBlock(cellFormat, cellCharfmt)
                        if type(rec.value(x)) is int:
                            tableCursor.insertText(str(rec.value(x)))
                        elif type(rec.value(x)) is QDate:
                            tableCursor.insertText(rec.value(x).toString('MM-dd-yyyy'))
                        elif type(rec.value(x)) is float:
                            tableCursor.insertText("{:,.2f}".format(rec.value(x)))
                        else:
                            tableCursor.insertText(rec.value(x))
                        tableCursor.movePosition(QTextCursor.NextCell)
                        col += 1
                    row += 1
                cellFormat.setAlignment(Qt.AlignRight)
                cellCharfmt.setFontWeight(QFont.Bold)
                row = 6
                while row <= 5 + len(bottomData):
                    for col in range(1,table.columns()):
                        if col == 1:
                            cellFormat.setAlignment(Qt.AlignLeft)
                        else:
                            cellFormat.setAlignment(Qt.AlignRight)
                        tableCursor = table.cellAt(row, col).firstCursorPosition()
                        tableCursor.insertBlock(cellFormat, cellCharfmt)
                        tableCursor.insertText(bottomData[row - 6][col-1])
                        tableCursor.movePosition(QTextCursor.NextCell)
                    row += 1
                if self.record.value(10):
                    cursor.setPosition(mainFrame.lastPosition())
                    cursor.insertBlock(billToFormat, billToCharfmt)
                    cursor.insertText("    ")
                    cursor.insertBlock(billToFormat, billToCharfmt)
                    cursor.insertText("Exchange Rate AR$: {:.2f}".format(self.record.value(10)/self.record.value(6)))
            if not printer:
                return document
            document.print(printer)
        except Exception as err:
            print(type(err), err.args)

    def handlePrint(self):
        dialog = QPrintDialog()
        if dialog.exec_():
            self.handlePaintRequest(dialog.printer())



