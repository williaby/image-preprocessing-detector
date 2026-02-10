---
owner: docs-team
purpose: Standardize dataset naming conventions and alias mappings.
schema_type: common
status: active
tags:
- datasets
- naming
- standards
title: Dataset Naming Standard
---

> **Last Updated**: 2025-01-30
> **Purpose**: Resolve naming confusion by establishing canonical names and alias mappings
> **Migration Status**: 🔄 In Progress - standardizing to kebab-case
> **Enforcement**: All new code MUST use canonical names

---

## Naming Convention Standard

### Rules

1. **Canonical Name Format**: `kebab-case` (lowercase with hyphens)
   - ✅ Good: `nist-sd2`, `ohr-bench`, `coco-text`
   - ❌ Bad: `nist_sd2`, `OHR-Bench`, `CocoText`

2. **Alias Support**: Source names and common variations preserved for backward compatibility
   - Stored in `DATASET_REGISTRY` under `aliases` field
   - Code should normalize to canonical name internally

3. **Directory Names**: Match canonical names exactly
   - `01_base_data/nist-sd2/` (not `nist_db2` or `nist_sd_2`)

4. **Metadata References**: Use canonical names in all JSON metadata
   - `{"dataset_name": "nist-sd2", "dataset_version": "1.0"}`

5. **Code References**: Import canonical names from `DATASET_REGISTRY`
   - `from schema_utils import DATASET_REGISTRY`
   - `dataset = DATASET_REGISTRY["nist-sd2"]`

---

## Canonical Name Registry

### All Datasets (45 total)

