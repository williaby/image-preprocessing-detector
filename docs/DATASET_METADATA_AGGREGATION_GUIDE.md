---
owner: docs-team
purpose: Guide for aggregating Layer 2 metadata statistics
schema_type: common
status: active
tags:
- datasets
- metadata
- aggregation
title: Dataset Metadata Aggregation Guide
---

> **Purpose**: Generate aggregate statistics from Layer 2 metadata for Quick Reference tables
> **Script**: [scripts/aggregate_layer2_metadata.py](../scripts/aggregate_layer2_metadata.py)
> **Input**: Layer 2 enrichment JSON files (`/mnt/e/image_detection/metadata_registry/json/`)
> **Output**: Aggregate statistics JSON files (`metadata_registry/aggregates/`)

---

## Overview

The aggregation script processes Layer 2 enrichment metadata to compute dataset-level statistics:

- **Capture Method Distributions**: % born-digital, scanner, camera, synthetic
- **Quality Score Ranges**: Min, max, mean, median, stdev
- **Degradation Type Frequencies**: Top degradations with prevalence %
- **Domain Coverage**: % TAX, FIN, SCI, EDU, etc.
- **Layout Type Distributions**: % tabular, multi-column, form-based, etc.
- **Language/Script Coverage**: Script codes with counts and %
- **Content Flags Prevalence**: % with tables, formulas, handwriting, etc.
- **Text Scope Distributions**: % character-level, word-level, page-level, etc.
- **Text Statistics** (when GT text available): Character/word/sentence/paragraph length distributions

---

## Running the Aggregation

### Prerequisites

```bash
# Ensure Layer 2 metadata exists
ls /mnt/e/image_detection/metadata_registry/json/*.json | wc -l
# Should show 24 dataset JSON files (as of 2025-01-30)

# Ensure Python environment is activated
uv sync --extra dev
```

### Basic Usage

```bash
# Aggregate all datasets
python scripts/aggregate_layer2_metadata.py \
    --layer2-dir /mnt/e/image_detection/metadata_registry/json \
    --output-dir metadata_registry/aggregates \
    --verbose

# Expected output:
# Processing arabic-docs...
#    ✅ 10,045 samples
# Processing bhutan-afs...
#    ✅ 135 samples
# ...
# ✅ Processed 24 datasets
# 📁 Output: metadata_registry/aggregates
```

### Single Dataset

```bash
# Aggregate specific dataset
python scripts/aggregate_layer2_metadata.py \
    --dataset tablebank \
    --layer2-dir /mnt/e/image_detection/metadata_registry/json \
    --output-dir metadata_registry/aggregates \
    --verbose

# Expected output:
# Processing tablebank...
# ✅ Aggregated metadata for tablebank
#    Output: metadata_registry/aggregates/tablebank_stats.json
#    Samples: 278,582
#    Quality: 0.85-1.00 (μ=0.93)
#    Top degradations: compression, blur, none
```

---

## Output Format

Each dataset gets a `{dataset_name}_stats.json` file with this structure:

