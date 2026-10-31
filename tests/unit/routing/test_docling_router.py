"""Unit tests for DoclingRoutingEngine.

Tests cover:
- Each of the 6 routing rules individually
- Rule interactions (all rules evaluated, not first-match-wins)
- VLM escalation triggers (6 distinct triggers)
- Edge cases (no page summary, no script detection, defaults)
- Singleton factory functions
- Audit trail (rule_trace, vlm_reasons)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from image_preprocessing_detector.routing.docling_router import (
    DoclingRoutingEngine,
    RoutingDecision,
    get_default_engine,
    reset_default_engine,
    route_document,
)
from image_preprocessing_detector.routing.psm_recommender import PSMRecommender
from image_preprocessing_detector.schema import (
    DoclingRoutingParams,
    DocumentMetadata,
    DocumentScriptDetection,
    DQSMetadata,
    HandwritingAssessment,
    LayoutType,
    PageLayoutSummary,
    PageMetadata,
    ProcessingVersion,
    TableComplexity,
)

# =============================================================================
# Test helpers - minimal valid fixtures
# =============================================================================


def _make_page_metadata(page_index: int = 0) -> PageMetadata:
    """Create minimal valid PageMetadata."""
    return PageMetadata(
        page_index=page_index,
        width_px=2550,
        height_px=3300,
        dpi_input=300,
        dpi_effective=300,
    )


def _make_version() -> ProcessingVersion:
    """Create minimal valid ProcessingVersion."""
    return ProcessingVersion(pipeline_version="1.0.0-test")


def _make_page_summary(
    page_number: int = 1,
    layout_type: LayoutType = LayoutType.SINGLE_COLUMN,
    complexity_score: float = 0.5,
    **kwargs: object,
) -> PageLayoutSummary:
    """Create a PageLayoutSummary with sensible defaults."""
    return PageLayoutSummary(
        page_number=page_number,
        layout_type=layout_type,
        complexity_score=complexity_score,
        **kwargs,
    )


def _make_metadata(**kwargs: object) -> DocumentMetadata:
    """Create minimal valid DocumentMetadata with optional overrides."""
    defaults: dict[str, object] = {
        "document_id": "test-doc-001",
        "file_name": "test.pdf",
        "source_mime": "application/pdf",
        "num_pages": 1,
        "processing_version": _make_version(),
        "pages": [_make_page_metadata()],
    }
    defaults.update(kwargs)
    return DocumentMetadata(**defaults)  # type: ignore[arg-type]


def _make_script_detection(
    dominant_script: str = "Latn",
    dominant_confidence: float = 0.95,
    **kwargs: object,
) -> DocumentScriptDetection:
    """Create a DocumentScriptDetection with defaults."""
    return DocumentScriptDetection(
        dominant_script=dominant_script,
        dominant_confidence=dominant_confidence,
        **kwargs,
    )


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_script_router() -> MagicMock:
    """Create a mock ScriptRouter with sensible defaults."""
    router = MagicMock()
    router.get_engine_config.return_value = {
        "engine": "auto",
        "batch_size": 4,
    }
    router.get_lang_hint.return_value = None
    router.should_escalate_to_vlm.return_value = False
    router.get_vlm_escalation_reasons.return_value = []
    return router


@pytest.fixture
def engine(mock_script_router: MagicMock) -> DoclingRoutingEngine:
    """Return a DoclingRoutingEngine with mocked dependencies."""
    return DoclingRoutingEngine(
        script_router=mock_script_router,
        psm_recommender=PSMRecommender(),
    )


# =============================================================================
# Rule 1: Text layer quality -> skip OCR
# =============================================================================


class TestTextLayerRule:
    """Rule 1: born-digital + quality >= 0.90 -> ocr_enabled=False."""

    def test_high_quality_text_layer_skips_ocr(
        self, engine: DoclingRoutingEngine
    ) -> None:
        meta = _make_metadata(
            text_layer_quality=0.95,
            text_layer_skip_ocr=True,
        )
        decision = engine.route(meta)
        assert decision.params.ocr_enabled is False
        assert "text_layer_skip_ocr" in decision.rule_trace

    def test_high_quality_without_skip_flag_keeps_ocr(
        self, engine: DoclingRoutingEngine
    ) -> None:
        """quality >= 0.90 but text_layer_skip_ocr=False -> OCR stays on."""
        meta = _make_metadata(
            text_layer_quality=0.95,
            text_layer_skip_ocr=False,
        )
        decision = engine.route(meta)
        assert decision.params.ocr_enabled is True
        assert "text_layer_skip_ocr" not in decision.rule_trace

    def test_low_quality_keeps_ocr(self, engine: DoclingRoutingEngine) -> None:
        meta = _make_metadata(
            text_layer_quality=0.5,
            text_layer_skip_ocr=True,
        )
        decision = engine.route(meta)
        assert decision.params.ocr_enabled is True

    def test_boundary_at_threshold(self, engine: DoclingRoutingEngine) -> None:
        """Exactly 0.90 should trigger skip."""
        meta = _make_metadata(
            text_layer_quality=0.90,
            text_layer_skip_ocr=True,
        )
        decision = engine.route(meta)
        assert decision.params.ocr_enabled is False

    def test_no_text_layer_quality_keeps_ocr(
        self, engine: DoclingRoutingEngine
    ) -> None:
        meta = _make_metadata(text_layer_quality=None)
        decision = engine.route(meta)
        assert decision.params.ocr_enabled is True


# =============================================================================
# Rule 2: Script-aware engine selection
# =============================================================================


class TestScriptEngineRule:
    """Rule 2: Script -> engine selection + batch sizing."""

    def test_latin_script_sets_rapidocr(
        self,
        engine: DoclingRoutingEngine,
        mock_script_router: MagicMock,
    ) -> None:
        mock_script_router.get_engine_config.return_value = {
            "engine": "rapidocr",
            "batch_size": 4,
        }
        meta = _make_metadata(script_detection=_make_script_detection("Latn"))
        decision = engine.route(meta)
        assert decision.params.ocr_engine == "rapidocr"
        assert any("script_engine_Latn" in r for r in decision.rule_trace)

    def test_cjk_script_reduces_batch_size(
        self,
        engine: DoclingRoutingEngine,
        mock_script_router: MagicMock,
    ) -> None:
        mock_script_router.get_engine_config.return_value = {
            "engine": "paddleocr",
            "batch_size": 4,
        }
        meta = _make_metadata(script_detection=_make_script_detection("Hans"))
        decision = engine.route(meta)
        assert decision.params.page_batch_size <= 2

    def test_lang_hint_propagated(
        self,
        engine: DoclingRoutingEngine,
        mock_script_router: MagicMock,
    ) -> None:
        mock_script_router.get_engine_config.return_value = {
            "engine": "paddleocr",
            "batch_size": 4,
        }
        mock_script_router.get_lang_hint.return_value = "ch"
        meta = _make_metadata(script_detection=_make_script_detection("Hans"))
        decision = engine.route(meta)
        assert decision.params.ocr_lang == "ch"

    def test_no_script_detection_skips_rule(self, engine: DoclingRoutingEngine) -> None:
        meta = _make_metadata(script_detection=None)
        decision = engine.route(meta)
        assert decision.params.ocr_engine == "auto"

    def test_auto_engine_not_overridden(
        self,
        engine: DoclingRoutingEngine,
        mock_script_router: MagicMock,
    ) -> None:
        """When script router returns 'auto', engine stays default."""
        mock_script_router.get_engine_config.return_value = {
            "engine": "auto",
            "batch_size": 4,
        }
        meta = _make_metadata(script_detection=_make_script_detection("Latn"))
        decision = engine.route(meta)
        assert decision.params.ocr_engine == "auto"

    def test_config_batch_size_smaller_wins(
        self,
        engine: DoclingRoutingEngine,
        mock_script_router: MagicMock,
    ) -> None:
        """If script router says batch_size=1, use that even if not CJK."""
        mock_script_router.get_engine_config.return_value = {
            "engine": "auto",
            "batch_size": 1,
        }
        meta = _make_metadata(script_detection=_make_script_detection("Arab"))
        decision = engine.route(meta)
        assert decision.params.page_batch_size == 1


# =============================================================================
# Rule 3: VLM escalation
# =============================================================================


class TestVLMEscalationRule:
    """Rule 3: Multiple triggers -> VLM pipeline."""

    def test_handwriting_triggers_vlm(self, engine: DoclingRoutingEngine) -> None:
        meta = _make_metadata()
        ps = _make_page_summary(has_handwriting=True)
        meta = _make_metadata(page_layout_summary=[ps])
        decision = engine.route(meta, ps)
        assert decision.params.pipeline == "vlm"
        assert "handwriting_detected" in decision.vlm_reasons

    def test_low_dqs_triggers_vlm(self, engine: DoclingRoutingEngine) -> None:
        """DQS degradation_score >= 0.6 means quality < 0.4 -> VLM."""
        meta = _make_metadata(
            dqs=DQSMetadata(
                degradation_score=0.7,
                structural_complexity_score=0.3,
            )
        )
        decision = engine.route(meta)
        assert decision.params.pipeline == "vlm"
        assert any("low_dqs" in r for r in decision.vlm_reasons)

    def test_low_script_confidence_triggers_vlm(
        self,
        engine: DoclingRoutingEngine,
        mock_script_router: MagicMock,
    ) -> None:
        meta = _make_metadata(
            script_detection=_make_script_detection("Latn", dominant_confidence=0.3),
        )
        decision = engine.route(meta)
        assert decision.params.pipeline == "vlm"
        assert any("low_script_confidence" in r for r in decision.vlm_reasons)

    def test_complex_degradation_triggers_vlm(
        self, engine: DoclingRoutingEngine
    ) -> None:
        meta = _make_metadata(degradation_severity="complex")
        decision = engine.route(meta)
        assert decision.params.pipeline == "vlm"
        assert "complex_degradation" in decision.vlm_reasons

    def test_extreme_warping_triggers_vlm(self, engine: DoclingRoutingEngine) -> None:
        ps = _make_page_summary(warping_score=0.85)
        meta = _make_metadata(page_layout_summary=[ps])
        decision = engine.route(meta, ps)
        assert decision.params.pipeline == "vlm"
        assert any("extreme_warping" in r for r in decision.vlm_reasons)

    def test_mixed_orientation_triggers_vlm(self, engine: DoclingRoutingEngine) -> None:
        ps1 = _make_page_summary(page_number=1, orientation_angle=0)
        ps2 = _make_page_summary(page_number=2, orientation_angle=90)
        meta = _make_metadata(
            num_pages=2,
            pages=[_make_page_metadata(0), _make_page_metadata(1)],
            page_layout_summary=[ps1, ps2],
        )
        decision = engine.route(meta, ps1)
        assert decision.params.pipeline == "vlm"
        assert "mixed_orientation" in decision.vlm_reasons

    def test_script_router_vlm_escalation(
        self,
        engine: DoclingRoutingEngine,
        mock_script_router: MagicMock,
    ) -> None:
        """ScriptRouter-based VLM escalation reasons are included."""
        mock_script_router.get_vlm_escalation_reasons.return_value = [
            "script_Tibt_always_escalate"
        ]
        meta = _make_metadata(
            script_detection=_make_script_detection("Tibt", dominant_confidence=0.9),
        )
        decision = engine.route(meta)
        assert decision.params.pipeline == "vlm"
        assert "script_Tibt_always_escalate" in decision.vlm_reasons

    def test_no_vlm_triggers_standard_pipeline(
        self, engine: DoclingRoutingEngine
    ) -> None:
        """No VLM triggers -> standard pipeline."""
        meta = _make_metadata()
        ps = _make_page_summary()
        decision = engine.route(meta, ps)
        assert decision.params.pipeline == "standard"
        assert decision.vlm_reasons == []

    def test_multiple_vlm_reasons_accumulated(
        self,
        engine: DoclingRoutingEngine,
        mock_script_router: MagicMock,
    ) -> None:
        """Multiple VLM triggers should all appear in reasons."""
        mock_script_router.get_vlm_escalation_reasons.return_value = ["unknown_script"]
        ps = _make_page_summary(has_handwriting=True, warping_score=0.8)
        meta = _make_metadata(
            degradation_severity="complex",
            script_detection=_make_script_detection("Zzzz", dominant_confidence=0.2),
            page_layout_summary=[ps],
        )
        decision = engine.route(meta, ps)
        assert decision.params.pipeline == "vlm"
        assert len(decision.vlm_reasons) >= 4

    def test_warping_below_threshold_no_vlm(self, engine: DoclingRoutingEngine) -> None:
        ps = _make_page_summary(warping_score=0.5)
        meta = _make_metadata(page_layout_summary=[ps])
        decision = engine.route(meta, ps)
        assert "vlm_escalation" not in decision.rule_trace

    def test_handwriting_assessment_advanced_ocr(
        self, engine: DoclingRoutingEngine
    ) -> None:
        """HandwritingAssessment.needs_advanced_ocr triggers VLM."""
        hw = HandwritingAssessment()
        # Set fields to trigger needs_advanced_ocr
        hw_mock = MagicMock(spec=HandwritingAssessment)
        hw_mock.needs_advanced_ocr = True
        ps = _make_page_summary(
            has_handwriting=False,
            handwriting_assessment=hw_mock,
        )
        meta = _make_metadata(page_layout_summary=[ps])
        decision = engine.route(meta, ps)
        assert "handwriting_needs_advanced_ocr" in decision.vlm_reasons

    def test_mixed_orientation_low_confidence_ignored(
        self, engine: DoclingRoutingEngine
    ) -> None:
        """Pages with low orientation confidence don't count for mixed check."""
        ps1 = _make_page_summary(
            page_number=1,
            orientation_angle=0,
            orientation_confidence=0.3,
        )
        ps2 = _make_page_summary(
            page_number=2,
            orientation_angle=90,
            orientation_confidence=0.3,
        )
        meta = _make_metadata(
            num_pages=2,
            pages=[_make_page_metadata(0), _make_page_metadata(1)],
            page_layout_summary=[ps1, ps2],
        )
        decision = engine.route(meta, ps1)
        assert "mixed_orientation" not in decision.vlm_reasons


