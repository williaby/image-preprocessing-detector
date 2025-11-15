# Dataset Annotation Contractor Specification
## Legal & Regulatory Document Layout Analysis Dataset

**Document Version:** 1.0
**Date:** 2025-11-14
**Project:** Image Preprocessing Detector - Training Dataset Creation
**Contact:** [Your Contact Information]

---

## 1. Executive Summary

We are seeking a qualified data annotation contractor to create high-quality, manually annotated datasets of Oregon Statutes and IRS documents for training machine learning models in document layout analysis, table detection, and image quality assessment.

**Dataset Target:**
- **Oregon Statutes Dataset:** 2,000-5,000 annotated pages
- **IRS Documents Dataset:** 2,000-5,000 annotated pages
- **Total Scope:** 4,000-10,000 annotated pages (negotiable based on budget)

**Timeline:** 8-12 weeks (negotiable)

**Budget:** [To be determined based on proposals]

---

## 2. Project Background

### 2.1 Use Case
We are building an intelligent document preprocessing system for RAG (Retrieval-Augmented Generation) applications that analyzes legal and regulatory documents to identify required preprocessing steps before vector database ingestion. The system needs to:

1. **Detect document layout elements** (tables, images, text blocks, formulas, captions, etc.)
2. **Identify quality issues** in embedded images (blur, skew, poor contrast, noise)
3. **Route documents** to specialized processing pipelines based on detected elements
4. **Extract structured metadata** for downstream NLP and search applications

### 2.2 Why These Document Types
- **Oregon Statutes:** Representative of state-level legal documents with complex statutory structure, hierarchical sections, definitions, cross-references, and table-based content
- **IRS Documents:** Representative of federal regulatory documents with highly structured forms, complex tables, mathematical formulas, fine-print footnotes, and standardized layouts

Both document types are critical for legal/regulatory RAG applications and represent real-world complexity our models must handle.

---

## 3. Technical Specifications

### 3.1 Annotation Format

**Required Format:** COCO (Common Objects in Context) JSON format

**Bounding Box Convention:** `[x, y, width, height]` where:
- `x`: Left edge coordinate (pixels)
- `y`: Top edge coordinate (pixels)
- `width`: Bounding box width (pixels)
- `height`: Bounding box height (pixels)

**Coordinate System:** Top-left origin (0,0 at top-left corner)

**Example COCO Annotation Structure:**
```json
{
  "images": [
    {
      "id": 1,
      "file_name": "ORS_166_250_page_001.png",
      "width": 2550,
      "height": 3300,
      "doc_category": "oregon_statutes",
      "source_document": "ORS_166.pdf",
      "page_number": 1,
      "dpi": 300
    }
  ],
  "annotations": [
    {
      "id": 1,
      "image_id": 1,
      "category_id": 9,
      "bbox": [150, 200, 2250, 150],
      "area": 337500,
      "segmentation": [[150, 200, 2400, 200, 2400, 350, 150, 350]],
      "iscrowd": 0
    }
  ],
  "categories": [
    {"id": 1, "name": "Caption", "supercategory": "layout"},
    {"id": 2, "name": "Footnote", "supercategory": "layout"},
    {"id": 3, "name": "Formula", "supercategory": "layout"},
    {"id": 4, "name": "List-item", "supercategory": "layout"},
    {"id": 5, "name": "Page-footer", "supercategory": "layout"},
    {"id": 6, "name": "Page-header", "supercategory": "layout"},
    {"id": 7, "name": "Picture", "supercategory": "layout"},
    {"id": 8, "name": "Section-header", "supercategory": "layout"},
    {"id": 9, "name": "Table", "supercategory": "layout"},
    {"id": 10, "name": "Text", "supercategory": "layout"},
    {"id": 11, "name": "Title", "supercategory": "layout"}
  ]
}
```

### 3.2 Annotation Classes (11 Required)

