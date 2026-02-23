---
l4_category: training-dataset
l4_dataset: resolution-quality
l4_workstream: WS2
l4_source_datasets:
  - diqa-5000
  - ohr-bench
  - realdae
  - synth-multiscript-v3
l4_generation_script: scripts/label_resolution_quality.py
l4_image_count: 30000
l4_status: in_progress
---

# resolution-quality

> **Quick Stats**: 5,499/30,000 images (18%) | char-height-aware regression 0–1 | two-head shared dataset
>
> **Status**: 🔄 In Progress | **MNV4-H3 HAR Score**: 26/100 (Needs Work) | **SIG-G5-5 HAR Score**: 39/100
> (Needs Work) | **P0 Gaps**: 3 (MNV4-H3) + 4 (SIG-G5-5, 3 inherited)

---

## Section 1 — Identity

| Field | Value |
|-------|-------|
| **Dataset Name** | `resolution-quality` |
| **Head(s) Fed** | MNV4-H3 `resolution_quality` (primary gate) + SIG-G5-5 `resolution_quality_reg` (validation head) |
| **Model(s)** | MobileNetV4-Conv-S (MNV4-H3); SigLIP 2 NAFlex (SIG-G5-5) |
| **Task Type** | Regression 0–1 (char-height-aware quality score) |
| **Primary L2 Field(s)** | `resolution.resolution_quality_score` (shared between both heads) |
| **Training Phase** | Phase 4 — Pre-Correction Gate (MNV4-H3 trains first); Phase 5 — Page Attributes (SIG-G5-5) |
| **Target Size** | 30,000 images |
| **Image Size** | 224×224 (MNV4-H3 fixed input); variable NAFlex resolution (SIG-G5-5) |
| **Storage Location** | `E:\image_detection\03_training_datasets\resolution-quality\` |
| **GCS Path** | `gs://image_detection_b/resolution_quality_training/` |
| **Assembly Script** | `scripts/prepare_multitask_datasets.py resolution` (subcommand not yet implemented) |
| **HAR File(s)** | [har/mnv4-h3-resolution-quality.md](../../planning/har/mnv4-h3-resolution-quality.md), [har/sig-g5-resolution-quality-reg.md](../../planning/har/sig-g5-resolution-quality-reg.md) |
| **DDR File** | [diversity_reports/resolution_quality_ddr.md](../diversity_reports/resolution_quality_ddr.md) |

### Role Distinction Between the Two Heads

Both heads read the same L2 label field (`resolution.resolution_quality_score`) from the same 30,000-image
pool. Their training inputs differ:

| Attribute | MNV4-H3 | SIG-G5-5 |
|-----------|---------|---------|
| Input image | RAW (pre-correction) | CORRECTED (post deskew/CLAHE/sharpening) |
| Input resolution | Fixed 224×224 | NAFlex variable resolution |
| Output format | Linear regression 0–1 | Gaussian NLL (mu, sigma_sq) |
| Latency | ~3ms GPU | ~50ms GPU (co-runs with 18 other SigLIP heads) |
| Role | Pre-correction fast gate; triggers upscale when score < 0.4 | Teacher/validation; cross-checks MNV4-H3 drift; CPU fallback |
| Training order | Phase 4 (trains first) | Phase 5 (MNV4-H3 predictions available as weak labels) |
| Priority | P0 | P2 |

---

## Section 2 — Status

| Metric | MNV4-H3 | SIG-G5-5 |
|--------|---------|---------|
| **Assembly Status** | 🔄 In Progress | 🔄 In Progress |
| **Current Count** | 5,499 / 30,000 (18%) | 0 / 30,000 (corrected-image path missing) |
| **HAR Adequacy Score** | 26/100 — ⚠️ Needs Work | 39/100 — ⚠️ Needs Work |
| **P0 Gap Count** | 3 | 4 (3 inherited + 1 SIG-G5-5-specific) |
| **Primary Blockers** | OHR-Bench and RealDAE not labeled; multi-DPI rendering pipeline not built | All MNV4-H3 blockers + corrected-image assembly path not implemented |
| **Estimated Unblock Effort** | 3–4 days (labeling) + 2–3 days (multi-DPI pipeline) | 1 additional day (corrected-image assembly) |
| **Last HAR Updated** | 2026-02-23 | 2026-02-23 |

**Bootstrap Path**: Bootstrap training can begin immediately on the 5,499 DIQA-5000 V1 labels to validate
architecture convergence. Do not block on data completion. V2 label precision improvements
(Sauvola + ensemble; target IQR ≤ 4–5px vs. V1 IQR = 9.0px) must be deployed before production training.

---

## Section 3 — Source Pool Analysis

**Required L2 Field**: `resolution.resolution_quality_score` (float 0–1, char-height-aware)
**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better)
**Label Provenance**: tier_3_heuristic (V1: PaddleOCR DBNet + CC analysis). V2 will upgrade to
tier_2_model (Sauvola binarization + ensemble + calibration) once implemented.

