---
dataset_id: im2latex
version: "1.0"
license: CC0
commercial_use: true
iqa_profiles:
  - born_digital
baseline_quality: null
training_suitable: true
benchmark_suitable: false
documentation_status: complete
---

#### im2latex-100k

> **Quick Stats**: 103,556 formulas | LaTeX rendered | Transparent background | ArXiv source
>
> **License**: CC0 (Public Domain) | **Commercial Use**: Yes

##### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | im2latex-100k: Image-to-LaTeX Dataset |
| **Version** | 1.0 |
| **Maintainer** | Harvard NLP (Yuntian Deng) |
| **Paper** | [What You Get Is What You See (arXiv:1609.04938)](https://arxiv.org/abs/1609.04938) |
| **Repository** | [GitHub: harvardnlp/im2markup](https://github.com/harvardnlp/im2markup) |
| **Zenodo** | [im2latex-100k](https://zenodo.org/records/56198) |
| **License** | CC0 (Creative Commons Zero) |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/im2latex/` |
| **Documentation Status** | Complete |

##### 2. Source Data Inventory

###### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | PNG | Rendered LaTeX formulas (transparent background) |
| **Annotations** | TXT (LST) | LaTeX source code + split membership |
| **Metadata** | Implicit | Formula complexity from LaTeX length |
| **Supplementary** | README | Dataset documentation, license |

###### 2.2 Dataset Split Locations

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `formula_images/train/` | `im2latex_train.lst` | 83,883 | ✅ |
| **Validation** | `formula_images/validate/` | `im2latex_validate.lst` | 9,319 | ✅ |
| **Test** | `formula_images/test/` | `im2latex_test.lst` | 10,354 | ✅ |

**Split Organization Pattern**: `by_folder` (train/val/test directories)

**Notes**:

- Split files map image_id → formula_id
- Alternative structure uses single `images/` directory with same split files
- Formula source file (`im2latex_formulas.lst`) is shared across all splits

###### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **LaTeX Source** | TXT (line-indexed) | Image-level | Full LaTeX formula code (38-997 chars) |
| **Split Membership** | TXT (space-separated) | Image-level | Train/validate/test assignment |
| **Formula ID** | INT | Image-level | Line number in formulas.lst (0-indexed) |
| **Sequence Length** | Implicit | Image-level | Character count of LaTeX source |

###### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | README / Zenodo | License (CC0), citation, split counts |
| **Image-level** | Filename | Numeric ID (e.g., `0.png`, `1.png`) |
| **Annotation-level** | formulas.lst | LaTeX source code (line-indexed) |
| **Formula-level** | Implicit | Sequence length, symbol count, complexity |

###### 2.5 Annotation Schema Details

**Format**: Text files with line-indexed formulas and space-separated mappings

```
# im2latex_formulas.lst (103,556 lines)
Line 0: \alpha + \beta = \gamma
Line 1: \int_{0}^{\infty} e^{-x} dx
Line 2: \sum_{i=1}^{n} i^2 = \frac{n(n+1)(2n+1)}{6}
...

# im2latex_train.lst (83,883 entries)
0 42    ← Image ID, Formula ID (space-separated)
1 137
2 8900
...
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image_id` | int | Yes | Extracted from filename (e.g., `0.png` → 0) |
| `formula_id` | int | Yes | Line number in formulas.lst (0-indexed) |
| `latex_source` | str | Yes | LaTeX code at formula_id line |
| `split` | str | Yes | "train", "validate", or "test" |

###### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ LaTeX source | `latex_source` | **High** | Full formula rendering code |
| ✅ Split membership | `split` | **High** | Train/validate/test |
| ✅ Formula ID | `formula_id` | **High** | Line number in formulas.lst |
| ✅ Sequence length | `sequence_length` | Medium | Computed from LaTeX source |
| ✅ Symbol count | `symbol_count` | Medium | Regex count of LaTeX commands |
| ⚠️ Complexity | `complexity` | Low | Heuristic (simple/medium/complex) |

**Legend**: ✅ Directly usable | ⚠️ Heuristic derivation | ❌ Not available

###### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Synthetic |
| **Provenance Tier** | Tier 0 (Exact) |
| **Quality Assurance** | LaTeX rendering pipeline, exact by construction |
| **GT Label Coverage** | 100% |

##### 3. Project Usage

- **Path**: `01_base_data/formulas/im2latex/`
- **Purpose**: Mathematical notation IQA, compression sensitivity
- **Parser**: [`Im2latexParser`](../src/image_preprocessing_detector/annotation/parsers/formula/im2latex.py) | ✅ Complete

##### 5. Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Formulas** | 103,556 sequences |
| **Training Split** | 83,883 (81%) |
| **Validation Split** | 9,319 (9%) |
| **Test Split** | 10,354 (10%) |
| **Sequence Length** | 38-997 chars (mean: 118, median: 98) |
| **File Format** | PNG (transparent background) |
| **Download Size** | 306.8 MB total |

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/formulas/im2latex/` | ✅ Available | 10,000 PNG files |
| **Text/GT** | Native annotations | ✅ Available | TXT: LaTeX formula source code (`im2latex_formulas.lst`, line-indexed) |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |

##### Benchmark Performance (Image-to-LaTeX)

| Model | BLEU Score | Notes |
|-------|------------|-------|
| Im2Latex (baseline) | 0.67 | Encoder-decoder |
| Transformer-based | Higher | Better robustness |
| TexTeller | Higher than 0.67 | State-of-the-art baseline |
| Best reported | **89%** | Recent state-of-the-art |

*Evaluation: corpus BLEU (1-4 grams), Levenshtein Edit Distance, Exact Match*

##### 5.2 Content Composition

| Content Type | Count | Percentage | Notes |
|--------------|-------|------------|-------|
| **Math Formulas** | 103,556 | 100% | LaTeX-rendered formulas from ArXiv papers |
| Simple (<50 chars) | ~25,889 | 25% [Inferred] | Single operators, Greek letters |
| Medium (50-200 chars) | ~62,134 | 60% [Inferred] | Fractions, sums, integrals |
| Complex (>200 chars) | ~15,533 | 15% [Inferred] | Matrices, multi-line equations |

**Complexity Distribution** [Inferred]:

- Based on parser heuristic: `<50 chars = simple`, `50-200 = medium`, `>200 = complex`
- Median formula length: 98 characters (from paper)
- Mean formula length: 118 characters (from paper)
- Range: 38-997 characters (from paper)

**Symbol Types** [Empirically Derived]:

- Greek letters (α, β, γ, δ, ε, θ, λ, μ, π, σ, ω)
- Operators (∑, ∏, ∫, ∂, ∇, √, lim)
- Relations (=, ≠, ≈, ≤, ≥, ∈, ⊂, ⊃, →)
- Brackets ({}, [], (), ⟨⟩, ||)
- Sub/superscripts (x^2, x_i, x_i^j)
- Fractions (\frac{a}{b})
- Matrices (\begin{matrix}...\end{matrix})

##### 5.3 Text Statistics

**LaTeX Source Statistics** [Official]:

| Metric | Value | Source |
|--------|-------|--------|
| **Total Formulas** | 103,556 | Paper |
| **Avg Sequence Length** | 118 characters | Paper |
| **Median Sequence Length** | 98 characters | Paper |
| **Min Sequence Length** | 38 characters | Paper |
| **Max Sequence Length** | 997 characters | Paper |
| **LaTeX Command Density** | ~15% [Inferred] | Estimated from symbol patterns |

**Character Distribution** [Inferred]:

- Alphanumeric: ~50% (variable names, subscripts)
- LaTeX commands: ~15% (backslash commands)
- Special symbols: ~20% (operators, brackets)
- Whitespace: ~15% (spacing, formatting)

**Most Common LaTeX Commands** [Inferred from ArXiv domain]:

1. `\frac` (fractions)
2. `\sum` (summations)
3. `\int` (integrals)
4. `\alpha`, `\beta`, `\gamma` (Greek letters)
5. `\mathbb` (blackboard bold)
6. `^` (superscripts)
7. `_` (subscripts)
8. `\left`, `\right` (delimiters)

**Note**: No OCR text extraction needed - LaTeX source is ground truth "text".

##### 6. IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Rendered LaTeX (born-digital) |
| **Baseline Quality** | Clean (programmatically rendered) |
| **Blur Sensitivity** | **EXTREME** - Small symbols, subscripts |
| **Compression Sensitivity** | **EXTREME** - Thin strokes destroyed by JPEG |
| **Key Challenge** | Dense notation, variable symbol sizes |

##### Training Value

- **Strengths**: Clean ground truth, LaTeX source available, public domain
- **Weaknesses**: Born-digital only, no real degradation
- **Use Case**: Formula rendering quality, compression impact

##### Project Usage

- **Path**: `01_base_data/formulas/im2latex/`
- **Purpose**: Mathematical notation IQA, compression sensitivity
- **Parser**: [`Im2latexParser`](../src/image_preprocessing_detector/annotation/parsers/formula/im2latex.py) | ✅ Complete

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 10,000 (subset) |
| **File Format** | JPEG (100%) |
| **Dimensions** | 320 × 64 px (fixed) |
| **Avg File Size** | 4 KB |
| **Color Space** | RGB |
| **Capture Method** | Born-digital |
| **Domain** | SCI (Scientific) |
| **Content Flags** | Formulas: ✅ 100% |

---

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-16 | **Grade**: B (92.6/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 88.3 | 20% |  |
| Field Validity | 96.3 | 20% |  |
| Doc Completeness | 54.5 | 7% | Below threshold |
| Defect Rate | - | - | Excluded (no data) |
| Cross-Source Agreement | - | - | Excluded (no data) |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **92.6** | | **Grade B** |

###### 11.2 Key Defects

No defect catalog available for this dataset.

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: N/A

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/im2latex/](../../scripts/audit/results/im2latex/)

##### Reliability & Bottlenecks

> **Computed**: 2026-02-16 | **Samples**: 10,000 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 10,000 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `text_quality` | 100.0% | 0.000 |

---

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | ➖ | 0 | — | All formulas rendered upright (0°); no orientation variety |
| MNV4-H2 | skew_reg | ➖ | 0 | — | Programmatic rendering; zero skew by construction |
| MNV4-H3 | resolution_quality_reg | 🟡 | ~10,000 | Pseudo-label | Variable formula sizes (64px height); useful after RQ labeling — spans quality range |
| SIG-G1-1 | blur_score | 🟡 | ~10,000 | Pseudo-label | Extreme blur sensitivity documented (thin strokes); clean baseline with degradation augmentation potential |
| SIG-G1-2 | noise_score | 🟡 | ~10,000 | Pseudo-label | Born-digital, noise-free baseline; useful as low-noise anchor |
| SIG-G1-3 | contrast_score | 🟡 | ~10,000 | Pseudo-label | High-contrast black-on-transparent renders; good contrast anchor |
| SIG-G1-4 | skew_score | ➖ | 0 | — | No skew in rendered output |
| SIG-G1-5 | compression_score | 🟡 | ~10,000 | Pseudo-label | Extreme JPEG sensitivity documented; useful for compression quality head with degradation augmentation |
| SIG-G1-6 | overall_quality | 🟡 | ~10,000 | Pseudo-label | High-quality born-digital renders; provides "good quality" anchor samples |
| SIG-G2-1 | script_cls | 🟡 | ~10,000 | Native (Latn) | Latin class only (math rendered as Latin chars + symbols); unusual math-domain Latin not representative of general Latin text |
| SIG-G3-1 | orientation_cls (post) | ➖ | 0 | — | Same as pre-correction — upright only |
| SIG-G3-2 | skew_reg (post) | ➖ | 0 | — | No skew to correct |
| SIG-G4-1 | handwriting_presence_cls | ✅ | ~10,000 | Native (False) | Programmatically rendered formulas; reliable negative (no handwriting) examples |
| SIG-G4-2 | handwriting_legibility_cls | ❌ | 0 | — | Not applicable — no handwriting present |
| SIG-G4-3 | handwriting_content_type_cls | ❌ | 0 | — | Not applicable — no handwriting present |
| SIG-G4-4 | presence_reg | ❌ | 0 | — | Not applicable — no handwriting present |
| SIG-G4-5 | legibility_reg | ❌ | 0 | — | Not applicable — no handwriting present |
| SIG-G5-1 | capture_method_cls | ✅ | ~10,000 | Native (born_digital) | 100% born_digital; confirmed real signal — contributes to born_digital class in G5-1 |
| SIG-G5-2 | shadow_reg | ❌ | 0 | — | Born-digital renders on transparent/white background; no shadow |
| SIG-G5-3 | warping_reg | ❌ | 0 | — | Flat programmatic renders; no geometric distortion |
| SIG-G5-4 | code_cls | ✅ | ~10,000 | Native (LaTeX) | LaTeX is a markup/programming language; formulas are code content — primary code_cls signal |
| SIG-G5-5 | resolution_quality_reg | 🟡 | ~10,000 | Pseudo-label | Same as MNV4-H3 — variable formula dimensions useful after RQ labeling |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | 🟡 | 100% Latin (Latn); math-domain Latin only — not representative of general Latin document text |
| 2 | Capture method | ✅ | 100% born_digital; homogeneous but valid G5-1 training signal |
| 3 | Document domain | 🟡 | 100% EDU/SCI (ArXiv formulas); single domain — no cross-domain variety |
| 4 | Layout type | ❌ | Formula crops only; no page-level layout variation |
| 5 | Text density | ❌ | Formula-level crops; no meaningful text density variation |
| 6 | Degradation types | ❌ | Clean born-digital renders; zero real degradation |
| 7 | Resolution/DPI range | 🟡 | Variable formula dimensions (64px height fixed, variable width 38-997 char equivalents); limited DPI range |
| 8 | Document age | ❌ | Modern digital only; no aged or historical examples |
| 9 | Text scope | ✅ | 100% formula-level scope; comprehensive mathematical formula coverage |
| 10 | Content flags | ✅ | 100% has_formula; dedicated math formula dataset — strong formula content signal |
| 11 | Binarization status | 🟡 | Black symbols on transparent/white; effectively binarized by construction |
| 12 | Artifact types | ❌ | No scan artifacts, JPEG compression, shadows, or warping present |
| 13 | Color mode | 🟡 | Black-and-white rendered symbols; no color or grayscale variation |
| 14 | Font variety | 🟡 | LaTeX Computer Modern and related math fonts; limited to standard LaTeX font families |

### 13.3 Corpus Role & Constraints

This dataset is the **primary source for the `code_cls` head** (G5-4) given that LaTeX formulas constitute markup/programming language content, and it provides reliable **born_digital** samples for G5-1. Licensed CC0 (public domain) with no usage restrictions. The 10,000-sample annotated subset is the working pool; the full 103,556-formula corpus could expand code_cls coverage. Being born-digital with no degradation, its IQA contribution is limited to providing "clean quality" anchors; augmentation would be required to generate blur/compression/noise signal from this source.
