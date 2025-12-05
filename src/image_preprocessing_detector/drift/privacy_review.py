"""Privacy review workflow module - Sprint 6.3.6.

CLI-based workflow for reviewing and approving/rejecting harvested samples.

This module provides:
- PrivacyReviewManager: Manages the review workflow
- Batch review operations
- Status tracking and reporting
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from image_preprocessing_detector.drift.active_learning import (
    HarvestedSample,
    ManifestGenerator,
    PrivacyStatus,
)
from image_preprocessing_detector.utils.datetime_compat import utc_now

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

DEFAULT_REVIEW_OUTPUT_DIR = "data/privacy_reviews"


class ReviewDecision(Enum):
    """Review decision for a sample."""

    APPROVE = "approve"
    REJECT = "reject"
    SKIP = "skip"
    FLAG = "flag"  # Flag for additional review


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class ReviewRecord:
    """Record of a privacy review decision."""

    sample_id: str
    decision: ReviewDecision
    reviewer: str
    reviewed_at: datetime
    notes: str = ""
    previous_status: PrivacyStatus = PrivacyStatus.PENDING

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "sample_id": self.sample_id,
            "decision": self.decision.value,
            "reviewer": self.reviewer,
            "reviewed_at": self.reviewed_at.isoformat(),
            "notes": self.notes,
            "previous_status": self.previous_status.value,
        }


@dataclass
class ReviewSession:
    """A privacy review session."""

    session_id: str
    started_at: datetime
    reviewer: str
    manifest_ids: list[str]
    reviews: list[ReviewRecord] = field(default_factory=list)
    completed_at: datetime | None = None
    total_reviewed: int = 0
    approved_count: int = 0
    rejected_count: int = 0
    skipped_count: int = 0
    flagged_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "started_at": self.started_at.isoformat(),
            "reviewer": self.reviewer,
            "manifest_ids": self.manifest_ids,
            "reviews": [r.to_dict() for r in self.reviews],
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "total_reviewed": self.total_reviewed,
            "approved_count": self.approved_count,
            "rejected_count": self.rejected_count,
            "skipped_count": self.skipped_count,
            "flagged_count": self.flagged_count,
        }

    def add_review(self, record: ReviewRecord) -> None:
        """Add a review record and update counts."""
        self.reviews.append(record)
        self.total_reviewed += 1

        if record.decision == ReviewDecision.APPROVE:
            self.approved_count += 1
        elif record.decision == ReviewDecision.REJECT:
            self.rejected_count += 1
        elif record.decision == ReviewDecision.SKIP:
            self.skipped_count += 1
        elif record.decision == ReviewDecision.FLAG:
            self.flagged_count += 1


@dataclass
class ReviewSummary:
    """Summary of samples pending review."""

    total_pending: int = 0
    requires_review: int = 0
    already_approved: int = 0
    already_rejected: int = 0
    by_reason: dict[str, int] = field(default_factory=dict)
    manifests_with_pending: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_pending": self.total_pending,
            "requires_review": self.requires_review,
            "already_approved": self.already_approved,
            "already_rejected": self.already_rejected,
            "by_reason": self.by_reason,
            "manifests_with_pending": self.manifests_with_pending,
        }


# ============================================================================
# Privacy Review Manager
# ============================================================================


class PrivacyReviewManager:
    """Manages the privacy review workflow.

    Provides functionality to:
    - List samples pending review
    - Review and update sample status
    - Track review sessions
    - Generate review reports
    """

    def __init__(
        self,
        manifest_generator: ManifestGenerator,
        output_dir: str = DEFAULT_REVIEW_OUTPUT_DIR,
    ):
        """Initialize review manager.

        Args:
            manifest_generator: Manifest generator for loading/saving manifests
            output_dir: Directory for review session records
        """
        self.manifest_generator = manifest_generator
        self.output_path = Path(output_dir)
        self.output_path.mkdir(parents=True, exist_ok=True)

        self._current_session: ReviewSession | None = None
        self._session_counter = 0

    def get_review_summary(self) -> ReviewSummary:
        """Get summary of samples pending review.

        Returns:
            ReviewSummary with counts and breakdown
        """
        summary = ReviewSummary()

        manifest_paths = self.manifest_generator.list_manifests()

        for manifest_path in manifest_paths:
            manifest = self.manifest_generator.load_manifest(manifest_path)
            has_pending = False

            for sample in manifest.samples:
                if sample.privacy_status == PrivacyStatus.PENDING:
                    summary.total_pending += 1
                    has_pending = True
                    # Count by harvest reason
                    reason = sample.harvest_reason.value
                    summary.by_reason[reason] = summary.by_reason.get(reason, 0) + 1
                elif sample.privacy_status == PrivacyStatus.REQUIRES_REVIEW:
                    summary.requires_review += 1
                    has_pending = True
                    reason = sample.harvest_reason.value
                    summary.by_reason[reason] = summary.by_reason.get(reason, 0) + 1
                elif sample.privacy_status == PrivacyStatus.APPROVED:
                    summary.already_approved += 1
                elif sample.privacy_status == PrivacyStatus.REJECTED:
                    summary.already_rejected += 1

            if has_pending:
                summary.manifests_with_pending.append(manifest.manifest_id)

        return summary

    def get_samples_for_review(
        self,
        manifest_id: str | None = None,
        limit: int = 50,
        include_flagged: bool = True,
    ) -> list[tuple[str, HarvestedSample]]:
        """Get samples that need review.

        Args:
            manifest_id: Specific manifest to review (None for all)
            limit: Maximum samples to return
            include_flagged: Include samples that were flagged

        Returns:
            List of (manifest_id, sample) tuples
        """
        samples_to_review: list[tuple[str, HarvestedSample]] = []

        if manifest_id:
            manifest_paths = [
                p
                for p in self.manifest_generator.list_manifests()
                if manifest_id in p.name
            ]
        else:
            manifest_paths = self.manifest_generator.list_manifests()

        for manifest_path in manifest_paths:
            manifest = self.manifest_generator.load_manifest(manifest_path)

            for sample in manifest.samples:
                if sample.privacy_status in [
                    PrivacyStatus.PENDING,
                    PrivacyStatus.REQUIRES_REVIEW,
                ] or (include_flagged and sample.privacy_notes.startswith("FLAGGED:")):
                    samples_to_review.append((manifest.manifest_id, sample))

                if len(samples_to_review) >= limit:
                    break

            if len(samples_to_review) >= limit:
                break

        return samples_to_review

    def start_review_session(
        self,
        reviewer: str,
        manifest_ids: list[str] | None = None,
    ) -> ReviewSession:
        """Start a new review session.

        Args:
            reviewer: Name/ID of reviewer
            manifest_ids: Specific manifests to review (None for all pending)

        Returns:
            ReviewSession object
        """
        self._session_counter += 1
        session_id = (
            f"review_{utc_now().strftime('%Y%m%d_%H%M%S')}_{self._session_counter:04d}"
        )

        # Get manifests with pending samples if not specified
        if manifest_ids is None:
            summary = self.get_review_summary()
            manifest_ids = summary.manifests_with_pending

        session = ReviewSession(
            session_id=session_id,
            started_at=utc_now(),
            reviewer=reviewer,
            manifest_ids=manifest_ids,
        )

        self._current_session = session

        logger.info(
            f"Started review session {session_id} for {len(manifest_ids)} manifests"
        )

        return session

    def review_sample(
        self,
        manifest_id: str,
        sample_id: str,
        decision: ReviewDecision,
        reviewer: str,
        notes: str = "",
    ) -> bool:
        """Review a single sample and update its status.

        Args:
            manifest_id: ID of manifest containing sample
            sample_id: ID of sample to review
            decision: Review decision
            reviewer: Reviewer name/ID
            notes: Optional review notes

        Returns:
            True if review was recorded successfully
        """
        # Find manifest
        manifest_paths = [
            p for p in self.manifest_generator.list_manifests() if manifest_id in p.name
        ]

        if not manifest_paths:
            logger.error(f"Manifest not found: {manifest_id}")
            return False

        manifest_path = manifest_paths[0]
        manifest = self.manifest_generator.load_manifest(manifest_path)

        # Find sample
        sample = None
        for s in manifest.samples:
            if s.sample_id == sample_id:
                sample = s
                break

        if sample is None:
            logger.error(f"Sample not found: {sample_id}")
            return False

        # Record previous status
        previous_status = sample.privacy_status

        # Update sample status based on decision
        if decision == ReviewDecision.APPROVE:
            sample.privacy_status = PrivacyStatus.APPROVED
            sample.privacy_notes = (
                f"Approved by {reviewer}: {notes}"
                if notes
                else f"Approved by {reviewer}"
            )
        elif decision == ReviewDecision.REJECT:
            sample.privacy_status = PrivacyStatus.REJECTED
            sample.privacy_notes = (
                f"Rejected by {reviewer}: {notes}"
                if notes
                else f"Rejected by {reviewer}"
            )
        elif decision == ReviewDecision.FLAG:
            sample.privacy_status = PrivacyStatus.REQUIRES_REVIEW
            sample.privacy_notes = (
                f"FLAGGED: {notes}" if notes else "FLAGGED by reviewer"
            )
        # SKIP doesn't change status

        # Update manifest counts
        manifest.update_counts()

        # Save updated manifest
        self.manifest_generator.save_manifest(manifest)

        # Record review in session if active
        if self._current_session:
            record = ReviewRecord(
                sample_id=sample_id,
                decision=decision,
                reviewer=reviewer,
                reviewed_at=utc_now(),
                notes=notes,
                previous_status=previous_status,
            )
            self._current_session.add_review(record)

        logger.info(f"Reviewed sample {sample_id}: {decision.value} by {reviewer}")

        return True

    def batch_review(
        self,
        manifest_id: str,
        decision: ReviewDecision,
        reviewer: str,
        notes: str = "",
        sample_ids: list[str] | None = None,
    ) -> int:
        """Batch review multiple samples with the same decision.

        Args:
            manifest_id: Manifest to review
            decision: Decision to apply to all samples
            reviewer: Reviewer name/ID
            notes: Notes for all reviews
            sample_ids: Specific samples (None for all pending)

        Returns:
            Number of samples reviewed
        """
        reviewed = 0

        # Find manifest
        manifest_paths = [
            p for p in self.manifest_generator.list_manifests() if manifest_id in p.name
        ]

        if not manifest_paths:
            return 0

        manifest_path = manifest_paths[0]
        manifest = self.manifest_generator.load_manifest(manifest_path)

        for sample in manifest.samples:
            # Filter by sample_ids if provided
            if sample_ids and sample.sample_id not in sample_ids:
                continue

            # Only review pending samples
            if sample.privacy_status not in [
                PrivacyStatus.PENDING,
                PrivacyStatus.REQUIRES_REVIEW,
            ]:
                continue

            # Update status
            previous_status = sample.privacy_status

            if decision == ReviewDecision.APPROVE:
                sample.privacy_status = PrivacyStatus.APPROVED
                sample.privacy_notes = f"Batch approved by {reviewer}"
            elif decision == ReviewDecision.REJECT:
                sample.privacy_status = PrivacyStatus.REJECTED
                sample.privacy_notes = f"Batch rejected by {reviewer}"
            elif decision == ReviewDecision.FLAG:
                sample.privacy_status = PrivacyStatus.REQUIRES_REVIEW
                sample.privacy_notes = f"FLAGGED: {notes}"

            # Record in session
            if self._current_session:
                record = ReviewRecord(
                    sample_id=sample.sample_id,
                    decision=decision,
                    reviewer=reviewer,
                    reviewed_at=utc_now(),
                    notes=f"Batch review: {notes}",
                    previous_status=previous_status,
                )
                self._current_session.add_review(record)

            reviewed += 1

        # Update and save manifest
        manifest.update_counts()
        self.manifest_generator.save_manifest(manifest)

        logger.info(f"Batch reviewed {reviewed} samples in manifest {manifest_id}")

        return reviewed

    def end_review_session(self) -> ReviewSession | None:
        """End the current review session.

        Returns:
            Completed ReviewSession or None if no active session
        """
        if not self._current_session:
            return None

        session = self._current_session
        session.completed_at = utc_now()

        # Save session record
        self._save_session(session)

        self._current_session = None

        logger.info(
            f"Ended review session {session.session_id}: "
            f"{session.total_reviewed} reviewed, "
            f"{session.approved_count} approved, "
            f"{session.rejected_count} rejected"
        )

        return session

    def _save_session(self, session: ReviewSession) -> None:
        """Save session record to disk."""
        sessions_dir = self.output_path / "sessions"
        sessions_dir.mkdir(exist_ok=True)

        session_path = sessions_dir / f"{session.session_id}.json"
        with open(session_path, "w") as f:
            json.dump(session.to_dict(), f, indent=2)

    def get_session_history(self, limit: int = 20) -> list[ReviewSession]:
        """Get recent review sessions.

        Args:
            limit: Maximum sessions to return

        Returns:
            List of sessions, newest first
        """
        sessions: list[ReviewSession] = []
        sessions_dir = self.output_path / "sessions"

        if not sessions_dir.exists():
            return []

        for session_file in sorted(sessions_dir.glob("*.json"), reverse=True)[:limit]:
            try:
                with open(session_file) as f:
                    data = json.load(f)
                session = self._session_from_dict(data)
                sessions.append(session)
            except Exception:
                logger.exception(f"Failed to load session from {session_file}")

        return sessions

    def _session_from_dict(self, data: dict[str, Any]) -> ReviewSession:
        """Create session from dictionary."""
        from image_preprocessing_detector.utils.datetime_compat import ensure_aware

        reviews = [
            ReviewRecord(
                sample_id=r["sample_id"],
                decision=ReviewDecision(r["decision"]),
                reviewer=r["reviewer"],
                reviewed_at=ensure_aware(datetime.fromisoformat(r["reviewed_at"])),
                notes=r.get("notes", ""),
                previous_status=PrivacyStatus(r.get("previous_status", "pending")),
            )
            for r in data.get("reviews", [])
        ]

        return ReviewSession(
            session_id=data["session_id"],
            started_at=ensure_aware(datetime.fromisoformat(data["started_at"])),
            reviewer=data["reviewer"],
            manifest_ids=data["manifest_ids"],
            reviews=reviews,
            completed_at=(
                ensure_aware(datetime.fromisoformat(data["completed_at"]))
                if data.get("completed_at")
                else None
            ),
            total_reviewed=data.get("total_reviewed", 0),
            approved_count=data.get("approved_count", 0),
            rejected_count=data.get("rejected_count", 0),
            skipped_count=data.get("skipped_count", 0),
            flagged_count=data.get("flagged_count", 0),
        )

    def generate_report(self) -> dict[str, Any]:
        """Generate a review status report.

        Returns:
            Report dictionary with summary and details
        """
        summary = self.get_review_summary()
        sessions = self.get_session_history(limit=5)

        return {
            "generated_at": utc_now().isoformat(),
            "summary": summary.to_dict(),
            "recent_sessions": [s.to_dict() for s in sessions],
            "active_session": (
                self._current_session.to_dict() if self._current_session else None
            ),
        }


# ============================================================================
# CLI Helper Functions
# ============================================================================


def format_sample_for_review(
    sample: HarvestedSample,
    manifest_id: str,
) -> str:
    """Format a sample for CLI review display.

    Args:
        sample: Sample to format
        manifest_id: ID of containing manifest

    Returns:
        Formatted string for display
    """
    lines = [
        f"Sample ID: {sample.sample_id}",
        f"Manifest: {manifest_id}",
        f"Source: {sample.source_path}",
        f"Harvest Reason: {sample.harvest_reason.value}",
        f"Harvest Time: {sample.harvest_time.isoformat()}",
        f"Current Status: {sample.privacy_status.value}",
    ]

    if sample.entropy is not None:
        lines.append(f"Entropy: {sample.entropy:.3f}")
    if sample.agreement_score is not None:
        lines.append(f"Agreement: {sample.agreement_score:.3f}")

    if sample.quality_scores:
        scores = ", ".join(f"{k}: {v:.2f}" for k, v in sample.quality_scores.items())
        lines.append(f"Quality Scores: {scores}")

    if sample.privacy_notes:
        lines.append(f"Notes: {sample.privacy_notes}")

    if sample.metadata:
        lines.append(f"Metadata: {json.dumps(sample.metadata, indent=2)}")

    return "\n".join(lines)


def format_review_summary(summary: ReviewSummary) -> str:
    """Format review summary for CLI display.

    Args:
        summary: Summary to format

    Returns:
        Formatted string
    """
    lines = [
        "=== Privacy Review Summary ===",
        f"Pending Review: {summary.total_pending}",
        f"Requires Manual Review: {summary.requires_review}",
        f"Already Approved: {summary.already_approved}",
        f"Already Rejected: {summary.already_rejected}",
        "",
        "By Harvest Reason:",
    ]

    lines.extend(
        f"  {reason}: {count}" for reason, count in sorted(summary.by_reason.items())
    )

    if summary.manifests_with_pending:
        lines.append("")
        lines.append("Manifests with Pending Samples:")
        lines.extend(f"  - {mid}" for mid in summary.manifests_with_pending[:10])
        if len(summary.manifests_with_pending) > 10:
            lines.append(f"  ... and {len(summary.manifests_with_pending) - 10} more")

    return "\n".join(lines)


# ============================================================================
# Convenience Functions
# ============================================================================


def create_review_manager(
    manifest_dir: str,
    output_dir: str = DEFAULT_REVIEW_OUTPUT_DIR,
) -> PrivacyReviewManager:
    """Create a privacy review manager.

    Args:
        manifest_dir: Directory containing harvest manifests
        output_dir: Directory for review records

    Returns:
        Configured PrivacyReviewManager
    """
    manifest_generator = ManifestGenerator(manifest_dir)
    return PrivacyReviewManager(manifest_generator, output_dir)


__all__ = [
    "DEFAULT_REVIEW_OUTPUT_DIR",
    "PrivacyReviewManager",
    "ReviewDecision",
    "ReviewRecord",
    "ReviewSession",
    "ReviewSummary",
    "create_review_manager",
    "format_review_summary",
    "format_sample_for_review",
]
