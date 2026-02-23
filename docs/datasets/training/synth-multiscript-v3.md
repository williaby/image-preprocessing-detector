---
l4_category: training-dataset
l4_dataset: synth-multiscript-v3
l4_workstream: WS2
l4_generation_script: scripts/generate_base_dataset_v3.py
l4_gcs_path: gs://image_detection_b/synth_multiscript_v3/
l4_image_count: 350012
l4_status: active
---

#### Synthetic Multi-Script Dataset v3 (synth-multiscript-v3)

> **Quick Stats**: 350,012 images (✅ Complete in total count) | 27 scripts | 198 languages | Synthetic documents | Layer 2 v2.3
>
> **GCS Audit 2026-02-21**: `gs://image_detection_b/synth_multiscript_v3/` — 350,012 jpg images across 27 script
> folders (confirmed by live `gsutil ls` jpg count). Generation target was met. However, distribution is
> severely imbalanced (generator bug confirmed): Arab 49,169 (3.8x target), 17 scripts below the 12,963
> target. Status: ✅ Complete (350,012 images) — ⚠️ Imbalanced distribution (needs rebalancing, not
> regeneration from scratch). The previous 190,485 count was from an incomplete GCS listing made before
> all sidecar .json files existed. Each image has a paired .json sidecar.
>
> **Script composition note**: v3 contains Armn (Armenian) and Grek (Greek) instead of Cher (Cherokee)
> and Cans (Canadian Aboriginal Syllabics) from the original design. Kore is used for Korean (not Hang).
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
| **v3.0** | **350,012** *(target met — but distribution imbalanced: Arab 49K, 17 scripts below 12,963 target; generator bug confirmed)* | **JPEG q95** | **~285 GB** | **Pristine base, v2.3 schema, CJK vertical text, generation provenance, ±22 deg skew, English secondary weighting, chunked generation** |

##### Dataset Statistics (Actual)

| Metric | Value |
|--------|-------|
| **Total Images** | 350,012 *(GCS-confirmed by live gsutil ls jpg count, 2026-02-21; generation target met — ⚠️ distribution imbalanced, see per-script table below)* |
| **Total Metadata** | 350,012 paired .json sidecars (each image has a paired sidecar) |
| **Train Split** | ~280,010 (80% estimate) |
| **Val Split** | ~35,001 (10% estimate) |
| **Test Split** | ~35,001 (10% estimate) |
| **Split Registry** | 345,638 entries (Unraid-based; GCS subset uses `splits.jsonl` at GCS prefix root) |
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

##### Script Coverage (27 Scripts, Actual Counts — GCS jpg count 2026-02-21)

> **Distribution Warning**: Generator bug caused severe imbalance. Arab is 3.8x the per-script target (12,963).
> 17 scripts are below target. Dataset needs rebalancing before training, not regeneration from scratch.
> Scripts present differ from original design: Armn and Grek replace Cher and Cans; Kore used for Korean (not Hang).

| Script | Count | vs Target | Script | Count | vs Target | Script | Count | vs Target |
|--------|-------|-----------|--------|-------|-----------|--------|-------|-----------|
| Arab | 49,169 | ⚠️ 3.8x | Armn | 21,538 | ⚠️ 1.7x | Beng | 18,872 | ⚠️ 1.5x |
| Cyrl | 23,424 | ⚠️ 1.8x | Ethi | 17,942 | ⚠️ 1.4x | Grek | 18,160 | ⚠️ 1.4x |
| Hans | 24,130 | ⚠️ 1.9x | Hant | 14,486 | ✅ | Guru | 14,657 | ✅ |
| Latn | 19,449 | ⚠️ 1.5x | Jpan | 11,995 | ❌ -968 | Knda | 11,038 | ❌ -1,925 |
| Laoo | 9,736 | ❌ -3,227 | Deva | 8,901 | ❌ -4,062 | Mlym | 8,509 | ❌ -4,454 |
| Geor | 8,458 | ❌ -4,505 | Orya | 7,626 | ❌ -5,337 | Gujr | 7,577 | ❌ -5,386 |
| Khmr | 6,642 | ❌ -6,321 | Taml | 6,112 | ❌ -6,851 | Hebr | 6,512 | ❌ -6,451 |
| Kore | 6,120 | ❌ -6,843 | Mymr | 5,787 | ❌ -7,176 | Tibt | 5,803 | ❌ -7,160 |
| Sinh | 5,930 | ❌ -7,033 | Telu | 5,750 | ❌ -7,213 | Thai | 5,689 | ❌ -7,274 |

**Total**: 350,012 | **Target per script**: 12,963 | **Scripts at/above target**: 10 | **Scripts below target**: 17

##### CJK Vertical Text (Tategaki) (Validated)

| Script | Actual TTB % | Target | Status |
|--------|-------------|--------|--------|
| **Jpan** (Japanese) | 30.0% (3,599/11,995) | 30% | PASS |
| **Hans** (Simplified Chinese) | 10.0% (2,413/24,130) | 10% | PASS |
| **Hant** (Traditional Chinese) | 10.2% (1,478/14,486) | 10% | PASS |

Total vertical text samples: ~7,490 (estimated at 30%/10%/10% of confirmed per-script counts).

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
| **Script Detection** | 350K (direct, GCS-confirmed) — ⚠️ requires rebalancing before training | All base images on GCS | None | Native DPI |
| **Orientation** | 50K | 12.5K x 4 rotations | Rotation + light degradation | 224px |
| **Skew** | 50-80K synth + 19K natural | Stratified by script/DPI | Orient + skew(±45 deg, 42 bins) + hybrid degradation | 384px |
| **Resolution Quality** | 30K | Stratified across 7 DPI | Char height measurement + light degradation | 224px |
| **IQA Pseudo-Labels** | 100K | Diverse subset | Hybrid degradation with parameter replay | 384px |
| **Shadow** | 15K | Diverse subset | Shadow overlay (Augraphy) | 384px |
| **Warping** | 20K | Diverse subset | Perspective/page curl | 384px |

##### Generation Commands

```bash
# Target: 350K images (~2 days on 6-core Xeon). Target met at 350,012 images.
# Note: Generator bug caused severe distribution imbalance (Arab 49K, 17 scripts below 12,963 target).
# Rebalancing required before training use; do not regenerate from scratch.
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
| Total image count | PASS | 350,012 jpg images on GCS (confirmed 2026-02-21 by live gsutil ls count) |
| Corrupt images | PASS | Each image has paired .json sidecar (350,012 pairs) |
| Script distribution | ⚠️ WARN | Severely imbalanced — Arab 49,169 (3.8x target), 17 scripts below 12,963 target. Rebalancing required. |
| CJK vertical text | PASS | Jpan 30.0%, Hans 10.0%, Hant 10.2% |
| Split registry | PASS | SHA256-keyed splits.jsonl at GCS prefix root |
| Font diversity | PASS | 27 scripts, 15 with 5+ font families |
| Schema version | PASS | 100% v2.3.0 |
| Script composition | NOTE | Armn + Grek present instead of Cher + Cans from original design; Kore used for Korean (not Hang) |

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
