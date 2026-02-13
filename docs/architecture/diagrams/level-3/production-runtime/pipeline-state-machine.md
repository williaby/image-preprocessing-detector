---
schema_type: common
title: "Level 3: Production Runtime - Pipeline State Machine"
description: "Detailed state machine specification for the production document processing
  pipeline"
tags:
- architecture
- level_3
- production_runtime
- state_machine
- error_handling
status: published
owner: "core-maintainer"
authors:
- name: "Byron Williams"
purpose: "Document the complete state machine implementation for production runtime
  pipeline including all 13 states, transitions, timeouts, and error recovery paths."
---
This document provides the complete state machine specification for the production document processing pipeline, including all states, transitions, error handling, and edge cases.

> **Implementation Status**: ⚠️ **Design Complete, Implementation In Progress**
>
> This state machine design is complete and documented below. The core pipeline (Phases 0-3) is **✅ 100% implemented**.
> Advanced orchestration features (Phase 4) are **⚠️ 98% complete** with the following components:
>
> **Implemented** (Phases 0-3, 6):
>
> - ✅ Ingestion & Preflight (Phase 0, 1B)
> - ✅ PDF Classification (Phase 2)
> - ✅ Text Gate (Phase 1)
> - ✅ Classical IQA (Phase 1, 1C)
> - ✅ Layout-Lite (Phase 2)
> - ✅ MobileNetV4-Conv-S + SigLIP 2 NAFlex (multi-task)
> - ✅ Correction (Phase 1)
> - ✅ DQS & Routing (Phase 2)
> - ✅ Output Generation (Phase 0, 2)
> - ✅ Workers & Celery Tasks (Phase 4)
> - ✅ Monitoring & Drift Detection (Phase 6)
>
> **In Progress** (Phase 4):
>
> - ⚠️ Device Orchestration (98% complete - async I/O remaining)
> - ⚠️ State machine orchestrator module (planned)
>
> **Source Files**:
>
> - Implemented: 43/44 files (16,727 lines)
> - Planned: 1 file (~183 lines for state orchestrator)

---

## Overview

The production runtime processes documents through **16 well-defined states** with explicit entry/exit conditions, timeouts, and comprehensive error recovery. This state machine ensures predictable behavior, robust error handling, and complete audit trails.

### Design Principles

1. **Explicit State Transitions**: Every state change is logged and tracked
2. **Timeout Enforcement**: All states have bounded execution time
3. **Graceful Degradation**: Fallback paths for all error conditions
4. **Partial Success**: Process as many pages as possible, flag failures
5. **Audit Trail**: Complete history of state transitions and decisions

### State Machine Characteristics

| Characteristic | Value |
|---------------|-------|
| **Total States** | 16 (including terminal states) |
| **Happy Path States** | 14 (INGESTION → OUTPUT) |
| **Error States** | 2 (FAILED, PARTIAL_SUCCESS) |
| **Average Latency** | 150ms/page (GPU), 500ms/page (CPU) |
| **Maximum Timeout** | 600s total per document |
| **Retry Budget** | 3 attempts per transient failure |

---

## Complete State Diagram

