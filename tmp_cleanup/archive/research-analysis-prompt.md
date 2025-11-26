<!-- markdownlint-disable MD013 -->
<!--
SPDX-FileCopyrightText: 2024 Byron Williams <byronawilliams@gmail.com>
SPDX-License-Identifier: MIT
-->

# Periodic Research Analysis Prompt

**Version**: 1.0
**Date**: 2025-11-13
**Purpose**: Standardized LLM prompt for discovering new research and best practices
**Review Schedule**: Quarterly (every 3 months)

---

## Overview

This document provides a standardized prompt for conducting periodic research analysis to keep the Image Preprocessing Detector aligned with the latest advances in document processing, OCR, image quality assessment, and RAG applications.

**Review Frequency**: Every 3 months (January, April, July, October)
**Last Review**: 2025-11-13 (Initial analysis using 72 papers from document_issues_research.txt)
**Next Review**: 2026-02-13

---

## Project Context Summary

Use this context when querying for new research:

### Project Overview

**Image Preprocessing Detector** is an intelligent document quality assessment and preprocessing system designed for RAG (Retrieval-Augmented Generation) applications. The system analyzes documents (PDFs, images) and identifies required preprocessing steps before vector database ingestion.

**Key Innovation**: Multi-stage pipeline with text detection gate that routes documents to specialized processing paths:

- **No-text path**: Classical CV + ML IQA (skew, blur, contrast, noise)
- **Text-detected path**: YOLOv8 layout detection + hybrid IQA on embedded images

**Technology Stack**:

- Classical Computer Vision: OpenCV (Hough transform, Laplacian, histogram analysis)
- Deep Learning: PyTorch, YOLOv8, MobileNetV3/EfficientNet
- Production: ONNX Runtime with INT8 quantization
- Deployment: CPU-first strategy with optional GPU acceleration

**Performance Targets**:

- Latency: < 150ms per page (GPU), < 400ms per page (CPU)
- Accuracy: mAP > 0.88 (IQA), mAP@.50 > 0.82 (layout detection)
- Throughput: > 6 pages/sec per GPU worker

### Current Phase

**Phase**: Phase 2 - ML-based Image Quality Assessment
**Timeline**: Weeks 8-11 (current)
**Focus**: Training multi-label CNN for IQA with 6 defect types (blur, noise, skew, perspective, low_contrast, orientation)

**Completed**:

- ✅ Phase 0: Foundation and scaffolding
- ✅ Phase 1: MVP with classical CV methods (blur, skew, contrast detection)
- ✅ Phase 1B: DPI detection and upscaling to 300 DPI

**Upcoming**:

- ⏳ Phase 3: YOLOv8 layout detection (DocLayNet 11 classes)
- ⏳ Phase 4: Production hardening and Document Quality Score (DQS)
- ⏳ Phase 5: Continuous improvement

### Current Capabilities

**Image Quality Detection** (IQA):

- Blur detection (Laplacian variance + ML)
- Skew detection (Hough transform + ML)
- Contrast assessment (histogram analysis + ML)
- Noise detection (connected components + ML)
- DPI upscaling (OpenCV algorithms)
- Perspective distortion (ML - Phase 2)

**Planned Capabilities** (from DETECTION_TAXONOMY.md):

- Binarization quality assessment (Phase 2)
- Illumination uniformity detection (Phase 2)
- Bleed-through detection (Phase 3)
- Warping/curvature detection (Phase 3)
- Watermark detection (Phase 3)
- Stamp/seal detection (Phase 3)
- Signature detection (Phase 3)

**Layout Analysis** (Phase 3):

- DocLayNet 11 classes (Text, Title, List, Table, Picture, Caption, Formula, Footnote, Page-Header, Page-Footer, Section-Header)
- Parasitic content detection (headers/footers)
- Footnote linking
- Figure-caption linking
- Vertical text orientation

**Specialized Content**:

- PDF type classification (image_only, born_digital, hybrid)
- Handwriting vs printed text (Phase 2)
- Language/script detection (235 languages via Wili-2018)
- Mathematical content (formulas, equations)

