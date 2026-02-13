"""Unit tests for Layout Taxonomy cross-schema conversion.

Tests for:
- LayoutTaxonomy config loading and YAML validation
- Round-trip conversions for all 11 DocLayNet classes
- Lossy conversion flagging (child -> parent coarsening)
- Ambiguous expansion flagging (parent -> child, confidence < 1.0)
- All 7 schema class mappings
- Alias normalization
- DocLayNet index maps
- Mask index maps
"""

from __future__ import annotations

from typing import ClassVar

import pytest

from image_preprocessing_detector.schema_utils.layout_taxonomy import (
    ConversionResult,
    LayoutTaxonomy,
    get_default_taxonomy,
    reset_default_taxonomy,
)


@pytest.fixture
def taxonomy() -> LayoutTaxonomy:
    """Create LayoutTaxonomy with default config."""
    return LayoutTaxonomy()


class TestConfigLoading:
    """Test YAML config loading and validation."""

    def test_config_loads_successfully(self, taxonomy: LayoutTaxonomy) -> None:
        """Taxonomy loads without errors."""
        assert taxonomy.version == "1.0.0"

    def test_repr(self, taxonomy: LayoutTaxonomy) -> None:
        """Repr includes version and counts."""
        r = repr(taxonomy)
        assert "1.0.0" in r
        assert "canonical_classes=" in r
        assert "schemas=" in r

    def test_available_schemas(self, taxonomy: LayoutTaxonomy) -> None:
        """All 7 schemas are registered."""
        schemas = taxonomy.get_available_schemas()
        assert len(schemas) == 7
        for name in [
            "doclaynet",
            "docstructbench",
            "publaynet",
            "docling",
            "d4la",
            "funsd",
            "docsynth300k",
        ]:
            assert name in schemas

    def test_no_orphaned_canonical_classes(self, taxonomy: LayoutTaxonomy) -> None:
        """Every canonical class with a parent references a valid class."""
        all_classes = taxonomy.get_canonical_classes()
        for cls in all_classes:
            parent = taxonomy._get_parent(cls)
            if parent is not None:
                assert parent in all_classes, (
                    f"{cls} references unknown parent {parent}"
                )

    def test_no_circular_parents(self, taxonomy: LayoutTaxonomy) -> None:
        """No circular parent chains exist."""
        all_classes = taxonomy.get_canonical_classes()
        for cls in all_classes:
            visited: set[str] = set()
            current: str | None = cls
            while current is not None:
                assert current not in visited, (
                    f"Circular parent chain detected at {current}"
                )
                visited.add(current)
                current = taxonomy._get_parent(current)

    def test_all_schema_labels_map_to_valid_canonical(
        self, taxonomy: LayoutTaxonomy
    ) -> None:
        """Every schema class maps to a known canonical class."""
        all_canonical = set(taxonomy.get_canonical_classes())
        for schema in taxonomy.get_available_schemas():
            for label in taxonomy.get_schema_classes(schema):
                canonical = taxonomy.to_canonical(label, schema)
                assert canonical in all_canonical, (
                    f"{schema}:{label} -> {canonical} not in canonical set"
                )

    def test_invalid_config_path_raises(self) -> None:
        """FileNotFoundError for missing config."""
        with pytest.raises(FileNotFoundError):
            LayoutTaxonomy(config_path="/nonexistent/path.yaml")

    def test_unknown_schema_raises_on_get_classes(
        self, taxonomy: LayoutTaxonomy
    ) -> None:
        """ValueError for unknown schema in get_schema_classes."""
        with pytest.raises(ValueError, match="Unknown schema"):
            taxonomy.get_schema_classes("nonexistent")

    def test_unknown_target_schema_raises_on_from_canonical(
        self, taxonomy: LayoutTaxonomy
    ) -> None:
        """ValueError for unknown schema in from_canonical."""
        with pytest.raises(ValueError, match="Unknown target schema"):
            taxonomy.from_canonical("TEXT", "nonexistent")


