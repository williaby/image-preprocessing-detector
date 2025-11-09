---
schema_type: dev
title: "ADR-005: MkDocs Documentation System with Front Matter Validation"
description: "Decision to use MkDocs with Material theme and Pydantic-validated front matter for comprehensive documentation"
tags: [adr, documentation, mkdocs, pydantic, validation, json-ld]
status: published
owner: "core-maintainer"
authors:
  - name: "Byron Williams"
created: "2025-01-08"
updated: "2025-01-08"
purpose: "Document the decision to implement MkDocs with Material theme, front matter validation, and JSON-LD injection for comprehensive documentation."
---

# ADR-005: MkDocs Documentation System with Front Matter Validation

**Status**: ✅ **Accepted**
**Date**: 2025-11-08 (Implementation), 2025-01-08 (ADR Documentation)
**Deciders**: Byron Williams
**Related**: Documentation Infrastructure, OpenSSF Best Practices

## Context

The project needed comprehensive documentation infrastructure with:

### Requirements

1. **User-Friendly**: Easy navigation for developers and users
2. **API Documentation**: Auto-generated from docstrings
3. **Structured Metadata**: Machine-readable documentation metadata
4. **Quality Gates**: Validation for documentation standards
5. **SEO**: Searchable, discoverable documentation
6. **Compliance**: OpenSSF Best Practices documentation requirements
7. **Maintainability**: Low-overhead authoring workflow

### Challenges

1. **Mixed Content Types**: Guides, API reference, development docs, project docs, security guides
2. **Metadata Quality**: Inconsistent front matter across documents
3. **Search Optimization**: Need structured data for search engines
4. **Ownership Tracking**: Who owns which documentation?
5. **Review Cadence**: When was documentation last reviewed?
6. **Automation**: How to generate API docs from code?

## Decision

**Implement MkDocs with Material theme, Pydantic-validated YAML front matter, and automated JSON-LD injection.**

### Architecture

```
MkDocs (Material Theme)
  ├─ Markdown + YAML front matter (validated by Pydantic v2)
  ├─ mkdocstrings[python] + griffe-pydantic → API from docstrings
  ├─ git-revision-date-localized-plugin → datePublished/dateModified
  ├─ mkdocs-gen-files → build-time Tools Catalog
  ├─ Theme override → global JSON-LD injection from page.meta
  └─ CI Pipeline
       1) Autofix front matter (validate_front_matter.py --fix)
       2) Strict validation (validate_front_matter.py)
       3) MkDocs build --strict
       4) Link checking (lychee)
       5) Deploy to GitHub Pages
```

### Key Components

1. **MkDocs Material**
   - Modern, responsive theme
   - Built-in search
   - Navigation sidebar
   - Dark mode support
   - Mobile-friendly

2. **Front Matter Validation** (Pydantic v2)
   - Discriminated unions by `schema_type`
   - Required fields: title, description, tags, owner, purpose
   - Autofix capability for missing/invalid fields
   - Pre-commit hook integration

   ```yaml
   ---
   schema_type: dev  # Discriminator: dev, guide, api, project, security, common
   title: "Page Title"
   description: "Brief description"
   tags: [snake_case, tags]
   owner: "core-maintainer"
   authors:
     - name: "Byron Williams"
   purpose: "One sentence ending with punctuation."
   ---
   ```

3. **mkdocstrings Integration**
   - Auto-generates API docs from Google-style docstrings
   - griffe-pydantic plugin for Pydantic model documentation
   - No code imports required (static analysis)

4. **JSON-LD Injection**
   - Structured data for search engines
   - TechArticle schema for documentation pages
   - Automatic metadata from front matter

5. **Git-Based Dates**
   - `datePublished`: First commit of file
   - `dateModified`: Last commit of file
   - Automatic tracking via git-revision-date-localized-plugin

### Content Organization

```
docs/
  ├─ index.md              # Project overview
  ├─ guides/               # User guides (7 files)
  │   ├─ installation.md
  │   ├─ quick-start.md
  │   ├─ overview.md
  │   └─ ...
  ├─ api/                  # API reference (6 files)
  │   ├─ schema.md
  │   ├─ ingestion.md
  │   └─ ...
  ├─ development/          # Development docs (4 files)
  │   ├─ architecture.md
  │   ├─ testing.md
  │   └─ ...
  ├─ project/              # Project docs (3 files)
  │   ├─ roadmap.md
  │   ├─ changelog.md
  │   └─ license.md
  ├─ security/             # Security guides (2 files)
  │   ├─ codeql-python-scanning-guide.md
  │   └─ fuzzing-implementation-guide.md
  └─ ADRs/                 # Architecture Decision Records
      ├─ README.md
      ├─ 0001-consolidate-linting-with-ruff.md
      └─ ...
```

