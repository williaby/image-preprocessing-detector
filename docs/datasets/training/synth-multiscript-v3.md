#### Synthetic Multi-Script Dataset v3 (synth-multiscript-v3)

> **Quick Stats**: 350,012 images | 27 scripts | 198 languages | Synthetic documents | Layer 2 v2.3
>
> **License**: MIT | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Synthetic Multi-Script Document Dataset v3 |
| **Short Code** | `synth-multiscript-v3` |
| **Version** | 3.0.0 |
| **Text Source** | [OpenLID-v2](https://huggingface.co/datasets/laurievb/OpenLID-v2) (198 languages) |
| **Generator** | `src/image_preprocessing_detector/synthetic/generator.py` |
| **Generation Script** | `scripts/generate_base_dataset_v3.py` |
| **Validation Script** | `scripts/validate_base_dataset_v3.py` |
| **Schema Version** | Layer 2 Enrichment v2.3.0 |
| **License** | MIT |
| **Generated** | 2026-02-12 to 2026-02-15 |

##### Version History

| Version | Images | Format | Size | Key Changes |
|---------|--------|--------|------|-------------|
| v1.0 | 27,000 | PNG | ~50 GB | Initial generation, 3-tier DPI |
| v2.0 | 250,000 | PNG | ~800 GB | 7-tier DPI, color modes, document age, hybrid augmentation |
| **v3.0** | **350,012** | **JPEG q95** | **285 GB** | **Pristine base, v2.3 schema, CJK vertical text, generation provenance, ±22 deg skew, English secondary weighting, chunked generation** |

##### Dataset Statistics (Actual)

| Metric | Value |
|--------|-------|
| **Total Images** | 350,012 |
| **Total Metadata** | 350,011 (1 orphan image) |
| **Train Split** | 276,060 (79.9%) |
| **Val Split** | 34,444 (10.0%) |
| **Test Split** | 35,134 (10.2%) |
| **Split Registry** | 345,638 entries |
| **Scripts** | 27 ISO 15924 scripts |
| **Languages** | 198 OpenLID-v2 language varieties |
| **File Format** | JPEG quality 95 |
| **Total Size** | 285 GB (images + metadata) |
| **Metadata Size** | ~2.3 GB (JSON only) |
| **Image Storage** | Pristine (no degradation baked in) |
| **Schema Version** | 100% v2.3.0 |

##### Key Design: Pristine Base + Deferred Degradation

v3 stores base images as **pristine** (no degradation or geometric transforms applied). Degradation parameters are recorded in metadata for reproducible replay. Derived task-specific views apply their own transforms at derivation time.

**Rationale**:

- Resolution quality views need pristine char heights
- Skew views apply degradation AFTER geometric transforms
- IQA views can replay degradation with exact parameters for ground-truth labels
- No information loss; maximum downstream flexibility

##### Script Coverage (27 Scripts, Actual Counts)

| Script | Count | Script | Count | Script | Count |
|--------|-------|--------|-------|--------|-------|
| Latn | 28,295 | Arab | 27,168 | Deva | 27,260 |
| Hans | 15,078 | Tibt | 13,302 | Hant | 12,258 |
| Mlym | 12,260 | Orya | 12,265 | Ethi | 12,158 |
| Thai | 12,168 | Guru | 12,049 | Grek | 12,025 |
| Taml | 12,001 | Cyrl | 11,980 | Jpan | 11,973 |
| Armn | 11,971 | Knda | 11,960 | Laoo | 11,937 |
| Beng | 10,387 | Kore | 6,049 | Mymr | 6,044 |
| Hebr | 6,018 | Telu | 5,997 | Gujr | 5,951 |
| Sinh | 5,825 | Khmr | 5,791 | Geor | 5,732 |

##### CJK Vertical Text (Tategaki) (Validated)

| Script | Actual TTB % | Target | Status |
|--------|-------------|--------|--------|
| **Jpan** (Japanese) | 30.0% (3,593/11,995) | 30% | PASS |
| **Hans** (Simplified Chinese) | 10.0% (2,402/24,130) | 10% | PASS |
| **Hant** (Traditional Chinese) | 10.2% (1,480/14,486) | 10% | PASS |

Total vertical text samples: 6,352.

##### Document Composition (Actual)

| Type | Count | % |
|------|-------|---|
| Single-script | 85,666 | 44.9% |
| Two-script | 82,008 | 43.0% |
| Three-script | 18,924 | 9.9% |
| Four-script | 1,272 | 0.7% |
| Five-script | 1,330 | 0.7% |
| Six-script | 1,285 | 0.7% |

Multi-script total: 104,819 (55.1%). English secondary in multi-script: 25,086 (23.6% of multi-script).

##### Quality Tier Distribution (Actual)

| Quality Tier | Count | % |
|--------------|-------|---|
| PRISTINE | 19,103 | 10.0% |
| HIGH | 47,448 | 24.9% |
| MEDIUM | 66,755 | 35.0% |
| LOW | 38,238 | 20.1% |
| DEGRADED | 18,941 | 9.9% |

**Hybrid Augmentation Pipeline**: Augraphy (document-specific: bleed-through, ink degradation, paper aging, bookbinding, dirty drum, folding) + Albumentations (general: blur, noise, compression, color jitter). Order: Augraphy first, Albumentations second.

**Document Age** (v2.0+): 80% modern, 15% aged (yellowing, foxing), 5% historical (ink fading, paper degradation).

##### Resolution Tier Distribution (Actual)

| Tier | DPI | Count | % |
|------|-----|-------|---|
| VERY_LOW | 72 | 15,491 | 8.1% |
| LOW | 100 | 22,715 | 11.9% |
| MEDIUM_LOW | 150 | 28,551 | 15.0% |
| MEDIUM | 200 | 38,285 | 20.1% |
| STANDARD | 300 | 47,285 | 24.8% |
| HIGH | 400 | 22,890 | 12.0% |
| VERY_HIGH | 600 | 15,268 | 8.0% |

##### Layout Types (11 Generator Types -> 4 Layer 2 Types)

The generator uses 11 internal layout types, mapped to Layer 2 `LayoutType` values via `LAYOUT_TO_LAYER2`:

| Generator Type | Count | Layer 2 Value |
|---------------|-------|---------------|
| columns | 50,879 | `multi_column` |
| header_body | 45,632 | `single_column` |
| interleaved | 32,976 | `single_column` |
| stacked | 18,950 | `single_column` |
| form | 10,318 | `form_based` |
| captioned | 6,903 | `single_column` |
| sidebar | 6,872 | `multi_column` |
| header_body_footer | 6,811 | `single_column` |
| single_line | 4,168 | `single_column` |
| short_blocks | 3,530 | `complex` |
| dense_text | 3,446 | `single_column` |

**Layer 2 distribution** (in metadata JSON files):

| Layout Type | % |
|-------------|---|
| `single_column` | 64.3% |
| `multi_column` | 24.9% |
| `form_based` | 8.2% |
| `complex` | 2.6% |

##### Resolution Quality Labels (v2.3)

| Field | Type | Description |
|-------|------|-------------|
| `character_height_px` | float | Best available char height (prefer clean) |
| `character_height_clean_px` | float | Pre-degradation measurement |
| `character_height_degraded_px` | float | Post-degradation measurement |
| `character_height_analytical_px` | float | font_size_pt * DPI / 72 (theoretical) |
| `character_height_rendered_px` | float | Actual rendered glyph height via CC analysis on pristine image |
| `resolution_quality_score` | float | Piecewise score 0-1 |
| `coarse_bucket` | str | needs_major_upscale / needs_light_upscale / optimal / good / oversized |
| `font_size_pt` | float | Pillow font size used |
| `target_dpi` | int | DPI tier target |
| `measurement_method` | str | sauvola_cc_v2 |
| `label_provenance` | str | tier_0_exact (synthetic ground truth) |
| `label_source` | str | synthetic_exact |
| `label_confidence` | float | 1.0 (exact ground truth) |

> Coarse bucket thresholds: <16px major, 16-32px light, 32-48px optimal, 48-96px good, >96px oversized

##### Geometric Labels

| Field | Type | Description |
|-------|------|-------------|
| `orientation_class` | int | 0, 90, 180, or 270 degrees |
| `skew_angle_degrees` | float | ±22 deg (expanded from ±10 deg in v2) |

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

##### Text Direction Labels

| Field | Type | Scope | Description |
|-------|------|-------|-------------|
| `text_direction` | str | Per-language | `"ltr"`, `"rtl"`, or `"ttb"` for this language block |
| `text_directions_present` | list[str] | Document-level | All directions in the image (e.g., `["ltr", "ttb"]`) |

##### Generation Provenance

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

##### Storage Locations

| Location | Path | Contents |
|----------|------|----------|
| **Unraid NFS** | `/mnt/unraid/appdata/synthetic_multiscript_v3/` | Full dataset (285 GB) |
| **GCS** | `gs://image_detection_b/synth_multiscript_v3/` | Full dataset mirror |
| **E: drive metadata** | `/mnt/e/image_detection/metadata_registry/json/synth-multiscript-v3/` | JSON metadata only (~2.3 GB) |
| **Split Registry** | `splits.jsonl` (in dataset root) | 345,638 SHA256-keyed entries |

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
# Full production generation (350K images, ~2 days on 6-core Xeon)
python scripts/generate_base_dataset_v3.py \
    --output-dir /path/to/synthetic_multiscript_v3 \
    --total-images 350000 \
    --workers 4 \
    --seed 42 \
    --augmenter hybrid \
    --chunk-size 10000 \
    --resume \
    --yes

# Validation (run after generation completes)
python scripts/validate_base_dataset_v3.py \
    --dataset-dir /path/to/synthetic_multiscript_v3
```

**Generation notes**:

- `--chunk-size 10000` restarts workers every 10K images to prevent OOM from augmentation pipeline memory leaks
- `--resume` counts existing `.jpg` files and continues from where it left off
- Generated on Intel Xeon E5-2690 v4 (6 cores/12 threads), 62 GB RAM, NFS storage
- Throughput: ~1.8 img/s sustained with 4 workers

##### Validation Results (2026-02-15)

| Check | Status | Details |
|-------|--------|---------|
| Corrupt images | WARN | 1 orphan image (missing JSON) out of 350,012 |
| CJK vertical text | PASS | Jpan 30.0%, Hans 10.0%, Hant 10.2% |
| Split registry | PASS | 345,638 entries, 80/10/10 split, no leakage |
| Font diversity | PASS | 27 scripts, 15 with 5+ font families |
| Schema version | PASS | 100% v2.3.0 |

##### Deprecated Versions

| Version | Path | Status |
|---------|------|--------|
| v1.0 (27K) | `synthetic_multiscript/` | **DELETED** |
| v2.0 (250K) | `synthetic_multiscript_full/` | **DELETED** |
| v2.0-aug | `synthetic_multiscript_augmented/` | **DELETED** |
| v2.0 metadata | `metadata_registry/json/synth-multiscript-250k/` | **DELETED** |
| Linux copy | `data/synthetic_250k/` | **DELETED** |

All old dataset copies and metadata were removed to prevent confusion with v3.

---

#### Additional Script Detection Resources (Not Downloaded)

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
