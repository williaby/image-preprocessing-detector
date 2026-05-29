---
schema_type: common
title: "Ingest to Prepare-Audio Contract"
description: "Contract defining the interface between Ingest (rag-processor) and
  Prepare-Audio (audio-processor) for audio and video file processing."
tags:
- pipeline
- integration
- contract
- ingestion
- rag_pipeline
status: active
owner: core-maintainer
purpose: "Define the complete interface contract between Ingest and Prepare-Audio for
  audio/video file ingestion, job lifecycle, and output delivery."
---

**Version:** 1.0.0 | **Status:** Active | **Last Updated:** 2026-02

## Executive Summary

This document defines the interface contract between:

- **Ingest** (`rag-processor`, Upstream): React SPA + FastAPI gateway — receives files
  from users, routes to appropriate processing service, tracks job status
- **Prepare-Audio** (`audio-processor`, Downstream): Audio signal conditioning,
  Deepgram transcription, speaker diarization, DOM assembly

The contract covers:

1. **File Handoff**: Supported audio/video formats and upload mechanisms
2. **Job Request**: API request format for processing jobs
3. **Status Reporting**: Progress and completion callbacks
4. **Output Delivery**: TranscriptMetadata.json location and schema reference

---

## 1. Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│                    INGEST (rag-processor)                      │
│              React SPA + FastAPI + Redis/RQ                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User Upload → File Validation → MIME routing decision          │
│                                                                 │
│  AUDIO/VIDEO FILES:                                             │
│  ├── Upload to GCS: 00-source/{trace_id}/                      │
│  ├── ProcessingRequest JSON (see Section 3)                    │
│  └── POST /api/v1/process to Prepare-Audio FastAPI             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              PREPARE-AUDIO (audio-processor)              │
│         FastAPI + Redis/RQ + AudioConditioner pipeline          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  INPUTS:                                                        │
│  ├── Audio/video file in GCS 00-source/                        │
│  └── ProcessingRequest JSON                                    │
│                                                                 │
│  Processing: FFmpeg → VAD → Quality check → Deepgram → DOM     │
│                                                                 │
│  OUTPUT: TranscriptMetadata.json (GCS: 02-transcribed/)        │
│          → Unify (audio-track mode)                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Supported File Types

### 2.1 Audio Formats (Routed to Prepare-Audio)

| Format | MIME Type | Max Size | Notes |
|--------|-----------|----------|-------|
| WAV | audio/wav | 2GB | Preferred — no conversion needed |
| MP3 | audio/mpeg | 2GB | FFmpeg decode |
| MP4 | video/mp4 | 2GB | FFmpeg audio extraction |
| M4A | audio/mp4 | 2GB | FFmpeg decode |
| FLAC | audio/flac | 2GB | FFmpeg decode |
| OGG | audio/ogg | 2GB | FFmpeg decode |
| WebM | audio/webm | 2GB | FFmpeg audio extraction |
| MOV | video/quicktime | 2GB | FFmpeg audio extraction |
| AVI | video/x-msvideo | 2GB | FFmpeg audio extraction |
| MKV | video/x-matroska | 2GB | FFmpeg audio extraction |

### 2.2 Routing Decision

Ingest routes files to Prepare-Audio when:

- MIME type is `audio/*` or `video/*`
- File extension is in the supported list above
- Magic bytes validation passes (Ingest pre-validates before routing)

All other file types are routed to Prepare-Doc.

---

## 3. Job Request Format

Ingest POSTs to `POST /api/v1/process` on the Prepare-Audio FastAPI service.

### 3.1 Request Body

```json
{
  "document_id": "uuid-v4",
  "trace_id": "uuid-v4",
  "source_gcs_uri": "gs://rag-pipeline-{env}/{trace_id}/00-source/{filename}",
  "output_gcs_prefix": "gs://rag-pipeline-{env}/{trace_id}/02-transcribed/",
  "callback_url": "https://rag-processor.{env}/api/v1/jobs/{trace_id}/status",
  "options": {
    "language": "en",
    "diarization": true,
    "summarization": true,
    "smart_format": true
  }
}
```

