# LLM Prompt: Comprehensive Dataset Research for Document Preprocessing

**Purpose:** Deep web research to identify publicly available datasets that increase functional requirement coverage for a document preprocessing detection system.

**Optimized for:** Perplexity AI, ChatGPT with web browsing, Claude with web search, or any LLM with internet access

**Instructions:** Copy the entire prompt below into your research-capable LLM. The LLM should use web search extensively to find recent datasets (2020-2025).

---

## RESEARCH PROMPT (Copy from here)

```markdown
# Deep Research Task: Document Preprocessing & Layout Analysis Datasets

I need you to conduct comprehensive web research to identify publicly available datasets
that support training ML models for intelligent document preprocessing. Use your web
search capabilities extensively - I expect you to search academic repositories, GitHub,
Hugging Face, Kaggle, government data portals, and research papers published in 2020-2025.

## Project Context

**System:** Intelligent document preprocessing detector for RAG (Retrieval-Augmented Generation) applications

**Purpose:** Analyze documents (PDFs, images) to identify required preprocessing steps before
vector database ingestion. Critical for legal, regulatory, financial, and technical document processing.

**Current State:** I have some datasets (DocLayNet, TableBank, NIST handwriting) but significant
gaps in coverage for specific document types and functional requirements.

---

## Functional Requirements Coverage Gaps

I need datasets that support these functional requirements. For EACH FR below, search for
specialized datasets and mark which FRs each dataset covers.

### FR-1: Document Type Classification

**Requirement:** Classify PDF files into three types:
- **"image_only"**: Scanned documents with no extractable digital text
- **"born_digital"**: Digital text, no significant images
- **"hybrid"**: Digital text + embedded images containing text

**Current Coverage:** 🔴 **100% SYNTHETIC** (0% real-world data)
**Critical Need:** Real-world annotated PDFs labeled by type (minimum 2,000 samples)

**Search Keywords:**
- "scanned vs born-digital document classification dataset"
- "PDF document type annotation dataset"
- "hybrid document detection dataset 2023 2024 2025"
- "OCR vs native text PDF classification"

### FR-2: Text Detection Gate

**Requirement:** Fast detection of text presence in images to route documents to appropriate
processing pipelines.

**Current Coverage:** 🟡 Partial coverage from DocLayNet
**Need:** Datasets with "no text" images (charts, diagrams, photos) vs. "text-present" images

**Search Keywords:**
- "text vs non-text image classification dataset"
- "scene text detection dataset ICDAR COCO-Text"
- "document image text presence annotation"
- "natural images vs document images dataset"

### FR-3: Skew Detection & Correction

**Requirement:** Detect and correct page rotation/skew (±45 degrees)

**Current Coverage:** 🟡 Partial from document image datasets
**Need:** Real-world skewed legal/regulatory documents with ground truth rotation angles

**Search Keywords:**
- "document skew detection dataset ground truth angles"
- "rotated document correction dataset"
- "page orientation detection dataset"
- "document image deskewing benchmark 2023 2024"

### FR-4: Blur Detection (Image Quality Assessment)

**Requirement:** Detect out-of-focus blur, motion blur, compression artifacts in scanned documents

**Current Coverage:** 🟡 Partial from IQA datasets (LIVE, TID2013)
**Need:** Blur annotations specifically for document images (not natural images)

**Search Keywords:**
- "document image quality assessment dataset"
- "scanned document blur detection dataset"
- "OCR quality dataset blur noise artifacts"
- "document image degradation dataset DIBCO H-DIBCO"

### FR-5: Layout Detection (11 Classes)

**Requirement:** Detect document layout elements with bounding boxes:
- Caption, Footnote, Formula, List-item, Page-footer, Page-header, Picture,
  Section-header, Table, Text, Title

**Current Coverage:** ✅ Strong (DocLayNet 80K pages)
**Need:** Legal/regulatory document specialization (Oregon Statutes, IRS forms, federal regulations)

**Search Keywords:**
- "legal document layout analysis dataset 2023 2024"
- "regulatory document annotation dataset"
- "federal register layout detection dataset"
- "IRS tax form dataset annotations"
- "statute layout analysis ground truth"

### FR-6: Table Detection & Structure Recognition

**Requirement:** Detect tables and extract row/column structure

**Current Coverage:** ✅ Strong (TableBank 417K tables, DocLayNet)
**Need:** Complex tables in legal/financial documents (nested headers, merged cells, footnotes)

**Search Keywords:**
- "complex table structure recognition dataset"
- "financial table detection dataset SEC filings"
- "legal document table annotation dataset"
- "table structure recognition benchmark FinTabNet SciTSR"

### FR-7: Formula Detection

**Requirement:** Detect mathematical formulas in documents (tax calculations, equations)

**Current Coverage:** 🟡 Partial from DocLayNet
**Need:** Formula detection in financial/tax documents (not just LaTeX math papers)

**Search Keywords:**
- "mathematical formula detection dataset financial documents"
- "tax calculation formula annotation dataset"
- "formula recognition dataset CROHME ICDAR"
- "equation detection in business documents dataset"

### FR-8: Handwriting Detection

**Requirement:** Detect handwritten vs. printed text regions

**Current Coverage:** ✅ Strong (IAM, NIST, RIMES)
**Need:** Mixed handwritten/printed forms (tax forms, legal affidavits)

**Search Keywords:**
- "handwritten text detection dataset mixed documents"
- "printed vs handwritten segmentation dataset"
- "form understanding dataset handwritten fields FUNSD"
- "tax form handwriting detection dataset"

### FR-9: DPI Detection & Upscaling

**Requirement:** Detect low-resolution images (<300 DPI) and upscale appropriately

**Current Coverage:** 🔴 **Limited** - mostly synthetic evaluation
**Need:** Multi-resolution document datasets with ground truth DPI labels

**Search Keywords:**
- "document image resolution dataset DPI labels"
- "super-resolution dataset document images"
- "low resolution document enhancement dataset"
- "image upscaling benchmark scanned documents"

### FR-10: OCR Quality Assessment

**Requirement:** Predict OCR error rate before running OCR (to decide if preprocessing needed)

**Current Coverage:** 🟡 Partial
**Need:** Documents with OCR ground truth and quality scores

**Search Keywords:**
- "OCR quality prediction dataset"
- "OCR error rate estimation dataset"
- "document image quality for OCR dataset"
- "OCR accuracy benchmark dataset ICDAR robust reading"

---

## Document Type Priorities

I specifically need datasets containing these document types (in priority order):

### Priority 1: Legal & Regulatory Documents

**High Value:**
- **Oregon Statutes** (state-level legal code)
- **Federal Statutes** (United States Code - USC)
- **Federal Regulations** (Code of Federal Regulations - CFR)
- **IRS Tax Forms** (1040, 1065, W-2, etc.) and Publications

**Search Strategy:**
Search government open data portals, legal tech research, law school datasets:
- "legal document analysis dataset GitHub Hugging Face"
- "federal register machine learning dataset"
- "USC CFR document understanding dataset"
- "tax form layout analysis dataset"
- site:github.com "oregon statutes" dataset
- site:huggingface.co "legal documents" annotations
- site:data.gov legal document dataset annotations

### Priority 2: Financial Documents

**High Value:**
- SEC filings (10-K, 10-Q, 8-K)
- Bank statements
- Financial reports
- Invoice/receipt datasets

**Search Keywords:**
- "SEC filing dataset layout annotations"
- "financial document understanding dataset FinTabNet"
- "invoice receipt dataset annotations SROIE CORD"
- "bank statement table detection dataset"

### Priority 3: Technical & Scientific Documents

**High Value:**
- Scientific papers (arXiv, PubMed)
- Technical manuals
- Patent documents

**Search Keywords:**
- "scientific paper layout dataset PubLayNet SciBank"
- "patent document analysis dataset"
- "technical manual dataset annotations"

---

## Search Methodology (IMPORTANT)

### Phase 1: Academic Paper Databases (2020-2025)

Search these repositories for recent datasets:

1. **arXiv.org** - Search terms: "document layout dataset", "document understanding benchmark", "legal document dataset"
2. **Papers with Code** - Filter by "Document Analysis" task, sort by most recent
3. **ACM Digital Library** - Search: "document layout analysis dataset" (2020-2025)
4. **IEEE Xplore** - Search: "document image dataset" filter: 2020-2025
5. **Semantic Scholar** - Search: "annotated legal document dataset"

### Phase 2: Dataset Repositories

Search these platforms:

1. **Hugging Face Datasets** - Search: "document", "layout", "legal", "financial", "IRS", "tax"
   - Filter: created 2020-2025, has annotations
2. **GitHub** - Search: `dataset legal documents annotations`, `document layout ground truth`
   - Filter: recent activity, README with download links
3. **Kaggle Datasets** - Search: "document analysis", "OCR", "table detection", "legal documents"
4. **Zenodo** - Search: "document dataset", "layout annotations"
5. **Data.gov** - Search: "legal documents", "federal register", "IRS forms"

### Phase 3: Specialized Sources

1. **NIST Databases** - Check Special Databases catalog for new releases (2020+)
2. **European Union Open Data Portal** - Search: "legal documents", "regulatory documents"
3. **University Research Groups**:
   - Penn State DALI Lab (document analysis)
   - Adobe Document Understanding Lab
   - Microsoft Document AI Research
4. **Industry Datasets**:
   - RVL-CDIP (tobacco litigation documents - check for updates)
   - Kleister (business documents)
   - DocBank (check for legal document subset)

### Phase 4: Recent Competitions & Challenges

Search for datasets from recent competitions:

1. **ICDAR Competitions** (2021, 2023, 2025) - Document layout, table detection, text extraction
2. **CLEF eHealth** - Clinical document datasets (may have layout annotations)
3. **Kaggle Competitions** - Historical document challenges

---

## Required Output Format

For EACH dataset you find, provide this structured information:

### Dataset Entry Template

```markdown
## Dataset Name

