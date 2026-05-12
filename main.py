import asyncio
import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.requests import Request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
template_dir = Path(__file__).parent / "templates"

# Aktualnie podłączeni klienci
sender_ws: WebSocket | None = None
listener_ws: WebSocket | None = None


@app.get("/sender", response_class=HTMLResponse)
async def sender_page(request: Request):
    return (template_dir / "sender.html").read_text(encoding='utf-8', errors='replace')


@app.get("/listener", response_class=HTMLResponse)
async def listener_page(request: Request):
    return (template_dir / "listener.html").read_text(encoding='utf-8', errors='replace')


@app.websocket("/signal")
async def websocket_signal(ws: WebSocket):
    global sender_ws, listener_ws
    role = ws.query_params.get("role")
    if role not in ("sender", "listener"):
        await ws.close(code=1008)
        return

    await ws.accept()

    if role == "sender":
        if sender_ws is not None:
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
        port=2137,
        ssl_keyfile="key.pem",
        ssl_certfile="cert.pem",
        reload=False,
    )