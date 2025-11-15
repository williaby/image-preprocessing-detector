# LLM Prompt: Document Annotation Strategy Analysis

**Purpose:** Use this prompt with any LLM (ChatGPT, Claude, Gemini) to help plan your document annotation strategy, evaluate contractors, or optimize your dataset composition.

**Instructions:** Copy the prompt below and paste it into your LLM interface. Customize the bracketed sections with your specific details.

---

## Prompt Template

```markdown
I'm planning a document annotation project for training machine learning models in
layout analysis and need strategic guidance.

## Project Context

**Domain:** Legal and regulatory document processing for RAG applications

**Use Case:** Intelligent document preprocessing system that detects layout elements
(tables, text blocks, images, formulas) and quality issues (blur, skew, contrast)
before vector database ingestion.

**Document Types:**
- Oregon Statutes (state-level legal documents)
- IRS forms and publications (federal tax documents)

**ML Tasks:**
1. Document layout detection (YOLOv8) - 11 classes
2. Table detection and structure recognition
3. Image quality assessment (IQA) on embedded images
4. Text detection gate (routing documents to appropriate pipelines)

## Current Situation

**Existing Datasets Available:**
- DocLayNet: 80,863 pages with "Laws & Regulations" category (COCO format)
  - Contains federal regulations/statutes (sources not fully documented)
  - 11 annotation classes: Caption, Footnote, Formula, List-item, Page-footer,
    Page-header, Picture, Section-header, Table, Text, Title
- TableBank: 417K labeled tables (not legal documents)
- Pile of Law: Text-only federal regulations (no layout annotations)

**Gap Analysis:**
- ❌ No Oregon Statutes dataset found
- ❌ No IRS documents with layout annotations found
- ✅ DocLayNet may contain federal statutes/regulations (needs verification)

**Dataset Sufficiency Concern:**
From my current dataset analysis:
- Total Samples: 3,489,124
  - Real-World: 3,184,124 (91.3%)
  - Synthetic: 305,000 (8.7%)
- 🔴 Synthetic Only: 1 functional requirement (100% synthetic, 0% real-world)

## Options Under Consideration

### Option 1: Contract Professional Annotation
**Scope:** 4,000-10,000 pages Oregon Statutes + IRS documents
**Estimated Cost:** $8,000-60,000 (depending on volume and vendor)
**Timeline:** 12 weeks
**Quality:** IAA ≥ 0.85, professional QA

### Option 2: DIY Annotation
**Scope:** 500-2,000 pages (smaller pilot)
**Estimated Cost:** $3,000-12,000 (hire freelancers via Upwork)
**Timeline:** 6-8 weeks
**Quality:** Self-managed, higher risk

### Option 3: Transfer Learning from DocLayNet
**Scope:** Use DocLayNet "Laws & Regulations" subset + fine-tuning
**Estimated Cost:** $0 (dataset cost) + compute for training
**Timeline:** 2-4 weeks
**Quality:** Depends on domain similarity (federal vs. state laws, general forms vs. IRS)

### Option 4: Hybrid (Real + Synthetic)
**Scope:** 2,000-4,000 real pages + synthetic augmentation
**Estimated Cost:** $10,000-25,000
**Timeline:** 8-10 weeks
**Quality:** Mixed (real-world foundation + synthetic diversity)

## Questions for Analysis

Please provide strategic recommendations on:

### 1. Dataset Sufficiency
Given that I currently have 91.3% real-world data across my overall dataset but
one functional requirement is 100% synthetic:
- Is this a critical gap that must be addressed?
- What are the risks of synthetic-only data for [SPECIFY WHICH FR]?
- Should I prioritize real-world annotation for that specific FR?

### 2. Annotation Strategy
Considering my budget is [INSERT: $10K / $25K / $50K / flexible]:
- Which option (1-4) provides the best ROI for model performance?
- What's the minimum viable dataset size for production-quality layout detection?
- Should I start with a smaller pilot (e.g., 1,000 pages) and expand later?

### 3. Document Selection
For maximum training value with limited budget:
- Which Oregon ORS chapters should I prioritize? (e.g., diverse layouts, common in legal RAG)
- Which IRS forms provide best coverage? (e.g., 1040 vs. specialized schedules)
- Should I annotate full documents or strategically sample pages?

### 4. Synthetic Data Viability
For the 8.7% synthetic data I currently use:
- What quality thresholds should synthetic data meet to avoid degrading model performance?
- Can synthetic data effectively augment real-world annotations for rare classes (e.g., Formula, Picture)?
- What are best practices for validating synthetic layout annotations?

### 5. Transfer Learning Feasibility
If I use DocLayNet as base training data:
- What domain shift risks exist between federal regulations → Oregon statutes?
- What domain shift risks exist between general documents → IRS forms?
- How many fine-tuning samples would I need for each domain?

### 6. Vendor Selection
If I choose contracted annotation (Option 1):
- What are the top 3 red flags to watch for in contractor proposals?
- Should I prioritize vendors with legal document expertise vs. general layout annotation experience?
- Is dual annotation (IAA measurement) worth the 10-15% cost premium?

### 7. Quality vs. Quantity Tradeoff
With a fixed budget:
- Is it better to annotate 10,000 pages at "good enough" quality (IoU 0.75-0.80) or
  5,000 pages at "excellent" quality (IoU 0.90+)?
- What's the performance impact of lower-quality annotations on YOLOv8 training?

### 8. Phased Approach
Should I adopt a staged strategy:
- Phase 1: 1,000 pages diverse sample → train baseline model → measure performance
- Phase 2: Identify model weaknesses (confusion matrix analysis)
- Phase 3: Targeted annotation of underperforming classes/document types
- Phase 4: Scale to 5,000-10,000 pages for production model

Or is it better to annotate the full dataset upfront with uniform coverage?

## Constraints & Preferences

**Budget:** [INSERT: e.g., "Prefer <$20K but can stretch to $35K for strong ROI"]
**Timeline:** [INSERT: e.g., "Need production model in 6 months"]
**Risk Tolerance:** [INSERT: e.g., "Low - this is for legal compliance applications"]
**Existing Resources:** [INSERT: e.g., "Have ML engineers but no annotation expertise"]

## Desired Output

Please provide:
1. **Recommended strategy** (which option or hybrid approach)
2. **Justification** (why this maximizes performance per dollar)
3. **Risk mitigation** (what could go wrong and how to prevent it)
4. **Phased roadmap** (month-by-month plan with decision gates)
5. **Success metrics** (how to measure if annotation quality is sufficient)
6. **Alternative scenarios** (backup plans if initial approach underperforms)

## Additional Context

[INSERT ANY ADDITIONAL DETAILS:]
- Specific Oregon statutes you work with frequently
- IRS forms that are mission-critical for your use case
- Performance requirements (e.g., "Must detect tables with >95% recall")
- Deployment constraints (e.g., "Real-time inference <100ms/page")
```

