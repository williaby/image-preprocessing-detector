"""Prompt templates and response parsing for handwriting legibility scoring.

Generates per-sheet prompts that instruct vision models to score each
labeled cell in a contact sheet, and parses the structured JSON response
back into per-image score dicts.

Example:
    >>> from image_preprocessing_detector.labeling.handwriting.prompts import (
    ...     build_sheet_prompt,
    ...     parse_sheet_response,
    ... )
    >>> messages = build_sheet_prompt(n_images=12)
    >>> # (send to model, receive raw dict)
    >>> scores = parse_sheet_response(raw, n_images=12)
"""

from __future__ import annotations

import re
from typing import Any

from image_preprocessing_detector.labeling.handwriting.config import (
    LEGIBILITY_CLASS_TO_SCORE,
    VALID_LEGIBILITY_CLASSES,
    VALID_PRESENCE_CLASSES,
)

# ──────────────────────────────────────────────
# System prompt
# ──────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a handwriting quality assessor. You will be shown a contact sheet \
containing multiple handwriting images arranged in a numbered grid. Each image \
has a white "#N" badge in its top-left corner identifying it.

For EACH image in the grid, assess two independent dimensions:

PRESENCE - how much of the image area contains handwriting:
  NONE         = no handwriting visible at all (printed text, blank, non-text image)
  MARGINAL     = traces or annotations only (<10% of area)
  PARTIAL      = handwriting alongside printed text (10-50% of area)
  SUBSTANTIAL  = mostly handwriting (50-90% of area)
  DOMINANT     = image is almost entirely handwriting (>90% of area)

LEGIBILITY - how readable the handwriting is (only when presence != NONE):
  NOT_APPLICABLE = presence is NONE (no handwriting to score)
  ILLEGIBLE      = cannot be read at all (severe degradation, crossed-out, \
smeared beyond recognition)
  POOR           = very difficult to read; most words require guessing
  FAIR           = readable with effort; some words unclear
  GOOD           = mostly clear; occasional ambiguous letters
  EXCELLENT      = clear and easy to read throughout

Scoring rules:
- Set legibility to NOT_APPLICABLE when presence is NONE
- legibility_score must be null when presence is NONE
- Score each image INDEPENDENTLY - do not compare images to each other
- Focus on ink clarity, stroke definition, letter spacing, and line separation
- Degradation (blur, fading, stains) that makes handwriting harder to read \
  LOWERS legibility_score
- Respond ONLY with a valid JSON object - no markdown fences, no extra text

