# Stream 1: Schema Analysis & Design

**Date**: 2026-01-29
**Status**: Draft for Review
**Purpose**: Deep analysis of existing schema infrastructure to inform Stream 1 work

---

## Executive Summary

This analysis reveals that **significant infrastructure already exists** that was not reflected in the initial restructured plan. The main issues are:

1. **Fields exist but in the wrong location** - `CaptureMethod`, ISO 15924 scripts, etc. exist in `annotation/schemas/` but not in main `schema.py`
2. **Type mismatches** - Main schema uses free-form strings where typed enums exist
3. **Binary vs continuous labels** - Need to ensure ML training uses continuous scores

**Key Finding**: We need to **bridge** existing infrastructure to main schema, not duplicate it.

---

## Part 1: Existing Schema Inventory

### 1.1 What Already Exists ✅

| Feature | Location | Type | Notes |
|---------|----------|------|-------|
| **Document Source** | `annotation/schemas/enums.py` | `CaptureMethod` enum | 7 values including `UNKNOWN` |
| **PDF Type** | `schema.py` | `PDFType` enum | `IMAGE_ONLY`, `BORN_DIGITAL`, `HYBRID` |
| **ISO 15924 Scripts** | `schema_utils/iso_language_script.py` | `ISO15924Script` enum | 30+ scripts with `ZZZZ` for unknown |
| **Script Families** | `schema_utils/iso_language_script.py` | `ScriptFamily` enum | `LATIN`, `CJK`, `ARABIC`, `INDIC`, `CYRILLIC`, `OTHER` |
| **Language Tags** | `schema_utils/iso_language_script.py` | `LanguageScriptTag` dataclass | BCP 47 compliant |
| **Language Info** | `schema.py` | `LanguageInfo` model | Has `script: str` (needs typing) |
| **Orientation** | `schema.py` | `OrientationDetection` model | Complete with confidence |
| **DQS** | `schema.py` | `DQSMetadata` model | Continuous 0-1 scores ✅ |
| **IQA Scores** | `schema.py` | `PageMetadata.ml_iqa` | Continuous scores per metric ✅ |

### 1.2 CaptureMethod vs PDFType - NOT THE SAME

Your intuition was correct - there IS overlap, but they serve different purposes:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Document Classification                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  PDFType (Content Structure)         CaptureMethod (Physical Origin)     │
│  ──────────────────────────         ────────────────────────────────     │
│  • BORN_DIGITAL: Created in         • BORN_DIGITAL: Native creation      │
│    software (has text layer)        • SCANNER_FLATBED: Flatbed scan      │
│  • IMAGE_ONLY: No text layer        • SCANNER_ADF: Feeder scan           │
│  • HYBRID: Mixed pages              • CAMERA_PROFESSIONAL: Pro camera    │
│                                     • CAMERA_SMARTPHONE: Phone camera    │
│                                     • FAX: Fax transmission              │
│                                     • UNKNOWN                             │
│                                                                          │
│  Used for: Text extraction          Used for: Degradation prediction     │
│            routing decisions                   correction selection      │
│                                               DocRes escalation          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Example**: A scanned PDF (`PDFType.IMAGE_ONLY`) could be from a flatbed scanner (`CaptureMethod.SCANNER_FLATBED`) or a smartphone (`CaptureMethod.CAMERA_SMARTPHONE`) - these have very different quality characteristics.

**Recommendation**: Keep both. They encode different information.

### 1.3 Existing ISO 15924 Script Enum

The `ISO15924Script` enum already has 30+ scripts:

```python
# From schema_utils/iso_language_script.py

class ISO15924Script(str, Enum):
    # Latin-derived
    LATN = "Latn"  # Latin

    # CJK
    HANS = "Hans"  # Han (Simplified)
    HANT = "Hant"  # Han (Traditional)
    JPAN = "Jpan"  # Japanese (Han + Hiragana + Katakana)
    KORE = "Kore"  # Korean (Hangul + Han)
    HANI = "Hani"  # Han (generic)

    # South Asian (10 scripts)
    DEVA = "Deva"  # Devanagari
    BENG = "Beng"  # Bengali
    TAML = "Taml"  # Tamil
    TELU = "Telu"  # Telugu
    GUJR = "Gujr"  # Gujarati
    KNDA = "Knda"  # Kannada
    MLYM = "Mlym"  # Malayalam
    ORYA = "Orya"  # Odia
    SINH = "Sinh"  # Sinhala
    GURU = "Guru"  # Gurmukhi

    # Southeast Asian
    THAI = "Thai"  # Thai
    KHMR = "Khmr"  # Khmer
    MYMR = "Mymr"  # Myanmar
    LAOO = "Laoo"  # Lao
    TIBT = "Tibt"  # Tibetan

    # Middle Eastern
    ARAB = "Arab"  # Arabic
    HEBR = "Hebr"  # Hebrew

    # European
    CYRL = "Cyrl"  # Cyrillic
    GREK = "Grek"  # Greek
    ARMN = "Armn"  # Armenian
    GEOR = "Geor"  # Georgian

    # Other
    ETHI = "Ethi"  # Ethiopic
    HANG = "Hang"  # Hangul
    HIRA = "Hira"  # Hiragana
    KANA = "Kana"  # Katakana

    # Special
    ZYYY = "Zyyy"  # Common (punctuation, numbers)
    ZINH = "Zinh"  # Inherited
    ZZZZ = "Zzzz"  # Unknown/Undetermined
```

**The 10-class ML list** (`SCRIPT_DETECTION_CLASSES`) is a subset for training:

