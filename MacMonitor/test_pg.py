import sys
import pyqtgraph as pg
from PyQt6.QtWidgets import QApplication, QMainWindow

app = QApplication(sys.argv)
win = QMainWindow()
plot = pg.PlotWidget()
win.setCentralWidget(plot)
win.show()
sys.exit(app.exec())