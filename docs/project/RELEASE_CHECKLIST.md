---
schema_type: common
title: "Release Checklist"
description: "Pre-release validation checklist for deployments"
tags:
  - guide
  - deployment
  - releases
status: published
owner: core-maintainer
authors:
  - name: "Byron Williams"
purpose: "Document pre-release validation steps and requirements."
---

Pre-release validation checklist for Image Preprocessing Detector.

## Version Information

| Item | Value |
|------|-------|
| Version | 0.1.0 |
| Release Date | TBD |
| Release Type | Initial Release |

---

## Pre-Release Validation

### Code Quality

- [x] All tests pass: 1282 passed, 58 skipped, 3 xfailed
- [x] Coverage meets threshold: 90.15% (target: 80%)
- [x] No critical linting errors (Ruff)
- [x] Type checking passes (MyPy)
- [x] Security scan clean (Bandit)
- [x] Dependency vulnerabilities checked (Safety)

### Documentation

- [x] API documentation complete (REST API guide)
- [x] Deployment guide complete (local, Docker, Modal)
- [x] Model cards updated (teacher/student specs)
- [x] ADRs current (35-36 added)
- [x] Project B handoff guide complete
- [x] CHANGELOG updated

### Testing

- [x] Unit tests comprehensive (1000+ tests)
- [x] Integration tests pass
- [x] API endpoint tests pass (78 tests)
- [x] Performance benchmarks documented
- [x] Edge cases covered

### Infrastructure

- [x] Dockerfile validated
- [x] docker-compose.yaml validated
- [x] Modal integration documented

---

## Smoke Tests

### Local Development

```bash
# Install and run
poetry install --with dev --extras api
poetry run pytest -v --no-cov  # Should pass

# Start API
poetry run uvicorn image_preprocessing_detector.api.app:app --port 8000

# Verify endpoints
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/version
```

### Docker

```bash
# Build
docker build -t image-preprocessing-detector:test .

# Run
docker run -d -p 8000:8000 --name imgprep-test image-preprocessing-detector:test

# Verify
curl http://localhost:8000/health
curl -X POST http://localhost:8000/process -F "file=@test.pdf"

# Cleanup
docker stop imgprep-test && docker rm imgprep-test
```

### API Endpoints

| Endpoint | Method | Expected Status |
|----------|--------|-----------------|
| `/health` | GET | 200 |
| `/ready` | GET | 200 |
| `/version` | GET | 200 |
| `/docs` | GET | 200 |
| `/process` | POST (valid file) | 200 |
| `/process` | POST (invalid file) | 400 |
| `/batch` | POST (valid files) | 200 |

### Processing Validation

```bash
# Test with sample PDF
curl -X POST http://localhost:8000/process \
  -F "file=@samples/test_document.pdf" \
  -o result.json

# Verify response structure
jq '.result.document_id' result.json  # Should have document_id
jq '.result.dqs' result.json          # Should have DQS scores
jq '.result.ocr_routing_recommendation' result.json  # Should have routing
```

---

## Rollback Plan

### If Issues Found Post-Release

1. **Identify Severity**
   - Critical: Security, data loss, crashes
   - High: Major functionality broken
   - Medium: Minor functionality issues
   - Low: Cosmetic, documentation

2. **Rollback Steps**

   **Docker**:

   ```bash
   # Pull previous version
   docker pull image-preprocessing-detector:0.0.x

   # Restart with previous
   docker-compose down
   docker-compose up -d
   ```

   **Poetry/Local**:

   ```bash
   # Checkout previous tag
   git checkout v0.0.x
   poetry install
   ```

3. **Communication**
   - Notify stakeholders of rollback
   - Document issues found
   - Create bug tickets

---

## Post-Release Monitoring

### First 24 Hours

- [ ] Monitor error rates in logs
- [ ] Check processing latencies
- [ ] Verify no memory leaks
- [ ] Monitor API response times
- [ ] Check Modal usage (if enabled)

### First Week

- [ ] Review user feedback
- [ ] Analyze error patterns
- [ ] Check resource utilization
- [ ] Validate cost projections
- [ ] Update documentation if needed

### Metrics to Watch

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| API latency (p50) | <500ms | >1s |
| API latency (p99) | <2s | >5s |
| Error rate | <1% | >5% |
| Processing success | >95% | <90% |
| Memory usage | <2GB | >4GB |

---

## Sign-Off

| Role | Name | Date | Approved |
|------|------|------|----------|
| Developer | | | [ ] |
| Reviewer | | | [ ] |
| QA | | | [ ] |
| Release Manager | | | [ ] |

---

## Release Notes Template

```markdown
# Image Preprocessing Detector v0.1.0

## Highlights

- Initial release of preprocessing and IQA pipeline
- REST API for document processing
- Docker deployment support
- Teacher-student ML architecture for IQA

## Features

- Single document processing (POST /process)
- Batch processing with async status (POST /batch)
- Document Quality Score (DQS) calculation
- OCR routing recommendations
- Classical CV + ML hybrid IQA

## API Endpoints

- GET /health, /ready, /version
- POST /process (single file)
- POST /batch (multiple files)
- GET /batch/{job_id}/status
- GET /batch/{job_id}/result
- DELETE /batch/{job_id}

## Deployment Options

- Local development (Poetry + uvicorn)
- Docker Compose
- Modal (serverless GPU)

## Requirements

- Python 3.11+
- OpenCV 4.8+
- PyMuPDF 1.23+

## Known Issues

- Teacher model on CPU is blocked by default (high latency)
- Modal cold starts may add 5-15s latency

## Upgrading

First release - no upgrade path needed.
```
