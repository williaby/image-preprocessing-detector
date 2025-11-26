# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#

"""Unit tests for configuration settings."""

import os
from unittest.mock import patch

import pytest

from image_preprocessing_detector.core.config import Settings


class TestSettings:
    """Test Settings class initialization and validation."""

    def test_default_settings(self) -> None:
        """Test default settings initialization."""
        settings = Settings()

        assert settings.enable_pdf_upscaling is True
        assert settings.pdf_min_dpi == 300
        assert settings.pdf_target_dpi == 300
        assert settings.pdf_upscale_algorithm == "lanczos"
        assert settings.pdf_preserve_original_on_error is True

    def test_keyword_arguments_override(self) -> None:
        """Test that keyword arguments override defaults."""
        settings = Settings(
            enable_pdf_upscaling=False,
            pdf_min_dpi=200,
            pdf_target_dpi=400,
            pdf_upscale_algorithm="bicubic",
            pdf_preserve_original_on_error=False,
        )

        assert settings.enable_pdf_upscaling is False
        assert settings.pdf_min_dpi == 200
        assert settings.pdf_target_dpi == 400
        assert settings.pdf_upscale_algorithm == "bicubic"
        assert settings.pdf_preserve_original_on_error is False

    def test_environment_variables_override_defaults(self) -> None:
        """Test that environment variables override defaults."""
        with patch.dict(
            os.environ,
            {
                "IMAGE_PREP_ENABLE_PDF_UPSCALING": "false",
                "IMAGE_PREP_PDF_MIN_DPI": "250",
                "IMAGE_PREP_PDF_TARGET_DPI": "350",
                "IMAGE_PREP_PDF_UPSCALE_ALGORITHM": "inter_cubic",
                "IMAGE_PREP_PDF_PRESERVE_ORIGINAL_ON_ERROR": "false",
            },
        ):
            settings = Settings()

            assert settings.enable_pdf_upscaling is False
            assert settings.pdf_min_dpi == 250
            assert settings.pdf_target_dpi == 350
            assert settings.pdf_upscale_algorithm == "inter_cubic"
            assert settings.pdf_preserve_original_on_error is False

    def test_keyword_arguments_override_environment(self) -> None:
        """Test that keyword arguments take precedence over environment variables."""
        with patch.dict(
            os.environ,
            {
                "IMAGE_PREP_ENABLE_PDF_UPSCALING": "false",
                "IMAGE_PREP_PDF_MIN_DPI": "250",
                "IMAGE_PREP_PDF_UPSCALE_ALGORITHM": "inter_cubic",
            },
        ):
            settings = Settings(
                enable_pdf_upscaling=True,
                pdf_min_dpi=300,
                pdf_upscale_algorithm="lanczos",
            )

            assert settings.enable_pdf_upscaling is True
            assert settings.pdf_min_dpi == 300
            assert settings.pdf_upscale_algorithm == "lanczos"

    def test_invalid_algorithm_falls_back_to_default(
        self, capsys: pytest.CaptureFixture, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that invalid algorithm from environment falls back to default."""
        with patch.dict(
            os.environ,
            {"IMAGE_PREP_PDF_UPSCALE_ALGORITHM": "invalid_algorithm"},
        ):
            settings = Settings()

            # Should fall back to default
            assert settings.pdf_upscale_algorithm == "lanczos"

            # Check for warning in captured output - could be in stdout (direct print)
            # or in log records (when structlog is configured by other tests)
            captured = capsys.readouterr()
            log_text = " ".join(record.message for record in caplog.records)
            combined_output = captured.out + captured.err + log_text

            assert "Invalid algorithm 'invalid_algorithm'" in combined_output
            assert "Using default: lanczos" in combined_output

    def test_all_valid_algorithms(self) -> None:
        """Test that all valid algorithms are accepted."""
        valid_algorithms = [
            "lanczos",
            "bicubic",
            "inter_cubic",
            "inter_linear",
            "inter_area",
        ]

        for algorithm in valid_algorithms:
            with patch.dict(
                os.environ,
                {"IMAGE_PREP_PDF_UPSCALE_ALGORITHM": algorithm},
            ):
                settings = Settings()
                assert settings.pdf_upscale_algorithm == algorithm

    def test_boolean_env_parsing(self) -> None:
        """Test boolean environment variable parsing variations."""
        true_values = ["true", "True", "TRUE", "1", "yes", "YES", "on", "ON"]
        false_values = ["false", "False", "FALSE", "0", "no", "NO", "off", "OFF"]

        for true_val in true_values:
            with patch.dict(os.environ, {"IMAGE_PREP_ENABLE_PDF_UPSCALING": true_val}):
                settings = Settings()
                assert settings.enable_pdf_upscaling is True

        for false_val in false_values:
            with patch.dict(os.environ, {"IMAGE_PREP_ENABLE_PDF_UPSCALING": false_val}):
                settings = Settings()
                assert settings.enable_pdf_upscaling is False

    def test_invalid_int_falls_back_to_default(self) -> None:
        """Test that invalid integer values fall back to defaults."""
        with patch.dict(
            os.environ,
            {
                "IMAGE_PREP_PDF_MIN_DPI": "not_a_number",
                "IMAGE_PREP_PDF_TARGET_DPI": "invalid",
            },
        ):
            settings = Settings()

            # Should fall back to defaults
            assert settings.pdf_min_dpi == 300
            assert settings.pdf_target_dpi == 300
