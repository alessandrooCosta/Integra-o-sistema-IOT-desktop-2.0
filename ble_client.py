import asyncio
import json
from bleak import BleakScanner, BleakClient
from datetime import datetime

# Mesmo UUID do ESP32
SERVICE_UUID = "12345678-1234-1234-1234-1234567890ab" #
CHARACTERISTIC_UUID = "abcdef12-3456-7890-abcd-ef1234567890" #

ESP32_NAME = "ESP32_EAM_Device"

# =========================================================
# Callback executado ao receber dados BLE do ESP32
# =========================================================
def notification_handler(sender, data: bytearray):
    try:
        msg = data.decode("utf-8")
        evento = json.loads(msg)
        ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        print(f"\n[{ts}] 📩 Evento recebido via BLE:")
        print(f" → Dispositivo: {evento.get('device')}")
        print(f" → Falha: {evento.get('falha')}")
        print(f" → Setor: {evento.get('setor')}\n")

        # 🔹 Aqui futuramente você pode criar O.S. automática
        # criar_ordem_servico(local=evento["setor"], nivel=0, ...)
    except Exception as e:
        print("❌ Erro ao processar evento:", e)

# =========================================================
# Descobre e conecta ao ESP32
# =========================================================
async def connect_ble():
    print("🔍 Procurando dispositivo BLE...")
    devices = await BleakScanner.discover(timeout=6)

    esp32 = next((d for d in devices if ESP32_NAME in d.name), None)
    if not esp32:
        print("⚠️ ESP32 não encontrado. Certifique-se de que está pareado e anunciando.")
        return

    print(f"✅ Dispositivo encontrado: {esp32.name} ({esp32.address})")
    async with BleakClient(esp32) as client:
        print("🔗 Conectado ao ESP32!")
        await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
        print("🛰️ Monitorando eventos BLE...\n")

        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Encerrando conexão BLE...")
            await client.stop_notify(CHARACTERISTIC_UUID)

# =========================================================
# Execução principal
# =========================================================
if __name__ == "__main__":
    try:
        asyncio.run(connect_ble())
    except Exception as e:
        print("❌ Erro:", e)
