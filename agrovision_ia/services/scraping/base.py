from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


class ScrapingError(Exception):
    """Erro irrecuperável de uma fonte de scraping."""


@dataclass(frozen=True)
class ScrapingResult:
    source: str
    fetched_at: datetime
    payload: dict[str, Any] = field(default_factory=dict)


class ScrapingSource(ABC):
    name: str = ""
    ttl_seconds: int = 600

    @abstractmethod
    def fetch(self) -> ScrapingResult: ...

    @abstractmethod
    def cache_key(self) -> str: ...
