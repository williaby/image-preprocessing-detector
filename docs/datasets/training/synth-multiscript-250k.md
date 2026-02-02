#### Synthetic Multi-Script Dataset (OpenLID-Integrated)

> **Quick Stats**: 250,000 images | 27 scripts | 198 languages | Synthetic documents
>
> **License**: MIT | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Synthetic Multi-Script Document Dataset |
| **Short Code** | `synth-multiscript` |
| **Version** | 1.0 |
| **Text Source** | [OpenLID-v2](https://huggingface.co/datasets/laurievb/OpenLID-v2) (198 languages) |
| **Generator** | `src/image_preprocessing_detector/synthetic/generator.py` |
| **License** | MIT |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 250,000 |
| **Train Split** | 200,000 (80%) |
| **Val Split** | 25,000 (10%) |
| **Test Split** | 25,000 (10%) |
| **Scripts** | 27 ISO 15924 scripts |
| **Languages** | 198 OpenLID-v2 language varieties |
| **File Format** | PNG |

##### Script Coverage (27 Scripts)

| Tier | Scripts | % of Dataset |
|------|---------|--------------|
| **Tier 1 (High)** | Latn, Arab, Hans, Cyrl, Deva, Hant | 48% |
| **Tier 2 (Medium)** | Jpan, Kore, Beng, Thai, Taml, Hebr, Telu, Grek, Gujr, Knda | 29% |
| **Tier 3 (Lower)** | Mlym, Guru, Mymr, Tibt, Sinh, Khmr, Laoo, Geor, Armn, Ethi, Orya | 23% |

##### Quality Tier Distribution

| Quality Tier | Overall Quality | % | Augmentation |
|--------------|-----------------|---|--------------|
| PRISTINE | 0.95-1.00 | 10% | None |
| HIGH | 0.80-0.95 | 25% | Light (Albumentations) |
| MEDIUM | 0.60-0.80 | 35% | Moderate |
| LOW | 0.40-0.60 | 20% | Heavy |
| DEGRADED | 0.00-0.40 | 10% | Heavy + extras |

##### Resolution Tiers (NaFlex Optimized)

| Tier | Width | % | Use Case |
|------|-------|---|----------|
| LOW | 500-700px | 20% | Fast inference, simple scripts |
| MEDIUM | 700-1000px | 50% | SigLIP sweet spot |
| HIGH | 1000-1400px | 30% | Complex scripts (CJK, Tibetan) |

##### IQA Labels (8 Dimensions)

| Label | Description |
|-------|-------------|
| `blur` | Gaussian, motion, median blur |
| `noise` | Sensor/paper texture noise |
| `compression` | JPEG compression artifacts |
| `ink_degradation` | Ink bleed, fading, low ink |
| `paper_degradation` | Texture, stains, aging |
| `geometric_distortion` | Rotation, perspective warping |
| `bleed_through` | Show-through from reverse |
| `overall_quality` | Composite score (0-1) |

##### Document Composition

| Type | % | Description |
|------|---|-------------|
| Single-script | 35% | Pure script samples |
| Two-script | 45% | Bilingual documents |
| Three-script | 12% | Complex multilingual |
| Four+-script | 3% | Edge cases |

##### Key Features

- **Language Diversity**: 198 languages from OpenLID-v2 corpus (vs single-language samples)
- **Script-Confusable Pairs**: Includes kas_Arab/kas_Deva, ace_Arab/ace_Latn for robustness
- **Weighted Language Sampling**: Major languages weighted higher (eng 15%, spa 10%, fra 8%, etc.)
- **Layout Variety**: 11 layout types (stacked, columns, form, interleaved, etc.)
- **Text Density**: 5 levels (minimal → dense)
- **IQA Independence**: Quality distribution independent of script (prevents spurious correlations)

##### Project Usage

- **Path**: `/mnt/e/image_detection/03_training_datasets/synthetic_multiscript_v2/`
- **Phase(s)**: Phase 10B (Script Detection Training)
- **Purpose**: Primary training dataset for 27-class script detection with SigLIP
- **Model Target**: SigLIP v2 NaFlex (Native Flexible resolution)

---

#### Additional Script Detection Resources (Not Downloaded)

The following datasets may be valuable but require manual download or registration:

| Dataset | Scripts | Format | Source | Notes |
|---------|---------|--------|--------|-------|
| **SIW-13** | Tibetan, Hebrew, Cyrillic, Thai (13 scripts) | JPG | [Project](https://xbai.vlrlab.net/mspnProjectPage/) | ⚠️ Download link broken |
| **MTHv2** | Mongolian, Tibetan | PNG | [GitHub](https://github.com/HCIILAB/MTHv2_Datasets_Release) | Historical documents (Chinese, not Tibetan) |
| **SleukRith-Set** | Khmer | PNG | [GitHub](https://github.com/donavaly/SleukRith-Set) | Cambodian palm leaf manuscripts |
| **ARDIS** | Arabic digits | PNG | [ARDIS](https://ardisdataset.github.io/ARDIS/) | Arabic-Indic digit dataset |
| **Bengali AI CV19** | Bengali | PNG | [Kaggle](https://www.kaggle.com/c/bengaliai-cv19/data) | Bengali grapheme classification |
| **HangulDB** | Korean | - | [GitHub](https://github.com/callee2006/HangulDB) | Korean Hangul characters |
| **HIT-OR3C** | Chinese | - | [IAPR-TC11](http://www.iapr-tc11.org/mediawiki/index.php/HIT-OR3C) | Chinese characters |
| **DDI-100** | Cyrillic | JPG | [GitHub](https://github.com/machine-intelligence-laboratory/DDI-100) | 300 GB - too large |
| **DocHPLT** | 50+ languages | Text | [HuggingFace](https://huggingface.co/datasets/HPLT/DocHPLT) | For synthetic generation |

---
