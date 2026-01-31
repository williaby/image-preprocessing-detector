# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser template generator for new datasets.

This module provides utilities for generating parser boilerplate when adding
new datasets to the annotation system. It creates properly structured parser
classes that follow project conventions.

Features:
    - Generate parser class from template
    - Generate dataset config entry
    - Validate required fields
    - Support for different parser categories (quality, layout, etc.)

Example:
    >>> from image_preprocessing_detector.annotation.parsers.template import (
    ...     generate_parser,
    ...     ParserCategory,
    ...     DatasetInfo,
    ... )
    >>>
    >>> info = DatasetInfo(
    ...     dataset_name="my-dataset",
    ...     url="https://example.com/my-dataset",
    ...     license="Apache-2.0",
    ...     domain="FORMS",
    ...     sample_count="10000",
    ...     label_description="CSV with quality scores",
    ...     category=ParserCategory.QUALITY,
    ... )
    >>>
    >>> output_path = generate_parser(info, Path("./parsers/quality"))
    >>> print(f"Generated: {output_path}")
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from string import Template
from typing import Any


class ParserCategory(Enum):
    """Category of parser determines output directory and base patterns.

    Attributes:
        QUALITY: Quality assessment datasets (DIQA, SmartDoc, etc.)
        LAYOUT: Layout annotation datasets (DocLayNet, FUNSD, etc.)
        HANDWRITING: Handwriting/signature datasets
        MULTILINGUAL: Script/language datasets
        DOCUMENT: General document datasets
    """

    QUALITY = "quality"
    LAYOUT = "layout"
    HANDWRITING = "handwriting"
    MULTILINGUAL = "multilingual"
    DOCUMENT = "document"


@dataclass
class DatasetInfo:
    """Information needed to generate a parser template.

    Attributes:
        dataset_name: Human-readable dataset name (e.g., "DIQA-5000")
        url: Dataset source URL
        license: License type (e.g., "Apache-2.0", "CC-BY-4.0")
        domain: Primary domain category (maps to DomainLevel1 enum)
        sample_count: Approximate number of samples (e.g., "5000", "~10K")
        label_description: Description of label/annotation format
        category: Parser category for directory placement
        capture_method: How documents were captured (default: UNKNOWN)
        has_human_mos: Whether dataset has human Mean Opinion Scores
        has_table: Known table content (True/False/None)
        has_formula: Known formula content (True/False/None)
        has_handwriting: Known handwriting content (True/False/None)
        has_signature: Known signature content (True/False/None)
        has_coco_annotations: Whether annotations are in COCO format
        iso639_language: Language code for multilingual datasets
        iso15924_script: Script code for script identification datasets
    """

    dataset_name: str
    url: str = "TODO: Add dataset URL"
    license: str = "TODO: Check license"
    domain: str = "GENERAL"
    sample_count: str = "TODO"
    label_description: str = "TODO: Describe the annotation format"
    category: ParserCategory = ParserCategory.DOCUMENT
    capture_method: str = "UNKNOWN"
    has_human_mos: bool = False
    has_table: bool | None = None
    has_formula: bool | None = None
    has_handwriting: bool | None = None
    has_signature: bool | None = None
    has_coco_annotations: bool = False
    iso639_language: str | None = None
    iso15924_script: str | None = None
    extra_fields: dict[str, Any] = field(default_factory=dict)

    def get_class_name(self) -> str:
        """Generate Python class name from dataset name.

        Returns:
            PascalCase class name (e.g., "DIQA5000" -> "Diqa5000Parser")
        """
        # Remove special characters, capitalize each word
        clean = re.sub(r"[^a-zA-Z0-9]", " ", self.dataset_name)
        parts = clean.split()
        class_name = "".join(p.title() for p in parts)
        return f"{class_name}Parser"

    def get_dataset_slug(self) -> str:
        """Generate URL-safe dataset slug.

        Returns:
            Lowercase hyphenated slug (e.g., "diqa-5000")
        """
        slug = self.dataset_name.lower()
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        return slug.strip("-")

    def get_module_name(self) -> str:
        """Generate Python module name.

        Returns:
            Lowercase underscore name (e.g., "diqa_5000")
        """
        slug = self.get_dataset_slug()
        return slug.replace("-", "_")

    def validate_script_code(self) -> tuple[bool, str | None]:
        """Validate ISO 15924 script code if provided.

        Uses the three-tier script architecture validation:
        - Tier 1: Validates against ISO15924Script enum
        - Provides suggestions for common errors (case, legacy names)

        Returns:
            Tuple of (is_valid, error_or_suggestion_message)
            Returns (True, None) if no script code set or code is valid

        Example:
            >>> info = DatasetInfo(dataset_name="test", iso15924_script="Latn")
            >>> info.validate_script_code()
            (True, None)
            >>> info = DatasetInfo(dataset_name="test", iso15924_script="latin")
            >>> info.validate_script_code()
            (False, "Try 'Latn' (normalized from 'latin')")
        """
        if not self.iso15924_script:
            return True, None

        # Import here to avoid circular imports
        from image_preprocessing_detector.schema_utils.iso_language_script import (
            validate_script_code_for_ml,
        )

        return validate_script_code_for_ml(self.iso15924_script)


