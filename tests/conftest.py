"""
Pytest configuration and fixtures for image_preprocessing_detector tests.

This module provides:
- Test fixture paths for real dataset samples
- Pytest markers for different test categories
- Shared fixtures for common test resources
- Custom plugins for test quality enforcement (weak assertion detector)

Custom Plugins:
    The weak assertion detector is available via --weak-assertions flag.
    See tests/plugins/weak_assertion_detector.py for details.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

# Add tests directory to path for plugin import
_tests_dir = Path(__file__).parent
if str(_tests_dir) not in sys.path:
    sys.path.insert(0, str(_tests_dir))

# Import plugin hooks to register them
from plugins.weak_assertion_detector import (
    pytest_addoption as _weak_assertion_addoption,
)
from plugins.weak_assertion_detector import (
    pytest_configure as _weak_assertion_configure,
)

# ============================================================================
# Test Fixture Paths
# ============================================================================

# Root paths
PROJECT_ROOT = Path(__file__).parent.parent
FIXTURES_DIR = PROJECT_ROOT / "data" / "test_fixtures"
BENCHMARKS_DIR = PROJECT_ROOT / "data" / "benchmarks"

# Glob patterns - extracted to constants to avoid duplication (S1192)
PDF_GLOB_PATTERN = "*.pdf"
IMAGE_GLOB_PATTERN = "*.{jpg,png,jpeg}"


# ============================================================================
# Pytest Markers
# ============================================================================


def pytest_addoption(parser):
    """Add custom command line options."""
    # Delegate to weak assertion plugin
    _weak_assertion_addoption(parser)


def pytest_configure(config):
    """Register custom pytest markers and plugins."""
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

    # Register weak assertion detector plugin
    _weak_assertion_configure(config)


# ============================================================================
# Optional Dependency Handling
# ============================================================================

CV2_AVAILABLE = importlib.util.find_spec("cv2") is not None
TORCH_AVAILABLE = importlib.util.find_spec("torch") is not None

_CV2_TEST_MODULES = {
    "tests.integration.test_cli",
    "tests.integration.test_pdf_upscaling_integration",
    "tests.integration.test_phase2_complete",
    "tests.integration.test_pipeline",
    "tests.integration.test_real_fixtures",
    "tests.unit.test_corrections",
    "tests.unit.test_image_loader",
    "tests.unit.test_iqa_classical",
    "tests.unit.test_iqa_ml",
    "tests.unit.test_json_generator",
    "tests.unit.test_pdf_analyzer",
    "tests.unit.test_pdf_loader",
    "tests.unit.test_pdf_resolution",
    "tests.unit.test_pdf_upscaler",
    "tests.unit.test_text_gate",
}

_TORCH_TEST_MODULES = {
    "tests.unit.test_loss_functions",
    "tests.unit.test_resnet_teacher",
}

_CV2_TEST_PATH_SUFFIXES = {
    "tests/integration/test_cli.py",
    "tests/integration/test_pdf_upscaling_integration.py",
    "tests/integration/test_phase2_complete.py",
    "tests/integration/test_pipeline.py",
    "tests/integration/test_real_fixtures.py",
    "tests/unit/test_corrections.py",
    "tests/unit/test_image_loader.py",
    "tests/unit/test_iqa_classical.py",
    "tests/unit/test_iqa_ml.py",
    "tests/unit/test_json_generator.py",
    "tests/unit/test_pdf_analyzer.py",
    "tests/unit/test_pdf_loader.py",
    "tests/unit/test_pdf_resolution.py",
    "tests/unit/test_pdf_upscaler.py",
    "tests/unit/test_text_gate.py",
}

_TORCH_TEST_PATH_SUFFIXES = {
    "tests/unit/test_loss_functions.py",
    "tests/unit/test_resnet_teacher.py",
}


def pytest_ignore_collect(
    collection_path: Path, config, **kwargs
):  # pragma: no cover - collection-time hook
    """Skip collecting test modules that require missing optional dependencies."""
    path = kwargs.get("path", collection_path)
    path_str = str(path)

    if not CV2_AVAILABLE and any(
        path_str.endswith(suffix) for suffix in _CV2_TEST_PATH_SUFFIXES
    ):
        return True

    return not TORCH_AVAILABLE and any(
        path_str.endswith(suffix) for suffix in _TORCH_TEST_PATH_SUFFIXES
    )


def pytest_collection_modifyitems(config, items):
    """
    Skip tests that rely on optional heavy dependencies when they are absent.

    This keeps the base (non-ML) environment green while still running the tests
    when contributors install the `ml` extras.
    """

    if not CV2_AVAILABLE:
        skip_cv2 = pytest.mark.skip(
            reason="OpenCV is not installed (optional dependency)"
        )
    if not TORCH_AVAILABLE:
        skip_torch = pytest.mark.skip(
            reason="PyTorch is not installed (install with `--with ml` extras)"
        )

    for item in items:
        module_name = getattr(getattr(item, "module", None), "__name__", "")

        if not CV2_AVAILABLE and module_name in _CV2_TEST_MODULES:
            item.add_marker(skip_cv2)

        if not TORCH_AVAILABLE and module_name in _TORCH_TEST_MODULES:
            item.add_marker(skip_torch)


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


@pytest.fixture(scope="session")
def iqa_samples_dir(fixtures_dir: Path) -> Path:
    """Return path to IQA ground truth samples."""
    return fixtures_dir / "iqa_samples"


@pytest.fixture(scope="session")
def training_validation_dir(fixtures_dir: Path) -> Path:
    """Return path to training validation samples."""
    return fixtures_dir / "training_validation"


@pytest.fixture(scope="session")
def augmentation_input_dir(fixtures_dir: Path) -> Path:
    """Return path to augmentation input samples."""
    return fixtures_dir / "augmentation_input"


@pytest.fixture(scope="session")
def layout_samples_dir(fixtures_dir: Path) -> Path:
    """Return path to layout edge case samples."""
    return fixtures_dir / "layout_samples"


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
    pdfs = sorted(doclaynet_fixtures_dir.glob(PDF_GLOB_PATTERN))
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


@pytest.fixture(scope="session")
def iqa_sample_images(iqa_samples_dir: Path) -> list[Path]:
    """
    Return list of IQA ground truth sample images.

    These are carefully selected samples with known quality defects:
    - Reference clean (pristine, DMOS=0.0)
    - Gaussian blur (high blur)
    - White noise (high noise)
    - Low contrast (poor illumination)
    - JPEG artifacts (compression artifacts)
    - Combined defects (blur + noise + skew)
    """
    images = sorted(iqa_samples_dir.glob("*.png"))
    if not images:
        pytest.skip("IQA sample images not available")
    return images


@pytest.fixture(scope="session")
def iqa_labels(iqa_samples_dir: Path) -> dict:
    """
    Return IQA ground truth labels.

    Returns dictionary mapping filenames to quality scores:
    - dmos: Overall quality score (0-100, higher = worse)
    - blur: Blur level (0.0-1.0)
    - noise: Noise level (0.0-1.0)
    - illumination: Illumination issues (0.0-1.0)
    - artifacts: Compression artifacts (0.0-1.0)
    - skew: Skew/rotation (0.0-1.0)
    """
    import json

    labels_file = iqa_samples_dir / "labels.json"
    if not labels_file.exists():
        pytest.skip("IQA labels.json not available")

    with labels_file.open() as f:
        return json.load(f)


@pytest.fixture(scope="session")
def training_validation_images(training_validation_dir: Path) -> list[Path]:
    """
    Return list of training validation sample images.

    These represent a quality spectrum:
    - 3 clean baseline samples
    - 1 moderate degradation sample
    - 1 severe degradation sample
    """
    images = sorted(training_validation_dir.glob("*.jpg"))
    if not images:
        pytest.skip("Training validation images not available")
    return images


@pytest.fixture(scope="session")
def augmentation_input_images(augmentation_input_dir: Path) -> list[Path]:
    """
    Return list of clean augmentation input samples.

    These are pristine baseline images for augmentation testing:
    - Clean text page
    - Clean table page
    - Clean form page
    """
    images = sorted(augmentation_input_dir.glob("*.jpg"))
    if not images:
        pytest.skip("Augmentation input images not available")
    return images


@pytest.fixture(scope="session")
def layout_edge_case_samples(layout_samples_dir: Path) -> list[Path]:
    """
    Return list of layout edge case samples (PDF + images).

    These represent challenging layout scenarios:
    - Dense math equations (PDF)
    - Watermarked document (PDF)
    - Colorful background (JPG)
    - Handwriting mixed with printed text (JPG)
    """
    samples = []
    samples.extend(sorted(layout_samples_dir.glob(PDF_GLOB_PATTERN)))
    samples.extend(sorted(layout_samples_dir.glob("*.jpg")))
    if not samples:
        pytest.skip("Layout edge case samples not available")
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
def tables_figures_pdf(doclaynet_fixtures_dir: Path) -> Path:
    """Return PDF with tables and figures fixture."""
    pdf = doclaynet_fixtures_dir / "tables_figures_2.pdf"
    if not pdf.exists():
        pytest.skip("Tables/figures PDF fixture not available")
    return pdf


@pytest.fixture
def all_doclaynet_pdfs(doclaynet_fixtures_dir: Path) -> list[Path]:
    """Return list of all DocLayNet PDF fixture paths."""
    if not doclaynet_fixtures_dir.exists():
        return []
    return list(doclaynet_fixtures_dir.glob(PDF_GLOB_PATTERN))


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


@pytest.fixture
def rotated_table_image(tablebank_fixtures_dir: Path) -> Path:
    """Return rotated table image fixture."""
    for ext in ["png", "jpg", "jpeg"]:
        img = tablebank_fixtures_dir / f"rotated_3.{ext}"
        if img.exists():
            return img
    pytest.skip("Rotated table image fixture not available")


@pytest.fixture
def low_quality_table_image(tablebank_fixtures_dir: Path) -> Path:
    """Return low quality/blurry table image fixture."""
    for ext in ["jpg", "jpeg", "png"]:
        img = tablebank_fixtures_dir / f"low_quality_4.{ext}"
        if img.exists():
            return img
    pytest.skip("Low quality table image fixture not available")


@pytest.fixture
def embedded_graphics_table_image(tablebank_fixtures_dir: Path) -> Path:
    """Return table with embedded graphics image fixture."""
    for ext in ["jpg", "jpeg", "png"]:
        img = tablebank_fixtures_dir / f"embedded_graphics_5.{ext}"
        if img.exists():
            return img
    pytest.skip("Embedded graphics table image fixture not available")


@pytest.fixture
def all_tablebank_images(tablebank_fixtures_dir: Path) -> list[Path]:
    """Return list of all TableBank image fixture paths."""
    if not tablebank_fixtures_dir.exists():
        return []
    images = list(tablebank_fixtures_dir.glob("*.png"))
    images.extend(tablebank_fixtures_dir.glob("*.jpg"))
    return images


@pytest.fixture
def low_quality_image(tablebank_fixtures_dir: Path) -> Path:
    """Return low quality/blurry image fixture."""
    for ext in ["jpg", "jpeg", "png"]:
        img = tablebank_fixtures_dir / f"low_quality_4.{ext}"
        if img.exists():
            return img
    pytest.skip("Low quality image fixture not available")


@pytest.fixture
def low_contrast_pdf(doclaynet_fixtures_dir: Path) -> Path:
    """Return low contrast PDF fixture."""
    pdf = doclaynet_fixtures_dir / "low_contrast_5.pdf"
    if not pdf.exists():
        pytest.skip("Low contrast PDF fixture not available")
    return pdf


@pytest.fixture
def reference_clean_image(iqa_samples_dir: Path) -> Path:
    """Return pristine reference IQA image (DMOS=0.0)."""
    img = iqa_samples_dir / "reference_clean.png"
    if not img.exists():
        pytest.skip("Reference clean IQA image not available")
    return img


@pytest.fixture
def blurry_image(iqa_samples_dir: Path) -> Path:
    """Return high blur IQA sample image."""
    img = iqa_samples_dir / "gaussian_blur_high.png"
    if not img.exists():
        pytest.skip("Blurry IQA image not available")
    return img


@pytest.fixture
def noisy_image(iqa_samples_dir: Path) -> Path:
    """Return high noise IQA sample image."""
    img = iqa_samples_dir / "white_noise_high.png"
    if not img.exists():
        pytest.skip("Noisy IQA image not available")
    return img


@pytest.fixture
def watermarked_pdf(layout_samples_dir: Path) -> Path:
    """Return watermarked document PDF fixture."""
    pdf = layout_samples_dir / "watermarked_document.pdf"
    if not pdf.exists():
        pytest.skip("Watermarked PDF fixture not available")
    return pdf


@pytest.fixture
def dense_math_pdf(layout_samples_dir: Path) -> Path:
    """Return dense math equations PDF fixture."""
    pdf = layout_samples_dir / "dense_math_page4.pdf"
    if not pdf.exists():
        pytest.skip("Dense math PDF fixture not available")
    return pdf


@pytest.fixture
def handwriting_mixed_image(layout_samples_dir: Path) -> Path:
    """Return handwriting mixed with printed text image fixture."""
    img = layout_samples_dir / "handwriting_mixed.jpg"
    if not img.exists():
        pytest.skip("Handwriting mixed image fixture not available")
    return img


@pytest.fixture
def colorful_background_image(layout_samples_dir: Path) -> Path:
    """Return colorful background document image fixture."""
    img = layout_samples_dir / "colorful_background.jpg"
    if not img.exists():
        pytest.skip("Colorful background image fixture not available")
    return img


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
