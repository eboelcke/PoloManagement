


from PyQt5.QtPrintSupport import QPrintPreviewDialog, QPrintDialog
from PyQt5.QtGui import (QTextDocument, QTextCursor, QStandardItemModel, QStandardItem,
                         QTextTableFormat, QTextLength, QIcon, QDoubleValidator,
                         QTextTableCellFormat, QTextCharFormat, QFont, QTextOption, QColor,
                         QFocusEvent, QMouseEvent, QTextFrameFormat, QTextFrame)
from PyQt5.QtWidgets import (QTableView, QMessageBox, QHeaderView, QDateEdit, QProgressDialog, QToolButton,
                             QLineEdit, QSpinBox, QWidget, QHBoxLayout, QVBoxLayout, QComboBox, QApplication, QLabel,
                             QPlainTextEdit, QAbstractItemView, QDialog, QTextEdit)
from PyQt5.QtCore import (Qt, QVariant, pyqtSignal, pyqtSlot, QEvent, QObject, QTimer,QRunnable,
                          QMetaObject, QThread, Q_ARG, Q_RETURN_ARG, QDate)
from PyQt5.QtSql import QSqlQueryModel, QSqlDatabase, QSqlQuery
import sys, traceback, time

DOWNPAYMENT = 0
INSTALLMENT = 1
FINAL_PAYMENT = 2
BREAKE_BALANCE = 3
BREAKE_BASE = 4
SALE_COMMISION = 5
OTHER_PAYMENTS = 6

AGREEMENT_TYPE_BREAKING = 0
AGREEMENT_TYPE_FULL = 1
AGREEMENT_TYPE_PLAY = 2
AGREEMENT_TYPE_OVER_BASE = 3
AGREEMENT_TYPE_OVER_EXPENSES = 4

OPEN_NEW = 7
OPEN_EDIT = 8
OPEN_EDIT_ONE = 9
OPEN_FILE = 10
OPEN_DELETE = 14
DELETE_FILE = 11
COPY_FILE = 12
RENAME_FILE = 13

CONTACT_RESPONSIBLE = 30
CONTACT_PLAYER = 31
CONTACT_BREAKER = 32
CONTACT_BUYER = 33
CONTACT_DEALER = 34
CONTACT_ALL = 35
CONTACT_POLO_PLAYER = 36
CONTACT_BUSTER = 37
CONTACT_VETERINARY = 38

HORSE_BREAKING = 40
HORSE_PLAYING = 41
HORSE_INVENTORY = 42

REPORT_TYPE_ALL_HORSES = 50
REPORT_TYPE_ALL_BREAKING_HORSES = 51
REPORT_TYPE_ALL_PLAYING_HORSES = 52

BRAKE_TYPE_FINAL = 0
BRAKE_TYPE_HALFBREAKE = 1
BRAKE_TYPE_INCOMPLETE = 2

BRAKE_RATE_EXCELLENT = 0
BRAKE_RATE_VERY_GOOD = 1
BRAKE_RATE_GOOD = 2
BRAKE_RATE_FAIR_=3
BRAKE_RATE_POOR = 4

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

PAYABLES_TYPE_DOWNPAYMENT = 0
PAYABLES_TYPE_BOARD = 1
PAYABLES_TYPE_FULL_BREAK = 2
PAYABLES_TYPE_HALF_BREAK = 3
PAYABLES_TYPE_SALE = 4
PAYABLES_TYPE_OTHER= 5
PAYABLES_TYPE_ALL = 6

PAYMENT_MODALITY_AT_END = 0
PAYMENT_MODALITY_MONTHLY_FEE = 1
PAYMENT_MODALITY_MONTHLY_ONSITEONLY = 2

TEMP_RECORD_IN = 0
TEMP_RECORD_OUT = 1

PAYMENT_TYPE_CHECK = 0
PAYMENT_TYPE_TRANSFER = 1
PAYMENT_TYPE_CASH = 2

