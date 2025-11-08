"""Nox sessions for local testing and documentation workflows.

Nox is a command-line tool that automates testing in multiple Python environments.
This file defines sessions for documentation validation, building, and serving.

Usage:
    nox -s fm          # Validate and autofix front matter
    nox -s docs        # Build documentation
    nox -s serve       # Serve documentation locally
    nox -s docstrings  # Check docstring coverage
    nox -s reuse       # Check REUSE compliance
    nox -s sbom        # Generate SBOM
    nox -s scan        # Scan SBOM for vulnerabilities
"""

import nox

# Use the same Python version as the project
nox.options.sessions = ["fm", "docs"]
nox.options.reuse_existing_virtualenvs = True


@nox.session(python="3.12")
def fm(session: nox.Session) -> None:
    """Validate and autofix front matter in documentation.

    This session installs the required dependencies and runs the front matter
    validation script with autofix enabled.
    """
    session.install("pydantic>=2.0", "python-frontmatter>=1.1", "ruamel.yaml>=0.18")
    session.run("python", "tools/validate_front_matter.py", "docs", "--fix")


@nox.session(python="3.12")
def docs(session: nox.Session) -> None:
    """Build documentation with MkDocs.

    This session installs the project with docs dependencies and builds
    the documentation in strict mode.
    """
    session.install("-e", ".[dev]")
    session.run("mkdocs", "build", "--strict")


@nox.session(python="3.12")
def serve(session: nox.Session) -> None:
    """Serve documentation locally for development.

    This session starts the MkDocs development server with live reloading.
    Access at http://127.0.0.1:8000
    """
    session.install("-e", ".[dev]")
    session.run("mkdocs", "serve")


@nox.session(python="3.12")
def docstrings(session: nox.Session) -> None:
    """Check docstring coverage with interrogate and pydocstyle.

    This session validates that docstrings meet the Google style convention
    and that coverage meets the minimum threshold.
    """
    session.install("pydocstyle>=6.3", "interrogate>=1.7")
    session.run("pydocstyle", "src/")
    session.run("interrogate", "-c", "pyproject.toml", "src/")


@nox.session(python="3.12")
def validate(session: nox.Session) -> None:
    """Run all validation checks for documentation.

    This session combines front matter validation, docstring checks,
    and documentation building to ensure everything is correct.
    """
    session.install(
        "-e",
        ".[dev]",
        "pydantic>=2.0",
        "python-frontmatter>=1.1",
        "ruamel.yaml>=0.18",
        "pydocstyle>=6.3",
        "interrogate>=1.7",
    )
    session.run("python", "tools/validate_front_matter.py", "docs", "--fix")
    session.run("pydocstyle", "src/")
    session.run("interrogate", "-c", "pyproject.toml", "src/")
    session.run("mkdocs", "build", "--strict")


@nox.session(python="3.12")
def reuse(session: nox.Session) -> None:
    """Check REUSE compliance.

    This session uses the REUSE tool to verify that all files have proper
    licensing information according to the REUSE specification.
    Requires Docker to be installed and running.
    """
    session.run(
        "docker",
        "run",
        "--rm",
        "--volume",
        f"{session.posargs[0] if session.posargs else '.'}:/data",
        "fsfe/reuse:latest",
        "lint",
        external=True,
    )


@nox.session(python="3.12")
def reuse_spdx(session: nox.Session) -> None:
    """Generate REUSE SPDX document.

    This session generates an SPDX document from the REUSE metadata.
    The SPDX file is saved to reuse-spdx.json in the current directory.
    Requires Docker to be installed and running.
    """
    session.run(
        "docker",
        "run",
        "--rm",
        "--volume",
        f"{session.posargs[0] if session.posargs else '.'}:/data",
        "fsfe/reuse:latest",
        "spdx",
        "--output",
        "/data/reuse-spdx.json",
        external=True,
    )
    session.log("SPDX document generated: reuse-spdx.json")


@nox.session(python="3.12")
def sbom(session: nox.Session) -> None:
    """Generate CycloneDX SBOM.

    This session generates Software Bill of Materials (SBOM) in CycloneDX format
    for runtime, development, and complete dependency sets.
    """
    session.install("cyclonedx-bom==4.6.1")

    # Generate runtime SBOM (production dependencies only)
    session.run(
        "cyclonedx-py",
        "poetry",
        "--of",
        "json",
        "-o",
        "sbom-runtime.json",
        "--no-dev",
    )
    session.log("Runtime SBOM generated: sbom-runtime.json")

    # Generate development SBOM (dev dependencies only)
    session.run(
        "cyclonedx-py",
        "poetry",
        "--of",
        "json",
        "-o",
        "sbom-dev.json",
        "--only",
        "dev",
    )
    session.log("Development SBOM generated: sbom-dev.json")

    # Generate complete SBOM (all dependencies)
    session.run(
        "cyclonedx-py",
        "poetry",
        "--of",
        "json",
        "-o",
        "sbom-complete.json",
    )
    session.log("Complete SBOM generated: sbom-complete.json")


@nox.session(python="3.12")
def scan(session: nox.Session) -> None:
    """Scan SBOM for vulnerabilities.

    This session uses Trivy to scan the generated SBOMs for known vulnerabilities.
    Requires Docker to be installed and running.
    Requires SBOM files to be generated first (run 'nox -s sbom').
    """
    import pathlib

    sbom_file = session.posargs[0] if session.posargs else "sbom-runtime.json"

    if not pathlib.Path(sbom_file).exists():
        session.error(f"SBOM file not found: {sbom_file}. Run 'nox -s sbom' first.")

    session.run(
        "docker",
        "run",
        "--rm",
        "--volume",
        f"{pathlib.Path('.').absolute()}:/workspace",
        "aquasec/trivy:latest",
        "sbom",
        f"/workspace/{sbom_file}",
        "--severity",
        "CRITICAL,HIGH",
        "--format",
        "table",
        external=True,
    )


@nox.session(python="3.12")
def compliance(session: nox.Session) -> None:
    """Run all compliance checks.

    This session runs REUSE compliance checks and generates SBOMs
    for comprehensive compliance validation.
    """
    session.log("Running REUSE compliance check...")
    reuse(session)

    session.log("Generating SBOMs...")
    sbom(session)

    session.log("Scanning runtime SBOM for vulnerabilities...")
    scan(session)

    session.log("All compliance checks completed successfully!")