```plantuml
@startuml Production_Pipeline_State_Machine
!theme plain
skinparam backgroundColor #FEFEFE

title Production Runtime Pipeline - Complete State Machine
footer 16 States | GPU: 150ms/page | CPU: 500ms/page | Max: 600s total

[*] --> INGESTION : Document received

state INGESTION {
  [*] --> Loading
  Loading --> ExtractingPages : PDF detected
  Loading --> NormalizingImage : Image detected
  ExtractingPages --> [*]
  NormalizingImage --> [*]
}
INGESTION : **Entry**: PDF/image received
INGESTION : **Exit**: Pages extracted to 300 DPI
INGESTION : **Timeout**: 30s
INGESTION : **Source**: ingestion/document_processor.py (303 lines)
INGESTION : **Source**: ingestion/pdf_loader.py (265 lines)
INGESTION : **Source**: ingestion/image_loader.py (280 lines)

INGESTION --> PREFLIGHT : Pages ready
INGESTION --> FAILED : Corrupted file

state PREFLIGHT {
  [*] --> AnalyzingDPI
  AnalyzingDPI --> Upscaling : DPI < 300
  AnalyzingDPI --> [*] : DPI >= 300
  Upscaling --> [*]
}
PREFLIGHT : **Entry**: Pages extracted
PREFLIGHT : **Exit**: DPI analyzed, upscaling complete
PREFLIGHT : **Timeout**: 15s
PREFLIGHT : **Source**: ingestion/pdf_analyzer.py (256 lines)
PREFLIGHT : **Source**: ingestion/pdf_resolution.py (264 lines)
PREFLIGHT : **Source**: ingestion/pdf_upscaler.py (330 lines)

PREFLIGHT --> PDF_CLASSIFICATION : Preflight complete
PREFLIGHT --> PDF_CLASSIFICATION : Skip upscaling (timeout)

state PDF_CLASSIFICATION {
  [*] --> ExtractingText
  ExtractingText --> DetectingImages
  DetectingImages --> Classifying
  Classifying --> [*]
}
PDF_CLASSIFICATION : **Entry**: Preflight complete
PDF_CLASSIFICATION : **Exit**: PDF type determined
PDF_CLASSIFICATION : **Timeout**: 10s
PDF_CLASSIFICATION : **Types**: image_only, born_digital, hybrid
PDF_CLASSIFICATION : **Source**: classification/pdf_type_classifier.py (135 lines)
PDF_CLASSIFICATION : **Source**: classification/pdf_image_detector.py (194 lines)
PDF_CLASSIFICATION : **Source**: classification/pdf_text_extractor.py (122 lines)

PDF_CLASSIFICATION --> TEXT_GATE : Classification complete
PDF_CLASSIFICATION --> TEXT_GATE : Default to image_only (timeout)

state TEXT_GATE {
  [*] --> StrokeDensity
  StrokeDensity --> ConnectedComponents
  ConnectedComponents --> EdgeDensity
  EdgeDensity --> EnsembleVote
  EnsembleVote --> [*]
}
TEXT_GATE : **Entry**: Classification complete
TEXT_GATE : **Exit**: Text presence determined
TEXT_GATE : **Timeout**: 10s
TEXT_GATE : **Results**: NO_TEXT, TEXT_DETECTED
TEXT_GATE : **Performance**: <10ms/page, 99.5% precision
TEXT_GATE : **Source**: detection/text_gate.py (334 lines)

TEXT_GATE --> CLASSICAL_IQA : Gate complete
TEXT_GATE --> CLASSICAL_IQA : Default to TEXT_DETECTED (timeout)

state CLASSICAL_IQA {
  [*] --> HoughSkew
  HoughSkew --> LaplacianBlur
  LaplacianBlur --> HistogramContrast
  HistogramContrast --> NoiseDetection
  NoiseDetection --> IlluminationAnalysis
  IlluminationAnalysis --> JPEGBlockiness
  JPEGBlockiness --> BinarizationQuality
  BinarizationQuality --> BleedThrough
  BleedThrough --> [*]
}
CLASSICAL_IQA : **Entry**: Text gate complete
CLASSICAL_IQA : **Exit**: 8 classical detectors complete
CLASSICAL_IQA : **Timeout**: 30s
CLASSICAL_IQA : **Detectors**: skew, blur, contrast, noise, illumination, blockiness, binarization, bleed-through
CLASSICAL_IQA : **Source**: detection/iqa_classical.py (2,844 lines)
CLASSICAL_IQA : **Source**: detection/advanced_detectors.py (892 lines)

CLASSICAL_IQA --> LAYOUT_LITE : TEXT_DETECTED path
CLASSICAL_IQA --> MOBILENET_PRECORRECTION : NO_TEXT path
CLASSICAL_IQA --> MOBILENET_PRECORRECTION : Skip failed detectors (timeout)

state LAYOUT_LITE {
  [*] --> DoclingLayout
  DoclingLayout --> ColumnDetection
  ColumnDetection --> TableDetection
  TableDetection --> FigureDetection
  FigureDetection --> WatermarkDetection
  WatermarkDetection --> BackgroundAnalysis
  BackgroundAnalysis --> FuzzyScanDetection
  FuzzyScanDetection --> ComplexityScoring
  ComplexityScoring --> [*]
}
LAYOUT_LITE : **Entry**: TEXT_DETECTED + classical IQA complete
LAYOUT_LITE : **Exit**: Layout classification complete
LAYOUT_LITE : **Timeout**: 60s
LAYOUT_LITE : **Classes**: 11 DocLayNet classes
LAYOUT_LITE : **Source**: detection/doclayout_yolo.py (801 lines)
LAYOUT_LITE : **Source**: detection/layout_lite/analyzer.py (138 lines)
LAYOUT_LITE : **Source**: detection/layout_lite/*.py (1,808 lines total)

LAYOUT_LITE --> MOBILENET_PRECORRECTION : Layout complete
LAYOUT_LITE --> MOBILENET_PRECORRECTION : Skip layout (timeout)

state MOBILENET_PRECORRECTION {
  [*] --> DeviceSelection
  DeviceSelection --> LoadMobileNet : Device available
  LoadMobileNet --> OrientationHead
  OrientationHead --> SkewHead
  SkewHead --> ResolutionQualityHead
  ResolutionQualityHead --> [*]
  DeviceSelection --> [*] : All devices unavailable
}
MOBILENET_PRECORRECTION : **Entry**: IQA route determined
MOBILENET_PRECORRECTION : **Exit**: MobileNetV4-Conv-S inference complete (3 heads)
MOBILENET_PRECORRECTION : **Timeout**: 15s
MOBILENET_PRECORRECTION : **Model**: MobileNetV4-Conv-S, 3 heads (orientation, skew, resolution quality)
MOBILENET_PRECORRECTION : **Performance**: ~3ms (GPU), 8-12ms (CPU)
MOBILENET_PRECORRECTION : **Source**: detection/iqa_ml.py (1,303 lines)
MOBILENET_PRECORRECTION : **Source**: utils/device_probe.py (183 lines)

MOBILENET_PRECORRECTION --> PRE_CORRECTION : Inference complete
MOBILENET_PRECORRECTION --> CORRECTION : Fallback to classical only (timeout)

state PRE_CORRECTION {
  [*] --> ApplyOrientation
  ApplyOrientation --> ApplyDeskew
  ApplyDeskew --> ApplyResolutionFix
  ApplyResolutionFix --> [*]
}
PRE_CORRECTION : **Entry**: MobileNetV4 inference complete
PRE_CORRECTION : **Exit**: Orientation/skew/resolution corrections applied
PRE_CORRECTION : **Timeout**: 20s
PRE_CORRECTION : **Operations**: Orientation correction, deskew, resolution upscaling
PRE_CORRECTION : **Source**: correction/corrections.py (1,222 lines)

PRE_CORRECTION --> CONFIDENCE_CHECK : Pre-corrections applied
PRE_CORRECTION --> CONFIDENCE_CHECK : Skip pre-corrections (timeout)

state CONFIDENCE_CHECK {
  [*] --> EvaluateMobileNetHeads
  EvaluateMobileNetHeads --> EvaluateSigLIP2Heads
  EvaluateSigLIP2Heads --> PerHeadThresholdCheck
  PerHeadThresholdCheck --> [*]
}
CONFIDENCE_CHECK : **Entry**: Pre-correction complete
CONFIDENCE_CHECK : **Exit**: Per-head confidence evaluated across all model heads
CONFIDENCE_CHECK : **Timeout**: 5s
CONFIDENCE_CHECK : **Thresholds**: Orientation < 0.7, Skew < 0.6, Resolution < 0.5, IQA < 0.5, Script < 0.6, Handwriting < 0.5
CONFIDENCE_CHECK : **Source**: detection/discrepancy.py (786 lines)
CONFIDENCE_CHECK : **Source**: detection/hybrid_iqa.py (351 lines)

CONFIDENCE_CHECK --> SIGLIP2_ANALYSIS : All heads confident
CONFIDENCE_CHECK --> SIGLIP2_ANALYSIS : Some heads need SigLIP 2 analysis
CONFIDENCE_CHECK --> CLASSICAL_FALLBACK : Low confidence on specific heads
CONFIDENCE_CHECK --> CORRECTION : Skip evaluation (timeout)

state SIGLIP2_ANALYSIS {
  [*] --> DeviceSelection2
  DeviceSelection2 --> LoadSigLIP2 : Device available
  LoadSigLIP2 --> IQAGroup
  IQAGroup --> ScriptGroup
  ScriptGroup --> OrientationSkewGroup
  OrientationSkewGroup --> HandwritingGroup
  HandwritingGroup --> PageAttrsGroup
  PageAttrsGroup --> [*]
  DeviceSelection2 --> [*] : All devices unavailable
}
SIGLIP2_ANALYSIS : **Entry**: Confidence check complete, multi-task analysis needed
SIGLIP2_ANALYSIS : **Exit**: SigLIP 2 NAFlex inference complete (16 heads, 5 groups)
SIGLIP2_ANALYSIS : **Timeout**: 200s
SIGLIP2_ANALYSIS : **Model**: SigLIP 2 NAFlex, 88M params, 16 heads across 5 groups
SIGLIP2_ANALYSIS : **Groups**: IQA, Script, Orientation+Skew, Handwriting, Page Attrs
SIGLIP2_ANALYSIS : **Performance**: ~50ms (GPU), ~150ms (CPU)
SIGLIP2_ANALYSIS : **Source**: detection/iqa_ml.py (1,303 lines)

SIGLIP2_ANALYSIS --> CONFIDENCE_CHECK : Inference complete, re-evaluate confidence
SIGLIP2_ANALYSIS --> CORRECTION : Use available predictions (timeout)

state CLASSICAL_FALLBACK {
  [*] --> CheckOrientationConf
  CheckOrientationConf --> HoughOrientation : conf < 0.7
  CheckOrientationConf --> CheckSkewConf : conf >= 0.7
  HoughOrientation --> CheckSkewConf
  CheckSkewConf --> HoughSkew : conf < 0.6
  CheckSkewConf --> CheckResolutionConf : conf >= 0.6
  HoughSkew --> CheckResolutionConf
  CheckResolutionConf --> DPICharHeight : conf < 0.5
  CheckResolutionConf --> CheckIQAConf : conf >= 0.5
  DPICharHeight --> CheckIQAConf
  CheckIQAConf --> ClassicalIQA : conf < 0.5
  CheckIQAConf --> CheckScriptConf : conf >= 0.5
  ClassicalIQA --> CheckScriptConf
  CheckScriptConf --> OpenLIDMapping : conf < 0.6
  CheckScriptConf --> CheckHandwritingConf : conf >= 0.6
  OpenLIDMapping --> CheckHandwritingConf
  CheckHandwritingConf --> StrokeAnalysis : conf < 0.5
  CheckHandwritingConf --> [*] : conf >= 0.5
  StrokeAnalysis --> [*]
}
CLASSICAL_FALLBACK : **Entry**: Head confidence below threshold
CLASSICAL_FALLBACK : **Exit**: Head-specific classical fallback applied
CLASSICAL_FALLBACK : **Timeout**: 30s
CLASSICAL_FALLBACK : **Rules**: 6 head-specific fallback methods
CLASSICAL_FALLBACK : **Source**: detection/iqa_classical.py (2,844 lines)
CLASSICAL_FALLBACK : **Source**: detection/orientation_detector.py (608 lines)

CLASSICAL_FALLBACK --> CORRECTION : Fallback complete
CLASSICAL_FALLBACK --> CORRECTION : Use available predictions (timeout)

state CORRECTION {
  [*] --> Deskew
  Deskew --> CLAHE
  CLAHE --> Sharpening
  Sharpening --> Denoising
  Denoising --> TransformHistory
  TransformHistory --> [*]
}
CORRECTION : **Entry**: IQA complete
CORRECTION : **Exit**: Corrections applied
CORRECTION : **Timeout**: 50s
CORRECTION : **Operations**: Deskew, CLAHE, Sharpen, Denoise
CORRECTION : **Source**: correction/corrections.py (1,222 lines)

CORRECTION --> DQS_CALCULATION : Corrections complete
CORRECTION --> DQS_CALCULATION : Skip corrections (timeout)

state DQS_CALCULATION {
  [*] --> DegradationScore
  DegradationScore --> ComplexityScore
  ComplexityScore --> WeightedSum
  WeightedSum --> [*]
}
DQS_CALCULATION : **Entry**: Corrections complete
DQS_CALCULATION : **Exit**: Document Quality Score computed
DQS_CALCULATION : **Timeout**: 10s
DQS_CALCULATION : **Formula**: DQS = w1×degradation + w2×complexity
DQS_CALCULATION : **Source**: metrics/dqs_calculator.py (1,369 lines)

DQS_CALCULATION --> ROUTING : DQS computed
DQS_CALCULATION --> ROUTING : Default DQS=0.5 (timeout)

state ROUTING {
  [*] --> AnalyzeDQS
  AnalyzeDQS --> ConsiderPDFType
  ConsiderPDFType --> ConsiderComplexity
  ConsiderComplexity --> SelectStrategy
  SelectStrategy --> [*]
}
ROUTING : **Entry**: DQS computed
ROUTING : **Exit**: Routing recommendation generated
ROUTING : **Timeout**: 5s
ROUTING : **Strategies**: OCR_FAST, OCR_ADVANCED, VISION_SIMPLE, VISION_STRUCTURED
ROUTING : **Source**: routing/recommendation_engine.py (140 lines)

ROUTING --> OUTPUT : Routing complete
ROUTING --> OUTPUT : Default to OCR_ADVANCED (timeout)

state OUTPUT {
  [*] --> SerializeMetadata
  SerializeMetadata --> WriteImages
  WriteImages --> UploadToGCS
  UploadToGCS --> [*]
}
OUTPUT : **Entry**: Routing complete
OUTPUT : **Exit**: JSON + images serialized
OUTPUT : **Timeout**: 10s
OUTPUT : **Format**: DocumentMetadata.json + PNG images
OUTPUT : **Source**: output/json_generator.py (486 lines)

OUTPUT --> [*] : Success
OUTPUT --> PARTIAL_SUCCESS : < 50% pages failed
OUTPUT --> FAILED : > 50% pages failed OR critical error

state PARTIAL_SUCCESS {
}
PARTIAL_SUCCESS : **Status**: Document completed with failures
PARTIAL_SUCCESS : **Threshold**: 10-50% pages failed
PARTIAL_SUCCESS : **Action**: Flag failed pages in metadata

state FAILED {
}
FAILED : **Status**: Document processing failed
FAILED : **Reasons**: Corrupted file, > 50% pages failed, critical error
FAILED : **Action**: Return error metadata, alert

@enduml
```

