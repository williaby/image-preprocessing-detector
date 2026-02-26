---
l4_category: training-dataset
l4_dataset: code-detection
l4_workstream: WS3
l4_source_datasets:
  - multimodal-textbook
  - doclaynet
  - github-code-snippets
l4_generation_script: scripts/generate_code_detection_dataset.py
l4_image_count: 10000
l4_status: planned
---

# Code Detection

> **P0 ARCHITECTURAL ISSUE — CODE-G05**
>
> The training head is currently named `code_reg` in `SIGLIP2_MULTITASK_REQUIREMENTS.md`
> and `modal/train_siglip2_multitask.py`. This is an architectural misnomer.
>
> **The training signal is boolean** (`has_code` = True/False). This must be:
>
> - Binary classification (sigmoid activation + BCE loss)
> - Renamed to `code_cls` everywhere
>
> **Files requiring rename before training**:
>
> - `docs/planning/SIGLIP2_MULTITASK_REQUIREMENTS.md`
> - `modal/train_siglip2_multitask.py`
> - The head registry / model architecture definition
>
> **Status**: 8,613/10,000 dry-run confirmed. Full run BLOCKED pending this rename.

---

> **Quick Stats**: 10,000 images (target) | Binary classification — does page contain code? |
> `has_code` bool label
>
> **Status**: 8,613/10,000 dry-run confirmed. Full generation run blocked pending CODE-G05 (architectural rename) resolution. | **HAR Score**: 55/100 | **P0 Gaps**: 5

---

## Section 1 — Identity

| Field | Value |
|-------|-------|
| **Dataset Name** | `code-detection` |
| **Head(s) Fed** | SIG-G5-4 `code_reg` (rename to `code_cls` — see architectural note below) |
| **Model(s)** | SigLIP 2 NAFlex |
| **Task Type** | Binary Classification — sigmoid output, BCE loss (see architectural note) |
| **Primary L2 Field(s)** | `content_flags.has_code` (bool) + `structure.code_language` (str, optional) |
| **Training Phase** | Phase 5 — Page Attributes |
| **Target Size** | 10,000 images |
| **Image Size** | 384px (standard SigLIP 2 input) |
| **Storage Location** | `E:\image_detection\03_training_datasets\code-detection\` |
| **GCS Path** | `gs://image_detection_b/code_detection_training/` |
| **Assembly Script** | `scripts/generate_code_detection_dataset.py` |
| **HAR File(s)** | [har/sig-g5-code-reg.md](../../planning/har/sig-g5-code-reg.md) |
| **DDR File** | No DDR file — code-detection is entirely generated; no source dataset diversity report |

### Architectural Note: Regression vs. Binary Classification (CRITICAL — Unanimous Consensus)

The head is named `code_reg` in
[SIGLIP2_MULTITASK_REQUIREMENTS.md](../../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md) and
described as "Regression 0-1" in the architecture diagram. This framing is a **misnomer** and
creates metric confusion.

The training signal is `content_flags.has_code`, a boolean field. No ground-truth continuous
intermediate values exist at dataset assembly time. The correct formulation is therefore Binary
Cross-Entropy (BCE) loss with sigmoid activation — binary classification, not regression. A
4-model consensus (Gemini 2.5 Pro, Gemini 3 Pro, DeepSeek R1, Grok-4) is **unanimous** on this
point. The 0-1 output is best described as "probability of code presence" — not a regression
scalar.

**Required action (CODE-G05)**: Rename `code_reg` to `code_cls` in
`config/siglip2_multitask.yaml`, the training script, and all planning documents. Change metric
tracking from MAE to AUC ≥ 0.90 and F1 ≥ 0.85 (MAE is meaningless for a binary label).

**Future path to true regression**: If `code_pixel_ratio` (fraction of page area that is code)
is later derived from layout detection, the head can be converted to regression with SmoothL1
loss. Until such labels exist, binary classification framing is mandatory.

### 8 Supported Code Languages

| Language | Notes |
|----------|-------|
| Python | Dominant in ML/data science documents |
| JavaScript | Web and frontend documents |
| TypeScript | Web and typed JavaScript documents |
| Java | Enterprise documentation |
| C++ | Systems and embedded documentation |
| Go | Infrastructure and tooling documentation |
| Rust | Systems programming documentation |
| SQL | Database and analytics documentation |

### Downstream Routing Rule