### Training Strategy

**Three-Tier Dataset Strategy** (ADR-029):

1. **Tier 1: Training** (50k synthetic samples from TableBank + Albumentations augmentation, weak supervision)
2. **Tier 2: Benchmarks** (LIVE, CSIQ, DocLayNet - evaluation only, never training)
3. **Tier 3: Test Fixtures** (< 50 MB, committed to git for CI/CD)

**Hybrid Validation** (ADR-011):

- Train on synthetic data (perfect labels)
- Calibrate on real-world data (production distribution)
- Critical discovery: Synthetic-only calibration caused 100% false positive rate on real documents

**Infrastructure** (ADR-030):

- Local dataset generation (development machine)
- Google Cloud Storage for datasets/models (~88 GB)
- Google Colab Pro for GPU training (T4/V100/A100)

### Key Architecture Decisions

**ADRs Referenced**:

- ADR-007: Hybrid IQA approach (per-element quality assessment)
- ADR-008: Multi-stage pipeline architecture (text detection fork)
- ADR-011: Hybrid validation strategy (synthetic + real-world calibration)
- ADR-029: Three-tier dataset strategy
- ADR-030: GCS/Colab training workflow
- ADR-031: Registry-based benchmarking framework

---

## Research Analysis Prompt

Use the following prompt with an LLM that has web search capabilities (e.g., Perplexity, ChatGPT with browsing, Claude with web search):

```text
You are a research analyst helping to identify the latest advances in document preprocessing,
OCR, image quality assessment, and RAG applications.

PROJECT CONTEXT:
I'm building an Image Preprocessing Detector for RAG applications that:
- Detects document quality issues (blur, skew, noise, contrast, warping, bleed-through)
- Performs layout analysis (DocLayNet 11 classes: text, tables, figures, formulas, etc.)
- Routes documents to optimal processing pipelines (OCR vs VLM based on quality/complexity)
- Uses hybrid approach: Classical CV (OpenCV) + Deep Learning (YOLOv8, MobileNetV3)
- Targets production deployment: < 150ms latency per page, > 0.88 mAP for IQA

CURRENT CAPABILITIES:
✅ Blur, skew, contrast, noise detection (classical + ML)
✅ DPI upscaling to 300 DPI (5 OpenCV algorithms)
✅ Text detection gate (ensemble heuristics)
✅ Hybrid validation (synthetic + real-world calibration)
⏳ Phase 2: Multi-label IQA CNN (6 defect types)
⏳ Phase 3: YOLOv8 layout detection (DocLayNet)

RESEARCH FOCUS AREAS:
1. Image Quality Assessment (IQA) for documents (not natural images)
2. Document layout analysis and object detection
3. Document preprocessing for OCR and RAG applications
4. Binarization, illumination normalization, dewarping techniques
5. Bleed-through detection and suppression
6. Watermark/stamp/seal detection
7. Handwriting vs printed text classification
8. Multi-lingual and mixed-script document processing
9. Document Quality Score (DQS) metrics for intelligent routing
10. Production optimization (model quantization, edge deployment)

SEARCH CRITERIA:
- Research papers published in the last 12-18 months (2024-2025)
- Focus on: CVPR, ICCV, ECCV, ICDAR, DAS, IJDAR, ACM DocEng conferences
- Arxiv preprints with >10 citations or from reputable institutions
- Industry research from Google, Microsoft, Adobe, Amazon (Textract, etc.)
- Open-source datasets with permissive licenses (Apache-2.0, MIT, CC-BY)

TASKS:
1. Search for recent papers on document IQA (not natural image IQA like BRISQUE/NIQE)
2. Find advances in document layout analysis (beyond LayoutLM/DocLayNet)
3. Identify new preprocessing techniques (binarization, dewarping, illumination)
4. Discover new datasets for document quality assessment or layout analysis
5. Find production deployment optimizations (quantization, distillation, edge inference)
6. Identify RAG-specific document preprocessing best practices
7. Look for new benchmark datasets or evaluation metrics

OUTPUT FORMAT:
For each relevant paper/resource found, provide:
- **Title**: Full paper title
- **Authors**: First author et al.
- **Venue**: Conference/journal and year (e.g., CVPR 2024, Arxiv 2025)
- **Summary**: 2-3 sentence summary of key contribution
- **Relevance**: How this could improve our system (specific FR or capability)
- **Dataset/Code**: Link to dataset, code, or model weights (if available)
- **Priority**: High/Medium/Low based on impact potential
- **Action Items**: Specific next steps (download dataset, implement technique, benchmark)

EXAMPLE OUTPUT:
**Title**: "DocUNet++: High-Resolution Document Unwarping with Adaptive Deformations"
**Authors**: Zhang et al.
**Venue**: CVPR 2024
**Summary**: Improves DocUNet dewarping by 15% mAP using adaptive mesh deformations and
multi-scale feature fusion. Handles severe warping (book spines) better than polynomial regression.
**Relevance**: FR-3.11 (Warping/Curvature Detection - Phase 3). Could replace polynomial
regression for book scan dewarping.
**Dataset/Code**: https://github.com/example/docunet-plus-plus, Pre-trained weights available
**Priority**: High (Phase 3 critical path)
**Action Items**:
  1. Download pre-trained model and benchmark on book scan test set
  2. Compare vs polynomial regression baseline (accuracy + latency)
  3. Integrate if latency < 200ms per page on T4 GPU

Please conduct this research analysis and provide findings.
```text

