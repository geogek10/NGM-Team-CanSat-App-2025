import sys
import pandas as pd
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QFileDialog, QInputDialog
from PyQt6.QtGui import QIcon
import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter
from scipy.signal import savgol_filter
import numpy as np

class CSVPlotter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Reed Solomon Decoded Message Plot")
        self.setGeometry(100, 100, 800, 600)
        
        # Ορισμός εικονιδίου εφαρμογής
        self.setWindowIcon(QIcon("icon.png"))  # Βεβαιώσου ότι το icon.png υπάρχει στον φάκελο
        
        # Κύριο widget και layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout()
        self.central_widget.setLayout(main_layout)
        
        # Διάγραμμα
        self.plot_widget = pg.PlotWidget()
        main_layout.addWidget(self.plot_widget)
        
        # Κουμπιά για επιλογή εξομάλυνσης
        button_layout = QHBoxLayout()
        self.btn_raw = QPushButton("Χωρίς Εξομάλυνση")
        self.btn_savgol = QPushButton("Savitzky-Golay")
        self.btn_rolling = QPushButton("Κινητός Μέσος Όρος")
        self.btn_pressure_altitude = QPushButton("Υψόμετρο από Πίεση")
        self.btn_save = QPushButton("Αποθήκευση Γραφήματος")
        
        self.btn_raw.clicked.connect(self.plot_raw)
        self.btn_savgol.clicked.connect(self.plot_savgol)
        self.btn_rolling.clicked.connect(self.plot_rolling)
        self.btn_pressure_altitude.clicked.connect(self.plot_pressure_altitude)
        self.btn_save.clicked.connect(self.save_plot)
        
        button_layout.addWidget(self.btn_raw)
        button_layout.addWidget(self.btn_savgol)
        button_layout.addWidget(self.btn_rolling)
        button_layout.addWidget(self.btn_pressure_altitude)
        button_layout.addWidget(self.btn_save)
        
        main_layout.addLayout(button_layout)
        
        # Φόρτωση δεδομένων
        self.load_data()
    
    def load_data(self):
        try:
            df = pd.read_csv("Reed_Solomon_Decoded_Message.csv")
            self.altitude = df.iloc[:, 10]  # 11η στήλη (Python index ξεκινά από 0)
            self.temperature = df.iloc[:, 13]  # 14η στήλη
            self.pressure = df.iloc[:, 12]  # 13η στήλη (Ατμοσφαιρική πίεση σε hPa)
            
            # Ζήτηση δεδομένων από τον χρήστη
            P0, ok1 = QInputDialog.getDouble(self, "Εισαγωγή P0", "Πίεση στο επίπεδο της θάλασσας (hPa):", 1013.25, 800, 1100, 2)
            T0, ok2 = QInputDialog.getDouble(self, "Εισαγωγή T0", "Θερμοκρασία στο επίπεδο της θάλασσας (°C):", 15, -50, 50, 2)
            
            if not ok1 or not ok2:
                return
            
            # Μετατροπή της θερμοκρασίας σε Kelvin
            T0 += 273.15
            
            # Σταθερές
            L = 0.0065  # Ρυθμός μείωσης θερμοκρασίας (K/m)
            R = 8.31432  # Παγκόσμια σταθερά αερίων (J/(mol·K))
            g = 9.80665  # Επιτάχυνση της βαρύτητας (m/s²)
            M = 0.0289644  # Μοριακή μάζα του αέρα (kg/mol)
            
            # Υπολογισμός υψομέτρου από την πίεση με μεγαλύτερη ακρίβεια
            self.altitude_from_pressure = (T0 / L) * (1 - (self.pressure / P0) ** ((R * L) / (g * M)))
            
            # Εξομάλυνση των δεδομένων με το Savitzky-Golay φίλτρο
            self.altitude_savgol = savgol_filter(self.altitude, window_length=11, polyorder=2)
            self.temperature_savgol = savgol_filter(self.temperature, window_length=11, polyorder=2)
            
            # Εξομάλυνση με κινητό μέσο όρο (rolling mean)
            self.altitude_rolling = self.altitude.rolling(window=11, center=True).mean()
            self.temperature_rolling = self.temperature.rolling(window=11, center=True).mean()
            
            # Αρχική εμφάνιση (χωρίς εξομάλυνση)
            self.plot_raw()
        except Exception as e:
            print(f"Σφάλμα κατά την ανάγνωση του αρχείου: {e}")
    
    def plot_raw(self):
        self.plot_widget.clear()
        self.plot_widget.plot(self.altitude, self.temperature, pen='r', symbol='o', symbolSize=5, symbolBrush='b')
        self.plot_widget.setLabel("left", "Θερμοκρασία (°C)")
        self.plot_widget.setLabel("bottom", "Υψόμετρο (m)")
        self.plot_widget.setTitle("Σχέση Υψομέτρου - Θερμοκρασίας (Χωρίς Εξομάλυνση)")

    def plot_savgol(self):
        self.plot_widget.clear()
        self.plot_widget.plot(self.altitude_savgol, self.temperature_savgol, pen='g', symbol='o', symbolSize=5, symbolBrush='b')
        self.plot_widget.setLabel("left", "Θερμοκρασία (°C)")
        self.plot_widget.setLabel("bottom", "Υψόμετρο (m)")
        self.plot_widget.setTitle("Σχέση Υψομέτρου - Θερμοκρασίας (Savitzky-Golay)")
    
    def plot_rolling(self):
        self.plot_widget.clear()
        self.plot_widget.plot(self.altitude_rolling, self.temperature_rolling, pen='b', symbol='o', symbolSize=5, symbolBrush='b')
        self.plot_widget.setLabel("left", "Θερμοκρασία (°C)")
        self.plot_widget.setLabel("bottom", "Υψόμετρο (m)")
        self.plot_widget.setTitle("Σχέση Υψομέτρου - Θερμοκρασίας (Κινητός Μέσος Όρος)")
    
    def plot_pressure_altitude(self):
        self.plot_widget.clear()
        self.plot_widget.plot(self.altitude_from_pressure, self.temperature, pen='m', symbol='o', symbolSize=5, symbolBrush='b')
        self.plot_widget.setLabel("left", "Θερμοκρασία (°C)")
        self.plot_widget.setLabel("bottom", "Υψόμετρο (m) (Υπολογισμένο από πίεση)")
        self.plot_widget.setTitle("Σχέση Υψομέτρου - Θερμοκρασίας (Υπολογισμένο από πίεση)")

    def save_plot(self):
            file_path, _ = QFileDialog.getSaveFileName(self, "Αποθήκευση Γραφήματος", "diagram.png", "PNG Files (*.png);;All Files (*)")
            if file_path:
                exporter = ImageExporter(self.plot_widget.plotItem)
                exporter.export(file_path)
                print(f"Το γράφημα αποθηκεύτηκε ως {file_path}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CSVPlotter()
    window.show()
    sys.exit(app.exec())