**URL:** [Direct link to dataset download or GitHub repo]

**Source/Publisher:** [Organization or research group]

**Publication Year:** [2020-2025]

**Size:**
- Total documents: [number]
- Total pages/images: [number]
- File size: [GB]

**Document Types Covered:**
- [ ] Oregon Statutes
- [ ] Federal Statutes (USC)
- [ ] Federal Regulations (CFR)
- [ ] IRS Forms/Publications
- [ ] Financial documents (SEC, invoices, etc.)
- [ ] Scientific papers
- [ ] Technical manuals
- [ ] Patents
- [ ] Other: [specify]

**Annotation Type:**
- [ ] Layout bounding boxes (COCO format)
- [ ] Table structure annotations
- [ ] Text regions (printed/handwritten)
- [ ] Document type labels (image_only/born_digital/hybrid)
- [ ] Image quality labels (blur, skew, contrast)
- [ ] OCR ground truth
- [ ] Other: [specify]

**Functional Requirements Covered:** (Check all that apply)
- [ ] FR-1: Document Type Classification
- [ ] FR-2: Text Detection Gate
- [ ] FR-3: Skew Detection
- [ ] FR-4: Blur Detection (IQA)
- [ ] FR-5: Layout Detection (11 classes)
- [ ] FR-6: Table Detection
- [ ] FR-7: Formula Detection
- [ ] FR-8: Handwriting Detection
- [ ] FR-9: DPI Detection/Upscaling
- [ ] FR-10: OCR Quality Assessment