# =============================================================================
# Rule 4: Table mode
# =============================================================================


class TestTableModeRule:
    """Rule 4: High complexity or merged cells -> accurate mode."""

    def test_high_complexity_accurate_mode(self, engine: DoclingRoutingEngine) -> None:
        tc = TableComplexity(complexity_score=0.8, has_merged_cells=False)
        ps = _make_page_summary(has_tables=True, table_complexity=tc)
        meta = _make_metadata(page_layout_summary=[ps])
        decision = engine.route(meta, ps)
        assert decision.params.table_mode == "accurate"
        assert "table_mode_accurate" in decision.rule_trace

    def test_merged_cells_accurate_mode(self, engine: DoclingRoutingEngine) -> None:
        tc = TableComplexity(complexity_score=0.3, has_merged_cells=True)
        ps = _make_page_summary(has_tables=True, table_complexity=tc)
        meta = _make_metadata(page_layout_summary=[ps])
        decision = engine.route(meta, ps)
        assert decision.params.table_mode == "accurate"

    def test_simple_table_fast_mode(self, engine: DoclingRoutingEngine) -> None:
        tc = TableComplexity(complexity_score=0.3, has_merged_cells=False)
        ps = _make_page_summary(has_tables=True, table_complexity=tc)
        meta = _make_metadata(page_layout_summary=[ps])
        decision = engine.route(meta, ps)
        assert decision.params.table_mode == "fast"
        assert "table_mode_fast" in decision.rule_trace

    def test_no_tables_no_table_rule(self, engine: DoclingRoutingEngine) -> None:
        ps = _make_page_summary(has_tables=False)
        meta = _make_metadata(page_layout_summary=[ps])
        decision = engine.route(meta, ps)
        assert "table_mode_accurate" not in decision.rule_trace
        assert "table_mode_fast" not in decision.rule_trace

    def test_tables_without_complexity_no_change(
        self, engine: DoclingRoutingEngine
    ) -> None:
        """has_tables=True but table_complexity=None -> no rule fires."""
        ps = _make_page_summary(has_tables=True, table_complexity=None)
        meta = _make_metadata(page_layout_summary=[ps])
        decision = engine.route(meta, ps)
        assert "table_mode_accurate" not in decision.rule_trace
        assert "table_mode_fast" not in decision.rule_trace

    def test_boundary_at_threshold(self, engine: DoclingRoutingEngine) -> None:
        """complexity_score == 0.6 should trigger accurate mode."""
        tc = TableComplexity(complexity_score=0.6, has_merged_cells=False)
        ps = _make_page_summary(has_tables=True, table_complexity=tc)
        meta = _make_metadata(page_layout_summary=[ps])
        decision = engine.route(meta, ps)
        assert decision.params.table_mode == "accurate"


