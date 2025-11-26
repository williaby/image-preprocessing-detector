# Deployment Guide

Complete guide for deploying the Image Preprocessing Detector API across different environments.

## Deployment Options

| Option | Best For | GPU Support | Complexity |
|--------|----------|-------------|------------|
| Local (Poetry) | Development | Yes (local) | Low |
| Docker Compose | Single server | Optional | Medium |
| Kubernetes | Production scale | Yes (node pools) | High |
| Modal | Serverless GPU | Yes (auto-scale) | Low |

---

## Local Development

### Prerequisites

- Python 3.11+
- Poetry 2.0+
- CUDA 12.1+ (optional, for GPU)

### Installation

```bash
# Clone repository
git clone https://github.com/williaby/image-preprocessing-detector.git
cd image-preprocessing-detector

# Install dependencies
poetry install --with dev --extras api

# Verify installation
poetry run imgprep --version
```

### Running the API

```bash
# Development server (auto-reload)
poetry run uvicorn image_preprocessing_detector.api.app:app \
  --host 0.0.0.0 --port 8000 --reload

# Production-like (multiple workers)
poetry run uvicorn image_preprocessing_detector.api.app:app \
  --host 0.0.0.0 --port 8000 --workers 4

# With specific log level
poetry run uvicorn image_preprocessing_detector.api.app:app \
  --host 0.0.0.0 --port 8000 --log-level info
```

### Verify Deployment

```bash
# Health check
curl http://localhost:8000/health

# Readiness (includes device detection)
curl http://localhost:8000/ready

# Test processing
curl -X POST http://localhost:8000/process \
  -F "file=@test.pdf"
```

---

## Docker Deployment

### Build Images

```bash
# Build CPU image
docker build -t image-preprocessing-detector:latest .

# Build GPU image (requires NVIDIA Docker)
docker build -f Dockerfile.gpu -t image-preprocessing-detector:gpu .
```

### Run with Docker

```bash
# CPU-only
docker run -d -p 8000:8000 \
  --name imgprep-api \
  -e IMGPREP_API_AUTH_ENABLED=false \
  image-preprocessing-detector:latest

# With GPU (requires nvidia-docker)
docker run -d -p 8000:8000 \
  --name imgprep-api-gpu \
  --gpus all \
  -e IMGPREP_API_DEFAULT_PREFER_GPU=true \
  image-preprocessing-detector:gpu
```

### Docker Compose

```bash
# Start CPU service
docker-compose up -d api

# Start with Redis for production rate limiting
docker-compose --profile production up -d

# Start GPU service (requires NVIDIA Docker)
docker-compose --profile gpu up -d api-gpu

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

### Docker Compose Profiles

| Profile | Services | Description |
|---------|----------|-------------|
| (default) | api | CPU-only API on port 8000 |
| production | api, redis | API + Redis for rate limiting |
| gpu | api-gpu | GPU-enabled API on port 8001 |

---

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster 1.25+
- kubectl configured
- NGINX Ingress Controller
- (Optional) cert-manager for TLS

### Quick Start

```bash
# Deploy all resources
kubectl apply -k k8s/

# Or step by step
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/ingress.yaml
```

### Configure Secrets

**Important**: Replace placeholder values before deploying.

```bash
# Create secret with real values
kubectl create secret generic imgprep-secret \
  --from-literal=IMGPREP_API_AUTH_ENABLED=true \
  --from-literal=IMGPREP_API_API_KEYS='key1,key2,key3' \
  --from-literal=IMGPREP_API_INTERNAL_CALLERS='["10.0.0.0/8"]' \
  --namespace=imgprep
```

### Verify Deployment

```bash
# Check pods
kubectl get pods -n imgprep

# Check service
kubectl get svc -n imgprep

# Port forward for local access
kubectl port-forward svc/imgprep-api 8000:80 -n imgprep

# Test health
curl http://localhost:8000/health
```

### Scaling

```bash
# Check HPA status
kubectl get hpa -n imgprep