```python
SCRIPT_DETECTION_CLASSES = [
    "Latn", "Cyrl", "Arab", "Deva", "Hans", "Hant", "Jpan", "Kore", "Thai", "Tibt"
]
```

---

## Part 2: Issues to Address

### 2.1 Problem: LanguageInfo Uses Free-Form String

**Current** (in `schema.py`):

```python
class LanguageInfo(BaseModel):
    script: str = Field(...)  # Free-form string!
    confidence: float = Field(...)
```

**Required**:

```python
class LanguageInfo(BaseModel):
    script: ISO15924Script = Field(...)  # Typed enum
    confidence: float = Field(...)
```

### 2.2 Problem: CaptureMethod Not in Main Schema

`CaptureMethod` exists in `annotation/schemas/enums.py` but `DocumentMetadata` doesn't use it.

**Required**: Add to `DocumentMetadata`:

```python
class DocumentMetadata(BaseModel):
    # ... existing fields ...
    capture_method: CaptureMethod | None = Field(None)
    capture_method_confidence: float | None = Field(None, ge=0.0, le=1.0)
```

### 2.3 Problem: Binary vs Continuous Labels

The user correctly identified that binary labels caused training issues with ResNet-50 teacher.

**Current IQA schema** (correctly uses continuous):

```python
PageMetadata.ml_iqa = {
    "blur_score": 0.82,        # Continuous ✅
    "noise_score": 0.78,       # Continuous ✅
    "contrast_score": 0.85,    # Continuous ✅
    # ...
}
```

**Script detection needs the same pattern**:

```python
# BAD: Binary/discrete
script_type: ISO15924Script  # Just the class - no confidence distribution

# GOOD: Continuous with distribution
script_detection: ScriptDetectionResult = {
    "primary_script": "Latn",
    "primary_confidence": 0.92,
    "script_probabilities": {
        "Latn": 0.92,
        "Cyrl": 0.05,
        "Grek": 0.02,
        "Zzzz": 0.01,
    },
    "detection_method": "siglip2_multitask",
}
```

---

## Part 3: Script Detection Design

### 3.1 Three-Tier Script Architecture

**Design Principle**: Preserve maximum source granularity. We don't know which scripts need which engines until after testing, so we should never lose detail.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                 Three-Tier Script Detection Architecture                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  TIER 1: Storage Layer (Full ISO 15924)                                  │
│  ──────────────────────────────────────                                  │
│  • Store EXACT script code from source data                              │
│  • 200+ possible values (full ISO 15924 standard)                        │
│  • NEVER lose source granularity                                         │
│  • Examples: "Gujr", "Knda", "Mlym", "Orya" (not just "Deva")            │
│  • Unknown scripts: "Zzzz" with original source note                     │
│                                                                          │
│  TIER 2: ML Training Layer (Grouped Classes)                             │
│  ───────────────────────────────────────────                             │
│  • Aggregated classes for tractable model training                       │
│  • ~15-20 classes (can expand as training data allows)                   │
│  • Mapping: ISO 15924 → ML Class (configurable)                          │
│  • "OTHER" bucket for scripts without dedicated training                 │
│                                                                          │
│  TIER 3: Routing Layer (Engine Groups)                                   │
│  ─────────────────────────────────────                                   │
│  • Groups scripts by OCR engine recommendation                           │
│  • FULLY CONFIGURABLE - update after testing!                            │
│  • Same ML class might route to different engines                        │
│  • Examples: "rapidocr_group", "paddleocr_cjk", "tesseract_rtl"          │
│                                                                          │
│  Data Flow:                                                              │
│  ──────────                                                              │
│  Source Data → [Tier 1: Store "Gujr"]                                    │
│                     ↓                                                    │
│             [Tier 2: Map to "INDIC_OTHER" for training]                  │
│                     ↓                                                    │
│             [Tier 3: Route to "paddleocr" based on config]               │
│                                                                          │
│  Key: Tier 2 and 3 mappings are CONFIG, not code!                        │
│       Can be updated based on testing without code changes.              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Tier 1: Full ISO 15924 Storage

**Principle**: Store the exact script code from source data. Never aggregate at storage.

```python
# schema.py - Storage model

class ScriptInstance(BaseModel):
    """Single script detection instance - stores FULL ISO 15924 code."""

    # ALWAYS store the exact ISO 15924 code - never aggregate here
    iso15924_code: str = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Exact ISO 15924 4-letter code (e.g., 'Gujr', not 'Deva')"
    )

    # Confidence in this specific detection
    confidence: float = Field(..., ge=0.0, le=1.0)

    # Where did this label come from?
    source: str = Field(
        ...,
        description="Label source: 'dataset_ground_truth', 'vlm_pseudo', 'model_inference', 'ocr_detected'"
    )

    # Original source detail (preserve for debugging)
    source_detail: str | None = Field(
        None,
        description="Original label from source (e.g., 'Gujarati', 'ગુજરાતી')"
    )

    # Bounding box if script is localized (for mixed-script docs)
    bbox: list[int] | None = Field(
        None,
        description="Region where this script was detected [x, y, w, h]"
    )
```

### 3.3 Tier 2: ML Training Classes (Configurable)

**Principle**: Group scripts for tractable training. Mapping is CONFIG, not code.

