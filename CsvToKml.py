import sys
import csv
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QTextEdit, QFileDialog


class CSVToKMLApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CSV to KML Converter")
        self.setGeometry(100, 100, 600, 400)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        self.select_file_button = QPushButton("Select CSV File")
        self.select_file_button.clicked.connect(self.select_csv_file)
        self.layout.addWidget(self.select_file_button)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.layout.addWidget(self.output_text)

    def select_csv_file(self):
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("CSV Files (*.csv)")
        if file_dialog.exec():
            csv_file_path = file_dialog.selectedFiles()[0]
            try:
                kml_content = self.generate_kml(csv_file_path)
                self.save_kml_file(kml_content)
                self.output_text.setText("KML file generated successfully!")
            except Exception as e:
                self.output_text.setText(f"Error: {str(e)}")

    def generate_kml(self, csv_file_path):
        kml_header = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
"""
        kml_footer = """</Document>
</kml>
"""
        placemarks = ""

        with open(csv_file_path, 'r') as csv_file:
            reader = csv.reader(csv_file)
            next(reader)  # Παράβλεψη της επικεφαλίδας
            for row in reader:
                latitude = row[4]
                longitude = row[5]
                altitude = row[10]
                placemark = f"""
    <Placemark>
        <Point>
            <altitudeMode>absolute</altitudeMode>
            <coordinates>{longitude},{latitude},{altitude}</coordinates>
        </Point>
    </Placemark>
    """
                placemarks += placemark

        return kml_header + placemarks + kml_footer

    def save_kml_file(self, kml_content):
        file_dialog = QFileDialog(self)
        file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        file_dialog.setNameFilter("KML Files (*.kml)")
        if file_dialog.exec():
            kml_file_path = file_dialog.selectedFiles()[0]
            with open(kml_file_path, 'w') as kml_file:
                kml_file.write(kml_content)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CSVToKMLApp()
    window.show()
    sys.exit(app.exec())
