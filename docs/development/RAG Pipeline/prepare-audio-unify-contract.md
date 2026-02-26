---
schema_type: common
title: "Prepare-Audio to Unify Contract"
description: "Contract defining the interface between Prepare-Audio (audio-processor)
  and Unify for the audio track of the RAG pipeline."
tags:
- pipeline
- integration
- contract
- ingestion
- rag_pipeline
status: active
owner: core-maintainer
purpose: "Define the complete interface contract between Prepare-Audio and Unify for
  audio-derived content. Unify MUST NOT run OCR for audio-track inputs."
---

**Version:** 1.0.0 | **Status:** Active | **Last Updated:** 2026-02

## Executive Summary

This document defines the interface contract between:

- **Prepare-Audio** (`foundry-prepare-audio`, Upstream): Audio signal conditioning,
  Deepgram Nova-2 transcription, speaker diarization, and Docling DOM assembly
- **Unify** (`foundry-unify`, Downstream): Docling DOM unification — skips OCR for
  audio-derived content; performs DOM normalization only

**Key architectural constraint**: Unify MUST NOT run OCR engines when receiving
audio-derived content. It reads `source_track: "audio"` from `TranscriptMetadata.json`
and branches to DOM-unification-only mode.

---

## 1. Architecture Overview

```text
┌───────────────────────────────────────────────────────────────┐
│              PREPARE-AUDIO (foundry-prepare-audio)            │
│         Audio signal conditioning + Deepgram transcription    │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  Inputs: audio/video files from GCS 00-source/               │
│                                                               │
│  Processing pipeline (ADR-002 AudioConditioner):             │
│  FFmpeg → 16kHz PCM → Silero VAD → RMS normalize →           │
│  QualityAssessor → Deepgram Nova-2 → DOMBuilder              │
│                                                               │
│  OUTPUTS:                                                     │
│  └── TranscriptMetadata.json (GCS: 02-transcribed/)          │
│      ├── source_track: "audio"                               │
│      ├── docling_document (pre-assembled DOM)                │
│      └── audio_quality, speakers[], transcription            │
│                                                               │
└───────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────┐
│                    UNIFY (foundry-unify)                      │
│              Docling DOM unification (audio-track mode)       │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  AUDIO-TRACK MODE: skip all OCR engines                      │
│  Read source_track == "audio" → extract docling_document     │
│  Normalize DOM to unified schema                             │
│  Apply any cross-document metadata enrichment                │
│                                                               │
│  OUTPUT: DoclingDOM.json (GCS: 03-docling-dom/)              │
│  (same schema as document-track output — feeds Chunk)        │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

---

## 2. GCS Artifact Paths

```text
Prepare-Audio writes to:
  gs://rag-pipeline-{env}/{trace_id}/02-transcribed/TranscriptMetadata.json

Unify reads from:
  gs://rag-pipeline-{env}/{trace_id}/02-transcribed/TranscriptMetadata.json

Unify writes to (same schema as document track):
  gs://rag-pipeline-{env}/{trace_id}/03-docling-dom/DoclingDOM.json
