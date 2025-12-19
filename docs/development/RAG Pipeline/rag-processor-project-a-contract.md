---
schema_type: common
title: "RAG Processor → Project A Interface Contract"
description: "Contract defining the interface between rag-processor (upstream UI) and Project A (image_detection)"
tags:
  - pipeline
  - integration
  - contract
  - api
status: draft
owner: core-maintainer
purpose: "Define the complete interface contract between rag-processor and Project A for document ingestion and processing."
version: 1.1.0
reviewed_by: "Multi-model consensus (Gemini 2.5 Pro, GPT-4.1)"
---

# RAG Processor → Project A Interface Contract

**Version:** 1.1.0 | **Status:** Draft | **Last Updated:** 2025-12

> **Review Status**: Evaluated by Level 3 expert consensus. Critical security and reliability improvements applied.

## Executive Summary

This document defines the interface contract between:

- **RAG Processor** (Upstream): React + FastAPI full-stack application providing document upload UI and job orchestration
- **Project A** (Downstream): Document preprocessing, IQA assessment, corrections, and routing metadata generation

The contract covers:

1. **File Handoff**: Supported file types and upload mechanisms
2. **Job Request**: API request format for processing jobs
3. **Status Reporting**: Progress and completion callbacks
4. **Output Delivery**: Processed document metadata and corrected images

---

## 1. Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                         RAG PROCESSOR                                    │
│                    (React Frontend + FastAPI Backend)                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  User Upload → File Validation → Job Queue → Processing Router          │
│                                                                         │
│  OUTPUTS TO PROJECT A:                                                  │
│  ├── Raw document file (PDF, image, Office)                            │
│  ├── ProcessingRequest JSON                                            │
│  └── Callback URL for status updates                                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                         ┌──────────┴──────────┐
                         │                     │
                         ▼                     ▼
