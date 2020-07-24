from PyQt5.QtWidgets import (QWidget, QPushButton, QHBoxLayout, QVBoxLayout, QTableView,
                             QGridLayout, QApplication, QToolButton, QLabel, QGroupBox, QDialog)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QSettings, QAbstractTableModel, QModelIndex, QVariant, pyqtSlot, QJsonDocument
from PyQt5.QtSql import (QSqlQueryModel, QSqlDatabase,
                         QSqlTableModel, QSqlQuery)
from ext.Contacts import Contacts
from ext.BrokeReceive import ReceiveBroken
from ext.MySQLConnector import MySQLConnector
from ext.ListPicker import PickerWidget
import sys
from ext.HorseReports import AvailableHorses
import PoloResource


class MyModel(QSqlQueryModel):
    def __init__(self):
        super().__init__()

    def data(self,idx, role=Qt.DisplayRole):
        try:
            if not idx.isValid() or \
                not(0<=idx.row() < self.query().size()):
                return QVariant()
            if self.query().seek(idx.row()):
                contact = self.query().record()
                if role == Qt.DisplayRole:
                    print(idx.column())

                    return QVariant(contact.value(idx.column()))

                if role == Qt.TextAlignmentRole:
            #    return QVariant()
                    return QVariant(Qt.AlignCenter)
        except Exception as err:
            print(type(err).__name__, err.args)


class Test(QDialog):

    def __init__(self):
        try:
            super().__init__()
            self.db = None
            self.setWindowTitle('Test Widget')
            ok, self.db = self.connectDB()
            self.checkModel()
            self.table = QTableView()
            self.table.setModel(self.model)
            self.table.doubleClicked.connect(self.testWidget)
            btnTest = QPushButton('Test')
            btnTest.clicked.connect(self.testWidget)
            btnTest.setMaximumSize(50,50)
            btnTest.setIcon(QIcon(":/Icons8/transport.png"))
            layout = QVBoxLayout()
            layout.addWidget(self.table)
            layout.addWidget(btnTest)
            self.setLayout(layout)
            if not ok:
                raise Exception("DB not opened")

        except Exception as err:
            print(err)


    def lookValue(self):
        row = self.table.currentIndex().row()
        record = self.model.record(row)
        print(record.value(1))

    def checkModel(self):
        qry = QSqlQuery(self.db)
        qry.exec("SELECT id, fullname, playerseller FROM contacts")
        self.model = MyModel()
        self.model.setQuery(qry)

    @pyqtSlot()
    def testWidget(self):
        settings = QSettings(":ext/config.ini", QSettings.IniFormat)
        host = settings.value("mysql/host")
        database = settings.value("mysql/Database")
        user = settings.value("mysql/user")
        password = settings.value("mysql/password")
        con_dict = {'user': user, 'host': host, 'database': database, 'password': password}

        h = ReceiveBroke(self.db, con_dict)
        h.show()
        h.exec_()

    def connectDB(self):

        sett = QSettings("ext/config.ini", QSettings.IniFormat)
        db = QSqlDatabase.addDatabase("QMYSQL3")
        db.setHostName(sett.value("mysql/host"))
        db.setDatabaseName(sett.value("mysql/database"))
        db.setUserName(sett.value("mysql/user"))
        db.setPassword(sett.value("mysql/password"))
        if db.open():
            return True, db
        return False, None

if __name__ == '__main__':
    app = QApplication(sys.argv)
    tst = Test()
    tst.show()
    app.exec()