**Format:**
- Image format: [PNG, JPEG, PDF, TIFF]
- Annotation format: [COCO JSON, Pascal VOC, YOLO, custom]
- Resolution/DPI: [if specified]

**License:**
- [ ] Public domain / CC0
- [ ] CC-BY (attribution required)
- [ ] CC-BY-SA (share-alike)
- [ ] Research/academic use only
- [ ] Other: [specify]

**Quality Indicators:**
- Inter-annotator agreement (if reported): [IoU or percentage]
- Validation set provided: [Yes/No]
- Train/test split provided: [Yes/No]
- Data quality issues noted: [any known limitations]

**Relevance Score (1-10):** [How well does this fill my gaps?]
- Legal/regulatory content: [1-10]
- Annotation completeness: [1-10]
- Dataset size adequacy: [1-10]
- Overall: [Average score]

**Notes:**
[Any additional context: associated papers, known issues, comparison to similar datasets]

**Citation:**
[BibTeX or APA citation if from academic paper]
```

---

## Prioritization Criteria

When evaluating datasets, prioritize based on:

1. **Gap Coverage (40%):**
   - Does it cover FR-1 (document type classification)? → High priority
   - Does it cover FR-9 (DPI detection)? → High priority
   - Contains legal/regulatory documents? → High priority

2. **Real-World Data (30%):**
   - Scanned documents from actual sources (not synthetic LaTeX-generated)
   - Government PDFs (Oregon, IRS, Federal Register)
   - Quality variations (blur, skew, low-res) present

3. **Annotation Quality (20%):**
   - COCO format or easily convertible
   - Inter-annotator agreement reported
   - Multiple annotators per document

4. **Dataset Size (10%):**
   - Minimum 1,000 documents for specialized domains
   - Minimum 10,000 pages for general document layout

---

## Minimum Success Criteria

Your research should identify at least:

- **3-5 datasets** covering FR-1 (document type classification)
- **2-3 datasets** with legal/regulatory documents (Oregon, federal, IRS)
- **1-2 datasets** covering FR-9 (DPI/resolution labels)
- **5-10 datasets** overall that fill current gaps

If you cannot find datasets for a specific FR or document type, explicitly note this
and suggest:
- Alternative search strategies
- Potential data generation approaches
- Similar datasets that could be adapted

---

## Additional Research Questions

While searching, also investigate:

### Question 1: DocLayNet Coverage Verification
- Can you find the DocLayNet paper or dataset documentation that specifies EXACTLY
  what sources are in the "Laws & Regulations" category?
- Does it include USC, CFR, state statutes, or other identifiable legal sources?

### Question 2: Recent Dataset Trends (2023-2025)
- What are the newest document understanding datasets published in 2024-2025?
- Any emerging datasets focused on government documents, legal tech, or financial compliance?

### Question 3: Multimodal Document Datasets
- Are there datasets with both visual layout AND text content annotations?
- Datasets designed for document VQA (Visual Question Answering) that might include
  legal or financial documents?

### Question 4: Industry Datasets
- Has TurboTax, LegalZoom, Adobe, or other document processing companies released
  public datasets?
- Any corporate research labs (Google, Microsoft, IBM) with recent document datasets?

### Question 5: International Legal Documents
- Are there annotated datasets for legal documents from other jurisdictions (UK, EU, Canada)
  that could transfer to US legal documents?
- Government open data portals in other countries with better dataset availability?

---

## Output Formatting

Please structure your response as follows:

### Part 1: Executive Summary (1 paragraph)
Brief overview of findings: total datasets found, coverage of high-priority gaps, notable discoveries.

### Part 2: High-Priority Datasets (Top 5-10)
Use the dataset entry template above for each high-priority find. Sort by relevance score.

### Part 3: Supplementary Datasets (Remaining finds)
Shorter descriptions for additional datasets that provide partial coverage or lower relevance.

### Part 4: Gap Analysis
List FRs and document types where NO suitable datasets were found. Suggest alternatives.

### Part 5: Recommendations
Based on findings, recommend:
- Which datasets should I prioritize downloading/using?
- Should I proceed with contractor annotation (from earlier specs) or can I use existing datasets?
- Hybrid strategies (e.g., "Use Dataset X for tables, annotate Oregon statutes separately")

### Part 6: Search Methodology Notes
Document your search process:
- Which repositories/databases you searched
- Total search queries executed
- Most productive search terms
- Dead ends or unproductive search paths (to save me time)

---

## Example Output (Abbreviated)

Here's what a strong response looks like:

```markdown
## Executive Summary