# =============================================================================
# Rule 5: Enrichments
# =============================================================================


class TestEnrichmentRule:
    """Rule 5: Code/math presence -> enable enrichments."""

    def test_code_enables_enrich_code(self, engine: DoclingRoutingEngine) -> None:
        ps = _make_page_summary(has_code=True)
        meta = _make_metadata(page_layout_summary=[ps])
        decision = engine.route(meta, ps)
        assert decision.params.enrich_code is True
        assert "enrich_code" in decision.rule_trace

    def test_math_enables_enrich_formula(self, engine: DoclingRoutingEngine) -> None:
        ps = _make_page_summary(has_dense_math=True)
        meta = _make_metadata(page_layout_summary=[ps])
        decision = engine.route(meta, ps)
        assert decision.params.enrich_formula is True
        assert "enrich_formula" in decision.rule_trace

    def test_both_code_and_math(self, engine: DoclingRoutingEngine) -> None:
        ps = _make_page_summary(has_code=True, has_dense_math=True)
        meta = _make_metadata(page_layout_summary=[ps])
        decision = engine.route(meta, ps)
        assert decision.params.enrich_code is True
        assert decision.params.enrich_formula is True

    def test_no_code_no_math_defaults(self, engine: DoclingRoutingEngine) -> None:
        ps = _make_page_summary()
        meta = _make_metadata(page_layout_summary=[ps])
        decision = engine.route(meta, ps)
        assert decision.params.enrich_code is False
        assert decision.params.enrich_formula is False


