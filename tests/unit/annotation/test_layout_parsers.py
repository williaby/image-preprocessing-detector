# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Unit tests for layout annotation parsers.

Tests cover:
    - DocLayNetParser: COCO-format layout annotations (11 classes)
    - TableBankParser: COCO-format table detection
    - PubTabNetParser: JSONL table structure with HTML
    - FinTabNetParser: JSONL financial table structure
    - FunsdParser: Form understanding annotations (dict format)
    - FunsdPlusParser: Extended FUNSD annotations
    - SroieParser: Receipt OCR with quad text boxes
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from image_preprocessing_detector.annotation.parsers.layout import (
    register_layout_parsers,
)
from image_preprocessing_detector.annotation.parsers.layout.doclaynet import (
    DocLayNetParser,
)
from image_preprocessing_detector.annotation.parsers.layout.fintabnet import (
    FinTabNetParser,
)
from image_preprocessing_detector.annotation.parsers.layout.funsd import FunsdParser
from image_preprocessing_detector.annotation.parsers.layout.funsd_plus import (
    FunsdPlusParser,
)
from image_preprocessing_detector.annotation.parsers.layout.pubtabnet import (
    PubTabNetParser,
)
from image_preprocessing_detector.annotation.parsers.layout.sroie import SroieParser
from image_preprocessing_detector.annotation.parsers.layout.tablebank import (
    TableBankParser,
)
from image_preprocessing_detector.annotation.schemas.immutable import OriginalLabels

# ==============================================================================
# DocLayNetParser Tests
# ==============================================================================


class TestDocLayNetParser:
    """Test suite for DocLayNet parser."""

    @pytest.fixture
    def parser(self) -> DocLayNetParser:
        """Create DocLayNetParser instance."""
        return DocLayNetParser()

    @pytest.fixture
    def dataset_path(self, tmp_path: Path) -> Path:
        """Create mock DocLayNet dataset structure."""
        dataset = tmp_path / "doclaynet"
        dataset.mkdir()

        # Create COCO annotations
        coco_dir = dataset / "COCO"
        coco_dir.mkdir()

        coco_data = {
            "images": [
                {"id": 1, "file_name": "doc1234_0.png"},
                {"id": 2, "file_name": "doc1234_1.png"},
            ],
            "annotations": [
                {
                    "id": 1,
                    "image_id": 1,
                    "category_id": 1,
                    "bbox": [100, 200, 300, 50],
                },
                {
                    "id": 2,
                    "image_id": 1,
                    "category_id": 9,
                    "bbox": [100, 300, 400, 200],
                },
                {
                    "id": 3,
                    "image_id": 2,
                    "category_id": 3,
                    "bbox": [50, 100, 200, 30],
                },
            ],
            "categories": [
                {"id": 1, "name": "Caption"},
                {"id": 3, "name": "Formula"},
                {"id": 9, "name": "Table"},
            ],
        }

        train_path = coco_dir / "train.json"
        with open(train_path, "w") as f:
            json.dump(coco_data, f)

        return dataset

    def test_dataset_names(self, parser: DocLayNetParser) -> None:
        """Test dataset_names property."""
        assert parser.dataset_names == ["doclaynet"]

    def test_parse_with_annotations(
        self, parser: DocLayNetParser, dataset_path: Path
    ) -> None:
        """Test parsing image with COCO annotations."""
        image_path = dataset_path / "PNG" / "doc1234_0.png"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert "doclaynet_annotations" in labels.raw_labels
        annotations = labels.raw_labels["doclaynet_annotations"]
        assert len(annotations) == 2
        assert annotations[0]["category_name"] == "Caption"
        assert annotations[1]["category_name"] == "Table"
        assert annotations[0]["bbox"] == [100, 200, 300, 50]

    def test_parse_multiple_images(
        self, parser: DocLayNetParser, dataset_path: Path
    ) -> None:
        """Test parsing different images from same dataset."""
        image_path_1 = dataset_path / "PNG" / "doc1234_0.png"
        labels_1 = parser.parse(dataset_path, image_path_1, {})
        assert len(labels_1.raw_labels["doclaynet_annotations"]) == 2

        image_path_2 = dataset_path / "PNG" / "doc1234_1.png"
        labels_2 = parser.parse(dataset_path, image_path_2, {})
        assert len(labels_2.raw_labels["doclaynet_annotations"]) == 1
        assert (
            labels_2.raw_labels["doclaynet_annotations"][0]["category_name"]
            == "Formula"
        )

    def test_parse_no_annotations(
        self, parser: DocLayNetParser, dataset_path: Path
    ) -> None:
        """Test parsing image with no annotations."""
        image_path = dataset_path / "PNG" / "nonexistent.png"
        labels = parser.parse(dataset_path, image_path, {})

        assert (
            labels.raw_labels is None
            or "doclaynet_annotations" not in labels.raw_labels
        )

    def test_parse_missing_coco_file(
        self, parser: DocLayNetParser, tmp_path: Path
    ) -> None:
        """Test parsing when COCO file is missing."""
        dataset = tmp_path / "empty"
        dataset.mkdir()
        image_path = dataset / "PNG" / "doc001.png"
        labels = parser.parse(dataset, image_path, {})

        assert (
            labels.raw_labels is None
            or "doclaynet_annotations" not in labels.raw_labels
        )


