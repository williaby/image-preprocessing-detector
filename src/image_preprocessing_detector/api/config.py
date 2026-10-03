"""API configuration settings.

Provides configuration for:
- CORS settings
- Rate limiting
- API versioning
- Device preferences
"""

from functools import lru_cache
from typing import Any

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class APISettings(BaseSettings):
    """API configuration settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="IMGPREP_API_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API metadata
    title: str = Field(
        default="Image Preprocessing Detector API",
        description="API title for OpenAPI docs",
    )
    description: str = Field(
        default=(
            "Front door for the RAG document pipeline. Accepts raw documents "
            "(PDF, PNG, JPEG, TIFF, WebP), assesses image quality, and returns "
            "a per-page quality summary plus an OCR routing recommendation.\n\n"
            "## Features\n\n"
            "- **Classical IQA**: blur, noise, and contrast detectors per page\n"
            "- **Document Quality Score (DQS)**: degradation score (the "
            "structural complexity component is currently a fixed placeholder)\n"
            "- **PDF classification**: image_only / born_digital / hybrid\n"
            "- **Routing**: `ocr_fast`, `ocr_advanced` or `vision_structured`, "
            "chosen from the degradation score\n"
            "- **Async batch**: submit-and-poll jobs for multi-file ingestion\n\n"
            "The HTTP API exposes a subset of the full preprocessing pipeline: "
            "geometric and quality corrections and the ML teacher/student IQA "
            "models are not yet applied by these endpoints.\n\n"
            "See the project repository (`docs/api/`) for further reference "
            "material."
        ),
        description="API description for OpenAPI docs",
    )
    version: str = Field(
        default="0.1.0",
        description="API version",
    )
    contact_name: str = Field(
        default="Image Preprocessing Detector Maintainers",
        description="OpenAPI contact name",
    )
    contact_url: str = Field(
        default="https://github.com/williaby/image-preprocessing-detector",
        description="OpenAPI contact URL",
    )
    contact_email: str = Field(
        default="",
        description=(
            "OpenAPI contact email. Leave empty to omit `email` from the "
            "published `info.contact` object; preferred over a placeholder."
        ),
    )
    license_name: str = Field(
        default="CC-BY-SA-4.0",
        description="OpenAPI license name (SPDX identifier of the project license)",
    )
    license_url: str = Field(
        default="https://creativecommons.org/licenses/by-sa/4.0/",
        description="OpenAPI license URL",
    )
    server_url: str = Field(
        default="http://localhost:8000",
        description=(
            "Base URL advertised in the OpenAPI `servers` list (used by "
            "Swagger UI Try-it-out). Set this to the public URL of the "
            "deployment. Leave empty to omit `servers`, in which case "
            "OpenAPI clients default to the host serving the document."
        ),
    )
    server_description: str = Field(
        default="Local development server",
        description="Description of the OpenAPI `servers` entry",
    )
    terms_of_service: str = Field(
        default="",
        description=(
            "OpenAPI terms-of-service URL. Leave empty to omit "
            "`info.termsOfService` from the published schema; do not point "
            "this at the project LICENSE."
        ),
    )

    # CORS settings
    cors_enabled: bool = Field(
        default=True,
        description="Enable CORS middleware",
    )
    cors_origins: list[str] = Field(
        default=[],
        description="Allowed CORS origins",
    )
    cors_allow_credentials: bool = Field(
        default=False,
        description="Allow credentials in CORS requests",
    )
    cors_allow_methods: list[str] = Field(
        default=["*"],
        description="Allowed HTTP methods for CORS",
    )
    cors_allow_headers: list[str] = Field(
        default=["*"],
        description="Allowed headers for CORS",
    )

    @model_validator(mode="after")
    def validate_cors_credentials_with_origins(self) -> "APISettings":
        """Reject wildcard origins when credentials are enabled.

        Browsers silently ignore ``Access-Control-Allow-Origin: *`` when
        credentials are included in a request, so the combination of
        ``allow_credentials=True`` and ``allow_origins=["*"]`` is both
        ineffective and a security misconfiguration.  Raise early so
        operators receive an explicit error rather than a silent misbehaviour.

        When ``cors_enabled`` is False the CORS middleware is not mounted, so
        legacy ``cors_origins`` / ``cors_allow_credentials`` values are
        irrelevant and must not block startup.

        Raises:
            ValueError: If cors_enabled is True, cors_allow_credentials is
                True, and "*" appears in cors_origins.
        """
        if not self.cors_enabled:
            return self
        if self.cors_allow_credentials and "*" in self.cors_origins:
            msg = (
                "CORS misconfiguration: cors_allow_credentials=True cannot be "
                "combined with cors_origins=['*']. Browsers block credentialed "
                "requests to wildcard origins. Specify explicit allowed origins "
                "or set cors_allow_credentials=False."
            )
            raise ValueError(msg)
        return self

    # Rate limiting
    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable rate limiting",
    )
    rate_limit_requests: int = Field(
        default=100,
        description="Max requests per window",
    )
    rate_limit_window_seconds: int = Field(
        default=60,
        description="Rate limit window in seconds",
    )

    # Batch processing limits
    max_batch_size: int = Field(
        default=100,
        description="Maximum files per batch request",
    )
    max_file_size_mb: int = Field(
        default=50,
        description="Maximum file size in MB",
    )

    # Processing options
    default_prefer_gpu: bool = Field(
        default=True,
        description="Prefer GPU for processing by default",
    )
    default_enable_corrections: bool = Field(
        default=True,
        description="Enable corrections by default",
    )
    default_enable_teacher: bool = Field(
        default=False,
        description="Enable teacher inference by default",
    )

    # Timeouts
    process_timeout_seconds: int = Field(
        default=300,
        description="Timeout for single document processing",
    )
    batch_timeout_seconds: int = Field(
        default=3600,
        description="Timeout for batch processing",
    )

    # Logging
    log_request_body: bool = Field(
        default=False,
        description="Log request body (may contain sensitive data)",
    )
    log_response_body: bool = Field(
        default=False,
        description="Log response body",
    )

    # Authentication
    auth_enabled: bool = Field(
        default=False,
        description="Enable API key authentication",
    )
    api_keys: list[str] = Field(
        default=[],
        description="Valid API keys (comma-separated in env var)",
    )
    internal_callers: list[str] = Field(
        default=[],
        description="IP addresses allowed without auth",
    )

    # Modal GPU Budget Settings (Phase 4 - Device Priority)
    modal_budget_enabled: bool = Field(
        default=True,
        description="Enable Modal GPU budget enforcement",
    )
    modal_daily_budget_dollars: float = Field(
        default=10.0,
        description="Maximum daily spend on Modal GPU in dollars",
    )
    modal_monthly_budget_dollars: float = Field(
        default=100.0,
        description="Maximum monthly spend on Modal GPU in dollars",
    )
    modal_cost_per_gpu_hour: float = Field(
        default=0.36,
        description="Cost per GPU hour (T4 default)",
    )
    modal_budget_warning_threshold: float = Field(
        default=0.8,
        description="Warn when budget usage exceeds this ratio (0-1)",
    )

    def get_openapi_tags(self) -> list[dict[str, Any]]:
        """Get OpenAPI tag metadata."""
        return [
            {
                "name": "health",
                "description": "Health and readiness endpoints",
            },
            {
                "name": "process",
                "description": "Document processing endpoints",
            },
            {
                "name": "batch",
                "description": "Batch processing endpoints",
            },
        ]


@lru_cache
def get_api_settings() -> APISettings:
    """Get cached API settings instance."""
    return APISettings()
