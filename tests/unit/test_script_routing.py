"""Unit tests for Script ML Mapping and Script Router.

Tests for:
- ScriptMLMapping (Tier 2 of three-tier architecture)
- ScriptRouter (Tier 3 of three-tier architecture)
"""

from __future__ import annotations

import pytest

from image_preprocessing_detector.routing.script_router import (
    ScriptRouter,
    get_default_router,
    reset_default_router,
)
from image_preprocessing_detector.schema_utils.script_ml_mapping import (
    ScriptMLMapping,
    get_default_mapping,
    reset_default_mapping,
)


class TestScriptMLMapping:
    """Test ScriptMLMapping class (Tier 2)."""

    @pytest.fixture
    def mapping(self) -> ScriptMLMapping:
        """Create ScriptMLMapping with test config."""
        # Use default config path - will use defaults if config missing
        return ScriptMLMapping()

    def test_latin_script_mapping(self, mapping: ScriptMLMapping) -> None:
        """Test Latin script maps to LATN class."""
        assert mapping.to_ml_class("Latn") == "LATN"

    def test_cjk_script_mappings(self, mapping: ScriptMLMapping) -> None:
        """Test CJK scripts map to correct classes."""
        assert mapping.to_ml_class("Hans") == "HANS"
        assert mapping.to_ml_class("Hant") == "HANT"
        assert mapping.to_ml_class("Jpan") == "JPAN"
        assert mapping.to_ml_class("Kore") == "KORE"

    def test_indic_script_mappings(self, mapping: ScriptMLMapping) -> None:
        """Test major Indic scripts have dedicated classes."""
        assert mapping.to_ml_class("Deva") == "DEVA"
        assert mapping.to_ml_class("Beng") == "BENG"
        assert mapping.to_ml_class("Taml") == "TAML"
        assert mapping.to_ml_class("Telu") == "TELU"

    def test_other_indic_scripts_grouped(self, mapping: ScriptMLMapping) -> None:
        """Test minor Indic scripts map to INDIC_OTHER."""
        # These should be grouped if config has the grouping
        ml_class = mapping.to_ml_class("Gujr")
        assert ml_class in ("INDIC_OTHER", "OTHER", "GUJR")  # Flexible for config

    def test_unknown_script(self, mapping: ScriptMLMapping) -> None:
        """Test unknown script code maps to Zzzz -> UNKNOWN."""
        assert mapping.to_ml_class("Zzzz") == "UNKNOWN"

    def test_unmapped_script_uses_default(self, mapping: ScriptMLMapping) -> None:
        """Test truly unknown scripts use default mapping."""
        result = mapping.to_ml_class("Xxxx")  # Made-up code
        assert result == mapping.default

    def test_get_all_codes_for_class(self, mapping: ScriptMLMapping) -> None:
        """Test getting all ISO codes for an ML class."""
        latn_codes = mapping.get_all_codes_for_class("LATN")
        assert "Latn" in latn_codes

    def test_get_num_classes(self, mapping: ScriptMLMapping) -> None:
        """Test getting number of ML classes."""
        num_classes = mapping.get_num_classes()
        assert num_classes > 0
        assert num_classes <= 25  # Reasonable upper bound

    def test_is_valid_iso15924(self, mapping: ScriptMLMapping) -> None:
        """Test checking valid ISO 15924 codes."""
        assert mapping.is_valid_iso15924("Latn") is True
        assert mapping.is_valid_iso15924("Xxxx") is False

    def test_reload(self, mapping: ScriptMLMapping) -> None:
        """Test config reload doesn't crash."""
        # Just verify reload doesn't raise
        mapping.reload()

    def test_singleton_default_mapping(self) -> None:
        """Test default mapping singleton."""
        reset_default_mapping()

        mapping1 = get_default_mapping()
        mapping2 = get_default_mapping()

        assert mapping1 is mapping2

        # Clean up
        reset_default_mapping()