```json
{
  "dataset_name": "tablebank",
  "total_samples": 278582,

  "splits_included": ["train", "test", "val"],
  "split_counts": {
    "train": 222866,
    "test": 27858,
    "val": 27858
  },
  "split_coverage_pct": {
    "train": 80.0,
    "test": 10.0,
    "val": 10.0
  },

  "capture_methods": {
    "born_digital": 278582
  },
  "capture_methods_pct": {
    "born_digital": 100.0
  },

  "quality_scores": [0.85, 0.87, 0.89, ...],
  "quality_summary": {
    "min": 0.85,
    "max": 1.00,
    "mean": 0.93,
    "median": 0.94,
    "stdev": 0.05
  },

  "degradation_types": {
    "compression": 33430,
    "blur": 22286,
    "none": 222866
  },
  "degradation_types_pct": {
    "compression": 12.0,
    "blur": 8.0,
    "none": 80.0
  },
  "top_degradations": [
    {
      "type": "compression",
      "count": 33430,
      "percentage": 12.0,
      "mean_severity": 0.15
    },
    {
      "type": "blur",
      "count": 22286,
      "percentage": 8.0,
      "mean_severity": 0.12
    }
  ],

  "domains": {
    "SCI": 236795,
    "TEC": 41787
  },
  "domains_pct": {
    "SCI": 85.0,
    "TEC": 15.0
  },

  "layout_types": {
    "tabular": 278582
  },
  "layout_types_pct": {
    "tabular": 100.0
  },

  "text_densities": {
    "dense": 195007,
    "moderate": 69646,
    "sparse": 13929
  },
  "text_densities_pct": {
    "dense": 70.0,
    "moderate": 25.0,
    "sparse": 5.0
  },

  "script_codes": {
    "Latn": 264653,
    "Zyyy": 13929
  },
  "script_codes_pct": {
    "Latn": 95.0,
    "Zyyy": 5.0
  },
  "script_families": {
    "latin": 264653,
    "other": 13929
  },
  "script_families_pct": {
    "latin": 95.0,
    "other": 5.0
  },
  "top_scripts": [
    {"script": "Latn", "count": 264653, "percentage": 95.0},
    {"script": "Zyyy", "count": 13929, "percentage": 5.0}
  ],

  "content_flags": {
    "has_table": 278582,
    "has_formula": 41787,
    "has_figure": 69646
  },
  "content_flags_pct": {
    "has_table": 100.0,
    "has_formula": 15.0,
    "has_figure": 25.0
  },

  "text_scopes": {
    "page": 278582
  },
  "text_scopes_pct": {
    "page": 100.0
  },

  "content_types": {
    "printed": 278582
  },
  "content_types_pct": {
    "printed": 100.0
  },

  "paper_sizes": {
    "A4": 111433,
    "Letter": 153220,
    "Custom": 13929
  },
  "paper_sizes_pct": {
    "A4": 40.0,
    "Letter": 55.0,
    "Custom": 5.0
  },

  "text_statistics": {
    "samples_with_text": 250000,
    "samples_with_text_pct": 89.7,
    "text_sources": {
      "ground_truth": 200000,
      "ocr_tesseract": 50000
    },
    "text_sources_pct": {
      "ground_truth": 80.0,
      "ocr_tesseract": 20.0
    },
    "character_count": {
      "min": 12,
      "max": 8500,
      "mean": 850.4,
      "median": 720,
      "stdev": 420.2,
      "percentiles": {"p25": 520, "p50": 720, "p75": 1100}
    },
    "word_count": {
      "min": 2,
      "max": 1450,
      "mean": 145.3,
      "median": 125,
      "stdev": 72.1,
      "percentiles": {"p25": 88, "p50": 125, "p75": 188}
    },
    "sentence_count": {
      "min": 1,
      "max": 85,
      "mean": 8.2,
      "median": 7,
      "stdev": 4.5,
      "percentiles": {"p25": 5, "p50": 7, "p75": 11}
    },
    "paragraph_count": {
      "min": 1,
      "max": 25,
      "mean": 2.1,
      "median": 2,
      "stdev": 1.8,
      "percentiles": {"p25": 1, "p50": 2, "p75": 3}
    },
    "avg_word_length": {
      "min": 3.2,
      "max": 9.4,
      "mean": 5.8,
      "median": 5.7,
      "stdev": 1.2
    },
    "avg_sentence_length": {
      "min": 4,
      "max": 52,
      "mean": 17.6,
      "median": 16,
      "stdev": 6.3
    }
  }
}
```

---

## Text Content & Statistics Pipeline

