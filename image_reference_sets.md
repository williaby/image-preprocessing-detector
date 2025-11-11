# Comprehensive Validation Framework for Pre-Conversion Document Analysis in RAG Pipelines

**A Strategic Framework for Document Pre-Conversion Validation**

---

## Executive Summary

The automated ingestion of documents, such as PDFs and JPGs, into a Retrieval-Augmented Generation (RAG) pipeline requires a preliminary validation step to prevent the introduction of corrupted or unparseable data. A "bad" document—one that fails to convert cleanly to markdown—presents a bifurcated failure mode. This report establishes a validation framework that addresses both systemic document failures and semantic structural failures, providing a comprehensive review of existing datasets to build a robust testing suite.

This framework is built on a core dichotomy:

1. **Functional Failure (Systemic Issues)**: This pertains to failures where the entire document or large portions of it are unreadable, leading to a catastrophic failure of the Optical Character Recognition (OCR) process itself. This category maps directly to image quality issues such as low lighting, noise, blur, and low resolution. The validation goal is to test a model's ability to measure image quality against a continuous metric.

2. **Semantic Failure (Structural Issues)**: This pertains to failures where the document image is of high quality and perfectly legible, but its content includes structural elements that a standard, linear markdown converter cannot correctly parse. This includes tables, mathematical formulas, and handwritten annotations, which become jumbled or lost, corrupting the semantic meaning of the extracted text.[^1] The validation goal is to test a model's ability to detect and locate these high-risk structures using discrete ground truth, such as bounding boxes.

Within this framework, a second distinction is critical for validating systemic failures: the nature of the ground truth itself. Document Image Quality Assessment (DIQA) is often measured in two ways: subjective human perception or objective functional outcome.[^3]

- **Subjective (Mean Opinion Score - MOS)**: Datasets like DIQA-5000[^5] and others[^6] employ human annotators to provide a MOS score, answering the question, "Does this document look sharp and high-quality to a person?"

- **Objective (OCR Accuracy)**: Other datasets, as referenced in multiple studies[^3], use OCR accuracy as the ground truth quality score. This answers the functional question, "Can a machine successfully read this document?"

For the specific application of a RAG pipeline, which is an automated, non-human process, the success of text extraction is not dependent on human-perceived quality (MOS). It is 100% dependent on the success of the OCR engine (e.g., Tesseract, ABBYY) used in the pipeline. Therefore, datasets that utilize OCR accuracy as the ground truth[^7] are functionally superior and more relevant to this use case than those based on subjective human scores. This analysis will prioritize datasets that enable this direct, functional validation.

---

## I. Benchmarking Systemic Degradations: Document Image Quality Assessment (DIQA)

This section reviews datasets designed to validate the detection of systemic "image issues" (low lighting, noise, blur), structured by the subjective-versus-objective ground truth principle.

### A. Subjective (Perceptual) Benchmarks: Validating against Human Perception (MOS)

These datasets are typically large, modern, and well-suited for training a robust model to recognize a wide variety of degradations that humans perceive as "low quality."

#### 1. DIQA-5000 (VQualA 2025 Challenge)

This dataset is built from 500 original document images captured by mobile phones, encompassing text-heavy pages, tables, diagrams, and handwritten notes.[^5] The originals contain the exact degradations sought: "defocus blur, moiré patterns, creases or warping, and shadows"[^5], which map to blur, noise, and low lighting. Each original is processed with enhancement algorithms to create 10 variants, totaling 5,000 images.[^5]

**Ground Truth**: 15 annotators provided three separate Mean Opinion Scores (MOS) on a 0-5 scale for:
1. Overall quality
2. Sharpness
3. Color fidelity[^5]

This multi-dimensional ground truth would allow a validation model to be tested specifically on its ability to predict the "sharpness" score as a proxy for blur.

**Use Case**: Training/validation for perceptual quality assessment

#### 2. DocIQ (DIQA-5000 Dataset)

