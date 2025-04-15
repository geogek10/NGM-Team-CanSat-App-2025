# fifthstepwindow.py
import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
from pyqtgraph.exporters import ImageExporter
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QMessageBox, QTabWidget, QSizePolicy
)
from PyQt6.QtGui import QPainter, QPixmap

# --- BackgroundWidget ---
class BackgroundWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Διαβάζουμε την εικόνα ως QPixmap
        self.background_image = QPixmap("NGM--MONOCHROME-GRAY-33.png")
        
    def paintEvent(self, event):
        painter = QPainter(self)
        if not self.background_image.isNull():
            scaled = self.background_image.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        super().paintEvent(event)

# --- PieChartTab ---
class PieChartTab(QWidget):
    def __init__(self, file_path, title, max_col_index, parent=None):
        """
        :param file_path: Το CSV αρχείο με τα δεδομένα.
        :param title: Τίτλος του διαγράμματος (π.χ., "Απόδοση Reed - Solomon").
        :param max_col_index: Ο index της στήλης που περιέχει τον "μέγιστο" αριθμό μηνυμάτων.
        """
        super().__init__(parent)
        self.file_path = file_path
        self.chart_title = title
        self.max_col_index = max_col_index
        self.layout = QVBoxLayout()
        self.info_label = QLabel(f"Χρησιμοποιείται αρχείο: {os.path.basename(file_path)}")
        self.layout.addWidget(self.info_label)
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        # Responsive: να επεκτείνεται το canvas
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.layout.addWidget(self.canvas)
        self.save_btn = QPushButton("Αποθήκευση Διαγράμματος")
        self.save_btn.clicked.connect(self.save_chart)
        self.layout.addWidget(self.save_btn)
        self.setLayout(self.layout)
        self.load_and_plot()

    def load_and_plot(self):
        try:
            df = pd.read_csv(self.file_path)
            # Διόρθωση: προσθέτουμε 1 στο πλήθος των γραμμών για να διορθωθεί το off-by-one
            total_messages = len(df) + 1
            max_value = df.iloc[:, self.max_col_index].max()
            if pd.isna(max_value):
                QMessageBox.critical(self, "Σφάλμα", f"Δεν βρέθηκε έγκυρη τιμή στη στήλη {self.max_col_index+1} του αρχείου.")
                return
            missing = max_value - total_messages if max_value > total_messages else 0
            data = [total_messages, missing]
            # Εμφάνιση ως αριθμοί και ποσοστά
            labels = [f"Ελήφθησαν\n({total_messages}, {total_messages/max_value*100:.1f}%)",
                      f"Μη Ελήφθησαν\n({missing}, {missing/max_value*100:.1f}%)"]
            
            self.ax.clear()
            self.ax.pie(data, labels=labels, autopct=lambda pct: f"{pct:.1f}%", startangle=90)
            self.ax.set_title(self.chart_title)
            self.canvas.draw()
        except Exception as e:
            QMessageBox.critical(self, "Σφάλμα", f"Σφάλμα φόρτωσης ή σχεδίασης: {e}")

    def save_chart(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Αποθήκευση Διαγράμματος", "chart.png", "PNG Files (*.png);;All Files (*)")
        if file_path:
            self.figure.savefig(file_path)
            QMessageBox.information(self, "Επιτυχία", f"Το διάγραμμα αποθηκεύτηκε ως {file_path}")

# --- FifthStepWindow ---
class FifthStepWindow(BackgroundWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.setWindowTitle("Βήμα Πέμπτο")
        self.setMinimumSize(800, 600)  # Responsive
        self.layout = QVBoxLayout()
        
        self.tabs = QTabWidget()
        self.tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Tab 1: Απόδοση Reed - Solomon
        tab1_file = "Reed_Solomon_Decoded_Message.csv"
        tab1 = PieChartTab(tab1_file, "Απόδοση Reed - Solomon", max_col_index=3)
        
        # Tab 2: Απόδοση BCJR
        tab2_file = "BCJR_Output_clean.csv"
        tab2 = PieChartTab(tab2_file, "Απόδοση BCJR", max_col_index=1)
        
        # Tab 3: Απόδοση MAP
        tab3_file = "MAP_Output_clean.csv"
        tab3 = PieChartTab(tab3_file, "Απόδοση MAP", max_col_index=1)
        
        # Tab 4: Απόδοση SOVA
        tab4_file = "SOVA_Output_clean.csv"
        tab4 = PieChartTab(tab4_file, "Απόδοση SOVA", max_col_index=1)
        
        # Tab 5: Απόδοση HYBRID
        tab5_file = "HYBRID_Output_clean.csv"
        tab5 = PieChartTab(tab5_file, "Απόδοση HYBRID", max_col_index=1)
        
        self.tabs.addTab(tab1, "Reed-Solomon")
        self.tabs.addTab(tab2, "BCJR")
        self.tabs.addTab(tab3, "MAP")
        self.tabs.addTab(tab4, "SOVA")
        self.tabs.addTab(tab5, "HYBRID")
        
        self.layout.addWidget(self.tabs)
        # Responsive: κουμπί αποθήκευσης με expanding policy
        self.save_btn = QPushButton("Αποθήκευση Διαγράμματος")
        self.save_btn.clicked.connect(self.save_plot)
        self.layout.addWidget(self.save_btn)
        self.setLayout(self.layout)

    def save_plot(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Αποθήκευση Διαγράμματος", "diagram.png", "PNG Files (*.png);;All Files (*)")
        if file_path:
            current_index = self.tabs.currentIndex()
            # Υποθέτουμε ότι κάθε tab είναι instance της PieChartTab
            if hasattr(self.tabs.currentWidget(), "canvas"):
                exporter = ImageExporter(self.tabs.currentWidget().canvas.figure.axes[0].figure)
                exporter.export(file_path)
            else:
                QMessageBox.warning(self, "Προειδοποίηση", "Δεν βρέθηκε ενεργό διάγραμμα για αποθήκευση.")
            QMessageBox.information(self, "Επιτυχία", f"Το διάγραμμα αποθηκεύτηκε ως {file_path}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FifthStepWindow()
    window.show()
    sys.exit(app.exec())
