---
schema_type: common
title: "REST API Documentation"
description: "API reference for the Image Preprocessing Detector REST endpoints"
tags:
  - api_reference
  - documentation
  - reference
status: published
owner: core-maintainer
authors:
  - name: "Byron Williams"
purpose: "Document REST API endpoints, authentication, and usage examples."
---

Comprehensive documentation for the Image Preprocessing Detector REST API.

## Overview

The API provides document preprocessing and quality assessment for RAG pipelines. It supports single document processing and batch operations with async status tracking.

**Base URL**: `http://localhost:8000` (local) or your configured domain

**API Version**: `0.1.0`

## Authentication

When authentication is enabled (`IMGPREP_API_AUTH_ENABLED=true`), all protected endpoints require an API key.

```bash
# Include API key in request header
curl -H "X-API-Key: your-api-key-here" http://localhost:8000/process
```text

**Public Endpoints** (no auth required):

- `GET /` - Root navigation
- `GET /health` - Health check
- `GET /ready` - Readiness check
- `GET /version` - Version info
- `GET /docs` - OpenAPI documentation
- `GET /openapi.json` - OpenAPI schema

**Protected Endpoints**:

- `POST /process` - Single document processing
- `POST /batch` - Batch job submission
- `GET /batch/{job_id}/status` - Job status
- `GET /batch/{job_id}/result` - Job results
- `DELETE /batch/{job_id}` - Delete job

### Internal Callers

Configure `IMGPREP_API_INTERNAL_CALLERS` with IP addresses that bypass authentication:

```bash
export IMGPREP_API_INTERNAL_CALLERS='["10.0.0.0/8", "172.16.0.0/12"]'
```text

---

## Rate Limiting

When enabled (`IMGPREP_API_RATE_LIMIT_ENABLED=true`), processing endpoints are rate limited.

**Default**: 100 requests per 60 seconds per client (by API key or IP)

**Response Headers**:

```text
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Window: 60
```text

**Rate Limit Exceeded (429)**:

```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Max 100 requests per 60 seconds.",
  "retry_after_seconds": 45,
  "correlation_id": "abc123"
}
```text

---

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `invalid_file_type` | 400 | Unsupported file extension |
| `file_too_large` | 400 | File exceeds size limit |
| `invalid_parameters` | 400 | Invalid request parameters |
| `empty_file` | 400 | File is empty |
| `unauthorized` | 401 | Missing API key |
| `forbidden` | 403 | Invalid API key |
| `processing_failed` | 422 | Processing error occurred |
| `corrupt_file` | 422 | File is corrupt or unreadable |
| `unsupported_format` | 422 | File format not supported |
| `rate_limit_exceeded` | 429 | Too many requests |
| `internal_error` | 500 | Server error |
| `gpu_unavailable` | 500 | GPU requested but unavailable |
| `model_load_failed` | 500 | ML model failed to load |

### Error Response Format

```json
{
  "error": "invalid_file_type",
  "message": "File type .docx is not supported. Supported types: .pdf, .png, .jpg, .jpeg, .tiff, .tif, .bmp",
  "details": {
    "file_name": "document.docx",
    "detected_type": ".docx"
  },
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```text

---

## Endpoints

### Health Check

#### `GET /health`

Returns service health status.

**Response**:

```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00Z",
  "uptime_seconds": 3600.5
}
```text

**curl**:

```bash
curl http://localhost:8000/health
```text

---

#### `GET /ready`

Returns readiness status with component checks.

**Response**:

```json
{
  "status": "ready",
  "timestamp": "2025-01-15T10:30:00Z",
  "checks": {
    "disk_space": true,
    "memory": true,
    "models_loaded": true
  },
  "device": {
    "type": "cpu",
    "name": "Intel Core i7",
    "memory_available_gb": 8.5
  }
}
```text

**curl**:

```bash
curl http://localhost:8000/ready
```text

---

#### `GET /version`

Returns API and pipeline version information.

**Response**:

```json
{
  "api_version": "0.1.0",
  "pipeline_version": "0.1.0",
  "python_version": "3.11.6",
  "models": {
    "iqa_student": "resnet18-iqa-v1.0.0",
    "iqa_teacher": "resnet50-iqa-v1.0.0",
    "layout_lite": "doclayout-yolo-v1.0.0"
  }
}
```text

**curl**:

```bash
curl http://localhost:8000/version
```text

---

### Single Document Processing

#### `POST /process`

Process a single document (PDF or image).

**Request**:

- Content-Type: `multipart/form-data`
- File field: `file` (required)
- Options: `prefer_gpu`, `enable_corrections`, `enable_teacher`, `dpi_threshold`

