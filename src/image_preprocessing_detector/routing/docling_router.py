"""Docling Routing Engine — Generate Docling CLI parameters from analysis.

Maps Project A document analysis results to Docling CLI parameters for
Project B handoff. Implements 6 routing rules evaluated in priority order:

1. **Text layer quality**: born-digital + quality >= 0.90 -> skip OCR
2. **Script-aware engine**: Script -> engine selection + batch sizing
3. **VLM escalation**: Multiple triggers -> VLM pipeline
4. **Table mode**: High complexity or merged cells -> accurate mode
5. **Enrichments**: Code/math presence -> enable enrichments
6. **PSM**: Delegate to PSMRecommender for Tesseract mode

The engine consumes ``DocumentMetadata`` and per-page ``PageLayoutSummary``
from schema.py and produces a ``DoclingRoutingParams`` instance ready for
CLI serialization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from image_preprocessing_detector.routing.psm_recommender import (
    PSMInput,
    PSMRecommender,
)
from image_preprocessing_detector.routing.script_router import ScriptRouter
from image_preprocessing_detector.utils import get_logger

if TYPE_CHECKING:
    from image_preprocessing_detector.schema import (
        DoclingRoutingParams,
        DocumentMetadata,
        PageLayoutSummary,
    )

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Thresholds — single source of truth for tuning
# ---------------------------------------------------------------------------
_TEXT_LAYER_QUALITY_THRESHOLD = 0.90
_DQS_LOW_THRESHOLD = 0.4
_SCRIPT_CONFIDENCE_LOW_THRESHOLD = 0.55
_WARPING_EXTREME_THRESHOLD = 0.75
_TABLE_COMPLEXITY_ACCURATE_THRESHOLD = 0.6

# CJK scripts that benefit from reduced batch size
_CJK_SCRIPTS = frozenset({"Hans", "Hant", "Jpan", "Kore", "Hani"})

# Latin/Cyrillic/Greek family that can use rapidocr
_RAPIDOCR_SCRIPTS = frozenset({"Latn", "Cyrl", "Grek"})


@dataclass(frozen=True)
class RoutingDecision:
    """Captures the routing decision with audit trail.

    Attributes:
        params (DoclingRoutingParams): Generated Docling CLI parameters.
        vlm_reasons (list[str]): Reasons for VLM escalation (empty if standard pipeline).
        rule_trace (list[str]): Ordered list of rules that modified the params.
    """

    params: DoclingRoutingParams
    vlm_reasons: list[str]
    rule_trace: list[str]


@dataclass
class _MutableParams:
    """Internal mutable state accumulated across routing rules.

    Converted to ``DoclingRoutingParams`` at the end of routing.
    """

    pipeline: str = "standard"
    vlm_model: str | None = None
    ocr_enabled: bool = True
    ocr_force: bool = False
    ocr_engine: str = "auto"
    ocr_lang: str | None = None
    psm: int | None = None
    tables_enabled: bool = True
    table_mode: str = "accurate"
    enrich_code: bool = False
    enrich_formula: bool = False
    page_batch_size: int = 4
    vlm_reasons: list[str] = field(default_factory=list)
    rule_trace: list[str] = field(default_factory=list)


class DoclingRoutingEngine:
    """Generate Docling CLI parameters from document analysis results.

    Consumes ``DocumentMetadata`` (document-level fields) and an optional
    representative ``PageLayoutSummary`` to produce a ``DoclingRoutingParams``
    instance with an audit trail of which rules fired.

    Args:
        script_router (ScriptRouter | None): ScriptRouter for engine/VLM lookups. If None,
            lazily loaded via ``get_default_router()``.
        psm_recommender (PSMRecommender | None): PSMRecommender for PSM selection. If None,
            a new default instance is created.

    Example:
        >>> from image_preprocessing_detector.routing.docling_router import (
        ...     DoclingRoutingEngine,
        ... )
        >>> engine = DoclingRoutingEngine()
        >>> decision = engine.route(doc_metadata)
        >>> decision.params.to_cli_args()
        ['--pipeline=standard', '--ocr-engine=rapidocr', ...]
    """

    def __init__(
        self,
        script_router: ScriptRouter | None = None,
        psm_recommender: PSMRecommender | None = None,
    ) -> None:
        self._script_router = script_router
        self._psm_recommender = psm_recommender or PSMRecommender()

    @property
    def script_router(self) -> ScriptRouter:
        """Lazy-load the default ScriptRouter if not injected."""
        if self._script_router is None:
            from image_preprocessing_detector.routing.script_router import (
                get_default_router,
            )

            self._script_router = get_default_router()
        return self._script_router

    def route(
        self,
        metadata: DocumentMetadata,
        page_summary: PageLayoutSummary | None = None,
    ) -> RoutingDecision:
        """Generate Docling routing params from document analysis.

        Evaluates all 6 routing rules in order, accumulating parameters.
        Unlike PSMRecommender (first-match-wins), all rules are evaluated
        because they control independent aspects of the Docling config.

        Args:
            metadata (DocumentMetadata): Document-level analysis results.
            page_summary (PageLayoutSummary | None): Representative page layout summary (typically the
                first or most complex page). If None and metadata has
                page_layout_summary entries, the first one is used.

        Returns:
            RoutingDecision: RoutingDecision with params, VLM reasons, and rule trace.
        """
        # Use first page summary if none provided
        if page_summary is None and metadata.page_layout_summary:
            page_summary = metadata.page_layout_summary[0]

        params = _MutableParams()

        # Apply all rules in order
        self._apply_text_layer_rule(metadata, params)
        self._apply_script_engine_rule(metadata, params)
        self._apply_vlm_escalation_rule(metadata, page_summary, params)
        self._apply_table_mode_rule(page_summary, params)
        self._apply_enrichment_rule(page_summary, params)
        self._apply_psm_rule(page_summary, params)

        # Convert to frozen DoclingRoutingParams
        routing_params = self._to_docling_params(params)

        decision = RoutingDecision(
            params=routing_params,
            vlm_reasons=list(params.vlm_reasons),
            rule_trace=list(params.rule_trace),
        )

        logger.info(
            "docling_routing_complete",
            pipeline=decision.params.pipeline,
            vlm_reasons=len(decision.vlm_reasons),
            rules_fired=len(decision.rule_trace),
        )

        return decision

    # ------------------------------------------------------------------
    # Rule 1: Text layer quality
    # ------------------------------------------------------------------

    def _apply_text_layer_rule(
        self,
        metadata: DocumentMetadata,
        params: _MutableParams,
    ) -> None:
        """Born-digital with high text layer quality -> skip OCR.

        Condition: ``text_layer_quality >= 0.90`` AND ``text_layer_skip_ocr``
        is True (set by upstream text-layer analysis).
        """
        if (
            metadata.text_layer_quality is not None
            and metadata.text_layer_quality >= _TEXT_LAYER_QUALITY_THRESHOLD
            and metadata.text_layer_skip_ocr
        ):
            params.ocr_enabled = False
            params.rule_trace.append("text_layer_skip_ocr")
            logger.debug(
                "rule_text_layer",
                quality=metadata.text_layer_quality,
                action="skip_ocr",
            )

    # ------------------------------------------------------------------
    # Rule 2: Script-aware engine selection
    # ------------------------------------------------------------------

    def _apply_script_engine_rule(
        self,
        metadata: DocumentMetadata,
        params: _MutableParams,
    ) -> None:
        """Map dominant script to OCR engine and batch size.

        - Latin/Cyrillic/Greek with decent quality -> rapidocr
        - CJK scripts -> reduced batch size (memory)
        - Delegates to ScriptRouter for engine config and lang hints
        """
        if metadata.script_detection is None:
            return

        dominant = metadata.script_detection.dominant_script
        config = self.script_router.get_engine_config(dominant)

        # Set engine from routing config
        engine = str(config.get("engine", "auto"))
        if engine != "auto":
            params.ocr_engine = engine

        # Language hint
        lang_hint = self.script_router.get_lang_hint(dominant)
        if lang_hint is not None:
            params.ocr_lang = lang_hint

        # CJK memory optimization
        if dominant in _CJK_SCRIPTS:
            params.page_batch_size = min(params.page_batch_size, 2)

        # Batch size from routing config
        config_batch = int(config.get("batch_size", 4))
        if config_batch < params.page_batch_size:
            params.page_batch_size = config_batch

        params.rule_trace.append(f"script_engine_{dominant}")
        logger.debug(
            "rule_script_engine",
            script=dominant,
            engine=params.ocr_engine,
            batch_size=params.page_batch_size,
        )

    # ------------------------------------------------------------------
    # Rule 3: VLM escalation
    # ------------------------------------------------------------------

    def _apply_vlm_escalation_rule(
        self,
        metadata: DocumentMetadata,
        page_summary: PageLayoutSummary | None,
        params: _MutableParams,
    ) -> None:
        """Escalate to VLM pipeline when heuristic/standard OCR is insufficient.

        Triggers:
        - Handwriting present (from page summary or handwriting assessment)
        - DQS < 0.4 (severely degraded)
        - Script confidence < 0.55
        - Complex degradation (degradation_severity == "complex")
        - Warping > 0.75 (extreme distortion)
        - Mixed orientation (multiple pages with different angles)
        - ScriptRouter VLM escalation (rare scripts, unknown scripts)
        """
        reasons: list[str] = []

        # Handwriting trigger
        if page_summary is not None and page_summary.has_handwriting:
            reasons.append("handwriting_detected")
        if (
            page_summary is not None
            and page_summary.handwriting_assessment is not None
            and page_summary.handwriting_assessment.needs_advanced_ocr
        ):
            reasons.append("handwriting_needs_advanced_ocr")

        # DQS < 0.4 trigger
        if metadata.dqs is not None:
            dqs_degradation = metadata.dqs.degradation_score
            if dqs_degradation >= (1.0 - _DQS_LOW_THRESHOLD):
                # degradation_score is 0=pristine, 1=degraded
                # So high degradation (>= 0.6) means low quality (< 0.4)
                reasons.append(f"low_dqs_degradation_{dqs_degradation:.2f}")

        # Script confidence trigger
        if (
            metadata.script_detection is not None
            and metadata.script_detection.dominant_confidence
            < _SCRIPT_CONFIDENCE_LOW_THRESHOLD
        ):
            reasons.append(
                f"low_script_confidence_{metadata.script_detection.dominant_confidence:.2f}"
            )

        # Complex degradation trigger
        if metadata.degradation_severity == "complex":
            reasons.append("complex_degradation")

        # Warping trigger
        if (
            page_summary is not None
            and page_summary.warping_score > _WARPING_EXTREME_THRESHOLD
        ):
            reasons.append(f"extreme_warping_{page_summary.warping_score:.2f}")

        # Mixed orientation trigger (check all pages)
        if self._has_mixed_orientation(metadata):
            reasons.append("mixed_orientation")

        # Script-based VLM escalation (delegate to ScriptRouter)
        if metadata.script_detection is not None:
            script_reasons = self.script_router.get_vlm_escalation_reasons(
                metadata.script_detection.dominant_script,
                metadata.script_detection.dominant_confidence,
            )
            reasons.extend(script_reasons)

        if reasons:
            params.pipeline = "vlm"
            # vlm_model stays None here intentionally: when pipeline="vlm" and no explicit
            # model is set, Docling uses its built-in default VLM (SmolDocling or configured
            # default). To specify a model, set DoclingRoutingParams.vlm_model explicitly
            # before calling to_cli_args(). See Bug 1.3 in DOCLING_INTEGRATION_GAP_REPORT.md.
            params.vlm_reasons.extend(reasons)
            params.rule_trace.append("vlm_escalation")
            logger.debug(
                "rule_vlm_escalation",
                reason_count=len(reasons),
                reasons=reasons,
            )

    def _has_mixed_orientation(self, metadata: DocumentMetadata) -> bool:
        """Check if document has pages with different orientations."""
        if len(metadata.page_layout_summary) < 2:
            return False

        angles = {
            ps.orientation_angle
            for ps in metadata.page_layout_summary
            if ps.orientation_confidence > 0.5
        }
        return len(angles) > 1

    # ------------------------------------------------------------------
    # Rule 4: Table mode
    # ------------------------------------------------------------------

    def _apply_table_mode_rule(
        self,
        page_summary: PageLayoutSummary | None,
        params: _MutableParams,
    ) -> None:
        """Select table extraction mode based on complexity.

        - complexity_score >= 0.6 -> accurate mode
        - Merged cells detected -> accurate mode
        - Otherwise -> fast mode (default is already accurate)
        """
        if page_summary is None or not page_summary.has_tables:
            return

        tc = page_summary.table_complexity
        if tc is None:
            return

        if (
            tc.complexity_score >= _TABLE_COMPLEXITY_ACCURATE_THRESHOLD
            or tc.has_merged_cells
        ):
            params.table_mode = "accurate"
            params.rule_trace.append("table_mode_accurate")
            logger.debug(
                "rule_table_mode",
                complexity=tc.complexity_score,
                merged_cells=tc.has_merged_cells,
                mode="accurate",
            )
        else:
            params.table_mode = "fast"
            params.rule_trace.append("table_mode_fast")
            logger.debug("rule_table_mode", mode="fast")

    # ------------------------------------------------------------------
    # Rule 5: Enrichments
    # ------------------------------------------------------------------

    def _apply_enrichment_rule(
        self,
        page_summary: PageLayoutSummary | None,
        params: _MutableParams,
    ) -> None:
        """Enable Docling enrichment plugins for code and math.

        - ``has_code`` -> ``enrich_code=True``
        - ``has_dense_math`` -> ``enrich_formula=True``
        """
        if page_summary is None:
            return

        if page_summary.has_code:
            params.enrich_code = True
            params.rule_trace.append("enrich_code")
            logger.debug("rule_enrichment", type="code")

        if page_summary.has_dense_math:
            params.enrich_formula = True
            params.rule_trace.append("enrich_formula")
            logger.debug("rule_enrichment", type="formula")

    # ------------------------------------------------------------------
    # Rule 6: PSM recommendation
    # ------------------------------------------------------------------

    def _apply_psm_rule(
        self,
        page_summary: PageLayoutSummary | None,
        params: _MutableParams,
    ) -> None:
        """Delegate PSM selection to PSMRecommender."""
        if page_summary is None:
            return

        psm_input = PSMInput(
            layout_type=page_summary.layout_type,
            has_tables=page_summary.has_tables,
            is_sparse=page_summary.complexity_score < 0.2,
            has_handwriting=page_summary.has_handwriting,
            orientation_confidence=page_summary.orientation_confidence,
            element_count=self._estimate_element_count(page_summary),
        )

        rec = self._psm_recommender.recommend(psm_input)
        params.psm = rec.psm
        params.rule_trace.append(f"psm_{rec.psm}")
        logger.debug(
            "rule_psm",
            psm=rec.psm,
            reason=rec.reason,
            confidence=rec.confidence,
        )

    @staticmethod
    def _estimate_element_count(page_summary: PageLayoutSummary) -> int:
        """Estimate element count from boolean flags.

        PageLayoutSummary has boolean flags but not an explicit element
        count. Approximate by counting detected features.
        """
        count = 0
        if page_summary.has_tables:
            count += 1
        if page_summary.has_figures:
            count += 1
        if page_summary.has_code:
            count += 1
        if page_summary.has_dense_math:
            count += 1
        if page_summary.has_handwriting:
            count += 1
        if page_summary.has_list_items:
            count += 1
        if page_summary.has_headers_footers:
            count += 2
        return count

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _to_docling_params(params: _MutableParams) -> DoclingRoutingParams:
        """Convert mutable state to frozen DoclingRoutingParams."""
        from image_preprocessing_detector.schema import DoclingRoutingParams

        return DoclingRoutingParams(
            pipeline=params.pipeline,  # type: ignore[arg-type]
            vlm_model=params.vlm_model,
            ocr_enabled=params.ocr_enabled,
            ocr_force=params.ocr_force,
            ocr_engine=params.ocr_engine,
            ocr_lang=params.ocr_lang,
            psm=params.psm,
            tables_enabled=params.tables_enabled,
            table_mode=params.table_mode,  # type: ignore[arg-type]
            enrich_code=params.enrich_code,
            enrich_formula=params.enrich_formula,
            page_batch_size=params.page_batch_size,
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_default_engine: DoclingRoutingEngine | None = None


def get_default_engine() -> DoclingRoutingEngine:
    """Return (and lazily create) the module-level DoclingRoutingEngine singleton."""
    global _default_engine
    if _default_engine is None:
        _default_engine = DoclingRoutingEngine()
    return _default_engine


def reset_default_engine() -> None:
    """Reset the module-level singleton. Useful for testing."""
    global _default_engine
    _default_engine = None


def route_document(
    metadata: DocumentMetadata,
    page_summary: PageLayoutSummary | None = None,
) -> RoutingDecision:
    """Convenience function — route a document using the default engine.

    Args:
        metadata (DocumentMetadata): Document-level analysis results.
        page_summary (PageLayoutSummary | None): Optional representative page layout summary.

    Returns:
        RoutingDecision: RoutingDecision with Docling params, VLM reasons, and audit trail.
    """
    return get_default_engine().route(metadata, page_summary)


__all__ = [
    "DoclingRoutingEngine",
    "RoutingDecision",
    "get_default_engine",
    "reset_default_engine",
    "route_document",
]
