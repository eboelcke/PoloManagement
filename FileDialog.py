import sys
from PyQt5.QtWidgets import QApplication, QWidget, QInputDialog, QLineEdit, QFileDialog
from PyQt5.QtGui import QIcon

class FileDialog(QWidget):

    def __init__(self):
        super().__init__()
        self.title = "Polo Management - Open File"
        self.left = 10
        self.top = 10
        self.width = 640
        self.height = 480
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        #self.openFileNameDialog()
        #self.openFileNamesDialog()
        #self.saveFileDialog()

    def openFileNameDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename, _ = QFileDialog.getOpenFileName(self, self.windowTitle(), '/home',                                         "All files (*);; pdf files ((*.pdf) ;; text files (*txt)",
                                                  options=options)
        self.setDirectory("C:/Users/Erick/Projects/PyQt5_design/Agreements/")
        if filename:
            print(filename)

    def openFileNamesDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        files, _ = QFileDialog.getOpenFileNames(self,"QFileDialog.getOpenFileNames()",
                                                    "C:/Users/Erick/Projects/PyQt5_design/Agreements/",
                                                "All files (*); pdf files (*.pdf); text files (*.txt)",
                                               options=options)
        if files:
            print(files)

    def saveFileDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename, _ = QFileDialog.getSaveFileName(self, "QFileDialog.getSaveFileName",
                                                  "C:/Users/Erick/Projects/PyQt5_design/Agreements/",
                                                  "All files (*);; pdf files(*.pdf);; text files (*.pdf)",
                                                  options=options)
        if filename:
            print(filename)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    fd = FileDialog()
    sys.exit(app.exec_())

