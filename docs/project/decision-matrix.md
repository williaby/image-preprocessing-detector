---
schema_type: common
title: "Critical Decision Matrix"
tags:
  - planning
  - project_management
status: published
owner: core-maintainer
purpose: Project planning documentation for critical decision matrix.
---

**Purpose**: Prioritize and track key architectural and implementation decisions before starting development.

**Status**: ✅ **DECISIONS FINALIZED** - Phase 1 implementation approved (2025-01-15)

---

## ✅ FINALIZED DECISIONS (2025-01-15)

### Decision #1: Throughput Target - **APPROVED**
- **Target**: 1,000 pages/hour (0.28 pages/sec, ~3.6 sec/page)
- **Rationale**: Baseline from OCR project, achievable with modest hardware
- **Performance Budget**: < 500ms/page (Phase 1 classical CV), < 150ms/page (Phase 2-3 with ML)

### Decision #2: Hardware Configuration - **APPROVED**
- **GPU**: NVIDIA Quadro P2000 (5GB VRAM, Pascal architecture)
- **CPU**: 2× Intel Xeon E5-2690 (16 cores total, 8 cores each)
- **Environment**: Unraid server (shared GPU across processes)
- **Deployment Strategy**: CPU-first (Phase 1), GPU acceleration (Phase 2-3)

### Decision #3: v1 Detection Scope - **APPROVED**
- **Must-Have**: Tables, Text blocks, Images/Figures
- **Ideally (if feasible)**: Handwriting, Mathematical Formulas
- **Timeline**: Standard scope (14 weeks to v1)
- **Training Data**: Available via DocLayNet (11 layout classes including all target classes)

### Decision #4: Test Data - **APPROVED**
- **Source**: `/home/byron/dev/data_ingestor/data/benchmarks/`
- **Datasets**:
  - READoc: 500 PDFs with Markdown ground truth
  - DocLayNet: 1,000 images with layout annotations (11 classes)
  - PubTables-1M: 500 tables with structure annotations
- **Validation Strategy**: Use DocLayNet for layout detection validation

---

## Decision Priority Matrix

| # | Decision | Impact | Urgency | Dependencies | Status | Owner |
|---|----------|--------|---------|--------------|--------|-------|
| 1 | Throughput target (pages/hour) | CRITICAL | HIGH | Affects hardware sizing, architecture choices | ✅ **APPROVED** | Byron Williams |
| 2 | Hardware deployment (GPU/CPU mix) | CRITICAL | HIGH | Depends on #1 (throughput), affects cost | ✅ **APPROVED** | Byron Williams |
| 3 | v1 detection scope (element classes) | HIGH | HIGH | Affects training data needs, timeline | ✅ **APPROVED** | Byron Williams |
| 4 | PDF source distribution | HIGH | MEDIUM | Affects training data strategy | 🟡 PENDING | Data Team |
| 5 | Language/script coverage | MEDIUM | MEDIUM | Affects model complexity | 🟡 PENDING | Product Owner |
| 6 | Superscript/footnote timing | MEDIUM | LOW | Affects v1 scope, downstream coordination | 🟢 RECOMMENDED | Architecture Team |
| 7 | Downstream metadata format | MEDIUM | MEDIUM | Affects JSON schema design | 🟡 PENDING | Integration Team |
| 8 | Deployment environment | HIGH | LOW | Affects infrastructure planning | 🟡 PENDING | DevOps Lead |
| 9 | Precision vs Recall balance | MEDIUM | LOW | Affects threshold tuning | 🟢 RECOMMENDED | ML Team |
| 10 | Active learning budget | LOW | LOW | Affects annotation cost | 🟡 PENDING | Project Manager |

**Legend**:
- 🔴 **BLOCKED**: Critical blocker, must resolve immediately
- 🟡 **PENDING**: Needs stakeholder input
- 🟢 **RECOMMENDED**: Technical team has recommendation, needs approval

---

## Decision #1: Throughput Target (CRITICAL - BLOCKING)

### Question
What is the target throughput for the preprocessing pipeline?

### Options

