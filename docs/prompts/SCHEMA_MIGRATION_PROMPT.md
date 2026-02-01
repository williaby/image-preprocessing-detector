---
title: Layer 2 Schema Migration - Instructional Prompt for LLM
purpose: Migrate existing Layer 2 metadata from flat field format to full nested object schema
owner: data-team
status: ready
priority: P0-BLOCKING
estimated_time: 4 hours
---

# Task: Migrate Layer 2 Metadata from Flat to Nested Schema Format

## Context

You are working on Project A, an image preprocessing and quality assessment system for a multi-project RAG document pipeline. The system uses a three-layer metadata architecture to track dataset annotations:

- **Layer 1 (Immutable)**: Original dataset labels, never modified
- **Layer 2 (Enrichment)**: Derived annotations from ML models and analysis
- **Layer 3 (Training)**: Training-ready labels computed on-demand

**Problem**: There are currently TWO different Layer 2 schema formats in use:

1. **Simplified flat format** (20 datasets) - Used by legacy annotation pipeline
2. **Full nested object format** (1 dataset: synth-multiscript-250k) - Used by synthetic generator

This inconsistency blocks metadata aggregation and enrichment work.

**Your Mission**: Create a migration script to convert all 20 existing datasets from flat format → full nested schema format.

---

## Repository Structure

```
/home/byron/dev/image_detection/
├── docs/
│   └── schema/
│       └── layer2_enrichment.schema.json          # Target schema definition
├── metadata_registry/
│   └── aggregates/                                # Aggregate statistics output
├── src/image_preprocessing_detector/
│   └── annotation/
│       ├── schemas/
│       │   ├── enrichment.py                      # Pydantic models for Layer 2
│       │   └── immutable.py                       # Pydantic models for Layer 1
│       └── parsers/                               # Dataset-specific parsers
└── scripts/
    └── aggregate_layer2_metadata.py               # Aggregation script (expects nested format)
```

**External Storage** (not in git):

- Layer 2 metadata files: `/mnt/e/image_detection/metadata_registry/json/`
- Format: `{dataset_name}_metadata.json` (one file per dataset)

---

## Current State: Flat Field Format

**Example from existing metadata** (`/mnt/e/image_detection/metadata_registry/json/fintabnet_metadata.json`):

```json
{
  "dataset_name": "fintabnet",
  "sample_count": 97475,
  "samples": [
    {
      "id": "uuid-here",
      "enrichments": {
        "versions": [
          {
            "version": 1,
            "created_by": "annotate_base_metadata.py_v2.0.0",
            "method": "tier_2_model",
            "data": {
              "capture_method": "born_digital",              ← STRING (simplified)
              "capture_confidence": 0.95,
              "capture_detection_method": "dataset_config",
              "resolution_dpi": 300,                         ← FLAT FIELDS
              "resolution_category": "standard_300",
              "resolution_pixels": [2796, 4129],
              "domain_level1": "FIN",                        ← STRING (simplified)
              "domain_confidence": 0.8,
              "has_table": true,                             ← BOOLEAN (simplified)
              "has_formula": false,
              "has_handwriting": false,
              "has_figure": false,
              "content_flags_tier": "tier_2_model",
              "content_flags_source": "doclayout_yolo",
              "text_scope": "page",                          ← STRING (simplified)
              "layout_detections": [...]
            }
          }
        ]
      }
    }
  ]
}
```

---

## Target State: Full Nested Object Format

**Example from synthetic dataset** (`/home/byron/dev/image_detection/data/synthetic_250k/.../sample.json`):

