import sys
import re
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QDialog, QPushButton, QRadioButton, QTextEdit,QLabel,
                             QCheckBox, QGridLayout, QWidget, QApplication)
from PyQt5.QtGui import QTextCursor


class Find(QDialog):

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.parent = parent
        self.lastMatch = None
        self.initUI()

    def initUI(self):

        findButton = QPushButton("Find", self)
        findButton.clicked.connect(self.find)
        findFirstButton = QPushButton("Find First", self)
        findFirstButton.clicked.connect(self.findFirst)
        replaceButton = QPushButton("Replace", self)
        replaceButton.clicked.connect(self.replace)
        allButton = QPushButton("Replace All")
        allButton.clicked.connect(self.replaceAll)

        self.normalRadio = QRadioButton("Normal", self)
        self.normalRadio.toggled.connect(self.normalMode)
        self.regexRadio = QRadioButton("Regex", self)
        self.regexRadio.toggled.connect(self.regexMode)

        self.findField = QTextEdit(self)
        self.findField.resize(250,50)
        self.replaceField = QTextEdit(self)
        self.replaceField.resize(250, 50)

        optionsLabel = QLabel("Options: ", self)

        self.caseSen = QCheckBox("Case Sensitive", self)
        self.wholeWords = QCheckBox("Whole Words", self)

        spacer = QWidget(self)
        spacer.setFixedSize(0,10)

        layout = QGridLayout()

        layout.addWidget(self.findField, 1, 0, 1, 4)
        layout.addWidget(self.normalRadio,2,2)
        layout.addWidget(self.regexRadio, 2, 3)
        layout.addWidget(findButton,2, 0)
        layout.addWidget(findFirstButton,2, 1)

        layout.addWidget(self.replaceField, 3, 0, 1, 4)
        layout.addWidget(replaceButton,4, 0, 1, 2)
        layout.addWidget(allButton, 4, 2, 1, 2)

        layout.addWidget(spacer, 5, 0)

        layout.addWidget(optionsLabel, 6, 0)

        layout.addWidget(self.caseSen,6, 1)
        layout.addWidget(self.wholeWords, 6, 2)

        self.setGeometry(300, 300, 360, 250)
        self.setWindowTitle("Find And Replace")
        self.setLayout(layout)

        self.normalRadio.setChecked(True)

    def findFirst(self):
        self.lastMatch = None
        self.find()

    def find(self):
        text = self.parent.text.toPlainText()
        query = self.findField.toPlainText()

        if self.wholeWords.isChecked():
            query = r'\W' + query + r'\W'

        flags = 0 if self.caseSen.isChecked() else re.I
        pattern = re.compile(query, flags)
        start = self.lastMatch.start() + 1 if self.lastMatch else 0
        self.lastMatch = pattern.search(text, start)
        if self.lastMatch:
            try:
                start = self.lastMatch.start()
                end = self.lastMatch.end()
                if self.wholeWords.isChecked():
                    start += 1
                    end -=1
                self.moveCursor(start, end)
            except Exception as err:
                   print(err)

        else:
            try:
                self.parent.text.moveCursor(QTextCursor.End)
            except Exception as err:
                print(err)

    def replace(self):
        try:
            cursor = self.parent.text.textCursor()
            if self.lastMatch and cursor.hasSelection():
                cursor.insertText(self.replaceField.toPlainText())
                self.parent.text.setTextCursor(cursor)
        except Exception as err:
            print(err)

    def replaceAll(self):
        self.lastMatch = None
        self.find()
        while self.lastMatch:
            self.replace()
            self.find()

    def regexMode(self):
        self.caseSen.setChecked(False)
        self.caseSen.setEnabled(False)
        self.wholeWords.setChecked(False)
        self.wholeWords.setEnabled(False)

    def normalMode(self):
        self.caseSen.setEnabled(True)
        self.wholeWords.setEnabled(True)

    def moveCursor(self, start, end):
        cursor = self.parent.text.textCursor()
        cursor.setPosition(start)
        try:
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, end - start)
            self.parent.text.setTextCursor(cursor)
        except Exception as err:
            print(err)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    f =  Find()
    f.show()
    app.exec()