┌────────────────────────────────┐   ┌────────────────────────────────┐
│          PROJECT A             │   │     AUDIO PROCESSOR            │
│   (image_detection)            │   │   (parallel pipeline)          │
├────────────────────────────────┤   ├────────────────────────────────┤
│                                │   │                                │
│  INPUTS:                       │   │  INPUTS:                       │
│  ├── PDF, PNG, JPEG, TIFF      │   │  ├── MP3, WAV, M4A, etc.       │
│  ├── DOCX, XLSX, PPTX          │   │  └── ProcessingRequest JSON    │
│  └── ProcessingRequest JSON    │   │                                │
│                                │   │                                │
│  Processing:                   │   │  Processing:                   │
│  IQA → Corrections → Layout    │   │  Transcription → Diarization   │
│                                │   │                                │
│  OUTPUT: DocumentMetadata.json │   │  OUTPUT: TranscriptMetadata    │
│          + Corrected Images    │   │          + Transcript files    │
│          → Project B           │   │          → Downstream          │
│                                │   │                                │
└────────────────────────────────┘   └────────────────────────────────┘
```

---

## 2. Supported File Types

### 2.1 Document Types (Routed to Project A)

| MIME Type | Extensions | Max Size | Notes |
|-----------|------------|----------|-------|
| `application/pdf` | `.pdf` | 100 MB | Primary document format |
| `image/png` | `.png` | 50 MB | Single-page images |
| `image/jpeg` | `.jpg`, `.jpeg` | 50 MB | Single-page images |
| `image/tiff` | `.tif`, `.tiff` | 100 MB | Multi-page supported |
| `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | `.docx` | 50 MB | Word documents |
| `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | `.xlsx` | 50 MB | Excel spreadsheets |
| `application/vnd.openxmlformats-officedocument.presentationml.presentation` | `.pptx` | 100 MB | PowerPoint presentations |

### 2.2 Audio Types (Routed to Audio Processor - NOT Project A)

| MIME Type | Extensions | Routing |
|-----------|------------|---------|
| `audio/*` | `.mp3`, `.wav`, `.m4a`, etc. | Audio Processor |

### 2.3 File Validation Requirements

RAG Processor MUST validate before routing to Project A:

```python
# Required validation before handoff
VALIDATION_RULES = {
    "max_file_size_mb": 100,
    "max_pages_pdf": 500,
    "min_resolution_dpi": 72,  # Project A will upscale if < 300 DPI
    "allowed_mime_types": [
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/tiff",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ],
    "reject_encrypted_pdf": True,
    "reject_password_protected": True,
}
```

---

## 3. Job Request Format

### 3.1 ProcessingRequest Schema

RAG Processor sends this JSON payload when submitting a document for processing:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ProcessingRequest",
  "version": "1.0.0",
  "type": "object",
  "required": [
    "request_id",
    "tenant_id",
    "document_id",
    "file_location",
    "mime_type",
    "callback_url",
    "created_at"
  ],
  "properties": {
    "request_id": {
      "type": "string",
      "format": "uuid",
      "description": "Client-generated unique identifier. Used as IDEMPOTENCY KEY - safe to retry with same request_id"
    },
    "tenant_id": {
      "type": "string",
      "minLength": 1,
      "description": "Tenant identifier for rate limiting, access control, and metrics. REQUIRED for multi-tenancy."
    },
    "document_id": {
      "type": "string",
      "minLength": 1,
      "description": "User-facing document identifier"
    },
    "file_location": {
      "type": "object",
      "required": ["type", "path"],
      "properties": {
        "type": {
          "type": "string",
          "enum": ["local", "gcs", "s3", "url"],
          "description": "Storage type for the source file"
        },
        "path": {
          "type": "string",
          "description": "Path or URL to the source file"
        },
        "credentials_ref": {
          "type": "string",
          "description": "Reference to credentials secret (for cloud storage)"
        }
      }
    },
    "mime_type": {
      "type": "string",
      "description": "MIME type of the source file"
    },
    "file_size_bytes": {
      "type": "integer",
      "minimum": 1,
      "description": "File size in bytes"
    },
    "original_filename": {
      "type": "string",
      "description": "Original filename as uploaded by user"
    },
    "callback_url": {
      "type": "string",
      "format": "uri",
      "description": "URL for status updates and completion notification"
    },
    "output_location": {
      "type": "object",
      "properties": {
        "type": {
          "type": "string",
          "enum": ["local", "gcs", "s3"]
        },
        "base_path": {
          "type": "string",
          "description": "Base path for output files"
        }
      }
    },
    "processing_options": {
      "$ref": "#/definitions/ProcessingOptions"
    },
    "metadata": {
      "type": "object",
      "description": "User-provided metadata to pass through",
      "additionalProperties": true
    },
    "priority": {
      "type": "string",
      "enum": ["low", "default", "high"],
      "default": "default"
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    }
  },
  "definitions": {
    "ProcessingOptions": {
      "type": "object",
      "properties": {
        "apply_corrections": {
          "type": "boolean",
          "default": true,
          "description": "Apply automatic image corrections (deskew, CLAHE, etc.)"
        },
        "target_dpi": {
          "type": "integer",
          "default": 300,
          "minimum": 150,
          "maximum": 600,
          "description": "Target DPI for output images"
        },
        "skip_layout_detection": {
          "type": "boolean",
          "default": false,
          "description": "Skip layout-lite detection (faster processing)"
        },
        "force_ocr_routing": {
          "type": "string",
          "enum": ["ocr_fast", "ocr_advanced", "vision_simple", "vision_structured"],
          "description": "Override automatic OCR routing recommendation"
        },
        "page_range": {
          "type": "object",
          "properties": {
            "start": {"type": "integer", "minimum": 1},
            "end": {"type": "integer", "minimum": 1}
          },
          "description": "Process only specified page range. CONSTRAINT: end >= start. If end > doc pages, process to last page."
        },
        "on_partial_failure": {
          "type": "string",
          "enum": ["proceed", "fail"],
          "default": "proceed",
          "description": "Behavior when some pages fail: 'proceed' continues with successful pages, 'fail' aborts entire job"
        },
        "extract_embedded_images": {
          "type": "boolean",
          "default": true,
          "description": "Extract and process images embedded in Office documents"
        }
      }
    }
  }
}
```

### 3.2 Example Request

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "tenant_acme_corp",
  "document_id": "doc_2024_annual_report",
  "file_location": {
    "type": "gcs",
    "path": "gs://rag-processor-uploads/2024/12/annual_report.pdf",
    "credentials_ref": "gcs-service-account"
  },
  "mime_type": "application/pdf",
  "file_size_bytes": 15728640,
  "original_filename": "2024_Annual_Report.pdf",
  "callback_url": "https://api.rag-processor.example.com/webhooks/processing-status",
  "output_location": {
    "type": "gcs",
    "base_path": "gs://rag-processor-outputs/processed/"
  },
  "processing_options": {
    "apply_corrections": true,
    "target_dpi": 300,
    "extract_embedded_images": true
  },
  "metadata": {
    "user_id": "user_123",
    "project_id": "proj_456",
    "tags": ["financial", "annual-report"]
  },
  "priority": "high",
  "created_at": "2024-12-19T10:30:00Z"
}
```

---

## 4. Communication Protocols

### 4.1 Job Submission

**Option A: REST API (Synchronous)**

```http
POST /api/v1/process HTTP/1.1
Host: project-a.internal:8080
Content-Type: application/json
Authorization: Bearer <service-token>

{ProcessingRequest JSON}
```

**Response:**

```json
{
  "job_id": "job_abc123",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "estimated_wait_seconds": 30,
  "queue_position": 5
}
```

**Option B: Message Queue (Asynchronous - Recommended)**

```python
# RAG Processor publishes to Redis/RabbitMQ queue
queue_name = "project-a.processing.{priority}"  # high, default, low

message = {
    "type": "processing_request",
    "payload": ProcessingRequest,
    "timestamp": "2024-12-19T10:30:00Z"
}
```

### 4.2 Status Updates (Callbacks)

Project A sends **authenticated** status updates to the `callback_url`:

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "job_id": "job_abc123",
  "status": "processing",
  "progress": {
    "current_page": 5,
    "total_pages": 20,
    "phase": "iqa_analysis",
    "percent_complete": 25
  },
  "updated_at": "2024-12-19T10:31:00Z"
}
```

**Callback Authentication (REQUIRED):**

All callbacks MUST include HMAC signature for verification:

```http
POST {callback_url} HTTP/1.1
Content-Type: application/json
X-Webhook-Signature: sha256=<hmac_signature>
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
X-Timestamp: 1703001600
```

**Signature Generation:**

```python
import hmac
import hashlib
import json

def sign_callback(payload: dict, secret: str, timestamp: int) -> str:
    """Generate HMAC-SHA256 signature for callback."""
    message = f"{timestamp}.{json.dumps(payload, sort_keys=True)}"
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"
```

**RAG Processor MUST verify:**

1. `X-Webhook-Signature` matches computed HMAC
2. `X-Timestamp` is within 5 minutes of current time (replay protection)
3. `X-Request-ID` matches a known pending request

### 4.3 Callback Retry Policy

If callback delivery fails, Project A MUST retry with exponential backoff:

| Attempt | Delay | Total Elapsed |
|---------|-------|---------------|
| 1 | Immediate | 0s |
| 2 | 5s | 5s |
| 3 | 15s | 20s |
| 4 | 60s | 80s |
| 5 | 300s | 380s |
| 6+ | Give up, publish to DLQ | — |

**Dead Letter Queue**: Failed callbacks after max retries are published to `project-a.callbacks.dlq` for manual investigation.

```json
{
  "original_callback": { /* full callback payload */ },
  "failure_reason": "Connection refused",
  "attempts": 6,
  "first_attempt_at": "2024-12-19T10:31:00Z",
  "last_attempt_at": "2024-12-19T10:37:20Z"
}
```

**Status Values:**

| Status | Description |
|--------|-------------|
| `queued` | Request received, waiting in queue |
| `processing` | Actively processing |
| `completed` | Processing finished successfully |
| `failed` | Processing failed (see `error` field) |
| `partial_failure` | Some pages failed, others succeeded |

### 4.4 Completion Notification

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "job_id": "job_abc123",
  "status": "completed",
  "result": {
    "metadata_location": "gs://rag-processor-outputs/processed/doc_abc123/metadata.json",
    "output_directory": "gs://rag-processor-outputs/processed/doc_abc123/",
    "num_pages_processed": 20,
    "processing_time_seconds": 45.2,
    "ocr_routing_recommendation": "ocr_advanced",
    "quality_summary": {
      "overall_quality": 0.82,
      "degradation_score": 0.18,
      "pages_corrected": 3
    }
  },
  "completed_at": "2024-12-19T10:31:45Z"
}
```