### Mermaid Alternative (GitHub-Native Rendering)

For easier viewing in GitHub, here's a simplified Mermaid version of the state machine:

```mermaid
stateDiagram-v2
    [*] --> INGESTION

    INGESTION --> PREFLIGHT : Pages extracted
    INGESTION --> FAILED : Corrupted file

    PREFLIGHT --> PDF_CLASSIFICATION : Analysis complete

    PDF_CLASSIFICATION --> TEXT_GATE : Type determined

    TEXT_GATE --> CLASSICAL_IQA : Gate complete

    CLASSICAL_IQA --> LAYOUT_LITE : TEXT_DETECTED
    CLASSICAL_IQA --> MOBILENET_PRECORRECTION : NO_TEXT

    LAYOUT_LITE --> MOBILENET_PRECORRECTION : Layout complete

    MOBILENET_PRECORRECTION --> PRE_CORRECTION : Inference complete
    MOBILENET_PRECORRECTION --> CORRECTION : Timeout fallback

    PRE_CORRECTION --> CONFIDENCE_CHECK : Pre-corrections applied

    CONFIDENCE_CHECK --> SIGLIP2_ANALYSIS : Multi-task analysis needed
    CONFIDENCE_CHECK --> CLASSICAL_FALLBACK : Low confidence heads
    CONFIDENCE_CHECK --> CORRECTION : All heads confident

    SIGLIP2_ANALYSIS --> CORRECTION : Analysis complete

    CLASSICAL_FALLBACK --> CORRECTION : Fallback complete

    CORRECTION --> DQS_CALCULATION : Corrections applied

    DQS_CALCULATION --> ROUTING : DQS computed

    ROUTING --> OUTPUT : Recommendation generated

    OUTPUT --> [*] : Success
    OUTPUT --> PARTIAL_SUCCESS : 10-50% pages failed
    OUTPUT --> FAILED : >50% pages failed

    FAILED --> [*]
    PARTIAL_SUCCESS --> [*]

    note right of INGESTION
        Entry: PDF/image received
        Exit: 300 DPI pages
        Timeout: 30s
    end note

    note right of MOBILENET_PRECORRECTION
        MobileNetV4-Conv-S:
        3 heads, ~3ms GPU
        Orientation, Skew, Resolution
    end note

    note right of SIGLIP2_ANALYSIS
        SigLIP 2 NAFlex:
        16 heads, 5 groups, ~50ms GPU
        IQA, Script, Orient, Handwriting, PageAttrs
    end note

    note right of CLASSICAL_FALLBACK
        6 head-specific rules:
        Hough, DPI, OpenLID, stroke analysis
    end note
```

