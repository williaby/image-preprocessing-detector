"""Generate dynamic badges for benchmark results.

Creates badge JSON files that can be served via shields.io endpoint or
GitHub Pages for dynamic README badges.

Usage:
    python -m benchmarks.runners.generate_badges

"""

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def load_latest_aggregates(reports_dir: Path) -> dict[str, Any]:
    """Load latest aggregate results from all suites.

    Args:
        reports_dir: Path to reports directory

    Returns:
        Dictionary of suite -> aggregates
    """
    results: dict[str, Any] = {}

    if not reports_dir.exists():
        return results

    for suite_dir in reports_dir.iterdir():
        if not suite_dir.is_dir():
            continue

        # Find latest results
        timestamp_dirs = sorted(suite_dir.iterdir(), reverse=True)
        if not timestamp_dirs:
            continue

        results_file = timestamp_dirs[0] / "results.json"
        if results_file.exists():
            with open(results_file) as f:
                data = json.load(f)
                results[suite_dir.name] = data.get("aggregates", {})

    return results


def create_badge_json(label: str, message: str, color: str) -> dict[str, Any]:
    """Create badge JSON in shields.io endpoint format.

    Args:
        label: Badge label (left side)
        message: Badge message (right side)
        color: Badge color (green, yellow, red, blue, etc.)

    Returns:
        Badge JSON dictionary
    """
    return {
        "schemaVersion": 1,
        "label": label,
        "message": message,
        "color": color,
    }


def get_color_for_metric(
    value: float, target: float, lower_is_better: bool = False
) -> str:
    """Determine badge color based on metric performance.

    Args:
        value: Current value
        target: Target value
        lower_is_better: Whether lower is better

    Returns:
        Color name (green, yellow, red)
    """
    if lower_is_better:
        if value <= target:
            return "brightgreen"
        if value <= target * 1.2:
            return "yellow"
        return "red"

    if value >= target:
        return "brightgreen"
    if value >= target * 0.8:
        return "yellow"
    return "red"


@dataclass(frozen=True)
class BadgeDefinition:
    suite: str
    metric_key: str
    label: str
    target: float
    lower_is_better: bool
    format_str: str


BadgeResult = tuple[str, str, str]
PLACEHOLDER_COLOR = "lightgrey"
NO_DATA_MESSAGE = "no data"
PENDING_MESSAGE = "pending"


BADGE_DEFINITIONS: list[BadgeDefinition] = [
    # IQA Metrics
    BadgeDefinition(
        suite="synthetic-iqa-blur-full",
        metric_key="blur_correlation",
        label="IQA Blur r",
        target=0.85,
        lower_is_better=False,
        format_str=".3f",
    ),
    BadgeDefinition(
        suite="synthetic-iqa-blur-full",
        metric_key="blur_rmse",
        label="IQA Blur RMSE",
        target=0.05,
        lower_is_better=True,
        format_str=".3f",
    ),
    BadgeDefinition(
        suite="synthetic-iqa-skew-full",
        metric_key="skew_mae",
        label="IQA Skew MAE",
        target=0.5,
        lower_is_better=True,
        format_str=".2f°",
    ),
    BadgeDefinition(
        suite="synthetic-iqa-skew-full",
        metric_key="deskew_success_rate",
        label="Deskew Success",
        target=0.99,
        lower_is_better=False,
        format_str=".1%",
    ),
    BadgeDefinition(
        suite="synthetic-iqa-noise-full",
        metric_key="snr_improvement",
        label="SNR Improvement",
        target=6.0,
        lower_is_better=False,
        format_str=".1f dB",
    ),
    BadgeDefinition(
        suite="synthetic-iqa-noise-full",
        metric_key="psnr",
        label="PSNR",
        target=30.0,
        lower_is_better=False,
        format_str=".1f dB",
    ),
    BadgeDefinition(
        suite="synthetic-iqa-noise-full",
        metric_key="ssim",
        label="SSIM",
        target=0.9,
        lower_is_better=False,
        format_str=".3f",
    ),
    BadgeDefinition(
        suite="synthetic-iqa-binarization-full",
        metric_key="f_measure",
        label="Binarization F1",
        target=0.95,
        lower_is_better=False,
        format_str=".3f",
    ),
    # Layout Detection
    BadgeDefinition(
        suite="doclaynet-layout-full",
        metric_key="mAP",
        label="Layout mAP",
        target=0.80,
        lower_is_better=False,
        format_str=".3f",
    ),
]


def save_badge_file(badges_dir: Path, metric_key: str, badge: dict[str, Any]) -> None:
    badge_file = badges_dir / f"{metric_key.replace('_', '-')}.json"
    with open(badge_file, "w") as f:
        json.dump(badge, f, indent=2)


def create_placeholder_badge(
    badge_def: BadgeDefinition, badges_dir: Path, message: str
) -> BadgeResult:
    badge = create_badge_json(badge_def.label, message, PLACEHOLDER_COLOR)
    save_badge_file(badges_dir, badge_def.metric_key, badge)
    return badge_def.label, message, PLACEHOLDER_COLOR


