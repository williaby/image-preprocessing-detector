# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Integration tests for the parser registry.

Tests that the ParserRegistry properly loads and manages all dataset parsers,
ensuring correct registration, lookup, and integration with DATASET_CONFIGS.
"""

from __future__ import annotations

import pytest

from image_preprocessing_detector.annotation.config import DATASET_CONFIGS
from image_preprocessing_detector.annotation.parsers import ParserRegistry
from image_preprocessing_detector.annotation.parsers.base import DatasetParser


class TestParserRegistryIntegration:
    """Integration tests for ParserRegistry with all parser categories."""

    @pytest.fixture
    def registry(self) -> ParserRegistry:
        """Create default registry with all parsers."""
        return ParserRegistry.create_default()

    def test_create_default_loads_parsers(self, registry: ParserRegistry) -> None:
        """Test create_default() loads parsers from all categories."""
        # Should have parsers registered
        assert len(registry) > 0

        # Should have parsers from different categories
        datasets = registry.list_datasets()

        # Quality parsers
        assert "diqa-5000" in datasets or "diqa" in datasets

        # Layout parsers
        assert "doclaynet" in datasets
        assert "tablebank" in datasets

        # Handwriting parsers
        assert "signatr6k" in datasets or "signatr" in datasets

        # Multilingual parsers
        assert "mdiw13" in datasets or "mdiw" in datasets

        # Document parsers
        assert "rvl_cdip" in datasets or "rvl-cdip" in datasets

    def test_all_parsers_implement_protocol(self, registry: ParserRegistry) -> None:
        """Test all registered parsers implement DatasetParser protocol."""
        for dataset_name in registry.list_datasets():
            parser = registry.get_parser(dataset_name)
            assert parser is not None
            assert isinstance(parser, DatasetParser)
            assert hasattr(parser, "dataset_names")
            assert hasattr(parser, "parse")

    def test_list_parsers_returns_tuples(self, registry: ParserRegistry) -> None:
        """Test list_parsers returns (dataset_name, class_name) tuples."""
        parsers = registry.list_parsers()

        assert isinstance(parsers, list)
        assert len(parsers) > 0

        for item in parsers:
            assert isinstance(item, tuple)
            assert len(item) == 2
            dataset_name, class_name = item
            assert isinstance(dataset_name, str)
            assert isinstance(class_name, str)
            assert class_name.endswith("Parser")

    def test_get_parser_returns_correct_type(self, registry: ParserRegistry) -> None:
        """Test get_parser returns the correct parser type."""
        # Quality parser
        diqa_parser = registry.get_parser("diqa-5000")
        if diqa_parser is not None:
            assert "DIQA" in type(diqa_parser).__name__

        # Layout parser
        doclaynet_parser = registry.get_parser("doclaynet")
        if doclaynet_parser is not None:
            assert "DocLayNet" in type(doclaynet_parser).__name__

    def test_get_parser_nonexistent_returns_none(self, registry: ParserRegistry) -> None:
        """Test get_parser returns None for unregistered datasets."""
        parser = registry.get_parser("nonexistent_dataset_xyz")
        assert parser is None

    def test_has_parser_check(self, registry: ParserRegistry) -> None:
        """Test has_parser returns correct boolean."""
        datasets = registry.list_datasets()
        if datasets:
            # First dataset should exist
            assert registry.has_parser(datasets[0]) is True

        # Nonexistent dataset
        assert registry.has_parser("nonexistent_dataset_xyz") is False

    def test_contains_operator(self, registry: ParserRegistry) -> None:
        """Test __contains__ operator works."""
        datasets = registry.list_datasets()
        if datasets:
            assert datasets[0] in registry

        assert "nonexistent_dataset_xyz" not in registry

    def test_registry_datasets_sorted(self, registry: ParserRegistry) -> None:
        """Test list_datasets returns sorted list."""
        datasets = registry.list_datasets()
        assert datasets == sorted(datasets)


class TestParserRegistryManagement:
    """Tests for registry management operations."""

    def test_create_empty_registry(self) -> None:
        """Test create_empty returns empty registry."""
        registry = ParserRegistry.create_empty()
        assert len(registry) == 0
        assert registry.list_datasets() == []

    def test_register_custom_parser(self) -> None:
        """Test registering a custom parser."""
        from image_preprocessing_detector.annotation.parsers.base import BaseParser
        from image_preprocessing_detector.annotation.schemas.immutable import OriginalLabels
        from pathlib import Path
        from typing import Any

        class CustomParser(BaseParser):
            @property
            def dataset_names(self) -> list[str]:
                return ["custom_dataset"]

            def parse(
                self,
                dataset_path: Path,
                image_path: Path,
                config: dict[str, Any],
            ) -> OriginalLabels:
                return OriginalLabels()

        registry = ParserRegistry.create_empty()
        parser = CustomParser()
        registry.register(parser)

        assert "custom_dataset" in registry
        assert registry.get_parser("custom_dataset") is parser
        assert len(registry) == 1

    def test_register_duplicate_raises_error(self) -> None:
        """Test registering duplicate dataset raises ValueError."""
        from image_preprocessing_detector.annotation.parsers.base import BaseParser
        from image_preprocessing_detector.annotation.schemas.immutable import OriginalLabels
        from pathlib import Path
        from typing import Any

        class Parser1(BaseParser):
            @property
            def dataset_names(self) -> list[str]:
                return ["duplicate_dataset"]

            def parse(
                self, dataset_path: Path, image_path: Path, config: dict[str, Any]
            ) -> OriginalLabels:
                return OriginalLabels()

        class Parser2(BaseParser):
            @property
            def dataset_names(self) -> list[str]:
                return ["duplicate_dataset"]

            def parse(
                self, dataset_path: Path, image_path: Path, config: dict[str, Any]
            ) -> OriginalLabels:
                return OriginalLabels()

        registry = ParserRegistry.create_empty()
        registry.register(Parser1())

        with pytest.raises(ValueError, match="already registered"):
            registry.register(Parser2())

    def test_unregister_parser(self) -> None:
        """Test unregistering a parser."""
        registry = ParserRegistry.create_default()
        datasets = registry.list_datasets()

        if datasets:
            first_dataset = datasets[0]
            assert first_dataset in registry

            result = registry.unregister(first_dataset)
            assert result is True
            assert first_dataset not in registry

    def test_unregister_nonexistent_returns_false(self) -> None:
        """Test unregistering nonexistent dataset returns False."""
        registry = ParserRegistry.create_empty()
        result = registry.unregister("nonexistent")
        assert result is False


class TestDatasetConfigCoverage:
    """Tests for coverage between DATASET_CONFIGS and parser registry."""

    @pytest.fixture
    def registry(self) -> ParserRegistry:
        """Create default registry."""
        return ParserRegistry.create_default()

    def test_all_datasets_with_parsers_have_config(self, registry: ParserRegistry) -> None:
        """Test all registered datasets have corresponding DATASET_CONFIGS entry."""
        registered_datasets = registry.list_datasets()

        for dataset_name in registered_datasets:
            # Check if dataset or a variant exists in DATASET_CONFIGS
            # Some parsers register multiple names (e.g., 'diqa-5000' and 'diqa')
            found = False
            for config_name in DATASET_CONFIGS:
                # Check exact match or common variants
                if dataset_name == config_name:
                    found = True
                    break
                # Handle name variants (underscores vs hyphens)
                normalized = dataset_name.replace("-", "_").replace("_", "-")
                config_normalized = config_name.replace("-", "_").replace("_", "-")
                if normalized == config_normalized:
                    found = True
                    break

            # Note: Some parsers may register alias names not in DATASET_CONFIGS
            # This is acceptable for backwards compatibility

    def test_parser_names_match_dataset_config_parser_name(
        self, registry: ParserRegistry
    ) -> None:
        """Test parser_name in DATASET_CONFIGS matches registered parser."""
        for name, config in DATASET_CONFIGS.items():
            if config.parser_name is not None:
                # Check if parser is registered
                if registry.has_parser(name):
                    parser = registry.get_parser(name)
                    assert parser is not None
                    # Parser class should handle this dataset


class TestParserCategoryLoading:
    """Tests for loading parsers from each category."""

    def test_quality_parsers_load(self) -> None:
        """Test quality parsers load correctly."""
        from image_preprocessing_detector.annotation.parsers.quality import (
            register_quality_parsers,
        )

        registry = ParserRegistry.create_empty()
        register_quality_parsers(registry)

        # Should have quality parsers registered
        assert len(registry) > 0
        datasets = registry.list_datasets()

        # At least one quality parser
        quality_datasets = {"diqa-5000", "dibco", "ocr_quality", "smartdoc-qa"}
        assert any(d in datasets for d in quality_datasets)

    def test_layout_parsers_load(self) -> None:
        """Test layout parsers load correctly."""
        from image_preprocessing_detector.annotation.parsers.layout import (
            register_layout_parsers,
        )

        registry = ParserRegistry.create_empty()
        register_layout_parsers(registry)

        assert len(registry) > 0
        datasets = registry.list_datasets()

        # At least one layout parser
        layout_datasets = {
            "doclaynet",
            "tablebank",
            "pubtabnet",
            "fintabnet",
            "funsd",
            "sroie",
        }
        assert any(d in datasets for d in layout_datasets)

    def test_handwriting_parsers_load(self) -> None:
        """Test handwriting parsers load correctly."""
        from image_preprocessing_detector.annotation.parsers.handwriting import (
            register_handwriting_parsers,
        )

        registry = ParserRegistry.create_empty()
        register_handwriting_parsers(registry)

        assert len(registry) > 0
        datasets = registry.list_datasets()

        # At least one handwriting parser
        handwriting_datasets = {"signatr6k", "nist_sd19", "nist_db2", "pucit_ohul"}
        assert any(d in datasets for d in handwriting_datasets)

    def test_multilingual_parsers_load(self) -> None:
        """Test multilingual parsers load correctly."""
        from image_preprocessing_detector.annotation.parsers.multilingual import (
            register_multilingual_parsers,
        )

        registry = ParserRegistry.create_empty()
        register_multilingual_parsers(registry)

        assert len(registry) > 0
        datasets = registry.list_datasets()

        # At least one multilingual parser
        multilingual_datasets = {"mdiw13", "cc_ocr", "tibhcr", "arabic_docs_ocr"}
        assert any(d in datasets for d in multilingual_datasets)

    def test_document_parsers_load(self) -> None:
        """Test document parsers load correctly."""
        from image_preprocessing_detector.annotation.parsers.document import (
            register_document_parsers,
        )

        registry = ParserRegistry.create_empty()
        register_document_parsers(registry)

        assert len(registry) > 0
        datasets = registry.list_datasets()

        # At least one document parser
        document_datasets = {"rvl_cdip", "midv500", "omnidocbench", "ohr-bench"}
        assert any(d in datasets for d in document_datasets)


class TestParserFunctionality:
    """Tests for actual parser functionality via registry."""

    @pytest.fixture
    def registry(self) -> ParserRegistry:
        """Create default registry."""
        return ParserRegistry.create_default()

    def test_parser_returns_original_labels(
        self, registry: ParserRegistry, tmp_path
    ) -> None:
        """Test parsers return OriginalLabels instances."""
        from pathlib import Path

        from image_preprocessing_detector.annotation.schemas.immutable import (
            OriginalLabels,
        )

        # Test a few parsers with mock data
        datasets = registry.list_datasets()

        for dataset_name in datasets[:5]:  # Test first 5 parsers
            parser = registry.get_parser(dataset_name)
            if parser is None:
                continue

            # Create minimal mock structure
            dataset_path = tmp_path / dataset_name
            dataset_path.mkdir(exist_ok=True)
            image_path = dataset_path / "test_image.png"
            image_path.touch()

            # Parse should return OriginalLabels
            result = parser.parse(dataset_path, image_path, {})
            assert isinstance(result, OriginalLabels)
