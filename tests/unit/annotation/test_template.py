# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for parser template generation.

Tests the template generator module that creates boilerplate
for new dataset parsers.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from image_preprocessing_detector.annotation.parsers.template import (
    PARSER_TEMPLATE,
    DatasetInfo,
    ParserCategory,
    generate_config_entry,
    generate_parser,
    generate_test_stub,
    validate_dataset_info,
)


class TestDatasetInfo:
    """Tests for DatasetInfo dataclass."""

    def test_get_class_name_simple(self) -> None:
        """Test class name generation for simple dataset names."""
        info = DatasetInfo(dataset_name="diqa")
        assert info.get_class_name() == "DiqaParser"

    def test_get_class_name_with_numbers(self) -> None:
        """Test class name generation with numbers."""
        info = DatasetInfo(dataset_name="diqa-5000")
        assert info.get_class_name() == "Diqa5000Parser"

    def test_get_class_name_with_underscores(self) -> None:
        """Test class name generation with underscores."""
        info = DatasetInfo(dataset_name="nist_sd19")
        assert info.get_class_name() == "NistSd19Parser"

    def test_get_class_name_mixed_case(self) -> None:
        """Test class name generation normalizes case."""
        info = DatasetInfo(dataset_name="DocLayNet")
        assert info.get_class_name() == "DoclaynetParser"

    def test_get_dataset_slug_simple(self) -> None:
        """Test slug generation for simple names."""
        info = DatasetInfo(dataset_name="DIQA")
        assert info.get_dataset_slug() == "diqa"

    def test_get_dataset_slug_with_spaces(self) -> None:
        """Test slug generation handles spaces."""
        info = DatasetInfo(dataset_name="My Dataset Name")
        assert info.get_dataset_slug() == "my-dataset-name"

    def test_get_dataset_slug_with_special_chars(self) -> None:
        """Test slug generation handles special characters."""
        info = DatasetInfo(dataset_name="DIQA (v2.0)")
        assert info.get_dataset_slug() == "diqa-v2-0"

    def test_get_module_name(self) -> None:
        """Test module name generation."""
        info = DatasetInfo(dataset_name="diqa-5000")
        assert info.get_module_name() == "diqa_5000"

    def test_default_values(self) -> None:
        """Test default values are set correctly."""
        info = DatasetInfo(dataset_name="test")
        assert info.category == ParserCategory.DOCUMENT
        assert info.capture_method == "UNKNOWN"
        assert info.has_human_mos is False
        assert info.has_table is None


class TestGenerateParser:
    """Tests for generate_parser function."""

    def test_generates_file(self, tmp_path: Path) -> None:
        """Test that parser file is generated."""
        info = DatasetInfo(
            dataset_name="test-dataset",
            category=ParserCategory.QUALITY,
        )

        output = generate_parser(info, tmp_path)

        assert output.exists()
        assert output.name == "test_dataset.py"

    def test_file_content_has_class(self, tmp_path: Path) -> None:
        """Test generated file contains parser class."""
        info = DatasetInfo(dataset_name="test-dataset")
        output = generate_parser(info, tmp_path)

        content = output.read_text()
        assert "class TestDatasetParser(BaseParser):" in content

    def test_file_content_has_dataset_names(self, tmp_path: Path) -> None:
        """Test generated file has correct dataset names property."""
        info = DatasetInfo(dataset_name="test-dataset")
        output = generate_parser(info, tmp_path)

        content = output.read_text()
        assert 'return ["test-dataset"]' in content

    def test_file_content_has_docstring(self, tmp_path: Path) -> None:
        """Test generated file has docstring with metadata."""
        info = DatasetInfo(
            dataset_name="test-dataset",
            url="https://example.com",
            license="MIT",
            domain="FORMS",
        )
        output = generate_parser(info, tmp_path)

        content = output.read_text()
        assert "Source: https://example.com" in content
        assert "License: MIT" in content
        assert "Domain: FORMS" in content

    def test_raises_on_existing_file(self, tmp_path: Path) -> None:
        """Test raises FileExistsError if file exists."""
        info = DatasetInfo(dataset_name="test")
        output_file = tmp_path / "test.py"
        output_file.write_text("existing content")

        with pytest.raises(FileExistsError):
            generate_parser(info, tmp_path)

    def test_overwrite_flag(self, tmp_path: Path) -> None:
        """Test overwrite=True replaces existing file."""
        info = DatasetInfo(dataset_name="test")
        output_file = tmp_path / "test.py"
        output_file.write_text("old content")

        output = generate_parser(info, tmp_path, overwrite=True)

        content = output.read_text()
        assert "old content" not in content
        assert "class TestParser" in content

    def test_creates_output_dir(self, tmp_path: Path) -> None:
        """Test creates output directory if missing."""
        info = DatasetInfo(dataset_name="test")
        nested_dir = tmp_path / "nested" / "dir"

        output = generate_parser(info, nested_dir)

        assert output.exists()
        assert nested_dir.exists()

    def test_validates_dataset_name_required(self) -> None:
        """Test raises ValueError if dataset_name empty."""
        info = DatasetInfo(dataset_name="")

        with pytest.raises(ValueError, match="dataset_name is required"):
            generate_parser(info, Path("/tmp"))


