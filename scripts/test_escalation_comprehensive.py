#!/usr/bin/env python3
"""Comprehensive test of the tiered language detection escalation system.

Tests:
1. Script validation catching mismatches
2. Tier 1b free vision model detection
3. Escalation flow from Tier 1a → 1b → 2
4. Human review queue population
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.language_escalation import (
    EscalationConfig,
    EscalationManager,
    validate_language_script_match,
    detect_via_vision_llm,
    SCRIPT_VALID_LANGUAGES,
)


# =============================================================================
# Test Data
# =============================================================================


@dataclass
class MockLocalResult:
    """Mock result from Tier 1a local detection."""

    primary_language: str = "und"
    primary_script: str | None = None
    detected_languages: list[str] = field(default_factory=list)
    detected_scripts: list[str] = field(default_factory=list)
    confidence: float = 0.5
    method: str = "mock"
    votes: list = field(default_factory=list)
    is_multilingual: bool = False


@dataclass
class MockVote:
    """Mock detector vote."""

    language: str
    confidence: float
    detector: str


# =============================================================================
# Test 1: Script Validation
# =============================================================================


def test_script_validation():
    """Test script-language validation catches mismatches."""
    print("\n" + "=" * 60)
    print("TEST 1: Script-Language Validation")
    print("=" * 60)

    test_cases = [
        # (language, scripts, expected_valid, description)
        ("en", ["Latn"], True, "English + Latin script = valid"),
        ("ar", ["Arab"], True, "Arabic + Arabic script = valid"),
        ("hi", ["Deva"], True, "Hindi + Devanagari = valid"),
        ("ja", ["Jpan"], True, "Japanese + Japanese script = valid"),
        ("zh", ["Hans"], True, "Chinese + Simplified Han = valid"),
        ("bo", ["Tibt"], True, "Tibetan + Tibetan script = valid"),
        ("dz", ["Tibt"], True, "Dzongkha + Tibetan script = valid"),
        # Mismatches
        ("en", ["Tibt"], False, "English + Tibetan script = INVALID"),
        ("ar", ["Latn"], False, "Arabic + Latin script = INVALID"),
        ("zh", ["Deva"], False, "Chinese + Devanagari = INVALID"),
        ("ru", ["Latn"], False, "Russian + Latin script = INVALID"),
        # Edge cases
        ("und", ["Latn"], True, "Undetermined language = always valid"),
        ("mul", ["Latn"], True, "Multiple languages = always valid"),
        ("en", [], True, "No script detected = always valid"),
    ]

    passed = 0
    failed = 0

    for lang, scripts, expected_valid, desc in test_cases:
        result = validate_language_script_match(lang, scripts)
        status = "✓" if result.is_valid == expected_valid else "✗"

        if result.is_valid == expected_valid:
            passed += 1
            print(f"  {status} {desc}")
        else:
            failed += 1
            print(f"  {status} {desc}")
            print(f"      Expected: {expected_valid}, Got: {result.is_valid}")
            if result.mismatch_reason:
                print(f"      Reason: {result.mismatch_reason}")

    print(f"\n  Results: {passed}/{passed + failed} passed")
    return failed == 0


# =============================================================================
# Test 2: Tier 1b Free Vision Detection
# =============================================================================


def test_tier1b_vision():
    """Test Tier 1b free vision model detection."""
    print("\n" + "=" * 60)
    print("TEST 2: Tier 1b Free Vision Model")
    print("=" * 60)

    # Test images with known languages
    test_images = [
        Path(
            "/mnt/e/datasets/MLT-19/MLT19/test/ts_000035.jpg"
        ),  # Should have Latin text
        Path("/mnt/e/datasets/MLT-19/MLT19/test/ts_000001.jpg"),  # Another test
    ]

    available_images = [p for p in test_images if p.exists()]

    if not available_images:
        print("  ⚠ No test images available, skipping vision test")
        return True

    model = "qwen/qwen-2.5-vl-7b-instruct:free"
    print(f"  Using model: {model}")

    for image_path in available_images[:2]:  # Test up to 2 images
        print(f"\n  Testing: {image_path.name}")

        result = detect_via_vision_llm(image_path, model)

        if result:
            print("    ✓ API call successful")
            print(f"    Primary language: {result.get('primary_language', 'N/A')}")
            print(f"    Primary script: {result.get('primary_script', 'N/A')}")
            print(f"    Confidence: {result.get('total_confidence', 'N/A')}")
            print(f"    Is multilingual: {result.get('is_multilingual', 'N/A')}")

            languages = result.get("languages", [])
            if languages:
                print(f"    Languages detected ({len(languages)}):")
                for lang in languages[:5]:  # Show first 5
                    print(
                        f"      - {lang.get('code')}: {lang.get('confidence', 'N/A')}"
                    )
        else:
            print("    ✗ API call failed")
            return False

    return True


# =============================================================================
# Test 3: Full Escalation Flow
# =============================================================================


def test_escalation_flow():
    """Test full escalation flow from Tier 1a → 1b → 2."""
    print("\n" + "=" * 60)
    print("TEST 3: Full Escalation Flow")
    print("=" * 60)

    test_image = Path("/mnt/e/datasets/MLT-19/MLT19/test/ts_000035.jpg")

    if not test_image.exists():
        print("  ⚠ Test image not available, skipping escalation test")
        return True

    # Test scenarios
    scenarios = [
        {
            "name": "High confidence - No escalation",
            "local_result": MockLocalResult(
                primary_language="en",
                primary_script="Latn",
                detected_languages=["en"],
                detected_scripts=["Latn"],
                confidence=0.85,
                votes=[
                    MockVote("en", 0.9, "fasttext"),
                    MockVote("en", 0.8, "lingua"),
                ],
            ),
            "expected_tier": 1,
            "expected_method_contains": "tier1a",
        },
        {
            "name": "Low confidence - Escalate to Tier 1b",
            "local_result": MockLocalResult(
                primary_language="en",
                primary_script="Latn",
                detected_languages=["en"],
                detected_scripts=["Latn"],
                confidence=0.4,
                votes=[
                    MockVote("en", 0.4, "fasttext"),
                    MockVote("fr", 0.3, "lingua"),
                ],
            ),
            "expected_tier": 1,  # Should resolve at Tier 1b
            "expected_method_contains": "tier1b",
        },
        {
            "name": "Script mismatch - Force escalation",
            "local_result": MockLocalResult(
                primary_language="en",  # English detected
                primary_script="Tibt",  # But Tibetan script - mismatch!
                detected_languages=["en"],
                detected_scripts=["Tibt"],
                confidence=0.7,
                votes=[MockVote("en", 0.7, "fasttext")],
            ),
            "expected_tier": 1,  # Should escalate due to mismatch
            "expected_method_contains": "tier1b",
        },
    ]

    config = EscalationConfig(
        confidence_threshold=0.6,
        tier1b_confidence_threshold=0.7,
        validate_script_match=True,
    )
    manager = EscalationManager(config)

    passed = 0
    for scenario in scenarios:
        print(f"\n  Scenario: {scenario['name']}")

        result = manager.detect(test_image, scenario["local_result"])

        tier_ok = result.tier == scenario["expected_tier"]
        method_ok = scenario["expected_method_contains"] in result.method

        if tier_ok and method_ok:
            print(f"    ✓ Tier: {result.tier} (expected {scenario['expected_tier']})")
            print(f"    ✓ Method: {result.method}")
            print(f"    Language: {result.primary_language}")
            print(f"    Confidence: {result.confidence:.2f}")
            passed += 1
        else:
            print(f"    ✗ Tier: {result.tier} (expected {scenario['expected_tier']})")
            print(
                f"    ✗ Method: {result.method} (expected to contain '{scenario['expected_method_contains']}')"
            )

    print(f"\n  Results: {passed}/{len(scenarios)} scenarios passed")
    return passed == len(scenarios)


# =============================================================================
# Test 4: Review Queue
# =============================================================================


def test_review_queue():
    """Test human review queue population."""
    print("\n" + "=" * 60)
    print("TEST 4: Human Review Queue")
    print("=" * 60)

    from scripts.language_escalation import queue_for_review, EscalationConfig
    import tempfile
    import json

    # Create temp queue directory
    with tempfile.TemporaryDirectory() as tmpdir:
        config = EscalationConfig(
            review_queue_path=Path(tmpdir),
        )

        # Create mock data
        local_result = MockLocalResult(
            primary_language="und",
            confidence=0.3,
        )

        tier2_result = {
            "primary_language": "en",
            "total_confidence": 0.5,
        }

        # Queue for review
        test_image = Path("/tmp/test_image.jpg")
        queue_for_review(
            test_image,
            local_result,
            tier2_result,
            reason="test_low_confidence",
            config=config,
        )

        # Verify queue file created
        queue_file = Path(tmpdir) / "pending_review.jsonl"

        if queue_file.exists():
            print("  ✓ Queue file created")

            with open(queue_file) as f:
                entry = json.loads(f.readline())

            if entry.get("reason") == "test_low_confidence":
                print("  ✓ Entry has correct reason")
            else:
                print(f"  ✗ Wrong reason: {entry.get('reason')}")
                return False

            if entry.get("status") == "pending":
                print("  ✓ Entry status is 'pending'")
            else:
                print(f"  ✗ Wrong status: {entry.get('status')}")
                return False

            return True
        print("  ✗ Queue file not created")
        return False


# =============================================================================
# Test 5: Script Coverage
# =============================================================================


def test_script_coverage():
    """Test that we have good script-language coverage."""
    print("\n" + "=" * 60)
    print("TEST 5: Script-Language Coverage")
    print("=" * 60)

    total_scripts = len(SCRIPT_VALID_LANGUAGES)
    total_languages = sum(len(langs) for langs in SCRIPT_VALID_LANGUAGES.values())

    print(f"  Scripts covered: {total_scripts}")
    print(f"  Languages mapped: {total_languages}")

    # Check key scripts
    key_scripts = [
        "Latn",
        "Arab",
        "Deva",
        "Hans",
        "Hant",
        "Jpan",
        "Kore",
        "Cyrl",
        "Tibt",
    ]
    missing = [s for s in key_scripts if s not in SCRIPT_VALID_LANGUAGES]

    if missing:
        print(f"  ✗ Missing key scripts: {missing}")
        return False
    print("  ✓ All key scripts covered")

    # Sample coverage
    print("\n  Sample script mappings:")
    for script in key_scripts[:5]:
        langs = sorted(SCRIPT_VALID_LANGUAGES.get(script, set()))[:5]
        print(f"    {script}: {', '.join(langs)}...")

    return True


# =============================================================================
# Main
# =============================================================================


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("COMPREHENSIVE ESCALATION SYSTEM TEST")
    print("=" * 60)

    results = {
        "Script Validation": test_script_validation(),
        "Script Coverage": test_script_coverage(),
        "Review Queue": test_review_queue(),
        "Tier 1b Vision": test_tier1b_vision(),
        "Escalation Flow": test_escalation_flow(),
    }

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test_name}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
