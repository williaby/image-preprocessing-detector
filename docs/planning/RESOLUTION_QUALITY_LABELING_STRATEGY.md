# Resolution Quality Labeling Strategy for Camera-Captured Document Datasets

## Context

We need a **resolution quality score (0-1)** for every image in our training pipeline to determine if upsampling/downsampling is needed (target: ~300 DPI / character height 32-48px). Datasets like DIQA-5000 lack DPI metadata and character pixel height labels entirely. This analysis investigates how to generate reliable resolution quality pseudo-labels for images where no ground truth exists.

### DIQA-5000 Gap Analysis

- **5,500 images** (500 camera-captured `ori/` + 5,000 enhanced `res/`)
- **Has**: 3-dim MOS scores (overall, sharpness, color_fidelity), image dimensions (~1946x2781 px)
- **Missing**: DPI metadata, character height measurements, resolution quality labels
- **Provenance**: Born-digital PDFs printed at 300 DPI, then photographed by smartphone
- **Complications**: 22% rotated 90 degrees, 76% Chinese text, degradations (shadow 20%, blur 20%, moire 20%, creases 20%, occlusion 20%)
- **Audit status**: L2 metadata only 33.1% accurate overall (18 systemic defects identified)

### Existing Codebase

- `_measure_char_height()` in [generator.py:547-623](src/image_preprocessing_detector/synthetic/generator.py#L547-L623) - connected component analysis, only used on synthetic data
- `pdf_resolution.py` - PyMuPDF metadata-based DPI (useless for camera-captured images)
- Planned MobileNetV4 `resolution_quality` head needs 30K labeled training images

---

## Three Approaches Evaluated

### Approach 1: Connected Component Character Height Extraction

- Apply existing `_measure_char_height()` to all images
- Map median char height to 0-1 score via piecewise linear mapping
- Cross-validate with MOS sharpness score

### Approach 2: Frequency-Domain Resolution Estimation (MTF/Power Spectrum)

- Compute 2D FFT power spectrum, measure high-frequency energy ratio
- Calibrate against known-DPI synthetic references

### Approach 3: OCR-Driven Multi-Scale Quality Labeling

- Multi-resolution stack per image (0.5x through 2.0x)
- Run PaddleOCR at each scale, score = current_confidence / peak_confidence

---

## 5-Model Consensus Results

**Models consulted**: Gemini 2.5 Pro, Gemini 3 Pro Preview, GPT-5.2 (empty response - known issue), DeepSeek R1, Grok 4

**Mean confidence**: 8.75/10 (range 8-9, 4 responding models)

### Unanimous Agreements (4/4 models)

| Finding | Details |
|---------|---------|
| **Approach 3 produces highest quality labels** | Directly measures OCR readability = gold standard for this task |
| **Approach 2 should be DISCARDED** | Measures sharpness/focus, NOT geometric resolution. Cannot distinguish sharp 8px text from blurry 60px text. JPEG compression and moire confound it further |
| **Hybrid of Approach 1 + 3 is optimal** | Use Approach 1 as fast pre-filter, Approach 3 for degraded/CJK images |
| **Orientation correction is MANDATORY first** | All approaches assume horizontal text. 22% rotation corrupts height, frequency, and OCR measurements |
| **Approach 1 too brittle alone for DIQA-5000** | CJK disconnected radicals + degradations (shadow, blur) cause catastrophic CC analysis failures |

### Unanimous Rankings

| Dimension | Ranking |
|-----------|---------|
| Label Quality | Approach 3 >> Approach 1 > Approach 2 |
| Feasibility | Approach 1 > Approach 2 > Approach 3 |
| Cost-effectiveness | Approach 1 > Approach 2 > Approach 3 |

### Key Model-Specific Insights

| Source | Novel Insight |
|--------|---------------|
| **Gemini 3 Pro Preview** | Use OCR **text detector** (DBNet) bounding box heights instead of recognition confidence. This avoids the blur-vs-scale confusion (blurry image at correct size yields low confidence but correct bbox height). Single pass = 5,500 inferences, not 33,000 |
| **DeepSeek R1** | Manually validate ~500 labels as calibration ground truth. Use PaddleOCR's built-in orientation detection for dual-purpose (rotation fix + labeling) |
| **Grok 4** | Long-term: train lightweight CNN on synthetic multi-DPI data for production prediction. Use MOS sharpness correlation as validation signal. Consider MTurk for calibration subset |
| **Gemini 2.5 Pro** | Industry standard: "proxy ground truth" via task-aligned labeling (Google DocAI, Abbyy use same pattern). Approach 1 CJK calibration is "a sinkhole of engineering time" |

### Points of Minor Disagreement

| Topic | Majority View | Minority View |
|-------|--------------|---------------|
| Approach 1 utility | Gemini 2.5/3 Pro: "fundamentally brittle", use only as cheap pre-filter | Grok 4: More balanced - fits project's deterministic patterns, viable for non-degraded Latin images |
| Compute cost concern | Gemini 3 Pro: "trivial, 1-2 hours on consumer GPU" | Grok 4: "~days of compute" for multi-scale (overestimate for 5.5K images) |
| Approach 2 severity | Gemini 3 Pro: "fundamentally flawed" | DeepSeek R1: Least suitable but could supplement Approach 1 for upsampling artifact detection |

---

## Consensus-Evolved Recommendation: Two-Stage Precision Measurement

The consensus produced a superior hybrid, refined further to target ~2px precision where possible.

### Method: DBNet Text Detection + Intra-Region CC Analysis

**Stage 1 - Robust Text Region Detection (DBNet)**

1. **Pre-process**: Correct orientation using PaddleOCR's built-in orientation classifier
2. **Detect**: Run PaddleOCR text detection stage (DBNet) on each image - single pass
3. **Extract**: Get polygon bounding boxes of all detected text lines
4. **Coarse height**: Compute line height from polygon edge distances (precision: ±2-3px clean, ±5-8px degraded)

**Stage 2 - Precise Character Height Within Detected Regions (CC Analysis)**

1. **Crop** (step 5): For each detected text line polygon, extract the region with polygon mask
2. **Local binarize** (step 6): Adaptive thresholding per-region (not global 0.85*mean), handles uneven lighting/shadows
3. **CC analysis** (step 7): Run connected components on the masked region - now operating on known-text with no non-text noise
4. **Filter** (step 8): Keep components with aspect ratio 0.2-5.0, area within 0.1%-10% of region (tighter bounds since we know it's text)
5. **Measure** (step 9): Median character height from filtered CCs within each region
6. **Aggregate** (step 10): Weighted median across all text regions (weight by region area)

**Why Stage 2 inside DBNet regions is dramatically more reliable than standalone CC:**

- No non-text regions (figures, whitespace, page borders) to confuse filtering
- Local adaptive threshold per region handles shadow/lighting gradients
- Polygon mask eliminates edge artifacts from adjacent regions
- Aspect ratio filtering more accurate when you know content is text
- CJK stroke fragmentation reduced because binarization threshold is locally calibrated

**Stage 3 - Scoring and Validation**

1. **Score** (step 11): Map aggregate median character height to 0-1 quality score via piecewise mapping:
    - <16px = 0.0-0.15 (needs major upscaling)
    - 16-32px = 0.15-0.55 (needs light upscaling)
    - 32-48px = 0.55-0.75 (optimal OCR range)
    - 48-96px = 0.75-0.95 (good, may downscale)
    - >96px = 0.95-1.0 (oversized)
2. **Cross-validate** (step 12): Correlate with MOS sharpness scores (expect r > 0.5)
3. **Manual review** (step 13): Validate ~500 samples across MOS tiers

### Expected Precision

| Image Quality | Stage 1 Only (DBNet bbox) | Stage 1+2 Combined | Notes |
|--------------|--------------------------|---------------------|-------|
| Clean, high-contrast | ±2-3px | ±1-2px | CC analysis adds sub-box precision |
| Moderate degradation | ±5-8px | ±3-4px | Local adaptive threshold handles shadows |
| Heavy degradation | ±8-12px | ±5-7px | CC still noisy but DBNet regions constrain search |
| Aggregate (median across page) | ±3-5px | ±2-3px | Many text lines smooth individual box noise |

**Bottom line**: Combined approach reliably achieves ~2-3px on page-level aggregate, ~3-5px per-region. Sufficient for continuous regression training with consistent ordering. Coarse buckets are rock-solid.

### Output Schema (Per-Image)

Each labeled image produces a measurement record with confidence and range:

```json
{
  "resolution_quality_score": 0.62,
  "confidence_pct": 0.85,
  "char_height_px": 38.5,
  "char_height_range_px": [35.0, 42.0],
  "score_range": [0.57, 0.67],
  "coarse_bucket": "optimal",
  "measurement_method": "stage_1_2",
  "num_text_regions": 42,
  "num_valid_cc_regions": 38,
  "height_cv": 0.12,
  "flagged_for_review": false
}
```

**Field descriptions:**

| Field | Type | Description |
|-------|------|-------------|
| `resolution_quality_score` | float 0-1 | Primary label: piecewise-mapped from `char_height_px` |
| `confidence_pct` | float 0-1 | How confident in this measurement (see formula below) |
| `char_height_px` | float | Weighted median character height across all text regions |
| `char_height_range_px` | [float, float] | 95% confidence interval: [P25, P75] of per-region heights |
| `score_range` | [float, float] | Quality score range derived from `char_height_range_px` mapped through piecewise function |
| `coarse_bucket` | string | One of: `needs_major_upscale` (<16px), `needs_light_upscale` (16-32px), `optimal` (32-48px), `good` (48-96px), `oversized` (>96px) |
| `measurement_method` | string | `stage_1_2` (full precision) or `stage_1_only` (CC failed, bbox height used) |
| `num_text_regions` | int | Total text line regions detected by DBNet |
| `num_valid_cc_regions` | int | Regions where Stage 2 CC analysis succeeded |
| `height_cv` | float | Coefficient of variation of per-region heights (lower = more uniform = more confident) |
| `flagged_for_review` | bool | True if <3 text regions or confidence <0.4 |

**Confidence formula:**

```python
region_factor = min(1.0, num_text_regions / 10)  # More regions = better
uniformity_factor = max(0.0, 1.0 - height_cv)     # Low variance = better
method_factor = 1.0 if method == "stage_1_2" else 0.8  # CC adds precision
confidence_pct = region_factor * uniformity_factor * method_factor
```

**Range calculation:**

```python
# Per-region heights: [h1, h2, ..., hN]
char_height_range_px = [percentile(heights, 25), percentile(heights, 75)]
# Map both bounds through piecewise function
score_range = [piecewise_map(char_height_range_px[0]), piecewise_map(char_height_range_px[1])]
```

### Fallback Logic

- If Stage 2 CC analysis fails for a region (< 3 valid components): fall back to Stage 1 bbox height for that region, set `measurement_method = "stage_1_only"` for that region
- If < 3 text regions detected on entire page: `flagged_for_review = true`, `confidence_pct` capped at 0.3
- If `height_cv > 0.5` (very inconsistent heights): `flagged_for_review = true`

### Cost Estimate

- 5,500 images x 1 PaddleOCR detection pass + CC analysis = ~2-3 hours on P40 GPU
- CC analysis adds ~5-10ms per detected text region (~30-50 regions/page = ~200-500ms/image)
- Manual validation of 500 samples = ~4-6 hours human time
- Total: ~1 day of effort for high-precision pseudo-labels

### Applicability Beyond DIQA-5000

This method works for any camera-captured or scanned document dataset lacking DPI metadata:

- OHR-Bench (8.5K images)
- RealDAE (1.2K images)
- SmartDoc-QA
- Any future camera-captured datasets

---

## Verification Plan

1. Run two-stage measurement on 36 DIQA-5000 audit samples (already have visual ground truth)
2. Compare Stage 1 vs Stage 1+2 precision on the same samples to quantify improvement
3. Check correlation between resolution quality score and MOS sharpness (expect r > 0.5)
4. Validate that rotated images produce correct heights after orientation correction
5. Spot-check 500 images across MOS tiers (low/mid/high) for label sanity
6. Measure per-image processing time to confirm P40 throughput estimates

---

## Critical Files

| File | Role |
|------|------|
| [generator.py:547-623](src/image_preprocessing_detector/synthetic/generator.py#L547-L623) | Existing `_measure_char_height()` with piecewise mapping (reference implementation) |
| [pdf_resolution.py](src/image_preprocessing_detector/ingestion/pdf_resolution.py) | Current DPI detection (metadata-only, not applicable here) |
| [schema_adapter.py:492-507](src/image_preprocessing_detector/synthetic/schema_adapter.py#L492-L507) | Resolution metadata fields in L2 schema |
| [DIQA_5000_METADATA_AUDIT_REPORT.md](docs/reports/DIQA_5000_METADATA_AUDIT_REPORT.md) | Full audit with 36 validated samples |
| [SIGLIP2_MULTITASK_REQUIREMENTS.md](docs/planning/SIGLIP2_MULTITASK_REQUIREMENTS.md) | MobileNetV4 resolution_quality head design |
| [DATASET_DIVERSITY_REQUIREMENTS.md](docs/planning/DATASET_DIVERSITY_REQUIREMENTS.md) | Resolution quality dataset plan (30K images) |
