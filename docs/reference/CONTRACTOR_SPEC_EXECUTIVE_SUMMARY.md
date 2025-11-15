# Executive Summary: Legal Document Annotation RFP
## Oregon Statutes & IRS Forms Layout Analysis Dataset

**Version:** 1.0
**Date:** 2025-11-14
**Full Specification:** [CONTRACTOR_SPEC_DATASET_ANNOTATION.md](CONTRACTOR_SPEC_DATASET_ANNOTATION.md)

---

## Project Overview

We are commissioning a professionally annotated dataset of **Oregon Statutes and IRS documents** for training machine learning models in document layout analysis. This dataset will power an intelligent preprocessing system for legal/regulatory RAG applications.

**Objective:** Create 4,000-10,000 pages of high-quality COCO-format layout annotations to train YOLOv8 and other document understanding models.

---

## Scope of Work

### Dataset Requirements

| Component | Target | Details |
|-----------|--------|---------|
| **Oregon Statutes** | 2,000-5,000 pages | 10-15 ORS chapters from oregonlegislature.gov |
| **IRS Documents** | 2,000-5,000 pages | 15+ forms/publications (1040, 1065, W-2, etc.) |
| **Total Pages** | 4,000-10,000 | Negotiable based on budget |
| **Format** | COCO JSON | Bounding boxes `[x, y, width, height]` |
| **Resolution** | 300 DPI PNG | Converted from official PDFs |

### Annotation Classes (11 Required)

Documents must be annotated with these layout elements:

1. **Caption** - Table/figure captions
2. **Footnote** - Citations, definitional notes
3. **Formula** - Tax calculations, equations
4. **List-item** - Statutory subsections, enumerated lists
5. **Page-footer** - Page numbers, document IDs
6. **Page-header** - Chapter titles, running heads
7. **Picture** - Diagrams, charts, signature blocks
8. **Section-header** - Section/subsection titles
9. **Table** - Structured tabular data
10. **Text** - Body paragraphs
11. **Title** - Document/chapter titles

---

## Quality Requirements

### Inter-Annotator Agreement (IAA)
- **Minimum 10% dual annotation** for consistency measurement
- **IoU threshold:** ≥ 0.85 for matching bounding boxes
- **Class agreement:** ≥ 95% label accuracy

### Validation Process
- **100-page pilot set** delivered for client approval before full production
- **Automated validation:** COCO schema, bbox coordinates, polygon validity
- **Quality metrics:**
  - Bounding box accuracy: ≤ 5px margin error
  - Class label accuracy: ≥ 98%
  - Missing annotations: < 1%

---

## Deliverables

### 1. Annotated Dataset
```
dataset/
├── images/                      # PNG images (300 DPI)
│   ├── oregon_statutes/
│   └── irs_documents/
├── annotations/                 # COCO JSON files
│   ├── oregon_statutes_train.json    (70%)
│   ├── oregon_statutes_val.json      (15%)
│   ├── oregon_statutes_test.json     (15%)
│   ├── irs_documents_train.json
│   ├── irs_documents_val.json
│   └── irs_documents_test.json
├── source_pdfs/                # Original PDFs with metadata
└── metadata/                   # Statistics, IAA reports
```

### 2. Documentation
- **Dataset statistics** (class distribution, page counts, document manifest)
- **IAA report** (IoU histograms, confusion matrices, edge cases)
- **Annotation guidelines** (final version with all decisions documented)
- **Source manifest** (URLs, download dates, checksums)

### 3. Data Split
- **Train:** 70% (document-level split, stratified by class)
- **Validation:** 15%
- **Test:** 15%

---

## Timeline & Budget

### Proposed Schedule (12 Weeks)

| Weeks | Phase | Milestone |
|-------|-------|-----------|
| 1-2 | **Kickoff & PDF Collection** | All source PDFs downloaded, converted to PNG |
| 3-4 | **Pilot Annotation** | 100-page pilot delivered for approval |
| 5 | **Pilot Review** | Client feedback, guideline refinement |
| 6-10 | **Full Production** | Remaining 7,000-9,000 pages annotated |
| 11 | **QA & Validation** | IAA measurement, error correction |
| 12 | **Final Delivery** | Complete dataset with documentation |

### Payment Structure (Milestone-Based)

| Milestone | Payment | Deliverable |
|-----------|---------|-------------|
| Kickoff | 10% | Signed contract, project plan |
| Pilot Approval | 20% | Client-approved 100-page pilot |
| 50% Complete | 30% | ~4,000 pages with IAA report |
| 100% Complete | 30% | All annotations, QA passed |
| Final Delivery | 10% | Complete dataset + documentation |

### Estimated Pricing

Based on industry standards for complex document layout annotation:

| Tier | Pages | Cost/Page | Total Budget |
|------|-------|-----------|--------------|
| **Minimum Viable** | 4,000 | $2-4 | **$8,000-16,000** |
| **Recommended** | 6,000 | $3-5 | **$18,000-30,000** |
| **Comprehensive** | 10,000 | $4-6 | **$40,000-60,000** |

**Pricing factors:**
- Legal document complexity: +20-30%
- COCO format requirements: +10-15%
- Dual annotation (IAA): +10-15%
- Rush delivery: +20-40%

---

## Contractor Qualifications

### Required Experience
✅ **COCO format annotation** (provide portfolio examples)
✅ **Document layout annotation** (tables, headers, text blocks)
✅ **IAA > 0.85** (proven quality assurance processes)
✅ **Team capacity** for 4,000-10,000 pages in 8-12 weeks