class TestDocLayNetRoundTrip:
    """Test lossless round-trip for all 11 DocLayNet classes."""

    DOCLAYNET_CLASSES: ClassVar[list[str]] = [
        "Caption",
        "Footnote",
        "Formula",
        "List-item",
        "Page-footer",
        "Page-header",
        "Picture",
        "Section-header",
        "Table",
        "Text",
        "Title",
    ]

    @pytest.mark.parametrize("label", DOCLAYNET_CLASSES)
    def test_roundtrip_lossless(self, taxonomy: LayoutTaxonomy, label: str) -> None:
        """DocLayNet label -> canonical -> DocLayNet is lossless."""
        canonical = taxonomy.to_canonical(label, "doclaynet")
        assert canonical != "UNKNOWN", f"{label} mapped to UNKNOWN"

        result = taxonomy.from_canonical(canonical, "doclaynet")
        assert result.target_label == label
        assert not result.is_lossy
        assert result.confidence == 1.0

    @pytest.mark.parametrize("label", DOCLAYNET_CLASSES)
    def test_convert_roundtrip(self, taxonomy: LayoutTaxonomy, label: str) -> None:
        """Full convert() round-trip for DocLayNet."""
        result = taxonomy.convert(label, "doclaynet", "doclaynet")
        assert result.target_label == label
        assert not result.is_lossy
        assert result.source_label == label
        assert result.source_schema == "doclaynet"


class TestLossyConversion:
    """Test lossy conversion flagging."""

    def test_figure_caption_to_doclaynet_is_lossy(
        self, taxonomy: LayoutTaxonomy
    ) -> None:
        """DocStructBench figure_caption -> DocLayNet Caption (lossy)."""
        result = taxonomy.convert("figure_caption", "docstructbench", "doclaynet")
        assert result.target_label == "Caption"
        assert result.is_lossy
        assert result.source_label == "figure_caption"

    def test_table_caption_to_doclaynet_is_lossy(
        self, taxonomy: LayoutTaxonomy
    ) -> None:
        """DocStructBench table_caption -> DocLayNet Caption (lossy)."""
        result = taxonomy.convert("table_caption", "docstructbench", "doclaynet")
        assert result.target_label == "Caption"
        assert result.is_lossy

    def test_table_footnote_to_doclaynet_is_lossy(
        self, taxonomy: LayoutTaxonomy
    ) -> None:
        """DocStructBench table_footnote -> DocLayNet Footnote (lossy)."""
        result = taxonomy.convert("table_footnote", "docstructbench", "doclaynet")
        assert result.target_label == "Footnote"
        assert result.is_lossy

    def test_d4la_letterhead_to_doclaynet_is_lossy(
        self, taxonomy: LayoutTaxonomy
    ) -> None:
        """D4LA LetterHead -> DocLayNet Page-header (lossy via parent)."""
        result = taxonomy.convert("LetterHead", "d4la", "doclaynet")
        assert result.target_label == "Page-header"
        assert result.is_lossy

    def test_docling_code_to_doclaynet_is_lossy(self, taxonomy: LayoutTaxonomy) -> None:
        """Docling code -> DocLayNet Text (lossy via parent)."""
        result = taxonomy.convert("code", "docling", "doclaynet")
        assert result.target_label == "Text"
        assert result.is_lossy

    def test_docling_chart_to_doclaynet_is_lossy(
        self, taxonomy: LayoutTaxonomy
    ) -> None:
        """Docling chart -> DocLayNet Picture (lossy via parent)."""
        result = taxonomy.convert("chart", "docling", "doclaynet")
        assert result.target_label == "Picture"
        assert result.is_lossy

    def test_abandon_to_doclaynet_unmapped(self, taxonomy: LayoutTaxonomy) -> None:
        """DocStructBench abandon -> ABANDONED has no DocLayNet mapping."""
        result = taxonomy.convert("abandon", "docstructbench", "doclaynet")
        assert result.target_label == "(unmapped)"
        assert result.is_lossy
        assert result.confidence == 0.0

    def test_docling_form_to_doclaynet_unmapped(self, taxonomy: LayoutTaxonomy) -> None:
        """Docling form -> FORM has no DocLayNet mapping."""
        result = taxonomy.convert("form", "docling", "doclaynet")
        assert result.target_label == "(unmapped)"
        assert result.is_lossy