| Canonical Name | Source Name | Common Aliases | Status | Notes |
|----------------|-------------|----------------|--------|-------|
| `arabic-docs` | arabic_docs_ocr | arabic_docs, arabic-ocr | ✅ | Arabic OCR dataset |
| `bhutan-afs` | bhutan_financial | bhutan_financial, bhutan-financial | ✅ | Bhutan annual financial statements |
| `cc-ocr` | cc_ocr | cc_ocr, ccocr | ✅ | CJK mixed OCR |
| `coco-text` | cocotext | cocotext, coco_text | 🔄 | Scene text (COCO dataset) |
| `cvsi` | cvsi | cvsi2015, cvsi-2015 | ✅ | Video scene text |
| `dibco` | dibco | dibco-train | ✅ | Document binarization competition dataset |
| `diqa-5000` | diqa | diqa_5000, diqa5000 | ✅ | Document IQA benchmark |
| `doc3d` | doc3D-dataset | doc-3d, doc_3d, Doc3D | ✅ | Document 3D shape recovery (dewarping) |
| `doclaynet` | doclaynet | doc-laynet | ✅ | DocLayNet layout dataset |
| `docsynth` | docsynth300k | docsynth_300k, docsynth-300k | 🔄 | Synthetic documents (300K) |
| `dzongkha-digits` | dzongkha_digits | dzongkha-digits, dzongkha_digits | ✅ | Dzongkha handwritten digits (Tibetan script) |
| `financebench` | financebench | finance-bench | 🔄 | Financial RAG QA |
| `fintabnet` | fintabnet | fin-tab-net | ✅ | Financial tables |
| `funsd` | funsd | - | ✅ | Form understanding (noisy scans) |
| `funsd-plus` | funsd_plus | funsdplus, funsd+ | ✅ | Extended FUNSD |
| `hasy` | hasyv2 | hasy_v2, maths_handwriting | ✅ | Math symbols handwriting |
| `hindi-synth` | hindi_ocr_synthetic | hindi_ocr, hindi-ocr-synthetic | ✅ | Synthetic Hindi OCR |
| `hiertext` | hiertext | hier-text, hier_text | ✅ | Hierarchical scene text |
| `iam` | iam_handwriting | iam_handwriting, iam-handwriting | 🔄 | IAM handwriting database |
| `im2latex` | im2latex | im2latex-100k | ✅ | Image to LaTeX formulas |
| `invoices-kg` | invoices_kaggle | invoices_kaggle, kaggle-invoices | ✅ | Kaggle invoices dataset |
| `jssoda` | jssoda | JSSODa (HuggingFace capitalization) | 🔄 | Japanese Simple Synthetic OCR Dataset |
| `mathverse` | mathverse | math-verse | ✅ | Multi-modal math problems |
| `mdiw13` | mdiw13 | mdiw-13, mdiw_13 | ✅ | Multi-lingual document image words (13 scripts) |
| `midv500` | midv500 | midv-500 | ✅ | Mobile ID documents (500 types) |
| `midv500-data` | midv500_data | midv500_data, midv-500-data | ✅ | Extended MIDV-500 |
| `mle2e` | mle2e | ml-e2e | ✅ | Multi-lingual end-to-end |
| `mlt19` | mlt19 | mlt-19, icdar-mlt19 | ✅ | Multi-lingual text (ICDAR 2019) |
| `mobile-receipts` | mobile_receipts_voxel51 | mobile_receipts, receipts-voxel | 🔄 | Mobile receipts (Voxel51) |
| `multilingual-scripts` | multilingual_scripts | multilingual_scripts | ✅ | Synthetic multi-script (27 scripts, 3K sample) |
| `multimodal-textbook` | multimodal_textbook | multimodal_textbook | ✅ | STEM textbook pages |
| `openlid-v2` | openlid_v2 | openlid-v2, openlid2 | 📚 | OpenLID v2 text corpus (201 languages, 116M+ samples) |
| `muharaf` | muharaf | muharaf_arabic_manuscripts | 🔄 | Arabic historical manuscripts |
| `nepali-handwritten` | nepali_handwritten | nepali_handwritten | ✅ | Nepali handwriting |
| `nist-sd2` | nist_db2 | nist_sd2, nist_sd_2, nist-db2 | ✅ | NIST Special Database 2 (tax forms) |
| `nist-sd6` | nist_sd6 | nist_sd_6 | ✅ | NIST SD-6 (forms + handprint) |
| `nist-sd19` | nist_sd19 | nist_sd_19 | ✅ | NIST SD-19 (handwriting) |
| `ocr-quality` | ocr_quality | ocr_quality | ✅ | OCR quality reference dataset |
| `ohr-bench` | ohr_bench | ohr_bench, ohrbench | 🔄 | OCR hallucination benchmark |
| `omnidocbench` | omnidocbench | omni-doc-bench | 🔄 | Multi-task benchmark framework |
| `pubtabnet` | pubtabnet | pub-tab-net | ✅ | Publication tables dataset |
| `pucit-ohul` | pucit_ohul_urdu | pucit_ohul, pucit-ohul-urdu | ✅ | PUCIT Urdu handwriting |
| `realdae` | realdae | real-dae | ✅ | Real document auto-enhancement |
| `rvl-cdip` | rvl_cdip | rvl_cdip, rvlcdip | ✅ | RVL-CDIP document classification |
| `signatr6k` | signatr6k | signatr-6k, signature-6k | ✅ | Text segmentation (signatures) |
| `siw13` | siw13 | siw-13, siw_13 | ✅ | Script identification words (13 scripts) |
| `smartdoc-qa` | smartdoc-qa | smartdoc_qa | ✅ | Mobile capture quality assessment |
| `sroie` | sroie_icdar2019 | sroie-receipts, sroie-icdar2019 | ✅ | ICDAR 2019 SROIE Malaysian receipts (973 images) |
| `synth-multiscript-250k` | synthetic_250k | synth-multiscript, synthetic_250k | 🔄 | Synthetic multi-script 250K (27 scripts, SigLIP training) |
| `synthetic-iqa` | synthetic_iqa | synthetic_iqa | ✅ | Synthetic IQA test samples |
| `tablebank` | tablebank | table-bank | ✅ | TableBank dataset |
| `tibhcr` | TibHCR | Tibetan Handwritten Character Recognition | ✅ | Tibetan handwriting |
| `tobacco800` | tobacco800 | tobacco-800 | ✅ | Tobacco 800 degraded docs |
| `wili-2018` | wili_2018 | wili2018, wili | ❌ | Wikipedia language ID (text-only) |
| `yarmouk` | yarmouk_ocr_images | yarmouk_ocr, yarmouk-ocr | ✅ | Yarmouk Arabic OCR |

