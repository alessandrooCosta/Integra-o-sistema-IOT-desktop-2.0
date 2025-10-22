from __future__ import annotations
import json, os, re, time
from dataclasses import dataclass
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import requests

# =============================================================
# ⚙️ Configurações
# =============================================================
SESSION_TTL_SECONDS = 15 * 60  # 15 minutos

# =============================================================
# 📦 Estrutura de configuração
# =============================================================
@dataclass
class EAMConfig:
    server: str
    tenant: str
    org: str
    user: str
    password: str
    proxy_url: str | None = None  # Exemplo: "http://localhost:8000/eamproxy"

# =============================================================
# 🔧 Funções auxiliares
# =============================================================
def _normalize_base(server: str) -> str:
    s = (server or "").strip().rstrip("/")
    if not s.startswith("http://") and not s.startswith("https://"):
        s = "https://" + s
    return s

def _ews_url(server: str) -> str:
    return f"{_normalize_base(server)}/axis/services/EWSConnector"

def _sessions_dir() -> str:
    d = os.path.join(os.path.dirname(__file__), "sessions")
    os.makedirs(d, exist_ok=True)
    return os.path.abspath(d)

def _session_path(cfg: EAMConfig) -> str:
    host = urlparse(_normalize_base(cfg.server)).hostname or "unknown"
    key = f"{host}_{cfg.tenant}_{cfg.user}_{cfg.org}".replace("/", "_")
    return os.path.join(_sessions_dir(), f"{key}.json")

def _extract_faultstring(xml_text: str) -> str | None:
    try:
        root = ET.fromstring(xml_text)
        ns = {"s": "http://schemas.xmlsoap.org/soap/envelope/"}
        fault = root.find(".//s:Fault", ns)
        if fault is None:
            m = re.search(r"<faultstring>(.*?)</faultstring>", xml_text, re.S | re.I)
            return m.group(1).strip() if m else None
        fs = fault.find("faultstring")
        return (fs.text or "").strip() if fs is not None else None
    except Exception:
        return None

def _extract_session_id(xml_text: str) -> str | None:
    try:
        root = ET.fromstring(xml_text)
        ns = {"m": "http://schemas.datastream.net/MP_functions"}
        sid = root.find(".//m:Session/m:sessionId", ns)
        if sid is not None and sid.text:
            return sid.text.strip()
    except Exception:
        pass
    m = re.search(r"<sessionId>([^<]+)</sessionId>", xml_text, re.I)
    return m.group(1).strip() if m else None

