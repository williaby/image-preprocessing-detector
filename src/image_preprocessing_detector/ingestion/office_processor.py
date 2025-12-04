"""Office Document Processor Module.

Extracts embedded images from Microsoft Office documents (.docx, .xlsx, .pptx)
for preprocessing in the IQA pipeline.

Phase 8 Implementation - Uses Docling for document parsing when available,
with fallback to python-docx/openpyxl/python-pptx for image extraction.

Scope:
- Extract ALL embedded images (charts, diagrams, photos, scanned inserts)
- Apply standard image preprocessing to each extracted image
- Generate per-image metadata for Project B handoff

Out of Scope (Project B responsibility):
- Text extraction from office documents
- Document structure parsing
- Table/formatting extraction
"""

import io
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from image_preprocessing_detector.schema import DocumentType
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)

# File extension to document type mapping
OFFICE_EXTENSIONS: dict[str, DocumentType] = {
    ".docx": DocumentType.OFFICE_WORD,
    ".doc": DocumentType.OFFICE_WORD,
    ".xlsx": DocumentType.OFFICE_EXCEL,
    ".xls": DocumentType.OFFICE_EXCEL,
    ".pptx": DocumentType.OFFICE_POWERPOINT,
    ".ppt": DocumentType.OFFICE_POWERPOINT,
}

# MIME type to document type mapping
OFFICE_MIME_TYPES: dict[str, DocumentType] = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocumentType.OFFICE_WORD,
    "application/msword": DocumentType.OFFICE_WORD,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": DocumentType.OFFICE_EXCEL,
    "application/vnd.ms-excel": DocumentType.OFFICE_EXCEL,
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": DocumentType.OFFICE_POWERPOINT,
    "application/vnd.ms-powerpoint": DocumentType.OFFICE_POWERPOINT,
}

# Supported image formats within Office documents
SUPPORTED_IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".tiff",
    ".tif",
    ".emf",
    ".wmf",
}


@dataclass
class EmbeddedImage:
    """Represents an embedded image extracted from an office document.

    Attributes:
        image: The extracted image as numpy array (BGR format)
        image_index: Sequential index of the image in the document
        source_location: Location in document (e.g., "slide_3", "page_5", "sheet_2")
        original_filename: Original filename within the document archive
        original_size: Original image dimensions (width, height)
        format: Original image format (png, jpeg, etc.)
        metadata: Additional metadata from extraction
    """

    image: np.ndarray
    image_index: int
    source_location: str
    original_filename: str
    original_size: tuple[int, int]
    format: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OfficeDocumentInfo:
    """Information about an office document.

    Attributes:
        document_type: Type of office document
        file_path: Path to the document
        num_images: Number of embedded images found
        images: List of extracted embedded images
        extraction_method: Method used for extraction (docling, native, zipfile)
        errors: Any errors encountered during extraction
    """

    document_type: DocumentType
    file_path: str
    num_images: int
    images: list[EmbeddedImage]
    extraction_method: str
    errors: list[str] = field(default_factory=list)