From `SIGLIP2_MULTITASK_REQUIREMENTS.md`: `code_confidence > 0.5` → `enrich_code: true`. This
threshold must be calibrated on a real-world prevalence validation set before deployment; a
threshold of 0.6–0.7 is likely more appropriate in production (see Section 11).

---

## Section 2 — Status

| Metric | Value |
|--------|-------|
| **Assembly Status** | 🔄 In Progress — dry-run complete; full run blocked on P0 gaps |
| **Current Count** | 8,613 / 10,000 assembled (dry-run only; not written to disk) |
| **HAR Adequacy Score** | 55/100 — ⚠️ Needs Work |
| **P0 Gap Count** | 5 |
| **Primary Blockers** | (1) Head incorrectly typed as regression in requirements (CODE-G05); (2) negative contamination from multimodal_textbook unvalidated (CODE-G01); (3) full generation run not executed — dry-run only (CODE-G02); (4) printed-code-in-doc style ratio unenforced (CODE-G04); (5) performance targets not formally defined as classification metrics (CODE-G03) |
| **Estimated Unblock Effort** | 3–4 days total for all 5 P0 gaps |
| **Last HAR Updated** | 2026-02-23 |

---

## Section 3 — Source Pool Analysis

> *Derived from HAR § Section 2. Identifies which source datasets contribute to this assembled
> training dataset and how much of each is usable given the required L2 field coverage.*

**Required L2 Field**: `content_flags.has_code` (bool) — True for positive class, False for
negative class. Optional supplementary field: `structure.code_language` (str enum).

**Confidence Threshold**: tier_0_exact for generated positives (code is ground truth by
construction); tier_1_annotation for L2-labeled negatives (has_code=False from source metadata),
subject to contamination validation.

**Label Provenance**: tier_0_exact for generated positive examples; tier_1_annotation for
L2-confirmed negatives from multimodal_textbook and DocLayNet (contamination validation
required before negatives can be trusted at this tier — see CODE-G01).

### Candidate Source Datasets

| Source Dataset | Total Images | Field Populated | Coverage % | Conf ≥ 0.7 | Usable |
|----------------|-------------|-----------------|------------|-------------|--------|
| Generated code images (positive class) | 5,000 (dry-run approved) | Self-labeled — generated ground truth | 100% | tier_0_exact | ⚠️ 5,000 (full run pending; CODE-G02) |
| multimodal_textbook (`has_code=False` negative) | ~3,613 from dry-run | has_code=False from L2 metadata | ~72% of dry-run negatives | tier_1_annotation | ⚠️ 3,613 (contamination unvalidated — CODE-G01) |
| DocLayNet (financial/legal, negative supplement) | Available for downsampling | Pages without code regions labeled | Partial | tier_1_annotation | ⚠️ Available — gap closure (lower contamination risk than textbook) |
| DocSynth300K (candidate negative) | Available | L2 metadata analysis required | Unknown | Unknown | ❌ Requires audit before use |

### Contamination Risk Analysis

The negative pool from `multimodal_textbook` carries **medium-high contamination risk**.
Technical textbooks routinely contain inline code snippets (`print("hello")` in prose),
command-line examples, configuration excerpts, and pseudocode in algorithm descriptions. A
page labeled `has_code=False` at the page level may still contain inline code visible to a
vision model. Training on these as `code_confidence=0.0` poisons the negative examples.

Required mitigation: keyword-based heuristic filter applied to OCR text before inclusion
(tokens: `{`, `}`, `;`, `def`, `public static`, `import`, indentation patterns), followed by
a 100-sample manual spot-check. DocLayNet financial/legal pages carry lower contamination risk.

### Pool Summary

| Metric | Value |
|--------|-------|
| **Total usable (current — dry-run)** | 8,613 images |
| **Total usable (post-P0)** | ~10,000 images (gap of ~1,387 closed via DocLayNet) |
| **Training target** | 10,000 images |
| **Pool surplus/deficit** | -1,387 (-14% of target) — negatives only |
| **Real vs. synthetic ratio** | Positives: 100% synthetic (generated); Negatives: ~100% real document pages from L2 sources |

---

## Section 4 — Label Schema

**Primary L2 Field**: `content_flags.has_code`
**Type**: bool
**Range / Enum**: True (page contains code) / False (no code on page)
**Provenance Tier**: tier_0_exact (generated positives); tier_1_annotation (L2 negatives,
post-contamination validation)
**Derivation Formula**: Generated positives — code present by construction. Negatives — L2
`has_code=False` field from source dataset metadata, validated by keyword heuristic filter.

### Training Manifest Record Schema