```yaml
# config/script_ml_classes.yaml
# This mapping can be updated without code changes!

version: "1.0.0"
description: "ISO 15924 to ML training class mapping"

# ML classes we train on (expand as training data allows)
ml_classes:
  - LATN       # Latin-based scripts
  - CYRL       # Cyrillic
  - GREK       # Greek
  - ARAB       # Arabic script family
  - HEBR       # Hebrew
  - DEVA       # Devanagari
  - BENG       # Bengali
  - TAML       # Tamil
  - TELU       # Telugu
  - HANS       # Simplified Chinese
  - HANT       # Traditional Chinese
  - JPAN       # Japanese
  - KORE       # Korean
  - THAI       # Thai
  - TIBT       # Tibetan
  - INDIC_OTHER  # Other Indic scripts (grouped)
  - SE_ASIAN_OTHER  # Other Southeast Asian
  - OTHER      # Everything else with training data
  - UNKNOWN    # Cannot determine / no text

# Mapping: ISO 15924 code → ML class
# Scripts not listed map to "OTHER"
iso15924_to_ml_class:
  # Latin and extensions
  Latn: LATN
  Latf: LATN  # Fraktur
  Latg: LATN  # Gaelic

  # Cyrillic
  Cyrl: CYRL
  Cyrs: CYRL  # Old Church Slavonic

  # Greek
  Grek: GREK

  # Arabic family
  Arab: ARAB
  Aran: ARAB  # Nastaliq

  # Hebrew
  Hebr: HEBR

  # Devanagari - keep separate, high volume
  Deva: DEVA

  # Bengali - keep separate, high volume
  Beng: BENG

  # Tamil - keep separate
  Taml: TAML

  # Telugu - keep separate
  Telu: TELU

  # CJK - each separate
  Hans: HANS
  Hant: HANT
  Hani: HANS  # Generic Han → Simplified as default
  Jpan: JPAN
  Hrkt: JPAN  # Hiragana + Katakana
  Hira: JPAN
  Kana: JPAN
  Kore: KORE
  Hang: KORE  # Hangul only

  # Thai
  Thai: THAI

  # Tibetan
  Tibt: TIBT

  # Other Indic scripts → grouped (can split later with more data)
  Gujr: INDIC_OTHER
  Knda: INDIC_OTHER
  Mlym: INDIC_OTHER
  Orya: INDIC_OTHER
  Sinh: INDIC_OTHER
  Guru: INDIC_OTHER

  # Southeast Asian → grouped
  Khmr: SE_ASIAN_OTHER
  Laoo: SE_ASIAN_OTHER
  Mymr: SE_ASIAN_OTHER

  # Special codes
  Zyyy: OTHER   # Common (punctuation)
  Zinh: OTHER   # Inherited
  Zzzz: UNKNOWN # Undetermined

# Scripts we've seen but don't have training data for → OTHER
# These are preserved in Tier 1, just grouped for training
unmapped_default: OTHER
```

```python
# src/schema_utils/script_ml_mapping.py

from pathlib import Path
import yaml

class ScriptMLMapping:
    """Configurable ISO 15924 → ML class mapping."""

    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or Path("config/script_ml_classes.yaml")
        self._load_config()

    def _load_config(self) -> None:
        with open(self.config_path) as f:
            self.config = yaml.safe_load(f)
        self.ml_classes = set(self.config["ml_classes"])
        self.mapping = self.config["iso15924_to_ml_class"]
        self.default = self.config.get("unmapped_default", "OTHER")

    def to_ml_class(self, iso15924_code: str) -> str:
        """Map ISO 15924 code to ML training class."""
        return self.mapping.get(iso15924_code, self.default)

    def get_all_codes_for_class(self, ml_class: str) -> list[str]:
        """Get all ISO 15924 codes that map to an ML class."""
        return [k for k, v in self.mapping.items() if v == ml_class]

    def reload(self) -> None:
        """Hot-reload config without restart."""
        self._load_config()
```

### 3.4 Tier 3: Routing Configuration (Fully Configurable)

**Principle**: OCR engine routing is separate from ML training. Update after testing!

```yaml
# config/script_routing.yaml
# Update this based on OCR engine testing results!

version: "1.0.0"
last_tested: "2026-01-29"
description: "Script → OCR engine routing (update after testing!)"

# Default engine when no specific routing
default_engine: "auto"
default_batch_size: 4

# Routing rules: ML class → engine config
# These can reference ML classes OR specific ISO 15924 codes
routing_rules:

  # Latin scripts - RapidOCR is fastest
  LATN:
    engine: "rapidocr"
    batch_size: 8
    notes: "Tested 2026-01-15, 98% accuracy"

  # Cyrillic - RapidOCR also good
  CYRL:
    engine: "rapidocr"
    batch_size: 8

  # Greek
  GREK:
    engine: "rapidocr"
    batch_size: 8

  # RTL scripts need special handling
  ARAB:
    engine: "tesseract"
    batch_size: 4
    rtl: true
    lang_hint: "ara+fas+urd"

  HEBR:
    engine: "tesseract"
    batch_size: 4
    rtl: true
    lang_hint: "heb"

  # CJK - PaddleOCR best
  HANS:
    engine: "paddleocr"
    batch_size: 2  # Memory intensive
    lang_hint: "ch"

  HANT:
    engine: "paddleocr"
    batch_size: 2
    lang_hint: "chinese_cht"

  JPAN:
    engine: "paddleocr"
    batch_size: 2
    lang_hint: "japan"

  KORE:
    engine: "paddleocr"
    batch_size: 2
    lang_hint: "korean"

  # Indic - PaddleOCR has good support
  DEVA:
    engine: "paddleocr"
    batch_size: 4
    lang_hint: "devanagari"

  BENG:
    engine: "paddleocr"
    batch_size: 4

  TAML:
    engine: "paddleocr"
    batch_size: 4

  TELU:
    engine: "paddleocr"
    batch_size: 4

  # Grouped Indic - test to find best
  INDIC_OTHER:
    engine: "paddleocr"
    batch_size: 4
    notes: "TODO: Test individual scripts, may need to split"

  # Thai
  THAI:
    engine: "paddleocr"
    batch_size: 4
    lang_hint: "thai"

  # Tibetan - limited support everywhere
  TIBT:
    engine: "tesseract"
    batch_size: 2
    notes: "Limited accuracy, consider VLM escalation"
    vlm_escalation_threshold: 0.6

  # SE Asian grouped
  SE_ASIAN_OTHER:
    engine: "tesseract"
    batch_size: 4
    notes: "TODO: Test Khmer, Lao, Myanmar individually"

  # Catch-all
  OTHER:
    engine: "auto"
    batch_size: 4
    notes: "Let Docling auto-detect"

  UNKNOWN:
    engine: "auto"
    batch_size: 4

# Override rules for specific ISO 15924 codes
# Use when a specific script needs different handling than its ML class
iso15924_overrides:
  # Example: Gujarati needs different engine than other INDIC_OTHER
  # Gujr:
  #   engine: "tesseract"
  #   lang_hint: "guj"
  #   notes: "PaddleOCR Gujarati model not good, use Tesseract"

# VLM escalation rules
vlm_escalation:
  # Escalate to VLM if confidence below threshold
  confidence_threshold: 0.5
  # Always escalate these scripts (poor OCR support)
  always_escalate:
    - "Tibt"  # Tibetan
    - "Ethi"  # Ethiopic
    - "Mymr"  # Myanmar
```

