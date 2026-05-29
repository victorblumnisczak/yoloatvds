import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
AGENT_EVENT_LIMIT = int(os.getenv("AGENT_EVENT_LIMIT", "12"))

_cam_src = os.getenv("CAMERA_SOURCE", "0")
# Vazio ou ausente → None (usa pool aleatório); número → int (webcam); string → URL explícita
if not _cam_src:
    CAMERA_SOURCE: int | str | None = None
elif _cam_src.isdigit():
    CAMERA_SOURCE = int(_cam_src)
else:
    CAMERA_SOURCE = _cam_src
CAMERA_RECONNECT_SECONDS = int(os.getenv("CAMERA_RECONNECT_SECONDS", "5"))

MODEL_PATH = "yolov8n.pt"
CONFIDENCE_THRESHOLD = 0.45
SAVE_DIR = "static/captures"
DB_PATH = "detections.db"

TARGET_CLASSES = {"person", "car", "motorcycle", "truck", "bus"}
MIN_CONSECUTIVE_FRAMES = 3
ALERT_COOLDOWN_SECONDS = 20

# === Scraping ===
SCRAPING_ENABLED = os.getenv("SCRAPING_ENABLED", "true").lower() == "true"
SCRAPING_USER_AGENT = os.getenv("SCRAPING_USER_AGENT", "AgroVisionAI-Educational/1.0")
SCRAPING_TIMEOUT = int(os.getenv("SCRAPING_TIMEOUT", "10"))
SCRAPING_MIN_INTERVAL = int(os.getenv("SCRAPING_MIN_INTERVAL", "30"))
SCRAPING_WEATHER_TTL = int(os.getenv("SCRAPING_WEATHER_TTL", "600"))
SCRAPING_MARKET_TTL = int(os.getenv("SCRAPING_MARKET_TTL", "3600"))
SCRAPING_NEWS_TTL = int(os.getenv("SCRAPING_NEWS_TTL", "1800"))


def _parse_float(v: str | None) -> float | None:
    if not v:
        return None
    try:
        return float(v.replace(",", "."))
    except ValueError:
        return None


SCRAPING_LAT = _parse_float(os.getenv("SCRAPING_LAT"))
SCRAPING_LON = _parse_float(os.getenv("SCRAPING_LON"))
SCRAPING_PLACE_NAME = os.getenv("SCRAPING_PLACE_NAME") or None

SCRAPING_CACHE_DB = "scraping_cache.db"
