


from PyQt5.QtPrintSupport import QPrintPreviewDialog, QPrintDialog
from PyQt5.QtGui import (QTextDocument, QTextCursor, QStandardItemModel, QStandardItem,
                         QTextTableFormat, QTextLength, QIcon, QDoubleValidator,
                         QTextTableCellFormat, QTextCharFormat, QFont, QTextOption, QColor,
                         QFocusEvent, QMouseEvent)
from PyQt5.QtWidgets import (QTableView, QMessageBox, QHeaderView, QDateEdit, QPushButton, QToolButton,
                             QLineEdit, QSpinBox, QWidget, QHBoxLayout, QComboBox, QApplication, QLabel)
from PyQt5.QtCore import Qt, QVariant, pyqtSignal, pyqtSlot, QEvent
from PyQt5.QtSql import QSqlQueryModel

#from PyQt5 import QtGui
import sys

from PyQt5.QtCore import Qt, QDate
DOWNPAYMENT = 0
INSTALLMENT = 1
FINAL_PAYMENT = 2
BREAKE_BALANCE = 3
BREAKE_BASE = 4
SALE_COMMISION = 5
OTHER_PAYMENTS = 6

OPEN_NEW = 7
OPEN_EDIT = 8
OPEN_EDIT_ONE = 9
OPEN_FILE = 10
DELETE_FILE = 11
COPY_FILE = 12
RENAME_FILE = 13

CONTACT_RESPONSIBLE = 30
CONTACT_PLAYER = 31
CONTACT_BREAKER = 32
CONTACT_BUYER = 33
CONTACT_DEALER = 34
CONTACT_ALL = 35

HORSE_BREAKING = 40
HORSE_PLAYING = 41
HORSE_INVENTORY = 42

REPORT_TYPE_ALL_HORSES = 50
REPORT_TYPE_ALL_BREAKING_HORSES = 51
REPORT_TYPE_ALL_PLAYING_HORSES = 52

BRAKE_TYPE_POLO = 0
BRAKE_TYPE__CRIOLLA = 1
BRAKE_TYPE_HALFBREAKE = 2
BRAKE_TYPE_INCOMPLETE = 3

BRAKE_RATE_EXCELLENT = 0
BRAKE_RATE_GOOD = 1
BRAKE_RATE_FAIR_=2
BRAKE_RATE_POOR = 3

MORTALITY_CAUSE_DISEASE = 0
MORTALITY_CAUSE_ACCIDENT = 1
MORTALITY_CAUSE_SLAUGHTER = 2
MORTALITY_CAUSE_OLD_AGE = 3
MORTALITY_CAUSE_UNKNOWN = 4

REJECTION_TYPE_FINAL = 0
REJECTION_TYPE_VETERINARY = 1
REJECTION_TYPE_TRANSITORY = 2

REJECTION_CAUSE_PERFORMANCE = 0
REJECTION_CAUSE_CONFORMATION = 1
REJECTION_CAUSE_DISEASE = 2
REJECTION_CAUSE_INJURIY = 3
REJECTION_CAUSE_UNKNOWN = 4

PAYABLES_TYPE_SALE = 0
PAYABLES_TYPE_BOARD = 1
PAYABLE_TYPE_OTHER = 2



class Error(Exception):
    pass

class DataError(Error):

    def __init__(self, source, message, type = None):
        self.message = message
        self.source = source
        self.type = type

class ReportPrint():
    def __init__(self, table,title, centerColumns, colWidths):
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
        docCharFormat.setFont(QFont('Helvetica', 20))
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
        ageWith = QTextLength(QTextLength.FixedLength,45)
        sexWidth = QTextLength(QTextLength.FixedLength,45)
        coatWidth = QTextLength(QTextLength.FixedLength,120)
        brokeWidth = QTextLength(QTextLength.FixedLength, 60)
        activeWidth = QTextLength(QTextLength.FixedLength, 60)

        fmt.setColumnWidthConstraints(self.colWidths)
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
                    tableCursor.insertText(rec.value(x), charFormat)
                tableCursor.movePosition(QTextCursor.NextCell)
                col +=1
            row += 1
        document.print(printer)

