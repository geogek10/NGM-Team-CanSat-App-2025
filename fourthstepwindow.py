# fourthstepwindow.py
import sys, os, pandas as pd, numpy as np, pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter
from scipy.signal import savgol_filter
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QPainter, QPixmap, QImage, QIntValidator, QFont
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QLabel, QPushButton, QFileDialog, QMessageBox, QTabWidget, QSizePolicy, QToolTip
)
# --- Added imports for the new Map Generation Tab ---
import json
from PyQt6.QtWebEngineWidgets import QWebEngineView # Requires PyQt6-WebEngine

# --- Removed folium imports ---

# ---------------------------
# BackgroundWidget
# ---------------------------
class BackgroundWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        image_path = os.path.join(os.path.dirname(__file__), "NGM--MONOCHROME-GRAY-33.png")
        self.background_image = QPixmap(image_path)
        if self.background_image.isNull():
            print(f"Warning: Background image not found at {image_path}")

    def paintEvent(self, event):
        painter = QPainter(self)
        if not self.background_image.isNull():
            scaled = self.background_image.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            x = (self.width() - scaled.width()) / 2
            y = (self.height() - scaled.height()) / 2
            painter.drawPixmap(int(x), int(y), scaled)
        super().paintEvent(event)

# ---------------------------
# HoverScatterPlotItem
# ---------------------------
class HoverScatterPlotItem(pg.ScatterPlotItem):
    def __init__(self, x, y, data_list, **kwargs):
        super().__init__(x=x, y=y, **kwargs)
        spots = []
        default_brush = pg.mkBrush(255,0,0, 150)
        spot_brush = kwargs.get('brush', default_brush)
        for i, (xi, yi) in enumerate(zip(x, y)):
            spot_data = {'pos': (xi, yi), 'data': i, 'brush': spot_brush}
            spots.append(spot_data)
        self.setData(spots)
        self.data_list = data_list

    def hoverEvent(self, ev):
        if ev.isExit():
            QToolTip.hideText()
            return
        pts = self.pointsAt(ev.pos())
        if len(pts) > 0:
            pt = pts[0]
            idx = pt.data()
            if idx is not None and 0 <= idx < len(self.data_list):
                try:
                    data_item = self.data_list[int(idx)]
                    if isinstance(data_item, dict):
                         tooltip_text = "\n".join([f"{k}: {v}" for k, v in list(data_item.items())[:10]])
                         if len(data_item) > 10: tooltip_text += "\n..."
                    elif isinstance(data_item, (list, tuple)):
                         tooltip_text = ", ".join(map(str, data_item))
                    else:
                         tooltip_text = str(data_item)
                    QToolTip.setStyleSheet("QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white; }")
                    QToolTip.showText(ev.screenPos().toPoint(), tooltip_text, self)
                except (IndexError, ValueError, TypeError) as e:
                     QToolTip.showText(ev.screenPos().toPoint(), "Invalid Data", self)
        else:
             QToolTip.hideText()

