---
schema_type: dev
title: "ADR-016: Defer Superscript/Footnote Detection to Post-OCR"
description: "Defer superscript and footnote detection to post-OCR analysis phase"
tags: [adr, ocr, footnotes, superscripts, text-analysis]
status: published
owner: "core-maintainer"
authors:
  - name: "Byron Williams"
purpose: "Document the decision to defer superscript/footnote detection until after OCR provides baseline and font size information"
---

# ADR-016: Defer Superscript/Footnote Detection to Post-OCR

**Status**: Accepted
**Date**: 2025-01-15
**Deciders**: Byron Williams
**Related**:
- [ARCHITECTURE_SUMMARY.md](../../ARCHITECTURE_SUMMARY.md)
- [PROJECT_PLAN.md](../../PROJECT_PLAN.md)
- [ADR-008: Multi-Stage Pipeline Architecture](0008-multi-stage-pipeline-architecture.md)

## Context

Superscript and footnote detection could be implemented at the image preprocessing stage (Phase 1-3) or during post-OCR analysis (Phase 4+). We needed to decide the optimal stage for this functionality.

### Technical Challenges

**Image-Level Detection (Pre-OCR)**:
- Difficult to distinguish superscripts from noise
- No baseline information available
- Cannot determine relative font size
- Complex heuristics required (connected components analysis, spatial positioning)

**Post-OCR Detection**:
- OCR provides baseline position
- Font size metadata available
- Text content helps disambiguation (e.g., "1", "2", "3" likely footnote references)
- Simpler rule-based heuristics

## Decision

**Defer superscript and footnote detection to post-OCR analysis phase.**

### Rationale

1. **OCR Provides Critical Metadata**: Baseline position and font size make detection trivial
2. **Lower False Positive Rate**: Text content helps distinguish superscripts from noise
3. **Phase Alignment**: Post-OCR analysis is Phase 4+ work, matches development timeline
4. **Simpler Implementation**: Rule-based heuristics vs complex image processing

### Post-OCR Detection Strategy

```python
def detect_superscripts_post_ocr(ocr_results):
    """Detect superscripts using OCR metadata."""
    superscripts = []

    for word in ocr_results.words:
        # Check baseline position (above main text)
        if word.baseline_offset > threshold:
            # Check font size (smaller than main text)
            if word.font_size < main_text_size * 0.7:
                # Check content (numeric footnote reference)
                if word.text.isdigit() or word.text in ['*', '†', '‡']:
                    superscripts.append(word)

    return superscripts
```

## Consequences

### Positive

1. **Simpler Implementation**: Rule-based heuristics vs complex image processing
2. **Higher Accuracy**: OCR metadata enables reliable detection
3. **Phase Alignment**: Defers complexity to Phase 4 when OCR infrastructure ready
4. **Lower False Positives**: Text content helps disambiguation

### Negative

1. **Delayed Feature**: Not available until Phase 4
2. **OCR Dependency**: Requires OCR to be run first
3. **OCR Quality Impact**: Degraded OCR affects detection accuracy

### Neutral

1. **No Image Preprocessing**: Superscripts not enhanced/corrected during preprocessing
2. **Downstream Handling**: RAG systems handle superscripts during text extraction

## Alternatives Considered

### Alternative 1: Image-Level Detection (Pre-OCR)

**Approach**: Detect superscripts using connected components analysis and spatial positioning

**Advantages**:
- Available in Phase 1-3
- No OCR dependency
- Could enable superscript enhancement

**Disadvantages**:
- Complex heuristics (baseline estimation, relative sizing)
- Higher false positive rate (noise, decorations)
- Cannot distinguish content (numbers vs letters)
- Difficult to distinguish from small caps

**Why Rejected**: Too complex for limited benefit, better to use OCR metadata

### Alternative 2: ML-Based Detection (Pre-OCR)

**Approach**: Train YOLOv8 or segmentation model to detect superscripts

**Advantages**:
- Higher accuracy than heuristics
- Can handle complex layouts

**Disadvantages**:
- Requires labeled training data (expensive)
- Additional model deployment complexity
- Slower inference
- Still lacks text content for disambiguation

**Why Rejected**: Overkill for problem better solved by OCR metadata

### Alternative 3: Never Detect Superscripts

**Approach**: Ignore superscripts entirely, rely on downstream OCR

**Advantages**:
- Simplest approach
- No additional work

**Disadvantages**:
- Misses opportunity to improve OCR quality
- No structured metadata for footnote references

**Why Rejected**: Post-OCR detection is simple and valuable

## Implementation

### Phase 4 Post-OCR Analysis (Planned)

**Integration with OCR Pipeline**:
```python
def analyze_ocr_output(page_image, ocr_results):
    """Post-OCR analysis including superscript detection."""

    # 1. Baseline estimation
    baselines = estimate_text_baselines(ocr_results)

    # 2. Main text font size
    main_font_size = np.median([w.font_size for w in ocr_results.words])

    # 3. Detect superscripts
    superscripts = []
    for word in ocr_results.words:
        if (word.baseline_offset > 0.3 * main_font_size and
            word.font_size < 0.7 * main_font_size and
            (word.text.isdigit() or word.text in FOOTNOTE_SYMBOLS)):

            superscripts.append({
                "text": word.text,
                "bbox": word.bbox,
                "type": "footnote_reference" if word.text.isdigit() else "superscript"
            })

    # 4. Add to metadata
    return PostOCRMetadata(
        superscripts=superscripts,
        footnote_references=filter_footnote_refs(superscripts)
    )
```

**Footnote Symbols**: `['*', '†', '‡', '§', '¶', '**', '††']`

### Output Schema Extension

```python
class PostOCRMetadata(BaseModel):
    """Post-OCR analysis results."""
    superscripts: List[SuperscriptDetection]
    footnote_references: List[FootnoteReference]
    estimated_baselines: List[Baseline]

class SuperscriptDetection(BaseModel):
    text: str
    bbox: List[float]  # COCO format
    type: Literal["footnote_reference", "superscript", "exponent"]
    confidence: float
```

## References

- [ARCHITECTURE_SUMMARY.md](../../ARCHITECTURE_SUMMARY.md)
- [PROJECT_PLAN.md Phase 4](../../PROJECT_PLAN.md#phase-4-production-hardening-weeks-17-20)
- [ADR-008: Multi-Stage Pipeline Architecture](0008-multi-stage-pipeline-architecture.md)
- [DocTR OCR Documentation](https://mindee.github.io/doctr/)

## Lessons Learned

1. **OCR Metadata is Powerful**: Baseline and font size make detection trivial
2. **Phase Alignment Matters**: Defer complexity to appropriate development phase
3. **Simplicity Wins**: Rule-based heuristics with OCR metadata beat complex image processing
