"""Unit tests for OCR quality proxy metrics."""

from __future__ import annotations

import pytest

from image_preprocessing_detector.schema_utils.ocr_quality_proxy import (
    OcrProxyMetrics,
    compute_all_proxies,
    compute_cjk_latin_consistency,
    compute_layout_text_agreement,
    compute_line_regularity,
    compute_ocr_completeness,
    compute_ori_res_text_delta,
    compute_siglip2_ocr_agreement,
    compute_text_yield,
    compute_valid_char_rate,
    compute_word_density,
)

# -----------------------------------------------------------------------
# Group A: Text Extraction Volume
# -----------------------------------------------------------------------


class TestTextYield:
    """Tests for compute_text_yield."""

    def test_basic_calculation(self) -> None:
        result = compute_text_yield("Hello world", 1000, 1000)
        # 10 non-space chars / 1.0 megapixel = 10.0
        assert result == pytest.approx(10.0, abs=0.1)

    def test_zero_area(self) -> None:
        assert compute_text_yield("text", 0, 100) == 0.0

    def test_empty_text(self) -> None:
        assert compute_text_yield("", 1000, 1000) == 0.0

    def test_cjk_text(self) -> None:
        cjk = "测试文本内容"  # 6 chars
        result = compute_text_yield(cjk, 1000, 1000)
        assert result == pytest.approx(6.0, abs=0.1)

    def test_whitespace_excluded(self) -> None:
        result = compute_text_yield("a b c d e", 1000, 1000)
        # 5 non-space chars / 1.0 megapixel
        assert result == pytest.approx(5.0, abs=0.1)


class TestWordDensity:
    """Tests for compute_word_density."""

    def test_basic(self) -> None:
        result = compute_word_density("hello world foo", 1000.0)
        assert result == pytest.approx(3.0 / 1000.0)

    def test_zero_area(self) -> None:
        assert compute_word_density("hello", 0.0) == 0.0

    def test_empty_text(self) -> None:
        assert compute_word_density("", 1000.0) == 0.0


class TestOcrCompleteness:
    """Tests for compute_ocr_completeness."""

    def test_well_populated(self) -> None:
        # 500 chars across 10 regions = 50 chars/region = saturated
        assert compute_ocr_completeness(500, 10) == pytest.approx(1.0)

    def test_sparse(self) -> None:
        # 50 chars across 10 regions = 5 chars/region = 0.1
        assert compute_ocr_completeness(50, 10) == pytest.approx(0.1)

    def test_no_regions_with_text(self) -> None:
        assert compute_ocr_completeness(100, 0) == 1.0

    def test_no_regions_no_text(self) -> None:
        assert compute_ocr_completeness(0, 0) == 0.0

    def test_no_text_with_regions(self) -> None:
        assert compute_ocr_completeness(0, 5) == 0.0


# -----------------------------------------------------------------------
# Group B: Intra-Document Coherence
# -----------------------------------------------------------------------


class TestCjkLatinConsistency:
    """Tests for compute_cjk_latin_consistency."""

    def test_single_block(self) -> None:
        # Pure ASCII -> single Unicode block -> entropy 0
        assert compute_cjk_latin_consistency("abcdef") == 0.0

    def test_mixed_blocks(self) -> None:
        # Mix of CJK + Latin -> higher entropy
        result = compute_cjk_latin_consistency("Hello测试World世界")
        assert 0.0 < result < 1.0

    def test_empty(self) -> None:
        assert compute_cjk_latin_consistency("") == 0.0

    def test_single_char(self) -> None:
        assert compute_cjk_latin_consistency("a") == 0.0

    def test_whitespace_only(self) -> None:
        assert compute_cjk_latin_consistency("   \n\t  ") == 0.0


class TestLineRegularity:
    """Tests for compute_line_regularity."""

    def test_uniform_lines(self) -> None:
        text = "abcdefghij\n" * 10
        result = compute_line_regularity(text)
        assert result == pytest.approx(1.0, abs=0.01)

    def test_erratic_lines(self) -> None:
        text = "a\n" + "b" * 200 + "\nc\n" + "d" * 300 + "\ne"
        result = compute_line_regularity(text)
        assert result < 0.5

    def test_few_lines(self) -> None:
        # Less than 3 non-empty lines -> 0.5 default
        assert compute_line_regularity("hello\nworld") == 0.5

    def test_empty(self) -> None:
        assert compute_line_regularity("") == 0.5