**Supported File Types**: `.pdf`, `.png`, `.jpg`, `.jpeg`, `.tiff`, `.tif`, `.bmp`

**Max File Size**: 50 MB (configurable)

**curl Examples**:

```bash
# Basic processing (default options)
curl -X POST http://localhost:8000/process \
  -H "X-API-Key: your-key" \
  -F "file=@document.pdf"

# With custom options
curl -X POST http://localhost:8000/process \
  -H "X-API-Key: your-key" \
  -F "file=@scan.png" \
  -F "prefer_gpu=true" \
  -F "enable_corrections=true" \
  -F "enable_teacher=false" \
  -F "dpi_threshold=300"

# Force CPU processing
curl -X POST http://localhost:8000/process \
  -H "X-API-Key: your-key" \
  -F "file=@document.pdf" \
  -F "prefer_gpu=false"

# Enable teacher model for high-risk documents
curl -X POST http://localhost:8000/process \
  -H "X-API-Key: your-key" \
  -F "file=@important.pdf" \
  -F "enable_teacher=true"
```text

**Response (200 OK)**:

```json
{
  "status": "completed",
  "result": {
    "document_id": "doc_abc123",
    "file_name": "document.pdf",
    "num_pages": 5,
    "pdf_type": "image_only",
    "dqs": {
      "degradation_score": 0.25,
      "structural_complexity_score": 0.4,
      "pre_ocr_risk": 0.32
    },
    "ocr_routing_recommendation": "ocr_advanced",
    "pages": [
      {
        "page_index": 0,
        "width_px": 2550,
        "height_px": 3300,
        "issues_detected": 2,
        "corrections_applied": 2,
        "iqa_scores": {
          "blur_score": 0.85,
          "noise_score": 0.92,
          "contrast_score": 0.78,
          "skew_angle": 1.5
        }
      }
    ],
    "processing_time_ms": 1250.5,
    "device_used": "cpu"
  },
  "metadata_url": null,
  "corrected_images_url": null,
  "error": null
}
```text

**Error Response (400 Bad Request)**:

```json
{
  "error": "invalid_file_type",
  "message": "File type .docx is not supported",
  "details": {
    "supported_types": [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"]
  },
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```text

---

### Batch Processing

#### `POST /batch`

Submit multiple files for async batch processing.

**Request**:

- Content-Type: `multipart/form-data`
- Files field: `files` (multiple files)
- Max batch size: 100 files (configurable)

**curl**:

```bash
# Submit batch of files
curl -X POST http://localhost:8000/batch \
  -H "X-API-Key: your-key" \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.pdf" \
  -F "files=@scan1.png" \
  -F "files=@scan2.jpg"

# With options
curl -X POST http://localhost:8000/batch \
  -H "X-API-Key: your-key" \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.pdf" \
  -F "prefer_gpu=true"
```text

**Response (200 OK)**:

```json
{
  "job_id": "job_xyz789",
  "status": "pending",
  "total_files": 4,
  "processed_files": 0,
  "failed_files": 0,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z",
  "completed_at": null,
  "estimated_completion": "2025-01-15T10:35:00Z"
}
```text

---

#### `GET /batch/{job_id}/status`

Get current status of a batch job.

**curl**:

```bash
curl http://localhost:8000/batch/job_xyz789/status \
  -H "X-API-Key: your-key"
```text

**Response (200 OK)**:

```json
{
  "job_id": "job_xyz789",
  "status": "processing",
  "total_files": 4,
  "processed_files": 2,
  "failed_files": 0,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:32:00Z",
  "completed_at": null,
  "estimated_completion": "2025-01-15T10:34:00Z"
}
```text

**Response (404 Not Found)**:

```json
{
  "error": "not_found",
  "message": "Job not found: job_invalid",
  "correlation_id": "..."
}
```text

---

#### `GET /batch/{job_id}/result`

Get results of a completed batch job with pagination.

**Query Parameters**:

- `offset` (int, default: 0) - Skip first N results
- `limit` (int, default: 100, max: 1000) - Max results to return

**curl**:

```bash
# Get all results
curl "http://localhost:8000/batch/job_xyz789/result" \
  -H "X-API-Key: your-key"

# Paginated results
curl "http://localhost:8000/batch/job_xyz789/result?offset=0&limit=10" \
  -H "X-API-Key: your-key"
```text

**Response (200 OK)**:

