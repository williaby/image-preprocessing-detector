---
schema_type: common
title: "Chunk to Application Embedding Contract"
description: "Mandatory interface contract defining what Chunk must produce and what all
  per-application embedding implementations must accept and preserve."
tags:
- pipeline
- integration
- contract
- embedding
- rag_pipeline
status: active
owner: core-maintainer
purpose: "Define the complete interface contract between Chunk (foundry-chunk) and all
  per-application embedding implementations. Embedding is not a shared service, but the
  input interface is standardized across all AI applications."
---

**Version:** 1.0.0 | **Status:** Active | **Last Updated:** 2026-02

## Executive Summary

This document defines the interface contract between:

- **Chunk** (`foundry-chunk`, Upstream): Trust scoring, semantic chunking, RAGChunkSet assembly
- **Application Embedding** (Downstream): Per-application — each AI application implements
  its own embedding component

**Embedding is NOT a shared foundry service.** There is no `foundry-embed` repository. Instead,
each AI application that requires retrieval implements its own embedding component. However, ALL
such implementations MUST conform to this contract — they must accept the `RAGChunkSet` artifact
from Chunk and preserve the required metadata fields in their vector store entries.

**This is an interface contract, not a service contract.**

---

## 1. Architecture Overview

```text
┌──────────────────────────────────────────────────────────────┐
│                    CHUNK (foundry-chunk)                      │
│              Trust scoring + RAG chunking                     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Inputs from Unify: DoclingDOM.json + OCR metadata           │
│                                                              │
│  Processing: fusion → trust scoring → chunking strategy      │
│                                                              │
│  OUTPUTS:                                                    │
│  └── RAGChunkSet.json  (GCS: 04-chunks/)                     │
│      └── chunk[] with trust_score, ocr_engine_provenance     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                              │
           ┌──────────────────┴──────────────────┐
           ▼                                     ▼
┌──────────────────────┐            ┌────────────────────────┐
│   AI Application 1   │            │   AI Application 2     │
│   (e.g., tax Q&A)    │            │   (e.g., legal search) │
├──────────────────────┤            ├────────────────────────┤
│ Embedding component  │            │ Embedding component    │
│ (MUST honor contract)│            │ (MUST honor contract)  │
│                      │            │                        │
│ Free to choose:      │            │ Free to choose:        │
│ - Embedding model    │            │ - Embedding model      │
│ - Vector dimensions  │            │ - Vector DB backend    │
│ - Vector DB backend  │            │ - Similarity metric    │
└──────────────────────┘            └────────────────────────┘
```

---

## 2. GCS Artifact Path

```text
Input to application embedding:
gs://rag-pipeline-{env}/{trace_id}/04-chunks/RAGChunkSet.json
```

Each application reads from this GCS path after Chunk writes it. Chunk writes atomically;
applications poll or subscribe via Cloud Workflows completion signals.

---

## 3. RAGChunkSet Schema (What Chunk MUST Produce)

All fields listed here are REQUIRED unless explicitly marked `(optional)`.

### 3.1 Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | String | `"1.0"` — bump if schema changes |
| `document_id` | UUID | Stable document identifier (from Ingest) |
| `trace_id` | UUID | Pipeline execution trace ID |
| `source_track` | String | `"document"` or `"audio"` |
| `chunk_strategy` | String | `"by_title"`, `"token"`, or `"semantic"` |
| `total_chunks` | Integer | Total count of chunks in this set |
| `chunks` | Array | See Section 3.2 |

### 3.2 Per-Chunk Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `chunk_id` | UUID | **REQUIRED** | Stable chunk identifier |
| `document_id` | UUID | **REQUIRED** | Parent document ID |
| `trace_id` | UUID | **REQUIRED** | Pipeline trace ID |
| `text` | String | **REQUIRED** | Chunk text content |
| `page_range` | `[int, int]` | **REQUIRED** | `[start_page, end_page]` (1-indexed) |
| `section_hierarchy` | Array\<String\> | **REQUIRED** | Heading path, e.g., `["Chapter 2", "Section 2.1"]` |
| `trust_score` | Float 0-1 | **REQUIRED** | Derived from Prepare-Doc IQA metrics + Unify OCR confidence |
| `ocr_engine_provenance` | String | **REQUIRED** | OCR engine used (e.g., `"docling"`, `"tesseract"`), rooted in Prepare-Doc routing decision |
| `chunk_strategy` | String | **REQUIRED** | Strategy used for this specific chunk |
| `token_count` | Integer | **REQUIRED** | Token count (cl100k_base tokenizer) |
| `source_track` | String | **REQUIRED** | `"document"` or `"audio"` |
| `hallucination_risk` | Float 0-1 | **REQUIRED** | Estimated risk of OCR hallucination |
| `audio_fields` | Object | conditional | Present only when `source_track == "audio"` |

