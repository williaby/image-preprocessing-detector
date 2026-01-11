"""E2E test fixtures and configuration."""

import shutil
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

# Use modern numpy.random.Generator API (seeded for reproducibility)
_rng = np.random.default_rng(seed=42)


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for test outputs."""
    temp_dir = tempfile.mkdtemp(prefix="e2e_test_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


def _create_document_image(height: int = 825, width: int = 637) -> np.ndarray:
    """Create a synthetic document image for testing.

    Default size is 1/4 of letter size (825x637) for faster tests while
    maintaining sufficient resolution for IQA detectors.
    """
    # Create a document-like image (white background with text blocks)
    img = np.ones((height, width, 3), dtype=np.uint8) * 255

    # Scale factor from full size (3300x2550) to test size
    scale_x = width / 2550
    scale_y = height / 3300

    # Add header text block
    cv2.rectangle(
        img,
        (int(200 * scale_x), int(100 * scale_y)),
        (int(2350 * scale_x), int(200 * scale_y)),
        (0, 0, 0),
        -1,
    )

    # Add body text blocks (simulating paragraphs)
    for y in range(300, 2800, 100):
        # Vary line lengths to simulate text
        line_width = _rng.integers(1800, 2100)
        cv2.rectangle(
            img,
            (int(200 * scale_x), int(y * scale_y)),
            (int((200 + line_width) * scale_x), int((y + 20) * scale_y)),
            (30, 30, 30),
            -1,
        )

    # Add a figure placeholder
    cv2.rectangle(
        img,
        (int(200 * scale_x), int(2900 * scale_y)),
        (int(1200 * scale_x), int(3200 * scale_y)),
        (200, 200, 200),
        -1,
    )
    cv2.rectangle(
        img,
        (int(200 * scale_x), int(2900 * scale_y)),
        (int(1200 * scale_x), int(3200 * scale_y)),
        (100, 100, 100),
        2,
    )

    return img


# Module-scoped fixtures for faster tests (images created once per module)
@pytest.fixture(scope="module")
def sample_document_image():
    """Create a synthetic document image for testing.

    Module-scoped for performance - image is reused across all tests in module.
    """
    return _create_document_image()


@pytest.fixture(scope="module")
def sample_blurry_image(sample_document_image):
    """Create a blurry version of the sample document."""
    return cv2.GaussianBlur(sample_document_image, (21, 21), 10)


@pytest.fixture(scope="module")
def sample_noisy_image(sample_document_image):
    """Create a noisy version of the sample document."""
    # Use float arithmetic to properly add Gaussian noise
    img_float = sample_document_image.astype(np.float32)
    # Use higher sigma (50) to ensure detection - thresholds are: medium=5, high=12, critical=20
    noise = _rng.normal(0, 50, sample_document_image.shape).astype(np.float32)
    return np.clip(img_float + noise, 0, 255).astype(np.uint8)


@pytest.fixture(scope="module")
def sample_skewed_image(sample_document_image):
    """Create a skewed version of the sample document."""
    h, w = sample_document_image.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, 5, 1.0)  # 5 degree rotation
    return cv2.warpAffine(
        sample_document_image, rotation_matrix, (w, h), borderValue=(255, 255, 255)
    )


@pytest.fixture(scope="module")
def sample_low_contrast_image(sample_document_image):
    """Create a low contrast version of the sample document."""
    # Reduce contrast by compressing intensity range
    gray = cv2.cvtColor(sample_document_image, cv2.COLOR_BGR2GRAY)
    # Map 0-255 to 80-175 (low contrast)
    low_contrast = ((gray.astype(float) / 255.0) * 95 + 80).astype(np.uint8)
    return cv2.cvtColor(low_contrast, cv2.COLOR_GRAY2BGR)


@pytest.fixture(scope="module")
def multi_issue_image(sample_document_image):
    """Create an image with multiple quality issues."""
    # Apply blur
    img = cv2.GaussianBlur(sample_document_image, (11, 11), 5)

    # Add noise using float arithmetic
    img_float = img.astype(np.float32)
    noise = _rng.normal(0, 30, img.shape).astype(np.float32)
    img = np.clip(img_float + noise, 0, 255).astype(np.uint8)

    # Apply skew
    h, w = img.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, 3, 1.0)
    return cv2.warpAffine(img, rotation_matrix, (w, h), borderValue=(255, 255, 255))


@pytest.fixture
def fixtures_dir():
    """Return path to test fixtures directory."""
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def sample_documents_dir(fixtures_dir):
    """Return path to sample documents directory."""
    return fixtures_dir / "sample_documents"


# =============================================================================
# Real Test Fixtures from data/test_fixtures/
# =============================================================================


@pytest.fixture
def test_fixtures_dir():
    """Return path to real test fixtures directory."""
    return Path(__file__).parent.parent.parent / "data" / "test_fixtures"


@pytest.fixture
def doclaynet_fixtures_dir(test_fixtures_dir):
    """Return path to DocLayNet PDF fixtures."""
    return test_fixtures_dir / "doclaynet"


@pytest.fixture
def tablebank_fixtures_dir(test_fixtures_dir):
    """Return path to TableBank image fixtures."""
    return test_fixtures_dir / "tablebank"


# Individual DocLayNet PDF fixtures
@pytest.fixture
def simple_text_pdf(doclaynet_fixtures_dir):
    """Simple text-heavy PDF document."""
    return doclaynet_fixtures_dir / "simple_text_1.pdf"


@pytest.fixture
def tables_figures_pdf(doclaynet_fixtures_dir):
    """PDF with tables and figures."""
    return doclaynet_fixtures_dir / "tables_figures_2.pdf"


@pytest.fixture
def multi_column_pdf(doclaynet_fixtures_dir):
    """Multi-column layout PDF."""
    return doclaynet_fixtures_dir / "multi_column_3.pdf"


@pytest.fixture
def skewed_pdf(doclaynet_fixtures_dir):
    """Skewed/rotated PDF pages."""
    return doclaynet_fixtures_dir / "skewed_4.pdf"


@pytest.fixture
def low_contrast_pdf(doclaynet_fixtures_dir):
    """Low contrast PDF scans."""
    return doclaynet_fixtures_dir / "low_contrast_5.pdf"


# Individual TableBank image fixtures
@pytest.fixture
def simple_table_image(tablebank_fixtures_dir):
    """Simple table image (PNG)."""
    path = tablebank_fixtures_dir / "simple_table_1.png"
    if path.exists():
        return cv2.imread(str(path))
    return None


@pytest.fixture
def complex_table_image(tablebank_fixtures_dir):
    """Complex table with merged cells (PNG)."""
    path = tablebank_fixtures_dir / "complex_table_2.png"
    if path.exists():
        return cv2.imread(str(path))
    return None


@pytest.fixture
def rotated_table_image(tablebank_fixtures_dir):
    """Rotated table image (JPG)."""
    path = tablebank_fixtures_dir / "rotated_3.jpg"
    if path.exists():
        return cv2.imread(str(path))
    return None


@pytest.fixture
def low_quality_table_image(tablebank_fixtures_dir):
    """Low quality/blurry table image (JPG)."""
    path = tablebank_fixtures_dir / "low_quality_4.jpg"
    if path.exists():
        return cv2.imread(str(path))
    return None


@pytest.fixture
def embedded_graphics_table_image(tablebank_fixtures_dir):
    """Table with embedded graphics (JPG)."""
    path = tablebank_fixtures_dir / "embedded_graphics_5.jpg"
    if path.exists():
        return cv2.imread(str(path))
    return None


# Collection fixtures for iterating over all files
@pytest.fixture
def all_doclaynet_pdfs(doclaynet_fixtures_dir):
    """Return list of all DocLayNet PDF fixture paths."""
    if not doclaynet_fixtures_dir.exists():
        return []
    return list(doclaynet_fixtures_dir.glob("*.pdf"))


@pytest.fixture
def all_tablebank_images(tablebank_fixtures_dir):
    """Return list of all TableBank image fixture paths."""
    if not tablebank_fixtures_dir.exists():
        return []
    images = list(tablebank_fixtures_dir.glob("*.png"))
    images.extend(tablebank_fixtures_dir.glob("*.jpg"))
    return images
