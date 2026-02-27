"""Unit tests for annotation schema classes.

Tests the three-layer metadata architecture:
- Immutable layer (OriginalFileMetadata, OriginalLabels)
- Enrichment layer (EnrichmentData, EnrichmentVersion, LayoutDetection)
- Sample aggregate (SampleMetadata)
"""

from __future__ import annotations

import pytest

from image_preprocessing_detector.annotation.schemas import (
    CaptureMethod,
    DomainLevel1,
    EnrichmentData,
    EnrichmentTier,
    EnrichmentVersion,
    LayoutDetection,
    OriginalFileMetadata,
    OriginalLabels,
    ResolutionCategory,
    SampleMetadata,
)


class TestEnums:
    """Test enum definitions."""

    def test_capture_method_values(self) -> None:
        """Test CaptureMethod enum has expected values."""
        assert CaptureMethod.BORN_DIGITAL.value == "born_digital"
        assert CaptureMethod.SCANNER_FLATBED.value == "scanner_flatbed"
        assert CaptureMethod.SCANNER_ADF.value == "scanner_adf"
        assert CaptureMethod.CAMERA_PROFESSIONAL.value == "camera_professional"
        assert CaptureMethod.CAMERA_SMARTPHONE.value == "camera_smartphone"
        assert CaptureMethod.FAX.value == "fax"
        assert CaptureMethod.UNKNOWN.value == "unknown"

    def test_domain_level1_values(self) -> None:
        """Test DomainLevel1 enum has expected values."""
        assert DomainLevel1.TAX.value == "TAX"
        assert DomainLevel1.LEGAL.value == "LEG"
        assert DomainLevel1.FINANCIAL.value == "FIN"
        assert DomainLevel1.UNKNOWN.value == "UNK"

    def test_resolution_category_values(self) -> None:
        """Test ResolutionCategory enum has expected values."""
        assert ResolutionCategory.LOW.value == "low_<150"
        assert ResolutionCategory.MEDIUM.value == "medium_150-299"
        assert ResolutionCategory.STANDARD.value == "standard_300"
        assert ResolutionCategory.HIGH.value == "high_>300"

    def test_enrichment_tier_values(self) -> None:
        """Test EnrichmentTier enum has expected values."""
        assert EnrichmentTier.TIER_0_EXACT.value == "tier_0_exact"
        assert EnrichmentTier.TIER_1_ANNOTATION.value == "tier_1_annotation"
        assert EnrichmentTier.TIER_2_MODEL.value == "tier_2_model"
        assert EnrichmentTier.TIER_3_HEURISTIC.value == "tier_3_heuristic"

    def test_enums_are_str_subclass(self) -> None:
        """Test that enums are str subclasses for JSON serialization."""
        assert isinstance(CaptureMethod.BORN_DIGITAL, str)
        assert isinstance(DomainLevel1.TAX, str)
        assert isinstance(ResolutionCategory.LOW, str)
        assert isinstance(EnrichmentTier.TIER_0_EXACT, str)


class TestOriginalFileMetadata:
    """Test OriginalFileMetadata dataclass."""

    def test_create_with_required_fields(self) -> None:
        """Test creating OriginalFileMetadata with required fields."""
        meta = OriginalFileMetadata(
            format="png",
            width_px=2480,
            height_px=3508,
            channels=3,
            bit_depth=8,
            file_size_bytes=1_500_000,
        )

        assert meta.format == "png"
        assert meta.width_px == 2480
        assert meta.height_px == 3508
        assert meta.channels == 3
        assert meta.bit_depth == 8
        assert meta.file_size_bytes == 1_500_000
        assert meta.dpi is None
        assert meta.color_space is None

    def test_create_with_all_fields(self) -> None:
        """Test creating OriginalFileMetadata with all fields."""
        meta = OriginalFileMetadata(
            format="tiff",
            width_px=4960,
            height_px=7016,
            channels=4,
            bit_depth=16,
            file_size_bytes=50_000_000,
            dpi=600,
            color_space="CMYK",
        )

        assert meta.dpi == 600
        assert meta.color_space == "CMYK"


