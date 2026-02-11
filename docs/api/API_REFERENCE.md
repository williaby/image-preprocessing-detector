# API Reference

**Status**: ⚠️ Phase 5 - 40% Complete | **Version**: 0.1.0

FastAPI-based REST API for intelligent image preprocessing detection in RAG document pipelines.

## Overview

The Image Preprocessing Detector API provides endpoints for analyzing document quality, detecting issues, and generating routing recommendations for downstream OCR processing. Built with FastAPI, it offers both single-document and batch processing capabilities with GPU acceleration support.

### Base URL

```text
http://localhost:8000
```

### Authentication

**Default**: Disabled (development mode)

When enabled (`IMGPREP_API_AUTH_ENABLED=true`), all protected endpoints require an API key via header:

```http
X-API-Key: your-api-key-here
```

**Public Endpoints** (no auth required):

- `/` - Root/documentation links
- `/health` - Liveness check
- `/ready` - Readiness check
- `/version` - Version information
- `/docs` - OpenAPI documentation
- `/redoc` - ReDoc documentation
- `/openapi.json` - OpenAPI schema

### Rate Limiting

**Default**: 100 requests per 60 seconds (configurable)

Protected endpoints (`/process`, `/batch`) are rate-limited per client (by API key or IP address).

Rate limit headers included in responses:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Window: 60
```

When rate limit exceeded (HTTP 429):

```http
Retry-After: 30
```

### Request Tracking

All requests receive correlation IDs for debugging:

```http
X-Correlation-ID: 550e8400-e29b-41d4-a716-446655440000
X-Response-Time-Ms: 145.23
```

## Endpoints Summary

| Method | Endpoint | Purpose | Auth | Rate Limited | Status |
|--------|----------|---------|------|--------------|--------|
| GET | `/` | Root redirect | ❌ | ❌ | ✅ Implemented |
| GET | `/health` | Liveness check | ❌ | ❌ | ✅ Implemented |
| GET | `/ready` | Readiness check | ❌ | ❌ | ✅ Implemented |
| GET | `/version` | Version info | ❌ | ❌ | ✅ Implemented |
| POST | `/process` | Process single document | ✅ | ✅ | ✅ Implemented |
| POST | `/batch` | Submit batch job | ✅ | ✅ | ✅ Implemented |
| GET | `/batch/{job_id}/status` | Get job status | ✅ | ❌ | ✅ Implemented |
| GET | `/batch/{job_id}/result` | Get job results | ✅ | ❌ | ✅ Implemented |
| DELETE | `/batch/{job_id}` | Delete job | ✅ | ❌ | ✅ Implemented |

## Detailed Endpoint Documentation

### Root Endpoint

#### `GET /`

Returns API documentation links and available endpoints.

**Response (200)**:

```json
{
  "message": "Image Preprocessing Detector API",
  "docs": "/docs",
  "health": "/health",
  "ready": "/ready",
  "version": "/version"
}
```

**Example**:

```bash
curl http://localhost:8000/
```

---

### Health Endpoints

#### `GET /health`

Basic liveness check - returns healthy if server is running.

**Response (200)**:

```json
{
  "status": "healthy",
  "timestamp": "2026-02-10T12:34:56.789Z",
  "uptime_seconds": 3600.5
}
```

**Response (503)**: Server is unhealthy (service degraded)

**Example**:

```bash
curl http://localhost:8000/health
```

---

#### `GET /ready`

Readiness check with dependency validation for load balancer probes.

**Checks Performed**:

- Device capabilities (GPU/CPU availability)
- Core module imports (IQA detectors, schema)
- Configuration validity

**Response (200)**:

```json
{
  "status": "ready",
  "timestamp": "2026-02-10T12:34:56.789Z",
  "checks": {
    "device_probe": true,
    "iqa_detectors": true,
    "schema": true,
    "configuration": true
  },
  "device": {
    "has_local_gpu": true,
    "gpu_name": "NVIDIA RTX 4090",
    "cpu_count": 16,
    "modal_available": true
  }
}
```

**Response (503)**: Server is not ready (one or more checks failed)

```json
{
  "status": "not_ready",
  "timestamp": "2026-02-10T12:34:56.789Z",
  "checks": {
    "device_probe": true,
    "iqa_detectors": false,
    "schema": true,
    "configuration": true
  },
  "device": {
    "has_local_gpu": false,
    "gpu_name": null,
    "cpu_count": 8,
    "modal_available": false
  }
}
```

**Example**:

```bash
curl http://localhost:8000/ready
```

---

#### `GET /version`

Returns API version, Python version, and model versions.

**Response (200)**:

```json
{
  "api_version": "0.1.0",
  "python_version": "3.11.9",
  "pipeline_version": "1.0.0",
  "models": {
    "teacher_model": "resnet50_teacher_50epoch",
    "student_model": "resnet18_student",
    "layout_model": null
  }
}
```

**Example**:

```bash
curl http://localhost:8000/version
```

---

### Document Processing

#### `POST /process`

Upload and process a single PDF or image file for IQA analysis.

**Request**:

- **Content-Type**: `multipart/form-data`
- **Body**:
  - `file` (required): Document to process (PDF or image)
  - `prefer_gpu` (optional, default: `true`): Prefer GPU for processing
  - `enable_corrections` (optional, default: `true`): Apply automatic corrections
  - `enable_teacher` (optional, default: `false`): Enable teacher model inference

**Supported File Types**:

- PDFs: `.pdf`
- Images: `.png`, `.jpg`, `.jpeg`, `.tiff`, `.tif`, `.webp`

**File Size Limit**: 50 MB (configurable via `IMGPREP_API_MAX_FILE_SIZE_MB`)

**Response (200)**:

```json
{
  "status": "completed",
  "result": {
    "document_id": "550e8400-e29b-41d4-a716-446655440000",
    "file_name": "sample.pdf",
    "num_pages": 5,
    "pdf_type": "image_only",
    "dqs": {
      "degradation_score": 0.35,
      "structural_complexity_score": 0.30,
      "pre_ocr_risk": null
    },
    "ocr_routing_recommendation": "ocr_advanced",
    "pages": [
      {
        "page_index": 0,
        "width_px": 2480,
        "height_px": 3508,
        "issues_detected": 2,
        "corrections_applied": 0,
        "iqa_scores": {
          "blur_score": 0.85,
          "noise_score": 0.72,
          "contrast_score": 0.65,
          "skew_angle": null
        }
      }
    ],
    "processing_time_ms": 245.67,
    "device_used": "cuda"
  },
  "metadata_url": null,
  "corrected_images_url": null,
  "error": null
}
```

**Response (400)**: Invalid request

```json
{
  "status": "failed",
  "result": null,
  "metadata_url": null,
  "corrected_images_url": null,
  "error": {
    "error": "invalid_file_type",
    "message": "Unsupported file type: .docx",
    "details": {
      "supported_extensions": [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".webp"]
    },
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Response (422)**: Processing failed

```json
{
  "status": "failed",
  "result": null,
  "metadata_url": null,
  "corrected_images_url": null,
  "error": {
    "error": "processing_failed",
    "message": "Document processing failed: Corrupt PDF structure",
    "details": null,
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Response (429)**: Rate limit exceeded

```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Max 100 requests per 60 seconds.",
  "retry_after_seconds": 30,
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Examples**:

```bash
# Basic upload
curl -X POST http://localhost:8000/process \
  -F "file=@document.pdf"

# With GPU preference disabled
curl -X POST http://localhost:8000/process \
  -F "file=@document.pdf" \
  -F "prefer_gpu=false"

# Enable teacher model inference
curl -X POST http://localhost:8000/process \
  -F "file=@document.pdf" \
  -F "enable_teacher=true"

# With API key authentication
curl -X POST http://localhost:8000/process \
  -H "X-API-Key: your-api-key-here" \
  -F "file=@document.pdf"
```

---

### Batch Processing

#### `POST /batch`

Submit multiple files for batch processing. Returns a job ID for tracking progress.

**Request**:

- **Content-Type**: `multipart/form-data`
- **Body**:
  - `files` (required): List of documents to process
  - `prefer_gpu` (optional, default: `true`): Prefer GPU for processing
  - `enable_corrections` (optional, default: `true`): Apply automatic corrections
  - `enable_teacher` (optional, default: `false`): Enable teacher model inference

**Batch Size Limit**: 100 files (configurable via `IMGPREP_API_MAX_BATCH_SIZE`)

**Response (200)**:

```json
{
  "job_id": "batch-550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "total_files": 25,
  "processed_files": 0,
  "failed_files": 0,
  "created_at": "2026-02-10T12:34:56.789Z",
  "updated_at": "2026-02-10T12:34:56.789Z",
  "completed_at": null,
  "estimated_completion": null
}
```

**Response (400)**: Invalid request

```json
{
  "error": "invalid_parameters",
  "message": "Batch size 150 exceeds limit of 100",
  "details": null,
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Examples**:

```bash
# Submit batch job
curl -X POST http://localhost:8000/batch \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.pdf" \
  -F "files=@doc3.pdf"

# With processing options
curl -X POST http://localhost:8000/batch \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.pdf" \
  -F "prefer_gpu=true" \
  -F "enable_teacher=true"
```

---

#### `GET /batch/{job_id}/status`

Get the current status of a batch processing job.

**Path Parameters**:

- `job_id` (required): Job identifier returned from POST /batch

**Response (200)**:

```json
{
  "job_id": "batch-550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "total_files": 25,
  "processed_files": 15,
  "failed_files": 2,
  "created_at": "2026-02-10T12:34:56.789Z",
  "updated_at": "2026-02-10T12:36:30.123Z",
  "completed_at": null,
  "estimated_completion": "2026-02-10T12:38:00.000Z"
}
```

**Response (404)**: Job not found

```json
{
  "detail": "Job batch-550e8400-e29b-41d4-a716-446655440000 not found"
}
```

**Status Values**:

- `pending`: Job queued, not yet started
- `processing`: Job in progress
- `completed`: Job finished successfully
- `failed`: Job failed (all files failed)

**Example**:

```bash
curl http://localhost:8000/batch/batch-550e8400-e29b-41d4-a716-446655440000/status
```

---

#### `GET /batch/{job_id}/result`

Get the results of a completed batch processing job.

**Path Parameters**:

- `job_id` (required): Job identifier

**Query Parameters**:

- `offset` (optional, default: 0): Pagination offset
- `limit` (optional, default: 100): Maximum results to return

**Response (200)**:

```json
{
  "job_id": "batch-550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "results": [
    {
      "document_id": "doc-1",
      "file_name": "doc1.pdf",
      "num_pages": 3,
      "pdf_type": "born_digital",
      "dqs": {
        "degradation_score": 0.15,
        "structural_complexity_score": 0.45,
        "pre_ocr_risk": null
      },
      "ocr_routing_recommendation": "ocr_fast",
      "pages": [],
      "processing_time_ms": 123.45,
      "device_used": "cuda"
    }
  ],
  "errors": [
    {
      "error": "processing_failed",
      "message": "Failed to process corrupt.pdf: Invalid PDF structure",
      "details": null,
      "correlation_id": null
    }
  ],
  "total_processing_time_ms": 3456.78
}
```

**Response (404)**: Job not found

**Response (425)**: Job not yet completed

```json
{
  "detail": "Job batch-550e8400-e29b-41d4-a716-446655440000 is still processing",
  "status": "processing",
  "progress": "15/25"
}
```

**Example**:

```bash
# Get all results
curl http://localhost:8000/batch/batch-550e8400-e29b-41d4-a716-446655440000/result

# Paginate results
curl "http://localhost:8000/batch/batch-550e8400-e29b-41d4-a716-446655440000/result?offset=10&limit=50"
```

---

#### `DELETE /batch/{job_id}`

Delete a batch job and its results from the job store.

**Path Parameters**:

- `job_id` (required): Job identifier

**Response (200)**:

```json
{
  "message": "Job batch-550e8400-e29b-41d4-a716-446655440000 deleted"
}
```

**Response (404)**: Job not found

**Example**:

```bash
curl -X DELETE http://localhost:8000/batch/batch-550e8400-e29b-41d4-a716-446655440000
```

---

## Request/Response Models

### Processing Models

#### `ProcessingOptions`

Processing configuration options.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `prefer_gpu` | boolean | `true` | Prefer GPU for processing |
| `enable_corrections` | boolean | `true` | Apply automatic corrections |
| `enable_teacher` | boolean | `false` | Enable teacher model inference |
| `dpi_threshold` | integer | `300` | Minimum DPI threshold for upscaling |

#### `ProcessingResult`

Document processing result.

| Field | Type | Description |
|-------|------|-------------|
| `document_id` | string | Unique document identifier (UUID) |
| `file_name` | string | Original file name |
| `num_pages` | integer | Number of pages processed |
| `pdf_type` | string? | Detected PDF type (`image_only`, `born_digital`, `hybrid`) |
| `dqs` | `DQSSummary`? | Document Quality Score summary |
| `ocr_routing_recommendation` | string? | Recommended OCR strategy (`ocr_fast`, `ocr_advanced`, `vision_simple`, `vision_structured`) |
| `pages` | `PageSummary[]` | Per-page analysis summaries |
| `processing_time_ms` | float | Total processing time in milliseconds |
| `device_used` | string | Device used for processing (`cpu`, `cuda`, `modal`) |

#### `DQSSummary`

Document Quality Score summary.

| Field | Type | Description |
|-------|------|-------------|
| `degradation_score` | float | Overall degradation score (0-1, lower is better quality) |
| `structural_complexity_score` | float | Structural complexity score (0-1) |
| `pre_ocr_risk` | float? | Pre-OCR risk score (0-1, higher is riskier) |

#### `PageSummary`

Per-page analysis summary.

| Field | Type | Description |
|-------|------|-------------|
| `page_index` | integer | Page index (0-based) |
| `width_px` | integer | Page width in pixels |
| `height_px` | integer | Page height in pixels |
| `issues_detected` | integer | Number of quality issues detected |
| `corrections_applied` | integer | Number of corrections applied |
| `iqa_scores` | `IQAScoreSummary`? | IQA score summary |

#### `IQAScoreSummary`

Image Quality Assessment score summary.

| Field | Type | Description |
|-------|------|-------------|
| `blur_score` | float? | Blur quality score (0-1, higher is sharper) |
| `noise_score` | float? | Noise quality score (0-1, higher is cleaner) |
| `contrast_score` | float? | Contrast quality score (0-1, higher is better) |
| `skew_angle` | float? | Detected skew angle in degrees |

### Batch Models

#### `BatchJobStatus`

Batch job status and progress.

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | Unique job identifier (UUID) |
| `status` | `ProcessingStatus` | Job status (`pending`, `processing`, `completed`, `failed`) |
| `total_files` | integer | Total files in batch |
| `processed_files` | integer | Files processed so far |
| `failed_files` | integer | Files that failed processing |
| `created_at` | datetime | Job creation timestamp |
| `updated_at` | datetime | Last update timestamp |
| `completed_at` | datetime? | Completion timestamp |
| `estimated_completion` | datetime? | Estimated completion time |

#### `BatchJobResult`

Batch job processing results.

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | Unique job identifier |
| `status` | `ProcessingStatus` | Job status |
| `results` | `ProcessingResult[]` | Processing results (paginated) |
| `errors` | `ErrorResponse[]` | Processing errors |
| `total_processing_time_ms` | float | Total processing time in milliseconds |

### Error Models

#### `ErrorResponse`

Standard error response format.

| Field | Type | Description |
|-------|------|-------------|
| `error` | `ErrorCode` | Structured error code |
| `message` | string | Human-readable error message |
| `details` | object? | Additional error details |
| `correlation_id` | string? | Request correlation ID for debugging |

#### `ErrorCode` Enum

Structured error codes for API responses.

| Code | HTTP Status | Category | Description |
|------|-------------|----------|-------------|
| `invalid_file_type` | 400 | Validation | Unsupported file type |
| `file_too_large` | 400 | Validation | File exceeds size limit |
| `invalid_parameters` | 400 | Validation | Invalid request parameters |
| `empty_file` | 400 | Validation | Uploaded file is empty |
| `processing_failed` | 422 | Processing | Document processing failed |
| `corrupt_file` | 422 | Processing | File is corrupt or malformed |
| `unsupported_format` | 422 | Processing | File format not supported |
| `internal_error` | 500 | Server | Internal server error |
| `gpu_unavailable` | 500 | Server | GPU processing unavailable |
| `model_load_failed` | 500 | Server | Model loading failed |
| `rate_limit_exceeded` | 429 | Rate Limiting | Too many requests |
| `unauthorized` | 401 | Auth | Missing or invalid API key |
| `forbidden` | 403 | Auth | Insufficient permissions |

---

## Middleware Configuration

### CORS

**Default**: Enabled with permissive settings (development mode)

```bash
# Environment variables
IMGPREP_API_CORS_ENABLED=true
IMGPREP_API_CORS_ORIGINS=["*"]  # Comma-separated list
IMGPREP_API_CORS_ALLOW_CREDENTIALS=true
IMGPREP_API_CORS_ALLOW_METHODS=["*"]
IMGPREP_API_CORS_ALLOW_HEADERS=["*"]
```

**Production Recommendation**: Restrict origins to specific domains.

### Request Logging

**Default**: Enabled with structured logging

All requests are logged with:

- Correlation ID
- Method and path
- Query parameters
- Client IP
- Response status code
- Response time

**Optional**: Enable request/response body logging (disabled by default for security)

```bash
IMGPREP_API_LOG_REQUEST_BODY=false
IMGPREP_API_LOG_RESPONSE_BODY=false
```

### Rate Limiting

**Default**: 100 requests per 60-second window

**Configuration**:

```bash
IMGPREP_API_RATE_LIMIT_ENABLED=true
IMGPREP_API_RATE_LIMIT_REQUESTS=100
IMGPREP_API_RATE_LIMIT_WINDOW_SECONDS=60
```

**Note**: Rate limiting is **per-worker** with in-memory storage. For production multi-worker deployments, use Redis-based distributed rate limiting (planned).

**Limited Endpoints**: Only `/process` and `/batch` endpoints are rate-limited.

### API Key Authentication

**Default**: Disabled (development mode)

**Configuration**:

```bash
IMGPREP_API_AUTH_ENABLED=false
IMGPREP_API_API_KEYS=["key1","key2","key3"]  # Comma-separated
IMGPREP_API_INTERNAL_CALLERS=["127.0.0.1","::1"]  # Bypass auth for internal IPs
```

**Internal Callers**: Requests from specified IP addresses bypass authentication (useful for internal service-to-service calls).

---

## Error Handling

### Error Response Format

All errors follow a consistent JSON structure:

```json
{
  "error": "error_code",
  "message": "Human-readable error message",
  "details": {
    "additional": "context"
  },
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### HTTP Status Codes

| Status | Meaning | When Used |
|--------|---------|-----------|
| 200 | OK | Successful request |
| 400 | Bad Request | Validation errors (invalid file type, size, parameters) |
| 401 | Unauthorized | Missing API key (when auth enabled) |
| 403 | Forbidden | Invalid API key (when auth enabled) |
| 404 | Not Found | Resource not found (batch job) |
| 422 | Unprocessable Entity | Processing failed (corrupt file, unsupported format) |
| 425 | Too Early | Batch job not yet completed |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server errors |
| 503 | Service Unavailable | Server not ready (dependencies unavailable) |

### Common Error Scenarios

#### File Validation Errors (400)

```json
{
  "error": "invalid_file_type",
  "message": "Unsupported file type: .docx",
  "details": {
    "supported_extensions": [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".webp"]
  }
}
```

#### File Size Errors (400)

```json
{
  "error": "file_too_large",
  "message": "File size 75.3MB exceeds limit of 50MB"
}
```

#### Processing Errors (422)

```json
{
  "error": "processing_failed",
  "message": "Document processing failed: Corrupt PDF structure"
}
```

#### Rate Limiting (429)

```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Max 100 requests per 60 seconds.",
  "retry_after_seconds": 30
}
```

Headers:

```http
Retry-After: 30
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Window: 60
```

#### Authentication Errors (401)

```json
{
  "error": "unauthorized",
  "message": "API key required. Provide X-API-Key header."
}
```

---

## Implementation Status

### Phase 5 Completion: 40%

| Component | Status | Notes |
|-----------|--------|-------|
| **Health Endpoints** | ✅ Implemented | `/health`, `/ready`, `/version` fully functional |
| **Process Endpoint** | ✅ Implemented | POST `/process` with full IQA pipeline |
| **Batch Endpoints** | ✅ Implemented | POST `/batch`, GET status/result, DELETE job |
| **Middleware** | ✅ Implemented | CORS, logging, rate limiting, auth |
| **Error Handling** | ✅ Implemented | Structured error codes and responses |
| **Model Preloading** | ✅ Implemented | Student/teacher models preloaded on startup |
| **Device Detection** | ✅ Implemented | GPU/CPU capability probing |
| **File Validation** | ✅ Implemented | Type, size, content validation |
| **Metadata URLs** | ❌ Not Implemented | `metadata_url` and `corrected_images_url` return `null` |
| **Load Testing** | ❌ Not Implemented | Performance benchmarks pending |
| **Deployment Automation** | ❌ Not Implemented | CI/CD pipeline for API deployment pending |
| **Production Hardening** | ⚠️ Partial | In-memory job store, per-worker rate limiting |

### Known Limitations

1. **In-Memory Job Store**: Batch jobs stored in memory (lost on restart). Production should use Redis/database.
2. **Per-Worker Rate Limiting**: Rate limits are per-worker instance. Multi-worker deployments need distributed rate limiting.
3. **Metadata URLs**: `metadata_url` and `corrected_images_url` fields always return `null` (file storage integration pending).
4. **Job Cleanup**: No automatic cleanup of old batch jobs (manual cleanup via DELETE endpoint).
5. **Estimated Completion**: `estimated_completion` field always returns `null` (ETA calculation not implemented).
6. **Model Lazy Loading Fallback**: If model preloading fails, lazy loading occurs on first request (cold start penalty).

### Planned Enhancements

**Phase 5 Remaining Work (60%)**:

- File storage integration for metadata and corrected images
- Redis-based job store for batch processing
- Distributed rate limiting (Redis)
- Load testing and performance benchmarks
- Deployment automation (Docker, Kubernetes manifests)
- Prometheus metrics integration
- Health check integration with monitoring systems
- API versioning strategy (v1, v2 routes)

---

## Configuration Reference

### Environment Variables

All configuration via environment variables with `IMGPREP_API_` prefix:

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `IMGPREP_API_TITLE` | string | `"Image Preprocessing Detector API"` | API title for docs |
| `IMGPREP_API_DESCRIPTION` | string | `"Intelligent image preprocessing..."` | API description |
| `IMGPREP_API_VERSION` | string | `"0.1.0"` | API version |
| **CORS** | | | |
| `IMGPREP_API_CORS_ENABLED` | boolean | `true` | Enable CORS middleware |
| `IMGPREP_API_CORS_ORIGINS` | list[string] | `["*"]` | Allowed origins (comma-separated) |
| `IMGPREP_API_CORS_ALLOW_CREDENTIALS` | boolean | `true` | Allow credentials |
| `IMGPREP_API_CORS_ALLOW_METHODS` | list[string] | `["*"]` | Allowed HTTP methods |
| `IMGPREP_API_CORS_ALLOW_HEADERS` | list[string] | `["*"]` | Allowed headers |
| **Rate Limiting** | | | |
| `IMGPREP_API_RATE_LIMIT_ENABLED` | boolean | `true` | Enable rate limiting |
| `IMGPREP_API_RATE_LIMIT_REQUESTS` | integer | `100` | Max requests per window |
| `IMGPREP_API_RATE_LIMIT_WINDOW_SECONDS` | integer | `60` | Window duration in seconds |
| **Processing Limits** | | | |
| `IMGPREP_API_MAX_BATCH_SIZE` | integer | `100` | Max files per batch request |
| `IMGPREP_API_MAX_FILE_SIZE_MB` | integer | `50` | Max file size in MB |
| **Processing Defaults** | | | |
| `IMGPREP_API_DEFAULT_PREFER_GPU` | boolean | `true` | Default GPU preference |
| `IMGPREP_API_DEFAULT_ENABLE_CORRECTIONS` | boolean | `true` | Default corrections enabled |
| `IMGPREP_API_DEFAULT_ENABLE_TEACHER` | boolean | `false` | Default teacher model disabled |
| **Timeouts** | | | |
| `IMGPREP_API_PROCESS_TIMEOUT_SECONDS` | integer | `300` | Single document timeout |
| `IMGPREP_API_BATCH_TIMEOUT_SECONDS` | integer | `3600` | Batch processing timeout |
| **Logging** | | | |
| `IMGPREP_API_LOG_REQUEST_BODY` | boolean | `false` | Log request bodies |
| `IMGPREP_API_LOG_RESPONSE_BODY` | boolean | `false` | Log response bodies |
| **Authentication** | | | |
| `IMGPREP_API_AUTH_ENABLED` | boolean | `false` | Enable API key auth |
| `IMGPREP_API_API_KEYS` | list[string] | `[]` | Valid API keys (comma-separated) |
| `IMGPREP_API_INTERNAL_CALLERS` | list[string] | `[]` | Internal IPs (bypass auth) |
| **Modal GPU Budget** | | | |
| `IMGPREP_API_MODAL_BUDGET_ENABLED` | boolean | `true` | Enable Modal GPU budget |
| `IMGPREP_API_MODAL_DAILY_BUDGET_DOLLARS` | float | `10.0` | Daily budget in USD |
| `IMGPREP_API_MODAL_MONTHLY_BUDGET_DOLLARS` | float | `100.0` | Monthly budget in USD |
| `IMGPREP_API_MODAL_COST_PER_GPU_HOUR` | float | `0.36` | Cost per GPU hour (T4) |
| `IMGPREP_API_MODAL_BUDGET_WARNING_THRESHOLD` | float | `0.8` | Warning threshold (0-1) |

### Example `.env` File

```bash
# API Configuration
IMGPREP_API_VERSION=0.1.0
IMGPREP_API_CORS_ORIGINS=["https://app.example.com","https://admin.example.com"]

# Rate Limiting
IMGPREP_API_RATE_LIMIT_REQUESTS=200
IMGPREP_API_RATE_LIMIT_WINDOW_SECONDS=60

# Authentication (production)
IMGPREP_API_AUTH_ENABLED=true
IMGPREP_API_API_KEYS=["prod-key-abc123","prod-key-xyz789"]
IMGPREP_API_INTERNAL_CALLERS=["10.0.1.10","10.0.1.11"]

# Processing Limits
IMGPREP_API_MAX_BATCH_SIZE=50
IMGPREP_API_MAX_FILE_SIZE_MB=100

# Modal GPU Budget
IMGPREP_API_MODAL_DAILY_BUDGET_DOLLARS=20.0
IMGPREP_API_MODAL_MONTHLY_BUDGET_DOLLARS=300.0
```

---

## Running the API

### Local Development

```bash
# Install dependencies
uv sync --extra dev --extra workers

# Start development server
uvicorn image_preprocessing_detector.api.app:app --reload --host 0.0.0.0 --port 8000

# Or using uv run
uv run uvicorn image_preprocessing_detector.api.app:app --reload --host 0.0.0.0 --port 8000
```

### Production Deployment

```bash
# Production server with multiple workers
uvicorn image_preprocessing_detector.api.app:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-config logging.yaml
```

### Docker Deployment

```bash
# Build image
docker build -t image-prep-api:latest .

# Run container
docker run -d \
  -p 8000:8000 \
  -e IMGPREP_API_AUTH_ENABLED=true \
  -e IMGPREP_API_API_KEYS=["key1","key2"] \
  --name image-prep-api \
  image-prep-api:latest
```

---

## Interactive Documentation

### OpenAPI (Swagger UI)

**URL**: `http://localhost:8000/docs`

Interactive API documentation with:

- Endpoint exploration
- Request/response schema visualization
- Try-it-out functionality
- Model definitions

### ReDoc

**URL**: `http://localhost:8000/redoc`

Alternative documentation interface with:

- Clean, readable layout
- Code samples
- Model definitions
- Tag-based organization

### OpenAPI Schema

**URL**: `http://localhost:8000/openapi.json`

Raw OpenAPI 3.0 schema for:

- Client code generation
- API testing tools
- Third-party integrations

---

## Client Examples

### Python (requests)

```python
import requests

# Single document processing
with open("document.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/process",
        files={"file": f},
        params={"prefer_gpu": True, "enable_teacher": False},
        headers={"X-API-Key": "your-api-key"}
    )
    result = response.json()
    print(f"Document ID: {result['result']['document_id']}")
    print(f"Processing time: {result['result']['processing_time_ms']}ms")

# Batch processing
files = [
    ("files", open("doc1.pdf", "rb")),
    ("files", open("doc2.pdf", "rb")),
    ("files", open("doc3.pdf", "rb")),
]
response = requests.post(
    "http://localhost:8000/batch",
    files=files,
    headers={"X-API-Key": "your-api-key"}
)
job_id = response.json()["job_id"]

# Check batch status
status_response = requests.get(f"http://localhost:8000/batch/{job_id}/status")
print(status_response.json())

# Get batch results (when complete)
result_response = requests.get(f"http://localhost:8000/batch/{job_id}/result")
print(result_response.json())
```

### cURL

```bash
# Single document
curl -X POST http://localhost:8000/process \
  -H "X-API-Key: your-api-key" \
  -F "file=@document.pdf" \
  -F "prefer_gpu=true"

# Batch processing
curl -X POST http://localhost:8000/batch \
  -H "X-API-Key: your-api-key" \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.pdf" \
  -F "files=@doc3.pdf"

# Check status
curl http://localhost:8000/batch/{job_id}/status

# Get results
curl http://localhost:8000/batch/{job_id}/result
```

### JavaScript (fetch)

```javascript
// Single document processing
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('http://localhost:8000/process?prefer_gpu=true', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key'
  },
  body: formData
});

const result = await response.json();
console.log('Document ID:', result.result.document_id);

// Batch processing
const batchFormData = new FormData();
files.forEach(file => batchFormData.append('files', file));

const batchResponse = await fetch('http://localhost:8000/batch', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key'
  },
  body: batchFormData
});

const batchResult = await batchResponse.json();
const jobId = batchResult.job_id;

// Poll for status
const statusResponse = await fetch(`http://localhost:8000/batch/${jobId}/status`);
const status = await statusResponse.json();
```

---

## Monitoring and Observability

### Health Check Integration

Kubernetes/Docker health checks:

```yaml
# Kubernetes liveness probe
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30

# Kubernetes readiness probe
readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

### Structured Logging

All logs include:

- `correlation_id`: Request tracking
- `timestamp`: ISO 8601 format
- `event`: Structured event name
- Context fields (method, path, status_code, duration_ms, etc.)

Example log entry:

```json
{
  "event": "request_completed",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "POST",
  "path": "/process",
  "status_code": 200,
  "duration_ms": 245.67,
  "timestamp": "2026-02-10T12:34:56.789Z",
  "level": "info"
}
```

### Performance Metrics (Planned)

Future integration with Prometheus:

- Request duration histograms
- Request rate counters
- Error rate counters
- Active request gauges
- Device usage metrics (GPU/CPU)
- Model inference times

---

## Security Considerations

### File Upload Security

1. **File Type Validation**: Extension and MIME type checking
2. **File Size Limits**: Configurable max size (default 50MB)
3. **Content Validation**: Empty file detection
4. **Temporary File Cleanup**: Automatic cleanup after processing
5. **Path Traversal Protection**: Safe file name handling

### Authentication Best Practices

1. **Strong API Keys**: Use long, random keys (32+ characters)
2. **Key Rotation**: Regularly rotate API keys
3. **Environment Variables**: Never hardcode keys in code
4. **HTTPS Only**: Use TLS in production
5. **Internal Caller Whitelist**: Restrict internal access by IP

### Rate Limiting Strategy

1. **Per-Client Limits**: Rate limiting by API key or IP
2. **Selective Enforcement**: Only rate-limit processing endpoints
3. **Graceful Degradation**: Return 429 with Retry-After header
4. **Distributed Limiting**: Use Redis for multi-worker deployments (planned)

### CORS Configuration

**Development**: Permissive (`*` origins)
**Production**: Restrict to specific domains:

```bash
IMGPREP_API_CORS_ORIGINS=["https://app.example.com"]
IMGPREP_API_CORS_ALLOW_CREDENTIALS=true
```

---

## Troubleshooting

### Common Issues

#### GPU Not Detected

**Symptom**: `device_used: "cpu"` in results despite GPU available

**Solutions**:

1. Check CUDA installation: `nvidia-smi`
2. Verify PyTorch GPU support: `python -c "import torch; print(torch.cuda.is_available())"`
3. Check readiness endpoint: `curl http://localhost:8000/ready`

#### Rate Limit Errors

**Symptom**: HTTP 429 responses

**Solutions**:

1. Check rate limit headers in response
2. Implement exponential backoff with `Retry-After` header
3. Increase rate limits via environment variables
4. Use batch endpoints for multiple files

#### Model Loading Failures

**Symptom**: `model_load_failed` errors

**Solutions**:

1. Verify model files exist in `models/iqa/onnx/`
2. Check model file permissions
3. Verify ONNX Runtime installation
4. Check logs for detailed error messages

#### Batch Job Not Progressing

**Symptom**: Job stuck in `processing` status

**Solutions**:

1. Check server logs for errors
2. Verify background task processing
3. Check file validation errors
4. Monitor server resource usage (memory, CPU)

---

## Related Documentation

- [Project CLAUDE.md](/home/byron/dev/image_detection/CLAUDE.md) - Project overview and standards
- [Project Plan](/home/byron/dev/image_detection/docs/planning/PROJECT_PLAN.md) - Detailed phase breakdown
- [Schema Reference](/home/byron/dev/image_detection/src/image_preprocessing_detector/schema.py) - Pydantic models
- [Device Orchestration](/home/byron/dev/image_detection/src/image_preprocessing_detector/utils/device_orchestrator.py) - GPU/CPU priority logic
- [Modal Quick Reference](/home/byron/dev/image_detection/docs/reference/MODAL_QUICK_REFERENCE.md) - Modal GPU integration

---

**Last Updated**: 2026-02-10
**API Version**: 0.1.0
**Phase**: 5 (Deployment) - 40% Complete
