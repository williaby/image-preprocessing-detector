# Head Adequacy Review: code_reg (SIG-G5-4)

> **Status**: ✅ Complete
> **Version**: 2.0
> **Created**: 2026-02-22
> **Updated**: 2026-02-23
> **HAR Index**: [HAR_MASTER_INDEX.md](../HAR_MASTER_INDEX.md)
> **Batch**: F — Page Attributes
> **Adequacy**: ⚠️ Needs Work (Score: 54.6 / 100 | P0 blockers present; all resolvable ≤2 weeks)

---

## Section 1 — Head Specification

| Field | Value |
| --- | --- |
| Head ID | SIG-G5-4 |
| Model | SigLIP 2 NAFlex |
| Group | G5 — Page Attributes |
| Head Name | code_reg (also written as code_confidence) |
| Task Type | Binary Classification — sigmoid output, BCE loss (see architectural note below) |
| Output Format | Sigmoid output [0-1] interpreted as P(document contains code) |
| Priority | P2 |
| Performance Target | AUC ≥ 0.90, F1 ≥ 0.85 on held-out code-heavy documents (proposed; see CODE-G03) |
| Primary L2 Field | `content_flags.has_code` (bool) + `structure.code_language` (enum, optional) |
| Shared-Data Heads | None (dedicated code-detection dataset) |
| Training Phase | Phase 5 — Page Attributes |

### Architectural Note: Regression vs. Binary Classification

This head is named `code_reg` and described as "Regression 0-1" in
[SIGLIP2_MULTITASK_REQUIREMENTS.md](../SIGLIP2_MULTITASK_REQUIREMENTS.md). This framing is
a misnomer. The training signal is `content_flags.has_code`, a boolean field with no ground-truth
continuous intermediate values available at dataset assembly time. The loss function is therefore
Binary Cross-Entropy (BCE) with sigmoid activation — the standard formulation for binary
classification, not regression.

**Recommendation (unanimous from 4-model consensus)**: Formally reclassify this head as binary
classification in all planning documents and in `config/siglip2_multitask.yaml`. The 0-1 output
is best described as "probability of code presence" — not a regression scalar. This changes no
implementation (sigmoid+BCE is already correct) but eliminates metric confusion (MAE is
meaningless here; AUC and F1 are the correct metrics).

**Future path to true regression**: If intermediate labels are later derived (e.g., "code pixel
area fraction" from layout detection), the head can be converted to regression with SmoothL1 loss.
Until such labels exist, binary classification framing is mandatory.

### 8 Supported Code Languages

| Language | Notes |
| --- | --- |
| Python | Dominant in ML/data science documents |
| JavaScript | Web and frontend documents |
| Java | Enterprise documentation |
| C++ | Systems and embedded documentation |
| Go | Infrastructure and tooling documentation |
| Rust | Systems programming documentation |
| TypeScript | Web and typed JavaScript documentation |
| SQL | Database and analytics documentation |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `content_flags.has_code` _(bool)_ + `structure.code_language` _(enum, optional)_

**Confidence Threshold**: tier_0_exact for generated positives (code is known ground truth by
construction); tier_0_exact for L2-labeled negatives (has_code=False confirmed from source dataset
metadata); contamination validation required before negatives can be trusted at this tier (see
CODE-G01).

**Label Provenance**: tier_0_exact for generated positive examples (code is constructed ground
truth); tier_1_annotation for L2-confirmed negatives from multimodal_textbook and DocLayNet
(has_code=False field populated from source labeling).

### Candidate Source Datasets

| Dataset | Total Images | Field Populated | Coverage % | Conf ≥ 0.7 | Usable |
| --- | --- | --- | --- | --- | --- |
| Generated code images (positive class) | 5,000 (dry-run approved) | Self-labeled (generated ground truth) | 100% | tier_0_exact | 5,000 |
| multimodal_textbook (negative class) | ~3,613 from dry-run | has_code=False from L2 metadata | ~72% of dry-run negatives | tier_1_annotation | 3,613 (contamination unvalidated — see CODE-G01) |
| DocLayNet (negative class supplement) | Available for downsampling | Pages without code regions labeled | Partially populated | tier_1_annotation | Available (contamination lower risk than textbook) |
| DocSynth300K (candidate negative) | Available | L2 metadata analysis required | Unknown | Unknown | Requires audit |

### Code Detection Generator Details

`scripts/generate_code_detection_dataset.py` exists and dry-run is complete.

Dry-run result: **8,613 records** (5,000 positive + 3,613 negative)

Generator configuration:

- 8 programming languages (Python, JavaScript, Java, C++, Go, Rust, TypeScript, SQL)
- Dark and light syntax-highlighting themes
- 4 DPI configs (72, 150, 300, 600 DPI)
- 2 rendering styles: "screenshot" (browser/IDE framing) and "printed-code-in-doc" (code embedded in document layout)

**Critical rendering style concern**: The "screenshot" style (IDE chrome, dark background, RGB
syntax highlighting) is architecturally OOD for a document scanner pipeline. SigLIP 2 processes
corrected document images — not IDE windows. The "printed-code-in-doc" style (monospace font in
document context, white background, black text) matches the actual pipeline input distribution.
Generator must enforce ≥70% "printed-code-in-doc" style (see CODE-G04).

### Usable Pool Summary

| Component | Count | Status | Notes |
| --- | --- | --- | --- |
| Generated positives (dry-run) | 5,000 | Approved — full run pending | tier_0_exact; language distribution may be Python-heavy |
| L2 negatives (dry-run) | 3,613 | Contamination unvalidated | multimodal_textbook + DocLayNet; keyword filter needed |
| **Total current pool** | **8,613** | **86% of 10K target** | |
| **Gap to target** | **1,387** | Negatives only | Expandable via DocLayNet/DocSynth300K |

### Contamination Risk Analysis

The negative pool from `multimodal_textbook` carries a **medium-high contamination risk**.
Technical textbooks routinely contain:

- Inline code snippets (`print("hello")` in prose)
- Command-line examples and terminal output
- Configuration file excerpts
- Pseudocode in algorithm descriptions

A page labeled `has_code=False` at the page level may still contain inline code that renders
visually as code to a vision model. Training on these as `code_confidence=0.0` poisons the
model's negative examples. Required mitigation: keyword-based heuristic filter (looking for
`{`, `}`, `;`, `def`, `public static`, `import`, indentation patterns) applied to OCR text
before final inclusion, followed by 100-sample manual spot-check.

