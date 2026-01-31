# Stream 1 Schema Migration Guide

**Version**: 1.0.0
**Date**: 2026-01-29
**Status**: Active

---

## Overview

Stream 1 introduces significant schema extensions to support the three-tier script detection
architecture and enhanced routing capabilities. This guide helps downstream consumers migrate
to the new schema.

## Breaking Changes

### 1. LanguageInfo.script Type Change

**Before (pre-Stream 1):**

```python
class LanguageInfo(BaseModel):
    script: str  # Free-form string like "Latin", "CJK"
    confidence: float
```

**After (Stream 1):**

```python
class LanguageInfo(BaseModel):
    script: ISO15924Script  # Typed enum
    confidence: float
    language_code: str | None  # NEW: Optional ISO 639 code
```

**Migration:**

```python
# Old way - no longer works
lang = LanguageInfo(script="Latin", confidence=0.95)

# New way - use enum
from image_preprocessing_detector.schema_utils.iso_language_script import ISO15924Script
lang = LanguageInfo(script=ISO15924Script.LATN, confidence=0.95)

# Or use the from_legacy helper
lang = LanguageInfo.from_legacy("Latin", confidence=0.95)

# Access string value via property
print(lang.script_str)  # "Latn"
```

## New Optional Fields

The following fields are **optional** and backward-compatible. Existing code will continue
to work without modification.

### DocumentMetadata Extensions

| Field | Type | Description |
|-------|------|-------------|
| `capture_method` | `CaptureMethod \| None` | How document was captured |
| `capture_method_confidence` | `float \| None` | Confidence in capture method |
| `script_detection` | `DocumentScriptDetection \| None` | Full script detection |
| `text_layer_quality` | `float \| None` | PDF text layer quality (0-1) |
| `text_layer_skip_ocr` | `bool` | True if text layer good enough |
| `degradation_severity` | `Literal["simple", "complex"]` | Degradation classification |
| `docling_params` | `DoclingRoutingParams \| None` | Generated Docling CLI params |
| `recommended_psm` | `int \| None` | Tesseract PSM recommendation |
| `vlm_escalation_reasons` | `list[str]` | Why VLM was recommended |

### PageLayoutSummary Extensions

| Field | Type | Description |
|-------|------|-------------|
| `has_shadows` | `bool` | Shadow artifacts detected |
| `shadow_score` | `float` | Shadow severity (0-1) |
| `shadow_severity` | `Literal["none", "mild", "moderate", "severe"]` | Categorical severity |
| `has_warping` | `bool` | Warping detected |
| `warping_score` | `float` | Warping severity (0-1) |
| `warping_type` | `str \| None` | Type: barrel, pincushion, etc. |
| `has_code` | `bool` | Code blocks detected |
| `code_confidence` | `float` | Code detection confidence |
| `table_complexity` | `TableComplexity \| None` | Table structure complexity |
| `handwriting_score` | `float` | Handwriting presence (0-1) |
| `orientation_angle` | `int` | Detected orientation (0, 90, 180, 270) |
| `orientation_confidence` | `float` | Orientation detection confidence |
| `orientation_corrected` | `bool` | Whether correction was applied |
| `degradations` | `list[str]` | Degradation types detected |

## New Models

### ScriptDetectionResult

Stores individual script detection with full ISO 15924 granularity:

```python
from image_preprocessing_detector.schema import ScriptDetectionResult

# Create from detection
result = ScriptDetectionResult(
    detected_script="Latn",  # Exact ISO 15924 code
    confidence=0.95,
    detection_method="siglip2_multitask",
    script_probabilities={"Latn": 0.95, "Cyrl": 0.03, "Grek": 0.02},
)

# Create from legacy label
result = ScriptDetectionResult.from_source_label("Latin", confidence=1.0)

# Create unknown result
result = ScriptDetectionResult.unknown(reason="no_text_detected")
```

### DocumentScriptDetection

Aggregates script detections for multi-script documents:

