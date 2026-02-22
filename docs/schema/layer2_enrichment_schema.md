---
schema_type: common
title: "Layer 2 Enrichment Schema Visualization"
tags:
  - schema
  - json
  - metadata
status: published
owner: docs-team
purpose: "Entity relationship diagram for the Layer 2 enrichment metadata schema."
---

> **Schema**: `layer2_enrichment.schema.json`
> **Purpose**: Prepare-Doc Layer 2 Enrichment - Derived annotations with full provenance tracking

## Entity Relationship Diagram

```mermaid
erDiagram
    Layer2EnrichmentMetadata ||--o| Provenance : "has"
    Layer2EnrichmentMetadata ||--|| EnrichmentData : "contains"

    EnrichmentData ||--o| CaptureMethodInfo : "capture_method"
    EnrichmentData ||--o| ResolutionInfo : "resolution"
    EnrichmentData ||--o| DomainInfo : "domain"
    EnrichmentData ||--o| StructureInfo : "structure"
    EnrichmentData ||--o| QualityInfo : "quality"
    EnrichmentData ||--o| LanguageInfo : "language"
    EnrichmentData ||--o{ LanguageInfo : "languages"
    EnrichmentData ||--o| TextScopeInfo : "text_scope"
    EnrichmentData ||--o| PaperSizeInfo : "paper_size"
    EnrichmentData ||--o| ContentFlags : "content_flags"
    EnrichmentData ||--o| LLMScores : "llm_scores"
    EnrichmentData ||--o{ LayoutDetection : "layout_detections"

    QualityInfo ||--o{ Degradation : "degradations"
    LayoutDetection ||--|| COCOBoundingBox : "bbox"
    Degradation ||--o| COCOBoundingBox : "region"
```

## Class Diagram

```mermaid
classDiagram
    class Layer2EnrichmentMetadata {
        <<root>>
        +string sample_id [uuid]
        +integer enrichment_version
        +datetime created_at
        +string created_by
        +enum method
        +string description
        +Provenance provenance
        +EnrichmentData data
    }

    class Provenance {
        +string git_sha [nullable]
        +string script_version [nullable]
        +string model_checkpoint [nullable]
        +string config_hash [nullable]
    }

    class EnrichmentData {
        +CaptureMethodInfo capture_method
        +ResolutionInfo resolution
        +DomainInfo domain
        +StructureInfo structure
        +QualityInfo quality
        +LanguageInfo language
        +LanguageInfo[] languages
        +TextScopeInfo text_scope
        +PaperSizeInfo paper_size
        +ContentFlags content_flags
        +LLMScores llm_scores
        +LayoutDetection[] layout_detections
    }

    class CaptureMethodInfo {
        +enum method
        +number confidence [0-1]
        +string detection_method
    }

    class ResolutionInfo {
        +integer dpi [nullable]
        +enum category
        +integer[2] pixels
        +number character_height_rendered_px [nullable]
        +integer output_size_px [nullable]
    }

    class DomainInfo {
        +enum level1
        +string level2 [nullable]
        +string level3 [nullable]
        +number confidence [0-1]
    }

    class StructureInfo {
        +enum text_density [nullable]
        +enum layout_type [nullable]
        +string[] element_types
        +enum[] text_directions_present [nullable]
    }

    class QualityInfo {
        +number overall_score [0-1]
        +Degradation[] degradations
    }

    class Degradation {
        +string type
        +enum severity
        +number severity_numeric [0-1]
        +number confidence [0-1]
        +string detection_method
        +enum location
        +COCOBoundingBox region [nullable]
    }

    class LanguageInfo {
        +string language_code [ISO 639]
        +enum script_code [ISO 15924]
        +string bcp47_tag
        +enum script_family
        +enum text_direction [nullable]
        +number confidence [0-1]
        +string detection_method
        +boolean is_rtl
        +boolean is_primary
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

    class ContentFlags {
        +boolean has_table [nullable]
        +boolean has_formula [nullable]
        +boolean has_handwriting [nullable]
        +boolean has_signature [nullable]
        +boolean has_figure [nullable]
        +enum tier
        +string source
    }

    class LLMScores {
        +number predicted_mos [1-5]
        +number predicted_normalized [0-1]
        +number prediction_confidence [0-1]
        +string model_name [nullable]
    }

    class LayoutDetection {
        +enum class_name [DocLayNet 11]
        +COCOBoundingBox bbox
        +number[4] bbox_original [nullable]
        +enum bbox_source_format
        +number confidence [0-1]
        +string source
        +number area [nullable]
    }

    class COCOBoundingBox {
        <<array>>
        +number x
        +number y
        +number width
        +number height
    }

    Layer2EnrichmentMetadata --> Provenance
    Layer2EnrichmentMetadata --> EnrichmentData
    EnrichmentData --> CaptureMethodInfo
    EnrichmentData --> ResolutionInfo
    EnrichmentData --> DomainInfo
    EnrichmentData --> StructureInfo
    EnrichmentData --> QualityInfo
    EnrichmentData --> LanguageInfo
    EnrichmentData --> TextScopeInfo
    EnrichmentData --> PaperSizeInfo
    EnrichmentData --> ContentFlags
    EnrichmentData --> LLMScores
    EnrichmentData --> LayoutDetection
    QualityInfo --> Degradation
    LayoutDetection --> COCOBoundingBox
    Degradation --> COCOBoundingBox
```