**Benefits of Mermaid**:

- ✅ Native GitHub rendering (no external tools needed)
- ✅ Simpler syntax for quick edits
- ✅ Better for code reviews and pull requests

**Note**: The PlantUML diagram above is more detailed and should be considered the canonical reference. The Mermaid version is a simplified alternative for quick viewing.

---

## State Transition Tables

### Happy Path: Text Detected, GPU Available

| State | Entry Condition | Exit Condition | Next State | Latency |
|-------|----------------|----------------|------------|---------|
| **INGESTION** | Document received | Pages extracted to 300 DPI | PREFLIGHT | 10-30s |
| **PREFLIGHT** | Pages extracted | DPI analyzed, upscaling complete | PDF_CLASSIFICATION | 5-15s |
| **PDF_CLASSIFICATION** | Preflight complete | PDF type determined | TEXT_GATE | 2-10s |
| **TEXT_GATE** | Classification complete | Text presence determined | CLASSICAL_IQA | <10ms |
| **CLASSICAL_IQA** | Text gate complete | 8 detectors complete | LAYOUT_LITE | 10-30s |
| **LAYOUT_LITE** | TEXT_DETECTED + IQA complete | Layout classification complete | MOBILENET_PRECORRECTION | 30-60s |
| **MOBILENET_PRECORRECTION** | Layout complete | MobileNetV4-Conv-S inference complete (3 heads) | PRE_CORRECTION | ~3ms (GPU), 8-12ms (CPU) |
| **PRE_CORRECTION** | MobileNetV4 complete | Orientation/skew/resolution corrections applied | CONFIDENCE_CHECK | 10-20ms |
| **CONFIDENCE_CHECK** | Pre-correction complete | Per-head confidence evaluated | SIGLIP2_ANALYSIS or CORRECTION | 1-5s |
| **SIGLIP2_ANALYSIS** | Multi-task analysis needed | SigLIP 2 NAFlex inference complete (16 heads) | CORRECTION | ~50ms (GPU), ~150ms (CPU) |
| **CORRECTION** | IQA complete | Corrections applied | DQS_CALCULATION | 20-50s |
| **DQS_CALCULATION** | Corrections complete | DQS computed | ROUTING | 5-10s |
| **ROUTING** | DQS computed | Routing recommendation generated | OUTPUT | 1-5s |
| **OUTPUT** | Routing complete | JSON + images serialized | SUCCESS | 5-10s |

