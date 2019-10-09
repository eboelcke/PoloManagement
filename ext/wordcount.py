from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QLabel, QGridLayout, QWidget


class WordCount(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        currentLabel = QLabel("Current Selection", self)
        currentLabel.setStyleSheet("font-weight:bold; font-size: 15px;")

        currentWordsLabel = QLabel("Words: ", self)
        currentSymbolsLabel = QLabel("Symbols", self)

        totalWordsLabel = QLabel("Words: ", self)
        totalSymbolsLabel = QLabel("Symbols: ")

        self.currentWords = QLabel(self)
        self.currentSymbols = QLabel(self)

        totalLabel = QLabel("Total", self)
        totalLabel.setStyleSheet("font-weight:bold; font-size:15px;")

        self.totalWords = QLabel(self)
        self.totalSymbols = QLabel(self)

        spacer = QWidget()
        spacer.setFixedSize(0,5)

        layout = QGridLayout(self)
        layout.addWidget(currentLabel, 0, 0)
        layout.addWidget(currentWordsLabel, 1,0)
        layout.addWidget(self.currentWords, 1, 1)
        layout.addWidget(currentSymbolsLabel,2,0)
        layout.addWidget(self.currentSymbols,2, 1)
        layout.addWidget(spacer,3,0)
        layout.addWidget(totalLabel, 4,0)
        layout.addWidget(totalWordsLabel, 5,0)
        layout.addWidget(self.totalWords,5,1)
        layout.addWidget(totalSymbolsLabel,6,0)
        layout.addWidget(self.totalSymbols,6,1)

        self.setWindowTitle("Word Count")
        self.setGeometry(300, 300, 200, 200)
        self.setLayout(layout)

    def getText(self):
        text = self.parent.text.textCursor().selectedText()
        words= str(len(text.split()))
        symbols = str(len(text))

        self.currentWords.setText(words)
        self.currentSymbols.setText(symbols)

        text = self.parent.text.toPlainText()
        words = str(len(text.split()))
        symbols = str(len(text))

        self.totalWords.setText(words)
        self.totalSymbols.setText(symbols)