class QSqlAlignColorQueryModel(QSqlQueryModel):
    """QSqlQueryModel subclass allowing for :
        - Center the data through a list of columns numbers to
          be centered -
          CenterColumns = [colNumber int,......colNumber int]
        - Set the font and background color using the  colorDict dictionary
        'column' is the dictionary key and must be write exactly as it is.
         colorDict = {'column': (colNumber int),
            checkString: (QColor(b), QColor(t)),
            ..
            ..
            checkString: (QColor(), QColor())]
            Where   colNumber is the coloumn number to be checked.
                    checkString is the string to be match in the above column.
                    QColor(b) is the color to assigned to the background.
                    QColor(t) is the color to be aliened to the text.
            """

    def __init__(self, centerColumns, colorDict):
        super().__init__()
        self.centerColumns = centerColumns
        self.colorDict = colorDict

    def data(self, idx, role=Qt.DisplayRole):
        try:
            if not idx.isValid() or \
                not(0<=idx.row() < self.query().size()):
                return QVariant()
            if self.query().seek(idx.row()):
                qry = self.query().record()
                if role == Qt.DisplayRole:
                    return QVariant(qry.value(idx.column()))
                if role == Qt.TextAlignmentRole:
                    if idx.column() in self.centerColumns:
                        return QVariant(Qt.AlignHCenter)
                    return QVariant(Qt.AlignLeft)
                if role == Qt.TextColorRole:
                    try:
                        return QVariant(self.colorDict[qry.value(self.colorDict['column'])][1])
                    except KeyError:
                        return
                if role == Qt.BackgroundColorRole:
                    try:
                        return QVariant(self.colorDict[qry.value(self.colorDict['column'])][0])
                    except KeyError:
                        return
        except Exception as err:
            print(type(err.__name__), err.args)

    def findIdItem(self, id, fieldNumber):
        self.query().seek(-1)
        while self.query().next():
            if self.query().value(fieldNumber) == id:
                return self.query().record()
        raise DataError("findIdItem", "Record not found", 10)


class TableViewAndModel(QTableView):
    """
    Tableview intended to include a QSclQueryModel, using the QSqlAlignColorQueryModel alreadey modified as to center
     and color rows and columns. Parameters are:
        qry: The query to expose. It must include an id column that would be hidden plus other optiona columns that
            be also hidden;
        colorDict:, dictionary with the key of the string value to check for each row and the value being a tuple of the
            column number to be checked and the color pair for text and background.
        colDict: Dictionary {colNb: (str colName,
                                     bool colHidden,
                                     bool QHeaderView,
                                     bool colCentered - default rightAlign
                                     int/None printWidth)}
        size: (height int, width int) Size of the table

    """

    def __init__(self, colDict, colorDict, size, qry=None):
        super().__init__()
        self.qry = qry
        self.colorDict = colorDict
        self.colDict = colDict
        self.size = size
        if self.qry is not None:
            self.setTable()

    def setTable(self):
        try:
            if self.qry.size() < 0:
                return
            self.qry.first()
            fields = self.qry.record().count()
            centerColumns = [x for x in range(fields) if self.colDict[x][3]]
            model = QSqlAlignColorQueryModel(centerColumns, self.colorDict)
            model.setQuery(self.qry)
            [model.setHeaderData(x, Qt.Horizontal, self.colDict[x][0]) for x in range(fields)]
            self.setModel(model)
            [self.hideColumn(x) for x in range(fields) if self.colDict[x][1]]
            header = self.horizontalHeader()
            [header.setSectionResizeMode(x, QHeaderView.ResizeToContents) if self.colDict[x][2] else
            header.setSectionResizeMode(x, QHeaderView.Stretch) for x in range(fields)]
            visibleColumns = len([x for x in range(fields) if not self.isColumnHidden(x)])
            printColumnWidths = [QTextLength(QTextLength.FixedLength, self.colDict[x][4]) if
                                 self.colDict[x][4] is not None else QTextLength() for x in range(visibleColumns)]

            self.verticalHeader().setVisible(False)
            self.verticalHeader().setDefaultSectionSize(25)
            self.horizontalHeader().setStyleSheet("QHeaderView { font-size: 8pt;}")
            self.setStyleSheet("TableViewAndModel {font-size: 8pt;}")
            self.setMinimumSize(*self.size)
        except DataError as err:
            QMessageBox.warning(self,"DataError", err.message)
        except Exception as err:
            print(type(err).__name__, err.args)

    @property
    def query(self):
        return self.qry

    @query.setter
    def query(self, qry):
        self.qry = qry

    def findRecordId(self, column, id ):
        self.qry.fist()
        while self.qry.next():
            if self.qry.idx.column(column) == id:
                return qry.record()