### Candidate Source Datasets

| Source Dataset | Total Images | Field Populated | Coverage % | Conf ≥ 0.7 | Usable |
|----------------|-------------|-----------------|------------|-------------|--------|
| DIQA-5000 | 5,500 | Yes (V1 complete) | 99.9% (5,499 labeled, 1 error) | ~80% est. (precision degrades near bucket boundaries) | ✅ 5,499 |
| OHR-Bench | 8,500 | No | 0% | — | ⚠️ 0 (ready to label — Gap RQ-MNV4-G01) |
| RealDAE | 1,200 | No | 0% | — | ⚠️ 0 (ready to label — Gap RQ-MNV4-G02) |
| DocLayNet (multi-DPI renders) | 81,000 source pages (subset) | No | 0% | — | ⚠️ 0 (needs rendering pipeline — Gap RQ-MNV4-G03) |
| synth-multiscript-v3 | 190,485 | No (DPI known at generation) | 0% via L2 | tier_0_exact via sidecar | ⚠️ 0 (derivable from generator metadata) |

### Pool Summary

| Metric | Value |
|--------|-------|
| **Total usable (current)** | 5,499 images |
| **Total usable (post-P0, labeling only)** | ~15,199 images (DIQA-5000 + OHR-Bench + RealDAE) |
| **Total usable (post-P0, full)** | ~30,000 images (above + DocLayNet multi-DPI renders) |
| **Training target** | 30,000 images |
| **Pool surplus/deficit** | −24,501 (−82% of target) |
| **Real vs. synthetic ratio** | 100% real documents (labels derived from actual image measurements; no synthetic generation) |

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
|-----------|---------------|-------|-------------|--------|
| RQ-MNV4-D01 | DIQA-5000 | `resolution.char_height_px` | V1 median IQR = 9.0px vs. 2–3px target; 54% cross-bucket rate near boundary values | Open — V2 Sauvola strategy planned |
| RQ-MNV4-D02 | DIQA-5000 | `resolution.resolution_quality_score` | Score compression: 83% of images fall in 2.5–3.2 MOS range after bucket normalization, limiting regression gradient signal | Open — V2 score distribution review needed |
| RQ-MNV4-D03 | DIQA-5000 | `resolution.char_height_px` | CJK radical fragmentation: disconnected strokes fragment into short CCs, deflating median char_height for CJK documents | Open — V2 Phase A morphological closing addresses this |

### Known Issues

| KI Code | Description | Impact |
|---------|-------------|--------|
| KI-RQ-01 | PaddleOCR v2 ONLY (`paddleocr>=2.7,<3.0`) — v3 API completely incompatible; labeling pipeline silently fails on v3 | HIGH — version pin must be enforced in requirements |
| KI-RQ-02 | SIGILL on Intel Broadwell CPUs: PaddlePaddle CPU path hits illegal instruction (no AVX-512) | MEDIUM — labeling must run on GPU VM (Vultr A100 or equivalent) |
| KI-RQ-03 | V1 precision: median IQR 9.0px (target 2–3px), 54% cross-bucket rate; bootstrap OK, production requires V2 | MEDIUM — V2 strategy documented in RESOLUTION_QUALITY_V2_STRATEGY.md |
| KI-RQ-04 | Born-digital low-DPI paradox: large fonts at 72 DPI yield high char_height despite low effective resolution — the label is correct but training distribution must include these examples | MEDIUM — Gap RQ-MNV4-G05; OOD-Resolution 6a tests this |
| KI-G5-5-01 | CLAHE over-enhancement creates distribution shift for SIG-G5-5: corrected images appear higher quality; if CLAHE settings change in production, SIG-G5-5 silently drifts | HIGH — SIG-G5-5 specific; KI-G5-5-01 |
| KI-G5-5-02 | Post-upscale artifacts: if MNV4-H3 triggers upscaling, SIG-G5-5 sees the upscaled image; bicubic upscale creates ringing artifacts not in training data | MEDIUM — SIG-G5-5 specific |

---

## Section 4 — Label Schema

**Primary L2 Field**: `resolution.resolution_quality_score`
**Type**: float
**Range**: 0.0–1.0 (log-normalized, char-height-aware)
**Provenance Tier**: tier_3_heuristic (V1); tier_2_model (V2, target)
**Derivation Formula**: `resolution_quality_score = f(char_height_px)` where char_height is the median
character height measured via PaddleOCR DBNet text detection + connected-component analysis on the image.

### Score-to-Bucket Mapping

| Score Range | Bucket | char_height_px | Interpretation |
|-------------|--------|---------------|----------------|
| 0.0–0.30 | `needs_major_upscale` | < 8px | Document unreadable for OCR |
| 0.30–0.55 | `needs_light_upscale` | 8–24px | Below optimal OCR range |
| 0.55–0.75 | `optimal` | 32–48px | Ideal for OCR engines |
| 0.75–1.0 | `good` | > 48px | Above optimal; no upscaling needed |