```python
# src/routing/script_router.py

class ScriptRouter:
    """Route scripts to OCR engines based on configurable rules."""

    def __init__(
        self,
        ml_mapping: ScriptMLMapping,
        routing_config_path: Path | None = None,
    ):
        self.ml_mapping = ml_mapping
        self.routing_config_path = routing_config_path or Path("config/script_routing.yaml")
        self._load_routing_config()

    def _load_routing_config(self) -> None:
        with open(self.routing_config_path) as f:
            self.routing = yaml.safe_load(f)

    def get_engine_config(self, iso15924_code: str) -> dict:
        """Get OCR engine configuration for a script.

        Priority:
        1. ISO 15924 override (most specific)
        2. ML class routing rule
        3. Default config
        """
        # Check for specific ISO override
        overrides = self.routing.get("iso15924_overrides", {})
        if iso15924_code in overrides:
            return {**self._get_defaults(), **overrides[iso15924_code]}

        # Map to ML class and get routing
        ml_class = self.ml_mapping.to_ml_class(iso15924_code)
        rules = self.routing.get("routing_rules", {})

        if ml_class in rules:
            return {**self._get_defaults(), **rules[ml_class]}

        return self._get_defaults()

    def _get_defaults(self) -> dict:
        return {
            "engine": self.routing.get("default_engine", "auto"),
            "batch_size": self.routing.get("default_batch_size", 4),
        }

    def should_escalate_to_vlm(self, iso15924_code: str, confidence: float) -> bool:
        """Check if script should escalate to VLM pipeline."""
        vlm_config = self.routing.get("vlm_escalation", {})

        # Always escalate list
        always = vlm_config.get("always_escalate", [])
        if iso15924_code in always:
            return True

        # Confidence threshold
        threshold = vlm_config.get("confidence_threshold", 0.5)
        return confidence < threshold

    def reload(self) -> None:
        """Hot-reload config without restart."""
        self._load_routing_config()
```

### 3.5 Script Detection Result Schema (Three-Tier Aware)

```python
class ScriptDetectionResult(BaseModel):
    """Script detection output preserving full granularity.

    Stores Tier 1 (exact ISO 15924) while providing Tier 2/3 mappings.
    """

    # TIER 1: Exact ISO 15924 code (NEVER aggregate here)
    detected_script: str = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Exact ISO 15924 4-letter code"
    )
    confidence: float = Field(..., ge=0.0, le=1.0)

    # Source provenance (preserve original labels)
    detection_method: str = Field(
        ...,
        description="Method: 'heuristic', 'siglip2_multitask', 'ocr_langdetect'"
    )
    source_label: str | None = Field(
        None,
        description="Original label from source data before normalization"
    )

    # TIER 2: ML class (computed, not stored - use mapping config)
    # This is a @property, not a stored field

    # TIER 3: Routing hints (computed from config)
    # These are @properties, not stored fields

    # Full probability distribution (for soft routing decisions)
    # Keys are ISO 15924 codes, not ML classes
    script_probabilities: dict[str, float] = Field(
        default_factory=dict,
        description="Probability distribution over ISO 15924 codes"
    )

    # Unknown handling
    is_unknown: bool = Field(default=False)
    unknown_reason: str | None = Field(None)

    # For region-level detection (mixed-script documents)
    bbox: list[int] | None = Field(None, description="[x, y, w, h] if localized")
    page_index: int | None = Field(None, description="Page number if multi-page")

    def get_ml_class(self, mapping: "ScriptMLMapping") -> str:
        """Get ML training class (Tier 2) via config mapping."""
        return mapping.to_ml_class(self.detected_script)

    def get_routing_config(self, router: "ScriptRouter") -> dict:
        """Get OCR routing config (Tier 3) via config."""
        return router.get_engine_config(self.detected_script)

    @classmethod
    def unknown(
        cls,
        reason: str,
        method: str = "heuristic",
        source_label: str | None = None,
    ) -> "ScriptDetectionResult":
        """Factory for unknown script results."""
        return cls(
            detected_script="Zzzz",
            confidence=0.0,
            detection_method=method,
            source_label=source_label,
            script_probabilities={"Zzzz": 1.0},
            is_unknown=True,
            unknown_reason=reason,
        )

    @classmethod
    def from_source_label(
        cls,
        source_label: str,
        confidence: float = 1.0,
        method: str = "dataset_ground_truth",
    ) -> "ScriptDetectionResult":
        """Create from source dataset label, normalizing to ISO 15924."""
        from image_preprocessing_detector.schema_utils.iso_language_script import (
            normalize_legacy_script,
        )

        iso_code = normalize_legacy_script(source_label)
        return cls(
            detected_script=iso_code,
            confidence=confidence,
            detection_method=method,
            source_label=source_label,  # Preserve original!
            script_probabilities={iso_code: confidence},
            is_unknown=(iso_code == "Zzzz"),
            unknown_reason="unmapped_source_label" if iso_code == "Zzzz" else None,
        )
```

