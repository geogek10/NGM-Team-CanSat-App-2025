# thirdstepwindow.py
import sys
import csv
import re
import os
from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QFileDialog, QLabel, QMessageBox
from backgroundwidget import BackgroundWidget

class ThirdStepWindow(BackgroundWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.setWindowTitle("Βήμα Τρίτο")
        self.setMinimumSize(800,600)
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
            # Διόρθωση του regex ώστε να επιτρέπει τους χαρακτήρες: ψηφία, κόμμα, τελεία, άνω/κάτω τελεία, slash
            pattern = re.compile(r'^[0-9,-.:/]+$')
            output_files = []
            for file in self.csv_files:
                clean_rows = []
                with open(file, newline='', encoding='utf-8', errors='replace') as csvfile:
                    reader = csv.reader(csvfile)
                    for row in reader:
                        # Έλεγχος ότι η γραμμή έχει ακριβώς 12 στήλες
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

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = ThirdStepWindow()
    window.show()
    sys.exit(app.exec())
