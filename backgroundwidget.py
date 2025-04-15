# backgroundwidget.py
import os
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPixmap, QIcon
from PyQt6.QtWidgets import QWidget

class BackgroundWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Φορτώνουμε το background image (υποθέτουμε ότι βρίσκεται στον ίδιο φάκελο)
        self.background_image = QPixmap("NGM--MONOCHROME-GRAY-33.png")
        # Ορίζουμε το εικονίδιο της εφαρμογής (π.χ., icon.png)
        self.setWindowIcon(QIcon("icon.png"))
        
    def paintEvent(self, event):
        painter = QPainter(self)
        if not self.background_image.isNull():
            # Κλιμακώνουμε την εικόνα ώστε να χωράει στο widget διατηρώντας τις αναλογίες
            scaled = self.background_image.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        super().paintEvent(event)