# ---------------------------
# GPSDataTab
# ---------------------------
class GPSDataTab(QWidget):
    # (GPSDataTab code remains unchanged from previous version)
    def __init__(self, file_path, alt_index, temp_index, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.alt_index = alt_index
        self.temp_index = temp_index
        self.df = None
        self.altitude = None
        self.temperature = None
        self.tooltip_data = []
        self.layout = QVBoxLayout()
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.plot_widget.setBackground('k')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.layout.addWidget(self.plot_widget)
        btn_layout = QHBoxLayout()
        self.btn_raw = QPushButton("Raw Data")
        self.btn_rolling = QPushButton("Rolling Average (11)")
        self.btn_savgol = QPushButton("Savitzky-Golay (11, 2)")
        self.btn_save = QPushButton("Save Plot")
        btn_layout.addWidget(self.btn_raw)
        btn_layout.addWidget(self.btn_rolling)
        btn_layout.addWidget(self.btn_savgol)
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.btn_save)
        self.layout.addLayout(btn_layout)
        self.setLayout(self.layout)
        self.btn_raw.clicked.connect(self.plot_raw)
        self.btn_rolling.clicked.connect(self.plot_rolling)
        self.btn_savgol.clicked.connect(self.plot_savgol)
        self.btn_save.clicked.connect(self.save_plot)
        self.load_data()
        if self.df is not None:
            self.plot_raw()

    def load_data(self):
        if not os.path.exists(self.file_path):
             QMessageBox.critical(self, "Error", f"File not found: {self.file_path}")
             self.df = None; return
        try:
            try:
                 self.df = pd.read_csv(self.file_path, low_memory=False)
                 if self.alt_index >= len(self.df.columns) or self.temp_index >= len(self.df.columns):
                      print(f"Warning: Indices ({self.alt_index},{self.temp_index}) seem out of bounds for columns {list(self.df.columns)}. Trying without header.")
                      raise IndexError("Index out of bounds with header")
                 alt_col_name = self.df.columns[self.alt_index]
                 temp_col_name = self.df.columns[self.temp_index]
                 print(f"GPS Tab: Using columns '{alt_col_name}' (idx {self.alt_index}) for Alt, '{temp_col_name}' (idx {self.temp_index}) for Temp.")
                 self.altitude = pd.to_numeric(self.df.iloc[:, self.alt_index], errors='coerce')
                 self.temperature = pd.to_numeric(self.df.iloc[:, self.temp_index], errors='coerce')
                 self.tooltip_data = [row.to_dict() for _, row in self.df.iterrows()]
            except (IndexError, ValueError, pd.errors.ParserError, TypeError):
                 print(f"Info: Reading GPS file '{os.path.basename(self.file_path)}' assuming no header.")
                 self.df = pd.read_csv(self.file_path, header=None, low_memory=False)
                 if self.alt_index >= len(self.df.columns) or self.temp_index >= len(self.df.columns):
                     raise IndexError(f"Index out of bounds ({max(self.alt_index, self.temp_index)}) for {len(self.df.columns)} columns (no header).")
                 self.altitude = pd.to_numeric(self.df.iloc[:, self.alt_index], errors='coerce')
                 self.temperature = pd.to_numeric(self.df.iloc[:, self.temp_index], errors='coerce')
                 self.tooltip_data = [ {f'col_{i}': val for i, val in row.items() } for _, row in self.df.iterrows()]

            initial_rows = len(self.df)
            valid_mask = self.altitude.notna() & self.temperature.notna()
            self.altitude = self.altitude[valid_mask].reset_index(drop=True)
            self.temperature = self.temperature[valid_mask].reset_index(drop=True)
            self.tooltip_data = [self.tooltip_data[i] for i, valid in enumerate(valid_mask) if valid]
            print(f"GPS Tab: Kept {len(self.altitude)} rows out of {initial_rows} after removing NaNs in Alt/Temp columns.")
            if self.altitude.empty or self.temperature.empty:
                 raise ValueError("No valid numeric data found in specified columns after cleaning.")

        except FileNotFoundError:
             QMessageBox.critical(self, "Error", f"File not found: {self.file_path}"); self.df = None
        except IndexError as e:
            QMessageBox.critical(self, "Error", f"Column index error loading GPS data: {e}\nFile: {os.path.basename(self.file_path)}\nIndices: Alt={self.alt_index}, Temp={self.temp_index}"); self.df = None
        except ValueError as e:
            QMessageBox.critical(self, "Error", f"Data type error loading GPS data: {e}\nFile: {os.path.basename(self.file_path)}\nIndices: Alt={self.alt_index}, Temp={self.temp_index}"); self.df = None
        except Exception as e:
            import traceback; print(traceback.format_exc())
            QMessageBox.critical(self, "Error", f"An unexpected error occurred loading GPS data:\n{e}\nFile: {os.path.basename(self.file_path)}"); self.df = None

    def add_line_and_scatter(self, x, y, color, name):
        x_np = np.array(x, dtype=float)
        y_np = np.array(y, dtype=float)
        valid_indices = ~np.isnan(x_np) & ~np.isnan(y_np)
        x_plot = x_np[valid_indices]
        y_plot = y_np[valid_indices]
        if len(x_plot) == 0: print(f"Warning: No valid (non-NaN) points to plot for '{name}'."); return

        line_item = pg.PlotDataItem(x_plot, y_plot, pen=pg.mkPen(color=color, width=2), name=name)
        self.plot_widget.addItem(line_item)

        filtered_tooltip_data = [self.tooltip_data[i] for i, valid in enumerate(valid_indices) if valid]
        if filtered_tooltip_data:
             scatter = HoverScatterPlotItem(x=x_plot, y=y_plot, data_list=filtered_tooltip_data,
                                            size=8, brush=pg.mkBrush(color), name=name + " Points")
             self.plot_widget.addItem(scatter)
        else: print(f"Warning: No valid data points to scatter plot for '{name}' (check data filtering).")

    def _common_plot_settings(self, title):
        self.plot_widget.clear()
        self.plot_widget.addLegend(offset=(10, 10), labelTextColor='w')
        label_style = {'color': '#FFF', 'font-size': '12pt'}
        self.plot_widget.setLabel("left", "Temperature (°C)", units='°C', **label_style)
        self.plot_widget.setLabel("bottom", "Altitude (m)", units='m', **label_style)
        self.plot_widget.setTitle(title + f" - {os.path.basename(self.file_path)}", color='w', size='14pt')
        axis_pen = pg.mkPen(color=(200, 200, 200))
        self.plot_widget.getAxis('left').setPen(axis_pen); self.plot_widget.getAxis('left').setTextPen(axis_pen)
        self.plot_widget.getAxis('bottom').setPen(axis_pen); self.plot_widget.getAxis('bottom').setTextPen(axis_pen)

    def plot_raw(self):
        if self.df is None or self.altitude is None or self.temperature is None: print("GPS Raw Plot: Data not loaded."); return
        if self.altitude.empty: print("GPS Raw Plot: Altitude data is empty."); return
        self._common_plot_settings("GPS Data (Raw)")
        x = self.altitude.values; y = self.temperature.values
        self.add_line_and_scatter(x, y, 'r', "Raw Data")
        print(f"GPS Raw Plot: Plotted {len(x)} points.")

    def plot_rolling(self):
        if self.df is None or self.altitude is None or self.temperature is None: print("GPS Rolling Plot: Data not loaded."); return
        if self.altitude.empty: print("GPS Rolling Plot: Altitude data is empty."); return
        window = 11
        if len(self.altitude) < window: QMessageBox.warning(self, "Warning", f"Not enough data points ({len(self.altitude)}) for rolling window {window}."); return
        self._common_plot_settings("GPS Data (Rolling Average)")
        x = self.altitude.rolling(window=window, center=True, min_periods=1).mean().values
        y = self.temperature.rolling(window=window, center=True, min_periods=1).mean().values
        self.add_line_and_scatter(x, y, 'c', f"Rolling Avg ({window})")
        print(f"GPS Rolling Plot: Plotted rolling average.")

    def plot_savgol(self):
        if self.df is None or self.altitude is None or self.temperature is None: print("GPS SavGol Plot: Data not loaded."); return
        if self.altitude.empty: print("GPS SavGol Plot: Altitude data is empty."); return
        window, poly = 11, 2
        if window % 2 == 0: window += 1
        if len(self.altitude) <= window: QMessageBox.warning(self, "Warning", f"Not enough data points ({len(self.altitude)}) for Savitzky-Golay window {window}. Required > {window}."); return
        if poly >= window: QMessageBox.warning(self, "Warning", f"Polynomial order ({poly}) must be less than window length ({window}) for Savitzky-Golay."); return

        self._common_plot_settings("GPS Data (Savitzky-Golay)")
        try:
            if self.altitude.isnull().any() or self.temperature.isnull().any():
                 print("Warning: NaNs detected in data before SavGol. Filtering again.")
                 valid_mask = self.altitude.notna() & self.temperature.notna()
                 alt_clean = self.altitude[valid_mask].values
                 temp_clean = self.temperature[valid_mask].values
                 tooltips_clean = [self.tooltip_data[i] for i, valid in enumerate(valid_mask) if valid]
                 if len(alt_clean) <= window: QMessageBox.warning(self, "Warning", f"Not enough data points ({len(alt_clean)}) for Savitzky-Golay window {window} after cleaning NaNs."); return
            else:
                 alt_clean = self.altitude.values; temp_clean = self.temperature.values; tooltips_clean = self.tooltip_data

            x = savgol_filter(alt_clean, window_length=window, polyorder=poly)
            y = savgol_filter(temp_clean, window_length=window, polyorder=poly)
            self.tooltip_data = tooltips_clean
            self.add_line_and_scatter(x, y, 'y', f"Sav-Gol ({window},{poly})")
            print(f"GPS SavGol Plot: Plotted Savitzky-Golay filtered data.")
        except ValueError as e: QMessageBox.critical(self, "Sav-Gol Error", f"Error applying Savitzky-Golay filter: {e}")
        except Exception as e: import traceback; print(traceback.format_exc()); QMessageBox.critical(self, "Sav-Gol Error", f"Unexpected error during Savitzky-Golay: {e}")

    def save_plot(self):
        if not self.plot_widget.plotItem.items: QMessageBox.warning(self, "Cannot Save", "No plot data to save."); return
        suggested_filename = f"gps_plot_{os.path.splitext(os.path.basename(self.file_path))[0]}.png"
        file_path, _ = QFileDialog.getSaveFileName(self, "Save GPS Plot", suggested_filename, "PNG Files (*.png);;JPEG Files (*.jpg);;All Files (*)")
        if file_path:
            try:
                exporter = ImageExporter(self.plot_widget.plotItem)
                exporter.parameters()['width'] = 1920
                exporter.export(file_path)
                QMessageBox.information(self, "Success", f"Plot saved as {file_path}")
            except Exception as e: import traceback; print(traceback.format_exc()); QMessageBox.critical(self, "Save Error", f"Could not save plot: {e}")


