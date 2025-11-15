"""Generate dynamic badges for benchmark results.

Creates badge JSON files that can be served via shields.io endpoint or
GitHub Pages for dynamic README badges.

Usage:
    python -m benchmarks.runners.generate_badges

"""

import json
import sys
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
    results = {}

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


def generate_badges(results: dict[str, Any], badges_dir: Path) -> None:
    """Generate all badge JSON files.

    Args:
        results: Latest benchmark results
        badges_dir: Directory to save badge JSON files
    """
    badges_dir.mkdir(parents=True, exist_ok=True)

    # Badge definitions: (suite, metric_key, label, target, lower_is_better, format)
    badge_defs = [
        # IQA Metrics
        (
            "synthetic-iqa-blur-full",
            "blur_correlation",
            "IQA Blur r",
            0.85,
            False,
            ".3f",
        ),
        ("synthetic-iqa-blur-full", "blur_rmse", "IQA Blur RMSE", 0.05, True, ".3f"),
        ("synthetic-iqa-skew-full", "skew_mae", "IQA Skew MAE", 0.5, True, ".2f°"),
        (
            "synthetic-iqa-skew-full",
            "deskew_success_rate",
            "Deskew Success",
            0.99,
            False,
            ".1%",
        ),
        (
            "synthetic-iqa-noise-full",
            "snr_improvement",
            "SNR Improvement",
            6.0,
            False,
            ".1f dB",
        ),
        ("synthetic-iqa-noise-full", "psnr", "PSNR", 30.0, False, ".1f dB"),
        ("synthetic-iqa-noise-full", "ssim", "SSIM", 0.9, False, ".3f"),
        (
            "synthetic-iqa-binarization-full",
            "f_measure",
            "Binarization F1",
            0.95,
            False,
            ".3f",
        ),
        # Layout Detection
        ("doclaynet-layout-full", "mAP", "Layout mAP", 0.80, False, ".3f"),
    ]

    created_badges = []

    for suite, metric_key, label, target, lower_is_better, format_str in badge_defs:
        if suite not in results:
            # Create "pending" badge
            badge = create_badge_json(label, "pending", "lightgrey")
            badge_file = badges_dir / f"{metric_key.replace('_', '-')}.json"
            with open(badge_file, "w") as f:
                json.dump(badge, f, indent=2)
            created_badges.append((label, "pending", "lightgrey"))
            continue

        aggregates = results[suite]
        if metric_key not in aggregates:
            badge = create_badge_json(label, "no data", "lightgrey")
            badge_file = badges_dir / f"{metric_key.replace('_', '-')}.json"
            with open(badge_file, "w") as f:
                json.dump(badge, f, indent=2)
            created_badges.append((label, "no data", "lightgrey"))
            continue

        # Get metric value
        metric_data = aggregates[metric_key]
        if isinstance(metric_data, dict):
            value = metric_data.get("mean")
        else:
            value = metric_data

        if value is None:
            badge = create_badge_json(label, "no data", "lightgrey")
            badge_file = badges_dir / f"{metric_key.replace('_', '-')}.json"
            with open(badge_file, "w") as f:
                json.dump(badge, f, indent=2)
            created_badges.append((label, "no data", "lightgrey"))
            continue

        # Format value
        if "%" in format_str:
            message = format_str.format(value * 100)
        elif "°" in format_str or "dB" in format_str:
            message = format_str.format(value)
        else:
            message = format_str.format(value)

        # Determine color
        color = get_color_for_metric(value, target, lower_is_better)

        # Create badge
        badge = create_badge_json(label, message, color)
        badge_file = badges_dir / f"{metric_key.replace('_', '-')}.json"

        with open(badge_file, "w") as f:
            json.dump(badge, f, indent=2)

        created_badges.append((label, message, color))

    # Create summary badge (overall pass rate)
    total_metrics = len(badge_defs)
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
    with open(badges_dir / "summary.json", "w") as f:
        json.dump(summary_badge, f, indent=2)

    return created_badges


def create_badge_urls(badges_dir: Path, repo_name: str) -> dict[str, str]:
    """Generate shields.io URLs for badges.

    Args:
        badges_dir: Directory containing badge JSON files
        repo_name: GitHub repository name (owner/repo)

    Returns:
        Dictionary mapping badge names to URLs
    """
    base_url = f"https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/{repo_name}/main/.github/badges/"

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
        icon = "✓" if color == "brightgreen" else "⚠" if color == "yellow" else "✗"
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
