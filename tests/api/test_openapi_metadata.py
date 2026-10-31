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
    """Build settings from field defaults only, with auth and rate limiting off.

    ``model_construct`` does not read ``IMGPREP_API_*`` environment variables
    or ``.env``, so the default-value assertions cannot depend on the caller's
    environment.
    """
    return APISettings.model_construct(
        auth_enabled=False, rate_limit_enabled=False, **overrides
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


@pytest.fixture
def export_module():
    """Load ``scripts/export_openapi.py`` as a module."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "export_openapi", REPO_ROOT / "scripts" / "export_openapi.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_export_openapi_rejects_output_outside_repo(
    export_module, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The export script must refuse to write outside the repository."""
    # Patch the boundary to a sibling directory so the test does not depend
    # on where pytest places ``tmp_path`` (e.g. a repo-local ``--basetemp``).
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    monkeypatch.setattr(export_module, "REPO_ROOT", fake_repo)

    outside = tmp_path / "outside" / "openapi.json"
    with pytest.raises(ValueError, match="outside the repository"):
        export_module.export_openapi(outside)
    assert not outside.exists()


def test_export_openapi_rejects_symlink_escape(
    export_module, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A path inside the repo that symlinks outside must also be refused."""
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    link = fake_repo / "docs"
    try:
        link.symlink_to(outside_dir, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not supported on this platform")
    monkeypatch.setattr(export_module, "REPO_ROOT", fake_repo)

    with pytest.raises(ValueError, match="outside the repository"):
        export_module.export_openapi(link / "openapi.json")
    assert not (outside_dir / "openapi.json").exists()
