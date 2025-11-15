# DocLayNet Dataset Coverage for Stage 3A/3B Validation

**Dataset**: DocLayNet (81,471 PDFs with COCO annotations)
**Location**: `/home/byron/dev/data_ingestor/data/benchmarks/doclaynet`

---

## Stage 3A: Image Quality Assessment (IQA) - NO-TEXT BRANCH

**Detection Categories**: 6 total

| # | Issue | Ground Truth Available? | Validation Approach |
|---|-------|------------------------|---------------------|
| 1 | **Noise** | ❌ No labels | Manual annotation or synthetic only |
| 2 | **Blur** | ❌ No labels | Manual annotation or synthetic only |
| 3 | **Skew/Rotation** | ❌ No labels | Manual annotation or synthetic only |
| 4 | **Perspective Distortion** | ❌ No labels | Manual annotation or synthetic only |
| 5 | **Low Contrast** | ❌ No labels | Manual annotation or synthetic only |
| 6 | **Image Orientation** | ❌ No labels | Manual annotation or synthetic only |

**Coverage**: **0/6 (0%)** - No IQA ground truth in DocLayNet

### Alternative Validation Strategy for Stage 3A

Since DocLayNet lacks IQA labels:

1. ✅ **Synthetic validation** (current approach) - 100% ground truth control
2. 🔧 **Manual labeling**: Select 100-200 DocLayNet samples, manually label quality issues
3. 📊 **Statistical analysis**: Analyze distribution of detected issues across dataset
4. 🎯 **Unsupervised validation**: Compare detector outputs with human judgment on samples

**Recommendation**: Continue with synthetic validation + manual spot-checking on DocLayNet samples

---

## Stage 3B: Document Element Detection - TEXT BRANCH

**Detection Categories**: 6 total (4 primary + 2 deferred)

### DocLayNet COCO Categories (11 total)
1. Caption
2. Footnote
3. Formula
4. List-item
5. Page-footer
6. Page-header
7. Picture
8. Section-header
9. Table
10. Text
11. Title

### Coverage Analysis

| # | Element | DocLayNet Label | Available? | Count Estimate | Notes |
|---|---------|----------------|------------|----------------|-------|
| 1 | **Tables** | `Table` | ✅ Yes | ~25,000+ | Perfect match |
| 2 | **Images/Figures** | `Picture` | ✅ Yes | ~30,000+ | Perfect match |
| 3 | **Handwriting** | ❌ None | ❌ No | 0 | Not in DocLayNet |
| 4 | **Mathematical Formulas** | `Formula` | ✅ Yes | ~15,000+ | Perfect match |
| 5 | **Non-Latin characters** | ❌ None | ⚠️ Partial | Unknown | No script labels, but may exist in documents |
| 6 | **Superscript/Footnotes** | `Footnote` | ✅ Yes | ~20,000+ | Perfect match |

**Coverage**: **4/6 (66.7%)** - Good coverage for primary elements

### Bonus Categories Available

DocLayNet provides additional layout elements beyond Stage 3B requirements:

| DocLayNet Category | Usefulness | Potential Use |
|-------------------|------------|---------------|
| `Caption` | ✅ High | Can improve Table/Figure detection |
| `List-item` | ✅ Medium | Structured content extraction |
| `Page-footer` / `Page-header` | ✅ Medium | Document structure understanding |
| `Section-header` / `Title` | ✅ High | Document hierarchy |
| `Text` | ✅ Critical | Text block segmentation |

---

## Validation Capabilities Summary

### Stage 3A (IQA) - 0/6 Detectable with DocLayNet
- **Current approach**: ✅ Synthetic validation (28 images, 100% ground truth)
- **DocLayNet contribution**: ❌ None (no quality labels)
- **Recommendation**: Manual label 100-200 DocLayNet samples for real-world validation

### Stage 3B (Document Elements) - 4/6 Detectable with DocLayNet

#### ✅ **Can Validate** (4 elements):
1. **Tables** - ~25,000+ annotated instances
2. **Images/Figures** - ~30,000+ annotated instances
3. **Mathematical Formulas** - ~15,000+ annotated instances
4. **Footnotes** - ~20,000+ annotated instances

#### ❌ **Cannot Validate** (2 elements):
5. **Handwriting** - Not present in DocLayNet (business documents)
6. **Non-Latin characters** - No script identification labels

---

## Recommended Validation Strategy

### Phase 1 (Current) - Completed ✅
- Synthetic IQA validation: **28 images with perfect ground truth**
- Metrics: Blur 100%, Contrast 100%, Skew 82%

### Phase 2 - LayoutParser Integration (Next)