A separate but similarly named dataset, this DIQA-5000 consists of 5,000 document images derived from 500 real-world PDFs that were printed and then "enhanced".[^8] It also provides multi-dimensional subjective ratings from 15 subjects for "overall quality, sharpness, and color fidelity".[^9] The associated research highlights a model that uses layout masks during quality assessment, suggesting that the location of a blur (e.g., on a title vs. a footer) impacts perceived quality.[^11]

**Format**: 1600x1600 images[^11]

**Use Case**: State-of-the-art perceptual benchmark with layout-aware quality metrics

### B. Objective (Functional) Benchmarks: Validating against Machine Readability (OCR)

This approach represents the gold standard for RAG pre-flight validation, as it directly correlates image degradation with the functional failure of text extraction.

#### 3. Sharpness-OCR-Correlation (SOC) Dataset ⭐ **Gold Standard for RAG**

This is a smaller, highly focused dataset ideal for functional validation.[^7] It contains 175 document images captured from 25 "ideally clean" documents.[^12] The sole degradation introduced is "varying levels of focal-blur introduced manually".[^13]

**Ground Truth**: Not a human score but the "character level OCR accuracy"[^13] obtained from three separate OCR engines:
- ABBYY Finereader (acc_f)
- Tesseract (acc_t)
- Omnipage (acc_o)[^7]

This ground truth is provided in a simple Excel file (`SOC_gt.xlsx`).[^7]

This dataset enables a direct and powerful validation strategy. The RAG pipeline will almost certainly use an OCR engine like Tesseract to extract text. The SOC dataset provides the exact Tesseract accuracy (acc_t) for its 175 images. A validation framework can thus bypass proxies like "blur level" and test the model on its ability to predict the actual outcome of interest.

**Recommended Validation Strategy:**
1. Define a functional failure threshold (e.g., "any document where Tesseract accuracy is < 90% must be flagged").
2. Run the OpenCV detection model against the 175 images in the SOC dataset.
3. Measure the model's precision, recall, and F1-score in predicting which images fall below this acc_t < 0.90 threshold.

This provides the most functionally relevant, high-impact validation possible for detecting "image issues."

### C. Comparative Analysis of DIQA Datasets

| Dataset | Size | Degradation Types | Ground Truth Format | File Formats | Key Differentiator for RAG |
|---------|------|-------------------|---------------------|--------------|----------------------------|
| **DIQA-5000 (VQualA)** | 5,000 images | Defocus blur, moiré, creases, shadows, enhancement artifacts[^5] | Mean Opinion Score (MOS) 0-5 for 3 dimensions: overall, sharpness, color fidelity[^5] | JPGs, output.txt for demo scores[^5] | Large-scale, multi-dimensional perceptual quality benchmark. Good for training. |
| **DocIQ (DIQA-5000)** | 5,000 images | Enhancement artifacts on printed PDFs[^8][^9] | Mean Opinion Score (MOS) 0-5 for 3 dimensions: overall, sharpness, color fidelity[^9] | 1600x1600 images[^11] | State-of-the-art perceptual benchmark. Associated with layout-aware quality metrics.[^11] |
| **SOC Dataset** | 175 images | Varying levels of focal blur[^13] | OCR Accuracy (ABBYY, Tesseract, Omnipage)[^7] | Images + SOC_gt.xlsx[^7] | Gold standard for RAG validation. Directly links blur to functional OCR failure.[^3] |

---

## II. Validating Structural Hazard Detection: Layout, Tables, and Formulas

This section transitions from systemic quality to structural hazards. In these cases, the images are assumed to be high-quality, but their content (layout, tables, formulas) will break a simple markdown conversion. The validation goal is to confirm the model can detect and flag these semantic regions.

### A. General Layout Analysis (The "Table" Detector)

The primary task is to detect tables, which is best validated using a general-purpose document layout analysis dataset.

