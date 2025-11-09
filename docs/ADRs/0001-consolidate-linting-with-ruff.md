---
schema_type: dev
title: "ADR-001: Consolidate Python Linting with Ruff"
description: "Decision to consolidate Black, pydocstyle, and partial Bandit functionality into Ruff"
tags: [adr, tooling, linting, ruff, consolidation]
status: published
owner: "core-maintainer"
authors:
  - name: "Byron Williams"
created: "2025-01-08"
updated: "2025-01-08"
purpose: "Document the decision to consolidate multiple Python linting tools into Ruff for better maintainability and performance."
---

# ADR-001: Consolidate Python Linting with Ruff

**Status**: ✅ **Accepted**
**Date**: 2025-01-08
**Deciders**: Byron Williams
**Related**: Sprint 3 - Advanced Testing and Tooling Consolidation

## Context

The project used multiple overlapping Python linting and formatting tools:

- **Black**: Code formatting (line length, quotes, indentation)
- **Ruff**: Limited linting (9 rule categories: E, W, F, I, B, C4, UP, ARG, SIM)
- **pydocstyle**: Docstring style checking (Google convention)
- **MyPy**: Type checking (strict on src/, relaxed on tests/)
- **interrogate**: Docstring coverage metrics
- **Bandit**: Security scanning

### Problems

1. **Tool Duplication**: Black and Ruff formatter serve the same purpose
2. **Performance Overhead**: Multiple tools running sequentially in pre-commit hooks
3. **Configuration Fragmentation**: Settings spread across multiple tools
4. **Maintenance Burden**: Keeping multiple tools updated and coordinated

### Requirements

- Maintain comprehensive code quality coverage
- Preserve Google-style docstring enforcement
- Keep security scanning capabilities
- Maintain type checking rigor
- Minimize pre-commit hook execution time

## Decision

**Consolidate Black, pydocstyle, and partial Bandit functionality into Ruff.**

### Changes

1. **Replace Black with Ruff Format**
   - Enable `[tool.ruff.format]` in pyproject.toml
   - Black-compatible formatting (88 char line length)
   - Add `ruff-format` pre-commit hook

2. **Replace pydocstyle with Ruff D Rules**
   - Add "D" (pydocstyle) to Ruff lint rules
   - Configure Google-style convention
   - Remove standalone pydocstyle hook

3. **Supplement Bandit with Ruff S Rules**
   - Add "S" (flake8-bandit) for basic security checks
   - Keep standalone Bandit for advanced security scanning
   - Ruff catches common issues, Bandit for deep analysis

4. **Expand Ruff Linting**
   - From 9 to 13 rule categories
   - Added: D (pydocstyle), S (security), N (naming), A (builtins), DTZ (datetime), PIE, Q (quotes), RET (return), PTH (pathlib)

5. **Keep Specialized Tools**
   - **MyPy**: Unique type checking capabilities
   - **interrogate**: Coverage metrics and reporting
   - **Bandit**: Advanced security pattern detection

### Configuration

```toml
[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.format]
quote-style = "double"
docstring-code-format = true

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP", "ARG", "SIM", "D", "S", "T20", "PT", "RUF", "N", "A", "DTZ", "PIE", "Q", "RET", "PTH"]

[tool.ruff.lint.pydocstyle]
convention = "google"
```

## Consequences

### Positive

1. **Single Formatter**: Ruff format replaces Black (one less tool)
2. **Unified Configuration**: All linting rules in one place
3. **Performance**: Ruff is 10-100× faster than traditional tools
4. **Consistency**: Single tool enforces multiple dimensions of code quality
5. **Maintenance**: Fewer dependencies to update and coordinate
6. **Pre-commit Speed**: Faster hook execution with fewer tools

### Negative

1. **Migration Effort**: Required updating pre-commit hooks and CI workflows
2. **Learning Curve**: Team needs to understand Ruff's unified approach
3. **Bandit Overlap**: Some security rules now checked by both Ruff (S) and Bandit
   - Mitigation: Acceptable redundancy, Bandit provides deeper analysis

### Neutral

1. **Coverage Unchanged**: All checks still enforced, just different tool
2. **Configuration Migration**: Straightforward translation from old tools to Ruff

## Alternatives Considered

### Alternative 1: Keep All Tools Separate
**Rejected**: Maintains tool duplication and slower pre-commit hooks

### Alternative 2: Remove MyPy and Use Only Ruff
**Rejected**: Ruff doesn't do type checking, MyPy is essential for type safety

### Alternative 3: Remove Bandit and Use Only Ruff S Rules
**Rejected**: Ruff's security rules are basic, Bandit catches advanced patterns

### Alternative 4: Adopt Pylint Instead of Ruff
**Rejected**: Slower than Ruff, doesn't include formatting, heavier configuration

## Implementation

- **PR**: Sprint 3 - Advanced Testing and Tooling Consolidation
- **Commit**: `3c34081`
- **Files Modified**:
  - `pyproject.toml`: Enhanced Ruff configuration
  - `.pre-commit-config.yaml`: Removed Black and pydocstyle hooks, added ruff-format
  - `poetry.lock`: Updated dependencies

## References

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Ruff vs. Other Tools](https://docs.astral.sh/ruff/faq/#how-does-ruff-compare-to-flake8)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [pyproject.toml Ruff Config](../../pyproject.toml#L213-L305)
- [Pre-commit Hooks](../../.pre-commit-config.yaml#L22-L30)
