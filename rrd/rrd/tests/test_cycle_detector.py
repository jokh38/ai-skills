"""Tests for cycle_detector module"""

import pytest

from core.cycle_detector import CycleDetector
from core.data_types import PatchToon


class TestCycleDetector:
    """Test suite for CycleDetector class"""

    def test_initialization(self):
        """Test CycleDetector initialization"""
        detector = CycleDetector(window_size=4)
        assert detector.window_size == 4
        assert len(detector.state.patch_hash_history) == 0
        assert len(detector.state.signature_history) == 0

    def test_initialization_default(self):
        """Test CycleDetector with default window_size"""
        detector = CycleDetector()
        assert detector.window_size == 4

    def test_check_duplicate_patch_new_patch(self):
        """Test duplicate detection with new patch"""
        detector = CycleDetector()
        patch = PatchToon(
            file_path="test.py", line_range=(1, 2), old_code="old", new_code="new"
        )

        is_duplicate = detector.check_duplicate_patch(patch)

        assert is_duplicate is False
        assert detector.state.last_patch == patch

    def test_check_duplicate_patch_exact_duplicate(self):
        """Test duplicate detection with exact duplicate"""
        detector = CycleDetector()
        patch = PatchToon(
            file_path="test.py", line_range=(1, 2), old_code="old", new_code="new"
        )

        detector.check_duplicate_patch(patch)
        is_duplicate = detector.check_duplicate_patch(patch)

        assert is_duplicate is True

    def test_check_duplicate_patch_different_code(self):
        """Test duplicate detection with different new_code"""
        detector = CycleDetector()
        patch1 = PatchToon(
            file_path="test.py", line_range=(1, 2), old_code="old", new_code="new1"
        )
        patch2 = PatchToon(
            file_path="test.py", line_range=(1, 2), old_code="old", new_code="new2"
        )

        detector.check_duplicate_patch(patch1)
        is_duplicate = detector.check_duplicate_patch(patch2)

        assert is_duplicate is False

    def test_check_signature_cycle_no_history(self):
        """Test signature cycle detection with no history"""
        detector = CycleDetector()
        signatures = frozenset(["sig1", "sig2"])

        is_cycle = detector.check_signature_cycle(signatures)

        assert is_cycle is False

    def test_check_signature_cycle_match(self):
        """Test signature cycle detection with matching signature"""
        detector = CycleDetector(window_size=3)

        # Add same signature 3 times
        signatures = frozenset(["sig1", "sig2"])
        for _ in range(3):
            detector.check_signature_cycle(signatures)

        is_cycle = detector.check_signature_cycle(signatures)

        assert is_cycle is True

    def test_check_signature_cycle_window_limit(self):
        """Test signature cycle detection respects window size"""
        detector = CycleDetector(window_size=2)

        # Add same signature 3 times
        signatures1 = frozenset(["sig1"])
        signatures2 = frozenset(["sig2"])

        for _ in range(3):
            detector.check_signature_cycle(signatures1)
        detector.check_signature_cycle(signatures2)

        is_cycle = detector.check_signature_cycle(signatures1)

        assert is_cycle is False
        assert len(detector.state.signature_history) <= 2

    def test_reset(self):
        """Test resetting cycle detector"""
        detector = CycleDetector()
        patch = PatchToon(
            file_path="test.py", line_range=(1, 2), old_code="old", new_code="new"
        )

        detector.check_duplicate_patch(patch)
        detector.check_signature_cycle(frozenset(["sig1"]))
        detector.reset()

        assert len(detector.state.patch_hash_history) == 0
        assert len(detector.state.signature_history) == 0
        assert detector.state.last_patch is None
        assert detector.state.last_patch_hash is None

    def test_get_state(self):
        """Test getting current state"""
        detector = CycleDetector()
        state = detector.get_state()

        assert state.patch_hash_history == []
        assert state.signature_history == []
        assert state.last_patch is None
        assert state.last_patch_hash is None
