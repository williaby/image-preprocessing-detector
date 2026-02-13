# Resolution Quality Labeling V2 Strategy

## Context

The V1 resolution quality pipeline (PaddleOCR DBNet + Connected Component analysis) successfully labels 5,500 DIQA-5000 images with coarse bucket classification (Kruskal-Wallis H=141.6, p=1.7e-30, 3% anomaly rate). However, the continuous regression precision is insufficient for training weak labels:

| Metric | V1 Actual | Target | Gap |
|--------|-----------|--------|-----|
| Median char height IQR | 9.0 px | 2-3 px | 3-4.5x |
| Score range width | 0.159 | <0.05 | 3x |
| Cross-bucket boundary | 54% | <15% | 3.6x |
| Coarse bucket accuracy | 97% | 97% | Met |

**Root causes of V1 imprecision:**

1. **CJK radical fragmentation**: Chinese characters with disconnected strokes (left-right, top-bottom structures) fragment into multiple short CCs, dragging median height down and inflating variance
2. **Gaussian adaptive threshold**: Global block size poorly handles shadows (20% of DIQA-5000), uneven lighting, and low-contrast CJK strokes
3. **Simple median aggregation**: Sensitive to outlier regions (logos, headers, decorative elements)
4. **No font-size awareness**: Aspect ratio filters (0.2-5.0) are too broad; CJK characters are nearly square while Latin is tall-narrow

---

## 5-Model Consensus Summary

**Models consulted**: Gemini 2.5 Pro (9/10), Gemini 3 Pro Preview (9/10), GPT-5.2 (empty - known issue), DeepSeek R1 (8/10), Grok 4 (8/10)

**Mean confidence**: 8.5/10 across 4 responding models

### Unanimous Agreements (4/4)

| Finding | Details |
|---------|---------|
| **Morphological closing for CJK** | Vertical/horizontal closing kernel (1x3 or 3x3) reconnects fragmented radicals before measurement |
| **Synthetic calibration** | Render known-DPI text, measure with pipeline, build correction model for systematic bias |
| **Frequency domain rejected** | Confirmed: measures sharpness/focus, not geometric resolution. JPEG/moire confound it |
| **Current pipeline is sound foundation** | Two-stage DBNet + measurement is architecturally correct; improvements are evolutionary |

### Majority Agreements (3/4)

| Finding | Models | Details |
|---------|--------|---------|
| **Sauvola binarization** | DeepSeek, Grok, Gemini 3 | DIBCO gold standard; handles shadows/degradation far better than Gaussian adaptive. k=0.2 optimal |
| **Gold standard validation subset** | Gemini 3, Grok, Gemini 2.5 | 300-500 images with multi-scale OCR ground truth for pipeline validation |
| **Font-size-aware filtering** | Grok, Gemini 3, DeepSeek | Dynamic aspect ratios: CJK ~0.8-1.2 (square), Latin ~0.3-0.7 (tall-narrow) |

### Key Tension: Projection Profiles vs Improved CC

| Approach | Advocate | Rationale |
|----------|----------|-----------|
| **Replace CC with horizontal projection profiles** | Gemini 3 Pro Preview | Treats entire text line as statistical unit; averages 20-30 chars, dampening noise by sqrt(N). Robust to CJK fragmentation by design |
| **Improve CC internals** | DeepSeek R1, Grok 4 | Sauvola + morphological closing + multi-scale CC fixes root causes. Less architectural risk, builds on proven code |

**Resolution**: Use BOTH as ensemble. Projection profiles excel at line-level height (robust to CJK fragmentation); improved CC excels at character-level precision (sub-line measurement for Latin/mixed). Weight by detected script type:

- CJK-heavy documents: projection profile weight higher (0.7 proj / 0.3 CC)
- Latin-heavy documents: CC weight higher (0.3 proj / 0.7 CC)
- Mixed: equal weights (0.5 / 0.5)

### Model-Specific Novel Insights

| Source | Insight |
|--------|---------|
| **Gemini 3 Pro Preview** | KDE mode estimation instead of median - text lines are consistent, mode is far more robust to outlier heights (logos, noise) |
| **DeepSeek R1** | Multi-scale CC analysis: upscale regions with median height <10px by 2x before CC extraction; DBSCAN clustering on height distributions to separate body text from headers/footnotes |
| **Grok 4** | Active learning loop: flag low-confidence measurements for manual review; iteratively refine calibration model with human-validated corrections |
| **Gemini 2.5 Pro** | Synthetic calibration can verify the piecewise_quality_score mapping function itself, not just the height measurement |