DocLayNet negatives carry lower contamination risk (mostly financial/scientific documents
without inline code), but still require spot-check validation.

### VLM Validation Sampling Tier

Generated positives (5,000) require no VLM validation — code is generated ground truth.
L2 negatives require a **10% spot-check** (approximately 360 images from the 3,613) using
the keyword heuristic filter, with manual review of images flagged as potentially contaminated.
Target: reject contaminated negatives and replace with verified non-technical sources (DocLayNet
financial/legal pages).

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| CODE-KI-01 | multimodal_textbook | has_code | Page-level has_code=False does not guarantee absence of inline code snippets visible to a vision model | Keyword filter mitigation planned |
| CODE-KI-02 | Generated positives | code_language | Python likely over-represented in 8-language pool due to generator defaults; per-language caps not enforced | Enforce ≤625 images per language (5K/8 languages) |
| CODE-KI-03 | All positives | rendering_style | Screenshot vs printed-code-in-doc ratio not enforced; uncontrolled ratio risks pipeline domain mismatch | Enforce ≥70% printed-code-in-doc |
| CODE-KI-04 | All positive sources | capture_method | Generated code is entirely born-digital; no scanned physical code (e.g., printed textbook pages, photocopied code listings) | Accepted limitation; partial coverage via DocLayNet negatives of scanned technical docs |

### Remediation Path

1. Apply keyword heuristic filter to multimodal_textbook negatives (0.5 days)
2. Manual spot-check 100 samples from filtered candidates (0.5 days)
3. Run full generator with ≥70% printed-code-in-doc ratio enforced (0.5 days)
4. Enforce per-language caps (≤625 images per language) in generator config (0.25 days)
5. Source 1,387 additional negatives from DocLayNet financial/legal pages (0.5 days)
6. Define AUC/F1 performance targets in `config/siglip2_multitask.yaml` (0.25 days)
7. Source ≥200 real scanned code documents for gold-standard validation holdout (1 day)

---

## Section 3 — Training Dataset Targets

