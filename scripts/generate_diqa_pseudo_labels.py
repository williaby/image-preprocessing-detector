#!/usr/bin/env python3
"""Generate DIQA-style pseudo-labels for the unified training corpus.

Uses DeQA-Doc per-dimension models (mPLUG-Owl2-7B) via subprocess
isolation to score all images in a training manifest across 3
DIQA dimensions: overall, sharpness, color_fidelity.

Output is a JSONL file with soft probability distributions and
normalized scores suitable for SigLIP 2 multi-task training.

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python scripts/generate_diqa_pseudo_labels.py \\
            --manifest /path/to/training_manifest.jsonl \\
            --deqa-venv /home/byron/dev/DeQA-Doc/DeQA-Score/.venv \\
            --deqa-root /home/byron/dev/DeQA-Doc/DeQA-Score \\
            --model-dir /path/to/deqa_models \\
            --output /path/to/diqa_pseudo_labels.jsonl \\
            --device cuda:0

Manifest format (input JSONL):
    {"image_path": "/abs/path/to/image.jpg", "sha256": "abc123..."}

Output format (JSONL):
    {
        "sha256": "abc123...",
        "image_path": "/abs/path/to/image.jpg",
        "deqa_model": "mplug_owl2_7b_per_dim",
        "overall": {"level_probs": [0.02, 0.08, 0.30, 0.45, 0.15], "score": 0.605},
        "sharpness": {"level_probs": [...], "score": 0.72},
        "color_fidelity": {"level_probs": [...], "score": 0.81},
        "inference_time_ms": 1350.0
    }

Checkpointing:
    Progress is saved every --checkpoint-interval images. If interrupted,
    re-running with the same --output will skip already-processed images.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections.abc import Callable
from pathlib import Path


def _load_completed(output_path: Path) -> set[str]:
    """Load SHA256s of already-processed images from output file."""
    completed: set[str] = set()
    if output_path.exists():
        with output_path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    sha = record.get("sha256")
                    if sha:
                        completed.add(sha)
                except json.JSONDecodeError:
                    continue
    return completed


def _load_manifest(manifest_path: Path) -> list[dict[str, str]]:
    """Load training manifest, returning list of {image_path, sha256} dicts."""
    records: list[dict[str, str]] = []
    with manifest_path.open() as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                print(
                    f"WARNING: Skipping malformed line {line_num}: {exc}",
                    file=sys.stderr,
                )
                continue

            if "image_path" not in record:
                print(
                    f"WARNING: Line {line_num} missing 'image_path', skipping",
                    file=sys.stderr,
                )
                continue

            # Compute sha256 if not provided
            if "sha256" not in record:
                img_path = Path(record["image_path"])
                if img_path.exists():
                    h = hashlib.sha256()
                    with open(img_path, "rb") as img_f:
                        for chunk in iter(lambda: img_f.read(65536), b""):
                            h.update(chunk)
                    record["sha256"] = h.hexdigest()
                else:
                    record["sha256"] = ""

            records.append(record)
    return records


def main() -> None:
    """Run the pseudo-labeling pipeline."""
    parser = argparse.ArgumentParser(
        description="Generate DIQA pseudo-labels using DeQA-Doc models"
    )
    parser.add_argument(
        "--manifest", type=str, required=True, help="Input JSONL manifest"
    )
    parser.add_argument(
        "--deqa-venv", type=str, required=True, help="Path to DeQA-Doc venv"
    )
    parser.add_argument(
        "--deqa-root", type=str, required=True, help="Path to DeQA-Score root"
    )
    parser.add_argument(
        "--model-dir",
        type=str,
        required=True,
        help="Directory containing per-dimension model dirs (overall/, sharpness/, color_fidelity/)",
    )
    parser.add_argument("--output", type=str, required=True, help="Output JSONL path")
    parser.add_argument("--device", type=str, default="cuda:0")
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=500,
        help="Save progress every N images",
    )
    parser.add_argument("--preprocessor-path", type=str, default=None)
    parser.add_argument("--load-8bit", action="store_true")
    parser.add_argument("--load-4bit", action="store_true")
    args = parser.parse_args()

    # Lazy import to allow --help without dependencies
    from image_preprocessing_detector.labeling.deqa.subprocess_runner import (
        DeQARunnerConfig,
        DeQASubprocessRunner,
    )

    model_dir = Path(args.model_dir)
    model_paths = {
        "overall": str(model_dir / "overall"),
        "sharpness": str(model_dir / "sharpness"),
        "color_fidelity": str(model_dir / "color_fidelity"),
    }

    # Validate model directories exist
    for dim, path in model_paths.items():
        if not Path(path).exists():
            print(
                f"ERROR: Model directory for '{dim}' not found: {path}", file=sys.stderr
            )
            sys.exit(1)

    config = DeQARunnerConfig(
        deqa_venv=args.deqa_venv,
        deqa_root=args.deqa_root,
        model_paths=model_paths,
        device=args.device,
        batch_size=args.batch_size,
        preprocessor_path=args.preprocessor_path,
        load_8bit=args.load_8bit,
        load_4bit=args.load_4bit,
    )

    runner = DeQASubprocessRunner(config)

    # Load manifest and skip already-completed
    manifest_path = Path(args.manifest)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    records = _load_manifest(manifest_path)
    completed = _load_completed(output_path)

    remaining = [r for r in records if r["sha256"] not in completed]
    print(
        f"Manifest: {len(records)} total, {len(completed)} already done, "
        f"{len(remaining)} remaining",
        file=sys.stderr,
    )

    if not remaining:
        print("All images already processed. Nothing to do.", file=sys.stderr)
        return

    # Process in chunks for checkpointing
    chunk_size = args.checkpoint_interval
    total_processed = 0
    start_time = time.monotonic()

    for chunk_start in range(0, len(remaining), chunk_size):
        chunk = remaining[chunk_start : chunk_start + chunk_size]
        image_paths = [r["image_path"] for r in chunk]
        sha_map = {r["image_path"]: r["sha256"] for r in chunk}

        def _make_progress(base_processed: int) -> Callable[[str, int, int], None]:
            def _progress(dimension: str, processed: int, total: int) -> None:
                elapsed = time.monotonic() - start_time
                overall_done = base_processed + processed
                rate = overall_done / max(elapsed, 0.001)
                print(
                    f"  [{dimension}] {processed}/{total} "
                    f"(overall: {overall_done}/{len(remaining)}, "
                    f"{rate:.1f} img/s)",
                    file=sys.stderr,
                    end="\r",
                )

            return _progress

        predictions = runner.score_images(
            image_paths, progress_callback=_make_progress(total_processed)
        )

        # Write results
        with output_path.open("a") as f:
            for pred in predictions:
                output_record = {
                    "sha256": sha_map.get(pred.image_path, ""),
                    "image_path": pred.image_path,
                    "deqa_model": "mplug_owl2_7b_per_dim",
                }

                for dim in ("overall", "sharpness", "color_fidelity"):
                    score = getattr(pred, dim)
                    if score is not None:
                        output_record[dim] = {
                            "level_probs": score.level_probs,
                            "score": score.score_normalized,
                        }
                    else:
                        output_record[dim] = None

                output_record["inference_time_ms"] = pred.inference_time_ms
                if pred.errors:
                    output_record["errors"] = pred.errors

                f.write(json.dumps(output_record) + "\n")

        total_processed += len(chunk)
        elapsed = time.monotonic() - start_time
        rate = total_processed / max(elapsed, 0.001)
        print(
            f"\nCheckpoint: {total_processed}/{len(remaining)} processed "
            f"({rate:.1f} img/s, elapsed {elapsed:.0f}s)",
            file=sys.stderr,
        )

    elapsed = time.monotonic() - start_time
    print(
        f"\nDone. Processed {total_processed} images in {elapsed:.0f}s "
        f"({total_processed / max(elapsed, 0.001):.1f} img/s). "
        f"Output: {output_path}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