---

## 5. Output Format

### 5.1 Output Directory Structure

Project A produces output conforming to the Project A → Project B contract:

```text
{output_base_path}/{document_id}/
├── metadata.json           # DocumentMetadata (see schema.py)
├── page_0000.png           # Corrected page image (300 DPI)
├── page_0001.png
├── ...
└── processing_log.json     # Detailed processing log (optional)
```

### 5.2 DocumentMetadata Schema

See [schema.py](../../../src/image_preprocessing_detector/schema.py) for the complete Pydantic models. Key fields relevant to RAG Processor:

```python
class DocumentMetadata(BaseModel):
    document_id: str                    # Matches request document_id
    file_name: str                      # Original filename
    source_mime: str                    # MIME type
    document_type: DocumentType         # image/pdf/office_*
    num_pages: int

    # Quality metrics for UI display
    dqs: DQSMetadata | None             # Document Quality Score
    pre_ocr_risk: float | None          # 0-1 risk score

    # Routing for Project B
    pdf_type: PDFType | None            # image_only/born_digital/hybrid
    ocr_routing_recommendation: OCRRoutingStrategy | None

    # Per-page details
    pages: list[PageMetadata]
    page_layout_summary: list[PageLayoutSummary]
```

### 5.3 Summary for UI Display

RAG Processor can extract these fields for user display:

