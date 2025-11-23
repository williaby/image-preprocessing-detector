"""E2E test fixtures and configuration."""

import shutil
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for test outputs."""
    temp_dir = tempfile.mkdtemp(prefix="e2e_test_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_document_image():
    """Create a synthetic document image for testing."""
    # Create a document-like image (white background with text blocks)
    img = np.ones((3300, 2550, 3), dtype=np.uint8) * 255

    # Add header text block
    cv2.rectangle(img, (200, 100), (2350, 200), (0, 0, 0), -1)

    # Add body text blocks (simulating paragraphs)
    for y in range(300, 2800, 100):
        # Vary line lengths to simulate text
        width = np.random.randint(1800, 2100)
        cv2.rectangle(img, (200, y), (200 + width, y + 20), (30, 30, 30), -1)

    # Add a figure placeholder
    cv2.rectangle(img, (200, 2900), (1200, 3200), (200, 200, 200), -1)
    cv2.rectangle(img, (200, 2900), (1200, 3200), (100, 100, 100), 2)

    return img


@pytest.fixture
def sample_blurry_image(sample_document_image):
    """Create a blurry version of the sample document."""
    return cv2.GaussianBlur(sample_document_image, (21, 21), 10)


@pytest.fixture
def sample_noisy_image(sample_document_image):
    """Create a noisy version of the sample document."""
    # Use float arithmetic to properly add Gaussian noise
    img_float = sample_document_image.astype(np.float32)
    # Use higher sigma (50) to ensure detection - thresholds are: medium=5, high=12, critical=20
    noise = np.random.normal(0, 50, sample_document_image.shape).astype(np.float32)
    return np.clip(img_float + noise, 0, 255).astype(np.uint8)


@pytest.fixture
def sample_skewed_image(sample_document_image):
    """Create a skewed version of the sample document."""
    h, w = sample_document_image.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, 5, 1.0)  # 5 degree rotation
    return cv2.warpAffine(
        sample_document_image, rotation_matrix, (w, h), borderValue=(255, 255, 255)
    )


@pytest.fixture
def sample_low_contrast_image(sample_document_image):
    """Create a low contrast version of the sample document."""
    # Reduce contrast by compressing intensity range
    gray = cv2.cvtColor(sample_document_image, cv2.COLOR_BGR2GRAY)
    # Map 0-255 to 80-175 (low contrast)
    low_contrast = ((gray.astype(float) / 255.0) * 95 + 80).astype(np.uint8)
    return cv2.cvtColor(low_contrast, cv2.COLOR_GRAY2BGR)


@pytest.fixture
def multi_issue_image(sample_document_image):
    """Create an image with multiple quality issues."""
    # Apply blur
    img = cv2.GaussianBlur(sample_document_image, (11, 11), 5)

    # Add noise using float arithmetic
    img_float = img.astype(np.float32)
    noise = np.random.normal(0, 30, img.shape).astype(np.float32)
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
