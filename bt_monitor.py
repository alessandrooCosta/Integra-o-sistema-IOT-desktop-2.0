# bt_monitor.py
import threading
import time
import json
import serial  # pip install pyserial
from datetime import datetime

class BTMonitor(threading.Thread):
    def __init__(self, port: str, baudrate: int = 115200, on_event=None, on_log=None):
        super().__init__(daemon=True)
        self.port = port
        self.baudrate = baudrate
        self.on_event = on_event  # callback(dict)
        self.on_log = on_log      # callback(str)
        self._stop = False
        self.ser = None

    def log(self, msg):
        if self.on_log:
            self.on_log(msg)

    def stop(self):
        self._stop = True
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
        except:
            pass

    def run(self):
        while not self._stop:
            try:
                if not self.ser or not self.ser.is_open:
                    self.log(f"🔌 Abrindo porta {self.port} @ {self.baudrate}...")
                    self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
                    self.log("✅ Porta aberta.")

                line = self.ser.readline().decode(errors='ignore').strip()
                if not line:
                    continue

                self.log(f"📥 BT RX: {line}")
                try:
                    data = json.loads(line)
                    if self.on_event:
                        self.on_event(data)  # ex.: {"device":"MOTOR_A","status":"ok"}
                except json.JSONDecodeError:
                    self.log("⚠️ JSON inválido no BT.")

            except (serial.SerialException, OSError) as e:
                self.log(f"❌ Erro BT: {e}. Tentando reconectar em 3s...")
                time.sleep(3)
            except Exception as e:
                self.log(f"❌ Erro inesperado BT: {e}")
                time.sleep(1)
