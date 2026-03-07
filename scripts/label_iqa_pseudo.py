"""MUSIQ + TOPIQ-NR ensemble pseudo-labeling for corpus-wide IQA quality scores.

Generates IQA pseudo-labels by running pretrained blind NR-IQA models (MUSIQ,
TOPIQ-NR) via the ``pyiqa`` library on every image in the training corpus.
Results are written back into L2 metadata files as an ``iqa_pseudo_labels``
dict in ``enrichments.versions[-1].data``.

This is the **highest-leverage** unblocking task for SigLIP 2 multi-task
training: without IQA pseudo-labels, none of the G1 IQA heads can train.

Models
------
- **MUSIQ** (Multi-Scale Image Quality Transformer): Trained on KonIQ-10k,
  outputs ~[0, 100] MOS-like scores.  Normalized to [0, 1] by dividing by 100.
- **TOPIQ-NR** (No-Reference): Trained on KonIQ-10k, outputs [0, 1] natively.

Output schema (per sample, into ``enrichments.versions[-1].data``)::

    {
        "iqa_pseudo_labels": {
            "musiq_mos": 0.72,
            "topiq_mos": 0.68,
            "ensemble_mos": 0.70,
            "model_agreement": 0.96,
            "label_tier": "tier_2_model"
        }
    }

Training contract
-----------------
``modal/train_siglip2_multitask.py:1193-1199`` reads IQA as MOS [1,5] and
normalizes to [0,1] via ``_normalize_mos()``.  The ``ensemble_mos`` maps to
the ``overall`` dimension.  Downstream ``prepare_multitask_datasets.py`` will
read ``iqa_pseudo_labels.ensemble_mos`` from L2 and emit it in the training
manifest.

Modes
-----
- **Full run** (default): Process all datasets, write L2 metadata.
- ``--validate-only``: SRCC gate on DIQA-5000 held-out; no L2 writes.
- ``--dry-run``: Count eligible samples, estimate timing; no inference.
- ``--spot-check N``: Infer N random samples per dataset, print distributions.

Usage
-----
::

    # Step 1: Validate SRCC gate (REQUIRED first)
    uv run python scripts/label_iqa_pseudo.py --validate-only --device cuda

    # Step 2: Dry-run to estimate timing
    uv run python scripts/label_iqa_pseudo.py --dry-run

    # Step 3: Spot-check 20 images from representative datasets
    uv run python scripts/label_iqa_pseudo.py \\
        --datasets doclaynet ohr-bench tobacco800 \\
        --spot-check 20 --device cuda

    # Step 4: Full corpus run (GPU recommended)
    uv run python scripts/label_iqa_pseudo.py --device cuda --batch-size 500

Dependencies
------------
Install: ``uv sync --extra iqa``
"""

from __future__ import annotations

import json
import logging
import random
import shutil
import statistics
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click
import cv2
import numpy as np
from tqdm import tqdm

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_MODELS: frozenset[str] = frozenset(("musiq", "topiq_nr"))

# Raw score ranges for normalization to [0, 1].
# MUSIQ (KonIQ-10k variant): outputs ~[0, 100] MOS scale.
# TOPIQ-NR: outputs [0, 1] natively.
SCORE_RANGES: dict[str, tuple[float, float]] = {
    "musiq": (0.0, 100.0),
    "topiq_nr": (0.0, 1.0),
}

# Per-image latency estimates (ms) from benchmark_iqa_models.py
_GPU_LATENCY_MS: dict[str, float] = {"musiq": 24.0, "topiq_nr": 18.0}
_CPU_LATENCY_MS: dict[str, float] = {"musiq": 145.0, "topiq_nr": 123.0}

# DIQA-5000 defaults for validation mode
_DIQA_METADATA_FILENAME = "diqa-5000_metadata.json"
_DIQA_DATASET_SUFFIX = "02_benchmark_only/diqa-5000"

# Default SRCC threshold for validation gate
_DEFAULT_SRCC_THRESHOLD = 0.55