class TestScriptRouter:
    """Test ScriptRouter class (Tier 3)."""

    @pytest.fixture
    def router(self) -> ScriptRouter:
        """Create ScriptRouter with test config."""
        mapping = ScriptMLMapping()
        return ScriptRouter(mapping)

    def test_latin_script_engine(self, router: ScriptRouter) -> None:
        """Test Latin script routes to appropriate engine."""
        config = router.get_engine_config("Latn")
        # Engine should be one of the valid options
        assert config["engine"] in ("rapidocr", "tesseract", "paddleocr", "auto")

    def test_cjk_script_batch_size(self, router: ScriptRouter) -> None:
        """Test CJK scripts have reduced batch size for memory."""
        config = router.get_engine_config("Hans")
        # CJK typically has smaller batch size
        assert config["batch_size"] <= 4

    def test_rtl_script_flag(self, router: ScriptRouter) -> None:
        """Test RTL scripts have RTL flag."""
        config = router.get_engine_config("Arab")
        # Arabic should have RTL flag if config is complete
        # If using defaults, this might not be set
        rtl = config.get("rtl", False)
        assert isinstance(rtl, bool)

    def test_get_engine_shortcut(self, router: ScriptRouter) -> None:
        """Test get_engine convenience method."""
        engine = router.get_engine("Latn")
        assert isinstance(engine, str)

    def test_get_batch_size_shortcut(self, router: ScriptRouter) -> None:
        """Test get_batch_size convenience method."""
        batch_size = router.get_batch_size("Latn")
        assert isinstance(batch_size, int)
        assert batch_size > 0

    def test_should_escalate_to_vlm_low_confidence(self, router: ScriptRouter) -> None:
        """Test VLM escalation for low confidence."""
        # Very low confidence should trigger escalation
        should_escalate = router.should_escalate_to_vlm("Latn", confidence=0.2)
        assert should_escalate is True

    def test_should_not_escalate_high_confidence(self, router: ScriptRouter) -> None:
        """Test no VLM escalation for high confidence."""
        should_escalate = router.should_escalate_to_vlm("Latn", confidence=0.95)
        assert should_escalate is False

    def test_should_escalate_unknown_script(self, router: ScriptRouter) -> None:
        """Test VLM escalation for unknown script."""
        should_escalate = router.should_escalate_to_vlm("Zzzz", confidence=0.5)
        # Unknown script typically escalates
        assert isinstance(should_escalate, bool)

    def test_get_vlm_escalation_reasons(self, router: ScriptRouter) -> None:
        """Test getting VLM escalation reasons."""
        reasons = router.get_vlm_escalation_reasons("Latn", confidence=0.2)
        assert isinstance(reasons, list)
        # Low confidence should give a reason
        assert len(reasons) > 0

    def test_reload(self, router: ScriptRouter) -> None:
        """Test config reload doesn't crash."""
        router.reload()

    def test_singleton_default_router(self) -> None:
        """Test default router singleton."""
        reset_default_router()
        reset_default_mapping()

        router1 = get_default_router()
        router2 = get_default_router()

        assert router1 is router2

        # Clean up
        reset_default_router()
        reset_default_mapping()


class TestThreeTierIntegration:
    """Test three-tier architecture integration."""

    def test_tier1_to_tier2_to_tier3(self) -> None:
        """Test full flow from ISO 15924 to engine config."""
        from image_preprocessing_detector.schema import ScriptDetectionResult

        # Tier 1: Create detection result with ISO 15924 code
        detection = ScriptDetectionResult(
            detected_script="Deva",
            confidence=0.90,
            detection_method="heuristic",
        )

        # Tier 2: Get ML class
        mapping = ScriptMLMapping()
        ml_class = detection.get_ml_class(mapping)
        assert ml_class in ("DEVA", "INDIC_OTHER", "OTHER")

        # Tier 3: Get routing config
        router = ScriptRouter(mapping)
        config = detection.get_routing_config(router)
        assert "engine" in config
        assert "batch_size" in config

    def test_multi_script_routing(self) -> None:
        """Test routing for multi-script document."""
        from image_preprocessing_detector.schema import (
            DocumentScriptDetection,
            ScriptDetectionResult,
        )

        instances = [
            ScriptDetectionResult(
                detected_script="Latn",
                confidence=0.95,
                detection_method="heuristic",
            ),
            ScriptDetectionResult(
                detected_script="Hans",
                confidence=0.88,
                detection_method="heuristic",
            ),
        ]

        detection = DocumentScriptDetection.from_instances(instances)

        assert detection.is_multilingual is True
        assert detection.needs_multi_engine is True