Text statistics follow a two-stage pipeline that separates extraction from calculation:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TEXT PROCESSING PIPELINE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  STAGE 1: Text Extraction (dataset-specific)                                │
│  ──────────────────────────────────────────                                 │
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │ COCO-Text    │    │ IAM .txt     │    │ DocTR OCR    │                   │
│  │ annotations  │    │ transcripts  │    │ output       │                   │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                   │
│         │                   │                   │                           │
│         ▼                   ▼                   ▼                           │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │ parse_coco   │    │ parse_iam    │    │ extract_ocr  │   Dataset-        │
│  │ _text()      │    │ _trans()     │    │ _output()    │   specific        │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘   parsers         │
│         │                   │                   │                           │
│         └───────────────────┴───────────────────┘                           │
│                             │                                               │
│                             ▼                                               │
│                   ┌─────────────────┐                                       │
│                   │  text_content   │  ◄── Standardized Layer 2 field       │
│                   │  {              │                                       │
│                   │    full_text,   │                                       │
│                   │    segments,    │                                       │
│                   │    source_type  │                                       │
│                   │  }              │                                       │
│                   └────────┬────────┘                                       │
│                            │                                                │
│  STAGE 2: Statistics Calculation (universal)                                │
│  ───────────────────────────────────────────                                │
│                            │                                                │
│                            ▼                                                │
│                   ┌─────────────────┐                                       │
│                   │ calculate_text  │   Single script works on              │
│                   │ _statistics()   │   any dataset's text_content          │
│                   └────────┬────────┘                                       │
│                            │                                                │
│                            ▼                                                │
│                   ┌─────────────────┐                                       │
│                   │ text_statistics │  ◄── Computed statistics              │
│                   │  {              │                                       │
│                   │    char_count,  │                                       │
│                   │    word_count,  │                                       │
│                   │    sent_count,  │                                       │
│                   │    para_count   │                                       │
│                   │  }              │                                       │
│                   └─────────────────┘                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Stage 1: Text Extraction

Each dataset requires a parser to extract text into the standardized `text_content` field:

```bash
# Add text extraction to existing parser
python scripts/annotate_base_metadata.py \
    --dataset cocotext \
    --extract-text \
    --layer2-dir /mnt/e/image_detection/metadata_registry/json

# Or run standalone text extractor for datasets with OCR
python scripts/extract_text_content.py \
    --dataset iam \
    --source-type ground_truth \
    --source-format txt_file \
    --layer2-dir /mnt/e/image_detection/metadata_registry/json
```

**Parser responsibilities:**

- Read source text (GT files, COCO annotations, OCR output)
- Populate `text_content.full_text` with normalized UTF-8 text
- Set `source_type`, `source_format`, `extraction_method`
- Optionally populate `segments` array if positional info available

### Stage 2: Statistics Calculation

Once `text_content` is populated, a single universal script computes statistics:

```bash
# Calculate text statistics for all datasets with text_content
python scripts/calculate_text_statistics.py \
    --layer2-dir /mnt/e/image_detection/metadata_registry/json \
    --output-dir /mnt/e/image_detection/metadata_registry/json \
    --verbose

# Single dataset
python scripts/calculate_text_statistics.py \
    --dataset cocotext \
    --layer2-dir /mnt/e/image_detection/metadata_registry/json
```

**Statistics computed:**

- `character_count`, `character_count_no_spaces`
- `word_count` (whitespace tokenization)
- `sentence_count` (punctuation-based: . ! ?)
- `paragraph_count` (double newline or explicit markers)
- `line_count` (single newline)
- `avg_word_length`, `avg_sentence_length`, `avg_paragraph_length`

### Text Extraction Status by Dataset

| Dataset | Text Source | Status | Parser |
|---------|-------------|--------|--------|
| cocotext | COCO annotations | ⚠️ Pending | `parse_cocotext_text()` |
| iam | .txt transcripts | ⚠️ Pending | `parse_iam_transcription()` |
| hiertext | JSON annotations | ⚠️ Pending | `parse_hiertext_text()` |
| funsd | JSON annotations | ⚠️ Pending | `parse_funsd_text()` |
| sroie | .txt GT files | ⚠️ Pending | `parse_sroie_text()` |
| mlt19 | JSON annotations | ⚠️ Pending | `parse_mlt_text()` |
| textocr | COCO annotations | ⚠️ Pending | `parse_textocr_text()` |
| totaltext | .txt GT files | ⚠️ Pending | `parse_totaltext_text()` |