def metric_value_from_aggregates(metric_data: Any) -> float | None:
    if metric_data is None:
        return None
    if isinstance(metric_data, dict):
        mean_value = metric_data.get("mean")
        return float(mean_value) if mean_value is not None else None
    return float(metric_data)


def format_metric_value(value: float, format_str: str) -> str:
    if "{" in format_str:
        return format_str.format(value)

    match = re.match(r"^([.\d]+[a-z%])", format_str, re.IGNORECASE)
    if match:
        spec = match.group(1)
        suffix = format_str[len(spec) :]
        if "%" in spec:
            formatted_value = value * 100
            spec_without_pct = spec.replace("%", "f")
            return f"{formatted_value:{spec_without_pct}}{suffix}%"
        return f"{value:{spec}}{suffix}"

    return f"{value:{format_str}}"


def create_summary_badge(badges_dir: Path, created_badges: list[BadgeResult]) -> None:
    total_metrics = len(BADGE_DEFINITIONS)
    passed_metrics = sum(1 for _, _, color in created_badges if color == "brightgreen")
    pass_rate = (passed_metrics / total_metrics * 100) if total_metrics > 0 else 0

    if pass_rate >= 80:
        summary_color = "brightgreen"
    elif pass_rate >= 60:
        summary_color = "yellow"
    else:
        summary_color = "red"

    summary_badge = create_badge_json(
        "Benchmarks", f"{passed_metrics}/{total_metrics} passing", summary_color
    )
    save_badge_file(badges_dir, "summary", summary_badge)


def generate_badges(results: dict[str, Any], badges_dir: Path) -> list[BadgeResult]:
    """Generate all badge JSON files.

    Args:
        results: Latest benchmark results
        badges_dir: Directory to save badge JSON files
    """
    badges_dir.mkdir(parents=True, exist_ok=True)

    created_badges = []

    for badge_def in BADGE_DEFINITIONS:
        if badge_def.suite not in results:
            created_badges.append(
                create_placeholder_badge(badge_def, badges_dir, PENDING_MESSAGE)
            )
            continue

        aggregates = results[badge_def.suite]
        if badge_def.metric_key not in aggregates:
            created_badges.append(
                create_placeholder_badge(badge_def, badges_dir, NO_DATA_MESSAGE)
            )
            continue

        # Get metric value
        value = metric_value_from_aggregates(aggregates[badge_def.metric_key])

        if value is None:
            created_badges.append(
                create_placeholder_badge(badge_def, badges_dir, NO_DATA_MESSAGE)
            )
            continue

        message = format_metric_value(value, badge_def.format_str)

        color = get_color_for_metric(value, badge_def.target, badge_def.lower_is_better)

        # Create badge
        badge = create_badge_json(badge_def.label, message, color)
        save_badge_file(badges_dir, badge_def.metric_key, badge)

        created_badges.append((badge_def.label, message, color))

    create_summary_badge(badges_dir, created_badges)
    return created_badges


def create_badge_urls(badges_dir: Path, repo_name: str) -> dict[str, str]:
    """Generate shields.io URLs for badges.

    Args:
        badges_dir: Directory containing badge JSON files
        repo_name: GitHub repository name (owner/repo)

    Returns:
        Dictionary mapping badge names to URLs
    """
    base_url = (
        "https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/"
        f"{repo_name}/main/.github/badges/"
    )

    badge_urls = {}
    for badge_file in badges_dir.glob("*.json"):
        badge_name = badge_file.stem
        badge_urls[badge_name] = f"{base_url}{badge_file.name}"

    return badge_urls


def main() -> int:
    """Main entry point."""
    print("=== Generating Benchmark Badges ===\n")

    # Paths
    reports_dir = project_root / "reports"
    badges_dir = project_root / ".github" / "badges"

    # Load results
    print(f"Loading results from: {reports_dir}")
    results = load_latest_aggregates(reports_dir)

    if not results:
        print("⚠ No results found. Generating placeholder badges.")
    else:
        print(f"✓ Found results for {len(results)} suites")

    # Generate badges
    print(f"\nGenerating badges in: {badges_dir}")
    created = generate_badges(results, badges_dir)

    print(f"\n✓ Generated {len(created)} badges:")
    for label, message, color in created:
        icon_map = {"brightgreen": "✓", "yellow": "⚠"}
        icon = icon_map.get(color, "✗")
        print(f"  {icon} {label}: {message} ({color})")

    # Generate URLs (assuming williaby/image-preprocessing-detector)
    badge_urls = create_badge_urls(badges_dir, "williaby/image-preprocessing-detector")

    print("\n=== Badge URLs ===")
    print("\nAdd these to your README:")
    for name, url in badge_urls.items():
        markdown = f"![{name}]({url})"
        print(f"  {markdown}")

    print("\n✓ Badges generated successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
