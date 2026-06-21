"""Test parser HTML."""

from drug_image_fetcher.fetch.page_parser import extract_image_candidates, extract_page_text

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta property="og:image" content="https://cdn.example.com/og-tachipirina.jpg" />
</head>
<body>
  <img src="https://cdn.example.com/logo.png" alt="logo" width="40" height="40" />
  <img src="https://cdn.example.com/favicon.ico" alt="icon" />
  <img class="product-image" src="https://cdn.example.com/prodotto.jpg"
       alt="Tachipirina 500 mg" width="320" height="320" />
  <script type="application/ld+json">
  {
    "@type": "Product",
    "name": "Tachipirina",
    "image": "https://cdn.example.com/jsonld.jpg"
  }
  </script>
</body>
</html>
"""


def test_extract_page_text_strips_scripts() -> None:
    text = extract_page_text(SAMPLE_HTML)
    assert "Product" not in text or "Tachipirina" in text


def test_extract_image_candidates_filters_decorative() -> None:
    candidates = extract_image_candidates(SAMPLE_HTML, "https://example.com/p")
    urls = {c.image_url for c in candidates}

    assert "https://cdn.example.com/logo.png" not in urls
    assert "https://cdn.example.com/favicon.ico" not in urls
    assert "https://cdn.example.com/og-tachipirina.jpg" in urls
    assert "https://cdn.example.com/prodotto.jpg" in urls
    assert "https://cdn.example.com/jsonld.jpg" in urls
