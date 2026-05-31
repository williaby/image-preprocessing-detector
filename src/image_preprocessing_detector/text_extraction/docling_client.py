"""Docling REST API client for document text extraction.

Wraps the Docling server's ``POST /v1/convert/file`` endpoint to convert
documents (PDF, images) into structured text, markdown, and JSON output.

Accepts optional ``DoclingRoutingParams`` from the routing engine to
configure OCR settings, pipeline selection, and table extraction mode.

Example:
    >>> from image_preprocessing_detector.text_extraction import DoclingClient
    >>> client = DoclingClient(host="192.168.1.209", port=5001)
    >>> result = client.convert_file(Path("document.pdf"))
    >>> print(result.text[:100])
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import httpx

from image_preprocessing_detector.utils import get_logger

if TYPE_CHECKING:
    from image_preprocessing_detector.schema import DoclingRoutingParams

logger = get_logger(__name__)

# Default configuration — host is read from DOCLING_HOST env var at import time.
# The fallback IP is a LAN-local Docling server; override via DOCLING_HOST for
# production or non-local deployments.
_FALLBACK_HOST = (
    "192.168.1.209"  # NOSONAR (S1313) — LAN-local default, overridden by env
)
DEFAULT_HOST = os.environ.get("DOCLING_HOST", _FALLBACK_HOST)
DEFAULT_PORT = 5001
DEFAULT_TIMEOUT = 300.0  # 5 minutes for large documents


class DoclingServerError(Exception):
    """Raised when the Docling server returns an error or is unreachable."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


@dataclass(frozen=True)
class DoclingResult:
    """Result from Docling document conversion.

    Attributes:
        text: Extracted plain text content.
        markdown: Markdown-formatted content (if available).
        json_content: Raw JSON response from Docling.
        page_count: Number of pages detected.
        tables_found: Number of tables extracted.
        processing_time_ms: Server-side processing time in milliseconds.
        success: Whether the conversion succeeded.
        error: Error message if conversion failed.
        source_path: Path to the source document.
    """

    text: str
    markdown: str
    json_content: dict[str, Any]
    page_count: int
    tables_found: int
    processing_time_ms: float
    success: bool
    error: str | None = None
    source_path: str = ""


def _routing_params_to_form_data(
    params: DoclingRoutingParams | None,
) -> dict[str, str]:
    """Convert DoclingRoutingParams to REST API form data fields.

    Args:
        params (DoclingRoutingParams | None): Routing params from the routing engine, or None for defaults.

    Returns:
        dict[str, str]: Dictionary of form field names to string values."""
    data: dict[str, str] = {"output_format": "json"}

    if params is None:
        return data

    # Pipeline selection
    if params.pipeline != "standard":
        data["pipeline"] = params.pipeline

    # VLM model
    if params.vlm_model:
        data["vlm_model"] = params.vlm_model

    # OCR settings
    if not params.ocr_enabled:
        data["ocr"] = "false"
    elif params.ocr_force:
        data["force_ocr"] = "true"

    if params.ocr_engine != "auto":
        data["ocr_engine"] = params.ocr_engine

    if params.ocr_lang:
        data["ocr_lang"] = params.ocr_lang

    # Table settings
    if not params.tables_enabled:
        data["tables"] = "false"
    else:
        data["table_mode"] = params.table_mode

    return data


