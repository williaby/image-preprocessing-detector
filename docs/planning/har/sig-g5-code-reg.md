# Head Adequacy Review: code_reg (SIG-G5-4)

> **Status**: 🔄 Scaffolded — Analysis Pending
> **Version**: 1.0
> **Created**: 2026-02-22
> **Updated**: 2026-02-22
> **HAR Index**: [HAR_MASTER_INDEX.md](../HAR_MASTER_INDEX.md)
> **Batch**: F — Page Attributes
> **Adequacy**: ⏳ TBD

---

## Section 1 — Head Specification

| Field | Value |
| --- | --- |
| Head ID | SIG-G5-4 |
| Model | SigLIP 2 NAFlex |
| Group | G5 — Page Attributes |
| Head Name | code_reg (also written as code_confidence) |
| Task Type | Regression 0-1 (confidence that document contains code) |
| Output Format | Linear output [0-1] |
| Priority | P2 |
| Performance Target | TBD (performance metric not yet specified) |
| Primary L2 Field | `content_flags.has_code` (bool) + `structure.code_language` (enum) |
| Shared-Data Heads | None (dedicated code detection dataset) |
| Training Phase | Phase 5 — Page Attributes |

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

**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better)

**Label Provenance**: tier_0_exact for generated positive examples (code is known ground truth); tier_0_exact for L2-labeled negatives (has_code=False confirmed from source dataset metadata)

**Audit-Derived Defects**: _(analysis required — check docs/audit/audits/ for DocSynth300K and multimodal_textbook has_code field population)_

### Candidate Source Datasets

| Dataset | Total Images | Field Populated | Coverage % | Conf ≥ 0.7 | Audit Grade | Usable |
| --- | --- | --- | --- | --- | --- | --- |
| Generated code images (positive class) | 5,000 (target) | ✅ Generated (self-labeled) | 100% | tier_0_exact | — | 5,000 (dry-run: 5,000 approved) |
| DocSynth300K | _(analysis required)_ | _(analysis required — has_code field from L2)_ | — | — | — | — |
| multimodal_textbook | _(analysis required)_ | _(analysis required — has_code=False from L2)_ | — | — | — | — |
| DocLayNet | _(analysis required)_ | _(analysis required — pages without code regions)_ | — | — | — | — |
| RVL-CDIP enriched | _(analysis required)_ | _(analysis required — code-heavy categories)_ | — | — | — | — |

### Code Detection Generator Details

`scripts/generate_code_detection_dataset.py` exists. Dry-run result: 8,613 records (5,000 positive + 3,613 negative). Full run pending.

Generator configuration:

- 8 programming languages (Python, JavaScript, Java, C++, Go, Rust, TypeScript, SQL)
- Dark and light syntax-highlighting themes
- 4 DPI configs (72, 150, 300, 600 DPI)
- 2 rendering styles: "screenshot" (browser/IDE framing) and "printed-code-in-doc" (embedded in document layout)

### Usable Pool Summary

- **Total usable before enrichment**: 8,613 from dry-run (5,000 positive generated + 3,613 negative sourced from L2 negatives)
- **Training target**: 10,000 images (5,000 positive + 5,000 negative)
- **Gap**: ~1,387 additional negative examples needed (or expand positive pool and rebalance)

### VLM Validation Sampling Tier

_(analysis required — generated positives require no VLM validation (self-labeled); negative examples from L2 may require spot-check validation to confirm has_code=False labels are accurate)_

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| _(analysis required)_ | — | — | — | — |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| KI-G5-4-01 | Performance target not yet specified — no MAE, accuracy, or F1 target defined for code_reg | MEDIUM — evaluation criteria must be defined before training |
| KI-G5-4-02 | Partial code coverage (one snippet in a long document) should produce intermediate score (~0.3–0.5) but generation script currently produces binary positive/negative — no partial coverage training examples | MEDIUM — model may overfit to all-or-nothing labels |
| KI-G5-4-03 | Negative pool from dry-run (3,613 images) is slightly below 5K target — gap of ~1,387 negatives | LOW — addressable by expanding negative source dataset coverage |
| KI-G5-4-04 | Born-digital capture strongly correlates with code presence (code is almost always born-digital) — model may learn capture_method as a shortcut feature rather than visual code structure | MEDIUM — must include born-digital NON-code negatives to break spurious correlation |

