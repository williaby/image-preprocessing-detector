---
schema_type: common
title: Mutation Testing Guide
tags:
  - testing
  - mutation_testing
  - quality
status: published
owner: docs-team
purpose: Guide for running mutation tests to verify test suite quality.
---

## Overview

Mutation testing helps verify the quality of our test suite by introducing small changes (mutations) to the code and checking if tests catch these bugs. A high mutation score indicates tests that effectively detect code changes.

## Quick Start

```bash
# Run mutation tests on all modules (slow - full run)
./scripts/run_mutation_tests.sh

# Run on a specific module (faster)
./scripts/run_mutation_tests.sh --module=schema

# Run in fast mode (only critical modules)
./scripts/run_mutation_tests.sh --fast

# Generate HTML report
./scripts/run_mutation_tests.sh --report
```

## Direct Commands

If you prefer to run mutmut directly:

```bash
# Run all mutations
poetry run mutmut run

# Run on specific file
poetry run mutmut run --paths-to-mutate=src/image_preprocessing_detector/schema.py

# Show results
poetry run mutmut results

# Show specific mutant
poetry run mutmut show 42

# Generate HTML report
poetry run mutmut html

# Show statistics
poetry run mutmut show-stats
```

## Configuration

Mutation testing is configured in `pyproject.toml`:

```toml
[tool.mutmut]
paths_to_mutate = "src/"
backup = false
runner = "uv run pytest -x --assert=plain -o addopts=''"
tests_dir = "tests/"
dict_synonyms = "Struct, NamedStruct"
```

### Key Settings

- **paths_to_mutate**: Source directories to mutate
- **backup**: Don't create backup files (we use git)
- **runner**: Command to run tests (using uv for speed)
- **tests_dir**: Where to find tests

## Understanding Results

### Mutation Statuses

| Status | Meaning | Action |
|--------|---------|--------|
| **killed** | Test caught the bug | Good - test works |
| **survived** | Test missed the bug | Add/improve tests |
| **timeout** | Test took too long | May be OK (infinite loop caught) |
| **suspicious** | Unexpected behavior | Investigate |
| **skipped** | Mutation skipped | Usually OK |

### Mutation Score

```
Mutation Score = (killed / total) × 100
```

- **>80%**: Excellent test coverage
- **60-80%**: Good, but room for improvement
- **<60%**: Tests need significant improvement

## Common Mutations

mutmut applies various mutations:

| Type | Example | What it tests |
|------|---------|---------------|
| Boundary | `>` → `>=` | Boundary conditions |
| Operator | `+` → `-` | Arithmetic operations |
| Constant | `1` → `2` | Magic numbers |
| Boolean | `True` → `False` | Boolean logic |
| Return | Remove return | Return value handling |

## Prioritizing Fixes

Focus on surviving mutants in:

1. **Critical paths**: schema.py, core/config.py
2. **Security-sensitive code**: validation, input handling
3. **Business logic**: dqs_calculator, routing

Less critical:
- Logging statements
- Error message changes
- UI/formatting code

## Example: Investigating Survivors

```bash
# Show surviving mutant #42
poetry run mutmut show 42

# Output:
# --- a/src/image_preprocessing_detector/schema.py
# +++ b/src/image_preprocessing_detector/schema.py
# @@ -100,7 +100,7 @@
#      @field_validator("confidence")
#      @classmethod
#      def validate_confidence(cls, v):
# -        if v < 0.0 or v > 1.0:
# +        if v <= 0.0 or v > 1.0:  # Mutation: < to <=
#              raise ValueError(...)

# Add test to kill this mutation:
def test_confidence_zero_is_valid():
    """Test that confidence=0.0 is valid (boundary condition)."""
    issue = DetectedIssue(
        type=IssueType.BLUR,
        severity=IssueSeverity.LOW,
        confidence=0.0,  # This should be valid!
    )
    assert issue.confidence == 0.0
```

## CI Integration

Mutation testing runs on-demand (not in CI by default due to time):

```yaml
# Optional CI job
mutation-testing:
  runs-on: ubuntu-latest
  if: github.event_name == 'workflow_dispatch'
  steps:
    - uses: actions/checkout@v4
    - run: poetry install --with dev
    - run: poetry run mutmut run --paths-to-mutate=src/image_preprocessing_detector/schema.py
    - run: poetry run mutmut results
```

## Best Practices

1. **Run regularly**: Weekly mutation testing catches test rot
2. **Focus on core modules**: Prioritize business logic over utilities
3. **Document survivors**: Track known surviving mutants with justification
4. **Combine with coverage**: High coverage + high mutation score = quality tests

## Target Mutation Score

| Module | Target | Current | Notes |
|--------|--------|---------|-------|
| schema.py | >85% | TBD | Core data models |
| detection/*.py | >80% | TBD | IQA algorithms |
| ingestion/*.py | >75% | TBD | File loading |
| metrics/*.py | >85% | TBD | Quality scores |

## Troubleshooting

### Slow Runs

```bash
# Use --paths-to-mutate for specific files
poetry run mutmut run --paths-to-mutate=src/image_preprocessing_detector/schema.py

# Use parallel testing (if pytest-xdist installed)
# Edit pyproject.toml runner to add -n auto
```

### Cache Issues

```bash
# Clear cache and restart
rm .mutmut-cache
poetry run mutmut run
```

### False Positives

Some mutations may survive legitimately:
- Logging changes (message text)
- Error message wording
- Unreachable code paths

Document these in a `.mutmut-allowlist` file if needed.

## References

- [mutmut Documentation](https://mutmut.readthedocs.io/)
- [Mutation Testing Theory](https://en.wikipedia.org/wiki/Mutation_testing)
- [TEST_IMPROVEMENT_TRACKER.md](./TEST_IMPROVEMENT_TRACKER.md) - Test coverage tracking