class TestAmbiguousExpansion:
    """Test ambiguous expansion with reduced confidence."""

    def test_caption_to_docstructbench_ambiguous(
        self, taxonomy: LayoutTaxonomy
    ) -> None:
        """DocLayNet Caption -> DocStructBench: multiple candidates."""
        # CAPTION maps to multiple DocStructBench labels via children
        # but directly only if DocStructBench has a direct "Caption" mapping
        # DocStructBench has figure_caption, table_caption, formula_caption
        # which map to child canonical classes, not CAPTION directly.
        # So from_canonical(CAPTION, docstructbench) should be unmapped
        # or find it through a direct mapping.
        result = taxonomy.from_canonical("CAPTION", "docstructbench")
        # CAPTION is not directly in docstructbench, so unmapped
        assert result.is_lossy or result.confidence < 1.0

    def test_d4la_page_footer_ambiguous(self, taxonomy: LayoutTaxonomy) -> None:
        """D4LA has Footer and PageFooter both mapping to PAGE_FOOTER_D4LA."""
        # Both Footer and PageFooter map to PAGE_FOOTER_D4LA
        result = taxonomy.from_canonical("PAGE_FOOTER_D4LA", "d4la")
        # Should resolve (potentially with reduced confidence if multiple)
        assert result.target_label in ("Footer", "PageFooter")


class TestDocStructBenchFullCoverage:
    """Test all 10 DocStructBench classes convert to canonical."""

    DOCSTRUCTBENCH_CLASSES: ClassVar[list[str]] = [
        "title",
        "plain text",
        "abandon",
        "figure",
        "figure_caption",
        "table",
        "table_caption",
        "table_footnote",
        "isolate_formula",
        "formula_caption",
    ]

    @pytest.mark.parametrize("label", DOCSTRUCTBENCH_CLASSES)
    def test_to_canonical(self, taxonomy: LayoutTaxonomy, label: str) -> None:
        """Every DocStructBench class maps to a valid canonical."""
        canonical = taxonomy.to_canonical(label, "docstructbench")
        assert canonical != "UNKNOWN", f"DocStructBench {label!r} mapped to UNKNOWN"

    def test_class_count(self, taxonomy: LayoutTaxonomy) -> None:
        """DocStructBench has exactly 10 classes."""
        classes = taxonomy.get_schema_classes("docstructbench")
        assert len(classes) == 10


class TestPubLayNetFullCoverage:
    """Test all 5 PubLayNet classes convert to canonical."""

    PUBLAYNET_CLASSES: ClassVar[list[str]] = [
        "Text",
        "Title",
        "List",
        "Table",
        "Figure",
    ]

    @pytest.mark.parametrize("label", PUBLAYNET_CLASSES)
    def test_to_canonical(self, taxonomy: LayoutTaxonomy, label: str) -> None:
        """Every PubLayNet class maps to a valid canonical."""
        canonical = taxonomy.to_canonical(label, "publaynet")
        assert canonical != "UNKNOWN", f"PubLayNet {label!r} mapped to UNKNOWN"

    def test_class_count(self, taxonomy: LayoutTaxonomy) -> None:
        """PubLayNet has exactly 5 classes."""
        classes = taxonomy.get_schema_classes("publaynet")
        assert len(classes) == 5