#### 1. PubLayNet

This is a large dataset annotated with bounding boxes and segmentations.[^14] However, its critical limitation is its source: it is derived only from the PubMed Central Open Access Subset.[^14] The annotations are also automatically generated by matching PDF and XML formats, not by human review.[^14]

**Classes**: 5 (text, title, list, table, figure)
**Annotation**: COCO format (auto-generated)[^14]
**Size**: 335K+ images
**Limitation**: Very low source diversity (PubMed only)[^14][^15]

#### 2. DocLayNet ⭐ **Recommended for Layout Validation**

This dataset was created specifically to address the "severe lack in layout variability" of datasets like PubLayNet.[^15] Research shows that models trained on PubLayNet's scientific-only layouts experience a significant drop in accuracy when applied to more diverse, challenging layouts.[^15]

**Key Features**:
- 80,863 pages manually annotated by experts[^15]
- 6 document categories: Finance, Science, Patents, Tenders, Law, and Manuals[^17]
- 11 classes (e.g., Table, Caption, Footer)[^17]
- COCO JSON format (human-annotated)[^15]
- PNG images (1025x1025)[^17]

For an "in-the-wild" RAG pipeline that will ingest diverse documents (legal, financial, technical), **DocLayNet is the only appropriate choice** for validation. Validating against PubLayNet would be misleading. A table detector can be validated by filtering these annotations for the "Table" class and measuring performance against those bounding boxes.

### B. Specialized Table Detection

Should the general "Table" class in DocLayNet prove insufficient, more specialized datasets exist.

#### 3. TableBank

A large dataset of 417K labeled tables generated with weak supervision from Word and Latex documents.[^18] For the detection task, it provides annotations in the familiar MS COCO format.[^18]

#### 4. PubTabNet

An even larger dataset with over 568k images, also from PubMed.[^20] Its ground truth is significantly more detailed, providing a full HTML representation of the table, including Cell Content and Cell Location.[^20]