class OfficeProcessor:
    """Processor for extracting embedded images from Office documents.

    Supports Word (.docx), Excel (.xlsx), and PowerPoint (.pptx) documents.
    Extracts all embedded images for preprocessing in the IQA pipeline.

    Example:
        >>> processor = OfficeProcessor()
        >>> doc_info = processor.process("presentation.pptx")
        >>> for img in doc_info.images:
        ...     print(f"Image {img.image_index} from {img.source_location}")
        ...     # Process image through IQA pipeline
    """

    def __init__(self, use_docling: bool = True) -> None:
        """Initialize the office processor.

        Args:
            use_docling: Whether to try using Docling for extraction (falls back if unavailable)
        """
        self.use_docling = use_docling
        self._docling_available = (
            self._check_docling_available() if use_docling else False
        )

        logger.info(
            "Office processor initialized",
            use_docling=use_docling,
            docling_available=self._docling_available,
        )

    def _check_docling_available(self) -> bool:
        """Check if Docling library is available."""
        try:
            import docling  # noqa: F401
        except ImportError:
            logger.debug("Docling not available, using fallback extraction")
            return False
        else:
            return True

    def detect_document_type(self, file_path: str | Path) -> DocumentType | None:
        """Detect office document type from file extension.

        Args:
            file_path: Path to the document

        Returns:
            DocumentType if office document, None otherwise
        """
        path = Path(file_path)
        ext = path.suffix.lower()
        return OFFICE_EXTENSIONS.get(ext)

    def is_office_document(self, file_path: str | Path) -> bool:
        """Check if file is a supported office document.

        Args:
            file_path: Path to the document

        Returns:
            True if office document, False otherwise
        """
        return self.detect_document_type(file_path) is not None

    def process(self, file_path: str | Path) -> OfficeDocumentInfo:
        """Process an office document and extract embedded images.

        Args:
            file_path: Path to the office document

        Returns:
            OfficeDocumentInfo with extracted images and metadata

        Raises:
            ValueError: If file is not a supported office document
            FileNotFoundError: If file does not exist
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        doc_type = self.detect_document_type(path)
        if doc_type is None:
            raise ValueError(f"Unsupported file type: {path.suffix}")

        logger.info(
            "Processing office document",
            file_path=str(path),
            document_type=doc_type.value,
        )

        # Try Docling first if available
        if self._docling_available:
            try:
                return self._extract_with_docling(path, doc_type)
            except Exception as e:
                logger.warning(
                    f"Docling extraction failed, falling back to native: {e}"
                )

        # Fallback to native extraction (ZIP-based for OOXML formats)
        return self._extract_from_zip(path, doc_type)

    def _extract_with_docling(
        self, file_path: Path, doc_type: DocumentType
    ) -> OfficeDocumentInfo:
        """Extract images using Docling library.

        Args:
            file_path: Path to the document
            doc_type: Type of office document

        Returns:
            OfficeDocumentInfo with extracted images
        """
        # Note: This is a placeholder for Docling integration
        # Docling API may vary - this shows the expected interface
        try:
            from docling.document_converter import DocumentConverter

            converter = DocumentConverter()
            result = converter.convert(str(file_path))

            images: list[EmbeddedImage] = []
            errors: list[str] = []

            # Extract images from Docling result
            # The actual API may differ based on Docling version
            if hasattr(result, "document") and hasattr(result.document, "pictures"):
                for idx, picture in enumerate(result.document.pictures):
                    try:
                        # Convert picture data to numpy array
                        if hasattr(picture, "image") and picture.image is not None:
                            pil_image = picture.image
                            if isinstance(pil_image, Image.Image):
                                # Convert PIL to numpy (BGR for OpenCV compatibility)
                                np_image = np.array(pil_image)
                                if len(np_image.shape) == 3 and np_image.shape[2] == 3:
                                    np_image = np_image[:, :, ::-1]  # RGB to BGR

                                images.append(
                                    EmbeddedImage(
                                        image=np_image,
                                        image_index=idx,
                                        source_location=f"page_{getattr(picture, 'page', 0)}",
                                        original_filename=f"image_{idx}",
                                        original_size=(
                                            np_image.shape[1],
                                            np_image.shape[0],
                                        ),
                                        format="unknown",
                                        metadata={"source": "docling"},
                                    )
                                )
                    except Exception as e:
                        errors.append(f"Failed to extract image {idx}: {e}")

            logger.info(
                "Docling extraction complete",
                num_images=len(images),
                num_errors=len(errors),
            )

            return OfficeDocumentInfo(
                document_type=doc_type,
                file_path=str(file_path),
                num_images=len(images),
                images=images,
                extraction_method="docling",
                errors=errors,
            )

        except (OSError, RuntimeError, ValueError):
            # OSError: file access errors
            # RuntimeError: Docling internal errors
            # ValueError: invalid document format
            logger.exception("Docling extraction failed for %s", file_path)
            raise

    def _extract_from_zip(
        self, file_path: Path, doc_type: DocumentType
    ) -> OfficeDocumentInfo:
        """Extract images from OOXML documents using ZIP extraction.

        OOXML formats (.docx, .xlsx, .pptx) are ZIP archives containing
        media files in specific directories.

        Args:
            file_path: Path to the document
            doc_type: Type of office document

        Returns:
            OfficeDocumentInfo with extracted images
        """
        images: list[EmbeddedImage] = []
        errors: list[str] = []

        # Image directories in OOXML formats
        media_paths = {
            DocumentType.OFFICE_WORD: ["word/media/"],
            DocumentType.OFFICE_EXCEL: ["xl/media/"],
            DocumentType.OFFICE_POWERPOINT: ["ppt/media/"],
        }

        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                # Get list of all files in archive
                file_list = zf.namelist()

                # Find media files
                media_prefixes = media_paths.get(doc_type, [])
                image_idx = 0

                for file_name in file_list:
                    # Check if file is in media directory
                    if not any(
                        file_name.startswith(prefix) for prefix in media_prefixes
                    ):
                        continue

                    # Check if file is an image
                    ext = Path(file_name).suffix.lower()
                    if ext not in SUPPORTED_IMAGE_EXTENSIONS:
                        continue

                    try:
                        # Extract and load image
                        image_data = zf.read(file_name)
                        pil_image = Image.open(io.BytesIO(image_data))

                        # Convert to numpy array (BGR for OpenCV)
                        np_image = np.array(pil_image.convert("RGB"))
                        np_image = np_image[:, :, ::-1]  # RGB to BGR

                        # Determine source location from path
                        source_location = self._determine_source_location(
                            file_name, doc_type
                        )

                        images.append(
                            EmbeddedImage(
                                image=np_image,
                                image_index=image_idx,
                                source_location=source_location,
                                original_filename=Path(file_name).name,
                                original_size=(pil_image.width, pil_image.height),
                                format=ext.lstrip("."),
                                metadata={
                                    "archive_path": file_name,
                                    "source": "zipfile",
                                },
                            )
                        )
                        image_idx += 1

                    except Exception as e:
                        errors.append(f"Failed to extract {file_name}: {e}")
                        logger.warning(f"Failed to extract image from {file_name}: {e}")

        except zipfile.BadZipFile:
            errors.append("Invalid or corrupted ZIP archive")
            logger.exception("Invalid ZIP archive: %s", file_path)

        logger.info(
            "ZIP extraction complete",
            file_path=str(file_path),
            num_images=len(images),
            num_errors=len(errors),
        )

        return OfficeDocumentInfo(
            document_type=doc_type,
            file_path=str(file_path),
            num_images=len(images),
            images=images,
            extraction_method="zipfile",
            errors=errors,
        )

    def _determine_source_location(
        self, archive_path: str, doc_type: DocumentType
    ) -> str:
        """Determine the source location of an image within the document.

        Args:
            archive_path: Path within the ZIP archive
            doc_type: Type of office document

        Returns:
            Human-readable source location string
        """
        # For now, use a simple naming based on document type
        # More sophisticated location tracking would require parsing rels files
        filename = Path(archive_path).stem

        if doc_type == DocumentType.OFFICE_WORD:
            return f"document_{filename}"
        if doc_type == DocumentType.OFFICE_EXCEL:
            return f"workbook_{filename}"
        if doc_type == DocumentType.OFFICE_POWERPOINT:
            return f"presentation_{filename}"
        return f"unknown_{filename}"

    def extract_images_to_files(
        self,
        doc_info: OfficeDocumentInfo,
        output_dir: str | Path,
        output_format: str = "png",
    ) -> list[str]:
        """Extract embedded images to files.

        Args:
            doc_info: Document info from process()
            output_dir: Directory to save images
            output_format: Output image format (png, jpg)

        Returns:
            List of saved file paths
        """
        import cv2

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        saved_paths: list[str] = []

        for img in doc_info.images:
            filename = f"embedded_{img.image_index:03d}.{output_format}"
            file_path = output_path / filename

            cv2.imwrite(str(file_path), img.image)
            saved_paths.append(str(file_path))

            logger.debug(f"Saved embedded image to {file_path}")

        logger.info(f"Saved {len(saved_paths)} images to {output_dir}")
        return saved_paths


def detect_office_type(file_path: str | Path) -> DocumentType | None:
    """Convenience function to detect office document type.

    Args:
        file_path: Path to the document

    Returns:
        DocumentType if office document, None otherwise

    Example:
        >>> doc_type = detect_office_type("report.docx")
        >>> if doc_type:
        ...     print(f"Document type: {doc_type.value}")
    """
    processor = OfficeProcessor(use_docling=False)
    return processor.detect_document_type(file_path)


def extract_office_images(
    file_path: str | Path,
    use_docling: bool = True,
) -> OfficeDocumentInfo:
    """Convenience function to extract images from office document.

    Args:
        file_path: Path to the office document
        use_docling: Whether to use Docling if available

    Returns:
        OfficeDocumentInfo with extracted images

    Example:
        >>> doc_info = extract_office_images("presentation.pptx")
        >>> print(f"Found {doc_info.num_images} embedded images")
        >>> for img in doc_info.images:
        ...     # Process each image through IQA pipeline
        ...     pass
    """
    processor = OfficeProcessor(use_docling=use_docling)
    return processor.process(file_path)