Found 23 datasets with varying relevance. **Strong coverage** for FR-5 (layout detection),
FR-6 (table detection), FR-8 (handwriting). **Critical gaps** remain for FR-1 (document
type classification - 0 datasets found), FR-9 (DPI labels - 1 partial dataset), and
legal document specialization (Oregon statutes - 0 datasets, IRS forms - 1 NIST database).

Highest-value find: **FinTabNet-Complex** (2024) has financial tables with nested structures
similar to tax forms. Potential transfer learning for IRS documents.

Recommendation: Use DocLayNet + FinTabNet for layout/tables, but contract annotation
still needed for Oregon statutes and document type classification (2,000-4,000 pages).

---

## High-Priority Datasets

### 1. FinTabNet-Complex (2024)

**URL:** https://example.com/fintabnet-complex

**Source/Publisher:** Stanford Financial AI Lab

**Publication Year:** 2024

**Size:**
- Total documents: 12,847 SEC filings
- Total pages: 89,234
- File size: 45 GB

**Document Types Covered:**
- [x] Financial documents (SEC, invoices, etc.)
- [ ] IRS Forms/Publications
- [ ] Oregon Statutes

**Annotation Type:**
- [x] Layout bounding boxes (COCO format)
- [x] Table structure annotations (row/column cells, merged cells)
- [ ] Document type labels