**Status Legend**:

- ✅ **Complete**: Training-ready, canonical name established
- 🔄 **In Progress**: Format conversion, label extraction, or generation underway
- 📚 **Non-Image Corpus**: Text-only corpus used for generation
- ❌ **Blocked**: Cannot use for image training

---

## Migration Guide

### Step 1: Update DATASET_REGISTRY

**Location**: `src/image_preprocessing_detector/schema_utils/dataset_source.py`

**Before**:

```python
DATASET_REGISTRY = {
    "nist_db2": {
        "full_name": "NIST SD-2 (Tax Forms)",
        "category": "forms",
        "license": "Public Domain"
    }
}
```

**After**:

```python
DATASET_REGISTRY = {
    "nist-sd2": {
        "full_name": "NIST SD-2 (Tax Forms)",
        "category": "forms",
        "license": "Public Domain",
        "aliases": ["nist_db2", "nist_sd2", "nist_sd_2", "nist-db2"]
    }
}
```

### Step 2: Normalize Function

Add utility function to handle aliases:

```python
# src/image_preprocessing_detector/schema_utils/dataset_source.py

def normalize_dataset_name(name: str) -> str:
    """
    Normalize dataset name to canonical format.

    Args:
        name: Dataset name (canonical or alias)

    Returns:
        Canonical dataset name

    Raises:
        KeyError: If dataset name not found in registry
    """
    # Check if already canonical
    if name in DATASET_REGISTRY:
        return name

    # Search aliases
    for canonical, info in DATASET_REGISTRY.items():
        if name in info.get("aliases", []):
            return canonical

    raise KeyError(f"Dataset '{name}' not found in registry")

# Usage example
canonical_name = normalize_dataset_name("nist_db2")  # Returns "nist-sd2"
dataset_info = DATASET_REGISTRY[canonical_name]
```

### Step 3: Rename Directories

**Current State**:

```
01_base_data/
├── nist_db2/              ← Underscore format
├── hasyv2/                ← No separator
└── ohr_bench/             ← Underscore format
```

**Target State**:

```
01_base_data/
├── nist-sd2/              ← Canonical kebab-case
├── hasy/                  ← Canonical short name
└── ohr-bench/             ← Canonical kebab-case
```

**Migration Script**:

```bash
#!/bin/bash
# scripts/migrate_dataset_names.sh

# Backup first!
cp -r 01_base_data 01_base_data_backup

# Rename directories
mv 01_base_data/nist_db2 01_base_data/nist-sd2
mv 01_base_data/hasyv2 01_base_data/hasy
mv 01_base_data/ohr_bench 01_base_data/ohr-bench
# ... repeat for all datasets

echo "Migration complete. Verify and remove backup."
```

### Step 4: Update Metadata References

**Find all metadata files**:

```bash
grep -r "nist_db2" metadata_registry/
grep -r "historical_degraded" metadata_registry/
```

**Update JSON files**:

```python
# scripts/update_metadata_names.py

import json
from pathlib import Path

ALIAS_MAP = {
    "nist_db2": "nist-sd2",
    "hasyv2": "hasy",
    "ohr_bench": "ohr-bench",
    # ... add all mappings
}

def update_metadata_file(filepath: Path):
    with open(filepath) as f:
        data = json.load(f)

    # Update dataset_name field
    if "dataset_name" in data:
        old_name = data["dataset_name"]
        if old_name in ALIAS_MAP:
            data["dataset_name"] = ALIAS_MAP[old_name]
            print(f"Updated {filepath}: {old_name} → {ALIAS_MAP[old_name]}")

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

# Run on all metadata files
for filepath in Path("metadata_registry/json/").glob("*.json"):
    update_metadata_file(filepath)
```

### Step 5: Update Code References

**Find code references**:

```bash
grep -r "nist_db2" src/
grep -r "historical_degraded" src/
```

**Replace with canonical names**:

