"""Out-of-Distribution (OOD) detector using embedding-space Mahalanobis distance.

Tier 1 of the cross-model agreement system: detects when SigLIP2's predictions
may be unreliable because the input document is far from the DIQA-5000 training
distribution in embedding space.

Uses Mahalanobis distance with Ledoit-Wolf covariance shrinkage to handle the
high-dimensional (768-dim) embedding space robustly.

Usage:
    >>> detector = EmbeddingOODDetector.from_embeddings(train_embeddings)
    >>> detector.save("ood_params.npz")
    >>> # At inference:
    >>> detector = EmbeddingOODDetector.load("ood_params.npz")
    >>> result = detector.score(embedding)
    >>> if result.is_ood:
    ...     # Trigger Tier 2 cross-model validation
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class OODResult:
    """Result of OOD detection for a single image.

    Attributes:
        mahalanobis_distance: Mahalanobis distance from training distribution.
        is_ood: Whether the image is flagged as out-of-distribution.
        percentile: Approximate percentile rank vs calibration set (0-100).
        threshold: The threshold used for OOD decision.
    """

    mahalanobis_distance: float
    is_ood: bool
    percentile: float
    threshold: float


class EmbeddingOODDetector:
    """Mahalanobis distance-based OOD detector for SigLIP2 embeddings.

    Computes Mahalanobis distance of new embeddings from the training
    distribution, using Ledoit-Wolf shrinkage for covariance estimation.

    Args:
        mean: Mean embedding vector (768-dim).
        precision_matrix: Inverse covariance matrix (768x768).
        threshold: Mahalanobis distance threshold for OOD flag.
        calibration_distances: Sorted distances from calibration set for percentile.
    """

    def __init__(
        self,
        mean: np.ndarray,
        precision_matrix: np.ndarray,
        threshold: float,
        calibration_distances: np.ndarray | None = None,
    ) -> None:
        self._mean = mean
        self._precision = precision_matrix
        self._threshold = threshold
        self._calibration_distances = calibration_distances

    @classmethod
    def from_embeddings(
        cls,
        embeddings: np.ndarray,
        threshold_percentile: float = 95.0,
    ) -> EmbeddingOODDetector:
        """Fit OOD detector from training set embeddings.

        Args:
            embeddings (np.ndarray): Training embeddings, shape (n_samples, embed_dim).
            threshold_percentile (float): Percentile of training distances to use as OOD threshold (default: 95th percentile).

        Returns:
            EmbeddingOODDetector: Fitted EmbeddingOODDetector instance."""
        from sklearn.covariance import LedoitWolf

        n_samples, embed_dim = embeddings.shape
        logger.info(
            "fitting_ood_detector",
            n_samples=n_samples,
            embed_dim=embed_dim,
            threshold_pct=threshold_percentile,
        )

        mean = embeddings.mean(axis=0)

        lw = LedoitWolf()
        lw.fit(embeddings)
        precision_matrix = lw.precision_

        logger.info(
            "ledoit_wolf_fitted",
            shrinkage=float(lw.shrinkage_),
        )

        # Compute calibration distances
        diffs = embeddings - mean
        cal_distances = np.sqrt(np.sum(diffs @ precision_matrix * diffs, axis=1))
        cal_distances_sorted = np.sort(cal_distances)

        threshold = float(np.percentile(cal_distances, threshold_percentile))
        logger.info(
            "ood_threshold_set",
            threshold=threshold,
            median_distance=float(np.median(cal_distances)),
            max_distance=float(cal_distances.max()),
        )

        return cls(
            mean=mean,
            precision_matrix=precision_matrix,
            threshold=threshold,
            calibration_distances=cal_distances_sorted,
        )

    def _build_result(self, distance: float) -> OODResult:
        """Build an OODResult from a Mahalanobis distance.

        Args:
            distance (float): Mahalanobis distance value.

        Returns:
            OODResult: OODResult with distance, flag, and percentile."""
        percentile = 0.0
        if self._calibration_distances is not None:
            idx = np.searchsorted(self._calibration_distances, distance)
            percentile = 100.0 * idx / len(self._calibration_distances)

        return OODResult(
            mahalanobis_distance=distance,
            is_ood=distance > self._threshold,
            percentile=percentile,
            threshold=self._threshold,
        )

    def score(self, embedding: np.ndarray) -> OODResult:
        """Compute OOD score for a single embedding.

        Args:
            embedding (np.ndarray): Single embedding vector (768-dim).

        Returns:
            OODResult: OODResult with distance, flag, and percentile."""
        diff = embedding - self._mean
        distance = float(np.sqrt(diff @ self._precision @ diff))
        return self._build_result(distance)

    def score_batch(self, embeddings: np.ndarray) -> list[OODResult]:
        """Compute OOD scores for a batch of embeddings.

        Args:
            embeddings (np.ndarray): Batch of embeddings, shape (n, embed_dim).

        Returns:
            list[OODResult]: List of OODResult for each embedding."""
        diffs = embeddings - self._mean
        distances = np.sqrt(np.sum(diffs @ self._precision * diffs, axis=1))
        return [self._build_result(float(dist)) for dist in distances]

    def save(self, path: str | Path) -> None:
        """Save detector parameters to disk.

        Args:
            path (str | Path): Output path (.npz file)."""
        save_dict: dict[str, Any] = {
            "mean": self._mean,
            "precision_matrix": self._precision,
            "threshold": np.array([self._threshold]),
        }
        if self._calibration_distances is not None:
            save_dict["calibration_distances"] = self._calibration_distances
        np.savez_compressed(str(path), **save_dict)
        logger.info("ood_detector_saved", path=str(path))

    @classmethod
    def load(cls, path: str | Path) -> EmbeddingOODDetector:
        """Load detector parameters from disk.

        Args:
            path (str | Path): Path to saved .npz file.

        Returns:
            EmbeddingOODDetector: Loaded EmbeddingOODDetector instance."""
        data = np.load(str(path))
        cal_dist = data.get("calibration_distances")
        detector = cls(
            mean=data["mean"],
            precision_matrix=data["precision_matrix"],
            threshold=float(data["threshold"][0]),
            calibration_distances=cal_dist,
        )
        logger.info(
            "ood_detector_loaded",
            path=str(path),
            embed_dim=data["mean"].shape[0],
        )
        return detector

    @property
    def threshold(self) -> float:
        """Current OOD threshold."""
        return self._threshold

    @threshold.setter
    def threshold(self, value: float) -> None:
        """Update OOD threshold (e.g., after tuning on OOD validation set)."""
        self._threshold = value


__all__ = [
    "EmbeddingOODDetector",
    "OODResult",
]
