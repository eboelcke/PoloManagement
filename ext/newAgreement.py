import sys
from PyQt5.QtWidgets import (QDialog, QLabel, QLineEdit, QPushButton, QCheckBox, QTextEdit,
                             QHBoxLayout, QGridLayout, QCalendarWidget,
                             QDateEdit, QApplication, QVBoxLayout, QGroupBox, QRadioButton, QSpinBox,
                             QFormLayout, QMessageBox, QButtonGroup)
from PyQt5.QtCore import Qt, QDate, QEvent, pyqtSlot, QVariant
from PyQt5.QtGui import  QStandardItem, QDoubleValidator, QIntValidator, QMouseEvent
from PyQt5.QtSql import QSqlDatabase, QSqlQuery,QSqlError, QSqlQueryModel
from ext.socketclient import  RequestHandler
#from ext.SpinFocus import FocusSpin
from ext.ListPicker import PickerWidget
from ext.Contacts import Contacts
from ext import APM
from ext.APM import FocusSpin
from ext.Settings import SettingsDialog



class ComunicationError(Exception):
    pass


class Agreement(QDialog):
    """This class receives the a {connection_settings"} fromPoloAgreements and would:
    - Determine  id the supplier is in the database table 'suppliers' and if not include it.
    -Make an empty file (*.equ) in the form: [agreement title date.equ].
    - Select the horses to be included into the agreement according to the breaking option.
    - Determine if the supplier dir for the breaking | play&sale option exists and if not created
    - Save in the Agreements table the agreement parameters"""



    def __init__(self,db, address, parent=None):
        super().__init__(parent= None)
        self.parent = parent
        self.db = db
        if not self.db.isOpen():
            self.db.open()
        self.address = address
        self.setModal(True)
        self.supplierId = None
        self.responsibleId = None
        self.agreementTitle = ['', "- Play & Sale Agreement - ", QDate.currentDate().toString("MM-dd-yyyy")]
        self.okToSave = [None,
        QDate.currentDate(), None, None, None]
        self.playOkToSave = None
        self.chooseSize = None
        self.agreementId = None
        self.agreementType = 0
        self.filename = None
        self.setWindowTitle("New Play & Sale Agreement")
        self.setUi()



        #self.toggleBreaking()
        #self.radioAtEnd.setChecked(True)

    def setUi(self):
        lblAgreement = QLabel("Agreement Title")
        lblDate = QLabel("Date")
        lblSupplier   = QLabel("Supplier Name")
        lblResponsible = QLabel("Responsible")
        lblResponsible.setAlignment(Qt.AlignRight)
        lblAmount = QLabel("Maximum /Total Amount")
        lblDownPayment = QLabel("DownPayment")
        lblInstallments = QLabel("Installments")
        lblMinimunPayment = QLabel("Minimum Amount (%)")
        self.lblNotes = QLabel("Notes")
        self.lblNotes.setAlignment(Qt.AlignCenter)
        lblAgreementDetail = QLabel("Horse's Agreement Detail")
        lblAgreementDetail.setAlignment(Qt.AlignCenter)

        self.dataPlayer = None
        self.dataBreaker = None
        self.dataResponsible = None
        self.modelSupplier = None
        self.modelResponsible = None

        self.lineAgreement = QLineEdit()
        self.lineAgreement.setEnabled(False)

        self.dateEdit = QDateEdit()
        self.dateEdit.setDate(QDate.currentDate())
        self.dateEdit.setCalendarPopup(True)
        self.dateEdit.dateChanged.connect(self.changedDate)

        valAmount = QDoubleValidator(0.00, 99999.99, 2)

        self.lineInstallments = QLineEdit('0')
        self.spinInstallments = QSpinBox()
        self.spinInstallments.setRange(0, 24)
        self.spinInstallments.setMaximumWidth(50)
        self.spinInstallments.setEnabled(False)

        self.lineDownpayment = QLineEdit('0.00')
        self.lineDownpayment.setValidator(valAmount)
        self.lineDownpayment.setMaximumWidth(100)
        self.lineDownpayment.setAlignment(Qt.AlignRight)

        self.spinMinimum = QSpinBox()
        self.spinMinimum.setValue(0)
        self.spinMinimum.setRange(0, 100)
        self.spinMinimum.setMaximumWidth(50)

        self.textNotes = QTextEdit()
        self.checkBreaking = QCheckBox("Breaking")
        self.checkBreaking.setTristate(False)
        self.checkBreaking.stateChanged.connect(self.toggleBreaking)

        self.comboSupplier = APM.FocusCombo(self)
        self.comboSupplier.setMaximumSize(220,30)
        self.comboSupplier.setEditable(True)
        self.comboSupplier.activated.connect(self.supplierChange)
        self.comboSupplier.focusLost.connect(self.supplierFocusLost)
        self.comboSupplier.doubleClicked.connect(self.editContact)

        self.comboResponsible = APM.FocusCombo()
        self.comboResponsible.setEditable(True)
        self.comboResponsible.setMaximumSize(200, 25)
        self.comboResponsible.setMinimumSize(200, 25)
        self.comboResponsible.focusLost.connect(self.responsibleFocusLost)

        self.load_combos()

        btnClose = QPushButton("Cancel", self)
        btnClose.clicked.connect(self.close)
        btnClose.setMaximumSize(70, 30)

        self.btnOk = QPushButton("Save", self)
        self.btnOk.clicked.connect(self.saveNew)
        self.btnOk.setMaximumSize(70,30)
        self.btnOk.setEnabled(False)

        btnNewContact = QPushButton("New Contact")
        btnNewContact.setMaximumSize(100, 30)
        btnNewContact.clicked.connect(self.newContact)

        self.radioAtEnd = QRadioButton("On Completion")
        self.radioAtEnd.setChecked(False)
        self.radioAtEnd.toggled.connect(self.paymentOptionChanged)

        self.radioFee = QRadioButton("Monthly Installments")
        self.radioFee.setChecked(True)
        self.radioFee.toggled.connect(self.paymentOptionChanged)

        self.radioOnSite = QRadioButton("Monthly On Site Only")
        self.radioOnSite.toggled.connect(self.paymentOptionChanged)

        self.groupPayment = QGroupBox("Payment Options")
        self.groupPayment.setCheckable(False)

        self.paymentOptions = QButtonGroup()
        self.paymentOptions.addButton(self.radioFee)
        self.paymentOptions.addButton(self.radioAtEnd)
        self.paymentOptions.addButton(self.radioOnSite)
        self.paymentOptions.setId(self.radioAtEnd, 0)
        self.paymentOptions.setId(self.radioFee, 1)
        self.paymentOptions.setId(self.radioOnSite, 2)
        self.paymentOptions.buttonClicked.connect(self.checkOption)

        radioBreaking = QRadioButton("Breaking")
        radioBreaking.setChecked(True)
        radioPlay = QRadioButton("Play and Sale")
        radioOverBase = QRadioButton("Over Base")
        radioFull = QRadioButton("Break and Play")
        radioOverAll = QRadioButton("Over all")

        self.agreementOption = QButtonGroup()
        self.agreementOption.addButton(radioBreaking)
        self.agreementOption.addButton(radioPlay)
        self.agreementOption.addButton(radioFull)
        self.agreementOption.addButton(radioOverBase)
        self.agreementOption.addButton(radioOverAll)
        self.agreementOption.setId(radioBreaking, 0)
        self.agreementOption.setId(radioFull, 1)
        self.agreementOption.setId(radioPlay, 2)
        self.agreementOption.setId(radioOverBase, 3)
        self.agreementOption.setId(radioOverAll,4)
        self.agreementOption.buttonClicked[int].connect(self.getAgreementType)

        #Sales conditions

        lblSaleBaseAmount = QLabel("Base Amount")
        lblSaleBaseTo = QLabel("To:")
        lblSaleBasePercent = QLabel("%")

        lblSaleFirstFrom = QLabel("From:")
        lblSaleFirstTo = QLabel("To:")
        lblSaleFirstPercent = QLabel("%")

        lblSaleSecondFrom    = QLabel("From")
        lblSaleSecondTo  = QLabel("To:")
        lblSaleSecondPercent = QLabel("%")

        lblSaleThirdFrom = QLabel("From:")
        lblSaleThirdTo = QLabel("To:")
        lblSaleThirdPercent = QLabel("%")

        lblSaleFinalAmount = QLabel("Over:")
        lblSaleFinalPercent = QLabel("%")

        self.lineAmount = QLineEdit('0.00')
        self.lineAmount.setAlignment(Qt.AlignRight)
        self.lineAmount.setMaximumWidth(100)
        self.lineAmount.setValidator(valAmount)
        self.lineAmount.editingFinished.connect(self.totalAmountChanged)

        self.lineSaleBaseAmount = QLineEdit('0.00')
        self.lineSaleBaseAmount.editingFinished.connect(self.saleBaseAmountChanged)
        self.lineSaleBaseAmount.setValidator(valAmount)
        self.lineSaleBaseAmount.setMaximumWidth(100)
        self.lineSaleBaseAmount.setAlignment(Qt.AlignRight)

        self.spinSaleBasePercent = FocusSpin()
        self.spinSaleBasePercent.valueChanged.connect(lambda :self.setLastPercent(self.spinSaleBasePercent.value()))

        self.lineSaleFirstFrom = QLineEdit('0.00')
        self.lineSaleFirstFrom.setEnabled(False)
        self.lineSaleFirstFrom.setMaximumWidth(100)
        self.lineSaleFirstFrom.setEnabled(False)
        self.lineSaleFirstFrom.setAlignment(Qt.AlignRight)

        self.lineSaleFirstTo = QLineEdit('0.00')
        self.lineSaleFirstTo.setEnabled(False)
        self.lineSaleFirstTo.setValidator(valAmount)
        self.lineSaleFirstTo.editingFinished.connect(self.saleFirstToChanged)
        self.lineSaleFirstTo.setMaximumWidth(100)
        self.lineSaleFirstTo.setAlignment(Qt.AlignRight)

        self.spinSaleFirstPercent = FocusSpin()
        self.spinSaleFirstPercent.setEnabled(False)
        self.spinSaleFirstPercent.setRange(0,100)
        self.spinSaleFirstPercent.valueChanged.connect(lambda: self.setLastPercent(self.spinSaleFirstPercent.value()))
        self.lineSaleSecondFrom = QLineEdit('0.00')
        self.lineSaleSecondFrom.setEnabled(False)
        self.lineSaleSecondFrom.setMaximumWidth(100)
        self.lineSaleSecondFrom.setAlignment(Qt.AlignRight)

        self.lineSaleSecondTo = QLineEdit('0.00')
        self.lineSaleSecondTo.setEnabled(False)
        self.lineSaleSecondTo.setValidator(valAmount)
        self.lineSaleSecondTo.editingFinished.connect(self.saleSecondToChanged)
        self.lineSaleSecondTo.setMaximumWidth(100)
        self.lineSaleSecondTo.setAlignment(Qt.AlignRight)

        self.spinSaleSecondPercent = FocusSpin()
        self.spinSaleSecondPercent.setEnabled(False)
        self.spinSaleSecondPercent.valueChanged.connect(lambda: self.setLastPercent(self.spinSaleSecondPercent.value()))

        self.lineSaleThirdFrom = QLineEdit('0.00')
        self.lineSaleThirdFrom.setEnabled(False)
        self.lineSaleThirdFrom.setValidator(valAmount)
        self.lineSaleThirdFrom.setMaximumWidth(100)
        self.lineSaleThirdFrom.setAlignment(Qt.AlignRight)

        self.lineSaleThirdTo = QLineEdit('0.00')
        self.lineSaleThirdTo.setEnabled(False)
        self.lineSaleSecondTo.setValidator(valAmount)
        self.lineSaleThirdTo.editingFinished.connect(self.saleThirdToChanged)
        self.lineSaleThirdTo.setMaximumWidth(100)
        self.lineSaleThirdTo.setAlignment(Qt.AlignRight)

        self.spinSaleThirdPercent = FocusSpin()
        self.spinSaleThirdPercent.setEnabled(False)
        self.spinSaleThirdPercent.valueChanged.connect(lambda: self.setLastPercent(self.spinSaleThirdPercent.value()))

        self.lineSaleFinalAmount = QLineEdit('0.00')
        self.lineSaleFinalAmount.setEnabled(False)
        self.lineSaleFinalAmount.setMaximumWidth(100)
        self.lineSaleFinalAmount.setAlignment(Qt.AlignRight)

        self.spinSaleFinalPercent = QSpinBox()

        self.picker = PickerWidget(False, db=self.db, con_string=self.parent.con_string,parent=self)
        self.picker.increase.connect(self.querySize)

        agreementOptionLayout = QHBoxLayout()
        agreementOptionLayout.addWidget(radioBreaking)
        agreementOptionLayout.addWidget(radioFull)
        agreementOptionLayout.addWidget(radioPlay)
        agreementOptionLayout.addWidget(radioOverBase)
        agreementOptionLayout.addWidget(radioOverAll)


        groupBasic = QGroupBox()
        groupBasicLayout = QGridLayout()
        groupBasicLayout.addWidget(lblAgreement,0,0)
        groupBasicLayout.addWidget(self.lineAgreement,0,1,1,-1)
        groupBasicLayout.addWidget(lblDate,1,0)
        groupBasicLayout.addWidget(self.dateEdit,1,1)
        #groupBasicLayout.addWidget(self.checkBreaking,1,2)
        groupBasicLayout.addLayout(agreementOptionLayout,1,3)
        groupBasicLayout.addWidget(lblSupplier,2,0)
        groupBasicLayout.addWidget(self.comboSupplier,2,1)
        groupBasicLayout.addWidget(lblResponsible,2,2)
        groupBasicLayout.addWidget(self.comboResponsible,2,3)

        groupBasic.setLayout(groupBasicLayout)


        saleLayout = QGridLayout()

        saleLayout.addWidget(lblSaleBaseAmount,0,0)
        saleLayout.addWidget(lblSaleBaseTo,0,2)
        saleLayout.addWidget(self.lineSaleBaseAmount,0,3)
        saleLayout.addWidget(lblSaleBasePercent,0,4)
        saleLayout.addWidget(self.spinSaleBasePercent, 0,5)


        saleLayout.addWidget((lblSaleFirstFrom), 1, 0)
        saleLayout.addWidget((self.lineSaleFirstFrom), 1, 1)
        saleLayout.addWidget(lblSaleFirstTo, 1, 2)
        saleLayout.addWidget((self.lineSaleFirstTo), 1, 3)
        saleLayout.addWidget(lblSaleFirstPercent, 1, 4)
        saleLayout.addWidget(self.spinSaleFirstPercent, 1, 5)

        saleLayout.addWidget((lblSaleSecondFrom), 2, 0)
        saleLayout.addWidget((self.lineSaleSecondFrom), 2, 1)
        saleLayout.addWidget(lblSaleSecondTo, 2, 2)
        saleLayout.addWidget((self.lineSaleSecondTo), 2, 3)
        saleLayout.addWidget(lblSaleSecondPercent, 2, 4)
        saleLayout.addWidget(self.spinSaleSecondPercent, 2, 5)

        saleLayout.addWidget((lblSaleThirdFrom), 3, 0)
        saleLayout.addWidget((self.lineSaleThirdFrom), 3, 1)
        saleLayout.addWidget(lblSaleThirdTo, 3, 2)
        saleLayout.addWidget((self.lineSaleThirdTo), 3, 3)
        saleLayout.addWidget(lblSaleThirdPercent, 3, 4)
        saleLayout.addWidget(self.spinSaleThirdPercent, 3, 5)

        saleLayout.addWidget(lblSaleFinalAmount, 4, 0)
        saleLayout.addWidget(self.lineSaleFinalAmount, 4, 1)
        saleLayout.addWidget(lblSaleFinalPercent, 4, 4)
        saleLayout.addWidget(self.spinSaleFinalPercent, 4, 5)

        self.groupSale = QGroupBox("Sales Sharing")
        self.groupSale.setLayout(saleLayout)
        self.groupSale.setCheckable(True)
        self.groupSale.toggled.connect(self.clearSaleGroup)

        layout = QGridLayout()
        btnLayout = QHBoxLayout()
        btnLayout.addWidget(btnNewContact)
        btnLayout.addSpacing(800)
        btnLayout.addWidget(btnClose)
        btnLayout.addWidget((self.btnOk))

        amountLayout = QFormLayout()
        amountLayout.addRow(lblAmount, self.lineAmount)
        amountLayout.addRow(lblDownPayment, self.lineDownpayment)
        amountLayout.addRow(lblMinimunPayment, self.spinMinimum)
        amountLayout.addRow(lblInstallments, self.spinInstallments)

        self.groupAmount = QGroupBox("Payments")
        self.groupAmount.setLayout(amountLayout)
        self.groupAmount.setMaximumWidth(300)

        groupLayout = QVBoxLayout()
        groupLayout.addWidget(self.radioAtEnd)
        groupLayout.addWidget(self.radioFee)
        groupLayout.addWidget(self.radioOnSite)

        self.groupPayment.setLayout(groupLayout)

        basicLayout = QHBoxLayout()
        basicLayout.addSpacing(100)
        basicLayout.addWidget(groupBasic)
        basicLayout.addSpacing(100)

        middleLayout = QHBoxLayout()
        middleLayout.addWidget((self.groupPayment))
        middleLayout.addWidget(self.groupAmount)
        middleLayout.addWidget(self.groupSale)


        notesLayout = QVBoxLayout()
        notesLayout.addWidget(self.lblNotes)
        notesLayout.addWidget(self.textNotes)

        bottonLayout = QHBoxLayout()
        #bottonLayout.addSpacing(100)
        bottonLayout.addWidget(self.picker)
        #bottonLayout.addLayout(notesLayout)
        #bottonLayout.addSpacing(100)

        vLayout = QVBoxLayout()
        vLayout.addLayout(basicLayout)
        vLayout.addLayout(middleLayout)
        vLayout.addLayout(bottonLayout)
        vLayout.addLayout(notesLayout)
        vLayout.addLayout(btnLayout)

        vLayout.setContentsMargins(-1,-1,-1,0)
        layout.setContentsMargins(-1,0,-1,-1)

        self.setLayout(vLayout)
        self.setMaximumSize(1000, 500)
        self.toggleBreaking()

    @pyqtSlot(int)
    def getAgreementType(self, id):
        self.agreementType = id
        self.toggleBreaking()
        return

    @pyqtSlot()
    def sendSupplier(self):
        self.picker.supplierId = self.comboSupplier.getHiddenData(0)

    def eventFilter(self, watched, event):
        if watched == self.comboSupplier and event == QEvent.MouseButtonDblClick:
            print('pos {}'.format(event.pos()))

    @pyqtSlot(int)
    def setLastPercent(self, int):
        if int > self.spinSaleFinalPercent.value():
            self.spinSaleFinalPercent.setValue(int)


    @pyqtSlot(APM.FocusCombo)
    def supplierFocusLost(self, combo):
        try:
            self.setFocusPolicy(Qt.NoFocus)
            name = combo.currentText()
            if combo.findText(name) > -1:
                return
            else:
                if name.count(',') == 0 :
                    message = "Use proper Name format 'firstName, lastName'"
                    QMessageBox.warning(self,'Wrong name format', message)
                    combo.setFocus()
                    combo.setFocusPolicy(Qt.NoFocus)
                    combo.setCurrentIndex(0)
                    return
                res = QMessageBox.question(self,'New contact', 'Include: ' +combo.currentText() + '?')
                if res == QMessageBox.Yes:
                    self.loadNewContact(name, True)
                    return
                combo.setFocus()
                combo.setFocusPolicy(Qt.NoFocus)
                combo.setCurrentIndex(0)
        except Exception as err:
            print(err)
        finally:
            self.setFocusPolicy(Qt.StrongFocus)

    @pyqtSlot(APM.FocusCombo)
    def responsibleFocusLost(self, combo):
        try:
            self.setFocusPolicy(Qt.NoFocus)
            name = combo.currentText()
            if combo.findText(name) > -1:
                self.okToSave[3] = combo.getHiddenData(0)
                return
            else:
                if name.count(',') == 0 :
                    message = "Use proper Name format 'firstName, lastName'"
                    QMessageBox.warning(self,'Wrong name format', message)
                    combo.setFocus()
                    combo.setFocusPolicy(Qt.NoFocus)
                    combo.setCurrentIndex(0)
                    return
                res = QMessageBox.question(self,'New contact', 'Include: ' +combo.currentText() + '?')
                if res == QMessageBox.Yes:
                    self.loadNewContact(name, False)
                    return
                combo.setFocus()
                combo.setFocusPolicy(Qt.NoFocus)
                combo.setCurrentIndex(0)
        except Exception as err:
            print(err)
        finally:
            self.setFocusPolicy(Qt.StrongFocus)

    def loadNewContact(self, name, supplier = True):
        try:
            qryCheck = QSqlQuery(self.db)
            qryCheck.prepare("""
                        SELECT fullname FROM contacts 
                        WHERE fullname = ? """)
            qryCheck.addBindValue(QVariant(name))
            qryCheck.exec()
            if qryCheck.size() > 0:
                qryUpdate = QSqlQuery(self.db)
                if supplier != True:
                    qryUpdate.prepare(""" UPDATE contacts 
                        SET responsible = True 
                        WHERE id = ? """)
                else:
                    if self.agreementType in [0,1]: #checkBreaking.isChecked():
                        qryUpdate.prepare("""UPDATE contacts 
                           SET  horsebreaker = True 
                           WHERE id = ? """)
                    else:
                        qryUpdate.prepare("""
                            UPDATE contacts 
                            SET playerseller = True 
                            WHERE  id = ?""")
                qryUpdate.addBindValue(QVariant(qryCheck.value(0)))
                qryUpdate.exec()
                self.load_combos()
            qry = QSqlQuery(self.db)
            qry.prepare("""
                    INSERT INTO contacts (
                    fullname, playerseller, horsebreaker, responsible, active)
                    VALUES (?, ?, ?, ?, True)""")
            qry.addBindValue(QVariant(name))
            qry.addBindValue(QVariant(not self.checkBreaking.isChecked()))
            qry.addBindValue(QVariant(self.checkBreaking.isChecked()))
            qry.addBindValue(QVariant(not supplier))
            qry.exec()
            self.load_combos()
        except Exception as err:
            print(err)

    @pyqtSlot()
    def querySize(self):
        self.chooseSize = self.picker.querySize
        self.okSaving()

    @pyqtSlot()
    def load_combos(self):
        if self.db.isOpen():
            self.qryPlayer = QSqlQuery(self.db)
            self.qryPlayer.prepare("""
            SELECT id, fullname
            FROM Contacts
            WHERE playerseller = True
            AND active = True
            AND NOT systemcontact
            ORDER BY fullname;""")

            self.qrybreaker = QSqlQuery(self.db)
            self.qrybreaker.prepare("""
            SELECT id, fullname
            FROM Contacts
            WHERE horsebreaker = True
            AND active = True
            AND NOT systemcontact
            ORDER BY fullname;""")

            self.qryresponsible = QSqlQuery(self.db)
            self.qryresponsible.prepare("""
                        SELECT id, fullname
                        FROM Contacts
                        WHERE responsible = True
                        AND active = True
                        ORDER BY fullname;""")
            try:
                self.qryPlayer.exec()
                self.qrybreaker.exec()
                self.qryresponsible.exec()
            except APM.DataError as err:
                raise APM.DataError(err.source, err.message)
            except Exception as err:
                print(type(err).__name__)


            self.modelSupplier = QSqlQueryModel()
            self.modelSupplier.setQuery(self.qryPlayer)
            self.comboSupplier.setModel(self.modelSupplier)
            self.comboSupplier.setModelColumn(1)
            self.comboSupplier.setCurrentIndex(0)

            self.modelResponsible = QSqlQueryModel()
            self.modelResponsible.setQuery(self.qryresponsible)
            self.comboResponsible.setModel(self.modelResponsible)
            self.comboResponsible.setModelColumn(1)
            self.comboResponsible.setCurrentIndex(0)

    @pyqtSlot()
    def totalAmountChanged(self):
        self.okToSave[4] = float(self.lineAmount.text())
        self.okSaving()

    @pyqtSlot()
    def clearSaleGroup(self):
        if not self.groupSale.isChecked():
            self.lineSaleBaseAmount.setText('')
            self.lineSaleFirstFrom.setText('')
            self.lineSaleFirstTo.setText('')
            self.lineSaleSecondFrom.setText('')
            self.lineSaleSecondTo.setText('')
            self.lineSaleThirdFrom.setText('')
            self.lineSaleThirdTo.setText('')
            self.lineSaleFinalAmount.setText('')
            self.spinSaleBasePercent.setValue(0)
            self.spinSaleFirstPercent.setValue(0)
            self.spinSaleSecondPercent.setValue(0)
            self.spinSaleThirdPercent.setValue(0)
            self.spinSaleFinalPercent.setValue(0)

    @pyqtSlot()
    def saleBaseAmountChanged(self):
        self.lineSaleFirstFrom.setText(str(float(self.lineSaleBaseAmount.text()) + 1))
        self.lineSaleFirstTo.setText('0.00')
        self.lineSaleFinalAmount.setText(self.lineSaleFirstFrom.text())
        self.lineSaleFirstTo.setEnabled(True)
        self.spinSaleFirstPercent.setEnabled(True)
        self.spinSaleBasePercent.setFocus()

    @pyqtSlot()
    def saleFirstToChanged(self):
        if float(self.lineSaleFirstTo.text())> 0:
            self.lineSaleSecondFrom.setText(str(float(self.lineSaleFirstTo.text()) + 1))
            self.lineSaleSecondTo.setText('0.00')
            self.lineSaleFinalAmount.setText(self.lineSaleSecondFrom.text())
            self.lineSaleSecondTo.setEnabled(True)
            self.spinSaleSecondPercent.setEnabled(True)
            #self.spinSaleFirstPercent.setFocus()
            if float(self.lineSaleFirstTo.text()) < float(self.lineSaleFirstFrom.text()):
                self.warningMessage("Data Error", "The upper limit must be more than {}". format(
                        self.lineSaleFirstFrom.text()))
                self.lineSaleFirtTo.setText('0.00')
                self.lineSaleFirstTo.setFocus()

    @pyqtSlot()
    def saleSecondToChanged(self):
        if float(self.lineSaleSecondTo.text()) > 0:
            self.lineSaleThirdFrom.setText(str(float(self.lineSaleSecondTo.text()) + 1))
            self.lineSaleThirdTo.setText('0.00')
            self.lineSaleFinalAmount.setText(self.lineSaleThirdFrom.text())
            self.lineSaleThirdTo.setEnabled(True)
            self.spinSaleThirdPercent.setEnabled(True)
            self.spinSaleSecondPercent.setFocus()
            if float(self.lineSaleSecondTo.text()) < float(self.lineSaleSecondFrom.text()):
                self.warningMessage("Data Error", "The upper limit must be more than {}". format(
                        self.lineSaleSecondFrom.text()))
                self.lineSaleSecondTo.setText('0.00')
                self.lineSaleSecondTo.setFocus()

    @pyqtSlot()
    def saleThirdToChanged(self):
        if float(self.lineSaleThirdTo.text()) > 0:
            self.lineSaleFinalAmount.setText(str(float(self.lineSaleThirdTo.text()) + 1))
            self.spinSaleThirdPercent.setEnabled(True)
            self.spinSaleThirdPercent.setFocus()
            if float(self.lineSaleThirdTo.text()) < float(self.lineSaleThirdFrom.text()):
                self.warningMessage("Data Error", "The upper limit must be more than {}". format(
                        self.lineSaleThirdFrom.text()))
                self.lineSaleThirdTo.setText('0.00')
                self.lineSaleThirdTo.setFocus()


    @pyqtSlot()
    def checkOption(self):
        print(self.paymentOptions.checkedId())

    @pyqtSlot()
    def paymentOptionChanged(self):
        if self.radioAtEnd.isChecked():
            self.spinInstallments.setValue(0)
            self.spinInstallments.setEnabled(False)
        else:
            self.spinInstallments.setEnabled(True)
            self.spinInstallments.setValue(12)

    def changedDate(self):
        self.agreementTitle[2] = self.dateEdit.date().toString("MM-dd-yyyy")
        self.setAgreementTitle()
        self.okToSave[1] = self.dateEdit.date().toString("yyyy-MM-dd")
        self.okSaving()

    @pyqtSlot()
    def editContact(self):
        print('edit contact fired')
        try:
            c = Contacts(self.db,self.comboSupplier.currentText(), APM.OPEN_EDIT_ONE, self.supplierId,parent=self)
            c.show()
            c.exec()
        except Exception as err:
            print(type(err).__name__, err.args)

    @pyqtSlot(str)
    def newSupplier(self,txt):
        if self.isVisible():
            try:
                if self.comboSupplier.findText(txt):
                    print(txt)
            except Exception as err:
                print(err)

    @property
    def getFilename(self):
        return self.filename

    @property
    def getID(self):
        return self.agreementId

    def newContact(self):
        c = Contacts(self.db,parent=self)
        c.show()
        c.exec()

    def supplierChange(self):
        try:
            self.agreementTitle[0] = self.comboSupplier.currentText()
            self.setAgreementTitle()
            self.okToSave[2] = self.comboSupplier.getHiddenData(0)
            self.okSaving()
            self.picker.loadBaseTable()
        except TypeError as err:
            print('supplierChange' + type(err).__name__ + ' ' + err.args[0])

    @pyqtSlot()
    def responsibleChanged(self):
        try:
            self.responsibleId = self.comboResponsible.getHiddenData(0)
            self.okToSave[3] = int(self.responsibleId)
            self.okSaving()
        except TypeError as err:
            print('responsibleChange ' + type(err).__name__ + ' ' + err.args[0])

    def setAgreementTitle(self):
        try:
            if not self.agreementTitle.count(''):
                self.lineAgreement.setText("".join(self.agreementTitle))
                self.okToSave[0] = self.lineAgreement.text()
                self.okSaving()
        except Exception as err:
            print('setAgreementTitle' + err.args)


    def toggleBreaking(self):
        try:
            self.btnOk.setEnabled(False)
            self.lineAgreement.clear()
            self.modelSupplier.clear()
            if self.agreementType == 0:
                self.setWindowTitle("New Horse Breaking Agreement")
                self.agreementTitle[1] = "- Horse Breaking Agreement - "
            elif self.agreementType == 1:
                self.setWindowTitle("New Horse Full Breaking & Playing Agreement")
                self.agreementTitle[1] = "- Horse Full Breaking & Playing Agreement - "
            elif self.agreementType == 2:
                self.setWindowTitle("New Play & Sale Agreement")
                self.agreementTitle[1] = "- Play & Sale Agreement - "
            elif self.agreementType == 3:
                self.setWindowTitle("New Play & Sale Over Base Agreement")
                self.agreementTitle[1] = "- Play & Sale Over Base Agreement - "
            else:
                self.setWindowTitle("New Play & Sale Over Expenses Agreement")
                self.agreementTitle[1] = "- Play & Sale Over Expenses Agreement - "

            if self.agreementType in [0,1]: #isChecked():
                if self.qrybreaker.size() < 1:
                    raise APM.DataError("Horse Breakers", "The Horse Breaker list is empty!")
                self.modelSupplier.setQuery(self.qrybreaker)
                self.groupSale.setChecked(False) if self.agreementType == 0 else self.groupSale.setChecked(True)
                self.spinMinimum.setEnabled(True)
                self.radioFee.setChecked(True)
            else:
                if self.qryPlayer.size() < 1:
                    raise APM.DataError("Polo Player", "The Polo Player -Play&Sale- list is empty!")
                self.modelSupplier.setQuery(self.qryPlayer)
                self.agreementTitle[1] = "- Play & Sale Agreement - "
                self.groupSale.setChecked(True)
                self.spinMinimum.setEnabled(False)
                self.radioFee.setChecked(True)
            self.comboSupplier.setModelColumn(1)
            self.comboSupplier.setCurrentIndex(0)
            self.agreementTitle[0] = self.comboSupplier.currentText()
            self.agreementTitle[2] = self.dateEdit.date().toString("MM/dd/yyyy")
            self.changedDate()
            self.setAgreementTitle()
            self.picker.breaking = True if self.agreementType in [0,1] else False

        except APM.DataError as err:
            raise APM.DataError(err.source, err.message)
        except Exception as err:
            print(err)
        self.supplierChange()
        self.responsibleChanged()

    def okSaving(self):
        if self.isVisible():
            try:
                idx = self.okToSave.index(None)
                if self.agreementType == 1 and idx == 4:
                    raise ValueError("Full")
            except ValueError as err:
                if self.chooseSize is not None:
                    if self.chooseSize() > 0:
                        self.btnOk.setEnabled(True)
                        return
                self.btnOk.setEnabled(False)

    def warningMessage(self, title, message):
        QMessageBox.warning(self,
                            title,
                            message,
                            QMessageBox.Ok)

    def normalizeFloat(self, lineEdit):
        try:
            res = float(lineEdit.text())
        except TypeError as err:
            res = 0.0
        except ValueError as err:
            res = 0.0
        return res

    def saveNew(self):
        rewrite = False
        try:
            while True:
                sett = SettingsDialog()
                farmData = (sett.farm, sett.farmAddress)
                answer, size = RequestHandler.handle_request(RequestHandler, self.address, ["NEW_AGREEMENT",
                                                             self.lineAgreement.text(),
                                                             self.comboSupplier.currentText(),
                                                             self.comboResponsible.currentText(),
                                                             self.dateEdit.date().toString('yyyy-MM-dd'),
                                                             self.comboSupplier.getHiddenData(0),
                                                             self.comboResponsible.getHiddenData(0),
                                                             self.agreementType,
                                                             self.normalizeFloat(self.lineAmount),
                                                             self.spinInstallments.value(),
                                                             self.normalizeFloat(self.lineDownpayment),
                                                             self.spinMinimum.value(),
                                                             self.paymentOptions.checkedId(),
                                                             self.textNotes.document().toHtml(),
                                                             self.normalizeFloat(self.lineSaleBaseAmount),
                                                             self.normalizeFloat(self.lineSaleFirstFrom),
                                                             self.normalizeFloat(self.lineSaleFirstTo),
                                                             self.normalizeFloat(self.lineSaleSecondFrom),
                                                             self.normalizeFloat(self.lineSaleSecondTo),
                                                             self.normalizeFloat(self.lineSaleThirdFrom),
                                                             self.normalizeFloat(self.lineSaleThirdTo),
                                                             self.normalizeFloat(self.lineSaleFinalAmount),
                                                             self.spinSaleBasePercent.value(),
                                                             self.spinSaleFirstPercent.value(),
                                                             self.spinSaleSecondPercent.value(),
                                                             self.spinSaleThirdPercent.value(),
                                                             self.spinSaleFinalPercent.value(),
                                                             self.groupSale.isChecked(),
                                                             rewrite,
                                                             self.picker.agreementHorses,
                                                             farmData])
                if not answer[0]:
                    msgBox = QMessageBox()
                    updateButton = QPushButton("UPDATE")

                    if answer[3] == QSqlError.UnknownError:
                        msgBox.setWindowTitle("File Exists")
                        msgBox.setText("File: '{}' already exists!".format(answer[1]))
                        msgBox.setInformativeText("Do you want to overwrite it?")
                        msgBox.setStandardButtons(QMessageBox.Yes| QMessageBox.No)
                        msgBox.setDefaultButton(QMessageBox.No)
                    elif answer[3] == QSqlError.StatementError:
                        if answer[4] == 1062:
                            msgBox.setWindowTitle("SQL Statement Error")
                            msgBox.setText("Record for file:  '{}' already exists!".format(answer[1]))
                            msgBox.setInformativeText("Do you want to update it?")
                            msgBox.setDetailedText(answer[2])
                            msgBox.addButton(updateButton, QMessageBox.AcceptRole)
                            msgBox.setStandardButtons(QMessageBox.Cancel)
                            msgBox.setDefaultButton(QMessageBox.Cancel)
                        elif answer[4] == 1064:
                            msgBox.setWindowTitle("SQL Syntax Error")
                            msgBox.setInformativeText("Information for file '{}' has not been saved".format(answer[1]))
                            msgBox.setStandardButtons(QMessageBox.Ok)
                    ret = msgBox.exec_()
                    if ret == QMessageBox.Yes:
                        rewrite = True
                        continue
                    elif ret == QMessageBox.AcceptRole:
                        self.updateAgreement(answer[5])
                        return
                    elif ret == QMessageBox.No or ret == QMessageBox.Critical:
                        self.closeNewAgreement()
                        return
                    else:
                        return
                break
            id = answer[2]
            self.agreementId = id
            self.filename = answer[1]
            self.parent.filename = answer[1]
            self.accept()
            return answer[0]
        except ComunicationError as err:
            print(err)
        except Exception as err:
            print(type(err).__name__, err.args)

    def updateAgreement(self, id):
        pass

    def openCalendar(self):
        calendar = QCalendarWidget(parent=self)
        calendar.setGridVisible(True)
        print("Calendar here")

    def closeNewAgreement(self):
        if self.db.isOpen():
            self.db.close()
        self.close()



if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.exec()
