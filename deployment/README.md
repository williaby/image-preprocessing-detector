# Docling OCR Server Deployment

Deploy IBM Docling OCR server on Docker VM (192.168.1.209) for dataset text extraction.

## Architecture

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                      GCS-Based Processing Pipeline                       │
└─────────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐         ┌──────────────────┐         ┌──────────────┐
    │     GCS      │         │    Docker VM     │         │     GCS      │
    │   (Source)   │ ──────► │  192.168.1.209   │ ──────► │   (Output)   │
    │              │         │                  │         │              │
    │ datasets/    │  gsutil │ ┌──────────────┐ │  gsutil │ extracted_   │
    │  pubtabnet/  │  -m cp  │ │   Docling    │ │  -m cp  │  text/       │
    │  tablebank/  │ ──────► │ │   Server     │ │ ──────► │  pubtabnet/  │
    │  doclaynet/  │         │ │  (8 workers) │ │         │  tablebank/  │
    │  ...         │         │ └──────────────┘ │         │  ...         │
    └──────────────┘         └──────────────────┘         └──────────────┘
                                     │
                              62GB RAM / 12 CPU
                              ~12 pages/second
```

**Why GCS-based?**

- NFS is slow for large file operations
- Datasets already stored in GCS
- Only extracted text (small) uploaded back
- Parallel download with `gsutil -m`

## System Resources

| Resource | Docker VM | Allocation |
|----------|-----------|------------|
| CPU | 12 threads (Xeon E5-2690 v4) | 8-10 threads |
| RAM | 62GB | 32-48GB |
| GPU | None | CPU-only |
| Storage | 37GB local + 1.4TB NFS | Local for processing |

## Quick Start (GCS Workflow)

```bash
# 1. Set up GCS processing environment
./setup-gcs-processing.sh

# 2. Process a dataset
ssh byron@192.168.1.209
cd /data/docling/scripts
export GOOGLE_APPLICATION_CREDENTIALS=/data/docling/secrets/gcs-credentials.json
python3 gcs_processor.py pubtabnet --workers 8
```

## Deployment Modes

### Standard Mode (Faster)

- **Throughput**: ~12 pages/second
- **RAM Usage**: ~16-24GB
- **Best for**: Born-digital documents, simple tables

```bash
./deploy-docling.sh standard
```

### VLM Mode (Higher Accuracy)

- **Throughput**: ~8-10 pages/second
- **RAM Usage**: ~24-32GB
- **Model**: GraniteDocling-258M
- **Best for**: Formulas, code blocks, complex layouts

```bash
./deploy-docling.sh vlm
```

### GCS Mode (Recommended)

- **Throughput**: ~12 pages/second
- **Storage**: Downloads from GCS, uploads results to GCS
- **Best for**: Large datasets, avoiding NFS bottleneck

```bash
./setup-gcs-processing.sh
```

## GCS Processing Workflow

### Step 1: Set Up Environment

```bash
./setup-gcs-processing.sh
```

This script:

1. Installs gcloud CLI on Docker VM
2. Sets up service account authentication
3. Creates processing directories
4. Deploys Docling container
5. Installs Python processing script

### Step 2: Configure GCS Credentials

Copy your service account JSON:

```bash
scp ~/gcs-service-account.json byron@192.168.1.209:/data/docling/secrets/gcs-credentials.json
```

Or authenticate interactively:

```bash
ssh byron@192.168.1.209
gcloud auth application-default login
```

### Step 3: Process Datasets

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

### Step 4: Check Results

Results are uploaded to:

```text
gs://image_detection_b/image-preprocessing-detector/extracted_text/<dataset>/
```

## Endpoints

| Endpoint | URL |
|----------|-----|
| API | `http://192.168.1.209:5001` |
| Web UI | `http://192.168.1.209:5001/ui` |
| API Docs | `http://192.168.1.209:5001/docs` |
| Health | `http://192.168.1.209:5001/health` |

## Usage Examples

### Health Check

```bash
curl http://192.168.1.209:5001/health
```

