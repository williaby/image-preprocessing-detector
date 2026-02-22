---
schema_type: common
title: "Document Metadata Schema Visualization"
tags:
  - schema
  - json
  - reference
status: published
owner: docs-team
purpose: "Entity relationship diagram for the document metadata output schema."
---

> **Schema**: `document_metadata.schema.json`
> **Purpose**: Prepare-Doc output schema for Unify handoff - Preprocessing, IQA & Coarse Layout Gateway

## Entity Relationship Diagram

```mermaid
erDiagram
    DocumentMetadata ||--|| DQSMetadata : "dqs"
    DocumentMetadata ||--o{ DocumentLanguage : "languages"
    DocumentMetadata ||--o{ PageLayoutSummary : "page_layout_summary"
    DocumentMetadata ||--o| UpscalingMetadata : "upscaling"
    DocumentMetadata ||--o| TeacherUsage : "teacher_usage"
    DocumentMetadata ||--|| ProcessingVersion : "processing_version"
    DocumentMetadata ||--o{ PageMetadata : "pages"

    PageMetadata ||--o| MLIQAResult : "ml_iqa"
    PageMetadata ||--o| MLIQAResult : "teacher_iqa"
    PageMetadata ||--o{ DetectedIssue : "detected_issues"
    PageMetadata ||--o{ PlannedAction : "planned_actions"
    PageMetadata ||--o{ DocumentElement : "elements"
    PageMetadata ||--o{ LanguageInfo : "languages"
    PageMetadata ||--o| TextScopeInfo : "text_scope"
    PageMetadata ||--o| PaperSizeInfo : "paper_size"
    PageMetadata ||--o{ TransformHistory : "transform_history"

    DocumentElement ||--o{ DetectedIssue : "quality_issues"
    LanguageInfo ||--o| COCOBoundingBox : "region"
```

## Class Diagram - Document Level

```mermaid
classDiagram
    class DocumentMetadata {
        <<root>>
        +string document_id
        +string file_name
        +string source_mime
        +integer num_pages
        +enum pdf_type
        +DocumentLanguage[] languages
        +enum primary_script_family
        +boolean has_non_latin
        +boolean has_rtl
        +number pre_ocr_risk [0-1]
        +DQSMetadata dqs
        +enum ocr_routing_recommendation
        +PageLayoutSummary[] page_layout_summary
        +UpscalingMetadata upscaling [nullable]
        +TeacherUsage teacher_usage [nullable]
        +ProcessingVersion processing_version
        +PageMetadata[] pages
    }

    class DQSMetadata {
        <<required>>
        +number degradation_score [0-1]
        +number structural_complexity_score [0-1]
    }

    class DocumentLanguage {
        +string language_code [ISO 639]
        +string script_code [ISO 15924]
        +string bcp47_tag
        +number confidence [0-1]
        +boolean is_primary
    }

    class PageLayoutSummary {
        <<required>>
        +integer page_number [1-based]
        +enum layout_type
        +boolean has_tables
        +boolean has_figures
        +boolean has_dense_math
        +boolean has_handwriting
        +boolean fuzzy_scan
        +boolean watermark
        +boolean colorful_background
        +number complexity_score [0-1]
    }

    class UpscalingMetadata {
        +boolean performed
        +integer original_dpi
        +integer target_dpi
        +enum algorithm
        +number processing_time_ms
    }

    class TeacherUsage {
        +integer[] pages_with_teacher
        +object escalation_reasons
        +string teacher_device [nullable]
        +integer total_teacher_time_ms
    }

    class ProcessingVersion {
        <<required>>
        +string pipeline_version
        +string iqa_model_hash [nullable]
        +string layout_model_hash [nullable]
        +object thresholds
        +datetime timestamp
    }

    DocumentMetadata --> DQSMetadata
    DocumentMetadata --> DocumentLanguage
    DocumentMetadata --> PageLayoutSummary
    DocumentMetadata --> UpscalingMetadata
    DocumentMetadata --> TeacherUsage
    DocumentMetadata --> ProcessingVersion
```

## Class Diagram - Page Level

