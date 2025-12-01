# GitHub Actions Workflows

This project uses a **hybrid approach** combining org-level reusable workflows with project-specific custom implementations.

## Architecture

```
┌─────────────────────────────────────────┐
│  image_detection        │
│  (This Repository)                      │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │ Caller Workflows (.github/        │ │
│  │ workflows/*.yml)                   │ │
│  │                                    │ │
│  │ • compatibility.yml                │ │
│  │ • mutation-testing.yml             │ │
│  │ • release.yml                      │ │
│  └───────────────────────────────────┘ │
│              │                          │
│              │ uses:                    │
│              ▼                          │
└─────────────────────────────────────────┘
               │
               │
┌──────────────▼──────────────────────────┐
│  ByronWilliamsCPA  │
│  /.github Repository                    │
│  (Organization-Level)                   │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │ Reusable Workflows (.github/      │ │
│  │ workflows/*.yml)                   │ │
│  │                                    │ │
│  │ • python-compatibility.yml         │ │
│  │ • python-mutation.yml              │ │
│  │ • python-release.yml               │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  Custom Workflows                       │
│  (Project-Specific)                     │
│                                         │
│  • ci.yml (CV dependencies)            │
│  • security-analysis.yml (image sec)   │
│  • docs.yml (validation)               │
│  • benchmark-results.yml               │
│  • qlty.yml                            │
│  • codecov.yml                         │
└─────────────────────────────────────────┘
```

## Workflow Descriptions

### Org-Level Reusable Workflows

#### Multi-Version Compatibility (`compatibility.yml`)

**Calls**: `ByronWilliamsCPA/.github/.github/workflows/python-compatibility.yml@main`

Multi-version Python testing (3.10-3.14):

- Matrix testing across Python versions
- Pre-release support (Python 3.14)
- Configurable OS matrix
- Failure tolerance for experimental versions

**Triggers**: PR, push to main/develop

---

#### Mutation Testing (`mutation-testing.yml`)

**Calls**: `ByronWilliamsCPA/.github/.github/workflows/python-mutation.yml@main`

Advanced mutation testing with mutmut:

- 80% mutation score threshold
- HTML report generation
- PR comment posting
- Configurable timeout (120min for CV code)

**Triggers**: Weekly schedule (Sunday 2am), manual dispatch

---

#### Semantic Release (`release.yml`)

**Calls**: `ByronWilliamsCPA/.github/.github/workflows/python-release.yml@main`

Automated release with semantic versioning:

- Auto version bumping (Conventional Commits)
- Auto-generated changelog
- SLSA provenance generation
- PyPI publishing with OIDC
- Force release options (patch/minor/major)

**Triggers**: Push to main, manual dispatch

---

### Custom Project-Specific Workflows

#### CI Pipeline (`ci.yml`)

**Custom implementation with image processing focus**

Comprehensive CI with CV/ML dependencies:

- Python 3.10-3.14 multi-version testing
- OpenCV, PyMuPDF, PyTorch installation
- Disk space management for CV libraries
- LLM governance (assumption tag verification)
- Ruff linting, BasedPyright type checking
- 80%+ test coverage enforcement

**Why Custom**: CV/ML dependencies require specialized setup not in org-level workflows

**Triggers**: PR, push to main/develop

---

#### Security Analysis (`security-analysis.yml`)

**Custom implementation with image processing security**

Comprehensive security scanning:

- CodeQL with CV-specific queries
- Image processing security validation
- PDF path traversal protection
- Memory limit checks for large images
- Bandit, Safety, OSV Scanner
- Dependency review

**Why Custom**: Image/PDF file handling requires project-specific security checks

**Triggers**: PR, push to main/develop, weekly schedule

---

#### Documentation (`docs.yml`)

**Custom implementation with advanced validation**

Documentation build and quality gates:

- Front matter validation + autofix
- Link checking with Lychee
- Docstring quality enforcement
- MkDocs build with Material theme
- GitHub Pages deployment

**Why Custom**: More comprehensive validation than org-level workflow

**Triggers**: Push/PR affecting docs, manual dispatch

---

#### Benchmark Results Auto-Update (`benchmark-results.yml`)

**Project-specific automation**

Updates README from committed benchmark results:

- Detects new benchmark results in reports/
- Updates benchmarks/README.md
- Generates status badges
- Auto-commits changes with [skip ci]

**Why Custom**: Project-specific benchmark automation

**Triggers**: Push benchmark results to reports/, manual dispatch

---

#### Qlty Coverage Upload (`qlty.yml`)

**Project-specific integration**

Dedicated Qlty code quality platform integration:

- Downloads coverage from CI artifacts
- Uploads lcov.info to Qlty
- Workflow_run trigger (security best practice)

**Why Custom**: Modern code quality platform integration

**Triggers**: After CI completes successfully

---

#### Codecov Upload (`codecov.yml`)

**Secure coverage upload pattern**

