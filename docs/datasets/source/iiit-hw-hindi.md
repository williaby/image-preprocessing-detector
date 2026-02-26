---
dataset_id: iiit-hw-hindi
version: "1.0"
license: research
commercial_use: false
iqa_profiles:
  - varied_quality
  - scanner_artifacts
baseline_quality: null
training_suitable: true
benchmark_suitable: true
documentation_status: complete
---

#### IIIT-HW-Hindi (IIIT Handwritten Hindi Words)

> **Quick Stats**: 95,430 images | 69,853 train / 12,708 val / 12,869 test | Devanagari word-level HW | 1.89 GB
>
> **License**: Academic/Research | **Commercial Use**: No

##### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | IIIT-INDIC-HW-WORDS: Handwritten Indic Words Dataset (Hindi subset) |
| **Version** | 1.0 |
| **Release Date** | 2022 |
| **Last Updated** | 2024 (HuggingFace Parquet mirror) |
| **Maintainer** | CVIT (Centre for Visual Information Technology), IIIT Hyderabad |
| **Paper** | [IIIT-INDIC-HW-WORDS: A Dataset for Indic Handwritten Text Recognition](https://cvit.iiit.ac.in/research/projects/cvit-projects/iiit-indic-hw-words) |
| **Repository** | [HuggingFace: c3rl/IIIT-INDIC-HW-WORDS-Hindi](https://huggingface.co/datasets/c3rl/IIIT-INDIC-HW-WORDS-Hindi) |
| **License** | Research/Academic use |
| **Commercial Use** | No |
| **Documentation Status** | Complete |

**Citation**:
> Santhoshini Gongidi and C. V. Jawahar, "IIIT-INDIC-HW-WORDS: A Dataset for Indic Handwritten Text Recognition," 2022. CVIT, IIIT Hyderabad.

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | JPEG | Word-level Hindi handwriting images (cropped word regions) |
| **Transcriptions** | Parquet `text` field | Devanagari Unicode word text |

##### 2.2 Dataset Split Locations

| Split | HuggingFace Path | Local Path | Count | Status |
|-------|-----------------|-----------|-------|--------|
| **Train** | `default/train/*.parquet` | `iiit-hw-hindi/iiit_hw_hindi_train_*.jpg` | 69,853 | ✅ Complete |
| **Validation** | `default/validation/*.parquet` | `iiit-hw-hindi/iiit_hw_hindi_validation_*.jpg` | 12,708 | ✅ Complete |
| **Test** | `default/test/*.parquet` | `iiit-hw-hindi/iiit_hw_hindi_test_*.jpg` | 12,869 | ✅ Complete |
| **Total** | — | — | 95,430 | ✅ All local |

**Split Organization Pattern**: `single_dir` — all locally-extracted images in `iiit-hw-hindi/` with filename encoding split and index

> **Notes**:
>
> - Full dataset downloaded from HuggingFace Parquet (`c3rl/IIIT-INDIC-HW-WORDS-Hindi`) via streaming
> - All 95,430 images extracted as JPEG quality 90 using `scripts/download_iiit_hw_hindi_full.py`
> - Images are JPEG with variable width (301–2,560 px), representing word-level crops
> - Ground truth TSV at `iiit-hw-hindi/iiit_hw_hindi_groundtruth.tsv` (95,431 lines incl. header)

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Text Transcriptions** | Parquet string | Word-level | Hindi Unicode (Devanagari, UTF-8) |

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Image data** | Parquet `image` column | PIL Image bytes (JPEG) |
| **Transcription** | Parquet `text` column | Devanagari word string |
| **Split** | Parquet filename / split name | train / validation / test |

##### 2.5 Annotation Schema Details

> **Format**: HuggingFace Parquet with `image` (ImageObject) and `text` (string) fields

```python
# HuggingFace access
from datasets import load_dataset
ds = load_dataset("c3rl/IIIT-INDIC-HW-WORDS-Hindi", split="test", streaming=True)
sample = next(iter(ds))
# sample["image"] → PIL.Image (JPEG, variable width)
# sample["text"]  → "केंद्रों" (Devanagari Unicode)
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image` | PIL.Image | Yes | JPEG word crop |
| `text` | str | Yes | Devanagari Unicode transcription |
| `split` | str | Derived | train / validation / test |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Hindi text GT | `transcription` | High | Devanagari Unicode |
| ✅ Script info | `iso639_language=hi` | High | Hindi, Devanagari |
| ❌ Bounding boxes | — | Low | Word-level crops (no region coords) |
| ❌ Quality scores | — | Low | Compute from IQA analysis |

**Legend**: ✅ Directly usable | ❌ Not available

##### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human Expert (crowdsourced with QA, CVIT standard) |
| **Provenance Tier** | Tier 1 (Human Expert Annotation) |
| **Annotator Details** | CVIT annotation pipeline; multiple Indic language experts |
| **Quality Assurance** | IIIT Hyderabad research dataset — peer-reviewed |
| **GT Label Coverage** | 100% — all images have Devanagari text transcription |

---

#### 3. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | OOD evaluation (sub-source 5c: Devanagari handwriting) |
| **Purpose** | OOD Hindi HW for `handwriting_presence`, `script`, Devanagari OOD coverage |
| **Local Path** | `01_base_data/handwriting/iiit-hw-hindi/` |
| **Subset Used** | Full 95,430 images extracted (all splits); see `scripts/download_iiit_hw_hindi_full.py` |
| **Preprocessing** | Parquet streaming → PIL.Image → JPEG q90 save |

#### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | `iiit_hw_hindi` (handwriting category) |
| **Parser Status** | ✅ Implemented |
| **Layer 1 Fields** | `transcription` (Devanagari Unicode), `split` |
| **Layer 2 Auto-Derived** | `iso639_language=hi`, `script_family=Deva`, `text_direction=ltr` |
| **Config Entry** | `iiit-hw-hindi` in dataset config registry |

#### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/handwriting/iiit-hw-hindi/` | ✅ Complete | 95,430 JPEG (all splits) |
| **Ground Truth** | `01_base_data/handwriting/iiit-hw-hindi/iiit_hw_hindi_groundtruth.tsv` | ✅ Available | 95,431 rows (header + all images) |
| **Full Dataset** | HuggingFace: `c3rl/IIIT-INDIC-HW-WORDS-Hindi` | ✅ Mirrored | Source Parquet for re-extraction |
| **Layer 2 Metadata** | `metadata_registry/json/iiit_hw_hindi_metadata.json` | ⚠️ Pending | Run annotate_base_metadata.py then integrate script |

**To extract more images**:

```bash
# Extract 1000 additional test images via streaming
uv run python -c "
from datasets import load_dataset
from pathlib import Path
from PIL import Image as PILImage
import csv

out = Path('/mnt/e/image_detection/01_base_data/handwriting/iiit-hw-hindi')
ds = load_dataset('c3rl/IIIT-INDIC-HW-WORDS-Hindi', split='test', streaming=True)
gt = []
for i, s in enumerate(ds):
    if i >= 1000: break
    p = out / f'iiit_hw_hindi_test_{i:05d}.jpg'
    s['image'].save(p, 'JPEG', quality=90)
    gt.append((str(p), 'test', p.name, s['text']))
print(f'Extracted {len(gt)} images')
"
```

---

#### 4. Dataset Statistics

##### 4.1 Split Coverage

| Split | Source Count | Local Count | Coverage | Status |
|-------|--------------|-------------|----------|--------|
| **Train** | 69,853 | 69,853 | 100% | ✅ Complete |
| **Validation** | 12,708 | 12,708 | 100% | ✅ Complete |
| **Test** | 12,869 | 12,869 | 100% | ✅ Complete |
| **Total** | 95,430 | 95,430 | 100% | ✅ All local |

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 95,430 (all locally extracted) |
| **Training Split** | 69,853 (73%) |
| **Validation Split** | 12,708 (13%) |
| **Test Split** | 12,869 (14%) |
| **Image Width Range** | 301–2,560 pixels |
| **Image Height** | Variable (word-level crops) |
| **File Format** | JPEG (via PIL conversion from Parquet) |
| **Total HF Size** | 1.89 GB (Parquet) |
| **Local Disk Size** | ~40 MB (400 extracted images) |

##### 4.3 Text Statistics

| Metric | Value |
|--------|-------|
| **Script** | Devanagari (Hindi) |
| **Language** | Hindi (hi) |
| **Granularity** | Word-level images and transcriptions |
| **Text Length** | 1–23 characters per word |
| **Transcription Coverage** | 100% |

##### Directory Structure

```text
iiit-hw-hindi/
├── iiit_hw_hindi_train_00000.jpg   # Extracted train images
├── iiit_hw_hindi_train_00001.jpg
├── ...
├── iiit_hw_hindi_test_00000.jpg    # Extracted test images
├── iiit_hw_hindi_test_00001.jpg
├── ...
└── iiit_hw_hindi_groundtruth.tsv   # GT: path, split, filename, hindi_text
```

---

#### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | Handwritten Hindi words — diverse vocabulary |
| **Document Types** | Isolated word-level handwriting samples |
| **Language(s)** | Hindi (Devanagari script) |
| **Temporal Range** | 2022 collection |
| **Acquisition Method** | Multiple writers (scan or camera — CVIT unspecified) |

##### 5.1 Script Coverage

| Script/Language | ISO Code | Samples | Notes |
|-----------------|----------|---------|-------|
| Devanagari (Hindi) | Deva/hi | 95,430 | Isolated word crops |

**Script Families Present**: Brahmic (Devanagari)

#### 6. IQA Profile

##### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Word-level handwriting crops (scanner or camera, CVIT standard) |
| **Original Quality** | Good (IIIT Hyderabad controlled collection) |
| **Known Artifacts** | Variable pen pressure, ink spread, ruled paper backgrounds |

##### 6.2 Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Blur** | HIGH | Devanagari conjunct consonants sensitive to blur |
| **Noise** | MEDIUM | Handwriting on ruled paper introduces background noise |
| **Skew** | LOW | Word crops typically well-aligned |
| **Contrast** | LOW | Ink-on-paper — generally high contrast |

#### 7. Known Issues & Limitations

- **Research License**: Academic/research use only — not for commercial deployment
- **Word-Level Only**: No page-level or paragraph-level context; isolated word crops
- **Full Extract Complete**: All 95,430 images extracted locally via `scripts/download_iiit_hw_hindi_full.py`
- **No Bounding Boxes**: Word-level images without polygon or region coordinates
- **Hindi Only**: This HuggingFace dataset is the Hindi (Devanagari) subset of IIIT-INDIC-HW-WORDS; other Indic scripts not included here

#### 8. Representative Samples

> Placeholder - To be populated during dataset profiling.

| Sample | Description | Notable Features |
|--------|-------------|------------------|
| `iiit_hw_hindi_test_00000.jpg` | Hindi word crop | Devanagari, cursive style |
| `iiit_hw_hindi_train_00000.jpg` | Hindi word from train | Formal Devanagari print style |

#### 9. References

##### Primary Citation

```bibtex
@inproceedings{gongidi2022iiit,
  title={IIIT-INDIC-HW-WORDS: A Dataset for Indic Handwritten Text Recognition},
  author={Gongidi, Santhoshini and Jawahar, C. V.},
  year={2022},
  institution={CVIT, IIIT Hyderabad},
  url={https://cvit.iiit.ac.in/research/projects/cvit-projects/iiit-indic-hw-words}
}
```

##### Related Works

- [Muharaf](muharaf.md) — Arabic cursive handwriting (analogous Semitic script)
- [KHATT](khatt.md) — Arabic handwriting (1,000 writers)
- [IndicDLP](indicdlp.md) — Indic layout dataset (same IIIT Hyderabad ecosystem)

#### 10. Dataset-Specific Notes

##### 10.1 Annotation Caveats

- **Word Boundaries**: Images are pre-cropped to word level; some crops may include partial neighboring characters
- **Devanagari Matras**: Vowel diacritics (matras) are included — critical for accurate transcription

##### 10.2 Implementation Notes

- **Streaming Access**: Use `streaming=True` with HuggingFace `load_dataset()` to avoid 1.89 GB full download
- **OOD Use**: Sub-source 5c — Devanagari HW for `handwriting_presence` and `script=Deva` heads
- **`build_ood_dataset.py` parameter**: `--iiit-indic-dir /mnt/e/image_detection/01_base_data/handwriting/iiit-hw-hindi`

##### 10.3 External Resources

- **HuggingFace Dataset Card**: [https://huggingface.co/datasets/c3rl/IIIT-INDIC-HW-WORDS-Hindi](https://huggingface.co/datasets/c3rl/IIIT-INDIC-HW-WORDS-Hindi)
- **CVIT Project Page**: [https://cvit.iiit.ac.in/research/projects/cvit-projects/iiit-indic-hw-words](https://cvit.iiit.ac.in/research/projects/cvit-projects/iiit-indic-hw-words)

---

#### 11. Layer 2 Audit Summary

> **Status**: No audit performed. Parser implemented; Layer 2 enrichment pipeline not yet run.

---

#### 12. Reliability & Bottlenecks

> **Status**: Parser implemented. 400 images locally available; full dataset accessible via HuggingFace streaming.

- **No Data Bottleneck**: All 95,430 images extracted locally. Ready for `annotate_base_metadata.py` run.
- **License Constraint**: Research-only; OOD registry entries flagged with `license_restriction=research`

---

## 13. Training Head Coverage

> **Purpose**: Documents how this dataset contributes to the 22 training heads across
> MobileNetV4-Conv-S (pre-correction) and SigLIP 2 NAFlex (multi-task) models.

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | ❌ | 0 | — | Word-level crops are axis-aligned; no orientation variation present |
| MNV4-H2 | skew_reg | ❌ | 0 | — | Word crops are tightly cropped and well-aligned; no skew angle labels |
| MNV4-H3 | resolution_quality_reg | ➖ | ~400 (local) | Computed | Char-height scoring applicable; pending IQA labeling pipeline run |
| SIG-G1-1 | blur_score | ➖ | ~400 (local) | Computed | Devanagari conjuncts highly blur-sensitive; IQA pipeline required |
| SIG-G1-2 | noise_score | ➖ | ~400 (local) | Computed | Ruled paper background introduces noise; IQA pipeline required |
| SIG-G1-3 | contrast_score | ➖ | ~400 (local) | Computed | Ink-on-paper yields high contrast; IQA pipeline required |
| SIG-G1-4 | skew_score | ➖ | ~400 (local) | Computed | Word crops well-aligned; expected low skew penalty; IQA pipeline required |
| SIG-G1-5 | compression_score | ➖ | ~400 (local) | Computed | JPEG q90 via PIL; low compression artifact level; IQA pipeline required |
| SIG-G1-6 | overall_quality | ➖ | ~400 (local) | Computed | Controlled CVIT collection; expected good quality; IQA pipeline required |
| SIG-G2-1 | script_cls | 🟡 | ~95,430 (streaming) | GT (Deva) | Devanagari is one of the 19 training classes; research license — OOD eval use preferred |
| SIG-G3-1 | orientation_cls (post) | ❌ | 0 | — | No orientation variation in word-level crops; not applicable |
| SIG-G3-2 | skew_reg (post) | ❌ | 0 | — | Word crops are pre-aligned; residual skew head not applicable |
| SIG-G4-1 | handwriting_presence_cls | 🟡 | ~95,430 (streaming) | GT (derived: DOMINANT) | 100% handwritten Devanagari word images; presence = DOMINANT; OOD eval use |
| SIG-G4-2 | handwriting_legibility_cls | 🟡 | ~95,430 (streaming) | Proxy (transcription present) | Devanagari transcription available for all images → proxy for LEGIBLE class |
| SIG-G4-3 | handwriting_content_type_cls | 🟡 | ~95,430 (streaming) | GT (derived: CURSIVE/MIXED) | Hindi handwriting is semi-cursive; content_type = CURSIVE or MIXED |
| SIG-G4-4 | presence_reg | 🟡 | ~95,430 (streaming) | GT (derived: 1.0) | All images are handwritten word crops → presence ratio = 1.0 |
| SIG-G4-5 | legibility_reg | 🟡 | ~95,430 (streaming) | Proxy (0.8) | Transcription present → legibility proxy score ~0.8; no explicit rating |
| SIG-G5-1 | capture_method_cls | ➖ | ~400 (local) | Unverified | CVIT collection method unspecified (scanner or camera); assign SCANNER as default pending clarification |
| SIG-G5-2 | shadow_reg | ❌ | 0 | — | Controlled academic collection; no shadow variation present |
| SIG-G5-3 | warping_reg | ❌ | 0 | — | Word-level crops are flat; no page curl or perspective distortion |
| SIG-G5-4 | code_cls | ❌ | 0 | — | Hindi text only; no programming code or structured syntax content |
| SIG-G5-5 | resolution_quality_reg | ➖ | ~400 (local) | Computed | Variable width 301–2,560px; char-height scoring applicable after IQA pipeline run |

**Contribution legend**: ✅ Primary | 🟡 Secondary | ➖ Negatives only | ❌ Not applicable

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | 🟡 | Devanagari (Brahmic family) exclusively; strong single-script Deva contribution |
| 2 | Capture method | 🟡 | CVIT controlled collection — likely SCANNER or CAMERA; unspecified in documentation; assign SCANNER as default |
| 3 | Document domain | 🟡 | Handwritten Hindi vocabulary words; no domain specialization (general language) |
| 4 | Layout type | 🟡 | Word-level crops only; no page, paragraph, or line layout structure |
| 5 | Text density | 🟡 | Single isolated word per image; lowest possible text density granularity |
| 6 | Degradation types | 🟡 | Variable pen pressure, ink spread, ruled paper backgrounds; no synthetic degradation |
| 7 | Resolution/DPI range | 🟡 | Width 301–2,560px (variable word-level crops); DPI not documented; moderate range |
| 8 | Document age | ✅ | Modern (2022 CVIT collection); no historical or aged documents |
| 9 | Text scope | 🟡 | Word-level only; no sentence, paragraph, or full-page context |
| 10 | Content flags | ✅ | has_handwriting=true for all 95,430 images; 100% handwriting coverage |
| 11 | Binarization status | 🟡 | JPEG color images from Parquet; ink-on-paper may appear near-binary but stored as color |
| 12 | Artifact types | 🟡 | Ruled paper line backgrounds, variable pen pressure, occasional ink bleed |
| 13 | Color mode | 🟡 | JPEG RGB (color JPEG from Parquet); likely near-grayscale in practice (ink on white/ruled paper) |
| 14 | Font variety | ❌ | Natural handwriting only; no typeset fonts; writer style variation provides some variety |

**Coverage legend**: ✅ Well-covered | 🟡 Partial | ❌ Not present

### 13.3 Corpus Role & Constraints

IIIT-HW-Hindi is the primary Devanagari handwriting resource in the collection, providing 95,430 word-level crops from CVIT, IIIT Hyderabad, and is used principally as an OOD evaluation source for SIG-G2-1 `script_cls` (Deva class) and SIG-G4 handwriting heads (presence=DOMINANT, content_type=CURSIVE/MIXED). The research-only license prohibits commercial use, so all registry entries must carry `license_restriction=research`; training use requires explicit institutional clearance and should default to OOD evaluation only. All 95,430 images are locally extracted at `01_base_data/handwriting/iiit-hw-hindi/` — the dataset is ready for `annotate_base_metadata.py` and the Layer 2 enrichment pipeline.

---