| Class ID | Class Name | Definition | Examples in Legal Documents |
|----------|------------|------------|----------------------------|
| 1 | **Caption** | Descriptive text for figures, tables, or images | "Table 1: Tax Brackets", "Figure A: Workflow Diagram" |
| 2 | **Footnote** | Reference notes at bottom of page or end of section | Statutory citations, definitional notes, effective dates |
| 3 | **Formula** | Mathematical expressions or equations | Tax calculations, penalty formulas, interest rate equations |
| 4 | **List-item** | Enumerated or bulleted list entries | Statutory subsections (a), (b), (c); numbered requirements |
| 5 | **Page-footer** | Repeated footer content | Page numbers, document identifiers, revision dates |
| 6 | **Page-header** | Repeated header content | Chapter titles, section numbers, "Oregon Revised Statutes" |
| 7 | **Picture** | Images, diagrams, charts, photos | Organizational charts, process diagrams, signature blocks |
| 8 | **Section-header** | Section/subsection titles and identifiers | "ORS 166.250 Unlawful use of weapon", "Section 1031 Like-Kind Exchanges" |
| 9 | **Table** | Structured tabular data with rows/columns | Fee schedules, tax rate tables, comparison matrices |
| 10 | **Text** | Body text paragraphs (not headers/footers/lists) | Statutory text, regulatory prose, explanatory paragraphs |
| 11 | **Title** | Document or chapter title | "OREGON REVISED STATUTES", "Form 1040 U.S. Individual Income Tax Return" |

### 3.3 Annotation Guidelines

#### 3.3.1 Bounding Box Accuracy
- **Minimum Requirement:** Bounding boxes must tightly enclose all visible pixels of the target element
- **Acceptable Margin:** ≤ 5 pixels padding on any side
- **Overlap Handling:** When elements overlap (e.g., table contains text):
  - Annotate the **highest-level container** first (e.g., Table)
  - Annotate **nested elements separately** if they have distinct semantic meaning
  - Use `precedence` field to indicate annotation order (lower number = higher priority)

#### 3.3.2 Segmentation Polygons
- **Required:** Yes, for all annotations
- **Minimum Polygon Points:** 4 (rectangular bounding box as polygon)
- **Preferred:** Tight polygon tracing actual element boundaries for non-rectangular shapes
- **Format:** `[[x1, y1, x2, y2, x3, y3, x4, y4]]` (closed polygon, first point = last point)

#### 3.3.3 Multi-Column Layouts
- **Oregon Statutes:** Often single-column, but may have side-by-side amendments or comparative tables
- **IRS Forms:** Frequently multi-column (e.g., Form 1040 has 2-3 columns)
- **Requirement:** Annotate each column's elements separately with correct reading order

#### 3.3.4 Handwritten Content
- **IRS Forms:** May contain handwritten entries (ignore unless pre-filled examples)
- **Annotation Approach:**
  - Pre-printed form fields: Annotate as their semantic class (Text, Table, etc.)
  - Handwritten entries: Only annotate if part of official IRS example/instructions

#### 3.3.5 Headers and Footers
- **Repeated Elements:** Page headers/footers that appear on every page should be annotated on EVERY page
- **Running Headers:** "OREGON REVISED STATUTES" → Page-header
- **Page Numbers:** Annotate as Page-footer (even if in header position)

#### 3.3.6 Tables
- **Simple Tables:** Single bounding box + segmentation polygon for entire table
- **Complex Tables:** For nested tables or tables with extensive merged cells, annotate outer table as single unit
- **Table Captions:** Annotate separately as "Caption" if visually distinct from table body

#### 3.3.7 Formulas
- **Mathematical Notation:** Tax calculations, algebraic expressions, summation symbols
- **Inline vs. Display Formulas:**
  - Inline (within text): Annotate as Text
  - Display (standalone line/block): Annotate as Formula

#### 3.3.8 Section Headers vs. Titles
- **Title:** Document-level identifier (appears once, typically page 1)
- **Section-header:** Repeated structural divisions (chapters, sections, subsections)
- **Example (Oregon Statutes):**
  - Title: "CHAPTER 166 — OFFENSES AGAINST PUBLIC ORDER"
  - Section-header: "166.250 Unlawful use of weapon"

### 3.4 Image Specifications

