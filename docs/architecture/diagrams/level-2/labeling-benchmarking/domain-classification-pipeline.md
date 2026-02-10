---
schema_type: common
title: "Level 2: Domain Classification & Metadata Enrichment Pipeline"
description: "Multi-field metadata enrichment via OpenRouter LLMs with tiered confidence escalation"
tags:
- architecture
- diagrams
- level_2
- domain_classification
- metadata_enrichment
- openrouter
- workstream_5
status: published
owner: "core-maintainer"
authors:
- name: "Byron Williams"
purpose: "Document the LLM-based domain classification pipeline that enriches Layer 2 metadata
  with domain labels, language detection, and visual content flags via OpenRouter API."
---

# Domain Classification & Metadata Enrichment Pipeline

Enriches per-sample Layer 2 metadata using OpenRouter LLM models. Classifies documents into 10 domain codes and extracts multiple metadata fields in a single API call, using tiered confidence escalation across free text models and paid vision models.

**Status**: Active
**Lines of Code**: ~1,200 (4 modules + 1 script + 4 test files)

---

## Overview

**Problem**: Many datasets lack domain labels (`domain_level1`), leaving samples as `UNK`. For example, DocLayNet (81K images) is 100% `UNK` despite containing financial, scientific, legal, and other document types.

**Solution**: Per-sample LLM classification via OpenRouter API that:

1. Routes text-available samples to free text models (7 available)
2. Escalates low-confidence results to secondary models
3. Falls back to paid vision models for image-only samples
4. Extracts multiple Layer 2 fields per API call for negligible extra cost

**Key Design Decisions**:

- All 7 user-specified models are text-only (no vision support)
- Vision fallback uses paid models (~$0.00021/sample)
- Multi-field extraction maximizes value per API call (input tokens dominate cost)
- Follows established enrichment script pattern (`enrich_language_from_gt.py`)

---

## Architecture Diagram

See [domain-classification-pipeline.puml](domain-classification-pipeline.puml) for the PlantUML source.

---

## Module Structure

```
src/image_preprocessing_detector/labeling/domain/
    __init__.py              # Public exports
    config.py                # Model configs, thresholds, constants
    prompts.py               # Text and vision prompt templates
    openrouter_client.py     # OpenRouter API client (OpenAI SDK)
    classifier.py            # MetadataEnricher orchestrator

scripts/
    enrich_metadata_from_llm.py   # CLI enrichment script

tests/unit/labeling/domain/
    test_config.py
    test_prompts.py
    test_openrouter_client.py
    test_classifier.py
```

---

## Classification Flow

### Tiered Confidence Escalation

```
Sample Input
    |
    v
Has text? ----YES----> Primary Text Model (deepseek-r1, FREE)
    |                       |
    NO                  confidence >= 0.85?
    |                   YES -> ACCEPT (4 fields)
    v                   NO  -> Secondary Text Model (llama-3.3-70b, FREE)
Primary Vision Model            -> Take higher confidence
(gemini-2.0-flash, PAID)
    |
confidence >= 0.80?
YES -> ACCEPT (11 fields)
NO  -> Secondary Vision Model (qwen2.5-vl-3b, PAID)
        -> Take higher confidence
```

### Fields Extracted Per API Call

| Mode | Fields | Cost |
|------|--------|------|
| **Text** (free) | domain, iso639_language, iso15924_script, content_type | $0.00 |
| **Vision** (paid) | All text fields + capture_method, has_table, has_formula, has_handwriting, has_signature, has_figure, orientation | ~$0.00021/sample |

---

## Model Roster

### Text Models (All Free)

| Model | Context | Role |
|-------|---------|------|
| `deepseek/deepseek-r1-0528:free` | 164K | Primary text |
| `meta-llama/llama-3.3-70b-instruct:free` | 128K | Secondary text |
| `stepfun/step-3.5-flash:free` | 256K | Alternate |
| `qwen/qwen3-coder:free` | 262K | Alternate |
| `nvidia/nemotron-3-nano-30b-a3b:free` | 256K | Alternate |
| `z-ai/glm-4.5-air:free` | 131K | Alternate |
| `tngtech/tng-r1t-chimera:free` | 164K | Alternate |

### Vision Models (Paid)

