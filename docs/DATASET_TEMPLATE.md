# Dataset Documentation Template

> **Version**: 1.0.0
> **Last Updated**: 2025-12-17
> **Purpose**: Standardized template for comprehensive IQA dataset documentation
> **Consensus**: Validated by Gemini 3 Pro (9/10) and Claude Sonnet 4.5 (8/10)

---

## Template Structure

Each dataset entry should follow this structure. For the main DATASET_CATALOG.md, use the
**Quick Reference** format. For detailed documentation, create individual files in `docs/datasets/`.

---

## Quick Reference Format (for DATASET_CATALOG.md)

Use this condensed format in the main catalog for rapid dataset selection:

```markdown
### [Dataset Name]

> **Quick Stats**: [count] images | [source_type] | [primary IQA characteristics]
>
> **License**: [license] | **Commercial Use**: Yes/No/Restricted

- **Path**: `01_base_data/category/dataset_name/`
- **Paper**: [Title (Year)](link)
- **IQA Profile**: [blur_sensitive, high_contrast, etc.]
- **Project Usage**: Phase X training/validation/benchmark

[2-3 sentence description of dataset and its IQA relevance]
```

---

## Detailed Dataset Card Template

For individual dataset files (`docs/datasets/[dataset_name].md`):

```markdown
---
# YAML Frontmatter (machine-readable)
dataset_id: dataset_name
version: "1.0"
license: CC-BY-4.0
commercial_use: true
iqa_profiles:
  - blur_sensitive
  - high_contrast
baseline_quality: 8.2
training_suitable: true
benchmark_suitable: false
documentation_status: complete  # complete | partial | inferred
---
```

### [Dataset Name]

> **Quick Stats**: 260,025 images | Born-digital | High contrast | Blur-sensitive | Grid lines

#### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Complete official dataset name |
| **Version** | Version number (e.g., v1.0, v2.1) |
| **Release Date** | YYYY-MM-DD |
| **Last Updated** | YYYY-MM-DD |
| **Maintainer** | Organization (e.g., Microsoft Research) |
| **Paper** | [Citation Title (Year)](paper_url) |
| **Repository** | [Official Source](repo_url) |
| **License** | License type with [link](license_url) |
| **Commercial Use** | Yes / No / Restricted (explain) |
| **Documentation Status** | Complete / Partial / Inferred |

#### 2. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Phase 7 training |
| **Purpose** | Training / Validation / Testing / Benchmark |
| **Local Path** | `01_base_data/tables/tablebank/` |
| **Subset Used** | Full dataset / Specific subset (explain) |
| **Preprocessing** | Required steps before use |
| **Dataloader** | `src/data/tablebank_loader.py` |

#### 3. Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 260,025 |
| **Training Split** | 208,000 (80%) |
| **Validation Split** | 26,000 (10%) |
| **Test Split** | 26,025 (10%) |
| **Image Dimensions** | 600-2000px (variable) |
| **Resolution (DPI)** | 72-300 (variable) |
| **File Format(s)** | JPG |
| **Color Space** | RGB / Grayscale |
| **Total Size on Disk** | 45.2 GB |
| **Annotation Format** | JSON / XML / None |

##### Directory Structure

```text
tablebank/
├── train/
│   ├── word/           # 78K Word-extracted tables
│   └── latex/          # 130K LaTeX-rendered tables
├── val/
└── test/
```

##### Baseline Quality Metrics

> **Source**: [Empirically Derived] from 1000-sample profiling

| Metric | Mean ± Std | Min | Max | Percentiles (25/50/75) |
|--------|------------|-----|-----|------------------------|
| **Entropy** | 7.2 ± 0.8 | 5.1 | 7.9 | 6.7 / 7.3 / 7.8 |
| **Edge Density** | 0.15 ± 0.06 | 0.02 | 0.34 | 0.11 / 0.14 / 0.19 |
| **Contrast Ratio** | 45 ± 12 | 18 | 89 | 38 / 44 / 52 |
| **Laplacian Variance** | 320 ± 180 | 12 | 890 | 185 / 290 / 420 |
| **Aspect Ratio** | 1.2 ± 0.4 | 0.5 | 3.2 | 0.9 / 1.1 / 1.4 |

#### 4. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | Scientific publications, financial documents |
| **Document Types** | Tables only (isolated table regions) |
| **Language(s)** | English (98%), Other (2%) |
| **Temporal Range** | 2010-2020 publications |
| **Acquisition Method** | Word document extraction, LaTeX rendering |

##### Class/Category Distribution

