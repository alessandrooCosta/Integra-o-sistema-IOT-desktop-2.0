import requests
from urllib.parse import urlparse

# ===============================================================
# 🔧 Função auxiliar: gerar endpoint SOAP automaticamente
# ===============================================================
def _gerar_endpoint_soap(url_informada: str) -> str:
    """
    Recebe a URL digitada pelo usuário e retorna o endpoint SOAP correto.
    Exemplo:
      Entrada:  http://192.168.15.9:7575/web/base/logout?tenant=ASSET_EAM01
      Saída:    http://192.168.15.9:7575/axis/services/EWSConnector
    """
    parsed = urlparse(url_informada)
    if not parsed.scheme or not parsed.hostname:
        return url_informada  # evita erro se algo inesperado vier

    base = f"{parsed.scheme}://{parsed.hostname}"
    if parsed.port:
        base += f":{parsed.port}"
    return f"{base}/axis/services/EWSConnector"


# ===============================================================
# 🔍 Função: testar conexão SOAP
# ===============================================================
def testar_conexao(url, user, password, org):
    """
    Testa a conectividade SOAP com o EAM.
    Verifica se o endpoint é acessível e se o servidor responde corretamente.
    """
    url_soap = _gerar_endpoint_soap(url)
    print(f"🔗 Testando endpoint SOAP: {url_soap}")

    envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
        <soapenv:Header/>
        <soapenv:Body>
            <ping>teste</ping>
        </soapenv:Body>
    </soapenv:Envelope>"""

    headers = {
        "Content-Type": "text/xml;charset=UTF-8",
        "SOAPAction": ""
    }

    try:
        r = requests.post(url_soap, data=envelope.encode("utf-8"), headers=headers, timeout=10, verify=False)
        print(f"📬 Status HTTP: {r.status_code}")
        if r.status_code in [200, 500]:
            print("✅ Conexão estabelecida (servidor respondeu).")
            return True
        else:
            print("⚠️ Servidor não respondeu como esperado.")
            return False
    except Exception as e:
        print(f"🚨 Erro ao testar conexão: {e}")
        return False


# ===============================================================
# ⚙️ Função principal: criar ordem de serviço (OS)
# ===============================================================
def criar_ordem_servico(local, nivel, timestamp, cfg):
    """
    Cria uma Ordem de Serviço no EAM via SOAP.
    """
    descricao = f"Alerta: nível de água {nivel}mm em {local}"[:80]
    url_soap = _gerar_endpoint_soap(cfg.get("url"))

    print(f"📡 Enviando requisição SOAP para {url_soap} ...")

    envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
    <soapenv:Envelope
        xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:mp="http://schemas.datastream.net/MP_functions/MP0023_001"
        xmlns:wo="http://schemas.datastream.net/MP_entities/WorkOrder_001"
        xmlns:wsse="http://schemas.xmlsoap.org/ws/2002/04/secext"
        xmlns:mf="http://schemas.datastream.net/MP_fields">

        <soapenv:Header>
            <wsse:Security>
                <wsse:UsernameToken>
                    <wsse:Username>{cfg['user']}</wsse:Username>
                    <wsse:Password>{cfg['password']}</wsse:Password>
                </wsse:UsernameToken>
            </wsse:Security>
            <Organization xmlns="http://schemas.datastream.net/headers">{cfg['org']}</Organization>
        </soapenv:Header>

        <soapenv:Body>
            <mp:MP0023_AddWorkOrder_001 verb="Add" noun="WorkOrder" version="001" callname="AddWorkOrder">
                <wo:WorkOrder>
                    <mf:WORKORDERID auto_generated="true">
                        <mf:JOBNUM></mf:JOBNUM>
                        <mf:ORGANIZATIONID entity="User">
                            <mf:ORGANIZATIONCODE>{cfg['org']}</mf:ORGANIZATIONCODE>
                        </mf:ORGANIZATIONID>
                        <mf:DESCRIPTION>{descricao}</mf:DESCRIPTION>
                    </mf:WORKORDERID>

                    <mf:STATUS entity="User">
                        <mf:STATUSCODE>R</mf:STATUSCODE>
                        <mf:DESCRIPTION>Ready</mf:DESCRIPTION>
                    </mf:STATUS>

                    <mf:EQUIPMENTID>
                        <mf:EQUIPMENTCODE>AR-001</mf:EQUIPMENTCODE>
                        <mf:ORGANIZATIONID entity="Organization">
                            <mf:ORGANIZATIONCODE>*</mf:ORGANIZATIONCODE>
                        </mf:ORGANIZATIONID>
                    </mf:EQUIPMENTID>

                    <mf:DEPARTMENTID>
                        <mf:DEPARTMENTCODE>*</mf:DEPARTMENTCODE>
                        <mf:ORGANIZATIONID entity="Group">
                            <mf:ORGANIZATIONCODE>{cfg['org']}</mf:ORGANIZATIONCODE>
                        </mf:ORGANIZATIONID>
                    </mf:DEPARTMENTID>

                    <mf:TYPE entity="User">
                        <mf:TYPECODE>BRKD</mf:TYPECODE>
                        <mf:DESCRIPTION>Tipo de OS Calibração</mf:DESCRIPTION>
                    </mf:TYPE>

                    <mf:FIXED></mf:FIXED>
                </wo:WorkOrder>
            </mp:MP0023_AddWorkOrder_001>
        </soapenv:Body>
    </soapenv:Envelope>"""

    headers = {
        "Content-Type": "text/xml;charset=UTF-8",
        "Accept": "text/xml",
        "SOAPAction": ""
    }

    try:
        response = requests.post(
            url_soap,
            data=envelope.encode("utf-8"),
            headers=headers,
            timeout=30,
            verify=False
        )

        print(f"📬 Status HTTP: {response.status_code}")
        print("🧾 Resposta SOAP (parcial):")
        print(response.text[:800])
        print("-" * 80)

        # Verifica sucesso com base no texto de retorno
        if "Ordem de serviço" in response.text or "<returnCode>0</returnCode>" in response.text:
            print("✅ OS criada com sucesso!")
            return True
        else:
            print("⚠️ Falha ao criar OS — verifique o retorno acima.")
            return False

    except Exception as e:
        print(f"🚨 Erro na integração SOAP: {e}")
        return False