# Manual scaling
kubectl scale deployment imgprep-api --replicas=5 -n imgprep
```

### GPU Node Pools (GKE/EKS/AKS)

For GPU support, use node selectors or tolerations:

```yaml
# Add to deployment.yaml
spec:
  template:
    spec:
      nodeSelector:
        cloud.google.com/gke-accelerator: nvidia-tesla-t4
      tolerations:
        - key: nvidia.com/gpu
          operator: Exists
          effect: NoSchedule
```

---

## Modal Deployment

Modal provides serverless GPU compute for teacher model inference.

### Setup

```bash
# Install Modal
pip install modal

# Authenticate
modal token new

# Verify
modal token current
```

### Configure Secrets

```bash
# Add GCS credentials for model storage
modal secret create gcs-credentials \
  GOOGLE_APPLICATION_CREDENTIALS_JSON="$(cat service-account.json)"
```

### Deploy Functions

```bash
# Deploy training function (Phase 2)
modal deploy modal/train_phase2_iqa.py

# Run training
modal run modal/train_phase2_iqa.py
```

### Integration with API

The API automatically uses Modal for teacher inference when:

1. `enable_teacher=true` in request
2. No local GPU available
3. Modal credentials configured

```python
# Environment variable to enable Modal fallback
export IMGPREP_MODAL_ENABLED=true
export IMGPREP_MODAL_APP_NAME=image-detection
```

---

## Environment Variables

### Core Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `IMGPREP_API_TITLE` | Image Preprocessing Detector API | API title |
| `IMGPREP_API_VERSION` | 0.1.0 | API version |
| `IMGPREP_API_DESCRIPTION` | ... | API description |

### CORS Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `IMGPREP_API_CORS_ENABLED` | true | Enable CORS |
| `IMGPREP_API_CORS_ORIGINS` | ["*"] | Allowed origins (JSON array) |
| `IMGPREP_API_CORS_ALLOW_CREDENTIALS` | true | Allow credentials |
| `IMGPREP_API_CORS_ALLOW_METHODS` | ["*"] | Allowed methods |
| `IMGPREP_API_CORS_ALLOW_HEADERS` | ["*"] | Allowed headers |

### Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `IMGPREP_API_AUTH_ENABLED` | false | Enable API key auth |
| `IMGPREP_API_API_KEYS` | [] | Valid API keys (comma-separated) |
| `IMGPREP_API_INTERNAL_CALLERS` | [] | IP allowlist (JSON array) |

### Rate Limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `IMGPREP_API_RATE_LIMIT_ENABLED` | true | Enable rate limiting |
| `IMGPREP_API_RATE_LIMIT_REQUESTS` | 100 | Max requests per window |
| `IMGPREP_API_RATE_LIMIT_WINDOW_SECONDS` | 60 | Window duration |

### Processing Limits

| Variable | Default | Description |
|----------|---------|-------------|
| `IMGPREP_API_MAX_BATCH_SIZE` | 100 | Max files per batch |
| `IMGPREP_API_MAX_FILE_SIZE_MB` | 50 | Max file size |
| `IMGPREP_API_PROCESS_TIMEOUT_SECONDS` | 300 | Single doc timeout |
| `IMGPREP_API_BATCH_TIMEOUT_SECONDS` | 3600 | Batch job timeout |

### Processing Options

| Variable | Default | Description |
|----------|---------|-------------|
| `IMGPREP_API_DEFAULT_PREFER_GPU` | true | Prefer GPU by default |
| `IMGPREP_API_DEFAULT_ENABLE_CORRECTIONS` | true | Enable corrections |
| `IMGPREP_API_DEFAULT_ENABLE_TEACHER` | false | Enable teacher model |

### Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `IMGPREP_API_LOG_REQUEST_BODY` | false | Log request bodies |
| `IMGPREP_API_LOG_RESPONSE_BODY` | false | Log response bodies |

---

## Secrets Checklist

Before deploying to production, ensure these secrets are configured:

| Secret | Environment | Required |
|--------|-------------|----------|
| API Keys | `IMGPREP_API_API_KEYS` | If auth enabled |
| GCS Credentials | Modal secret | If using Modal |
| TLS Certificate | K8s secret | If using HTTPS |
| Redis Password | Docker/K8s | If using Redis |

### Secure Secret Management

**Docker**:

```bash
# Use Docker secrets or environment files
docker run --env-file .env.production ...
```

**Kubernetes**:

```bash
# Use sealed-secrets for GitOps
kubeseal --format=yaml < secret.yaml > sealed-secret.yaml

