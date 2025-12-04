"""Unit tests for privacy review workflow module."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from image_preprocessing_detector.drift.active_learning import (
    HarvestedSample,
    HarvestReason,
    ManifestGenerator,
    PrivacyStatus,
)
from image_preprocessing_detector.drift.privacy_review import (
    PrivacyReviewManager,
    ReviewDecision,
    ReviewRecord,
    ReviewSession,
    ReviewSummary,
    format_review_summary,
    format_sample_for_review,
)
from image_preprocessing_detector.utils.datetime_compat import utc_now


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def manifest_generator(temp_dir: Path) -> ManifestGenerator:
    """Create manifest generator with sample data."""
    generator = ManifestGenerator(temp_dir / "manifests")

    # Create sample manifest
    samples = []
    for i in range(20):
        status = PrivacyStatus.PENDING
        if i < 5:
            status = PrivacyStatus.APPROVED
        elif i < 10:
            status = PrivacyStatus.REQUIRES_REVIEW

        sample = HarvestedSample(
            sample_id=f"sample_{i:04d}",
            source_path=f"/data/sample_{i:04d}.png",
            harvest_time=utc_now(),
            harvest_reason=HarvestReason.HIGH_ENTROPY
            if i % 2 == 0
            else HarvestReason.LOW_AGREEMENT,
            entropy=0.8,
            privacy_status=status,
        )
        samples.append(sample)

    manifest = generator.create_manifest(samples)
    generator.save_manifest(manifest)

    return generator


@pytest.fixture
def review_manager(
    temp_dir: Path, manifest_generator: ManifestGenerator
) -> PrivacyReviewManager:
    """Create privacy review manager."""
    return PrivacyReviewManager(
        manifest_generator,
        output_dir=str(temp_dir / "reviews"),
    )


class TestReviewSummary:
    """Tests for ReviewSummary."""

    def test_summary_creation(self) -> None:
        """Test creating a review summary."""
        summary = ReviewSummary(
            total_pending=10,
            requires_review=5,
            already_approved=20,
            already_rejected=2,
        )

        assert summary.total_pending == 10
        assert summary.requires_review == 5
        assert summary.already_approved == 20

    def test_summary_to_dict(self) -> None:
        """Test summary serialization."""
        summary = ReviewSummary(total_pending=10)
        data = summary.to_dict()

        assert data["total_pending"] == 10
        assert "by_reason" in data


class TestReviewRecord:
    """Tests for ReviewRecord."""

    def test_record_creation(self) -> None:
        """Test creating a review record."""
        record = ReviewRecord(
            sample_id="sample_001",
            decision=ReviewDecision.APPROVE,
            reviewer="test_reviewer",
            reviewed_at=utc_now(),
            notes="Looks good",
        )

        assert record.sample_id == "sample_001"
        assert record.decision == ReviewDecision.APPROVE
        assert record.notes == "Looks good"

    def test_record_to_dict(self) -> None:
        """Test record serialization."""
        record = ReviewRecord(
            sample_id="sample_001",
            decision=ReviewDecision.REJECT,
            reviewer="test_reviewer",
            reviewed_at=utc_now(),
        )

        data = record.to_dict()

        assert data["decision"] == "reject"
        assert data["reviewer"] == "test_reviewer"


class TestReviewSession:
    """Tests for ReviewSession."""

    def test_session_creation(self) -> None:
        """Test creating a review session."""
        session = ReviewSession(
            session_id="session_001",
            started_at=utc_now(),
            reviewer="test_reviewer",
            manifest_ids=["manifest_1", "manifest_2"],
        )

        assert session.session_id == "session_001"
        assert len(session.manifest_ids) == 2
        assert session.total_reviewed == 0

    def test_add_review(self) -> None:
        """Test adding reviews to session."""
        session = ReviewSession(
            session_id="session_001",
            started_at=utc_now(),
            reviewer="test_reviewer",
            manifest_ids=[],
        )

        # Add approved review
        session.add_review(
            ReviewRecord(
                sample_id="s1",
                decision=ReviewDecision.APPROVE,
                reviewer="test",
                reviewed_at=utc_now(),
            )
        )

        # Add rejected review
        session.add_review(
            ReviewRecord(
                sample_id="s2",
                decision=ReviewDecision.REJECT,
                reviewer="test",
                reviewed_at=utc_now(),
            )
        )

        assert session.total_reviewed == 2
        assert session.approved_count == 1
        assert session.rejected_count == 1

    def test_session_to_dict(self) -> None:
        """Test session serialization."""
        session = ReviewSession(
            session_id="session_001",
            started_at=utc_now(),
            reviewer="test_reviewer",
            manifest_ids=["m1"],
        )

        data = session.to_dict()

        assert data["session_id"] == "session_001"
        assert data["reviewer"] == "test_reviewer"


class TestPrivacyReviewManager:
    """Tests for PrivacyReviewManager."""

    def test_get_review_summary(self, review_manager: PrivacyReviewManager) -> None:
        """Test getting review summary."""
        summary = review_manager.get_review_summary()

        assert summary.total_pending > 0 or summary.requires_review > 0
        assert summary.already_approved == 5  # From fixture

    def test_get_samples_for_review(self, review_manager: PrivacyReviewManager) -> None:
        """Test getting samples for review."""
        samples = review_manager.get_samples_for_review(limit=10)

        assert len(samples) > 0
        # Each item is (manifest_id, sample)
        manifest_id, sample = samples[0]
        assert manifest_id is not None
        assert sample.privacy_status in [
            PrivacyStatus.PENDING,
            PrivacyStatus.REQUIRES_REVIEW,
        ]

    def test_start_review_session(self, review_manager: PrivacyReviewManager) -> None:
        """Test starting a review session."""
        session = review_manager.start_review_session(reviewer="test_user")

        assert session is not None
        assert session.reviewer == "test_user"
        assert len(session.manifest_ids) > 0

    def test_review_sample_approve(self, review_manager: PrivacyReviewManager) -> None:
        """Test approving a sample."""
        # Get a sample to review
        samples = review_manager.get_samples_for_review(limit=1)
        assert len(samples) > 0

        manifest_id, sample = samples[0]

        # Start session and approve
        review_manager.start_review_session(reviewer="test_user")
        success = review_manager.review_sample(
            manifest_id=manifest_id,
            sample_id=sample.sample_id,
            decision=ReviewDecision.APPROVE,
            reviewer="test_user",
            notes="Approved for training",
        )

        assert success is True

        # Verify sample was updated
        updated_samples = review_manager.get_samples_for_review()
        sample_ids = [s.sample_id for _, s in updated_samples]
        assert sample.sample_id not in sample_ids  # Should no longer need review

    def test_review_sample_reject(self, review_manager: PrivacyReviewManager) -> None:
        """Test rejecting a sample."""
        samples = review_manager.get_samples_for_review(limit=1)
        assert len(samples) > 0

        manifest_id, sample = samples[0]

        review_manager.start_review_session(reviewer="test_user")
        success = review_manager.review_sample(
            manifest_id=manifest_id,
            sample_id=sample.sample_id,
            decision=ReviewDecision.REJECT,
            reviewer="test_user",
            notes="Contains PII",
        )

        assert success is True

    def test_batch_review(self, review_manager: PrivacyReviewManager) -> None:
        """Test batch reviewing samples."""
        # Get samples
        samples = review_manager.get_samples_for_review(limit=5)
        assert len(samples) > 0

        manifest_id = samples[0][0]

        review_manager.start_review_session(reviewer="test_user")
        count = review_manager.batch_review(
            manifest_id=manifest_id,
            decision=ReviewDecision.APPROVE,
            reviewer="test_user",
            notes="Batch approved",
        )

        assert count > 0

    def test_end_review_session(self, review_manager: PrivacyReviewManager) -> None:
        """Test ending a review session."""
        review_manager.start_review_session(reviewer="test_user")

        # Do some reviews
        samples = review_manager.get_samples_for_review(limit=2)
        for manifest_id, sample in samples:
            review_manager.review_sample(
                manifest_id=manifest_id,
                sample_id=sample.sample_id,
                decision=ReviewDecision.APPROVE,
                reviewer="test_user",
            )

        session = review_manager.end_review_session()

        assert session is not None
        assert session.total_reviewed == 2
        assert session.completed_at is not None

    def test_get_session_history(self, review_manager: PrivacyReviewManager) -> None:
        """Test getting session history."""
        # Create and end a session
        review_manager.start_review_session(reviewer="test_user")
        review_manager.end_review_session()

        history = review_manager.get_session_history()

        assert len(history) >= 1

    def test_generate_report(self, review_manager: PrivacyReviewManager) -> None:
        """Test generating a review report."""
        report = review_manager.generate_report()

        assert "summary" in report
        assert "recent_sessions" in report
        assert "generated_at" in report


class TestReviewDecisions:
    """Tests for review decisions."""

    def test_all_decision_types(self) -> None:
        """Test all decision types."""
        decisions = [
            ReviewDecision.APPROVE,
            ReviewDecision.REJECT,
            ReviewDecision.SKIP,
            ReviewDecision.FLAG,
        ]

        for decision in decisions:
            record = ReviewRecord(
                sample_id="test",
                decision=decision,
                reviewer="test",
                reviewed_at=utc_now(),
            )
            assert record.decision == decision


class TestFormatFunctions:
    """Tests for formatting helper functions."""

    def test_format_sample_for_review(self) -> None:
        """Test formatting a sample for display."""
        sample = HarvestedSample(
            sample_id="sample_001",
            source_path="/data/sample_001.png",
            harvest_time=utc_now(),
            harvest_reason=HarvestReason.HIGH_ENTROPY,
            entropy=0.85,
            agreement_score=0.3,
            privacy_status=PrivacyStatus.PENDING,
        )

        formatted = format_sample_for_review(sample, "manifest_001")

        assert "sample_001" in formatted
        assert "manifest_001" in formatted
        assert "high_entropy" in formatted
        assert "0.85" in formatted  # Entropy

    def test_format_review_summary(self) -> None:
        """Test formatting a review summary."""
        summary = ReviewSummary(
            total_pending=10,
            requires_review=5,
            already_approved=50,
            already_rejected=3,
            by_reason={"high_entropy": 8, "low_agreement": 7},
            manifests_with_pending=["manifest_1", "manifest_2"],
        )

        formatted = format_review_summary(summary)

        assert "Pending Review: 10" in formatted
        assert "Already Approved: 50" in formatted
        assert "high_entropy: 8" in formatted