---

## Research Focus Areas (Detailed)

### 1. Image Quality Assessment (Document-Specific)

**Current Gap**: Most IQA research focuses on natural images (BRISQUE, NIQE, KonCept512). Document-specific IQA is under-researched.

**Search Keywords**:

- "document image quality assessment"
- "document binarization quality metrics"
- "OCR preprocessing quality"
- "document degradation detection"
- "scanned document quality"

**Target Metrics**:

- Multi-label classification (6+ defect types)
- Real-time inference (< 50ms per page on CPU)
- Calibration quality (ECE < 0.1)

**Example Questions**:

- Are there new document-specific IQA datasets beyond LIVE/CSIQ?
- Has anyone solved the synthetic-to-real distribution shift problem we encountered (ADR-011)?
- Are there better weak supervision techniques than classical detectors (BRISQUE, Laplacian)?

### 2. Document Layout Analysis

**Current Approach**: YOLOv8 on DocLayNet (11 classes), mAP@.50 > 0.82 target

**Search Keywords**:

- "document layout analysis 2024"
- "LayoutLMv3 improvements"
- "table detection transformer"
- "document object detection"
- "reading order prediction"

**Target Improvements**:

- Faster inference (< 100ms per page on T4 GPU)
- Better small object detection (formulas, footnotes)
- Reading order prediction (multi-column documents)

**Example Questions**:

- Are there LayoutLMv4 or newer multimodal document models?
- Has anyone published better table structure recognition than TableFormer?
- Are there new datasets beyond DocLayNet for layout analysis?

### 3. Document Preprocessing Techniques

**Current Gap**: Missing binarization, illumination normalization, dewarping, bleed-through suppression

**Search Keywords**:

- "adaptive document binarization 2024"
- "illumination normalization scanned documents"
- "document dewarping deep learning"
- "bleed-through removal"
- "document rectification perspective"

**Target Capabilities**:

- Binarization: Otsu/Sauvola/Niblack (Phase 2)
- Illumination: Adaptive histogram equalization (Phase 2)
- Dewarping: DocUNet or polynomial regression (Phase 3)
- Bleed-through: Frequency domain filtering (Phase 3)

**Example Questions**:

- Are there better binarization methods than Sauvola for degraded documents?
- Has anyone solved uneven illumination on mobile captures?
- Are there real-time dewarping methods (< 200ms per page)?

### 4. RAG-Specific Preprocessing

