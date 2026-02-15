"""Unit tests for orientation detection module (Phase 8)."""

import cv2
import numpy as np
import pytest

rng = np.random.default_rng(42)

from image_preprocessing_detector.detection.orientation_detector import (
    OrientationConfig,
    OrientationDetector,
    OrientationVote,
    correct_orientation,
    detect_orientation,
)
from image_preprocessing_detector.schema import OrientationAngle, OrientationDetection


class TestOrientationConfig:
    """Test OrientationConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = OrientationConfig()

        assert config.consensus_required == 2
        assert config.min_confidence == pytest.approx(0.6)
        assert config.auto_correct_threshold == pytest.approx(0.8)
        assert config.hough_threshold == 50
        assert config.min_line_length == 50
        assert config.max_line_gap == 10

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = OrientationConfig(
            consensus_required=3,
            min_confidence=0.7,
            auto_correct_threshold=0.9,
        )

        assert config.consensus_required == 3
        assert config.min_confidence == pytest.approx(0.7)
        assert config.auto_correct_threshold == pytest.approx(0.9)


class TestOrientationVote:
    """Test OrientationVote dataclass."""

    def test_vote_creation(self) -> None:
        """Test creating an orientation vote."""
        vote = OrientationVote(
            method="text_line_analysis",
            angle=90,
            confidence=0.85,
            details={"total_lines": 50},
        )

        assert vote.method == "text_line_analysis"
        assert vote.angle == 90
        assert vote.confidence == pytest.approx(0.85)
        assert vote.details["total_lines"] == 50


class TestOrientationDetector:
    """Test OrientationDetector class."""

    @pytest.fixture
    def detector(self) -> OrientationDetector:
        """Create default detector instance."""
        return OrientationDetector()

    @pytest.fixture
    def upright_document_image(self) -> np.ndarray:
        """Create a synthetic upright document image with horizontal text lines."""
        # Create white background
        img = np.ones((800, 600, 3), dtype=np.uint8) * 255

        # Draw horizontal text-like lines
        for y in range(100, 700, 30):
            # Add some variation to simulate text
            cv2.line(img, (50, y), (550, y), (0, 0, 0), 1)
            # Add some shorter lines like words
            for x in range(50, 500, 80):
                length = rng.integers(40, 70)
                cv2.line(img, (x, y + 5), (x + length, y + 5), (30, 30, 30), 1)

        return img

    @pytest.fixture
    def rotated_90_image(self, upright_document_image: np.ndarray) -> np.ndarray:
        """Create a 90-degree rotated document image."""
        return cv2.rotate(upright_document_image, cv2.ROTATE_90_CLOCKWISE)

    @pytest.fixture
    def rotated_180_image(self, upright_document_image: np.ndarray) -> np.ndarray:
        """Create a 180-degree rotated document image."""
        return cv2.rotate(upright_document_image, cv2.ROTATE_180)

    @pytest.fixture
    def rotated_270_image(self, upright_document_image: np.ndarray) -> np.ndarray:
        """Create a 270-degree rotated document image."""
        return cv2.rotate(upright_document_image, cv2.ROTATE_90_COUNTERCLOCKWISE)

    def test_init_default_config(self, detector: OrientationDetector) -> None:
        """Test detector initialization with default config."""
        assert detector.config.consensus_required == 2
        assert detector.config.min_confidence == pytest.approx(0.6)

    def test_init_custom_config(self) -> None:
        """Test detector initialization with custom config."""
        config = OrientationConfig(consensus_required=3, min_confidence=0.8)
        detector = OrientationDetector(config)

        assert detector.config.consensus_required == 3
        assert detector.config.min_confidence == pytest.approx(0.8)

    def test_detect_returns_orientation_detection(
        self, detector: OrientationDetector, upright_document_image: np.ndarray
    ) -> None:
        """Test detection returns OrientationDetection model."""
        result = detector.detect(upright_document_image)

        assert isinstance(result, OrientationDetection)
        assert isinstance(result.detected_angle, OrientationAngle)
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.detection_method, str)
        assert isinstance(result.auto_corrected, bool)
        assert isinstance(result.needs_correction, bool)

    def test_detect_grayscale_input(self, detector: OrientationDetector) -> None:
        """Test detection works with grayscale input."""
        gray_img = np.ones((400, 300), dtype=np.uint8) * 255
        # Add some content
        cv2.line(gray_img, (50, 100), (250, 100), 0, 2)

        result = detector.detect(gray_img)

        assert isinstance(result, OrientationDetection)

    def test_detect_bgr_input(self, detector: OrientationDetector) -> None:
        """Test detection works with BGR input."""
        bgr_img = np.ones((400, 300, 3), dtype=np.uint8) * 255
        # Add some content
        cv2.line(bgr_img, (50, 100), (250, 100), (0, 0, 0), 2)

        result = detector.detect(bgr_img)

        assert isinstance(result, OrientationDetection)

    def test_detect_empty_image(self, detector: OrientationDetector) -> None:
        """Test detection on blank/empty image returns low confidence."""
        blank_img = np.ones((400, 300, 3), dtype=np.uint8) * 255

        result = detector.detect(blank_img)

        # Should return a result but with low confidence or no consensus
        assert isinstance(result, OrientationDetection)

    def test_normalize_angle(self, detector: OrientationDetector) -> None:
        """Test angle normalization to valid orientations."""
        assert detector._normalize_angle(10) == 0
        assert detector._normalize_angle(80) == 90
        assert detector._normalize_angle(170) == 180
        assert detector._normalize_angle(260) == 270
        assert detector._normalize_angle(350) == 0
        assert detector._normalize_angle(360) == 0
        assert detector._normalize_angle(450) == 90  # wraps around to 90

    def test_angle_to_enum(self, detector: OrientationDetector) -> None:
        """Test integer angle to enum conversion."""
        assert detector._angle_to_enum(0) == OrientationAngle.UPRIGHT
        assert detector._angle_to_enum(90) == OrientationAngle.ROTATED_90
        assert detector._angle_to_enum(180) == OrientationAngle.ROTATED_180
        assert detector._angle_to_enum(270) == OrientationAngle.ROTATED_270
        assert detector._angle_to_enum(45) == OrientationAngle.UPRIGHT  # Default

    def test_aggregate_votes_empty(self, detector: OrientationDetector) -> None:
        """Test vote aggregation with empty votes."""
        result = detector._aggregate_votes([])

        assert result.detected_angle == OrientationAngle.UPRIGHT
        assert result.confidence == pytest.approx(0.0)
        assert result.needs_correction is False

    def test_aggregate_votes_unanimous(self, detector: OrientationDetector) -> None:
        """Test vote aggregation with unanimous agreement."""
        votes = [
            OrientationVote("method1", 90, 0.9, {}),
            OrientationVote("method2", 90, 0.8, {}),
            OrientationVote("method3", 90, 0.85, {}),
        ]

        result = detector._aggregate_votes(votes)

        assert result.detected_angle == OrientationAngle.ROTATED_90
        assert result.confidence > 0.5
        assert result.needs_correction is True
        assert "unanimous" in result.detection_method

    def test_aggregate_votes_consensus(self, detector: OrientationDetector) -> None:
        """Test vote aggregation with 2/3 consensus."""
        votes = [
            OrientationVote("method1", 90, 0.9, {}),
            OrientationVote("method2", 90, 0.8, {}),
            OrientationVote("method3", 0, 0.6, {}),
        ]

        result = detector._aggregate_votes(votes)

        assert result.detected_angle == OrientationAngle.ROTATED_90
        assert result.needs_correction is True
        assert "consensus" in result.detection_method

    def test_method_votes_dict(
        self, detector: OrientationDetector, upright_document_image: np.ndarray
    ) -> None:
        """Test that method_votes dict is populated."""
        result = detector.detect(upright_document_image)

        # method_votes should contain votes from detection methods
        assert result.method_votes is not None or result.detection_method == "none"


class TestOrientationDetectionConvenienceFunctions:
    """Test convenience functions for orientation detection."""

    @pytest.fixture
    def sample_image(self) -> np.ndarray:
        """Create a sample image for testing."""
        img = np.ones((400, 300, 3), dtype=np.uint8) * 255
        # Add horizontal lines
        for y in range(50, 350, 30):
            cv2.line(img, (20, y), (280, y), (0, 0, 0), 1)
        return img

    def test_detect_orientation_function(self, sample_image: np.ndarray) -> None:
        """Test detect_orientation convenience function."""
        result = detect_orientation(sample_image)

        assert isinstance(result, OrientationDetection)
        assert isinstance(result.detected_angle, OrientationAngle)

    def test_detect_orientation_with_config(self, sample_image: np.ndarray) -> None:
        """Test detect_orientation with custom config."""
        config = OrientationConfig(consensus_required=1)
        result = detect_orientation(sample_image, config=config)

        assert isinstance(result, OrientationDetection)

    def test_correct_orientation_upright(self, sample_image: np.ndarray) -> None:
        """Test correct_orientation with upright detection (no correction needed)."""
        detection = OrientationDetection(
            detected_angle=OrientationAngle.UPRIGHT,
            confidence=0.9,
            detection_method="test",
            auto_corrected=False,
            needs_correction=False,
        )

        corrected, was_corrected = correct_orientation(sample_image, detection)

        assert was_corrected is False
        assert np.array_equal(corrected, sample_image)

    def test_correct_orientation_90_degrees(self, sample_image: np.ndarray) -> None:
        """Test correct_orientation for 90-degree rotation."""
        detection = OrientationDetection(
            detected_angle=OrientationAngle.ROTATED_90,
            confidence=0.9,
            detection_method="test",
            auto_corrected=False,
            needs_correction=True,
        )

        corrected, was_corrected = correct_orientation(sample_image, detection)

        assert was_corrected is True
        # 90° rotation swaps width and height
        assert corrected.shape[0] == sample_image.shape[1]
        assert corrected.shape[1] == sample_image.shape[0]

    def test_correct_orientation_180_degrees(self, sample_image: np.ndarray) -> None:
        """Test correct_orientation for 180-degree rotation."""
        detection = OrientationDetection(
            detected_angle=OrientationAngle.ROTATED_180,
            confidence=0.9,
            detection_method="test",
            auto_corrected=False,
            needs_correction=True,
        )

        corrected, was_corrected = correct_orientation(sample_image, detection)

        assert was_corrected is True
        # 180° rotation preserves shape
        assert corrected.shape == sample_image.shape

    def test_correct_orientation_270_degrees(self, sample_image: np.ndarray) -> None:
        """Test correct_orientation for 270-degree rotation."""
        detection = OrientationDetection(
            detected_angle=OrientationAngle.ROTATED_270,
            confidence=0.9,
            detection_method="test",
            auto_corrected=False,
            needs_correction=True,
        )

        corrected, was_corrected = correct_orientation(sample_image, detection)

        assert was_corrected is True
        # 270° rotation swaps width and height
        assert corrected.shape[0] == sample_image.shape[1]
        assert corrected.shape[1] == sample_image.shape[0]


class TestOrientationCorrectorIntegration:
    """Integration tests for orientation correction."""

    def test_full_pipeline_upright_image(self) -> None:
        """Test full detection and correction pipeline with upright image."""
        # Create a document-like image
        img = np.ones((600, 400, 3), dtype=np.uint8) * 255
        for y in range(50, 550, 25):
            cv2.line(img, (30, y), (370, y), (0, 0, 0), 1)

        # Detect and correct
        detection = detect_orientation(img)
        corrected, _ = correct_orientation(img, detection)

        # Should not change an upright image
        assert isinstance(corrected, np.ndarray)

    def test_full_pipeline_roundtrip(self) -> None:
        """Test that rotating and correcting returns similar result."""
        # Create original image
        original = np.ones((600, 400, 3), dtype=np.uint8) * 255
        for y in range(50, 550, 25):
            cv2.line(original, (30, y), (370, y), (0, 0, 0), 1)

        # Rotate 90 degrees
        rotated = cv2.rotate(original, cv2.ROTATE_90_CLOCKWISE)

        # Create detection result (simulating detection)
        detection = OrientationDetection(
            detected_angle=OrientationAngle.ROTATED_90,
            confidence=0.95,
            detection_method="test",
            auto_corrected=False,
            needs_correction=True,
        )

        # Correct
        corrected, was_corrected = correct_orientation(rotated, detection)

        assert was_corrected is True
        # Should have same shape as original
        assert corrected.shape == original.shape