class TestDoclingFullCoverage:
    """Test all 23 Docling classes convert to canonical."""

    DOCLING_CLASSES: ClassVar[list[str]] = [
        "caption",
        "chart",
        "footnote",
        "formula",
        "list_item",
        "page_footer",
        "page_header",
        "picture",
        "section_header",
        "table",
        "text",
        "title",
        "document_index",
        "code",
        "checkbox_selected",
        "checkbox_unselected",
        "form",
        "key_value_region",
        "grading_scale",
        "handwritten_text",
        "empty_value",
        "paragraph",
        "reference",
    ]

    @pytest.mark.parametrize("label", DOCLING_CLASSES)
    def test_to_canonical(self, taxonomy: LayoutTaxonomy, label: str) -> None:
        """Every Docling class maps to a valid canonical."""
        canonical = taxonomy.to_canonical(label, "docling")
        assert canonical != "UNKNOWN", f"Docling {label!r} mapped to UNKNOWN"

    def test_class_count(self, taxonomy: LayoutTaxonomy) -> None:
        """Docling has exactly 23 classes."""
        classes = taxonomy.get_schema_classes("docling")
        assert len(classes) == 23


class TestD4LAFullCoverage:
    """Test all 27 D4LA classes convert to canonical."""

    D4LA_CLASSES: ClassVar[list[str]] = [
        "DocTitle",
        "ListText",
        "LetterHead",
        "Question",
        "RegionList",
        "TableName",
        "FigureName",
        "Footer",
        "Number",
        "ParaTitle",
        "RegionTitle",
        "LetterDear",
        "OtherText",
        "Abstract",
        "Table",
        "Equation",
        "PageHeader",
        "Catalog",
        "ParaText",
        "Date",
        "LetterSign",
        "RegionKV",
        "Author",
        "Figure",
        "Reference",
        "PageFooter",
        "PageNumber",
    ]

    @pytest.mark.parametrize("label", D4LA_CLASSES)
    def test_to_canonical(self, taxonomy: LayoutTaxonomy, label: str) -> None:
        """Every D4LA class maps to a valid canonical."""
        canonical = taxonomy.to_canonical(label, "d4la")
        assert canonical != "UNKNOWN", f"D4LA {label!r} mapped to UNKNOWN"

    def test_class_count(self, taxonomy: LayoutTaxonomy) -> None:
        """D4LA has exactly 27 classes."""
        classes = taxonomy.get_schema_classes("d4la")
        assert len(classes) == 27


class TestDocSynth300KFullCoverage:
    """Test all 10 DocSynth300K classes convert to canonical."""

    def test_matches_docstructbench(self, taxonomy: LayoutTaxonomy) -> None:
        """DocSynth300K has same classes as DocStructBench."""
        dsb_classes = taxonomy.get_schema_classes("docstructbench")
        ds300k_classes = taxonomy.get_schema_classes("docsynth300k")
        assert dsb_classes == ds300k_classes

    def test_class_count(self, taxonomy: LayoutTaxonomy) -> None:
        """DocSynth300K has exactly 10 classes."""
        classes = taxonomy.get_schema_classes("docsynth300k")
        assert len(classes) == 10


class TestAliasNormalization:
    """Test alias resolution for common label variants."""

    def test_list_item_hyphen(self, taxonomy: LayoutTaxonomy) -> None:
        """list-item resolves to DocLayNet List-item."""
        canonical = taxonomy.to_canonical("list-item", "doclaynet")
        assert canonical == "LIST_ITEM"

    def test_listitem_no_separator(self, taxonomy: LayoutTaxonomy) -> None:
        """listitem resolves to DocLayNet List-item."""
        canonical = taxonomy.to_canonical("listitem", "doclaynet")
        assert canonical == "LIST_ITEM"

    def test_list_item_space(self, taxonomy: LayoutTaxonomy) -> None:
        """'list item' resolves to DocLayNet List-item."""
        canonical = taxonomy.to_canonical("list item", "doclaynet")
        assert canonical == "LIST_ITEM"

    def test_page_footer_underscore_docling(self, taxonomy: LayoutTaxonomy) -> None:
        """page_footer resolves in docling context."""
        canonical = taxonomy.to_canonical("page_footer", "docling")
        assert canonical == "PAGE_FOOTER"

    def test_section_header_underscore_docling(self, taxonomy: LayoutTaxonomy) -> None:
        """section_header resolves in docling context."""
        canonical = taxonomy.to_canonical("section_header", "docling")
        assert canonical == "SECTION_HEADER"

    def test_plain_text_underscore(self, taxonomy: LayoutTaxonomy) -> None:
        """plain_text alias resolves to 'plain text'."""
        canonical = taxonomy.to_canonical("plain_text", "docstructbench")
        assert canonical == "PLAIN_TEXT"

    def test_figure_caption_hyphen(self, taxonomy: LayoutTaxonomy) -> None:
        """figure-caption alias resolves."""
        canonical = taxonomy.to_canonical("figure-caption", "docstructbench")
        assert canonical == "FIGURE_CAPTION"


