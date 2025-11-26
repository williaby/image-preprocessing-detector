---
schema_type: common
title: "ADR-002: Separate Mutation Testing from Main CI"
description: "Decision to run mutation testing on a separate schedule with threshold-based
  flagging"
tags:
- adr
- testing
- mutation_testing
- ci_cd
- performance
status: published
owner: "core-maintainer"
authors:
- name: "Byron Williams"
purpose: "Document the decision to separate mutation testing from the main CI pipeline
  for cost and performance optimization."
---


**Status**: ✅ **Accepted**
**Date**: 2025-01-08
**Deciders**: Byron Williams
**Related**: Sprint 3 - Advanced Testing and Tooling Consolidation

## Context

Mutation testing is a powerful technique for assessing test quality by introducing small code changes (mutations) and verifying that tests catch them. However, mutation testing has significant performance implications:

### Performance Characteristics

- **Runtime**: 10-100× slower than regular test suite
- **Cost**: Expensive for large codebases (100+ mutations)
- **Diminishing Returns**: Value comes from identifying weak tests, not real-time verification

### Requirements

1. **Test Quality**: Need to verify tests catch mutations
2. **CI Performance**: Main CI must remain fast (< 15 minutes)
3. **Actionable Feedback**: Only flag when mutation score drops below threshold
4. **Cost Control**: Avoid expensive operations on every commit

### User Request

> "I want mutmut to be separate in the workflows from the other tools so that it can be scheduled on its own cadence and only flag above a predefined threshold"

## Decision

**Create dedicated mutation testing workflow running on weekly schedule with configurable thresholds.**

### Implementation

1. **Separate Workflow**: [.github/workflows/mutation-testing.yml](.github/workflows/mutation-testing.yml)
   - NOT part of main CI gates
   - Does not block PRs
   - Independent failure/success status

2. **Weekly Schedule**: Sundays at 2:00 AM UTC
   - Runs during low-activity period
   - One execution per week reduces cost
   - Manual trigger available for on-demand testing

3. **Threshold-Based Flagging**: Default 80% mutation score
   - Only fails if score drops below threshold
   - Prevents false positives from edge case mutations
   - Configurable via workflow_dispatch input

4. **Comprehensive Reporting**:
   - HTML report artifact (90-day retention)
   - JSON results for programmatic analysis
   - Automatic PR comments with mutation scores
   - GitHub step summary with visual metrics

### Configuration

```yaml
# Weekly schedule (Sundays 2:00 AM UTC)
on:
  schedule:
    - cron: "0 2 * * 0"
  workflow_dispatch:
    inputs:
      mutation_threshold:
        default: '80'
        type: string
```

```toml
# pyproject.toml
[tool.mutmut]
paths_to_mutate = "src/"
runner = "poetry run pytest -x --assert=plain -o addopts=''"
tests_dir = "tests/"
```

## Consequences

### Positive

1. **Fast CI**: Main CI remains < 15 minutes (no mutation testing overhead)
2. **Cost Control**: Weekly execution vs. per-commit (saving ~95% of mutation runs)
3. **Actionable Alerts**: Only flags real test quality issues (threshold-based)
4. **Comprehensive Analysis**: Full mutation testing without time pressure
5. **Non-Blocking**: Doesn't prevent merges, guides improvements
6. **Flexible Threshold**: Adjustable via workflow_dispatch for different quality bars

### Negative

1. **Delayed Feedback**: Issues discovered weekly vs. per-commit
   - Mitigation: Manual workflow_dispatch available for on-demand testing
2. **Longer Runtime**: 120-minute timeout for comprehensive testing
   - Acceptable: Not blocking PRs, runs overnight
3. **Additional Workflow**: One more workflow to maintain
   - Minimal: Standard GitHub Actions patterns

### Neutral

1. **Coverage vs. Speed Trade-off**: Accepted for better overall velocity
2. **Separate Quality Signal**: Mutation score tracked independently from coverage

## Alternatives Considered

### Alternative 1: Mutation Testing in Main CI

**Rejected**:

- Would add 30-60 minutes to PR feedback loop
- Expensive for every commit
- May block valid PRs on edge case mutations

### Alternative 2: Mutation Testing on Every PR

**Rejected**:

- Too expensive (cost scales with PR volume)
- Slower PR velocity
- Similar issues to Alternative 1

### Alternative 3: No Mutation Testing

**Rejected**:

- Misses opportunity to improve test quality
- No mechanism to detect weak test coverage
- Lower confidence in test suite effectiveness

### Alternative 4: Daily Schedule

**Rejected**:

- Still expensive for marginal additional value
- Weekly cadence provides sufficient feedback

## Implementation

- **Workflow**: [.github/workflows/mutation-testing.yml](../../.github/workflows/mutation-testing.yml)
- **Configuration**: [pyproject.toml](../../pyproject.toml#L394-L402)
- **PR**: Sprint 3 - Advanced Testing and Tooling Consolidation
- **Commit**: `3c34081`

## Monitoring

### Success Metrics

1. **Mutation Score**: Track trend over time (target: > 80%)
2. **Test Improvements**: Number of tests added after mutation failures
3. **CI Performance**: Main CI remains under 15-minute target

### Failure Scenarios

1. **Score Drop Below Threshold**: Review survived mutations, strengthen tests
2. **Timeout**: Optimize test suite or increase timeout
3. **Infrastructure Issues**: Check GitHub Actions status, retry manually

## References

- [mutmut Documentation](https://github.com/boxed/mutmut)
- [Mutation Testing Best Practices](https://pedrorijo.com/blog/intro-mutation/)
- [GitHub Actions Scheduled Events](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule)
- [Mutation Testing Workflow](../../.github/workflows/mutation-testing.yml)