### 3.6 Multi-Script Document Handling

```python
class DocumentScriptDetection(BaseModel):
    """Document-level script detection with full granularity preserved.

    Aggregates page/region-level detections while preserving all detail.
    """

    # ALL detected scripts with full detail (Tier 1 - preserve everything)
    script_instances: list[ScriptDetectionResult] = Field(
        default_factory=list,
        description="All script detections with full ISO 15924 codes"
    )

    # Document-level summary (computed from instances)
    dominant_script: str = Field(
        ...,
        description="Most prevalent ISO 15924 code"
    )
    dominant_confidence: float = Field(..., ge=0.0, le=1.0)

    # Full distribution over ISO 15924 codes (not ML classes!)
    script_distribution: dict[str, float] = Field(
        default_factory=dict,
        description="Percentage of pages/area per ISO 15924 code"
    )

    # Multi-script indicators
    is_multilingual: bool = Field(default=False)
    unique_scripts: list[str] = Field(
        default_factory=list,
        description="All unique ISO 15924 codes detected"
    )

    # Provenance
    detection_method: str = Field(default="aggregated")
    page_count: int = Field(default=0)
    region_count: int = Field(default=0)

    def get_ml_class_distribution(self, mapping: "ScriptMLMapping") -> dict[str, float]:
        """Get distribution over ML classes (Tier 2) for training/routing."""
        ml_dist: dict[str, float] = {}
        for iso_code, pct in self.script_distribution.items():
            ml_class = mapping.to_ml_class(iso_code)
            ml_dist[ml_class] = ml_dist.get(ml_class, 0.0) + pct
        return ml_dist

    def get_routing_engines(self, router: "ScriptRouter") -> list[dict]:
        """Get all OCR engines needed (Tier 3) for this document."""
        engines = []
        seen = set()
        for iso_code in self.unique_scripts:
            config = router.get_engine_config(iso_code)
            engine = config.get("engine", "auto")
            if engine not in seen:
                seen.add(engine)
                engines.append({
                    "engine": engine,
                    "scripts": [iso_code],
                    **config,
                })
            else:
                # Add script to existing engine entry
                for e in engines:
                    if e["engine"] == engine:
                        e["scripts"].append(iso_code)
                        break
        return engines

    @property
    def needs_multi_engine(self) -> bool:
        """Check if multiple OCR engines are needed."""
        # This is computed dynamically based on current routing config
        # Can change without re-processing documents!
        return len(self.unique_scripts) > 1

    @classmethod
    def from_instances(
        cls,
        instances: list[ScriptDetectionResult],
    ) -> "DocumentScriptDetection":
        """Aggregate script instances to document level."""

        if not instances:
            return cls(
                script_instances=[],
                dominant_script="Zzzz",
                dominant_confidence=0.0,
                is_multilingual=False,
                detection_method="empty",
            )

        # Count by ISO 15924 code (preserve full granularity!)
        script_counts: dict[str, float] = {}
        confidence_sums: dict[str, float] = {}

        for inst in instances:
            code = inst.detected_script
            script_counts[code] = script_counts.get(code, 0) + 1
            confidence_sums[code] = confidence_sums.get(code, 0.0) + inst.confidence

        total = sum(script_counts.values())
        distribution = {k: v / total for k, v in script_counts.items()}

        # Find dominant (by count, not confidence)
        dominant = max(script_counts.keys(), key=lambda k: script_counts[k])
        dominant_conf = confidence_sums[dominant] / script_counts[dominant]

        unique = sorted(script_counts.keys(), key=lambda k: -script_counts[k])

        return cls(
            script_instances=instances,
            dominant_script=dominant,
            dominant_confidence=round(dominant_conf, 4),
            script_distribution=distribution,
            is_multilingual=len(unique) > 1,
            unique_scripts=unique,
            detection_method="aggregated",
            page_count=len(set(i.page_index for i in instances if i.page_index is not None)),
            region_count=len(instances),
        )
```

### 3.7 Unknown and Edge Case Handling

