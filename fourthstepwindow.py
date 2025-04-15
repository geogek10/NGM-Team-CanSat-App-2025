# fourthstepwindow.py
import sys, os, pandas as pd, numpy as np, pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter
from scipy.signal import savgol_filter
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPixmap, QImage
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QLabel, QPushButton, QFileDialog, QMessageBox, QTabWidget, QSizePolicy, QToolTip
)

# ---------------------------
# BackgroundWidget: Responsive background
# ---------------------------
class BackgroundWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.background_image = QPixmap("NGM--MONOCHROME-GRAY-33.png")
        
    def paintEvent(self, event):
        painter = QPainter(self)
        if not self.background_image.isNull():
            scaled = self.background_image.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        super().paintEvent(event)

# ---------------------------
# HoverScatterPlotItem: ScatterPlotItem με hover tooltips
# ---------------------------
class HoverScatterPlotItem(pg.ScatterPlotItem):
    def __init__(self, x, y, data_list, **kwargs):
        super().__init__(x=x, y=y, **kwargs)
        spots = []
        for i, (xi, yi) in enumerate(zip(x, y)):
            spots.append({'pos': (xi, yi), 'data': i, 'brush': kwargs.get('brush', pg.mkBrush(255,0,0))})
        self.setData(spots)
        self.data_list = data_list

    def hoverEvent(self, ev):
        if ev.isExit():
            QToolTip.hideText()
            return
        pts = self.pointsAt(ev.pos())
        if pts.size > 0:
            pt = pts[0]
            idx = pt.data()
            if idx is not None and idx < len(self.data_list):
                QToolTip.showText(ev.screenPos().toPoint(), str(self.data_list[int(idx)]))

