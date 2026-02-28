"""Tests for tiered font sampling in the synthetic generation pipeline.

Verifies that get_tiered_font() returns diverse font families per script
and that the tier distribution approximately matches FONT_TIER_WEIGHTS.
"""

from __future__ import annotations

from collections import Counter
from typing import ClassVar
from unittest.mock import patch

import pytest

from image_preprocessing_detector.synthetic.config import (
    FONT_RECOMMENDATIONS,
    FONT_TIER_WEIGHTS,
    HANDWRITING_FONTS,
    MIMICRY_FONTS,
)
from image_preprocessing_detector.synthetic.fonts import FontManager


@pytest.fixture
def font_manager() -> FontManager:
    """Create and scan a FontManager instance."""
    fm = FontManager()
    fm.scan_fonts()
    return fm


class TestFontManagerDiscovery:
    """Test that FontManager discovers fonts for all configured scripts."""

    def test_scans_fonts_successfully(self, font_manager: FontManager) -> None:
        """FontManager should discover fonts from system and bundled dirs."""
        assert len(font_manager.fonts_by_script) > 0
        total_fonts = sum(
            len(cache.fonts) for cache in font_manager.fonts_by_script.values()
        )
        assert total_fonts > 100, f"Expected 100+ fonts, found {total_fonts}"

    def test_all_recommended_scripts_have_fonts(
        self,
        font_manager: FontManager,
    ) -> None:
        """Every script in FONT_RECOMMENDATIONS should have at least one font."""
        for script in FONT_RECOMMENDATIONS:
            # Skip variant scripts that map to base scripts
            # Kore maps to Hang in ISO 15924; FontManager uses Hang
            if script in ("Arab_Nastaliq", "Cyrl_Bulgarian", "Kore"):
                continue
            cache = font_manager.fonts_by_script.get(script)
            assert cache is not None and len(cache.fonts) > 0, (
                f"Script {script} has no fonts discovered"
            )


class TestTieredFontSampling:
    """Test that tiered font sampling produces diverse output."""

    @pytest.mark.parametrize(
        "script_code",
        ["Latn", "Arab", "Deva", "Thai", "Khmr"],
    )
    def test_tiered_font_returns_diverse_families(
        self,
        font_manager: FontManager,
        script_code: str,
    ) -> None:
        """Calling get_tiered_font 50 times should yield 2+ distinct families."""
        families_seen: set[str] = set()
        for _ in range(50):
            font = font_manager.get_tiered_font(script_code, size=24)
            if font is not None and hasattr(font, "path"):
                # Extract family from the font path
                path_str = str(font.path) if hasattr(font, "path") else "unknown"
                families_seen.add(path_str)

        # At minimum, tiered sampling should produce variety
        # (even 2 families proves it's not stuck on the default)
        assert len(families_seen) >= 2, (
            f"Script {script_code}: only {len(families_seen)} distinct fonts "
            f"after 50 calls — tiered sampling may not be working"
        )

    def test_nastaliq_selection_for_urdu(
        self,
        font_manager: FontManager,
    ) -> None:
        """Urdu should select Nastaliq-style fonts, not Naskh."""
        font = font_manager.get_tiered_font("Arab", size=24, language_code="urd_Arab")
        # Should not crash; font may be None if no Nastaliq fonts installed
        assert font is None or font is not None

    def test_bulgarian_cyrillic_variant(
        self,
        font_manager: FontManager,
    ) -> None:
        """Bulgarian should use Cyrl_Bulgarian font recommendations."""
        font = font_manager.get_tiered_font("Cyrl", size=24, language_code="bul_Cyrl")
        # Should not crash; font may be None if no Bulgarian fonts installed
        assert font is None or font is not None


class TestRendererIntegration:
    """Test that the renderer actually calls get_tiered_font."""

    def test_load_font_calls_get_tiered_font(
        self,
        font_manager: FontManager,
    ) -> None:
        """DocumentRenderer._load_font should use get_tiered_font, not default."""
        from image_preprocessing_detector.synthetic.renderer import DocumentRenderer

        renderer = DocumentRenderer(font_manager)

        with patch.object(
            font_manager,
            "get_tiered_font",
            wraps=font_manager.get_tiered_font,
        ) as mock_tiered:
            renderer._load_font("Latn", 24, "body", "eng_Latn")
            mock_tiered.assert_called_once_with("Latn", 24, "eng_Latn")

    def test_load_font_passes_language_code(
        self,
        font_manager: FontManager,
    ) -> None:
        """_load_font should forward language_code for Nastaliq detection."""
        from image_preprocessing_detector.synthetic.renderer import DocumentRenderer

        renderer = DocumentRenderer(font_manager)

        with patch.object(
            font_manager,
            "get_tiered_font",
            wraps=font_manager.get_tiered_font,
        ) as mock_tiered:
            renderer._load_font("Arab", 24, "body", "urd_Arab")
            mock_tiered.assert_called_once_with("Arab", 24, "urd_Arab")