| Model | Input $/M | Output $/M | Role |
|-------|-----------|------------|------|
| `google/gemini-2.0-flash-001` | $0.10 | $0.40 | Primary vision |
| `google/gemini-2.0-flash-lite-001` | $0.075 | $0.30 | Alternate vision |
| `qwen/qwen2.5-vl-3b-instruct` | ~$0.03 | ~$0.09 | Secondary vision |

---

## Domain Taxonomy (10 Codes)

| Code | Domain | Examples |
|------|--------|----------|
| TAX | Tax | Forms, returns, schedules, W-2, 1099 |
| LEG | Legal | Contracts, court filings, briefs, patents |
| FIN | Financial | Invoices, receipts, bank statements, SEC filings |
| TEC | Technical | Manuals, specifications, datasheets |
| SCI | Scientific | Research papers, journal articles, theses |
| ADM | Administrative | Memos, letters, correspondence, meeting minutes |
| MED | Medical | Patient records, prescriptions, lab results |
| EDU | Educational | Textbooks, exams, worksheets, certificates |
| PER | Personal | IDs, passports, birth certificates |
| UNK | Unknown | Truly unclassifiable |

---

## Key Components

### config.py

- `DomainModelConfig` (frozen): Model identifier, role, max_tokens, vision support
- `DomainPipelineConfig` (frozen): Model roster, confidence thresholds, retry settings, API key resolution
- `EnrichmentResult`: All extracted metadata fields (domain + language + content flags)
- `AVAILABLE_TEXT_MODELS` / `AVAILABLE_VISION_MODELS`: Model inventories

### prompts.py

- `build_text_prompt(text, max_chars)`: System + user messages for text classification (4 fields)
- `build_vision_prompt()`: System + user messages for vision classification (11 fields), caller appends image

### openrouter_client.py

- `OpenRouterClient`: Lazily initializes OpenAI SDK with `base_url="https://openrouter.ai/api/v1"`
- `classify_text()` / `classify_image()`: High-level classification methods
- Exponential backoff retry (1s/2s/4s), JSON extraction (clean/markdown/brace patterns)
- Image encoding: PIL resize to max 1024px, convert to RGB, base64 PNG

### classifier.py

- `MetadataEnricher`: Orchestrator implementing tiered confidence escalation
- `enrich_sample()`: Routes text vs vision, handles escalation
- `enrich_batch()`: Batch processing with rate limiting, resume support, error isolation
- `_fallback_result()`: UNK result with zero confidence on failure

### enrich_metadata_from_llm.py

- 14 text datasets + 3 vision-only datasets configured
- Text extraction per format (COCO, FUNSD, JSONL, FinTabNet, Docling OCR)
- CLI: `--dataset`, `--all`, `--dry-run`, `--limit`, `--resume`, `--text-only`, `--vision-only`
- Output: `{dataset}_llm_enrichment.json` in metadata registry

---

## Cost Estimates

| Scale | Text (free) | Vision (~$0.00021/sample) |
|-------|-------------|---------------------------|
| 1,000 samples | $0.00 | $0.21 |
| 10,000 samples | $0.00 | $2.10 |
| 100,000 samples | $0.00 | $21.00 |

Multi-field extraction adds ~$0.000016/sample in extra output tokens.

---

## Test Coverage

83 unit tests across 4 test modules:

| Module | Tests | Coverage |
|--------|-------|----------|
| test_config.py | 14 | Config validation, defaults, API key |
| test_prompts.py | 15 | Prompt structure, domain codes, truncation |
| test_openrouter_client.py | 28 | JSON parsing, response parsing, retry, helpers |
| test_classifier.py | 26 | Routing, escalation, batch, error handling |

---

## Integration Points

- **Input**: Layer 1 annotations (ground truth text), extracted/OCR text, document images
- **Output**: Layer 2 `EnrichmentData` fields (`domain_level1`, `iso639_language`, `capture_method`, content flags)
- **Pattern**: Follows `enrich_language_from_gt.py` enrichment script conventions
- **Registry**: Outputs to `metadata_registry/json/{dataset}_llm_enrichment.json`

---

## Related Documentation

- [Automated Data Labeling Pipeline](../data-preparation/automated-data-labeling-pipeline.puml) - Broader labeling architecture
- [Metadata Schema Architecture](../data-preparation/metadata-schema-architecture.puml) - Layer 2 schema details
- [Labeling & Benchmarking Models](index.md) - Workstream 5 overview
