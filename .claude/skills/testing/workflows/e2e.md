---
argument-hint: [workflow-name]
description: Creates end-to-end tests for complete document processing pipelines, CLI workflows, and multi-component integration scenarios. Tests full user journeys from file input to final output.
allowed-tools: Read, Write, Bash(pytest:*)
---

# E2E Tester

Specialized end-to-end testing for data ingestion pipelines, focusing on complete user workflows from document input through parsing, chunking, and export to final output validation.

## Core Responsibilities

- **Pipeline Testing**: Complete document processing flows (detect → parse → chunk → export)
- **CLI Workflow Testing**: Command-line interface end-to-end scenarios
- **Fallback Chain Testing**: Parser fallback mechanisms with real failures
- **Multi-Format Testing**: Processing different document formats end-to-end
- **Error Recovery**: Complete error handling and recovery workflows

## E2E Testing Approach

### Complete Pipeline Testing

**Full Processing Pipeline**:
```python
@pytest.mark.e2e
class TestDocumentProcessingPipeline:
    """End-to-end tests for complete document processing."""

    def test_complete_pdf_processing_workflow(self, tmp_path):
        """Test complete PDF processing from input to output."""
        # Arrange - Create real PDF file
        pdf_file = tmp_path / "test_document.pdf"
        create_realistic_pdf(pdf_file, pages=5, has_tables=True)

        # Act - Process through complete pipeline
        settings = Settings()
        router = DocumentRouter(settings)

        # Initialize parsers
        router.parser_registry.register(PyMuPDFParser(), [DocumentFormat.PDF])

        # Process document
        document, result = router.process_document(source_path=pdf_file)

        # Apply chunking
        chunker = TokenChunker(chunk_size=1000, chunk_overlap=200)
        chunks = chunker.chunk_document(document)
        document.chunks = chunks

        # Export to JSON and Markdown
        exporter = DocumentExporter()
        output_path = tmp_path / "output"
        json_data, markdown = exporter.export(
            document, OutputFormat.BOTH, output_path
        )

        # Assert - Verify complete pipeline results
        assert result.success is True
        assert len(document.elements) > 0
        assert len(chunks) > 0
        assert (output_path.with_suffix(".json")).exists()
        assert (output_path.with_suffix(".md")).exists()

        # Verify data integrity through pipeline
        assert json_data["document_id"] == document.document_id
        assert len(json_data["elements"]) == len(document.elements)
        assert document.document_id in markdown
```

**Multi-Step Pipeline Validation**:
```python
@pytest.mark.e2e
def test_pipeline_preserves_metadata_through_stages(tmp_path):
    """Test that metadata is preserved through all pipeline stages."""
    # Create document with rich metadata
    pdf_file = create_pdf_with_metadata(
        tmp_path,
        title="Test Document",
        author="Test Author",
        keywords=["test", "pipeline", "metadata"],
    )

    # Process through pipeline
    router = DocumentRouter(Settings())
    router.parser_registry.register(PyMuPDFParser(), [DocumentFormat.PDF])

    document, _ = router.process_document(source_path=pdf_file)

    # Verify parsing preserved metadata
    assert document.metadata.get("title") == "Test Document"
    assert document.metadata.get("author") == "Test Author"

    # Chunk document
    chunker = ByTitleChunker()
    chunks = chunker.chunk_document(document)
    document.chunks = chunks

    # Verify chunking preserved document metadata
    assert document.metadata.get("title") == "Test Document"

    # Export document
    exporter = DocumentExporter()
    json_data = exporter.to_json(document)

    # Verify export preserved all metadata
    assert json_data["metadata"]["title"] == "Test Document"
    assert json_data["metadata"]["author"] == "Test Author"
```

### CLI Workflow Testing

**CLI Command Testing**:
```python
@pytest.mark.e2e
class TestCLIWorkflows:
    """End-to-end tests for CLI commands."""

    def test_cli_process_command_with_json_output(self, tmp_path):
        """Test CLI process command creates JSON output."""
        from click.testing import CliRunner
        from data_ingestor.cli.main import cli

        # Create test PDF
        pdf_file = tmp_path / "input.pdf"
        create_realistic_pdf(pdf_file)

        output_file = tmp_path / "output.json"

        # Run CLI command
        runner = CliRunner()
        result = runner.invoke(cli, [
            "process",
            str(pdf_file),
            "--output", str(output_file),
            "--format", "json",
        ])

        # Verify CLI execution
        assert result.exit_code == 0
        assert output_file.exists()

        # Verify output content
        import json
        with output_file.open() as f:
            data = json.load(f)

        assert "document_id" in data
        assert "elements" in data
        assert len(data["elements"]) > 0
```