| Field | Value |
| --- | --- |
| Target Count | 10,000 images (5,000 positive + 5,000 negative) |
| Assembly Status | Script created, dry-run complete (8,613 records). Full run pending. |
| Distribution | 50% positive (has_code=True, code_confidence = 1.0) / 50% negative (has_code=False, code_confidence = 0.0) |
| Positive Source | `scripts/generate_code_detection_dataset.py` — 8 languages, dark/light themes, 4 DPI configs, 2 styles |
| Negative Source | L2 multimodal_textbook (has_code=False) + DocLayNet financial/legal pages |
| Real Data Ratio | Positives: 100% synthetic generated; Negatives: real documents from L2 sources |
| Style Distribution Target | ≥70% "printed-code-in-doc" / ≤30% "screenshot" style (currently unenforced) |
| Language Distribution Target | ≤625 per language (8 languages) = balanced 8-way split (currently unenforced) |
| Assembly Script | `scripts/generate_code_detection_dataset.py` |

### Training Split Recommendation

The 50/50 positive/negative training split is appropriate and recommended by 3 of 4 consensus
models (Gemini 2.5 Pro, Gemini 3 Pro, DeepSeek R1). Training on real-world prevalence (~5-10%
code documents) biases the model toward majority-class prediction. The 50/50 split forces the
model to learn discriminative features from both classes.

**Inference threshold calibration**: Deploy with a higher decision threshold (e.g., 0.6-0.7
rather than 0.5) to account for the fact that code-containing documents are rare in the
production stream. The threshold should be calibrated on a held-out validation set reflecting
real-world prevalence (~5-10% positive rate).

One model (Grok-4) recommends a 10/90 positive/negative split to better reflect real-world
prevalence. This is a minority position — the majority view (3 models) is that threshold
calibration at inference is the better path, not skewing the training distribution.

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: 51 / 100 (estimated; computed from head-relevant dimensions)

| Dimension | L2 Field | Relevance | Target | Current | Score |
| --- | --- | --- | --- | --- | --- |
| content_flags | `content_flags.has_code` | CRITICAL — the label; positive/negative balance required | 50% pos / 50% neg; ≥70% printed-code style | 5K pos / 3.6K neg; style ratio unenforced | 60% |
| domain | `domain.level1` | HIGH — code appears in TEC/SCI/EDU docs; must not appear dominant in FIN/LEG negatives | ≥ 3 domains with positives (TEC, SCI, EDU); negatives must span ≥ 3 domains (FIN, LEG, ADM) | Generated positives: domain unknown; negatives: DocLayNet spans FIN/TEC/SCI | 55% |
| capture_method | `capture_method.method` | MEDIUM — code is almost always born-digital; model may learn capture_method as shortcut | ≥ 2 methods; born-digital negatives must be abundant to break spurious correlation | Generated positives: 100% born-digital; negatives: DocLayNet (born-digital) + multimodal_textbook (born-digital) — almost no camera/scanner negatives | 40% |
| color_mode | `image_properties.color_mode` | HIGH — dark-mode screenshots (color) vs printed code (grayscale) are visually distinct training signals | ≥ 2 modes: color (dark-mode screenshots) + grayscale/black-on-white (printed) | Generator covers dark/light themes; no binarized code coverage | 60% |
| resolution | `resolution.category` | MEDIUM — code character recognition is resolution-sensitive (small monospace chars, special symbols) | All 4 DPI tiers (72/150/300/600) represented | Generator covers all 4 DPI tiers | 90% |
| layout_type | `structure.layout_type` | MEDIUM — full-page code listings vs inline snippets vs screenshot windows | ≥ 2 layout types (full-page code; inline-snippet-in-prose) | Generator produces both styles | 65% |
| script_code | `language.script_code` | MEDIUM — code comments in CJK scripts are entirely absent | ≥ 2 script families (Latin + CJK) | All 8 languages generate Latin-only code; no CJK code comments | 20% |
| document_age | `image_properties.document_age` | LOW — code documentation is overwhelmingly modern | Modern dominant | Modern only | 70% |
| degradation | `quality.degradations` | MEDIUM — printed code in scanned books may have blur, contrast issues | ≥ 2 degradation levels in printed-code positives | Generator produces clean DPI tiers; no scan-degraded code examples | 45% |

### Key Diversity Gap: Capture Method Correlation

Code is almost exclusively born-digital (IDEs, editors, PDF renders of code). If all positive
examples are born-digital AND some negatives are also born-digital (DocLayNet), the model learns
to associate capture_method with code rather than visual code structure. Mitigation: ensure
negatives include a large proportion of non-technical born-digital documents (DocLayNet financial
pages, DocSynth300K administrative documents). Born-digital non-code negatives must exceed
born-digital positives in count within the negative pool.

