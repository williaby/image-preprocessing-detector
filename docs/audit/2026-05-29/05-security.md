# Security & Secrets Audit (2026-05-29)

Read-only audit. No live secrets found in tracked code. Main real risks: a transitively pinned old `transformers 4.37.2` (known RCE CVEs) and broad use of `trust_remote_code=True` / `torch.load(weights_only=False)` on model loading paths. Several scanner tools (bandit, safety, osv-scanner, snyk) were not runnable offline; findings rely on config and lockfile inspection plus grep.

## Findings

### SEC-01 - Vulnerable `transformers 4.37.2` resolved transitively (known RCE/ReDoS CVEs)
- Severity: High
- Effort: M
- Affected: `uv.lock` (lines ~7661, ~10700-10743), pulled by `pyiqa 0.1.14.1`
- Evidence: lockfile pins two `transformers` versions: `4.57.3` (project, requires `>=4.40.0`) and `4.37.2` (forced by `pyiqa 0.1.14.1` dependency). The `4.37.2` node resolves under markers `python_full_version >= '3.12'` on darwin / linux-aarch64 / win32. transformers `<4.48` is affected by deserialization and ReDoS RCE issues fixed upstream in the 4.48 line.
- Recommendation: Confirm whether the `iqa` extra (pyiqa) is shipped in any runtime image; if so, pin `pyiqa` to a release that allows `transformers>=4.48`, or constrain `transformers>=4.48` and drop pyiqa from production extras. If `iqa` is dev/labeling-only, document it as not production-reachable.
- cve: CVE-2024-11392 / CVE-2024-11393 / CVE-2024-11394 (transformers <4.48; verify exact IDs against the resolved 4.37.2 surface)

### SEC-02 - `trust_remote_code=True` on model loads
- Severity: Medium
- Effort: M
- Affected: `src/image_preprocessing_detector/labeling/arena/inference/regression.py:189,209,215`, `.../annotation/enrichment/providers/siglip.py:278,282`, plus 17 total occurrences across `src/`, `scripts/`, `modal/`
- Evidence: `AutoProcessor.from_pretrained(model_path, trust_remote_code=True)` and `AutoModel.from_pretrained(spec.id, revision=spec.revision, trust_remote_code=True)`. `spec.id` / `model_path` are caller-supplied. `trust_remote_code=True` executes arbitrary Python shipped with the model repo; if a model id/path is ever attacker-influenced, this is RCE.
- Recommendation: Set `trust_remote_code=False` for first-party checkpoints; gate `True` behind an allowlist of known model ids and pin `revision` to a full commit SHA (already partly done via `revision=spec.revision`).

### SEC-03 - `torch.load(weights_only=False)` on checkpoint load
- Severity: Medium
- Effort: S
- Affected: `src/image_preprocessing_detector/detection/siglip2_multitask.py:236-239`, `scripts/run_model_benchmark.py:331,542,825,931`, `modal/train_siglip2_multitask.py:494`
- Evidence: `torch.load(self.checkpoint_path, map_location=..., weights_only=False)`. `weights_only=False` unpickles arbitrary objects; loading an untrusted checkpoint is code execution. `checkpoint_path` is config-driven. Note `labeling/arena/inference/regression.py:171` and `scripts/checkpoint_manager.py:231` already use `weights_only=True` or document trust (`# nosec B614`), so the codebase is inconsistent.
- Recommendation: Use `weights_only=True` where the checkpoint is a plain state_dict (the siglip2 path calls `ckpt.get("model_state_dict", ckpt)`, so a wrapped dict may still need full load - prefer `safetensors` for these). Document the trust boundary inline for the remaining `weights_only=False` calls.

### SEC-04 - Expired `.snyk` ignore for ONNX CVE-2025-51480
- Severity: Low
- Effort: S
- Affected: `.snyk` (SNYK-PYTHON-ONNX-10877916 block), `onnx 1.20.1` in `uv.lock`
- Evidence: ignore `expires: '2025-02-22T00:00:00.000Z'` - expired ~3 months before audit date (2026-05-29). The justification (inference-only, `save_external_data` unused) is reasonable, but the expiry has lapsed so Snyk will now re-flag it.
- Recommendation: Re-review and re-date the ignore (or remove if a fixed onnx is available). Verify `save_external_data` is still unused.
- cve: CVE-2025-51480

### SEC-05 - API upload buffers full body before size check
- Severity: Low
- Effort: M
- Affected: `src/image_preprocessing_detector/api/routes/process.py:323-341`
- Evidence: `content = await file.read()` reads the entire upload into memory, then `file_size_mb > settings.max_file_size_mb` is checked afterward. `validate_file()` receives `_max_size_mb` but ignores it ("reserved for future use"). A large upload is fully buffered before rejection - memory-exhaustion DoS surface. MIME-type mismatch is only logged, not rejected (extension allowlist still applies).
- Recommendation: Enforce a streaming/Content-Length size cap before reading the body (reject early on `Content-Length`), and stream to the temp file in bounded chunks rather than reading all bytes into memory.

### SEC-06 - API key check is not constant-time
- Severity: Low
- Effort: S
- Affected: `src/image_preprocessing_detector/api/middleware.py:257` (`if api_key not in self.api_keys`)
- Evidence: set-membership comparison of the provided key against valid keys is not timing-safe; theoretical timing side-channel on key validation.
- Recommendation: Compare with `hmac.compare_digest` against hashed candidates, or accept as low-risk defense-in-depth given keys are high-entropy and behind TLS.

## Clean areas
- No hardcoded live secrets in tracked `src/`, `scripts/`, `modal/`, `configs/`; matches are env-sourced (`os.environ`/`getenv`), schema fields, or labeled test fixtures.
- `.env` is untracked and gitignored; `.env.example` contains only placeholders (`your-gcp-project-id`, `your-huggingface-token-here`).
- Only secret-like literals are intentional CodeQL/test fixtures in `tests/security/test_codeql_validation.py` (with `# nosec`), correctly ignored in `.gitguardian.yaml`.
- GitHub Actions: all third-party actions SHA-pinned; every workflow declares top-level `permissions:`; `write`/`id-token: write` scoped to release/publish/pages jobs with justification; no `pull_request_target`; `workflow_run` consumers (codecov/coverage/qlty/slsa) gate on `conclusion == 'success'` and download artifacts (no untrusted-head checkout-and-run). Untrusted `github.event.*` values used only in concurrency keys and via env var (`PR_BASE_REF`), not inline in `run:`.
- No `shell=True`, `os.system`, `eval`/`exec`, or unsafe `yaml.load` in `src/`/`scripts/`/`modal/`.
- `except: pass` blocks (19) are narrowly typed (ValueError / ImportError / JSONDecodeError); no broad bare-except swallowing of critical failures in pipeline hot paths.
- Upload temp files use `tempfile.NamedTemporaryFile` (random name, only `.suffix` taken from user filename) - no path traversal.

## Tooling limitation
`bandit`, `safety`, `osv-scanner`, and `snyk` were not executable in this offline sandbox (`bandit` not installed; network scanners would fail). Dependency-CVE findings here come from `uv.lock` inspection; re-run `osv-scanner --lockfile=uv.lock` and `bandit -r src -ll` in CI to confirm SEC-01/SEC-04.