---

## Example Customization

Here's how you might fill in the template for your specific situation:

```markdown
## Constraints & Preferences

**Budget:** Prefer <$25K but can justify up to $40K if demonstrably better model performance

**Timeline:** Need production-ready model in 5 months (by April 2025) to support Q2 legal research launch

**Risk Tolerance:** Medium-Low - This supports legal professionals, so accuracy is critical,
but not life-safety or regulated compliance

**Existing Resources:**
- 2 ML engineers with PyTorch/YOLOv8 experience
- Access to Modal.com GPU compute (T4/A10G)
- No in-house annotation expertise
- Legal domain expert available for guideline review (5-10 hours)

## Additional Context

**High-Priority Oregon Statutes:**
- ORS 90 (Landlord-Tenant): Very common in our legal research queries
- ORS 163 (Crimes Against Persons): Complex statutory structure, good training diversity
- ORS 656 (Workers' Compensation): Heavy use of tables and fee schedules

**High-Priority IRS Forms:**
- Form 1040 + Schedules (most common tax filing)
- Form 1065 (partnership returns - complex multi-page layout)
- Publication 535 (mixed text/tables, good for testing layout variety)

**Performance Requirements:**
- Table detection recall >90% (critical for extracting tax computation tables)
- Layout detection mAP@.50 >0.80 (acceptable for v1.0 production)
- Inference latency <200ms/page on T4 GPU (user-facing application)

**Deployment Constraints:**
- Cloud deployment (Modal.com serverless functions)
- Must handle scanned PDFs with varying quality (DPI 150-600)
- Multi-page document batching (process entire ORS chapter or full tax return)
```

