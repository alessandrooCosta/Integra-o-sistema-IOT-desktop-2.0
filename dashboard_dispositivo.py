import threading
import time
from datetime import datetime
import requests

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton
)

from soap_client import criar_ordem_servico
from iot_monitor import IoTMonitor


class WorkerSignals(QObject):
    update_status = pyqtSignal(str)
    log_message = pyqtSignal(str)


class DashboardDispositivo(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.cfg = None
        self.sid = None
        self.running = False
        self.device_id = "Maquina_01"

        layout = QVBoxLayout()

        self.label_status = QLabel("📡 Aguardando dados do dispositivo ESP32...")
        self.text_log = QTextEdit()
        self.text_log.setReadOnly(True)

        self.btn_start = QPushButton("▶️ Iniciar Monitoramento")
        self.btn_start.clicked.connect(self.toggle_monitoramento)

        self.btn_sair = QPushButton("Voltar")
        self.btn_sair.clicked.connect(self._on_sair_clicked)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.btn_start)
        button_layout.addWidget(self.btn_sair)

        layout.addWidget(self.label_status)
        layout.addWidget(self.text_log)
        layout.addLayout(button_layout)
        self.setLayout(layout)

        with open("assets/login_style.qss", "r", encoding="utf-8") as f:
            self.setStyleSheet(f.read())




    # -------------------------------------------------------------
    def initialize_dashboard(self, cfg, sid):
        self.cfg = cfg
        self.sid = sid
        self.text_log.clear()
        self.text_log.append("✅ Dashboard conectado ao servidor FastAPI.")
        self.text_log.append(f"🔑 Sessão (SID): {sid[:10]}...")

        # O IoTMonitor é iniciado, mas não interfere no loop principal
        self.iot_monitor = IoTMonitor(cfg, sid, self)
        self.iot_monitor.start()

    def _on_sair_clicked(self):
        """Retorna ao menu principal."""
        if self.iot_monitor:
            self.iot_monitor.stop()
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
        """Loop que consulta o status do ESP32 (na nuvem via Render)
        e cria uma OS automática quando o dispositivo fica offline.
        """
        signals = WorkerSignals()
        signals.update_status.connect(self.label_status.setText)
        signals.log_message.connect(self.text_log.append)

        api_url = f"http://fastapi-6wmq.onrender.com/status/{self.device_id}"
        falha_detectada = False

        while self.running:
            try:
                r = requests.get(api_url, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    online = data.get("online", False)
                    status = data.get("falha", "sem falha")
                    segmentos = data.get("segmentos", [])
                    ts = data.get("last_update", "")

                    if online:
                        msg = f"✅ {self.device_id} online | {status} | segmentos={segmentos}"
                        falha_detectada = False
                    else:
                        msg = f"⚠️ {self.device_id} offline ou sem dados."

                        if not falha_detectada:
                            falha_detectada = True
                            signals.log_message.emit(f"[{datetime.now():%H:%M:%S}] 🚨 {self.device_id} sem comunicação!")

                            sucesso = criar_ordem_servico(
                                local="Equipamento desconectado",
                                nivel=0,
                                timestamp=ts or datetime.now().isoformat(),
                                cfg=self.cfg,
                                sid=self.sid
                            )
                            if sucesso:
                                signals.log_message.emit("✅ OS criada automaticamente por desconexão.\n")
                            else:
                                signals.log_message.emit("⚠️ Falha ao criar OS de desconexão.\n")

                    signals.update_status.emit(msg)

                else:
                    signals.log_message.emit(f"⚠️ Erro HTTP {r.status_code} ao consultar status.")
            except Exception as e:
                signals.log_message.emit(f"❌ Erro de conexão: {e}")

            time.sleep(5)

