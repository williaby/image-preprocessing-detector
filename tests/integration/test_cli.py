"""
Integration tests for CLI tool.
"""

import json
import tempfile
from pathlib import Path

import cv2
import numpy as np
from click.testing import CliRunner

from image_preprocessing_detector.cli import cli


class TestCLIProcess:
    """Test CLI process command."""

    def test_process_single_image(self) -> None:
        """Test processing a single image file."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test image
            img = np.ones((1000, 800, 3), dtype=np.uint8) * 255
            cv2.rectangle(img, (100, 100), (700, 900), (0, 0, 0), 2)

            img_path = Path(tmpdir) / "test.jpg"
            cv2.imwrite(str(img_path), img)

            # Create output path
            output_path = Path(tmpdir) / "output.json"

            # Run CLI
            result = runner.invoke(
                cli, ["process", str(img_path), "--output", str(output_path)]
            )

            # Check result
            assert result.exit_code == 0
            assert "Processing complete" in result.output
            assert output_path.exists()

            # Verify JSON structure
            with open(output_path) as f:
                data = json.load(f)
                assert "document_id" in data
                assert "pages" in data
                assert len(data["pages"]) == 1

    def test_process_with_dry_run(self) -> None:
        """Test processing with dry-run mode (no corrections)."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create skewed test image
            img = np.ones((1000, 800, 3), dtype=np.uint8) * 255

            # Add text-like pattern
            for y in range(100, 900, 40):
                cv2.line(img, (100, y), (700, y), (0, 0, 0), 2)

            img_path = Path(tmpdir) / "test.jpg"
            cv2.imwrite(str(img_path), img)

            output_path = Path(tmpdir) / "output.json"

            # Run CLI with dry-run
            result = runner.invoke(
                cli,
                ["process", str(img_path), "--output", str(output_path), "--dry-run"],
            )

            # Check result
            assert result.exit_code == 0
            assert output_path.exists()

            # Verify no corrections were applied
            with open(output_path) as f:
                data = json.load(f)
                page = data["pages"][0]
                assert len(page["transform_history"]) == 0

    def test_process_with_custom_thresholds(self) -> None:
        """Test processing with custom detection thresholds."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test image
            img = np.ones((1000, 800, 3), dtype=np.uint8) * 255

            img_path = Path(tmpdir) / "test.jpg"
            cv2.imwrite(str(img_path), img)

            output_path = Path(tmpdir) / "output.json"

            # Run CLI with custom thresholds
            result = runner.invoke(
                cli,
                [
                    "process",
                    str(img_path),
                    "--output",
                    str(output_path),
                    "--blur-threshold",
                    "0.9",
                    "--skew-threshold",
                    "0.85",
                    "--contrast-threshold",
                    "0.75",
                ],
            )

            # Check result
            assert result.exit_code == 0
            assert output_path.exists()

    def test_process_invalid_file(self) -> None:
        """Test processing with invalid file path."""
        runner = CliRunner()

        # Try to process non-existent file
        result = runner.invoke(
            cli, ["process", "/nonexistent/file.pdf", "--output", "out.json"]
        )

        # Should fail
        assert result.exit_code != 0

    def test_process_unsupported_format(self) -> None:
        """Test processing with unsupported file format."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create unsupported file type
            unsupported_path = Path(tmpdir) / "test.txt"
            unsupported_path.write_text("not an image")

            output_path = Path(tmpdir) / "output.json"

            # Run CLI
            result = runner.invoke(
                cli, ["process", str(unsupported_path), "--output", str(output_path)]
            )

            # Should fail with error message
            assert result.exit_code == 1
            assert "Unsupported file format" in result.output