```json
{
  "job_id": "job_xyz789",
  "status": "completed",
  "results": [
    {
      "document_id": "doc_001",
      "file_name": "doc1.pdf",
      "num_pages": 3,
      "pdf_type": "image_only",
      "dqs": {
        "degradation_score": 0.2,
        "structural_complexity_score": 0.3,
        "pre_ocr_risk": 0.25
      },
      "ocr_routing_recommendation": "ocr_fast",
      "pages": [...],
      "processing_time_ms": 850.2,
      "device_used": "cpu"
    }
  ],
  "errors": [
    {
      "error": "corrupt_file",
      "message": "Failed to read doc2.pdf: corrupt header",
      "details": {"file_name": "doc2.pdf"},
      "correlation_id": "..."
    }
  ],
  "total_processing_time_ms": 3500.5
}
```text

---

#### `DELETE /batch/{job_id}`

Delete a batch job and its results.

**curl**:

```bash
curl -X DELETE http://localhost:8000/batch/job_xyz789 \
  -H "X-API-Key: your-key"
```text

**Response (200 OK)**:

```json
{
  "message": "Job deleted successfully",
  "job_id": "job_xyz789"
}
```text

---

## Device Behavior

The API uses a device priority system for ML inference:

| Priority | Device | When Used |
|----------|--------|-----------|
| 1 | Local GPU | `prefer_gpu=true` and CUDA available |
| 2 | Local CPU | `prefer_gpu=false` or no GPU |
| 3 | Modal GPU | Teacher inference with no local GPU |

### GPU Detection

Check device status via `/ready` endpoint:

```bash
curl http://localhost:8000/ready | jq '.device'
```text

**GPU Available**:

```json
{
  "type": "gpu",
  "name": "NVIDIA GeForce RTX 3080",
  "memory_available_gb": 10.2
}
```text

**CPU Only**:

```json
{
  "type": "cpu",
  "name": "Intel Core i7-12700",
  "memory_available_gb": 32.0
}
```text

### Processing Time Expectations

| Device | Single Page | 10-Page PDF |
|--------|-------------|-------------|
| GPU (RTX 3080) | ~40ms | ~400ms |
| CPU (i7-12700) | ~150ms | ~1500ms |
| Modal GPU | ~200ms* | ~2000ms* |

*Includes network overhead

### When Teacher Model is Used

The teacher model (ResNet-50) provides higher accuracy but higher latency:

1. **Explicit Request**: `enable_teacher=true` in request options
2. **High Uncertainty**: Student model confidence < 0.7
3. **High-Risk Document**: Complex layouts or degraded quality

**Note**: Teacher inference on CPU is blocked by default due to latency (>500ms/page). Configure via `IMGPREP_ALLOW_TEACHER_CPU=true` to override.

---

## Request Headers

| Header | Required | Description |
|--------|----------|-------------|
| `X-API-Key` | Conditional | API key (if auth enabled) |
| `X-Correlation-ID` | Optional | Custom correlation ID for tracing |
| `Content-Type` | Yes | `multipart/form-data` for uploads |

## Response Headers

| Header | Description |
|--------|-------------|
| `X-Correlation-ID` | Request correlation ID |
| `X-Response-Time-Ms` | Server processing time |
| `X-RateLimit-Limit` | Max requests per window |
| `X-RateLimit-Remaining` | Remaining requests |
| `X-RateLimit-Window` | Window duration (seconds) |
| `Retry-After` | Seconds until rate limit resets (429 only) |

---

## Python Client Example

```python
import httpx

# Configure client
client = httpx.Client(
    base_url="http://localhost:8000",
    headers={"X-API-Key": "your-api-key"},
    timeout=300.0
)

# Single document processing
with open("document.pdf", "rb") as f:
    response = client.post(
        "/process",
        files={"file": ("document.pdf", f, "application/pdf")},
        data={"prefer_gpu": "true", "enable_corrections": "true"}
    )

result = response.json()
print(f"Document ID: {result['result']['document_id']}")
print(f"DQS: {result['result']['dqs']}")
print(f"Routing: {result['result']['ocr_routing_recommendation']}")

# Batch processing
files = [
    ("files", ("doc1.pdf", open("doc1.pdf", "rb"), "application/pdf")),
    ("files", ("doc2.pdf", open("doc2.pdf", "rb"), "application/pdf")),
]
response = client.post("/batch", files=files)
job = response.json()
print(f"Job ID: {job['job_id']}")

# Poll for completion
import time
while True:
    status = client.get(f"/batch/{job['job_id']}/status").json()
    if status["status"] == "completed":
        break
    time.sleep(1)

# Get results
results = client.get(f"/batch/{job['job_id']}/result").json()
for r in results["results"]:
    print(f"{r['file_name']}: {r['ocr_routing_recommendation']}")
```text

---

## OpenAPI Schema

Full OpenAPI schema available at:

- Interactive docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- JSON schema: `http://localhost:8000/openapi.json`
