---
schema_type: common
title: "LICENSES/"
tags:
  - licensing
  - legal
status: published
owner: core-maintainer
purpose: Documentation for licenses/.
---

<!--
SPDX-FileCopyrightText: 2024 Byron Williams <byronawilliams@gmail.com>
SPDX-License-Identifier: CC0-1.0
-->

**Purpose**: License text files for REUSE Specification compliance (FSFE REUSE).

## What Goes Here

**✅ Belongs in LICENSES/**:

- Full text of all licenses used in the project
- Apache-2.0, MIT, CC-BY-4.0, CC0-1.0, ODbL-1.0
- License texts for third-party dependencies
- SPDX-compliant license files

**❌ Does NOT belong here**:

- **Project LICENSE file** → `LICENSE` (root-level, project license)
- **License headers** → Source code files (inline SPDX identifiers)
- **Copyright notices** → `.reuse/dep5` file (bulk copyright declarations)

## REUSE Specification

This project follows the [REUSE Specification](https://reuse.software/) for license compliance:

1. **License Files**: Full license texts in `LICENSES/`
2. **File Headers**: SPDX identifiers in source files
3. **Dep5 File**: Bulk declarations in `.reuse/dep5`

## Current License Files

### Project Code: Apache-2.0

**File**: `Apache-2.0.txt`

- Used for: Main project source code (`src/`, `tests/`, `scripts/`)
- Full license text from Apache Software Foundation

### Documentation: CC-BY-4.0

**File**: `CC-BY-4.0.txt`

- Used for: Documentation files (`docs/`, `README.md`)
- Creative Commons Attribution 4.0 International

### Data/Configs: CC0-1.0

**File**: `CC0-1.0.txt`

- Used for: Configuration files, data files
- Public domain dedication

### Dataset Dependencies: ODbL-1.0

**File**: `ODbL-1.0.txt`

- Used for: Datasets with Open Database License
- Example: Some public datasets require attribution

### Permissive Code: MIT

**File**: `MIT.txt`

- Used for: Code snippets from MIT-licensed sources
- Includes copyright notice requirement

## SPDX License Identifiers

Each file in the project includes an SPDX identifier:

```python
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: Apache-2.0
```

## Verification

Check REUSE compliance:

```bash
# Install reuse tool
pip install reuse

# Run compliance check
reuse lint

# Expected output: Congratulations! Your project is compliant.
```

## Adding New Licenses

If adding a new dependency with a different license:

1. **Download license text**: Get from SPDX or source
2. **Add to LICENSES/**: Save as `{SPDX-ID}.txt`
3. **Update .reuse/dep5**: Add copyright/license info
4. **Run reuse lint**: Verify compliance

Example:

```bash
# Download BSD-3-Clause license (using SPDX canonical GitHub URL with release tag)
curl https://raw.githubusercontent.com/spdx/license-list-data/v3.25.0/text/BSD-3-Clause.txt > LICENSES/BSD-3-Clause.txt

# Verify
reuse lint
```

## License Compatibility

**Outbound License**: Apache-2.0 (for distributed software)

**Compatible Inbound Licenses**:

- ✅ Apache-2.0 (same license)
- ✅ MIT (permissive, compatible)
- ✅ BSD-3-Clause (permissive, compatible)
- ✅ CC0-1.0 (public domain, compatible)
- ⚠️ GPL-3.0 (copyleft, requires review)
- ❌ Proprietary (incompatible for open source)

## CI/CD Integration

REUSE compliance checked in CI:

```yaml
# .github/workflows/reuse.yml
- name: REUSE Compliance Check
  uses: fsfe/reuse-action@v1
```

## Distinction from Root LICENSE

- **LICENSES/**: All license texts used in project
- **LICENSE** (root): Project's main license (Apache-2.0)

The root `LICENSE` file declares the project license, while `LICENSES/` contains all licenses used by the project and its dependencies.

## Dataset License Attribution

When using public datasets:

1. **Check license**: DocLayNet (CDLA-Permissive-2.0), Genalog (MIT)
2. **Add license text**: Download to `LICENSES/` if not already present
3. **Document in CITATIONS.md**: Reference in `docs/references/CITATIONS.md`
4. **Include in .reuse/dep5**: Add copyright/license info

## Resources

- [REUSE Specification](https://reuse.software/spec/)
- [SPDX License List](https://spdx.org/licenses/)
- [REUSE Tool](https://github.com/fsfe/reuse-tool)
- [FSFE REUSE](https://reuse.software/)