```python
from image_preprocessing_detector.schema import (
    DocumentScriptDetection,
    ScriptDetectionResult,
)

instances = [
    ScriptDetectionResult(detected_script="Latn", confidence=0.95, detection_method="heuristic"),
    ScriptDetectionResult(detected_script="Hans", confidence=0.88, detection_method="heuristic"),
]

detection = DocumentScriptDetection.from_instances(instances)
print(detection.dominant_script)  # "Latn"
print(detection.is_multilingual)  # True
print(detection.unique_scripts)   # ["Latn", "Hans"]
```

### DoclingRoutingParams

Generates Docling CLI arguments:

```python
from image_preprocessing_detector.schema import DoclingRoutingParams

params = DoclingRoutingParams(
    pipeline="vlm",
    vlm_model="deepseekocr_ollama",
    ocr_enabled=False,
    table_mode="accurate",
)

# Generate CLI args
cli_args = params.to_cli_args()
# ["--pipeline=vlm", "--vlm-model=deepseekocr_ollama", "--no-ocr", ...]

# Export as YAML
yaml_str = params.to_yaml()
```

### TableComplexity

Table structure complexity indicators:

```python
from image_preprocessing_detector.schema import TableComplexity

tc = TableComplexity(
    has_borders=True,
    estimated_rows=10,
    estimated_columns=5,
    has_merged_cells=True,
    complexity_score=0.75,
)
```

## Three-Tier Script Architecture

Stream 1 introduces a three-tier architecture for script handling:

### Tier 1: Storage (Full ISO 15924)

Store exact ISO 15924 codes. Never aggregate at storage level.

```python
# Store "Gujr" not "Deva" for Gujarati
result = ScriptDetectionResult(
    detected_script="Gujr",  # Exact code
    confidence=0.90,
    detection_method="heuristic",
)
```

### Tier 2: ML Training Classes

Group scripts into tractable training classes via config:

```python
from image_preprocessing_detector.schema_utils import ScriptMLMapping

mapping = ScriptMLMapping()  # Loads config/script_ml_classes.yaml

# Gujarati maps to INDIC_OTHER for training
ml_class = mapping.to_ml_class("Gujr")  # "INDIC_OTHER"

# Latin stays as LATN
ml_class = mapping.to_ml_class("Latn")  # "LATN"
```

### Tier 3: OCR Engine Routing

Route scripts to OCR engines via config:

```python
from image_preprocessing_detector.routing import ScriptRouter
from image_preprocessing_detector.schema_utils import ScriptMLMapping

mapping = ScriptMLMapping()
router = ScriptRouter(mapping)

# Get engine config
config = router.get_engine_config("Hans")
# {"engine": "paddleocr", "batch_size": 2, "lang_hint": "ch"}

# Check VLM escalation
should_escalate = router.should_escalate_to_vlm("Tibt", confidence=0.4)
```

## Configuration Files

Two new config files control Tier 2 and Tier 3:

### config/script_ml_classes.yaml

Maps ISO 15924 codes to ML training classes:

```yaml
iso15924_to_ml_class:
  Latn: LATN
  Gujr: INDIC_OTHER
  Hans: HANS
  # ...

unmapped_default: OTHER
```

### config/script_routing.yaml

Maps scripts to OCR engines:

```yaml
routing_rules:
  LATN:
    engine: "rapidocr"
    batch_size: 8
  HANS:
    engine: "paddleocr"
    batch_size: 2
    lang_hint: "ch"
  # ...

vlm_escalation:
  confidence_threshold: 0.5
  always_escalate:
    - "Tibt"
    - "Ethi"
```

## Hot Reload

Both mapping and routing support hot reload:

```python
# Reload after config change
mapping.reload()
router.reload()
```

## Backward Compatibility

All new fields have sensible defaults. Existing code that doesn't use the new
fields will continue to work unchanged.

```python
# This still works exactly as before
metadata = DocumentMetadata(
    document_id="doc_001",
    file_name="sample.pdf",
    source_mime="application/pdf",
    num_pages=1,
    processing_version=ProcessingVersion(pipeline_version="0.1.0"),
    pages=[...],
)
# All new fields default to None or empty lists
```

## Annotation Parser Alignment (Extended Stream 1)

