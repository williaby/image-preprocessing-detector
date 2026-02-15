#!/usr/bin/env python3
"""Fetch all SonarCloud issues for the project and save to a local report.

Usage:
    python scripts/fetch_sonarcloud_issues.py [--output results/sonarcloud_issues.json]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import requests
from collections import Counter
from datetime import datetime, UTC
from pathlib import Path

PROJECT_KEY = "williaby_image-preprocessing-detector"
API_BASE = "https://sonarcloud.io/api"
PAGE_SIZE = 500  # max allowed by SonarCloud API
MAX_PAGES = 50  # safety limit (500*50 = 25,000 issues max)


def fetch_issues_page(page: int, page_size: int = PAGE_SIZE) -> dict:
    """Fetch a single page of issues from SonarCloud API."""
    url = (
        f"{API_BASE}/issues/search"
        f"?componentKeys={PROJECT_KEY}"
        f"&ps={page_size}"
        f"&p={page}"
        f"&statuses=OPEN,CONFIRMED,REOPENED"
        f"&additionalFields=_all"
    )
    headers = {"Accept": "application/json"}

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_all_issues() -> tuple[list[dict], dict]:
    """Fetch all issues with pagination. Returns (issues, metadata)."""
    all_issues: list[dict] = []
    page = 1

    # First request to get total count
    data = fetch_issues_page(page)
    total = data["paging"]["total"]
    all_issues.extend(data["issues"])
    print(f"Total issues: {total}")
    print(f"Page 1: fetched {len(data['issues'])} issues")

    # Calculate pages needed
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    total_pages = min(total_pages, MAX_PAGES)

    # SonarCloud API limits to 10,000 results via pagination
    if total > 10000:
        print(
            f"WARNING: SonarCloud API limits pagination to 10,000 results. {total} total issues exist."
        )
        total_pages = min(total_pages, 10000 // PAGE_SIZE)

    # Fetch remaining pages
    for page in range(2, total_pages + 1):
        time.sleep(0.3)  # rate limit courtesy
        data = fetch_issues_page(page)
        fetched = len(data["issues"])
        all_issues.extend(data["issues"])
        print(
            f"Page {page}/{total_pages}: fetched {fetched} issues (total: {len(all_issues)})"
        )

        if fetched == 0:
            break

    metadata = {
        "project_key": PROJECT_KEY,
        "total_reported": total,
        "total_fetched": len(all_issues),
        "fetched_at": datetime.now(tz=UTC).isoformat(),
        "effort_total_minutes": data.get("effortTotal", 0),
    }

    return all_issues, metadata


def build_summary(issues: list[dict]) -> dict:
    """Build summary statistics from issues."""
    severity_counts = Counter(i.get("severity", "UNKNOWN") for i in issues)
    type_counts = Counter(i.get("type", "UNKNOWN") for i in issues)
    rule_counts = Counter(i.get("rule", "UNKNOWN") for i in issues)
    status_counts = Counter(i.get("status", "UNKNOWN") for i in issues)

    # Group by file
    file_counts: Counter[str] = Counter()
    for issue in issues:
        component = issue.get("component", "")
        # Strip project key prefix
        file_path = component.replace(f"{PROJECT_KEY}:", "")
        file_counts[file_path] += 1

    # Group by directory (top 2 levels)
    dir_counts: Counter[str] = Counter()
    for file_path, count in file_counts.items():
        parts = file_path.split("/")
        if len(parts) >= 2:
            dir_key = "/".join(parts[:2])
        else:
            dir_key = parts[0] if parts else "root"
        dir_counts[dir_key] += count

    # Effort by severity
    effort_by_severity: Counter[str] = Counter()
    for issue in issues:
        effort_str = issue.get("effort", "0min")
        minutes = _parse_effort(effort_str)
        effort_by_severity[issue.get("severity", "UNKNOWN")] += minutes

    return {
        "by_severity": dict(severity_counts.most_common()),
        "by_type": dict(type_counts.most_common()),
        "by_rule": dict(rule_counts.most_common(30)),
        "by_status": dict(status_counts.most_common()),
        "by_file": dict(file_counts.most_common(50)),
        "by_directory": dict(dir_counts.most_common(20)),
        "effort_minutes_by_severity": dict(effort_by_severity.most_common()),
        "total_rules_triggered": len(rule_counts),
        "total_files_affected": len(file_counts),
    }


def _parse_effort(effort: str) -> int:
    """Parse SonarCloud effort string like '5min', '1h', '2h30min' to minutes."""
    if not effort:
        return 0
    minutes = 0
    effort = effort.strip()
    if "h" in effort:
        parts = effort.split("h")
        minutes += int(parts[0].strip()) * 60
        remainder = parts[1].strip() if len(parts) > 1 else ""
        if remainder and "min" in remainder:
            minutes += int(remainder.replace("min", "").strip())
    elif "min" in effort:
        minutes += int(effort.replace("min", "").strip())
    elif "d" in effort:
        parts = effort.split("d")
        minutes += int(parts[0].strip()) * 480  # 8h workday
    return minutes


def format_issue_for_report(issue: dict) -> dict:
    """Extract the most useful fields from a raw issue."""
    component = issue.get("component", "")
    file_path = component.replace(f"{PROJECT_KEY}:", "")

    return {
        "key": issue.get("key", ""),
        "rule": issue.get("rule", ""),
        "severity": issue.get("severity", ""),
        "type": issue.get("type", ""),
        "file": file_path,
        "line": issue.get("line"),
        "message": issue.get("message", ""),
        "effort": issue.get("effort", ""),
        "status": issue.get("status", ""),
        "tags": issue.get("tags", []),
        "creation_date": issue.get("creationDate", ""),
        "update_date": issue.get("updateDate", ""),
        "text_range": issue.get("textRange"),
    }


def write_markdown_report(
    issues: list[dict], summary: dict, metadata: dict, output_path: Path
) -> None:
    """Write a human-readable markdown report."""
    md_path = output_path.with_suffix(".md")
    lines: list[str] = []

    lines.append("# SonarCloud Issues Report")
    lines.append("")
    lines.append(f"**Project**: `{metadata['project_key']}`")
    lines.append(f"**Fetched**: {metadata['fetched_at']}")
    lines.append(
        f"**Total Issues**: {metadata['total_fetched']} (of {metadata['total_reported']} reported)"
    )
    lines.append(
        f"**Total Effort**: {metadata['effort_total_minutes']} minutes ({metadata['effort_total_minutes'] / 60:.1f} hours)"
    )
    lines.append("")

    # Severity breakdown
    lines.append("## Issues by Severity")
    lines.append("")
    lines.append("| Severity | Count | Effort (min) |")
    lines.append("|----------|-------|-------------|")
    severity_order = ["BLOCKER", "CRITICAL", "MAJOR", "MINOR", "INFO"]
    for sev in severity_order:
        count = summary["by_severity"].get(sev, 0)
        effort = summary["effort_minutes_by_severity"].get(sev, 0)
        if count > 0:
            lines.append(f"| {sev} | {count} | {effort} |")
    lines.append("")

    # Type breakdown
    lines.append("## Issues by Type")
    lines.append("")
    lines.append("| Type | Count |")
    lines.append("|------|-------|")
    for type_name, count in summary["by_type"].items():
        lines.append(f"| {type_name} | {count} |")
    lines.append("")

    # Top rules
    lines.append("## Top 30 Rules Triggered")
    lines.append("")
    lines.append("| Rule | Count | Description (from first occurrence) |")
    lines.append("|------|-------|-------------------------------------|")
    rule_messages: dict[str, str] = {}
    for issue in issues:
        rule = issue.get("rule", "")
        if rule not in rule_messages:
            rule_messages[rule] = issue.get("message", "")[:80]
    for rule, count in summary["by_rule"].items():
        msg = rule_messages.get(rule, "")
        lines.append(f"| `{rule}` | {count} | {msg} |")
    lines.append("")

    # Top directories
    lines.append("## Issues by Directory")
    lines.append("")
    lines.append("| Directory | Count |")
    lines.append("|-----------|-------|")
    for dir_name, count in summary["by_directory"].items():
        lines.append(f"| `{dir_name}` | {count} |")
    lines.append("")

    # Top files
    lines.append("## Top 50 Files by Issue Count")
    lines.append("")
    lines.append("| File | Count |")
    lines.append("|------|-------|")
    for file_name, count in summary["by_file"].items():
        lines.append(f"| `{file_name}` | {count} |")
    lines.append("")

    # Detailed issue list grouped by file
    lines.append("## All Issues (Grouped by File)")
    lines.append("")

    # Group issues by file
    issues_by_file: dict[str, list[dict]] = {}
    for issue in issues:
        formatted = format_issue_for_report(issue)
        file_key = formatted["file"]
        if file_key not in issues_by_file:
            issues_by_file[file_key] = []
        issues_by_file[file_key].append(formatted)

    # Sort files by issue count descending
    sorted_files = sorted(issues_by_file.items(), key=lambda x: len(x[1]), reverse=True)

    for file_path, file_issues in sorted_files:
        lines.append(f"### `{file_path}` ({len(file_issues)} issues)")
        lines.append("")
        lines.append("| Line | Severity | Rule | Message | Effort |")
        lines.append("|------|----------|------|---------|--------|")
        # Sort by line number
        file_issues.sort(key=lambda x: x.get("line") or 0)
        for fi in file_issues:
            line_num = fi["line"] if fi["line"] else "-"
            msg = fi["message"].replace("|", "\\|")[:100]
            lines.append(
                f"| {line_num} | {fi['severity']} | `{fi['rule']}` | {msg} | {fi['effort']} |"
            )
        lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Markdown report written to: {md_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch SonarCloud issues")
    parser.add_argument(
        "--output",
        default="results/sonarcloud_issues.json",
        help="Output JSON file path (markdown report auto-generated alongside)",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Fetching issues for project: {PROJECT_KEY}")
    print("=" * 60)

    try:
        issues, metadata = fetch_all_issues()
    except requests.exceptions.HTTPError as exc:
        response = exc.response
        print(f"ERROR: HTTP {response.status_code} - {response.reason}")
        if response.status_code == 403:
            print(
                "The project may be private. Set SONAR_TOKEN env var for authentication."
            )
        sys.exit(1)

    print("=" * 60)
    print(f"Fetched {len(issues)} issues successfully")

    # Build summary
    summary = build_summary(issues)

    # Prepare output
    report = {
        "metadata": metadata,
        "summary": summary,
        "issues": [format_issue_for_report(i) for i in issues],
    }

    # Write JSON
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"JSON report written to: {output_path}")

    # Write markdown
    write_markdown_report(issues, summary, metadata, output_path)

    # Print quick summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total issues: {metadata['total_fetched']}")
    print(f"Files affected: {summary['total_files_affected']}")
    print(f"Rules triggered: {summary['total_rules_triggered']}")
    print(
        f"Effort: {metadata['effort_total_minutes']} minutes ({metadata['effort_total_minutes'] / 60:.1f} hours)"
    )
    print("\nBy severity:")
    for sev in ["BLOCKER", "CRITICAL", "MAJOR", "MINOR", "INFO"]:
        count = summary["by_severity"].get(sev, 0)
        if count:
            print(f"  {sev}: {count}")
    print("\nBy type:")
    for type_name, count in summary["by_type"].items():
        print(f"  {type_name}: {count}")


if __name__ == "__main__":
    main()
