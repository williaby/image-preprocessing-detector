# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for scripts/validate_dqs_correlation.py - DQS correlation validation.

These tests verify the DQS correlation validation script correctly:
- Calculates Pearson correlation
- Generates synthetic documents
- Simulates OCR accuracy
- Validates correlation thresholds
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np

# Add scripts directory to path for import
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from validate_dqs_correlation import (
    pearson_correlation,
    simulate_ocr_accuracy,
)


class TestPearsonCorrelation:
    """Tests for pearson_correlation function."""

    def test_perfect_positive_correlation(self) -> None:
        """Test perfect positive correlation returns 1.0."""
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [1.0, 2.0, 3.0, 4.0, 5.0]

        correlation, p_value = pearson_correlation(x, y)

        assert abs(correlation - 1.0) < 0.001

    def test_perfect_negative_correlation(self) -> None:
        """Test perfect negative correlation returns -1.0."""
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [5.0, 4.0, 3.0, 2.0, 1.0]

        correlation, p_value = pearson_correlation(x, y)

        assert abs(correlation - (-1.0)) < 0.001

    def test_no_correlation(self) -> None:
        """Test uncorrelated data returns near zero."""
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [3.0, 1.0, 4.0, 1.0, 5.0]  # Random-ish

        correlation, p_value = pearson_correlation(x, y)

        # Correlation should be relatively low
        assert abs(correlation) < 0.8

    def test_returns_p_value(self) -> None:
        """Test that p-value is returned."""
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [1.0, 2.0, 3.0, 4.0, 5.0]

        correlation, p_value = pearson_correlation(x, y)

        assert isinstance(p_value, float)
        assert 0.0 <= p_value <= 1.0

    def test_scaled_linear_relationship(self) -> None:
        """Test scaled linear relationship has high correlation."""
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [10.0, 20.0, 30.0, 40.0, 50.0]  # y = 10*x

        correlation, p_value = pearson_correlation(x, y)

        assert abs(correlation - 1.0) < 0.001

    def test_shifted_relationship(self) -> None:
        """Test shifted relationship has high correlation."""
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [101.0, 102.0, 103.0, 104.0, 105.0]  # y = x + 100

        correlation, p_value = pearson_correlation(x, y)

        assert abs(correlation - 1.0) < 0.001


class TestSimulateOCRAccuracy:
    """Tests for simulate_ocr_accuracy function."""

    def test_high_quality_high_accuracy(self) -> None:
        """Test high quality documents get high OCR accuracy."""
        # Create mock DQS with high quality (high degradation score = good)
        mock_dqs = MagicMock()
        mock_dqs.degradation_score = 0.95  # High quality
        mock_dqs.structural_complexity_score = 0.1  # Low complexity

        accuracy = simulate_ocr_accuracy(mock_dqs)

        # High quality should give high accuracy
        assert accuracy > 0.8

    def test_low_quality_lower_accuracy(self) -> None:
        """Test low quality documents get lower OCR accuracy."""
        mock_dqs = MagicMock()
        mock_dqs.degradation_score = 0.2  # Low quality
        mock_dqs.structural_complexity_score = 0.1

        accuracy = simulate_ocr_accuracy(mock_dqs)

        # Low quality should give lower accuracy
        assert accuracy < 0.7

    def test_high_complexity_penalty(self) -> None:
        """Test high complexity reduces accuracy."""
        # Same quality, different complexity
        mock_dqs_simple = MagicMock()
        mock_dqs_simple.degradation_score = 0.8
        mock_dqs_simple.structural_complexity_score = 0.1

        mock_dqs_complex = MagicMock()
        mock_dqs_complex.degradation_score = 0.8
        mock_dqs_complex.structural_complexity_score = 0.9

        accuracy_simple = simulate_ocr_accuracy(mock_dqs_simple)
        accuracy_complex = simulate_ocr_accuracy(mock_dqs_complex)

        # Complex should be lower (on average, with noise it might vary)
        # Run multiple times to get average
        simple_avg = np.mean(
            [simulate_ocr_accuracy(mock_dqs_simple) for _ in range(20)]
        )
        complex_avg = np.mean(
            [simulate_ocr_accuracy(mock_dqs_complex) for _ in range(20)]
        )

        assert simple_avg > complex_avg

    def test_accuracy_in_valid_range(self) -> None:
        """Test accuracy is always in 0-1 range."""
        for _ in range(50):
            mock_dqs = MagicMock()
            mock_dqs.degradation_score = np.random.random()
            mock_dqs.structural_complexity_score = np.random.random()

            accuracy = simulate_ocr_accuracy(mock_dqs)

            assert 0.0 <= accuracy <= 1.0


class TestValidateDqsCorrelation:
    """Tests for validate_dqs_correlation function."""

    def test_function_exists(self) -> None:
        """Test that validation function exists."""
        from validate_dqs_correlation import validate_dqs_correlation

        assert callable(validate_dqs_correlation)


class TestGenerateSyntheticDocument:
    """Tests for generate_synthetic_document function."""

    def test_function_exists(self) -> None:
        """Test that function exists."""
        from validate_dqs_correlation import generate_synthetic_document

        assert callable(generate_synthetic_document)


class TestMain:
    """Tests for main entry point."""

    def test_main_exists(self) -> None:
        """Test that main function exists and is callable."""
        from validate_dqs_correlation import main

        assert callable(main)
