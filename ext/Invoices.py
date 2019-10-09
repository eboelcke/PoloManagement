import sys
import os
from PyQt5.QtWidgets import (QDialog, QMessageBox, QFrame, QApplication, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QLineEdit,QTextEdit, QComboBox, QDateEdit, QSpinBox)
from PyQt5.QtSql import QSqlQuery, QSqlQueryModel
from ext.CQSqlDatabase import Cdatabase


from PyQt5.QtCore import Qt, QDate
from PyQt5.QtSql import QSqlDatabase, QSqlQueryModel, QSqlQuery
from ext.CQSqlDatabase import Cdatabase

class Invoice(QDialog):
    def __init__(self, qdb, mode='New', invoiceid=None):
        super().__init__()
        if qdb is not None:
            self.db = qdb
        self.invoiceId = invoiceid
        self.mode = mode
        self.setUI()
        self.loadSuppliers()

    def setUI(self):
        self.setWindowTitle("Invoice")
        invoiceFrame = QFrame()
        invoiceFrame.setMaximumWidth(1000)
        invoiceFrame.setFrameStyle(QFrame.Panel | QFrame.Plain)
        invoiceFrame.setLineWidth(2)



        lblSupplier = QLabel('Services Supplier: ')
        self.comboSupplier = QComboBox(self)
        self.comboSupplier.setMinimumWidth(300)

        lblNumber = QLabel("Number: ")
        lineNumber = QLineEdit()
        lineNumber.setMaximumWidth(100)
        lblTotal = QLabel('Total Amount')
        lineTotal = QLineEdit()
        lineTotal.setAlignment(Qt.AlignRight)
        lineTotal.setMinimumWidth(150)
        lblDate = QLabel('Date: ')
        dateInvoice = QDateEdit()
        dateInvoice.setCalendarPopup(True)
        dateInvoice.setDate(QDate.currentDate())
        dateInvoice.setDisplayFormat('yyyy-MM-dd')
        dateInvoice.setMinimumWidth(120)
        lblPesosAmount = QLabel('Pesos Argentinos:')
        lblNotes = QLabel('Notes')
        txtNotes = QTextEdit()
        lblType = QLabel(self.mode)
        lblType.setStyleSheet("QLabel {background-color: red; color: white;}")
        lblType.setAlignment(Qt.AlignCenter)

        invoiceVLayout = QVBoxLayout()
        invoiceLayout_1 = QHBoxLayout()
        invoiceLayout = QHBoxLayout()

        invoiceLayout_1.addWidget(lblSupplier)
        invoiceLayout_1.addWidget(self.comboSupplier)
        invoiceLayout_1.addWidget(lblType)
        invoiceLayout.addWidget(lblDate)
        invoiceLayout.addWidget(dateInvoice)
        invoiceLayout.addWidget(lblNumber)
        invoiceLayout.addWidget(lineNumber)
        invoiceLayout.addWidget(lblTotal)
        invoiceLayout.addWidget(lineTotal)

        invoiceVLayout.addLayout(invoiceLayout_1)
        invoiceVLayout.addLayout(invoiceLayout)

        invoiceFrame.setLayout(invoiceVLayout)

        detailFrame = QFrame()
        detailFrame.setMinimumSize(50, 50)
        layout = QVBoxLayout()
        layout.addWidget(invoiceFrame)
        layout.addWidget(detailFrame)
        self.setLayout(layout)

    def loadSuppliers(self):
        with Cdatabase(self.db) as suppliersDb:
            qry = QSqlQuery(suppliersDb)
            qry.prepare("""
            SELECT id, 
            fullname, 
            playerseller,
            horsebreaker
            FROM contacts 
            WHERE playerseller 
            OR horsebreaker 
            ORDER BY fullname""")
            qry.exec_()
        modelSupplier = QSqlQueryModel()
        modelSupplier.setQuery(qry)
        self.comboSupplier.setModel(modelSupplier)
        self.comboSupplier.setModelColumn(1)
        return



def main():
    app = QApplication(sys.argv)
    myInvoice = Invoice()
    myInvoice.show()
    app.exec()

if __name__ == '__main__':
    main()