#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Enrich OOD registry records with domain_level1 labels.

Domain taxonomy (10 classes):
  SCI  – Scientific / academic papers, preprints, research
  FIN  – Financial: reports, invoices, receipts, budgets
  GOV  – Government: ID docs, tenders, regulations, forms, certificates
  EDU  – Educational / linguistic: handwriting corpora, scripts, textbooks
  TEC  – Technical: code screenshots, terminals, patents, manuals
  LGL  – Legal: laws, regulations, contracts (non-government origin)
  MED  – Medical / clinical
  REL  – Religious / cultural texts
  SCN  – Natural-scene text (street signs, store fronts)
  UNK  – Cannot be determined without visual inspection

Usage
-----
    # Dry run (prints stats, no file changes)
    python scripts/enrich_ood_domain.py --dry-run

    # Enrich the registry in-place
    python scripts/enrich_ood_domain.py

    # Generate contact sheets for UNK groups (for human review)
    python scripts/enrich_ood_domain.py --contact-sheets --output-dir /tmp/ood_domain_review

    # Full pipeline: enrich + contact sheets
    python scripts/enrich_ood_domain.py --contact-sheets --output-dir /tmp/ood_domain_review
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

# ──────────────────────────────────────────────
# Domain taxonomy
# ──────────────────────────────────────────────

DOMAINS: tuple[str, ...] = (
    "SCI",
    "FIN",
    "GOV",
    "EDU",
    "TEC",
    "LGL",
    "MED",
    "REL",
    "SCN",
    "UNK",
)

# DocLayNet doc_category → domain
DOCLAYNET_DOMAIN_MAP: dict[str, str] = {
    "financial_reports": "FIN",
    "scientific_articles": "SCI",
    "laws_and_regulations": "LGL",
    "laws_regulations": "LGL",  # alias
    "patents": "TEC",
    "government_tenders": "GOV",
    "manuals": "TEC",
}

# RVL-CDIP class → domain (16 classes)
RVL_CDIP_DOMAIN_MAP: dict[str, str] = {
    "advertisement": "FIN",  # Visual review: tobacco-industry corporate records (invoices, memos)
    "budget": "FIN",
    "email": "UNK",
    "file_folder": "UNK",
    "form": "GOV",
    "handwritten": "EDU",
    "invoice": "FIN",
    "letter": "UNK",
    "memo": "UNK",
    "news": "UNK",
    "note": "EDU",
    "report": "UNK",
    "resume": "UNK",
    "scientific_publication": "SCI",
    "scientific_report": "SCI",
    "specification": "TEC",
}

# source_dataset → domain (for local_dataset_* methods)
SOURCE_DATASET_DOMAIN_MAP: dict[str, str] = {
    # Geometry distortion sources
    "warpdoc": "SCI",  # Academic paper warp/distortion dataset
    "docalign12k": "SCI",  # Document alignment academic papers
    # Shadow / capture sources
    "sd7k": "UNK",  # Real-world shadow on documents (mixed types)
    "wsrd": "UNK",  # Watermark/shadow removal (mixed)
    "realdae": "UNK",  # Real-world degradation (mixed)
    # Handwriting
    "hiertext": "SCN",  # Natural scene text (street level)
    "casia-hwdb2-line": "EDU",
    "iiit-indic": "EDU",
    "khatt": "EDU",
    "muharaf": "EDU",
    "casia-hwdb2": "EDU",
    "nist-sd19": "EDU",
    # Multilingual
    "mlt19": "EDU",
    "mdiw13": "EDU",
    # ID documents
    "midv500": "GOV",
    "midv2020": "GOV",
    # Benchmark
    "ohr-bench": "EDU",
    "ohr_bench": "EDU",
}

# Reason-prefix string → domain (for local_dataset_copy without gen_meta)
REASON_PREFIX_DOMAIN_MAP: dict[str, str] = {
    "5c IIIT-INDIC": "EDU",
    "5a KHATT": "EDU",
    "5a Muharaf": "EDU",
    "5b CASIA-HWDB2": "EDU",
    "3d RVL-CDIP": "GOV",  # test split scanner (business docs)
    "3b docalign12k": "SCI",
    "2b WarpDoc": "SCI",
    "2b docalign12k": "SCI",
    "4c RealDAE": "UNK",
    "3b WarpDoc": "SCI",
}