```json
{
  "image_path": "code-detection/images/{filename}.jpg",
  "source_dataset": "generated_code|multimodal_textbook|doclaynet",
  "split": "train",
  "split_type": "train",
  "label_provenance": "tier_0_exact",
  "label_confidence": 1.0,
  "has_code": true,
  "code_confidence": 1.0,
  "code_pixel_ratio": 0.85,
  "code_languages": ["python"],
  "rendering_style": "printed-code-in-doc",
  "capture_method": "born_digital"
}
```

**Field definitions**:

| Field | Type | Values | Notes |
|-------|------|--------|-------|
| `has_code` | bool | True / False | Primary training label |
| `code_confidence` | float | 0.0 or 1.0 (training); 0.0–1.0 (OOD evaluation) | 1.0 = clear code; 0.0 = no code; intermediate values reserved for mixed-page OOD (CODE-G09) |
| `code_pixel_ratio` | float | 0.0–1.0 | Fraction of page area occupied by code; derived from generator layout for positives; 0.0 for negatives |
| `code_languages` | list[str] | ["python", "javascript", "typescript", "java", "cpp", "go", "rust", "sql"] | Languages present in the image; empty list for negatives |
| `rendering_style` | str | "printed-code-in-doc" / "screenshot" | Distinguishes document-embedded code from IDE/browser screenshot style |
| `label_provenance` | str | "tier_0_exact" / "tier_1_annotation" | Provenance tier of the has_code label |

**Inference threshold note**: The downstream routing rule uses `code_confidence > 0.5` →
`enrich_code: true`. With 50/50 training data, the raw sigmoid output is uncalibrated for a
5–10% real-world code-document prior. A deployment threshold of 0.6–0.7 will likely be more
appropriate and should be calibrated on a held-out validation set reflecting real-world
prevalence before deployment.

### Label Statistics (target — post-assembly)

| Metric | Value |
|--------|-------|
| **Positive class** | 5,000 images (50% of total) |
| **Negative class** | 5,000 images (50% of total) |
| **Target mean confidence** | 0.5 (binary, balanced) |
| **Language distribution** | ≤625 per language (8 languages, balanced) |
| **Style distribution** | ≥70% printed-code-in-doc / ≤30% screenshot (target; currently unenforced) |

---

## Section 5 — Composition & Splits

### Target Distribution

| Class | Label | Target % | Target Count | Source |
|-------|-------|----------|-------------|--------|
| Positive — GitHub synthetic code | `has_code=True`, code_confidence=1.0 | 40% | 4,000 | `generate_code_detection_dataset.py` |
| Positive — textbook page with code | `has_code=True`, code_confidence=1.0 | 10% | 1,000 | multimodal_textbook (L2 has_code=True) |
| Negative — DocLayNet prose-only | `has_code=False`, code_confidence=0.0 | 30% | 3,000 | DocLayNet financial/legal pages |
| Negative — textbook page without code | `has_code=False`, code_confidence=0.0 | 20% | 2,000 | multimodal_textbook (L2 has_code=False, contamination-validated) |
| **Total** | — | **100%** | **10,000** | — |

**Split rationale**: The 50/50 positive/negative training split is the majority recommendation
from 4-model consensus (Gemini 2.5 Pro, Gemini 3 Pro, DeepSeek R1). Training on real-world
prevalence (~5–10% code documents) biases the model toward majority-class prediction. The 50/50
split forces the model to learn discriminative features from both classes. Grok-4 recommended a
10/90 split to reflect real-world prevalence — this is a minority position. The majority view
is that threshold calibration at inference is the correct path for handling low-prevalence
deployment, not skewing the training distribution.

**Rendering style distribution for positives**:

| Style | Target % | Target Count | Notes |
|-------|----------|-------------|-------|
| "printed-code-in-doc" (code embedded in document layout) | ≥70% | ≥3,500 | Matches document scanner pipeline input distribution |
| "screenshot" (IDE/browser dark-mode framing) | ≤30% | ≤1,500 | Valid positive but architecturally OOD for scanner pipeline |

**Language distribution for positives**:

| Language | Target Count | Cap |
|----------|-------------|-----|
| Python | ≤625 | Per-language cap enforced in generator |
| JavaScript | ≤625 | " |
| TypeScript | ≤625 | " |
| Java | ≤625 | " |
| C++ | ≤625 | " |
| Go | ≤625 | " |
| Rust | ≤625 | " |
| SQL | ≤625 | " |

### Split Strategy