# Dataset name -> path_suffix mapping (extracted from DATASET_CONFIGS in
# src/image_preprocessing_detector/annotation/config/datasets.py).
# Hardcoded here to keep scripts standalone (no src/ import required).
_DATASET_PATH_SUFFIXES: dict[str, str] = {
    # Benchmark (4)
    "diqa-5000": "02_benchmark_only/diqa-5000",
    "smartdoc-qa": "02_benchmark_only/smartdoc-qa",
    "dibco": "02_benchmark_only/dibco",
    "omnidocbench": "02_benchmark_only/omnidocbench",
    # Degraded (2)
    "tobacco800": "01_base_data/degraded/tobacco800",
    "historical_degraded": "01_base_data/degraded/historical_degraded",
    # Documents (2)
    "rvl_cdip": "01_base_data/documents/rvl_cdip",
    "doclaynet": "01_base_data/documents/doclaynet",
    # Forms (5)
    "nist-sd2": "01_base_data/forms/nist-sd2",
    "nist_sd6": "01_base_data/forms/nist_sd6",
    "funsd": "01_base_data/forms/funsd",
    "funsd_plus": "01_base_data/forms/funsd_plus",
    "sroie": "01_base_data/forms/sroie_icdar2019",
    # Tables (3)
    "tablebank": "01_base_data/tables/tablebank",
    "pubtabnet": "01_base_data/tables/pubtabnet",
    "fintabnet": "01_base_data/tables/fintabnet",
    # Handwriting (12)
    "nist_sd19": "01_base_data/handwriting/nist-sd19",
    "signatr6k": "01_base_data/handwriting/signatr6k",
    "maths_handwriting": "01_base_data/handwriting/maths_handwriting",
    "muharaf": "01_base_data/handwriting/muharaf/public",
    "iam": "01_base_data/handwriting/iam_handwriting",
    "hasyv2": "01_base_data/handwriting/hasy/hasy-data",
    "egyptian-handwriting": "01_base_data/handwriting/egyptian-handwriting",
    "salami": "01_base_data/handwriting/salami",
    "gnhk": "01_base_data/handwriting/gnhk",
    "signverod": "01_base_data/handwriting/signverod",
    "popp-line": "01_base_data/forms/popp-datasets",
    "ndl-minhon": "01_base_data/handwriting/ndl-minhon/images",
    # Formulas (2)
    "im2latex": "01_base_data/formulas/im2latex",
    "mathverse": "01_base_data/formulas/mathverse",
    # Educational (1)
    "multimodal_textbook": "01_base_data/educational/multimodal_textbook",
    # Camera-captured (1)
    "realdae": "01_base_data/camera_captured/realdae",
    # OCR Quality (1)
    "ocr_quality": "01_base_data/ocr_quality",
    # Multilingual / Script (14)
    "pucit_ohul": "01_base_data/language/pucit-ohul",
    "multilingual_scripts": "01_base_data/language/multilingual_scripts",
    "midv500": "01_base_data/language/midv500_data/midv500",
    "midv2020": "01_base_data/documents/midv2020/extracted",
    "bhutan_financial": "01_base_data/documents/bhutan_financial",
    "mdiw13": "01_base_data/language/mdiw13",
    "cc_ocr": "01_base_data/language/huggingface_downloads/CC-OCR/extracted_images",
    "cocotext": "01_base_data/text_detection/cocotext/images",
    "tibhcr": "01_base_data/language/huggingface_downloads/TibHCR/TibHCR",
    "mlt19": "01_base_data/language/mlt19",
    "arabic_docs_ocr": "01_base_data/language/arabic_docs_ocr",
    "hindi_ocr_synthetic": "01_base_data/language/hindi_ocr_synthetic",
    "nepali_handwritten": "01_base_data/language/nepali_handwritten",
    "yarmouk_ocr": "01_base_data/language/yarmouk",
    # Script Identification (3)
    "cvsi": "01_base_data/language/cvsi",
    "siw13": "01_base_data/language/siw13",
    "mle2e": "01_base_data/language/mle2e",
    # OHR-Bench (1)
    "ohr-bench": "02_benchmark_only/ohr-bench",
    # FinanceBench (1)
    "financebench": "02_benchmark_only/financebench",
    # Correction / Shadow / Dewarping (7)
    "anyphotodoc6300": "01_base_data/correction/anyphotodoc6300",
    "docalign12k": "01_base_data/correction/docalign12k",
    "wsrd": "01_base_data/correction/wsrd",
    "warpdoc": "01_base_data/correction/warpdoc",
    "docreal": "01_base_data/correction/docreal",
    "sd7k": "01_base_data/correction/sd7k",
    "staindoc": "01_base_data/correction/staindoc",
    "drccbi": "01_base_data/correction/drccbi",
    # Layout (1)
    "indicdlp": "01_base_data/layout/indicdlp/images",
    # Specialized (1)
    "markushgrapher": "01_base_data/specialized/markushgrapher/images",
    # Quality / Benchmark (2)
    "document-haystack": "02_benchmark_only/document-haystack",
    "q-doc": "02_benchmark_only/q-doc",
    # Synthetic training (1)
    "synth-multiscript-250k": "03_training_datasets/synthetic_multiscript",
    # Tibetan (1)
    "openpecha-ocr-drutsa": "01_base_data/language/openpecha-ocr-drutsa",
    # Japanese (5)
    "jssoda": "01_base_data/language/multilingual_scripts/jssoda",
    "vjroda": "01_base_data/language/multilingual_scripts/vjroda/images",
    "ndl-docl": "01_base_data/language/multilingual_scripts/ndl-docl/full_images",
    "pdmocr-part1": "01_base_data/language/multilingual_scripts/pdmocr-part1/images",
    "pdmocr-part2": "01_base_data/language/multilingual_scripts/pdmocr-part2/images",
    # Synthetic (1)
    "doc3d": "01_base_data/camera_captured/doc3d/data/doc3d/img",
}


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------