# ──────────────────────────────────────────────
# Per-acquisition-method domain rules
# ──────────────────────────────────────────────

# Acquisition methods with fixed domain (no metadata lookup needed)
FIXED_DOMAIN_BY_METHOD: dict[str, str] = {
    "arxiv_pdf_render": "SCI",
    "arxiv_pdf_code_page": "SCI",
    "playwright_code_python": "TEC",
    "playwright_code_javascript": "TEC",
    "playwright_code_rust": "TEC",
    "playwright_code_go": "TEC",
    "playwright_code_sql": "TEC",
    "terminal_pil_render": "TEC",
    "synthetic_pillow_render": "EDU",  # Font variation renders for script study
    "midv_frame_midv500": "GOV",  # ID documents
    "tobacco800_direct": "GOV",  # Historical business/tobacco docs
    "synthetic_albumentations": "GOV",  # Blank form template
    "opencv_sauvola_jpeg": "EDU",  # Arabic handwriting (Muharaf source)
    # DocSynth300K sourced — no category metadata available
    "augraphy_photocopy_4x": "UNK",
    # Note: augraphy_pipeline handled in step 10 via RVL class lookup (not fixed)
}


def _build_doclaynet_sha_map() -> dict[str, str]:
    """Build SHA256-stem → doc_category from all DocLayNet COCO splits."""
    coco_base = Path(
        "/mnt/e/image_detection/01_base_data/documents/doclaynet/ground_truth/coco"
    )
    sha_to_cat: dict[str, str] = {}
    for split in ("train", "val", "test"):
        coco_path = coco_base / f"{split}.json"
        if not coco_path.exists():
            continue
        with coco_path.open() as fh:
            coco = json.load(fh)
        for img in coco["images"]:
            sha = img["file_name"].replace(".png", "")
            sha_to_cat[sha] = img["doc_category"]
    return sha_to_cat


def _extract_doclaynet_sha(source_image: str) -> str:
    """Extract the SHA256 stem from a DocLayNet source_image path."""
    return Path(source_image).stem


def _rvl_class_from_path(path: str) -> str:
    """Extract RVL-CDIP class from a filename like 'rvl_advertisement_0047.jpg'."""
    fname = Path(path).name
    if fname.startswith("rvl_"):
        parts = fname.split("_")
        if len(parts) >= 2:
            return parts[1]
    return ""


def _reason_prefix_domain(reason: str) -> str | None:
    """Look up domain from reason string prefix."""
    for prefix, domain in REASON_PREFIX_DOMAIN_MAP.items():
        if reason.startswith(prefix):
            return domain
    return None


