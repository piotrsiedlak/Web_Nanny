import asyncio
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
from uuid import uuid4

import uvicorn
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
template_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(template_dir))

AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() == "true"
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")
TLS_ENABLED = os.getenv("TLS_ENABLED", "true").lower() == "true"
TLS_CERTFILE = os.getenv("TLS_CERTFILE", "cert.pem")
TLS_KEYFILE = os.getenv("TLS_KEYFILE", "key.pem")
PORT = int(os.getenv("PORT", "8001"))
RECONNECT_GRACE_SECONDS = int(os.getenv("RECONNECT_GRACE_SECONDS", "30"))
CLEANUP_INTERVAL_SECONDS = int(os.getenv("CLEANUP_INTERVAL_SECONDS", "60"))
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"

@dataclass
class SessionInfo:
    sid: str
    role: str
    ws: Optional[WebSocket]
    created_at: float
    last_activity: float

    def refresh(self) -> None:
        self.last_activity = time.time()

    def is_expired(self) -> bool:
        return time.time() - self.last_activity > RECONNECT_GRACE_SECONDS

sessions: Dict[str, SessionInfo] = {}

sender_ws: Optional[WebSocket] = None
listener_ws: Optional[WebSocket] = None
app_start_time = time.time()

# Rate limiting: track connection attempts by IP
connection_attempts: Dict[str, list] = {}
MAX_CONNECTIONS_PER_IP = 10
RATE_LIMIT_WINDOW = 60  # seconds


def get_client_ip(request_headers: dict) -> str:
    """Extract client IP from headers (supports X-Forwarded-For for proxies)."""
    if "x-forwarded-for" in request_headers:
        return request_headers["x-forwarded-for"].split(",")[0].strip()
    return request_headers.get("client-host", "unknown")


def check_rate_limit(client_ip: str) -> bool:
    """Check if client has exceeded connection rate limit."""
    # Skip rate limiting when disabled or for unknown/local test clients
    if not RATE_LIMIT_ENABLED:
        return True
    if not client_ip or client_ip == "unknown" or client_ip.startswith("127.") or client_ip == "::1":
        return True
    now = time.time()
    if client_ip not in connection_attempts:
        connection_attempts[client_ip] = []
    
    # Remove old attempts outside the window
    connection_attempts[client_ip] = [
        t for t in connection_attempts[client_ip] 
        if now - t < RATE_LIMIT_WINDOW
    ]
    
    # Check if limit exceeded
    if len(connection_attempts[client_ip]) >= MAX_CONNECTIONS_PER_IP:
        return False
    
    # Record this attempt
    connection_attempts[client_ip].append(now)
    return True


def validate_startup_config() -> None:
    """Validate configuration on startup."""
    if AUTH_ENABLED and not AUTH_TOKEN:
        logger.warning("AUTH_ENABLED is true but AUTH_TOKEN is empty or not set")
    
    if TLS_ENABLED:
        ensure_tls_certificates()
        cert_path = Path(TLS_CERTFILE)
        key_path = Path(TLS_KEYFILE)
        if not cert_path.exists():
            raise FileNotFoundError(f"TLS certificate not found: {TLS_CERTFILE}")
        if not key_path.exists():
            raise FileNotFoundError(f"TLS key not found: {TLS_KEYFILE}")
        logger.info("TLS certificates validated successfully")
    else:
        logger.warning("TLS_ENABLED is false - running without HTTPS/WSS")


def generate_self_signed_cert(key_path: Path, cert_path: Path) -> None:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "PL"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Warsaw"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Warsaw"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "WebNanny"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=365))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
        .sign(key, hashes.SHA256())
    )

    key_path.parent.mkdir(parents=True, exist_ok=True)
    cert_path.parent.mkdir(parents=True, exist_ok=True)

    with key_path.open("wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    with cert_path.open("wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))


