# This Python file uses the following encoding: utf-8
import os.path
import sys

from PyQt6.QtWidgets import QComboBox, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QListWidgetItem, QMessageBox
import pandas as pd
import pyqtgraph as pg

# Important:
# You need to run the following command to generate the ui_form.py file
#     pyside6-uic form.ui -o ui_form.py, or
#     pyside2-uic form.ui -o ui_form.py
from ui_form import Ui_MainWindow
import resources_rc
import pyqtgraph as pg

class TimeAxisItem(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        return [self.sec_to_time_string(v) for v in values]

    def sec_to_time_string(self, seconds):
        seconds = int(seconds)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02}:{m:02}:{s:02}"





class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.comboBoxYAxis = []
        self.ui.spinBox.setRange(0,5)
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
        self.ui.listWidgetFiles.itemChanged.connect(self.update_items_ComboY)

        #self.ui.listWidgetFilterY.currentItemChanged.connect(self.update_items_ComboY)

        # FILTER Y COMBOBOXES!!!!!
        self.ui.spinBox.valueChanged.connect(self.update_Y_Axis_list)

        #GRAFİK ÇİZİM YERİ.
        time_axis = TimeAxisItem(orientation='bottom')
        self.plot_widget = pg.PlotWidget(axisItems={'bottom': time_axis})
        self.plot_widget.addLegend()
        self.ui.verticalLayout_10.addWidget(self.plot_widget)

        self.ui.buttonFile.clicked.connect(self.plot_graph)

    def plot_graph(self):
        x_index = self.ui.comboBox.currentIndex()
        filename, x_col = self.ui.comboBox.itemData(x_index)
        x = self.data[filename][x_col]

        y_series = []
        y_cols = []
        for combo in self.comboBoxYAxis:
            index = combo.currentIndex()
            filename, y_col = combo.itemData(index)
            y_cols.append(y_col)
            y = self.data[filename][y_col]
            y_series.append(y)

        self.plot_widget.clear()
        self.plot_widget.addLegend()

        if pd.api.types.is_datetime64_any_dtype(x):
            x = (x - x.iloc[0]).dt.total_seconds()


        #colors will come from listwidgetFilterY!!!!
        colors = ['r', 'g', 'b', 'm', 'c', 'y']
        for i, y in enumerate(y_series):
            pen = pg.mkPen(color=colors[i % len(colors)], width = 3)
            label = f"{y_cols[i]}"
            self.plot_widget.plot(x, y, pen=pen, downsample=10, autoDownsample = True, name = label)

    def update_items_ComboY(self):
        for comboBox in self.comboBoxYAxis:
            comboBox.clear()
            self.add_items_comboBox(comboBox)

    def update_Y_Axis_list(self):
        desired_count = self.ui.spinBox.value()
        current_count = self.ui.listWidgetFilterY.count()

        # adding comboBox
        if desired_count > current_count:
            for i in range(desired_count - current_count):
                item = QListWidgetItem()
                #labelOfCombo = QLabel("1")
                comboBox = QComboBox()
                self.add_items_comboBox(comboBox)
                self.comboBoxYAxis.append(comboBox)
                print("Available Y axis comboBoxes: ", self.comboBoxYAxis)
                self.ui.listWidgetFilterY.addItem(item) #LABEL ??
                self.ui.listWidgetFilterY.setItemWidget(item,comboBox)

        elif desired_count < current_count:
            for _ in range(current_count - desired_count):
                last_row = self.ui.listWidgetFilterY.count() - 1
                self.comboBoxYAxis.remove(self.comboBoxYAxis[last_row])
                item = self.ui.listWidgetFilterY.takeItem(last_row)
                widget = self.ui.listWidgetFilterY.itemWidget(item)
                if widget is not None:
                    widget.deleteLater()
                del item


    def add_items_comboBox(self, combo):
        combo.clear()
        for idx, file_path in enumerate(self.available_CSV_FilesNames):
            filename = os.path.basename(file_path)
            df = self.data[filename]
            file_number = idx + 1

            for col in df.columns:
                display_text = f"CSV{file_number} - {col}"
                combo.addItem(display_text, (filename, col))

    def update_available_csv_files(self):
        self.available_CSV_FilesNames.clear()

        for i in range(self.ui.listWidgetFiles.count()):
            item = self.ui.listWidgetFiles.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                full_path = item.data(Qt.ItemDataRole.UserRole)
                self.available_CSV_FilesNames.append(full_path)
        print("Available files: ", self.available_CSV_FilesNames)
        self.add_items_comboBox(self.ui.comboBox)

    def update_CSV_List(self):
        self.ui.listWidgetFiles.clear()
        for idx, file_path in enumerate(self.uploaded_CSV_FilesNames):
            file_number = idx + 1
            short_name = os.path.basename(file_path)
            display_name = f"CSV{file_number}: {short_name}"

            item = QListWidgetItem(display_name)

            item.setData(Qt.ItemDataRole.UserRole, file_path)

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