**Total Happy Path Latency**: 100-150ms/page (GPU)

---

### Error Recovery Path 1: Low Confidence → Classical Fallback

| State | Entry Condition | Exit Condition | Next State | Recovery Action |
|-------|----------------|----------------|------------|-----------------|
| **MOBILENET_PRECORRECTION** | IQA route determined | Inference complete, some heads low confidence | PRE_CORRECTION | Log warning, flag low-confidence heads |
| **PRE_CORRECTION** | MobileNetV4 complete | Pre-corrections applied where confident | CONFIDENCE_CHECK | Apply corrections only from confident heads |
| **CONFIDENCE_CHECK** | Pre-correction complete | Low confidence on specific heads | CLASSICAL_FALLBACK | Route to head-specific classical methods |
| **CLASSICAL_FALLBACK** | Head confidence below threshold | Classical fallback complete | CORRECTION | Use classical result for low-confidence heads |

**Purpose**: Handle pages where model heads cannot confidently assess specific attributes

**Fallback Rate**: 5-15% of pages (per-head, varies by attribute)

---

### Error Recovery Path 2: Resource Exhaustion → Fallback Device

| State | Entry Condition | Exit Condition | Next State | Recovery Action |
|-------|----------------|----------------|------------|-----------------|
| **MOBILENET_PRECORRECTION** | Device selection | Local GPU unavailable | MOBILENET_PRECORRECTION | Try Modal GPU |
| **MOBILENET_PRECORRECTION** | Device selection | Modal GPU unavailable | MOBILENET_PRECORRECTION | Try CPU |
| **MOBILENET_PRECORRECTION** | Device selection | All devices unavailable | CORRECTION | Fallback to classical IQA only |

**Purpose**: Ensure processing continues even when preferred devices are unavailable

**Fallback Order**: Local GPU → Modal GPU → CPU → Classical Only

---

### Error Recovery Path 3: Partial Page Failure

| State | Entry Condition | Exit Condition | Next State | Recovery Action |
|-------|----------------|----------------|------------|-----------------|
| **INGESTION** | Processing page 42 | Page 42 corrupted | INGESTION | Skip page, continue with page 43 |
| **MOBILENET_PRECORRECTION** | Processing page 57 | Inference timeout | CONFIDENCE_CHECK | Use classical IQA prediction for page 57 |
| **OUTPUT** | All pages processed | 15% pages failed | PARTIAL_SUCCESS | Flag failed pages in metadata |

**Purpose**: Process as many pages as possible, isolate failures

**Thresholds**:

- **< 10% failed**: Continue, flag in metadata
- **10-50% failed**: Set status to `partial_success`
- **> 50% failed**: Abort, set status to `failed`

---

### Fallback Path: No Text Detected

| State | Entry Condition | Exit Condition | Next State | Difference from Happy Path |
|-------|----------------|----------------|------------|----------------------------|
| **TEXT_GATE** | Gate complete | NO_TEXT determined | CLASSICAL_IQA | Same |
| **CLASSICAL_IQA** | Text gate complete | 8 detectors complete | MOBILENET_PRECORRECTION | **Skip LAYOUT_LITE** |
| **MOBILENET_PRECORRECTION** | Classical complete | MobileNetV4 inference complete | PRE_CORRECTION | Same |
| **PRE_CORRECTION** | MobileNetV4 complete | Pre-corrections applied | CONFIDENCE_CHECK | Same |
| **CONFIDENCE_CHECK** | Pre-correction complete | Confidence evaluated | SIGLIP2_ANALYSIS or CORRECTION | Same |

**Purpose**: Optimize pipeline for pure images (scanned photos, diagrams) by skipping text-specific layout analysis

---

## Timeout Behavior

### Per-State Timeouts

