"""Smoke test runner for fast CI validation.

Runs benchmark subsets for quick feedback in CI pipelines.

Usage:
    python -m benchmarks.runners.run_smoke --suite doclaynet-layout-smoke
    python -m benchmarks.runners.run_smoke --all

SPDX-License-Identifier: Apache-2.0
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from benchmarks.runners.run_benchmark import load_registry, run_benchmark


def get_smoke_suites(registry_path: Path) -> list[str]:
    """Get list of all smoke test suites.

    Args:
        registry_path: Path to registry.yml

    Returns:
        List of smoke suite names
    """
    registry = load_registry(registry_path)
    smoke_suites = []

    for suite in registry["suites"]:
        # Smoke suites either have "smoke" in name or have smoke_subset defined
        if "smoke" in suite["name"] or suite.get("smoke_subset") is not None:
            smoke_suites.append(suite["name"])

    return smoke_suites


def run_smoke_tests(
    suite_names: list[str],
    registry_path: Path,
) -> bool:
    """Run multiple smoke test suites.

    Args:
        suite_names: List of suite names to run
        registry_path: Path to registry.yml

    Returns:
        True if all tests passed
    """
    results = {}
    failed_suites = []

    print(f"=== Running {len(suite_names)} Smoke Tests ===\n")

    for i, suite_name in enumerate(suite_names, 1):
        print(f"[{i}/{len(suite_names)}] Running: {suite_name}")
        print("=" * 60)

        try:
            result = run_benchmark(suite_name, registry_path=registry_path)

            if "error" in result:
                print(f"✗ FAILED: {result['error']}\n")
                failed_suites.append(suite_name)
                results[suite_name] = "FAILED"
            else:
                print("✓ PASSED\n")
                results[suite_name] = "PASSED"

        except Exception as e:
            print(f"✗ FAILED with exception: {e}\n")
            failed_suites.append(suite_name)
            results[suite_name] = "FAILED"

    # Print summary
    print("\n" + "=" * 60)
    print("=== Smoke Test Summary ===")
    print("=" * 60)

    for suite_name, status in results.items():
        icon = "✓" if status == "PASSED" else "✗"
        print(f"{icon} {suite_name}: {status}")

    print("=" * 60)
    passed_count = sum(1 for s in results.values() if s == "PASSED")
    total_count = len(results)
    print(f"Results: {passed_count}/{total_count} passed")

    if failed_suites:
        print(f"\nFailed suites: {', '.join(failed_suites)}")
        return False
    print("\n✓ All smoke tests passed!")
    return True


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run smoke tests for quick validation")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--suite",
        help="Name of a specific smoke test suite to run",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Run all smoke test suites",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=project_root / "benchmarks" / "registry.yml",
        help="Path to registry.yml (default: benchmarks/registry.yml)",
    )

    args = parser.parse_args()

    if args.all:
        # Run all smoke suites
        smoke_suites = get_smoke_suites(args.registry)

        if not smoke_suites:
            print("✗ No smoke test suites found in registry")
            return 1

        print(f"Found {len(smoke_suites)} smoke test suites:")
        for suite in smoke_suites:
            print(f"  - {suite}")
        print()

        success = run_smoke_tests(smoke_suites, args.registry)
        return 0 if success else 1

    # Run single suite
    try:
        result = run_benchmark(args.suite, registry_path=args.registry)

        if "error" in result:
            print(f"\n✗ Smoke test failed: {result['error']}")
            return 1

        print("\n✓ Smoke test passed")
        return 0

    except Exception as e:
        print(f"\n✗ Smoke test failed with exception: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
