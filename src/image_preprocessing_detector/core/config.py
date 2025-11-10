# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Configuration settings for image preprocessing detector."""

import os
from typing import Literal


class Settings:
    """Configuration settings for image preprocessing.

    Settings can be overridden via environment variables with prefix IMAGE_PREP_.
    Keyword arguments take precedence over environment variables.
    """

    def __init__(
        self,
        enable_pdf_upscaling: bool | None = None,
        pdf_min_dpi: int | None = None,
        pdf_target_dpi: int | None = None,
        pdf_upscale_algorithm: (
            Literal["lanczos", "bicubic", "inter_cubic", "inter_linear", "inter_area"]
            | None
        ) = None,
        pdf_preserve_original_on_error: bool | None = None,
    ) -> None:
        """Initialize settings from environment variables or keyword arguments.

        Args:
            enable_pdf_upscaling: Enable/disable upscaling (overrides env var)
            pdf_min_dpi: Minimum DPI threshold (overrides env var)
            pdf_target_dpi: Target DPI for upscaling (overrides env var)
            pdf_upscale_algorithm: Algorithm selection (overrides env var)
            pdf_preserve_original_on_error: Preserve original on error (overrides env var)
        """
        # PDF Resolution Pre-processing (Phase 1B)
        self.enable_pdf_upscaling: bool = (
            enable_pdf_upscaling
            if enable_pdf_upscaling is not None
            else self._get_bool_env("IMAGE_PREP_ENABLE_PDF_UPSCALING", True)
        )
        self.pdf_min_dpi: int = (
            pdf_min_dpi
            if pdf_min_dpi is not None
            else self._get_int_env("IMAGE_PREP_PDF_MIN_DPI", 300)
        )
        self.pdf_target_dpi: int = (
            pdf_target_dpi
            if pdf_target_dpi is not None
            else self._get_int_env("IMAGE_PREP_PDF_TARGET_DPI", 300)
        )
        self.pdf_upscale_algorithm: Literal[
            "lanczos", "bicubic", "inter_cubic", "inter_linear", "inter_area"
        ] = (
            pdf_upscale_algorithm
            if pdf_upscale_algorithm is not None
            else self._get_str_env("IMAGE_PREP_PDF_UPSCALE_ALGORITHM", "lanczos")  # type: ignore
        )
        self.pdf_preserve_original_on_error: bool = (
            pdf_preserve_original_on_error
            if pdf_preserve_original_on_error is not None
            else self._get_bool_env("IMAGE_PREP_PDF_PRESERVE_ORIGINAL_ON_ERROR", True)
        )

    def _get_bool_env(self, key: str, default: bool) -> bool:
        """Get boolean from environment variable.

        Args:
            key: Environment variable key
            default: Default value if not set

        Returns:
            Boolean value from environment or default
        """
        value = os.getenv(key)
        if value is None:
            return default
        return value.lower() in ("true", "1", "yes", "on")

    def _get_int_env(self, key: str, default: int) -> int:
        """Get integer from environment variable.

        Args:
            key: Environment variable key
            default: Default value if not set

        Returns:
            Integer value from environment or default
        """
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    def _get_str_env(self, key: str, default: str) -> str:
        """Get string from environment variable.

        Args:
            key: Environment variable key
            default: Default value if not set

        Returns:
            String value from environment or default
        """
        return os.getenv(key, default)
