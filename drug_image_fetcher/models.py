"""Modelli dati PillApp drug image fetcher."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ImageFetchResult:
    """Risultato finale del fetch immagine."""

    success: bool
    image_url: str | None = None
    source_page_url: str | None = None
    message: str = ""

    @classmethod
    def found(cls, image_url: str, source_page_url: str) -> ImageFetchResult:
        return cls(
            success=True,
            image_url=image_url,
            source_page_url=source_page_url,
            message="Immagine trovata",
        )

    @classmethod
    def not_found(cls, reason: str = "") -> ImageFetchResult:
        return cls(
            success=False,
            message=reason or "Immagine non trovata",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "imageUrl": self.image_url,
            "sourcePageUrl": self.source_page_url,
            "message": self.message,
        }
