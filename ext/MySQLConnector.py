import pymysql
from pymysql import connections



class MySQLConnector:
    def __init__(self, con_dict):
        #super().__init__()
        self.cnx = None
        self.con_dict = con_dict

    def __enter__(self):
        #self.cnx = super().connect(host='SERVER', user='erick', database='agreements', password='tuppence')
        #self.cnx = self.connect(**self.con_dict)
        self.cnx = pymysql.connect(**self.con_dict)

        return self.cnx

    def __exit__(self):
        self.cnx.close()

