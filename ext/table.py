import sys
from PyQt5.QtWidgets import (QDialog, QLabel, QSpinBox, QPushButton, QGridLayout, QApplication,
                             QMessageBox)
from PyQt5.QtGui import QTextTableFormat

class Table(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        rowsLabel = QLabel("Rows: ", self)
        self.rows = QSpinBox(self)
        self.rows.setValue(3)

        colsLabel = QLabel("Columns: ")
        self.cols = QSpinBox(self)
        self.cols.setValue(3)

        spaceLabel = QLabel("Cell spacing: ", self)
        self.space = QSpinBox(self)

        padLabel = QLabel("Cell padding", self)
        self.pad = QSpinBox(self)
        self.pad.setValue(10)

        insertButton = QPushButton("Insert", self)
        insertButton.clicked.connect(self.insert)

        layout = QGridLayout()

        layout.addWidget(rowsLabel, 0, 0)
        layout.addWidget(self.rows,0,1)
        layout.addWidget(colsLabel,1,0)
        layout.addWidget(self.cols,1,1)
        layout.addWidget(padLabel,2,0)
        layout.addWidget(self.pad,2,1)
        layout.addWidget(spaceLabel,3,0)
        layout.addWidget(self.space,3,1)
        layout.addWidget(insertButton,4,0,1,2)

        self.setWindowTitle("Insert Table")
        self.setGeometry(300, 300, 200, 100)
        self.setLayout(layout)

    def insert(self):
        cursor = self.parent.text.textCursor()
        rows = self.rows.value()
        cols = self.cols.value()
        if not rows or not cols:
            popup = QMessageBox(QMessageBox.Warning,
                                "Parameter Error",
                                "rows or columns may not be cero",
                                QMessageBox.Ok,self)
            popup.show()
        else:
            padding = self.pad.value()
            space = self.space.value()

            fmt = QTextTableFormat()
            fmt.setCellPadding(padding)
            fmt.setCellSpacing(space)
            cursor.insertTable(rows, cols, fmt)
            self.close()




if __name__ == '__main__':
    app = QApplication(sys.argv)
    tb = Table()
    tb.show()
    app.exec()



