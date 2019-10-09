

from PyQt5.QtWidgets import (QMessageBox, QDialog, QPushButton, QTableView, QVBoxLayout,
                             QHeaderView, QHBoxLayout)
from PyQt5.QtSql import QSqlQuery, QSqlQueryModel
from PyQt5.QtCore import Qt, QVariant
from PyQt5.QtGui import QColor, QTextLength
from PyQt5.QtPrintSupport import QPrintPreviewDialog, QPrintDialog
from ext.CQSqlDatabase import Cdatabase
from ext.APM import DataError, ReportPrint, QSqlAlignColorQueryModel
from ext.Horses import QSqlAlignQueryModel
from ext import APM



class AvailableHorses(QDialog):

    def __init__(self, db, reportType, parent=None):
        super().__init__(parent=None)
        self.parent = parent
        self.reportType = reportType
        self.cdb = db
        self.setModal(True)
        self.setUI()
        self.table = None
        self.centerColumns = []
        self.printColumnWidths = []
        if self.reportType == APM.REPORT_TYPE_ALL_HORSES:
            self.setAllHorsesTable()
        elif self.reportType == APM.REPORT_TYPE_ALL_BREAKING_HORSES:
            self.setAllBreakingHorsesTable(APM.REPORT_TYPE_ALL_BREAKING_HORSES)
        elif self.reportType == APM.REPORT_TYPE_ALL_PLAYING_HORSES:
            self.setAllBreakingHorsesTable(APM.REPORT_TYPE_ALL_PLAYING_HORSES)


    def setUI(self):
        self.setWindowTitle("Unassigned Horses")
        self.horseTable = QTableView()
        self.horseTable.verticalHeader().setVisible(False)

        oKButton = QPushButton("OK")
        oKButton.clicked.connect(self.close)
        oKButton.setMaximumSize(50, 30)

        printButton = QPushButton('Print')
        printButton.setMaximumSize(80,30)
        printButton.clicked.connect(self.handlePrint)

        previewButton = QPushButton('Preview')
        previewButton.setMaximumSize(80,30)
        previewButton.clicked.connect(self.handlePreview)

        buttonsLayout = QHBoxLayout()
        buttonsLayout.addWidget(printButton)
        buttonsLayout.addWidget(previewButton)
        buttonsLayout.addWidget(oKButton)


        layout = QVBoxLayout()
        layout.addWidget(self.horseTable)
        layout.addLayout(buttonsLayout)
        self.setLayout(layout)

    def setAllBreakingHorsesTable(self, mode):
        qry = QSqlQuery(self.cdb)
        qry.prepare("""SELECT 
        ah.id ID, 
        h.rp RP, 
        h.name, 
        CASE 
            WHEN h.sexid = 1 THEN _ucs2 X'2642'
            WHEN h.sexid = 2 THEN _ucs2 X'2640'
            WHEN h.sexid = 3 THEN _ucs2 X'265E'
        END Sex,
        c.coat as Coat,
        TIMESTAMPDIFF(YEAR, h.dob, CURDATE()) Age,
        TIMESTAMPDIFF(MONTH, ah.dos, CURDATE()) Month,
        ah.agreementid AgrNo,
        ct.fullname as Contact
        FROM 
        agreementhorses AS ah
        INNER JOIN horses AS h 
        ON ah.horseid = h.id
        INNER JOIN coats as c
        ON h.coatid = c.id
        INNER JOIN agreements as a
        ON ah.agreementid = a.id
        INNER JOIN contacts as ct
        ON a.supplierid = ct.id 
        WHERE ah.active 
            AND a.breaking = ?
        ORDER BY a.breaking, a.id;""")
        qry.addBindValue(QVariant(True))if self.reportType == APM.REPORT_TYPE_ALL_BREAKING_HORSES \
            else qry.addBindValue(QVariant(False))
        qry.exec_()
        try:
            if qry.size() < 0:
                raise DataError('setAllHorsesTable', qry.lastError().text())
            elif qry.size() == 0:
                raise DataError('No Data', "There are not horses to show")
            self.centerColumns = [1, 3, 5, 6, 7]
            colorDict = {'column': (3),
                         u'\u2640': (QColor('pink'), QColor('black')),
                         u'\u2642': (QColor('lightskyblue'), QColor('black')),
                         u'\u265E': (QColor('lightgrey'), QColor('black'))}
            allHorsesModel = QSqlAlignColorQueryModel(self.centerColumns,colorDict)
            allHorsesModel.setQuery(qry)
            allHorsesModel.setHeaderData(0, Qt.Horizontal, "ID")
            allHorsesModel.setHeaderData(1, Qt.Horizontal, "RP")
            allHorsesModel.setHeaderData(2, Qt.Horizontal, "Name")
            allHorsesModel.setHeaderData(3, Qt.Horizontal, "Sex")
            allHorsesModel.setHeaderData(4, Qt.Horizontal, "Coat")
            allHorsesModel.setHeaderData(5, Qt.Horizontal, "Age")
            allHorsesModel.setHeaderData(6, Qt.Horizontal, "Month")
            allHorsesModel.setHeaderData(7, Qt.Horizontal, "AgrNo")
            allHorsesModel.setHeaderData(8, Qt.Horizontal, "With")
            self.horseTable.setModel(allHorsesModel)
            self.horseTable.hideColumn(0)
            header = self.horseTable.horizontalHeader()
            header.setStyleSheet("QHeaderView {font-size: 8pt;}")
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.Stretch)
            header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(8, QHeaderView.ResizeToContents)
            self.horseTable.setRowHeight(0, 10)
            self.horseTable.verticalHeader().setDefaultSectionSize(
                self.horseTable.rowHeight(0))
            self.horseTable.setMinimumSize(700, 400)
            self.setWindowTitle("Horses On Breaking Agreements") if self.reportType == APM.REPORT_TYPE_ALL_BREAKING_HORSES \
                else self.setWindowTitle("Horses On Play & Sale Agreements")
            self.setMinimumWidth(800)
            # set the printing column widths

            col_1 = QTextLength(QTextLength.FixedLength, 45)
            col_2 = QTextLength()
            col_3 = QTextLength(QTextLength.FixedLength, 45)
            col_4 = QTextLength(QTextLength.FixedLength, 120)
            col_5 = QTextLength(QTextLength.FixedLength, 45)
            col_6 = QTextLength(QTextLength.FixedLength, 45)
            col_7 = QTextLength(QTextLength.FixedLength, 45)
            col_8 = QTextLength()

            self.printColumnWidths = [col_1, col_2, col_3, col_4, col_5,
                                      col_6, col_7, col_8]


        except DataError as err:
            QMessageBox.warning(self, "DataError", err.message)


    def setAllPlayingHorsesTable(self):
        pass

    def setAllHorsesTable(self):
        """Gets the query for the model, uses a subclasesd SqlQueryModel including the posibility to
        pass information on centered columns and tex and background colors.
        Centered columns ares set in a list ([column#,....column#n]) where column referes to the column that
         will be centered.
         The color information is place in a dictionary with the following format:
            {'column' : value,
            key1:(QTextColor, QBackGroundCColor),
             key2: (QTextColor, QBackgroundColor),
             ....................................,
             keyn:(QTextColor, QBackgroundColor)}}
        where:
            column is the query field number,
            key is the comparison value to check agaisnt the query(column).value()
            and (QTextColor, QBackGroundColor) is a tuple with two QColor values, the first for
            QTextColorRole, and the second for QbackgroundColorrole"""
        colorDict = {'column':(5),
                        u'\u2640':(QColor('pink'), QColor('black')),
                        u'\u2642':(QColor('lightskyblue'), QColor('black')),
                        u'\u265E': (QColor('lightgrey'), QColor('black'))}
        try:
            with Cdatabase(self.cdb, 'reportAll') as db:
                qry = QSqlQuery(db)
                qry.exec_("""SELECT h.id,
                 h.rp,
                 h.name,
                 h.dob,
                 FLOOR(DATEDIFF(CURDATE(), h.dob)/365) Age,
                 CASE WHEN h.sexid = 1 THEN _ucs2 X'2642'
                 WHEN h.sexid = 2 THEN _ucs2 X'2640'
                 WHEN h.sexid = 3 THEN _ucs2 X'265E'
                 END Sex,
                 c.coat,
                 IF (h.isbroke = 1, _ucs2 X'2714', '') broke,
                 IF (h.isbreakable = 1, _ucs2 X'2714', '') breakable,
                 IF (h.active = 1, _ucs2 X'2714', '') active
                 FROM horses as h
                 INNER JOIN sexes as s
                 ON h.sexid = s.id
                 INNER JOIN coats as c
                 ON h.coatid = c.id
                 WHERE h.active
                 AND h.id NOT IN (SELECT ah.horseid FROM agreementhorses ah
                                  WHERE ah.active)
                 ORDER BY h.isbroke, h.sexid, h.name""")
            if qry.size() < 1:
                raise DataError('setAllHorsesTable', qry.lastError().text())
            self.centerColumns = [1, 4, 5, 7, 9]
            allHorsesModel = QSqlAlignColorQueryModel(self.centerColumns,colorDict)
            allHorsesModel.setQuery(qry)
            allHorsesModel.setHeaderData(1,Qt.Horizontal,"RP")
            allHorsesModel.setHeaderData(2, Qt.Horizontal, "Name")
            allHorsesModel.setHeaderData(3, Qt.Horizontal, "DOB")
            allHorsesModel.setHeaderData(4, Qt.Horizontal, "Age")
            allHorsesModel.setHeaderData(5, Qt.Horizontal, "Sex")
            allHorsesModel.setHeaderData(6, Qt.Horizontal, "Coat")
            allHorsesModel.setHeaderData(7, Qt.Horizontal, "Broke")
            allHorsesModel.setHeaderData(9,Qt.Horizontal, "Active")
            self.horseTable.setModel(allHorsesModel)
            self.horseTable.hideColumn(0)
            self.horseTable.hideColumn(8)
            header = self.horseTable.horizontalHeader()
            header.setStyleSheet("QHeaderView {font-size: 8pt;}")
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.Stretch)
            header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(9, QHeaderView.ResizeToContents)
            self.horseTable.setRowHeight(0, 10)
            self.horseTable.verticalHeader().setDefaultSectionSize(
                self.horseTable.rowHeight(0))
            self.horseTable.setMinimumSize(700, 400)

            #set the printing column widths

            col_1 = QTextLength(QTextLength.FixedLength, 45)
            col_2 = QTextLength()
            col_3 = QTextLength(QTextLength.FixedLength, 100)
            col_4 = QTextLength(QTextLength.FixedLength, 45)
            col_5 = QTextLength(QTextLength.FixedLength, 45)
            col_6 = QTextLength(QTextLength.FixedLength, 120)
            col_7 = QTextLength(QTextLength.FixedLength, 60)
            col_8 = QTextLength(QTextLength.FixedLength, 60)

            self.printColumnWidths = [col_1, col_2, col_3, col_4, col_5,
                                      col_6, col_7, col_8]

        except DataError as err:
            QMessageBox.warning(self,"DataError", err.message)

    def handlePrint(self):
        rep = ReportPrint(self.horseTable,self.window.title(),self.centerColumns,
                          self.printColumnWidths)
        rep.handlePrint()

    def handlePreview(self):
        rep = ReportPrint(self.horseTable, self.windowTitle(), self.centerColumns,
                          self.printColumnWidths)
        rep.handlePreview()