```json
{
  "document_id": "doc_abc123",
  "original_filename": "2024_Annual_Report.pdf",
  "status": "completed",
  "summary": {
    "num_pages": 20,
    "document_type": "pdf",
    "pdf_type": "born_digital",
    "overall_quality": 0.85,
    "quality_grade": "A",
    "issues_detected": 3,
    "corrections_applied": 2,
    "routing": "ocr_fast",
    "estimated_ocr_difficulty": "low"
  },
  "ready_for_ocr": true,
  "next_step": "project_b"
}
```

---

## 6. Error Handling

### 6.1 Error Response Format

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "job_id": "job_abc123",
  "status": "failed",
  "error": {
    "code": "FILE_CORRUPT",
    "message": "PDF file is corrupted and cannot be read",
    "details": {
      "exception": "PyMuPDF.fitz.FileDataError",
      "page": null,
      "recoverable": false
    }
  },
  "failed_at": "2024-12-19T10:30:05Z"
}
```

### 6.2 Error Codes

| Code | HTTP Status | Description | RAG Processor Action |
|------|-------------|-------------|----------------------|
| `FILE_NOT_FOUND` | 404 | Source file not accessible | Verify file location, retry |
| `FILE_CORRUPT` | 422 | File is corrupted | Notify user, request re-upload |
| `FILE_ENCRYPTED` | 422 | PDF is password-protected | Notify user, request password |
| `FILE_TOO_LARGE` | 413 | File exceeds size limit | Notify user, split document |
| `UNSUPPORTED_FORMAT` | 415 | MIME type not supported | Route to different processor |
| `PROCESSING_TIMEOUT` | 504 | Processing exceeded timeout | Retry with higher priority |
| `INTERNAL_ERROR` | 500 | Unexpected error | Retry, alert ops if persistent |
| `RATE_LIMITED` | 429 | Too many requests | Back off, retry later |

### 6.3 Partial Failure Handling

For multi-page documents where some pages fail:

```json
{
  "status": "partial_failure",
  "result": {
    "metadata_location": "gs://outputs/doc_abc123/metadata.json",
    "num_pages_processed": 18,
    "num_pages_failed": 2,
    "failed_pages": [
      {"page_index": 5, "error": "Image extraction failed"},
      {"page_index": 12, "error": "IQA timeout"}
    ]
  },
  "proceed_with_available": true
}
```

### 6.4 Job Cancellation

Jobs can be cancelled via `DELETE /api/v1/jobs/{job_id}`:

```http
DELETE /api/v1/jobs/job_abc123 HTTP/1.1
Authorization: Bearer <service-token>
X-Tenant-ID: tenant_acme_corp
```

**Response:**

```json
{
  "job_id": "job_abc123",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "cancelling",
  "message": "Cancellation requested, job will stop at next checkpoint"
}
```

**Cancellation State Machine:**

```text
queued ──────► cancelled (immediate)
processing ──► cancelling ──► cancelled (at next page boundary)
completed ───► (cannot cancel)
failed ──────► (cannot cancel)
```

**Callback on Cancellation:**

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "job_id": "job_abc123",
  "status": "cancelled",
  "result": {
    "pages_processed_before_cancel": 5,
    "cancelled_at": "2024-12-19T10:31:00Z",
    "cancelled_by": "user_request"
  }
}
```

