"""Schema utilities for Project A metadata standardization.

This module provides:
- Bounding box format conversion and standardization
- Degradation-to-issue type mapping
- ISO language and script code utilities
- ISO paper size detection (ISO 216)
- Text scope/granularity classification
- JSON Schema validation utilities

All metadata uses:
- COCO bounding box format [x, y, width, height]
- ISO 639-1/3 language codes
- ISO 15924 script codes
- BCP 47 language tags
- ISO 216 paper sizes (A4, Letter, etc.)
- Standardized text scope vocabulary

Example:
    >>> from image_preprocessing_detector.schema_utils import (
    ...     convert_bbox,
    ...     BBoxFormat,
    ...     iqa_vector_to_runtime_issues,
    ...     validate_enrichment,
    ...     ValidationResult,
    ...     LanguageScriptTag,
    ...     create_language_script_info,
    ...     detect_paper_size,
    ...     PaperSize,
    ...     TextScope,
    ...     create_text_scope_info,
    ... )
    >>>
    >>> # Convert YOLO bbox to COCO
    >>> coco_bbox = convert_bbox([100, 200, 300, 250], "xyxy", "coco_xywh")
    >>>
    >>> # Convert 45-dim vector to runtime issues
    >>> issues = iqa_vector_to_runtime_issues(iqa_vector)
    >>>
    >>> # Create ISO-compliant language metadata
    >>> lang_info = create_language_script_info("zh", "Hans", confidence=0.95)
    >>>
    >>> # Detect paper size from image dimensions
    >>> paper_info = detect_paper_size(2480, 3508, dpi=300)  # A4 at 300 DPI
    >>>
    >>> # Create text scope metadata
    >>> scope_info = create_text_scope_info(TextScope.PAGE, content_type="printed")
    >>>
    >>> # Validate enrichment data
    >>> result = validate_enrichment(my_data)
    >>> if not result.valid:
    ...     print(result.errors)
"""

from image_preprocessing_detector.schema_utils.bbox_utils import (
    BBoxFormat,
    BoundingBox,
    batch_standardize_detections,
    convert_bbox,
    standardize_layout_detection,
)
from image_preprocessing_detector.schema_utils.dataset_source import (
    DATASET_REGISTRY,
    DatasetCategory,
    DatasetInfo,
    FileIntegrity,
    LicenseType,
    SampleSourceInfo,
    SourceInfo,
    create_file_integrity,
    create_source_info,
    get_dataset_info,
    get_datasets_by_category,
    get_datasets_by_license,
    get_datasets_with_mos,
    validate_sample_id,
)
from image_preprocessing_detector.schema_utils.degradation_mapping import (
    DEGRADATION_BY_NAME,
    DEGRADATION_INDEX,
    DEGRADATION_TO_ISSUE,
    GROUP_RANGES,
    DegradationGroup,
    DegradationType,
    RuntimeIssueType,
    SeverityLevel,
    aggregate_group_scores,
    get_degradation_group,
    iqa_vector_to_runtime_issues,
    runtime_issues_to_iqa_vector,
)
from image_preprocessing_detector.schema_utils.iso_language_script import (
    LANGUAGE_TO_DEFAULT_SCRIPT,
    SCRIPT_DETECTION_CLASSES,
    SCRIPT_TO_FAMILY,
    SCRIPT_TO_LANGUAGES,
    ISO639Language,
    ISO15924Script,
    ISOLanguageScriptInfo,
    LanguageScriptTag,
    ScriptFamily,
    create_language_script_info,
    get_iso15924_script,
    is_valid_iso15924_code,
    normalize_legacy_script,
    validate_script_code_for_ml,
)
from image_preprocessing_detector.schema_utils.iso_paper_sizes import (
    A4_PIXELS_BY_DPI,
    LETTER_PIXELS_BY_DPI,
    PAPER_SIZE_SPECS,
    PaperSize,
    PaperSizeInfo,
    PaperSizeSpec,
    PaperSizeStandard,
    detect_paper_size,
    get_expected_pixels,
)
from image_preprocessing_detector.schema_utils.openlid_integration import (
    ISO639_1_TO_3,
    ISO639_3_TO_1,
    OpenLIDDetector,
    OpenLIDResult,
    detect_language_openlid,
    detect_top_k_openlid,
)
from image_preprocessing_detector.schema_utils.openlid_integration import (
    get_detector as get_openlid_detector,
)
from image_preprocessing_detector.schema_utils.script_ml_mapping import (
    ScriptMLMapping,
    get_default_mapping,
    reset_default_mapping,
)
from image_preprocessing_detector.schema_utils.text_scope import (
    DATASET_SCOPE_DEFAULTS,
    SCOPE_CHAR_RANGES,
    SCOPE_ORDER,
    SCOPE_WORD_RANGES,
    TEXT_SCOPE_SPECS,
    ContentType,
    TextDensity,
    TextScope,
    TextScopeInfo,
    TextScopeSpec,
    compare_scopes,
    create_text_scope_info,
    estimate_scope_from_chars,
    estimate_scope_from_dimensions,
    estimate_scope_from_words,
    is_scope_compatible,
)
from image_preprocessing_detector.schema_utils.validation import (
    SchemaValidator,
    ValidationResult,
    get_layer2_schema,
    get_output_schema,
    validate_bbox,
    validate_document_metadata,
    validate_enrichment,
    validate_iqa_vector,
)

