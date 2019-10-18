import sys
import os
from PyQt5.QtWidgets import ( QDialog, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel, QLineEdit, QPlainTextEdit,
                             QPushButton, QTableView, QMessageBox, QCheckBox,
                              QHeaderView, QAbstractItemView)
from PyQt5.QtCore import Qt, QSettings, pyqtSlot, QVariant
from PyQt5.QtGui import QStandardItemModel, QColor
from PyQt5.QtSql import QSqlQuery, QSqlQueryModel, QSqlDriver
from ext.socketclient import RequestHandler
from ext import APM
from ext.CQSqlDatabase import Cdatabase
from ext.APM import QSqlAlignColorQueryModel, TableViewAndModel
from configparser import ConfigParser

class QSqlAlignQueryModel(QSqlQueryModel):
    def __init__(self, mode=APM.CONTACT_ALL):
        super().__init__()
        self.type = mode

    def data(self,idx, role=Qt.DisplayRole):
        try:
            if not idx.isValid() or \
                not(0<=idx.row() < self.query().size()):
                return QVariant()
            if self.query().seek(idx.row()):
                contact = self.query().record()
                if self.type == APM.CONTACT_ALL:
                    if role == Qt.DisplayRole:
                        return QVariant(contact.value(idx.column()))
                    elif role == Qt.TextAlignmentRole:
                        if idx.column() == 1:
                            return QVariant(Qt.AlignLeft)
                        else:
                            return QVariant(Qt.AlignCenter)
                    elif role == Qt.TextColorRole:
                        if contact.value(2):
                            return QVariant(QColor(Qt.white))
                        elif contact.value(3):
                            return QVariant(QColor(Qt.red))
                        elif contact.value(4):
                            return QVariant(QColor(Qt.darkBlue))
                        elif contact.value(5):
                            return QVariant(QColor(Qt.black))
                        elif contact.value(6):
                            return QVariant(QColor(Qt.white))
                    elif role == Qt.BackgroundColorRole:
                        if contact.value(2):
                            return QVariant(QColor(Qt.red))
                        elif contact.value(3):
                            return QVariant(QColor(Qt.yellow))
                        elif contact.value(4):
                            return QVariant(QColor(Qt.white))
                        elif contact.value(5):
                            return QVariant(QColor(Qt.green))
                        elif contact.value(6):
                            return QVariant(QColor(Qt.black))
                else:
                    if role == Qt.DisplayRole:
                        return QVariant(contact.value(idx.column()))
                    elif role == Qt.TextAlignmentRole:
                        if idx.column() == 1:
                            return QVariant(Qt.AlignLeft)
                        else:
                            return QVariant(Qt.AlignCenter)
                    elif role == Qt.TextColorRole:
                        if contact.value(7):
                            return QVariant(QColor(Qt.darkBlue))
                        else:
                            return QVariant(QColor(Qt.white))
                    elif role == Qt.BackgroundColorRole:
                        if contact.value(7):
                            return QVariant(QColor(Qt.white))
                        else:
                            return QVariant(QColor(Qt.black))
        except Exception as err:
            print(type(err).__name__, err.args)