def _infer_domain(
    record: dict,
    sha_map: dict[str, str],
) -> tuple[str, str, float]:
    """Infer domain for a single OOD registry record.

    Returns
    -------
    (domain, source_description, confidence)
        domain: one of DOMAINS
        source_description: how the domain was determined
        confidence: 0.0–1.0 (1.0 = certain, 0.5 = educated guess, 0.0 = UNK)
    """
    method = record.get("acquisition_method", "")
    gm = record.get("generation_metadata", {})
    reason = record.get("reason", "")
    source_path = record.get("source_path", "")

    # ── 1. Fixed-method lookup ──────────────────────────────────────────────
    if method in FIXED_DOMAIN_BY_METHOD:
        dom = FIXED_DOMAIN_BY_METHOD[method]
        conf = 0.9 if dom != "UNK" else 0.0
        return dom, f"fixed_method:{method}", conf

    # ── 2. synthetic_generation — route by generator_script ────────────────
    if method == "synthetic_generation":
        gen_script = gm.get("generator_script", "")

        # Code screenshots from this project's own scripts → TEC
        if gen_script == "generate_ood_code_screenshots.py":
            return "TEC", "code_screenshot_generator", 0.95

        # Screen recapture or compound distortion — DocLayNet source_image lookup
        src_img = gm.get("source_image", "")
        if src_img:
            sha = _extract_doclaynet_sha(src_img)
            dl_cat = sha_map.get(sha)
            if dl_cat:
                dom = DOCLAYNET_DOMAIN_MAP.get(dl_cat, "UNK")
                return dom, f"doclaynet_coco:{dl_cat}", 0.95
        return "UNK", "synthetic_generation_no_sha_match", 0.0

    # ── 3. albumentations_compound — DocSynth300K source, no category ──────
    if method == "albumentations_compound":
        # source_image points to docsynth300k — no category metadata available
        src_img = gm.get("source_image", "")
        if "docsynth300k" in src_img:
            return "UNK", "docsynth300k_no_category", 0.0
        # Fallback: try DocLayNet SHA lookup
        if src_img:
            sha = _extract_doclaynet_sha(src_img)
            dl_cat = sha_map.get(sha)
            if dl_cat:
                dom = DOCLAYNET_DOMAIN_MAP.get(dl_cat, "UNK")
                return dom, f"doclaynet_coco:{dl_cat}", 0.95
        return "UNK", "albumentations_compound_no_source", 0.0

    # ── 3. DocLayNet local PDF (doclaynet_local_pdf_*) ─────────────────────
    if method.startswith("doclaynet_local_pdf"):
        stem = gm.get("doclaynet_stem", "")
        if stem:
            dl_cat = sha_map.get(stem)
            if dl_cat:
                dom = DOCLAYNET_DOMAIN_MAP.get(dl_cat, "UNK")
                return dom, f"doclaynet_coco:{dl_cat}", 0.95
        return "UNK", "doclaynet_local_pdf_no_match", 0.0

    # ── 4. Watermark / binarization (DocSynth300K source) ──────────────────
    if method in ("pil_watermark", "sauvola_binarize", "opencv_sauvola_jpeg"):
        src_img = gm.get("source_image", "")
        if "docsynth300k" in src_img:
            return "UNK", "docsynth300k_no_category", 0.0
        # muharaf is the source for some sauvola records
        if "muharaf" in src_img:
            return "EDU", "muharaf_handwriting", 0.8
        return "UNK", "watermark_binarize_unknown_source", 0.0

    # ── 5. Synthetic composite shadow (trace via source_compound) ───────────
    if method == "synthetic_composite_shadow":
        # source_compound points to a 4a_compound image (DocLayNet-derived)
        # We can't easily trace the sha without a second lookup pass
        return "UNK", "composite_shadow_chain_not_resolved", 0.0

    # ── 6. local_dataset_full_pool ──────────────────────────────────────────
    if method == "local_dataset_full_pool":
        src_ds = gm.get("source_dataset", "").lower()
        dom = SOURCE_DATASET_DOMAIN_MAP.get(src_ds)
        if dom:
            conf = 0.0 if dom == "UNK" else 0.85
            return dom, f"source_dataset:{src_ds}", conf
        # Fallback: try to infer from source_path/reason
        for key, val in SOURCE_DATASET_DOMAIN_MAP.items():
            if key in source_path.lower() or key in reason.lower():
                conf = 0.0 if val == "UNK" else 0.75
                return val, f"path_contains:{key}", conf
        return "UNK", "local_full_pool_unknown", 0.0

    # ── 7. local_dataset_train_split ────────────────────────────────────────
    if method == "local_dataset_train_split":
        src_ds = gm.get("source_dataset", "").lower()
        dom = SOURCE_DATASET_DOMAIN_MAP.get(src_ds)
        if dom:
            conf = 0.0 if dom == "UNK" else 0.85
            return dom, f"source_dataset:{src_ds}", conf
        return "UNK", "local_train_split_unknown", 0.0

    # ── 8. local_dataset_copy ───────────────────────────────────────────────
    if method == "local_dataset_copy":
        # Try gen_meta source_dataset first
        src_ds = gm.get("source_dataset", "").lower()
        if src_ds:
            dom = SOURCE_DATASET_DOMAIN_MAP.get(src_ds)
            if dom:
                conf = 0.0 if dom == "UNK" else 0.85
                return dom, f"source_dataset:{src_ds}", conf
        # Fallback: reason prefix
        dom = _reason_prefix_domain(reason)
        if dom:
            conf = 0.0 if dom == "UNK" else 0.8
            return dom, f"reason_prefix:{reason[:30]}", conf
        # Fallback: path-based dataset detection
        for key, val in SOURCE_DATASET_DOMAIN_MAP.items():
            if key.replace("-", "_") in source_path.replace("-", "_").lower():
                conf = 0.0 if val == "UNK" else 0.7
                return val, f"path_contains:{key}", conf
        return "UNK", "local_copy_unknown", 0.0

    # ── 9. OHR-Bench ───────────────────────────────────────────────────────
    if method.startswith("ohr_bench"):
        return "EDU", "ohr_bench_academic_benchmark", 0.8

    # ── 10. Augraphy RVL-CDIP ──────────────────────────────────────────────
    if method == "augraphy_pipeline":
        src = gm.get("source", "")
        rvl_cls = _rvl_class_from_path(src)
        if rvl_cls:
            dom = RVL_CDIP_DOMAIN_MAP.get(rvl_cls, "UNK")
            conf = 0.0 if dom == "UNK" else 0.8
            return dom, f"rvl_cdip_class:{rvl_cls}", conf
        return "UNK", "augraphy_rvl_no_class", 0.0

    # ── Default ─────────────────────────────────────────────────────────────
    return "UNK", f"no_rule_for_method:{method}", 0.0