class TestUnknownLabels:
    """Test unknown label handling."""

    def test_unknown_label_returns_unknown(self, taxonomy: LayoutTaxonomy) -> None:
        """Unrecognized label maps to UNKNOWN."""
        canonical = taxonomy.to_canonical("completely_made_up", "doclaynet")
        assert canonical == "UNKNOWN"

    def test_unknown_schema_returns_unknown(self, taxonomy: LayoutTaxonomy) -> None:
        """Unknown schema name maps to UNKNOWN."""
        canonical = taxonomy.to_canonical("Text", "nonexistent_schema")
        assert canonical == "UNKNOWN"

    def test_empty_label_returns_unknown(self, taxonomy: LayoutTaxonomy) -> None:
        """Empty string maps to UNKNOWN."""
        canonical = taxonomy.to_canonical("", "doclaynet")
        assert canonical == "UNKNOWN"


class TestDocLayNetIndexMap:
    """Test build_doclaynet_index_map() output."""

    def test_all_doclaynet_labels_present(self, taxonomy: LayoutTaxonomy) -> None:
        """All 11 DocLayNet native labels map to indices 0-10."""
        idx_map = taxonomy.build_doclaynet_index_map()
        doclaynet_labels = [
            "Caption",
            "Footnote",
            "Formula",
            "List-item",
            "Page-footer",
            "Page-header",
            "Picture",
            "Section-header",
            "Table",
            "Text",
            "Title",
        ]
        for label in doclaynet_labels:
            assert label in idx_map, f"{label} missing from index map"
            assert 0 <= idx_map[label] <= 10

    def test_indices_are_correct(self, taxonomy: LayoutTaxonomy) -> None:
        """DocLayNet indices match config values."""
        idx_map = taxonomy.build_doclaynet_index_map()
        assert idx_map["Caption"] == 0
        assert idx_map["Footnote"] == 1
        assert idx_map["Formula"] == 2
        assert idx_map["List-item"] == 3
        assert idx_map["Page-footer"] == 4
        assert idx_map["Page-header"] == 5
        assert idx_map["Picture"] == 6
        assert idx_map["Section-header"] == 7
        assert idx_map["Table"] == 8
        assert idx_map["Text"] == 9
        assert idx_map["Title"] == 10

    def test_docstructbench_labels_have_indices(self, taxonomy: LayoutTaxonomy) -> None:
        """DocStructBench labels map to DocLayNet indices."""
        idx_map = taxonomy.build_doclaynet_index_map()
        # "plain text" -> TEXT -> index 9
        assert idx_map["plain text"] == 9
        # "figure" -> PICTURE -> index 6
        assert idx_map["figure"] == 6
        # "table" -> TABLE -> index 8
        assert idx_map["table"] == 8
        # "figure_caption" -> CAPTION -> index 0
        assert idx_map["figure_caption"] == 0

    def test_aliases_included_in_index_map(self, taxonomy: LayoutTaxonomy) -> None:
        """Alias labels are also in the index map."""
        idx_map = taxonomy.build_doclaynet_index_map()
        # plain_text alias -> "plain text" -> PLAIN_TEXT -> TEXT -> 9
        assert idx_map.get("plain_text") == 9

    def test_canonical_names_in_index_map(self, taxonomy: LayoutTaxonomy) -> None:
        """Canonical class names are also mapped."""
        idx_map = taxonomy.build_doclaynet_index_map()
        assert idx_map["CAPTION"] == 0
        assert idx_map["TEXT"] == 9
        assert idx_map["TABLE"] == 8
        assert idx_map["PICTURE"] == 6


