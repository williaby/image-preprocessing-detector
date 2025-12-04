---
schema_type: common
title: "Deployment Guide"
description: "Comprehensive deployment guide for Image Preprocessing Detector API"
tags:
  - deployment
  - documentation
status: published
owner: core-maintainer
authors:
  - name: "Byron Williams"
purpose: "Guide for deploying the API across different environments and platforms."
---

Complete guide for deploying the Image Preprocessing Detector API across different environments and platforms.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Environment Configuration](#environment-configuration)
- [Monitoring & Logging](#monitoring--logging)
- [Troubleshooting](#troubleshooting)

---

## Overview

The Image Preprocessing Detector API can be deployed in multiple configurations:

1. **Local Development** - Direct Python execution with uv
2. **Docker** - Containerized single-instance deployment
3. **Docker Compose** - Multi-container local stack
4. **Kubernetes** - Production-grade orchestrated deployment

**Recommended for Production**: Kubernetes with Helm charts

---

## Prerequisites

### All Deployments

- Python 3.11+ (for local development)
- Git
- Environment variables configured (see [Environment Configuration](#environment-configuration))

### Docker Deployments

- Docker 24.0+
- Docker Compose 2.20+ (for compose deployments)

### Kubernetes Deployments

- Kubernetes 1.20+
- Helm 3.8+
- kubectl configured
- Container registry access (GHCR, Docker Hub, etc.)

---

## Local Development

### Quick Start

```bash
# Clone repository
git clone https://github.com/yourusername/image_detection.git
cd image_detection

# Install dependencies
uv sync --extra dev

# Run API server
uv run uvicorn image_preprocessing_detector.api.app:app --reload --host 0.0.0.0 --port 8000
```

**Access**: <http://localhost:8000>

**Docs**: <http://localhost:8000/docs>

### Development Server Options

```bash
# With custom host/port
uv run uvicorn image_preprocessing_detector.api.app:app --host 127.0.0.1 --port 8080

# With auto-reload (development)
uv run uvicorn image_preprocessing_detector.api.app:app --reload

# With multiple workers (production-like)
uv run uvicorn image_preprocessing_detector.api.app:app --workers 4

# With custom log level
uv run uvicorn image_preprocessing_detector.api.app:app --log-level debug
```

### Environment Setup

Create `.env` file:

```bash
# API Configuration
IMGPREP_API_TITLE="Image Preprocessing Detector API - Dev"
IMGPREP_API_VERSION="0.1.0-dev"
IMGPREP_API_LOG_LEVEL="DEBUG"

# Disable auth for local dev
IMGPREP_API_AUTH_ENABLED=false
IMGPREP_API_RATE_LIMIT_ENABLED=false

# File limits
IMGPREP_API_MAX_FILE_SIZE_MB=50
IMGPREP_API_MAX_BATCH_SIZE=100
```

---

## Docker Deployment

### Build Docker Image

```bash
# Standard CPU-only image
docker build -t image-preprocessing-detector:latest -f Dockerfile .

# GPU-enabled image
docker build -t image-preprocessing-detector:gpu -f Dockerfile.gpu .
```

### Run Container

#### CPU-only

```bash
docker run -d \
  --name imgprep-api \
  -p 8000:8000 \
  -e IMGPREP_API_AUTH_ENABLED=false \
  -v $(pwd)/models:/app/models \
  image-preprocessing-detector:latest
```

#### GPU-enabled

```bash
docker run -d \
  --name imgprep-api-gpu \
  --gpus all \
  -p 8000:8000 \
  -e IMGPREP_API_AUTH_ENABLED=false \
  -v $(pwd)/models:/app/models \
  image-preprocessing-detector:gpu
```

### Docker Compose

**File**: `docker-compose.yml` (create in project root)

```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - IMGPREP_API_AUTH_ENABLED=false
      - IMGPREP_API_RATE_LIMIT_ENABLED=false
      - IMGPREP_API_LOG_LEVEL=DEBUG
    volumes:
      - ./models:/app/models
      - ./data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Optional: Redis for batch job storage (multi-worker deployments)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped
```

**Start**:

```bash
docker-compose up -d
```

**Stop**:

```bash
docker-compose down
```

**Logs**:

```bash
docker-compose logs -f api
```

### Verify Container Size

```bash
docker images image-preprocessing-detector:latest
# Should be <2GB (Phase 5 success criteria)
```

---

## Kubernetes Deployment

### Using kubectl (Raw Manifests)

```bash
# Apply manifests directly
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml
```

### Using Helm (Recommended)

#### Development Environment

```bash
helm install imgprep-api ./charts/image-preprocessing-detector \
  -f charts/image-preprocessing-detector/values-dev.yaml \
  --namespace imgprep-dev \
  --create-namespace
```

#### Staging Environment

```bash
helm install imgprep-api ./charts/image-preprocessing-detector \
  --namespace imgprep-staging \
  --create-namespace \
  --set image.tag=v1.0.0-rc.1 \
  --set ingress.hosts[0].host=api-staging.example.com
```

#### Production Environment

```bash
helm install imgprep-api ./charts/image-preprocessing-detector \
  -f charts/image-preprocessing-detector/values-prod.yaml \
  --namespace imgprep-prod \
  --create-namespace \
  --set image.tag=v1.0.0 \
  --set secrets.apiKeys="$PROD_API_KEYS"
```

### Helm Operations

**Upgrade**:

```bash
helm upgrade imgprep-api ./charts/image-preprocessing-detector \
  -f charts/image-preprocessing-detector/values-prod.yaml \
  --namespace imgprep-prod \
  --set image.tag=v1.1.0
```

**Rollback**:

```bash
helm rollback imgprep-api -n imgprep-prod
```

**Uninstall**:

```bash
helm uninstall imgprep-api -n imgprep-prod
```

**List Releases**:

```bash
helm list -A
```

### GPU Node Configuration

**Node Labels** (if not auto-labeled):

```bash
kubectl label nodes <node-name> accelerator=nvidia-tesla-t4
```

**Helm Values** (`values-gpu.yaml`):

```yaml
gpu:
  enabled: true
  count: 1
  type: "nvidia.com/gpu"

nodeSelector:
  accelerator: nvidia-tesla-t4

tolerations:
  - key: nvidia.com/gpu
    operator: Exists
    effect: NoSchedule
```

**Deploy**:

```bash
helm install imgprep-api ./charts/image-preprocessing-detector \
  -f values-gpu.yaml \
  --namespace imgprep-gpu
```

---

## Environment Configuration

### Environment Variables Matrix

| Variable | Dev | Staging | Prod | Description |
|----------|-----|---------|------|-------------|
| `IMGPREP_API_TITLE` | Custom | Custom | Custom | API title |
| `IMGPREP_API_VERSION` | dev | rc.X | X.Y.Z | API version |
| `IMGPREP_API_LOG_LEVEL` | DEBUG | INFO | INFO | Log verbosity |
| `IMGPREP_API_AUTH_ENABLED` | false | true | true | Enable auth |
| `IMGPREP_API_RATE_LIMIT_ENABLED` | false | true | true | Rate limiting |
| `IMGPREP_API_MAX_FILE_SIZE_MB` | 50 | 50 | 50 | Max upload size |
| `IMGPREP_API_MAX_BATCH_SIZE` | 100 | 100 | 100 | Max batch files |
| `IMGPREP_API_CORS_ENABLED` | true | true | true | CORS support |
| `IMGPREP_API_CORS_ORIGINS` | ["*"] | ["https://staging.example.com"] | ["https://example.com"] | Allowed origins |
| `IMGPREP_API_KEYS` | N/A | secret | secret | API keys |
| `IMGPREP_API_INTERNAL_CALLERS` | N/A | ["10.0.0.0/8"] | ["10.0.0.0/8"] | Internal IPs |

### Secrets Management

#### Local Development

```bash
# Use .env file (not committed)
echo "IMGPREP_API_KEYS=dev-key-1,dev-key-2" > .env
```

#### Kubernetes

```bash
# Create secret
kubectl create secret generic imgprep-api-secret \
  --from-literal=api-keys="prod-key-1,prod-key-2" \
  --from-literal=internal-callers='["10.0.0.0/8"]' \
  -n imgprep-prod
```

#### Helm (Recommended)

```bash
# Via values file (encrypted with sops/sealed-secrets)
helm install imgprep-api ./charts/image-preprocessing-detector \
  --set secrets.apiKeys="prod-key-1,prod-key-2"
```

---

## Monitoring & Logging

### Health Checks

**Liveness** (is service running):

```bash
curl http://localhost:8000/health
```

**Readiness** (can service handle traffic):

```bash
curl http://localhost:8000/ready
```

**Version**:

```bash
curl http://localhost:8000/version
```

### Kubernetes Probes

Configured in Helm chart:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: http
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: http
  initialDelaySeconds: 10
  periodSeconds: 5
```

### Logs

**Docker**:

```bash
docker logs -f imgprep-api
```

**Kubernetes**:

```bash
kubectl logs -l app.kubernetes.io/name=image-preprocessing-detector -f -n imgprep-prod
```

**Structured Logging** (JSON format):

```json
{
  "event": "process_request_received",
  "filename": "document.pdf",
  "content_type": "application/pdf",
  "prefer_gpu": true,
  "correlation_id": "abc123",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Prometheus Metrics

**Endpoint**: `/metrics` (if enabled)

**Key Metrics**:

- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency
- `processing_time_seconds` - Document processing time
- `model_inference_seconds` - ML model inference time
- `gpu_utilization_percent` - GPU usage (if available)

---

## Troubleshooting

### Common Issues

#### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

#### Models Not Loading

```bash
# Check model files exist
ls -lh models/iqa/onnx/

# Verify permissions
chmod -R 755 models/

# Check logs for model loading errors
docker logs imgprep-api | grep "model"
```

#### High Memory Usage

```bash
# Check container memory
docker stats imgprep-api

# In Kubernetes
kubectl top pods -n imgprep-prod
```

**Solutions**:

- Reduce batch size
- Enable model pre-loading (one-time memory cost)
- Increase resource limits

#### API Returns 503 (Not Ready)

```bash
# Check readiness endpoint
curl http://localhost:8000/ready

# Common causes:
# - Models failed to load
# - Device probe failed
# - Configuration invalid
```

### Debug Mode

Enable verbose logging:

```bash
# Environment variable
export IMGPREP_API_LOG_LEVEL=DEBUG

# Kubernetes
kubectl set env deployment/imgprep-api IMGPREP_API_LOG_LEVEL=DEBUG -n imgprep-prod
```

### Performance Issues

**Symptom**: High latency (>500ms per request)

**Diagnosis**:

```bash
# Check GPU availability
curl http://localhost:8000/ready | jq '.device'

# Monitor processing time
kubectl logs -l app.kubernetes.io/name=image-preprocessing-detector -n imgprep-prod | grep "processing_time_ms"
```

**Solutions**:

- Enable GPU if available
- Reduce concurrent requests
- Scale horizontally (more replicas)
- Pre-load models (eliminate cold start)

### Rollback Procedure

#### Helm

```bash
# List release history
helm history imgprep-api -n imgprep-prod

# Rollback to previous version
helm rollback imgprep-api -n imgprep-prod

# Rollback to specific revision
helm rollback imgprep-api 3 -n imgprep-prod
```

#### Kubernetes (manual)

```bash
# Rollback deployment
kubectl rollout undo deployment/imgprep-api -n imgprep-prod

# Rollback to specific revision
kubectl rollout undo deployment/imgprep-api --to-revision=2 -n imgprep-prod
```

---

## Best Practices

1. **Always test in staging before production**
2. **Use Helm for multi-environment deployments**
3. **Enable autoscaling in production (HPA)**
4. **Monitor health/ready endpoints continuously**
5. **Set resource limits to prevent resource exhaustion**
6. **Use immutable image tags (not `latest`)**
7. **Encrypt secrets (never commit plaintext)**
8. **Configure log rotation for long-running containers**
9. **Test rollback procedures regularly**
10. **Document environment-specific configurations**

---

## Additional Resources

- [REST API Documentation](../api/rest-api.md)
- [Helm Chart README](../../charts/image-preprocessing-detector/README.md)
- [Load Testing Guide](../../tests/load/README.md)
- [Docker Compose Examples](https://docs.docker.com/compose/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
