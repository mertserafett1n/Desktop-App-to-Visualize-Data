# This Python file uses the following encoding: utf-8
import os.path
import sys
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QListWidgetItem, QMessageBox
import pandas as pd


# Important:
# You need to run the following command to generate the ui_form.py file
#     pyside6-uic form.ui -o ui_form.py, or
#     pyside2-uic form.ui -o ui_form.py
from ui_form import Ui_MainWindow

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)


        self.data = {}
        self.uploaded_CSV_FilesNames = []
        self.available_CSV_FilesNames = []

        # switching pages
        self.ui.buttonFilterX.clicked.connect(lambda: self.ui.pagesMenu.setCurrentWidget(self.ui.pageFilterX))
        self.ui.buttonFilterY.clicked.connect(lambda: self.ui.pagesMenu.setCurrentWidget(self.ui.pageFilterY))
        self.ui.buttonFile.clicked.connect(lambda: self.ui.pagesMenu.setCurrentWidget(self.ui.pageFile))

        self.ui.buttonUploadCSV.clicked.connect(self.load_csv)

        #ListWidget to show CSV Files
        self.ui.listWidgetFiles.itemChanged.connect(self.update_available_csv_files)

        #pageFilterX PART

    def add_items_columX(self):
        self.ui.comboBox.clear()

        for file_path in self.available_CSV_FilesNames:
            df = pd.read_csv(file_path, sep=';')
            self.data[os.path.basename(file_path)] = df
            self.ui.comboBox.addItems(df.columns)

    def update_available_csv_files(self):
        self.available_CSV_FilesNames.clear()

        for i in range(self.ui.listWidgetFiles.count()):
            item = self.ui.listWidgetFiles.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                display_name = item.text()
                for full_path in self.uploaded_CSV_FilesNames:
                    if os.path.basename(full_path) == display_name:
                        self.available_CSV_FilesNames.append(full_path)
                        break
        print("Available files: ", self.available_CSV_FilesNames)
        self.add_items_columX()

    def update_CSV_List(self):
        self.ui.listWidgetFiles.clear()
        for file_name in self.uploaded_CSV_FilesNames:
            short_name = os.path.basename(file_name)
            item = QListWidgetItem(short_name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.ui.listWidgetFiles.addItem(item)

    def load_csv(self):
        fname, _ = QFileDialog.getOpenFileName(
            self, "CSV Sec", "", "CSV Dosyaları (*.csv)"
        )
        if fname:
            try:
                df = pd.read_csv(fname, sep=';')

                # Virgül nokta fix
                for col in df.columns:
                    if df[col].dtype == object:
                        try:
                            df[col] = (
                                df[col]
                                .astype(str)
                                .str.replace(",", ".", regex=False)
                                .astype(float)
                            )
                        except ValueError:
                            print("Donuşturulemedi.")
                            pass

                # Timestamp fix
                if "Timestamp" in df.columns:
                    df["Timestamp"] = pd.to_datetime(df["Timestamp"], format="%H:%M:%S.%f")

                # DOSYA ADI
                file_name = os.path.basename(fname)
                self.data[file_name] = df  # dict'e ekle

            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Dosya okunamadı:\n{str(e)}")
                return

            # lısteye eklemece
            if fname and fname not in self.uploaded_CSV_FilesNames:
                self.uploaded_CSV_FilesNames.append(fname)
                self.update_CSV_List()



if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())
