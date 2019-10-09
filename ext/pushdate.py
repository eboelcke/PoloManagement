import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QComboBox, QPushButton, QGridLayout
from PyQt5.QtGui import QTextCursor

from time import strftime

class DateTime(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.formats = ["%A, %d. %B %Y %H:%M",
                        "%A, %d. %B %Y",
                        "%d. %B %Y %H:%M",
                        "%d.%m.%Y %H:%M",
                        "%d. %B %Y",
                        "%d %m %Y",
                        "%d.%m.%Y"
                        "%x"
                        "%X",
                        "%H:%M"]
        self.initUI()

    def initUI(self):
        self.box = QComboBox(self)
        [self.box.addItem(strftime(fmt)) for fmt in self.formats]
        insert = QPushButton("Insert",self)
        insert.clicked.connect(self.insert)
        cancel = QPushButton("Cancel", self)
        cancel.clicked.connect(self.close)

        layout = QGridLayout()

        layout.addWidget(self.box, 0, 0, 1, 2)
        layout.addWidget(insert,1,0)
        layout.addWidget(cancel,1,1)

        self.setWindowTitle("Date and Time")
        self.setGeometry(300, 300, 400, 80)
        self.setLayout(layout)

    def insert(self):
        cursor = self.parent.text.textCursor()
        dateTime = strftime(self.formats[self.box.currentIndex()])
        cursor.insertText(dateTime)
        self.close()






