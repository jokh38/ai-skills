"""Tests for history_manager module"""

import tempfile
from pathlib import Path
import pytest

from core.history_manager import ContextPruner, SessionRecorder
from core.data_types import FailureSignature, PatchToon


@pytest.fixture
def temp_dir():
    """Create temporary directory for history files"""
    temp = Path(tempfile.mkdtemp())
    yield temp
    # Cleanup is handled by tempfile


class TestContextPruner:
    """Test suite for ContextPruner class"""

    def test_initialization(self):
        """Test ContextPruner initialization"""
        pruner = ContextPruner()

        assert len(pruner.issue_log) == 0
        assert len(pruner.last_pruned_items) == 0

    def test_get_active_context_no_failures(self):
        """Test getting active context with no failures"""
        pruner = ContextPruner()
        failures = []

        context = pruner.get_active_context(failures, iteration=1)

        assert context.current_failures == []
        assert context.active_history == []
        assert context.iteration == 1

    def test_get_active_context_with_failures(self):
        """Test getting active context with failures"""
        pruner = ContextPruner()

        failures = [
            FailureSignature("test.py", "foo", "ValueError"),
            FailureSignature("test.py", "bar", "TypeError"),
        ]

        context = pruner.get_active_context(failures, iteration=2)

        assert len(context.current_failures) == 2
        assert context.iteration == 2

    def test_get_active_context_filters_resolved(self):
        """Test that active context filters out resolved issues"""
        pruner = ContextPruner()

        # Add initial failures
        failures = [
            FailureSignature("test.py", "foo", "ValueError"),
            FailureSignature("test.py", "bar", "TypeError"),
        ]
        context1 = pruner.get_active_context(failures, iteration=1)

        # Now only one failure remains (bar resolved)
        new_failures = [FailureSignature("test.py", "foo", "ValueError")]
        context2 = pruner.get_active_context(new_failures, iteration=2)

        assert len(context2.current_failures) == 1
        assert len(pruner.last_pruned_items) == 1

    def test_log_attempt(self):
        """Test logging an attempt"""
        pruner = ContextPruner()

        signature = FailureSignature("test.py", "foo", "ValueError")
        pruner.log_attempt(signature, iteration=1, action="patch", result="success")

        assert len(pruner.issue_log) == 1
        assert pruner.issue_log[0]["target_signature"] == str(signature)

    def test_mark_resolved(self):
        """Test marking an issue as resolved"""
        pruner = ContextPruner()

        signature = FailureSignature("test.py", "foo", "ValueError")
        pruner.log_attempt(signature, iteration=1, action="patch", result="success")
        pruner.mark_resolved(signature)

        assert pruner.is_active(signature) is False

    def test_is_active(self):
        """Test checking if a signature is active"""
        pruner = ContextPruner()

        signature = FailureSignature("test.py", "foo", "ValueError")

        # Before logging, it should be active
        assert pruner.is_active(signature) is True

        # After logging and marking resolved
        pruner.log_attempt(signature, iteration=1, action="patch", result="success")
        pruner.mark_resolved(signature)

        assert pruner.is_active(signature) is False

    def test_reset(self):
        """Test resetting pruner"""
        pruner = ContextPruner()

        signature = FailureSignature("test.py", "foo", "ValueError")
        pruner.log_attempt(signature, iteration=1, action="patch", result="success")
        pruner.reset()

        assert len(pruner.issue_log) == 0
        assert len(pruner.last_pruned_items) == 0


class TestSessionRecorder:
    """Test suite for SessionRecorder class"""

    def test_initialization(self, temp_dir):
        """Test SessionRecorder initialization"""
        recorder = SessionRecorder(session_dir=temp_dir)

        assert recorder.session_dir == temp_dir
        assert len(recorder.iterations) == 0

    def test_append_log(self, temp_dir):
        """Test appending a log entry"""
        recorder = SessionRecorder(session_dir=temp_dir)

        signature = FailureSignature("test.py", "foo", "ValueError")
        patch = PatchToon(
            file_path="test.py", line_range=(1, 2), old_code="old", new_code="new"
        )

        recorder.append_log(
            iteration=1, patch=patch, outcome=[signature], pruned=[], status="success"
        )

        assert len(recorder.iterations) == 1
        assert recorder.iterations[0]["iteration"] == 1

    def test_append_log_without_patch(self, temp_dir):
        """Test appending a log entry without patch"""
        recorder = SessionRecorder(session_dir=temp_dir)

        signature = FailureSignature("test.py", "foo", "ValueError")

        recorder.append_log(
            iteration=1,
            patch=None,
            outcome=[signature],
            pruned=[],
            status="in_progress",
        )

        assert len(recorder.iterations) == 1
        assert "patch" not in recorder.iterations[0]

    def test_save_session_summary(self, temp_dir):
        """Test saving session summary"""
        recorder = SessionRecorder(session_dir=temp_dir)

        summary = recorder.save_session_summary(total_iterations=5, status="completed")

        assert summary.total_iterations == 5
        assert summary.status == "completed"
        assert recorder.summary_file.exists()

    def test_get_session_history(self, temp_dir):
        """Test getting session history"""
        recorder = SessionRecorder(session_dir=temp_dir)

        signature = FailureSignature("test.py", "foo", "ValueError")
        recorder.append_log(
            iteration=1, patch=None, outcome=[signature], pruned=[], status="success"
        )

        history = recorder.get_session_history()

        assert len(history) == 1
        assert history[0]["iteration"] == 1
