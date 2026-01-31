---
owner: docs-team
purpose: Enhanced dataset quick reference with Layer 2 metadata aggregates
schema_type: common
status: proposal
tags:
- datasets
- training
- metadata
title: Dataset Quick Reference (Enhanced with Layer 2 Metadata)
---

> **Purpose**: Proposal for enhancing Quick Reference with aggregated Layer 2 metadata
> **Goal**: Surface qualitative/quantitative dataset characteristics for better training decisions
> **Based On**: layer2_enrichment.schema.json metadata fields

---

## Enhancement Strategy

### Problem

Current Quick Reference shows:

- Dataset name, image count, split info, license
- Generic "Notes" column with vague descriptors
- **Missing**: Distribution of capture methods, domains, quality levels, layout types, content characteristics

### Solution

Add **metadata profile cards** for each dataset showing aggregated Layer 2 statistics.

---

## Proposed Enhanced Table Format

### Example: IQA Training Section

| Dataset | Images | **Capture Method** | **Quality Profile** | **Content Type** | **Degradations** | Split | License |
|---------|--------|-------------------|---------------------|------------------|------------------|-------|---------|
| ohr-bench | 8,561 | 📄 Born-digital (100%) | **MOS**: 1.2-4.8 (μ=3.1)<br>**Overall**: 0.15-0.95 | 🖨️ Printed (85%)<br>✍️ Handwritten (15%) | Blur (65%), Noise (45%),<br>Compression (35%) | 6,849 train | Research |
| diqa-5000 | 5,500 | 🖨️ Scanner (70%)<br>📱 Camera (30%) | **MOS**: 1.0-5.0 (μ=2.9)<br>**Overall**: 0.10-1.00 | 🖨️ Printed (100%) | Skew (40%), Low-contrast (35%),<br>Blur (30%), Noise (25%) | 4,400 train | Research |
| realdae | 1,200 | 📱 Camera (100%) | **Overall**: 0.20-0.85<br>**Before/After pairs** | 🖨️ Printed (100%) | Shadow (80%), Perspective (60%),<br>Blur (45%), Glare (30%) | All (600 pairs) | Research |

**Key Additions**:

1. **Capture Method** - Icons + percentages showing scanner vs camera vs born-digital distribution
2. **Quality Profile** - MOS range + mean, overall quality score distribution
3. **Content Type** - Printed vs handwritten vs scene text breakdown
4. **Degradations** - Top 3-4 degradation types with prevalence percentages

---

## Metadata Profile Cards (Per-Dataset)

For detailed dataset pages, add comprehensive metadata profile:

### Example: TableBank Metadata Profile

```markdown
#### TableBank - Metadata Profile

**Capture Method Distribution**:
- Born-digital: 100% (LaTeX/Word exports)
- Scanner: 0%
- Camera: 0%

**Resolution Analysis**:
- DPI: 72-300 (μ=150)
- Category: Low (<150): 35%, Medium (150-299): 45%, Standard (300): 20%
- Pixel dimensions: 800×600 to 2400×1800

**Domain Coverage** (3-level taxonomy):
- SCI (Scientific): 85% (SCI>PUB>JOUR: 60%, SCI>PUB>CONF: 25%)
- TEC (Technical): 15% (TEC>REF>MAN: 10%, TEC>REF>DOC: 5%)

**Structure Characteristics**:
- Text Density: Dense (70%), Moderate (25%), Sparse (5%)
- Layout Type: Tabular (100%)
- Element Types: Table (100%), Caption (80%), Text (40%)

**Quality Profile**:
- Overall Score: 0.85-1.00 (μ=0.93) - very clean dataset
- Common Degradations:
  - Compression artifacts: 12% (mild)
  - Slight blur: 8% (mild)
  - None detected: 80%

**Language/Script Distribution**:
- English/Latin: 95% (primary)
- Multi-script (Latin+Math): 5%
- RTL scripts: 0%

**Text Scope**:
- Scope: Page-level (100%)
- Content Type: Printed (100%), Born-digital (100%)
- Estimated chars: 200-2000 per table, 1000-5000 per page

**Paper Size**:
- A4: 40%
- Letter: 55%
- Custom (PDF crop): 5%

**Content Flags** (% of dataset):
- has_table: 100%
- has_formula: 15%
- has_handwriting: 0%
- has_signature: 0%
- has_figure: 25%

**Training Suitability Matrix**:
✅ **Excellent for**: Table detection, layout analysis, born-digital IQA
⚠️ **Limited for**: Degradation detection (very clean), handwriting, multi-script
❌ **Not suitable for**: Camera capture artifacts, scanner degradation, non-tabular layouts
```

