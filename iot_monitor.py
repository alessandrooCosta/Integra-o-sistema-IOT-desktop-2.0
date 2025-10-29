import threading
import time
import requests
from datetime import datetime

# Importa a função de criação de OS
from soap_client import criar_ordem_servico

class IoTMonitor:
    def __init__(self, cfg, sid, dashboard, interval=5):
        """
        cfg: configurações EAM (objeto EAMConfig)
        sid: sessão autenticada
        dashboard: referência para o widget PyQt (para atualizar logs e status)
        interval: intervalo de consulta (segundos)
        """
        self.cfg = cfg
        self.sid = sid
        self.dashboard = dashboard
        self.interval = interval
        self.running = False
        self.render_api = "https://fastapi-6wmq.onrender.com/status/MOTOR_A"

    def start(self):
        """Inicia a thread de monitoramento"""
        if not self.running:
            self.running = True
            t = threading.Thread(target=self._loop, daemon=True)
            t.start()
            self.dashboard.text_log.append("🛰️ Iniciando monitoramento do dispositivo no Render...")
        else:
            self.dashboard.text_log.append("ℹ️ Monitoramento já está em execução.")

    def stop(self):
        """Para o monitoramento"""
        self.running = False
        self.dashboard.text_log.append("🛑 Monitoramento interrompido.")

    def _loop(self):
        while self.running:
            try:
                resp = requests.get(self.render_api, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status", "desconhecido")
                    online = data.get("online", False)
                    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

                    self.dashboard.label_status.setText(f"🌐 {status.upper()} ({timestamp})")
                    self.dashboard.text_log.append(f"[{timestamp}] STATUS → {status} | online={online}")

                    if status == "falha":
                        self.dashboard.text_log.append("🚨 Falha detectada! Criando O.S. no EAM...")
                        local = "Equipamento MOTOR_A"
                        nivel = "N/A"

                        sucesso = criar_ordem_servico(
                            local=local,
                            nivel=nivel,
                            timestamp=timestamp,
                            cfg=self.cfg,
                            sid=self.sid
                        )

                        if sucesso:
                            self.dashboard.text_log.append("✅ O.S. aberta com sucesso no EAM.\n")
                        else:
                            self.dashboard.text_log.append("⚠️ Falha ao abrir O.S. no EAM.\n")

                else:
                    self.dashboard.text_log.append(f"⚠️ Erro HTTP {resp.status_code} ao consultar status.")

            except Exception as e:
                self.dashboard.text_log.append(f"❌ Erro no monitoramento: {e}")

            time.sleep(self.interval)