**Current Gap**: Most research focuses on OCR accuracy, not RAG retrieval quality

**Search Keywords**:

- "RAG document preprocessing"
- "OCR hinders RAG" (2024 paper identified this)
- "document chunking strategies"
- "parasitic content removal"
- "footnote linking RAG"

**Target Insights**:

- Which preprocessing steps most impact RAG retrieval quality?
- How to handle headers/footers (parasitic content)?
- How to preserve table structure in vector embeddings?

**Example Questions**:

- Are there new RAG benchmarks that measure preprocessing impact?
- Has anyone quantified the value of footnote linking for RAG accuracy?
- Are there better chunking strategies than fixed-size windows?

### 5. Production Optimization

**Current Approach**: ONNX Runtime, INT8 quantization, CPU-first deployment

**Search Keywords**:

- "document model quantization"
- "edge document processing"
- "mobile OCR optimization"
- "ONNX runtime optimization"
- "TensorRT document models"

**Target Metrics**:

- < 2 GB memory per worker
- < 150ms latency per page (GPU)
- < 400ms latency per page (CPU)

**Example Questions**:

- Are there better quantization methods than INT8 (e.g., INT4, mixed precision)?
- Has anyone deployed YOLOv8 on edge devices for documents?
- Are there model distillation techniques for document models?

### 6. New Datasets and Benchmarks

**Current Datasets**: TableBank, DocLayNet, LIVE, CSIQ, Wili-2018, SignaTR6K, OmniDocBench

**Search Keywords**:

- "document dataset 2024"
- "OCR benchmark dataset"
- "document quality assessment dataset"
- "permissive license document dataset"
- "multilingual document corpus"

**Target Characteristics**:

- Permissive license (Apache-2.0, MIT, CC-BY)
- > 10k samples for training
- Ground-truth annotations (COCO format for layout)
- Diverse document types (academic, business, historical, mobile)

**Example Questions**:

- Are there new document quality datasets with ground-truth defect labels?
- Has anyone released a book scan dataset for dewarping?
- Are there new multi-lingual document datasets beyond Wili-2018?

### 7. Specialized Content Detection

**Current Gap**: Limited research on watermarks, stamps, seals, signatures in documents

**Search Keywords**:

- "watermark detection documents"
- "seal stamp recognition"
- "signature detection verification"
- "margin annotation detection"
- "document forensics"

**Target Capabilities**:

- Watermark detection (P1 - Phase 3)
- Stamp/seal detection (P2 - Phase 3)
- Signature detection (P2 - Phase 3)
- Margin annotations (P2 - Phase 3)

**Example Questions**:

- Are there new methods for watermark detection beyond frequency domain?
- Has anyone published a stamp/seal detection dataset?
- Are there signature verification models we can adapt for detection?

### 8. Document Quality Score (DQS) Metrics

**Current Approach**: Two-axis DQS (degradation score + structural complexity score)

**Search Keywords**:

- "document quality metric"
- "document complexity score"
- "OCR confidence prediction"
- "document routing intelligent"
- "VLM vs OCR routing"

**Target Insights**:

- How to predict OCR success before running OCR?
- How to quantify document complexity for routing decisions?
- Are there industry standards for document quality metrics?

**Example Questions**:

- Has anyone published DQS-like metrics for document routing?
- Are there OCR confidence predictors that don't require running OCR?
- How do VLM providers (GPT-4o Vision) handle document quality internally?

---

## Research Analysis Template

Use this template to capture findings from each quarterly review:

