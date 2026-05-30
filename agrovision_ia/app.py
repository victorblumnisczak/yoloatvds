import json
import os
import threading
from typing import Literal

import cv2
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from services.logging_config import setup_logging, get_logger
from services.schemas import ChatRequest
from services.event_repository import init_db, list_events
from services.config import (
    AGENT_EVENT_LIMIT, SCRAPING_ENABLED, SCRAPING_MIN_INTERVAL, SCRAPING_CACHE_DB
)
from services.video_monitor import VideoMonitor
from services.chat_session_service import ChatSessionService
from services.scraping.cache import ScrapingCache
from services.scraping.rate_limiter import RateLimiter
from services.scraping.scraping_service import ScrapingService
from services.scraping.weather import WeatherSource
from services.scraping.market import MarketSource
from services.scraping.news import NewsSource
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

_scraping_cache = ScrapingCache(SCRAPING_CACHE_DB)
_rate_limiter = RateLimiter(SCRAPING_MIN_INTERVAL)
_weather_source = WeatherSource(
    active_camera_provider=lambda: monitor.status().get("source")
)
_market_source = MarketSource()
_news_source = NewsSource()
scraping_service = ScrapingService(
    sources=[_weather_source, _market_source, _news_source],
    cache=_scraping_cache,
    rate_limiter=_rate_limiter,
)


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
@app.on_event("startup")
def startup():
    init_db()
    monitor.start()
    log.info("Warmup do Ollama disparado em background.")
    threading.Thread(target=ollama_client.warmup, daemon=True).start()
    if SCRAPING_ENABLED:
        threading.Thread(
            target=scraping_service.background_refresh_loop,
            kwargs={"interval_seconds": 60},
            daemon=True,
        ).start()
        log.info("ScrapingService inicializado.")
    else:
        log.info("Scraping desabilitado por configuração (.env).")


# ---------------------------------------------------------------------------
# Rotas principais
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


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
    external = scraping_service.get_full_context() if SCRAPING_ENABLED else None
    return agent.get_status(external)


@app.get("/ollama/status")
def ollama_status():
    return ollama_client.is_alive()


@app.get("/scraping/status")
def scraping_status():
    if not SCRAPING_ENABLED:
        return {"enabled": False, "sources": [], "cache": {"total": 0, "by_source": {}}}
    return scraping_service.status()


@app.post("/scraping/refresh")
def scraping_refresh(source: Literal["weather", "market", "news"]):
    if not SCRAPING_ENABLED:
        return JSONResponse(status_code=503, content={"error": "scraping desabilitado"})
    result = scraping_service.get(source, force=True)
    if not result:
        return JSONResponse(status_code=503, content={"error": "falha ao refrescar"})
    return result.payload


@app.get("/scraping/news")
def scraping_news():
    if not SCRAPING_ENABLED:
        return JSONResponse(status_code=503, content={"error": "scraping desabilitado"})
    result = scraping_service.get("news")
    if not result:
        return JSONResponse(status_code=503, content={"error": "indisponível"})
    return result.payload


@app.get("/scraping/market")
def scraping_market():
    if not SCRAPING_ENABLED:
        return JSONResponse(status_code=503, content={"error": "scraping desabilitado"})
    result = scraping_service.get("market")
    if not result:
        return JSONResponse(status_code=503, content={"error": "indisponível"})
    return result.payload


@app.get("/scraping/weather")
def scraping_weather():
    if not SCRAPING_ENABLED:
        return JSONResponse(status_code=503, content={"error": "scraping desabilitado"})
    result = scraping_service.get("weather")
    if not result:
        return JSONResponse(status_code=503, content={"error": "indisponível"})
    return result.payload


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
        external = scraping_service.get_full_context() if SCRAPING_ENABLED else None
        answer = agent.ask(body.message, history, events, external)
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
            external = scraping_service.get_full_context() if SCRAPING_ENABLED else None
            for chunk in agent.ask_stream(body.message, history, events, external):
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
