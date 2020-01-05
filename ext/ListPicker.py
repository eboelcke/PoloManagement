from PyQt5.QtWidgets import (QPushButton, QTableView,QMessageBox,
                             QGridLayout, QApplication, QToolButton, QLabel, QGroupBox)
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt5.QtSql import QSqlQueryModel, QSqlQuery, QSqlDatabase, QSqlError
from PyQt5.QtCore import QVariant
from ext.Horses import ShowHorse
from ext.APM import Cdatabase, DataError, TableViewAndModel
import pymysql
import sys

class PickerWidget(QGroupBox):

    increase = pyqtSignal()

    def __init__(self, isBreaking=False, db=None, con_string=None, parent=None):
        super().__init__(parent=None)
        self.hiddenColumns = [0, 1, 3, 4, 5, 6, 7]
        self.db = db
        self.supplierId = None
        self.parent = parent
        self.con_string = con_string
        if not self.db.isOpen():
            self.db.open()
        self.agreementid = None
        self.isBreaking = isBreaking
        self.tempDb = self.db.cloneDatabase(self.db, "Temp")
        if not self.tempDb.isOpen():
            self.tempDb.open()
        self.cnn = pymysql.connect(**self.con_string)
        self.createTables()
        self.setUI()
        #self.loadBaseTable()

    def setUI(self):
        self.setMinimumSize(600, 200)
        self.lblTest = QLabel("Test")
        lblInventory = QLabel("Available")
        lblSelected = QLabel("Selected")

        self.toolRight = QToolButton()
        self.toolRight.setIcon(QIcon(":icons8/arrows/right-arrow.png"))
        self.toolRight.setMinimumSize(100, 30)
        self.toolRight.clicked.connect(self.stockClicked)
        self.toolRight.setEnabled(False)

        self.toolLeft = QToolButton()
        self.toolLeft.setIcon(QIcon(":icons8/arrows/left-arrow.png"))
        self.toolLeft.setMinimumSize(100, 30)
        self.toolLeft.clicked.connect(self.deleteClicked)
        self.toolLeft.setEnabled(False)

        self.btnDetail = QPushButton("Show Details")
        self.btnDetail.setMinimumSize(100, 30)
        self.btnDetail.setEnabled(False)
        self.btnDetail.clicked.connect(self.showDetail)

        colorDict = {'column': (3),
                     u'\u2640': (QColor('pink'), QColor('black')),
                     u'\u2642': (QColor('lightskyblue'), QColor('black')),
                     u'\u265E': (QColor('lightgrey'), QColor('black'))}

        colDict = {0:("Id", True, True, True, None),
                   1:("RP", False, True, True, None),
                   2: ("Horse", False, False, False, None),
                   3: ("Sex", False, True, True, None),
                   4: ("Coat", False, True, False, None),
                   5: ("Age", False, True, True, None),
                   6: ("Locationid", True, True, False, None)}


        qryBase , qryChoose = self.loadBaseTable()
        self.horseView = TableViewAndModel(colDict, colorDict, (100,200), qryBase)
        self.horseView.clicked.connect(self.stockHighlighted)
        self.horseView.doubleClicked.connect(self.stockClicked)
        self.horseView.setSelectionBehavior(QTableView.SelectRows)


        self.selectView = TableViewAndModel(colDict, colorDict, (100,200),qryChoose)
        self.selectView.doubleClicked.connect(self.deleteClicked)
        self.selectView.setSelectionBehavior(QTableView.SelectRows)

        try:
            layout = QGridLayout()
            layout.addWidget(lblInventory,0,0)
            layout.addWidget(lblSelected,0,7)
            layout.addWidget(self.horseView,1,0,6,5)
            layout.addWidget(self.toolRight,2,6)
            layout.addWidget(self.toolLeft,4,6)
            layout.addWidget(self.selectView,1,7,6,5)
            layout.addWidget(self.btnDetail,5,6)
            self.setLayout(layout)
        except Exception as err:
            print(err)

    @property
    def breaking(self):
        return self.isBreaking

    @breaking.setter
    def breaking(self, isBreaking):
        qryDropStock = QSqlQuery(self.tempDb)
        qryDropStock.exec("TRUNCATE stock")

        qryDropChoose = QSqlQuery(self.tempDb)
        qryDropChoose.exec("TRUNCATE choose")

        self.isBreaking = isBreaking
        self.loadBaseTable()
        self.refreshModels()

    @pyqtSlot()
    def showDetail(self):
        qry = self.horseView.model().query()
        try:
            row = self.horseView.selectedIndexes()[0].row()
            qry.seek(row)
            detail = ShowHorse(self.db, qry.value(0))
            detail.show()
            detail.exec_()
        except IndexError as err:
            return


    @pyqtSlot()
    def stockHighlighted(self):
        self.toolLeft.setEnabled(False)
        self.toolRight.setEnabled(True)
        self.btnDetail.setEnabled(True)

    @pyqtSlot()
    def chooseHighlighted(self):
        try:
            self.toolLeft.setEnabled(True)
            self.toolRight.setEnabled(False)
            self.btnDetail.setEnabled(False)
        except Exception as err:
            print(err)

    def loadBaseTable(self):
        try:
            qryTruncate = QSqlQuery(self.tempDb)
            qryTruncate.exec("Truncate stock")
            qryTruncate.exec("Truncate choose")
            qryLoad = QSqlQuery(self.tempDb)
            qryLoad.prepare("""
                INSERT INTO stock 
                (id, rp, horse, sex, coat, age, locationid )
                SELECT h.id, h.rp, h.name,
                CASE
                    WHEN h.sexid = 1 THEN _ucs2 x'2642'
                    WHEN h.sexid = 2 THEN _ucs2 x'2640'
                    WHEN h.sexid = 3 THEN _ucs2 x'265E'
                END Sex,
                c.coat, 
                TIMESTAMPDIFF(YEAR,h.dob, CURDATE()) Age,
                h.locationid 
                FROM horses as h
                INNER JOIN coats as c
                ON h.coatid = c.id
                INNER JOIN sexes s 
                ON h.sexid = s.id
                WHERE
                h.isbroke != ?
                AND h.active
                AND h.id NOT IN (SELECT horseid FROM agreementhorses WHERE active = 1)
                AND h.locationid
                AND EXISTS (SELECT id FROM locations WHERE id = h.locationid AND (contactid = 0 OR contactid = ?))   
                ORDER BY h.sexid, h.name""")
            qryLoad.addBindValue(QVariant(self.isBreaking))
            qryLoad.addBindValue(QVariant(self.parent.comboSupplier.getHiddenData(0)))
            qryLoad.exec()
            if qryLoad.lastError().type() != 0:
                raise DataError("createTable", qryLoad.lastError().text())
            if not self.isVisible():
                qryBase = QSqlQuery(self.tempDb)
                qryBase.exec("""
                    SELECT id, rp, horse, sex, coat, age, locationid
                        FROM stock""")
                if qryBase.lastError().type() != 0:
                   raise DataError("createTable", qryBase.lastError().Text())
                qryChoose = QSqlQuery(self.tempDb)
                qryChoose.exec("""
                    SELECT id, rp, horse, sex, coat, age, locationid
                    FROM choose""")
                if qryChoose.lastError().type() != 0:
                    raise DataError("createTable", qryChoose.lastError().Text())
                return (qryBase, qryChoose)
            self.refreshModels()
        except DataError as err:
            print(err.source, err.args)
        except Exception as err:
            print(type(err).__name__, err.args)

    def createTables(self):
        try:
            qryInventory = QSqlQuery(self.tempDb)
            qryInventory.exec("""
                            CREATE TEMPORARY TABLE IF NOT EXISTS Stock(
                            id INTEGER PRIMARY KEY UNIQUE NOT NULL,
                            rp VARCHAR(5),
                            horse VARCHAR(45) NOT NULL,
                            sex VARCHAR(10) NOT NULL,
                            coat VARCHAR(50) NOT NULL,
                            age SMALLINT(5),
                            locationid SMALLINT(5))
                            """)
            if qryInventory.lastError().type() != 0:
                raise DataError("createTable", qryInventory.lastError().Text())
            qryChoose = QSqlQuery(self.tempDb)
            qryChoose.exec("""
                        CREATE TEMPORARY TABLE IF NOT EXISTS choose (
                            id INTEGER PRIMARY KEY UNIQUE NOT NULL,
                            rp VARCHAR(5),
                            horse VARCHAR(45) NOT NULL,
                            sex VARCHAR(10) NOT NULL,
                            coat VARCHAR(50) NOT NULL,
                            age SMALLint(5),
                            locationid SMALLINT(5))
                        """)
            if qryChoose.lastError().type() != 0:
                raise DataError("createTable", qryChoose.lastError().Text())
        except DataError as err:
            print(err.source, err.args)
        except Exception as err:
            print(type(err).__name__, err.args)

    def stockClicked(self):
        qry = self.horseView.model().query()
        qryTrans = QSqlQuery(self.tempDb)
        qryTrans.prepare("""INSERT INTO choose (id, rp, horse, sex, coat, age,  locationid) 
        VALUES (?, ?, ?, ?, ?, ?, ?)""")
        qryTrans.addBindValue(QVariant(qry.value(0)))
        qryTrans.addBindValue(QVariant(qry.value(1)))
        qryTrans.addBindValue(QVariant(qry.value(2)))
        qryTrans.addBindValue(QVariant(qry.value(3)))
        qryTrans.addBindValue(QVariant(qry.value(4)))
        qryTrans.addBindValue(QVariant(qry.value(5)))
        qryTrans.addBindValue(QVariant(qry.value(6)))
        qryTrans.exec_()
        if qryTrans.lastError().type() !=0:
            raise DataError('stockClicked', qryTrans.lastError().text())
        self.refreshModels()
        self.increase.emit()


    def deleteClicked(self):
        qry = self.selectView.model().query()
        qryDelete = QSqlQuery(self.tempDb)
        qryDelete.prepare("""
                    DELETE  FROM choose 
                    WHERE id = ?;""")
        qryDelete.addBindValue(QVariant(qry.value(0)))
        qryDelete.exec_()
        self.refreshModels()
        self.increase.emit()

    def refreshModels(self):
        qryStock = QSqlQuery(self.tempDb)
        qryStock.exec_ ("""
                            SELECT id, rp, horse, sex, coat, age, locationid
                            FROM  stock 
                            WHERE id NOT IN (SELECT id FROM choose) 
                            ;""")
        self.horseView.model().setQuery(qryStock)

        qryChoose = QSqlQuery(self.tempDb)
        qryChoose.exec_("""
                            SELECT id, rp, horse, sex, coat, age, locationid
                            FROM choose ;""")
        self.selectView.model().setQuery(qryChoose)

    @property
    def agreement(self):
        return self.agreementid

    @agreement.setter
    def agreement(self, agreement):
        self.agreementid = agreement

    @property
    def agreementHorses(self):
        qry = self.selectView.model().query()
        lst = []
        qry.seek(-1)
        while qry.next():
            lst.append((qry.value(0), qry.value(6)))
        return lst

    def saveAgreementHorses(self,agreementId):
        if agreementId is None:
            QMessageBox.Warning(self, 'Agreement not saved','Need to save the agreement",'
                                                            'Must save the agreement before saving the agreement horses')
            return
        try:
            with Cdatabase(self.db, 'InsertDB') as insertDB:
                qry = self.selectView.model().query()
                qry.seek(-1)
                qryInsert = QSqlQuery(insertDB)
                qryInsert.prepare("""
                    INSERT INTO agreementhorses (
                    agreementid, horseid)
                    VALUES ( ?, ? )""")
                while qry.next():
                    qryInsert.addBindValue(QVariant(agreementId))
                    qryInsert.addBindValue(QVariant(qry.value(0)))
                    qryInsert.exec()
        except Exception as err:
            print(type(err).__name__, err.args)

    def querySize(self):
        return self.selectView.model().query().size()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    lst = PickerWidget()
    lst.show()
    lst.agreementHorsesSave(0)
    app.exec_()
    sys.exit(app.exec_())


