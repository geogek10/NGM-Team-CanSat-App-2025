# datawindow.py
import sys
import csv
import re
import os
from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QFileDialog, QLabel, QMessageBox
from backgroundwidget import BackgroundWidget

MIN_VALID_COLUMNS = 8

class DataWindow(BackgroundWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.setWindowTitle("Βήμα Πρώτο")
        self.setMinimumSize(800, 600)
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
                    # Απομάκρυνση της τελευταίας στήλης
                    row = row[:-1]
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

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = DataWindow()
    window.show()
    sys.exit(app.exec())