PAYMENT_CURRENCY_USA = 0
PAYMENT_CURRENCY_LOCAL = 1

CLEARENCE_REASON_BREAK = 0
CLEARENCE_REASON_REJECT = 1

CURRENCY_USA_DOLAR = 0
CURRENCY_ARGENTINE_PESO = 1

OTHER_CONCEPT_TRANSPORTATION = 0
OTHER_CONCEPT_VETERINARY = 1
OTHER_CONCEPT_BLACKSMITH = 2
OTHER_CONCEPT_TACK = 3
OTHER_CONCEPT_CLUB_FEE = 4
OTHER_CONCEPT_TOURNAMENT_FEE = 5
OTHER_CONCEPT_STALLS = 6
OTHER_CONCEPT_OTHER = 7

INVOICE_TYPE_C = 0
INVOICE_TYPE_A = 1

BANCO_GALICIA = 0
BANCO_NACION = 1
BANCO_PROVINCIA = 2
BANCO_SANTANDER = 3
BANCO_COLUMBIA = 4
BANCO_MACRO = 5
BANCO_FRANCES = 6

WHERE_CLAUSE_ONE = 0
WHERE_CLAUSE_ALL = 1

class Error(Exception):
    pass

class DataError(Error):

    def __init__(self, source, message, type = None):
        self.message = message
        self.source = source
        self.type = type

class Cdatabase(QSqlDatabase):

    def __init__(self,db,dbName='cbd', openedConnection = []):
        super().__init__()
        self.opendConnection = openedConnection
        self.db = db
        try:
            if not QSqlDatabase.contains(dbName) :
                self.db = self.cloneDatabase(db, dbName)
        except Exception as err:
            raise DataError("CDatabase - __init__",  self.lastError().text())

    def __enter__(self):
        if not self.db.open():
            raise DataError( "MySQL Connection",
                                 self.db.lastError().text() + " The program will close now!",
                             self.db.lastError().type())
        return self.db

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()

class FocusPlainTextEdit(QPlainTextEdit):
    focusOut = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.installEventFilter(self)
        #self.setFocusPolicy(Qt.StrongFocus)

    def eventFilter(self, obj, event):
        if type(obj) is FocusPlainTextEdit:
            if event.type() == QEvent.FocusOut:
                self.focusOut.emit()
        return super().eventFilter(obj, event)

