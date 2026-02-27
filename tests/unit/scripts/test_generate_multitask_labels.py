"""Unit tests for the multi-task pseudo-labeling pipeline.

Tests cover:
- Shannon entropy computation for classification distributions
- Regression uncertainty flagging
- Label record generation from MultiTaskPrediction
- Image file discovery
- List chunking for parallel processing
- CLI argument parsing
- Active learning flag logic
"""

from __future__ import annotations

# Import script module functions via importlib since scripts/ is not a package
import importlib.util
import json
import math
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[3] / "scripts" / "generate_multitask_labels.py"
)
_spec = importlib.util.spec_from_file_location(
    "generate_multitask_labels", _SCRIPT_PATH
)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

_compute_classification_entropy = _mod._compute_classification_entropy
_compute_regression_uncertainty_flag = _mod._compute_regression_uncertainty_flag
_prediction_to_label_record = _mod._prediction_to_label_record
_find_images = _mod._find_images
_chunk_list = _mod._chunk_list
build_parser = _mod.build_parser
DEFAULT_ENTROPY_THRESHOLD = _mod.DEFAULT_ENTROPY_THRESHOLD
IMAGE_EXTENSIONS = _mod.IMAGE_EXTENSIONS


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_prediction() -> MagicMock:
    """Create a mock MultiTaskPrediction with realistic values."""
    pred = MagicMock()

    # IQA scores
    pred.iqa_overall.mu = 0.80
    pred.iqa_overall.sigma_sq = 0.04
    pred.iqa_sharpness.mu = 0.85
    pred.iqa_sharpness.sigma_sq = 0.03
    pred.iqa_color.mu = 0.70
    pred.iqa_color.sigma_sq = 0.05

    # Script (high confidence)
    pred.script.predicted_class = "LATN"
    pred.script.confidence = 0.95
    pred.script.distribution = {"LATN": 0.95, "CYRL": 0.03, "OTHER": 0.02}

    # Source
    pred.source.predicted_class = "scanned"
    pred.source.confidence = 0.88
    pred.source.distribution = {
        "scanned": 0.88,
        "camera": 0.10,
        "born_digital": 0.02,
    }

    # Orientation
    pred.orientation.predicted_class = "0"
    pred.orientation.confidence = 0.99
    pred.orientation.distribution = {
        "0": 0.99,
        "90": 0.005,
        "180": 0.003,
        "270": 0.002,
    }
    pred.orientation_degrees = 0

    # Regression
    pred.shadow.value = 0.15
    pred.shadow.sigma_sq = 0.01
    pred.warping.value = 0.05
    pred.warping.sigma_sq = 0.02

    # Metadata
    pred.inference_time_ms = 42.5
    pred.device = "cpu"

    return pred


@pytest.fixture
def uncertain_prediction() -> MagicMock:
    """Create a mock prediction with high uncertainty (for active learning)."""
    pred = MagicMock()

    pred.iqa_overall.mu = 0.50
    pred.iqa_overall.sigma_sq = 0.2
    pred.iqa_sharpness.mu = 0.50
    pred.iqa_sharpness.sigma_sq = 0.2
    pred.iqa_color.mu = 0.50
    pred.iqa_color.sigma_sq = 0.2

    # Script: near-uniform distribution → high entropy
    pred.script.predicted_class = "LATN"
    pred.script.confidence = 0.15
    pred.script.distribution = {
        "LATN": 0.15,
        "CYRL": 0.14,
        "GREK": 0.13,
        "ARAB": 0.12,
        "HEBR": 0.11,
        "OTHER": 0.10,
        "UNKNOWN": 0.25,
    }

    pred.source.predicted_class = "camera"
    pred.source.confidence = 0.40
    pred.source.distribution = {
        "scanned": 0.30,
        "camera": 0.40,
        "born_digital": 0.30,
    }

    pred.orientation.predicted_class = "0"
    pred.orientation.confidence = 0.30
    pred.orientation.distribution = {
        "0": 0.30,
        "90": 0.25,
        "180": 0.25,
        "270": 0.20,
    }
    pred.orientation_degrees = 0

    pred.shadow.value = 0.50
    pred.shadow.sigma_sq = 0.5  # High uncertainty
    pred.warping.value = 0.50
    pred.warping.sigma_sq = 0.5  # High uncertainty

    pred.inference_time_ms = 55.0
    pred.device = "cpu"

    return pred


