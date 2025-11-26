import asyncio
import json
from bleak import BleakScanner, BleakClient
from PyQt6.QtCore import QThread, pyqtSignal

# UUIDs do ESP32 (de ble_comando.ino)
DEVICE_NAME = "Maquina_01_Monitor"
SERVICE_UUID = "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
STATUS_CHAR_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8" # Notificação (ESP32 -> App)
CMD_CHAR_UUID = "a7891234-7339-4d6f-871d-a026e7d1746f"   # Escrita (App -> ESP32)

class BLEMonitorThread(QThread):
    """
    Thread dedicada para gerenciar a conexão assíncrona BLE (via bleak).
    Comunica-se com a thread principal do PyQt6 usando sinais.
    """
    # Sinais para comunicação segura com a Thread principal do GUI
    signal_log = pyqtSignal(str)
    signal_connected = pyqtSignal()
    signal_disconnected = pyqtSignal()
    signal_event_received = pyqtSignal(dict) # Emite o dicionário de evento JSON

    def __init__(self, parent=None):
        super().__init__(parent)
        self._address = None
        self._client = None
        self._loop = None
        self._running = False
        self._is_connected = False

    def run(self):
        """Método executado quando a thread é iniciada."""
        self._running = True
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            self.signal_log.emit("Thread BLE iniciada. Varrendo...")
            self._loop.run_until_complete(self._connect_and_monitor())
        except Exception as e:
            self.signal_log.emit(f"❌ Erro fatal no loop assíncrono: {e}")
        finally:
            self._loop.close()
            self._running = False
            self._is_connected = False
            self.signal_log.emit("Thread BLE encerrada.")

    async def _connect_and_monitor(self):
        """Lógica principal de varredura, conexão e monitoramento."""

        device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=10.0)

        if not device:
            self.signal_log.emit(f"❌ Dispositivo '{DEVICE_NAME}' não encontrado após 10s.")
            self.signal_disconnected.emit()
            return

        self._address = device.address
        self.signal_log.emit(f"✅ Dispositivo encontrado: {self._address}")

        try:
            # Usamos o callback de desconexão para gerenciar falhas de link
            self._client = BleakClient(self._address, disconnected_callback=self._on_disconnect)
            self.signal_log.emit("🔗 Tentando conectar...")
            await self._client.connect()
            self._is_connected = True
            self.signal_connected.emit()

            # 1. Assinar Notificações de Status/Evento
            self.signal_log.emit("🔔 Assinando notificações de EVENTOS...")
            await self._client.start_notify(STATUS_CHAR_UUID, self._notification_handler)

            # 2. Mantém o loop rodando enquanto estiver conectado
            while self._is_connected and self._running:
                await asyncio.sleep(1) # Mantém o loop de eventos ativo

        except Exception as e:
            self.signal_log.emit(f"❌ Erro de conexão/monitoramento: {e}")
        finally:
            self._is_connected = False
            if self._client and self._client.is_connected:
                await self._client.disconnect()
            self._client = None
            # O sinal de desconexão já é emitido pelo _on_disconnect ou na falha acima

    def _on_disconnect(self, client):
        """Callback executado quando o dispositivo BLE se desconecta."""
        if self._is_connected:
            self.signal_log.emit("💔 Dispositivo desconectado pelo ESP32 ou falha de link.")
        self._is_connected = False
        self.signal_disconnected.emit()


    def _notification_handler(self, characteristic, data: bytearray):
        """Lida com os dados recebidos via NOTIFY (ESP32 -> App)."""
        try:
            # Lógica do seu código de exemplo: Decodificar e parsear JSON
            msg = data.decode("utf-8")
            evento = json.loads(msg)
            self.signal_log.emit(f"📩 JSON Evento Recebido: {msg}")
            self.signal_event_received.emit(evento) # Envia o dicionário para o Dashboard
        except Exception as e:
            self.signal_log.emit(f"❌ Erro ao decodificar/parsear JSON: {e}")

    async def _async_send_command(self, command: str):
        """Função assíncrona para enviar comandos."""
        if not self._client or not self._is_connected:
            self.signal_log.emit("⚠️ Não conectado. Falha ao enviar comando.")
            return

        try:
            # Envia o comando para a característica de CMD
            await self._client.write_gatt_char(CMD_CHAR_UUID, command.encode('utf-8'), response=True)
            self.signal_log.emit(f"⬆️ Comando '{command}' enviado com sucesso.")
        except Exception as e:
            self.signal_log.emit(f"❌ Erro ao enviar comando: {e}")

    def send_command(self, command: str):
        """Envia comandos (RESET) para o ESP32 (thread-safe)."""
        if self._loop and self._is_connected:
            # Agendamos a função assíncrona para ser executada no loop de eventos
            asyncio.run_coroutine_threadsafe(self._async_send_command(command), self._loop)
        else:
            self.signal_log.emit("⚠️ Não foi possível enviar o comando. Conexão inativa.")

    def stop(self):
        """Encerra a conexão e a thread."""
        self._running = False
        if self._loop and self._loop.is_running():
            # Agenda o encerramento da thread no loop
            self._loop.call_soon_threadsafe(self._loop.stop)
        self.wait(2000) # Espera a thread terminar (2 segundos)
        self.signal_log.emit("🛑 Tentativa de encerramento de thread.")