# ---------------------------
# PressureDataTab
# ---------------------------
class PressureDataTab(QWidget):
    # (PressureDataTab code remains unchanged from previous version)
    def __init__(self, file_path, press_index, temp_index, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.press_index = press_index
        self.temp_index = temp_index
        self.df = None
        self.pressure = None
        self.temperature = None
        self.tooltip_data = []
        self.layout = QVBoxLayout()
        input_layout = QHBoxLayout()
        self.label_P0 = QLabel("Sea Level Pressure P₀ (hPa):")
        self.edit_P0 = QLineEdit("1013.25")
        self.edit_P0.setValidator(QIntValidator(800, 1200, self))
        self.edit_P0.setToolTip("Standard sea level pressure is 1013.25 hPa")
        self.label_T0 = QLabel("Sea Level Temperature T₀ (°C):")
        self.edit_T0 = QLineEdit("15")
        self.edit_T0.setValidator(QIntValidator(-50, 50, self))
        self.edit_T0.setToolTip("Standard sea level temperature is 15 °C")
        input_layout.addWidget(self.label_P0); input_layout.addWidget(self.edit_P0)
        input_layout.addSpacing(20)
        input_layout.addWidget(self.label_T0); input_layout.addWidget(self.edit_T0)
        input_layout.addStretch(1)
        self.layout.addLayout(input_layout)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.plot_widget.setBackground('k')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.layout.addWidget(self.plot_widget)
        btn_layout = QHBoxLayout()
        self.btn_raw = QPushButton("Calculate & Plot Raw")
        self.btn_rolling = QPushButton("Rolling Average (11)")
        self.btn_savgol = QPushButton("Savitzky-Golay (11, 2)")
        self.btn_save = QPushButton("Save Plot")
        btn_layout.addWidget(self.btn_raw); btn_layout.addWidget(self.btn_rolling); btn_layout.addWidget(self.btn_savgol)
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.btn_save)
        self.layout.addLayout(btn_layout)
        self.setLayout(self.layout)
        self.btn_raw.clicked.connect(self.plot_raw)
        self.btn_rolling.clicked.connect(self.plot_rolling)
        self.btn_savgol.clicked.connect(self.plot_savgol)
        self.btn_save.clicked.connect(self.save_plot)
        self.edit_P0.textChanged.connect(self.replot_current)
        self.edit_T0.textChanged.connect(self.replot_current)
        self.current_plot_type = 'raw'
        self.load_data()
        if self.df is not None:
             self.plot_raw()

    def load_data(self):
        if not os.path.exists(self.file_path):
             QMessageBox.critical(self, "Error", f"File not found: {self.file_path}"); self.df = None; return
        try:
            try:
                 self.df = pd.read_csv(self.file_path, low_memory=False)
                 if self.press_index >= len(self.df.columns) or self.temp_index >= len(self.df.columns):
                      print(f"Warning: Indices ({self.press_index},{self.temp_index}) seem out of bounds for columns {list(self.df.columns)}. Trying without header.")
                      raise IndexError("Index out of bounds with header")
                 press_col_name = self.df.columns[self.press_index]; temp_col_name = self.df.columns[self.temp_index]
                 print(f"Pressure Tab: Using columns '{press_col_name}' (idx {self.press_index}) for Press, '{temp_col_name}' (idx {self.temp_index}) for Temp.")
                 self.pressure = pd.to_numeric(self.df.iloc[:, self.press_index], errors='coerce')
                 self.temperature = pd.to_numeric(self.df.iloc[:, self.temp_index], errors='coerce')
                 self.tooltip_data = [row.to_dict() for _, row in self.df.iterrows()]
            except (IndexError, ValueError, pd.errors.ParserError, TypeError):
                 print(f"Info: Reading Pressure file '{os.path.basename(self.file_path)}' assuming no header.")
                 self.df = pd.read_csv(self.file_path, header=None, low_memory=False)
                 if self.press_index >= len(self.df.columns) or self.temp_index >= len(self.df.columns):
                     raise IndexError(f"Index out of bounds ({max(self.press_index, self.temp_index)}) for {len(self.df.columns)} columns (no header).")
                 self.pressure = pd.to_numeric(self.df.iloc[:, self.press_index], errors='coerce')
                 self.temperature = pd.to_numeric(self.df.iloc[:, self.temp_index], errors='coerce')
                 self.tooltip_data = [ {f'col_{i}': val for i, val in row.items() } for _, row in self.df.iterrows()]

            initial_rows = len(self.df)
            valid_mask = self.pressure.notna() & self.temperature.notna()
            self.pressure = self.pressure[valid_mask].reset_index(drop=True)
            self.temperature = self.temperature[valid_mask].reset_index(drop=True)
            self.tooltip_data = [self.tooltip_data[i] for i, valid in enumerate(valid_mask) if valid]
            print(f"Pressure Tab: Kept {len(self.pressure)} rows out of {initial_rows} after removing NaNs in Press/Temp columns.")

            if not (self.pressure > 0).all(): print(f"Warning: Found non-positive pressure values. Count: {(self.pressure <= 0).sum()}. These will likely result in NaN altitude.")
            if not ((self.pressure > 50) & (self.pressure < 1100)).all():
                extreme_pressures = self.pressure[(self.pressure <= 50) | (self.pressure >= 1100)]
                print(f"Warning: Found {len(extreme_pressures)} pressure values outside typical range (50-1100 hPa). Min: {self.pressure.min()}, Max: {self.pressure.max()}.")
            if self.pressure.empty or self.temperature.empty: raise ValueError("No valid numeric data found in specified pressure/temperature columns after cleaning.")

        except FileNotFoundError: QMessageBox.critical(self, "Error", f"File not found: {self.file_path}"); self.df = None
        except IndexError as e: QMessageBox.critical(self, "Error", f"Column index error loading Pressure data: {e}\nFile: {os.path.basename(self.file_path)}\nIndices: Press={self.press_index}, Temp={self.temp_index}"); self.df = None
        except ValueError as e: QMessageBox.critical(self, "Error", f"Data type error loading Pressure data: {e}\nFile: {os.path.basename(self.file_path)}\nIndices: Press={self.press_index}, Temp={self.temp_index}"); self.df = None
        except Exception as e: import traceback; print(traceback.format_exc()); QMessageBox.critical(self, "Error", f"An unexpected error occurred loading Pressure data:\n{e}\nFile: {os.path.basename(self.file_path)}"); self.df = None

    def compute_altitude(self, P0_hPa, T0_C):
        if self.pressure is None or self.pressure.empty: print("Compute Altitude: Pressure data is missing or empty."); return None
        P0_Pa = P0_hPa * 100.0; T0_K = T0_C + 273.15; L = 0.0065; R = 8.314462618; g = 9.80665; M = 0.0289644
        pressure_Pa = self.pressure * 100.0
        exponent = (R * L) / (g * M)
        if P0_Pa <= 0: print("Error: Sea Level Pressure P0 must be positive."); return pd.Series(np.nan, index=self.pressure.index)
        pressure_ratio = pressure_Pa / P0_Pa
        with np.errstate(invalid='ignore'): altitude = (T0_K / L) * (1 - np.power(pressure_ratio.astype(float), exponent))
        nan_count = pd.isna(altitude).sum()
        if nan_count > 0: print(f"Compute Altitude: Generated {nan_count} NaN values, likely due to invalid pressure ratios (e.g., P <= 0 or P/P0 <= 0).")
        return altitude

    def add_line_and_scatter(self, x, y, color, name):
        x_np = np.array(x, dtype=float); y_np = np.array(y, dtype=float)
        valid_indices = ~np.isnan(x_np) & ~np.isnan(y_np)
        x_plot = x_np[valid_indices]; y_plot = y_np[valid_indices]
        if len(x_plot) == 0: print(f"Warning: No valid (non-NaN) points to plot for '{name}'."); return

        line_item = pg.PlotDataItem(x_plot, y_plot, pen=pg.mkPen(color=color, width=2), name=name)
        self.plot_widget.addItem(line_item)

        if len(self.tooltip_data) == len(x_np):
            filtered_tooltip_data = [self.tooltip_data[i] for i, valid in enumerate(valid_indices) if valid]
            if filtered_tooltip_data:
                 scatter = HoverScatterPlotItem(x=x_plot, y=y_plot, data_list=filtered_tooltip_data,
                                                size=8, brush=pg.mkBrush(color), name=name + " Points")
                 self.plot_widget.addItem(scatter)
            else: print(f"Warning: No valid data points to scatter plot for '{name}' (check tooltip filtering).")
        else: print(f"Warning: Tooltip data length ({len(self.tooltip_data)}) mismatch with data length ({len(x_np)}). Skipping scatter plot hover for '{name}'.")

    def _get_p0_t0(self):
        try:
            P0_str = self.edit_P0.text(); T0_str = self.edit_T0.text()
            if not P0_str or not T0_str: print("Warning: P0 or T0 field is empty."); return None, None
            P0 = float(P0_str); T0 = float(T0_str)
            if not (800 <= P0 <= 1200): print(f"Warning: P0 value {P0} is outside typical range (800-1200 hPa).")
            if not (-70 <= T0 <= 60): print(f"Warning: T0 value {T0} is outside typical range (-70 to 60 °C).")
            return P0, T0
        except ValueError: print("Warning: Invalid numeric input for P0 or T0."); return None, None

    def _common_plot_settings(self, title):
        self.plot_widget.clear()
        self.plot_widget.addLegend(offset=(10, 10), labelTextColor='w')
        label_style = {'color': '#FFF', 'font-size': '12pt'}
        self.plot_widget.setLabel("left", "Temperature (°C)", units='°C', **label_style)
        self.plot_widget.setLabel("bottom", "Calculated Altitude (m)", units='m', **label_style)
        self.plot_widget.setTitle(title + f" - {os.path.basename(self.file_path)}", color='w', size='14pt')
        axis_pen = pg.mkPen(color=(200, 200, 200))
        self.plot_widget.getAxis('left').setPen(axis_pen); self.plot_widget.getAxis('left').setTextPen(axis_pen)
        self.plot_widget.getAxis('bottom').setPen(axis_pen); self.plot_widget.getAxis('bottom').setTextPen(axis_pen)

    def replot_current(self):
        if self.current_plot_type == 'raw': self.plot_raw()
        elif self.current_plot_type == 'rolling': self.plot_rolling()
        elif self.current_plot_type == 'savgol': self.plot_savgol()

    def plot_raw(self):
        self.current_plot_type = 'raw'
        if self.df is None or self.pressure is None or self.temperature is None: print("Pressure Raw Plot: Data not loaded."); return
        if self.pressure.empty: print("Pressure Raw Plot: Pressure data is empty."); return
        P0, T0 = self._get_p0_t0()
        if P0 is None or T0 is None: return
        alt = self.compute_altitude(P0, T0)
        if alt is None: return
        self._common_plot_settings(f"Pressure Based Altitude (Raw, P₀={P0}, T₀={T0})")
        self.add_line_and_scatter(alt.values, self.temperature.values, 'r', "Raw Data")
        print(f"Pressure Raw Plot: Plotted {len(alt)} points.")

    def plot_rolling(self):
        self.current_plot_type = 'rolling'
        if self.df is None or self.pressure is None or self.temperature is None: print("Pressure Rolling Plot: Data not loaded."); return
        if self.pressure.empty: print("Pressure Rolling Plot: Pressure data is empty."); return
        P0, T0 = self._get_p0_t0()
        if P0 is None or T0 is None: return
        alt = self.compute_altitude(P0, T0)
        if alt is None: return
        window = 11
        valid_alt_count = alt.notna().sum()
        if valid_alt_count < window: QMessageBox.warning(self, "Warning", f"Not enough valid calculated altitude points ({valid_alt_count}) for rolling window {window}."); return
        self._common_plot_settings(f"Pressure Based Altitude (Rolling Avg, P₀={P0}, T₀={T0})")
        alt_roll = alt.rolling(window=window, center=True, min_periods=1).mean()
        temp_roll = self.temperature.rolling(window=window, center=True, min_periods=1).mean()
        self.add_line_and_scatter(alt_roll.values, temp_roll.values, 'c', f"Rolling Avg ({window})")
        print("Pressure Rolling Plot: Plotted rolling average.")

    def plot_savgol(self):
        self.current_plot_type = 'savgol'
        if self.df is None or self.pressure is None or self.temperature is None: print("Pressure SavGol Plot: Data not loaded."); return
        if self.pressure.empty: print("Pressure SavGol Plot: Pressure data is empty."); return
        P0, T0 = self._get_p0_t0()
        if P0 is None or T0 is None: return
        alt = self.compute_altitude(P0, T0)
        if alt is None: return

        window, poly = 11, 2
        valid_mask = alt.notna() & self.temperature.notna()
        alt_clean = alt[valid_mask].values; temp_clean = self.temperature[valid_mask].values
        tooltips_clean = [self.tooltip_data[i] for i, valid in enumerate(valid_mask) if valid]
        if window % 2 == 0: window += 1
        if len(alt_clean) <= window: QMessageBox.warning(self, "Warning", f"Not enough valid data points ({len(alt_clean)}) for Savitzky-Golay window {window} after cleaning NaNs."); return
        if poly >= window: QMessageBox.warning(self, "Warning", f"Polynomial order ({poly}) must be less than window length ({window}) for Savitzky-Golay."); return

        self._common_plot_settings(f"Pressure Based Altitude (Sav-Gol, P₀={P0}, T₀={T0})")
        try:
            alt_savgol = savgol_filter(alt_clean, window_length=window, polyorder=poly)
            temp_savgol = savgol_filter(temp_clean, window_length=window, polyorder=poly)
            self.tooltip_data = tooltips_clean
            self.add_line_and_scatter(alt_savgol, temp_savgol, 'y', f"Sav-Gol ({window},{poly})")
            print("Pressure SavGol Plot: Plotted Savitzky-Golay filtered data.")
        except ValueError as e: QMessageBox.critical(self, "Sav-Gol Error", f"Error applying Savitzky-Golay filter: {e}")
        except Exception as e: import traceback; print(traceback.format_exc()); QMessageBox.critical(self, "Sav-Gol Error", f"Unexpected error during Savitzky-Golay: {e}")

    def save_plot(self):
        if not self.plot_widget.plotItem.items: QMessageBox.warning(self, "Cannot Save", "No plot data to save."); return
        P0, T0 = self._get_p0_t0()
        p0_str = f"P0{P0}" if P0 is not None else "P0_unknown"
        t0_str = f"T0{T0}" if T0 is not None else "T0_unknown"
        suggested_filename = f"pressure_alt_plot_{os.path.splitext(os.path.basename(self.file_path))[0]}_{p0_str}_{t0_str}.png"
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Pressure Altitude Plot", suggested_filename, "PNG Files (*.png);;JPEG Files (*.jpg);;All Files (*)")
        if file_path:
            try:
                exporter = ImageExporter(self.plot_widget.plotItem)
                exporter.parameters()['width'] = 1920
                exporter.export(file_path)
                QMessageBox.information(self, "Success", f"Plot saved as {file_path}")
            except Exception as e: import traceback; print(traceback.format_exc()); QMessageBox.critical(self, "Save Error", f"Could not save plot: {e}")


