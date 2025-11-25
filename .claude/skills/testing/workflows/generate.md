---
argument-hint: [module-path]
description: Generates comprehensive test suites with 80%+ coverage for data processing pipelines, parsers, and exporters. Uses pytest patterns, property-based testing, and leverages existing fixtures.
allowed-tools: Read, Write, Bash(pytest:*), Task
---

# Test Generator

Specialized test generation for data ingestion pipelines, document processing, and RAG systems. Creates unit, integration, and component tests following pytest best practices with emphasis on data quality validation.

## Core Responsibilities

- **Unit Test Generation**: Pure function tests for parsers, chunkers, exporters, validators
- **Integration Test Generation**: Pipeline flows, parser fallbacks, multi-component workflows
- **Property-Based Testing**: Hypothesis-driven tests for edge cases and invariants
- **Fixture Utilization**: Leverage existing conftest.py fixtures and create new ones as needed
- **Coverage Optimization**: Ensure 80%+ coverage with targeted test cases

## Testing Approach

### Test Organization
Follow project structure:
- `tests/unit/` - Fast isolated tests (< 1s each)
- `tests/integration/` - Cross-component tests with real dependencies
- `tests/contract/` - External service contract validation
- `tests/e2e/` - Full workflow tests

### Test Patterns

**AAA Pattern** (Arrange-Act-Assert):
```python
def test_parser_extracts_elements(sample_document, mock_parser):
    # Arrange
    parser = mock_parser

    # Act
    result = parser.parse(sample_document)

    # Assert
    assert result.success is True
    assert len(result.elements) > 0
```

**Parametrized Tests** for edge cases:
```python
@pytest.mark.parametrize("chunk_size,expected_chunks", [
    (100, 10),
    (500, 2),
    (1000, 1),
])
def test_chunking_with_various_sizes(sample_document, chunk_size, expected_chunks):
    chunker = TokenChunker(chunk_size=chunk_size)
    chunks = chunker.chunk_document(sample_document)
    assert len(chunks) == expected_chunks
```

**Property-Based Testing** with hypothesis:
```python
from hypothesis import given, strategies as st

@given(st.integers(min_value=1, max_value=10000))
def test_chunk_size_always_positive(chunk_size):
    chunker = TokenChunker(chunk_size=chunk_size)
    assert chunker.chunk_size > 0
```

### Fixture Usage

**Always leverage existing fixtures** from conftest.py:
- `sample_document` - Comprehensive document with metadata
- `sample_document_element` - Element with metadata
- `mock_parser` / `mock_parser_class` - Parser mocking
- `parser_registry`, `document_router` - Router testing
- `temp_test_file` - Temporary PDF files
- `security_test_inputs` - OWASP-based malicious inputs
- `performance_metrics` - Timing and performance validation
- `edge_case_inputs` - Comprehensive edge cases

### Coverage Requirements

- **Overall**: 80% minimum
- **Critical paths**: Parsers, chunkers, exporters should approach 95%+
- **Error handling**: Every exception path must be tested
- **Edge cases**: Null, empty, large, invalid inputs

### Pytest Markers

Use appropriate markers for test classification:
```python
@pytest.mark.unit  # Fast isolated test
@pytest.mark.integration  # Cross-component test
@pytest.mark.slow  # Excluded from fast dev cycle
@pytest.mark.security  # Security validation
@pytest.mark.perf  # Performance benchmark
```

## Test Generation Workflow

1. **Analyze module** - Understand public API, critical paths, dependencies
2. **Identify test scenarios** - Happy paths, error cases, edge cases, boundaries
3. **Select fixtures** - Use existing fixtures or propose new ones
4. **Write tests** - Follow AAA pattern, clear naming, comprehensive assertions
5. **Add markers** - Classify tests appropriately
6. **Verify coverage** - Ensure 80%+ coverage for new code

## Integration Points

- **pytest** - Primary test framework with asyncio support
- **hypothesis** - Property-based testing for invariants
- **pytest-mock** - Mocking external dependencies
- **pytest-cov** - Coverage measurement and reporting
- **conftest.py** - Centralized fixture management

## Output Standards

**Test Files**:
- Naming: `test_*.py` in appropriate subdirectory
- Classes: `Test*` for grouping related tests
- Functions: `test_*` with descriptive names

**Test Quality**:
- Clear test names describing what is tested
- Comprehensive docstrings explaining test purpose
- Single assertion focus (or related assertions)
- No test interdependencies
- Fast execution (< 1s for unit tests)

**Example Test Structure**:
```python
"""Tests for PDF parser functionality."""

import pytest
from data_ingestor.parsers.pdf_parser import PyMuPDFParser
from data_ingestor.core.models import DocumentFormat

class TestPyMuPDFParser:
    """Tests for PyMuPDFParser class."""

    def test_supports_pdf_format(self):
        """Test that parser supports PDF format."""
        parser = PyMuPDFParser()
        assert parser.supports_format(DocumentFormat.PDF) is True

    def test_parse_extracts_elements(self, temp_test_file):
        """Test that parser extracts document elements."""
        parser = PyMuPDFParser()
        from data_ingestor.core.models import Document, ProcessingStatus

        doc = Document(
            source_path=temp_test_file,
            format=DocumentFormat.PDF,
            status=ProcessingStatus.PENDING,
        )

        result = parser.parse(doc)

        assert result.success is True
        assert len(result.elements) > 0
        assert result.parser_name == "PyMuPDFParser"
```

## Agent Delegation

For complex test generation requiring comprehensive strategy:
- Use `test-engineer` agent via Task tool
- Agent provides multi-tier testing approach
- Handles complex fixture design and test architecture

---

*Nested workflow within testing skill. For comprehensive test strategy, invoke test-engineer agent.*
