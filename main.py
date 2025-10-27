from __future__ import annotations
import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget,
    QWidget, QVBoxLayout, QPushButton, QLabel
)

from ui_login import LoginWidget
from dashboard_simulador import DashboardWindow
from dashboard_dispositivo import DashboardDispositivo


class MenuInicial(QWidget):
    """
    Tela inicial para escolher qual dashboard abrir.
    """
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

        layout = QVBoxLayout()

        self.label = QLabel("Selecione o modo de operação:")
        self.label.setStyleSheet("font-size: 16px; font-weight: bold;")

        self.btn_simulador = QPushButton("💧 Dashboard Simulador (Teste Local)")
        self.btn_simulador.clicked.connect(self.abrir_simulador)

        self.btn_dispositivo = QPushButton("📡 Dashboard Dispositivo (ESP32)")
        self.btn_dispositivo.clicked.connect(self.abrir_dispositivo)

        layout.addWidget(self.label)
        layout.addWidget(self.btn_simulador)
        layout.addWidget(self.btn_dispositivo)
        layout.addStretch()
        self.setLayout(layout)

    def abrir_simulador(self):
        self.main_window.setCurrentWidget(self.main_window.dashboard_simulador)

    def abrir_dispositivo(self):
        self.main_window.setCurrentWidget(self.main_window.dashboard_dispositivo)


class MainWindow(QMainWindow):
    """
    Janela principal que gerencia as telas (login, menu, dashboards).
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IOT EAM Integration")
        self.resize(650, 480)

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # Telas
        self.login_widget = LoginWidget(self)
        self.menu_widget = MenuInicial(self)
        self.dashboard_simulador = DashboardWindow(self)
        self.dashboard_dispositivo = DashboardDispositivo(self)

        # Adiciona as telas
        self.stacked_widget.addWidget(self.login_widget)
        self.stacked_widget.addWidget(self.menu_widget)
        self.stacked_widget.addWidget(self.dashboard_simulador)
        self.stacked_widget.addWidget(self.dashboard_dispositivo)

        # Tela inicial → Login
        self.show_login_screen()

    # --------------------------------------------------------------
    def setCurrentWidget(self, widget):
        self.stacked_widget.setCurrentWidget(widget)

    def show_login_screen(self):
        """Retorna à tela de login e reseta dashboards."""
        self.dashboard_simulador.running = False
        self.dashboard_dispositivo.running = False
        self.dashboard_simulador.btn_start.setText("▶️ Iniciar Simulador")
        self.dashboard_dispositivo.btn_start.setText("▶️ Iniciar Monitoramento")
        self.dashboard_simulador.label_status.setText("💧 Aguardando leituras do sensor...")
        self.dashboard_dispositivo.label_status.setText("📡 Aguardando dados do dispositivo...")
        self.setCurrentWidget(self.login_widget)

    def show_menu(self):
        """Exibe o menu principal após o login."""
        self.setCurrentWidget(self.menu_widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())
