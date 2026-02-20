# Unresolved PR Review Comments - Tracking

> **Generated**: 2026-02-16 00:57 UTC
> **Repository**: williaby/image-preprocessing-detector
> **Scope**: All merged PRs, current (non-outdated) unresolved threads

## Summary

| Metric | Count |
|--------|-------|
| Total | 91 |
| Severity: critical | 11 |
| Severity: medium | 32 |
| Severity: unclassified | 12 |
| Severity: low | 36 |

| Topic | Count | Priority |
|-------|-------|----------|
| security | 91 | HIGH |

## Triage Legend

- `[ ]` - Not reviewed
- `[x]` - Addressed
- `[~]` - Won't fix
- `[!]` - Needs investigation

## Security (91)

### 1. PR #136 - docs/datasets/source/markushgrapher.md

- **Status**: [x]
- **Severity**: critical
- **PR**: [#136 - feat: comprehensive dataset enrichment and documentation expansion](https://github.com/williaby/image-preprocessing-detector/pull/136)
- **Reviewer**: @coderabbitai
- **Date**: 2026-02-14
- **File**: `docs/datasets/source/markushgrapher.md`
- **Line**: 348

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🔴 Critical_

<details>
<summary>🧩 Analysis chain</summary>

🌐 Web query:

`MarkushGrapher-Datasets HuggingFace ds4sd citation format`

💡 Result:

If you’re citing the Hugging Face dataset repo **`docling-project/MarkushGrapher-Datasets`**, the most standard approach is:

1) **Cite the accompanying paper (recommended / primary)**
**BibTeX (paper):**

```bibtex
`@misc`{morin2025markushgrapher,
  title        = {MarkushGrapher: Joint Visual and Textual Recognition of Markush Structures},
  author       = {Lucas Morin and Val{\'e}ry Weber and Ahmed Nassar and Gerhard Ingmar Meijer and Luc Van Gool and Yawei Li and Peter Staar},
  year         = {2025},
  eprint       = {2503.16096},
  archivePrefix= {arXiv},
  primaryClass = {cs.CV},
  doi          = {10.48550/arXiv.2503.16096}
}
```

[1]

1) **Also cite the dataset repository on Hugging Face (recommended / secondary)**
**BibTeX (dataset repo):**

```bibtex
`@dataset`{markushgrapher_datasets_hf,
  title     = {MarkushGrapher-Datasets},
  author    = {docling-project (Hugging Face Hub repository; contributor: lucas-morin)},
  publisher = {Hugging Face},
  license   = {CC-BY-4.0},
  url       = {https://huggingface.co/datasets/docling-project/MarkushGrapher-Datasets},
  note      = {Accessed 2026-02-14}
}
```

[2][3]

**Notes**

- The dataset card explicitly says it “contains datasets introduced in _MarkushGrapher: Joint Visual and Textual Recognition of Markush Structures_.” [3]
- Use your required style guide (APA/MLA/Chicago) by converting the same fields (title, author/org, year, URL, access date). [2][3]

**Sources**
[1] ([arxiv.org](https://arxiv.org/abs/2503.16096))
[2] ([huggingface.co](https://huggingface.co/datasets/docling-project/MarkushGrapher-Datasets))
[3] ([huggingface.co](https://huggingface.co/datasets/docling-project/MarkushGrapher-Datasets/blob/main/README.md))

Citations:

- 1: <https://arxiv.org/abs/2503.16096>
- 2: <https://huggingface.co/datasets/docling-project/MarkushGrapher-Datasets>
- 3: <https://huggingface.co/datasets/docling-project/MarkushGrapher-Datasets/blob/main/README.md>

---

</details>

**Update BibTeX citation to match HuggingFace dataset card.**

The citation is incorrect on multiple fronts. The dataset is hosted under `docling-project`, not `ds4sd`. Update the author to reference the correct organization and fix the URL to `https://huggingface.co/datasets/docling-project/MarkushGrapher-Datasets`. Additionally, the HuggingFace dataset card explicitly recommends citing the accompanying paper as the primary reference: Morin et al., "MarkushGrapher: Joint Visual and Textual Recognition of Markush Structures" (2025, arXiv:2503.16096). Add both the paper citation and the corrected dataset repository citation.

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In `@docs/datasets/source/markushgrapher.md` around lines 339 - 347, The BibTeX
entry with key ds4sd2024markushgrapher and title "MarkushGrapher Datasets:
Chemical Structure Recognition" is incorrect; update the dataset citation to use
author/publisher "docling-project" and change the URL to
https://huggingface.co/datasets/docling-project/MarkushGrapher-Datasets, and add
the recommended primary paper citation for Morin et al., "MarkushGrapher: Joint
Visual and Textual Recognition of Markush Structures" (2025, arXiv:2503.16096)
as a separate `@article/`@misc entry in the same file so both the paper and the
corrected dataset repository are included.
```

</details>

<!-- fingerprinting:phantom:triton:puma -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 2. PR #109 - osv-scanner.toml

- **Status**: [x]
- **Severity**: critical
- **PR**: [#109 - feat: add DeQA-Doc labeling infrastructure with 3-dimension quality assessment](https://github.com/williaby/image-preprocessing-detector/pull/109)
- **Reviewer**: @coderabbitai
- **Date**: 2026-01-18
- **File**: `osv-scanner.toml`
- **Line**: 33

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🔴 Critical_

<details>
<summary>🧩 Analysis chain</summary>

🌐 Web query:

`osv-scanner v2.2.4 disputed CVE auto-filter`

💡 Result:

Short answer: No — osv-scanner v2.2.4 does not introduce an automatic "disputed CVE" filter. The v2.2.4 release notes (features/fixes) don’t mention filtering disputed CVEs; handling of "disputed" CVE records is a property of the upstream CVE/NVD→OSV data conversion and OSV data handling, not a scanner flag in the v2.2.4 release. [1][2]

If you need, I can:

- point to the exact release notes and relevant issues, or
- show how to confirm whether a given CVE marked "Disputed" is being reported by your scanner (command + sample output). [1][3]

Sources:

- osv-scanner v2.2.4 release notes. [1]
- NVD explanation of the "Disputed" tag. [2]
- Coverage/discussion of how OSV/feeds handled disputed CVEs (data conversion/behaviour). [3]

---

🌐 Web query:

`osv-scanner how to handle disputed CVE vulnerabilities configuration`

💡 Result:

Short answer: add the disputed ID(s) to osv-scanner’s ignore list (in osv-scanner.toml) or pass them to the scanner/fix command; optionally add a reason and expiry. If you want different behavior (treat disputed as vulnerabilities rather than dropped), check the OSV data source policy (OSV historically treated some “disputed” CVEs differently). [1][2][3]

How to do it

- Configure in osv-scanner.toml (project dir or via --config):
  Example entry:
  [[IgnoredVulns]]
  id = "CVE-YYYY-NNNN"
  reason = "Vendor disputes but we consider it low-risk for this app"

  # ignoreUntil = "2026-03-01"  # optional expiry

  (Documentation: IgnoreVulns key). [1]

- CLI / remediation flags: when running guided remediation or fixes you can filter out specific OSV IDs with the --ignore-vulns flag or use the --vulns flag to only include explicit IDs. Example: --ignore-vulns=CVE-YYYY-NNNN. [2]

Notes and recommendations

- Prefer documenting a reason and optional expiry so the exception is reviewed later. [1]
- If you rely on OSV data, be aware OSV’s handling of “disputed” CVEs has changed historically — verify the OSV source semantics you depend on so you don’t accidentally drop advisories. [3]

Sources:
[1] OSV-Scanner configuration / IgnoreVulns docs.
[2] OSV-Scanner guided remediation / flags (--ignore-vulns, --vulns).
[3] Report about OSV handling of disputed CVEs (context on disputed vs withdrawn).

---

</details>

**Remove documentation-only approach and add explicit `[[IgnoredVulns]]` entry for PYSEC-2022-42969.**

osv-scanner v2.2.4 does not auto-filter disputed CVEs; the `[[IgnoredVulns]]` entries must be explicitly configured. The current change removes the explicit ignore for PYSEC-2022-42969 / CVE-2022-42969 without providing a replacement mechanism, which will cause osv-scanner to report this vulnerability again.

Add back the explicit ignore entry:

```
[[IgnoredVulns]]
id = "PYSEC-2022-42969"
reason = "py library ReDoS in SVN parsing - disputed (DISPUTED in NVD as of May 2024)"
```

Optionally include an expiry date to schedule a future review of this disputed status.

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In `@osv-scanner.toml` around lines 24 - 33, Restore an explicit
ignored-vulnerability entry for the disputed CVE by adding a [[IgnoredVulns]]
block for PYSEC-2022-42969 (ID string "PYSEC-2022-42969") with a clear reason
field describing the dispute (e.g., "py library ReDoS in SVN parsing - disputed
(DISPUTED in NVD as of May 2024)"); optionally include an expiry/timestamp field
if your config supports it to schedule review. Locate where other
[[IgnoredVulns]] blocks are defined in osv-scanner.toml and add this entry so
the scanner won’t report the CVE. Ensure the id field matches "PYSEC-2022-42969"
exactly and the reason text documents the dispute.
```

</details>

<!-- fingerprinting:phantom:medusa:ocelot -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 3. PR #106 - modal/train_siglip2_iqa.py

- **Status**: [x]
- **Severity**: critical
- **PR**: [#106 - feat: Add SigLIP2-IQA-Base-86M Document Quality Assessment Model](https://github.com/williaby/image-preprocessing-detector/pull/106)
- **Reviewer**: @coderabbitai
- **Date**: 2026-01-16
- **File**: `modal/train_siglip2_iqa.py`
- **Line**: 1107

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟡 Minor_

<details>
<summary>🧩 Analysis chain</summary>

🌐 Web query:

`PyTorch torch.load weights_only parameter security PyTorch 2.x`

💡 Result:

Short answer: A critical RCE was found in torch.load’s weights_only handling (CVE-2025-32434). It affects PyTorch ≤ 2.5.1 and was fixed in 2.6.0 — do not rely on weights_only=True in older 2.x releases; upgrade and avoid loading untrusted .pt files (or use safetensors / isolate the load). [1][2][3]

Key points and actions

- Vulnerability: torch.load(weights_only=True) can still lead to remote code execution (RCE). CVE-2025-32434 / GitHub advisory. Affects < 2.6.0. [1][4]
- Patch: Fixed in PyTorch 2.6.0; upgrade to 2.6.0 or later. [1][4]
- Documentation: Since 2.6 the default/behaviour and a restricted unpickler for weights-only loads is documented; still, older versions remain unsafe. [6]
- Immediate mitigations: (a) upgrade PyTorch to ≥2.6.0, (b) never torch.load untrusted model files, (c) prefer safe formats like safetensors when possible, (d) run model-loading in isolated environments if you must load untrusted files. [2][3][6]

Sources

- PyTorch security advisory (GHSA / CVE): torch.load with weights_only=True RCE. [1][4]
- Coverage/analysis articles and CVE summaries. [2][3]
- PyTorch serialization docs describing weights_only behavior (post-fix). [6]

---

🏁 Script executed:

```shell
fd "train_siglip2_iqa.py" --type f
```

Repository: williaby/image-preprocessing-detector

Length of output: 107

---

🏁 Script executed:

```shell
cat -n modal/train_siglip2_iqa.py | sed -n '1085,1095p'
```

Repository: williaby/image-preprocessing-detector

Length of output: 516

---

🏁 Script executed:

```shell
cat -n modal/train_siglip2_iqa.py | sed -n '1150,1160p'
```

Repository: williaby/image-preprocessing-detector

Length of output: 445

---

🏁 Script executed:

```shell
fd "requirements.txt\|setup.py\|pyproject.toml" --type f | head -20
```

Repository: williaby/image-preprocessing-detector

Length of output: 63

---

🏁 Script executed:

```shell
find . -name "requirements*.txt" -o -name "pyproject.toml" -o -name "setup.py" -o -name "setup.cfg" | head -20
```

Repository: williaby/image-preprocessing-detector

Length of output: 323

---

🏁 Script executed:

```shell
cat pyproject.toml 2>/dev/null || cat setup.py 2>/dev/null || cat requirements.txt 2>/dev/null || echo "No standard dependency file found"
```

Repository: williaby/image-preprocessing-detector

Length of output: 25490

---

🏁 Script executed:

```shell
rg "torch\.load" modal/train_siglip2_iqa.py -n
```

Repository: williaby/image-preprocessing-detector

Length of output: 222

---

🏁 Script executed:

```shell
rg "torch\.load" modal/ -n --type py
```

Repository: williaby/image-preprocessing-detector

Length of output: 1157

---

</details>

**Add `weights_only=True` to `torch.load` calls for consistency and defensive security.**

PyTorch 2.9.0 (specified in project dependencies) includes the fix for CVE-2025-32434. However, explicitly setting `weights_only=True` aligns with the pattern used elsewhere in `modal/*.py` and follows defensive programming best practices. Apply to both lines 1090 and 1156.

<details>
<summary>🐛 Proposed fix</summary>

```diff
-        best_state = torch.load(output_dir / "siglip2_iqa_best.pt")
+        best_state = torch.load(output_dir / "siglip2_iqa_best.pt", weights_only=True)
```

Apply the same fix at line 1156.
</details>

<!-- suggestion_start -->

<details>
<summary>📝 Committable suggestion</summary>

> ‼️ **IMPORTANT**
> Carefully review the code before committing. Ensure that it accurately replaces the highlighted code, contains no missing lines, and has no issues with indentation. Thoroughly test & benchmark the code to ensure it meets the requirements.

```suggestion
        best_state = torch.load(output_dir / "siglip2_iqa_best.pt", weights_only=True)
        model.load_state_dict(best_state["model_state_dict"])
```

</details>

<!-- suggestion_end -->

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In `@modal/train_siglip2_iqa.py` around lines 1090 - 1091, The checkpoint loads
use torch.load(...) without weights_only and should be changed to
torch.load(..., weights_only=True) for both places that load checkpoints (the
call that assigns best_state and the later call at the end of training), so
update the torch.load invocations that produce best_state and the
final_state/loaded checkpoint to pass weights_only=True before passing the
loaded["model_state_dict"] into model.load_state_dict(...).
```

</details>

<!-- fingerprinting:phantom:medusa:ocelot -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 4. PR #106 - modal/train_siglip2_iqa.py

- **Status**: [x]
- **Severity**: critical
- **PR**: [#106 - feat: Add SigLIP2-IQA-Base-86M Document Quality Assessment Model](https://github.com/williaby/image-preprocessing-detector/pull/106)
- **Reviewer**: @coderabbitai
- **Date**: 2026-01-16
- **File**: `modal/train_siglip2_iqa.py`
- **Line**: 1108

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🔴 Critical_

<details>
<summary>🧩 Analysis chain</summary>

🌐 Web query:

`CVE-2025-32434 PyTorch torch.load vulnerability`

💡 Result:

Summary: CVE-2025-32434 is a critical remote‑code‑execution (RCE) vulnerability in PyTorch where torch.load(..., weights_only=True) can still execute arbitrary code for malicious .pt/.pth files. Affected versions: PyTorch <= 2.5.1. Fixed in PyTorch 2.6.0. Published/assigned April 17–18, 2025. [1][2][3]

Risk/impact: An attacker who supplies a crafted model file that a victim loads with torch.load(weights_only=True) can achieve arbitrary command execution on the host (full system compromise). [1][2]

Mitigation/Recommended actions:

- Upgrade PyTorch to 2.6.0 or later immediately. [1][3]
- Do not load model files from untrusted sources. Treat .pt/.pth files as untrusted pickles. [2]
- Where possible, use safer formats/loaders (e.g., safetensors) or perform loading inside isolated environments. [1][5]

References:

- GitHub Security Advisory (pytorch): torch.load with weights_only=True → RCE (GHSA-53q9-r3pm-6pq6). [1]
- NVD / CVE entry CVE-2025-32434. [2]
- PyTorch advisory/patch notes and fixes (fixed in 2.6.0). [3]

If you want, I can: (a) show a short detection check to find vulnerable PyTorch versions in your environment, (b) give pip/conda upgrade commands, or (c) review a model file safely. Which would you like?

---

🏁 Script executed:

```shell
# Check the file and verify torch version pinning and torch.load calls
cd modal
# First, let's see if the file exists and check the torch version
fd "train_siglip2_iqa.py"
```

Repository: williaby/image-preprocessing-detector

Length of output: 101

---

🏁 Script executed:

```shell
# Check around line 75 for torch version and lines 1104-1106, 1170 for torch.load calls
if [ -f modal/train_siglip2_iqa.py ]; then
  echo "=== Line 75 (torch version) ==="
  sed -n '73,77p' modal/train_siglip2_iqa.py
  echo ""
  echo "=== Lines 1102-1108 (torch.load call 1) ==="
  sed -n '1102,1108p' modal/train_siglip2_iqa.py
  echo ""
  echo "=== Lines 1168-1174 (torch.load call 2) ==="
  sed -n '1168,1174p' modal/train_siglip2_iqa.py
fi
```

Repository: williaby/image-preprocessing-detector

Length of output: 739

---

🏁 Script executed:

```shell
# Search for all torch.load calls in the file to ensure we find all instances
rg 'torch\.load' modal/train_siglip2_iqa.py -n -A 2
```

Repository: williaby/image-preprocessing-detector

Length of output: 387

---

</details>

**Upgrade PyTorch to ≥2.6.0 to fix CVE-2025-32434 RCE vulnerability—`weights_only=True` does not mitigate this issue.**

PyTorch 2.5.1 (pinned on line 75) contains CVE-2025-32434, a critical remote-code-execution vulnerability in `torch.load`. Critically, `weights_only=True` does **not** protect against this vulnerability—attackers can execute arbitrary code even with that flag enabled. The only fix is to upgrade to PyTorch 2.6.0 or later.

Update lines 1104 and 1170 by upgrading the PyTorch dependency to 2.6.0+ as shown in line 75's pip configuration.

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In `@modal/train_siglip2_iqa.py` around lines 1104 - 1106, The code currently
calls torch.load (seen in the block using best_state = torch.load(...), followed
by model.load_state_dict(...) and model.eval()) while the project pins
torch==2.5.1; upgrade the PyTorch dependency to >=2.6.0 in the pip/config where
torch is pinned (line with the version pin) and ensure all torch.load usages
(including the one that loads "siglip2_iqa_best.pt" and any other torch.load at
line ~1170) run under the upgraded package; do not rely on weights_only=True as
a mitigation—bump the dependency to 2.6.0+ and run tests/CI to validate no API
breaks.
```

</details>

<!-- fingerprinting:phantom:poseidon:ocelot -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 5. PR #100 - README.md

- **Status**: [x]
- **Severity**: critical
- **PR**: [#100 - refactor(modal): Extract shared utilities and fix SonarCloud security hotspots](https://github.com/williaby/image-preprocessing-detector/pull/100)
- **Reviewer**: @coderabbitai
- **Date**: 2026-01-11
- **File**: `README.md`
- **Line**: 360

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🔴 Critical_

**⚠️ CRITICAL: PR objectives mismatch — wrong files provided for review**

The PR objectives describe "refactor(modal): Extract shared utilities and fix SonarCloud security hotspots" (torch.load, tar.extractall, regex ReDoS, etc.), but the three files provided for review are pure documentation (README.md, DATASET_CATALOG.md, architecture diagrams). The actual Modal refactor files (modal/shared/, modal/arena_*.py) are not included.

**Action Required**: Please verify that the correct files were provided for this code review. The current files appear to be from a different PR focused on architecture documentation.

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In @README.md around lines 351 - 360, The PR contains only docs (README.md,
DATASET_CATALOG.md, architecture diagrams) but the objective mentions a Modal
refactor and security fixes; update the branch/PR to include the actual refactor
files under modal/shared/ and modal/arena_*.py (the modules you intended to
change), ensure changes include fixes for torch.load usage, safe extraction
instead of tar.extractall, and any regex ReDoS hardening, and revise the PR
title/description to accurately list these files and security hotspots so
reviewers can assess the intended changes.
```

</details>

<!-- fingerprinting:phantom:triton:mongoose -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 6. PR #56 - docs/development/phase-7-continuous-labels-strategy.md

- **Status**: [~]
- **Severity**: critical
- **PR**: [#56 - feat: integrate org-level reusable workflows and resolve security issues](https://github.com/williaby/image-preprocessing-detector/pull/56)
- **Reviewer**: @coderabbitai
- **Date**: 2025-12-01
- **File**: `docs/development/phase-7-continuous-labels-strategy.md`
- **Line**: 147

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🔴 Critical_

**Critical security issue: Use defusedxml instead of xml.etree.ElementTree.**

Line 107 uses `xml.etree.ElementTree` to parse DocCreator XML ground truth. This is vulnerable to XML attacks (billion laughs, external entity expansion) that were addressed in the PR by adding defusedxml.

Apply this diff to fix the security vulnerability:

```diff
-from xml.etree import ElementTree as ET
+from defusedxml import ElementTree as ET
```

The rest of the parsing code remains the same, as defusedxml provides a drop-in replacement for xml.etree.ElementTree.

Note: Ensure `defusedxml>=0.7.1` is in project dependencies (already added in pyproject.toml).

> Committable suggestion skipped: line range outside the PR's diff.

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In docs/development/phase-7-continuous-labels-strategy.md around lines 105 to
137, the XML parsing uses xml.etree.ElementTree which is vulnerable to XML
attacks; replace it with defusedxml's drop-in replacement (e.g., import
defusedxml.ElementTree as ET and use ET.parse(xml_path)) so parsing is safe,
keep the rest of the function unchanged, and ensure defusedxml>=0.7.1 is listed
in project dependencies.
```

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 7. PR #56 - src/image_preprocessing_detector/ingestion/pdf_resolution.py

- **Status**: [x]
- **Severity**: critical
- **PR**: [#56 - feat: integrate org-level reusable workflows and resolve security issues](https://github.com/williaby/image-preprocessing-detector/pull/56)
- **Reviewer**: @coderabbitai
- **Date**: 2025-12-01
- **File**: `src/image_preprocessing_detector/ingestion/pdf_resolution.py`
- **Line**: 147

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🔴 Critical_

<details>
<summary>🧩 Analysis chain</summary>

🏁 Script executed:

```shell
#!/bin/bash
# Search for validate_safe_path imports and usages
echo "=== validate_safe_path imports in ingestion module ==="
rg -n "validate_safe_path" src/image_preprocessing_detector/ingestion/ --type py

echo -e "\n=== Path operations in ingestion module functions ==="
rg -n "Path\(" src/image_preprocessing_detector/ingestion/ --type py -A 2

echo -e "\n=== File list in ingestion module ==="
fd . src/image_preprocessing_detector/ingestion/ --type f -e py
```

Repository: williaby/image-preprocessing-detector

Length of output: 5731

---

🏁 Script executed:

```shell
#!/bin/bash
# Check if path_security.py exists and examine pdf_resolution.py
echo "=== Checking path_security.py existence ==="
ls -la src/image_preprocessing_detector/utils/path_security.py 2>&1 || echo "File not found"

echo -e "\n=== Examining pdf_resolution.py (lines 140-180) ==="
sed -n '140,180p' src/image_preprocessing_detector/ingestion/pdf_resolution.py
```

Repository: williaby/image-preprocessing-detector

Length of output: 1874

---

🏁 Script executed:

```shell
#!/bin/bash
# Examine path_security.py
echo "=== Examining path_security.py ==="
cat src/image_preprocessing_detector/utils/path_security.py

echo -e "\n=== Searching for validate_safe_path usage across entire codebase ==="
rg -n "validate_safe_path" --type py
```

Repository: williaby/image-preprocessing-detector

Length of output: 5040

---

🏁 Script executed:

```shell
#!/bin/bash
# Check imports in pdf_resolution.py and similar files
echo "=== Imports in pdf_resolution.py ==="
head -30 src/image_preprocessing_detector/ingestion/pdf_resolution.py

echo -e "\n=== Checking if validate_safe_path is documented/referenced in PR context ==="
rg -n "path.traversal\|path_traversal\|traverse" --type py --type md
```

Repository: williaby/image-preprocessing-detector

Length of output: 960

---

</details>

**Add path traversal validation to the `analyze_pdf_resolution` method.**

The `pdf_path` parameter should be validated using `validate_safe_path` from `src/image_preprocessing_detector/utils/path_security.py` (line 169) before the existence check. The utility is already imported and used throughout the codebase (modal, data modules) to prevent directory traversal attacks. While similar path operations across the ingestion module (`pdf_upscaler.py`, `pdf_analyzer.py`, `pdf_loader.py`, `image_loader.py`) follow the same pattern, this public method accepting user-provided paths should validate against traversal patterns like `../` constructs.

Replace the current existence-only check with `validate_safe_path(pdf_path, must_exist=True)` to align with the PR's security fixes.

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In src/image_preprocessing_detector/ingestion/pdf_resolution.py around line 147,
the analyze_pdf_resolution method only checks for file existence and lacks path
traversal validation; replace the existence-only check with a call to
validate_safe_path(pdf_path, must_exist=True) (from
src/image_preprocessing_detector/utils/path_security.py) at the start of the
method so that user-supplied paths are validated against traversal patterns
before any file operations.
```

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 8. PR #54 - benchmarks/LICENSES.md

- **Status**: [x]
- **Severity**: critical
- **PR**: [#54 - chore: merge markdownlint fixes and resolve compatibility issues](https://github.com/williaby/image-preprocessing-detector/pull/54)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-26
- **File**: `benchmarks/LICENSES.md`
- **Line**: 40

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🔴 Critical_

<details>
<summary>🧩 Analysis chain</summary>

markdownlint MD040 rule code fence language specifier

---

<web_search_result>
MD040 (alias: fenced-code-language) requires fenced code blocks to include a language specifier (e.g. ```js,```bash) so renderers can apply syntax highlighting. To fix: add the appropriate language after the opening backticks (or use ```text for plain text). You can disable or configure the rule in your markdownlint config if needed. [1][2][3]

Sources:

- markdownlint (rule list & MD040). [1]
- mdBook / mdbook-lint description + config examples (allowed_languages, language_optional, disabling). [2]
- PyMarkdown/MD040 summary and examples (behavior, no auto-fix). [3]
</web_search_result>

---

Script executed:

```shell
#!/bin/bash
# Check for markdownlint configuration files in the repository
fd -e ".markdownlintrc" -o -e ".markdownlintrc.json" -o -e ".markdownlintrc.yaml" -o -e ".markdownlintrc.yml" -o -e "markdownlint.config.js" || echo "No config files found with standard names"

# Also check for markdownlint in package.json or similar
fd -e "package.json" | head -5 | xargs -I {} sh -c 'echo "=== {} ===" && cat "{}"' 2>/dev/null | grep -A 10 -B 2 "markdownlint" || true

# Check the benchmarks/LICENSES.md file to see current state
echo "=== Checking benchmarks/LICENSES.md ==="
wc -l benchmarks/LICENSES.md
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stdout:

```
No config files found with standard names
=== Checking benchmarks/LICENSES.md ===
391 benchmarks/LICENSES.md
```

stderr:

```
error: The argument '--owner <user:group>' requires a value but none was supplied

For more information try '--help'
```

</shell_result>

---

Script executed:

```shell
#!/bin/bash
# View specific lines from benchmarks/LICENSES.md showing code fence changes
# Check lines around 40, 48, 76, 104 to see current state
sed -n '38,42p;46,50p;74,78p;102,106p' benchmarks/LICENSES.md
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stdout:

````
**Citation**:

```bibtex
@inproceedings{pfitzmann2022doclaynet,
  title={DocLayNet: A Large Human-Annotated Dataset for Document-Layout Analysis},
  year={2022}
}
```text

**SPDX-License-Identifier**: `CDLA-Permissive-2.0`
  year={2020}
}
```text

**SPDX-License-Identifier**: `CC-BY-4.0`
  year={2020}
}
```text

**SPDX-License-Identifier**: `CC-BY-4.0`
````

</shell_result>

---

Script executed:

```shell
#!/bin/bash
# Get a wider view of the file to understand the structure
sed -n '35,55p' benchmarks/LICENSES.md
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stdout:

````

**Usage**: Full bundle use permitted. Commercial use allowed.

**Citation**:

```bibtex
@inproceedings{pfitzmann2022doclaynet,
  title={DocLayNet: A Large Human-Annotated Dataset for Document-Layout Analysis},
  author={Pfitzmann, Birgit and Auer, Christoph and Dolfi, Michele and Nassar, Ahmed S and Staar, Peter WJ},
  booktitle={Proceedings of the 28th ACM SIGKDD Conference on Knowledge Discovery and Data Mining},
  pages={3743--3751},
  year={2022}
}
```text

**SPDX-License-Identifier**: `CDLA-Permissive-2.0`

---

### DocBank

````

</shell_result>

---

Script executed:

```shell
#!/bin/bash
# Check if the closing fence is properly formatted or corrupted
# Look at a complete bibtex section to see the pattern
sed -n '40,42p;48,50p;76,78p' benchmarks/LICENSES.md | cat -A
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stdout:

````
```bibtex$
@inproceedings{pfitzmann2022doclaynet,$
  title={DocLayNet: A Large Human-Annotated Dataset for Document-Layout Analysis},$
```text$
$
**SPDX-License-Identifier**: `CDLA-Permissive-2.0`$
```text$
$
**SPDX-License-Identifier**: `CC-BY-4.0`$
````

</shell_result>

---

</details>

**Code fences are malformed—closing delimiters were incorrectly replaced with language specifiers.**

The closing fences for bibtex blocks (` ``` `) have been replaced with ` ```text `, which breaks markdown structure. Bibtex blocks remain unclosed, and orphaned ` ```text ` markers appear outside any code block context. This prevents proper rendering and violates markdown syntax.

**Fix**: Restore proper fence closure by replacing ` ```text ` with ` ``` ` to close each bibtex block, or revert these lines entirely.

Also applies to: 48, 76, 104, 132, 161, 188, 215, 244, 273

<details>
<summary>🤖 Prompt for AI Agents</summary>

````
In benchmarks/LICENSES.md around line 40 (and similarly at lines 48, 76, 104,
132, 161, 188, 215, 244, 273), several bibtex code blocks are not properly
closed because the closing fence markers were changed to "```text"; restore each
of those closing fences back to a plain closing triple-backtick ("```") so every
opening "```bibtex" has a matching "```" terminator (or remove the stray
"```text" lines entirely) to fix the markdown code-fence syntax and ensure
correct rendering.
````

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 9. PR #54 - docs/api/schema.md

- **Status**: [x]
- **Severity**: critical
- **PR**: [#54 - chore: merge markdownlint fixes and resolve compatibility issues](https://github.com/williaby/image-preprocessing-detector/pull/54)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-26
- **File**: `docs/api/schema.md`
- **Line**: 25

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🔴 Critical_

<details>
<summary>🧩 Analysis chain</summary>

Script executed:

```shell
#!/bin/bash
# Check the file size first
wc -l docs/api/schema.md
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stdout:

```
119 docs/api/schema.md
```

</shell_result>

---

Script executed:

```shell
#!/bin/bash
# Read the problematic sections
echo "=== Lines 15-30 (around line 25) ==="
sed -n '15,30p' docs/api/schema.md | cat -n

echo ""
echo "=== Lines 104-112 (around line 108) ==="
sed -n '104,112p' docs/api/schema.md | cat -n
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stdout:

````
=== Lines 15-30 (around line 25) ===
     1 ## Overview
     2
     3 The schema uses a hierarchical structure with COCO-aligned bounding boxes for compatibility with LayoutParser and other document analysis tools:
     4
     5 ```text
     6 DocumentMetadata
     7   └── PageMetadata (one per page)
     8       ├── DetectedIssue (quality issues)
     9       └── DocumentElement (layout elements)
    10           └── DetectedIssue (per-element quality)
    11 ```text
    12
    13 ## Module Reference
    14
    15 ::: image_preprocessing_detector.schema
    16     options:

=== Lines 104-112 (around line 108) ===
     1 ```
     2
     3 ## Key Features
     4
     5 - **Pydantic v2**: Modern validation with discriminated unions
     6 - **COCO Alignment**: Compatible with LayoutParser, Detectron2
     7 - **JSON I/O**: Built-in serialization methods
     8 - **Type Safety**: Comprehensive type hints
     9 - **Hybrid IQA**: Per-element quality assessment for embedded images
````

</shell_result>

---

Script executed:

```shell
#!/bin/bash
# Check git diff to see what changed in this file
echo "=== Git diff for docs/api/schema.md ==="
git diff HEAD docs/api/schema.md | head -100
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stdout:

```
=== Git diff for docs/api/schema.md ===
```

</shell_result>

---

Script executed:

```shell
#!/bin/bash
# Read full file around line 108
echo "=== Lines 102-115 ==="
sed -n '102,115p' docs/api/schema.md | cat -n
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stdout:

````
=== Lines 102-115 ===
     1 # Extract coordinates
     2 x, y, width, height = element.bbox
     3 ```
     4
     5 ## Key Features
     6
     7 - **Pydantic v2**: Modern validation with discriminated unions
     8 - **COCO Alignment**: Compatible with LayoutParser, Detectron2
     9 - **JSON I/O**: Built-in serialization methods
    10 - **Type Safety**: Comprehensive type hints
    11 - **Hybrid IQA**: Per-element quality assessment for embedded images
    12 - **Transform History**: Audit trail for all preprocessing operations
    13
    14 ## See Also
````

</shell_result>

---

Script executed:

```shell
#!/bin/bash
# Check git log to see if this file was modified
echo "=== Git log for docs/api/schema.md ==="
git log --oneline -10 -- docs/api/schema.md

echo ""
echo "=== Git status ==="
git status docs/api/schema.md

echo ""
echo "=== Check current branch ==="
git branch -v
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stdout:

```
=== Git log for docs/api/schema.md ===
aa51f62 chore: consolidate REUSE licensing annotations

=== Git status ===
HEAD detached at FETCH_HEAD
You are in a sparse checkout with 99% of tracked files present.

nothing to commit, working tree clean

=== Check current branch ===
* (HEAD detached at FETCH_HEAD) aa51f62 chore: consolidate REUSE licensing annotations
  coderabbit_54                 aa51f62 chore: consolidate REUSE licensing annotations
  main                          0eab040 feat: Phase 5 testing, documentation, and infrastructure improvements (#53)
```

</shell_result>

---

Script executed:

````shell
#!/bin/bash
# Search for all code fence patterns in the file
echo "=== All code fences (backticks) in docs/api/schema.md ==="
rg -n '^\s*```' docs/api/schema.md
````

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stdout:

````
=== All code fences (backticks) in docs/api/schema.md ===
19:```text
25:```text
40:```python
71:```
75:```python
87:```
93:```python
104:```
````

</shell_result>

---

Script executed:

```shell
#!/bin/bash
# Read the entire file to see all code blocks
cat -n docs/api/schema.md
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stdout:

````
     1 ---
     2 schema_type: common
     3 title: "Schema API"
     4 description: "Pydantic schema models for document metadata and quality assessment"
     5 tags: [api_reference, documentation]
     6 status: published
     7 owner: "docs-team"
     8 authors:
     9   - name: "Byron Williams"
    10 purpose: "Document the Pydantic schema models for JSON I/O and validation."
    11 ---
    12
    13 The schema module provides Pydantic v2 models for representing document metadata, quality issues, and processing results. All models include comprehensive validation and support JSON serialization.
    14
    15 ## Overview
    16
    17 The schema uses a hierarchical structure with COCO-aligned bounding boxes for compatibility with LayoutParser and other document analysis tools:
    18
    19 ```text
    20 DocumentMetadata
    21   └── PageMetadata (one per page)
    22       ├── DetectedIssue (quality issues)
    23       └── DocumentElement (layout elements)
    24           └── DetectedIssue (per-element quality)
    25 ```text
    26
    27 ## Module Reference
    28
    29 ::: image_preprocessing_detector.schema
    30     options:
    31       show_root_heading: true
    32       show_source: false
    33       members_order: source
    34       heading_level: 2
    35
    36 ## Usage Examples
    37
    38 ### Creating Metadata
    39
    40 ```python
    41 from image_preprocessing_detector.schema import (
    42     DocumentMetadata,
    43     PageMetadata,
    44     DetectedIssue,
    45 )
    46
    47 # Create document metadata
    48 metadata = DocumentMetadata(
    49     source_file="document.pdf",
    50     num_pages=5,
    51     processing_version="0.1.0",
    52 )
    53
    54 # Add page metadata
    55 page = PageMetadata(
    56     page_number=1,
    57     dpi=300,
    58     dimensions=(2550, 3300),
    59 )
    60 metadata.pages.append(page)
    61
    62 # Add quality issue
    63 issue = DetectedIssue(
    64     issue_type="blur",
    65     severity="high",
    66     confidence=0.92,
    67     location=[100, 200, 500, 600],  # COCO format: [x, y, width, height]
    68     metadata={"laplacian_variance": 45.2},
    69 )
    70 page.detected_issues.append(issue)
    71 ```
    72
    73 ### JSON Serialization
    74
    75 ```python
    76 # Serialize to JSON
    77 json_str = metadata.model_dump_json(indent=2)
    78
    79 # Write to file
    80 metadata.to_json_file("output.json")
    81
    82 # Load from file
    83 loaded = DocumentMetadata.from_json_file("output.json")
    84
    85 # Validate JSON
    86 metadata_dict = metadata.model_dump()
    87 ```
    88
    89 ### Bounding Box Format
    90
    91 All bounding boxes use **COCO format** `[x, y, width, height]`:
    92
    93 ```python
    94 from image_preprocessing_detector.schema import DocumentElement
    95
    96 element = DocumentElement(
    97     element_type="table",
    98     bbox=[100, 200, 800, 600],  # x=100, y=200, w=800, h=600
    99     confidence=0.95,
   100 )
   101
   102 # Extract coordinates
   103 x, y, width, height = element.bbox
   104 ```
   105
   106 ## Key Features
   107
   108 - **Pydantic v2**: Modern validation with discriminated unions
   109 - **COCO Alignment**: Compatible with LayoutParser, Detectron2
   110 - **JSON I/O**: Built-in serialization methods
   111 - **Type Safety**: Comprehensive type hints
   112 - **Hybrid IQA**: Per-element quality assessment for embedded images
   113 - **Transform History**: Audit trail for all preprocessing operations
   114
   115 ## See Also
   116
   117 - [Ingestion API](ingestion.md) - Loading and preprocessing
   118 - [Detection API](detection.md) - Quality issue detection
   119 - [Output API](output.md) - JSON generation
````

</shell_result>

---

</details>

**⚠️ PARTIAL CORRECTION: Code block closing fence issue at line 25 only — line 108 reference is incorrect.**

Line 25 contains a malformed code block closing fence:

- **Line 19**: Opens with ` ```text ` ✓ (correct)
- **Line 25**: Closes with ` ```text ` ✗ (incorrect — should be ` ``` `)

The review's reference to **line 108** is inaccurate. Line 104 (the closing fence for the subsequent code block in that vicinity) correctly uses ` ``` ` without a language identifier.

**Required correction**:

```diff
- ```text
+ ```
```

This appears only at **line 25**.

<details>
<summary>🤖 Prompt for AI Agents</summary>

````
In docs/api/schema.md around lines 19 to 25, the code block opened with
"```text" at line 19 is improperly closed at line 25 with "```text"; replace the
line 25 closing fence with a plain "```" so the block is correctly terminated
(do not add or remove language identifiers elsewhere and ensure only line 25 is
changed).
````

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 10. PR #53 - k8s/deployment.yaml

- **Status**: [~]
- **Severity**: critical
- **PR**: [#53 - feat: Phase 5 testing, documentation, and infrastructure improvements](https://github.com/williaby/image-preprocessing-detector/pull/53)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-26
- **File**: `k8s/deployment.yaml`
- **Line**: 104

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟠 Major_

**Deployment manifest provides good baseline with affinity and pod disruption considerations, but requires security and reproducibility improvements.**

The manifest includes pod anti-affinity, topology spread constraints, and proper health probes. However, critical production issues must be addressed before deployment: image tag reproducibility, storage limits, and secrets handling.

**Critical Production Issues**:

1. **Image Tag** (line 39): Use specific version tag, not `latest`
2. **Storage Limits** (lines 85-88): Add `sizeLimit` to both emptyDir volumes
3. **Image Pull Policy** (line 40): Change to `Always`
4. **Secrets as Env Vars** (line 49): Mount as files instead

After fixing these items, this deployment will be production-ready.

<details>
<summary>🧰 Tools</summary>

<details>
<summary>🪛 Checkov (3.2.334)</summary>

[low] 2-104: Image should use digest

(CKV_K8S_43)

---

[low] 2-104: Image Pull Policy should be Always

(CKV_K8S_15)

---

[low] 2-104: Image Tag should be fixed - not latest or blank

(CKV_K8S_14)

---

[low] 2-104: Use read-only filesystem for containers where possible

(CKV_K8S_22)

---

[low] 2-104: Containers should run as a high UID to avoid host conflict

(CKV_K8S_40)

---

[low] 2-104: Ensure that the seccomp profile is set to docker/default or runtime/default

(CKV_K8S_31)

---

[low] 2-104: Prefer using secrets as files over secrets as environment variables

(CKV_K8S_35)

---

[low] 2-104: Ensure that Service Account Tokens are only mounted where necessary

(CKV_K8S_38)

</details>
<details>
<summary>🪛 GitHub Check: SonarCloud Code Analysis</summary>

[warning] 38-38: Specify a storage limit for this container.

See more on <https://sonarcloud.io/project/issues?id=williaby_image-preprocessing-detector&issues=AZq-beT19rTh3ospdvFw&open=AZq-beT19rTh3ospdvFw&pullRequest=53>

</details>

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 11. PR #52 - scripts/validate_datasets.py

- **Status**: [x]
- **Severity**: critical
- **PR**: [#52 - refactor: fix qlty issues, add linter configs, reduce complexity](https://github.com/williaby/image-preprocessing-detector/pull/52)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-25
- **File**: `scripts/validate_datasets.py`
- **Line**: 247

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟠 Major_

<details>
<summary>🧩 Analysis chain</summary>

Script executed:

```shell
# First, let's examine the file structure and read the validation script
cd /tmp && git clone https://github.com/CodeRabbit/repository 2>/dev/null || true
cd /tmp/repository || cd /tmp

# Find the file under review
find . -name "validate_datasets.py" -type f 2>/dev/null | head -5
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stderr:

```
/bin/bash: line 3: cd: /tmp/repository: No such file or directory
```

</shell_result>

---

Script executed:

```shell
# Get an overview of the file size first
wc -l scripts/validate_datasets.py 2>/dev/null || echo "File not found in standard location"

# Try to locate it
fd "validate_datasets.py" . 2>/dev/null || find . -name "*validate*" -type f 2>/dev/null | head -10
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stdout:

```
429 scripts/validate_datasets.py
./scripts/validate_datasets.py
```

</shell_result>

---

Script executed:

```shell
#!/bin/bash
# Search for validate_datasets file
find . -type f -name "*.py" | grep -E "(validate|dataset)" | head -20
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stdout:

```
./.claude/skills/project-planning/scripts/validate-planning-docs.py
./data/dataset.py
./scripts/download_all_datasets.py
./scripts/download_iqa_datasets.py
./scripts/download_phase3_datasets.py
./scripts/generate_100k_iqa_dataset.py
./scripts/generate_dataset_status.py
./scripts/validate_artifacts.py
./scripts/validate_pdf_resolution.py
./scripts/validate_routing_accuracy.py
./scripts/create_final_dataset.py
./scripts/download_table_datasets.py
./scripts/generate_phase2_validation_datasets.py
./scripts/measure_dataset_sufficiency.py
./scripts/prepare_invoice_dataset.py
./scripts/test_dataset_generation.py
./scripts/validate_datasets.py
./scripts/validate_dqs_correlation.py
./scripts/validate_layout_lite.py
./scripts/validate_pdf_classification.py
```

</shell_result>

---

Script executed:

```shell
#!/bin/bash
# Search for the _update_summary_for_status function definition
rg -n "_update_summary_for_status" --type py -A 30
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stdout:

```
scripts/validate_datasets.py:230:def _update_summary_for_status(
scripts/validate_datasets.py-231-    results: dict, status: str, details: dict, config: dict, name: str
scripts/validate_datasets.py-232-) -> None:
scripts/validate_datasets.py-233-    """Update summary counters based on dataset status."""
scripts/validate_datasets.py-234-    status_map = {
scripts/validate_datasets.py-235-        "found": "found",
scripts/validate_datasets.py-236-        "missing": "missing",
scripts/validate_datasets.py-237-        "empty": "empty",
scripts/validate_datasets.py-238-        "symlink_broken": "broken",
scripts/validate_datasets.py-239-    }
scripts/validate_datasets.py-240-    if status in status_map:
scripts/validate_datasets.py-241-        results["summary"][status_map[status]] += 1
scripts/validate_datasets.py-242-        if status == "found":
scripts/validate_datasets.py-243-            results["summary"]["total_size"] += details.get("size", 0)
scripts/validate_datasets.py-244-        elif status in ("missing", "symlink_broken") and config["required"]:
scripts/validate_datasets.py-245-            results["required_missing"].append(name)
scripts/validate_datasets.py-246-
scripts/validate_datasets.py-247-
scripts/validate_datasets.py-248-def _validate_dataset_category(
scripts/validate_datasets.py-249-    category: str, datasets: dict, data_root: Path, results: dict
scripts/validate_datasets.py-250-) -> None:
scripts/validate_datasets.py-251-    """Validate all datasets in a category and update results."""
scripts/validate_datasets.py-252-    for name, config in datasets.items():
scripts/validate_datasets.py-253-        results["summary"]["total"] += 1
scripts/validate_datasets.py-254-        status, details = validate_dataset(name, config, data_root)
scripts/validate_datasets.py-255-        results[category][name] = {
scripts/validate_datasets.py-256-            "status": status,
scripts/validate_datasets.py-257-            "details": details,
scripts/validate_datasets.py-258-            "description": config["description"],
scripts/validate_datasets.py-259-        }
scripts/validate_datasets.py:260:        _update_summary_for_status(results, status, details, config, name)
scripts/validate_datasets.py-261-
scripts/validate_datasets.py-262-
scripts/validate_datasets.py-263-def validate_all_datasets(data_root: Path) -> dict:
scripts/validate_datasets.py-264-    """Validate all expected datasets."""
scripts/validate_datasets.py-265-    results = {
scripts/validate_datasets.py-266-        "summary": {
scripts/validate_datasets.py-267-            "total": 0,
scripts/validate_datasets.py-268-            "found": 0,
scripts/validate_datasets.py-269-            "missing": 0,
scripts/validate_datasets.py-270-            "empty": 0,
scripts/validate_datasets.py-271-            "broken": 0,
scripts/validate_datasets.py-272-            "total_size": 0,
scripts/validate_datasets.py-273-        },
scripts/validate_datasets.py-274-        "benchmarks": {},
scripts/validate_datasets.py-275-        "raw": {},
scripts/validate_datasets.py-276-        "required_missing": [],
scripts/validate_datasets.py-277-    }
scripts/validate_datasets.py-278-
scripts/validate_datasets.py-279-    _validate_dataset_category(
scripts/validate_datasets.py-280-        "benchmarks", EXPECTED_DATASETS["benchmarks"], data_root, results
scripts/validate_datasets.py-281-    )
scripts/validate_datasets.py-282-    _validate_dataset_category("raw", EXPECTED_DATASETS["raw"], data_root, results)
scripts/validate_datasets.py-283-
scripts/validate_datasets.py-284-    return results
scripts/validate_datasets.py-285-
scripts/validate_datasets.py-286-
scripts/validate_datasets.py-287-def _get_status_display(
scripts/validate_datasets.py-288-    status: str, details: dict, include_type: bool = True
scripts/validate_datasets.py-289-) -> tuple[str, str, str]:
scripts/validate_datasets.py-290-    """Get display info for a dataset status."""
```

</shell_result>

---

Script executed:

```shell
#!/bin/bash
# Find all references to "empty" status in Python files
rg -n "empty" --type py -B 2 -A 2 | grep -E "(status|empty|required)" | head -40
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stdout:

```
tests/unit/test_corrections.py:101:    def test_correct_empty_image_raises(self) -> None:
tests/unit/test_corrections.py:102:        """Test correction raises ValueError for empty image."""
tests/unit/test_corrections.py:105:        with pytest.raises(ValueError, match="Invalid or empty image"):
tests/unit/test_corrections.py:112:        with pytest.raises(ValueError, match="Invalid or empty image"):
tests/unit/test_corrections.py:183:    def test_correct_empty_image_raises(self) -> None:
tests/unit/test_corrections.py:184:        """Test enhancement raises ValueError for empty image."""
tests/unit/test_corrections.py:187:        with pytest.raises(ValueError, match="Invalid or empty image"):
tests/unit/test_corrections.py:281:    def test_correct_empty_image_raises(self) -> None:
tests/unit/test_corrections.py:282:        """Test sharpening raises ValueError for empty image."""
tests/unit/test_corrections.py:285:        with pytest.raises(ValueError, match="Invalid or empty image"):
tests/unit/test_text_gate.py:129:    def test_detect_empty_image_raises(self) -> None:
tests/unit/test_text_gate.py:130:        """Test detection raises ValueError for empty image."""
tests/unit/test_text_gate.py:133:        with pytest.raises(ValueError, match="Invalid or empty image"):
tests/unit/test_text_gate.py:150:        with pytest.raises(ValueError, match="Invalid or empty image"):
tests/unit/test_json_generator.py:255:    def test_build_empty_raises(self) -> None:
tests/unit/detection/test_layout_lite.py:222:        with pytest.raises(ValueError, match="Invalid or empty image"):
tests/unit/detection/test_layout_lite.py:225:        with pytest.raises(ValueError, match="Invalid or empty image"):
tests/unit/detection/test_layout_lite.py:278:        with pytest.raises(ValueError, match="Invalid or empty image"):
tests/unit/detection/test_layout_lite.py:318:        with pytest.raises(ValueError, match="Invalid or empty image"):
tests/unit/detection/test_layout_lite.py:357:        with pytest.raises(ValueError, match="Invalid or empty image"):
tests/unit/detection/test_layout_lite.py:383:        with pytest.raises(ValueError, match="Invalid or empty image"):
tests/unit/detection/test_layout_lite.py:417:        with pytest.raises(ValueError, match="Invalid or empty image"):
tests/unit/test_iqa_classical.py:153:    def test_detect_empty_image_raises(self) -> None:
tests/unit/test_iqa_classical.py:154:        """Test detection raises ValueError for empty image."""
tests/unit/test_iqa_classical.py:157:        with pytest.raises(ValueError, match="Invalid or empty image"):
tests/unit/test_iqa_classical.py:164:        with pytest.raises(ValueError, match="Invalid or empty image"):
tests/unit/test_iqa_classical.py:250:    def test_detect_empty_image_raises(self) -> None:
tests/unit/test_iqa_classical.py:251:        """Test detection raises ValueError for empty image."""
tests/unit/test_iqa_classical.py:254:        with pytest.raises(ValueError, match="Invalid or empty image"):
tests/unit/test_iqa_classical.py:342:    def test_detect_empty_image_raises(self) -> None:
tests/unit/test_iqa_classical.py:343:        """Test detection raises ValueError for empty image."""
tests/unit/test_iqa_classical.py:346:        with pytest.raises(ValueError, match="Invalid or empty image"):
tests/unit/test_iqa_classical.py:483:    def test_detect_empty_image_raises(self) -> None:
tests/unit/test_iqa_classical.py:484:        """Test detection raises ValueError for empty image."""
tests/unit/test_iqa_classical.py:487:        with pytest.raises(ValueError, match="Invalid or empty image"):
tests/unit/test_iqa_classical.py:494:        with pytest.raises(ValueError, match="Invalid or empty image"):
tests/unit/test_iqa_classical.py:745:    def test_detect_empty_image_raises(self) -> None:
tests/unit/test_iqa_classical.py:746:        """Test detection raises ValueError for empty image."""
tests/unit/test_iqa_classical.py:749:        with pytest.raises(ValueError, match="Invalid or empty image"):
tests/unit/test_iqa_classical.py:756:        with pytest.raises(ValueError, match="Invalid or empty image"):
```

</shell_result>

---

Script executed:

```shell
#!/bin/bash
# Search for test files related to validation
find . -type f -name "*test*.py" | grep -i validat
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stdout:

```
./tests/security/test_codeql_validation.py
```

</shell_result>

---

Script executed:

```shell
#!/bin/bash
# Let's start by finding and examining the validate_datasets.py file
echo "=== Locating file ==="
find . -name "validate_datasets.py" -type f 2>/dev/null

echo -e "\n=== Checking file size ==="
wc -l scripts/validate_datasets.py 2>/dev/null || echo "Not at standard path, searching..."

echo -e "\n=== Searching for the function ==="
rg -n "_update_summary_for_status" --type py -A 20 2>/dev/null | head -60

echo -e "\n=== Searching for 'empty' status handling ==="
rg -n '"empty"' --type py -B 3 -A 3 2>/dev/null | head -80

echo -e "\n=== Looking for test files ==="
find . -type f -name "*test*.py" 2>/dev/null | grep -i validat || find . -type f -name "test_*.py" 2>/dev/null | head -10
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stdout:

```
=== Locating file ===
./scripts/validate_datasets.py

=== Checking file size ===
429 scripts/validate_datasets.py

=== Searching for the function ===
scripts/validate_datasets.py:230:def _update_summary_for_status(
scripts/validate_datasets.py-231-    results: dict, status: str, details: dict, config: dict, name: str
scripts/validate_datasets.py-232-) -> None:
scripts/validate_datasets.py-233-    """Update summary counters based on dataset status."""
scripts/validate_datasets.py-234-    status_map = {
scripts/validate_datasets.py-235-        "found": "found",
scripts/validate_datasets.py-236-        "missing": "missing",
scripts/validate_datasets.py-237-        "empty": "empty",
scripts/validate_datasets.py-238-        "symlink_broken": "broken",
scripts/validate_datasets.py-239-    }
scripts/validate_datasets.py-240-    if status in status_map:
scripts/validate_datasets.py-241-        results["summary"][status_map[status]] += 1
scripts/validate_datasets.py-242-        if status == "found":
scripts/validate_datasets.py-243-            results["summary"]["total_size"] += details.get("size", 0)
scripts/validate_datasets.py-244-        elif status in ("missing", "symlink_broken") and config["required"]:
scripts/validate_datasets.py-245-            results["required_missing"].append(name)
scripts/validate_datasets.py-246-
scripts/validate_datasets.py-247-
scripts/validate_datasets.py-248-def _validate_dataset_category(
scripts/validate_datasets.py-249-    category: str, datasets: dict, data_root: Path, results: dict
scripts/validate_datasets.py-250-) -> None:
--
scripts/validate_datasets.py:260:        _update_summary_for_status(results, status, details, config, name)
scripts/validate_datasets.py-261-
scripts/validate_datasets.py-262-
scripts/validate_datasets.py-263-def validate_all_datasets(data_root: Path) -> dict:
scripts/validate_datasets.py-264-    """Validate all expected datasets."""
scripts/validate_datasets.py-265-    results = {
scripts/validate_datasets.py-266-        "summary": {
scripts/validate_datasets.py-267-            "total": 0,
scripts/validate_datasets.py-268-            "found": 0,
scripts/validate_datasets.py-269-            "missing": 0,
scripts/validate_datasets.py-270-            "empty": 0,
scripts/validate_datasets.py-271-            "broken": 0,
scripts/validate_datasets.py-272-            "total_size": 0,
scripts/validate_datasets.py-273-        },
scripts/validate_datasets.py-274-        "benchmarks": {},
scripts/validate_datasets.py-275-        "raw": {},
scripts/validate_datasets.py-276-        "required_missing": [],
scripts/validate_datasets.py-277-    }
scripts/validate_datasets.py-278-
scripts/validate_datasets.py-279-    _validate_dataset_category(
scripts/validate_datasets.py-280-        "benchmarks", EXPECTED_DATASETS["benchmarks"], data_root, results

=== Searching for 'empty' status handling ===
tests/unit/test_iqa_classical.py-1381-        """Test that empty image raises ValueError."""
tests/unit/test_iqa_classical.py-1382-        detector = BleedThroughDetector()
tests/unit/test_iqa_classical.py-1383-
tests/unit/test_iqa_classical.py:1384:        with pytest.raises(ValueError, match="empty"):
tests/unit/test_iqa_classical.py-1385-            detector.detect(np.array([]))
tests/unit/test_iqa_classical.py-1386-
tests/unit/test_iqa_classical.py-1387-    def test_too_small_image_raises_error(self) -> None:
--
scripts/validate_datasets.py-204-
scripts/validate_datasets.py-205-        # Check if empty
scripts/validate_datasets.py-206-        if file_count == 0:
scripts/validate_datasets.py:207:            return "empty", {
scripts/validate_datasets.py-208-                "path": str(dataset_path),
scripts/validate_datasets.py-209-                "required": config["required"],
scripts/validate_datasets.py-210-                "phase": config["phase"],
--
scripts/validate_datasets.py-234-    status_map = {
scripts/validate_datasets.py-235-        "found": "found",
scripts/validate_datasets.py-236-        "missing": "missing",
scripts/validate_datasets.py:237:        "empty": "empty",
scripts/validate_datasets.py-238-        "symlink_broken": "broken",
scripts/validate_datasets.py-239-    }
scripts/validate_datasets.py-240-    if status in status_map:
--
scripts/validate_datasets.py-267-            "total": 0,
scripts/validate_datasets.py-268-            "found": 0,
scripts/validate_datasets.py-269-            "missing": 0,
scripts/validate_datasets.py:270:            "empty": 0,
scripts/validate_datasets.py-271-            "broken": 0,
scripts/validate_datasets.py-272-            "total_size": 0,
scripts/validate_datasets.py-273-        },
--
scripts/validate_datasets.py-295-            f" [{details.get('type', '')}]" if include_type else "",
scripts/validate_datasets.py-296-        ),
scripts/validate_datasets.py-297-        "missing": ("❌", "", ""),
scripts/validate_datasets.py:298:        "empty": ("⚠️", " (empty directory)", ""),
scripts/validate_datasets.py-299-        "symlink_broken": ("🔗", " (broken symlink)", ""),
scripts/validate_datasets.py-300-    }
scripts/validate_datasets.py-301-    return status_info.get(status, ("❓", "", ""))

=== Looking for test files ===
./tests/security/test_codeql_validation.py
```

</shell_result>

---

Script executed:

```shell
#!/bin/bash
# Read more of the file to understand context
echo "=== Full validate_dataset function ==="
sed -n '170,215p' scripts/validate_datasets.py

echo -e "\n=== Check how required_missing is used ==="
rg -n "required_missing" --type py -B 2 -A 2

echo -e "\n=== Look at EXPECTED_DATASETS structure ==="
rg -n "EXPECTED_DATASETS" --type py -A 5 | head -80
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stdout:

```
=== Full validate_dataset function ===
        return "missing", {
            "path": str(dataset_path),
            "required": config["required"],
            "phase": config["phase"],
        }

    # Check if symlink
    if dataset_path.is_symlink():
        target = dataset_path.resolve()
        if not target.exists():
            return "symlink_broken", {
                "path": str(dataset_path),
                "target": str(target),
                "required": config["required"],
                "phase": config["phase"],
            }
        # Symlink is valid
        size = get_directory_size(target)
        file_count = count_files(target)
        return "found", {
            "path": str(dataset_path),
            "type": "symlink",
            "target": str(target),
            "size": size,
            "size_human": format_size(size),
            "file_count": file_count,
            "required": config["required"],
            "phase": config["phase"],
        }

    # Regular directory
    if dataset_path.is_dir():
        size = get_directory_size(dataset_path)
        file_count = count_files(dataset_path)

        # Check if empty
        if file_count == 0:
            return "empty", {
                "path": str(dataset_path),
                "required": config["required"],
                "phase": config["phase"],
            }

        return "found", {
            "path": str(dataset_path),
            "type": "directory",

=== Check how required_missing is used ===
scripts/validate_datasets.py-243-            results["summary"]["total_size"] += details.get("size", 0)
scripts/validate_datasets.py-244-        elif status in ("missing", "symlink_broken") and config["required"]:
scripts/validate_datasets.py:245:            results["required_missing"].append(name)
scripts/validate_datasets.py-246-
scripts/validate_datasets.py-247-
--
scripts/validate_datasets.py-274-        "benchmarks": {},
scripts/validate_datasets.py-275-        "raw": {},
scripts/validate_datasets.py:276:        "required_missing": [],
scripts/validate_datasets.py-277-    }
scripts/validate_datasets.py-278-
--
scripts/validate_datasets.py-339-
scripts/validate_datasets.py-340-    # Required missing
scripts/validate_datasets.py:341:    if results["required_missing"]:
scripts/validate_datasets.py-342-        print("\n❗ REQUIRED DATASETS MISSING:")
scripts/validate_datasets.py-343-        print("-" * 80)
scripts/validate_datasets.py:344:        for name in results["required_missing"]:
scripts/validate_datasets.py-345-            print(f"  - {name}")
scripts/validate_datasets.py-346-
--
scripts/validate_datasets.py-416-
scripts/validate_datasets.py-417-    # Exit with error if required datasets are missing
scripts/validate_datasets.py:418:    if results["required_missing"]:
scripts/validate_datasets.py-419-        logger.error(
scripts/validate_datasets.py:420:            f"Validation failed: {len(results['required_missing'])} required datasets missing"
scripts/validate_datasets.py-421-        )
scripts/validate_datasets.py-422-        return 1

=== Look at EXPECTED_DATASETS structure ===
scripts/validate_datasets.py:33:EXPECTED_DATASETS = {
scripts/validate_datasets.py-34-    "benchmarks": {
scripts/validate_datasets.py-35-        "doclaynet": {
scripts/validate_datasets.py-36-            "path": "benchmarks/doclaynet",
scripts/validate_datasets.py-37-            "type": "symlink",
scripts/validate_datasets.py-38-            "target": "/home/byron/dev/data_ingestor/data/benchmarks/doclaynet",
--
scripts/validate_datasets.py:280:        "benchmarks", EXPECTED_DATASETS["benchmarks"], data_root, results
scripts/validate_datasets.py-281-    )
scripts/validate_datasets.py:282:    _validate_dataset_category("raw", EXPECTED_DATASETS["raw"], data_root, results)
scripts/validate_datasets.py-283-
scripts/validate_datasets.py-284-    return results
scripts/validate_datasets.py-285-
scripts/validate_datasets.py-286-
scripts/validate_datasets.py-287-def _get_status_display(
```

</shell_result>

---

Script executed:

```shell
#!/bin/bash
# Check git history for the previous implementation
echo "=== Git log for validate_datasets.py ==="
git log --oneline scripts/validate_datasets.py | head -20

echo -e "\n=== Check git diff for recent changes to _update_summary_for_status ==="
git log -p --follow -S "_update_summary_for_status" -- scripts/validate_datasets.py | head -200
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stdout:

```
=== Git log for validate_datasets.py ===
9845e94 chore: add markdownlint and yamllint configs with 120 char line length

=== Check git diff for recent changes to _update_summary_for_status ===
```

</shell_result>

---

Script executed:

```shell
#!/bin/bash
# Check if there's a test file for validate_datasets
echo "=== Finding test files for validate_datasets ==="
find . -type f -name "*test*validate*dataset*" -o -name "*validate*dataset*test*" 2>/dev/null

echo -e "\n=== Looking for any test that tests empty dataset handling ==="
rg -n "empty" --type py tests/ 2>/dev/null | grep -i "dataset\|validat" | head -30
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stdout:

```
=== Finding test files for validate_datasets ===

=== Looking for any test that tests empty dataset handling ===
```

</shell_result>

---

Script executed:

```shell
#!/bin/bash
# Let's see the full file to understand the overall structure and exit behavior
echo "=== Check the main function and exit behavior ==="
sed -n '350,429p' scripts/validate_datasets.py

echo -e "\n=== Check for how exit code is determined ==="
rg -n "exit\|sys.exit" scripts/validate_datasets.py -B 3 -A 3
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 1

stdout:

```
=== Check the main function and exit behavior ===
    for name, info in results["benchmarks"].items():
        _print_dataset_entry(name, info, show_required=True, show_type=True)

    # Raw datasets
    print("\n📁 RAW DATASETS")
    print("-" * 80)
    for name, info in results["raw"].items():
        _print_dataset_entry(name, info, show_required=False, show_type=False)

    print("\n" + "=" * 80)


def save_validation_json(results: dict, output_path: Path):
    """Save validation results to JSON file."""
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Validation results saved to: {output_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate dataset presence and status",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--data-root", default="data", help="Root data directory (default: data)"
    )
    parser.add_argument("--output-json", help="Save validation results to JSON file")
    parser.add_argument(
        "--upload-to-gcs",
        action="store_true",
        help="Upload datasets to GCS after validation (not yet implemented)",
    )

    args = parser.parse_args()

    # Get data root
    if os.path.isabs(args.data_root):
        data_root = Path(args.data_root)
    else:
        project_root = Path(__file__).parent.parent
        data_root = project_root / args.data_root

    if not data_root.exists():
        logger.error(f"Data directory not found: {data_root}")
        return 1

    logger.info(f"Validating datasets in: {data_root.absolute()}")

    # Validate all datasets
    results = validate_all_datasets(data_root)

    # Print report
    print_validation_report(results)

    # Save JSON if requested
    if args.output_json:
        output_path = Path(args.output_json)
        save_validation_json(results, output_path)

    # Upload to GCS if requested
    if args.upload_to_gcs:
        logger.warning(
            "GCS upload not yet implemented - use scripts/upload_datasets_to_gcs.sh"
        )

    # Exit with error if required datasets are missing
    if results["required_missing"]:
        logger.error(
            f"Validation failed: {len(results['required_missing'])} required datasets missing"
        )
        return 1

    logger.info("✅ Validation complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

=== Check for how exit code is determined ===
```

</shell_result>

---

Script executed:

```shell
#!/bin/bash
# Get more context on the validate_dataset function and how empty is handled
echo "=== Full validate_dataset function ==="
sed -n '170,228p' scripts/validate_datasets.py

echo -e "\n=== Check required_missing usage ==="
rg -n "required_missing" --type py -B 2 -A 2 scripts/validate_datasets.py

echo -e "\n=== Git history of this function ==="
git log --oneline scripts/validate_datasets.py | head -15

echo -e "\n=== Check main function for exit logic ==="
tail -60 scripts/validate_datasets.py
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stdout:

```
=== Full validate_dataset function ===
        return "missing", {
            "path": str(dataset_path),
            "required": config["required"],
            "phase": config["phase"],
        }

    # Check if symlink
    if dataset_path.is_symlink():
        target = dataset_path.resolve()
        if not target.exists():
            return "symlink_broken", {
                "path": str(dataset_path),
                "target": str(target),
                "required": config["required"],
                "phase": config["phase"],
            }
        # Symlink is valid
        size = get_directory_size(target)
        file_count = count_files(target)
        return "found", {
            "path": str(dataset_path),
            "type": "symlink",
            "target": str(target),
            "size": size,
            "size_human": format_size(size),
            "file_count": file_count,
            "required": config["required"],
            "phase": config["phase"],
        }

    # Regular directory
    if dataset_path.is_dir():
        size = get_directory_size(dataset_path)
        file_count = count_files(dataset_path)

        # Check if empty
        if file_count == 0:
            return "empty", {
                "path": str(dataset_path),
                "required": config["required"],
                "phase": config["phase"],
            }

        return "found", {
            "path": str(dataset_path),
            "type": "directory",
            "size": size,
            "size_human": format_size(size),
            "file_count": file_count,
            "required": config["required"],
            "phase": config["phase"],
        }

    return "unknown", {
        "path": str(dataset_path),
        "required": config["required"],
        "phase": config["phase"],
    }


=== Check required_missing usage ===
243-            results["summary"]["total_size"] += details.get("size", 0)
244-        elif status in ("missing", "symlink_broken") and config["required"]:
245:            results["required_missing"].append(name)
246-
247-
--
274-        "benchmarks": {},
275-        "raw": {},
276:        "required_missing": [],
277-    }
278-
--
339-
340-    # Required missing
341:    if results["required_missing"]:
342-        print("\n❗ REQUIRED DATASETS MISSING:")
343-        print("-" * 80)
344:        for name in results["required_missing"]:
345-            print(f"  - {name}")
346-
--
416-
417-    # Exit with error if required datasets are missing
418:    if results["required_missing"]:
419-        logger.error(
420:            f"Validation failed: {len(results['required_missing'])} required datasets missing"
421-        )
422-        return 1

=== Git history of this function ===
9845e94 chore: add markdownlint and yamllint configs with 120 char line length

=== Check main function for exit logic ===
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate dataset presence and status",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--data-root", default="data", help="Root data directory (default: data)"
    )
    parser.add_argument("--output-json", help="Save validation results to JSON file")
    parser.add_argument(
        "--upload-to-gcs",
        action="store_true",
        help="Upload datasets to GCS after validation (not yet implemented)",
    )

    args = parser.parse_args()

    # Get data root
    if os.path.isabs(args.data_root):
        data_root = Path(args.data_root)
    else:
        project_root = Path(__file__).parent.parent
        data_root = project_root / args.data_root

    if not data_root.exists():
        logger.error(f"Data directory not found: {data_root}")
        return 1

    logger.info(f"Validating datasets in: {data_root.absolute()}")

    # Validate all datasets
    results = validate_all_datasets(data_root)

    # Print report
    print_validation_report(results)

    # Save JSON if requested
    if args.output_json:
        output_path = Path(args.output_json)
        save_validation_json(results, output_path)

    # Upload to GCS if requested
    if args.upload_to_gcs:
        logger.warning(
            "GCS upload not yet implemented - use scripts/upload_datasets_to_gcs.sh"
        )

    # Exit with error if required datasets are missing
    if results["required_missing"]:
        logger.error(
            f"Validation failed: {len(results['required_missing'])} required datasets missing"
        )
        return 1

    logger.info("✅ Validation complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

</shell_result>

---

Script executed:

```shell
#!/bin/bash
# Check for any comments or documentation about empty dataset handling
echo "=== Looking for comments near the empty handling ==="
sed -n '200,220p' scripts/validate_datasets.py

echo -e "\n=== Check for any TODO or FIXME comments ==="
rg -n "TODO|FIXME" scripts/validate_datasets.py

echo -e "\n=== Look at the exact line where empty is determined and how it's handled in prior versions ==="
git log -p --all -- scripts/validate_datasets.py | head -400

echo -e "\n=== Check if there's any config documentation about 'required' field ==="
rg -n '"required"' scripts/validate_datasets.py -B 1 -A 1 | head -60
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stdout:

```
=== Looking for comments near the empty handling ===
    # Regular directory
    if dataset_path.is_dir():
        size = get_directory_size(dataset_path)
        file_count = count_files(dataset_path)

        # Check if empty
        if file_count == 0:
            return "empty", {
                "path": str(dataset_path),
                "required": config["required"],
                "phase": config["phase"],
            }

        return "found", {
            "path": str(dataset_path),
            "type": "directory",
            "size": size,
            "size_human": format_size(size),
            "file_count": file_count,
            "required": config["required"],
            "phase": config["phase"],

=== Check for any TODO or FIXME comments ===

=== Look at the exact line where empty is determined and how it's handled in prior versions ===

=== Check if there's any config documentation about 'required' field ===
39-            "phase": 1,
40:            "required": True,
41-            "description": "DocLayNet layout detection dataset",
--
46-            "phase": "?",
47:            "required": False,
48-            "description": "Signature detection dataset",
--
53-            "phase": 1,
54:            "required": True,
55-            "description": "Synthetic IQA dataset (auto-generated)",
--
60-            "phase": 2,
61:            "required": False,
62-            "description": "COCO-Text annotations",
--
67-            "phase": 3,
68:            "required": False,
69-            "description": "OmniDocBench multi-task benchmark",
--
74-            "phase": 2,
75:            "required": False,
76-            "description": "TableBank table detection dataset",
--
81-            "phase": 2,
82:            "required": False,
83-            "description": "PubTabNet table structure dataset",
--
88-            "phase": 2,
89:            "required": False,
90-            "description": "FinTabNet financial table dataset",
--
95-            "phase": 2,
96:            "required": False,
97-            "description": "WiLI language identification dataset",
--
104-            "phase": 1,
105:            "required": False,
106-            "description": "DocBank raw data",
--
111-            "phase": 1,
112:            "required": False,
113-            "description": "RVL-CDIP document classification",
--
118-            "phase": 1,
119:            "required": False,
120-            "description": "Tobacco800 document classification",
--
171-            "path": str(dataset_path),
172:            "required": config["required"],
173-            "phase": config["phase"],
--
182-                "target": str(target),
183:                "required": config["required"],
184-                "phase": config["phase"],
--
195-            "file_count": file_count,
196:            "required": config["required"],
197-            "phase": config["phase"],
--
```

</shell_result>

---

Script executed:

```shell
#!/bin/bash
# Let's get more git history details
echo "=== Full git log with stat ==="
git log --all --stat scripts/validate_datasets.py

echo -e "\n=== Check if this is a new file or has history ==="
git log --follow --all -- scripts/validate_datasets.py | head -80
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stdout:

````
=== Full git log with stat ===
commit 9845e94c2bf7042a6cac2591682eb2ae5cbf2e4a
Author: Byron Williams <byronawilliams@gmail.com>
Date:   Tue Nov 25 15:17:29 2025 -0800

    chore: add markdownlint and yamllint configs with 120 char line length

    - Add .markdownlint.yaml with 120 char line length (matching project standards)
    - Add .yamllint.yaml with 120 char line length and relaxed truthy rules
    - Remove deprecated .hadolint.yaml and .shellcheckrc (qlty uses defaults)

    🤖 Generated with [Claude Code](https://claude.com/claude-code)

    Co-Authored-By: Claude <noreply@anthropic.com>

 scripts/validate_datasets.py | 429 +++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 429 insertions(+)

commit d59091db1c7951a93fdc438ef855d1b1b090e785
Author: williaby <67131297+williaby@users.noreply.github.com>
Date:   Sat Nov 15 19:20:34 2025 -0800

    Phase 1 MVP Completion: Ready for Phase 2 (#30)

    * docs: Add PR 14-15 reconciliation guide and DQS routing ADR

    Create comprehensive reconciliation document analyzing PRs 14-15:
    - Identifies critical inconsistencies (bbox format, performance targets)
    - Categorizes content as keep/update/discard with clear rationale
    - Provides 4-phase integration roadmap with action items
    - Documents 10-33x performance discrepancy requiring resolution

    Create ADR-0028 for Document Quality Score (DQS) framework:
    - Two-axis scoring: degradation (blur, noise) vs structural (tables, formulas)
    - Four-quadrant routing: vision_simple, vision_structured, ocr_fast, ocr_advanced
    - Complete implementation spec with schema, calculator, and routing logic
    - Monitoring strategy with Prometheus metrics and alerting
    - Phase 4 deployment plan with feature flags and A/B testing

    Update ADR index to include ADR-0028 in Phase Planning section.

    Related: PRs #14, #15

    * docs: Implement PR 14-15 reconciliation decisions and create functional requirements v2

    Update reconciliation document with project owner decisions:
    - Project name: Keep "Image Preprocessing Detector"
    - Office formats: Defer to Phase 5 with Docling integration (embedded images only)
    - PDF Portfolio: Ignore completely (permanently out of scope)
    - DQS Framework: Implement in Phase 4 (confirmed)

    Create functional_requirements_v2.md (docs/requirements/):
    - Fix CRITICAL bounding box format: [x,y,w,h] COCO format (was [x1,y1,x2,y2])
    - Update performance targets: Split GPU (150ms, 6+ pages/sec) vs CPU (400ms, 2+ pages/sec)
    - Update correction thresholds: 2° skew with do-no-harm guardrails (was 0.5°)
    - Add Office formats to Phase 5: Embedded image preprocessing only
    - Remove PDF Portfolio: Permanently out of scope
    - Add DQS routing: Four-quadrant decision matrix (Phase 4)
    - Add language detection: FR-5.3 with langdetect/fasttext
    - Add handwriting classification: FR-5.2 with F1 ≥ 0.90 target
    - Align with all ADRs (0001-0028) and PROJECT_PLAN phases

    Update PROJECT_PLAN Phase 5:
    - Add Office format preprocessing (Task 6):
      - Extract embedded images from .docx, .xlsx, .pptx
      - Run existing preprocessing pipeline (DPI upscaling, deskew, denoise)
      - Pass corrected images to Docling for improved OCR accuracy
      - Timeline: Weeks 21-25 implementation
    - Add dependencies: python-docx, openpyxl, python-pptx
    - Add success criteria: >15% OCR accuracy improvement on embedded images

    All three recommended steps completed per user request.

    Related: PRs #14, #15
    Supersedes: PRs #14-15 functional_requirements.md

    * fix: Pin dependencies by hash to satisfy OpenSSF Scorecard requirements

    Address OpenSSF Scorecard pinned version warnings by:
    - Pin GitHub Actions to commit SHA (ClusterFuzzLite v1 → 884713a6)
    - Pin Docker image to digest (gcr.io/oss-fuzz-base/base-builder-python)
    - Pin pip packages to specific versions with hashes where applicable:
      * poetry==2.2.1 (.clusterfuzzlite/build.sh)
      * atheris==2.3.0 (.clusterfuzzlite/build.sh)
      * twine==6.2.0 (.github/workflows/publish-pypi.yml)
      * cyclonedx-bom==4.6.1 with SHA256 hash (.github/workflows/sbom.yml)

    This improves supply chain security by ensuring reproducible builds
    and preventing dependency confusion attacks.

    Resolves: 46/46 third-party GitHub Actions pinned
    Resolves: 1/1 container images pinned
    Resolves: 5/5 pip commands pinned

    * feat: Phase 2 Week 1 - Dataset analysis and Genalog integration infrastructure

    **Dataset Reference Analysis:**
    - Convert image_reference_sets.txt to markdown format
    - Add Phase 2 Week 1 coverage analysis
    - Map identified datasets against PROJECT_PLAN.md requirements
    - Document gaps (RVL-CDIP, Tobacco800, DocBank for base clean documents)
    - Coverage matrix shows strong IQA validation datasets (DIQA-5000, SOC)
    - Genalog and DocCreator identified as synthetic augmentation tools

    **Genalog Integration (Infrastructure Complete):**
    - Add genalog dependency to pyproject.toml (ml group)
    - Create augmentation package with Pydantic configuration schemas
    - Implement GenalogDegrader wrapper class (infrastructure only)
    - Support for 4 degradation types:
      * Blur (Gaussian blur for defocus/motion simulation)
      * Bleed-through (double-sided printing artifacts)
      * Salt & pepper noise (ink degradation)
      * Morphological operations (erode, dilate, open, close)
    - Type-safe configuration with validation
    - Reproducible degradations via seed control
    - Batch processing support
    - Placeholder for sensitivity analysis (Phase 2 Week 2+)

    **Documentation:**
    - Create docs/GENALOG_INTEGRATION.md with:
      * Installation guide (Python + system dependencies)
      * Architecture and module structure
      * Usage examples and API reference
      * Configuration reference with all parameters
      * Validation strategy (SOC dataset for functional validation)
      * Phase 2 implementation roadmap
      * Troubleshooting guide

    **Status:**
    - ✅ Infrastructure: Complete (config, wrapper, docs)
    - 🔨 Implementation: Pending (actual Genalog API calls in Phase 2 Week 1-2)
    - 🔨 Data Generation: Pending (50k synthetic images in Phase 2 Week 2-3)

    **References:**
    - image_reference_sets.md Section IV: Synthetic Generation
    - PROJECT_PLAN.md Phase 2 Week 1: Data Collection & Augmentation
    - Genalog: https://github.com/microsoft/genalog

    **No Breaking Changes** - New augmentation package is independent module

    * docs: Add dataset URLs and comprehensive citation framework

    **Dataset URLs Added (image_reference_sets.md):**
    - DIQA-5000 (VQualA 2025): https://codalab.lisn.upsaclay.fr/competitions/23020
    - DocIQ: https://arxiv.org/abs/2509.17012
    - SOC Dataset: https://github.com/rjchern/DIQA_CNN
    - PubLayNet: https://github.com/ibm-aur-nlp/PubLayNet
    - DocLayNet: https://github.com/DS4SD/DocLayNet + HuggingFace
    - TableBank: https://doc-analysis.github.io/tablebank-page/
    - PubTabNet: https://github.com/ibm-aur-nlp/PubTabNet
    - Marmot: https://www.icst.pku.edu.cn/cpdp/sjzy/
    - TFD-ICDAR 2019: https://github.com/MaliParag/TFD-ICDAR2019
    - SignaTR6K: https://arxiv.org/abs/2307.07887
    - DISEC'13: https://arxiv.org/abs/1912.02504
    - Kaggle Noisy/Rotated: https://www.kaggle.com/datasets/sthabile/noisy-and-rotated-scanned-documents
    - DocCreator: https://github.com/DocCreator/DocCreator
    - Genalog: https://github.com/microsoft/genalog
    - RVL-CDIP: https://adamharley.com/rvl-cdip/ + HuggingFace
    - Tobacco800: https://www.kaggle.com/datasets/patrickaudriaz/tobacco800
    - DocBank: https://doc-analysis.github.io/docbank-page/

    **New CITATIONS.md File:**
    - Comprehensive BibTeX citations for all datasets
    - License compliance matrix
    - Usage status tracking (Currently Used, Planned, Reference)
    - Detailed attribution guidelines for publications
    - Required attribution text for each dataset
    - Update procedures and maintenance guidelines

    **Currently Used Datasets:**
    - ✅ DocLayNet: 80,863 pages for validation (CDLA-Permissive-2.0)
    - ✅ Genalog: Synthetic degradation infrastructure (MIT License)

    **README.md Updates:**
    - Added "Datasets Used" section under Citation
    - Links to CITATIONS.md for full attribution details
    - License badges for DocLayNet and Genalog

    **Citation Guidelines Established:**
    1. Required citations for actively used datasets
    2. BibTeX format for all datasets
    3. In-text citation examples
    4. License compliance requirements
    5. Quarterly review procedures

    **Benefits:**
    - Clear academic attribution for dataset usage
    - License compliance documentation
    - Easy reference for future publications
    - Transparent dataset tracking
    - Community standards compliance

    **References:**
    - See validation/DOCLAYNET_COVERAGE.md for DocLayNet usage details
    - See docs/GENALOG_INTEGRATION.md for Genalog infrastructure

    **No Breaking Changes** - Pure documentation updates

    * docs: Add public dataset accessibility analysis

    87.5% public coverage. Phase 2 Week 1 unaffected.

    * Merge claude review phase 2 plan (#17)

    * docs: Add comprehensive Phase 2 ML IQA implementation plan

    Create detailed 4-week implementation roadmap for Phase 2: ML for Image
    Quality Assessment. Includes complete technical specifications, code
    examples, integration strategies, and success criteria.

    Phase 2 Goals:
    - Train multi-label IQA CNN (MobileNetV3/EfficientNet)
    - Improve detection accuracy beyond Phase 1 classical methods
    - Add noise, perspective, and orientation detection
    - Ensemble fusion of classical + ML approaches
    - ONNX optimization for <200ms CPU inference

    Success Criteria:
    - mAP > 0.88 across all labels
    - Per-class F1 > 0.85 (6 issue types)
    - ECE < 0.05 (well-calibrated)
    - JSON Accuracy > 0.75 (vs Phase 1: 0.60)

    Implementation Plan:
    - Week 1: Data collection & augmentation (50k images, weak supervision)
    - Week 2: Model training (PyTorch, cross-validation, checkpointing)
    - Week 3: Evaluation & optimization (ONNX export, INT8 quantization)
    - Week 4: Integration & testing (ensemble fusion, 80%+ coverage)

    Dependencies: All ML packages already defined in pyproject.toml
    Ready for: Phase 2 kickoff after Phase 1/1B completion

    Ref: PROJECT_PLAN.md Phase 2 (lines 929-992)

    * docs: Add comprehensive project improvement opportunities analysis

    Create detailed analysis document identifying strategic improvement
    opportunities across 6 key areas: performance, architecture, code quality,
    data pipeline, ML workflow, and production readiness.

    Key Recommendations (P0 - Quick Wins):
    - Caching layer for 20-40% latency reduction
    - Plugin architecture for better extensibility
    - Experiment tracking (MLflow) for 10× faster ML iteration
    - Pydantic-based configuration management

    Strategic Enhancements (P1 - High Impact):
    - Batch processing pipeline (5-10× throughput improvement)
    - Automated hyperparameter tuning (5-10% mAP gain)
    - Circuit breaker pattern for graceful degradation
    - Model quantization (40-60% inference speedup)
    - DVC pipeline for reproducible data workflows
    - Multi-model serving for A/B testing

    Medium Priority (P2):
    - Streaming pipeline for O(1) memory usage
    - DAG-based pipeline orchestration
    - Early exit optimization (40-60% latency on clean docs)
    - Property-based testing expansion
    - Integration test suite expansion (19 → 50+ tests)

    Expected Impact:
    - Performance: 20-60% latency reduction, 5-10× throughput
    - Code Quality: 90%+ coverage, 80%+ mutation kill rate
    - ML Workflow: 10× faster iteration, 100% reproducibility
    - Production: 99.5%+ uptime, full observability

    Phase 2 Integration:
    - Week 1: Infrastructure (plugins, config, MLflow, DVC)
    - Week 2: Training (hyperparameter tuning, data quality)
    - Week 3: Optimization (caching, quantization, perf tests)
    - Week 4: Integration (batch processing, circuit breaker, multi-model)

    Document provides prioritized roadmap (P0/P1/P2/P3) with clear
    implementation phases, expected ROI, and integration points for
    Phases 2-4.

    Ref: PROJECT_PLAN.md, PHASE_2_PLAN.md

    ---------

    Co-authored-by: Claude <noreply@anthropic.com>

    * fix: Update CI/CD badge URLs to use workflow file names (#20)

    Changed badge URLs from workflow display names to workflow file names
    for more reliable badge status display. This ensures badges correctly
    show the status of workflows running on the main branch.

    - Updated badge format from workflows/{name} to actions/workflows/{file}
    - Maintained ?branch=main parameter to show only main branch status
    - Affects: CI Pipeline, Security Analysis, Documentation, ClusterFuzzLite, SBOM badges

    Co-authored-by: Claude <noreply@anthropic.com>

    * Merge claude openss work (#22)

    * docs: Add cryptography scope statement to SECURITY.md

    Add clarification that this library does not implement cryptographic
    primitives, protocols, password management, or key/token generation.
    Transport security is delegated to hosting platforms.

    Part of OpenSSF Best Practices badge requirements.

    * docs: Add secret management section to SECURITY.md

    Document secret scanning and prevention measures:
    - Gitleaks CI scanning for secret exposure
    - GitHub's built-in Secret Scanning
    - detect-secrets pre-commit hooks for local prevention
    - Explicit statement that no private keys/tokens stored

    Part of OpenSSF Best Practices badge requirements.

    ---------

    Co-authored-by: Claude <noreply@anthropic.com>

    * docs: Expand Phase 5 with comprehensive operational excellence plan (#18)

    - Break Phase 5 into 4 sub-phases (5A-5D) spanning weeks 21-40+
    - Phase 5A: Operational Foundation (monitoring, logging, tracing, alerting)
      * Prometheus + Grafana stack with 3 dashboards
      * Structured logging with Loki/Elasticsearch
      * Distributed tracing (Jaeger/Tempo)
      * Sentry error tracking and on-call rotation
    - Phase 5B: Intelligence & Automation (drift detection, MLOps)
      * Model drift detection (KL divergence, confidence monitoring)
      * Data flywheel and active learning pipeline
      * MLOps automation with MLflow, DVC, GitHub Actions
      * A/B testing framework with auto-rollback
      * Quarterly calibration and retraining
    - Phase 5C: Optimization & Scale (cost, performance, scalability)
      * Cost optimization strategies (30%+ reduction target)
      * Performance tuning (20% latency improvement)
      * Scalability testing (10x load capacity)
      * Chaos engineering validation
      * Multi-region deployment strategy
      * Comprehensive operational runbooks
    - Phase 5D: Ongoing Operations (continuous excellence)
      * Weekly/monthly/quarterly operational cadence
      * On-call responsibilities and incident response
      * Detailed KPIs (uptime, latency, cost, drift, MTTR)
      * Team structure and roles (SRE, ML Eng, Data Eng)
      * Budget estimates ($382k-$564k annual)
      * Long-term roadmap (Phases 6-8)

    Key additions:
    - 1,250+ lines of detailed implementation guidance
    - Code examples for monitoring, drift detection, A/B testing
    - Prometheus alerting rules and Grafana dashboard specs
    - MLflow model registry and DVC dataset versioning workflows
    - Kubernetes auto-scaling configurations
    - Post-Incident Review and QBR templates
    - Technology stack specifications for all Phase 5 components

    This expansion provides production-ready operational guidance for
    maintaining and continuously improving the system over years of use.

    Co-authored-by: Claude <noreply@anthropic.com>
    Co-authored-by: Claude Code <claude-code@anthropic.com>

    * fix: Add CodeQL badge and fix dependency-security workflow condition (#23)

    This commit addresses two issues:

    1. **CodeQL Badge**: Add CodeQL badge to README.md CI/CD Status section
       - Badge links to GitHub Security Code Scanning page
       - Provides visibility into CodeQL analysis status

    2. **Workflow Fix**: Fix dependency-security job condition in security-analysis.yml
       - Change from `!= 'schedule'` to `== 'pull_request'`
       - Prevents job from running on workflow_dispatch events
       - GitHub Dependency Review Action requires PR context (base_ref/head_ref)
       - Resolves error: "Both a base ref and head ref must be provided"

    The dependency-security job now only runs during pull_request events where
    the required git references are available.

    Fixes: #128 (workflow run failure)

    Co-authored-by: Claude <noreply@anthropic.com>

    * feat: Implement comprehensive benchmarking and evaluation framework

    Implements the complete benchmarking infrastructure for Phases 1-3 of the
    Image Preprocessing Detector, providing standardized evaluation across
    layout detection, IQA, tables, handwriting, and language identification.

    ## Core Components

    ### 1. Registry System (benchmarks/registry.yml)
    - Centralized configuration for 30+ benchmark suites
    - Phase-aligned suites (Phase 1: IQA + DocLayNet, Phase 2-3: ML tasks)
    - Smoke test subsets for fast CI validation
    - Target metrics with paper baselines

    ### 2. Dataset Adapters (benchmarks/adapters/)
    - BaseAdapter interface with PageSample dataclass
    - Synthetic IQA adapter (blur, skew, noise, contrast, binarization)
    - DocLayNet adapter (11-class layout detection, doc-wise splits)
    - DatasetRegistry for dynamic loading

    ### 3. Metrics Modules (benchmarks/metrics/)
    - **Image Quality (image_metrics.py)**:
      - Blur: Pearson correlation ≥ 0.85, RMSE ≤ 0.05
      - Skew: MAE ≤ 0.5°, deskew success ≥ 99%
      - Noise: SNR improvement ≥ 6 dB
      - Quality: PSNR ≥ 30 dB, SSIM ≥ 0.9
      - Binarization: F-measure ≥ 0.95
    - **Detection (detection_metrics.py)**:
      - COCO-style mAP@[.5:.95]
      - Per-class AP, precision, recall, F1
      - IoU calculations

    ### 4. Scorers (benchmarks/scorers/)
    - AggregateScorer: Statistics, summaries, pass/fail status
    - Outputs: JSON results + Markdown summaries

    ### 5. Runners (benchmarks/runners/)
    - **run_benchmark.py**: Full benchmark execution
    - **run_smoke.py**: Fast CI smoke tests (<5 min)
    - Environment-aware (BENCHMARKS_DATA_DIR, etc.)

    ### 6. Schema Extensions (src/.../schema.py)
    - OmniDocBench attributes (data_source, layout, language, etc.)
    - ElementRelation: Parent-child relationships
    - ReadingOrder: Reading order graphs
    - Backward compatible with existing schema

    ### 7. Label Mapping (benchmarks/labelmaps/)
    - OmniDocBench → DocLayNet 11-class mapping
    - Handles ambiguous mappings (code_txt, references)
    - YAML-based configuration

    ## Testing

    - Unit tests for image and detection metrics (tests/benchmarks/)
    - Test coverage for blur, skew, noise, binarization, IoU, mAP
    - Pytest markers ready for extended testing

    ## Documentation

    - Comprehensive README (benchmarks/README.md)
    - License compliance tracking (benchmarks/LICENSES.md)
    - Dataset licenses: CDLA-Permissive, CC-BY-4.0, CC-BY-NC-4.0
    - Usage examples and troubleshooting

    ## Phase Roadmap

    **Phase 1 (Complete)**:
    - Base adapter interface ✓
    - Synthetic IQA adapter ✓
    - DocLayNet adapter ✓
    - IQA metrics (FR-3.1 → FR-3.7) ✓
    - Detection metrics (mAP, IoU) ✓
    - Benchmark runners ✓

    **Phase 2 (Planned)**:
    - TableBank, FinTabNet, COCO-Text, WiLI-2018 adapters
    - TEDS scorer for table structure
    - ML model integration (YOLOv8, MobileNetV3)

    **Phase 3 (Planned)**:
    - OmniDocBench end-to-end evaluation
    - Composite scoring (layout + text + table + formula)
    - Attribute-sliced evaluation
    - Production throughput benchmarks

    ## Usage

    ```bash
    # Generate synthetic test data
    python -m benchmarks.runners.run_benchmark --suite synthetic-iqa-blur-smoke

    # Run all smoke tests (CI)
    python -m benchmarks.runners.run_smoke --all

    # Full DocLayNet benchmark (requires dataset)
    python -m benchmarks.runners.run_benchmark --suite doclaynet-layout-full
    ```

    ## Integration Notes

    - Compatible with existing IQA modules (detection/, correction/)
    - Schema extensions are optional (backward compatible)
    - CI-ready (smoke tests designed for GitHub Actions)
    - Extensible architecture for future tasks

    Resolves: Phase 1 benchmarking requirements
    Related: PROJECT_PLAN.md sections on evaluation

    SPDX-License-Identifier: Apache-2.0

    * docs: Add comprehensive benchmark comparison tables and status badges

    Add detailed benchmark comparison section including:
    - Status badges (Phase 1 Complete, IQA Implemented, etc.)
    - Quick metrics summary table with current status
    - Comparison with SOTA tools (Marker, Docling, MinerU, Mathpix, GPT-4o)
    - OmniDocBench end-to-end scores from paper (Table 2)
    - Attribute-sliced performance targets
    - Handwriting, language ID, and throughput benchmarks
    - Instructions for running benchmarks and viewing results

    Tables show:
    - Our ambitious targets (composite ≥ 85.0 vs Mathpix 82.65)
    - Current TBD status with phase indicators
    - Paper baselines and references
    - License info for each tool

    Provides clear comparison context similar to OmniDocBench leaderboard
    format while showing our development roadmap.

    Related: OmniDocBench arXiv:2412.07626

    * feat: Add automated benchmark results update system

    Implements automated system for updating benchmark results in README
    with GitHub Actions integration and dynamic badge generation.

    ## New Components

    ### 1. Update Scripts
    - **update_readme.py**: Parses latest results and updates README tables
    - **generate_badges.py**: Creates shields.io endpoint JSON badges
    - **aggregate.py**: Combines multiple runs into comparative reports

    ### 2. GitHub Actions Workflow
    - **benchmark-results.yml**: Automated nightly benchmark runs
      - Runs all synthetic IQA benchmarks
      - Updates README with latest results
      - Generates dynamic badges
      - Commits changes back to repo
      - Runs smoke tests on PRs

    ### 3. Documentation
    - **AUTO_UPDATE.md**: Complete guide to automated update system
      - How it works (automatic + manual flows)
      - Configuration and troubleshooting
      - Badge usage and customization
      - Best practices and FAQ

    ## Features

    **Automatic Updates**:
    - Nightly runs at 2 AM UTC
    - Updates Quick Metrics Summary table
    - Color-coded status icons (✓, ✗, 🔄, ⏳)
    - Commits with [skip ci] to prevent loops

    **Dynamic Badges**:
    - Shields.io compatible JSON endpoints
    - Color-coded: green (pass), yellow (warn), red (fail)
    - Per-metric badges (blur, skew, PSNR, etc.)
    - Overall summary badge (X/Y passing)

    **Manual Updates**:
    ```bash
    # Run benchmarks
    python -m benchmarks.runners.run_benchmark --suite synthetic-iqa-blur-full

    # Update README
    python -m benchmarks.runners.update_readme

    # Generate badges
    python -m benchmarks.runners.generate_badges

    # Aggregate reports
    python -m benchmarks.runners.aggregate --format all
    ```

    **Aggregate Reports**:
    - CSV: Cross-suite comparison
    - Markdown: Human-readable reports
    - JSON: Machine-readable data
    - Historical trend tracking

    ## Workflow Triggers

    1. **Schedule**: Nightly at 2 AM UTC
    2. **Manual**: GitHub Actions UI (workflow_dispatch)
    3. **Push**: Changes to benchmarks/ or src/
    4. **PR**: Smoke tests only (<10 min)

    ## Badge Examples

    ![IQA Blur](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/williaby/image-preprocessing-detector/main/.github/badges/blur-correlation.json)

    ![Benchmarks](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/williaby/image-preprocessing-detector/main/.github/badges/summary.json)

    ## Integration

    - Compatible with existing benchmark runners
    - Non-breaking additions to framework
    - Extensible for new metrics and suites
    - CI/CD ready with artifact retention

    Related: #benchmarks #automation #ci-cd

    * feat: Integrate detection modules with benchmarking framework

    Completed Steps 1-4 of the integration layer, connecting existing
    classical IQA detectors with the benchmarking and evaluation pipeline.

    **Integration Layer (benchmarks/tasks/iqa.py)**:
    - Created task plugin to orchestrate detector-metric connections
    - Implemented 5 IQA benchmark workflows:
      * run_blur_benchmark(): BlurDetector → blur_correlation/blur_rmse
      * run_skew_benchmark(): SkewDetector + correct_skew → MAE/success_rate
      * run_noise_benchmark(): OpenCV denoising → PSNR/SSIM/SNR
      * run_contrast_benchmark(): enhance_contrast → enhancement_ratio
      * run_binarization_benchmark(): Otsu → F-measure
    - All benchmarks integrate detection, correction, and metrics modules

    **Runner Updates**:
    - Modified run_benchmark.py to delegate IQA tasks to task plugin
    - Enabled auto-download for synthetic datasets
    - Fixed dataset adapter registration in __init__.py

    **Dependencies**:
    - Added pyyaml, scipy, scikit-image to dev dependencies
    - Installed package in editable mode for proper imports

    **Dataset Adapter Fixes**:
    - Fixed SyntheticIQAAdapter to create data_dir when download=True
    - Changed super().__init__ to pass download parameter correctly

    **Validation Results**:
    - Blur benchmark: Correlation 0.683, RMSE 2.314 (9 samples)
    - Skew benchmark: MAE 0.0°, Success rate 100% (9 samples)
    - Auto-update system verified functional

    **What Works**:
    - Synthetic dataset auto-generation
    - Detection module execution
    - Metric calculation and aggregation
    - Results persistence to reports/ directory
    - Summary generation

    **Next Steps**:
    - Run full benchmark suites (not just smoke tests)
    - Test DocLayNet layout benchmark with user's dataset
    - Verify GitHub Actions workflow for nightly runs
    - Generate badges with real results

    Related: Phase 1 benchmarking implementation

    * feat: Add automated benchmark results update system

    Implemented comprehensive infrastructure for auto-updating README with
    benchmark results using a local-first workflow to handle large datasets.

    **Architecture Update**:
    - Changed from CI-based benchmarking to local-first approach
    - GitHub Actions now only updates README from committed results
    - Datasets stay local (gitignored, too large for GitHub)
    - Only small JSON results (5-50KB) committed to git

    **GitHub Actions Workflow** (.github/workflows/benchmark-results.yml):
    - Renamed job: run-benchmarks → update-readme
    - Removed benchmark execution steps (requires local datasets)
    - Triggers on: push to reports/**/*.json
    - Only updates README from committed results
    - Generates badges and commits README updates
    - Timeout reduced: 60min → 10min (no heavy computation)

    **Documentation** (benchmarks/AUTO_UPDATE.md):
    - Complete rewrite explaining local-first workflow
    - Step-by-step guide: Run locally → Commit results → CI updates
    - Troubleshooting guide for common issues
    - Best practices for commit messages and dataset organization
    - FAQ covering dataset sharing, result management, multi-machine setup
    - Workflow diagrams and examples

    **Update Scripts**:
    - update_readme.py: Parses reports/*.json, updates Quick Metrics table
    - generate_badges.py: Creates shields.io endpoint JSON files
    - aggregate.py: Combines multiple runs for trend analysis

    **Why Local-First**:
    1. Datasets too large for GitHub:
       - DocLayNet: 11GB
       - PubMedQA: 2.1GB
       - GitHub limit: 100MB per file, slow at >1GB
    2. Results are tiny:
       - JSON files: 5-50KB each
       - Safe to commit and version control
    3. CI doesn't need datasets:
       - Only parses committed JSON
       - Fast execution (<2 minutes)
       - Works on GitHub free tier

    **Workflow**:
    1. Developer runs benchmarks locally with datasets
    2. Commits small JSON results to reports/
    3. CI detects new results, updates README automatically
    4. Pushes README changes with [skip ci]

    **Benefits**:
    - Repository stays small (<100MB)
    - Fast clone times
    - CI runs quickly
    - Results version controlled
    - README always current
    - Works across multiple machines

    Related: Phase 1 benchmarking infrastructure

    * docs: Add benchmark dataset installation guide

    Created comprehensive documentation for downloading and setting up
    benchmark datasets locally (gitignored, not committed to GitHub).

    **Contents**:
    - Quick reference table with dataset sizes and download links
    - Installation instructions for each dataset:
      * Synthetic IQA: Auto-generated (no manual download)
      * DocLayNet: 11GB manual download with citation requirements
      * PubMedQA: 2.1GB optional download
    - Directory structure and organization guidelines
    - Gitignore explanation (datasets local, results committed)
    - Instructions for adding custom datasets
    - License information and attribution requirements
    - Troubleshooting guide for common issues

    **Key Info**:
    - DocLayNet: CC BY 4.0, requires citation
    - Synthetic IQA: Public domain, auto-generated
    - All datasets gitignored to keep repo small
    - Only results JSON files committed (5-50KB each)

    Related: Local-first benchmarking architecture

    * chore: Add missing tags to front matter allow-list

    Add tags required by PR #21 documentation:
    - Project Management: reconciliation, pr_review, requirements, specifications, functional, non_functional
    - Infrastructure: production
    - Technical: routing, scoring, pipeline_selection

    This enables validation to pass for:
    - ADR-0028 (Document Quality Score routing)
    - PR 14-15 Reconciliation guide
    - Functional Requirements v2.0

    Related: #21

    🤖 Generated with [Claude Code](https://claude.com/claude-code)

    Co-Authored-By: Claude <noreply@anthropic.com>

    * fix: Resolve benchmarking framework dependency conflicts

    - Disabled genalog dependency (conflicts with modern scipy/scikit-image)
    - Added scikit-image ^0.25.2 to dev dependencies for benchmarking PSNR/SSIM
    - Added junit.xml to .gitignore
    - Updated README and CHANGELOG to reflect file reorganization
    - File reorganization: moved project docs to docs/project/, docs/phases/, docs/reference/

    **Genalog Conflict Resolution:**
    - genalog 0.1.0 (2021) requires matplotlib 3.2.1 and scikit-image 0.16.2
    - Benchmarking framework requires scipy ^1.16.3 and scikit-image ^0.25.2
    - Solution: Disabled genalog temporarily (optional ml dependency)
    - TODO: Find alternative synthetic degradation library or fork genalog for Phase 2

    **Verified:**
    - Benchmarking smoke test passes: synthetic-iqa-blur-smoke
    - PSNR and SSIM metrics working with scikit-image 0.25.2

    🤖 Generated with [Claude Code](https://claude.com/claude-code)

    Co-Authored-By: Claude <noreply@anthropic.com>

    * chore: Reorganize root directory for better maintainability

    - Move 18 documentation files to organized subdirectories
      - Phase docs → docs/project/phases/
      - Reviews → docs/reviews/
      - Setup guides → docs/setup/
      - Reference materials → docs/reference/
      - Scripts → scripts/

    - Delete 5 build artifacts (already in .gitignore)
      - coverage.xml, junit.xml, sbom-*.json

    - Update .gitignore to explicitly ignore junit.xml
    - Update documentation references in README.md and CHANGELOG.md

    Reduces root clutter from 46 to 24 essential files (48% reduction).
    All git history preserved via 'git mv' for tracked files.

    Note: Front matter validation skipped for moved files - will be fixed in follow-up commit.

    🤖 Generated with [Claude Code](https://claude.com/claude-code)

    Co-Authored-By: Claude <noreply@anthropic.com>

    * docs: Add comprehensive dataset installation guide

    - Created docs/DATASET_INSTALLATION.md with complete setup instructions
    - Updated data/benchmarks/README.md with quick reference
    - Documented all 10 benchmark datasets with installation steps
    - Added OmniDocBench setup (requires HuggingFace account due to rate limiting)
    - Included license compliance summary and citation requirements
    - Added troubleshooting section for common issues

    **Dataset Status:**
    ✅ doclaynet - Symlinked from data_ingestor (11GB)
    ✅ signatr6k - Present locally
    ✅ synthetic_iqa - Auto-generated on benchmark runs
    ✅ cocotext - Extracted (annotations only, 53MB)
    ⚠️ omnidocbench - Requires manual HF authentication (rate limited)
    ⏸️ Phase 2 datasets - Require manual download (TableBank, PubTabNet, etc.)

    **Total Space**: ~36GB (excluding symlinked doclaynet)

    🤖 Generated with [Claude Code](https://claude.com/claude-code)

    Co-Authored-By: Claude <noreply@anthropic.com>

    * style: Apply Ruff formatting to benchmarks and augmentation modules

    Applied Ruff formatting to ensure code style consistency across:
    - Benchmarks framework (adapters, metrics, runners, tasks)
    - Augmentation modules (genalog config and degrader)

    Also updated pre-commit config to exclude benchmarks/ from MyPy
    checks, aligning with CI workflow that only type-checks src/.

    This addresses formatting issues identified during CI validation
    and ensures all files meet project code quality standards.

    🤖 Generated with [Claude Code](https://claude.com/claude-code)

    Co-Authored-By: Claude <noreply@anthropic.com>

    * style: Fix non-critical Ruff warnings in benchmarks framework

    Comprehensive cleanup of code quality issues:

    **Fixed Issues:**
    - Shadowed builtin (A002): Renamed `format` parameter to `bbox_format`
    - Dict iteration (SIM118): Removed unnecessary `.keys()` calls
    - List concatenation (RUF005): Used iterable unpacking
    - Datetime timezone (DTZ005): Added UTC timezone to all datetime.now() calls
    - isinstance syntax (UP038): Updated to modern `X | Y` syntax in core modules
    - Unused variables (F841): Removed unused metadata variables in IQA tasks
    - __all__ sorting (RUF022): Alphabetically sorted augmentation exports

    **Configuration Updates:**
    - Added benchmarks logging infrastructure (utils/logging_config.py)
    - Configured Ruff to allow print statements in CLI tools (benchmarks/)
    - Added per-file ignores for benchmark utilities and placeholders
    - Preserved Phase 2 implementation placeholders in genalog_degrader.py

    **Test Results:**
    - All 266 tests pass with 87% coverage (exceeds 80% requirement)
    - All Ruff checks pass with updated configuration

    This maintains CLI usability while enforcing code quality standards
    in core application modules.

    🤖 Generated with [Claude Code](https://claude.com/claude-code)

    Co-Authored-By: Claude <noreply@anthropic.com>

    * feat: Migrate Phase 2-3 training to Google Colab Pro with 12-hour session management

    Implements complete infrastructure for training ML models on Google Colab Pro,
    optimized for 12-hour session limits with automatic checkpoint management.

    Infrastructure Components:
    - Checkpoint manager with auto-save/resume for 12-hour sessions
    - Google Drive sync utilities for dataset and model persistence
    - Colab environment utilities (GPU detection, optimization)
    - Training configurations for Phase 2 (IQA) and Phase 3 (YOLOv8)
    - Complete Jupyter notebooks for both training phases
    - Comprehensive 300+ line training guide

    Key Features:
    - Auto-saves every 5 epochs OR 30 minutes (whichever comes first)
    - Auto-stops at 11.5 hours (30min before session limit)
    - Seamless resume across multiple sessions
    - Multi-session training support for YOLOv8 (5-7 sessions)
    - Embedded TensorBoard monitoring
    - ONNX export for deployment

    Cost Optimization:
    - Phase 2: $12/month (1 month sufficient, 15-20 GPU hours)
    - Phase 3: $24 total (2 months, 50-80 GPU hours over 5-7 days)
    - 85% cost savings vs AWS/GCP GPU hourly rates

    Files Added:
    - scripts/checkpoint_manager.py: Session-aware checkpoint system
    - scripts/gdrive_sync.py: Google Drive integration
    - scripts/colab_utils.py: Colab environment helpers
    - configs/colab_phase2_iqa.yaml: Phase 2 training config
    - configs/colab_phase3_yolov8.yaml: Phase 3 training config
    - notebooks/colab/phase2_iqa_training.ipynb: IQA training workflow
    - notebooks/colab/phase3_yolov8_training.ipynb: YOLOv8 training workflow
    - docs/COLAB_TRAINING_GUIDE.md: Complete training guide

    Files Modified:
    - PROJECT_PLAN.md: Updated Phase 2 & 3 with Colab workflows
    - pyproject.toml: Added [colab] dependency group

    Addresses: Phase 2-3 training platform migration from local to cloud

    * chore: Add Phase 2 infrastructure with ML dependencies and data processing modules

    - Add ML dependencies for Phase 2 training (DVC, PyTorch, Celery, HuggingFace)
    - Create data processing modules (augmentation, weak supervision)
    - Add Google Colab vs HF Spaces comparison documentation
    - Add hardware configuration and data collection strategy docs
    - Fix benchmarks imports to use relative imports
    - Configure pytest pythonpath for better module resolution
    - Add coverage exclusions for benchmarks and data directories
    - Exclude data/ directory from mypy pre-commit checks

    🤖 Generated with [Claude Code](https://claude.com/claude-code)

    Co-Authored-By: Claude <noreply@anthropic.com>

    * chore: Add zip files to data/test gitignore pattern

    * docs: Align Phase 2 plan with Google Colab training migration

    - Add prominent training platform update notice at top of document
    - Reference Google Colab Pro notebooks and COLAB_TRAINING_GUIDE.md
    - Update infrastructure section with Colab-specific requirements
    - Clarify document focuses on methodology while Colab guide covers infrastructure
    - Add quick links to training notebook, guide, and configuration

    This ensures consistency with PROJECT_PLAN.md which was already updated
    for the Google Colab migration (commit f94b987).

    🤖 Generated with [Claude Code](https://claude.com/claude-code)

    Co-Authored-By: Claude <noreply@anthropic.com>

    * docs: Add Google Cloud Storage configuration for Phase 2 training

    - Add comprehensive Colab storage setup guide with dual storage strategy
    - Create GCS-specific training configuration (colab_phase2_iqa_gcs.yaml)
    - Document project-specific setup (image-detection-478105, gs://image_detection_b)
    - Include hybrid workflow: Google Drive for training, GCS for backup/production
    - Add cost comparison, troubleshooting, and quick start checklist

    Project Details:
    - GCP Project: image-detection (ID: image-detection-478105)
    - GCS Bucket: image_detection_b
    - Storage Strategy: Drive (primary) + GCS (backup/production)

    🤖 Generated with [Claude Code](https://claude.com/claude-code)

    Co-Authored-By: Claude <noreply@anthropic.com>

    * docs: Prioritize GCS over Google Drive for security

    BREAKING: Reorder storage options to recommend GCS as primary method

    Security Changes:
    - Add prominent warning about Google Drive full access requirement
    - Move GCS to Option 1 (recommended) with detailed quick start
    - Demote Google Drive to Option 2 (alternative)
    - Add 5-step GCS-only workflow that avoids Drive access entirely

    Rationale:
    - Google Drive mounting requires full access to all personal files
    - GCS provides better security isolation (bucket-level permissions)
    - User already has GCS bucket configured (gs://image_detection_b)
    - More cost-effective ($0.50 vs $2/month)
    - Better suited for ML training workflows

    🤖 Generated with [Claude Code](https://claude.com/claude-code)

    Co-Authored-By: Claude <noreply@anthropic.com>

    * docs: Add comprehensive dataset structure for all phases

    - Remove invalid gsutil mkdir commands (GCS doesn't support empty directories)
    - Add detailed file structure for Phase 2 (IQA) and Phase 3 (YOLOv8)
    - Document dataset sources and preparation steps for each phase
    - Include expected file counts and storage sizes
    - Reference DATASET_INSTALLATION.md for base dataset downloads
    - Reference Phase 2/3 plan docs for data preparation workflows

    Phase 2 Structure:
    - train/val/test splits with images/ and labels.json
    - ~50,000 total images (~10GB)
    - Sources: RVL-CDIP, DocBank, Tobacco800 + synthetic augmentation

    Phase 3 Structure:
    - train/val/test splits with images/ and labels/ (YOLO format)
    - ~200,000+ total images (~40-50GB)
    - Sources: PubLayNet, DocLayNet, TableBank

    🤖 Generated with [Claude Code](https://claude.com/claude-code)

    Co-Authored-By: Claude <noreply@anthropic.com>

    * chore: Add GCS service account key patterns to gitignore

    Prevent accidental commit of sensitive credentials:
    - *.b64 (base64 encoded keys)
    - *.json.b64
    - *service-account*.json

    🤖 Generated with [Claude Code](https://claude.com/claude-code)

    Co-Authored-By: Claude <noreply@anthropic.com>

    * docs: Add Phase 2 dataset preparation and testing documentation

    Added comprehensive documentation for Phase 2 IQA training:

    - DATASET_PREPARATION.md: Dataset structure, GCS workflow, validation
    - PHASE2_QUICKSTART.md: Quick reference for Phase 2 setup
    - TESTING_STRATEGY.md: Comprehensive testing strategy (3-tier)
    - Updated DATASET_INSTALLATION.md with external IQA datasets
    - Updated PUBLIC_DATASET_COVERAGE.md with Phase 2 benchmarks
    - Updated colab-storage-setup.md with GCS integration
    - Updated benchmarks/README.md with dataset registry

    Documentation supports:
    - 50k synthetic samples with weak supervision
    - 3 external IQA validation datasets (LIVE, CSIQ, LIVE Challenge)
    - GCS-first storage strategy for Colab training
    - Test fixtures for CI/CD (< 50 MB)

    Note: Front matter validation will be fixed in follow-up commit

    🤖 Generated with [Claude Code](https://claude.com/claude-code)

    Co-Authored-By: Claude <noreply@anthropic.com>

    * feat: Add Phase 2 dataset generation and GCS upload scripts

    Added comprehensive scripts for Phase 2 IQA dataset pipeline:

    Dataset Generation:
    - prepare_phase2_data.py: Generate 50k synthetic samples with weak supervision
      - Albumentations augmentation (medium preset)
      - Classical IQA labeling (BRISQUE, Laplacian, Hough transform)
      - 70/15/15 train/val/test split

    External Dataset Downloads:
    - download_iqa_datasets.py: LIVE, CSIQ, LIVE Challenge (5 GB, 2,807 images)
    - download_omnidocbench.py: Document understanding benchmark
    - download_table_datasets.py: TableBank dataset downloader

    GCS Integration:
    - upload_datasets_to_gcs.sh: Batch upload to Google Cloud Storage
    - auth_gcs.sh: GCS authentication helper with service account
    - gcs_helpers.sh: Reusable GCS utility functions
    - validate_datasets.py: Dataset integrity validation

    Workflow:
    1. Generate synthetic data (50k samples, ~20 GB)
    2. Download external IQA validation datasets (~5 GB)
    3. Validate dataset structure and labels
    4. Upload to GCS for Colab Pro training

    Note: Linting issues (ruff, mypy, bandit) will be fixed in follow-up

    🤖 Generated with [Claude Code](https://claude.com/claude-code)

    Co-Authored-By: Claude <noreply@anthropic.com>

    * test: Add test fixtures infrastructure and real-world integration tests

    Added comprehensive test fixtures for CI/CD testing without full datasets:

    Test Fixtures (828 KB total, well under 50 MB limit):
    - doclaynet/: 5 PDFs (432 KB) - layout detection samples
    - tablebank/: 5 images (324 KB) - table detection samples
    - wili_2018/: 10 text files (52 KB) - language ID samples
    - cocotext/: Empty (requires extraction)
    - omnidocbench/: Empty (requires Arrow format handling)

    Extraction Scripts:
    - extract_test_fixtures.py: Automated extraction from full datasets
    - extract_wili_samples.py: Language-specific sample extractor

    Testing Infrastructure:
    - tests/conftest.py: Pytest fixtures and markers
    - tests/integration/test_real_fixtures.py: 14 real-world integration tests

    pytest Markers:
    - @pytest.mark.requires_full_dataset: Skipped in CI
    - @pytest.mark.real_data: Tests with real fixtures

    Benefits:
    - Fast CI/CD: No 88+ GB dataset downloads
    - Offline development: Work without internet
    - Reproducible tests: Same fixtures across environments

    Note: Linting fixes needed (ruff, mypy, bandit issues)
    Next: Extract cocotext and omnidocbench fixtures

    🤖 Generated with [Claude Code](https://claude.com/claude-code)

    Co-Authored-By: Claude <noreply@anthropic.com>

    * docs: Document planned IQA test fixtures for Phase 2 Week 3

    Updated test fixtures README to document planned IQA fixtures:

    Planned IQA Fixtures (~2 MB):
    - live/: 5 LIVE dataset samples with ground-truth DMOS scores
      - Reference (clean, DMOS=0.0)
      - JPEG compression (DMOS~25)
      - Gaussian blur (DMOS~45)
      - White noise (DMOS~38)
      - Low contrast (DMOS~52)
    - synthetic/: 3 generated variants for edge cases
      - Extreme blur
      - Combined defects (blur + noise)
      - Rotated/skewed document
    - labels.json: Ground-truth quality scores

    Projected Impact:
    - Current size: 828 KB
    - After IQA fixtures: 3.0 MB (still well under 50 MB limit)

    License Compliance:
    - LIVE dataset: Academic/Research license
    - Requires citation in project documentation
    - Research use allowed with proper attribution

    Timeline: Week 3 (after Phase 2 training complete)

    Reference: tmp_cleanup/.tmp-test-fixtures-iqa-requirements-20251113.md

    🤖 Generated with [Claude Code](https://claude.com/claude-code)

    Co-Authored-By: Claude <noreply@anthropic.com>

    * docs: Add ADR-029 and ADR-030 for Phase 2 dataset and infrastructure strategy

    Added two Architecture Decision Records documenting critical Phase 2 decisions:

    ADR-029: Phase 2 Dataset Selection Strategy
    - Three-tier dataset approach: 50k synthetic training + external validation + test fixtures
    - Weak supervision using classical IQA algorithms (BRISQUE, Laplacian, Hough transform)
    - External validation datasets: LIVE, CSIQ, LIVE Challenge (~2,807 images, ground-truth quality scores)
    - Test fixtures: 8 samples (~2 MB) for CI/CD testing without 88+ GB downloads
    - Dataset coverage: blur, noise, skew, perspective, low_contrast, orientation
    - Cost analysis: $0 training data (synthetic) vs. $5k-$25k manual annotation
    - Code support: prepare_phase2_data.py, download_iqa_datasets.py, extract_iqa_fixtures.py

    ADR-030: GCS and Colab Pro Training Workflow
    - GCS-first storage strategy replacing Google Drive for security and performance
    - Google Colab Pro for GPU training (T4/V100/A100, 24-hour runtime)
    - Cost efficiency: $10.52/month vs. $100-$200/month for dedicated GPU instances
    - Performance: 50-100 MB/s GCS transfers vs. 5-10 MB/s Google Drive sync
    - Security: Service account isolation, no credential exposure
    - Code support: auth_gcs.sh, upload_datasets_to_gcs.sh, gcs_helpers.sh

    Both ADRs include comprehensive alternatives analysis, implementation details,
    consequences, and validation strategies.

    NOTE: Committed with --no-verify. Front matter tags (phase_2, dataset, weak_supervision,
    infrastructure, gcs, colab) need to be added to allowed tags registry in follow-up.

    Related: ADR-022 (Synthetic Data), ADR-023 (Weak Supervision), ADR-024 (Active Learning),
    ADR-025 (MobileNetV3), ADR-027 (ONNX Quantization)

    🤖 Generated with [Claude Code](https://claude.com/claude-code)

    Co-Authored-By: Claude <noreply@anthropic.com>

    * docs: Add ADR-031 for comprehensive benchmarking framework

    Added Architecture Decision Record documenting the registry-based benchmarking frame

... [stdout truncated: output exceeded 50000 characters (123822 total). Please modify your command to reduce output size, for example by:
- Using grep/rg to filter results
- Using head/tail to limit lines
- Using --max-count flag with grep/rg
- Processing output with awk/sed to extract only needed information]
````

</shell_result>

---

Script executed:

```shell
#!/bin/bash
# Look for detailed git history and previous implementations
echo "=== Searching git history for _update_summary_for_status ==="
git log --all -S "required_missing" --oneline -- scripts/validate_datasets.py

echo -e "\n=== Get the full git log with diffs ==="
git log --all -p -- scripts/validate_datasets.py 2>/dev/null | head -500

echo -e "\n=== Check config structure for required field ==="
sed -n '33,100p' scripts/validate_datasets.py
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stdout:

```
=== Searching git history for _update_summary_for_status ===
9845e94 chore: add markdownlint and yamllint configs with 120 char line length
d59091d Phase 1 MVP Completion: Ready for Phase 2 (#30)

=== Get the full git log with diffs ===
commit 9845e94c2bf7042a6cac2591682eb2ae5cbf2e4a
Author: Byron Williams <byronawilliams@gmail.com>
Date:   Tue Nov 25 15:17:29 2025 -0800

    chore: add markdownlint and yamllint configs with 120 char line length

    - Add .markdownlint.yaml with 120 char line length (matching project standards)
    - Add .yamllint.yaml with 120 char line length and relaxed truthy rules
    - Remove deprecated .hadolint.yaml and .shellcheckrc (qlty uses defaults)

    🤖 Generated with [Claude Code](https://claude.com/claude-code)

    Co-Authored-By: Claude <noreply@anthropic.com>

diff --git a/scripts/validate_datasets.py b/scripts/validate_datasets.py
new file mode 100755
index 0000000..2188287
--- /dev/null
+++ b/scripts/validate_datasets.py
@@ -0,0 +1,429 @@
+# SPDX-FileCopyrightText: 2024 Byron Williams <byronawilliams@gmail.com>
+# SPDX-License-Identifier: MIT
+
+#!/usr/bin/env python3
+"""
+Dataset Validation Script
+
+Validates that all required datasets are present locally and checks their status
+against the DATASET_INSTALLATION.md requirements.
+
+Usage:
+    python scripts/validate_datasets.py
+    python scripts/validate_datasets.py --upload-to-gcs
+"""
+
+import argparse
+import json
+import logging
+import os
+import sys
+from pathlib import Path
+
+# Setup logging
+logging.basicConfig(
+    level=logging.INFO,
+    format="%(asctime)s - %(levelname)s - %(message)s",
+    datefmt="%Y-%m-%d %H:%M:%S",
+)
+logger = logging.getLogger(__name__)
+
+
+# Expected datasets configuration
+EXPECTED_DATASETS = {
+    "benchmarks": {
+        "doclaynet": {
+            "path": "benchmarks/doclaynet",
+            "type": "symlink",
+            "target": "/home/byron/dev/data_ingestor/data/benchmarks/doclaynet",
+            "phase": 1,
+            "required": True,
+            "description": "DocLayNet layout detection dataset",
+        },
+        "signatr6k": {
+            "path": "benchmarks/signatr6k",
+            "type": "directory",
+            "phase": "?",
+            "required": False,
+            "description": "Signature detection dataset",
+        },
+        "synthetic_iqa": {
+            "path": "benchmarks/synthetic_iqa",
+            "type": "directory",
+            "phase": 1,
+            "required": True,
+            "description": "Synthetic IQA dataset (auto-generated)",
+        },
+        "cocotext": {
+            "path": "benchmarks/cocotext",
+            "type": "directory",
+            "phase": 2,
+            "required": False,
+            "description": "COCO-Text annotations",
+        },
+        "omnidocbench": {
+            "path": "benchmarks/omnidocbench",
+            "type": "directory",
+            "phase": 3,
+            "required": False,
+            "description": "OmniDocBench multi-task benchmark",
+        },
+        "tablebank": {
+            "path": "benchmarks/tablebank",
+            "type": "directory",
+            "phase": 2,
+            "required": False,
+            "description": "TableBank table detection dataset",
+        },
+        "pubtabnet": {
+            "path": "benchmarks/pubtabnet",
+            "type": "directory",
+            "phase": 2,
+            "required": False,
+            "description": "PubTabNet table structure dataset",
+        },
+        "fintabnet": {
+            "path": "benchmarks/fintabnet",
+            "type": "directory",
+            "phase": 2,
+            "required": False,
+            "description": "FinTabNet financial table dataset",
+        },
+        "wili_2018": {
+            "path": "benchmarks/wili_2018",
+            "type": "directory",
+            "phase": 2,
+            "required": False,
+            "description": "WiLI language identification dataset",
+        },
+    },
+    "raw": {
+        "docbank": {
+            "path": "raw/docbank",
+            "type": "directory",
+            "phase": 1,
+            "required": False,
+            "description": "DocBank raw data",
+        },
+        "rvl-cdip": {
+            "path": "raw/rvl-cdip",
+            "type": "directory",
+            "phase": 1,
+            "required": False,
+            "description": "RVL-CDIP document classification",
+        },
+        "tobacco800": {
+            "path": "raw/tobacco800",
+            "type": "directory",
+            "phase": 1,
+            "required": False,
+            "description": "Tobacco800 document classification",
+        },
+    },
+}
+
+
+def get_directory_size(path: Path) -> int:
+    """Calculate directory size in bytes."""
+    total_size = 0
+    try:
+        for item in path.rglob("*"):
+            if item.is_file():
+                total_size += item.stat().st_size
+    except Exception as e:
+        logger.warning(f"Error calculating size for {path}: {e}")
+        return 0
+    return total_size
+
+
+def format_size(bytes_size: int) -> str:
+    """Format bytes to human-readable size."""
+    for unit in ["B", "KB", "MB", "GB", "TB"]:
+        if bytes_size < 1024.0:
+            return f"{bytes_size:.2f} {unit}"
+        bytes_size /= 1024.0
+    return f"{bytes_size:.2f} PB"
+
+
+def count_files(path: Path, pattern: str = "*") -> int:
+    """Count files matching pattern in directory."""
+    try:
+        return len(list(path.rglob(pattern)))
+    except Exception:
+        return 0
+
+
+def validate_dataset(
+    _dataset_name: str, config: dict, data_root: Path
+) -> tuple[str, dict]:
+    """
+    Validate a single dataset.
+
+    Returns:
+        Tuple of (status, details_dict)
+        status: 'found', 'missing', 'symlink_broken', 'empty'
+    """
+    dataset_path = data_root / config["path"]
+
+    # Check if exists
+    if not dataset_path.exists():
+        return "missing", {
+            "path": str(dataset_path),
+            "required": config["required"],
+            "phase": config["phase"],
+        }
+
+    # Check if symlink
+    if dataset_path.is_symlink():
+        target = dataset_path.resolve()
+        if not target.exists():
+            return "symlink_broken", {
+                "path": str(dataset_path),
+                "target": str(target),
+                "required": config["required"],
+                "phase": config["phase"],
+            }
+        # Symlink is valid
+        size = get_directory_size(target)
+        file_count = count_files(target)
+        return "found", {
+            "path": str(dataset_path),
+            "type": "symlink",
+            "target": str(target),
+            "size": size,
+            "size_human": format_size(size),
+            "file_count": file_count,
+            "required": config["required"],
+            "phase": config["phase"],
+        }
+
+    # Regular directory
+    if dataset_path.is_dir():
+        size = get_directory_size(dataset_path)
+        file_count = count_files(dataset_path)
+
+        # Check if empty
+        if file_count == 0:
+            return "empty", {
+                "path": str(dataset_path),
+                "required": config["required"],
+                "phase": config["phase"],
+            }
+
+        return "found", {
+            "path": str(dataset_path),
+            "type": "directory",
+            "size": size,
+            "size_human": format_size(size),
+            "file_count": file_count,
+            "required": config["required"],
+            "phase": config["phase"],
+        }
+
+    return "unknown", {
+        "path": str(dataset_path),
+        "required": config["required"],
+        "phase": config["phase"],
+    }
+
+
+def _update_summary_for_status(
+    results: dict, status: str, details: dict, config: dict, name: str
+) -> None:
+    """Update summary counters based on dataset status."""
+    status_map = {
+        "found": "found",
+        "missing": "missing",
+        "empty": "empty",
+        "symlink_broken": "broken",
+    }
+    if status in status_map:
+        results["summary"][status_map[status]] += 1
+        if status == "found":
+            results["summary"]["total_size"] += details.get("size", 0)
+        elif status in ("missing", "symlink_broken") and config["required"]:
+            results["required_missing"].append(name)
+
+
+def _validate_dataset_category(
+    category: str, datasets: dict, data_root: Path, results: dict
+) -> None:
+    """Validate all datasets in a category and update results."""
+    for name, config in datasets.items():
+        results["summary"]["total"] += 1
+        status, details = validate_dataset(name, config, data_root)
+        results[category][name] = {
+            "status": status,
+            "details": details,
+            "description": config["description"],
+        }
+        _update_summary_for_status(results, status, details, config, name)
+
+
+def validate_all_datasets(data_root: Path) -> dict:
+    """Validate all expected datasets."""
+    results = {
+        "summary": {
+            "total": 0,
+            "found": 0,
+            "missing": 0,
+            "empty": 0,
+            "broken": 0,
+            "total_size": 0,
+        },
+        "benchmarks": {},
+        "raw": {},
+        "required_missing": [],
+    }
+
+    _validate_dataset_category(
+        "benchmarks", EXPECTED_DATASETS["benchmarks"], data_root, results
+    )
+    _validate_dataset_category("raw", EXPECTED_DATASETS["raw"], data_root, results)
+
+    return results
+
+
+def _get_status_display(
+    status: str, details: dict, include_type: bool = True
+) -> tuple[str, str, str]:
+    """Get display info for a dataset status."""
+    status_info = {
+        "found": (
+            "✅",
+            f" ({details.get('size_human', '')}, {details.get('file_count', 0)} files)",
+            f" [{details.get('type', '')}]" if include_type else "",
+        ),
+        "missing": ("❌", "", ""),
+        "empty": ("⚠️", " (empty directory)", ""),
+        "symlink_broken": ("🔗", " (broken symlink)", ""),
+    }
+    return status_info.get(status, ("❓", "", ""))
+
+
+def _print_dataset_entry(
+    name: str, info: dict, show_required: bool = True, show_type: bool = True
+) -> None:
+    """Print a single dataset entry."""
+    status = info["status"]
+    details = info["details"]
+    emoji, size_info, type_info = _get_status_display(status, details, show_type)
+
+    required_marker = " [REQUIRED]" if show_required and details.get("required") else ""
+    phase_info = f" [Phase {details.get('phase', '?')}]"
+
+    print(
+        f"  {emoji} {name:<20} {status:<15}{size_info}{type_info if show_type else ''}{phase_info}{required_marker}"
+    )
+    print(f"     {info['description']}")
+    if status == "found" and details.get("type") == "symlink":
+        print(f"     → {details.get('target', '')}")
+
+
+def print_validation_report(results: dict):
+    """Print formatted validation report."""
+    print("\n" + "=" * 80)
+    print("DATASET VALIDATION REPORT")
+    print("=" * 80)
+
+    # Summary
+    summary = results["summary"]
+    print("\n📊 SUMMARY")
+    print("-" * 80)
+    print(f"Total datasets expected: {summary['total']}")
+    print(f"✅ Found: {summary['found']}")
+    print(f"❌ Missing: {summary['missing']}")
+    print(f"⚠️  Empty: {summary['empty']}")
+    print(f"🔗 Broken symlinks: {summary['broken']}")
+    print(f"💾 Total size: {format_size(summary['total_size'])}")
+
+    # Required missing
+    if results["required_missing"]:
+        print("\n❗ REQUIRED DATASETS MISSING:")
+        print("-" * 80)
+        for name in results["required_missing"]:
+            print(f"  - {name}")
+
+    # Benchmark datasets
+    print("\n📚 BENCHMARK DATASETS")
+    print("-" * 80)
+    for name, info in results["benchmarks"].items():
+        _print_dataset_entry(name, info, show_required=True, show_type=True)
+
+    # Raw datasets
+    print("\n📁 RAW DATASETS")
+    print("-" * 80)
+    for name, info in results["raw"].items():
+        _print_dataset_entry(name, info, show_required=False, show_type=False)
+
+    print("\n" + "=" * 80)
+
+
+def save_validation_json(results: dict, output_path: Path):
+    """Save validation results to JSON file."""
+    with open(output_path, "w") as f:
+        json.dump(results, f, indent=2)
+    logger.info(f"Validation results saved to: {output_path}")
+
+
+def main():
+    """Main entry point."""
+    parser = argparse.ArgumentParser(
+        description="Validate dataset presence and status",
+        formatter_class=argparse.RawDescriptionHelpFormatter,
+    )
+    parser.add_argument(
+        "--data-root", default="data", help="Root data directory (default: data)"
+    )
+    parser.add_argument("--output-json", help="Save validation results to JSON file")
+    parser.add_argument(
+        "--upload-to-gcs",
+        action="store_true",
+        help="Upload datasets to GCS after validation (not yet implemented)",
+    )
+
+    args = parser.parse_args()
+
+    # Get data root
+    if os.path.isabs(args.data_root):
+        data_root = Path(args.data_root)
+    else:
+        project_root = Path(__file__).parent.parent
+        data_root = project_root / args.data_root
+
+    if not data_root.exists():
+        logger.error(f"Data directory not found: {data_root}")
+        return 1
+
+    logger.info(f"Validating datasets in: {data_root.absolute()}")
+
+    # Validate all datasets
+    results = validate_all_datasets(data_root)
+
+    # Print report
+    print_validation_report(results)
+
+    # Save JSON if requested
+    if args.output_json:
+        output_path = Path(args.output_json)
+        save_validation_json(results, output_path)
+
+    # Upload to GCS if requested
+    if args.upload_to_gcs:
+        logger.warning(
+            "GCS upload not yet implemented - use scripts/upload_datasets_to_gcs.sh"
+        )
+
+    # Exit with error if required datasets are missing
+    if results["required_missing"]:
+        logger.error(
+            f"Validation failed: {len(results['required_missing'])} required datasets missing"
+        )
+        return 1
+
+    logger.info("✅ Validation complete!")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())

commit d59091db1c7951a93fdc438ef855d1b1b090e785
Author: williaby <67131297+williaby@users.noreply.github.com>
Date:   Sat Nov 15 19:20:34 2025 -0800

    Phase 1 MVP Completion: Ready for Phase 2 (#30)

    * docs: Add PR 14-15 reconciliation guide and DQS routing ADR

    Create comprehensive reconciliation document analyzing PRs 14-15:
    - Identifies critical inconsistencies (bbox format, performance targets)
    - Categorizes content as keep/update/discard with clear rationale
    - Provides 4-phase integration roadmap with action items
    - Documents 10-33x performance discrepancy requiring resolution

    Create ADR-0028 for Document Quality Score (DQS) framework:
    - Two-axis scoring: degradation (blur, noise) vs structural (tables, formulas)
    - Four-quadrant routing: vision_simple, vision_structured, ocr_fast, ocr_advanced
    - Complete implementation spec with schema, calculator, and routing logic
    - Monitoring strategy with Prometheus metrics and alerting
    - Phase 4 deployment plan with feature flags and A/B testing

    Update ADR index to include ADR-0028 in Phase Planning section.

    Related: PRs #14, #15

    * docs: Implement PR 14-15 reconciliation decisions and create functional requirements v2

    Update reconciliation document with project owner decisions:
    - Project name: Keep "Image Preprocessing Detector"
    - Office formats: Defer to Phase 5 with Docling integration (embedded images only)
    - PDF Portfolio: Ignore completely (permanently out of scope)
    - DQS Framework: Implement in Phase 4 (confirmed)

    Create functional_requirements_v2.md (docs/requirements/):
    - Fix CRITICAL bounding box format: [x,y,w,h] COCO format (was [x1,y1,x2,y2])
    - Update performance targets: Split GPU (150ms, 6+ pages/sec) vs CPU (400ms, 2+ pages/sec)
    - Update correction thresholds: 2° skew with do-no-harm guardrails (was 0.5°)
    - Add Office formats to Phase 5: Embedded image preprocessing only
    - Remove PDF Portfolio: Permanently out of scope
    - Add DQS routing: Four-quadrant decision matrix (Phase 4)
    - Add language detection: FR-5.3 with langdetect/fasttext
    - Add handwriting classification: FR-5.2 with F1 ≥ 0.90 target
    - Align with all ADRs (0001-0028) and PROJECT_PLAN phases

    Update PROJECT_PLAN Phase 5:
    - Add Office format preprocessing (Task 6):
      - Extract embedded images from .docx, .xlsx, .pptx
      - Run existing preprocessing pipeline (DPI upscaling, deskew, denoise)
      - Pass corrected images to Docling for improved OCR accuracy
      - Timeline: Weeks 21-25 implementation

=== Check config structure for required field ===
EXPECTED_DATASETS = {
    "benchmarks": {
        "doclaynet": {
            "path": "benchmarks/doclaynet",
            "type": "symlink",
            "target": "/home/byron/dev/data_ingestor/data/benchmarks/doclaynet",
            "phase": 1,
            "required": True,
            "description": "DocLayNet layout detection dataset",
        },
        "signatr6k": {
            "path": "benchmarks/signatr6k",
            "type": "directory",
            "phase": "?",
            "required": False,
            "description": "Signature detection dataset",
        },
        "synthetic_iqa": {
            "path": "benchmarks/synthetic_iqa",
            "type": "directory",
            "phase": 1,
            "required": True,
            "description": "Synthetic IQA dataset (auto-generated)",
        },
        "cocotext": {
            "path": "benchmarks/cocotext",
            "type": "directory",
            "phase": 2,
            "required": False,
            "description": "COCO-Text annotations",
        },
        "omnidocbench": {
            "path": "benchmarks/omnidocbench",
            "type": "directory",
            "phase": 3,
            "required": False,
            "description": "OmniDocBench multi-task benchmark",
        },
        "tablebank": {
            "path": "benchmarks/tablebank",
            "type": "directory",
            "phase": 2,
            "required": False,
            "description": "TableBank table detection dataset",
        },
        "pubtabnet": {
            "path": "benchmarks/pubtabnet",
            "type": "directory",
            "phase": 2,
            "required": False,
            "description": "PubTabNet table structure dataset",
        },
        "fintabnet": {
            "path": "benchmarks/fintabnet",
            "type": "directory",
            "phase": 2,
            "required": False,
            "description": "FinTabNet financial table dataset",
        },
        "wili_2018": {
            "path": "benchmarks/wili_2018",
            "type": "directory",
            "phase": 2,
            "required": False,
            "description": "WiLI language identification dataset",
        },
    },
    "raw": {
```

</shell_result>

---

Script executed:

```shell
#!/bin/bash
# Search for any tests or documentation about empty dataset handling
echo "=== Looking for tests related to validate_datasets ==="
find tests -name "*validate*" -o -name "*dataset*" 2>/dev/null | head -20

echo -e "\n=== Check DATASET_INSTALLATION.md for guidance on empty datasets ==="
find . -name "DATASET_INSTALLATION.md" -o -name "*DATASET*" 2>/dev/null | head -10

echo -e "\n=== Look for any comments or TODOs about empty handling ==="
rg -n "empty" scripts/validate_datasets.py -B 3 -A 3 | head -40

echo -e "\n=== Check if there are any issues or PRs mentioning this ==="
git log --all --grep="empty.*dataset" --grep="required.*dataset" --oneline 2>/dev/null | head -10
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stdout:

```
=== Looking for tests related to validate_datasets ===
tests/fixtures/phase1_validation/validate_detectors.py
tests/fixtures/phase1_validation/validate_doclaynet_sample.py

=== Check DATASET_INSTALLATION.md for guidance on empty datasets ===
./docs/DATASET_GENERATION_GUIDE.md
./docs/DATASET_LOCATIONS.md
./docs/reference/DATASET_SUFFICIENCY_REPORT.md

=== Look for any comments or TODOs about empty handling ===
161-
162-    Returns:
163-        Tuple of (status, details_dict)
164:        status: 'found', 'missing', 'symlink_broken', 'empty'
165-    """
166-    dataset_path = data_root / config["path"]
167-
--
202-        size = get_directory_size(dataset_path)
203-        file_count = count_files(dataset_path)
204-
205:        # Check if empty
206-        if file_count == 0:
207:            return "empty", {
208-                "path": str(dataset_path),
209-                "required": config["required"],
210-                "phase": config["phase"],
--
234-    status_map = {
235-        "found": "found",
236-        "missing": "missing",
237:        "empty": "empty",
238-        "symlink_broken": "broken",
239-    }
240-    if status in status_map:
--
267-            "total": 0,
268-            "found": 0,
269-            "missing": 0,
270:            "empty": 0,
271-            "broken": 0,
272-            "total_size": 0,
273-        },
--
295-            f" [{details.get('type', '')}]" if include_type else "",
296-        ),
297-        "missing": ("❌", "", ""),
298:        "empty": ("⚠️", " (empty directory)", ""),
299-        "symlink_broken": ("🔗", " (broken symlink)", ""),
300-    }

=== Check if there are any issues or PRs mentioning this ===
```

</shell_result>

---

Script executed:

```shell
#!/bin/bash
# Check for documentation about dataset validation expectations
echo "=== Search for DATASET_INSTALLATION or related docs ==="
find docs -type f -name "*.md" 2>/dev/null | xargs grep -l "empty\|required" 2>/dev/null | head -5

echo -e "\n=== Look at the synthetic_iqa and doclaynet configs (the required ones) ==="
sed -n '50,60p' scripts/validate_datasets.py

echo -e "\n=== Check if empty datasets could ever be marked as required=true ==="
grep -n "required.*True" scripts/validate_datasets.py
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stdout:

```
=== Search for DATASET_INSTALLATION or related docs ===
docs/ADRs/0003-adopt-property-based-testing.md
docs/ADRs/0004-github-actions-security-hardening.md
docs/ADRs/0005-mkdocs-documentation-system.md
docs/ADRs/0006-synthetic-validation-dataset-strategy.md
docs/ADRs/0008-multi-stage-pipeline-architecture.md

=== Look at the synthetic_iqa and doclaynet configs (the required ones) ===
        "synthetic_iqa": {
            "path": "benchmarks/synthetic_iqa",
            "type": "directory",
            "phase": 1,
            "required": True,
            "description": "Synthetic IQA dataset (auto-generated)",
        },
        "cocotext": {
            "path": "benchmarks/cocotext",
            "type": "directory",
            "phase": 2,

=== Check if empty datasets could ever be marked as required=true ===
40:            "required": True,
54:            "required": True,
305:    name: str, info: dict, show_required: bool = True, show_type: bool = True
351:        _print_dataset_entry(name, info, show_required=True, show_type=True)
```

</shell_result>

---

</details>

Based on my verification, I can now provide the rewritten review comment. The concern raised in the original review is **valid and confirmed**. The code deliberately excludes "empty" status from the `required_missing` logic, meaning empty required datasets will not trigger validation failure. This appears to be either an unintended oversight or an undocumented design decision, as there are no tests or documentation explaining why this behavior is acceptable.

---

**Empty required datasets should trigger validation failure, not pass silently**

The refactored `_update_summary_for_status` correctly centralizes summary accounting, but it only adds entries to `results["required_missing"]` when `status in ("missing", "symlink_broken")` and `config["required"]` is true. This means a required dataset that exists but is empty (0 files) will not be treated as "required missing" and will not trigger a non-zero exit, even though it's functionally unusable.

Currently, only two datasets are marked `required=True`: "doclaynet" and "synthetic_iqa". While this may not cause immediate issues (doclaynet is a symlink unlikely to be empty; synthetic_iqa is auto-generated), an empty required dataset is as unusable as a missing one. To make validation truly comprehensive, either:

1. Add "empty" to the condition on line 244: `elif status in ("missing", "empty", "symlink_broken") and config["required"]:`
2. Or document the explicit choice to treat empty required datasets as acceptable warnings rather than failures.

Without this change, CI/CD systems relying on validation exit codes may proceed with incomplete data.

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In scripts/validate_datasets.py around lines 230-247, the function
_update_summary_for_status currently treats "empty" datasets as not triggering
required_missing; modify the logic so that required datasets with status "empty"
are also appended to results["required_missing"] (e.g., include "empty" in the
elif condition alongside "missing" and "symlink_broken") so empty required
datasets cause validation failure; update any related tests or documentation as
needed to reflect this change.
```

</details>

<!-- fingerprinting:phantom:poseidon:olive -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 12. PR #136 - docs/datasets/source/drccbi.md

- **Status**: [x]
- **Severity**: medium
- **PR**: [#136 - feat: comprehensive dataset enrichment and documentation expansion](https://github.com/williaby/image-preprocessing-detector/pull/136)
- **Reviewer**: @coderabbitai
- **Date**: 2026-02-14
- **File**: `docs/datasets/source/drccbi.md`
- **Line**: 296

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟡 Minor_

**Consolidate duplicate license warnings.**

Lines 292-293 both flag the unverified license issue with slightly different phrasing ("commercial use" vs "production use"). Merge these into a single, clear warning.

<details>
<summary>📝 Proposed consolidation</summary>

```diff
-- **License Unknown**: No explicit license provided - contact authors before commercial use
-- **License status is unverified - contact dataset authors before production use**
+- **License Unknown**: License status is unverified - contact dataset authors before commercial or production use
```

</details>

<!-- suggestion_start -->

<details>
<summary>📝 Committable suggestion</summary>

> ‼️ **IMPORTANT**
> Carefully review the code before committing. Ensure that it accurately replaces the highlighted code, contains no missing lines, and has no issues with indentation. Thoroughly test & benchmark the code to ensure it meets the requirements.

```suggestion
- **License Unknown**: License status is unverified - contact dataset authors before commercial or production use
```

</details>

<!-- suggestion_end -->

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In `@docs/datasets/source/drccbi.md` around lines 292 - 293, Remove the duplicated
license warnings and replace them with a single clear sentence; specifically,
consolidate the two lines that read "**License Unknown**: No explicit license
provided - contact authors before commercial use" and "**License status is
unverified - contact dataset authors before production use**" into one unified
warning such as "**License status unverified**: No explicit license provided —
contact the dataset authors before commercial or production use." Ensure only
the consolidated sentence remains in place of the two original lines.
```

</details>

<!-- fingerprinting:phantom:triton:puma -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 13. PR #136 - docs/datasets/source/iam.md

- **Status**: [x]
- **Severity**: medium
- **PR**: [#136 - feat: comprehensive dataset enrichment and documentation expansion](https://github.com/williaby/image-preprocessing-detector/pull/136)
- **Reviewer**: @coderabbitai
- **Date**: 2026-02-14
- **File**: `docs/datasets/source/iam.md`
- **Line**: 60

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟡 Minor_

**Distinguish writers from annotators.**

The "Annotator Details" field lists "657 writers providing handwriting samples," but writers created the raw handwriting data, not the ground truth annotations. The actual annotators who transcribed the text and generated bounding boxes are not mentioned. Consider clarifying who performed the annotation work (transcription and XML generation) versus who created the source handwriting samples.

<details>
<summary>📝 Suggested clarification</summary>

```diff
-| **Annotator Details** | 657 writers providing handwriting samples |
+| **Annotator Details** | Transcription and bounding box annotations created by FKI Research Group; handwriting samples from 657 writers |
```

</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In `@docs/datasets/source/iam.md` at line 60, Update the table row currently
labeled "Annotator Details" (the cell containing "657 writers providing
handwriting samples") to clearly separate authors of the original handwriting
from the people who produced the annotations: rename that row to "Writer
Details" (e.g., "657 writers providing handwriting samples") and add a new row
"Annotator Details" that states who performed transcription and XML/bounding-box
generation (e.g., "X annotators performed transcriptions and generated XML
bounding boxes") or provide the specific team/organization responsible; ensure
the text mentions both the writers and the annotators (transcription/XML) so the
roles are unambiguous.
```

</details>

<!-- fingerprinting:phantom:triton:puma -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 14. PR #135 - .qlty/qlty.toml

- **Status**: [x]
- **Severity**: medium
- **PR**: [#135 - feat: Stream 3 heuristic detector benchmarking with Go/No-Go decisions](https://github.com/williaby/image-preprocessing-detector/pull/135)
- **Reviewer**: @coderabbitai
- **Date**: 2026-02-15
- **File**: `.qlty/qlty.toml`
- **Line**: 328

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟡 Minor_

**Unpinned HuggingFace downloads pose supply chain risk.**

B615 warns about downloads without version pinning. While "latest data" may be desired for benchmarking, this creates reproducibility issues and supply chain security risks:

- Dataset contents could change between runs
- Malicious or corrupted data could be introduced upstream

For benchmarking specifically, consider documenting the dataset versions used in results (e.g., in the JSON outputs) even if not pinning in code, so results remain reproducible.

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In @.qlty/qlty.toml around lines 322 - 328, The triage rule that ignores
bandit:B615 for files matching "scripts/**" skips warnings about unpinned
HuggingFace downloads and creates reproducibility/supply-chain risk; update the
affected scripts that call load_dataset (under scripts/**) to record the exact
dataset identifier/fingerprint/commit or config used (e.g., dataset name +
revision or dataset_info.fingerprint) and include that metadata in the benchmark
JSON outputs, or alternatively pin the dataset revision in the load_dataset
call, and then remove or narrow the triage entry (match.rules = ["bandit:B615"]
/ match.file_patterns = ["scripts/**"] in the triage block) so the rule is not
broadly ignored.
```

</details>

<!-- fingerprinting:phantom:poseidon:ocelot -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 15. PR #134 - pyproject.toml

- **Status**: [x]
- **Severity**: medium
- **PR**: [#134 - fix: dependency updates, security fixes, ~700 SonarCloud quality issues](https://github.com/williaby/image-preprocessing-detector/pull/134)
- **Reviewer**: @coderabbitai
- **Date**: 2026-02-13
- **File**: `pyproject.toml`
- **Line**: 166

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟡 Minor_

<details>
<summary>🧩 Analysis chain</summary>

🌐 Web query:

`python-multipart 0.0.22 CVE fix security vulnerability`

💡 Result:

`python-multipart` **0.0.22** includes a security fix for **CVE-2026-24486** (path traversal / arbitrary file write). The issue affects versions **prior to 0.0.22** when using the non-default settings `UPLOAD_DIR` **and** `UPLOAD_KEEP_FILENAME=True`, allowing a crafted filename to write files outside the intended upload directory. **Upgrade to `python-multipart>=0.0.22`** to remediate; as a workaround, avoid `UPLOAD_KEEP_FILENAME=True`. [1][2]

Note: an earlier DoS issue (**CVE-2024-53981**) was fixed in **0.0.18**, so **0.0.22 also includes that fix**. [3]

**Sources:** [1] [2] [3]

---

🌐 Web query:

`python-multipart 0.0.22 release notes compatibility FastAPI Starlette`

💡 Result:

## python-multipart 0.0.22 release notes (and what changed)

- **Release date:** **Jan 25, 2026**. [3]
- **Change:** “Drop directory path from filename in `File`” (i.e., uploaded filenames no longer retain any client-supplied path components). [1]
- **Security context:** 0.0.22 is cited as the **fixed version** for **CVE-2026-24486** (path traversal / arbitrary file write when using non-default `UPLOAD_DIR` + `UPLOAD_KEEP_FILENAME=True`). [2]

## Compatibility with Starlette

- Starlette **requires at least `python-multipart>=0.0.18`** (bumped in Starlette 0.42.0). So **0.0.22 satisfies Starlette’s minimum**. [4]
- Starlette also changed its import expectations (to match `python-multipart`’s newer import path): in **Starlette 0.41.1** it “Change[d] `python-multipart` import to `python_multipart`”. This means **older Starlette versions (before 0.41.1) can break** with newer python-multipart releases that no longer provide the old `multipart` import layout. [4]

## Compatibility with FastAPI

- FastAPI uses Starlette for request/form parsing, and `python-multipart` is an **optional dependency** used for `request.form()` / form-data handling (commonly installed via `fastapi[standard]`). [5]
- Practically: **FastAPI compatibility follows Starlette’s**—so **FastAPI versions that depend on Starlette ≥ 0.42.0 should work with python-multipart 0.0.22** (since Starlette’s minimum is 0.0.18). [4][5]

**Sources:**
[1] Python Multipart changelog (0.0.22 entry) — <https://multipart.fastapiexpert.com/changelog/>
[2] GitLab advisory for CVE-2026-24486 — <https://advisories.gitlab.com/pkg/pypi/python-multipart/CVE-2026-24486/>
[3] PyPI release history for python-multipart — <https://pypi.org/project/python-multipart/>
[4] Starlette release notes (python-multipart min version + import change) — <https://starlette.dev/release-notes/>
[5] FastAPI PyPI docs (standard deps include python-multipart for form parsing) — <https://pypi.org/project/fastapi/0.115.4/>

---

🌐 Web query:

`python-multipart 0.0.22 breaking changes`

💡 Result:

In **python-multipart 0.0.22 (2026-01-25)** the notable **breaking/behavior change** is:

- **Directory components are stripped from uploaded filenames** in `File` (it now uses `os.path.basename(file_name)` before splitting base/ext). If your code relied on `File` preserving paths like `b"/tmp/foo.txt"` or `b"../foo.txt"` (especially with `UPLOAD_KEEP_FILENAME=True`), it will now behave differently (only `foo.txt` is kept). [1][2]

Why this happened / impact:

- This change is part of fixing a **path traversal / arbitrary file write** vulnerability (CVE-2026-24486 / GHSA-wp53-j4wj-2cfg) that could be triggered under **non-default config** such as `UPLOAD_DIR` + `UPLOAD_KEEP_FILENAME=True` with a malicious filename. Upgrading to **0.0.22** is the fix. [2][3]

**Sources:** changelog + patch diff + CVE advisory. [1][2][3]

---

🌐 Web query:

`python-multipart license`

💡 Result:

`python-multipart` is licensed under the **Apache License 2.0 (Apache-2.0)**. [1], [2]

Note: this is different from the PyPI package named `multipart`, which is **MIT** licensed. [3]

**Sources:** [1] GitHub repo (LICENSE/README), [2] PyPI project page, [3] PyPI `multipart` project page.

---

</details>

**The CVE-2026-24486 fix justifies the upgrade; verify multipart upload tests still pass after this version bump.**

The bump to python-multipart 0.0.22 is appropriate for the security fix (path traversal / arbitrary file write when using non-default `UPLOAD_DIR` + `UPLOAD_KEEP_FILENAME=True`). Compatibility with fastapi>=0.115 and starlette>=0.49.1 is satisfied, as Starlette 0.49.1 requires >=0.0.18 and the import path changes in 0.0.22 align with Starlette 0.41.1+.

However, 0.0.22 strips directory components from uploaded filenames (using `os.path.basename()`). Verify that existing multipart upload tests do not rely on filename path preservation; tests validating behavior with paths like `"../foo.txt"` will fail with this version.

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In `@pyproject.toml` at line 166, The multipart library upgrade to
python-multipart 0.0.22 changes uploaded filename handling (it now strips
directory components via os.path.basename), so run the multipart upload test
suite and update any tests that assumed path-preserving filenames: locate tests
referencing UPLOAD_KEEP_FILENAME, UPLOAD_DIR, or asserting received filenames
like "../foo.txt" and change assertions to expect the basename ("foo.txt") or
use safe test inputs; if the code relied on preserving paths, update the upload
handling logic to explicitly restore or validate paths instead of relying on the
library (refer to the pyproject.toml dependency bump and tests that assert
upload filename behavior).
```

</details>

<!-- fingerprinting:phantom:medusa:eagle -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 16. PR #133 - src/image_preprocessing_detector/detection/handwriting_detector.py

- **Status**: [x]
- **Severity**: medium
- **PR**: [#133 - feat: Stream 2 heuristic detectors (11 modules + E2E tests)](https://github.com/williaby/image-preprocessing-detector/pull/133)
- **Reviewer**: @coderabbitai
- **Date**: 2026-02-13
- **File**: `src/image_preprocessing_detector/detection/handwriting_detector.py`
- **Line**: 431

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟡 Minor_

**Validate `threshold` and `min_components` to avoid misconfiguration.**
Out-of-range thresholds or non-positive component counts silently break detection semantics.

<details>
<summary>✅ Suggested guardrails</summary>

```diff
     def __init__(
         self,
         threshold: float = _DEFAULT_THRESHOLD,
         min_components: int = _MIN_COMPONENTS,
     ) -> None:
         """Initialise handwriting detector.
@@
         """
+        if not 0.0 <= threshold <= 1.0:
+            raise ValueError("threshold must be between 0.0 and 1.0")
+        if min_components < 1:
+            raise ValueError("min_components must be >= 1")
         self.threshold = threshold
         self.min_components = min_components
```

</details>
As per coding guidelines “Security best practices (input validation)”.

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In `@src/image_preprocessing_detector/detection/handwriting_detector.py` around
lines 411 - 431, Validate constructor inputs in the __init__ of the handwriting
detector: ensure threshold is a numeric value within [0.0, 1.0] and
min_components is an integer >= 1 (or at least >= _MIN_COMPONENTS if you prefer
the module default). Add explicit checks (use isinstance for numeric/int or
convert safely) and raise ValueError (or TypeError for bad types) with clear
messages if values are out of range; assign attributes only after validation and
keep the existing logger.info call. This ensures threshold and min_components on
the HandwritingDetector instance cannot be misconfigured.
```

</details>

<!-- fingerprinting:phantom:poseidon:eagle -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 17. PR #109 - src/image_preprocessing_detector/labeling/deqa/ensemble.py

- **Status**: [~]
- **Severity**: medium
- **PR**: [#109 - feat: add DeQA-Doc labeling infrastructure with 3-dimension quality assessment](https://github.com/williaby/image-preprocessing-detector/pull/109)
- **Reviewer**: @coderabbitai
- **Date**: 2026-01-18
- **File**: `src/image_preprocessing_detector/labeling/deqa/ensemble.py`
- **Line**: 133

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟠 Major_

<details>
<summary>🧩 Analysis chain</summary>

🏁 Script executed:

```shell
# First, let's look at the ensemble.py file around the mentioned lines
cat -n src/image_preprocessing_detector/labeling/deqa/ensemble.py | head -150
```

Repository: williaby/image-preprocessing-detector

Length of output: 6061

---

🏁 Script executed:

```shell
# Find the ModelConfig definition
fd -t f "*.py" | xargs rg "class ModelConfig" -A 10
```

Repository: williaby/image-preprocessing-detector

Length of output: 2392

---

🏁 Script executed:

```shell
# Check for other snapshot_download usages in the codebase
rg "snapshot_download" -t py -B 2 -A 5
```

Repository: williaby/image-preprocessing-detector

Length of output: 12185

---

🏁 Script executed:

```shell
# Check if there's any existing revision handling in the config
rg "ModelScope\|snapshot_download\|revision" src/image_preprocessing_detector/labeling/deqa/ -t py -B 2 -A 2
```

Repository: williaby/image-preprocessing-detector

Length of output: 63

---

🏁 Script executed:

```shell
cat -n src/image_preprocessing_detector/labeling/deqa/config.py | grep -A 30 "class ModelConfig"
```

Repository: williaby/image-preprocessing-detector

Length of output: 1387

---

🏁 Script executed:

```shell
# Check if there's a revision parameter anywhere in the config
rg "revision" src/image_preprocessing_detector/labeling/deqa/ -t py -B 2 -A 2
```

Repository: williaby/image-preprocessing-detector

Length of output: 9609

---

🌐 Web query:

`ModelScope snapshot_download revision parameter best practices documentation`

💡 Result:

Summary — what the revision parameter does

- revision lets you pick which Git revision of the model repo to download (branch name, tag, or commit hash). If omitted, ModelScope picks the repo default/latest and prints a “Model revision not specified, use revision: <X>” warning. [1][2]

Best practices

1. Pin to a commit hash (or an immutable tag) for exact reproducibility — commit hashes never change. [1][2]
2. If you need a stable release but readable names, use released tags (v1.0.0, v1.0.3, etc.). [1][3]
3. Always record the resolved revision printed by snapshot_download when you don’t pass revision. That lets you reproduce later. [2][3]
4. Use allow/ignore (include/exclude) patterns to avoid downloading large unnecessary files when testing different revisions. [1][2]
5. For private models or CI, log in / provide credentials and set cache/local_dir explicitly to control where the chosen revision is stored. [3]

Examples

- Pin to tag: snapshot_download(model_id='owner/model', revision='v1.0.0'). [1]
- Pin to commit: snapshot_download(model_id='owner/model', revision='0123abcd...'). [1][2]

Sources
[1] ModelScope snapshot_download docs / SDK references (examples and revision description).
[2] ModelScope usage guides and community notes showing the “revision not specified” behavior and caching.
[3] ModelScope CLI / blog posts describing include/exclude patterns, cache_dir/local_dir and revision usage.

---

🏁 Script executed:

```shell
# Let me check the full context around both snapshot_download calls in ensemble.py
cat -n src/image_preprocessing_detector/labeling/deqa/ensemble.py | sed -n '113,250p'
```

Repository: williaby/image-preprocessing-detector

Length of output: 6237

---

🏁 Script executed:

```shell
# Check if specialist.py and vl_single.py are also reviewed or if they have similar issues
grep -n "revision=\"master\"" src/image_preprocessing_detector/labeling/deqa/*.py
```

Repository: williaby/image-preprocessing-detector

Length of output: 384

---

</details>

**Use pinned revisions for ModelScope snapshot_download instead of "master".**

The hardcoded `revision="master"` in `_load_mplug_model` and `_load_qwen_model` uses a mutable branch, breaking reproducibility and supply-chain guarantees. Add a `revision` field to `ModelConfig` and apply it consistently across all `snapshot_download` calls—this matches the project's existing pattern for HuggingFace revisions. ModelScope supports revision pinning via commit hash or tag, which should be used instead of branch names.

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In `@src/image_preprocessing_detector/labeling/deqa/ensemble.py` around lines 124
- 133, The ModelScope download uses a hardcoded revision="master" which breaks
reproducibility; add a revision attribute to the ModelConfig dataclass/structure
and update all ModelScope snapshot_download calls (notably in _load_mplug_model
and _load_qwen_model) to pass model_config.revision instead of the literal
"master", falling back to None or an explicit pinned value if revision is unset,
and ensure the ModelConfig is populated wherever model configs are created so
revision is applied consistently across the codebase.
```

</details>

<!-- fingerprinting:phantom:medusa:eagle -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 18. PR #106 - modal/train_siglip2_iqa.py

- **Status**: [x]
- **Severity**: medium
- **PR**: [#106 - feat: Add SigLIP2-IQA-Base-86M Document Quality Assessment Model](https://github.com/williaby/image-preprocessing-detector/pull/106)
- **Reviewer**: @coderabbitai
- **Date**: 2026-01-16
- **File**: `modal/train_siglip2_iqa.py`
- **Line**: 100

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟠 Major_

**Security concern: Service account credentials embedded in Docker image.**

Copying the GCS service account JSON file directly into the image with `copy=True` bakes the credentials into a persistent image layer. This is problematic because:

1. Image layers can be inspected/cached
2. The secret is already available via `modal.Secret.from_name("gcs-credentials")` at line 162

Consider using only the Modal secret mechanism and removing the embedded file copy.

<details>
<summary>♻️ Suggested approach</summary>

```diff
-    # Copy GCS credentials for authentication
-    .add_local_file(
-        ".gcp/service-account.json",
-        "/root/.gcp/service-account.json",
-        copy=True,
-    )
```

Then in `download_diqa5000_from_gcs`, use the secret environment variable instead:

```python
# The Modal secret already injects credentials - use them directly
# or write them to the expected path at runtime from the secret
```

</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In `@modal/train_siglip2_iqa.py` around lines 94 - 99, The Docker build currently
bakes GCP credentials via .add_local_file(..., copy=True) which embeds the
service-account.json into the image; remove that call and stop copying the file
into the image, and instead rely on the existing
modal.Secret.from_name("gcs-credentials") (used at or around where
modal.Secret.from_name is referenced) to inject credentials at runtime; update
download_diqa5000_from_gcs to read the secret-provided credentials from the
environment or write the secret to the expected path at container start (rather
than bundling the file during build) so no persistent image layer contains the
JSON.
```

</details>

<!-- fingerprinting:phantom:medusa:ocelot -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 19. PR #105 - modal/train_hyperiqa_plus_plus.py

- **Status**: [~]
- **Severity**: medium
- **PR**: [#105 - feat: Add HyperIQA++ Document IQA Model](https://github.com/williaby/image-preprocessing-detector/pull/105)
- **Reviewer**: @coderabbitai
- **Date**: 2026-01-16
- **File**: `modal/train_hyperiqa_plus_plus.py`
- **Line**: 712

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟠 Major_

**`weights_only=True` will fail to load checkpoint containing non-tensor data.**

The checkpoint saved at lines 940-948 includes `config` (a dataclass) and `val_metrics` (a dict). Loading with `weights_only=True` only allows tensor data and will fail with a `_pickle.UnpicklingError`. Either:

1. Change to `weights_only=False` (security trade-off, but checkpoint is from trusted volume), or
2. Remove non-tensor data from checkpoint saves and reconstruct from known values.

<details>
<summary>Option 1: Allow non-tensor data (matches benchmark script)</summary>

```diff
             checkpoint = torch.load(
                 checkpoint_to_load,
                 map_location=device,
-                weights_only=True,
+                weights_only=False,  # noqa: S614 - checkpoint from trusted Modal volume
             )
```

</details>

<details>
<summary>Option 2: Save only tensor-compatible data</summary>

In the checkpoint save blocks (lines 940-948 and 961-968), convert config to dict:

```diff
             torch.save(
                 {
                     "epoch": epoch,
                     "model_state_dict": model.state_dict(),
                     "optimizer_state_dict": optimizer.state_dict(),
                     "val_metrics": val_metrics,
-                    "config": config,
+                    "config": config.__dict__,  # Save as dict for weights_only=True compatibility
                 },
                 checkpoint_path,
             )
```

</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In `@modal/train_hyperiqa_plus_plus.py` around lines 706 - 712, The torch.load
call using weights_only=True will fail because saved checkpoints include
non-tensor objects (config dataclass and val_metrics dict); fix by either (A)
allowing non-tensor data: change the torch.load invocation where
checkpoint_to_load is used to set weights_only=False so torch.load(...,
map_location=device, weights_only=False), or (B) keep weights_only=True but
change the checkpoint save sites (the torch.save/ checkpoint dicts that include
config and val_metrics) to serialize only tensor-compatible data (e.g., convert
config to a dict or omit val_metrics) so saved checkpoints contain only tensors
before loading with weights_only=True. Ensure you update the corresponding
torch.save usages that construct the checkpoint dict (the places that currently
include config and val_metrics) if you choose option B.
```

</details>

<!-- fingerprinting:phantom:medusa:ocelot -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 20. PR #100 - docs/architecture/diagrams/INDEX.md

- **Status**: [x]
- **Severity**: medium
- **PR**: [#100 - refactor(modal): Extract shared utilities and fix SonarCloud security hotspots](https://github.com/williaby/image-preprocessing-detector/pull/100)
- **Reviewer**: @coderabbitai
- **Date**: 2026-01-11
- **File**: `docs/architecture/diagrams/INDEX.md`
- **Line**: 284

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟡 Minor_

<details>
<summary>🧩 Analysis chain</summary>

🏁 Script executed:

```shell
# First, check if the file exists and read the relevant sections
if [ -f "docs/architecture/diagrams/INDEX.md" ]; then
  echo "=== Lines 275-284 (Layout Model Training section) ==="
  sed -n '275,284p' docs/architecture/diagrams/INDEX.md
  echo ""
  echo "=== Lines 403-422 (Supporting Infrastructure section) ==="
  sed -n '403,422p' docs/architecture/diagrams/INDEX.md
else
  echo "File not found"
fi
```

Repository: williaby/image-preprocessing-detector

Length of output: 1500

---

🏁 Script executed:

```shell
# Search for all occurrences of "GAP" in the INDEX.md file
rg "GAP" docs/architecture/diagrams/INDEX.md -n -B 2 -A 2
```

Repository: williaby/image-preprocessing-detector

Length of output: 904

---

🏁 Script executed:

```shell
# Check if referenced files in the tables actually exist
# Sample file paths that should be verified
fd -type f -name "*.py" | grep -E "(teacher_trainer|student_trainer|dqs_calculator|device_orchestrator)" | head -20
```

Repository: williaby/image-preprocessing-detector

Length of output: 251

---

🏁 Script executed:

```shell
# Also check the complete directory structure of the model files referenced
fd -type f -path "*/training/*" -name "*.py" | head -20
```

Repository: williaby/image-preprocessing-detector

Length of output: 251

---

🏁 Script executed:

```shell
# Fix the file path verification - check for existence of common training files
find . -name "train_phase*.py" 2>/dev/null
find . -name "*trainer*.py" 2>/dev/null | head -10
find . -path "*/modal/*" -name "*.py" 2>/dev/null | head -10
```

Repository: williaby/image-preprocessing-detector

Length of output: 868

---

</details>

**Consolidate gap documentation across three scattered locations for consistency.**

Gap analysis currently appears in three places:

- Lines 275–284: "Layout Model Training (GAP)" (inline in Model Training workstream)
- Lines 403–422: "Celery Workers (GAP - No Diagram)" and "Monitoring & Drift Detection (GAP - No Diagram)" (Supporting Infrastructure section)
- Line 467: Cross-reference table with "(GAP - needs diagram)"

This fragmentation obscures the overall picture of missing diagrams and uses inconsistent labeling formats. Consolidate all gaps into a unified "Missing Diagrams & Recommendations" section, or elevate supporting infrastructure gaps to the same prominence as workstream gaps for clearer prioritization.

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In @docs/architecture/diagrams/INDEX.md around lines 275 - 284, The document
fragments "Layout Model Training (GAP)", "Celery Workers (GAP - No Diagram)",
"Monitoring & Drift Detection (GAP - No Diagram)" and the cross-reference entry
"(GAP - needs diagram)" should be consolidated into a single "Missing Diagrams &
Recommendations" section; create that new section and move the content from
those three headings into it, standardize each gap label to a single format
(e.g., "GAP - needs diagram"), and add the specific recommendation to create
project-a-layout-training.puml (for DocLayout-YOLO/Layout-Lite) under
"level-2/model-training/". Ensure the original headings are removed or replaced
with references to the new consolidated section so there is a single
authoritative list of missing diagrams and recommendations.
```

</details>

<!-- fingerprinting:phantom:triton:mongoose -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 21. PR #79 - modal/export_student_onnx.py

- **Status**: [~]
- **Severity**: medium
- **PR**: [#79 - feat(phase7): implement continuous training infrastructure and deprecate Phase 2 assets](https://github.com/williaby/image-preprocessing-detector/pull/79)
- **Reviewer**: @coderabbitai
- **Date**: 2026-01-10
- **File**: `modal/export_student_onnx.py`
- **Line**: 40

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟠 Major_

<details>
<summary>🧩 Analysis chain</summary>

🏁 Script executed:

```shell
# First, check if the service account file is referenced elsewhere in modal/
rg -n "service-account.json" modal/
```

Repository: williaby/image-preprocessing-detector

Length of output: 1840

---

🏁 Script executed:

```shell
# Check if Modal Secrets are used (gcs-credentials or Secret.from_name pattern)
rg -n "gcs-credentials|Secret.from_name" modal/
```

Repository: williaby/image-preprocessing-detector

Length of output: 1068

---

🏁 Script executed:

```shell
# Read the specific file to understand the image definition and credential handling
cat -n modal/export_student_onnx.py | head -100
```

Repository: williaby/image-preprocessing-detector

Length of output: 3785

---

</details>

**Use Modal Secrets instead of embedding credentials in the container image.**

The `.add_local_file()` call at lines 36-40 has two issues: (1) the image build will fail if `.gcp/service-account.json` doesn't exist locally, and (2) embedding credentials in the container image is a security risk. Other Modal scripts in this repo (e.g., `train_phase7_production.py`, `train_phase7_mvp.py`) use `modal.Secret.from_name("gcs-credentials")` instead. Follow the established pattern documented in `app.py` and remove the local file mount in favor of secrets.

<!-- fingerprinting:phantom:medusa:ocelot -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 22. PR #79 - docs/planning/PHASE7_TRAINING_CRITIQUE.md

- **Status**: [~]
- **Severity**: medium
- **PR**: [#79 - feat(phase7): implement continuous training infrastructure and deprecate Phase 2 assets](https://github.com/williaby/image-preprocessing-detector/pull/79)
- **Reviewer**: @coderabbitai
- **Date**: 2026-01-10
- **File**: `docs/planning/PHASE7_TRAINING_CRITIQUE.md`
- **Line**: 601

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟠 Major_

**Clarify decision-making authority and mandatory vs. optional recommendations.**

The three deployment paths (A: Teacher-only, B: Production model, C: Both) are well-structured, but the document doesn't specify:

1. **Who decides which path?** (e.g., engineering lead, PM, technical lead)
2. **What decision criteria?** (e.g., "Choose Path A if shipping timeline <4 weeks")
3. **Blocking status**: Is this critique blocking v4 training or informational?
4. **Mandatory vs. optional**: Language alternates between "must" (lines 502, 513, 641) and "should" (line 457), creating ambiguity about which recommendations are blockers.

**Recommendation**: Add a decision matrix at the end of Section 5.1:

```markdown
### 5.4 Decision Framework

| Question | If YES → | If NO → |
|----------|----------|---------|
| Ship in <4 weeks? | Path A | Path B |
| Already distilling to ResNet-18? | Path A | Path C |
| Have $25k+ compute budget? | Path B | Path A |
```

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In @docs/planning/PHASE7_TRAINING_CRITIQUE.md around lines 490 - 601, The
document leaves ambiguity around who chooses between the three deployment paths
(A: Teacher-only, B: Production model, C: Both), what criteria to use, and which
recommendations are blocking; add a concise "5.4 Decision Framework" under
Section 5.1 that: (1) defines decision authority (e.g., Engineering Lead + PM as
final decision-makers, with Technical Lead advisory), (2) enumerates binary
decision criteria tied to paths (e.g., "ship <4 weeks? → Path A", "distillation
already in place? → Path A", "compute budget ≥ $25k? → Path B"), (3) marks each
action in Section 5.1 as BLOCKING or OPTIONAL (use explicit terms like "BLOCKER"
vs "RECOMMENDATION"), and (4) standardizes all modal language by replacing
ambiguous 'must/should' instances in Section 5.1 and related bullets with clear
labels (BLOCKER/RECOMMENDATION/ADVISORY) referencing the three paths and the
items (Run pure MSE baseline, Validate compression labels, Ablation study) so
reviewers can immediately see which path each item blocks or supports.
```

</details>

<!-- fingerprinting:phantom:triton:mongoose -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 23. PR #62 - .github/workflows/deploy.yml

- **Status**: [~]
- **Severity**: medium
- **PR**: [#62 - feat(phase4): Device-Priority Execution & Modal GPU Integration](https://github.com/williaby/image-preprocessing-detector/pull/62)
- **Reviewer**: @coderabbitai
- **Date**: 2025-12-04
- **File**: `.github/workflows/deploy.yml`
- **Line**: 222

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟠 Major_

<details>
<summary>🧩 Analysis chain</summary>

🏁 Script executed:

```shell
# Search for all values files in charts directory
fd -t f "values.*\.yaml" charts/
```

Repository: williaby/image-preprocessing-detector

Length of output: 233

---

🏁 Script executed:

```shell
# Also check the entire deploy.yml to see how dev and prod deployments use values files
cat -n .github/workflows/deploy.yml
```

Repository: williaby/image-preprocessing-detector

Length of output: 12074

---

</details>

**Add environment-specific values file for staging deployment.**

Staging deployment (lines 200-206) lacks a `-f` flag to specify environment-specific values, unlike dev (line 131) and prod (line 256). This causes staging to use only the default `values.yaml`, risking configuration inconsistency. A `values-staging.yaml` file must be created in `charts/image-preprocessing-detector/` and referenced in the helm command:

```diff
       - name: Deploy with Helm
         run: |
           helm upgrade --install imgprep-api ./charts/image-preprocessing-detector \
+            -f charts/image-preprocessing-detector/values-staging.yaml \
             --namespace imgprep-staging \
```

> Committable suggestion skipped: line range outside the PR's diff.

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
.github/workflows/deploy.yml around lines 198 to 206: the Helm deploy step for
staging omits an environment-specific values file causing staging to use only
default values; create charts/image-preprocessing-detector/values-staging.yaml
with the staging overrides (replicas, resource limits, imagePullSecrets, env
vars, etc.) and update the Helm command to include -f
charts/image-preprocessing-detector/values-staging.yaml so the staging
deployment uses the correct configuration.
```

</details>

<!-- fingerprinting:phantom:medusa:ocelot -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 24. PR #62 - .github/workflows/deploy.yml

- **Status**: [~]
- **Severity**: medium
- **PR**: [#62 - feat(phase4): Device-Priority Execution & Modal GPU Integration](https://github.com/williaby/image-preprocessing-detector/pull/62)
- **Reviewer**: @coderabbitai
- **Date**: 2025-12-04
- **File**: `.github/workflows/deploy.yml`
- **Line**: 35

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟠 Major_

**Missing dependency on CI quality gates before deployment.**

Per coding guidelines, deployments must only proceed after tests pass with 80%+ coverage, Ruff/MyPy checks pass, and Bandit/Safety security scans pass. The `build` job proceeds directly without these gates, risking deployment of untested or non-compliant code.

Consider adding a dependency on a CI workflow or adding quality gate jobs:

```diff
 jobs:
+  ci:
+    name: Run CI Checks
+    uses: ./.github/workflows/ci.yml  # or inline test/lint/scan steps
+
   build:
     name: Build and Push Docker Image
+    needs: ci
     runs-on: ubuntu-latest
```

Alternatively, if a separate CI workflow exists, use `workflow_run` trigger to ensure this workflow only runs after CI succeeds.

> Committable suggestion skipped: line range outside the PR's diff.

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
.github/workflows/deploy.yml lines 28-35: the build job currently runs
unconditionally and lacks dependencies on CI quality gates; update the workflow
so the deployment/build job waits for the CI jobs that enforce tests (coverage
>=80%), Ruff/MyPy linting, and Bandit/Safety scans to complete
successfully—either by adding needs: [ci-tests, lint, security-scan] (where
those job names run in this workflow) or by converting this workflow to trigger
on workflow_run for the CI workflow and only run on success; ensure the
referenced job names or workflow_run target exist and that the test job emits
coverage threshold or fails when coverage <80% so the build job will not start
until all gates pass.
```

</details>

<!-- fingerprinting:phantom:medusa:ocelot -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 25. PR #59 - tests/api/test_api_comprehensive.py

- **Status**: [x]
- **Severity**: medium
- **PR**: [#59 - test: consolidate comprehensive test suite from feature branches](https://github.com/williaby/image-preprocessing-detector/pull/59)
- **Reviewer**: @coderabbitai
- **Date**: 2025-12-02
- **File**: `tests/api/test_api_comprehensive.py`
- **Line**: 846

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟡 Minor_

**Incomplete test method.**

The test `test_rate_limit_headers_present` ends with an unused variable assignment and no assertions, making it effectively a no-op.

Either complete the test with proper assertions or remove it:

```diff
     def test_rate_limit_headers_present(
         self, full_middleware_settings: APISettings
     ) -> None:
         """Rate limit headers are present in responses."""
         app = create_app(settings=full_middleware_settings)
         client = TestClient(app)

-        _ = client.get("/health")
-        # Health is not in limit_paths by default, so no rate limit headers
-        # But for process endpoint with valid auth...
+        # Health endpoint may not have rate limit headers
+        response = client.get("/health")
+        assert response.status_code == 200
+        # Verify response is valid even without rate limit headers on health
```

<!-- fingerprinting:phantom:medusa:ocelot -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 26. PR #56 - .github/workflows/release.yml

- **Status**: [x]
- **Severity**: medium
- **PR**: [#56 - feat: integrate org-level reusable workflows and resolve security issues](https://github.com/williaby/image-preprocessing-detector/pull/56)
- **Reviewer**: @coderabbitai
- **Date**: 2025-12-01
- **File**: `.github/workflows/release.yml`
- **Line**: 56

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟠 Major_

<details>
<summary>🧩 Analysis chain</summary>

🏁 Script executed:

```shell
#!/bin/bash
# Check if the short SHA is valid by attempting to access it via git
# Since we can't directly access external repos, let's verify the format and search for any documentation about SHA pinning best practices

# First, let's check the format - a short SHA should be at least 7 characters
SHORT_SHA="3bf8bf5"
echo "Short SHA length: ${#SHORT_SHA}"

# Verify it's a valid hex string
if [[ $SHORT_SHA =~ ^[0-9a-f]+$ ]]; then
  echo "SHA format is valid (hexadecimal)"
else
  echo "SHA format is invalid"
fi

# Check the length - GitHub typically uses 7+ characters for short SHAs
if [ ${#SHORT_SHA} -ge 7 ]; then
  echo "Short SHA length is acceptable (minimum 7 characters)"
fi
```

Repository: williaby/image-preprocessing-detector

Length of output: 188

---

🌐 Web query:

`GitHub Actions workflow reference best practices full SHA vs short SHA security`

💡 Result:

Short answer: always pin third‑party actions and reusable workflows to the full (40‑char) commit SHA, not a tag/branch or short SHA, and enforce/audit SHA pinning across the org. This prevents silent supply‑chain changes and aligns with GitHub security guidance. [1][2][4]

Concise best‑practice checklist

- Pin actions/workflows to the full commit SHA (e.g., actions/checkout@<full‑sha>). Don’t use short SHAs. [1][2]
- Treat SHA pins as immutable references but rotate/update them regularly after you review the action’s change and security fixes. Use Dependabot/automation to propose updates. [4]
- Verify the SHA comes from the action’s canonical repo (not a fork). [1]
- Prefer audited/verified creators and avoid “unpinnable” actions that pull remote code or dependencies at runtime. [4]
- Enforce org/repo policies to require full‑SHA pinning and/or block specific actions/versions. Use allow/block lists for governance. [5]
- Audit action source code before pinning; prefer minimal permissions and use least‑privilege tokens (set GITHUB_TOKEN permissions). Set actions/checkout options (e.g., fetch‑depth, persist‑credentials) appropriately. [1][3]
- If you must use a tag/branch for convenience, do so only for highly trusted/maintained actions and combine with monitoring/alerts for updates. [1]

Relevant references

- GitHub Actions security guidance (pin to full‑length SHA + auditing). [1]
- GitHub change log: short‑SHA deprecation and rationale. [2]
- actions/checkout docs (checkout behavior, fetch‑depth, persist‑credentials). [3]
- GitHub Well‑Architected / action supply‑chain recommendations (unpinnable actions, automation). [4]
- GitHub policy support for SHA pinning and blocking actions. [5]

If you want, I can: (a) scan your repository workflows and list any non‑pinned/short‑SHA references, or (b) provide an automation workflow to enforce/update full‑SHA pins. Which would you prefer?

---

</details>

**Replace short SHA with full 40-character commit SHA for workflow reference.**

Using the short SHA `3bf8bf5` creates a supply-chain security risk. GitHub's official security guidance requires pinning reusable workflows to the full 40-character commit SHA, not short SHAs or tags, to prevent silent upstream changes. Update the reference to use the complete commit hash: `uses: ByronWilliamsCPA/.github/.github/workflows/python-release.yml@[full-sha]`

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
.github/workflows/release.yml around line 56: the workflow currently pins a
reusable workflow using a short SHA (`3bf8bf5`), which is insecure; update the
`uses:` reference to the full 40-character commit SHA of
ByronWilliamsCPA/.github/.github/workflows/python-release.yml (e.g. `uses:
ByronWilliamsCPA/.github/.github/workflows/python-release.yml@[full-40-char-sha]`),
commit that change, and ensure the full SHA is verified from the source
repository before pushing.
```

</details>

<!-- fingerprinting:phantom:medusa:ocelot -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 27. PR #56 - data/dataset.py

- **Status**: [x]
- **Severity**: medium
- **PR**: [#56 - feat: integrate org-level reusable workflows and resolve security issues](https://github.com/williaby/image-preprocessing-detector/pull/56)
- **Reviewer**: @coderabbitai
- **Date**: 2025-12-01
- **File**: `data/dataset.py`
- **Line**: 435

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟠 Major_

**Security inconsistency: `image_path` should also be validated.**

The `label_path` is validated with `validate_safe_path` (line 433), but `image_path` is not (line 422). If the split JSON file could be attacker-controlled or modified, this creates a path traversal vulnerability for image loading.

Apply this diff for consistency:

```diff
         sample = self.samples[idx]

         # Load image
-        image_path = Path(sample["image_path"])
+        image_path = validate_safe_path(sample["image_path"], must_exist=True)
         image = cv2.imread(str(image_path))
```

Additionally, consider validating paths in the original `IQADataset` class (lines 148-160) for consistency across the codebase.

<!-- suggestion_start -->

<details>
<summary>📝 Committable suggestion</summary>

> ‼️ **IMPORTANT**
> Carefully review the code before committing. Ensure that it accurately replaces the highlighted code, contains no missing lines, and has no issues with indentation. Thoroughly test & benchmark the code to ensure it meets the requirements.

```suggestion
        sample = self.samples[idx]

        # Load image
        image_path = validate_safe_path(sample["image_path"], must_exist=True)
        image = cv2.imread(str(image_path))

        if image is None:
            msg = f"Failed to load image at index {idx}: {image_path}"
            raise IndexError(msg)

        # Convert BGR to RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Load labels - validate path to prevent directory traversal
        label_path = validate_safe_path(sample["label_path"], must_exist=True)
        with open(label_path) as f:
            label_data = json.load(f)
```

</details>

<!-- suggestion_end -->

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In data/dataset.py around lines 419 to 435, the code reads image_path directly
from the sample and calls cv2.imread without validation, which risks path
traversal; update the code to validate image_path using
validate_safe_path(sample["image_path"], must_exist=True) (same as label_path)
before reading the file, then pass the validated path to cv2.imread; also apply
the same validation pattern to the IQADataset class around lines 148-160 to
ensure consistency across the codebase.
```

</details>

<!-- fingerprinting:phantom:medusa:ocelot -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 28. PR #56 - scripts/omnidocbench_baseline/models/adapters/resnet.py

- **Status**: [~]
- **Severity**: medium
- **PR**: [#56 - feat: integrate org-level reusable workflows and resolve security issues](https://github.com/williaby/image-preprocessing-detector/pull/56)
- **Reviewer**: @coderabbitai
- **Date**: 2025-12-01
- **File**: `scripts/omnidocbench_baseline/models/adapters/resnet.py`
- **Line**: 97

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟠 Major_

<details>
<summary>🧩 Analysis chain</summary>

🏁 Script executed:

```shell
# Check PyTorch version requirements in the project
find . -name "requirements*.txt" -o -name "setup.py" -o -name "pyproject.toml" | head -20
```

Repository: williaby/image-preprocessing-detector

Length of output: 278

---

🏁 Script executed:

```shell
# Search for torch.load usage patterns in the codebase
rg "torch\.load" --type py -B 2 -A 2
```

Repository: williaby/image-preprocessing-detector

Length of output: 3123

---

🏁 Script executed:

```shell
# Check if weights_only is already used elsewhere
rg "weights_only" --type py
```

Repository: williaby/image-preprocessing-detector

Length of output: 992

---

🌐 Web query:

`PyTorch torch.load weights_only parameter introduction version security`

💡 Result:

Short answer

- The weights_only option existed earlier, but PyTorch flipped its default to weights_only=True in the 2.6 change (so 2.6+ uses the safer mode by default). [1][2][3]

Security issue and fix

- A remote-code-execution (RCE) vulnerability was reported where torch.load(..., weights_only=True) could still be bypassed for legacy (.tar) checkpoints (CVE-2025-32434). The root cause: a legacy loading path (_legacy_load) didn’t consistently enforce the weights-only unpickler, allowing unsafe pickle semantics. [4][5]
- PyTorch fixed the issue in the 2.6+ line (the changelog/threads and security advisories point to the PR/commit that enforces weights-only behavior and require explicit allowlisting via torch.serialization.add_safe_globals). Upgrade to PyTorch ≥ 2.6 to get the fix. [2][5][1]

Practical recommendations

- Upgrade to PyTorch >= 2.6 (contains the fix and flips weights_only default to True). [2][1]
- When loading untrusted checkpoints, prefer safetensors or ensure weights_only=True and only allowlist specific globals via torch.serialization.add_safe_globals() if necessary. If you must disable weights_only, only do so for trusted files. [1][4]

Sources

1. torch.load docs (weights_only description).
2. PyTorch discussion/dev posts about flipping weights_only default and 2.6 change.
3. Notes in 2.6 docs about weights_only default flip.
4. CVE report / analysis of CVE-2025-32434.
5. GitLab advisory / PyTorch security advisory referencing the fixing commit.

---

🏁 Script executed:

```shell
cat requirements.txt requirements-dev.txt 2>/dev/null | grep -i torch
```

Repository: williaby/image-preprocessing-detector

Length of output: 63

---

🏁 Script executed:

```shell
cat pyproject.toml | grep -i torch -A 2 -B 2
```

Repository: williaby/image-preprocessing-detector

Length of output: 1730

---

🏁 Script executed:

```shell
cat -n scripts/omnidocbench_baseline/models/adapters/resnet.py | sed -n '80,100p'
```

Repository: williaby/image-preprocessing-detector

Length of output: 1147

---

🏁 Script executed:

```shell
# Check what's being loaded - is it just state_dict or full checkpoint?
rg "load_state_dict" scripts/omnidocbench_baseline/models/adapters/resnet.py -A 1 -B 1
```

Repository: williaby/image-preprocessing-detector

Length of output: 305

---

</details>

**Security: Add `weights_only=True` to `torch.load` for safer checkpoint loading.**

`torch.load` without `weights_only=True` can execute arbitrary code via pickle deserialization. Since this module loads checkpoints that may come from external sources, this poses a security risk. The project already implements this pattern in `src/image_preprocessing_detector/training/checkpoint_utils.py` and `generate_soft_labels.py`.

Apply this diff:

```diff
-                    state_dict = torch.load(checkpoint_path, map_location=self._device)
+                    state_dict = torch.load(
+                        checkpoint_path,
+                        map_location=self._device,
+                        weights_only=True,
+                    )
```

The project requires PyTorch >= 2.9.0, which fully supports the `weights_only` parameter, and since only state tensors are loaded (not custom objects), this change is safe and compatible.

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In scripts/omnidocbench_baseline/models/adapters/resnet.py around lines 86 to
97, the call to torch.load when loading a checkpoint uses pickle deserialization
and should be made safe by adding weights_only=True; update the torch.load
invocation to torch.load(checkpoint_path, map_location=self._device,
weights_only=True) so only tensor weights are deserialized while preserving
map_location and subsequent load_state_dict usage; leave the existence check,
logging, and fallback behavior unchanged.
```

</details>

<!-- fingerprinting:phantom:medusa:ocelot -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 29. PR #56 - modal/generate_pseudo_labels.py

- **Status**: [~]
- **Severity**: medium
- **PR**: [#56 - feat: integrate org-level reusable workflows and resolve security issues](https://github.com/williaby/image-preprocessing-detector/pull/56)
- **Reviewer**: @coderabbitai
- **Date**: 2025-12-01
- **File**: `modal/generate_pseudo_labels.py`
- **Line**: 504

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟠 Major_

**Credentials file not cleaned up after use.**

The temporary file containing GCS credentials is created with `delete=False` but never explicitly deleted. This could leave sensitive credentials on disk.

```diff
+import atexit
+
 # In _setup_gcs_credentials or process_gcs_dataset:
         with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
             f.write(base64.b64decode(gcp_sa_key).decode())
             credentials_path = f.name
         os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
+        # Register cleanup on exit
+        atexit.register(lambda: os.unlink(credentials_path) if os.path.exists(credentials_path) else None)
```

Alternatively, consider using a context manager pattern to ensure cleanup.

<!-- suggestion_start -->

<details>
<summary>📝 Committable suggestion</summary>

> ‼️ **IMPORTANT**
> Carefully review the code before committing. Ensure that it accurately replaces the highlighted code, contains no missing lines, and has no issues with indentation. Thoroughly test & benchmark the code to ensure it meets the requirements.

```suggestion
import atexit

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(base64.b64decode(gcp_sa_key).decode())
            credentials_path = f.name
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        # Register cleanup on exit
        atexit.register(lambda: os.unlink(credentials_path) if os.path.exists(credentials_path) else None)
```

</details>

<!-- suggestion_end -->

<!-- fingerprinting:phantom:medusa:ocelot -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 30. PR #56 - scripts/omnidocbench_baseline/extract_ground_truth.py

- **Status**: [~]
- **Severity**: medium
- **PR**: [#56 - feat: integrate org-level reusable workflows and resolve security issues](https://github.com/williaby/image-preprocessing-detector/pull/56)
- **Reviewer**: @coderabbitai
- **Date**: 2025-12-01
- **File**: `scripts/omnidocbench_baseline/extract_ground_truth.py`
- **Line**: 78

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟠 Major_

<details>
<summary>🧩 Analysis chain</summary>

🌐 Web query:

`HuggingFace trust_remote_code security risks arbitrary code execution`

💡 Result:

Short answer

- trust_remote_code=True tells transformers to run Python code from a model repo (custom model/tokenizer classes). That can execute arbitrary code from the repo on your machine, so it is a direct remote-code-execution (RCE) risk. [1][2][3]

Why it's risky (concise)

- Model repos can include arbitrary Python files; loading them executes that code locally. [1]
- Some past vulnerabilities/PoCs (unsafe deserialization, malicious models) have led to RCEs and public exploits (multiple CVEs and security reports in 2024). [3][4][5]

Practical mitigations

- Don't set trust_remote_code=True for untrusted repos. Inspect the repo’s Python files (modeling code) before enabling. [1]
- Prefer safetensors / avoid pickle-based weights; safetensors prevents code execution when loading weights. [1]
- Pin repository revision (commit hash) to avoid unnoticed updates. [1]
- Run untrusted models in isolated environments (containers, sandboxed VMs) with minimal privileges and no sensitive credentials mounted.
- Keep transformers and related packages updated; apply security patches for known CVEs. [3][4]
- Use automated scanning (malware/pickle scanners) and internal policy to whitelist trusted repos. [5][6]

References

- Hugging Face docs / security guidance (safetensors, verify code, pin revision). [1]
- BleepingComputer reporting on malicious models discovered on Hugging Face. [5]
- NVD / CVE entries and public advisories for transformers deserialization / RCE (examples: CVE-2024-3568, CVE-2024-11394). [3][4]
- Example malicious-test model repo on HF (demonstrates warning text + download). [6]

If you want, I can:

- check a specific model repo for suspicious files, or
- give a short script to scan/compare a repo before loading with trust_remote_code=True.

---

🏁 Script executed:

```shell
# Check the full context around the load_dataset call and any related comments
cat -n scripts/omnidocbench_baseline/extract_ground_truth.py | head -90 | tail -30
```

Repository: williaby/image-preprocessing-detector

Length of output: 1018

---

🏁 Script executed:

```shell
# Search for any comments or documentation about trust_remote_code
rg "trust_remote_code|OmniDocBench" scripts/omnidocbench_baseline/ -A 2 -B 2
```

Repository: williaby/image-preprocessing-detector

Length of output: 21067

---

🏁 Script executed:

```shell
# Check if there's a README or documentation explaining the security decisions
fd "README|SECURITY|docs" scripts/omnidocbench_baseline/ --type f
```

Repository: williaby/image-preprocessing-detector

Length of output: 120

---

</details>

**Document security implications of `trust_remote_code=True` or make it configurable.**

The `trust_remote_code=True` flag at line 77 enables execution of code from the remote dataset repository. While OmniDocBench is an official dataset that requires this flag for proper loading, this remains a remote code execution vector. Add a comment explaining why it's necessary, or better yet, make it a CLI option (defaulting to `True` for OmniDocBench but allowing users to disable it or pin a specific revision for isolation purposes).

<!-- fingerprinting:phantom:medusa:ocelot -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 31. PR #56 - src/image_preprocessing_detector/ingestion/office_processor.py

- **Status**: [x]
- **Severity**: medium
- **PR**: [#56 - feat: integrate org-level reusable workflows and resolve security issues](https://github.com/williaby/image-preprocessing-detector/pull/56)
- **Reviewer**: @coderabbitai
- **Date**: 2025-12-01
- **File**: `src/image_preprocessing_detector/ingestion/office_processor.py`
- **Line**: 447

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟠 Major_

**Missing path validation in `extract_images_to_files`.**

The PR objective mentions path traversal fixes, but this method doesn't validate `output_dir` before creating directories and writing files. An attacker-controlled `output_dir` could write files outside intended locations.

```diff
     def extract_images_to_files(
         self,
         doc_info: OfficeDocumentInfo,
         output_dir: str | Path,
         output_format: str = "png",
     ) -> list[str]:
         """Extract embedded images to files."""
         import cv2
+        from image_preprocessing_detector.utils.path_security import validate_safe_path

-        output_path = Path(output_dir)
+        output_path = validate_safe_path(output_dir)
         output_path.mkdir(parents=True, exist_ok=True)

         saved_paths: list[str] = []

         for img in doc_info.images:
             filename = f"embedded_{img.image_index:03d}.{output_format}"
-            file_path = output_path / filename
+            file_path = validate_safe_path(
+                output_path / filename, allowed_base=output_path
+            )

             cv2.imwrite(str(file_path), img.image)
             saved_paths.append(str(file_path))
```

> Committable suggestion skipped: line range outside the PR's diff.

<!-- fingerprinting:phantom:medusa:ocelot -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 32. PR #54 - docs/MODEL_STORAGE.md

- **Status**: [~]
- **Severity**: medium
- **PR**: [#54 - chore: merge markdownlint fixes and resolve compatibility issues](https://github.com/williaby/image-preprocessing-detector/pull/54)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-26
- **File**: `docs/MODEL_STORAGE.md`
- **Line**: 194

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟠 Major_

**Fix ordered list numbering: line 190 should be ` 2. `, not ` 1. `.**

The prerequisites section has two consecutive list items both numbered `1.` (lines 184 and 190). Per MD029 (ordered list prefix fix mentioned in PR objectives), the second item must be numbered `2.` to form a valid ordered list.

Apply this diff to correct the list numbering:

```diff
1. **HF Token**: Set `HF_TOKEN` environment variable

   ```bash
   export HF_TOKEN=your_huggingface_token
   ```

-1. **GCS Access**: Ensure `GOOGLE_APPLICATION_CREDENTIALS` is set
+2. **GCS Access**: Ensure `GOOGLE_APPLICATION_CREDENTIALS` is set

   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
   ```

```

<details>
<summary>🤖 Prompt for AI Agents</summary>

```

In docs/MODEL_STORAGE.md around lines 184 to 194 the ordered list numbering is
wrong: both prerequisites items are labeled "1." — update the second list item
(line ~190) to "2." so the ordered list is sequential, leaving the surrounding
markdown and code blocks unchanged.

```

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 33. PR #53 - docs/planning/workflows_opus/SCOPE_RESOLUTION_RECOMMENDATIONS.md

- **Status**: [~]
- **Severity**: medium
- **PR**: [#53 - feat: Phase 5 testing, documentation, and infrastructure improvements](https://github.com/williaby/image-preprocessing-detector/pull/53)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-26
- **File**: `docs/planning/workflows_opus/SCOPE_RESOLUTION_RECOMMENDATIONS.md`
- **Line**: 310

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟡 Minor_

**Use standard text formatting for document footer.**

The document footer (line 295) uses emphasis markdown (`*...*`), which is interpreted as semantic emphasis rather than a byline. For better semantic clarity and to resolve linter warnings, use standard text formatting.



Apply this fix:

```diff
-*Recommendations prepared by Claude Opus 4.5 on 2025-01-25*
+---
+
+Recommendations prepared by Claude Opus 4.5 on 2025-01-25
```

<!-- suggestion_start -->

<details>
<summary>📝 Committable suggestion</summary>

> ‼️ **IMPORTANT**
> Carefully review the code before committing. Ensure that it accurately replaces the highlighted code, contains no missing lines, and has no issues with indentation. Thoroughly test & benchmark the code to ensure it meets the requirements.

```suggestion
| Artifact Promotion | ADD | Complete implementation exists | TBD |
| Layout Model | DocLayout-YOLO | Config is authoritative | TBD |

---

---

Recommendations prepared by Claude Opus 4.5 on 2025-01-25
```

</details>

<!-- suggestion_end -->

<details>
<summary>🧰 Tools</summary>

<details>
<summary>🪛 markdownlint-cli2 (0.18.1)</summary>

295-295: Emphasis used instead of a heading

(MD036, no-emphasis-as-heading)

</details>

</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In docs/planning/workflows_opus/SCOPE_RESOLUTION_RECOMMENDATIONS.md around lines
290 to 295 the footer line is wrapped in emphasis markdown (*...*), which causes
semantic/emphasis rendering and linter warnings; replace the emphasized footer
with plain text (remove the surrounding asterisks) and ensure it remains a
simple sentence like: Recommendations prepared by Claude Opus 4.5 on 2025-01-25.
```

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 34. PR #53 - src/image_preprocessing_detector/api/**init**.py

- **Status**: [x]
- **Severity**: medium
- **PR**: [#53 - feat: Phase 5 testing, documentation, and infrastructure improvements](https://github.com/williaby/image-preprocessing-detector/pull/53)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-26
- **File**: `src/image_preprocessing_detector/api/__init__.py`
- **Line**: 11

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟡 Minor_

<details>
<summary>🧩 Analysis chain</summary>

Script executed:

```shell
#!/bin/bash
# Search for status and result endpoint implementations in the API routes
echo "=== Searching for /status endpoint ==="
rg -n "status" src/image_preprocessing_detector/api/ -A 2 -B 2

echo -e "\n=== Searching for /result endpoint ==="
rg -n "result" src/image_preprocessing_detector/api/ -A 2 -B 2

echo -e "\n=== Listing API files structure ==="
find src/image_preprocessing_detector/api/ -type f -name "*.py" | head -20
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stdout:

```
=== Searching for /status endpoint ===
src/image_preprocessing_detector/api/models.py-140-    """Response for single document processing."""
src/image_preprocessing_detector/api/models.py-141-
src/image_preprocessing_detector/api/models.py:142:    status: ProcessingStatus = Field(description="Processing status")
src/image_preprocessing_detector/api/models.py-143-    result: ProcessingResult | None = Field(
src/image_preprocessing_detector/api/models.py-144-        default=None, description="Processing result (if completed)"
--
src/image_preprocessing_detector/api/models.py-170-
src/image_preprocessing_detector/api/models.py-171-    job_id: str = Field(description="Unique job identifier")
src/image_preprocessing_detector/api/models.py:172:    status: ProcessingStatus = Field(description="Job status")
src/image_preprocessing_detector/api/models.py-173-    total_files: int = Field(description="Total files in batch")
src/image_preprocessing_detector/api/models.py-174-    processed_files: int = Field(default=0, description="Files processed so far")
--
src/image_preprocessing_detector/api/models.py-188-
src/image_preprocessing_detector/api/models.py-189-    job_id: str = Field(description="Unique job identifier")
src/image_preprocessing_detector/api/models.py:190:    status: ProcessingStatus = Field(description="Job status")
src/image_preprocessing_detector/api/models.py-191-    results: list[ProcessingResult] = Field(
src/image_preprocessing_detector/api/models.py-192-        default_factory=list, description="Processing results"
--
src/image_preprocessing_detector/api/routes/process.py-15-
src/image_preprocessing_detector/api/routes/process.py-16-import structlog
src/image_preprocessing_detector/api/routes/process.py:17:from fastapi import APIRouter, File, UploadFile, status
src/image_preprocessing_detector/api/routes/process.py-18-from fastapi.responses import JSONResponse
src/image_preprocessing_detector/api/routes/process.py-19-
--
src/image_preprocessing_detector/api/routes/process.py-303-        )
src/image_preprocessing_detector/api/routes/process.py-304-        return JSONResponse(
src/image_preprocessing_detector/api/routes/process.py:305:            status_code=status.HTTP_400_BAD_REQUEST,
src/image_preprocessing_detector/api/routes/process.py-306-            content=ProcessResponse(
src/image_preprocessing_detector/api/routes/process.py:307:                status=ProcessingStatus.FAILED,
src/image_preprocessing_detector/api/routes/process.py-308-                error=validation_error,
src/image_preprocessing_detector/api/routes/process.py-309-            ).model_dump(),
--
src/image_preprocessing_detector/api/routes/process.py-335-                )
src/image_preprocessing_detector/api/routes/process.py-336-                return JSONResponse(
src/image_preprocessing_detector/api/routes/process.py:337:                    status_code=status.HTTP_400_BAD_REQUEST,
src/image_preprocessing_detector/api/routes/process.py-338-                    content=ProcessResponse(
src/image_preprocessing_detector/api/routes/process.py:339:                        status=ProcessingStatus.FAILED,
src/image_preprocessing_detector/api/routes/process.py-340-                        error=error,
src/image_preprocessing_detector/api/routes/process.py-341-                    ).model_dump(),
--
src/image_preprocessing_detector/api/routes/process.py-350-                )
src/image_preprocessing_detector/api/routes/process.py-351-                return JSONResponse(
src/image_preprocessing_detector/api/routes/process.py:352:                    status_code=status.HTTP_400_BAD_REQUEST,
src/image_preprocessing_detector/api/routes/process.py-353-                    content=ProcessResponse(
src/image_preprocessing_detector/api/routes/process.py:354:                        status=ProcessingStatus.FAILED,
src/image_preprocessing_detector/api/routes/process.py-355-                        error=error,
src/image_preprocessing_detector/api/routes/process.py-356-                    ).model_dump(),
--
src/image_preprocessing_detector/api/routes/process.py-376-
src/image_preprocessing_detector/api/routes/process.py-377-        return ProcessResponse(
src/image_preprocessing_detector/api/routes/process.py:378:            status=ProcessingStatus.COMPLETED,
src/image_preprocessing_detector/api/routes/process.py-379-            result=result,
src/image_preprocessing_detector/api/routes/process.py-380-        )
--
src/image_preprocessing_detector/api/routes/process.py-388-        )
src/image_preprocessing_detector/api/routes/process.py-389-        return JSONResponse(
src/image_preprocessing_detector/api/routes/process.py:390:            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
src/image_preprocessing_detector/api/routes/process.py-391-            content=ProcessResponse(
src/image_preprocessing_detector/api/routes/process.py:392:                status=ProcessingStatus.FAILED,
src/image_preprocessing_detector/api/routes/process.py-393-                error=error,
src/image_preprocessing_detector/api/routes/process.py-394-            ).model_dump(),
--
src/image_preprocessing_detector/api/routes/health.py-12-
src/image_preprocessing_detector/api/routes/health.py-13-import structlog
src/image_preprocessing_detector/api/routes/health.py:14:from fastapi import APIRouter, Response, status
src/image_preprocessing_detector/api/routes/health.py-15-from pydantic import BaseModel, Field
src/image_preprocessing_detector/api/routes/health.py-16-
--
src/image_preprocessing_detector/api/routes/health.py-30-    """Response model for health check."""
src/image_preprocessing_detector/api/routes/health.py-31-
src/image_preprocessing_detector/api/routes/health.py:32:    status: str = Field(description="Health status: healthy or unhealthy")
src/image_preprocessing_detector/api/routes/health.py-33-    timestamp: datetime = Field(description="Current server timestamp")
src/image_preprocessing_detector/api/routes/health.py-34-    uptime_seconds: float | None = Field(
--
src/image_preprocessing_detector/api/routes/health.py-40-    """Response model for readiness check."""
src/image_preprocessing_detector/api/routes/health.py-41-
src/image_preprocessing_detector/api/routes/health.py:42:    status: str = Field(description="Ready status: ready or not_ready")
src/image_preprocessing_detector/api/routes/health.py-43-    timestamp: datetime = Field(description="Current server timestamp")
src/image_preprocessing_detector/api/routes/health.py-44-    checks: dict[str, bool] = Field(description="Individual readiness check results")
--
src/image_preprocessing_detector/api/routes/health.py-86-
src/image_preprocessing_detector/api/routes/health.py-87-    Returns:
src/image_preprocessing_detector/api/routes/health.py:88:        HealthResponse with status and timestamp.
src/image_preprocessing_detector/api/routes/health.py-89-    """
src/image_preprocessing_detector/api/routes/health.py-90-    logger.debug("health_check_called")
src/image_preprocessing_detector/api/routes/health.py-91-    return HealthResponse(
src/image_preprocessing_detector/api/routes/health.py:92:        status="healthy",
src/image_preprocessing_detector/api/routes/health.py-93-        timestamp=utc_now(),
src/image_preprocessing_detector/api/routes/health.py-94-        uptime_seconds=get_uptime_seconds(),
--
src/image_preprocessing_detector/api/routes/health.py-115-
src/image_preprocessing_detector/api/routes/health.py-116-    Args:
src/image_preprocessing_detector/api/routes/health.py:117:        response: FastAPI response object for setting status code.
src/image_preprocessing_detector/api/routes/health.py-118-
src/image_preprocessing_detector/api/routes/health.py-119-    Returns:
--
src/image_preprocessing_detector/api/routes/health.py-168-        checks["configuration"] = False
src/image_preprocessing_detector/api/routes/health.py-169-
src/image_preprocessing_detector/api/routes/health.py:170:    # Determine overall ready status
src/image_preprocessing_detector/api/routes/health.py-171-    is_ready = all(checks.values())
src/image_preprocessing_detector/api/routes/health.py:172:    status_str = "ready" if is_ready else "not_ready"
src/image_preprocessing_detector/api/routes/health.py-173-
src/image_preprocessing_detector/api/routes/health.py-174-    if not is_ready:
src/image_preprocessing_detector/api/routes/health.py:175:        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
src/image_preprocessing_detector/api/routes/health.py-176-        logger.warning("readiness_check_failed", checks=checks)
src/image_preprocessing_detector/api/routes/health.py-177-    else:
--
src/image_preprocessing_detector/api/routes/health.py-179-
src/image_preprocessing_detector/api/routes/health.py-180-    return ReadyResponse(
src/image_preprocessing_detector/api/routes/health.py:181:        status=status_str,
src/image_preprocessing_detector/api/routes/health.py-182-        timestamp=utc_now(),
src/image_preprocessing_detector/api/routes/health.py-183-        checks=checks,
--
src/image_preprocessing_detector/api/__init__.py-4-- Single document processing (/process)
src/image_preprocessing_detector/api/__init__.py-5-- Batch document processing (/batch)
src/image_preprocessing_detector/api/__init__.py:6:- Job status tracking (/status, /result)
src/image_preprocessing_detector/api/__init__.py-7-"""
src/image_preprocessing_detector/api/__init__.py-8-
--
src/image_preprocessing_detector/api/middleware.py-104-            "request_completed",
src/image_preprocessing_detector/api/middleware.py-105-            **log_context,
src/image_preprocessing_detector/api/middleware.py:106:            status_code=response.status_code,
src/image_preprocessing_detector/api/middleware.py-107-            duration_ms=round(duration_ms, 2),
src/image_preprocessing_detector/api/middleware.py-108-        )
--
src/image_preprocessing_detector/api/middleware.py-245-            )
src/image_preprocessing_detector/api/middleware.py-246-            return JSONResponse(
src/image_preprocessing_detector/api/middleware.py:247:                status_code=401,
src/image_preprocessing_detector/api/middleware.py-248-                content={
src/image_preprocessing_detector/api/middleware.py-249-                    "error": "unauthorized",
--
src/image_preprocessing_detector/api/middleware.py-260-            )
src/image_preprocessing_detector/api/middleware.py-261-            return JSONResponse(
src/image_preprocessing_detector/api/middleware.py:262:                status_code=403,
src/image_preprocessing_detector/api/middleware.py-263-                content={
src/image_preprocessing_detector/api/middleware.py-264-                    "error": "forbidden",
--
src/image_preprocessing_detector/api/middleware.py-393-
src/image_preprocessing_detector/api/middleware.py-394-            return JSONResponse(
src/image_preprocessing_detector/api/middleware.py:395:                status_code=429,
src/image_preprocessing_detector/api/middleware.py-396-                content={
src/image_preprocessing_detector/api/middleware.py-397-                    "error": "rate_limit_exceeded",
--
src/image_preprocessing_detector/api/routes/batch.py-3-Sprint 5.2.3: Batch endpoints
src/image_preprocessing_detector/api/routes/batch.py-4-- POST /batch - Submit batch processing job
src/image_preprocessing_detector/api/routes/batch.py:5:- GET /batch/{job_id}/status - Get job status
src/image_preprocessing_detector/api/routes/batch.py-6-- GET /batch/{job_id}/result - Get job results
src/image_preprocessing_detector/api/routes/batch.py-7-"""
--
src/image_preprocessing_detector/api/routes/batch.py-15-
src/image_preprocessing_detector/api/routes/batch.py-16-import structlog
src/image_preprocessing_detector/api/routes/batch.py:17:from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile, status
src/image_preprocessing_detector/api/routes/batch.py-18-from fastapi.responses import JSONResponse
src/image_preprocessing_detector/api/routes/batch.py-19-
--
src/image_preprocessing_detector/api/routes/batch.py-107-                {
src/image_preprocessing_detector/api/routes/batch.py-108-                    "processed_files": idx + 1,
src/image_preprocessing_detector/api/routes/batch.py:109:                    "status": ProcessingStatus.PROCESSING,
src/image_preprocessing_detector/api/routes/batch.py-110-                },
src/image_preprocessing_detector/api/routes/batch.py-111-            )
--
src/image_preprocessing_detector/api/routes/batch.py-140-        job_id,
src/image_preprocessing_detector/api/routes/batch.py-141-        {
src/image_preprocessing_detector/api/routes/batch.py:142:            "status": ProcessingStatus.COMPLETED,
src/image_preprocessing_detector/api/routes/batch.py-143-            "results": results,
src/image_preprocessing_detector/api/routes/batch.py-144-            "errors": errors,
--
src/image_preprocessing_detector/api/routes/batch.py-184-
src/image_preprocessing_detector/api/routes/batch.py-185-    Returns:
src/image_preprocessing_detector/api/routes/batch.py:186:        BatchJobStatus with job ID and initial status.
src/image_preprocessing_detector/api/routes/batch.py-187-    """
src/image_preprocessing_detector/api/routes/batch.py-188-    settings = get_api_settings()
--
src/image_preprocessing_detector/api/routes/batch.py-203-        )
src/image_preprocessing_detector/api/routes/batch.py-204-        return JSONResponse(
src/image_preprocessing_detector/api/routes/batch.py:205:            status_code=status.HTTP_400_BAD_REQUEST,
src/image_preprocessing_detector/api/routes/batch.py-206-            content=error.model_dump(),
src/image_preprocessing_detector/api/routes/batch.py-207-        )
--
src/image_preprocessing_detector/api/routes/batch.py-214-        )
src/image_preprocessing_detector/api/routes/batch.py-215-        return JSONResponse(
src/image_preprocessing_detector/api/routes/batch.py:216:            status_code=status.HTTP_400_BAD_REQUEST,
src/image_preprocessing_detector/api/routes/batch.py-217-            content=error.model_dump(),
src/image_preprocessing_detector/api/routes/batch.py-218-        )
--
src/image_preprocessing_detector/api/routes/batch.py-225-            validation_error.correlation_id = correlation_id
src/image_preprocessing_detector/api/routes/batch.py-226-            return JSONResponse(
src/image_preprocessing_detector/api/routes/batch.py:227:                status_code=status.HTTP_400_BAD_REQUEST,
src/image_preprocessing_detector/api/routes/batch.py-228-                content=validation_error.model_dump(),
src/image_preprocessing_detector/api/routes/batch.py-229-            )
--
src/image_preprocessing_detector/api/routes/batch.py-237-            )
src/image_preprocessing_detector/api/routes/batch.py-238-            return JSONResponse(
src/image_preprocessing_detector/api/routes/batch.py:239:                status_code=status.HTTP_400_BAD_REQUEST,
src/image_preprocessing_detector/api/routes/batch.py-240-                content=error.model_dump(),
src/image_preprocessing_detector/api/routes/batch.py-241-            )
--
src/image_preprocessing_detector/api/routes/batch.py-249-    _job_store[job_id] = {
src/image_preprocessing_detector/api/routes/batch.py-250-        "job_id": job_id,
src/image_preprocessing_detector/api/routes/batch.py:251:        "status": ProcessingStatus.PENDING,
src/image_preprocessing_detector/api/routes/batch.py-252-        "total_files": len(files_data),
src/image_preprocessing_detector/api/routes/batch.py-253-        "processed_files": 0,
--
src/image_preprocessing_detector/api/routes/batch.py-271-    background_tasks.add_task(process_batch_job, job_id, files_data, options)
src/image_preprocessing_detector/api/routes/batch.py-272-
src/image_preprocessing_detector/api/routes/batch.py:273:    # Update status to processing
src/image_preprocessing_detector/api/routes/batch.py:274:    _update_job(job_id, {"status": ProcessingStatus.PROCESSING})
src/image_preprocessing_detector/api/routes/batch.py-275-
src/image_preprocessing_detector/api/routes/batch.py-276-    logger.info("batch_job_created", job_id=job_id, num_files=len(files_data))
--
src/image_preprocessing_detector/api/routes/batch.py-278-    return BatchJobStatus(
src/image_preprocessing_detector/api/routes/batch.py-279-        job_id=job_id,
src/image_preprocessing_detector/api/routes/batch.py:280:        status=ProcessingStatus.PROCESSING,
src/image_preprocessing_detector/api/routes/batch.py-281-        total_files=len(files_data),
src/image_preprocessing_detector/api/routes/batch.py-282-        processed_files=0,
--
src/image_preprocessing_detector/api/routes/batch.py-288-
src/image_preprocessing_detector/api/routes/batch.py-289-@router.get(
src/image_preprocessing_detector/api/routes/batch.py:290:    "/{job_id}/status",
src/image_preprocessing_detector/api/routes/batch.py-291-    response_model=BatchJobStatus,
src/image_preprocessing_detector/api/routes/batch.py:292:    summary="Get batch job status",
src/image_preprocessing_detector/api/routes/batch.py:293:    description="Get the current status of a batch processing job.",
src/image_preprocessing_detector/api/routes/batch.py-294-    responses={
src/image_preprocessing_detector/api/routes/batch.py:295:        200: {"description": "Job status retrieved"},
src/image_preprocessing_detector/api/routes/batch.py-296-        404: {"description": "Job not found"},
src/image_preprocessing_detector/api/routes/batch.py-297-    },
src/image_preprocessing_detector/api/routes/batch.py-298-)
src/image_preprocessing_detector/api/routes/batch.py:299:async def get_batch_status(job_id: str) -> BatchJobStatus:
src/image_preprocessing_detector/api/routes/batch.py:300:    """Get the status of a batch job.
src/image_preprocessing_detector/api/routes/batch.py-301-
src/image_preprocessing_detector/api/routes/batch.py-302-    Args:
--
src/image_preprocessing_detector/api/routes/batch.py-309-    if not job:
src/image_preprocessing_detector/api/routes/batch.py-310-        raise HTTPException(
src/image_preprocessing_detector/api/routes/batch.py:311:            status_code=status.HTTP_404_NOT_FOUND,
src/image_preprocessing_detector/api/routes/batch.py-312-            detail=f"Job {job_id} not found",
src/image_preprocessing_detector/api/routes/batch.py-313-        )
--
src/image_preprocessing_detector/api/routes/batch.py-315-    return BatchJobStatus(
src/image_preprocessing_detector/api/routes/batch.py-316-        job_id=job["job_id"],
src/image_preprocessing_detector/api/routes/batch.py:317:        status=job["status"],
src/image_preprocessing_detector/api/routes/batch.py-318-        total_files=job["total_files"],
src/image_preprocessing_detector/api/routes/batch.py-319-        processed_files=job["processed_files"],
--
src/image_preprocessing_detector/api/routes/batch.py-354-    if not job:
src/image_preprocessing_detector/api/routes/batch.py-355-        raise HTTPException(
src/image_preprocessing_detector/api/routes/batch.py:356:            status_code=status.HTTP_404_NOT_FOUND,
src/image_preprocessing_detector/api/routes/batch.py-357-            detail=f"Job {job_id} not found",
src/image_preprocessing_detector/api/routes/batch.py-358-        )
src/image_preprocessing_detector/api/routes/batch.py-359-
src/image_preprocessing_detector/api/routes/batch.py:360:    if job["status"] not in (ProcessingStatus.COMPLETED, ProcessingStatus.FAILED):
src/image_preprocessing_detector/api/routes/batch.py-361-        return JSONResponse(
src/image_preprocessing_detector/api/routes/batch.py:362:            status_code=425,  # Too Early
src/image_preprocessing_detector/api/routes/batch.py-363-            content={
src/image_preprocessing_detector/api/routes/batch.py-364-                "detail": f"Job {job_id} is still processing",
src/image_preprocessing_detector/api/routes/batch.py:365:                "status": job["status"].value,
src/image_preprocessing_detector/api/routes/batch.py-366-                "progress": f"{job['processed_files']}/{job['total_files']}",
src/image_preprocessing_detector/api/routes/batch.py-367-            },
--
src/image_preprocessing_detector/api/routes/batch.py-374-    return BatchJobResult(
src/image_preprocessing_detector/api/routes/batch.py-375-        job_id=job_id,
src/image_preprocessing_detector/api/routes/batch.py:376:        status=job["status"],
src/image_preprocessing_detector/api/routes/batch.py-377-        results=paginated_results,
src/image_preprocessing_detector/api/routes/batch.py-378-        errors=job.get("errors", []),
--
src/image_preprocessing_detector/api/routes/batch.py-401-    if job_id not in _job_store:
src/image_preprocessing_detector/api/routes/batch.py-402-        raise HTTPException(
src/image_preprocessing_detector/api/routes/batch.py:403:            status_code=status.HTTP_404_NOT_FOUND,
src/image_preprocessing_detector/api/routes/batch.py-404-            detail=f"Job {job_id} not found",
src/image_preprocessing_detector/api/routes/batch.py-405-        )

=== Searching for /result endpoint ===
src/image_preprocessing_detector/api/routes/health.py-42-    status: str = Field(description="Ready status: ready or not_ready")
src/image_preprocessing_detector/api/routes/health.py-43-    timestamp: datetime = Field(description="Current server timestamp")
src/image_preprocessing_detector/api/routes/health.py:44:    checks: dict[str, bool] = Field(description="Individual readiness check results")
src/image_preprocessing_detector/api/routes/health.py-45-    device: dict[str, Any] = Field(description="Available compute device information")
src/image_preprocessing_detector/api/routes/health.py-46-
--
src/image_preprocessing_detector/api/routes/health.py-118-
src/image_preprocessing_detector/api/routes/health.py-119-    Returns:
src/image_preprocessing_detector/api/routes/health.py:120:        ReadyResponse with detailed check results.
src/image_preprocessing_detector/api/routes/health.py-121-    """
src/image_preprocessing_detector/api/routes/health.py-122-    logger.debug("readiness_check_called")
--
src/image_preprocessing_detector/api/routes/process.py-104-    document_id = str(uuid.uuid4())
src/image_preprocessing_detector/api/routes/process.py-105-
src/image_preprocessing_detector/api/routes/process.py:106:    # Initialize result containers
src/image_preprocessing_detector/api/routes/process.py-107-    pages: list[PageSummary] = []
src/image_preprocessing_detector/api/routes/process.py-108-    dqs: DQSSummary | None = None
--
src/image_preprocessing_detector/api/routes/process.py-151-
src/image_preprocessing_detector/api/routes/process.py-152-            # Classify PDF type
src/image_preprocessing_detector/api/routes/process.py:153:            pdf_type_result = classifier.classify(file_path)
src/image_preprocessing_detector/api/routes/process.py:154:            pdf_type = pdf_type_result.value if pdf_type_result else None
src/image_preprocessing_detector/api/routes/process.py-155-
src/image_preprocessing_detector/api/routes/process.py-156-            # Load pages - PDFLoader.load() returns PageImage objects
--
src/image_preprocessing_detector/api/routes/process.py-176-        for idx, (page_image, width, height) in enumerate(page_data):
src/image_preprocessing_detector/api/routes/process.py-177-            # Run IQA detectors
src/image_preprocessing_detector/api/routes/process.py:178:            blur_result = blur_detector.detect(page_image)
src/image_preprocessing_detector/api/routes/process.py:179:            noise_result = noise_detector.detect(page_image)
src/image_preprocessing_detector/api/routes/process.py:180:            contrast_result = contrast_detector.detect(page_image)
src/image_preprocessing_detector/api/routes/process.py-181-
src/image_preprocessing_detector/api/routes/process.py-182-            # Calculate normalized scores
src/image_preprocessing_detector/api/routes/process.py-183-            iqa_metrics = normalize_classical_iqa(
src/image_preprocessing_detector/api/routes/process.py:184:                blur_result=blur_result,
src/image_preprocessing_detector/api/routes/process.py:185:                contrast_result=contrast_result,
src/image_preprocessing_detector/api/routes/process.py:186:                noise_result=noise_result,
src/image_preprocessing_detector/api/routes/process.py-187-            )
src/image_preprocessing_detector/api/routes/process.py-188-
--
src/image_preprocessing_detector/api/routes/process.py-201-            issues_count = sum(
src/image_preprocessing_detector/api/routes/process.py-202-                [
src/image_preprocessing_detector/api/routes/process.py:203:                    1 if blur_result.is_blurred else 0,
src/image_preprocessing_detector/api/routes/process.py:204:                    1 if noise_result.is_noisy else 0,
src/image_preprocessing_detector/api/routes/process.py:205:                    1 if contrast_result.is_low_contrast else 0,
src/image_preprocessing_detector/api/routes/process.py-206-                ]
src/image_preprocessing_detector/api/routes/process.py-207-            )
--
src/image_preprocessing_detector/api/routes/process.py-280-
src/image_preprocessing_detector/api/routes/process.py-281-    Returns:
src/image_preprocessing_detector/api/routes/process.py:282:        ProcessResponse with processing results.
src/image_preprocessing_detector/api/routes/process.py-283-    """
src/image_preprocessing_detector/api/routes/process.py-284-    settings = get_api_settings()
--
src/image_preprocessing_detector/api/routes/process.py-362-
src/image_preprocessing_detector/api/routes/process.py-363-        # Process the document
src/image_preprocessing_detector/api/routes/process.py:364:        result = await process_document(
src/image_preprocessing_detector/api/routes/process.py-365-            file_path=tmp_path,
src/image_preprocessing_detector/api/routes/process.py-366-            file_name=file.filename or "document",
--
src/image_preprocessing_detector/api/routes/process.py-370-        logger.info(
src/image_preprocessing_detector/api/routes/process.py-371-            "process_completed",
src/image_preprocessing_detector/api/routes/process.py:372:            document_id=result.document_id,
src/image_preprocessing_detector/api/routes/process.py:373:            num_pages=result.num_pages,
src/image_preprocessing_detector/api/routes/process.py:374:            processing_time_ms=result.processing_time_ms,
src/image_preprocessing_detector/api/routes/process.py-375-        )
src/image_preprocessing_detector/api/routes/process.py-376-
src/image_preprocessing_detector/api/routes/process.py-377-        return ProcessResponse(
src/image_preprocessing_detector/api/routes/process.py-378-            status=ProcessingStatus.COMPLETED,
src/image_preprocessing_detector/api/routes/process.py:379:            result=result,
src/image_preprocessing_detector/api/routes/process.py-380-        )
src/image_preprocessing_detector/api/routes/process.py-381-
--
src/image_preprocessing_detector/api/__init__.py-4-- Single document processing (/process)
src/image_preprocessing_detector/api/__init__.py-5-- Batch document processing (/batch)
src/image_preprocessing_detector/api/__init__.py:6:- Job status tracking (/status, /result)
src/image_preprocessing_detector/api/__init__.py-7-"""
src/image_preprocessing_detector/api/__init__.py-8-
--
src/image_preprocessing_detector/api/models.py-141-
src/image_preprocessing_detector/api/models.py-142-    status: ProcessingStatus = Field(description="Processing status")
src/image_preprocessing_detector/api/models.py:143:    result: ProcessingResult | None = Field(
src/image_preprocessing_detector/api/models.py:144:        default=None, description="Processing result (if completed)"
src/image_preprocessing_detector/api/models.py-145-    )
src/image_preprocessing_detector/api/models.py-146-    metadata_url: str | None = Field(
--
src/image_preprocessing_detector/api/models.py-189-    job_id: str = Field(description="Unique job identifier")
src/image_preprocessing_detector/api/models.py-190-    status: ProcessingStatus = Field(description="Job status")
src/image_preprocessing_detector/api/models.py:191:    results: list[ProcessingResult] = Field(
src/image_preprocessing_detector/api/models.py:192:        default_factory=list, description="Processing results"
src/image_preprocessing_detector/api/models.py-193-    )
src/image_preprocessing_detector/api/models.py-194-    errors: list[ErrorResponse] = Field(
--
src/image_preprocessing_detector/api/routes/batch.py-4-- POST /batch - Submit batch processing job
src/image_preprocessing_detector/api/routes/batch.py-5-- GET /batch/{job_id}/status - Get job status
src/image_preprocessing_detector/api/routes/batch.py:6:- GET /batch/{job_id}/result - Get job results
src/image_preprocessing_detector/api/routes/batch.py-7-"""
src/image_preprocessing_detector/api/routes/batch.py-8-
--
src/image_preprocessing_detector/api/routes/batch.py-83-    logger.info("batch_job_started", job_id=job_id, num_files=len(files_data))
src/image_preprocessing_detector/api/routes/batch.py-84-
src/image_preprocessing_detector/api/routes/batch.py:85:    results: list[ProcessingResult] = []
src/image_preprocessing_detector/api/routes/batch.py-86-    errors: list[ErrorResponse] = []
src/image_preprocessing_detector/api/routes/batch.py-87-
--
src/image_preprocessing_detector/api/routes/batch.py-96-            try:
src/image_preprocessing_detector/api/routes/batch.py-97-                # Process the document
src/image_preprocessing_detector/api/routes/batch.py:98:                result = await process_document(tmp_path, filename, options)
src/image_preprocessing_detector/api/routes/batch.py:99:                results.append(result)
src/image_preprocessing_detector/api/routes/batch.py-100-            finally:
src/image_preprocessing_detector/api/routes/batch.py-101-                # Cleanup
--
src/image_preprocessing_detector/api/routes/batch.py-136-    elapsed_ms = (time.perf_counter() - start_time) * 1000
src/image_preprocessing_detector/api/routes/batch.py-137-
src/image_preprocessing_detector/api/routes/batch.py:138:    # Update job with final results
src/image_preprocessing_detector/api/routes/batch.py-139-    _update_job(
src/image_preprocessing_detector/api/routes/batch.py-140-        job_id,
src/image_preprocessing_detector/api/routes/batch.py-141-        {
src/image_preprocessing_detector/api/routes/batch.py-142-            "status": ProcessingStatus.COMPLETED,
src/image_preprocessing_detector/api/routes/batch.py:143:            "results": results,
src/image_preprocessing_detector/api/routes/batch.py-144-            "errors": errors,
src/image_preprocessing_detector/api/routes/batch.py-145-            "completed_at": utc_now(),
--
src/image_preprocessing_detector/api/routes/batch.py-151-        "batch_job_completed",
src/image_preprocessing_detector/api/routes/batch.py-152-        job_id=job_id,
src/image_preprocessing_detector/api/routes/batch.py:153:        num_results=len(results),
src/image_preprocessing_detector/api/routes/batch.py-154-        num_errors=len(errors),
src/image_preprocessing_detector/api/routes/batch.py-155-        elapsed_ms=elapsed_ms,
--
src/image_preprocessing_detector/api/routes/batch.py-256-        "updated_at": now,
src/image_preprocessing_detector/api/routes/batch.py-257-        "completed_at": None,
src/image_preprocessing_detector/api/routes/batch.py:258:        "results": [],
src/image_preprocessing_detector/api/routes/batch.py-259-        "errors": [],
src/image_preprocessing_detector/api/routes/batch.py-260-        "start_time": time.perf_counter(),
--
src/image_preprocessing_detector/api/routes/batch.py-326-
src/image_preprocessing_detector/api/routes/batch.py-327-@router.get(
src/image_preprocessing_detector/api/routes/batch.py:328:    "/{job_id}/result",
src/image_preprocessing_detector/api/routes/batch.py-329-    response_model=BatchJobResult,
src/image_preprocessing_detector/api/routes/batch.py:330:    summary="Get batch job results",
src/image_preprocessing_detector/api/routes/batch.py:331:    description="Get the results of a completed batch processing job.",
src/image_preprocessing_detector/api/routes/batch.py-332-    responses={
src/image_preprocessing_detector/api/routes/batch.py:333:        200: {"description": "Job results retrieved"},
src/image_preprocessing_detector/api/routes/batch.py-334-        404: {"description": "Job not found"},
src/image_preprocessing_detector/api/routes/batch.py-335-        425: {"description": "Job not yet completed"},
src/image_preprocessing_detector/api/routes/batch.py-336-    },
src/image_preprocessing_detector/api/routes/batch.py-337-)
src/image_preprocessing_detector/api/routes/batch.py:338:async def get_batch_result(
src/image_preprocessing_detector/api/routes/batch.py-339-    job_id: str,
src/image_preprocessing_detector/api/routes/batch.py-340-    offset: int = 0,
src/image_preprocessing_detector/api/routes/batch.py-341-    limit: int = 100,
src/image_preprocessing_detector/api/routes/batch.py-342-) -> BatchJobResult | JSONResponse:
src/image_preprocessing_detector/api/routes/batch.py:343:    """Get the results of a batch job.
src/image_preprocessing_detector/api/routes/batch.py-344-
src/image_preprocessing_detector/api/routes/batch.py-345-    Args:
src/image_preprocessing_detector/api/routes/batch.py-346-        job_id: The job ID.
src/image_preprocessing_detector/api/routes/batch.py-347-        offset: Pagination offset.
src/image_preprocessing_detector/api/routes/batch.py:348:        limit: Maximum results to return.
src/image_preprocessing_detector/api/routes/batch.py-349-
src/image_preprocessing_detector/api/routes/batch.py-350-    Returns:
src/image_preprocessing_detector/api/routes/batch.py:351:        BatchJobResult with processing results.
src/image_preprocessing_detector/api/routes/batch.py-352-    """
src/image_preprocessing_detector/api/routes/batch.py-353-    job = _get_job(job_id)
--
src/image_preprocessing_detector/api/routes/batch.py-368-        )
src/image_preprocessing_detector/api/routes/batch.py-369-
src/image_preprocessing_detector/api/routes/batch.py:370:    # Paginate results
src/image_preprocessing_detector/api/routes/batch.py:371:    results = job.get("results", [])
src/image_preprocessing_detector/api/routes/batch.py:372:    paginated_results = results[offset : offset + limit]
src/image_preprocessing_detector/api/routes/batch.py-373-
src/image_preprocessing_detector/api/routes/batch.py-374-    return BatchJobResult(
src/image_preprocessing_detector/api/routes/batch.py-375-        job_id=job_id,
src/image_preprocessing_detector/api/routes/batch.py-376-        status=job["status"],
src/image_preprocessing_detector/api/routes/batch.py:377:        results=paginated_results,
src/image_preprocessing_detector/api/routes/batch.py-378-        errors=job.get("errors", []),
src/image_preprocessing_detector/api/routes/batch.py-379-        total_processing_time_ms=job.get("total_processing_time_ms", 0),
--
src/image_preprocessing_detector/api/routes/batch.py-384-    "/{job_id}",
src/image_preprocessing_detector/api/routes/batch.py-385-    summary="Delete batch job",
src/image_preprocessing_detector/api/routes/batch.py:386:    description="Delete a batch job and its results.",
src/image_preprocessing_detector/api/routes/batch.py-387-    responses={
src/image_preprocessing_detector/api/routes/batch.py-388-        200: {"description": "Job deleted"},

=== Listing API files structure ===
src/image_preprocessing_detector/api/__init__.py
src/image_preprocessing_detector/api/app.py
src/image_preprocessing_detector/api/config.py
src/image_preprocessing_detector/api/middleware.py
src/image_preprocessing_detector/api/models.py
src/image_preprocessing_detector/api/routes/__init__.py
src/image_preprocessing_detector/api/routes/batch.py
src/image_preprocessing_detector/api/routes/health.py
src/image_preprocessing_detector/api/routes/process.py
```

</shell_result>

---

</details>

**Update docstring to reflect actual batch job endpoint paths.**

The documented endpoints `/status` and `/result` are actually nested under the batch job routes as `/batch/{job_id}/status` and `/batch/{job_id}/result` (implemented at lines 289–298 and 327–337 in `src/image_preprocessing_detector/api/routes/batch.py`). The module docstring should clarify these are batch job tracking endpoints with their correct path structure.

<details>
<summary>🧰 Tools</summary>

<details>
<summary>🪛 GitHub Actions: Documentation</summary>

[error] 1-1: Command 'uv run ruff check src/' failed with 40 linting errors found in the codebase. Review the local log for detailed rule violations (e.g., mutable ContextVar defaults, unused arguments, missing docstrings, and other S/SI/R tips reported by Ruff).

</details>

</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In src/image_preprocessing_detector/api/__init__.py lines 1-11, the module
docstring incorrectly lists /status and /result as top-level endpoints; update
the docstring to state that job status and result tracking are provided for
batch jobs under /batch/{job_id}/status and /batch/{job_id}/result (and keep
/process and /batch as documented), clearly indicating these two endpoints are
nested under the batch job route and include the {job_id} path parameter in the
description.
```

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 35. PR #53 - k8s/deployment.yaml

- **Status**: [~]
- **Severity**: medium
- **PR**: [#53 - feat: Phase 5 testing, documentation, and infrastructure improvements](https://github.com/williaby/image-preprocessing-detector/pull/53)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-26
- **File**: `k8s/deployment.yaml`
- **Line**: 49

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟠 Major_

**Prefer secrets as files over environment variables for sensitive data.**

Sourcing secrets via environment variables exposes them to process inspection (e.g., `ps` command, container logs). For production, mount secrets as files.

Apply this diff:

```diff
         envFrom:
           - configMapRef:
               name: imgprep-config
-          - secretRef:
-              name: imgprep-secret
         env:
           - name: SOME_CONFIG
             valueFrom:
               configMapKeyRef:
                 name: imgprep-config
                 key: SOME_KEY
+        volumeMounts:
+          - name: secrets-volume
+            mountPath: /var/run/secrets/imgprep
+            readOnly: true
       volumes:
+        - name: secrets-volume
+          secret:
+            secretName: imgprep-secret
```

Adjust the mount path and environment variable reading logic in your application accordingly.

> Committable suggestion skipped: line range outside the PR's diff.

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In k8s/deployment.yaml around lines 45-49, the secret is injected via env vars;
change this to mount the secret as files and remove the secretRef envFrom. Add a
volume under spec.template.spec.volumes that references secretName:
imgprep-secret, add a corresponding volumeMount in the container with a secure
mountPath (e.g., /etc/imgprep/secret) and appropriate read-only mode; remove the
secret from envFrom and keep the configMap envFrom if needed. Then update the
application to read sensitive values from files at the chosen mountPath (e.g.,
read /etc/imgprep/secret/KEY_NAME), handle missing file errors, and ensure file
permissions are set to read-only for the container; do not leave secret data in
environment variables or logs.
```

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 36. PR #53 - src/image_preprocessing_detector/api/config.py

- **Status**: [x]
- **Severity**: medium
- **PR**: [#53 - feat: Phase 5 testing, documentation, and infrastructure improvements](https://github.com/williaby/image-preprocessing-detector/pull/53)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-26
- **File**: `src/image_preprocessing_detector/api/config.py`
- **Line**: 53

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟠 Major_

**Security: CORS credentials with wildcard origin is ineffective.**

When `cors_allow_credentials` is `True`, browsers ignore `Access-Control-Allow-Origin: *` and the request fails. If credentials are needed, you must specify explicit origins. Consider changing the default to `False` or using explicit origins.

```diff
     cors_origins: list[str] = Field(
-        default=["*"],
+        default=[],
         description="Allowed CORS origins",
     )
     cors_allow_credentials: bool = Field(
-        default=True,
+        default=False,
         description="Allow credentials in CORS requests",
     )
```

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In src/image_preprocessing_detector/api/config.py around lines 46 to 53, the
config currently enables cors_allow_credentials=True while cors_origins defaults
to ["*"], which is ineffective and insecure because browsers reject wildcard
origins when credentials are allowed; change the default to
cors_allow_credentials=False or require explicit origins by setting cors_origins
to an empty list or a list of allowed origins, and update validation/docs to
enforce that if cors_allow_credentials is True then cors_origins must not
contain "*" (raise a validation error) so callers must provide explicit origins.
```

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 37. PR #53 - .gitguardian.yaml

- **Status**: [x]
- **Severity**: medium
- **PR**: [#53 - feat: Phase 5 testing, documentation, and infrastructure improvements](https://github.com/williaby/image-preprocessing-detector/pull/53)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-26
- **File**: `.gitguardian.yaml`
- **Line**: 41

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟠 Major_

**Tighten match patterns to avoid suppressing legitimate secrets.**

The patterns `"test-key-*"` and `"valid-*-key*"` are overly broad and could inadvertently suppress warnings for real credentials that happen to follow these naming conventions. Additionally, GitGuardian's `match` field uses string matching (not regex by default), so these patterns will match any substring occurrence.

Consider one or more of the following mitigations:

1. **Use regex patterns explicitly** (if GitGuardian supports them): Constrain patterns to test-specific contexts, e.g., `test-key-[a-z0-9]{16}` or similar.
2. **Use inline-ignore comments** in code instead of global patterns: Add `# ggshield: ignore` to specific lines in test files to suppress known false positives locally.
3. **Restrict patterns to known test-only prefixes**: If possible, use a more specific prefix like `TEST_API_KEY_` or `FIXTURE_` instead of generic `test-key-*`.
4. **Document the rationale**: Add a comment explaining why each pattern is necessary and what false positives it prevents.

For example, a more secure approach:

```yaml
  ignored_matches:
    # Strictly prefixed test fixtures, only in test files
    - name: "test-api-keys"
      match: "test-api-key-fixture-"
    # AWS documentation example (verified safe)
    - name: "aws-example-key"
      match: "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
```

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
.gitguardian.yaml lines 29-41: the ignored_matches entries "test-key-*" and
"valid-*-key*" are too broad and will suppress legitimate secrets; tighten them
by replacing wildcard substrings with either explicit regex patterns (if
GitGuardian supports regex) using anchors and constrained character classes
(e.g. test-key-[a-z0-9]{N}$) or by switching to strict, test-only prefixes (e.g.
TEST_API_KEY_ or FIXTURE_) and/or moving ignores to inline comments in specific
test files (# ggshield: ignore) so only known test fixtures are suppressed; also
remove or narrow the global "valid-*-key*" rule, and add a short comment next to
each ignored_match explaining why it is safe and what it targets.
```

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 38. PR #52 - .github/workflows/qlty.yml

- **Status**: [x]
- **Severity**: medium
- **PR**: [#52 - refactor: fix qlty issues, add linter configs, reduce complexity](https://github.com/williaby/image-preprocessing-detector/pull/52)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-25
- **File**: `.github/workflows/qlty.yml`
- **Line**: 40

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟠 Major_

<details>
<summary>🧩 Analysis chain</summary>

Script executed:

```shell
cat -n .github/workflows/qlty.yml
```

Repository: williaby/image-preprocessing-detector

---

<shell_result>
Repository: williaby/image-preprocessing-detector
Exit code: 0

stdout:

```
     1 # Qlty Coverage Upload Workflow
     2 # Dedicated workflow for uploading test coverage reports to Qlty
     3
     4 name: Qlty
     5
     6 on:
     7   workflow_run:
     8     workflows: ["CI"]
     9     types:
    10       - completed
    11
    12 permissions: read-all
    13
    14 jobs:
    15   upload-coverage:
    16     name: Upload Coverage to Qlty
    17     runs-on: ubuntu-latest
    18     if: ${{ github.event.workflow_run.conclusion == 'success' }}
    19     permissions:
    20       contents: read        # Required for downloading artifacts
    21       actions: read         # Required for workflow_run artifact download
    22
    23     steps:
    24       - name: Harden the runner (Audit outbound calls)
    25         uses: step-security/harden-runner@91182cccc01eb5e619899d80e4e971d6181294a7 # v2.10.1
    26         with:
    27           egress-policy: audit
    28
    29       - name: Download coverage artifacts
    30         uses: actions/download-artifact@fa0a91b85d4f404e444e00e005971372dc801d16 # v4.1.8
    31         with:
    32           name: test-results-3.12
    33           github-token: ${{ secrets.GITHUB_TOKEN }}
    34           run-id: ${{ github.event.workflow_run.id }}
    35
    36       - name: Upload coverage to Qlty
    37         uses: qltysh/qlty-action/coverage@v2
    38         with:
    39           token: ${{ secrets.QLTY_COVERAGE_TOKEN }}
    40           files: reports/lcov.info
    41
    42       - name: Coverage upload status
    43         if: always()
    44         env:
    45           GH_REPOSITORY: ${{ github.repository }}
    46         run: |
    47           if [ -f reports/lcov.info ]; then
    48             echo "Coverage report uploaded successfully"
    49             echo "View coverage at: https://qlty.sh"
    50           else
    51             echo "Coverage report not found at reports/lcov.info"
    52             echo "This may indicate the test suite did not run or failed"
    53           fi
```

</shell_result>

---

qltysh qlty-action coverage v2 commit SHA github

---

<web_search_result>
The tag "v2" (qltysh/qlty-action) points to commit a19242102d17e497f437d7466aa01b528537e899. [1][2]

Sources:
[1] qltysh/qlty-action — Tags page (v2).
[2] Commit a19242102d17e497f437d7466aa01b528537e899.
</web_search_result>

---

</details>

**Pin the `qltysh/qlty-action/coverage` action to a specific SHA.**

Other actions in this workflow are SHA-pinned for security (`step-security/harden-runner@91182cccc01eb5e619899d80e4e971d6181294a7`, `actions/download-artifact@fa0a91b85d4f404e444e00e005971372dc801d16`), but `qltysh/qlty-action/coverage@v2` uses only a version tag. Pin to commit `a19242102d17e497f437d7466aa01b528537e899`:

```yaml
uses: qltysh/qlty-action/coverage@a19242102d17e497f437d7466aa01b528537e899
```

This ensures supply-chain security consistency across all actions.

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
.github/workflows/qlty.yml lines 36-40: the workflow uses the
qltysh/qlty-action/coverage action by tag (@v2) which is not SHA-pinned; update
the uses line to reference the specific commit SHA provided
(a19242102d17e497f437d7466aa01b528537e899) so the action is pinned to that exact
commit, matching the security posture of the other steps and preventing
supply-chain drift.
```

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 39. PR #51 - .claude/agents/code-reviewer.md

- **Status**: [x]
- **Severity**: medium
- **PR**: [#51 - chore: align project with cookiecutter-python-template standards](https://github.com/williaby/image-preprocessing-detector/pull/51)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-25
- **File**: `.claude/agents/code-reviewer.md`
- **Line**: 65

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟡 Minor_

**Add blank lines before headings and specify code block language.**

Multiple markdown formatting issues per MD022 (headings) and MD040 (code block language):

- Headings at lines 11, 17, 23, 29, 37, 43, 49, 55 need blank lines above them
- Line 63 code block needs a language identifier

Apply this diff to fix heading spacing and code block language:

```diff
 ## Capabilities

 ### Code Analysis
+
 - Identify code smells and anti-patterns
 - Check adherence to Python best practices
 - Evaluate code complexity and maintainability
 - Detect potential bugs and edge cases

 ### Standards Compliance
+
 - Verify PEP 8 and project style guide compliance
 - Check type annotation completeness
 - Validate docstring coverage and quality
 - Ensure consistent naming conventions

 ### Security Review
+
 - Identify potential security vulnerabilities
 - Check for hardcoded secrets or credentials
 - Validate input handling and sanitization
 - Review authentication and authorization logic

 ### Performance Review
+
 - Identify potential performance bottlenecks
 - Check for unnecessary database queries (N+1)
 - Review memory usage patterns
 - Evaluate algorithm complexity

 ## Review Checklist

 ### Code Quality
+
 - [ ] Code is readable and self-documenting
 - [ ] Functions are single-purpose (SRP)
 - [ ] No unnecessary complexity
 - [ ] Error handling is appropriate

 ### Testing
+
 - [ ] Tests cover new functionality
 - [ ] Edge cases are tested
 - [ ] Test names are descriptive
 - [ ] Mocks are used appropriately

 ### Documentation
+
 - [ ] Public APIs are documented
 - [ ] Complex logic has comments
 - [ ] README updated if needed
 - [ ] CHANGELOG entry added

 ### Security
+
 - [ ] No hardcoded secrets
 - [ ] Input validation present
 - [ ] SQL injection prevented
 - [ ] XSS prevention in place

 ## Invocation

-```
+```text
 /review or via Task tool with subagent_type='code-reviewer'
 ```

```

<details>
<summary>🧰 Tools</summary>

<details>
<summary>🪛 markdownlint-cli2 (0.18.1)</summary>

11-11: Headings should be surrounded by blank lines
Expected: 1; Actual: 0; Below

(MD022, blanks-around-headings)

---

17-17: Headings should be surrounded by blank lines
Expected: 1; Actual: 0; Below

(MD022, blanks-around-headings)

---

23-23: Headings should be surrounded by blank lines
Expected: 1; Actual: 0; Below

(MD022, blanks-around-headings)

---

29-29: Headings should be surrounded by blank lines
Expected: 1; Actual: 0; Below

(MD022, blanks-around-headings)

---

37-37: Headings should be surrounded by blank lines
Expected: 1; Actual: 0; Below

(MD022, blanks-around-headings)

---

43-43: Headings should be surrounded by blank lines
Expected: 1; Actual: 0; Below

(MD022, blanks-around-headings)

---

49-49: Headings should be surrounded by blank lines
Expected: 1; Actual: 0; Below

(MD022, blanks-around-headings)

---

55-55: Headings should be surrounded by blank lines
Expected: 1; Actual: 0; Below

(MD022, blanks-around-headings)

---

63-63: Fenced code blocks should have a language specified

(MD040, fenced-code-language)

</details>

</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

````

In .claude/agents/code-reviewer.md around lines 9–65, headings at lines 11, 17,
23, 29, 37, 43, 49, and 55 need a blank line inserted immediately above each
heading to satisfy MD022, and the fenced code block around line 63 must include
a language identifier (use "text") to satisfy MD040; update the file to add
those blank lines and change the opening fence to ```text (ensuring the closing
fence remains```), keeping other content and indentation unchanged.

````

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 40. PR #51 - .claude/agents/project-plan-synthesizer.md

- **Status**: [x]
- **Severity**: medium
- **PR**: [#51 - chore: align project with cookiecutter-python-template standards](https://github.com/williaby/image-preprocessing-detector/pull/51)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-25
- **File**: `.claude/agents/project-plan-synthesizer.md`
- **Line**: 94

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟡 Minor_

**Specify language for code block at line 94.**

Code block is missing language specification. Based on context (Context7 lookups), add a language or marker:



```diff
  Use Context7 to lookup current best practices for technologies in the tech stack:

- ```
+ ```text
  # For each major technology in tech-spec.md
  mcp__context7__resolve-library-id(libraryName="fastapi")  # or relevant framework
  mcp__context7__get-library-docs(context7CompatibleLibraryID="/tiangolo/fastapi", topic="project structure")
  ```
```

<details>
<summary>🧰 Tools</summary>

<details>
<summary>🪛 markdownlint-cli2 (0.18.1)</summary>

94-94: Fenced code blocks should have a language specified

(MD040, fenced-code-language)

</details>

</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

````

In .claude/agents/project-plan-synthesizer.md around line 94, the fenced code
block labeled under "Security requirements" lacks a language specifier; update
the opening fence to include a language marker (e.g., ```text) so the block is
annotated, and ensure the closing``` remains present; since the lines show
Context7 lookup commands, use "text" (or another appropriate marker) to avoid
incorrect syntax highlighting.

````

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 41. PR #51 - .claude/skills/testing/workflows/security.md

- **Status**: [x]
- **Severity**: medium
- **PR**: [#51 - chore: align project with cookiecutter-python-template standards](https://github.com/williaby/image-preprocessing-detector/pull/51)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-25
- **File**: `.claude/skills/testing/workflows/security.md`
- **Line**: 198

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟡 Minor_

**Fix markdown formatting: add blank lines before code blocks.**

Multiple code blocks lack required blank lines before them per markdownlint MD031. This affects lines 38, 86, 106, 131, 170.


Example pattern to apply throughout:

```diff
 ```python
+
 @pytest.mark.security
 def test_...
```

Specifically:
- Line 38: Add blank line before `@pytest.mark.security`
- Line 86: Add blank line before `@pytest.mark.security`
- Line 106: Add blank line before `@pytest.mark.security`
- Line 131: Add blank line before `@pytest.mark.security`
- Line 170: Add blank line before `@pytest.mark.security`

<details>
<summary>🧰 Tools</summary>

<details>
<summary>🪛 markdownlint-cli2 (0.18.1)</summary>

38-38: Fenced code blocks should be surrounded by blank lines

(MD031, blanks-around-fences)

---

86-86: Fenced code blocks should be surrounded by blank lines

(MD031, blanks-around-fences)

---

106-106: Fenced code blocks should be surrounded by blank lines

(MD031, blanks-around-fences)

---

131-131: Fenced code blocks should be surrounded by blank lines

(MD031, blanks-around-fences)

---

170-170: Fenced code blocks should be surrounded by blank lines

(MD031, blanks-around-fences)

</details>

</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
.claude/skills/testing/workflows/security.md around lines 38-198: several fenced
code blocks violate markdownlint MD031 because there is no blank line
immediately before the opening triple-backtick or the language-tagged fence; add
a single blank line above each affected code block (specifically ensure a blank
line exists before the blocks starting at the areas reported near lines 38, 86,
106, 131, and 170) so that every code fence is preceded by an empty line while
preserving existing indentation and content.
```

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 42. PR #51 - .github/workflows/sonarcloud.yml

- **Status**: [x]
- **Severity**: medium
- **PR**: [#51 - chore: align project with cookiecutter-python-template standards](https://github.com/williaby/image-preprocessing-detector/pull/51)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-25
- **File**: `.github/workflows/sonarcloud.yml`
- **Line**: 57

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟡 Minor_

**Improve shell quoting in SONAR_TOKEN check.**

The conditional test and echo statements need proper quoting to avoid word splitting and globbing issues (SC2086). The current approach works but doesn't follow shell best practices.

```diff
         if [ -n "${{ secrets.SONAR_TOKEN }}" ]; then
-            echo "has-token=true" >> $GITHUB_OUTPUT
-            echo "::notice::SONAR_TOKEN is configured. SonarCloud analysis will run."
+            echo "has-token=true" >> "$GITHUB_OUTPUT"
+            echo "::notice::SONAR_TOKEN is configured. SonarCloud analysis will run."
           else
-            echo "has-token=false" >> $GITHUB_OUTPUT
-            echo "::warning::SONAR_TOKEN is not configured. Skipping SonarCloud analysis."
-            echo "To enable SonarCloud:"
-            echo "1. Create a project at https://sonarcloud.io"
-            echo "2. Generate a token at https://sonarcloud.io/account/security"
-            echo "3. Add SONAR_TOKEN as a repository secret"
+            echo "has-token=false" >> "$GITHUB_OUTPUT"
+            {
+              echo "::warning::SONAR_TOKEN is not configured. Skipping SonarCloud analysis."
+              echo "To enable SonarCloud:"
+              echo "1. Create a project at https://sonarcloud.io"
+              echo "2. Generate a token at https://sonarcloud.io/account/security"
+              echo "3. Add SONAR_TOKEN as a repository secret"
+            } >> $GITHUB_OUTPUT
           fi
```


> Committable suggestion skipped: line range outside the PR's diff.

<details>
<summary>🧰 Tools</summary>

<details>
<summary>🪛 actionlint (1.7.8)</summary>

46-46: shellcheck reported issue in this script: SC2086:info:2:28: Double quote to prevent globbing and word splitting

(shellcheck)

---

46-46: shellcheck reported issue in this script: SC2086:info:5:29: Double quote to prevent globbing and word splitting

(shellcheck)

</details>
<details>
<summary>🪛 Checkov (3.2.334)</summary>

[low] 48-49: Base64 High Entropy String

(CKV_SECRET_6)

</details>

</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In .github/workflows/sonarcloud.yml around lines 46 to 57, the shell uses
unquoted variable expansions and redirection targets which can lead to
word-splitting and globbing; update the script to quote the token check and any
variable expansions (e.g. the SONAR_TOKEN test) and quote the output file
variable used with >> (or use printf with a quoted target) so all expansions are
double-quoted, and keep echo/printf arguments quoted to avoid SC2086 issues.
```

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 43. PR #51 - .github/workflows/sonarcloud.yml

- **Status**: [x]
- **Severity**: medium
- **PR**: [#51 - chore: align project with cookiecutter-python-template standards](https://github.com/williaby/image-preprocessing-detector/pull/51)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-25
- **File**: `.github/workflows/sonarcloud.yml`
- **Line**: 80

<details>
<summary>Comment</summary>

_⚠️ Potential issue_ | _🟡 Minor_

<details>
<summary>🧩 Analysis chain</summary>

**Consider a safer alternative to `curl | sh` for UV installation.**

While this pattern is common for tool installation, piping untrusted shell scripts directly to `sh` is a security anti-pattern. Consider verifying checksums or using a pinned version URL if available.

---

🌐 Web query:

```web
What is the recommended secure installation method for the UV package manager?
```

💡 Result:

Which "UV" do you mean? (link or repo/name — e.g., the Rust-based Python package manager "uv", the libuv library, or something else?)

---



</details>

I need to clarify the search to specify the Astral uv package manager (the Rust-based Python package manager). Let me search with more specific terms:

**Consider pinning the UV version or using GitHub releases for verification.**

While the official Astral documentation recommends `curl -LsSf https://astral.sh/uv/install.sh | sh` for installation, you can improve security posture by:

1. **Pin a specific version**: Include the version in the URL (e.g., `https://astral.sh/uv/0.9.12/install.sh`)
2. **Use GitHub releases with checksums**: Each release page includes binaries and instructions for using the standalone installer via github.com, which provides checksums for verification
3. **Alternative methods**: uv is published to PyPI and can be installed with pipx

The current implementation installs the latest version without pinning, which may cause non-deterministic builds across workflow runs.

<details>
<summary>🧰 Tools</summary>

<details>
<summary>🪛 actionlint (1.7.8)</summary>

78-78: shellcheck reported issue in this script: SC2086:info:2:28: Double quote to prevent globbing and word splitting

(shellcheck)

</details>

</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
.github/workflows/sonarcloud.yml lines 78-80: the workflow installs Astral's uv
via an unpinned curl installer which yields non-deterministic and unverifiable
builds; modify the step to pin a specific uv version (use the versioned
installer URL), or download a release artifact from the project's GitHub
releases and verify it with the provided checksum, or alternatively install via
pipx/pip with a pinned package version; ensure the chosen approach includes
explicit versioning and integrity verification (checksum/signature) and update
the workflow step accordingly.
```

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 44. PR #109 - osv-scanner.toml

- **Status**: [x]
- **Severity**: unclassified
- **PR**: [#109 - feat: add DeQA-Doc labeling infrastructure with 3-dimension quality assessment](https://github.com/williaby/image-preprocessing-detector/pull/109)
- **Reviewer**: @copilot-pull-request-reviewer
- **Date**: 2026-01-17
- **File**: `osv-scanner.toml`
- **Line**: 34

<details>
<summary>Comment</summary>

The osv-scanner.toml file removes documented exclusions for PYSEC-2022-42969 and CVE-2025-53000 but the new version only documents them without actual IgnoredVulns entries. This inconsistency might cause these vulnerabilities to be reported again if they weren't auto-filtered. Consider keeping the explicit ignores or adding a note about when they were removed.

</details>

### 45. PR #70 - src/image_preprocessing_detector/workers/tasks.py

- **Status**: [x]
- **Severity**: unclassified
- **PR**: [#70 - feat(phase4): Phase 4 validation and completion - 98% complete](https://github.com/williaby/image-preprocessing-detector/pull/70)
- **Reviewer**: @copilot-pull-request-reviewer
- **Date**: 2025-12-06
- **File**: `src/image_preprocessing_detector/workers/tasks.py`
- **Line**: 154

<details>
<summary>Comment</summary>

Using `doc_id or request_id or "unknown"` as a fallback creates a security risk. If both `doc_id` and `request_id` are None (or empty strings), all such requests will share the same budget tracking identifier "unknown". This could allow malicious actors to exhaust the budget by sending many requests without IDs. Consider either:

1. Making `doc_id` required and raising an error if not provided
2. Generating a unique ID (e.g., UUID) instead of using "unknown"

```python
doc_id = doc_id or request_id
if not doc_id:
    raise ValueError("Either doc_id or request_id must be provided for budget tracking")
```

</details>

### 46. PR #69 - modal/teacher_inference.py

- **Status**: [~]
- **Severity**: unclassified
- **PR**: [#69 - feat(phase4): Phase 4 validation fixes and test improvements](https://github.com/williaby/image-preprocessing-detector/pull/69)
- **Reviewer**: @copilot-pull-request-reviewer
- **Date**: 2025-12-06
- **File**: `modal/teacher_inference.py`
- **Line**: 90

<details>
<summary>Comment</summary>

The Modal image configuration copies a GCS service account JSON file directly into the container image. This embeds credentials in the container image which could be a security risk if the image is shared or leaked. Consider using Modal secrets instead:

```python
# Instead of .add_local_file(), use Modal secrets:
@app.cls(
    image=image,
    secrets=[modal.Secret.from_name("gcs-credentials")],
    ...
)
```

Then access credentials via environment variables set by Modal secrets rather than embedding them in the image.

</details>

### 47. PR #62 - .github/workflows/deploy.yml

- **Status**: [~]
- **Severity**: unclassified
- **PR**: [#62 - feat(phase4): Device-Priority Execution & Modal GPU Integration](https://github.com/williaby/image-preprocessing-detector/pull/62)
- **Reviewer**: @copilot-pull-request-reviewer
- **Date**: 2025-12-04
- **File**: `.github/workflows/deploy.yml`
- **Line**: 119

<details>
<summary>Comment</summary>

The kubeconfig is decoded from base64 and written to disk with chmod 600, but there's no cleanup of this sensitive file after the job completes. Consider using a cleanup step in a `post:` action or ensure the file is deleted in an `always()` step to avoid leaving credentials on the runner.

</details>

### 48. PR #52 - tests/security/test_codeql_validation.py

- **Status**: [x]
- **Severity**: unclassified
- **PR**: [#52 - refactor: fix qlty issues, add linter configs, reduce complexity](https://github.com/williaby/image-preprocessing-detector/pull/52)
- **Reviewer**: @copilot-pull-request-reviewer
- **Date**: 2025-11-25
- **File**: `tests/security/test_codeql_validation.py`
- **Line**: 57

<details>
<summary>Comment</summary>

Variable _aws_secret_key is not used.

</details>

### 49. PR #52 - tests/security/test_codeql_validation.py

- **Status**: [x]
- **Severity**: unclassified
- **PR**: [#52 - refactor: fix qlty issues, add linter configs, reduce complexity](https://github.com/williaby/image-preprocessing-detector/pull/52)
- **Reviewer**: @copilot-pull-request-reviewer
- **Date**: 2025-11-25
- **File**: `tests/security/test_codeql_validation.py`
- **Line**: 58

<details>
<summary>Comment</summary>

Variable _jwt_secret is not used.

</details>

### 50. PR #49 - scripts/colab_utils.py

- **Status**: [x]
- **Severity**: unclassified
- **PR**: [#49 - feat: Phase-4 implementation](https://github.com/williaby/image-preprocessing-detector/pull/49)
- **Reviewer**: @copilot-pull-request-reviewer
- **Date**: 2025-11-25
- **File**: `scripts/colab_utils.py`
- **Line**: 73

<details>
<summary>Comment</summary>

Good practice: using `shutil.which` to resolve the nvidia-smi path before executing it. However, the security comment references B603 but the actual risk here is command injection if the path resolution fails silently. Consider adding explicit validation that `nvidia_smi_path` is not None before use.

</details>

### 51. PR #46 - modal/train_phase3_doclayout_yolo.py

- **Status**: [x]
- **Severity**: unclassified
- **PR**: [#46 - feat: enhance training pipeline and coverage configuration](https://github.com/williaby/image-preprocessing-detector/pull/46)
- **Reviewer**: @copilot-pull-request-reviewer
- **Date**: 2025-11-24
- **File**: `modal/train_phase3_doclayout_yolo.py`
- **Line**: 62

<details>
<summary>Comment</summary>

The `download_gcs_directory` function is vulnerable to path traversal attacks. When constructing `relative_path` using `Path(blob.name).relative_to(prefix)`, if a malicious blob name contains path traversal sequences (e.g., `../../../etc/passwd`), it could write files outside the intended `destination` directory.

Add validation to ensure the resolved `target_path` stays within the `destination` directory:

```python
def download_gcs_directory(bucket: Any, prefix: str, destination: Path) -> None:
    """Download all objects under a GCS prefix into a destination directory."""
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    for blob in bucket.list_blobs(prefix=prefix):
        if blob.name.endswith("/"):
            continue
        if blob.name == prefix:
            continue
        relative_path = Path(blob.name).relative_to(prefix)
        target_path = (destination / relative_path).resolve()

        # Security: Validate path is within destination
        if not str(target_path).startswith(str(destination)):
            raise ValueError(f"Path traversal detected: {blob.name}")

        target_path.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(target_path))
```

</details>

### 52. PR #46 - modal/train_phase2_iqa.py

- **Status**: [~]
- **Severity**: unclassified
- **PR**: [#46 - feat: enhance training pipeline and coverage configuration](https://github.com/williaby/image-preprocessing-detector/pull/46)
- **Reviewer**: @copilot-pull-request-reviewer
- **Date**: 2025-11-24
- **File**: `modal/train_phase2_iqa.py`
- **Line**: 407

<details>
<summary>Comment</summary>

Checkpoint saving should use `weights_only=True` parameter for consistency with the secure loading practices introduced in `checkpoint_utils.py`. While saving doesn't have the same security risk as loading, this ensures consistency and forward compatibility. Note that `weights_only` is primarily for `torch.load`, but documenting the intent here would be valuable.

</details>

### 53. PR #45 - scripts/organize_dual_storage.py

- **Status**: [x]
- **Severity**: unclassified
- **PR**: [#45 - test: complete Phase 2/3 test coverage and datetime_compat tests](https://github.com/williaby/image-preprocessing-detector/pull/45)
- **Reviewer**: @copilot-pull-request-reviewer
- **Date**: 2025-11-22
- **File**: `scripts/organize_dual_storage.py`
- **Line**: 170

<details>
<summary>Comment</summary>

While the nosec comment acknowledges the security consideration, the command construction using shlex.quote() at lines 160-161 doesn't actually protect against command injection since the quoted values are still passed to subprocess.run() as separate list elements. The shlex.quote() is unnecessary here and creates false security confidence. Use the list directly without quoting.

</details>

### 54. PR #45 - scripts/organize_dual_storage.py

- **Status**: [x]
- **Severity**: unclassified
- **PR**: [#45 - test: complete Phase 2/3 test coverage and datetime_compat tests](https://github.com/williaby/image-preprocessing-detector/pull/45)
- **Reviewer**: @copilot-pull-request-reviewer
- **Date**: 2025-11-22
- **File**: `scripts/organize_dual_storage.py`
- **Line**: 264

<details>
<summary>Comment</summary>

Same security issue as Comment 3 - unnecessary shlex.quote() usage (lines 250-251) creates false security confidence when using subprocess.run() with a list.

</details>

### 55. PR #1 - pyproject.toml

- **Status**: [x]
- **Severity**: unclassified
- **PR**: [#1 - Security improvements and ClusterFuzzLite fuzzing integration](https://github.com/williaby/image-preprocessing-detector/pull/1)
- **Reviewer**: @copilot-pull-request-reviewer
- **Date**: 2025-11-08
- **File**: `pyproject.toml`
- **Line**: 139

<details>
<summary>Comment</summary>

Black version is being updated to `>=24.3.0` in the `[tool.poetry.group.dev.dependencies]` section to address CVE-2024-21503, but the `[project.optional-dependencies]` dev section (around line 71) still specifies `black>=23.7.0`.

Both locations should be updated consistently for PEP 621 compliance and to ensure the security fix is applied regardless of which dependency specification is used.

</details>

### 56. PR #105 - modal/train_hyperiqa_plus_plus.py

- **Status**: [~]
- **Severity**: low
- **PR**: [#105 - feat: Add HyperIQA++ Document IQA Model](https://github.com/williaby/image-preprocessing-detector/pull/105)
- **Reviewer**: @coderabbitai
- **Date**: 2026-01-16
- **File**: `modal/train_hyperiqa_plus_plus.py`
- **Line**: 212

<details>
<summary>Comment</summary>

_🧹 Nitpick_ | _🔵 Trivial_

**Consider cleaning up the credentials temp file after GCS operations complete.**

The credentials file written to disk at `credentials_path` is never deleted. While the container is ephemeral, explicitly cleaning up sensitive files is a defense-in-depth practice.


<details>
<summary>♻️ Suggested improvement</summary>

Store the path and clean up at the end of the function:

```diff
     os.chmod(credentials_path, 0o600)
     os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
+    # Store for cleanup
+    _credentials_temp_path = credentials_path
 elif "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
```

Then at the end of the function (before `return dataset_path`):

```python
    # Clean up credentials temp file
    if gcp_sa_key and Path(credentials_path).exists():
        Path(credentials_path).unlink()
```
</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In `@modal/train_hyperiqa_plus_plus.py` around lines 205 - 212, The temp GCP
credentials file created in the tempfile.NamedTemporaryFile block
(credentials_path) is never removed; update the function (the block that writes
gcp_sa_key_json and sets os.environ["GOOGLE_APPLICATION_CREDENTIALS"]) to record
credentials_path and delete that file after GCS operations complete (before
returning dataset_path) when gcp_sa_key is present and the file exists; also
ensure deletion does not run before any code that needs
GOOGLE_APPLICATION_CREDENTIALS and handle missing file gracefully.
```

</details>

<!-- fingerprinting:phantom:medusa:ocelot -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 57. PR #79 - docs/planning/PHASE7_SPRINT_IMPLEMENTATION_PLAN.md

- **Status**: [~]
- **Severity**: low
- **PR**: [#79 - feat(phase7): implement continuous training infrastructure and deprecate Phase 2 assets](https://github.com/williaby/image-preprocessing-detector/pull/79)
- **Reviewer**: @coderabbitai
- **Date**: 2026-01-10
- **File**: `docs/planning/PHASE7_SPRINT_IMPLEMENTATION_PLAN.md`
- **Line**: 15

<details>
<summary>Comment</summary>

_🧹 Nitpick_ | _🔵 Trivial_

**Author attribution includes both "Claude Code" and "Byron Williams".**

Line 14-15 attributes authorship to both "Claude Code" (AI) and "Byron Williams" (human). This is an unusual attribution pattern. Recommend clarifying:



Use a more standard format:

```yaml
authors:
  - name: "Byron Williams"
    role: "Original design and planning"
  - name: "Claude Code"  # AI assistant
    role: "Sprint breakdown and task specification"
```

Or, if this is entirely human-written, remove the AI attribution for clarity.

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In @docs/planning/PHASE7_SPRINT_IMPLEMENTATION_PLAN.md around lines 14 - 15, The
authorship lines currently list both "Claude Code" and "Byron Williams" which is
ambiguous; replace those two simple name entries with a clear authors block that
either (A) explicitly distinguishes the human and AI contributions (e.g., an
authors YAML list with entries for "Byron Williams" and "Claude Code" including
a role or note such as 'Original design and planning' and 'AI assistant, sprint
breakdown and task specification'), or (B) if the content is entirely
human-authored, remove the "Claude Code" entry and leave only "Byron Williams";
update the document to use the chosen authors: structure so authors are
unambiguous.
```

</details>

<!-- fingerprinting:phantom:triton:mongoose -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 58. PR #79 - docs/planning/PHASE7_SPRINT_IMPLEMENTATION_PLAN.md

- **Status**: [~]
- **Severity**: low
- **PR**: [#79 - feat(phase7): implement continuous training infrastructure and deprecate Phase 2 assets](https://github.com/williaby/image-preprocessing-detector/pull/79)
- **Reviewer**: @coderabbitai
- **Date**: 2026-01-10
- **File**: `docs/planning/PHASE7_SPRINT_IMPLEMENTATION_PLAN.md`
- **Line**: 1127

<details>
<summary>Comment</summary>

_🧹 Nitpick_ | _🔵 Trivial_

**Quick reference commands are helpful but lack error handling context.**

Appendix A (lines 1102-1129) provides concise commands for each sprint, which is convenient. However, these commands lack context for failure scenarios:

- What if `gsutil` is not installed or authenticated?
- What if a Modal training run is interrupted partway?
- What if GCS upload fails mid-transfer?



Add a "Troubleshooting" section or inline comments addressing:

```bash
# Sprint 2: Dataset Generation
poetry run python scripts/generate_iqa_dataset.py --output-dir data/phase7_mvp/01_augmented
# Note: Requires ~50GB free space. If interrupted, delete 01_augmented/ and retry.

# GSUtil upload (may fail due to auth or network)
gsutil -m cp data/phase7_mvp/archives/*.tar gs://your-bucket/phase7_mvp/
# If resuming after interruption, gsutil -m automatically resumes partial uploads.
```

This helps operators recover from common failure modes.

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In @docs/planning/PHASE7_SPRINT_IMPLEMENTATION_PLAN.md around lines 1102 - 1129,
Add a concise "Troubleshooting" section after the sprint commands that lists
common failure modes and recovery steps referencing the exact scripts/commands
shown (e.g., generate_iqa_dataset.py, create_tar_archives.py, gsutil -m cp,
modal/train_phase7_baseline.py, modal/train_phase7_production.py,
modal/train_phase7_distillation.py, pytest
tests/integration/test_phase7_pipeline.py); for each include one-line checks and
fixes such as verifying disk space before running generate_iqa_dataset.py
(approx. 50GB) and removing the output dir to retry, validating gsutil is
installed and authenticated and using resumable options/flags or retrying failed
gsutil uploads, documenting how to restart or re-run Modal training jobs and
capture logs if interrupted, and adding a note to rerun the pytest integration
test after fixes—keep each item short and directly tied to the command name so
operators can act quickly.
```

</details>

<!-- fingerprinting:phantom:triton:mongoose -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 59. PR #79 - docs/planning/PHASE7_SPRINT_IMPLEMENTATION_PLAN.md

- **Status**: [~]
- **Severity**: low
- **PR**: [#79 - feat(phase7): implement continuous training infrastructure and deprecate Phase 2 assets](https://github.com/williaby/image-preprocessing-detector/pull/79)
- **Reviewer**: @coderabbitai
- **Date**: 2026-01-10
- **File**: `docs/planning/PHASE7_SPRINT_IMPLEMENTATION_PLAN.md`
- **Line**: 861

<details>
<summary>Comment</summary>

_🧹 Nitpick_ | _🔵 Trivial_

**Document prerequisite infrastructure setup (GCS, Modal, credentials).**

Multiple sprints assume external infrastructure is ready:
- Sprint 2 (line 810): `gsutil` command assumes GCS credentials configured
- Sprint 3 & 4: Modal training assumes Modal account, authentication, and GPU quota
- No documentation of setup or troubleshooting

Add a prerequisites section documenting:
1. Required credentials (GCS service account, Modal API key)
2. Verification steps (e.g., `gsutil ls` to test GCS access)
3. Fallback options if services are unavailable





Also applies to: 925-934

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In @docs/planning/PHASE7_SPRINT_IMPLEMENTATION_PLAN.md around lines 850 - 861,
Add a new "Prerequisites" section near the training invocation (around the modal
run / gs:// dataset block and also apply same addition near lines ~925-934) that
lists required credentials (GCS service account key and Modal API key), required
accounts/quota (Modal account and GPU quota), and any required CLI tools
(gsutil, modal CLI); include explicit verification steps such as running gsutil
ls <bucket> to confirm GCS access and modal auth status checks for Modal, and
describe fallback options if unavailable (e.g., using local datasets, running
without Modal/GPU, or alternative cloud buckets) so readers can validate and
recover before running modal/train_phase7_baseline.py with flags like --dataset,
--epochs, --batch-size, --lr.
```

</details>

<!-- fingerprinting:phantom:triton:mongoose -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 60. PR #79 - docs/planning/PHASE7_SPRINT_IMPLEMENTATION_PLAN.md

- **Status**: [~]
- **Severity**: low
- **PR**: [#79 - feat(phase7): implement continuous training infrastructure and deprecate Phase 2 assets](https://github.com/williaby/image-preprocessing-detector/pull/79)
- **Reviewer**: @coderabbitai
- **Date**: 2026-01-10
- **File**: `docs/planning/PHASE7_SPRINT_IMPLEMENTATION_PLAN.md`
- **Line**: 1127

<details>
<summary>Comment</summary>

_🧹 Nitpick_ | _🔵 Trivial_

**Quick reference commands are helpful, but add context about environment setup.**

Appendix A provides command snippets (lines 1101-1127), but lacks:
1. **Prerequisite checks**: No verification that tools (Poetry, Python, gsutil) are installed
2. **Error recovery**: No guidance if a command fails
3. **Logging/debugging**: No mention of how to capture logs or debug issues

Consider adding a "Getting Started" section at the beginning with:
- System requirements checklist
- Environment setup commands
- Common troubleshooting steps

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In @docs/planning/PHASE7_SPRINT_IMPLEMENTATION_PLAN.md around lines 1099 - 1127,
Appendix A's command snippets need a preceding "Getting Started" section that
lists system requirements (required Python version, Poetry, gsutil, gsutil
authentication), provides quick prerequisite checks (commands to verify poetry,
python and gsutil are installed and authenticated), and includes brief
error-recovery and logging guidance (common failure causes and remedies,
retry/auth checks, how to capture command output and modal/pytest logs for
debugging). Add this single section before the Appendix A command block, include
exact verification/check commands and authentication reminders, and append a
short troubleshooting subsection referencing the existing sprint commands (e.g.,
dataset scripts, modal runs, pytest) so users know what to check when those
specific commands fail.
```

</details>

<!-- fingerprinting:phantom:triton:mongoose -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 61. PR #79 - modal/export_student_onnx.py

- **Status**: [~]
- **Severity**: low
- **PR**: [#79 - feat(phase7): implement continuous training infrastructure and deprecate Phase 2 assets](https://github.com/williaby/image-preprocessing-detector/pull/79)
- **Reviewer**: @coderabbitai
- **Date**: 2026-01-10
- **File**: `modal/export_student_onnx.py`
- **Line**: 256

<details>
<summary>Comment</summary>

_🧹 Nitpick_ | _🔵 Trivial_

**Consider using Modal secrets instead of inline environment variable.**

Setting `GOOGLE_APPLICATION_CREDENTIALS` inline works, but Modal's secret handling already configures credentials. The explicit environment variable setting may be redundant.



<details>
<summary>🔧 Simplify credential handling</summary>

If the GCS secret is properly configured in Modal, you may not need the explicit environment variable:

```diff
     print("\n☁️ Uploading to GCS...")
-    import os
-    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/root/.gcp/service-account.json"
+    # Credentials already configured via Modal image .add_local_file()

     client = storage.Client()
```

Test whether this works without the explicit env var. If not, keep the current approach with a comment explaining why it's needed.
</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In @modal/export_student_onnx.py around lines 234 - 235, The code sets
GOOGLE_APPLICATION_CREDENTIALS inline via
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] which is redundant when Modal
secrets already provide GCP credentials; remove the hardcoded env assignment in
modal/export_student_onnx.py and rely on Modal's secret mounting or credential
injection instead (verify GCS access works in the Modal run), and if removal
breaks auth, keep the assignment but add a brief comment near the os.environ set
explaining why the explicit path is required and reference the Modal secret name
used for clarity.
```

</details>

<!-- fingerprinting:phantom:poseidon:puma -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 62. PR #66 - k8s/deployment.yaml

- **Status**: [~]
- **Severity**: low
- **PR**: [#66 - chore: code quality improvements and complexity reduction](https://github.com/williaby/image-preprocessing-detector/pull/66)
- **Reviewer**: @coderabbitai
- **Date**: 2025-12-04
- **File**: `k8s/deployment.yaml`
- **Line**: 41

<details>
<summary>Comment</summary>

_🧹 Nitpick_ | _🔵 Trivial_

**Align deployment overlays with the documented prod/local intent**

The new comments clarifying `imagePullPolicy` and `readOnlyRootFilesystem` behavior are helpful. Just ensure your production overlays/Helm values actually switch to `imagePullPolicy: Always` and `readOnlyRootFilesystem: true`, so the live configuration matches the documented intent and security posture.




Also applies to: 74-79

<!-- fingerprinting:phantom:poseidon:olive -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 63. PR #62 - src/image_preprocessing_detector/orchestration/modal_client.py

- **Status**: [x]
- **Severity**: low
- **PR**: [#62 - feat(phase4): Device-Priority Execution & Modal GPU Integration](https://github.com/williaby/image-preprocessing-detector/pull/62)
- **Reviewer**: @copilot-pull-request-reviewer
- **Date**: 2025-12-04
- **File**: `src/image_preprocessing_detector/orchestration/modal_client.py`
- **Line**: 333

<details>
<summary>Comment</summary>

The `random.uniform()` usage here has a noqa comment for S311/B311, but the jitter is actually used for backoff timing in a circuit breaker pattern. While this is not cryptographic use, using `random.uniform()` for timing-based operations can still be problematic in some security contexts. Consider using `random.SystemRandom().uniform()` for better unpredictability, or document why standard random is acceptable here.
```suggestion
        # Add jitter (±25%) using cryptographically secure random
        jitter = random.SystemRandom().uniform(0.75, 1.25)
```

</details>

### 64. PR #62 - charts/image-preprocessing-detector/templates/deployment.yaml

- **Status**: [~]
- **Severity**: low
- **PR**: [#62 - feat(phase4): Device-Priority Execution & Modal GPU Integration](https://github.com/williaby/image-preprocessing-detector/pull/62)
- **Reviewer**: @coderabbitai
- **Date**: 2025-12-04
- **File**: `charts/image-preprocessing-detector/templates/deployment.yaml`
- **Line**: 39

<details>
<summary>Comment</summary>

_🧹 Nitpick_ | _🔵 Trivial_

**Consider disabling service account token auto-mount if not needed.**

Per static analysis, the service account should either be bound to RBAC roles or have `automountServiceAccountToken: false` set in the pod spec if the application doesn't need Kubernetes API access.



If the application doesn't need to interact with the Kubernetes API, add:

```diff
      serviceAccountName: {{ include "image-preprocessing-detector.serviceAccountName" . }}
+     automountServiceAccountToken: false
      securityContext:
```

<!-- suggestion_start -->

<details>
<summary>📝 Committable suggestion</summary>

> ‼️ **IMPORTANT**
> Carefully review the code before committing. Ensure that it accurately replaces the highlighted code, contains no missing lines, and has no issues with indentation. Thoroughly test & benchmark the code to ensure it meets the requirements.

```suggestion
      serviceAccountName: {{ include "image-preprocessing-detector.serviceAccountName" . }}
      automountServiceAccountToken: false
      securityContext:
        {{- toYaml .Values.podSecurityContext | nindent 8 }}
```

</details>

<!-- suggestion_end -->

<details>
<summary>🧰 Tools</summary>

<details>
<summary>🪛 GitHub Check: SonarCloud Code Analysis</summary>

[warning] 33-33: Bind this Service Account to RBAC or disable "automountServiceAccountToken".

See more on https://sonarcloud.io/project/issues?id=williaby_image-preprocessing-detector&issues=AZrnuZl8ZoKYRQxXeA5y&open=AZrnuZl8ZoKYRQxXeA5y&pullRequest=62

</details>

</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In charts/image-preprocessing-detector/templates/deployment.yaml around lines 33
to 35, the Pod spec currently sets a serviceAccountName but does not disable
automatic mounting of the service account token; if the application does not
need Kubernetes API access, add automountServiceAccountToken: false to the pod
spec (at the same indentation level as serviceAccountName and securityContext)
to prevent the service account token from being mounted, otherwise ensure the
service account is explicitly bound to the minimal RBAC roles required.
```

</details>

<!-- fingerprinting:phantom:medusa:ocelot -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 65. PR #62 - tests/load/locustfile.py

- **Status**: [x]
- **Severity**: low
- **PR**: [#62 - feat(phase4): Device-Priority Execution & Modal GPU Integration](https://github.com/williaby/image-preprocessing-detector/pull/62)
- **Reviewer**: @coderabbitai
- **Date**: 2025-12-04
- **File**: `tests/load/locustfile.py`
- **Line**: 31

<details>
<summary>Comment</summary>

_🧹 Nitpick_ | _🔵 Trivial_

**Document or externalize the test API key.**

The hardcoded `api_key = "test-api-key"` is acceptable for load testing but should be externalized for flexibility:

```diff
+import os
+
 class DocumentProcessorUser(HttpUser):
     # ...
-    api_key = "test-api-key"
+    # API key for authentication (override via LOAD_TEST_API_KEY env var)
+    api_key = os.environ.get("LOAD_TEST_API_KEY", "test-api-key")
```

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In tests/load/locustfile.py around line 31 there is a hardcoded api_key =
"test-api-key"; replace this with an externally-provided value (e.g., read from
an environment variable or a test config) by using
os.environ.get("LOAD_TEST_API_KEY", "test-api-key") or similar, and update test
documentation or README to instruct how to set LOAD_TEST_API_KEY; ensure the
code still falls back to the default for convenience but prefers the external
value for flexibility.
```

</details>

<!-- fingerprinting:phantom:medusa:ocelot -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 66. PR #59 - tests/unit/scripts/test_generate_dataset_status.py

- **Status**: [x]
- **Severity**: low
- **PR**: [#59 - test: consolidate comprehensive test suite from feature branches](https://github.com/williaby/image-preprocessing-detector/pull/59)
- **Reviewer**: @coderabbitai
- **Date**: 2025-12-02
- **File**: `tests/unit/scripts/test_generate_dataset_status.py`
- **Line**: 198

<details>
<summary>Comment</summary>

_🧹 Nitpick_ | _🔵 Trivial_

**Optional: also assert type/shape of GCS credentials constant**

The constant checks for `NFS_ROOT` and `GCS_BUCKET` are useful sanity tests. If you want slightly stronger coverage of the module contract, you could add a small test asserting that `GCS_CREDENTIALS` exists and is a `Path` (or `str`, matching the implementation) since it is used to construct the GCS auth environment.

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In tests/unit/scripts/test_generate_dataset_status.py around lines 186 to 201,
add an assertion to ensure the GCS_CREDENTIALS constant is defined and has the
expected type; import GCS_CREDENTIALS from generate_dataset_status and assert
isinstance(GCS_CREDENTIALS, Path) (or str if the module defines it as a string)
and optionally assert the path/string is non-empty to validate the credential
value shape.
```

</details>

<!-- fingerprinting:phantom:poseidon:olive -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 67. PR #59 - tests/unit/scripts/test_organize_dual_storage.py

- **Status**: [x]
- **Severity**: low
- **PR**: [#59 - test: consolidate comprehensive test suite from feature branches](https://github.com/williaby/image-preprocessing-detector/pull/59)
- **Reviewer**: @coderabbitai
- **Date**: 2025-12-02
- **File**: `tests/unit/scripts/test_organize_dual_storage.py`
- **Line**: 295

<details>
<summary>Comment</summary>

_🧹 Nitpick_ | _🔵 Trivial_

**Robust gsutil invocation testing; optionally assert dataset‑specific path usage**

The `pull_from_gcs` tests cover unknown datasets, successful `gsutil rsync` invocation, and `CalledProcessError` handling, with clean mocking of `subprocess.run` and credentials. As an optional enhancement, consider asserting that the constructed command includes the expected bucket/path segment for the chosen dataset (e.g., using `DATASETS["tablebank"]["gcs_path"]`) so that a miswired source/destination would be caught by tests, not just by integration runs.

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In tests/unit/scripts/test_organize_dual_storage.py around lines 233 to 295, add
an assertion that the gsutil command includes the dataset-specific GCS path so
test fails if the source/destination is miswired; retrieve the expected path
from the module under test (e.g., import or reference
organize_dual_storage.DATASETS["tablebank"]["gcs_path"] or patch DATASETS) and
assert that expected_path is a substring of the constructed cmd list (or its
joined string) after mock_run was called.
```

</details>

<!-- fingerprinting:phantom:poseidon:olive -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 68. PR #59 - tests/unit/scripts/test_organize_dual_storage.py

- **Status**: [x]
- **Severity**: low
- **PR**: [#59 - test: consolidate comprehensive test suite from feature branches](https://github.com/williaby/image-preprocessing-detector/pull/59)
- **Reviewer**: @coderabbitai
- **Date**: 2025-12-02
- **File**: `tests/unit/scripts/test_organize_dual_storage.py`
- **Line**: 341

<details>
<summary>Comment</summary>

_🧹 Nitpick_ | _🔵 Trivial_

**Sync tests capture main failure and success paths; you can mirror the command checks from pull**

These `sync_to_gcs` tests nicely mirror the `pull_from_gcs` coverage: unknown dataset, missing NFS, and successful `gsutil` call, with `mock_run.assert_called_once()` ensuring exactly one subprocess invocation. Similar to `pull_from_gcs`, you might also validate that the command arguments include the expected local NFS path and GCS path for the selected dataset, which would harden the tests against accidental source/destination swaps.

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In tests/unit/scripts/test_organize_dual_storage.py around lines 296 to 341, the
successful sync test only asserts that subprocess.run was called once but does
not verify the exact gsutil command or that the local NFS and GCS paths are
correct; update the test to assert the subprocess.run call arguments include the
expected source (nfs_dataset path) and destination (GCS path for "tablebank")
and the credential env var or -i flag as used by sync_to_gcs (e.g., use
mock_run.assert_called_once_with(...) or inspect mock_run.call_args and compare
the command list and kwargs), keeping the existing returncode setup and print
patching intact.
```

</details>

<!-- fingerprinting:phantom:poseidon:olive -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 69. PR #59 - tests/api/test_api_comprehensive.py

- **Status**: [x]
- **Severity**: low
- **PR**: [#59 - test: consolidate comprehensive test suite from feature branches](https://github.com/williaby/image-preprocessing-detector/pull/59)
- **Reviewer**: @coderabbitai
- **Date**: 2025-12-02
- **File**: `tests/api/test_api_comprehensive.py`
- **Line**: 478

<details>
<summary>Comment</summary>

_🧹 Nitpick_ | _🔵 Trivial_

**Consider simplifying the schema import failure test.**

The current approach of patching `builtins.__import__` is complex and fragile. The test may not accurately simulate a real schema import failure scenario.


A simpler approach would be to mock the specific check within the readiness endpoint rather than manipulating the import system:

```python
def test_ready_with_schema_import_failure(self) -> None:
    """Readiness check fails when schema import fails."""
    settings = APISettings(
        title="Test API",
        rate_limit_enabled=False,
        auth_enabled=False,
    )
    app = create_app(settings=settings)
    client = TestClient(app)

    # Mock the schema check to simulate failure
    with patch(
        "image_preprocessing_detector.api.routes.health.check_schema_available",
        return_value=False,
    ):
        response = client.get("/ready")
        data = response.json()
        assert "schema" in data["checks"]
```

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
tests/api/test_api_comprehensive.py lines 405-478: the test simulates a schema
import failure by patching builtins.__import__, which is fragile and
unnecessary; instead, patch the specific readiness check function that verifies
schema availability. Replace the complex import-mocking block with a patch of
"image_preprocessing_detector.api.routes.health.check_schema_available" to
return False, call client.get("/ready"), and assert that "schema" is present in
data["checks"] (and/or that the schema check value is False) so the test
reliably simulates a schema failure.
```

</details>

<!-- fingerprinting:phantom:medusa:ocelot -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 70. PR #56 - data/doccreator_loader.py

- **Status**: [x]
- **Severity**: low
- **PR**: [#56 - feat: integrate org-level reusable workflows and resolve security issues](https://github.com/williaby/image-preprocessing-detector/pull/56)
- **Reviewer**: @coderabbitai
- **Date**: 2025-12-01
- **File**: `data/doccreator_loader.py`
- **Line**: 222

<details>
<summary>Comment</summary>

_🛠️ Refactor suggestion_ | _🟠 Major_

**Duplicate `validate_safe_path` function - use centralized utility.**

This function is duplicated from `src/image_preprocessing_detector/utils/path_security.py` (as shown in relevant snippets). The PR already has a centralized path security module.



```diff
-def validate_safe_path(
-    file_path: str | Path, allowed_base: str | Path | None = None
-) -> Path:
-    """Validate file path to prevent directory traversal attacks.
-    ...
-    """
-    path = Path(file_path).resolve()
-
-    # Check for path traversal patterns
-    if ".." in str(file_path):
-        raise ValueError(f"Path traversal detected: {file_path}")
-
-    # If allowed_base specified, ensure path is within it
-    if allowed_base:
-        base = Path(allowed_base).resolve()
-        if not str(path).startswith(str(base)):
-            raise ValueError(f"Path {path} is outside allowed base {base}")
-
-    return path
+from image_preprocessing_detector.utils.path_security import validate_safe_path
```

Note: The centralized version in `path_security.py` also supports `must_exist` parameter which could be useful.


> Committable suggestion skipped: line range outside the PR's diff.

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In data/doccreator_loader.py around lines 196 to 224, the validate_safe_path
function is a duplicate of the centralized utility in
src/image_preprocessing_detector/utils/path_security.py; remove this duplicate
and import and call the shared validate_safe_path from that module instead
(adjusting any call sites), and if callers require existence checks, pass
through or add use of the centralized function's must_exist parameter so
behavior remains consistent; ensure imports are updated and tests adjusted
accordingly.
```

</details>

<!-- fingerprinting:phantom:medusa:ocelot -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 71. PR #56 - modal/generate_pseudo_labels.py

- **Status**: [~]
- **Severity**: low
- **PR**: [#56 - feat: integrate org-level reusable workflows and resolve security issues](https://github.com/williaby/image-preprocessing-detector/pull/56)
- **Reviewer**: @coderabbitai
- **Date**: 2025-12-01
- **File**: `modal/generate_pseudo_labels.py`
- **Line**: 610

<details>
<summary>Comment</summary>

_🛠️ Refactor suggestion_ | _🟠 Major_

**Refactor `process_gcs_dataset` to reduce cognitive complexity.**

SonarCloud flagged this function with complexity 26 (allowed: 15). The function handles GCS setup, image listing, filtering, batching, labeling, and checkpointing - too many responsibilities.



Extract helper functions for separation of concerns:

```python
# Suggested extraction:
def _setup_gcs_credentials() -> storage.Client:
    """Setup GCS client with credentials from environment."""
    gcp_sa_key = os.environ.get("GCP_SA_KEY")
    if gcp_sa_key:
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(base64.b64decode(gcp_sa_key).decode())
            credentials_path = f.name
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
    return storage.Client()


def _list_pending_images(
    bucket: storage.Bucket,
    prefix: str,
    output_prefix: str,
    max_images: int | None,
    resume: bool,
) -> list[storage.Blob]:
    """List images pending processing, excluding already processed."""
    # ... filtering logic
```

<details>
<summary>🧰 Tools</summary>

<details>
<summary>🪛 GitHub Check: SonarCloud Code Analysis</summary>

[failure] 512-512: Define a constant instead of duplicating this literal ".tiff" 3 times.

See more on https://sonarcloud.io/project/issues?id=williaby_image-preprocessing-detector&issues=AZrbDSEeyMDzcBtENpsD&open=AZrbDSEeyMDzcBtENpsD&pullRequest=56

---

[failure] 471-471: Refactor this function to reduce its Cognitive Complexity from 26 to the 15 allowed.

See more on https://sonarcloud.io/project/issues?id=williaby_image-preprocessing-detector&issues=AZrbDSEeyMDzcBtENpsJ&open=AZrbDSEeyMDzcBtENpsJ&pullRequest=56

---

[failure] 474-474: Define a constant instead of duplicating this literal "labels/" 3 times.

See more on https://sonarcloud.io/project/issues?id=williaby_image-preprocessing-detector&issues=AZrbDSEeyMDzcBtENpsG&open=AZrbDSEeyMDzcBtENpsG&pullRequest=56

</details>

</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In modal/generate_pseudo_labels.py around lines 471 to 612, the function
process_gcs_dataset is overly complex (SonarCloud complexity 26) because it
mixes GCS credential setup, listing/filtering images, downloading, batching,
labeling, saving, and checkpointing; extract responsibilities into small
helpers: _setup_gcs_credentials() to configure GOOGLE_APPLICATION_CREDENTIALS
and return a storage.Client, _list_pending_images(bucket, prefix, output_prefix,
max_images, resume) to list blobs and return the filtered pending image blobs,
_download_batch(batch_blobs) to download bytes and ids while updating error
stats, _save_results(bucket, results, output_prefix, stats) to upload label
files and update stats, and _save_checkpoint(bucket, output_prefix, stats,
force=False) to write periodic/final stats; then simplify process_gcs_dataset to
call these helpers in sequence, keeping only high-level loop logic and stats
aggregation to reduce cognitive complexity.
```

</details>

<!-- fingerprinting:phantom:medusa:ocelot -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 72. PR #56 - scripts/omnidocbench_baseline/run_baseline_evaluation.py

- **Status**: [~]
- **Severity**: low
- **PR**: [#56 - feat: integrate org-level reusable workflows and resolve security issues](https://github.com/williaby/image-preprocessing-detector/pull/56)
- **Reviewer**: @coderabbitai
- **Date**: 2025-12-01
- **File**: `scripts/omnidocbench_baseline/run_baseline_evaluation.py`
- **Line**: 307

<details>
<summary>Comment</summary>

_🧹 Nitpick_ | _🔵 Trivial_

**Missing error handling for dataset loading failure.**

The `load_dataset` call could fail for various reasons (network issues, authentication, dataset unavailable). Consider adding more specific error handling.



```diff
     try:
-        from datasets import load_dataset
+        from datasets import load_dataset, DatasetDict
     except ImportError:
         logger.error("datasets library required. Install with: pip install datasets")
         sys.exit(1)

     logger.info("Loading OmniDocBench from HuggingFace...")
     token = token or os.getenv("HF_TOKEN")

+    try:
         dataset = load_dataset(
             "opendatalab/OmniDocBench",
             token=token,
             trust_remote_code=True,
         )
+    except Exception as e:
+        logger.error(f"Failed to load OmniDocBench dataset: {e}")
+        logger.info("Ensure HF_TOKEN is set for gated datasets")
+        sys.exit(1)
```

<!-- suggestion_start -->

<details>
<summary>📝 Committable suggestion</summary>

> ‼️ **IMPORTANT**
> Carefully review the code before committing. Ensure that it accurately replaces the highlighted code, contains no missing lines, and has no issues with indentation. Thoroughly test & benchmark the code to ensure it meets the requirements.

```suggestion
        from datasets import load_dataset, DatasetDict
    except ImportError:
        logger.error("datasets library required. Install with: pip install datasets")
        sys.exit(1)

    logger.info("Loading OmniDocBench from HuggingFace...")
    token = token or os.getenv("HF_TOKEN")

    try:
        dataset = load_dataset(
            "opendatalab/OmniDocBench",
            token=token,
            trust_remote_code=True,
        )
    except Exception as e:
        logger.error(f"Failed to load OmniDocBench dataset: {e}")
        logger.info("Ensure HF_TOKEN is set for gated datasets")
        sys.exit(1)
```

</details>

<!-- suggestion_end -->

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In scripts/omnidocbench_baseline/run_baseline_evaluation.py around lines 295 to
307, the call to load_dataset lacks error handling; wrap the load_dataset(...)
invocation in a try/except block that catches specific HuggingFace/data-related
exceptions (and a broad Exception fallback), log a clear error including the
exception message and any token/auth guidance, and exit with a non-zero status
if loading fails so the script fails fast and surfaces the root cause.
```

</details>

<!-- fingerprinting:phantom:medusa:ocelot -->

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 73. PR #54 - data/test_fixtures/README.md

- **Status**: [x]
- **Severity**: low
- **PR**: [#54 - chore: merge markdownlint fixes and resolve compatibility issues](https://github.com/williaby/image-preprocessing-detector/pull/54)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-26
- **File**: `data/test_fixtures/README.md`
- **Line**: 369

<details>
<summary>Comment</summary>

_🧹 Nitpick_ | _🔵 Trivial_

**Ensure proper citation format for LIVE dataset citation block.**

The citation block is formatted as text but should use standard BibTeX or inline citation format for clarity in automated citation tools. Line 365-369 appears to be plain text rather than a structured format.



Consider updating to standard BibTeX format:

```bibtex
@article{sheikh2006live,
  title={A statistical evaluation of recent full reference image quality assessment algorithms},
  author={Sheikh, H.R. and Seshadrinathan, K. and Moorthy, A.K. and Wang, Z. and Bovik, A.C. and Cormack, L.K.},
  journal={IEEE Transactions on Image Processing},
  volume={15},
  number={11},
  pages={3440--3451},
  year={2006}
}
```

<details>
<summary>🤖 Prompt for AI Agents</summary>

````

In data/test_fixtures/README.md around lines 363 to 369, the LIVE dataset
citation is currently a plain text fenced block; replace it with a standard
BibTeX formatted fenced block (```bibtex ...```) containing the full @article
entry for Sheikh et al. 2006 (title, authors, journal, volume, number, pages,
year) and ensure the fence language is bibtex (not text) and the surrounding
header "IQA Fixtures Citation (required for LIVE dataset):" remains unchanged so
automated citation tools can parse it.

````

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 74. PR #53 - Dockerfile.gpu

- **Status**: [x]
- **Severity**: low
- **PR**: [#53 - feat: Phase 5 testing, documentation, and infrastructure improvements](https://github.com/williaby/image-preprocessing-detector/pull/53)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-26
- **File**: `Dockerfile.gpu`
- **Line**: 16

<details>
<summary>Comment</summary>

_🧹 Nitpick_ | _🔵 Trivial_

**Pin APT package versions to ensure reproducible builds.**

Unversioned packages can lead to non-deterministic builds and security drift. Specify versions explicitly:

```diff
-RUN apt-get update && apt-get install -y --no-install-recommends \
-    build-essential \
-    curl \
+RUN apt-get update && apt-get install -y --no-install-recommends \
+    build-essential=12.9.3 \
+    curl=7.68.0-1ubuntu2.24 \
```

(Adjust version numbers to match your baseline.)

<!-- suggestion_start -->

<details>
<summary>📝 Committable suggestion</summary>

> ‼️ **IMPORTANT**
> Carefully review the code before committing. Ensure that it accurately replaces the highlighted code, contains no missing lines, and has no issues with indentation. Thoroughly test & benchmark the code to ensure it meets the requirements.

```suggestion
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential=12.9.3 \
    curl=7.68.0-1ubuntu2.24 \
    && rm -rf /var/lib/apt/lists/*
```

</details>

<!-- suggestion_end -->

<details>
<summary>🧰 Tools</summary>

<details>
<summary>🪛 Hadolint (2.14.0)</summary>

[warning] 12-12: Pin versions in apt get install. Instead of `apt-get install <package>` use `apt-get install <package>=<version>`

(DL3008)

</details>

</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In Dockerfile.gpu around lines 12 to 15 the apt-get install call uses unpinned
package names which makes builds non-deterministic; update the Dockerfile to pin
each package to an explicit version (e.g. build-essential=<version>,
curl=<version>) by specifying package=version in the apt-get install command,
record the chosen baseline versions in a comment or variable, and ensure apt-get
update runs immediately before the install so the pinned versions are
resolvable; optionally document how to obtain the exact version strings
(apt-cache policy / apt list -a) and use --no-install-recommends as you already
do.
```

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 75. PR #53 - k8s/deployment.yaml

- **Status**: [~]
- **Severity**: low
- **PR**: [#53 - feat: Phase 5 testing, documentation, and infrastructure improvements](https://github.com/williaby/image-preprocessing-detector/pull/53)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-26
- **File**: `k8s/deployment.yaml`
- **Line**: 78

<details>
<summary>Comment</summary>

_🧹 Nitpick_ | _🔵 Trivial_

**Consider enabling read-only root filesystem for enhanced security.**

Currently `readOnlyRootFilesystem: false`. If the application can function with a read-only root, enabling this reduces the attack surface. If writes to root are required, the current setting is acceptable but should be documented.



If writable root is not required:

```diff
         securityContext:
           allowPrivilegeEscalation: false
-          readOnlyRootFilesystem: false
+          readOnlyRootFilesystem: true
           capabilities:
             drop:
               - ALL
```

Then ensure `/app/tmp` and `/app/logs` are properly mounted as writable volumes (they are—see volumeMounts at line 79-83).

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In k8s/deployment.yaml around lines 73 to 78, change the pod securityContext to
set readOnlyRootFilesystem: true if the application does not need to write to
the container root; ensure writable paths (/app/tmp and /app/logs) are
explicitly listed under volumeMounts (see lines 79–83) and backed by volumes so
the app can write there, or if root writes are required, add a comment
documenting why readOnlyRootFilesystem remains false and which paths must be
writable; update the manifest accordingly.
```

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 76. PR #53 - docs/planning/workflows_opus/TEST_GAP_REMEDIATION_PLAN.md

- **Status**: [x]
- **Severity**: low
- **PR**: [#53 - feat: Phase 5 testing, documentation, and infrastructure improvements](https://github.com/williaby/image-preprocessing-detector/pull/53)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-26
- **File**: `docs/planning/workflows_opus/TEST_GAP_REMEDIATION_PLAN.md`
- **Line**: 711

<details>
<summary>Comment</summary>

_🧹 Nitpick_ | _🔵 Trivial_

**Secrets handling in CI example writes credentials to disk.**

The example CI configuration writes the GCP service account key JSON to a file (`/tmp/gcp-key.json`). While this is common practice, consider noting that:
1. The file should be cleaned up after use
2. Using workload identity federation is preferred over long-lived service account keys

This is documentation, so it's advisory rather than a code issue.

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In docs/planning/workflows_opus/TEST_GAP_REMEDIATION_PLAN.md around lines 686 to
696, the CI example writes the GCP service account JSON to /tmp/gcp-key.json
without guidance on cleanup or safer alternatives; update the docs to (1) show
or state that the temporary credentials file must be removed after use (e.g.,
delete or shred the file and unset GOOGLE_APPLICATION_CREDENTIALS in the
workflow), and (2) recommend using Workload Identity Federation or other
short-lived credential methods instead of long-lived service account keys,
including a brief note or links to GCP docs for configuring Workload Identity
Federation for GitHub Actions.
```

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 77. PR #52 - scripts/validate_pdf_classification.py

- **Status**: [x]
- **Severity**: low
- **PR**: [#52 - refactor: fix qlty issues, add linter configs, reduce complexity](https://github.com/williaby/image-preprocessing-detector/pull/52)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-25
- **File**: `scripts/validate_pdf_classification.py`
- **Line**: 63

<details>
<summary>Comment</summary>

_🛠️ Refactor suggestion_ | _🟠 Major_

**Remove duplicated path validation - use `_path_security` module instead.**

This `_validate_path` function duplicates the functionality already provided by `scripts/_path_security.py` (which `create_final_dataset.py` uses). This violates DRY and could lead to inconsistent validation behavior across scripts.



```diff
+from _path_security import (
+    PathValidationError,
+    validate_input_path,
+    validate_output_path,
+)
+
-def _validate_path(path: Path, must_exist: bool = True) -> Path:
-    """
-    Validate and resolve a path to prevent path traversal attacks.
-    ...
-    """
-    try:
-        resolved = path.resolve(strict=must_exist)
-    except (OSError, RuntimeError) as e:
-        msg = f"Invalid path: {path}"
-        raise ValueError(msg) from e
-
-    # Ensure path doesn't contain suspicious patterns
-    path_str = str(resolved)
-    if "\x00" in path_str:
-        msg = f"Path contains null bytes: {path}"
-        raise ValueError(msg)
-
-    return resolved
```

Then update usages:
- `_validate_path(labels_file, must_exist=True)` → `validate_input_path(labels_file)`
- `_validate_path(args.pdf_dir, must_exist=True)` → `validate_directory(args.pdf_dir)`
- Output path validation → `validate_output_path(args.output)`


> Committable suggestion skipped: line range outside the PR's diff.

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In scripts/validate_pdf_classification.py around lines 37 to 63, remove the
duplicated _validate_path function and replace its usages to rely on the central
scripts/_path_security.py helpers: import validate_input_path,
validate_directory, validate_output_path from scripts._path_security and change
calls accordingly — replace _validate_path(labels_file, must_exist=True) with
validate_input_path(labels_file), replace _validate_path(args.pdf_dir,
must_exist=True) with validate_directory(args.pdf_dir), and replace the output
path validation with validate_output_path(args.output); ensure the import is
added at top and delete the _validate_path function to avoid duplication.
```

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 78. PR #51 - .claude/agents/security-auditor.md

- **Status**: [x]
- **Severity**: low
- **PR**: [#51 - chore: align project with cookiecutter-python-template standards](https://github.com/williaby/image-preprocessing-detector/pull/51)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-25
- **File**: `.claude/agents/security-auditor.md`
- **Line**: 55

<details>
<summary>Comment</summary>

_🧹 Nitpick_ | _🔵 Trivial_

**Minor wording: avoid repeating "properly" in configuration checklist.**

Lines 52-56 repeat "properly" adjacent to each other. Consider rewording for variety:

```diff
-### Configuration Security
-- [ ] Secrets in environment variables
-- [ ] Secure default configurations
-- [ ] TLS/SSL properly configured
-- [ ] CORS properly restricted
+### Configuration Security
+- [ ] Secrets in environment variables
+- [ ] Secure default configurations
+- [ ] TLS/SSL configured securely
+- [ ] CORS properly restricted
```

Minor style improvement; content is solid and commands correctly use `uv run`.

<details>
<summary>🧰 Tools</summary>

<details>
<summary>🪛 LanguageTool</summary>

[style] ~55-~55: This adverb was used twice in the sentence. Consider removing one of them or replacing them with a synonym.
Context: ... TLS/SSL properly configured - [ ] CORS properly restricted  ### Authentication & Author...

(ADVERB_REPETITION_PREMIUM)

</details>
<details>
<summary>🪛 markdownlint-cli2 (0.18.1)</summary>

51-51: Headings should be surrounded by blank lines
Expected: 1; Actual: 0; Below

(MD022, blanks-around-headings)

</details>

</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In .claude/agents/security-auditor.md around lines 51 to 55 the checklist
repeats the word "properly" in adjacent items; update the wording to avoid
duplication by rephrasing those two lines — for example change "TLS/SSL properly
configured" to "TLS/SSL configured and enforced" and change "CORS properly
restricted" to "CORS restricted to trusted origins" (or similar concise
alternatives) so the checklist reads more smoothly while preserving the same
meaning.
```

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 79. PR #51 - .claude/commands/meta-list-commands.md

- **Status**: [x]
- **Severity**: low
- **PR**: [#51 - chore: align project with cookiecutter-python-template standards](https://github.com/williaby/image-preprocessing-detector/pull/51)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-25
- **File**: `.claude/commands/meta-list-commands.md`
- **Line**: 25

<details>
<summary>Comment</summary>

_🛠️ Refactor suggestion_ | _🟠 Major_

**Convert category descriptions from emphasis to headings.**

Lines 25, 99, 115, and 131 use emphasis (`**...**`) for category descriptions instead of proper markdown headings. Convert these to heading format for proper document structure (MD036):

**Lines 25 (Quality), 99 (Security), 115 (Workflow), 131 (Meta):**
```diff
-**Code formatting and quality validation across file types**
+#### Code Formatting and Quality Validation
+Code formatting and quality validation across file types.
```

This improves document accessibility and structure.




Also applies to: 99-99, 115-115, 131-131

<details>
<summary>🧰 Tools</summary>

<details>
<summary>🪛 markdownlint-cli2 (0.18.1)</summary>

25-25: Emphasis used instead of a heading

(MD036, no-emphasis-as-heading)

</details>

</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In .claude/commands/meta-list-commands.md around lines 25, 99, 115, and 131, the
category descriptions are written using bold/emphasis (**...**) instead of
markdown headings; replace each emphasized category description with an
appropriate markdown heading (e.g., prepend one or more # characters to create
H2/H3 as desired) so they become proper headings, ensure spacing before and
after the heading lines follows Markdown conventions, and verify the updated
headings pass MD036 linting.
```

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 80. PR #51 - .claude/skills/security/workflows/encrypt.md

- **Status**: [x]
- **Severity**: low
- **PR**: [#51 - chore: align project with cookiecutter-python-template standards](https://github.com/williaby/image-preprocessing-detector/pull/51)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-25
- **File**: `.claude/skills/security/workflows/encrypt.md`
- **Line**: 76

<details>
<summary>Comment</summary>

_🧹 Nitpick_ | _🔵 Trivial_

**Add blank lines around headings and code blocks for markdown compliance.**

Multiple heading and code block spacing violations. All headings should have a blank line below before subsequent content, and code blocks need blank lines before and after.


Key spacing issues throughout:
- Lines 12, 24, 42, 50, 57, 68: Headings need blank line below before code/content
- Lines 14, 25, 44, 52, 58: Code blocks need blank line above
- All code blocks already have blank lines below in most cases, but some are missing

Example fix (lines 11–15):

```diff
 ## Encryption
+
 ### Symmetric Encryption (Password-based)
+
 ```bash
 gpg --symmetric --cipher-algo AES256 \
```

Apply consistently throughout the document to pass linting and improve readability.

<details>
<summary>🧰 Tools</summary>

<details>
<summary>🪛 LanguageTool</summary>

[grammar] ~72-~72: Ensure spelling is correct
Context: ...es - Rotate encryption keys periodically - Backup GPG private keys securely - Use strong ...

(QB_NEW_EN_ORTHOGRAPHY_ERROR_IDS_1)

</details>
<details>
<summary>🪛 markdownlint-cli2 (0.18.1)</summary>

13-13: Headings should be surrounded by blank lines
Expected: 1; Actual: 0; Below

(MD022, blanks-around-headings)

---

14-14: Fenced code blocks should be surrounded by blank lines

(MD031, blanks-around-fences)

---

24-24: Headings should be surrounded by blank lines
Expected: 1; Actual: 0; Below

(MD022, blanks-around-headings)

---

25-25: Fenced code blocks should be surrounded by blank lines

(MD031, blanks-around-fences)

---

43-43: Headings should be surrounded by blank lines
Expected: 1; Actual: 0; Below

(MD022, blanks-around-headings)

---

44-44: Fenced code blocks should be surrounded by blank lines

(MD031, blanks-around-fences)

---

51-51: Headings should be surrounded by blank lines
Expected: 1; Actual: 0; Below

(MD022, blanks-around-headings)

---

52-52: Fenced code blocks should be surrounded by blank lines

(MD031, blanks-around-fences)

---

57-57: Headings should be surrounded by blank lines
Expected: 1; Actual: 0; Below

(MD022, blanks-around-headings)

---

58-58: Fenced code blocks should be surrounded by blank lines

(MD031, blanks-around-fences)

</details>

</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

````

In .claude/skills/security/workflows/encrypt.md around lines 12 to 76, several
headings and fenced code blocks lack required blank lines before/after them; add
a single blank line after each heading (lines 12, 24, 42, 50, 57, 68) and ensure
each code fence has a blank line above it (lines 14, 25, 44, 52, 58) so every
heading is followed by an empty line and each ```bash (or```) code block is
preceded and followed by a blank line to satisfy Markdown linting and improve
readability.

````

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 81. PR #51 - .claude/agents/api-development-agent.md

- **Status**: [x]
- **Severity**: low
- **PR**: [#51 - chore: align project with cookiecutter-python-template standards](https://github.com/williaby/image-preprocessing-detector/pull/51)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-25
- **File**: `.claude/agents/api-development-agent.md`
- **Line**: 32

<details>
<summary>Comment</summary>

_🧹 Nitpick_ | _🔵 Trivial_

**Use hyphenated compound adjective: "rate-limiting" modifies the noun.**

Line 32 reads "API gateway integration and rate limiting" but should use "rate-limiting" when it modifies the following noun.

```diff
-  - API gateway integration and rate limiting
+  - API gateway integration and rate-limiting configuration
```

<!-- suggestion_start -->

<details>
<summary>📝 Committable suggestion</summary>

> ‼️ **IMPORTANT**
> Carefully review the code before committing. Ensure that it accurately replaces the highlighted code, contains no missing lines, and has no issues with indentation. Thoroughly test & benchmark the code to ensure it meets the requirements.

```suggestion
- API gateway integration and rate-limiting configuration
```

</details>

<!-- suggestion_end -->

<details>
<summary>🧰 Tools</summary>

<details>
<summary>🪛 LanguageTool</summary>

[uncategorized] ~32-~32: If this is a compound adjective that modifies the following noun, use a hyphen.
Context: ...Insomnia) - API gateway integration and rate limiting - Authentication and authorization impl...

(EN_COMPOUND_ADJECTIVE_INTERNAL)

</details>

</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In .claude/agents/api-development-agent.md around line 32, the phrase "API
gateway integration and rate limiting" uses an un-hyphenated compound adjective;
update the text to "API gateway integration and rate-limiting" (or rephrase so
"rate limiting" is not used as a modifier) by editing line 32 to include the
hyphen.
```

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 82. PR #51 - .claude/agents/security-auditor.md

- **Status**: [x]
- **Severity**: low
- **PR**: [#51 - chore: align project with cookiecutter-python-template standards](https://github.com/williaby/image-preprocessing-detector/pull/51)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-25
- **File**: `.claude/agents/security-auditor.md`
- **Line**: 57

<details>
<summary>Comment</summary>

_🛠️ Refactor suggestion_ | _🟠 Major_

**Add blank lines before all subheadings for markdown compliance.**

This file has 8 markdown linting violations (MD022): subheadings on lines 11, 17, 23, 29, 37, 45, 51, 57 lack required blank lines above them. Add one blank line before each `### Subheading`.



Example for lines 9–11:

```diff
 ## Capabilities

+
 ### Vulnerability Detection
```

Apply this pattern consistently throughout the file (before lines 17, 23, 29, 37, 45, 51, 57).



> Committable suggestion skipped: line range outside the PR's diff.

<details>
<summary>🧰 Tools</summary>

<details>
<summary>🪛 LanguageTool</summary>

[style] ~55-~55: This adverb was used twice in the sentence. Consider removing one of them or replacing them with a synonym.
Context: ... TLS/SSL properly configured - [ ] CORS properly restricted  ### Authentication & Author...

(ADVERB_REPETITION_PREMIUM)

</details>
<details>
<summary>🪛 markdownlint-cli2 (0.18.1)</summary>

11-11: Headings should be surrounded by blank lines
Expected: 1; Actual: 0; Below

(MD022, blanks-around-headings)

---

17-17: Headings should be surrounded by blank lines
Expected: 1; Actual: 0; Below

(MD022, blanks-around-headings)

---

23-23: Headings should be surrounded by blank lines
Expected: 1; Actual: 0; Below

(MD022, blanks-around-headings)

---

29-29: Headings should be surrounded by blank lines
Expected: 1; Actual: 0; Below

(MD022, blanks-around-headings)

---

37-37: Headings should be surrounded by blank lines
Expected: 1; Actual: 0; Below

(MD022, blanks-around-headings)

---

45-45: Headings should be surrounded by blank lines
Expected: 1; Actual: 0; Below

(MD022, blanks-around-headings)

---

51-51: Headings should be surrounded by blank lines
Expected: 1; Actual: 0; Below

(MD022, blanks-around-headings)

---

57-57: Headings should be surrounded by blank lines
Expected: 1; Actual: 0; Below

(MD022, blanks-around-headings)

</details>

</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
.claude/agents/security-auditor.md lines 11–57: several third-level headings
lack the required blank line above them (MD022). Insert a single blank line
immediately before each `### ...` subheading at the specified lines (11, 17, 23,
29, 37, 45, 51, 57) so every `###` heading is preceded by one empty line; apply
this consistently throughout the file.
```

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 83. PR #51 - .claude/context/development-standards.md

- **Status**: [x]
- **Severity**: low
- **PR**: [#51 - chore: align project with cookiecutter-python-template standards](https://github.com/williaby/image-preprocessing-detector/pull/51)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-25
- **File**: `.claude/context/development-standards.md`
- **Line**: 12

<details>
<summary>Comment</summary>

_🛠️ Refactor suggestion_ | _🟠 Major_

**Add blank lines before section headings to satisfy markdown linting (MD022, MD031).**

Multiple headings lack preceding blank lines, and several code blocks lack surrounding blank lines. This creates 12+ markdown linting violations. Apply this pattern throughout:

```diff
  **Standards**:
  - Line length: 88 characters (Python), 120 (Markdown/YAML)
  - Type hints required on all public functions
  - Docstrings required (Google style)
+
  ### Security
```

Affected sections: "### Code Quality" (line 12), "### Security" (line 27), "### Testing" (line 44), "### Git Workflow" (line 59), "## Naming Conventions" (line 75), "## Documentation Standards" (line 87), "## Environment Setup" (line 94), "## Pre-Commit Checklist" (line 113), "## Common Commands by Task" (line 125), "### Starting New Feature" (line 126), "### Before Commit" (line 136), "### Before Push" (line 140), "## File Organization" (line 153).




Also applies to: 27-27, 44-44, 59-59, 75-75, 87-87, 94-94, 113-113, 125-125, 135-135, 140-140, 153-153

<details>
<summary>🧰 Tools</summary>

<details>
<summary>🪛 markdownlint-cli2 (0.18.1)</summary>

12-12: Headings should be surrounded by blank lines
Expected: 1; Actual: 0; Below

(MD022, blanks-around-headings)

</details>

</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
.claude/context/development-standards.md lines 12, 27, 44, 59, 75, 87, 94, 113,
125-126, 135-136, 140, 153: several headings and surrounding code blocks lack a
preceding blank line causing markdown-lint violations (MD022, MD031); insert a
single blank line immediately before each listed heading and ensure code blocks
have an empty line before and after them throughout the file so every heading
and fenced/indented code block is separated by at least one blank line to
satisfy the lint rules.
```

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 84. PR #51 - .claude/skills/security/context/security-commands.md

- **Status**: [x]
- **Severity**: low
- **PR**: [#51 - chore: align project with cookiecutter-python-template standards](https://github.com/williaby/image-preprocessing-detector/pull/51)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-25
- **File**: `.claude/skills/security/context/security-commands.md`
- **Line**: 13

<details>
<summary>Comment</summary>

_🛠️ Refactor suggestion_ | _🟠 Major_

**Add blank lines before subheadings (MD022 violations).**

The file has 5 markdown linting violations where subheadings lack preceding blank lines (lines 13, 24, 43, 51, 57).

```diff
  # Security Commands

  Comprehensive security validation, scanning, and enforcement commands for development environments and applications.
+
  ## Quick Reference
```

Apply the same pattern before "## Environment Security Validation", "### GPG Key Validation", "### SSH Key Validation", "### Git Security Configuration", and "## Dependency Security Scanning".




Also applies to: 24-24, 43-43, 51-51, 57-57

<details>
<summary>🧰 Tools</summary>

<details>
<summary>🪛 markdownlint-cli2 (0.18.1)</summary>

13-13: Headings should be surrounded by blank lines
Expected: 1; Actual: 0; Below

(MD022, blanks-around-headings)

</details>

</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In .claude/skills/security/context/security-commands.md around lines 13, 24, 43,
51, and 57, several subheadings are missing a preceding blank line (MD022). For
each of those lines insert a single blank line immediately before the heading
("## Environment Security Validation", "### GPG Key Validation", "### SSH Key
Validation", "### Git Security Configuration", and "## Dependency Security
Scanning") so each heading is separated by one empty line from the previous
content, then save the file.
```

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 85. PR #51 - .claude/skills/security/workflows/validate-env.md

- **Status**: [x]
- **Severity**: low
- **PR**: [#51 - chore: align project with cookiecutter-python-template standards](https://github.com/williaby/image-preprocessing-detector/pull/51)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-25
- **File**: `.claude/skills/security/workflows/validate-env.md`
- **Line**: 13

<details>
<summary>Comment</summary>

_🛠️ Refactor suggestion_ | _🟠 Major_

**Add blank lines before subheadings to satisfy markdown linting standards.**

Lines 13, 18, 23, 28, and 32 lack preceding blank lines before their subheadings. Markdownlint rule MD022 requires blank lines around headings for consistency.

```diff
  ## Core Validations
+
  ### 1. SSH Key Validation
  - Check if SSH key is loaded in ssh-agent
  - Verify key type and strength (256-bit minimum)
  - Validate key permissions
+
  ### 2. Git Signing Configuration
  - Check if commit signing is enabled
  - Verify signing key configuration
  - Validate signing format (SSH or GPG)
+
  ### 3. GPG Key Validation (Optional)
  - Check for GPG secret keys
  - Verify key is not expired
  - Confirm encryption capability
+
  ### 4. Git User Configuration
  - Verify user.name is set
  - Verify user.email is set
+
  ### 5. Commit Signature Verification
  - Check recent commits for signatures
  - Validate signature status
```




Also applies to: 18-18, 23-23, 28-28, 32-32

<details>
<summary>🧰 Tools</summary>

<details>
<summary>🪛 markdownlint-cli2 (0.18.1)</summary>

13-13: Headings should be surrounded by blank lines
Expected: 1; Actual: 0; Below

(MD022, blanks-around-headings)

</details>

</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In .claude/skills/security/workflows/validate-env.md around lines 13, 18, 23,
28, and 32, several subheadings lack a blank line before them which violates
markdownlint MD022; fix by inserting a single blank line immediately above each
of the subheading lines (13, 18, 23, 28, 32) so every heading is preceded by one
empty line to satisfy the linting rule.
```

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 86. PR #51 - .github/workflows/sonarcloud.yml

- **Status**: [x]
- **Severity**: low
- **PR**: [#51 - chore: align project with cookiecutter-python-template standards](https://github.com/williaby/image-preprocessing-detector/pull/51)
- **Reviewer**: @coderabbitai
- **Date**: 2025-11-25
- **File**: `.github/workflows/sonarcloud.yml`
- **Line**: 151

<details>
<summary>Comment</summary>

_🧹 Nitpick_ | _🔵 Trivial_

**Consolidate multiple shell redirects into a single grouped redirect.**

The step uses multiple individual `>> $GITHUB_STEP_SUMMARY` redirects (SC2129). Grouping them improves efficiency and readability.

```diff
       - name: Quality Gate Summary
         if: always()
         run: |
-          echo "### SonarCloud Quality Gate" >> $GITHUB_STEP_SUMMARY
-          echo "" >> $GITHUB_STEP_SUMMARY
-          DASH_URL="https://sonarcloud.io/dashboard?id=williaby_image-preprocessing-detector"
-          echo "View detailed results: $DASH_URL" >> $GITHUB_STEP_SUMMARY
-          echo "" >> $GITHUB_STEP_SUMMARY
-          echo "**Metrics analyzed:**" >> $GITHUB_STEP_SUMMARY
-          echo "- Code Quality (bugs, code smells, maintainability)" >> $GITHUB_STEP_SUMMARY
-          echo "- Security (vulnerabilities, security hotspots)" >> $GITHUB_STEP_SUMMARY
-          echo "- Test Coverage" >> $GITHUB_STEP_SUMMARY
-          echo "- Code Duplication" >> $GITHUB_STEP_SUMMARY
-          echo "- Technical Debt" >> $GITHUB_STEP_SUMMARY
+          {
+            echo "### SonarCloud Quality Gate"
+            echo ""
+            DASH_URL="https://sonarcloud.io/dashboard?id=williaby_image-preprocessing-detector"
+            echo "View detailed results: $DASH_URL"
+            echo ""
+            echo "**Metrics analyzed:**"
+            echo "- Code Quality (bugs, code smells, maintainability)"
+            echo "- Security (vulnerabilities, security hotspots)"
+            echo "- Test Coverage"
+            echo "- Code Duplication"
+            echo "- Technical Debt"
+          } >> "$GITHUB_STEP_SUMMARY"
```

<!-- suggestion_start -->

<details>
<summary>📝 Committable suggestion</summary>

> ‼️ **IMPORTANT**
> Carefully review the code before committing. Ensure that it accurately replaces the highlighted code, contains no missing lines, and has no issues with indentation. Thoroughly test & benchmark the code to ensure it meets the requirements.

```suggestion
        run: |
          {
            echo "### SonarCloud Quality Gate"
            echo ""
            DASH_URL="https://sonarcloud.io/dashboard?id=williaby_image-preprocessing-detector"
            echo "View detailed results: $DASH_URL"
            echo ""
            echo "**Metrics analyzed:**"
            echo "- Code Quality (bugs, code smells, maintainability)"
            echo "- Security (vulnerabilities, security hotspots)"
            echo "- Test Coverage"
            echo "- Code Duplication"
            echo "- Technical Debt"
          } >> "$GITHUB_STEP_SUMMARY"
```

</details>

<!-- suggestion_end -->

<details>
<summary>🧰 Tools</summary>

<details>
<summary>🪛 actionlint (1.7.8)</summary>

138-138: shellcheck reported issue in this script: SC2086:info:1:39: Double quote to prevent globbing and word splitting

(shellcheck)

---

138-138: shellcheck reported issue in this script: SC2086:info:2:12: Double quote to prevent globbing and word splitting

(shellcheck)

---

138-138: shellcheck reported issue in this script: SC2129:style:4:1: Consider using { cmd1; cmd2; } >> file instead of individual redirects

(shellcheck)

---

138-138: shellcheck reported issue in this script: SC2086:info:4:44: Double quote to prevent globbing and word splitting

(shellcheck)

---

138-138: shellcheck reported issue in this script: SC2086:info:5:12: Double quote to prevent globbing and word splitting

(shellcheck)

---

138-138: shellcheck reported issue in this script: SC2086:info:6:33: Double quote to prevent globbing and word splitting

(shellcheck)

---

138-138: shellcheck reported issue in this script: SC2086:info:7:63: Double quote to prevent globbing and word splitting

(shellcheck)

---

138-138: shellcheck reported issue in this script: SC2086:info:8:59: Double quote to prevent globbing and word splitting

(shellcheck)

---

138-138: shellcheck reported issue in this script: SC2086:info:9:27: Double quote to prevent globbing and word splitting

(shellcheck)

---

138-138: shellcheck reported issue in this script: SC2086:info:10:30: Double quote to prevent globbing and word splitting

(shellcheck)

---

138-138: shellcheck reported issue in this script: SC2086:info:11:28: Double quote to prevent globbing and word splitting

(shellcheck)

</details>

</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
.github/workflows/sonarcloud.yml around lines 138 to 149: multiple echo
statements each appending with ">> $GITHUB_STEP_SUMMARY" should be consolidated
to a single grouped redirect to improve efficiency and avoid SC2129; replace the
repeated redirects by grouping the echo commands inside a single block
redirected once (e.g., using a here-document or a command group with a single
">> $GITHUB_STEP_SUMMARY") so all summary lines are appended in one operation.
```

</details>

<!-- This is an auto-generated comment by CodeRabbit -->

</details>

### 87. PR #49 - scripts/test_dataset_generation.py

- **Status**: [x]
- **Severity**: low
- **PR**: [#49 - feat: Phase-4 implementation](https://github.com/williaby/image-preprocessing-detector/pull/49)
- **Reviewer**: @copilot-pull-request-reviewer
- **Date**: 2025-11-25
- **File**: `scripts/test_dataset_generation.py`
- **Line**: 53

<details>
<summary>Comment</summary>

[nitpick] The nosec comment correctly identifies this as a controlled subprocess call. However, consider using `shutil.which('uv')` to resolve the full path to the executable for additional security (similar to the pattern in scripts/download_all_datasets.py).

</details>

### 88. PR #2 - CONTRIBUTING.md

- **Status**: [x]
- **Severity**: low
- **PR**: [#2 - docs: Implement OpenSSF Best Practices badge requirements](https://github.com/williaby/image-preprocessing-detector/pull/2)
- **Reviewer**: @copilot-pull-request-reviewer
- **Date**: 2025-11-08
- **File**: `CONTRIBUTING.md`
- **Line**: 412

<details>
<summary>Comment</summary>

The issue response policy commitments (7-14 days for bugs, 14-21 days for enhancements) conflict with the SECURITY.md timelines (7 days acknowledgment for all issues) and docs/badgeapp_response.md suggestions (7 days for bugs, 14 days for enhancements). Standardize response time commitments across all documentation files.
```suggestion
- **Acknowledge all issues (bugs and enhancements)** within 7 days
- **Respond to bug reports** within 7 days
- **Respond to enhancement requests** within 14 days
- **Triage severity** within 14 days of report
```

</details>

### 89. PR #2 - CONTRIBUTING.md

- **Status**: [x]
- **Severity**: low
- **PR**: [#2 - docs: Implement OpenSSF Best Practices badge requirements](https://github.com/williaby/image-preprocessing-detector/pull/2)
- **Reviewer**: @copilot-pull-request-reviewer
- **Date**: 2025-11-08
- **File**: `CONTRIBUTING.md`
- **Line**: 416

<details>
<summary>Comment</summary>

The issue response timeline here states "typically within 7-14 days" for bug reports and "typically within 14-21 days" for enhancement requests, but SECURITY.md specifies "Within 7 days" for acknowledgment and "Within 14 days" for initial assessment without the "typically" qualifier. For consistency across the project documentation, consider aligning these timelines or clarifying that SECURITY.md commitments apply to security issues specifically while general issues follow the more flexible timeline stated here.
```suggestion
**Note**: The above timeframes apply to general issues (bugs and enhancements). For security-related issues, we follow the stricter commitments outlined in [SECURITY.md](SECURITY.md): acknowledgment within 7 days and initial assessment within 14 days.

As a single-maintainer project, these timeframes are goals and may vary depending on workload and availability. All issues will be acknowledged and triaged as promptly as possible, but responses may occasionally take longer during busy periods.
```

</details>

### 90. PR #1 - CHANGELOG.md

- **Status**: [x]
- **Severity**: low
- **PR**: [#1 - Security improvements and ClusterFuzzLite fuzzing integration](https://github.com/williaby/image-preprocessing-detector/pull/1)
- **Reviewer**: @copilot-pull-request-reviewer
- **Date**: 2025-11-07
- **File**: `CHANGELOG.md`
- **Line**: 33

<details>
<summary>Comment</summary>

Missing changelog entry: The CHANGELOG should document the Python version change from 3.12 to 3.11+ under the "### Changed" section. This is a significant change that affects users and should be noted, e.g., "Updated minimum Python version from 3.12 to 3.11 to support Atheris fuzzing compatibility".
```suggestion
- Updated FastAPI from 0.100.1 to >=0.115.0 (fixes PVE-2024-64930 ReDoS vulnerability)
- Updated minimum Python version from 3.12 to 3.11+ to support Atheris fuzzing compatibility
```

</details>

### 91. PR #1 - .github/workflows/cifuzzy.yml

- **Status**: [x]
- **Severity**: low
- **PR**: [#1 - Security improvements and ClusterFuzzLite fuzzing integration](https://github.com/williaby/image-preprocessing-detector/pull/1)
- **Reviewer**: @copilot-pull-request-reviewer
- **Date**: 2025-11-08
- **File**: `.github/workflows/cifuzzy.yml`
- **Line**: 47

<details>
<summary>Comment</summary>

ClusterFuzzLite run_fuzzers action is pinned to @v1 tag instead of SHA hash. While the comment acknowledges this, consider using a commit SHA or tracking the security implications, as this differs from the project's standard of pinning all GitHub Actions to SHA hashes.
```suggestion
        # Pinning ClusterFuzzLite run_fuzzers action to commit SHA for security
        uses: google/clusterfuzzlite/actions/run_fuzzers@c7e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2 # v1.0.0 (replace with actual SHA)
```

</details>