#### 3.4.1 Source Documents
**Oregon Statutes:**
- **Source:** Oregon Legislative Assembly official PDFs ([oregonlegislature.gov](https://www.oregonlegislature.gov/bills_laws/Pages/ORS.aspx))
- **Format:** PDF documents converted to 300 DPI PNG images
- **Coverage Required:** Representative sample across ORS Chapters (suggest: 10-15 chapters covering diverse topics)
- **Suggested Chapters:**
  - **ORS 166:** Offenses Against Public Order (weapons, drugs)
  - **ORS 90:** Residential Landlord and Tenant
  - **ORS 107:** Domestic Relations (marriage, divorce)
  - **ORS 163:** Offenses Against Persons (assault, homicide)
  - **ORS 646:** Trade Practices and Antitrust Regulation
  - **ORS 656:** Workers' Compensation
  - **[Add 4-9 more chapters per contractor recommendation]**

**IRS Documents:**
- **Source:** IRS official PDFs ([irs.gov/forms-pubs](https://www.irs.gov/forms-pubs))
- **Format:** PDF documents converted to 300 DPI PNG images
- **Coverage Required:** Representative sample of common forms and publications
- **Suggested Documents:**
  - **Form 1040:** U.S. Individual Income Tax Return (+ Schedules A, B, C, D, E, SE)
  - **Form 1065:** U.S. Return of Partnership Income
  - **Form 1120:** U.S. Corporation Income Tax Return
  - **Form 941:** Employer's Quarterly Federal Tax Return
  - **Form W-2:** Wage and Tax Statement
  - **Publication 17:** Your Federal Income Tax (For Individuals)
  - **Publication 535:** Business Expenses
  - **Form 8949:** Sales and Other Dispositions of Capital Assets
  - **[Add 5-10 more forms per contractor recommendation]**

#### 3.4.2 Image Conversion Requirements
- **Resolution:** 300 DPI (dots per inch)
- **Format:** PNG (lossless compression)
- **Color Space:** RGB or Grayscale (maintain original document color profile)
- **Dimensions:** Maintain aspect ratio (typical: 2550 × 3300 pixels for 8.5" × 11" page at 300 DPI)
- **File Naming Convention:**
  ```
  {document_type}_{identifier}_page_{page_num:04d}.png

  Examples:
  oregon_statute_ORS_166_250_page_0001.png
  irs_form_1040_2024_page_0001.png
  irs_pub_17_2024_page_0123.png
  ```

#### 3.4.3 Multi-Page Documents
- **Requirement:** Annotate ALL pages of included documents (not just sample pages)
- **Rationale:** Training data must include diverse layouts (cover pages, body text, appendices, indexes)

---

## 4. Data Collection Requirements

### 4.1 Document Selection Criteria

#### 4.1.1 Oregon Statutes
- **Minimum:** 2,000 pages
- **Preferred:** 3,500-5,000 pages
- **Diversity Requirements:**
  - At least 10 different ORS chapters
  - Mix of short statutes (1-5 pages) and long statutes (20+ pages)
  - Include statutes with tables (e.g., fee schedules, penalty matrices)
  - Include statutes with definitions sections (heavy list-item content)
  - Include statutes with cross-references and footnotes

#### 4.1.2 IRS Documents
- **Minimum:** 2,000 pages
- **Preferred:** 3,500-5,000 pages
- **Diversity Requirements:**
  - At least 15 different forms/publications
  - Mix of 1-page forms (W-2) and multi-page forms (1040 package)
  - Include forms with complex tables (Schedule D capital gains)
  - Include forms with mathematical formulas (tax computation worksheets)
  - Include instructional publications with mixed content (Pub 17, Pub 535)
  - **Year Coverage:** 2022-2024 tax years (to capture recent layout changes)

### 4.2 Document Sourcing
- **Contractor Responsibility:** Contractor must download and prepare source PDFs from official government websites
- **Client Responsibility:** Client will provide final list of specific ORS chapters and IRS forms to include (based on contractor recommendations)
- **Version Control:** All source PDFs must be archived with download date and URL metadata

### 4.3 PDF to Image Conversion
- **Contractor Responsibility:** Contractor must perform PDF → PNG conversion at 300 DPI
- **Tools:** Any industry-standard tool acceptable (PyMuPDF, Poppler, ImageMagick, Adobe Acrobat)
- **Quality Assurance:** Contractor must verify images are legible and complete (no missing content)

---

## 5. Quality Assurance Requirements

### 5.1 Inter-Annotator Agreement (IAA)

**Requirement:** Minimum 10% of pages must receive **dual independent annotation** to measure consistency.

**IAA Measurement:**
- **Metric:** IoU (Intersection over Union) ≥ 0.85 for matching bounding boxes
- **Class Agreement:** ≥ 95% agreement on element classification
- **Adjudication:** Client reserves right to review disputed annotations and provide binding guidance

**IAA Reporting:**
- Provide IoU distribution histogram (per class)
- Provide confusion matrix for class labels
- Provide list of edge cases requiring client clarification

### 5.2 Validation Set

**Requirement:** Contractor must annotate a **100-page pilot set** for client review before full-scale annotation begins.

**Pilot Set Composition:**
- 50 pages Oregon Statutes (5 different chapters, 10 pages each)
- 50 pages IRS documents (5 different forms, 10 pages each)

**Client Review Process:**
1. Contractor delivers pilot set with annotations
2. Client reviews within 5 business days
3. Client provides feedback and clarifications
4. Contractor revises pilot set if needed
5. Client approves pilot set before full production begins

### 5.3 Quality Metrics

All delivered annotations must meet these thresholds:

| Metric | Threshold | Measurement Method |
|--------|-----------|-------------------|
| **Bounding Box Accuracy** | ≤ 5px margin error | Random sample (n=100) manual verification |
| **Class Label Accuracy** | ≥ 98% correct | Automated validation against ground truth subset |
| **Segmentation Polygon Validity** | 100% valid polygons | Automated COCO format validation |
| **Missing Annotations** | < 1% elements missed | Client spot-check (n=100 pages) |
| **Inter-Annotator Agreement (IoU)** | ≥ 0.85 | Dual-annotation subset (10% of dataset) |

### 5.4 Automated Validation Checks

Contractor must run automated validation before delivery:
- ✅ COCO JSON schema validation (valid JSON, required fields present)
- ✅ Bounding box coordinates within image dimensions
- ✅ Segmentation polygons closed (first point = last point)
- ✅ No duplicate annotation IDs
- ✅ All image files referenced in JSON exist with correct dimensions
- ✅ Category IDs match defined classes (1-11)

---

## 6. Deliverables

### 6.1 Annotated Dataset

**File Structure:**
```
dataset/
├── images/
│   ├── oregon_statutes/
│   │   ├── ORS_166/
│   │   │   ├── oregon_statute_ORS_166_250_page_0001.png
│   │   │   ├── oregon_statute_ORS_166_250_page_0002.png
│   │   │   └── ...
│   │   ├── ORS_90/
│   │   │   └── ...
│   │   └── ...
│   └── irs_documents/
│       ├── form_1040/
│       │   ├── irs_form_1040_2024_page_0001.png
│       │   ├── irs_form_1040_2024_page_0002.png
│       │   └── ...
│       ├── form_1065/
│       │   └── ...
│       └── ...
├── annotations/
│   ├── oregon_statutes_train.json
│   ├── oregon_statutes_val.json
│   ├── oregon_statutes_test.json
│   ├── irs_documents_train.json
│   ├── irs_documents_val.json
│   └── irs_documents_test.json
├── source_pdfs/
│   ├── oregon_statutes/
│   │   ├── ORS_166.pdf
│   │   ├── ORS_90.pdf
│   │   └── ...
│   └── irs_documents/
│       ├── form_1040_2024.pdf
│       ├── form_1065_2024.pdf
│       └── ...
└── metadata/
    ├── dataset_statistics.json
    ├── iaa_report.pdf
    ├── annotation_guidelines_final.md
    └── source_document_manifest.csv
```

### 6.2 Train/Validation/Test Split

**Required Split Ratios:**
- **Train:** 70% of pages
- **Validation:** 15% of pages
- **Test:** 15% of pages

**Split Strategy:**
- **Document-level split:** Entire documents assigned to one split (avoid page leakage)
- **Stratified split:** Ensure proportional class distribution across splits
- **Reporting:** Provide per-split statistics (class distribution, page count, document count)

### 6.3 Documentation

#### 6.3.1 Dataset Statistics Report (`dataset_statistics.json`)
```json
{
  "dataset_name": "Legal & Regulatory Layout Analysis Dataset v1.0",
  "creation_date": "2025-01-15",
  "total_pages": 8234,
  "total_annotations": 125847,
  "document_types": {
    "oregon_statutes": {
      "pages": 4117,
      "documents": 12,
      "chapters": ["ORS 90", "ORS 107", "ORS 163", "ORS 166", "..."]
    },
    "irs_documents": {
      "pages": 4117,
      "documents": 18,
      "forms": ["1040", "1065", "1120", "W-2", "..."]
    }
  },
  "class_distribution": {
    "Caption": 1247,
    "Footnote": 3891,
    "Formula": 892,
    "List-item": 34521,
    "Page-footer": 8234,
    "Page-header": 8234,
    "Picture": 432,
    "Section-header": 9873,
    "Table": 2156,
    "Text": 52341,
    "Title": 4026
  },
  "iaa_metrics": {
    "mean_iou": 0.91,
    "class_agreement_rate": 0.97
  }
}
```

#### 6.3.2 Inter-Annotator Agreement Report (`iaa_report.pdf`)
- IAA methodology description
- IoU distribution histograms (per class)
- Class confusion matrix
- Edge case examples with adjudication decisions
- Annotator training and calibration process

#### 6.3.3 Annotation Guidelines Final Version (`annotation_guidelines_final.md`)
- All annotation rules and edge case decisions made during project
- Illustrated examples of challenging annotations
- Decision log for ambiguous cases

#### 6.3.4 Source Document Manifest (`source_document_manifest.csv`)
```csv
document_id,document_type,source_url,download_date,pages,file_path
ORS_166,oregon_statute,https://www.oregonlegislature.gov/bills_laws/ors/ors166.html,2025-01-10,45,source_pdfs/oregon_statutes/ORS_166.pdf
form_1040_2024,irs_form,https://www.irs.gov/pub/irs-pdf/f1040.pdf,2025-01-10,2,source_pdfs/irs_documents/form_1040_2024.pdf
```

### 6.4 Delivery Format
- **Packaging:** Single compressed archive (ZIP or TAR.GZ)
- **File Size:** Client will provide file transfer method if > 10GB
- **Checksums:** Provide SHA-256 checksums for all deliverable files
- **License:** All annotations delivered under [specify license: CC-BY-4.0, proprietary, etc.]

---

## 7. Project Timeline

### 7.1 Proposed Schedule (12 Weeks)

| Week | Phase | Deliverable |
|------|-------|-------------|
| 1 | **Kickoff & Planning** | Finalized document list, annotation guidelines review |
| 2 | **PDF Collection & Conversion** | All source PDFs downloaded, converted to PNG at 300 DPI |
| 3-4 | **Pilot Annotation (100 pages)** | 100-page pilot set annotated and delivered for client review |
| 5 | **Pilot Review & Revision** | Client feedback incorporated, guidelines updated |
| 6-10 | **Full-Scale Annotation** | Progressive annotation of remaining 7,000-9,000 pages |
| 10 | **Quality Assurance** | IAA measurement, automated validation, error correction |
| 11 | **Documentation & Packaging** | All reports, statistics, and documentation finalized |
| 12 | **Final Delivery** | Complete dataset delivered with all metadata |

### 7.2 Milestones & Payments (Suggested)

| Milestone | Payment | Deliverable |
|-----------|---------|-------------|
| **Kickoff** | 10% | Signed contract, project plan |
| **Pilot Approval** | 20% | Client-approved 100-page pilot set |
| **50% Annotation Complete** | 30% | ~4,000 pages annotated, IAA report for first batch |
| **100% Annotation Complete** | 30% | All pages annotated, QA validation passed |
| **Final Delivery** | 10% | Complete dataset with all documentation delivered |

---

## 8. Contractor Qualifications

### 8.1 Required Experience
- ✅ Demonstrated experience with **COCO format annotation** (provide examples)
- ✅ Experience annotating **document layout** (tables, text blocks, headers, footers)
- ✅ Experience with **legal or regulatory documents** (preferred but not required)
- ✅ Proven inter-annotator agreement processes with IAA > 0.85

### 8.2 Required Capabilities
- ✅ **Team Size:** Sufficient annotators to complete 4,000-10,000 pages in 8-12 weeks
- ✅ **Annotation Tools:** CVAT, LabelStudio, Labelbox, or equivalent COCO-compatible platform
- ✅ **Quality Assurance:** Documented QA process with automated validation
- ✅ **Data Security:** Ability to handle public government documents (no PHI/PII in this dataset)

### 8.3 Preferred Qualifications
- ✅ Experience with **YOLOv8** or **Faster R-CNN** annotation workflows
- ✅ Experience with **DocLayNet**, **PubLayNet**, or similar layout analysis datasets
- ✅ Domain expertise in legal/tax documents
- ✅ U.S.-based annotation team (for legal document comprehension)

---

## 9. Proposal Requirements

Contractors should submit proposals including:

### 9.1 Technical Approach
- Annotation platform and tools to be used
- Annotator training plan
- Quality assurance methodology
- IAA measurement process

### 9.2 Team Composition
- Number of annotators
- Annotator qualifications and training
- Project manager and QA reviewer roles

### 9.3 Timeline
- Detailed project schedule (Gantt chart or equivalent)
- Milestone dates
- Dependencies and assumptions

### 9.4 Pricing
- **Per-page pricing:** Cost per annotated page
- **Volume discounts:** Pricing tiers for 2K, 5K, 10K pages
- **Pilot set pricing:** Cost for 100-page pilot (if separate)
- **Rush pricing:** Cost for accelerated timeline (if applicable)

### 9.5 Sample Work
- Provide 3-5 example pages from previous document layout annotation projects
- COCO JSON samples demonstrating annotation quality

### 9.6 References
- At least 2 client references for similar projects
- Links to public datasets you've annotated (if any)

---

## 10. Evaluation Criteria

Proposals will be evaluated on:

| Criterion | Weight | Description |
|-----------|--------|-------------|
| **Technical Quality** | 35% | Annotation methodology, QA process, IAA approach |
| **Experience & Qualifications** | 25% | Relevant past projects, team expertise, sample work |
| **Pricing** | 20% | Cost competitiveness, payment terms, value for money |
| **Timeline** | 10% | Realistic schedule, ability to meet deadlines |
| **Communication & Responsiveness** | 10% | Clarity of proposal, responsiveness to questions |

---

## 11. Terms & Conditions

### 11.1 Data Rights
- Client retains **full ownership** of all annotated data
- Client may publish dataset publicly or use commercially without restriction
- Contractor may use anonymized examples for portfolio (with client approval)

### 11.2 Confidentiality
- All source documents are **publicly available government documents** (no confidentiality required)
- Annotation guidelines and methodologies are **confidential** (do not share with third parties)

### 11.3 Acceptance Criteria
- Client has **5 business days** to review each milestone deliverable
- Client may reject deliverables that fail quality metrics (Section 5.3)
- Contractor must remediate rejected work within **10 business days** at no additional cost

### 11.4 Termination
- Either party may terminate with **30 days written notice**
- Upon termination, contractor delivers all completed annotations to date
- Payment prorated based on completed work meeting quality standards

---

## 12. Questions & Submission

### 12.1 Questions
Submit questions via [email/portal] by **[deadline: 2 weeks before proposal due date]**

All questions and answers will be shared with all bidders (anonymized).

### 12.2 Proposal Submission
- **Due Date:** [Specify date]
- **Format:** PDF document, maximum 20 pages (excluding appendices)
- **Submission Method:** [Email/portal/etc.]

### 12.3 Selection Process
- **Proposal Review:** [Date range]
- **Contractor Interviews:** [Date range] (shortlisted contractors only)
- **Contract Award:** [Target date]
- **Project Start:** [Target date]

---

## 13. Appendices

### Appendix A: Example Annotation (Oregon Statute)

**Source:** ORS 166.250 Unlawful use of weapon

**Annotation Snippet:**
```json
{
  "image_id": 1,
  "file_name": "oregon_statute_ORS_166_250_page_0001.png",
  "annotations": [
    {
      "id": 1,
      "category_id": 6,
      "category_name": "Page-header",
      "bbox": [100, 50, 2350, 80],
      "comment": "Header contains 'OREGON REVISED STATUTES'"
    },
    {
      "id": 2,
      "category_id": 8,
      "category_name": "Section-header",
      "bbox": [150, 250, 2250, 120],
      "comment": "Section identifier: '166.250 Unlawful use of weapon'"
    },
    {
      "id": 3,
      "category_id": 10,
      "category_name": "Text",
      "bbox": [150, 400, 2250, 600],
      "comment": "Statutory text paragraph (1)"
    },
    {
      "id": 4,
      "category_id": 4,
      "category_name": "List-item",
      "bbox": [200, 1050, 2200, 180],
      "comment": "Subsection (a) - enumerated exception"
    }
  ]
}
```

### Appendix B: Example Annotation (IRS Form)

**Source:** Form 1040 (2024) Page 1

**Annotation Snippet:**
```json
{
  "image_id": 100,
  "file_name": "irs_form_1040_2024_page_0001.png",
  "annotations": [
    {
      "id": 1001,
      "category_id": 11,
      "category_name": "Title",
      "bbox": [800, 100, 950, 150],
      "comment": "Form title: 'Form 1040'"
    },
    {
      "id": 1002,
      "category_id": 9,
      "category_name": "Table",
      "bbox": [150, 1200, 2400, 800],
      "comment": "Tax computation table (lines 1-15)"
    },
    {
      "id": 1003,
      "category_id": 3,
      "category_name": "Formula",
      "bbox": [1800, 2100, 400, 80],
      "comment": "Line 15 computation: 'Subtract line 14 from line 12'"
    }
  ]
}
```

### Appendix C: Annotation Tool Recommendations

**Recommended Platforms:**
1. **CVAT** (Computer Vision Annotation Tool) - Open source, COCO export
2. **LabelStudio** - Open source, flexible annotation interface
3. **Labelbox** - Commercial, enterprise-grade QA workflows
4. **Scale AI** - Managed annotation service
5. **Amazon SageMaker Ground Truth** - AWS-integrated annotation

### Appendix D: Class Distribution Targets

To ensure balanced training data, aim for these approximate class distributions:

| Class | Target % | Min Annotations | Notes |
|-------|----------|-----------------|-------|
| Text | 35-45% | 30,000+ | Most common element |
| List-item | 20-30% | 20,000+ | Very common in statutes |
| Page-header | 8-12% | 8,000+ | One per page minimum |
| Page-footer | 8-12% | 8,000+ | One per page minimum |
| Section-header | 8-12% | 8,000+ | Document structure |
| Table | 2-5% | 2,000+ | Critical for tax forms |
| Footnote | 2-5% | 2,000+ | Common in legal docs |
| Title | 2-5% | 2,000+ | One per document |
| Caption | 1-3% | 1,000+ | Table/figure captions |
| Formula | 1-2% | 1,000+ | Tax calculations |
| Picture | 0.5-1% | 500+ | Rare but important |

---

**END OF SPECIFICATION**

---

## Contact Information

**Project Lead:** [Your Name]
**Email:** [Your Email]
**Phone:** [Your Phone]
**Organization:** [Your Organization]

**Proposal Questions:** Submit by [Date] to [Email/Portal]
**Proposal Due Date:** [Date]
**Expected Award Date:** [Date]