def _load_models(
    model_names: tuple[str, ...],
    device: str,
) -> dict[str, Any]:
    """Load pyiqa metrics for the requested models.

    Args:
        model_names: Model identifiers (subset of ``VALID_MODELS``).
        device: Torch device string (``"cuda"``, ``"cpu"``, etc.).

    Returns:
        Dict mapping model_name to pyiqa metric object.

    Raises:
        ImportError: If pyiqa is not installed.
    """
    import torch

    try:
        import pyiqa
    except ImportError:
        click.echo(
            "ERROR: pyiqa not installed. Run: uv sync --extra iqa",
            err=True,
        )
        raise

    metrics: dict[str, Any] = {}
    for name in model_names:
        if name not in VALID_MODELS:
            click.echo(f"WARNING: Unknown model '{name}', skipping.", err=True)
            continue
        click.echo(f"Loading {name} on {device} ...")
        metric = pyiqa.create_metric(name, device=torch.device(device))
        metrics[name] = metric
        click.echo(f"  {name} loaded (lower_better={metric.lower_better})")
    return metrics


# ---------------------------------------------------------------------------
# Score normalization
# ---------------------------------------------------------------------------


def _normalize_score(raw_score: float, model_name: str) -> float:
    """Normalize a raw model score to [0, 1].

    MUSIQ outputs ~[0, 100] (KonIQ-10k MOS scale).
    TOPIQ-NR outputs ~[0, 1].

    Args:
        raw_score: Raw float from model inference.
        model_name: One of ``VALID_MODELS``.

    Returns:
        Score clipped to ``[0.0, 1.0]``, rounded to 4 decimal places.
    """
    _, hi = SCORE_RANGES[model_name]
    normalized = raw_score / hi if hi > 1.0 else raw_score
    return round(float(max(0.0, min(1.0, normalized))), 4)


# ---------------------------------------------------------------------------
# Ensemble computation
# ---------------------------------------------------------------------------


def _compute_ensemble(scores: dict[str, float]) -> dict[str, Any]:
    """Compute ensemble MOS and model agreement from individual scores.

    Args:
        scores: Dict of ``{model_name: normalized_score}``.

    Returns:
        Complete ``iqa_pseudo_labels`` dict ready for L2 storage.
    """
    result: dict[str, Any] = {"label_tier": "tier_2_model"}

    if "musiq" in scores:
        result["musiq_mos"] = scores["musiq"]
    if "topiq_nr" in scores:
        result["topiq_mos"] = scores["topiq_nr"]

    score_values = list(scores.values())
    result["ensemble_mos"] = round(sum(score_values) / len(score_values), 4)

    if len(score_values) >= 2:
        result["model_agreement"] = round(
            1.0 - abs(score_values[0] - score_values[1]), 4
        )
    else:
        result["model_agreement"] = 1.0

    return result


# ---------------------------------------------------------------------------
# Single-image inference
# ---------------------------------------------------------------------------


def _infer_single(
    img_path: Path,
    metrics: dict[str, Any],
    device: str,
) -> dict[str, Any] | None:
    """Run all loaded NR-IQA models on a single image.

    Loads image via cv2 (BGR), converts to RGB torch tensor [0, 1],
    runs each metric, normalizes scores, computes ensemble.

    Args:
        img_path: Absolute path to image file.
        metrics: Dict of ``{model_name: pyiqa_metric}``.
        device: Torch device string.

    Returns:
        Dict with ``iqa_pseudo_labels`` fields, or ``None`` on load failure.
    """
    import torch

    img_bgr = cv2.imread(str(img_path))
    if img_bgr is None:
        logger.warning("Failed to load image: %s", img_path)
        return None

    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    img_tensor = torch.from_numpy(img_rgb).permute(2, 0, 1).unsqueeze(0).float() / 255.0
    img_tensor = img_tensor.to(device)

    scores: dict[str, float] = {}
    for name, metric in metrics.items():
        try:
            with torch.no_grad():
                raw = metric(img_tensor)
            scores[name] = _normalize_score(float(raw.cpu().item()), name)
        except Exception:
            logger.warning(
                "Inference failed for %s on %s", name, img_path, exc_info=True
            )
            return None

    return _compute_ensemble(scores)