class CreateDatabase():
    def __init__(self, con_string, parent=None):
        self.con_string = con_string

    def create(self):
        db = QSqlDatabase.addDatabase("QMYSQL", "Create")
        db.setUserName(self.con_string['user'])
        db.setHostName(self.con_string['host'])
        db.setPassword(self.con_string['password'])
        ok = db.open()
        if not ok:
            raise DataError('create', db.lastError().text())
        qry = QSqlQuery(db)
        qry.prepare("CREATE DATABASE IF NOT EXISTS {}".format(self.con_string['database']))
        #qry.prepare("CREATE DATABASE IF NOT EXISTS ?")
        #qry.addBindValue(QVariant(self.con_string['database']))
        qry.exec()
        if qry.lastError().type() != 0:
            print(qry.lastError().text())
            raise DataError('create', qry.lastError().text())
        return True



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
            Where   colNumber is the column number to be checked.
                    checkString is the string to be match in the above column.
                    QColor(b) is the color to assigned to the background.
                    QColor(t) is the color to be aliened to the text.
            """

    def __init__(self, centerColumns, rightColumns, colorDict):
        super().__init__()
        self.centerColumns = centerColumns
        self.rightColumns = rightColumns
        self.colorDict = colorDict

    def data(self, idx, role=Qt.DisplayRole):
        try:
            if not idx.isValid() or \
                not(0<=idx.row() < self.query().size()):
                return QVariant()
            if self.query().seek(idx.row()):
                qry = self.query().record()
                value = qry.value(idx.column())
                if role == Qt.DisplayRole:
                    if isinstance(value,float):
                        num = QVariant('{:.2f}'.format(round(value,2))) if value >= 0 else \
                            QVariant("({:.2f})".format(abs(round(value,2))))
                        return num
                    return QVariant(qry.value(idx.column()))
                if role == Qt.TextAlignmentRole:
                    if idx.column() in self.centerColumns:
                        return QVariant(Qt.AlignHCenter)
                    elif idx.column() in self.rightColumns:
                        return QVariant(Qt.AlignRight)
                    return QVariant(Qt.AlignLeft)
                if role == Qt.TextColorRole:
                    try:
                        value = qry.value(idx.column())
                        if isinstance(value, float) and value < 0:
                            return QVariant(QColor("red"))
                        return QVariant(self.colorDict[qry.value(self.colorDict['column'])][1])
                    except KeyError:
                        return
                if role == Qt.BackgroundColorRole:
                    try:
                        if isinstance(value, float) and value < 0 :
                            return QVariant(QColor("white"))
                        return QVariant(self.colorDict[qry.value(self.colorDict['column'])][0])
                    except KeyError:
                        return
        except Exception as err:
            print(type(err).__name__, err.args)

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
                                     int colCentered - (1:center; 2 right;0 default leftAlign
                                     int/None printWidth)}
        size: (height int, width int) Size of the table

    """

    currentMove = pyqtSignal(int)

    def __init__(self, colDict, colorDict, size, qry=None):
        super().__init__()
        self.qry = qry
        self.colorDict = colorDict
        self.colDict = colDict
        self.size = size
        self.installEventFilter(self)
        if self.qry is not None:
            self.setTable()

    def setTable(self):
        try:
            fields = self.qry.record().count()
            centerColumns = [x for x in range(fields) if self.colDict[x][3]== 1]
            rightColumns = [x for x in range(fields) if self.colDict[x][3]== 2]
            model = QSqlAlignColorQueryModel(centerColumns, rightColumns, self.colorDict)
            model.setQuery(self.qry)
            [model.setHeaderData(x, Qt.Horizontal, self.colDict[x][0]) for x in range(fields)]
            self.setModel(model)
            [self.hideColumn(x) for x in range(fields) if self.colDict[x][1]]
            header = self.horizontalHeader()
            [header.setSectionResizeMode(x, QHeaderView.ResizeToContents) if self.colDict[x][2] else
            header.setSectionResizeMode(x, QHeaderView.Stretch) for x in range(fields)]
            visibleColumns = len([x for x in range(fields) if not self.isColumnHidden(x)])
            #printColumnWidths = [QTextLength(QTextLength.FixedLength, self.colDict[x][4]) if
            #                     self.colDict[x][4] is not None else QTextLength() for x in range(visibleColumns)]

            self.verticalHeader().setVisible(False)
            self.verticalHeader().setDefaultSectionSize(25)
            self.horizontalHeader().setStyleSheet("QHeaderView { font-size: 8pt;}")
            self.setStyleSheet("TableViewAndModel {font-size: 8pt;}")
            #self.setMinimumSize(*self.size)
            self.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.setSelectionMode(QAbstractItemView.SingleSelection)
        except DataError as err:
            QMessageBox.warning(self,"DataError", err.message)
        except Exception as err:
            print(type(err).__name__, err.args)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Down:
                self.currentMove.emit(self.currentIndex().row() + 1)
            if event.key() == Qt.Key_Up:
                self.currentMove.emit(self.currentIndex().row() +1)
        return super().eventFilter(obj, event)

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
        self.dateChanged.emit(self)

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
        if itemList is None:
            focusModel = QSqlQueryModel()
            super(FocusCombo, self).setModel(focusModel)
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

    def seekMultipleData(self, dataDict):
        """Function designto get a match on several columns of a QComboBox
            **dataDict is a dictionary od the form {"column int": data}
            The "column" mus be consisten with the combo Query"""
        qry = self.model().query()
        row = -1
        while qry.next():
            row +=1
            for key in dataDict.keys():
                check = True
                if qry.value(key) != dataDict[key]:
                    check = False
                    break
            if not check:
                continue
            else:
                break
        if check:
            self.setCurrentIndex(row)



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
        return idx

    def getHiddenData(self, column):
        """Function to retrieve data from not visible columns
        Input: int: column
        Output str: data"""
        col = self.modelColumn()
        self.setModelColumn(column)
        if self.currentText().isdigit():
            val = int(self.currentText())
        else:
            val = self.currentText()
        self.setModelColumn(col)
        return val