**Recommendation**: For the detection task (flagging a region), not recognition (parsing the table's contents), the detailed ground truth of PubTabNet is unnecessary. The **TableBank-Detection dataset**[^18] would be the most appropriate specialized dataset. However, the primary recommendation remains to **start with DocLayNet**, as it validates table detection within the context of complex, full-page layouts.

### C. Mathematical Formula Detection

Detecting mathematical formulas is a unique challenge. The primary difficulty, as noted in research[^22], lies in the "huge variations" in aspect ratio, the "small size of embedded or inline formulas," and the "similarity between variables and normal text characters." These "inline" formulas are the true RAG-killers, as they are easily mangled with surrounding text.

#### 5. Marmot Dataset

Sourced from 400 document pages, this dataset provides extremely detailed, multi-level ground truth.[^23]

**Key Features**:
- 1,575 "isolated formulas"
- 7,907 "embedded formulas" (critical for RAG)[^23]
- Bounding boxes and Unicode for individual characters within each formula[^23]
- PDF + Images format[^23]

#### 6. TFD-ICDAR 2019

This dataset provides ground truth at two levels:[^24]
1. "Math regions" (a bounding box for the whole formula)
2. "Character locations" (a bounding box for each character, labeled as "MATH_SYMBOL" or "ORDINARY_TEXT")

**Size**: ~800 pages, ~38,000 total math expressions[^24]
**Format**: PDF URLs + GT files[^24]

**Critical Validation Strategy**: A validation strategy that lumps all formula types together would be dangerously misleading. A model could achieve high accuracy by only finding large, isolated formulas while missing 100% of the critical inline ones. Therefore, the validation must be structured to report **two separate F1-scores**:
1. "Isolated Formula Detection"
2. "Inline Formula Detection"

The latter score, validated against the 7,907 embedded formulas in Marmot[^23] or the equivalent in TFD-ICDAR 2019[^24], is the mission-critical metric for this task.

### D. Comparative Analysis of Layout Datasets

| Dataset | Size | Source Diversity | No. of Classes | Annotation Format | Key RAG Implication |
|---------|------|------------------|----------------|-------------------|---------------------|
| **PubLayNet** | 335K+ images | Very Low (PubMed only)[^14][^15] | 5 (text, title, list, table, figure) | COCO (Auto-generated)[^14] | Misleading for "in-the-wild" validation. Accuracy drops significantly on other doc types.[^15] |
| **DocLayNet** | 80,863 images | High (Finance, Legal, Patents, Manuals, etc.)[^17] | 11 (e.g., Table, Caption, Footer)[^17] | COCO (Human-annotated)[^15] | **Gold standard for general layout validation.** Matches diverse, real-world RAG inputs. |

### E. Comparative Analysis of Formula Detection Datasets

| Dataset | Size | Ground Truth Format | Explicit "Inline" Support | File Formats | Key RAG Implication |
|---------|------|---------------------|---------------------------|--------------|---------------------|
| **Marmot** | 400 pages; 1,575 isolated + 7,907 embedded formulas[^23] | BBox for formula; BBox + Unicode for chars within formula[^23] | Yes (7,907 "embedded" formulas)[^23] | PDF + Images[^23] | Ideal for RAG. Explicitly separates "isolated" and "embedded" formulas for granular validation. |
| **TFD-ICDAR 2019** | ~800 pages; ~38,000 total expressions[^24] | BBox for "math region"; BBox + label for chars ("MATH" vs "TEXT")[^24] | Yes (distinguishes single-char vs multi-char expressions)[^24] | PDF URLs + GT files[^24] | Also excellent. Character-level labels allow validation of detection (region) and classification (text vs. math). |

---

## III. Isolating Modality and Geometric Issues: Handwriting and Skew

This section addresses the final two detection tasks: identifying non-printed text (handwriting) and geometric distortion (skew), both of which are critical failures for standard OCR.

### A. Handwritten vs. Printed Text Segmentation

The challenge is not classifying entire documents as handwritten. The real-world problem, common in forms and annotated legal or financial documents, is the "mixed-modality" case where handwritten text and printed text "coexist" or "overlap" on the same page.[^2] This requires a segmentation approach, not a simple classification.

#### 7. SignaTR6K

This is the ideal dataset for this task. It consists of over 6,000 augmented images derived from 200 "pixel-level manually annotated crops" from "genuine legal documents".[^26]

**Key Features**:
- Pixel-level segmentation masks for three classes: Printed Text (PT), Handwritten Text (HT), and Background (BG)[^26]
- 6,257 total images from Thomson Reuters legal documents
- 256x256 crops with RGB pixel-wise segmentation
- Train/Val/Test splits: 5,169 / 530 / 558
- Real legal docs with overlapping text[^26][^28]

**Validation Strategy**: The pixel-level masks in SignaTR6K[^26] are perfect for a precise, robust validation metric like the **Intersection over Union (IoU)**.[^31] The OpenCV model's generated "handwriting region" (whether a bounding box or a mask) can be compared directly to the ground truth "HT" mask to calculate a precise IoU score.

### B. Geometric Distortion (Skew) Detection

Skew, or document rotation, will cause line-based OCR to fail. The validation metric is the "absolute difference of the estimated skew and the ground truth skew angle"[^33], also known as the **Average Error Deviation (AED)**.[^34]

A robust validation requires a two-part strategy:

#### 8. DISEC'13 - "Unit Test" for Algorithm Correctness

This dataset tests the skew-detection algorithm in a "clean-room" environment.

**Key Features**:
- 155 unique images, each synthetically rotated 10 times (1,550 total samples)[^35]
- Ground truth: Precise floating-point angle "randomly selected from the limited range of (-15°, +15°)"[^35]
- **Validation Metric**: Average Error Deviation (AED)[^35]

**Purpose**: Success on this dataset confirms the algorithm (e.g., Hough Transform[^36]) is mathematically correct.

#### 9. Kaggle "Noisy and Rotated Scanned Documents" - "Integration Test" for Robustness

This dataset tests the algorithm in a real-world scenario.

**Key Features**:
- 600 scanned images (500 labeled) that are both "noisy" and "rotated"[^37]
- Ground truth: Scanned angle in tighter range of -5° to 5°[^37][^40]
- **Validation Metric**: Average Error Deviation (AED)

**Purpose**: This two-part validation is essential. A skew-detection algorithm relies on finding text lines; image noise can break these lines, causing the algorithm to fail even on a correct image. If a model performs well on DISEC'13 but poorly on the Kaggle dataset, this indicates the algorithm is correct but not robust. The solution would be to implement a denoising pre-processing step before the skew detection is performed.

### C. Comparative Analysis of Handwriting & Skew Validation Datasets

| Task | Dataset | Size | Ground Truth Format | Key Features | Validation Metric |
|------|---------|------|---------------------|--------------|-------------------|
| **Handwriting** | SignaTR6K | 6,000+ images (from 200 crops)[^26] | Pixel-level segmentation masks (PT, HT, BG)[^26] | Real legal docs; focuses on overlapping text[^26][^28] | Intersection over Union (IoU)[^31] |
| **Skew** | DISEC'13 | 1,550 samples (155 unique)[^35] | Precise rotation angle (-15° to +15°)[^35] | "Unit Test": Clean images, only rotation. Tests algorithm correctness. | Average Error Deviation (AED)[^35] |
| **Skew** | Kaggle Noisy/Rotated | 600 images (500 labeled)[^37] | Rotation angle (-5° to +5°)[^40] | "Integration Test": Images are both noisy and rotated. Tests algorithm robustness. | Average Error Deviation (AED) |

---

## IV. Synthetic Generation: A Controlled Environment for Comprehensive Validation

An advanced alternative (or supplement) to collecting static datasets is to synthetically generate validation data. This provides programmatic control over degradation parameters, enabling the generation of "massive ground-truthed data with high variability".[^41]

### A. Synthetic Document Generation Tools

#### 10. DocCreator

An open-source, cross-platform software for generating synthetic documents and applying degradations.[^42]

**Key Features**:
- Simulates physical and print defects
- Degradations: "Bleed-through," "Ink degradation," "Adaptive blur," "Holes," "Phantom character apparition," and "Paper deformation"[^42]
- Software (GUI/C++)[^42][^43]
- Controlled XML ground truth[^42]

**Use Case**: Excellent for simulating aging and printing defects on physical documents.

#### 11. Genalog ⭐ **Recommended for Automation**

An "open-source Python library" from Microsoft.[^45]

**Key Features**:
- **Python Library** - Highly integrable into ML validation workflows
- Simulates digital and scan defects
- Degradations: "blur," "bleed-through," "salt-and-pepper noise," and "morphological operations" (e.g., erode, dilate)[^45]
- Controlled (text + HTML/CSS templates)[^45]
- 2023 benchmark: "strong performer," "best-balanced tool," "slightly better for numerical accuracy" than DocCreator[^45]

**Use Case**: Ideal for automation. Easy to script and integrate into a validation pipeline for sensitivity analysis.

### B. Sensitivity Analysis Methodology

These tools enable a far more sophisticated validation methodology: **Sensitivity Analysis**.

Instead of a simple F1-score on a static dataset with random degradation levels, a synthetic tool allows for the creation of a validation set on a gradient. For example:

```
doc_skew_0.5.jpg (skew = 0.5°)
doc_skew_1.0.jpg (skew = 1.0°)
doc_skew_1.5.jpg (skew = 1.5°)
...
doc_skew_10.0.jpg (skew = 10.0°)
```

The same can be done for blur kernel size, noise percentage, etc. By running the OpenCV detector against this gradient, it is possible to plot the model's "Issue Detected" probability against the ground truth degradation parameter. This plot, or "characteristic curve," reveals precisely at what point (e.g., "3.5°," "2.0px blur kernel") the model's detection activates. This allows for the precise tuning of the model's internal thresholds to match a specific business requirement, transforming validation from a pass/fail check into a robust engineering practice.

### C. Comparative Analysis of Synthetic Tools

| Tool | Type | Supported Degradations | Ground Truth | Key RAG Implication |
|------|------|------------------------|--------------|---------------------|
| **DocCreator** | Software (GUI/C++)[^42][^43] | Physical/Print: Bleed-through, Ink degradation, Adaptive blur, Holes, Phantom characters, Paper deformation[^42] | Controlled XML ground truth[^42] | Excellent for simulating aging and printing defects on physical documents. |
| **Genalog** | Python Library[^45] | Digital/Scan: Blur, Bleed-through, Salt-and-pepper noise, Morphological operations (erode/dilate)[^45] | Controlled (text + HTML/CSS templates)[^45] | **Ideal for automation.** Easy to script and integrate into a validation pipeline for sensitivity analysis. |

---

## V. Strategic Recommendations for Validation Suite Construction

A comprehensive validation framework for this RAG pre-flight model should be constructed in two stages: a "Core Suite" of existing datasets for broad functional validation, and an "Advanced Strategy" for precise threshold tuning.

### A. The "Core Suite": Immediate Validation Plan

This suite provides a pragmatic collection of the best-in-class existing datasets to build a comprehensive validation testbed.

1. **For Systemic Quality (Blur, Noise)**:
   - **Dataset**: SOC Dataset[^7]
   - **Reason**: Its ground truth is Tesseract OCR accuracy, which is the most functionally relevant metric for the RAG pipeline. This is a direct test of the consequence of the blur, not just the blur itself.[^7]

2. **For Structural Layout (Tables)**:
   - **Dataset**: DocLayNet[^17]
   - **Reason**: Its high source diversity (legal, financial, patents)[^17] matches the "in-the-wild" nature of a RAG pipeline. Its "Table" class provides a "gold-standard" human-annotated[^17] ground truth in COCO format.

3. **For Structural Content (Formulas)**:
   - **Dataset**: Marmot[^23] or TFD-ICDAR 2019[^24]
   - **Reason**: Both provide explicit bounding boxes for the mission-critical "inline" / "embedded" formulas[^22], allowing for a separate, crucial validation score.

4. **For Modality (Handwriting)**:
   - **Dataset**: SignaTR6K[^26]
   - **Reason**: Its pixel-level masks for overlapping printed and handwritten text[^26] provide a robust validation (via IoU metric) for the most challenging version of this problem.

5. **For Geometry (Skew)**:
   - **Dataset 1**: DISEC'13[^35] (as a "Unit Test" for correctness).
   - **Dataset 2**: Kaggle "Noisy and Rotated"[^37] (as an "Integration Test" for robustness).
   - **Reason**: This two-part approach validates the algorithm's correctness against its robustness to noise, which are two separate failure modes.

### B. The "Advanced" Strategy: Sensitivity and Threshold Analysis

This second phase of validation moves beyond simple pass/fail accuracy to robust engineering.

- **Tool**: Use Genalog.[^45] Its nature as a Python library makes it the easiest to integrate into an automated validation script.
- **Methodology**: Implement the "Sensitivity Analysis" described in Section IV.
- **Action**: Create a script that iterates through a range of degradation parameters (e.g., skew_angle from 0 to 10 in 0.5-degree steps; blur_kernel from 1 to 5 in 0.5px steps).
- **Outcome**: This produces a characteristic curve for each detector. This allows the model's internal OpenCV thresholds to be quantitatively tuned to meet a specific, documented performance target (e.g., "reject all documents with skew > 2.0°"), ensuring the pre-flight check is both effective and aligned with business requirements.

---

## VI. Phase 2 Week 1 Coverage Analysis

This section maps the identified datasets against the specific requirements for **Phase 2 Week 1: Data Collection & Augmentation** for Image Quality Assessment (IQA).

### A. Phase 2 Week 1 Requirements (from PROJECT_PLAN.md)

**Objectives**:
1. Collect 10k+ clean document images from:
   - RVL-CDIP (400k images)
   - Tobacco800 (800 images)
   - DocBank (500k+ clean scanned documents)
   - Born-digital PDFs rendered at high DPI
2. Build Albumentations augmentation pipeline
3. Generate 50k synthetic augmented images
4. Weak supervision using BRISQUE/NIQE scores
5. Manual validation on 10k ambiguous samples

### B. Coverage Matrix

| Requirement | Status | Identified Datasets | Gap/Action Needed |
|------------|--------|---------------------|-------------------|
| **IQA Training Data** | ✅ **GOOD** | DIQA-5000 (x2 variants), SOC Dataset | Well covered with 10k+ IQA-annotated images |
| **Base Clean Documents** | ⚠️ **PARTIAL** | None explicitly identified in this document | **NEED**: RVL-CDIP, Tobacco800, DocBank (user will handle locally) |
| **Synthetic Augmentation Tools** | ✅ **EXCELLENT** | Genalog (Python), DocCreator (GUI/C++) | Both tools identified with clear recommendations |
| **Skew Detection Validation** | ✅ **GOOD** | DISEC'13, Kaggle Noisy/Rotated | Two-part validation strategy covered |
| **Functional Validation** | ✅ **EXCELLENT** | SOC Dataset (OCR accuracy ground truth) | Gold standard for RAG validation |
| **Blur/Noise/Contrast** | ✅ **GOOD** | DIQA-5000 variants, Synthetic tools | 10k perceptual MOS + synthetic generation |

### C. Assessment Summary

**✅ Well Covered:**
- IQA-specific validation datasets (10k+ annotated images)
- Synthetic augmentation infrastructure (Genalog Python library recommended)
- Functional validation (SOC Dataset with OCR accuracy ground truth)
- Phase 3 datasets (all layout, table, formula, handwriting datasets identified)

**⚠️ Gaps (User to Handle Locally):**
- Base clean document datasets (RVL-CDIP, Tobacco800, DocBank) needed for synthetic augmentation source material

### D. Phase-Appropriate Dataset Mapping

**Phase 2 (Current - IQA Training):**
- ✅ DIQA-5000 (VQualA 2025) - 5k images with MOS scores
- ✅ DocIQ (DIQA-5000) - 5k images with layout-aware quality metrics
- ✅ SOC Dataset - 175 images with OCR accuracy (primary functional validation)
- ✅ DISEC'13 - 1,550 samples for skew detection
- ✅ Kaggle Noisy/Rotated - 600 images for skew robustness
- ✅ Genalog (Python library) - Synthetic augmentation (50k target)
- ⚠️ **USER TO HANDLE**: RVL-CDIP, Tobacco800, DocBank (base clean documents)

**Phase 3 (Future - Layout Detection):**
- ✅ DocLayNet - 80,863 human-annotated pages (recommended)
- ✅ PubLayNet - 335k+ pages (not recommended due to low diversity)
- ✅ TableBank - 417K tables (specialized)
- ✅ PubTabNet - 568k+ tables (specialized)
- ✅ Marmot - 9,482 formulas (1,575 isolated + 7,907 embedded)
- ✅ TFD-ICDAR 2019 - 38k formulas
- ✅ SignaTR6K - 6k+ handwriting segmentation crops

### E. Immediate Actions for Phase 2 Week 1

1. **Prioritize Genalog Integration** (see Section VII below):
   - Python library = easy integration into augmentation pipeline
   - Use for Phase 2 Week 1 synthetic data generation (50k target)
   - Implement sensitivity analysis methodology

2. **Leverage SOC Dataset for Functional Validation**:
   - 175 images with Tesseract accuracy ground truth
   - Most functionally relevant for RAG pipeline validation
   - Use as primary test set for IQA model evaluation

3. **Use DIQA-5000 Datasets for Training**:
   - 10k total images (5k + 5k from both variants)
   - MOS scores available for perceptual quality training
   - Combine with synthetic augmentations from Genalog

4. **Base Clean Documents** (User to handle locally):
   - RVL-CDIP (400k images) - https://adamharley.com/rvl-cdip/
   - Tobacco800 (800 images) - Kaggle or original source
   - DocBank (500k pages) - https://doc-analysis.github.io/docbank-page/

---

## VII. References

[^1]: PdfTable: A Unified Toolkit for Deep Learning-Based Table Extraction - arXiv
[^2]: Distinction between handwritten and machine-printed text based on the bag of visual words model - PRImA Research Lab
[^3]: A deep learning approach to document image quality assessment - ResearchGate
[^5]: VQualA 2025 DIQA: Document Image Quality ... - CodaLab
[^6]: (PDF) A Document Image Dataset for Quality Assessment - ResearchGate
[^7]: rjchern/DIQA_CNN: Document Image Quality Assessment via Convolutional Neural Network - GitHub
[^8]: [Literature Review] DocIQ: A Benchmark Dataset and Feature Fusion Network for Document Image Quality Assessment - Moonlight
[^9]: DocIQ: A Benchmark Dataset and Feature Fusion Network for Document Image Quality Assessment - ChatPaper
[^11]: DocIQ: A Benchmark Dataset and Feature Fusion Network for Document Image Quality Assessment - arXiv
[^12]: A dataset for quality assessment of camera captured document images - ResearchGate
[^13]: A Dataset for Quality Assessment of Camera Captured Document Images - ResearchGate
[^14]: Document layout recognition dataset: PubLayNet - Kaggle
[^15]: DocLayNet: A Large Human-Annotated Dataset for Document-Layout Analysis - ResearchGate
[^17]: DS4SD/DocLayNet: DocLayNet: A Large Human ... - GitHub
[^18]: TableBank Dataset
[^20]: TableExtractNet: A Model of Automatic Detection and Recognition of Table Structures from Unstructured Documents - MDPI
[^22]: ICDAR 2021 Competition on Mathematical Formula Detection - ResearchGate
[^23]: User Manual of Co-Reader - ICST PKU
[^24]: MaliParag/TFD-ICDAR2019: TDF-ICDAR 2019 Dataset for ... - GitHub
[^26]: Handwritten and Printed Text Segmentation: A Signature Case Study - arXiv
[^28]: Handwritten and Printed Text Segmentation: A Signature Case Study - CVF Open Access
[^31]: ICDAR 2013 Handwritten Segmentation Contest - ResearchGate
[^33]: Algorithms for document image skew estimation - Digital Scholarship@UNLV
[^34]: A Novel Adaptive Deskewing Algorithm for Document Images - PMC
[^35]: A Document Skew Detection Method Using Fast Hough Transform - arXiv
[^36]: Voting-Based Document Image Skew Detection - MDPI
[^37]: Noisy and Rotated Scanned Documents - Kaggle
[^40]: CNN to correct the Rotation of Noisy Scanned Pages - Kaggle
[^41]: DocCreator: A New Software for Creating Synthetic Ground-Truthed Document Images - MDPI
[^42]: DocCreator/DocCreator: DIAR software for synthetic ... - GitHub
[^43]: DocCreator - LabRI
[^45]: Top 3 Synthetic Document Generators Benchmarked - AIMultiple

---

**Document Version**: 1.1 (Enhanced with Phase 2 Week 1 Analysis)
**Last Updated**: 2025-01-15
**Maintained by**: Image Preprocessing Detector Project Team