```

---

## 3. TranscriptMetadata.json Schema (What Prepare-Audio MUST Produce)

### 3.1 Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `document_id` | UUID | **REQUIRED** | Stable document identifier (from Ingest) |
| `trace_id` | UUID | **REQUIRED** | Pipeline execution trace ID |
| `source_track` | String | **REQUIRED** | MUST be `"audio"` — signals Unify to skip OCR |
| `source_file` | String | **REQUIRED** | GCS URI of original audio/video file |
| `audio_properties` | Object | **REQUIRED** | See Section 3.2 |
| `audio_quality` | Object | **REQUIRED** | See Section 3.3 |
| `deepgram_metadata` | Object | **REQUIRED** | See Section 3.4 |
| `transcription` | Object | **REQUIRED** | See Section 3.5 |
| `speakers` | Array | **REQUIRED** | See Section 3.6 |
| `summary` | String | optional | AI-generated summary from Deepgram summarization v2 |
| `docling_document` | Object | **REQUIRED** | Pre-assembled Docling DOM (see Section 4) |

### 3.2 audio_properties

| Field | Type | Description |
|-------|------|-------------|
| `duration_seconds` | Float | Total audio duration |
| `sample_rate_hz` | Integer | Sample rate after conditioning (16000) |
| `channels` | Integer | Channel count after conditioning (1 = mono) |
| `format` | String | Original container format (e.g., `"mp4"`, `"wav"`, `"mp3"`) |

### 3.3 audio_quality

| Field | Type | Description |
|-------|------|-------------|
| `snr_db` | Float | Signal-to-noise ratio in dB |
| `clipping_ratio` | Float 0-1 | Fraction of samples at clipping threshold |
| `silence_ratio` | Float 0-1 | Fraction of audio that is silence |
| `speech_ratio` | Float 0-1 | Fraction of audio with detected speech |

### 3.4 deepgram_metadata

| Field | Type | Description |
|-------|------|-------------|
| `model` | String | Deepgram model used (e.g., `"nova-2"`) |
| `language` | String | Detected language code |
| `confidence` | Float 0-1 | Overall transcription confidence |
| `processing_time_seconds` | Float | Deepgram API processing time |

### 3.5 transcription

| Field | Type | Description |
|-------|------|-------------|
| `full_text` | String | Complete transcript text |
| `utterances` | Array | Per-utterance details (see below) |

**Utterance fields**:

| Field | Type | Description |
|-------|------|-------------|
| `start_ms` | Integer | Start timestamp in milliseconds |
| `end_ms` | Integer | End timestamp in milliseconds |
| `text` | String | Utterance text |
| `speaker_id` | String | Speaker identifier |
| `confidence` | Float 0-1 | Per-utterance confidence |
| `words` | Array | Per-word timing (optional) |

### 3.6 speakers

| Field | Type | Description |
|-------|------|-------------|
| `id` | String | Speaker identifier (e.g., `"speaker_0"`) |
| `label` | String | Human-readable label (e.g., `"Speaker 1"`) |
| `speaking_time_seconds` | Float | Total speaking time for this speaker |

---

## 4. Docling DOM (Pre-Assembled by DOMBuilder)

Prepare-Audio pre-assembles the Docling DOM before writing `TranscriptMetadata.json`.
Unify MUST use this pre-assembled DOM as-is (after normalization) rather than running
its own DOM construction for audio content.

### DOM Element Mapping

| Audio Element | Docling DOM Type | Key Fields |
|---------------|------------------|------------|
| Speaker turn | `SectionItem` | `speaker_id`, `speaker_label` |
| Utterance | `TextItem` | `start_ms`, `end_ms`, `confidence`, `playback_url` |
| Summary | `SectionItem` | `is_summary: true`, rendered at top of DOM |

---

## 5. Unify Behavioral Requirements for Audio Track

| Requirement | Description |
|-------------|-------------|
| **Skip OCR** | Unify MUST NOT run Docling, Tesseract, or any OCR engine for audio-track inputs |
| **Read source_track** | Unify MUST check `source_track` before processing and branch accordingly |
| **Use pre-assembled DOM** | Unify MUST extract `docling_document` from TranscriptMetadata and use it as the DOM source |
| **Normalize schema** | Unify MUST normalize the Docling DOM to the same schema used for document-track outputs |
| **Quality flag** | If `audio_quality.snr_db` is below threshold, Unify MUST add a quality warning flag to the DoclingDOM metadata (not reject) |
| **Preserve trace_id** | Unify MUST carry `trace_id` from TranscriptMetadata into DoclingDOM.json |

---

## 6. Error Handling

| Scenario | Required Behavior |
|----------|-------------------|
| Missing `source_track` field | Unify MUST reject with `MISSING_SOURCE_TRACK` error |
| `source_track` is not `"audio"` | Process as document track (different code path) |
| Missing `docling_document` | Unify MUST reject with `MISSING_DOCLING_DOM` error |
| `audio_quality.snr_db` below threshold | Unify MUST add quality warning to DoclingDOM, continue processing |
| Missing `transcription.full_text` | Unify MUST reject with `EMPTY_TRANSCRIPT` error |

---

## 7. Related Documents

| Document | Description |
|----------|-------------|
| [prepare-doc-unify-contract.md](prepare-doc-unify-contract.md) | Document track equivalent |
| [ingest-prepare-audio-contract.md](ingest-prepare-audio-contract.md) | Ingest → Prepare-Audio handoff |
| [prepare-audio-transcription-workflow.puml](../../architecture/diagrams/level-2/downstream-context/prepare-audio-transcription-workflow.puml) | AudioConditioner pipeline diagram |
| **audio-processor repo** | [ByronWilliamsCPA/audio-processor](https://github.com/ByronWilliamsCPA/audio-processor) |
| **ADR-002** (audio-processor) | AudioConditioner 7-stage pipeline design |
