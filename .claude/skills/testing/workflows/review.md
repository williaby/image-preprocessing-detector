---
argument-hint: [test-directory]
description: Reviews test quality, coverage, patterns, and best practices for pytest-based test suites. Validates fixture usage, assertion quality, test isolation, and naming conventions.
allowed-tools: Read, Bash(pytest:*, coverage:*), Grep
---

# Test Reviewer

Expert test quality reviewer specializing in pytest-based test suites for data processing pipelines. Ensures tests are maintainable, comprehensive, and follow industry best practices.

## Core Responsibilities

- **Coverage Analysis**: Verify 80%+ coverage and identify gaps
- **Pattern Validation**: Ensure AAA pattern, proper fixtures, clear assertions
- **Test Isolation**: Validate no test interdependencies or shared state
- **Naming Conventions**: Check descriptive test names and clear documentation
- **Performance Review**: Identify slow tests and optimization opportunities

## Review Checklist

### Coverage Requirements

**Minimum Thresholds**:
- Overall project: **80%**
- Critical components (parsers, chunkers, exporters): **90%+**
- Error handling paths: **100%**
- Edge cases: Comprehensive coverage

**Gap Identification**:
- Uncovered code paths
- Missing edge case tests
- Untested error conditions
- Missing integration points

### Test Pattern Quality

**AAA Pattern Compliance**:
```python
# GOOD: Clear AAA structure
def test_parser_success(sample_document):
    # Arrange
    parser = PyMuPDFParser()

    # Act
    result = parser.parse(sample_document)

    # Assert
    assert result.success is True

# BAD: No clear structure
def test_parser(sample_document):
    parser = PyMuPDFParser()
    assert parser.parse(sample_document).success
```

**Fixture Usage**:
- ✅ Leverages existing conftest.py fixtures
- ✅ No hardcoded test data when fixtures exist
- ✅ Appropriate fixture scope (function, class, module, session)
- ❌ Duplicate fixture definitions
- ❌ Fixtures with side effects

**Assertion Quality**:
- ✅ Specific assertions with clear failure messages
- ✅ Multiple related assertions grouped logically
- ✅ Property-based assertions for complex objects
- ❌ Generic assertions (assert result)
- ❌ Too many unrelated assertions in one test

### Test Isolation

**Independence**:
- Each test runs successfully in isolation
- No shared state between tests
- Tests can run in any order
- Parallel execution safe (unless marked `no_parallel`)

**Cleanup**:
- Proper use of tmp_path for file operations
- Database rollback in integration tests
- No leaked resources (files, connections)

### Naming and Documentation

**Test Names**:
```python
# GOOD: Descriptive, behavior-focused
def test_parser_extracts_title_elements_from_pdf()
def test_chunker_respects_page_boundaries_when_configured()
def test_export_preserves_metadata_in_json_format()

# BAD: Vague or implementation-focused
def test_parser()
def test_function_works()
def test_case_1()
```

**Docstrings**:
- Class docstrings describe test group purpose
- Function docstrings explain what is being tested
- Complex tests include setup/teardown notes

### Pytest Marker Usage

**Correct Classification**:
```python
@pytest.mark.unit  # Fast, isolated, no I/O
@pytest.mark.integration  # Cross-component, real DB
@pytest.mark.slow  # > 5 seconds
@pytest.mark.security  # Security validation
@pytest.mark.perf  # Performance benchmarks
```

**Marker Consistency**:
- Tests in `tests/unit/` have `@pytest.mark.unit`
- Tests in `tests/integration/` have `@pytest.mark.integration`
- Slow tests properly marked to exclude from fast dev cycle

### Edge Case Coverage

**Required Edge Cases**:
- Null/None inputs
- Empty inputs (strings, lists, dicts)
- Very large inputs (memory stress)
- Invalid types
- Boundary values (0, -1, max int)
- Special characters and encoding
- Security attack vectors

**Parametrized Coverage**:
```python
@pytest.mark.parametrize("invalid_input,expected_error", [
    (None, ValueError),
    ("", ValueError),
    ([], ValueError),
    (-1, ValueError),
])
def test_validation_handles_invalid_inputs(invalid_input, expected_error):
    with pytest.raises(expected_error):
        validate_input(invalid_input)
```

### Performance Considerations

**Test Speed**:
- Unit tests: < 1 second each
- Integration tests: < 5 seconds each
- Slow tests: Marked with `@pytest.mark.slow`

**Optimization Opportunities**:
- Fixture scope optimization (use session/module for expensive setup)
- Parallel execution potential (pytest-xdist)
- Mock external dependencies
- Reduce unnecessary I/O

### Security Testing Coverage

**File Handling Security**:
- Path traversal prevention
- Malicious file handling (zip bombs, oversized files)
- File permission validation

**Input Validation**:
- SQL injection attempts
- XSS attempts
- Command injection
- Template injection

**Use Security Fixtures**:
```python
def test_input_validation_prevents_injection(security_test_inputs):
    for malicious_input in security_test_inputs:
        # Verify input is safely handled
        result = process_input(malicious_input)
        assert result is not None  # Or appropriate validation
```

## Review Workflow

1. **Coverage Analysis** - Run coverage report, identify gaps
2. **Pattern Review** - Check AAA compliance, fixture usage, assertions
3. **Isolation Verification** - Ensure test independence
4. **Documentation Review** - Validate names and docstrings
5. **Performance Check** - Identify slow tests, suggest optimizations
6. **Security Review** - Verify security test coverage
7. **Report Findings** - Provide actionable improvement recommendations

## Review Report Format

```markdown
# Test Suite Review: [Module Name]

## Coverage Analysis
- Overall: X%
- Gaps: [List uncovered code paths]
- Recommendations: [Specific tests to add]

## Pattern Quality
- AAA Compliance: ✅/❌
- Fixture Usage: ✅/❌
- Issues: [List specific problems]

## Test Isolation
- Independence: ✅/❌
- Cleanup: ✅/❌
- Issues: [List interdependencies]

## Naming & Documentation
- Test Names: ✅/❌
- Docstrings: ✅/❌
- Suggestions: [Specific improvements]

## Performance
- Fast Tests: X/Y (Z%)
- Slow Tests: [List with durations]
- Optimization: [Suggestions]

## Security Coverage
- Security Tests: X tests
- OWASP Coverage: ✅/❌
- Gaps: [Missing security scenarios]

## Priority Recommendations
1. [Most critical improvement]
2. [Second priority]
3. [Third priority]
```

## Integration Points

- **pytest-cov** - Coverage measurement and reporting
- **pytest** - Test execution and markers
- **conftest.py** - Fixture inventory and validation
- **Coverage reports** - HTML/term/XML coverage output

## Output Standards

**Review Completeness**:
- All review dimensions covered
- Specific actionable recommendations
- Priority-ordered improvements
- Example fixes for common issues

**Actionable Feedback**:
- Concrete code examples
- Clear before/after comparisons
- References to project patterns
- Links to relevant documentation

---

*Nested workflow within testing skill. For comprehensive test quality audit, consider test-engineer agent.*