---

## V2 Architecture: Three-Phase Precision Improvement

### Phase A: Quick Wins (Target: +/-6-7px)

**Effort**: ~200 LOC, +15% compute, 1-2 days
**Changes to `resolution_quality.py`**:

#### A1. Sauvola Binarization

Replace Gaussian adaptive threshold with Sauvola (DIBCO gold standard):

```python
# Current (V1): resolution_quality.py line 202
binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY_INV, block_size, C)

# V2: Sauvola binarization
# OpenCV ximgproc.niBlackThreshold with SAUVOLA method
binary = cv2.ximgproc.niBlackThreshold(
    gray, maxValue=255,
    type=cv2.THRESH_BINARY_INV,
    blockSize=block_size,
    k=0.2,  # DIBCO-optimal for degraded documents
    binarizationMethod=cv2.ximgproc.BINARIZATION_SAUVOLA
)
```

**Why**: Sauvola computes threshold locally using both mean AND standard deviation. Handles shadows, uneven lighting, and low-contrast CJK strokes that Gaussian threshold misses.

#### A2. Morphological Closing for CJK

Add morphological closing before CC extraction:

```python
# After binarization, before CC extraction
# Horizontal kernel reconnects left-right radicals
kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 1))
# Vertical kernel reconnects top-bottom radicals
kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 3))
# Apply both
binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_h)
binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_v)
```

**Why**: Chinese characters like `明` (sun + moon) have disconnected radicals that CC analysis fragments. Closing bridges 1-2px gaps without merging separate characters.

#### A3. KDE Mode Estimation

Replace median aggregation with KDE mode:

```python
from scipy.stats import gaussian_kde

def robust_mode(heights: list[float], bandwidth: float = 0.5) -> float:
    """Estimate mode via KDE - more robust than median for multimodal distributions."""
    if len(heights) < 5:
        return float(np.median(heights))
    kde = gaussian_kde(heights, bw_method=bandwidth)
    x_grid = np.linspace(min(heights), max(heights), 200)
    mode_idx = np.argmax(kde(x_grid))
    return float(x_grid[mode_idx])
```

**Why**: Documents have consistent body text height with outlier headers/footnotes. Median is pulled by outliers; KDE mode finds the dominant peak in the height distribution.

**Expected improvement**: IQR from 9.0px to ~6-7px (30-35% reduction)

---

### Phase B: Ensemble Measurement (Target: +/-4-5px)

**Effort**: ~400 LOC, +30% compute, 3-4 days
**New module or extension of `resolution_quality.py`**:

#### B1. Horizontal Projection Profiles

New measurement method for line-level height:

```python
def measure_line_height_projection(region_crop: np.ndarray) -> float:
    """Measure text line height via horizontal projection profile.

    Counts black pixels per row after binarization. The line height is
    the distance between 5% threshold crossings of the projection.
    Averages geometry of 20-30 characters, dampening noise by sqrt(N).
    """
    # 1. Binarize (Sauvola)
    binary = sauvola_binarize(region_crop)

    # 2. Horizontal projection: count black pixels per row
    projection = np.sum(binary > 0, axis=1).astype(float)

    # 3. Find line extent: 5% of max projection as threshold
    threshold = 0.05 * np.max(projection)
    active_rows = np.where(projection > threshold)[0]

    if len(active_rows) < 3:
        return -1.0  # Fallback signal

    # 4. Height = distance from first to last active row
    return float(active_rows[-1] - active_rows[0] + 1)
```

**Why**: Projection profiles treat the entire text line as a single statistical unit. CJK radical fragmentation is irrelevant because disconnected strokes still project onto the same rows. Noise dampening scales as sqrt(N) where N is the number of characters in the line.

#### B2. Ensemble Fusion

Combine CC height and projection height with script-aware weighting:

