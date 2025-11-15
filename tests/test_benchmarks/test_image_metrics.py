"""Unit tests for image quality metrics.

Tests the deterministic metrics functions for IQA evaluation.

SPDX-License-Identifier: Apache-2.0
"""

import numpy as np
import pytest

from benchmarks.metrics.image_metrics import (
    blur_correlation,
    blur_rmse,
    deskew_success_rate,
    psnr,
    skew_mae,
    ssim,
)


class TestBlurMetrics:
    """Tests for blur detection metrics."""

    def test_blur_correlation_perfect(self) -> None:
        """Test blur correlation with perfect prediction."""
        gt = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        pred = np.array([0.0, 1.0, 2.0, 3.0, 4.0])

        corr = blur_correlation(pred, gt)
        assert corr == pytest.approx(1.0, abs=0.01)

    def test_blur_correlation_inverted(self) -> None:
        """Test blur correlation with inverted prediction."""
        gt = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        pred = np.array([4.0, 3.0, 2.0, 1.0, 0.0])

        corr = blur_correlation(pred, gt)
        assert corr == pytest.approx(-1.0, abs=0.01)

    def test_blur_rmse_perfect(self) -> None:
        """Test RMSE with perfect prediction."""
        gt = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        pred = np.array([0.0, 1.0, 2.0, 3.0, 4.0])

        rmse = blur_rmse(pred, gt)
        assert rmse == pytest.approx(0.0, abs=1e-6)

    def test_blur_rmse_constant_offset(self) -> None:
        """Test RMSE with constant offset."""
        gt = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        pred = np.array([1.0, 2.0, 3.0, 4.0, 5.0])  # +1.0 offset

        rmse = blur_rmse(pred, gt)
        assert rmse == pytest.approx(1.0, abs=0.01)


class TestSkewMetrics:
    """Tests for skew detection metrics."""

    def test_skew_mae_perfect(self) -> None:
        """Test MAE with perfect prediction."""
        gt = np.array([-5.0, -2.5, 0.0, 2.5, 5.0])
        pred = np.array([-5.0, -2.5, 0.0, 2.5, 5.0])

        mae = skew_mae(pred, gt)
        assert mae == pytest.approx(0.0, abs=1e-6)

    def test_skew_mae_constant_error(self) -> None:
        """Test MAE with constant error."""
        gt = np.array([0.0, 0.0, 0.0, 0.0, 0.0])
        pred = np.array([0.5, 0.5, 0.5, 0.5, 0.5])

        mae = skew_mae(pred, gt)
        assert mae == pytest.approx(0.5, abs=0.01)

    def test_deskew_success_rate_all_success(self) -> None:
        """Test success rate with all successful deskews."""
        gt = np.array([0.0, 0.0, 0.0, 0.0, 0.0])
        corrected = np.array([0.1, -0.1, 0.2, -0.2, 0.0])

        success_rate = deskew_success_rate(corrected, gt, threshold=0.5)
        assert success_rate == pytest.approx(1.0)

    def test_deskew_success_rate_partial_success(self) -> None:
        """Test success rate with partial success."""
        gt = np.array([0.0, 0.0, 0.0, 0.0])
        corrected = np.array(
            [0.3, 0.7, -0.4, 1.5]
        )  # 2 success (0.3, -0.4), 2 fail (0.7, 1.5)

        success_rate = deskew_success_rate(corrected, gt, threshold=0.5)
        assert success_rate == pytest.approx(0.5)


class TestNoiseMetrics:
    """Tests for noise and quality metrics."""

    def test_psnr_identical_images(self) -> None:
        """Test PSNR with identical images."""
        img = np.random.randint(0, 255, (100, 100), dtype=np.uint8)

        psnr_value = psnr(img, img)
        assert psnr_value == pytest.approx(float("inf"), abs=1e6)

    def test_psnr_different_images(self) -> None:
        """Test PSNR with different images."""
        ref = np.full((100, 100), 128, dtype=np.uint8)
        test = np.full((100, 100), 138, dtype=np.uint8)  # +10 intensity

        psnr_value = psnr(ref, test)
        # PSNR should be finite and positive
        assert psnr_value > 0
        assert psnr_value < 100  # Reasonable upper bound

    def test_ssim_identical_images(self) -> None:
        """Test SSIM with identical images."""
        img = np.random.randint(0, 255, (100, 100), dtype=np.uint8)

        ssim_value = ssim(img, img)
        assert ssim_value == pytest.approx(1.0, abs=0.01)

    def test_ssim_different_images(self) -> None:
        """Test SSIM with different images."""
        ref = np.full((100, 100), 128, dtype=np.uint8)
        test = np.full((100, 100), 138, dtype=np.uint8)

        ssim_value = ssim(ref, test)
        # SSIM should be less than 1 for different images
        assert 0.0 < ssim_value < 1.0


