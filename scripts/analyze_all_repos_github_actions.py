#!/usr/bin/env python3
"""Analyze GitHub Actions usage across ALL repositories (personal + org).

This script scans all repositories in your personal account and specified organizations
to identify the true cost drivers across your entire GitHub footprint.

Usage:
    export GITHUB_TOKEN=$(gh auth token)
    python scripts/analyze_all_repos_github_actions.py

    # Or specify organizations
    python scripts/analyze_all_repos_github_actions.py --orgs ByronWilliamsCPA AnotherOrg
"""

import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests


@dataclass
class RepoStats:
    """Statistics for a single repository."""

    owner: str
    repo: str
    total_runs: int = 0
    total_duration_minutes: float = 0.0
    total_cost_usd: float = 0.0
    failed_runs: int = 0
    workflow_breakdown: dict[str, float] = field(default_factory=dict)


# GitHub Actions pricing (Linux)
PRICING_LINUX = 0.008  # $0.008 per minute


class MultiRepoAnalyzer:
    """Analyze GitHub Actions usage across multiple repositories."""

    def __init__(self, token: str):
        """Initialize analyzer with GitHub credentials.

        Args:
            token: GitHub personal access token
        """
        self.token = token
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def get_user_repos(self) -> list[dict[str, str]]:
        """Get all repositories accessible to the authenticated user.

        Returns:
            List of {owner, repo} dicts
        """
        url = "https://api.github.com/user/repos"
        params = {"per_page": 100, "affiliation": "owner,collaborator"}

        all_repos = []
        page = 1

        while True:
            params["page"] = page
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            repos = response.json()
            if not repos:
                break

            all_repos.extend(repos)

            if len(repos) < 100:
                break

            page += 1

        return [
            {"owner": repo["owner"]["login"], "repo": repo["name"]}
            for repo in all_repos
        ]

    def get_org_repos(self, org: str) -> list[dict[str, str]]:
        """Get all repositories in an organization.

        Args:
            org: Organization name

        Returns:
            List of {owner, repo} dicts
        """
        url = f"https://api.github.com/orgs/{org}/repos"
        params = {"per_page": 100}

        all_repos = []
        page = 1

        while True:
            params["page"] = page
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            repos = response.json()
            if not repos:
                break

            all_repos.extend(repos)

            if len(repos) < 100:
                break

            page += 1

        return [
            {"owner": org, "repo": repo["name"]}
            for repo in all_repos
        ]

    def fetch_workflow_runs(
        self, owner: str, repo: str, days: int = 30
    ) -> list[dict[str, Any]]:
        """Fetch workflow runs for a specific repository.

        Args:
            owner: Repository owner
            repo: Repository name
            days: Number of days to look back

        Returns:
            List of workflow run objects
        """
        created_after = (datetime.now() - timedelta(days=days)).isoformat()
        url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs"
        params = {
            "created": f">={created_after}",
            "per_page": 100,
            "status": "completed",
        }

        all_runs = []
        page = 1

        while True:
            params["page"] = page
            try:
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
                response.raise_for_status()

                data = response.json()
                runs = data.get("workflow_runs", [])

                if not runs:
                    break

                all_runs.extend(runs)

                if len(runs) < 100:
                    break

                page += 1
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    # Repository doesn't have Actions enabled
                    return []
                raise

        return all_runs

    def analyze_repo(self, owner: str, repo: str, days: int = 30) -> RepoStats:
        """Analyze a single repository.

        Args:
            owner: Repository owner
            repo: Repository name
            days: Number of days to analyze

        Returns:
            Repository statistics
        """
        runs = self.fetch_workflow_runs(owner, repo, days=days)

        if not runs:
            return RepoStats(owner=owner, repo=repo)

        stats = RepoStats(owner=owner, repo=repo)
        stats.total_runs = len(runs)

        workflow_durations: dict[str, float] = defaultdict(float)

        for run in runs:
            # Calculate duration
            created_at = datetime.fromisoformat(
                run["created_at"].replace("Z", "+00:00")
            )
            updated_at = datetime.fromisoformat(
                run["updated_at"].replace("Z", "+00:00")
            )
            duration_minutes = (updated_at - created_at).total_seconds() / 60.0
            stats.total_duration_minutes += duration_minutes
            stats.total_cost_usd += duration_minutes * PRICING_LINUX

            # Track by workflow
            workflow_name = run["name"]
            workflow_durations[workflow_name] += duration_minutes

            # Track failures
            if run.get("conclusion") == "failure":
                stats.failed_runs += 1

        stats.workflow_breakdown = dict(workflow_durations)

        return stats

    def analyze_all(
        self, orgs: list[str] | None = None, days: int = 30
    ) -> dict[str, RepoStats]:
        """Analyze all repositories (user + specified orgs).

        Args:
            orgs: List of organization names to include
            days: Number of days to analyze

        Returns:
            Dictionary of repo_full_name to statistics
        """
        # Get all repositories
        repos = self.get_user_repos()

        if orgs:
            for org in orgs:
                print(f"Fetching repositories for organization: {org}")
                org_repos = self.get_org_repos(org)
                repos.extend(org_repos)

        print(f"\nFound {len(repos)} repositories to analyze")
        print(f"Analyzing workflow runs from the last {days} days...\n")

        # Analyze each repository
        all_stats: dict[str, RepoStats] = {}

        for i, repo_info in enumerate(repos, 1):
            owner = repo_info["owner"]
            repo = repo_info["repo"]
            full_name = f"{owner}/{repo}"

            print(f"[{i}/{len(repos)}] Analyzing {full_name}...", end="")
            sys.stdout.flush()

            try:
                stats = self.analyze_repo(owner, repo, days=days)

                if stats.total_runs > 0:
                    all_stats[full_name] = stats
                    print(f" {stats.total_runs} runs, ${stats.total_cost_usd:.2f}")
                else:
                    print(" (no workflow runs)")
            except Exception as e:
                print(f" ERROR: {e}")
                continue

        return all_stats

    def print_report(self, all_stats: dict[str, RepoStats], days: int = 30) -> None:
        """Print comprehensive multi-repo report.

        Args:
            all_stats: Repository statistics
            days: Number of days analyzed
        """
        # Sort by total cost (descending)
        sorted_stats = sorted(
            all_stats.values(), key=lambda s: s.total_cost_usd, reverse=True
        )

        total_cost = sum(s.total_cost_usd for s in all_stats.values())
        total_runs = sum(s.total_runs for s in all_stats.values())
        total_duration = sum(s.total_duration_minutes for s in all_stats.values())

        print("\n" + "=" * 120)
        print(f"GitHub Actions Multi-Repository Analysis - Last {days} Days")
        print("=" * 120)
        print(f"Total Repositories Analyzed: {len(all_stats)}")
        print(f"Total Workflow Runs: {total_runs}")
        print(f"Total Duration: {total_duration:,.2f} minutes ({total_duration/60:,.2f} hours)")
        print(f"Total Estimated Cost: ${total_cost:,.2f}")
        print("=" * 120)

        print(
            f"\n{'Repository':<50} {'Runs':>8} {'Duration (min)':>15} {'Cost (USD)':>12} {'Failed':>8}"
        )
        print("-" * 120)

        for stat in sorted_stats:
            repo_name = f"{stat.owner}/{stat.repo}"
            print(
                f"{repo_name:<50} {stat.total_runs:>8} {stat.total_duration_minutes:>15,.2f} "
                f"${stat.total_cost_usd:>11,.2f} {stat.failed_runs:>8}"
            )

        print("-" * 120)
        print(
            f"{'TOTAL':<50} {total_runs:>8} {total_duration:>15,.2f} ${total_cost:>11,.2f}"
        )
        print("=" * 120)

        # Top 10 most expensive repositories
        print("\n🔥 TOP 10 MOST EXPENSIVE REPOSITORIES:")
        for i, stat in enumerate(sorted_stats[:10], 1):
            percentage = (stat.total_cost_usd / total_cost * 100) if total_cost > 0 else 0
            print(f"{i:2d}. {stat.owner}/{stat.repo}: ${stat.total_cost_usd:,.2f} ({percentage:.1f}% of total)")

        # Repositories with high failure rates
        print("\n⚠️  REPOSITORIES WITH HIGH FAILURE RATES:")
        high_failure = [
            s for s in sorted_stats
            if s.total_runs >= 5 and (s.failed_runs / s.total_runs) > 0.2
        ]
        if high_failure:
            for stat in high_failure[:10]:
                failure_rate = (stat.failed_runs / stat.total_runs * 100)
                print(f"• {stat.owner}/{stat.repo}: {failure_rate:.1f}% failure rate ({stat.failed_runs}/{stat.total_runs})")
        else:
            print("No repositories with consistently high failure rates")

        # Workflow-level breakdown for top 3 repos
        print("\n📊 WORKFLOW BREAKDOWN - TOP 3 REPOSITORIES:")
        for i, stat in enumerate(sorted_stats[:3], 1):
            print(f"\n{i}. {stat.owner}/{stat.repo} (${stat.total_cost_usd:.2f})")
            sorted_workflows = sorted(
                stat.workflow_breakdown.items(), key=lambda x: x[1], reverse=True
            )
            for workflow_name, duration in sorted_workflows[:5]:
                cost = duration * PRICING_LINUX
                print(f"   • {workflow_name}: {duration:.2f} min (${cost:.2f})")

    def export_json(self, all_stats: dict[str, RepoStats], output_file: str) -> None:
        """Export statistics to JSON file.

        Args:
            all_stats: Repository statistics
            output_file: Output file path
        """
        data = {
            "generated_at": datetime.now().isoformat(),
            "repositories": [
                {
                    "owner": s.owner,
                    "repo": s.repo,
                    "total_runs": s.total_runs,
                    "total_duration_minutes": round(s.total_duration_minutes, 2),
                    "total_cost_usd": round(s.total_cost_usd, 2),
                    "failed_runs": s.failed_runs,
                    "workflow_breakdown": {
                        k: round(v, 2) for k, v in s.workflow_breakdown.items()
                    },
                }
                for s in sorted(
                    all_stats.values(), key=lambda x: x.total_cost_usd, reverse=True
                )
            ],
        }

        with Path(output_file).open("w") as f:
            json.dump(data, f, indent=2)

        print(f"\n✅ Exported detailed statistics to {output_file}")


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze GitHub Actions usage across multiple repositories"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to analyze (default: 30)",
    )
    parser.add_argument(
        "--orgs",
        nargs="+",
        help="Organization names to include (e.g., ByronWilliamsCPA)",
    )
    parser.add_argument(
        "--output",
        default="github_actions_multi_repo_analysis.json",
        help="Output JSON file (default: github_actions_multi_repo_analysis.json)",
    )

    args = parser.parse_args()

    # Get GitHub token
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("❌ Error: GITHUB_TOKEN environment variable not set")
        print("\nUsage:")
        print("  export GITHUB_TOKEN=$(gh auth token)")
        print("  python scripts/analyze_all_repos_github_actions.py")
        print("\nOr specify organizations:")
        print("  python scripts/analyze_all_repos_github_actions.py --orgs ByronWilliamsCPA")
        sys.exit(1)

    # Run analysis
    analyzer = MultiRepoAnalyzer(token=token)
    all_stats = analyzer.analyze_all(orgs=args.orgs, days=args.days)

    if not all_stats:
        print("\n⚠️  No repositories found with workflow runs in the specified period")
        sys.exit(0)

    analyzer.print_report(all_stats, days=args.days)
    analyzer.export_json(all_stats, args.output)

    print("\n💡 NEXT STEPS:")
    print("1. Review top 10 most expensive repositories")
    print("2. Check repositories with high failure rates (wasted compute)")
    print("3. Apply tiered CI strategy to top cost drivers")
    print("4. Consider consolidating workflows across similar projects")


if __name__ == "__main__":
    main()
