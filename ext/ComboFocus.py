from PyQt5.QtWidgets import QComboBox, QApplication
from PyQt5.QtCore import pyqtSignal, QEvent, Qt
from PyQt5.QtGui import QFocusEvent, QMouseEvent
from PyQt5 import QtGui
import sys


class FocusCombo(QComboBox):
    focusLost = pyqtSignal(QComboBox)
    focusGot = pyqtSignal(QComboBox)
    doubleClicked = pyqtSignal(QComboBox)

    def __init__(self, parent = None):
        super().__init__(parent)
        self.parent = parent

    @property
    def find(self, searchStr, column ):
        col = self.modelColumn()
        self.setModelColumn(column)
        idx = self.findData(searchStr, Qt.DisplayRole)
        self.currentIndex(idx)
        self.setModelColumn(col)


    def setEditable(self, editable):
        super().setEditable(editable)
        if self.lineEdit() is not None:
            self.lineEdit().installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.lineEdit():
            if event.type() == QEvent.MouseButtonDblClick:
                self.doubleClicked.emit(self)
        return super(FocusCombo, self).eventFilter(obj,event)

    def mouseDoubleClickEvent(self,event):
        print("double click detected")
        self.doubleClicked.emit(self)
        super(FocusCombo, self).mouseDoubleClickEvent(event)

    def focusOutEvent(self, event):
        if event.gotFocus():
            self.focusGot.emit(self)

        elif event.lostFocus():
            self.focusLost.emit(self)
        super(FocusCombo, self).focusOutEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    cb = FocusCombo()
    cb.addItems(list("abcdef"))
    cb.setEditable(True)
    cb.show()
    cb.doubleClicked.connect(print)
    app.exec_()
    sys.exit(app.exec_())