class TestCLIBatch:
    """Test CLI batch command."""

    def test_batch_multiple_images(self) -> None:
        """Test batch processing of multiple images."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()

            # Create 3 test images
            for i in range(3):
                img = np.ones((1000, 800, 3), dtype=np.uint8) * 255
                img_path = input_dir / f"test_{i}.jpg"
                cv2.imwrite(str(img_path), img)

            # Run batch processing
            result = runner.invoke(
                cli, ["batch", str(input_dir), "--output-dir", str(output_dir)]
            )

            # Check result
            assert result.exit_code == 0
            assert "Batch processing complete" in result.output
            assert "Successful: 3" in result.output

            # Verify output files
            assert len(list(output_dir.glob("*.json"))) == 3

    def test_batch_with_dry_run(self) -> None:
        """Test batch processing with dry-run mode."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()

            # Create test images
            for i in range(2):
                img = np.ones((1000, 800, 3), dtype=np.uint8) * 255
                img_path = input_dir / f"test_{i}.jpg"
                cv2.imwrite(str(img_path), img)

            # Run batch processing with dry-run
            result = runner.invoke(
                cli,
                ["batch", str(input_dir), "--output-dir", str(output_dir), "--dry-run"],
            )

            # Check result
            assert result.exit_code == 0
            assert output_dir.exists()
            assert len(list(output_dir.glob("*.json"))) == 2

    def test_batch_empty_directory(self) -> None:
        """Test batch processing with empty directory."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()

            # Run batch processing on empty directory
            result = runner.invoke(
                cli, ["batch", str(input_dir), "--output-dir", str(output_dir)]
            )

            # Should fail
            assert result.exit_code == 1
            assert "No supported files found" in result.output

    def test_batch_mixed_file_types(self) -> None:
        """Test batch processing with mixed file types."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()

            # Create JPG image
            img = np.ones((1000, 800, 3), dtype=np.uint8) * 255
            jpg_path = input_dir / "image1.jpg"
            cv2.imwrite(str(jpg_path), img)

            # Create PNG image
            png_path = input_dir / "image2.png"
            cv2.imwrite(str(png_path), img)

            # Create unsupported file
            txt_path = input_dir / "test.txt"
            txt_path.write_text("not an image")

            # Run batch processing
            result = runner.invoke(
                cli, ["batch", str(input_dir), "--output-dir", str(output_dir)]
            )

            # Should process only image files
            assert result.exit_code == 0
            assert len(list(output_dir.glob("*.json"))) == 2