# ---------------------------------------------------------------------------
# Dataset discovery and path resolution
# ---------------------------------------------------------------------------


def _discover_datasets(
    l2_dir: Path,
    filter_names: tuple[str, ...],
) -> list[tuple[str, Path]]:
    """Find all ``*_metadata.json`` files, optionally filtered by name.

    Args:
        l2_dir: Directory containing L2 metadata files.
        filter_names: If non-empty, only include these dataset names.

    Returns:
        Sorted list of ``(dataset_name, metadata_path)`` tuples.
    """
    results: list[tuple[str, Path]] = []
    for meta_path in sorted(l2_dir.glob("*_metadata.json")):
        name = meta_path.stem.replace("_metadata", "")
        if filter_names and name not in filter_names:
            continue
        results.append((name, meta_path))
    return results


def _get_dataset_base(dataset_name: str, e_drive_root: Path) -> Path | None:
    """Resolve dataset base directory from canonical name.

    Args:
        dataset_name: Canonical dataset name.
        e_drive_root: Root of external data drive.

    Returns:
        Resolved path, or ``None`` if dataset not in mapping.
    """
    suffix = _DATASET_PATH_SUFFIXES.get(dataset_name)
    if suffix is None:
        return None
    return e_drive_root / suffix


def _resolve_image_path(
    sample: dict[str, Any],
    dataset_base: Path,
) -> Path | None:
    """Resolve image path from L2 sample's ``source.original_path``.

    Args:
        sample: L2 metadata sample dict.
        dataset_base: Root directory for this dataset.

    Returns:
        Absolute path if file exists, else ``None``.
    """
    original_path = sample.get("source", {}).get("original_path", "")
    if not original_path:
        return None
    full_path = dataset_base / original_path
    if not full_path.exists():
        return None
    return full_path


# ---------------------------------------------------------------------------
# L2 metadata helpers (pattern from label_shadow_severity.py)
# ---------------------------------------------------------------------------


def _get_latest_data(sample: dict[str, Any]) -> dict[str, Any]:
    """Return the mutable ``data`` dict of the latest enrichment version.

    If no versions with a ``data`` key exist, creates and appends a minimal
    version entry so the pseudo-label field has somewhere to live.

    Args:
        sample: A single sample dict from the L2 metadata ``samples`` array.

    Returns:
        The ``data`` dict (may be newly created, always mutable).
    """
    enrichments: dict[str, Any] = sample.setdefault("enrichments", {})
    versions: list[dict[str, Any]] = enrichments.setdefault("versions", [])

    for version_entry in reversed(versions):
        if "data" in version_entry:
            return version_entry["data"]

    stub: dict[str, Any] = {
        "version": len(versions) + 1,
        "created_at": datetime.now(UTC).isoformat(),
        "created_by": "label_iqa_pseudo.py",
        "method": "musiq_topiq_ensemble",
        "data": {},
    }
    versions.append(stub)
    enrichments["current_version"] = len(versions)
    return stub["data"]


def _load_l2(path: Path) -> dict[str, Any]:
    """Load L2 metadata JSON.

    Args:
        path: Path to the metadata file.

    Returns:
        Parsed metadata dict.
    """
    with path.open(encoding="utf-8") as f:
        return json.load(f)  # type: ignore[return-value]


def _save_l2(data: dict[str, Any], path: Path) -> None:
    """Write L2 metadata to disk atomically (temp file -> rename).

    Args:
        data: Metadata dict to serialise.
        path: Destination path.
    """
    parent = path.parent
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=parent,
        suffix=".tmp",
        delete=False,
    ) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp_path = Path(tmp.name)

    shutil.move(str(tmp_path), path)


# ---------------------------------------------------------------------------
# Core labeling loop
# ---------------------------------------------------------------------------


