#### Bhutan Financial Statements

> **Quick Stats**: 125 pages | Government financial + tax documents | Real-world complex tables | Public domain
>
> **License**: Public Domain | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Bhutan Government Documents (AFS 2024-25 + Tax Act 2021) |
| **Version** | 2024-25 / 2021 |
| **Release Date** | 2024 |
| **Maintainer** | Royal Government of Bhutan |
| **Download** | [AFS 2024-25](https://mof.gov.bt/wp-content/uploads/2025/12/AFS_2024-25-2.pdf), [Tax Act 2021](https://mof.gov.bt/wp-content/uploads/2025/04/Tax-Act-of-Bhutan-2021.pdf) |
| **License** | Public Domain (Government Document) |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/bhutan_financial/` |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Pages** | 125 (10 exclusions applied) |
| **Source Documents** | AFS 2024-25 (115 pages) + Tax Act 2021 (10 pages) |
| **File Format** | PNG (converted from PDF) |
| **Resolution** | 300 DPI |
| **Source Format** | PDF (official government publication) |

##### Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | Government financial reporting + tax legislation |
| **Document Types** | Balance sheets, income statements, schedules, tax code articles |
| **Language** | English |
| **Table Characteristics** | Multi-column layouts, footnotes, decimal-aligned numbers |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Born-digital (official government PDF) |
| **Baseline Quality** | High (professional typesetting) |
| **Table Complexity** | **HIGH** - Financial tables with merged cells, footnotes |
| **Layout Complexity** | **HIGH** - Multi-column, mixed content |
| **Skew Sensitivity** | LOW - Born-digital, no scanning artifacts |
| **Key Value** | Real-world government financial document samples |

##### Training Value

- **Strengths**: Real government documents, complex table layouts, public domain, document diversity (financial + legal)
- **Weaknesses**: Single source (one country), limited quantity
- **Complementary Datasets**: FinTabNet for financial diversity, DocLayNet for layout variety
- **Phase 10A Role**: 125 government document samples for orientation detection training

##### Data Quality Notes

- **Excluded Blank (3)**: AFS pages 3, 5, 125 - moved to `_excluded_blank/`
- **Excluded Rotated (7)**: AFS pages 94-100 - moved to `_excluded_rotated/` to reduce rotated-table prevalence
- **Remaining Rotated Table Pages (29)**: Pages 66-73, 77-78, 101-116, 122-124 contain portrait pages with 90-degree rotated tables. Kept as edge cases (23.2% of subset vs original 29.5%).

##### Project Usage

- **Path**: `01_base_data/documents/bhutan_financial/`
- **Phase(s)**: Phase 10A (Orientation Detection)
- **Purpose**: Real-world government document training, complex table samples
- **Added**: 2025-01-24
- **Quality Review**: 2025-01-25 (10 total exclusions: 3 blank + 7 rotated)
- **Parser**: ⚠️ GenericParser (minimal metadata only) | `src/image_preprocessing_detector/annotation/parsers/generic.py`

---