---

## 7. Authentication & Security

### 7.1 Service-to-Service Authentication

```yaml
# Required headers
Authorization: Bearer <jwt-service-token>
X-Request-ID: <uuid>  # For tracing
X-Correlation-ID: <uuid>  # Links to user session
X-Tenant-ID: <tenant_id>  # Must match request body tenant_id
```

### 7.2 Token Claims

```json
{
  "iss": "rag-processor",
  "sub": "service:rag-processor",
  "aud": "project-a",
  "tenant_id": "tenant_acme_corp",
  "exp": 1703001600,
  "permissions": ["submit_job", "cancel_job", "read_status"]
}
```

**Tenant Validation**: The `tenant_id` in JWT claims MUST match the `tenant_id` in request body. Mismatches are rejected with `403 Forbidden`.

### 7.3 URL Validation (SSRF Protection)

**CRITICAL**: All URLs (`file_location.path`, `callback_url`) MUST be validated to prevent SSRF attacks.

```python
# Project A URL validation rules
URL_VALIDATION = {
    # Allowed schemes
    "allowed_schemes": ["https"],  # HTTP rejected

    # Blocked IP ranges (RFC 1918 + loopback)
    "blocked_ip_ranges": [
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "127.0.0.0/8",
        "169.254.0.0/16",  # Link-local
        "::1/128",         # IPv6 loopback
        "fc00::/7",        # IPv6 private
    ],

    # Callback URL must be in allowlist
    "callback_domain_allowlist": [
        "api.rag-processor.example.com",
        "webhooks.rag-processor.example.com",
    ],

    # File location validation
    "file_location_rules": {
        "gcs": {"bucket_prefix": "rag-processor-"},
        "s3": {"bucket_prefix": "rag-processor-"},
        "url": "BLOCKED",  # External URLs rejected by default
        "local": {"allowed_paths": ["/data/uploads/"]},
    },
}
```

**Validation Errors:**

| Scenario | Error Code | Message |
|----------|------------|---------|
| HTTP scheme | `INVALID_URL` | "HTTPS required for all URLs" |
| Internal IP | `SSRF_BLOCKED` | "Internal IP addresses not allowed" |
| Callback domain not in allowlist | `INVALID_CALLBACK` | "Callback domain not authorized" |
| Blocked file_location type | `UNSUPPORTED_LOCATION` | "URL file locations disabled" |

### 7.4 Credential Resolution

The `credentials_ref` field references secrets stored in a secrets manager:

```python
# Credential resolution contract
CREDENTIAL_RESOLUTION = {
    # Secrets manager integration
    "provider": "google-secret-manager",  # or "aws-secrets-manager", "hashicorp-vault"

    # Reference format
    "format": "projects/{project}/secrets/{secret_name}/versions/latest",

    # Example resolution
    "gcs-service-account": "projects/rag-processor/secrets/gcs-service-account/versions/latest",

    # Access control
    "project_a_service_account": "project-a@rag-processor.iam.gserviceaccount.com",

    # Credential types supported
    "types": ["service_account_json", "api_key", "oauth_token"],
}
```

**Project A MUST**:

1. Resolve `credentials_ref` via configured secrets manager
2. Use short-lived credentials (1 hour max)
3. Never log credential values
4. Validate credential has access to specified path

### 7.5 Data Security Requirements

| Requirement | Implementation |
|-------------|----------------|
| Data in transit | TLS 1.3 required |
| Data at rest | GCS/S3 encryption (AES-256) |
| Credential isolation | Secrets manager references only |
| PII handling | No PII in logs, metadata only |
| Retention | 30 days default, configurable per tenant |
| Audit logging | All access logged with tenant_id, request_id |