### Parser Fallback Chain Testing

**Fallback Mechanism Validation**:
```python
@pytest.mark.e2e
class TestParserFallbackChains:
    """Test parser fallback mechanisms end-to-end."""

    def test_falls_back_to_secondary_parser_on_failure(self, tmp_path):
        """Test that parser fallback works with real failures."""
        # Create PDF that primary parser might fail on
        problematic_pdf = create_problematic_pdf(tmp_path)

        router = DocumentRouter(Settings())

        # Register parsers with priorities
        primary_parser = MarkerPDFParser()  # Higher quality, might fail
        fallback_parser = PyMuPDFParser()  # More robust

        router.parser_registry.register(primary_parser, [DocumentFormat.PDF], priority=10)
        router.parser_registry.register(fallback_parser, [DocumentFormat.PDF], priority=20)

        # Process document
        document, result = router.process_document(source_path=problematic_pdf)

        # Verify processing succeeded (potentially via fallback)
        assert result.success is True
        assert len(document.elements) > 0

        # Verify which parser was used
        assert document.parser_used in ["MarkerPDFParser", "PyMuPDFParser"]
```

### Multi-Format Testing

**Different Format Workflows**:
```python
@pytest.mark.e2e
@pytest.mark.parametrize("format,create_func,expected_elements", [
    (DocumentFormat.PDF, create_realistic_pdf, 10),
    # Add more formats as they're implemented
])
def test_multi_format_processing(tmp_path, format, create_func, expected_elements):
    """Test processing different document formats end-to-end."""
    # Create document of specified format
    doc_file = tmp_path / f"test.{format.value}"
    create_func(doc_file)

    # Process through pipeline
    router = DocumentRouter(Settings())
    # Register appropriate parsers based on format

    document, result = router.process_document(source_path=doc_file)

    # Verify successful processing
    assert result.success is True
    assert len(document.elements) >= expected_elements
    assert document.format == format
```

### Data Integrity Validation

**Round-Trip Testing**:
```python
@pytest.mark.e2e
def test_export_import_round_trip_preserves_data(tmp_path):
    """Test that data survives export/import round-trip."""
    # Create and process document
    pdf_file = create_realistic_pdf(tmp_path / "input.pdf")

    router = DocumentRouter(Settings())
    router.parser_registry.register(PyMuPDFParser(), [DocumentFormat.PDF])

    original_doc, _ = router.process_document(source_path=pdf_file)

    # Export to JSON
    exporter = DocumentExporter()
    json_file = tmp_path / "export.json"
    exporter.export(original_doc, OutputFormat.JSON, json_file)

    # Import back from JSON
    import json
    with json_file.open() as f:
        imported_data = json.load(f)

    # Verify data integrity
    assert imported_data["document_id"] == original_doc.document_id
    assert len(imported_data["elements"]) == len(original_doc.elements)
    assert imported_data["format"] == original_doc.format.value

    # Verify metadata preservation
    for key, value in original_doc.metadata.items():
        assert imported_data["metadata"][key] == value
```

## E2E Test Characteristics

**Real Dependencies**:
- Use actual file I/O (with tmp_path)
- Real parser libraries (PyMuPDF, Marker)
- Complete pipeline execution
- Minimal mocking (only external services)

**User Perspective**:
- Test from user's point of view
- Complete workflows from start to finish
- Verify user-facing outputs
- Test error messages and feedback

**Performance**:
- Mark with @pytest.mark.e2e
- May be slower (> 5 seconds)
- Consider @pytest.mark.slow for very long tests

## Integration Points

- **tmp_path** - Temporary file creation
- **CliRunner** - CLI command testing
- **Real parsers** - PyMuPDFParser, MarkerPDFParser
- **@pytest.mark.e2e** - Test classification

## Output Standards

**E2E Test Quality**:
- Complete user workflows
- Real file operations
- Comprehensive assertions at each stage
- Clear documentation of workflow tested

**Test Structure**:
```python
@pytest.mark.e2e
def test_workflow_name(tmp_path):
    """Test [complete workflow description]."""
    # Arrange: Create realistic inputs
    # Act: Execute complete workflow
    # Assert: Verify end-to-end results and side effects
```

---

*Nested workflow within testing skill. For comprehensive E2E testing strategy across multiple workflows, use test-engineer agent.*