```python
def ensemble_height(
    cc_height: float,
    proj_height: float,
    script_type: str = "unknown",  # "cjk", "latin", "mixed"
    cc_confidence: float = 1.0,
    proj_confidence: float = 1.0,
) -> float:
    """Fuse CC and projection measurements with script-aware weighting."""
    # Script-aware base weights
    weights = {
        "cjk": (0.3, 0.7),     # Projection better for CJK
        "latin": (0.7, 0.3),   # CC better for Latin
        "mixed": (0.5, 0.5),   # Equal
        "unknown": (0.5, 0.5),
    }
    w_cc, w_proj = weights.get(script_type, (0.5, 0.5))

    # Adjust by measurement confidence
    w_cc *= cc_confidence
    w_proj *= proj_confidence

    # Normalize
    total = w_cc + w_proj
    if total < 1e-6:
        return cc_height  # Fallback

    return (w_cc * cc_height + w_proj * proj_height) / total
```

#### B3. Font-Size-Aware CC Filtering

Dynamic aspect ratio bounds based on detected script:

```python
SCRIPT_ASPECT_RATIOS = {
    "cjk": (0.6, 1.4),    # Nearly square characters
    "latin": (0.2, 0.8),  # Tall-narrow characters
    "arabic": (0.3, 1.5), # Wide variation
    "default": (0.2, 5.0), # Current V1 bounds (fallback)
}
```

#### B4. DBSCAN Height Clustering

Separate body text from headers/footnotes before aggregation:

```python
from sklearn.cluster import DBSCAN

def cluster_heights(heights: list[float], eps: float = 3.0) -> list[float]:
    """Use DBSCAN to find the dominant text height cluster."""
    if len(heights) < 5:
        return heights

    X = np.array(heights).reshape(-1, 1)
    clusters = DBSCAN(eps=eps, min_samples=3).fit(X)

    # Find largest cluster (body text)
    labels, counts = np.unique(clusters.labels_[clusters.labels_ >= 0], return_counts=True)
    if len(labels) == 0:
        return heights

    dominant_label = labels[np.argmax(counts)]
    return [h for h, l in zip(heights, clusters.labels_) if l == dominant_label]
```

**Expected improvement**: IQR from ~6-7px to ~4-5px (additional 30% reduction)

---

### Phase C: Synthetic Calibration (Target: +/-3-4px)

**Effort**: ~300 LOC + 2K synthetic images, 2-3 days

#### C1. Synthetic Calibration Dataset

Render text at known character heights using the existing synthetic generator:

```python
# Generate calibration pairs: (known_height_px, measured_height_px)
CALIBRATION_HEIGHTS = [8, 12, 16, 20, 24, 28, 32, 36, 40, 48, 64, 96, 128]
DEGRADATION_LEVELS = ["clean", "light_shadow", "heavy_shadow", "blur", "moire"]
SCRIPTS = ["latin", "cjk", "mixed"]

# ~2K images: 13 heights x 5 degradations x 3 scripts x ~10 samples each
```

#### C2. Correction Model

Train a lightweight regression to correct systematic bias:

```python
# Linear regression: Real_Height = a * Measured_Height + b
# Or per-degradation-type correction:
# Real_Height = f(Measured_Height, degradation_score, script_type)

from sklearn.linear_model import LinearRegression
# or
from sklearn.ensemble import GradientBoostingRegressor

# Features: [measured_height, height_cv, confidence, num_regions, degradation_proxy]
# Target: known_height (from synthetic rendering)
```

**Why**: Even with Sauvola + morphological closing, degradation causes systematic underestimation (blur erodes binary masks, reducing measured height). A calibration model learned from synthetic ground truth corrects this bias without requiring human annotations.

#### C3. Gold Standard Validation Set

Create 300-500 image validation set using multi-scale OCR:

```python
# Run PaddleOCR recognition at 5 scales: 0.5x, 0.75x, 1.0x, 1.5x, 2.0x
# Peak confidence scale indicates optimal resolution
# Back-calculate character height from scale ratio

# This is computationally expensive (~5x inference) so only for validation
# NOT for production labeling
```

#### C4. Active Learning Loop

Flag low-confidence measurements for human validation:

```python
# Criteria for active learning review:
# 1. confidence_pct < 0.4
# 2. CC and projection disagree by >20%
# 3. DBSCAN finds >3 clusters (unusual document)
# 4. height_cv > 0.4 (high inconsistency)

# Human reviews ~100-200 images per iteration
# Corrections feed back into calibration model
```

**Expected improvement**: IQR from ~4-5px to ~3-4px (final 20-25% reduction)

---

## Implementation Priority

