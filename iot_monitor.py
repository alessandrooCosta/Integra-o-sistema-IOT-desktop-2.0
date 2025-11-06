import threading
import time
import requests
from datetime import datetime
# Importa a função de criação de OS
from PyQt6.QtCore import QObject, pyqtSignal
from soap_client import criar_ordem_servico

class WorkerSignals(QObject):
    """Define os sinais disponíveis para a thread de trabalho."""
    log_message = pyqtSignal(str)
    status_update = pyqtSignal(str)
    error = pyqtSignal(str)

class IoTMonitor:
    def __init__(self, cfg, sid, dashboard, interval=20):
        """
        cfg: configurações EAM (objeto EAMConfig)
        sid: sessão autenticada
        dashboard: referência para o widget PyQt (para atualizar logs e status)
        interval: intervalo de consulta (segundos)
        """
        self.cfg = cfg
        self.sid = sid
        self.dashboard = dashboard

        # Configura os sinais para comunicação segura com a GUI
        self.signals = WorkerSignals()
        self.signals.log_message.connect(self.dashboard.text_log.append)
        self.signals.status_update.connect(self.dashboard.label_status.setText)
        self.signals.error.connect(lambda msg: self.dashboard.text_log.append(f"❌ {msg}"))

        self.interval = interval
        self.running = False
        self.render_api = "https://fastapi-6wmq.onrender.com/status/Maquina_01"
    def start(self):
        """Inicia a thread de monitoramento"""
        if not self.running:
            self.running = True
            t = threading.Thread(target=self._loop, daemon=True)
            t.start()
            self.signals.log_message.emit("🛰️ Iniciando monitoramento do dispositivo no Render...")
        else:
            self.signals.log_message.emit("ℹ️ Monitoramento já está em execução.")

    def stop(self):
        """Para o monitoramento"""
        self.running = False
        self.signals.log_message.emit("🛑 Monitoramento interrompido.")

    def _loop(self):
        while self.running:
            try:
                resp = requests.get(self.render_api, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("falha", "sem_falha")
                    setor = data.get("setor", "")
                    online = data.get("online", False)
                    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

                    self.signals.status_update.emit(f"🌐 {status.upper()} | {setor}")
                    self.signals.log_message.emit(f"[{timestamp}] FALHA → {status} | SETOR={setor} | online={online}")

                    if status == "_falha":
                        self.signals.log_message.emit("🚨 Falha detectada! Criando O.S. no EAM...")
                        local = "Equipamento Maquina_01"
                        nivel = "N/A"

                        sucesso = criar_ordem_servico(
                            local=local,
                            nivel=nivel,
                            timestamp=timestamp,
                            cfg=self.cfg,
                            sid=self.sid
                        )

                        if sucesso:
                            self.signals.log_message.emit("✅ O.S. aberta com sucesso no EAM.\n")
                        else:
                            self.signals.log_message.emit("⚠️ Falha ao abrir O.S. no EAM.\n")

                else:
                    self.signals.error.emit(f"Erro HTTP {resp.status_code} ao consultar status.")

            except Exception as e:
                self.signals.error.emit(f"Erro no monitoramento: {e}")

            time.sleep(self.interval)