### Convert Single File

```bash
curl -X POST "http://192.168.1.209:5001/v1/convert/file" \
  -H "accept: application/json" \
  -F "file=@document.pdf" \
  -F "output_format=markdown"
```

### Convert from URL

```bash
curl -X POST "http://192.168.1.209:5001/v1/convert/source" \
  -H "Content-Type: application/json" \
  -d '{"sources": [{"kind": "http", "url": "https://arxiv.org/pdf/2501.17887"}]}'
```

## Integration with Project A

Use the client module in `src/image_preprocessing_detector/text_extraction/`:

```python
from image_preprocessing_detector.text_extraction import DoclingClient

client = DoclingClient(host="192.168.1.209", port=5001)

# Extract text from single file
result = await client.extract_text(Path("document.pdf"))
print(result.text)

# Batch process dataset
async for result in client.extract_batch(image_paths, concurrency=16):
    save_to_metadata(result)
```

## Performance Tuning

### Standard Mode

Edit `docker-compose.docling.yml`:

```yaml
environment:
  - DOCLING_SERVE_WORKERS=8      # Increase for more parallelism
  - DOCLING_OCR_BATCH_SIZE=128   # Increase for more RAM usage
```

### VLM Mode

Edit `docker-compose.docling-vlm.yml`:

```yaml
environment:
  - DOCLING_SERVE_WORKERS=4      # Keep lower for VLM
  - DOCLING_VLM_CONCURRENCY=4    # VLM concurrent requests
```

### GCS Mode

Edit `scripts/gcs_processor.py` arguments:

```bash
python3 gcs_processor.py pubtabnet \
  --workers 16 \
  --batch-size 10000 \
  --use-tmpfs
# --workers: Concurrent API requests
# --batch-size: Files per batch
# --use-tmpfs: Use RAM for faster I/O
```

## Monitoring

### Container Logs

```bash
ssh byron@192.168.1.209 "docker logs -f docling-serve"
```

### Resource Usage

```bash
ssh byron@192.168.1.209 "docker stats docling-serve"
```

### GCS Processing Progress

```bash
# Check uploaded results
gsutil ls gs://image_detection_b/image-preprocessing-detector/extracted_text/
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
ssh byron@192.168.1.209 "docker logs docling-serve"

# Check resources
ssh byron@192.168.1.209 "free -h && df -h"
```

### Slow Processing

1. Check CPU usage: `docker stats docling-serve`
2. Increase workers if CPU underutilized
3. Decrease batch size if RAM constrained

### GCS Authentication Failed

```bash
# Test GCS access
ssh byron@192.168.1.209 \
  "GOOGLE_APPLICATION_CREDENTIALS=/data/docling/secrets/gcs-credentials.json \
   gsutil ls gs://image_detection_b/"
```

### VLM Model Download Slow

First startup downloads ~1GB GraniteDocling model. Wait for health check or:

```bash
# Pre-download model
ssh byron@192.168.1.209 "docker exec docling-serve python -c \
  \"from transformers import AutoModel; AutoModel.from_pretrained('ibm-granite/granite-docling-258M')\""
```

## Dataset Processing Estimates

| Dataset Category | Images | Standard | VLM |
|-----------------|--------|----------|-----|
| Tables (Tier 1) | 944,057 | 22 hrs | 26 hrs |
| Documents | 480,863 | 11 hrs | 13 hrs |
| Forms | 14,583 | 20 min | 24 min |
| **Total Tier 1** | **1,452,580** | **33 hrs** | **40 hrs** |

## Files

```text
deployment/
├── README.md                       # This file
├── deploy-docling.sh               # NFS deployment script
├── setup-gcs-processing.sh         # GCS deployment script
├── docker-compose.docling.yml      # Standard mode compose
├── docker-compose.docling-vlm.yml  # VLM mode compose
├── docker-compose.docling-gcs.yml  # GCS mode compose
└── scripts/
    ├── gcs_processor.py            # Python GCS processor
    └── process-dataset-gcs.sh      # Bash GCS processor
```