# Parser class template with all required boilerplate
PARSER_TEMPLATE = Template('''# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for ${dataset_name} dataset.

Dataset Information:
    - Source: ${url}
    - License: ${license}
    - Domain: ${domain}
    - Samples: ${sample_count}

Label Format:
    ${label_description}

Dataset Structure:
    ${dataset_slug}/
        TODO: Document actual structure
        annotations/
        images/

Example:
    >>> parser = ${class_name}()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/${dataset_slug}"),
    ...     image_path=Path("/data/${dataset_slug}/images/img001.jpg"),
    ...     config={},
    ... )
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ..base import BaseParser
from ...schemas.immutable import OriginalLabels

logger = logging.getLogger(__name__)


class ${class_name}(BaseParser):
    """Parser for ${dataset_name} dataset.

    ${label_description}
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["${dataset_slug}"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse labels for a single image.

        Args:
            dataset_path: Root path of the ${dataset_name} dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary

        Returns:
            OriginalLabels with extracted fields populated

        Raises:
            No exceptions raised - returns empty OriginalLabels if parsing fails
        """
        labels = OriginalLabels()

        # TODO: Implement parsing logic for your dataset
        #
        # Common patterns:
        #
        # 1. CSV with quality scores:
        #    csv_path = dataset_path / "annotations.csv"
        #    with open(csv_path) as f:
        #        reader = csv.DictReader(f)
        #        for row in reader:
        #            if row["filename"] == image_path.name:
        #                labels.human_mos = float(row["score"])
        #
        # 2. COCO JSON format:
        #    json_path = dataset_path / "annotations.json"
        #    with open(json_path) as f:
        #        coco = json.load(f)
        #    # Find annotations for this image
        #    image_id = self._get_image_id(coco, image_path)
        #    labels.coco_annotations = [a for a in coco["annotations"]
        #                               if a["image_id"] == image_id]
        #
        # 3. Per-image annotation files:
        #    ann_path = image_path.with_suffix(".json")
        #    if ann_path.exists():
        #        with open(ann_path) as f:
        #            labels.raw_labels = json.load(f)
        #
        # 4. Directory-based labels (from folder name):
        #    split_dir = image_path.parent.name
        #    labels.split = split_dir  # "train", "val", "test"

        return labels

    def supports_batch(self) -> bool:
        """Whether this parser supports efficient batch operations.

        Override and return True if your dataset has shared annotation files
        (like a single COCO JSON) where batch loading is more efficient.
        """
        return False

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        """Validate dataset configuration.

        Args:
            config: Dataset configuration to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors: list[str] = []

        # TODO: Add validation for required config fields
        # Example:
        # if "annotation_file" not in config:
        #     errors.append("Missing required 'annotation_file' in config")

        return errors


__all__ = ["${class_name}"]
''')