def ensure_tls_certificates() -> None:
    if not TLS_ENABLED:
        return

    key_path = Path(TLS_KEYFILE)
    cert_path = Path(TLS_CERTFILE)

    if key_path.exists() and cert_path.exists():
        return

    logger.warning("TLS certificate or key not found, generating self-signed certificates")
    generate_self_signed_cert(key_path, cert_path)
    logger.info("Generated self-signed TLS certificate at %s and key at %s", cert_path, key_path)


def check_auth(token: Optional[str], auth_header: Optional[str] = None) -> bool:
    if not AUTH_ENABLED:
        return True
    candidate = token
    if not candidate and auth_header:
        if auth_header.startswith("Bearer "):
            candidate = auth_header[7:]
    return bool(candidate and secrets.compare_digest(candidate, AUTH_TOKEN))


def create_or_refresh_session(role: str, sid: Optional[str]) -> SessionInfo:
    if sid and sid in sessions and sessions[sid].role == role:
        session = sessions[sid]
        session.refresh()
        return session

    sid = sid or uuid4().hex
    session = SessionInfo(sid=sid, role=role, ws=None, created_at=time.time(), last_activity=time.time())
    sessions[sid] = session
    return session


async def cleanup_sessions() -> None:
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
        expired_keys = [sid for sid, session in sessions.items() if session.is_expired()]
        for sid in expired_keys:
            session = sessions.pop(sid, None)
            if session and session.ws is not None:
                try:
                    await session.ws.close(code=status.WS_1000_NORMAL_CLOSURE)
                except Exception:
                    pass
            logger.info("Usuwanie wygasłej sesji %s", sid)


@app.on_event("startup")
async def startup_event() -> None:
    validate_startup_config()
    asyncio.create_task(cleanup_sessions())


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    return {
        "status": "ok",
        "uptime_seconds": time.time() - app_start_time,
        "active_sessions": len(sessions),
        "sender_connected": sender_ws is not None,
        "listener_connected": listener_ws is not None,
    }


@app.get("/metrics")
async def metrics():
    """Metrics endpoint for monitoring active sessions and connections."""
    active_sessions = {
        sid: {
            "role": session.role,
            "connected": session.ws is not None,
            "age_seconds": time.time() - session.created_at,
            "idle_seconds": time.time() - session.last_activity,
        }
        for sid, session in sessions.items()
    }
    return {
        "total_sessions": len(sessions),
        "active_sessions": active_sessions,
        "sender_ws_active": sender_ws is not None,
        "listener_ws_active": listener_ws is not None,
        "uptime_seconds": time.time() - app_start_time,
    }


@app.get("/")
async def homepage(request: Request):
    path = template_dir / "homepage.html"
    return HTMLResponse(path.read_text(encoding='utf-8'))


