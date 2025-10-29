import threading
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout
)
from bt_monitor import BTMonitor
from soap_client import criar_ordem_servico


class DashboardBluetooth(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.cfg = None
        self.sid = None
        self.bt_monitor = None
        self.running = False

        # 🧱 Layout base
        self.label_status = QLabel("🔵 Aguardando conexão Bluetooth...")
        self.text_log = QTextEdit()
        self.text_log.setReadOnly(True)

        self.btn_connect = QPushButton("🔗 Conectar ao ESP32")
        self.btn_connect.clicked.connect(self.connect_bt)

        self.btn_disconnect = QPushButton("❌ Desconectar")
        self.btn_disconnect.clicked.connect(self.disconnect_bt)
        self.btn_disconnect.setEnabled(False)

        self.btn_sair = QPushButton("⬅️ Voltar")
        self.btn_sair.clicked.connect(self._on_sair_clicked)

        # 🔹 Layouts
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.btn_connect)
        buttons_layout.addWidget(self.btn_disconnect)
        buttons_layout.addWidget(self.btn_sair)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.label_status)
        main_layout.addWidget(self.text_log)
        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)

    # -------------------------------------------------------------
    def initialize_dashboard(self, cfg, sid):
        """Recebe configuração e sessão da tela de login."""
        self.cfg = cfg
        self.sid = sid
        self.text_log.clear()
        self.text_log.append("✅ Dashboard Bluetooth inicializado.")
        self.text_log.append(f"🔑 Sessão (SID): {sid[:10]}...\n")

    # -------------------------------------------------------------
    def connect_bt(self):
        """Inicia conexão com o ESP32 via Bluetooth."""
        if self.bt_monitor:
            self.text_log.append("⚠️ Já conectado ao ESP32.\n")
            return

        self.text_log.append("🔌 Tentando abrir porta COM7...\n")
        self.bt_monitor = BTMonitor(
            port="COM7",  # altere para a porta Bluetooth real
            baudrate=115200,
            on_event=self.on_bt_event,
            on_log=self.text_log.append
        )
        self.bt_monitor.start()
        self.label_status.setText("📡 Conectado ao ESP32 (aguardando eventos)...")
        self.btn_connect.setEnabled(False)
        self.btn_disconnect.setEnabled(True)

    def disconnect_bt(self):
        """Encerra o monitoramento Bluetooth."""
        if self.bt_monitor:
            self.bt_monitor.stop()
            self.bt_monitor = None
            self.label_status.setText("🔌 Bluetooth desconectado.")
            self.text_log.append("🛑 Conexão encerrada.\n")
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)

    # -------------------------------------------------------------
    def on_bt_event(self, data):
        """Recebe eventos JSON do ESP32."""
        device = data.get("device", "desconhecido")
        status = data.get("status", "sem_status")
        ts = datetime.now().strftime("%H:%M:%S")

        if status in ("online", "ok"):
            self.label_status.setText(f"✅ {device} online ({status})")
            self.text_log.append(f"[{ts}] {device} → {status}\n")

        elif status == "falha":
            self.label_status.setText(f"🚨 {device} falha detectada (Bluetooth)")
            self.text_log.append(f"[{ts}] {device} → FALHA detectada! Criando OS...\n")

            sucesso = criar_ordem_servico(
                local="Falha detectada via Bluetooth",
                nivel=0,
                timestamp=ts,
                cfg=self.cfg,
                sid=self.sid
            )
            if sucesso:
                self.text_log.append("✅ OS criada automaticamente (Bluetooth).\n")
            else:
                self.text_log.append("⚠️ Falha ao criar OS via Bluetooth.\n")

    # -------------------------------------------------------------
    def _on_sair_clicked(self):
        """Retorna ao menu principal."""
        if self.bt_monitor:
            self.bt_monitor.stop()
        self.main_window.show_menu()