@pytest.fixture
def image_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with test images."""
    for name in ("doc1.jpg", "doc2.png", "doc3.tiff"):
        (tmp_path / name).write_bytes(b"\x00" * 100)
    # Non-image files should be ignored
    (tmp_path / "readme.txt").write_text("not an image")
    (tmp_path / "data.csv").write_text("col1,col2")
    # Subdirectory with images
    sub = tmp_path / "subdir"
    sub.mkdir()
    (sub / "doc4.jpeg").write_bytes(b"\x00" * 100)
    return tmp_path


# ============================================================================
# Test entropy computation
# ============================================================================


class TestClassificationEntropy:
    """Tests for _compute_classification_entropy."""

    def test_uniform_distribution(self) -> None:
        """Uniform distribution has maximum entropy."""
        dist = {"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25}
        entropy = _compute_classification_entropy(dist)
        expected = -4 * 0.25 * math.log(0.25)
        assert entropy == pytest.approx(expected, abs=1e-6)

    def test_degenerate_distribution(self) -> None:
        """Single-class distribution has zero entropy."""
        dist = {"A": 1.0, "B": 0.0, "C": 0.0}
        entropy = _compute_classification_entropy(dist)
        assert entropy == pytest.approx(0.0, abs=1e-6)

    def test_binary_half_half(self) -> None:
        """50/50 binary distribution has ln(2) entropy."""
        dist = {"A": 0.5, "B": 0.5}
        entropy = _compute_classification_entropy(dist)
        assert entropy == pytest.approx(math.log(2), abs=1e-6)

    def test_high_confidence(self) -> None:
        """High-confidence distribution has low entropy."""
        dist = {"LATN": 0.95, "OTHER": 0.05}
        entropy = _compute_classification_entropy(dist)
        assert entropy < 0.3

    def test_empty_distribution(self) -> None:
        """Empty distribution has zero entropy."""
        entropy = _compute_classification_entropy({})
        assert entropy == 0.0

    def test_entropy_increases_with_uncertainty(self) -> None:
        """More uniform distributions have higher entropy."""
        confident = {"A": 0.9, "B": 0.1}
        uncertain = {"A": 0.5, "B": 0.5}
        assert _compute_classification_entropy(
            confident
        ) < _compute_classification_entropy(uncertain)


# ============================================================================
# Test regression uncertainty flagging
# ============================================================================


class TestRegressionUncertaintyFlag:
    """Tests for _compute_regression_uncertainty_flag."""

    def test_low_uncertainty_not_flagged(self) -> None:
        """Low sigma_sq below threshold is not flagged."""
        assert not _compute_regression_uncertainty_flag(0.05, threshold=0.1)

    def test_high_uncertainty_flagged(self) -> None:
        """High sigma_sq above threshold is flagged."""
        assert _compute_regression_uncertainty_flag(0.5, threshold=0.1)

    def test_exact_threshold_not_flagged(self) -> None:
        """Exactly at threshold is not flagged (strict >)."""
        assert not _compute_regression_uncertainty_flag(0.1, threshold=0.1)

    def test_custom_threshold(self) -> None:
        """Custom threshold works correctly."""
        assert _compute_regression_uncertainty_flag(0.3, threshold=0.2)
        assert not _compute_regression_uncertainty_flag(0.1, threshold=0.2)


# ============================================================================
# Test label record generation
# ============================================================================


class TestPredictionToLabelRecord:
    """Tests for _prediction_to_label_record."""

    def test_basic_structure(
        self,
        sample_prediction: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Label record has expected top-level keys."""
        image_path = tmp_path / "doc1.jpg"
        record = _prediction_to_label_record(
            image_path,
            tmp_path,
            sample_prediction,
            DEFAULT_ENTROPY_THRESHOLD,
        )
        assert "image_path" in record
        assert "predictions" in record
        assert "active_learning" in record
        assert "inference_time_ms" in record
        assert "device" in record

    def test_relative_path(
        self,
        sample_prediction: MagicMock,
        tmp_path: Path,
    ) -> None:
        """image_path is relative to input_dir."""
        image_path = tmp_path / "subdir" / "doc1.jpg"
        record = _prediction_to_label_record(
            image_path,
            tmp_path,
            sample_prediction,
            DEFAULT_ENTROPY_THRESHOLD,
        )
        assert record["image_path"] == "subdir/doc1.jpg"

    def test_predictions_contain_all_tasks(
        self,
        sample_prediction: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Predictions section has all 8 tasks."""
        record = _prediction_to_label_record(
            tmp_path / "doc.jpg",
            tmp_path,
            sample_prediction,
            DEFAULT_ENTROPY_THRESHOLD,
        )
        preds = record["predictions"]
        assert "iqa" in preds
        assert "script" in preds
        assert "source" in preds
        assert "orientation" in preds
        assert "shadow" in preds
        assert "warping" in preds

    def test_iqa_nested_structure(
        self,
        sample_prediction: MagicMock,
        tmp_path: Path,
    ) -> None:
        """IQA predictions have mu and sigma_sq for all dimensions."""
        record = _prediction_to_label_record(
            tmp_path / "doc.jpg",
            tmp_path,
            sample_prediction,
            DEFAULT_ENTROPY_THRESHOLD,
        )
        iqa = record["predictions"]["iqa"]
        for dim in ("overall", "sharpness", "color"):
            assert "mu" in iqa[dim]
            assert "sigma_sq" in iqa[dim]

    def test_classification_has_distribution(
        self,
        sample_prediction: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Classification predictions include full softmax distribution."""
        record = _prediction_to_label_record(
            tmp_path / "doc.jpg",
            tmp_path,
            sample_prediction,
            DEFAULT_ENTROPY_THRESHOLD,
        )
        script = record["predictions"]["script"]
        assert "distribution" in script
        assert "entropy" in script
        assert isinstance(script["distribution"], dict)

    def test_confident_prediction_not_flagged(
        self,
        sample_prediction: MagicMock,
        tmp_path: Path,
    ) -> None:
        """High-confidence prediction is not flagged for active learning."""
        record = _prediction_to_label_record(
            tmp_path / "doc.jpg",
            tmp_path,
            sample_prediction,
            DEFAULT_ENTROPY_THRESHOLD,
        )
        assert not record["active_learning"]["flagged"]

    def test_uncertain_prediction_flagged(
        self,
        uncertain_prediction: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Low-confidence prediction is flagged for active learning."""
        record = _prediction_to_label_record(
            tmp_path / "doc.jpg",
            tmp_path,
            uncertain_prediction,
            entropy_threshold=0.5,
        )
        assert record["active_learning"]["flagged"]

    def test_json_serializable(
        self,
        sample_prediction: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Label record is JSON-serializable."""
        record = _prediction_to_label_record(
            tmp_path / "doc.jpg",
            tmp_path,
            sample_prediction,
            DEFAULT_ENTROPY_THRESHOLD,
        )
        serialized = json.dumps(record)
        assert isinstance(serialized, str)


# ============================================================================
# Test file discovery
# ============================================================================


class TestFindImages:
    """Tests for _find_images."""

    def test_finds_images(self, image_dir: Path) -> None:
        """Finds image files in directory."""
        images = _find_images(image_dir, recursive=False)
        assert len(images) == 3
        extensions = {p.suffix.lower() for p in images}
        assert extensions <= IMAGE_EXTENSIONS

    def test_ignores_non_images(self, image_dir: Path) -> None:
        """Non-image files are excluded."""
        images = _find_images(image_dir, recursive=False)
        names = {p.name for p in images}
        assert "readme.txt" not in names
        assert "data.csv" not in names

    def test_recursive_search(self, image_dir: Path) -> None:
        """Recursive search finds subdirectory images."""
        images = _find_images(image_dir, recursive=True)
        assert len(images) == 4  # 3 top-level + 1 in subdir
        names = {p.name for p in images}
        assert "doc4.jpeg" in names

    def test_non_recursive_excludes_subdirs(self, image_dir: Path) -> None:
        """Non-recursive search skips subdirectories."""
        images = _find_images(image_dir, recursive=False)
        names = {p.name for p in images}
        assert "doc4.jpeg" not in names

    def test_sorted_output(self, image_dir: Path) -> None:
        """Results are sorted by path."""
        images = _find_images(image_dir, recursive=False)
        assert images == sorted(images)

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Empty directory returns empty list."""
        images = _find_images(tmp_path, recursive=False)
        assert images == []


# ============================================================================
# Test list chunking
# ============================================================================


class TestChunkList:
    """Tests for _chunk_list."""

    def test_even_split(self) -> None:
        """List splits evenly."""
        chunks = _chunk_list(list(range(10)), 2)
        assert len(chunks) == 2
        assert all(len(c) == 5 for c in chunks)

    def test_uneven_split(self) -> None:
        """Uneven split puts remainder in last chunk."""
        chunks = _chunk_list(list(range(7)), 3)
        total = sum(len(c) for c in chunks)
        assert total == 7

    def test_more_chunks_than_items(self) -> None:
        """More chunks than items creates single-item chunks."""
        chunks = _chunk_list([1, 2], 5)
        total = sum(len(c) for c in chunks)
        assert total == 2

    def test_single_chunk(self) -> None:
        """Single chunk returns full list."""
        chunks = _chunk_list(list(range(5)), 1)
        assert len(chunks) == 1
        assert chunks[0] == list(range(5))

    def test_preserves_all_items(self) -> None:
        """All items preserved after chunking."""
        original = list(range(13))
        chunks = _chunk_list(original, 4)
        flattened = [item for chunk in chunks for item in chunk]
        assert flattened == original


# ============================================================================
# Test CLI parser
# ============================================================================


class TestBuildParser:
    """Tests for argument parser configuration."""

    def test_required_args(self) -> None:
        """Parser requires input-dir, checkpoint, and output-json."""
        parser = build_parser()
        args = parser.parse_args(
            [
                "--input-dir",
                "/tmp/images",
                "--checkpoint",
                "/tmp/model.pt",
                "--output-json",
                "/tmp/output.json",
            ]
        )
        assert args.input_dir == Path("/tmp/images")
        assert args.checkpoint == Path("/tmp/model.pt")
        assert args.output_json == Path("/tmp/output.json")

    def test_defaults(self) -> None:
        """Optional args have correct defaults."""
        parser = build_parser()
        args = parser.parse_args(
            [
                "--input-dir",
                "/tmp/images",
                "--checkpoint",
                "/tmp/model.pt",
                "--output-json",
                "/tmp/output.json",
            ]
        )
        assert args.device is None
        assert args.entropy_threshold == DEFAULT_ENTROPY_THRESHOLD
        assert args.workers == 1
        assert not args.recursive
        assert not args.verbose

    def test_all_options(self) -> None:
        """All optional args are accepted."""
        parser = build_parser()
        args = parser.parse_args(
            [
                "--input-dir",
                "/tmp/images",
                "--checkpoint",
                "/tmp/model.pt",
                "--output-json",
                "/tmp/output.json",
                "--device",
                "cuda",
                "--entropy-threshold",
                "2.0",
                "--workers",
                "4",
                "--recursive",
                "--verbose",
            ]
        )
        assert args.device == "cuda"
        assert args.entropy_threshold == 2.0
        assert args.workers == 4
        assert args.recursive
        assert args.verbose
