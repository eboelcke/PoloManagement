
from PyQt5.QtSql import QSqlDatabase
from ext.APM import DataError


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