**Functional Requirements Covered:**
- [x] FR-5: Layout Detection (Table class heavily represented)
- [x] FR-6: Table Detection (primary focus)
- [ ] FR-1: Document Type Classification

**Format:**
- Image format: PNG (300 DPI)
- Annotation format: COCO JSON + custom table structure JSON
- Resolution/DPI: 300 DPI

**License:**
- [x] CC-BY (attribution required)

**Quality Indicators:**
- Inter-annotator agreement: IoU 0.88 for table bboxes, 0.92 for cell-level
- Validation set: Yes (15% of data)
- Train/test split: 70/15/15 pre-defined

**Relevance Score:** 8/10
- Legal/regulatory content: 6/10 (financial but not IRS/legal)
- Annotation completeness: 9/10
- Dataset size adequacy: 9/10
- Overall: 8/10

**Notes:**
Complex tables similar to IRS Schedule D (capital gains) and Schedule C (business income).
Could serve as proxy for tax form table detection training. Newer than TableBank with
better handling of merged cells and footnote integration.

**Citation:**
```
@inproceedings{zhang2024fintabnet,
  title={FinTabNet-Complex: A Large-Scale Dataset for Complex Table Understanding in Financial Documents},
  author={Zhang, X. and Liu, Y. and Chen, Z.},
  booktitle={ICDAR 2024},
  year={2024}
}
```

[Continue with 4-9 more high-priority datasets...]
```

---

## Ready to Begin?

Start your research now. Use aggressive web search - I expect you to query 30-50 times
across multiple repositories, databases, and academic sources. Focus on datasets published
2020-2025 for best quality and modern annotation standards.

**Estimated research time:** 20-30 minutes of intensive searching
**Expected output length:** 3,000-5,000 words with structured dataset entries

Begin your research and provide comprehensive findings.
```

---

## END OF PROMPT

---

## Usage Instructions for You

### Step 1: Choose Your Research LLM

**Recommended options:**

