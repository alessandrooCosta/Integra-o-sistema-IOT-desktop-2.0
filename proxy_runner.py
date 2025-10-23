# proxy_runner.py
import subprocess
import sys
import os
import time
import threading
import socket

def _port_is_open(host="127.0.0.1", port=8000, timeout=0.5):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

def run_proxy():
    """Executa o proxy FastAPI em background, sem travar o PyQt."""
    proxy_path = os.path.join(os.path.dirname(__file__), "eam_proxy.py")

    # Já está no ar?
    if _port_is_open("127.0.0.1", 8000):
        print("⚙️ Proxy já em execução em http://localhost:8000")
        return

    print("🚀 Iniciando proxy local em background...")

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_CONSOLE

    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "eam_proxy:app", "--host", "0.0.0.0", "--port", "8000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags
    )

    # aguarda subir
    for _ in range(30):
        if _port_is_open("127.0.0.1", 8000):
            print("✅ Proxy iniciado em http://localhost:8000")
            return
        time.sleep(0.2)

    print("⚠️ Não foi possível confirmar o proxy na porta 8000.")

def start_proxy():
    """Inicia o proxy em uma thread para não travar a UI."""
    t = threading.Thread(target=run_proxy, daemon=True)
    t.start()
    time.sleep(0.5)
