from datetime import datetime
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from services.scraping.base import ScrapingSource, ScrapingResult, ScrapingError
from services.config import (
    SCRAPING_USER_AGENT, SCRAPING_TIMEOUT, SCRAPING_NEWS_TTL,
)
from services.logging_config import get_logger

log = get_logger("agrovision.scraping.news")

# Fonte: Embrapa (Empresa Brasileira de Pesquisa Agropecuária) — instituição pública federal
# robots.txt: /busca-de-noticias não está em nenhuma linha Disallow.
# Seletores validados em 29/05/2026:
#   container = div.conteudo
#   título    = div.titulo a
#   data      = span.situacao
#   link      = div.titulo a [href]
NEWS_URL = "https://www.embrapa.br/busca-de-noticias"
MAX_HEADLINES = 5
MAX_TITLE_LEN = 120


class NewsSource(ScrapingSource):
    name = "news"
    ttl_seconds = SCRAPING_NEWS_TTL

    def cache_key(self) -> str:
        return "news:embrapa:busca-de-noticias"

    def fetch(self) -> ScrapingResult:
        try:
            with httpx.Client(
                timeout=SCRAPING_TIMEOUT,
                headers={"User-Agent": SCRAPING_USER_AGENT},
                follow_redirects=True,
            ) as client:
                r = client.get(NEWS_URL)
                r.raise_for_status()
                html = r.text
        except httpx.HTTPError as exc:
            raise ScrapingError(f"Falha HTTP em {NEWS_URL}: {exc}") from exc

        soup = BeautifulSoup(html, "lxml")

        items = soup.select("div.conteudo")
        if not items:
            log.warning("Nenhum div.conteudo encontrado — HTML do Embrapa pode ter mudado")
            raise ScrapingError("HTML inesperado em embrapa.br/busca-de-noticias")

        headlines: list[dict] = []
        for item in items[:MAX_HEADLINES]:
            titulo_el = item.select_one("div.titulo a")
            data_el = item.select_one("span.situacao")

            if not titulo_el:
                continue

            title = titulo_el.get_text(strip=True)[:MAX_TITLE_LEN]
            date = data_el.get_text(strip=True) if data_el else ""
            href = titulo_el.get("href")
            url = urljoin(NEWS_URL, href) if href else None

            headlines.append({"title": title, "date": date, "url": url})

        if not headlines:
            raise ScrapingError("Nenhuma manchete extraída")

        log.info("Manchetes extraídas: %d itens", len(headlines))
        payload = {
            "source_url": NEWS_URL,
            "fonte_credito": "Embrapa/MAPA",
            "headlines": headlines,
        }
        return ScrapingResult(source=self.name, fetched_at=datetime.now(), payload=payload)
