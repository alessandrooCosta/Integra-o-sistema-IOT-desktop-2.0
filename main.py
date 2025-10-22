# main.py
from __future__ import annotations
import sys
from PyQt6.QtWidgets import QApplication
from ui_login import LoginWidget

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = LoginWidget()
    w.resize(520, 260)
    w.show()
    sys.exit(app.exec())
