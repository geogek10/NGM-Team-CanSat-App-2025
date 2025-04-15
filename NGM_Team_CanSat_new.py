import sys
import csv
import re
import os
import subprocess
import shutil
import pandas as pd
import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter
from scipy.signal import savgol_filter
import numpy as np
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QPainter, QPixmap, QIcon
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout,
    QFileDialog, QLabel, QMessageBox, QHBoxLayout, QInputDialog, QMainWindow, QLineEdit
)

# Ορισμός ελάχιστου πλήθους στηλών για πλήρη γραμμή
MIN_VALID_COLUMNS = 8

# --- BackgroundWidget ---
class BackgroundWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.background_image = QPixmap("NGM--MONOCHROME-GRAY-33.png")
        # Ορισμός εικονιδίου εφαρμογής
        self.setWindowIcon(QIcon("icon.png"))  # Βεβαιώσου ότι το icon.png υπάρχει στον φάκελο
        
        
    def paintEvent(self, event):
        painter = QPainter(self)
        if not self.background_image.isNull():
            scaled = self.background_image.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        super().paintEvent(event)

# --- Βήμα 1: DataWindow ---
class DataWindow(BackgroundWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.setWindowTitle("Βήμα Πρώτο")
        self.setFixedSize(800,600)
        self.layout = QVBoxLayout()
        self.file_label = QLabel("Δεν έχει επιλεγεί αρχείο.")
        self.layout.addWidget(self.file_label)
        self.select_file_btn = QPushButton("Επιλογή Αρχείου CSV")
        self.select_file_btn.clicked.connect(self.select_file)
        self.layout.addWidget(self.select_file_btn)
        self.split_btn = QPushButton("Διαχωρισμός Δεδομένων")
        self.split_btn.clicked.connect(self.split_data)
        self.layout.addWidget(self.split_btn)
        self.setLayout(self.layout)
        self.csv_file = None

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Επιλογή CSV αρχείου", "", "CSV Files (*.csv)")
        if file_path:
            self.csv_file = file_path
            self.file_label.setText(f"Επιλεγμένο αρχείο: {file_path}")

    def split_data(self):
        if not self.csv_file:
            QMessageBox.warning(self, "Προειδοποίηση", "Παρακαλώ επιλέξτε αρχείο CSV πρώτα.")
            return
        try:
            with open(self.csv_file, newline='', encoding='utf-8', errors='replace') as csvfile:
                reader = csv.reader(csvfile)
                rs_rows = []
                turbo_rows = []
                err_rows = []
                error_counter = 1
                for row in reader:
                    if not row:
                        continue
                    if len(row) < MIN_VALID_COLUMNS:
                        err_rows.append([str(error_counter)] + row)
                        error_counter += 1
                        continue
                    row = row[:-1]  # Απομάκρυνση τελευταίας στήλης
                    rs_index = None
                    turbo_index = None
                    for i, cell in enumerate(row):
                        if "Reed-Solomon Decoded Message:" in cell:
                            rs_index = i
                            break
                        if "Received Bit Message" in cell:
                            turbo_index = i
                            break
                    if rs_index is not None:
                        m = re.search(r"Reed-Solomon Decoded Message:\s*(\d+)", row[rs_index])
                        if m:
                            number = m.group(1)
                            new_row = [number] + row[:rs_index] + row[rs_index+1:]
                            if len(','.join(new_row)) < 90:
                                err_rows.append([str(error_counter)] + row + ["(length < 90)"])
                                error_counter += 1
                            else:
                                rs_rows.append(new_row)
                        else:
                            err_rows.append([str(error_counter)] + row)
                            error_counter += 1
                    elif turbo_index is not None:
                        m = re.search(r"Received Bit Message #(\d+)#\s*:\s*(.+)", row[turbo_index])
                        if m:
                            number = m.group(1)
                            binary_data = m.group(2).strip()
                            new_turbo_row = [number, binary_data]
                            if len(','.join(new_turbo_row)) > 2000:
                                err_rows.append([str(error_counter)] + row + ["(length > 2000)"])
                                error_counter += 1
                            else:
                                turbo_rows.append(new_turbo_row)
                        else:
                            err_rows.append([str(error_counter)] + row)
                            error_counter += 1
                    else:
                        err_rows.append([str(error_counter)] + row)
                        error_counter += 1
            base_dir = os.path.dirname(self.csv_file)
            if rs_rows:
                rs_file = os.path.join(base_dir, "Reed_Solomon_Decoded_Message.csv")
                with open(rs_file, 'w', newline='', encoding='utf-8') as f:
                    csv.writer(f).writerows(rs_rows)
            if turbo_rows:
                turbo_file = os.path.join(base_dir, "Turbo_Codes_Data.csv")
                with open(turbo_file, 'w', newline='', encoding='utf-8') as f:
                    csv.writer(f).writerows(turbo_rows)
            if err_rows:
                err_file = os.path.join(base_dir, "Error_Invalid_payload.csv")
                with open(err_file, 'w', newline='', encoding='utf-8') as f:
                    csv.writer(f).writerows(err_rows)
            QMessageBox.information(self, "Επιτυχία", "Ο διαχωρισμός ολοκληρώθηκε επιτυχώς.")
            if (os.path.exists(os.path.join(base_dir, "Reed_Solomon_Decoded_Message.csv"))
                and os.path.exists(os.path.join(base_dir, "Turbo_Codes_Data.csv"))
                and os.path.exists(os.path.join(base_dir, "Error_Invalid_payload.csv"))
               ) and self.main_window is not None:
                self.main_window.first_step_btn.setText("Βήμα Πρώτο ✔")
                self.main_window.first_step_btn.setEnabled(False)
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Σφάλμα", f"Παρουσιάστηκε σφάλμα: {e}")

# --- Βήμα 2: TurboCodesWindow ---
class TurboCodesWindow(BackgroundWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.setWindowTitle("Βήμα Δεύτερο")
        self.setFixedSize(800,600)
        self.layout = QVBoxLayout()
        self.file_label = QLabel("Δεν έχει επιλεγεί αρχείο.")
        self.layout.addWidget(self.file_label)
        self.select_file_btn = QPushButton("Επιλογή Αρχείου CSV")
        self.select_file_btn.clicked.connect(self.select_file)
        self.layout.addWidget(self.select_file_btn)
        self.run_csv_btn = QPushButton("Εκτέλεση Csv_Reader_Writer")
        self.run_csv_btn.clicked.connect(self.run_csv_reader_writer)
        self.layout.addWidget(self.run_csv_btn)
        self.setLayout(self.layout)
        self.csv_file = None
        self.process = None
        self.timer = QTimer()
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.check_process)

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Επιλογή CSV αρχείου", "", "CSV Files (*.csv)")
        if file_path:
            self.csv_file = file_path
            self.file_label.setText(f"Επιλεγμένο αρχείο: {file_path}")

    def run_csv_reader_writer(self):
        if not self.csv_file:
            QMessageBox.warning(self, "Προειδοποίηση", "Παρακαλώ επιλέξτε αρχείο CSV πρώτα.")
            return
        base_dir = os.getcwd()
        executable_path = os.path.join(base_dir, "Csv_Reader_Writer")
        if not os.path.exists(executable_path):
            QMessageBox.critical(self, "Σφάλμα", f"Δεν βρέθηκε το Csv_Reader_Writer στο φάκελο: {base_dir}")
            return
        try:
            if sys.platform.startswith("win"):
                cmd = ['cmd', '/c', executable_path]
                self.process = subprocess.Popen(cmd, shell=True)
            elif sys.platform.startswith("linux"):
                terminal_cmd = None
                if shutil.which("konsole"):
                    terminal_cmd = ["konsole", "-e", f"{executable_path}"]
                elif shutil.which("gnome-terminal"):
                    terminal_cmd = ["gnome-terminal", "--", "bash", "-c", f"{executable_path}; exit"]
                elif shutil.which("xterm"):
                    terminal_cmd = ["xterm", "-e", f"{executable_path}; exit"]
                if terminal_cmd is None:
                    QMessageBox.critical(self, "Σφάλμα", "Δεν βρέθηκε διαθέσιμο terminal για εκτέλεση.")
                    return
                self.process = subprocess.Popen(terminal_cmd)
            elif sys.platform.startswith("darwin"):
                script = f'tell application "Terminal" to do script "{executable_path}; exit"'
                self.process = subprocess.Popen(['osascript', '-e', script])
            else:
                QMessageBox.critical(self, "Σφάλμα", "Μη υποστηριζόμενη πλατφόρμα για άνοιγμα terminal.")
                return
            self.timer.start()
        except Exception as e:
            QMessageBox.critical(self, "Σφάλμα", f"Παρουσιάστηκε σφάλμα κατά την εκτέλεση του Csv_Reader_Writer:\n{e}")

    def check_process(self):
        if self.process is not None:
            retcode = self.process.poll()
            if retcode is not None:
                self.timer.stop()
                QMessageBox.information(self, "Επιτυχία", "Το Csv_Reader_Writer ολοκληρώθηκε.")
                if self.main_window is not None:
                    self.main_window.second_step_btn.setText("Βήμα Δεύτερο ✔")
                    self.main_window.second_step_btn.setEnabled(False)
                self.close()

# --- Βήμα 3: ThirdStepWindow ---
class ThirdStepWindow(BackgroundWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.setWindowTitle("Βήμα Τρίτο")
        self.setFixedSize(800,600)
        self.layout = QVBoxLayout()
        self.file_label = QLabel("Δεν έχουν επιλεγεί αρχεία.")
        self.layout.addWidget(self.file_label)
        self.select_files_btn = QPushButton("Επιλογή Αρχείων CSV")
        self.select_files_btn.clicked.connect(self.select_files)
        self.layout.addWidget(self.select_files_btn)
        self.clean_btn = QPushButton("Διαχωρισμός Καθαρών Δεδομένων")
        self.clean_btn.clicked.connect(self.clean_data)
        self.layout.addWidget(self.clean_btn)
        self.setLayout(self.layout)
        self.csv_files = []

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Επιλογή CSV αρχείων", "", "CSV Files (*.csv)")
        if files:
            self.csv_files = files
            self.file_label.setText("Επιλεγμένα αρχεία:\n" + "\n".join(files))

    def clean_data(self):
        if not self.csv_files:
            QMessageBox.warning(self, "Προειδοποίηση", "Παρακαλώ επιλέξτε αρχεία CSV πρώτα.")
            return
        try:
            pattern = re.compile(r'^[0-9,.:-/]+$')
            output_files = []
            for file in self.csv_files:
                clean_rows = []
                with open(file, newline='', encoding='utf-8', errors='replace') as csvfile:
                    reader = csv.reader(csvfile)
                    for row in reader:
                        if len(row) != 12:
                            continue
                        row_str = ",".join(row)
                        if pattern.fullmatch(row_str):
                            clean_rows.append(row)
                base_dir, filename = os.path.split(file)
                name, ext = os.path.splitext(filename)
                output_file = os.path.join(base_dir, f"{name}_clean{ext}")
                if clean_rows:
                    with open(output_file, 'w', newline='', encoding='utf-8') as f:
                        csv.writer(f).writerows(clean_rows)
                    output_files.append(output_file)
            if output_files:
                QMessageBox.information(self, "Επιτυχία", "Ο διαχωρισμός ολοκληρώθηκε.\nΑποτελέσματα:\n" + "\n".join(output_files))
            else:
                QMessageBox.information(self, "Ενημέρωση", "Δεν βρέθηκαν 'καθαρά' δεδομένα στα αρχεία.")
            if self.main_window is not None:
                self.main_window.third_step_btn.setText("Βήμα Τρίτο ✔")
                self.main_window.third_step_btn.setEnabled(False)
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Σφάλμα", f"Παρουσιάστηκε σφάλμα:\n{e}")

# --- Βήμα 4: FourthStepWindow ---
class FourthStepWindow(BackgroundWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.setWindowTitle("Βήμα Τέταρτο")
        self.setFixedSize(800, 600)
        self.layout = QVBoxLayout()
        
        # Διάταξη για τις τιμές P0 και T0
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
        
        # Κουμπί ενημέρωσης διαγράμματος
        self.update_btn = QPushButton("Ενημέρωση Διαγράμματος")
        self.update_btn.clicked.connect(self.load_and_plot_data)
        self.layout.addWidget(self.update_btn)
        
        # Plot widget για το διάγραμμα
        self.plot_widget = pg.PlotWidget()
        self.layout.addWidget(self.plot_widget)
        
        # Διάταξη κουμπιών για εξομάλυνση
        btn_layout = QHBoxLayout()
        self.btn_raw = QPushButton("Raw Pressure")
        self.btn_savgol = QPushButton("Savitzky-Golay (Pressure)")
        self.btn_rolling = QPushButton("Rolling (Pressure)")
        self.btn_save = QPushButton("Αποθήκευση Γραφήματος")
        btn_layout.addWidget(self.btn_raw)
        btn_layout.addWidget(self.btn_savgol)
        btn_layout.addWidget(self.btn_rolling)
        btn_layout.addWidget(self.btn_save)
        self.layout.addLayout(btn_layout)
        
        self.setLayout(self.layout)
        
        # Σύνδεση κουμπιών
        self.btn_raw.clicked.connect(self.plot_pressure_raw)
        self.btn_savgol.clicked.connect(self.plot_pressure_savgol)
        self.btn_rolling.clicked.connect(self.plot_pressure_rolling)
        self.btn_save.clicked.connect(self.save_plot)
        
        # Φόρτωση αρχικών δεδομένων
        self.load_and_plot_data()
    
    def load_and_plot_data(self):
        try:
            # Προσπαθούμε να φορτώσουμε το προεπιλεγμένο CSV (αν υπάρχει)
            default_file = "Reed_Solomon_Decoded_Message.csv"
            if os.path.exists(default_file):
                df = pd.read_csv(default_file)
            else:
                file_path, _ = QFileDialog.getOpenFileName(self, "Επιλογή CSV αρχείου", "", "CSV Files (*.csv)")
                if not file_path:
                    return
                df = pd.read_csv(file_path)
            
            # Εξαγωγή δεδομένων (υποθέτουμε ότι:
            #  - 11η στήλη (index 10) είναι υψόμετρο (raw)
            #  - 14η στήλη (index 13) είναι θερμοκρασία (°C)
            #  - 13η στήλη (index 12) είναι πίεση (hPa)
            self.altitude = df.iloc[:, 10]
            self.temperature = df.iloc[:, 13]
            self.pressure = df.iloc[:, 12]
            
            # Λήψη τιμών P0 και T0 από τα QLineEdit (με μετατροπή σε float)
            P0 = float(self.edit_P0.text())
            T0 = float(self.edit_T0.text())
            self.label_P0.setText(f"P₀ (πίεση στο επίπεδο της θάλασσας): {P0} hPa")
            self.label_T0.setText(f"T₀ (θερμοκρασία στο επίπεδο της θάλασσας): {T0} °C")
            T0_K = T0 + 273.15
            
            # Σταθερές
            L = 0.0065  # K/m
            R = 8.31432  # J/(mol·K)
            g = 9.80665  # m/s²
            M = 0.0289644  # kg/mol
            
            # Υπολογισμός υψομέτρου από πίεση
            self.altitude_from_pressure = (T0_K / L) * (1 - (self.pressure / P0) ** ((R * L) / (g * M)))
            
            # Αρχική εμφάνιση raw
            self.plot_pressure_raw()
        except Exception as e:
            QMessageBox.critical(self, "Σφάλμα", f"Σφάλμα φόρτωσης δεδομένων:\n{e}")
    
    def plot_pressure_raw(self):
        self.plot_widget.clear()
        self.plot_widget.plot(self.altitude_from_pressure, self.temperature, pen='r', symbol='o', symbolSize=5, symbolBrush='b')
        self.plot_widget.setLabel("left", "Θερμοκρασία (°C)")
        self.plot_widget.setLabel("bottom", "Υψόμετρο (m) (από πίεση)")
        self.plot_widget.setTitle("Pressure-Derived Altitude vs Temperature (Raw)")
    
    def plot_pressure_savgol(self):
        self.plot_widget.clear()
        altitude_savgol = savgol_filter(self.altitude_from_pressure, window_length=11, polyorder=2)
        temperature_savgol = savgol_filter(self.temperature, window_length=11, polyorder=2)
        self.plot_widget.plot(altitude_savgol, temperature_savgol, pen='g', symbol='o', symbolSize=5, symbolBrush='b')
        self.plot_widget.setLabel("left", "Θερμοκρασία (°C)")
        self.plot_widget.setLabel("bottom", "Υψόμετρο (m) (από πίεση)")
        self.plot_widget.setTitle("Pressure-Derived Altitude vs Temperature (Savitzky-Golay)")
    
    def plot_pressure_rolling(self):
        self.plot_widget.clear()
        altitude_rolling = self.altitude_from_pressure.rolling(window=11, center=True).mean()
        temperature_rolling = self.temperature.rolling(window=11, center=True).mean()
        self.plot_widget.plot(altitude_rolling, temperature_rolling, pen='b', symbol='o', symbolSize=5, symbolBrush='b')
        self.plot_widget.setLabel("left", "Θερμοκρασία (°C)")
        self.plot_widget.setLabel("bottom", "Υψόμετρο (m) (από πίεση)")
        self.plot_widget.setTitle("Pressure-Derived Altitude vs Temperature (Rolling Average)")
    
    def save_plot(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Αποθήκευση Γραφήματος", "diagram.png", "PNG Files (*.png);;All Files (*)")
        if file_path:
            exporter = ImageExporter(self.plot_widget.plotItem)
            exporter.export(file_path)
            QMessageBox.information(self, "Επιτυχία", f"Το γράφημα αποθηκεύτηκε ως {file_path}")

# --- Κύριο Παράθυρο ---
class MainWindow(BackgroundWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NGM Team App")
        self.setFixedSize(800,600)
        self.layout = QVBoxLayout()
        self.first_step_btn = QPushButton("Βήμα Πρώτο")
        self.first_step_btn.clicked.connect(self.open_first_step)
        self.layout.addWidget(self.first_step_btn)
        self.second_step_btn = QPushButton("Βήμα Δεύτερο")
        self.second_step_btn.clicked.connect(self.open_second_step)
        self.layout.addWidget(self.second_step_btn)
        self.third_step_btn = QPushButton("Βήμα Τρίτο")
        self.third_step_btn.clicked.connect(self.open_third_step)
        self.layout.addWidget(self.third_step_btn)
        self.fourth_step_btn = QPushButton("Βήμα Τέταρτο")
        self.fourth_step_btn.clicked.connect(self.open_fourth_step)
        self.layout.addWidget(self.fourth_step_btn)
        self.setLayout(self.layout)

    def open_first_step(self):
        self.data_window = DataWindow(main_window=self)
        self.data_window.show()

    def open_second_step(self):
        self.turbo_window = TurboCodesWindow(main_window=self)
        self.turbo_window.show()

    def open_third_step(self):
        self.third_window = ThirdStepWindow(main_window=self)
        self.third_window.show()

    def open_fourth_step(self):
        self.fourth_window = FourthStepWindow(main_window=self)
        self.fourth_window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())