class TestBinarizationMetrics:
    """Tests for binarization quality metrics."""

    def test_binarization_perfect(self) -> None:
        """Test binarization metrics with perfect match."""
        from benchmarks.metrics.image_metrics import binarization_metrics

        true_mask = np.array([[True, False], [False, True]])
        pred_mask = np.array([[True, False], [False, True]])

        precision, recall, f_measure, ber = binarization_metrics(pred_mask, true_mask)

        assert precision == pytest.approx(1.0)
        assert recall == pytest.approx(1.0)
        assert f_measure == pytest.approx(1.0)
        assert ber == pytest.approx(0.0)

    def test_binarization_half_correct(self) -> None:
        """Test binarization metrics with 50% correct."""
        from benchmarks.metrics.image_metrics import binarization_metrics

        true_mask = np.array([[True, False], [False, True]])
        pred_mask = np.array([[True, True], [False, False]])  # 2 correct, 2 wrong

        precision, recall, f_measure, ber = binarization_metrics(pred_mask, true_mask)

        # Precision: 1 TP / (1 TP + 1 FP) = 0.5
        assert precision == pytest.approx(0.5)
        # Recall: 1 TP / (1 TP + 1 FN) = 0.5
        assert recall == pytest.approx(0.5)
        # F-measure: 2 * 0.5 * 0.5 / (0.5 + 0.5) = 0.5
        assert f_measure == pytest.approx(0.5)
        # BER: 2 errors / 4 total = 0.5
        assert ber == pytest.approx(0.5)


class TestDetectionMetrics:
    """Tests for object detection metrics."""

    def test_bbox_iou_identical(self) -> None:
        """Test IoU with identical boxes."""
        from benchmarks.metrics.detection_metrics import bbox_iou

        bbox1 = np.array([10, 20, 30, 40])  # [x, y, w, h]
        bbox2 = np.array([10, 20, 30, 40])

        iou = bbox_iou(bbox1, bbox2)
        assert iou == pytest.approx(1.0)

    def test_bbox_iou_no_overlap(self) -> None:
        """Test IoU with no overlap."""
        from benchmarks.metrics.detection_metrics import bbox_iou

        bbox1 = np.array([0, 0, 10, 10])
        bbox2 = np.array([20, 20, 10, 10])

        iou = bbox_iou(bbox1, bbox2)
        assert iou == pytest.approx(0.0)

    def test_bbox_iou_partial_overlap(self) -> None:
        """Test IoU with partial overlap."""
        from benchmarks.metrics.detection_metrics import bbox_iou

        bbox1 = np.array([0, 0, 20, 20])  # Area = 400
        bbox2 = np.array([10, 10, 20, 20])  # Area = 400
        # Intersection: 10x10 = 100
        # Union: 400 + 400 - 100 = 700
        # IoU = 100 / 700 ≈ 0.143

        iou = bbox_iou(bbox1, bbox2)
        assert iou == pytest.approx(0.143, abs=0.01)


class TestAggregateMetrics:
    """Tests for aggregate IQA metrics."""

    def test_aggregate_all_pass(self) -> None:
        """Test aggregate with all metrics passing."""
        from benchmarks.metrics.image_metrics import aggregate_iqa_metrics

        metrics = {
            "blur_correlation": 0.90,  # Target: ≥ 0.85
            "blur_rmse": 0.03,  # Target: ≤ 0.05
            "skew_mae": 0.4,  # Target: ≤ 0.5
            "deskew_success_rate": 0.995,  # Target: ≥ 0.99
            "snr_improvement": 8.0,  # Target: ≥ 6.0
            "psnr": 35.0,  # Target: ≥ 30.0
            "ssim": 0.95,  # Target: ≥ 0.9
            "f_measure": 0.97,  # Target: ≥ 0.95
        }

        results = aggregate_iqa_metrics(metrics)

        assert results["overall"]["pass_rate"] == pytest.approx(1.0)
        assert results["overall"]["passed_count"] == 8
        assert results["overall"]["total_count"] == 8

    def test_aggregate_partial_pass(self) -> None:
        """Test aggregate with some metrics failing."""
        from benchmarks.metrics.image_metrics import aggregate_iqa_metrics

        metrics = {
            "blur_correlation": 0.80,  # Target: ≥ 0.85 (FAIL)
            "blur_rmse": 0.03,  # Target: ≤ 0.05 (PASS)
            "skew_mae": 0.8,  # Target: ≤ 0.5 (FAIL)
            "psnr": 25.0,  # Target: ≥ 30.0 (FAIL)
        }

        results = aggregate_iqa_metrics(metrics)

        assert results["overall"]["pass_rate"] == pytest.approx(0.25)  # 1/4
        assert results["overall"]["passed_count"] == 1
        assert results["overall"]["total_count"] == 4