### Key Diversity Gap: Script Coverage

All 8 supported languages produce Latin/ASCII output. Real-world code documents — especially
in East Asian software engineering contexts — contain CJK-script comments, variable names, and
string literals. Python files with Chinese comments or SQL queries with CJK column names are
entirely absent from the positive pool. This creates OOD exposure for non-Western engineering
documents.

---

## Section 5 — Wild Condition Coverage

**Overall Score**: 33% (2 partial + 0 full out of 6 conditions)

| Wild Condition | L2 Field Evidence | Training Coverage | OOD Coverage | Status |
| --- | --- | --- | --- | --- |
| Pseudocode and algorithm boxes in academic papers (LaTeX \algorithm environments, numbered steps, indented logic without valid syntax) | `content_flags.has_code` disputed — pseudocode is not executable code | None — generator produces syntactically valid code only | OOD-Code 8b (arXiv papers with code blocks, 60 images) — but pseudocode is only partially covered | ⚠️ Partial — consensus elevates to P0; false positive risk is high |
| Tabular data with aligned columns and monospace font (log files, CSV previews, terminal output resembling code structure) | `content_flags.has_code` = false (monospace ≠ code) | None — negatives from DocLayNet/textbook; no explicit monospace-heavy non-code examples | OOD-Code 8c (terminal output, 40 images) | ⚠️ Partial — terminal output covered in OOD only |
| CJK code comments — Python/SQL with Chinese/Japanese variable names and comments | `content_flags.has_code` = true; `structure.code_language` = Python/SQL | None — all generated code is Latin/ASCII | Not covered in OOD-Code design | ❌ Not covered |
| Low-resolution scanned code listings (code printed in technical books at 150 DPI, scan-degraded) | `content_flags.has_code` = true; capture via scanner | None — generated code is born-digital; no scan-degraded code positives | OOD-Code 8a (source code screenshots, 100 images) — but these are born-digital, not scanned | ❌ Not covered |
| IDE screenshots with full UI chrome (file tree, status bar, tabs, line numbers, minimap) | `content_flags.has_code` = true | Generator produces clean code blocks; no IDE chrome/framing elements | OOD-Code 8a (IDE screenshots, 100 images of source code screenshots) | ⚠️ Partial — OOD-Code targets IDE screenshots but training has no IDE chrome examples |
| Mixed pages — code block with prose explanation (typical in technical manuals and Jupyter notebooks) | `content_flags.has_code` = true (page level); code occupies minority of page | None — generator produces binary full-page code or full-page non-code; no partial-code mixed pages | OOD-Code 8b (arXiv mixed prose+code, 60 images, 0.3–0.7 confidence range) | ⚠️ Partial — OOD covers this; training has no mixed-page examples at intermediate confidence |

### Missing Training Coverage: Mixed Pages

The most common real-world form of code in documents is a code block embedded within prose
(a technical manual chapter, a Jupyter notebook cell, an arXiv appendix). The generator produces
purely positive (full-page code) or purely negative (no code) examples. Mixed-page examples
with intermediate code confidence (0.3–0.7) are entirely absent from training. The model will
learn to predict only values near 0.0 or 1.0, failing on partial-code pages. This is documented
as KI-G5-4-02 in the scaffold and is a meaningful production gap.

---

## Section 6 — OOD Design

**Primary OOD Category**: OOD-Code (Phase 8, P2, 200 total images)

### OOD Sub-Sources

| Sub-Source | Images | Source | Labels Required | Evaluation Stage | Notes |
| --- | --- | --- | --- | --- | --- |
| 8a. Source code screenshots — IDE/GitHub | 100 | Screenshots of VS Code, JetBrains, GitHub repository view displaying code; 5+ programming languages | `code_confidence=1.0` (human-labeled), `capture_method=born_digital` or `camera_smartphone`, `color_mode=color`, IQA labels | siglip2 | IDE chrome (file tree, line numbers, gutter, tabs, minimap) is outside generator training distribution. Tests robustness to framing elements surrounding code body. Must SHA256+pHash dedup against any training images. |
| 8b. Mixed prose + code — arXiv / Jupyter notebooks | 60 | arXiv technical papers with large code appendices; Jupyter .ipynb exports rendered as page images | `code_confidence` ≈ 0.3–0.7 (human-labeled, proportional to code area fraction), `capture_method=born_digital` | siglip2 | Primary test of intermediate confidence region. Code occupies minority of page. Tests whether head assigns partial confidence rather than binary extreme. SHA256+pHash dedup required against any arXiv pages in negative training set. |
| 8c. Terminal/console output | 40 | Terminal session screenshots; CLI output logs rendered as images | `code_confidence=0.5–0.7` (human-labeled; terminal commands are executable but context-free), `capture_method=born_digital` or `camera_smartphone`, `color_mode=color` | siglip2 | Deliberate ambiguity: monospace text, command-like syntax, but no function/class/import structure. Label with moderate confidence rather than extreme to test boundary behavior. |

