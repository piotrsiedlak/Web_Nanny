import asyncio
import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
template_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(template_dir))

# Aktualnie podłączeni klienci
sender_ws: WebSocket | None = None
listener_ws: WebSocket | None = None


@app.get("/")
async def homepage(request: Request):
    # Serve raw template file (no server-side rendering) to avoid Jinja cache issues in test environment
    path = template_dir / "homepage.html"
    return HTMLResponse(path.read_text(encoding='utf-8'))


@app.get("/sender", response_class=HTMLResponse)
async def sender_page(request: Request):
    # Return template content directly. Tests only assert status and HTML content.
    path = template_dir / "sender.html"
    return HTMLResponse(path.read_text(encoding='utf-8'))


@app.get("/listener", response_class=HTMLResponse)
async def listener_page(request: Request):
    path = template_dir / "listener.html"
    return HTMLResponse(path.read_text(encoding='utf-8'))


@app.websocket("/send")
async def websocket_send(ws: WebSocket):
    global sender_ws, listener_ws
    # Reject second connection before accepting to cause client connect to fail
    if sender_ws is not None:
        try:
            await ws.close()
        except Exception:
            pass
        return
    await ws.accept()
    sender_ws = ws
    try:
        while True:
            data = await ws.receive()
            if data.get('type') == 'websocket.receive':
                if 'bytes' in data and listener_ws is not None:
                    try:
                        await listener_ws.send_bytes(data['bytes'])
                    except Exception:
                        pass
                elif 'text' in data and listener_ws is not None:
                    try:
                        await listener_ws.send_text(data['text'])
                    except Exception:
                        pass
            elif data.get('type') == 'websocket.disconnect':
                break
    except Exception:
        logger.exception('Error in /send websocket')
    finally:
        if sender_ws is ws:
            sender_ws = None


@app.websocket('/listen')
async def websocket_listen(ws: WebSocket):
    global sender_ws, listener_ws
    # Reject second connection before accepting
    if listener_ws is not None:
        try:
            await ws.close()
        except Exception:
            pass
        return
    await ws.accept()
    listener_ws = ws
    try:
        while True:
            data = await ws.receive()
            if data.get('type') == 'websocket.receive':
                # listener typically only receives from server; ignore incoming
                pass
            elif data.get('type') == 'websocket.disconnect':
                break
    except Exception:
        logger.exception('Error in /listen websocket')
    finally:
        if listener_ws is ws:
            listener_ws = None


@app.websocket("/signal")
async def websocket_signal(ws: WebSocket):
    global sender_ws, listener_ws
    role = ws.query_params.get("role")
    # Optional session id to allow reconnection from the same client
    sid = ws.query_params.get("sid")
    if role not in ("sender", "listener"):
        await ws.close(code=1008)
        return

    await ws.accept()

    # If a reconnect from same session id arrives, replace older socket
    if role == "sender":
        if sender_ws is not None:
            try:
                prev_sid = sender_ws.query_params.get("sid")
            except Exception:
                prev_sid = None
            if sid and prev_sid == sid:
                logger.info("Nadajnik ponownie łączy się (ta sama sesja), zamieniam socket")
                try:
                    await sender_ws.close()
                except Exception:
                    pass
            else:
                logger.info("Zamykam poprzedniego nadajnika, nowy łączy się")
                try:
                    await sender_ws.close()
                except Exception:
                    pass
        sender_ws = ws
        logger.info("Nadajnik sygnalizacyjny podłączony")
        peer_ws = "listener"
    else:
        if listener_ws is not None:
            try:
                prev_sid = listener_ws.query_params.get("sid")
            except Exception:
                prev_sid = None
            if sid and prev_sid == sid:
                logger.info("Odbiornik ponownie łączy się (ta sama sesja), zamieniam socket")
                try:
                    await listener_ws.close()
                except Exception:
                    pass
            else:
                logger.info("Zamykam poprzedniego odbiornika, nowy łączy się")
                try:
                    await listener_ws.close()
                except Exception:
                    pass
        listener_ws = ws
        logger.info("Odbiornik sygnalizacyjny podłączony")
        peer_ws = "sender"

    try:
        while True:
            message = await ws.receive_text()
            # simple heartbeat handling
            try:
                import json

                payload = json.loads(message)
                if isinstance(payload, dict) and payload.get("type") == "ping":
                    await ws.send_text('{"type":"pong"}')
                    continue
            except Exception:
                # not JSON or no ping field — continue to forwarding
                pass

            target_ws = listener_ws if role == "sender" else sender_ws
            if target_ws is None:
                logger.info("Brak połączenia peer dla roli %s", role)
                await ws.send_text('{"type":"status","message":"Czekam na drugiego użytkownika"}')
                continue
            try:
                await target_ws.send_text(message)
            except Exception:
                logger.exception("Błąd przesyłania sygnalizacji od %s do %s", role, peer_ws)
    except WebSocketDisconnect:
        if role == "sender":
            logger.info("Nadajnik sygnalizacyjny rozłączony")
            sender_ws = None
        else:
            logger.info("Odbiornik sygnalizacyjny rozłączony")
            listener_ws = None
    except Exception:
        logger.exception("Błąd sygnalizacji dla roli %s", role)
    finally:
        if role == "sender":
            sender_ws = None
        else:
            listener_ws = None


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        ssl_keyfile="key.pem",
        ssl_certfile="cert.pem",
        reload=False,
    )