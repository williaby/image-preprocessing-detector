# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Consensus aggregation of multi-model handwriting legibility scores.

Takes raw per-model, per-image score dicts from HwLegibilityScorer and
produces a single consensus score per image, with confidence derived from
model agreement (1 - std).

Example:
    >>> from image_preprocessing_detector.labeling.handwriting.aggregator import (
    ...     aggregate_sheet_scores,
    ...     AggregatedScore,
    ... )
    >>> # model_scores: dict[model_id, dict[img_idx, score_dict]]
    >>> consensus = aggregate_sheet_scores(model_scores, model_weights)
    >>> consensus[1].legibility_score  # float or None
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from image_preprocessing_detector.labeling.handwriting.config import (
    LEGIBILITY_CLASS_ORDER,
    PRESENCE_CLASS_ORDER,
    VALID_LEGIBILITY_CLASSES,
    VALID_PRESENCE_CLASSES,
)


@dataclass
class AggregatedScore:
    """Consensus handwriting score for a single image.

    Attributes:
        image_idx: 1-based position index in the contact sheet.
        presence: Consensus presence class (majority vote).
        presence_score: Weighted mean presence_score across models.
        legibility: Consensus legibility class (majority vote, conservative tie-break).
        legibility_score: Weighted mean legibility_score across models (None if N/A).
        legibility_confidence: Agreement score 0-1 (1 - std; None when < 2 responses).
        model_count: Number of models that returned a valid score.
        model_names: List of model IDs that contributed to the consensus.
        high_disagreement: True when legibility_score std > disagreement_threshold.
        needs_review: True when fewer than min_model_responses responded.
    """

    image_idx: int
    presence: str | None
    presence_score: float | None
    legibility: str | None
    legibility_score: float | None
    legibility_confidence: float | None
    model_count: int
    model_names: list[str]
    high_disagreement: bool
    needs_review: bool


def aggregate_sheet_scores(
    model_scores: dict[str, dict[int, dict[str, Any]]],
    model_weights: dict[str, float] | None = None,
    disagreement_threshold: float = 0.20,
    min_model_responses: int = 2,
) -> dict[int, AggregatedScore]:
    """Aggregate per-model, per-image scores into consensus results.

    Args:
        model_scores: Map from model_id to per-image score dicts.
            Inner dict maps 1-based image index to score dict.
        model_weights: Optional map from model_id to weight. Missing
            models default to weight 1.0.
        disagreement_threshold: Std dev above which the score is flagged
            as high_disagreement.
        min_model_responses: Minimum valid model responses for consensus.
            Images below this are marked needs_review.

    Returns:
        Dict mapping 1-based image index to AggregatedScore.
    """
    weights = model_weights or {}

    # Collect all image indices across all models
    all_indices: set[int] = set()
    for scores in model_scores.values():
        all_indices.update(scores.keys())

    results: dict[int, AggregatedScore] = {}
    for idx in sorted(all_indices):
        results[idx] = _aggregate_single_image(
            idx,
            model_scores,
            weights,
            disagreement_threshold,
            min_model_responses,
        )
    return results


def _accumulate_model_votes(
    entry: dict[str, Any],
    weight: float,
    presence_votes: list[str],
    presence_values: list[tuple[float, float]],
    legibility_votes: list[str],
    legibility_values: list[tuple[float, float]],
) -> None:
    """Accumulate presence and legibility votes from a single model entry.

    Mutates the caller's vote lists in-place, appending only valid class labels
    and (score, weight) pairs where the score is non-null.

    Args:
        entry: Per-image score dict from one model.
        weight: This model's contribution weight.
        presence_votes: Accumulated presence class labels (mutated).
        presence_values: Accumulated (presence_score, weight) pairs (mutated).
        legibility_votes: Accumulated legibility class labels (mutated).
        legibility_values: Accumulated (legibility_score, weight) pairs (mutated).
    """
    presence = entry.get("presence")
    if presence and presence in VALID_PRESENCE_CLASSES:
        presence_votes.append(presence)
        if (ps := entry.get("presence_score")) is not None:
            presence_values.append((float(ps), weight))

    legibility = entry.get("legibility")
    if legibility and legibility in VALID_LEGIBILITY_CLASSES:
        legibility_votes.append(legibility)
        if (ls := entry.get("legibility_score")) is not None:
            legibility_values.append((float(ls), weight))