### Remediation Path

_(analysis required — enumerate steps: 1) define performance target (F1, accuracy, or MAE), 2) run full generation script, 3) source additional negatives to reach 5K balance, 4) create partial-code examples for intermediate label coverage)_

---

## Section 3 — Training Dataset Targets

| Field | Value |
| --- | --- |
| Target Count | 10,000 images (5,000 positive + 5,000 negative) |
| Assembly Status | 🔄 Script created, dry-run complete (8,613 records). Full run pending. |
| Distribution | ~50% positive (has_code=True, code_confidence ≈ 1.0) / ~50% negative (has_code=False, code_confidence = 0.0) |
| Positive Source | `scripts/generate_code_detection_dataset.py` — 8 languages, dark/light themes, 4 DPI configs, 2 styles |
| Negative Source | L2 multimodal_textbook (has_code=False) + DocLayNet (pages without code regions) + DocSynth300K |
| Real Data Ratio | Positives: 100% synthetic (generated); Negatives: real documents from L2 sources |
| Partial Code Coverage | Not yet implemented — intermediate scores (0.3–0.5) for single-snippet pages not represented |
| Assembly Script | `scripts/generate_code_detection_dataset.py` |

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: _(TBD — computed after assembly)_

| Dimension | L2 Field | Relevance | Target | Current | Score |
| --- | --- | --- | --- | --- | --- |
| content_flags | `content_flags.has_code` | CRITICAL — this IS the label; positive/negative balance and intermediate cases must be well-represented | 50% positive / 50% negative; ≥ 3 partial-code examples | 5K pos / 3.6K neg (dry-run) — gap in partial coverage | TBD |
| domain | `domain.level1` | HIGH — code appears in software documentation, academic papers, textbooks, technical reports | ≥ 5 domains with positive examples (SWE, SCI, EDU, FIN for SQL) | unknown | TBD |
| capture_method | `capture_method.method` | MEDIUM — code is almost always born-digital; must include born-digital negatives to prevent spurious correlation | ≥ 2 methods; born-digital negatives must outnumber camera negatives | unknown | TBD |
| color_mode | `image_properties.color_mode` | MEDIUM — dark vs light theme (both supported by generator); printed code may be grayscale | ≥ 2 modes (color with syntax highlighting + grayscale printed) | Dry-run includes dark/light themes | TBD |
| resolution | `resolution.category` | MEDIUM — code is sometimes from low-DPI screenshots; generator covers 4 DPI tiers | All 4 DPI tiers (72/150/300/600) represented | Generator covers all 4 tiers | TBD |
| domain | `domain.level1` | HIGH — see above | ≥ 5 domains | unknown | TBD |
| layout_type | `structure.layout_type` | MEDIUM — code blocks appear inline vs as full-page code listings; "screenshot" vs "printed-code-in-doc" styles | Both rendering styles represented | Generator covers both styles | TBD |
| document_age | `image_properties.document_age` | LOW — code documentation is overwhelmingly modern | Modern dominant; aged as edge case | unknown | TBD |

---

## Section 5 — Wild Condition Coverage

**Overall Score**: _(TBD — computed after analysis)_