def _generate_contact_sheets(
    unk_records: list[dict],
    output_dir: Path,
    images_per_sheet: int = 16,
    cols: int = 4,
    seed: int = 42,
) -> list[Path]:
    """Generate contact sheets for UNK records grouped by acquisition method.

    Args:
        unk_records: Records with domain_level1 == 'UNK'.
        output_dir: Directory where contact sheets will be saved.
        images_per_sheet: Images per contact sheet (power of cols recommended).
        cols: Columns per sheet.
        seed: Random seed for sampling.

    Returns:
        List of generated sheet paths.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
    from image_preprocessing_detector.labeling.handwriting.contact_sheet import (
        create_hw_contact_sheet,
    )

    rng = random.Random(seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    sheet_paths: list[Path] = []

    # Group by acquisition method
    by_method: dict[str, list[dict]] = defaultdict(list)
    for rec in unk_records:
        by_method[rec.get("acquisition_method", "unknown")].append(rec)

    for method, recs in sorted(by_method.items()):
        # Sample up to 2x images_per_sheet for review (first sheet = random sample)
        sample_size = min(len(recs), images_per_sheet * 2)
        sampled = rng.sample(recs, sample_size)

        # Split into sheets
        for sheet_idx, start in enumerate(range(0, len(sampled), images_per_sheet)):
            batch = sampled[start : start + images_per_sheet]
            img_paths = [Path(r["source_path"]) for r in batch]

            # Filter to existing paths
            existing = [p for p in img_paths if p.exists()]
            if not existing:
                continue

            sheet_name = f"{method}_sheet_{sheet_idx:02d}.jpg"
            sheet_path = output_dir / sheet_name
            try:
                create_hw_contact_sheet(
                    existing,
                    sheet_path,
                    cols=cols,
                    cell_width_px=384,
                    jpeg_quality=80,
                    label_font_size=18,
                )
                sheet_paths.append(sheet_path)
                print(f"  Created: {sheet_path.name}  ({len(existing)} images)")
            except Exception as exc:
                print(f"  WARNING: Failed to create {sheet_name}: {exc}")

    return sheet_paths


def _generate_review_csv(records: list[dict], output_path: Path) -> None:
    """Write a CSV of UNK records for manual domain annotation."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as fh:
        fh.write(
            "sha256,source_path,acquisition_method,reason,current_domain,domain_source,confidence,annotated_domain\n"
        )
        for rec in records:
            enr = rec.get("enrichment", {})
            sha = rec.get("sha256", "")[:16]
            sp = rec.get("source_path", "")
            meth = rec.get("acquisition_method", "")
            reason = rec.get("reason", "").replace(",", ";")[:80]
            dom = enr.get("domain_level1", "UNK")
            src = enr.get("domain_source", "")
            conf = enr.get("domain_confidence", 0.0)
            fh.write(f"{sha},{sp},{meth},{reason},{dom},{src},{conf:.2f},\n")