def _label_dataset(
    dataset_name: str,
    l2_path: Path,
    dataset_base: Path,
    metrics: dict[str, Any],
    device: str,
    batch_size: int,
) -> dict[str, int]:
    """Label IQA pseudo-scores for a single dataset.

    Follows the resumable batch pattern from ``label_shadow_severity.py``:
    skips samples where ``iqa_pseudo_labels`` already exists, saves atomically
    every ``batch_size`` samples.

    Args:
        dataset_name: Dataset identifier for display.
        l2_path: Path to ``*_metadata.json``.
        dataset_base: Root image directory.
        metrics: Loaded pyiqa models.
        device: Torch device.
        batch_size: Save interval.

    Returns:
        Counts dict: ``labelled``, ``already_done``, ``skipped``, ``errors``.
    """
    click.echo(f"\n[{dataset_name}] Loading L2 metadata from {l2_path} ...")
    metadata = _load_l2(l2_path)
    samples: list[dict[str, Any]] = metadata.get("samples", [])
    click.echo(f"[{dataset_name}] {len(samples):,} samples loaded")

    counts: dict[str, int] = {
        "labelled": 0,
        "already_done": 0,
        "skipped": 0,
        "errors": 0,
    }

    modified = False
    for batch_start in range(0, len(samples), batch_size):
        batch = samples[batch_start : batch_start + batch_size]

        for sample in tqdm(
            batch,
            desc=f"{dataset_name} [{batch_start:,}-{batch_start + len(batch):,}]",
            unit="img",
        ):
            data_dict = _get_latest_data(sample)

            if "iqa_pseudo_labels" in data_dict:
                counts["already_done"] += 1
                continue

            img_path = _resolve_image_path(sample, dataset_base)
            if img_path is None:
                counts["skipped"] += 1
                continue

            result = _infer_single(img_path, metrics, device)
            if result is None:
                counts["errors"] += 1
                continue

            data_dict["iqa_pseudo_labels"] = result
            counts["labelled"] += 1
            modified = True

        if modified:
            click.echo(f"  Saving progress at sample {batch_start + len(batch):,} ...")
            _save_l2(metadata, l2_path)
            modified = False

    # Final save (covers partial last batch)
    _save_l2(metadata, l2_path)

    click.echo(
        f"[{dataset_name}] Done: "
        f"labelled={counts['labelled']:,}, "
        f"already_done={counts['already_done']:,}, "
        f"skipped={counts['skipped']:,}, "
        f"errors={counts['errors']:,}"
    )
    return counts


# ---------------------------------------------------------------------------
# Spot-check mode
# ---------------------------------------------------------------------------


def _run_spot_check(
    dataset_name: str,
    samples: list[dict[str, Any]],
    dataset_base: Path,
    metrics: dict[str, Any],
    n: int,
    device: str,
) -> None:
    """Sample N images, run inference, print score distributions.

    Args:
        dataset_name: Dataset identifier for display.
        samples: L2 metadata samples list.
        dataset_base: Root image directory.
        metrics: Loaded pyiqa models.
        n: Number of random samples to process.
        device: Torch device.
    """
    eligible = [s for s in samples if _resolve_image_path(s, dataset_base) is not None]
    if not eligible:
        click.echo(f"  [{dataset_name}] No eligible images found for spot-check.")
        return

    selected = random.sample(eligible, min(n, len(eligible)))
    click.echo(
        f"  [{dataset_name}] Spot-checking {len(selected)} / {len(eligible)} images ..."
    )

    ensemble_scores: list[float] = []
    per_model: dict[str, list[float]] = {name: [] for name in metrics}

    for sample in tqdm(selected, desc=f"spot-check {dataset_name}", unit="img"):
        img_path = _resolve_image_path(sample, dataset_base)
        if img_path is None:
            continue
        result = _infer_single(img_path, metrics, device)
        if result is None:
            continue
        ensemble_scores.append(result["ensemble_mos"])
        for name in metrics:
            field = "musiq_mos" if name == "musiq" else "topiq_mos"
            if field in result:
                per_model[name].append(result[field])

    if not ensemble_scores:
        click.echo(f"  [{dataset_name}] All spot-check images failed inference.")
        return

    click.echo(
        f"\n  [{dataset_name}] Spot-check results ({len(ensemble_scores)} images):"
    )
    if len(ensemble_scores) > 1:
        click.echo(
            f"    ensemble_mos: "
            f"min={min(ensemble_scores):.4f}, "
            f"max={max(ensemble_scores):.4f}, "
            f"mean={statistics.mean(ensemble_scores):.4f}, "
            f"median={statistics.median(ensemble_scores):.4f}, "
            f"stdev={statistics.stdev(ensemble_scores):.4f}"
        )
    else:
        click.echo(f"    ensemble_mos: value={ensemble_scores[0]:.4f} (single sample)")
    for name, values in per_model.items():
        if len(values) > 1:
            click.echo(
                f"    {name}: "
                f"min={min(values):.4f}, max={max(values):.4f}, "
                f"mean={statistics.mean(values):.4f}"
            )


