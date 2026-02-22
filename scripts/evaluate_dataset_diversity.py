#!/usr/bin/env python3
"""Dataset Diversity Report (DDR) generator.

Evaluates training datasets across 14 diversity dimensions, generates
per-dataset markdown reports, and runs OOD leakage checks.

Usage:
    # Evaluate a single dataset
    python scripts/evaluate_dataset_diversity.py --dataset orientation \\
        --output docs/datasets/diversity_reports/

    # Run OOD check only
    python scripts/evaluate_dataset_diversity.py --ood-check-only

    # List available datasets
    python scripts/evaluate_dataset_diversity.py --list-datasets
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import click

# ──────────────────────────────────────────────────────────────────────────────
# Dataset Registry
# ──────────────────────────────────────────────────────────────────────────────

# Known training datasets with their primary heads and L2 metadata paths
DATASET_REGISTRY: dict[str, dict[str, Any]] = {
    "orientation": {
        "heads": ["MV4-H1 (orientation 4-class)", "SigLIP-G3 (orientation)"],
        "images": 50_000,
        "l2_metadata": None,  # No L2 metadata — orientation-specific manifest
        "manifest_path": "E:/image_detection/03_training_datasets/orientation/labels/train_labels.jsonl",
        "notes": "50K images; 60% real DocLayNet/RVL-CDIP + 40% v3 synthetic",
        # Orientation manifest uses non-standard field names — alias to DDR standard
        "field_aliases": {
            "orientation_class": "orientation",  # int {0,1,2,3} → orientation dim
            "orientation_degrees": "skew_angle",  # degrees → skew dim (optional)
            "source_dataset": "source",  # dataset name → source dim
        },
    },
    "skew": {
        "heads": ["MV4-H2 (skew regression)", "SigLIP-G3 (skew)"],
        "images": 90_412,
        "l2_metadata": None,
        "manifest_path": "E:/image_detection/03_training_datasets/skew/train/labels.json",
        "notes": "90K images; 71K synthetic + 19K natural scans",
        # Skew manifest uses `angle` instead of `skew_angle`
        "field_aliases": {
            "angle": "skew_angle",
        },
    },
    "resolution-quality": {
        "heads": ["MV4-H3 (resolution quality)", "SigLIP-G5 (resolution)"],
        "images": 5_500,
        "l2_metadata": "/mnt/e/image_detection/metadata_registry/json/diqa5000_metadata.json",
        "manifest_path": "results/diqa5000_resolution_labels.json",
        "notes": "5.5K DIQA-5000 images with char-height labels",
    },
    "iqa-curated": {
        "heads": ["SigLIP-G1 (IQA 6 heads)"],
        "images": 16_000,
        "l2_metadata": None,
        "manifest_path": None,
        "notes": "16-23K curated IQA samples; excludes iqa_phase7_165k (FLAWED)",
    },
    "iqa-synthetic": {
        "heads": ["SigLIP-G1 (IQA pre-training)"],
        "images": 100_000,
        "l2_metadata": None,
        "manifest_path": None,
        "notes": "100K planned synthetic IQA; tier_0 labels only",
    },
    "handwriting": {
        "heads": ["SigLIP-G4 (5 handwriting heads)"],
        "images": 60_000,
        "l2_metadata": None,
        "manifest_path": None,
        "notes": "60K planned; non-Latin scripts completely absent currently",
    },
    "capture-method": {
        "heads": ["SigLIP-G5 (capture method 7-class)"],
        "images": 50_000,
        "l2_metadata": None,
        "manifest_path": None,
        "notes": "50K planned; modern scanners completely absent",
    },
    "shadow": {
        "heads": ["SigLIP-G5 (shadow regression)"],
        "images": 15_000,
        "l2_metadata": "/mnt/e/image_detection/metadata_registry/json/sd7k_metadata.json",
        "manifest_path": "E:/image_detection/metadata_registry/json/sd7k_metadata.json",
        "notes": "sd7k (7,239) + wsrd (~2,200) paired shadow images; shadow_severity in L2",
    },
    "warping": {
        "heads": ["SigLIP-G5 (warping regression)"],
        "images": 20_000,
        "l2_metadata": "/mnt/e/image_detection/metadata_registry/json/warpdoc_metadata.json",
        "manifest_path": "E:/image_detection/metadata_registry/json/warpdoc_metadata.json",
        "notes": "warpdoc (1,020) paired warping images; warping_severity in L2",
    },
    "synth-multiscript-v3": {
        "heads": ["SigLIP-G2 (script detection 19-27 classes)"],
        "images": 350_012,
        "l2_metadata": None,
        "manifest_path": "gs://image_detection_b/synth_multiscript_v3/splits.jsonl",
        "notes": "350K on GCS (complete total; 8.6x class imbalance from generator bug); Mongolian absent",
    },
}

# The 14 diversity dimensions (from DATASET_DIVERSITY_REQUIREMENTS.md)
DIVERSITY_DIMENSIONS: list[str] = [
    "script",  # ISO 15924 script code
    "orientation",  # 0/90/180/270 degrees
    "source",  # scanned/camera/born_digital
    "shadow",  # 0-1 severity
    "warping",  # 0-1 severity
    "document_type",  # form/book/receipt/newspaper/etc
    "color_mode",  # binarized/grayscale/color
    "document_age",  # modern/aged/historical
    "language",  # ISO 639-1 language code
    "resolution_dpi",  # effective DPI bucket
    "capture_device",  # scanner/phone/born_digital/screen_recapture
    "noise_level",  # 0-1 severity
    "blur_level",  # 0-1 severity
    "compression",  # 0-1 severity
]

# Wild conditions per dataset (from WILD_CONDITIONS_ANALYSIS.md)
# Maps dataset name to list of (condition, covered) tuples
WILD_CONDITIONS: dict[str, list[tuple[str, str]]] = {
    "orientation": [
        ("Symmetric documents (near-identical 0°/180°)", "❌ Missing"),
        ("Non-Latin RTL documents (Arabic/Hebrew)", "⚠️ Partial"),
        ("Camera perspective vs pure rotation", "⚠️ Partial"),
        ("Partial/cropped page", "❌ Missing"),
    ],
    "skew": [
        ("Camera perspective vs pure rotation (>30°)", "⚠️ Partial"),
        ("Combined skew + warping (non-flat page)", "❌ Missing"),
        ("Near-zero skew distribution (<2°)", "⚠️ Partial"),
    ],
    "resolution-quality": [
        ("Vector PDF rendered at low effective DPI", "❌ Missing"),
        ("Upscaled raster (bicubic 2x-4x)", "❌ Missing"),
        ("Mixed raster/vector document", "❌ Missing"),
        ("Sub-pixel ClearType rendering", "❌ Missing"),
    ],
    "iqa-curated": [
        ("Multiply-distorted (5+ types simultaneously)", "❌ Missing"),
        ("Mobile phone motion blur + defocus combined", "⚠️ Partial"),
        ("Book gutter shadow gradient + curvature", "❌ Missing"),
        ("Aged/historical documents", "❌ Missing"),
        ("Fax artifacts", "❌ Missing"),
        ("Screen recapture (RGB aliasing + moiré)", "❌ Missing"),
    ],
    "iqa-synthetic": [
        ("Multiply-distorted (5+ types simultaneously)", "❌ Missing"),
        ("Non-linear quality calibration", "❌ Missing"),
    ],
    "handwriting": [
        ("Arabic cursive handwriting", "❌ Missing"),
        ("CJK character handwriting", "❌ Missing"),
        ("Devanagari handwriting", "❌ Missing"),
        ("Cyrillic handwriting", "❌ Missing"),
        ("Form fill-in handwriting", "❌ Missing"),
    ],
    "capture-method": [
        ("Modern flatbed scanner (2020+ CIS)", "❌ Missing"),
        ("ADF scanner with curl artifacts", "❌ Missing"),
        ("Screen recapture (phone→monitor)", "❌ Missing"),
    ],
    "shadow": [
        ("Book gutter/spine shadow", "❌ Missing"),
        ("Finger-cast shadows", "⚠️ Partial"),
        ("Multiple overlapping shadows", "❌ Missing"),
    ],
    "warping": [
        ("Book spine cylindrical distortion", "⚠️ Partial"),
        ("Crumpled/creased pages", "❌ Missing"),
        ("Combined warp + skew + blur", "❌ Missing"),
    ],
    "synth-multiscript-v3": [
        ("Mongolian vertical script", "❌ Missing"),
        ("Historical/archaic variants (Fraktur, Ottoman)", "❌ Missing"),
        ("Decorative/display fonts (Tier 3-4 scripts)", "❌ Missing"),
        ("Script degraded near-illegibly", "⚠️ Partial"),
    ],
}


# ──────────────────────────────────────────────────────────────────────────────
# OOD Leakage Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _compute_sha256(image_path: Path) -> str:
    """Compute SHA256 hash of image file bytes.

    Args:
        image_path: Absolute path to the image file.

    Returns:
        Hex-encoded SHA256 digest string.
    """
    hasher = hashlib.sha256()
    with image_path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _load_ood_registry(ood_registry_path: Path) -> set[str]:
    """Load OOD registry SHA256 hashes from a JSONL file.

    Returns an empty set if the registry file is missing or empty.
    Each line must be a JSON object with a ``sha256`` key.

    Args:
        ood_registry_path: Path to ``metadata_registry/ood_registry.jsonl``.

    Returns:
        Set of SHA256 hex strings for OOD-reserved images.
    """
    if not ood_registry_path.exists():
        return set()
    hashes: set[str] = set()
    with ood_registry_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if sha256 := entry.get("sha256"):
                    hashes.add(sha256)
            except json.JSONDecodeError:
                continue
    return hashes


def _check_ood_leakage_for_ddr(
    image_paths: list[Path],
    ood_registry_path: Path,
) -> tuple[bool, int]:
    """Check for OOD leakage among a list of image paths.

    Computes SHA256 for each existing image and compares against the
    OOD registry.  Returns immediately if the registry is empty.

    Args:
        image_paths: List of resolved image file paths to check.
        ood_registry_path: Path to ``metadata_registry/ood_registry.jsonl``.

    Returns:
        Tuple of ``(has_leakage, leakage_count)`` where ``has_leakage``
        is ``True`` when at least one OOD image was found.
    """
    ood_hashes = _load_ood_registry(ood_registry_path)
    if not ood_hashes:
        return False, 0

    leakage_count = 0
    for img_path in image_paths:
        if not img_path.exists():
            continue
        if _compute_sha256(img_path) in ood_hashes:
            leakage_count += 1

    return leakage_count > 0, leakage_count


# ──────────────────────────────────────────────────────────────────────────────
# Diversity Scoring
# ──────────────────────────────────────────────────────────────────────────────


def _compute_wild_condition_score(
    dataset_name: str,
) -> tuple[float, list[dict[str, str]]]:
    """Compute wild condition coverage score (0–100).

    Full credit for covered conditions, half credit for partial.
    Datasets with no defined conditions score 0.

    Args:
        dataset_name: Key in ``WILD_CONDITIONS``.

    Returns:
        Tuple of ``(score_0_100, conditions_list)`` where each entry in
        ``conditions_list`` is ``{"condition": str, "status": str}``.
    """
    conditions = WILD_CONDITIONS.get(dataset_name, [])
    if not conditions:
        return 0.0, []

    covered = sum(1 for _, status in conditions if status == "✅ Covered")
    partial = sum(1 for _, status in conditions if status == "⚠️ Partial")
    total = len(conditions)

    score = (covered + partial * 0.5) / total * 100
    conditions_list = [
        {"condition": cond, "status": status} for cond, status in conditions
    ]
    return score, conditions_list


def _chi_square_test(
    observed: dict[str, int],
) -> tuple[float, bool]:
    """Chi-square uniformity test against a uniform expected distribution.

    Uses the Wilson–Hilferty approximation to derive the critical value
    at p = 0.01 without requiring SciPy.

    Args:
        observed: Mapping of category label → count.

    Returns:
        Tuple of ``(chi_square_stat, passes)`` where ``passes`` is
        ``True`` when the test does **not** reject uniformity (p > 0.01).
    """
    total = sum(observed.values())
    n_cats = len(observed)
    if total == 0 or n_cats < 2:
        return 0.0, True

    expected_per_cat = total / n_cats
    chi_sq = sum(
        (count - expected_per_cat) ** 2 / expected_per_cat
        for count in observed.values()
        if expected_per_cat > 0
    )

    # Wilson–Hilferty approximation for chi-square critical value at p=0.01
    df = n_cats - 1
    z_99 = 2.326  # z_{0.99} one-tailed
    wh_factor = 1 - 2 / (9 * max(df, 1)) + z_99 * math.sqrt(2 / (9 * max(df, 1)))
    critical_value = df * (wh_factor**3)

    return chi_sq, chi_sq < critical_value


def _label_quality_score(
    samples: list[dict[str, Any]],
    required_fields: list[str],
) -> dict[str, Any]:
    """Compute label quality metrics from a list of sample dicts.

    Args:
        samples: List of manifest-style sample dicts.
        required_fields: Field names that must be present and non-null
            for a sample to be considered complete.

    Returns:
        Dict with keys ``completeness`` (float %), ``tier_distribution``
        (dict str→int), ``per_field_coverage`` (dict str→float %),
        and ``total_samples`` (int).
    """
    if not samples:
        return {
            "completeness": 0.0,
            "tier_distribution": {},
            "per_field_coverage": {},
            "total_samples": 0,
        }

    total = len(samples)
    tier_counts: Counter[str] = Counter()
    field_coverage: dict[str, int] = defaultdict(int)
    complete_count = 0

    for sample in samples:
        label_tier = sample.get("label_tier", sample.get("tier", "tier_unknown"))
        tier_counts[str(label_tier)] += 1

        all_present = True
        for field in required_fields:
            val = sample.get(field)
            if val is not None and val != "":
                field_coverage[field] += 1
            else:
                all_present = False

        if all_present:
            complete_count += 1

    return {
        "completeness": complete_count / total * 100,
        "tier_distribution": dict(tier_counts),
        "per_field_coverage": {
            field: count / total * 100 for field, count in field_coverage.items()
        },
        "total_samples": total,
    }


def _compute_overall_score(
    wild_score: float,
    diversity_score: float,
    label_score: float,
    statistical_score: float,
    leakage_passed: bool,
) -> float:
    """Compute weighted overall diversity score (0–100).

    Weights: 30% wild condition coverage, 30% 14-dimension diversity,
    20% label quality, 20% statistical tests.  OOD leakage failure
    overrides all components and returns 0.

    Args:
        wild_score: Wild condition coverage score (0–100).
        diversity_score: 14-dimension diversity score (0–100).
        label_score: Label quality completeness score (0–100).
        statistical_score: Fraction of passing chi-square tests × 100.
        leakage_passed: False if OOD leakage was detected.

    Returns:
        Weighted overall score clamped to [0, 100].
    """
    if not leakage_passed:
        return 0.0

    return (
        wild_score * 0.30
        + diversity_score * 0.30
        + label_score * 0.20
        + statistical_score * 0.20
    )


# ──────────────────────────────────────────────────────────────────────────────
# Sample Loading
# ──────────────────────────────────────────────────────────────────────────────


def _load_gcs_jsonl(gcs_path: str, max_lines: int = 10_000) -> list[dict[str, Any]]:
    """Stream up to *max_lines* records from a GCS JSONL file via ``gsutil cat``.

    Args:
        gcs_path: GCS URI (``gs://bucket/path/file.jsonl``).
        max_lines: Maximum number of lines to read (avoids downloading huge files).

    Returns:
        List of parsed JSON dicts, or ``[]`` on any error.
    """
    try:
        result = subprocess.run(
            ["gsutil", "cat", gcs_path],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            return []
        samples: list[dict[str, Any]] = []
        for line in result.stdout.splitlines()[:max_lines]:
            line = line.strip()
            if not line:
                continue
            try:
                samples.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return samples
    except (OSError, subprocess.TimeoutExpired, FileNotFoundError):
        return []


def _flatten_l2_sample(sample: dict[str, Any]) -> dict[str, Any]:
    """Flatten L2 metadata enrichment fields to the top level for DDR analysis.

    L2 metadata files store enrichment data under
    ``enrichments.versions[-1].data.*``.  This function promotes those fields
    to the top level and adds DDR-friendly aliases:

    - ``shadow_severity``    → ``shadow``
    - ``warping_severity``   → ``warping``
    - ``capture_method``     → ``source``  (always; L2 top-level ``source`` is a
                                            provenance dict, not the DDR dimension)
    - ``source.original_path`` → ``image_path`` (if no flat image_path present)

    Args:
        sample: Raw sample dict from an L2 metadata file.

    Returns:
        Flattened sample dict, or the original if no enrichment data found.
    """
    if "enrichments" not in sample:
        return sample
    try:
        data: dict[str, Any] = sample["enrichments"]["versions"][-1]["data"]
    except (KeyError, IndexError, TypeError):
        return sample

    flat = dict(sample)
    flat.update(data)

    # Severity aliases
    if "shadow_severity" in flat and "shadow" not in flat:
        flat["shadow"] = flat["shadow_severity"]
    if "warping_severity" in flat and "warping" not in flat:
        flat["warping"] = flat["warping_severity"]

    # L2 top-level ``source`` is a provenance dict — override with capture_method string
    if "capture_method" in flat:
        flat["source"] = str(flat["capture_method"])

    # Derive image_path from L2 provenance dict if no flat string is present
    if not isinstance(flat.get("image_path"), str):
        l2_source = sample.get("source", {})
        if isinstance(l2_source, dict):
            flat["image_path"] = l2_source.get("original_path", "")

    return flat


def _load_local_manifest(path: Path) -> list[dict[str, Any]]:
    """Load sample dicts from a local JSON or JSONL file.

    Handles three formats:
    - JSON list: ``[{...}, ...]``
    - JSON dict with ``"samples"`` key: ``{"samples": [{...}, ...]}``
    - JSON dict mapping filenames to label dicts (skew/orientation labels.json):
      ``{"img.jpg": {"angle": 1.2, ...}, ...}`` — each entry gains an
      ``"image_path"`` key set to the filename if not already present.
    - JSONL: one JSON object per line.

    L2 metadata files (``{dataset}_metadata.json``) use the ``{"samples": [...]}``
    format with nested ``enrichments`` — ``_flatten_l2_sample`` is applied
    automatically when the first sample contains an ``"enrichments"`` key.

    Args:
        path: Path to the local manifest file.

    Returns:
        List of sample dicts, or ``[]`` on failure.
    """
    try:
        if path.suffix == ".jsonl":
            samples: list[dict[str, Any]] = []
            with path.open() as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            samples.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            return samples

        with path.open() as f:
            data = json.load(f)

        raw_samples: list[dict[str, Any]]
        if isinstance(data, list):
            raw_samples = data  # type: ignore[assignment]
        elif isinstance(data, dict) and "samples" in data:
            raw_samples = data["samples"]  # type: ignore[assignment]
        elif isinstance(data, dict):
            # Dict-keyed format: {filename: {label_fields}}
            raw_samples = []
            for filename, fields in data.items():
                if isinstance(fields, dict):
                    sample = dict(fields)
                    if "image_path" not in sample:
                        sample["image_path"] = filename
                    raw_samples.append(sample)
        else:
            return []

        # Flatten L2 enrichment fields if this is an L2 metadata file
        if raw_samples and "enrichments" in raw_samples[0]:
            return [_flatten_l2_sample(s) for s in raw_samples]
        return raw_samples
    except (json.JSONDecodeError, OSError):
        pass
    return []


def _load_dataset_samples(dataset_name: str) -> list[dict[str, Any]]:
    """Attempt to load manifest samples for a dataset.

    Supports local JSON/JSONL files, E:/ Windows paths (converted to /mnt/e/),
    directory paths (searches for merge_manifest.json / manifest.json /
    train/labels.json), and gs:// GCS paths (sampled via ``gsutil cat``).

    Args:
        dataset_name: Key in ``DATASET_REGISTRY``.

    Returns:
        List of sample dicts from the manifest, or ``[]`` on failure.
    """
    registry = DATASET_REGISTRY.get(dataset_name, {})
    manifest_path: str | None = registry.get("manifest_path")

    if not manifest_path:
        return []

    # Convert Windows E:/ paths to WSL /mnt/e/ paths
    if manifest_path.startswith("E:/"):
        manifest_path = "/mnt/e/" + manifest_path[3:]

    # GCS paths: stream via gsutil cat (capped at 10K lines to avoid huge downloads)
    if manifest_path.startswith("gs://"):
        return _load_gcs_jsonl(manifest_path, max_lines=10_000)

    path = Path(manifest_path)
    try:
        if not path.exists():
            return []
    except OSError:
        return []  # Drive not mounted (e.g. /mnt/e not available)

    # Directory: search for a known manifest file inside
    if path.is_dir():
        for candidate_name in (
            "merge_manifest.json",
            "manifest.json",
            "train/labels.json",
        ):
            candidate = path / candidate_name
            try:
                if candidate.exists():
                    return _load_local_manifest(candidate)
            except OSError:
                continue
        return []

    samples = _load_local_manifest(path)

    # Apply dataset-specific field aliases (e.g. orientation manifest uses
    # orientation_class/source_dataset instead of orientation/source).
    aliases: dict[str, str] = registry.get("field_aliases", {})
    if aliases and samples:
        aliased = []
        for s in samples:
            s2 = dict(s)
            for src_key, dst_key in aliases.items():
                if src_key in s2 and dst_key not in s2:
                    s2[dst_key] = s2[src_key]
            aliased.append(s2)
        return aliased

    return samples


# ──────────────────────────────────────────────────────────────────────────────
# Required Fields Registry
# ──────────────────────────────────────────────────────────────────────────────


def _get_required_fields(dataset_name: str) -> list[str]:
    """Return the minimum required label fields for a dataset.

    Args:
        dataset_name: Key in ``DATASET_REGISTRY``.

    Returns:
        List of field name strings that must be non-null for a complete sample.
    """
    field_map: dict[str, list[str]] = {
        "orientation": [
            "image_path",
            "orientation",
            "source",
        ],  # orientation_class/source_dataset aliased
        "skew": ["image_path", "skew_angle", "orientation"],
        "resolution-quality": ["image_path", "resolution_score", "char_height"],
        "iqa-curated": ["image_path", "blur", "noise", "contrast", "overall"],
        "synth-multiscript-v3": ["image_path", "script", "orientation", "source"],
        "shadow": ["image_path", "shadow", "source"],
        "warping": ["image_path", "warping", "source"],
        "capture-method": ["image_path", "source"],
        "handwriting": ["image_path", "handwriting_presence", "handwriting_script"],
    }
    return field_map.get(dataset_name, ["image_path"])


# ──────────────────────────────────────────────────────────────────────────────
# Markdown Rendering
# ──────────────────────────────────────────────────────────────────────────────


def _render_section_1(
    wild_score: float,
    wild_conditions: list[dict[str, str]],
    covered_count: int,
    partial_count: int,
    missing_count: int,
) -> list[str]:
    """Render Section 1: Wild Condition Coverage Matrix.

    Args:
        wild_score: Coverage score (0–100).
        wild_conditions: List of ``{"condition": str, "status": str}`` dicts.
        covered_count: Number of fully covered conditions.
        partial_count: Number of partially covered conditions.
        missing_count: Number of missing conditions.

    Returns:
        List of markdown lines for Section 1.
    """
    total = len(wild_conditions)
    lines = [
        "## Section 1: Wild Condition Coverage Matrix",
        "",
        f"**Score**: {wild_score:.1f}/100",
        (
            f"**Summary**: {covered_count} covered / {partial_count} partial / "
            f"{missing_count} missing ({total} total conditions)"
        ),
        "",
        "| Wild Condition | Status |",
        "| --- | --- |",
    ]
    for cond in wild_conditions:
        lines.append(f"| {cond['condition']} | {cond['status']} |")
    if not wild_conditions:
        lines.append("| *No wild conditions defined for this dataset* | — |")
    return lines


def _render_section_2(
    diversity_score: float,
    dim_distributions: dict[str, Counter[str]],
    sample_count: int,
) -> list[str]:
    """Render Section 2: 14-Dimension Diversity Scores.

    Args:
        diversity_score: Average dimension score (0–100).
        dim_distributions: Mapping of dimension → value Counter.
        sample_count: Number of samples with dimension data.

    Returns:
        List of markdown lines for Section 2.
    """
    lines = [
        "## Section 2: 14-Dimension Diversity Scores",
        "",
        f"**Score**: {diversity_score:.1f}/100",
        f"**Samples with dimension data**: {sample_count:,}",
        "",
        "| Dimension | Unique Values | Min Coverage % | Score |",
        "| --- | --- | --- | --- |",
    ]
    for dim in DIVERSITY_DIMENSIONS:
        dist = dim_distributions.get(dim, Counter())
        if not dist:
            lines.append(f"| {dim} | — | — | ⚠️ Not measured |")
            continue
        total_in_dim = sum(dist.values())
        n_unique = len(dist)
        min_pct = min(v / total_in_dim * 100 for v in dist.values())
        if n_unique > 1 and min_pct >= 5:
            dim_score_val, flag = 100.0, "✅"
        elif n_unique > 1:
            dim_score_val, flag = 50.0, "⚠️"
        else:
            dim_score_val, flag = 0.0, "❌"
        lines.append(
            f"| {dim} | {n_unique} | {min_pct:.1f}% | {flag} {dim_score_val:.0f} |"
        )
    return lines


def _render_section_3(
    label_score: float,
    label_quality: dict[str, Any],
    required_fields: list[str],
) -> list[str]:
    """Render Section 3: Label Quality Audit.

    Args:
        label_score: Completeness-based score (0–100).
        label_quality: Output of ``_label_quality_score``.
        required_fields: Fields that must be present for completeness.

    Returns:
        List of markdown lines for Section 3.
    """
    lines = [
        "## Section 3: Label Quality Audit",
        "",
        f"**Score**: {label_score:.1f}/100",
        f"**Total samples**: {label_quality['total_samples']:,}",
        f"**Label completeness**: {label_quality['completeness']:.1f}%",
        "",
        "**Required fields**: "
        + (
            ", ".join(f"`{f}`" for f in required_fields)
            if required_fields
            else "*(not defined)*"
        ),
        "",
    ]
    tier_dist: dict[str, int] = label_quality.get("tier_distribution", {})
    if tier_dist:
        lines += [
            "| Tier | Count | % |",
            "| --- | --- | --- |",
        ]
        total_tier = sum(tier_dist.values())
        for tier, count in sorted(tier_dist.items()):
            pct = count / total_tier * 100 if total_tier else 0
            lines.append(f"| {tier} | {count:,} | {pct:.1f}% |")
    else:
        lines.append("*No tier information available in loaded samples.*")
    return lines


def _render_section_4(
    ood_registry_path: Path,
    has_leakage: bool,
    leakage_count: int,
    ood_hash_count: int,
) -> list[str]:
    """Render Section 4: OOD Leakage Check.

    Args:
        ood_registry_path: Path used for the registry (shown in report).
        has_leakage: True if OOD images were detected.
        leakage_count: Number of OOD images found.
        ood_hash_count: Total hashes in the registry.

    Returns:
        List of markdown lines for Section 4.
    """
    lines = ["## Section 4: OOD Leakage Check", ""]
    if ood_hash_count == 0:
        lines += [
            "**Result**: ⚠️ Registry empty — check skipped",
            "",
            f"The OOD registry at `{ood_registry_path}` is empty. "
            "Populate it with OOD image SHA256 hashes before running leakage checks.",
        ]
    elif has_leakage:
        lines += [
            f"**Result**: ❌ FAIL — {leakage_count} OOD images found in dataset",
            "",
            "OOD-registered images were found in this dataset. Remove them before training.",
        ]
    else:
        lines.append(
            f"**Result**: ✅ PASS — 0 OOD images found ({ood_hash_count} OOD hashes checked)"
        )
    return lines


def _render_section_5(
    statistical_score: float,
    stat_results: list[dict[str, Any]],
) -> list[str]:
    """Render Section 5: Statistical Diversity Tests.

    Args:
        statistical_score: Fraction of passing tests × 100.
        stat_results: List of per-dimension test result dicts.

    Returns:
        List of markdown lines for Section 5.
    """
    lines = [
        "## Section 5: Statistical Diversity Tests",
        "",
        f"**Score**: {statistical_score:.1f}/100",
        "",
        "Chi-square uniformity tests (target: p > 0.01, i.e. chi_sq < critical value):",
        "",
        "| Dimension | Chi-Square | Categories | Result |",
        "| --- | --- | --- | --- |",
    ]
    for result in stat_results:
        flag = "✅ PASS" if result["passes"] else "❌ FAIL"
        lines.append(
            f"| {result['dimension']} | {result['chi_sq']:.2f} | "
            f"{result['n_categories']} | {flag} |"
        )
    if not stat_results:
        lines.append(
            "| *No dimension data available for statistical tests* | — | — | ⚠️ |"
        )
    return lines


def _render_section_6(
    overall_score: float,
    wild_score: float,
    diversity_score: float,
    label_score: float,
    statistical_score: float,
    overall_grade: str,
) -> list[str]:
    """Render Section 6: Overall Diversity Score table.

    Args:
        overall_score: Weighted overall score (0–100).
        wild_score: Wild condition sub-score.
        diversity_score: Dimension diversity sub-score.
        label_score: Label quality sub-score.
        statistical_score: Statistical tests sub-score.
        overall_grade: Human-readable grade string.

    Returns:
        List of markdown lines for Section 6.
    """
    return [
        "## Section 6: Overall Diversity Score",
        "",
        "| Component | Weight | Score | Weighted |",
        "| --- | --- | --- | --- |",
        f"| Wild condition coverage | 30% | {wild_score:.1f} | {wild_score * 0.30:.1f} |",
        f"| 14-dimension diversity | 30% | {diversity_score:.1f} | {diversity_score * 0.30:.1f} |",
        f"| Label quality | 20% | {label_score:.1f} | {label_score * 0.20:.1f} |",
        f"| Statistical tests | 20% | {statistical_score:.1f} | {statistical_score * 0.20:.1f} |",
        f"| **Overall** | 100% | **{overall_score:.1f}** | |",
        "",
        f"**Grade**: {overall_grade}",
    ]


def _render_section_7(dataset_name: str, heads: list[str]) -> list[str]:
    """Render Section 7: Multi-Model Consensus Review placeholder.

    Args:
        dataset_name: Dataset identifier for the prompt template.
        heads: Model heads this dataset serves.

    Returns:
        List of markdown lines for Section 7.
    """
    heads_str = ", ".join(heads)
    return [
        "## Section 7: Multi-Model Consensus Review",
        "",
        "*Pending — run 5-model consensus review after automated scoring:*",
        "",
        "```bash",
        "# Run consensus review (models: gemini-2.5-pro, gemini-3-pro-preview,",
        "#   gpt-5.2, deepseek-r1-0528, grok-4)",
        f"# Prompt: Review DDR for {dataset_name} serving {heads_str}.",
        "# Output: Append to this file as Section 7.",
        "```",
        "",
        "**Consensus review not yet run.**",
    ]


# ──────────────────────────────────────────────────────────────────────────────
# DDR Orchestration
# ──────────────────────────────────────────────────────────────────────────────


def _compute_dim_distributions(
    samples: list[dict[str, Any]],
) -> dict[str, Counter[str]]:
    """Extract per-dimension value distributions from loaded samples.

    Only includes dimensions where at least one non-null value exists.

    Args:
        samples: List of manifest sample dicts.

    Returns:
        Mapping of dimension name → Counter of observed values.
    """
    dim_distributions: dict[str, Counter[str]] = {}
    for dim in DIVERSITY_DIMENSIONS:
        values = [str(s[dim]) for s in samples if s.get(dim) is not None]
        if values:
            dim_distributions[dim] = Counter(values)
    return dim_distributions


def _compute_diversity_score(
    dim_distributions: dict[str, Counter[str]],
) -> float:
    """Average per-dimension score across all 14 dimensions.

    Scoring per dimension:
    - 100 if ≥2 unique values and min category share ≥5 %
    - 50  if ≥2 unique values but min category share <5 %
    - 0   if only 1 unique value or dimension not measured

    Args:
        dim_distributions: Output of ``_compute_dim_distributions``.

    Returns:
        Mean score across all dimensions (0–100).
    """
    scores: list[float] = []
    for dim in DIVERSITY_DIMENSIONS:
        dist = dim_distributions.get(dim, Counter())
        if not dist:
            scores.append(0.0)
            continue
        total_in_dim = sum(dist.values())
        n_unique = len(dist)
        min_pct = min(v / total_in_dim * 100 for v in dist.values())
        if n_unique > 1 and min_pct >= 5:
            scores.append(100.0)
        elif n_unique > 1:
            scores.append(50.0)
        else:
            scores.append(0.0)
    return sum(scores) / len(scores) if scores else 0.0


def _run_statistical_tests(
    dim_distributions: dict[str, Counter[str]],
) -> tuple[float, list[dict[str, Any]]]:
    """Run chi-square uniformity tests on key categorical dimensions.

    Tested dimensions: script, orientation, source, color_mode, document_age.

    Args:
        dim_distributions: Output of ``_compute_dim_distributions``.

    Returns:
        Tuple of ``(statistical_score, stat_results)`` where
        ``statistical_score`` is the fraction of passing tests × 100.
    """
    tested_dims = ["script", "orientation", "source", "color_mode", "document_age"]
    stat_results: list[dict[str, Any]] = []
    pass_count = 0

    for dim in tested_dims:
        dist = dim_distributions.get(dim, Counter())
        if not dist:
            continue
        chi_sq, passes = _chi_square_test(dist)
        stat_results.append(
            {
                "dimension": dim,
                "chi_sq": round(chi_sq, 2),
                "passes": passes,
                "n_categories": len(dist),
            }
        )
        if passes:
            pass_count += 1

    statistical_score = (
        pass_count / max(len(stat_results), 1) * 100 if stat_results else 50.0
    )
    return statistical_score, stat_results


def _build_report_header(
    dataset_name: str,
    registry_info: dict[str, Any],
    sample_count: int,
) -> list[str]:
    """Build the report title block and metadata section.

    Args:
        dataset_name: Dataset identifier.
        registry_info: Entry from ``DATASET_REGISTRY``.
        sample_count: Number of samples successfully loaded.

    Returns:
        List of markdown lines for the header block.
    """
    heads = ", ".join(registry_info.get("heads", ["Unknown"]))
    image_count = registry_info.get("images", "Unknown")
    image_str = f"{image_count:,}" if isinstance(image_count, int) else str(image_count)
    notes = registry_info.get("notes", "")

    return [
        f"# Dataset Diversity Report: {dataset_name}",
        "",
        f"> **Generated**: {date.today().isoformat()}",
        f"> **Dataset**: {dataset_name}",
        f"> **Primary Heads**: {heads}",
        f"> **Image Count**: {image_str}",
        f"> **Samples Loaded**: {sample_count:,}",
        f"> **Notes**: {notes}",
        "",
        "---",
    ]


def _generate_ddr(
    dataset_name: str,
    output_dir: Path,
    ood_registry_path: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Generate a Dataset Diversity Report for a single dataset.

    Orchestrates all seven report sections, writes the markdown file,
    and returns a summary dict for multi-dataset aggregation.

    Args:
        dataset_name: Key in ``DATASET_REGISTRY``.
        output_dir: Directory to write the DDR markdown file.
        ood_registry_path: Path to ``metadata_registry/ood_registry.jsonl``.
        dry_run: When ``True``, print report to stdout instead of writing.

    Returns:
        Dict with ``overall_score``, per-section scores, ``leakage_passed``,
        ``samples_loaded``, and ``grade``.

    Raises:
        ValueError: When ``dataset_name`` is not in ``DATASET_REGISTRY``.
    """
    if dataset_name not in DATASET_REGISTRY:
        raise ValueError(
            f"Unknown dataset: {dataset_name!r}. "
            f"Available: {list(DATASET_REGISTRY.keys())}"
        )

    registry_info = DATASET_REGISTRY[dataset_name]
    samples = _load_dataset_samples(dataset_name)

    click.echo(f"Generating DDR for {dataset_name} ({len(samples)} samples loaded)...")

    # Section 1: Wild condition coverage
    wild_score, wild_conditions = _compute_wild_condition_score(dataset_name)
    covered_count = sum(1 for c in wild_conditions if c["status"] == "✅ Covered")
    partial_count = sum(1 for c in wild_conditions if c["status"] == "⚠️ Partial")
    missing_count = sum(1 for c in wild_conditions if c["status"] == "❌ Missing")

    # Section 2: 14-dimension diversity
    dim_distributions = _compute_dim_distributions(samples)
    diversity_score = _compute_diversity_score(dim_distributions)

    # Section 3: Label quality
    required_fields = _get_required_fields(dataset_name)
    label_quality = _label_quality_score(samples, required_fields)
    # Use 50.0 when no samples to inspect (neutral — cannot confirm or deny)
    label_score = label_quality["completeness"] if samples else 50.0

    # Section 4: OOD leakage
    image_paths = [Path(s["image_path"]) for s in samples if s.get("image_path")]
    ood_hashes = _load_ood_registry(ood_registry_path)
    has_leakage, leakage_count = _check_ood_leakage_for_ddr(
        image_paths[:1000], ood_registry_path
    )
    leakage_passed = not has_leakage

    # Section 5: Statistical tests
    statistical_score, stat_results = _run_statistical_tests(dim_distributions)

    # Section 6: Overall score
    overall_score = _compute_overall_score(
        wild_score, diversity_score, label_score, statistical_score, leakage_passed
    )
    if overall_score >= 90:
        overall_grade = "✅ Excellent — cleared for training"
    elif overall_score >= 70:
        overall_grade = "✅ Good — cleared for training"
    else:
        overall_grade = "⚠️ Insufficient — remediation required before training"

    # Assemble full report
    sep = ["", "---", ""]
    heads: list[str] = registry_info.get("heads", [])

    sections: list[list[str]] = [
        _build_report_header(dataset_name, registry_info, len(samples)),
        sep,
        _render_section_1(
            wild_score, wild_conditions, covered_count, partial_count, missing_count
        ),
        sep,
        _render_section_2(diversity_score, dim_distributions, len(samples)),
        sep,
        _render_section_3(label_score, label_quality, required_fields),
        sep,
        _render_section_4(
            ood_registry_path, has_leakage, leakage_count, len(ood_hashes)
        ),
        sep,
        _render_section_5(statistical_score, stat_results),
        sep,
        _render_section_6(
            overall_score,
            wild_score,
            diversity_score,
            label_score,
            statistical_score,
            overall_grade,
        ),
        sep,
        _render_section_7(dataset_name, heads),
        ["", "---", "", "*Generated by `scripts/evaluate_dataset_diversity.py`*"],
    ]

    report = "\n".join(line for section in sections for line in section)

    if dry_run:
        click.echo(report)
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{dataset_name.replace('-', '_')}_ddr.md"
        output_file.write_text(report)
        click.echo(f"DDR written to: {output_file}")

    return {
        "dataset": dataset_name,
        "overall_score": overall_score,
        "wild_score": wild_score,
        "diversity_score": diversity_score,
        "label_score": label_score,
        "statistical_score": statistical_score,
        "leakage_passed": leakage_passed,
        "samples_loaded": len(samples),
        "grade": overall_grade,
    }


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────


@click.command()
@click.option(
    "--dataset",
    "dataset_name",
    default=None,
    help="Dataset name to evaluate. See --list-datasets for available names.",
)
@click.option(
    "--all-datasets",
    is_flag=True,
    default=False,
    help="Evaluate all 10 training datasets in sequence.",
)
@click.option(
    "--output",
    "output_dir",
    type=click.Path(path_type=Path),
    default=Path("docs/datasets/diversity_reports"),
    show_default=True,
    help="Output directory for DDR markdown files.",
)
@click.option(
    "--ood-registry",
    type=click.Path(path_type=Path),
    default=Path("metadata_registry/ood_registry.jsonl"),
    show_default=True,
    help="Path to OOD registry JSONL file.",
)
@click.option(
    "--ood-check-only",
    is_flag=True,
    default=False,
    help="Run OOD leakage check only (no full DDR).",
)
@click.option(
    "--list-datasets",
    is_flag=True,
    default=False,
    help="List all available dataset names and exit.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print report to stdout instead of writing file.",
)
def main(
    dataset_name: str | None,
    all_datasets: bool,
    output_dir: Path,
    ood_registry: Path,
    ood_check_only: bool,
    list_datasets: bool,
    dry_run: bool,
) -> None:
    """Generate Dataset Diversity Reports (DDRs) for training datasets.

    Each report covers 7 sections: wild condition coverage, 14-dimension
    diversity, label quality, OOD leakage check, statistical tests,
    overall score, and multi-model consensus summary.
    """
    if list_datasets:
        click.echo("Available datasets:")
        for name, info in DATASET_REGISTRY.items():
            heads = ", ".join(info.get("heads", []))
            click.echo(f"  {name:<30} {info.get('images', 0):>8,} images  [{heads}]")
        return

    if ood_check_only:
        ood_hashes = _load_ood_registry(ood_registry)
        click.echo(f"OOD registry: {ood_registry}")
        click.echo(f"OOD hashes loaded: {len(ood_hashes)}")
        if ood_hashes:
            click.echo("Registry loaded and accessible.")
        else:
            click.echo(
                "Registry is empty — populate with OOD SHA256 hashes to enable enforcement."
            )
        return

    datasets_to_run: list[str] = []

    if all_datasets:
        datasets_to_run = list(DATASET_REGISTRY.keys())
    elif dataset_name:
        datasets_to_run = [dataset_name]
    else:
        click.echo(
            "Specify --dataset NAME, --all-datasets, or --list-datasets.", err=True
        )
        raise SystemExit(1)

    results: list[dict[str, Any]] = []
    for ds in datasets_to_run:
        try:
            result = _generate_ddr(ds, output_dir, ood_registry, dry_run=dry_run)
            results.append(result)
        except ValueError as exc:
            click.echo(f"Error: {exc}", err=True)

    if len(results) > 1:
        click.echo("\n" + "=" * 70)
        click.echo("DIVERSITY EVALUATION SUMMARY")
        click.echo("=" * 70)
        click.echo(f"{'Dataset':<30} {'Score':>6} {'Grade'}")
        click.echo("-" * 70)
        for r in results:
            score_str = f"{r['overall_score']:.1f}"
            grade_short = "Cleared" if r["overall_score"] >= 70 else "Remediate"
            click.echo(f"{r['dataset']:<30} {score_str:>6}  {grade_short}")


if __name__ == "__main__":
    main()
