# turbocodeswindow.py
import sys
import os
import subprocess
import shutil
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QFileDialog, QLabel, QMessageBox
from backgroundwidget import BackgroundWidget

class TurboCodesWindow(BackgroundWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.setWindowTitle("Βήμα Δεύτερο")
        self.setMinimumSize(800,600)
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

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = TurboCodesWindow()
    window.show()
    sys.exit(app.exec())
