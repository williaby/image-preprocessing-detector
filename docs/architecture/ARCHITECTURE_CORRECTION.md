# Architecture Correction: Hybrid IQA Approach

**Date**: 2025-01-15
**Issue**: Original architecture had IQA only on no-text branch
**Correction**: Documents with text often contain embedded images that need quality assessment

**See**: [ADR-007: Hybrid IQA Approach for Embedded Images](docs/ADRs/0007-hybrid-iqa-approach.md)

---

## Updated Architecture

### Original (Incorrect)
```
Text Detection Gate
    ↓              ↓
[NO TEXT]      [TEXT DETECTED]
    ↓              ↓
IQA Only       Layout Detection Only
```

### Corrected (Accurate)
```
Text Detection Gate
    ↓              ↓
[NO TEXT]      [TEXT DETECTED]
    ↓              ↓
IQA on         Layout Detection (YOLO)
Full Page           ↓
                [Detect Image/Figure Elements]
                    ↓
                Run IQA on Each Image Bbox
                    ↓
                Report per-element quality issues
```

---

## Key Insight

**Real-world scenario**: Technical documentation, academic papers, reports
- Contains text (headers, paragraphs, captions)
- Contains embedded images (diagrams, photos, charts)
- **The embedded images may have quality issues** (blur, low resolution, noise)

**Solution**: Hybrid approach
1. Text detection gate routes to layout detection path
2. YOLOv8 detects all elements including Image/Figure bboxes
3. **For each detected Image element**:
   - Crop the image region from the page
   - Run IQA classifier on the cropped region
   - Report quality issues specific to that image
4. This allows targeted correction without affecting text regions

---

## Implementation Changes

### Stage 3B Updated: Document Element Detection + Hybrid IQA

**Processing Flow:**
1. **Layout Detection** (YOLOv8): Detect all elements (Table, Image, Handwriting, Formula)
2. **Image Quality Assessment** (Per Image Element):
   ```python
   for element in detected_elements:
       if element.category == "image":
           # Crop image region
           image_crop = crop_bbox(page_image, element.bbox)

           # Run IQA on cropped region
           quality_issues = iqa_model.predict(image_crop)

           # Attach to element metadata
           element.quality_issues = quality_issues
           element.needs_correction = any(issue.confidence > 0.85 for issue in quality_issues)
   ```

3. **Selective Correction**: Apply corrections only to problematic image regions

### Benefits

1. **Precision**: Only correct images that need it, preserve good quality images
2. **Safety**: Avoid applying page-level corrections that might harm text regions
3. **Granularity**: Track quality issues per image element for detailed reporting
4. **Flexibility**: Different correction strategies for embedded images vs full-page scans

### JSON Schema Addition

```json
{
  "elements": [
    {
      "id": "elem_001",
      "category": "image",
      "bbox": [150, 400, 300, 200],
      "confidence": 0.94,
      "quality_issues": [
        {
          "type": "blur",
          "confidence": 0.87,
          "severity": "medium",
          "metrics": {"laplacian_variance": 125.4}
        }
      ],
      "needs_correction": true,
      "correction_applied": {
        "action": "sharpen",
        "params": {"kernel_size": 5, "alpha": 1.5},
        "success": true
      }
    }
  ]
}
```

---

## Performance Impact

**Additional Latency per Page**:
- If page has N detected images
- IQA per image: 1-3ms GPU (on cropped region)
- Total: N × 1-3ms additional latency
- Typical: 2-3 images per page → +2-9ms
- **Acceptable trade-off** for correct quality assessment

**Optimization**:
- Batch inference: Process all image crops in single batch
- Early exit: Skip IQA if image is large and high-resolution (likely good quality)
- Parallel: Run IQA on crops while other elements are being processed

---

## Updated Stage Summary

### Stage 3: Detection (Text Branch)

1. **Layout Detection (YOLOv8)**: 2-7ms GPU
   - Detect: Tables, Images, Handwriting, Formulas

2. **Hybrid IQA** (Per Image Element): 1-3ms GPU per image
   - Crop each detected Image/Figure region
   - Run IQA classifier on crop
   - Report quality issues per element

3. **Secondary Analysis**: 5-10ms
   - Non-Latin script detection
   - (Superscript/footnotes deferred to post-OCR)

**Total Text Branch**: 8-20ms GPU (depending on number of images)

---

## Decision: Corrected Architecture Approved

**Rationale**: More accurate to real-world needs, minimal performance impact

**Action Items**:
- [x] Document architecture correction
- [ ] Update PROJECT_PLAN.md with hybrid IQA approach
- [ ] Implement hybrid IQA in Phase 1/2
- [ ] Update JSON schema to include per-element quality issues

---

*This correction ensures the system handles the most common real-world scenario: documents with text AND embedded images that may have quality issues.*