```python
# Before
dataset_name = "nist_db2"

# After
from schema_utils import normalize_dataset_name
dataset_name = normalize_dataset_name("nist_db2")  # Returns "nist-sd2"
```

---

## Naming Conflicts Resolved

### Historical Naming Issues

| Issue | Old Names | Canonical Name | Resolution |
|-------|-----------|----------------|------------|
| NIST SD-2 mismatch | `nist-sd2`, `nist_db2`, `nist_sd2` | `nist-sd2` | All aliases map to `nist-sd2` |
| DIBCO naming | `dibco-train` | `dibco` | Standardized to `dibco` |
| HASYv2 variants | `hasyv2`, `hasy_v2`, `maths_handwriting` | `hasy` | All map to `hasy` |
| Yarmouk confusion | `yarmouk_ocr`, `yarmouk_ocr_images` | `yarmouk` | Image version is primary |
| COCO-Text | `cocotext`, `coco_text`, `coco-text` | `coco-text` | Hyphenated canonical |

### Future Prevention

1. **All new datasets** MUST use kebab-case from day one
2. **Aliases** added to `DATASET_REGISTRY` for backward compatibility
3. **Pre-commit hook** validates dataset names in metadata
4. **Documentation** enforces canonical names in all examples

---

## Validation & Enforcement

### Pre-Commit Hook

**Location**: `.git/hooks/pre-commit` or `.pre-commit-config.yaml`

```yaml
# .pre-commit-config.yaml

repos:
  - repo: local
    hooks:
      - id: validate-dataset-names
        name: Validate dataset names
        entry: python scripts/validate_dataset_names.py
        language: system
        files: \.(json|py)$
        stages: [commit]
```

**Validation Script**:

```python
# scripts/validate_dataset_names.py

import json
import sys
from pathlib import Path
from schema_utils import DATASET_REGISTRY

def validate_file(filepath: Path) -> bool:
    """Validate dataset names in file match canonical registry."""
    if filepath.suffix == ".json":
        with open(filepath) as f:
            data = json.load(f)

        if "dataset_name" in data:
            name = data["dataset_name"]
            if name not in DATASET_REGISTRY:
                print(f"❌ Invalid dataset name in {filepath}: '{name}'")
                print(f"   Use canonical name or update DATASET_REGISTRY")
                return False

    return True

# Run validation on staged files
errors = False
for filepath in sys.argv[1:]:
    if not validate_file(Path(filepath)):
        errors = True

sys.exit(1 if errors else 0)
```

### Runtime Validation

**In code**:

```python
from schema_utils import normalize_dataset_name, DATASET_REGISTRY

def get_dataset_info(name: str):
    """Get dataset info with automatic name normalization."""
    try:
        canonical = normalize_dataset_name(name)
        return DATASET_REGISTRY[canonical]
    except KeyError:
        raise ValueError(f"Unknown dataset: {name}")

# Usage
info = get_dataset_info("nist_db2")  # Automatically normalized to "nist-sd2"
```

---

## Registry Integration

### Full DATASET_REGISTRY Example

```python
# src/image_preprocessing_detector/schema_utils/dataset_source.py

DATASET_REGISTRY = {
    "nist-sd2": {
        "full_name": "NIST SD-2 (Tax Forms)",
        "category": "forms",
        "license": "Public Domain",
        "images": 5590,
        "format": "png",
        "labels": ["form_labels"],
        "aliases": ["nist_db2", "nist_sd2", "nist_sd_2", "nist-db2"],
        "storage_path": "01_base_data/nist-sd2/",
        "training_ready": True
    },
    "dibco": {
        "full_name": "DIBCO Document Binarization Competition",
        "category": "degradation",
        "license": "Academic",
        "images": 343,
        "format": "png",
        "labels": ["degradation_labels", "binarization"],
        "aliases": ["dibco-train"],
        "storage_path": "01_base_data/dibco/",
        "training_ready": True,
        "splits": {
            "train": 212,
            "test": 131  # RESERVED - competition test sets
        }
    },
    "hasy": {
        "full_name": "HASYv2 Math Symbols Handwriting",
        "category": "handwriting",
        "license": "CC0",
        "images": 168233,
        "format": "png",
        "labels": ["symbol_labels", "handwriting"],
        "aliases": ["hasyv2", "hasy_v2", "maths_handwriting"],
        "storage_path": "01_base_data/hasy/",
        "training_ready": True,
        "splits": {
            "train": 151410,
            "test": 16823  # RESERVED
        }
    },
    # ... 41 more datasets
}

def normalize_dataset_name(name: str) -> str:
    """Normalize dataset name to canonical format."""
    if name in DATASET_REGISTRY:
        return name

    for canonical, info in DATASET_REGISTRY.items():
        if name in info.get("aliases", []):
            return canonical

    raise KeyError(f"Dataset '{name}' not found in registry. "
                   f"Available: {list(DATASET_REGISTRY.keys())}")

def get_dataset_info(name: str) -> dict:
    """Get dataset info with automatic name normalization."""
    canonical = normalize_dataset_name(name)
    return DATASET_REGISTRY[canonical]
```

