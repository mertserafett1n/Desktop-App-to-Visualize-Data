from PyQt6.QtWidgets import QApplication, QMainWindow
from ui_form import Ui_MainWindow  # Matches your form

class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # Connect your buttons here...

if __name__ == "__main__":
    app = QApplication([])
    window = MyWindow()
    window.show()
    app.exec()