Actual measured DIQA-5000 distribution: 49.3% needs_light_upscale / 36.6% optimal / 11.2% good /
2.8% needs_major_upscale.

### V2 Labeling Pipeline (Sauvola Strategy)

V2 precision improvements (IQR target ≤ 4–5px vs. V1 = 9.0px):

- **Phase A** (P0, 1–2d): Sauvola binarization (k=0.2) + morphological closing (3×1 horizontal, 1×3 vertical kernels) + KDE mode estimation → ~6–7px IQR
- **Phase B** (P1, 3–4d): Horizontal projection profiles + ensemble fusion + DBSCAN clustering + font-aware filtering → ~4–5px IQR
- **Script-aware ensemble weighting**: CJK → 0.7 projection / 0.3 CC; Latin → 0.3 projection / 0.7 CC

### Training Manifest Record Schema

```json
{
  "image_path": "resolution_quality/images/{filename}.jpg",
  "source_dataset": "diqa-5000",
  "split": "train",
  "split_type": "train",
  "label_provenance": "tier_3_heuristic",
  "label_confidence": 0.80,
  "resolution_quality_score": 0.52,
  "char_height_px": 28.5,
  "measurement_method": "paddleocr_dbnet_cc",
  "coarse_bucket": "needs_light_upscale",
  "capture_method": "scanner"
}
```

SIG-G5-5 records additionally carry `correction_pipeline_version` to track CLAHE/deskew settings:

```json
{
  "image_path": "resolution_quality/corrected_images/{filename}.jpg",
  "correction_pipeline_version": "v1.2.0",
  "resolution_quality_score": 0.54,
  "char_height_px": 29.1,
  "measurement_method": "paddleocr_dbnet_cc",
  "coarse_bucket": "needs_light_upscale"
}
```

### Label Statistics (DIQA-5000 V1 — current)

| Metric | Value |
|--------|-------|
| **Images labeled** | 5,499 (1 error) |
| **Median char_height_px** | 31px |
| **Median score** | 0.525 |
| **Score IQR** | 9.0px (V1; V2 target ≤ 4–5px) |
| **Cross-bucket rate** | 54% near boundary values (V1 defect) |
| **Anomaly rate** | 3% (KW-validated coarse buckets) |

---

## Section 5 — Composition & Splits

### Target Distribution

| Bucket | Score Range | Target % | Target Count |
|--------|-------------|----------|-------------|
| `needs_light_upscale` | 0.30–0.55 | ~49% | ~14,700 |
| `optimal` | 0.55–0.75 | ~37% | ~11,100 |
| `good` | 0.75–1.0 | ~11% | ~3,300 |
| `needs_major_upscale` | 0.0–0.30 | ~3% | ~900 |