---

## Usage Tips

### For Different Scenarios

**Scenario 1: Budget Optimization**
Focus your prompt on: "With exactly $15,000 budget, what's the optimal allocation
between annotation volume, quality, and document diversity?"

**Scenario 2: Contractor Evaluation**
Add: "I've received 3 proposals: Vendor A ($3.50/page, 6K pages, 10 weeks),
Vendor B ($5.00/page, 4K pages, 8 weeks, legal doc specialists), Vendor C
($2.00/page, 8K pages, 14 weeks, offshore team). Which should I choose?"

**Scenario 3: Technical Validation**
Add: "I trained a baseline YOLOv8 model on DocLayNet (laws_and_regulations subset)
and tested on 50 Oregon statute pages. Table mAP@.50 = 0.62, Text mAP = 0.78.
Is this sufficient to justify fine-tuning, or do I need a from-scratch Oregon dataset?"

**Scenario 4: Synthetic Data Design**
Add: "If I generate synthetic Oregon statutes using LaTeX templates + random content,
what layout parameters should I vary? (font size, margins, table complexity,
footnote density, etc.) What's the risk of overfitting to synthetic patterns?"

### Multi-Turn Conversation

After the LLM provides initial recommendations:

**Follow-up 1:** "You recommended Option 3 (transfer learning). Can you create a
detailed experiment plan with success criteria for each phase?"

**Follow-up 2:** "What specific DocLayNet statistics should I analyze to determine
if the 'laws_and_regulations' category is similar enough to Oregon statutes?"

**Follow-up 3:** "Draft a 1-page vendor evaluation rubric I can use to score the
3 proposals I received."

---

## Expected LLM Output Quality

A strong LLM response should include:

✅ **Quantitative reasoning:** "Based on YOLO data requirements (typically 1,500-3,000
instances per class for 0.80+ mAP), you'll need at least 2,500 annotated pages
assuming ~1.2 tables/page in legal documents..."

✅ **Risk analysis:** "Transfer learning risks: Domain shift between federal regs
(dense legal prose, citations) vs. Oregon statutes (more structured, definitions
sections). Mitigation: Fine-tune on 500-1,000 Oregon pages..."

✅ **Decision framework:** "Use this decision tree: If DocLayNet test mAP > 0.75 →
fine-tune (save $20K). If < 0.75 → annotate 2,000 Oregon pages. If 0.65-0.75 →
hybrid approach..."

✅ **Concrete next steps:** "Week 1: Download DocLayNet laws_and_regulations subset.
Week 2: Train baseline YOLOv8-m. Week 3: Test on 100 Oregon pages (manually annotate
for ground truth). Week 4: Decision gate..."

---

## Saving LLM Responses

Create a decision log file:

```bash
# Save LLM conversation for reference
docs/planning/ANNOTATION_STRATEGY_LLM_ANALYSIS.md
```

Include in the file:
- Date and LLM model used (e.g., "ChatGPT-4 on 2025-11-14")
- Full prompt and responses
- Decision made based on analysis
- Rationale for any deviations from LLM recommendations

---

## Related Documents

- **Full Contractor Spec:** [CONTRACTOR_SPEC_DATASET_ANNOTATION.md](CONTRACTOR_SPEC_DATASET_ANNOTATION.md) (44 pages)
- **Executive Summary:** [CONTRACTOR_SPEC_EXECUTIVE_SUMMARY.md](CONTRACTOR_SPEC_EXECUTIVE_SUMMARY.md) (2 pages)
- **Dataset Sufficiency Report:** [DATASET_SUFFICIENCY_REPORT.md](DATASET_SUFFICIENCY_REPORT.md)
- **Project Plan:** [../planning/PROJECT_PLAN.md](../planning/PROJECT_PLAN.md)

---

**Prompt Version:** 1.0
**Last Updated:** 2025-11-14
**Maintained by:** [Your Name]