## Consequences

### Positive

1. **Professional Documentation**: Material theme provides polished, modern UI
2. **Quality Enforcement**: Pydantic validation prevents metadata issues
3. **SEO Optimization**: JSON-LD structured data improves discoverability
4. **Low Maintenance**: Auto-generation reduces manual effort
5. **Ownership Clarity**: Front matter tracks document ownership
6. **Automated Validation**: Pre-commit and CI enforce standards
7. **API Documentation**: mkdocstrings keeps docs in sync with code
8. **Compliance**: Satisfies OpenSSF Best Practices documentation requirements

### Negative

1. **Initial Setup**: Required front matter migration for all docs
   - One-time cost: Completed during implementation
2. **Learning Curve**: Team needs to understand front matter schema
   - Mitigated: Comprehensive validation errors and autofix
3. **Build Dependency**: Requires Python environment for builds
   - Acceptable: Already required for project

### Neutral

1. **Static Site**: GitHub Pages hosting (free, reliable)
2. **CI Integration**: Documentation workflow runs on doc changes
3. **ReadTheDocs**: Also configured for .readthedocs.yaml

## Implementation Details

### Front Matter Schema Types

```python
# Discriminated union based on schema_type
class CommonFrontMatter(BaseModel):
    schema_type: Literal["common"] = "common"
    title: str
    description: str
    tags: list[str]
    owner: str
    purpose: str

class GuideFrontMatter(CommonFrontMatter):
    schema_type: Literal["guide"] = "guide"
    difficulty: Literal["beginner", "intermediate", "advanced"]
    prerequisites: list[str] | None = None

class APIFrontMatter(CommonFrontMatter):
    schema_type: Literal["api"] = "api"
    module: str
    # ...
```

### Validation CLI

```bash
# Autofix front matter
poetry run python tools/validate_front_matter.py docs --fix

# Strict validation
poetry run python tools/validate_front_matter.py docs

# JSON report
poetry run python tools/validate_front_matter.py docs --emit-json > report.json
```

### CI Pipeline

```yaml
- name: Autofix front matter
  run: poetry run python tools/validate_front_matter.py docs --fix

- name: Validate front matter (strict)
  run: poetry run python tools/validate_front_matter.py docs

- name: Build MkDocs site
  run: poetry run mkdocs build --clean

- name: Link Checker
  uses: lycheeverse/lychee-action@v2
  with:
    args: --no-progress site/
```

## Alternatives Considered

### Alternative 1: Sphinx
**Rejected**:
- More complex configuration
- Heavier theme customization required
- ReStructuredText less familiar than Markdown

### Alternative 2: Docusaurus (React-based)
**Rejected**:
- Requires Node.js (additional toolchain)
- Overkill for Python project
- Slower build times

### Alternative 3: No Front Matter Validation
**Rejected**:
- Inconsistent metadata quality
- No enforcement of documentation standards
- Manual quality checks required

### Alternative 4: Jekyll (GitHub Pages default)
**Rejected**:
- Less Python-friendly
- No built-in API documentation generation
- Weaker plugin ecosystem for Python projects

## Migration Path

1. **Phase 1**: Install MkDocs and dependencies ✅
2. **Phase 2**: Create front matter schema and validator ✅
3. **Phase 3**: Migrate existing documentation ✅
4. **Phase 4**: Add pre-commit hooks ✅
5. **Phase 5**: Configure CI/CD pipeline ✅
6. **Phase 6**: Deploy to GitHub Pages ✅

## Success Metrics

- 21 documentation pages with validated front matter ✅
- 100% front matter validation passing ✅
- Automatic deployment on main branch merges ✅
- < 5 minute build time ✅
- OpenSSF Best Practices documentation criteria met ✅

## References

- [MkDocs Documentation](https://www.mkdocs.org/)
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
- [mkdocstrings](https://mkdocstrings.github.io/)
- [griffe-pydantic](https://mkdocstrings.github.io/griffe-pydantic/)
- [JSON-LD for Technical Documentation](https://schema.org/TechArticle)
- [mkdocs.yml Configuration](../../mkdocs.yml)
- [Front Matter Validator](../../tools/validate_front_matter.py)
- [Documentation Workflow](../../.github/workflows/docs.yml)
- [ReadTheDocs Config](../../.readthedocs.yaml)