| Split | Images | Percentage |
|-------|-------:|------------|
| Train | 7,000 | 70% |
| Val | 1,500 | 15% |
| Test | 1,500 | 15% |
| **Total** | **10,000** | **100%** |

**Split Method**: Stratified by class (positive/negative) and source dataset to maintain 50/50
ratio in all splits.
**Random Seed**: 42
**Leakage Prevention**: Generated positives are synthetic — no overlap with source datasets.
Negative images from DocLayNet/multimodal_textbook must not appear in other datasets' test splits
(global split registry via SHA256). arXiv pages used as negatives must be SHA256+pHash deduped
against OOD-Code 8b (arXiv mixed prose+code) to prevent training leakage into OOD evaluation.

---

## Section 6 — 14-Dimension Diversity

> **Full DDR Audit**: No DDR file — code-detection is an assembled/generated dataset with no
> source-dataset diversity report. Diversity analysis is conducted at assembly time via the
> generator configuration.
>
> **HAR Section 4 Reference**: [sig-g5-code-reg.md § Section 4](../../planning/har/sig-g5-code-reg.md)
>
> **Overall Diversity Score**: 51/100 (pre-assembly estimate from HAR)

| Dimension | L2 Field | Relevance | Target | Current | Status |
|-----------|----------|-----------|--------|---------|--------|
| content_flags | `content_flags.has_code` | CRITICAL | 50% positive / 50% negative; ≥70% printed-code-in-doc style | 5K positive / 3.6K negative (dry-run); style ratio unenforced | ⚠️ Partial |
| color_mode | `image_properties.color_mode` | HIGH | ≥2 modes: color (dark-mode screenshots) + grayscale/black-on-white (printed code) | Generator covers dark/light themes; no binarized code examples | ⚠️ Partial |
| domain | `domain.level1` | HIGH | ≥3 domains with positives (TEC, SCI, EDU); negatives must span ≥3 domains (FIN, LEG, ADM) | Generated positives: domain unknown; negatives: DocLayNet spans FIN/TEC/SCI | ⚠️ Partial |
| layout_type | `structure.layout_type` | MEDIUM | ≥2 layout types: full-page code listings and inline-snippet-in-prose | Generator produces both styles | ⚠️ Partial |
| degradation | `quality.degradations` | MEDIUM | ≥2 degradation levels in printed-code positives | Generator produces clean DPI tiers; no scan-degraded code examples | ❌ Missing |
| capture_method | `capture_method.method` | MEDIUM | ≥2 methods; born-digital negatives must be abundant to break spurious correlation | Generated positives: 100% born-digital; negatives: DocLayNet + textbook — almost no camera/scanner negatives | ⚠️ Partial |
| resolution | `resolution.category` | MEDIUM | All 4 DPI tiers (72/150/300/600) represented | Generator covers all 4 DPI tiers | ✅ Covered |
| document_age | `image_properties.document_age` | LOW | Modern dominant | Modern only | ✅ Adequate |
| script_code | `language.script_code` | MEDIUM | ≥2 script families (Latin + CJK) | All 8 languages produce Latin/ASCII code only; no CJK code comments | ❌ Missing |

### Key Diversity Gaps

- **Capture method correlation risk**: Code is almost exclusively born-digital (IDEs, editors,
  PDF renders). If all positive examples are born-digital AND negatives are also born-digital
  (DocLayNet), the model may learn to associate `capture_method=born_digital` with code presence
  rather than visual code structure. Mitigation: born-digital non-code negatives must exceed
  born-digital positives in count within the negative pool.
- **CJK code comments absent**: All 8 supported languages produce Latin/ASCII output only.
  Real-world engineering documents — especially East Asian software documentation — contain
  Python files with Chinese docstrings, SQL queries with CJK column names, and JavaScript
  with Korean variable names. These are entirely missing from the positive pool (see CODE-G07).
- **Scan-degraded code absent**: Printed code in technical books (150 DPI, scanner artifacts,
  ink variation) looks different from born-digital code renders. No scan-degraded code positives
  exist in the training pool (see CODE-G11).
- **Pseudocode absent from negative pool**: LaTeX `\algorithm` environments, numbered pseudo-steps,
  and indented logic blocks resemble code visually but are not executable. These hard negatives
  are the most significant false-positive risk (see CODE-G06).

---

## Section 7 — Wild Condition Coverage

> **HAR Section 5 Reference**: [sig-g5-code-reg.md § Section 5](../../planning/har/sig-g5-code-reg.md)
>
> **Overall Wild Condition Score**: 33% (2 partial + 0 full out of 6 conditions assessed)

