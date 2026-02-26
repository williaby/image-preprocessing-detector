---
dataset_id: khatt
version: "1.0"
license: academic
commercial_use: false
iqa_profiles:
  - scanner_artifacts
  - varied_quality
baseline_quality: null
training_suitable: true
benchmark_suitable: true
documentation_status: complete
---

#### KHATT (KFUPM Handwritten Arabic TexT)

> **Quick Stats**: ~1,633 images | 1,000 writers | Arabic cursive handwriting | Paragraph-level scans
>
> **License**: Academic Research Only | **Commercial Use**: No

##### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | KHATT: KFUPM Handwritten Arabic TexT Database |
| **Version** | 1.0 (September 2012 Release) |
| **Release Date** | 2012 |
| **Last Updated** | 2024 (HuggingFace mirror) |
| **Maintainer** | King Fahd University of Petroleum and Minerals (KFUPM) |
| **Paper** | [KHATT: Arabic Offline Handwritten Text Database (ICFHR 2012)](https://ieeexplore.ieee.org/document/6424430) |
| **Repository** | [HuggingFace: benhachem/KHATT](https://huggingface.co/datasets/benhachem/KHATT) |
| **License** | Academic Research Only (non-commercial) |
| **Commercial Use** | No |
| **Documentation Status** | Complete |

**Citation**:
> S. A. Mahmoud, I. Ahmad, M. Alshayeb, W. G. Al-Khatib, M. T. Parvez, G. A. Fink, V. Margner, and H. EL Abed, "KHATT: Arabic Offline Handwritten Text Database," In Proceedings of the 13th International Conference on Frontiers in Handwriting Recognition (ICFHR 2012), Bari, Italy, 2012, pp. 447-452, IEEE Computer Society.

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | TIF (original), JPG (converted) | Paragraph-level Arabic handwriting scans |
| **Transcriptions** | TXT | Arabic Unicode text (UTF-8, RTL) |
| **Ground Truth** | XLSX | `Groundtruth-Unicode.xlsx` — full paragraph transcriptions |
| **Loading Script** | Python | `KHATT.py` — HuggingFace dataset loader |

##### 2.2 Dataset Split Locations

| Split | Images Path | Count | Status |
|-------|-------------|-------|--------|
| **Train** | `train/` | ~1,400 | ✅ Available |
| **Validation** | `validation/` | ~233 | ✅ Available |
| **Total** | — | ~1,633 | ✅ |

**Split Organization Pattern**: `by_folder` — separate directories per split

> **Notes**:
>
> - Images downloaded from HuggingFace as ZIP archives (`data/train.zip`, `data/validation.zip`)
> - Original format is TIFF; converted to JPEG 90 quality on extraction
> - Each `.tif` has a companion `.txt` with Arabic Unicode transcription

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Text Transcriptions** | TXT | Paragraph-level | Arabic Unicode (UTF-8, right-to-left) |
| **Ground Truth Table** | XLSX | Paragraph-level | `Groundtruth-Unicode.xlsx` maps image IDs to full text |

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Filename encoding** | Image stem | `{writerID}_Para{paraNum}_{lineNum}` (e.g., `AHTD3A0001_Para2_3`) |
| **Writer identity** | Filename prefix | First 9 chars identify writer (1,000 unique writers) |
| **Dataset-level** | HuggingFace README | License, citation, task description |

##### 2.5 Annotation Schema Details

> **Format**: Per-image TXT companion file with Unicode Arabic paragraph text

```text
AHTD3A0001_Para2_3.tif  ← paragraph scan
AHTD3A0001_Para2_3.txt  ← UTF-8 Arabic text transcription
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `stem` | str | Yes | Image filename without extension |
| `writer_id` | str | Yes | First 9 chars of stem |
| `para_num` | int | Yes | Paragraph index from filename |
| `transcription` | str | Yes | Arabic Unicode from companion .txt |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Arabic text GT | `transcription` | High | UTF-8 Arabic Unicode |
| ✅ Writer identity | `writer_id` | Medium | From filename |
| ✅ Script info | `iso639_language=ar` | High | Arabic, RTL |
| ❌ Bounding boxes | — | Low | Paragraph-level only |
| ❌ Quality scores | — | Low | Compute from IQA analysis |

**Legend**: ✅ Directly usable | ❌ Not available

##### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human Expert (1,000 writers produced self-transcribed samples) |
| **Provenance Tier** | Tier 1 (Human Expert Annotation) |
| **Annotator Details** | 1,000 writers from diverse backgrounds; each writer contributed multiple paragraphs |
| **Quality Assurance** | ICFHR 2012 benchmark dataset — peer-reviewed annotation |
| **GT Label Coverage** | 100% — all images have companion .txt transcription |

---

#### 3. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | OOD evaluation (sub-source 5a: Arabic cursive handwriting) |
| **Purpose** | OOD Arabic cursive HW evaluation for handwriting_presence and handwriting_content_type heads |
| **Local Path** | `01_base_data/handwriting/khatt/` |
| **Subset Used** | All ~1,633 images (train + validation) |
| **Preprocessing** | TIF → JPEG conversion at quality 90 |

#### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | `khatt` (handwriting category) |
| **Parser Status** | ✅ Implemented |
| **Layer 1 Fields** | `transcription` (Arabic Unicode), `writer_id`, `para_num` |
| **Layer 2 Auto-Derived** | `iso639_language=ar`, `script_family=Arab`, `text_direction=rtl` |
| **Config Entry** | `khatt` in dataset config registry |

#### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images (Train)** | `01_base_data/handwriting/khatt/train/` | ✅ Available | ~1,400 JPEG |
| **Images (Val)** | `01_base_data/handwriting/khatt/validation/` | ✅ Available | ~233 JPEG |
| **Ground Truth** | `01_base_data/handwriting/khatt/khatt_groundtruth.tsv` | ✅ Available | TSV with Arabic text |
| **Original ZIPs** | `01_base_data/handwriting/khatt/data/` | ✅ Available | `train.zip`, `validation.zip` |
| **Layer 2 Metadata** | `metadata_registry/json/khatt_layer2.json` | ❌ Not generated | Parser not yet run |

---

#### 4. Dataset Statistics

##### 4.1 Split Coverage

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | ~1,400 | 0 | 0% | ❌ Parser not run |
| **Validation** | ~233 | 0 | 0% | ❌ Parser not run |
| **Total** | ~1,633 | 0 | 0% | ❌ Parser not run |

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | ~1,633 |
| **Training Split** | ~1,400 (86%) |
| **Validation Split** | ~233 (14%) |
| **Unique Writers** | 1,000 |
| **Paragraphs per Writer** | ~1.6 average |
| **Image Dimensions** | Variable (paragraph scans) |
| **Original Format** | TIFF (scanned) |
| **Converted Format** | JPEG quality 90 |
| **Total Size on Disk** | ~14 MB (JPEG) / ~180 MB (original TIFF in ZIPs) |

##### 4.3 Text Statistics

| Metric | Value |
|--------|-------|
| **Script** | Arabic (Naskh/cursive style) |
| **Language** | Arabic (ar) |
| **Granularity** | Paragraph-level images |
| **Transcription Coverage** | 100% (companion .txt per image) |
| **Ground Truth Source** | `Groundtruth-Unicode.xlsx` + per-image .txt |

##### Directory Structure

```text
khatt/
├── data/
│   ├── train.zip               # Original download (TIFF + TXT)
│   └── validation.zip
├── train/
│   └── *.jpg                   # ~1,400 JPEG paragraph images
├── validation/
│   └── *.jpg                   # ~233 JPEG paragraph images
├── khatt_groundtruth.tsv       # Combined GT: path, split, stem, arabic_text
├── Groundtruth-Unicode.xlsx    # Original Excel GT table
├── KHATT.py                    # HuggingFace dataset loader
└── README.md                   # Dataset description
```

---

#### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | Handwritten Arabic text — diverse topics (news, stories, forms) |
| **Document Types** | Paragraph-level handwriting samples on ruled paper |
| **Language(s)** | Arabic |
| **Temporal Range** | 2012 collection (modern handwriting) |
| **Acquisition Method** | Flatbed scanner (TIFF format) |

##### 5.1 Script Coverage

| Script/Language | ISO Code | Samples | Notes |
|-----------------|----------|---------|-------|
| Arabic (cursive) | Arab | ~1,633 | Naskh and Ruq'ah styles |

**Script Families Present**: Arabic (cursive, unconstrained)

#### 6. IQA Profile

##### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Flatbed scanner (TIFF) |
| **Capture Device** | Flatbed scanner (1,000 different writers, varied scanners implied) |
| **Original Quality** | Good to excellent (controlled academic capture) |
| **Compression** | TIFF → JPEG 90 (minimal quality loss) |
| **Known Artifacts** | Ruled paper lines, ink bleed-through, slight pen pressure variation |

##### 6.2 Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Blur** | HIGH | Arabic diacritics (harakat) critical for legibility |
| **Noise** | LOW | Controlled scanner environment |
| **Skew** | MEDIUM | Writers used ruled paper — minimal inherent skew |
| **Contrast** | LOW | Ink-on-white scans — high native contrast |
| **Compression** | MEDIUM | JPEG artifacts affect Arabic letter connections |

##### 6.3 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **OOD Value** | HIGH — 1,000-writer diversity, unseen handwriting styles |
| **Unique Characteristics** | Largest multi-writer Arabic HW dataset from controlled academic capture |
| **Complementary Datasets** | Muharaf (damaged historical); AHTD (historical; if available) |
| **Benchmark Suitability** | HIGH — ICFHR 2012 benchmark, established evaluation protocol |
| **Known Limitations** | No bounding boxes; paragraph-level only; academic license |

#### 7. Known Issues & Limitations

- **Academic License**: Non-commercial research only; cannot be used in commercial products
- **TIFF Format**: Original format requires conversion for standard ML pipelines
- **No Bounding Boxes**: Paragraph-level images only; no word or line segmentation provided
- **Ruled Paper Artifacts**: Background has visible ruled lines that may affect IQA scores
- **Language Only Arabic**: No script diversity (all Modern Standard Arabic)

#### 8. Representative Samples

> Placeholder - To be populated during dataset profiling.

| Sample | Description | Notable Features |
|--------|-------------|------------------|
| `AHTD3A0001_Para2_3` | Writer A001, paragraph 2, section 3 | Formal Naskh style |
| `AHTD3A0438_Para3_4` | Validation writer | Casual Ruq'ah style |

#### 9. References

##### Primary Citation

```bibtex
@inproceedings{mahmoud2012khatt,
  title={KHATT: Arabic Offline Handwritten Text Database},
  author={Mahmoud, S.A. and Ahmad, I. and Alshayeb, M. and Al-Khatib, W.G.
          and Parvez, M.T. and Fink, G.A. and Margner, V. and EL Abed, H.},
  booktitle={Proceedings of the 13th International Conference on Frontiers
             in Handwriting Recognition (ICFHR 2012)},
  pages={447--452},
  year={2012},
  organization={IEEE Computer Society}
}
```

##### Related Works

- [Muharaf](muharaf.md) — Arabic historical manuscripts (damaged/historical style)
- [IAM](iam.md) — Latin handwriting database (analogous scope for Latin)

#### 10. Dataset-Specific Notes

##### 10.1 Annotation Caveats

- **Writer ID in Filename**: `AHTD3A{NNNN}` prefix uniquely identifies each of 1,000 writers
- **Paragraph Numbering**: `_Para{N}_{M}` where N=paragraph, M=segment within paragraph
- **Diacritics**: Arabic text includes full harakat (vowel diacritics) in some samples

##### 10.2 Implementation Notes

- **TIF Conversion**: Use `PIL.Image.open(tif).convert("RGB").save(jpg, "JPEG", quality=90)`
- **RTL Text**: Transcriptions are UTF-8 Arabic — ensure right-to-left rendering if displaying
- **OOD Use**: Sub-source 5a — Arabic cursive for `handwriting_presence` and `handwriting_content_type` heads
- **`build_ood_dataset.py` parameter**: `--khatt-dir /mnt/e/image_detection/01_base_data/handwriting/khatt`

##### 10.3 External Resources

- **HuggingFace Dataset Card**: [https://huggingface.co/datasets/benhachem/KHATT](https://huggingface.co/datasets/benhachem/KHATT)
- **KFUPM KHATT Page**: Original dataset from King Fahd University of Petroleum and Minerals
- **ICFHR 2012**: International Conference on Frontiers in Handwriting Recognition

---

#### 11. Layer 2 Audit Summary

> **Status**: No audit performed. Parser implemented; Layer 2 enrichment pipeline not yet run.

---

#### 12. Reliability & Bottlenecks

> **Status**: Parser implemented. Layer 2 metadata not yet generated.

- **Bottleneck**: TIFF→JPEG conversion completed; images ready for enrichment pipeline
- **License Constraint**: Academic-only — OOD registry entries flagged with `license_restriction=academic`

---

## 13. Training Head Coverage

> **Purpose**: Documents how this dataset contributes to the 22 training heads across
> MobileNetV4-Conv-S (pre-correction) and SigLIP 2 NAFlex (multi-task) models.

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
| ------- | --------- | ------------ | ------------ | ---------- | ----- |
| MNV4-H1 | orientation_cls | ❌ | 0 | N/A | No orientation GT; academic license — OOD evaluation only |
| MNV4-H2 | skew_reg | ❌ | 0 | N/A | No skew GT; academic license — OOD evaluation only |
| MNV4-H3 | resolution_quality_reg | ❌ | 0 | N/A | No resolution quality labels; academic license — OOD evaluation only |
| SIG-G1-1 | blur_score | 🟡 | ~1,633 | tier_3_heuristic | OOD evaluation only — flatbed scanner baseline; low blur negatives |
| SIG-G1-2 | noise_score | 🟡 | ~1,633 | tier_3_heuristic | OOD evaluation only — controlled scanner; low noise baseline |
| SIG-G1-3 | contrast_score | 🟡 | ~1,633 | tier_3_heuristic | OOD evaluation only — ink-on-white; high contrast baseline |
| SIG-G1-4 | skew_score | ❌ | 0 | N/A | No quality-based skew degradation in controlled flatbed scanner |
| SIG-G1-5 | compression_score | 🟡 | ~1,633 | tier_3_heuristic | OOD evaluation only — JPEG q90 from TIFF; minimal compression baseline |
| SIG-G1-6 | overall_quality | 🟡 | ~1,633 | tier_3_heuristic | OOD evaluation only — clean scanner quality baseline |
| SIG-G2-1 | script_cls | 🟡 | ~1,633 | GT (ARAB) | OOD evaluation only — academic license prevents training use |
| SIG-G3-1 | orientation_cls (post) | ❌ | 0 | N/A | No orientation GT |
| SIG-G3-2 | skew_reg (post) | ❌ | 0 | N/A | No skew GT |
| SIG-G4-1 | handwriting_presence_cls | 🟡 | ~1,633 | GT (derived) | OOD evaluation — 100% handwritten Arabic paragraph scans |
| SIG-G4-2 | handwriting_legibility_cls | 🟡 | ~1,633 | Proxy (text GT) | Transcription present → legible proxy |
| SIG-G4-3 | handwriting_content_type_cls | 🟡 | ~1,633 | GT (derived) | All cursive Arabic (Naskh/Ruq'ah) — content_type=cursive |
| SIG-G4-4 | presence_reg | 🟡 | ~1,633 | GT (derived) | OOD evaluation — ratio=1.0 (all handwritten) |
| SIG-G4-5 | legibility_reg | 🟡 | ~1,633 | Proxy | OOD evaluation — transcription present → proxy score 0.8 |
| SIG-G5-1 | capture_method_cls | 🟡 | ~1,633 | GT (derived) | OOD evaluation — flatbed scanner |
| SIG-G5-2 | shadow_reg | ❌ | - | - | Not applicable — controlled scanner capture |
| SIG-G5-3 | warping_reg | ❌ | - | - | Not applicable — flat page scans |
| SIG-G5-4 | code_cls | ❌ | - | - | No code content |
| SIG-G5-5 | resolution_quality_reg (SigLIP) | ❌ | 0 | N/A | No resolution quality labels; academic license — OOD evaluation only |

**Contribution legend**: ✅ Primary | 🟡 Secondary | ➖ Negatives only | ❌ Not applicable

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
| - | --------- | -------- | ------- |
| 1 | Script families | 🟡 | ARAB — OOD Arabic cursive handwriting; academic license limits training use |
| 2 | Capture method | ✅ | Flatbed scanner (TIFF → JPEG) |
| 3 | Document domain | 🟡 | Handwritten Arabic paragraphs (news, stories, forms) |
| 4 | Layout type | 🟡 | Paragraph-level images (not line/word crops) |
| 5 | Text density | 🟡 | Multi-line paragraph images |
| 6 | Degradation types | 🟡 | Ruled paper lines, ink bleed-through, pen pressure variation |
| 7 | Resolution/DPI range | 🟡 | Controlled scanner quality (DPI unspecified) |
| 8 | Document age | ✅ | Modern (2012 collection) |
| 9 | Text scope | 🟡 | Paragraph-level; no word/line segmentation |
| 10 | Content flags | ✅ | has_handwriting=true, 100% |
| 11 | Binarization status | 🟡 | Color JPEG (from TIFF scanner) |
| 12 | Artifact types | 🟡 | Ruled paper background; no shadow/warp |
| 13 | Color mode | 🟡 | JPEG RGB (scanner capture on ruled paper) |
| 14 | Font variety | ❌ | Handwriting only — Naskh and Ruq'ah cursive styles |

**Coverage legend**: ✅ Well-covered | 🟡 Partial | ❌ Not present

### 13.3 Corpus Role & Constraints

> **Status**: OOD evaluation source for Arabic cursive handwriting heads; not used for primary training.
>
> KHATT provides 1,633 paragraph-level handwritten Arabic images from 1,000 diverse writers,
> making it the most writer-diverse Arabic HW dataset in the collection. Academic Research Only
> license prevents use as primary training data — all contributions are OOD evaluation only.
> Mark all samples with `license_restriction=academic` in the OOD registry. Complementary to
> Muharaf (historical Arabic) for comprehensive ARAB handwriting OOD coverage.

---
