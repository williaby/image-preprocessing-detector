---
schema_type: common
title: "foundry-unify: Repository and Architecture Design"
description: "Design spec for the foundry-unify Python service: repo scaffolding, layered
  architecture, data contracts, core interfaces, FastAPI surface, and Phase B1 scope."
purpose: "Give the foundry-unify team the full architectural design, interface contracts,
  and Phase B1 scope boundary needed to scaffold and begin development."
status: active
owner: core-maintainer
tags:
  - pipeline
  - rag_pipeline
  - integration
  - ocr
  - architecture
  - specifications
---

**Version:** 1.0.0 | **Status:** Approved | **Date:** 2026-05-05

---

## 1. Context

foundry-unify is Stage 3 of the six-service Foundry RAG pipeline. It sits between two
upstream preprocessing services and the downstream chunking service:

```text
foundry-ingest
      │
      ├── audio/video ──► foundry-prepare-audio ──┐
      │                                            │
      └── documents ────► foundry-prepare-doc ─────┤
                                                   │
                                          foundry-unify   ◄─── THIS SERVICE
                                                   │
                                          foundry-chunk
```

**Mission**: Receive preprocessing metadata and corrected artifacts from both upstream
tracks, run OCR orchestration via docling-serve, assemble a unified `DoclingDOM.json`,
and write it to GCS `03-docling-dom/` for foundry-chunk to consume.

**Key constraint**: Two radically different input tracks produce one identical output
schema. The document track requires full OCR orchestration. The audio track skips OCR
entirely and passes through a pre-assembled DOM after schema normalization.

**Reference**: Full pipeline context and all input/output contracts are in
[`docs/development/RAG Pipeline/foundry-unify-team-handoff.md`](../RAG%20Pipeline/foundry-unify-team-handoff.md).

---

## 2. Repository Scaffolding

**GitHub**: `ByronWilliamsCPA/Unify` (public)

Scaffolded via the `cookiecutter-python-template` with these feature flags:

| Variable | Value |
|---|---|
| `project_name` | `Foundry Unify` |
| `project_slug` | `foundry_unify` |
| `author_name` | `Byron Williams` |
| `author_email` | `byronawilliams@gmail.com` |
| `python_version` | `3.12` |
| `include_cli` | `no` |
| `include_github_actions` | `yes` |
| `include_semantic_release` | `yes` |
| `include_codecov` | `yes` |
| `include_sonarcloud` | `yes` |
| `include_renovate` | `yes` |
| `include_docker` | `yes` |
| `use_mkdocs` | `yes` |
| `include_coderabbit` | `yes` |

SonarCloud org: `williaby`, project key: `ByronWilliamsCPA_Unify`.

---

## 3. Architectural Approach

**Layered architecture with stub implementations.**

Core interfaces and data models are defined upfront to cover the full four-phase roadmap.
Phase B1 ships one minimal concrete implementation behind each interface. Phases B2-B4 add
new implementations without touching existing ones and without restructuring the codebase.

This approach was chosen over a thin-adapter approach (fast to ship, hard to extend) and
a full-orchestration approach (over-engineered for B1) because the handoff document
provides a complete four-phase roadmap with well-defined contracts at every boundary —
exactly the situation where interface discipline pays off across months of development.

---

## 4. Package Structure

```text
src/foundry_unify/
├── api/
│   ├── routes.py          # FastAPI router — POST /v1/process, GET /health, GET /v1/status/{trace_id}
│   └── models.py          # Request/response Pydantic models for the HTTP surface
│
├── contracts/
│   ├── document.py        # DocumentMetadata + DoclingRoutingParams (subset of schema.py)
│   ├── audio.py           # TranscriptMetadata
│   └── output.py          # DoclingDOM — the unified output schema
│
├── adapters/
│   ├── gcs.py             # GCS read/write — download metadata, upload DoclingDOM.json
│   └── docling_client.py  # HTTP client for docling-serve (copied from image_detection)
│
├── routing/
│   ├── tier_router.py     # TierRouter Protocol + StandardTierRouter (B1)
│   └── specialist.py      # SpecialistDispatcher Protocol + StubDispatcher (B1)
│
├── processing/
│   ├── dom_assembler.py   # DomAssembler Protocol + B1DomAssembler
│   ├── audio_normalizer.py # AudioNormalizer Protocol + B2AudioNormalizer (passthrough)
│   └── mitigations.py     # MitigationHook Protocol + KI-002 and KI-003 stubs
│
├── config.py              # Settings via pydantic-settings
└── app.py                 # FastAPI app factory with dependency injection
```

