#!/usr/bin/env python3
"""CLI for multi-model handwriting legibility scoring via VLM contact sheets.

Five subcommands run in sequence to produce Layer 2 legibility metadata:

    select     -- Stratified sampling of handwriting images from a dataset
    sheets     -- Create labeled contact sheets from a sample manifest
    score      -- Send sheets to multiple OpenRouter vision models
    aggregate  -- Compute consensus scores across models
    integrate  -- Write consensus scores into Layer 2 metadata JSONs

Usage::

    # Full pipeline on IAM (dry run first)
    python scripts/score_handwriting_legibility.py select iam --count 24 --dry-run
    python scripts/score_handwriting_legibility.py sheets results/hw_legibility/iam/manifest.json
    python scripts/score_handwriting_legibility.py score results/hw_legibility/iam/sheets/ --dry-run
    python scripts/score_handwriting_legibility.py score results/hw_legibility/iam/sheets/
    python scripts/score_handwriting_legibility.py aggregate results/hw_legibility/iam/
    python scripts/score_handwriting_legibility.py integrate results/hw_legibility/iam/consensus_scores.json

    # HierText calibration (validates against ground-truth legibility bool)
    python scripts/score_handwriting_legibility.py select hiertext --count 200
    python scripts/score_handwriting_legibility.py sheets results/hw_legibility/hiertext/manifest.json
    python scripts/score_handwriting_legibility.py score results/hw_legibility/hiertext/sheets/
    python scripts/score_handwriting_legibility.py aggregate results/hw_legibility/hiertext/ \\
        --validate-against-gt results/hw_legibility/hiertext/manifest.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
import structlog

logger = structlog.get_logger(__name__)

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────

# Default Layer 2 metadata root (can override with --l2-dir)
DEFAULT_L2_DIR = Path("/mnt/e/image_detection/metadata_registry/json")

# Results directory root
DEFAULT_RESULTS_DIR = Path("results/hw_legibility")

# Datasets where presence is always NONE (skip VLM — use rule-based labeling)
ALWAYS_NONE_DATASETS = frozenset(
    {
        "doclaynet",
        "pubtabnet",
        "rvl-cdip",
        "tablebank",
        "fintabnet",
        "funsd",
        "funsd-plus",
        "sroie",
    }
)

# Datasets where ground-truth legibility bools exist (for --validate-against-gt)
GT_LEGIBILITY_BOOL_DATASETS = frozenset({"hiertext", "coco-text"})


# ──────────────────────────────────────────────
# CLI group
# ──────────────────────────────────────────────


@click.group()
@click.version_option("1.0.0")
def cli() -> None:
    """Multi-model VLM scoring for handwriting legibility labels."""


# ──────────────────────────────────────────────
# select
# ──────────────────────────────────────────────


@cli.command()
@click.argument("dataset")
@click.option(
    "--count",
    default=500,
    show_default=True,
    help="Number of images to sample (0 = all).",
)
@click.option(
    "--l2-dir",
    type=click.Path(path_type=Path),
    default=DEFAULT_L2_DIR,
    show_default=True,
    help="Layer 2 metadata root directory.",
)
@click.option(
    "--results-dir",
    type=click.Path(path_type=Path),
    default=DEFAULT_RESULTS_DIR,
    show_default=True,
    help="Output root for hw_legibility results.",
)
@click.option("--dry-run", is_flag=True, help="Print manifest without saving.")
def select(
    dataset: str,
    count: int,
    l2_dir: Path,
    results_dir: Path,
    dry_run: bool,
) -> None:
    """Sample images from DATASET and write a scoring manifest.

    DATASET: canonical dataset name (e.g. iam, hiertext, muharaf).

    The manifest is a JSON list of dicts with keys:
    ``image_path``, ``sample_id``, ``gt_legible`` (None unless dataset has GT).
    """
    if dataset in ALWAYS_NONE_DATASETS:
        click.echo(
            f"[skip] {dataset} is rule-based (presence=NONE). No VLM scoring needed.",
            err=True,
        )
        sys.exit(0)

    metadata_path = _find_l2_metadata(l2_dir, dataset)
    if metadata_path is None:
        click.echo(
            f"[error] No L2 metadata found for '{dataset}' in {l2_dir}", err=True
        )
        sys.exit(1)

    samples = _load_l2_samples(metadata_path)
    if count > 0 and len(samples) > count:
        import random

        random.seed(42)
        samples = random.sample(samples, count)

    has_gt = dataset in GT_LEGIBILITY_BOOL_DATASETS
    manifest = _build_manifest(samples, has_gt)

    click.echo(
        f"[select] {dataset}: {len(manifest)} images selected"
        f"{' (has GT legibility)' if has_gt else ''}",
        err=True,
    )

    if dry_run:
        click.echo(json.dumps(manifest[:3], indent=2))
        click.echo(f"... ({len(manifest)} total — dry run, not saved)", err=True)
        return

    out_dir = results_dir / dataset
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    click.echo(f"[select] Manifest saved: {manifest_path}", err=True)


# ──────────────────────────────────────────────
# sheets
# ──────────────────────────────────────────────


@cli.command()
@click.argument("manifest_path", type=click.Path(exists=True, path_type=Path))
@click.option("--cols", default=4, show_default=True, help="Columns per contact sheet.")
@click.option("--rows", default=3, show_default=True, help="Rows per contact sheet.")
@click.option(
    "--cell-width",
    default=512,
    show_default=True,
    help="Cell thumbnail width in pixels.",
)
@click.option(
    "--jpeg-quality", default=85, show_default=True, help="JPEG save quality."
)
def sheets(
    manifest_path: Path,
    cols: int,
    rows: int,
    cell_width: int,
    jpeg_quality: int,
) -> None:
    """Create labeled contact sheets from MANIFEST_PATH.

    Sheets are saved alongside the manifest in a ``sheets/`` subdirectory.
    A ``sheet_index.json`` maps sheet filename → list of image indices.
    """
    from image_preprocessing_detector.labeling.handwriting.contact_sheet import (
        create_hw_contact_sheet,
        partition_into_sheets,
    )

    manifest = json.loads(manifest_path.read_text())
    image_paths = [Path(entry["image_path"]) for entry in manifest]
    images_per_sheet = cols * rows

    batches = partition_into_sheets(image_paths, images_per_sheet)
    out_dir = manifest_path.parent / "sheets"
    out_dir.mkdir(parents=True, exist_ok=True)

    sheet_index: list[dict[str, object]] = []
    global_offset = 0

    for sheet_num, batch in enumerate(batches, start=1):
        sheet_name = f"sheet_{sheet_num:04d}.jpg"
        sheet_path = out_dir / sheet_name

        create_hw_contact_sheet(
            batch,
            sheet_path,
            cols=cols,
            cell_width_px=cell_width,
            jpeg_quality=jpeg_quality,
        )

        indices = list(range(global_offset, global_offset + len(batch)))
        sheet_index.append(
            {
                "sheet_file": sheet_name,
                "n_images": len(batch),
                "manifest_indices": indices,
                "global_offset": global_offset,
            }
        )
        global_offset += len(batch)

        click.echo(
            f"[sheets] {sheet_name}: {len(batch)} images "
            f"(manifest indices {indices[0]}–{indices[-1]})",
            err=True,
        )

    index_path = out_dir / "sheet_index.json"
    index_path.write_text(json.dumps(sheet_index, indent=2))
    click.echo(f"[sheets] {len(batches)} sheets saved to {out_dir}", err=True)
    click.echo(f"[sheets] Index: {index_path}", err=True)


# ──────────────────────────────────────────────
# score
# ──────────────────────────────────────────────


@cli.command()
@click.argument("sheets_dir", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--models",
    multiple=True,
    default=(),
    help="Model IDs to use (repeatable). Defaults to config roster.",
)
@click.option(
    "--dry-run", is_flag=True, help="Print prompt and exit without API calls."
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Override raw_scores output directory.",
)
def score(
    sheets_dir: Path,
    models: tuple[str, ...],
    dry_run: bool,
    output_dir: Path | None,
) -> None:
    """Send contact sheets in SHEETS_DIR to vision models and save raw scores.

    Raw scores per model are saved as JSON files in a ``raw_scores/``
    subdirectory alongside the sheets.
    """
    from image_preprocessing_detector.labeling.handwriting.config import (
        HwVisionModelConfig,
        LegibilityScorerConfig,
    )
    from image_preprocessing_detector.labeling.handwriting.scorer import (
        HwLegibilityScorer,
    )

    index_path = sheets_dir / "sheet_index.json"
    if not index_path.exists():
        click.echo(f"[error] sheet_index.json not found in {sheets_dir}", err=True)
        sys.exit(1)

    sheet_index = json.loads(index_path.read_text())

    # Build config — override model roster if --models specified
    if models:
        model_tuple = tuple(HwVisionModelConfig(model_id=m) for m in models)
        cfg = LegibilityScorerConfig(vision_models=model_tuple)
    else:
        from image_preprocessing_detector.labeling.handwriting.config import (
            get_default_config,
        )

        cfg = get_default_config()

    if dry_run:
        click.echo("[dry-run] Models that would be called:", err=True)
        for m in cfg.vision_models:
            click.echo(f"  - {m.model_id}", err=True)
        click.echo(f"[dry-run] Sheets to score: {len(sheet_index)}", err=True)
        click.echo(
            f"[dry-run] API calls: {len(sheet_index)} × {len(cfg.vision_models)} = "
            f"{len(sheet_index) * len(cfg.vision_models)}",
            err=True,
        )
        return

    raw_scores_dir = output_dir or (sheets_dir.parent / "raw_scores")
    raw_scores_dir.mkdir(parents=True, exist_ok=True)

    scorer = HwLegibilityScorer(cfg)

    # Accumulate results per model across all sheets
    all_model_results: dict[str, dict[int, dict[str, object]]] = {
        m.model_id: {} for m in cfg.vision_models
    }
    all_errors: dict[str, list[str]] = {m.model_id: [] for m in cfg.vision_models}

    for sheet_entry in sheet_index:
        sheet_file = str(sheet_entry["sheet_file"])
        n_images = int(str(sheet_entry["n_images"]))
        global_offset = int(str(sheet_entry["global_offset"]))
        sheet_path = sheets_dir / sheet_file

        if not sheet_path.exists():
            click.echo(f"[warning] Missing sheet: {sheet_path}", err=True)
            continue

        result = scorer.score_sheet(sheet_path, n_images)

        # Remap local 1-based indices to global manifest indices
        for model_id, per_image in result.model_scores.items():
            for local_idx, score_dict in per_image.items():
                global_idx = global_offset + (local_idx - 1)
                all_model_results[model_id][global_idx] = score_dict

        for model_id, error in result.model_errors.items():
            all_errors[model_id].append(f"{sheet_file}: {error}")

        click.echo(
            f"[score] {sheet_file}: "
            f"{len(result.model_scores)} models OK, "
            f"{len(result.model_errors)} errors",
            err=True,
        )

    # Save per-model raw score files
    for model_id, scores in all_model_results.items():
        slug = _model_slug(model_id)
        out_path = raw_scores_dir / f"{slug}.json"
        payload = {
            "model_id": model_id,
            "scores": {str(k): v for k, v in scores.items()},
            "errors": all_errors.get(model_id, []),
        }
        out_path.write_text(json.dumps(payload, indent=2))
        click.echo(f"[score] Saved: {out_path} ({len(scores)} images)", err=True)

    stats = scorer.get_usage_stats()
    click.echo(
        f"[score] Done. Total API calls: {stats['total_calls']}, "
        f"tokens: {stats['total_tokens']:,}",
        err=True,
    )


# ──────────────────────────────────────────────
# aggregate
# ──────────────────────────────────────────────


@cli.command()
@click.argument("dataset_dir", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--disagreement-threshold",
    default=0.20,
    show_default=True,
    help="Std dev above which scores are flagged as high_disagreement.",
)
@click.option(
    "--min-responses",
    default=2,
    show_default=True,
    help="Minimum model responses required for consensus.",
)
@click.option(
    "--validate-against-gt",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Manifest with gt_legible bool fields for calibration SRCC check.",
)
def aggregate(
    dataset_dir: Path,
    disagreement_threshold: float,
    min_responses: int,
    validate_against_gt: Path | None,
) -> None:
    """Aggregate raw model scores into consensus_scores.json.

    DATASET_DIR should contain a ``raw_scores/`` subdirectory produced
    by the ``score`` subcommand.
    """
    from image_preprocessing_detector.labeling.handwriting.aggregator import (
        aggregate_sheet_scores,
    )

    raw_scores_dir = dataset_dir / "raw_scores"
    if not raw_scores_dir.exists():
        click.echo(f"[error] raw_scores/ not found in {dataset_dir}", err=True)
        sys.exit(1)

    model_scores: dict[str, dict[int, dict[str, object]]] = {}
    model_weights: dict[str, float] = {}

    for score_file in sorted(raw_scores_dir.glob("*.json")):
        payload = json.loads(score_file.read_text())
        model_id = str(payload.get("model_id", score_file.stem))
        raw = payload.get("scores", {})
        model_scores[model_id] = {int(k): v for k, v in raw.items()}
        model_weights[model_id] = 1.0
        click.echo(
            f"[aggregate] Loaded {len(model_scores[model_id])} scores from {model_id}",
            err=True,
        )

    if not model_scores:
        click.echo("[error] No raw score files found.", err=True)
        sys.exit(1)

    consensus = aggregate_sheet_scores(
        model_scores,
        model_weights=model_weights,
        disagreement_threshold=disagreement_threshold,
        min_model_responses=min_responses,
    )

    # Summary statistics
    n_total = len(consensus)
    n_needs_review = sum(1 for s in consensus.values() if s.needs_review)
    n_high_disagreement = sum(1 for s in consensus.values() if s.high_disagreement)
    valid_scores = [
        s.legibility_score
        for s in consensus.values()
        if s.legibility_score is not None and not s.needs_review
    ]

    if valid_scores:
        mean_score = sum(valid_scores) / len(valid_scores)
        variance = sum((x - mean_score) ** 2 for x in valid_scores) / len(valid_scores)
        import math as _math

        std_score = _math.sqrt(variance)
    else:
        mean_score = std_score = 0.0

    click.echo(f"[aggregate] {n_total} images processed", err=True)
    click.echo(f"[aggregate] needs_review: {n_needs_review}", err=True)
    click.echo(f"[aggregate] high_disagreement: {n_high_disagreement}", err=True)
    click.echo(
        f"[aggregate] legibility_score — mean: {mean_score:.3f}, std: {std_score:.3f}",
        err=True,
    )

    if std_score < 0.15:
        click.echo(
            "[WARNING] Score spread is low (std < 0.15). "
            "Possible score compression — check prompt and calibrate.",
            err=True,
        )

    # Optional ground-truth validation (HierText calibration gate)
    if validate_against_gt is not None:
        _run_gt_validation(consensus, validate_against_gt)

    # Serialise
    output: list[dict[str, object]] = []
    for idx, score in sorted(consensus.items()):
        output.append(
            {
                "image_idx": idx,
                "presence": score.presence,
                "presence_score": score.presence_score,
                "legibility": score.legibility,
                "legibility_score": score.legibility_score,
                "legibility_confidence": score.legibility_confidence,
                "model_count": score.model_count,
                "model_names": score.model_names,
                "high_disagreement": score.high_disagreement,
                "needs_review": score.needs_review,
            }
        )

    out_path = dataset_dir / "consensus_scores.json"
    out_path.write_text(json.dumps(output, indent=2))
    click.echo(f"[aggregate] Saved: {out_path}", err=True)


# ──────────────────────────────────────────────
# integrate
# ──────────────────────────────────────────────


@cli.command()
@click.argument("consensus_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--l2-dir",
    type=click.Path(path_type=Path),
    default=DEFAULT_L2_DIR,
    show_default=True,
    help="Layer 2 metadata root directory.",
)
@click.option(
    "--manifest",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Manifest JSON to map image indices back to sample IDs.",
)
@click.option("--dry-run", is_flag=True, help="Print updates without writing files.")
def integrate(
    consensus_path: Path,
    l2_dir: Path,
    manifest: Path | None,
    dry_run: bool,
) -> None:
    """Write consensus scores from CONSENSUS_PATH into Layer 2 metadata.

    Each image's legibility and presence fields are written to the
    ``handwriting_assessment`` block inside the L2 enrichment payload.
    """
    from image_preprocessing_detector.labeling.handwriting.config import PROMPT_VERSION

    consensus_list = json.loads(consensus_path.read_text())

    # Load manifest to resolve image_idx → sample_id / L2 metadata path
    manifest_data: list[dict[str, object]] = []
    if manifest is not None:
        manifest_data = json.loads(manifest.read_text())
    else:
        # Auto-discover manifest from same directory
        auto_manifest = consensus_path.parent / "manifest.json"
        if auto_manifest.exists():
            manifest_data = json.loads(auto_manifest.read_text())

    if not manifest_data:
        click.echo(
            "[error] Manifest not found — cannot map indices to sample IDs.", err=True
        )
        sys.exit(1)

    n_updated = n_skipped = n_missing = 0

    for entry in consensus_list:
        idx = int(str(entry["image_idx"]))
        if idx >= len(manifest_data):
            n_missing += 1
            continue

        manifest_entry = manifest_data[idx]
        sample_id = str(manifest_entry.get("sample_id", ""))
        if not sample_id:
            n_skipped += 1
            continue

        if entry.get("needs_review"):
            n_skipped += 1
            continue

        l2_path = _find_sample_l2_path(l2_dir, sample_id)
        if l2_path is None:
            n_missing += 1
            continue

        update = {
            "hw_legibility_score": entry.get("legibility_score"),
            "hw_legibility_class": entry.get("legibility"),
            "hw_legibility_confidence": entry.get("legibility_confidence"),
            "hw_presence_score": entry.get("presence_score"),
            "hw_presence_class": entry.get("presence"),
            "hw_legibility_model_count": entry.get("model_count"),
            "hw_legibility_model_names": entry.get("model_names"),
            "hw_legibility_prompt_version": PROMPT_VERSION,
        }

        if dry_run:
            click.echo(f"[dry-run] Would update {l2_path.name}: {update}", err=True)
        else:
            _write_l2_update(l2_path, sample_id, update)

        n_updated += 1

    click.echo(
        f"[integrate] updated={n_updated}, skipped={n_skipped}, missing={n_missing}",
        err=True,
    )


# ──────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────


def _model_slug(model_id: str) -> str:
    """Convert a model ID to a safe filename slug.

    Args:
        model_id: OpenRouter model identifier, e.g. 'google/gemini-2.0-flash-001'.

    Returns:
        Filename-safe slug, e.g. 'google-gemini-2.0-flash-001'.
    """
    return model_id.replace("/", "-").replace(":", "-")


def _find_l2_metadata(l2_dir: Path, dataset: str) -> Path | None:
    """Locate the L2 metadata JSON for a dataset.

    Tries ``{dataset}_metadata.json`` and ``{dataset}.json`` naming patterns.

    Args:
        l2_dir: Root directory of L2 metadata files.
        dataset: Canonical dataset name.

    Returns:
        Path to metadata file, or None if not found.
    """
    for name in (f"{dataset}_metadata.json", f"{dataset}.json"):
        path = l2_dir / name
        if path.exists():
            return path
    return None


def _load_l2_samples(metadata_path: Path) -> list[dict[str, object]]:
    """Load sample list from an L2 metadata JSON file.

    Args:
        metadata_path: Path to the L2 metadata JSON.

    Returns:
        List of sample dicts.
    """
    data = json.loads(metadata_path.read_text())
    if isinstance(data, list):
        return data
    return data.get("samples", [])


def _build_manifest(
    samples: list[dict[str, object]],
    has_gt: bool,
) -> list[dict[str, object]]:
    """Build a scoring manifest from L2 sample dicts.

    Args:
        samples: L2 sample dicts containing image_path and sample_id.
        has_gt: True if dataset has ground-truth ``legible`` bool field.

    Returns:
        Manifest list with image_path, sample_id, and optional gt_legible.
    """
    manifest = []
    for sample in samples:
        image_path = str(sample.get("image_path") or sample.get("file_path") or "")
        sample_id = str(sample.get("sample_id") or sample.get("id") or "")
        if not image_path:
            continue
        entry: dict[str, object] = {
            "image_path": image_path,
            "sample_id": sample_id,
        }
        if has_gt:
            # HierText / COCO-Text ground-truth legible bool
            entry["gt_legible"] = sample.get("gt_legible") or sample.get("legible")
        manifest.append(entry)
    return manifest


def _find_sample_l2_path(l2_dir: Path, sample_id: str) -> Path | None:
    """Locate the L2 metadata JSON for a specific sample.

    Sample IDs typically encode the dataset name as a prefix, e.g.
    ``iam_a01-000u-00``. Falls back to scanning json/ subdir.

    Args:
        l2_dir: Root directory of L2 metadata files.
        sample_id: Unique sample identifier.

    Returns:
        Path to metadata file, or None if not found.
    """
    # Primary: dataset-named bulk file (most common L2 pattern)
    dataset_prefix = sample_id.split("_")[0] if "_" in sample_id else sample_id[:6]
    for name in (f"{dataset_prefix}_metadata.json", f"{dataset_prefix}.json"):
        path = l2_dir / name
        if path.exists():
            return path
    return None


def _write_l2_update(
    l2_path: Path,
    sample_id: str,
    update: dict[str, object],
) -> None:
    """Write handwriting assessment fields into a bulk L2 metadata file.

    Locates the sample by sample_id inside the bulk JSON and updates
    the ``enrichments.versions[-1].data`` block in place.

    Args:
        l2_path: Path to the bulk L2 metadata JSON file.
        sample_id: ID of the sample to update.
        update: Dict of field names and values to write.
    """
    data = json.loads(l2_path.read_text())
    samples = data if isinstance(data, list) else data.get("samples", [])

    updated = False
    for sample in samples:
        sid = str(sample.get("sample_id") or sample.get("id") or "")
        if sid != sample_id:
            continue
        enrichments = sample.setdefault("enrichments", {})
        versions: list[dict[str, object]] = enrichments.setdefault("versions", [])
        if not versions:
            versions.append({"data": {}})
        data_block = versions[-1].setdefault("data", {})
        data_block.update(update)
        updated = True
        break

    if not updated:
        logger.warning(
            "l2_write_sample_not_found", sample_id=sample_id, path=str(l2_path)
        )
        return

    if isinstance(data, list):
        l2_path.write_text(json.dumps(data, indent=2))
    else:
        l2_path.write_text(json.dumps(data, indent=2))


def _run_gt_validation(
    consensus: dict[int, object],
    manifest_path: Path,
) -> None:
    """Compute SRCC against ground-truth legibility bools (HierText calibration).

    Prints SRCC to stderr. Target: SRCC > 0.60 before scaling to full datasets.

    Args:
        consensus: Aggregated consensus scores dict.
        manifest_path: Manifest JSON with ``gt_legible`` bool per entry.
    """
    manifest = json.loads(manifest_path.read_text())

    pred_scores: list[float] = []
    gt_values: list[float] = []

    for idx, score in consensus.items():  # type: ignore[union-attr]
        if idx >= len(manifest):
            continue
        gt_legible = manifest[idx].get("gt_legible")
        if gt_legible is None:
            continue
        ls = getattr(score, "legibility_score", None)
        if ls is None:
            continue
        pred_scores.append(float(ls))
        gt_values.append(1.0 if gt_legible else 0.0)

    if len(pred_scores) < 10:
        click.echo(
            f"[validate] Only {len(pred_scores)} paired GT samples — SRCC unreliable.",
            err=True,
        )
        return

    srcc = _spearman_rank_correlation(pred_scores, gt_values)
    passed = srcc >= 0.60
    status = "PASS" if passed else "FAIL (target >= 0.60)"
    click.echo(
        f"[validate] GT calibration SRCC: {srcc:.3f} — {status} "
        f"({len(pred_scores)} paired samples)",
        err=True,
    )
    if not passed:
        click.echo(
            "[validate] WARNING: Low SRCC — do not scale to full datasets. "
            "Revise prompt version and re-run calibration.",
            err=True,
        )


def _spearman_rank_correlation(x: list[float], y: list[float]) -> float:
    """Compute Spearman rank correlation coefficient.

    Args:
        x: Predicted scores.
        y: Ground-truth values.

    Returns:
        SRCC float in [-1, 1].
    """
    n = len(x)
    if n < 3:
        return 0.0

    def rank(values: list[float]) -> list[float]:
        sorted_vals = sorted(enumerate(values), key=lambda t: t[1])
        ranks: list[float] = [0.0] * n
        for rank_val, (orig_idx, _) in enumerate(sorted_vals, start=1):
            ranks[orig_idx] = float(rank_val)
        return ranks

    rx, ry = rank(x), rank(y)
    mean_rx = sum(rx) / n
    mean_ry = sum(ry) / n
    num = sum((a - mean_rx) * (b - mean_ry) for a, b in zip(rx, ry))
    den_x = sum((a - mean_rx) ** 2 for a in rx) ** 0.5
    den_y = sum((b - mean_ry) ** 2 for b in ry) ** 0.5
    if den_x == 0 or den_y == 0:
        return 0.0
    return num / (den_x * den_y)


if __name__ == "__main__":
    cli()