class TestMaskIndexMap:
    """Test build_mask_index_map() for different schemas."""

    def test_doclaynet_mask_map_has_11_entries(self, taxonomy: LayoutTaxonomy) -> None:
        """DocLayNet mask map has 11 entries."""
        mask_map = taxonomy.build_mask_index_map("doclaynet")
        assert len(mask_map) == 11

    def test_docling_mask_map_has_23_entries(self, taxonomy: LayoutTaxonomy) -> None:
        """Docling mask map has 23 entries."""
        mask_map = taxonomy.build_mask_index_map("docling")
        assert len(mask_map) == 23

    def test_d4la_mask_map_has_27_entries(self, taxonomy: LayoutTaxonomy) -> None:
        """D4LA mask map has 27 entries."""
        mask_map = taxonomy.build_mask_index_map("d4la")
        assert len(mask_map) == 27

    def test_mask_indices_contiguous(self, taxonomy: LayoutTaxonomy) -> None:
        """Mask indices are contiguous 0..N-1."""
        for schema in taxonomy.get_available_schemas():
            mask_map = taxonomy.build_mask_index_map(schema)
            indices = sorted(mask_map.values())
            assert indices == list(range(len(indices))), (
                f"{schema} indices not contiguous"
            )

    def test_mask_channel_count_matches_map(self, taxonomy: LayoutTaxonomy) -> None:
        """get_mask_channel_count matches map length for all schemas."""
        for schema in taxonomy.get_available_schemas():
            count = taxonomy.get_mask_channel_count(schema)
            mask_map = taxonomy.build_mask_index_map(schema)
            assert count == len(mask_map)


class TestToDocLayNet:
    """Test to_doclaynet() and to_doclaynet_index()."""

    def test_doclaynet_canonical_returns_self(self, taxonomy: LayoutTaxonomy) -> None:
        """DocLayNet top-level canonical -> same DocLayNet label."""
        assert taxonomy.to_doclaynet("CAPTION") == "Caption"
        assert taxonomy.to_doclaynet("TEXT") == "Text"
        assert taxonomy.to_doclaynet("TABLE") == "Table"

    def test_child_walks_to_parent(self, taxonomy: LayoutTaxonomy) -> None:
        """Child canonical class walks to DocLayNet parent."""
        assert taxonomy.to_doclaynet("FIGURE_CAPTION") == "Caption"
        assert taxonomy.to_doclaynet("CODE") == "Text"
        assert taxonomy.to_doclaynet("CHART") == "Picture"
        assert taxonomy.to_doclaynet("EQUATION") == "Formula"
        assert taxonomy.to_doclaynet("LETTERHEAD") == "Page-header"
        assert taxonomy.to_doclaynet("PAGE_NUMBER") == "Page-footer"

    def test_unmappable_returns_unknown(self, taxonomy: LayoutTaxonomy) -> None:
        """Classes without DocLayNet parent return UNKNOWN."""
        assert taxonomy.to_doclaynet("FORM") == "UNKNOWN"
        assert taxonomy.to_doclaynet("ABANDONED") == "UNKNOWN"
        assert taxonomy.to_doclaynet("UNKNOWN") == "UNKNOWN"

    def test_to_doclaynet_index_values(self, taxonomy: LayoutTaxonomy) -> None:
        """to_doclaynet_index returns correct values."""
        assert taxonomy.to_doclaynet_index("CAPTION") == 0
        assert taxonomy.to_doclaynet_index("TEXT") == 9
        assert taxonomy.to_doclaynet_index("TITLE") == 10
        # Child classes inherit parent index
        assert taxonomy.to_doclaynet_index("FIGURE_CAPTION") == 0
        assert taxonomy.to_doclaynet_index("CODE") == 9

    def test_to_doclaynet_index_none_for_unmappable(
        self, taxonomy: LayoutTaxonomy
    ) -> None:
        """to_doclaynet_index returns None for unmappable classes."""
        assert taxonomy.to_doclaynet_index("FORM") is None
        assert taxonomy.to_doclaynet_index("ABANDONED") is None
        assert taxonomy.to_doclaynet_index("NONEXISTENT") is None


