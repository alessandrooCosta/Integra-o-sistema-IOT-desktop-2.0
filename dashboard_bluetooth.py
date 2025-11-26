import threading
import json
import os
import sys
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout, QMessageBox
)
from PyQt6.QtCore import pyqtSlot, Qt
from ble_monitor_thread import BLEMonitorThread # Importa o módulo BLE correto
from soap_client import criar_ordem_servico # Mantido para a lógica de OS

def resource_path(relative_path):
    """ Obtém o caminho absoluto para o recurso, funciona para dev e para PyInstaller """
    try:
        # PyInstaller cria uma pasta temporária e armazena o caminho em _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class DashboardBluetooth(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.cfg = None
        self.sid = None
        self.ble_monitor = None
        self.current_event_data = {} # Armazena o último evento JSON

        # 🧱 Layout base
        self.icon_label = QLabel("Dispositivo: Não conectado.")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 18px; font-weight: bold; color: red;")

        self.label_status = QLabel("Aguardando início do monitoramento...")
        self.label_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.text_log = QTextEdit()
        self.text_log.setReadOnly(True)

        self.btn_connect = QPushButton("Conectar ao ESP32 (BLE)")
        self.btn_connect.clicked.connect(self.start_ble_monitoring)

        self.btn_reset_cmd = QPushButton("Enviar Comando RESET")
        self.btn_reset_cmd.clicked.connect(self.send_reset_command)
        self.btn_reset_cmd.setEnabled(False)

        self.btn_disconnect = QPushButton("Desconectar")
        self.btn_disconnect.clicked.connect(self.disconnect_ble)
        self.btn_disconnect.setEnabled(False)

        self.btn_sair = QPushButton("Voltar")
        self.btn_sair.clicked.connect(self._on_sair_clicked)

        # 🔹 Layouts
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.btn_connect)
       # buttons_layout.addWidget(self.btn_reset_cmd)
        buttons_layout.addWidget(self.btn_disconnect)
        buttons_layout.addWidget(self.btn_sair)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.icon_label)
        main_layout.addWidget(self.label_status)
        main_layout.addWidget(self.text_log)
        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)

        qss_path = resource_path("assets/login_style.qss")
        with open(qss_path, "r", encoding="utf-8") as f:
            self.setStyleSheet(f.read())

    # -------------------------------------------------------------
    def initialize_dashboard(self, cfg, sid):
        """Recebe configuração e sessão da tela de login."""
        self.cfg = cfg
        self.sid = sid
        self.text_log.clear()
        self.text_log.append("✅ Conexão Bluetooth (BLE) inicializada.")
        self.text_log.append(f"🔑 Sessão (SID): {sid[:10]}...\n")

    # -------------------------------------------------------------
    @pyqtSlot()
    def start_ble_monitoring(self):
        """Inicia a varredura e tenta conexão BLE."""
        if self.ble_monitor and self.ble_monitor.isRunning():
            self.text_log.append("⚠️ O monitoramento BLE já está em andamento.\n")
            return

        # Inicializa o monitor BLE (QThread)
        self.ble_monitor = BLEMonitorThread()

        # Conecta os Sinais do Monitor aos Slots do Dashboard
        self.ble_monitor.signal_log.connect(self.text_log.append)
        self.ble_monitor.signal_connected.connect(self.on_ble_connected)
        self.ble_monitor.signal_disconnected.connect(self.on_ble_disconnected)
        self.ble_monitor.signal_event_received.connect(self.on_ble_event_received)

        self.text_log.append("Iniciando varredura e conexão BLE...")
        self.btn_connect.setEnabled(False)
        self.btn_disconnect.setEnabled(False)
        self.btn_reset_cmd.setEnabled(False)

        # Inicia a thread
        self.ble_monitor.start()

    @pyqtSlot()
    def disconnect_ble(self):
        """Encerra o monitoramento BLE."""
        if self.ble_monitor:
            self.ble_monitor.stop()
            # A thread irá emitir signal_disconnected ao encerrar,
            # que chamará on_ble_disconnected, limpando self.ble_monitor
            # para evitar chamadas duplicadas.
        else:
            self.on_ble_disconnected()

    @pyqtSlot()
    def on_ble_connected(self):
        """Slot chamado quando a conexão BLE é estabelecida."""
        self.label_status.setText("Conectado ao ESP32 (BLE). Aguardando eventos...")
        self.text_log.append("Conexão BLE estabelecida e Notificações assinadas.")
        self.btn_connect.setEnabled(False)
        self.btn_disconnect.setEnabled(True)
        self.btn_reset_cmd.setEnabled(True)

    @pyqtSlot()
    def on_ble_disconnected(self):
        """Slot chamado quando a conexão BLE é encerrada."""
        self.label_status.setText("🔵 Bluetooth: Não conectado.")
        self.text_log.append("🛑 Cliente BLE desconectado.")
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)
        self.btn_reset_cmd.setEnabled(False)
        self.ble_monitor = None

    @pyqtSlot(dict)
    def on_ble_event_received(self, event_data: dict):
        """
        Recebe e processa o dicionário de evento JSON do ESP32.
        Estrutura esperada: {"device": "...", "falha": "...", "setor": "..."}
        """
        ts = datetime.now().strftime("%H:%M:%S")
        self.current_event_data = event_data # Armazena o último evento

        device = event_data.get("device", "N/A")
        falha = event_data.get("falha", "N/A")
        setor = event_data.get("setor", "N/A")

        self.label_status.setText(f"🚨 Último Evento: {falha} no {setor}")
        self.text_log.append(f"[{ts}] 📩 Evento Recebido de {device}: Falha={falha}, Setor={setor}")

        # Lógica para criar OS se a falha não for um "reset"
        if falha.lower() not in ("reset", "reset_ble", "reset_botao"):
            self.text_log.append("🔔 Falha detectada! Criando O.S. automática...")

            # Assumindo que criar_ordem_servico existe e é funcional
            sucesso = criar_ordem_servico(
                local=f"Falha {falha} detectada no {setor} via Bluetooth",
                nivel=0,
                timestamp=ts,
                cfg=self.cfg,
                sid=self.sid
            )
            if sucesso:
                self.text_log.append("✅ OS criada automaticamente (BLE).\n")
            else:
                self.text_log.append("⚠️ Falha ao criar OS via BLE.\n")
        else:
            self.text_log.append(f"[{ts}] Comando de {falha.upper()} recebido/enviado.\n")

    # -------------------------------------------------------------
    @pyqtSlot()
    def send_reset_command(self):
        """Envia o comando RESET para o ESP32 via Característica de Escrita."""
        if not self.ble_monitor or not self.ble_monitor._is_connected:
            QMessageBox.warning(self, "Aviso", "Não conectado. Não é possível enviar o comando RESET.")
            return

        self.text_log.append("Enviando comando 'RESET' via BLE...")
        self.ble_monitor.send_command("RESET")

    # -------------------------------------------------------------
    @pyqtSlot()
    def _on_sair_clicked(self):
        """Retorna ao menu principal."""
        self.disconnect_ble()
        self.main_window.show_menu()