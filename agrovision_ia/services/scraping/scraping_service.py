import threading
from services.scraping.base import ScrapingSource, ScrapingResult, ScrapingError
from services.scraping.cache import ScrapingCache
from services.scraping.rate_limiter import RateLimiter
from services.logging_config import get_logger

log = get_logger("agrovision.scraping.service")


class ScrapingService:
    def __init__(self, sources: list[ScrapingSource], cache: ScrapingCache,
                 rate_limiter: RateLimiter):
        self._sources = {s.name: s for s in sources}
        self._cache = cache
        self._rate = rate_limiter
        self._stop = threading.Event()

    def list_sources(self) -> list[str]:
        return list(self._sources.keys())

    def get(self, source_name: str, *, force: bool = False) -> ScrapingResult | None:
        src = self._sources.get(source_name)
        if not src:
            log.warning("Fonte desconhecida: %s", source_name)
            return None
        key = src.cache_key()
        if not force:
            cached = self._cache.get(key)
            if cached:
                return cached
        if not self._rate.can_request(source_name):
            wait = self._rate.time_until_allowed(source_name)
            log.info("Rate limit em %s (espera %.1fs). Servindo cache stale.", source_name, wait)
            return self._cache.get_stale(key)
        try:
            self._rate.record_request(source_name)
            result = src.fetch()
            self._cache.set(key, result, src.ttl_seconds)
            log.info("Fonte %s atualizada com sucesso.", source_name)
            return result
        except ScrapingError as exc:
            log.warning("Falha controlada em %s: %s", source_name, exc)
            return self._cache.get_stale(key)
        except Exception:
            log.exception("Erro inesperado ao buscar %s", source_name)
            return self._cache.get_stale(key)

    def get_full_context(self) -> dict[str, ScrapingResult]:
        out = {}
        for name in self._sources:
            r = self.get(name)
            if r:
                out[name] = r
        return out

    def status(self) -> dict:
        return {
            "enabled": True,
            "sources": self.list_sources(),
            "cache": self._cache.stats(),
        }

    def background_refresh_loop(self, interval_seconds: int = 60) -> None:
        log.info("Background refresh iniciado (intervalo=%ds).", interval_seconds)
        while not self._stop.wait(interval_seconds):
            for name in self.list_sources():
                self.get(name)

    def stop(self) -> None:
        self._stop.set()
