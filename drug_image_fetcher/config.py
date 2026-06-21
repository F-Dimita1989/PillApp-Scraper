"""Configurazione centralizzata del fetcher."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from drug_image_fetcher.search.trusted_sites import TRUSTED_DRUG_DOMAINS


@dataclass
class FetcherConfig:
    """Parametri runtime del motore di recupero immagini."""

    # Rete
    user_agent: str = (
        "PillApp-DrugImageFetcher/0.1 (+https://pillapp.example; clinical-use)"
    )
    request_timeout_seconds: float = 15.0
    max_retries: int = 3
    retry_backoff_base_seconds: float = 1.0
    use_httpx: bool = False

    # Cache
    enable_cache: bool = True
    aic_cache_ttl_seconds: int = 86_400  # 24h
    http_cache_ttl_seconds: int = 3_600  # 1h
    cache_directory: str | None = None

    # Pipeline
    max_search_queries: int = 4
    max_pages_per_query: int = 5
    max_total_pages: int = 12

    # Scoring — soglia conservativa: preferisce non mostrare nulla
    min_confidence_score: float = 0.72
    min_image_width: int = 120
    min_image_height: int = 120

    # Pesi scoring (somma teorica max ~1.0 prima di penalità)
    weight_aic_match: float = 0.35
    weight_name_match: float = 0.22
    weight_dosage_match: float = 0.15
    weight_form_match: float = 0.12
    weight_quantity_match: float = 0.12
    weight_company_match: float = 0.06

    penalty_dosage_mismatch: float = 0.25
    penalty_form_mismatch: float = 0.22
    penalty_quantity_mismatch: float = 0.20
    penalty_small_image: float = 0.12
    penalty_generic_page: float = 0.18
    penalty_weak_name: float = 0.10

    # Provider ricerca
    trusted_domains: tuple[str, ...] = TRUSTED_DRUG_DOMAINS
    extra_curated_urls: list[str] = field(default_factory=list)
    google_cse_api_key: str | None = None
    google_cse_engine_id: str | None = None
    enable_trusted_pharmacy_search: bool = True
    enable_manufacturer_search: bool = True

    @classmethod
    def conservative(cls) -> FetcherConfig:
        """Profilo ultra-conservativo per ambienti clinici."""
        return cls(
            min_confidence_score=0.78,
            max_search_queries=3,
            max_total_pages=8,
            penalty_dosage_mismatch=0.30,
            penalty_form_mismatch=0.28,
            penalty_quantity_mismatch=0.25,
        )

    @classmethod
    def from_env(cls, **overrides: object) -> FetcherConfig:
        """
        Carica credenziali da variabili d'ambiente.

        GOOGLE_CSE_API_KEY, GOOGLE_CSE_ENGINE_ID, DRUG_IMAGE_CACHE_DIR
        """
        config = cls.conservative()
        api_key = os.getenv("GOOGLE_CSE_API_KEY")
        engine_id = os.getenv("GOOGLE_CSE_ENGINE_ID")
        cache_dir = os.getenv("DRUG_IMAGE_CACHE_DIR")

        if api_key:
            config.google_cse_api_key = api_key
        if engine_id:
            config.google_cse_engine_id = engine_id
        if cache_dir:
            config.cache_directory = cache_dir

        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config

    @classmethod
    def production(cls) -> FetcherConfig:
        """Profilo produzione PillApp: conservativo + env."""
        return cls.from_env()

    def google_cse_enabled(self) -> bool:
        return bool(self.google_cse_api_key and self.google_cse_engine_id)