class TestConvertAnnotations:
    """Test batch annotation conversion."""

    def test_batch_conversion(self, taxonomy: LayoutTaxonomy) -> None:
        """Batch convert annotations preserves extra fields."""
        anns = [
            {"label": "figure_caption", "bbox": [0, 0, 100, 50]},
            {"label": "table", "bbox": [10, 10, 200, 100]},
        ]
        results = taxonomy.convert_annotations(anns, "docstructbench", "doclaynet")
        assert len(results) == 2
        assert results[0]["label"] == "Caption"
        assert results[0]["bbox"] == [0, 0, 100, 50]
        assert results[0]["canonical_class"] == "FIGURE_CAPTION"
        assert results[0]["is_lossy"] is True

        assert results[1]["label"] == "Table"
        assert results[1]["bbox"] == [10, 10, 200, 100]
        assert results[1]["canonical_class"] == "TABLE"

    def test_empty_annotations(self, taxonomy: LayoutTaxonomy) -> None:
        """Empty list returns empty list."""
        assert taxonomy.convert_annotations([], "doclaynet", "docling") == []


class TestConversionResult:
    """Test ConversionResult dataclass."""

    def test_frozen(self) -> None:
        """ConversionResult is immutable."""
        result = ConversionResult(
            canonical_class="TEXT",
            target_label="Text",
            is_lossy=False,
            loss_description=None,
            confidence=1.0,
            source_schema="doclaynet",
            source_label="Text",
        )
        with pytest.raises(AttributeError):
            result.canonical_class = "TABLE"  # type: ignore[misc]


class TestReload:
    """Test hot-reload functionality."""

    def test_reload_clears_caches(self, taxonomy: LayoutTaxonomy) -> None:
        """Reload clears cached lookups."""
        # Warm cache
        taxonomy.to_canonical("Text", "doclaynet")
        taxonomy.to_doclaynet("TEXT")

        # Reload
        taxonomy.reload()

        # Should still work after reload
        assert taxonomy.to_canonical("Text", "doclaynet") == "TEXT"
        assert taxonomy.to_doclaynet("TEXT") == "Text"


class TestSingleton:
    """Test module-level singleton."""

    def test_get_default_taxonomy(self) -> None:
        """Singleton returns same instance."""
        reset_default_taxonomy()
        t1 = get_default_taxonomy()
        t2 = get_default_taxonomy()
        assert t1 is t2

    def test_reset_creates_new_instance(self) -> None:
        """Reset forces new instance creation."""
        reset_default_taxonomy()
        t1 = get_default_taxonomy()
        reset_default_taxonomy()
        t2 = get_default_taxonomy()
        assert t1 is not t2


class TestCrossSchemaConversions:
    """Test conversions between non-DocLayNet schemas."""

    def test_docstructbench_to_publaynet(self, taxonomy: LayoutTaxonomy) -> None:
        """DocStructBench figure -> PubLayNet Figure."""
        result = taxonomy.convert("figure", "docstructbench", "publaynet")
        assert result.target_label == "Figure"

    def test_docling_to_d4la_table(self, taxonomy: LayoutTaxonomy) -> None:
        """Docling table -> D4LA Table."""
        result = taxonomy.convert("table", "docling", "d4la")
        assert result.target_label == "Table"

    def test_d4la_to_docling_reference(self, taxonomy: LayoutTaxonomy) -> None:
        """D4LA Reference -> Docling reference (via REFERENCE canonical)."""
        result = taxonomy.convert("Reference", "d4la", "docling")
        assert result.target_label == "reference"
        assert not result.is_lossy

    def test_d4la_abstract_to_docling(self, taxonomy: LayoutTaxonomy) -> None:
        """D4LA Abstract -> Docling text (lossy, via TEXT parent)."""
        result = taxonomy.convert("Abstract", "d4la", "docling")
        assert result.target_label == "text"
        assert result.is_lossy
