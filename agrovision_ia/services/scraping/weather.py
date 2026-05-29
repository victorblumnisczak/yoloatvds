from datetime import datetime
import httpx
from services.scraping.base import ScrapingSource, ScrapingResult, ScrapingError
from services.config import (
    SCRAPING_USER_AGENT, SCRAPING_TIMEOUT, SCRAPING_WEATHER_TTL,
    SCRAPING_LAT, SCRAPING_LON, SCRAPING_PLACE_NAME,
)
from services.logging_config import get_logger

log = get_logger("agrovision.scraping.weather")

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

# Mapeamento Caltrans → coordenadas (extraído da URL da câmera ativa)
DISTRICT_COORDS: dict[str, tuple[float, float, str]] = {
    "D11": (32.55, -117.05, "San Diego, CA"),
    "D4":  (37.78, -122.40, "San Francisco, CA"),
    "D3":  (38.58, -121.49, "Sacramento, CA"),
    "D12": (33.65, -117.84, "Orange County, CA"),
    "D7":  (34.05, -118.24, "Los Angeles, CA"),
}

# WMO Weather codes — descrição PT-BR
WMO_DESCRIPTIONS: dict[int, str] = {
    0: "céu limpo",
    1: "predominantemente limpo", 2: "parcialmente nublado", 3: "nublado",
    45: "neblina", 48: "neblina com geada",
    51: "garoa leve", 53: "garoa moderada", 55: "garoa intensa",
    61: "chuva leve", 63: "chuva moderada", 65: "chuva forte",
    71: "neve leve", 73: "neve moderada", 75: "neve forte",
    77: "grãos de neve",
    80: "pancadas leves", 81: "pancadas moderadas", 82: "pancadas violentas",
    85: "pancadas de neve leves", 86: "pancadas de neve fortes",
    95: "trovoada", 96: "trovoada com granizo leve", 99: "trovoada com granizo forte",
}


def _district_from_url(url: str) -> str | None:
    """Extrai 'D11' de uma URL Caltrans como '.../D11/C214_SB_5.../playlist.m3u8'."""
    if not url or not isinstance(url, str):
        return None
    parts = url.split("/")
    for p in parts:
        if p.startswith("D") and p[1:].isdigit():
            return p
    return None


def _geocode(place_name: str) -> tuple[float, float, str] | None:
    try:
        with httpx.Client(timeout=SCRAPING_TIMEOUT,
                          headers={"User-Agent": SCRAPING_USER_AGENT}) as client:
            r = client.get(GEOCODING_URL, params={"name": place_name, "count": 1, "language": "pt"})
            r.raise_for_status()
            data = r.json()
            results = data.get("results") or []
            if not results:
                return None
            first = results[0]
            name = first.get("name", place_name)
            admin = first.get("admin1", "")
            full = f"{name}, {admin}" if admin else name
            return float(first["latitude"]), float(first["longitude"]), full
    except Exception:
        log.exception("Falha no geocoding de %s", place_name)
        return None


class WeatherSource(ScrapingSource):
    name = "weather"
    ttl_seconds = SCRAPING_WEATHER_TTL

    def __init__(self, active_camera_provider=None):
        """
        active_camera_provider: callable que retorna a URL/fonte ativa
          da câmera (usado para inferir o distrito Caltrans). Pode ser None.
        """
        self._camera_provider = active_camera_provider

    def _resolve_location(self) -> tuple[float, float, str]:
        # 1) Coordenadas explícitas
        if SCRAPING_LAT is not None and SCRAPING_LON is not None:
            name = SCRAPING_PLACE_NAME or f"{SCRAPING_LAT:.2f},{SCRAPING_LON:.2f}"
            return SCRAPING_LAT, SCRAPING_LON, name
        # 2) Nome do lugar (geocoding)
        if SCRAPING_PLACE_NAME:
            g = _geocode(SCRAPING_PLACE_NAME)
            if g:
                return g
        # 3) Distrito Caltrans da câmera ativa
        if self._camera_provider:
            cam = self._camera_provider()
            district = _district_from_url(str(cam) if cam else "")
            if district and district in DISTRICT_COORDS:
                return DISTRICT_COORDS[district]
        # 4) Default — San Diego (D11)
        return DISTRICT_COORDS["D11"]

    def cache_key(self) -> str:
        lat, lon, _ = self._resolve_location()
        return f"weather:{lat:.4f},{lon:.4f}"

    def fetch(self) -> ScrapingResult:
        lat, lon, location_name = self._resolve_location()
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,precipitation",
            "timezone": "auto",
        }
        try:
            with httpx.Client(timeout=SCRAPING_TIMEOUT,
                              headers={"User-Agent": SCRAPING_USER_AGENT}) as client:
                r = client.get(FORECAST_URL, params=params)
                r.raise_for_status()
                data = r.json()
        except httpx.HTTPError as exc:
            raise ScrapingError(f"Falha HTTP no Open-Meteo: {exc}") from exc

        current = data.get("current") or {}
        code = int(current.get("weather_code", 0))
        payload = {
            "location": location_name,
            "latitude": lat,
            "longitude": lon,
            "temperature_c": current.get("temperature_2m"),
            "feels_like_c": current.get("apparent_temperature"),
            "humidity_pct": current.get("relative_humidity_2m"),
            "wind_kmh": current.get("wind_speed_10m"),
            "precipitation_mm": current.get("precipitation"),
            "weather_code": code,
            "weather_description": WMO_DESCRIPTIONS.get(code, f"código {code}"),
            "observed_at": current.get("time"),
            "source_credit": "Open-Meteo (CC BY 4.0)",
        }
        return ScrapingResult(source=self.name, fetched_at=datetime.now(), payload=payload)