1. **Perplexity AI** ([perplexity.ai](https://perplexity.ai))
   - Best for: Deep web research with citations
   - Pro subscription recommended for unlimited research
   - Can search academic databases, GitHub, Hugging Face simultaneously

2. **ChatGPT with GPT-4 + Web Browsing** ([chat.openai.com](https://chat.openai.com))
   - Best for: Structured analysis of search results
   - Plus subscription required for web browsing
   - Good at synthesizing information from multiple sources

3. **Claude with Web Search** (if available in your region)
   - Best for: Detailed analysis and longer outputs
   - Strong at following complex instructions

4. **Google Gemini Advanced** ([gemini.google.com](https://gemini.google.com))
   - Best for: Google Scholar integration, Google Dataset Search
   - Can search academic papers effectively

### Step 2: Customize the Prompt (Optional)

You can adjust these sections if needed:

**Adjust Budget Context:**
Add to the end of the prompt:
```markdown
Additional Context: My annotation budget is $20,000-35,000. If you find datasets
that reduce annotation needs to <2,000 pages, that saves significant costs.
Prioritize findings that maximize cost savings.
```

**Adjust Timeline:**
```markdown
Additional Context: I need to start model training by February 2025. Prioritize
datasets that are immediately downloadable (no approval process, no paywalls).
```

**Specify Performance Targets:**
```markdown
Additional Context: My target model performance is mAP@.50 > 0.82 for layout
detection. Prioritize datasets known to produce high-performing models or
with published benchmark results.
```

### Step 3: Run the Research

1. **Copy the entire prompt** (lines 13-485 in the file)
2. **Paste into your chosen LLM**
3. **Wait for comprehensive results** (20-40 minutes depending on LLM)
4. **Save the output** to a file

### Step 4: Save Results

Create a results file:

```bash
docs/reference/DATASET_RESEARCH_RESULTS_[DATE].md
```

### Step 5: Analyze Results

After getting the research results, ask follow-up questions:

**Follow-up 1: Verification**
```markdown
For the top 5 datasets you found, please verify:
1. Are the download links still active?
2. What is the actual file size (check the repository)?
3. Are there any usage restrictions I should be aware of?
4. Has anyone published benchmark results using these datasets?
```

**Follow-up 2: Comparison**
```markdown
Create a comparison matrix of the top 10 datasets with columns:
- Dataset name
- Size (pages)
- Legal/IRS content (Yes/No)
- FR coverage (list FR numbers)
- Cost (free/paid)
- Download complexity (easy/medium/hard)
- Overall recommendation score (1-10)
```

**Follow-up 3: Strategy**
```markdown
Based on your findings, recommend a specific strategy:

Scenario A: I found 5+ high-quality datasets covering most FRs
→ Recommend which to download, how to combine them, minimal contractor annotation needed

Scenario B: I found 2-3 partial datasets with significant gaps
→ Recommend hybrid approach: use these datasets + contract for missing coverage

Scenario C: I found 0-1 relevant datasets
→ Recommend proceeding with full contractor annotation per my earlier spec
```

---

## Expected Research Quality

A **strong research response** should include:

✅ **15-25 dataset candidates** with varying relevance levels
✅ **Direct URLs** to dataset repositories (GitHub, Hugging Face, Zenodo, etc.)
✅ **Publication citations** for datasets from academic papers
✅ **Coverage mapping** showing which FRs each dataset addresses
✅ **Gap identification** for FRs with no datasets found
✅ **Cost-benefit analysis** comparing dataset usage vs. contractor annotation
✅ **Search methodology documentation** (which databases searched, query terms used)

A **weak research response** would be:

❌ Generic dataset names without URLs
❌ Only well-known datasets (DocLayNet, PubLayNet) already mentioned
❌ No verification of download availability
❌ Missing FR coverage mapping
❌ No analysis of legal/regulatory document presence

---

## Integration with Previous Documents

After completing research, you can:

1. **Update contractor spec** - Adjust annotation scope based on available datasets
2. **Revise budget** - Reduce annotation volume if datasets fill gaps
3. **Create hybrid plan** - Use found datasets + targeted contractor annotation for gaps
4. **Update DATASET_SUFFICIENCY_REPORT.md** - Add newly discovered datasets to coverage analysis

---

## Related Documents

- **Contractor Specification (44 pages):** [CONTRACTOR_SPEC_DATASET_ANNOTATION.md](CONTRACTOR_SPEC_DATASET_ANNOTATION.md)
- **Executive Summary (2 pages):** [CONTRACTOR_SPEC_EXECUTIVE_SUMMARY.md](CONTRACTOR_SPEC_EXECUTIVE_SUMMARY.md)
- **Strategy Prompt:** [LLM_PROMPT_ANNOTATION_STRATEGY.md](LLM_PROMPT_ANNOTATION_STRATEGY.md)
- **Dataset Sufficiency Report:** [DATASET_SUFFICIENCY_REPORT.md](DATASET_SUFFICIENCY_REPORT.md)
- **Functional Requirements:** [../requirements/functional_requirements_v2.md](../requirements/functional_requirements_v2.md)

---

**Prompt Version:** 1.0
**Optimized for:** Research-capable LLMs with web access
**Estimated Research Time:** 30-60 minutes (LLM processing)
**Last Updated:** 2025-11-14
