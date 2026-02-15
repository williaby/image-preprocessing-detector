"""Per-field confidence and source provenance tracking mixin.

Provides methods to track confidence scores and detection method
provenance for each enrichment field, enabling downstream training
to weight samples by label reliability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ResolvedField:
    """Result of resolving a field value from a priority chain.

    Attributes:
        value: The resolved field value.
        confidence: Confidence score (0.0-1.0).
        source: Detection method / source name.
        source_rank: Position in priority chain (1 = highest).
    """

    value: Any
    confidence: float
    source: str
    source_rank: int = 1


@dataclass
class FieldConfidenceRecord:
    """Accumulated confidence records for a single sample.

    Attributes:
        fields: Mapping of field_name to ResolvedField.
    """

    fields: dict[str, ResolvedField] = field(default_factory=dict)

    def track(self, field_name: str, resolved: ResolvedField) -> None:
        """Record a resolved field value with its confidence.

        Args:
            field_name: Name of the enrichment field.
            resolved: The resolved field with value, confidence, source.
        """
        self.fields[field_name] = resolved

    def get_confidence(self, field_name: str) -> float:
        """Get the confidence for a tracked field.

        Args:
            field_name: Name of the enrichment field.

        Returns:
            Confidence score, or 0.0 if field not tracked.
        """
        rec = self.fields.get(field_name)
        return rec.confidence if rec else 0.0

    def get_source(self, field_name: str) -> str:
        """Get the detection method for a tracked field.

        Args:
            field_name: Name of the enrichment field.

        Returns:
            Source/detection method string, or "none" if not tracked.
        """
        rec = self.fields.get(field_name)
        return rec.source if rec else "none"

    def get_min_confidence(self) -> tuple[float, str]:
        """Get the minimum confidence across all tracked fields.

        Returns:
            Tuple of (min_confidence, field_name). Returns (0.0, "none")
            if no fields are tracked.
        """
        if not self.fields:
            return (0.0, "none")
        min_field = min(self.fields.items(), key=lambda kv: kv[1].confidence)
        return (min_field[1].confidence, min_field[0])

    def to_dict(self) -> dict[str, dict[str, Any]]:
        """Export all field confidence records as a dict.

        Returns:
            Dict mapping field_name to {value, confidence, source, source_rank}.
        """
        return {
            name: {
                "value": rec.value,
                "confidence": round(rec.confidence, 4),
                "source": rec.source,
                "source_rank": rec.source_rank,
            }
            for name, rec in self.fields.items()
        }


class ConfidenceTrackingMixin:
    """Mixin for tracking per-field confidence and source provenance.

    Manages a FieldConfidenceRecord per sample during integration,
    enabling export of confidence metadata alongside field values.
    """

    def create_confidence_record(self) -> FieldConfidenceRecord:
        """Create a new empty confidence record for a sample.

        Returns:
            Fresh FieldConfidenceRecord instance.
        """
        return FieldConfidenceRecord()

    def track_field(
        self,
        record: FieldConfidenceRecord,
        field_name: str,
        value: Any,
        confidence: float,
        source: str,
        source_rank: int = 1,
    ) -> None:
        """Track a resolved field value with confidence metadata.

        Args:
            record: The confidence record for this sample.
            field_name: Name of the enrichment field.
            value: The resolved field value.
            confidence: Confidence score (0.0-1.0).
            source: Detection method / source name.
            source_rank: Position in priority chain (1 = highest).
        """
        record.track(
            field_name,
            ResolvedField(
                value=value,
                confidence=confidence,
                source=source,
                source_rank=source_rank,
            ),
        )

    def get_confidence_summary(
        self,
        record: FieldConfidenceRecord,
    ) -> dict[str, Any]:
        """Get a summary of confidence tracking for a sample.

        Args:
            record: The confidence record for this sample.

        Returns:
            Dict with min_confidence, min_confidence_field,
            tracked_field_count, and per-field details.
        """
        min_conf, min_field = record.get_min_confidence()
        return {
            "min_confidence": round(min_conf, 4),
            "min_confidence_field": min_field,
            "tracked_field_count": len(record.fields),
            "fields": record.to_dict(),
        }