class TestOriginalLabels:
    """Test OriginalLabels dataclass."""

    def test_create_empty(self) -> None:
        """Test creating OriginalLabels with no labels."""
        labels = OriginalLabels()

        assert labels.diqa_overall is None
        assert labels.doclaynet_annotations is None
        assert labels.funsd_annotations is None

    def test_create_with_diqa_labels(self) -> None:
        """Test creating OriginalLabels with DIQA scores."""
        labels = OriginalLabels(
            diqa_overall=4.5,
            diqa_sharpness=4.2,
            diqa_color_fidelity=4.8,
            diqa_original_image="ori/img001.jpg",
        )

        assert labels.diqa_overall == pytest.approx(4.5)
        assert labels.diqa_sharpness == pytest.approx(4.2)
        assert labels.diqa_color_fidelity == pytest.approx(4.8)

    def test_funsd_annotations_is_dict(self) -> None:
        """Test P0-4 fix: FUNSD annotations are dict, not list."""
        # FUNSD format is an object/dict, not a list
        labels = OriginalLabels(
            funsd_annotations={"form": [], "words": []},
        )

        assert isinstance(labels.funsd_annotations, dict)

    def test_doclaynet_annotations_is_list(self) -> None:
        """Test DocLayNet annotations are list (COCO format)."""
        labels = OriginalLabels(
            doclaynet_annotations=[
                {"bbox": [100, 200, 300, 400], "category": "text"},
            ],
        )

        assert isinstance(labels.doclaynet_annotations, list)


class TestLayoutDetection:
    """Test LayoutDetection dataclass."""

    def test_create_detection(self) -> None:
        """Test creating a layout detection."""
        detection = LayoutDetection(
            class_name="table",
            bbox=[100.0, 200.0, 300.0, 400.0],
            confidence=0.95,
            source="doclayout_yolo",
        )

        assert detection.class_name == "table"
        assert detection.bbox == [100.0, 200.0, 300.0, 400.0]
        assert detection.confidence == pytest.approx(0.95)
        assert detection.source == "doclayout_yolo"


class TestEnrichmentData:
    """Test EnrichmentData dataclass."""

    def test_create_empty(self) -> None:
        """Test creating EnrichmentData with defaults."""
        data = EnrichmentData()

        assert data.capture_method is None
        assert data.resolution_dpi is None
        assert data.has_table is None
        assert data.layout_detections is None

    def test_create_with_content_flags(self) -> None:
        """Test creating EnrichmentData with content flags."""
        data = EnrichmentData(
            has_table=True,
            has_formula=False,
            has_handwriting=True,
            content_flags_tier="tier_0_exact",
            content_flags_source="dataset_construction",
        )

        assert data.has_table is True
        assert data.has_formula is False
        assert data.has_handwriting is True
        assert data.content_flags_tier == "tier_0_exact"

    def test_create_with_iso_fields(self) -> None:
        """Test creating EnrichmentData with ISO-compliant fields (v2.1)."""
        data = EnrichmentData(
            iso639_language="en",
            iso15924_script="Latn",
            script_family="latin",
            bcp47_tag="en-Latn",
            text_scope="page",
            paper_size="A4",
            paper_size_standard="iso",
        )

        assert data.iso639_language == "en"
        assert data.iso15924_script == "Latn"
        assert data.text_scope == "page"
        assert data.paper_size == "A4"


class TestEnrichmentVersion:
    """Test EnrichmentVersion dataclass."""

    def test_create_version(self) -> None:
        """Test creating an enrichment version."""
        version = EnrichmentVersion(
            version=1,
            created_at="2025-01-26T12:00:00Z",
            created_by="annotate_base_metadata.py",
            method="tier_2_model",
            description="Initial YOLO inference",
            git_sha="abc123def456",
            script_version="2.0.0",
        )

        assert version.version == 1
        assert version.method == "tier_2_model"
        assert version.git_sha == "abc123def456"

    def test_create_with_data(self) -> None:
        """Test creating enrichment version with data."""
        data = EnrichmentData(has_table=True)
        version = EnrichmentVersion(
            version=1,
            created_at="2025-01-26T12:00:00Z",
            created_by="test",
            method="tier_0_exact",
            description="Test",
            data=data,
        )

        assert version.data.has_table is True