def main() -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Enrich OOD registry with domain labels."
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("metadata_registry/ood_registry.jsonl"),
        help="Path to OOD registry JSONL",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print stats only, do not write"
    )
    parser.add_argument(
        "--contact-sheets",
        action="store_true",
        help="Generate contact sheets for UNK records",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/tmp/ood_domain_review"),
        help="Directory for contact sheets and review CSV",
    )
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for sampling")
    args = parser.parse_args()

    registry_path = args.registry
    if not registry_path.exists():
        print(f"ERROR: Registry not found: {registry_path}", file=sys.stderr)
        return 1

    # Build DocLayNet SHA → category mapping
    print("Building DocLayNet SHA → category map...")
    sha_map = _build_doclaynet_sha_map()
    print(f"  Loaded {len(sha_map):,} DocLayNet image entries")

    # Load registry
    print(f"Loading registry from {registry_path}...")
    records: list[dict] = []
    with registry_path.open() as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    print(f"  {len(records):,} records loaded")

    # Infer domains
    print("Inferring domains...")
    domain_counter: Counter[str] = Counter()
    source_counter: Counter[str] = Counter()
    updated_records: list[dict] = []

    for rec in records:
        domain, source_desc, confidence = _infer_domain(rec, sha_map)
        domain_counter[domain] += 1
        source_counter[source_desc.split(":")[0]] += 1

        # Add/update enrichment field
        enrichment = rec.setdefault("enrichment", {})
        enrichment["domain_level1"] = domain
        enrichment["domain_source"] = source_desc
        enrichment["domain_confidence"] = round(confidence, 3)
        updated_records.append(rec)

    # Print statistics
    print("\n── Domain Distribution ──────────────────────────────")
    total = len(records)
    for dom in DOMAINS:
        count = domain_counter.get(dom, 0)
        pct = count / total * 100
        bar = "█" * (count // 50)
        print(f"  {dom:5s}  {count:6d}  ({pct:5.1f}%)  {bar}")

    print("\n── Inference Source Distribution ───────────────────")
    for src, cnt in source_counter.most_common(15):
        print(f"  {cnt:6d}  {src}")

    unk_records = [
        r for r in updated_records if r["enrichment"]["domain_level1"] == "UNK"
    ]
    print(f"\nTotal UNK: {len(unk_records)} ({len(unk_records) / total * 100:.1f}%)")

    # ── UNK breakdown by method ──────────────────────────────────────────
    unk_by_method: Counter[str] = Counter(
        r.get("acquisition_method", "") for r in unk_records
    )
    print("\n── UNK by Acquisition Method ────────────────────────")
    for meth, cnt in unk_by_method.most_common():
        print(f"  {cnt:6d}  {meth}")

    if args.dry_run:
        print("\nDry run — no files written.")
        return 0

    # Write enriched registry
    print(f"\nWriting enriched registry to {registry_path}...")
    tmp_path = registry_path.with_suffix(".jsonl.tmp")
    with tmp_path.open("w") as fh:
        for rec in updated_records:
            fh.write(json.dumps(rec, separators=(",", ":")) + "\n")
    tmp_path.replace(registry_path)
    print(f"  Wrote {len(updated_records):,} records")

    # Generate contact sheets
    if args.contact_sheets:
        print(f"\nGenerating contact sheets for {len(unk_records)} UNK records...")
        print(f"  Output dir: {args.output_dir}")
        sheet_paths = _generate_contact_sheets(
            unk_records, args.output_dir, seed=args.seed
        )
        print(f"  Generated {len(sheet_paths)} contact sheets")

        # Write review CSV for all UNK records
        csv_path = args.output_dir / "unk_domain_review.csv"
        _generate_review_csv(unk_records, csv_path)
        print(f"  Review CSV: {csv_path}")

        # Also write summary JSON
        summary = {
            "total_records": total,
            "domain_distribution": dict(domain_counter),
            "unk_count": len(unk_records),
            "unk_by_method": dict(unk_by_method),
            "contact_sheets": [str(p) for p in sheet_paths],
        }
        summary_path = args.output_dir / "enrichment_summary.json"
        with summary_path.open("w") as fh:
            json.dump(summary, fh, indent=2)
        print(f"  Summary JSON: {summary_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