```python
# Unknown script handling strategies

class UnknownScriptStrategy(str, Enum):
    """How to handle unknown scripts in the pipeline."""

    # Store as Zzzz, let downstream handle
    PASSTHROUGH = "passthrough"

    # Attempt OCR with auto-detect, update script based on result
    OCR_DETECT = "ocr_detect"

    # Escalate to VLM for script identification
    VLM_ESCALATE = "vlm_escalate"

    # Use heuristics (stroke density, aspect ratio) for best guess
    HEURISTIC_GUESS = "heuristic_guess"


def handle_unknown_script(
    result: ScriptDetectionResult,
    strategy: UnknownScriptStrategy,
    image: np.ndarray | None = None,
) -> ScriptDetectionResult:
    """Apply strategy for unknown scripts."""

    if not result.is_unknown:
        return result

    if strategy == UnknownScriptStrategy.PASSTHROUGH:
        return result

    if strategy == UnknownScriptStrategy.HEURISTIC_GUESS:
        # Apply visual heuristics
        if image is not None:
            guessed = _heuristic_script_guess(image)
            return ScriptDetectionResult(
                detected_script=guessed.code,
                confidence=guessed.confidence * 0.7,  # Discount for heuristic
                detection_method="heuristic_fallback",
                source_label=result.source_label,
                is_unknown=False,
                unknown_reason=None,
            )

    # Other strategies would involve async calls to OCR/VLM
    return result


def normalize_source_script_label(source_label: str, dataset: str) -> str:
    """Normalize various source label formats to ISO 15924.

    Preserves the original label in source_label field.
    """
    # Dataset-specific mappings
    dataset_mappings = {
        "mlt2019": {
            "Arabic": "Arab",
            "Latin": "Latn",
            "Chinese": "Hans",  # MLT doesn't distinguish Hans/Hant
            "Japanese": "Jpan",
            "Korean": "Kore",
            "Bangla": "Beng",
            "Hindi": "Deva",
            "Mixed": "Zyyy",
        },
        "coco_text": {
            "english": "Latn",
            "not english": "Zzzz",  # Too vague - mark unknown
        },
        # Add more dataset-specific mappings
    }

    if dataset in dataset_mappings:
        mapping = dataset_mappings[dataset]
        return mapping.get(source_label, "Zzzz")

    # Fall back to generic normalization
    from image_preprocessing_detector.schema_utils.iso_language_script import (
        normalize_legacy_script,
    )
    return normalize_legacy_script(source_label)
```

---

## Part 4: Continuous Label Schema for Training

### 4.1 The Binary Label Problem

**What went wrong with ResNet-50 teacher training**:

```python
# BAD: Binary labels
training_sample = {
    "image_path": "doc_001.png",
    "has_blur": True,       # Binary - loses magnitude
    "has_noise": False,     # Binary - no gradient signal
    "has_skew": True,       # Binary - all skew treated equal
}

# Model learned: "blur or no blur" instead of "how much blur"
# Result: Poor calibration, low correlation with human MOS
```

**What works**:

```python
# GOOD: Continuous labels with uncertainty
training_sample = {
    "image_path": "doc_001.png",
    "blur_score": 0.73,              # Continuous severity
    "blur_confidence": 0.85,          # Label confidence
    "noise_score": 0.12,              # Low noise
    "noise_confidence": 0.92,
    "skew_angle_degrees": 2.3,        # Actual measurement
    "skew_severity": 0.15,            # Normalized severity
}
```

### 4.2 Required Schema for All Detection Tasks

```python
class ContinuousDetectionScore(BaseModel):
    """Base schema for all continuous detection outputs.

    Use this pattern for ALL detection tasks to ensure:
    1. Continuous scores for gradient-based training
    2. Confidence bounds for uncertainty quantification
    3. Calibration metadata for post-hoc adjustment
    """

    # Primary score (MUST be continuous 0-1)
    score: float = Field(..., ge=0.0, le=1.0, description="Detection score")

    # Uncertainty (for proper loss weighting)
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in this score (1 - uncertainty)"
    )

    # Optional: Raw model outputs for calibration
    logit: float | None = Field(None, description="Raw logit before sigmoid")
    temperature: float | None = Field(None, description="Temperature used for calibration")

    # Provenance
    detection_method: str = Field(..., description="Model or heuristic used")
    model_version: str | None = Field(None)


class ShadowDetection(ContinuousDetectionScore):
    """Shadow detection with continuous severity."""

    # Extend base with shadow-specific fields
    shadow_regions: list[list[int]] | None = Field(
        None,
        description="Bounding boxes of shadow regions [x, y, w, h]"
    )
    shadow_coverage_percent: float = Field(
        0.0,
        ge=0.0,
        le=100.0,
        description="Percentage of image area affected by shadows"
    )


class WarpingDetection(ContinuousDetectionScore):
    """Warping/curvature detection with continuous severity."""

    curvature_type: str | None = Field(
        None,
        description="Type: 'barrel', 'pincushion', 'perspective', 'wave'"
    )
    max_deviation_pixels: float | None = Field(
        None,
        description="Maximum deviation from straight line in pixels"
    )
    requires_docres: bool = Field(
        False,
        description="True if severity requires DocRes correction"
    )


class TextLayerQuality(ContinuousDetectionScore):
    """PDF text layer quality assessment."""

    # Extend with text-layer specific metrics
    extraction_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Ratio of successfully extracted characters"
    )
    unicode_error_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Rate of replacement characters (U+FFFD)"
    )
    font_embedding_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Rate of properly embedded fonts"
    )
    skip_ocr_recommended: bool = Field(
        False,
        description="True if text layer is good enough to skip OCR"
    )
```

### 4.3 Script Detection Training Schema

