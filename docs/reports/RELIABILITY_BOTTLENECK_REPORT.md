# Reliability Bottleneck Report

> Generated: 2026-02-09 18:28 | Datasets: 47 | Samples: 1,937,501
>
> Source: `scripts/materialize_reliability_summary.py --all --force --update-docs`
>
> Metadata: `/mnt/e/image_detection/metadata_registry/json/*_metadata.json`

## Executive Summary

Across **47 datasets** and **1,937,501 samples**, the per-sample
`min_confidence` reliability metric produces the following category distribution:

| Category | Threshold | Samples | % |
|---|---|---:|---:|
| Hard label | >= 0.9 | 4 | 0.0% |
| Soft label | >= 0.7 | 5,649 | 0.3% |
| Active learning | >= 0.5 | 16,417 | 0.8% |
| Unreliable | < 0.5 | 1,917,493 | 99.0% |
| **Total** | | **1,937,501** | **100%** |

The 99% unreliable rate is **expected** -- most datasets were scanned with
Tier 3 fallback (`--no-yolo`), leaving fields like `layout_detections`,
`has_table`, `text_quality`, and `language` at 0.0 confidence. The
`min_confidence` metric correctly surfaces these gaps.

## Bottleneck Field Summary

Fields most frequently responsible for dragging `min_confidence` below threshold:

| Field | Datasets (top bottleneck) | Total Bottleneck Samples |
|---|---:|---:|
| `text_quality` | 13 | 823,258 |
| `layout_detections` | 9 | 666,213 |
| `has_table` | 6 | 156,500 |
| `language` | 10 | 130,649 |
| `domain` | 5 | 99,821 |
| `has_formula` | 1 | 54,120 |
| `capture_method` | 3 | 9,002 |

### Remediation Priority

| Field | Fix | Impact |
|---|---|---|
| `text_quality` | Run Docling OCR or map GT text sources | 13 datasets, ~636K samples |
| `language` | Run OpenLID-v2 language detection backfill | 10 datasets, ~129K samples |
| `layout_detections` | Run DocLayout-YOLO inference (remove `--no-yolo`) | 9 datasets, ~665K samples |
| `has_table` / `has_formula` | Derived from layout detections; resolves with YOLO pass | 7 datasets |
| `domain` | Improve domain classification heuristic or add manual labels | 5 datasets |
| `capture_method` | Add capture method annotations to dataset configs | 3 datasets |

## Datasets with Enriched Labels

Only 6 datasets have samples above the unreliable threshold:

| Dataset | Usable | Total | % Usable | Avg Conf | Top Bottleneck |
|---|---:|---:|---:|---:|---|
| rvl_cdip | 10,175 | 16,000 | 63.6% | 0.53 | `layout_detections` |
| nist-sd2 | 4,924 | 5,590 | 88.1% | 0.59 | `layout_detections` |
| nist_sd6 | 4,751 | 5,595 | 84.9% | 0.57 | `layout_detections` |
| invoices-kg | 1,414 | 1,414 | 100.0% | 0.76 | `layout_detections` |
| funsd_plus | 780 | 1,139 | 68.5% | 0.55 | `layout_detections` |
| funsd | 26 | 199 | 13.1% | 0.35 | `language` |

## Full Dataset Table

