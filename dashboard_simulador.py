import random
import threading
import time
from datetime import datetime

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton
)
from soap_client import criar_ordem_servico


class WorkerSignals(QObject):
    """Define os sinais que a thread de trabalho pode emitir."""
    update_status = pyqtSignal(str)
    log_message = pyqtSignal(str)


class DashboardWindow(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window  # ✅ recebe referência da janela principal
        self.cfg = None
        self.sid = None
        self.running = False

        layout = QVBoxLayout()

        self.label_status = QLabel("💧 Aguardando leituras do sensor...")
        self.text_log = QTextEdit()
        self.text_log.setReadOnly(True)

        self.btn_start = QPushButton("▶️ Iniciar Simulador")
        self.btn_start.clicked.connect(self.toggle_simulador)

        self.btn_sair = QPushButton("Sair")
        self.btn_sair.clicked.connect(self._on_sair_clicked)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.btn_start)
        button_layout.addWidget(self.btn_sair)

        layout.addWidget(self.label_status)
        layout.addWidget(self.text_log)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def initialize_dashboard(self, cfg, sid):
        """
        Inicializa o dashboard com a configuração e o ID da sessão.
        Este método é chamado ANTES de o widget se tornar visível.
        """
        self.cfg = cfg
        self.sid = sid
        self.text_log.clear()
        self.text_log.append("✅ Dashboard inicializado e pronto para o monitoramento.")
        self.text_log.append(f"🔑 Sessão (SID) ativa: {sid[:10]}...")

    def _on_sair_clicked(self):
        """Notifica a janela principal para voltar à tela de login."""
        if self.running:
            self.toggle_simulador()  # Para o simulador se estiver rodando
        self.main_window.show_login_screen()

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
        # Cria um objeto de sinais e conecta-os aos métodos da GUI
        signals = WorkerSignals()
        signals.update_status.connect(self.label_status.setText)
        signals.log_message.connect(self.text_log.append)

        while self.running:
            nivel = random.uniform(0, 100)  # nível de água simulado em mm
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

            # Emite sinais para atualizar a GUI de forma segura a partir da thread
            signals.update_status.emit(f"💧 Nível atual: {nivel:.1f} mm ({timestamp})")
            signals.log_message.emit(f"[{timestamp}] Nível de água: {nivel:.1f} mm")

            # Se nível for crítico → aciona SOAP
            if nivel > 5:
                signals.log_message.emit("🚨 Nível crítico detectado! Tentando abrir OS no EAM...")
                local = "Pista Principal - Aeroporto"

                # Passa o sid para a função de criação da OS
                sucesso = criar_ordem_servico(
                    local=local,
                    nivel=nivel,
                    timestamp=timestamp,
                    cfg=self.cfg,
                    sid=self.sid
                )

                if sucesso:
                    signals.log_message.emit("✅ OS aberta com sucesso!\n")
                else:
                    signals.log_message.emit("⚠️ Falha ao abrir OS. Verifique o log.\n")

            time.sleep(5)  # intervalo entre leituras
