"""
Domini affidabili per il recupero immagini confezione.

I risultati da provider web vengono accettati solo se l'URL appartiene
a uno di questi domini (o sottodomini).
"""

from __future__ import annotations

from urllib.parse import quote_plus, urlparse

# Portali istituzionali e farmacie online italiane con schede prodotto strutturate
TRUSTED_DRUG_DOMAINS: tuple[str, ...] = (
    "farmaci.agenziafarmaco.gov.it",
    "farmaciaigea.com",
    "farmae.it",
    "redcare.it",
    "farmagalenica.it",
    "farmasave.it",
    "farmaciauno.it",
    "medicitalia.it",
)

# Mappatura titolare AIC → dominio sito istituzionale (ricerca interna)
MANUFACTURER_SEARCH_TEMPLATES: dict[str, str] = {
    "angelini": "https://www.angelini.it/?s={query}",
    "menarini": "https://www.menarini.com/it-it/search?q={query}",
    "chiesi": "https://www.chiesi.com/it/search?q={query}",
    "recordati": "https://www.recordati.com/it/search?q={query}",
    "bayer": "https://www.bayer.com/it/it/search?q={query}",
    "pfizer": "https://www.pfizer.it/search?query={query}",
    "novartis": "https://www.novartis.com/it-it/search?q={query}",
    "sandoz": "https://www.sandoz.it/search?q={query}",
    "teva": "https://www.tevaitalia.it/search?q={query}",
}

# Template ricerca interna su farmacie con URL stabili
PHARMACY_SEARCH_TEMPLATES: tuple[tuple[str, str], ...] = (
    (
        "farmaciaigea.com",
        "https://www.farmaciaigea.com/catalogsearch/result/?q={query}",
    ),
    (
        "farmae.it",
        "https://www.farmae.it/catalogsearch/result/?q={query}",
    ),
    (
        "redcare.it",
        "https://www.redcare.it/search?q={query}",
    ),
)


def normalize_domain(url_or_domain: str) -> str:
    if "://" in url_or_domain:
        host = urlparse(url_or_domain).netloc.lower()
    else:
        host = url_or_domain.lower()
    return host.removeprefix("www.")


def is_trusted_url(url: str, domains: tuple[str, ...] | list[str] | None = None) -> bool:
    allowed = domains or TRUSTED_DRUG_DOMAINS
    host = normalize_domain(url)
    for domain in allowed:
        d = domain.removeprefix("www.")
        if host == d or host.endswith(f".{d}"):
            return True
    return False


def build_site_restriction_clause(
    domains: tuple[str, ...] | list[str],
    *,
    max_sites: int = 6,
) -> str:
    """Clausola site: per Google CSE / query restrittive."""
    selected = list(domains)[:max_sites]
    if not selected:
        return ""
    parts = [f"site:{d}" for d in selected]
    if len(parts) == 1:
        return parts[0]
    return "(" + " OR ".join(parts) + ")"


def build_restricted_search_query(
    base_query: str,
    domains: tuple[str, ...] | list[str] | None = None,
) -> str:
    clause = build_site_restriction_clause(domains or TRUSTED_DRUG_DOMAINS)
    if not clause:
        return base_query
    return f"{base_query} {clause}"


def resolve_manufacturer_search_url(
    holder: str | None,
    query: str,
) -> str | None:
    if not holder:
        return None
    holder_norm = holder.lower()
    for keyword, template in MANUFACTURER_SEARCH_TEMPLATES.items():
        if keyword in holder_norm:
            return template.format(query=quote_plus(query))
    return None
