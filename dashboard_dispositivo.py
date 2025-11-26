import threading
import time
from datetime import datetime
import requests
import os
import sys

from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton
)

from soap_client import criar_ordem_servico

def resource_path(relative_path):
    """ Obtém o caminho absoluto para o recurso, funciona para dev e para PyInstaller """
    try:
        # PyInstaller cria uma pasta temporária e armazena o caminho em _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class WorkerSignals(QObject):
    update_status = pyqtSignal(str)
    log_message = pyqtSignal(str)
    update_icon = pyqtSignal(bool)  # 🔹 Novo sinal para o ícone visual


class DashboardDispositivo(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.cfg = None
        self.sid = None
        self.running = False
        self.device_id = "Maquina_01"

        layout = QVBoxLayout()

        # 🔹 Indicador visual de status (🟢 / 🔴)
        self.icon_label = QLabel("🔴 Dispositivo offline")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 18px; font-weight: bold; color: red;")

        self.label_status = QLabel("📡 Aguardando início do monitoramento...")
        self.label_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.text_log = QTextEdit()
        self.text_log.setReadOnly(True)

        # Botões
        self.btn_start = QPushButton("▶️ Iniciar Monitoramento")
        self.btn_start.clicked.connect(self.toggle_monitoramento)

        self.btn_sair = QPushButton("⬅️ Voltar")
        self.btn_sair.clicked.connect(self._on_sair_clicked)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.btn_start)
        button_layout.addWidget(self.btn_sair)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.label_status)
        layout.addWidget(self.text_log)
        layout.addLayout(button_layout)
        self.setLayout(layout)

        # Estilo
        qss_path = resource_path("assets/login_style.qss")
        with open(qss_path, "r", encoding="utf-8") as f:
            self.setStyleSheet(f.read())

    # -------------------------------------------------------------
    def initialize_dashboard(self, cfg, sid):
        self.cfg = cfg
        self.sid = sid
        self.text_log.clear()
        self.text_log.append("✅ Dashboard conectado ao servidor FastAPI.")
        self.text_log.append(f"🔑 Sessão (SID): {sid[:10]}...")

    # -------------------------------------------------------------
    def toggle_monitoramento(self):
        if not self.running:
            self.running = True
            self.btn_start.setText("⏹️ Parar Monitoramento")
            self.label_status.setText("🛰️ Iniciando monitoramento do ESP32...")
            self.text_log.append("\n🔄 Monitoramento iniciado...\n")
            threading.Thread(target=self._loop_monitor, daemon=True).start()
        else:
            self.running = False
            self.btn_start.setText("▶️ Iniciar Monitoramento")
            self.label_status.setText("📡 Monitoramento pausado.")
            self.icon_label.setText("🔴 Dispositivo offline")
            self.icon_label.setStyleSheet("font-size: 18px; font-weight: bold; color: red;")
            self.text_log.append("🛑 Monitoramento interrompido.\n")

    # -------------------------------------------------------------
    def _loop_monitor(self):
        signals = WorkerSignals()
        signals.update_status.connect(self.label_status.setText)
        signals.log_message.connect(self.text_log.append)
        signals.update_icon.connect(self._update_icon_label)

        api_url = f"https://fastapi-6wmq.onrender.com/status/{self.device_id}"

        ultima_falha = None
        ultima_data= None

        while self.running:
            try:
                r = requests.get(api_url, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    online = data.get("online", False)
                    falha = data.get("falha", "")
                    segmentos = data.get("segmentos", [])
                    ts = data.get("last_update", "")

                    # Atualiza ícone
                    signals.update_icon.emit(online)

                    # Exibe falhas reais
                    if online and falha.startswith("falha_"):
                        if ultima_falha != falha or ultima_data != ultima_data:
                            setor = segmentos[0] if segmentos else "não especificado"
                            tipo = falha.replace("falha_", "").capitalize()
                            msg = f"🚨 Falha detectada: {tipo} ({setor})"
                            signals.log_message.emit(msg)

                            sucesso = criar_ordem_servico(
                                local=f"{self.device_id} - {setor}",
                                nivel=0,
                                timestamp=ts or datetime.now().isoformat(),
                                cfg=self.cfg,
                                sid=self.sid
                            )
                            if sucesso:
                                signals.log_message.emit("✅ OS criada automaticamente no EAM.\n")
                            else:
                                signals.log_message.emit("⚠️ Erro ao criar OS.\n")

                            ultima_falha = falha
                            ultima_data = ts

                    elif not online:
                        signals.update_status.emit("⚠️ Dispositivo offline.")
                    else:
                            signals.update_status.emit("✅ Dispositivo online e estável.")

                else:
                    signals.log_message.emit(f"⚠️ Erro HTTP {r.status_code} ao consultar servidor.")
            except Exception as e:
                signals.log_message.emit(f"❌ Erro de conexão: {e}")

            time.sleep(5)

    # -------------------------------------------------------------
    def _update_icon_label(self, online: bool):
        """Atualiza o ícone visual 🟢/🔴"""
        if online:
            self.icon_label.setText("🟢 Dispositivo online")
            self.icon_label.setStyleSheet("font-size: 18px; font-weight: bold; color: green;")
        else:
            self.icon_label.setText("🔴 Dispositivo offline")
            self.icon_label.setStyleSheet("font-size: 18px; font-weight: bold; color: red;")

    # -------------------------------------------------------------
    def _on_sair_clicked(self):
        if self.running:
            self.running = False
            self.btn_start.setText("▶️ Iniciar Monitoramento")
        self.main_window.show_menu()