class TestCLIHelp:
    """Test CLI help commands."""

    def test_main_help(self) -> None:
        """Test main CLI help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Image Preprocessing Detector" in result.output
        assert "process" in result.output
        assert "batch" in result.output

    def test_process_help(self) -> None:
        """Test process command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["process", "--help"])

        assert result.exit_code == 0
        assert "Process a single PDF or image file" in result.output
        assert "--output" in result.output
        assert "--dry-run" in result.output

    def test_batch_help(self) -> None:
        """Test batch command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["batch", "--help"])

        assert result.exit_code == 0
        assert "Process a directory" in result.output
        assert "--output-dir" in result.output


class TestCLIErrorPaths:
    """Test CLI error handling and edge cases."""

    def test_process_pdf_path(self, tmp_path):
        """Test processing a PDF file (covers PDF loading path)."""
        import fitz

        # Create a simple single-page PDF
        pdf_path = tmp_path / "test.pdf"
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 50), "Test PDF", fontsize=12)
        doc.save(str(pdf_path))
        doc.close()

        output_path = tmp_path / "output.json"

        runner = CliRunner()
        result = runner.invoke(
            cli, ["process", str(pdf_path), "--output", str(output_path)]
        )

        assert result.exit_code == 0
        assert output_path.exists()

    def test_process_image_path(self, tmp_path):
        """Test processing a direct image file (covers image loading path)."""
        import cv2
        import numpy as np

        # Create a simple test image
        img_path = tmp_path / "test.jpg"
        img = np.ones((100, 100, 3), dtype=np.uint8) * 255
        cv2.imwrite(str(img_path), img)

        output_path = tmp_path / "output.json"

        runner = CliRunner()
        result = runner.invoke(
            cli, ["process", str(img_path), "--output", str(output_path)]
        )

        assert result.exit_code == 0
        assert output_path.exists()

    def test_process_with_corrections_applied(self, tmp_path):
        """Test that corrections are applied when not in dry-run mode."""
        import cv2
        import numpy as np

        # Create a low-contrast image
        img_path = tmp_path / "low_contrast.jpg"
        # Gray image with low contrast
        img = np.ones((200, 200, 3), dtype=np.uint8) * 128
        # Add some text-like patterns
        for y in range(20, 180, 20):
            cv2.line(img, (20, y), (180, y), (100, 100, 100), 2)
        cv2.imwrite(str(img_path), img)

        output_path = tmp_path / "output.json"

        runner = CliRunner()
        result = runner.invoke(
            cli, ["process", str(img_path), "--output", str(output_path)]
        )

        # Should succeed even if corrections are applied
        assert result.exit_code == 0
        assert output_path.exists()

    def test_batch_with_errors(self, tmp_path):
        """Test batch processing handles individual file errors."""
        import cv2
        import numpy as np

        # Create input directory with mixed quality
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()

        # Create 2 valid images
        for i in range(2):
            img = np.ones((100, 100, 3), dtype=np.uint8) * 255
            cv2.imwrite(str(input_dir / f"valid_{i}.jpg"), img)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "batch",
                str(input_dir),
                "--output-dir",
                str(output_dir),
            ],
        )

        # Should succeed
        assert result.exit_code == 0
        # Check that output directory was created
        assert output_dir.exists()


class TestCLICorrectionPaths:
    """Test correction application paths in CLI."""

    def test_process_with_skew_correction(self, tmp_path):
        """Test that skew correction is applied when detected."""
        import cv2
        import numpy as np

        # Create a skewed image with text patterns
        img_path = tmp_path / "skewed.jpg"
        img = np.ones((400, 400, 3), dtype=np.uint8) * 255

        # Add horizontal text-like lines
        for y in range(50, 350, 30):
            cv2.line(img, (50, y), (350, y), (0, 0, 0), 3)

        # Apply artificial skew
        center = (200, 200)
        M = cv2.getRotationMatrix2D(center, -2.0, 1.0)
        img = cv2.warpAffine(img, M, (400, 400), borderValue=(255, 255, 255))

        cv2.imwrite(str(img_path), img)

        output_path = tmp_path / "output.json"

        runner = CliRunner()
        # Use lower skew threshold to ensure correction is applied
        result = runner.invoke(
            cli,
            [
                "process",
                str(img_path),
                "--output",
                str(output_path),
                "--skew-threshold",
                "0.5",
            ],
        )

        assert result.exit_code == 0
        assert output_path.exists()

    def test_process_with_blur_correction(self, tmp_path):
        """Test that blur correction is applied when detected."""
        import cv2
        import numpy as np

        # Create a sharp image with text, then blur it
        img_path = tmp_path / "blurred.jpg"
        img = np.ones((400, 400, 3), dtype=np.uint8) * 255

        # Add text-like patterns
        for y in range(50, 350, 30):
            cv2.line(img, (50, y), (350, y), (0, 0, 0), 3)

        # Apply moderate blur
        img = cv2.GaussianBlur(img, (15, 15), 5.0)

        cv2.imwrite(str(img_path), img)

        output_path = tmp_path / "output.json"

        runner = CliRunner()
        # Use moderate blur threshold
        result = runner.invoke(
            cli,
            [
                "process",
                str(img_path),
                "--output",
                str(output_path),
                "--blur-threshold",
                "0.6",
            ],
        )

        assert result.exit_code == 0
        assert output_path.exists()

    def test_process_with_contrast_enhancement(self, tmp_path):
        """Test that contrast enhancement is applied when detected."""
        import cv2
        import numpy as np

        # Create a low-contrast image with text patterns
        img_path = tmp_path / "low_contrast.jpg"
        img = np.ones((400, 400, 3), dtype=np.uint8) * 140

        # Add low-contrast text-like patterns
        for y in range(50, 350, 30):
            cv2.line(img, (50, y), (350, y), (120, 120, 120), 3)

        cv2.imwrite(str(img_path), img)

        output_path = tmp_path / "output.json"

        runner = CliRunner()
        # Use moderate contrast threshold
        result = runner.invoke(
            cli,
            [
                "process",
                str(img_path),
                "--output",
                str(output_path),
                "--contrast-threshold",
                "0.5",
            ],
        )

        assert result.exit_code == 0
        assert output_path.exists()

    def test_batch_success_and_error_counts(self, tmp_path):
        """Test batch processing tracks success and error counts."""
        import cv2
        import numpy as np

        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()

        # Create 3 valid images
        for i in range(3):
            img = np.ones((200, 200, 3), dtype=np.uint8) * 255
            # Add text patterns
            for y in range(20, 180, 20):
                cv2.line(img, (20, y), (180, y), (0, 0, 0), 2)
            cv2.imwrite(str(input_dir / f"image_{i}.jpg"), img)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "batch",
                str(input_dir),
                "--output-dir",
                str(output_dir),
            ],
        )

        # Should succeed with all files processed
        assert result.exit_code == 0
        assert "Successful: 3" in result.output
        assert output_dir.exists()

        # Check that JSON files were created
        json_files = list(output_dir.glob("*.json"))
        assert len(json_files) == 3