### 3.3 Audio Fields (when `source_track == "audio"`)

| Field | Type | Description |
|-------|------|-------------|
| `start_ms` | Integer | Start timestamp in milliseconds |
| `end_ms` | Integer | End timestamp in milliseconds |
| `speaker_id` | String | Speaker identifier from Prepare-Audio diarization |
| `confidence` | Float 0-1 | Deepgram transcription confidence for this segment |

---

## 4. What Application Embedding MUST Preserve

All per-application embedding implementations MUST store the following fields as queryable
or filterable metadata in their vector store entries. These fields trace quality and
provenance from Prepare-Doc through the entire pipeline.

| Field | Storage Requirement | Reason |
|-------|---------------------|--------|
| `chunk_id` | **Searchable/filterable** | Cross-service lookup; must be able to retrieve chunk by ID |
| `trust_score` | **Stored as metadata; filterable** | Retrieval quality filtering (e.g., exclude chunks below 0.5) |
| `ocr_engine_provenance` | **Stored as metadata** | Audit trail; debug OCR quality issues |
| `document_id` | **Stored as metadata; filterable** | Cross-service traceability |
| `trace_id` | **Stored as metadata** | Pipeline execution tracing |
| `page_range` | **Stored as metadata** | Source citation in retrieval responses |
| `section_hierarchy` | **Stored as metadata** | Section-level navigation |
| `hallucination_risk` | **Stored as metadata; filterable** | Safety filtering in retrieval |

---

## 5. What Application Embedding is Free to Choose

Applications have full discretion over:

| Decision | Options |
|----------|---------|
| Embedding model | OpenAI text-embedding-3-*, Cohere embed-*, local models, etc. |
| Vector dimensions | Any — depends on chosen model |
| Vector DB backend | pgvector, Milvus, Weaviate, Qdrant, Pinecone, etc. |
| Similarity metric | Cosine, dot product, Euclidean |
| Index type | HNSW, IVF, exact — depends on scale |
| Chunk selection | Which chunks to embed vs. skip (e.g., skip very short chunks) |
| Batching strategy | How to batch chunks for embedding API calls |
| Re-embedding policy | When to re-embed on model upgrades |

---

## 6. Trust Score Provenance Chain

The `trust_score` field traces quality signals across three services:

```text
Prepare-Doc IQA assessment
  → IQA scores in DocumentMetadata.json (blur, noise, contrast, etc.)
    → Unify OCR confidence measurement
      → Chunk trust scoring computation
        → trust_score in RAGChunkSet chunk[]
          → MUST be stored in vector store metadata
            → Available for retrieval quality filtering
```

Applications MUST NOT recompute or override `trust_score`. It is a pipeline artifact.

---

## 7. Error Handling

| Scenario | Required Behavior |
|----------|-------------------|
| Missing `trust_score` in RAGChunkSet | Application MUST reject chunk and log ERROR |
| `trust_score` below application threshold | Application MAY skip embedding for that chunk (log WARN) |
| Missing `chunk_id` | Application MUST reject entire RAGChunkSet and alert |
| `source_track == "audio"` but `audio_fields` absent | Application MUST reject chunk and log ERROR |
| Vector store write failure | Application MUST retry (exponential backoff) and log ERROR |

---

## 8. Related Documents

| Document | Description |
|----------|-------------|
| [prepare-doc-unify-contract.md](prepare-doc-unify-contract.md) | Prepare-Doc → Unify handoff |
| [prepare-audio-unify-contract.md](prepare-audio-unify-contract.md) | Prepare-Audio → Unify handoff |
| [ingest-prepare-doc-contract.md](ingest-prepare-doc-contract.md) | Ingest → Prepare-Doc handoff |
| [embed-vectorstore-workflow.puml](../../architecture/diagrams/level-2/downstream-context/embed-vectorstore-workflow.puml) | Contract workflow diagram |
| [ADR-0029](../../ADRs/0029-prepare-doc-scope-boundaries.md) | Prepare-Doc scope boundaries |
