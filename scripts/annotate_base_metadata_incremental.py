#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""
Incremental wrapper for annotate_base_metadata.py that processes one dataset at a time.

This script provides crash-resistant processing by:
1. Processing datasets one at a time
2. Saving outputs after each dataset completes
3. Tracking progress in a state file
4. Resuming from last successful dataset on restart

Usage:
    # Process all datasets incrementally
    python scripts/annotate_base_metadata_incremental.py

    # Process specific dataset
    python scripts/annotate_base_metadata_incremental.py --dataset diqa-5000

    # Resume from last checkpoint
    python scripts/annotate_base_metadata_incremental.py --resume

    # Reset state and start fresh
    python scripts/annotate_base_metadata_incremental.py --reset
"""
import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
STATE_FILE = PROJECT_ROOT / ".annotate_progress.json"
E_DRIVE_ROOT = Path("/mnt/e/image_detection")
METADATA_ROOT = E_DRIVE_ROOT / "metadata_registry"

# Import dataset configs from original script
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from annotate_base_metadata import DATASET_CONFIGS


class ProgressTracker:
    """Track progress across multiple runs."""

    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.state = self._load_state()

    def _load_state(self) -> dict[str, Any]:
        """Load progress state from file."""
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)
        return {
            "completed_datasets": [],
            "failed_datasets": {},
            "last_updated": None,
            "total_datasets": len(DATASET_CONFIGS),
        }

    def save_state(self) -> None:
        """Save current state to file."""
        self.state["last_updated"] = datetime.now(UTC).isoformat()
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=2)
        logger.info(f"Progress saved to {self.state_file}")

    def mark_completed(self, dataset_name: str) -> None:
        """Mark a dataset as completed."""
        if dataset_name not in self.state["completed_datasets"]:
            self.state["completed_datasets"].append(dataset_name)
        # Remove from failed if it was there
        self.state["failed_datasets"].pop(dataset_name, None)
        self.save_state()

    def mark_failed(self, dataset_name: str, error: str) -> None:
        """Mark a dataset as failed."""
        self.state["failed_datasets"][dataset_name] = {
            "error": error,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self.save_state()

    def get_pending_datasets(self) -> list[str]:
        """Get list of datasets not yet processed."""
        completed = set(self.state["completed_datasets"])
        all_datasets = set(DATASET_CONFIGS.keys())
        return sorted(all_datasets - completed)

    def reset(self) -> None:
        """Reset all progress."""
        self.state = {
            "completed_datasets": [],
            "failed_datasets": {},
            "last_updated": None,
            "total_datasets": len(DATASET_CONFIGS),
        }
        self.save_state()
        logger.info("Progress reset")

    def print_summary(self) -> None:
        """Print progress summary."""
        total = self.state["total_datasets"]
        completed = len(self.state["completed_datasets"])
        failed = len(self.state["failed_datasets"])
        pending = total - completed

        logger.info("=" * 70)
        logger.info("PROGRESS SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total datasets: {total}")
        logger.info(f"Completed: {completed} ({100*completed/total:.1f}%)")
        logger.info(f"Failed: {failed}")
        logger.info(f"Pending: {pending}")

        if self.state["completed_datasets"]:
            logger.info(f"\nCompleted datasets ({len(self.state['completed_datasets'])}):")
            for ds in self.state["completed_datasets"]:
                logger.info(f"  ✓ {ds}")

        if self.state["failed_datasets"]:
            logger.info(f"\nFailed datasets ({len(self.state['failed_datasets'])}):")
            for ds, info in self.state["failed_datasets"].items():
                logger.info(f"  ✗ {ds}: {info['error']}")

        if self.state.get("last_updated"):
            logger.info(f"\nLast updated: {self.state['last_updated']}")


def process_single_dataset(dataset_name: str, use_yolo: bool = True) -> tuple[bool, str]:
    """
    Process a single dataset using the original script.

    Returns:
        (success: bool, message: str)
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"Processing: {dataset_name}")
    logger.info(f"{'='*70}")

    # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-tainted-env-args
    # dataset_name is validated against DATASET_CONFIGS whitelist before reaching here
    cmd = [
        "uv", "run", "python",
        "scripts/annotate_base_metadata.py",
        "--scan",
        "--dataset", dataset_name,
    ]

    if not use_yolo:
        cmd.append("--no-yolo")

    try:
        # nosemgrep: python.lang.security.audit.dangerous-subprocess-use
        # dataset_name is validated against DATASET_CONFIGS whitelist (see main())
        # subprocess uses list format (no shell), safe against command injection
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour timeout per dataset
            check=False,  # Handle return code explicitly below
        )

        if result.returncode == 0:
            logger.info(f"✓ {dataset_name} completed successfully")
            return True, "Success"
        else:
            error_msg = result.stderr[-500:] if result.stderr else "Unknown error"
            logger.error(f"✗ {dataset_name} failed: {error_msg}")
            return False, error_msg

    except subprocess.TimeoutExpired:
        error_msg = "Timeout after 1 hour"
        logger.error(f"✗ {dataset_name} timed out")
        return False, error_msg

    except Exception as e:
        error_msg = str(e)
        logger.error(f"✗ {dataset_name} crashed: {error_msg}")
        return False, error_msg


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Incremental dataset annotation")
    parser.add_argument("--dataset", type=str, help="Process specific dataset only")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    parser.add_argument("--reset", action="store_true", help="Reset progress and start over")
    parser.add_argument("--no-yolo", action="store_true", help="Disable YOLO inference")
    parser.add_argument("--status", action="store_true", help="Show progress status and exit")

    args = parser.parse_args()

    tracker = ProgressTracker(STATE_FILE)

    if args.reset:
        tracker.reset()
        return

    if args.status:
        tracker.print_summary()
        return

    use_yolo = not args.no_yolo

    # Determine which datasets to process
    if args.dataset:
        if args.dataset not in DATASET_CONFIGS:
            logger.error(f"Unknown dataset: {args.dataset}")
            logger.info(f"Available: {', '.join(DATASET_CONFIGS.keys())}")
            sys.exit(1)
        datasets_to_process = [args.dataset]
    else:
        datasets_to_process = tracker.get_pending_datasets()

    if not datasets_to_process:
        logger.info("All datasets already processed!")
        tracker.print_summary()
        return

    logger.info(f"Processing {len(datasets_to_process)} dataset(s)")
    logger.info(f"YOLO: {'ENABLED' if use_yolo else 'DISABLED'}")
    logger.info(f"Output: {METADATA_ROOT}")

    # Process each dataset
    for i, dataset_name in enumerate(datasets_to_process, 1):
        logger.info(f"\n[{i}/{len(datasets_to_process)}] {dataset_name}")

        success, message = process_single_dataset(dataset_name, use_yolo=use_yolo)

        if success:
            tracker.mark_completed(dataset_name)
        else:
            tracker.mark_failed(dataset_name, message)
            logger.warning(f"Continuing to next dataset despite failure...")

    # Final summary
    logger.info("\n")
    tracker.print_summary()

    if tracker.state["failed_datasets"]:
        logger.warning("\nSome datasets failed. Review errors above and retry with --resume")
        sys.exit(1)
    else:
        logger.info("\n✓ All datasets processed successfully!")


if __name__ == "__main__":
    main()
