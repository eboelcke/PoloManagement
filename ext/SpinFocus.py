from PyQt5.QtWidgets import QSpinBox, QApplication
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFocusEvent
import sys


class FocusSpin(QSpinBox):
    focusLost = pyqtSignal(QSpinBox)
    focusGot = pyqtSignal(QSpinBox)

    def __init__(self, parent = None):
        super().__init__(parent)
        self.parent = parent

    def focusOutEvent(self, event):
        if event.gotFocus():
            self.focusGot.emit(self)

        elif event.lostFocus():
            try:
                self.focusLost.emit(self)
            except Exception as err:
                print(err)

        return

if __name__ == '__main__':
    app = QApplication(sys.argv)
    cb = FocusSpin()
    cb.show()
    app.exec()