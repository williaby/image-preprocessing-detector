"""Cross-model agreement validator for OOD-aware document IQA.

Tier 1 + Tier 2 integration: combines embedding-space OOD detection with
cross-model agreement scoring to produce a reliability score for SigLIP2
predictions.

Architecture:
    Tier 1: EmbeddingOODDetector (Mahalanobis distance, ~1ms)
    Tier 2: VLM + CLIP-IQA validators with calibrated z-scores (~2-3s)

The reliability score indicates how trustworthy SigLIP2's IQA predictions
are for a given document image. Higher scores = more disagreement = less
reliable.

Usage:
    >>> validator = CrossModelValidator.from_config(config)
    >>> result = validator.validate(prediction_with_embedding)
    >>> if result.needs_review:
    ...     # Route to manual review or use validator scores instead
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from image_preprocessing_detector.detection.cross_model_calibration import (
    CrossModelCalibrator,
)
from image_preprocessing_detector.detection.ood_detector import (
    EmbeddingOODDetector,
    OODResult,
)
from image_preprocessing_detector.detection.siglip2_multitask import (
    MultiTaskPrediction,
)
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)

DIMENSIONS = ("overall", "sharpness", "color")


@dataclass(frozen=True)
class ValidatorScore:
    """Individual validator's assessment for one dimension.

    Attributes:
        validator: Validator name.
        dimension: Quality dimension.
        raw_output: Raw output from validator (category or score).
        z_score: Calibrated z-score vs expected MOS.
    """

    validator: str
    dimension: str
    raw_output: str | float
    z_score: float | None


@dataclass(frozen=True)
class ReliabilityResult:
    """Complete reliability assessment for a document image.

    Attributes:
        ood_result: Tier 1 embedding OOD detection result.
        tier2_invoked: Whether Tier 2 validators were run.
        validator_scores: Per-validator, per-dimension z-scores.
        agreement_distance: Mahalanobis distance over z-score vector.
        reliability_score: Combined reliability (0=reliable, higher=suspect).
        needs_review: Whether the image should be flagged for review.
        z_vector: Raw z-score vector used for agreement distance.
    """

    ood_result: OODResult
    tier2_invoked: bool
    validator_scores: list[ValidatorScore]
    agreement_distance: float
    reliability_score: float
    needs_review: bool
    z_vector: list[float]


@dataclass
class ValidatorConfig:
    """Configuration for cross-model validation.

    Attributes:
        ood_params_path: Path to saved OOD detector parameters.
        calibration_path: Path to saved calibration parameters.
        tier2_threshold: Mahalanobis distance threshold for invoking Tier 2.
        agreement_threshold: Z-score agreement threshold for flagging review.
        z_covariance_path: Path to saved z-score covariance matrix.
    """

    ood_params_path: str | Path
    calibration_path: str | Path
    tier2_threshold: float | None = None
    agreement_threshold: float = 2.0
    z_covariance_path: str | Path | None = None


class CrossModelValidator:
    """Tiered cross-model validation for SigLIP2 reliability.

    Implements the two-tier reliability detection system:
    - Tier 1: Embedding Mahalanobis distance (always runs, ~1ms)
    - Tier 2: Cross-model agreement scoring (conditional, ~2-3s)

    Args:
        ood_detector: Fitted embedding OOD detector.
        calibrator: Fitted cross-model calibrator.
        z_precision: Inverse covariance of z-score vector (for Mahalanobis).
        z_mean: Mean z-score vector from calibration.
        agreement_threshold: Threshold on agreement distance for flagging.
    """

    def __init__(
        self,
        ood_detector: EmbeddingOODDetector,
        calibrator: CrossModelCalibrator,
        z_precision: np.ndarray | None = None,
        z_mean: np.ndarray | None = None,
        agreement_threshold: float = 2.0,
    ) -> None:
        self._ood_detector = ood_detector
        self._calibrator = calibrator
        self._z_precision = z_precision
        self._z_mean = z_mean if z_mean is not None else np.zeros(0)
        self._agreement_threshold = agreement_threshold

    @classmethod
    def from_config(cls, config: ValidatorConfig) -> CrossModelValidator:
        """Load validator from saved configuration files.

        Args:
            config: Paths to all saved parameter files.

        Returns:
            Loaded CrossModelValidator instance.
        """
        ood_detector = EmbeddingOODDetector.load(config.ood_params_path)
        calibrator = CrossModelCalibrator.load(config.calibration_path)

        z_precision = None
        z_mean = None
        if config.z_covariance_path and Path(config.z_covariance_path).exists():
            data = np.load(str(config.z_covariance_path))
            z_precision = data["precision"]
            z_mean = data.get("mean", np.zeros(z_precision.shape[0]))

        if config.tier2_threshold is not None:
            ood_detector.threshold = config.tier2_threshold

        return cls(
            ood_detector=ood_detector,
            calibrator=calibrator,
            z_precision=z_precision,
            z_mean=z_mean,
            agreement_threshold=config.agreement_threshold,
        )

    def validate_tier1(self, prediction: MultiTaskPrediction) -> OODResult:
        """Run Tier 1 embedding OOD detection only.

        Args:
            prediction: SigLIP2 prediction (must have embedding).

        Returns:
            OODResult with Mahalanobis distance.

        Raises:
            ValueError: If prediction has no embedding.
        """
        if prediction.embedding is None:
            msg = "Prediction must include embedding for OOD detection. Use predict(return_embedding=True)."
            raise ValueError(msg)
        return self._ood_detector.score(prediction.embedding)

    def validate(
        self,
        prediction: MultiTaskPrediction,
        vlm_ratings: dict[str, str] | None = None,
        clip_scores: dict[str, float] | None = None,
        force_tier2: bool = False,
    ) -> ReliabilityResult:
        """Run full tiered validation.

        Args:
            prediction: SigLIP2 prediction (must have embedding).
            vlm_ratings: VLM categorical ratings per dimension
                (e.g. {"overall": "good", "sharpness": "fair"}).
            clip_scores: CLIP-IQA continuous scores per dimension
                (e.g. {"overall": 0.72}).
            force_tier2: Force Tier 2 even if Tier 1 passes.

        Returns:
            ReliabilityResult with full assessment.
        """
        # Tier 1: Embedding OOD
        ood_result = self.validate_tier1(prediction)

        # Decide whether to invoke Tier 2
        run_tier2 = ood_result.is_ood or force_tier2
        if not run_tier2 and vlm_ratings is None and clip_scores is None:
            return ReliabilityResult(
                ood_result=ood_result,
                tier2_invoked=False,
                validator_scores=[],
                agreement_distance=0.0,
                reliability_score=ood_result.mahalanobis_distance,
                needs_review=False,
                z_vector=[],
            )

        # Tier 2: Cross-model agreement
        validator_scores: list[ValidatorScore] = []
        z_values: list[float] = []

        siglip_scores = {
            "overall": prediction.iqa_overall.mu,
            "sharpness": prediction.iqa_sharpness.mu,
            "color": prediction.iqa_color.mu,
        }

        # VLM categorical z-scores
        if vlm_ratings:
            for dim in DIMENSIONS:
                if dim not in vlm_ratings:
                    continue
                cat = vlm_ratings[dim]
                vname = f"vlm_{dim}"
                z = self._calibrator.z_score_categorical(vname, cat, siglip_scores[dim])
                validator_scores.append(
                    ValidatorScore(
                        validator="vlm",
                        dimension=dim,
                        raw_output=cat,
                        z_score=z,
                    )
                )
                if z is not None:
                    z_values.append(z)

        # CLIP-IQA continuous z-scores
        if clip_scores:
            for dim, score in clip_scores.items():
                if dim not in DIMENSIONS:
                    continue
                vname = f"clip_{dim}"
                z = self._calibrator.z_score_continuous(
                    vname, score, siglip_scores[dim]
                )
                validator_scores.append(
                    ValidatorScore(
                        validator="clip",
                        dimension=dim,
                        raw_output=score,
                        z_score=z,
                    )
                )
                if z is not None:
                    z_values.append(z)

        # Agreement distance
        agreement_distance = 0.0
        if z_values:
            z_vec = np.array(z_values)
            if (
                self._z_precision is not None
                and len(z_vec) == self._z_precision.shape[0]
            ):
                diff = z_vec - self._z_mean[: len(z_vec)]
                agreement_distance = float(np.sqrt(diff @ self._z_precision @ diff))
            else:
                # Fallback: Euclidean norm of z-scores
                agreement_distance = float(np.linalg.norm(z_vec))

        # Combined reliability score
        # Weight Tier 1 and Tier 2 signals
        reliability_score = agreement_distance
        needs_review = agreement_distance > self._agreement_threshold or any(
            abs(z) > 3.0
            for vs in validator_scores
            if vs.z_score is not None
            for z in [vs.z_score]
        )

        return ReliabilityResult(
            ood_result=ood_result,
            tier2_invoked=True,
            validator_scores=validator_scores,
            agreement_distance=agreement_distance,
            reliability_score=reliability_score,
            needs_review=needs_review,
            z_vector=z_values,
        )

    @staticmethod
    def fit_z_covariance(
        z_vectors: np.ndarray,
        save_path: str | Path | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Fit z-score covariance from calibration set.

        Uses Ledoit-Wolf shrinkage for robust estimation.

        Args:
            z_vectors: Calibration z-scores, shape (n_samples, n_validators).
            save_path: Optional path to save parameters.

        Returns:
            Tuple of (precision_matrix, mean_vector).
        """
        from sklearn.covariance import LedoitWolf

        lw = LedoitWolf()
        lw.fit(z_vectors)

        mean = z_vectors.mean(axis=0)
        precision = lw.precision_

        logger.info(
            "z_covariance_fitted",
            n_validators=z_vectors.shape[1],
            n_samples=z_vectors.shape[0],
            shrinkage=float(lw.shrinkage_),
        )

        if save_path:
            np.savez_compressed(
                str(save_path),
                precision=precision,
                mean=mean,
                covariance=lw.covariance_,
            )
            logger.info("z_covariance_saved", path=str(save_path))

        return precision, mean


def reliability_result_to_dict(result: ReliabilityResult) -> dict[str, Any]:
    """Convert ReliabilityResult to JSON-serializable dict.

    Args:
        result: Reliability assessment result.

    Returns:
        Nested dict with all assessment data.
    """
    return {
        "ood": {
            "mahalanobis_distance": result.ood_result.mahalanobis_distance,
            "is_ood": result.ood_result.is_ood,
            "percentile": result.ood_result.percentile,
        },
        "tier2_invoked": result.tier2_invoked,
        "validator_scores": [
            {
                "validator": vs.validator,
                "dimension": vs.dimension,
                "raw_output": vs.raw_output,
                "z_score": vs.z_score,
            }
            for vs in result.validator_scores
        ],
        "agreement_distance": result.agreement_distance,
        "reliability_score": result.reliability_score,
        "needs_review": result.needs_review,
        "z_vector": result.z_vector,
    }


__all__ = [
    "CrossModelValidator",
    "ReliabilityResult",
    "ValidatorConfig",
    "ValidatorScore",
    "reliability_result_to_dict",
]
