from fastapi import FastAPI, Request, Response
import httpx

# ==============================================================
# ⚙️ Configurações básicas
# ==============================================================

# URL do conector SOAP real do EAM Cloud
EAM_URL = "https://us1.eam.hxgnsmartcloud.com/axis/services/EWSConnector"

# Sua API Key (registrada no tenant)
API_KEY = "aea718747d-b616-40bd-ade4-9931dc98de38"

# Cria instância FastAPI
app = FastAPI(title="EAM Proxy", version="1.0")

# ==============================================================
# 🔁 Rota principal do proxy
# ==============================================================

@app.post("/eamproxy")
async def eam_proxy(request: Request):
    """
    Repassa qualquer requisição SOAP recebida para o EAM Cloud,
    adicionando a API Key e mantendo o XML original.
    """
    # Lê o corpo XML enviado pelo cliente (PyQt)
    xml_body = await request.body()

    # Headers originais
    headers_in = dict(request.headers)
    # Headers SOAP para envio ao EAM
    headers_out = {
        "Content-Type": headers_in.get("content-type", "text/xml;charset=UTF-8"),
        "SOAPAction": headers_in.get("soapaction", ""),
        "x-api-key": API_KEY,
    }

    print("📨 Repassando requisição SOAP para EAM...")
    print(f"🔗 Destino: {EAM_URL}")
    print(f"📋 Headers: {headers_out}")
    print("🧾 XML Enviado:")
    print(xml_body.decode("utf-8"))
    print("------------------------------------------------")

    # Envia para o EAM real
    async with httpx.AsyncClient(verify=True, timeout=60) as client:
        try:
            resp = await client.post(EAM_URL, content=xml_body, headers=headers_out)
            print(f"📬 Resposta EAM: {resp.status_code}")
            print(resp.text[:800])
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
# 🚀 Execução local (modo standalone)
# ==============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)