| Phase | Priority | Effort | Precision Gain | Dependencies |
|-------|----------|--------|----------------|--------------|
| A (Sauvola + closing + KDE) | **P0 - Do First** | 1-2 days | 9px -> 6-7px | OpenCV ximgproc |
| B (Ensemble + DBSCAN) | **P1 - Do Second** | 3-4 days | 6-7px -> 4-5px | scipy, sklearn |
| C (Calibration + gold set) | **P2 - Do Third** | 2-3 days | 4-5px -> 3-4px | Synthetic gen |

**Total effort**: 6-9 days for full V2 pipeline
**Compute overhead**: +45% over V1 (still <6 hours for 30K images on A100)

---

## Validation Plan

### Per-Phase Validation

| Checkpoint | Method | Success Criteria |
|------------|--------|-----------------|
| Phase A complete | Re-run on 36 DIQA-5000 audit samples | IQR <= 7px, cross-bucket <= 40% |
| Phase B complete | Re-run on full DIQA-5000 (5,500) | IQR <= 5px, cross-bucket <= 25% |
| Phase C complete | Validate against gold standard (300-500) | MAE <= 3px, Spearman r >= 0.90 |

### Cross-Dataset Validation

After V2 pipeline is stable, run on:

1. **OHR-Bench** (8,500 images) - different degradation profile
2. **RealDAE** (1,200 images) - real document artifacts
3. **SmartDoc-QA** - camera-captured with known DPI reference

### Regression Checks

- Coarse bucket accuracy must NOT degrade (maintain KW H > 100)
- Measurement coverage must stay >= 99%
- Processing speed must stay < 1 second/image on A100

---

## Output Schema Changes (V2)

V2 adds 4 new fields to the per-image record:

```json
{
  "resolution_quality_score": 0.62,
  "confidence_pct": 0.92,
  "char_height_px": 38.5,
  "char_height_range_px": [36.0, 41.0],
  "score_range": [0.59, 0.65],
  "coarse_bucket": "optimal",
  "measurement_method": "stage_1_2_v2",
  "num_text_regions": 42,
  "num_valid_cc_regions": 38,
  "height_cv": 0.08,
  "flagged_for_review": false,

  "v2_projection_height_px": 39.1,
  "v2_ensemble_weight": {"cc": 0.3, "projection": 0.7},
  "v2_dominant_script": "cjk",
  "v2_calibration_applied": true
}
```

---

## Dependencies

| Package | Version | Phase | Purpose |
|---------|---------|-------|---------|
| opencv-contrib-python | >= 4.8 | A | Sauvola via ximgproc |
| scipy | >= 1.10 | A | KDE mode estimation |
| scikit-learn | >= 1.3 | B, C | DBSCAN, regression |
| numpy | >= 1.24 | All | Array operations |
| paddleocr | >= 2.7, < 3.0 | All | DBNet text detection (unchanged) |

**Note**: `opencv-contrib-python` replaces `opencv-python` to access `ximgproc` module. They cannot coexist.

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Sauvola slower than Gaussian | Low | ~2x slower per region, but regions are small crops; total pipeline impact <15% |
| Morphological closing merges adjacent characters | Medium | Use 3x1 / 1x3 kernels (not 3x3); validate on tight-spacing samples |
| Projection profiles fail on single-word regions | Medium | Fallback to CC for regions with <5 characters; track via measurement_method |
| Synthetic calibration overfits to rendering engine | Medium | Use diverse fonts (50+), backgrounds, degradation profiles |
| opencv-contrib-python compatibility | Low | Well-maintained; same API as opencv-python with extra modules |
| DBSCAN eps sensitivity | Medium | Tune on audit samples; adaptive eps based on median height |

---

## Critical Files