def _aggregate_single_image(
    idx: int,
    model_scores: dict[str, dict[int, dict[str, Any]]],
    weights: dict[str, float],
    disagreement_threshold: float,
    min_model_responses: int,
) -> AggregatedScore:
    """Compute consensus for a single image index.

    Args:
        idx: 1-based image index.
        model_scores: Full model_scores mapping.
        weights: Model weight overrides.
        disagreement_threshold: Std threshold for high_disagreement flag.
        min_model_responses: Minimum valid responses required.

    Returns:
        AggregatedScore for this image.
    """
    valid_model_ids: list[str] = []
    presence_votes: list[str] = []
    presence_values: list[tuple[float, float]] = []  # (score, weight)
    legibility_votes: list[str] = []
    legibility_values: list[tuple[float, float]] = []  # (score, weight)

    for model_id, per_image in model_scores.items():
        entry = per_image.get(idx)
        if entry is None or entry.get("needs_review"):
            continue

        valid_model_ids.append(model_id)
        _accumulate_model_votes(
            entry,
            weights.get(model_id, 1.0),
            presence_votes,
            presence_values,
            legibility_votes,
            legibility_values,
        )

    n_valid = len(valid_model_ids)
    needs_review = n_valid < min_model_responses

    consensus_presence = _majority_vote(presence_votes, PRESENCE_CLASS_ORDER)
    consensus_legibility = _majority_vote(legibility_votes, LEGIBILITY_CLASS_ORDER)

    # Force NOT_APPLICABLE when presence is NONE
    if consensus_presence == "NONE":
        consensus_legibility = "NOT_APPLICABLE"
        legibility_values = []

    presence_score = _weighted_mean(presence_values)
    legibility_score = _weighted_mean(legibility_values)
    legibility_confidence, high_disagreement = _compute_confidence(
        legibility_values, disagreement_threshold
    )

    return AggregatedScore(
        image_idx=idx,
        presence=consensus_presence,
        presence_score=presence_score,
        legibility=consensus_legibility,
        legibility_score=legibility_score,
        legibility_confidence=legibility_confidence,
        model_count=n_valid,
        model_names=valid_model_ids,
        high_disagreement=high_disagreement,
        needs_review=needs_review,
    )


def _majority_vote(votes: list[str], order: dict[str, int]) -> str | None:
    """Return majority-vote winner, breaking ties conservatively (lower quality).

    Args:
        votes: List of class labels from each model.
        order: Dict mapping class label to ordinal (lower = worse quality).

    Returns:
        Winning class label, or None if votes is empty.
    """
    if not votes:
        return None

    counts: dict[str, int] = {}
    for v in votes:
        counts[v] = counts.get(v, 0) + 1

    max_count = max(counts.values())
    candidates = [cls for cls, cnt in counts.items() if cnt == max_count]

    # Conservative tie-break: pick the lower quality class
    return min(candidates, key=lambda c: order.get(c, 0))


def _weighted_mean(values: list[tuple[float, float]]) -> float | None:
    """Compute weighted mean of (value, weight) pairs.

    Args:
        values: List of (score, weight) tuples.

    Returns:
        Weighted mean float, or None if values is empty.
    """
    if not values:
        return None
    total_weight = sum(w for _, w in values)
    if total_weight == 0:
        return None
    return sum(v * w for v, w in values) / total_weight


def _compute_confidence(
    values: list[tuple[float, float]],
    threshold: float,
) -> tuple[float | None, bool]:
    """Compute agreement confidence (1 - std) and disagreement flag.

    Args:
        values: List of (score, weight) tuples from each model.
        threshold: Std dev above which disagreement is flagged.

    Returns:
        Tuple of (confidence, high_disagreement). Confidence is None
        when fewer than 2 values are available.
    """
    if len(values) < 2:
        return None, False

    scores = [v for v, _ in values]
    n = len(scores)
    mean = sum(scores) / n
    variance = sum((s - mean) ** 2 for s in scores) / n
    std = math.sqrt(variance)

    confidence = max(0.0, 1.0 - std)
    high_disagreement = std > threshold
    return confidence, high_disagreement