| Category | Count | Percentage |
|----------|-------|------------|
| Word-extracted | 78,000 | 30% |
| LaTeX-rendered | 182,025 | 70% |

#### 5. IQA Profile

##### 5.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Born-digital (rendered, not scanned) |
| **Capture Device** | N/A (programmatic extraction) |
| **Original Quality** | Clean, no scanning artifacts |
| **Compression** | JPEG quality 85-95 |
| **Known Artifacts** | Minor JPEG blocking on some samples |

##### 5.2 Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Blur** | HIGH | Grid lines and small text extremely sensitive |
| **Noise** | MEDIUM | High contrast masks moderate noise |
| **Skew** | HIGH | Cell alignment degrades rapidly with rotation |
| **Contrast** | LOW | Already high contrast (black on white) |
| **Compression** | HIGH | JPEG artifacts destroy thin lines |

##### 5.3 Document Feature Characteristics

| Feature | Presence | IQA Implications |
|---------|----------|------------------|
| **Text Size Range** | 8-14pt typical | Small text sensitive to blur |
| **Line/Grid Density** | High | Grid lines are blur detection targets |
| **Font Diversity** | Low (standard fonts) | Consistent OCR behavior expected |
| **Mathematical Notation** | Common in LaTeX subset | Subscripts/superscripts fragile |
| **Color Usage** | Minimal (B&W) | Grayscale processing sufficient |

##### 5.4 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | HIGH - Large volume, clean ground truth for table quality |
| **Unique Characteristics** | Grid line detection, cell boundary sharpness |
| **Complementary Datasets** | Combine with PubTabNet for scientific tables |
| **Benchmark Suitability** | MEDIUM - Born-digital only, lacks real scan artifacts |
| **Known Limitations** | No handwritten content, limited degradation variety |

#### 6. Known Issues & Limitations

- **Quality Bias**: Born-digital only; doesn't represent scanned document quality
- **Domain Bias**: Heavy scientific/financial focus; limited document variety
- **Annotation Gaps**: Table structure annotations exist but not IQA-specific labels
- **Class Imbalance**: 70% LaTeX vs 30% Word creates rendering style bias
- **Resolution Variance**: Wide DPI range requires normalization

#### 7. Representative Samples

> Include 2-3 example images showing typical quality and any notable artifacts

| Sample | Description | Notable Features |
|--------|-------------|------------------|
| ![Sample 1](../assets/datasets/tablebank_sample1_thumb.png) | Typical LaTeX table | Clean grid, standard font |
| ![Sample 2](../assets/datasets/tablebank_sample2_thumb.png) | Complex nested table | Dense content, small text |
| ![Sample 3](../assets/datasets/tablebank_sample3_thumb.png) | Financial table | Decimal alignment, footnotes |

#### 8. References

##### Primary Citation

```bibtex
@inproceedings{li2020tablebank,
  title={TableBank: Table Benchmark for Image-based Table Detection and Recognition},
  author={Li, Minghao and others},
  booktitle={LREC},
  year={2020}
}
```

##### Related Works

- [PubTabNet](pubtabnet.md) - Complementary scientific table dataset
- [FinTabNet](fintabnet.md) - Financial tables with similar structure

##### Leaderboards

- [Papers With Code - Table Detection](https://paperswithcode.com/task/table-detection)

---

## Documentation Status Markers

Use these markers to indicate documentation completeness:

| Marker | Meaning |
|--------|---------|
| `[Official]` | Information from official documentation/paper |
| `[Empirically Derived]` | Computed from actual dataset samples |
| `[Inferred]` | Reasoned from available evidence |
| `[NEEDS_PROFILING]` | Section requires empirical analysis |
| `[NEEDS_VERIFICATION]` | Information needs confirmation |

---

## Automation Notes

### Profiling Script

For datasets lacking official documentation, use the profiling script:

```bash
# Generate baseline quality metrics for a dataset
python scripts/profile_dataset.py \
  --input /mnt/e/image_detection/01_base_data/tables/tablebank/ \
  --sample-size 1000 \
  --output docs/datasets/tablebank_profile.json
```

### Metrics Computed

The profiling script computes:

- **Entropy**: Shannon entropy of grayscale histogram
- **Edge Density**: Canny edge pixel ratio
- **Contrast Ratio**: (max - min) / mean intensity
- **Laplacian Variance**: Blur proxy (higher = sharper)
- **Aspect Ratio**: Width / height distribution
- **File Size per Pixel**: Compression quality indicator

---

## Template Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-17 | Initial template based on Gemini/Claude consensus |