### 7.6 Content Validation (Malware Protection)

Before processing, Project A SHOULD validate file content:

```python
CONTENT_VALIDATION = {
    # Magic byte validation (don't trust MIME type header)
    "validate_magic_bytes": True,

    # Malware scanning (if available)
    "malware_scan": {
        "enabled": True,
        "provider": "clamav",  # or cloud-based scanner
        "on_detection": "reject",  # or "quarantine"
    },

    # PDF-specific checks
    "pdf_checks": {
        "reject_javascript": True,
        "reject_launch_actions": True,
        "max_nested_objects": 100,
    },
}
```

---

## 8. Rate Limits & Quotas

### 8.1 Default Limits

| Resource | Limit | Window |
|----------|-------|--------|
| Requests per tenant | 100 | per minute |
| Concurrent jobs | 10 | active |
| Total pages per hour | 1000 | per tenant |
| File size | 100 MB | per request |

### 8.2 Priority Queues

| Priority | Queue | Max Wait | Use Case |
|----------|-------|----------|----------|
| `high` | Dedicated | 30s | Interactive user waiting |
| `default` | Shared | 5m | Normal processing |
| `low` | Batch | 30m | Background/bulk jobs |

---

## 9. Monitoring & Observability

### 9.1 Required Metrics (Project A → RAG Processor)

```python
# Metrics exposed at /metrics endpoint
metrics = {
    # Job metrics (with tenant labels for multi-tenancy)
    "project_a_jobs_total": Counter(
        "Total jobs processed",
        labels=["tenant_id", "status", "mime_type", "priority"]
    ),
    "project_a_processing_seconds": Histogram(
        "Processing time per job",
        labels=["tenant_id", "document_type"],
        buckets=[1, 5, 10, 30, 60, 120, 300, 600]
    ),
    "project_a_pages_processed": Counter(
        "Total pages processed",
        labels=["tenant_id"]
    ),

    # Queue metrics
    "project_a_queue_depth": Gauge(
        "Current queue depth",
        labels=["priority"]
    ),
    "project_a_active_jobs": Gauge(
        "Currently processing jobs",
        labels=["tenant_id"]
    ),

    # Callback metrics (for reliability monitoring)
    "project_a_callbacks_total": Counter(
        "Total callbacks sent",
        labels=["tenant_id", "status", "attempt"]
    ),
    "project_a_callback_latency_seconds": Histogram(
        "Callback delivery latency",
        labels=["tenant_id"],
        buckets=[0.1, 0.5, 1, 2, 5, 10, 30]
    ),
    "project_a_callback_failures": Counter(
        "Failed callback deliveries",
        labels=["tenant_id", "error_type"]
    ),

    # Error metrics
    "project_a_errors_total": Counter(
        "Total errors",
        labels=["tenant_id", "error_code"]
    ),
}
```

### 9.2 Distributed Tracing

All requests MUST propagate trace context for end-to-end debugging:

```yaml
# Required trace headers (W3C Trace Context)
traceparent: 00-<trace_id>-<span_id>-01
tracestate: rag-processor=<parent_span>

# Custom correlation headers
X-Request-ID: <uuid>        # Unique per request, client-generated
X-Correlation-ID: <uuid>    # User session ID, spans multiple requests
X-Tenant-ID: <tenant_id>    # For tenant isolation
```

**Trace ID propagation**: Project A MUST include trace IDs in:

- All log entries
- Callback requests to RAG Processor
- Downstream calls to storage/secrets manager
- Messages published to queues

### 9.3 Structured Logging

```json
{
  "timestamp": "2024-12-19T10:30:00Z",
  "level": "info",
  "service": "project-a",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "correlation_id": "user-session-xyz",
  "tenant_id": "tenant_acme_corp",
  "event": "processing_started",
  "document_id": "doc_abc123",
  "num_pages": 20,
  "mime_type": "application/pdf"
}
```

**Required log events:**

