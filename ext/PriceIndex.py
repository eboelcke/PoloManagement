from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import (QDialog, QMessageBox, QFrame, QVBoxLayout, QHBoxLayout, QAbstractItemView,
                             QGridLayout, QLabel, QPushButton, QLineEdit,QTextEdit, QDateEdit, QToolButton, QCheckBox)
from PyQt5.QtGui import QDoubleValidator, QIcon, QColor
from PyQt5.QtCore import Qt, QDate, pyqtSlot, QModelIndex
from PyQt5.QtSql import QSqlDatabase, QSqlQueryModel, QSqlQuery, QSql
from ext.APM import (FocusCombo, NullDateEdit, TableViewAndModel,INDEX_UPGRADE, INDEX_NEW, INDEX_EDIT,
                     DataError, OPEN_DELETE)
from ext import Settings

class CostIndex(QDialog):
    def __init__(self, db, indexDate, supplierid, agreementId=None, supplierName=None ,mode=None, parent=None ):
        super().__init__()
        self.db = db
        self.supplierid = supplierid
        self.agreementId = agreementId
        self.indexDate = indexDate
        self.mode = mode
        self.parent = parent
        self.record = None
        self.setModal(True)
        self.templateId = None
        self.setWindowTitle("{} Index for {}".format("New Base" if mode == INDEX_NEW  else "Update",supplierName))
        self.setUI()

    def setUI(self):

        lblAgreement = QLabel('Agreement')
        self.comboAgreements = FocusCombo()
        self.comboAgreements.model().setQuery(self.getAgreements())
        self.comboAgreements.setModelColumn(1)
        self.comboAgreements.seekData(self.agreementId, 0)
        self.comboAgreements.activated.connect(self.loadTemplates)
        self.comboAgreements.activated.connect(self.enableSave)

        qryTemplate, qryConcepts = self.getTemplates()
        templateDate = None
        templateRate = None
        if qryTemplate.first():
            self.templateId = qryTemplate.value(0)
            templateDate = qryTemplate.value(1)
            templateRate = "{:.2f}".format(qryTemplate.value(3))

        lblTemplateDate = QLabel("Template Date")
        self.dateTemplateDate = NullDateEdit(self)
        self.dateTemplateDate.setEnabled(False)
        self.dateTemplateDate.setDate(templateDate if templateDate else QDate.currentDate())
        self.dateTemplateDate.setMinimumWidth(120)

        lblDate = QLabel("Date")
        self.indexdate = QDateEdit()
        self.indexdate.setCalendarPopup(True)
        self.indexdate.setDate(self.indexDate)
        self.indexdate.setDisplayFormat('MM-dd-yyyy')
        self.indexdate.setMinimumWidth(120)
        self.indexdate.editingFinished.connect(self.enableSave)

        valAmount = QDoubleValidator(0.00, 99999.99, 2)
        valQuantity = QDoubleValidator(0.000, 9999.999, 3)

        lblExchangeRate = QLabel("Exchange Rate")
        self.lineExchangeRate = QLineEdit()
        self.lineExchangeRate.setValidator(valAmount)
        self.lineExchangeRate.setText(templateRate)
        self.lineExchangeRate.setMaximumWidth(100)
        self.lineExchangeRate.editingFinished.connect(self.enableSave)
        self.lineExchangeRate.editingFinished.connect(self.updateExchangeRate)
        self.lineExchangeRate.setAlignment(Qt.AlignRight)

        lblConcept = QLabel("Concept")
        self.lineConcept = QLineEdit()
        self.lineConcept.setMinimumWidth(150)
        self.lineConcept.setEnabled(False)
        self.lineConcept.editingFinished.connect(self.enableSaveConcept)

        lblCurrency = QLabel("Currency")
        self.comboCurrency = FocusCombo(itemList=['U$A', 'AR$'])
        self.comboCurrency.setCurrentIndex(-1)  # (self.getCurrency())
        self.comboCurrency.setModelColumn(1)
        self.comboCurrency.setMaximumWidth(70)
        self.comboCurrency.activated.connect(self.enableSaveConcept)
        self.comboCurrency.setObjectName('2')
        self.comboCurrency.setEnabled(False)

        lblUnitPrice = QLabel('Unit Price')
        self.linePrice = QLineEdit()
        self.linePrice.setValidator(valAmount)
        self.linePrice.setAlignment(Qt.AlignRight)
        self.linePrice.setMinimumWidth(30)
        self.linePrice.setMaximumWidth(100)
        self.linePrice.setObjectName('1')
        self.linePrice.editingFinished.connect(self.enableSaveConcept)
        self.linePrice.setEnabled(False)

        lblQuantity = QLabel('Quantity')
        self.lineQuantity = QLineEdit()
        self.lineQuantity.setValidator(valQuantity)
        self.lineQuantity.setAlignment(Qt.AlignRight)
        self.lineQuantity.setMinimumWidth(30)
        self.lineQuantity.setMaximumWidth(100)
        self.lineQuantity.setObjectName('0')
        self.lineQuantity.editingFinished.connect(self.enableSaveConcept)
        self.lineQuantity.setEnabled(False)

        self.lblAmount = QLabel("Amount:")
        self.lblAmount.setMinimumWidth(300)
        self.lineAmount = QLineEdit()
        self.lineAmount.setEnabled(False)
        self.lineAmount.setValidator(valAmount)
        self.lineAmount.setText('')

        colorDict = {'column': (2),
                     1: (QColor('white'), QColor('blue')),
                     0: (QColor('red'), QColor('yellow'))}
        colDict = {0: ("ID", True, True, False, None),
                   1: ("Concept", False, False, False, None),
                   2: ("CurrencyIndex", True, True, False, None),
                   3: ("Currency Sign", False, False, True, None),
                   4: ("Price", False, True, 2, None),
                   5: ("Quantity", False, True, 2, None),
                   6: ("Amount", False, True, 2, None),
                   7: ("ConceptID", True, True, True, None),
                   8: ("Currencyid", True, True, True, None)}

        self.tableTemplate = TableViewAndModel(colDict=colDict, colorDict=colorDict,
                                               size=(500, 500), qry=qryConcepts)
        self.tableTemplate.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tableTemplate.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tableTemplate.doubleClicked.connect(self.getConcept)
        self.tableTemplate.currentSelect.connect(self.moveSelection)

        self.lblTotal = QLabel(self.getIndex())

        pushCancel = QPushButton("Exit")
        pushCancel.setMaximumWidth(70)
        pushCancel.clicked.connect(self.widgetClose)

        self.pushSave = QPushButton("Save")
        self.pushSave.setMaximumWidth(70)
        self.pushSave.setEnabled(True)
        self.pushSave.clicked.connect(self.saveAndClose)

        self.pushReset = QPushButton()
        self.pushReset.setIcon(QIcon(":Icons8/Edit/reset.png"))
        self.pushReset.setMaximumWidth(50)
        self.pushReset.setEnabled(False)
        self.pushReset.clicked.connect(self.resetWidget)

        self.pushDelete = QPushButton("Delete")
        self.pushDelete.setMaximumWidth(70)
        self.pushDelete.setEnabled(False)
        self.pushDelete.clicked.connect(self.deleteIndex)

        self.pushSaveConcept = QPushButton("Save")
        self.pushSaveConcept.setMaximumWidth(70)
        self.pushSaveConcept.setEnabled(False)
        self.pushSaveConcept.clicked.connect(self.saveConcept)

        self.pushDeleteConcept = QPushButton("Delete")
        self.pushDeleteConcept.setMaximumWidth(70)
        self.pushDeleteConcept.setEnabled(False)
        self.pushDeleteConcept.clicked.connect(self.deleteConcept)

        self.pushAddConcept = QPushButton("Add")
        self.pushAddConcept.setMaximumWidth(70)
        self.pushAddConcept.setVisible(True if self.mode == INDEX_NEW else False)
        self.pushAddConcept.clicked.connect(self.loadRecord)

        self.pushEditConcept = QPushButton("Edit")
        self.pushEditConcept.setMaximumWidth(70)
        self.pushEditConcept.setEnabled(False)
        self.pushEditConcept.clicked.connect(self.editConcept)

        self.pushClearConcept = QPushButton("Clear")
        self.pushClearConcept.setMaximumWidth(70)
        self.pushClearConcept.setEnabled(True)
        self.pushClearConcept.clicked.connect(self.clearConceptDraft)

        costIndexLayout = QGridLayout()
        costIndexLayout.addWidget(lblTemplateDate,0,0)
        costIndexLayout.addWidget(self.dateTemplateDate,0,1)
        costIndexLayout.addWidget(lblAgreement, 1, 0)
        costIndexLayout.addWidget(self.comboAgreements,1,1,4,2,Qt.AlignTop)
        costIndexLayout.addWidget(lblDate,2,0)
        costIndexLayout.addWidget(self.indexdate,2,1)
        costIndexLayout.addWidget(lblExchangeRate,2,2)
        costIndexLayout.addWidget(self.lineExchangeRate,2,3)

        costIndexFrame = QFrame()
        costIndexFrame.setLayout(costIndexLayout)
        costIndexFrame.setMaximumWidth(500)

        costDetailLayout = QGridLayout()
        costDetailLayout.addWidget(lblConcept,0,0)
        costDetailLayout.addWidget(self.lineConcept,0,1, Qt.AlignLeft)
        costDetailLayout.addWidget(lblCurrency,0,3)
        costDetailLayout.addWidget(self.comboCurrency,0,4)
        costDetailLayout.addWidget(lblUnitPrice,1,0)
        costDetailLayout.addWidget(self.linePrice,1,1, Qt.AlignLeft)
        costDetailLayout.addWidget(lblQuantity,1,3)
        costDetailLayout.addWidget(self.lineQuantity,1,4)
        costDetailLayout.addWidget(self.lblAmount,2,2)
        costDetailLayout.addWidget(self.lineAmount,2,3)
        costDetailLayout.addWidget(self.pushClearConcept,3,0)
        costDetailLayout.addWidget(self.pushDeleteConcept, 3, 1)
        costDetailLayout.addWidget(self.pushEditConcept,3, 2,)
        costDetailLayout.addWidget(self.pushAddConcept,3,3)
        costDetailLayout.addWidget(self.pushSaveConcept, 3, 4)

        costDetailFrame = QFrame()
        costDetailFrame.setMaximumWidth(500)
        costDetailFrame.setLayout(costDetailLayout)

        dataLayout = QGridLayout()
        dataLayout.addWidget(self.tableTemplate,0,0)
        dataLayout.addWidget(self.lblTotal,1,0, Qt.AlignRight)

        dataFrame = QFrame()
        dataFrame.setMaximumWidth(500)
        dataFrame.setLayout(dataLayout)

        buttonsLayout = QHBoxLayout()
        buttonsLayout.addWidget(pushCancel, Qt.AlignRight)
        buttonsLayout.addWidget(self.pushReset, Qt.AlignRight)
        buttonsLayout.addWidget(self.pushSave, Qt.AlignRight)

        layout = QVBoxLayout()
        layout.addWidget(costIndexFrame,Qt.AlignHCenter)
        layout.addWidget(costDetailFrame)
        layout.addWidget(dataFrame)
        layout.addLayout(buttonsLayout)

        self.setLayout(layout)

    @pyqtSlot()
    def loadTemplates(self):
        try:
            if self.mode == INDEX_NEW:
                newDate = QDate.fromString(self.comboAgreements.getHiddenData(2), "yyyy-MM-dd")
                self.indexdate.setDate(newDate)
                return
            newDate = QDate.fromString(self.comboAgreements.getHiddenData(2), "yyyy-MM-dd")
            qryIndex, qryConcept = self.getTemplates()
            self.dateTemplateDate.setDate(qryIndex.value(1))
            self.lineExchangeRate.setText("{:.2f}".format(qryIndex.value(3)))
            self.tableTemplate.model().setQuery(qryConcept)
            self.lblTotal.setText(self.getIndex())



        except Exception as err:
            print("CostIndex: loadTemplates", err.args)

    def getAgreements(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL costindex_getagreements ({}, {})".format(self.supplierid, self.mode))
            if qry.lastError().type() != 0:
                raise DataError("CostIndex: getAgreements", qry.lastQuery().text())
            return qry
        except DataError as err:
            print(err.source, err.message)

    @pyqtSlot()
    def updateExchangeRate(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL costindex_updateexchangerate({})".format(self.lineExchangeRate.text()))
            if qry.lastError().type() != 0:
                raise DataError("updateExchangeRate", qry.lastError().text())
            self.tableTemplate.model().setQuery(qry)
            self.lblTotal.setText(self.getIndex())

        except DataError as err:
            print("updateExchangeRate", qry.lastError().text())

    @pyqtSlot()
    def saveConcept(self):
        try:
            ans = QMessageBox.question(self, "Save concept", "Do you want to save concept {}?".format(
                self.lineConcept.text()), QMessageBox.Yes | QMessageBox.No)
            if ans == QMessageBox.Yes:
                qry = QSqlQuery(self.db)
                qry.exec("CALL costindex_addoreditconcept({}, '{}', {}, {}, "
                         "{}, {}, {})".format(
                    'NULL' if self.record is None else self.record.value(7),
                    self.lineConcept.text() if self.mode == 0 else 'NULL',
                    self.comboCurrency.currentIndex() if self.mode == 0 else 'NULL',
                    self.linePrice.text(),
                    self.lineQuantity.text() if self.mode == 0 else 'NULL',
                    self.lineAmount.text(),
                    self.mode
                    ))
                if qry.lastError().type() != 0:
                    raise DataError("CostIndex: saveConcept", qry.lastError().text())
                self.tableTemplate.model().setQuery(qry)
                self.lblTotal.setText(self.getIndex())
                self.enableSave()
            self.clearConceptDraft()

        except DataError as err:
            print(err.args)
        except Exception as err:
            print("CostIndex: Concept", err.args)

    @pyqtSlot()
    def deleteConcept(self):
        try:
            ans = QMessageBox.question(self, "Delete concept", "Do you want to delete concept {}?".format(
                self.record.value(1)), QMessageBox.Yes|QMessageBox.No)
            if ans == QMessageBox.Yes:
                qry = QSqlQuery(self.db)
                qry.exec("CALL costindex_deleteconcept({})".format(self.record.value(7)))
                if qry.lastError().type() != 0:
                    raise DataError("deleteConcept", qry.LastError().text())
                self.tableTemplate.model().setQuery(qry)
                self.lblTotal.setText(self.getIndex())
                self.enableSave()
            self.clearConceptDraft()
        except DataError as err:
            print("deleteConcept", err.args)

    @pyqtSlot()
    def loadRecord(self, record=None):
        try:
            res = QMessageBox.question(self, "Edit Concept", "Do you want to {} '{}' concept?\n"
                                                         "".format("Edit or Delete" if self.mode == INDEX_NEW \
                                                                   else "Edit", record.value(1)) if record is not None else
                                   "Do you want to add a new concept?")
            if res == QMessageBox.Yes:
                if record is not None:
                    self.pushDeleteConcept.setEnabled(True if self.mode == INDEX_NEW else False)
                    self.pushEditConcept.setEnabled(True)
                    self.lineConcept.setText(record.value(1))
                    self.comboCurrency.setCurrentIndex(record.value(2))
                    self.linePrice.setText("{:.2f}".format(record.value(4)))
                    self.lineQuantity.setText("{:.3f}".format(record.value(5)))
                    self.lineAmount.setText("{:.2f}".format(record.value(6)))
                    self.record = record
                    return
                self.lineConcept.setEnabled(True)
                self.linePrice.setEnabled(True)
                self.lineQuantity.setEnabled(True)
                self.comboCurrency.setEnabled(True)
                self.lineConcept.clear()
                self.linePrice.clear()
                self.lineQuantity.clear()
                self.comboCurrency.setCurrentIndex(-1)
                self.lineAmount.clear()
                return
            self.clearConceptDraft()
        except Exception as err:
            print("loadRecord", err.args)

    @pyqtSlot(int)
    def moveSelection(self, row):
        try:
            qry = self.tableTemplate.model().query()
            qry.seek(row)
            record = qry.record()
            self.loadRecord(record)
        except Exception as err:
            print('moveSelection', err.args)

    @pyqtSlot()
    def getConcept(self):
        try:
            qry = self.tableTemplate.model().query()
            row = self.tableTemplate.currentIndex().row()
            qry.seek(row)
            record = qry.record()
            self.loadRecord(record)
        except Exception as err:
            print('getConcept', err.args)

    @pyqtSlot()
    def clearConceptDraft(self):
        self.lineConcept.setEnabled(False)
        self.linePrice.setEnabled(False)
        self.lineQuantity.setEnabled(False)
        self.comboCurrency.setEnabled(False)
        self.lineConcept.clear()
        self.linePrice.clear()
        self.lineQuantity.clear()
        self.comboCurrency.setCurrentIndex(-1)
        self.lineAmount.clear()
        self.pushDeleteConcept.setEnabled(False)
        self.pushEditConcept.setEnabled(False)

    def createTemporaryTables(self):
        qry = QSqlQuery(self.db)
        qry.exec("CALL costindex_temporarytables({},{})".format(self.supplierid, self.agreementid))
        if qry.lastError().type()!= 0:
            raise DataError("createTemporaryTables", qry.lastError().text())
        if qry.first():
            raise DataError("createTemporaryTables", qry.value(0))

    @pyqtSlot()
    def getTemplates(self):
        qryTemplates = QSqlQuery(self.db)
        qryIndex = QSqlQuery(self.db)
        qryConcepts =QSqlQuery(self.db)
        qryTemplates.exec("CALL costindex_temporarytables({},{}, {})".format(self.supplierid,
                'NULL' if self.comboAgreements.currentIndex() < 0 else\
                    self.comboAgreements.getHiddenData(0), self.mode))
        if qryTemplates.lastError().type() != 0:
            raise DataError("CostIndex: getTemplates", qryTemplates.lastError().text())
        if qryTemplates.first():
            if qryTemplates.value(0) == 0:
                if self.isVisible():
                    raise DataError("CostIndex: getTemplates", "The base template is missing!")
            else:
                raise DataError("getTemplates", qryTemplates.value(0))
        qryIndex.exec("CALL costindex_getcostindex()")
        if qryIndex.lastError().type() != 0:
            raise DataError("CostIndex: getTemplates-qryIndex", qryIndex.lastError().text())
        if not qryIndex.first():
            if self.isVisible():
                res = QMessageBox.warning(self, "Cost Index", "The base index is missing", QMessageBox.Close)
                raise DataError("CostIndex: getTemplates", "The base index is missing")
                return
        #costindexid = qryIndex.value(0)
        qryConcepts.exec("CALL costindex_gettemplateconcepts()")
        if qryConcepts.lastError().type() != 0:
            raise DataError("CostIndex:  getTemplate", qryConcepts.lastError().text())
        return qryIndex, qryConcepts

    def getTemplateConcepts(self, id):
        qry = QSqlQuery(self.db)
        qry.exec("CALL costindex_gettemplateconcepts({})".format(id))
        if qry.lastError().type() != 0:
            raise DataError("gettemplateconcept", qry.lastError().text())
        return qry

    @pyqtSlot()
    def enableSaveConcept(self):
        if self.lineConcept.text() and self.comboCurrency.currentText() \
            and self.linePrice.text() and self.lineQuantity.text():
            self.pushSaveConcept.setEnabled(True)
            self.pushDeleteConcept.setEnabled(True)
            if self.sender().objectName() in ['0','1','2']:
                self.lineAmount.setText("{:.2f}".format(float(self.linePrice.text()) *
                                                               float(self.lineQuantity.text())
                                                               if self.comboCurrency.currentIndex() == 1 else
                                                               float(self.linePrice.text()) *
                                                               float(self.lineQuantity.text()) *
                                                               float(self.lineExchangeRate.text())))


    @pyqtSlot()
    def enableSave(self):
        try:
            if self.comboAgreements.currentIndex() < 0:
                return
            self.pushSave.setEnabled(True)
            self.pushReset.setEnabled(True)
        except AttributeError as err:
            pass

    @pyqtSlot()
    def widgetClose(self):
        self.done(QDialog.Rejected)

    @pyqtSlot()
    def deleteIndex(self):
        pass

    @pyqtSlot()
    def saveAndClose(self):
        try:
            if isinstance(self.parent, QDialog):
                costIndex = [self.indexdate.date().toString("yyyy-MM-dd"), self.lineExchangeRate.text()]
                concepts = []
                qry = self.tableTemplate.model().query()
                qry.seek(-1)
                while qry.next():
                    concepts.append((qry.value(1),
                                     qry.value(2),
                                     qry.value(4),
                                     qry.value(5),
                                     qry.value(6)))

                self.parent.costIndex = costIndex
                self.parent.costIndexDetail = concepts
                self.parent.lineBaseIndex.setText(self.lblTotal.text()[7:])
                self.widgetClose()
                return
            qry = QSqlQuery(self.db)
            qry.exec("CALL costindex_save({}, '{}', {}, {})".format(self.comboAgreements.getHiddenData(0),
                                                                    self.indexdate.date().toString('yyyy-MM-dd'),
                                                                    self.lineExchangeRate.text(),
                                                                    True if self.mode == INDEX_NEW else False))
            if qry.lastError().type() != 0:
                raise DataError("CostIndex: saveAndClose", qry.lastError().text())
            if qry.first():
                raise DataError("CostIndex: saveAndClose", qry.value(0))
            #self.parent.costIndex
        except DataError as err:
            print("saveAndClose", err.message)
        except Exception as err:
            print("saveAndClose ", err.args)
        finally:
            self.widgetClose()

    @pyqtSlot()
    def resetWidget(self):
        try:
            qry = QSqlQuery(self.db)
            qry.exec("CALL costindex_droptemporarytables()")
            if qry.lastError().type() != 0:
                raise DataError("resetWidget", qry.lastError().text())
            qryTemplate, qryConcepts = self.getTemplates()
            if qryTemplate.first():
                self.templateId = qryTemplate.value(0)
                templateDate = qryTemplate.value(1)
                templateRate = "{:.2f}".format(qryTemplate.value(3))
                self.indexdate.setDate(self.indexDate)
                self.lineExchangeRate.setText(templateRate)
                self.tableTemplate.model().setQuery(qryConcepts)
                self.lblTotal.setText(self.getIndex())

        except DataError as err:
            print("resetWidget", qry.lastError().text())
        except Exception as err:
            print("resetWidget", err.args)

    def getIndex(self):
        try:
            amount = 0
            qry = self.tableTemplate.model().query()
            qry.seek(-1)
            while qry.next():
                amount += qry.value(6)
            return " Index: {:.2f}".format(amount)
        except TypeError as err:
            print("CostIndex: getIndex", "Empty query")
            self.lblTotal.settext('0')

    @pyqtSlot()
    def editConcept(self):
        if self.mode == INDEX_NEW:
            self.lineConcept.setEnabled(True)
            self.linePrice.setEnabled(True)
            self.lineQuantity.setEnabled(True)
            self.comboCurrency.setEnabled(True)
        else:
            self.linePrice.setEnabled(True)