```python
class ScriptDetectionTrainingLabel(BaseModel):
    """Training label for script detection with full distribution.

    For teacher model training, we need soft labels (probability distributions)
    not hard labels (single class).
    """

    # Image identifier
    image_id: str
    image_path: str

    # Soft label: probability distribution over ALL classes
    # Sum must equal 1.0
    class_probabilities: dict[str, float] = Field(
        ...,
        description="Probability distribution over script classes"
    )

    # Hard label (for evaluation)
    ground_truth_script: str = Field(..., description="ISO 15924 code")

    # Label source
    label_source: str = Field(
        ...,
        description="Source: 'human', 'dataset', 'vlm_pseudo', 'teacher_pseudo'"
    )
    label_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in this label"
    )

    # Multi-script handling
    is_multi_script: bool = Field(default=False)
    secondary_scripts: list[str] = Field(default_factory=list)

    @field_validator("class_probabilities")
    @classmethod
    def validate_probabilities(cls, v: dict[str, float]) -> dict[str, float]:
        """Ensure probabilities sum to 1."""
        total = sum(v.values())
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Probabilities must sum to 1, got {total}")
        return v

    @classmethod
    def from_hard_label(
        cls,
        image_id: str,
        image_path: str,
        script: str,
        label_source: str = "dataset",
        smoothing: float = 0.1,
    ) -> "ScriptDetectionTrainingLabel":
        """Convert hard label to soft label with smoothing.

        Label smoothing prevents overconfident predictions and
        improves calibration.
        """
        num_classes = len(SCRIPT_DETECTION_CLASSES)
        smooth_prob = smoothing / num_classes
        target_prob = 1.0 - smoothing + smooth_prob

        probs = {s: smooth_prob for s in SCRIPT_DETECTION_CLASSES}
        if script in probs:
            probs[script] = target_prob
        else:
            # Unknown script - map to ZZZZ
            probs["Zzzz"] = target_prob

        return cls(
            image_id=image_id,
            image_path=image_path,
            class_probabilities=probs,
            ground_truth_script=script,
            label_source=label_source,
            label_confidence=1.0 - smoothing,
        )
```

---

## Part 5: Proposed Schema Changes

### 5.1 Changes to schema.py

```python
# Add these imports
from image_preprocessing_detector.annotation.schemas.enums import CaptureMethod
from image_preprocessing_detector.schema_utils.iso_language_script import (
    ISO15924Script,
    ScriptFamily,
)


# Update LanguageInfo to use typed enum
class LanguageInfo(BaseModel):
    """Information about detected language/script in a document."""

    script: ISO15924Script = Field(
        ...,
        description="Script code (ISO 15924)"
    )
    script_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in script detection"
    )
    language: str | None = Field(
        None,
        description="Language code (ISO 639-1/3) if known"
    )
    script_family: ScriptFamily | None = Field(
        None,
        description="High-level script family for routing"
    )

    # For backward compatibility
    @property
    def confidence(self) -> float:
        """Alias for script_confidence."""
        return self.script_confidence


# Add ScriptDetection model
class ScriptDetection(BaseModel):
    """Document-level script detection with multi-script support."""

    # Primary detection
    dominant_script: ISO15924Script = Field(...)
    dominant_confidence: float = Field(..., ge=0.0, le=1.0)
    script_family: ScriptFamily = Field(...)

    # Full distribution (for routing decisions)
    script_probabilities: dict[str, float] = Field(default_factory=dict)

    # Multi-script
    is_multilingual: bool = Field(default=False)
    secondary_scripts: list[ISO15924Script] = Field(default_factory=list)

    # Unknown handling
    is_unknown: bool = Field(default=False)
    unknown_reason: str | None = Field(None)

    # Routing
    recommended_ocr_engine: str = Field(default="auto")

    # Provenance
    detection_method: str = Field(default="heuristic")
    model_version: str | None = Field(None)


# Add to PageLayoutSummary
class PageLayoutSummary(BaseModel):
    # ... existing fields ...

    # NEW: Shadow detection
    has_shadows: bool = Field(default=False)
    shadow_score: float = Field(default=0.0, ge=0.0, le=1.0)
    shadow_severity: Literal["none", "mild", "moderate", "severe"] = Field(default="none")

    # NEW: Warping detection
    has_warping: bool = Field(default=False)
    warping_score: float = Field(default=0.0, ge=0.0, le=1.0)
    warping_type: str | None = Field(None)  # "barrel", "pincushion", "wave"

    # NEW: Code detection
    has_code: bool = Field(default=False)
    code_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    # NEW: Table complexity (when has_tables=True)
    table_complexity: float | None = Field(None, ge=0.0, le=1.0)
    estimated_table_rows: int | None = Field(None)
    estimated_table_cols: int | None = Field(None)
    tables_have_borders: bool | None = Field(None)


# Add to DocumentMetadata
class DocumentMetadata(BaseModel):
    # ... existing fields ...

    # NEW: Capture method (different from pdf_type!)
    capture_method: CaptureMethod | None = Field(
        None,
        description="How document was captured (scanner, camera, born_digital)"
    )
    capture_method_confidence: float | None = Field(None, ge=0.0, le=1.0)

    # NEW: Script detection (replaces has_non_latin with richer info)
    script_detection: ScriptDetection | None = Field(
        None,
        description="Script/language detection with confidence and distribution"
    )

    # NEW: Text layer quality (for born_digital/hybrid)
    text_layer_quality: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="PDF text layer quality (1.0 = perfect, skip OCR)"
    )
    text_layer_skip_ocr: bool = Field(
        default=False,
        description="True if text layer is good enough to skip OCR"
    )

    # NEW: Degradation severity (for DocRes routing)
    degradation_severity: Literal["simple", "complex"] = Field(
        default="simple",
        description="simple = classical CV sufficient, complex = needs DocRes"
    )

    # NEW: PSM recommendation
    recommended_psm: int | None = Field(
        None,
        ge=0,
        le=13,
        description="Tesseract PSM recommendation (0-13)"
    )

    # Keep existing has_non_latin for backward compatibility
    # but mark as deprecated
    has_non_latin: bool = Field(
        default=False,
        description="DEPRECATED: Use script_detection.is_multilingual instead"
    )
```