| Dataset | Total | Hard | Soft | Active | Unreliable | Avg Conf | Top Bottleneck | % | 2nd Bottleneck | % |
|---|---:|---:|---:|---:|---:|---:|---|---:|---|---:|
| arabic_docs_ocr | 8,203 | 0 | 0 | 0 | 8,203 | 0.28 | `domain` | 90.2 | `layout_detections` | 9.8 |
| bhutan_financial | 135 | 0 | 0 | 0 | 135 | 0.00 | `language` | 100.0 | `-` | 0.0 |
| cc_ocr | 6,284 | 0 | 0 | 0 | 6,284 | 0.00 | `has_table` | 100.0 | `-` | 0.0 |
| cvsi | 10,715 | 0 | 0 | 0 | 10,715 | 0.00 | `text_quality` | 100.0 | `-` | 0.0 |
| dibco | 212 | 0 | 0 | 0 | 212 | 0.00 | `language` | 100.0 | `-` | 0.0 |
| diqa-5000 | 5,500 | 0 | 0 | 0 | 5,500 | 0.29 | `domain` | 91.7 | `layout_detections` | 4.7 |
| doclaynet | 81,471 | 0 | 0 | 0 | 81,471 | 0.25 | `domain` | 84.8 | `has_table` | 15.2 |
| dzongkha-digits | 0 | 0 | 0 | 0 | 62 | 0.00 | `capture_method` | 100.0 | `-` | 0.0 |
| financebench | 54,120 | 0 | 0 | 0 | 54,120 | 0.00 | `has_formula` | 100.0 | `-` | 0.0 |
| fintabnet | 97,475 | 0 | 0 | 0 | 97,475 | 0.00 | `layout_detections` | 100.0 | `-` | 0.0 |
| funsd | 199 | 4 | 11 | 11 | 173 | 0.35 | `language` | 98.0 | `domain` | 2.0 |
| funsd_plus | 1,139 | 0 | 77 | 703 | 359 | 0.55 | `layout_detections` | 98.5 | `has_table` | 1.5 |
| hasyv2 | 168,233 | 0 | 0 | 0 | 168,233 | 0.00 | `text_quality` | 100.0 | `-` | 0.0 |
| hiertext | 11,639 | 0 | 0 | 0 | 11,639 | 0.00 | `language` | 100.0 | `-` | 0.0 |
| hindi_ocr_synthetic | 80,008 | 0 | 0 | 0 | 80,008 | 0.00 | `has_table` | 100.0 | `-` | 0.0 |
| historical_degraded | 1,356 | 0 | 0 | 0 | 1,356 | 0.00 | `language` | 100.0 | `-` | 0.0 |
| im2latex | 10,000 | 0 | 0 | 0 | 10,000 | 0.00 | `layout_detections` | 100.0 | `-` | 0.0 |
| invoices-kg | 1,414 | 0 | 1,376 | 38 | 0 | 0.76 | `layout_detections` | 99.9 | `has_table` | 0.1 |
| jssoda | 0 | 0 | 0 | 0 | 2,000 | 0.00 | `capture_method` | 100.0 | `-` | 0.0 |
| maths_handwriting | 15,000 | 0 | 0 | 0 | 15,000 | 0.00 | `text_quality` | 100.0 | `-` | 0.0 |
| mathverse | 6,940 | 0 | 0 | 0 | 6,940 | 0.00 | `capture_method` | 100.0 | `-` | 0.0 |
| mdiw13 | 290,213 | 0 | 0 | 0 | 290,213 | 0.00 | `text_quality` | 63.6 | `language` | 36.4 |
| midv500 | 15,050 | 0 | 0 | 0 | 15,050 | 0.00 | `has_table` | 100.0 | `-` | 0.0 |
| mle2e | 1,816 | 0 | 0 | 0 | 1,816 | 0.00 | `has_table` | 100.0 | `-` | 0.0 |
| mlt19 | 19,657 | 0 | 0 | 0 | 19,657 | 0.26 | `domain` | 79.6 | `layout_detections` | 20.4 |
| muharaf | 25,711 | 0 | 0 | 0 | 25,711 | 0.00 | `has_table` | 100.0 | `-` | 0.0 |
| multilingual_scripts | 3,279 | 0 | 0 | 0 | 3,279 | 0.00 | `text_quality` | 100.0 | `-` | 0.0 |
| multimodal_textbook | 1,113 | 0 | 0 | 0 | 1,113 | 0.00 | `language` | 100.0 | `-` | 0.0 |
| nepali_handwritten | 958 | 0 | 0 | 0 | 958 | 0.00 | `text_quality` | 100.0 | `-` | 0.0 |
| nist-sd2 | 5,590 | 0 | 512 | 4,412 | 666 | 0.59 | `layout_detections` | 98.4 | `has_table` | 1.6 |
| nist_sd19 | 3,669 | 0 | 0 | 0 | 3,669 | 0.00 | `text_quality` | 100.0 | `-` | 0.0 |
| nist_sd6 | 5,595 | 0 | 399 | 4,352 | 844 | 0.57 | `layout_detections` | 99.5 | `text_quality` | 0.5 |
| ocr_quality | 1,000 | 0 | 0 | 0 | 1,000 | 0.00 | `language` | 100.0 | `-` | 0.0 |
| ohr-bench | 8,303 | 0 | 0 | 0 | 8,303 | 0.00 | `language` | 100.0 | `-` | 0.0 |
| omnidocbench | 377 | 0 | 0 | 0 | 377 | 0.00 | `language` | 76.7 | `has_table` | 23.3 |
| pubtabnet | 519,030 | 0 | 0 | 0 | 519,030 | 0.00 | `layout_detections` | 100.0 | `-` | 0.0 |
| pucit_ohul | 7,401 | 0 | 0 | 0 | 7,401 | 0.00 | `layout_detections` | 100.0 | `-` | 0.0 |
| realdae | 583 | 0 | 0 | 0 | 583 | 0.00 | `text_quality` | 100.0 | `-` | 0.0 |
| rvl_cdip | 16,000 | 0 | 3,274 | 6,901 | 5,825 | 0.53 | `layout_detections` | 74.2 | `text_quality` | 25.8 |
| signatr6k | 12,514 | 0 | 0 | 0 | 12,514 | 0.00 | `text_quality` | 100.0 | `-` | 0.0 |
| siw13 | 16,291 | 0 | 0 | 0 | 16,291 | 0.00 | `text_quality` | 100.0 | `-` | 0.0 |
| smartdoc-qa | 4,260 | 0 | 0 | 0 | 4,260 | 0.22 | `domain` | 61.6 | `layout_detections` | 38.4 |
| sroie | 973 | 0 | 0 | 0 | 973 | 0.38 | `language` | 84.9 | `layout_detections` | 15.1 |
| tablebank | 260,025 | 0 | 0 | 0 | 260,025 | 0.00 | `text_quality` | 100.0 | `-` | 0.0 |
| tibhcr | 141,698 | 0 | 0 | 0 | 141,698 | 0.00 | `text_quality` | 100.0 | `-` | 0.0 |
| tobacco800 | 1,290 | 0 | 0 | 0 | 1,290 | 0.00 | `text_quality` | 100.0 | `-` | 0.0 |
| yarmouk_ocr | 15,062 | 0 | 0 | 0 | 15,062 | 0.00 | `has_table` | 100.0 | `-` | 0.0 |

## Methodology

### Reliability Categories

Each sample computes `min_confidence` across 10 enrichment fields:
`capture_method`, `resolution`, `domain`, `language`, `text_quality`,
`has_table`, `has_formula`, `has_handwriting`, `layout_detections`,
`script_detection`.

| Category | min_confidence Range | Training Suitability |
|---|---|---|
| Hard label | >= 0.9 | Direct training with full weight |
| Soft label | >= 0.7 | Training with reduced weight or label smoothing |
| Active learning | >= 0.5 | Candidate for human review or active learning loop |
| Unreliable | < 0.5 | Exclude from training; needs enrichment |

### Bottleneck Identification

For each sample, the field with the lowest confidence is the bottleneck.
Dataset-level bottleneck percentages show what fraction of samples are
bottlenecked by each field.

### Scripts

| Script | Purpose |
|---|---|
| `scripts/materialize_reliability_summary.py` | Compute per-sample reliability and write to metadata JSON |
| `scripts/backfill_text_quality_confidence.py` | Backfill text_quality confidence from GT/OCR sources |
| `scripts/analyze_soft_labels.py` | Detailed per-field soft label analysis |
| `scripts/disk_manifest.py` | Reconcile images on disk vs metadata registry |