# Dataset config entry template
CONFIG_TEMPLATE = Template("""    DatasetConfig(
        name="${dataset_slug}",
        path_suffix="${path_suffix}",
        pattern="**/*.${image_ext}",
        capture_method=CaptureMethod.${capture_method},
        domain=DomainLevel1.${domain},
        is_benchmark=${is_benchmark},
        has_human_mos=${has_human_mos},
        parser_name="${parser_name}",${optional_fields}
    ),
""")


def generate_parser(
    info: DatasetInfo,
    output_dir: Path | None = None,
    overwrite: bool = False,
) -> Path:
    """Generate parser template for a new dataset.

    Creates a new parser Python file with all required boilerplate,
    following project conventions and best practices.

    Args:
        info: Dataset information for template substitution
        output_dir: Directory to write parser file. If None, uses default
                    based on category (e.g., parsers/quality/)
        overwrite: If True, overwrite existing file. Default False.

    Returns:
        Path to generated parser file

    Raises:
        FileExistsError: If file exists and overwrite=False
        ValueError: If required info fields are missing

    Example:
        >>> info = DatasetInfo(
        ...     dataset_name="My Dataset",
        ...     category=ParserCategory.QUALITY,
        ... )
        >>> path = generate_parser(info, Path("./parsers/quality"))
    """
    # Validate required fields
    if not info.dataset_name:
        raise ValueError("dataset_name is required")

    # Determine output directory
    if output_dir is None:
        # Default to category subdirectory
        base_dir = Path(__file__).parent
        output_dir = base_dir / info.category.value

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate output filename
    module_name = info.get_module_name()
    output_file = output_dir / f"{module_name}.py"

    # Check for existing file
    if output_file.exists() and not overwrite:
        raise FileExistsError(
            f"Parser file already exists: {output_file}. Use overwrite=True to replace."
        )

    # Substitute template variables
    content = PARSER_TEMPLATE.substitute(
        dataset_name=info.dataset_name,
        class_name=info.get_class_name(),
        dataset_slug=info.get_dataset_slug(),
        url=info.url,
        license=info.license,
        domain=info.domain,
        sample_count=info.sample_count,
        label_description=info.label_description,
    )

    # Write parser file
    output_file.write_text(content)

    return output_file


def generate_config_entry(
    info: DatasetInfo,
    path_suffix: str | None = None,
    image_ext: str = "jpg",
) -> str:
    """Generate DatasetConfig entry for config/datasets.py.

    Args:
        info: Dataset information
        path_suffix: Path suffix relative to e_drive_root.
                     If None, generates based on category and slug.
        image_ext: Image file extension (default: "jpg")

    Returns:
        String containing DatasetConfig instantiation code

    Example:
        >>> info = DatasetInfo(dataset_name="My Dataset", domain="FORMS")
        >>> config_code = generate_config_entry(info)
        >>> print(config_code)
    """
    slug = info.get_dataset_slug()

    # Generate path suffix if not provided
    if path_suffix is None:
        if info.category == ParserCategory.QUALITY:
            path_suffix = f"02_benchmark_only/{slug}"
        else:
            path_suffix = f"01_base_data/{info.category.value}/{slug}"

    # Build optional fields string
    optional_parts = []

    if info.has_table is not None:
        optional_parts.append(f"has_table={info.has_table}")
    if info.has_formula is not None:
        optional_parts.append(f"has_formula={info.has_formula}")
    if info.has_handwriting is not None:
        optional_parts.append(f"has_handwriting={info.has_handwriting}")
    if info.has_signature is not None:
        optional_parts.append(f"has_signature={info.has_signature}")
    if info.has_coco_annotations:
        optional_parts.append("has_coco_annotations=True")
    if info.iso639_language:
        optional_parts.append(f'iso639_language="{info.iso639_language}"')
    if info.iso15924_script:
        optional_parts.append(f'iso15924_script="{info.iso15924_script}"')

    optional_fields = ""
    if optional_parts:
        optional_fields = "\n        " + ",\n        ".join(optional_parts) + ","

    return CONFIG_TEMPLATE.substitute(
        dataset_slug=slug,
        path_suffix=path_suffix,
        image_ext=image_ext,
        capture_method=info.capture_method,
        domain=info.domain,
        is_benchmark=str(info.category == ParserCategory.QUALITY),
        has_human_mos=str(info.has_human_mos),
        parser_name=info.get_module_name(),
        optional_fields=optional_fields,
    )