# ==============================================================================
# TableBankParser Tests
# ==============================================================================


class TestTableBankParser:
    """Test suite for TableBank parser."""

    @pytest.fixture
    def parser(self) -> TableBankParser:
        """Create TableBankParser instance."""
        return TableBankParser()

    @pytest.fixture
    def dataset_path(self, tmp_path: Path) -> Path:
        """Create mock TableBank dataset structure."""
        dataset = tmp_path / "tablebank"
        dataset.mkdir()

        # Create annotations directory
        ann_dir = dataset / "Detection" / "annotations"
        ann_dir.mkdir(parents=True)

        coco_data = {
            "images": [
                {"id": 1, "file_name": "table001.png"},
                {"id": 2, "file_name": "table002.png"},
            ],
            "annotations": [
                {
                    "id": 1,
                    "image_id": 1,
                    "category_id": 1,
                    "bbox": [50, 100, 400, 300],
                },
                {
                    "id": 2,
                    "image_id": 1,
                    "category_id": 1,
                    "bbox": [50, 500, 400, 200],
                },
            ],
            "categories": [{"id": 1, "name": "table"}],
        }

        train_path = ann_dir / "train.json"
        with open(train_path, "w") as f:
            json.dump(coco_data, f)

        return dataset

    def test_dataset_names(self, parser: TableBankParser) -> None:
        """Test dataset_names property."""
        assert parser.dataset_names == ["tablebank"]

    def test_parse_with_tables(
        self, parser: TableBankParser, dataset_path: Path
    ) -> None:
        """Test parsing image with table annotations."""
        image_path = dataset_path / "Detection" / "images" / "latex" / "table001.png"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert "tablebank_annotations" in labels.raw_labels
        annotations = labels.raw_labels["tablebank_annotations"]
        assert len(annotations) == 2
        assert annotations[0]["category_name"] == "table"
        assert annotations[0]["bbox"] == [50, 100, 400, 300]


# ==============================================================================
# PubTabNetParser Tests
# ==============================================================================