| File | Role |
|------|------|
| [resolution_quality.py](../../src/image_preprocessing_detector/schema_utils/resolution_quality.py) | Core module - Phase A/B changes here |
| [label_resolution_quality.py](../../scripts/label_resolution_quality.py) | Labeling script - Phase C integration |
| [integrate_resolution_quality.py](../../scripts/integrate_resolution_quality.py) | L2 metadata integration (unchanged) |
| [RESOLUTION_QUALITY_LABELING_STRATEGY.md](RESOLUTION_QUALITY_LABELING_STRATEGY.md) | V1 strategy (reference) |
| [generator.py:547-623](../../src/image_preprocessing_detector/synthetic/generator.py#L547-L623) | Synthetic char height measurement (reference for Phase C) |
| [diqa-5000.md](../datasets/source/diqa-5000.md) | Dataset documentation (v6 with RQ section) |

---

## Model Selection Evaluation (2026-02-12)

### Question

Would replacing PaddleOCR DBNet with a different text detection/recognition model significantly improve measurement accuracy?

### 4-Model Consensus (FOR/AGAINST Debate)

**Models**: Gemini 2.5 Pro (FOR, 9/10), Gemini 3 Pro Preview (AGAINST, 9/10), DeepSeek R1 (NEUTRAL, 8/10), Grok 4 (NEUTRAL, 8/10)

### Unanimous Agreements (4/4)

| Finding | Details |
|---------|---------|
| **PaddleOCR rec=True is lowest-risk first step** | Same library, enable recognition flag, get per-character CJK positions |
| **Line-level alternatives offer NO improvement** | DBNet++, MMOCR line detection, docTR still need CC analysis |
| **Tesseract not viable** | LSTM boxes loose and erratic on noisy camera images |
| **Validation on degraded subset mandatory** | Must test 500+ DIQA-5000 degraded images before committing |

### Key Disagreement: Detection vs Measurement

| Position | Advocate | Core Argument |
|----------|----------|---------------|
| **Replace with char-level model** | Gemini 2.5 Pro (9/10) | Character-level detection directly outputs what we need. CC improvements are diminishing returns on imprecise input |
| **Keep detector, improve measurement** | Gemini 3 Pro Preview (9/10) | "Detectors are not micrometers" - NN boxes optimize for IoU, not pixel-precise height. Raw pixel measurement (Sauvola/projection) is actual ground truth |

### Resolution: Don't Change Detector, DO Add Recognizer

The disagreement resolves when distinguishing between:

- **Detection models** (CRAFT heatmaps, DBNet char-level): IoU-optimized, padded boxes - Gemini 3 is RIGHT that these are imprecise
- **Recognition positions** (PaddleOCR rec=True): Recognizer-derived character positions learned from CJK geometry - these ARE more precise

**Recommended architecture**:

```text
Primary:  DBNet detection → PaddleOCR recognition (rec=True) → char box heights → KDE aggregation
Fallback: DBNet detection → V2 CC (Sauvola + morphological closing + projection profiles)
Trigger:  recognition confidence < threshold OR rec returns 0 characters
```

### Model Comparison Matrix (from DeepSeek R1)

| Model | Accuracy Gain | CJK Handling | Degradation Robustness | Output |
|-------|---------------|--------------|------------------------|--------|
| **PaddleOCR rec=True** | High | Excellent | Moderate | Char boxes |
| **CRAFT** | High | Poor (fragments radicals) | Poor | Char heatmaps |
| **Surya OCR** | High | Good | Good | Char boxes |
| **DBNet++** | Low | Good | Good | Lines only |
| **docTR** | Low-Med | Moderate | Moderate | Lines/words |
| **MMOCR** | Low | Good | Good | Lines only |
| **Tesseract** | Low | Poor | Very Poor | Char boxes (loose) |

### Impact on V2 Phases

| Phase | With rec=True | Without rec=True |
|-------|---------------|-----------------|
| **A (Sauvola + closing)** | Still needed as **fallback** for rec failures | Primary measurement path |
| **B (Projection + ensemble)** | Ensemble now includes rec char heights as third signal | Primary measurement path |
| **C (Calibration)** | Calibrate rec-derived heights too | Calibrate CC/projection heights |

### Practical Next Step

Before implementing full V2, run a **quick validation experiment**:

1. Enable `rec=True` on 500 DIQA-5000 images (mix of clean + degraded + rotated)
2. Extract per-character box heights from recognizer output
3. Compare IQR against V1 CC heights on same images
4. If IQR < 5px: rec=True becomes primary, V2 CC becomes fallback
5. If IQR >= 5px: proceed with V2 CC improvements as primary

**Estimated effort**: 2-4 hours (mostly API exploration + scripting)

### Script-Aware Optimization

If a script detection head runs before resolution quality measurement (e.g., MobileNetV4 script head or synth-multiscript-250K classifier), knowing the document script significantly improves accuracy:

| Script | Optimal Strategy | Aspect Ratio | Closing Kernel | Ensemble Weight |
|--------|-----------------|--------------|----------------|-----------------|
| CJK | Projection profiles primary | 0.6-1.4 (square) | Aggressive (3x1 + 1x3) | 0.7 proj / 0.3 CC |
| Latin | CC analysis primary | 0.2-0.8 (tall-narrow) | Minimal (1x1) | 0.3 proj / 0.7 CC |
| Arabic | Projection primary (RTL) | 0.3-1.5 (wide variation) | Moderate (2x1) | 0.6 proj / 0.4 CC |
| Devanagari | Projection + headline detection | 0.4-1.2 | Moderate | 0.5 proj / 0.5 CC |
| Mixed | Equal ensemble | 0.2-5.0 (broad) | Moderate | 0.5 / 0.5 |

**Script detection improves RQ accuracy by**:

1. Selecting optimal measurement method per script (±1-2px reduction)
2. Setting appropriate binarization parameters (CJK needs lower Sauvola k)
3. Adjusting morphological closing (CJK needs aggressive reconnection)
4. Filtering CC aspect ratios to match script geometry
5. Weighting ensemble signals based on known script characteristics

---

## Consensus Provenance

### V2 Strategy Consensus (2026-02-12)

- **Tool**: PAL MCP consensus workflow
- **Models**: Gemini 2.5 Pro (9/10), Gemini 3 Pro Preview (9/10), GPT-5.2 (empty), DeepSeek R1 (8/10), Grok 4 (8/10)
- **Mean confidence**: 8.5/10
- **Continuation ID**: 4c85b438-409b-4375-9222-146dcc445259

### Model Selection Consensus (2026-02-12)

- **Tool**: PAL MCP consensus workflow (FOR/AGAINST debate)
- **Models**: Gemini 2.5 Pro (FOR, 9/10), Gemini 3 Pro Preview (AGAINST, 9/10), DeepSeek R1 (NEUTRAL, 8/10), Grok 4 (NEUTRAL, 8/10)
- **Mean confidence**: 8.5/10
- **Continuation ID**: 9887202b-eb65-436a-97bb-08aee04991b9

---

## Weak Label Output Schema (v2.2)

Defines the output format for the weak label model (teacher) predictions when labeling real datasets.
Used by `integrate_resolution_quality.py` to merge into L2 metadata.

### Per-Image Prediction Record

```json
{
  "image_id": "doclaynet_0001.png",
  "char_height_px": 34.2,
  "char_height_std": 2.1,
  "resolution_quality_score": 0.58,
  "quality_score_std": 0.06,
  "coarse_bucket": "optimal",
  "bucket_probabilities": {
    "needs_major_upscale": 0.01,
    "needs_light_upscale": 0.22,
    "optimal": 0.63,
    "good": 0.12,
    "oversized": 0.02
  },
  "label_provenance": "tier_2_model",
  "label_source": "weak_label_model_v1",
  "label_confidence": 0.82,
  "script_used": "Latn",
  "script_confidence": 0.95,
  "model_version": "mobilenetv4_rq_v1",
  "training_data_version": "synth-multiscript-v2-rq"
}
```

### Provenance Tiers

| Tier | Source | Confidence | Use Case |
|------|--------|------------|----------|
| `tier_0_exact` | Synthetic generation | 1.0 | Ground truth for teacher training |
| `tier_1_annotation` | Human annotation | 0.9-1.0 | Gold standard validation |
| `tier_2_model` | Weak label model | 0.5-0.95 | Bulk real dataset labeling |
| `tier_3_heuristic` | CC measurement | 0.3-0.9 | V1 PaddleOCR pipeline |

### Soft Label Training Usage

- **Student classification**: KL-divergence loss on `bucket_probabilities` (soft cross-entropy)
- **Student regression**: Uncertainty-weighted MSE on `quality_score` using `quality_score_std`
- **Sample weighting**: `label_confidence * (1 / max(quality_score_std, 0.01))`
- **Active learning**: Flag samples where `quality_score_std > threshold` for manual review

### Comparison: Hard vs Soft Labels

| Aspect | Hard Labels (V1) | Soft Labels (V2) |
|--------|-------------------|-------------------|
| Bucket | Single class | Probability distribution over 5 classes |
| Score | Point estimate | Mean + standard deviation |
| Boundary behavior | Arbitrary cutoff | Smooth transition with uncertainty |
| Training signal | Cross-entropy | KL-divergence (preserves teacher uncertainty) |
| Calibration | Often overconfident | Uncertainty-aware |
