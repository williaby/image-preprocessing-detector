"""Mixin classes for integration script composition.

Each mixin provides a focused set of methods that can be composed
incrementally into integration scripts:

- KIMitigationMixin: Known issue mitigations (KI-001 through KI-009)
- ConfidenceTrackingMixin: Per-field confidence and source provenance
- ContentFlagsMixin: Content flag derivation with VLM overrides
- ReliabilitySummaryMixin: Sample reliability tier computation
"""

from __future__ import annotations

from scripts.audit.integration.mixins.confidence_tracking import (
    ConfidenceTrackingMixin,
)
from scripts.audit.integration.mixins.content_flags import ContentFlagsMixin
from scripts.audit.integration.mixins.ki_mitigation import KIMitigationMixin
from scripts.audit.integration.mixins.reliability_summary import (
    ReliabilitySummaryMixin,
)

__all__ = [
    "ConfidenceTrackingMixin",
    "ContentFlagsMixin",
    "KIMitigationMixin",
    "ReliabilitySummaryMixin",
]
