"""
Pytest configuration and fixtures for image_preprocessing_detector tests.

This module provides:
- Test fixture paths for real dataset samples
- Pytest markers for different test categories
- Shared fixtures for common test resources
"""

from pathlib import Path

import pytest

# ============================================================================
# Test Fixture Paths
# ============================================================================

# Root paths
PROJECT_ROOT = Path(__file__).parent.parent
FIXTURES_DIR = PROJECT_ROOT / "data" / "test_fixtures"
BENCHMARKS_DIR = PROJECT_ROOT / "data" / "benchmarks"


# ============================================================================
# Pytest Markers
# ============================================================================


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers",
        "unit: Unit tests (fast, isolated, no external dependencies)",
    )
    config.addinivalue_line(
        "markers",
        "integration: Integration tests (moderate speed, may use fixtures)",
    )
    config.addinivalue_line(
        "markers",
        "benchmark: Benchmark tests (slow, comprehensive performance tests)",
    )
    config.addinivalue_line(
        "markers",
        "requires_full_dataset: Tests requiring full datasets (88+ GB, skip in CI)",
    )
    config.addinivalue_line(
        "markers",
        "slow: Slow tests (can be excluded with -m 'not slow')",
    )
    config.addinivalue_line(
        "markers",
        "real_data: Tests using real test fixtures (not synthetic)",
    )


# ============================================================================
# Fixture Directory Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Return path to test fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def doclaynet_fixtures_dir(fixtures_dir: Path) -> Path:
    """Return path to DocLayNet test fixtures."""
    return fixtures_dir / "doclaynet"


@pytest.fixture(scope="session")
def tablebank_fixtures_dir(fixtures_dir: Path) -> Path:
    """Return path to TableBank test fixtures."""
    return fixtures_dir / "tablebank"


@pytest.fixture(scope="session")
def wili_fixtures_dir(fixtures_dir: Path) -> Path:
    """Return path to WiLI-2018 test fixtures."""
    return fixtures_dir / "wili_2018"


@pytest.fixture(scope="session")
def cocotext_fixtures_dir(fixtures_dir: Path) -> Path:
    """Return path to COCO-Text test fixtures."""
    return fixtures_dir / "cocotext"


@pytest.fixture(scope="session")
def omnidocbench_fixtures_dir(fixtures_dir: Path) -> Path:
    """Return path to OmniDocBench test fixtures."""
    return fixtures_dir / "omnidocbench"


# ============================================================================
# File Collection Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def doclaynet_pdfs(doclaynet_fixtures_dir: Path) -> list[Path]:
    """
    Return list of DocLayNet PDF fixtures.

    These are carefully selected PDFs representing different document types:
    - Simple text-heavy documents
    - Documents with tables and figures
    - Multi-column layouts
    - Skewed/rotated pages
    - Low contrast or blurry scans
    """
    pdfs = sorted(doclaynet_fixtures_dir.glob("*.pdf"))
    if not pdfs:
        pytest.skip("DocLayNet fixtures not available")
    return pdfs


@pytest.fixture(scope="session")
def tablebank_images(tablebank_fixtures_dir: Path) -> list[Path]:
    """
    Return list of TableBank image fixtures.

    These are carefully selected table images representing:
    - Simple tables (3-5 columns)
    - Complex tables (10+ columns, merged cells)
    - Rotated tables
    - Low quality/blurry tables
    - Tables with embedded graphics
    """
    images = sorted(tablebank_fixtures_dir.glob("*.{jpg,png,jpeg}"))
    if not images:
        # Try without case sensitivity
        images = sorted(tablebank_fixtures_dir.glob("*.[jJ][pP][gG]"))
        images.extend(sorted(tablebank_fixtures_dir.glob("*.[pP][nN][gG]")))
        images.extend(sorted(tablebank_fixtures_dir.glob("*.[jJ][pP][eE][gG]")))

    if not images:
        pytest.skip("TableBank fixtures not available")
    return images