Target distribution is derived from DIQA-5000 empirical distribution (validated by KW H=141.6,
p=1.7e−30, Cohen's d=0.91). Multi-DPI rendering pipeline will be tuned to reproduce this distribution
across all 8 DPI tiers (72/100/150/200/250/300/400/600).

### DPI Tier Coverage (Target)

| DPI Tier | Expected Bucket | Representation Required |
|----------|----------------|------------------------|
| 72 DPI | needs_major_upscale / needs_light_upscale | Must include born-digital (large fonts → high char_height paradox) |
| 100 DPI | needs_light_upscale | Born-digital and scanned both required |
| 150 DPI | needs_light_upscale | Transition zone; script-aware measurement critical |
| 200 DPI | needs_light_upscale / optimal | Natural scan distribution |
| 250 DPI | optimal | OCR boundary zone |
| 300 DPI | optimal | Standard scan target |
| 400 DPI | good | High-quality scan |
| 600 DPI | good | Archive-quality scan |

### Split Strategy

| Split | Images | Percentage |
|-------|-------:|------------|
| Train | 21,000 | 70% |
| Val | 4,500 | 15% |
| Test | 4,500 | 15% |
| **Total** | **30,000** | **100%** |

**Split Method**: Document-level split (not image-level). All DPI renders of the same source document
assigned to the same split.
**Random Seed**: 42
**Leakage Prevention**: Global split registry (SHA256-keyed on source document ID, not image hash).
DIQA-5000 is 100% in training. OHR-Bench test split withheld from training labels — only the
OHR-Bench test split is eligible for OOD-Resolution 6b. DocLayNet OOD images (sub-source 6a) must use
pages not appearing in any training split.

**MNV4-H3 / SIG-G5-5 Split Parity**: Train/val/test splits must be byte-identical between MNV4-H3
and SIG-G5-5 (enforced via shared global split registry). Registry keys on source document ID, not
corrected-image SHA256, because correction parameters may change between training runs.

---

## Section 6 — 14-Dimension Diversity

> **Full DDR Audit**: [resolution_quality_ddr.md](../diversity_reports/resolution_quality_ddr.md)
> **HAR Section 4 Reference**: [mnv4-h3-resolution-quality.md § Section 4](../../planning/har/mnv4-h3-resolution-quality.md)
> **Overall Diversity Score**: 20.0/100 (DDR automated; manifest not yet linked — see note below)

**DDR Note**: The automated DDR scores 0.0/100 for wild condition coverage and 14-dimension diversity
because the training manifest has not yet been assembled (L2 metadata not linked to the 5,499 DIQA-5000
images in the diversity evaluation pipeline). Label quality scores 50.0/100. The dimension scores
below reflect human analysis of DIQA-5000 characteristics and planned source composition.

| Dimension | L2 Field | Relevance | Target | Current (DIQA-5000) | Status |
|-----------|----------|-----------|--------|---------------------|--------|
| resolution_dpi | `resolution.category` | CRITICAL — core signal; DPI tier coverage must span full range | All 8 DPI tiers (72/100/150/200/250/300/400/600) | Natural scan distribution; 72–150 DPI tier likely underrepresented | ❌ Critical gap |
| capture_method | `capture_method.method` | HIGH — scanner/camera/born-digital yield different char_height/DPI relationships | ≥ 3 methods; ≥ 20% born_digital | Predominantly scanned; born_digital fraction unknown but likely very low | ❌ Critical gap |
| script_code | `language.script_code` | HIGH — CJK chars ~1.5× Latin height; radical fragmentation degrades V1 measurement | ≥ 3 script families (LATN, HANS/HANT, ARAB); ≥ 15% CJK | Predominantly Latin; CJK fraction unknown | ❌ Gap |
| color_mode | `image_properties.color_mode` | HIGH — binarized docs lose fine char structure; Sauvola vs. Gaussian adaptive behaves differently | ≥ 2 modes (color/grayscale + binarized) | Predominantly grayscale/color; binarized fraction unknown | ⚠️ Partial |
| degradation | `quality.degradations` | MEDIUM — blur/noise reduce effective char_height measurement accuracy | ≥ 3 degradation types; blur at multiple severity levels | DIQA-5000 includes blur, noise, contrast degradation | ⚠️ Partial |
| domain | `domain.level1` | MEDIUM — document density affects char_height measurement reliability | ≥ 5 domains | Varied document types; domain balance unknown | ⚠️ Partial |
| layout_type | `structure.layout_type` | MEDIUM — dense formula/table layouts confound char_height detection | ≥ 3 types | DIQA-5000 includes mixed layouts | ⚠️ Partial |
| document_age | `image_properties.document_age` | MEDIUM — aged docs have ink spread affecting apparent char boundaries | ≥ 2 age classes (modern + aged) | Mostly modern documents | ❌ Gap |

### Key Diversity Gaps

- Born-digital low-DPI examples almost certainly absent from DIQA-5000 (all scanned). Without these,
  the model may learn scanner texture as a proxy for "high quality" — the single most critical training
  distribution gap.
- Low-DPI tier (72–150 DPI) underrepresented; scanned documents are typically ≥ 200 DPI.
- CJK and non-Latin script coverage in DIQA-5000 presumed low; char_height measurement is script-
  dependent (CJK ~1.5× Latin height); V1 CC fragmentation degrades CJK label quality further.
- Multi-DPI rendering pipeline (DocLayNet at 8 DPI tiers) is the primary remediation path for
  resolution_dpi, capture_method, and domain dimension gaps simultaneously.

---

## Section 7 — Wild Condition Coverage

> **HAR Section 5 Reference**: [mnv4-h3-resolution-quality.md § Section 5](../../planning/har/mnv4-h3-resolution-quality.md)
> **Overall Wild Condition Score**: 0.0/100 (DDR automated; no conditions covered in current manifest)

| Wild Condition | L2 Evidence | Status | Gap |
|----------------|-------------|--------|-----|
| Born-digital PDF at low DPI (large fonts → high char_height despite low pixel density) | `capture_method.method` = born_digital + `resolution.dpi` < 150 | ❌ Missing | DIQA-5000 is scan-dominated; born-digital low-DPI examples absent. Char-height scoring handles this CORRECTLY (high char_height at 72 DPI IS OCR-optimal), but model must see examples to avoid learning scanner texture as quality proxy. Gap RQ-MNV4-G05. OOD-Resolution 6a tests this. |
| Bicubic-upscaled raster (2×/4× interpolation; no new information despite higher DPI) | `resolution.upscale_factor` | ❌ Missing | Model must learn that bicubic-upscaled images have crisp edges but reduced effective OCR quality. Labels derived from pre-upscale originals. Gap RQ-MNV4-G06. OOD-Resolution 6b tests this. |
| High-DPI scan with optical blur (300+ DPI but illegible due to camera motion or defocus) | `quality.degradations` includes blur | ⚠️ Partial | DIQA-5000 includes blur examples at natural severity; high-DPI-with-severe-blur combination may be underrepresented. Pixel count alone does not predict readability. Gap RQ-MNV4-G07/G08. |
| CJK documents (naturally large characters ~1.5× Latin height) | `language.script_code` in {HANS, HANT, JPAN, KORE} | ❌ Missing | V1 CC pipeline degraded by radical fragmentation; score may overestimate quality. V2 Phase A morphological closing addresses measurement; training data gap remains. |
| Image-only pages (no text; PaddleOCR detects nothing) | `structure.has_text` = false | ⚠️ Partial | Label falls back to DPI-based heuristic; label quality is lower for text-absent pages. Gap RQ-MNV4-G10. |
| CLAHE over-enhancement on already-sharp images (SIG-G5-5 only) | Post-correction image properties | ❌ Missing | SIG-G5-5 specific: CLAHE applied to high-contrast images may create artificial sharpness signal. OOD sub-source 6c needed. Gap RQ-SIG-G04. |
| Post-deskew blank margins affecting edge char_height measurement (SIG-G5-5 only) | Image geometry post-deskew | ❌ Missing | SIG-G5-5 specific: severely skewed documents introduce blank triangular margins after deskew; PaddleOCR may detect zero characters in these regions. Gap RQ-SIG-G04. |

---

## Section 8 — OOD Cross-Reference

> **Full OOD Catalog**: [OOD_DATASET_CATALOG.md](../OOD_DATASET_CATALOG.md)
> **HAR Section 6 Reference**: [mnv4-h3-resolution-quality.md § Section 6](../../planning/har/mnv4-h3-resolution-quality.md)

| Field | Value |
|-------|-------|
| **Primary OOD Category** | OOD-Resolution |
| **OOD Target Images (shared)** | 500 images (sub-sources 6a + 6b); +300 SIG-G5-5-specific (6c + 6d + 6e) |
| **OOD Acquisition Status** | ⏳ Not started (Phase 6, P0) |

### Shared OOD Sub-Sources (MNV4-H3 and SIG-G5-5)

| OOD Sub-source | Images | Relevance | Stress Scenario |
|----------------|-------:|-----------|-----------------|
| 6a. Vector PDF at 3 DPIs | 300 | ✅ Direct | DocLayNet born-digital PDFs rendered at 72/150/300 DPI (100 pages × 3 DPIs). Tests born-digital low-DPI paradox: large fonts at 72 DPI → high char_height despite low effective resolution. SIG-G5-5: images passed through correction pipeline before OOD evaluation. SHA256+pHash dedup against training manifests required (Hamming ≤ 5). Must use pages NOT overlapping with DocLayNet training images. |
| 6b. Upscaled rasters | 200 | ✅ Direct | OHR-Bench test split or RealDAE subset (NOT DIQA-5000 — in training). 2× and 4× bicubic upscaling (100 images × 2 factors). Labels derived from pre-upscale originals. SIG-G5-5 divergence from MNV4-H3 on this sub-source flags upscale-artifact sensitivity. |

### SIG-G5-5-Specific OOD Sub-Sources (Gap RQ-SIG-G07)

| OOD Sub-source | Images | Stress Scenario |
|----------------|-------:|-----------------|
| 6c. CLAHE over-enhanced images | 100 | Training-excluded documents with CLAHE applied at 3 clip_limit levels (1.0/2.0/4.0). Tests whether SIG-G5-5 inflates quality score due to CLAHE-enhanced apparent contrast. |
| 6d. Severely deskewed with blank margins | 100 | Training-excluded documents with ≥ 15° skew, after deskew correction. Tests whether deskew blank margins cause underestimation of char-height near image edges. |
| 6e. MNV4-H3 / SIG-G5-5 divergence cases | 100 | Top-50 divergence cases by \|MNV4-H3 − SIG-G5-5\| sampled from DIQA-5000 val set after both models are trained, human-verified ground truth. Directly tests divergence signal; calibrates whether divergence predicts labeling error or genuine model disagreement. |

### Ensemble Conflict Resolution Policy (SIG-G5-5 at Inference)

| Scenario | Action |
|----------|--------|
| \|SIG-G5-5_mu − MNV4-H3\| ≤ 0.1 | Agreement — use SIG-G5-5_mu as final |
| \|SIG-G5-5_mu − MNV4-H3\| > 0.1 AND SIG-G5-5 sigma_sq < 0.05 | SIG-G5-5 confident — override MNV4-H3 |
| \|SIG-G5-5_mu − MNV4-H3\| > 0.1 AND SIG-G5-5 sigma_sq ≥ 0.05 | Uncertainty — use conservative (lower) of the two scores; flag for quality escalation |
| \|SIG-G5-5_mu − MNV4-H3\| > 0.25 (any sigma_sq) | Major divergence — flag for human review; apply safe default (needs_light_upscale treatment) |
| SIG-G5-5 unavailable (CPU-only fallback) | Fall back to MNV4-H3 prediction only |

Divergence threshold of 0.1 is a placeholder pending empirical calibration via OOD sub-source 6e.

**OOD Leakage Risk**: DIQA-5000 is 100% in training — must not appear in any OOD sub-source.
OHR-Bench test split withheld from training. DocLayNet OOD renders (6a) must use pages not in any
training split. Global split registry (SHA256-keyed) required. SIG-G5-5 additional requirement:
correction pipeline version must be documented for every OOD image to enable re-evaluation if
correction settings change.

---

## Section 9 — Assembly Pipeline

**Status**: 🔄 Partially blocked (labeling scripts exist and validated; `prepare_multitask_datasets.py resolution` subcommand not yet implemented)

### Phase 1 — Label Existing Source Datasets

Run the validated labeling pipeline on OHR-Bench and RealDAE on Vultr A100 VM:

```bash
# Prerequisite: PaddleOCR v2 only (pin paddleocr>=2.7,<3.0); run on GPU VM
# Throughput: ~12.1 img/s on A100; OHR-Bench ~11 min, RealDAE ~2 min

# Label OHR-Bench (8,500 images) — Gap RQ-MNV4-G01
uv run python scripts/label_resolution_quality.py \
    --input-dir /mnt/e/image_detection/01_base_data/iqa/ohr-bench/images \
    --output /mnt/e/image_detection/results/ohrbench_resolution_labels.json

uv run python scripts/integrate_resolution_quality.py \
    --labels /mnt/e/image_detection/results/ohrbench_resolution_labels.json \
    --metadata /mnt/e/image_detection/metadata_registry/json/ohr_bench_metadata.json

# Label RealDAE (1,200 images) — Gap RQ-MNV4-G02
uv run python scripts/label_resolution_quality.py \
    --input-dir /mnt/e/image_detection/01_base_data/iqa/realdae/images \
    --output /mnt/e/image_detection/results/realdae_resolution_labels.json

uv run python scripts/integrate_resolution_quality.py \
    --labels /mnt/e/image_detection/results/realdae_resolution_labels.json \
    --metadata /mnt/e/image_detection/metadata_registry/json/realdae_metadata.json
```

### Phase 2 — Assembly (subcommand not yet implemented)

```bash
# Dry run (validates without writing)
uv run python scripts/prepare_multitask_datasets.py resolution --dry-run

# Full assembly (after Gap RQ-MNV4-G03 is resolved)
uv run python scripts/prepare_multitask_datasets.py resolution

# SIG-G5-5 corrected-image assembly (after Gap RQ-SIG-G04 is resolved)
uv run python scripts/prepare_multitask_datasets.py resolution --corrected-images
```

### Dependencies

| Dependency | Status | Required For |
|------------|--------|-------------|
| `scripts/label_resolution_quality.py` | ✅ Ready (validated on DIQA-5000) | All source dataset labeling |
| `scripts/integrate_resolution_quality.py` | ✅ Ready (validated on DIQA-5000) | Merging labels into L2 metadata |
| `diqa_5000_metadata.json` | ✅ Complete (V1 labels, 5,499 images) | Current training pool |
| `ohr_bench_metadata.json` | ⚠️ Needs labeling (Gap RQ-MNV4-G01) | +8,500 images |
| `realdae_metadata.json` | ⚠️ Needs labeling (Gap RQ-MNV4-G02) | +1,200 images |
| Multi-DPI rendering pipeline | ❌ Not created (Gap RQ-MNV4-G03) | +~15,000 images (DocLayNet renders) |
| `prepare_multitask_datasets.py resolution` subcommand | ❌ Not created (Gap RQ-MNV4-G03) | Final manifest assembly |
| Corrected-image assembly path | ❌ Not created (Gap RQ-SIG-G04) | SIG-G5-5 training images |
| V2 Sauvola labeling (Phase A) | ❌ Not created (Gap RQ-MNV4-G04) | Production-quality labels |
| PaddleOCR v2 (`paddleocr>=2.7,<3.0`) | ✅ Available | Labeling pipeline |
| GPU VM (Vultr A100 or equivalent) | ✅ Available (207.246.124.234) | Labeling throughput |

### Generated Outputs

| File | Description |
|------|-------------|
| `train_manifest.json` | Flat JSON list of training records (MNV4-H3: raw images) |
| `val_manifest.json` | Flat JSON list of validation records |
| `test_manifest.json` | Flat JSON list of test records |
| `train_manifest_corrected.json` | Flat JSON list (SIG-G5-5: corrected images) |
| `resolution_quality/images/` | Raw training images |
| `resolution_quality/corrected_images/` | Correction-pipeline-processed images (SIG-G5-5) |

---

## Section 10 — Gap Registry

> **Source**: [mnv4-h3-resolution-quality.md § Section 8](../../planning/har/mnv4-h3-resolution-quality.md),
> [sig-g5-resolution-quality-reg.md § Section 8](../../planning/har/sig-g5-resolution-quality-reg.md)
> **MNV4-H3 HAR Score**: 26/100 — ⚠️ Needs Work
> **SIG-G5-5 HAR Score**: 39/100 — ⚠️ Needs Work

### P0 Blockers (must resolve before assembly can run)

#### MNV4-H3 Blockers

| Gap ID | Description | Root Cause | Remediation | Effort |
|--------|-------------|------------|-------------|--------|
| RQ-MNV4-G01 | `resolution.resolution_quality_score` not populated in OHR-Bench L2 metadata | Labeling pipeline not yet run on OHR-Bench (8,500 images) | Run `scripts/label_resolution_quality.py` + `scripts/integrate_resolution_quality.py` on OHR-Bench on Vultr A100 VM (~11 min at 12.1 img/s). Adds ~8,500 images to pool. | 0.5 days |
| RQ-MNV4-G02 | `resolution.resolution_quality_score` not populated in RealDAE L2 metadata | Labeling pipeline not yet run on RealDAE (1,200 images) | Run labeling pipeline on RealDAE. Adds ~1,200 images to pool. | 0.25 days |
| RQ-MNV4-G03 | Multi-DPI rendering pipeline not implemented; 72/100/150 DPI tier critically underrepresented | `prepare_multitask_datasets.py resolution` subcommand not yet created | Implement resolution subcommand: render DocLayNet source PDFs at 8 DPI tiers (72/100/150/200/250/300/400/600), run labeling pipeline on renders, build manifest. Adds ~15,000 images. | 2–3 days |

#### SIG-G5-5 Blockers (3 inherited + 1 specific)

| Gap ID | Description | Root Cause | Remediation | Effort |
|--------|-------------|------------|-------------|--------|
| RQ-SIG-G01 | `resolution.resolution_quality_score` not populated in OHR-Bench L2 metadata | Inherits RQ-MNV4-G01 | Same as RQ-MNV4-G01 (shared effort) | 0 additional days |
| RQ-SIG-G02 | `resolution.resolution_quality_score` not populated in RealDAE L2 metadata | Inherits RQ-MNV4-G02 | Same as RQ-MNV4-G02 (shared effort) | 0 additional days |
| RQ-SIG-G03 | Multi-DPI rendering pipeline not implemented | Inherits RQ-MNV4-G03 (adds corrected-image step) | Implement resolution subcommand with corrected-image assembly; render DocLayNet at 8 DPI tiers, apply correction pipeline, run labeling, build manifest | 0.5 additional days beyond RQ-MNV4-G03 |
| RQ-SIG-G04 | Corrected-image assembly path not implemented | SIG-G5-5 trains on corrected images; no pipeline applies correction and re-measures labels | Implement corrected-image assembly: (1) apply correction pipeline to each training image, (2) re-run RQ labeling on corrected versions where skew > 5° or aggressive CLAHE applies | 1 day |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Remediation | Effort |
|--------|-------------|-------------|--------|
| RQ-MNV4-G04 | V2 labeling precision not implemented: V1 IQR = 9.0px vs. target 4–5px (54% cross-bucket rate) | Implement V2 Phase A (Sauvola binarization k=0.2 + morphological closing 3×1/1×3 + KDE mode) in `src/image_preprocessing_detector/schema_utils/resolution_quality.py`. Then Phase B (projection profiles + ensemble + DBSCAN). | Phase A: 1–2 days; Phase B: 3–4 days |
| RQ-MNV4-G05 | Born-digital low-DPI examples absent from training distribution (DIQA-5000 is scan-dominated) | Include born-digital low-DPI renders explicitly via DocLayNet rendering at 72/100 DPI (part of RQ-MNV4-G03). Ensure ≥ 10% of pool is born-digital; ≥ 5% is born-digital at < 150 DPI. | Part of RQ-MNV4-G03 |
| RQ-MNV4-G06 | Upscaling artifact examples absent from training distribution | Add 2×/4× bicubic upscaling augmentation to `prepare_multitask_datasets.py resolution` pipeline. Labels derived from pre-upscale originals. | 0.5 days (part of RQ-MNV4-G03) |
| RQ-SIG-G05 | Ensemble conflict resolution policy not calibrated; divergence thresholds (0.1/0.25) are placeholders | After both heads are trained, run inference comparison on full DIQA-5000 val set; calibrate thresholds; implement divergence logging at inference | 0.5 days (policy) + 0.5 days (instrumentation) |
| RQ-SIG-G06 | V2 labeling strategy shared with MNV4-H3 (inherits RQ-MNV4-G04) | Same as RQ-MNV4-G04 | Shared effort |
| RQ-SIG-G07 | OOD sub-sources 6c/6d/6e for correction pipeline artifacts not yet acquired | Define and acquire CLAHE over-enhanced images (6c), post-deskew blank margin images (6d), MNV4-H3/SIG-G5-5 divergence cases (6e) after both models are trained | 1 day design + 1 day acquisition |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
|--------|-------------|-------------|
| RQ-MNV4-G07 | Image-only pages rely on DPI heuristic fallback — formula not formally documented | Define and document DPI-only fallback label formula for text-absent pages in labeling script docstring and L2 schema notes |
| RQ-MNV4-G08 | High-DPI-but-blurry optical degradation not covered in OOD (pixel count high but content unreadable) | Add OOD-Resolution 6c sub-source: 100 high-DPI scans with controlled optical blur. Source from OHR-Bench degraded subset or artificially blurred RealDAE images. |
| RQ-MNV4-G09 | JPEG compression artifacts not covered in OOD (aggressive DCT blocking reduces apparent char resolution) | Add OOD-Resolution 6d sub-source (future): 50 images with JPEG quality 10–30 applied to varied-DPI source documents |
| RQ-MNV4-G10 | CJK char_height calibration not validated (CJK chars naturally ~1.5× Latin height) | Add CJK-stratified validation during resolution labeling; audit DIQA-5000 CJK subset; ensure ≥ 10% CJK scripts in final 30K pool |
| RQ-SIG-G08 | MNV4-H3 weak label integration not yet designed | After MNV4-H3 Phase 4 training, generate predictions on the 30K dataset; integrate as tier_2_model soft labels for SIG-G5-5 Phase 5 training using uncertainty-weighted MSE loss: `label_confidence * (1 / max(quality_score_std, 0.01))` |
| RQ-SIG-G09 | NaFlex token budget not configured for resolution quality task | Configure NaFlex minimum resolution to preserve ≥ 32px per char-height; high-resolution documents must not be internally downscaled beyond the discrimination threshold |
| RQ-SIG-G10 | DIQA-5000 script composition not characterized | Audit DIQA-5000 script distribution; if predominantly Latin, CJK quality estimation will be undertrained |

---

## Section 11 — Performance Targets

> **Source**: [SIGLIP2_MULTITASK_REQUIREMENTS.md](../../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md)

| Head ID | Head Name | Task | Target Metric | Target Value | Test Set |
|---------|-----------|------|--------------|-------------|----------|
| MNV4-H3 | `resolution_quality` | Regression 0–1 | MAE | < 0.10 | Multi-DPI test set (OOD-Resolution) |
| MNV4-H3 | `resolution_quality` | Regression 0–1 | SRCC | ≥ 0.70 | Human MOS or OCR degradation metric |
| MNV4-H3 | `resolution_quality` | Latency | GPU latency | < 5ms | A10 benchmark |
| MNV4-H3 | `resolution_quality` | Latency | CPU latency | < 15ms | 4-core CPU benchmark |
| SIG-G5-5 | `resolution_quality_reg` | Regression 0–1 (Gaussian NLL) | SRCC | ≥ 0.70 | OOD-Resolution; validated against MNV4-H3 predictions |
| SIG-G5-5 | `resolution_quality_reg` | Inter-model | Divergence \|mu − MNV4-H3\| ≤ 0.1 on 80% of OOD images | | OOD-Resolution sub-sources 6a + 6b |

**Cascade Impact**: MNV4-H3 is the earliest quality gate in the pipeline. An incorrect prediction
propagates downstream:

- If MNV4-H3 mislabels a low-quality document as acceptable → SigLIP 2 receives blurry/low-res input → all 19 SigLIP 2 heads degrade in accuracy.
- If MNV4-H3 mislabels a high-quality document as needing upscaling → unnecessary upscaling pass adds latency and introduces interpolation artifacts.

This cascade dependency makes MNV4-H3 a P0 blocker for overall pipeline quality.

**Pipeline Trigger Thresholds**:

- Upscale trigger: `resolution_quality_score` < 0.4 (char_height < ~24px)
- Downscale trigger: `resolution_quality_score` > 0.8 AND image > 4000px
- SIG-G5-5 override of MNV4-H3: when sigma_sq < 0.05 AND \|divergence\| > 0.1

### Achieved Results

| Head | Val MAE | Test MAE | SRCC | Status |
|------|---------|---------|------|--------|
| MNV4-H3 `resolution_quality` | — | — | — | ❌ Not trained (bootstrap training pending) |
| SIG-G5-5 `resolution_quality_reg` | — | — | — | ❌ Not trained (Phase 5, after MNV4-H3) |

---

## Related Documents

- **HAR Files**: [mnv4-h3-resolution-quality.md](../../planning/har/mnv4-h3-resolution-quality.md),
  [sig-g5-resolution-quality-reg.md](../../planning/har/sig-g5-resolution-quality-reg.md)
- **DDR**: [resolution_quality_ddr.md](../diversity_reports/resolution_quality_ddr.md)
- **Head Spec**: [SIGLIP2_MULTITASK_REQUIREMENTS.md](../../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md)
- **V2 Labeling Strategy**: [RESOLUTION_QUALITY_V2_STRATEGY.md](../../planning/RESOLUTION_QUALITY_V2_STRATEGY.md)
- **Diversity Spec**: [DATASET_DIVERSITY_REQUIREMENTS.md](../../planning/DATASET_DIVERSITY_REQUIREMENTS.md)
- **Source Datasets**: [DATASET_QUICK_REFERENCE.md](../DATASET_QUICK_REFERENCE.md)
- **OOD Catalog**: [OOD_DATASET_CATALOG.md](../OOD_DATASET_CATALOG.md)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-23 | Initial creation from MNV4-H3 and SIG-G5-5 HAR files + DDR |
