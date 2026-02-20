#!/usr/bin/env python3
"""Resolve unresolved GitHub PR review threads via GraphQL API.

Reuses queries from check_unresolved_pr_comments.py to find unresolved threads,
then resolves them via GraphQL mutation.

Usage:
    python scripts/resolve_pr_comments.py                          # dry-run
    python scripts/resolve_pr_comments.py --execute                # resolve all
    python scripts/resolve_pr_comments.py --execute --thread-ids PRRT_abc
    python scripts/resolve_pr_comments.py --repo owner/repo --execute
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess  # nosec B404
import sys

from check_unresolved_pr_comments import (
    _GRAPHQL_PR_LIST,
    _GRAPHQL_PR_THREADS,
    _REPO_SLUG_RE,
    _SCANNER_AUTHORS,
    _SCANNER_PATTERNS,
)

_GRAPHQL_RESOLVE_THREAD = 'mutation { resolveReviewThread(input: {threadId: "%s"}) { thread { isResolved } } }'

# GitHub PR review thread IDs follow the PRRT_ prefix pattern
_THREAD_ID_RE = re.compile(r"^PRRT_[A-Za-z0-9]+$")


def _run_graphql(query: str) -> dict:
    """Execute a GraphQL query via gh CLI."""
    result = subprocess.run(  # nosec B603 B607
        ["gh", "api", "graphql", "-f", f"query={query}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"Error: {result.stderr.strip()}", file=sys.stderr)
        return {}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print(f"Error parsing GitHub API response: {exc}", file=sys.stderr)
        return {}


def _fetch_unresolved_threads(owner: str, repo: str) -> list[dict]:
    """Fetch all unresolved, non-scanner review threads from merged PRs."""
    pr_data = _run_graphql(_GRAPHQL_PR_LIST % (owner, repo))
    if not pr_data:
        print("Failed to fetch PR list", file=sys.stderr)
        sys.exit(1)

    try:
        pr_numbers = [
            pr["number"]
            for pr in pr_data["data"]["repository"]["pullRequests"]["nodes"]
        ]
    except (KeyError, TypeError) as exc:
        print(f"Unexpected PR list response structure: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Scanning {len(pr_numbers)} merged PRs...", file=sys.stderr)

    threads: list[dict] = []
    for pr_num in pr_numbers:
        result = _run_graphql(_GRAPHQL_PR_THREADS % (owner, repo, pr_num))
        if not result or "data" not in result:
            continue
        pr = result["data"]["repository"]["pullRequest"]
        if not pr:
            continue

        for thread in pr["reviewThreads"]["nodes"]:
            if thread["isResolved"]:
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

            threads.append(
                {
                    "thread_id": thread.get("id", ""),
                    "pr": pr["number"],
                    "pr_title": pr["title"],
                    "author": author,
                    "path": first.get("path", ""),
                    "body": body[:80].replace("\n", " "),
                }
            )
    return threads


def _resolve_thread(thread_id: str) -> bool:
    """Resolve a single review thread. Returns True on success."""
    if not _THREAD_ID_RE.match(thread_id):
        print(f"Skipping invalid thread ID: {thread_id!r}", file=sys.stderr)
        return False
    result = _run_graphql(_GRAPHQL_RESOLVE_THREAD % thread_id)
    if not result:
        return False
    try:
        return result["data"]["resolveReviewThread"]["thread"]["isResolved"]
    except (KeyError, TypeError):
        return False


def main() -> None:
    """Run the PR comment resolver."""
    parser = argparse.ArgumentParser(
        description="Resolve unresolved PR review threads."
    )
    parser.add_argument(
        "--repo",
        default="williaby/image-preprocessing-detector",
        help="GitHub repo in owner/name format (default: %(default)s)",
    )
    parser.add_argument(
        "--execute", action="store_true", help="Actually resolve (default: dry-run)"
    )
    parser.add_argument("--thread-ids", nargs="+", help="Resolve only these thread IDs")
    args = parser.parse_args()

    if "/" not in args.repo or args.repo.count("/") != 1:
        print(
            f"Error: --repo must be in owner/name format, got {args.repo!r}",
            file=sys.stderr,
        )
        sys.exit(1)
    owner, repo = args.repo.split("/")
    for slug, name in ((owner, "owner"), (repo, "repo")):
        if not _REPO_SLUG_RE.match(slug):
            print(f"Error: invalid {name} slug {slug!r}", file=sys.stderr)
            sys.exit(1)
    threads = _fetch_unresolved_threads(owner, repo)

    if args.thread_ids:
        target_ids = set(args.thread_ids)
        threads = [t for t in threads if t["thread_id"] in target_ids]

    if not threads:
        print("No unresolved threads found.")
        return

    print(f"\nFound {len(threads)} unresolved thread(s):\n")
    for t in threads:
        print(f"  [{t['thread_id'][:16]}...] PR #{t['pr']} @{t['author']} {t['path']}")
        print(f"    {t['body']}")

    if not args.execute:
        print(
            f"\nDry-run: {len(threads)} thread(s) would be resolved. Re-run with --execute."
        )
        return

    print(f"\nResolving {len(threads)} thread(s)...")
    resolved = failed = 0
    for t in threads:
        ok = _resolve_thread(t["thread_id"])
        tag = "Resolved" if ok else "FAILED"
        print(f"  {tag}: {t['thread_id'][:16]}... (PR #{t['pr']})")
        if ok:
            resolved += 1
        else:
            failed += 1

    print(f"\nSummary: {resolved} resolved, {failed} failed, {len(threads)} total")


if __name__ == "__main__":
    main()
