"""Test del fetcher AIC-first."""

from unittest.mock import MagicMock, patch

from drug_image_fetcher.api import fetch_drug_image
from drug_image_fetcher.config import FetcherConfig
from drug_image_fetcher.engine import (
    _aic_in_text,
    _aic_in_url,
    _extract_og_image,
    _extract_product_links,
)
from drug_image_fetcher.models import ImageFetchResult


# ---------------------------------------------------------------------------
# Unit test sulle funzioni helper
# ---------------------------------------------------------------------------

def test_aic_in_url_true() -> None:
    assert _aic_in_url("https://www.farmae.it/products/oki-048414104", "048414104")


def test_aic_in_url_false() -> None:
    assert not _aic_in_url("https://www.farmae.it/products/tachipirina", "048414104")


def test_aic_in_text_true() -> None:
    assert _aic_in_text("<html>AIC 048414104</html>", "048414104")


def test_aic_in_text_false() -> None:
    assert not _aic_in_text("<html>altro farmaco</html>", "048414104")


def test_extract_og_image_meta() -> None:
    html = '<meta property="og:image" content="https://cdn.example.com/048414104.jpg">'
    assert _extract_og_image(html, "https://example.com") == "https://cdn.example.com/048414104.jpg"


def test_extract_og_image_jsonld() -> None:
    html = """
    <script type="application/ld+json">
    {"@type":"Product","image":"https://cdn.example.com/img.jpg","name":"Farmaco"}
    </script>
    """
    assert _extract_og_image(html, "https://example.com") == "https://cdn.example.com/img.jpg"


def test_extract_product_links_prefers_aic_in_url() -> None:
    html = """
    <a href="/products/altro-prodotto">altro</a>
    <a href="/products/oki-048414104">oki corretto</a>
    """
    links = _extract_product_links(
        html, "https://www.farmae.it/search", "048414104", ("/products/",)
    )
    assert links[0].endswith("048414104")


def test_extract_product_links_skip_other_domain() -> None:
    html = '<a href="https://altro.com/products/oki-048414104">link esterno</a>'
    links = _extract_product_links(
        html, "https://www.farmae.it/search", "048414104", ("/products/",)
    )
    assert len(links) == 0


# ---------------------------------------------------------------------------
# Test integrazione (mock HTTP)
# ---------------------------------------------------------------------------

SEARCH_HTML = """
<html><body>
  <a href="/products/oki-dolore-e-febbre-048414104">Oki 12 cpr</a>
  <a href="/products/altro-farmaco">altro</a>
</body></html>
"""

PRODUCT_HTML = """
<html>
<head>
  <meta property="og:image" content="https://www.farmae.it/cdn/shop/files/048414104.jpg">
</head>
<body>AIC 048414104 Oki dolore e febbre 12 compresse</body>
</html>
"""


def test_fetch_drug_image_success_via_pharmacy() -> None:
    """Con HTTP mockato: ricerca → scheda prodotto → og:image."""
    call_count = 0

    def fake_get(url, **kwargs):
        nonlocal call_count
        call_count += 1
        mock = MagicMock()
        mock.status_code = 200
        if "search" in url:
            mock.text = SEARCH_HTML
        else:
            mock.text = PRODUCT_HTML
        return mock

    cfg = FetcherConfig(enable_cache=False)

    with patch("drug_image_fetcher.engine.requests.Session") as MockSession:
        session_instance = MockSession.return_value
        session_instance.get.side_effect = fake_get
        session_instance.mount = MagicMock()
        session_instance.headers = {}

        with patch("drug_image_fetcher.engine._build_session", return_value=session_instance):
            result = fetch_drug_image("048414104", config=cfg)

    assert result.success is True
    assert "048414104" in result.image_url
    assert result.source_page_url is not None


def test_fetch_drug_image_not_found() -> None:
    """Nessun risultato di ricerca → not found."""
    def fake_get(url, **kwargs):
        mock = MagicMock()
        mock.status_code = 200
        mock.text = "<html><body>nessun prodotto</body></html>"
        return mock

    cfg = FetcherConfig(enable_cache=False)

    with patch("drug_image_fetcher.engine._build_session") as mock_build:
        session_instance = MagicMock()
        session_instance.get.side_effect = fake_get
        mock_build.return_value = session_instance

        result = fetch_drug_image("000000000", config=cfg)

    assert result.success is False


def test_fetch_invalid_aic() -> None:
    result = fetch_drug_image("", config=FetcherConfig(enable_cache=False))
    assert result.success is False


def test_image_fetch_result_to_dict() -> None:
    r = ImageFetchResult.found("https://example.com/img.jpg", "https://example.com")
    d = r.to_dict()
    assert d["success"] is True
    assert d["imageUrl"] == "https://example.com/img.jpg"


def test_image_fetch_result_not_found_to_dict() -> None:
    r = ImageFetchResult.not_found("test reason")
    d = r.to_dict()
    assert d["success"] is False
    assert d["imageUrl"] is None