# ---------------------------------------------------------------------------
# Validation mode (SRCC gate)
# ---------------------------------------------------------------------------


def _run_validation(
    metrics: dict[str, Any],
    device: str,
    l2_dir: Path,
    e_drive_root: Path,
    limit: int,
    srcc_threshold: float,
) -> bool:
    """Validate ensemble against DIQA-5000 human MOS.

    Loads DIQA-5000 samples from the test split, runs ensemble inference, and
    computes Spearman rank correlation (SRCC) against human MOS scores.

    Args:
        metrics: Loaded pyiqa models.
        device: Torch device.
        l2_dir: L2 metadata directory.
        e_drive_root: External data drive root.
        limit: Max images to process.
        srcc_threshold: Minimum SRCC to pass.

    Returns:
        ``True`` if SRCC >= threshold (PASS), ``False`` otherwise (FAIL).
    """
    from scipy import stats

    diqa_meta_path = l2_dir / _DIQA_METADATA_FILENAME
    diqa_dataset_dir = e_drive_root / _DIQA_DATASET_SUFFIX

    if not diqa_meta_path.exists():
        click.echo(f"ERROR: DIQA-5000 metadata not found: {diqa_meta_path}", err=True)
        return False
    if not diqa_dataset_dir.exists():
        click.echo(f"ERROR: DIQA-5000 dataset not found: {diqa_dataset_dir}", err=True)
        return False

    click.echo(f"Loading DIQA-5000 metadata from {diqa_meta_path} ...")
    metadata = _load_l2(diqa_meta_path)
    all_samples: list[dict[str, Any]] = metadata.get("samples", [])

    # Filter to test split samples with MOS scores
    valid_samples: list[dict[str, Any]] = []
    for s in all_samples:
        split = s.get("source", {}).get("split", "")
        mos = s.get("original_labels", {}).get("mos_overall")
        if split == "test" and mos is not None:
            valid_samples.append(s)

    if limit > 0:
        valid_samples = valid_samples[:limit]

    click.echo(f"Validating on {len(valid_samples)} DIQA-5000/test images ...")

    ensemble_scores: list[float] = []
    human_mos: list[float] = []

    for sample in tqdm(valid_samples, desc="Validating DIQA-5000/test", unit="img"):
        mos_val = sample["original_labels"]["mos_overall"]

        img_path = _resolve_image_path(sample, diqa_dataset_dir)
        if img_path is None:
            continue

        result = _infer_single(img_path, metrics, device)
        if result is None:
            continue

        ensemble_scores.append(result["ensemble_mos"])
        # Normalize human MOS from [1, 5] to [0, 1] for fair comparison
        human_mos.append((float(mos_val) - 1.0) / 4.0)

    if len(ensemble_scores) < 30:
        click.echo(
            f"FAIL: Only {len(ensemble_scores)} valid samples (need >= 30)", err=True
        )
        return False

    preds_arr = np.array(ensemble_scores)
    gt_arr = np.array(human_mos)

    srcc_result = stats.spearmanr(preds_arr, gt_arr)
    srcc = float(getattr(srcc_result, "statistic", srcc_result.correlation))
    pvalue = float(srcc_result.pvalue)

    plcc_result = stats.pearsonr(preds_arr, gt_arr)
    plcc = float(getattr(plcc_result, "statistic", plcc_result[0]))

    mae = float(np.mean(np.abs(preds_arr - gt_arr)))
    rmse = float(np.sqrt(np.mean((preds_arr - gt_arr) ** 2)))

    passed = srcc >= srcc_threshold

    click.echo("\n--- VALIDATION RESULTS ---")
    click.echo(f"  Samples:   {len(ensemble_scores)}")
    click.echo(f"  SRCC:      {srcc:.4f} (p={pvalue:.2e})")
    click.echo(f"  PLCC:      {plcc:.4f}")
    click.echo(f"  MAE:       {mae:.4f}")
    click.echo(f"  RMSE:      {rmse:.4f}")
    click.echo(f"  Threshold: {srcc_threshold}")
    click.echo(f"  Result:    {'PASS' if passed else 'FAIL'}")

    # Per-model diagnostics
    click.echo("\n  Per-model score ranges:")
    click.echo(
        f"    ensemble: [{min(ensemble_scores):.4f}, {max(ensemble_scores):.4f}]"
    )
    click.echo(
        f"    human_mos (normalized): [{min(human_mos):.4f}, {max(human_mos):.4f}]"
    )

    return passed


