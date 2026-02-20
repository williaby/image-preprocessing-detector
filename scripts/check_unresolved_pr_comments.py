#!/usr/bin/env python3
"""Check for unresolved PR review comments across merged PRs.

Queries the GitHub GraphQL API for unresolved review threads on merged pull requests,
filters out automated security scanner noise (Semgrep, Snyk, CodeQL code-scanning),
and outputs a categorized summary.

Usage:
    # Summary only (default)
    python scripts/check_unresolved_pr_comments.py

    # Full tracking file regeneration
    python scripts/check_unresolved_pr_comments.py --output docs/planning/UNRESOLVED_PR_COMMENTS_TRACKING.md

    # Show only security and error-handling topics
    python scripts/check_unresolved_pr_comments.py --topics security error-handling

    # Show only current (non-outdated) items
    python scripts/check_unresolved_pr_comments.py --current-only

    # JSON output for further processing
    python scripts/check_unresolved_pr_comments.py --json

Requirements:
    - gh CLI installed and authenticated
    - jq (optional, for JSON pretty-printing)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


# Automated scanner authors whose threads are pure noise
_SCANNER_AUTHORS = frozenset({
    "github-advanced-security",
    "semgrep-code-williaby",
    "snyk-bot",
    "dependabot",
    "github-actions",
    "codecov",
    "sonarcloud",
})

# Body patterns that indicate scanner-generated comments
_SCANNER_PATTERNS = ("code-scanning/", "semgrep", "snyk")

_GRAPHQL_PR_LIST = """
{
  repository(owner: "%s", name: "%s") {
    pullRequests(states: MERGED, first: 100, orderBy: {field: CREATED_AT, direction: DESC}) {
      nodes {
        number
      }
    }
  }
}
"""

_GRAPHQL_PR_THREADS = """
{
  repository(owner: "%s", name: "%s") {
    pullRequest(number: %d) {
      number
      title
      mergedAt
      url
      reviewThreads(first: 100) {
        nodes {
          isResolved
          isOutdated
          id
          comments(first: 10) {
            nodes {
              body
              author {
                login
              }
              createdAt
              path
              line
            }
          }
        }
      }
    }
  }
}
"""


def _classify_severity(body: str) -> str:
    """Classify comment severity from reviewer markup."""
    bl = body.lower()
    if "\U0001f534 critical" in bl or ("critical" in bl and "security" in bl):
        return "critical"
    if "potential issue" in bl or "\U0001f7e0 medium" in bl:
        return "medium"
    if any(p in bl for p in ("nitpick", "\U0001f535 trivial", "\U0001f7e1 minor")):
        return "low"
    if "suggestion" in bl:
        return "low"
    return "unclassified"


def _classify_topic(body: str) -> str:
    """Classify comment topic from content keywords."""
    bl = body.lower()
    topic_keywords: dict[str, list[str]] = {
        "security": ["security", "vulnerab", "injection", "xss", "csrf", "secret", "credential", "auth"],
        "error-handling": ["error handling", "exception", "try/except", "raise", "error boundary"],
        "data-consistency": ["inconsisten", "mismatch", "denominator", "count"],
        "performance": ["performance", "cache", "optimize", "slow", "memory"],
        "typing": ["type hint", "type annotation", "typing", "mypy", "pyright", "type:"],
        "testing": ["test", "coverage", "assert", "mock"],
        "dead-code": ["duplicate", "redundant", "unused", "dead code"],
        "magic-numbers": ["magic number", "hardcod", "constant"],
        "documentation": ["docstring", "documentation", "comment", "readme", "frontmatter", "h1", "heading"],
    }
    for topic, keywords in topic_keywords.items():
        if any(kw in bl for kw in keywords):
            return topic
    return "other"


def _run_graphql_query(query: str) -> dict:
    """Execute a single GraphQL query via gh CLI."""
    result = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"Error querying GitHub API: {result.stderr}", file=sys.stderr)
        return {}
    return json.loads(result.stdout)


def _run_graphql(owner: str, repo: str) -> dict:
    """Fetch all merged PRs and their review threads in batches to avoid timeouts."""
    # Step 1: get PR numbers
    pr_list_data = _run_graphql_query(_GRAPHQL_PR_LIST % (owner, repo))
    if not pr_list_data:
        print("Failed to fetch PR list", file=sys.stderr)
        sys.exit(1)

    pr_numbers = [
        pr["number"]
        for pr in pr_list_data["data"]["repository"]["pullRequests"]["nodes"]
    ]
    print(f"Found {len(pr_numbers)} merged PRs, fetching review threads...", file=sys.stderr)

    # Step 2: fetch each PR's threads individually
    all_pr_nodes = []
    for i, pr_num in enumerate(pr_numbers, 1):
        query = _GRAPHQL_PR_THREADS % (owner, repo, pr_num)
        result = _run_graphql_query(query)
        if result and "data" in result:
            pr_data = result["data"]["repository"]["pullRequest"]
            if pr_data:
                all_pr_nodes.append(pr_data)
        if i % 20 == 0:
            print(f"  ... fetched {i}/{len(pr_numbers)} PRs", file=sys.stderr)

    print(f"  ... fetched {len(pr_numbers)}/{len(pr_numbers)} PRs", file=sys.stderr)

    return {"data": {"repository": {"pullRequests": {"nodes": all_pr_nodes}}}}


def _extract_items(data: dict, *, current_only: bool = False) -> list[dict]:
    """Extract and classify unresolved review threads."""
    prs = data["data"]["repository"]["pullRequests"]["nodes"]
    items = []

    for pr in prs:
        for thread in pr["reviewThreads"]["nodes"]:
            if thread["isResolved"]:
                continue
            is_outdated = thread.get("isOutdated", False)
            if current_only and is_outdated:
                continue

            comments = thread["comments"]["nodes"]
            if not comments:
                continue

            first = comments[0]
            author_obj = first.get("author")
            author = author_obj.get("login", "unknown") if author_obj else "unknown"

            if author.lower() in _SCANNER_AUTHORS:
                continue

            body = first.get("body", "")
            if any(p in body.lower() for p in _SCANNER_PATTERNS):
                continue

            replies = []
            for comment in comments[1:]:
                r_author_obj = comment.get("author")
                r_author = r_author_obj.get("login", "unknown") if r_author_obj else "unknown"
                replies.append({
                    "author": r_author,
                    "date": comment.get("createdAt", "")[:10],
                    "body": comment.get("body", ""),
                })

            items.append({
                "pr": pr["number"],
                "pr_title": pr["title"],
                "pr_url": pr["url"],
                "thread_id": thread.get("id", ""),
                "author": author,
                "date": first.get("createdAt", "")[:10],
                "path": first.get("path", ""),
                "line": first.get("line"),
                "severity": _classify_severity(body),
                "topic": _classify_topic(body),
                "outdated": is_outdated,
                "body": body,
                "replies": replies,
            })

    # Sort: security first, then severity, then PR desc
    severity_order = {"critical": 0, "medium": 1, "unclassified": 2, "low": 3}
    topic_order_map = {
        "security": 0, "error-handling": 1, "data-consistency": 2, "performance": 3,
        "typing": 4, "testing": 5, "dead-code": 6, "magic-numbers": 7,
        "documentation": 8, "other": 9,
    }
    items.sort(key=lambda x: (
        topic_order_map.get(x["topic"], 99),
        severity_order.get(x["severity"], 99),
        -x["pr"],
    ))
    return items


def _print_summary(items: list[dict]) -> None:
    """Print a concise summary to stdout."""
    current = [i for i in items if not i["outdated"]]
    outdated = [i for i in items if i["outdated"]]

    print("=" * 60)
    print("UNRESOLVED PR REVIEW COMMENTS")
    print("=" * 60)
    print(f"Total:    {len(items)}")
    print(f"Current:  {len(current)}")
    print(f"Outdated: {len(outdated)}")
    print()

    print("By reviewer:")
    for author, count in Counter(i["author"] for i in items).most_common():
        print(f"  @{author}: {count}")
    print()

    print("By severity (current only):")
    for sev, count in Counter(i["severity"] for i in current).most_common():
        print(f"  {sev}: {count}")
    print()

    priority_map = {
        "security": "HIGH", "error-handling": "MEDIUM", "data-consistency": "MEDIUM",
        "performance": "MEDIUM", "typing": "LOW", "testing": "LOW",
        "dead-code": "LOW", "magic-numbers": "LOW", "documentation": "LOW", "other": "LOW",
    }
    print("By topic (current only):")
    for topic, count in Counter(i["topic"] for i in current).most_common():
        priority = priority_map.get(topic, "LOW")
        print(f"  [{priority:6s}] {topic}: {count}")
    print()

    print("By PR (top 10):")
    for pr_num, count in Counter(i["pr"] for i in current).most_common(10):
        title = next((i["pr_title"] for i in items if i["pr"] == pr_num), "")
        print(f"  PR #{pr_num} ({count}): {title[:60]}")


def _generate_tracking_md(items: list[dict]) -> str:
    """Generate a full markdown tracking file."""
    topic_counts = Counter(i["topic"] for i in items)
    sev_counts = Counter(i["severity"] for i in items)

    lines = [
        "# Unresolved PR Review Comments - Tracking",
        "",
        f"> **Generated**: {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "> **Repository**: williaby/image-preprocessing-detector",
        "> **Scope**: All merged PRs, current (non-outdated) unresolved threads",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|--------|-------|",
        f"| Total | {len(items)} |",
    ]
    for sev in ("critical", "medium", "unclassified", "low"):
        if sev_counts.get(sev, 0) > 0:
            lines.append(f"| Severity: {sev} | {sev_counts[sev]} |")

    priority_map = {
        "security": "HIGH", "error-handling": "MEDIUM", "data-consistency": "MEDIUM",
        "performance": "MEDIUM", "typing": "LOW", "testing": "LOW",
        "dead-code": "LOW", "magic-numbers": "LOW", "documentation": "LOW", "other": "LOW",
    }
    lines.extend([
        "",
        "| Topic | Count | Priority |",
        "|-------|-------|----------|",
    ])
    topic_order = [
        "security", "error-handling", "data-consistency", "performance",
        "typing", "testing", "dead-code", "magic-numbers", "documentation", "other",
    ]
    for topic in topic_order:
        if topic_counts.get(topic, 0) > 0:
            lines.append(f"| {topic} | {topic_counts[topic]} | {priority_map.get(topic, 'LOW')} |")

    lines.extend([
        "",
        "## Triage Legend",
        "",
        "- `[ ]` - Not reviewed",
        "- `[x]` - Addressed",
        "- `[~]` - Won't fix",
        "- `[!]` - Needs investigation",
        "",
    ])

    current_topic = None
    item_id = 0
    for item in items:
        if item["topic"] != current_topic:
            current_topic = item["topic"]
            lines.append(f"## {current_topic.replace('-', ' ').title()} ({topic_counts[current_topic]})")
            lines.append("")

        item_id += 1
        line_str = str(item["line"]) if item["line"] else "N/A"
        outdated_tag = " [OUTDATED]" if item["outdated"] else ""
        lines.extend([
            f"### {item_id}. PR #{item['pr']} - {item['path']}{outdated_tag}",
            "",
            "- **Status**: [ ]",
            f"- **Severity**: {item['severity']}",
            f"- **PR**: [#{item['pr']} - {item['pr_title']}]({item['pr_url']})",
            f"- **Reviewer**: @{item['author']}",
            f"- **Date**: {item['date']}",
            f"- **File**: `{item['path']}`",
            f"- **Line**: {line_str}",
            "",
            "<details>",
            "<summary>Comment</summary>",
            "",
            item["body"].strip(),
            "",
        ])
        if item["replies"]:
            lines.append("**Replies:**")
            lines.append("")
            for reply in item["replies"]:
                lines.append(f"> **@{reply['author']}** ({reply['date']}):")
                reply_clean = reply["body"].strip().replace("\n", "\n> ")
                lines.extend([f"> {reply_clean}", ""])
        lines.extend(["</details>", ""])

    return "\n".join(lines)


def main() -> None:
    """Run the unresolved PR comments checker."""
    parser = argparse.ArgumentParser(
        description="Check for unresolved PR review comments across merged PRs.",
    )
    parser.add_argument(
        "--repo",
        default="williaby/image-preprocessing-detector",
        help="GitHub repo in owner/name format (default: %(default)s)",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Write full tracking markdown file to this path",
    )
    parser.add_argument(
        "--topics",
        nargs="+",
        help="Filter to specific topics (e.g., security error-handling)",
    )
    parser.add_argument(
        "--current-only",
        action="store_true",
        help="Exclude outdated threads (code has changed under them)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output raw JSON for further processing",
    )
    args = parser.parse_args()

    owner, repo = args.repo.split("/")
    print(f"Querying {owner}/{repo} for unresolved review threads...", file=sys.stderr)

    data = _run_graphql(owner, repo)
    items = _extract_items(data, current_only=args.current_only)

    if args.topics:
        items = [i for i in items if i["topic"] in args.topics]

    if args.json_output:
        # Strip large body fields for JSON summary if desired
        print(json.dumps(items, indent=2))
        return

    if args.output:
        content = _generate_tracking_md(items)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content)
        print(f"Tracking file written to {args.output} ({len(items)} items)", file=sys.stderr)
    else:
        _print_summary(items)


if __name__ == "__main__":
    main()