```mermaid
classDiagram
    class PageMetadata {
        <<per-page>>
        +integer page_index [0-based]
        +integer width_px
        +integer height_px
        +integer dpi_input
        +integer dpi_effective
        +MLIQAResult ml_iqa [nullable]
        +MLIQAResult teacher_iqa [nullable]
        +DetectedIssue[] detected_issues
        +PlannedAction[] planned_actions
        +DocumentElement[] elements
        +LanguageInfo[] languages
        +TextScopeInfo text_scope [nullable]
        +PaperSizeInfo paper_size [nullable]
        +TransformHistory[] transform_history
    }

    class MLIQAResult {
        +enum source [student|teacher]
        +number blur_score [0-1]
        +number noise_score [0-1]
        +number contrast_score [0-1]
        +number skew_score [0-1]
        +number compression_score [0-1]
        +number overall_quality [0-1]
        +string device
        +number inference_time_ms
        +string escalation_reason
    }

    class DetectedIssue {
        <<required: type, confidence, severity>>
        +enum type
        +number confidence [0-1]
        +enum severity
        +object metrics
    }

    class PlannedAction {
        <<required: action, confidence, reason>>
        +enum action
        +object params
        +number confidence [0-1]
        +string reason
    }

    class DocumentElement {
        <<required: id, category, bbox, confidence>>
        +string id
        +enum category
        +integer[4] bbox [COCO]
        +integer[][] polygon [nullable]
        +number confidence [0-1]
        +object attributes
        +DetectedIssue[] quality_issues
        +boolean needs_correction
        +object correction_applied [nullable]
    }

    class LanguageInfo {
        +string language_code [nullable]
        +enum script_code [ISO 15924]
        +enum script_family
        +number confidence [0-1]
        +boolean is_rtl
        +COCOBoundingBox region
    }

    class TextScopeInfo {
        +enum scope
        +enum content_type
        +enum density
        +integer estimated_chars [nullable]
        +integer estimated_words [nullable]
        +number confidence [0-1]
        +string detection_method
    }

    class PaperSizeInfo {
        +enum detected_size
        +enum standard
        +number width_mm
        +number height_mm
        +enum orientation
        +number confidence [0-1]
        +boolean is_exact_match
    }

    class TransformHistory {
        <<required: action, started_at, finished_at, status>>
        +string action
        +object params
        +datetime started_at
        +datetime finished_at
        +enum status
        +string error_message [nullable]
    }

    class COCOBoundingBox {
        <<array: [x, y, w, h]>>
        +number x
        +number y
        +number width
        +number height
    }

    PageMetadata --> MLIQAResult
    PageMetadata --> DetectedIssue
    PageMetadata --> PlannedAction
    PageMetadata --> DocumentElement
    PageMetadata --> LanguageInfo
    PageMetadata --> TextScopeInfo
    PageMetadata --> PaperSizeInfo
    PageMetadata --> TransformHistory
    DocumentElement --> DetectedIssue
    LanguageInfo --> COCOBoundingBox
```

## Enumeration Values

```mermaid
classDiagram
    class PdfTypeEnum {
        <<enumeration>>
        image_only
        born_digital
        hybrid
    }

    class OcrRoutingEnum {
        <<enumeration>>
        ocr_fast
        ocr_advanced
        vision_simple
        vision_structured
    }

    class LayoutTypeEnum {
        <<enumeration>>
        single_column
        multi_column
        three_column
        complex
        unknown
    }

    class UpscaleAlgorithmEnum {
        <<enumeration>>
        lanczos
        bicubic
        inter_linear
        inter_cubic
        inter_area
    }

    class IssueTypeEnum {
        <<enumeration>>
        noise
        blur
        skew
        perspective
        low_contrast
        orientation
        low_dpi
    }

    class SeverityEnum {
        <<enumeration>>
        low
        medium
        high
        critical
    }

    class CorrectionActionEnum {
        <<enumeration>>
        deskew
        perspective_correction
        sharpen
        denoise
        clahe
        background_normalization
        upsample
        rotate
    }

    class ElementCategoryEnum {
        <<enumeration>>
        table
        image
        handwriting
        formula
        text_block
        figure
    }

    class ScriptFamilyEnum {
        <<enumeration>>
        latin
        cjk
        arabic
        indic
        cyrillic
        other
    }

    class TransformStatusEnum {
        <<enumeration>>
        success
        failed
        skipped
    }
```

## Data Flow - Prepare-Doc to Unify Handoff