---

## Migration Checklist

### Phase 1: Registry & Code (Week 1)

- [ ] Update `DATASET_REGISTRY` with canonical names and aliases
- [ ] Add `normalize_dataset_name()` function
- [ ] Add pre-commit hook for validation
- [ ] Update all code imports to use canonical names
- [ ] Run test suite to verify no breaks

### Phase 2: Directories (Week 2)

- [ ] Create backup of `01_base_data/` and `02_benchmark_only/`
- [ ] Run directory rename script
- [ ] Verify all images accessible at new paths
- [ ] Update symlinks (if any)
- [ ] Test dataset loading code

### Phase 3: Metadata (Week 2-3)

- [ ] Run metadata update script
- [ ] Verify all metadata files use canonical names
- [ ] Regenerate Layer 2 enrichment files (if needed)
- [ ] Update split files in `splits/` directory

### Phase 4: Documentation (Week 3)

- [ ] Update DATASET_QUICK_REFERENCE.md
- [ ] Update DATASET_PROCESSING_STATUS.md
- [ ] Update individual dataset files in source/
- [ ] Update all training documentation
- [ ] Update CLAUDE.md

### Phase 5: Validation (Week 3-4)

- [ ] Run full validation suite
- [ ] Verify training pipeline works
- [ ] Test all conversion scripts
- [ ] Verify metadata registry queries
- [ ] End-to-end test on 5 datasets

---

## Reference Implementation

### Example: Loading Dataset with Alias Support

```python
from pathlib import Path
from schema_utils import get_dataset_info

# User provides alias
user_input = "nist_db2"  # Old name

# Get canonical info
info = get_dataset_info(user_input)
# Returns:
# {
#   "full_name": "NIST SD-2 (Tax Forms)",
#   "category": "forms",
#   "storage_path": "01_base_data/nist-sd2/",
#   ...
# }

# Load images from correct path
dataset_path = Path(info["storage_path"])
images = list(dataset_path.glob("*.png"))
print(f"Loaded {len(images)} images from {info['full_name']}")
```

### Example: Batch Name Normalization

```python
from schema_utils import normalize_dataset_name

# Mixed name formats from legacy code
legacy_names = ["nist_db2", "hasyv2", "tablebank"]

# Normalize all to canonical
canonical_names = [normalize_dataset_name(name) for name in legacy_names]
# Result: ["nist-sd2", "hasy", "tablebank"]
```

---

## Related Documentation

- **Quick Reference**: [DATASET_QUICK_REFERENCE.md](DATASET_QUICK_REFERENCE.md) - Training-focused lookup
- **Processing Status**: [DATASET_PROCESSING_STATUS.md](DATASET_PROCESSING_STATUS.md) - Current state tracking
- **Individual Datasets**: [source/](source/) - 51 individual dataset files
- **Task Indices**: [indices/](indices/) - 7 task-based training recipes
- **Schema Utilities**: `src/image_preprocessing_detector/schema_utils/dataset_source.py` - Python registry

---

**Last Updated**: 2025-02-02
**Migration Status**: ✅ Complete
**Questions**: Contact data team or create issue in project repository