Required output format (keys are image numbers as strings):
{"1": {"presence": "DOMINANT", "presence_score": 0.85, \
"legibility": "GOOD", "legibility_score": 0.72},
 "2": {"presence": "NONE", "presence_score": 0.02, \
"legibility": "NOT_APPLICABLE", "legibility_score": null}}"""


def build_sheet_prompt(n_images: int) -> list[dict[str, Any]]:
    """Build chat messages for contact-sheet legibility scoring.

    The image content block must be appended by the caller after this
    function returns, since encoding is handled by the scorer.

    Args:
        n_images: Number of labeled images in the contact sheet (1-12).

    Returns:
        List of chat message dicts ready for the OpenRouter API.
        Caller appends the base64 image block to messages[1]["content"].
    """
    image_list = ", ".join(f'"{i}"' for i in range(1, n_images + 1))
    user_text = (
        f"Score all {n_images} handwriting images in this contact sheet. "
        f"Return scores for image numbers: {image_list}."
    )
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
            ],
        },
    ]


# ──────────────────────────────────────────────
# Response parsing
# ──────────────────────────────────────────────


def parse_sheet_response(
    raw: dict[str, Any],
    n_images: int,
) -> dict[int, dict[str, Any]]:
    """Parse a model's JSON response into per-image score dicts.

    Handles:
    - Keys as string numbers ("1"-"12") or integer keys
    - Missing fields substituted with conservative defaults
    - Invalid enum values coerced to nearest valid class or None
    - Partial responses (missing images marked as needs_review)

    Args:
        raw: Parsed JSON dict from the model (output of _extract_json).
        n_images: Expected number of images on the sheet.

    Returns:
        Dict mapping image index (1-based int) to a score dict with keys:
        ``presence``, ``presence_score``, ``legibility``, ``legibility_score``,
        ``needs_review``.
    """
    results: dict[int, dict[str, Any]] = {}

    for idx in range(1, n_images + 1):
        # Accept both string and int keys from model responses
        entry = raw.get(str(idx))
        if entry is None or not isinstance(entry, dict):
            results[idx] = _make_needs_review(idx)
            continue

        presence = _coerce_presence(entry.get("presence"))
        presence_score = _coerce_score(entry.get("presence_score"))
        legibility = _coerce_legibility(entry.get("legibility"), presence)
        legibility_score = _coerce_legibility_score(
            entry.get("legibility_score"), legibility
        )

        results[idx] = {
            "presence": presence,
            "presence_score": presence_score,
            "legibility": legibility,
            "legibility_score": legibility_score,
            "needs_review": False,
        }

    return results


# ──────────────────────────────────────────────
# Coercion helpers
# ──────────────────────────────────────────────


def _coerce_presence(value: Any) -> str:
    """Coerce raw presence value to a valid enum string.

    Args:
        value: Raw value from model response.

    Returns:
        Valid VALID_PRESENCE_CLASSES member, or "NONE" as safe fallback.
    """
    if value is None:
        return "NONE"
    normalised = str(value).upper().strip()
    # Handle synonym aliases that models sometimes produce
    _synonyms: dict[str, str] = {
        "SPARSE": "MARGINAL",
        "MODERATE": "PARTIAL",
        "FULL": "DOMINANT",
        "YES": "SUBSTANTIAL",
        "NO": "NONE",
    }
    normalised = _synonyms.get(normalised, normalised)
    return normalised if normalised in VALID_PRESENCE_CLASSES else "NONE"


def _coerce_legibility(value: Any, presence: str) -> str:
    """Coerce raw legibility value to a valid enum string.

    Args:
        value: Raw value from model response.
        presence: Already-coerced presence class for this image.

    Returns:
        Valid VALID_LEGIBILITY_CLASSES member. Returns NOT_APPLICABLE
        when presence is NONE regardless of model output.
    """
    if presence == "NONE":
        return "NOT_APPLICABLE"
    if value is None:
        return "FAIR"  # Conservative middle-ground default
    normalised = str(value).upper().strip()
    _synonyms: dict[str, str] = {
        "N/A": "NOT_APPLICABLE",
        "NA": "NOT_APPLICABLE",
        "UNREADABLE": "ILLEGIBLE",
        "READABLE": "GOOD",
        "VERY_GOOD": "EXCELLENT",
    }
    normalised = _synonyms.get(normalised, normalised)
    return normalised if normalised in VALID_LEGIBILITY_CLASSES else "FAIR"


def _coerce_score(value: Any) -> float | None:
    """Coerce a raw score value to a clamped float or None.

    Args:
        value: Raw score value from model response.

    Returns:
        Float in [0.0, 1.0] or None if value is null/missing.
    """
    if value is None:
        return None
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, score))


def _coerce_legibility_score(value: Any, legibility: str) -> float | None:
    """Coerce legibility score, enforcing null for NOT_APPLICABLE.

    Args:
        value: Raw legibility_score from model response.
        legibility: Already-coerced legibility class.

    Returns:
        Float in [0.0, 1.0], or None when legibility is NOT_APPLICABLE
        or when the model returned null.
    """
    if legibility == "NOT_APPLICABLE":
        return None
    score = _coerce_score(value)
    if score is None:
        # Fall back to class midpoint so downstream aggregation still works
        return LEGIBILITY_CLASS_TO_SCORE.get(legibility)
    return score


def _make_needs_review(_idx: int) -> dict[str, Any]:
    """Create a placeholder result flagged as needs_review.

    Used when a model response is missing an image's entry entirely.

    Args:
        idx: 1-based image index.

    Returns:
        Score dict with all fields set to None and needs_review=True.
    """
    return {
        "presence": None,
        "presence_score": None,
        "legibility": None,
        "legibility_score": None,
        "needs_review": True,
    }


def extract_json_from_response(text: str) -> dict[str, Any]:
    """Extract a JSON object from raw model response text.

    Handles LLM response patterns:
    - Clean JSON
    - JSON inside markdown code fences (```json ... ```)
    - JSON with leading/trailing prose

    Args:
        text: Raw model response content string.

    Returns:
        Parsed JSON dict.

    Raises:
        ValueError: If no valid JSON object can be extracted.
    """
    import json

    stripped = text.strip()

    # Direct parse
    try:
        result = json.loads(stripped)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass  # Try next parsing strategy

    # Markdown code fence
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", stripped, re.DOTALL)
    if fence_match:
        try:
            result = json.loads(fence_match.group(1).strip())
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass  # Try next parsing strategy

    # First {...} with possible nested braces (allows one level of nesting)
    nested_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", stripped, re.DOTALL)
    if nested_match:
        try:
            result = json.loads(nested_match.group(0))
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass  # All strategies exhausted; raise ValueError below

    msg = f"Could not extract valid JSON from response: {text[:300]}"
    raise ValueError(msg)
