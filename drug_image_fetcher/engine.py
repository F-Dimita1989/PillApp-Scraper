"""
Pipeline di recupero immagine farmaco da codice AIC.

Logica:
  1. Prova URL diretti costruiti con l'AIC (farmae.it ha AIC nell'URL e nel filename)
  2. Cerca l'AIC su siti trusted (ricerca interna)
  3. Dal primo link prodotto che contiene l'AIC → estrai og:image
  4. Fallback: Google CSE se configurato
"""

from __future__ import annotations

import json
import re
import time
from urllib.parse import quote_plus, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from drug_image_fetcher.config import FetcherConfig
from drug_image_fetcher.logging_config import logger
from drug_image_fetcher.models import ImageFetchResult

# ---------------------------------------------------------------------------
# Siti trusted: (dominio, template_ricerca_per_AIC, hints_url_prodotto)
# ---------------------------------------------------------------------------
_PHARMACY_SITES: list[dict] = [
    {
        "domain": "farmae.it",
        # API Shopify suggest — restituisce JSON direttamente, funziona senza JS
        "suggest_api": "https://www.farmae.it/search/suggest.json?q={query}&resources[type]=product&resources[limit]=10",
        "search": "https://www.farmae.it/search?q={aic}",
        "product_hints": ("/products/",),
    },
    {
        "domain": "farmaciaigea.com",
        "suggest_api": None,
        "search": "https://www.farmaciaigea.com/search?q={aic}",
        "product_hints": ("/prodotti/", "/product/", "/farmaci/"),
    },
    {
        "domain": "redcare.it",
        "suggest_api": None,
        "search": "https://www.redcare.it/search?q={aic}",
        "product_hints": ("/p/", "/products/", "/prodotti/"),
    },
    {
        "domain": "medicitalia.it",
        "suggest_api": None,
        "search": "https://www.medicitalia.it/farmaci/?q={aic}",
        "product_hints": ("/farmaci/",),
    },
]

GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"