class Contacts(QDialog):

    def __init__(self, db, fullname=None, mode=APM.OPEN_NEW, contactid = None, parent=None):
        super().__init__()
        self.parent = parent
        self.db = db
        self.fullname = fullname
        self.contactid = contactid
        self.setModal(True)
        self.mode = mode
        self.setUI()

    def setUI(self):
        self.setMinimumWidth(600)
        lblName = QLabel("Fullname")
        self.lineName = QLineEdit()
        self.lineName.setToolTip("Lastname, Firstname")
        self.lineName.editingFinished.connect(self.checkFullname)

        lblAddress = QLabel('Address:')
        self.textAddress = QPlainTextEdit()
        self.textAddress.setToolTip("Contact Address")
        self.textAddress.setTabStopWidth(33)

        lblPhone = QLabel('Telephone')
        self.linePhone = QLineEdit()
        self.linePhone.setToolTip("Contact telephone")
        self.linePhone.setMaximumWidth(250)
        self.linePhone.editingFinished.connect(self.enableSave)

        lblEmail = QLabel('Email')
        self.lineEmail = QLineEdit()
        self.lineEmail.setToolTip("Contact Email address")
        self.lineEmail.setMaximumWidth(250)
        self.lineEmail.editingFinished.connect(self.enableSave)

        self.checkPlayer = QCheckBox("Polo Seller")
        self.checkPlayer.setToolTip("Horse maker and seller")
        self.checkPlayer.stateChanged.connect(self.enableSave)

        self.checkBreaker = QCheckBox("Horse Breaker")
        self.checkBreaker.setToolTip("Horse Breaker")
        self.checkBreaker.stateChanged.connect(self.enableSave)

        self.checkBuyer = QCheckBox("Horse Buyer")
        self.checkBuyer.setToolTip("Horse Buyer")
        self.checkBuyer.stateChanged.connect(self.enableSave)

        self.checkDealer = QCheckBox("Horse Dealer")
        self.checkDealer.setToolTip("Horses' Sale Dealer")
        self.checkDealer.stateChanged.connect(self.enableSave)

        self.checkResponsible = QCheckBox("Manager")
        self.checkResponsible.setToolTip("Farm Responsible")
        self.checkResponsible.stateChanged.connect(self.enableSave)

        self.checkActualBreaker = QCheckBox("Buster")
        self.checkActualBreaker.setToolTip("Actual BHorse Buster")
        self.checkActualBreaker.stateChanged.connect(self.enableSave)

        self.checkActualPlayer = QCheckBox("Player")
        self.checkActualPlayer.setToolTip("Actual Polo Player")
        self.checkActualPlayer.stateChanged.connect(self.enableSave)

        self.checkVeterinary = QCheckBox('Veterinary')
        self.checkVeterinary.setToolTip('Acting Veterinary')
        self.checkVeterinary.stateChanged.connect(self.enableSave)

        self.checkActive = QCheckBox("Active")
        self.checkActive.setToolTip("Weather the contact is active")
        self.checkActive.setChecked(True)
        self.checkActive.stateChanged.connect(self.enableSave)

        self.pushSave = QPushButton("Save")
        self.pushSave.setMaximumWidth(60)
        self.pushSave.setEnabled(False)
        self.pushSave.clicked.connect(self.saveAndClose)

        pushCancel = QPushButton("Cancel")
        pushCancel.setMaximumWidth(60)
        pushCancel.clicked.connect(self.close)
        pushCancel.setFocus()

        hLayoutTop = QHBoxLayout()
        hLayoutTop.addWidget(lblName)
        hLayoutTop.addWidget(self.lineName)

        gLayoutAddress = QGridLayout()
        gLayoutAddress.addWidget(lblAddress, 0, 0)
        gLayoutAddress.addWidget(self.textAddress, 0, 1, 2, 2)
        gLayoutAddress.addWidget(lblPhone, 0,3)
        gLayoutAddress.addWidget(self.linePhone, 0, 4)
        gLayoutAddress.addWidget(lblEmail,1,3)
        gLayoutAddress.addWidget(self.lineEmail, 1,4)
        #gLayoutAddress.addWidget(self.checkActive,2,2)

        hLayoutType = QHBoxLayout()
        hLayoutType.addSpacing(100)
        hLayoutType.addWidget(self.checkPlayer)
        hLayoutType.addWidget(self.checkBreaker)

        hLayoutActual = QHBoxLayout()
        hLayoutActual.addSpacing(100)
        hLayoutActual.addWidget(self.checkActualPlayer)
        hLayoutActual.addWidget(self.checkActualBreaker)

        hLayoutSale = QHBoxLayout()
        hLayoutSale.addSpacing(100)
        hLayoutSale.addWidget(self.checkBuyer)
        hLayoutSale.addWidget(self.checkDealer)

        hLayoutBottom = QHBoxLayout()
        hLayoutBottom.addSpacing(100)
        hLayoutBottom.addWidget(self.checkResponsible)
        hLayoutBottom.addWidget(self.checkVeterinary)
        hLayoutBottom.addWidget(self.checkActive)

        hLayoutButtons = QHBoxLayout()
        hLayoutButtons.addSpacing(400)
        hLayoutButtons.addWidget(pushCancel)
        hLayoutButtons.addWidget(self.pushSave)

        vLayout = QVBoxLayout()
        vLayout.addLayout(hLayoutTop)
        vLayout.addLayout(gLayoutAddress)
        vLayout.addLayout(hLayoutType)
        vLayout.addLayout(hLayoutActual)
        vLayout.addLayout(hLayoutSale)
        vLayout.addLayout(hLayoutBottom)
        vLayout.addSpacing(20)
        if self.mode == APM.OPEN_EDIT:
            try:
                self.setMinimumWidth(850)
                colDict = {
                    0: ("ID", True, True, True, None),
                    1: ("Contact", False, False, False, None),
                    2: ("Play", False, True, True, None),
                    3: ("Break", False, True, True, None),
                    4: ("Player", False, True, True, None),
                    5: ("Buster", False, True, True, None),
                    6: ("Checker", False, True, True, None),
                    7: ("Buyer", False, True, True, None),
                    8: ("Dealer", False, True, True, None),
                    9: ("Veterinay", False, True, True, None),
                    10: ("Active", True, True, True, None),
                    11: ("Address", True, True, False, None),
                    12: ("Telephone", True, True, False, None),
                    13: ("EMail", True, True, False, None)}
                colorDict = {
                }
                qry = self.getContactsQuery()
                self.tableContacts = TableViewAndModel(colDict, colorDict,(500, 100),qry)
                self.tableContacts.verticalHeader().setVisible(False)
                self.tableContacts.doubleClicked.connect(self.getContactData)
                hLayoutButtons.insertStretch(0,5)
                vLayout.addWidget(self.tableContacts)
            except APM.DataError as err:
                print(type(err).__name__, err.args)
                res = QMessageBox.warning(self, err.args[0],err.args[1])
                sys.exit()
            except Exception as err:
                print(type(err).__name__, err.args)
        elif self.mode == APM.OPEN_EDIT_ONE:
            self.loadContact()
        vLayout.addLayout(hLayoutButtons)

        self.setLayout(vLayout)
        self.setWindowTitle("New Contact" if self.mode == APM.OPEN_NEW else "Edit Contact:")
        self.tableContacts.setFocus() if self.mode == APM.OPEN_EDIT else self.lineName.setFocus()

    @pyqtSlot()
    def getContactData(self):
        row = self.tableContacts.currentIndex().row()
        self.tableContacts.model().query().seek(row)
        record = self.tableContacts.model().query().record()
        try:
            res = QMessageBox.question(self,"Edit Contact", "Do you want to edit {}´data.\n Check data and edit it "
                                            " as necessary".format(record.value(1)))
            if res != QMessageBox.Yes:
                self.contactid = None
                self.lineName.clear()
                self.checkPlayer.setChecked(False)
                self.checkBreaker.setChecked(False)
                self.checkResponsible.setChecked(False)
                self.checkBuyer.setChecked(False)
                self.checkDealer.setChecked(False)
                self.checkVeterinary.setCheck(False)
                self.checkActive.setChecked(True)
                self.pushSave.setEnabled(False)
                self.setWindowTitle("Edit Contact:")

                return
            self.setWindowTitle("Edit Contact: {}".format(record.value(1)))
            self.contactid = record.value(0)
            self.lineName.setText(record.value(1))
            self.checkPlayer.setChecked(True if record.value(2) == u'\u2714' else False)
            self.checkBreaker.setChecked(True if record.value(3) == u'\u2714' else False)
            self.checkActualBreaker.setChecked(True if record.value(4) == u'\u2714' else False)
            self.checkActualPlayer.setChecked(True if record.value(5)== u'\u2714' else False)
            self.checkResponsible.setChecked(True if record.value(6) == u'\u2714' else False)
            self.checkBuyer.setChecked(True if record.value(7) == u'\u2714' else False)
            self.checkDealer.setChecked(True if record.value(8) == u'\u2714' else False)
            self.checkVeterinary.setChecked(True if record.value(9) == u'\u2714' else False)
            self.checkActive.setChecked(True if record.value(10) == u'\u2714' else False)
            self.setWindowTitle("Edit Contact: '" + record.value(1) + "'")
            self.textAddress.setPlainText(record.value(11))
            self.linePhone.setText(record.value(12))
            self.lineEmail.setText(record.value(13))
        except Exception as err:
            print(type(err).__name__, err.args)

    def getContactsQuery(self):
        with Cdatabase(self.db, 'xdb') as xdb:
            qry = QSqlQuery(xdb)
            qry.exec("""SELECT
            id, 
            fullname, 
            If (playerseller = 1, _ucs2 X'2714', ''), 
            if(horsebreaker = 1, _ucs2 X'2714', ''), 
            if (breaker = 1, _ucs2 x'2714', ''),
            if (player = 1, _ucs2 x'2714', ''),
            if(responsible = 1, _ucs2 X'2714', ''),
            if(buyer = 1,_ucs2 X'2714', ''), 
            if(dealer = 1,_ucs2 X'2714', ''),
            if (veterinary = 1, _ucs2 x'2714', ''), 
            if(active = 1, _ucs2 X'2714', ''),
            address,
            telephone,
            email
            FROM contacts
            ORDER BY fullname""")
        return qry

    @pyqtSlot()
    def enableSave(self):
        send_object = self.sender()
        if isinstance(send_object, QPushButton):
            return
        if self.mode == APM.OPEN_EDIT and self.contactid is None:
            QMessageBox.warning(self, "Wrong Mode", "Cannot save a new contact in the edit form!", )
            self.pushSave.setEnabled(False)
            if isinstance(send_object, QLineEdit):
                send_object.clear()
                self.textAddress.clear()
            elif isinstance(send_object, QCheckBox):
                if send_object == self.checkActive:
                    self.checkActive.setChecked(True)
                else:
                    send_object.setChecked(False)
            return

        if len(self.lineName.text()) > 0 :
            self.pushSave.setEnabled(True)

    @pyqtSlot()
    def checkFullname(self):
        try:
            if len(self.lineName.text()) > 0:
                self.lineName.text().index(",")
            self.lineName.setText(self.lineName.text().title())
        except ValueError as err:
            msgBox = QMessageBox()
            msgBox.setText("The customer name '{}' isn't formatted properly".format(self.lineName.text()))
            msgBox.exec()
            #self.lineName.clear()
            self.lineName.setFocus()
            return
        if self.mode == APM.OPEN_NEW:
            qry = QSqlQuery(self.db)
            #qry = QSqlQuery(self.cdb)
            qry.prepare("""SELECT id FROM contacts 
            WHERE fullname = ?;""")
            qry.addBindValue(QVariant(self.lineName.text()))
            qry.exec_()
            if qry.size() > 0:
                QMessageBox.warning(self, "Duplicate Name","The contact '{}' already exists! Use the existing or enter a different name".format(self.lineName.text()))
                self.lineName.clear()
                return
        if self.isVisible():
            self.enableSave()

    def loadContact(self):
        qry = QSqlQuery(self.db)
        qry.prepare("""
        SELECT fullname, playerseller, horsebreaker, buyer,
         dealer, responsible, breaker, player, veterinary, active FROM contacts 
         WHERE id = ?""")
        qry.addBindValue(QVariant(self.contactid))
        try:
            qry.exec_()
            if qry.size() == -1:
                raise ValueError(qry.lastError.text())
            qry.first()
            self.lineName.setText(qry.value(0))
            self.checkPlayer.setChecked(qry.value(1))
            self.checkBreaker.setChecked(qry.value(2))
            self.checkBuyer.setChecked(qry.value(3))
            self.checkDealer.setChecked(qry.value(4))
            self.checkResponsible.setChecked(qry.value(5))
            self.checkActualBreaker.seChecked(qry.value(6))
            self.checkActualPlayer.setChecked(qry.value(7))
            self.checkVeterinary.setChecked(qry.value(8))
            self.checkActive.setChecked(qry.value(9))
        except ValueError as err:
            print(type(err).__name__, err.argv)
            return
        except Exception as err:
            print(type(err).__name__, err.argv)
            return
        return

    @pyqtSlot()
    def saveAndClose(self):
        qry = QSqlQuery(self.db)
        if self.mode == APM.OPEN_NEW:
            qry.prepare("""
            INSERT INTO contacts
            (fullname,
            address,
            telephone,
            email,
            playerseller,
            horsebreaker,
            buyer,
            dealer,
            responsible,
            breaker,
            player,
            veterinary,
            active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""")
        else:
            qry.prepare("""
            UPDATE contacts 
            SET fullname = ?,
            address = ?,
            telephone = ?,
            email = ?,
            playerseller = ?, 
            horsebreaker = ?, 
            buyer = ?, 
            dealer = ?, 
            responsible = ?,
            breaker = ?,
            player = ?,
            veterinary = ?, 
            active = ? 
            WHERE id = ?""")
        qry.addBindValue(QVariant(self.lineName.text()))
        qry.addBindValue(QVariant(self.textAddress.toPlainText()))
        qry.addBindValue(QVariant(self.linePhone.text()))
        qry.addBindValue(QVariant(self.lineEmail.text()))
        qry.addBindValue(QVariant(self.checkPlayer.isChecked()))
        qry.addBindValue(QVariant(self.checkBreaker.isChecked()))
        qry.addBindValue(QVariant(self.checkBuyer.isChecked()))
        qry.addBindValue(QVariant(self.checkDealer.isChecked()))
        qry.addBindValue(QVariant(self.checkResponsible.isChecked()))
        qry.addBindValue(QVariant(self.checkActualBreaker.isChecked()))
        qry.addBindValue(QVariant(self.checkActualPlayer.isChecked()))
        qry.addBindValue(QVariant(self.checkVeterinary.isChecked()))
        qry.addBindValue(QVariant(self.checkActive.isChecked()))
        if self.mode == APM.OPEN_EDIT:
            qry.addBindValue(QVariant(self.contactid))
        try:
            qry.exec()
            if qry.numRowsAffected() != 1:
                print(qry.lastError().text())
                raise APM.DataError('SaveAndClose',qry.lastError().text())
        except APM.DataError as err:
            print(err.source, err.message)
            return
        except Exception as err:
            print('Save&close', type(err).__name__ , err.args)
            return
        self.close()