class TestGenerateConfigEntry:
    """Tests for generate_config_entry function."""

    def test_generates_config_code(self) -> None:
        """Test generates valid config code."""
        info = DatasetInfo(
            dataset_name="test-dataset",
            domain="FORMS",
        )

        code = generate_config_entry(info)

        assert "DatasetConfig(" in code
        assert 'name="test-dataset"' in code
        assert "DomainLevel1.FORMS" in code

    def test_includes_content_flags(self) -> None:
        """Test content flags are included when set."""
        info = DatasetInfo(
            dataset_name="test",
            has_table=True,
            has_formula=False,
        )

        code = generate_config_entry(info)

        assert "has_table=True" in code
        assert "has_formula=False" in code

    def test_excludes_none_flags(self) -> None:
        """Test None content flags are not included."""
        info = DatasetInfo(
            dataset_name="test",
            has_table=None,
        )

        code = generate_config_entry(info)

        assert "has_table" not in code

    def test_includes_multilingual_fields(self) -> None:
        """Test multilingual fields are included."""
        info = DatasetInfo(
            dataset_name="arabic-docs",
            iso639_language="ar",
            iso15924_script="Arab",
        )

        code = generate_config_entry(info)

        assert 'iso639_language="ar"' in code
        assert 'iso15924_script="Arab"' in code

    def test_custom_path_suffix(self) -> None:
        """Test custom path suffix is used."""
        info = DatasetInfo(dataset_name="test")

        code = generate_config_entry(info, path_suffix="custom/path")

        assert 'path_suffix="custom/path"' in code

    def test_auto_path_suffix_benchmark(self) -> None:
        """Test auto-generated path suffix for benchmark."""
        info = DatasetInfo(
            dataset_name="diqa",
            category=ParserCategory.QUALITY,
        )

        code = generate_config_entry(info)

        assert "02_benchmark_only/diqa" in code


class TestGenerateTestStub:
    """Tests for generate_test_stub function."""

    def test_generates_test_class(self) -> None:
        """Test generates test class."""
        info = DatasetInfo(dataset_name="test-dataset")

        code = generate_test_stub(info)

        assert "class TestTestDatasetParser:" in code

    def test_has_fixture(self) -> None:
        """Test has parser fixture."""
        info = DatasetInfo(dataset_name="test")

        code = generate_test_stub(info)

        assert "@pytest.fixture" in code
        assert "def parser(self)" in code

    def test_has_basic_tests(self) -> None:
        """Test has basic test methods."""
        info = DatasetInfo(dataset_name="test")

        code = generate_test_stub(info)

        assert "def test_dataset_names" in code
        assert "def test_parse_returns_original_labels" in code
        assert "def test_supports_batch_default" in code

    def test_correct_import_path(self) -> None:
        """Test import path matches category."""
        info = DatasetInfo(
            dataset_name="test",
            category=ParserCategory.LAYOUT,
        )

        code = generate_test_stub(info)

        assert "annotation.parsers.layout.test" in code


class TestValidateDatasetInfo:
    """Tests for validate_dataset_info function."""

    def test_empty_name_is_error(self) -> None:
        """Test empty name produces error."""
        info = DatasetInfo(dataset_name="")

        warnings = validate_dataset_info(info)

        assert any("dataset_name is required" in w for w in warnings)
        assert any("ERROR" in w for w in warnings)

    def test_todo_url_is_warning(self) -> None:
        """Test TODO URL produces warning."""
        info = DatasetInfo(
            dataset_name="test",
            url="TODO: Add URL",
        )

        warnings = validate_dataset_info(info)

        assert any("url not set" in w for w in warnings)
        assert any("WARNING" in w for w in warnings)

    def test_todo_license_is_warning(self) -> None:
        """Test TODO license produces warning."""
        info = DatasetInfo(
            dataset_name="test",
            license="TODO: Check license",
        )

        warnings = validate_dataset_info(info)

        assert any("license not set" in w for w in warnings)

    def test_general_domain_is_info(self) -> None:
        """Test GENERAL domain produces info."""
        info = DatasetInfo(
            dataset_name="test",
            url="https://example.com",
            license="MIT",
            domain="GENERAL",
        )

        warnings = validate_dataset_info(info)

        assert any("domain is GENERAL" in w for w in warnings)
        assert any("INFO" in w for w in warnings)

    def test_complete_info_minimal_warnings(self) -> None:
        """Test complete info has minimal warnings."""
        info = DatasetInfo(
            dataset_name="test",
            url="https://example.com",
            license="MIT",
            domain="FORMS",
            sample_count="5000",
            label_description="CSV with quality scores",
        )

        warnings = validate_dataset_info(info)

        errors = [w for w in warnings if "ERROR" in w]
        assert len(errors) == 0


class TestParserTemplate:
    """Tests for PARSER_TEMPLATE constant."""

    def test_template_has_placeholders(self) -> None:
        """Test template has expected placeholders."""
        # The template should have these variables
        expected = [
            "${dataset_name}",
            "${class_name}",
            "${dataset_slug}",
            "${url}",
            "${license}",
            "${domain}",
        ]

        for placeholder in expected:
            assert placeholder in PARSER_TEMPLATE.template

    def test_template_substitution_works(self) -> None:
        """Test template substitution produces valid Python."""
        content = PARSER_TEMPLATE.substitute(
            dataset_name="Test",
            class_name="TestParser",
            dataset_slug="test",
            url="https://example.com",
            license="MIT",
            domain="GENERAL",
            sample_count="100",
            label_description="Test labels",
        )

        # Should be valid Python syntax
        compile(content, "<test>", "exec")
