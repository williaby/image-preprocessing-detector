---
schema_type: common
title: "ADR-003: Adopt Property-Based Testing with Hypothesis"
description: "Decision to use Hypothesis for property-based testing to complement
  example-based tests"
tags:
- adr
- testing
- hypothesis
- property_based_testing
- quality
status: published
owner: "core-maintainer"
authors:
- name: "Byron Williams"
purpose: "Document the decision to adopt property-based testing with Hypothesis for
  discovering edge cases and verifying invariants."
---


**Status**: ✅ **Accepted**
**Date**: 2025-01-08
**Deciders**: Byron Williams
**Related**: Sprint 3 - Advanced Testing and Tooling Consolidation

## Context

Traditional example-based testing (pytest) tests specific inputs and outputs. While effective, it has limitations:

### Limitations of Example-Based Testing

1. **Limited Coverage**: Only tests cases the developer thinks of
2. **Edge Case Blind Spots**: May miss boundary conditions
3. **Maintenance**: Each edge case requires a new test
4. **False Confidence**: 100% coverage doesn't mean all behaviors tested

### Project Requirements

The Image Preprocessing Detector handles diverse inputs:

- PDF files (various encodings, corrupted data)
- Images (PNG, JPEG, TIFF, corrupted headers)
- Bounding boxes (coordinates, dimensions)
- Confidence scores (0.0-1.0 range validation)
- Document metadata (JSON serialization/deserialization)

**Need**: Systematic way to discover edge cases and verify invariants across input space.

## Decision

**Adopt Hypothesis for property-based testing to complement example-based pytest tests.**

### Approach

1. **Complement, Don't Replace**: Keep example-based tests for known scenarios
2. **Focus on Invariants**: Test properties that should always hold
3. **Custom Strategies**: Build domain-specific data generators
4. **Roundtrip Testing**: Verify serialization/deserialization
5. **Boundary Validation**: Test edge cases systematically

### Implementation

Created [tests/unit/test_property_based.py](../../tests/unit/test_property_based.py) with:

1. **Custom Hypothesis Strategies**:

   ```python
   @composite
   def confidence_scores(draw):
       """Generate valid confidence scores (0.0 to 1.0)."""
       return draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))

   @composite
   def bounding_boxes(draw):
       """Generate valid COCO-format bounding boxes [x, y, width, height]."""
       # ... ensures all coordinates and dimensions are positive
   ```

2. **Property Tests**:
   - **Validation invariants**: `0.0 <= confidence <= 1.0` always holds
   - **Roundtrip serialization**: `serialize(deserialize(x)) == x`
   - **Format constraints**: COCO bboxes always `[x, y, width, height]`
   - **Boundary conditions**: Page dimensions must be positive
   - **Edge cases**: Multi-page documents, empty metadata

3. **Integration with pytest**: Hypothesis integrates seamlessly with existing test suite

### Examples

```python
@given(confidence_scores())
def test_confidence_always_in_valid_range(confidence: float) -> None:
    """Property: All generated confidence scores must be valid."""
    assert 0.0 <= confidence <= 1.0

    issue = DetectedIssue(
        type=IssueType.BLUR,
        confidence=confidence,
        severity=IssueSeverity.LOW,
    )
    assert issue.confidence == confidence

@given(detected_issues())
def test_detected_issue_json_roundtrip(issue: DetectedIssue) -> None:
    """Property: JSON encode → decode should preserve data."""
    json_str = issue.model_dump_json()
    deserialized = DetectedIssue.model_validate_json(json_str)

    assert deserialized.type == issue.type
    assert abs(deserialized.confidence - issue.confidence) < 1e-6
```

## Consequences

### Positive

1. **Edge Case Discovery**: Hypothesis finds edge cases developers miss
   - Example: Found datetime timezone handling issues during implementation
2. **Invariant Verification**: Systematically tests properties that should always hold
3. **Reduced Test Maintenance**: One property test replaces dozens of example tests
4. **Regression Prevention**: Hypothesis saves failing examples for regression testing
5. **Documentation**: Property tests document system invariants
6. **Confidence Boost**: More confident in handling diverse real-world inputs

### Negative

1. **Learning Curve**: Team needs to understand property-based testing concepts
   - Mitigation: Created comprehensive examples in test_property_based.py
2. **Test Runtime**: Hypothesis runs 100+ examples per test (slower than single example)
   - Mitigation: Acceptable overhead (< 5 seconds per test class)
3. **Debugging**: Shrinking failing examples can be complex
   - Mitigation: Hypothesis provides minimal failing example automatically

### Neutral

1. **Complementary Approach**: Works alongside example-based tests
2. **Additional Dependency**: Hypothesis already installed (0.21.0+)

## Alternatives Considered

### Alternative 1: Only Example-Based Testing

**Rejected**:

- Misses edge cases
- Requires manual enumeration of test cases
- Less confidence in handling diverse inputs

### Alternative 2: QuickCheck (Haskell-style)

**Rejected**:

- Hypothesis is the Python standard
- Better pytest integration
- More active Python community

### Alternative 3: Faker for Test Data

**Rejected**:

- Faker generates realistic data, not edge cases
- Doesn't verify invariants
- No automatic shrinking

### Alternative 4: Manual Fuzzing

**Rejected**:

- Less systematic than Hypothesis
- No shrinking to minimal failing example
- More code to maintain

## Test Coverage

Property-based tests added for:

1. **Schema Validation** (5 properties):
   - Confidence score ranges
   - Bounding box format constraints
   - Invalid input rejection
   - Roundtrip serialization
   - JSON encode/decode

2. **Transformations** (2 properties):
   - Transform history recording
   - Multi-transform composition

3. **Edge Cases** (3 properties):
   - Page dimension validation
   - Multi-page documents
   - Empty/minimal metadata

4. **Integration** (1 property):
   - Quality issues serialization

## Implementation

- **Test File**: [tests/unit/test_property_based.py](../../tests/unit/test_property_based.py)
- **PR**: Sprint 3 - Advanced Testing and Tooling Consolidation
- **Commit**: `3c34081`
- **Lines**: 343 LOC (comprehensive examples)

## References

- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [Property-Based Testing with Hypothesis](https://www.hillelwayne.com/post/hypothesis-intro/)
- [Hypothesis Strategies](https://hypothesis.readthedocs.io/en/latest/data.html)
- [Property-Based Testing Best Practices](https://www.youtube.com/watch?v=hXnS_Xjwk2Y)
- [Test Implementation](../../tests/unit/test_property_based.py)