| Wild Condition | L2 Evidence | Status | Gap |
|----------------|-------------|--------|-----|
| Pseudocode and algorithm boxes in academic papers (LaTeX `\algorithm` environments, numbered steps, indented logic without valid syntax) | `content_flags.has_code` disputed — pseudocode is not executable code | ⚠️ Partial | Generator produces only syntactically valid code. OOD-Code 8b (arXiv papers, 60 images) partially covers this. Dedicated pseudocode hard negatives are entirely absent from training. False-positive risk is HIGH — 2 of 4 consensus models elevate to P0 (see CODE-G06). |
| Tabular data / terminal output resembling code (log files, CSV previews, monospace-formatted terminal sessions) | `content_flags.has_code` = False (monospace ≠ code) | ⚠️ Partial | No explicit monospace-heavy non-code training examples. OOD-Code 8c (terminal output, 40 images) covers evaluation but not training. |
| Mixed pages — code block with prose explanation (technical manuals, Jupyter notebooks, arXiv papers) | `content_flags.has_code` = True; code occupies minority of page | ⚠️ Partial | Generator produces purely positive (full-page code) or purely negative (no code). Mixed-page examples with intermediate confidence (0.3–0.7) are absent. Model will behave as near-binary classifier on partial-code pages (see CODE-G09). |
| CJK code comments — Python/SQL with Chinese/Japanese/Korean variable names and comments | `content_flags.has_code` = True; `structure.code_language` = Python/SQL | ❌ Missing | Generator uses Latin/ASCII only for all 8 languages. No CJK code examples in training or OOD design (see CODE-G07). |
| Low-resolution scanned code listings (code printed in technical books, scan-degraded at 150 DPI) | `content_flags.has_code` = True; capture via scanner | ❌ Missing | Generated code is born-digital. No scan-degraded code positives exist. OOD-Code 8a targets born-digital IDE screenshots, not scanned prints (see CODE-G11). |
| IDE screenshots with full UI chrome (file tree, status bar, tabs, line numbers, minimap) | `content_flags.has_code` = True | ⚠️ Partial | Generator produces clean code blocks without IDE framing elements. OOD-Code 8a (100 images of IDE/GitHub screenshots) tests this but training has no IDE chrome examples. |

---

## Section 8 — OOD Cross-Reference

> **Full OOD Catalog**: [OOD_DATASET_CATALOG.md](../OOD_DATASET_CATALOG.md)
>
> **HAR Section 6 Reference**: [sig-g5-code-reg.md § Section 6](../../planning/har/sig-g5-code-reg.md)

| Field | Value |
|-------|-------|
| **Primary OOD Category** | OOD-Code (Phase 8, P2) |
| **OOD Target Images (this head)** | 200 images |
| **OOD Acquisition Status** | Not started |

| OOD Sub-source | Images | Relevance | Stress Scenario |
|----------------|-------:|-----------|-----------------|
| 8a. Source code screenshots — IDE/GitHub | 100 | Direct | IDE chrome (file tree, line numbers, gutter, tabs, minimap) is outside generator training distribution. Tests robustness to framing elements surrounding code body. 5+ programming languages. Labels: `code_confidence=1.0`, human-verified. Must SHA256+pHash dedup against training images. |
| 8b. Mixed prose + code — arXiv / Jupyter notebooks | 60 | Direct | Primary test of intermediate confidence region. Code occupies minority of page (arXiv appendices, Jupyter .ipynb exports). Labels: `code_confidence` ≈ 0.3–0.7 (proportional to code area fraction, human-labeled). SHA256+pHash dedup required against any arXiv pages in negative training set. |
| 8c. Terminal / console output | 40 | Direct | Deliberate ambiguity: monospace text, command-like syntax, but no function/class/import structure. Labels: `code_confidence` = 0.5–0.7 (moderate — terminal commands are executable but context-free). Tests boundary behavior on code-adjacent content. |

### OOD Coverage Gaps

| Gap | Risk | Proposed Remediation |
|-----|------|---------------------|
| CJK code comments absent from OOD design | MEDIUM — no evaluation of cross-script code detection | Add OOD-Code 8d: Python/SQL with Chinese/Japanese comments (20 images, generated) |
| Scanned/printed code absent from OOD design | MEDIUM — scanner input distribution not evaluated for code detection | Add OOD-Code 8e: scanned technical book pages containing code listings (20 images, internal scan) |
| Pseudocode only partially covered in OOD | HIGH — hard negative gap causing false positives | OOD-Code 8b partially covers this via arXiv — add dedicated pseudocode-only OOD subset (20 images of algorithm papers) |