**What you CAN validate with DocLayNet:**

```python
# Full validation pipeline for Stage 3B
validation_targets = {
    "tables": {
        "coco_category": "Table",
        "validation_metric": "IoU > 0.5 (COCO mAP)",
        "sample_size": "1,000 PDFs",
        "expected_accuracy": ">80% mAP@0.5"
    },
    "figures": {
        "coco_category": "Picture",
        "validation_metric": "IoU > 0.5 (COCO mAP)",
        "sample_size": "1,000 PDFs",
        "expected_accuracy": ">85% mAP@0.5"
    },
    "formulas": {
        "coco_category": "Formula",
        "validation_metric": "IoU > 0.5 (COCO mAP)",
        "sample_size": "500 PDFs",
        "expected_accuracy": ">75% mAP@0.5"
    },
    "footnotes": {
        "coco_category": "Footnote",
        "validation_metric": "IoU > 0.5 (COCO mAP)",
        "sample_size": "500 PDFs",
        "expected_accuracy": ">70% mAP@0.5"
    }
}
```

**Sample validation code:**
```python
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval

# Load DocLayNet COCO annotations
coco_gt = COCO('/path/to/doclaynet/coco/val.json')

# Run your detector on validation set
detections = run_element_detector(validation_images)

# Calculate COCO mAP metrics
coco_dt = coco_gt.loadRes(detections)
coco_eval = COCOeval(coco_gt, coco_dt, 'bbox')
coco_eval.evaluate()
coco_eval.accumulate()
coco_eval.summarize()
```

### Phase 3 - Additional Datasets for Missing Elements

**For Handwriting Detection:**
- **IAM Handwriting Database**: 13,353 handwritten pages
- **RIMES Dataset**: French handwritten documents
- **NIST Handwriting Forms**: US government forms

**For Non-Latin Scripts:**
- **XFUND**: Multilingual forms (7 languages)
- **FUNSD**: Form understanding dataset
- **RVL-CDIP**: Document classification with diverse scripts

---

## Immediate Next Steps

### Option 1: Expand IQA Validation (Recommended for Production)
```bash
# Manual labeling script for DocLayNet quality issues
poetry run python validation/label_doclaynet_quality.py \
    --sample-size 200 \
    --output validation/doclaynet_quality_labels.json
```

### Option 2: Prepare for Stage 3B Validation
```bash
# Validate against DocLayNet COCO annotations (Phase 2)
poetry run python validation/validate_element_detection.py \
    --coco-path /home/byron/dev/data_ingestor/data/benchmarks/doclaynet/ground_truth/coco/val.json \
    --images-path /home/byron/dev/data_ingestor/data/benchmarks/doclaynet/documents/pdf \
    --categories table,picture,formula,footnote
```

---

## Summary Table

| Validation Target | Can Use DocLayNet? | Sample Size | Ground Truth Quality |
|------------------|-------------------|-------------|----------------------|
| **Stage 3A - IQA** | | | |
| Noise | ❌ | 0 | N/A |
| Blur | ❌ | 0 | N/A |
| Skew | ❌ | 0 | N/A |
| Perspective | ❌ | 0 | N/A |
| Contrast | ❌ | 0 | N/A |
| Orientation | ❌ | 0 | N/A |
| **Stage 3B - Elements** | | | |
| Tables | ✅ | ~25,000 | Excellent (COCO bbox) |
| Figures | ✅ | ~30,000 | Excellent (COCO bbox) |
| Formulas | ✅ | ~15,000 | Excellent (COCO bbox) |
| Footnotes | ✅ | ~20,000 | Excellent (COCO bbox) |
| Handwriting | ❌ | 0 | N/A |
| Non-Latin | ⚠️ | Unknown | No labels |

**Overall Coverage**: **4/12 (33%)** elements can be validated with DocLayNet ground truth

**Stage 3A Coverage**: **0/6 (0%)** - Use synthetic validation
**Stage 3B Coverage**: **4/6 (67%)** - Excellent for primary document elements

---

## Conclusion

**DocLayNet is PERFECT for Stage 3B document element detection** but provides **NO validation** for Stage 3A image quality assessment.

**Recommended Approach**:
1. ✅ **Continue synthetic validation for Stage 3A** (current approach works well)
2. ✅ **Use DocLayNet for Stage 3B** when you implement LayoutParser/YOLOv8 (Phase 2)
3. 🔧 **Manual label 100-200 DocLayNet samples** for real-world IQA validation (optional)
4. 📊 **Combine synthetic + DocLayNet** for comprehensive validation coverage

---

*Analysis based on DocLayNet v1.0 dataset structure (2025-11-04)*
