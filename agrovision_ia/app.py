import json
import os
import threading
import time

import cv2
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from services.schemas import ChatRequest
from services.event_repository import init_db, list_events
from services.video_monitor import VideoMonitor
import services.monitoring_agent as agent
import services.ollama_client as ollama_client
import services.camera_pool as camera_pool

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

# Histórico em memória (sessão única — demo de sala de aula)
_chat_history: list = []


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
@app.on_event("startup")
def startup():
    init_db()
    monitor.start()
    print("[startup] Warmup do Ollama disparado em background.")
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


def _mjpeg_generator():
    while True:
        frame = monitor.get_last_frame()
        if frame is None:
            time.sleep(0.1)
            continue
        success, buffer = cv2.imencode(".jpg", frame)
        if not success:
            continue
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
        )
        time.sleep(0.05)


@app.get("/video_feed")
def video_feed():
    return StreamingResponse(
        _mjpeg_generator(),
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
    global _chat_history
    try:
        answer = agent.ask(body.message, _chat_history)
        _chat_history.append({"role": "user", "content": body.message})
        _chat_history.append({"role": "assistant", "content": answer})
        if len(_chat_history) > 16:
            _chat_history = _chat_history[-16:]
        return {"answer": answer}
    except RuntimeError as exc:
        return {"answer": str(exc)}
    except Exception:
        return {
            "answer": (
                "Não foi possível consultar o agente no momento. "
                "Verifique se o Ollama está ativo e tente novamente."
            )
        }


@app.post("/chat/stream")
def chat_stream(body: ChatRequest):
    global _chat_history

    def generate():
        accumulated: list[str] = []
        try:
            for chunk in agent.ask_stream(body.message, _chat_history):
                accumulated.append(chunk)
                yield json.dumps({"chunk": chunk}, ensure_ascii=False) + "\n"
            full_response = "".join(accumulated)
            _chat_history.append({"role": "user", "content": body.message})
            _chat_history.append({"role": "assistant", "content": full_response})
            if len(_chat_history) > 16:
                del _chat_history[:-16]
            yield json.dumps({"done": True}) + "\n"
        except RuntimeError as exc:
            yield json.dumps({"error": str(exc)}, ensure_ascii=False) + "\n"
        except Exception as e:
            import traceback
            print(f"[chat/stream] ERRO: {type(e).__name__}: {e}")
            traceback.print_exc()
            yield json.dumps(
                {"error": "Não foi possível consultar o agente no momento."},
                ensure_ascii=False,
            ) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")