# =============================================================================
# Rule 6: PSM recommendation
# =============================================================================


class TestPSMRule:
    """Rule 6: Delegate to PSMRecommender."""

    def test_single_column_gets_psm_6(self, engine: DoclingRoutingEngine) -> None:
        ps = _make_page_summary(layout_type=LayoutType.SINGLE_COLUMN)
        meta = _make_metadata(page_layout_summary=[ps])
        decision = engine.route(meta, ps)
        assert decision.params.psm == 6
        assert "psm_6" in decision.rule_trace

    def test_multi_column_gets_psm_3(self, engine: DoclingRoutingEngine) -> None:
        ps = _make_page_summary(layout_type=LayoutType.MULTI_COLUMN)
        meta = _make_metadata(page_layout_summary=[ps])
        decision = engine.route(meta, ps)
        assert decision.params.psm == 3

    def test_tables_get_psm_6(self, engine: DoclingRoutingEngine) -> None:
        ps = _make_page_summary(has_tables=True)
        meta = _make_metadata(page_layout_summary=[ps])
        decision = engine.route(meta, ps)
        assert decision.params.psm == 6

    def test_no_page_summary_no_psm(self, engine: DoclingRoutingEngine) -> None:
        meta = _make_metadata()
        decision = engine.route(meta)
        assert decision.params.psm is None


