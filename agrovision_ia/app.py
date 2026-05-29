import json
import os
import threading

import cv2
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from services.logging_config import setup_logging, get_logger
from services.schemas import ChatRequest
from services.event_repository import init_db, list_events
from services.config import AGENT_EVENT_LIMIT
from services.video_monitor import VideoMonitor
from services.chat_session_service import ChatSessionService
import services.monitoring_agent as agent
import services.ollama_client as ollama_client
import services.camera_pool as camera_pool

setup_logging()
log = get_logger("agrovision.app")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="AgroVision AI")

os.makedirs("static", exist_ok=True)
os.makedirs("static/captures", exist_ok=True)
os.makedirs("templates", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

monitor = VideoMonitor()
chat_sessions = ChatSessionService()
SESSION_ID = "default"  # single-user por enquanto


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
@app.on_event("startup")
def startup():
    init_db()
    monitor.start()
    log.info("Warmup do Ollama disparado em background.")
    threading.Thread(target=ollama_client.warmup, daemon=True).start()


# ---------------------------------------------------------------------------
# Rotas principais
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    events = list_events(20)
    return templates.TemplateResponse(
        "index.html", {"request": request, "events": events}
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": "AgroVision AI"}


@app.get("/events")
def get_events():
    return JSONResponse(content=list_events(50))


@app.get("/camera/status")
def camera_status():
    return monitor.status()


@app.get("/cameras")
def cameras():
    status = monitor.status()
    return {"active": status["source"], "pool": camera_pool.list_all()}


@app.get("/agent/status")
def agent_status():
    return agent.get_status()


@app.get("/ollama/status")
def ollama_status():
    return ollama_client.is_alive()


# ---------------------------------------------------------------------------
# Rotas de vídeo
# ---------------------------------------------------------------------------
@app.get("/frame")
def get_frame():
    frame = monitor.get_last_frame()
    if frame is None:
        return JSONResponse(
            status_code=503, content={"error": "Nenhum frame disponível ainda"}
        )
    success, buffer = cv2.imencode(".jpg", frame)
    if not success:
        return JSONResponse(
            status_code=500, content={"error": "Falha na codificação do frame"}
        )
    return Response(content=buffer.tobytes(), media_type="image/jpeg")


@app.get("/video_feed")
def video_feed():
    return StreamingResponse(
        monitor.iter_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/stream")
def stream():
    """Alias para /video_feed — mantém compatibilidade com versões anteriores."""
    return video_feed()


# ---------------------------------------------------------------------------
# Chat — Agente AgroVision via Ollama
# ---------------------------------------------------------------------------
@app.post("/chat")
def chat(body: ChatRequest):
    try:
        events = list_events(AGENT_EVENT_LIMIT)
        history = chat_sessions.get(SESSION_ID)
        answer = agent.ask(body.message, history, events)
        chat_sessions.append(SESSION_ID, "user", body.message)
        chat_sessions.append(SESSION_ID, "assistant", answer)
        return {"answer": answer}
    except RuntimeError as exc:
        log.warning("Falha controlada no /chat: %s", exc)
        return {"answer": str(exc)}
    except Exception:
        log.exception("Erro inesperado no /chat")
        return {
            "answer": (
                "Não foi possível consultar o agente no momento. "
                "Verifique se o Ollama está ativo e tente novamente."
            )
        }


@app.post("/chat/stream")
def chat_stream(body: ChatRequest):
    def generate():
        accumulated: list[str] = []
        try:
            events = list_events(AGENT_EVENT_LIMIT)
            history = chat_sessions.get(SESSION_ID)
            for chunk in agent.ask_stream(body.message, history, events):
                accumulated.append(chunk)
                yield json.dumps({"chunk": chunk}, ensure_ascii=False) + "\n"
            full_response = "".join(accumulated)
            chat_sessions.append(SESSION_ID, "user", body.message)
            chat_sessions.append(SESSION_ID, "assistant", full_response)
            yield json.dumps({"done": True}) + "\n"
        except RuntimeError as exc:
            log.warning("Falha controlada no /chat/stream: %s", exc)
            yield json.dumps({"error": str(exc)}, ensure_ascii=False) + "\n"
        except Exception:
            log.exception("Erro inesperado no /chat/stream")
            yield json.dumps(
                {"error": "Não foi possível consultar o agente no momento."},
                ensure_ascii=False,
            ) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")