| Option | Pages/Hour | Workers Needed | Monthly Cost | Use Case |
|--------|------------|----------------|--------------|----------|
| **Low** | < 10,000 | 2-4 CPU workers | $200-400 | Pilot, small datasets |
| **Medium** | 10,000 - 100,000 | 5-10 GPU (T4) | $1,200-2,500 | Production, moderate scale |
| **High** | 100,000 - 500,000 | 20-50 GPU (T4/A10) | $5,000-12,000 | Enterprise, high volume |
| **Very High** | > 500,000 | 50+ GPU + auto-scaling | $12,000+ | Large-scale RAG ingestion |

### Impact
- **Architecture**: Low throughput allows CPU-only, high requires GPU optimization
- **Cost**: 25-50x cost difference between low and high
- **Timeline**: High throughput requires more optimization work (add 2-3 weeks)

### Recommendation
Start with **Medium** (10k-100k pages/hour) for production launch:
- Balances cost and capability
- GPU acceleration for ML models
- Horizontal scaling path to high throughput
- Can downgrade to CPU for cost savings if throughput is lower

### Decision Needed By
**Week 1** - Blocks hardware provisioning and architecture finalization

### Stakeholders
- [ ] Product Owner (business requirements)
- [ ] Finance (budget approval)
- [ ] DevOps (infrastructure capacity)

---

## Decision #2: Hardware Deployment Mix (CRITICAL - BLOCKING)

### Question
What hardware configuration should we deploy?

### Options (Based on Medium Throughput Target)

| Configuration | Setup | Cost/Month | Performance | Pros/Cons |
|---------------|-------|------------|-------------|-----------|
| **A: GPU-Only** | 8× T4 workers | $2,040 | 12-15 pages/sec | ✅ Fast, consistent<br>❌ Higher cost |
| **B: Hybrid** | 4× T4 + 8× CPU | $1,900 | 10-12 pages/sec | ✅ Cost-effective<br>❌ Complex routing |
| **C: CPU-Only** | 20× CPU (8-core) | $2,200 | 6-8 pages/sec | ✅ Simple<br>❌ Slower, more workers |
| **D: Serverless** | Auto-scaling (GCP/AWS) | $1,500-3,000 | Variable | ✅ Elastic<br>❌ Cold starts |

### Dependencies
- Depends on Decision #1 (throughput target)
- Affects model optimization strategy (INT8 quantization priority)

### Recommendation
**Option A: GPU-Only (8× T4 workers)** for production launch:
- Consistent performance (no routing complexity)
- Simplest deployment and monitoring
- Clear scaling path (add more T4 workers)
- Cost-effective at medium scale
- Future optimization: Can switch to hybrid if cost becomes issue

**Alternative for Pilot**: Start with 2× T4 workers ($510/month) to validate, then scale

### Decision Needed By
**Week 1** - Blocks infrastructure provisioning

### Stakeholders
- [ ] DevOps Lead (infrastructure)
- [ ] Finance (budget approval)
- [ ] Architecture Team (technical validation)

---

## Decision #3: v1 Detection Scope (HIGH - NEEDS INPUT)

### Question
Which document element classes are must-have for v1 launch?

### Options

| Scope | Classes Included | Training Data Effort | Timeline | Accuracy Target |
|-------|------------------|---------------------|----------|-----------------|
| **Minimal** | Tables, Images | LOW (PubLayNet sufficient) | 12 weeks | mAP > 0.85 |
| **Standard** | + Handwriting | MEDIUM (+1k custom labels) | 14 weeks | mAP > 0.82 |
| **Full** | + Formulas | HIGH (+1.5k custom labels) | 16 weeks | mAP > 0.80 |
| **Extended** | + Footnotes (pre-OCR) | VERY HIGH (+3k labels) | 20 weeks | mAP > 0.75 |

### Impact
- **Timeline**: 4-8 week difference between minimal and extended
- **Annotation Cost**: $500 (minimal) to $3,000 (extended)
- **Accuracy**: More classes → lower per-class accuracy
- **Downstream**: May require workflow changes if classes missing