**Layer responsibilities:**

- `contracts/` — read-only data definitions; the only layer that changes when upstream schemas change
- `adapters/` — all I/O (GCS, docling-serve); no business logic
- `routing/` — decides which tier and which specialist engine to use per element
- `processing/` — assembles the DoclingDOM from raw OCR output; applies mitigation hooks
- `api/` — HTTP surface only; delegates immediately to the service layer

---

## 5. Data Contracts

### 5.1 Document Track Input (`contracts/document.py`)

Key fields consumed from `DocumentMetadata.json` (schema v2.0):

```python
class DoclingRoutingParams(BaseModel):
    pipeline: Literal["standard", "vlm", "legacy"]
    ocr_enabled: bool
    ocr_force: bool
    ocr_engine: Literal["auto", "rapidocr", "tesseract"]
    tables_enabled: bool
    table_mode: Literal["fast", "accurate"]
    enrich_code: bool
    enrich_formula: bool
    page_batch_size: int
    vlm_model: str | None
    ocr_lang: str | None
    psm: int | None

    def to_cli_args(self) -> list[str]: ...

class DocumentMetadata(BaseModel):
    document_id: str
    trace_id: str
    pdf_type: Literal["image_only", "born_digital", "hybrid"]
    processing_recommendation: ProcessingRecommendation
    quality_assessment: QualityAssessment
    pages: list[PageMetadata]
    docling_params: DoclingRoutingParams
```

Full schema reference: `src/image_preprocessing_detector/schema.py` (this repo), classes
`DocumentMetadata` (line 1249), `DoclingRoutingParams` (line 755).

### 5.2 Audio Track Input (`contracts/audio.py`)

```python
class TranscriptMetadata(BaseModel):
    source_track: Literal["audio", "document"]
    document_id: str
    trace_id: str
    docling_document: dict          # Pre-assembled DOM — passed through after normalization
    transcription: Transcription    # full_text absence is a hard error
    audio_quality: AudioQuality     # snr_db below threshold → quality warning, not rejection
```

### 5.3 Unified Output (`contracts/output.py`)

Schema is identical regardless of input track. foundry-chunk reads this without knowing
which track produced it.

```python
class DoclingDOM(BaseModel):
    document_id: str
    trace_id: str
    source_track: Literal["document", "audio"]
    metadata: ProcessingMetadata    # processing_tier, engine provenance
    pages: list[PageDOM]

class PageDOM(BaseModel):
    page_number: int
    elements: list[LayoutElement]
    reading_order_confidence: float

class LayoutElement(BaseModel):
    element_type: str               # Title, Text, Table, Picture, Formula, etc.
    bbox: BoundingBox
    text: str
    ocr_engine_provenance: str
    reading_order: int
    is_parasitic: bool = False      # B2: headers, footers, watermarks
```

GCS output path: `gs://rag-pipeline-{env}/{trace_id}/03-docling-dom/DoclingDOM.json`

---

## 6. Core Interfaces

All interfaces are Python `Protocol` classes — no inheritance required, structural typing
only. This keeps concrete implementations decoupled and test-injectable via FastAPI `Depends()`.

### 6.1 TierRouter (`routing/tier_router.py`)

```python
class TierRouter(Protocol):
    def select_tier(self, meta: DocumentMetadata) -> ProcessingTier: ...

class StandardTierRouter:
    """B1: reads processing_recommendation.tier directly from metadata.
    B4: adds VLM validation logic and threshold override handling."""
    def select_tier(self, meta: DocumentMetadata) -> ProcessingTier:
        return ProcessingTier(meta.processing_recommendation.tier)
```

