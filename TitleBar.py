import sys

from PyQt5.QtCore import QPoint
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QResizeEvent

class CustomBar(QWidget):

    def __init__(self, parent, title):
        super().__init__()
        self.parent = parent
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0,0,0,0)
        self.title = QLabel(title)

        btn_size = 35

        self.btn_close = QPushButton('x')
        self.btn_close.setFixedSize(btn_size, btn_size)
        self.btn_close.setStyleSheet("background-color: red;")
        self.btn_close.clicked.connect(self.btn_close_clicked)

        self.btn_max = QPushButton("+")
        self.btn_max.setFixedSize(btn_size, btn_size)
        self.btn_max.setStyleSheet("background-color : gray;")
        self.btn_max.clicked.connect(self.btn_max_clicked)

        self.title.setFixedHeight(btn_size)
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("""
        background-color : black;
        color : white;
        font-family: Tahoma;
        font-style: normal;
        font-size: 8pt;
        font-weight: bold;
        """)
        self.layout.addWidget(self.title)
        self.layout.addWidget(self.btn_max)
        self.layout.addWidget(self.btn_max)
        self.setLayout(self.layout)

        self.start = QPoint(0,0)
        self.pressing = False

    def resizeEvent(self, QResizeEvent):
        super().resizeEvent(QResizeEvent)
        self.title.setFixedWidth(self.parent.width())

    def mousePressEvent(self, event):
        self.start = self.mapToGlobal(event.pos())
        self.pressing = True

    def mouseMoveEvent(self, event):
        if self.pressing:
            self.end = self.mapToGlobal(event.pos())
            self.movement = self.end - self.start
            self.parent.setGeometry(self.mapToGlobal(self.movement).x(),
                                    self.mapToGlobal(self.movement).y(),
                                    self.parent.width(),
                                    self.parent.height())
            self.start = self.end

    def mouseReleaseEvent(self, QMouseEvent):
        self.pressing = False

    def btn_close_clicked(self):
        self.parent.hide()

    def btn_max_clicked(self):
        self.parent.showMaximized()