@dataclass
class DoclingClient:
    """HTTP client for the Docling REST API.

    Attributes:
        host: Docling server hostname or IP.
        port: Docling server port.
        timeout: Request timeout in seconds.
    """

    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    timeout: float = DEFAULT_TIMEOUT
    _client: httpx.Client | None = field(default=None, repr=False)

    @property
    def base_url(self) -> str:
        """Base URL for the Docling server.

        Uses HTTP intentionally: the Docling server runs on a private LAN
        segment without TLS termination.  For deployments that expose the
        service over a public network, place it behind an HTTPS reverse proxy.
        """
        return f"http://{self.host}:{self.port}"  # NOSONAR (S5332) — private LAN service; see docstring

    def _get_client(self) -> httpx.Client:
        """Get or create the httpx client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client

    def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None and not self._client.is_closed:
            self._client.close()
            self._client = None

    def health_check(self) -> bool:
        """Check if the Docling server is reachable.

        Returns:
            bool: True if the server responds to health check."""
        try:
            client = self._get_client()
            response = client.get("/health", timeout=5.0)
        except (httpx.ConnectError, httpx.TimeoutException):
            return False
        else:
            return bool(response.status_code == 200)

    def convert_file(
        self,
        file_path: Path,
        routing_params: DoclingRoutingParams | None = None,
    ) -> DoclingResult:
        """Convert a document file via the Docling REST API.

        Args:
            file_path (Path): Path to the document (PDF, image, etc.).
            routing_params (DoclingRoutingParams | None): Optional routing params from DoclingRoutingEngine.

        Returns:
            DoclingResult: DoclingResult with extracted text, markdown, and metadata.

        Raises:
            DoclingServerError: If the server returns an error or is unreachable.
            FileNotFoundError: If the input file does not exist.
        """
        if not file_path.exists():
            msg = f"File not found: {file_path}"
            raise FileNotFoundError(msg)

        start = time.perf_counter()
        client = self._get_client()
        form_data = _routing_params_to_form_data(routing_params)

        logger.info(
            "docling_convert_start",
            file=str(file_path),
            pipeline=form_data.get("pipeline", "standard"),
        )

        try:
            file_content = file_path.read_bytes()
            response = client.post(
                "/v1/convert/file",
                files={"file": (file_path.name, file_content)},
                data=form_data,
            )
        except httpx.ConnectError as e:
            elapsed = (time.perf_counter() - start) * 1000
            msg = f"Cannot connect to Docling server at {self.base_url}: {e}"
            raise DoclingServerError(msg) from e
        except httpx.TimeoutException as e:
            elapsed = (time.perf_counter() - start) * 1000
            msg = f"Docling server timeout after {elapsed:.0f}ms: {e}"
            raise DoclingServerError(msg) from e

        elapsed_ms = (time.perf_counter() - start) * 1000

        if response.status_code != 200:
            error_text = response.text[:500]
            msg = f"Docling server returned HTTP {response.status_code}: {error_text}"
            raise DoclingServerError(msg, status_code=response.status_code)

        result = response.json()
        return self._parse_response(result, file_path, elapsed_ms)

    @staticmethod
    def _parse_response(
        result: dict[str, Any],
        file_path: Path,
        elapsed_ms: float,
    ) -> DoclingResult:
        """Parse the Docling JSON response into a DoclingResult.

        Args:
            result (dict[str, Any]): Raw JSON response from the server.
            file_path (Path): Source file path for metadata.
            elapsed_ms (float): Client-side elapsed time.

        Returns:
            DoclingResult: Structured DoclingResult."""
        doc = result.get("document", {})

        # Extract text content
        text = doc.get("text_content", "") or doc.get("md_content", "")
        markdown = doc.get("md_content", "") or ""

        # Parse structured content
        raw_json: object = doc.get("json_content", {})
        parsed_json: dict[str, Any] = (
            cast("dict[str, Any]", raw_json) if isinstance(raw_json, dict) else {}
        )
        pages: list[Any] = parsed_json.get("pages", []) if parsed_json else []
        tables: list[Any] = parsed_json.get("tables", []) if parsed_json else []

        server_time = result.get("processing_time", elapsed_ms)
        is_success = result.get("status") == "success"

        page_count = len(pages) if pages else 1
        table_count = len(tables)

        logger.info(
            "docling_convert_complete",
            file=str(file_path),
            success=is_success,
            pages=page_count,
            tables=table_count,
            time_ms=f"{elapsed_ms:.0f}",
        )

        return DoclingResult(
            text=text,
            markdown=markdown,
            json_content=parsed_json,
            page_count=page_count,
            tables_found=table_count,
            processing_time_ms=server_time,
            success=is_success,
            error=result.get("error"),
            source_path=str(file_path),
        )

    def __enter__(self) -> DoclingClient:
        """Support context manager usage."""
        return self

    def __exit__(self, *args: object) -> None:
        """Close client on context exit."""
        self.close()