class TestPubTabNetParser:
    """Test suite for PubTabNet parser."""

    @pytest.fixture
    def parser(self) -> PubTabNetParser:
        """Create PubTabNetParser instance."""
        return PubTabNetParser()

    @pytest.fixture
    def dataset_path(self, tmp_path: Path) -> Path:
        """Create mock PubTabNet dataset structure."""
        dataset = tmp_path / "pubtabnet"
        dataset.mkdir()

        # Create JSONL file
        jsonl_path = dataset / "PubTabNet_2.0.0.jsonl"
        entries = [
            {
                "filename": "PMC1234_table_0.png",
                "split": "train",
                "html": {
                    "structure": {
                        "tokens": [
                            "<thead>",
                            "<tr>",
                            "<td>",
                            "Cell1",
                            "</td>",
                            "</tr>",
                            "</thead>",
                        ]
                    },
                    "cells": [
                        {"tokens": ["Cell1"], "bbox": [10, 20, 100, 50]},
                        {"tokens": ["Cell2"], "bbox": [110, 20, 200, 50]},
                    ],
                },
            },
            {
                "filename": "PMC5678_table_0.png",
                "split": "val",
                "html": {
                    "structure": {"tokens": ["<table>", "</table>"]},
                    "cells": [{"tokens": ["Data"], "bbox": [5, 10, 50, 30]}],
                },
            },
        ]

        with open(jsonl_path, "w") as f:
            f.writelines(json.dumps(entry) + "\n" for entry in entries)

        return dataset

    def test_dataset_names(self, parser: PubTabNetParser) -> None:
        """Test dataset_names property."""
        assert parser.dataset_names == ["pubtabnet"]

    def test_parse_with_html_structure(
        self, parser: PubTabNetParser, dataset_path: Path
    ) -> None:
        """Test parsing image with HTML table structure."""
        image_path = dataset_path / "train" / "PMC1234_table_0.png"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.table_html == "<thead><tr><td>Cell1</td></tr></thead>"
        assert labels.cell_annotations is not None
        assert len(labels.cell_annotations) == 2
        assert labels.cell_annotations[0]["tokens"] == ["Cell1"]
        assert labels.cell_annotations[0]["bbox"] == [10, 20, 100, 50]
        assert labels.raw_labels is not None
        assert labels.raw_labels["split"] == "train"

    def test_parse_different_split(
        self, parser: PubTabNetParser, dataset_path: Path
    ) -> None:
        """Test parsing from different split."""
        image_path = dataset_path / "val" / "PMC5678_table_0.png"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.table_html == "<table></table>"
        assert labels.raw_labels["split"] == "val"

    def test_parse_no_match(self, parser: PubTabNetParser, dataset_path: Path) -> None:
        """Test parsing when no matching entry found."""
        image_path = dataset_path / "train" / "nonexistent.png"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.table_html is None
        assert labels.cell_annotations is None


# ==============================================================================
# FinTabNetParser Tests
# ==============================================================================


class TestFinTabNetParser:
    """Test suite for FinTabNet parser."""

    @pytest.fixture
    def parser(self) -> FinTabNetParser:
        """Create FinTabNetParser instance."""
        return FinTabNetParser()

    @pytest.fixture
    def dataset_path(self, tmp_path: Path) -> Path:
        """Create mock FinTabNet dataset structure."""
        dataset = tmp_path / "fintabnet"
        dataset.mkdir()

        # Create JSONL file
        jsonl_path = dataset / "fintabnet.jsonl"
        entries = [
            {
                "filename": "table_001.png",
                "html": {
                    "structure": {
                        "tokens": [
                            "<table>",
                            "<tr>",
                            "<td>",
                            "Revenue",
                            "</td>",
                            "</tr>",
                            "</table>",
                        ]
                    },
                    "cells": [
                        {"tokens": ["Revenue"], "bbox": [20, 30, 150, 60]},
                        {"tokens": ["$1000"], "bbox": [160, 30, 250, 60]},
                    ],
                },
            }
        ]

        with open(jsonl_path, "w") as f:
            f.writelines(json.dumps(entry) + "\n" for entry in entries)

        return dataset

    def test_dataset_names(self, parser: FinTabNetParser) -> None:
        """Test dataset_names property."""
        assert parser.dataset_names == ["fintabnet"]

    def test_parse_financial_table(
        self, parser: FinTabNetParser, dataset_path: Path
    ) -> None:
        """Test parsing financial table structure."""
        image_path = dataset_path / "images" / "table_001.png"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.table_html == "<table><tr><td>Revenue</td></tr></table>"
        assert labels.cell_annotations is not None
        assert len(labels.cell_annotations) == 2
        assert labels.cell_annotations[0]["tokens"] == ["Revenue"]


# ==============================================================================
# FunsdParser Tests
# ==============================================================================