---

## Quick Reference Sections to Enhance

### 1. "Datasets by Training Purpose" Tables

**Add columns**:

- **Capture Method** (icons: 📄 born-digital, 🖨️ scanner, 📱 camera, 🎨 synthetic)
- **Quality Range** (min-max-mean overall_score)
- **Primary Degradations** (top 3 types with %)
- **Content Mix** (printed/handwritten/scene text %)

**Example Row**:

```
| ohr-bench | 8,561 | 📄 100% | 0.15-0.95 (μ=0.45) | Blur 65%, Noise 45%, Compression 35% | 🖨️ 85% / ✍️ 15% | 6,849 train | Research |
```

### 2. New Section: "Dataset Characteristics Matrix"

**Purpose**: Quick filtering by metadata characteristics

```markdown
## Dataset Characteristics Matrix

### By Capture Method

| Capture Method | Datasets | Total Images | Primary Use Cases |
|----------------|----------|--------------|-------------------|
| 📄 **Born-Digital** | tablebank, pubtabnet, doclaynet, im2latex, docsynth | ~1.2M | Layout detection, clean IQA baseline, table structure |
| 🖨️ **Scanner (Flatbed/ADF)** | funsd, tobacco800, dibco, rvl_cdip | ~19K | Degradation detection, archival quality, real scans |
| 📱 **Camera (Professional)** | realdae, smartdoc-qa, midv500 | ~9K | Mobile capture, shadow/perspective, real-world degradation |
| 📱 **Camera (Smartphone)** | smartdoc-qa subset | ~2K | Consumer-grade capture, low-light, motion blur |
| 🎨 **Synthetic** | synth-multiscript-250k, hindi-synth, iqa_phase7_165k | ~495K | Controlled degradation, script diversity, augmentation |

### By Domain Coverage

| Domain | Datasets | Total Images | Subdomains Covered |
|--------|----------|--------------|-------------------|
| 📊 **Financial (FIN)** | fintabnet, financebench, bhutan-afs, invoices | ~152K | Annual reports, financial tables, invoices, tax forms |
| 🔬 **Scientific (SCI)** | pubtabnet, tablebank, mathverse, im2latex | ~856K | Research papers, academic tables, math formulas |
| 📚 **Educational (EDU)** | multimodal-textbook, mathverse | ~8K | Textbooks, STEM diagrams, educational content |
| 🏛️ **Administrative (ADM)** | funsd, nist-sd2, nist-sd6, sroie | ~14K | Forms, receipts, tax documents, administrative records |
| 📰 **General (UNK)** | rvl_cdip, tobacco800, historical-degraded | ~18K | Mixed document types, archival scans |

### By Quality Distribution

| Quality Range | Datasets | Total Images | Typical Degradations |
|---------------|----------|--------------|---------------------|
| **High (0.8-1.0)** | tablebank, pubtabnet, doclaynet, im2latex | ~1M | Minimal degradation, born-digital clean |
| **Medium (0.5-0.8)** | ohr-bench, diqa subset, rvl_cdip | ~30K | Moderate blur/noise, scanner artifacts |
| **Low (0.2-0.5)** | dibco, tobacco800, historical-degraded, diqa subset | ~3K | Severe degradation, aging, archival scans |
| **Mixed (0.1-1.0)** | diqa-5000, iqa_phase7_165k, synth-multiscript-250k | ~420K | Full quality spectrum for IQA training |

### By Text Density

| Density | Datasets | Total Images | Characteristics |
|---------|----------|--------------|----------------|
| **Sparse** | signatr6k, im2latex, scene text subset | ~75K | Minimal text, single words/formulas, signatures |
| **Moderate** | funsd, sroie, invoices, receipts | ~5K | Forms, structured documents, mixed density |
| **Dense** | tablebank, pubtabnet, rvl_cdip, scientific papers | ~950K | Paragraph-heavy, dense text, research papers |

### By Layout Complexity

| Layout Type | Datasets | Total Images | Use Cases |
|-------------|----------|--------------|-----------|
| **Single Column** | historical-degraded, tobacco800, dibco | ~3K | Simple layouts, historical docs, degradation focus |
| **Multi Column** | rvl_cdip, scientific papers subset | ~500K | Journals, newspapers, complex layouts |
| **Tabular** | tablebank, pubtabnet, fintabnet | ~944K | Table detection, structure extraction |
| **Form-Based** | funsd, nist-sd2, sroie | ~8K | Form understanding, key-value extraction |
| **Complex/Mixed** | doclaynet, omnidocbench, financebench | ~135K | Multi-element layouts, nested structures |

### By Content Flags

| Content Type | Datasets (% with flag) | Total Images | Notes |
|--------------|----------------------|--------------|-------|
| **has_table** | tablebank (100%), pubtabnet (100%), fintabnet (100%), doclaynet (60%), rvl_cdip (15%) | ~1.1M | Table-centric vs mixed documents |
| **has_formula** | im2latex (100%), mathverse (95%), multimodal-textbook (40%), tablebank (15%) | ~130K | Math-heavy content |
| **has_handwriting** | hasy (100%), nist-sd19 (100%), nist-sd6 (80%), nepali-handwritten (100%), pucit-ohul (100%) | ~190K | Handwriting detection training |
| **has_signature** | signatr6k (100%), funsd (25%), nist-sd6 (10%) | ~15K | Signature detection/removal |
| **has_figure** | doclaynet (55%), multimodal-textbook (70%), scientific papers (45%) | ~450K | Figure/image detection |

### By Script Diversity

| Script Family | Datasets | Total Images | Scripts Covered |
|---------------|----------|--------------|----------------|
| **Latin-only** | tablebank, pubtabnet, funsd, rvl_cdip, tobacco800 | ~1.3M | English, European languages |
| **CJK** | cc-ocr, mlt19 subset, synth-multiscript-250k subset | ~280K | Hans, Hant, Jpan, Kore |
| **Indic** | hindi-synth, nepali-handwritten, synth-multiscript-250k subset | ~90K | Deva, Beng, Gujr, Taml, Telu, Knda |
| **Arabic/RTL** | arabic-docs, yarmouk, synth-multiscript-250k subset | ~28K | Arab, Hebr |
| **Multi-script** | synth-multiscript-250k (27 scripts), mlt19 (10), mdiw13 (13) | ~560K | Comprehensive script coverage |

### By Text Scope

| Scope Level | Datasets | Total Images | Granularity |
|-------------|----------|--------------|-------------|
| **Character-level** | hasy, nist-sd19, im2latex (formula symbols) | ~178K | Symbol/character recognition |
| **Word-level** | mlt19, mdiw13, cc-ocr, scene text datasets | ~390K | Word spotting, text detection |
| **Line-level** | historical-degraded, dibco, tobacco800 | ~3K | OCR line extraction |
| **Paragraph-level** | doclaynet, rvl_cdip, scientific papers | ~550K | Text block segmentation |
| **Page-level** | tablebank, pubtabnet, financebench | ~1M | Full-page layout analysis |
| **Document-level** | omnidocbench (metadata), financebench (PDFs) | ~54K | Multi-page document classification |
```