**OOD Leakage Risk**: LOW. Generation script uses PIL+Pygments synthesis — no training data
from existing datasets. OOD targets (IDE screenshots, Jupyter notebooks, terminal output) are
architecturally distinct from the generator's clean code blocks and document-embedded styles.
The only leakage risk is arXiv pages in OOD-Code 8b overlapping with arXiv pages used as
negatives in training. SHA256+pHash dedup required for arXiv subset only.

---

## Section 9 — Assembly Pipeline

**Status**: 🔄 Ready to run (blocked on P0 gap resolution — see Section 10 before executing)

The code-detection dataset is assembled entirely by the generator script
`scripts/generate_code_detection_dataset.py`, which uses PIL and Pygments to render synthetic
code images. Negatives are drawn from L2 metadata sources (multimodal_textbook and DocLayNet)
via the L2 field `content_flags.has_code=False`. Unlike other multi-task datasets, this
dataset does not use `scripts/prepare_multitask_datasets.py` — the generator script is the
primary assembly entry point.

### Assembly Commands

```bash
# Step 1: Validate negative pool (required before full run — addresses CODE-G01)
# Apply keyword heuristic filter to multimodal_textbook negative candidates.
# Filter for: { } ; def import public_static indentation patterns in OCR text.
# Manually spot-check 100 filtered candidates. Reject contaminated images.
# (No script yet — manual process or extend generator with --validate-negatives flag)

# Step 2: Dry-run (completed, 8,613 records — validates pipeline without writing to disk)
uv run python scripts/generate_code_detection_dataset.py --dry-run

# Step 3: Full generation (not yet run — resolve P0 gaps first)
uv run python scripts/generate_code_detection_dataset.py \
  --output-dir /mnt/e/image_detection/03_training_datasets/code-detection/

# Optional: enforce style ratio and language caps (add these flags when available)
#   --printed-ratio 0.70    (≥70% printed-code-in-doc style — CODE-G04)
#   --max-per-language 625  (per-language cap — CODE-G08)

# Step 4: Upload to GCS (after full run)
gsutil -m cp -r /mnt/e/image_detection/03_training_datasets/code-detection/ \
  gs://image_detection_b/code_detection_training/
```

### Dependencies

| Dependency | Status | Required For |
|------------|--------|-------------|
| `scripts/generate_code_detection_dataset.py` | ✅ Exists; dry-run complete | Positive class generation and manifest output |
| L2 multimodal_textbook metadata (`multimodal_textbook_metadata.json`) | ✅ Exists | Negative class: has_code=False records |
| L2 DocLayNet metadata | ✅ Exists | Negative class supplement (financial/legal pages) |
| Keyword heuristic filter for negative contamination validation | ❌ Not yet implemented | CODE-G01 remediation before full run |
| `--printed-ratio` generator flag | ❌ Not yet implemented | CODE-G04 remediation |
| DocSynth300K L2 metadata audit | ❌ Not yet done | Candidate additional negatives (optional) |

### Generated Outputs

| File | Description |
|------|-------------|
| `train_manifest.json` | Flat JSON list of 7,000 training records |
| `val_manifest.json` | Flat JSON list of 1,500 validation records |
| `test_manifest.json` | Flat JSON list of 1,500 test records |
| `code-detection/images/` | Generated code images (printed-code-in-doc and screenshot styles) |

**Manifest contract** (per project memory): flat JSON list (NOT `{"samples": [...]}`);
`image_path` relative to `/data/` (Modal Volume mount); `split_type` field required.

---

## Section 10 — Gap Registry

