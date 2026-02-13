# Deployment Runbook

**Image Preprocessing Detector** - Comprehensive deployment guide for all environments.

**Last Updated**: 2026-02-10
**Status**: Active Reference

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Celery Workers](#celery-workers)
5. [Modal GPU Training](#modal-gpu-training)
6. [Docling OCR Server](#docling-ocr-server)
7. [Monitoring & Alerting](#monitoring--alerting)
8. [Health Checks](#health-checks)
9. [Environment Variables](#environment-variables)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

**Local Development**:

```bash
# Python 3.11+ with uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Git with GPG signing configured
gpg --list-secret-keys  # Must show GPG key
git config --get user.signingkey  # Must be configured

# Pre-commit hooks
uv sync --extra dev
uv run pre-commit install
```

**Docker Deployment**:

```bash
# Docker Engine 24.0+
docker --version

# Docker Compose v2.20+
docker compose version

# For GPU: NVIDIA Container Toolkit
nvidia-smi  # Verify GPU access
```

**Celery Workers**:

```bash
# Redis server
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Or install locally
# macOS: brew install redis && brew services start redis
# Ubuntu: sudo apt install redis-server && sudo systemctl start redis
```

**Modal GPU Training**:

```bash
# Modal CLI installed via uv
uv sync  # Installs modal from dependencies

# Modal account and authentication
uv run modal token new  # One-time setup
```

### Required Credentials

**GCS Service Account** (for training datasets):

- File: `gcs-service-account.json`
- Location: `/path/to/gcs-service-account.json`
- Set: `GOOGLE_APPLICATION_CREDENTIALS` environment variable

**Modal Secrets**:

```bash
# GCS credentials for Modal (base64-encoded)
./scripts/modal_helpers.sh setup-gcs-secret /path/to/gcs-service-account.json
```

**Hugging Face Token** (for model hub):

- Create at: <https://huggingface.co/settings/tokens>
- Set: `HF_TOKEN` environment variable

---

## Local Development

### Quick Start

```bash
# Clone repository
git clone https://github.com/williaby/image-preprocessing-detector
cd image-preprocessing-detector

# Install dependencies (includes dev tools)
uv sync --extra dev

# Install with ML dependencies (Phase 2+)
uv sync --extra dev --extra ml

# Setup pre-commit hooks (required before first commit)
uv run pre-commit install

# Verify installation
uv run imgprep --help
uv run pytest -v
```

### Development Workflow

**Run CLI Tool**:

```bash
uv run imgprep process input.pdf --output result.json
uv run imgprep layout list  # List layout taxonomy
```

**Run Tests**:

```bash
# All tests with coverage (80% minimum enforced)
uv run pytest -v

# Specific test categories
uv run pytest -v -m unit               # Unit tests only
uv run pytest -v -m integration        # Integration tests only
uv run pytest -v -m "not slow"         # Exclude slow tests

# Single test file
uv run pytest tests/unit/test_schema.py -v

# With coverage report
uv run pytest --cov=src --cov-report=html --cov-report=term-missing

# Run tests in parallel (faster for large suites)
uv run pytest -n auto
```

**Code Quality**:

```bash
# Format code (required before commit)
uv run ruff format src tests

# Lint and auto-fix
uv run ruff check --fix src tests

# Type checking (BasedPyright - strict on src/, 3-5x faster than MyPy)
uv run basedpyright src

# Run all pre-commit hooks manually
uv run pre-commit run --all-files

# Security scanning
uv run bandit -r src
uv run safety check
```

### Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your settings (see Environment Variables section)
```

---

## Docker Deployment

### CPU Container (Standard API)

**Build**:

```bash
docker build -t imgprep-api:latest -f Dockerfile .
```

**Run**:

```bash
docker run -d \
  --name imgprep-api \
  -p 8000:8000 \
  -v $(pwd)/models:/app/models:ro \
  -v $(pwd)/logs:/app/logs:rw \
  --env-file .env \
  imgprep-api:latest
```

**Configuration**:

- **Workers**: 4 (default in Dockerfile)
- **Memory**: No specific limit (adjust via Docker runtime flags)
- **Port**: 8000

### GPU Container (GPU-Accelerated)

**Build**:

```bash
docker build -t imgprep-api-gpu:latest -f Dockerfile.gpu .
```

**Run**:

```bash
docker run -d \
  --name imgprep-api-gpu \
  --gpus all \
  -p 8000:8000 \
  -v $(pwd)/models:/app/models:ro \
  -v $(pwd)/logs:/app/logs:rw \
  --env-file .env \
  imgprep-api-gpu:latest
```

**Configuration**:

- **Workers**: 2 (default in Dockerfile.gpu - fewer for GPU memory)
- **GPU**: NVIDIA CUDA 12.1.1 with cuDNN 8
- **Memory**: Adjust based on GPU VRAM (e.g., 14GB limit for T4 16GB GPU)

### Resource Limits (Standalone Docker)

For standalone Docker (non-Swarm), use runtime flags:

```bash
# CPU limits
docker run -d \
  --cpus="8" \
  --memory="32g" \
  --memory-reservation="16g" \
  ...

# GPU limits (VRAM managed by NVIDIA driver)
docker run -d \
  --gpus all \
  --memory="48g" \
  ...
```

### Health Check

```bash
# Check container health
docker ps --filter name=imgprep-api

# Test API endpoint
curl http://localhost:8000/health

# View logs
docker logs imgprep-api -f
```

---

## Celery Workers

### Redis Setup

**Start Redis (Docker)**:

```bash
docker run -d \
  --name redis \
  -p 6379:6379 \
  redis:7-alpine
```

**Verify Connection**:

```bash
redis-cli ping  # Should return PONG
```

### Install Worker Dependencies

```bash
uv sync --extra dev --extra workers
```

### Start Workers

**Default Worker** (standard document processing):

```bash
celery -A image_preprocessing_detector.workers worker -l info
```

**GPU Worker** (IQA inference, priority queue):

```bash
celery -A image_preprocessing_detector.workers worker -l info -Q gpu -c 2
```

**Batch Worker** (batch document processing):

```bash
celery -A image_preprocessing_detector.workers worker -l info -Q batch
```

**Multiple Queues**:

```bash
celery -A image_preprocessing_detector.workers worker -l info -Q default,gpu,batch
```

### Monitor with Flower

```bash
celery -A image_preprocessing_detector.workers flower --port=5555
# Open http://localhost:5555
```

### Configuration

**Environment Variables**:

```bash
export CELERY_BROKER_URL="redis://localhost:6379/0"
export CELERY_RESULT_BACKEND="redis://localhost:6379/1"
```

**Queue Configuration**:

- `default`: Standard document processing (no priority)
- `gpu`: IQA analysis (GPU-optimized, priority queue)
- `batch`: Batch document processing (high timeout, 300s limit)

**Concurrency Settings**:

- Default worker: Auto-detect CPUs
- GPU worker: `-c 2` (minimize prefetch for GPU tasks)
- Batch worker: `-c 4` (adjust based on available resources)

### Health Check

```bash
# Ping workers
celery -A image_preprocessing_detector.workers inspect ping

# Check active tasks
celery -A image_preprocessing_detector.workers inspect active

# Check registered tasks
celery -A image_preprocessing_detector.workers inspect registered
```

---

## Modal GPU Training

**Complete Reference**: [docs/reference/MODAL_QUICK_REFERENCE.md](../reference/MODAL_QUICK_REFERENCE.md)

### Setup Status

SETUP COMPLETE - Ready to run training!

- Modal installed and authenticated
- GCS credentials configured in Modal secrets
- GPU access verified

### Verify Setup (Optional)

```bash
# Verify Modal authentication
uv run modal profile list

# Verify GCS secret exists
uv run modal secret list | grep gcs-credentials

# Test GPU access
uv run modal run tmp_cleanup/modal_gpu_test.py
```

### Training Commands

**Phase 2: ResNet Teacher-Student IQA**:

```bash
# Start training (IMPORTANT: use --detach to keep running)
uv run modal run --detach modal/train_phase2_iqa.py

# Monitor from CLI
uv run modal app logs iqa-phase2-training --follow

# Monitor dashboard
open https://modal.com/apps
```

**Key Details**:

- **Teacher Model**: ResNet-50 (50 epochs, ~13-21 hours)
- **Student Model**: ResNet-18 (30 epochs, distilled from teacher)
- **Dataset**: OHR-Bench document IQA dataset via GCS (~18 GB)
- **Recommended GPU**: L4 (24GB VRAM, $0.80/h)
- **Cost**: $10.40-$16.80 or $0 with $30/month free tier

### GPU Selection Guide

| GPU | $/hour | VRAM | Best For | Speed vs T4 |
|-----|--------|------|----------|-------------|
| **T4** | **$0.59** | 16GB | Budget training, small models | 1.0x (baseline) |
| **L4** | **$0.80** | 24GB | **Recommended for Phase 2** | ~1.4x faster |
| **A10** | **$1.10** | 24GB | Large models, faster training | ~1.8x faster |

**Recommendation**: Use **L4 GPU** for Phase 2 training (best speed/cost balance, completes within free tier).

### GCS Dataset Integration

Datasets are loaded from GCS using Python `google-cloud-storage` library:

```python
from google.cloud import storage
client = storage.Client()
bucket = client.bucket("image_detection_b")
prefix = "image-preprocessing-detector/datasets/iqa_phase2/"
blobs = list(bucket.list_blobs(prefix=prefix))
# Parallel download with ThreadPoolExecutor (32 workers)
```

**Performance**: ~3,500 files/min with 32 workers (50,000 files in ~14 minutes).

### Check Usage

```bash
# Current month usage
uv run modal profile current

# Dashboard
open https://modal.com/usage
```

### Cancel Training

```bash
# Via dashboard (recommended)
open https://modal.com/apps
# Find run → Click "Cancel"

# Via CLI
uv run modal app stop image-detection
```

---

## Docling OCR Server

**Complete Reference**: [deployment/README.md](../../deployment/README.md)

### Architecture

Docling OCR server deployed on Docker VM (192.168.1.209) for dataset text extraction.

**System Resources**:

- CPU: 12 threads (Xeon E5-2690 v4)
- RAM: 62GB
- GPU: None (CPU-only)
- Storage: 37GB local + 1.4TB NFS

### Deployment Modes

**Standard Mode** (Faster):

```bash
./deployment/deploy-docling.sh standard
```

- Throughput: ~12 pages/second
- RAM Usage: ~16-24GB
- Best for: Born-digital documents, simple tables

**VLM Mode** (Higher Accuracy):

```bash
./deployment/deploy-docling.sh vlm
```

- Throughput: ~8-10 pages/second
- RAM Usage: ~24-32GB
- Model: GraniteDocling-258M
- Best for: Formulas, code blocks, complex layouts

**GCS Mode** (Recommended for large datasets):

```bash
./deployment/setup-gcs-processing.sh
```

- Downloads from GCS, uploads results to GCS
- Avoids NFS bottleneck

### Endpoints

| Endpoint | URL |
|----------|-----|
| API | `http://192.168.1.209:5001` |
| Web UI | `http://192.168.1.209:5001/ui` |
| API Docs | `http://192.168.1.209:5001/docs` |
| Health | `http://192.168.1.209:5001/health` |

### Usage Examples

**Health Check**:

```bash
curl http://192.168.1.209:5001/health
```

**Convert Single File**:

```bash
curl -X POST "http://192.168.1.209:5001/v1/convert/file" \
  -H "accept: application/json" \
  -F "file=@document.pdf" \
  -F "output_format=markdown"
```

**Convert from URL**:

```bash
curl -X POST "http://192.168.1.209:5001/v1/convert/source" \
  -H "Content-Type: application/json" \
  -d '{"sources": [{"kind": "http", "url": "https://arxiv.org/pdf/2501.17887"}]}'
```

### GCS Processing Workflow

**Step 1: Set Up Environment**:

```bash
./deployment/setup-gcs-processing.sh
```

**Step 2: Configure GCS Credentials**:

```bash
scp ~/gcs-service-account.json byron@192.168.1.209:/data/docling/secrets/gcs-credentials.json
```

**Step 3: Process Datasets**:

```bash
ssh byron@192.168.1.209
cd /data/docling/scripts
export GOOGLE_APPLICATION_CREDENTIALS=/data/docling/secrets/gcs-credentials.json

# List available datasets
python3 gcs_processor.py --list

# Process a dataset
python3 gcs_processor.py pubtabnet --workers 8 --batch-size 5000

# Dry run (list files without processing)
python3 gcs_processor.py tablebank --dry-run
```

**Step 4: Check Results**:

```bash
gsutil ls gs://image_detection_b/image-preprocessing-detector/extracted_text/
```

### Performance Tuning

**Standard Mode** (edit `docker-compose.docling.yml`):

```yaml
environment:
  - DOCLING_SERVE_WORKERS=8      # Increase for more parallelism
  - DOCLING_OCR_BATCH_SIZE=128   # Increase for more RAM usage
```

**VLM Mode** (edit `docker-compose.docling-vlm.yml`):

```yaml
environment:
  - DOCLING_SERVE_WORKERS=4      # Keep lower for VLM
  - DOCLING_VLM_CONCURRENCY=4    # VLM concurrent requests
```

### Monitoring

**Container Logs**:

```bash
ssh byron@192.168.1.209 "docker logs -f docling-serve"
```

**Resource Usage**:

```bash
ssh byron@192.168.1.209 "docker stats docling-serve"
```

---

## Monitoring & Alerting

### Prometheus Setup

**Configuration File**: `configs/monitoring/prometheus_alerts.yaml`

**Alert Groups**:

- `imgprep_errors`: High error rates, sustained errors
- `imgprep_latency`: P95/P99 latency degradation
- `imgprep_quality`: Quality drift, high teacher escalation
- `imgprep_budget`: Modal GPU budget warnings
- `imgprep_infrastructure`: GPU memory, queue depth, worker status
- `imgprep_throughput`: Throughput below targets

**Load Alert Rules**:

```yaml
# Add to prometheus.yml
rule_files:
  - /path/to/configs/monitoring/prometheus_alerts.yaml
```

### Key Alerts

**Critical Alerts** (require immediate action):

- `ImagePrepHighErrorRate`: Error rate >5% for 5 minutes
- `ImagePrepBudgetExceeded`: Daily Modal GPU spend >$10
- `ImagePrepNoWorkers`: All processing workers are down
- `ImagePrepModelNotLoaded`: ONNX model failed to load

**Warning Alerts** (monitor closely):

- `ImagePrepHighLatencyGPU`: P95 GPU latency >150ms
- `ImagePrepHighLatencyCPU`: P95 CPU latency >400ms
- `ImagePrepQualityDrift`: Median DQS dropped >10% vs 24h baseline
- `ImagePrepBudgetWarning`: Daily Modal GPU spend >$8 (80% of limit)

### Grafana Dashboards

**Recommended Panels**:

1. **Throughput**: Pages processed per second (GPU vs CPU)
2. **Latency**: P50, P95, P99 processing times
3. **Quality**: DQS distribution, teacher escalation rate
4. **Errors**: Error rate, error types distribution
5. **Budget**: Modal GPU spend (daily, monthly)
6. **Infrastructure**: GPU memory, queue depth, active workers

### Metrics Endpoints

**API Metrics** (if Prometheus client configured):

```bash
curl http://localhost:8000/metrics
```

**Celery Metrics** (via Flower):

```bash
curl http://localhost:5555/api/workers
curl http://localhost:5555/api/tasks
```

---

## Health Checks

### Local Development

**CLI Tool**:

```bash
uv run imgprep --version
uv run imgprep --help
```

**Python Import**:

```python
from image_preprocessing_detector.schema import DocumentMetadata
print("Import successful")
```

**Tests**:

```bash
uv run pytest tests/unit/test_schema.py -v
```

### Docker Containers

**API Health**:

```bash
curl -f http://localhost:8000/health || echo "UNHEALTHY"
```

**Container Health Status**:

```bash
docker inspect --format='{{.State.Health.Status}}' imgprep-api
```

### Celery Workers

**Ping Workers**:

```bash
celery -A image_preprocessing_detector.workers inspect ping
```

**Check Active Tasks**:

```bash
celery -A image_preprocessing_detector.workers inspect active
```

**Redis Connection**:

```bash
redis-cli ping  # Should return PONG
```

### Modal Training

**List Running Apps**:

```bash
uv run modal app list
```

**Check Specific App**:

```bash
uv run modal app describe image-detection
```

**View Logs**:

```bash
uv run modal app logs image-detection --tail 100
```

### Docling OCR Server

**Health Endpoint**:

```bash
curl http://192.168.1.209:5001/health
```

**Container Status**:

```bash
ssh byron@192.168.1.209 "docker ps --filter name=docling-serve"
```

**Resource Usage**:

```bash
ssh byron@192.168.1.209 "docker stats docling-serve --no-stream"
```

---

## Environment Variables

Complete reference from `.env.example`:

### Phase 1B: PDF Resolution & DPI Upscaling

```bash
# Enable PDF upscaling for low-resolution documents
IMAGE_PREP_ENABLE_PDF_UPSCALING=true

# Minimum DPI threshold - documents below this will be upscaled
IMAGE_PREP_PDF_MIN_DPI=300

# Target DPI for upscaling
IMAGE_PREP_PDF_TARGET_DPI=300

# Upscaling algorithm
# Options: lanczos (best quality), bicubic (balanced), inter_linear (fastest),
#          inter_cubic (high quality), inter_area (downsampling)
IMAGE_PREP_PDF_UPSCALE_ALGORITHM=lanczos

# Preserve original file if upscaling fails (recommended: true)
IMAGE_PREP_PDF_PRESERVE_ORIGINAL_ON_ERROR=true
```

### Model Artifact Storage (GCS + Hugging Face Hub)

```bash
# GCS Bucket for RAG Pipeline Models
GCS_BUCKET_NAME=rag-pipeline-models

# GCS Project ID
GCP_PROJECT_ID=your-gcp-project-id

# Google Application Credentials (path to service account JSON)
# SECURITY: Never commit this file to version control!
GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcp-service-account-key.json

# Hugging Face API Token
# Create at: https://huggingface.co/settings/tokens
HF_TOKEN=your-huggingface-token-here

# Hugging Face Username/Organization
HF_USERNAME=your-hf-username

# Default project name for artifact storage
MODEL_PROJECT_NAME=image-preprocessing-detector

# Dataset version tracking
DATASET_VERSION=v1.0.0
```

### Training Configuration

```bash
# Enable debug mode for verbose logging
DEBUG=false

# Random seed for reproducibility
RANDOM_SEED=42
```

### Celery Configuration (Phase 4)

```bash
# Redis connection URL for message broker
CELERY_BROKER_URL=redis://localhost:6379/0

# Redis connection URL for results
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### Budget Enforcement (Phase 4)

```bash
# Enable/disable Modal GPU budget tracking
IMGPREP_MODAL_BUDGET_ENABLED=true

# Daily budget limit in USD (resets at UTC midnight)
IMGPREP_MODAL_DAILY_BUDGET=10.00

# Monthly budget limit in USD (resets on month boundary)
IMGPREP_MODAL_MONTHLY_BUDGET=100.00

# GPU cost per hour in USD (default: T4 pricing)
IMGPREP_MODAL_GPU_COST_HOUR=0.36

# Warning threshold (0-1, triggers alert at this utilization %)
IMGPREP_MODAL_WARNING_THRESHOLD=0.80
```

### Device Orchestration (Phase 4)

```bash
# Inference mode: production, qa, development
IMGPREP_INFERENCE_MODE=production

# Allow CPU fallback for teacher model (not recommended for production)
IMGPREP_ALLOW_CPU_TEACHER=false

# Enable Modal GPU for teacher inference
IMGPREP_ENABLE_MODAL=true

# Teacher model budget limits (page counts)
IMGPREP_TEACHER_BUDGET_PER_DOC=10
IMGPREP_TEACHER_BUDGET_PER_BATCH=100
IMGPREP_TEACHER_BUDGET_MONTHLY_HOURS=10.0

# Modal connection settings
IMGPREP_MODAL_TIMEOUT_MS=30000
IMGPREP_MODAL_MAX_RETRIES=3
```

### API Configuration (Phase 5)

```bash
# API server configuration
IMGPREP_API_TITLE="Image Preprocessing Detector API"
IMGPREP_API_VERSION="0.1.0"

# GPU preference for API
IMGPREP_API_DEFAULT_PREFER_GPU=false  # Set to true for GPU containers
```

---

## Troubleshooting

### Local Development Issues

**Import Errors**:

```bash
# Ensure package is installed in editable mode
uv sync --extra dev
uv run pip install -e .
```

**Type Errors**:

```bash
# Run BasedPyright type checker (strict on src/)
uv run basedpyright src

# Check specific file
uv run basedpyright src/image_preprocessing_detector/schema.py
```

**Test Failures**:

```bash
# Check coverage threshold (80% minimum)
uv run pytest --cov=src --cov-report=term-missing

# Run specific failing test
uv run pytest tests/path/to/test.py::test_name -v

# Check pre-commit hooks
uv run pre-commit run --all-files
```

**Environment Issues**:

```bash
# Verify GPG and SSH keys
gpg --list-secret-keys
ssh-add -l
git config --get user.signingkey
```

### Docker Container Issues

**Container Won't Start**:

```bash
# Check logs
docker logs imgprep-api

# Check resource constraints
docker stats imgprep-api
```

**API Not Responding**:

```bash
# Check health endpoint
curl http://localhost:8000/health

# Check if container is running
docker ps --filter name=imgprep-api

# Restart container
docker restart imgprep-api
```

**GPU Not Detected** (Dockerfile.gpu):

```bash
# Verify NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi

# Check NVIDIA Container Toolkit
nvidia-container-cli info
```

### Celery Worker Issues

**Workers Not Starting**:

```bash
# Check Redis connection
redis-cli ping

# Check Celery configuration
celery -A image_preprocessing_detector.workers inspect conf

# Start worker with verbose logging
celery -A image_preprocessing_detector.workers worker -l debug
```

**Tasks Not Processing**:

```bash
# Check queue lengths
celery -A image_preprocessing_detector.workers inspect active_queues

# Check registered tasks
celery -A image_preprocessing_detector.workers inspect registered

# Purge queue (CAUTION: deletes all pending tasks)
celery -A image_preprocessing_detector.workers purge
```

**High Memory Usage**:

```bash
# Reduce worker concurrency
celery -A image_preprocessing_detector.workers worker -c 2

# Reduce prefetch multiplier (default: 1)
celery -A image_preprocessing_detector.workers worker --prefetch-multiplier 1
```

### Modal Training Issues

**Authentication Failed**:

```bash
# Re-authenticate
uv run modal token new

# Verify token
uv run modal token current
```

**GCS Access Failed**:

```bash
# Verify secret exists
uv run modal secret list | grep gcs-credentials

# Re-create secret
uv run modal secret create gcs-credentials \
  GOOGLE_APPLICATION_CREDENTIALS=@/path/to/key.json

# Test GCS access locally
gsutil ls gs://rag-pipeline-models/
```

**Out of Memory (OOM)**:

```bash
# Reduce batch size in config (configs/modal_phase2_iqa.yaml)
# Upgrade to A10 GPU (24GB vs T4 16GB)
# Enable gradient accumulation in training script
```

**Training Stuck/Slow**:

```bash
# Check logs
uv run modal app logs iqa-phase2-training --tail 100

# Check GPU utilization (via Modal dashboard)
open https://modal.com/apps

# Cancel and restart
uv run modal app stop image-detection
uv run modal run --detach modal/train_phase2_iqa.py
```

### Docling OCR Server Issues

**Container Won't Start**:

```bash
# Check logs
ssh byron@192.168.1.209 "docker logs docling-serve"

# Check resources
ssh byron@192.168.1.209 "free -h && df -h"
```

**Slow Processing**:

```bash
# Check CPU usage
ssh byron@192.168.1.209 "docker stats docling-serve"

# Increase workers if CPU underutilized
# Edit docker-compose file: DOCLING_SERVE_WORKERS=12

# Decrease batch size if RAM constrained
# Edit docker-compose file: DOCLING_OCR_BATCH_SIZE=64
```

**GCS Authentication Failed**:

```bash
# Test GCS access
ssh byron@192.168.1.209 \
  "GOOGLE_APPLICATION_CREDENTIALS=/data/docling/secrets/gcs-credentials.json \
   gsutil ls gs://image_detection_b/"

# Re-copy credentials
scp ~/gcs-service-account.json byron@192.168.1.209:/data/docling/secrets/gcs-credentials.json
```

**VLM Model Download Slow**:

```bash
# First startup downloads ~1GB GraniteDocling model
# Wait for health check or pre-download:
ssh byron@192.168.1.209 "docker exec docling-serve python -c \
  \"from transformers import AutoModel; AutoModel.from_pretrained('ibm-granite/granite-docling-258M')\""
```

### Performance Issues

**High Latency**:

```bash
# Check Prometheus alerts
curl http://localhost:9090/api/v1/alerts

# GPU: P95 target <150ms, CPU: P95 target <400ms
# If exceeded, check GPU memory, batch sizes, worker concurrency
```

**Low Throughput**:

```bash
# GPU target: >6 pages/sec, CPU target: >2 pages/sec
# Increase worker count or GPU concurrency
# Check queue depth and backlog
```

**Quality Drift**:

```bash
# Check median DQS over time
# Compare current 1h median vs 24h baseline
# Investigate if >10% drop detected
```

---

## Quick Command Reference

### Local Development

```bash
uv sync --extra dev --extra ml     # Install dependencies
uv run pre-commit install           # Setup pre-commit hooks
uv run imgprep --help               # Run CLI tool
uv run pytest -v                    # Run tests
uv run ruff format src tests        # Format code
uv run basedpyright src             # Type checking
```

### Docker

```bash
docker build -t imgprep-api -f Dockerfile .              # Build CPU
docker build -t imgprep-api-gpu -f Dockerfile.gpu .      # Build GPU
docker run -d -p 8000:8000 imgprep-api                   # Run CPU
docker run -d --gpus all -p 8000:8000 imgprep-api-gpu    # Run GPU
curl http://localhost:8000/health                         # Health check
```

### Celery

```bash
celery -A image_preprocessing_detector.workers worker -l info     # Start worker
celery -A image_preprocessing_detector.workers flower             # Start Flower
celery -A image_preprocessing_detector.workers inspect ping       # Check workers
```

### Modal

```bash
uv run modal run --detach modal/train_phase2_iqa.py      # Start training
uv run modal app logs iqa-phase2-training --follow        # Monitor logs
uv run modal app list                                     # List running apps
open https://modal.com/apps                               # Dashboard
```

### Docling OCR

```bash
./deployment/deploy-docling.sh standard                   # Deploy standard
./deployment/deploy-docling.sh vlm                        # Deploy VLM
curl http://192.168.1.209:5001/health                     # Health check
ssh byron@192.168.1.209 "docker logs -f docling-serve"    # View logs
```

---

## Additional Resources

- **Modal Quick Reference**: [docs/reference/MODAL_QUICK_REFERENCE.md](../reference/MODAL_QUICK_REFERENCE.md)
- **Docling Deployment Guide**: [deployment/README.md](../../deployment/README.md)
- **Architecture Documentation**: [docs/architecture/](../architecture/)
- **Dataset Quick Reference**: [docs/datasets/DATASET_QUICK_REFERENCE.md](../datasets/DATASET_QUICK_REFERENCE.md)
- **Project Plan**: [docs/planning/PROJECT_PLAN.md](../planning/PROJECT_PLAN.md)

---

**Last Updated**: 2026-02-10
**Maintainer**: Documentation Team
**Version**: 1.0.0