```markdown
# Research Analysis - [Quarter] [Year]

**Date**: [YYYY-MM-DD]
**Analyst**: [Name]
**Review Period**: Last [12-18] months
**Total Papers Reviewed**: [Number]
**High Priority Findings**: [Number]

---

## Summary of Key Findings

[2-3 paragraph executive summary of most impactful discoveries]

---

## High Priority Papers

### [Paper Title]

**Authors**: [First Author et al.]
**Venue**: [Conference/Journal Year]
**Citations**: [Number] (as of review date)
**Link**: [URL to paper/arxiv]

**Summary**:
[2-3 sentences describing key contribution]

**Relevance to Project**:
[Which FR, capability, or phase this impacts]

**Key Insights**:
- [Insight 1]
- [Insight 2]
- [Insight 3]

**Dataset/Code**:
- Dataset: [Link if available, license type]
- Code: [GitHub link if available]
- Pre-trained Models: [Link if available]

**Action Items**:
- [ ] [Specific action 1 - assign to Phase/Week]
- [ ] [Specific action 2]
- [ ] [Specific action 3]

**Priority**: High / Medium / Low
**Effort Estimate**: [Hours]
**Target Phase**: [Phase 2/3/4/5]

---

## Medium Priority Papers

[Same structure as High Priority, but briefer summaries]

---

## New Datasets Discovered

### [Dataset Name]

**Size**: [GB / Number of samples]
**License**: [Apache-2.0 / MIT / CC-BY / Academic]
**Domain**: [Academic / Business / Historical / Mobile / etc.]
**Annotations**: [COCO layout / Quality labels / etc.]
**Link**: [URL]

**Training Use**: Yes / No / Validation Only
**Benchmark Use**: Yes / No

**Relevance**:
[Which FR or capability this supports]

**Action Items**:
- [ ] Download and validate (Week X)
- [ ] Integrate into benchmarks registry
- [ ] Add to DOCUMENT_TYPE_COVERAGE_MATRIX

---

## Industry Trends Observed

[Bullet list of trends noticed across multiple papers]

**Example**:
- Vision Transformers (ViT) replacing CNNs for document layout (5 papers)
- Multimodal models (text + vision) outperforming vision-only (8 papers)
- Edge deployment focus increasing (quantization, distillation - 12 papers)

---

## Gaps Identified in Current Approach

[Areas where research shows our approach may be suboptimal]

**Example**:
- Our weak supervision approach (classical detectors) may be outdated vs. self-supervised learning
- DocLayNet may be insufficient for table structure (need TableBank integration)
- Missing recent advances in binarization (new Sauvola variants published)

---

## Recommended Updates to Project

### Functional Requirements Updates

- [ ] Add FR-X.X: [New requirement based on research]
- [ ] Update FR-Y.Y: [Refinement based on new techniques]

### Detection Taxonomy Updates

- [ ] Add new issue: [Issue type - Priority]
- [ ] Reclassify: [Move from P2 to P1 based on research impact]

### Dataset Strategy Updates

- [ ] Add dataset: [Name - for training/benchmark]
- [ ] Deprecate dataset: [Name - if better alternative found]

### Architecture Updates

- [ ] Consider: [New architecture approach - e.g., ViT instead of CNN]
- [ ] Benchmark: [New technique vs current approach]

---

## Next Review Date

**Scheduled**: [3 months from current review]
**Focus Areas**: [Specific areas to prioritize in next review]

---

## Appendix: Full Paper List

[Complete list of all papers reviewed, organized by category]

### Image Quality Assessment
1. [Paper title] - [Authors] - [Venue Year] - [Link]
2. ...

### Layout Analysis
1. [Paper title] - [Authors] - [Venue Year] - [Link]
2. ...

### Preprocessing Techniques
1. [Paper title] - [Authors] - [Venue Year] - [Link]
2. ...

[etc.]
```text

---

## Review Process

### Quarterly Review Workflow

**Week 1: Research Collection**

1. Run standardized prompt with LLM (Perplexity, ChatGPT with browsing)
2. Search key conferences: CVPR, ICCV, ECCV, ICDAR, DAS, ACM DocEng
3. Search Arxiv for preprints (>10 citations or reputable institutions)
4. Search industry blogs: Google Research, Microsoft Research, Adobe Research
5. Compile list of 30-50 candidate papers

**Week 2: Paper Review and Prioritization**

