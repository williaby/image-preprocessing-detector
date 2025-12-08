#!/usr/bin/env python3
"""Analyze GitHub Actions workflow resource usage and costs.

This script uses the GitHub API to:
1. Fetch workflow run history
2. Calculate total duration and costs per workflow
3. Identify the most expensive workflows
4. Provide optimization recommendations

Usage:
    export GITHUB_TOKEN=your_token_here
    python scripts/analyze_github_actions_usage.py

Or use gh CLI:
    gh auth token | python scripts/analyze_github_actions_usage.py --use-stdin-token
"""

import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests


@dataclass
class WorkflowStats:
    """Statistics for a single workflow."""

    name: str
    total_runs: int = 0
    total_duration_minutes: float = 0.0
    total_cost_usd: float = 0.0
    avg_duration_minutes: float = 0.0
    failed_runs: int = 0
    cancelled_runs: int = 0
    success_runs: int = 0


# GitHub Actions pricing (Linux)
# Source: https://docs.github.com/en/billing/managing-billing-for-github-actions/about-billing-for-github-actions
PRICING_LINUX = {
    "ubuntu-latest": 0.008,  # $0.008 per minute
    "ubuntu-22.04": 0.008,
    "ubuntu-20.04": 0.008,
}

PRICING_WINDOWS = {
    "windows-latest": 0.016,  # $0.016 per minute
    "windows-2022": 0.016,
    "windows-2019": 0.016,
}

PRICING_MACOS = {
    "macos-latest": 0.08,  # $0.08 per minute
    "macos-13": 0.08,
    "macos-12": 0.08,
    "macos-11": 0.08,
}