| Wild Condition | L2 Field Evidence | Status | Gap |
| --- | --- | --- | --- |
| IDE screenshots (VSCode/JetBrains with file tree panels, line numbers, syntax highlighting) | `content_flags.has_code` = true | ⚠️ | OOD-Code targets this; generator produces clean code blocks — IDE chrome (file tree, status bar) outside generation-script distribution |
| Jupyter notebooks (code cells + markdown + output cells mixed) | `content_flags.has_code` = true, `structure.layout_type` = mixed | ⚠️ | OOD-Code targets this; partial code coverage challenge — code cell among many non-code cells |
| Terminal output (monospace text without keywords) | `content_flags.has_code` = true | ⏳ | OOD-Code targets this; terminal output lacks `def`/`class`/`import` keywords that generator relies on |
| Pseudocode and algorithm boxes in papers | `content_flags.has_code` = true | ⏳ | LaTeX-rendered algorithm environments look like code but use different syntax than generated examples |
| Configuration files (YAML, TOML, JSON) displayed in documents | `content_flags.has_code` = true | ⏳ | Not in 8 supported languages — config formats are structurally similar to code but use different syntax |
| Born-digital non-code documents with monospace font sections | `content_flags.has_code` = false | ⚠️ | Risk of false positive: monospace font ≠ code; negatives must include monospace-heavy non-code documents |

---

## Section 6 — OOD Design

**Primary OOD Category**: OOD-Code (Phase 8, P2, 200 total images)

### OOD Sub-Sources

| Sub-Source | Images | Source | Labels Required | Evaluation Stage | Notes |
| --- | --- | --- | --- | --- | --- |
| IDE screenshots (VSCode/JetBrains) | 75 | Screenshots of IDEs displaying code with file tree, tabs, status bar | has_code=true, code_confidence=1.0, warping_type=none, capture_method=BORN_DIGITAL | siglip2 | IDE chrome panels (file tree, gutter, line numbers, minimap) not present in generator output. Tests robustness to framing elements outside code body. |
| Mixed prose + code (arXiv / Jupyter notebooks) | 75 | arXiv papers with inline code snippets; Jupyter .ipynb rendered as images | has_code=true, code_confidence ≈ 0.3–0.7 (partial), layout_type=mixed | siglip2 | Intermediate code_confidence region (~0.3–0.5). Code occupies minority of page. Tests whether head correctly assigns partial confidence rather than binary output. Must SHA256+pHash dedup against any arXiv pages in negative training set. |
| Terminal output pages | 50 | Terminal session screenshots or printed CLI output | has_code=false (ambiguous — no keywords), or has_code=true (command lines are executable) | siglip2 | Deliberate ambiguity: monospace text, command-line syntax, but no traditional code structure. Label as has_code=true with code_confidence ≈ 0.4–0.6 to acknowledge ambiguity. Tests edge-of-distribution behavior. |

### OOD Acquisition Status

**Status**: ⏳ Not started (Phase 8, P2)

### OOD Leakage Risk

**Level**: LOW

Generation script uses fresh PIL+Pygments synthesis — no training data from existing datasets. OOD targets genuinely novel code-containing formats (IDE chrome, Jupyter mixed, terminal output) that are architecturally distinct from the generator's clean code blocks and document-embedded code styles. No dedup required against training manifests since OOD sources are independently acquired. The only leakage risk is if arXiv papers used in OOD-Code overlap with arXiv papers in other training datasets — SHA256+pHash dedup required for arXiv subset of OOD sub-source 2.

---

## Section 7 — Cross-Head Consistency

### Head Interactions

| Related Head | Relationship | Consistency Requirement |
| --- | --- | --- |
| SIG-G5-1 (capture_cls) | Born-digital capture strongly correlates with code presence — must prevent spurious feature learning | Negatives in code_reg training MUST include a large proportion of born-digital non-code documents (DocLayNet is born-digital; DocSynth300K is born-digital). If all born-digital images are code (positive) and all scanned images are non-code (negative), the model learns capture_method rather than visual code content. Born-digital negatives must be explicitly verified in training manifest. |
| SIG-G4 heads (handwriting_reg) | No shared training data | Code detection and handwriting detection are orthogonally distinct content types. No consistency risk. |
| SIG-G3-2 (skew_reg) | No shared training data | Generated code images should be validated to have zero skew (generated at skew=0 by default) to avoid confounding skew head evaluation. |

