---
dataset_id: kuzushiji
version: "1.0"
license: CC-BY-SA-4.0
commercial_use: true
iqa_profiles:
  - historical_artifacts
  - low_resolution
baseline_quality: null
training_suitable: true
benchmark_suitable: false
documentation_status: complete
---

### Kuzushiji (K-MNIST / K-49 / K-Kanji)

> **Quick Stats**: 481,336 images total | 3 sub-datasets | Pre-modern Japanese cursive script | CC BY-SA 4.0
>
> **License**: CC BY-SA 4.0 | **Commercial Use**: Permitted (with ShareAlike)

#### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Kuzushiji-MNIST, Kuzushiji-49, Kuzushiji-Kanji |
| **Version** | 1.0 |
| **Release Date** | 2019 |
| **Last Updated** | 2019 |
| **Maintainer** | ROIS-DS Center for Open Data in the Humanities (CODH) |
| **Paper** | T. Clanuwat et al., "Deep Learning for Classical Japanese Literature," NeurIPS 2018 Workshop |
| **Repository** | [rois-codh/kmnist](https://github.com/rois-codh/kmnist) |
| **Official Site** | [CODH KMNIST](https://codh.rois.ac.jp/kmnist/index.html.en) |
| **License** | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| **Commercial Use** | Yes (with ShareAlike — derivative works must use CC BY-SA 4.0) |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/kuzushiji/` |
| **Documentation Status** | Complete |

##### Sub-Dataset Summary

| Sub-Dataset | Images | Classes | Resolution | Script | Content |
|------------|--------|---------|------------|--------|---------|
| **K-MNIST** | 70,000 | 10 | 28×28 px | Hiragana | 10 rows of historical Hiragana |
| **K-49** | 270,912 | 49 | 28×28 px | Hiragana | 48 Hiragana + 1 iteration mark |
| **K-Kanji** | 140,424 | 3,832 | 64×64 px | Kanji | Historical Kanji (highly imbalanced) |
| **Total** | **481,336** | **3,891** | | **Jpan** | |

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

##### 2.1 Provided File Types

| Sub-Dataset | File Format | Description |
|------------|-------------|-------------|
| **K-MNIST** | IDX binary (`.gz`) | MNIST-format: 4 files (train-images, train-labels, test-images, test-labels) |
| **K-49** | NumPy (`.npz` / `.npy`) | 4 files: `k49-train-imgs.npz`, `k49-train-labels.npy`, `k49-test-imgs.npz`, `k49-test-labels.npy` |
| **K-Kanji** | TAR archive → PNG | `kkanji2.tar` → per-class subdirectories of 64×64 PNG images |
| **Class Maps** | CSV | `kmnist_classmap.csv`, `k49_classmap.csv` — integer → Unicode codepoint + reading |

##### 2.2 Dataset Split Locations

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **K-MNIST Train** | `kmnist/images/train/` | `kmnist/data/train-labels-idx1-ubyte.gz` | 60,000 | ✅ |
| **K-MNIST Test** | `kmnist/images/test/` | `kmnist/data/t10k-labels-idx1-ubyte.gz` | 10,000 | ✅ RESERVED |
| **K-49 Train** | `k49/images/train/` | `k49/data/k49-train-labels.npy` | 232,365 | ✅ |
| **K-49 Test** | `k49/images/test/` | `k49/data/k49-test-labels.npy` | 38,547 | ✅ RESERVED |
| **K-Kanji All** | `kkanji/kkanji2/{class}/` | Encoded in directory name | 140,424 | ✅ |
| **Total** | | | **481,336** | ✅ Complete |

**Split Organization Pattern**: K-MNIST: `mnist_ubyte_files` (4 IDX binary files); K-49: `numpy_split_files` (4 NumPy arrays); K-Kanji: `single_dir_with_category` (per-class directories)

> **Notes**:
>
> - K-MNIST test (10,000) and K-49 test (38,547) are RESERVED for benchmark evaluation only
> - K-Kanji has no official train/test split — must create stratified split by class
> - Filesystem counts are authoritative (verified via materialization script)

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Character Class** | Integer (0–N) | Image-level | K-MNIST: 0–9; K-49: 0–48; K-Kanji: 0–3831 |
| **Unicode Mapping** | `kmnist_classmap.csv` / `k49_classmap.csv` | Class-level | Integer → Unicode Hiragana/Kanji codepoint + romanized reading |
| **Script** | Derived | Image-level | All: historical Japanese Kuzushiji cursive style |

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | GitHub README | Version, license, citation, split sizes, class counts |
| **Class-level** | `kmnist_classmap.csv`, `k49_classmap.csv` | Integer label → Unicode codepoint → Japanese character → romanized reading |
| **Image-level** | Encoded in IDX/NPZ arrays | Pixel array (uint8), class label per row |
| **K-Kanji image-level** | Directory name | Unicode codepoint encoded as directory name (`U+XXXXXX` in Kaggle, actual char in extracted) |

##### 2.5 Annotation Schema Details

**IDX Binary Format (K-MNIST)**:

```text
Images file:
  [4 bytes] magic = 0x00000803
  [4 bytes] num_images
  [4 bytes] num_rows = 28
  [4 bytes] num_cols = 28
  [N×28×28 bytes] pixel data (uint8, row-major)

Labels file:
  [4 bytes] magic = 0x00000801
  [4 bytes] num_labels
  [N bytes] label data (uint8, class 0–9)
```

**NumPy Format (K-49)**:

```text
k49-train-imgs.npz  → arr_0: shape (232365, 28, 28), dtype uint8
k49-train-labels.npy → shape (232365,), dtype uint8, values 0–48
k49-test-imgs.npz   → arr_0: shape (38547, 28, 28), dtype uint8
k49-test-labels.npy  → shape (38547,), dtype uint8
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Image pixel array | uint8 ndarray | Yes | Shape (28,28) for K-MNIST/K-49, (64,64) for K-Kanji |
| Class integer label | uint8 | Yes | Maps to Unicode via classmap CSV |
| Unicode character | str | Derived | `text_content.full_text` — 1 character per image |
| Split (train/test) | str | Yes | From source file name (train-images vs t10k-images) |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Integer class label | `text_content.full_text` (Unicode char) | High | Via classmap CSV lookup |
| ✅ Script (derived) | `language.script_code` = `Jpan` | High | All images are Japanese |
| ✅ Split info | `provenance.split` | High | From source file name |
| ✅ Historical period flag | `provenance.historical` | Medium | All pre-1900 |
| ⚠️ Class balance | `provenance.class_weight` | Low | K-Kanji needs inverse-freq weights |
| ❌ Bounding boxes | — | N/A | Character-level crops, no boxes needed |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

##### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Derived from digitized historical books (National Institute of Japanese Literature) |
| **Provenance Tier** | Tier 1 (extracted from manually annotated historical archives) |
| **Annotator Details** | CODH annotators; source: historical Japanese books from the NIJL collection |
| **Inter-Annotator Agreement** | Not reported; quality assured by multiple expert annotators |
| **Quality Assurance** | Multiple expert annotators; balanced sampling for K-MNIST/K-49; K-Kanji uses exhaustive class enumeration |
| **GT Label Coverage** | 100% — every image has a Unicode character label [Official] |

---

#### 3. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Script detection (Phase 10B), Handwriting presence (SigLIP2 Group 4) |
| **Purpose** | Training; K-MNIST/K-49 test splits reserved for benchmark |
| **Local Path** | `/mnt/e/image_detection/01_base_data/handwriting/kuzushiji/` |
| **Subset Used** | K-49 train split (~6,000 stratified) for script_cls; K-49 full for handwriting heads |
| **Preprocessing** | Upscale from 28×28/64×64 to ≥224px (INTER_CUBIC or INTER_LANCZOS4) before SigLIP2 |
| **Dataloader** | `src/image_preprocessing_detector/annotation/parsers/handwriting/kuzushiji.py` |

**Addressing Project Gaps**:

- JPAN currently "OK" at ~10K from synth-multiscript + JSSODA. K-49 alone adds 232K train examples.
- Kuzushiji adds **handwritten** JPAN (vs. synth-multiscript's printed Japanese) — critical for content_type diversity.
- K-Kanji's 3,832 rare Kanji classes are valuable for few-shot generalization of the JPAN script class.

**Usage Strategy for Script Detection**:

Use K-49 train split (232K, 49 classes). Stratified sample ~6,000 images matching JPAN target. K-Kanji adds rare Kanji diversity. K-MNIST is a subset of K-49 and primarily useful for baseline validation.

**Resolution Consideration**:

28×28 and 64×64 px crops need upscaling for SigLIP2 (which expects at least 224px). Use `cv2.resize` with `INTER_CUBIC` or `INTER_LANCZOS4` to upscale to ≥224px before feeding to SigLIP2.

#### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | `src/image_preprocessing_detector/annotation/parsers/handwriting/kuzushiji.py` |
| **Parser Status** | Complete |
| **Integration Script** | `scripts/integrate_kuzushiji_enrichments.py` |
| **Materialization Script** | `scripts/materialize_kuzushiji.py` |
| **Layer 1 Fields** | `text_content.full_text` (Unicode char), `language.script_code` (Jpan), `provenance.split` |
| **Layer 2 Auto-Derived** | `has_handwriting=True`, `language_code=ja`, `script_code=Jpan`, `capture_method=scanner_flatbed` |
| **Config Entry** | `DATASET_CONFIGS["kuzushiji"]` |

**Required Parser Capabilities**:

1. IDX binary loading for K-MNIST (4 files)
2. NumPy `.npz`/`.npy` loading for K-49 (4 files)
3. Per-class directory loading for K-Kanji
4. Unicode mapping from `kmnist_classmap.csv` and `k49_classmap.csv`
5. Upscale from 28×28/64×64 to ≥224px for downstream use
6. Assign script metadata: `Jpan`, `ja`, `JPAN`
7. Handle class imbalance metadata (K-Kanji)

**Schema-Derived Comparison Matrix**:

| Source Field | Layer 2 Target | Parser Handles? | Priority | Notes |
|--------------|----------------|-----------------|----------|-------|
| Integer label → Unicode | `text_content.full_text` | Yes | High | Via classmap CSV |
| Image array (uint8) | Saved PNG | Yes | High | Written to disk on materialize |
| Script (derived) | `language.script_code` | Yes | High | `Hira` or `Hani` → `Jpan` |
| Split (filename pattern) | `provenance.split` | Yes | High | From IDX/NPZ file name |
| Historical period | `provenance.historical` | Yes | Medium | Flag as historical |
| Class balance | `provenance.class_weight` | Partial | Low | K-Kanji needs inverse-freq weights |

#### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **K-MNIST raw** | `/mnt/e/image_detection/01_base_data/handwriting/kuzushiji/kmnist/data/` | Complete | IDX (train+test, .gz) + NPZ + `kmnist_classmap.csv` |
| **K-MNIST images** | `/mnt/e/image_detection/01_base_data/handwriting/kuzushiji/kmnist/images/` | Complete | 60,000 train PNGs + 10,000 test PNGs; `train_index.jsonl` + `test_index.jsonl` written |
| **K-49 raw** | `/mnt/e/image_detection/01_base_data/handwriting/kuzushiji/k49/data/` | Complete | NPZ train+test (shapes verified: 232365×28×28, 38547×28×28) + `k49_classmap.csv` |
| **K-49 images** | `/mnt/e/image_detection/01_base_data/handwriting/kuzushiji/k49/images/` | Complete | 232,365 train PNGs + 38,547 test PNGs; `train_index.jsonl` + `test_index.jsonl` written |
| **K-Kanji images** | `/mnt/e/image_detection/01_base_data/handwriting/kuzushiji/kkanji/kkanji2/` | Complete | 3,832 dirs / 140,424 PNGs extracted; `all_index.jsonl` written |
| **Layer 2 Metadata** | `metadata_registry/json/kuzushiji_metadata.json` | Complete | 1.7 GB, 481,336 samples, generated 2026-02-24 |

**CDN Investigation (confirmed 2026-02-24)**:

- `codh.rois.ac.jp` → `136.187.88.58` — DNS resolves correctly but TCP times out on both HTTP and HTTPS
- `torchvision.datasets.KMNIST(download=True)` will also fail — it uses the same CDN (single mirror)
- All official CODH download paths are unreachable from this host

**Kaggle download (completed 2026-02-24)** via `anokas/kuzushiji` (571 MB) + `taniokam/kmnist` (41 MB):

- `anokas/kuzushiji` contains K-49 NPZ, K-Kanji tar, `kmnist_classmap.csv`, `k49_classmap.csv`
- K-Kanji from Kaggle uses `U+XXXXXX` code-point dir naming — `scripts/materialize_kuzushiji.py`
  handles the rename to actual Unicode characters on extraction

```bash
# Materialize K-MNIST (70K images) — COMPLETE
uv run python scripts/materialize_kuzushiji.py --sub-dataset kmnist

# Materialize K-49 (270K images — takes ~2h on NTFS at ~30 img/s) — COMPLETE
uv run python scripts/materialize_kuzushiji.py --sub-dataset k49

# Index K-Kanji (scans existing dirs, writes all_index.jsonl) — COMPLETE
uv run python scripts/materialize_kuzushiji.py --sub-dataset kkanji
```

---

#### 4. Dataset Statistics

##### 4.1 Split Coverage

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **K-MNIST Train** | 60,000 | 60,000 | 100% | Complete |
| **K-MNIST Test** | 10,000 | 10,000 | 100% | Complete (benchmark reserved) |
| **K-49 Train** | 232,365 | 232,365 | 100% | Complete |
| **K-49 Test** | 38,547 | 38,547 | 100% | Complete (benchmark reserved) |
| **K-Kanji All** | 140,424 | 140,424 | 100% | Complete (no official train/test split) |
| **Total** | **481,336** | **481,336** | **100%** | All splits complete |

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 481,336 |
| **K-MNIST Train** | 60,000 (28×28 px grayscale) |
| **K-MNIST Test** | 10,000 (28×28 px grayscale) |
| **K-49 Train** | 232,365 (28×28 px grayscale) |
| **K-49 Test** | 38,547 (28×28 px grayscale) |
| **K-Kanji All** | 140,424 (64×64 px grayscale) |
| **Total Classes** | 3,891 (10 + 49 + 3,832) |
| **File Format(s)** | PNG (materialized); IDX binary / NumPy arrays (raw) |
| **Color Space** | Grayscale |
| **Layer 2 Coverage** | 481,336 / 481,336 (100%) [Empirically Derived] |

##### 4.3 Text Statistics

> **Availability**: Available — Unicode character transcription for every image
> **Source**: `ground_truth` (via classmap CSV lookup)

| Metric | Value |
|--------|-------|
| **Text Scope** | Character-level (1 Unicode character per image) |
| **Character Count per Sample** | 1 (exactly — single character crops) |
| **Unique Unicode Characters** | 3,891 (10 K-MNIST + 49 K-49 + 3,832 K-Kanji, with overlap) |
| **Script** | Jpan (Hiragana + Kanji in Kuzushiji cursive style) |
| **GT Coverage** | 100% — all 481,336 samples have Unicode transcription [Official] |

> **Note**: Because each image contains exactly one character, traditional text statistics
> (word count, sentence count) are not applicable. The relevant metric is class-level
> Unicode coverage, which is 100%.

##### Directory Structure

```text
kuzushiji/
├── kmnist/
│   ├── data/                    # IDX binary .gz files + kmnist_classmap.csv
│   └── images/
│       ├── train/               # 60,000 PNGs (train_index.jsonl)
│       └── test/                # 10,000 PNGs (test_index.jsonl)
├── k49/
│   ├── data/                    # NPZ/NPY files + k49_classmap.csv
│   └── images/
│       ├── train/               # 232,365 PNGs (train_index.jsonl)
│       └── test/                # 38,547 PNGs (test_index.jsonl)
└── kkanji/
    └── kkanji2/                 # 3,832 per-class dirs / 140,424 PNGs (all_index.jsonl)
        ├── {unicode_char}/
        └── ...
```

**Sub-Dataset Statistics Detail**:

K-MNIST:

| Metric | Value |
|--------|-------|
| Total Images | 70,000 |
| Train | 60,000 |
| Test | 10,000 |
| Classes | 10 (rows of Hiragana) |
| Resolution | 28×28 px (grayscale) |
| Balance | Balanced (~6,000/class train, ~1,000/class test) |

K-49:

| Metric | Value |
|--------|-------|
| Total Images | 270,912 |
| Train | 232,365 |
| Test | 38,547 |
| Classes | 49 (Hiragana + iteration mark) |
| Resolution | 28×28 px (grayscale) |
| Balance | Intentionally imbalanced |

K-Kanji:

| Metric | Value |
|--------|-------|
| Total Images | 140,424 |
| Classes | 3,832 |
| Resolution | 64×64 px (grayscale) |
| Balance | Highly imbalanced (1 to ~4,000 per class) |
| Min per class | 1 sample |
| Max per class | ~4,000 samples |

---

#### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | Historical Japanese literature (pre-1900 manuscripts) — EDU |
| **Document Types** | Extracted character crops from scanned book pages |
| **Language(s)** | Japanese (classical/pre-modern), ISO 639-1: `ja` |
| **Script** | Jpan: Kuzushiji (pre-modern cursive Hiragana + Kanji) |
| **Capture Method** | Scanner — high-resolution archival scans of NIJL book collection, normalized to character crops |
| **Content Type** | Handwritten (100%) — cursive historical script |
| **Historical Period** | Pre-1900 (Edo period and earlier) |
| **Text Scope** | Character-level (one character per image) |

##### 5.1 Class/Category Distribution

| Sub-Dataset | Category | Classes | Samples | Balance |
|-------------|----------|---------|---------|---------|
| K-MNIST | 10 Hiragana rows | 10 | 70,000 | Balanced |
| K-49 | 48 Hiragana + 1 iteration mark | 49 | 270,912 | Imbalanced |
| K-Kanji | Historical Kanji | 3,832 | 140,424 | Highly imbalanced (1–4,000/class) |

##### 5.2 Class/Category Definitions

| Class/Category | ID | Description | Parent |
|----------------|-----|-------------|--------|
| Hiragana (K-MNIST) | 0–9 | 10 of the most common Kuzushiji Hiragana characters | Jpan |
| Hiragana (K-49) | 0–48 | 48 Hiragana characters + 1 iteration mark (々) | Jpan |
| Kanji (K-Kanji) | 0–3831 | 3,832 historical Kanji in Kuzushiji cursive style | Jpan |

> Unicode mappings in `kmnist_classmap.csv` and `k49_classmap.csv` provide integer → Unicode → reading for K-MNIST and K-49. K-Kanji class identity is encoded directly in the directory name (Unicode character).

##### 5.3 Language & Script Coverage

| Script/Language | ISO Code | Sub-Dataset | Samples |
|-----------------|----------|-------------|---------|
| Hiragana (historical Kuzushiji) | Hira → Jpan | K-MNIST | 70,000 |
| Hiragana (historical Kuzushiji) | Hira → Jpan | K-49 | 270,912 |
| Kanji (historical Kuzushiji) | Hani → Jpan | K-Kanji | 140,424 |

**Script ML Class**: `JPAN`

**Script Characteristics**:

- Kuzushiji: pre-modern cursive Japanese, illegible to modern readers
- Hiragana in heavily connected, flowing stroke style
- Kanji in archaic variant forms from historical dictionaries
- Fundamentally different visual appearance from modern Japanese printing

---

#### 6. IQA Profile

##### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Archival scanner crops, normalized to 28×28 or 64×64 px |
| **Capture Device** | High-resolution flatbed archival scanner (`scanner_flatbed`); heavily downsampled for this release |
| **Original Quality** | Variable (historical documents: aging, bleed-through, foxing in originals) |
| **Compression** | None for K-MNIST/K-49 (raw uint8 arrays); lossless PNG for K-Kanji |
| **Known Artifacts** | Heavy downsampling (28px is very small); some inter-class visual overlap from cursive style |

##### 6.2 Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Resolution** | CRITICAL | 28×28 px is extremely low for modern models; must upscale to ≥224px |
| **Blur** | HIGH | Downsampling introduces effective blur at 28px; fine stroke detail lost |
| **Noise** | MEDIUM | Historical aging noise partially preserved after downsampling |
| **Contrast** | LOW | Grayscale normalization applied during materialization |
| **Compression** | N/A | Lossless PNG and raw arrays; no compression artifacts |
| **Class imbalance** | HIGH (K-Kanji) | Many rare Kanji have <10 training examples |

##### 6.3 Document Feature Characteristics

| Feature | Presence | IQA Implications |
|---------|----------|------------------|
| **Text Size Range** | 28×28 px (K-MNIST/K-49), 64×64 px (K-Kanji) | Very small; all features are at character scale |
| **Stroke Complexity** | High (cursive connecting strokes) | Kuzushiji strokes blur together at low resolution |
| **Font Diversity** | N/A — handwriting only | Historical calligraphic variation between scribes |
| **Color Usage** | Grayscale only | No color information; ink-on-paper appearance |
| **Historical Artifacts** | Aging, bleed-through (partially preserved) | Visible in some samples after downsampling |

##### 6.4 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | HIGH — 481K historical Japanese handwriting crops; unique Kuzushiji cursive style |
| **Unique Characteristics** | Pre-modern cursive Japanese unavailable elsewhere; Kuzushiji ≠ modern Japanese |
| **Complementary Datasets** | Combine with JSSODA (modern Japanese scene text) and CASIA-HWDB2 (Chinese handwriting) |
| **Benchmark Suitability** | MEDIUM — K-MNIST/K-49 test splits reserved; K-Kanji has no official test split |
| **Known Limitations** | Very low resolution (28×28 px) requires upscaling; Kuzushiji style differs from modern Japanese |

---

#### 7. Known Issues & Limitations

- **Very low resolution**: 28×28 px is extremely small for modern ViT/SigLIP2 models. Upscaling introduces artifacts but is necessary.
- **Kuzushiji ≠ modern Japanese**: These are pre-modern cursive forms, not standard modern Hiragana/Kanji. Models trained only on Kuzushiji may underperform on modern Japanese. Use in combination with modern Japanese printed data.
- **K-49 class imbalance**: Some classes have significantly more samples than others. Apply class weighting during training.
- **K-Kanji one-shot classes**: 3,832 classes with as few as 1 sample each. Only useful for few-shot or multi-task learning; standard cross-entropy will fail on rare classes.
- **No official K-Kanji train/test split**: Must create stratified split by class.
- **ShareAlike license**: Derivative models/datasets must use CC BY-SA 4.0. Not an issue for internal training; becomes relevant if publishing derived artifacts.
- **CODH CDN unreachable**: `codh.rois.ac.jp` TCP-blocked from this host. Use Kaggle mirrors `anokas/kuzushiji` (K-MNIST/K-49/K-Kanji) and `taniokam/kmnist` as alternatives.

---

#### 9. References

##### Primary Citation

```bibtex
@article{clanuwat2018deep,
  title     = {Deep Learning for Classical Japanese Literature},
  author    = {Clanuwat, Tarin and Bober-Irizar, Mikel and Kitamoto, Asanobu
               and Lamb, Alex and Yamamoto, Kazuaki and Ha, David},
  journal   = {arXiv preprint arXiv:1812.01718},
  year      = {2018},
  url       = {https://arxiv.org/abs/1812.01718}
}
```

##### Related Works

- [jssoda.md](jssoda.md) — Complementary JPAN: modern Japanese scene text
- [mle2e.md](mle2e.md) — Complementary CJK: mixed CJK text
- [tibhcr.md](tibhcr.md) — Analogous: character-level crops (Tibetan), similar usage pattern
- [casia-hwdb2-line.md](casia-hwdb2-line.md) — Analogous: Chinese handwriting line crops

##### Leaderboards

- [Papers With Code — Kuzushiji-MNIST](https://paperswithcode.com/dataset/kuzushiji-mnist)
- [Papers With Code — Kuzushiji-49](https://paperswithcode.com/dataset/kuzushiji-49)

---

#### 10. Dataset-Specific Notes

##### 10.1 Historical Significance

Kuzushiji was the standard written form of Japanese before educational reforms in 1900. Over 99% of pre-Meiji Japanese books, correspondence, and records are written in Kuzushiji. ML models trained on these datasets enable digitization of this vast corpus currently inaccessible to modern readers. CODH provides an annotation game ([KuroNet](https://codh.rois.ac.jp/kuronet/)) for crowdsourced annotation.

##### 10.2 Class Map Files

The Unicode class mapping CSVs (`kmnist_classmap.csv`, `k49_classmap.csv`) map integer labels to:

- Unicode codepoint
- Japanese character (Hiragana)
- Romanized reading

These are in the GitHub repository at `rois-codh/kmnist`.

##### 10.3 CC BY-SA ShareAlike Implications

Any **published** derivative datasets or trained models must use CC BY-SA 4.0. For internal ML training pipelines that produce model weights used internally, the ShareAlike clause does not require open-sourcing model weights — it applies to distributed works.

##### 10.4 Acquisition Notes

- Official CODH CDN (`codh.rois.ac.jp`) TCP-blocks from this host (confirmed 2026-02-24)
- `torchvision.datasets.KMNIST(download=True)` uses the same CDN and will also fail
- Kaggle mirror `anokas/kuzushiji` (571 MB) provides K-49 NPZ, K-Kanji tar, and class maps
- Kaggle mirror `taniokam/kmnist` (41 MB) provides K-MNIST IDX files
- K-Kanji from Kaggle uses `U+XXXXXX` directory naming; `scripts/materialize_kuzushiji.py` handles rename to actual Unicode characters

---

#### 11. Layer 2 Audit Summary

##### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-24 | **Grade**: A (100/100) | **Auditor**: manual 200-sample audit

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 1.000 | 0.278 | All enrichment fields present in 200/200 samples |
| Field Validity | 1.000 | 0.278 | All field values correct in 200/200 checks |
| Doc Completeness | 1.000 | 0.167 | All required fields populated |
| Defect Rate | 1.000 | 0.167 | 0 issues found across 200 samples |
| VLM Accuracy | N/A | 0.111 | Deferred — 28×28 px too small for meaningful VLM inspection |
| **Overall** | **1.000** | | **Grade A (100/100)** |

##### 11.2 Key Defects

> No defects found. All 200 audited samples passed every check.

##### 11.3 VLM Inspection Summary

> **Status**: Deferred — 28×28 px images are too small for meaningful VLM visual inspection.
> Character-level crops at this resolution do not contain enough pixels for VLM content assessment.
> Unicode transcription correctness validated via classmap lookup instead.

| Flag | Inspected | FP Rate | Notes |
|------|----------:|--------:|-------|
| has_handwriting | 200 | 0% | All 200 samples correctly flagged True via classmap verification |
| correct_language (ja) | 200 | 0% | All 200 samples confirmed `ja` |
| correct_script (Jpan) | 200 | 0% | All 200 samples confirmed `Jpan` |
| correct_capture (scanner_flatbed) | 200 | 0% | All 200 samples confirmed |

**Audit Pass Rate**: 100% (200/200 samples across all 10 audit dimensions)

**Audit Dimensions Checked**:

| Check | Pass Rate | Notes |
|-------|----------:|-------|
| has_enrichment | 200/200 (100%) | All samples have Layer 2 enrichment |
| has_transcription | 200/200 (100%) | All samples have Unicode char transcription |
| correct_language (ja) | 200/200 (100%) | |
| correct_script (Jpan) | 200/200 (100%) | |
| correct_capture (scanner_flatbed) | 200/200 (100%) | |
| correct_handwriting (True) | 200/200 (100%) | |
| correct_scope (character) | 200/200 (100%) | |
| resolution_check (28px or 64px) | 200/200 (100%) | |
| content_flags_tier (tier_0_exact) | 200/200 (100%) | |
| domain_ok (EDU) | 200/200 (100%) | |

##### 11.4 Cross-Dataset Findings

- None — no cross-dataset issues discovered during this audit.

**Audit Artifacts**: `scripts/audit/results/kuzushiji/` (if generated)

---

#### 12. Reliability & Bottlenecks

> **Purpose**: Auto-generated composite reliability summary. Populated by `materialize_reliability_summary.py`.
>
> **Status**: Layer 2 integration complete (2026-02-24). All 481,336 samples processed.

##### 12.1 Composite Category Distribution

> **Computed**: 2026-02-24 | **Samples**: 481,336 | **Audit Pass Rate**: 100% (200-sample audit)

| Category | Notes |
|----------|-------|
| hard_label | Unicode character GT is exact (Tier 0) — all samples qualify |
| soft_label | N/A |
| active_learning | N/A |
| unreliable | 0 — no samples flagged during audit |

**Category Thresholds**: hard_label >= 0.9, soft_label >= 0.7, active_learning >= 0.5, unreliable < 0.5

> **Note**: Formal composite category distribution requires running `materialize_reliability_summary.py`.
> Based on 100% audit pass rate and Tier 0 (exact) Unicode GT labels, expected distribution is
> near-100% hard_label.

##### 12.2 Top Bottleneck Fields

> Based on audit results, no bottleneck fields identified. All enrichment fields pass at 100%.
> Potential future bottleneck: `resolution_quality` head labels are negatives only (28px hard negatives),
> not positive training signal — this is by design, not a defect.

| Rank | Field | Bottleneck % | Notes |
|-----:|-------|-------------:|-------|
| 1 | `resolution_quality` | N/A | Design constraint — 28px images are hard negatives by intent |

---

#### 13. Training Head Coverage

> **Purpose**: Documents how this dataset contributes to the 22 training heads across
> MobileNetV4-Conv-S (pre-correction) and SigLIP 2 NAFlex (multi-task) models.

##### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
| ------- | --------- | ------------ | ------------ | ---------- | ----- |
| MNV4-H1 | orientation_cls | Not applicable | - | - | Character-level 28×28 px crops; no orientation variation or labels |
| MNV4-H2 | skew_reg | Not applicable | - | - | Character crops; no skew labels applicable |
| MNV4-H3 | resolution_quality_reg | Negatives only | ~10K | Negatives | 28×28 px is very low res — useful as hard negatives |
| SIG-G1-1 | blur_score | Negatives only | ~10K | Negatives | 28×28 px normalized crops at standard quality; low-blur anchors |
| SIG-G1-2 | noise_score | Negatives only | ~10K | Negatives | 28×28 px normalized crops; contributes low-noise anchors |
| SIG-G1-3 | contrast_score | Negatives only | ~10K | Negatives | 28×28 px normalized crops; contributes low-contrast anchors |
| SIG-G1-4 | skew_score | Not applicable | - | - | Character crops lack document-level skew quality degradation |
| SIG-G1-5 | compression_score | Negatives only | ~10K | Negatives | PNG lossless (K-Kanji) / raw uint8 (K-MNIST, K-49); zero-compression anchors |
| SIG-G1-6 | overall_quality | Not applicable | - | - | No MOS scores; 28×28 px crops not suitable for overall quality assessment |
| SIG-G2-1 | script_cls | Primary | ~6,000 train | GT (JPAN) | Stratified sample from K-49 train (232K available); use K-49 only |
| SIG-G3-1 | orientation_cls (post) | Not applicable | - | - | Character-level crops; no orientation variation or labels |
| SIG-G3-2 | skew_reg (post) | Not applicable | - | - | Character crops; no skew labels applicable |
| SIG-G4-1 | handwriting_presence_cls | Primary | ~6,000 train | GT (derived) | 100% handwritten historical character crops |
| SIG-G4-2 | handwriting_legibility_cls | Secondary | ~6,000 train | Proxy (char GT) | Unicode label present → legible proxy; Kuzushiji ≠ modern |
| SIG-G4-3 | handwriting_content_type_cls | Primary | ~6,000 train | GT (derived) | All cursive historical — content_type=cursive |
| SIG-G4-4 | presence_reg | Primary | ~6,000 train | GT (derived) | ratio=1.0 (all handwritten) |
| SIG-G4-5 | legibility_reg | Secondary | ~6,000 train | Proxy | Unicode label present → proxy score 0.8 |
| SIG-G5-1 | capture_method_cls | Secondary | ~6,000 train | GT (derived) | Scanner (archival high-res, heavily downsampled) |
| SIG-G5-2 | shadow_reg | Not applicable | - | - | Not applicable — uniform dark background |
| SIG-G5-3 | warping_reg | Not applicable | - | - | Not applicable — normalized character crops |
| SIG-G5-4 | code_cls | Not applicable | - | - | No code content |
| SIG-G5-5 | resolution_quality_reg (SigLIP) | Negatives only | ~10K | Negatives | 28×28 px hard negatives; upscale to ≥224 px before SigLIP inference |

**Contribution legend**: Primary | Secondary | Negatives only | Not applicable

##### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
| - | --------- | -------- | ------- |
| 1 | Script families | Well-covered | JPAN — fills handwritten CJK gap; Kuzushiji cursive adds unique visual style |
| 2 | Capture method | Well-covered | Scanner (archival high-res → normalized crops) |
| 3 | Document domain | Well-covered | Historical Japanese literature (pre-1900 manuscripts) |
| 4 | Layout type | Well-covered | Character-level crops (isolated characters) |
| 5 | Text density | Not present | Single character per image |
| 6 | Degradation types | Partial | Aging, bleed-through in originals — partially preserved after downsampling |
| 7 | Resolution/DPI range | Negatives only | 28×28 px (K-MNIST/K-49) and 64×64 px (K-Kanji) — very low; hard negatives for resolution head |
| 8 | Document age | Well-covered | Historical (pre-1900 Edo period and earlier) |
| 9 | Text scope | Partial | Character-level only (no line/page images) |
| 10 | Content flags | Well-covered | has_handwriting=true, 100% |
| 11 | Binarization status | Partial | Raw grayscale uint8 arrays / PNG (not binarized) |
| 12 | Artifact types | Partial | Historical aging partially preserved; heavy downsampling introduces quantization artifacts |
| 13 | Color mode | Partial | Grayscale (K-MNIST/K-49 raw arrays, K-Kanji PNG) |
| 14 | Font variety | Not present | Handwriting only — historical Kuzushiji cursive (no fonts) |

**Coverage legend**: Well-covered | Partial | Negatives only | Not present

##### 13.3 Corpus Role & Constraints

> **Status**: Primary training source for script_cls (JPAN handwritten) and handwriting heads;
> low-resolution negatives for resolution quality head.
>
> Pre-modern Japanese cursive character corpus providing 481,336 images across three sub-datasets.
> Use K-49 train split (232K) stratified to ~6,000 for script detection to avoid class imbalance.
> K-Kanji (140K, 3,832 classes) contributes rare Kanji diversity but requires class weighting.
> CC BY-SA 4.0 ShareAlike license: internal training is permitted; publishing derived datasets/models
> requires ShareAlike compliance. 28×28 px images MUST be upscaled to ≥224 px (INTER_CUBIC or
> INTER_LANCZOS4) before SigLIP2 inference — use as hard negatives for resolution quality head.
> K-MNIST test split (10,000) and K-49 test split (38,547) RESERVED for benchmark evaluation.