### 3.2 Request Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `document_id` | UUID | **REQUIRED** | Stable document identifier assigned by Ingest |
| `trace_id` | UUID | **REQUIRED** | Unique pipeline execution trace identifier |
| `source_gcs_uri` | String | **REQUIRED** | Full GCS URI of the uploaded audio/video file |
| `output_gcs_prefix` | String | **REQUIRED** | GCS prefix where Prepare-Audio writes output |
| `callback_url` | String | **REQUIRED** | Ingest endpoint for status updates |
| `options.language` | String | optional | BCP-47 language code (default: `"en"`) |
| `options.diarization` | Boolean | optional | Enable speaker diarization (default: `true`) |
| `options.summarization` | Boolean | optional | Enable Deepgram summarization (default: `true`) |
| `options.smart_format` | Boolean | optional | Enable Deepgram smart formatting (default: `true`) |

---

## 4. Job Lifecycle

### 4.1 Job States

| State | Description |
|-------|-------------|
| `queued` | Request received, job enqueued in Redis/RQ |
| `validating` | Magic bytes and size validation in progress |
| `conditioning` | AudioConditioner running (FFmpeg, resampling, VAD) |
| `transcribing` | Deepgram Nova-2 API call in progress |
| `assembling` | DOMBuilder constructing Docling DOM |
| `completed` | TranscriptMetadata.json written to GCS |
| `failed` | Processing failed — see error codes (Section 5) |

### 4.2 Status Callbacks

Prepare-Audio POSTs status updates to `callback_url` at each state transition:

```json
{
  "trace_id": "uuid-v4",
  "document_id": "uuid-v4",
  "state": "transcribing",
  "timestamp": "2026-02-22T14:30:00Z",
  "progress_pct": 45,
  "error": null
}
```

On completion, `state == "completed"` and:

```json
{
  "trace_id": "uuid-v4",
  "document_id": "uuid-v4",
  "state": "completed",
  "timestamp": "2026-02-22T14:31:15Z",
  "progress_pct": 100,
  "output_uri": "gs://rag-pipeline-{env}/{trace_id}/02-transcribed/TranscriptMetadata.json",
  "error": null
}
```

---

## 5. Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_FILE_TYPE` | 400 | MIME type not supported or magic bytes invalid |
| `FILE_TOO_LARGE` | 413 | File exceeds 2GB limit |
| `FILE_TOO_SHORT` | 422 | Audio duration below minimum threshold |
| `QUALITY_TOO_LOW` | 422 | SNR, clipping, or speech ratio below threshold |
| `DEEPGRAM_ERROR` | 502 | Deepgram API returned an error response |
| `DEEPGRAM_TIMEOUT` | 504 | Deepgram API call exceeded timeout |
| `GCS_WRITE_ERROR` | 502 | Failed to write output to GCS |
| `INTERNAL_ERROR` | 500 | Unexpected processing failure |

---

## 6. Output

On success, Prepare-Audio writes to:

```text
gs://rag-pipeline-{env}/{trace_id}/02-transcribed/TranscriptMetadata.json
```

The schema of this file is defined in:
[prepare-audio-unify-contract.md](prepare-audio-unify-contract.md) — Section 3.

Ingest receives the `output_uri` in the completion callback and passes it downstream to
Cloud Workflows for Unify processing.

---

## 7. Authentication & Security

| Aspect | Implementation |
|--------|----------------|
| **Ingest → Prepare-Audio** | Service-to-service: Cloud Workflows service account + Cloudflare Access |
| **GCS access** | Service account with `roles/storage.objectAdmin` on `rag-pipeline-*` buckets |
| **Deepgram API key** | Stored in Secret Manager; injected at runtime |
| **Callback authentication** | Ingest validates callback source via shared secret header |

---

## 8. Related Documents

| Document | Description |
|----------|-------------|
| [ingest-prepare-doc-contract.md](ingest-prepare-doc-contract.md) | Document track equivalent |
| [prepare-audio-unify-contract.md](prepare-audio-unify-contract.md) | Prepare-Audio → Unify handoff |
| [prepare-audio-transcription-workflow.puml](../../architecture/diagrams/level-2/downstream-context/prepare-audio-transcription-workflow.puml) | AudioConditioner pipeline diagram |
| **Ingest repo** | [ByronWilliamsCPA/rag-processor](https://github.com/ByronWilliamsCPA/rag-processor) |
| **audio-processor repo** | [ByronWilliamsCPA/audio-processor](https://github.com/ByronWilliamsCPA/audio-processor) |
