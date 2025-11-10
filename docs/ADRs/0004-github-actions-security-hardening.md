---
schema_type: common
title: "ADR-004: GitHub Actions Security Hardening"
description: "Decision to implement least-privilege permissions and eliminate download-then-run
  patterns in workflows"
tags:
- adr
- security
- ci_cd
- github_actions
- openssf
status: published
owner: "core-maintainer"
authors:
- name: "Byron Williams"
purpose: "Document the decision to harden GitHub Actions workflows following OpenSSF
  Scorecard recommendations."
---


**Status**: ✅ **Accepted**
**Date**: 2025-01-08
**Deciders**: Byron Williams
**Related**: Sprint 1 - Workflow Security Hardening, OpenSSF Scorecard Compliance

## Context

OpenSSF Scorecard identified security issues in GitHub Actions workflows:

### Identified Vulnerabilities

1. **Overly Permissive Tokens**: Workflows had `permissions: write-all` or no explicit permissions
   - Risk: Compromised workflow can modify code, publish releases, access secrets
   - Impact: Supply chain attack vector

2. **Download-Then-Run Patterns**: 7 instances of `curl | python` for Poetry installation
   ```yaml
   curl -sSL https://install.python-poetry.org | python3 -
   ```
   - Risk: MITM attack could inject malicious code
   - Impact: Build-time code execution vulnerability

3. **Missing Action SHA Pinning**: Some actions pinned by tag instead of SHA
   - Risk: Tag can be moved to malicious commit
   - Impact: Workflow compromise

### OpenSSF Scorecard Score

- **Before**: Token-Permissions: 0/10, Dangerous-Workflow: 3/10
- **Target**: Token-Permissions: 10/10, Dangerous-Workflow: 10/10
- **Impact**: Overall score improvement: ~6.8 → ~8.5 (+1.7 points)

## Decision

**Implement comprehensive security hardening across all 9 GitHub Actions workflows.**

### Changes

1. **Least-Privilege Token Permissions**
   - Top-level: `permissions: read-all` (default deny)
   - Job-level: Grant write permissions only where needed

   ```yaml
   permissions: read-all  # Top-level default

   jobs:
     security-scan:
       permissions:
         security-events: write  # Only for SARIF upload
         contents: read
   ```

2. **Eliminate Download-Then-Run Patterns**
   - Replace `curl | python` with trusted GitHub Actions
   - Use SHA-pinned `snok/install-poetry@76e04a911780d5b312d89783f7b1cd627778900a` (v1.4.1)
   - Add `POETRY_VERSION: 2.1.2` environment variable for consistency

3. **Complete SHA Pinning**
   - All actions pinned by commit SHA with version comment
   - Example: `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2`

### Affected Workflows

| Workflow | Permissions | Poetry Pattern | Impact |
|----------|-------------|----------------|--------|
| ci.yml | ✅ Fixed (3 locations) | ✅ Replaced | High |
| codecov.yml | ✅ Fixed | N/A | Medium |
| security-analysis.yml | ✅ Fixed (3 locations) | ✅ Replaced | High |
| scorecard.yml | ✅ Already compliant | N/A | Low |
| cifuzzy.yml | ✅ Fixed | N/A | Medium |
| pr-validation.yml | ✅ Fixed (1 location) | ✅ Replaced | Medium |
| reuse.yml | ✅ Fixed | N/A | Low |
| docs.yml | ✅ Fixed | N/A | Medium |
| sbom.yml | ✅ Fixed | N/A | Medium |

## Consequences

### Positive

1. **Reduced Attack Surface**: Least-privilege tokens limit blast radius
2. **Supply Chain Security**: SHA pinning prevents action hijacking
3. **MITM Protection**: Eliminated download-then-run vulnerabilities
4. **OpenSSF Compliance**: Improved Scorecard score (+1.7 points)
5. **Audit Trail**: Explicit permissions document workflow requirements
6. **Best Practices**: Aligns with GitHub security recommendations

### Negative