### Preferred Experience
⭐ YOLOv8 or Faster R-CNN annotation workflows
⭐ Legal/tax document domain expertise
⭐ U.S.-based annotators (for legal comprehension)
⭐ Experience with DocLayNet, PubLayNet, or similar datasets

---

## Recommended Vendors

### Tier 1: Premium Quality (High Cost)
1. **Scale AI** ([scale.com](https://scale.com)) - Industry leader, ML-optimized workflows
2. **Labelbox** ([labelbox.com](https://labelbox.com)) - Enterprise QA, managed services

### Tier 2: Balanced Quality/Cost
3. **CloudFactory** ([cloudfactory.com](https://cloudfactory.com)) - Strong legal doc experience
4. **iMerit** ([imerit.net](https://imerit.net)) - Cost-effective, large annotator pool

### Tier 3: Self-Service Platforms
5. **Amazon SageMaker Ground Truth** - AWS-integrated, pay-per-use
6. **Appen** ([appen.com](https://appen.com)) - Hybrid managed/DIY options

---

## Proposal Requirements

Contractors must submit:

### 1. Technical Approach
- Annotation platform/tools (CVAT, LabelStudio, etc.)
- Annotator training plan
- QA methodology and IAA process

### 2. Pricing
- **Per-page pricing** (itemized by complexity)
- **Volume discounts** (2K/5K/10K tiers)
- **Pilot pricing** (if separate from main project)

### 3. Timeline
- Detailed schedule with milestones
- Team size and capacity
- Dependencies and risk factors

### 4. Sample Work
- **3-5 example pages** from previous layout annotation projects
- **COCO JSON samples** demonstrating quality

### 5. References
- Minimum 2 client references for similar work
- Links to public datasets annotated (if available)

---

## Evaluation Criteria

| Criterion | Weight | Focus Areas |
|-----------|--------|-------------|
| **Technical Quality** | 35% | Methodology, QA rigor, IAA approach |
| **Experience** | 25% | Portfolio, team expertise, references |
| **Pricing** | 20% | Cost competitiveness, payment terms |
| **Timeline** | 10% | Realistic schedule, track record |
| **Communication** | 10% | Proposal clarity, responsiveness |

---

## Alternative Approaches

### Option A: DIY Annotation
**Pros:** Lower cost ($8,000-12,000 for 4,000 pages), full control
**Cons:** Time-intensive, requires hiring/managing annotators
**Best for:** Budget <$15,000 or existing annotation team

### Option B: Smaller Pilot Dataset
**Pros:** Validate model viability before large investment
**Cons:** May limit model performance, requires expansion later
**Best for:** Proof-of-concept phase, transfer learning from DocLayNet

### Option C: Hybrid Real + Synthetic
**Pros:** Cost reduction via synthetic augmentation
**Cons:** Synthetic data quality varies, domain shift risk
**Best for:** Augmenting real-world annotations (80-90% real + 10-20% synthetic)

---

## Next Steps

### Week 1: Prepare RFP
- [ ] Customize contractor spec with budget, timeline, contact info
- [ ] Finalize document list (Oregon ORS chapters, IRS forms)
- [ ] Identify 3-5 vendors to approach

### Week 2-3: RFP Distribution
- [ ] Send RFP to selected vendors
- [ ] Host vendor Q&A session (optional)
- [ ] Collect proposals

### Week 4-5: Evaluation
- [ ] Score proposals using evaluation criteria
- [ ] Request sample annotations from top 2-3 vendors (5 pages each)
- [ ] Conduct vendor interviews

### Week 6: Award
- [ ] Negotiate final pricing and terms
- [ ] Award contract with pilot clause
- [ ] Kickoff meeting and guideline review

---

## Success Metrics

### Dataset Quality
✅ **IAA ≥ 0.85** across all annotation classes
✅ **Class balance** within target ranges (Appendix D of full spec)
✅ **Zero missing elements** in manual spot-check (n=100 pages)

### Model Performance (Post-Training)
🎯 **Layout Detection mAP@.50 > 0.82** (YOLOv8 on test set)
🎯 **Table Detection mAP@.50 > 0.85** (specialized table model)
🎯 **Inference Speed < 150ms/page** (GPU inference)

### Project Delivery
✅ **On-time delivery** within 12-week window
✅ **On-budget** within ±10% of contracted price
✅ **Complete documentation** (statistics, IAA reports, guidelines)

---

## Contact & Resources

**Full Specification:** 44 pages, [CONTRACTOR_SPEC_DATASET_ANNOTATION.md](CONTRACTOR_SPEC_DATASET_ANNOTATION.md)

**Key Resources:**
- DocLayNet dataset: [github.com/DS4SD/DocLayNet](https://github.com/DS4SD/DocLayNet)
- COCO format spec: [cocodataset.org](https://cocodataset.org)
- Oregon Statutes: [oregonlegislature.gov](https://www.oregonlegislature.gov/bills_laws/Pages/ORS.aspx)
- IRS Forms: [irs.gov/forms-pubs](https://www.irs.gov/forms-pubs)

**Project Contact:**
[Your Name]
[Your Email]
[Your Organization]

---

**Prepared by:** Claude Code
**Document ID:** EXEC-SUMMARY-ANNOTATION-RFP-v1.0
**Last Updated:** 2025-11-14