class TestValidCharRate:
    """Tests for compute_valid_char_rate."""

    def test_clean_latin(self) -> None:
        result = compute_valid_char_rate("Hello, World! 123.")
        assert result > 0.9

    def test_clean_cjk(self) -> None:
        result = compute_valid_char_rate("测试文本内容")
        assert result == pytest.approx(1.0)

    def test_garbled(self) -> None:
        # Control characters and replacement chars
        garbled = "\x00\x01\x02\x03\ufffd\ufffd"
        result = compute_valid_char_rate(garbled)
        assert result < 0.5

    def test_empty(self) -> None:
        assert compute_valid_char_rate("") == 0.0

    def test_mixed_valid_invalid(self) -> None:
        # 3 valid + 3 invalid
        text = "abc\x00\x01\x02"
        result = compute_valid_char_rate(text)
        assert result == pytest.approx(0.5)


# -----------------------------------------------------------------------
# Group C: Cross-Signal Agreement
# -----------------------------------------------------------------------


class TestLayoutTextAgreement:
    """Tests for compute_layout_text_agreement."""

    def test_no_text_no_layout(self) -> None:
        assert compute_layout_text_agreement(0, 0, 0.0) == 1.0

    def test_text_no_layout(self) -> None:
        assert compute_layout_text_agreement(100, 0, 0.0) == 0.5

    def test_good_agreement(self) -> None:
        # 10 regions, moderate text area ratio, appropriate char count
        # expected = 10 * 100 * max(0.1, 0.5*10) = 10 * 100 * 5 = 5000
        # ratio = 5000/5000 = 1.0 -> exp(-|log(1)|) = 1.0
        result = compute_layout_text_agreement(5000, 10, 0.5)
        assert result > 0.9

    def test_poor_agreement(self) -> None:
        # Many regions but almost no text
        result = compute_layout_text_agreement(5, 50, 0.5)
        assert result < 0.5


class TestOriResTextDelta:
    """Tests for compute_ori_res_text_delta."""

    def test_improvement(self) -> None:
        # Enhanced has more text
        result = compute_ori_res_text_delta(200.0, 100.0)
        assert result > 0.0

    def test_degradation(self) -> None:
        result = compute_ori_res_text_delta(50.0, 100.0)
        assert result < 0.0

    def test_zero_original(self) -> None:
        # Should not divide by zero
        result = compute_ori_res_text_delta(100.0, 0.0)
        assert result > 0.0


class TestSiglip2OcrAgreement:
    """Tests for compute_siglip2_ocr_agreement."""

    def test_perfect_agreement(self) -> None:
        result = compute_siglip2_ocr_agreement(0.5, 50.0, 100.0)
        assert result == pytest.approx(1.0)

    def test_disagreement(self) -> None:
        # IQA says high quality, but text yield is low
        result = compute_siglip2_ocr_agreement(0.9, 10.0, 100.0)
        assert result < 0.5

    def test_zero_max(self) -> None:
        assert compute_siglip2_ocr_agreement(0.5, 10.0, 0.0) == 0.5


# -----------------------------------------------------------------------
# Integration: compute_all_proxies
# -----------------------------------------------------------------------


class TestComputeAllProxies:
    """Tests for compute_all_proxies convenience function."""

    def test_basic_without_optional(self) -> None:
        result = compute_all_proxies(
            text="Hello world testing OCR output quality",
            image_width=2000,
            image_height=3000,
            layout_text_region_count=5,
            text_region_area_px=50000.0,
            layout_text_area_ratio=0.3,
        )
        assert isinstance(result, OcrProxyMetrics)
        assert result.text_yield > 0.0
        assert result.word_density > 0.0
        assert 0.0 <= result.ocr_completeness <= 1.0
        assert 0.0 <= result.cjk_latin_consistency <= 1.0
        assert 0.0 <= result.line_regularity <= 1.0
        assert 0.0 <= result.valid_char_rate <= 1.0
        assert 0.0 <= result.layout_text_agreement <= 1.0
        assert result.ori_res_text_delta is None
        assert result.siglip2_ocr_agreement is None

    def test_with_optional_params(self) -> None:
        result = compute_all_proxies(
            text="Hello world",
            image_width=1000,
            image_height=1000,
            layout_text_region_count=3,
            text_region_area_px=10000.0,
            layout_text_area_ratio=0.2,
            ori_text_yield=5.0,
            iqa_overall_mu=0.6,
            text_yield_max=20.0,
        )
        assert result.ori_res_text_delta is not None
        assert result.siglip2_ocr_agreement is not None

    def test_to_dict(self) -> None:
        result = compute_all_proxies(
            text="Test",
            image_width=1000,
            image_height=1000,
            layout_text_region_count=1,
            text_region_area_px=5000.0,
            layout_text_area_ratio=0.1,
        )
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "text_yield" in d
        assert "ori_res_text_delta" in d
        assert d["ori_res_text_delta"] is None

    def test_empty_text(self) -> None:
        result = compute_all_proxies(
            text="",
            image_width=1000,
            image_height=1000,
            layout_text_region_count=0,
            text_region_area_px=0.0,
            layout_text_area_ratio=0.0,
        )
        assert result.text_yield == 0.0
        assert result.word_density == 0.0
        assert result.valid_char_rate == 0.0
