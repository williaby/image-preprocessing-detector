---
schema_type: common
title: "License Policy Exceptions"
tags:
  - security
  - compliance
  - licensing
status: published
owner: docs-team
purpose: Documents approved license exceptions for development dependencies.
---

## Overview

This project follows a strict **GPL-free license policy** for distributed dependencies. However, certain **development-only dependencies** are allowed to have GPL licenses because they are not distributed with the MIT-licensed package.

**Policy**: `deny-licenses: GPL-2.0, GPL-3.0` (configured in [.github/workflows/security-analysis.yml](../../.github/workflows/security-analysis.yml))

## Approved Exceptions

The following packages have GPL or unknown licenses but are approved for use because they are **development-only dependencies** (not included in the distributed package):

### 1. grandalf (GPL-3.0-or-later)

- **Package**: `grandalf@0.8`
- **License**: GPL-3.0-or-later
- **Source**: Transitive dependency of `dvc`
- **Purpose**: DVC pipeline DAG visualization
- **Justification**:
  - Development-only dependency (dataset versioning tool)
  - Not imported in production code
  - Not distributed with MIT-licensed package
  - Only used via CLI (`poetry run dvc`)
- **Risk**: None (isolated to development environment)
- **Approved By**: Security team
- **Date**: 2025-11-16

### 2. text-unidecode (Dual-Licensed)

- **Package**: `text-unidecode@1.3`
- **License**: Artistic-1.0-Perl OR GPL-1.0-only OR GPL-2.0-or-later
- **Source**: Transitive dependency of `dvc` (via `python-slugify`)
- **Purpose**: Unicode text normalization for slug generation
- **Justification**:
  - Dual-licensed with **Artistic-1.0-Perl** as acceptable alternative
  - Development-only dependency
  - Not distributed with package
- **Risk**: None (acceptable license alternative available)
- **Approved By**: Security team
- **Date**: 2025-11-16

### 3. billiard (License Not Detected)

- **Package**: `billiard@4.2.3`
- **License**: Not detected by dependency scanner
- **Actual License**: BSD (verified at https://github.com/celery/billiard/blob/master/LICENSE.txt)
- **Source**: Transitive dependency of `dvc` (via `celery`)
- **Purpose**: Multiprocessing library for Celery task queue
- **Justification**:
  - BSD-3-Clause licensed (GPL-free)
  - Scanner failed to detect license file
  - Development-only dependency
- **Risk**: None (verified BSD license)
- **Approved By**: Security team
- **Date**: 2025-11-16

### 4. dulwich (Dual-Licensed)

- **Package**: `dulwich@0.24.10`
- **License**: Apache-2.0 OR GPL-2.0-or-later
- **Source**: Transitive dependency of `dvc`
- **Purpose**: Pure-Python Git implementation
- **Justification**:
  - Dual-licensed with **Apache-2.0** as acceptable alternative
  - Development-only dependency
  - Not distributed with package
- **Risk**: None (Apache-2.0 license preferred)
- **Approved By**: Security team
- **Date**: 2025-11-16

### 5. pygit2 (GPL with Linking Exception)

- **Package**: `pygit2@1.19.0`
- **License**: GPL-2.0 with GCC Runtime Library Exception
- **Source**: Transitive dependency of `dvc`
- **Purpose**: Python bindings for libgit2
- **Justification**:
  - GPL-2.0 **with linking exception** (allows proprietary use)
  - Development-only dependency
  - Not distributed with package
  - Linking exception explicitly permits use in non-GPL software
- **Risk**: None (linking exception applies)
- **Approved By**: Security team
- **Date**: 2025-11-16

### 6. zc-lockfile (License Not Detected)

- **Package**: `zc-lockfile@4.0`
- **License**: Not detected by dependency scanner
- **Actual License**: ZPL-2.1 (Zope Public License)
- **Source**: Transitive dependency of `dvc`
- **Purpose**: File locking utilities for Zope components
- **Justification**:
  - ZPL-2.1 licensed (GPL-compatible, not GPL itself)
  - Scanner failed to detect license
  - Development-only dependency
- **Risk**: None (verified ZPL-2.1 license)
- **Approved By**: Security team
- **Date**: 2025-11-16

## License Policy Summary

### Distributed Package (Production)

**Package License**: MIT
**Allowed Dependencies**: MIT, Apache-2.0, BSD-3-Clause, ISC, PSF-2.0
**Denied Dependencies**: GPL-2.0, GPL-3.0, AGPL, proprietary licenses

### Development Dependencies Only

**Additional Allowed**:
- GPL licenses (if dev-only, not distributed)
- Dual-licensed packages with acceptable alternatives
- Packages with linking exceptions

**Rationale**: Development tools are not distributed with the package and do not affect the license of the MIT-licensed code.

## Configuration

Exception configured in [.github/workflows/security-analysis.yml](../../.github/workflows/security-analysis.yml:186):

```yaml
allow-dependencies-licenses: 'pkg:pypi/grandalf, pkg:pypi/text-unidecode, pkg:pypi/billiard, pkg:pypi/dulwich, pkg:pypi/pygit2, pkg:pypi/zc-lockfile'
```

## Verification

To verify these packages are not distributed with the package:

```bash
# Check production dependencies only
poetry export -f requirements.txt --output requirements.txt --without-hashes

# Verify DVC and transitive deps are NOT in requirements.txt
grep -E "grandalf|text-unidecode|billiard|dulwich|pygit2|zc-lockfile" requirements.txt
# Should return: (no matches)

# Check dev dependencies (where these appear)
poetry export -f requirements.txt --output requirements-dev.txt --with dev --without-hashes
grep -E "grandalf|text-unidecode|billiard|dulwich|pygit2|zc-lockfile" requirements-dev.txt
# Should return: (matches found - expected)
```

## Future Considerations

If any of these packages appear in **production dependencies** (not just dev):

1. ❌ **Immediate action required** - Remove or replace the dependency
2. ⚠️  **License violation** - GPL dependencies cannot be included in MIT-licensed distribution
3. 🔄 **Migration path** - Use alternatives documented in [.tmp-dataset-versioning-alternatives-analysis.md](../../tmp_cleanup/.tmp-dataset-versioning-alternatives-analysis.md)

**Recommended Migration**: Hugging Face Hub (Apache 2.0) as documented in alternatives analysis.

## Review Schedule

- **Quarterly Review**: Verify exceptions are still valid
- **On Dependency Updates**: Re-verify licenses haven't changed
- **Before Major Releases**: Audit all dependencies for license compliance

---

**Last Reviewed**: 2025-11-16
**Next Review**: 2025-02-16
**Approved By**: Security team
**Status**: Active