# =============================================================================
# Integration: All rules together
# =============================================================================


class TestRuleInteraction:
    """All 6 rules are evaluated, not first-match-wins."""

    def test_all_rules_fire_together(
        self,
        engine: DoclingRoutingEngine,
        mock_script_router: MagicMock,
    ) -> None:
        """A document triggering all rules gets all params set."""
        mock_script_router.get_engine_config.return_value = {
            "engine": "rapidocr",
            "batch_size": 4,
        }
        mock_script_router.get_vlm_escalation_reasons.return_value = []

        tc = TableComplexity(complexity_score=0.8, has_merged_cells=True)
        ps = _make_page_summary(
            has_tables=True,
            table_complexity=tc,
            has_code=True,
            has_dense_math=True,
            has_handwriting=True,
        )
        meta = _make_metadata(
            text_layer_quality=0.95,
            text_layer_skip_ocr=True,
            script_detection=_make_script_detection("Latn"),
            page_layout_summary=[ps],
        )

        decision = engine.route(meta, ps)

        # Rule 1: text layer -> skip OCR
        assert decision.params.ocr_enabled is False
        # Rule 2: script engine
        assert decision.params.ocr_engine == "rapidocr"
        # Rule 3: VLM from handwriting
        assert decision.params.pipeline == "vlm"
        # Rule 4: table mode
        assert decision.params.table_mode == "accurate"
        # Rule 5: enrichments
        assert decision.params.enrich_code is True
        assert decision.params.enrich_formula is True
        # Rule 6: PSM
        assert decision.params.psm is not None

        # Audit trail has entries from multiple rules
        assert len(decision.rule_trace) >= 5

    def test_uses_first_page_summary_when_none_provided(
        self, engine: DoclingRoutingEngine
    ) -> None:
        """When page_summary is None, first entry from metadata is used."""
        ps = _make_page_summary(has_code=True)
        meta = _make_metadata(page_layout_summary=[ps])
        decision = engine.route(meta, page_summary=None)
        assert decision.params.enrich_code is True

    def test_no_page_summary_at_all(self, engine: DoclingRoutingEngine) -> None:
        """No page_summary in args or metadata -> PSM/enrichments skipped."""
        meta = _make_metadata(page_layout_summary=[])
        decision = engine.route(meta)
        assert decision.params.psm is None
        assert decision.params.enrich_code is False
        assert decision.params.enrich_formula is False