### OOD Coverage Gaps

| Gap | Risk | Proposed Remediation |
| --- | --- | --- |
| CJK code comments not in OOD design | MEDIUM — no evaluation of cross-script code detection | Add OOD-Code 8d: Python/SQL files with Chinese/Japanese comments (20 images, generated) |
| Scanned/printed code (book scan at 150 DPI) not in OOD design | MEDIUM — scanner input distribution not evaluated for code detection | Add OOD-Code 8e: scanned technical book pages containing code listings (20 images, internal scan) |
| Pseudocode entirely absent from OOD | HIGH — hard negative gap that causes false positives | OOD-Code 8b partially covers this via arXiv — but dedicated pseudocode-only OOD subset needed (add 20 images of algorithm papers) |

### OOD Acquisition Status

**Status**: Not started (Phase 8, P2)

### OOD Leakage Risk

**Level**: LOW

Generation script uses PIL+Pygments synthesis — no training data from existing datasets.
OOD targets (IDE screenshots, Jupyter notebooks, terminal output) are architecturally distinct
from the generator's clean code blocks and document-embedded styles. The only leakage risk is
arXiv papers in OOD-Code 8b overlapping with arXiv pages used as negatives in training.
SHA256+pHash dedup required for arXiv subset only.

---

## Section 7 — Cross-Head Consistency

### Head Interactions

| Related Head | Relationship | Consistency Requirement |
| --- | --- | --- |
| SIG-G5-1 (capture_cls) | Born-digital capture strongly correlates with code presence — must prevent model learning capture_method as a shortcut feature | Negatives in code_reg training MUST include a large proportion of born-digital non-code documents (DocLayNet financial/legal pages). If all born-digital images are code (positive) and all scanned images are non-code (negative), the model learns capture method rather than visual code content. Born-digital non-code negatives must be ≥50% of the negative pool. |
| SIG-G2-1 (script_code) | `structure.code_language` links to script detection — SQL with CJK column names appears as both has_code=True and CJK script | Code containing CJK strings (SQL: `SELECT 商品名称 FROM 产品表`) creates interaction between code detection and script detection. The model should predict code_confidence ≈ 1.0 regardless of script content — this is a potential failure mode. |
| SIG-G4 heads (handwriting) | No shared training data; orthogonally distinct | No consistency risk. |
| SIG-G3-2 (skew_reg) | Generated code images should have zero skew (generated at skew=0 by default) | Validate that generator produces zero-skew images to avoid confounding skew head evaluation during multi-task training. |

### Split Leakage Risk

**Level**: LOW

