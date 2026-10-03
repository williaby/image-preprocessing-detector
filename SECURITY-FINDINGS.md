# Security Findings - Image Preprocessing Detector

**Date**: 2026-05-15
**Branch**: `claude/secure-image-preprocessing-yn1RK`
**Scope**: ML pipeline security, metadata handling, dependency pinning, GitHub Actions hardening.

This document records findings from a security review of the image
preprocessing detector. Findings marked **FIXED** are addressed in this
branch; **OPEN** findings require operator action documented below.

---

## Summary

| # | Severity | Area | Title | Status |
|---|----------|------|-------|--------|
| 1 | High | ML | `torch.load(weights_only=False)` in production inference path | **FIXED** |
| 2 | High | ML | `torch.load(weights_only=False)` in Modal training script | **FIXED** (Modal image still pins torch 2.5.1; see finding 2) |
| 3 | Medium | ML | Unvalidated model path in Arena `LocalBackend` | **FIXED** |
| 4 | Medium | ML | Unvalidated model path in Arena `RegressionBackend` | **FIXED** |
| 5 | High | API | No magic-byte content validation on uploads | **FIXED** |
| 6 | High | API | Full upload buffered in memory before size check | **FIXED** |
| 7 | High | API | Batch endpoint has no cumulative size cap | **FIXED** |
| 8 | Medium | API | `validate_file()` `_max_size_mb` parameter unused | **FIXED** |
| 9 | Medium | Ingestion | PDF loader has no `max_pages` limit (DoS risk) | **FIXED** |
| 10 | High | CI | `actions/github-script@v7` not SHA-pinned | **Resolved on `main` (#191)** |
| 11 | High | CI | `astral-sh/setup-uv@v5` not SHA-pinned (3 locations) | **Resolved on `main` (#191)** |
| 12 | Medium | CI | Org-reusable workflows track `main` by SHA; stale-pin risk (3 files) | **OPEN** |
| 13 | Low | CI | 13 workflows lack `step-security/harden-runner` | **OPEN** |
| 14 | Low | Deps | `transformers` constraint in `iqa` extra (`==4.37.2`) | **OPEN** |
| 15 | Low | Metadata | EXIF DPI extraction lacks bounds checking | **Accepted** |

Total: **11 fixed**, **3 documented for follow-up**, **1 accepted**.

---

## ML Pipeline Security

### 1. `torch.load(weights_only=False)` in production inference - **FIXED**

**Severity**: High (Remote Code Execution if checkpoint source is untrusted)

`torch.load` without `weights_only=True` invokes Python's pickle
machinery, which can execute arbitrary code embedded in the checkpoint.
Since PyTorch 2.6 the recommended default is `weights_only=True`; the
inference path bypassed it.

**Location**: `src/image_preprocessing_detector/detection/siglip2_multitask.py:236`

**Before**:

```python
ckpt = torch.load(
    self.checkpoint_path,
    map_location=self._device,
    weights_only=False,
)
state_dict = ckpt.get("model_state_dict", ckpt)
```

**After**: Switched to `weights_only=True` and added a
`isinstance(ckpt, dict)` guard so the downstream `.get()` call is safe
when the checkpoint is a raw state dict.

The trainers store `scipy.stats.spearmanr` output (`numpy.float64`) in the
checkpoint's `metrics` and `composite_score`, which a plain
`weights_only=True` load rejects. The loader therefore goes through
`utils/safe_checkpoint.load_checkpoint_weights_only`, which allowlists only
the pickle globals needed for *numeric* numpy scalars via
`torch.serialization.safe_globals`. Arrays, object dtypes and arbitrary
callables are still rejected; `tests/unit/utils/test_safe_checkpoint.py`
covers a trainer-style round trip and a code-execution payload that must
not run.

**Risk if exploited**: An attacker who can write to the configured
`checkpoint_path` (filesystem, mounted volume, or shared model
registry) could execute arbitrary code in the inference process - including credential exfiltration and lateral movement.

---

### 2. `torch.load(weights_only=False)` in Modal training script - **FIXED** (with caveat)

**Severity**: High (same mechanism, training context)

**Location**: `modal/train_siglip2_multitask.py` (`load_iqa_checkpoint`)

The v2 IQA checkpoint loader used pickle deserialization. Even in a
training context, this is unsafe when checkpoints originate from
shared storage. Applied the same `weights_only=True` fix with a
defensive `isinstance` guard and the same numpy scalar allowlist (inlined,
because the Modal image cannot import the package). The trainer now also
saves plain Python floats for `metrics` and `composite_score`.

**Caveat**: the Modal training images (`modal/train_siglip2_multitask.py`
and four sibling scripts) still pin `torch==2.5.1`, inside the
CVE-2025-32434 range where `weights_only=True` is bypassable. In that runtime
the flag is defense in depth, not a complete mitigation; checkpoints come
from our own trainer on a private Modal volume. Bumping the image pins to
torch>=2.6.0 needs a training smoke test and is listed under follow-up work.

---

### 3. Unvalidated artifact path in Arena `LocalBackend` - **FIXED**

**Severity**: Medium (Path traversal / arbitrary read)

**Location**: `src/image_preprocessing_detector/labeling/arena/inference/local.py:83`

The backend constructed `Path(spec.id)` directly without validating
for traversal patterns. `spec.id` is operator-supplied today, but
nothing prevented a future caller from passing
`../../etc/something` or absolute paths outside the model registry.

**Fix**: Routed the path through `validate_safe_path()` with
`must_exist=True`. Traversal patterns and non-existent paths now
raise `ModelLoadError`.

---

### 4. Unvalidated model path in Arena `RegressionBackend` - **FIXED**

**Severity**: Medium

**Location**: `src/image_preprocessing_detector/labeling/arena/inference/regression.py:161`

Same class of issue as #3, with an additional concern: if the literal
path didn't exist, the code retried under `checkpoints/`, but a
malicious `spec.id` like `../../etc/passwd` could still escape that
prefix.

**Fix**: Validate `spec.id` against traversal patterns up front, and
constrain the `checkpoints/` fallback with
`allowed_base=checkpoints_base` so resolved paths cannot escape.

---

### Already-secure ML loading (verified, no changes needed)

- `torch.load(..., weights_only=True)` at `regression.py:171` - already safe.
- `np.load(...)` calls have no `allow_pickle=True` flag - safe by default.
- ONNX model loading does not invoke pickle.
- HuggingFace `from_pretrained()` / `snapshot_download()` calls use HF Hub.
  Model IDs are hard-coded (not user-supplied), and the Hub client provides
  integrity via standard download caching plus the ability to pin to a
  specific revision/commit. It does **not** perform cryptographic signature
  verification of downloaded artifacts by default
  ([huggingface_hub docs](https://huggingface.co/docs/huggingface_hub/main/en/guides/download)),
  so for stronger guarantees the calls in this repo should be tightened
  to pin a `revision=` argument once we settle on production weights.

---

## API Upload Security

### 5. No magic-byte validation on uploads - **FIXED**

**Severity**: High (extension spoofing → parser exposure)

**Location**: `src/image_preprocessing_detector/api/routes/process.py:51` (and `batch.py`)

The API validated only the file extension and (loosely) the
client-supplied MIME type. A caller could upload an executable, a
zip-bomb, or a malformed PDF/image polyglot under a `.png` name and
the bytes would reach PyMuPDF / OpenCV / PIL - libraries with their
own history of parser CVEs.

**Fix**: Added `src/image_preprocessing_detector/utils/file_validation.py`,
a stdlib-only magic-byte validator covering PDF/PNG/JPEG/TIFF/WebP/BMP.
The process and batch handlers now call `validate_file_content(content, ext)`
after reading bytes and return 400 if the magic bytes do not match the
declared extension. Tests added in
`tests/unit/utils/test_file_validation.py`.

We deliberately did **not** add `python-magic` as a dependency - it
requires the libmagic system library, which would complicate the
Docker image and Modal runtime. The hand-rolled signature table is
sufficient for our supported types.

---

### 6. Full upload buffered before size check - **FIXED**

**Severity**: High (memory exhaustion DoS)

**Location**: `src/image_preprocessing_detector/api/routes/process.py:325` (and `batch.py`)

`content = await file.read()` read the entire upload into memory
before the size check ran. A client lying about Content-Length could
push gigabytes through before being rejected.

**Fix**: Added `read_with_size_limit()` which reads in 1 MB chunks and
aborts as soon as cumulative bytes exceed `max_file_size_mb`. Used by
both the `/process` and `/batch` endpoints.

---

### 7. Batch endpoint has no cumulative size cap - **FIXED**

**Severity**: High (memory exhaustion DoS)

**Location**: `src/image_preprocessing_detector/api/routes/batch.py:240`

Each file in a batch was validated for its individual size cap, but
the endpoint accepted up to `max_batch_size` (default 100) files in
one request. 100 × 50 MB = 5 GB into RAM before processing started.

**Fix**: Added a separate `max_batch_total_size_mb` setting (default
500 MB) and track cumulative `total_bytes` across the batch loop;
the per-file streaming read is also given `extra_byte_limit =
remaining_batch_bytes` so a single file aborts mid-stream the moment
it would push the batch over the cap. The cap is deliberately
**smaller** than `max_batch_size × max_file_size_mb` (which equals
5 GB at defaults - the original worst case) so the new check
actually triggers under abuse, not just at the theoretical maximum.

---

### 8. `validate_file()` `_max_size_mb` parameter ignored - **FIXED**

**Severity**: Medium (latent bug)

The parameter was prefixed `_` and marked "reserved for future use".
Now actually consulted: if `UploadFile.size` advertises a value above
the cap, the request is rejected before any bytes are read.

---

### Path traversal in API temp files - **Verified safe**

`tempfile.NamedTemporaryFile(suffix=Path(filename).suffix)` uses an OS-
generated random basename in the system temp directory. The
user-controlled suffix is appended after that random name, so it
cannot escape the temp directory or land at a predictable location.
Existing `path_security.py` is consistently applied where user paths
do reach the filesystem (`office_processor.py:436`,
`pdf_resolution.py:171`, `text_layer_analyzer.py:160`).

---

## Ingestion Hardening

### 9. PDF loader has no page-count limit - **FIXED**

**Severity**: Medium (CPU/memory exhaustion DoS)

**Location**: `src/image_preprocessing_detector/ingestion/pdf_loader.py:97`

`PDFLoader.load()` iterated every page, rendering each to a pixmap at
300 DPI. A 10 000-page adversarial PDF would tie up a worker for
minutes and consume gigabytes of RAM. The API route had its own
in-handler `if len(page_data) >= 100: break`, but other callers (CLI,
Celery workers, Modal jobs) had no protection.

**Fix**: Added `max_pages` constructor argument with a
`DEFAULT_MAX_PAGES = 500` cap, plus an explicit `allow_truncation`
flag (default `False`). Behaviour is now asymmetric by caller:

- **CLI / Celery / Modal callers** (default `allow_truncation=False`):
  documents exceeding `max_pages` raise `PDFTooManyPagesError` so a
  partial analysis cannot be mistaken for a complete one.
- **API `/process` and `/batch` routes** (opt in via
  `allow_truncation=True` with the route-level
  `max_pdf_pages_per_request` setting, default 100): pages beyond
  the cap are skipped, a `pdf_page_limit_exceeded_truncating`
  warning is logged, and the count is surfaced to the client via
  `ProcessingResult.pages_truncated`. The loader also records the
  truncation state in `last_total_pages` / `last_pages_truncated`
  so callers can detect partial results without re-opening the PDF.

**Limits of this fix** (not covered, tracked as follow-up):

- The cap bounds *rendering* through `PDFLoader` only. `classify_pdf_type`
  (text extraction and image detection) still walks every page of the
  upload, and in the API it runs before the loader, so it is not bounded by
  the page cap. Other direct PyMuPDF callers are likewise uncapped.
- `max_pixels` is per page. There is no cumulative pixel or byte budget
  across pages, so `max_pages` x `max_pixels` is the theoretical worst case.
- The pixel guard runs lazily per page, so pages before an oversized one
  are rendered first.
- The API returns HTTP 200 with a truncated page set, flagged only by
  `pages_truncated`; clients must check that field.
- Defaults are breaking for non-API callers (see `CHANGELOG.md`); `load_pdf()`
  accepts `max_pages`, `max_pixels` and `allow_truncation` overrides, but the
  CLI has no override flag yet.

---

## Metadata Handling

### 15. EXIF DPI extraction lacks bounds checking - **Accepted**

**Location**: `src/image_preprocessing_detector/ingestion/image_loader.py:171`

EXIF tags 282/283 (X/Y resolution) are coerced to `float` with no
range check. A malformed EXIF could supply `1e308` and propagate
through DPI calculations.

Reviewed and accepted as low-risk: PIL's `getexif()` does not execute
EXIF content; values are only used numerically in DPI math whose
worst-case outcome is a bogus `needs_upscaling` flag, not a
vulnerability. No fix applied to avoid breaking legitimate scans with
unusual resolutions.

No EXIF values are interpolated into shell commands, SQL, filenames,
or log strings - verified via repository-wide grep.

---

## Dependency Security

`pyproject.toml`, `uv.lock`, and the exported `requirements*.txt`
files are well-maintained. Highlights:

| Package | Min version | Locked version | Notes |
|---|---|---|---|
| pillow | `>=12.1.1` | 12.1.1 | Snyk CVE fix applied |
| pymupdf | `>=1.27.1` | 1.27.1 | Snyk CVE fix applied |
| torch | `>=2.10.0` | 2.10.0 | Above the `weights_only` requirement |
| torchvision | `>=0.25.0` | 0.25.0 | |
| opencv-python-headless | `>=4.8.0,<5.0.0` | 4.11.0.86 | Above CVE threshold |
| onnxruntime | `>=1.17.0` | 1.23.2 | |
| onnx | (dev) | 1.20.1 | Above CVE-2024-7776 fix |
| fastapi | `>=0.115.0` | 0.128.0 | |
| urllib3 | `>=2.6.3` | 2.6.3 | |
| protobuf | `>=6.33.5` | 6.33.5 | GHSA-7gcm-g887-7qv7 |
| pyasn1 | `>=0.6.2` | 0.6.2 | GHSA-63vm-454h-vhhq |

### 14. `transformers` pin in `iqa` extra - **OPEN**

**Severity**: Low (track upstream)

The `iqa` dependency group resolves `transformers==4.37.2` transitively
through `pyiqa` (it is not a direct pin in `pyproject.toml`; the `labeling`
extra requires `>=4.40.0`, which is why the two are declared as conflicting).
Newer
`transformers` releases have addressed several deserialization issues
in `trust_remote_code` paths. Project code does pass
`trust_remote_code=True` to `AutoProcessor.from_pretrained()` in
`regression.py:191` - this is only invoked for operator-loaded local
checkpoints, so impact is bounded, but bumping to `>=4.48` when the
upstream constraint allows would close the window entirely.

**Recommendation**: Track and bump when other `iqa` dependencies allow.

---

## GitHub Actions Hardening

### 10/11. Unpinned action references - **RESOLVED ON `main`**

`main` pinned these two actions independently in PR #191 ("pin third-party
Actions to commit SHAs"). After merging `main` into this branch, the two
workflow files match `main` exactly and this PR no longer modifies them. The
current pins are:

| File | Line | Pinned to |
|---|---|---|
| `.github/workflows/performance-regression.yml` | 139 | `actions/github-script@f28e40c7f34bde8b3046d885e986cb6290c5673b # v7.1.0` |
| `.github/workflows/security-analysis.yml` | 97, 237, 290 | `astral-sh/setup-uv@d4b2f3b6ecc6e67c4457f6d3e41ec42d3d0fcb86 # v5.4.2` |

This branch's original pins (`@60a0d83... # v7.0.1`, `@e58605a9... # v5`) were
superseded by `main`'s newer SHAs during the merge, so no separate change is
needed here.

Audit confirmed all other third-party `uses:` lines in this repo are pinned to 40-char SHAs.

### 12. Org-reusable workflows tracking `main` - **OPEN**

These reference workflows in repositories outside this audit's scope. After
merging `main`, all three are already pinned to a full 40-character commit
SHA, but each line still carries a trailing `# main` comment and the pin is
a moving snapshot of the shared repository's `main` rather than a reviewed
release:

| File | Line | Reference |
|---|---|---|
| `.github/workflows/coverage.yml` | 26 | `ByronWilliamsCPA/.github/.github/workflows/python-qlty-coverage.yml@c75ea078...` |
| `.github/workflows/container-security.yml` | 40 | `williaby/.github/.github/workflows/python-container-security.yml@c75ea078...` |
| `.github/workflows/slsa-provenance.yml` | 103 | `ByronWilliamsCPA/.github/.github/workflows/python-slsa.yml@c75ea078...` |

`slsa-provenance.yml` produces signed attestations and runs with
`id-token: write`, so the shared repository is part of this repo's trust
base for provenance. A full-SHA pin means a force-push to `main` in the
shared repo cannot silently change what runs here; the residual risk is
stale pins.

**Remaining work**: keep these pins current deliberately (for example via
Dependabot's `github-actions` ecosystem) and replace the 7-character
`@74323d9` pin in `mutation-testing.yml` with the full 40-character SHA.
`release.yml` is already pinned to a full SHA.

### 13. `harden-runner` missing from 13 workflows - **OPEN**

**Severity**: Low (defense-in-depth)

9 workflows already use `step-security/harden-runner` with
`egress-policy: audit`. The remaining 13 do not. Adding it everywhere
would surface unexpected outbound traffic during CI, which is the
intended OpenSSF Scorecard hardening posture.

**Recommendation**: Add the following step (same pin as
`slsa-provenance.yml`) at the top of each missing workflow's main job:

```yaml
- name: Harden runner
  uses: step-security/harden-runner@e14015d583714f6e62063499dc959a02595150a1 # v2.21.1
  with:
    egress-policy: audit
```

Workflows missing it (verify with
`git grep -L harden-runner -- '.github/workflows/*.yml'`):
`benchmark-results.yml`, `container-security.yml`, `coverage.yml`,
`dependency-review.yml`, `docs.yml`, `mutation-testing.yml`,
`performance-regression.yml`, `pr-validation.yml`,
`python-compatibility.yml`, `release.yml`, `reuse.yml`, `sbom.yml`,
`sonarcloud.yml`.

Not fixed in this PR because adding a step to 13 unrelated workflows
introduces broad CI surface area better validated incrementally.

### Other workflow checks - **Verified clean**

- **Permissions blocks**: every workflow has a top-level `permissions:`
  block; no `write-all` granted; broad permissions consistently
  scoped to a single job rather than workflow-wide.
- **`pull_request_target`**: not used anywhere - every PR-triggered
  workflow uses safe `pull_request`.
- **Script injection**: no `${{ github.event.*.title|.body|.head.ref|.comment.body }}`
  interpolated into `run:` shells. Where `github.event.inputs.*` is
  used (`fips-compatibility.yml`), it's passed through env vars, not
  shell-interpolated.
- **`curl | bash` patterns**: none.
- **Pip installs from unverified sources**: `cyclonedx-bom==4.6.1` and
  `twine==6.2.0` are version-pinned in workflow `pip install` calls;
  no arbitrary URLs.
- **External model downloads in CI**: none - benchmarks and training
  do not run in GitHub Actions.

---

## Verification

To reproduce the fixes locally:

```bash
# Unit tests for the new magic-byte validator
PYTHONPATH=src python -m pytest tests/unit/utils/test_file_validation.py -v

# Round-trip a trainer-style checkpoint and confirm a malicious pickle is rejected
uv run --extra dev python -m pytest tests/unit/utils/test_safe_checkpoint.py \
  tests/unit/detection/test_siglip2_multitask.py --override-ini="addopts=" -q

# API regression tests need the api extra, and cv2 must be imported before the
# first request, so run them after another module that imports it
uv run --extra dev --extra api python -m pytest tests/unit/test_image_loader.py \
  tests/api --override-ini="addopts=" -q

# Confirm no executable torch.load(weights_only=False) in src/ or modal/
grep -rn "weights_only=False" src/ modal/
# Expect: comment and docstring mentions only (safe_checkpoint.py,
# siglip2_multitask.py). scripts/run_model_benchmark.py still uses
# weights_only=False; see follow-up work.
```

---

## Follow-up Work (outside this PR's scope)

1. Pin the three org-reusable workflows (finding 12) - requires a
   commit SHA selection in `ByronWilliamsCPA/.github` and
   `williaby/.github`.
2. Roll `harden-runner` out to the remaining 13 workflows (finding
   13).
3. Bump the `iqa` extra's `transformers` pin when upstream `iqa`
   dependencies allow `>=4.48` (finding 14).
4. Bump the `torch==2.5.1` pins in the Modal training images
   (`modal/train_siglip2_multitask.py`, `train_siglip2_iqa.py`,
   `train_siglip2_iqa_v2.py`, `train_skew_estimator.py`,
   `extract_siglip2_diqa5000.py`) to torch>=2.6.0 after a training smoke test
   (finding 2), and replace `weights_only=False` in
   `scripts/run_model_benchmark.py`.
5. Bound PDF classification and add a cumulative pixel budget (finding 9
   limits), and add a CLI override for the PDF page and pixel caps.
6. Consider migrating any new ML checkpoints to safetensors format - even with `weights_only=True`, safetensors gives a stricter
   parser and explicit metadata separation.
