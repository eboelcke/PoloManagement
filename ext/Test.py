import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QDialog, QLineEdit, QPushButton, QMessageBox, QHBoxLayout, QLabel)
from ext.APM import DataError


class MainTest(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setUI()

    def setUI(self):
        self.setWindowTitle('Test')
        self.setMinimumSize(500, 500)
        lblTest = QLabel("Test)")
        pushOpenDialog = QPushButton("Open")
        pushOpenDialog.setMinimumSize(50, 50)
        pushOpenDialog.clicked.connect(self.openDialog)
        self.setCentralWidget(pushOpenDialog)

    def openDialog(self):
        try:
            diag = DialogTest()
            diag.show()
            diag.exec()
        except DataError as err:
            QMessageBox.critical(self, err.source, err.message)

class DialogTest(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setUi()

    def setUi(self):
        self.setWindowTitle('Dialog')
        self.setMinimumSize(500, 500)
        lblTest = QLabel("Test)")
        pushTest = QPushButton("Open")
        pushTest.clicked.connect(self.test)
        hLayout = QHBoxLayout()
        hLayout.addWidget(lblTest)
        hLayout.addWidget(pushTest)
        self.setLayout(hLayout)

    def test(self):
        try:
            1/0
        except ZeroDivisionError as err:
            raise DataError("test", err.args)

def main():
    app = QApplication(sys.argv)
    window = MainTest()
    window.show()
    app.exec_()

if __name__ == '__main__':
    main()