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
  }
}
```

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
- **Quick Reference**: [docs/DATASET_QUICK_REFERENCE.md](DATASET_QUICK_REFERENCE.md)
- **Enhancement Proposal**: [docs/DATASET_QUICK_REFERENCE_ENHANCED_PROPOSAL.md](DATASET_QUICK_REFERENCE_ENHANCED_PROPOSAL.md)

---

**Last Updated**: 2025-01-30
**Script Version**: 1.0.0
**Maintained By**: Data team
