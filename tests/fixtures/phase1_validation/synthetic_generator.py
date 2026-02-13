"""
Synthetic image generator for IQA validation.

Generates test images with known, controlled defects:
- Skew: Rotation at precise angles
- Blur: Gaussian blur with known kernel sizes
- Contrast: Controlled contrast reduction
"""

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw


class SyntheticImageGenerator:
    """
    Generates synthetic document images with controlled defects.

    Use for validation and accuracy testing of IQA detectors.
    """

    def __init__(self, output_dir: str | Path = "validation/synthetic_images"):
        """
        Initialize synthetic image generator.

        Args:
            output_dir: Directory to save generated images
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_text_document(
        self,
        width: int = 2480,
        height: int = 3509,
        _dpi: int = 300,
        background_color: tuple[int, int, int] = (255, 255, 255),
        text_color: tuple[int, int, int] = (0, 0, 0),
    ) -> np.ndarray:
        """
        Generate a synthetic document page with text.

        Args:
            width: Image width in pixels
            height: Image height in pixels
            _dpi: DPI resolution (reserved for future use)
            background_color: RGB background color
            text_color: RGB text color

        Returns:
            Clean document image as numpy array (BGR format)
        """
        # Create PIL image
        img = Image.new("RGB", (width, height), background_color)
        draw = ImageDraw.Draw(img)

        # Generate text content (simulate document)
        y_position = 100
        line_height = 60
        margin_left = 150

        # Title
        title_text = "SYNTHETIC DOCUMENT FOR IQA VALIDATION"
        draw.text((margin_left, y_position), title_text, fill=text_color)
        y_position += line_height * 2

        # Body paragraphs
        lorem_ipsum = [
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
            "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.",
            "Duis aute irure dolor in reprehenderit in voluptate velit esse.",
            "Excepteur sint occaecat cupidatat non proident, sunt in culpa.",
        ]

        for _ in range(15):  # Multiple paragraphs
            for line in lorem_ipsum:
                if y_position > height - 200:
                    break
                draw.text((margin_left, y_position), line, fill=text_color)
                y_position += line_height

            y_position += line_height  # Paragraph spacing

        # Convert to OpenCV BGR format
        img_array = np.array(img)
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

        return img_bgr

    def apply_skew(
        self, image: np.ndarray, angle_degrees: float
    ) -> tuple[np.ndarray, float]:
        """
        Apply controlled skew (rotation) to an image.

        Args:
            image: Input image (BGR format)
            angle_degrees: Rotation angle in degrees (-45 to +45)

        Returns:
            Tuple of (skewed_image, actual_angle)
        """
        h, w = image.shape[:2]
        center = (w // 2, h // 2)

        # Create rotation matrix
        M = cv2.getRotationMatrix2D(center, angle_degrees, 1.0)

        # Calculate new dimensions to avoid cropping
        cos = abs(M[0, 0])
        sin = abs(M[0, 1])
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))

        # Adjust transformation matrix
        M[0, 2] += (new_w / 2) - center[0]
        M[1, 2] += (new_h / 2) - center[1]

        # Apply rotation
        skewed = cv2.warpAffine(
            image,
            M,
            (new_w, new_h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255),
        )

        return skewed, angle_degrees

    def apply_blur(
        self, image: np.ndarray, kernel_size: int = 15
    ) -> tuple[np.ndarray, int]:
        """
        Apply Gaussian blur with known kernel size.

        Args:
            image: Input image (BGR format)
            kernel_size: Gaussian kernel size (odd number)

        Returns:
            Tuple of (blurred_image, kernel_size)
        """
        # Ensure kernel size is odd
        if kernel_size % 2 == 0:
            kernel_size += 1

        blurred = cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)

        return blurred, kernel_size

    def reduce_contrast(
        self, image: np.ndarray, factor: float = 0.5
    ) -> tuple[np.ndarray, float]:
        """
        Reduce image contrast by a known factor.

        Args:
            image: Input image (BGR format)
            factor: Contrast reduction factor (0.0-1.0, where 1.0 = no change)

        Returns:
            Tuple of (low_contrast_image, factor)
        """
        # Convert to float
        img_float = image.astype(float)

        # Calculate mean
        mean = img_float.mean()

        # Reduce contrast: blend with mean
        low_contrast = mean + (img_float - mean) * factor

        # Clip and convert back to uint8
        low_contrast = np.clip(low_contrast, 0, 255).astype(np.uint8)

        return low_contrast, factor

    def add_salt_pepper_noise(
        self, image: np.ndarray, salt_amount: float = 0.01, pepper_amount: float = 0.01
    ) -> tuple[np.ndarray, tuple[float, float]]:
        """
        Add salt (white) and pepper (black) noise to image.

        Args:
            image: Input image (BGR format)
            salt_amount: Percentage of pixels to whiten (0.0-1.0)
            pepper_amount: Percentage of pixels to darken (0.0-1.0)

        Returns:
            Tuple of (noisy_image, (salt_amount, pepper_amount))
        """
        noisy = image.copy()
        h, w = image.shape[:2]
        num_pixels = h * w
        rng = np.random.default_rng(42)

        # Add salt noise (white pixels)
        num_salt = int(num_pixels * salt_amount)
        salt_coords = [rng.integers(0, i, num_salt) for i in (h, w)]
        noisy[salt_coords[0], salt_coords[1], :] = 255

        # Add pepper noise (black pixels)
        num_pepper = int(num_pixels * pepper_amount)
        pepper_coords = [rng.integers(0, i, num_pepper) for i in (h, w)]
        noisy[pepper_coords[0], pepper_coords[1], :] = 0

        return noisy, (salt_amount, pepper_amount)

    def apply_bleed_through(
        self,
        image: np.ndarray,
        alpha: float = 0.3,
        offset_x: int = 5,
        offset_y: int = 5,
    ) -> tuple[np.ndarray, tuple[float, int, int]]:
        """
        Simulate ink bleed-through from reverse side of page.

        Args:
            image: Input image (BGR format)
            alpha: Bleed-through strength (0.0-1.0, higher = less visible)
            offset_x: Horizontal offset in pixels
            offset_y: Vertical offset in pixels

        Returns:
            Tuple of (image_with_bleed, (alpha, offset_x, offset_y))
        """
        h, w = image.shape[:2]

        # Create shifted (flipped) version to simulate reverse side
        reverse = cv2.flip(image, 0)  # Flip vertically

        # Shift the reverse image
        M = np.float32([[1, 0, offset_x], [0, 1, offset_y]])
        shifted_reverse = cv2.warpAffine(reverse, M, (w, h))

        # Blend with alpha (lower alpha = more visible bleed-through)
        bleed = cv2.addWeighted(image, 1.0, shifted_reverse, 1.0 - alpha, 0)

        return bleed, (alpha, offset_x, offset_y)

    def apply_morphological_op(
        self,
        image: np.ndarray,
        operation: str = "erode",
        kernel_size: int = 3,
        kernel_shape: str = "rect",
    ) -> tuple[np.ndarray, tuple[str, int, str]]:
        """
        Apply morphological operations (erosion, dilation, opening, closing).

        Args:
            image: Input image (BGR format)
            operation: One of 'erode', 'dilate', 'open', 'close'
            kernel_size: Morphological kernel size (odd number)
            kernel_shape: One of 'rect', 'ellipse', 'cross'

        Returns:
            Tuple of (processed_image, (operation, kernel_size, kernel_shape))
        """
        # Ensure kernel size is odd
        if kernel_size % 2 == 0:
            kernel_size += 1

        # Create kernel based on shape
        if kernel_shape == "ellipse":
            kernel = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE, (kernel_size, kernel_size)
            )
        elif kernel_shape == "cross":
            kernel = cv2.getStructuringElement(
                cv2.MORPH_CROSS, (kernel_size, kernel_size)
            )
        else:  # rect
            kernel = cv2.getStructuringElement(
                cv2.MORPH_RECT, (kernel_size, kernel_size)
            )

        # Apply operation
        if operation == "erode":
            result = cv2.erode(image, kernel, iterations=1)
        elif operation == "dilate":
            result = cv2.dilate(image, kernel, iterations=1)
        elif operation == "open":
            result = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)
        elif operation == "close":
            result = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)
        else:
            result = image

        return result, (operation, kernel_size, kernel_shape)

    def generate_gradient_set(
        self,
        degradation_type: str = "blur",
        num_samples: int = 20,
        param_range: tuple[float, float] = (1, 50),
    ) -> list[tuple[Path, dict]]:
        """
        Generate gradient test set for characteristic curve analysis.

        Creates images with gradually increasing degradation levels to plot
        detector response curves and tune thresholds precisely.

        Args:
            degradation_type: One of 'blur', 'skew', 'contrast', 'noise'
            num_samples: Number of gradient steps
            param_range: (min, max) range for degradation parameter

        Returns:
            List of (filepath, ground_truth) tuples
        """
        gradient_set = []
        base_img = self.generate_text_document()

        print(
            f"Generating {num_samples} gradient samples for {degradation_type} "
            f"(range: {param_range[0]}-{param_range[1]})"
        )

        # Generate linearly spaced parameter values
        param_values = np.linspace(param_range[0], param_range[1], num_samples)

        for i, param_value in enumerate(param_values):
            if degradation_type == "blur":
                # Blur kernel must be odd integer
                kernel_size = int(param_value)
                if kernel_size % 2 == 0:
                    kernel_size += 1
                degraded, _ = self.apply_blur(base_img.copy(), kernel_size)
                filepath = self.output_dir / f"gradient_blur_{i:03d}_k{kernel_size}.png"
                ground_truth = {
                    "degradation_type": "blur",
                    "parameter_value": kernel_size,
                    "step": i,
                }

            elif degradation_type == "skew":
                degraded, _ = self.apply_skew(base_img.copy(), param_value)
                filepath = (
                    self.output_dir / f"gradient_skew_{i:03d}_{param_value:.2f}deg.png"
                )
                ground_truth = {
                    "degradation_type": "skew",
                    "parameter_value": param_value,
                    "step": i,
                }

            elif degradation_type == "contrast":
                # Contrast factor (0.0 = no contrast, 1.0 = original)
                # Invert range so higher values = worse quality
                factor = 1.0 - (param_value / param_range[1])
                factor = max(0.01, min(1.0, factor))
                degraded, _ = self.reduce_contrast(base_img.copy(), factor)
                filepath = (
                    self.output_dir / f"gradient_contrast_{i:03d}_f{factor:.3f}.png"
                )
                ground_truth = {
                    "degradation_type": "contrast",
                    "parameter_value": factor,
                    "step": i,
                }

            elif degradation_type == "noise":
                # Noise amount (percentage of pixels)
                amount = param_value / 100.0  # Convert to 0.0-1.0
                degraded, _ = self.add_salt_pepper_noise(
                    base_img.copy(), amount, amount
                )
                filepath = self.output_dir / f"gradient_noise_{i:03d}_a{amount:.4f}.png"
                ground_truth = {
                    "degradation_type": "noise",
                    "parameter_value": amount,
                    "step": i,
                }

            else:
                continue

            # Save image
            cv2.imwrite(str(filepath), degraded)
            gradient_set.append((filepath, ground_truth))

        print(f"✓ Generated {len(gradient_set)} gradient samples")

        return gradient_set

    def generate_test_set(
        self,
        num_clean: int = 5,
        skew_angles: list[float] = None,
        blur_kernels: list[int] = None,
        contrast_factors: list[float] = None,
    ) -> dict[str, list[tuple[Path, dict]]]:
        """
        Generate a complete test set with various defects.

        Args:
            num_clean: Number of clean reference images
            skew_angles: List of skew angles to test (degrees)
            blur_kernels: List of blur kernel sizes to test
            contrast_factors: List of contrast reduction factors to test

        Returns:
            Dictionary mapping defect type to list of (file_path, ground_truth) tuples
        """
        if skew_angles is None:
            skew_angles = [0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 15.0, 30.0]

        if blur_kernels is None:
            blur_kernels = [5, 11, 15, 21, 31, 51]

        if contrast_factors is None:
            contrast_factors = [0.8, 0.6, 0.4, 0.3, 0.2, 0.1]

        test_set = {
            "clean": [],
            "skew": [],
            "blur": [],
            "contrast": [],
            "combined": [],
        }

        print(f"Generating synthetic test set in {self.output_dir}")

        # Generate clean reference images
        print(f"Generating {num_clean} clean reference images...")
        for i in range(num_clean):
            img = self.generate_text_document()
            filepath = self.output_dir / f"clean_{i:02d}.png"
            cv2.imwrite(str(filepath), img)

            ground_truth = {
                "has_skew": False,
                "skew_angle": 0.0,
                "is_blurred": False,
                "blur_kernel": 0,
                "is_low_contrast": False,
                "contrast_factor": 1.0,
            }
            test_set["clean"].append((filepath, ground_truth))

        # Generate skewed images
        print(f"Generating {len(skew_angles)} skewed images...")
        base_img = self.generate_text_document()
        for angle in skew_angles:
            skewed, actual_angle = self.apply_skew(base_img, angle)
            filepath = self.output_dir / f"skew_{angle:.1f}deg.png"
            cv2.imwrite(str(filepath), skewed)

            ground_truth = {
                "has_skew": abs(angle) > 0.5,
                "skew_angle": actual_angle,
                "is_blurred": False,
                "blur_kernel": 0,
                "is_low_contrast": False,
                "contrast_factor": 1.0,
            }
            test_set["skew"].append((filepath, ground_truth))

        # Generate blurred images
        print(f"Generating {len(blur_kernels)} blurred images...")
        base_img = self.generate_text_document()
        for kernel in blur_kernels:
            blurred, actual_kernel = self.apply_blur(base_img, kernel)
            filepath = self.output_dir / f"blur_k{kernel}.png"
            cv2.imwrite(str(filepath), blurred)

            ground_truth = {
                "has_skew": False,
                "skew_angle": 0.0,
                "is_blurred": kernel > 5,  # Threshold
                "blur_kernel": actual_kernel,
                "is_low_contrast": False,
                "contrast_factor": 1.0,
            }
            test_set["blur"].append((filepath, ground_truth))

        # Generate low-contrast images
        print(f"Generating {len(contrast_factors)} low-contrast images...")
        base_img = self.generate_text_document()
        for factor in contrast_factors:
            low_contrast, actual_factor = self.reduce_contrast(base_img, factor)
            filepath = self.output_dir / f"contrast_{factor:.1f}.png"
            cv2.imwrite(str(filepath), low_contrast)

            ground_truth = {
                "has_skew": False,
                "skew_angle": 0.0,
                "is_blurred": False,
                "blur_kernel": 0,
                "is_low_contrast": factor < 0.7,  # Threshold
                "contrast_factor": actual_factor,
            }
            test_set["contrast"].append((filepath, ground_truth))

        # Generate combined defects (realistic scenarios)
        print("Generating images with combined defects...")
        combinations = [
            (2.0, 11, 0.6),  # Mild: slight skew + mild blur + mild contrast
            (5.0, 15, 0.4),  # Moderate: moderate skew + blur + contrast
            (10.0, 21, 0.3),  # Severe: heavy skew + blur + contrast
        ]

        for i, (angle, kernel, factor) in enumerate(combinations):
            base_img = self.generate_text_document()
            img, _ = self.apply_skew(base_img, angle)
            img, _ = self.apply_blur(img, kernel)
            img, _ = self.reduce_contrast(img, factor)

            filepath = self.output_dir / f"combined_{i:02d}.png"
            cv2.imwrite(str(filepath), img)

            ground_truth = {
                "has_skew": abs(angle) > 0.5,
                "skew_angle": angle,
                "is_blurred": kernel > 5,
                "blur_kernel": kernel,
                "is_low_contrast": factor < 0.7,
                "contrast_factor": factor,
            }
            test_set["combined"].append((filepath, ground_truth))

        print(f"✓ Test set generated: {sum(len(v) for v in test_set.values())} images")

        return test_set


if __name__ == "__main__":
    # Generate test set
    generator = SyntheticImageGenerator()
    test_set = generator.generate_test_set()

    # Print summary
    print("\nTest Set Summary:")
    print("=" * 60)
    for defect_type, images in test_set.items():
        print(f"{defect_type.capitalize()}: {len(images)} images")
    print("=" * 60)
