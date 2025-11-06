import threading
import time
from datetime import datetime
import requests

from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton
)

from soap_client import criar_ordem_servico
from iot_monitor import IoTMonitor


class WorkerSignals(QObject):
    update_status = pyqtSignal(str)
    log_message = pyqtSignal(str)
    update_connection = pyqtSignal(bool)


class DashboardDispositivo(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.cfg = None
        self.sid = None
        self.running = False
        self.device_id = "Maquina_01"

        layout = QVBoxLayout()

        # 🔹 Indicador visual de status
        self.connection_label = QLabel("🔴 Dispositivo offline")
        self.connection_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.connection_label.setStyleSheet("font-size: 16px; font-weight: bold; color: red;")

        # 🔹 Texto de status e log
        self.label_status = QLabel("📡 Aguardando dados do dispositivo ESP32...")
        self.text_log = QTextEdit()
        self.text_log.setReadOnly(True)

        # 🔹 Botões
        self.btn_start = QPushButton("▶️ Iniciar Monitoramento")
        self.btn_start.clicked.connect(self.toggle_monitoramento)

        self.btn_sair = QPushButton("Voltar")
        self.btn_sair.clicked.connect(self._on_sair_clicked)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.btn_start)
        button_layout.addWidget(self.btn_sair)

        layout.addWidget(self.connection_label)
        layout.addWidget(self.label_status)
        layout.addWidget(self.text_log)
        layout.addLayout(button_layout)
        self.setLayout(layout)

        # 🔹 Estilo
        with open("assets/login_style.qss", "r", encoding="utf-8") as f:
            self.setStyleSheet(f.read())

    # -------------------------------------------------------------
    def initialize_dashboard(self, cfg, sid):
        self.cfg = cfg
        self.sid = sid
        self.text_log.clear()
        self.text_log.append("✅ Dashboard conectado ao servidor FastAPI.")
        self.text_log.append(f"🔑 Sessão (SID): {sid[:10]}...")

        # Inicia monitor secundário (não interfere no loop principal)
        self.iot_monitor = IoTMonitor(cfg, sid, self)
        self.iot_monitor.start()

    def _on_sair_clicked(self):
        """Retorna ao menu principal."""
        if hasattr(self, "iot_monitor"):
            self.iot_monitor.stop()
        if self.running:
            self.running = False
            self.btn_start.setText("▶️ Iniciar Monitoramento")
        self.main_window.show_menu()

    # -------------------------------------------------------------
    def toggle_monitoramento(self):
        if not self.running:
            self.running = True
            self.btn_start.setText("⏹️ Parar Monitoramento")
            self.text_log.append("\n🔄 Monitoramento do ESP32 iniciado...\n")
            threading.Thread(target=self._loop_monitor, daemon=True).start()
        else:
            self.running = False
            self.btn_start.setText("▶️ Iniciar Monitoramento")
            self.text_log.append("🛑 Monitoramento interrompido.\n")

    # -------------------------------------------------------------
    def _loop_monitor(self):
        signals = WorkerSignals()
        signals.update_status.connect(self.label_status.setText)
        signals.log_message.connect(self.text_log.append)
        signals.update_connection.connect(self._update_connection_label)

        api_url = f"https://fastapi-6wmq.onrender.com/status/{self.device_id}"
        ultima_os = {"falha": None, "timestamp": datetime.min}

        while self.running:
            try:
                r = requests.get(api_url, timeout=20)
                if r.status_code == 200:
                    data = r.json()
                    online = data.get("online", False)
                    falha = data.get("falha", "sem falha")
                    setor = data.get("setor", "")
                    segmentos = data.get("segmentos", [])
                    ts = data.get("last_update", "")
                    now = datetime.now()

                    # Atualiza ícone 🟢🟡
                    signals.update_connection.emit(online)

                    # Log básico
                   # msg = f"{'✅' if online else '⚠️'} {self.device_id} {'online' if online else 'offline'} | {falha} | SETOR={setor or 'none'} | online={online}"
                   # signals.update_status.emit(msg)
                   # signals.log_message.emit(f"[{now:%H:%M:%S}] FALHA → {falha} | SETOR={setor or 'none'} | online={online}")

                    # ----------------------------------------------------------
                    # 📌 Cria OS apenas para falhas reais
                    # ----------------------------------------------------------
                    if online and falha.startswith("falha_") and falha not in ["falha_vibracao", "alive"]:
                        tempo_desde_ultima = (now - ultima_os["timestamp"]).total_seconds()
                        if falha != ultima_os["falha"] or tempo_desde_ultima > 60:
                            signals.log_message.emit(f"🚨 Falha detectada: {falha} em {setor or segmentos}")
                            try:
                                sucesso = criar_ordem_servico(
                                    local=f"{self.device_id} - {setor or 'sem_setor'}",
                                    nivel=0,
                                    timestamp=ts or now.isoformat(),
                                    cfg=self.cfg,
                                    sid=self.sid
                                )
                                ultima_os.update({"falha": falha, "timestamp": now})
                                if sucesso:
                                    signals.log_message.emit("✅ OS criada automaticamente por falha.\n")
                                else:
                                    signals.log_message.emit("⚠️ Falha ao criar OS de falha.\n")
                            except Exception as e:
                                signals.log_message.emit(f"❌ Erro ao criar OS de falha: {e}")

                    # ----------------------------------------------------------
                    # 🚫 Nunca cria OS por desconexão → apenas loga
                    # ----------------------------------------------------------
                    if not online:
                      signals.log_message.emit(f"[{now:%H:%M:%S}] ⚠️")

                else:
                    signals.log_message.emit(f"⚠️ Erro HTTP {r.status_code} ao consultar status.")

            except Exception as e:
                signals.log_message.emit(f"❌ Erro de conexão: {e}")

            time.sleep(5)

    # -------------------------------------------------------------
    def _update_connection_label(self, online: bool):
        """Atualiza ícone de status visual"""
        if online:
            self.connection_label.setText("🟢 Dispositivo online")
            self.connection_label.setStyleSheet("font-size: 16px; font-weight: bold; color: green;")
        else:
            self.connection_label.setText("🟡 Dispositivo offline (sem comunicação)")
            self.connection_label.setStyleSheet("font-size: 16px; font-weight: bold; color: orange;")