def _build_session(config: FetcherConfig) -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": config.user_agent,
        "Accept-Language": "it-IT,it;q=0.9",
    })
    retry = Retry(
        total=config.max_retries,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def _get_html(session: requests.Session, url: str, timeout: float) -> str | None:
    try:
        r = session.get(url, timeout=timeout)
        if r.status_code == 200:
            return r.text
        logger.debug("HTTP %s → %s", r.status_code, url)
        return None
    except requests.RequestException as exc:
        logger.debug("Errore fetch %s: %s", url, exc)
        return None


def _aic_in_text(html_text: str, aic: str) -> bool:
    """Verifica che l'AIC (solo cifre) compaia nel testo/HTML della pagina."""
    return aic in re.sub(r"\D", "", html_text)


def _aic_in_url(url: str, aic: str) -> bool:
    return aic in re.sub(r"\D", "", url)


def _extract_og_image(html: str, base_url: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    for meta in soup.find_all("meta"):
        prop = (meta.get("property") or meta.get("name") or "").lower()
        if prop in {"og:image", "og:image:url", "twitter:image"}:
            content = (meta.get("content") or "").strip()
            if content and content.startswith("http"):
                return content
    # Fallback: JSON-LD Product image
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            types = item.get("@type", "")
            if isinstance(types, str):
                types = [types]
            if "Product" in types or "Drug" in types:
                img = item.get("image")
                if isinstance(img, str) and img.startswith("http"):
                    return img
                if isinstance(img, list) and img:
                    first = img[0]
                    if isinstance(first, str):
                        return first
                    if isinstance(first, dict):
                        return first.get("url")
    return None


def _extract_product_links(
    html: str, base_url: str, aic: str, product_hints: tuple[str, ...]
) -> list[str]:
    """
    Estrae dalla pagina di ricerca i link a schede prodotto.
    Preferisce quelli che hanno l'AIC nell'URL (match forte).
    """
    soup = BeautifulSoup(html, "html.parser")
    domain = urlparse(base_url).netloc.removeprefix("www.")
    with_aic: list[str] = []
    without_aic: list[str] = []

    for a in soup.find_all("a", href=True):
        href = str(a["href"]).strip()
        absolute = urljoin(base_url, href).split("?")[0].split("#")[0]

        # deve restare sullo stesso dominio
        if domain not in urlparse(absolute).netloc:
            continue
        # deve sembrare una scheda prodotto
        if not any(hint in absolute for hint in product_hints):
            continue

        if _aic_in_url(absolute, aic):
            with_aic.append(absolute)
        else:
            without_aic.append(absolute)

    # prima i link con AIC nell'URL, poi gli altri
    seen: set[str] = set()
    result: list[str] = []
    for url in with_aic + without_aic:
        if url not in seen:
            seen.add(url)
            result.append(url)
    return result


def _shopify_suggest_links(
    session: requests.Session,
    api_template: str,
    query: str,
    base_domain: str,
    timeout: float,
) -> list[str]:
    """Usa l'API Shopify suggest.json per ottenere URL prodotto senza JS."""
    url = api_template.format(query=quote_plus(query))
    try:
        r = session.get(url, timeout=timeout)
        if r.status_code != 200:
            return []
        data = r.json()
    except Exception:
        return []
    products = (
        data.get("resources", {}).get("results", {}).get("products", [])
    )
    links = []
    for p in products:
        path = (p.get("url") or "").split("?")[0]
        if not path:
            continue
        absolute = f"https://www.{base_domain}{path}" if path.startswith("/") else path
        if absolute not in links:
            links.append(absolute)
    return links


def _try_google_cse(
    session: requests.Session, config: FetcherConfig, aic: str
) -> list[str]:
    if not config.google_cse_enabled():
        return []
    site_clause = " OR ".join(f"site:{d}" for d in config.trusted_domains[:5])
    params = {
        "key": config.google_cse_api_key,
        "cx": config.google_cse_engine_id,
        "q": f"{aic} ({site_clause})",
        "num": 5,
        "safe": "active",
    }
    try:
        r = session.get(
            GOOGLE_CSE_URL, params=params, timeout=config.request_timeout_seconds
        )
        if r.status_code != 200:
            return []
        return [item["link"] for item in r.json().get("items", []) if "link" in item]
    except Exception as exc:
        logger.debug("Google CSE fallito: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Entry point principale
# ---------------------------------------------------------------------------

def fetch_image_by_aic(
    aic: str,
    name: str | None = None,
    config: FetcherConfig | None = None,
) -> ImageFetchResult:
    """
    Cerca l'immagine della confezione identificata dall'AIC.

    Strategia per ogni sito trusted:
      1. Cerca per AIC → controlla se i link prodotto contengono l'AIC
      2. Se niente, cerca per nome (se fornito) → filtra solo i link che contengono l'AIC
      3. Dalla scheda prodotto confermata → og:image
      4. Fallback: Google CSE
    """
    aic = re.sub(r"\D", "", aic.strip())
    if not aic:
        return ImageFetchResult.not_found("AIC non valido")

    cfg = config or FetcherConfig.production()
    session = _build_session(cfg)

    logger.info("Cercando immagine per AIC %s", aic)

    # Fase 1: siti trusted
    for site in _PHARMACY_SITES:
        if site["domain"] not in cfg.trusted_domains:
            continue

        product_hints = tuple(site["product_hints"])

        # Query ordinate: prima AIC, poi nome se disponibile
        queries = [aic]
        if name and name.strip():
            queries.append(name.strip())

        candidate_links: list[str] = []
        for query in queries:
            # Usa Shopify suggest API se disponibile (più affidabile dell'HTML)
            if site.get("suggest_api"):
                api_links = _shopify_suggest_links(
                    session,
                    site["suggest_api"],
                    query,
                    site["domain"],
                    cfg.request_timeout_seconds,
                )
                for link in api_links:
                    if link not in candidate_links:
                        candidate_links.append(link)
            else:
                search_url = site["search"].format(aic=quote_plus(query))
                html = _get_html(session, search_url, cfg.request_timeout_seconds)
                if html:
                    links = _extract_product_links(html, search_url, aic, product_hints)
                    for link in links:
                        if link not in candidate_links:
                            candidate_links.append(link)

        logger.debug("%s → %d link candidati", site["domain"], len(candidate_links))

        for product_url in candidate_links[:8]:
            prod_html = _get_html(session, product_url, cfg.request_timeout_seconds)
            if not prod_html:
                continue

            # La pagina deve confermare l'AIC (nell'URL o nel testo/HTML)
            if not (_aic_in_url(product_url, aic) or _aic_in_text(prod_html, aic)):
                logger.debug("AIC non confermato su %s, salto", product_url)
                continue

            image_url = _extract_og_image(prod_html, product_url)
            if image_url:
                logger.info("Immagine trovata su %s", product_url)
                return ImageFetchResult.found(image_url, product_url)

    # Fase 2: Google CSE
    cse_urls = _try_google_cse(session, cfg, aic)
    for url in cse_urls:
        html = _get_html(session, url, cfg.request_timeout_seconds)
        if not html:
            continue
        if not (_aic_in_url(url, aic) or _aic_in_text(html, aic)):
            continue
        image_url = _extract_og_image(html, url)
        if image_url:
            logger.info("Immagine trovata via CSE su %s", url)
            return ImageFetchResult.found(image_url, url)

    return ImageFetchResult.not_found(
        f"Nessuna immagine trovata per AIC {aic} — prova a configurare Google CSE"
    )