**Status Legend:**

- ✅ Complete - text_content populated
- ⚠️ Pending - parser not yet implemented
- ❌ N/A - dataset has no text labels

---

## Integration with Quick Reference

After running aggregation, use the statistics to update DATASET_QUICK_REFERENCE.md:

### Before (Manual)

```markdown
| tablebank | 278,582 | ... | Apache-2.0 | Table regions |
```

### After (Metadata-Driven)

```markdown
| tablebank | 278,582 | 📄 100% | 0.85-1.00 (μ=0.93) | 🖨️ 100% | Compression 12%, Blur 8% | ... | Apache-2.0 |
```

### Automation Script

Create `scripts/update_quick_reference_from_aggregates.py` to automatically populate tables:

```python
# Read aggregate statistics
with open("metadata_registry/aggregates/tablebank_stats.json") as f:
    stats = json.load(f)

# Generate table row
capture_icon = "📄" if stats["capture_methods_pct"].get("born_digital", 0) > 80 else "🖨️"
capture_pct = max(stats["capture_methods_pct"].items(), key=lambda x: x[1])
quality_range = f"{stats['quality_summary']['min']}-{stats['quality_summary']['max']} (μ={stats['quality_summary']['mean']})"
top_degs = ", ".join(f"{d['type']} {d['percentage']:.0f}%" for d in stats["top_degradations"][:3])

print(f"| {dataset_name} | {stats['total_samples']:,} | {capture_icon} {capture_pct[1]:.0f}% | {quality_range} | ... | {top_degs} | ... |")
```

---

## Maintenance Workflow

### When to Regenerate Aggregates

1. **After Layer 2 annotation** of new datasets
2. **After re-processing** existing datasets with updated enrichment pipeline
3. **Weekly** during active annotation work
4. **Before major releases** to ensure documentation accuracy

### Automation (Optional)

Add to `.github/workflows/` or pre-commit hooks:

```yaml
# .github/workflows/aggregate-metadata.yml
name: Aggregate Layer 2 Metadata

on:
  push:
    paths:
      - 'metadata_registry/json/**'

jobs:
  aggregate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Aggregate metadata
        run: |
          python scripts/aggregate_layer2_metadata.py \
            --layer2-dir /mnt/e/image_detection/metadata_registry/json \
            --output-dir metadata_registry/aggregates \
            --verbose
      - name: Commit updated aggregates
        run: |
          git add metadata_registry/aggregates/
          git commit -m "chore: update aggregate metadata statistics"
          git push
```

---

## Troubleshooting

### No Layer 2 files found

```bash
# Check external drive is mounted
ls /mnt/e/image_detection/metadata_registry/json/

# If not mounted, mount it first
# (command depends on your system)
```

### Aggregation errors

```bash
# Run with verbose to see errors
python scripts/aggregate_layer2_metadata.py --verbose

# Check specific dataset JSON format
python -m json.tool /mnt/e/image_detection/metadata_registry/json/tablebank_sample.json
```

### Import errors

```bash
# Ensure Python environment includes project source
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH python scripts/aggregate_layer2_metadata.py
```

---

## Related Documentation

- **Layer 2 Schema**: [docs/schema/layer2_enrichment.schema.json](schema/layer2_enrichment.schema.json)
- **Quick Reference**: [datasets/DATASET_QUICK_REFERENCE.md](datasets/DATASET_QUICK_REFERENCE.md)
- **Enhancement Proposal**: [DATASET_QUICK_REFERENCE_ENHANCED_PROPOSAL.md](DATASET_QUICK_REFERENCE_ENHANCED_PROPOSAL.md)

---

**Last Updated**: 2025-01-30
**Script Version**: 1.0.0
**Maintained By**: Data team
