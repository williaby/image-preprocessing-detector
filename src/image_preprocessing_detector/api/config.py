"""API configuration settings.

Provides configuration for:
- CORS settings
- Rate limiting
- API versioning
- Device preferences
"""

from functools import lru_cache
from typing import Any

from pydantic import Field
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
        default="Intelligent image preprocessing detection for RAG document pipelines",
        description="API description for OpenAPI docs",
    )
    version: str = Field(
        default="0.1.0",
        description="API version",
    )

    # CORS settings
    cors_enabled: bool = Field(
        default=True,
        description="Enable CORS middleware",
    )
    cors_origins: list[str] = Field(
        default=["*"],
        description="Allowed CORS origins",
    )
    cors_allow_credentials: bool = Field(
        default=True,
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
