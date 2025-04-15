# mainwindow.py
import sys
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget, QPushButton
from backgroundwidget import BackgroundWidget
from datawindow import DataWindow
from turbocodeswindow import TurboCodesWindow
from thirdstepwindow import ThirdStepWindow
from fourthstepwindow import FourthStepWindow
from fifthstepwindow import FifthStepWindow

class MainWindow(BackgroundWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NGM Team App")
        self.setMinimumSize(800,600)
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
        
        self.fifth_step_btn = QPushButton("Βήμα Πέμπτο")
        self.fifth_step_btn.clicked.connect(self.open_fifth_step)
        self.layout.addWidget(self.fifth_step_btn)

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

    def open_fifth_step(self):
        self.fifth_window = FifthStepWindow(main_window=self)
        self.fifth_window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