```json
{
  "sample_id": "uuid-here",
  "enrichment_version": 1,
  "created_by": "synthetic_generator_v1.0.0",
  "method": "tier_0_exact",
  "data": {
    "capture_method": {                              ← OBJECT (full schema)
      "method": "born_digital",
      "confidence": 0.95,
      "detection_method": "dataset_config"
    },
    "resolution": {                                  ← OBJECT (full schema)
      "dpi": 300,
      "category": "standard_300",
      "pixels": [2796, 4129]
    },
    "domain": {                                      ← OBJECT (full schema)
      "level1": "FIN",
      "level2": null,
      "level3": null,
      "confidence": 0.8
    },
    "structure": {                                   ← OBJECT (full schema)
      "text_density": null,
      "layout_type": null,
      "element_types": []
    },
    "quality": {                                     ← OBJECT (full schema)
      "overall_score": null,
      "degradations": []
    },
    "language": {                                    ← OBJECT (full schema)
      "language_code": null,
      "script_code": null,
      "bcp47_tag": null,
      "script_family": null,
      "confidence": null,
      "detection_method": null,
      "is_rtl": false,
      "is_primary": true
    },
    "text_scope": {                                  ← OBJECT (full schema)
      "scope": "page",
      "content_type": null,
      "density": null,
      "estimated_chars": null,
      "estimated_words": null,
      "confidence": null,
      "detection_method": null
    },
    "content_flags": {                               ← OBJECT (full schema)
      "has_table": true,
      "has_formula": false,
      "has_handwriting": false,
      "has_signature": false,
      "has_figure": false,
      "tier": "tier_2_model",
      "source": "doclayout_yolo"
    },
    "llm_scores": null,
    "layout_detections": [...]
  }
}
```

---

## Your Task: Create Migration Script

### Objective

Create `scripts/migrate_layer2_schema_to_full.py` that:

1. **Reads** existing Layer 2 metadata files (flat format) from `/mnt/e/image_detection/metadata_registry/json/`
2. **Converts** flat fields → full nested objects according to target schema
3. **Validates** converted data against JSON schema
4. **Writes** migrated files to backup location first, then updates originals
5. **Reports** conversion statistics and any errors

### Requirements

**Input**:

- Source directory: `/mnt/e/image_detection/metadata_registry/json/`
- 20 dataset metadata files in flat format

**Output**:

- Backup directory: `/mnt/e/image_detection/metadata_registry/json_backup_20250130/`
- Updated files: `/mnt/e/image_detection/metadata_registry/json/` (migrated format)
- Migration report: `metadata_registry/migration_report_20250130.json`

**Validation**:

- All migrated files must validate against `docs/schema/layer2_enrichment.schema.json`
- Sample counts must match (no data loss)
- All original fields must be preserved in converted format

---

## Field Mapping Specification

### 1. capture_method (string → object)

**Flat Format**:

```json
{
  "capture_method": "born_digital",
  "capture_confidence": 0.95,
  "capture_detection_method": "dataset_config"
}
```

**Full Schema**:

```json
{
  "capture_method": {
    "method": "born_digital",
    "confidence": 0.95,
    "detection_method": "dataset_config"
  }
}
```

**Rules**:

- If `capture_confidence` missing, use `0.5` (medium confidence)
- If `capture_detection_method` missing, use `"unknown"`

---

### 2. resolution (flat fields → object)

**Flat Format**:

```json
{
  "resolution_dpi": 300,
  "resolution_category": "standard_300",
  "resolution_pixels": [2796, 4129]
}
```

**Full Schema**:

```json
{
  "resolution": {
    "dpi": 300,
    "category": "standard_300",
    "pixels": [2796, 4129]
  }
}
```

---

### 3. domain (flat fields → object)

**Flat Format**:

```json
{
  "domain_level1": "FIN",
  "domain_level2": null,
  "domain_level3": null,
  "domain_confidence": 0.8
}
```

**Full Schema**:

```json
{
  "domain": {
    "level1": "FIN",
    "level2": null,
    "level3": null,
    "confidence": 0.8
  }
}
```

**Rules**:

- If `domain_confidence` missing, use `0.3` for "UNK", `0.8` for classified domains

---

### 4. structure (NEW - create placeholder object)