---

## Training Decision Matrix (New Section)

**Purpose**: Map training tasks to optimal dataset combinations based on metadata

```markdown
## Training Decision Matrix

### Task: IQA Model Training (ResNet-18 Student)

**Metadata Requirements**:
- Quality range: Full spectrum (0.1-1.0) for regression
- Degradations: Diverse types (blur, noise, skew, contrast, compression, etc.)
- Capture methods: Scanner + camera + born-digital for generalization
- Content mix: Printed (primary) + handwritten (secondary) for robustness

**Optimal Dataset Combination**:
| Dataset | Contribution | Rationale (Metadata-Driven) |
|---------|-------------|----------------------------|
| iqa_phase7_165k | **Base training (70%)** | Synthetic with controlled degradation spectrum (0.1-1.0), 8 IQA dimensions, all capture methods simulated |
| diqa-5000 (train) | **Real-world grounding (15%)** | Real degradation patterns, scanner+camera mix, human MOS scores for calibration |
| ohr-bench (train) | **OCR-specific bias (10%)** | Born-digital + synthetic, OCR-relevant degradations, text-heavy content |
| realdae (train) | **Camera-specific patterns (5%)** | Real camera artifacts (shadow, perspective), before/after pairs for delta learning |

**Expected Coverage** (from aggregated Layer 2 metadata):
- Capture methods: Born-digital (40%), Synthetic (35%), Scanner (15%), Camera (10%)
- Quality distribution: Low (25%), Medium (40%), High (35%)
- Degradation types: Blur (65%), Noise (55%), Compression (45%), Skew (35%), Contrast (30%), Shadow (15%)
- Content: Printed (85%), Handwritten (15%), Scene text (5%)
- Domains: SCI (40%), UNK (30%), FIN (15%), EDU (10%), ADM (5%)

---

### Task: Layout Detection (YOLOv10-doc, 11 DocLayNet Classes)

**Metadata Requirements**:
- Layout types: Diverse (single/multi-column, tabular, form-based, complex)
- Element types: All 11 DocLayNet classes (Caption, Footnote, Formula, List-Item, Page-Footer, Page-Header, Picture, Section-Header, Table, Text, Title)
- Domains: Scientific, financial, administrative for variety
- Quality: Clean to moderate (0.5-1.0) to avoid noise interfering with layout learning

**Optimal Dataset Combination**:
| Dataset | Contribution | Rationale (Metadata-Driven) |
|---------|-------------|----------------------------|
| doclaynet (train) | **Base training (60%)** | All 11 classes, diverse layouts (single/multi-column, complex), domains (SCI, FIN, ADM), quality 0.7-1.0 |
| pubtabnet (train) | **Table specialization (25%)** | Tabular layouts, table structure ground truth, scientific domain, quality 0.8-1.0 |
| tablebank (train) | **Table diversity (10%)** | Born-digital tables (LaTeX/Word), mixed text density, quality 0.85-1.0 |
| fintabnet | **Domain balance (5%)** | Financial tables, different layout patterns, quality 0.7-1.0 |

**Expected Coverage**:
- Layout types: Tabular (40%), Multi-column (35%), Single-column (15%), Complex (10%)
- Domains: SCI (65%), FIN (20%), TEC (10%), ADM (5%)
- Element coverage: Table (85%), Text (100%), Caption (60%), Formula (20%), Picture (35%), Headers/Footers (45%)
- Quality: Clean (0.8-1.0): 70%, Moderate (0.5-0.8): 30%

---

### Task: Script Classification (SigLIP, 27 Scripts)

**Metadata Requirements**:
- Script diversity: All 27 target scripts with balanced representation
- Script families: Latin, CJK, Indic, Arabic, Cyrillic, other
- Text scope: Word-level to paragraph-level (not character-only)
- Multi-script documents: Single-script (60%), 2-script (30%), 3+ script (10%)
- Quality: Mixed (synthetic clean + real degraded) for robustness

**Optimal Dataset Combination**:
| Dataset | Contribution | Rationale (Metadata-Driven) |
|---------|-------------|----------------------------|
| synth-multiscript-250k | **Base training (60%)** | 27 scripts, controlled multi-script distribution (35% single, 45% two-script, 20% three+), synthetic quality 0.2-0.9, 8 IQA dimensions |
| mdiw13 (train) | **Real-world validation (25%)** | 13 scripts, word-level ground truth, real degradation, competition-quality annotations |
| mlt19 (train) | **Scene text diversity (10%)** | 10 languages, scene text (different domain), word-level boxes, quality 0.4-0.9 |
| arabic-docs + hindi-synth + cc-ocr | **Script-specific boosting (5%)** | Underrepresented scripts (Arab, Deva, CJK), additional samples for balance |

**Expected Coverage** (script distribution from Layer 2 metadata):
- Latin: 25%
- CJK (Hans/Hant/Jpan/Kore): 20%
- Indic (Deva/Beng/Gujr/Taml/Telu/Knda): 18%
- Arabic: 12%
- Cyrillic: 8%
- Other (Tibt, Khmr, Mymr, Armn, Hebr, Thai, etc.): 17%
- Multi-script documents: 40%
```

