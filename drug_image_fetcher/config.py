"""Configurazione del fetcher."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class FetcherConfig:
    user_agent: str = (
        "PillApp-DrugImageFetcher/1.0 (+https://pillapp.example; clinical-use)"
    )
    request_timeout_seconds: float = 15.0
    max_retries: int = 2
    enable_cache: bool = True
    cache_ttl_seconds: int = 86_400  # 24h
    cache_directory: str | None = None
    google_cse_api_key: str | None = None
    google_cse_engine_id: str | None = None

    # Domini trusted su cui cercare
    trusted_domains: tuple[str, ...] = (
        "farmae.it",
        "farmaciaigea.com",
        "redcare.it",
        "medicitalia.it",
    )

    @classmethod
    def from_env(cls) -> FetcherConfig:
        cfg = cls()
        cfg.google_cse_api_key = os.getenv("GOOGLE_CSE_API_KEY")
        cfg.google_cse_engine_id = os.getenv("GOOGLE_CSE_ENGINE_ID")
        if d := os.getenv("DRUG_IMAGE_CACHE_DIR"):
            cfg.cache_directory = d
        return cfg

    @classmethod
    def production(cls) -> FetcherConfig:
        return cls.from_env()

    def google_cse_enabled(self) -> bool:
        return bool(self.google_cse_api_key and self.google_cse_engine_id)
