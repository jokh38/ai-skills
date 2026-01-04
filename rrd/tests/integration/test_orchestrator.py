"""Integration tests for RRD Orchestrator"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from orchestrator.rrd_orchestrator import RRDOrchestrator
from orchestrator.session_manager import SessionManager


class TestRRDOrchestrator:
    """Test suite for RRDOrchestrator"""

    @pytest.fixture
    def workspace(self, tmp_path):
        """Create temporary workspace for testing"""
        return tmp_path

    @pytest.fixture
    def spec_file(self, tmp_path):
        """Create a sample specification file"""
        spec = tmp_path / "spec.md"
        spec.write_text("""
# Feature: Calculator

Implement a simple calculator with the following operations:
- add(a, b): Returns sum of a and b
- subtract(a, b): Returns difference of a and b
- multiply(a, b): Returns product of a and b
- divide(a, b): Returns quotient of a and b (raises ZeroDivisionError if b=0)

All functions should accept int or float and return the same type.
""")
        return spec

    @pytest.fixture
    def orchestrator(self, workspace):
        """Create RRDOrchestrator instance"""
        return RRDOrchestrator(config_path=None, workspace=workspace)

    def test_initialization(self, orchestrator, workspace):
        """Test orchestrator initialization"""
        assert orchestrator.workspace == workspace
        assert orchestrator.config is not None
        assert orchestrator.session_manager is not None
        assert orchestrator.phase_executor is not None
        assert orchestrator.cycle_detector is not None

    def test_session_manager_initialization(self, orchestrator):
        """Test session manager is properly initialized"""
        assert isinstance(orchestrator.session_manager, SessionManager)
        assert orchestrator.session_manager.workspace == orchestrator.workspace

    @patch("orchestrator.phase_executor.PhaseExecutor")
    def test_execute_l1_context_success(self, mock_executor, orchestrator, spec_file, workspace):
        """Test L1 phase execution succeeds"""
        # Mock phase executor methods
        mock_phase_executor = mock_executor.return_value
        mock_phase_executor.l1_load_knowledge.return_value = []
        mock_phase_executor.l1_analyze_codebase.return_value = Mock(
            file_summary=[Mock()], structure={}
        )
        mock_phase_executor.l1_generate_adversarial_tests.return_value = [
            workspace / "rrd" / "tests" / "test_feature.py"
        ]

        # Execute L1
        result = orchestrator.execute_l1_context(spec_file)

        # Verify result
        assert result.status == "completed"
        assert len(result.tests_generated) > 0
        assert result.codebase_analysis is not None
        assert isinstance(result.knowledge_kernel, list)

    @patch("orchestrator.phase_executor.PhaseExecutor")
    @patch("pathlib.Path.write_text")
    def test_execute_l2_cycle_success(
        self, mock_write, mock_executor, orchestrator, spec_file, workspace
    ):
        """Test L2 phase execution succeeds"""
        # Mock phase executor methods
        mock_phase_executor = mock_executor.return_value
        mock_phase_executor.l2_red_create_skeleton.return_value = [
            workspace / "rrd" / "skeleton.py"
        ]

        mock_green_result = Mock(
            files_created=[workspace / "rrd" / "src" / "implementation.py"],
            attempts=2,
            success=True,
            quality_score=85.0,
        )
        mock_phase_executor.l2_green_implement.return_value = mock_green_result

        mock_qa_result = Mock(
            quality_report=Mock(quality_score=85.0),
            gate_results=Mock(passed=True),
            auto_fixes=[],
            status="passed",
        )
        mock_phase_executor.l2_blue_qa_analysis.return_value = mock_qa_result

        # Mock test file existence
        test_file = workspace / "rrd" / "tests" / "test_feature.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("# Test file")

        # Execute L2
        result = orchestrator.execute_l2_cycle(spec_file.read_text())

        # Verify result
        assert result.status == "completed"
        assert result.cycle_count == 0
        assert result.quality_report is not None
        assert result.gate_results.passed is True

    @patch("orchestrator.phase_executor.PhaseExecutor")
    def test_execute_l3_hardening_success(self, mock_executor, orchestrator):
        """Test L3 phase execution succeeds"""
        # Mock phase executor methods
        mock_phase_executor = mock_executor.return_value

        mock_qa_result = Mock(
            quality_report=Mock(quality_score=90.0),
            gate_results=Mock(passed=True, failed_gates=[]),
            auto_fixes=[],
            status="passed",
        )
        mock_phase_executor.l3_hardening_qa.return_value = mock_qa_result

        mock_review_result = Mock(findings=[], critical_count=0, high_count=0, status="passed")
        mock_phase_executor.l3_adversarial_review.return_value = mock_review_result

        # Execute L3
        result = orchestrator.execute_l3_hardening()

        # Verify result
        assert result.status == "completed"
        assert result.quality_score == 90.0
        assert result.gate_results.passed is True
        assert result.critical_count == 0

    @patch("orchestrator.phase_executor.PhaseExecutor")
    def test_execute_l4_documentation_success(
        self, mock_executor, orchestrator, spec_file, workspace
    ):
        """Test L4 phase execution succeeds"""
        # Mock phase executor methods
        mock_phase_executor = mock_executor.return_value
        mock_phase_executor.l4_update_knowledge_kernel.return_value = None
        mock_phase_executor.llm.generate_documentation.return_value = "# Documentation"
        mock_phase_executor.l4_commit_with_context.return_value = "abc123"

        # Create implementation and test files
        impl_file = workspace / "rrd" / "src" / "implementation.py"
        test_file = workspace / "rrd" / "tests" / "test_feature.py"
        impl_file.parent.mkdir(parents=True, exist_ok=True)
        impl_file.write_text("# Implementation")
        test_file.write_text("# Tests")

        # Execute L4
        result = orchestrator.execute_l4_documentation(spec_file)

        # Verify result
        assert result.status == "completed"
        assert result.commit_hash == "abc123"
        assert result.documentation_generated is True
        assert result.knowledge_updated is True

    @patch.object(RRDOrchestrator, "execute_l1_context")
    @patch.object(RRDOrchestrator, "execute_l2_cycle")
    @patch.object(RRDOrchestrator, "execute_l3_hardening")
    @patch.object(RRDOrchestrator, "execute_l4_documentation")
    def test_execute_full_workflow_success(
        self, mock_l4, mock_l3, mock_l2, mock_l1, orchestrator, spec_file
    ):
        """Test full workflow execution succeeds"""
        # Mock all phases
        mock_l1.return_value = Mock(
            tests_generated=[],
            knowledge_kernel=[],
            codebase_analysis=Mock(file_summary=[]),
            status="completed",
        )
        mock_l2.return_value = Mock(
            implementation_files=[],
            quality_report=Mock(quality_score=85.0),
            gate_results=Mock(passed=True),
            cycle_count=0,
            status="completed",
        )
        mock_l3.return_value = Mock(
            security_findings=[],
            quality_score=90.0,
            quality_report=Mock(quality_score=90.0),
            gate_results=Mock(passed=True),
            status="completed",
        )
        mock_l4.return_value = Mock(
            commit_hash="abc123",
            documentation_generated=True,
            knowledge_updated=True,
            status="completed",
        )

        # Execute full workflow
        result = orchestrator.execute_full_workflow(spec_file)

        # Verify result
        assert result.session_id is not None
        assert len(result.phases_completed) == 4
        assert "L1_load_knowledge" in result.phases_completed
        assert "L1_analyze" in result.phases_completed
        assert "L2_red" in result.phases_completed
        assert "L3_hardening_qa" in result.phases_completed

    @patch.object(RRDOrchestrator, "execute_l1_context")
    def test_execute_full_workflow_l1_failure(self, mock_l1, orchestrator, spec_file):
        """Test full workflow handles L1 failure"""
        # Mock L1 failure
        mock_l1.return_value = Mock(
            tests_generated=[], knowledge_kernel=[], codebase_analysis=None, status="failed"
        )

        # Execute full workflow should raise exception
        with pytest.raises(RuntimeError):
            orchestrator.execute_full_workflow(spec_file)