class GitHubActionsAnalyzer:
    """Analyze GitHub Actions usage and costs."""

    def __init__(self, token: str, owner: str, repo: str):
        """Initialize analyzer with GitHub credentials.

        Args:
            token: GitHub personal access token
            owner: Repository owner (username or org)
            repo: Repository name
        """
        self.token = token
        self.owner = owner
        self.repo = repo
        self.base_url = f"https://api.github.com/repos/{owner}/{repo}"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def fetch_workflow_runs(
        self, days: int = 30, per_page: int = 100
    ) -> list[dict[str, Any]]:
        """Fetch workflow runs from the last N days.

        Args:
            days: Number of days to look back
            per_page: Results per page (max 100)

        Returns:
            List of workflow run objects
        """
        created_after = (datetime.now() - timedelta(days=days)).isoformat()
        url = f"{self.base_url}/actions/runs"
        params = {
            "created": f">={created_after}",
            "per_page": per_page,
            "status": "completed",  # Only completed runs have accurate timing
        }

        all_runs = []
        page = 1

        while True:
            params["page"] = page
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            runs = data.get("workflow_runs", [])

            if not runs:
                break

            all_runs.extend(runs)

            # Check if there are more pages
            if len(runs) < per_page:
                break

            page += 1

        return all_runs

    def fetch_workflow_usage(self, workflow_id: int) -> dict[str, Any]:
        """Fetch detailed usage for a specific workflow.

        Args:
            workflow_id: Workflow ID

        Returns:
            Usage statistics including billable time
        """
        url = f"{self.base_url}/actions/workflows/{workflow_id}/timing"
        response = requests.get(url, headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json()

    def calculate_run_cost(self, run: dict[str, Any]) -> float:
        """Calculate cost for a single workflow run.

        Args:
            run: Workflow run object

        Returns:
            Estimated cost in USD
        """
        # Duration in minutes
        created_at = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
        updated_at = datetime.fromisoformat(run["updated_at"].replace("Z", "+00:00"))
        duration_minutes = (updated_at - created_at).total_seconds() / 60.0

        # Determine runner type from run metadata
        # Note: This is an approximation - actual runner type requires job-level API call
        runner_os = run.get("runner_name", "ubuntu-latest")

        # Default to Linux pricing (most common)
        rate = PRICING_LINUX.get("ubuntu-latest", 0.008)

        # Adjust if we can detect Windows/macOS
        if "windows" in runner_os.lower():
            rate = PRICING_WINDOWS.get("windows-latest", 0.016)
        elif "macos" in runner_os.lower():
            rate = PRICING_MACOS.get("macos-latest", 0.08)

        return duration_minutes * rate

    def analyze_workflows(self, days: int = 30) -> dict[str, WorkflowStats]:
        """Analyze all workflows and calculate statistics.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary of workflow name to statistics
        """
        print(f"Fetching workflow runs from the last {days} days...")
        runs = self.fetch_workflow_runs(days=days)
        print(f"Found {len(runs)} completed workflow runs")

        stats: dict[str, WorkflowStats] = defaultdict(
            lambda: WorkflowStats(name="Unknown")
        )

        for run in runs:
            workflow_name = run["name"]
            if workflow_name not in stats:
                stats[workflow_name] = WorkflowStats(name=workflow_name)

            stat = stats[workflow_name]
            stat.total_runs += 1

            # Calculate duration
            created_at = datetime.fromisoformat(
                run["created_at"].replace("Z", "+00:00")
            )
            updated_at = datetime.fromisoformat(
                run["updated_at"].replace("Z", "+00:00")
            )
            duration_minutes = (updated_at - created_at).total_seconds() / 60.0
            stat.total_duration_minutes += duration_minutes

            # Calculate cost (approximation)
            stat.total_cost_usd += self.calculate_run_cost(run)

            # Track status
            conclusion = run.get("conclusion", "unknown")
            if conclusion == "success":
                stat.success_runs += 1
            elif conclusion == "failure":
                stat.failed_runs += 1
            elif conclusion == "cancelled":
                stat.cancelled_runs += 1

        # Calculate averages
        for stat in stats.values():
            if stat.total_runs > 0:
                stat.avg_duration_minutes = stat.total_duration_minutes / stat.total_runs

        return dict(stats)

    def print_report(self, stats: dict[str, WorkflowStats], days: int = 30) -> None:
        """Print formatted report of workflow statistics.

        Args:
            stats: Workflow statistics
            days: Number of days analyzed
        """
        # Sort by total cost (descending)
        sorted_stats = sorted(
            stats.values(), key=lambda s: s.total_cost_usd, reverse=True
        )

        total_cost = sum(s.total_cost_usd for s in stats.values())
        total_runs = sum(s.total_runs for s in stats.values())
        total_duration = sum(s.total_duration_minutes for s in stats.values())

        print("\n" + "=" * 100)
        print(f"GitHub Actions Usage Report - Last {days} Days")
        print("=" * 100)
        print(f"Repository: {self.owner}/{self.repo}")
        print(f"Total Workflows: {len(stats)}")
        print(f"Total Runs: {total_runs}")
        print(f"Total Duration: {total_duration:,.2f} minutes ({total_duration/60:,.2f} hours)")
        print(f"Total Estimated Cost: ${total_cost:,.2f}")
        print("=" * 100)

        print(
            f"\n{'Workflow Name':<40} {'Runs':>8} {'Duration (min)':>15} {'Avg (min)':>12} {'Cost (USD)':>12} {'Failed':>8}"
        )
        print("-" * 100)

        for stat in sorted_stats:
            print(
                f"{stat.name:<40} {stat.total_runs:>8} {stat.total_duration_minutes:>15,.2f} "
                f"{stat.avg_duration_minutes:>12,.2f} ${stat.total_cost_usd:>11,.2f} {stat.failed_runs:>8}"
            )

        print("-" * 100)
        print(
            f"{'TOTAL':<40} {total_runs:>8} {total_duration:>15,.2f} "
            f"{total_duration/total_runs if total_runs > 0 else 0:>12,.2f} ${total_cost:>11,.2f}"
        )
        print("=" * 100)

        # Top 5 most expensive workflows
        print("\n🔥 TOP 5 MOST EXPENSIVE WORKFLOWS:")
        for i, stat in enumerate(sorted_stats[:5], 1):
            percentage = (stat.total_cost_usd / total_cost * 100) if total_cost > 0 else 0
            print(f"{i}. {stat.name}: ${stat.total_cost_usd:,.2f} ({percentage:.1f}% of total)")

        # Workflows with high failure rates
        print("\n⚠️  WORKFLOWS WITH HIGH FAILURE RATES:")
        high_failure = [
            s for s in sorted_stats
            if s.total_runs >= 5 and (s.failed_runs / s.total_runs) > 0.2
        ]
        if high_failure:
            for stat in high_failure[:5]:
                failure_rate = (stat.failed_runs / stat.total_runs * 100)
                print(f"• {stat.name}: {failure_rate:.1f}% failure rate ({stat.failed_runs}/{stat.total_runs})")
        else:
            print("No workflows with consistently high failure rates")

    def export_json(self, stats: dict[str, WorkflowStats], output_file: str) -> None:
        """Export statistics to JSON file.

        Args:
            stats: Workflow statistics
            output_file: Output file path
        """
        data = {
            "repository": f"{self.owner}/{self.repo}",
            "generated_at": datetime.now().isoformat(),
            "workflows": [
                {
                    "name": s.name,
                    "total_runs": s.total_runs,
                    "total_duration_minutes": round(s.total_duration_minutes, 2),
                    "avg_duration_minutes": round(s.avg_duration_minutes, 2),
                    "total_cost_usd": round(s.total_cost_usd, 2),
                    "success_runs": s.success_runs,
                    "failed_runs": s.failed_runs,
                    "cancelled_runs": s.cancelled_runs,
                }
                for s in sorted(
                    stats.values(), key=lambda x: x.total_cost_usd, reverse=True
                )
            ],
        }

        with Path(output_file).open("w") as f:
            json.dump(data, f, indent=2)

        print(f"\n✅ Exported detailed statistics to {output_file}")


def main() -> None:
    """Main entry point."""
    # Get GitHub token
    token = os.environ.get("GITHUB_TOKEN")
    if not token and "--use-stdin-token" in sys.argv:
        token = sys.stdin.read().strip()

    if not token:
        print("❌ Error: GITHUB_TOKEN environment variable not set")
        print("\nUsage:")
        print("  export GITHUB_TOKEN=your_token_here")
        print("  python scripts/analyze_github_actions_usage.py")
        print("\nOr use gh CLI:")
        print("  gh auth token | python scripts/analyze_github_actions_usage.py --use-stdin-token")
        sys.exit(1)

    # Get repository info from git remote
    try:
        import subprocess
        remote_url = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"],
            text=True,
        ).strip()

        # Parse owner/repo from URL
        # Supports both HTTPS and SSH URLs
        if "github.com" in remote_url:
            parts = remote_url.replace(".git", "").split("/")
            owner = parts[-2].split(":")[-1]  # Handle SSH URLs
            repo = parts[-1]
        else:
            raise ValueError("Not a GitHub repository")

    except Exception as e:
        print(f"❌ Error: Could not determine repository from git remote: {e}")
        print("\nMake sure you're in a git repository with a GitHub remote")
        sys.exit(1)

    # Parse arguments
    days = 30
    if "--days" in sys.argv:
        try:
            days_idx = sys.argv.index("--days")
            days = int(sys.argv[days_idx + 1])
        except (ValueError, IndexError):
            print("❌ Error: Invalid --days argument")
            sys.exit(1)

    # Run analysis
    analyzer = GitHubActionsAnalyzer(token=token, owner=owner, repo=repo)
    stats = analyzer.analyze_workflows(days=days)
    analyzer.print_report(stats, days=days)

    # Export to JSON
    output_file = "github_actions_usage.json"
    analyzer.export_json(stats, output_file)

    print("\n💡 OPTIMIZATION TIPS:")
    print("1. Cache dependencies to reduce setup time")
    print("2. Use matrix builds selectively (avoid testing on all OS/Python versions)")
    print("3. Skip CI jobs for documentation-only changes")
    print("4. Use workflow path filters to run only relevant jobs")
    print("5. Consider using self-hosted runners for frequent builds")
    print("6. Reduce redundant security scans (consolidate into fewer workflows)")


if __name__ == "__main__":
    main()