@pytest.fixture(scope="session")
def wili_text_samples(wili_fixtures_dir: Path) -> list[Path]:
    """
    Return list of WiLI-2018 text sample fixtures.

    These are text samples in 10 diverse languages:
    - English (eng), French (fra), German (deu)
    - Spanish (spa), Chinese (zho), Arabic (ara)
    - Russian (rus), Japanese (jpn), Korean (kor)
    - Hindi (hin)
    """
    samples = sorted(wili_fixtures_dir.glob("*.txt"))
    # Exclude manifest files
    samples = [s for s in samples if "manifest" not in s.name.lower()]

    if not samples:
        pytest.skip("WiLI-2018 fixtures not available")
    return samples


# ============================================================================
# Individual Sample Fixtures (for targeted tests)
# ============================================================================


@pytest.fixture
def simple_text_pdf(doclaynet_fixtures_dir: Path) -> Path:
    """Return simple text-heavy PDF fixture."""
    pdf = doclaynet_fixtures_dir / "simple_text_1.pdf"
    if not pdf.exists():
        pytest.skip("Simple text PDF fixture not available")
    return pdf


@pytest.fixture
def skewed_pdf(doclaynet_fixtures_dir: Path) -> Path:
    """Return skewed/rotated PDF fixture."""
    pdf = doclaynet_fixtures_dir / "skewed_4.pdf"
    if not pdf.exists():
        pytest.skip("Skewed PDF fixture not available")
    return pdf


@pytest.fixture
def multi_column_pdf(doclaynet_fixtures_dir: Path) -> Path:
    """Return multi-column layout PDF fixture."""
    pdf = doclaynet_fixtures_dir / "multi_column_3.pdf"
    if not pdf.exists():
        pytest.skip("Multi-column PDF fixture not available")
    return pdf


@pytest.fixture
def simple_table_image(tablebank_fixtures_dir: Path) -> Path:
    """Return simple table image fixture."""
    # Try both extensions
    for ext in ["png", "jpg", "jpeg"]:
        img = tablebank_fixtures_dir / f"simple_table_1.{ext}"
        if img.exists():
            return img
    pytest.skip("Simple table image fixture not available")


@pytest.fixture
def complex_table_image(tablebank_fixtures_dir: Path) -> Path:
    """Return complex table image fixture."""
    for ext in ["png", "jpg", "jpeg"]:
        img = tablebank_fixtures_dir / f"complex_table_2.{ext}"
        if img.exists():
            return img
    pytest.skip("Complex table image fixture not available")


# ============================================================================
# Benchmark Dataset Fixtures (requires full datasets)
# ============================================================================


@pytest.fixture(scope="session")
def full_doclaynet_dir() -> Path:
    """
    Return path to full DocLayNet dataset (requires_full_dataset marker).

    WARNING: This is a 40+ GB dataset. Tests using this fixture should be
    marked with @pytest.mark.requires_full_dataset to skip in CI.
    """
    full_dir = BENCHMARKS_DIR / "doclaynet"
    if not full_dir.exists():
        pytest.skip("Full DocLayNet dataset not available")
    return full_dir


@pytest.fixture(scope="session")
def full_tablebank_dir() -> Path:
    """
    Return path to full TableBank dataset (requires_full_dataset marker).

    WARNING: This is a 46+ GB dataset. Tests using this fixture should be
    marked with @pytest.mark.requires_full_dataset to skip in CI.
    """
    full_dir = BENCHMARKS_DIR / "tablebank"
    if not full_dir.exists():
        pytest.skip("Full TableBank dataset not available")
    return full_dir


# ============================================================================
# Temporary Directory Fixtures
# ============================================================================


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    """Return temporary directory for test outputs."""
    output_dir = tmp_path / "output"
    output_dir.mkdir(exist_ok=True)
    return output_dir


@pytest.fixture
def tmp_cache_dir(tmp_path: Path) -> Path:
    """Return temporary directory for caching."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir
