from datetime import datetime
import re
import httpx
from bs4 import BeautifulSoup
from services.scraping.base import ScrapingSource, ScrapingResult, ScrapingError
from services.config import (
    SCRAPING_USER_AGENT, SCRAPING_TIMEOUT, SCRAPING_MARKET_TTL,
)
from services.logging_config import get_logger

log = get_logger("agrovision.scraping.market")

# Cada commodity tem sua própria subpágina em Notícias Agrícolas
# Estrutura confirmada: table.cot-fisicas, row[1] = dados, 3 colunas (data | preço | variação)
COMMODITY_PAGES: dict[str, tuple[str, str]] = {
    "boi gordo": ("https://www.noticiasagricolas.com.br/cotacoes/boi-gordo", "@"),
    "soja":      ("https://www.noticiasagricolas.com.br/cotacoes/soja",      "saca 60kg"),
    "milho":     ("https://www.noticiasagricolas.com.br/cotacoes/milho",     "saca 60kg"),
    "cafe":      ("https://www.noticiasagricolas.com.br/cotacoes/cafe",      "saca 60kg"),
}

SOURCE_URL = "https://www.noticiasagricolas.com.br/cotacoes/"


def _parse_price_brl(text: str) -> float | None:
    """Converte '349,70' ou '1.555,67' para float (formato BR)."""
    if not text:
        return None
    cleaned = re.sub(r"[^\d,.\-]", "", text).strip()
    if not cleaned:
        return None
    # Formato brasileiro: 1.234,56 → remover ponto (milhar), vírgula → ponto decimal
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_variation(text: str) -> float | None:
    """Converte '+0,13' ou '-0,60' para float."""
    if not text:
        return None
    cleaned = re.sub(r"[^\d,.\-+]", "", text).strip()
    cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _fetch_commodity(product: str, url: str, unit: str) -> dict | None:
    """Busca uma subpágina e extrai preço + variação da table.cot-fisicas."""
    try:
        with httpx.Client(
            timeout=SCRAPING_TIMEOUT,
            headers={"User-Agent": SCRAPING_USER_AGENT},
            follow_redirects=True,
        ) as client:
            r = client.get(url)
            r.raise_for_status()
            html = r.text
    except httpx.HTTPError as exc:
        log.warning("Falha HTTP ao buscar %s (%s): %s", product, url, exc)
        return None

    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", class_="cot-fisicas")
    if not table:
        log.warning("table.cot-fisicas não encontrada para %s — HTML pode ter mudado", product)
        return None

    rows = table.find_all("tr")
    # row[0] = cabeçalho, row[1] = dados, row[2] = rodapé
    if len(rows) < 2:
        log.warning("Estrutura inesperada para %s: apenas %d rows", product, len(rows))
        return None

    cells = [td.get_text(strip=True) for td in rows[1].find_all(["th", "td"])]
    if len(cells) < 2:
        log.warning("Células insuficientes para %s: %s", product, cells)
        return None

    # Coluna 0 = data, coluna 1 = preço, coluna 2 = variação (se existir)
    price = _parse_price_brl(cells[1])
    variation = _parse_variation(cells[2]) if len(cells) > 2 else None
    observed_date = cells[0] if cells[0] else None

    if price is None:
        log.warning("Preço não parseável para %s: '%s'", product, cells[1])
        return None

    return {
        "product": product,
        "price_brl": price,
        "unit": unit,
        "variation_pct": variation,
        "observed_date": observed_date,
    }


class MarketSource(ScrapingSource):
    name = "market"
    ttl_seconds = SCRAPING_MARKET_TTL

    def cache_key(self) -> str:
        return "market:noticiasagricolas:cotacoes"

    def fetch(self) -> ScrapingResult:
        quotes: list[dict] = []
        for product, (url, unit) in COMMODITY_PAGES.items():
            entry = _fetch_commodity(product, url, unit)
            if entry:
                quotes.append(entry)

        if not quotes:
            raise ScrapingError(
                "Nenhuma cotação extraída — todas as subpáginas falharam ou mudaram estrutura"
            )

        payload = {
            "source_url": SOURCE_URL,
            "fonte_credito": "CEPEA/ESALQ-USP via Notícias Agrícolas",
            "quotes": quotes,
        }
        log.info("Cotações extraídas: %d produtos", len(quotes))
        return ScrapingResult(source=self.name, fetched_at=datetime.now(), payload=payload)
