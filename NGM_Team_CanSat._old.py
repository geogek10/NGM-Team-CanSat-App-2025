import sys
import pandas as pd
import matplotlib.pyplot as plt
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget, QFileDialog, QComboBox, QHBoxLayout

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Ρύθμιση του παραθύρου
        self.setWindowTitle("Επιλογή Αρχείου CSV και Στηλών")
        self.setGeometry(100, 100, 400, 200)

        # Δημιουργία widgets
        self.label = QLabel("Δεν έχει επιλεγεί αρχείο", self)
        self.button_select_file = QPushButton("Επιλέξτε Αρχείο CSV", self)
        self.button_select_file.clicked.connect(self.open_file_dialog)

        self.combo_x = QComboBox(self)
        self.combo_y = QComboBox(self)
        self.button_plot = QPushButton("Εμφάνιση Διαγράμματος", self)
        self.button_plot.clicked.connect(self.plot_data)
        self.button_plot.setEnabled(False)  # Αρχικά απενεργοποιημένο

        # Ρύθμιση layout
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.button_select_file)

        layout_combos = QHBoxLayout()
        layout_combos.addWidget(QLabel("Επιλέξτε στήλη X:"))
        layout_combos.addWidget(self.combo_x)
        layout_combos.addWidget(QLabel("Επιλέξτε στήλη Y:"))
        layout_combos.addWidget(self.combo_y)

        layout.addLayout(layout_combos)
        layout.addWidget(self.button_plot)

        # Ορισμός κεντρικού widget
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Αρχικοποίηση DataFrame
        self.df = None

    def open_file_dialog(self):
        # Άνοιγμα διαλόγου επιλογής αρχείου
        file_name, _ = QFileDialog.getOpenFileName(self, "Επιλέξτε Αρχείο CSV", "", "CSV Files (*.csv)")
        if file_name:
            self.label.setText(f"Επιλεγμένο αρχείο: {file_name}")
            self.load_csv(file_name)

    def load_csv(self, file_name):
        try:
            # Προσπαθούμε να φορτώσουμε το CSV με κεφαλίδες
            self.df = pd.read_csv(file_name)
            if not all(isinstance(col, str) for col in self.df.columns):
                # Αν οι κεφαλίδες δεν είναι strings, πιθανόν δεν υπάρχουν κεφαλίδες
                self.df = pd.read_csv(file_name, header=None)
                self.df.columns = [f"Column {i}" for i in range(len(self.df.columns))]
            self.populate_combos()
            self.button_plot.setEnabled(True)
        except Exception as e:
            self.label.setText(f"Σφάλμα κατά τη φόρτωση του αρχείου: {e}")

    def populate_combos(self):
        # Γεμίζουμε τα dropdown menus με τα ονόματα των στηλών
        columns = self.df.columns.tolist()
        self.combo_x.clear()
        self.combo_y.clear()
        self.combo_x.addItems([str(col) for col in columns])
        self.combo_y.addItems([str(col) for col in columns])

    def plot_data(self):
        if self.df is not None:
            x_col = self.combo_x.currentText()
            y_col = self.combo_y.currentText()
            if x_col and y_col:
                try:
                    plt.figure()
                    plt.plot(self.df[x_col], self.df[y_col], marker='o')
                    plt.xlabel(x_col)
                    plt.ylabel(y_col)
                    plt.title(f"Διάγραμμα {x_col} vs {y_col}")
                    plt.show()
                except Exception as e:
                    self.label.setText(f"Σφάλμα κατά τη δημιουργία του διαγράμματος: {e}")
            else:
                self.label.setText("Παρακαλώ επιλέξτε και τις δύο στήλες.")

# Εκτέλεση της εφαρμογής
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())