# ---------------------------
# OuterTab
# ---------------------------
class OuterTab(QWidget):
    # (OuterTab code remains unchanged from previous version)
    def __init__(self, file_path, gps_alt_index, gps_temp_index, press_index, press_temp_index, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(2,2,2,2)
        self.nested_tabs = QTabWidget()
        self.nested_tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        if not os.path.exists(file_path):
             error_label = QLabel(f"Error: Data file not found!\nExpected at: {file_path}")
             error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
             self.layout.addWidget(error_label)
             print(f"Error: File not found for OuterTab: {file_path}")
        else:
             print(f"Info: Creating OuterTab for file: {file_path}")
             self.gps_tab = GPSDataTab(file_path, gps_alt_index, gps_temp_index)
             self.nested_tabs.addTab(self.gps_tab, "GPS Altitude vs Temp")
             self.pressure_tab = PressureDataTab(file_path, press_index, press_temp_index)
             self.nested_tabs.addTab(self.pressure_tab, "Pressure Altitude vs Temp")
             self.layout.addWidget(self.nested_tabs)
        self.setLayout(self.layout)


# --- Start of Google Maps MapGenerationTab code ---

API_KEY = "AIzaSyBwbh8kAT2ou6FElnqaFJ9d6JpJ-bko_2M" # Replace with your actual key

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
  <head>
    <title>Heatmap</title>
    <meta name="viewport" content="initial-scale=1.0">
    <meta charset="utf-8">
    <style>
      html, body, #map {{
        height: 100%;
        margin: 0;
        padding: 0;
      }}
    </style>
    <script src="https://maps.googleapis.com/maps/api/js?key={api_key}&libraries=visualization"></script>
    <script>
      var heatmapData = {heatmap_data};
      function initMap() {{
        var mapCenter = {{lat: {center_lat}, lng: {center_lon}}};
        var map = new google.maps.Map(document.getElementById('map'), {{
          zoom: 8,
          center: mapCenter,
          mapTypeId: 'satellite',
          tilt: 45
        }});
        var heatmap = new google.maps.visualization.HeatmapLayer({{
          data: heatmapData.map(function(point) {{
            if (point && typeof point[0] === 'number' && typeof point[1] === 'number') {{
                 return new google.maps.LatLng(point[0], point[1]);
            }} else {{
                 console.warn("Invalid point data skipped:", point);
                 return null;
            }}
          }}).filter(p => p !== null),
          radius: 20,
          blur: 10,
          gradient: [ // Rainbow gradient
            'rgba(0, 0, 255, 0)',     // Transparent Blue
            'rgba(0, 0, 255, 1)',     // Blue
            'rgba(0, 255, 255, 1)',   // Cyan
            'rgba(0, 255, 0, 1)',     // Green
            'rgba(255, 255, 0, 1)',   // Yellow
            'rgba(255, 0, 0, 1)'      // Red
          ]
        }});
        heatmap.setMap(map);
      }}
    </script>
  </head>
  <body onload="initMap()">
    <div id="map"></div>
  </body>
