"""Pipeline principale di recupero immagine farmaco."""

from __future__ import annotations

from drug_image_fetcher.cache import DrugImageCache, HttpResponseCache
from drug_image_fetcher.config import FetcherConfig
from drug_image_fetcher.fetch.http_client import HttpClientProtocol, build_http_client
from drug_image_fetcher.fetch.page_parser import extract_image_candidates, extract_page_text
from drug_image_fetcher.logging_config import logger
from drug_image_fetcher.models import DrugInfo, ImageFetchResult, PageMatch
from drug_image_fetcher.normalize.text import normalize_aic
from drug_image_fetcher.scoring.scorer import PageScorer, select_best_match
from drug_image_fetcher.search.providers import CompositeSearchProvider, SearchProvider
from drug_image_fetcher.search.queries import build_search_queries


class DrugImageEngine:
    """Orchestra query, fetch, parsing, scoring e selezione."""

    def __init__(
        self,
        config: FetcherConfig | None = None,
        *,
        search_provider: SearchProvider | None = None,
        http_client: HttpClientProtocol | None = None,
        aic_cache: DrugImageCache | None = None,
        http_cache: HttpResponseCache | None = None,
    ) -> None:
        self._config = config or FetcherConfig()
        self._http_cache = http_cache or HttpResponseCache(
            ttl_seconds=self._config.http_cache_ttl_seconds,
            directory=self._config.cache_directory,
        )
        self._aic_cache = aic_cache or DrugImageCache(
            ttl_seconds=self._config.aic_cache_ttl_seconds,
            directory=self._config.cache_directory,
        )
        self._http = http_client or build_http_client(self._config, self._http_cache)
        self._search_provider = search_provider
        self._scorer = PageScorer(self._config)

    def fetch(self, drug: DrugInfo) -> ImageFetchResult:
        aic_key = normalize_aic(drug.aic)
        if not aic_key:
            return ImageFetchResult.not_found(["AIC mancante o non valido"])

        if self._config.enable_cache:
            cached = self._aic_cache.get(aic_key)
            if cached is not None:
                logger.info("Risultato da cache AIC: %s", aic_key)
                return cached

        provider = self._resolve_search_provider(drug)
        queries = build_search_queries(drug, self._config.max_search_queries)
        if not queries:
            return ImageFetchResult.not_found(["impossibile costruire query di ricerca"])

        logger.info(
            "Avvio fetch immagine per AIC=%s, query=%d",
            aic_key,
            len(queries),
        )

        visited_pages: set[str] = set()
        all_matches: list[PageMatch] = []

        for query in queries:
            if len(visited_pages) >= self._config.max_total_pages:
                break

            search_results = provider.search(
                query,
                max_results=self._config.max_pages_per_query,
            )
            logger.debug("Query '%s' → %d risultati", query, len(search_results))

            for result in search_results:
                if result.url in visited_pages:
                    continue
                if len(visited_pages) >= self._config.max_total_pages:
                    break

                visited_pages.add(result.url)
                page_match = self._process_page(drug, result.url)
                if page_match:
                    all_matches.extend(page_match)

        best = select_best_match(all_matches, self._config)
        if best is None:
            reasons = _collect_rejection_reasons(all_matches)
            outcome = ImageFetchResult.not_found(reasons)
        else:
            candidate = best.candidates[0]
            outcome = ImageFetchResult.found(
                image_url=candidate.image_url,
                source_page_url=best.source_page_url,
                confidence_score=best.relevance_score,
                matched_fields=best.matched_fields,
                rejected_reasons=best.rejected_reasons,
            )

        if self._config.enable_cache:
            self._aic_cache.set(aic_key, outcome)

        return outcome

    def _resolve_search_provider(self, drug: DrugInfo) -> SearchProvider:
        if self._search_provider is not None:
            return self._search_provider

        from drug_image_fetcher.search.providers import build_production_providers

        return build_production_providers(drug, self._config, self._http.get)

    def _process_page(
        self, drug: DrugInfo, page_url: str
    ) -> list[PageMatch]:
        html = self._http.get(page_url)
        if not html:
            return []

        page_text = extract_page_text(html)
        candidates = extract_image_candidates(
            html,
            page_url,
            min_width=self._config.min_image_width,
            min_height=self._config.min_image_height,
        )

        return self._scorer.score_page(drug, page_url, page_text, candidates)


def _collect_rejection_reasons(matches: list[PageMatch]) -> list[str]:
    if not matches:
        return ["nessuna pagina utile trovata"]

    best = max(matches, key=lambda m: m.relevance_score)
    reasons = [
        f"score massimo {best.relevance_score:.2f} sotto soglia",
    ]
    reasons.extend(best.rejected_reasons[:5])
    return reasons