1. **Maintenance Overhead**: Must update SHA pins when updating actions
   - Mitigation: Renovate automates SHA pin updates
2. **Verbosity**: More explicit permissions configuration
   - Acceptable: Security over brevity
3. **Migration Effort**: All 9 workflows required updates
   - One-time cost: Completed in Sprint 1

### Neutral

1. **Functional Equivalence**: No behavior changes, only security improvements
2. **Python Version Update**: Updated MyPy from 3.11 to 3.12 (housekeeping)

## Implementation Details

### Token Permission Patterns

**Read-Only Jobs** (most common):
```yaml
permissions: read-all  # Top-level covers all read-only jobs
```

**SARIF Upload** (CodeQL, Scorecard, Trivy):
```yaml
permissions:
  contents: read
  security-events: write  # Required for GitHub Security tab
```

**PR Comments** (Codecov, Dependency Review):
```yaml
permissions:
  contents: read
  pull-requests: write   # Required for PR comments
  statuses: write        # Required for commit status
```

**GitHub Pages Deployment**:
```yaml
permissions:
  contents: write  # Required for gh-pages branch update
```

### Poetry Installation Pattern

**Before (Unsafe)**:
```yaml
- name: Install Poetry
  run: curl -sSL https://install.python-poetry.org | python3 -
```

**After (Secure)**:
```yaml
env:
  POETRY_VERSION: 2.1.2

- name: Install Poetry
  uses: snok/install-poetry@76e04a911780d5b312d89783f7b1cd627778900a # v1.4.1
  with:
    version: ${{ env.POETRY_VERSION }}
    virtualenvs-create: true
    virtualenvs-in-project: true
```

## Alternatives Considered

### Alternative 1: Checksum Verification
```yaml
run: |
  curl -fsSL -o install-poetry.py https://install.python-poetry.org
  echo "EXPECTED_SHA256  install-poetry.py" | sha256sum -c -
  python3 install-poetry.py
```
**Rejected**: More complex, harder to maintain, still network-dependent

### Alternative 2: Keep Permissive Tokens
**Rejected**: Violates principle of least privilege, fails OpenSSF checks

### Alternative 3: Mix of Patterns
**Rejected**: Inconsistent security posture across workflows

## Monitoring

### OpenSSF Scorecard Checks

- **Token-Permissions**: 0/10 → 10/10 ✅
- **Dangerous-Workflow**: 3/10 → 10/10 ✅
- **Pinned-Dependencies**: Maintained 10/10 ✅

### Ongoing Maintenance

- **Renovate**: Automated SHA pin updates
- **Monthly Review**: Verify no new unsafe patterns introduced
- **Security Alerts**: GitHub Dependabot for vulnerable actions

## Files Modified

- `.github/workflows/ci.yml`: Permissions + 3 Poetry replacements
- `.github/workflows/codecov.yml`: Permissions
- `.github/workflows/security-analysis.yml`: Permissions + 3 Poetry replacements
- `.github/workflows/scorecard.yml`: Already compliant
- `.github/workflows/cifuzzy.yml`: Permissions
- `.github/workflows/pr-validation.yml`: Permissions + 1 Poetry replacement + Python 3.11→3.12
- `.github/workflows/reuse.yml`: Permissions
- `.github/workflows/docs.yml`: Permissions
- `.github/workflows/sbom.yml`: Permissions

## References

- [OpenSSF Scorecard - Token Permissions](https://github.com/ossf/scorecard/blob/main/docs/checks.md#token-permissions)
- [OpenSSF Scorecard - Dangerous Workflow](https://github.com/ossf/scorecard/blob/main/docs/checks.md#dangerous-workflow)
- [GitHub Actions Security Best Practices](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- [snok/install-poetry Action](https://github.com/snok/install-poetry)
- [Workflow Security Audit](../../tmp_cleanup/.tmp-workflow-security-audit-20250108.md)
- [Commit: d21278c](https://github.com/williaby/image-preprocessing-detector/commit/d21278c)