# ---------------------------
# GPSDataTab: Για εμφάνιση GPS Data
# ---------------------------
class GPSDataTab(QWidget):
    def __init__(self, file_path, alt_index, temp_index, parent=None):
        """
        :param file_path: CSV αρχείο.
        :param alt_index: index για υψόμετρο.
        :param temp_index: index για θερμοκρασία.
        """
        super().__init__(parent)
        self.file_path = file_path
        self.alt_index = alt_index
        self.temp_index = temp_index
        self.layout = QVBoxLayout()
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.layout.addWidget(self.plot_widget)
        btn_layout = QHBoxLayout()
        self.btn_raw = QPushButton("Raw")
        self.btn_rolling = QPushButton("Rolling Average")
        self.btn_savgol = QPushButton("Savitzky-Golay")
        self.btn_save = QPushButton("Save Plot")
        btn_layout.addWidget(self.btn_raw)
        btn_layout.addWidget(self.btn_rolling)
        btn_layout.addWidget(self.btn_savgol)
        btn_layout.addWidget(self.btn_save)
        self.layout.addLayout(btn_layout)
        self.setLayout(self.layout)
        # Συνδέσεις κουμπιών
        self.btn_raw.clicked.connect(self.plot_raw)
        self.btn_rolling.clicked.connect(self.plot_rolling)
        self.btn_savgol.clicked.connect(self.plot_savgol)
        self.btn_save.clicked.connect(self.save_plot)
        self.load_data()

    def load_data(self):
        try:
            self.df = pd.read_csv(self.file_path)
            self.altitude = self.df.iloc[:, self.alt_index]
            self.temperature = self.df.iloc[:, self.temp_index]
            self.tooltip_data = [self.df.iloc[i].to_dict() for i in range(len(self.df))]
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading GPS data: {e}")

    def add_line_and_scatter(self, x, y, color):
        # Προσθέτουμε γραμμή
        line_item = pg.PlotDataItem(x, y, pen=pg.mkPen(color=color, width=2))
        self.plot_widget.addItem(line_item)
        # Προσθέτουμε scatter με hover
        scatter = HoverScatterPlotItem(x=x, y=y, data_list=self.tooltip_data, size=10, brush=pg.mkBrush(color))
        self.plot_widget.addItem(scatter)

    def plot_raw(self):
        self.plot_widget.clear()
        x = self.altitude.values
        y = self.temperature.values
        self.add_line_and_scatter(x, y, 'r')
        self.plot_widget.setLabel("left", "Temperature (°C)")
        self.plot_widget.setLabel("bottom", "Altitude (m)")
        self.plot_widget.setTitle("GPS Data (Raw)")

    def plot_rolling(self):
        self.plot_widget.clear()
        x = self.altitude.rolling(window=11, center=True).mean().values
        y = self.temperature.rolling(window=11, center=True).mean().values
        self.add_line_and_scatter(x, y, 'b')
        self.plot_widget.setLabel("left", "Temperature (°C)")
        self.plot_widget.setLabel("bottom", "Altitude (m)")
        self.plot_widget.setTitle("GPS Data (Rolling Average)")

    def plot_savgol(self):
        self.plot_widget.clear()
        x = savgol_filter(self.altitude.values, window_length=11, polyorder=2)
        y = savgol_filter(self.temperature.values, window_length=11, polyorder=2)
        self.add_line_and_scatter(x, y, 'g')
        self.plot_widget.setLabel("left", "Temperature (°C)")
        self.plot_widget.setLabel("bottom", "Altitude (m)")
        self.plot_widget.setTitle("GPS Data (Savitzky-Golay)")

    def save_plot(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Plot", "gps_plot.png", "PNG Files (*.png);;All Files (*)")
        if file_path:
            exporter = ImageExporter(self.plot_widget.plotItem)
            exporter.export(file_path)
            QMessageBox.information(self, "Success", f"Plot saved as {file_path}")

# ---------------------------
# PressureDataTab: Για Pressure Based Data
# ---------------------------
class PressureDataTab(QWidget):
    def __init__(self, file_path, press_index, temp_index, parent=None):
        """
        :param file_path: CSV αρχείο.
        :param press_index: index για πίεση.
        :param temp_index: index για θερμοκρασία.
        """
        super().__init__(parent)
        self.file_path = file_path
        self.press_index = press_index
        self.temp_index = temp_index
        self.layout = QVBoxLayout()
        # Sea-level inputs
        input_layout = QHBoxLayout()
        self.label_P0 = QLabel("P₀ (hPa):")
        self.edit_P0 = QLineEdit("1013.25")
        self.label_T0 = QLabel("T₀ (°C):")
        self.edit_T0 = QLineEdit("15")
        input_layout.addWidget(self.label_P0)
        input_layout.addWidget(self.edit_P0)
        input_layout.addWidget(self.label_T0)
        input_layout.addWidget(self.edit_T0)
        self.layout.addLayout(input_layout)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.layout.addWidget(self.plot_widget)
        btn_layout = QHBoxLayout()
        self.btn_raw = QPushButton("Raw")
        self.btn_rolling = QPushButton("Rolling Average")
        self.btn_savgol = QPushButton("Savitzky-Golay")
        self.btn_save = QPushButton("Save Plot")
        btn_layout.addWidget(self.btn_raw)
        btn_layout.addWidget(self.btn_rolling)
        btn_layout.addWidget(self.btn_savgol)
        btn_layout.addWidget(self.btn_save)
        self.layout.addLayout(btn_layout)
        self.setLayout(self.layout)
        self.btn_raw.clicked.connect(self.plot_raw)
        self.btn_rolling.clicked.connect(self.plot_rolling)
        self.btn_savgol.clicked.connect(self.plot_savgol)
        self.btn_save.clicked.connect(self.save_plot)
        self.load_data()

    def load_data(self):
        try:
            self.df = pd.read_csv(self.file_path)
            self.pressure = self.df.iloc[:, self.press_index]
            self.temperature = self.df.iloc[:, self.temp_index]
            self.tooltip_data = [self.df.iloc[i].to_dict() for i in range(len(self.df))]
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading Pressure data: {e}")

    def compute_altitude(self, P0, T0):
        T0_K = T0 + 273.15
        L = 0.0065
        R = 8.31432
        g = 9.80665
        M = 0.0289644
        altitude = (T0_K / L) * (1 - (self.pressure / P0) ** ((R * L) / (g * M)))
        return altitude

    def add_line_and_scatter(self, x, y, color):
        line_item = pg.PlotDataItem(x, y, pen=pg.mkPen(color=color, width=2))
        self.plot_widget.addItem(line_item)
        scatter = HoverScatterPlotItem(x=x, y=y, data_list=self.tooltip_data, size=10, brush=pg.mkBrush(color))
        self.plot_widget.addItem(scatter)

    def plot_raw(self):
        try:
            P0 = float(self.edit_P0.text())
            T0 = float(self.edit_T0.text())
        except ValueError:
            QMessageBox.warning(self, "Warning", "Please enter valid P₀ and T₀ values.")
            return
        alt = self.compute_altitude(P0, T0)
        self.plot_widget.clear()
        self.add_line_and_scatter(alt.values, self.temperature.values, 'r')
        self.plot_widget.setLabel("left", "Temperature (°C)")
        self.plot_widget.setLabel("bottom", "Altitude (m)")
        self.plot_widget.setTitle("Pressure Based Data (Raw)")

    def plot_rolling(self):
        try:
            P0 = float(self.edit_P0.text())
            T0 = float(self.edit_T0.text())
        except ValueError:
            QMessageBox.warning(self, "Warning", "Please enter valid P₀ and T₀ values.")
            return
        alt = self.compute_altitude(P0, T0)
        alt_roll = alt.rolling(window=11, center=True).mean()
        temp_roll = self.temperature.rolling(window=11, center=True).mean()
        self.plot_widget.clear()
        self.add_line_and_scatter(alt_roll.values, temp_roll.values, 'b')
        self.plot_widget.setLabel("left", "Temperature (°C)")
        self.plot_widget.setLabel("bottom", "Altitude (m)")
        self.plot_widget.setTitle("Pressure Based Data (Rolling Average)")

    def plot_savgol(self):
        try:
            P0 = float(self.edit_P0.text())
            T0 = float(self.edit_T0.text())
        except ValueError:
            QMessageBox.warning(self, "Warning", "Please enter valid P₀ and T₀ values.")
            return
        alt = self.compute_altitude(P0, T0)
        alt_savgol = savgol_filter(alt.values, window_length=11, polyorder=2)
        temp_savgol = savgol_filter(self.temperature.values, window_length=11, polyorder=2)
        self.plot_widget.clear()
        self.add_line_and_scatter(alt_savgol, temp_savgol, 'g')
        self.plot_widget.setLabel("left", "Temperature (°C)")
        self.plot_widget.setLabel("bottom", "Altitude (m)")
        self.plot_widget.setTitle("Pressure Based Data (Savitzky-Golay)")

    def save_plot(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Plot", "pressure_plot.png", "PNG Files (*.png);;All Files (*)")
        if file_path:
            exporter = ImageExporter(self.plot_widget.plotItem)
            exporter.export(file_path)
            QMessageBox.information(self, "Success", f"Plot saved as {file_path}")

# ---------------------------
# HoverScatterPlotItem (ξανά για Pressure Tab, αν δεν έχει οριστεί ήδη)
# ---------------------------
class HoverScatterPlotItem(pg.ScatterPlotItem):
    def __init__(self, x, y, data_list, **kwargs):
        super().__init__(x=x, y=y, **kwargs)
        spots = []
        for i, (xi, yi) in enumerate(zip(x, y)):
            spots.append({'pos': (xi, yi), 'data': i, 'brush': kwargs.get('brush', pg.mkBrush(255,0,0))})
        self.setData(spots)
        self.data_list = data_list

    def hoverEvent(self, ev):
        if ev.isExit():
            QToolTip.hideText()
            return
        pts = self.pointsAt(ev.pos())
        if pts.size > 0:
            pt = pts[0]
            idx = pt.data()
            if idx is not None and idx < len(self.data_list):
                QToolTip.showText(ev.screenPos().toPoint(), str(self.data_list[int(idx)]))

# ---------------------------
# OuterTab: Κύρια καρτέλα για κάθε αλγόριθμο, με nested tabs "GPS Data" και "Pressure Based Data"
# ---------------------------
class OuterTab(QWidget):
    def __init__(self, file_path, gps_alt_index, gps_temp_index, press_index, press_temp_index, parent=None):
        """
        :param file_path: CSV αρχείο.
        :param gps_alt_index: index για υψόμετρο στο GPS Data.
        :param gps_temp_index: index για θερμοκρασία στο GPS Data.
        :param press_index: index για πίεση στο Pressure Data.
        :param press_temp_index: index για θερμοκρασία στο Pressure Data.
        """
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.nested_tabs = QTabWidget()
        self.nested_tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # GPS Data tab
        self.gps_tab = GPSDataTab(file_path, gps_alt_index, gps_temp_index)
        self.nested_tabs.addTab(self.gps_tab, "GPS Data")
        # Pressure Based Data tab
        self.pressure_tab = PressureDataTab(file_path, press_index, press_temp_index)
        self.nested_tabs.addTab(self.pressure_tab, "Pressure Based Data")
        self.layout.addWidget(self.nested_tabs)
        self.setLayout(self.layout)

# ---------------------------
# FourthStepWindow: Κύριο παράθυρο με 5 κύριες καρτέλες για τους αλγόριθμους
# ---------------------------
class FourthStepWindow(BackgroundWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.setWindowTitle("Βήμα Τέταρτο")
        self.setMinimumSize(800,600)
        self.layout = QVBoxLayout()
        self.outer_tabs = QTabWidget()
        self.outer_tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Reed-Solomon: file: Reed_Solomon_Decoded_Message.csv
        # GPS Data: Altitude from column 11 (index 10), Temperature from column 14 (index 13)
        # Pressure Based: Pressure from column 13 (index 12), Temperature from column 14 (index 13)
        reed_solomon_tab = OuterTab("Reed_Solomon_Decoded_Message.csv", gps_alt_index=10, gps_temp_index=13,
                                     press_index=12, press_temp_index=13)
        
        # BCJR: file: BCJR_Output_clean.csv
        # GPS Data: Altitude from column 9 (index 8), Temperature from column 12 (index 11)
        # Pressure Based: Pressure from column 11 (index 10), Temperature from column 12 (index 11)
        bcjr_tab = OuterTab("BCJR_Output_clean.csv", gps_alt_index=8, gps_temp_index=11,
                            press_index=10, press_temp_index=11)
        
        # MAP: file: MAP_Output_clean.csv, ίδιο mapping όπως BCJR
        map_tab = OuterTab("MAP_Output_clean.csv", gps_alt_index=8, gps_temp_index=11,
                            press_index=10, press_temp_index=11)
        
        # SOVA: file: SOVA_Output_clean.csv, ίδιο mapping όπως BCJR
        sova_tab = OuterTab("SOVA_Output_clean.csv", gps_alt_index=8, gps_temp_index=11,
                            press_index=10, press_temp_index=11)
        
        # HYBRID: file: HYBRID_Output_clean.csv, ίδιο mapping όπως BCJR
        hybrid_tab = OuterTab("HYBRID_Output_clean.csv", gps_alt_index=8, gps_temp_index=11,
                            press_index=10, press_temp_index=11)
        
        self.outer_tabs.addTab(reed_solomon_tab, "Reed-Solomon")
        self.outer_tabs.addTab(bcjr_tab, "BCJR")
        self.outer_tabs.addTab(map_tab, "MAP")
        self.outer_tabs.addTab(sova_tab, "SOVA")
        self.outer_tabs.addTab(hybrid_tab, "HYBRID")
        
        self.layout.addWidget(self.outer_tabs)
        self.setLayout(self.layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FourthStepWindow()
    window.show()
    sys.exit(app.exec())