# Or external-secrets for Vault/AWS Secrets Manager
```

---

## Troubleshooting

### Cold Start Issues

**Symptom**: First request takes 10-30 seconds

**Cause**: Model loading on first inference

**Solutions**:

1. Configure Kubernetes readiness probe with sufficient `initialDelaySeconds`
2. Pre-warm models on startup (configured by default)
3. Use larger instance memory to cache models

```yaml
# K8s: Increase startup time allowance
readinessProbe:
  initialDelaySeconds: 30  # Increase from 5
  periodSeconds: 10
```

### GPU Detection Issues

**Symptom**: GPU available but not detected

**Check GPU status**:

```bash
# Local
nvidia-smi

# In container
docker exec imgprep-api nvidia-smi

# Via API
curl http://localhost:8000/ready | jq '.device'
```

**Common Causes**:

1. CUDA drivers not installed
2. NVIDIA Docker runtime not configured
3. Container not started with `--gpus all`

**Fix for Docker**:

```bash
# Verify NVIDIA Docker
docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi

# Run API with GPU
docker run --gpus all -p 8000:8000 image-preprocessing-detector:gpu
```

### Memory Issues

**Symptom**: OOM errors during batch processing

**Solutions**:

1. Reduce batch size: `IMGPREP_API_MAX_BATCH_SIZE=50`
2. Increase container memory limits
3. Process large PDFs page-by-page

```yaml
# K8s: Increase memory
resources:
  limits:
    memory: "4Gi"  # Increase from 2Gi
```

### Rate Limit Issues

**Symptom**: 429 errors with valid usage

**Solutions**:

1. Increase limit: `IMGPREP_API_RATE_LIMIT_REQUESTS=200`
2. Use API key-based rate limiting (separate limits per key)
3. Add internal caller IP to allowlist

### Network Timeout Issues

**Symptom**: Timeouts during large file uploads

**Solutions**:

1. Increase client timeout
2. Configure NGINX ingress timeouts:

   ```yaml
   nginx.ingress.kubernetes.io/proxy-read-timeout: "600"
   nginx.ingress.kubernetes.io/proxy-body-size: "100m"
   ```

3. Use chunked uploads for very large files

---

## Health Monitoring

### Prometheus Metrics

The API exposes Prometheus-compatible metrics (when configured):

```bash
curl http://localhost:8000/metrics
```

### Kubernetes Health Checks

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  periodSeconds: 10
```

### Log Aggregation

Configure structured logging output:

```bash
# JSON logs for ELK/Loki
export IMGPREP_LOG_FORMAT=json

# View structured logs
docker logs imgprep-api | jq '.'
```

---

## Performance Tuning

### Worker Configuration

| Deployment | Recommended Workers | Notes |
|------------|---------------------|-------|
| CPU-only | 4-8 | 1 per CPU core |
| GPU | 2 | Limited by GPU memory |
| Mixed | 4 CPU + 2 GPU | Separate services |

### Batch Processing Optimization

```bash
# Optimal batch sizes by device
IMGPREP_API_MAX_BATCH_SIZE=100  # CPU
IMGPREP_API_MAX_BATCH_SIZE=50   # GPU (memory limited)
```

### Caching

Models are cached in memory after first load. For K8s, consider:

- Using init containers for model download
- Persistent volumes for model cache
- Node-local SSD for faster loading