def _save_session(cfg: EAMConfig, session_id: str) -> dict:
    now = int(time.time())
    data = {
        "server": _normalize_base(cfg.server),
        "tenant": cfg.tenant,
        "org": cfg.org,
        "user": cfg.user,
        "session_id": session_id,
        "created_at": now,
        "expires_at": now + SESSION_TTL_SECONDS,
    }
    with open(_session_path(cfg), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data

def _load_session(cfg: EAMConfig) -> dict | None:
    p = _session_path(cfg)
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        if (data.get("server") == _normalize_base(cfg.server)
                and data.get("tenant") == cfg.tenant
                and data.get("org") == cfg.org
                and data.get("user") == cfg.user):
            return data
        return None
    except Exception:
        return None

# =============================================================
# 🧩 Login via MP0302_GetAssetEquipment_001
# =============================================================
def _login_envelope(cfg: EAMConfig) -> str:
    # Login via MP0302_GetAssetEquipment_001 compatível com EAM Cloud
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope
    xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:mp="http://schemas.datastream.net/MP_functions/MP0302_001"
    xmlns:wsse="http://schemas.xmlsoap.org/ws/2002/04/secext"
    xmlns:mf="http://schemas.datastream.net/MP_fields">
  <soapenv:Header>
    <wsse:Security>
      <wsse:UsernameToken>
        <wsse:Username>{cfg.user}</wsse:Username>
        <wsse:Password>{cfg.password}</wsse:Password>
      </wsse:UsernameToken>
    </wsse:Security>
    <Tenant xmlns="http://schemas.datastream.net/headers">{cfg.tenant}</Tenant>
    <Organization xmlns="http://schemas.datastream.net/headers">{cfg.org}</Organization>
  </soapenv:Header>
  <soapenv:Body>
    <mp:MP0302_GetAssetEquipment_001 verb="Get" noun="AssetEquipment" version="001" callname="GetAssetEquipment">
      <mf:ASSETID>
        <mf:EQUIPMENTCODE>AA-001</mf:EQUIPMENTCODE>
        <mf:ORGANIZATIONID entity="Organization">
          <mf:ORGANIZATIONCODE>{cfg.org}</mf:ORGANIZATIONCODE>
        </mf:ORGANIZATIONID>
      </mf:ASSETID>
    </mp:MP0302_GetAssetEquipment_001>
  </soapenv:Body>
</soapenv:Envelope>""".strip()

# =============================================================
# 🌐 Comunicação SOAP
# =============================================================
def _http_headers_for() -> dict:
    return {"Content-Type": "text/xml;charset=UTF-8", "SOAPAction": ""}

def _post_soap(cfg: EAMConfig, xml: str) -> requests.Response:
    url = cfg.proxy_url.strip() if cfg.proxy_url else _ews_url(cfg.server)
    headers = _http_headers_for()
    print(f"🔗 POST {url}")
    print(f"Headers: {headers}")
    print("--- XML ENVIADO ---")
    print(xml)
    print("-----------------")
    resp = requests.post(url, data=xml.encode("utf-8"), headers=headers, timeout=60)
    return resp

# =============================================================
# 🔐 Sessão e autenticação
# =============================================================
def login_eam(cfg: EAMConfig) -> str:
    env = _login_envelope(cfg)
    resp = _post_soap(cfg, env)

    print(f"📬 Status {resp.status_code}")
    print("--- RESPOSTA ---")
    print(resp.text[:1000])
    print("-----------------")

    if resp.status_code != 200:
        fs = _extract_faultstring(resp.text) or resp.text[:300]
        raise RuntimeError(f"HTTP {resp.status_code} ao autenticar. Detalhe: {fs}")

    sid = _extract_session_id(resp.text)
    if not sid:
        fs = _extract_faultstring(resp.text) or resp.text[:500]
        raise RuntimeError(f"Falha ao obter sessionId. Detalhe: {fs}")

    _save_session(cfg, sid)
    return sid

def get_valid_session(cfg: EAMConfig) -> str:
    cached = _load_session(cfg)
    now = int(time.time())
    if cached and cached.get("session_id") and cached.get("expires_at", 0) > now:
        return cached["session_id"]
    return login_eam(cfg)

# =============================================================
# 📨 Envio de SOAP com sessão ativa
# =============================================================
def envelope_with_session(cfg: EAMConfig, session_id: str, body_xml: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
  <soapenv:Header>
    <dstm:Session xmlns:dstm="http://schemas.datastream.net/MP_functions">
      <sessionId>{session_id}</sessionId>
    </dstm:Session>
    <Tenant xmlns="http://schemas.datastream.net/headers">{cfg.tenant}</Tenant>
    <Organization xmlns="http://schemas.datastream.net/headers">{cfg.org}</Organization>
  </soapenv:Header>
  <soapenv:Body>
    {body_xml}
  </soapenv:Body>
</soapenv:Envelope>""".strip()

def send_soap_with_session(cfg: EAMConfig, body_xml: str, soap_action: str | None = "") -> requests.Response:
    def _do(session_id: str) -> requests.Response:
        env = envelope_with_session(cfg, session_id, body_xml)
        url = cfg.proxy_url.strip() if cfg.proxy_url else _ews_url(cfg.server)
        headers = _http_headers_for()
        if soap_action:
            headers["SOAPAction"] = soap_action
        return requests.post(url, data=env.encode("utf-8"), headers=headers, timeout=60)

    sid = get_valid_session(cfg)
    r = _do(sid)

    if any(err in r.text for err in (
            "Invalid session", "Session Not Found", "No security handler", "Your session has expired"
    )):
        sid = login_eam(cfg)
        r = _do(sid)

    return r