### 6.2 SpecialistDispatcher (`routing/specialist.py`)

```python
class SpecialistDispatcher(Protocol):
    def dispatch(self, element: LayoutElement, meta: DocumentMetadata) -> str: ...

class StubDispatcher:
    """B1: always returns base docling engine.
    B3: routes tables → tableformer/structeqtable, formulas → texify/unimernet,
        handwriting → trocr, code blocks → docling-standard."""
    def dispatch(self, element: LayoutElement, meta: DocumentMetadata) -> str:
        return "docling-standard"
```

### 6.3 DomAssembler (`processing/dom_assembler.py`)

```python
class DomAssembler(Protocol):
    def assemble(self, pages: list[RawPage], meta: DocumentMetadata) -> DoclingDOM: ...

class B1DomAssembler:
    """B1: assembles DOM from docling-serve JSON response. Applies mitigation hooks
    as a strategy list — KI-002 and KI-003 are stubs in B1, activated in B3.
    B3: merges specialist OCR outputs per element before assembly."""
    def __init__(self, mitigations: list[MitigationHook]) -> None: ...
```

### 6.4 AudioNormalizer (`processing/audio_normalizer.py`)

```python
class AudioNormalizer(Protocol):
    def normalize(self, meta: TranscriptMetadata) -> DoclingDOM: ...

class B2AudioNormalizer:
    """Passes docling_document through after schema normalization.
    Maps: speaker turns → SectionItem, utterances → TextItem (with timing fields),
    summary → SectionItem at top of DOM."""
    def normalize(self, meta: TranscriptMetadata) -> DoclingDOM: ...
```

### 6.5 Mitigation Hooks (`processing/mitigations.py`)

```python
class MitigationHook(Protocol):
    def apply(self, elements: list[LayoutElement]) -> list[LayoutElement]: ...

class TableMulticolumnMitigation:
    """KI-002 (HIGH): reclassifies low-confidence Table → Text when no rows/cols
    detected by TableFormer. B1: passthrough stub. B3: confidence gating enabled.
    Reference: docs/known_issues/KI-002-docling-table-multicolumn.md"""
    def apply(self, elements: list[LayoutElement]) -> list[LayoutElement]:
        return elements  # B1 passthrough

class PictureDenseTextMitigation:
    """KI-003 (MEDIUM): VLM inspection on Picture elements, override to Text if
    VLM returns text content. B1: passthrough stub. B3: VLM inspection enabled.
    Reference: docs/known_issues/KI-003-docling-picture-dense-text.md"""
    def apply(self, elements: list[LayoutElement]) -> list[LayoutElement]:
        return elements  # B1 passthrough
```

---

## 7. FastAPI HTTP Surface

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/process` | Trigger processing for a trace ID |
| `GET` | `/health` | Liveness — checks docling-serve and GCS reachability |
| `GET` | `/v1/status/{trace_id}` | Poll processing state |

### POST /v1/process

**Request:**

```python
class ProcessRequest(BaseModel):
    trace_id: str
    document_id: str
    source_track: Literal["document", "audio"]
    env: Literal["dev", "staging", "prod"] = "dev"
```

**Processing flow:**

```text
1. Download metadata from GCS (DocumentMetadata.json or TranscriptMetadata.json)
2. Branch on source_track — hard error MISSING_SOURCE_TRACK if absent
3. Document track:
   a. TierRouter.select_tier() → ProcessingTier
   b. For each page: DoclingClient.convert() with DoclingRoutingParams
   c. DomAssembler.assemble() with mitigation hooks applied
4. Audio track:
   a. AudioNormalizer.normalize() → DoclingDOM directly (no OCR)
5. GcsAdapter.write_dom() → 03-docling-dom/DoclingDOM.json
6. Return 200 {trace_id, document_id, output_path, processing_tier}
```

**Error response:**

```python
class ProcessingError(BaseModel):
    error_code: str     # MISSING_SOURCE_TRACK | MISSING_DOCLING_DOM | EMPTY_TRANSCRIPT
    trace_id: str
    message: str