class ShowContacts(QDialog):
    def __init__(self, db, mode):
        super().__init__()
        self.sdb = Cdatabase(db, "show")
        self.type = mode
        self.initUI()
        self.setMinimumSize(600,200)

    def initUI(self):
        pushOK = QPushButton("Close")
        pushOK.setMaximumSize(50, 30)
        pushOK.clicked.connect(self.close)
        self.tableContacts = QTableView()
        self.tableContacts.verticalHeader().setVisible(False)
        self.modelContacts = QSqlAlignQueryModel(self.type)
        qry = self.getContactsQuery()
        self.modelContacts.setQuery(qry)
        self.modelContacts.setHeaderData(0, Qt.Horizontal, "ID")
        self.modelContacts.setHeaderData(1, Qt.Horizontal, "Name")
        self.modelContacts.setHeaderData(2, Qt.Horizontal, "Player")
        self.modelContacts.setHeaderData(3, Qt.Horizontal, 'Breaker')
        self.modelContacts.setHeaderData(4, Qt.Horizontal, "Manager")
        self.modelContacts.setHeaderData(5, Qt.Horizontal, 'Buyer')
        self.modelContacts.setHeaderData(6, Qt.Horizontal, 'Dealer')
        self.modelContacts.setHeaderData(7, Qt.Horizontal, 'Active')
        self.tableContacts.setModel(self.modelContacts)
        self.tableContacts.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tableContacts.setStyleSheet("QTableView {font-size: 8pt;}")
        header = self.tableContacts.horizontalHeader()
        header.setStyleSheet("QHeaderView {font-size: 8pt;}")
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.tableContacts.setRowHeight(0, 10)
        self.tableContacts.verticalHeader().setDefaultSectionSize(self.tableContacts.rowHeight(0))
        self.tableContacts.setColumnWidth(0, 50)
        self.tableContacts.setColumnWidth(1, 100)
        self.tableContacts.hideColumn(0)
        #self.tableContacts.clicked.connect(self.getContactData)
        layout = QVBoxLayout()
        hLayout = QHBoxLayout()
        hLayout.addSpacing(500)
        hLayout.addWidget(pushOK)
        layout.addWidget(self.tableContacts)
        layout.addLayout(hLayout)

        self.setLayout(layout)



    def getContactsQuery(self):
        qry = QSqlQuery(self.sdb)
        select = """SELECT
                 id, 
                 fullname, 
                 IF (playerseller = 1, _ucs2 X'2714', ''), 
                 if(horsebreaker = 1, _ucs2 X'2714', ''), 
                 if(responsible = 1, _ucs2 X'2714', ''),
                 if(buyer = 1,_ucs2 X'2714', ''), 
                 if(dealer = 1,_ucs2 X'2714', ''), 
                 if(active = 1, _ucs2 X'2714', '')
                 FROM contacts """
        if self.type == APM.CONTACT_BUYER:
            where = "WHERE buyer "
            self.setWindowTitle("Horse Buyers")
        elif self.type == APM.CONTACT_DEALER:
            where = "WHERE dealer "
            self.setWindowTitle("Horse Dealers")
        elif self.type == APM.CONTACT_BREAKER:
            where = "WHERE horsebreaker "
            self.setWindowTitle("Horse Breakers")
        elif self.type == APM.CONTACT_RESPONSIBLE:
            where = "WHERE responsible "
            self.setWindowTitle("Authorized Representative")
        elif self.type == APM.CONTACT_PLAYER:
            where = "WHERE playerseller "
            self.setWindowTitle("Polo Player Sellers")
        qry.prepare(select + where + "ORDER BY fullname")
        qry.exec()
        return qry