@app.get("/sender", response_class=HTMLResponse)
async def sender_page(request: Request, token: Optional[str] = Query(None), lang: Optional[str] = Query("en")):
    if AUTH_ENABLED and not check_auth(token, request.headers.get("authorization")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return templates.TemplateResponse("sender.html", {"request": request, "lang": lang})


@app.get("/listener", response_class=HTMLResponse)
async def listener_page(request: Request, token: Optional[str] = Query(None), lang: Optional[str] = Query("en")):
    if AUTH_ENABLED and not check_auth(token, request.headers.get("authorization")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return templates.TemplateResponse("listener.html", {"request": request, "lang": lang})


@app.websocket("/send")
async def websocket_send(ws: WebSocket):
    global sender_ws, listener_ws
    
    # Rate limiting check
    client_ip = get_client_ip(dict(ws.headers))
    if not check_rate_limit(client_ip):
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Rate limit exceeded")
        logger.warning("Rate limit exceeded for client %s on /send", client_ip)
        return
    
    if AUTH_ENABLED and not check_auth(ws.query_params.get("token"), ws.headers.get("authorization")):
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if sender_ws is not None:
        try:
            await ws.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass
        return

    await ws.accept()
    sender_ws = ws
    try:
        while True:
            data = await ws.receive()
            if data.get("type") == "websocket.receive":
                if "bytes" in data and listener_ws is not None:
                    try:
                        await listener_ws.send_bytes(data["bytes"])
                    except Exception:
                        pass
                elif "text" in data and listener_ws is not None:
                    try:
                        await listener_ws.send_text(data["text"])
                    except Exception:
                        pass
            elif data.get("type") == "websocket.disconnect":
                break
    except Exception:
        logger.exception("Error in /send websocket")
    finally:
        if sender_ws is ws:
            sender_ws = None


@app.websocket('/listen')
async def websocket_listen(ws: WebSocket):
    global sender_ws, listener_ws
    
    # Rate limiting check
    client_ip = get_client_ip(dict(ws.headers))
    if not check_rate_limit(client_ip):
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Rate limit exceeded")
        logger.warning("Rate limit exceeded for client %s on /listen", client_ip)
        return
    
    if AUTH_ENABLED and not check_auth(ws.query_params.get("token"), ws.headers.get("authorization")):
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if listener_ws is not None:
        try:
            await ws.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass
        return

    await ws.accept()
    listener_ws = ws
    try:
        while True:
            data = await ws.receive()
            if data.get("type") == "websocket.receive":
                pass
            elif data.get("type") == "websocket.disconnect":
                break
    except Exception:
        logger.exception("Error in /listen websocket")
    finally:
        if listener_ws is ws:
            listener_ws = None


@app.websocket("/signal")
async def websocket_signal(ws: WebSocket):
    global sender_ws, listener_ws
    role = ws.query_params.get("role")
    sid = ws.query_params.get("sid")
    token = ws.query_params.get("token")
    
    # Rate limiting check
    client_ip = get_client_ip(dict(ws.headers))
    if not check_rate_limit(client_ip):
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Rate limit exceeded")
        logger.warning("Rate limit exceeded for client %s", client_ip)
        return

    if AUTH_ENABLED and not check_auth(token, ws.headers.get("authorization")):
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if role not in ("sender", "listener"):
        await ws.close(code=1008)
        return

    session = create_or_refresh_session(role, sid)
    if session.ws is not None and session.ws is not ws:
        try:
            await session.ws.close(code=status.WS_1000_NORMAL_CLOSURE)
        except Exception:
            pass

    await ws.accept()
    session.ws = ws

    if role == "sender":
        sender_ws = ws
        logger.info("Sender signal socket connected, session=%s", session.sid)
        peer_ws = "listener"
    else:
        listener_ws = ws
        logger.info("Listener signal socket connected, session=%s", session.sid)
        peer_ws = "sender"

    try:
        while True:
            message = await ws.receive_text()
            try:
                payload = json.loads(message)
                if isinstance(payload, dict) and payload.get("type") == "ping":
                    session.refresh()
                    await ws.send_text(json.dumps({"type": "pong"}))
                    continue
            except Exception:
                pass

            session.refresh()
            target_ws = listener_ws if role == "sender" else sender_ws
            if target_ws is None:
                logger.info("Waiting for peer connection for role %s", role)
                await ws.send_text(json.dumps({"type": "status", "message": "Waiting for peer"}))
                continue

            try:
                await target_ws.send_text(message)
            except Exception:
                logger.exception("Error forwarding signaling from %s to %s", role, peer_ws)
    except WebSocketDisconnect:
        logger.info("Signal socket disconnected for role %s, session=%s", role, session.sid)
    except Exception:
        logger.exception("Unexpected signaling error for role %s", role)
    finally:
        if session.ws is ws:
            session.ws = None
        if role == "sender" and sender_ws is ws:
            sender_ws = None
        if role == "listener" and listener_ws is ws:
            listener_ws = None
        session.last_activity = time.time()


if __name__ == "__main__":
    server_options = {"host": "0.0.0.0", "port": PORT, "reload": False}
    if TLS_ENABLED:
        server_options["ssl_certfile"] = TLS_CERTFILE
        server_options["ssl_keyfile"] = TLS_KEYFILE

    uvicorn.run("main:app", **server_options)
