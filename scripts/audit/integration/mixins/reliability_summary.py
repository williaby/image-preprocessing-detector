"""Sample reliability summary computation mixin.

Computes per-sample reliability tiers based on confidence thresholds
across five field groups: capture, domain, language, layout, and
content_flags.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from scripts.audit.integration.constants import (
    ACTIVE_LEARNING_THRESHOLD,
    HARD_LABEL_THRESHOLD,
    RELIABILITY_FIELD_DEFS,
    SOFT_LABEL_THRESHOLD,
)


def _classify_confidence(confidence: float) -> str:
    """Classify a confidence value into a reliability tier.

    Args:
        confidence: Confidence score (0.0-1.0).

    Returns:
        Tier string: "hard_label", "soft_label", "active_learning",
        or "unreliable".
    """
    if confidence >= HARD_LABEL_THRESHOLD:
        return "hard_label"
    if confidence >= SOFT_LABEL_THRESHOLD:
        return "soft_label"
    if confidence >= ACTIVE_LEARNING_THRESHOLD:
        return "active_learning"
    return "unreliable"


class ReliabilitySummaryMixin:
    """Mixin for computing sample reliability summaries.

    Assesses five field groups and produces a reliability tier for
    each based on confidence thresholds:
      >= 0.9 -> hard_label
      >= 0.7 -> soft_label
      >= 0.5 -> active_learning
      <  0.5 -> unreliable
    """

    def compute_reliability_summary(
        self,
        data: dict[str, Any],
        *,
        field_defs: list[tuple[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Compute sample_reliability_summary for an enrichment data dict.

        Args:
            data: The enrichment data dict being built for this sample.
            field_defs: Override field definitions. Defaults to
                RELIABILITY_FIELD_DEFS.

        Returns:
            Dict with min_confidence, min_confidence_field,
            min_confidence_category, field counts, field_summary list,
            and computed_at timestamp.
        """
        defs = field_defs or RELIABILITY_FIELD_DEFS
        fields: list[dict[str, Any]] = []

        for field_name, conf_key in defs:
            confidence = data.get(conf_key, 0.0)
            if confidence is None:
                confidence = 0.0

            category = _classify_confidence(confidence)

            fields.append(
                {
                    "field": field_name,
                    "confidence": round(confidence, 4),
                    "category": category,
                    "is_soft_label": category == "soft_label",
                }
            )

        min_field = min(fields, key=lambda f: f["confidence"])

        return {
            "min_confidence": min_field["confidence"],
            "min_confidence_field": min_field["field"],
            "min_confidence_category": min_field["category"],
            "assessed_field_count": len(fields),
            "hard_field_count": sum(1 for f in fields if f["category"] == "hard_label"),
            "soft_field_count": sum(1 for f in fields if f["category"] == "soft_label"),
            "field_summary": fields,
            "computed_at": datetime.now(UTC).isoformat(),
        }
