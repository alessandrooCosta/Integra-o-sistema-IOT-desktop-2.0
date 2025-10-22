# ui_login.py
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QFormLayout, QVBoxLayout, QMessageBox
)
from PyQt6.QtCore import Qt
from eam_session_manager import EAMConfig, get_valid_session

class LoginWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

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
        self.ed_tenant.setPlaceholderText("ex.: IBNQI1720580460_DEM")

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
        server = self.ed_server.text().strip()
        org    = self.ed_org.text().strip()
        tenant = self.ed_tenant.text().strip()
        user   = self.ed_user.text().strip()
        passwd = self.ed_pass.text().strip()

        if not all([server, org, tenant, user, passwd]):
            QMessageBox.warning(self, "Campos obrigatórios", "Preencha todos os campos (Port é opcional).")
            return

        # Ajuste: se quiser usar API Key na Cloud, basta adicionar aqui:
        cfg = EAMConfig(
            server=self.ed_server.text().strip(),     # ex.: "https://us1.eam.hxgnsmartcloud.com" ou "http://192.168.15.9:7575"
            tenant=self.ed_tenant.text().strip(),     # ex.: "IBNQI1720580460_DEM" ou "ASSET_EAM01"
            org=self.ed_org.text().strip(),           # ex.: "C001"
            user=self.ed_user.text().strip(),         # ex.: "ACOSTA"
            password=self.ed_pass.text().strip(),
            proxy_url="http://localhost:8000/eamproxy"  # se cloud; deixe None no on-prem
        )


        try:
            sid = get_valid_session(cfg)  # usa cache ou faz login
            self.ed_token.setText(sid)
            QMessageBox.information(self, "OK", "Sessão válida e salva.")
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))
