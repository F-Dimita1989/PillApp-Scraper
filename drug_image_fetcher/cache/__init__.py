"""Sistema di cache TTL per risultati AIC e risposte HTTP."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict
from pathlib import Path
from threading import RLock
from typing import Any, Generic, TypeVar

from drug_image_fetcher.logging_config import logger
from drug_image_fetcher.models import ImageFetchResult

T = TypeVar("T")


class TTLCache(Generic[T]):
    """Cache in-memory con scadenza per chiave."""

    def __init__(self, ttl_seconds: int, name: str = "cache") -> None:
        self._ttl = ttl_seconds
        self._name = name
        self._store: dict[str, tuple[float, T]] = {}
        self._lock = RLock()

    def get(self, key: str) -> T | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: T) -> None:
        with self._lock:
            self._store[key] = (time.monotonic() + self._ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


class DrugImageCache:
    """Cache risultati per AIC con persistenza opzionale su disco."""

    def __init__(
        self,
        ttl_seconds: int = 86_400,
        directory: str | Path | None = None,
    ) -> None:
        self._memory = TTLCache[ImageFetchResult](ttl_seconds, name="aic")
        self._directory = Path(directory) if directory else None
        if self._directory:
            self._directory.mkdir(parents=True, exist_ok=True)

    def _file_path(self, aic: str) -> Path | None:
        if not self._directory:
            return None
        safe_key = hashlib.sha256(aic.encode()).hexdigest()[:16]
        return self._directory / f"aic_{safe_key}.json"

    def get(self, aic: str) -> ImageFetchResult | None:
        cached = self._memory.get(aic)
        if cached is not None:
            logger.debug("Cache AIC hit (memory): %s", aic)
            return cached

        path = self._file_path(aic)
        if path and path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                result = _deserialize_result(data)
                self._memory.set(aic, result)
                logger.debug("Cache AIC hit (disk): %s", aic)
                return result
            except (json.JSONDecodeError, KeyError, TypeError):
                logger.warning("Cache AIC corrotta, ignorata: %s", path)

        return None

    def set(self, aic: str, result: ImageFetchResult) -> None:
        self._memory.set(aic, result)
        path = self._file_path(aic)
        if path:
            path.write_text(
                json.dumps(_serialize_result(result), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )


class HttpResponseCache:
    """Cache contenuto HTML per URL."""

    def __init__(
        self,
        ttl_seconds: int = 3_600,
        directory: str | Path | None = None,
    ) -> None:
        self._memory = TTLCache[str](ttl_seconds, name="http")
        self._directory = Path(directory) if directory else None
        if self._directory:
            self._directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _key(url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()

    def get(self, url: str) -> str | None:
        key = self._key(url)
        cached = self._memory.get(key)
        if cached is not None:
            return cached

        if self._directory:
            path = self._directory / f"http_{key}.html"
            if path.exists():
                content = path.read_text(encoding="utf-8")
                self._memory.set(key, content)
                return content
        return None

    def set(self, url: str, content: str) -> None:
        key = self._key(url)
        self._memory.set(key, content)
        if self._directory:
            path = self._directory / f"http_{key}.html"
            path.write_text(content, encoding="utf-8")


def _serialize_result(result: ImageFetchResult) -> dict[str, Any]:
    return asdict(result)


def _deserialize_result(data: dict[str, Any]) -> ImageFetchResult:
    return ImageFetchResult(**data)
