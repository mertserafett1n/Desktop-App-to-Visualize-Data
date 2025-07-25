# This Python file uses the following encoding: utf-8
import os.path
import sys
import glob
import csv
from PyQt6.QtWidgets import QComboBox, QLabel
from PyQt6.QtCore import Qt, QSettings, QTimer, QSize, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
from PyQt6 import QtGui, QtWidgets
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QListWidgetItem,
    QMessageBox, QDialog, QVBoxLayout, QWidget, QHBoxLayout,
    QComboBox, QPushButton, QSizePolicy
)
import pandas as pd
import pyqtgraph as pg
from PyQt6.QtGui import QDoubleValidator
from ui_form import Ui_MainWindow
import resources_rc


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
        self._dialogs = []
        self.comboBoxYAxis = []
        self.data = {}
        self.uploaded_CSV_FilesNames = []
        self.available_CSV_FilesNames = []

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # Load and apply the stylesheet
        self.load_stylesheet()
        
        self.ui.spinBox.setRange(0, 5)
        self.menu_open = True

        self.ui.buttonMenu.clicked.connect(self.toggle_menu)

        # switching pages
        self.ui.buttonFilterX.clicked.connect(lambda: self.ui.pagesMenu.setCurrentWidget(self.ui.pageFilterX))
        self.ui.buttonFilterY.clicked.connect(lambda: self.ui.pagesMenu.setCurrentWidget(self.ui.pageFilterY))
        self.ui.buttonFile.clicked.connect(lambda: self.ui.pagesMenu.setCurrentWidget(self.ui.pageFile))

        self.ui.buttonUploadCSV.installEventFilter(self)

        self.ui.buttonUploadCSV.clicked.connect(self.load_csv)
        self.ui.buttonAlt.clicked.connect(self.showMinimized)
        self.ui.buttonMaximize.clicked.connect(self.toggle_maximize_restore)
        self.ui.buttonClose.clicked.connect(self.close)

        #ListWidget to show CSV Files
        self.ui.listWidgetFiles.itemChanged.connect(self.update_available_csv_files)
        self.ui.listWidgetFiles.itemChanged.connect(self.update_items_ComboY)

        #self.ui.listWidgetFilterY.currentItemChanged.connect(self.update_items_ComboY)

        # FILTER Y COMBOBOXES!!!!!
        self.ui.spinBox.valueChanged.connect(self.update_Y_Axis_list)
        self.ui.listWidgetFilterY.setSpacing(5)  # 5 pixels between rows

        #GRAFİK ÇİZİM YERİ.
        # Create layout for frameChart
        self.chart_layout = QtWidgets.QVBoxLayout(self.ui.frameChart)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        self.chart_layout.setSpacing(0)  # Remove spacing
        
        time_axis = TimeAxisItem(orientation='bottom')
        self.plot_widget = pg.PlotWidget(axisItems={'bottom': time_axis})
        self.plot_widget.addLegend()
        
        # Add plot widget to frameChart instead of verticalLayout_10
        self.chart_layout.addWidget(self.plot_widget)
        self.ui.buttonCreateGraph.clicked.connect(lambda: self.plot_graph())
        self.ui.buttonPopUp.clicked.connect(self.pop_up_graph)

        #FilterX line Edits
        self.ui.buttonResetFilters.clicked.connect(self.reset_filters)
        self.ui.lineEditMinX.setValidator(QDoubleValidator())
        self.ui.lineEditMaxX.setValidator(QDoubleValidator())

        #GPT SAID USE LIKE THIS??
        self.settings = QSettings("ASPILSAN", "DesktopApp")

        last_folder = self.settings.value("csv_folder", "")
        if last_folder:
            self.load_folder(folder_path=last_folder)

        self.marker_comboFunc()