> **Source**: [sig-g5-code-reg.md § Section 8](../../planning/har/sig-g5-code-reg.md)
>
> **HAR Adequacy Score**: 55/100 — ⚠️ Needs Work

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Description | Root Cause | Remediation | Effort |
|--------|-------------|------------|-------------|--------|
| CODE-G01 | Negative class contamination unvalidated — 3,613 negatives from multimodal_textbook may contain inline code snippets labeled has_code=False at page level | Page-level L2 label does not guarantee visual code-free content for a vision model | Apply keyword heuristic filter (`{`, `}`, `;`, `def`, `public static`, `import`, indentation patterns) to OCR text of all negative candidates; manually spot-check 100 images from high-risk candidates; reject contaminated images and replace with DocLayNet financial/legal pages | 1–2 days |
| CODE-G02 | Full generator run not yet executed — positive class exists only as dry-run approval | Dry-run was completed for planning; full execution requires finalizing generator config | Review generator config; enforce ≥70% printed-code-in-doc ratio, ≤625 per language, and consistent DPI distribution; execute full run of `scripts/generate_code_detection_dataset.py` | 0.5 days |
| CODE-G03 | Performance targets not formally defined as classification metrics — no AUC, F1, or threshold specified for this head in `config/siglip2_multitask.yaml` | Head was marked TBD in SIGLIP2_MULTITASK_REQUIREMENTS.md; original target was MAE (meaningless for binary label) | Define and document performance targets: AUC ≥ 0.90, F1 ≥ 0.85 on held-out code-heavy documents; add to `config/siglip2_multitask.yaml` and HAR; source ≥200 real scanned code documents as gold-standard validation holdout | 0.5 days (decision + documentation) |
| CODE-G04 | Screenshot vs. printed-code-in-doc style ratio not enforced — generator may produce majority screenshot-style images which are OOD for document scanner pipeline | Generator was designed with two styles but no ratio constraint was implemented | Add `--printed-ratio 0.70` parameter to generator or enforce 70/30 ratio in config; re-run dry-run to confirm ratio before full execution | 0.5 days |
| CODE-G05 | Head classified as "regression" in planning documents but uses sigmoid+BCE (binary classification) — causes metric confusion (MAE is meaningless; AUC/F1 are correct metrics) | Naming convention inherited from other G5 heads (`shadow_reg`, `warping_reg`) that ARE true regressions | Update `config/siglip2_multitask.yaml`, SIGLIP2_MULTITASK_REQUIREMENTS.md, and HAR to reflect binary classification framing; rename `code_reg` to `code_cls`; change loss function documentation to BCE; update metric tracking to AUC + F1 | 0.5 days (documentation and configuration) |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Remediation | Effort |
|--------|-------------|-------------|--------|
| CODE-G06 | Pseudocode and algorithm-box negatives absent — LaTeX `\algorithm` environments, numbered pseudo-steps, and indented logic blocks visually resemble code but are not executable; false positive risk is HIGH on academic papers. **Note**: Gemini 3 Pro and Grok-4 argue this should be elevated to P0 — if initial evaluation shows FPR > 15% on academic documents, treat as a retroactive P0. | Source 300–500 arXiv paper pages containing algorithm boxes; label as has_code=False (pseudocode is not code); add to negative pool as hard negatives | 1 day |
| CODE-G07 | CJK code comments absent from positive pool — Python/SQL/JavaScript with Chinese/Japanese/Korean variable names, comments, and string literals are entirely unrepresented | Extend generator to add CJK-comment variants: 5% of generated positives should include code with CJK comments (Chinese Python docstrings, Japanese SQL table names, Korean JavaScript variable names) | 1–2 days |
| CODE-G08 | Language distribution may be Python-heavy — generator defaults may produce more Python examples than the 625-per-language cap target | Audit dry-run language distribution; enforce strict ≤625 cap per language in generator; prioritize under-represented languages (Rust, TypeScript, Go) | 0.25 days |
| CODE-G09 | Mixed-page training examples absent — pages containing both code and prose are the most common real-world form, but training data is binary (all-code or all-prose) | Implement partial-code page generator: embed 1–3 code snippets into multi-paragraph document layout; target 500–1,000 examples with code occupying 20–50% of page; label code_confidence ≈ 0.4–0.6 using code pixel area fraction | 1–2 days |
| CODE-G10 | Gold-standard validation holdout not sourced — all validation data is synthetic or L2-labeled; real-world accuracy is unmeasurable without human-verified physical documents | Source ≥200 real scanned code document pages (technical manuals, programming textbooks, printed code listings) with human verification; keep separate from training; use as primary evaluation signal | 1–2 days |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
|--------|-------------|-------------|
| CODE-G11 | Scanned/printed code absent from positive pool — code printed in textbooks and photocopied listings look different from born-digital renders; scanner artifacts change appearance | Add 200–500 physically scanned code listing images to positive pool; source from public domain programming books or generate by scanning printed code at 150/300 DPI |
| CODE-G12 | Configuration file formats (YAML, TOML, JSON, INI) not covered by 8 languages — structurally similar to code but are configuration data | Define policy: YAML/TOML/JSON displayed in documents → has_code=True with confidence ≈ 0.6; document in schema; optionally add as 9th language variant in generator |
| CODE-G13 | Terminal output policy undefined — should CLI output (commands without function definitions) be has_code=True or False? | Define policy: recommend has_code=True for interactive shell output (commands are executable); label as code_confidence ≈ 0.5–0.7 (lower than IDE code at 1.0); document in L2 schema annotation guide |