The annotation parsers have been aligned with the three-tier script architecture.

### OriginalLabels.iso15924_script_code Field

A new field `iso15924_script_code` has been added to `OriginalLabels` for standardized script storage:

```python
from image_preprocessing_detector.annotation.schemas.immutable import OriginalLabels

labels = OriginalLabels()
labels.script_name = "Arabic"           # Human-readable name (unchanged)
labels.iso15924_script_code = "Arab"    # NEW: Standardized ISO 15924 code
```

**Updated Parsers**:

The following multilingual/handwriting parsers now populate `iso15924_script_code`:

| Parser | Script Code | Human Name |
|--------|-------------|------------|
| `Mlt19Parser` | Dynamic (Arab, Deva, etc.) | Dynamic |
| `ArabicDocsParser` | `Arab` | Arabic |
| `TibhcrParser` | `Tibt` | Tibetan |
| `NepaliHandwrittenParser` | `Deva` | Devanagari |
| `YarmoukParser` | `Arab` | Arabic |
| `CvsiParser` | Dynamic (10 scripts) | Dynamic |
| `Siw13Parser` | Dynamic (13 scripts) | Dynamic |
| `Mle2eParser` | Dynamic (4 scripts) | Dynamic |
| `CcOcrParser` | `Hans` | Chinese |
| `Mdiw13Parser` | Dynamic (13 scripts) | Dynamic |
| `HindiOcrSyntheticParser` | `Deva` | Devanagari |
| `PucitOhulParser` | `Arab` | Arabic |
| `MultilingualScriptsParser` | Dynamic | Dynamic |

### Validation Helpers

New validation helpers ensure ISO 15924 code correctness:

```python
from image_preprocessing_detector.schema_utils import (
    is_valid_iso15924_code,
    get_iso15924_script,
    validate_script_code_for_ml,
)

# Check if code is valid
is_valid_iso15924_code("Latn")  # True
is_valid_iso15924_code("INVALID")  # False

# Get typed enum from code
script = get_iso15924_script("Latn")  # ISO15924Script.LATN

# Validate with suggestions for fixing
validate_script_code_for_ml("latin")  # (False, "Try 'Latn' (normalized from 'latin')")
validate_script_code_for_ml("LATN")   # (False, "Case mismatch: use 'Latn' not 'LATN'")
```

### DatasetInfo Validation

The `DatasetInfo` template now validates ISO 15924 codes:

```python
from image_preprocessing_detector.annotation.parsers.template import (
    DatasetInfo,
    validate_dataset_info,
)

# Check individual dataset info
info = DatasetInfo(dataset_name="my-dataset", iso15924_script="arabic")
is_valid, message = info.validate_script_code()
# (False, "Try 'Arab' (normalized from 'arabic')")

# Full validation includes script check
warnings = validate_dataset_info(info)
# [..., "WARNING: iso15924_script invalid - Try 'Arab' (normalized from 'arabic')"]
```

## Import Changes

New exports available:

```python
# From schema.py
from image_preprocessing_detector.schema import (
    # New models
    ScriptDetectionResult,
    DocumentScriptDetection,
    TableComplexity,
    DoclingRoutingParams,
    # Bridged enums (re-exported)
    CaptureMethod,
    ISO15924Script,
    ScriptFamily,
)

# From schema_utils
from image_preprocessing_detector.schema_utils import (
    ScriptMLMapping,
    get_default_mapping,
    reset_default_mapping,
)

# From routing
from image_preprocessing_detector.routing import (
    ScriptRouter,
    get_default_router,
    reset_default_router,
)
```

## Testing

Run Stream 1 tests:

```bash
uv run pytest tests/unit/test_schema_stream1.py tests/unit/test_script_routing.py -v
```

---

## Questions?

See:

- [STREAM_1_SCHEMA_ANALYSIS.md](../planning/STREAM_1_SCHEMA_ANALYSIS.md) - Design rationale
- [PHASE_10_11_RESTRUCTURED_PLAN.md](../planning/PHASE_10_11_RESTRUCTURED_PLAN.md) - Full plan

---

**End of Migration Guide**