class TestFunsdParser:
    """Test suite for FUNSD parser."""

    @pytest.fixture
    def parser(self) -> FunsdParser:
        """Create FunsdParser instance."""
        return FunsdParser()

    @pytest.fixture
    def dataset_path(self, tmp_path: Path) -> Path:
        """Create mock FUNSD dataset structure."""
        dataset = tmp_path / "funsd"
        dataset.mkdir()

        # Create training annotations
        train_ann_dir = dataset / "training_data" / "annotations"
        train_ann_dir.mkdir(parents=True)

        funsd_data = {
            "form": [
                {
                    "text": "Company Name",
                    "box": [100, 50, 300, 80],
                    "label": "question",
                    "linking": [[1, 2]],
                    "words": [
                        {"text": "Company", "box": [100, 50, 180, 80]},
                        {"text": "Name", "box": [185, 50, 300, 80]},
                    ],
                },
                {
                    "text": "Acme Corp",
                    "box": [310, 50, 450, 80],
                    "label": "answer",
                    "linking": [[1, 2]],
                    "words": [
                        {"text": "Acme", "box": [310, 50, 380, 80]},
                        {"text": "Corp", "box": [385, 50, 450, 80]},
                    ],
                },
            ]
        }

        ann_path = train_ann_dir / "form001.json"
        with open(ann_path, "w") as f:
            json.dump(funsd_data, f)

        return dataset

    def test_dataset_names(self, parser: FunsdParser) -> None:
        """Test dataset_names property."""
        assert parser.dataset_names == ["funsd"]

    def test_parse_form_annotations(
        self, parser: FunsdParser, dataset_path: Path
    ) -> None:
        """Test parsing FUNSD form annotations."""
        image_path = dataset_path / "training_data" / "images" / "form001.png"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.funsd_annotations is not None
        assert isinstance(labels.funsd_annotations, dict)
        assert "form" in labels.funsd_annotations
        assert len(labels.funsd_annotations["form"]) == 2
        assert labels.funsd_annotations["form"][0]["label"] == "question"
        assert labels.funsd_annotations["form"][0]["text"] == "Company Name"
        assert labels.funsd_annotations["form"][1]["label"] == "answer"

    def test_parse_sets_document_type(
        self, parser: FunsdParser, dataset_path: Path
    ) -> None:
        """Test that parser sets document_type metadata."""
        image_path = dataset_path / "training_data" / "images" / "form001.png"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["document_type"] == "form"
        assert labels.raw_labels["is_scanned"] is True


# ==============================================================================
# FunsdPlusParser Tests
# ==============================================================================


class TestFunsdPlusParser:
    """Test suite for FUNSD+ parser."""

    @pytest.fixture
    def parser(self) -> FunsdPlusParser:
        """Create FunsdPlusParser instance."""
        return FunsdPlusParser()

    @pytest.fixture
    def dataset_path(self, tmp_path: Path) -> Path:
        """Create mock FUNSD+ dataset structure."""
        dataset = tmp_path / "funsd_plus"
        dataset.mkdir()

        # Create annotations
        ann_dir = dataset / "annotations"
        ann_dir.mkdir()

        funsd_data = {
            "form": [
                {
                    "text": "Invoice Number",
                    "box": [50, 100, 200, 130],
                    "label": "question",
                    "linking": [],
                    "words": [{"text": "Invoice", "box": [50, 100, 120, 130]}],
                }
            ]
        }

        ann_path = ann_dir / "invoice001.json"
        with open(ann_path, "w") as f:
            json.dump(funsd_data, f)

        return dataset

    def test_dataset_names(self, parser: FunsdPlusParser) -> None:
        """Test dataset_names property."""
        assert parser.dataset_names == ["funsd_plus", "funsd+"]

    def test_parse_extended_funsd(
        self, parser: FunsdPlusParser, dataset_path: Path
    ) -> None:
        """Test parsing FUNSD+ annotations."""
        image_path = dataset_path / "images" / "invoice001.png"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.funsd_annotations is not None
        assert isinstance(labels.funsd_annotations, dict)
        assert "form" in labels.funsd_annotations
        assert labels.funsd_annotations["form"][0]["text"] == "Invoice Number"


# ==============================================================================
# SroieParser Tests
# ==============================================================================


