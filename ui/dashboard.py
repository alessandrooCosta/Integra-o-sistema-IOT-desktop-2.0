import random
import threading
import time
from datetime import datetime
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton
from services.config_manager import load_config
from services.soap_client import criar_ordem_servico


class DashboardWindow(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window  # ✅ recebe referência da janela principal
        self.cfg = load_config()
        self.running = False

        layout = QVBoxLayout()

        self.label_status = QLabel("💧 Aguardando leituras do sensor...")
        self.text_log = QTextEdit()
        self.text_log.setReadOnly(True)

        self.btn_start = QPushButton("▶️ Iniciar Simulador")
        self.btn_start.clicked.connect(self.toggle_simulador)

        layout.addWidget(self.label_status)
        layout.addWidget(self.text_log)
        layout.addWidget(self.btn_start)
        self.setLayout(layout)

    def toggle_simulador(self):
        if not self.running:
            self.running = True
            self.btn_start.setText("⏹️ Parar Simulador")
            self.text_log.append("🔄 Simulador iniciado...\n")
            threading.Thread(target=self._loop_simulador, daemon=True).start()
        else:
            self.running = False
            self.btn_start.setText("▶️ Iniciar Simulador")
            self.text_log.append("🛑 Simulador parado.\n")

    def _loop_simulador(self):
        while self.running:
            nivel = random.uniform(0, 100)  # nível de água simulado em mm
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

            self.label_status.setText(f"💧 Nível atual: {nivel:.1f} mm ({timestamp})")
            self.text_log.append(f"[{timestamp}] Nível de água: {nivel:.1f} mm")

            # Se nível for crítico → aciona SOAP
            if nivel > 5:
                self.text_log.append("🚨 Nível crítico detectado! Tentando abrir OS no EAM...")
                local = "Pista Principal - Aeroporto"
                sucesso = criar_ordem_servico(local, nivel, timestamp, self.cfg)

                if sucesso:
                    self.text_log.append("✅ OS aberta com sucesso!\n")
                else:
                    self.text_log.append("⚠️ Falha ao abrir OS. Verifique o log.\n")

            time.sleep(5)  # intervalo entre leituras