## Enumeration Values

```mermaid
classDiagram
    class MethodEnum {
        <<enumeration>>
        tier_0_exact
        tier_1_annotation
        tier_2_model
        tier_3_heuristic
    }

    class CaptureMethodEnum {
        <<enumeration>>
        born_digital
        scanner_flatbed
        scanner_adf
        camera_professional
        camera_smartphone
        fax
        synthetic
        unknown
    }

    class ResolutionCategoryEnum {
        <<enumeration>>
        low_150
        medium_150_299
        standard_300
        high_300
    }

    class DomainLevel1Enum {
        <<enumeration>>
        TAX
        LEG
        FIN
        TEC
        SCI
        ADM
        MED
        EDU
        PER
        UNK
    }

    class TextDensityEnum {
        <<enumeration>>
        sparse
        moderate
        dense
    }

    class LayoutTypeEnum {
        <<enumeration>>
        single_column
        multi_column
        three_column
        complex
        form_based
        tabular
        unknown
    }

    class SeverityEnum {
        <<enumeration>>
        none
        mild
        moderate
        severe
    }

    class ScriptCodeEnum {
        <<enumeration>>
        Latn ~Latin~
        Hans ~Simplified Chinese~
        Hant ~Traditional Chinese~
        Jpan ~Japanese~
        Kore ~Korean~
        Deva ~Devanagari~
        Arab ~Arabic~
        Cyrl ~Cyrillic~
        ... ~+25 more~
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

    class TextScopeEnum {
        <<enumeration>>
        character
        word
        phrase
        sentence
        line
        paragraph
        page
        document
        mixed
        unknown
    }

    class ContentTypeEnum {
        <<enumeration>>
        printed
        handwritten
        mixed
        scene_text
        synthetic
        unknown
    }

    class PaperSizeEnum {
        <<enumeration>>
        A0..A6
        B4..B5
        Letter
        Legal
        Tabloid
        Custom
        Unknown
    }

    class DocLayNetClassEnum {
        <<enumeration>>
        Caption
        Footnote
        Formula
        List_Item
        Page_Footer
        Page_Header
        Picture
        Section_Header
        Table
        Text
        Title
    }
```

## Data Flow Overview

```mermaid
flowchart TB
    subgraph Input["Layer 1 Input"]
        L1[("sample_id<br/>(UUID)")]
    end

    subgraph Layer2["Layer 2 Enrichment"]
        direction TB
        Root["Layer2EnrichmentMetadata"]
        Prov["Provenance<br/>git_sha, script_version"]
        Data["EnrichmentData"]
    end

    subgraph Enrichments["Enrichment Categories"]
        direction LR
        Cap["CaptureMethod<br/>born_digital, scanner..."]
        Res["Resolution<br/>DPI, pixels"]
        Dom["Domain<br/>TAX, LEG, FIN..."]
        Str["Structure<br/>text_density, layout_type"]
        Qual["Quality<br/>overall_score, degradations"]
        Lang["Language<br/>ISO 639 + ISO 15924"]
        Scope["TextScope<br/>character→document"]
        Paper["PaperSize<br/>ISO 216 / ANSI"]
        Flags["ContentFlags<br/>table, formula, handwriting"]
        LLM["LLMScores<br/>predicted MOS"]
        Layout["LayoutDetections[]<br/>11 DocLayNet classes"]
    end

    L1 --> Root
    Root --> Prov
    Root --> Data
    Data --> Cap
    Data --> Res
    Data --> Dom
    Data --> Str
    Data --> Qual
    Data --> Lang
    Data --> Scope
    Data --> Paper
    Data --> Flags
    Data --> LLM
    Data --> Layout
```

## Key Constraints

| Field | Constraint | Description |
|-------|------------|-------------|
| `sample_id` | UUID format | Links to Layer 1 immutable record |
| `enrichment_version` | integer ≥ 1 | Version tracking for updates |
| `method` | enum (4 tiers) | Provenance tier classification |
| `confidence` fields | 0.0 - 1.0 | Normalized confidence scores |
| `bbox` | [x, y, w, h] | COCO format, top-left origin |
| `script_code` | ISO 15924 | 4-letter, Title case (e.g., "Latn") |
| `language_code` | ISO 639-1/3 | 2-3 letter lowercase (e.g., "en") |
