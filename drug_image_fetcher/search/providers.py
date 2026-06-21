"""
Provider di ricerca web — stack produzione PillApp.

Ordine predefinito (build_production_providers):
  1. AifaDirectPageProvider      — fonte istituzionale per AIC
  2. TrustedPharmacySearchProvider — ricerca su farmacie whitelist
  3. ManufacturerSiteProvider    — ricerca sul sito del titolare AIC
  4. GoogleCustomSearchProvider  — CSE limitato ai domini trusted (se configurato)
  5. StaticUrlListProvider       — URL curati manualmente (extra)
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable
from urllib.parse import quote_plus

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from drug_image_fetcher.config import FetcherConfig
from drug_image_fetcher.logging_config import logger
from drug_image_fetcher.models import DrugInfo
from drug_image_fetcher.normalize.text import normalize_aic
from drug_image_fetcher.search.trusted_sites import (
    PHARMACY_SEARCH_TEMPLATES,
    build_restricted_search_query,
    is_trusted_url,
    resolve_manufacturer_search_url,
)

GOOGLE_CSE_API_URL = "https://www.googleapis.com/customsearch/v1"


@dataclass(frozen=True, slots=True)
class SearchResult:
    url: str
    title: str = ""
    snippet: str = ""
    provider: str = ""


class SearchProvider(ABC):
    """Interfaccia per qualsiasi backend di ricerca."""

    name: str = "base"

    @abstractmethod
    def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        ...


class CompositeSearchProvider(SearchProvider):
    """Concatena più provider fino a raggiungere max_results."""

    name = "composite"

    def __init__(self, providers: list[SearchProvider]) -> None:
        self._providers = providers

    def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        results: list[SearchResult] = []
        seen_urls: set[str] = set()

        for provider in self._providers:
            if len(results) >= max_results:
                break
            try:
                batch = provider.search(
                    query,
                    max_results=max_results - len(results),
                )
            except Exception as exc:
                logger.warning("Provider %s fallito: %s", provider.name, exc)
                continue

            for item in batch:
                if item.url not in seen_urls:
                    seen_urls.add(item.url)
                    results.append(item)

        return results


class AifaDirectPageProvider(SearchProvider):
    """
    URL diretto sul portale AIFA per AIC.

    TODO: verificare periodicamente il pattern URL su farmaci.agenziafarmaco.gov.it
    """

    name = "aifa_direct"

    def __init__(self, drug: DrugInfo) -> None:
        self._drug = drug

    def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        aic = normalize_aic(self._drug.aic)
        if not aic:
            return []

        urls = [
            (
                f"https://farmaci.agenziafarmaco.gov.it/bancadatifarmaci/"
                f"farmaco?aic={aic}"
            ),
        ]
        return [
            SearchResult(url=url, title=f"AIFA {aic}", provider=self.name)
            for url in urls[:max_results]
        ]


class TrustedPharmacySearchProvider(SearchProvider):
    """
    Genera URL di ricerca interna su farmacie italiane whitelist.

    Non scraping cieco: solo template URL noti e domini verificati.
    Il motore analizza la pagina risultati; lo scoring filtra i falsi positivi.
    """

    name = "trusted_pharmacy"

    def __init__(self, config: FetcherConfig) -> None:
        self._config = config

    def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        results: list[SearchResult] = []
        encoded = quote_plus(query)

        for domain, template in PHARMACY_SEARCH_TEMPLATES:
            if domain not in self._config.trusted_domains:
                continue
            url = template.format(query=encoded)
            results.append(
                SearchResult(
                    url=url,
                    title=f"Ricerca {domain}",
                    provider=self.name,
                )
            )
            if len(results) >= max_results:
                break

        return results


class ManufacturerSiteProvider(SearchProvider):
    """Ricerca sul sito del titolare AIC, se mappato."""

    name = "manufacturer_site"

    def __init__(self, drug: DrugInfo) -> None:
        self._drug = drug

    def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        url = resolve_manufacturer_search_url(
            self._drug.marketing_authorization_holder,
            query,
        )
        if not url:
            return []

        return [
            SearchResult(
                url=url,
                title=f"Titolare {self._drug.marketing_authorization_holder}",
                provider=self.name,
            )
        ][:max_results]


class StaticUrlListProvider(SearchProvider):
    """URL curati manualmente dal team PillApp."""

    name = "static_urls"

    def __init__(self, urls: list[str]) -> None:
        self._urls = urls

    def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        return [
            SearchResult(url=url, title=url, provider=self.name)
            for url in self._urls[:max_results]
        ]


class GoogleCustomSearchProvider(SearchProvider):
    """
    Google Custom Search JSON API con filtro domini trusted.

    Configurare il motore CSE su https://programmablesearchengine.google.com/
    includendo i domini in trusted_sites.TRUSTED_DRUG_DOMAINS.

    Variabili d'ambiente: GOOGLE_CSE_API_KEY, GOOGLE_CSE_ENGINE_ID
    """

    name = "google_cse"

    def __init__(self, config: FetcherConfig) -> None:
        if not config.google_cse_enabled():
            raise ValueError("Google CSE richiede api_key e engine_id")

        self._config = config
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": config.user_agent})

        retry = Retry(
            total=config.max_retries,
            backoff_factor=config.retry_backoff_base_seconds,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self._session.mount("https://", adapter)

    def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        restricted_query = build_restricted_search_query(
            query,
            self._config.trusted_domains,
        )
        params = {
            "key": self._config.google_cse_api_key,
            "cx": self._config.google_cse_engine_id,
            "q": restricted_query,
            "num": min(max_results, 10),
            "safe": "active",
        }

        try:
            response = self._session.get(
                GOOGLE_CSE_API_URL,
                params=params,
                timeout=self._config.request_timeout_seconds,
            )
        except requests.RequestException as exc:
            logger.warning("Google CSE request fallita: %s", exc)
            return []

        if response.status_code != 200:
            logger.info("Google CSE HTTP %s", response.status_code)
            return []

        try:
            payload = response.json()
        except json.JSONDecodeError:
            logger.warning("Google CSE risposta non JSON")
            return []

        if "error" in payload:
            logger.warning(
                "Google CSE errore: %s",
                payload["error"].get("message", "unknown"),
            )
            return []

        results: list[SearchResult] = []
        for item in payload.get("items", []):
            url = item.get("link", "")
            if not url.startswith("http"):
                continue
            if not is_trusted_url(url, self._config.trusted_domains):
                logger.debug("Google CSE URL fuori whitelist ignorato: %s", url)
                continue

            results.append(
                SearchResult(
                    url=url,
                    title=item.get("title", ""),
                    snippet=item.get("snippet", ""),
                    provider=self.name,
                )
            )
            if len(results) >= max_results:
                break

        logger.debug(
            "Google CSE query='%s' → %d risultati trusted",
            restricted_query[:80],
            len(results),
        )
        return results


def build_production_providers(
    drug: DrugInfo,
    config: FetcherConfig,
) -> CompositeSearchProvider:
    """
    Stack produzione consigliato per PillApp.

    AIFA → farmacie trusted → titolare AIC → Google CSE → URL extra
    """
    providers: list[SearchProvider] = [
        AifaDirectPageProvider(drug),
    ]

    if config.enable_trusted_pharmacy_search:
        providers.append(TrustedPharmacySearchProvider(config))

    if config.enable_manufacturer_search and drug.marketing_authorization_holder:
        providers.append(ManufacturerSiteProvider(drug))

    if config.google_cse_enabled():
        providers.append(GoogleCustomSearchProvider(config))
    else:
        logger.info(
            "Google CSE non configurato — imposta GOOGLE_CSE_API_KEY e "
            "GOOGLE_CSE_ENGINE_ID per copertura web estesa"
        )

    if config.extra_curated_urls:
        providers.append(StaticUrlListProvider(config.extra_curated_urls))

    return CompositeSearchProvider(providers)


def build_default_providers(
    drug: DrugInfo,
    http_get: Callable[[str], str | None],
    *,
    config: FetcherConfig | None = None,
    extra_urls: list[str] | None = None,
) -> CompositeSearchProvider:
    """Retrocompatibilità — delega a build_production_providers."""
    cfg = config or FetcherConfig.conservative()
    if extra_urls:
        merged = list(cfg.extra_curated_urls) + list(extra_urls)
        cfg.extra_curated_urls = merged
    return build_production_providers(drug, cfg)