</html>
"""

class MapGenerationTab(QWidget):
    def __init__(self, map_view, parent=None):
        super().__init__(parent)
        self.map_view = map_view
        self.selected_file_path = None
        self._init_ui_elements()
        self._setup_layout()
        self._connect_signals()
        self.apply_styles() # Call the (now modified) styles method

    def _init_ui_elements(self):
        # --- Use standard Qt elements, styling removed ---
        self.btn_select_file = QPushButton('1. Select CSV for Mapping')
        # self.btn_select_file.setObjectName("selectButtonMap") # Object names are for styling
        self.btn_select_file.setToolTip("Select CSV with Latitude/Longitude columns")

        self.lbl_file_path = QLabel('<i>No file selected.</i>')
        self.lbl_file_path.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_file_path.setWordWrap(True)
        # self.lbl_file_path.setObjectName("filePathLabelMap")

        # Use QFont for bold instead of HTML tag if preferred for consistency without stylesheets
        self.input_section_label = QLabel("Specify Coordinate Column Indices (0-based)")
        font = QFont(); font.setBold(True); self.input_section_label.setFont(font)
        # self.input_section_label = QLabel("<b>2. Specify Coordinate Column Indices</b> (0-based)") # HTML bold

        self.lat_label = QLabel('Latitude:')
        self.lat_col_input = QLineEdit("4")
        self.lat_col_input.setValidator(QIntValidator(0, 999, self))
        self.lat_col_input.setToolTip("0-based index for Latitude")
        self.lat_col_input.setFixedWidth(50) # Keep fixed width for layout

        self.lon_label = QLabel('Longitude:')
        self.lon_col_input = QLineEdit("5")
        self.lon_col_input.setValidator(QIntValidator(0, 999, self))
        self.lon_col_input.setToolTip("0-based index for Longitude")
        self.lon_col_input.setFixedWidth(50) # Keep fixed width for layout

        self.btn_generate_maps = QPushButton('3. Generate Heatmap')
        # self.btn_generate_maps.setObjectName("generateButtonMap")
        self.btn_generate_maps.setToolTip("Generate Google Maps heatmap from CSV data")
        self.btn_generate_maps.setEnabled(False)

        self.lbl_status = QLabel('')
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # self.lbl_status.setObjectName("statusLabelMap")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setMinimumHeight(40) # Keep minimum height

    def _setup_layout(self):
        # Layout setup remains the same logically
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12) # Keep spacing
        main_layout.setContentsMargins(15, 15, 15, 15) # Adjust margins if needed for default look

        fs_layout = QHBoxLayout()
        fs_layout.addWidget(self.btn_select_file)
        fs_layout.addWidget(self.lbl_file_path, 1)
        main_layout.addLayout(fs_layout)

        # Keep structure but styling comes from default/global stylesheet
        input_group_box = QWidget()
        input_group_layout = QVBoxLayout(input_group_box)
        input_group_layout.setContentsMargins(0, 5, 0, 5)
        input_group_layout.addWidget(self.input_section_label)

        input_fields_layout = QHBoxLayout()
        input_fields_layout.setSpacing(15)
        lat_widget = QWidget(); lat_layout = QHBoxLayout(lat_widget); lat_layout.setContentsMargins(0, 0, 0, 0)
        lat_layout.addWidget(self.lat_label); lat_layout.addWidget(self.lat_col_input); lat_layout.addStretch()
        lon_widget = QWidget(); lon_layout = QHBoxLayout(lon_widget); lon_layout.setContentsMargins(0, 0, 0, 0)
        lon_layout.addWidget(self.lon_label); lon_layout.addWidget(self.lon_col_input); lon_layout.addStretch()
        input_fields_layout.addWidget(lat_widget)
        input_fields_layout.addWidget(lon_widget)
        input_group_layout.addLayout(input_fields_layout)
        main_layout.addWidget(input_group_box)

        # Center button using layout, button appearance is default
        btn_hbox = QHBoxLayout()
        btn_hbox.addStretch(1)
        btn_hbox.addWidget(self.btn_generate_maps)
        btn_hbox.addStretch(1)
        main_layout.addLayout(btn_hbox)

        # Status label appearance is default
        main_layout.addWidget(self.lbl_status)
        main_layout.addStretch(1)

    def _connect_signals(self):
        self.btn_select_file.clicked.connect(self.select_file)
        self.btn_generate_maps.clicked.connect(self.generate_heatmap)

    def apply_styles(self):
        # --- STYLING REMOVED ---
        # Remove the setStyleSheet call to inherit default/global styles
        # self.setStyleSheet(""" ... specific styles ... """)
        pass # Now this method does nothing, so the widget uses default styles

    def select_file(self):
        # (select_file logic remains unchanged)
        start_dir = os.path.expanduser("~")
        fname, _ = QFileDialog.getOpenFileName(self, 'Select CSV File for Mapping', start_dir, "CSV Files (*.csv)")
        if fname:
            self.selected_file_path = fname
            display_name = os.path.basename(fname)
            self.lbl_file_path.setText(f"Selected: <b>{display_name}</b>") # HTML bold is fine here
            self.lbl_file_path.setToolTip(self.selected_file_path)
            self.btn_generate_maps.setEnabled(True)
            self.set_status('')
            try:
                 df_head = pd.read_csv(fname, nrows=5, header=0)
                 cols = [c.lower().strip() for c in df_head.columns]
                 found_lat, found_lon = False, False
                 if 'latitude' in cols: self.lat_col_input.setText(str(cols.index('latitude'))); found_lat=True
                 elif 'lat' in cols: self.lat_col_input.setText(str(cols.index('lat'))); found_lat=True
                 if 'longitude' in cols: self.lon_col_input.setText(str(cols.index('longitude'))); found_lon=True
                 elif 'lon' in cols: self.lon_col_input.setText(str(cols.index('lon'))); found_lon=True
                 elif 'lng' in cols: self.lon_col_input.setText(str(cols.index('lng'))); found_lon=True
                 if not (found_lat and found_lon): self.lat_col_input.setText("4"); self.lon_col_input.setText("5")
            except Exception:
                 print("Info: Could not auto-detect columns or file has no header. Using defaults.")
                 self.lat_col_input.setText("4"); self.lon_col_input.setText("5")
        else:
            if not self.selected_file_path:
                self.lbl_file_path.setText('<i>No file selected.</i>')
                self.lbl_file_path.setToolTip('')
                self.btn_generate_maps.setEnabled(False)

    def set_status(self, message, is_error=False):
        # Keep status label styling for feedback, or remove if truly default is desired
        self.lbl_status.setText(message)
        # Option 1: Keep styled feedback
        style_sheet = "padding: 8px; border-radius: 4px; color: {color}; background-color: {bg_color}; border: 1px solid {border_color};"
        if is_error:
            self.lbl_status.setStyleSheet(style_sheet.format(color="#a94442", bg_color="#f2dede", border_color="#ebccd1")) # Reddish error
        elif "Success" in message:
            self.lbl_status.setStyleSheet(style_sheet.format(color="#3c763d", bg_color="#dff0d8", border_color="#d6e9c6")) # Greenish success
        elif message: # Info message
            self.lbl_status.setStyleSheet(style_sheet.format(color="#31708f", bg_color="#d9edf7", border_color="#bce8f1")) # Bluish info
        else: # Clear
             # Revert to default background/border
             self.lbl_status.setStyleSheet("") # Clears specific stylesheet

        # Option 2: Remove all styling (use default label appearance)
        # if is_error: self.lbl_status.setText(f"Error: {message}")
        # elif "Success" in message: self.lbl_status.setText(f"Success: {message}")
        # else: self.lbl_status.setText(message)
        # self.lbl_status.setStyleSheet("") # Ensure no lingering styles

        QApplication.processEvents()

    def generate_heatmap(self):
        # (generate_heatmap logic remains unchanged)
        if not self.selected_file_path:
            QMessageBox.warning(self, "File Not Selected", "Please select a CSV file first.")
            return

        lat_index_str = self.lat_col_input.text()
        lon_index_str = self.lon_col_input.text()
        try:
            if not lat_index_str or not lon_index_str: raise ValueError("Indices required.")
            lat_index = int(lat_index_str); lon_index = int(lon_index_str)
            if lat_index < 0 or lon_index < 0: raise ValueError("Indices must be non-negative.")
            if lat_index == lon_index: raise ValueError("Latitude and Longitude indices must differ.")
        except ValueError as e:
            self.set_status(f"Input Error: {e}", True)
            QMessageBox.critical(self, "Invalid Input", f"Invalid column index: {e}")
            return

        self.set_status("Processing... Reading CSV.")
        QApplication.processEvents()
        try:
            df = None; latitude_col = None; longitude_col = None
            try:
                df_hdr = pd.read_csv(self.selected_file_path, delimiter=",", header=0, on_bad_lines='warn', low_memory=False)
                max_index = max(lat_index, lon_index)
                if df_hdr.shape[1] <= max_index:
                     print(f"MapGen: Index {max_index} out of bounds with header=0 ({df_hdr.shape[1]} cols), trying header=None.")
                     raise IndexError
                df = df_hdr
                print("MapGen: Reading CSV with header=0.")
                latitude_col = pd.to_numeric(df.iloc[:, lat_index].astype(str).str.strip(), errors='coerce')
                longitude_col = pd.to_numeric(df.iloc[:, lon_index].astype(str).str.strip(), errors='coerce')
            except (IndexError, Exception) as e_hdr:
                print(f"MapGen: Failed reading with header=0 ({e_hdr}), trying header=None.")
                try:
                     df_no_hdr = pd.read_csv(self.selected_file_path, delimiter=",", header=None, on_bad_lines='warn', low_memory=False)
                     max_index = max(lat_index, lon_index)
                     if df_no_hdr.shape[1] <= max_index:
                         raise IndexError(f"Index ({max_index}) is out of bounds. File has only {df_no_hdr.shape[1]} columns (no header).")
                     df = df_no_hdr
                     print("MapGen: Reading CSV with header=None.")
                     latitude_col = pd.to_numeric(df.iloc[:, lat_index].astype(str).str.strip(), errors='coerce')
                     longitude_col = pd.to_numeric(df.iloc[:, lon_index].astype(str).str.strip(), errors='coerce')
                except Exception as e_no_hdr:
                    err_msg = f"Error reading CSV: Tried with/without header.\nHeader=0 Error: {e_hdr}\nHeader=None Error: {e_no_hdr}"
                    self.set_status(err_msg, True)
                    QMessageBox.critical(self, "CSV Read Error", f"Could not read CSV file with or without header. Please check format and indices.\n\nDetails:\n{err_msg}")
                    return

            if df is None or latitude_col is None or longitude_col is None:
                 raise ValueError("Failed to load coordinate data from CSV.")

            self.set_status("Processing... Extracting coordinates.")
            valid_coords_df = pd.DataFrame({'lat': latitude_col, 'lon': longitude_col}).dropna()

            if valid_coords_df.empty:
                raise ValueError(f"No valid numeric coordinate pairs found in columns {lat_index} (Lat) and {lon_index} (Lon) after cleaning. Check data and indices.")

            coordinates = list(zip(valid_coords_df['lat'], valid_coords_df['lon']))
            center_lat = valid_coords_df['lat'].mean() if not valid_coords_df.empty else 0
            center_lon = valid_coords_df['lon'].mean() if not valid_coords_df.empty else 0
            num_coords = len(coordinates)

            self.set_status(f"Processing... Found {num_coords} points. Generating heatmap.")

            serializable_coordinates = []
            for lat, lon in coordinates:
                 if np.isfinite(lat) and np.isfinite(lon):
                     serializable_coordinates.append([lat, lon])
                 else:
                     print(f"Warning: Skipping non-finite coordinate pair: Lat={lat}, Lon={lon}")

            if not serializable_coordinates:
                 raise ValueError("No valid finite coordinates remaining after filtering.")

            heatmap_data = json.dumps(serializable_coordinates)

            html_content = HTML_TEMPLATE.format(
                api_key=API_KEY,
                heatmap_data=heatmap_data,
                center_lat=center_lat,
                center_lon=center_lon
            )

            output_dir = os.path.dirname(self.selected_file_path)
            base_filename = os.path.splitext(os.path.basename(self.selected_file_path))[0]
            html_file_path = os.path.join(output_dir, f"{base_filename}_google_heatmap.html")
            try:
                 with open(html_file_path, "w", encoding="utf-8") as file: file.write(html_content)
                 print(f"Google heatmap HTML saved to: {html_file_path}")
            except Exception as e_save: print(f"Warning: Could not save HTML file: {e_save}")

            self.map_view.setHtml(html_content, QUrl.fromLocalFile(os.path.abspath(self.selected_file_path)))

            self.set_status(f"Success: Heatmap generated for {len(serializable_coordinates)} points and displayed.", is_error=False) # Explicitly False

        except FileNotFoundError:
            err_msg = f"File not found:\n{self.selected_file_path}"
            self.set_status(err_msg, True); QMessageBox.critical(self, "File Not Found", err_msg)
            self.reset_selection()
        except pd.errors.EmptyDataError:
            err_msg = f"The selected CSV file is empty:\n{os.path.basename(self.selected_file_path)}"
            self.set_status(err_msg, True); QMessageBox.critical(self, "Empty File", err_msg)
            self.reset_selection()
        except (pd.errors.ParserError, ValueError) as e:
            err_msg = f"Error processing file data:\n{e}"
            self.set_status(err_msg, True); QMessageBox.critical(self, "Data Processing Error", err_msg)
        except MemoryError:
            err_msg = "Memory Error: The file is too large to process."
            self.set_status(err_msg, True); QMessageBox.critical(self, "Memory Error", err_msg)
        except (IndexError, KeyError) as e:
            err_msg = f"Column Index Error: {e}\nVerify columns {lat_index} (Lat) / {lon_index} (Lon) exist."
            self.set_status(err_msg, True); QMessageBox.critical(self, "Column Index Error", err_msg)
        except Exception as e:
            err_msg = f"An unexpected error occurred:\n{e}"
            self.set_status(err_msg, True)
            import traceback; print("--- Map Generation Unexpected Error ---"); print(traceback.format_exc()); print("---")
            QMessageBox.critical(self, "Unexpected Error", err_msg)

    def reset_selection(self):
        self.selected_file_path = None
        self.lbl_file_path.setText('<i>No file selected.</i>')
        self.lbl_file_path.setToolTip('')
        self.btn_generate_maps.setEnabled(False)
        self.set_status("") # Clear status message
        self.map_view.setHtml("<html><body><p>Select a CSV file and generate a heatmap.</p></body></html>")

# --- End of Google Maps MapGenerationTab code ---


# ---------------------------
# FourthStepWindow
# ---------------------------
class FourthStepWindow(BackgroundWidget):
    # (FourthStepWindow code remains unchanged from previous version)
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.setWindowTitle("Step Four: Data Analysis and Mapping")
        self.setMinimumSize(950, 750)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)

        self.outer_tabs = QTabWidget()
        self.outer_tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        data_dir = "."
        rs_file = os.path.join(data_dir, "Reed_Solomon_Decoded_Message.csv")
        bcjr_file = os.path.join(data_dir, "BCJR_Output_clean.csv")
        map_file = os.path.join(data_dir, "MAP_Output_clean.csv")
        sova_file = os.path.join(data_dir, "SOVA_Output_clean.csv")
        hybrid_file = os.path.join(data_dir, "HYBRID_Output_clean.csv")

        reed_solomon_tab = OuterTab(rs_file, gps_alt_index=10, gps_temp_index=13, press_index=12, press_temp_index=13)
        bcjr_tab = OuterTab(bcjr_file, gps_alt_index=8, gps_temp_index=11, press_index=10, press_temp_index=11)
        map_dec_tab = OuterTab(map_file, gps_alt_index=8, gps_temp_index=11, press_index=10, press_temp_index=11)
        sova_tab = OuterTab(sova_file, gps_alt_index=8, gps_temp_index=11, press_index=10, press_temp_index=11)
        hybrid_tab = OuterTab(hybrid_file, gps_alt_index=8, gps_temp_index=11, press_index=10, press_temp_index=11)

        self.outer_tabs.addTab(reed_solomon_tab, "Reed-Solomon Analysis")
        self.outer_tabs.addTab(bcjr_tab, "BCJR Analysis")
        self.outer_tabs.addTab(map_dec_tab, "MAP Analysis")
        self.outer_tabs.addTab(sova_tab, "SOVA Analysis")
        self.outer_tabs.addTab(hybrid_tab, "HYBRID Analysis")

        self.map_tab_container = QWidget()
        map_tab_layout = QHBoxLayout(self.map_tab_container)
        map_tab_layout.setContentsMargins(0, 0, 0, 0)
        map_tab_layout.setSpacing(0)

        self.map_web_view = QWebEngineView()
        self.map_web_view.setMinimumSize(400, 400)
        self.map_web_view.setHtml("<html><body><p style='padding:20px; font-family: sans-serif; color: #555;'>Select a CSV file using the panel on the left and click 'Generate Heatmap' to view the Google Map.</p></body></html>")

        self.map_controls = MapGenerationTab(self.map_web_view)
        self.map_controls.setFixedWidth(350) # Keep fixed width for layout stability

        map_tab_layout.addWidget(self.map_controls)
        map_tab_layout.addWidget(self.map_web_view, 1)

        self.outer_tabs.addTab(self.map_tab_container, "Google Heatmap")

        self.layout.addWidget(self.outer_tabs)


# Main execution block
if __name__ == "__main__":
    if hasattr(Qt.ApplicationAttribute, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    # Optional: Define a global stylesheet if you want a consistent look
    # app.setStyleSheet("""
    #     QPushButton { padding: 5px 10px; }
    #     QLineEdit { padding: 3px; }
    #     /* Add more global styles */
    # """)

    window = FourthStepWindow()
    window.show()
    sys.exit(app.exec())
