# ui_login.py
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QFormLayout, QVBoxLayout, QMessageBox
)
from PyQt6.QtCore import Qt
from eam_session_manager import EAMConfig, get_valid_session

class LoginWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

        self.ed_server = QLineEdit()
        self.ed_port = QLineEdit()
        self.ed_org = QLineEdit()
        self.ed_tenant = QLineEdit()
        self.ed_user = QLineEdit()
        self.ed_pass = QLineEdit()
        self.ed_token = QLineEdit()
        self.ed_token.setReadOnly(True)

        self.ed_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_port.setPlaceholderText("(opcional)")
        self.ed_server.setPlaceholderText("ex.: us1.eam.hxgnsmartcloud.com ou http://192.168.15.9:7575")
        self.ed_org.setPlaceholderText("ex.: C001")
        self.ed_tenant.setText("IBNQI1720580460_DEM") # Valor fixo
        self.ed_tenant.setReadOnly(True) # Campo não editável

        btn_save = QPushButton("Entrar")
        btn_save.clicked.connect(self.on_save)

        form = QFormLayout()
        form.addRow(QLabel("Server:"), self.ed_server)
        form.addRow(QLabel("Port: (Opcional)"), self.ed_port)
        form.addRow(QLabel("Organization:"), self.ed_org)
        form.addRow(QLabel("Tenant:"), self.ed_tenant)
        form.addRow(QLabel("Username:"), self.ed_user)
        form.addRow(QLabel("Password:"), self.ed_pass)
        form.addRow(QLabel("Token de Autenticação:"), self.ed_token)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(btn_save, alignment=Qt.AlignmentFlag.AlignLeft)
        self.setLayout(layout)
        self.setWindowTitle("Configuração de Conexão - EAM")

    def on_save(self):
        # 🔧 Captura os campos de entrada
        server = self.ed_server.text().strip()
        org = self.ed_org.text().strip()
        tenant = self.ed_tenant.text().strip()
        user = self.ed_user.text().strip()
        password = self.ed_pass.text().strip()

        # 🧩 Validação dos campos obrigatórios
        if not all([server, org, tenant, user, password]):
            QMessageBox.warning(self, "Campos obrigatórios", "Preencha todos os campos (Port é opcional).")
            return

        # 🔹 Monta a configuração para conexão com o EAM
        cfg = EAMConfig(
            server=server,
            tenant=tenant,
            org=org,
            user=user,
            password=password,
            proxy_url="http://localhost:8080/eamproxy"  # ou None se for on-prem
        )

        try:
            # 🔐 Autentica e obtém o Session ID (SID)
            sid = get_valid_session(cfg)
            self.ed_token.setText(sid)
            QMessageBox.information(self, "OK", "Sessão válida e salva.")

            # Inicializa os dashboards com os dados da sessão
            if hasattr(self.main_window, 'dashboard_simulador'):
                self.main_window.dashboard_simulador.initialize_dashboard(cfg, sid)
            if hasattr(self.main_window, 'dashboard_dispositivo'):
                self.main_window.dashboard_dispositivo.initialize_dashboard(cfg, sid)

            # Após o login, exibe o menu principal
            if hasattr(self.main_window, 'show_menu'):
                self.main_window.show_menu()

        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))