class PercentOrAmountLineEdit(QWidget):
    """This custom widget consists on a QLabel; a QLineEdit and a QPushButton.
    Clicking on the push button will toggle: on the label with the % sign; on the
    QLineEdit the validator from the amount format '###.."".00' to the percent format expresed  as
    '0.00 to 100.00'
    Input:
        labelText: str: label text
        amountData: tuple: (int from, int to, int decimal) for Amount Validator
        percentDecimal: int number of percent decimals"""

    def __init__(self, labelText, amountData, percentDecimal, parent=None, percent = False):
        super().__init__(parent=None)
        self.labelText = labelText
        self.amountData = amountData
        self.percentDecimal = percentDecimal
        self.parent = parent
        self.percent = percent
        self.setUI()

    def setUI(self):
        self.setToolTip("Enter the total amount")
        self.toggleButton = QToolButton(self)
        self.toggleButton.setIcon(QIcon(":Icons8/Edit/reset.png"))
        self.toggleButton.setStatusTip('Toggles Percent(%)/Amount ($)')
        self.toggleButton.setMaximumSize(30, 25)
        self.toggleButton.clicked.connect(self.toggle)

        self.lblConcept = QLabel(self.labelText)

        self.amountValidator = QDoubleValidator(*self.amountData)
        self.amountValidator.setNotation(QDoubleValidator.StandardNotation)

        self.percentValidator = QDoubleValidator(0.00, 100.00, self.percentDecimal)
        self.percentValidator.setNotation(QDoubleValidator.StandardNotation)

        self.lineValue = QLineEdit('0.00')
        self.lineValue.setMaximumWidth(100)
        self.lineValue.setToolTip("Toggle Amount/Percent")
        self.lineValue.setAlignment(Qt.AlignRight)
        self.lineValue.setValidator(self.amountValidator)
        self.lineValue.enterEvent = lambda _ : self.lineValue.selectAll()
        self.lineValue.editingFinished.connect(self.parent.enableSave)
        self.lineValue.textChanged.connect(self.validateValue)
        layout = QHBoxLayout()
        layout.addWidget(self.lblConcept)
        layout.addWidget(self.toggleButton)
        layout.addWidget(self.lineValue)
        self.setLayout(layout)

    @pyqtSlot()
    def validateValue(self):
        if self.lineValue.hasAcceptableInput():
            return
        QMessageBox.warning(self, "Invalid Data", "{} is out of the range allowed from '{}' to '{}'".format(
            self.lineValue.text(), self.lineValue.validator().bottom(), self.lineValue.validator().top()))
        self.lineValue.setText('0.00')
        self.lineValue.setFocus()

    @property
    def isPercent(self):
        return self.percent

    def toggle(self):
        if not self.percent:
            self.lblConcept.setText(self.labelText + ' (%)')
            self.lineValue.setValidator(self.percentValidator)
            self.setToolTip("Enter The Expenses percent")
            self.percent = True
        else:
            self.lblConcept.setText(self.labelText + '($)')
            self.lineValue.setValidator(self.amountValidator)
            self.setToolTip("Enter Expense Amount ($)")
            self.percent = False
        self.lineValue.setText('0.00')

    def clear(self):
        self.lineValue.clear()

    @property
    def percentType(self):
        return self.percent

    @property
    def value(self):
        return self.lineValue.text()