---

## Implementation Plan

### Phase 1: Aggregate Layer 2 Metadata (Week 1)

- [ ] Create aggregation script to compute per-dataset statistics from Layer 2 JSON files
- [ ] Extract distributions for: capture_method, quality scores, degradation types, domains, layout types, content flags, language/script, text scope
- [ ] Generate summary JSON: `metadata_registry/aggregates/{dataset_name}_stats.json`

### Phase 2: Update Quick Reference Tables (Week 1-2)

- [ ] Add "Capture Method" column with icons and percentages
- [ ] Add "Quality Range" column with min-max-mean
- [ ] Add "Primary Degradations" column with top 3 types
- [ ] Add "Content Mix" column with printed/handwritten/scene text %

### Phase 3: Add Metadata Characteristics Matrix (Week 2)

- [ ] Create "By Capture Method" table
- [ ] Create "By Domain Coverage" table
- [ ] Create "By Quality Distribution" table
- [ ] Create "By Text Density" table
- [ ] Create "By Layout Complexity" table
- [ ] Create "By Content Flags" table
- [ ] Create "By Script Diversity" table
- [ ] Create "By Text Scope" table

### Phase 4: Add Training Decision Matrix (Week 3)

- [ ] Document metadata requirements for each training task
- [ ] Provide dataset combinations with metadata-driven rationale
- [ ] Show expected coverage from aggregated metadata