# -------------------------------FUNCTIONS----------------------------------------------------

    def plot_graph(self, plot_widget=None):
        x_index = self.ui.comboBox.currentIndex()
        filename, x_col = self.ui.comboBox.itemData(x_index)
        x = self.data[filename][x_col]

        y_series = []
        display_texts = []
        for combo in self.comboBoxYAxis:
            index = combo.currentIndex()
            filename, y_col = combo.itemData(index)
            display_text = combo.currentText()
            display_texts.append(display_text)
            y = self.data[filename][y_col]
            y_series.append(y)

        # Checking if X is timestamp
        is_time_axis = pd.api.types.is_datetime64_any_dtype(x)

        # if comes from main
        if plot_widget is None:
            # Removing old widget from layout
            self.chart_layout.removeWidget(self.plot_widget)
            self.plot_widget.deleteLater()

            if is_time_axis:
                time_axis = TimeAxisItem(orientation='bottom')
                self.plot_widget = pg.PlotWidget(axisItems={'bottom': time_axis})
            else:
                self.plot_widget = pg.PlotWidget()

            self.plot_widget.addLegend()
            self.chart_layout.addWidget(self.plot_widget)
            plot_widget = self.plot_widget

        else:
            #  For pop-ups or external, use the passed one
            plot_widget.clear()
            plot_widget.addLegend()

        # If timestamp
        if is_time_axis:
            x = (x - x.iloc[0]).dt.total_seconds()

        if self.ui.checkBoxFilterX.isChecked():

            min_text = self.ui.lineEditMinX.text().strip()
            max_text = self.ui.lineEditMaxX.text().strip()

            mask = pd.Series([True] * len(x), index=x.index)

            if min_text:
                try:
                    min_value = float(min_text)
                    mask &= x >= min_value
                except ValueError:
                    QMessageBox.warning(self, "Invalid Min", "Min X must be a number.")
                    return

            if max_text:
                try:
                    max_value = float(max_text)
                    mask &= x <= max_value
                except ValueError:
                    QMessageBox.warning(self, "Invalid Max", "Max X must be a number.")
                    return

            # Check if filter results in any data
            if not mask.any():
                QMessageBox.warning(self, "No Data", "Filter resulted in no data points. Please adjust your filter values.")
                return

            # Apply filter and reset index to avoid KeyError issues
            x = x[mask].reset_index(drop=True)
            y_series = [y[mask].reset_index(drop=True) for y in y_series]
        plot_widget.showGrid(x = self.ui.checkBoxGridX.isChecked(), y = self.ui.checkBoxGridY.isChecked())
        if self.ui.checkBoxHideMarker.isChecked():
            marker_style = self.ui.comboMarkers.currentData()
            marker_size = self.ui.comboMarkerSize.currentData()
        else:
            marker_style = None
            marker_size = None

        colors = ['r', 'g', 'b', 'm', 'c', 'y']

        for i, y in enumerate(y_series):
            pen = pg.mkPen(color=colors[i % len(colors)], width=3)
            label = f"{display_texts[i]}"

            kwargs = dict(
                pen=pen,
                downsample=10,
                autoDownsample=True,
                name=label
            )

            if marker_style:
                kwargs["symbol"] = marker_style
                kwargs["symbolSize"] = marker_size

            plot_widget.plot(x, y, **kwargs)

    def update_items_ComboY(self):
        for comboBox in self.comboBoxYAxis:
            comboBox.clear()
            self.add_items_comboBox(comboBox)

    def update_Y_Axis_list(self):
        desired_count = self.ui.spinBox.value()
        current_count = self.ui.listWidgetFilterY.count()

        #Add new items if needed
        if desired_count > current_count:
            for i in range(desired_count - current_count):
                item = QListWidgetItem()
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)  # Only enabled
                item.setSizeHint(QSize(item.sizeHint().width(), 40))

                container = QWidget()
                layout = QHBoxLayout()
                layout.setContentsMargins(5, 5, 5, 5)

                comboBox = QComboBox()
                self.add_items_comboBox(comboBox)
                self.comboBoxYAxis.append(comboBox)


                #DESIGN!!
                container.setFixedHeight(50)
                comboBox.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
                comboBox.setMinimumHeight(30)  # For example
                comboBox.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                layout.setContentsMargins(5, 5, 5, 5)
                layout.setSpacing(5)

                remove_button = QPushButton("✕")
                remove_button.setFixedSize(25, 25)
                # Styling handled by stylesheet now

                # Connect remove button to remove this comboBox
                remove_button.clicked.connect(lambda _, cb=comboBox: self.remove_Y_Axis_item(cb))

                layout.addWidget(comboBox)
                layout.addWidget(remove_button)
                container.setLayout(layout)

                self.ui.listWidgetFilterY.addItem(item)
                self.ui.listWidgetFilterY.setItemWidget(item, container)

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

    def load_csv(self, fname=None):
        if fname is None:
            fname, _ = QFileDialog.getOpenFileName(
                self, "Select CSV", "", "CSV Files (*.csv)"
            )
            if not fname:
                return

        try:

            df = pd.read_csv(fname, sep=';')
            dfComma = pd.read_csv(fname, sep = ',')
            if df.shape[1] == 1:
                df = dfComma.copy()
            # Fix commas, etc.
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
                        pass

            # Timestamp fix
            if "Timestamp" in df.columns:
                df["Timestamp"] = pd.to_datetime(df["Timestamp"], format="mixed")

            file_name = os.path.basename(fname)
            self.data[file_name] = df

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not read file:\n{str(e)}")
            return

        if fname and fname not in self.uploaded_CSV_FilesNames:
            self.uploaded_CSV_FilesNames.append(fname)
            self.update_CSV_List()

    def pop_up_graph(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Graph")


        x_index = self.ui.comboBox.currentIndex()
        filename, x_col = self.ui.comboBox.itemData(x_index)
        x = self.data[filename][x_col]

        is_time_axis = pd.api.types.is_datetime64_any_dtype(x)

        if is_time_axis:
            time_axis = TimeAxisItem(orientation='bottom')
            popup_plot = pg.PlotWidget(axisItems={'bottom': time_axis})
        else:
            popup_plot = pg.PlotWidget()

        popup_plot.addLegend()

        self.plot_graph(plot_widget=popup_plot)

        layout = QVBoxLayout()
        layout.addWidget(popup_plot)
        dialog.setLayout(layout)

        self._dialogs.append(dialog)

        dialog.show()

    def eventFilter(self, source, event):
        if source == self.ui.buttonUploadCSV:
            if event.type() == event.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.RightButton:
                    self.load_folder()
                    return True  # Event handled
                elif event.button() == Qt.MouseButton.LeftButton:
                    self.load_csv()
                    return True
        return super().eventFilter(source, event)

    def load_folder(self, folder_path=None):
        if folder_path is None:
            folder_path = QFileDialog.getExistingDirectory(
                self, "Select Folder", ""
            )
            if not folder_path:
                return

        # save path
        self.settings.setValue("csv_folder", folder_path)

        import glob
        csv_files = glob.glob(os.path.join(folder_path, "*.csv"))

        if not csv_files:
            QMessageBox.information(self, "No CSV Files", "No CSV files found in the selected folder.")
            return

        for file in csv_files:
            self.load_csv(file)

    def remove_Y_Axis_item(self, comboBox):
        for i in range(self.ui.listWidgetFilterY.count()):
            item = self.ui.listWidgetFilterY.item(i)
            container = self.ui.listWidgetFilterY.itemWidget(item)
            if container:
                if container.findChild(QComboBox) == comboBox:
                    self.comboBoxYAxis.remove(comboBox)
                    self.ui.listWidgetFilterY.takeItem(i)
                    container.deleteLater()
                    del item
                    self.ui.spinBox.setValue(self.ui.listWidgetFilterY.count())
                    break

    def reset_filters(self):
        self.ui.lineEditMaxX.clear()
        self.ui.lineEditMinX.clear()

    def toggle_menu(self):
        # Left frame current and target width
        left_width = self.ui.frameLeft.width()
        new_width = 0 if self.menu_open else 300  # adjust to your preferred open size

        # Animate frameLeft width
        self.animation_left = QPropertyAnimation(self.ui.frameLeft, b"maximumWidth")
        self.animation_left.setDuration(300)
        self.animation_left.setStartValue(left_width)
        self.animation_left.setEndValue(new_width)
        self.animation_left.setEasingCurve(QEasingCurve.Type.InOutCubic)

        # Combine animations if needed — here, right frame expands automatically with layout
        self.animations = QParallelAnimationGroup()
        self.animations.addAnimation(self.animation_left)
        self.animations.start()

        # Change icon
        if self.menu_open:
            # Closed state icon
            self.ui.buttonMenu.setIcon(QtGui.QIcon(":/icons/feather/chevron-left.svg"))
        else:
            # Open state icon
            self.ui.buttonMenu.setIcon(QtGui.QIcon(":/icons/feather/menu.svg"))

        self.menu_open = not self.menu_open

    def marker_comboFunc(self):
        self.ui.comboMarkers.addItem("Circle", "o")
        self.ui.comboMarkers.addItem("Square", "s")
        self.ui.comboMarkers.addItem("Triangle", "t")
        self.ui.comboMarkers.addItem("Diamond", "d")
        self.ui.comboMarkers.addItem("Plus", "+")
        self.ui.comboMarkers.addItem("Cross", "x")
        for size in range(1, 6):
            self.ui.comboMarkerSize.addItem(f"{size} pt", size)

    def toggle_maximize_restore(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def load_stylesheet(self):
        """Load and apply the custom stylesheet"""
        try:
            with open('stylesheet.qss', 'r') as file:
                stylesheet = file.read()
                self.setStyleSheet(stylesheet)
        except FileNotFoundError:
            print("Warning: stylesheet.qss not found. Using default styling.")
        except Exception as e:
            print(f"Error loading stylesheet: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())