class SQL_Query(QSqlQuery):
    """Subclass QSqlQuery adding the method seekData providing a way to
    find the first record where the search value is locates
    Data:
        data : value to be search for (str|int|date|decimal)
        column: field where to look for (int)"""

    def __init__(self, db):
        super().__init__(db)

    def seekData(self, data, column):
        try:
            self.seek(-1)
            while self.next():
                if self.value(column) == data:
                    return True
            return False

        except DataError as err:
            print(err.source, err.message)
        except Exception as err:
            print('seekData', type(err).__name__, err.args)

class FocusSpin(QSpinBox):
    focusLost = pyqtSignal(int)
    focusGot = pyqtSignal(QSpinBox)

    def __init__(self, parent = None):
        super().__init__(parent)
        self.parent = parent

    def focusOutEvent(self, event):
        if event.gotFocus():
            self.focusGot.emit(self.value())

        elif event.lostFocus():
            try:
                self.focusLost.emit(self.value())
            except Exception as err:
                print(err)
        return

if __name__ == '__main__':
    app = QApplication(sys.argv)
    cb = FocusCombo()
    cb.addItems(list("abcdef"))
    cb.setEditable(True)
    cb.show()
    cb.doubleClicked.connect(print)
    app.exec_()
    sys.exit(app.exec_())

class ProgressWidget(QWidget):
    finished = pyqtSignal()

    def __init__(self, parent=None):
        super(ProgressWidget, self).__init__(parent)
        self.pd = QProgressDialog("Operation in Progress..", None, 0, 100, parent)
        self.pd.setWindowModality(Qt.WindowModal)
        self.pd.canceled.connect(self.cancel)
        self.t = QTimer(self)
        self.t.timeout.connect(self.perform)
        self.pd.setValue(0)
        self.t.start(10)

    @property
    def value(self):
        return self.pd.value()

    @pyqtSlot()
    def perform(self):
        step = self.pd.value() + 1
        self.pd.setValue(step)
        if step > self.pd.maximum():
            self.cancel()

    def wasFinished(self):
        print("Progress Canceled")
        return self.pd.wasCanceled()


    @pyqtSlot()
    def cancel(self):
        self.t.stop()
        self.finished.emit()


class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)

class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.kwargs['progress_callback'] = self.signals.progress

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()

class Runnable(QRunnable):
    cycles = 0
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.fn.setValue(10)
        self.fn.show()
        self.data = args
        self.t = QTimer()
        self.t.timeout.connect(self.run)
        self.t.start(1000)

    def run(self):
        while self.cycles <= self.fn.maximum():
            QMetaObject.invokeMethod(self.fn, "setValue", Qt.QueuedConnection, Q_ARG(int, self.cycles))
            self.cycles += 1
            time.sleep(0.5)
            if self.cycles > self.fn.maximum():
                self.t.stop()

TIME_LIMIT = 1000

class WorkerThread(QThread):
    #countChanged = pyqtSignal(int)

    def __init__(self, obj):
        super().__init__()
        self.obj = obj
        self.start()

    def run(self):
        count = 0
        while count <= TIME_LIMIT:
            count += 1
            time.sleep(0.1)
            QMetaObject.invokeMethod(self.obj, "setValue", Qt.QueuedConnection, Q_ARG(int, count))
            #self.countChanged.emit(count)
