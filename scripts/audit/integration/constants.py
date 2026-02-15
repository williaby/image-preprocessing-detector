"""Shared constants for integration scripts.

Centralizes mappings, class sets, and default paths that were previously
copy-pasted across 52 integration scripts.
"""

from __future__ import annotations

from pathlib import Path

# ===================================================================
# Default paths
# ===================================================================
DEFAULT_REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")

# ===================================================================
# Version tags
# ===================================================================
DEFAULT_ENRICHMENT_VERSION_TAG = "integrated_v2"
DEFAULT_SCRIPT_VERSION = "1.1.0"

# ===================================================================
# Docling -> DocLayNet label mapping (KI-001)
#
# Covers core 11 DocLayNet classes plus Docling extensions.
# Used by KIMitigationMixin.apply_ki_001_layout_casing().
# ===================================================================
DOCLING_TO_DOCLAYNET: dict[str, str] = {
    "text": "Text",
    "list_item": "List-Item",
    "section_header": "Section-Header",
    "table": "Table",
    "picture": "Picture",
    "formula": "Formula",
    "caption": "Caption",
    "footnote": "Footnote",
    "page_footer": "Page-Footer",
    "page_header": "Page-Header",
    "title": "Title",
    "code": "Code",
    "checkbox_selected": "Checkbox-Selected",
    "checkbox_unselected": "Checkbox-Unselected",
}

# DocLayout-YOLO (DocStructBench) -> DocLayNet mapping
# Used when layout source is DocLayout-YOLO instead of Docling.
DOCLAYOUT_YOLO_TO_DOCLAYNET: dict[str, str] = {
    "figure": "Picture",
    "title": "Title",
    "plain text": "Text",
    "abandon": "Text",
    "figure_caption": "Caption",
    "table": "Table",
    "table_caption": "Caption",
    "table_footnote": "Footnote",
    "isolate_formula": "Formula",
    "formula_caption": "Caption",
}

# ===================================================================
# Content flag class sets
#
# Canonical layout class names (uppercase) used to derive boolean
# content flags from layout detections.
# ===================================================================
TABLE_CLASSES: frozenset[str] = frozenset({"TABLE"})
FORMULA_CLASSES: frozenset[str] = frozenset({"FORMULA", "ISOLATE_FORMULA"})
FIGURE_CLASSES: frozenset[str] = frozenset({"PICTURE", "FIGURE", "CHART"})
CODE_CLASSES: frozenset[str] = frozenset({"CODE"})

# ===================================================================
# Reliability tier thresholds
# ===================================================================
HARD_LABEL_THRESHOLD = 0.9
SOFT_LABEL_THRESHOLD = 0.7
ACTIVE_LEARNING_THRESHOLD = 0.5

# ===================================================================
# Default confidence values by source
# ===================================================================
CONFIDENCE_PARSER_GT = 0.95
CONFIDENCE_TRAIN_GT = 0.90
CONFIDENCE_DATASET_DOC = 1.0
CONFIDENCE_LAYOUT_DOCLING = 0.85
CONFIDENCE_VLM_CONTACT_SHEET = 0.75
CONFIDENCE_OPENLID = 0.70
CONFIDENCE_LLM_VISION = 0.65
CONFIDENCE_DEFAULT = 0.5
CONFIDENCE_NONE = 0.3
CONFIDENCE_UNKNOWN = 0.1

# ===================================================================
# Reliability field definitions
#
# Maps (field_name, confidence_key) for reliability summary computation.
# ===================================================================
RELIABILITY_FIELD_DEFS: list[tuple[str, str]] = [
    ("capture_method", "capture_confidence"),
    ("domain", "domain_confidence"),
    ("language", "language_confidence"),
    ("layout_detections", "layout_confidence"),
    ("content_flags", "content_flags_confidence"),
]