| State | Timeout | Rationale | Fallback Action |
|-------|---------|-----------|-----------------|
| **INGESTION** | 30s | Large PDFs take time to extract | Abort document |
| **PREFLIGHT** | 15s | DPI analysis is fast, upscaling moderate | Skip upscaling, use original |
| **PDF_CLASSIFICATION** | 10s | Text extraction can be slow for large PDFs | Default to `image_only` |
| **TEXT_GATE** | 10s | Should be < 10ms, buffer for safety | Default to `TEXT_DETECTED` |
| **CLASSICAL_IQA** | 30s | 8 detectors, some computationally expensive | Skip failed detectors, continue |
| **LAYOUT_LITE** | 60s | Docling layout model inference can be slow on CPU | Skip layout, use text-gate-only routing |
| **MOBILENET_PRECORRECTION** | 15s | MobileNetV4-Conv-S is fast (~3ms GPU, 8-12ms CPU) | Fallback to classical only |
| **PRE_CORRECTION** | 20s | Apply orientation/skew/resolution corrections | Skip pre-corrections, flag in metadata |
| **CONFIDENCE_CHECK** | 5s | Per-head threshold evaluation | Skip SigLIP 2, use classical fallback |
| **SIGLIP2_ANALYSIS** | 200s | SigLIP 2 NAFlex 16-head inference (~50ms GPU, ~150ms CPU) | Use classical fallback for all heads |
| **CLASSICAL_FALLBACK** | 30s | Head-specific classical methods (Hough, DPI, OpenLID, stroke) | Use default values for failed heads |
| **CORRECTION** | 50s | Multiple CV operations per page | Skip corrections, flag in metadata |
| **DQS_CALCULATION** | 10s | Weighted sum calculation | Default DQS = 0.5 |
| **ROUTING** | 5s | Decision tree logic | Default to `OCR_ADVANCED` |
| **OUTPUT** | 10s | JSON serialization + GCS upload | Abort document |

### Total Pipeline Timeout

**Maximum**: 600s per document (10 minutes)

**Purpose**: Prevent infinite loops, resource exhaustion

**Behavior**:

- Track cumulative time across all states
- If total exceeds 600s, abort processing
- Return partial results with error metadata

---

## Timeout Escalation Logic

### First Timeout in Document

```python
def handle_first_timeout(state: str, page: int):
    logger.warning(
        "state_timeout",
        state=state,
        page=page,
        timeout_count=1,
        action="continue_with_fallback"
    )
    # Execute fallback action for the state
    apply_fallback(state, page)
    # Continue to next state
    return "continue"
```

### Second Timeout in Same Document

```python
def handle_second_timeout(state: str, page: int):
    logger.error(
        "repeated_state_timeout",
        state=state,
        page=page,
        timeout_count=2,
        action="increment_error_count"
    )
    # Increment error counter
    document_context.error_count += 1
    # Apply fallback and continue
    apply_fallback(state, page)
    return "continue"
```

### Third Timeout in Same Document

```python
def handle_third_timeout(state: str, page: int):
    logger.critical(
        "critical_timeout_threshold",
        state=state,
        page=page,
        timeout_count=3,
        action="abort_document"
    )
    # Abort processing
    document_context.status = "failed"
    document_context.error_reason = f"Multiple timeouts in {state}"
    # Return partial results
    return generate_partial_output(document_context)
```

---

## Error Handling Categories

### Category 1: Transient Errors

**Examples**:

- Network timeout connecting to Modal GPU
- Temporary file system unavailable
- Redis connection timeout

**Recovery Strategy**: Retry with exponential backoff (max 3 attempts)

**Implementation**:

```python
def retry_with_backoff(operation, max_retries=3):
    base_delay = 1.0
    for attempt in range(max_retries):
        try:
            return operation()
        except TransientError as e:
            if attempt < max_retries - 1:
                jitter = random.uniform(0.8, 1.2)  # ±20% jitter
                delay = base_delay * (2 ** attempt) * jitter
                logger.warning(
                    "transient_error_retry",
                    error=str(e),
                    attempt=attempt + 1,
                    delay_seconds=delay
                )
                time.sleep(delay)
            else:
                logger.error("transient_error_max_retries", error=str(e))
                raise
```

**Purpose of Jitter**: Prevents thundering herd when multiple workers retry simultaneously

---

### Category 2: Resource Errors

**Examples**:

- GPU out of memory (OOM)
- Modal budget exhausted
- CPU overload (> 90% utilization)

**Recovery Strategy**: Fallback to alternative device

**Implementation**:

```python
def handle_resource_error(error: ResourceError, context: ProcessingContext):
    if error.type == "GPU_OOM":
        logger.warning("gpu_oom_fallback", action="try_modal_gpu")
        return try_device("modal_gpu", context)
    elif error.type == "MODAL_BUDGET_EXHAUSTED":
        logger.warning("modal_budget_exhausted", action="try_cpu")
        return try_device("cpu", context)
    elif error.type == "CPU_OVERLOAD":
        logger.error("cpu_overload", action="throttle_and_retry")
        time.sleep(5)  # Back off
        return try_device("cpu", context)
    else:
        logger.error("unknown_resource_error", error=str(error))
        raise
```

---

### Category 3: Data Errors

**Examples**:

- Corrupted PDF page
- Invalid image format
- Missing required metadata

**Recovery Strategy**: Skip page/element, log for review

**Implementation**:

```python
def handle_data_error(error: DataError, page: int, context: ProcessingContext):
    logger.error(
        "data_error_skip_page",
        page=page,
        error=str(error),
        action="skip_and_continue"
    )
    # Add to failed pages list
    context.failed_pages.append({
        "page_number": page,
        "error_category": "DATA",
        "error_code": error.code,
        "error_message": str(error),
        "timestamp": datetime.utcnow().isoformat()
    })
    # Continue with next page
    return "continue"
```

---

### Category 4: Critical Errors

**Examples**:

- Model file missing or corrupted
- Configuration error (e.g., invalid DQS weights)
- Database connection failure