class NullDateEdit(QWidget):
    """Custom widget including a QDateEdit widget and a QpushButton
    intended to accept null dates from a record or by resetting the
    QDateEdit widget.
    A null date can be set either by:
      - Clicking the QPushButton.
      - Double clicking the QDateEdit widget. It's not very dependable. You
            may need to click repeatedly until the signal goes through and in the mean time
            some section of the QDateEdit widget - particulary the month and year sections -
            may increase their value. Once the signal is fired, the widget it's set to None.
        - Setting an invalid or null date.
    On change of date a enableSave method will be fired.
    Requirements:
        -It must be called with the parent reference.
        - The calling widget must set the 'minimumDate' -'setMinimumDade.-
        - To make use of the doubleclick signal in the calling program a slot
             must be implemented either by setting the date to a null date (QDate(),
             or by calling the method 'clearDate()"""

    doubleClicked = pyqtSignal(QLineEdit)
    dateChanged = pyqtSignal(QDateEdit)

    def __init__(self, parent=None):
        super().__init__(parent=None)
        self.parent = parent
        self.initUI()
        self.lineEdit = self.findChild(QLineEdit)

    def initUI(self):
        layout = QHBoxLayout()
        self.clearButton = QToolButton(self)
        self.clearButton.setIcon(QIcon(":Icons8/Edit/reset.png"))
        self.clearButton.setStatusTip('Reset date to None')
        self.clearButton.setMaximumSize(30, 25)
        self.clearButton.clicked.connect(self.clearDate)
        self.dateEdit = QDateEdit()
        self.dateEdit.setMinimumWidth(120)
        self.dateEdit.setCalendarPopup(True)
        self.dateEdit.setSpecialValueText('None')
        self.dateEdit.dateChanged.connect(self.enableSave)
        layout.addWidget(self.clearButton)
        layout.addWidget(self.dateEdit)
        self.setLayout(layout)

    def setEditable(self, editable):
        self.setEditable(editable)
        if self.lineEdit is not None:
            self.lineEdit.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.lineEdit:
            if event.type() == QEvent.MouseButtonDblClick:
                self.doubleClicked.emit(self)
            elif event.type() == QEvent.KeyPress:
                self.dateChanged.emit(self)
        return super().eventFilter(obj, event)


    def mouseDoubleClickEvent(self, event):
        self.doubleClicked.emit(self)
        super().mouseDoubleClickEvent(event)


    @pyqtSlot()
    def clearDate(self):
        self.setDate(QDate())
        #self.parent.show()

    def enableSave(self):
        self.parent.enableSave()

    @property
    def minimumDate(self):
        return self.dateEdit.minimumDate()

    def setMinimumDate(self, date):
        self.dateEdit.setMinimumDate(date)

    @property
    def maximumDate(self):
        return self.dateEdit.maximumDate()

    def setMaximumDate(self,date):
        self.dateEdit.setMinimumDate(date)

    @property
    def date(self):
        return self.dateEdit.date()

    @property
    def text(self):
        return self.dateEdit.text()

    def setDate(self, date):
        if date.isNull():
            date = self.minimumDate
        self.dateEdit.setDate(date)





class FocusCombo(QComboBox):
    """Subclass of QComboBox that allows to :
    - Emmit a focusLost and focusGot signals
    - Emmit a doubleclicked signal
    - Set a list of items into the model as a two column
    Input:
    - parent: parent widget - default None
    _ itemList [itemStr(0) str,....., itemsStr(n)] - Default None"""
    focusLost = pyqtSignal(QComboBox)
    focusGot = pyqtSignal(QComboBox)
    doubleClicked = pyqtSignal(QComboBox)

    def __init__(self, parent = None, itemList = None):
        super().__init__(parent)
        if itemList is not None:
            self.setItemList(itemList)


    def setEditable(self, editable):
        super().setEditable(editable)
        if self.lineEdit() is not None:
            self.lineEdit().installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.lineEdit():
            if event.type() == QEvent.MouseButtonDblClick:
                self.doubleClicked.emit(self)
        return super(FocusCombo, self).eventFilter(obj,event)

    def mouseDoubleClickEvent(self,event):
        print("double click detected")
        self.doubleClicked.emit(self)
        super(FocusCombo, self).mouseDoubleClickEvent(event)

    def focusOutEvent(self, event):
        if event.gotFocus():
            self.focusGot.emit(self)

        elif event.lostFocus():
            self.focusLost.emit(self)
        super(FocusCombo, self).focusOutEvent(event)

    def setItemList(self, itemList):
        itemModel = QStandardItemModel(len(itemList), 2)
        keys = [str(x) for x in range(len(itemList))]

        for row, itemLst in enumerate(itemList):
            item = QStandardItem(keys[row])
            itemModel.setItem(row, 0, item)
            item = QStandardItem(itemList[row])
            itemModel.setItem(row, 1, item)
        super(FocusCombo, self).setModel(itemModel)

    def seekData(self, data, column=0):
        """Function design to position a combobox at the record searched - Usually with
        data from a db-. Required parameter ;data int; column int default: 0 - the default
        changes the columnModel
        from column 1 to column 0; searches the data (usually an id) and if found positions
        the combo at the found index, and changes back to the original column. Allows for
        a different column to be search - column -Optional parameter. If it does'nt find the
        data returns an DataError"""

        col = self.modelColumn()
        self.setModelColumn(column)
        idx = self.findData(data, Qt.DisplayRole, Qt.MatchExactly)
        self.setCurrentIndex(idx)
        self.setModelColumn(col)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    cb = FocusCombo()
    cb.addItems(list("abcdef"))
    cb.setEditable(True)
    cb.show()
    cb.doubleClicked.connect(print)
    app.exec_()
    sys.exit(app.exec_())









