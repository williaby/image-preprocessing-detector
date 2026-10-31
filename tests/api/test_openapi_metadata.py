"""Tests for OpenAPI metadata built by ``create_app`` from ``APISettings``.

Covers the license and servers entries of the published schema, including the
requirement that the default license matches the project license.
"""

from pathlib import Path

import pytest

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 has no stdlib tomllib
    tomllib = pytest.importorskip("tomli", reason="tomli required on Python 3.10")

# Skip all tests if FastAPI is not installed
fastapi = pytest.importorskip("fastapi", reason="FastAPI required for API tests")

from image_preprocessing_detector.api.app import create_app
from image_preprocessing_detector.api.config import APISettings

REPO_ROOT = Path(__file__).resolve().parents[2]


def _settings(**overrides: object) -> APISettings:
    """Build settings with auth and rate limiting off for schema tests."""
    return APISettings.model_validate(
        {"auth_enabled": False, "rate_limit_enabled": False, **overrides}
    )


class TestLicenseMetadata:
    """The published license must match the project license."""

    def test_default_license_matches_pyproject(self) -> None:
        """Default OpenAPI license is the SPDX id declared in pyproject.toml."""
        with (REPO_ROOT / "pyproject.toml").open("rb") as fh:
            project_license = tomllib.load(fh)["project"]["license"]["text"]

        info = create_app(settings=_settings()).openapi()["info"]

        assert project_license == "CC-BY-SA-4.0"
        assert info["license"]["name"] == project_license
        assert (
            info["license"]["url"] == "https://creativecommons.org/licenses/by-sa/4.0/"
        )

    def test_empty_license_url_is_omitted(self) -> None:
        """An empty license URL must not break schema generation."""
        info = create_app(settings=_settings(license_url="")).openapi()["info"]

        assert info["license"] == {"name": "CC-BY-SA-4.0"}

    def test_empty_license_name_omits_license(self) -> None:
        """An empty license name omits ``info.license`` entirely."""
        info = create_app(settings=_settings(license_name="")).openapi()["info"]

        assert "license" not in info


class TestServersMetadata:
    """The OpenAPI ``servers`` list is configurable."""

    def test_default_server_is_local_development(self) -> None:
        """Default server entry keeps the local development URL."""
        schema = create_app(settings=_settings()).openapi()

        assert schema["servers"] == [
            {"url": "http://localhost:8000", "description": "Local development server"}
        ]

    def test_custom_server_url_and_description(self) -> None:
        """Deployments can advertise their own server URL."""
        settings = _settings(
            server_url="https://api.example.org",
            server_description="Production",
        )

        schema = create_app(settings=settings).openapi()

        assert schema["servers"] == [
            {"url": "https://api.example.org", "description": "Production"}
        ]

    def test_empty_server_url_omits_servers(self) -> None:
        """An empty server URL leaves ``servers`` to the client default."""
        schema = create_app(settings=_settings(server_url="")).openapi()

        assert "servers" not in schema


def test_export_openapi_rejects_output_outside_repo(tmp_path: Path) -> None:
    """The export script must refuse to write outside the repository."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "export_openapi", REPO_ROOT / "scripts" / "export_openapi.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    outside = tmp_path / "openapi.json"
    with pytest.raises(ValueError, match="outside the repository"):
        module.export_openapi(outside)
    assert not outside.exists()
