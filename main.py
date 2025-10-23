# main.py
from __future__ import annotations
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from ui_login import LoginWidget
from dashboard import DashboardWindow


class MainWindow(QMainWindow):
    """A janela principal que gerencia as telas (widgets) da aplicação."""
    def __init__(self):
        super().__init__()

        self.setWindowTitle("IOT EAM Integration")
        self.resize(600, 450)

        # Widget que permite empilhar telas e mostrar uma de cada vez
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # Cria as instâncias das telas, passando a si mesma (self) como referência
        self.login_widget = LoginWidget(self)
        self.dashboard_widget = DashboardWindow(self)

        # Adiciona as telas ao gerenciador
        self.stacked_widget.addWidget(self.login_widget)
        self.stacked_widget.addWidget(self.dashboard_widget)

        # Define a tela de login como a inicial
        self.setCurrentWidget(self.login_widget)

    def setCurrentWidget(self, widget):
        """Método para trocar a tela visível."""
        self.stacked_widget.setCurrentWidget(widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())