### 5.2 Backward Compatibility

```python
# Add migration helper
def migrate_legacy_language_info(legacy: dict) -> LanguageInfo:
    """Migrate legacy LanguageInfo with string script to typed version."""
    from image_preprocessing_detector.schema_utils.iso_language_script import (
        normalize_legacy_script,
    )

    script_str = legacy.get("script", "unknown")
    iso_code = normalize_legacy_script(script_str)

    return LanguageInfo(
        script=ISO15924Script(iso_code),
        script_confidence=legacy.get("confidence", 0.0),
    )
```

---

## Part 6: Summary of Stream 1 Actions

### 6.1 What to KEEP (No Changes)

- [x] `PDFType` enum - correct as-is
- [x] `DQSMetadata` - uses continuous scores
- [x] `OrientationDetection` - complete model
- [x] `ISO15924Script` enum in schema_utils
- [x] `CaptureMethod` enum in annotation/schemas
- [x] `ScriptFamily` enum

### 6.2 What to MODIFY

| Item | Change |
|------|--------|
| `LanguageInfo` | Use `ISO15924Script` instead of `str` |
| `PageLayoutSummary` | Add shadow, warping, code, table complexity fields |
| `DocumentMetadata` | Add `capture_method`, `script_detection`, `text_layer_quality` |

### 6.3 What to ADD

| Item | Purpose |
|------|---------|
| `ScriptDetection` model | Multi-script support with distributions |
| `ScriptDetectionTrainingLabel` | Training data schema |
| `ContinuousDetectionScore` base | Ensure all detectors use continuous scores |
| `ShadowDetection` model | Shadow-specific fields |
| `WarpingDetection` model | Warping-specific fields |
| `TextLayerQuality` model | PDF text layer assessment |

### 6.4 What NOT to ADD (Already Exists)

- ❌ `DocumentSource` enum - Use existing `CaptureMethod`
- ❌ `ScriptType` enum - Use existing `ISO15924Script`
- ❌ `DegradationSeverity` enum - Simple literal type sufficient

---

## Part 7: Docling OCR Engine Mapping

Based on the expanded script list, here's the complete mapping for DoclingRouter:

```python
# Script → Docling OCR Engine Mapping

DOCLING_ENGINE_MAP = {
    # RapidOCR: Best for Latin, fast
    "Latn": {"engine": "rapidocr", "batch_size": 8},
    "Cyrl": {"engine": "rapidocr", "batch_size": 8},
    "Grek": {"engine": "rapidocr", "batch_size": 8},

    # Tesseract: Good general support, RTL
    "Arab": {"engine": "tesseract", "batch_size": 4, "rtl": True},
    "Hebr": {"engine": "tesseract", "batch_size": 4, "rtl": True},

    # PaddleOCR: Best for CJK and Indic
    "Hans": {"engine": "paddleocr", "batch_size": 2, "lang": "ch"},
    "Hant": {"engine": "paddleocr", "batch_size": 2, "lang": "cht"},
    "Jpan": {"engine": "paddleocr", "batch_size": 2, "lang": "japan"},
    "Kore": {"engine": "paddleocr", "batch_size": 2, "lang": "korean"},

    # PaddleOCR: Indic scripts
    "Deva": {"engine": "paddleocr", "batch_size": 4, "lang": "devanagari"},
    "Beng": {"engine": "paddleocr", "batch_size": 4, "lang": "bengali"},
    "Taml": {"engine": "paddleocr", "batch_size": 4, "lang": "tamil"},
    "Telu": {"engine": "paddleocr", "batch_size": 4, "lang": "telugu"},
    "Gujr": {"engine": "paddleocr", "batch_size": 4},
    "Mlym": {"engine": "paddleocr", "batch_size": 4},

    # Southeast Asian
    "Thai": {"engine": "paddleocr", "batch_size": 4, "lang": "thai"},
    "Mymr": {"engine": "tesseract", "batch_size": 4},
    "Khmr": {"engine": "tesseract", "batch_size": 4},

    # Other scripts (limited support)
    "Tibt": {"engine": "tesseract", "batch_size": 2},
    "Ethi": {"engine": "tesseract", "batch_size": 4},
    "Armn": {"engine": "tesseract", "batch_size": 4},
    "Geor": {"engine": "tesseract", "batch_size": 4},

    # Unknown/Mixed: Let Docling auto-detect
    "Zyyy": {"engine": "auto", "batch_size": 4},
    "Zzzz": {"engine": "auto", "batch_size": 4},
}
```

---

## Appendix A: Full ISO 15924 Reference

For analysis and storage, the full ISO 15924 list (200+ scripts) is available at:

- <https://unicode.org/iso15924/iso15924-codes.html>

Our `ISO15924Script` enum covers the ~35 scripts that represent 99%+ of documents you'll encounter. For rare scripts, use `ZZZZ` (unknown) and rely on post-OCR language detection.

---

**End of Document**

Sources:

- [Unicode ISO 15924 Code List](https://unicode.org/iso15924/iso15924-codes.html)
- [ISO 15924 Wikipedia](https://en.wikipedia.org/wiki/ISO_15924)
