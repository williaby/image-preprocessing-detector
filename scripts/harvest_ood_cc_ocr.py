#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Register CC-OCR benchmark images into the OOD registry.

Targets:
  - multi_lan_ocr/Korean   → 150 images → ood_script  (Hang — 0 existing)
  - multi_lan_ocr/Russian  → 150 images → ood_script  (Cyrl — 0 existing)
  - multi_lan_ocr/Arabic   → 100 images → ood_script  (Arab — 6 existing)
  - multi_lan_ocr/Japanese →  50 images → ood_script  (Jpan — 15 existing)
  - multi_scene_ocr/document_text → 100 images → ood_domain

Total target: ~550 new registrations (subject to dedup).

Dataset: CC-OCR (Comprehensive Multilingual OCR Benchmark)
Source: Hugging Face hub (Yuliang-Liu/cc-ocr), MIT license
Local path: /mnt/e/image_detection/01_base_data/language/huggingface_downloads/CC-OCR/

Usage:
    # Dry run
    python scripts/harvest_ood_cc_ocr.py --dry-run

    # Register up to 550 images
    python scripts/harvest_ood_cc_ocr.py
"""

from __future__ import annotations

import random
import shutil
import sys
from pathlib import Path

import click

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.ood_utils import (
    append_registry_entry,
    build_ground_truth_template,
    compute_phash,
    compute_sha256,
    is_duplicate,
    load_ood_registry,
    log_dry_run_summary,
)

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────

_CC_OCR_BASE = Path(
    "/mnt/e/image_detection/01_base_data/language/huggingface_downloads/CC-OCR/extracted_images"
)
_OOD_BASE = Path("/mnt/e/image_detection/ood")
_REGISTRY_DEFAULT = Path("metadata_registry/ood_registry.jsonl")

# ISO 15924 script tag for each language in multi_lan_ocr
_LANG_TO_SCRIPT: dict[str, str] = {
    "Arabic": "Arab",
    "French": "Latn",
    "German": "Latn",
    "Italian": "Latn",
    "Japanese": "Jpan",
    "Korean": "Hang",
    "Portuguese": "Latn",
    "Russian": "Cyrl",
    "Spanish": "Latn",
    "Vietnamese": "Latn",
}

# How many images to register per language (focus on underrepresented scripts)
_LANG_TARGETS: dict[str, int] = {
    "Korean": 150,  # Hang: 0 existing → fill completely
    "Russian": 150,  # Cyrl: 0 existing → fill completely
    "Arabic": 100,  # Arab: 6 existing → bring to ~106
    "Japanese": 50,  # Jpan: 15 existing → bring to ~65
    # Latn languages skipped — well covered by other sources
}

_LICENSE = "MIT"
_DATE = "2026-02-25"


def _register_batch(
    candidates: list[Path],
    output_dir: Path,
    target_count: int,
    sha_set: set[str],
    phash_list: list[str],
    dry_run: bool,
    registry_path: Path,
    make_entry_fn,  # callable(img_path, out_path, sha256, phash, idx) -> dict
    counters: dict,
) -> int:
    """Copy and register up to target_count images from candidates list.

    Returns the number of images registered.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    registered = 0

    for img_path in candidates:
        if registered >= target_count:
            break

        counters["evaluated"] += 1

        sha256 = compute_sha256(img_path)
        phash_hex = compute_phash(img_path)

        if is_duplicate(sha256, phash_hex, sha_set, phash_list):
            counters["dupl"] += 1
            continue

        idx = counters["total_registered"]
        out_name = f"ccr_{counters['prefix']}_{idx:04d}.jpg"
        out_path = output_dir / out_name

        if not dry_run:
            if img_path.suffix.lower() in (".jpg", ".jpeg"):
                shutil.copy2(img_path, out_path)
            else:
                from PIL import Image

                with Image.open(img_path) as im:
                    im.convert("RGB").save(out_path, format="JPEG", quality=90)
            # Recompute SHA of the written file
            sha256 = compute_sha256(out_path)
            phash_hex = compute_phash(out_path)

        entry = make_entry_fn(
            img_path, out_path if not dry_run else img_path, sha256, phash_hex
        )

        if not dry_run:
            append_registry_entry(entry, registry_path)
            sha_set.add(sha256)
            phash_list.append(phash_hex)

        counters["registered"] += 1
        counters["total_registered"] += 1
        registered += 1

    return registered