| Event | Level | When |
|-------|-------|------|
| `job_received` | info | Request accepted |
| `processing_started` | info | Processing begins |
| `page_processed` | debug | Each page complete |
| `processing_completed` | info | Job finished |
| `processing_failed` | error | Job failed |
| `callback_sent` | info | Callback delivered |
| `callback_failed` | warn | Callback delivery failed |
| `security_violation` | error | SSRF, auth failure, etc. |

### 9.4 Health Checks

```http
GET /health/live HTTP/1.1
# Returns 200 if service is running

GET /health/ready HTTP/1.1
# Returns 200 if service can accept new jobs
# Returns 503 if queue is full or dependencies unavailable
```

---

## 10. Versioning & Compatibility

### 10.1 API Versioning

- URL path versioning: `/api/v1/process`, `/api/v2/process`
- Header versioning: `Accept: application/vnd.project-a.v1+json`

### 10.2 Schema Versioning

| Version | Status | Breaking Changes |
|---------|--------|-----------------|
| 1.0.0 | Current | Initial release |

### 10.3 Deprecation Policy

- 6-month notice for breaking changes
- Maintain previous version for 12 months after deprecation
- Compatibility mode for field additions

---

## 11. Testing Requirements

### 11.1 Integration Test Cases

- [ ] Submit PDF → receive completion callback
- [ ] Submit image → receive completion callback
- [ ] Submit Office document → embedded images extracted
- [ ] Submit corrupt file → receive error callback
- [ ] Submit encrypted PDF → receive appropriate error
- [ ] Cancel in-progress job → job stops, callback sent
- [ ] Submit with page range → only specified pages processed
- [ ] Priority handling → high priority processed first

### 11.2 End-to-End Test Scenarios

- [ ] User uploads PDF via UI → sees processing status → receives results
- [ ] Bulk upload 100 documents → queue management works correctly
- [ ] Network failure during processing → retry logic works
- [ ] Project A unavailable → graceful degradation in RAG Processor

---

## Appendix A: Quick Reference

### A.1 Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/process` | POST | Submit processing job |
| `/api/v1/jobs/{job_id}` | GET | Get job status |
| `/api/v1/jobs/{job_id}` | DELETE | Cancel job (see 6.4) |
| `/health/live` | GET | Liveness check |
| `/health/ready` | GET | Readiness check |
| `/metrics` | GET | Prometheus metrics |

### A.2 Environment Variables

```bash
# RAG Processor configuration for Project A
PROJECT_A_URL=http://project-a.internal:8080
PROJECT_A_AUTH_TOKEN=<jwt-token>
PROJECT_A_TIMEOUT_SECONDS=300
PROJECT_A_RETRY_ATTEMPTS=3
PROJECT_A_QUEUE_TYPE=redis  # or "rest"
```

### A.3 Queue Names (if using message queue)

```text
project-a.processing.high     # High priority
project-a.processing.default  # Default priority
project-a.processing.low      # Low priority/batch
project-a.status              # Status updates from Project A
project-a.dlq                 # Dead letter queue
```

---

## Appendix B: Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.1.0 | 2025-12 | **Security & Reliability Improvements** (Level 3 Expert Review): |
| | | - Added `tenant_id` as required field for multi-tenancy |
| | | - Added HMAC callback authentication (Section 4.2) |
| | | - Added callback retry policy with DLQ (Section 4.3) |
| | | - Added SSRF protection and URL validation (Section 7.3) |
| | | - Added credential resolution contract (Section 7.4) |
| | | - Added content/malware validation (Section 7.6) |
| | | - Added job cancellation workflow (Section 6.4) |
| | | - Added `on_partial_failure` processing option |
| | | - Enhanced metrics with tenant labels (Section 9.1) |
| | | - Added distributed tracing requirements (Section 9.2) |
| | | - Documented `request_id` as idempotency key |
| 1.0.0 | 2025-12 | Initial draft |

---

## Contact & Support

| Role | Responsibility |
|------|----------------|
| RAG Processor Team | Upload handling, job orchestration, UI |
| Project A Team | Document processing, IQA, corrections |
| Shared | Queue management, authentication, monitoring |

**Change Request Process:**

1. Open GitHub issue in rag-processor or image_detection repo
2. Tag with `contract-change` label
3. Review impact on both projects
4. Update this contract document
5. Implement changes
6. Integration testing
7. Deploy
