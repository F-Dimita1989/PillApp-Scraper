"""Modelli dati per il pipeline di recupero immagini farmaco."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class DrugInfo:
    """Metadati confezione farmaceutica usati per il matching."""

    aic: str
    name: str
    dosage: str | None = None
    pharmaceutical_form: str | None = None
    package_quantity: str | None = None
    marketing_authorization_holder: str | None = None
    active_substance: str | None = None  # principio attivo, utile se nome commerciale varia

    def normalized_aic(self) -> str:
        return self.aic.strip().replace(" ", "")


@dataclass(frozen=True, slots=True)
class CandidateImage:
    """Immagine candidata estratta da una pagina web."""

    image_url: str
    source_page_url: str
    alt_text: str = ""
    title: str = ""
    width: int | None = None
    height: int | None = None
    extraction_method: str = "img_tag"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PageMatch:
    """Risultato di scoring per una pagina e le sue immagini candidate."""

    source_page_url: str
    page_text: str
    candidates: list[CandidateImage]
    relevance_score: float = 0.0
    matched_fields: list[str] = field(default_factory=list)
    rejected_reasons: list[str] = field(default_factory=list)
    field_scores: dict[str, float] = field(default_factory=dict)


@dataclass
class ImageFetchResult:
    """Risultato finale del fetch; può indicare assenza di match affidabile."""

    success: bool
    image_url: str | None = None
    source_page_url: str | None = None
    confidence_score: float = 0.0
    matched_fields: list[str] = field(default_factory=list)
    rejected_reasons: list[str] = field(default_factory=list)
    message: str = ""

    @classmethod
    def not_found(cls, reasons: list[str] | None = None) -> ImageFetchResult:
        return cls(
            success=False,
            message="Immagine non trovata in modo affidabile",
            rejected_reasons=reasons or [],
        )

    @classmethod
    def found(
        cls,
        *,
        image_url: str,
        source_page_url: str,
        confidence_score: float,
        matched_fields: list[str],
        rejected_reasons: list[str] | None = None,
    ) -> ImageFetchResult:
        return cls(
            success=True,
            image_url=image_url,
            source_page_url=source_page_url,
            confidence_score=confidence_score,
            matched_fields=matched_fields,
            rejected_reasons=rejected_reasons or [],
            message="Immagine trovata con confidenza sufficiente",
        )

    def to_dict(self) -> dict[str, Any]:
        """Serializzazione per API REST (FastAPI / backend C#)."""
        return {
            "success": self.success,
            "imageUrl": self.image_url,
            "sourcePageUrl": self.source_page_url,
            "confidenceScore": round(self.confidence_score, 4),
            "matchedFields": list(self.matched_fields),
            "rejectedReasons": list(self.rejected_reasons),
            "message": self.message,
        }
