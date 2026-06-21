"""Estrazione immagini candidate da pagine HTML."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from drug_image_fetcher.logging_config import logger
from drug_image_fetcher.models import CandidateImage

_SKIP_URL_PATTERNS = re.compile(
    r"(favicon|sprite|logo|banner|icon|avatar|placeholder|pixel|tracking|"
    r"badge|social|footer|header-nav|1x1|spacer|blank\.gif|data:image|"
    r"product-menu|cosmetici|menu-|/menu/|promo-|sidebar|nav-)",
    re.IGNORECASE,
)

_PRODUCT_HINTS = re.compile(
    r"(product|prodotto|farmaco|medicin|confezione|package|packaging|"
    r"drug|item-image|articolo|thumbnail-large|img-prod)",
    re.IGNORECASE,
)


def extract_page_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


def extract_image_candidates(
    html: str,
    page_url: str,
    *,
    min_width: int = 120,
    min_height: int = 120,
) -> list[CandidateImage]:
    soup = BeautifulSoup(html, "html.parser")
    candidates: list[CandidateImage] = []
    seen_urls: set[str] = set()

    def add_candidate(
        image_url: str,
        *,
        alt: str = "",
        title: str = "",
        width: int | None = None,
        height: int | None = None,
        method: str = "img_tag",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        absolute = _resolve_url(page_url, image_url)
        if not absolute or absolute in seen_urls:
            return
        if _should_skip_url(absolute):
            return
        if width is not None and width < min_width and height is not None and height < min_height:
            return

        seen_urls.add(absolute)
        candidates.append(
            CandidateImage(
                image_url=absolute,
                source_page_url=page_url,
                alt_text=alt,
                title=title,
                width=width,
                height=height,
                extraction_method=method,
                metadata=metadata or {},
            )
        )

    # og:image / twitter:image
    for meta in soup.find_all("meta"):
        prop = (meta.get("property") or meta.get("name") or "").lower()
        if prop in {"og:image", "og:image:url", "twitter:image", "twitter:image:src"}:
            content = meta.get("content", "").strip()
            if content:
                add_candidate(content, method="meta_og_image")

    # JSON-LD Product
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        _extract_jsonld_images(data, page_url, add_candidate)

    # img tags
    for img in soup.find_all("img"):
        if not isinstance(img, Tag):
            continue
        src = _best_img_src(img)
        if not src:
            continue

        width = _parse_dimension(img.get("width"))
        height = _parse_dimension(img.get("height"))
        classes = " ".join(img.get("class", []))
        img_id = img.get("id", "")
        hint_score = bool(_PRODUCT_HINTS.search(f"{classes} {img_id} {src}"))

        if not hint_score and _looks_like_decorative(img, src):
            continue

        add_candidate(
            src,
            alt=img.get("alt", ""),
            title=img.get("title", ""),
            width=width,
            height=height,
            method="img_tag_product" if hint_score else "img_tag",
            metadata={"product_hint": hint_score},
        )

    logger.debug(
        "Estratte %d immagini candidate da %s",
        len(candidates),
        page_url,
    )
    return candidates


def _extract_jsonld_images(
    data: Any,
    page_url: str,
    add_fn: Any,
) -> None:
    items = data if isinstance(data, list) else [data]
    for item in items:
        if not isinstance(item, dict):
            continue
        item_type = item.get("@type", "")
        types = item_type if isinstance(item_type, list) else [item_type]
        if not any(t in {"Product", "Drug", "MedicalEntity"} for t in types):
            continue

        image = item.get("image")
        if isinstance(image, str):
            add_fn(image, method="json_ld")
        elif isinstance(image, list):
            for entry in image:
                if isinstance(entry, str):
                    add_fn(entry, method="json_ld")
                elif isinstance(entry, dict) and entry.get("url"):
                    add_fn(entry["url"], method="json_ld")


def _best_img_src(img: Tag) -> str | None:
    for attr in ("src", "data-src", "data-lazy-src", "data-original"):
        value = img.get(attr)
        if value and not value.startswith("data:"):
            return value.strip()
    srcset = img.get("srcset")
    if srcset:
        parts = [p.strip().split()[0] for p in srcset.split(",") if p.strip()]
        if parts:
            return parts[-1]
    return None


def _parse_dimension(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value).replace("px", "").strip())
    except ValueError:
        return None


def _looks_like_decorative(img: Tag, src: str) -> bool:
    alt = (img.get("alt") or "").lower()
    if any(word in alt for word in ("logo", "icon", "banner", "menu")):
        return True
    width = _parse_dimension(img.get("width"))
    height = _parse_dimension(img.get("height"))
    if width is not None and height is not None and width < 80 and height < 80:
        return True
    return bool(_SKIP_URL_PATTERNS.search(src))


def _should_skip_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return True
    return bool(_SKIP_URL_PATTERNS.search(url))


def _resolve_url(base: str, relative: str) -> str | None:
    if not relative:
        return None
    return urljoin(base, relative)