# ---------------------------------------------------------------------------
# Dry-run mode
# ---------------------------------------------------------------------------


def _run_dry_run(
    l2_dir: Path,
    e_drive_root: Path,
    filter_names: tuple[str, ...],
    model_names: tuple[str, ...],
) -> None:
    """Count eligible samples and estimate processing time.

    Args:
        l2_dir: L2 metadata directory.
        e_drive_root: External data drive root.
        filter_names: If non-empty, only include these datasets.
        model_names: Models that will be used (for latency estimation).
    """
    datasets = _discover_datasets(l2_dir, filter_names)

    total_eligible = 0
    total_already_done = 0
    total_missing = 0
    total_samples = 0
    skipped_datasets: list[str] = []

    for name, meta_path in datasets:
        base = _get_dataset_base(name, e_drive_root)
        if base is None:
            skipped_datasets.append(name)
            continue

        metadata = _load_l2(meta_path)
        samples = metadata.get("samples", [])
        total_samples += len(samples)

        eligible = 0
        already = 0
        missing = 0

        for s in samples:
            data = _get_latest_data(s)
            if "iqa_pseudo_labels" in data:
                already += 1
                continue
            img = _resolve_image_path(s, base)
            if img is None:
                missing += 1
            else:
                eligible += 1

        click.echo(
            f"  {name}: {eligible:,} eligible, {already:,} done, {missing:,} missing "
            f"(total: {len(samples):,})"
        )
        total_eligible += eligible
        total_already_done += already
        total_missing += missing

    if skipped_datasets:
        click.echo(f"\n  Skipped (no path mapping): {', '.join(skipped_datasets)}")

    # Time estimates based on model latencies
    gpu_ms = sum(_GPU_LATENCY_MS.get(m, 25.0) for m in model_names)
    cpu_ms = sum(_CPU_LATENCY_MS.get(m, 150.0) for m in model_names)
    gpu_hours = (total_eligible * gpu_ms) / 1000 / 3600
    cpu_hours = (total_eligible * cpu_ms) / 1000 / 3600

    click.echo("\n--- DRY RUN SUMMARY ---")
    click.echo(f"  Datasets found:   {len(datasets)}")
    click.echo(f"  Datasets skipped: {len(skipped_datasets)}")
    click.echo(f"  Total samples:    {total_samples:,}")
    click.echo(f"  Total eligible:   {total_eligible:,}")
    click.echo(f"  Already done:     {total_already_done:,}")
    click.echo(f"  Missing images:   {total_missing:,}")
    click.echo(f"  Est. GPU time:    {gpu_hours:.1f} hours ({gpu_ms:.0f}ms/img)")
    click.echo(f"  Est. CPU time:    {cpu_hours:.1f} hours ({cpu_ms:.0f}ms/img)")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