**Recovery Strategy**: Abort document, alert operations

**Implementation**:

```python
def handle_critical_error(error: CriticalError, context: ProcessingContext):
    logger.critical(
        "critical_error_abort",
        error=str(error),
        document_id=context.document_id,
        action="abort_and_alert"
    )
    # Set document status to failed
    context.status = "failed"
    context.error_reason = f"Critical: {error.code}"
    # Send alert to operations team
    send_alert(
        severity="critical",
        message=f"Document processing aborted: {error}",
        document_id=context.document_id
    )
    # Return error metadata
    return generate_error_output(context)
```

---

## Edge Cases

### Edge Case 1: Partial Page Failures

**Scenario**: 15 out of 100 pages fail processing

**Thresholds**:

- **< 10% pages failed**: `status: "success"`, flag failed pages
- **10-50% pages failed**: `status: "partial_success"`, flag failed pages
- **> 50% pages failed**: `status: "failed"`, abort processing

**Implementation**:

```python
def determine_document_status(context: ProcessingContext):
    total_pages = len(context.pages)
    failed_pages = len(context.failed_pages)
    failure_rate = failed_pages / total_pages if total_pages > 0 else 0

    if failure_rate == 0:
        return "success"
    elif failure_rate < 0.10:
        logger.info("minor_page_failures", failure_rate=failure_rate)
        return "success"
    elif failure_rate < 0.50:
        logger.warning("partial_success", failure_rate=failure_rate)
        return "partial_success"
    else:
        logger.error("majority_pages_failed", failure_rate=failure_rate)
        return "failed"
```

---

### Edge Case 2: Circuit Breaker Triggered

**Scenario**: Modal GPU has failed 5 consecutive requests

**Circuit Breaker States**:

- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Too many failures, block requests for 60s
- **HALF_OPEN**: After 60s, allow 1 test request

**Behavior**:

```python
def get_device_with_circuit_breaker(context: ProcessingContext):
    # Check if Modal GPU circuit breaker is OPEN
    if circuit_breaker.is_open("modal_gpu"):
        logger.warning(
            "circuit_breaker_open",
            service="modal_gpu",
            action="fallback_to_cpu"
        )
        return "cpu"

    # Try Modal GPU
    try:
        result = invoke_modal_gpu(context)
        circuit_breaker.record_success("modal_gpu")
        return result
    except Exception as e:
        circuit_breaker.record_failure("modal_gpu")
        logger.error("modal_gpu_failure", error=str(e))
        # Fallback to CPU
        return invoke_cpu(context)
```

