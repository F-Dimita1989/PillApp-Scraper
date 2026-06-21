"""Client HTTP con retry, backoff e cache."""

from __future__ import annotations

import time
from typing import Protocol
from urllib.parse import urlparse

import requests
from requests import Response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from drug_image_fetcher.cache import HttpResponseCache
from drug_image_fetcher.config import FetcherConfig
from drug_image_fetcher.logging_config import logger


class HttpClientProtocol(Protocol):
    def get(self, url: str) -> str | None: ...


class RequestsHttpClient:
    """Client basato su requests con retry configurabile."""

    def __init__(self, config: FetcherConfig, cache: HttpResponseCache | None = None) -> None:
        self._config = config
        self._cache = cache
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": config.user_agent})

        retry_strategy = Retry(
            total=config.max_retries,
            backoff_factor=config.retry_backoff_base_seconds,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

    def get(self, url: str) -> str | None:
        if not _is_valid_http_url(url):
            logger.warning("URL non valido ignorato: %s", url)
            return None

        if self._cache and self._config.enable_cache:
            cached = self._cache.get(url)
            if cached is not None:
                logger.debug("HTTP cache hit: %s", url)
                return cached

        try:
            response: Response = self._session.get(
                url,
                timeout=self._config.request_timeout_seconds,
            )
            if response.status_code != 200:
                logger.info(
                    "HTTP %s per %s",
                    response.status_code,
                    url,
                )
                return None

            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                logger.debug("Content-Type non HTML ignorato: %s", content_type)
                return None

            text = response.text
            if self._cache and self._config.enable_cache:
                self._cache.set(url, text)

            return text

        except requests.RequestException as exc:
            logger.warning("Errore HTTP per %s: %s", url, exc)
            return None


class HttpxHttpClient:
    """Client alternativo basato su httpx (opzionale)."""

    def __init__(self, config: FetcherConfig, cache: HttpResponseCache | None = None) -> None:
        try:
            import httpx
        except ImportError as exc:
            raise ImportError(
                "httpx non installato. Esegui: pip install httpx"
            ) from exc

        self._httpx = httpx
        self._config = config
        self._cache = cache
        self._client = httpx.Client(
            headers={"User-Agent": config.user_agent},
            timeout=config.request_timeout_seconds,
            follow_redirects=True,
        )

    def get(self, url: str) -> str | None:
        if not _is_valid_http_url(url):
            return None

        if self._cache and self._config.enable_cache:
            cached = self._cache.get(url)
            if cached is not None:
                return cached

        for attempt in range(self._config.max_retries):
            try:
                response = self._client.get(url)
                if response.status_code == 200:
                    content_type = response.headers.get("Content-Type", "")
                    if "text/html" in content_type or "application/xhtml" in content_type:
                        text = response.text
                        if self._cache and self._config.enable_cache:
                            self._cache.set(url, text)
                        return text
                    return None

                if response.status_code in {429, 500, 502, 503, 504}:
                    _backoff_sleep(self._config, attempt)
                    continue
                return None

            except self._httpx.RequestError as exc:
                logger.warning("Errore httpx per %s: %s", url, exc)
                _backoff_sleep(self._config, attempt)

        return None


def build_http_client(
    config: FetcherConfig,
    cache: HttpResponseCache | None = None,
) -> HttpClientProtocol:
    if config.use_httpx:
        return HttpxHttpClient(config, cache)
    return RequestsHttpClient(config, cache)


def _backoff_sleep(config: FetcherConfig, attempt: int) -> None:
    delay = config.retry_backoff_base_seconds * (2**attempt)
    time.sleep(delay)


def _is_valid_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