class TestSroieParser:
    """Test suite for SROIE parser."""

    @pytest.fixture
    def parser(self) -> SroieParser:
        """Create SroieParser instance."""
        return SroieParser()

    @pytest.fixture
    def dataset_path(self, tmp_path: Path) -> Path:
        """Create mock SROIE dataset structure."""
        dataset = tmp_path / "sroie"
        dataset.mkdir()

        # Create train directory
        train_dir = dataset / "train"
        train_dir.mkdir()

        # Create text annotation file
        txt_path = train_dir / "X00001.txt"
        txt_content = """100,50,200,50,200,80,100,80,COMPANY NAME
220,50,400,50,400,80,220,80,Acme Corporation
100,100,180,100,180,130,100,130,Total:
200,100,280,100,280,130,200,130,$99.99
"""
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(txt_content)

        return dataset

    def test_dataset_names(self, parser: SroieParser) -> None:
        """Test dataset_names property."""
        assert parser.dataset_names == ["sroie"]

    def test_parse_receipt_text_boxes(
        self, parser: SroieParser, dataset_path: Path
    ) -> None:
        """Test parsing SROIE receipt text annotations."""
        image_path = dataset_path / "train" / "X00001.jpg"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.text_instances is not None
        assert len(labels.text_instances) == 4
        assert labels.text_instances[0]["bbox"] == [100, 50, 200, 50, 200, 80, 100, 80]
        assert labels.text_instances[0]["text"] == "COMPANY NAME"
        assert labels.text_instances[3]["text"] == "$99.99"

    def test_parse_sets_metadata(self, parser: SroieParser, dataset_path: Path) -> None:
        """Test that parser sets metadata fields."""
        image_path = dataset_path / "train" / "X00001.jpg"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["split"] == "train"
        assert labels.raw_labels["document_type"] == "receipt"

    def test_parse_test_split(self, parser: SroieParser, tmp_path: Path) -> None:
        """Test parsing from test split."""
        dataset = tmp_path / "sroie"
        test_dir = dataset / "test"
        test_dir.mkdir(parents=True)

        txt_path = test_dir / "X99999.txt"
        txt_content = "50,60,150,60,150,90,50,90,Test Receipt\n"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(txt_content)

        image_path = test_dir / "X99999.jpg"
        labels = parser.parse(dataset, image_path, {})

        assert labels.raw_labels["split"] == "test"

    def test_parse_malformed_line(self, parser: SroieParser, tmp_path: Path) -> None:
        """Test parsing with malformed annotation lines."""
        dataset = tmp_path / "sroie"
        train_dir = dataset / "train"
        train_dir.mkdir(parents=True)

        txt_path = train_dir / "X00002.txt"
        txt_content = """100,50,200,50,200,80,100,80,Valid Line
invalid line without coordinates
50,60,150,60,150,90,50,90,Another Valid Line
"""
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(txt_content)

        image_path = train_dir / "X00002.jpg"
        labels = parser.parse(dataset, image_path, {})

        # Should skip malformed line
        assert labels.text_instances is not None
        assert len(labels.text_instances) == 2


# ==============================================================================
# Integration Tests
# ==============================================================================


def test_all_parsers_implement_base_protocol() -> None:
    """Verify all parsers implement the BaseParser protocol correctly."""
    parsers = [
        DocLayNetParser(),
        TableBankParser(),
        PubTabNetParser(),
        FinTabNetParser(),
        FunsdParser(),
        FunsdPlusParser(),
        SroieParser(),
    ]

    for parser in parsers:
        # Must have dataset_names property
        assert hasattr(parser, "dataset_names")
        assert isinstance(parser.dataset_names, list)
        assert len(parser.dataset_names) > 0

        # Must have parse method
        assert hasattr(parser, "parse")
        assert callable(parser.parse)

        # Must have supports_batch method
        assert hasattr(parser, "supports_batch")
        assert callable(parser.supports_batch)

        # Must have parse_batch method
        assert hasattr(parser, "parse_batch")
        assert callable(parser.parse_batch)


def test_parser_returns_original_labels() -> None:
    """Verify all parsers return OriginalLabels instances."""
    parsers = [
        DocLayNetParser(),
        TableBankParser(),
        PubTabNetParser(),
        FinTabNetParser(),
        FunsdParser(),
        FunsdPlusParser(),
        SroieParser(),
    ]

    for parser in parsers:
        # Create minimal test environment
        fake_dataset_path = Path("/fake/dataset")
        fake_image_path = Path("/fake/image.jpg")

        result = parser.parse(fake_dataset_path, fake_image_path, {})

        # Must return OriginalLabels instance
        assert isinstance(result, OriginalLabels)


def test_register_layout_parsers() -> None:
    """Test that register_layout_parsers function exists and can be called."""
    from image_preprocessing_detector.annotation.parsers.registry import ParserRegistry

    registry = ParserRegistry()
    register_layout_parsers(registry)

    # Verify all parsers are registered
    assert len(registry._parsers) >= 7

    # Verify specific parsers are present
    parser_names = [p.dataset_names[0] for p in registry._parsers.values()]
    expected = ["doclaynet", "tablebank", "pubtabnet", "fintabnet", "funsd", "sroie"]
    for name in expected:
        assert name in parser_names