Dedicated Codecov coverage upload:

- Downloads coverage from CI artifacts
- Workflow_run trigger (prevents pwn requests)
- Graceful failure handling

**Why Custom**: Secure upload pattern, separate from CI

**Triggers**: After CI completes successfully

---

### Standard Workflows (Shared Implementation)

- **PR Validation** (`pr-validation.yml`): Dependency and standards validation
- **SBOM** (`sbom.yml`): Software bill of materials generation
- **OpenSSF Scorecard** (`scorecard.yml`): Supply chain security assessment
- **REUSE** (`reuse.yml`): License compliance checking
- **CIFuzzy** (`cifuzzy.yml`): Fuzzing with ClusterFuzzLite
- **SonarCloud** (`sonarcloud.yml`): Code quality analysis

---

## Why Hybrid Approach?

### Benefits of Org-Level Reusable Workflows

✅ **Consistency**: Standard workflows across all org projects
✅ **Maintainability**: Update once at org level, all projects benefit
✅ **Best Practices**: LLM governance, semantic versioning, SLSA provenance
✅ **Reduced Duplication**: Caller workflows are ~50 lines vs ~300+ custom

### Why Some Workflows Stay Custom

❌ **Computer Vision Dependencies**: OpenCV, PyTorch, PyMuPDF require specialized setup
❌ **Image Processing Security**: PDF/image file handling needs project-specific validation
❌ **Advanced Validation**: Docs workflow has better quality gates than org-level
❌ **Project-Specific Features**: Benchmark automation, unique integrations

---

## Configuration

Caller workflows are configured via `with:` parameters. Examples:

### Compatibility Testing

```yaml
uses: ByronWilliamsCPA/.github/.github/workflows/python-compatibility.yml@main
with:
  python-versions: '["3.10", "3.11", "3.12", "3.13", "3.14"]'
  allow-prereleases: true  # For Python 3.14 experimental
  coverage-threshold: 80
```

### Mutation Testing

```yaml
uses: ByronWilliamsCPA/.github/.github/workflows/python-mutation.yml@main
with:
  source-directory: 'src'
  mutation-threshold: 80
  fail-under-threshold: false  # Warn but don't block
  timeout-minutes: 120  # CV testing may be slower
```

### Semantic Release

```yaml
uses: ByronWilliamsCPA/.github/.github/workflows/python-release.yml@main
with:
  semantic-release: true
  publish-to-pypi: true
  pypi-package-name: 'image-preprocessing-detector'
```

---

## Workflow Decision Matrix

| Need | Use Org-Level | Use Custom | Reason |
|------|---------------|------------|--------|
| Multi-version testing | ✅ python-compatibility.yml | ❌ | Dedicated reusable workflow |
| CV/ML dependencies | ❌ | ✅ ci.yml | Requires OpenCV, PyTorch setup |
| Image processing security | ❌ | ✅ security-analysis.yml | PDF/image file validation |
| Mutation testing | ✅ python-mutation.yml | ❌ | Standard with good features |
| Semantic versioning | ✅ python-release.yml | ❌ | Auto versioning + SLSA |
| Advanced docs validation | ❌ | ✅ docs.yml | Better quality gates |
| Benchmark automation | ❌ | ✅ benchmark-results.yml | Project-specific |

---

## Local Development

Test workflows locally using [act](https://github.com/nektos/act):

```bash
# Test CI workflow
act -j setup-optimized

# Test specific workflow with event
act pull_request -j compatibility

# List all jobs
act -l
```

**Note**: Some workflows (compatibility, mutation, release) call org-level reusable workflows which `act` may not fully support.

---

## Troubleshooting

### Workflow Fails to Find Reusable Workflow

**Error**: `Workflow file not found`

**Solution**: Ensure org-level `.github` repository exists at:

```
ByronWilliamsCPA/.github/.github/workflows/*.yml
```

### Reusable Workflow Missing Features

**Issue**: Org-level workflow doesn't support CV dependencies

**Solution**: Keep custom workflow. This is expected - image processing requires specialized setup.

### Permission Denied

**Error**: `Resource not accessible by integration`

**Solution**: Check `permissions:` in workflow. Caller workflows may need:

```yaml
permissions:
  contents: write  # For releases
  pull-requests: write  # For PR comments
  id-token: write  # For OIDC/SLSA
```

---

## Documentation

- [GitHub Reusable Workflows Docs](https://docs.github.com/en/actions/using-workflows/reusing-workflows)
- [Org-Level Workflow Source](https://github.com/ByronWilliamsCPA/.github/tree/main/.github/workflows)
- [Project Contributing Guide](../../CONTRIBUTING.md)
- [Comparison Report](../../tmp_cleanup/.tmp-orgworkflows-comparison-20251130.md)

---

**Last Updated**: 2025-11-30
**Org Workflows Version**: `@main` (tracks latest org updates)
**Architecture**: Hybrid (org-level + custom)