```mermaid
flowchart TB
    subgraph InputDoc["Input Document"]
        PDF[("PDF/Image<br/>File")]
    end

    subgraph ProjectA["Prepare-Doc Processing"]
        direction TB

        subgraph DocLevel["Document-Level Analysis"]
            Type["PDF Type<br/>Classification"]
            Lang["Language/Script<br/>Detection"]
            DQS["DQS<br/>Calculation"]
            Route["OCR Routing<br/>Recommendation"]
        end

        subgraph PageLevel["Per-Page Processing"]
            IQA["ML IQA<br/>(Student)"]
            Teacher["Teacher IQA<br/>(if escalated)"]
            Issues["Issue<br/>Detection"]
            Corrections["Correction<br/>Planning"]
            Elements["Element<br/>Detection"]
        end

        subgraph Meta["Metadata Aggregation"]
            Version["Processing<br/>Version"]
            Upscale["Upscaling<br/>Info"]
            TeachUse["Teacher<br/>Usage Stats"]
        end
    end

    subgraph Output["DocumentMetadata.json"]
        JSON[("JSON<br/>Output")]
    end

    subgraph ProjectB["Unify (Downstream)"]
        OCR["OCR<br/>Orchestration"]
    end

    PDF --> Type
    PDF --> Lang
    PDF --> IQA

    Type --> DQS
    Lang --> Route
    IQA --> DQS
    IQA --> Issues
    IQA -.-> Teacher
    Teacher --> Issues
    Issues --> Corrections
    Corrections --> Elements

    DQS --> Route
    Route --> JSON
    Version --> JSON
    Upscale --> JSON
    TeachUse --> JSON
    Elements --> JSON

    JSON --> OCR
```

## Hierarchical Structure

```mermaid
flowchart TB
    subgraph Root["DocumentMetadata (Document Level)"]
        direction TB
        DocID["document_id, file_name, source_mime"]
        DocType["pdf_type, num_pages"]
        DocLang["languages[], primary_script_family, has_non_latin, has_rtl"]
        DocRisk["pre_ocr_risk, dqs, ocr_routing_recommendation"]
        DocLayout["page_layout_summary[]"]
        DocMeta["upscaling, teacher_usage, processing_version"]
    end

    subgraph Pages["pages[] (Page Level)"]
        direction TB
        PageDim["page_index, width_px, height_px, dpi_input, dpi_effective"]
        PageIQA["ml_iqa, teacher_iqa"]
        PageIssues["detected_issues[], planned_actions[]"]
        PageContent["elements[], languages[], text_scope, paper_size"]
        PageHistory["transform_history[]"]
    end

    subgraph Elements["elements[] (Element Level)"]
        direction TB
        ElemId["id, category, bbox, polygon, confidence"]
        ElemAttr["attributes, quality_issues[], needs_correction"]
        ElemCorrect["correction_applied"]
    end

    Root --> Pages
    Pages --> Elements
```

## Key Constraints

| Field | Constraint | Description |
|-------|------------|-------------|
| `document_id` | string, minLength: 1 | Unique identifier |
| `pdf_type` | enum (3 values) | Classification for routing |
| `pre_ocr_risk` | 0.0 - 1.0 | Combined OCR difficulty score |
| `dqs.degradation_score` | 0.0 - 1.0 | Image quality (0=pristine) |
| `dqs.structural_complexity_score` | 0.0 - 1.0 | Layout complexity (0=simple) |
| `page_index` | integer ≥ 0 | Zero-based index |
| `page_number` | integer ≥ 1 | One-based (layout summary) |
| `bbox` | [x, y, w, h] | COCO format, top-left origin |
| `processing_version.timestamp` | ISO 8601 | Processing datetime |

## Cross-Reference: Layer 2 Enrichment → Document Metadata

Several structures are shared or derived between schemas:

| Layer 2 Enrichment | Document Metadata | Relationship |
|-------------------|-------------------|--------------|
| `LanguageInfo` | `DocumentLanguage`, `LanguageInfo` | Nearly identical, different contexts |
| `TextScopeInfo` | `TextScopeInfo` | Identical structure |
| `PaperSizeInfo` | `PaperSizeInfo` | Identical structure |
| `COCOBoundingBox` | `COCOBoundingBox` | Identical format |
| `QualityInfo.degradations` | `DetectedIssue` | Similar but different severity enums |
| `LayoutDetection` | `DocumentElement` | Different class taxonomies |
| `ContentFlags` | `PageLayoutSummary` | Flags expanded to boolean fields |