def generate_test_stub(info: DatasetInfo) -> str:
    """Generate test stub for parser.

    Args:
        info: Dataset information

    Returns:
        String containing pytest test class stub

    Example:
        >>> info = DatasetInfo(dataset_name="My Dataset")
        >>> test_code = generate_test_stub(info)
    """
    class_name = info.get_class_name()
    slug = info.get_dataset_slug()
    module_name = info.get_module_name()
    category = info.category.value

    return f'''"""Tests for {class_name}."""

import pytest
from pathlib import Path

from image_preprocessing_detector.annotation.parsers.{category}.{module_name} import (
    {class_name},
)
from image_preprocessing_detector.annotation.schemas.immutable import OriginalLabels


class Test{class_name}:
    """Test suite for {class_name}."""

    @pytest.fixture
    def parser(self) -> {class_name}:
        """Create parser instance."""
        return {class_name}()

    def test_dataset_names(self, parser: {class_name}) -> None:
        """Test that parser reports correct dataset names."""
        assert "{slug}" in parser.dataset_names

    def test_parse_returns_original_labels(
        self,
        parser: {class_name},
        tmp_path: Path,
    ) -> None:
        """Test that parse returns OriginalLabels instance."""
        # Create minimal test structure
        image_dir = tmp_path / "images"
        image_dir.mkdir()
        image_file = image_dir / "test.jpg"
        image_file.touch()

        result = parser.parse(
            dataset_path=tmp_path,
            image_path=image_file,
            config={{}},
        )

        assert isinstance(result, OriginalLabels)

    def test_supports_batch_default(self, parser: {class_name}) -> None:
        """Test default batch support."""
        # Default should be False unless overridden
        assert parser.supports_batch() is False

    def test_validate_config_empty(self, parser: {class_name}) -> None:
        """Test config validation with empty config."""
        errors = parser.validate_config({{}})
        # TODO: Update based on required config fields
        assert isinstance(errors, list)
'''


def validate_dataset_info(info: DatasetInfo) -> list[str]:
    """Validate DatasetInfo for completeness.

    Args:
        info: Dataset info to validate

    Returns:
        List of validation warnings/errors
    """
    warnings = []

    if not info.dataset_name:
        warnings.append("ERROR: dataset_name is required")

    if info.url.startswith("TODO"):
        warnings.append("WARNING: url not set (starts with TODO)")

    if info.license.startswith("TODO"):
        warnings.append("WARNING: license not set (starts with TODO)")

    if info.sample_count == "TODO":
        warnings.append("WARNING: sample_count not set")

    if info.label_description.startswith("TODO"):
        warnings.append("WARNING: label_description not set")

    if info.domain == "GENERAL":
        warnings.append("INFO: domain is GENERAL (consider being more specific)")

    # Validate ISO 15924 script code if provided
    if info.iso15924_script:
        is_valid, message = info.validate_script_code()
        if not is_valid and message:
            warnings.append(f"WARNING: iso15924_script invalid - {message}")

    return warnings


__all__ = [
    "CONFIG_TEMPLATE",
    "PARSER_TEMPLATE",
    "DatasetInfo",
    "ParserCategory",
    "generate_config_entry",
    "generate_parser",
    "generate_test_stub",
    "validate_dataset_info",
]
