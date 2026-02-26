#!/usr/bin/env python3
"""Shared utilities for OOD dataset acquisition and registry management.

Provides SHA256/pHash deduplication, registry I/O, ground-truth templating,
and directory scaffolding used by all ``build_ood_dataset.py`` sub-commands.

Pattern reference: ``scripts/prepare_multitask_datasets.py`` (SHA256/OOD helpers).

Requires (``[project.optional-dependencies] ood`` group in pyproject.toml):
    imagehash>=4.3.1        # pHash computation
    Pillow>=10.0.0          # already in base; needed by imagehash
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OOD directory layout
# ---------------------------------------------------------------------------

OOD_SUBDIRECTORIES: tuple[str, ...] = (
    "ood_script",
    "ood_geometry",
    "ood_capture",
    "ood_degradation",
    "ood_handwriting",
    "ood_resolution",
    "ood_domain",
    "ood_code",
    "ood_mixed",
)

# ---------------------------------------------------------------------------
# Required registry entry fields (top-level, excluding ground_truth)
# ---------------------------------------------------------------------------

_REQUIRED_ENTRY_FIELDS: frozenset[str] = frozenset(
    {
        "sha256",
        "phash",
        "source_path",
        "ood_categories",
        "reason",
        "registered_date",
        "acquisition_method",
        "license",
        "dedup_verified",
        "evaluation_pipeline_stage",
        "ground_truth",
    }
)

# All 22 model-head fields that must be present in ground_truth (nullable OK).
# Matches the Per-Image Entry Template in docs/datasets/OOD_DATASET_CATALOG.md.
_GROUND_TRUTH_FIELDS: tuple[str, ...] = (
    "blur_score",
    "noise_score",
    "contrast_score",
    "compression_score",
    "skew_score",
    "overall_quality",
    "script",
    "open_set",
    "orientation",
    "skew_angle_degrees",
    "handwriting_presence",
    "handwriting_presence_score",
    "handwriting_legibility",
    "handwriting_legibility_score",
    "handwriting_content_type",
    "capture_method",
    "shadow_severity",
    "shadow_type",
    "warping_severity",
    "warping_type",
    "watermark_severity",
    "code_confidence",
    "resolution_quality",
    "color_mode",
    "document_age",
    "text_direction",
)


# ---------------------------------------------------------------------------
# SHA256 helpers
# ---------------------------------------------------------------------------


def compute_sha256(image_path: Path) -> str:
    """Compute SHA256 of raw image file bytes.

    Mirrors ``_compute_sha256()`` in ``scripts/prepare_multitask_datasets.py``
    to ensure hash values are directly comparable with training manifest hashes.

    Args:
        image_path: Path to the image file on disk.

    Returns:
        Hex-encoded SHA256 digest string (64 characters).

    Raises:
        FileNotFoundError: If *image_path* does not exist.
    """
    hasher = hashlib.sha256()
    with image_path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65_536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


# ---------------------------------------------------------------------------
# pHash helpers
# ---------------------------------------------------------------------------


def compute_phash(image_path: Path) -> str:
    """Compute 64-bit perceptual hash of an image.

    Uses ``imagehash.phash`` (DCT-based) which is robust to minor re-encoding,
    slight crops, and JPEG quality changes — critical for detecting near-duplicate
    OOD images that have been lightly post-processed.

    The hash is stored as a 64-character hex string (4 bits per hex char × 16 chars
    → 64 bits = 8 bytes). This is compact and directly comparable via
    ``hamming_distance()``.

    Args:
        image_path: Path to the image file.

    Returns:
        64-character hex string representing the pHash bit array.

    Raises:
        ImportError: If ``imagehash`` is not installed.
        FileNotFoundError: If *image_path* does not exist.
    """
    try:
        import imagehash
        from PIL import Image
    except ImportError as exc:
        raise ImportError(
            "imagehash is required for pHash computation. "
            "Install with: uv add imagehash --optional ood"
        ) from exc

    # PIL refuses to open images larger than ~89M pixels by default.
    # Temporarily raise the limit — imagehash already thumbnails internally.
    _old_limit = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = None  # Disable decompression bomb check for pHash.
    try:
        with Image.open(image_path) as img:
            # Down-sample very large images before pHash to avoid OOM.
            if img.width * img.height > 25_000_000:
                img = img.resize(
                    (img.width // 4, img.height // 4), Image.Resampling.LANCZOS
                )
            ph = imagehash.phash(img)
    finally:
        Image.MAX_IMAGE_PIXELS = _old_limit
    # ph.hash is a bool numpy array of shape (8, 8) = 64 bits.
    # Flatten to 1-D, pack bits into bytes, encode as hex.
    bits = ph.hash.flatten()
    byte_values = [
        int("".join(str(int(b)) for b in bits[i : i + 8]), 2)
        for i in range(0, 64, 8)
    ]
    return bytes(byte_values).hex()


def hamming_distance(h1: str, h2: str) -> int:
    """Count differing bits between two pHash hex strings.

    Args:
        h1: 16-character hex string (64-bit pHash) from ``compute_phash()``.
        h2: 16-character hex string (64-bit pHash) from ``compute_phash()``.

    Returns:
        Number of bit positions that differ (0 = identical, 64 = opposite).
    """
    b1 = int(h1, 16)
    b2 = int(h2, 16)
    xor = b1 ^ b2
    return bin(xor).count("1")


# ---------------------------------------------------------------------------
# Training manifest hash loader
# ---------------------------------------------------------------------------


def load_training_hashes(manifest_paths: list[Path]) -> set[str]:
    """Load SHA256 hashes of all images referenced across training manifests.

    Each manifest is a flat JSON list of dicts with an ``image_path`` key.
    The image file itself is hashed (not the path string), so the hash remains
    stable regardless of mount point or path prefix.

    Images that do not exist on disk are skipped with a logged warning —
    this handles the case where training manifests reference GCS paths not
    locally mirrored.

    Args:
        manifest_paths: Paths to ``train_manifest.json``, ``val_manifest.json``,
            etc. produced by ``prepare_multitask_datasets.py``.

    Returns:
        Set of SHA256 hex strings for every training image found on disk.
    """
    sha256_set: set[str] = set()
    for manifest_path in manifest_paths:
        if not manifest_path.exists():
            logger.warning("Training manifest not found, skipping: %s", manifest_path)
            continue
        with manifest_path.open() as fh:
            try:
                samples = json.load(fh)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in manifest: %s", manifest_path)
                continue
        if not isinstance(samples, list):
            logger.warning(
                "Manifest is not a flat list (got %s): %s",
                type(samples).__name__,
                manifest_path,
            )
            continue
        for sample in samples:
            img_path_str = sample.get("image_path", "")
            if not img_path_str:
                continue
            img_path = Path(img_path_str)
            if not img_path.is_absolute():
                # Manifest paths are relative to /data/ on Modal Volume.
                # Skip if not resolvable locally.
                continue
            if not img_path.exists():
                continue
            sha256_set.add(compute_sha256(img_path))
    return sha256_set


# ---------------------------------------------------------------------------
# OOD registry loader
# ---------------------------------------------------------------------------


def load_ood_registry(registry_path: Path) -> tuple[set[str], list[str]]:
    """Load SHA256 and pHash values from an existing OOD registry JSONL file.

    Used to prevent intra-registry duplicates when registering new entries.
    If the registry is missing or empty, returns empty collections — callers
    must handle this gracefully (first-run case).

    Args:
        registry_path: Path to ``metadata_registry/ood_registry.jsonl``.

    Returns:
        Tuple of (sha256_set, phash_list) where sha256_set contains all
        registered SHA256 hashes and phash_list contains all pHash hex strings
        for Hamming-distance comparison.
    """
    sha256_set: set[str] = set()
    phash_list: list[str] = []

    if not registry_path.exists() or registry_path.stat().st_size == 0:
        return sha256_set, phash_list

    with registry_path.open() as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("Skipping malformed JSON at line %d: %s", line_no, registry_path)
                continue
            if sha256 := entry.get("sha256"):
                sha256_set.add(sha256)
            if phash := entry.get("phash"):
                phash_list.append(phash)

    return sha256_set, phash_list


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------


def is_duplicate(
    sha256: str,
    phash: str,
    known_sha256s: set[str],
    known_phashes: list[str],
    hamming_threshold: int = 5,
) -> bool:
    """Return True if an image is a duplicate of any known image.

    A duplicate is defined as:
    - SHA256 exact match (byte-identical file), OR
    - pHash Hamming distance ≤ *hamming_threshold* to any known pHash
      (visually near-identical image)

    The Hamming threshold of 5 (out of 64 bits) is conservative — images
    that differ only in minor JPEG re-encoding, slight brightness adjustment,
    or 1-2 pixel crops will be caught, while genuinely different images
    from the same document collection will not be blocked.

    Args:
        sha256: SHA256 hex string of the candidate image.
        phash: pHash hex string of the candidate image.
        known_sha256s: Set of SHA256 hashes to check against.
        known_phashes: List of pHash strings to compare via Hamming distance.
        hamming_threshold: Maximum Hamming distance to consider near-duplicate.

    Returns:
        True if the image is a duplicate; False if it is unique.
    """
    if sha256 in known_sha256s:
        return True
    for known_phash in known_phashes:
        if hamming_distance(phash, known_phash) <= hamming_threshold:
            return True
    return False


# ---------------------------------------------------------------------------
# Ground truth template
# ---------------------------------------------------------------------------


def build_ground_truth_template() -> dict[str, Any]:
    """Return a ground_truth dict with all 26 head fields initialised to null.

    Callers should fill in fields that are known at registration time and
    leave genuinely unknown fields as ``None`` (serialised as JSON ``null``).
    Fields that require human review must be flagged via
    ``needs_human_review=True`` at the entry level.

    Returns:
        Dict mapping each ground truth field name to ``None``.
    """
    return {field: None for field in _GROUND_TRUTH_FIELDS}


# ---------------------------------------------------------------------------
# Registry entry validator and writer
# ---------------------------------------------------------------------------


def append_registry_entry(entry: dict[str, Any], registry_path: Path) -> None:
    """Validate a registry entry and append it as a JSON line.

    Performs lightweight validation:
    - All required top-level fields must be present.
    - ``ground_truth`` must be a dict containing all expected head fields.
    - The entry is appended atomically as a single JSON line (no trailing comma).

    Unlike the training-side ``_check_ood_leakage()`` (which exits on failure),
    this function raises ``ValueError`` on validation failure — the caller
    decides whether to skip or abort.

    Args:
        entry: Registry entry dict to append.
        registry_path: Path to ``metadata_registry/ood_registry.jsonl``.

    Raises:
        ValueError: If required fields are missing or ground_truth is incomplete.
    """
    missing_top = _REQUIRED_ENTRY_FIELDS - entry.keys()
    if missing_top:
        raise ValueError(
            f"Registry entry missing required fields: {sorted(missing_top)}\n"
            f"  source_path={entry.get('source_path', '<unknown>')}"
        )

    gt = entry.get("ground_truth")
    if not isinstance(gt, dict):
        raise ValueError(
            f"ground_truth must be a dict, got {type(gt).__name__}: "
            f"source_path={entry.get('source_path', '<unknown>')}"
        )
    missing_gt = set(_GROUND_TRUTH_FIELDS) - gt.keys()
    if missing_gt:
        raise ValueError(
            f"ground_truth missing fields: {sorted(missing_gt)}\n"
            f"  source_path={entry.get('source_path', '<unknown>')}"
        )

    # Add registration timestamp if caller did not set it.
    if not entry.get("registered_date"):
        entry["registered_date"] = date.today().isoformat()

    with registry_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Registry dry-run summary helper
# ---------------------------------------------------------------------------


def log_dry_run_summary(
    *,
    candidates: int,
    duplicates_training: int,
    duplicates_intra: int,
    unique: int,
    sub_command: str,
    dry_run: bool = True,
) -> None:
    """Print an acquisition summary table to stdout.

    Args:
        candidates: Total images evaluated.
        duplicates_training: Images blocked as training leakage.
        duplicates_intra: Images blocked as intra-registry duplicates.
        unique: Images registered (or that would be registered in dry-run).
        sub_command: Name of the sub-command being previewed.
        dry_run: When True, headers say "Would be registered"; when False,
            headers say "Registered".
    """
    import click

    if dry_run:
        header = f"  DRY-RUN SUMMARY  [{sub_command}]"
        reg_label = "  Would be registered   :"
    else:
        header = f"  ACQUISITION SUMMARY  [{sub_command}]"
        reg_label = "  Registered            :"

    click.echo(
        f"\n{'─' * 60}\n"
        f"{header}\n"
        f"{'─' * 60}\n"
        f"  Candidates evaluated  : {candidates:>6}\n"
        f"  Blocked (train leak)  : {duplicates_training:>6}\n"
        f"  Blocked (intra-dup)   : {duplicates_intra:>6}\n"
        f"{reg_label} {unique:>6}\n"
        f"{'─' * 60}"
    )


# ---------------------------------------------------------------------------
# Directory scaffold
# ---------------------------------------------------------------------------


def create_ood_directory_structure(ood_root: Path) -> None:
    """Create the 9-category OOD image storage directories.

    Safe to call on an existing tree — ``exist_ok=True`` is used throughout.
    Directories are created under *ood_root* as defined in
    ``docs/datasets/OOD_DATASET_CATALOG.md §Notes``.

    Args:
        ood_root: Root directory, typically ``/mnt/e/image_detection/ood/``.
    """
    ood_root.mkdir(parents=True, exist_ok=True)
    for subdir in OOD_SUBDIRECTORIES:
        (ood_root / subdir).mkdir(exist_ok=True)
    logger.info("OOD directory structure created at %s", ood_root)


# ---------------------------------------------------------------------------
# Convenience: compute both hashes in one call
# ---------------------------------------------------------------------------


def compute_hashes(image_path: Path) -> tuple[str, str]:
    """Compute (sha256, phash) for an image in a single call.

    Args:
        image_path: Path to the image file.

    Returns:
        Tuple of (sha256_hex, phash_hex).
    """
    return compute_sha256(image_path), compute_phash(image_path)


# ---------------------------------------------------------------------------
# Module self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ood_utils.py <image_path>")
        sys.exit(1)

    test_path = Path(sys.argv[1])
    if not test_path.exists():
        print(f"File not found: {test_path}")
        sys.exit(1)

    sha256, phash = compute_hashes(test_path)
    print(f"SHA256 : {sha256}")
    print(f"pHash  : {phash}")
    print(f"GT tmpl: {list(build_ground_truth_template().keys())}")
