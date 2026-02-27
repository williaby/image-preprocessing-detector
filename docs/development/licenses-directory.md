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

**Purpose**: License text files for REUSE Specification compliance (FSFE REUSE).

## What Goes Here

**Belongs in LICENSES/**:

- Full text of all licenses actively used in the project
- CC-BY-SA-4.0, CC0-1.0, ODbL-1.0, OFL-1.1
- License texts for third-party dependencies (add as needed)
- SPDX-compliant license files

**Does NOT belong here**:

- **Project LICENSE file** -> `LICENSE` (root-level, project license)
- **License declarations** -> `REUSE.toml` (centralized via `precedence = "override"`)

## REUSE Specification

This project follows the [REUSE Specification](https://reuse.software/) for license compliance:

1. **License Files**: Full license texts in `LICENSES/`
2. **REUSE.toml**: Centralized copyright and license declarations with `precedence = "override"` (no inline SPDX headers needed)

## Current License Files

### Project Code and Documentation: CC-BY-SA-4.0

**File**: `CC-BY-SA-4.0.txt`

- Used for: Source code (`src/`, `tests/`, `scripts/`), documentation (`docs/`, `*.md`)
- Creative Commons Attribution-ShareAlike 4.0 International

### Configuration and Metadata: CC0-1.0

**File**: `CC0-1.0.txt`

- Used for: Configuration files, build artifacts, generated files, metadata
- Public domain dedication

### Data and Models: ODbL-1.0

**File**: `ODbL-1.0.txt`

- Used for: Data files, datasets with Open Database License
- Requires attribution for redistribution

### Fonts: OFL-1.1

**File**: `OFL-1.1.txt`

- Used for: Font files included in the project
- SIL Open Font License

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
3. **Update REUSE.toml**: Add an `[[annotations]]` block with the new license
4. **Run reuse lint**: Verify compliance

Example:

```bash
# Download BSD-3-Clause license (using SPDX canonical GitHub URL with release tag)
curl -fSL https://raw.githubusercontent.com/spdx/license-list-data/v3.25.0/text/BSD-3-Clause.txt > LICENSES/BSD-3-Clause.txt

# Verify
reuse lint
```

## License Compatibility

**Outbound License**: CC-BY-SA-4.0

**Compatible Inbound Licenses**:

- CC-BY-4.0 (one-way compatible into CC-BY-SA-4.0)
- MIT (permissive, compatible)
- Apache-2.0 (permissive, compatible)
- BSD-3-Clause (permissive, compatible)
- CC0-1.0 (public domain, compatible)
- GPL-3.0 (one-way compatible from CC-BY-SA-4.0 outbound)

**Incompatible Inbound Licenses**:

- GPL-2.0, GPL-3.0 (separate copyleft family)
- AGPL-3.0 (network copyleft, requires service separation)
- Proprietary (incompatible)

## CI/CD Integration

REUSE compliance checked in CI:

```yaml
# .github/workflows/reuse.yml
- name: REUSE Compliance Check
  uses: fsfe/reuse-action@v4
```

## Distinction from Root LICENSE

- **LICENSES/**: All license texts used in project
- **LICENSE** (root): Project's main license (CC-BY-SA-4.0)

The root `LICENSE` file declares the project license, while `LICENSES/` contains all licenses used by the project and its dependencies.

## Dataset License Attribution

When using public datasets:

1. **Check license**: DocLayNet (CDLA-Permissive-2.0), Genalog (MIT)
2. **Add license text**: Download to `LICENSES/` if not already present
3. **Document in CITATIONS.md**: Reference in `docs/references/CITATIONS.md`
4. **Update REUSE.toml**: Add copyright/license annotation

## Resources

- [REUSE Specification](https://reuse.software/spec/)
- [SPDX License List](https://spdx.org/licenses/)
- [REUSE Tool](https://github.com/fsfe/reuse-tool)
- [FSFE REUSE](https://reuse.software/)