### Split Leakage Risk

**Level**: LOW

Dedicated generation pipeline with independent positive sources (PIL+Pygments). Negative examples from DocSynth300K/multimodal_textbook/DocLayNet may overlap with other training datasets — global split registry must confirm negatives used here are not in other datasets' test splits. Risk is LOW because code_reg uses these images only for has_code=False labels (a different semantic use than other datasets' primary labels), but leakage into OOD or test sets of other heads must still be prevented.

### Label Convention

`code_confidence = 0.0` means definitively NO code present on the page (confirmed from L2 has_code=False). `code_confidence = 1.0` means clearly contains code (generated examples or pages that are entirely code). Partial code (one snippet in a long document) → intermediate score ~0.3–0.5. This intermediate label range is not yet represented in training data — it is the most important gap to fill before the model generalizes beyond binary predictions. The L2 field `content_flags.has_code` is boolean — the continuous training signal [0,1] must be derived from additional signals (code line count, code area fraction) when intermediate scores are needed.

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Audit Defect | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- | --- |
| G5-4-G01 | — | Performance target not defined — no MAE, F1, or accuracy threshold specified for this head | Head was defined as TBD in SigLIP 2 requirements document | Define performance target: propose F1 ≥ 0.85 for binary has_code detection; define MAE target for intermediate confidence scores; confirm with project lead | 0.5 days (decision) |
| G5-4-G02 | — | Negative pool gap: 3,613 negatives (dry-run) vs 5,000 target — 1,387 additional negatives needed | Insufficient negative source dataset coverage identified so far | Audit remaining candidate datasets (PubTabNet, Tobacco800, RVL-CDIP) for has_code=False labels; expand negative coverage | 0.5 days |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| G5-4-G03 | Partial code coverage training examples not in dataset — model trained only on binary labels, may fail on intermediate cases | Generator produces binary positive/negative; no partial-code page generation implemented | Implement partial-code page generator: embed 1–2 code snippets into full-page document layouts; target 500–1,000 intermediate examples with code_confidence 0.3–0.5 | 1 day |
| G5-4-G04 | Born-digital non-code negatives not verified to be sufficient in training manifest — spurious correlation risk with capture_cls | Negative sourcing not stratified by capture_method | Stratify negative pool by capture_method: confirm ≥ 60% of negatives are born-digital origin; report in manifest statistics | 0.5 days |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| G5-4-G05 | Configuration file formats (YAML, TOML, JSON) not covered by 8-language generator — may need separate handling | Add YAML/TOML/JSON as optional 9th/10th/11th generator languages; or document as known limitation and label as has_code=true with lower confidence |
| G5-4-G06 | Terminal output ambiguity not resolved — should CLI output be has_code=true or false? | Define policy: recommend has_code=true for interactive shell output (commands are executable code); document in L2 schema |

---

## Section 9 — Multi-Model Consensus

**Status**: ⏳ Pending execution

**Adequacy Rating (pre-consensus)**: ⏳ TBD (analysis required)

**Analyst Summary**: _(To be written after Sections 2–8 analysis is complete)_

**Consensus Prompt**: _(To be written after Section 8 gap registry is complete)_

**Models**: google/gemini-2.5-pro, google/gemini-3-pro-preview, openai/gpt-5.2,
deepseek/deepseek-r1-0528, x-ai/grok-4 (all neutral)

**Consensus Summary**: _(Pending)_

**Final Rating**: _(Pending)_

**Top Recommendations**: _(Pending)_

### Scoring Summary

| Component | Weight | Score | Weighted |
| --- | --- | --- | --- |
| Source Pool Adequacy | 35% | TBD | TBD |
| 14-Dimension Coverage | 25% | TBD | TBD |
| Wild Condition Coverage | 20% | TBD | TBD |
| OOD Design Quality | 20% | TBD | TBD |
| **Overall** | 100% | — | TBD |

**Grade**: ⏳ TBD