__all__ = [
    "A4_PIXELS_BY_DPI",
    "DATASET_REGISTRY",
    "DATASET_SCOPE_DEFAULTS",
    "DEGRADATION_BY_NAME",
    "DEGRADATION_INDEX",
    "DEGRADATION_TO_ISSUE",
    "GROUP_RANGES",
    "LANGUAGE_TO_DEFAULT_SCRIPT",
    "LETTER_PIXELS_BY_DPI",
    "PAPER_SIZE_SPECS",
    "SCOPE_CHAR_RANGES",
    "SCOPE_ORDER",
    "SCOPE_WORD_RANGES",
    "SCRIPT_DETECTION_CLASSES",
    "SCRIPT_TO_FAMILY",
    "SCRIPT_TO_LANGUAGES",
    "TEXT_SCOPE_SPECS",
    # Bbox utilities
    "BBoxFormat",
    "BoundingBox",
    "ContentType",
    # Dataset Source Tracking
    "DatasetCategory",
    "DatasetInfo",
    "DegradationGroup",
    "DegradationType",
    "FileIntegrity",
    # ISO Language/Script
    "ISO639Language",
    "ISO15924Script",
    "ISOLanguageScriptInfo",
    "LanguageScriptTag",
    "LicenseType",
    # ISO Paper Sizes
    "PaperSize",
    "PaperSizeInfo",
    "PaperSizeSpec",
    "PaperSizeStandard",
    # Degradation mapping
    "RuntimeIssueType",
    "SampleSourceInfo",
    "SchemaValidator",
    "ScriptFamily",
    "SeverityLevel",
    "SourceInfo",
    "TextDensity",
    # Text Scope
    "TextScope",
    "TextScopeInfo",
    "TextScopeSpec",
    # Validation
    "ValidationResult",
    "aggregate_group_scores",
    "batch_standardize_detections",
    "compare_scopes",
    "convert_bbox",
    "create_file_integrity",
    "create_language_script_info",
    "get_iso15924_script",
    "is_valid_iso15924_code",
    "validate_script_code_for_ml",
    "create_source_info",
    "create_text_scope_info",
    "detect_paper_size",
    "estimate_scope_from_chars",
    "estimate_scope_from_dimensions",
    "estimate_scope_from_words",
    "get_dataset_info",
    "get_datasets_by_category",
    "get_datasets_by_license",
    "get_datasets_with_mos",
    "get_degradation_group",
    "get_expected_pixels",
    "get_layer2_schema",
    "get_output_schema",
    "iqa_vector_to_runtime_issues",
    "is_scope_compatible",
    "normalize_legacy_script",
    "runtime_issues_to_iqa_vector",
    "standardize_layout_detection",
    "validate_bbox",
    "validate_document_metadata",
    "validate_enrichment",
    "validate_iqa_vector",
    "validate_sample_id",
    # Stream 1: Script ML Mapping
    "ScriptMLMapping",
    "get_default_mapping",
    "reset_default_mapping",
    # OpenLID-v2 Integration
    "ISO639_1_TO_3",
    "ISO639_3_TO_1",
    "OpenLIDDetector",
    "OpenLIDResult",
    "detect_language_openlid",
    "detect_top_k_openlid",
    "get_openlid_detector",
]