```

Error codes match the contracts defined in the handoff document (Sections 3.2.4 and 6).

### Configuration (`config.py`)

```python
class Settings(BaseSettings):
    docling_serve_url: str = "http://192.168.1.209:5001"
    docling_timeout_seconds: int = 300
    gcs_bucket_template: str = "rag-pipeline-{env}"
    log_level: str = "INFO"
```

All interfaces are injected via `FastAPI.Depends()` — swappable in tests without
patching internals.

---

## 8. Dependencies

### Runtime

| Package | Purpose |
|---|---|
| `fastapi` + `uvicorn` | HTTP service |
| `docling-core>=2.3.0` | DoclingDOM types (consistent with audio-processor) |
| `google-cloud-storage` | GCS adapter |
| `pydantic-settings` | Environment-variable config binding |
| `httpx` | Async-compatible HTTP client for docling-serve |

### Dev/Test

| Package | Purpose |
|---|---|
| `pytest-asyncio` | Async FastAPI route testing |
| `respx` | httpx request mocking for docling-serve |
| `pytest-mock` | General mocking |
| `gcs-testbench` | Local GCS emulator for adapter integration tests |

---

## 9. Repo File Deliverables

```text
foundry-unify/
├── src/foundry_unify/         ← full package skeleton, all modules stubbed
├── tests/
│   ├── unit/                  ← interface and contract tests
│   └── integration/           ← GCS adapter + docling_client against live endpoints
├── deployment/
│   └── docker-compose.yml     ← foundry-unify service (mirrors docling-serve pattern)
├── docs/
│   ├── development/           ← Phase roadmap, contracts (from image_detection)
│   └── known_issues/          ← KI-002, KI-003, KI-008 (from image_detection)
├── configs/
│   └── project_b_thresholds.yaml  ← tier thresholds from handoff doc Section 5
├── .env.example               ← DOCLING_SERVE_URL, GCS_BUCKET_TEMPLATE, LOG_LEVEL
└── sonar-project.properties   ← SonarCloud config, org: williaby
```

---

## 10. Phase B1 Scope Boundary

Phase B1 gates on the integration test checklist from handoff Section 14:

- [ ] Born-digital PDF → `standard` tier → `DoclingDOM.json` written to GCS
- [ ] `DoclingRoutingParams.to_cli_args()` applied correctly to Docling configuration
- [ ] Audio input (`source_track: "audio"`) → OCR skipped, DOM normalized and written
- [ ] Missing `source_track` → `MISSING_SOURCE_TRACK` error returned
- [ ] Missing `docling_document` in audio input → `MISSING_DOCLING_DOM` error returned

**Out of B1 scope (stubs only):**

| Feature | Phase |
|---|---|
| Specialist OCR routing (tableformer, texify, trocr) | B3 |
| KI-002 and KI-003 mitigations | B3 |
| VLM pipeline (vlm_assisted, vlm_validated tiers) | B4 |
| Graph-based reading order with confidence scoring | B2 |
| Parasitic content detection and flagging | B2 |
| Prometheus metrics and debug overlay images | B4 |

---

## 11. Known Issues (Baked in from Day 1)

Three Docling layout model issues are already characterized. Mitigation hooks in
`processing/mitigations.py` provide stub implementations in B1 that are activated in B3
without touching assembly logic.

| Issue | Severity | Phase | Reference |
|---|---|---|---|
| KI-002: Multi-column text misclassified as Table | HIGH | B3 | `docs/known_issues/KI-002-docling-table-multicolumn.md` |
| KI-003: Dense text misclassified as Picture | MEDIUM | B3 | `docs/known_issues/KI-003-docling-picture-dense-text.md` |
| KI-008: Table misclassification corrupts reading order (downstream of KI-002) | HIGH | B3 | `docs/known_issues/KI-008-docling-multicolumn-text-extraction.md` |
