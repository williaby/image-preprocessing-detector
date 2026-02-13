#### Synthetic Multi-Script Dataset v3 (OpenLID-Integrated)

> **Quick Stats**: 350,000 images | 27 scripts | 198 languages | Synthetic documents | Layer 2 v2.3
>
> **License**: MIT | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Synthetic Multi-Script Document Dataset |
| **Short Code** | `synth-multiscript` |
| **Version** | 3.0 |
| **Text Source** | [OpenLID-v2](https://huggingface.co/datasets/laurievb/OpenLID-v2) (198 languages) |
| **Generator** | `src/image_preprocessing_detector/synthetic/generator.py` |
| **Generation Script** | `scripts/generate_base_dataset_v3.py` |
| **Validation Script** | `scripts/validate_base_dataset_v3.py` |
| **Schema Version** | Layer 2 Enrichment v2.3.0 |
| **License** | MIT |
| **Documentation Status** | Complete |

##### Version History

| Version | Images | Format | Key Changes |
|---------|--------|--------|-------------|
| v1.0 | 27,000 | PNG | Initial generation, 3-tier DPI |
| v2.0 | 250,000 | PNG | 7-tier DPI, color modes, document age, hybrid augmentation |
| **v3.0** | **350,000** | **JPEG q95** | **Pristine base, v2.3 schema, CJK vertical text, generation provenance, ±22 deg skew, English secondary weighting** |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 350,000 |
| **Train Split** | 280,000 (80%) |
| **Val Split** | 35,000 (10%) |
| **Test Split** | 35,000 (10%) |
| **Scripts** | 27 ISO 15924 scripts |
| **Languages** | 198 OpenLID-v2 language varieties |
| **File Format** | JPEG quality 95 (~200 KB/image) |
| **Total Size** | ~70 GB |
| **Image Storage** | Pristine (no degradation baked in) |

##### Key Design: Pristine Base + Deferred Degradation

v3 stores base images as **pristine** (no degradation or geometric transforms applied). Degradation parameters are recorded in metadata for reproducible replay. Derived task-specific views apply their own transforms at derivation time.

**Rationale**:

- Resolution quality views need pristine char heights
- Skew views apply degradation AFTER geometric transforms
- IQA views can replay degradation with exact parameters for ground-truth labels
- No information loss; maximum downstream flexibility

##### Script Coverage (27 Scripts)

| Tier | Scripts | % of Dataset |
|------|---------|--------------|
| **Tier 1 (High)** | Latn, Arab, Hans, Cyrl, Deva, Hant | 48% |
| **Tier 2 (Medium)** | Jpan, Kore, Beng, Thai, Taml, Hebr, Telu, Grek, Gujr, Knda | 29% |
| **Tier 3 (Lower)** | Mlym, Guru, Mymr, Tibt, Sinh, Khmr, Laoo, Geor, Armn, Ethi, Orya | 23% |

##### CJK Vertical Text (Tategaki) (v3.0 NEW)

Scripts supporting both horizontal and vertical writing generate both orientations:

| Script | Vertical (TTB) % | Horizontal (LTR) % |
|--------|-------------------|---------------------|
| **Jpan** (Japanese) | 30% | 70% |
| **Hans** (Simplified Chinese) | 10% | 90% |
| **Hant** (Traditional Chinese) | 10% | 90% |

Metadata records `text_direction` per language block and `text_directions_present` at document level.

##### Document Composition

| Type | % | Description |
|------|---|-------------|
| Single-script | 45% | Pure script samples |
| Two-script | 38% | Bilingual documents |
| Three-script | 10% | Complex multilingual |
| Four+-script | 2% | Edge cases |
| Priority pairs | 5% | High-value script pairs |

**English Secondary Weighting** (v3.0 NEW): In multi-script compositions, Latn (English) is weighted at 40% probability as the secondary script, mirroring real-world multilingual documents.

##### Quality Tier Distribution

| Quality Tier | Overall Quality | % | Augmentation |
|--------------|-----------------|---|--------------|
| PRISTINE | 0.95-1.00 | 10% | None |
| HIGH | 0.80-0.95 | 25% | Light (Albumentations) |
| MEDIUM | 0.60-0.80 | 35% | Moderate |
| LOW | 0.40-0.60 | 20% | Heavy |
| DEGRADED | 0.00-0.40 | 10% | Heavy + extras |

**Hybrid Augmentation Pipeline**: Augraphy (document-specific: bleed-through, ink degradation, paper aging, bookbinding, dirty drum, folding) + Albumentations (general: blur, noise, compression, color jitter). Order: Augraphy first, Albumentations second.

**Document Age** (v2.0+): 80% modern, 15% aged (yellowing, foxing), 5% historical (ink fading, paper degradation).

##### Resolution Tiers (7 DPI Tiers)

| Tier | DPI | Width Range | Weight | Use Case |
|------|-----|-------------|--------|----------|
| VERY_LOW | 72 | 500-700px | 8% | Screen-resolution documents |
| LOW | 100 | 700-900px | 10% | Low-quality scans |
| MEDIUM_LOW | 150 | 900-1200px | 12% | Draft-quality scans |
| MEDIUM | 200 | 1200-1600px | 15% | Standard office scans |
| STANDARD | 300 | 1800-2400px | 30% | Standard OCR quality |
| HIGH | 400 | 2400-3200px | 15% | High-quality scans |
| VERY_HIGH | 600 | 3600-4800px | 10% | Archival/professional |

##### Resolution Quality Labels (v2.3)

| Field | Type | Description |
|-------|------|-------------|
| `character_height_px` | float | Best available char height (prefer clean) |
| `character_height_clean_px` | float | Pre-degradation measurement |
| `character_height_degraded_px` | float | Post-degradation measurement |
| `character_height_analytical_px` | float | font_size_pt * DPI / 72 (theoretical) |
| `character_height_rendered_px` | float | **v3 NEW**: Actual rendered glyph height via CC analysis on pristine image |
| `resolution_quality_score` | float | Piecewise score 0-1 |
| `coarse_bucket` | str | needs_major_upscale / needs_light_upscale / optimal / good / oversized |
| `font_size_pt` | float | Pillow font size used |
| `target_dpi` | int | DPI tier target |
| `measurement_method` | str | sauvola_cc_v2 |
| `label_provenance` | str | tier_0_exact (synthetic ground truth) |
| `label_source` | str | synthetic_exact |
| `label_confidence` | float | 1.0 (exact ground truth) |

> Coarse bucket thresholds: <16px major, 16-32px light, 32-48px optimal, 48-96px good, >96px oversized

##### Geometric Labels (v3.0 Expanded)

| Field | Type | Description |
|-------|------|-------------|
| `orientation_class` | int | 0, 90, 180, or 270 degrees |
| `skew_angle_degrees` | float | **±22 deg** (expanded from ±10 deg in v2) |

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

##### Text Direction Labels (v3.0 NEW)

| Field | Type | Scope | Description |
|-------|------|-------|-------------|
| `text_direction` | str | Per-language | `"ltr"`, `"rtl"`, or `"ttb"` for this language block |
| `text_directions_present` | list[str] | Document-level | All directions in the image (e.g., `["ltr", "ttb"]`) |

##### Generation Provenance (v3.0 NEW)

Per-image metadata includes `generation_params` at the top level (alongside `data` and `schema_version`):

| Field | Type | Description |
|-------|------|-------------|
| `font_families_used` | list[str] | Font families used for rendering |
| `degradation_seed` | int | RNG seed for reproducible degradation replay |
| `base_image_sha256` | str | SHA256 hash for global split registry integration |

##### Color Modes

| Mode | % | Description |
|------|---|-------------|
| Color | 60% | Full RGB |
| Grayscale | 30% | Single channel |
| Binarized | 10% | Black and white |

##### Layout Types (11 Types)

| Layout | Weight | Description |
|--------|--------|-------------|
| STACKED | 24% | Vertical text blocks |
| TWO_COLUMN | 18% | Newspaper/academic style |
| THREE_COLUMN | 8% | Dense reference material |
| FORM | 12% | Structured field-value pairs |
| INTERLEAVED | 10% | Alternating script blocks |
| CENTERED | 8% | Title pages, certificates |
| GRID | 5% | Table-like structure |
| SIDEBAR | 5% | Main content + sidebar |
| HEADER_BODY | 5% | Header + body text |
| DENSE_TEXT | 4% | Full-page dense text |
| MIXED | 1% | Random mixed layout |

##### Project Usage

| Attribute | Value |
|-----------|-------|
| **Local Path** | `synthetic_multiscript_v3/` (via `--output-dir`) |
| **GCS Path** | `gs://image_detection_b/synth_multiscript_v3/` |
| **Split Registry** | Global SHA256-keyed JSONL (prevents cross-dataset leakage) |
| **Phase(s)** | SigLIP 2 Multi-Task Training, MobileNetV4 Training |
| **Purpose** | Pristine base from which all synthetic training views are derived |

##### Derived Task-Specific Views

v3 serves as the single base from which all synthetic training datasets are derived:

| View | Count | Source Selection | Transforms | Output Size |
|------|-------|-----------------|------------|-------------|
| **Script Detection** | 350K (direct) | All base images | None | Native DPI |
| **Orientation** | 50K | 12.5K x 4 rotations | Rotation + light degradation | 224px |
| **Skew** | 50-80K synth + 19K natural | Stratified by script/DPI | Orient + skew(±45 deg, 42 bins) + hybrid degradation | 384px |
| **Resolution Quality** | 30K | Stratified across 7 DPI | Char height measurement + light degradation | 224px |
| **IQA Pseudo-Labels** | 100K | Diverse subset | Hybrid degradation with parameter replay | 384px |
| **Shadow** | 15K | Diverse subset | Shadow overlay (Augraphy) | 384px |
| **Warping** | 20K | Diverse subset | Perspective/page curl | 384px |

##### Generation Commands

```bash
# Full production generation (350K images, ~2 days on GPU machine)
python scripts/generate_base_dataset_v3.py \
    --output-dir /path/to/synthetic_multiscript_v3 \
    --total-images 350000 \
    --workers 4 \
    --seed 42 \
    --augmenter hybrid \
    --yes

# Validation (run after generation completes)
python scripts/validate_base_dataset_v3.py \
    --dataset-dir /path/to/synthetic_multiscript_v3

# Resume interrupted generation
python scripts/generate_base_dataset_v3.py \
    --output-dir /path/to/synthetic_multiscript_v3 \
    --total-images 350000 \
    --workers 4 \
    --seed 42 \
    --augmenter hybrid \
    --resume \
    --yes
```

##### Key Features

- **Language Diversity**: 198 languages from OpenLID-v2 corpus
- **Script-Confusable Pairs**: Includes kas_Arab/kas_Deva, ace_Arab/ace_Latn for robustness
- **English Secondary Weighting**: 40% probability as secondary script in multi-script compositions
- **CJK Vertical Text**: Jpan 30% TTB, Hans/Hant 10% TTB with per-block direction metadata
- **Pristine Base**: No degradation baked in; derived views apply transforms with full control
- **Generation Provenance**: SHA256, degradation seeds, and font families recorded per image
- **Global Split Registry**: SHA256-keyed JSONL prevents cross-dataset train/test leakage
- **Hybrid Augmentation**: Augraphy (document effects) + Albumentations (general effects)
- **IQA Independence**: Quality distribution independent of script (prevents spurious correlations)

##### Deprecated Versions

| Version | Path | Status |
|---------|------|--------|
| v1.0 (27K) | `synthetic_multiscript/` | **DELETED** |
| v2.0 (250K) | `synthetic_multiscript_full/` | **DELETED** |
| v2.0-aug | `synthetic_multiscript_augmented/` | **DELETED** |
| Linux copy | `data/synthetic_250k/` | **DELETED** |

All old dataset copies were removed to prevent confusion with v3.

---

#### Additional Script Detection Resources (Not Downloaded)

The following datasets may be valuable but require manual download or registration:

| Dataset | Scripts | Format | Source | Notes |
|---------|---------|--------|--------|-------|
| **SIW-13** | Tibetan, Hebrew, Cyrillic, Thai (13 scripts) | JPG | [Project](https://xbai.vlrlab.net/mspnProjectPage/) | Download link broken |
| **MTHv2** | Mongolian, Tibetan | PNG | [GitHub](https://github.com/HCIILAB/MTHv2_Datasets_Release) | Historical documents |
| **SleukRith-Set** | Khmer | PNG | [GitHub](https://github.com/donavaly/SleukRith-Set) | Palm leaf manuscripts |
| **ARDIS** | Arabic digits | PNG | [ARDIS](https://ardisdataset.github.io/ARDIS/) | Arabic-Indic digit dataset |
| **Bengali AI CV19** | Bengali | PNG | [Kaggle](https://www.kaggle.com/c/bengaliai-cv19/data) | Grapheme classification |
| **HangulDB** | Korean | - | [GitHub](https://github.com/callee2006/HangulDB) | Korean Hangul characters |
| **HIT-OR3C** | Chinese | - | [IAPR-TC11](http://www.iapr-tc11.org/mediawiki/index.php/HIT-OR3C) | Chinese characters |
| **DDI-100** | Cyrillic | JPG | [GitHub](https://github.com/machine-intelligence-laboratory/DDI-100) | 300 GB - too large |
| **DocHPLT** | 50+ languages | Text | [HuggingFace](https://huggingface.co/datasets/HPLT/DocHPLT) | For synthetic generation |

---