1. Skim abstracts and filter to 15-20 high-relevance papers
2. Deep read high-priority papers (introduction, method, results)
3. Categorize by research focus area (IQA, layout, preprocessing, etc.)
4. Prioritize by impact potential (High/Medium/Low)
5. Extract key insights and action items

**Week 3: Integration Planning**

1. Map findings to functional requirements (FR updates needed?)
2. Identify new datasets to download and integrate
3. Estimate effort for integrating new techniques
4. Update DETECTION_TAXONOMY.md if new issues discovered
5. Update DOCUMENT_TYPE_COVERAGE_MATRIX if new document types needed
6. Create ADR if new architecture decision warranted

**Week 4: Documentation and Handoff**

1. Complete research analysis template
2. Update project documentation (FR, taxonomy, coverage matrix)
3. Create GitHub issues for action items
4. Schedule implementation in upcoming phases
5. Set next review date (3 months)

---

## Research Sources

### Academic Conferences (Primary Sources)

**Computer Vision**:

- CVPR (Computer Vision and Pattern Recognition) - June
- ICCV (International Conference on Computer Vision) - October
- ECCV (European Conference on Computer Vision) - October

**Document Analysis**:

- ICDAR (International Conference on Document Analysis and Recognition) - September
- DAS (Document Analysis Systems) - Biennial
- IJDAR (International Journal on Document Analysis and Recognition) - Quarterly

**Machine Learning**:

- NeurIPS (Neural Information Processing Systems) - December
- ICML (International Conference on Machine Learning) - July
- ICLR (International Conference on Learning Representations) - May

**Document Engineering**:

- ACM DocEng (Document Engineering) - September
- JCDL (Joint Conference on Digital Libraries) - September

### Preprint Archives

**Arxiv Categories**:

- cs.CV (Computer Vision and Pattern Recognition)
- cs.LG (Machine Learning)
- cs.CL (Computation and Language) - for RAG research
- cs.IR (Information Retrieval) - for document retrieval

### Industry Research Blogs

**Company Research**:

- Google Research Blog: <https://research.google/blog/>
- Microsoft Research Blog: <https://www.microsoft.com/en-us/research/blog/>
- Adobe Research: <https://research.adobe.com/>
- Meta AI Research: <https://ai.meta.com/research/>
- Amazon Science (Textract team): <https://www.amazon.science/>

### Open Datasets

**Dataset Aggregators**:

- Papers with Code: <https://paperswithcode.com/datasets> (filter by "document")
- Hugging Face Datasets: <https://huggingface.co/datasets> (search "document", "OCR")
- Google Dataset Search: <https://datasetsearch.research.google.com/>

**Document-Specific Repositories**:

- DocLayNet: <https://github.com/DS4SD/DocLayNet>
- TableBank: <https://github.com/doc-analysis/TableBank>
- FUNSD: <https://guillaumejaume.github.io/FUNSD/>
- RVL-CDIP: <https://adamharley.com/rvl-cdip/>

---

## Version History

| Version | Date | Changes | Reviewer |
|---------|------|---------|----------|
| 1.0 | 2025-11-13 | Initial creation | Byron Williams |

---

## Related Documentation

- [DETECTION_TAXONOMY.md](DETECTION_TAXONOMY.md): Complete taxonomy of detection capabilities
- [DOCUMENT_TYPE_COVERAGE_MATRIX.md](DOCUMENT_TYPE_COVERAGE_MATRIX.md): Document type testing coverage
- [functional_requirements_v2.md](requirements/functional_requirements_v2.md): Functional requirements
- [PUBLIC_DATASET_COVERAGE.md](PUBLIC_DATASET_COVERAGE.md): Current dataset coverage analysis
- [ADR-029](ADRs/0029-phase2-dataset-selection-strategy.md): Three-tier dataset strategy
- [ADR-031](ADRs/0031-comprehensive-benchmarking-framework.md): Benchmarking framework

---

**Next Review**: 2026-02-13 (3 months from creation)
**Review Trigger**: Can be run earlier if major conference proceedings published (e.g., CVPR 2026)