# =============================================================================
# Edge cases
# =============================================================================


class TestEdgeCases:
    """Edge cases and defaults."""

    def test_defaults_with_minimal_metadata(self, engine: DoclingRoutingEngine) -> None:
        """Minimal metadata produces sensible defaults."""
        meta = _make_metadata()
        decision = engine.route(meta)
        assert decision.params.pipeline == "standard"
        assert decision.params.ocr_enabled is True
        assert decision.params.ocr_engine == "auto"
        assert decision.params.page_batch_size == 4
        assert decision.params.enrich_code is False
        assert decision.params.enrich_formula is False

    def test_routing_decision_is_frozen_dataclass(
        self, engine: DoclingRoutingEngine
    ) -> None:
        meta = _make_metadata()
        decision = engine.route(meta)
        assert isinstance(decision, RoutingDecision)
        assert isinstance(decision.params, DoclingRoutingParams)

    def test_cli_args_generation(self, engine: DoclingRoutingEngine) -> None:
        """Params produced by router can be serialized to CLI args."""
        ps = _make_page_summary(has_code=True)
        meta = _make_metadata(page_layout_summary=[ps])
        decision = engine.route(meta, ps)
        args = decision.params.to_cli_args()
        assert isinstance(args, list)
        assert "--pipeline=standard" in args
        assert "--enrich-code" in args


# =============================================================================
# Singleton and convenience functions
# =============================================================================


class TestSingleton:
    """Module-level singleton and convenience functions."""

    def test_get_default_engine_returns_same_instance(self) -> None:
        reset_default_engine()
        engine1 = get_default_engine()
        engine2 = get_default_engine()
        assert engine1 is engine2

    def test_reset_clears_singleton(self) -> None:
        reset_default_engine()
        engine1 = get_default_engine()
        reset_default_engine()
        engine2 = get_default_engine()
        assert engine1 is not engine2

    def test_route_document_convenience(self) -> None:
        """route_document() uses default engine."""
        reset_default_engine()
        meta = _make_metadata()
        decision = route_document(meta)
        assert isinstance(decision, RoutingDecision)
        reset_default_engine()


# =============================================================================
# Lazy ScriptRouter loading
# =============================================================================


class TestLazyScriptRouter:
    """ScriptRouter is lazy-loaded when not injected."""

    def test_lazy_loads_script_router(self) -> None:
        engine = DoclingRoutingEngine(script_router=None)
        with patch(
            "image_preprocessing_detector.routing.script_router.get_default_router"
        ) as mock_get:
            mock_router = MagicMock()
            mock_router.get_engine_config.return_value = {
                "engine": "auto",
                "batch_size": 4,
            }
            mock_router.get_lang_hint.return_value = None
            mock_router.get_vlm_escalation_reasons.return_value = []
            mock_get.return_value = mock_router

            meta = _make_metadata(
                script_detection=_make_script_detection("Latn"),
            )
            engine.route(meta)
            mock_get.assert_called_once()


# =============================================================================
# Element count estimation
# =============================================================================


class TestElementCountEstimation:
    """_estimate_element_count heuristic."""

    def test_empty_page_zero_elements(self) -> None:
        ps = _make_page_summary()
        count = DoclingRoutingEngine._estimate_element_count(ps)
        assert count == 0

    def test_all_flags_set(self) -> None:
        ps = _make_page_summary(
            has_tables=True,
            has_figures=True,
            has_code=True,
            has_dense_math=True,
            has_handwriting=True,
            has_list_items=True,
            has_headers_footers=True,
        )
        count = DoclingRoutingEngine._estimate_element_count(ps)
        # 7 flags, headers_footers counts as 2
        assert count == 8
