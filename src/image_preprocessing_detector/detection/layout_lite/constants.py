"""Shared constants for layout-lite detection."""

# Figure detection constants
MORPH_KERNEL_SIZE = (3, 3)  # Morphological gradient kernel for text stroke detection
GRADIENT_THRESHOLD = 30  # Gradient intensity threshold for text pixel detection

# Column detection constants
VALLEY_THRESHOLD = 0.05  # Less than 5% pixel density indicates gap
DEFAULT_MIN_COLUMN_GAP = 30  # Minimum gap width between columns in pixels
DEFAULT_MIN_COLUMN_WIDTH = 100  # Minimum column width in pixels

# Table detection constants
DEFAULT_MIN_HORIZONTAL_LINES = 10  # Minimum horizontal lines for table detection
DEFAULT_MIN_VERTICAL_LINES = 5  # Minimum vertical lines for table detection
DEFAULT_GRID_INTERSECTION_THRESHOLD = 0.3  # Minimum intersection ratio for grid
CANNY_LOW_THRESHOLD = 50  # Canny edge detection low threshold
CANNY_HIGH_THRESHOLD = 150  # Canny edge detection high threshold
HOUGH_THRESHOLD = 50  # Hough transform threshold
MAX_LINE_GAP = 10  # Maximum gap between line segments
ANGLE_TOLERANCE = 10  # Degrees tolerance for horizontal/vertical classification

# Figure detection constants
DEFAULT_MIN_FIGURE_AREA_RATIO = 0.20  # Minimum area ratio for figure (20%)
DEFAULT_MAX_TEXT_DENSITY = 0.05  # Maximum text density for figure (5%)

# Fuzzy scan detection constants
DEFAULT_BLUR_THRESHOLD = 0.7  # Minimum blur score for fuzzy scan
DEFAULT_NOISE_THRESHOLD = 0.5  # Minimum noise score for fuzzy scan
SHARP_IMAGE_VARIANCE = 500.0  # Laplacian variance for sharp images
CLEAN_IMAGE_STD = 30.0  # Standard deviation for clean images

# Watermark detection constants
DEFAULT_LOW_FREQ_THRESHOLD = 0.15  # Minimum low-frequency energy for watermark
FREQ_CENTER_SIZE_RATIO = 10  # Frequency domain center size (1/10th of dimension)
WATERMARK_OPACITY_NORMALIZER = 50.0  # Normalization factor for opacity score

# Colorful background detection constants
DEFAULT_MIN_UNIQUE_COLORS = 100  # Minimum unique colors for colorful background
DEFAULT_MIN_AVG_SATURATION = 0.3  # Minimum average saturation
HIST_H_BINS = 16  # Histogram bins for hue
HIST_S_BINS = 8  # Histogram bins for saturation
HIST_V_BINS = 8  # Histogram bins for value
SIGNIFICANT_COLOR_THRESHOLD = 0.001  # Pixel count threshold (0.1% of total)

# Gaussian blur kernel size
GAUSSIAN_KERNEL_SIZE = (5, 5)