**Flat Format**: (NONE - doesn't exist in current data)

**Full Schema**:

```json
{
  "structure": {
    "text_density": null,
    "layout_type": null,
    "element_types": []
  }
}
```

**Rules**:

- Always create this object even if all fields are null/empty
- Will be populated later by StructureProvider

---

### 5. quality (NEW - create placeholder object)

**Flat Format**: (NONE - doesn't exist in current data)

**Full Schema**:

```json
{
  "quality": {
    "overall_score": null,
    "degradations": []
  }
}
```

**Rules**:

- Always create this object even if all fields are null/empty
- Will be populated later by DegradationProvider

---

### 6. language (NEW - create placeholder object)

**Flat Format**: (NONE - doesn't exist in current data)

**Full Schema**:

```json
{
  "language": {
    "language_code": null,
    "script_code": null,
    "bcp47_tag": null,
    "script_family": null,
    "confidence": null,
    "detection_method": null,
    "is_rtl": false,
    "is_primary": true
  }
}
```

**Rules**:

- Always create this object with null values
- Will be populated later by LanguageProvider
- Exception: If `script_family` exists in flat format, migrate it to `language.script_family`

---

### 7. text_scope (string → object)

**Flat Format**:

```json
{
  "text_scope": "page",
  "content_type": "printed"
}
```

**Full Schema**:

```json
{
  "text_scope": {
    "scope": "page",
    "content_type": "printed",
    "density": null,
    "estimated_chars": null,
    "estimated_words": null,
    "confidence": null,
    "detection_method": null
  }
}
```

**Rules**:

- If `text_scope` is string, use as `scope` field
- If `content_type` exists as separate field, migrate to nested object
- Other fields default to null

---

### 8. content_flags (flat booleans → object)

**Flat Format**:

```json
{
  "has_table": true,
  "has_formula": false,
  "has_handwriting": false,
  "has_signature": false,
  "has_figure": false,
  "content_flags_tier": "tier_2_model",
  "content_flags_source": "doclayout_yolo"
}
```

**Full Schema**:

```json
{
  "content_flags": {
    "has_table": true,
    "has_formula": false,
    "has_handwriting": false,
    "has_signature": false,
    "has_figure": false,
    "tier": "tier_2_model",
    "source": "doclayout_yolo"
  }
}
```

**Rules**:

- Migrate all `has_*` boolean fields
- Rename `content_flags_tier` → `tier`
- Rename `content_flags_source` → `source`

---

### 9. llm_scores (NEW - create placeholder)

**Flat Format**: (NONE)

**Full Schema**:

```json
{
  "llm_scores": null
}
```

**Rules**:

- Always set to null (will be populated by SigLIPProvider later)

---

### 10. layout_detections (preserve as-is)

**Both Formats**: Same structure (array of COCO boxes)

**Full Schema**:

```json
{
  "layout_detections": [
    {
      "class_name": "Table",
      "bbox": [x, y, width, height],
      "confidence": 0.95,
      "source": "doclayout_yolo"
    }
  ]
}
```

**Rules**:

- Copy array as-is, no transformation needed

---

## Implementation Requirements

### Script Specification

**File**: `scripts/migrate_layer2_schema_to_full.py`

**Command-Line Interface**:

```bash
# Migrate all datasets
python scripts/migrate_layer2_schema_to_full.py \
    --input-dir /mnt/e/image_detection/metadata_registry/json \
    --backup-dir /mnt/e/image_detection/metadata_registry/json_backup_20250130 \
    --output-dir /mnt/e/image_detection/metadata_registry/json \
    --validate \
    --verbose

# Migrate single dataset (dry-run)
python scripts/migrate_layer2_schema_to_full.py \
    --dataset fintabnet \
    --input-dir /mnt/e/image_detection/metadata_registry/json \
    --dry-run \
    --verbose

# Migrate single dataset (actual)
python scripts/migrate_layer2_schema_to_full.py \
    --dataset fintabnet \
    --input-dir /mnt/e/image_detection/metadata_registry/json \
    --backup-dir /mnt/e/image_detection/metadata_registry/json_backup_20250130 \
    --output-dir /mnt/e/image_detection/metadata_registry/json \
    --validate
```

### Core Function Template

```python
#!/usr/bin/env python3
"""Migrate Layer 2 metadata from flat field format to full nested object schema.

This script converts existing Layer 2 metadata files from the legacy flat field
format to the full nested object format matching the Layer 2 enrichment schema.

Usage:
    python scripts/migrate_layer2_schema_to_full.py --input-dir /mnt/e/... --backup-dir /mnt/e/...
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

def migrate_sample_data(flat_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert flat field format to full nested schema format.

    Args:
        flat_data: Sample enrichment data in flat format

    Returns:
        Migrated data in full nested object format
    """
    nested_data = {}

    # 1. Migrate capture_method (string → object)
    if "capture_method" in flat_data:
        nested_data["capture_method"] = {
            "method": flat_data["capture_method"],
            "confidence": flat_data.get("capture_confidence", 0.5),
            "detection_method": flat_data.get("capture_detection_method", "unknown")
        }

    # 2. Migrate resolution (flat → object)
    if "resolution_dpi" in flat_data or "resolution_category" in flat_data:
        nested_data["resolution"] = {
            "dpi": flat_data.get("resolution_dpi"),
            "category": flat_data.get("resolution_category"),
            "pixels": flat_data.get("resolution_pixels")
        }

    # 3. Migrate domain (flat → object)
    if "domain_level1" in flat_data:
        confidence = flat_data.get("domain_confidence", 0.3 if flat_data["domain_level1"] == "UNK" else 0.8)
        nested_data["domain"] = {
            "level1": flat_data["domain_level1"],
            "level2": flat_data.get("domain_level2"),
            "level3": flat_data.get("domain_level3"),
            "confidence": confidence
        }

    # 4. Create structure placeholder (NEW)
    nested_data["structure"] = {
        "text_density": flat_data.get("text_density"),
        "layout_type": flat_data.get("layout_type"),
        "element_types": flat_data.get("element_types", [])
    }

    # 5. Create quality placeholder (NEW)
    nested_data["quality"] = {
        "overall_score": flat_data.get("overall_score"),
        "degradations": flat_data.get("degradations", [])
    }

    # 6. Create language placeholder (NEW)
    nested_data["language"] = {
        "language_code": flat_data.get("language_code"),
        "script_code": flat_data.get("script_code"),
        "bcp47_tag": flat_data.get("bcp47_tag"),
        "script_family": flat_data.get("script_family"),  # May exist in some flat data
        "confidence": flat_data.get("language_confidence"),
        "detection_method": flat_data.get("language_detection_method"),
        "is_rtl": flat_data.get("is_rtl", False),
        "is_primary": flat_data.get("is_primary", True)
    }

    # 7. Migrate text_scope (string → object)
    if "text_scope" in flat_data:
        nested_data["text_scope"] = {
            "scope": flat_data["text_scope"] if isinstance(flat_data["text_scope"], str) else flat_data.get("text_scope", {}).get("scope"),
            "content_type": flat_data.get("content_type"),
            "density": flat_data.get("text_density_scope"),
            "estimated_chars": flat_data.get("estimated_chars"),
            "estimated_words": flat_data.get("estimated_words"),
            "confidence": flat_data.get("text_scope_confidence"),
            "detection_method": flat_data.get("text_scope_detection_method")
        }

    # 8. Migrate content_flags (flat booleans → object)
    nested_data["content_flags"] = {
        "has_table": flat_data.get("has_table", False),
        "has_formula": flat_data.get("has_formula", False),
        "has_handwriting": flat_data.get("has_handwriting", False),
        "has_signature": flat_data.get("has_signature", False),
        "has_figure": flat_data.get("has_figure", False),
        "tier": flat_data.get("content_flags_tier"),
        "source": flat_data.get("content_flags_source")
    }

    # 9. Create llm_scores placeholder
    nested_data["llm_scores"] = flat_data.get("llm_scores")  # Usually null

    # 10. Preserve layout_detections as-is
    if "layout_detections" in flat_data:
        nested_data["layout_detections"] = flat_data["layout_detections"]

    return nested_data


def migrate_dataset(
    dataset_name: str,
    input_dir: Path,
    output_dir: Path,
    backup_dir: Optional[Path] = None,
    validate: bool = True,
    dry_run: bool = False,
    verbose: bool = False
) -> Dict[str, Any]:
    """Migrate a single dataset from flat to nested schema.

    Args:
        dataset_name: Canonical dataset name
        input_dir: Directory with original metadata files
        output_dir: Directory for migrated metadata files
        backup_dir: Optional backup directory
        validate: Validate against JSON schema
        dry_run: Don't write files, just report
        verbose: Print detailed progress

    Returns:
        Migration statistics dict
    """
    input_file = input_dir / f"{dataset_name}_metadata.json"

    if not input_file.exists():
        return {
            "dataset": dataset_name,
            "status": "skipped",
            "reason": "No metadata file found"
        }

    # Load original file
    with open(input_file) as f:
        dataset_metadata = json.load(f)

    # Backup if requested
    if backup_dir and not dry_run:
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_file = backup_dir / f"{dataset_name}_metadata.json"
        with open(backup_file, 'w') as f:
            json.dump(dataset_metadata, f, indent=2)
        if verbose:
            print(f"✅ Backed up to {backup_file}")

    # Migrate each sample
    migrated_samples = []
    errors = []

    for idx, sample in enumerate(dataset_metadata.get("samples", [])):
        try:
            # Extract enrichment data
            enrichments = sample.get("enrichments", {})
            versions = enrichments.get("versions", [])

            for version in versions:
                flat_data = version.get("data", {})

                # Convert to nested format
                nested_data = migrate_sample_data(flat_data)

                # Replace data field
                version["data"] = nested_data

            migrated_samples.append(sample)

        except Exception as e:
            errors.append({
                "sample_index": idx,
                "sample_id": sample.get("id", "unknown"),
                "error": str(e)
            })
            if verbose:
                print(f"⚠️  Error migrating sample {idx}: {e}")

    # Update dataset metadata
    dataset_metadata["samples"] = migrated_samples

    # Add migration metadata
    dataset_metadata["migration"] = {
        "migrated_at": "2025-01-30T00:00:00Z",
        "migration_script": "migrate_layer2_schema_to_full.py_v1.0.0",
        "format_version": "full_nested_v2.0",
        "samples_migrated": len(migrated_samples),
        "errors": len(errors)
    }

    # Validate if requested
    if validate:
        # TODO: Implement JSON schema validation
        # from jsonschema import validate as json_validate
        # with open("docs/schema/layer2_enrichment.schema.json") as f:
        #     schema = json.load(f)
        # for sample in migrated_samples:
        #     json_validate(sample["enrichments"]["versions"][-1], schema)
        pass

    # Write migrated file
    if not dry_run:
        output_file = output_dir / f"{dataset_name}_metadata.json"
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(dataset_metadata, f, indent=2)
        if verbose:
            print(f"✅ Migrated {output_file}")

    return {
        "dataset": dataset_name,
        "status": "success" if not errors else "partial",
        "samples_total": len(dataset_metadata.get("samples", [])),
        "samples_migrated": len(migrated_samples),
        "errors": errors
    }


def main():
    """Main migration function."""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate Layer 2 metadata to full schema")
    parser.add_argument("--dataset", help="Migrate single dataset (canonical name)")
    parser.add_argument("--input-dir", type=Path, required=True, help="Input directory with flat format files")
    parser.add_argument("--output-dir", type=Path, required=True, help="Output directory for migrated files")
    parser.add_argument("--backup-dir", type=Path, help="Backup directory (recommended)")
    parser.add_argument("--validate", action="store_true", help="Validate against JSON schema")
    parser.add_argument("--dry-run", action="store_true", help="Don't write files, just report")
    parser.add_argument("--verbose", action="store_true", help="Print detailed progress")

    args = parser.parse_args()

    # Get list of datasets to migrate
    if args.dataset:
        datasets = [args.dataset]
    else:
        # Find all metadata files
        metadata_files = list(args.input_dir.glob("*_metadata.json"))
        datasets = [f.stem.replace("_metadata", "") for f in metadata_files]

    # Migrate each dataset
    results = []
    for dataset_name in datasets:
        if args.verbose:
            print(f"\n{'='*60}")
            print(f"Migrating: {dataset_name}")
            print(f"{'='*60}")

        result = migrate_dataset(
            dataset_name=dataset_name,
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            backup_dir=args.backup_dir,
            validate=args.validate,
            dry_run=args.dry_run,
            verbose=args.verbose
        )
        results.append(result)

    # Generate migration report
    report = {
        "migration_date": "2025-01-30",
        "total_datasets": len(results),
        "successful": sum(1 for r in results if r["status"] == "success"),
        "partial": sum(1 for r in results if r["status"] == "partial"),
        "skipped": sum(1 for r in results if r["status"] == "skipped"),
        "results": results
    }

    # Write report
    report_file = Path("metadata_registry/migration_report_20250130.json")
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    # Print summary
    print(f"\n{'='*60}")
    print(f"MIGRATION SUMMARY")
    print(f"{'='*60}")
    print(f"Total datasets: {report['total_datasets']}")
    print(f"✅ Successful: {report['successful']}")
    print(f"⚠️  Partial: {report['partial']}")
    print(f"⏭️  Skipped: {report['skipped']}")
    print(f"📁 Report: {report_file}")

    if args.backup_dir:
        print(f"💾 Backup: {args.backup_dir}")


if __name__ == "__main__":
    main()
```

---

## Validation Criteria

After migration, verify:

1. **Sample Count Preservation**:

   ```bash
   # Before migration
   cat /mnt/e/.../fintabnet_metadata.json | jq '.sample_count'
   # After migration
   cat /mnt/e/.../fintabnet_metadata.json | jq '.sample_count'
   # Must match!
   ```

2. **Field Completeness**:

   ```bash
   # Check all 10 top-level fields exist
   cat /mnt/e/.../fintabnet_metadata.json | jq '.samples[0].enrichments.versions[0].data | keys'
   # Should show: capture_method, resolution, domain, structure, quality, language, text_scope, content_flags, llm_scores, layout_detections
   ```

3. **Data Preservation**:

   ```bash
   # Spot-check that no data was lost
   # Example: Check has_table value preserved
   cat /mnt/e/.../fintabnet_metadata.json | jq '.samples[0].enrichments.versions[0].data.content_flags.has_table'
   # Should match original flat_data.has_table value
   ```

4. **Schema Validation** (optional but recommended):

   ```python
   from jsonschema import validate
   import json

   with open("docs/schema/layer2_enrichment.schema.json") as f:
       schema = json.load(f)

   with open("migrated_file.json") as f:
       data = json.load(f)

   # Validate each sample's enrichment data
   for sample in data["samples"]:
       for version in sample["enrichments"]["versions"]:
           validate(instance=version, schema=schema)
   ```

---

## Expected Outputs

### 1. Migration Report

**File**: `metadata_registry/migration_report_20250130.json`

```json
{
  "migration_date": "2025-01-30",
  "total_datasets": 20,
  "successful": 20,
  "partial": 0,
  "skipped": 0,
  "results": [
    {
      "dataset": "fintabnet",
      "status": "success",
      "samples_total": 97475,
      "samples_migrated": 97475,
      "errors": []
    },
    {
      "dataset": "dibco",
      "status": "success",
      "samples_total": 212,
      "samples_migrated": 212,
      "errors": []
    }
    // ... 18 more datasets
  ]
}
```

### 2. Backup Files

**Location**: `/mnt/e/image_detection/metadata_registry/json_backup_20250130/`

All 20 original files preserved as-is for rollback if needed.

### 3. Migrated Files

**Location**: `/mnt/e/image_detection/metadata_registry/json/`

All 20 files updated with full nested schema format.

---

## Testing Strategy

### Unit Tests

Create `tests/unit/test_schema_migration.py`:

```python
import pytest
from scripts.migrate_layer2_schema_to_full import migrate_sample_data

def test_migrate_capture_method():
    """Test capture_method flat → nested migration."""
    flat = {
        "capture_method": "born_digital",
        "capture_confidence": 0.95,
        "capture_detection_method": "dataset_config"
    }

    nested = migrate_sample_data(flat)

    assert nested["capture_method"]["method"] == "born_digital"
    assert nested["capture_method"]["confidence"] == 0.95
    assert nested["capture_method"]["detection_method"] == "dataset_config"

def test_migrate_domain():
    """Test domain flat → nested migration."""
    flat = {
        "domain_level1": "FIN",
        "domain_confidence": 0.8
    }

    nested = migrate_sample_data(flat)

    assert nested["domain"]["level1"] == "FIN"
    assert nested["domain"]["level2"] is None
    assert nested["domain"]["confidence"] == 0.8

def test_migrate_content_flags():
    """Test content_flags flat → nested migration."""
    flat = {
        "has_table": True,
        "has_formula": False,
        "content_flags_tier": "tier_2_model",
        "content_flags_source": "doclayout_yolo"
    }

    nested = migrate_sample_data(flat)

    assert nested["content_flags"]["has_table"] is True
    assert nested["content_flags"]["has_formula"] is False
    assert nested["content_flags"]["tier"] == "tier_2_model"
    assert nested["content_flags"]["source"] == "doclayout_yolo"

def test_create_placeholders():
    """Test placeholder creation for missing fields."""
    flat = {"capture_method": "scanner"}  # Minimal data

    nested = migrate_sample_data(flat)

    # Check all placeholder objects created
    assert "structure" in nested
    assert "quality" in nested
    assert "language" in nested
    assert nested["quality"]["degradations"] == []
    assert nested["structure"]["element_types"] == []
```

### Integration Test

```python
def test_migrate_full_dataset():
    """Test migrating a complete dataset file."""
    from scripts.migrate_layer2_schema_to_full import migrate_dataset

    result = migrate_dataset(
        dataset_name="dibco",
        input_dir=Path("/mnt/e/.../json"),
        output_dir=Path("/tmp/test_migration"),
        validate=True,
        dry_run=False,
        verbose=True
    )

    assert result["status"] == "success"
    assert result["samples_migrated"] == result["samples_total"]
    assert len(result["errors"]) == 0
```

---

## Success Criteria

Migration is complete when:

- [x] All 20 datasets migrated successfully (0 errors)
- [x] Backup created at `/mnt/e/.../json_backup_20250130/`
- [x] All migrated files validate against `layer2_enrichment.schema.json`
- [x] Sample counts match before/after migration
- [x] Aggregation script works on migrated data:

  ```bash
  python scripts/aggregate_layer2_metadata.py --dataset fintabnet --verbose
  # Should show stats without errors
  ```

- [x] Spot-check 5 datasets: verify data preserved correctly

---

## Edge Cases to Handle

1. **Missing fields in flat data**: Set to null in nested format
2. **Unknown capture method**: Use `"unknown"` with confidence `0.0`
3. **script_family as "ltr"**: This is non-standard, should map to `"latin"` in language.script_family
4. **Empty content_flags**: All false, tier/source can be null
5. **Missing text_scope**: Create object with all null values

---

## Rollback Plan

If migration fails or produces invalid data:

```bash
# Restore from backup
rm -rf /mnt/e/image_detection/metadata_registry/json/*
cp -r /mnt/e/image_detection/metadata_registry/json_backup_20250130/* /mnt/e/image_detection/metadata_registry/json/

# Verify restoration
python scripts/aggregate_layer2_metadata.py --dataset fintabnet --verbose
```

---

## Deliverables

1. **Script**: `scripts/migrate_layer2_schema_to_full.py` (executable, documented)
2. **Tests**: `tests/unit/test_schema_migration.py` (passing)
3. **Backup**: All 20 original files backed up
4. **Migration Report**: `metadata_registry/migration_report_20250130.json`
5. **Validation**: All migrated files pass schema validation

---

## References

- **Target Schema**: `/home/byron/dev/image_detection/docs/schema/layer2_enrichment.schema.json`
- **Example Full Format**: `/home/byron/dev/image_detection/data/synthetic_250k/worker_0/Arab/a6f2c20c-512c-423e-9c1e-55140c99bce6.json`
- **Example Flat Format**: `/mnt/e/image_detection/metadata_registry/json/fintabnet_metadata.json`
- **Pydantic Models**: `/home/byron/dev/image_detection/src/image_preprocessing_detector/annotation/schemas/enrichment.py`

---

**Estimated Time**: 4 hours (2 hours implementation + 1 hour testing + 1 hour validation)
**Priority**: P0 (BLOCKING all subsequent enrichment work)
**Assignee**: LLM Agent or Development Team
**Due Date**: End of Week 1