### Phase 5: Add Metadata Profile Cards (Ongoing)

- [ ] Generate per-dataset profile cards from aggregated stats
- [ ] Add to DATASET_CATALOG.md for each dataset

---

## Aggregation Script Example

```python
# scripts/aggregate_layer2_metadata.py

import json
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List

def aggregate_dataset_metadata(dataset_name: str, layer2_dir: Path) -> Dict:
    """Aggregate Layer 2 metadata for a dataset."""

    layer2_files = list(layer2_dir.glob(f"{dataset_name}_*.json"))

    stats = {
        "dataset_name": dataset_name,
        "total_samples": len(layer2_files),
        "capture_methods": Counter(),
        "quality_scores": [],
        "degradation_types": Counter(),
        "domains": Counter(),
        "layout_types": Counter(),
        "text_densities": Counter(),
        "script_codes": Counter(),
        "script_families": Counter(),
        "content_flags": defaultdict(int),
        "text_scopes": Counter(),
        "paper_sizes": Counter(),
    }

    for filepath in layer2_files:
        with open(filepath) as f:
            metadata = json.load(f)

        data = metadata["data"]

        # Capture method
        if "capture_method" in data:
            stats["capture_methods"][data["capture_method"]["method"]] += 1

        # Quality scores
        if "quality" in data and data["quality"].get("overall_score"):
            stats["quality_scores"].append(data["quality"]["overall_score"])

        # Degradations
        if "quality" in data and "degradations" in data["quality"]:
            for deg in data["quality"]["degradations"]:
                stats["degradation_types"][deg["type"]] += 1

        # Domains
        if "domain" in data:
            stats["domains"][data["domain"]["level1"]] += 1

        # Structure
        if "structure" in data:
            if data["structure"].get("layout_type"):
                stats["layout_types"][data["structure"]["layout_type"]] += 1
            if data["structure"].get("text_density"):
                stats["text_densities"][data["structure"]["text_density"]] += 1

        # Language/Script
        if "language" in data:
            stats["script_codes"][data["language"]["script_code"]] += 1
            stats["script_families"][data["language"]["script_family"]] += 1

        # Content flags
        if "content_flags" in data:
            for flag, value in data["content_flags"].items():
                if value is True and flag.startswith("has_"):
                    stats["content_flags"][flag] += 1

        # Text scope
        if "text_scope" in data:
            stats["text_scopes"][data["text_scope"]["scope"]] += 1

        # Paper size
        if "paper_size" in data:
            stats["paper_sizes"][data["paper_size"]["detected_size"]] += 1

    # Compute summary statistics
    if stats["quality_scores"]:
        stats["quality_summary"] = {
            "min": min(stats["quality_scores"]),
            "max": max(stats["quality_scores"]),
            "mean": sum(stats["quality_scores"]) / len(stats["quality_scores"]),
            "median": sorted(stats["quality_scores"])[len(stats["quality_scores"]) // 2]
        }

    # Convert counters to percentages
    for key in ["capture_methods", "degradation_types", "domains", "layout_types", "text_densities", "script_codes", "script_families", "text_scopes", "paper_sizes"]:
        total = sum(stats[key].values())
        if total > 0:
            stats[f"{key}_pct"] = {k: round(v / total * 100, 1) for k, v in stats[key].items()}

    # Content flags as percentages
    stats["content_flags_pct"] = {k: round(v / stats["total_samples"] * 100, 1) for k, v in stats["content_flags"].items()}

    return stats

# Run for all datasets
output_dir = Path("metadata_registry/aggregates/")
output_dir.mkdir(exist_ok=True)

for dataset_name in DATASET_REGISTRY.keys():
    stats = aggregate_dataset_metadata(dataset_name, Path("metadata_registry/json/"))
    with open(output_dir / f"{dataset_name}_stats.json", "w") as f:
        json.dump(stats, f, indent=2)
    print(f"✅ Aggregated metadata for {dataset_name}")
```

---

## Benefits

### For Training Decisions

1. **Quantitative Filtering**: "Show me datasets with >50% camera capture and quality <0.5" → immediate answers
2. **Coverage Analysis**: See exact script/domain/degradation coverage before training
3. **Bias Detection**: Identify under-represented capture methods, domains, or quality levels
4. **Dataset Balancing**: Mix datasets to achieve target metadata distributions

### For LLM Context Efficiency

1. **Metadata-Rich Tables**: Claude can answer "which datasets have tables?" by reading table percentages, not loading full catalog
2. **Training Recipes**: Claude can build training datasets based on metadata requirements, not guesswork
3. **Gap Analysis**: Claude can identify "we need more camera-captured Arabic handwriting" from metadata gaps

### For Documentation Quality

1. **Provenance**: All statistics traceable to Layer 2 metadata
2. **Up-to-date**: Regenerate aggregates when Layer 2 metadata updated
3. **Reproducible**: Aggregation script ensures consistency

---

**Next Steps**: Review this proposal and decide which enhancements to implement first.
