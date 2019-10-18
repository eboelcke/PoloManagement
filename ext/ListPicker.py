from PyQt5.QtWidgets import (QPushButton, QTableView,QMessageBox,
                             QGridLayout, QApplication, QToolButton, QLabel, QGroupBox)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt5.QtSql import QSqlQueryModel, QSqlQuery, QSqlDatabase, QSqlError
from PyQt5.QtCore import QVariant
from ext.Horses import ShowHorse
from ext.CQSqlDatabase import Cdatabase
import sys

class PickerWidget(QGroupBox):

    increase = pyqtSignal()

    def __init__(self, isBreaking=False, db = None, parent=None):
        super().__init__(parent=None)
        self.hiddenColumns = [0, 1, 3, 4, 5, 6, 7]
        self.db = db
        self.agreementid = None
        try:
            self.isBreaking = isBreaking
        except Exception as err:
            print(type(err).__name__, err.args)
        self.setUI()
        self.parent = parent
        self.SQliteDB = self.openSQLite()
        try:
            self.createTables()
        except Exception as err:
            print(err)
        self.loadBaseTable()

    def setUI(self):
        #if not self.db.isOpen():
        #
        self.setMinimumSize(600, 200)
        self.lblTest = QLabel("Test")
        lblInventory = QLabel("Available")
        lblSelected = QLabel("Selected")
        self.toolRight = QToolButton()
        self.toolRight.setIcon(QIcon(":icons8/arrows/right-arrow.png"))
        self.toolRight.setMaximumSize(100, 30)
        self.toolRight.setMinimumWidth(100)
        self.toolRight.clicked.connect(self.stockClicked)
        self.toolRight.setEnabled(False)

        self.toolLeft = QToolButton()
        self.toolLeft.setIcon(QIcon(":icons8/arrows/left-arrow.png"))
        self.toolLeft.setMaximumSize(100, 30)
        self.toolLeft.setMinimumWidth(80)
        self.toolLeft.clicked.connect(self.deleteClicked)
        self.toolLeft.setEnabled(False)

        self.btnDetail = QPushButton("Show Details")
        self.btnDetail.setMinimumSize(100, 30)
        self.btnDetail.setEnabled(False)
        self.btnDetail.clicked.connect(self.showDetail)

        self.horseView = QTableView()
        self.horseView.setMinimumWidth(200)
        self.horseView.verticalHeader().setVisible(False)
        self.horseView.verticalHeader().setDefaultSectionSize(24)
        self.horseView.horizontalHeader().setVisible(False)
        self.horseView.verticalHeader().setVisible(False)
        self.horseView.clicked.connect(self.stockHighlighted)
        self.horseView.doubleClicked.connect(self.stockClicked)
        self.horseView.setSelectionBehavior(QTableView.SelectRows)


        self.selectView = QTableView()
        self.selectView.setMaximumWidth(180)
        self.selectView.verticalHeader().setVisible(False)
        self.selectView.verticalHeader().setDefaultSectionSize(24)
        self.selectView.horizontalHeader().setVisible(False)
        self.selectView.verticalHeader().setVisible(False)
        self.selectView.doubleClicked.connect(self.deleteClicked)
        self.selectView.setSelectionBehavior(QTableView.SelectRows)

        try:
            layout = QGridLayout()
            layout.addWidget(lblInventory,0,0)
            layout.addWidget(lblSelected,0,3)
            layout.addWidget(self.horseView,1,0,5,2)
            layout.addWidget(self.toolRight,2,2)
            layout.addWidget(self.toolLeft,4,2)
            layout.addWidget(self.selectView,1,3,5,2)
            layout.addWidget(self.btnDetail,5,2)
            self.setLayout(layout)
        except Exception as err:
            print(err)

    @property
    def liteDB(self):
        return self.SQliteDB

    @property
    def breaking(self):
        return self.isBreaking

    @breaking.setter
    def breaking(self, isBreaking):
        qryDropStock = QSqlQuery(self.SQliteDB)
        qryDropStock.prepare("DROP TABLE stock")
        qryDropStock.exec_()

        qryDropChoose = QSqlQuery(self.SQliteDB)
        qryDropChoose.prepare("DROP TABLE choose")
        qryDropChoose.exec_()

        qryDropAllHorses = QSqlQuery(self.SQliteDB)
        qryDropAllHorses.prepare("DROP TABLE allhorses")
        qryDropAllHorses.exec_()
        self.isBreaking = isBreaking
        self.createTables()
        self.loadBaseTable()

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
        qry = QSqlQuery()
        qry.prepare("""
        SELECT h.id, h.rp, h.name,
         s.sex, c.coat, h.dob, h.sexid, h.coatid 
        FROM horses as h
        INNER JOIN sexes as s
        ON h.sexid = s.id
        INNER JOIN coats as c
        ON h.coatid = c.id
        WHERE
         h.isbroke != ?
         AND h.active
         AND h.id NOT IN (SELECT horseid FROM agreementhorses WHERE active = 1)   
         ORDER BY h.sexid, h.name""")
        qry.addBindValue(QVariant(self.isBreaking))
        qry.exec_()
        print(qry.isActive())
        qryInsert = QSqlQuery(self.SQliteDB)
        qry.seek(-1)
        while qry.next():
            try:
                qryInsert.prepare("""INSERT INTO STOCK 
                              (id, rp, name, sex, coat, dob, sexid, coatid) 
                              VALUES(?, ?, ?, ?, ?, ?, ?, ?)""")
                qryInsert.addBindValue(QVariant(qry.value(0)))
                qryInsert.addBindValue(QVariant(qry.value(1)))
                qryInsert.addBindValue(QVariant(qry.value(2)))
                qryInsert.addBindValue(QVariant(qry.value(3)))
                qryInsert.addBindValue(QVariant(qry.value(4)))
                qryInsert.addBindValue(QVariant(qry.value(5)))
                qryInsert.addBindValue(QVariant(qry.value(6)))
                qryInsert.addBindValue(QVariant(qry.value(7)))
                qryInsert.exec_()
                if not qryInsert.lastError().type != 0:
                    raise Exception(qryInsert.lastError().text())
            except Exception as err:
                print(type(err).__name__, err.args)
        qry.finish()
        qryRetrive = QSqlQuery(self.SQliteDB)
        qryRetrive.prepare("""
                            SELECT id, rp, name, sex, coat, dob, sexid, coatid 
                            FROM stock""")
        qryRetrive.exec_()
        qryAllHorses = QSqlQuery(self.SQliteDB)
        qryAllHorses.prepare("CREATE TABLE allhorses AS SELECT * FROM Stock ")
        qryAllHorses.exec_()

        model = QSqlQueryModel()
        model.setQuery(qryRetrive)
        self.horseView.setModel(model)
        [self.horseView.setColumnHidden(x, True) for x in self.hiddenColumns]
        self.horseView.setColumnWidth(0, 1)
        self.horseView.setColumnWidth(2, 170)
        self.horseView.setMaximumWidth(180)
        #self.horseView.clicked.connect(self.stockHighlighted)

        qryChoose = QSqlQuery(self.SQliteDB)
        qryChoose.exec_("SELECT id, rp, name FROM choose")

        chooseModel = QSqlQueryModel()
        chooseModel.setQuery(qryChoose)
        self.selectView.setModel(chooseModel)
        self.selectView.clicked.connect(self.chooseHighlighted)

    def openSQLite(self):
        SQLiteDB = QSqlDatabase.addDatabase("QSQLITE", "sqlite")
        SQLiteDB.setDatabaseName(":memory:")
        ok = SQLiteDB.open()
        if ok:
            return SQLiteDB

    def createTables(self):
        try:
            self.SQliteDB.transaction()
            qryInventory = QSqlQuery(self.SQliteDB)
            qryInventory.prepare("""
                            CREATE TABLE IF NOT EXISTS Stock(
                            id INTEGER PRIMARY KEY UNIQUE NOT NULL,
                            rp VARCHAR(5),
                            name VARCHAR(45) NOT NULL,
                            sex VARCHAR(50) NOT NULL,
                            coat VARCHAR(50) NOT NULL,
                            dob DATETIME,
                            sexid TINYINT(1) NOT NULL,
                            coatid TINYINT(1) NOT NULL)
                            """)
            qryInventory.exec_()
            qrychoose = QSqlQuery(self.SQliteDB)
            qrychoose.prepare("""
                        CREATE TABLE IF NOT EXISTS choose (
                        id INTEGER PRIMARY KEY UNIQUE NOT NULL,
                        rp VARCHAR(5),
                        name VARCHAR(45) NOT NULL)
                        """)
            qrychoose.exec_()
            self.SQliteDB.commit()
        except QSqlError as err:
            self.SQliteDB.rollback()
            print("SQlError", err.text())
        except Exception as err:
            print(type(err).__name__, err.args)
            self.SQliteDB.rollback()



    def stockClicked(self):
        qry = self.horseView.model().query()
        id = qry.value(0)
        rp = qry.value(1)
        name = qry.value(2)
        qryTrans = QSqlQuery(self.SQliteDB)
        qryTrans.prepare("INSERT INTO choose (id, rp, name) VALUES (?, ?, ?)")
        qryTrans.addBindValue(QVariant(id))
        qryTrans.addBindValue(QVariant(rp))
        qryTrans.addBindValue(QVariant(name))
        qryTrans.exec_()
        print(qryTrans.numRowsAffected())
        print(qryTrans.lastError().text())
        self.refreshModels()
        self.increase.emit()


    def deleteClicked(self):
        qry = self.selectView.model().query()
        id = qry.value(0)
        qryDelete = QSqlQuery(self.SQliteDB)
        qryDelete.prepare("""
                    DELETE  FROM choose 
                    WHERE id = ?;""")
        qryDelete.addBindValue(QVariant(id))
        qryDelete.exec_()
        print(qryDelete.numRowsAffected())
        self.refreshModels()
        self.increase.emit()

    def refreshModels(self):
        qryStock = QSqlQuery(self.SQliteDB)
        qryStock.exec_ ("""
                            SELECT a.id, a.rp, a.name, a.sex, a.coat, a.dob,  a.sexid, a.coatid
                            FROM  allhorses AS A
                            WHERE id NOT IN (SELECT c.id FROM choose AS c) 
                            ;""")


        modelStock = QSqlQueryModel()
        modelStock.setQuery(qryStock)
        self.horseView.setModel(modelStock)

        qryChoose = QSqlQuery(self.SQliteDB)
        qryChoose.exec_("""
                            SELECT id, rp, name
                            FROM choose ;""")
        modelChoose = QSqlQueryModel()
        modelChoose.setQuery(qryChoose)
        self.selectView.setModel(modelChoose)
        self.selectView.setMaximumWidth(300)
        self.selectView.setColumnWidth(2,170)
        [self.selectView.hideColumn(x) for x in [0,1]]
        self.selectView.setMaximumWidth(180)

    @property
    def sqliteQuerySize(self):
        qry = self.selectView.model().query()
        rows = 0
        qry.seek(-1)
        while qry.next():
            rows += 1
        return rows

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
            lst.append(qry.value(0))
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





if __name__ == '__main__':
    app = QApplication(sys.argv)
    lst = PickerWidget()
    lst.show()
    lst.agreementHorsesSave(0)
    app.exec_()
    sys.exit(app.exec_())