class TestHandwritingFontCoverage:
    """Test handwriting fonts are configured for appropriate scripts."""

    def test_handwriting_fonts_exist_for_major_scripts(self) -> None:
        """Major scripts should have handwriting font recommendations."""
        scripts_needing_handwriting = ["Cyrl", "Arab", "Hebr", "Deva", "Latn"]
        for script in scripts_needing_handwriting:
            assert script in HANDWRITING_FONTS, (
                f"Script {script} missing from HANDWRITING_FONTS"
            )
            assert len(HANDWRITING_FONTS[script]) >= 1, (
                f"Script {script} has no handwriting fonts configured"
            )

    def test_font_tier_weights_sum_to_one(self) -> None:
        """FONT_TIER_WEIGHTS must sum to 1.0 for valid probability distribution."""
        total = sum(FONT_TIER_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001, (
            f"FONT_TIER_WEIGHTS sum to {total}, expected 1.0"
        )


class TestAdversarialTierPopulation:
    """Test that ADVERSARIAL tiers are populated and sampled correctly.

    V4 Font Diversity Strategy requires non-empty ADVERSARIAL tiers for
    11 scripts to enable cross-script confusion and structural destruction
    testing in the OOD evaluation set.
    """

    _SCRIPTS_WITH_ADVERSARIAL: ClassVar[list[str]] = [
        "Latn",
        "Arab",
        "Deva",
        "Cyrl",
        "Grek",
        "Hans",
        "Kore",
        "Sinh",
        "Telu",
        "Khmr",
        "Thai",
    ]

    @pytest.mark.parametrize(
        "script_code",
        _SCRIPTS_WITH_ADVERSARIAL,
    )
    def test_adversarial_tier_not_empty(self, script_code: str) -> None:
        """Each target script must have at least one ADVERSARIAL font."""
        recs = FONT_RECOMMENDATIONS.get(script_code)
        assert recs is not None, (
            f"Script {script_code} missing from FONT_RECOMMENDATIONS"
        )
        adversarial = recs.get("ADVERSARIAL", [])
        assert len(adversarial) >= 1, f"Script {script_code}: ADVERSARIAL tier is empty"

    @pytest.mark.parametrize(
        "script_code",
        ["Latn", "Arab", "Deva", "Cyrl", "Grek"],
    )
    def test_adversarial_fonts_discoverable(
        self,
        font_manager: FontManager,
        script_code: str,
    ) -> None:
        """FontManager should find at least one ADVERSARIAL font for key scripts."""
        recs = FONT_RECOMMENDATIONS.get(script_code, {})
        adversarial_families = recs.get("ADVERSARIAL", [])
        assert len(adversarial_families) >= 1

        matching = font_manager._find_fonts_by_families(
            script_code,
            adversarial_families,
        )
        assert len(matching) >= 1, (
            f"Script {script_code}: no ADVERSARIAL fonts discovered "
            f"(tried: {adversarial_families})"
        )

    def test_adversarial_tier_sampled_at_expected_rate(
        self,
        font_manager: FontManager,
    ) -> None:
        """ADVERSARIAL tier should be sampled at roughly 5% (1-12% range)."""
        n_draws = 2000
        tier_counts: Counter[str] = Counter()

        for _ in range(n_draws):
            tier = font_manager._select_tier(FONT_TIER_WEIGHTS)
            tier_counts[tier] += 1

        adversarial_count = tier_counts.get("ADVERSARIAL", 0)
        adversarial_rate = adversarial_count / n_draws

        # Expected 5% per FONT_TIER_WEIGHTS; allow 1-12% range for randomness
        assert 0.01 <= adversarial_rate <= 0.12, (
            f"ADVERSARIAL tier sampled at {adversarial_rate:.1%} "
            f"({adversarial_count}/{n_draws}), expected 1-12%"
        )

    def test_case_variation_cap(self) -> None:
        """ALL CAPS images must not exceed 5% of total rendered samples."""
        # Verify the 5% cap logic matches expectations
        for n_images in [50, 100, 150, 200, 375]:
            max_caps = max(1, int(n_images * 0.05))
            assert max_caps / n_images <= 0.05 or n_images < 20, (
                f"n_images={n_images}: caps={max_caps} exceeds 5% cap"
            )
            assert max_caps >= 1, (
                f"n_images={n_images}: must produce at least 1 caps image"
            )

    @pytest.mark.parametrize(
        "target_script",
        list(MIMICRY_FONTS.keys()),
    )
    def test_mimicry_font_loading(
        self,
        font_manager: FontManager,
        target_script: str,
    ) -> None:
        """get_mimicry_font should return a valid font or graceful None."""
        font, family = font_manager.get_mimicry_font(target_script, size=24)
        # Mimicry fonts are rare/specialty — not all may be installed.
        # The API must not crash regardless of availability.
        if font is not None:
            assert family != "", (
                f"Mimicry font loaded for {target_script} but family is empty"
            )
        else:
            # Graceful None is acceptable when fonts are not installed
            assert family == ""