class TestSampleMetadata:
    """Test SampleMetadata dataclass."""

    @pytest.fixture
    def sample_metadata(self) -> SampleMetadata:
        """Create a sample metadata instance for testing."""
        return SampleMetadata(
            id="abc123def456abc123def456abc12345",
            file_hash="sha256:abcdef1234567890" * 4,
            dataset_name="diqa-5000",
            dataset_version="1.0",
            original_path="train/img001.png",
            original_filename="img001.png",
            download_date="2025-01-15",
            original_labels=OriginalLabels(diqa_overall=4.5),
            original_file=OriginalFileMetadata(
                format="png",
                width_px=2480,
                height_px=3508,
                channels=3,
                bit_depth=8,
                file_size_bytes=1_500_000,
            ),
        )

    def test_create_sample(self, sample_metadata: SampleMetadata) -> None:
        """Test creating a sample metadata record."""
        assert sample_metadata.id == "abc123def456abc123def456abc12345"
        assert sample_metadata.dataset_name == "diqa-5000"
        assert sample_metadata.current_version == 0
        assert len(sample_metadata.enrichment_versions) == 0

    def test_add_enrichment(self, sample_metadata: SampleMetadata) -> None:
        """Test adding an enrichment version."""
        data = EnrichmentData(has_table=True)
        version_num = sample_metadata.add_enrichment(
            data=data,
            created_by="test",
            method="tier_0_exact",
            description="Test enrichment",
        )

        assert version_num == 1
        assert sample_metadata.current_version == 1
        assert len(sample_metadata.enrichment_versions) == 1
        assert sample_metadata.enrichment_versions[0].data.has_table is True

    def test_add_multiple_enrichments(self, sample_metadata: SampleMetadata) -> None:
        """Test adding multiple enrichment versions."""
        sample_metadata.add_enrichment(
            data=EnrichmentData(has_table=True),
            created_by="test",
            method="tier_0_exact",
            description="First",
        )

        sample_metadata.add_enrichment(
            data=EnrichmentData(has_table=True, has_formula=True),
            created_by="test2",
            method="tier_2_model",
            description="Second",
        )

        assert sample_metadata.current_version == 2
        assert len(sample_metadata.enrichment_versions) == 2

    def test_get_current_enrichment(self, sample_metadata: SampleMetadata) -> None:
        """Test getting current enrichment data."""
        # No enrichments yet
        assert sample_metadata.get_current_enrichment() is None

        # Add enrichment
        sample_metadata.add_enrichment(
            data=EnrichmentData(has_table=True),
            created_by="test",
            method="tier_0_exact",
            description="Test",
        )

        current = sample_metadata.get_current_enrichment()
        assert current is not None
        assert current.has_table is True

    def test_get_enrichment_version(self, sample_metadata: SampleMetadata) -> None:
        """Test getting a specific enrichment version."""
        sample_metadata.add_enrichment(
            data=EnrichmentData(has_table=True),
            created_by="test",
            method="tier_0_exact",
            description="First",
        )

        sample_metadata.add_enrichment(
            data=EnrichmentData(has_formula=True),
            created_by="test",
            method="tier_2_model",
            description="Second",
        )

        v1 = sample_metadata.get_enrichment_version(1)
        v2 = sample_metadata.get_enrichment_version(2)
        v3 = sample_metadata.get_enrichment_version(3)

        assert v1 is not None
        assert v1.data.has_table is True
        assert v2 is not None
        assert v2.data.has_formula is True
        assert v3 is None  # Doesn't exist

    def test_to_dict(self, sample_metadata: SampleMetadata) -> None:
        """Test converting sample to dictionary."""
        sample_metadata.add_enrichment(
            data=EnrichmentData(has_table=True),
            created_by="test",
            method="tier_0_exact",
            description="Test",
        )

        result = sample_metadata.to_dict()

        assert result["id"] == sample_metadata.id
        assert result["source"]["dataset_name"] == "diqa-5000"
        assert result["original_labels"]["diqa_overall"] == pytest.approx(4.5)
        assert result["original_file"]["format"] == "png"
        assert result["enrichments"]["current_version"] == 1
        assert len(result["enrichments"]["versions"]) == 1

    def test_from_dict_roundtrip(self, sample_metadata: SampleMetadata) -> None:
        """Test roundtrip conversion to/from dict."""
        sample_metadata.add_enrichment(
            data=EnrichmentData(has_table=True, resolution_dpi=300),
            created_by="test",
            method="tier_2_model",
            description="Test enrichment",
            git_sha="abc123",
        )

        # Convert to dict and back
        data = sample_metadata.to_dict()
        restored = SampleMetadata.from_dict(data)

        # Verify fields
        assert restored.id == sample_metadata.id
        assert restored.file_hash == sample_metadata.file_hash
        assert restored.dataset_name == sample_metadata.dataset_name
        assert restored.current_version == sample_metadata.current_version
        assert len(restored.enrichment_versions) == 1
        assert restored.enrichment_versions[0].data.has_table is True
        assert restored.enrichment_versions[0].data.resolution_dpi == 300