### Recommendation
**Standard scope** (Tables, Images, Handwriting):
- Covers 85% of common document types
- Handwriting detection is valuable for mixed documents
- Formula detection can be added in v1.1 (4-week sprint)
- Defer footnotes to post-OCR (see Decision #6)

**Rationale**:
- Balances coverage and timeline
- Public datasets cover most needs
- Custom labeling budget reasonable ($1,000-1,500)
- Clear path to v1.1 for additional classes

### Decision Needed By
**Week 2** - Affects data collection planning

### Stakeholders
- [ ] Product Owner (business requirements)
- [ ] Downstream Team (LayoutParser/OCR requirements)
- [ ] ML Team (training feasibility)

---

## Decision #4: PDF Source Distribution (HIGH - NEEDS DATA)

### Question
What is the expected distribution of PDF/image sources?

### Impact on Training Strategy

| Source Type | Training Data Strategy | Special Considerations |
|-------------|------------------------|------------------------|
| **Vector PDFs (born-digital)** | Clean rasterization, fewer quality issues | Focus on layout detection |
| **Scanned Documents (flatbed)** | More quality issues, controlled degradation | IQA training critical |
| **Scanned Documents (legacy)** | Halftone, fax artifacts, heavy degradation | Real-world augmentation essential |
| **Camera Captures (phone)** | Perspective, lighting, blur challenges | Perspective correction critical |

### Data Collection Needed
- [ ] Sample 500 representative documents from production sources
- [ ] Analyze distribution:
  - % vector PDFs
  - % high-quality scans (>200 DPI)
  - % legacy scans (<200 DPI, halftone, fax)
  - % camera captures
- [ ] Identify worst-case examples for test set

### Recommendation
**Assume mixed distribution** (conservative approach):
- 40% vector PDFs (clean, born-digital)
- 40% high-quality scans (modern scanners, 200-300 DPI)
- 15% legacy scans (older scanners, fax, halftone)
- 5% camera captures

**Training Data Implications**:
- Focus augmentation on legacy scan artifacts
- Include halftone, JPEG compression, uneven illumination
- Test perspective correction on camera capture subset
- Validate on real-world samples from each category

### Decision Needed By
**Week 2** - Affects augmentation strategy design

### Stakeholders
- [ ] Data Team (source analysis)
- [ ] ML Team (training strategy)

---

## Decision #5: Language/Script Coverage (MEDIUM - NEEDS INPUT)

### Question
What language/script coverage is required?

### Options

| Coverage | Scripts Supported | Detection Method | Complexity |
|----------|-------------------|------------------|------------|
| **Latin-only** | Latin alphabet | No script detection needed | LOW |
| **Latin + CJK** | Chinese, Japanese, Korean | Lightweight OCR + script ID | MEDIUM |
| **Multi-script** | Latin, CJK, Arabic, Cyrillic, etc. | Comprehensive script detection | HIGH |

### Impact
- **Latin-only**: Simplest, no pre-OCR script detection
- **Multi-script**: Requires lightweight OCR on text blocks (+5-10ms latency)
- **Training Data**: Multi-script requires diverse document sources

### Recommendation
**Start with Latin-only, plan for multi-script in v1.1**:
- Most enterprise documents are Latin-based
- Avoids latency of script detection in v1
- Can add script detection in 2-week sprint if needed
- Test on multi-script documents to ensure no breaking

**If multi-script required for v1**:
- Integrate Tesseract fast mode on detected text blocks
- Budget +5-10ms per page for script identification
- Include CJK/Arabic/Cyrillic documents in test set

### Decision Needed By
**Week 2** - Affects pipeline design and test set composition

### Stakeholders
- [ ] Product Owner (geographic coverage requirements)
- [ ] Downstream Team (OCR capabilities)

---

## Decision #6: Superscript/Footnote Detection (MEDIUM - RECOMMENDATION READY)

### Question
Should superscript and footnote detection be included in v1 preprocessing?

### Options

| Approach | Timing | Accuracy | Complexity | Latency |
|----------|--------|----------|------------|---------|
| **Pre-OCR (pixel-level)** | v1 | LOW (60-70%) | HIGH | +15-25ms |
| **Post-OCR (baseline analysis)** | v1.1 (or downstream) | HIGH (85-90%) | MEDIUM | +5ms |

### Recommendation
**Defer to post-OCR (v1.1 or downstream)**:

**Rationale**:
- OCR provides precise baseline and font size data
- Pre-OCR pixel analysis is unreliable (low accuracy)
- Adds complexity and latency to v1
- Downstream OCR tools (Tesseract, Marker) already extract this
- Can be added as lightweight post-processing step in v1.1

**Implementation Path**:
1. v1: Document in JSON that superscript/footnote detection is deferred
2. v1.1 (if needed): Add post-OCR analysis module (2-week sprint)
3. Alternative: Let downstream LayoutParser/OCR handle it

### Decision Needed By
**Week 3** - Not blocking, but affects v1 scope communication

### Stakeholders
- [ ] Product Owner (v1 requirements)
- [ ] Downstream Team (LayoutParser/OCR coordination)

### Status
✅ **Technical recommendation ready** - Awaiting stakeholder approval

---

## Decision #7: Downstream Metadata Format (MEDIUM - NEEDS VALIDATION)

### Question
Does the proposed JSON schema meet downstream requirements?

### Proposed Schema Highlights
- COCO-aligned bounding boxes (easy LayoutParser integration)
- Page-level diagnostics (detected issues, confidence scores)
- Transform history (reproducibility and debugging)
- Element attributes (category, confidence, custom attributes)

### Validation Needed
- [ ] Share JSON schema with LayoutParser team
- [ ] Confirm bounding box format (COCO vs YOLO vs custom)
- [ ] Validate coordinate system (pixel space, origin top-left)
- [ ] Confirm metadata fields needed (script, orientation, etc.)
- [ ] Test integration with sample JSONs

### Action Items
1. Schedule meeting with LayoutParser/OCR team (Week 2)
2. Share sample JSON outputs for validation
3. Iterate on schema based on feedback
4. Lock schema by Week 3 (before Phase 0 completion)

### Decision Needed By
**Week 3** - Affects JSON schema finalization

### Stakeholders
- [ ] LayoutParser Team
- [ ] Tesseract/Marker/Docling Team
- [ ] Architecture Team

---

## Decision #8: Deployment Environment (HIGH - NEEDS INPUT)

### Question
Where should the production service be deployed?

### Options

| Environment | Pros | Cons | Cost Model |
|-------------|------|------|------------|
| **Cloud (AWS/GCP/Azure)** | Auto-scaling, managed services, easy deployment | Higher variable cost, vendor lock-in | Pay-per-use |
| **On-Premise** | Fixed cost, full control, data privacy | Higher upfront cost, more management | CapEx |
| **Hybrid** | Flexibility, cost optimization | Complex networking, coordination | Mixed |

### Recommendation
**Start with Cloud (GCP or AWS)** for faster launch:
- Deploy on GCP (Cloud Run + GPU VMs) or AWS (ECS + EC2)
- Use managed Kubernetes (GKE or EKS) for orchestration
- Auto-scaling for variable workload
- Clear migration path to on-premise if cost becomes issue

**Migration to On-Premise**:
- Evaluate after 6 months of production usage
- Compare actual costs: Cloud vs on-premise TCO
- Move if processing volume justifies hardware investment

### Decision Needed By
**Week 1** - Affects infrastructure setup

### Stakeholders
- [ ] DevOps Lead (deployment strategy)
- [ ] Finance (cost model preference)
- [ ] Security (data privacy requirements)

---

## Decision #9: Precision vs Recall Balance (MEDIUM - RECOMMENDATION READY)

### Question
Should we optimize for precision (fewer false positives) or recall (fewer false negatives)?

### Trade-offs

| Priority | Confidence Thresholds | Impact |
|----------|----------------------|--------|
| **High Precision** | 0.85-0.90 | Fewer corrections, avoid over-correction harm |
| **Balanced** | 0.70-0.80 | Standard approach |
| **High Recall** | 0.60-0.70 | More corrections, risk over-correction |

### Recommendation
**Favor Precision (thresholds 0.85-0.90)**:

**Rationale**:
- Over-correction (false positive) harms OCR more than missed correction (false negative)
- Deskewing a straight page → introduces artifacts
- CLAHE on good contrast → reduces OCR accuracy
- Better to miss an issue than apply wrong correction

**Implementation**:
- Set default confidence threshold: 0.85
- Apply "do-no-harm" guardrails (measure improvement before/after)
- Tune per issue type during calibration (Phase 2)
- Monitor production: Adjust if false negative rate too high

### Decision Needed By
**Week 4** - Can be tuned during Phase 1, not blocking

### Stakeholders
- [ ] ML Team (threshold tuning)
- [ ] Downstream Team (OCR impact validation)

### Status
✅ **Technical recommendation ready** - Can finalize during Phase 1

---

## Decision #10: Active Learning Budget (LOW - NEEDS INPUT)

### Question
What annotation budget should we allocate for active learning iterations?

### Estimated Costs

| Annotation Volume | Cost | Timeline | Expected Improvement |
|-------------------|------|----------|----------------------|
| **Minimal** (500 pages) | $500 | 1-2 weeks | +2-3% mAP |
| **Standard** (1,500 pages) | $1,500 | 3-4 weeks | +4-6% mAP |
| **Comprehensive** (3,000 pages) | $3,000 | 5-6 weeks | +6-8% mAP |

### Recommendation
**Standard budget ($1,500 for 1,500 pages)**:
- 3-4 active learning iterations
- Focus on rare classes (handwriting, formulas)
- Mine high-uncertainty samples (maximize ROI)
- Balance cost and accuracy improvement

### Decision Needed By
**Week 4** - Affects Phase 3 planning, not blocking Phase 0-2

### Stakeholders
- [ ] Project Manager (budget approval)
- [ ] ML Team (active learning strategy)

---

## Decision Timeline

### Week 1 (CRITICAL)
- [ ] **Decision #1**: Throughput target → Determines hardware needs
- [ ] **Decision #2**: Hardware deployment → Blocks infrastructure provisioning
- [ ] **Decision #8**: Deployment environment → Affects setup

### Week 2 (HIGH PRIORITY)
- [ ] **Decision #3**: v1 detection scope → Affects data collection
- [ ] **Decision #4**: PDF source distribution → Affects training strategy
- [ ] **Decision #5**: Language/script coverage → Affects pipeline design
- [ ] **Decision #7**: Downstream metadata format → Schedule validation meeting

### Week 3 (MEDIUM PRIORITY)
- [ ] **Decision #6**: Superscript/footnote timing → Confirm with stakeholders
- [ ] **Decision #7**: Lock JSON schema → After downstream validation

### Week 4 (LOW PRIORITY)
- [ ] **Decision #9**: Precision vs Recall → Can tune during Phase 1
- [ ] **Decision #10**: Active learning budget → Phase 3 planning

---

## Next Steps

### Immediate Actions (Week 1)

1. **Schedule Stakeholder Meeting** (by Day 2)
   - Attendees: Product Owner, Finance, DevOps, ML Lead
   - Agenda: Decisions #1, #2, #8 (critical blockers)
   - Duration: 1 hour
   - Output: Finalized throughput target and hardware plan

2. **Request Data Samples** (by Day 3)
   - From: Data Team / Production
   - Request: 500 representative PDF/image samples
   - Purpose: Analyze source distribution (Decision #4)

3. **Schedule Integration Meeting** (by Day 5)
   - Attendees: LayoutParser Team, OCR Team, Architecture
   - Agenda: Validate JSON schema, discuss handoff format
   - Duration: 1 hour
   - Output: Confirmed metadata requirements

4. **Provision Development Environment** (by Week 1 end)
   - Set up GPU workstations or cloud instances
   - Install dependencies (Poetry, Docker, etc.)
   - Initialize repository and CI/CD

---

## Decision Log Template

**Use this template to record final decisions:**

```markdown
## Decision: [Title]
**Date**: YYYY-MM-DD
**Decision Owner**: [Name]
**Stakeholders**: [List]

### Context
[Why this decision was needed]

### Options Considered
1. [Option A]
2. [Option B]
3. [Option C]

### Decision
[Chosen option and rationale]

### Consequences
- Positive: [Expected benefits]
- Negative: [Trade-offs or risks]

### Action Items
- [ ] [Specific task 1]
- [ ] [Specific task 2]

### Review Date
[When to revisit this decision]
```

---

*For complete project details, see [PROJECT_PLAN.md](../planning/PROJECT_PLAN.md)*
*For architecture overview, see [ARCHITECTURE_SUMMARY.md](../architecture/ARCHITECTURE_SUMMARY.md)*
