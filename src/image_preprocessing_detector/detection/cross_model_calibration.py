"""Cross-model calibration for OOD agreement system.

Maps validator outputs (categorical VLM ratings, continuous IQA scores) to
expected MOS distributions, enabling z-score computation for agreement detection.

Calibrated against ground-truth MOS (not SigLIP2 scores) to avoid reference-model
bias — the system detects when SigLIP2 is wrong, not just when others disagree.

Usage:
    >>> calibrator = CrossModelCalibrator()
    >>> calibrator.fit_categorical("vlm_overall", categories, mos_values)
    >>> calibrator.fit_continuous("clip_overall", clip_scores, mos_values)
    >>> calibrator.save("calibration_params.json")
    >>>
    >>> # At inference:
    >>> calibrator = CrossModelCalibrator.load("calibration_params.json")
    >>> z = calibrator.z_score_categorical("vlm_overall", "good", siglip_mu=3.8)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class CategoryDistribution:
    """Statistics of MOS conditioned on a VLM category.

    Attributes:
        category (str): Quality level name (e.g. "good").
        mean_mos (float): E[MOS | category].
        std_mos (float): Std[MOS | category].
        count (int): Number of calibration samples in this category.
        quantiles (dict[str, float]): 5th, 25th, 50th, 75th, 95th percentiles of MOS.
    """

    category: str
    mean_mos: float
    std_mos: float
    count: int
    quantiles: dict[str, float]


class CrossModelCalibrator:
    """Calibration mapper for cross-model agreement scoring.

    Stores conditional distributions P(MOS | validator_output) for both
    categorical (VLM) and continuous (CLIP-IQA) validators.
    """

    def __init__(self) -> None:
        self._categorical_maps: dict[str, dict[str, CategoryDistribution]] = {}
        self._continuous_maps: dict[str, dict[str, Any]] = {}

    def fit_categorical(
        self,
        validator_name: str,
        categories: list[str],
        mos_values: list[float],
        min_samples_per_category: int = 5,
    ) -> dict[str, CategoryDistribution]:
        """Fit conditional MOS distributions for a categorical validator.

        Args:
            validator_name (str): Identifier (e.g. "qwen3.5_overall").
            categories (list[str]): VLM category per image (e.g. ["good", "fair", ...]).
            mos_values (list[float]): Ground-truth MOS per image.
            min_samples_per_category (int): Minimum samples to compute distribution.

        Returns:
            dict[str, CategoryDistribution]: Dict mapping category to CategoryDistribution."""
        cats = np.array(categories)
        mos = np.array(mos_values, dtype=np.float64)
        unique_cats = sorted(set(categories))

        distributions: dict[str, CategoryDistribution] = {}
        for cat in unique_cats:
            mask = cats == cat
            cat_mos = mos[mask]

            if len(cat_mos) < min_samples_per_category:
                logger.warning(
                    "sparse_category",
                    validator=validator_name,
                    category=cat,
                    count=len(cat_mos),
                    min_required=min_samples_per_category,
                )
                continue

            quantiles = {
                "p5": float(np.percentile(cat_mos, 5)),
                "p25": float(np.percentile(cat_mos, 25)),
                "p50": float(np.percentile(cat_mos, 50)),
                "p75": float(np.percentile(cat_mos, 75)),
                "p95": float(np.percentile(cat_mos, 95)),
            }
            distributions[cat] = CategoryDistribution(
                category=cat,
                mean_mos=float(np.mean(cat_mos)),
                std_mos=float(np.std(cat_mos, ddof=1)) if len(cat_mos) > 1 else 0.5,
                count=len(cat_mos),
                quantiles=quantiles,
            )

        self._categorical_maps[validator_name] = distributions
        logger.info(
            "categorical_calibration_fitted",
            validator=validator_name,
            n_categories=len(distributions),
            total_samples=len(mos),
        )
        return distributions

    def fit_continuous(
        self,
        validator_name: str,
        validator_scores: list[float],
        mos_values: list[float],
    ) -> dict[str, Any]:
        """Fit isotonic regression for a continuous validator.

        Uses sklearn IsotonicRegression for monotonic mapping from
        validator score space to MOS space.

        Args:
            validator_name (str): Identifier (e.g. "clip_iqa_overall").
            validator_scores (list[float]): Continuous scores from validator.
            mos_values (list[float]): Ground-truth MOS per image.

        Returns:
            dict[str, Any]: Dict with regression parameters and residual statistics."""
        from sklearn.isotonic import IsotonicRegression

        scores = np.array(validator_scores, dtype=np.float64)
        mos = np.array(mos_values, dtype=np.float64)

        iso_reg = IsotonicRegression(out_of_bounds="clip")
        iso_reg.fit(scores, mos)

        predicted = iso_reg.predict(scores)
        residuals = mos - predicted
        residual_std = float(np.std(residuals, ddof=1))

        params = {
            "x_thresholds": iso_reg.X_thresholds_.tolist(),
            "y_thresholds": iso_reg.y_thresholds_.tolist(),
            "x_min": float(iso_reg.X_min_),
            "x_max": float(iso_reg.X_max_),
            "residual_std": residual_std,
            "residual_mean": float(np.mean(residuals)),
            "n_samples": len(mos),
        }
        self._continuous_maps[validator_name] = params

        logger.info(
            "continuous_calibration_fitted",
            validator=validator_name,
            residual_std=residual_std,
            n_samples=len(mos),
        )
        return params

    def z_score_categorical(
        self,
        validator_name: str,
        category: str,
        siglip_mu: float,
    ) -> float | None:
        """Compute z-score for a categorical validator output.

        z = (siglip_mu - E[MOS | category]) / Std[MOS | category]

        Args:
            validator_name (str): Validator identifier.
            category (str): VLM output category.
            siglip_mu (float): SigLIP2 predicted score for this dimension.

        Returns:
            float | None: Z-score, or None if category not in calibration."""
        distributions = self._categorical_maps.get(validator_name, {})
        dist = distributions.get(category)
        if dist is None:
            return None
        if dist.std_mos <= 0:
            return None
        return (siglip_mu - dist.mean_mos) / dist.std_mos

    def z_score_continuous(
        self,
        validator_name: str,
        validator_score: float,
        siglip_mu: float,
    ) -> float | None:
        """Compute z-score for a continuous validator output.

        z = (siglip_mu - f(validator_score)) / residual_std

        Args:
            validator_name (str): Validator identifier.
            validator_score (float): Raw score from continuous validator.
            siglip_mu (float): SigLIP2 predicted score for this dimension.

        Returns:
            float | None: Z-score, or None if validator not calibrated."""
        params = self._continuous_maps.get(validator_name)
        if params is None:
            return None

        # Reconstruct isotonic prediction via interpolation
        x_thresh = np.array(params["x_thresholds"])
        y_thresh = np.array(params["y_thresholds"])
        predicted_mos = float(np.interp(validator_score, x_thresh, y_thresh))

        residual_std = params["residual_std"]
        if residual_std <= 0:
            return None

        return float((siglip_mu - predicted_mos) / residual_std)

    def save(self, path: str | Path) -> None:
        """Save calibration parameters to JSON.

        Args:
            path (str | Path): Output file path."""
        data: dict[str, Any] = {
            "categorical": {},
            "continuous": self._continuous_maps,
        }
        for vname, dists in self._categorical_maps.items():
            data["categorical"][vname] = {
                cat: {
                    "category": d.category,
                    "mean_mos": d.mean_mos,
                    "std_mos": d.std_mos,
                    "count": d.count,
                    "quantiles": d.quantiles,
                }
                for cat, d in dists.items()
            }

        with open(str(path), "w") as f:  # nosemgrep: cli-path-traversal-open
            json.dump(data, f, indent=2)
        logger.info("calibration_saved", path=str(path))

    @classmethod
    def load(cls, path: str | Path) -> CrossModelCalibrator:
        """Load calibration parameters from JSON.

        Args:
            path (str | Path): Input file path.

        Returns:
            CrossModelCalibrator: Loaded CrossModelCalibrator instance."""
        with open(str(path)) as f:  # nosemgrep: cli-path-traversal-open
            data = json.load(f)

        cal = cls()
        for vname, cats in data.get("categorical", {}).items():
            cal._categorical_maps[vname] = {
                cat: CategoryDistribution(
                    category=d["category"],
                    mean_mos=d["mean_mos"],
                    std_mos=d["std_mos"],
                    count=d["count"],
                    quantiles=d["quantiles"],
                )
                for cat, d in cats.items()
            }
        cal._continuous_maps = data.get("continuous", {})

        logger.info(
            "calibration_loaded",
            path=str(path),
            n_categorical=len(cal._categorical_maps),
            n_continuous=len(cal._continuous_maps),
        )
        return cal


__all__ = [
    "CategoryDistribution",
    "CrossModelCalibrator",
]