Dedicated generation pipeline for positives with independent synthesis. Negative examples from
DocLayNet/multimodal_textbook may overlap with other training datasets — global split registry
must confirm negatives used here are not in other datasets' test splits. Risk is LOW because
code_reg uses these images only for `has_code=False` labels (a different semantic use than other
datasets' primary labels), but leakage into OOD or test sets of other heads must still be
prevented.

### Label Convention

`code_confidence = 0.0` means definitively NO code on the page (confirmed from L2 has_code=False,
after contamination validation). `code_confidence = 1.0` means clearly contains code (generated
examples). Partial code (one snippet in a long document) would produce intermediate score ~0.3–0.5
— but these intermediate labels are NOT yet represented in training data. The absence of mixed-page
training examples means the model will behave as a near-binary classifier even though the output
is a probability. This is documented as a P1 gap requiring partial-code example generation
before the head generalizes beyond binary predictions.

The downstream routing rule from [SIGLIP2_MULTITASK_REQUIREMENTS.md](../SIGLIP2_MULTITASK_REQUIREMENTS.md):
`code_confidence > 0.5` → `enrich_code: true`. The decision threshold of 0.5 should be calibrated
against a real-world prevalence validation set before deployment. With 50/50 training data, the
raw sigmoid output is uncalibrated for a 5-10% prior — a threshold of 0.6-0.7 will likely be
more appropriate in production.

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| CODE-G01 | Negative class contamination unvalidated — 3,613 negatives from multimodal_textbook may contain inline code snippets labeled has_code=False at page level | Page-level L2 label does not guarantee visual code-free content for a vision model | Apply keyword heuristic filter (detect `{`, `}`, `;`, `def`, `public static`, `import`, indentation patterns) to OCR text of all negative candidates; manually spot-check 100 images from high-risk candidates; reject contaminated images and replace with DocLayNet financial/legal pages | 1-2 days |
| CODE-G02 | Full generator run not yet executed — positive class exists only as dry-run | Dry-run was completed for planning; full execution requires approving generator config and triggering full run | Review generator config; enforce ≥70% printed-code-in-doc ratio, ≤625 per language, and consistent DPI distribution; execute full run of `scripts/generate_code_detection_dataset.py` | 0.5 days |
| CODE-G03 | Performance target not defined — no AUC, F1, or MAE threshold specified for this head | Head was marked TBD in SIGLIP2_MULTITASK_REQUIREMENTS.md | Define and document performance targets: AUC ≥ 0.90, F1 ≥ 0.85 on held-out code-heavy documents; add to `config/siglip2_multitask.yaml` and this HAR; source ≥ 200 real scanned code documents as gold-standard validation holdout | 0.5 days (decision + documentation) |
| CODE-G04 | Screenshot vs printed-code-in-doc style ratio not enforced — generator may produce majority screenshot-style images which are OOD for document scanner pipeline | Generator was designed with two styles but no ratio constraint | Add `--printed-ratio 0.70` parameter to generator or enforce 70/30 ratio in config; re-run dry-run to confirm ratio before full execution | 0.5 days |
| CODE-G05 | Head is classified as "regression" in planning documents but uses sigmoid+BCE (binary classification) — causes metric confusion (MAE is meaningless; AUC/F1 are correct) | Naming convention inherited from other G5 heads (shadow_reg, warping_reg) that ARE true regressions | Update `config/siglip2_multitask.yaml`, SIGLIP2_MULTITASK_REQUIREMENTS.md, and this HAR to reflect binary classification framing; change loss function documentation to BCE; update metric tracking to AUC + F1 (not MAE) | 0.5 days (documentation update) |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| CODE-G06 | Pseudocode and algorithm-box negatives absent — LaTeX \algorithm environments, numbered pseudo-steps, and indented logic blocks visually resemble code but are not executable; false positive risk is HIGH on academic papers | Generator only produces syntactically valid code; no pseudocode generation implemented | Source 300-500 arXiv paper pages containing algorithm boxes; label as has_code=False (pseudocode is not code) or has_code=True with low confidence (0.2–0.4) depending on policy decision; add to negative pool as hard negatives | 1 day |
| CODE-G07 | CJK code comments absent from positive pool — Python/SQL/JavaScript with Chinese/Japanese/Korean variable names, comments, and string literals | Generator uses Latin-only content for all 8 languages | Extend generator to add CJK-comment variants: 5% of generated positives should include code with CJK comments (Chinese Python docstrings, Japanese SQL table names, Korean JavaScript variable names) | 1-2 days |
| CODE-G08 | Language distribution may be Python-heavy — generator defaults may produce more Python examples than the 625-per-language cap target | Generator default weights not documented; Python is the largest and most template-varied language | Audit dry-run language distribution; enforce strict ≤625 cap per language in generator; add under-represented languages (Rust, TypeScript, Go) as priority to reach 625 | 0.25 days |
| CODE-G09 | Mixed-page training examples absent — pages containing both code and prose are the most common real-world form, but training data is binary (all-code or all-prose) | Generator produces full-page code blocks; no partial-code page layout | Implement partial-code page generator: embed 1-3 code snippets into a multi-paragraph document layout; target 500-1,000 examples with code occupying 20-50% of page; label code_confidence ≈ 0.4-0.6 using code pixel area fraction | 1-2 days |
| CODE-G10 | Gold-standard validation holdout not sourced — all validation data is synthetic or L2-labeled; real-world accuracy is unmeasurable | No physical document scanning effort planned for code detection | Source ≥ 200 real scanned code document pages (technical manuals, programming textbooks, printed code listings) with human verification of code presence; keep separate from training; use as primary evaluation signal | 1-2 days |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| CODE-G11 | Scanned/printed code absent from positive pool — code printed in textbooks and photocopied listings look different from born-digital code renders; scanner artifacts change appearance | Add 200-500 physically scanned code listing images to positive pool; source from public domain programming books or generate by scanning printed code at 150/300 DPI |
| CODE-G12 | Configuration file formats (YAML, TOML, JSON, INI) not covered by 8 languages — these are structurally similar to code but are configuration data | Define policy: YAML/TOML/JSON displayed in documents → has_code=True with confidence ≈ 0.6; document in schema; optionally add as 9th language variant in generator |
| CODE-G13 | Terminal output policy undefined — should CLI output (commands without function definitions) be has_code=True or False? | Define policy: recommend has_code=True for interactive shell output (commands are executable); label as code_confidence ≈ 0.5–0.7 (lower than IDE code at 1.0); document in L2 schema annotation guide |

---

## Section 9 — Multi-Model Consensus

**Models**: google/gemini-2.5-pro (neutral), google/gemini-3-pro-preview (neutral),
deepseek/deepseek-r1-0528 (neutral), x-ai/grok-4 (neutral)

**Analyst Pre-Consensus Summary**: The code_reg head is in a materially better state than the
shadow_reg and warping_reg heads: a working generator exists, a dry-run has been completed at
86% of target volume, and the data acquisition path is clear. The head is not blocked. However,
four P0 gaps prevent the full run from being trusted: negative contamination is unvalidated,
the generator style ratio is unenforced, performance targets are undefined, and the head is
architecturally misframed as regression. The most serious production risk is the absence of
hard negatives (pseudocode, monospace-heavy non-code content) and the false positive exposure
they create.

### Consensus Results

**Gemini 2.5 Pro (8/10 confidence)**: NEEDS WORK.

- Regression framing is a misnomer; binary classification (sigmoid+BCE) is the correct
  architecture. Re-labeling improves clarity; implementation is already correct.
- 50/50 training split is appropriate; real-world prevalence (~5-10%) affects inference
  threshold calibration, not training data balance.
- Negative contamination is the highest risk; tainted negatives will undermine model accuracy
  directly.
- Hard negatives (pseudocode, algorithm boxes) are critical missing items rated P1 — should
  receive additional urgency.
- Performance targets must be defined before training. Proposed: AUC > 0.98, F1 > 0.95.
- P0 prioritization is correct.

**Gemini 3 Pro (9/10 confidence)**: NEEDS WORK.

- Regression vs. classification distinction is clear and unambiguous: BCE loss + sigmoid =
  binary classification.
- Pseudocode/algorithm-box gap should be elevated from P1 to P0. Without these hard negatives,
  false positive rate on technical documents (academic papers, financial reports with aligned
  columns) will be unacceptable.
- Negative contamination from technical textbooks is severe — keyword heuristic filter before
  manual spot-check is the correct mitigation path.
- Printed-code-in-doc style ratio must be enforced at ≥80%. Screenshot-dominant training will
  fail on scanned/born-digital document ingestion.
- Need gold-standard holdout of ~200 real human-verified scanned pages for meaningful evaluation.

**DeepSeek R1 (8/10 confidence)**: NEEDS WORK.

- Binary classification is the correct framing. Agrees fully.
- 50/50 split for training is correct; evaluate on 5-10% prevalence test set.
- Negative contamination requires keyword heuristic or sourcing alternative verified non-technical
  negatives (novels, administrative reports) where contamination risk is near zero.
- Language imbalance (Python ≤30% cap recommended) and pseudocode hard negatives are both
  important P1 items.
- Confirms all P0 gaps are resolvable within 2-3 weeks.

**Grok-4 (8/10 confidence)**: NEEDS WORK.

- Confirms binary classification framing and BCE loss.
- Uniquely recommends adjusting training split to 10/90 positive/negative to reflect real-world
  prevalence — this is a minority position not supported by the other 3 models. The majority view
  (50/50 training + threshold calibration at inference) is adopted for this HAR.
- Agrees on all P0 gaps and their priority ordering.
- Emphasizes that the generator's strength (diverse DPI, language, style) is the biggest asset
  and the primary path to resolution.

### Points of Agreement (All 4 Models)

1. Binary classification (sigmoid+BCE) is the correct head architecture — "regression" is a
   misnomer. Implementation is already correct; only naming/documentation needs updating.
2. Negative contamination from technical textbooks is P0 and the highest risk to training quality.
3. Pseudocode and algorithm-box negatives are a critical gap — 2 of 4 models elevate to P0.
4. Printed-code-in-doc rendering style must represent ≥70-80% of positives to avoid pipeline
   domain mismatch.
5. Performance targets (AUC/F1) must be defined before training run.
6. Gold-standard holdout of real scanned code documents is needed for meaningful evaluation.
7. Overall rating: NEEDS WORK. Not blocked — generator exists and path is clear.

### Points of Disagreement

- **Training split (50/50 vs 10/90)**: 3 models (Gemini 2.5 Pro, Gemini 3 Pro, DeepSeek R1)
  recommend 50/50 training with prevalence-based threshold calibration at inference. Grok-4
  recommends 10/90 to reflect real-world code prevalence. HAR adopts the 50/50 majority
  recommendation, noting the Grok-4 argument as an implementation variant to evaluate post-training.
- **Pseudocode elevation (P1 vs P0)**: Gemini 3 Pro and Grok-4 argue pseudocode negatives should
  be P0. Gemini 2.5 Pro and DeepSeek R1 keep at P1. HAR documents this as a strong P1 (CODE-G06)
  with a note that if initial evaluation shows FPR > 15% on academic documents, CODE-G06 should
  be treated as a P0 retroactive blocker.

### Final Consensus Rating

**NEEDS WORK** — with five P0 items resolvable within 1-2 weeks. The head is not blocked: the
generator exists, the dry-run validates the data pipeline, and the volume gap (~1,387 negatives)
is easily closed. The P0 items are classification, validation, and configuration issues rather
than fundamental data sourcing blockers. Proceeding to a full generator run without addressing
negative contamination (CODE-G01) and style ratio enforcement (CODE-G04) would produce a
training dataset with known quality defects that require expensive retraining.

### Scoring Summary

| Component | Weight | Rationale | Raw Score | Weighted |
| --- | --- | --- | --- | --- |
| Source Pool Adequacy | 35% | 8,613 / 10,000 = 86% volume. Deducted for contamination risk (negatives unvalidated) and architectural framing issue: effective usable score ~70% | 70.0 | 24.5 |
| 14-Dimension Coverage | 25% | Average across 9 assessed dimensions: content_flags (60%), domain (55%), capture_method (40%), color_mode (60%), resolution (90%), layout_type (65%), script_code (20%), document_age (70%), degradation (45%). Mean = 56.1% | 56.0 | 14.0 |
| Wild Condition Coverage | 20% | (0 full + 4 partial × 0.5) / 6 total conditions = 33.3% | 33.3 | 6.7 |
| OOD Design Quality | 20% | Conceptually adequate design (3 sub-sources, 200 images, targets real failure modes). Deducted: no CJK code OOD, no scanned code OOD, pseudocode only partially covered, terminal output labeling policy undefined | 47.0 | 9.4 |
| **Overall** | 100% | — | — | **54.6** |

**Grade**: ⚠️ Needs Work (54.6 / 100 | P0 blockers present; all P0 resolvable ≤2 weeks)

### Top Recommendations (from consensus)

1. Formally reclassify head as binary classification — update `config/siglip2_multitask.yaml`,
   training script, and all HAR documentation. Change metric tracking from MAE to AUC + F1.
   This is a 0.5-day documentation and configuration change.

2. Apply keyword heuristic filter to all 3,613 negative candidates before full training run.
   Filter for code-indicator tokens (`{`, `}`, `def`, `import`, `public static`, `;`, indentation
   patterns). Manually spot-check 100 filtered candidates. Reject and replace contaminated
   negatives with DocLayNet financial/legal pages. Budget: 1-2 days.

3. Enforce ≥70% printed-code-in-doc style ratio in generator configuration before full run.
   Screenshot-dominant positives create pipeline domain mismatch. Add `--printed-ratio 0.70`
   parameter and re-validate dry-run distribution.

4. Source ≥200 real scanned code document pages (printed technical manuals, photocopied code
   listings, physical programming textbooks) as gold-standard validation holdout before evaluation.
   These must not appear in training. Budget: 1-2 days.

5. Define and lock AUC ≥ 0.90, F1 ≥ 0.85 as performance targets in `config/siglip2_multitask.yaml`.
   Set a secondary target for FPR ≤ 10% on academic documents (to validate pseudocode gap is
   not causing unacceptable false positives). If FPR > 15% on academic documents post-training,
   treat CODE-G06 (pseudocode hard negatives) as a retroactive P0.
