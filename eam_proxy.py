from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import httpx

# ==============================================================
# ⚙️ Configurações gerais
# ==============================================================

EAM_URL = "https://us1.eam.hxgnsmartcloud.com/axis/services/EWSConnector"
API_KEY = "aea718747d-b616-40bd-ade4-9931dc98de38"

app = FastAPI(title="EAM Proxy + IoT Integration", version="2.0")

# ==============================================================
# 📊 Banco em memória: status dos dispositivos IoT
# ==============================================================

devices_status = {}

# ==============================================================
# 🔁 Rota SOAP → Proxy entre o App Desktop e o EAM Cloud
# ==============================================================

@app.post("/eamproxy")
async def eam_proxy(request: Request):
    """
    Recebe requisições SOAP do App (Dashboard Simulador) e as encaminha
    ao EAM Cloud adicionando o API Key.
    """
    xml_body = await request.body()
    headers_in = dict(request.headers)

    headers_out = {
        "Content-Type": headers_in.get("content-type", "text/xml;charset=UTF-8"),
        "SOAPAction": headers_in.get("soapaction", ""),
        "x-api-key": API_KEY,
    }

    print("\n📨 Repassando requisição SOAP para EAM...")
    print(f"🔗 Destino: {EAM_URL}")
    print(f"📋 Headers: {headers_out}")
    print("🧾 XML (trecho):")
    print(xml_body.decode("utf-8")[:600])
    print("------------------------------------------------")

    async with httpx.AsyncClient(verify=True, timeout=60) as client:
        try:
            resp = await client.post(EAM_URL, content=xml_body, headers=headers_out)
            print(f"📬 Resposta EAM: {resp.status_code}")
            print(resp.text[:400])
            print("------------------------------------------------")
            return Response(
                content=resp.text,
                status_code=resp.status_code,
                media_type=resp.headers.get("content-type", "text/xml"),
            )
        except Exception as e:
            print(f"❌ Erro ao enviar SOAP: {e}")
            return Response(
                content=f"<error>Proxy error: {e}</error>",
                status_code=500,
                media_type="text/xml",
            )

# ==============================================================
# 🌐 Endpoint IoT → Recebe eventos do ESP32
# ==============================================================

@app.post("/event")
async def receive_event(request: Request):
    """
    Recebe dados do ESP32 (status do dispositivo).
    Exemplo JSON recebido:
    {
        "device": "MOTOR_A",
        "status": "ok"
    }
    """
    data = await request.json()
    device = data.get("device", "desconhecido")
    status = data.get("status", "sem_status")
    timestamp = datetime.now()

    devices_status[device] = {"status": status, "last_update": timestamp}

    print(f"\n📡 {device} → {status} ({timestamp})")
    return {"message": "Evento recebido com sucesso!"}

# ==============================================================
# 📈 Endpoint → Consulta status atual de um dispositivo
# ==============================================================

@app.get("/status/{device_id}")
async def get_status(device_id: str):
    """
    Retorna o status e o último horário de atualização do dispositivo.
    """
    info = devices_status.get(device_id)
    if not info:
        # Mesmo que não exista, retorna HTTP 200 (evita 404 no Dashboard)
        return JSONResponse(
            content={
                "device": device_id,
                "status": "desconhecido",
                "online": False
            },
            status_code=200
        )

    delta = datetime.now() - info["last_update"]
    online = delta < timedelta(seconds=10)

    return JSONResponse(
        content={
            "device": device_id,
            "status": info["status"],
            "last_update": info["last_update"].isoformat(),
            "online": online
        },
        status_code=200
    )

# ==============================================================
# 🔍 Endpoint básico de teste
# ==============================================================

@app.get("/")
def root():
    return {"status": "ok", "message": "EAM Proxy + IoT rodando com sucesso."}

# ==============================================================
# 🚀 Execução local
# ==============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