**Configuration** (from [level-2/production-runtime/index.md:161-176](../../level-2/production-runtime/index.md#L161-L176)):

```python
CircuitBreakerConfig(
    failure_threshold=5,      # Open after 5 consecutive failures
    timeout_seconds=60,       # Stay open for 60s
    success_threshold=2       # Require 2 successes to close from HALF_OPEN
)
```

---

### Edge Case 3: Budget Exhausted

**Scenario**: Monthly Modal GPU budget ($30) exhausted mid-document

**Budget Tiers** (from [level-2/production-runtime/index.md:256-264](../../level-2/production-runtime/index.md#L256-L264)):

- **Per-document**: $0.05
- **Per-batch**: $5.00
- **Monthly**: $30.00

**Behavior**:

```python
def check_budget_before_modal_invocation(context: ProcessingContext):
    # Check budget availability
    if not budget_tracker.has_budget("modal_gpu"):
        logger.warning(
            "modal_budget_exhausted",
            monthly_spent=budget_tracker.get_monthly_spend(),
            monthly_limit=30.00,
            action="fallback_to_cpu"
        )
        # Update metrics
        metrics.increment("iqa_budget_exhaustion_total")
        # Fallback to CPU
        return "cpu"

    # Budget available, proceed with Modal GPU
    return "modal_gpu"
```

---

### Edge Case 4: All Devices Unavailable

**Scenario**: Local GPU OOM, Modal GPU budget exhausted, CPU overloaded

**Behavior**:

```python
def handle_all_devices_unavailable(context: ProcessingContext):
    logger.critical(
        "all_devices_unavailable",
        local_gpu="oom",
        modal_gpu="budget_exhausted",
        cpu="overloaded",
        action="fallback_to_classical_only"
    )

    # Fall back to classical IQA only (no ML inference)
    classical_results = run_classical_iqa_only(context)

    # Set degraded status
    context.processing_mode = "degraded"
    context.ml_iqa_skipped = True

    # Send alert
    send_alert(
        severity="warning",
        message="ML IQA unavailable, using classical only",
        document_id=context.document_id
    )

    return classical_results
```

---

## State-Specific Implementation Details

### INGESTION State

**Source Files**:

- [ingestion/document_processor.py:1-303](../../../../src/image_preprocessing_detector/ingestion/document_processor.py) - Entry point orchestrator
- [ingestion/pdf_loader.py:1-265](../../../../src/image_preprocessing_detector/ingestion/pdf_loader.py) - PyMuPDF PDF extraction
- [ingestion/image_loader.py:1-280](../../../../src/image_preprocessing_detector/ingestion/image_loader.py) - Pillow image loading

**Entry Condition**: PDF or image file received via API or CLI

**Exit Condition**: All pages extracted and normalized to 300 DPI

**Timeout**: 30 seconds

**Failure Modes**:

1. **Corrupted PDF**: Abort with `status: "failed"`, `error_code: "CORRUPTED_PDF"`
2. **Unsupported format**: Abort with `status: "failed"`, `error_code: "UNSUPPORTED_FORMAT"`
3. **Extraction timeout**: Abort with `status: "failed"`, `error_code: "INGESTION_TIMEOUT"`

---

### MOBILENET_PRECORRECTION State

**Source Files**:

- [detection/iqa_ml.py:1-1303](../../../../src/image_preprocessing_detector/detection/iqa_ml.py) - Inference orchestration
- [utils/device_probe.py:1-183](../../../../src/image_preprocessing_detector/utils/device_probe.py) - Device selection

**Entry Condition**: Classical IQA complete (and layout-lite if TEXT_DETECTED)

**Exit Condition**: MobileNetV4-Conv-S inference complete, 3-head predictions available (orientation, skew, resolution quality)

**Timeout**: 15 seconds

**Device Selection Algorithm**:

```python
def select_device_for_mobilenet_inference():
    # Priority 1: Local GPU (~3ms)
    if device_probe.has_local_gpu() and device_probe.get_gpu_memory() > 500_000_000:
        return "local_gpu"

    # Priority 2: Modal GPU (~5ms including network)
    if budget_tracker.has_budget("modal_gpu"):
        return "modal_gpu"

    # Priority 3: CPU (8-12ms)
    if policy.allow_cpu:
        return "cpu"

    # No devices available
    raise NoDeviceAvailableError("All devices unavailable")
```

**Performance Targets**:

- Local GPU: ~3ms/page
- Modal GPU: ~5ms/page (including network latency)
- CPU: 8-12ms/page

### SIGLIP2_ANALYSIS State

**Source Files**:

- [detection/iqa_ml.py:1-1303](../../../../src/image_preprocessing_detector/detection/iqa_ml.py) - Multi-task inference orchestration

**Entry Condition**: Confidence check indicates multi-task analysis is needed

**Exit Condition**: SigLIP 2 NAFlex inference complete, 16-head predictions across 5 groups available

**Timeout**: 200 seconds

**Model Characteristics**:

- Architecture: SigLIP 2 NAFlex (88M params)
- Heads: 16 across 5 groups (IQA, Script, Orientation+Skew, Handwriting, Page Attrs)
- Performance: ~50ms (GPU), ~150ms (CPU)
- Memory: ~2GB GPU VRAM

### CLASSICAL_FALLBACK State

**Source Files**:

- [detection/iqa_classical.py:1-2844](../../../../src/image_preprocessing_detector/detection/iqa_classical.py) - Classical IQA detectors
- [detection/orientation_detector.py:1-608](../../../../src/image_preprocessing_detector/detection/orientation_detector.py) - Hough-based orientation

**Entry Condition**: Head confidence below threshold for one or more heads

**Exit Condition**: Classical fallback applied for all low-confidence heads

**Timeout**: 30 seconds

**Fallback Rules**:

| Head/Group | Threshold | Fallback Method |
|-----------|-----------|-----------------|
| Orientation (MobileNetV4) | < 0.7 | Hough line-based orientation detection |
| Skew (MobileNetV4) | < 0.6 | Classical Hough skew estimation |
| Resolution Quality (MobileNetV4) | < 0.5 | DPI metadata + connected component char height |
| IQA (SigLIP 2 Group 1) | < 0.5 | Classical IQA detectors (iqa_classical.py) |
| Script Detection (SigLIP 2 Group 2) | < 0.6 | OpenLID language -> script mapping |
| Handwriting (SigLIP 2 Group 4) | < 0.5 | Connected component stroke analysis |

---

## Telemetry and Monitoring

### Prometheus Metrics

**State Transition Tracking**:

```python
# Counter: Total state transitions
iqa_state_transitions_total{from_state, to_state}

# Histogram: Time spent in each state
iqa_state_duration_seconds{state}

# Gauge: Current processing state per worker
iqa_current_state{worker_id, state}
```

**Error Tracking**:

```python
# Counter: Errors by category
iqa_errors_total{error_code, category}

# Counter: Retry attempts
iqa_retry_attempts_total{reason}

# Gauge: Circuit breaker state
iqa_circuit_breaker_state{service}  # 0=closed, 1=open, 2=half_open
```

**Performance Metrics**:

```python
# Histogram: End-to-end latency per document
iqa_document_processing_duration_seconds

# Histogram: Latency per page
iqa_page_processing_duration_seconds{device}

# Counter: Pages processed
iqa_pages_processed_total{status}  # status: success, failed, skipped
```

---

### Structured Logging

**State Transition Logs**:

```python
logger.info(
    "state_transition",
    from_state="CLASSICAL_IQA",
    to_state="MOBILENET_PRECORRECTION",
    page_number=42,
    duration_ms=25.3,
    trace_id=trace_id
)
```

**Timeout Logs**:

```python
logger.warning(
    "state_timeout",
    state="MOBILENET_PRECORRECTION",
    page_number=57,
    timeout_seconds=100,
    elapsed_seconds=105.2,
    action="fallback_to_classical",
    trace_id=trace_id
)
```

**Error Logs**:

```python
logger.error(
    "state_error",
    state="INGESTION",
    error_code="CORRUPTED_PDF",
    error_message="Failed to decode PDF stream",
    page_number=12,
    action="abort_document",
    trace_id=trace_id
)
```

---

## Related Documentation

- [Level 2: Production Runtime Overview](../../level-2/production-runtime/index.md)
- [Level 3: Device Orchestrator](device-orchestrator.md)
- [Level 3: Production Runtime Swimlane](production-runtime-swimlane.puml)
- [Source File Inventory](../../FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md#ws1-production-runtime)

---

*Last Updated: 2026-02-09*
*Total States: 16 | Happy Path: 150ms/page (GPU) | Maximum Timeout: 600s*