@click.command()
@click.option(
    "--datasets",
    multiple=True,
    default=(),
    help="Specific datasets to process. Default: all *_metadata.json discovered.",
)
@click.option(
    "--l2-metadata-dir",
    default="/mnt/e/image_detection/metadata_registry/json/",
    type=click.Path(file_okay=False, path_type=Path),
    help="Directory containing {dataset}_metadata.json files.",
)
@click.option(
    "--e-drive-root",
    default="/mnt/e/image_detection/",
    type=click.Path(file_okay=False, path_type=Path),
    help="Root of the external data drive.",
)
@click.option(
    "--models",
    multiple=True,
    default=("musiq", "topiq_nr"),
    help="NR-IQA models to use. Choices: musiq, topiq_nr.",
)
@click.option(
    "--device",
    default="cuda",
    help="Torch device (cuda, cuda:0, cpu).",
)
@click.option(
    "--batch-size",
    default=500,
    show_default=True,
    type=int,
    help="Save progress to disk every N images.",
)
@click.option(
    "--validate-only",
    is_flag=True,
    help="SRCC gate on DIQA-5000 held-out; no L2 writes.",
)
@click.option(
    "--validation-limit",
    default=500,
    show_default=True,
    type=int,
    help="Max images for validation SRCC computation.",
)
@click.option(
    "--srcc-threshold",
    default=_DEFAULT_SRCC_THRESHOLD,
    show_default=True,
    type=float,
    help="Minimum SRCC to pass validation gate.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Count eligible samples and estimate timing; no inference.",
)
@click.option(
    "--spot-check",
    default=0,
    type=int,
    metavar="N",
    help="Infer N random samples per dataset, print distributions; no L2 writes.",
)
@click.option("--verbose", is_flag=True, help="Enable DEBUG logging.")
def main(
    datasets: tuple[str, ...],
    l2_metadata_dir: Path,
    e_drive_root: Path,
    models: tuple[str, ...],
    device: str,
    batch_size: int,
    validate_only: bool,
    validation_limit: int,
    srcc_threshold: float,
    dry_run: bool,
    spot_check: int,
    verbose: bool,
) -> None:
    """MUSIQ + TOPIQ-NR ensemble pseudo-labeling for corpus-wide IQA.

    Generates IQA pseudo-labels by running pretrained blind NR-IQA models on
    every image in the training corpus.  Results are written into L2 metadata.
    """
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )

    click.echo("=" * 60)
    click.echo("IQA Pseudo-Labeling Pipeline")
    click.echo(f"  Models:    {', '.join(models)}")
    click.echo(f"  Device:    {device}")
    click.echo(f"  L2 dir:    {l2_metadata_dir}")
    click.echo(f"  Data root: {e_drive_root}")
    if datasets:
        click.echo(f"  Datasets:  {', '.join(datasets)}")
    else:
        click.echo("  Datasets:  all (auto-discover)")
    click.echo("=" * 60)

    # --- Dry-run mode: no model loading needed ---
    if dry_run:
        click.echo("\n[DRY RUN] Counting eligible samples ...")
        _run_dry_run(l2_metadata_dir, e_drive_root, datasets, models)
        return

    # --- Load models (needed for validate, spot-check, and full run) ---
    metrics = _load_models(models, device)
    if not metrics:
        click.echo("ERROR: No models loaded. Aborting.", err=True)
        raise SystemExit(1)

    # --- Validate-only mode ---
    if validate_only:
        click.echo("\n[VALIDATE] Running SRCC gate on DIQA-5000 ...")
        passed = _run_validation(
            metrics,
            device,
            l2_metadata_dir,
            e_drive_root,
            validation_limit,
            srcc_threshold,
        )
        raise SystemExit(0 if passed else 1)

    # --- Discover datasets ---
    discovered = _discover_datasets(l2_metadata_dir, datasets)
    if not discovered:
        click.echo("No datasets found. Check --l2-metadata-dir and --datasets.")
        return

    click.echo(f"\nDiscovered {len(discovered)} dataset(s)")

    # --- Process each dataset ---
    grand_totals: dict[str, int] = {
        "labelled": 0,
        "already_done": 0,
        "skipped": 0,
        "errors": 0,
    }
    processed = 0
    skipped_datasets: list[str] = []

    for name, meta_path in discovered:
        base = _get_dataset_base(name, e_drive_root)
        if base is None:
            logger.info("Skipping %s: no path mapping in _DATASET_PATH_SUFFIXES", name)
            skipped_datasets.append(name)
            continue

        if not base.exists():
            logger.info("Skipping %s: directory not found: %s", name, base)
            skipped_datasets.append(name)
            continue

        if spot_check > 0:
            # Spot-check mode: load metadata, run spot check, no writes
            metadata = _load_l2(meta_path)
            samples = metadata.get("samples", [])
            _run_spot_check(name, samples, base, metrics, spot_check, device)
        else:
            # Full run: label and write back
            counts = _label_dataset(
                name,
                meta_path,
                base,
                metrics,
                device,
                batch_size,
            )
            for key in grand_totals:
                grand_totals[key] += counts[key]

        processed += 1

    # --- Summary ---
    click.echo("\n" + "=" * 60)
    click.echo("GRAND SUMMARY")
    click.echo(f"  Processed:    {processed} dataset(s)")
    if skipped_datasets:
        click.echo(
            f"  Skipped:      {len(skipped_datasets)} ({', '.join(skipped_datasets[:5])}{'...' if len(skipped_datasets) > 5 else ''})"
        )

    if spot_check == 0:
        click.echo(f"  Labelled:     {grand_totals['labelled']:,}")
        click.echo(f"  Already done: {grand_totals['already_done']:,}")
        click.echo(f"  Skipped:      {grand_totals['skipped']:,}")
        click.echo(f"  Errors:       {grand_totals['errors']:,}")
    click.echo("=" * 60)


if __name__ == "__main__":
    main()
