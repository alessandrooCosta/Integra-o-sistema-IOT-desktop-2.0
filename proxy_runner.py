import subprocess
import sys
import os
import time
import threading
import socket

def _port_is_open(host="127.0.0.1", port=8080, timeout=0.5):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

def run_proxy():
    """Executa o proxy FastAPI em background e garante que esteja pronto."""
    project_dir = os.path.dirname(os.path.abspath(__file__))
    proxy_file = os.path.join(project_dir, "eam_proxy.py")

    if _port_is_open("127.0.0.1", 8080):
        print("⚙️ Proxy já está em execução em http://localhost:8080")
        return

    print(f"🚀 Iniciando proxy local: {proxy_file}")

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NO_WINDOW  # 👈 evita abrir o CMD

    process =subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "eam_proxy:app", "--host", "0.0.0.0", "--port", "8080"],
        cwd = project_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags
    )

    # Aguarda o proxy subir
    for _ in range(40):
        if _port_is_open("127.0.0.1", 8080):
            print("✅ Proxy iniciado COM SUCESSO em http://localhost:8080")
            return
        time.sleep(0.25)

    print("⚠️ Não foi possível CONFIRMAR o proxy. Verifique logs.")

def start_proxy():
    """Inicia o proxy em thread separada (não trava a UI)."""
    t = threading.Thread(target=run_proxy, daemon=True)
    t.start()
    time.sleep(1)

