"""
Unit tests for text detection gate.
"""

import numpy as np
import pytest
from image_preprocessing_detector.detection.text_gate import (
    TextDetectionResult,
    TextGate,
    detect_text,
)


class TestTextDetectionResult:
    """Test TextDetectionResult dataclass."""

    def test_result_creation(self) -> None:
        """Test creating a TextDetectionResult instance."""
        result = TextDetectionResult(
            has_text=True,
            confidence=0.85,
            stroke_density=0.12,
            component_score=0.75,
            edge_score=0.08,
        )

        assert result.has_text is True
        assert result.confidence == 0.85
        assert result.stroke_density == 0.12
        assert result.component_score == 0.75
        assert result.edge_score == 0.08


class TestTextGate:
    """Test TextGate class."""

    def test_init_default_params(self) -> None:
        """Test TextGate initialization with defaults."""
        gate = TextGate()

        assert gate.stroke_threshold == 0.05
        assert gate.min_text_components == 10
        assert gate.edge_threshold_low == 50
        assert gate.edge_threshold_high == 150
        assert gate.min_component_area == 20
        assert gate.max_component_area == 5000
        assert gate.min_aspect_ratio == 0.1
        assert gate.max_aspect_ratio == 10.0

    def test_init_custom_params(self) -> None:
        """Test TextGate initialization with custom parameters."""
        gate = TextGate(
            stroke_threshold=0.10,
            min_text_components=20,
            edge_threshold_low=100,
            edge_threshold_high=200,
        )

        assert gate.stroke_threshold == 0.10
        assert gate.min_text_components == 20
        assert gate.edge_threshold_low == 100
        assert gate.edge_threshold_high == 200

    def test_detect_text_heavy_document(self) -> None:
        """Test detection on text-heavy synthetic document."""
        # Create synthetic text-like image: white background with black text patterns
        img = np.ones((500, 500, 3), dtype=np.uint8) * 255  # White background

        # Add horizontal text-like strokes (simulating lines of text)
        for y in range(50, 450, 30):  # Lines spaced 30 pixels apart
            # Random text-like segments
            for x in range(20, 480, 40):
                width = np.random.randint(20, 35)
                height = np.random.randint(8, 15)
                img[y : y + height, x : x + width] = 0  # Black text

        gate = TextGate()
        result = gate.detect(img)

        # Text should be detected with high confidence
        assert result.has_text is True
        assert result.confidence > 0.3  # Reasonable confidence for synthetic text
        assert result.stroke_density > 0.02  # Should have measurable stroke density
        assert result.component_score > 0.1  # Should have text-like components

    def test_detect_pure_image(self) -> None:
        """Test detection on pure image (no text)."""
        # Create synthetic natural image: smooth gradient (no noise to avoid false positives)
        img = np.zeros((500, 500, 3), dtype=np.uint8)

        # Smooth gradient (sky-like)
        for i in range(500):
            img[i, :] = [int(50 + i * 0.3), int(100 + i * 0.2), int(150 + i * 0.1)]

        gate = TextGate()
        result = gate.detect(img)

        # Smooth gradient should have very low stroke density and few components
        assert result.stroke_density < 0.10  # Low stroke density
        # Note: component_score can vary based on thresholding, so we check confidence
        assert result.confidence < 0.6  # Low overall confidence for pure gradient

    def test_detect_mixed_document(self) -> None:
        """Test detection on mixed document (text + images)."""
        # Create synthetic mixed document
        img = np.ones((800, 600, 3), dtype=np.uint8) * 255  # White background

        # Add text region (top half)
        for y in range(50, 350, 25):
            for x in range(20, 580, 35):
                width = np.random.randint(20, 30)
                height = np.random.randint(8, 12)
                img[y : y + height, x : x + width] = 0

        # Add image region (bottom half) - smooth gradient
        for i in range(400, 750):
            img[i, :] = [100, 150, 200]

        gate = TextGate()
        result = gate.detect(img)

        # Text should be detected (top half has text)
        assert result.has_text is True
        assert result.confidence > 0.2

    def test_detect_empty_image_raises(self) -> None:
        """Test detection raises ValueError for empty image."""
        gate = TextGate()

        with pytest.raises(ValueError, match="Invalid or empty image"):
            gate.detect(np.array([]))

    def test_detect_invalid_shape_raises(self) -> None:
        """Test detection raises ValueError for invalid image shape."""
        gate = TextGate()

        # Grayscale image (2D) instead of BGR (3D)
        gray_img = np.zeros((100, 100), dtype=np.uint8)

        with pytest.raises(ValueError, match="Expected BGR image with shape"):
            gate.detect(gray_img)

    def test_detect_none_image_raises(self) -> None:
        """Test detection raises ValueError for None image."""
        gate = TextGate()

        with pytest.raises(ValueError, match="Invalid or empty image"):
            gate.detect(None)  # type: ignore

    def test_stroke_density_computation(self) -> None:
        """Test stroke density computation on known patterns."""
        gate = TextGate()

        # Create image with known stroke density
        img = np.ones((100, 100, 3), dtype=np.uint8) * 255

        # Add 10 horizontal lines (high stroke density)
        for y in range(10, 100, 10):
            img[y : y + 2, :] = 0

        result = gate.detect(img)

        # Should have measurable stroke density
        assert result.stroke_density > 0.01

    def test_component_analysis(self) -> None:
        """Test connected components analysis."""
        gate = TextGate()

        # Create image with many small components (text-like)
        img = np.ones((200, 200, 3), dtype=np.uint8) * 255

        # Add 20 small rectangles (text-like components)
        for i in range(5):
            for j in range(4):
                x = 20 + j * 45
                y = 20 + i * 40
                img[y : y + 12, x : x + 25] = 0  # Text-like aspect ratio

        result = gate.detect(img)

        # Should detect text-like components
        assert result.component_score > 0.1
        assert result.has_text is True  # Many text-like components

    def test_edge_density_computation(self) -> None:
        """Test edge density computation."""
        gate = TextGate()

        # Create image with clear edges
        img = np.ones((200, 200, 3), dtype=np.uint8) * 255
        img[50:150, 50:150] = 0  # Large black square (4 edges)

        result = gate.detect(img)

        # Should have measurable edge density
        assert result.edge_score > 0.0

    def test_confidence_weighting(self) -> None:
        """Test confidence computation with known scores."""
        gate = TextGate()

        # Test with known input scores
        confidence = gate._compute_confidence(
            stroke_density=0.5, component_score=0.5, edge_score=0.5
        )

        # Weighted average: 0.4*0.5 + 0.4*0.5 + 0.2*0.5 = 0.5
        assert confidence == pytest.approx(0.5, abs=0.01)

    def test_confidence_bounds(self) -> None:
        """Test confidence is bounded between 0.0 and 1.0."""
        gate = TextGate()

        # Test with extreme values
        confidence_high = gate._compute_confidence(
            stroke_density=2.0, component_score=2.0, edge_score=2.0
        )
        confidence_low = gate._compute_confidence(
            stroke_density=-1.0, component_score=-1.0, edge_score=-1.0
        )

        assert 0.0 <= confidence_high <= 1.0
        assert 0.0 <= confidence_low <= 1.0

    def test_decision_logic_stroke_threshold(self) -> None:
        """Test decision logic triggers on high stroke density."""
        gate = TextGate(stroke_threshold=0.05)

        # Create image with high stroke density, low components
        img = np.ones((100, 100, 3), dtype=np.uint8) * 255
        for y in range(0, 100, 5):
            img[y : y + 1, :] = 0  # Dense horizontal lines

        result = gate.detect(img)

        # Should detect text based on stroke density alone
        assert result.stroke_density > gate.stroke_threshold
        assert result.has_text is True

    def test_decision_logic_component_threshold(self) -> None:
        """Test decision logic triggers on high component count."""
        gate = TextGate(min_text_components=10)

        # Create image with many small components
        img = np.ones((300, 300, 3), dtype=np.uint8) * 255
        for i in range(15):  # 15 components (> min_text_components)
            x = (i % 5) * 60 + 10
            y = (i // 5) * 100 + 10
            img[y : y + 15, x : x + 30] = 0

        result = gate.detect(img)

        # Should detect text based on component count
        assert result.component_score > 0.5  # Indicates >= min_text_components
        assert result.has_text is True


class TestDetectTextConvenience:
    """Test detect_text convenience function."""

    def test_detect_text_convenience(self) -> None:
        """Test detect_text convenience function."""
        # Create simple text-like image
        img = np.ones((100, 100, 3), dtype=np.uint8) * 255
        for y in range(10, 90, 15):
            img[y : y + 8, 10:90] = 0

        result = detect_text(img)

        assert isinstance(result, TextDetectionResult)
        assert result.has_text is True

    def test_detect_text_with_custom_params(self) -> None:
        """Test detect_text with custom parameters."""
        img = np.ones((100, 100, 3), dtype=np.uint8) * 255

        result = detect_text(img, stroke_threshold=0.10, min_text_components=20)

        assert isinstance(result, TextDetectionResult)