---

## Section 11 — Performance Targets

> **Source**: [SIGLIP2_MULTITASK_REQUIREMENTS.md](../../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md)
> and [sig-g5-code-reg.md § Section 1](../../planning/har/sig-g5-code-reg.md)
>
> **Important**: The original SIGLIP2_MULTITASK_REQUIREMENTS.md specifies this head as
> "Regression 0-1" with no explicit metric target. That framing is a misnomer (see Section 1
> architectural note). The correct targets for a binary classification head are AUC and F1,
> not MAE. The targets below reflect the HAR consensus recommendation and supersede the
> original requirements document until CODE-G05 is formally resolved.

| Head ID | Head Name (current) | Head Name (target) | Task | Target Metric | Target Value | Test Set |
|---------|--------------------|--------------------|------|--------------|-------------|----------|
| SIG-G5-4 | `code_reg` | `code_cls` (rename per CODE-G05) | Binary Classification (sigmoid + BCE) | AUC | ≥ 0.90 | OOD-Code (200 images) |
| SIG-G5-4 | `code_reg` | `code_cls` (rename per CODE-G05) | Binary Classification (sigmoid + BCE) | F1 | ≥ 0.85 | OOD-Code (200 images) |
| SIG-G5-4 | `code_reg` | `code_cls` (rename per CODE-G05) | Binary Classification (sigmoid + BCE) | FPR on academic documents | ≤ 10% | OOD-Code 8b (arXiv + pseudocode) |

**Secondary target**: FPR ≤ 10% on academic documents (OOD-Code 8b) validates that the
pseudocode gap (CODE-G06) is not causing unacceptable false positives. If FPR > 15% on
academic documents post-training, treat CODE-G06 as a retroactive P0 blocker.

### Inference Threshold Calibration

The downstream routing rule `code_confidence > 0.5` → `enrich_code: true` uses the default
sigmoid midpoint as the decision threshold. With 50/50 training data, the sigmoid output is
uncalibrated for the real-world code-document prior of ~5–10%. The recommended deployment
threshold is **0.6–0.7**, not 0.5. The threshold must be calibrated on a held-out validation
set reflecting real-world prevalence before production deployment.

**Calibration process**: After training, evaluate the uncalibrated model on a prevalence-matched
validation set (5–10% positive rate). Choose the threshold that maximizes F1 or satisfies the
FPR ≤ 10% constraint on academic documents, whichever is more stringent.

### Achieved Results

| Head | Val AUC | Val F1 | Test AUC | Test F1 | Status |
|------|---------|--------|----------|---------|--------|
| `code_reg` / `code_cls` | — | — | — | — | ❌ Not trained |

---

## P0 Gap Registry

| Gap ID | One-Line Description | Acceptance Criterion |
|--------|---------------------|---------------------|
| CODE-G05 | Head named `code_reg` but must be `code_cls` (binary classification) | Rename complete in all 3 files; training run passes with BCE loss |
| CODE-G01 | Negative contamination unvalidated — doclaynet negatives may contain code | Manual sample of 100 negatives confirms <5% contain code |
| CODE-G02 | Full generation run not executed (8,613/10,000 dry-run only) | Full 10,000-image run complete and manifest validated |
| CODE-G04 | Printed-code-in-doc vs screenshot ratio unenforced | 60/40 split enforced in generation script |
| CODE-G03 | Evaluation metrics not formally defined as classification metrics | Precision/recall/F1 defined; accuracy >=85% on val set |

---

## Related Documents

- **HAR File**: [sig-g5-code-reg.md](../../planning/har/sig-g5-code-reg.md)
- **DDR**: No DDR file — generated dataset; diversity tracked via generator configuration
- **Head Spec**: [SIGLIP2_MULTITASK_REQUIREMENTS.md](../../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md)
- **Diversity Spec**: [DATASET_DIVERSITY_REQUIREMENTS.md](../../planning/DATASET_DIVERSITY_REQUIREMENTS.md)
- **Source Datasets**: [DATASET_QUICK_REFERENCE.md](../DATASET_QUICK_REFERENCE.md)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-23 | Initial creation — 11 sections populated from HAR sig-g5-code-reg.md (v2.0) and SIGLIP2_MULTITASK_REQUIREMENTS.md |
