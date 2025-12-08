# Org Workflows Not Currently Used

> **Analysis Date**: 2025-12-07
> **Org Repos**: ByronWilliamsCPA/.github, williaby/.github
> **Available Workflows**: 14 + python-fuzzing.yml (williaby) + python-performance-regression.yml (williaby)

## 📊 Available vs Used

### Org Workflows Available (16 total)

**ByronWilliamsCPA/.github**:

1. python-ci.yml
2. python-codecov.yml
3. python-compatibility.yml
4. python-container-security.yml
5. python-docs.yml
6. python-mutation.yml
7. python-pr-validation.yml
8. python-publish-pypi.yml
9. python-release.yml
10. python-reuse.yml
11. python-sbom.yml
12. python-scorecard.yml
13. python-security-analysis.yml
14. python-slsa.yml

**williaby/.github** (additional):
15. python-fuzzing.yml ⭐
16. python-performance-regression.yml ⭐

---

## ✅ Currently Using (10 of 16 = 63%)

| Org Workflow | Used Via | Status |
|--------------|----------|--------|
| `python-ci.yml` | pr-checks.yml, weekly-comprehensive.yml | ✅ Using |
| `python-pr-validation.yml` | pr-checks.yml | ✅ Using |
| `python-reuse.yml` | pr-checks.yml | ✅ Using |
| `python-security-analysis.yml` | weekly-comprehensive.yml | ✅ Using |
| `python-scorecard.yml` | weekly-comprehensive.yml | ✅ Using |
| `python-sbom.yml` | weekly-comprehensive.yml | ✅ Using |
| `python-fuzzing.yml` | fuzzing-weekly.yml | ✅ Using |
| `python-performance-regression.yml` | performance-caller.yml | ✅ Using |
| `python-mutation.yml` | mutation-testing.yml | ✅ Using |
| `python-release.yml` | release.yml | ✅ Using |
| `python-docs.yml` | docs-caller.yml | ✅ Using (new) |
| `python-publish-pypi.yml` | pypi-publish-caller.yml | ✅ Using (new) |

---

## ❌ Not Currently Using (4 of 16 = 25%)

### 1. python-codecov.yml

**Status**: ❌ Not using as standalone
**Reason**: Already included in `python-ci.yml` workflow

**Analysis**:

- Coverage uploading handled by python-ci.yml
- No need for separate workflow
- **Action**: ✅ Correct to not use separately

---

### 2. python-container-security.yml

**Status**: ❌ Not using
**Reason**: This project doesn't use Docker containers yet

**Org Workflow Purpose**:

- Trivy container image scanning
- Hadolint Dockerfile linting
- Container security best practices

**Should You Use?**:

- **Not yet** - No Dockerfiles in this repo currently
- **Future**: When Phase 5 Docker deployment is implemented
- **Action**: ⏭️ Skip for now, add when deploying containers

---

### 3. python-slsa.yml

**Status**: ❌ Not using
**Reason**: SLSA provenance for supply chain security

**Org Workflow Purpose**:

- SLSA Level 3 provenance generation
- Supply chain attestations
- Build reproducibility

**Should You Use?**:

- **Optional** - SLSA is advanced supply chain security
- **Benefit**: Enhanced security for published packages
- **When**: Once publishing to PyPI
- **Action**: ⏭️ Add when ready to publish

**Implementation** (when ready):

```yaml
# Add to pypi-publish-caller.yml or as separate workflow
jobs:
  slsa:
    uses: ByronWilliamsCPA/.github/.github/workflows/python-slsa.yml@main
    permissions:
      id-token: write
      contents: write
      actions: read
```

---

### 4. python-compatibility.yml (Different Usage)

**Status**: ⚠️ Using differently
**Current**: Embedded in weekly-comprehensive.yml via python-ci.yml calls
**Alternative**: Could call python-compatibility.yml directly

**Analysis**:

- Currently: 5 separate python-ci.yml calls (one per Python version)
- Alternative: 1 python-compatibility.yml call with matrix

**Comparison**:

**Current Approach** (what you're doing):

```yaml
# weekly-comprehensive.yml
jobs:
  test-python-310:
    uses: .../python-ci.yml@main
    with:
      python-version: '3.10'

  test-python-311:
    uses: .../python-ci.yml@main
    with:
      python-version: '3.11'
  # ... 3 more calls
```

**Alternative Approach** (simpler):

```yaml
# weekly-comprehensive.yml
jobs:
  compatibility:
    uses: .../python-compatibility.yml@main
    with:
      python-versions: '["3.10", "3.11", "3.12", "3.13", "3.14"]'
      coverage-threshold: 80
```

**Pros of Alternative**:

- Fewer lines in caller workflow
- Single job handles multi-version testing
- Easier to maintain

**Cons of Alternative**:

- Less granular control per version
- All versions in one job (can't see individual results easily)

**Recommendation**: ⚠️ Consider switching to python-compatibility.yml for cleaner code

---

## 📋 Summary

### Workflows You Should Add

1. ⏭️ **python-slsa.yml** (when publishing to PyPI)
   - Supply chain security
   - SLSA Level 3 provenance
   - Add with PyPI publishing

2. ⏭️ **python-container-security.yml** (when deploying with Docker)
   - Trivy image scanning
   - Hadolint Dockerfile linting
   - Add in Phase 5 deployment

### Workflows Correctly Not Using

1. ✅ **python-codecov.yml** (already in python-ci.yml)

### Workflows to Consider Using Differently

1. ⚠️ **python-compatibility.yml** (could simplify weekly-comprehensive.yml)
   - Current: 5 separate python-ci.yml calls
   - Alternative: 1 python-compatibility.yml call with matrix
   - **Trade-off**: Simplicity vs granular control

---

## 🎯 Recommended Actions

### Immediate (No Action Needed)

- ✅ Using 10 of 14 applicable workflows (71%)
- ✅ 2 workflows not applicable yet (containers, SLSA)
- ✅ Excellent org workflow adoption

### Future (When Applicable)

- [ ] Add python-slsa.yml when publishing to PyPI
- [ ] Add python-container-security.yml when deploying with Docker

### Optional Optimization

- [ ] Consider replacing 5 python-ci.yml calls with 1 python-compatibility.yml call
  - Pros: Simpler, fewer lines
  - Cons: Less granular control
  - **Decision**: Your choice based on preference

---

## 📈 Org Workflow Usage Statistics

**Total Available**: 16 workflows (14 ByronWilliamsCPA + 2 williaby)
**Currently Using**: 12 (75%)
**Not Using**: 4

- 2 correctly not using (codecov, not applicable)
- 2 will use in future (slsa, container-security)

**Verdict**: ✅ **Excellent adoption rate!**

---

## 💡 Final Recommendations

### For This Repo

1. ✅ Current usage is excellent (75% adoption)
2. ✅ Missing workflows not applicable yet
3. ⚠️ Consider python-compatibility.yml for simpler weekly-comprehensive.yml (optional)
4. ⏭️ Add python-slsa.yml when publishing
5. ⏭️ Add python-container-security.yml in Phase 5

### For .github Team

1. See [ORG_WORKFLOW_ENHANCEMENT_RECOMMENDATIONS.md](ORG_WORKFLOW_ENHANCEMENT_RECOMMENDATIONS.md)
2. Priority enhancements: Draft PR awareness, tiered testing, concurrency groups
3. Expected org-wide impact: $15-25/month savings

---

**Conclusion**: You're using nearly all applicable org workflows! Only missing ones are for features not yet implemented (containers, PyPI publishing, SLSA provenance).