@click.command()
@click.option(
    "--registry",
    type=click.Path(path_type=Path),
    default=_REGISTRY_DEFAULT,
    show_default=True,
)
@click.option("--dry-run", is_flag=True, help="Print stats only, do not write")
@click.option("--seed", type=int, default=42, help="RNG seed for candidate ordering")
def main(registry: Path, dry_run: bool, seed: int) -> None:
    """Register CC-OCR benchmark images into the OOD registry."""
    if not _CC_OCR_BASE.exists():
        click.echo(f"ERROR: CC-OCR base not found: {_CC_OCR_BASE}", err=True)
        sys.exit(1)

    rng = random.Random(seed)
    sha_set, phash_list = load_ood_registry(registry)
    click.echo(f"Registry: {len(sha_set):,} existing entries")
    click.echo(f"Source: {_CC_OCR_BASE}")
    click.echo()

    counters: dict = {
        "evaluated": 0,
        "dupl": 0,
        "registered": 0,
        "total_registered": 0,
        "prefix": "kor",  # reset per batch
    }

    # ── 1. Register multi_lan_ocr languages ──────────────────────────────────
    for lang, target in _LANG_TARGETS.items():
        script = _LANG_TO_SCRIPT[lang]
        lang_dir = _CC_OCR_BASE / "multi_lan_ocr" / lang

        if not lang_dir.exists():
            click.echo(f"  {lang}: directory not found, skipping")
            continue

        candidates = sorted(
            f
            for f in lang_dir.rglob("*")
            if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png")
        )
        rng.shuffle(candidates)

        prefix = lang[:3].lower()
        counters["prefix"] = prefix

        output_dir = _OOD_BASE / "ood_script"

        def _make_script_entry(
            img_path: Path,
            out_path: Path,
            sha256: str,
            phash: str,
            _lang: str = lang,
            _script: str = script,
        ) -> dict:
            gt = build_ground_truth_template()
            gt["script"] = _script
            gt["open_set"] = False
            gt["capture_method"] = "camera_smartphone"
            gt["handwriting_presence"] = False
            gt["handwriting_presence_score"] = 0.0
            return {
                "sha256": sha256,
                "phash": phash,
                "source_path": str(out_path),
                "ood_categories": ["ood_script"],
                "reason": (
                    f"CC-OCR multi_lan_ocr/{_lang}: {img_path.name} — "
                    f"real OCR benchmark image; tests script_cls head ({_script})"
                ),
                "registered_date": _DATE,
                "acquisition_method": "local_dataset_copy",
                "license": _LICENSE,
                "dedup_verified": True,
                "evaluation_pipeline_stage": ["siglip2"],
                "needs_human_review": False,
                "ground_truth": gt,
                "generation_metadata": {
                    "source_dataset": "cc-ocr",
                    "track": "multi_lan_ocr",
                    "language": _lang,
                    "split_used": "test",
                    "original_path": str(img_path),
                },
                "enrichment": {
                    "domain_level1": "EDU",
                    "domain_source": "cc_ocr_multilingual_benchmark",
                    "domain_confidence": 0.8,
                },
            }

        before = counters["registered"]
        _register_batch(
            candidates,
            output_dir,
            target,
            sha_set,
            phash_list,
            dry_run,
            registry,
            _make_script_entry,
            counters,
        )
        after = counters["registered"]
        click.echo(f"  {lang:10s} ({script}): registered {after - before}")

    # ── 2. Register multi_scene_ocr/document_text → ood_domain ───────────────
    doc_dir = _CC_OCR_BASE / "multi_scene_ocr" / "document_text"
    if doc_dir.exists():
        counters["prefix"] = "doc"
        candidates = sorted(
            f
            for f in doc_dir.rglob("*")
            if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png")
        )
        rng.shuffle(candidates)
        output_dir = _OOD_BASE / "ood_domain"

        def _make_domain_entry(
            img_path: Path, out_path: Path, sha256: str, phash: str
        ) -> dict:
            gt = build_ground_truth_template()
            gt["capture_method"] = "camera_smartphone"
            gt["handwriting_presence"] = False
            gt["handwriting_presence_score"] = 0.0
            return {
                "sha256": sha256,
                "phash": phash,
                "source_path": str(out_path),
                "ood_categories": ["ood_domain"],
                "reason": (
                    f"CC-OCR multi_scene_ocr/document_text: {img_path.name} — "
                    "real-world document camera capture; tests capture_method + domain heads"
                ),
                "registered_date": _DATE,
                "acquisition_method": "local_dataset_copy",
                "license": _LICENSE,
                "dedup_verified": True,
                "evaluation_pipeline_stage": ["mobilenetv4", "siglip2"],
                "needs_human_review": False,
                "ground_truth": gt,
                "generation_metadata": {
                    "source_dataset": "cc-ocr",
                    "track": "multi_scene_ocr",
                    "sub_track": "document_text",
                    "split_used": "test",
                    "original_path": str(img_path),
                },
                "enrichment": {
                    "domain_level1": "UNK",
                    "domain_source": "cc_ocr_document_text_mixed",
                    "domain_confidence": 0.0,
                },
            }

        before = counters["registered"]
        _register_batch(
            candidates,
            output_dir,
            100,
            sha_set,
            phash_list,
            dry_run,
            registry,
            _make_domain_entry,
            counters,
        )
        after = counters["registered"]
        click.echo(f"  document_text (ood_domain): registered {after - before}")
    else:
        click.echo(f"  document_text directory not found: {doc_dir}")

    click.echo()
    log_dry_run_summary(
        sub_command="harvest-ood-cc-ocr",
        candidates=counters["evaluated"],
        duplicates_training=0,
        duplicates_intra=counters["dupl"],
        unique=counters["registered"],
        dry_run=dry_run,
    )


if __name__ == "__main__":
    main()
