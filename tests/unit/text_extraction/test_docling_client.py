"""Unit tests for DoclingClient."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from image_preprocessing_detector.schema import DoclingRoutingParams
from image_preprocessing_detector.text_extraction.docling_client import (
    DoclingClient,
    DoclingResult,
    DoclingServerError,
    _routing_params_to_form_data,
)

# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------


@pytest.fixture
def mock_response_success() -> dict:
    """Simulated successful Docling response."""
    return {
        "status": "success",
        "processing_time": 1234.5,
        "document": {
            "text_content": "Hello world extracted text",
            "md_content": "# Hello\n\nWorld extracted text",
            "json_content": {
                "pages": [{"page_num": 1}],
                "tables": [{"id": "t1", "cells": []}],
            },
        },
    }


@pytest.fixture
def tmp_pdf(tmp_path: Path) -> Path:
    """Create a temporary file for testing."""
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake content")
    return pdf


# -----------------------------------------------------------------------
# _routing_params_to_form_data
# -----------------------------------------------------------------------


class TestRoutingParamsToFormData:
    """Tests for _routing_params_to_form_data."""

    def test_none_params(self) -> None:
        result = _routing_params_to_form_data(None)
        assert result == {"output_format": "json"}

    def test_default_params(self) -> None:
        params = DoclingRoutingParams()
        result = _routing_params_to_form_data(params)
        assert result["output_format"] == "json"
        # Default pipeline is standard, should not be in form data
        assert "pipeline" not in result

    def test_vlm_pipeline(self) -> None:
        params = DoclingRoutingParams(
            pipeline="vlm",
            vlm_model="deepseekocr_ollama",
        )
        result = _routing_params_to_form_data(params)
        assert result["pipeline"] == "vlm"
        assert result["vlm_model"] == "deepseekocr_ollama"

    def test_ocr_disabled(self) -> None:
        params = DoclingRoutingParams(ocr_enabled=False)
        result = _routing_params_to_form_data(params)
        assert result["ocr"] == "false"

    def test_ocr_forced(self) -> None:
        params = DoclingRoutingParams(ocr_force=True)
        result = _routing_params_to_form_data(params)
        assert result["force_ocr"] == "true"

    def test_custom_engine_and_lang(self) -> None:
        params = DoclingRoutingParams(
            ocr_engine="tesseract",
            ocr_lang="ch",
        )
        result = _routing_params_to_form_data(params)
        assert result["ocr_engine"] == "tesseract"
        assert result["ocr_lang"] == "ch"

    def test_tables_disabled(self) -> None:
        params = DoclingRoutingParams(tables_enabled=False)
        result = _routing_params_to_form_data(params)
        assert result["tables"] == "false"

    def test_table_mode(self) -> None:
        params = DoclingRoutingParams(table_mode="fast")
        result = _routing_params_to_form_data(params)
        assert result["table_mode"] == "fast"


# -----------------------------------------------------------------------
# DoclingResult
# -----------------------------------------------------------------------


class TestDoclingResult:
    """Tests for DoclingResult dataclass."""

    def test_success_result(self) -> None:
        result = DoclingResult(
            text="Hello",
            markdown="# Hello",
            json_content={"pages": [{}]},
            page_count=1,
            tables_found=0,
            processing_time_ms=100.0,
            success=True,
        )
        assert result.success
        assert result.text == "Hello"
        assert result.error is None

    def test_error_result(self) -> None:
        result = DoclingResult(
            text="",
            markdown="",
            json_content={},
            page_count=0,
            tables_found=0,
            processing_time_ms=50.0,
            success=False,
            error="Parse failed",
        )
        assert not result.success
        assert result.error == "Parse failed"


# -----------------------------------------------------------------------
# DoclingClient
# -----------------------------------------------------------------------


class TestDoclingClient:
    """Tests for DoclingClient."""

    def test_base_url(self) -> None:
        client = DoclingClient(host="localhost", port=8080)
        assert client.base_url == "http://localhost:8080"

    def test_file_not_found(self) -> None:
        client = DoclingClient()
        with pytest.raises(FileNotFoundError, match="File not found"):
            client.convert_file(Path("/nonexistent/file.pdf"))

    @patch("image_preprocessing_detector.text_extraction.docling_client.httpx.Client")
    def test_convert_file_success(
        self,
        mock_client_cls: MagicMock,
        tmp_pdf: Path,
        mock_response_success: dict,
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_success

        mock_client = MagicMock()
        mock_client.is_closed = False
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        client = DoclingClient(host="test", port=5001)
        client._client = mock_client

        result = client.convert_file(tmp_pdf)

        assert result.success
        assert result.text == "Hello world extracted text"
        assert result.markdown == "# Hello\n\nWorld extracted text"
        assert result.page_count == 1
        assert result.tables_found == 1
        assert result.processing_time_ms == 1234.5

    @patch("image_preprocessing_detector.text_extraction.docling_client.httpx.Client")
    def test_convert_file_http_error(
        self,
        mock_client_cls: MagicMock,
        tmp_pdf: Path,
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_client = MagicMock()
        mock_client.is_closed = False
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        client = DoclingClient(host="test", port=5001)
        client._client = mock_client

        with pytest.raises(DoclingServerError, match="HTTP 500"):
            client.convert_file(tmp_pdf)

    @patch("image_preprocessing_detector.text_extraction.docling_client.httpx.Client")
    def test_convert_file_connection_error(
        self,
        mock_client_cls: MagicMock,
        tmp_pdf: Path,
    ) -> None:
        mock_client = MagicMock()
        mock_client.is_closed = False
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        mock_client_cls.return_value = mock_client

        client = DoclingClient(host="test", port=5001)
        client._client = mock_client

        with pytest.raises(DoclingServerError, match="Cannot connect"):
            client.convert_file(tmp_pdf)

    @patch("image_preprocessing_detector.text_extraction.docling_client.httpx.Client")
    def test_convert_file_with_routing_params(
        self,
        mock_client_cls: MagicMock,
        tmp_pdf: Path,
        mock_response_success: dict,
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_success

        mock_client = MagicMock()
        mock_client.is_closed = False
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        client = DoclingClient(host="test", port=5001)
        client._client = mock_client

        params = DoclingRoutingParams(
            pipeline="vlm",
            ocr_engine="tesseract",
            table_mode="fast",
        )
        result = client.convert_file(tmp_pdf, routing_params=params)

        assert result.success
        # Verify the form data was passed correctly
        call_kwargs = mock_client.post.call_args
        form_data = call_kwargs.kwargs.get("data", {})
        assert form_data["pipeline"] == "vlm"
        assert form_data["ocr_engine"] == "tesseract"
        assert form_data["table_mode"] == "fast"

    def test_context_manager(self) -> None:
        with DoclingClient(host="test", port=5001) as client:
            assert client.host == "test"
        # Client should be cleaned up

    def test_parse_response_empty_json_content(self) -> None:
        result = DoclingClient._parse_response(
            {"status": "success", "document": {"text_content": "hi"}},
            Path("test.pdf"),
            100.0,
        )
        assert result.text == "hi"
        assert result.json_content == {}
        assert result.page_count == 1
        assert result.tables_found == 0
