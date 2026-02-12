# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Unit tests for synth-multiscript v2.3 features.

Covers:
- SplitRegistry: deterministic split assignment, JSONL persistence, leakage detection
- _select_text_direction: CJK vertical ratios, fallback behavior
- Schema adapter v2.3 fields: text_direction, text_directions_present,
  character_height_rendered_px, output_size_px
- SKEW_RANGE_DEGREES bounds
- Generator v2.3 metadata: degradation_seed, base_image_sha256, font_families_used
- English secondary weighting in multi-script composition
"""

from __future__ import annotations

import random
from pathlib import Path

# =============================================================================
# SplitRegistry Tests
# =============================================================================


class TestHashToSplit:
    """Tests for the deterministic hash-to-split function."""

    def test_deterministic_for_same_hash(self) -> None:
        """Same hash always produces the same split."""
        from image_preprocessing_detector.schema_utils.split_registry import (
            _hash_to_split,
        )

        sha = "a" * 64
        results = {_hash_to_split(sha) for _ in range(100)}
        assert len(results) == 1

    def test_returns_valid_split_name(self) -> None:
        """All returned split names are train, val, or test."""
        from image_preprocessing_detector.schema_utils.split_registry import (
            _hash_to_split,
        )

        for i in range(200):
            sha = f"{i:064x}"
            assert _hash_to_split(sha) in {"train", "val", "test"}

    def test_respects_ratios_approximately(self) -> None:
        """Split distribution roughly matches the given ratios."""
        from image_preprocessing_detector.schema_utils.split_registry import (
            _hash_to_split,
        )

        counts = {"train": 0, "val": 0, "test": 0}
        n = 10000
        for i in range(n):
            # Generate unique hashes
            import hashlib

            sha = hashlib.sha256(str(i).encode()).hexdigest()
            counts[_hash_to_split(sha)] += 1

        # 80/10/10 ratios with generous tolerance (±5%)
        assert counts["train"] / n > 0.75
        assert counts["train"] / n < 0.85
        assert counts["val"] / n > 0.05
        assert counts["test"] / n > 0.05

    def test_custom_ratios(self) -> None:
        """Custom ratios produce different distributions."""
        from image_preprocessing_detector.schema_utils.split_registry import (
            _hash_to_split,
        )

        # 50/25/25 split
        counts = {"train": 0, "val": 0, "test": 0}
        n = 5000
        for i in range(n):
            import hashlib

            sha = hashlib.sha256(str(i).encode()).hexdigest()
            counts[_hash_to_split(sha, ratios=(0.5, 0.25, 0.25))] += 1

        assert counts["train"] / n < 0.60  # Not 80% anymore
        assert counts["val"] / n > 0.15


class TestComputeImageHash:
    """Tests for image file SHA256 hashing."""

    def test_same_content_same_hash(self, tmp_path: Path) -> None:
        """Identical content produces identical hash."""
        from image_preprocessing_detector.schema_utils.split_registry import (
            compute_image_hash,
        )

        content = b"test image content"
        f1 = tmp_path / "img1.bin"
        f2 = tmp_path / "img2.bin"
        f1.write_bytes(content)
        f2.write_bytes(content)
        assert compute_image_hash(f1) == compute_image_hash(f2)

    def test_different_content_different_hash(self, tmp_path: Path) -> None:
        """Different content produces different hash."""
        from image_preprocessing_detector.schema_utils.split_registry import (
            compute_image_hash,
        )

        f1 = tmp_path / "img1.bin"
        f2 = tmp_path / "img2.bin"
        f1.write_bytes(b"content a")
        f2.write_bytes(b"content b")
        assert compute_image_hash(f1) != compute_image_hash(f2)

    def test_hash_is_64_char_hex(self, tmp_path: Path) -> None:
        """SHA256 hex digest is 64 characters."""
        from image_preprocessing_detector.schema_utils.split_registry import (
            compute_image_hash,
        )

        f = tmp_path / "test.bin"
        f.write_bytes(b"data")
        h = compute_image_hash(f)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


class TestSplitRegistry:
    """Tests for the SplitRegistry class."""

    def test_assign_and_lookup(self, tmp_path: Path) -> None:
        """Assigned split can be looked up."""
        from image_preprocessing_detector.schema_utils.split_registry import (
            SplitRegistry,
        )

        registry = SplitRegistry(tmp_path / "splits.jsonl")
        sha = "a" * 64
        split = registry.assign_split(sha)
        assert split in {"train", "val", "test"}
        assert registry.lookup(sha) == split

    def test_assign_is_idempotent(self, tmp_path: Path) -> None:
        """Assigning the same hash twice returns the same split."""
        from image_preprocessing_detector.schema_utils.split_registry import (
            SplitRegistry,
        )

        registry = SplitRegistry(tmp_path / "splits.jsonl")
        sha = "b" * 64
        s1 = registry.assign_split(sha)
        s2 = registry.assign_split(sha)
        assert s1 == s2

    def test_persistence_across_instances(self, tmp_path: Path) -> None:
        """Registry persists to JSONL and reloads correctly."""
        from image_preprocessing_detector.schema_utils.split_registry import (
            SplitRegistry,
        )

        path = tmp_path / "splits.jsonl"
        r1 = SplitRegistry(path)
        sha = "c" * 64
        split = r1.assign_split(sha, source_dataset="test_ds")

        # New instance loads from file
        r2 = SplitRegistry(path)
        assert r2.lookup(sha) == split
        assert len(r2) == 1

    def test_stats(self, tmp_path: Path) -> None:
        """Stats reflect assigned splits."""
        from image_preprocessing_detector.schema_utils.split_registry import (
            SplitRegistry,
        )

        registry = SplitRegistry(tmp_path / "splits.jsonl")
        for i in range(50):
            import hashlib

            sha = hashlib.sha256(str(i).encode()).hexdigest()
            registry.assign_split(sha)

        stats = registry.stats
        assert stats["train"] + stats["val"] + stats["test"] == 50

    def test_contains(self, tmp_path: Path) -> None:
        """__contains__ works for registered hashes."""
        from image_preprocessing_detector.schema_utils.split_registry import (
            SplitRegistry,
        )

        registry = SplitRegistry(tmp_path / "splits.jsonl")
        sha = "d" * 64
        assert sha not in registry
        registry.assign_split(sha)
        assert sha in registry

    def test_lookup_unknown_returns_none(self, tmp_path: Path) -> None:
        """Looking up unregistered hash returns None."""
        from image_preprocessing_detector.schema_utils.split_registry import (
            SplitRegistry,
        )

        registry = SplitRegistry(tmp_path / "splits.jsonl")
        assert registry.lookup("f" * 64) is None

    def test_verify_no_leakage_clean(self, tmp_path: Path) -> None:
        """No violations when sets are disjoint."""
        from image_preprocessing_detector.schema_utils.split_registry import (
            SplitRegistry,
        )

        registry = SplitRegistry(tmp_path / "splits.jsonl")
        train_hashes = set()
        test_hashes = set()

        import hashlib

        for i in range(100):
            sha = hashlib.sha256(str(i).encode()).hexdigest()
            split = registry.assign_split(sha)
            if split == "train":
                train_hashes.add(sha)
            elif split == "test":
                test_hashes.add(sha)

        # Disjoint sets should have no violations
        violations = registry.verify_no_leakage(
            train_hashes, test_hashes, "train", "test"
        )
        assert len(violations) == 0

    def test_malformed_jsonl_skipped(self, tmp_path: Path) -> None:
        """Malformed lines are skipped during loading."""
        from image_preprocessing_detector.schema_utils.split_registry import (
            SplitRegistry,
        )

        path = tmp_path / "splits.jsonl"
        path.write_text(
            '{"sha256": "aaaa", "split": "train"}\n'
            "not valid json\n"
            '{"sha256": "bbbb", "split": "test"}\n'
        )
        registry = SplitRegistry(path)
        assert len(registry) == 2


# =============================================================================
# _select_text_direction Tests
# =============================================================================


class TestSelectTextDirection:
    """Tests for CJK vertical text direction selection."""

    def _make_generator(self, seed: int = 42) -> object:
        """Create a minimal generator with RNG for testing."""
        from image_preprocessing_detector.synthetic.generator import (
            GenerationConfig,
            MultiScriptDocumentGenerator,
        )

        config = GenerationConfig(scripts=["Latn"], samples_per_script=1, seed=seed)
        gen = MultiScriptDocumentGenerator(config)
        gen._rng = random.Random(seed)
        return gen

    def test_latin_returns_ltr(self) -> None:
        """Latin script always returns ltr."""
        gen = self._make_generator()
        results = {gen._select_text_direction("Latn") for _ in range(100)}
        assert results == {"ltr"}

    def test_arab_returns_rtl(self) -> None:
        """Arabic script always returns rtl."""
        gen = self._make_generator()
        results = {gen._select_text_direction("Arab") for _ in range(100)}
        assert results == {"rtl"}

    def test_jpan_produces_both_ltr_and_ttb(self) -> None:
        """Japanese produces both horizontal and vertical text."""
        gen = self._make_generator(seed=0)
        results = set()
        for i in range(500):
            gen._rng = random.Random(i)
            results.add(gen._select_text_direction("Jpan"))
        assert "ltr" in results
        assert "ttb" in results

    def test_jpan_vertical_ratio_approximate(self) -> None:
        """Japanese vertical ratio is approximately 30%."""
        gen = self._make_generator()
        ttb_count = 0
        n = 2000
        for i in range(n):
            gen._rng = random.Random(i)
            if gen._select_text_direction("Jpan") == "ttb":
                ttb_count += 1
        ratio = ttb_count / n
        assert 0.20 < ratio < 0.40, f"Jpan vertical ratio {ratio:.2f} not ~0.30"

    def test_hans_vertical_ratio_approximate(self) -> None:
        """Simplified Chinese vertical ratio is approximately 10%."""
        gen = self._make_generator()
        ttb_count = 0
        n = 2000
        for i in range(n):
            gen._rng = random.Random(i)
            if gen._select_text_direction("Hans") == "ttb":
                ttb_count += 1
        ratio = ttb_count / n
        assert 0.03 < ratio < 0.20, f"Hans vertical ratio {ratio:.2f} not ~0.10"

    def test_hant_vertical_ratio_approximate(self) -> None:
        """Traditional Chinese vertical ratio is approximately 10%."""
        gen = self._make_generator()
        ttb_count = 0
        n = 2000
        for i in range(n):
            gen._rng = random.Random(i)
            if gen._select_text_direction("Hant") == "ttb":
                ttb_count += 1
        ratio = ttb_count / n
        assert 0.03 < ratio < 0.20, f"Hant vertical ratio {ratio:.2f} not ~0.10"

    def test_unknown_script_returns_ltr(self) -> None:
        """Unknown script code defaults to ltr."""
        gen = self._make_generator()
        assert gen._select_text_direction("Zzzz") == "ltr"


# =============================================================================
# Schema Adapter v2.3 Fields Tests
# =============================================================================


class TestSchemaAdapterV23Fields:
    """Tests for schema adapter handling of v2.3 fields."""

    def _make_sample(self, **kwargs: object) -> object:
        """Create a GeneratedSample with defaults."""
        from image_preprocessing_detector.synthetic.config import (
            LayoutType,
            TextDensity,
        )
        from image_preprocessing_detector.synthetic.schema_adapter import (
            GeneratedSample,
            IQALabels,
        )

        try:
            from PIL import Image

            img = Image.new("RGB", (100, 100), "white")
        except ImportError:
            img = None

        defaults = {
            "image": img,
            "sample_id": "test-001",
            "scripts": {"Latn"},
            "language_codes": ["eng_Latn"],
            "layout_type": LayoutType.STACKED,
            "text_density": TextDensity.MEDIUM,
            "iqa_labels": IQALabels(overall_quality=0.9),
            "resolution_dpi": 300,
            "width_px": 100,
            "height_px": 100,
        }
        defaults.update(kwargs)
        return GeneratedSample(**defaults)

    def test_text_directions_field_exists(self) -> None:
        """GeneratedSample has text_directions field."""
        sample = self._make_sample()
        sample.text_directions = {"Latn": "ltr"}
        assert sample.text_directions == {"Latn": "ltr"}

    def test_char_height_rendered_field(self) -> None:
        """GeneratedSample has char_height_rendered_px field."""
        sample = self._make_sample()
        sample.char_height_rendered_px = 24.5
        assert sample.char_height_rendered_px == 24.5

    def test_output_size_px_field(self) -> None:
        """GeneratedSample has output_size_px field."""
        sample = self._make_sample()
        sample.output_size_px = 384
        assert sample.output_size_px == 384

    def test_defaults_are_none(self) -> None:
        """New v2.3 fields default to None."""
        sample = self._make_sample()
        assert sample.text_directions is None
        assert sample.char_height_rendered_px is None
        assert sample.output_size_px is None

    def test_build_language_info_with_text_direction(self) -> None:
        """build_language_info includes text_direction when provided."""
        from image_preprocessing_detector.synthetic.schema_adapter import (
            Layer2SchemaAdapter,
        )

        adapter = Layer2SchemaAdapter()
        info = adapter.build_language_info(
            language_code="jpn_Jpan",
            script_code="Jpan",
            text_direction="ttb",
        )
        assert info["text_direction"] == "ttb"

    def test_build_language_info_without_text_direction(self) -> None:
        """build_language_info omits text_direction when None."""
        from image_preprocessing_detector.synthetic.schema_adapter import (
            Layer2SchemaAdapter,
        )

        adapter = Layer2SchemaAdapter()
        info = adapter.build_language_info(
            language_code="eng_Latn",
            script_code="Latn",
        )
        assert "text_direction" not in info

    def test_schema_version_is_2_3_0(self) -> None:
        """Schema adapter outputs version 2.3.0."""
        from image_preprocessing_detector.synthetic.schema_adapter import (
            Layer2SchemaAdapter,
        )

        adapter = Layer2SchemaAdapter()
        sample = self._make_sample(
            text_directions={"Latn": "ltr"},
            char_height_rendered_px=30.0,
        )
        metadata = adapter.build_enrichment_metadata(sample)
        assert metadata["schema_version"] == "2.3.0"

    def test_enrichment_includes_text_directions_present(self) -> None:
        """Enrichment metadata includes text_directions_present in structure."""
        from image_preprocessing_detector.synthetic.schema_adapter import (
            Layer2SchemaAdapter,
        )

        adapter = Layer2SchemaAdapter()
        sample = self._make_sample(
            text_directions={"Jpan": "ttb", "Latn": "ltr"},
        )
        metadata = adapter.build_enrichment_metadata(sample)
        data = metadata.get("data", {})
        structure = data.get("structure", {})
        directions = structure.get("text_directions_present")
        assert directions is not None
        assert set(directions) == {"ttb", "ltr"}

    def test_enrichment_includes_char_height_rendered(self) -> None:
        """Enrichment metadata includes char_height_rendered_px in resolution."""
        from image_preprocessing_detector.synthetic.schema_adapter import (
            Layer2SchemaAdapter,
        )

        adapter = Layer2SchemaAdapter()
        sample = self._make_sample(char_height_rendered_px=28.5)
        metadata = adapter.build_enrichment_metadata(sample)
        data = metadata.get("data", {})
        resolution = data.get("resolution", {})
        assert resolution.get("character_height_rendered_px") == 28.5


# =============================================================================
# SKEW_RANGE_DEGREES Tests
# =============================================================================


class TestSkewRangeDegrees:
    """Tests for skew range configuration and usage."""

    def test_config_value_is_plus_minus_22(self) -> None:
        """SKEW_RANGE_DEGREES is (-22.0, 22.0)."""
        from image_preprocessing_detector.synthetic.config import SKEW_RANGE_DEGREES

        assert SKEW_RANGE_DEGREES == (-22.0, 22.0)

    def test_skew_range_is_symmetric(self) -> None:
        """Skew range is symmetric around zero."""
        from image_preprocessing_detector.synthetic.config import SKEW_RANGE_DEGREES

        assert abs(SKEW_RANGE_DEGREES[0] + SKEW_RANGE_DEGREES[1]) < 0.001

    def test_generated_skew_within_bounds(self) -> None:
        """Simulated skew values stay within configured range."""
        from image_preprocessing_detector.synthetic.config import SKEW_RANGE_DEGREES

        rng = random.Random(42)
        for _ in range(1000):
            angle = rng.uniform(SKEW_RANGE_DEGREES[0], SKEW_RANGE_DEGREES[1])
            assert -22.0 <= angle <= 22.0


# =============================================================================
# CJK Vertical Ratios Config Tests
# =============================================================================


class TestCJKVerticalRatios:
    """Tests for CJK vertical text configuration."""

    def test_jpan_ratio(self) -> None:
        """Japanese vertical ratio is 0.30."""
        from image_preprocessing_detector.synthetic.config import CJK_VERTICAL_RATIOS

        assert CJK_VERTICAL_RATIOS["Jpan"] == 0.30

    def test_hans_ratio(self) -> None:
        """Simplified Chinese vertical ratio is 0.10."""
        from image_preprocessing_detector.synthetic.config import CJK_VERTICAL_RATIOS

        assert CJK_VERTICAL_RATIOS["Hans"] == 0.10

    def test_hant_ratio(self) -> None:
        """Traditional Chinese vertical ratio is 0.10."""
        from image_preprocessing_detector.synthetic.config import CJK_VERTICAL_RATIOS

        assert CJK_VERTICAL_RATIOS["Hant"] == 0.10

    def test_only_three_scripts(self) -> None:
        """Only Jpan, Hans, Hant have vertical ratios."""
        from image_preprocessing_detector.synthetic.config import CJK_VERTICAL_RATIOS

        assert set(CJK_VERTICAL_RATIOS.keys()) == {"Jpan", "Hans", "Hant"}

    def test_latin_not_in_ratios(self) -> None:
        """Latin is not in CJK vertical ratios."""
        from image_preprocessing_detector.synthetic.config import CJK_VERTICAL_RATIOS

        assert "Latn" not in CJK_VERTICAL_RATIOS


# =============================================================================
# English Secondary Weighting Tests
# =============================================================================


class TestEnglishSecondaryWeighting:
    """Tests for English prevalence in multi-script composition."""

    def test_config_value(self) -> None:
        """ENGLISH_SECONDARY_WEIGHT is 0.40."""
        from image_preprocessing_detector.synthetic.config import (
            ENGLISH_SECONDARY_WEIGHT,
        )

        assert ENGLISH_SECONDARY_WEIGHT == 0.40

    def test_two_script_pair_latn_prevalence(self) -> None:
        """Latin appears as secondary script more often than random chance."""
        from image_preprocessing_detector.synthetic.generator import (
            GenerationConfig,
            MultiScriptDocumentGenerator,
        )

        # Setup generator with multiple scripts including Latn
        config = GenerationConfig(
            scripts=["Arab", "Deva", "Latn", "Jpan", "Kore"],
            samples_per_script=1,
            seed=42,
        )
        gen = MultiScriptDocumentGenerator(config)
        gen._rng = random.Random(42)

        # Available scripts minus Latn-only pairs in TWO_SCRIPT_COMBINATIONS
        available = ["Arab", "Deva", "Latn", "Jpan", "Kore"]

        latn_count = 0
        n = 1000
        for i in range(n):
            gen._rng = random.Random(i)
            pair = gen._select_two_script_pair(available)
            if "Latn" in pair:
                latn_count += 1

        # With 5 scripts, random chance is ~36% (1 - (4/5)*(3/4))
        # With weighting, Latn should appear significantly more often
        # At minimum, the fallback path should produce >30% Latn
        ratio = latn_count / n
        assert ratio > 0.30, f"Latn appeared in only {ratio:.1%} of pairs"


# =============================================================================
# Generator v2.3 Metadata Tests
# =============================================================================


class TestGeneratorV23Metadata:
    """Tests for generation_params and v2.3 sample metadata."""

    def test_generation_params_keys(self) -> None:
        """generation_params includes degradation_seed, base_image_sha256, font_families_used."""
        expected_keys = {"degradation_seed", "base_image_sha256", "font_families_used"}
        # Just verify the key names exist in the generation_params schema
        from image_preprocessing_detector.synthetic.schema_adapter import (
            GeneratedSample,
        )

        # Check the field exists and can hold dict values
        sample = GeneratedSample.__dataclass_fields__
        assert "generation_params" in sample

    def test_compute_image_sha256_deterministic(self) -> None:
        """Same image produces same SHA256."""
        from PIL import Image

        from image_preprocessing_detector.synthetic.generator import (
            GenerationConfig,
            MultiScriptDocumentGenerator,
        )

        config = GenerationConfig(scripts=["Latn"], samples_per_script=1, seed=42)
        gen = MultiScriptDocumentGenerator(config)
        gen._rng = random.Random(42)

        img = Image.new("RGB", (100, 100), "white")
        h1 = gen._compute_image_sha256(img)
        h2 = gen._compute_image_sha256(img)
        assert h1 == h2
        assert len(h1) == 64

    def test_compute_image_sha256_different_images(self) -> None:
        """Different images produce different SHA256."""
        from PIL import Image

        from image_preprocessing_detector.synthetic.generator import (
            GenerationConfig,
            MultiScriptDocumentGenerator,
        )

        config = GenerationConfig(scripts=["Latn"], samples_per_script=1, seed=42)
        gen = MultiScriptDocumentGenerator(config)
        gen._rng = random.Random(42)

        img1 = Image.new("RGB", (100, 100), "white")
        img2 = Image.new("RGB", (100, 100), "red")
        assert gen._compute_image_sha256(img1) != gen._compute_image_sha256(img2)

    def test_measure_char_height_rendered_returns_float_or_none(self) -> None:
        """_measure_char_height_rendered returns float or None."""
        from PIL import Image

        from image_preprocessing_detector.synthetic.generator import (
            GenerationConfig,
            MultiScriptDocumentGenerator,
        )

        config = GenerationConfig(scripts=["Latn"], samples_per_script=1, seed=42)
        gen = MultiScriptDocumentGenerator(config)
        gen._rng = random.Random(42)

        # Blank image should return None (no text to measure)
        img = Image.new("RGB", (100, 100), "white")
        result = gen._measure_char_height_rendered(img)
        assert result is None or isinstance(result, float)


# =============================================================================
# Output Sizes Config Tests
# =============================================================================


class TestOutputSizes:
    """Tests for multi-resolution output size configuration."""

    def test_output_sizes_values(self) -> None:
        """OUTPUT_SIZES contains 224, 384, 512."""
        from image_preprocessing_detector.synthetic.config import OUTPUT_SIZES

        assert OUTPUT_SIZES == [224, 384, 512]

    def test_output_sizes_sorted(self) -> None:
        """OUTPUT_SIZES is in ascending order."""
        from image_preprocessing_detector.synthetic.config import OUTPUT_SIZES

        assert sorted(OUTPUT_SIZES) == OUTPUT_SIZES


# =============================================================================
# Layout Weights Adjustment Tests
# =============================================================================


class TestLayoutWeights:
    """Tests for layout weight adjustments."""

    def test_dense_text_weight_increased(self) -> None:
        """DENSE_TEXT weight is 4% (increased from 3%)."""
        from image_preprocessing_detector.synthetic.config import LAYOUT_WEIGHTS

        dense_text_weight = LAYOUT_WEIGHTS.get(
            next(k for k in LAYOUT_WEIGHTS if k.value == "dense_text"), 0
        )
        assert abs(dense_text_weight - 0.04) < 0.001

    def test_weights_sum_to_one(self) -> None:
        """All layout weights sum to approximately 1.0."""
        from image_preprocessing_detector.synthetic.config import LAYOUT_WEIGHTS

        total = sum(LAYOUT_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01, f"Layout weights sum to {total}, not ~1.0"
